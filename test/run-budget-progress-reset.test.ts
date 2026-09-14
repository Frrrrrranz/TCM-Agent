import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { RunBudget } from '../src/run-budget.js'

describe('RunBudget progress detection', () => {
  it('resets the repeat count when a tool outcome changes', () => {
    const budget = new RunBudget({ noProgressRepeats: 2 })

    assert.equal(budget.recordToolOutcome('lookup', { id: 1 }, 'first'), undefined)
    assert.equal(budget.recordToolOutcome('lookup', { id: 2 }, 'different'), undefined)
    assert.equal(budget.recordToolOutcome('lookup', { id: 1 }, 'first'), undefined)
    assert.equal(budget.snapshot().noProgressRepeats, 1)
  })
})
