export class OperationCancelledError extends Error {
  constructor(message = 'Operation cancelled') {
    super(message)
    this.name = 'AbortError'
  }
}

export function isCancellationError(error: unknown): boolean {
  return error instanceof Error && error.name === 'AbortError'
}

export function throwIfAborted(signal: AbortSignal | undefined): void {
  if (!signal?.aborted) return
  throw new OperationCancelledError()
}

export function abortableDelay(
  ms: number,
  signal: AbortSignal | undefined,
): Promise<void> {
  throwIfAborted(signal)

  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      signal?.removeEventListener('abort', handleAbort)
      resolve()
    }, Math.max(0, ms))

    const handleAbort = () => {
      clearTimeout(timeout)
      reject(new OperationCancelledError())
    }

    signal?.addEventListener('abort', handleAbort, { once: true })
  })
}
