# 🏥 TCM-Agent — 中医药全链路智能问答系统

<p align="center">
  <img src="./docs/logo.svg" alt="TCM-Agent Logo" width="180" />
</p>

<p align="center">
  <strong>基于 MiniCode 框架的中医药领域智能体</strong>
  <br />
  融合中医经典理论、结构化知识库与 RAG 语义检索的辅助决策引擎
</p>

<p align="center">
  <img src="https://img.shields.io/badge/状态-MVP%20工程化-4CAF50?style=for-the-badge" alt="状态: MVP 工程化" />
  <img src="https://img.shields.io/badge/框架-MiniCode-D97757?style=for-the-badge" alt="框架: MiniCode" />
  <img src="https://img.shields.io/badge/数据引擎-Python%20MCP-3776AB?style=for-the-badge" alt="数据引擎: Python MCP" />
  <img src="https://img.shields.io/badge/测试-48%20passed-4CAF50?style=for-the-badge" alt="测试: 48 passed" />
</p>

---

## 📋 目录

- [项目简介](#项目简介)
- [核心架构](#核心架构)
- [快速开始](#快速开始)
- [功能概览](#功能概览)
- [项目结构](#项目结构)
- [验证命令](#验证命令)
- [当前状态](#当前状态)
- [路线图](#路线图)
- [相关文档](#相关文档)

---

## 项目简介

**TCM-Agent** 是一个面向中医药领域的智能辅助决策系统。它基于 [MiniCode](https://github.com/LiuMengxuan04/MiniCode) 框架，通过注入中医角色定义、知识规则和工作流技能，结合 Python MCP Server 提供的中医药数据引擎，实现中药查询、配伍禁忌检查、辨证分析等核心能力。

### 设计原则

| 原则 | 说明 |
|------|------|
| **零代码侵入** | 中医药知识层使用纯 Markdown，不修改底层框架核心代码 |
| **分层解耦** | Agent 框架、知识层、数据引擎通过 MCP 协议通信 |
| **混合检索** | SQLite 精确查询 + ChromaDB 语义检索互补 |
| **可追溯入库** | 每条医学数据均可回溯到原始文本和复核状态 |
| **安全优先** | 所有输出包含免责声明和安全提示，十八反十九畏零漏报 |
| **评测驱动** | Harness 工程贯穿全流程，量化指标指导迭代优化 |

---

## 核心架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    TCM-Agent（项目根目录）                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  MiniCode (TypeScript) — 底层 Agent 框架【不动核心代码】    │  │
│  │  src/agent-loop.ts    ← 模型↔工具循环                      │  │
│  │  src/tool.ts          ← 工具注册中心                       │  │
│  │  src/prompt.ts        ← System Prompt 构建（注入中医角色）  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                      │
│  ┌───────────────────────┼───────────────────────────────────┐  │
│  │         中医药知识层（纯 Markdown，零代码侵入）              │  │
│  │                                                           │  │
│  │  TCM-AGENT.md              ← 中医角色 + 安全边界 + 免责     │  │
│  │  .tcm-agent/rules/         ← 辨证/方剂/中药/安全 规则       │  │
│  │  .tcm-agent/skills/        ← 辨证/查药/方剂匹配 工作流      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                      │
│                   MCP 协议 (stdio)                               │
│                          │                                      │
│  ┌───────────────────────┴───────────────────────────────────┐  │
│  │        tcm-mcp-server (Python) — 中医药数据引擎             │  │
│  │                                                           │  │
│  │  ┌─────────────────┐  ┌──────────────────────────────┐   │  │
│  │  │ MCP 工具层       │  │ RAG 检索引擎                 │   │  │
│  │  │                 │  │                              │   │  │
│  │  │ tcm_search_herb │  │ LangChain + ChromaDB          │   │  │
│  │  │ tcm_search_pres │  │                              │   │  │
│  │  │ tcm_diagnosis   │──│ {症状} → embedding → 检索    │   │  │
│  │  │ tcm_interact_chk│  │     → 相关医案/方剂/中药      │   │  │
│  │  │ tcm_acupoint    │  │     → LLM 重排序 → 返回      │   │  │
│  │  └─────────────────┘  └──────────────────────────────┘   │  │
│  │                                                           │  │
│  │  数据层：SQLite（结构化）+ ChromaDB（向量库）+ Markdown    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 三层架构

#### 1. 主 Agent 框架（MiniCode）

基于 MiniCode 框架，通过 System Prompt 注入中医角色定义，**不修改框架核心代码**。

| 模块 | 职责 |
|------|------|
| `src/agent-loop.ts` | 模型↔工具多轮调用循环 |
| `src/tool.ts` | 工具注册、校验、执行 |
| `src/prompt.ts` | System Prompt 构建（加载 TCM-AGENT.md + rules + skills） |
| `src/memory.ts` | 分层指令文件加载 |
| `src/mcp.ts` | MCP Server 通信管理 |

#### 2. 中医药知识层（纯 Markdown）

- **角色定义**：[TCM-AGENT.md](./TCM-AGENT.md) — 中医角色定位、核心能力、行为准则
- **知识规则**：`.tcm-agent/rules/` — 诊断学、中药学、方剂学、安全边界
- **工作流技能**：`.tcm-agent/skills/` — 辨证、查药、方剂匹配、医案分析

#### 3. 中医药数据引擎（tcm-mcp-server）

Python 实现的 MCP Server，提供结构化数据查询与 RAG 语义检索能力。

| 层次 | 技术栈 |
|------|--------|
| MCP 工具层 | Python MCP SDK |
| RAG 引擎 | LangChain + ChromaDB + sentence-transformers |
| 结构化数据 | SQLite |
| 向量模型 | BAAI/bge-large-zh-v1.5（Embedding）+ bge-reranker-large（重排序） |

---

## 快速开始

### 前置要求

- Node.js ≥ 18
- Python ≥ 3.10
- npm

### 安装

```bash
# 1. 安装主 Agent
cd TCM-Agent
npm install
npm run install-local

# 2. 安装 MCP Server
cd tcm-mcp-server
pip install -e .
```

### 配置 MCP Server

项目已预置 `.mcp.json` 配置文件，指向 `tcm-mcp-server`：

```json
{
  "mcpServers": {
    "tcm-data-engine": {
      "command": "python",
      "args": ["-m", "tcm_mcp_server.server"],
      "cwd": "tcm-mcp-server",
      "env": {
        "PYTHONPATH": "src",
        "PYTHONIOENCODING": "utf-8"
      },
      "enabled": true
    }
  }
}
```

### 启动

```bash
# 开发模式
cd TCM-Agent
npm run dev

# 或使用安装后的命令
minicode
```

---

## 功能概览

### MCP 工具清单

| 工具名 | 输入参数 | 检索方式 | 功能说明 |
|--------|----------|----------|----------|
| `tcm_search_herb` | `name`, `nature?`, `taste?`, `meridian?`, `keywords?` | SQLite + 向量 | 中药详情查询（性味归经功效主治禁忌） |
| `tcm_search_prescription` | `name?`, `syndrome?`, `symptoms?`, `herbs?` | 向量 + SQLite | 方剂详情查询（组成功用主治方解加减） |
| `tcm_diagnosis_syndrome` | `symptoms: string[]`, `tongue?`, `pulse?` | 向量检索 | 辨证分析（可能证型列表 + 置信度） |
| `tcm_drug_interaction_check` | `herbs: string[]` | 规则引擎 + SQLite | 配伍禁忌检查（十八反、十九畏） |
| `tcm_acupoint_search` | `name?`, `meridian?`, `keywords?` | SQLite | 穴位详情查询（定位归经主治操作） |
| `tcm_classic_case_search` | `keywords: string`, `syndrome?` | 向量检索 | 经典医案检索 |

### 安全规则覆盖

- **十八反**：36 组药物组合全覆盖
- **十九畏**：19 组药物组合全覆盖
- **别名映射**：支持常见别名（如附子/川乌/草乌→乌头，川贝母/浙贝母→贝母等）
- **妊娠禁忌**：妊娠禁忌药物警示
- **毒性药物**：毒性药物用量范围警示

### 数据接入质控

数据入库采用 **Schema 先行 + 规则解析为主 + LLM 辅助补洞 + 强校验 + 人工抽检** 策略：

```
中药 Markdown → normalize_text → parse_herb_markdown
  → HerbIngestionRecord → validate_herb_record
  → import SQLite 或写入 review queue
```

- 干净记录直接入库
- 毒性药物、禁忌内容进入复核队列
- 异常剂量单位进入复核
- 非法性味、归经字段直接拒绝

---

## 项目结构

```
TCM-Agent/                              ← 主仓库（基于 MiniCode 二开）
├── TCM-AGENT.md                        ← 中医角色定义
├── TCM-ARCHITECTURE.md                 ← 完整架构方案
├── .tcm-agent/
│   ├── rules/                          ← 中医知识规则
│   │   ├── tcm-diagnostics.md          ← 诊断学规则
│   │   ├── tcm-herbology.md            ← 中药学规则
│   │   ├── tcm-prescriptions.md        ← 方剂学规则
│   │   └── tcm-safety.md               ← 安全边界规则
│   └── skills/                         ← 工作流技能
│       ├── tcm-diagnosis/SKILL.md      ← 辨证工作流
│       ├── tcm-herb-query/SKILL.md     ← 中药查询工作流
│       ├── tcm-prescription-match/SKILL.md ← 方剂匹配工作流
│       └── tcm-case-analysis/SKILL.md  ← 医案分析工作流
├── .mcp.json                           ← MCP Server 配置
├── .github/workflows/tcm-harness.yml   ← CI 自动化测试
├── src/                                ← MiniCode 框架源码
├── web/                                ← Vue 3 Web UI 网关
│   ├── src/
│   │   ├── components/                 ← 聊天界面组件
│   │   ├── stores/                     ← Pinia 状态管理
│   │   └── router/                     ← 路由配置
│   └── vite.config.ts
├── tcm-mcp-server/                     ← Python 中医药数据引擎
│   ├── pyproject.toml
│   ├── src/
│   │   ├── server.py                   ← MCP Server 入口
│   │   ├── tools/                      ← MCP 工具实现
│   │   ├── rag/                        ← RAG 检索引擎
│   │   ├── models/                     ← 数据模型
│   │   └── data/                       ← 数据导入、校验、复核
│   ├── tests/                          ← Harness 评测工程
│   │   ├── datasets/                   ← 评测数据集
│   │   ├── unit/                       ← 单元测试
│   │   ├── rag/                        ← RAG 质量评测
│   │   ├── ingestion/                  ← 数据接入质控测试
│   │   ├── safety/                     ← 安全专项测试
│   │   ├── e2e/                        ← 端到端测试
│   │   └── benchmark/                  ← 性能基准测试
│   └── data/
│       ├── raw/                        ← 原始 Markdown
│       ├── normalized/                 ← 规范化 Markdown
│       ├── review/                     ← 待人工复核数据
│       ├── tcm.db                      ← SQLite 数据库
│       └── chroma/                     ← ChromaDB 持久化
└── docs/                               ← 文档与展示页面
```

---

## 验证命令

### 主 Agent 测试

```powershell
cd TCM-Agent
npm.cmd test          # 运行测试（204 passed）
npm.cmd run check     # TypeScript 类型检查
```

### MCP Server 测试

```powershell
cd tcm-mcp-server
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests -q
# 结果：48 passed
```

> **注意**：Anaconda 全局 pytest 插件与 NumPy 2 存在兼容冲突，需设置 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 避免外部插件污染测试环境。

---

## 当前状态

> **MVP 原型已可用，安全规则、MCP 集成和数据入库质控已开始工程化落地。**

### 已完成

| 模块 | 状态 | 说明 |
|------|------|------|
| 主 Agent 知识层 | ✅ | 中医角色、规则、技能加载，204 测试通过 |
| MCP 数据引擎 | ✅ | 6 个工具，SQLite + ChromaDB，种子数据（中药 29、方剂 14、证型 18、穴位 19） |
| 安全规则 | ✅ | 十八反、十九畏全覆盖，别名映射 |
| Harness 测试 | ✅ | 48 测试通过，含单元、安全、数据接入、集成测试 |
| 数据可追溯 | ✅ | source_file/source_hash/review_status 等追溯字段 |
| 数据接入闭环 | ✅ | Markdown → 规范化 → 解析 → 校验 → 复核 → 入库 |
| CI 自动化 | ✅ | GitHub Actions（tcm-harness.yml），自动运行主 Agent + MCP Harness |
| Web UI 网关 | ✅ | Vue 3 + Vite 聊天界面，Pinia 状态管理 |

### 种子数据规模

| 数据类型 | 数量 |
|----------|------|
| 中药 | 29 条 |
| 方剂 | 14 条 |
| 证型 | 18 条 |
| 穴位 | 19 条 |

### 已知缺口

- [ ] 批量数据导入（`data/raw/herbology/*.md`）
- [ ] 方剂 Markdown 解析
- [ ] RAG 质量评测（Recall@K、MRR、NDCG）

---

## 路线图

### P1：批量数据导入
- 支持从 `data/raw/herbology/*.md` 批量读取
- 生成导入成功数、review 数、拒绝数、汇总报告

### P2：方剂接入链路
- 建立 `PrescriptionIngestionRecord`
- 支持方剂 Markdown 解析与校验

### P2：RAG 质量 Harness
- 建立 `tests/rag/`
- Recall@5、MRR、精确字段匹配率

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [TCM-AGENT.md](./TCM-AGENT.md) | 中医角色定义与行为准则 |
| [TCM-ARCHITECTURE.md](./TCM-ARCHITECTURE.md) | 完整架构方案（含 RAG 设计、Harness 评测、实施路线图） |
| [ARCHITECTURE_ZH.md](./ARCHITECTURE_ZH.md) | MiniCode 框架架构说明 |
| [USAGE_ZH.md](./USAGE_ZH.md) | MiniCode 详细使用指南 |
| [CONTRIBUTING_ZH.md](./CONTRIBUTING_ZH.md) | 贡献规范 |

---

## 许可证

本项目基于 [MiniCode](https://github.com/LiuMengxuan04/MiniCode) 二次开发，遵循原项目许可证。详见 [LICENSE](./LICENSE)。

> **免责声明**：TCM-Agent 仅供中医药学习与参考研究使用，所有输出结果仅供参考，不构成医疗建议。请遵医嘱，切勿自行用药。
