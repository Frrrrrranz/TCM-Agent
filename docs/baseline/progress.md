# 升级进度（S0）

| 任务 ID | 状态 | 实际调用路径 | 变更 diff | 验证命令 / runId | 结果与限制 | 下一步 |
| --- | --- | --- | --- | --- | --- | --- |
| UPG-00 | integrated | `src/index.ts` → JSON/Web/MCP 入口已记录 | `docs/baseline/` | `npm.cmd test`：207/207；`git diff --check` 通过 | 已冻结 HEAD、WIP 路径、调用图和失败边界；未调用 live 模型/索引 | 补齐运行时版本与单次受控请求 trace，进入 UPG-01 |
| BENCH-00 | verified | `tcm-bench` → `FixtureAdapter` → scorer → manifest/results/report | `tcm-bench/`（产品仓库外独立目录） | `python -m pytest -q`：6 passed；`python -m compileall -q src` 通过 | 12 个 smoke case；fixture/replay 不代表 live 质量；真实 adapter 尚未接入 | 接入真实 Retrieval/MCP adapter，建立 BENCH-01 |

状态没有写成 `verified` 的项目，不能当作业务验收完成。
