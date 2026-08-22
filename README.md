# TCM-Agent

TCM-Agent 是一个面向中医药知识检索、辨证分析和用药安全提示的 AI Agent。项目由 TypeScript Agent 运行时、领域规则与技能、Python MCP 数据引擎，以及 Vue 诊疗工作台组成。

> 当前处于工程化完善阶段，可用于学习、研究和辅助分析，不可替代执业医师诊断、处方或急救处置。

## 当前状态

当前已完成 WebSocket v1 协议、会话边界、取消回合、`tcm-consultation` 工具隔离、领域 Schema、处方安全门和 MCP 结构化证据包装。MCP 结果保留原始 Markdown，同时附带版本号、来源哈希、数据集版本和证据 ID。

生产 Chroma 索引正在迁移到带来源追溯元数据的格式，旧索引不会在验证前被覆盖。RAG 基线使用测试专用 TF-IDF `LiteVectorStore`，不代表生产 BGE/Chroma 指标。

## 核心能力

- 中药、方剂、证候、穴位和医案的结构化检索。
- 基于症状、舌象与脉象的辨证候选分析。
- 十八反、十九畏及常见高风险用药组合提示。
- MCP 工具调用、会话恢复、上下文压缩、权限确认和技能加载。
- SQLite + ChromaDB 混合检索、行级来源证据和面向浏览器的流式对话界面。

## 架构

```text
Vue Web ──WebSocket── FastAPI Gateway ──JSON mode── TCM-Agent
                                                    │
                                                    ├─ 领域规则与技能
                                                    └─ MCP ── Python 数据/RAG 引擎
```

- `src/`：Agent Loop、模型适配、会话、权限、上下文和 MCP 客户端。
- `.tcm-agent/`、`TCM-AGENT.md`：中医领域规则、技能和行为边界。
- `tcm-mcp-server/`：结构化数据库、RAG、MCP 工具和 Web 网关。
- `web/`：Vue 3 + TypeScript 工作台。
- `test/`、`tcm-mcp-server/tests/`：运行时和数据引擎测试。

详细设计见 [ARCHITECTURE.md](./ARCHITECTURE.md)，完整命令见 [USAGE.md](./USAGE.md)。

## 快速开始

环境要求：Node.js 20.19+（或 22.12+）、Python 3.10+、npm。

```powershell
# Agent 运行时
npm ci
npm run check
npm test

# Python 数据引擎
cd tcm-mcp-server
python -m pip install -e ".[dev]"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest tests -q
```

Python 测试若遇到仓库临时目录权限问题，可使用独立临时目录：

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$tmp = Join-Path $env:TEMP ('tcm-agent-pytest-' + $PID)
python -m pytest tests\web tests\unit tests\ingestion tests\rag -q -o addopts='' --basetemp=$tmp
```

在 `~/.tcm-agent/settings.json` 配置模型：

```json
{
  "model": "your-model",
  "temperature": 0.2,
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
    "ANTHROPIC_API_KEY": "use-an-environment-variable-when-possible"
  }
}
```

然后从仓库根目录启动：

```powershell
npm run dev
```

也可运行 `npm run install-local` 安装 `tcm-agent` 启动命令。项目级 MCP 配置位于 `.mcp.json`。

咨询模式只加载咨询所需工具，可直接启动 JSON 网关：

```powershell
npm run dev -- --json-mode --tool-profile tcm-consultation
```

## 数据与配置

运行时数据路径由以下环境变量控制；未设置时使用 `tcm-mcp-server/data` 和仓库外层的 `DB`：

| 环境变量 | 用途 |
|---|---|
| `TCM_AGENT_DATA_DIR` | SQLite、Chroma、review queue 和导入摘要目录 |
| `TCM_AGENT_SOURCE_DATA_DIR` | 原始资料目录 |
| `TCM_AGENT_ALLOWED_ORIGINS` | WebSocket/CORS 来源白名单，禁止使用 `*` |
| `TCM_AGENT_DATASET_VERSION` | MCP 证据包中的数据集版本标记 |

MCP 数据引擎配置见 [.mcp.json](./.mcp.json)。

## Web 工作台

```powershell
# 终端 1：网关
cd tcm-mcp-server
python -m uvicorn tcm_mcp_server.web.main:app --app-dir src --reload

# 终端 2：前端
cd web
npm install
npm run dev
```

网关默认只允许 `http://localhost:5173` 和 `http://127.0.0.1:5173`，生产环境应显式设置 `TCM_AGENT_ALLOWED_ORIGINS`。

## RAG 评测与索引迁移

测试基线当前为：证型 15/15 命中、Recall@5=1.0000、MRR=0.9667；方剂 15/15 命中、Recall@5=1.0000、MRR=1.0000。该结果来自测试专用 TF-IDF 索引，不能直接外推到生产向量模型。

生产索引重建使用：

```powershell
cd tcm-mcp-server
$env:PYTHONPATH='src'
$env:TCM_AGENT_CHROMA_STAGE='data/chroma-v2-20260813-c'
python scripts\rebuild_chroma_v2.py
```

完成后应检查 staging 目录中的 `BUILD_COMPLETE.json`，确认四个集合数量和来源元数据，再进行索引切换。不要把未完成或失败的 staging 目录配置为生产 Chroma 路径。

## 验证

```powershell
npm run check
npm test
cd web
npm run build
```

Python 测试默认使用 `tcm-mcp-server/tmp/pytest`。若该目录被其他进程锁定，可通过 `--basetemp` 指向一个新的临时目录。

## 安全边界

- 输出只用于学习、研究和辅助决策，不构成医疗建议。
- 涉及孕产妇、儿童、老年人、肝肾功能异常、急症或高毒性药物时，必须提示线下就医或药师复核。
- 模型输出和检索结果均可能不完整；处方剂量、炮制、配伍和疗程必须由专业人员确认。

## 许可

见 [LICENSE](./LICENSE)。
