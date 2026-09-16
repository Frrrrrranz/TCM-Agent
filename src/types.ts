export type ProviderUsage = {
  inputTokens: number
  outputTokens: number
  totalTokens: number
  source: string
}

export type ProviderUsageMetadata = {
  providerUsage?: ProviderUsage
  usageStale?: boolean
  usageStaleReason?: string
}

export type ProviderThinkingBlock = {
  type: 'thinking' | 'redacted_thinking'
  [key: string]: unknown
}

export type MessageIdentity = {
  id?: string
}

export type ChatMessage =
  | ({ role: 'system'; content: string } & MessageIdentity)
  | ({ role: 'user'; content: string } & MessageIdentity)
  | ({ role: 'assistant_thinking'; blocks: ProviderThinkingBlock[] } & MessageIdentity)
  | ({ role: 'assistant'; content: string } & ProviderUsageMetadata & MessageIdentity)
  | ({ role: 'assistant_progress'; content: string } & ProviderUsageMetadata & MessageIdentity)
  | ({
      role: 'assistant_tool_call'
      toolUseId: string
      toolName: string
      input: unknown
    } & ProviderUsageMetadata & MessageIdentity)
  | ({
      role: 'tool_result'
      toolUseId: string
      toolName: string
      content: string
      isError: boolean
    } & MessageIdentity)
  | ({
      role: 'context_summary'
      content: string
      compressedCount: number
      timestamp: number
    } & MessageIdentity)
  | ({
      role: 'snip_boundary'
      content: string
      removedMessageIds: string[]
      removedCount: number
      tokensFreed: number
      timestamp: number
    } & MessageIdentity)

export type ToolCall = {
  id: string
  toolName: string
  input: unknown
}

export type StepDiagnostics = {
  stopReason?: string
  blockTypes?: string[]
  ignoredBlockTypes?: string[]
}

export type AgentStep =
  | {
      type: 'assistant'
      content: string
      kind?: 'final' | 'progress'
      thinkingBlocks?: ProviderThinkingBlock[]
      diagnostics?: StepDiagnostics
      usage?: ProviderUsage
    }
  | {
      type: 'tool_calls'
      calls: ToolCall[]
      content?: string
      contentKind?: 'progress'
      thinkingBlocks?: ProviderThinkingBlock[]
      diagnostics?: StepDiagnostics
      usage?: ProviderUsage
    }

export type ModelStreamEvent =
  | {
      type: 'text_delta'
      content: string
    }
  | {
      type: 'tool_argument_delta'
      index: number
      toolCallId?: string
      toolName?: string
      argumentsDelta: string
    }
  | {
      type: 'tool_call'
      index: number
      call: ToolCall
    }
  | {
      type: 'usage'
      usage: ProviderUsage
    }
  | {
      type: 'end'
      stopReason?: string
    }

export type ModelRequestOptions = {
  signal?: AbortSignal
  onEvent?: (event: ModelStreamEvent) => void
}

export interface ModelAdapter {
  next(
    messages: ChatMessage[],
    options?: ModelRequestOptions,
  ): Promise<AgentStep>
}

export type CompressionResult = {
  messages: ChatMessage[]
  summary: Extract<ChatMessage, { role: 'context_summary' }>
  removedCount: number
  tokensBefore: number
  tokensAfter: number
}
