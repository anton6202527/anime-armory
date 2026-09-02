import { ApiError } from './errors.ts'

export interface AuthConfiguration {
  supabaseUrl: string
  publishableKey: string
}

export interface AuthUser {
  id: string
  email?: string
  user_metadata?: Record<string, unknown>
}

export interface AuthSession {
  user: AuthUser
}

interface SupabaseTokenResponse {
  access_token?: string
  refresh_token?: string
  expires_in?: number
  user?: AuthUser
}

interface SupabaseErrorBody {
  code?: string
  error_code?: string
  msg?: string
  message?: string
  error_description?: string
}

export interface AuthResult {
  session: AuthSession | null
  confirmationRequired?: boolean
  action?: 'signed-in' | 'signed-up'
  cookies?: string[]
}

export type AuthUpstreamStatus = 'available' | 'unconfigured' | 'unhealthy' | 'timeout' | 'unavailable'

export interface AuthAvailability {
  available: boolean
  status: AuthUpstreamStatus
  code?: string
  message?: string
}

export interface AuthServiceOptions {
  healthTimeoutMs?: number
  requestTimeoutMs?: number
}

const ACCESS_COOKIE = 'labutv_access_token'
const REFRESH_COOKIE = 'labutv_refresh_token'
const COOKIE_PATH = '/api/v1'
const DEFAULT_HEALTH_TIMEOUT_MS = 1_500
const DEFAULT_REQUEST_TIMEOUT_MS = 8_000

function cookieValue(header: string | undefined, name: string): string | null {
  for (const entry of header?.split(';') ?? []) {
    const separator = entry.indexOf('=')
    if (separator < 0 || entry.slice(0, separator).trim() !== name) continue
    try {
      return decodeURIComponent(entry.slice(separator + 1).trim())
    } catch {
      return null
    }
  }
  return null
}

function sessionCookies(token: SupabaseTokenResponse): string[] {
  if (!token.access_token || !token.refresh_token) return []
  const maximumAge = Math.max(60, Math.min(token.expires_in ?? 3600, 86_400))
  return [
    `${ACCESS_COOKIE}=${encodeURIComponent(token.access_token)}; HttpOnly; SameSite=Lax; Path=${COOKIE_PATH}; Max-Age=${maximumAge}`,
    `${REFRESH_COOKIE}=${encodeURIComponent(token.refresh_token)}; HttpOnly; SameSite=Lax; Path=${COOKIE_PATH}; Max-Age=2592000`,
  ]
}

export function clearAuthCookies(): string[] {
  return [
    `${ACCESS_COOKIE}=; HttpOnly; SameSite=Lax; Path=${COOKIE_PATH}; Max-Age=0`,
    `${REFRESH_COOKIE}=; HttpOnly; SameSite=Lax; Path=${COOKIE_PATH}; Max-Age=0`,
  ]
}

function normalizeEmail(value: unknown): string {
  const email = typeof value === 'string' ? value.trim().toLowerCase() : ''
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    throw new ApiError(400, 'invalid_email', '请输入有效的邮箱地址')
  }
  return email
}

function normalizePassword(value: unknown): string {
  const password = typeof value === 'string' ? value : ''
  if (password.length < 6 || password.length > 1024) {
    throw new ApiError(400, 'invalid_password', '密码长度需要在 6 到 1024 位之间')
  }
  return password
}

function errorMessage(body: SupabaseErrorBody, fallback: string): string {
  return body.msg || body.message || body.error_description || fallback
}

function errorCode(body: SupabaseErrorBody): string {
  return body.code || body.error_code || ''
}

export class SupabaseAuthService {
  private readonly healthTimeoutMs: number
  private readonly requestTimeoutMs: number

  constructor(
    private readonly configuration: AuthConfiguration | undefined,
    private readonly request: typeof fetch = fetch,
    options: AuthServiceOptions = {},
  ) {
    this.healthTimeoutMs = Math.max(1, options.healthTimeoutMs ?? DEFAULT_HEALTH_TIMEOUT_MS)
    this.requestTimeoutMs = Math.max(1, options.requestTimeoutMs ?? DEFAULT_REQUEST_TIMEOUT_MS)
  }

  get configured(): boolean {
    return this.configuration !== undefined
  }

  private async supabase(
    pathname: string,
    init: RequestInit,
    signal: AbortSignal,
    timeoutMs = this.requestTimeoutMs,
  ): Promise<{ response: Response; body: SupabaseTokenResponse & SupabaseErrorBody }> {
    if (!this.configuration) {
      throw new ApiError(503, 'auth_not_configured', '登录服务尚未配置，请在后端环境中填写 SUPABASE_URL 与 SUPABASE_PUBLISHABLE_KEY')
    }
    if (signal.aborted) throw new ApiError(499, 'request_cancelled', '请求已取消')
    const timeoutSignal = AbortSignal.timeout(timeoutMs)
    const upstreamSignal = AbortSignal.any([signal, timeoutSignal])
    const upstreamError = (): ApiError => {
      if (signal.aborted) return new ApiError(499, 'request_cancelled', '请求已取消')
      if (timeoutSignal.aborted) {
        return new ApiError(504, 'auth_upstream_timeout', 'Supabase 登录服务响应超时，请检查项目状态或稍后重试')
      }
      return new ApiError(
        502,
        'auth_upstream_unavailable',
        '无法连接 Supabase 登录服务，请检查项目是否可用、本机网络与 SUPABASE_URL',
      )
    }
    let response: Response
    try {
      response = await this.request(`${this.configuration.supabaseUrl}/auth/v1${pathname}`, {
        ...init,
        headers: {
          apikey: this.configuration.publishableKey,
          'content-type': 'application/json',
          ...init.headers,
        },
        signal: upstreamSignal,
      })
    } catch {
      throw upstreamError()
    }
    let body: SupabaseTokenResponse & SupabaseErrorBody
    try {
      body = await response.json() as SupabaseTokenResponse & SupabaseErrorBody
    } catch {
      if (upstreamSignal.aborted) throw upstreamError()
      body = {}
    }
    return { response, body }
  }

