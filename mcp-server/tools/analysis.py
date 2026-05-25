"""分析报告类 MCP Tool (5个): 事件分析、财报分析、业绩前瞻、行业概览、催化剂日历."""

import json
import os
from datetime import datetime
from shared.clients import DataSourceManager
from shared.formatters import now_str, date_to_short

_ds = DataSourceManager()

STOCK_EVENT_ANALYSIS_PROMPT = """你是一个资深A股分析师。请按以下框架对上市公司事件进行三维联动分析。

## 分析框架

### Step 1: 风险初筛
检查事件是否触及：监管立案/ST/退市风险/债务违约。若是，直接判定【高风险-远离】。

### Step 2: 三维联动分析
- 基本面(EPS)：该事件能否在未来1-3个季度真实提升/降低公司每股收益？
- 估值面(PE)：该事件是否顺应当前政策热点/行业趋势，能否提升估值溢价？
- 筹码面(Money Flow)：事件带来了未来解禁抛压，还是大股东/机构真金白银锁仓？

### Step 3: 影响周期判定
- 脉冲性(短期)：仅影响1-5个交易日
- 趋势性(中长期)：能改变公司中期走势或基本面拐点

## 输出格式（严格遵守）

返回 Markdown 格式报告，结构如下：

# 📊 【事件自动化分析报告】 公司名(股票代码)

## 1. 事件画像
- 事件类型：[...]
- 事件摘要：[一句话核心事实]
- 公告日期：[YYYY-MM-DD]

## 2. 核心维度剖析
- 核心基本面变动：[...]
- 筹码供求与信心：[...]
- 外部行业匹配度：[...]

## 3. 综合评级与落地建议
- 事件属性：[短期脉冲 / 中期趋势变动 / 长期基本面重塑]
- 综合信号评级：[🔴 强风险-远离 / 🟡 中性-观察 / 🟢 积极-正向催化]
- 操作避坑提示：[至少3条，含⚠️风险点和✅积极信号]

## 4. 数据来源
列出数据来源"""

EARNINGS_ANALYSIS_PROMPT = """你是一个资深A股分析师。请分析以下公司财报数据。

按以下结构输出Markdown报告：
1. 业绩快照（营收/利润/利润率同比环比变化）
2. beat/miss 分析（vs 市场预期）
3. 业绩变动原因拆解
4. 下一季度展望
5. 综合评级"""

SECTOR_OVERVIEW_PROMPT = """你是一个资深行业分析师。请生成指定行业的概览报告。

按以下结构输出Markdown报告：
1. 行业整体表现（近期涨跌幅、估值水平）
2. 龙头公司对比
3. 近期政策与事件催化
4. 行业展望与投资建议"""

CATALYST_PROMPT = """你是一个金融市场日历分析师。请根据搜索到的近期事件信息，
生成催化剂日历。列出即将到来的重要事件和日期，评估每项事件的影响级别(高/中/低)。"""


def _get_skill_prompt_path() -> str:
    return os.path.join(
        os.path.dirname(__file__),
        "..", "..", "plugins", "vertical-plugins", "equity-research",
        "skills", "stock-event-analysis", "SKILL.md",
    )


