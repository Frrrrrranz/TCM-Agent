import readline from 'node:readline'
import type { ChatMessage, ModelAdapter } from './types.js'
import type { ToolRegistry } from './tool.js'
import type { PermissionManager } from './permissions.js'
import { runAgentTurn } from './agent-loop.js'
import { buildSystemPrompt } from './prompt.js'
import { createContextCollapseState } from './compact/context-collapse.js'
import { createContentReplacementState } from './utils/tool-result-storage.js'

interface JsonInput {
  type: 'user_message'
  content: string
  history?: ChatMessage[]
  history_context?: string
}

/**
 * 启动 JSON 协议服务器。
 * 通过标准输入按行读取指令，将 Agent 状态以流式 JSON 实时打印至标准输出。
 */
export async function runJsonModeServer(args: {
  cwd: string
  tools: ToolRegistry
  model: ModelAdapter
  permissions: PermissionManager
  runtime: any
}): Promise<void> {
  // 启动时立即输出 init 帧，向前端同步当前配置的实际模型名称
  console.log(JSON.stringify({ type: 'init', modelName: args.runtime?.model || 'Unknown Model' }))

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false,
  })

  // 内存备用消息历史（如果前端没有发送 history 字段）
  let memoryMessages: ChatMessage[] = [
    {
      role: 'system',
      content: await buildSystemPrompt(args.cwd, args.permissions.getSummary(), {
        skills: args.tools.getSkills(),
        mcpServers: args.tools.getMcpServers(),
      }),
    },
  ]

  const contextCollapseState = createContextCollapseState()
  const contentReplacementState = createContentReplacementState()

  for await (const line of rl) {
    if (!line.trim()) continue
    try {
      const input = JSON.parse(line) as JsonInput
      if (input.type === 'user_message') {
        let messages: ChatMessage[] = []
        if (input.history && input.history.length > 0) {
          messages = [...input.history]
        } else {
          messages = [...memoryMessages]
        }

        // 动态构建包含当前跨对话历史摘要的 System Prompt 并注入
        const systemPrompt = await buildSystemPrompt(args.cwd, args.permissions.getSummary(), {
          skills: args.tools.getSkills(),
          mcpServers: args.tools.getMcpServers(),
          historyContext: input.history_context,
        })
        if (messages.length > 0 && messages[0].role === 'system') {
          messages[0].content = systemPrompt
        } else {
          messages.unshift({ role: 'system', content: systemPrompt })
        }

        // 追加用户当前的消息
        messages.push({ role: 'user', content: input.content })

        args.permissions.beginTurn()

        try {
          const updatedMessages = await runAgentTurn({
            model: args.model,
            tools: args.tools,
            messages,
            cwd: args.cwd,
            permissions: args.permissions,
            modelName: args.runtime?.model ?? '',
            contentReplacementState,
            contextCollapseState,
            onToolStart: (toolName, toolInput) => {
              console.log(JSON.stringify({ type: 'tool_start', toolName, input: toolInput }))
            },
            onToolResult: (toolName, output, isError) => {
              console.log(JSON.stringify({ type: 'tool_result', toolName, output, isError }))
            },
            onAssistantMessage: (content) => {
              console.log(JSON.stringify({ type: 'assistant_message', content }))
            },
            onProgressMessage: (content) => {
              console.log(JSON.stringify({ type: 'progress_message', content }))
            },
          })

          memoryMessages = updatedMessages
          // 返回完成的消息列表，由前端进行会话持久化与状态同步
          console.log(JSON.stringify({ type: 'turn_complete', messages: updatedMessages }))
        } catch (err) {
          const errorMsg = err instanceof Error ? err.message : String(err)
          const errorMsgObj: ChatMessage = {
            role: 'assistant',
            content: `请求失败: ${errorMsg}`,
          }
          messages.push(errorMsgObj)
          memoryMessages = messages
          console.log(JSON.stringify({ type: 'error', content: errorMsg }))
          console.log(JSON.stringify({ type: 'turn_complete', messages }))
        } finally {
          args.permissions.endTurn()
        }
      }
    } catch (e) {
      console.log(
        JSON.stringify({
          type: 'error',
          content: `JSON 解析失败: ${e instanceof Error ? e.message : String(e)}`,
        })
      )
    }
  }
}
