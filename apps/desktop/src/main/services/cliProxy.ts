import fsp from 'node:fs/promises'
import { app } from 'electron'

const DEFAULT_BASE_URL = 'http://127.0.0.1:8317'
const DEVELOPMENT_CONFIG_PATH = '/opt/homebrew/etc/cliproxyapi.conf'
const MODEL_CACHE_TTL_MS = 60_000
const MODEL_TIMEOUT_MS = 8_000
const TEXT_TIMEOUT_MS = 90_000
const IMAGE_TIMEOUT_MS = 180_000
const MAX_CONFIG_BYTES = 256 * 1024
const MAX_MODEL_RESPONSE_BYTES = 2 * 1024 * 1024
const MAX_TEXT_RESPONSE_BYTES = 4 * 1024 * 1024
const MAX_IMAGE_RESPONSE_BYTES = 32 * 1024 * 1024
const MAX_TEXT_OUTPUT_CHARS = 80_000
const MAX_TEXT_OUTPUT_TOKENS = 8_192
const MAX_IMAGE_BYTES = 20 * 1024 * 1024
const MAX_INPUT_IMAGE_BYTES = 12 * 1024 * 1024
export const MAX_CANVAS_PROMPT_CHARS = 24_000

const MODEL_ID_PATTERN = /^[a-zA-Z0-9._:/-]{1,160}$/
const GPT_MODEL_PATTERN = /^(?:[a-z0-9._-]+\/)*gpt(?:-|$)/i
const GPT_IMAGE_MODEL_PATTERN = /(?:^|\/)gpt-image(?:-|$)|(?:^|\/)dall-e(?:-|$)/i
const ASPECT_RATIOS = new Set(['1:1', '3:2', '2:3', '4:3', '3:4', '16:9', '9:16'])

export type CanvasGenerationModality = 'text' | 'image'

export interface CanvasModel {
  id: string
  label: string
  modality: CanvasGenerationModality
  provider: 'cli-proxy-api'
}

export interface CanvasGenerationRequest {
  modality: CanvasGenerationModality
  model: string
  prompt: string
  aspectRatio?: string
  image?: { base64: string; mimeType: string }
}

export interface CanvasTextGenerationResult {
  modality: 'text'
  model: string
  text: string
}

export interface CanvasImageGenerationResult {
  modality: 'image'
  model: string
  image: {
    base64: string
    mimeType: string
    revisedPrompt?: string
  }
}

export type CanvasGenerationResult = CanvasTextGenerationResult | CanvasImageGenerationResult

export class CliProxyError extends Error {
  readonly name = 'CliProxyError'

  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message)
  }
}

interface CliProxyConfiguration {
  baseUrl: string
  apiKey: string
}

interface ModelCache {
  expiresAt: number
  models: CanvasModel[]
}

function stripYamlComment(value: string): string {
  let quote: '"' | "'" | null = null
  for (let index = 0; index < value.length; index += 1) {
    const character = value[index]
    if (quote) {
      if (character === quote && (quote === "'" || value[index - 1] !== '\\')) quote = null
      continue
    }
    if (character === '"' || character === "'") quote = character
    else if (character === '#') return value.slice(0, index).trim()
  }
  return value.trim()
}

function yamlScalar(value: string): string | null {
  const withoutComment = stripYamlComment(value).trim().replace(/,$/, '').trim()
  if (!withoutComment) return null
  let scalar = withoutComment
  if ((scalar.startsWith('"') && scalar.endsWith('"')) || (scalar.startsWith("'") && scalar.endsWith("'"))) {
    scalar = scalar.slice(1, -1)
    if (withoutComment.startsWith('"')) {
      try {
        scalar = JSON.parse(withoutComment) as string
      } catch {
        return null
      }
    } else {
      scalar = scalar.replace(/''/g, "'")
    }
  }
  if (scalar.length < 8 || scalar.length > 4096 || /[\s\u0000-\u001f\u007f]/.test(scalar)) return null
  return scalar
}

