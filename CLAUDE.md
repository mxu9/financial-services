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