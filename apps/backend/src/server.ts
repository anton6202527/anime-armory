import { randomUUID } from 'node:crypto'
import http, { type IncomingMessage, type Server, type ServerResponse } from 'node:http'

import { CliProxyProvider, parseGenerationRequest, type AiProvider } from './ai-provider.ts'
import {
  loadBackendConfig,
  SERVICE_NAME,
  SERVICE_VERSION,
  type BackendConfig,
} from './config.ts'
import type { AiGenerationRequest, AiGenerationResponse, AiModel } from './contracts.ts'
import { ApiError, asApiError } from './errors.ts'
import { canonicalSkillId, SkillRegistry } from './skill-registry.ts'
import { SkillRunManager } from './skill-runs.ts'
import { WorkFileStore } from './work-files.ts'
import { SupabaseAuthService } from './auth.ts'

interface ServerDependencies {
  config?: BackendConfig
  provider?: AiProvider
  registry?: SkillRegistry
  fileStore?: WorkFileStore
  skillRuns?: SkillRunManager
  auth?: SupabaseAuthService
}

interface RequestContext {
  requestId: string
  signal: AbortSignal
  origin?: string
}

class LimitedProvider implements AiProvider {
  readonly id = 'cliproxy' as const
  private active = 0
  private generationTimes: number[] = []

  constructor(
    private readonly delegate: AiProvider,
    private readonly maximumConcurrent: number,
  ) {}

  listModels(forceRefresh?: boolean, signal?: AbortSignal): Promise<AiModel[]> {
    return this.delegate.listModels(forceRefresh, signal)
  }

  async generate(request: AiGenerationRequest, signal?: AbortSignal): Promise<AiGenerationResponse> {
    const cutoff = Date.now() - 60_000
    this.generationTimes = this.generationTimes.filter((time) => time > cutoff)
    if (this.active >= this.maximumConcurrent || this.generationTimes.length >= 30) {
      throw new ApiError(429, 'generation_rate_limited', 'AI 生成请求过于频繁，请稍后重试')
    }
    this.active += 1
    this.generationTimes.push(Date.now())
    try {
      return await this.delegate.generate(request, signal)
    } finally {
      this.active = Math.max(0, this.active - 1)
    }
  }
}

class RequestRateLimiter {
  private readonly requests = new Map<string, number[]>()

  constructor(private readonly maximumPerMinute: number) {}

  accept(address: string): boolean {
    const cutoff = Date.now() - 60_000
    const recent = (this.requests.get(address) ?? []).filter((time) => time > cutoff)
    if (recent.length >= this.maximumPerMinute) {
      this.requests.set(address, recent)
      return false
    }
    recent.push(Date.now())
    this.requests.set(address, recent)
    if (this.requests.size > 256) {
      for (const [key, entries] of this.requests) {
        if (!entries.some((time) => time > cutoff)) this.requests.delete(key)
      }
    }
    return true
  }
}

function isLoopbackHostHeader(value: string | undefined): boolean {
  if (!value) return false
  try {
    const url = new URL(`http://${value}`)
    const hostname = url.hostname.toLowerCase()
    return hostname === '127.0.0.1' || hostname === 'localhost' || hostname === '[::1]'
  } catch {
    return false
  }
}

function requestId(): string {
  return randomUUID()
}

function sendJson(
  response: ServerResponse,
  status: number,
  body: unknown,
  context: Pick<RequestContext, 'requestId' | 'origin'>,
): void {
  if (response.destroyed || response.writableEnded) return
  response.statusCode = status
  response.setHeader('content-type', 'application/json; charset=utf-8')
  response.setHeader('cache-control', 'no-store')
  response.setHeader('x-content-type-options', 'nosniff')
  response.setHeader('x-frame-options', 'DENY')
  response.setHeader('referrer-policy', 'no-referrer')
  response.setHeader('x-request-id', context.requestId)
  if (context.origin) {
    response.setHeader('access-control-allow-origin', context.origin)
    response.setHeader('access-control-allow-credentials', 'true')
    response.setHeader('vary', 'Origin')
  }
  response.end(JSON.stringify(body))
}

function sendError(response: ServerResponse, error: unknown, context: RequestContext): void {
  const apiError = asApiError(error)
  sendJson(response, apiError.status, {
    error: {
      code: apiError.code,
      message: apiError.message,
      requestId: context.requestId,
    },
  }, context)
}

async function readBody(request: IncomingMessage, maximumBytes: number, signal: AbortSignal): Promise<Buffer> {
  const declaredLength = Number(request.headers['content-length'] ?? Number.NaN)
  if (Number.isFinite(declaredLength) && declaredLength > maximumBytes) {
    throw new ApiError(413, 'request_too_large', '请求体超过安全上限')
  }
  const chunks: Buffer[] = []
  let size = 0
  for await (const raw of request) {
    if (signal.aborted) throw new ApiError(499, 'request_cancelled', '请求已取消')
    const chunk = Buffer.isBuffer(raw) ? raw : Buffer.from(raw)
    size += chunk.length
    if (size > maximumBytes) throw new ApiError(413, 'request_too_large', '请求体超过安全上限')
    chunks.push(chunk)
  }
  return Buffer.concat(chunks, size)
}

