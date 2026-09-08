# 能力状态清单（UPG-00）

状态含义：`implemented` 仅表示代码或组件存在；`integrated` 表示主链路可达；`verified` 还要求有聚焦测试或 bench/trace 证据。本清单不把静态组件存在误报成业务完成。

| 能力 | 当前入口 | 状态 | 基线证据 | 主要缺口 |
| --- | --- | --- | --- | --- |
| CLI Agent loop | `src/index.ts` → `runAgentTurn` → `src/agent-loop.ts` | implemented | 代码入口存在 | 业务预算、无进展和完成条件未统一 |
| JSON 协议 | `src/index.ts --json-mode` → `src/json-server.ts` | implemented | `request/response` 协议代码存在 | cancel 当前只回执，未贯通正在运行的调用 |
| WebSocket 网关 | `web/src` → FastAPI web service → JSON 子进程 | implemented | 架构与 Web service 入口存在 | 需要实测首帧、迟到帧、取消和恢复 |
| 模型适配 | `src/openai-adapter.ts` / `src/anthropic-adapter.ts` | implemented | 双适配器存在 | 增量参数、AbortSignal、能力契约未闭环 |
| MCP/RAG 查询 | `.mcp.json` → Python MCP server | implemented | MCP 工具和 RAG 目录存在 | 真实 embedding、索引版本和引用定位需验证 |
| 领域规则 | `web/schema/domain.py` + `web/service/safety_gate.py` | implemented | Pydantic 规则组件存在 | 尚未证明所有输出路径强制经过规则 |
| 病例/报告版本 | 当前未见统一 Case/Run/Report 主链路 | planned | 本轮仅记录缺口 | 需要版本契约和草稿/复核状态 |
| 三角色审查 | `src/agents/tcm-experts.ts`、`call-teammate.ts` | implemented | 角色提示与隔离调用存在 | 尚未接入真实工具 Loop、父子生命周期和预算 |
| tcm-bench fixture | `../tcm-bench/src/tcm_bench` | integrated | 12 smoke cases、结果和报告产物 | 尚非真实模型/检索评测 |
| 历史全链路验收 | 无本轮证据 | planned | 历史数量不作为当前证明 | 需按 S0/S1 重新运行并保存 trace |
