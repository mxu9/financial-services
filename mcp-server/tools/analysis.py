"""分析报告类 MCP Tool (5个): 事件分析、财报分析、业绩前瞻、行业概览、催化剂日历."""

import json
import os
from datetime import datetime
from shared.clients import DataSourceManager
from shared.formatters import now_str, date_to_short

_ds = DataSourceManager()

_SKILL_DIR = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "plugins", "vertical-plugins", "equity-research", "skills",
)


def _load_skill(skill_name: str) -> str:
    """读取 SKILL.md 并去除 YAML frontmatter，作为 LLM system prompt。

    MCP Tool 的分析框架与 Claude Code Skill 共享同一来源（SKILL.md），
    确保两者输出质量和格式保持一致。
    """
    path = os.path.join(_SKILL_DIR, skill_name, "SKILL.md")
    if not os.path.isfile(path):
        return "你是一个资深A股分析师。请基于提供的数据进行分析，输出Markdown报告。"

    with open(path, encoding="utf-8") as f:
        content = f.read()

    # 去除 YAML frontmatter (---...---)
    if content.startswith("---"):
        parts = content.split("---", 2)
        content = parts[2] if len(parts) > 2 else content

    return content.strip()


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
            search_query += f" 最新公告 新闻 {datetime.now().year}年"
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

        report = _ds.generate_report(_load_skill("stock-event-analysis"), user_prompt)
        _save_report(company_name, report)
        return report
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

        return _ds.generate_report(_load_skill("earnings-analysis"), user_prompt)
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

        return _ds.generate_report(_load_skill("earnings-preview"), user_prompt)
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
        now = datetime.now()
        events = _ds.search(
            f"{sector_name} 行业 政策 趋势 {now.year}年{now.month}月"
        )

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

        return _ds.generate_report(_load_skill("sector-overview"), user_prompt)
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

        return _ds.generate_report(_load_skill("catalyst-calendar"), user_prompt)
    except Exception as e:
        return f"分析失败: {e}"
