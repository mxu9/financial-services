"""analyze_earnings — 季度财报分析."""

import json
from urllib.parse import quote
from tools.analysis import _ds, _extract_tables, _load_skill, _save_report, _REPORT_BASE, now_str


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
        # === A. 行情 (mx-data) ===
        market_raw = _ds.mx_data.query(
            f"{company_name} 最新价 总市值 pe pb 总股本 股息率"
        )
        market_text = json.dumps(_extract_tables(market_raw), ensure_ascii=False, indent=2)

        # === B. 财务基本面 (mx-data) ===
        fin_raw = _ds.mx_data.query(
            f"{company_name} 近三年 每股收益 净资产收益率 营收增长率"
            f" 净利润 毛利率 扣非净利润 经营现金流"
        )
        fin_text = json.dumps(_extract_tables(fin_raw), ensure_ascii=False, indent=2)

        # === C. 业绩新闻 + 机构预测 (mx-search) ===
        events = _ds.search(
            f"{company_name} {stock_code} 业绩 财报 {quarter} 机构预测 评级"
        )
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

        report = _ds.generate_report(_load_skill("earnings-analysis"), user_prompt)
        filename = _save_report(f"{company_name}_财报", report)
        return f"{report}\n\n---\n📥 报告下载: {_REPORT_BASE}/reports/{quote(filename, safe='._')}"
    except Exception as e:
        return f"分析失败: {e}"
