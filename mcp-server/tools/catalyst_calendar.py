"""catalyst_calendar — 催化剂事件日历."""

import json
from urllib.parse import quote
from tools.analysis import _ds, _load_skill, _save_report, _REPORT_BASE, now_str


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

        report = _ds.generate_report(_load_skill("catalyst-calendar"), user_prompt)
        filename = _save_report("催化剂日历", report)
        return f"{report}\n\n---\n📥 报告下载: {_REPORT_BASE}/reports/{quote(filename, safe='._')}"
    except Exception as e:
        return f"分析失败: {e}"
