# 现状请求调用图（UPG-00）

以下是基于当前源码入口的单次咨询路径记录。它是调用图和证据边界，不声称本轮已经调用 live 模型或真实数据库。

```text
Vue Web input
  → WebSocket / chat store
  → FastAPI web/api/chat.py
  → web/service/agent_service.py
  → Agent 子进程 `src/index.ts --json-mode`
  → json-server.ts
  → buildSystemPrompt + ToolRegistry + ModelAdapter
  → agent-loop.ts
  → OpenAI/Anthropic adapter
  → MCP tools / Python MCP server
  → tool result 回注 agent-loop
  → JSON protocol events
  → FastAPI/WebSocket
  → Vue chat/trace UI
```

## 入口证据

- CLI 与 JSON 模式入口：`src/index.ts`。
- JSON 请求解析、工具事件和终态：`src/json-server.ts`。
- Agent 循环：`src/agent-loop.ts`。
- 模型适配：`src/openai-adapter.ts`、`src/anthropic-adapter.ts`。
- 工具注册与 MCP hydration：`src/tools/index.ts`。
- Web 侧服务：`tcm-mcp-server/src/tcm_mcp_server/web/api/chat.py`、`web/service/agent_service.py`。
- 领域规则组件：`web/schema/domain.py`、`web/service/safety_gate.py`。

## 当前失败/不确定边界

1. `cancel_turn` 目前立即发送 `turn_cancelled`，但 JSON server 没有把请求绑定到可取消的正在运行任务；因此不能把该回执当作模型/工具已经停止。
2. `assistant_message` 事件固定带 `streaming: true`，而模型适配器当前以完整响应为主；真实首文本增量尚未证明。
3. 终态只暴露用户/助手消息，工具轨迹通过独立事件发送；重连、落账确认和迟到事件隔离尚未统一。
4. 领域 Pydantic 与安全函数存在，但当前基线没有证明普通咨询输出必经 `ConsultationResult` 和 fail-closed 校验。

这些边界进入后续 UPG-03/04/05 和 UPG-01，不在 S0 伪造为已修复。
