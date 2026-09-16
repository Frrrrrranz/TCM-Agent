import type {
  ModelStreamEvent,
  ProviderThinkingBlock,
  ProviderUsage,
  ToolCall,
} from './types.js'
import { readServerSentEvents } from './utils/sse.js'

type OpenAIToolAccumulator = {
  id: string
  name: string
  arguments: string
}

export type OpenAIStreamResult = {
  content: string
  reasoningContent: string
  toolCalls: ToolCall[]
  stopReason?: string
  usage?: ProviderUsage
}

function asRecord(value: unknown): Record<string, unknown> | undefined {
  return typeof value === 'object' && value !== null
    ? value as Record<string, unknown>
    : undefined
}

function parseToolInput(value: string): unknown {
  try {
    return JSON.parse(value) as unknown
  } catch {
    return value
  }
}

export async function parseOpenAIStream(
  response: Response,
  onEvent: (event: ModelStreamEvent) => void,
): Promise<OpenAIStreamResult> {
  let content = ''
  let reasoningContent = ''
  let stopReason: string | undefined
  let usage: ProviderUsage | undefined
  let finished = false
  const tools = new Map<number, OpenAIToolAccumulator>()

  for await (const payload of readServerSentEvents(response)) {
    if (payload === '[DONE]') {
      finished = true
      break
    }
    const frame = asRecord(JSON.parse(payload) as unknown)
    if (!frame) continue

    const usageFrame = asRecord(frame.usage)
    if (usageFrame) {
      const inputTokens = Number(usageFrame.prompt_tokens ?? 0)
      const outputTokens = Number(usageFrame.completion_tokens ?? 0)
      const totalTokens = Number(
        usageFrame.total_tokens ?? inputTokens + outputTokens,
      )
      if (totalTokens > 0) {
        usage = {
          inputTokens,
          outputTokens,
          totalTokens,
          source: 'openai',
        }
        onEvent({ type: 'usage', usage })
      }
    }

    const choices = Array.isArray(frame.choices) ? frame.choices : []
    const choice = asRecord(choices[0])
    if (!choice) continue
    if (typeof choice.finish_reason === 'string') {
      stopReason = choice.finish_reason
    }
    const delta = asRecord(choice.delta)
    if (!delta) continue

    if (typeof delta.content === 'string' && delta.content) {
      content += delta.content
      onEvent({ type: 'text_delta', content: delta.content })
    }
    if (
      typeof delta.reasoning_content === 'string' &&
      delta.reasoning_content
    ) {
      reasoningContent += delta.reasoning_content
    }

    const toolDeltas = Array.isArray(delta.tool_calls) ? delta.tool_calls : []
    for (const rawToolDelta of toolDeltas) {
      const toolDelta = asRecord(rawToolDelta)
      if (!toolDelta) continue
      const index = Number(toolDelta.index)
      if (!Number.isInteger(index) || index < 0) continue
      const current = tools.get(index) ?? { id: '', name: '', arguments: '' }
      if (typeof toolDelta.id === 'string') current.id += toolDelta.id
      const fn = asRecord(toolDelta.function)
      if (typeof fn?.name === 'string') current.name += fn.name
      if (typeof fn?.arguments === 'string') {
        current.arguments += fn.arguments
        onEvent({
          type: 'tool_argument_delta',
          index,
          toolCallId: current.id || undefined,
          toolName: current.name || undefined,
          argumentsDelta: fn.arguments,
        })
      }
      tools.set(index, current)
    }
  }

  if (!finished) throw new Error('OpenAI stream ended before [DONE]')

  const toolCalls = [...tools.entries()]
    .sort(([left], [right]) => left - right)
    .map(([index, tool]): ToolCall => {
      const call = {
        id: tool.id,
        toolName: tool.name,
        input: parseToolInput(tool.arguments),
      }
      onEvent({ type: 'tool_call', index, call })
      return call
    })
  onEvent({ type: 'end', stopReason })

  return { content, reasoningContent, toolCalls, stopReason, usage }
}

type AnthropicStreamBlock =
  | { type: 'text'; text: string }
  | { type: 'tool_use'; id: string; name: string; input: unknown }
  | ProviderThinkingBlock

