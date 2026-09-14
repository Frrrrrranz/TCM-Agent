import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { z } from 'zod'
import { runAgentTurn } from '../src/agent-loop.js'
import { RunBudget } from '../src/run-budget.js'
import { ToolRegistry } from '../src/tool.js'
import type { AgentStep, ChatMessage, ModelAdapter } from '../src/types.js'

describe('runAgentTurn budget integration', () => {
  it('stops after normalized repeated tool outcomes', async () => {
    let modelCalls = 0
    let toolCalls = 0
    const model: ModelAdapter = {
      async next(): Promise<AgentStep> {
        modelCalls += 1
        return {
          type: 'tool_calls',
          calls: [
            {
              id: `call-${modelCalls}`,
              toolName: 'lookup',
              input: modelCalls === 1
                ? { syndrome: '肝郁', limit: 3 }
                : { limit: 3, syndrome: '肝郁' },
            },
          ],
          usage: {
            inputTokens: 10,
            outputTokens: 5,
            totalTokens: 15,
            source: 'test',
          },
        }
      },
    }
    const tools = new ToolRegistry([
      {
        name: 'lookup',
        description: 'Returns a stable lookup result.',
        inputSchema: { type: 'object' },
        schema: z.object({ syndrome: z.string(), limit: z.number() }),
        async run() {
          toolCalls += 1
          return { ok: true, output: 'same result' }
        },
      },
    ])
    const budget = new RunBudget({
      modelCalls: 10,
      toolCalls: 10,
      tokens: 1_000,
      wallClockMs: 10_000,
      retries: 2,
      maxDepth: 0,
      concurrency: 1,
      noProgressRepeats: 2,
    })
    const messages: ChatMessage[] = [{ role: 'user', content: 'test' }]

    const result = await runAgentTurn({
      model,
      tools,
      messages,
      cwd: process.cwd(),
      budget,
    })

    assert.equal(modelCalls, 2)
    assert.equal(toolCalls, 2)
    assert.equal(budget.snapshot().stopReason, 'no_progress')
    assert.equal(result.at(-1)?.role, 'assistant')
    assert.match(
      result.at(-1)?.role === 'assistant' ? result.at(-1).content : '',
      /重复工具结果/,
    )
  })

  it('does not execute tools after the token budget is exhausted', async () => {
    let toolCalls = 0
    const model: ModelAdapter = {
      async next(): Promise<AgentStep> {
        return {
          type: 'tool_calls',
          calls: [{ id: 'call-1', toolName: 'lookup', input: {} }],
          usage: {
            inputTokens: 8,
            outputTokens: 4,
            totalTokens: 12,
            source: 'test',
          },
        }
      },
    }
    const tools = new ToolRegistry([
      {
        name: 'lookup',
        description: 'Should not run.',
        inputSchema: { type: 'object' },
        schema: z.object({}),
        async run() {
          toolCalls += 1
          return { ok: true, output: 'unexpected' }
        },
      },
    ])

    const result = await runAgentTurn({
      model,
      tools,
      messages: [{ role: 'user', content: 'test' }],
      cwd: process.cwd(),
      budget: new RunBudget({ tokens: 10 }),
    })

    assert.equal(toolCalls, 0)
    assert.equal(result.at(-1)?.role, 'assistant')
    assert.match(
      result.at(-1)?.role === 'assistant' ? result.at(-1).content : '',
      /Token 预算/,
    )
  })
})
