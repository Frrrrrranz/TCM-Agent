import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { z } from 'zod'
import { runAgentTurn } from '../src/agent-loop.js'
import { RunBudget } from '../src/run-budget.js'
import { ToolRegistry } from '../src/tool.js'
import type { AgentStep, ModelAdapter } from '../src/types.js'

function createToolThenFinalModel(): ModelAdapter {
  let modelCalls = 0
  return {
    async next(): Promise<AgentStep> {
      modelCalls += 1
      if (modelCalls === 1) {
        return {
          type: 'tool_calls',
          calls: [{ id: 'call-1', toolName: 'lookup', input: {} }],
        }
      }
      return { type: 'assistant', content: 'done' }
    },
  }
}

describe('runAgentTurn tool retry policy', () => {
  it('retries a transient failure only for an idempotent-safe tool', async () => {
    let attempts = 0
    const tools = new ToolRegistry([
      {
        name: 'lookup',
        description: 'Safe lookup.',
        inputSchema: { type: 'object' },
        schema: z.object({}),
        execution: {
          idempotency: 'safe',
          maxRetries: 2,
          retryBackoffMs: 0,
        },
        async run() {
          attempts += 1
          return attempts === 1
            ? { ok: false, output: 'HTTP 429 rate limit' }
            : { ok: true, output: 'ok' }
        },
      },
    ])
    const budget = new RunBudget({
      modelCalls: 5,
      toolCalls: 5,
      tokens: 10_000,
      wallClockMs: 10_000,
      retries: 2,
      maxDepth: 0,
      concurrency: 1,
      noProgressRepeats: 3,
    })

    const result = await runAgentTurn({
      model: createToolThenFinalModel(),
      tools,
      messages: [{ role: 'user', content: 'test' }],
      cwd: process.cwd(),
      budget,
    })

    assert.equal(attempts, 2)
    assert.equal(budget.snapshot().toolCalls, 2)
    assert.equal(budget.snapshot().retries, 1)
    assert.equal(result.at(-1)?.role, 'assistant')
    assert.equal(result.at(-1)?.role === 'assistant' ? result.at(-1).content : '', 'done')
  })

  it('does not retry a tool with unknown idempotency', async () => {
    let attempts = 0
    const tools = new ToolRegistry([
      {
        name: 'lookup',
        description: 'Unknown side effects.',
        inputSchema: { type: 'object' },
        schema: z.object({}),
        async run() {
          attempts += 1
          return { ok: false, output: 'HTTP 429 rate limit' }
        },
      },
    ])
    const budget = new RunBudget({ retries: 2 })

    await runAgentTurn({
      model: createToolThenFinalModel(),
      tools,
      messages: [{ role: 'user', content: 'test' }],
      cwd: process.cwd(),
      budget,
    })

    assert.equal(attempts, 1)
    assert.equal(budget.snapshot().retries, 0)
  })

  it('hard-stops when retry budget is exhausted', async () => {
    let attempts = 0
    const tools = new ToolRegistry([
      {
        name: 'lookup',
        description: 'Always transiently fails.',
        inputSchema: { type: 'object' },
        schema: z.object({}),
        execution: {
          idempotency: 'safe',
          maxRetries: 3,
          retryBackoffMs: 0,
        },
        async run() {
          attempts += 1
          return { ok: false, output: `HTTP 429 rate limit attempt ${attempts}` }
        },
      },
    ])
    const budget = new RunBudget({
      modelCalls: 5,
      toolCalls: 5,
      retries: 1,
      noProgressRepeats: 3,
    })

    const result = await runAgentTurn({
      model: createToolThenFinalModel(),
      tools,
      messages: [{ role: 'user', content: 'test' }],
      cwd: process.cwd(),
      budget,
    })

    assert.equal(attempts, 2)
    assert.equal(budget.snapshot().stopReason, 'retry_budget_exhausted')
    assert.match(
      result.at(-1)?.role === 'assistant' ? result.at(-1).content : '',
      /返工重试预算/,
    )
  })
})
