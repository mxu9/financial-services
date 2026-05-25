"""数据查询类 MCP Tool (4个): 行情、财务、新闻搜索、选股."""

import json
import os
from shared.clients import DataSourceManager

_ds = DataSourceManager()


def register(ds_manager: DataSourceManager = None):
    """注册数据查询 Tool 到 FastMCP 实例。由 server.py 调用。"""
    global _ds
    if ds_manager:
        _ds = ds_manager


async def get_market_data(company_name: str) -> str:
    """获取A股上市公司实时行情与估值数据。

    返回：最新价、总市值、PE(TTM)、PB、总股本、股息率。
    数据来源：东方财富妙想（mx-data）。
    """
    try:
        row = _ds.get_market(company_name)
        if "error" in row:
            return json.dumps(row, ensure_ascii=False, indent=2)
        return json.dumps(row, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


async def get_financials(
    company_name: str,
    years: int = 3,
) -> str:
    """获取A股上市公司历史财务数据。

    返回指定年度的每股收益(EPS)、净资产收益率(ROE)、营收增长率、
    净利润等核心财务指标。数据来源：东方财富妙想（mx-data）。
    """
    try:
        rows = _ds.get_financials(company_name, years)
        return json.dumps(rows[-20:], ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


async def search_events(
    query: str,
    search_type: str = "all",
) -> str:
    """搜索A股上市公司公告、新闻、研报和政策信息。

    支持按公告(notice)、新闻(news)、研报(report)分类筛选。
    数据来源：东方财富妙想搜索（mx-search）。

    Args:
        query: 搜索关键词（公司名/股票代码/事件关键词）
        search_type: 资讯类型 (all/notice/news/report)，默认all
    """
    try:
        result = _ds.search(query)
        items = result.get("items", [])
        if search_type != "all":
            type_map = {"notice": "NOTICE", "news": "NEWS", "report": "REPORT"}
            filter_type = type_map.get(search_type, search_type.upper())
            items = [i for i in items if i.get("type") == filter_type]

        return json.dumps(
            {"total": len(items), "items": items},
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


async def screen_stocks(conditions: str) -> str:
    """根据选股条件筛选A股股票。

    支持按行情指标（PE、PB、市值）、财务指标（ROE、毛利率）等条件筛选。
    数据来源：东方财富妙想-选股（mx-xuangu）。

    Args:
        conditions: 自然语言描述的选股条件（如 "PE<15且ROE>15%的银行股"）
    """
    try:
        result = _ds.mx_data.query(f"{conditions}")
        dto_list = (
            result.get("data", {})
            .get("data", {})
            .get("searchDataResultDTO", {})
            .get("dataTableDTOList", [])
        )
        if not dto_list:
            return json.dumps({"error": "未找到符合条件的股票"}, ensure_ascii=False)

        stocks = []
        for dto in dto_list[:20]:
            stocks.append(
                {
                    "code": dto.get("code", ""),
                    "name": dto.get("entityName", ""),
                    "title": dto.get("title", ""),
                }
            )
        return json.dumps({"total": len(stocks), "stocks": stocks}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
