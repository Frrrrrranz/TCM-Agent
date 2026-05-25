import type { ToolRegistry } from './tool.js'
import type {
  ChatMessage,
  ModelAdapter,
  ProviderThinkingBlock,
  ProviderUsage,
  StepDiagnostics,
  ToolCall,
} from './types.js'
import type { RuntimeConfig } from './config.js'
import { resolveMaxOutputTokens } from './utils/context.js'

const DEFAULT_MAX_RETRIES = 4
const BASE_RETRY_DELAY_MS = 500
const MAX_RETRY_DELAY_MS = 8_000

// ── OpenAI 请求/响应类型定义 ──────────────────────────────────────────────────

type OpenAISystemMessage = { role: 'system'; content: string }
type OpenAIUserMessage = { role: 'user'; content: string }
type OpenAIAssistantMessage = {
  role: 'assistant'
  content: string | null
  tool_calls?: OpenAIToolCall[]
}
type OpenAIToolMessage = { role: 'tool'; tool_call_id: string; content: string }

type OpenAIMessage =
  | OpenAISystemMessage
  | OpenAIUserMessage
  | OpenAIAssistantMessage
  | OpenAIToolMessage

type OpenAIToolCall = {
  id: string
  type: 'function'
  function: {
    name: string
    arguments: string
  }
}

type OpenAIUsage = {
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens?: number
}

type OpenAIResponseMessage = {
  role: string
  content: string | null
  tool_calls?: OpenAIToolCall[]
  // NOTE: DeepSeek 独有的推理链字段，用于判断模型是否依赖外部工具
  reasoning_content?: string
}

type OpenAIResponse = {
  choices?: Array<{
    message?: OpenAIResponseMessage
    finish_reason?: string
  }>
  usage?: OpenAIUsage
  error?: { message?: string } | string
}

// ── 重试工具函数（与 anthropic-adapter 保持一致）─────────────────────────────

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => {
    setTimeout(resolve, Math.max(0, ms))
  })
}

function getRetryLimit(): number {
  const value = Number(process.env.MINI_CODE_MAX_RETRIES)
  if (!Number.isFinite(value) || value < 0) {
    return DEFAULT_MAX_RETRIES
  }
  return Math.floor(value)
}

function shouldRetryStatus(status: number): boolean {
  return status === 429 || (status >= 500 && status < 600)
}

function parseRetryAfterMs(retryAfter: string | null): number | null {
  if (!retryAfter) return null
  const asSeconds = Number(retryAfter)
  if (Number.isFinite(asSeconds) && asSeconds >= 0) {
    return Math.floor(asSeconds * 1000)
  }
  const at = Date.parse(retryAfter)
  if (!Number.isFinite(at)) return null
  return Math.max(0, at - Date.now())
}

function getRetryDelayMs(attempt: number, retryAfterMs: number | null): number {
  if (retryAfterMs !== null) return retryAfterMs
  const base = Math.min(
    BASE_RETRY_DELAY_MS * Math.pow(2, Math.max(0, attempt - 1)),
    MAX_RETRY_DELAY_MS,
  )
  const jitter = Math.random() * 0.25 * base
  return Math.floor(base + jitter)
}

async function readJsonBody(response: Response): Promise<unknown> {
  const text = await response.text()
  if (!text.trim()) return {}
  try {
    return JSON.parse(text)
  } catch {
    return { error: { message: text.trim() } }
  }
}

function extractErrorMessage(data: unknown, status: number): string {
  if (typeof data === 'string' && data.trim()) return data.trim()

  if (
    typeof data === 'object' &&
    data !== null &&
    'error' in data &&
    typeof (data as Record<string, unknown>).error === 'object' &&
    (data as Record<string, unknown>).error !== null
  ) {
    const err = (data as Record<string, unknown>).error as Record<string, unknown>
    if (typeof err.message === 'string' && err.message.trim()) {
      return err.message.trim()
    }
  }

  if (
    typeof data === 'object' &&
    data !== null &&
    'error' in data &&
    typeof (data as Record<string, unknown>).error === 'string'
  ) {
    const errStr = (data as Record<string, unknown>).error as string
    if (errStr.trim()) return errStr.trim()
  }

  return `Model request failed: ${status}`
}

