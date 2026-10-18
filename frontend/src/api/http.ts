import type { ApiResponse } from '@/types/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
  } catch {
    throw new ApiError('无法连接服务器，请检查后端服务是否已启动', 0)
  }

  if (!response.headers.get('content-type')?.includes('application/json')) {
    throw new ApiError(
      response.status >= 500
        ? '后端服务暂不可用，请检查服务状态和 API 代理配置'
        : '服务器返回了无法识别的数据',
      response.status,
    )
  }

  let body: ApiResponse<T>
  try {
    body = (await response.json()) as ApiResponse<T>
  } catch {
    throw new ApiError('服务器返回了无法识别的数据', response.status)
  }
  if (!response.ok || body.code !== 200) {
    throw new ApiError(body.message || '请求失败', response.status)
  }
  return body.data as T
}

export function get<T>(path: string, token?: string): Promise<T> {
  return request<T>(path, {}, token)
}

export function post<T>(
  path: string,
  data?: unknown,
  token?: string,
): Promise<T> {
  return request<T>(
    path,
    { method: 'POST', body: data === undefined ? undefined : JSON.stringify(data) },
    token,
  )
}

export function put<T>(
  path: string,
  data: unknown,
  token: string,
): Promise<T> {
  return request<T>(path, { method: 'PUT', body: JSON.stringify(data) }, token)
}

export function patch<T>(
  path: string,
  data: unknown,
  token: string,
): Promise<T> {
  return request<T>(path, { method: 'PATCH', body: JSON.stringify(data) }, token)
}

export async function remove(path: string, token: string): Promise<void> {
  await request<unknown>(path, { method: 'DELETE' }, token)
}