export type AnthropicStreamResult = {
  content: AnthropicStreamBlock[]
  stopReason?: string
  usage?: ProviderUsage
}

export async function parseAnthropicStream(
  response: Response,
  onEvent: (event: ModelStreamEvent) => void,
): Promise<AnthropicStreamResult> {
  const blocks = new Map<number, Record<string, unknown>>()
  let inputTokens = 0
  let outputTokens = 0
  let stopReason: string | undefined
  let finished = false

  for await (const payload of readServerSentEvents(response)) {
    const frame = asRecord(JSON.parse(payload) as unknown)
    if (!frame || typeof frame.type !== 'string') continue

    if (frame.type === 'error') {
      throw new Error('Anthropic stream reported an error')
    }
    if (frame.type === 'message_stop') {
      finished = true
      break
    }
    if (frame.type === 'message_start') {
      const message = asRecord(frame.message)
      const rawUsage = asRecord(message?.usage)
      inputTokens = Number(rawUsage?.input_tokens ?? inputTokens)
      continue
    }
    if (frame.type === 'content_block_start') {
      const index = Number(frame.index)
      const block = asRecord(frame.content_block)
      if (Number.isInteger(index) && index >= 0 && block) {
        blocks.set(index, { ...block, partialJson: '' })
      }
      continue
    }
    if (frame.type === 'content_block_delta') {
      const index = Number(frame.index)
      const block = blocks.get(index)
      const delta = asRecord(frame.delta)
      if (!block || !delta) continue
      if (delta.type === 'text_delta' && typeof delta.text === 'string') {
        block.text = String(block.text ?? '') + delta.text
        onEvent({ type: 'text_delta', content: delta.text })
      } else if (
        delta.type === 'input_json_delta' &&
        typeof delta.partial_json === 'string'
      ) {
        block.partialJson = String(block.partialJson ?? '') + delta.partial_json
        onEvent({
          type: 'tool_argument_delta',
          index,
          toolCallId: typeof block.id === 'string' ? block.id : undefined,
          toolName: typeof block.name === 'string' ? block.name : undefined,
          argumentsDelta: delta.partial_json,
        })
      } else if (
        delta.type === 'thinking_delta' &&
        typeof delta.thinking === 'string'
      ) {
        block.thinking = String(block.thinking ?? '') + delta.thinking
      } else if (
        delta.type === 'signature_delta' &&
        typeof delta.signature === 'string'
      ) {
        block.signature = String(block.signature ?? '') + delta.signature
      }
      continue
    }
    if (frame.type === 'message_delta') {
      const delta = asRecord(frame.delta)
      if (typeof delta?.stop_reason === 'string') stopReason = delta.stop_reason
      const rawUsage = asRecord(frame.usage)
      outputTokens = Number(rawUsage?.output_tokens ?? outputTokens)
    }
  }

  if (!finished) throw new Error('Anthropic stream ended before message_stop')

  const content = [...blocks.entries()]
    .sort(([left], [right]) => left - right)
    .map(([index, block]): AnthropicStreamBlock | undefined => {
      if (block.type === 'text') {
        return { type: 'text', text: String(block.text ?? '') }
      }
      if (
        block.type === 'tool_use' &&
        typeof block.id === 'string' &&
        typeof block.name === 'string'
      ) {
        const partialJson = String(block.partialJson ?? '')
        const call: ToolCall = {
          id: block.id,
          toolName: block.name,
          input: partialJson ? parseToolInput(partialJson) : block.input,
        }
        onEvent({ type: 'tool_call', index, call })
        return { type: 'tool_use', id: call.id, name: call.toolName, input: call.input }
      }
      if (block.type === 'thinking' || block.type === 'redacted_thinking') {
        const { partialJson: _partialJson, ...thinkingBlock } = block
        return thinkingBlock as ProviderThinkingBlock
      }
      return undefined
    })
    .filter((block): block is AnthropicStreamBlock => block !== undefined)

  const totalTokens = inputTokens + outputTokens
  const usage = totalTokens > 0
    ? { inputTokens, outputTokens, totalTokens, source: 'anthropic' }
    : undefined
  if (usage) onEvent({ type: 'usage', usage })
  onEvent({ type: 'end', stopReason })
  return { content, stopReason, usage }
}
