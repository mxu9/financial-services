#!/usr/bin/env python3
"""独立的报告文件服务器，将 reports/ 目录以 HTTP 方式提供下载。

启动方式:
    python serve_reports.py                  # 默认端口 8001
    python serve_reports.py --port 8080      # 指定端口

配合 cloudflared 公共主机名（如 mcp.snaxum.com → localhost:8001），
即可通过公网下载分析报告。
"""

import sys
import os
import http.server
from functools import partial

PORT = 8001
if "--port" in sys.argv:
    idx = sys.argv.index("--port")
    PORT = int(sys.argv[idx + 1])

_DIR = os.path.dirname(os.path.abspath(__file__))

# .md 文件以 UTF-8 编码返回，避免中文乱码
http.server.SimpleHTTPRequestHandler.extensions_map[".md"] = (
    "text/markdown; charset=utf-8"
)

handler = partial(http.server.SimpleHTTPRequestHandler, directory=_DIR)
print(f"Reports server: http://127.0.0.1:{PORT}/reports/")
http.server.ThreadingHTTPServer(("", PORT), handler).serve_forever()
