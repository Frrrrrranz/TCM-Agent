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
  <img src="https://img.shields.io/badge/状态-生产级别-4CAF50?style=for-the-badge" alt="状态: 生产级别" />
  <img src="https://img.shields.io/badge/框架-MiniCode-D97757?style=for-the-badge" alt="框架: MiniCode" />
  <img src="https://img.shields.io/badge/数据引擎-Python%20MCP-3776AB?style=for-the-badge" alt="数据引擎: Python MCP" />
  <img src="https://img.shields.io/badge/测试-286%20passed-4CAF50?style=for-the-badge" alt="测试: 286 passed" />
</p>

---

## 📋 目录

- [项目简介](#项目简介)
- [核心成果](#核心成果)
- [核心架构](#核心架构)
- [快速开始](#快速开始)
- [功能概览](#功能概览)
- [项目结构](#项目结构)
- [验证命令](#验证命令)
- [当前状态与规模](#当前状态与规模)
- [路线图](#路线图)
- [相关文档](#相关文档)

---

## 项目简介

**TCM-Agent** 是一个面向中医药场景的 AI Agent 问答与临床智能诊断辅助系统，集成 MCP 工具调用、RAG 混合检索、Session Memory 异步记忆持久化与 Web 流式交互能力。项目基于 [MiniCode](https://github.com/LiuMengxuan04/MiniCode) 框架，通过注入中医角色知识与安全规则，结合 Python MCP Server 提供的百万级数据引擎，实现中药查询、配伍禁忌检查、辨证分析及医案检索等核心能力。

---

## 核心成果

| 成果维度 | 详细说明 |
|----------|----------|
| **三层解耦架构** | Agent 框架层、Markdown 知识规则层、Python MCP 数据引擎通过 MCP 协议通信，领域知识与底层框架彻底解耦。 |
| **大批量数据接入** | 解析清洗 HERB、TCMbank 及复方数据，累计入库 **127,945 条** 结构化记录，打通中药成分、配方多源关联。 |
| **向量库全量重建** | 基于全量数据重新构建 ChromaDB 向量索引，为 RAG 检索管线提供高质量的语义嵌入和相似度召回。 |
| **会话记忆系统** | 基于 SQLite 异步三表进行会话历史、运行轨迹及工具详情持久化。首创 **Fail-Open** 容错设计（写库异常绝不阻塞大模型推理），支持多轮对话摘要提取（最近 5 轮）并于 System Prompt 动态注入。 |
| **混合检索评测** | 建立 Recall@K / MRR / NDCG@K RAG 量化评测体系。证型检索（Reranked）与方剂检索（Hybrid）的 Recall@5 均达到 **1.0**。 |
| **安全规则引擎** | 内置十八反、十九畏及常用别名映射（如 `附子 / 川乌 -> 乌头` 等），支持妊娠禁忌和毒性剂量警示，安全检测零漏报。 |
| **双层评测与 CI** | Pytest Harness + GitHub Actions CI，主 Agent 204 个测试与 MCP Server 82 个测试（共计 **286 个测试**）全部通过。 |
| **智能诊断工作站** | 前端 Vue 3 + TypeScript 问诊控制台，通过 WebSocket 与 FastAPI Gateway 联航，实现多轮流式对话与工具调用状态渲染。 |

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

### 三层架构说明

#### 1. 主 Agent 框架（MiniCode）
基于 MiniCode 框架，通过 System Prompt 动态注入中医角色定义，**不修改框架底层核心代码**。
* `src/agent-loop.ts`：负责模型与外部工具的多轮循环交互。
* `src/tool.ts`：管理工具的统一注册、校验与执行。
* `src/prompt.ts`：System Prompt 构建（动态加载 `TCM-AGENT.md`、rules 及 skills）。

#### 2. 中医药知识层（纯 Markdown）
* **角色定位**：[TCM-AGENT.md](./TCM-AGENT.md) — 明确定义了中医角色边界、行为准则、输出稳定性与免责声明。
* **临床规则**：`.tcm-agent/rules/` — 包含诊断学、中药学、方剂学及配伍安全边界。
* **工作流技能**：`.tcm-agent/skills/` — 提供辨证、方剂匹配、中药查询和医案分析的标准化技能说明。

#### 3. 中医药数据引擎（tcm-mcp-server）
Python 构建的结构化数据与向量融合检索引擎。
* **MCP 工具服务**：基于 Python MCP SDK 将检索管线标准化为 6 个工具端点。
* **RAG 管线**：BGE 系列模型嵌入 + ChromaDB 向量语义检索 + BGE Reranker 重排序管线。
* **持久化三表**：SQLite 存储临床对话 Session、运行记录 Run 和 Tool 执行历史（`memory.db`），保障跨会话记忆恢复。

---

## 快速开始

### 前置要求
* Node.js ≥ 18
* Python ≥ 3.10
* npm

### 安装步骤
```bash
# 1. 安装主 Agent
cd TCM-Agent
npm install
npm run install-local

# 2. 安装 MCP Server
cd tcm-mcp-server
pip install -e .
```

### 启动服务
```bash
# 启动本地开发模式
cd TCM-Agent
npm run dev

# 或使用安装后的 minicode CLI 命令
minicode
```

---

## 功能概览

### MCP 工具清单

| 工具名 | 输入参数 | 检索方式 | 功能说明 |
|--------|----------|----------|----------|
| `tcm_search_herb` | `name`, `nature?`, `taste?`, `meridian?`, `keywords?` | SQLite + 向量 | 查询中药的性味、归经、功效、主治及禁忌 |
| `tcm_search_prescription` | `name?`, `syndrome?`, `symptoms?`, `herbs?` | 向量 + SQLite | 查询方剂的组成、功用、主治、方解及加减 |
| `tcm_diagnosis_syndrome` | `symptoms: string[]`, `tongue?`, `pulse?` | 向量检索 | 辨证分析，输出匹配证候列表与置信度评分 |
| `tcm_drug_interaction_check` | `herbs: string[]` | 规则引擎 + SQLite | 检查药物间的配伍禁忌（十八反、十九畏） |
| `tcm_acupoint_search` | `name?`, `meridian?`, `keywords?` | SQLite | 查询穴位归经、精准定位、主治与操作手法 |
| `tcm_classic_case_search` | `keywords: string`, `syndrome?` | 向量检索 | 检索相关的中医经典医案与临床治疗经验 |

### 配伍安全与别名映射
* **禁忌覆盖**：十八反（36组）、十九畏（19组）药物组合全覆盖。
* **别名自动转换**：支持将常见别名如 `附子 / 川乌 / 草乌` 正则映射至 `乌头`，`浙贝 / 川贝` 映射至 `贝母`，确保禁忌检测零漏报。
* **剂量与毒性预警**：对毒性中药和大剂量用药输出强安全警示及免责声明。

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
├── web/                                ← Vue 3 Web UI 诊断工作站
│   ├── src/
│   │   ├── components/                 ← 聊天及结构化组件
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
│   │   └── data/                       ← 数据导入、校验、会话持久化
│   ├── tests/                          ← Harness 评测工程
│   └── data/
│       ├── tcm.db                      ← SQLite 全量中医药数据库
│       ├── memory.db                   ← 会话历史持久化数据库
│       └── chroma/                     ← 全量重建的 ChromaDB 向量库
└── docs/                               ← 文档与可视化展示页面
```

---

## 验证命令

### 主 Agent 测试
```powershell
cd TCM-Agent
npm test          # 运行 TS 单元测试（204 passed）
npm run check     # TypeScript 强类型检查
```

### MCP Server 测试
```powershell
cd tcm-mcp-server
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests -q
# 结果：82 passed
```

---

## 当前状态与规模

### 数据集规模
* **中药主记录**：11,230 条（基于 HERB 与 TCMbank 清洗整合）
* **方剂主记录**：31,619 条（基于 ETCM 与复方数据库）
* **证型与穴位**：分别入库 18 条与 19 条

### 核心特性状态
* **Session 记忆持久化**：✅ 已落地，支持 WebSocket 帧中摘要传递，并在 System Prompt 动态注入，完美支持跨对话多轮记忆。
* **数据接入与可追溯性**：✅ 已完成，所有数据带 `source_file`、`source_hash`，支持毒性、剂量异常自动拦截与复核。
* **量化评测体系**：✅ 已建立，Reranked 证型检索及 Hybrid 方剂检索均在 15 组 GT 用例上跑通验证。

---

## 路线图

### P1：大批量 Markdown 数据流批量解析
- 支持从本地 raw 文件夹中读取大规模非结构化医学 Markdown 文本并增量写入 SQLite。

### P2：增量向量库更新方案
- 研发低延迟的 ChromaDB 增量嵌入更新机制，替代全量重建索引。

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [TCM-AGENT.md](./TCM-AGENT.md) | 中医角色定义与行为准则（包含输出温度对照表） |
| [TCM-ARCHITECTURE.md](./TCM-ARCHITECTURE.md) | 完整架构方案（含 RAG 设计、Harness 评测、实施路线图） |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | MiniCode 框架架构说明 |
| [USAGE.md](./USAGE.md) | MiniCode 详细使用指南 |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | 贡献规范 |
| [CLAUDE_CODE_PATTERNS.md](./CLAUDE_CODE_PATTERNS.md) | 深入理解 MiniCode 与 Claude Code 架构与设计模式的对比 |

---

## 许可证

本项目基于 [MiniCode](https://github.com/LiuMengxuan04/MiniCode) 二次开发，遵循原项目许可证。详见 [LICENSE](./LICENSE)。

> **免责声明**：TCM-Agent 仅供中医药学习与参考研究使用，所有输出结果仅供参考，不构成任何临床医疗建议。请遵医嘱，切勿自行盲目用药。
