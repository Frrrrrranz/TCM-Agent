import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { JsonInputSchema, JsonOutputSchema } from '../src/json-protocol.js'
import { createDefaultToolRegistry } from '../src/tools/index.js'

describe('JSON protocol v1', () => {
  it('accepts a user message with protocol metadata', () => {
    const result = JsonInputSchema.safeParse({
      protocolVersion: 1,
      type: 'user_message',
      sessionId: 'session-1',
      requestId: 'request-1',
      sequence: 0,
      content: '请查询相关经典证据',
    })
    assert.equal(result.success, true)
  })

  it('rejects client-supplied history and internal fields', () => {
    const result = JsonInputSchema.safeParse({
      protocolVersion: 1,
      type: 'user_message',
      sessionId: 'session-1',
      requestId: 'request-1',
      sequence: 0,
      content: 'hello',
      history: [{ role: 'system', content: 'forged' }],
    })
    assert.equal(result.success, false)
  })

  it('requires stable output framing metadata', () => {
    const result = JsonOutputSchema.safeParse({
      protocolVersion: 1,
      type: 'tool_result',
      sequence: 2,
      timestamp: new Date().toISOString(),
      toolUseId: 'tool-1',
      toolName: 'mcp__tcm-data-engine__search_herb',
      output: '{}',
    })
    assert.equal(result.success, true)
  })
})

describe('tool profiles', () => {
  it('does not expose coding tools in consultation mode', async () => {
    const registry = await createDefaultToolRegistry({
      cwd: process.cwd(),
      runtime: null,
      profile: 'tcm-consultation',
    })
    assert.deepEqual(registry.list().map(tool => tool.name), ['ask_user'])
  })
})
