"""统一数据源客户端封装：mx-data, mx-search, tushare, Anthropic."""

import os
import sys

SKILLS_DIR = os.path.expanduser(r"~\.claude\skills")
sys.path.insert(0, os.path.join(SKILLS_DIR, "mx-data"))
sys.path.insert(0, os.path.join(SKILLS_DIR, "mx-search"))

from mx_data import MXData
from mx_search import MXSearch


def _stock_code_to_ts_code(code: str) -> str:
    """6位纯数字 → tushare格式 (600036 → 600036.SH, 000792 → 000792.SZ)"""
    code = code.strip()
    if "." in code:
        return code
    if code.startswith(("6", "9")):
        return f"{code}.SH"
    elif code.startswith(("0", "3")):
        return f"{code}.SZ"
    elif code.startswith(("8", "4")):
        return f"{code}.BJ"
    return code


class DataSourceManager:
    """统一管理 mx-data、mx-search、tushare、Anthropic 四个外部服务."""

    def __init__(self):
        api_key = os.getenv("MX_APIKEY")
        if not api_key:
            raise ValueError("MX_APIKEY 环境变量未设置")

        self.mx_data = MXData(api_key=api_key)
        self.mx_search = MXSearch(api_key=api_key)
        self._tushare = None
        self._anthropic = None

    @property
    def tushare(self):
        if self._tushare is None:
            import tushare as ts
            token = os.getenv("TUSHARE_TOKEN", "")
            self._tushare = ts.pro_api(token) if token else None
        return self._tushare

    @property
    def anthropic(self):
        if self._anthropic is None:
            from anthropic import Anthropic
            # 兼容两种常见的 API Key 环境变量名
            api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN") or ""
            base_url = os.getenv("ANTHROPIC_BASE_URL", None)
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            self._anthropic = Anthropic(**kwargs) if api_key else None
        return self._anthropic

    # ---- 数据查询 ----

    def get_market(self, name: str) -> dict:
        """获取实时行情."""
        result = self.mx_data.query(f"{name} 最新价 总市值 pe pb 总股本 股息率")
        dto_list = (
            result.get("data", {})
            .get("data", {})
            .get("searchDataResultDTO", {})
            .get("dataTableDTOList", [])
        )
        if not dto_list:
            return {"error": "未找到行情数据"}

        dto = dto_list[0]
        table = dto.get("table", {})
        name_map = dto.get("nameMap", {})
        indicator_order = dto.get("indicatorOrder", [])

        if not table or not indicator_order:
            return {"error": "行情数据结构为空"}

        row = {}
        for key in indicator_order:
            label = name_map.get(key, key)
            values = table.get(key, [])
            row[label] = values[0] if values else None

        row["数据日期"] = table.get("headName", [None])[0] if table.get("headName") else None
        return row

    def get_financials(self, name: str, years: int = 3) -> list[dict]:
        """获取历史财务数据."""
        result = self.mx_data.query(
            f"{name} 近{years}年 每股收益 净资产收益率 营收增长率 净利润"
        )
        dto_list = (
            result.get("data", {})
            .get("data", {})
            .get("searchDataResultDTO", {})
            .get("dataTableDTOList", [])
        )
        if not dto_list:
            return [{"error": "未找到财务数据"}]

        rows = []
        for dto in dto_list:
            table = dto.get("table", {})
            name_map = dto.get("nameMap", {})
            indicator_order = dto.get("indicatorOrder", [])
            head_name = table.get("headName", [])

            for i, date in enumerate(head_name):
                row = {"date": date}
                for key in indicator_order:
                    label = name_map.get(key, key)
                    values = table.get(key, [])
                    if i < len(values):
                        row[label] = values[i]
                rows.append(row)
        return rows

    def search(self, query: str) -> dict:
        """搜索新闻/公告/研报."""
        result = self.mx_search.search(query)
        items = (
            result.get("data", {})
            .get("data", {})
            .get("llmSearchResponse", {})
            .get("data", [])
        )
        return {
            "total": len(items),
            "items": [
                {
                    "title": item.get("title", ""),
                    "date": item.get("date", ""),
                    "type": item.get("informationType", ""),
                    "source": item.get("insName", ""),
                    "summary": (item.get("content", "") or "")[:300],
                }
                for item in items
            ],
        }

    def generate_report(self, system_prompt: str, user_prompt: str) -> str:
        """调用 Anthropic API 生成分析报告."""
        if not self.anthropic:
            return "[错误] ANTHROPIC_API_KEY 未设置，无法生成分析报告"

        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        response = self.anthropic.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    # ---- 股票代码工具 ----

    @staticmethod
    def to_ts_code(code: str) -> str:
        return _stock_code_to_ts_code(code)
