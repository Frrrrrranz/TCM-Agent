import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  parseAnthropicStream,
  parseOpenAIStream,
} from '../src/model-stream.js'
import type { ModelStreamEvent } from '../src/types.js'

function createStreamResponse(parts: string[]): Response {
  const encoder = new TextEncoder()
  return new Response(new ReadableStream({
    start(controller) {
      for (const part of parts) controller.enqueue(encoder.encode(part))
      controller.close()
    },
  }), {
    headers: { 'content-type': 'text/event-stream' },
  })
}

describe('model stream parsing', () => {
  it('parses OpenAI text, split tool arguments, usage, and end events', async () => {
    const response = createStreamResponse([
      'data: {"choices":[{"delta":{"content":"你"}}]}\n\n',
      'data: {"choices":[{"delta":{"content":"好","tool_calls":[{"index":0,"id":"call-1","function":{"name":"lookup","arguments":"{\\"q\\":"}}]}}]}\n',
      '\ndata: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"\\"桂枝\\"}"}}]},"finish_reason":"tool_calls"}]}\n\n',
      'data: {"choices":[],"usage":{"prompt_tokens":4,"completion_tokens":3,"total_tokens":7}}\n\n',
      'data: [DONE]\n\n',
    ])
    const events: ModelStreamEvent[] = []

    const result = await parseOpenAIStream(response, event => events.push(event))

    assert.equal(result.content, '你好')
    assert.deepEqual(result.toolCalls, [{
      id: 'call-1',
      toolName: 'lookup',
      input: { q: '桂枝' },
    }])
    assert.equal(result.usage?.totalTokens, 7)
    assert.deepEqual(
      events.filter(event => event.type === 'text_delta'),
      [
        { type: 'text_delta', content: '你' },
        { type: 'text_delta', content: '好' },
      ],
    )
    assert.equal(events.at(-1)?.type, 'end')
  })

  it('parses Anthropic content blocks and incremental tool JSON', async () => {
    const frames = [
      { type: 'message_start', message: { usage: { input_tokens: 5 } } },
      { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } },
      { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: '完成' } },
      { type: 'content_block_start', index: 1, content_block: { type: 'tool_use', id: 'tool-1', name: 'search', input: {} } },
      { type: 'content_block_delta', index: 1, delta: { type: 'input_json_delta', partial_json: '{"query":' } },
      { type: 'content_block_delta', index: 1, delta: { type: 'input_json_delta', partial_json: '"黄芪"}' } },
      { type: 'message_delta', delta: { stop_reason: 'tool_use' }, usage: { output_tokens: 6 } },
      { type: 'message_stop' },
    ]
    const payload = frames.map(frame => `event: ${frame.type}\ndata: ${JSON.stringify(frame)}\n\n`).join('')
    const response = createStreamResponse([
      payload.slice(0, 73),
      payload.slice(73, 191),
      payload.slice(191),
    ])
    const events: ModelStreamEvent[] = []

    const result = await parseAnthropicStream(response, event => events.push(event))

    assert.deepEqual(result.content, [
      { type: 'text', text: '完成' },
      { type: 'tool_use', id: 'tool-1', name: 'search', input: { query: '黄芪' } },
    ])
    assert.equal(result.usage?.totalTokens, 11)
    assert.ok(events.some(event => event.type === 'tool_argument_delta'))
    assert.ok(events.some(event => event.type === 'tool_call'))
    assert.equal(events.at(-1)?.type, 'end')
  })
})