async function readJson(request: IncomingMessage, maximumBytes: number, signal: AbortSignal): Promise<unknown> {
  const contentType = request.headers['content-type']?.toString().toLowerCase() ?? ''
  if (!contentType.startsWith('application/json')) {
    throw new ApiError(415, 'unsupported_media_type', '该接口仅接受 application/json')
  }
  const contents = (await readBody(request, maximumBytes, signal)).toString('utf8')
  try {
    return JSON.parse(contents) as unknown
  } catch {
    throw new ApiError(400, 'invalid_json', '请求 JSON 无效')
  }
}

function decodeSegment(value: string): string {
  try {
    const decoded = decodeURIComponent(value)
    if (!decoded || decoded.length > 256 || decoded.includes('/') || decoded.includes('\\') || decoded.includes('\0')) {
      throw new Error('invalid')
    }
    return decoded
  } catch {
    throw new ApiError(400, 'invalid_path_parameter', '路径参数无效')
  }
}

function assertAllowedOrigin(request: IncomingMessage, config: BackendConfig): string | undefined {
  const raw = request.headers.origin?.trim()
  if (!raw) return undefined
  let origin: string
  try {
    origin = new URL(raw).origin
  } catch {
    throw new ApiError(403, 'origin_forbidden', '请求 Origin 无效')
  }
  if (origin !== raw || !config.allowedOrigins.has(origin)) {
    throw new ApiError(403, 'origin_forbidden', '该本地 Origin 未获后端授权')
  }
  return origin
}

function routePattern(pathname: string, expression: RegExp): RegExpMatchArray | null {
  return pathname.match(expression)
}

