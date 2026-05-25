# TCM-Agent 阶段性总结

更新日期：2026-05-25

## 当前阶段结论

项目已从架构草案推进到可验证的 MVP 工程化阶段。

当前主线能力包括：

- 主 Agent 已能加载中医角色、规则和技能文件。
- Python MCP Server 已具备中医药数据工具骨架。
- 中药查询与配伍禁忌检查已可运行。
- Harness 测试体系已建立最小闭环。
- 数据接入链路已具备规范化、解析、校验、复核和安全入库能力。

整体状态可以概括为：

> MVP 原型已可用，安全规则、MCP 集成和数据入库质控已开始工程化落地。

## 已完成内容

### 1. 主 Agent 知识层

位置：`TCM-Agent/`

已完成：

- `TCM-AGENT.md` 中医角色与安全边界定义。
- `.tcm-agent/rules/` 中医规则加载。
- `.tcm-agent/skills/` 中医技能发现与加载。
- `src/memory.ts` 支持加载 `TCM-AGENT.md` 和 `.tcm-agent/rules`。
- `src/skills.ts` 支持发现 `.tcm-agent/skills`。

验证结果：

- 主 Agent 测试通过：`204 passed`
- TypeScript 检查通过：`npm run check`

### 2. MCP 数据引擎

位置：`tcm-mcp-server/`

已完成：

- MCP Server 入口：`src/tcm_mcp_server/server.py`
- 工具层：
  - `tcm_search_herb`
  - `tcm_search_prescription`
  - `tcm_diagnosis_syndrome`
  - `tcm_drug_interaction_check`
  - `tcm_acupoint_search`
  - `tcm_classic_case_search`
- SQLite 数据库封装。
- ChromaDB 向量库接口。
- RAG pipeline 基础编排。

当前种子数据规模：

- 中药：29 条
- 方剂：14 条
- 证型：18 条
- 穴位：19 条

已验证能力：

- `桂枝` 可返回结构化中药信息。
- `乌头 + 半夏` 可检出十八反。
- `附子 + 半夏` 可通过别名规则检出十八反。
- MCP stdio 可真实启动并列出工具。

### 3. 安全规则覆盖

已完成：

- 配伍禁忌测试数据集：`tests/datasets/drug_interaction.json`
- 覆盖当前规则表中的十八反、十九畏。
- 增加常见别名映射：
  - `附子 / 川乌 / 草乌 -> 乌头`
  - `川贝母 / 浙贝母 -> 贝母`
  - `白芍 / 赤芍 -> 芍药`
  - `肉桂 -> 官桂`
  - 其他常见同类写法

安全测试：

- `tests/safety/test_drug_interaction.py`

### 4. Harness 测试体系

位置：`tcm-mcp-server/tests/`

已建立目录：

- `datasets/`
- `unit/`
- `safety/`
- `ingestion/`
- `integration/`

当前 MCP Harness 验证结果：

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests -q
```

结果：

```text
48 passed
```

说明：

当前 Anaconda 全局 pytest 插件与 NumPy 2 存在兼容冲突，因此需要设置 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 避免外部插件污染项目测试环境。

### 5. 数据可追溯链路

已完成：

- 数据模型增加追溯字段：
  - `source_file`
  - `source_heading`
  - `source_text`
  - `source_hash`
  - `parser_version`
  - `review_status`
  - `review_note`
- 旧 SQLite 数据库连接时会自动补列。
- 历史数据会 backfill 默认追溯信息。
- 已验证 `桂枝` 记录具备 `source_file='seed_herbs.py'` 和 64 位 `source_hash`。

相关测试：

- `tests/ingestion/test_source_traceability.py`

### 6. 数据接入最小闭环

已完成模块：

- `src/tcm_mcp_server/data/schema.py`
- `src/tcm_mcp_server/data/normalize_markdown.py`
- `src/tcm_mcp_server/data/parse_herbs.py`
- `src/tcm_mcp_server/data/validate_records.py`
- `src/tcm_mcp_server/data/review_queue.py`
- `src/tcm_mcp_server/data/import_sqlite.py`

当前支持流程：

```text
中药 Markdown
  -> normalize_text
  -> parse_herb_markdown
  -> HerbIngestionRecord
  -> validate_herb_record
  -> import SQLite 或写入 review queue
