import { ApiError, isAbortError } from './errors.ts'
import { resolveCliProxyConfiguration, type CliProxyConfiguration } from './config.ts'
import type { AiGenerationRequest, AiGenerationResponse, AiModel } from './contracts.ts'

const MODEL_ID_PATTERN = /^[a-zA-Z0-9._:/-]{1,160}$/
const GPT_MODEL_PATTERN = /^(?:[a-z0-9._-]+\/)*gpt(?:-|$)/i
const GPT_IMAGE_MODEL_PATTERN = /(?:^|\/)gpt-image(?:-|$)/i
const ASPECT_RATIOS = new Set(['1:1', '2:1', '3:2', '2:3', '4:3', '3:4', '16:9', '9:16'])
const IMAGE_MIME_TYPES = new Set(['image/png', 'image/jpeg', 'image/webp', 'image/gif'])
const MAX_MODEL_RESPONSE_BYTES = 2 * 1024 * 1024
const MAX_TEXT_RESPONSE_BYTES = 4 * 1024 * 1024
const MAX_IMAGE_RESPONSE_BYTES = 32 * 1024 * 1024
const MAX_TEXT_OUTPUT_CHARS = 80_000
const MAX_TEXT_OUTPUT_TOKENS = 8_192
const MAX_IMAGE_BYTES = 20 * 1024 * 1024
const MAX_INPUT_IMAGE_BYTES = 12 * 1024 * 1024
const MAX_PROMPT_CHARS = 24_000
const MODEL_CACHE_TTL_MS = 60_000

export interface AiProvider {
  readonly id: 'cliproxy'
  listModels(forceRefresh?: boolean, signal?: AbortSignal): Promise<AiModel[]>
  generate(request: AiGenerationRequest, signal?: AbortSignal): Promise<AiGenerationResponse>
}

export interface CliProxyProviderOptions {
  environment?: NodeJS.ProcessEnv
  configPath?: string
  configuration?: () => Promise<CliProxyConfiguration>
  fetch?: typeof globalThis.fetch
  modelTimeoutMs?: number
  textTimeoutMs?: number
  imageTimeoutMs?: number
}

function endpoint(baseUrl: string, pathname: string): string {
  return `${baseUrl}${pathname.startsWith('/') ? pathname : `/${pathname}`}`
}

type SupportedImageMimeType = NonNullable<AiGenerationRequest['image']>['mimeType']

function imageMimeType(bytes: Buffer): SupportedImageMimeType | null {
  if (bytes.length >= 8 && bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) {
    return 'image/png'
  }
  if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return 'image/jpeg'
  if (bytes.length >= 12 && bytes.subarray(0, 4).toString('ascii') === 'RIFF'
    && bytes.subarray(8, 12).toString('ascii') === 'WEBP') return 'image/webp'
  if (bytes.length >= 6 && /^GIF8[79]a$/.test(bytes.subarray(0, 6).toString('ascii'))) return 'image/gif'
  return null
}

function contentText(value: unknown): string {
  if (typeof value === 'string') return value
  if (!Array.isArray(value)) return ''
  return value.map((part) => {
    if (!part || typeof part !== 'object' || Array.isArray(part)) return ''
    const record = part as Record<string, unknown>
    return (record.type === 'text' || record.type === 'output_text') && typeof record.text === 'string'
      ? record.text
      : ''
  }).join('')
}

function responseText(payload: unknown): string {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return ''
  const record = payload as Record<string, unknown>
  if (typeof record.output_text === 'string' && record.output_text.trim()) return record.output_text.trim()
  if (!Array.isArray(record.output)) return ''
  return record.output.map((item) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return ''
    return contentText((item as Record<string, unknown>).content)
  }).join('').trim()
}

function imageSize(aspectRatio?: string): '1024x1024' | '1536x1024' | '1024x1536' {
  if (aspectRatio === '2:1' || aspectRatio === '16:9' || aspectRatio === '3:2' || aspectRatio === '4:3') {
    return '1536x1024'
  }
  if (aspectRatio === '9:16' || aspectRatio === '2:3' || aspectRatio === '3:4') return '1024x1536'
  return '1024x1024'
}

function upstreamFailure(status: number): ApiError {
  if (status === 401 || status === 403) {
    return new ApiError(502, 'cliproxy_auth_failed', 'cliproxy 鉴权失败，请检查服务端 API Key')
  }
  if (status === 404 || status === 405 || status === 501) {
    return new ApiError(501, 'cliproxy_endpoint_unsupported', '当前 cliproxy 不支持所需的生成接口')
  }
  if (status === 408 || status === 504) return new ApiError(504, 'cliproxy_timeout', 'cliproxy 请求超时')
  if (status === 429) return new ApiError(429, 'cliproxy_rate_limited', '共享模型当前繁忙，请稍后重试')
  return new ApiError(502, 'cliproxy_request_failed', `cliproxy 请求失败（HTTP ${status}）`)
}

