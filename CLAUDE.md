# 金融服务插件

面向金融服务的 Cowork 插件和 Claude 托管代理模板。每个命名代理从单一来源以两种方式发布。

## 仓库结构

```
├── plugins/
│   ├── agent-plugins/               #   命名代理 — 每个代理一个独立插件
│   │   └── <slug>/
│   │       ├── .claude-plugin/plugin.json
│   │       ├── agents/<slug>.md     #   ← 规范系统提示词（单一来源，双重包装）
│   │       └── skills/              #   ← 打包副本，从 vertical-plugins/ 同步
│   ├── vertical-plugins/            #   FSI 垂直领域 — 技能源、命令、MCP
│   │   └── <vertical>/
│   │       ├── .claude-plugin/plugin.json
│   │       ├── commands/
│   │       ├── skills/
│   │       └── .mcp.json
│   └── partner-built/               #   合作伙伴插件（LSEG、S&P Global）
├── managed-agent-cookbooks/         #   CMA 配方（每个命名代理一个目录）
│   └── <slug>/
│       ├── agent.yaml               #   system + skills → ../../plugins/agent-plugins/<slug>/...
│       ├── subagents/*.yaml         #   深度-1 叶子工作器
│       ├── steering-examples.json
│       └── README.md                #   安全层级 + 交接说明
├── claude-for-msft-365-install/     #   Microsoft 365 加载项的管理工具（独立于 FSI 插件）
└── scripts/                         #   deploy-managed-agent.sh, check.py, validate.py, orchestrate.py, sync-agent-skills.py
```

提交前运行 `python3 scripts/check.py` — 它会检查所有清单文件，验证 `system.file` / `skills.path` / `callable_agents.manifest` 引用是否正确解析，并在 `agent-plugins/<slug>/skills/` 中的副本与 `vertical-plugins/` 源文件发生漂移时报错。**在 `vertical-plugins/` 中编辑技能**，然后运行 `python3 scripts/sync-agent-skills.py` 将更改传播到代理包中。

## 关键文件

- `marketplace.json`: 市场清单 — 注册所有插件及其源路径
- `plugin.json`: 插件元数据 — 名称、描述、版本和组件发现设置
- `commands/*.md`: 斜杠命令，通过 `/plugin:command-name` 语法调用
- `skills/*/SKILL.md`: 特定任务的详细知识和工作流程
- `*.local.md`: 用户特定配置（已加入 gitignore）
- `mcp-categories.json`: 跨插件共享的规范 MCP 类别定义

## 开发工作流

1. 直接编辑 markdown 文件 — 更改立即生效
2. 使用 `/plugin:command-name` 语法测试命令
3. 当触发条件匹配时，技能会自动调用

## MCP Server

`mcp-server/` 是一个基于 FastMCP 的 MCP 服务器，将项目的金融数据查询和分析能力暴露为标准的 MCP Tool，供任何 MCP 客户端（Claude Desktop、Cursor、VS Code、自定义 Agent）调用。

### 目录结构

```
mcp-server/
├── server.py                 # FastMCP 主入口，注册 14 个 Tool，stdio/SSE 双模式
├── requirements.txt          # Python 依赖
├── .mcp.json                 # MCP 配置（Claude Code 加载用）
├── shared/
│   ├── clients.py            # DataSourceManager：统一封装 mx-data/mx-search/tushare/Anthropic
│   └── formatters.py         # 输出格式化工具
└── tools/
    ├── data_query.py         # 数据查询 (4): get_market_data, get_financials, search_events, screen_stocks
    ├── analysis.py           # 分析报告 (5): analyze_event, analyze_earnings, preview_earnings, sector_overview, catalyst_calendar
    └── valuation.py          # 估值数据 (5): get_dcf_data, get_ddm_data, get_comps_data, get_lbo_data, get_3statement_data
```

### 启动方式

```bash
# stdio 模式（本地单进程）
python mcp-server/server.py

# SSE 模式（仅本机）
python mcp-server/server.py --sse

# SSE 模式（允许远程连接）
python mcp-server/server.py --sse --host 0.0.0.0 --port 8000
```

### SSE 模式 HTTP 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/sse` | GET | MCP SSE 连接端点 |
| `/messages/` | POST | MCP JSON-RPC 消息端点（需 session_id） |

### 验证 MCP Server 是否工作

启动 SSE 模式后，用 curl 测试：

```bash
# 测试 SSE 端点（应返回 session endpoint）
curl -N --max-time 3 http://localhost:8000/sse
# 预期输出: event: endpoint
#           data: /messages/?session_id=xxx
```

连接成功即表示服务正常运行。进一步测试 Tool 调用：

