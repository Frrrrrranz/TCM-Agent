import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { z } from 'zod'
import { classifyToolFailure, ToolRegistry } from '../src/tool.js'

describe('tool error contract', () => {
  it('classifies standard runtime failures', () => {
    assert.equal(classifyToolFailure('HTTP 429 rate limit').code, 'transient')
    assert.equal(classifyToolFailure('request timed out').code, 'timeout')
    assert.equal(classifyToolFailure('permission denied').code, 'forbidden')
    assert.equal(classifyToolFailure('operation cancelled').code, 'cancelled')
    assert.equal(classifyToolFailure('version mismatch').code, 'version_mismatch')
    assert.equal(classifyToolFailure('unexpected failure').code, 'internal')
  })

  it('returns invalid_arguments for unknown tools and schema failures', async () => {
    const tools = new ToolRegistry([
      {
        name: 'lookup',
        description: 'Validates its input.',
        inputSchema: { type: 'object' },
        schema: z.object({ query: z.string() }),
        async run() {
          return { ok: true, output: 'ok' }
        },
      },
    ])

    const unknown = await tools.execute('missing', {}, { cwd: process.cwd() })
    const invalid = await tools.execute('lookup', {}, { cwd: process.cwd() })

    assert.equal(unknown.error?.code, 'invalid_arguments')
    assert.equal(invalid.error?.code, 'invalid_arguments')
    assert.equal(unknown.error?.retryable, false)
    assert.equal(invalid.error?.retryable, false)
  })

  it('normalizes returned and thrown failures', async () => {
    const tools = new ToolRegistry([
      {
        name: 'limited',
        description: 'Returns a transient failure.',
        inputSchema: { type: 'object' },
        schema: z.object({}),
        async run() {
          return { ok: false, output: 'HTTP 429 rate limit' }
        },
      },
      {
        name: 'timed',
        description: 'Throws a timeout.',
        inputSchema: { type: 'object' },
        schema: z.object({}),
        async run() {
          throw new Error('request timed out')
        },
      },
    ])

    const limited = await tools.execute('limited', {}, { cwd: process.cwd() })
    const timed = await tools.execute('timed', {}, { cwd: process.cwd() })

    assert.equal(limited.error?.code, 'transient')
    assert.equal(limited.error?.retryable, true)
    assert.equal(timed.error?.code, 'timeout')
    assert.equal(timed.error?.retryable, true)
  })
})
