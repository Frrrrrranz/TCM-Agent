export type RunBudgetLimits = {
  modelCalls?: number
  toolCalls?: number
  tokens?: number
  wallClockMs?: number
  retries?: number
  maxDepth?: number
  concurrency?: number
  noProgressRepeats?: number
}

export type RunBudgetStopReason =
  | 'model_call_budget_exhausted'
  | 'tool_call_budget_exhausted'
  | 'token_budget_exhausted'
  | 'wall_clock_budget_exhausted'
  | 'retry_budget_exhausted'
  | 'depth_budget_exhausted'
  | 'concurrency_budget_exhausted'
  | 'no_progress'

export type RunBudgetSnapshot = {
  modelCalls: number
  toolCalls: number
  tokens: number
  retries: number
  activeCalls: number
  peakConcurrency: number
  noProgressRepeats: number
  elapsedMs: number
  estimatedTokenMeasurements: number
  stopReason?: RunBudgetStopReason
}

export const DEFAULT_RUN_BUDGET_LIMITS: Readonly<Required<RunBudgetLimits>> = {
  modelCalls: 24,
  toolCalls: 48,
  tokens: 200_000,
  wallClockMs: 10 * 60 * 1000,
  retries: 5,
  maxDepth: 1,
  concurrency: 1,
  noProgressRepeats: 3,
}

type RunBudgetOptions = {
  now?: () => number
}

function stableSerialize(value: unknown): string {
  if (value === null) return 'null'
  if (typeof value === 'string') return JSON.stringify(value)
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) return `[${value.map(stableSerialize).join(',')}]`
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, entry]) => `${JSON.stringify(key)}:${stableSerialize(entry)}`)
    return `{${entries.join(',')}}`
  }
  return JSON.stringify(String(value))
}

export class RunBudget {
  private readonly limits: RunBudgetLimits
  private readonly now: () => number
  private readonly startedAt: number
  private modelCalls = 0
  private toolCalls = 0
  private tokens = 0
  private retries = 0
  private activeCalls = 0
  private peakConcurrency = 0
  private noProgressRepeats = 0
  private estimatedTokenMeasurements = 0
  private stopReason: RunBudgetStopReason | undefined
  private lastOutcomeFingerprint: string | undefined

  constructor(limits: RunBudgetLimits, options: RunBudgetOptions = {}) {
    for (const [name, value] of Object.entries(limits)) {
      const minimum = name === 'maxDepth' ? 0 : 1
      if (value !== undefined && (!Number.isInteger(value) || value < minimum)) {
        throw new Error(`${name} must be an integer greater than or equal to ${minimum}`)
      }
    }
    this.limits = { ...limits }
    this.now = options.now ?? Date.now
    this.startedAt = this.now()
  }

  beforeModelCall(): RunBudgetStopReason | undefined {
    const stopped = this.checkStoppedOrElapsed()
    if (stopped) return stopped
    if (this.isExhausted(this.modelCalls, this.limits.modelCalls)) {
      return this.stop('model_call_budget_exhausted')
    }
    this.modelCalls += 1
    return undefined
  }

  reserveToolCall(): RunBudgetStopReason | undefined {
    const stopped = this.checkStoppedOrElapsed()
    if (stopped) return stopped
    if (this.isExhausted(this.toolCalls, this.limits.toolCalls)) {
      return this.stop('tool_call_budget_exhausted')
    }
    if (this.isExhausted(this.activeCalls, this.limits.concurrency)) {
      return this.stop('concurrency_budget_exhausted')
    }
    this.toolCalls += 1
    this.activeCalls += 1
    this.peakConcurrency = Math.max(this.peakConcurrency, this.activeCalls)
    return undefined
  }

  releaseToolCall(): void {
    this.activeCalls = Math.max(0, this.activeCalls - 1)
  }

  recordTokenUsage(tokens: number, estimated = false): RunBudgetStopReason | undefined {
    if (!Number.isFinite(tokens) || tokens < 0) {
      throw new Error('tokens must be a finite non-negative number')
    }
    if (this.stopReason) return this.stopReason
    this.tokens += Math.ceil(tokens)
    if (estimated) this.estimatedTokenMeasurements += 1
    if (this.limits.tokens !== undefined && this.tokens >= this.limits.tokens) {
      return this.stop('token_budget_exhausted')
    }
    return this.checkElapsed()
  }

  consumeRetry(): RunBudgetStopReason | undefined {
    const stopped = this.checkStoppedOrElapsed()
    if (stopped) return stopped
    if (this.isExhausted(this.retries, this.limits.retries)) {
      return this.stop('retry_budget_exhausted')
    }
    this.retries += 1
    return undefined
  }

  validateDepth(depth: number): RunBudgetStopReason | undefined {
    const stopped = this.checkStoppedOrElapsed()
    if (stopped) return stopped
    if (!Number.isInteger(depth) || depth < 0) {
      throw new Error('depth must be a non-negative integer')
    }
    if (this.limits.maxDepth !== undefined && depth > this.limits.maxDepth) {
      return this.stop('depth_budget_exhausted')
    }
    return undefined
  }

  recordToolOutcome(
    toolName: string,
    input: unknown,
    output: string,
  ): RunBudgetStopReason | undefined {
    if (this.stopReason) return this.stopReason
    const fingerprint = `${toolName}:${stableSerialize(input)}:${stableSerialize(output)}`
    this.noProgressRepeats = fingerprint === this.lastOutcomeFingerprint
      ? this.noProgressRepeats + 1
      : 1
    this.lastOutcomeFingerprint = fingerprint
    const threshold = this.limits.noProgressRepeats
    if (threshold !== undefined && this.noProgressRepeats >= threshold) {
      return this.stop('no_progress')
    }
    return this.checkElapsed()
  }

  snapshot(): RunBudgetSnapshot {
    return {
      modelCalls: this.modelCalls,
      toolCalls: this.toolCalls,
      tokens: this.tokens,
      retries: this.retries,
      activeCalls: this.activeCalls,
      peakConcurrency: this.peakConcurrency,
      noProgressRepeats: this.noProgressRepeats,
      elapsedMs: Math.max(0, this.now() - this.startedAt),
      estimatedTokenMeasurements: this.estimatedTokenMeasurements,
      ...(this.stopReason ? { stopReason: this.stopReason } : {}),
    }
  }

  private checkStoppedOrElapsed(): RunBudgetStopReason | undefined {
    return this.stopReason ?? this.checkElapsed()
  }

  private checkElapsed(): RunBudgetStopReason | undefined {
    const limit = this.limits.wallClockMs
    if (limit !== undefined && this.now() - this.startedAt >= limit) {
      return this.stop('wall_clock_budget_exhausted')
    }
    return undefined
  }

  private stop(reason: RunBudgetStopReason): RunBudgetStopReason {
    this.stopReason = this.stopReason ?? reason
    return this.stopReason
  }

  private isExhausted(used: number, limit: number | undefined): boolean {
    return limit !== undefined && used >= limit
  }
}

export function createDefaultRunBudget(): RunBudget {
  return new RunBudget(DEFAULT_RUN_BUDGET_LIMITS)
}
