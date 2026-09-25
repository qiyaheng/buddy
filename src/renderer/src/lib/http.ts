/** 后端 HTTP 客户端：统一基址、错误结构与 JSON 处理。 */

/** 与主进程 preload 注入的上下文结构保持一致。 */
export interface AppContext {
  apiBase: string
  version: string
  platform: string
  isDev: boolean
}

let baseUrl = ''

export function configureHttp(context: AppContext): void {
  baseUrl = context.apiBase.replace(/\/$/, '')
}

export class ApiError extends Error {
  code: string
  status: number
  details: unknown

  constructor(code: string, message: string, status: number, details?: unknown) {
    super(message)
    this.code = code
    this.status = status
    this.details = details
  }
}

interface RequestOptions {
  method?: string
  body?: unknown
  signal?: AbortSignal
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, signal } = options
  const init: RequestInit = { method, signal }
  if (body !== undefined) {
    init.headers = { 'Content-Type': 'application/json' }
    init.body = JSON.stringify(body)
  }

  const res = await fetch(`${baseUrl}${path}`, init)
  if (res.status === 204) return undefined as T

  const payload = await res.json().catch(() => null)
  if (!res.ok) {
    throw new ApiError(
      payload?.code ?? `http_${res.status}`,
      payload?.message ?? `请求失败（${res.status}）`,
      res.status,
      payload?.details,
    )
  }
  return payload as T
}

export const http = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>(path, { signal }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
  del: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}
