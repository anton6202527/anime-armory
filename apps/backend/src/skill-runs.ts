import { createHash, randomUUID } from 'node:crypto'

import type { AiGenerationRequest, CreationLine, SkillDefinitionInput, SkillRun, SkillRunAttachmentInput } from './contracts.ts'
import type { AiProvider } from './ai-provider.ts'
import { ApiError } from './errors.ts'
import { canonicalSkillId, isCreationLine, SkillRegistry } from './skill-registry.ts'
import { WorkFileStore } from './work-files.ts'

const BUILTIN_SKILL_ID_PATTERN = /^[a-z0-9][a-z0-9-]{0,79}$/
const USER_SKILL_ID_PATTERN = /^user:[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$/
const SAFE_REFERENCE_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$/
const MODEL_ID_PATTERN = /^[a-zA-Z0-9._:/-]{1,160}$/
const IDEMPOTENCY_KEY_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9._:-]{7,199}$/
const MAX_PROMPT_CHARS = 12_000
const MAX_STRUCTURED_INPUT_CHARS = 24_000
const MAX_USER_SKILL_CHARS = 20_000
const MAX_ATTACHMENTS = 24
const MAX_SKILL_INSTRUCTION_CHARS = 16_000
const MAX_SKILL_IMAGE_BYTES = 12 * 1024 * 1024
const MODEL_PRIORITY = ['gpt-5.6-terra', 'gpt-5.6-sol', 'gpt-5.6-luna', 'gpt-5.5', 'gpt-5.4']

export interface CreateSkillRunInput {
  skillId: string
  workId: string
  projectId?: string
  workName?: string
  line: CreationLine
  prompt: string
  generationMode: 'manual' | 'auto'
  idempotencyKey: string
  modelPreference?: string
  attachments: SkillRunAttachmentInput[]
  context?: Record<string, unknown>
  skillDefinition?: SkillDefinitionInput
}

interface PreparedSkillRun extends CreateSkillRunInput {
  definition: string
  fingerprint: string
}

interface InternalJob {
  public: SkillRun
  input: PreparedSkillRun
  controller: AbortController
  idempotencyScope: string
}

function stringField(value: unknown, field: string, maximum: number, required = true): string | undefined {
  if (value === undefined && !required) return undefined
  if (typeof value !== 'string') throw new ApiError(400, 'invalid_skill_run_request', `${field} 必须是字符串`)
  const normalized = value.trim()
  if ((required && !normalized) || normalized.length > maximum || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(normalized)) {
    throw new ApiError(400, 'invalid_skill_run_request', `${field} 无效或超过长度上限`)
  }
  return normalized || undefined
}

function parseSkillDefinition(value: unknown): SkillDefinitionInput | undefined {
  if (value === undefined) return undefined
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new ApiError(400, 'invalid_skill_run_request', 'skillDefinition 格式无效')
  }
  const input = value as Record<string, unknown>
  const title = stringField(input.title, 'skillDefinition.title', 200) as string
  const description = stringField(input.description, 'skillDefinition.description', 2_000) as string
  const guide = stringField(input.guide, 'skillDefinition.guide', 16_000) as string
  const parseList = (item: unknown, field: string): string[] => {
    if (!Array.isArray(item) || item.length > 50) {
      throw new ApiError(400, 'invalid_skill_run_request', `${field} 必须是有限字符串数组`)
    }
    return item.map((entry) => stringField(entry, field, 1_000) as string)
  }
  const steps = parseList(input.steps, 'skillDefinition.steps')
  const useCases = parseList(input.useCases, 'skillDefinition.useCases')
  const total = title.length + description.length + guide.length
    + steps.reduce((sum, entry) => sum + entry.length, 0)
    + useCases.reduce((sum, entry) => sum + entry.length, 0)
  if (total > MAX_USER_SKILL_CHARS) {
    throw new ApiError(413, 'skill_definition_too_large', '用户 skill definition 超过安全上限')
  }
  return { title, description, guide, steps, useCases }
}

function parseAttachments(value: unknown): SkillRunAttachmentInput[] {
  if (value === undefined) return []
  if (!Array.isArray(value) || value.length > MAX_ATTACHMENTS) {
    throw new ApiError(400, 'invalid_skill_run_request', 'attachments 必须是有限数组')
  }
  return value.map((entry) => {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) {
      throw new ApiError(400, 'invalid_skill_run_request', 'attachment 格式无效')
    }
    const record = entry as Record<string, unknown>
    const id = stringField(record.id, 'attachment.id', 128) as string
    const name = stringField(record.name, 'attachment.name', 240) as string
    if (!SAFE_REFERENCE_PATTERN.test(id)) throw new ApiError(400, 'invalid_skill_run_request', 'attachment.id 无效')
    const mimeType = stringField(record.mimeType, 'attachment.mimeType', 160, false)
    const assetId = stringField(record.assetId, 'attachment.assetId', 128, false)
    if (assetId && !SAFE_REFERENCE_PATTERN.test(assetId)) {
      throw new ApiError(400, 'invalid_skill_run_request', 'attachment.assetId 无效')
    }
    return { id, name, ...(mimeType ? { mimeType } : {}), ...(assetId ? { assetId } : {}) }
  })
}

