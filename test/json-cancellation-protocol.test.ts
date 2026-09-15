import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { JsonOutputSchema } from '../src/json-protocol.js'

describe('JSON cancellation protocol', () => {
  it('distinguishes cancellation request acknowledgement from completion', () => {
    const base = {
      protocolVersion: 1,
      sessionId: 'session-1',
      requestId: 'request-1',
      timestamp: new Date().toISOString(),
    }

    assert.equal(
      JsonOutputSchema.safeParse({
        ...base,
        type: 'cancel_requested',
        sequence: 1,
      }).success,
      true,
    )
    assert.equal(
      JsonOutputSchema.safeParse({
        ...base,
        type: 'turn_cancelled',
        sequence: 2,
      }).success,
      true,
    )
  })
})
