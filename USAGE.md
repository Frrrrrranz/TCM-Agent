# TCM-Agent 使用指南

## 配置

用户配置目录默认为 `~/.tcm-agent/`，可通过 `TCM_AGENT_HOME` 修改。主配置文件为 `settings.json`：

```json
{
  "model": "your-model",
  "maxOutputTokens": 4096,
  "temperature": 0.2,
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
    "ANTHROPIC_API_KEY": "your-key"
  }
}
```

支持的运行时环境变量包括：

- `TCM_AGENT_HOME`：用户数据目录。
- `TCM_AGENT_MODEL`：覆盖模型名称。
- `TCM_AGENT_MODEL_MODE=mock`：离线测试模型。
- `TCM_AGENT_MAX_OUTPUT_TOKENS`：最大输出 token。
- `TCM_AGENT_TEMPERATURE` 或 `TCM_TEMPERATURE`：采样温度。
- `TCM_AGENT_MAX_RETRIES`：模型请求重试次数。
- `TCM_AGENT_BIN_DIR`：本地安装脚本的命令目录。

配置敏感凭据时优先使用进程环境变量，不要提交到 Git。

## 启动

```powershell
npm run dev
```

安装本地命令后可使用：

```powershell
tcm-agent
tcm-agent --resume
tcm-agent --resume <session-id>
tcm-agent --fork <session-id>
```

`--json-mode` 用于 FastAPI 网关等进程集成，不面向交互式用户。

## 交互命令

常用斜杠命令：

- `/help`：显示命令帮助。
- `/model <name>`：保存模型覆盖。
- `/config-paths`：显示配置路径。
- `/mcp`：显示 MCP 服务。
- `/skills`：显示已加载技能。
- `/memory`：显示已加载指令文件。
- `/permissions`：显示权限存储路径。
- `/init`：为当前项目创建 `.tcm-agent/` 和 `TCM-AGENT.md`。
- `/exit`：退出。

## MCP 管理

```powershell
tcm-agent mcp list
tcm-agent mcp add <name> -- <command> [args...]
tcm-agent mcp remove <name>
tcm-agent mcp login <name> --token <bearer-token>
tcm-agent mcp logout <name>
```

增加 `--project` 会操作当前目录的 `.mcp.json`；否则操作 `~/.tcm-agent/mcp.json`。项目已经内置 `tcm-data-engine` 配置。

## 技能管理

```powershell
tcm-agent skills list
tcm-agent skills add <path> --name <name> --project
tcm-agent skills remove <name> --project
```

项目技能位于 `.tcm-agent/skills/<name>/SKILL.md`，用户技能位于 `~/.tcm-agent/skills/<name>/SKILL.md`。

## 会话和上下文

会话按工作目录写入 `~/.tcm-agent/projects/`。长会话会进行上下文压缩；超大工具结果会保存到 `~/.tcm-agent/tool-results/`，提示词只保留预览和文件位置。

指令加载顺序是用户全局、项目祖先目录、当前目录。TCM-Agent 原生读取 `TCM-AGENT.md`、`TCM-AGENT.local.md`、`.tcm-agent/TCM-AGENT.md` 和 `.tcm-agent/rules/*.md`，同时保留 Claude 指令目录兼容。

## Web 模式

```powershell
cd tcm-mcp-server
python -m uvicorn tcm_mcp_server.web.main:app --app-dir src --reload
```

另开终端：

```powershell
cd web
npm run dev
```

默认开发地址由 Vite 和 Uvicorn 输出决定。部署前必须配置明确的 CORS 来源、鉴权、TLS 和反向代理限制。

## 故障排查

- 模型未配置：检查 `~/.tcm-agent/settings.json` 和 API 环境变量。
- MCP 未连接：运行 `/mcp`，确认 Python 依赖、`.mcp.json` 的 `cwd` 和 `PYTHONPATH`。
- 会话无法恢复：确认启动目录与原会话目录相同。
- Python 测试临时目录被锁：传入新的 `--basetemp`。