```

当前规则：

- 干净记录可以入库。
- 毒性药物进入复核。
- 禁忌、妊娠、十八反、十九畏相关内容进入复核。
- 异常剂量单位进入复核。
- 非法性味、归经字段直接拒绝。

相关测试：

- `tests/ingestion/test_markdown_normalize.py`
- `tests/ingestion/test_parse_herbs.py`
- `tests/ingestion/test_validate_records.py`
- `tests/ingestion/test_review_queue.py`
- `tests/ingestion/test_import_sqlite.py`

## 当前风险与缺口

### 1. 仓库结构仍需整理

当前结构：

- `TCM-Agent/` 是 Git 仓库。
- `tcm-mcp-server/` 位于外层，目前不是 Git 仓库。
- `.mcp.json` 通过相对路径指向外层 MCP Server。

风险：

- 协作、CI、发布时容易遗漏 MCP Server。
- 主仓库和 MCP 数据引擎版本关系不够明确。

建议：

- 将 `tcm-mcp-server/` 纳入主仓库，或独立建仓并固定版本依赖。

### 2. 数据接入仍只覆盖中药单条 Markdown

当前已支持：

- 单条中药 Markdown 规范化解析与入库。

尚未完成：

- `data/raw/herbology/*.md` 批量导入。
- 方剂 Markdown 解析。
- 证型、穴位数据解析。
- review 汇总报告。

### 3. RAG 质量评测尚未启动

当前已有：

- ChromaDB 文件。
- 向量检索接口。

尚未完成：

- Recall@K、MRR、NDCG 测试。
- rerank 前后对比。
- 症状到方剂或证型的质量评测。

### 4. CI 尚未固化

当前测试可本地运行，但还没有 GitHub Actions 工作流。

需要新增：

- `.github/workflows/tcm-harness.yml`
- 主 Agent Node 测试
- MCP Python Harness
- 禁用外部 pytest plugin 的环境变量

## 建议下一阶段任务

### P0：整理项目结构

目标：

- 明确 `TCM-Agent` 与 `tcm-mcp-server` 的版本关系。
- 决定 MCP Server 是纳入主仓库还是独立仓库。

### P1：加入 CI 最小集

目标：

- 每次提交自动运行：
  - 主 Agent `npm test`
  - 主 Agent `npm run check`
  - MCP Harness `pytest tests -q`

### P1：批量数据导入

目标：

- 支持从 `data/raw/herbology/*.md` 批量读取。
- 生成：
  - 导入成功数
  - review 数
  - 拒绝数
  - 汇总报告

### P2：方剂接入链路

目标：

- 建立 `PrescriptionIngestionRecord`
- 支持方剂 Markdown 解析。
- 增加方剂字段校验与 review 队列。

### P2：RAG 质量 Harness

目标：

- 建立 `tests/rag/`
- 增加最小检索质量指标：
  - Recall@5
  - MRR
  - 精确字段匹配率

## 当前验证命令

主 Agent：

```powershell
cd TCM-Agent
npm.cmd test
npm.cmd run check
```

MCP Server：

```powershell
cd tcm-mcp-server
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests -q
```

## 阶段性评价

这轮完成后，项目已经从“能跑的中医 MCP Demo”推进为“有 Harness、有安全规则、有数据接入闸门的 MVP 工程”。

下一阶段的关键不是继续堆功能，而是把 CI、批量导入和仓库结构固定下来，让每次扩数据、扩工具、扩 RAG 都有自动化质量保护。
