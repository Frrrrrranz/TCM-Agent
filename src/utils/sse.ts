export async function* readServerSentEvents(
  response: Response,
): AsyncGenerator<string> {
  if (!response.body) {
    throw new Error('Streaming response body is unavailable')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value, { stream: !done })
    buffer = buffer.replace(/\r\n/g, '\n')

    let boundary = buffer.indexOf('\n\n')
    while (boundary >= 0) {
      const frame = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      const data = frame
        .split('\n')
        .filter(line => line.startsWith('data:'))
        .map(line => line.slice(5).trimStart())
        .join('\n')
      if (data) yield data
      boundary = buffer.indexOf('\n\n')
    }

    if (done) break
  }

  const trailingData = buffer
    .split('\n')
    .filter(line => line.startsWith('data:'))
    .map(line => line.slice(5).trimStart())
    .join('\n')
  if (trailingData) yield trailingData
}
