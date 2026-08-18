import fsp from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

import { ApiError } from './errors.ts'
import type { AuthConfiguration } from './auth.ts'

export const SERVICE_NAME = 'anime-armory-backend' as const
export const SERVICE_VERSION = 1
export const DEFAULT_HOST = '127.0.0.1'
export const DEFAULT_PORT = 43_118
export const DEFAULT_CLIPROXY_URL = 'http://127.0.0.1:8317'
export const DEFAULT_CLIPROXY_CONFIG = '/opt/homebrew/etc/cliproxyapi.conf'
const MAX_CONFIG_BYTES = 256 * 1024

export const REPOSITORY_ROOT = fileURLToPath(new URL('../../..', import.meta.url))
export const DEFAULT_SKILLS_ROOT = path.join(REPOSITORY_ROOT, 'skills')
export const DEFAULT_RUNTIME_ROOT = path.join(REPOSITORY_ROOT, 'apps/backend/.runtime')

export interface BackendConfig {
  host: string
  port: number
  allowedOrigins: ReadonlySet<string>
  skillsRoot: string
  runtimeRoot: string
  maxBodyBytes: number
  maxUploadBytes: number
  maxConcurrentGenerations: number
  maxRequestsPerMinute: number
  auth?: AuthConfiguration
}

export interface CliProxyConfiguration {
  baseUrl: string
  apiKey: string
}

function parseInteger(value: string | undefined, fallback: number, minimum: number, maximum: number): number {
  if (value === undefined || value.trim() === '') return fallback
  const parsed = Number(value)
  if (!Number.isInteger(parsed) || parsed < minimum || parsed > maximum) {
    throw new ApiError(500, 'invalid_server_config', `服务端整数配置必须在 ${minimum} 到 ${maximum} 之间`)
  }
  return parsed
}

function isLoopbackHost(hostname: string): boolean {
  const normalized = hostname.toLowerCase()
  return normalized === '127.0.0.1' || normalized === 'localhost' || normalized === '[::1]' || normalized === '::1'
}

export function normalizeCliProxyBaseUrl(value: string): string {
  let url: URL
  try {
    url = new URL(value)
  } catch {
    throw new ApiError(503, 'cliproxy_invalid_config', 'CLI_PROXY_API_URL 不是有效 URL')
  }
  if ((url.protocol !== 'http:' && url.protocol !== 'https:')
    || url.username || url.password || url.search || url.hash) {
    throw new ApiError(
      503,
      'cliproxy_invalid_config',
      'CLI_PROXY_API_URL 必须是无凭据、查询参数或片段的 HTTP(S) URL',
    )
  }
  if (url.protocol === 'http:' && !isLoopbackHost(url.hostname)) {
    throw new ApiError(503, 'cliproxy_invalid_config', '远程 CLI_PROXY_API_URL 必须使用 HTTPS')
  }
  url.pathname = url.pathname.replace(/\/+$/, '').replace(/\/v1$/i, '') || '/'
  return url.toString().replace(/\/$/, '')
}

function stripYamlComment(value: string): string {
  let quote: '"' | "'" | null = null
  for (let index = 0; index < value.length; index += 1) {
    const character = value[index]
    if (quote) {
      if (character === quote && (quote === "'" || value[index - 1] !== '\\')) quote = null
    } else if (character === '"' || character === "'") {
      quote = character
    } else if (character === '#') {
      return value.slice(0, index).trim()
    }
  }
  return value.trim()
}

function yamlScalar(value: string): string | null {
  const withoutComment = stripYamlComment(value).trim().replace(/,$/, '').trim()
  if (!withoutComment) return null
  let scalar = withoutComment
  if ((scalar.startsWith('"') && scalar.endsWith('"')) || (scalar.startsWith("'") && scalar.endsWith("'"))) {
    if (scalar.startsWith('"')) {
      try {
        scalar = JSON.parse(scalar) as string
      } catch {
        return null
      }
    } else {
      scalar = scalar.slice(1, -1).replace(/''/g, "'")
    }
  }
  if (scalar.length < 8 || scalar.length > 4096 || /[\s\u0000-\u001f\u007f]/.test(scalar)) return null
  return scalar
}

export function firstApiKeyFromConfig(contents: string): string | null {
  const lines = contents.split(/\r?\n/)
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index] ?? ''
    const match = line.match(/^(\s*)api-keys\s*:\s*(.*?)\s*$/)
    if (!match || (match[1] ?? '').length !== 0) continue
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
      if ((child.match(/^\s*/)?.[0].length ?? 0) === 0) break
      const item = child.match(/^\s+-\s+(.+?)\s*$/)
      if (item) return yamlScalar(item[1] ?? '')
      break
    }
    return null
  }
  return null
}

async function apiKeyFromConfigFile(configPath: string): Promise<string> {
  try {
    const stat = await fsp.lstat(configPath)
    if (!stat.isFile() || stat.isSymbolicLink() || stat.size > MAX_CONFIG_BYTES) {
      throw new ApiError(503, 'cliproxy_invalid_config', 'cliproxy 开发配置文件无效或过大')
    }
    return firstApiKeyFromConfig(await fsp.readFile(configPath, 'utf8')) ?? ''
  } catch (error) {
    if (error instanceof ApiError) throw error
    const code = (error as NodeJS.ErrnoException).code
    if (code === 'ENOENT' || code === 'EACCES') return ''
    throw new ApiError(503, 'cliproxy_invalid_config', '无法读取 cliproxy 开发配置')
  }
}

