export async function fetchHealth() {
  const res = await fetch('/api/health')
  if (!res.ok) throw new Error(`health check failed: HTTP ${res.status}`)
  return res.json()
}

function parseFrames(buffer, onEvent) {
  let idx
  while ((idx = buffer.indexOf('\n\n')) >= 0) {
    const frame = buffer.slice(0, idx)
    buffer = buffer.slice(idx + 2)
    const dataLine = frame.split('\n').find((l) => l.startsWith('data:'))
    if (dataLine) {
      try {
        onEvent(JSON.parse(dataLine.slice(5).trim()))
      } catch {
        // skip malformed frame
      }
    }
  }
  return buffer
}

export async function streamChat(
  { messages, options, signal },
  handlers = {},
) {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, options }),
    signal,
  })
  if (!res.ok || !res.body) {
    throw new Error(`chat request failed: HTTP ${res.status}`)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    buffer = parseFrames(buffer, (evt) => {
      switch (evt.type) {
        case 'start':
          handlers.onStart?.(evt)
          break
        case 'token':
          handlers.onToken?.(evt.content)
          break
        case 'telemetry':
          handlers.onTelemetry?.(evt)
          break
        case 'usage':
          handlers.onUsage?.(evt.usage)
          break
        case 'notice':
          handlers.onNotice?.(evt.text)
          break
        case 'error':
          handlers.onError?.(evt.text)
          break
        case 'done':
          handlers.onDone?.(evt)
          break
        default:
          break
      }
    })
  }
}