export function createBackendServer(dependencies: ServerDependencies = {}): Server {
  const config = dependencies.config ?? loadBackendConfig()
  const rawProvider = dependencies.provider ?? new CliProxyProvider()
  const provider = new LimitedProvider(rawProvider, config.maxConcurrentGenerations)
  const registry = dependencies.registry ?? new SkillRegistry(config.skillsRoot)
  const fileStore = dependencies.fileStore ?? new WorkFileStore(config.runtimeRoot)
  const skillRuns = dependencies.skillRuns ?? new SkillRunManager(
    provider,
    registry,
    Math.min(2, config.maxConcurrentGenerations),
    fileStore,
  )
  const rateLimiter = new RequestRateLimiter(config.maxRequestsPerMinute)
  const auth = dependencies.auth ?? new SupabaseAuthService(config.auth)

  return http.createServer((request, response) => {
    const id = requestId()
    const controller = new AbortController()
    const abort = () => controller.abort()
    request.once('aborted', abort)
    response.once('close', () => {
      if (!response.writableEnded) abort()
    })
    void (async () => {
      let origin: string | undefined
      const initialContext: RequestContext = { requestId: id, signal: controller.signal }
      try {
        if (!isLoopbackHostHeader(request.headers.host)) {
          throw new ApiError(421, 'invalid_host', '本地后端仅接受回环 Host')
        }
        origin = assertAllowedOrigin(request, config)
        const context: RequestContext = { requestId: id, signal: controller.signal, ...(origin ? { origin } : {}) }
        const remoteAddress = request.socket.remoteAddress ?? 'unknown'
        if (!rateLimiter.accept(remoteAddress)) throw new ApiError(429, 'request_rate_limited', '请求过于频繁，请稍后重试')

        if (request.method === 'OPTIONS') {
          if (!origin) throw new ApiError(403, 'origin_forbidden', 'CORS 预检必须携带已授权 Origin')
          response.statusCode = 204
          response.setHeader('access-control-allow-origin', origin)
          response.setHeader('access-control-allow-credentials', 'true')
          response.setHeader('access-control-allow-methods', 'GET,POST,PUT,DELETE,OPTIONS')
          response.setHeader('access-control-allow-headers', 'Content-Type,X-Request-ID,Authorization')
          response.setHeader('access-control-max-age', '600')
          response.setHeader('vary', 'Origin')
          response.setHeader('x-request-id', id)
          response.end()
          return
        }

        const url = new URL(request.url ?? '/', 'http://127.0.0.1')
        const pathname = url.pathname.replace(/\/+$/, '') || '/'

        if (request.method === 'GET' && pathname === '/api/v1/health/live') {
          sendJson(response, 200, { service: SERVICE_NAME, version: SERVICE_VERSION, status: 'live' }, context)
          return
        }
        if (request.method === 'GET' && pathname === '/api/v1/auth/session') {
          const availability = await auth.availability(context.signal)
          const result = availability.available
            ? await auth.session(request.headers.cookie, context.signal)
            : { session: null }
          if (result.cookies?.length) response.setHeader('set-cookie', result.cookies)
          sendJson(response, 200, {
            configured: auth.configured,
            availability: availability.available,
            upstream: availability,
            session: result.session,
          }, context)
          return
        }
        if (request.method === 'POST' && pathname === '/api/v1/auth/access') {
          const result = await auth.access(await readJson(request, config.maxBodyBytes, context.signal), context.signal)
          if (result.cookies?.length) response.setHeader('set-cookie', result.cookies)
          sendJson(response, 200, {
            action: result.action,
            session: result.session,
            confirmationRequired: result.confirmationRequired ?? false,
          }, context)
          return
        }
        if (request.method === 'POST' && pathname === '/api/v1/auth/sign-out') {
          response.setHeader('set-cookie', await auth.signOut(request.headers.cookie, context.signal))
          sendJson(response, 200, { signedOut: true }, context)
          return
        }
        if (request.method === 'GET' && pathname === '/api/v1/health/ready') {
          const [providerResult, authResult] = await Promise.allSettled([
            provider.listModels(true, context.signal),
            auth.availability(context.signal),
          ])
          if (authResult.status === 'rejected') throw authResult.reason
          const providerReady = providerResult.status === 'fulfilled'
          const availability = authResult.value
          sendJson(response, providerReady ? 200 : 503, {
            service: SERVICE_NAME,
            version: SERVICE_VERSION,
            status: providerReady ? 'ready' : 'degraded',
            provider: {
              id: 'cliproxy',
              status: providerReady ? 'ready' : 'unavailable',
              modelCount: providerReady ? providerResult.value.length : 0,
            },
            auth: {
              configured: auth.configured,
              availability: availability.available,
              upstream: availability,
            },
            capabilities: {
              aiGeneration: true,
              skillRuns: true,
              skillRegistry: true,
              auth: availability.available,
            },
          }, context)
          return
        }
        if (request.method === 'GET' && pathname === '/api/v1/ai/models') {
          sendJson(response, 200, { models: await provider.listModels(false, context.signal) }, context)
          return
        }
        if (request.method === 'POST' && pathname === '/api/v1/ai/generations') {
          const value = await readJson(request, config.maxBodyBytes, context.signal)
          const generation = await provider.generate(parseGenerationRequest(value), context.signal)
          sendJson(response, 200, { generation }, context)
          return
        }
        if (request.method === 'GET' && pathname === '/api/v1/skills') {
          sendJson(response, 200, { skills: await registry.list() }, context)
          return
        }

        const skillSourcesMatch = routePattern(pathname, /^\/api\/v1\/skills\/([^/]+)\/sources$/)
        if (request.method === 'GET' && skillSourcesMatch?.[1]) {
          const skillId = canonicalSkillId(decodeSegment(skillSourcesMatch[1]))
          sendJson(response, 200, { skillId, sources: await registry.listSources(skillId) }, context)
          return
        }
        const skillSourceMatch = routePattern(pathname, /^\/api\/v1\/skills\/([^/]+)\/source$/)
        if (request.method === 'GET' && skillSourceMatch?.[1]) {
          const skillId = canonicalSkillId(decodeSegment(skillSourceMatch[1]))
          const sourcePath = url.searchParams.get('path')
          if (!sourcePath) throw new ApiError(400, 'source_path_required', 'path 查询参数不能为空')
          sendJson(response, 200, { skillId, source: await registry.readSource(skillId, sourcePath) }, context)
          return
        }
        const skillMatch = routePattern(pathname, /^\/api\/v1\/skills\/([^/]+)$/)
        if (request.method === 'GET' && skillMatch?.[1]) {
          sendJson(response, 200, { skill: await registry.get(decodeSegment(skillMatch[1])) }, context)
          return
        }

        if (request.method === 'POST' && pathname === '/api/v1/skill-runs') {
          const run = await skillRuns.create(await readJson(request, config.maxBodyBytes, context.signal))
          sendJson(response, 202, { run }, context)
          return
        }
        const runMatch = routePattern(pathname, /^\/api\/v1\/skill-runs\/([^/]+)$/)
        if (runMatch?.[1] && request.method === 'GET') {
          sendJson(response, 200, { run: skillRuns.get(decodeSegment(runMatch[1])) }, context)
          return
        }
        if (runMatch?.[1] && request.method === 'DELETE') {
          sendJson(response, 200, { run: skillRuns.cancel(decodeSegment(runMatch[1])) }, context)
          return
        }

        const uploadMatch = routePattern(pathname, /^\/api\/v1\/works\/([^/]+)\/files\/([^/]+)$/)
        if (request.method === 'PUT' && uploadMatch?.[1] && uploadMatch[2]) {
          const workId = decodeSegment(uploadMatch[1])
          const fileId = decodeSegment(uploadMatch[2])
          const bytes = await readBody(request, config.maxUploadBytes, context.signal)
          if (!bytes.length) throw new ApiError(400, 'empty_file', '上传文件不能为空')
          const file = await fileStore.put(workId, fileId, bytes, request.headers['content-type']?.toString())
          sendJson(response, 200, { file }, context)
          return
        }

        throw new ApiError(404, 'route_not_found', 'REST API 路由不存在')
      } catch (error) {
        const context: RequestContext = { requestId: id, signal: controller.signal, ...(origin ? { origin } : {}) }
        sendError(response, error, context)
      }
    })().finally(() => {
      request.removeListener('aborted', abort)
    })
  })
}