/** Parse only the first scalar in the top-level api-keys array; never interpret YAML tags or aliases. */
export function firstApiKeyFromConfig(contents: string): string | null {
  const lines = contents.split(/\r?\n/)
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index] ?? ''
    const match = line.match(/^(\s*)api-keys\s*:\s*(.*?)\s*$/)
    if (!match || match[1].length !== 0) continue
    const inline = stripYamlComment(match[2] ?? '')
    if (inline.startsWith('[')) {
      const closingIndex = inline.lastIndexOf(']')
      if (closingIndex <= 0) return null
      const body = inline.slice(1, closingIndex)
      let quote: '"' | "'" | null = null
      let first = body
      for (let cursor = 0; cursor < body.length; cursor += 1) {
        const character = body[cursor]
        if (quote) {
          if (character === quote && (quote === "'" || body[cursor - 1] !== '\\')) quote = null
        } else if (character === '"' || character === "'") quote = character
        else if (character === ',') {
          first = body.slice(0, cursor)
          break
        }
      }
      return yamlScalar(first)
    }
    if (inline) return yamlScalar(inline)

    for (let childIndex = index + 1; childIndex < lines.length; childIndex += 1) {
      const child = lines[childIndex] ?? ''
      if (!child.trim() || child.trimStart().startsWith('#')) continue
      const indentation = child.match(/^\s*/)?.[0].length ?? 0
      if (indentation === 0) break
      const item = child.match(/^\s+-\s+(.+?)\s*$/)
      if (item) return yamlScalar(item[1] ?? '')
      break
    }
    return null
  }
  return null
}

function normalizeBaseUrl(value: string): string {
  let url: URL
  try {
    url = new URL(value)
  } catch {
    throw new CliProxyError(503, 'cli_proxy_invalid_config', 'CLI_PROXY_API_URL 不是有效 URL')
  }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new CliProxyError(503, 'cli_proxy_invalid_config', 'CLI_PROXY_API_URL 必须是无凭据、查询参数或片段的 HTTP(S) URL')
  }
  url.pathname = url.pathname.replace(/\/+$/, '').replace(/\/v1$/i, '') || '/'
  return url.toString().replace(/\/$/, '')
}

function isLoopbackUrl(value: string): boolean {
  const hostname = new URL(value).hostname.toLowerCase()
  return hostname === '127.0.0.1' || hostname === 'localhost' || hostname === '[::1]'
}

function endpoint(baseUrl: string, pathname: string): string {
  return `${baseUrl}${pathname.startsWith('/') ? pathname : `/${pathname}`}`
}

function parseGenerationRequest(value: unknown): CanvasGenerationRequest {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new CliProxyError(400, 'canvas_generation_invalid_request', '生成请求格式无效')
  }
  const input = value as Record<string, unknown>
  const modality = input.modality
  if (modality !== 'text' && modality !== 'image') {
    throw new CliProxyError(400, 'canvas_generation_invalid_request', 'modality 必须是 text 或 image')
  }
  const model = typeof input.model === 'string' ? input.model.trim() : ''
  if (!MODEL_ID_PATTERN.test(model)) {
    throw new CliProxyError(400, 'canvas_generation_invalid_request', '模型 ID 无效')
  }
  const prompt = typeof input.prompt === 'string' ? input.prompt.trim() : ''
  if (!prompt || prompt.length > MAX_CANVAS_PROMPT_CHARS) {
    throw new CliProxyError(400, 'canvas_generation_invalid_request', `Prompt 不能为空且不能超过 ${MAX_CANVAS_PROMPT_CHARS} 个字符`)
  }
  const aspectRatio = typeof input.aspectRatio === 'string' && input.aspectRatio.trim()
    ? input.aspectRatio.trim()
    : undefined
  if (aspectRatio && (modality !== 'image' || !ASPECT_RATIOS.has(aspectRatio))) {
    throw new CliProxyError(400, 'canvas_generation_invalid_request', '图片比例仅支持 1:1、3:2、2:3、4:3、3:4、16:9 或 9:16')
  }
  let image: CanvasGenerationRequest['image']
  if (input.image !== undefined) {
    if (modality !== 'text' || !input.image || typeof input.image !== 'object' || Array.isArray(input.image)) {
      throw new CliProxyError(400, 'canvas_generation_invalid_request', '参考图片仅支持文本模型视觉分析')
    }
    const rawImage = input.image as Record<string, unknown>
    const base64 = typeof rawImage.base64 === 'string' ? rawImage.base64.replace(/\s/g, '') : ''
    const mimeType = typeof rawImage.mimeType === 'string' ? rawImage.mimeType : ''
    if (!base64 || !/^[a-zA-Z0-9+/]+={0,2}$/.test(base64)) {
      throw new CliProxyError(400, 'canvas_generation_invalid_request', '参考图片不是有效 base64')
    }
    const bytes = Buffer.from(base64, 'base64')
    const detectedMimeType = imageMimeType(bytes)
    if (!bytes.length || bytes.length > MAX_INPUT_IMAGE_BYTES || detectedMimeType !== mimeType) {
      throw new CliProxyError(400, 'canvas_generation_invalid_request', '参考图片格式无效或超过 12MB')
    }
    image = { base64: bytes.toString('base64'), mimeType }
  }
  return { modality, model, prompt, ...(aspectRatio ? { aspectRatio } : {}), ...(image ? { image } : {}) }
}

