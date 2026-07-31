import { spawn, type ChildProcess } from 'node:child_process'
import { randomBytes, randomUUID } from 'node:crypto'
import { createWriteStream } from 'node:fs'
import fsp from 'node:fs/promises'
import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http'
import path from 'node:path'
import { pipeline } from 'node:stream/promises'
import { dialog } from 'electron'
import type { AgentInfo, LineKey } from '@shared/types'
import { detectAgents } from './agents'
import { LINES, type WorkspaceService } from './workspace'

const BRIDGE_HOST = '127.0.0.1'
export const LOCAL_BRIDGE_PORT = 43117
const MAX_JSON_BYTES = 128 * 1024
const MAX_FILE_BYTES = 2 * 1024 * 1024 * 1024
const MAX_PROMPT_CHARS = 100_000
const MAX_JOB_OUTPUT_CHARS = 1_000_000
const TOKEN_TTL_MS = 12 * 60 * 60 * 1000
const SUPPORTED_AGENTS = new Set(['codex', 'claude', 'opencode'])
const LINE_KEYS = new Set<LineKey>(['novel', 'n2d', 'comic', 'ad', 'mv', 'song'])

type JobState = 'running' | 'succeeded' | 'failed' | 'cancelled'

interface BridgeSession {
  origin: string
  expiresAt: number
}

interface BridgeJob {
  id: string
  workId: string
  workDir: string
  agentId: string
  state: JobState
  message: string
  output: string
  startedAt: string
  finishedAt?: string
  process?: ChildProcess
}

interface JobRequest {
  workId: string
  workName: string
  line: LineKey
  prompt: string
  agentId?: string
  creationConfig?: {
    generationMode: 'manual' | 'auto'
    model: { modality: string; modelId: string; providerSpec?: string }
  }
}

interface FileHeaders {
  workId: string
  workName: string
  line: LineKey
  fileId: string
  fileName: string
}

class BridgeHttpError extends Error {
  constructor(readonly status: number, message: string) {
    super(message)
  }
}