async function limitedResponseBuffer(response: Response, maximumBytes: number): Promise<Buffer> {
  const declaredLength = Number(response.headers.get('content-length') ?? Number.NaN)
  if (Number.isFinite(declaredLength) && declaredLength > maximumBytes) {
    await response.body?.cancel().catch(() => undefined)
    throw new ApiError(502, 'cliproxy_output_too_large', 'cliproxy 返回内容超过安全上限')
  }
  if (!response.body) return Buffer.alloc(0)
  const reader = response.body.getReader()
  const chunks: Buffer[] = []
  let size = 0
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = Buffer.from(value)
      size += chunk.length
      if (size > maximumBytes) {
        await reader.cancel().catch(() => undefined)
        throw new ApiError(502, 'cliproxy_output_too_large', 'cliproxy 返回内容超过安全上限')
      }
      chunks.push(chunk)
    }
  } finally {
    reader.releaseLock()
  }
  return Buffer.concat(chunks, size)
}

async function limitedJson(response: Response, maximumBytes: number): Promise<unknown> {
  const body = (await limitedResponseBuffer(response, maximumBytes)).toString('utf8')
  try {
    return JSON.parse(body) as unknown
  } catch {
    throw new ApiError(502, 'cliproxy_invalid_response', 'cliproxy 返回了无效 JSON')
  }
}

export function parseGenerationRequest(value: unknown): AiGenerationRequest {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new ApiError(400, 'invalid_generation_request', '生成请求格式无效')
  }
  const input = value as Record<string, unknown>
  if (input.modality !== 'text' && input.modality !== 'image') {
    throw new ApiError(400, 'invalid_generation_request', 'modality 必须是 text 或 image')
  }
  const model = typeof input.model === 'string' ? input.model.trim() : ''
  const prompt = typeof input.prompt === 'string' ? input.prompt.trim() : ''
  if (!MODEL_ID_PATTERN.test(model)) throw new ApiError(400, 'invalid_generation_request', '模型 ID 无效')
  if (!prompt || prompt.length > MAX_PROMPT_CHARS) {
    throw new ApiError(400, 'invalid_generation_request', `prompt 不能为空且不能超过 ${MAX_PROMPT_CHARS} 个字符`)
  }
  const aspectRatio = typeof input.aspectRatio === 'string' && input.aspectRatio.trim()
    ? input.aspectRatio.trim()
    : undefined
  if (aspectRatio && (input.modality !== 'image' || !ASPECT_RATIOS.has(aspectRatio))) {
    throw new ApiError(400, 'invalid_generation_request', '图片比例无效')
  }
  const quality = input.quality === 'standard' || input.quality === 'high' ? input.quality : undefined
  if (input.quality !== undefined && (input.modality !== 'image' || !quality)) {
    throw new ApiError(400, 'invalid_generation_request', '图片画质无效')
  }
  let image: AiGenerationRequest['image']
  if (input.image !== undefined) {
    if (!input.image || typeof input.image !== 'object' || Array.isArray(input.image)) {
      throw new ApiError(400, 'invalid_generation_request', '参考图片格式无效')
    }
    const rawImage = input.image as Record<string, unknown>
    const base64 = typeof rawImage.base64 === 'string' ? rawImage.base64.replace(/\s/g, '') : ''
    const mimeType = typeof rawImage.mimeType === 'string' ? rawImage.mimeType : ''
    if (!base64 || !/^[a-zA-Z0-9+/]+={0,2}$/.test(base64) || !IMAGE_MIME_TYPES.has(mimeType)) {
      throw new ApiError(400, 'invalid_generation_request', '参考图片不是有效的受支持 base64 图片')
    }
    const bytes = Buffer.from(base64, 'base64')
    if (!bytes.length || bytes.length > MAX_INPUT_IMAGE_BYTES || imageMimeType(bytes) !== mimeType
      || (input.modality === 'image' && mimeType === 'image/gif')) {
      throw new ApiError(400, 'invalid_generation_request', '参考图片格式无效或超过 12MB')
    }
    image = { base64: bytes.toString('base64'), mimeType: mimeType as SupportedImageMimeType }
  }
  const normalizedAspectRatio = aspectRatio as NonNullable<AiGenerationRequest['aspectRatio']> | undefined
  return {
    modality: input.modality,
    model,
    prompt,
    ...(normalizedAspectRatio ? { aspectRatio: normalizedAspectRatio } : {}),
    ...(quality ? { quality } : {}),
    ...(image ? { image } : {}),
  }
}