function imageSize(aspectRatio?: string): '1024x1024' | '1536x1024' | '1024x1536' {
  if (aspectRatio === '16:9' || aspectRatio === '3:2' || aspectRatio === '4:3') return '1536x1024'
  if (aspectRatio === '9:16' || aspectRatio === '2:3' || aspectRatio === '3:4') return '1024x1536'
  return '1024x1024'
}

function contentText(value: unknown): string {
  if (typeof value === 'string') return value
  if (!Array.isArray(value)) return ''
  return value
    .map((part) => {
      if (!part || typeof part !== 'object' || Array.isArray(part)) return ''
      const record = part as Record<string, unknown>
      return (record.type === 'text' || record.type === 'output_text') && typeof record.text === 'string'
        ? record.text
        : ''
    })
    .join('')
}

function imageMimeType(bytes: Buffer): string | null {
  if (bytes.length >= 8 && bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) return 'image/png'
  if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return 'image/jpeg'
  if (bytes.length >= 12 && bytes.subarray(0, 4).toString('ascii') === 'RIFF' && bytes.subarray(8, 12).toString('ascii') === 'WEBP') return 'image/webp'
  if (bytes.length >= 6 && /^GIF8[79]a$/.test(bytes.subarray(0, 6).toString('ascii'))) return 'image/gif'
  return null
}

async function limitedResponseBuffer(response: Response, maxBytes: number): Promise<Buffer> {
  const declaredLength = Number(response.headers.get('content-length') ?? NaN)
  if (Number.isFinite(declaredLength) && declaredLength > maxBytes) {
    await response.body?.cancel().catch(() => undefined)
    throw new CliProxyError(502, 'cli_proxy_output_too_large', 'cli-proxy-api 返回内容超过安全上限')
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
      if (size > maxBytes) {
        await reader.cancel().catch(() => undefined)
        throw new CliProxyError(502, 'cli_proxy_output_too_large', 'cli-proxy-api 返回内容超过安全上限')
      }
      chunks.push(chunk)
    }
  } finally {
    reader.releaseLock()
  }
  return Buffer.concat(chunks, size)
}

async function limitedJson(response: Response, maxBytes: number): Promise<unknown> {
  const contents = (await limitedResponseBuffer(response, maxBytes)).toString('utf8')
  try {
    return JSON.parse(contents) as unknown
  } catch {
    throw new CliProxyError(502, 'cli_proxy_invalid_response', 'cli-proxy-api 返回了无效 JSON')
  }
}

function upstreamFailure(status: number): CliProxyError {
  if (status === 401 || status === 403) {
    return new CliProxyError(502, 'cli_proxy_auth_failed', 'cli-proxy-api 鉴权失败，请检查桌面端 API Key')
  }
  if (status === 404 || status === 405 || status === 501) {
    return new CliProxyError(501, 'cli_proxy_endpoint_unsupported', '当前 cli-proxy-api 不支持所需的生成接口')
  }
  if (status === 408 || status === 504) {
    return new CliProxyError(504, 'cli_proxy_timeout', 'cli-proxy-api 请求超时')
  }
  if (status === 429) {
    return new CliProxyError(429, 'cli_proxy_rate_limited', '共享模型当前繁忙，请稍后重试')
  }
  return new CliProxyError(502, 'cli_proxy_request_failed', `cli-proxy-api 请求失败（HTTP ${status}）`)
}

export class CliProxyService {
  private configurationPromise: Promise<CliProxyConfiguration> | null = null
  private modelCache: ModelCache | null = null