function parseContext(value: unknown): Record<string, unknown> | undefined {
  if (value === undefined) return undefined
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new ApiError(400, 'invalid_skill_run_request', 'context 必须是 JSON 对象')
  }
  let serialized: string
  try {
    serialized = JSON.stringify(value)
  } catch {
    throw new ApiError(400, 'invalid_skill_run_request', 'context 无法序列化')
  }
  if (serialized.length > MAX_STRUCTURED_INPUT_CHARS) {
    throw new ApiError(413, 'skill_input_too_large', 'context 超过安全上限')
  }
  return value as Record<string, unknown>
}

export function parseCreateSkillRunRequest(value: unknown): CreateSkillRunInput {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new ApiError(400, 'invalid_skill_run_request', 'skill run 请求格式无效')
  }
  const input = value as Record<string, unknown>
  const requestedSkillId = stringField(input.skillId, 'skillId', 133) as string
  if (!BUILTIN_SKILL_ID_PATTERN.test(requestedSkillId) && !USER_SKILL_ID_PATTERN.test(requestedSkillId)) {
    throw new ApiError(400, 'invalid_skill_run_request', 'skillId 无效')
  }
  const skillId = requestedSkillId.startsWith('user:') ? requestedSkillId : canonicalSkillId(requestedSkillId)
  const workIdValue = input.workId ?? input.projectId
  const workId = stringField(workIdValue, 'workId/projectId', 128) as string
  if (!SAFE_REFERENCE_PATTERN.test(workId)) throw new ApiError(400, 'invalid_skill_run_request', 'workId/projectId 无效')
  const projectId = stringField(input.projectId, 'projectId', 128, false)
  if (projectId && !SAFE_REFERENCE_PATTERN.test(projectId)) {
    throw new ApiError(400, 'invalid_skill_run_request', 'projectId 无效')
  }
  const workName = stringField(input.workName, 'workName', 240, false)
  if (!isCreationLine(input.line)) throw new ApiError(400, 'invalid_skill_run_request', 'line 无效')
  if (input.generationMode !== 'manual' && input.generationMode !== 'auto') {
    throw new ApiError(400, 'invalid_skill_run_request', 'generationMode 必须是 manual 或 auto')
  }
  let prompt: string
  if (typeof input.prompt === 'string') {
    prompt = stringField(input.prompt, 'prompt', MAX_PROMPT_CHARS) as string
  } else if (typeof input.input === 'string') {
    prompt = stringField(input.input, 'input', MAX_PROMPT_CHARS) as string
  } else if (input.input && typeof input.input === 'object') {
    try {
      prompt = JSON.stringify(input.input)
    } catch {
      throw new ApiError(400, 'invalid_skill_run_request', 'input 无法序列化')
    }
    if (prompt.length > MAX_STRUCTURED_INPUT_CHARS) {
      throw new ApiError(413, 'skill_input_too_large', 'input 超过安全上限')
    }
  } else {
    throw new ApiError(400, 'invalid_skill_run_request', 'prompt 或 input 必须提供一个')
  }
  const idempotencyKey = stringField(input.idempotencyKey, 'idempotencyKey', 200) as string
  if (!IDEMPOTENCY_KEY_PATTERN.test(idempotencyKey)) {
    throw new ApiError(400, 'invalid_skill_run_request', 'idempotencyKey 格式无效')
  }
  const modelPreference = stringField(input.modelPreference, 'modelPreference', 160, false)
  if (modelPreference && !MODEL_ID_PATTERN.test(modelPreference)) {
    throw new ApiError(400, 'invalid_skill_run_request', 'modelPreference 无效')
  }
  const context = parseContext(input.context)
  const skillDefinition = parseSkillDefinition(input.skillDefinition)
  return {
    skillId,
    workId,
    ...(projectId ? { projectId } : {}),
    ...(workName ? { workName } : {}),
    line: input.line,
    prompt,
    generationMode: input.generationMode,
    idempotencyKey,
    ...(modelPreference ? { modelPreference } : {}),
    attachments: parseAttachments(input.attachments),
    ...(context ? { context } : {}),
    ...(skillDefinition ? { skillDefinition } : {}),
  }
}