export async function resolveCliProxyConfiguration(
  environment: NodeJS.ProcessEnv = process.env,
  configPath = DEFAULT_CLIPROXY_CONFIG,
): Promise<CliProxyConfiguration> {
  if (environment.VITE_CLI_PROXY_API_KEY || environment.VITE_CUSTOM_OPENAI_API_KEY) {
    throw new ApiError(503, 'cliproxy_invalid_config', '检测到浏览器可见的 VITE_* 模型密钥，请移除')
  }
  const baseUrl = normalizeCliProxyBaseUrl(environment.CLI_PROXY_API_URL?.trim() || DEFAULT_CLIPROXY_URL)
  let apiKey = environment.CLI_PROXY_API_KEY?.trim() ?? ''
  if (!apiKey) apiKey = await apiKeyFromConfigFile(configPath)
  if (!apiKey || apiKey.length > 4096 || /[\s\u0000-\u001f\u007f]/.test(apiKey)) {
    throw new ApiError(503, 'cliproxy_not_configured', '未配置 CLI_PROXY_API_KEY，且未找到可用的本机 cliproxy 配置')
  }
  return { baseUrl, apiKey }
}

export function loadBackendConfig(environment: NodeJS.ProcessEnv = process.env): BackendConfig {
  const host = environment.BACKEND_HOST?.trim() || DEFAULT_HOST
  if (host !== '127.0.0.1' && host !== '::1' && host !== 'localhost') {
    throw new ApiError(500, 'invalid_server_config', '开发后端只允许绑定回环地址')
  }
  const originValues = (environment.BACKEND_ALLOWED_ORIGINS
    ?? 'http://127.0.0.1:4174,http://localhost:4174,http://[::1]:4174,http://127.0.0.1:5173,http://localhost:5173')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean)
  const allowedOrigins = new Set<string>()
  for (const value of originValues) {
    let origin: URL
    try {
      origin = new URL(value)
    } catch {
      throw new ApiError(500, 'invalid_server_config', 'BACKEND_ALLOWED_ORIGINS 包含无效 URL')
    }
    if (origin.protocol !== 'http:' || !isLoopbackHost(origin.hostname) || origin.origin !== value) {
      throw new ApiError(500, 'invalid_server_config', '开发 CORS Origin 必须是明确的本地 HTTP Origin')
    }
    allowedOrigins.add(origin.origin)
  }
  const supabaseUrlValue = environment.SUPABASE_URL?.trim() ?? ''
  const publishableKey = (environment.SUPABASE_PUBLISHABLE_KEY ?? environment.SUPABASE_ANON_KEY)?.trim() ?? ''
  if (Boolean(supabaseUrlValue) !== Boolean(publishableKey)) {
    throw new ApiError(500, 'invalid_server_config', 'SUPABASE_URL 与 SUPABASE_PUBLISHABLE_KEY 必须同时配置')
  }
  let auth: AuthConfiguration | undefined
  if (supabaseUrlValue && publishableKey) {
    let supabaseUrl: URL
    try {
      supabaseUrl = new URL(supabaseUrlValue)
    } catch {
      throw new ApiError(500, 'invalid_server_config', 'SUPABASE_URL 不是有效 URL')
    }
    if ((supabaseUrl.protocol !== 'https:' && !(supabaseUrl.protocol === 'http:' && isLoopbackHost(supabaseUrl.hostname)))
      || supabaseUrl.username || supabaseUrl.password || supabaseUrl.search || supabaseUrl.hash) {
      throw new ApiError(500, 'invalid_server_config', 'SUPABASE_URL 必须使用 HTTPS（本地回环地址除外）且不能包含凭据、查询参数或片段')
    }
    if (publishableKey.length < 20 || publishableKey.length > 4096 || /[\s\u0000-\u001f\u007f]/.test(publishableKey)) {
      throw new ApiError(500, 'invalid_server_config', 'SUPABASE_PUBLISHABLE_KEY 格式无效')
    }
    auth = {
      supabaseUrl: supabaseUrl.toString().replace(/\/+$/, ''),
      publishableKey,
    }
  }
  return {
    host,
    port: parseInteger(environment.BACKEND_PORT, DEFAULT_PORT, 1, 65_535),
    allowedOrigins,
    skillsRoot: environment.BACKEND_SKILLS_ROOT?.trim() || DEFAULT_SKILLS_ROOT,
    runtimeRoot: environment.BACKEND_RUNTIME_ROOT?.trim() || DEFAULT_RUNTIME_ROOT,
    maxBodyBytes: parseInteger(environment.BACKEND_MAX_BODY_BYTES, 18 * 1024 * 1024, 1024, 32 * 1024 * 1024),
    maxUploadBytes: parseInteger(environment.BACKEND_MAX_UPLOAD_BYTES, 12 * 1024 * 1024, 1024, 24 * 1024 * 1024),
    maxConcurrentGenerations: parseInteger(environment.BACKEND_MAX_CONCURRENT_GENERATIONS, 3, 1, 16),
    maxRequestsPerMinute: parseInteger(environment.BACKEND_MAX_REQUESTS_PER_MINUTE, 120, 10, 10_000),
    ...(auth ? { auth } : {}),
  }
}