  private async configuration(): Promise<CliProxyConfiguration> {
    if (this.configurationPromise) return this.configurationPromise
    this.configurationPromise = (async () => {
      const baseUrl = normalizeBaseUrl(
        process.env.CLI_PROXY_API_URL?.trim()
          || process.env.CUSTOM_OPENAI_BASE_URL?.trim()
          || DEFAULT_BASE_URL,
      )
      const explicitApiKey = process.env.CLI_PROXY_API_KEY?.trim()
        || process.env.CUSTOM_OPENAI_API_KEY?.trim()
        || ''
      if (!isLoopbackUrl(baseUrl) && new URL(baseUrl).protocol !== 'https:') {
        throw new CliProxyError(503, 'cli_proxy_invalid_config', '远程 CLI_PROXY_API_URL 必须使用 HTTPS')
      }
      let apiKey = explicitApiKey
      if (!apiKey && baseUrl === DEFAULT_BASE_URL && process.platform === 'darwin' && !app.isPackaged) {
        try {
          const stat = await fsp.stat(DEVELOPMENT_CONFIG_PATH)
          if (!stat.isFile() || stat.size > MAX_CONFIG_BYTES) {
            throw new CliProxyError(503, 'cli_proxy_invalid_config', 'cli-proxy-api 开发配置文件无效或过大')
          }
          apiKey = firstApiKeyFromConfig(await fsp.readFile(DEVELOPMENT_CONFIG_PATH, 'utf8')) ?? ''
        } catch (error) {
          if (error instanceof CliProxyError) throw error
          const code = (error as NodeJS.ErrnoException).code
          if (code !== 'ENOENT' && code !== 'EACCES') {
            throw new CliProxyError(503, 'cli_proxy_invalid_config', '无法读取 cli-proxy-api 开发配置')
          }
        }
      }
      if (!apiKey || apiKey.length > 4096 || /[\s\u0000-\u001f\u007f]/.test(apiKey)) {
        throw new CliProxyError(
          503,
          'cli_proxy_not_configured',
          '未配置 cli-proxy-api：请在桌面端设置 CLI_PROXY_API_KEY 或 CUSTOM_OPENAI_API_KEY',
        )
      }
      return { baseUrl, apiKey }
    })()
    return this.configurationPromise
  }

  private async request(pathname: string, init: RequestInit, timeoutMs: number, maxBytes: number, externalSignal?: AbortSignal): Promise<unknown> {
    const config = await this.configuration()
    const controller = new AbortController()
    const abortFromCaller = () => controller.abort()
    if (externalSignal?.aborted) controller.abort()
    else externalSignal?.addEventListener('abort', abortFromCaller, { once: true })
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    try {
      const headers = new Headers(init.headers)
      headers.set('authorization', `Bearer ${config.apiKey}`)
      headers.set('accept', 'application/json')
      const response = await fetch(endpoint(config.baseUrl, pathname), { ...init, headers, signal: controller.signal, redirect: 'error' })
      if (!response.ok) {
        await limitedResponseBuffer(response, 64 * 1024).catch(() => undefined)
        throw upstreamFailure(response.status)
      }
      return await limitedJson(response, maxBytes)
    } catch (error) {
      if (error instanceof CliProxyError) throw error
      if (externalSignal?.aborted) {
        throw new CliProxyError(499, 'cli_proxy_cancelled', '生成请求已取消')
      }
      if (error instanceof Error && error.name === 'AbortError') {
        throw new CliProxyError(504, 'cli_proxy_timeout', 'cli-proxy-api 请求超时')
      }
      throw new CliProxyError(503, 'cli_proxy_unavailable', '无法连接本机 cli-proxy-api')
    } finally {
      clearTimeout(timer)
      externalSignal?.removeEventListener('abort', abortFromCaller)
    }
  }

  async discoverCanvasModels(forceRefresh = false, signal?: AbortSignal): Promise<{ models: CanvasModel[] }> {
    if (!forceRefresh && this.modelCache && this.modelCache.expiresAt > Date.now()) {
      return { models: this.modelCache.models }
    }
    const payload = await this.request('/v1/models', { method: 'GET' }, MODEL_TIMEOUT_MS, MAX_MODEL_RESPONSE_BYTES, signal)
    const data = payload && typeof payload === 'object' && !Array.isArray(payload)
      ? (payload as Record<string, unknown>).data
      : null
    if (!Array.isArray(data)) {
      throw new CliProxyError(502, 'cli_proxy_invalid_response', 'cli-proxy-api 模型列表格式无效')
    }
    const seen = new Set<string>()
    const models: CanvasModel[] = []
    for (const raw of data) {
      if (!raw || typeof raw !== 'object' || Array.isArray(raw)) continue
      const id = typeof (raw as Record<string, unknown>).id === 'string'
        ? ((raw as Record<string, unknown>).id as string).trim()
        : ''
      if (!MODEL_ID_PATTERN.test(id) || !GPT_MODEL_PATTERN.test(id) || seen.has(id)) continue
      const modality: CanvasGenerationModality = GPT_IMAGE_MODEL_PATTERN.test(id) ? 'image' : 'text'
      seen.add(id)
      models.push({ id, label: id, modality, provider: 'cli-proxy-api' })
    }
    models.sort((left, right) => left.modality.localeCompare(right.modality) || left.id.localeCompare(right.id))
    this.modelCache = { expiresAt: Date.now() + MODEL_CACHE_TTL_MS, models }
    return { models }
  }

