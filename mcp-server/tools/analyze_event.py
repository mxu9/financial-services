"""analyze_event — 上市公司事件三维联动分析."""

import json
from datetime import datetime
from urllib.parse import quote
from tools.analysis import _ds, _extract_tables, _load_skill, _save_report, _REPORT_BASE


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
        # === A. 行情 + 筹码面 (mx-data) ===
        market_raw = _ds.mx_data.query(
            f"{company_name} 最新价 总市值 pe pb 总股本 股息率"
            f" 大股东质押比例"
        )
        market_text = json.dumps(_extract_tables(market_raw), ensure_ascii=False, indent=2)

        # === B. 财务 + 基本面 (mx-data) ===
        fin_raw = _ds.mx_data.query(
            f"{company_name} 近三年 每股收益 净资产收益率 营收增长率"
            f" 净利润 毛利率 扣非净利润 经营现金流"
        )
        fin_text = json.dumps(_extract_tables(fin_raw), ensure_ascii=False, indent=2)

        # === C. 催化剂(解禁) (mx-data) ===
        catalyst_raw = _ds.mx_data.query(
            f"{company_name} 限售股解禁"
        )
        catalyst_text = json.dumps(_extract_tables(catalyst_raw), ensure_ascii=False, indent=2)

        # === D. 事件搜索 (mx-search) ===
        search_query = f"{company_name} {stock_code}"
        if event_description:
            search_query += f" {event_description}"
        else:
            search_query += f" 最新公告 新闻 {datetime.now().year}年"
        events = _ds.search(search_query)
        events_text = json.dumps(events.get("items", [])[:10], ensure_ascii=False, indent=2)

        user_prompt = f"""请分析以下公司的近期事件。

公司：{company_name}
股票代码：{stock_code}
用户关注的事件：{event_description or '近期最重要的公司事件'}

=== 行情 + 筹码面 ===
{market_text}

=== 财务基本面 ===
{fin_text}

=== 催化剂(解禁) ===
{catalyst_text}

=== 近期事件 ===
{events_text}

请严格按照分析框架输出完整的Markdown报告。"""

        report = _ds.generate_report(_load_skill("stock-event-analysis"), user_prompt)
        filename = _save_report(company_name, report)
        return f"{report}\n\n---\n📥 报告下载: {_REPORT_BASE}/reports/{quote(filename, safe='._')}"
    except Exception as e:
        return f"分析失败: {e}"
