# 升级进度（S1）

| 任务 ID | 状态 | 实际调用路径 | 变更 diff | 验证命令 / runId | 结果与限制 | 下一步 |
| --- | --- | --- | --- | --- | --- | --- |
| UPG-00 | integrated | `src/index.ts` → JSON/Web/MCP 入口已记录 | `docs/baseline/` | `npm.cmd test`：207/207；`git diff --check` 通过 | 已冻结 HEAD、WIP 路径、调用图和失败边界；未调用 live 模型/索引 | 补齐运行时版本与单次受控请求 trace，进入 UPG-01 |
| BENCH-00 | verified | `tcm-bench` → `FixtureAdapter` → scorer → manifest/results/report | `tcm-bench/`（产品仓库外独立目录） | `python -m pytest -q`：6 passed；`python -m compileall -q src` 通过 | 12 个 smoke case；fixture/replay 不代表 live 质量；真实 adapter 尚未接入 | 接入真实 Retrieval/MCP adapter，建立 BENCH-01 |
| UPG-01 | integrated | Web review contract → draft service → owner-scoped repository → persistence | `web/schema/review.py`、`web/service/review_service.py`、`web/repository/review.py` | `python -m pytest tests/web -q`：26 passed | 已有病例/报告草稿、引用关系、owner 隔离和不可变保存；尚未接入完整 Web UI | 继续 Run/事件生命周期与报告交付门禁 |
| UPG-02 | integrated | `EmbeddingManager` → `VectorStore` → Chroma build/server；manifest 生成入口 | `rag/embedding_contract.py`、`rag/embeddings.py`、`rag/vector_store.py`、`rag/index_manifest.py` | `python -m pytest tests -q`：113 passed；`python -m compileall -q src` 通过 | 错模型/错维度/零向量显式失败；现有 Chroma 未重建，未生成 active manifest | 在 active manifest 和真实索引就绪后重跑 BENCH-01 |
| BENCH-01 | blocked | `tcm-bench.bench01` → live retrieval adapter → active index manifest gate | `tcm-bench/datasets/retrieval-live.json`、`tcm-bench/src/tcm_bench/bench01.py` | run `live-retrieval-4730765a1df2`：4/4 blocked | 阻断原因：`data/chroma/index-manifest.json` 不存在；未将 fixture/TF-IDF 计入 live 成绩 | 在不覆盖旧索引的前提下构建 staging index，生成 active manifest 后重跑 |

状态没有写成 `verified` 的项目，不能当作业务验收完成。