def _save_report(company: str, content: str) -> str:
    """保存报告到 reports/ 目录."""
    reports_dir = os.path.join(os.getcwd(), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    short_date = datetime.now().strftime("%y%m%d")
    filename = f"{company}_事件分析报告_{short_date}.md"
    filepath = os.path.join(reports_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


async def analyze_event(
    company_name: str,
    stock_code: str,
    event_description: str = "",
) -> str:
    """对A股上市公司事件进行自动化影响分析。

    执行三维联动分析（基本面EPS × 估值面PE × 筹码面Money Flow），
    输出结构化的事件分析报告（Markdown格式），并保存到 reports/ 目录。
    分析框架来源：equity-research/stock-event-analysis skill。

    Args:
        company_name: 公司中文简称（如 "招商银行"）
        stock_code: 6位股票代码（如 "600036"）
        event_description: 事件描述（可选，为空则分析近期最重要的公司事件）
    """
    try:
        market = _ds.get_market(company_name)
        search_query = f"{company_name} {stock_code}"
        if event_description:
            search_query += f" {event_description}"
        else:
            search_query += " 最新公告 新闻 2026年"
        events = _ds.search(search_query)
        financials = _ds.get_financials(company_name, years=3)

        events_text = json.dumps(events.get("items", [])[:10], ensure_ascii=False, indent=2)
        market_text = json.dumps(market, ensure_ascii=False, indent=2)
        fin_text = json.dumps(financials[-6:] if len(financials) > 6 else financials, ensure_ascii=False, indent=2)

        user_prompt = f"""请分析以下公司的近期事件。

公司：{company_name}
股票代码：{stock_code}
用户关注的事件：{event_description or '近期最重要的公司事件'}

=== 行情数据 ===
{market_text}

=== 近期事件 ===
{events_text}

=== 财务数据 ===
{fin_text}

请严格按照分析框架输出完整的Markdown报告。"""

        report = _ds.generate_report(STOCK_EVENT_ANALYSIS_PROMPT, user_prompt)
        filepath = _save_report(company_name, report)
        return f"{report}\n\n---\n📁 报告已保存至: {filepath}"
    except Exception as e:
        return f"分析失败: {e}"


async def analyze_earnings(
    company_name: str,
    stock_code: str,
    quarter: str = "latest",
) -> str:
    """分析上市公司季度财报。

    输出财报关键指标对比、beat/miss分析、业绩变动原因拆解。

    Args:
        company_name: 公司中文简称
        stock_code: 6位股票代码（如 "600036"）
        quarter: 财报季度 (latest/Q1/Q2/Q3/Q4)
    """
    try:
        market = _ds.get_market(company_name)
        financials = _ds.get_financials(company_name, years=3)
        events = _ds.search(f"{company_name} {stock_code} 业绩 财报 {quarter}")

        market_text = json.dumps(market, ensure_ascii=False, indent=2)
        fin_text = json.dumps(financials, ensure_ascii=False, indent=2)
        events_text = json.dumps(events.get("items", [])[:8], ensure_ascii=False, indent=2)

        user_prompt = f"""请分析以下公司{quarter}季度财报。

公司：{company_name} ({stock_code})
季度：{quarter}
当前日期：{now_str()}

=== 行情估值 ===
{market_text}

=== 历史财务趋势 ===
{fin_text}

=== 相关新闻/公告 ===
{events_text}

请输出完整的财报分析报告。"""

        return _ds.generate_report(EARNINGS_ANALYSIS_PROMPT, user_prompt)
    except Exception as e:
        return f"分析失败: {e}"


async def preview_earnings(company_name: str, stock_code: str) -> str:
    """构建业绩前瞻情景分析（乐观/基准/悲观三种情景）。

    Args:
        company_name: 公司中文简称
        stock_code: 6位股票代码（如 "600036"）
    """
    try:
        market = _ds.get_market(company_name)
        financials = _ds.get_financials(company_name, years=3)
        events = _ds.search(f"{company_name} {stock_code} 业绩前瞻 预期 展望")

        market_text = json.dumps(market, ensure_ascii=False, indent=2)
        fin_text = json.dumps(financials, ensure_ascii=False, indent=2)
        events_text = json.dumps(events.get("items", [])[:8], ensure_ascii=False, indent=2)

        prompt = """你是一个资深A股分析师。请构建该公司的业绩前瞻。
按乐观/基准/悲观三种情景分析，每种情景下估算关键财务指标的变化，
并给出概率权重。输出Markdown格式。"""

        user_prompt = f"""请为以下公司构建业绩前瞻情景分析。

公司：{company_name} ({stock_code})
当前日期：{now_str()}

=== 行情估值 ===
{market_text}

=== 历史财务趋势 ===
{fin_text}

=== 最新动态 ===
{events_text}

请输出完整的情景分析报告，包含三种情景的EPS预估和概率权重。"""

        return _ds.generate_report(prompt, user_prompt)
    except Exception as e:
        return f"分析失败: {e}"


async def sector_overview(sector_name: str) -> str:
    """生成行业板块概览报告。

    包含行业整体表现、龙头公司对比、近期政策与事件催化。

    Args:
        sector_name: 行业名称（如 "银行"、"新能源"、"医药生物"）
    """
    try:
        market = _ds.get_market(f"{sector_name}板块")
        events = _ds.search(f"{sector_name} 行业 政策 趋势 2026年5月")

        market_text = json.dumps(market, ensure_ascii=False, indent=2)
        events_text = json.dumps(events.get("items", [])[:10], ensure_ascii=False, indent=2)

        user_prompt = f"""请分析以下行业板块。

行业：{sector_name}
当前日期：{now_str()}

=== 板块指数数据 ===
{market_text}

=== 近期行业事件 ===
{events_text}

请输出完整的行业概览报告。"""

        return _ds.generate_report(SECTOR_OVERVIEW_PROMPT, user_prompt)
    except Exception as e:
        return f"分析失败: {e}"


async def catalyst_calendar(
    days_ahead: int = 14,
) -> str:
    """查询即将到来的催化剂事件日历。

    包含财报日期、股东会、分红除权日、行业会议等。

    Args:
        days_ahead: 向前查询天数（默认14天）
    """
    try:
        events = _ds.search(f"未来{days_ahead}天 A股 财报 股东会 分红 业绩预告 事件日历")

        events_text = json.dumps(events.get("items", [])[:15], ensure_ascii=False, indent=2)

        user_prompt = f"""请整理以下即将到来的A股市场催化剂事件。

时间范围：未来{days_ahead}天（从 {now_str()} 起）

=== 搜索到的即将到来的事件 ===
{events_text}

请按日期整理为催化剂日历，标注每项事件的影响级别（高/中/低）和影响标的。
输出Markdown格式的表格日历。"""

        return _ds.generate_report(CATALYST_PROMPT, user_prompt)
    except Exception as e:
        return f"分析失败: {e}"