function cleanWorkName(value: string): string {
  return value
    .replace(/[\\/:*?"<>|]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/[. ]+$/g, '')
    .slice(0, 80) || 'unnamed'
}

function safeFileName(value: string): string {
  const base = path.basename(value).replace(/[\\/:*?"<>|]/g, '_').replace(/^\.+/, '').trim()
  return base.slice(0, 180) || 'unnamed'
}

function requiredHeader(req: IncomingMessage, name: string, maxLength: number): string {
  const value = req.headers[name]?.toString().trim() ?? ''
  if (!value || value.length > maxLength) throw new BridgeHttpError(400, `无效请求头: ${name}`)
  return value
}

function uuid(value: string, label: string): string {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)) {
    throw new BridgeHttpError(400, `${label} 必须是 UUID`)
  }
  return value.toLowerCase()
}

function lineKey(value: string): LineKey {
  if (!LINE_KEYS.has(value as LineKey)) throw new BridgeHttpError(400, '不支持的创作系列')
  return value as LineKey
}

async function readJson(req: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = []
  let size = 0
  for await (const raw of req) {
    const chunk = Buffer.isBuffer(raw) ? raw : Buffer.from(raw)
    size += chunk.length
    if (size > MAX_JSON_BYTES) throw new BridgeHttpError(413, '请求内容过大')
    chunks.push(chunk)
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString('utf8')) as unknown
  } catch {
    throw new BridgeHttpError(400, '请求 JSON 无效')
  }
}

function parseJobRequest(value: unknown): JobRequest {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new BridgeHttpError(400, '任务格式无效')
  const input = value as Record<string, unknown>
  const workId = uuid(String(input.workId ?? ''), 'workId')
  const workName = cleanWorkName(String(input.workName ?? ''))
  const line = lineKey(String(input.line ?? ''))
  const prompt = typeof input.prompt === 'string' ? input.prompt.trim() : ''
  if (!prompt || prompt.length > MAX_PROMPT_CHARS) throw new BridgeHttpError(400, 'Prompt 为空或过长')
  const agentId = typeof input.agentId === 'string' && input.agentId.trim() ? input.agentId.trim() : undefined
  if (agentId && !SUPPORTED_AGENTS.has(agentId)) throw new BridgeHttpError(400, '不支持的 Agent')
  let creationConfig: JobRequest['creationConfig']
  if (input.creationConfig && typeof input.creationConfig === 'object' && !Array.isArray(input.creationConfig)) {
    const rawConfig = input.creationConfig as Record<string, unknown>
    const rawModel = rawConfig.model && typeof rawConfig.model === 'object' && !Array.isArray(rawConfig.model)
      ? rawConfig.model as Record<string, unknown>
      : null
    const generationMode = rawConfig.generationMode === 'manual' ? 'manual' : 'auto'
    const rawModality = typeof rawModel?.modality === 'string' ? rawModel.modality.trim() : ''
    const modality = ['text', 'image', 'video', 'audio'].includes(rawModality) ? rawModality : ''
    const rawModelId = typeof rawModel?.modelId === 'string' ? rawModel.modelId.trim() : ''
    const modelId = /^[a-zA-Z0-9._/-]{1,160}$/.test(rawModelId) ? rawModelId : ''
    const rawProviderSpec = typeof rawModel?.providerSpec === 'string' ? rawModel.providerSpec.trim() : ''
    const providerSpec = /^(?:deepseek|gemini)\/[a-zA-Z0-9._/-]{1,180}$/.test(rawProviderSpec) ? rawProviderSpec : ''
    if (modality && modelId) creationConfig = {
      generationMode,
      model: { modality, modelId, ...(providerSpec ? { providerSpec } : {}) },
    }
  }
  return { workId, workName, line, prompt, ...(agentId ? { agentId } : {}), ...(creationConfig ? { creationConfig } : {}) }
}

function invocation(agent: AgentInfo, prompt: string): { args: string[]; stdin?: string } {
  switch (agent.id) {
    case 'codex':
      return {
        args: [
          'exec',
          '--sandbox', 'workspace-write',
          '--ask-for-approval', 'never',
          '--skip-git-repo-check',
          '--ephemeral',
          '--color', 'never',
          '-',
        ],
        stdin: prompt,
      }
    case 'claude':
      return {
        args: ['--print', '--permission-mode', 'acceptEdits', '--no-session-persistence', prompt],
      }
    case 'opencode':
      return { args: ['run', '--format', 'default', prompt] }
    default:
      throw new BridgeHttpError(400, '该 Agent 暂不支持浏览器桥接')
  }
}

function agentRank(agent: AgentInfo): number {
  const order = ['codex', 'claude', 'opencode']
  const index = order.indexOf(agent.id)
  return index < 0 ? order.length : index
}

export class LocalBridgeService {
  private server: Server | null = null
  private sessions = new Map<string, BridgeSession>()
  private jobs = new Map<string, BridgeJob>()
  private pairingAt = new Map<string, number>()

  constructor(private readonly workspace: WorkspaceService) {}

  private allowedOrigins(): Set<string> {
    const configured = (process.env.ANIME_ARMORY_WEB_ORIGINS ?? '')
      .split(',')
      .map((origin) => origin.trim())
      .filter(Boolean)
    return new Set([
      'http://127.0.0.1:4174',
      'http://localhost:4174',
      ...configured,
    ])
  }

  private origin(req: IncomingMessage): string {
    const origin = req.headers.origin?.trim() ?? ''
    if (!origin || !this.allowedOrigins().has(origin)) throw new BridgeHttpError(403, '该网页未被允许连接本地桥接')
    return origin
  }

  private assertHost(req: IncomingMessage): void {
    const host = req.headers.host?.toLowerCase() ?? ''
    if (host !== `${BRIDGE_HOST}:${LOCAL_BRIDGE_PORT}` && host !== `localhost:${LOCAL_BRIDGE_PORT}`) {
      throw new BridgeHttpError(421, '无效的本地桥接 Host')
    }
  }

  private cors(res: ServerResponse, origin: string): void {
    res.setHeader('access-control-allow-origin', origin)
    res.setHeader('access-control-allow-methods', 'GET, POST, OPTIONS')
    res.setHeader(
      'access-control-allow-headers',
      'authorization, content-type, x-work-id, x-work-name, x-line, x-file-id, x-file-name',
    )
    res.setHeader('access-control-max-age', '600')
    res.setHeader('access-control-allow-private-network', 'true')
    res.setHeader('vary', 'Origin')
  }

  private json(res: ServerResponse, status: number, body: unknown, origin?: string): void {
    if (origin) this.cors(res, origin)
    res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' })
    res.end(JSON.stringify(body))
  }

  private authorize(req: IncomingMessage, origin: string): void {
    const token = req.headers.authorization?.match(/^Bearer\s+(.+)$/i)?.[1]
    const session = token ? this.sessions.get(token) : undefined
    if (!session || session.origin !== origin || session.expiresAt <= Date.now()) {
      if (token) this.sessions.delete(token)
      throw new BridgeHttpError(401, '本地桥接配对已失效')
    }
  }

  private async pair(origin: string): Promise<{ token: string; expiresAt: string }> {
    const previous = this.pairingAt.get(origin) ?? 0
    if (Date.now() - previous < 5000) throw new BridgeHttpError(429, '配对请求过于频繁')
    this.pairingAt.set(origin, Date.now())
    const result = await dialog.showMessageBox({
      type: 'question',
      buttons: ['允许本次连接', '拒绝'],
      defaultId: 0,
      cancelId: 1,
      title: '连接 LabuTV Web',
      message: '允许浏览器使用本机 AI Agent CLI？',
      detail: `${origin}\n\n网页只能向 LabuTV 工作区提交结构化创作任务，不能执行任意 Shell 命令。`,
      noLink: true,
    })
    if (result.response !== 0) throw new BridgeHttpError(403, '用户拒绝了本地桥接请求')
    const token = randomBytes(32).toString('base64url')
    const expiresAt = Date.now() + TOKEN_TTL_MS
    this.sessions.set(token, { origin, expiresAt })
    return { token, expiresAt: new Date(expiresAt).toISOString() }
  }

  private parseFileHeaders(req: IncomingMessage): FileHeaders {
    const workId = uuid(requiredHeader(req, 'x-work-id', 36), 'workId')
    const workName = cleanWorkName(decodeURIComponent(requiredHeader(req, 'x-work-name', 240)))
    const line = lineKey(requiredHeader(req, 'x-line', 16))
    const fileId = uuid(requiredHeader(req, 'x-file-id', 36), 'fileId')
    const fileName = safeFileName(decodeURIComponent(requiredHeader(req, 'x-file-name', 600)))
    return { workId, workName, line, fileId, fileName }
  }

  private async workDirectory(workId: string, workName: string, line: LineKey): Promise<string> {
    const root = await this.workspace.defaultWorkspace()
    const lineDir = LINES.find((item) => item.line === line)?.dir
    if (!lineDir) throw new BridgeHttpError(400, '不支持的创作系列')
    const workDir = path.join(root, '创作区', lineDir, `${cleanWorkName(workName)}--web-${workId.slice(0, 8)}`)
    await fsp.mkdir(workDir, { recursive: true })
    return workDir
  }

  private async saveFile(req: IncomingMessage, headers: FileHeaders): Promise<{ relativePath: string }> {
    const declaredSize = Number(req.headers['content-length'] ?? NaN)
    if (!Number.isSafeInteger(declaredSize) || declaredSize < 0 || declaredSize > MAX_FILE_BYTES) {
      throw new BridgeHttpError(413, '附件大小无效或超过 2GB')
    }
    const workDir = await this.workDirectory(headers.workId, headers.workName, headers.line)
    const relativePath = path.join('源本', headers.fileId, headers.fileName)
    const destination = path.join(workDir, relativePath)
    await fsp.mkdir(path.dirname(destination), { recursive: true })
    const temporary = `${destination}.upload-${randomUUID()}`
    let received = 0
    req.on('data', (chunk: Buffer) => {
      received += chunk.length
      if (received > declaredSize || received > MAX_FILE_BYTES) req.destroy(new Error('附件内容超过声明大小'))
    })
    try {
      await pipeline(req, createWriteStream(temporary, { flags: 'wx' }))
      if (received !== declaredSize) throw new BridgeHttpError(400, '附件内容长度不一致')
      await fsp.rename(temporary, destination)
    } catch (error) {
      await fsp.rm(temporary, { force: true }).catch(() => undefined)
      throw error
    }
    return { relativePath: relativePath.split(path.sep).join('/') }
  }

  private appendOutput(job: BridgeJob, text: string): void {
    job.output = `${job.output}${text}`.slice(-MAX_JOB_OUTPUT_CHARS)
  }

  private async startJob(request: JobRequest): Promise<BridgeJob> {
    const agents = (await detectAgents()).filter((agent) => agent.found && SUPPORTED_AGENTS.has(agent.id))
    const agent = request.agentId
      ? agents.find((candidate) => candidate.id === request.agentId)
      : agents.find((candidate) => candidate.id === 'codex') ?? agents[0]
    if (!agent) throw new BridgeHttpError(503, '未检测到支持的本地 AI Agent CLI')

    const workDir = await this.workDirectory(request.workId, request.workName, request.line)
    const repoRoot = await this.workspace.resolveRepo('')
    const fullPrompt = [
      `你正在 LabuTV 的 ${request.line} 作品目录中工作。`,
      `作品目录：${workDir}`,
      repoRoot ? `技能仓库：${repoRoot}` : '',
      request.creationConfig?.model.providerSpec
        ? `用户选择的模型路由：${request.creationConfig.model.providerSpec}（服务端 API Key；不要向前端或产物输出密钥）`
        : request.creationConfig?.model.modelId
          ? `用户选择的模型：${request.creationConfig.model.modelId}`
          : '',
      '只修改当前作品目录；如需创作流程说明，先读取技能仓库 skills/README.md 并使用对应系列 skill。',
      '',
      '用户需求：',
      request.prompt,
    ].filter(Boolean).join('\n')
    const taskFile = path.join(workDir, '_web任务.md')
    await fsp.writeFile(taskFile, `${fullPrompt}\n`, 'utf8')
    await fsp.writeFile(path.join(workDir, '_meta.json'), JSON.stringify({
      source: 'web-local-bridge',
      client_key: request.workId,
      name: request.workName,
      line: request.line,
      ...(request.creationConfig ? { creation_config: request.creationConfig } : {}),
      updated_at: new Date().toISOString(),
    }, null, 2), 'utf8')

    const command = invocation(agent, fullPrompt)
    const child = spawn(agent.path, command.args, {
      cwd: workDir,
      env: { ...process.env, TERM: 'dumb', NO_COLOR: '1' },
      stdio: ['pipe', 'pipe', 'pipe'],
    })
    const job: BridgeJob = {
      id: randomUUID(),
      workId: request.workId,
      workDir,
      agentId: agent.id,
      state: 'running',
      message: `${agent.name} 正在执行`,
      output: '',
      startedAt: new Date().toISOString(),
      process: child,
    }
    this.jobs.set(job.id, job)
    child.stdout?.on('data', (chunk: Buffer) => this.appendOutput(job, chunk.toString('utf8')))
    child.stderr?.on('data', (chunk: Buffer) => this.appendOutput(job, chunk.toString('utf8')))
    child.on('error', (error) => {
      job.state = 'failed'
      job.message = error.message
      job.finishedAt = new Date().toISOString()
      delete job.process
    })
    child.on('exit', (code, signal) => {
      if (job.state === 'cancelled') return
      job.state = code === 0 ? 'succeeded' : 'failed'
      job.message = code === 0 ? `${agent.name} 已完成` : `${agent.name} 退出（${signal ?? code ?? 'unknown'}）`
      job.finishedAt = new Date().toISOString()
      delete job.process
    })
    if (command.stdin) child.stdin?.end(command.stdin)
    else child.stdin?.end()
    return job
  }

  private publicJob(job: BridgeJob) {
    return {
      id: job.id,
      state: job.state,
      message: job.message,
      agentId: job.agentId,
      output: job.output,
      workDir: job.workDir,
      startedAt: job.startedAt,
      ...(job.finishedAt ? { finishedAt: job.finishedAt } : {}),
    }
  }

  private async handle(req: IncomingMessage, res: ServerResponse): Promise<void> {
    this.assertHost(req)
    const origin = this.origin(req)
    if (req.method === 'OPTIONS') {
      this.cors(res, origin)
      res.writeHead(204)
      res.end()
      return
    }
    const url = new URL(req.url ?? '/', `http://${BRIDGE_HOST}:${LOCAL_BRIDGE_PORT}`)
    if (req.method === 'GET' && url.pathname === '/v1/status') {
      const agents = (await detectAgents())
        .filter((agent) => agent.found && SUPPORTED_AGENTS.has(agent.id))
        .sort((left, right) => agentRank(left) - agentRank(right))
      this.json(res, 200, {
        service: 'anime-armory-local-bridge',
        version: 1,
        requiresPairing: true,
        agents: agents.map(({ id, name }) => ({ id, name })),
      }, origin)
      return
    }
    if (req.method === 'POST' && url.pathname === '/v1/pair') {
      this.json(res, 200, await this.pair(origin), origin)
      return
    }

    this.authorize(req, origin)
    if (req.method === 'GET' && url.pathname === '/v1/agents') {
      const agents = await detectAgents()
      this.json(res, 200, { agents: agents.filter((agent) => agent.found && SUPPORTED_AGENTS.has(agent.id)) }, origin)
      return
    }
    if (req.method === 'POST' && url.pathname === '/v1/work-files') {
      this.json(res, 201, await this.saveFile(req, this.parseFileHeaders(req)), origin)
      return
    }
    if (req.method === 'POST' && url.pathname === '/v1/agent/jobs') {
      const job = await this.startJob(parseJobRequest(await readJson(req)))
      this.json(res, 202, this.publicJob(job), origin)
      return
    }
    const jobMatch = url.pathname.match(/^\/v1\/agent\/jobs\/([0-9a-f-]+)$/i)
    if (req.method === 'GET' && jobMatch?.[1]) {
      const job = this.jobs.get(uuid(jobMatch[1], 'jobId'))
      if (!job) throw new BridgeHttpError(404, '本地任务不存在')
      this.json(res, 200, this.publicJob(job), origin)
      return
    }
    const cancelMatch = url.pathname.match(/^\/v1\/agent\/jobs\/([0-9a-f-]+)\/cancel$/i)
    if (req.method === 'POST' && cancelMatch?.[1]) {
      const job = this.jobs.get(uuid(cancelMatch[1], 'jobId'))
      if (!job) throw new BridgeHttpError(404, '本地任务不存在')
      if (job.state === 'running') {
        job.state = 'cancelled'
        job.message = '任务已取消'
        job.finishedAt = new Date().toISOString()
        job.process?.kill('SIGTERM')
        delete job.process
      }
      this.json(res, 200, this.publicJob(job), origin)
      return
    }
    throw new BridgeHttpError(404, '本地桥接接口不存在')
  }

  async start(): Promise<void> {
    if (this.server) return
    void detectAgents().catch(() => undefined)
    const server = createServer((req, res) => {
      void this.handle(req, res).catch((error: unknown) => {
        const status = error instanceof BridgeHttpError ? error.status : 500
        const message = error instanceof Error ? error.message : String(error)
        let origin: string | undefined
        try {
          origin = this.origin(req)
        } catch {
          origin = undefined
        }
        if (!res.headersSent) this.json(res, status, { error: { message } }, origin)
        else res.destroy()
      })
    })
    await new Promise<void>((resolve, reject) => {
      server.once('error', reject)
      server.listen(LOCAL_BRIDGE_PORT, BRIDGE_HOST, () => {
        server.off('error', reject)
        resolve()
      })
    })
    this.server = server
    console.log(`[local-bridge] listening on http://${BRIDGE_HOST}:${LOCAL_BRIDGE_PORT}`)
  }

  stop(): void {
    for (const job of this.jobs.values()) job.process?.kill('SIGTERM')
    this.jobs.clear()
    this.sessions.clear()
    this.server?.close()
    this.server = null
  }
}
