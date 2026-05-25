# 🏥 中医药智能体（TCM-Agent）完整架构方案

> 本文档描述 TCM-Agent 的完整架构设计、RAG 检索方案、MCP Server 工具清单、Harness 评测工程及实施路线图，作为项目整体参考。

---

## 目录

- [一、总体架构](#一总体架构)
- [二、分层說明](#二分層說明)
- [三、RAG 详细设计](#三rag-详细设计)
- [四、数据接入与结构化入库](#四数据接入与结构化入库)
- [五、MCP Server 工具清单](#五mcp-server-工具清单)
- [六、Harness 评测工程](#六harness-评测工程)
- [七、目录结构总览](#七目录结构总览)
- [八、MVP 实施路线图（7 天计划）](#八mvp-实施路线图7-天计划)
- [九、关键设计决策](#九关键设计决策)

---

## 一、总体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    TCM-Agent（项目根目录）                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  MiniCode (TypeScript) — 底层 Agent 框架【不动核心代码】    │  │
│  │                                                           │  │
│  │  src/agent-loop.ts    ← 模型↔工具循环                     │  │
│  │  src/tool.ts          ← 工具注册中心                       │  │
│  │  src/prompt.ts        ← System Prompt 构建（注入中医角色）  │  │
│  │  src/tui/*            ← 终端 UI                            │  │
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
│                   MCP 协议 (stdio/HTTP)                          │
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

### 架构核心原则

| 原则 | 说明 |
|------|------|
| **零代码侵入** | 中医药知识层使用纯 Markdown，不修改底层 MiniCode 核心代码 |
| **分层解耦** | Agent 框架、知识层、数据引擎通过 MCP 协议通信 |
| **混合检索** | SQLite 精确查询 + ChromaDB 语义检索互补 |
| **可追溯入库** | Markdown 原文、结构化记录、校验状态和人工复核结果必须可追溯 |
| **安全优先** | 所有输出必须包含免责声明和安全提示 |
| **评测驱动** | Harness 工程贯穿全流程，量化指标指导迭代优化 |

---

## 二、分层說明

### 2.1 主 Agent 框架（MiniCode）

> **核心代码不动**，仅通过 System Prompt 注入中医角色定义。

| 模块 | 职责 |
|------|------|
| `src/agent-loop.ts` | 模型↔工具多轮调用循环 |
| `src/tool.ts` | 工具注册、校验、执行 |
| `src/prompt.ts` | System Prompt 构建（加载 TCM-AGENT.md + rules + skills） |
| `src/memory.ts` | 分层指令文件加载（TCM-AGENT.md → rules → skills） |
| `src/mcp.ts` | MCP Server 通信管理 |

### 2.2 中医药知识层（纯 Markdown）

#### 角色定义

| 文件 | 内容 |
|------|------|
| `TCM-AGENT.md` | 中医角色定位、核心能力、行为准则、输出格式规范、知识边界 |

#### 知识规则（`.tcm-agent/rules/`）

| 文件 | 覆盖范围 |
|------|----------|
| `tcm-diagnostics.md` | 八纲辨证、脏腑辨证、气血津液辨证、六经辨证、卫气营血辨证 |
| `tcm-herbology.md` | 四气五味、归经理论、功效分类、特殊用法、炮制 |
| `tcm-prescriptions.md` | 君臣佐使组方结构、方剂分类速查、类方鉴别 |
| `tcm-safety.md` | 十八反、十九畏、妊娠禁忌、毒性药物警示、强制输出规则 |

#### 工作流技能（`.tcm-agent/skills/`）

| 技能目录 | 用途 |
|----------|------|
| `tcm-diagnosis/` | 四诊合参与辨证分析工作流 |
| `tcm-herb-query/` | 中药查询与解析工作流 |
| `tcm-prescription-match/` | 方剂匹配与推荐工作流 |
| `tcm-case-analysis/` | 医案分析与学习工作流 |

### 2.3 中医药数据引擎（tcm-mcp-server）

Python 实现的 MCP Server，提供结构化数据查询与 RAG 语义检索能力。

| 层次 | 技术栈 |
|------|--------|
| MCP 工具层 | Python MCP SDK |
| RAG 引擎 | LangChain + ChromaDB + sentence-transformers |
| 结构化数据 | SQLite |
| 向量模型 | BAAI/bge-large-zh-v1.5（Embedding）+ bge-reranker-large（重排序） |

---

## 三、RAG 详细设计

### 3.1 知识库构建（离线，一次性）

```
tcm-mcp-server/data/
├── raw/                              # 原始中医药文献（Markdown）
│   ├── herbology/                    # 《中药学》分类数据
│   │   ├── 解表药.md
│   │   ├── 清热药.md
│   │   └── ...
│   ├── prescriptions/               # 《方剂学》分类数据
│   │   ├── 解表剂.md
│   │   ├── 清热剂.md
│   │   └── ...
│   ├── diagnostics/                 # 《中医诊断学》
│   └── acupoints/                   # 针灸穴位数据
│
├── normalized/                       # 规范化 Markdown（固定字段模板）
├── review/                           # 待人工复核的抽取结果
│
├── chroma/                          # ChromaDB 持久化向量库（自动生成）
│
└── tcm.db                           # SQLite 结构化查询（精确匹配）
    ├── herbs (id, name, pinyin, nature, taste, meridian, toxicity...)
    ├── prescriptions (id, name, source, composition, indication...)
    ├── syndromes (id, name, category, key_symptoms...)
    └── acupoints (id, name, meridian, location, indication...)
```

### 3.2 RAG 检索流程

```
用户提问："头痛、发热、恶风、脉浮缓，用什么方？"
       │
       ▼
┌──────────────────┐
│  1. Query 改写    │  ← LangChain Prompt 模板
│  "头痛 发热 恶风   │
│   脉浮缓 方剂"     │
└────────┬─────────┘
         ▼
┌──────────────────┐
│  2. 向量检索      │  ← text-embedding-3-small / bge-large-zh
│  ChromaDB         │
│  → Top-10 相关片段 │
└────────┬─────────┘
         ▼
┌──────────────────┐
│  3. 重排序 (Rerank)│  ← cross-encoder 模型
│  → Top-3 精确结果  │
└────────┬─────────┘
         ▼
┌──────────────────┐
│  4. 结构化补全    │  ← SQLite 精确查表
│  桂枝汤完整信息    │     组成/功用/主治/方解/禁忌
└────────┬─────────┘
         ▼
┌──────────────────┐
│  5. 组装返回      │  ← Markdown 格式化
│  MCP Tool Result  │
└──────────────────┘
```

### 3.3 混合检索策略

| 查询类型 | 检索方式 | 说明 |
|----------|----------|------|
| 症状描述 → 证型 | **向量检索**（语义匹配） | "头痛发热恶风"→太阳中风证 |
| 中药名查询 | **SQLite 精确查表** | "桂枝"→性味归经功效 |
| 方剂名查询 | **SQLite + 向量检索** | "桂枝汤"→组成+相关类方 |
| 配伍禁忌检查 | **规则引擎**（十八反十九畏硬编码） | "半夏+附子"→警告 |
| 穴位查询 | **SQLite 精确查表** | "足三里"→定位+主治 |

### 3.4 RAG 管线组件

| 组件 | 文件 | 职责 |
|------|------|------|
| Embedding 模型管理 | `rag/embeddings.py` | 加载 bge-large-zh-v1.5，管理缓存 |
| ChromaDB 封装 | `rag/vector_store.py` | 向量库 CRUD，集合管理 |
| 混合检索引擎 | `rag/retriever.py` | 向量检索 + SQLite 精确查询 + 规则引擎 |
| RAG 管线编排 | `rag/pipeline.py` | LangChain 链式调用：改写→检索→重排→补全→组装 |

---

## 四、数据接入与结构化入库

### 4.1 入库原则

中医药结构化数据不采用 LLM 全自动入库。入库主链路采用 **Schema 先行 + 规则解析为主 + LLM 辅助补洞 + 强校验 + 人工抽检**，确保每条医学知识都能回溯到原始文本和复核状态。

| 原则 | 说明 |
|------|------|
| **Schema 先行** | 先固定 SQLite 表结构、字段枚举、剂量单位、禁忌类型，再导入数据 |
| **规则解析为主** | 对固定模板 Markdown 使用确定性解析器，避免自由文本直接入库 |
| **LLM 辅助补洞** | LLM 只产出候选 JSON，不直接写入数据库 |
| **强校验闸门** | Pydantic/JSON Schema、字段枚举、剂量单位、禁忌词和来源校验必须全部通过 |
| **人工复核闭环** | 低置信度、字段冲突、单位异常、毒性/禁忌相关记录进入 review 队列 |
| **原文可追溯** | SQLite 记录保留 source_file、source_heading、source_text、source_hash、review_status |

### 4.2 Markdown 规范化模板

原始教材 Markdown 先转换为固定字段模板，再进入解析器。模板示例：

```md
## 桂枝

- 类别：解表药
- 异名：
- 性味：辛、甘，温
- 归经：心、肺、膀胱经
- 功效：发汗解肌，温通经脉，助阳化气
- 主治：风寒感冒，脘腹冷痛，血寒经闭，关节痹痛，痰饮，水肿，心悸
- 用量：3-10g
- 用法：
- 禁忌：温病表热、阴虚阳盛者慎用
- 毒性：
- 来源：《中药学》十三五规划教材
```

### 4.3 入库流水线

```
原始 Markdown
   │
   ▼
1. 文档规范化
   - 标题层级整理
   - 字段名统一
   - 全角/半角、标点、剂量单位规范化
   │
   ▼
2. 规则解析
   - 固定字段抽取
   - 药名/方名/证型名标准化
   - source_text/source_hash 绑定
   │
   ▼
3. LLM 辅助抽取（仅用于非标准段落）
   - 输出候选 JSON
   - 标记不确定字段
   - 不直接写入 SQLite
   │
   ▼
4. 强校验闸门
   - Schema 校验
   - 枚举校验：四气、五味、归经、方剂分类
   - 剂量校验：单位、范围、特殊用法
   - 安全校验：十八反、十九畏、妊娠禁忌、毒性药物
   │
   ▼
5. 人工复核队列
   - 缺字段、冲突字段、异常剂量、禁忌相关记录进入 review/
   │
   ▼
6. SQLite + ChromaDB 构建
   - 通过复核的数据进入 SQLite
   - 原文片段和结构化摘要进入 ChromaDB
```

### 4.4 结构化数据模型扩展

核心表除业务字段外，统一追加溯源与复核字段：

| 字段 | 用途 |
|------|------|
| `source_file` | 原始 Markdown 文件路径 |
| `source_heading` | 原文标题或药物/方剂条目标题 |
| `source_text` | 对应原文片段 |
| `source_hash` | 原文片段哈希，用于检测教材内容变更 |
| `parser_version` | 抽取脚本版本 |
| `review_status` | `pending` / `approved` / `rejected` / `needs_review` |
| `review_note` | 人工复核备注 |

### 4.5 质控与失败策略

| 场景 | 策略 |
|------|------|
| 必填字段缺失 | 不入库，写入 review 队列 |
| 剂量单位异常 | 不入库，标记 `needs_review` |
| 安全禁忌字段涉及十八反/十九畏/毒性 | 必须人工复核后入库 |
| LLM 输出与规则解析冲突 | 以规则解析为准，并进入 review 队列 |
| source_hash 变化 | 触发重新解析和回归测试 |
| ChromaDB 构建失败 | 不影响 SQLite 精确查询，但 RAG 测试必须失败提示 |

### 4.6 数据接入脚本结构

```
tcm-mcp-server/src/data/
├── schema.py                  ← Pydantic/JSON Schema 定义
├── normalize_markdown.py      ← Markdown 规范化
├── parse_herbs.py             ← 中药字段解析
├── parse_prescriptions.py     ← 方剂字段解析
├── validate_records.py        ← 强校验闸门
├── review_queue.py            ← 生成待复核 JSONL/Markdown
├── import_sqlite.py           ← 写入 SQLite
└── build_chroma.py            ← 构建 ChromaDB
```

---

## 五、MCP Server 工具清单

| 工具名 | 输入参数 | 检索方式 | 输出 |
|--------|----------|----------|------|
| `tcm_search_herb` | `name`, `nature?`, `taste?`, `meridian?`, `keywords?` | SQLite + 向量 | 中药详情（性味归经功效主治禁忌） |
| `tcm_search_prescription` | `name?`, `syndrome?`, `symptoms?`, `herbs?` | 向量 + SQLite | 方剂详情（组成功用主治方解加减） |
| `tcm_diagnosis_syndrome` | `symptoms: string[]`, `tongue?`, `pulse?` | 向量检索 | 可能证型列表 + 置信度 + 辨证依据 |
| `tcm_drug_interaction_check` | `herbs: string[]` | 规则引擎 + SQLite | 配伍禁忌警告 + 原因说明 |
| `tcm_acupoint_search` | `name?`, `meridian?`, `keywords?` | SQLite | 穴位详情（定位归经主治操作） |
| `tcm_classic_case_search` | `keywords: string`, `syndrome?` | 向量检索 | 相关医案（病因病机治法方药） |

### MCP Server 模块结构

```
tcm-mcp-server/src/
├── server.py                   ← MCP Server 入口（注册所有工具）
├── tools/
│   ├── search_herb.py          ← 中药查询工具
│   ├── search_prescription.py  ← 方剂查询工具
│   ├── diagnosis_syndrome.py   ← 辨证分析工具
│   ├── drug_interaction.py     ← 配伍禁忌检查工具
│   ├── acupoint_search.py      ← 穴位查询工具
│   └── classic_case.py         ← 医案检索工具
├── rag/
│   ├── embeddings.py           ← Embedding 模型管理
│   ├── vector_store.py         ← ChromaDB 封装
│   ├── retriever.py            ← 混合检索引擎
│   └── pipeline.py             ← LangChain RAG 管线
├── models/
│   ├── herb.py                 ← 中药数据模型
│   ├── prescription.py         ← 方剂数据模型
│   ├── syndrome.py             ← 证型数据模型
│   └── acupoint.py             ← 穴位数据模型
└── data/
    ├── seed_herbs.py           ← 种子数据导入脚本
    ├── seed_prescriptions.py   ← 方剂种子数据导入
    └── build_chroma.py         ← 向量库构建脚本
```

---

## 六、Harness 评测工程

### 5.1 为什么 TCM-Agent 需要 Harness

> **MiniCode 主仓库**将 benchmark harness 列为 P2（非紧急），因为通用 coding agent 的评测场景复杂、标准不统一。
>
> **但 TCM-Agent 不同**——中医药领域有明确的「正确答案」可做 benchmark，且医疗场景对准确性要求极高，Harness 工程**不是可选项，而是必需品**。

| 必要性 | 说明 |
|--------|------|
| **医疗准确性** | 错一味药可能出问题，不能靠人工抽查 |
| **RAG 质量量化** | 需要 Recall@K、MRR、NDCG 等指标指导 Embedding 调优 |
| **安全规则保障** | 十八反十九畏等硬规则必须有自动化测试确保零漏报 |
| **回归测试** | 知识库更新后确保旧用例不退化 |
| **辨证一致性** | 同一症状集在不同轮次应得到一致的辨证结果 |

### 5.2 Harness 总体架构

```
tcm-mcp-server/
└── tests/                              ← Harness 根目录
    ├── conftest.py                     ← Pytest 全局配置、fixtures
    ├── datasets/                       ← 评测数据集（JSON/YAML）
    │   ├── herb_query.json             ← 中药查询评测集
    │   ├── prescription_match.json     ← 方剂匹配评测集
    │   ├── syndrome_diagnosis.json     ← 辨证评测集
    │   ├── drug_interaction.json       ← 配伍禁忌评测集
    │   ├── acupoint_query.json         ← 穴位查询评测集
    │   ├── end_to_end.json             ← 端到端流程评测集
    │   └── adversarial.json            ← 幻觉、矛盾输入、伪药名测试集
    │
    ├── unit/                           ← 单元测试（工具级）
    │   ├── test_search_herb.py
    │   ├── test_search_prescription.py
    │   ├── test_diagnosis_syndrome.py
    │   ├── test_drug_interaction.py
    │   ├── test_acupoint_search.py
    │   └── test_classic_case.py
    │
    ├── rag/                            ← RAG 质量评测
    │   ├── test_retrieval_quality.py   ← Recall@K / MRR / NDCG
    │   ├── test_rerank_improvement.py  ← 重排序前后对比
    │   └── test_hybrid_search.py       ← 混合检索策略对比
    │
    ├── safety/                         ← 安全专项测试
    │   ├── test_eighteen_anti.py       ← 十八反全覆盖测试
    │   ├── test_nineteen_fear.py       ← 十九畏全覆盖测试
    │   ├── test_pregnancy_contra.py    ← 妊娠禁忌测试
    │   └── test_toxicity_warning.py    ← 毒性药物警示测试
    │
    ├── e2e/                            ← 端到端集成测试
    │   ├── test_full_consultation.py   ← 完整问诊流程
    │   ├── test_multi_turn.py          ← 多轮对话场景
    │   └── test_adversarial.py         ← 对抗性拒答与矛盾识别
    │
    └── benchmark/                      ← 性能基准测试
        ├── test_latency.py             ← 各工具响应延迟
        ├── test_concurrency.py         ← 并发压力测试
        └── test_memory_usage.py        ← 内存占用监控
```

同时增加数据接入质控测试：

```
tcm-mcp-server/tests/ingestion/
├── test_markdown_normalize.py          ← Markdown 模板规范化测试
├── test_parse_herbs.py                 ← 中药字段解析测试
├── test_validate_records.py            ← Schema、枚举、剂量、禁忌校验
├── test_review_queue.py                ← 异常记录进入复核队列
└── test_source_traceability.py         ← source_text/source_hash 可追溯性
```

### 5.3 评测数据集设计

#### 数据集格式规范

```json
{
  "meta": {
    "name": "中药查询评测集",
    "version": "1.0",
    "source": "《中药学》十三五规划教材",
    "created": "2026-05-22",
    "total_cases": 120
  },
  "cases": [
    {
      "id": "herb-001",
      "category": "解表药",
      "input": {
        "name": "桂枝",
        "fields": ["nature", "taste", "meridian", "功效", "主治"]
      },
      "expected": {
        "nature": "温",
        "taste": "辛、甘",
        "meridian": "心、肺、膀胱经",
        "功效": "发汗解肌，温通经脉，助阳化气",
        "主治": "风寒感冒，脘腹冷痛，血寒经闭，关节痹痛，痰饮，水肿，心悸"
      },
      "strict_fields": ["nature", "taste"],
      "tolerance": {
        "功效": "partial_match"
      }
    }
  ]
}
```

#### 评测集规模规划

| 评测集 | 用例数 | 覆盖范围 | 标注方式 |
|--------|--------|----------|----------|
| 中药查询 | 120 | 覆盖 18 类中药代表性药物 | 教材原文标注 |
| 方剂匹配 | 100 | 覆盖 15 类方剂代表方 | 教材原文标注 |
| 辨证分析 | 80 | 覆盖八纲/脏腑/六经/卫气营血 | 专家标注 |
| 配伍禁忌 | 60 | 十八反 36 组 + 十九畏 19 组 + 妊娠禁忌 | 规则全覆盖 |
| 穴位查询 | 50 | 覆盖十四经重要穴位 | 教材原文标注 |
| 端到端流程 | 30 | 完整问诊→辨证→方剂→安全审查 | 专家标注 |
| 对抗性测试 | 30 | 伪药名、矛盾症状、不足信息、诱导越界 | 期望拒答/追问/指出矛盾 |

### 5.4 评测指标

#### RAG 检索质量指标

| 指标 | 计算方式 | 目标值 | 说明 |
|------|----------|--------|------|
| **Recall@K** | Top-K 中命中相关文档的比例 | ≥ 0.85 (K=5) | 检索覆盖率 |
| **MRR** | 第一个相关结果的倒数排名均值 | ≥ 0.75 | 首条命中质量 |
| **NDCG@K** | 考虑排序位置的归一化折损累计增益 | ≥ 0.80 (K=5) | 排序质量 |
| **精确匹配率** | 结构化字段完全匹配的比例 | ≥ 0.95 | 中药名/方剂名等精确字段 |

#### 工具准确性指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 中药查询准确率 | ≥ 98% | 性味归经功效主治完全正确 |
| 方剂匹配准确率 | ≥ 90% | 症状→方剂推荐合理 |
| 辨证准确率 | ≥ 85% | 证型判断与专家标注一致 |
| 配伍禁忌检出率 | **100%** | 十八反十九畏零漏报 |
| 配伍禁忌误报率 | ≤ 5% | 避免过度警告干扰用户 |
| 穴位查询准确率 | ≥ 98% | 定位归经主治完全正确 |
| 伪药名拒答率 | ≥ 95% | 如“九天玄女草”等不存在药名不得编造 |
| 信息不足追问率 | ≥ 90% | 仅给出“头痛”等不足信息时应主动追问 |

#### 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 单次查询 P50 延迟 | ≤ 500ms | 普通查询 |
| 单次查询 P99 延迟 | ≤ 2s | 含 RAG 检索的复杂查询 |
| 并发 10 请求成功率 | ≥ 99% | 轻量并发 |
| 内存峰值占用 | ≤ 512MB | 含 Embedding 模型加载 |

### 5.5 评测运行

```bash
# 运行全部评测
cd tcm-mcp-server
pytest tests/ -v --report=benchmark.json

# 仅运行安全专项测试
pytest tests/safety/ -v

# 仅运行数据接入质控测试
pytest tests/ingestion/ -v

# 运行 RAG 质量评测并输出详细指标
pytest tests/rag/ -v --metrics=all

# 运行端到端测试
pytest tests/e2e/ -v

# 生成评测报告
pytest tests/ -v --html=report.html --self-contained-html
```

### 5.6 持续集成集成

```yaml
# .github/workflows/tcm-harness.yml（示意）
name: TCM Harness
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: pip install -e tcm-mcp-server/
      - name: Run safety tests
        run: pytest tcm-mcp-server/tests/safety/ -v
      - name: Run ingestion quality tests
        run: pytest tcm-mcp-server/tests/ingestion/ -v
      - name: Run RAG quality tests
        run: pytest tcm-mcp-server/tests/rag/ -v --metrics=all
      - name: Run e2e tests
        run: pytest tcm-mcp-server/tests/e2e/ -v
```

---

## 七、目录结构总览

```
TCM-Agent/                              ← 基于 MiniCode 二开的 TCM-Agent 主仓库
├── TCM-AGENT.md                        ← 中医角色定义
├── .tcm-agent/
│   ├── rules/
│   │   ├── tcm-diagnostics.md          ← 中医诊断学规则
│   │   ├── tcm-herbology.md            ← 中药学规则
│   │   ├── tcm-prescriptions.md        ← 方剂学规则
│   │   └── tcm-safety.md               ← 安全边界规则
│   └── skills/
│       ├── tcm-diagnosis/SKILL.md      ← 辨证工作流
│       ├── tcm-herb-query/SKILL.md     ← 中药查询工作流
│       ├── tcm-prescription-match/SKILL.md ← 方剂匹配工作流
│       └── tcm-case-analysis/SKILL.md  ← 医案分析工作流
├── .mcp.json                           ← MCP Server 配置
└── tcm-mcp-server/                     ← Python 中医药数据引擎
    ├── pyproject.toml                  ← Python 项目配置
    ├── src/
    │   ├── server.py                   ← MCP Server 入口
    │   ├── tools/                      ← MCP 工具实现
    │   ├── rag/                        ← RAG 检索引擎
    │   ├── models/                     ← 数据模型
    │   └── data/                       ← 数据导入、校验、复核脚本
    ├── tests/                          ← Harness 评测工程
    │   ├── conftest.py                 ← Pytest 全局配置
    │   ├── datasets/                   ← 评测数据集
    │   ├── unit/                       ← 单元测试
    │   ├── rag/                        ← RAG 质量评测
    │   ├── ingestion/                  ← 数据接入质控测试
    │   ├── safety/                     ← 安全专项测试
    │   ├── e2e/                        ← 端到端测试
    │   └── benchmark/                  ← 性能基准测试
    └── data/
        ├── raw/                       ← 原始 Markdown
        ├── normalized/                ← 规范化 Markdown
        ├── review/                    ← 待人工复核数据
        ├── tcm.db                     ← SQLite 数据库
        └── chroma/                    ← ChromaDB 持久化
```

---

## 八、MVP 实施路线图（7 天计划）

> 第一轮 MVP 聚焦两个最可量化、最有安全价值的能力：**中药查询** 与 **配伍禁忌检查**。辨证工作流、医案分析、穴位检索和完整 RAG 推荐延后到第二迭代。

### 第一阶段：知识底座与安全边界（第 1-2 天）

| 步骤 | 产出 | 文件 |
|------|------|------|
| 1.1 | 中医角色与安全边界定义 | `TCM-AGENT.md` |
| 1.2 | 八纲辨证 + 脏腑辨证规则 | `.tcm-agent/rules/tcm-diagnostics.md` |
| 1.3 | 中药学四气五味归经规则 | `.tcm-agent/rules/tcm-herbology.md` |
| 1.4 | 配伍禁忌规则（十八反、十九畏、妊娠禁忌） | `.tcm-agent/rules/tcm-safety.md` |
| 1.5 | 安全边界（毒性药物、剂量、免责） | `.tcm-agent/rules/tcm-safety.md` |

### 第二阶段：结构化入库 MVP（第 3 天）

| 步骤 | 产出 | 文件 |
|------|------|------|
| 2.1 | 中药 Markdown 规范化模板 | `tcm-mcp-server/data/normalized/` |
| 2.2 | 中药 Schema 与校验规则 | `tcm-mcp-server/src/data/schema.py` |
| 2.3 | 中药解析与 SQLite 导入脚本 | `parse_herbs.py` / `import_sqlite.py` |
| 2.4 | 待复核队列生成 | `review_queue.py` |

### 第三阶段：MCP Server MVP（第 4-5 天）

| 步骤 | 产出 | 文件 |
|------|------|------|
| 3.1 | Python MCP Server 骨架 | `tcm-mcp-server/` |
| 3.2 | `tcm_search_herb` 精确查询工具 | `tools/search_herb.py` |
| 3.3 | `tcm_drug_interaction_check` 规则引擎 | `tools/drug_interaction.py` |
| 3.4 | MCP Server 配置接入 TCM-Agent | `.mcp.json` |
| 3.5 | ChromaDB/RAG 仅保留接口占位 | `rag/` |

### 第四阶段：Harness 与质控（第 5-6 天）

| 步骤 | 产出 | 说明 |
|------|------|------|
| 4.1 | 中药查询评测集 | `tests/datasets/herb_query.json` |
| 4.2 | 配伍禁忌评测集 | `tests/datasets/drug_interaction.json` |
| 4.3 | 数据接入质控测试 | `tests/ingestion/` |
| 4.4 | 安全专项测试（十八反十九畏全覆盖） | `tests/safety/` |
| 4.5 | 工具单元测试 | `tests/unit/test_search_herb.py` / `test_drug_interaction.py` |
| 4.6 | CI 集成最小集 | `.github/workflows/tcm-harness.yml` |

### 第五阶段：集成测试与交付（第 7 天）

| 步骤 | 产出 |
|------|------|
| 5.1 | 端到端测试（查药→返回结构化信息→安全提示） |
| 5.2 | 端到端测试（输入药物组合→配伍禁忌检查→原因说明） |
| 5.3 | System Prompt 优化（查询边界、免责声明、安全提示） |
| 5.4 | MVP Harness 达标验证 |

### 第二迭代候选功能

| 功能 | 推迟原因 |
|------|----------|
| 方剂匹配与推荐 | 需要更完整的方剂结构化库和症状标注集 |
| 辨证工作流 | 主观性强，需要专家标注和多轮追问评测 |
| 医案分析 | RAG 质量和医案来源清洗要求更高 |
| 穴位检索 | 与中药/方剂主链路相对独立，可独立迭代 |
| Neo4j 知识图谱 | 适合作为后续复杂关系查询增强，不进入 MVP |

---

## 九、关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 主框架语言 | TypeScript（不动） | 现有成熟 Agent 循环无需重写 |
| MCP Server 语言 | Python | RAG 生态最佳（LangChain、ChromaDB、sentence-transformers） |
| 向量数据库 | ChromaDB | 轻量、Python 原生、零运维 |
| 混合检索 | SQLite（精确查询）+ ChromaDB（语义检索） | 中药名/方剂名需精确匹配，症状描述需语义匹配 |
| Embedding 模型 | bge-large-zh-v1.5（BAAI） | 中文语义最佳，开源免费 |
| 重排序 | bge-reranker-large | 提升 RAG Top-3 准确率 |
| MCP 传输协议 | stdio | MiniCode 底层框架默认支持，零配置 |
| 知识层格式 | 纯 Markdown | 零代码侵入，AI 可直接读取 |
| 数据入库策略 | Schema 先行 + 规则解析 + LLM 辅助 + 人工复核 | 医疗知识必须可追溯、可校验、可回滚 |
| LLM 抽取边界 | 只产出候选 JSON，不直接写库 | 防止幻觉或误抽取静默污染数据库 |
| 安全机制 | 规则引擎硬编码 | 十八反十九畏等禁忌需确定性输出，不可依赖语义检索 |
| 评测框架 | Pytest + 结构化数据集 | Python 生态原生支持，与 MCP Server 语言一致 |
| 评测数据集格式 | JSON（含 meta + cases + expected） | 结构化可版本控制，支持精确/模糊匹配 |
| 安全测试策略 | 全覆盖硬编码用例 | 十八反十九畏需 100% 检出率，不可抽样 |

---

> **相关文档**
>
> - [TCM-AGENT.md](./TCM-AGENT.md) — 中医角色定义与行为准则
> - [ARCHITECTURE_ZH.md](./ARCHITECTURE_ZH.md) — MiniCode 框架架构说明
> - [ROADMAP_ZH.md](./ROADMAP_ZH.md) — MiniCode 路线图