  async availability(signal: AbortSignal): Promise<AuthAvailability> {
    if (!this.configuration) {
      return {
        available: false,
        status: 'unconfigured',
        code: 'auth_not_configured',
        message: '登录服务尚未配置',
      }
    }
    try {
      let probe = await this.supabase('/health', { method: 'GET' }, signal, this.healthTimeoutMs)
      if (probe.response.status === 404 || probe.response.status === 405) {
        probe = await this.supabase('/settings', { method: 'GET' }, signal, this.healthTimeoutMs)
      }
      if (probe.response.ok) return { available: true, status: 'available' }
      return {
        available: false,
        status: 'unhealthy',
        code: 'auth_upstream_unhealthy',
        message: 'Supabase 登录服务当前不可用，请检查项目状态与发布密钥',
      }
    } catch (error) {
      if (error instanceof ApiError && error.code === 'request_cancelled') throw error
      if (error instanceof ApiError && error.code === 'auth_upstream_timeout') {
        return { available: false, status: 'timeout', code: error.code, message: error.message }
      }
      const unavailable = error instanceof ApiError
        ? error
        : new ApiError(502, 'auth_upstream_unavailable', '无法连接 Supabase 登录服务，请检查项目状态与本机网络')
      return {
        available: false,
        status: 'unavailable',
        code: unavailable.code,
        message: unavailable.message,
      }
    }
  }

  private async passwordGrant(email: string, password: string, signal: AbortSignal) {
    return this.supabase('/token?grant_type=password', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }, signal)
  }

  async access(input: unknown, signal: AbortSignal): Promise<AuthResult> {
    const record = input && typeof input === 'object' && !Array.isArray(input)
      ? input as Record<string, unknown>
      : {}
    const email = normalizeEmail(record.email)
    const password = normalizePassword(record.password)
    const signIn = await this.passwordGrant(email, password, signal)
    if (signIn.response.ok && signIn.body.user && signIn.body.access_token) {
      return {
        action: 'signed-in',
        session: { user: signIn.body.user },
        confirmationRequired: false,
        cookies: sessionCookies(signIn.body),
      }
    }

    const signInCode = errorCode(signIn.body)
    const signInMessage = errorMessage(signIn.body, '登录失败，请稍后重试')
    const unknownAccount = signInCode === 'invalid_credentials' || /invalid login credentials/i.test(signInMessage)
    if (!unknownAccount) {
      throw new ApiError(signIn.response.status || 401, signInCode || 'auth_operation_failed', signInMessage)
    }

    const signUp = await this.supabase('/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }, signal)
    if (!signUp.response.ok || !signUp.body.user) {
      const code = errorCode(signUp.body)
      const message = errorMessage(signUp.body, '账号创建失败，请稍后重试')
      const accountExists = code === 'user_already_exists' || /already (?:been )?registered|user already exists/i.test(message)
      throw new ApiError(signUp.response.status || 400, code || 'auth_operation_failed', accountExists ? '该邮箱已注册，请检查密码后重试。' : message)
    }

    const hasSession = Boolean(signUp.body.access_token && signUp.body.refresh_token)
    return {
      action: 'signed-up',
      session: hasSession ? { user: signUp.body.user } : null,
      confirmationRequired: !hasSession,
      cookies: hasSession ? sessionCookies(signUp.body) : [],
    }
  }

  async session(cookieHeader: string | undefined, signal: AbortSignal): Promise<AuthResult> {
    if (!this.configuration) return { session: null }
    const accessToken = cookieValue(cookieHeader, ACCESS_COOKIE)
    if (accessToken) {
      const current = await this.supabase('/user', {
        method: 'GET',
        headers: { authorization: `Bearer ${accessToken}` },
      }, signal)
      const currentUser = current.body as typeof current.body & Partial<AuthUser>
      if (current.response.ok && currentUser.id) {
        return { session: { user: currentUser as AuthUser } }
      }
    }

    const refreshToken = cookieValue(cookieHeader, REFRESH_COOKIE)
    if (!refreshToken) return { session: null, cookies: accessToken ? clearAuthCookies() : [] }
    const refreshed = await this.supabase('/token?grant_type=refresh_token', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    }, signal)
    if (!refreshed.response.ok || !refreshed.body.user || !refreshed.body.access_token) {
      return { session: null, cookies: clearAuthCookies() }
    }
    return {
      session: { user: refreshed.body.user },
      cookies: sessionCookies(refreshed.body),
    }
  }

  async signOut(cookieHeader: string | undefined, signal: AbortSignal): Promise<string[]> {
    if (this.configuration) {
      const accessToken = cookieValue(cookieHeader, ACCESS_COOKIE)
      if (accessToken) {
        await this.supabase('/logout', {
          method: 'POST',
          headers: { authorization: `Bearer ${accessToken}` },
        }, signal).catch(() => undefined)
      }
    }
    return clearAuthCookies()
  }
}
