# TCM-Agent 架构

## 设计目标

TCM-Agent 的目标是把通用 Agent 推理循环与中医药领域知识、可追溯数据检索和安全规则组合成一个可验证的辅助分析系统。工程上优先保证：证据可追溯、工具调用可观察、会话可恢复、失败可降级、医疗边界明确。

## 组件

### Agent 运行时

`src/agent-loop.ts` 驱动模型与工具的多轮循环。模型适配器位于 `src/anthropic-adapter.ts` 和 `src/openai-adapter.ts`；`src/tool.ts` 与 `src/tools/` 管理工具注册和执行；`src/permissions.ts` 负责工作区外访问及高风险命令确认。

系统提示由 `src/prompt.ts` 构建，并加载：

- 根目录 `TCM-AGENT.md`；
- 祖先目录的 `TCM-AGENT.md`、`TCM-AGENT.local.md`；
- `.tcm-agent/rules/*.md`；
- `.tcm-agent/skills/*/SKILL.md`；
- 可选的 Claude 指令与技能兼容目录。

运行时数据统一存放在 `~/.tcm-agent/`，可用 `TCM_AGENT_HOME` 覆盖。这里包括配置、权限、会话、历史、MCP token、协议缓存和超大工具结果。

### 中医领域层

`TCM-AGENT.md` 定义角色、安全边界和回答结构；`.tcm-agent/rules/` 提供辨证、中药、方剂和安全规则；`.tcm-agent/skills/` 描述标准工作流。领域层是提示与流程约束，不代替数据工具的事实校验。

### MCP 数据引擎

`tcm-mcp-server/src/tcm_mcp_server/` 提供中药、方剂、证候、穴位、医案和配伍检查工具。结构化查询使用 SQLite，语义召回使用 ChromaDB 与嵌入模型。项目根目录 `.mcp.json` 通过 stdio 将数据引擎挂载到 Agent。

### Web 工作台

`tcm-mcp-server/src/tcm_mcp_server/web/` 是 FastAPI 网关，通过子进程 JSON 模式连接 Agent；`web/` 是 Vue 3 前端，通过 WebSocket 接收增量文本、工具调用和状态事件。

## 关键数据流

```text
用户问题
  → 领域提示与会话上下文
  → 模型决定回答或调用工具
  → MCP 结构化查询 / RAG / 安全检查
  → 工具结果回注模型
  → 带依据、限制和风险提示的回答
```

## 当前工程重点

- 固化浏览器会话 ID，并保证历史消息与实时消息语义一致。
- 收紧 Web 网关的鉴权、CORS、子进程启动和错误暴露。
- 限制面向医疗用户的通用编码工具，建立领域工具白名单。
- 修复 RAG 路径和模型初始化一致性，补充真实检索评测集。
- 增加端到端测试，验证 WebSocket、工具事件、恢复会话与失败降级。

这些事项的执行计划记录在仓库外层 `.agents/plan.md`，避免把协作过程文件混入干净 Git 仓库。
