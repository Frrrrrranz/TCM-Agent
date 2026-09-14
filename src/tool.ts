import { z } from 'zod'
import type { PermissionManager } from './permissions.js'
import type { SkillSummary } from './skills.js'
import type { McpServerSummary } from './mcp.js'

export type ToolContext = {
  cwd: string
  permissions?: PermissionManager
}

export type BackgroundTaskResult = {
  taskId: string
  type: 'local_bash'
  command: string
  pid: number
  status: 'running' | 'completed' | 'failed'
  startedAt: number
}

export type ToolErrorCode =
  | 'invalid_arguments'
  | 'forbidden'
  | 'transient'
  | 'timeout'
  | 'cancelled'
  | 'version_mismatch'
  | 'internal'

export type ToolFailure = {
  code: ToolErrorCode
  retryable: boolean
  message: string
}

export type ToolResult = {
  ok: boolean
  output: string
  error?: ToolFailure
  backgroundTask?: BackgroundTaskResult
  awaitUser?: boolean
}

export type ToolDefinition<TInput> = {
  name: string
  description: string
  inputSchema: Record<string, unknown>
  schema: z.ZodType<TInput>
  run(input: TInput, context: ToolContext): Promise<ToolResult>
}

type ToolRegistryMetadata = {
  skills?: SkillSummary[]
  mcpServers?: McpServerSummary[]
}

export function classifyToolFailure(message: string): ToolFailure {
  const normalized = message.toLowerCase()

  if (normalized.includes('abort') || normalized.includes('cancel')) {
    return { code: 'cancelled', retryable: false, message }
  }
  if (normalized.includes('timeout') || normalized.includes('timed out')) {
    return { code: 'timeout', retryable: true, message }
  }
  if (
    normalized.includes('429') ||
    normalized.includes('rate limit') ||
    normalized.includes('temporarily unavailable') ||
    normalized.includes('econnreset') ||
    normalized.includes('connection reset')
  ) {
    return { code: 'transient', retryable: true, message }
  }
  if (
    normalized.includes('forbidden') ||
    normalized.includes('permission denied') ||
    normalized.includes('not allowed') ||
    normalized.includes('unauthorized') ||
    normalized.includes('http 403')
  ) {
    return { code: 'forbidden', retryable: false, message }
  }
  if (
    normalized.includes('version mismatch') ||
    normalized.includes('stale version') ||
    normalized.includes('http 409')
  ) {
    return { code: 'version_mismatch', retryable: false, message }
  }

  return { code: 'internal', retryable: false, message }
}

export class ToolRegistry {
  private readonly toolsStore: ToolDefinition<unknown>[]
  private metadataStore: ToolRegistryMetadata
  private readonly disposers: Array<() => Promise<void>> = []

  constructor(
    tools: ToolDefinition<unknown>[],
    metadata: ToolRegistryMetadata = {},
    disposer?: () => Promise<void>,
  ) {
    this.toolsStore = [...tools]
    this.metadataStore = metadata
    if (disposer) {
      this.disposers.push(disposer)
    }
  }

  list(): ToolDefinition<unknown>[] {
    return this.toolsStore
  }

  getSkills(): SkillSummary[] {
    return this.metadataStore.skills ?? []
  }

  getMcpServers(): McpServerSummary[] {
    return this.metadataStore.mcpServers ?? []
  }

  setMcpServers(servers: McpServerSummary[]): void {
    this.metadataStore = {
      ...this.metadataStore,
      mcpServers: [...servers],
    }
  }

  addTools(nextTools: ToolDefinition<unknown>[]): void {
    const existingNames = new Set(this.toolsStore.map(tool => tool.name))
    for (const tool of nextTools) {
      if (existingNames.has(tool.name)) {
        continue
      }
      this.toolsStore.push(tool)
      existingNames.add(tool.name)
    }
  }

  addDisposer(disposer: () => Promise<void>): void {
    this.disposers.push(disposer)
  }

  find(name: string): ToolDefinition<unknown> | undefined {
    return this.toolsStore.find(tool => tool.name === name)
  }

  async execute(
    toolName: string,
    input: unknown,
    context: ToolContext,
  ): Promise<ToolResult> {
    const tool = this.find(toolName)
    if (!tool) {
      return {
        ok: false,
        output: `Unknown tool: ${toolName}`,
        error: {
          code: 'invalid_arguments',
          retryable: false,
          message: `Unknown tool: ${toolName}`,
        },
      }
    }

    const parsed = tool.schema.safeParse(input)
    if (!parsed.success) {
      return {
        ok: false,
        output: parsed.error.message,
        error: {
          code: 'invalid_arguments',
          retryable: false,
          message: parsed.error.message,
        },
      }
    }

    try {
      const result = await tool.run(parsed.data, context)
      if (result.ok || result.error) return result
      return {
        ...result,
        error: classifyToolFailure(result.output),
      }
    } catch (error) {
      const output = error instanceof Error ? error.message : String(error)
      return {
        ok: false,
        output,
        error: classifyToolFailure(output),
      }
    }
  }

  async dispose(): Promise<void> {
    await Promise.all(this.disposers.map(disposer => disposer()))
  }
}
