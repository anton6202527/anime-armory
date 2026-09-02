import { execFile } from 'node:child_process'
import type { AgentInfo, CodexModelInfo } from '@shared/types'

const PROBE_TIMEOUT = 8000

interface AgentDef {
  id: string
  name: string
  command: string
  binaries: string[]
  image: AgentInfo['image']
}

const AGENT_DEFS: AgentDef[] = [
  { id: 'claude', name: 'Claude Code', command: 'claude', binaries: ['claude'], image: 'maybe' },
  { id: 'codex', name: 'Codex CLI', command: 'codex', binaries: ['codex'], image: 'maybe' },
  { id: 'opencode', name: 'OpenCode', command: 'opencode', binaries: ['opencode'], image: 'no' },
  { id: 'gemini', name: 'Gemini CLI', command: 'gemini', binaries: ['gemini'], image: 'maybe' },
  { id: 'kimi', name: 'Kimi CLI', command: 'kimi', binaries: ['kimi', 'kimi-cli'], image: 'no' },
]

function runLoginShell(cmd: string, timeout: number): Promise<string> {
  return new Promise((resolve) => {
    const shell = process.env.SHELL || '/bin/zsh'
    const child = execFile(shell, ['-lc', cmd], { timeout }, (_err, stdout) => {
      resolve(stdout ?? '')
    })
    child.stdin?.end()
  })
}

function runExecutable(file: string, args: string[], timeout: number): Promise<string> {
  return new Promise((resolve) => {
    const child = execFile(file, args, { timeout }, (_err, stdout, stderr) => {
      resolve(`${stdout ?? ''}\n${stderr ?? ''}`)
    })
    child.stdin?.end()
  })
}

function runExecutableStdout(file: string, args: string[], timeout: number): Promise<string> {
  return new Promise((resolve) => {
    const child = execFile(file, args, { timeout, maxBuffer: 2 * 1024 * 1024 }, (error, stdout) => {
      resolve(error ? '' : stdout ?? '')
    })
    child.stdin?.end()
  })
}

// Probing forks a login shell (plus a second one when codex is present),
// which is slow and effectively deterministic within a session — cache it.
const DETECT_TTL = 60 * 1000
const CODEX_MODELS_TTL = 5 * 60 * 1000
let detectCache: { at: number; promise: Promise<AgentInfo[]> } | null = null
let codexModelsCache: { at: number; promise: Promise<CodexModelInfo[]> } | null = null

/**
 * Detect installed AI CLIs by probing the user's *login* shell once
 * (so PATH matches what the in-app terminal will see).
 */
export function detectAgents(force = false): Promise<AgentInfo[]> {
  const now = Date.now()
  if (!force && detectCache && now - detectCache.at < DETECT_TTL) return detectCache.promise
  const promise = detectAgentsUncached().catch((error) => {
    detectCache = null // don't cache failures
    throw error
  })
  detectCache = { at: now, promise }
  return promise
}

/**
 * Read the current ChatGPT account's visible Codex model catalog. The raw
 * catalog contains large instruction payloads, so only safe picker fields are
 * projected outside this adapter.
 */
export function detectCodexModels(force = false): Promise<CodexModelInfo[]> {
  const now = Date.now()
  if (!force && codexModelsCache && now - codexModelsCache.at < CODEX_MODELS_TTL) return codexModelsCache.promise
  const promise = detectCodexModelsUncached().catch(() => [])
  codexModelsCache = { at: now, promise }
  void promise.then((models) => {
    if (!models.length && codexModelsCache?.promise === promise) codexModelsCache = null
  })
  return promise
}

async function detectCodexModelsUncached(): Promise<CodexModelInfo[]> {
  const codex = (await detectAgents()).find((agent) => agent.id === 'codex' && agent.ready && agent.auth === 'chatgpt')
  if (!codex?.path) return []
  const stdout = await runExecutableStdout(codex.path, ['debug', 'models'], PROBE_TIMEOUT)
  if (!stdout) return []
  return parseCodexModelCatalog(JSON.parse(stdout) as unknown)
}

export function parseCodexModelCatalog(value: unknown): CodexModelInfo[] {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return []
  const models = (value as { models?: unknown }).models
  if (!Array.isArray(models)) return []
  return models.flatMap((raw): CodexModelInfo[] => {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return []
    const model = raw as Record<string, unknown>
    const id = typeof model.slug === 'string' ? model.slug.trim() : ''
    if (model.visibility !== 'list' || !/^[a-zA-Z0-9._/-]{1,160}$/.test(id)) return []
    const priority = typeof model.priority === 'number' && Number.isFinite(model.priority)
      ? model.priority
      : Number.MAX_SAFE_INTEGER
    return [{
      id,
      name: typeof model.display_name === 'string' && model.display_name.trim() ? model.display_name.trim() : id,
      description: typeof model.description === 'string' ? model.description.trim().slice(0, 500) : '',
      priority,
    }]
  }).sort((left, right) => left.priority - right.priority || left.id.localeCompare(right.id))
}

async function detectAgentsUncached(): Promise<AgentInfo[]> {
  const binaries = AGENT_DEFS.flatMap((d) => d.binaries)
  const stdout = await runLoginShell(
    binaries.map((b) => `command -v ${b} || true`).join('; '),
    PROBE_TIMEOUT,
  )
  const found = new Map<string, string>()
  for (const line of stdout.split('\n')) {
    const p = line.trim()
    if (!p || !p.startsWith('/')) continue
    const bin = p.split('/').pop() ?? ''
    if (!found.has(bin)) found.set(bin, p)
  }
  const results: AgentInfo[] = []
  for (const def of AGENT_DEFS) {
    const hit = def.binaries.map((b) => found.get(b)).find(Boolean)
    let image = def.image
    let auth: AgentInfo['auth']
    if (def.id === 'codex' && hit) {
      const probe = await runLoginShell('codex features list 2>/dev/null || codex plugin list 2>/dev/null || true', PROBE_TIMEOUT)
      if (/image|图/i.test(probe)) image = 'yes'
      const login = await runExecutable(hit, ['login', 'status'], PROBE_TIMEOUT)
      auth = /logged in using chatgpt/i.test(login)
        ? 'chatgpt'
        : /logged in using (?:an )?api key|api[_ -]?key/i.test(login)
          ? 'api-key'
          : /not logged in|logged out|login required/i.test(login)
            ? 'signed-out'
            : 'unknown'
    }
    const ready = Boolean(hit) && (def.id !== 'codex' || auth === 'chatgpt')
    results.push({
      id: def.id,
      name: def.name,
      command: def.command,
      found: Boolean(hit),
      path: hit ?? '',
      image: hit ? image : 'no',
      note: !hit
        ? '未检测到,可在终端安装后重试'
        : def.id === 'codex' && auth !== 'chatgpt'
          ? '已安装，但未使用 ChatGPT 账号登录'
          : '',
      ...(auth ? { auth } : {}),
      ready,
    })
  }
  return results
}
