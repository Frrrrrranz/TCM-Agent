# S0 失败例与限制

| 编号 | 失败/限制 | 复现入口 | 当前影响 | 计划归属 |
| --- | --- | --- | --- | --- |
| F-001 | 取消回执不等于底层调用已停止 | JSON `cancel_turn` 分支 | 可能出现迟到结果或新调用 | UPG-04/05 |
| F-002 | 完整响应路径被标记为 streaming | `json-server.ts` assistant event | 首可见文本和真实流式能力不可测 | UPG-04 |
| F-003 | 业务终止条件没有统一总预算 | `agent-loop.ts` 主入口 | 重复工具结果、超时和空响应的退出证据不足 | UPG-03 |
| F-004 | 角色文件存在但未接通实际审查工作流 | `src/agents/tcm-experts.ts` | 不能宣称三 Agent 已完成 | UPG-06 |
| F-005 | 规则组件存在但真实输出路径未完成验收 | `web/schema/domain.py` | 不能把组件单测当作发布门禁 | UPG-01 |
| F-006 | live 模型、真实索引和医学标注尚未纳入 smoke | 当前 S0 范围 | fixture 通过不等于领域质量通过 | BENCH-01/03 |