  private async assertAvailable(model: string, modality: CanvasGenerationModality, signal?: AbortSignal): Promise<void> {
    let models = (await this.discoverCanvasModels(false, signal)).models
    if (!models.some((candidate) => candidate.id === model && candidate.modality === modality)) {
      models = (await this.discoverCanvasModels(true, signal)).models
    }
    if (!models.some((candidate) => candidate.id === model && candidate.modality === modality)) {
      throw new CliProxyError(400, 'canvas_model_unavailable', `模型 ${model} 不可用或不支持 ${modality} 生成`)
    }
  }

  private responseText(payload: unknown): string {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return ''
    const record = payload as Record<string, unknown>
    if (typeof record.output_text === 'string' && record.output_text.trim()) return record.output_text.trim()
    if (!Array.isArray(record.output)) return ''
    return record.output
      .map((item) => {
        if (!item || typeof item !== 'object' || Array.isArray(item)) return ''
        return contentText((item as Record<string, unknown>).content)
      })
      .join('')
      .trim()
  }

  private async generateText(input: CanvasGenerationRequest, signal?: AbortSignal): Promise<string> {
    try {
      const payload = await this.request('/v1/responses', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          model: input.model,
          max_output_tokens: MAX_TEXT_OUTPUT_TOKENS,
          reasoning: { effort: 'none', context: 'current_turn' },
          text: { verbosity: 'medium' },
          input: input.image ? [{
            role: 'user',
            content: [
              { type: 'input_text', text: input.prompt },
              { type: 'input_image', image_url: `data:${input.image.mimeType};base64,${input.image.base64}` },
            ],
          }] : input.prompt,
        }),
      }, TEXT_TIMEOUT_MS, MAX_TEXT_RESPONSE_BYTES, signal)
      return this.responseText(payload)
    } catch (error) {
      if (!(error instanceof CliProxyError) || error.code !== 'cli_proxy_endpoint_unsupported') throw error
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
    }, TEXT_TIMEOUT_MS, MAX_TEXT_RESPONSE_BYTES, signal)
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

  async generateCanvasContent(value: unknown, signal?: AbortSignal): Promise<CanvasGenerationResult> {
    const input = parseGenerationRequest(value)
    await this.assertAvailable(input.model, input.modality, signal)
    if (input.modality === 'text') {
      const text = await this.generateText(input, signal)
      if (!text || text.length > MAX_TEXT_OUTPUT_CHARS) {
        throw new CliProxyError(502, 'cli_proxy_invalid_response', '文本模型返回为空或超过安全上限')
      }
      return { modality: 'text', model: input.model, text }
    }

    const payload = await this.request('/v1/images/generations', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        model: input.model,
        prompt: input.prompt,
        size: imageSize(input.aspectRatio),
        response_format: 'b64_json',
      }),
    }, IMAGE_TIMEOUT_MS, MAX_IMAGE_RESPONSE_BYTES, signal)
    const record = payload && typeof payload === 'object' && !Array.isArray(payload)
      ? payload as Record<string, unknown>
      : null
    const firstImage = Array.isArray(record?.data) ? record.data[0] : null
    const image = firstImage && typeof firstImage === 'object' && !Array.isArray(firstImage)
      ? firstImage as Record<string, unknown>
      : null
    const rawBase64 = typeof image?.b64_json === 'string' ? image.b64_json.replace(/\s/g, '') : ''
    if (!rawBase64 || !/^[a-zA-Z0-9+/]+={0,2}$/.test(rawBase64)) {
      throw new CliProxyError(502, 'cli_proxy_invalid_response', '图片模型未返回可用的 base64 图片')
    }
    const bytes = Buffer.from(rawBase64, 'base64')
    const mimeType = imageMimeType(bytes)
    if (!bytes.length || bytes.length > MAX_IMAGE_BYTES || !mimeType) {
      throw new CliProxyError(502, 'cli_proxy_invalid_response', '图片模型返回的文件无效或超过 20MB')
    }
    const revisedPrompt = typeof image?.revised_prompt === 'string'
      ? image.revised_prompt.trim().slice(0, MAX_CANVAS_PROMPT_CHARS)
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
