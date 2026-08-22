import readline from 'node:readline'
import { randomUUID } from 'node:crypto'
import type { ChatMessage, ModelAdapter } from './types.js'
import type { ToolRegistry } from './tool.js'
import type { PermissionManager } from './permissions.js'
import { runAgentTurn } from './agent-loop.js'
import { buildSystemPrompt } from './prompt.js'
import { createContextCollapseState } from './compact/context-collapse.js'
import { createContentReplacementState } from './utils/tool-result-storage.js'
import {
  createProtocolFrame,
  JsonInputSchema,
  type JsonInput,
  type JsonOutput,
} from './json-protocol.js'

function toPublicMessages(messages: ChatMessage[]): Array<Record<string, unknown>> {
  return messages.flatMap(message => {
    if (message.role === 'user' || message.role === 'assistant') {
      return [{ role: message.role, content: message.content }]
    }
    return []
  })
}

export async function runJsonModeServer(args: {
  cwd: string
  tools: ToolRegistry
  model: ModelAdapter
  permissions: PermissionManager
  runtime: any
}): Promise<void> {
  let sequence = 0
  let currentSessionId: string | undefined
  let currentRequestId: string | undefined
  const completedRequestIds = new Set<string>()
  const toolUseIds = new Map<string, string[]>()

  const emit = (
    frame: Omit<JsonOutput, 'protocolVersion' | 'sequence' | 'timestamp'>,
  ): void => {
    const parsed = createProtocolFrame(frame, sequence++)
    console.log(JSON.stringify(parsed))
  }

  emit({ type: 'init', modelName: args.runtime?.model || 'Unknown Model' })

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false,
  })

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
      const input: JsonInput = JsonInputSchema.parse(JSON.parse(line))
      currentSessionId = input.sessionId
      currentRequestId = input.requestId

      if (input.type === 'heartbeat') {
        emit({
          type: 'heartbeat_ack',
          sessionId: input.sessionId,
          requestId: input.requestId,
        })
        continue
      }

      if (input.type === 'cancel_turn') {
        emit({
          type: 'turn_cancelled',
          sessionId: input.sessionId,
          requestId: input.requestId,
        })
        continue
      }

      if (completedRequestIds.has(input.requestId)) {
        emit({
          type: 'error',
          sessionId: input.sessionId,
          requestId: input.requestId,
          content: 'request_id_already_completed',
        })
        continue
      }

      const messages: ChatMessage[] = [...memoryMessages]
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
            const toolUseId = randomUUID()
            const pending = toolUseIds.get(toolName) ?? []
            pending.push(toolUseId)
            toolUseIds.set(toolName, pending)
            emit({
              type: 'tool_start',
              sessionId: input.sessionId,
              requestId: input.requestId,
              toolUseId,
              toolName,
              input: toolInput,
            })
          },
          onToolResult: (toolName, output, isError) => {
            const pending = toolUseIds.get(toolName) ?? []
            const toolUseId = pending.shift()
            if (pending.length === 0) toolUseIds.delete(toolName)
            else toolUseIds.set(toolName, pending)
            emit({
              type: 'tool_result',
              sessionId: input.sessionId,
              requestId: input.requestId,
              toolUseId,
              toolName,
              output,
              isError,
            })
          },
          onAssistantMessage: content => {
            emit({
              type: 'assistant_message',
              sessionId: input.sessionId,
              requestId: input.requestId,
              content,
              streaming: true,
            })
          },
          onProgressMessage: content => {
            emit({
              type: 'progress_message',
              sessionId: input.sessionId,
              requestId: input.requestId,
              content,
            })
          },
        })

        memoryMessages = updatedMessages
        completedRequestIds.add(input.requestId)
        emit({
          type: 'turn_complete',
          sessionId: input.sessionId,
          requestId: input.requestId,
          messages: toPublicMessages(updatedMessages),
          streaming: false,
        })
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error)
        messages.push({ role: 'assistant', content: `请求失败: ${errorMsg}` })
        memoryMessages = messages
        emit({
          type: 'error',
          sessionId: input.sessionId,
          requestId: input.requestId,
          content: 'agent_turn_failed',
        })
        emit({
          type: 'turn_complete',
          sessionId: input.sessionId,
          requestId: input.requestId,
          messages: toPublicMessages(messages),
          streaming: false,
        })
      } finally {
        args.permissions.endTurn()
      }
    } catch {
      emit({
        type: 'error',
        sessionId: currentSessionId,
        requestId: currentRequestId,
        content: 'invalid_protocol_message',
      })
    }
  }
}