function userSkillDocument(definition: SkillDefinitionInput): string {
  return [
    `# ${definition.title}`,
    '',
    definition.description,
    '',
    definition.guide,
    '',
    '## Steps',
    ...definition.steps.map((step, index) => `${index + 1}. ${step}`),
    '',
    '## Use cases',
    ...definition.useCases.map((useCase) => `- ${useCase}`),
  ].join('\n')
}

function cloneRun(run: SkillRun): SkillRun {
  return {
    ...run,
    ...(run.artifacts ? { artifacts: run.artifacts.map((artifact) => ({ ...artifact })) } : {}),
  }
}

function requestFingerprint(input: CreateSkillRunInput): string {
  return createHash('sha256').update(JSON.stringify(input)).digest('hex')
}

function selectModel(models: Awaited<ReturnType<AiProvider['listModels']>>, preference?: string): string {
  const textModels = models.filter((model) => model.modality === 'text')
  if (preference) {
    const preferred = textModels.find((model) => model.id === preference)
    if (!preferred) throw new ApiError(400, 'model_unavailable', `指定的文本模型不可用：${preference}`)
    return preferred.id
  }
  for (const preferredId of MODEL_PRIORITY) {
    const match = textModels.find((model) => model.id === preferredId || model.id.endsWith(`/${preferredId}`))
    if (match) return match.id
  }
  const fallback = textModels.find((model) => /^gpt(?:-|$)/i.test(model.id) || /\/gpt(?:-|$)/i.test(model.id))
  if (!fallback) throw new ApiError(503, 'no_text_model', 'cliproxy 当前没有可用的 GPT 文本模型')
  return fallback.id
}

function executionPrompt(input: PreparedSkillRun): string {
  const definition = input.definition.length <= MAX_SKILL_INSTRUCTION_CHARS
    ? input.definition
    : `${input.definition.slice(0, MAX_SKILL_INSTRUCTION_CHARS)}\n\n[后续说明因服务端 prompt 上限截断]`
  const attachments = input.attachments.length
    ? input.attachments.map((attachment) => ({
        id: attachment.id,
        name: attachment.name,
        ...(attachment.mimeType ? { mimeType: attachment.mimeType } : {}),
        ...(attachment.assetId ? { assetId: attachment.assetId } : {}),
      }))
    : []
  return [
    '你正在 LabuTV 后端执行一个明确指定的创作 skill。严格遵循 skill 说明；不要声称运行了未运行的脚本，也不要输出本机路径、密钥或内部配置。',
    '',
    `Skill ID: ${input.skillId}`,
    `作品线: ${input.line}`,
    `执行模式: ${input.generationMode}`,
    '',
    '<skill-definition>',
    definition,
    '</skill-definition>',
    '',
    '<user-input>',
    input.prompt,
    '</user-input>',
    ...(input.context ? ['', '<context>', JSON.stringify(input.context), '</context>'] : []),
    ...(attachments.length ? ['', '<attachments>', JSON.stringify(attachments), '</attachments>'] : []),
    '',
    '返回可直接展示给用户的文本结果。若该 skill 必须依赖尚未执行的本地媒体脚本，清楚列出缺口与下一步，不得伪造完成。',
  ].join('\n')
}

export class SkillRunManager {
  private readonly jobs = new Map<string, InternalJob>()
  private readonly idempotency = new Map<string, { fingerprint: string; id: string }>()
  private readonly queue: string[] = []
  private active = 0

  constructor(
    private readonly provider: AiProvider,
    private readonly registry: SkillRegistry,
    private readonly concurrency = 2,
    private readonly fileStore?: WorkFileStore,
  ) {}

  async create(rawInput: unknown): Promise<SkillRun> {
    const input = parseCreateSkillRunRequest(rawInput)
    let definition: string
    if (input.skillId.startsWith('user:')) {
      if (!input.skillDefinition) {
        throw new ApiError(400, 'skill_definition_required', 'user:* skill 必须携带完整 skillDefinition')
      }
      definition = userSkillDocument(input.skillDefinition)
    } else {
      const registered = await this.registry.get(input.skillId)
      if (registered.line && registered.line !== input.line) {
        throw new ApiError(400, 'skill_line_mismatch', `skill ${input.skillId} 不属于 ${input.line} 作品线`)
      }
      definition = registered.definition
    }
    const fingerprint = requestFingerprint(input)
    const idempotencyScope = `${input.workId}:${input.idempotencyKey}`
    const existing = this.idempotency.get(idempotencyScope)
    if (existing) {
      if (existing.fingerprint !== fingerprint) {
        throw new ApiError(409, 'idempotency_conflict', '相同 idempotencyKey 已用于不同请求')
      }
      const job = this.jobs.get(existing.id)
      if (job) return cloneRun(job.public)
    }
    const id = randomUUID()
    const createdAt = new Date().toISOString()
    const prepared: PreparedSkillRun = { ...input, definition, fingerprint }
    const job: InternalJob = {
      public: { id, skillId: input.skillId, state: 'queued', message: '任务已排队', createdAt },
      input: prepared,
      controller: new AbortController(),
      idempotencyScope,
    }
    this.jobs.set(id, job)
    this.idempotency.set(idempotencyScope, { fingerprint, id })
    this.queue.push(id)
    queueMicrotask(() => this.drain())
    return cloneRun(job.public)
  }

