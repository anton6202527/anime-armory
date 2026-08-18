export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === 'AbortError'
}

export function asApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  if (isAbortError(error)) return new ApiError(499, 'request_cancelled', '请求已取消')
  return new ApiError(500, 'internal_error', '后端处理请求时发生错误')
}
