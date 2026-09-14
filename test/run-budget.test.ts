import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { RunBudget } from '../src/run-budget.js'

describe('RunBudget', () => {
  it('enforces model and tool call limits', () => {
    const modelBudget = new RunBudget({ modelCalls: 1 })
    assert.equal(modelBudget.beforeModelCall(), undefined)
    assert.equal(modelBudget.beforeModelCall(), 'model_call_budget_exhausted')

    const toolBudget = new RunBudget({ toolCalls: 1, concurrency: 1 })
    assert.equal(toolBudget.reserveToolCall(), undefined)
    toolBudget.releaseToolCall()
    assert.equal(toolBudget.reserveToolCall(), 'tool_call_budget_exhausted')
  })

  it('normalizes tool arguments before detecting repeated outcomes', () => {
    const budget = new RunBudget({ noProgressRepeats: 2 })

    assert.equal(
      budget.recordToolOutcome('lookup', { syndrome: '肝郁', limit: 3 }, 'same result'),
      undefined,
    )
    assert.equal(
      budget.recordToolOutcome('lookup', { limit: 3, syndrome: '肝郁' }, 'same result'),
      'no_progress',
    )
    assert.equal(budget.snapshot().noProgressRepeats, 2)
  })

  it('tracks estimated token usage and wall-clock limits', () => {
    let now = 100
    const budget = new RunBudget(
      { tokens: 10, wallClockMs: 50 },
      { now: () => now },
    )

    assert.equal(budget.recordTokenUsage(4, true), undefined)
    assert.equal(budget.snapshot().estimatedTokenMeasurements, 1)
    now = 150
    assert.equal(budget.beforeModelCall(), 'wall_clock_budget_exhausted')
  })

  it('enforces retry, depth, and concurrency limits', () => {
    const retryBudget = new RunBudget({ retries: 1 })
    assert.equal(retryBudget.consumeRetry(), undefined)
    assert.equal(retryBudget.consumeRetry(), 'retry_budget_exhausted')

    const depthBudget = new RunBudget({ maxDepth: 0 })
    assert.equal(depthBudget.validateDepth(0), undefined)
    assert.equal(depthBudget.validateDepth(1), 'depth_budget_exhausted')

    const concurrencyBudget = new RunBudget({ concurrency: 1 })
    assert.equal(concurrencyBudget.reserveToolCall(), undefined)
    assert.equal(
      concurrencyBudget.reserveToolCall(),
      'concurrency_budget_exhausted',
    )
  })

  it('rejects invalid limits and token measurements', () => {
    assert.throws(() => new RunBudget({ modelCalls: 0 }), /modelCalls/)
    assert.throws(() => new RunBudget({ maxDepth: -1 }), /maxDepth/)
    assert.throws(
      () => new RunBudget({ tokens: 10 }).recordTokenUsage(Number.NaN),
      /tokens/,
    )
  })
})
