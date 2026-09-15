import readline from 'node:readline'
import { randomUUID } from 'node:crypto'
import type { ChatMessage, ModelAdapter } from './types.js'
import type { ToolRegistry } from './tool.js'
import type { PermissionManager } from './permissions.js'
import { runAgentTurn } from './agent-loop.js'
import { createDefaultRunBudget } from './run-budget.js'
import {
  isCancellationError,
  throwIfAborted,
} from './utils/cancellation.js'
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
  const pendingCancellationKeys = new Set<string>()
  const cancellationKey = (sessionId: string, requestId: string): string =>
    JSON.stringify([sessionId, requestId])

  let activeTurn: {
    sessionId: string
    requestId: string
    controller: AbortController
  } | undefined

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

  const requestCancellation = (
    input: Extract<JsonInput, { type: 'cancel_turn' }>,
  ): boolean => {
    if (completedRequestIds.has(input.requestId)) return true
    if (
      !activeTurn ||
      activeTurn.sessionId !== input.sessionId ||
      activeTurn.requestId !== input.requestId
    ) {
      return false
    }
    if (!activeTurn.controller.signal.aborted) {
      activeTurn.controller.abort()
      emit({
        type: 'cancel_requested',
        sessionId: input.sessionId,
        requestId: input.requestId,
      })
    }
    return true
  }

  rl.on('line', line => {
    try {
      const parsed = JsonInputSchema.safeParse(JSON.parse(line))
      if (parsed.success && parsed.data.type === 'cancel_turn') {
        const handled = requestCancellation(parsed.data)
        if (!handled) {
          pendingCancellationKeys.add(
            cancellationKey(parsed.data.sessionId, parsed.data.requestId),
          )
        }
      }
    } catch {
      // The main protocol loop emits the validation error for malformed input.
    }
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
        pendingCancellationKeys.delete(
          cancellationKey(input.sessionId, input.requestId),
        )
        if (!requestCancellation(input)) {
          emit({
            type: 'error',
            sessionId: input.sessionId,
            requestId: input.requestId,
            content: 'cancel_target_not_running',
          })
        }
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

      const turnController = new AbortController()
      activeTurn = {
        sessionId: input.sessionId,
        requestId: input.requestId,
        controller: turnController,
      }
      const messages: ChatMessage[] = [...memoryMessages]
      if (
        pendingCancellationKeys.delete(
          cancellationKey(input.sessionId, input.requestId),
        )
      ) {
        requestCancellation({
          protocolVersion: input.protocolVersion,
          type: 'cancel_turn',
          sessionId: input.sessionId,
          requestId: input.requestId,
          sequence: input.sequence,
        })
      }
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
          budget: createDefaultRunBudget(),
          signal: turnController.signal,
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

        throwIfAborted(turnController.signal)
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
        if (isCancellationError(error)) {
          completedRequestIds.add(input.requestId)
          emit({
            type: 'turn_cancelled',
            sessionId: input.sessionId,
            requestId: input.requestId,
          })
          continue
        }

        completedRequestIds.add(input.requestId)
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
        if (activeTurn?.requestId === input.requestId) {
          activeTurn = undefined
        }
      }
    } catch {
      if (activeTurn?.requestId === currentRequestId) {
        activeTurn = undefined
      }
      emit({
        type: 'error',
        sessionId: currentSessionId,
        requestId: currentRequestId,
        content: 'invalid_protocol_message',
      })
    }
  }
}