// ── 消息格式转换：内部格式 → OpenAI 格式 ────────────────────────────────────

function toOpenAIMessages(messages: ChatMessage[]): OpenAIMessage[] {
  const result: OpenAIMessage[] = []
  // 收集连续的 assistant_tool_call，合并为单条 OpenAI assistant 消息
  let pendingToolCalls: OpenAIToolCall[] = []

  function flushPendingToolCalls(): void {
    if (pendingToolCalls.length === 0) return
    result.push({
      role: 'assistant',
      content: null,
      tool_calls: pendingToolCalls,
    })
    pendingToolCalls = []
  }

  for (const message of messages) {
    // FIXME: 多工具并行调用时，内部格式将它们拆成多条 assistant_tool_call。
    // OpenAI 要求同一轮的所有 tool_calls 合并在一条 assistant 消息里，
    // 因此这里做批量收集，遇到非 tool_call 时才 flush。
    if (message.role === 'assistant_tool_call') {
      pendingToolCalls.push({
        id: message.toolUseId,
        type: 'function',
        function: {
          name: message.toolName,
          arguments: JSON.stringify(message.input),
        },
      })
      continue
    }

    // tool_result 不触发 flush，因为它必须紧跟在 assistant tool_calls 之后
    if (message.role !== 'tool_result') {
      flushPendingToolCalls()
    }

    switch (message.role) {
      case 'system':
        result.push({ role: 'system', content: message.content })
        break

      case 'user':
        result.push({ role: 'user', content: message.content })
        break

      case 'assistant':
      case 'assistant_progress':
        result.push({ role: 'assistant', content: message.content })
        break

      case 'assistant_thinking':
        // NOTE: OpenAI 接口不接受 thinking 块回传，直接跳过。
        // DeepSeek 的推理链仅用于展示，不需要送回模型。
        break

      case 'tool_result':
        result.push({
          role: 'tool',
          tool_call_id: message.toolUseId,
          content: message.content,
        })
        break

      case 'context_summary':
        result.push({
          role: 'user',
          content: `[Context Summary from earlier conversation]\n${message.content}`,
        })
        break

      case 'snip_boundary':
        result.push({
          role: 'user',
          content: '[Earlier context was removed to manage context length]',
        })
        break
    }
  }

  flushPendingToolCalls()
  return result
}

// ── 工具格式转换：ToolRegistry → OpenAI tools 数组 ──────────────────────────

function toOpenAITools(
  tools: ToolRegistry,
): Array<{ type: 'function'; function: { name: string; description: string; parameters: unknown } }> {
  return tools.list().map(tool => ({
    type: 'function' as const,
    function: {
      name: tool.name,
      description: tool.description,
      // NOTE: Anthropic 用 input_schema，OpenAI 用 parameters，结构相同（JSON Schema）
      parameters: tool.inputSchema,
    },
  }))
}

// ── 用量标准化 ───────────────────────────────────────────────────────────────

function normalizeOpenAIUsage(usage: OpenAIUsage | undefined): ProviderUsage | undefined {
  if (!usage) return undefined
  const inputTokens = usage.prompt_tokens ?? 0
  const outputTokens = usage.completion_tokens ?? 0
  const totalTokens = usage.total_tokens ?? (inputTokens + outputTokens)
  if (totalTokens <= 0) return undefined
  return { inputTokens, outputTokens, totalTokens, source: 'openai' }
}

// ── 主适配器类 ───────────────────────────────────────────────────────────────

