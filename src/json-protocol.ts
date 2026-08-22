import { z } from 'zod'

export const PROTOCOL_VERSION = 1

const identifier = z.string().min(1).max(128)

export const JsonInputSchema = z.discriminatedUnion('type', [
  z.object({
    protocolVersion: z.literal(PROTOCOL_VERSION),
    type: z.literal('user_message'),
    sessionId: identifier,
    requestId: identifier,
    sequence: z.number().int().nonnegative(),
    content: z.string().trim().min(1).max(12000),
    cursor: z.number().int().nonnegative().optional(),
    history_context: z.string().max(8000).optional(),
  }).strict(),
  z.object({
    protocolVersion: z.literal(PROTOCOL_VERSION),
    type: z.literal('cancel_turn'),
    sessionId: identifier,
    requestId: identifier,
    sequence: z.number().int().nonnegative(),
  }).strict(),
  z.object({
    protocolVersion: z.literal(PROTOCOL_VERSION),
    type: z.literal('heartbeat'),
    sessionId: identifier,
    requestId: identifier.optional(),
    sequence: z.number().int().nonnegative(),
  }).strict(),
])

export type JsonInput = z.infer<typeof JsonInputSchema>

export const JsonOutputSchema = z.object({
  protocolVersion: z.literal(PROTOCOL_VERSION),
  type: z.enum([
    'init',
    'heartbeat_ack',
    'tool_start',
    'tool_result',
    'assistant_message',
    'progress_message',
    'turn_complete',
    'turn_cancelled',
    'error',
  ]),
  sessionId: identifier.optional(),
  requestId: identifier.optional(),
  sequence: z.number().int().nonnegative(),
  toolUseId: identifier.optional(),
  timestamp: z.string().datetime({ offset: true }),
  modelName: z.string().max(256).optional(),
  content: z.string().max(12000).optional(),
  toolName: z.string().max(256).optional(),
  input: z.unknown().optional(),
  output: z.string().max(20000).optional(),
  isError: z.boolean().optional(),
  messages: z.array(z.unknown()).optional(),
  streaming: z.boolean().optional(),
}).strict()

export type JsonOutput = z.infer<typeof JsonOutputSchema>

export function createProtocolFrame(
  frame: Omit<JsonOutput, 'protocolVersion' | 'sequence' | 'timestamp'>,
  sequence: number,
): JsonOutput {
  return JsonOutputSchema.parse({
    ...frame,
    protocolVersion: PROTOCOL_VERSION,
    sequence,
    timestamp: new Date().toISOString(),
  })
}
