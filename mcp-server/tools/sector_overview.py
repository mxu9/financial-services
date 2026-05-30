"""sector_overview — 行业板块概览."""

import json
from datetime import datetime
from urllib.parse import quote
from tools.analysis import _ds, _extract_tables, _load_skill, _save_report, _REPORT_BASE, now_str


async def sector_overview(sector_name: str) -> str:
    """生成行业板块概览报告。

    包含行业整体表现、龙头公司对比、近期政策与事件催化。

    Args:
        sector_name: 行业名称（如 "银行"、"新能源"、"医药生物"）
    """
    try:
        now = datetime.now()

        # === A. 板块指数 (mx-data) ===
        index_raw = _ds.mx_data.query(
            f"{sector_name}板块 指数 涨跌幅 pe pb 成分股"
        )
        index_text = json.dumps(_extract_tables(index_raw), ensure_ascii=False, indent=2)

        # === B. 龙头公司估值 (mx-data) ===
        leaders_raw = _ds.mx_data.query(
            f"{sector_name} 龙头 市值 营收 净利润 pe pb roe 股息率"
        )
        leaders_text = json.dumps(_extract_tables(leaders_raw), ensure_ascii=False, indent=2)

        # === C. 行业趋势 (mx-search) ===
        events = _ds.search(
            f"{sector_name} 行业 政策 趋势 竞争格局 {now.year}年{now.month}月"
        )
        events_text = json.dumps(events.get("items", [])[:10], ensure_ascii=False, indent=2)

        user_prompt = f"""请分析以下行业板块。

行业：{sector_name}
当前日期：{now_str()}

=== 板块指数 ===
{index_text}

=== 龙头公司 ===
{leaders_text}

=== 近期行业事件 ===
{events_text}

请输出完整的行业概览报告。"""

        report = _ds.generate_report(_load_skill("sector-overview"), user_prompt)
        filename = _save_report(f"{sector_name}行业概览", report)
        return f"{report}\n\n---\n📥 报告下载: {_REPORT_BASE}/reports/{quote(filename, safe='._')}"
    except Exception as e:
        return f"分析失败: {e}"
