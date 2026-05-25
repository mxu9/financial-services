#!/usr/bin/env python3
"""financial-services MCP Server — 金融数据查询与分析服务.

提供 14 个 MCP Tool，覆盖：
- 数据查询 (4): 行情、财务、新闻搜索、选股
- 分析报告 (5): 事件分析、财报分析、业绩前瞻、行业概览、催化剂日历
- 估值数据 (5): DCF、DDM、Comps、LBO、三表数据

启动方式:
    python server.py                              # stdio 模式 (默认)
    python server.py --sse                        # SSE 模式 (仅本机)
    python server.py --sse --host 0.0.0.0         # SSE 模式 (允许远程连接)
    python server.py --sse --host 0.0.0.0 --port 8765
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

# host 参数决定了 DNS rebinding 保护策略：
# - 127.0.0.1 (默认) → 启用保护，仅允许本机连接
# - 0.0.0.0 → 禁用保护，允许任何主机连接
_host = "127.0.0.1"
for i, arg in enumerate(sys.argv):
    if arg == "--host" and i + 1 < len(sys.argv):
        _host = sys.argv[i + 1]

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("financial-services", host=_host)

# ---- 注册数据查询 Tool (4个) ----
from tools.data_query import get_market_data, get_financials, search_events, screen_stocks

mcp.tool()(get_market_data)
mcp.tool()(get_financials)
mcp.tool()(search_events)
mcp.tool()(screen_stocks)

# ---- 注册估值数据 Tool (5个) ----
from tools.valuation import (
    get_dcf_data,
    get_ddm_data,
    get_comps_data,
    get_lbo_data,
    get_3statement_data,
)

mcp.tool()(get_dcf_data)
mcp.tool()(get_ddm_data)
mcp.tool()(get_comps_data)
mcp.tool()(get_lbo_data)
mcp.tool()(get_3statement_data)

# ---- 注册分析报告 Tool (5个) ----
from tools.analysis import (
    analyze_event,
    analyze_earnings,
    preview_earnings,
    sector_overview,
    catalyst_calendar,
)

mcp.tool()(analyze_event)
mcp.tool()(analyze_earnings)
mcp.tool()(preview_earnings)
mcp.tool()(sector_overview)
mcp.tool()(catalyst_calendar)


def _get_reports_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports")


def _register_report_routes(app):
    """在 Starlette app 上注册报告下载路由."""
    import json
    import mimetypes
    from starlette.responses import FileResponse, JSONResponse
    from starlette.routing import Route

    async def list_reports(request):
        reports_dir = _get_reports_dir()
        if not os.path.isdir(reports_dir):
            return JSONResponse({"reports": [], "total": 0})

        files = sorted(
            [f for f in os.listdir(reports_dir) if f.endswith(".md")],
            reverse=True,
        )
        report_list = []
        for f in files:
            path = os.path.join(reports_dir, f)
            size = os.path.getsize(path)
            report_list.append(
                {"filename": f, "size": size, "url": f"/reports/{f}"}
            )

        return JSONResponse({"reports": report_list, "total": len(report_list)})

    async def download_report(request):
        filename = request.path_params["filename"]
        # 路径穿越保护
        if ".." in filename or "/" in filename or "\\" in filename:
            return JSONResponse({"error": "Invalid filename"}, status_code=400)

        filepath = os.path.join(_get_reports_dir(), filename)
        if not os.path.isfile(filepath):
            return JSONResponse({"error": "Report not found"}, status_code=404)

        return FileResponse(filepath, media_type="text/markdown; charset=utf-8")

    app.routes.insert(0, Route("/reports", list_reports, methods=["GET"]))
    app.routes.insert(1, Route("/reports/{filename}", download_report, methods=["GET"]))


def main():
    args = sys.argv[1:]
    transport = "sse" if "--sse" in args else "stdio"
    host = "127.0.0.1"
    port = 8000

    for i, arg in enumerate(args):
        if arg == "--host" and i + 1 < len(args):
            host = args[i + 1]
        elif arg == "--port" and i + 1 < len(args):
            port = int(args[i + 1])

    print(f"financial-services MCP Server starting (transport={transport})", file=sys.stderr)

    if transport == "sse":
        import uvicorn
        from starlette.middleware.trustedhost import TrustedHostMiddleware

        app = mcp.sse_app()
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
        _register_report_routes(app)
        print(f"SSE endpoint:    http://{host}:{port}/sse", file=sys.stderr)
        print(f"Reports list:    http://{host}:{port}/reports", file=sys.stderr)
        print(f"Reports download: http://{host}:{port}/reports/{{filename}}", file=sys.stderr)
        uvicorn.run(app, host=host, port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