```bash
# 获取 session_id
SESSION=$(curl -s -N --max-time 3 http://localhost:8000/sse 2>&1 | grep "data:" | head -1 | sed 's/data: //')

# 列出所有 Tool（应返回 14 个工具）
curl -s -X POST "$SESSION" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### Docker 连接 MCP Server

本地 Docker 容器无法通过 `127.0.0.1` 访问宿主机。在 Dify 等工具中连接时：

**宿主机启动方式**（必须以 `--host 0.0.0.0` 启动）：

```bash
python mcp-server/server.py --sse --host 0.0.0.0 --port 8000
```

**Dify MCP 配置 URL**（二选一）：

| 方式 | URL | 适用场景 |
|------|-----|---------|
| Docker Desktop 内置域名 | `http://host.docker.internal:8000/sse` | Windows/Mac Docker Desktop |
| 宿主机局域网 IP | `http://192.168.x.x:8000/sse` | 任何 Docker 环境 |

**Windows 防火墙放行**（仅局域网 IP 方式需要）：

```powershell
netsh advfirewall firewall add rule name="MCP Server" dir=in action=allow protocol=tcp localport=8000
```

### 环境变量

| 变量 | 必需 | 说明 |
|------|------|------|
| `MX_APIKEY` | 是 | 东方财富妙想 API Key |
| `ANTHROPIC_API_KEY` 或 `ANTHROPIC_AUTH_TOKEN` | 是* | 生成分析报告时需 LLM API Key |
| `ANTHROPIC_BASE_URL` | 否 | 自定义 API 端点（如 DeepSeek 代理） |
| `ANTHROPIC_MODEL` | 否 | 报告生成模型（默认 `claude-sonnet-4-6`） |
| `TUSHARE_TOKEN` | 否 | Tushare Pro token，补充详细财务数据 |

*仅在调用分析报告类 Tool（analyze_event 等）时需要。数据查询类 Tool 不需要。

## 内网穿透

将本地 Dify / MCP Server 暴露到公网，供外部访问。

### ngrok

在本地服务和公网之间建立加密隧道，外网通过 `https://xxx.ngrok-free.app` 访问 `localhost:80`。

```bash
# 1. 注册获取 token
#    https://dashboard.ngrok.com/signup → 复制 Authtoken

# 2. 安装配置
winget install ngrok
ngrok config add-authtoken <你的token>

# 3. 启动
ngrok http 80 --url=<固定域名>.ngrok-free.app
```

启动后访问 `https://<固定域名>.ngrok-free.app/chatbot/xxx` 即可。

⚠️ 免费版有浏览器警告页，无法在 iframe 中去掉。1 GB/月带宽。

### Cloudflare Dashboard 公网路由（推荐）

通过 Cloudflare 公共主机名，将本地多个服务映射到不同子域名。

**完整流程**：

1. 打开 Cloudflare Dashboard → **Zero Trust** → **Networks** → **Tunnels**
2. 点击 **"创建隧道"** 按钮，按向导完成创建
3. 进入该隧道，在概览页面根据提示的"安装 cloudflared 连接器"步骤，下载并安装 cloudflared
4. 安装完成后，Windows 服务中会自动注册 **"cloudflared agent"** 服务，该服务与 Cloudflare 网络建立连接以实现高可用性
5. 如需停止 tunnel，关闭该 Windows 服务即可

**前提**：
- 已申请公共域名（如 `snaxum.com`），并托管在 Cloudflare

添加公共主机名，例如：

| Subdomain | Domain | Type | URL |
|-----------|--------|------|-----|
| `www` | `snaxum.com` | HTTP | `localhost:80` |
| `reports` | `snaxum.com` | HTTP | `localhost:8001` |

保存后，`www.snaxum.com` 指向本地的 Dify(80)，`reports.snaxum.com` 指向本地报告下载服务(8001)。

### cloudflared Quick Tunnel

```bash
winget install --id Cloudflare.cloudflared
cloudflared tunnel --url http://localhost:80
```

✅ 无需注册、无警告页、无限带宽、一条命令即可。

### 对比

| | ngrok | cloudflared Dashboard | cloudflared Quick |
|------|------|------|------|
| 注册 | 需要 | 需要（首次安装） | 不需要 |
| 域名 | 自带子域名 | 自有域名（需配置 DNS） | 临时随机域名 |
| 警告页 | ❌ 免费版有 | ✅ 无 | ✅ 无 |
| 带宽 | 1 GB/月 | 无限 | 无限 |
| 固定域名 | 免费 1 个 | ✅ 支持多子域名 | ❌ 不支持 |
| 多服务 | ❌ | ✅ 单隧道映射多端口 | ❌ |
| 适合 | 临时测试 | 长期部署 | 临时分享 |


## 报告下载服务

分析报告通过独立的 HTTP 服务器对外提供下载，与 MCP Server 分离部署。

### 启动

```bash
python serve_reports.py
```

默认监听 8001 端口，将 `reports/` 目录以静态文件形式提供服务。

`.md` 文件会以 UTF-8 编码返回，保证中文正常显示。

### 配置

在 `mcp-server/.env` 中设置报告下载的基础 URL：

```
REPORT_BASE_URL=https://reports.snaxum.com
```

MCP Server 的分析 Tool 会在报告末尾生成完整下载链接：

```
📥 报告下载: https://reports.snaxum.com/reports/xxx.md
```

### 与 Cloudflare 配合

在 Cloudflare Dashboard 添加公共主机名 `reports.snaxum.com → localhost:8001`，即可公网下载。