"""preview_earnings — 业绩前瞻情景分析."""

import json
from urllib.parse import quote
from tools.analysis import _ds, _extract_tables, _load_skill, _save_report, _REPORT_BASE, now_str


async def preview_earnings(company_name: str, stock_code: str) -> str:
    """构建业绩前瞻情景分析（乐观/基准/悲观三种情景）。

    Args:
        company_name: 公司中文简称
        stock_code: 6位股票代码（如 "600036"）
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

        # === C. 机构预测 + 前瞻 (mx-search) ===
        events = _ds.search(
            f"{company_name} {stock_code} 业绩前瞻 预期 展望 机构预测 EPS"
        )
        events_text = json.dumps(events.get("items", [])[:8], ensure_ascii=False, indent=2)

        user_prompt = f"""请为以下公司构建业绩前瞻情景分析。

公司：{company_name} ({stock_code})
当前日期：{now_str()}

=== 行情估值 ===
{market_text}

=== 历史财务趋势 ===
{fin_text}

=== 机构预测/最新动态 ===
{events_text}

请输出完整的情景分析报告，包含三种情景的EPS预估和概率权重。"""

        report = _ds.generate_report(_load_skill("earnings-preview"), user_prompt)
        filename = _save_report(f"{company_name}_业绩前瞻", report)
        return f"{report}\n\n---\n📥 报告下载: {_REPORT_BASE}/reports/{quote(filename, safe='._')}"
    except Exception as e:
        return f"分析失败: {e}"