export class CliProxyProvider implements AiProvider {
  readonly id = 'cliproxy' as const
  private readonly configuration: () => Promise<CliProxyConfiguration>
  private readonly fetchImplementation: typeof globalThis.fetch
  private readonly modelTimeoutMs: number
  private readonly textTimeoutMs: number
  private readonly imageTimeoutMs: number
  private modelCache: { expiresAt: number; models: AiModel[] } | undefined

  constructor(options: CliProxyProviderOptions = {}) {
    this.configuration = options.configuration
      ?? (() => resolveCliProxyConfiguration(options.environment, options.configPath))
    this.fetchImplementation = options.fetch ?? globalThis.fetch
    this.modelTimeoutMs = options.modelTimeoutMs ?? 8_000
    this.textTimeoutMs = options.textTimeoutMs ?? 90_000
    this.imageTimeoutMs = options.imageTimeoutMs ?? 180_000
  }

  private async request(
    pathname: string,
    init: RequestInit,
    timeoutMs: number,
    maximumBytes: number,
    externalSignal?: AbortSignal,
  ): Promise<unknown> {
    const configuration = await this.configuration()
    const controller = new AbortController()
    const abort = () => controller.abort()
    if (externalSignal?.aborted) controller.abort()
    else externalSignal?.addEventListener('abort', abort, { once: true })
    const timer = setTimeout(abort, timeoutMs)
    try {
      const headers = new Headers(init.headers)
      headers.set('authorization', `Bearer ${configuration.apiKey}`)
      headers.set('accept', 'application/json')
      const response = await this.fetchImplementation(endpoint(configuration.baseUrl, pathname), {
        ...init,
        headers,
        signal: controller.signal,
        redirect: 'error',
      })
      if (!response.ok) {
        await limitedResponseBuffer(response, 64 * 1024).catch(() => undefined)
        throw upstreamFailure(response.status)
      }
      return limitedJson(response, maximumBytes)
    } catch (error) {
      if (error instanceof ApiError) throw error
      if (externalSignal?.aborted) throw new ApiError(499, 'request_cancelled', '生成请求已取消')
      if (isAbortError(error)) throw new ApiError(504, 'cliproxy_timeout', 'cliproxy 请求超时')
      throw new ApiError(503, 'cliproxy_unavailable', '无法连接 cliproxy')
    } finally {
      clearTimeout(timer)
      externalSignal?.removeEventListener('abort', abort)
    }
  }

  async listModels(forceRefresh = false, signal?: AbortSignal): Promise<AiModel[]> {
    if (!forceRefresh && this.modelCache && this.modelCache.expiresAt > Date.now()) {
      return this.modelCache.models.map((model) => ({ ...model }))
    }
    const payload = await this.request('/v1/models', { method: 'GET' }, this.modelTimeoutMs, MAX_MODEL_RESPONSE_BYTES, signal)
    const data = payload && typeof payload === 'object' && !Array.isArray(payload)
      ? (payload as Record<string, unknown>).data
      : null
    if (!Array.isArray(data)) throw new ApiError(502, 'cliproxy_invalid_response', 'cliproxy 模型列表格式无效')
    const seen = new Set<string>()
    const models: AiModel[] = []
    for (const item of data) {
      if (!item || typeof item !== 'object' || Array.isArray(item)) continue
      const idValue = (item as Record<string, unknown>).id
      const id = typeof idValue === 'string' ? idValue.trim() : ''
      if (!MODEL_ID_PATTERN.test(id) || !GPT_MODEL_PATTERN.test(id) || seen.has(id)) continue
      seen.add(id)
      models.push({
        id,
        label: id,
        modality: GPT_IMAGE_MODEL_PATTERN.test(id) ? 'image' : 'text',
        provider: 'cliproxy',
      })
    }
    models.sort((left, right) => left.modality.localeCompare(right.modality) || left.id.localeCompare(right.id))
    this.modelCache = { expiresAt: Date.now() + MODEL_CACHE_TTL_MS, models }
    return models.map((model) => ({ ...model }))
  }

  private async assertAvailable(model: string, modality: AiGenerationRequest['modality'], signal?: AbortSignal): Promise<void> {
    let models = await this.listModels(false, signal)
    if (!models.some((candidate) => candidate.id === model && candidate.modality === modality)) {
      models = await this.listModels(true, signal)
    }
    if (!models.some((candidate) => candidate.id === model && candidate.modality === modality)) {
      throw new ApiError(400, 'model_unavailable', `模型 ${model} 不可用或不支持 ${modality} 生成`)
    }
  }

