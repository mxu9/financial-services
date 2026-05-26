"""输出格式化工具."""

from datetime import datetime


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def date_to_short(date_str: str) -> str:
    """2026-05-25 → 260525 (示例)"""
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return d.strftime("%y%m%d")
    except (ValueError, IndexError):
        return datetime.now().strftime("%y%m%d")


def format_market_row(row: dict) -> str:
    """行情数据格式化为 Markdown 表格行."""
    lines = ["| 指标 | 数值 |", "|------|------|"]
    for k, v in row.items():
        lines.append(f"| {k} | {v} |")
    return "\n".join(lines)


def format_event_list(items: list) -> str:
    """事件列表格式化为 Markdown."""
    lines = []
    for i, item in enumerate(items[:10], 1):
        type_tag = {"REPORT": "研报", "NEWS": "新闻", "NOTICE": "公告"}.get(
            item.get("type", ""), item.get("type", "")
        )
        lines.append(
            f"{i}. [{type_tag}] {item['title']} ({item['date'][:10] if item.get('date') else 'N/A'})"
        )
    return "\n".join(lines) if lines else "未找到相关事件"
