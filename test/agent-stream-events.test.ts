import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { runAgentTurn } from '../src/agent-loop.js'
import { ToolRegistry } from '../src/tool.js'
import type { AgentStep, ModelAdapter } from '../src/types.js'

describe('agent stream event forwarding', () => {
  it('forwards text deltas when the caller subscribes', async () => {
    const model: ModelAdapter = {
      async next(_messages, options): Promise<AgentStep> {
        options?.onEvent?.({ type: 'text_delta', content: '先' })
        options?.onEvent?.({ type: 'text_delta', content: '到' })
        options?.onEvent?.({ type: 'end', stopReason: 'stop' })
        return { type: 'assistant', content: '先到' }
      },
    }
    const deltas: string[] = []

    await runAgentTurn({
      model,
      tools: new ToolRegistry([]),
      messages: [{ role: 'user', content: 'test' }],
      cwd: process.cwd(),
      onAssistantDelta: content => deltas.push(content),
    })

    assert.deepEqual(deltas, ['先', '到'])
  })

  it('keeps non-streaming callers on the compatibility path', async () => {
    let receivedOnEvent: unknown = 'unset'
    const model: ModelAdapter = {
      async next(_messages, options): Promise<AgentStep> {
        receivedOnEvent = options?.onEvent
        return { type: 'assistant', content: 'done' }
      },
    }

    await runAgentTurn({
      model,
      tools: new ToolRegistry([]),
      messages: [{ role: 'user', content: 'test' }],
      cwd: process.cwd(),
    })

    assert.equal(receivedOnEvent, undefined)
  })
})