  get(id: string): SkillRun {
    const job = this.jobs.get(id)
    if (!job) throw new ApiError(404, 'skill_run_not_found', '找不到 skill run')
    return cloneRun(job.public)
  }

  cancel(id: string): SkillRun {
    const job = this.jobs.get(id)
    if (!job) throw new ApiError(404, 'skill_run_not_found', '找不到 skill run')
    if (job.public.state === 'succeeded' || job.public.state === 'failed' || job.public.state === 'cancelled') {
      if (job.public.state !== 'cancelled') throw new ApiError(409, 'skill_run_terminal', '已结束的 skill run 无法取消')
      return cloneRun(job.public)
    }
    job.controller.abort()
    if (job.public.state === 'queued') {
      job.public = {
        ...job.public,
        state: 'cancelled',
        message: '任务已取消',
        finishedAt: new Date().toISOString(),
      }
    }
    return cloneRun(job.public)
  }

  private drain(): void {
    while (this.active < this.concurrency) {
      const id = this.queue.shift()
      if (!id) break
      const job = this.jobs.get(id)
      if (!job || job.public.state !== 'queued') continue
      this.active += 1
      void this.execute(job).finally(() => {
        this.active = Math.max(0, this.active - 1)
        this.drain()
      })
    }
  }

  private async execute(job: InternalJob): Promise<void> {
    job.public = {
      ...job.public,
      state: 'running',
      message: '正在通过后端 AI 服务执行 skill',
      startedAt: new Date().toISOString(),
    }
    try {
      const models = await this.provider.listModels(false, job.controller.signal)
      const model = selectModel(models, job.input.modelPreference)
      job.public = { ...job.public, model }
      const request: AiGenerationRequest = {
        modality: 'text',
        model,
        prompt: executionPrompt(job.input),
      }
      const requestedAttachmentId = typeof job.input.context?.sourceAttachmentId === 'string'
        ? job.input.context.sourceAttachmentId
        : undefined
      const primaryAttachment = requestedAttachmentId
        ? job.input.attachments.find((attachment) => attachment.id === requestedAttachmentId)
        : job.input.attachments.find((attachment) => /^(?:image|audio)\//.test(attachment.mimeType ?? ''))
      const audioAttachment = primaryAttachment?.mimeType?.startsWith('audio/') ? primaryAttachment : undefined
      if (audioAttachment) {
        throw new ApiError(
          501,
          'audio_input_unavailable',
          '当前 cliproxy GPT adapter 尚不支持音频 Skill 输入，任务未伪造执行',
        )
      }
      const imageAttachment = primaryAttachment?.mimeType?.startsWith('image/') && !primaryAttachment.assetId
        ? primaryAttachment
        : undefined
      if (imageAttachment && this.fileStore) {
        const bytes = await this.fileStore.read(job.input.workId, imageAttachment.id, MAX_SKILL_IMAGE_BYTES)
        const mimeType = imageAttachment.mimeType
        if (mimeType === 'image/png' || mimeType === 'image/jpeg' || mimeType === 'image/webp' || mimeType === 'image/gif') {
          request.image = { base64: bytes.toString('base64'), mimeType }
        }
      }
      const result = await this.provider.generate(request, job.controller.signal)
      if (job.controller.signal.aborted) throw new ApiError(499, 'request_cancelled', '任务已取消')
      if (result.modality !== 'text') throw new ApiError(502, 'invalid_skill_output', 'skill runner 未返回文本结果')
      const artifact = {
        id: randomUUID(),
        kind: 'text' as const,
        name: `${job.input.skillId}-result.md`,
        mimeType: 'text/markdown; charset=utf-8',
        size: Buffer.byteLength(result.text),
        text: result.text,
      }
      job.public = {
        ...job.public,
        state: 'succeeded',
        message: 'skill 执行完成',
        finishedAt: new Date().toISOString(),
        output: result.text,
        artifacts: [artifact],
      }
    } catch (error) {
      const cancelled = job.controller.signal.aborted || (error instanceof ApiError && error.code === 'request_cancelled')
      job.public = {
        ...job.public,
        state: cancelled ? 'cancelled' : 'failed',
        message: cancelled
          ? '任务已取消'
          : error instanceof ApiError ? error.message : 'skill 执行失败',
        finishedAt: new Date().toISOString(),
      }
    }
  }
}