  private async generateText(input: AiGenerationRequest, signal?: AbortSignal): Promise<string> {
    try {
      const payload = await this.request('/v1/responses', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          model: input.model,
          max_output_tokens: MAX_TEXT_OUTPUT_TOKENS,
          input: input.image ? [{
            role: 'user',
            content: [
              { type: 'input_text', text: input.prompt },
              { type: 'input_image', image_url: `data:${input.image.mimeType};base64,${input.image.base64}` },
            ],
          }] : input.prompt,
        }),
      }, this.textTimeoutMs, MAX_TEXT_RESPONSE_BYTES, signal)
      return responseText(payload)
    } catch (error) {
      if (!(error instanceof ApiError) || error.code !== 'cliproxy_endpoint_unsupported') throw error
    }

    const payload = await this.request('/v1/chat/completions', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        model: input.model,
        messages: [{
          role: 'user',
          content: input.image ? [
            { type: 'text', text: input.prompt },
            { type: 'image_url', image_url: { url: `data:${input.image.mimeType};base64,${input.image.base64}` } },
          ] : input.prompt,
        }],
        max_completion_tokens: MAX_TEXT_OUTPUT_TOKENS,
        stream: false,
      }),
    }, this.textTimeoutMs, MAX_TEXT_RESPONSE_BYTES, signal)
    const record = payload && typeof payload === 'object' && !Array.isArray(payload)
      ? payload as Record<string, unknown>
      : null
    const firstChoice = Array.isArray(record?.choices) ? record.choices[0] : null
    const choice = firstChoice && typeof firstChoice === 'object' && !Array.isArray(firstChoice)
      ? firstChoice as Record<string, unknown>
      : null
    const message = choice?.message && typeof choice.message === 'object' && !Array.isArray(choice.message)
      ? choice.message as Record<string, unknown>
      : null
    return (contentText(message?.content) || (typeof choice?.text === 'string' ? choice.text : '')).trim()
  }

  async generate(request: AiGenerationRequest, signal?: AbortSignal): Promise<AiGenerationResponse> {
    const input = parseGenerationRequest(request)
    await this.assertAvailable(input.model, input.modality, signal)
    if (input.modality === 'text') {
      const text = await this.generateText(input, signal)
      if (!text || text.length > MAX_TEXT_OUTPUT_CHARS) {
        throw new ApiError(502, 'cliproxy_invalid_response', '文本模型返回为空或超过安全上限')
      }
      return { modality: 'text', model: input.model, text }
    }

    let pathname: string
    let init: RequestInit
    if (input.image) {
      const form = new FormData()
      form.set('model', input.model)
      form.set('prompt', input.prompt)
      form.set('size', imageSize(input.aspectRatio))
      form.set('quality', input.quality === 'high' ? 'high' : 'medium')
      form.set('response_format', 'b64_json')
      const bytes = Uint8Array.from(Buffer.from(input.image.base64, 'base64'))
      const extension = input.image.mimeType === 'image/jpeg' ? 'jpg' : input.image.mimeType.split('/')[1] || 'png'
      form.set('image', new Blob([bytes], { type: input.image.mimeType }), `reference.${extension}`)
      pathname = '/v1/images/edits'
      init = { method: 'POST', body: form }
    } else {
      pathname = '/v1/images/generations'
      init = {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          model: input.model,
          prompt: input.prompt,
          size: imageSize(input.aspectRatio),
          quality: input.quality === 'high' ? 'high' : 'medium',
          response_format: 'b64_json',
        }),
      }
    }
    const payload = await this.request(pathname, init, this.imageTimeoutMs, MAX_IMAGE_RESPONSE_BYTES, signal)
    const record = payload && typeof payload === 'object' && !Array.isArray(payload)
      ? payload as Record<string, unknown>
      : null
    const firstImage = Array.isArray(record?.data) ? record.data[0] : null
    const image = firstImage && typeof firstImage === 'object' && !Array.isArray(firstImage)
      ? firstImage as Record<string, unknown>
      : null
    const rawBase64 = typeof image?.b64_json === 'string' ? image.b64_json.replace(/\s/g, '') : ''
    if (!rawBase64 || !/^[a-zA-Z0-9+/]+={0,2}$/.test(rawBase64)) {
      throw new ApiError(502, 'cliproxy_invalid_response', '图片模型未返回可用的 base64 图片')
    }
    const bytes = Buffer.from(rawBase64, 'base64')
    const mimeType = imageMimeType(bytes)
    if (!bytes.length || bytes.length > MAX_IMAGE_BYTES || !mimeType) {
      throw new ApiError(502, 'cliproxy_invalid_response', '图片模型返回的文件无效或超过 20MB')
    }
    const revisedPrompt = typeof image?.revised_prompt === 'string'
      ? image.revised_prompt.trim().slice(0, MAX_PROMPT_CHARS)
      : ''
    return {
      modality: 'image',
      model: input.model,
      image: {
        base64: bytes.toString('base64'),
        mimeType,
        ...(revisedPrompt ? { revisedPrompt } : {}),
      },
    }
  }
}
