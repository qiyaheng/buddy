/** SSE 流式客户端：POST + ReadableStream 分帧解析（支持 AbortSignal 中断）。 */

import { ApiError } from './http'

let baseUrl = ''

export function configureSse(apiBase: string): void {
  baseUrl = apiBase.replace(/\/$/, '')
}

export interface AgentEvent {
  type: string
  [key: string]: unknown
}

interface StreamOptions {
  body: unknown
  signal: AbortSignal
  onEvent: (event: AgentEvent) => void
}

function parseEventBlock(block: string): AgentEvent | null {
  const dataLines: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trimStart())
    }
  }
  if (dataLines.length === 0) return null
  try {
    return JSON.parse(dataLines.join('\n')) as AgentEvent
  } catch {
    return null
  }
}

export async function streamPost(path: string, options: StreamOptions): Promise<void> {
  const res = await fetch(`${baseUrl}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(options.body),
    signal: options.signal,
  })

  if (!res.ok || !res.body) {
    const payload = await res.json().catch(() => null)
    throw new ApiError(
      payload?.code ?? `http_${res.status}`,
      payload?.message ?? `请求失败（${res.status}）`,
      res.status,
      payload?.details,
    )
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let separatorIndex: number
    while ((separatorIndex = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, separatorIndex)
      buffer = buffer.slice(separatorIndex + 2)
      const event = parseEventBlock(block)
      if (event) options.onEvent(event)
    }
  }
}
