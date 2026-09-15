import { afterEach, describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { AnthropicModelAdapter } from '../src/anthropic-adapter.js'
import { OpenAIModelAdapter } from '../src/openai-adapter.js'
import { runAgentTurn } from '../src/agent-loop.js'
import { ToolRegistry } from '../src/tool.js'
import type { RuntimeConfig } from '../src/config.js'
import type { AgentStep, ModelAdapter } from '../src/types.js'
import { abortableDelay } from '../src/utils/cancellation.js'

const originalFetch = globalThis.fetch

afterEach(() => {
  globalThis.fetch = originalFetch
})

function createRuntime(): RuntimeConfig {
  return {
    model: 'test-model',
    baseUrl: 'https://example.test',
    authToken: 'test-token',
    mcpServers: {},
    sourceSummary: 'test',
  }
}

function installAbortableFetch(): {
  started: Promise<AbortSignal>
} {
  let resolveStarted: (signal: AbortSignal) => void = () => undefined
  const started = new Promise<AbortSignal>(resolve => {
    resolveStarted = resolve
  })

  globalThis.fetch = ((_url: string | URL | Request, init?: RequestInit) => {
    const signal = init?.signal
    assert.ok(signal)
    resolveStarted(signal)
    return new Promise<Response>((_resolve, reject) => {
      signal.addEventListener(
        'abort',
        () => reject(new DOMException('Aborted', 'AbortError')),
        { once: true },
      )
    })
  }) as typeof fetch

  return { started }
}

describe('cancellation propagation', () => {
  it('makes retry delays abortable', async () => {
    const controller = new AbortController()
    const pending = abortableDelay(10_000, controller.signal)
    controller.abort()

    await assert.rejects(pending, { name: 'AbortError' })
  })

  it('passes the turn signal from agent loop to the model adapter', async () => {
    const controller = new AbortController()
    let receivedSignal: AbortSignal | undefined
    const model: ModelAdapter = {
      async next(_messages, options): Promise<AgentStep> {
        receivedSignal = options?.signal
        return new Promise((_resolve, reject) => {
          options?.signal?.addEventListener(
            'abort',
            () => reject(new DOMException('Aborted', 'AbortError')),
            { once: true },
          )
        })
      },
    }

    const pending = runAgentTurn({
      model,
      tools: new ToolRegistry([]),
      messages: [{ role: 'user', content: 'test' }],
      cwd: process.cwd(),
      signal: controller.signal,
    })
    await Promise.resolve()
    controller.abort()

    await assert.rejects(pending, { name: 'AbortError' })
    assert.equal(receivedSignal, controller.signal)
  })

  it('aborts OpenAI-compatible HTTP requests', async () => {
    const { started } = installAbortableFetch()
    const controller = new AbortController()
    const adapter = new OpenAIModelAdapter(
      new ToolRegistry([]),
      async () => createRuntime(),
    )

    const pending = adapter.next(
      [{ role: 'user', content: 'test' }],
      { signal: controller.signal },
    )
    assert.equal(await started, controller.signal)
    controller.abort()

    await assert.rejects(pending, { name: 'AbortError' })
  })

  it('aborts Anthropic HTTP requests', async () => {
    const { started } = installAbortableFetch()
    const controller = new AbortController()
    const adapter = new AnthropicModelAdapter(
      new ToolRegistry([]),
      async () => createRuntime(),
    )

    const pending = adapter.next(
      [{ role: 'user', content: 'test' }],
      { signal: controller.signal },
    )
    assert.equal(await started, controller.signal)
    controller.abort()

    await assert.rejects(pending, { name: 'AbortError' })
  })
})