export class OpenAIModelAdapter implements ModelAdapter {
  constructor(
    private readonly tools: ToolRegistry,
    private readonly getRuntimeConfig: () => Promise<RuntimeConfig>,
  ) {}

  async next(messages: ChatMessage[]): Promise<import('./types.js').AgentStep> {
    const runtime = await this.getRuntimeConfig()
    const openAIMessages = toOpenAIMessages(messages)
    const url = `${runtime.baseUrl.replace(/\/$/, '')}/v1/chat/completions`
    const maxOutputTokens = resolveMaxOutputTokens(runtime.model, runtime.maxOutputTokens)
    const openAITools = toOpenAITools(this.tools)

    const headers: Record<string, string> = {
      'content-type': 'application/json',
    }

    // NOTE: OpenAI 兼容接口统一用 Bearer Token，不区分 authToken 和 apiKey
    if (runtime.authToken) {
      headers.Authorization = `Bearer ${runtime.authToken}`
    } else if (runtime.apiKey) {
      headers.Authorization = `Bearer ${runtime.apiKey}`
    }

    const requestBody: Record<string, unknown> = {
      model: runtime.model,
      messages: openAIMessages,
      max_tokens: maxOutputTokens,
    }

    // 只有存在可用工具时才传入 tools 字段，避免空数组导致某些 API 报错
    if (openAITools.length > 0) {
      requestBody.tools = openAITools
      requestBody.tool_choice = 'auto'
    }

    const maxRetries = getRetryLimit()
    let response: Response | null = null

    for (let attempt = 0; attempt <= maxRetries; attempt += 1) {
      response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(requestBody),
      })
      if (response.ok) break
      if (!shouldRetryStatus(response.status) || attempt >= maxRetries) break
      const retryAfterMs = parseRetryAfterMs(response.headers.get('retry-after'))
      await sleep(getRetryDelayMs(attempt + 1, retryAfterMs))
    }

    if (!response) {
      throw new Error('Model request failed before receiving a response')
    }

    const data = (await readJsonBody(response)) as OpenAIResponse

    if (!response.ok) {
      throw new Error(extractErrorMessage(data, response.status))
    }

    const choice = data.choices?.[0]
    const responseMessage = choice?.message
    const finishReason = choice?.finish_reason
    const usage = normalizeOpenAIUsage(data.usage)

    // NOTE: 将 DeepSeek 的 reasoning_content（推理链）映射为 thinkingBlocks。
    // 这样在 TUI 中可以与 Claude 的 thinking block 使用同一渲染逻辑，
    // 方便用户判断模型是否通过 MCP 工具获取信息，而非依赖内部知识库。
    const thinkingBlocks: ProviderThinkingBlock[] = []
    if (
      responseMessage?.reasoning_content &&
      typeof responseMessage.reasoning_content === 'string' &&
      responseMessage.reasoning_content.trim()
    ) {
      thinkingBlocks.push({
        type: 'thinking',
        thinking: responseMessage.reasoning_content,
      })
    }

    const diagnostics: StepDiagnostics = {
      stopReason: finishReason,
    }

    const rawToolCalls = responseMessage?.tool_calls ?? []

    if (rawToolCalls.length > 0) {
      const calls: ToolCall[] = rawToolCalls.map(tc => ({
        id: tc.id,
        toolName: tc.function.name,
        input: (() => {
          try {
            return JSON.parse(tc.function.arguments) as unknown
          } catch {
            // FIXME: 如果模型返回了格式错误的 arguments，返回原始字符串作为降级处理
            return tc.function.arguments
          }
        })(),
      }))

      return {
        type: 'tool_calls',
        calls,
        content: responseMessage?.content ?? undefined,
        thinkingBlocks,
        diagnostics,
        usage,
      }
    }

    const content = responseMessage?.content ?? ''

    return {
      type: 'assistant',
      content,
      thinkingBlocks,
      diagnostics,
      usage,
    }
  }
}
