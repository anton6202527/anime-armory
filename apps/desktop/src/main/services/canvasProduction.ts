import { createHash, randomUUID } from 'node:crypto'
import fs from 'node:fs/promises'
import path from 'node:path'
import type {
  CanvasAuthoringAssetSummary,
  CanvasAuthoringClipInput,
  CanvasAuthoringInput,
  CanvasData,
  CanvasFinalAcceptRequest,
  CanvasFinalArtifactEvidence,
  CanvasGenerationKind,
  CanvasNodeAcceptanceEvidence,
  CanvasNodeAcceptRequest,
  CanvasProductionCompletion,
  CanvasProductionHistoryEntry,
  CanvasProductionNodeState,
  CanvasProductionState,
  CanvasProductionStatus,
  CanvasProductionSyncRequest,
  CanvasProductionTask,
  CanvasProductionTaskStatus,
  CanvasTaskStatusRequest,
  CanvasTaskSubmitRequest,
  CanvasTaskSubmitResult,
} from '@shared/types'
import { canvasCandidateTargetRel } from '../../shared/canvasTargets'

const STATE_KIND = 'anime_armory_canvas_production_state' as const
const STATE_VERSION = 2 as const
const COMPLETION_DEFINITION = 'canvas.final_product/v1' as const
const SHA256_RE = /^[a-f0-9]{64}$/
export const CANVAS_EPISODE_TASK_NODE_ID = '__episode__' as const

/** Process-local serialization is sufficient for Electron's single main
 * process. Atomic rename keeps readers on either the old or the new complete
 * JSON document; they never observe a half-written state. */
const stateWriteTails = new Map<string, Promise<void>>()

type Canonical = null | boolean | number | string | Canonical[] | { [key: string]: Canonical }

function canonicalize(value: unknown, stack = new Set<object>()): Canonical {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return value
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error('canonical JSON 不允许 NaN 或 Infinity')
    return Object.is(value, -0) ? 0 : value
  }
  if (Array.isArray(value)) {
    if (stack.has(value)) throw new Error('canonical JSON 不允许循环引用')
    stack.add(value)
    try {
      return value.map((item) => (item === undefined ? null : canonicalize(item, stack)))
    } finally {
      stack.delete(value)
    }
  }
  if (typeof value === 'object') {
    const object = value as Record<string, unknown>
    const prototype = Object.getPrototypeOf(object)
    if (prototype !== Object.prototype && prototype !== null) {
      throw new Error('canonical JSON 仅支持普通 object/array')
    }
    if (stack.has(object)) throw new Error('canonical JSON 不允许循环引用')
    stack.add(object)
    try {
      const out: Record<string, Canonical> = {}
      for (const key of Object.keys(object).sort()) {
        const child = object[key]
        // Match JSON object semantics without allowing a key-order dependent
        // representation for optional undefined fields.
        if (child !== undefined) out[key] = canonicalize(child, stack)
      }
      return out
    } finally {
      stack.delete(object)
    }
  }
  throw new Error(`canonical JSON 不支持 ${typeof value}`)
}

export function stableCanonicalJson(value: unknown): string {
  return JSON.stringify(canonicalize(value))
}

function canonicalSha256(value: unknown): string {
  return createHash('sha256').update(stableCanonicalJson(value), 'utf8').digest('hex')
}

function validateEpisode(episode: string): string {
  const clean = String(episode || '').trim()
  if (!clean || clean.includes('/') || clean.includes('\\') || clean.includes('\0')) {
    throw new Error('非法集名')
  }
  return clean
}

function normalizeSourceRel(value: string): string {
  const raw = String(value || '').trim().replaceAll('\\', '/')
  if (!raw || raw.startsWith('/') || /^[A-Za-z]:\//.test(raw)) {
    throw new Error('source_rel 必须是作品内相对路径')
  }
  const parts = raw.split('/').filter((item) => item && item !== '.')
  if (parts.some((item) => item === '..')) throw new Error('source_rel 不允许越级路径')
  const normalized = parts.join('/')
  if (!normalized) throw new Error('source_rel 必须是作品内相对路径')
  return normalized
}

function normalizeTargetSlot(value: string): string {
  const clean = String(value || '').trim()
  if (!clean || clean.length > 180 || /[\\/\0-\x1f]/.test(clean)) {
    throw new Error('target_slot 非法')
  }
  return clean
}

function normalizeTargetOutputPath(value: string): string {
  const clean = String(value || '').trim()
  return clean ? normalizeSourceRel(clean) : ''
}

function uniqueSorted(values: string[], label: string): string[] {
  const clean = values.map((item) => String(item || '').trim()).filter(Boolean)
  if (new Set(clean).size !== clean.length) throw new Error(`${label} 不允许重复项`)
  return clean.sort()
}

function normalizeClip(raw: CanvasAuthoringClipInput, finalStage: CanvasGenerationKind): CanvasAuthoringClipInput {
  const id = String(raw.id || '').trim()
  if (!id) throw new Error('clips[].id 不能为空')
  if (id === CANVAS_EPISODE_TASK_NODE_ID) throw new Error(`clips[].id 不能使用保留值 ${CANVAS_EPISODE_TASK_NODE_ID}`)
  const clip: CanvasAuthoringClipInput = {
    id,
    editable: canonicalize(raw.editable),
    final_target: {
      slot: normalizeTargetSlot(raw.final_target?.slot || finalStage),
      output_path: normalizeTargetOutputPath(raw.final_target?.output_path || ''),
    },
    ready: raw.ready !== false,
  }
  if (raw.runtime_inputs !== undefined) clip.runtime_inputs = canonicalize(raw.runtime_inputs)
  if (raw.image_runtime_inputs !== undefined) clip.image_runtime_inputs = canonicalize(raw.image_runtime_inputs)
  if (raw.asset_ids !== undefined) clip.asset_ids = uniqueSorted(raw.asset_ids, `${id}.asset_ids`)
  if (raw.generation_config_keys !== undefined) {
    clip.generation_config_keys = uniqueSorted(raw.generation_config_keys, `${id}.generation_config_keys`)
  }
  return clip
}

function normalizeAsset(raw: CanvasAuthoringAssetSummary): CanvasAuthoringAssetSummary {
  const id = String(raw.id || '').trim()
  const contentDigest = String(raw.content_digest || '').trim()
  if (!id) throw new Error('assets[].id 不能为空')
  if (!contentDigest) throw new Error(`asset ${id} 缺 content_digest`)
  const asset: CanvasAuthoringAssetSummary = { id, content_digest: contentDigest }
  const role = String(raw.role || '').trim()
  if (role) asset.role = role
  if (raw.summary !== undefined) asset.summary = canonicalize(raw.summary)
  return asset
}

export function normalizeCanvasAuthoringInput(input: CanvasAuthoringInput): CanvasAuthoringInput {
  const authority = String(input.authority || '').trim()
  if (!authority) throw new Error('authority 不能为空')
  const sourceSha256 = String(input.source_sha256 || '').trim().toLowerCase()
  const settingsSha256 = String(input.settings_sha256 || '').trim().toLowerCase()
  if (!SHA256_RE.test(sourceSha256)) throw new Error('source_sha256 必须是 SHA-256')
  if (!SHA256_RE.test(settingsSha256)) throw new Error('settings_sha256 必须是 SHA-256')
  const episode = validateEpisode(input.episode)
  const finalStage: CanvasGenerationKind = input.final_stage === 'image' ? 'image' : 'video'
  const clips = (input.clips || []).map((clip) => normalizeClip(clip, finalStage))
  const clipIds = clips.map((clip) => clip.id)
  if (new Set(clipIds).size !== clipIds.length) throw new Error('clips[].id 不允许重复')
  const assets = (input.assets || []).map(normalizeAsset).sort((a, b) => {
    return a.id < b.id ? -1 : a.id > b.id ? 1 : 0
  })
  const assetIds = assets.map((asset) => asset.id)
  if (new Set(assetIds).size !== assetIds.length) throw new Error('assets[].id 不允许重复')
  const generationConfigs = canonicalize(input.generation_configs || {})
  if (generationConfigs === null || Array.isArray(generationConfigs) || typeof generationConfigs !== 'object') {
    throw new Error('generation_configs 必须是 object')
  }
  return {
    authority,
    source_rel: normalizeSourceRel(input.source_rel),
    source_sha256: sourceSha256,
    settings_sha256: settingsSha256,
    episode,
    final_stage: finalStage,
    clips,
    assets,
    delivery_spec: canonicalize(input.delivery_spec),
    generation_configs: generationConfigs,
  }
}

function episodeHashPayload(input: CanvasAuthoringInput): unknown {
  return {
    authority: input.authority,
    source_rel: input.source_rel,
    source_sha256: input.source_sha256,
    settings_sha256: input.settings_sha256,
    episode: input.episode,
    final_stage: input.final_stage,
    // Editorial order is deliberately preserved.
    clips: input.clips.map((clip) => ({
      id: clip.id,
      editable: clip.editable,
      final_target: hashableFinalTarget(clip),
      asset_ids: clip.asset_ids,
      generation_config_keys: clip.generation_config_keys,
    })),
    // normalizeCanvasAuthoringInput already sorts assets by stable id.
    assets: input.assets,
    delivery_spec: input.delivery_spec,
    generation_configs: input.generation_configs,
  }
}

/** The sole episode-level business hash. Media SHA values remain evidence and
 * per-node hashes remain selective-invalidation indexes; neither is a second
 * episode state identity. */
export function computeCanvasContentHash(raw: CanvasAuthoringInput): string {
  const input = normalizeCanvasAuthoringInput(raw)
  return canonicalSha256(episodeHashPayload(input))
}

function configKeysForClip(input: CanvasAuthoringInput, clip: CanvasAuthoringClipInput): string[] {
  if (clip.generation_config_keys !== undefined) return clip.generation_config_keys
  return Object.keys(input.generation_configs).sort()
}

function assetsForClip(input: CanvasAuthoringInput, clip: CanvasAuthoringClipInput): unknown[] {
  if (clip.asset_ids === undefined) return input.assets
  const byId = new Map(input.assets.map((asset) => [asset.id, asset]))
  return clip.asset_ids.map((id) => byId.get(id) ?? { id, missing: true })
}

function hashableFinalTarget(clip: CanvasAuthoringClipInput): CanvasAuthoringClipInput['final_target'] | undefined {
  return clip.final_target.output_path ? clip.final_target : undefined
}

export function computeCanvasNodeFingerprints(raw: CanvasAuthoringInput): Record<string, string> {
  const input = normalizeCanvasAuthoringInput(raw)
  const configs = input.generation_configs
  return Object.fromEntries(input.clips.map((clip) => {
    const configKeys = configKeysForClip(input, clip).filter((key) => {
      return input.final_stage === 'video' || key.startsWith('image:')
    })
    const selectedConfigs = Object.fromEntries(configKeys.map((key) => [
      key,
      Object.hasOwn(configs, key) ? configs[key] : { missing: true },
    ]))
    const body = {
      authority: input.authority,
      source_rel: input.source_rel,
      settings_sha256: input.settings_sha256,
      episode: input.episode,
      clip: {
        id: clip.id,
        editable: clip.editable,
        final_target: hashableFinalTarget(clip),
        runtime_inputs: input.final_stage === 'image' ? clip.image_runtime_inputs : clip.runtime_inputs,
        asset_ids: clip.asset_ids,
        generation_config_keys: clip.generation_config_keys,
      },
      assets: assetsForClip(input, clip),
      delivery_spec: input.delivery_spec,
      generation_configs: selectedConfigs,
    }
    return [clip.id, canonicalSha256(body)]
  }))
}

/** Execution-stage hashes are dependency indexes, not a second episode
 * identity. In particular, image output bytes are excluded from the image
 * stage and included in the video stage via runtime_inputs. */
export function computeCanvasStageFingerprints(
  raw: CanvasAuthoringInput,
): Record<string, Record<CanvasGenerationKind, string>> {
  const input = normalizeCanvasAuthoringInput(raw)
  return Object.fromEntries(input.clips.map((clip) => {
    const body = (kind: CanvasGenerationKind) => {
      const configKeys = kind === 'video'
        ? configKeysForClip(input, clip)
        : configKeysForClip(input, clip).filter((key) => key.startsWith('image:'))
      const selectedConfigs = Object.fromEntries(configKeys.map((key) => [
        key,
        Object.hasOwn(input.generation_configs, key)
          ? input.generation_configs[key]
          : { missing: true },
      ]))
      return {
        authority: input.authority,
        source_rel: input.source_rel,
        settings_sha256: input.settings_sha256,
        episode: input.episode,
        clip: {
          id: clip.id,
          editable: clip.editable,
          final_target: hashableFinalTarget(clip),
          runtime_inputs: kind === 'image' ? clip.image_runtime_inputs : clip.runtime_inputs,
          asset_ids: clip.asset_ids,
          generation_config_keys: clip.generation_config_keys,
        },
        assets: assetsForClip(input, clip),
        delivery_spec: input.delivery_spec,
        generation_configs: selectedConfigs,
      }
    }
    return [clip.id, {
      image: canonicalSha256(body('image')),
      video: canonicalSha256(body('video')),
    }]
  }))
}

/** Per-output execution identity. A clip can own several image outputs, so a
 * first-frame job must never reuse an active anchor/end-frame job merely
 * because their common clip/stage dependencies happen to match. */
export function computeCanvasTargetFingerprint(
  raw: CanvasAuthoringInput,
  clipId: string,
  kind: CanvasGenerationKind,
  targetSlot: string,
  targetOutputPath = '',
): string {
  const input = normalizeCanvasAuthoringInput(raw)
  const clip = input.clips.find((item) => item.id === clipId)
  if (!clip) throw new Error(`找不到画布节点: ${clipId}`)
  const slot = normalizeTargetSlot(targetSlot || kind)
  const outputPath = normalizeTargetOutputPath(targetOutputPath)
  const exactKey = `${kind}:${clip.id}:${slot}`
  const legacyKey = `${kind}:${clip.id}`
  const selectedKey = Object.hasOwn(input.generation_configs, exactKey) ? exactKey : legacyKey
  const selectedConfig = Object.hasOwn(input.generation_configs, selectedKey)
    ? input.generation_configs[selectedKey]
    : { missing: true }
  return canonicalSha256({
    authority: input.authority,
    source_rel: input.source_rel,
    settings_sha256: input.settings_sha256,
    episode: input.episode,
    target: { kind, slot, output_path: outputPath },
    clip: {
      id: clip.id,
      editable: clip.editable,
      final_target: hashableFinalTarget(clip),
      runtime_inputs: kind === 'image' ? clip.image_runtime_inputs : clip.runtime_inputs,
      asset_ids: clip.asset_ids,
    },
    assets: assetsForClip(input, clip),
    delivery_spec: input.delivery_spec,
    generation_config: { key: selectedKey, value: selectedConfig },
  })
}

export function canvasProductionStatePath(root: string, episode: string): string {
  return path.join(path.resolve(root), '生产数据', `canvas_state_${validateEpisode(episode)}.json`)
}

async function canonicalStatePath(root: string, episode: string): Promise<string> {
  const base = await fs.realpath(root).catch(() => {
    throw new Error('作品目录不存在')
  })
  const stat = await fs.stat(base)
  if (!stat.isDirectory()) throw new Error('作品目录不存在')
  return path.join(base, '生产数据', `canvas_state_${validateEpisode(episode)}.json`)
}

async function withStateWriteLock<T>(file: string, action: () => Promise<T>): Promise<T> {
  const previous = stateWriteTails.get(file) ?? Promise.resolve()
  let release!: () => void
  const gate = new Promise<void>((resolve) => { release = resolve })
  const tail = previous.catch(() => undefined).then(() => gate)
  stateWriteTails.set(file, tail)
  await previous.catch(() => undefined)
  try {
    return await action()
  } finally {
    release()
    if (stateWriteTails.get(file) === tail) stateWriteTails.delete(file)
  }
}

async function atomicWriteJson(file: string, value: unknown): Promise<void> {
  await fs.mkdir(path.dirname(file), { recursive: true })
  const temp = `${file}.${process.pid}.${randomUUID()}.tmp`
  let handle: fs.FileHandle | undefined
  try {
    handle = await fs.open(temp, 'wx', 0o600)
    await handle.writeFile(`${JSON.stringify(value, null, 2)}\n`, 'utf8')
    await handle.sync()
    await handle.close()
    handle = undefined
    await fs.rename(temp, file)
    // Best-effort directory durability. Some platforms/filesystems reject
    // fsync on directories; the state file itself is already safely renamed.
    try {
      const directory = await fs.open(path.dirname(file), 'r')
      try {
        await directory.sync()
      } finally {
        await directory.close()
      }
    } catch {
      // ignored intentionally
    }
  } finally {
    if (handle) await handle.close().catch(() => undefined)
    await fs.unlink(temp).catch(() => undefined)
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function validateLoadedState(value: unknown, episode: string): CanvasProductionState {
  if (!isRecord(value) || value.kind !== STATE_KIND || (value.version !== 1 && value.version !== STATE_VERSION)) {
    throw new Error('canvas production state 格式或版本无效')
  }
  if (value.episode !== episode) throw new Error('canvas production state 集名不匹配')
  if (!Number.isInteger(value.revision) || Number(value.revision) < 1) throw new Error('canvas state revision 无效')
  if (!isRecord(value.authoring)) throw new Error('canvas state authoring 缺失')
  const authoring = normalizeCanvasAuthoringInput(value.authoring as unknown as CanvasAuthoringInput)
  const contentHash = computeCanvasContentHash(authoring)
  if (value.content_hash !== contentHash) throw new Error('canvas state content_hash 校验失败')
  if (!isRecord(value.node_fingerprints) || !Array.isArray(value.tasks) || !Array.isArray(value.history) || !isRecord(value.completion)) {
    throw new Error('canvas state 核心字段缺失')
  }
  const expectedNodes = computeCanvasNodeFingerprints(authoring)
  const expectedStages = computeCanvasStageFingerprints(authoring)
  if (value.version === 1) {
    const oldNodes = value.node_fingerprints as Record<string, unknown>
    value.node_fingerprints = Object.fromEntries(Object.entries(oldNodes).map(([id, raw]) => {
      const node = isRecord(raw) ? raw : {}
      return [id, { ...node, stage_input_hashes: expectedStages[id] }]
    }))
    value.tasks = (value.tasks as unknown[]).map((raw) => {
      if (!isRecord(raw)) return raw
      const nodeId = typeof raw.node_id === 'string' ? raw.node_id : ''
      const taskKind = raw.kind === 'image' || raw.kind === 'video' ? raw.kind : undefined
      const expected = taskKind ? expectedStages[nodeId]?.[taskKind] : undefined
      const active = raw.status === 'submitted' || raw.status === 'running'
      return expected && active && raw.input_hash !== expected
        ? { ...raw, status: 'stale', detail: 'v1 stage hash 已迁移，请重新提交' }
        : raw
    })
    value.version = STATE_VERSION
  }
  const loadedNodes = value.node_fingerprints as Record<string, unknown>
  const recordedIds = Object.keys(loadedNodes).sort()
  if (stableCanonicalJson(recordedIds) !== stableCanonicalJson(Object.keys(expectedNodes).sort())) {
    throw new Error('canvas state 节点集合与 authoring 不一致')
  }
  for (const [id, expected] of Object.entries(expectedNodes)) {
    const node = loadedNodes[id]
    if (!isRecord(node) || node.id !== id || node.input_hash !== expected ||
        !isRecord(node.stage_input_hashes) ||
        node.stage_input_hashes.image !== expectedStages[id].image ||
        node.stage_input_hashes.video !== expectedStages[id].video) {
      throw new Error(`canvas state 节点指纹无效: ${id}`)
    }
  }
  return { ...(value as unknown as CanvasProductionState), authoring }
}

async function readStateFile(file: string, episode: string): Promise<CanvasProductionState | null> {
  let text: string
  try {
    text = await fs.readFile(file, 'utf8')
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return null
    throw error
  }
  let value: unknown
  try {
    value = JSON.parse(text)
  } catch {
    throw new Error('canvas production state JSON 损坏')
  }
  return validateLoadedState(value, episode)
}

export async function readCanvasProductionState(root: string, episode: string): Promise<CanvasProductionState | null> {
  const cleanEpisode = validateEpisode(episode)
  const file = await canonicalStatePath(root, cleanEpisode)
  return readStateFile(file, cleanEpisode)
}

/** Serialize canonical authoring writes with candidate authorization/rename.
 * The callback must not call another production-state mutator. */
export async function withCanvasProductionStateLock<T>(
  root: string,
  episode: string,
  action: (state: CanvasProductionState | null) => Promise<T>,
): Promise<T> {
  const cleanEpisode = validateEpisode(episode)
  const file = await canonicalStatePath(root, cleanEpisode)
  return withStateWriteLock(file, async () => action(await readStateFile(file, cleanEpisode)))
}

function qaCounts(clip: CanvasData['clips'][number]): { blocks: number; warnings: number } {
  const fromFlags = (severity: string): number => (clip.qa || []).filter((flag) => {
    return String(flag.severity || '').toLowerCase() === severity || String(flag.status || '').toLowerCase() === severity
  }).length
  return {
    blocks: Math.max(0, Math.floor(clip.qa_blocks || 0), fromFlags('block')),
    warnings: Math.max(0, Math.floor(clip.qa_warnings || 0), fromFlags('warn')),
  }
}

function mediaFingerprint(clip: CanvasData['clips'][number] | undefined): string | undefined {
  if (!clip) return undefined
  const frames = (clip.frames || []).filter((frame) => frame.exists).map((frame) => ({
    role: frame.role,
    label: frame.label,
    revision: frame.revision || '',
    path: frame.abs || '',
  }))
  const hasMedia = clip.first_frame_exists || clip.video_exists || frames.length > 0
  if (!hasMedia) return undefined
  return canonicalSha256({
    first_frame_exists: clip.first_frame_exists,
    first_frame_path: clip.first_frame_abs || '',
    video_exists: clip.video_exists,
    video_revision: clip.video_revision || '',
    video_path: clip.video_abs || '',
    frames,
  })
}

function normalizedFinalEvidence(value: CanvasFinalArtifactEvidence | null): CanvasFinalArtifactEvidence | undefined {
  if (!value) return undefined
  return {
    path: String(value.path || '').trim(),
    exists: value.exists === true,
    sha256: String(value.sha256 || '').trim().toLowerCase(),
    content_hash: String(value.content_hash || '').trim().toLowerCase(),
    inputs_sha256: String(value.inputs_sha256 || '').trim().toLowerCase(),
    qa_blocks: Math.max(0, Math.floor(Number(value.qa_blocks) || 0)),
    qa_receipt_path: String(value.qa_receipt_path || '').trim(),
    qa_receipt_sha256: String(value.qa_receipt_sha256 || '').trim().toLowerCase(),
    probe_passed: value.probe_passed === true,
    revision: value.revision === undefined ? undefined : String(value.revision),
  }
}

function normalizedNodeAcceptance(value: CanvasNodeAcceptanceEvidence | undefined): CanvasNodeAcceptanceEvidence | undefined {
  if (!value) return undefined
  const reviewerKind = value.reviewer_kind === 'human' ? 'human' : value.reviewer_kind === 'delegated' ? 'delegated' : undefined
  if (!reviewerKind || value.verdict !== 'accepted' || Number(value.qa_blocks) !== 0) return undefined
  const out: CanvasNodeAcceptanceEvidence = {
    content_hash: String(value.content_hash || '').trim().toLowerCase(),
    input_hash: String(value.input_hash || '').trim().toLowerCase(),
    output_path: String(value.output_path || '').trim(),
    output_sha256: String(value.output_sha256 || '').trim().toLowerCase(),
    qa_receipt_path: String(value.qa_receipt_path || '').trim(),
    qa_receipt_sha256: String(value.qa_receipt_sha256 || '').trim().toLowerCase(),
    qa_blocks: 0,
    reviewer_kind: reviewerKind,
    verdict: 'accepted',
    job_id: String(value.job_id || '').trim(),
    accepted_at: String(value.accepted_at || '').trim(),
  }
  if (!out.output_path || !out.qa_receipt_path || !out.job_id || !out.accepted_at) return undefined
  if (!SHA256_RE.test(out.content_hash) || !SHA256_RE.test(out.input_hash) ||
      !SHA256_RE.test(out.output_sha256) || !SHA256_RE.test(out.qa_receipt_sha256)) return undefined
  return out
}

function acceptedInputsSha256(
  authoring: CanvasAuthoringInput,
  nodes: Record<string, CanvasProductionNodeState>,
): string | undefined {
  const manifest: Array<{ id: string; input_hash: string; output_sha256: string }> = []
  for (const clip of authoring.clips) {
    const node = nodes[clip.id]
    const acceptance = normalizedNodeAcceptance(node?.acceptance)
    if (!node || node.lifecycle !== 'accepted' || !acceptance ||
        acceptance.input_hash !== node.input_hash) {
      return undefined
    }
    manifest.push({ id: clip.id, input_hash: node.input_hash, output_sha256: acceptance.output_sha256 })
  }
  return canonicalSha256(manifest)
}

export function computeCanvasAcceptedInputsSha256(
  raw: CanvasAuthoringInput,
  acceptances: Record<string, CanvasNodeAcceptanceEvidence>,
): string | undefined {
  const authoring = normalizeCanvasAuthoringInput(raw)
  const fingerprints = computeCanvasNodeFingerprints(authoring)
  const manifest: Array<{ id: string; input_hash: string; output_sha256: string }> = []
  for (const clip of authoring.clips) {
    const acceptance = normalizedNodeAcceptance(acceptances[clip.id])
    if (!acceptance || acceptance.input_hash !== fingerprints[clip.id]) return undefined
    manifest.push({ id: clip.id, input_hash: fingerprints[clip.id], output_sha256: acceptance.output_sha256 })
  }
  return canonicalSha256(manifest)
}

function finalBlockers(
  authoring: CanvasAuthoringInput,
  nodes: Record<string, CanvasProductionNodeState>,
  contentHash: string,
  artifact: CanvasFinalArtifactEvidence | undefined,
): string[] {
  const blockers: string[] = []
  for (const id of Object.keys(nodes).sort()) {
    const node = nodes[id]
    if (node.lifecycle !== 'accepted') blockers.push(`node_not_accepted:${id}:${node.lifecycle}`)
    if (node.qa_blocks > 0) blockers.push(`node_qa_block:${id}:${node.qa_blocks}`)
    const acceptance = normalizedNodeAcceptance(node.acceptance)
    if (node.lifecycle === 'accepted' && (!acceptance || acceptance.input_hash !== node.input_hash)) {
      blockers.push(`node_acceptance_invalid:${id}`)
    }
  }
  const inputsSha256 = acceptedInputsSha256(authoring, nodes)
  if (!artifact || !artifact.exists) blockers.push('final_artifact_missing')
  else {
    if (!artifact.path) blockers.push('final_artifact_path_missing')
    if (!SHA256_RE.test(artifact.sha256)) blockers.push('final_artifact_sha256_invalid')
    if (artifact.content_hash !== contentHash) blockers.push('final_artifact_content_hash_stale')
    if (!inputsSha256 || artifact.inputs_sha256 !== inputsSha256) blockers.push('final_artifact_inputs_stale')
    if (artifact.qa_blocks > 0) blockers.push(`final_artifact_qa_block:${artifact.qa_blocks}`)
    if (!artifact.qa_receipt_path || !SHA256_RE.test(artifact.qa_receipt_sha256)) {
      blockers.push('final_artifact_qa_receipt_missing')
    }
    if (!artifact.probe_passed) blockers.push('final_artifact_probe_failed')
  }
  return blockers
}

function sameFinalArtifact(a: CanvasFinalArtifactEvidence | undefined, b: CanvasFinalArtifactEvidence | undefined): boolean {
  if (!a || !b) return a === b
  return a.path === b.path && a.exists === b.exists && a.sha256 === b.sha256 &&
    a.content_hash === b.content_hash && a.inputs_sha256 === b.inputs_sha256 &&
    a.qa_blocks === b.qa_blocks && a.qa_receipt_path === b.qa_receipt_path &&
    a.qa_receipt_sha256 === b.qa_receipt_sha256 && a.probe_passed === b.probe_passed
}

function refreshedCompletion(
  previous: CanvasProductionCompletion | undefined,
  authoring: CanvasAuthoringInput,
  nodes: Record<string, CanvasProductionNodeState>,
  contentHash: string,
  artifact: CanvasFinalArtifactEvidence | undefined,
): CanvasProductionCompletion {
  const blockers = finalBlockers(authoring, nodes, contentHash, artifact)
  const remainsComplete = Boolean(
    previous?.complete &&
    previous.bound_content_hash === contentHash &&
    sameFinalArtifact(previous.artifact, artifact) &&
    blockers.length === 0,
  )
  return {
    definition: COMPLETION_DEFINITION,
    complete: remainsComplete,
    bound_content_hash: remainsComplete ? contentHash : undefined,
    artifact,
    blockers,
    accepted_at: remainsComplete ? previous?.accepted_at : undefined,
  }
}

function currentTaskInputHash(
  task: CanvasProductionTask,
  nodes: Record<string, CanvasProductionNodeState>,
  contentHash: string,
  authoring: CanvasAuthoringInput,
): string | undefined {
  if (task.node_id === CANVAS_EPISODE_TASK_NODE_ID) return contentHash
  const node = nodes[task.node_id]
  if (!node) return undefined
  if ((task.kind === 'image' || task.kind === 'video') && task.target_slot) {
    return computeCanvasTargetFingerprint(
      authoring,
      task.node_id,
      task.kind,
      task.target_slot,
      task.target_output_path || '',
    )
  }
  return task.kind === 'image' || task.kind === 'video'
    ? node.stage_input_hashes[task.kind]
    : node.input_hash
}

export interface CanvasCandidatePromotionClaim {
  episode: string
  job_id: string
  scope: 'node' | 'final'
  content_hash: string
  task_input_hash: string
  target_output_path: string
  candidate_output_path: string
  node_id?: string
  node_input_hash?: string
  generation_kind?: CanvasGenerationKind
  target_slot?: string
  inputs_sha256?: string
}

/**
 * Hold the same lock used by every canvas-state mutation while a candidate is
 * revalidated and promoted.  The callback must do the final byte/stat check,
 * same-volume rename, and authoritative receipt write before returning.
 */
export async function withCurrentCanvasCandidatePromotion<T>(
  root: string,
  rawClaim: CanvasCandidatePromotionClaim,
  action: (state: CanvasProductionState, task: CanvasProductionTask) => Promise<T>,
): Promise<T> {
  const episode = validateEpisode(rawClaim.episode)
  const file = await canonicalStatePath(root, episode)
  return withStateWriteLock(file, async () => {
    const state = await readStateFile(file, episode)
    if (!state) throw new Error('candidate_promotion_state_missing')
    const task = state.tasks.find((item) => item.job_id === rawClaim.job_id)
    if (!task || (task.status !== 'submitted' && task.status !== 'running')) {
      throw new Error('candidate_promotion_task_not_active')
    }
    if (task.promotion_required !== true || task.content_hash !== rawClaim.content_hash ||
        state.content_hash !== rawClaim.content_hash || task.input_hash !== rawClaim.task_input_hash ||
        currentTaskInputHash(task, state.node_fingerprints, state.content_hash, state.authoring) !== task.input_hash) {
      throw new Error('candidate_promotion_task_stale')
    }
    const targetPath = normalizeTargetOutputPath(rawClaim.target_output_path)
    const candidatePath = normalizeTargetOutputPath(rawClaim.candidate_output_path)
    if (!targetPath || candidatePath !== canvasCandidateTargetRel(targetPath, task.job_id)) {
      throw new Error('candidate_promotion_path_mismatch')
    }

    if (rawClaim.scope === 'final') {
      if (task.node_id !== CANVAS_EPISODE_TASK_NODE_ID || task.kind !== 'production' ||
          task.target_output_path !== targetPath || task.candidate_output_path !== candidatePath ||
          !rawClaim.inputs_sha256 ||
          acceptedInputsSha256(state.authoring, state.node_fingerprints) !== rawClaim.inputs_sha256) {
        throw new Error('candidate_promotion_final_binding_mismatch')
      }
      const taskIndex = state.tasks.findIndex((item) => item.job_id === task.job_id)
      if (state.tasks.slice(taskIndex + 1).some((item) => item.target_output_path === targetPath)) {
        throw new Error('candidate_promotion_target_superseded')
      }
    } else {
      const nodeId = String(rawClaim.node_id || '').trim()
      const generationKind = rawClaim.generation_kind
      const node = state.node_fingerprints[nodeId]
      const authored = state.authoring.clips.find((clip) => clip.id === nodeId)
      if (!node || !authored || !generationKind || node.input_hash !== rawClaim.node_input_hash) {
        throw new Error('candidate_promotion_node_binding_mismatch')
      }
      if (task.node_id === CANVAS_EPISODE_TASK_NODE_ID && task.kind === 'production') {
        if (state.authoring.final_stage !== generationKind || authored.final_target.slot !== rawClaim.target_slot ||
            authored.final_target.output_path !== targetPath) {
          throw new Error('candidate_promotion_production_node_target_mismatch')
        }
      } else if (task.node_id !== nodeId || task.kind !== generationKind ||
          task.target_slot !== rawClaim.target_slot || task.target_output_path !== targetPath ||
          task.candidate_output_path !== candidatePath) {
        throw new Error('candidate_promotion_single_node_target_mismatch')
      }
      const taskIndex = state.tasks.findIndex((item) => item.job_id === task.job_id)
      const supersedingOwner = state.tasks.slice(taskIndex + 1).some((item) => {
        const ownsExactTarget = item.node_id === nodeId && item.target_output_path === targetPath
        const ownsProductionFinalTarget = item.node_id === CANVAS_EPISODE_TASK_NODE_ID &&
          item.kind === 'production' && authored.final_target.output_path === targetPath
        return ownsExactTarget || ownsProductionFinalTarget
      })
      if (supersedingOwner) throw new Error('candidate_promotion_target_superseded')
    }
    return action(state, task)
  })
}

const TERMINAL_TASKS = new Set<CanvasProductionTaskStatus>(['succeeded', 'failed', 'cancelled', 'stale'])

function isCurrentTask(
  task: CanvasProductionTask,
  nodes: Record<string, CanvasProductionNodeState>,
  contentHash: string,
  authoring: CanvasAuthoringInput,
): boolean {
  // A selective node/target fingerprint may intentionally survive an
  // unrelated authoring edit, but promotion is always bound to the canonical
  // episode revision.  Reusing an active task from an older root hash would
  // leave it permanently unpromotable because the main-process CAS correctly
  // rejects that old content_hash.
  return task.content_hash === contentHash &&
    currentTaskInputHash(task, nodes, contentHash, authoring) === task.input_hash
}

function deriveStatus(
  nodes: Record<string, CanvasProductionNodeState>,
  tasks: CanvasProductionTask[],
  completion: CanvasProductionCompletion,
  contentHash: string,
  authoring: CanvasAuthoringInput,
): CanvasProductionStatus {
  if (completion.complete) return 'complete'
  const values = Object.values(nodes)
  const currentArtifactBlocked = completion.artifact?.content_hash === contentHash &&
    (completion.artifact.qa_blocks || 0) > 0
  if (values.some((node) => node.qa_blocks > 0) || currentArtifactBlocked) return 'blocked'
  if (tasks.some((task) => {
    return (task.status === 'submitted' || task.status === 'running') && isCurrentTask(task, nodes, contentHash, authoring)
  })) return 'running'
  if (values.some((node) => node.lifecycle === 'generated' || Boolean(node.invalidation_reason)) ||
      tasks.some((task) => task.status === 'failed' && isCurrentTask(task, nodes, contentHash, authoring))) return 'needs_revision'
  if (values.length === 0 || values.some((node) => node.lifecycle === 'draft')) return 'draft'
  return 'ready'
}

function comparableState(state: CanvasProductionState): unknown {
  const nodes = Object.fromEntries(Object.entries(state.node_fingerprints).map(([id, node]) => [id, {
    id: node.id,
    input_hash: node.input_hash,
    stage_input_hashes: node.stage_input_hashes,
    lifecycle: node.lifecycle,
    media_fingerprint: node.media_fingerprint,
    qa_blocks: node.qa_blocks,
    qa_warnings: node.qa_warnings,
    invalidation_reason: node.invalidation_reason,
    acceptance: node.acceptance,
  }]))
  const tasks = state.tasks.map((task) => ({
    job_id: task.job_id,
    node_id: task.node_id,
    kind: task.kind,
    target_slot: task.target_slot,
    target_output_path: task.target_output_path,
    candidate_output_path: task.candidate_output_path,
    promotion_required: task.promotion_required,
    status: task.status,
    input_hash: task.input_hash,
    content_hash: task.content_hash,
    submitted_revision: task.submitted_revision,
    submitted_at: task.submitted_at,
    detail: task.detail,
  }))
  return {
    content_hash: state.content_hash,
    status: state.status,
    authoring: state.authoring,
    nodes,
    tasks,
    completion: state.completion,
  }
}

async function commitState(
  file: string,
  previous: CanvasProductionState | null,
  candidate: CanvasProductionState,
  reason: string,
  changedNodeIds: string[],
  invalidatedNodeIds: string[],
): Promise<CanvasProductionState> {
  const now = new Date().toISOString()
  const revision = (previous?.revision || 0) + 1
  const historyEntry: CanvasProductionHistoryEntry = {
    revision,
    content_hash: candidate.content_hash,
    status: candidate.status,
    reason,
    changed_node_ids: [...new Set(changedNodeIds)].sort(),
    invalidated_node_ids: [...new Set(invalidatedNodeIds)].sort(),
    created_at: now,
  }
  const state: CanvasProductionState = {
    ...candidate,
    revision,
    history: [...(previous?.history || []), historyEntry],
    created_at: previous?.created_at || now,
    updated_at: now,
  }
  await atomicWriteJson(file, state)
  return state
}

function blankCompletion(): CanvasProductionCompletion {
  return { definition: COMPLETION_DEFINITION, complete: false, blockers: ['final_artifact_missing'] }
}

function baseState(authoring: CanvasAuthoringInput, contentHash: string): CanvasProductionState {
  const now = new Date().toISOString()
  return {
    kind: STATE_KIND,
    version: STATE_VERSION,
    episode: authoring.episode,
    revision: 0,
    content_hash: contentHash,
    status: 'draft',
    authoring,
    node_fingerprints: {},
    tasks: [],
    completion: blankCompletion(),
    history: [],
    created_at: now,
    updated_at: now,
  }
}

export async function syncCanvasProductionState(
  root: string,
  request: CanvasProductionSyncRequest,
): Promise<CanvasProductionState> {
  const authoring = normalizeCanvasAuthoringInput(request.authoring)
  if (request.canvas.episode !== authoring.episode) throw new Error('CanvasData 与 authoring 集名不一致')
  const file = await canonicalStatePath(root, authoring.episode)
  return withStateWriteLock(file, async () => {
    const previous = await readStateFile(file, authoring.episode)
    if (request.observed_revision !== undefined &&
        (previous?.revision ?? 0) !== (request.observed_revision ?? 0)) {
      throw new Error('canvas_state_snapshot_stale')
    }
    const contentHash = computeCanvasContentHash(authoring)
    const inputHashes = computeCanvasNodeFingerprints(authoring)
    const stageInputHashes = computeCanvasStageFingerprints(authoring)
    const nextRevision = (previous?.revision || 0) + 1
    const now = new Date().toISOString()
    const canvasById = new Map(request.canvas.clips.map((clip) => [clip.id, clip]))
    const nodes: Record<string, CanvasProductionNodeState> = {}
    const changedNodeIds: string[] = []
    const invalidatedNodeIds: string[] = []

    for (const clip of authoring.clips) {
      const prior = previous?.node_fingerprints[clip.id]
      const canvasClip = canvasById.get(clip.id)
      const media = mediaFingerprint(canvasClip)
      const qa = canvasClip ? qaCounts(canvasClip) : { blocks: 0, warnings: 0 }
      const acceptance = normalizedNodeAcceptance(request.accepted_nodes?.[clip.id])
      // Accepted media is reusable across episode revisions when and only when
      // this node's complete dependency fingerprint is unchanged. The receipt's
      // content_hash remains immutable provenance for the run that produced it;
      // rebinding that field to a newer episode hash would fabricate evidence.
      const acceptanceCurrent = Boolean(acceptance && acceptance.input_hash === inputHashes[clip.id])
      const ready = clip.ready !== false
      const inputChanged = Boolean(prior && prior.input_hash !== inputHashes[clip.id])
      const mediaChanged = Boolean(prior && prior.media_fingerprint !== media)
      const awaitingRegeneration = Boolean(
        prior?.lifecycle === 'ready' &&
        (prior.invalidation_reason === 'authoring_input_changed' ||
          prior.invalidation_reason === 'regeneration_requested') &&
        !mediaChanged,
      )
      let lifecycle: CanvasProductionNodeState['lifecycle']
      let invalidationReason: string | undefined

      if (!ready) {
        lifecycle = 'draft'
        if (prior && prior.lifecycle !== 'draft') invalidationReason = 'authoring_not_ready'
      } else if (!media) {
        lifecycle = 'ready'
        if (prior?.media_fingerprint) invalidationReason = 'generated_media_missing'
      } else if (qa.blocks > 0) {
        lifecycle = 'generated'
        invalidationReason = 'qa_blocked'
      } else if (acceptanceCurrent) {
        lifecycle = 'accepted'
      } else if (inputChanged) {
        lifecycle = 'ready'
        invalidationReason = 'authoring_input_changed'
      } else if (awaitingRegeneration) {
        lifecycle = 'ready'
        invalidationReason = prior?.invalidation_reason
      } else {
        lifecycle = 'generated'
        invalidationReason = mediaChanged && prior?.lifecycle === 'accepted'
          ? 'accepted_media_changed'
          : prior?.invalidation_reason || 'awaiting_acceptance'
      }

      const changed = !prior || prior.input_hash !== inputHashes[clip.id] ||
        stableCanonicalJson(prior.stage_input_hashes) !== stableCanonicalJson(stageInputHashes[clip.id]) ||
        prior.lifecycle !== lifecycle ||
        prior.media_fingerprint !== media || prior.qa_blocks !== qa.blocks || prior.qa_warnings !== qa.warnings ||
        prior.invalidation_reason !== invalidationReason ||
        stableCanonicalJson(prior.acceptance ?? null) !== stableCanonicalJson(acceptanceCurrent ? acceptance : null)
      const newlyInvalidated = Boolean(
        invalidationReason &&
        (!prior?.invalidation_reason || prior.invalidation_reason !== invalidationReason || inputChanged || mediaChanged),
      )
      if (changed) changedNodeIds.push(clip.id)
      if (prior && (inputChanged || mediaChanged || (prior.lifecycle === 'accepted' && lifecycle !== 'accepted'))) {
        invalidatedNodeIds.push(clip.id)
      }
      nodes[clip.id] = {
        id: clip.id,
        input_hash: inputHashes[clip.id],
        stage_input_hashes: stageInputHashes[clip.id],
        lifecycle,
        media_fingerprint: media,
        qa_blocks: qa.blocks,
        qa_warnings: qa.warnings,
        invalidation_reason: invalidationReason,
        invalidated_at_revision: invalidationReason
          ? (newlyInvalidated ? nextRevision : (prior?.invalidated_at_revision || nextRevision))
          : undefined,
        acceptance: acceptanceCurrent ? acceptance : undefined,
        updated_at: changed ? now : (prior?.updated_at || now),
      }
    }

    for (const id of Object.keys(previous?.node_fingerprints || {})) {
      if (!nodes[id]) {
        changedNodeIds.push(id)
        invalidatedNodeIds.push(id)
      }
    }

    const tasks = (previous?.tasks || []).map((task): CanvasProductionTask => {
      if (isCurrentTask(task, nodes, contentHash, authoring)) return task
      // Terminal status is historical evidence. A succeeded image task may
      // intentionally change the downstream video input and must not be
      // rewritten as stale after the fact.
      if (TERMINAL_TASKS.has(task.status)) return task
      return { ...task, status: 'stale', detail: 'input_hash 已失效', updated_at: now }
    })
    const artifact = normalizedFinalEvidence(request.final_artifact)
    const completion = refreshedCompletion(previous?.completion, authoring, nodes, contentHash, artifact)
    const candidate: CanvasProductionState = {
      ...(previous || baseState(authoring, contentHash)),
      episode: authoring.episode,
      content_hash: contentHash,
      authoring,
      node_fingerprints: nodes,
      tasks,
      completion,
      status: 'draft',
    }
    candidate.status = deriveStatus(nodes, tasks, completion, contentHash, authoring)

    if (previous && stableCanonicalJson(comparableState(previous)) === stableCanonicalJson(comparableState(candidate))) {
      return previous
    }
    return commitState(
      file,
      previous,
      candidate,
      request.reason?.trim() || (previous ? 'sync' : 'initialize'),
      changedNodeIds,
      invalidatedNodeIds,
    )
  })
}

async function mutateExistingState(
  root: string,
  episode: string,
  action: (state: CanvasProductionState, now: string) => {
    candidate: CanvasProductionState
    reason: string
    changedNodeIds?: string[]
    invalidatedNodeIds?: string[]
  },
): Promise<CanvasProductionState> {
  const cleanEpisode = validateEpisode(episode)
  const file = await canonicalStatePath(root, cleanEpisode)
  return withStateWriteLock(file, async () => {
    const previous = await readStateFile(file, cleanEpisode)
    if (!previous) throw new Error('canvas production state 尚未初始化')
    const mutation = action(previous, new Date().toISOString())
    if (stableCanonicalJson(comparableState(previous)) === stableCanonicalJson(comparableState(mutation.candidate))) {
      return previous
    }
    return commitState(
      file,
      previous,
      mutation.candidate,
      mutation.reason,
      mutation.changedNodeIds || [],
      mutation.invalidatedNodeIds || [],
    )
  })
}

export async function recordCanvasTaskSubmit(
  root: string,
  request: CanvasTaskSubmitRequest,
): Promise<CanvasTaskSubmitResult> {
  let submitted: CanvasProductionTask | undefined
  let created = false
  const state = await mutateExistingState(root, request.episode, (previous, now) => {
    if (previous.content_hash !== request.expected_content_hash) throw new Error('canvas content_hash 已变化，请刷新后重试')
    const isEpisodeTask = request.node_id === CANVAS_EPISODE_TASK_NODE_ID
    const node = isEpisodeTask ? undefined : previous.node_fingerprints[request.node_id]
    if (!isEpisodeTask && !node) throw new Error(`找不到画布节点: ${request.node_id}`)
    if (node?.lifecycle === 'draft') throw new Error('draft 节点不能提交生成任务')
    const taskKind = String(request.kind || '').trim() || 'generation'
    const generationKind = request.kind === 'image' || request.kind === 'video' ? request.kind : undefined
    const productionKind = isEpisodeTask && taskKind === 'production'
    const targetSlot = (generationKind || productionKind) && request.target_slot
      ? normalizeTargetSlot(request.target_slot)
      : undefined
    const targetOutputPath = (targetSlot || productionKind) && request.target_output_path
      ? normalizeTargetOutputPath(request.target_output_path || '')
      : undefined
    const promotionRequired = request.promotion_required === true
    const taskInputHash = isEpisodeTask
      ? previous.content_hash
      : generationKind && targetSlot
        ? computeCanvasTargetFingerprint(previous.authoring, request.node_id, generationKind, targetSlot, targetOutputPath)
        : generationKind
          ? node!.stage_input_hashes[generationKind]
        : node!.input_hash
    const active = previous.tasks.find((task) => {
      return task.node_id === request.node_id &&
        task.kind === taskKind &&
        task.target_slot === targetSlot &&
        task.target_output_path === targetOutputPath &&
        (task.promotion_required === true) === promotionRequired &&
        task.content_hash === previous.content_hash &&
        task.input_hash === taskInputHash &&
        (task.status === 'submitted' || task.status === 'running')
    })
    if (active) {
      submitted = active
      return { candidate: previous, reason: `task_reuse:${active.job_id}` }
    }
    created = true
    const jobId = randomUUID()
    submitted = {
      job_id: jobId,
      node_id: request.node_id,
      kind: taskKind,
      target_slot: targetSlot,
      target_output_path: targetOutputPath,
      candidate_output_path: promotionRequired && targetOutputPath
        ? canvasCandidateTargetRel(targetOutputPath, jobId)
        : undefined,
      promotion_required: promotionRequired || undefined,
      status: 'submitted',
      input_hash: taskInputHash,
      content_hash: previous.content_hash,
      submitted_revision: previous.revision,
      submitted_at: now,
      updated_at: now,
      detail: request.detail?.trim() || undefined,
    }
    const supersededTaskIds = new Set(previous.tasks.flatMap((task) => {
      if (task.status !== 'submitted' && task.status !== 'running') return []
      if (productionKind && task.node_id !== CANVAS_EPISODE_TASK_NODE_ID) return [task.job_id]
      if (!productionKind && task.node_id === CANVAS_EPISODE_TASK_NODE_ID && task.kind === 'production') {
        return [task.job_id]
      }
      return []
    }))
    const tasks = [
      ...previous.tasks.map((task): CanvasProductionTask => supersededTaskIds.has(task.job_id)
        ? { ...task, status: 'stale', detail: `superseded_by:${jobId}`, updated_at: now }
        : task),
      submitted,
    ]
    const nodes = node ? {
      ...previous.node_fingerprints,
      [node.id]: {
        ...node,
        lifecycle: 'ready' as const,
        acceptance: undefined,
        invalidation_reason: 'regeneration_requested',
        invalidated_at_revision: previous.revision + 1,
        updated_at: now,
      },
    } : previous.node_fingerprints
    const completion = node
      ? refreshedCompletion(previous.completion, previous.authoring, nodes, previous.content_hash, previous.completion.artifact)
      : previous.completion
    const candidate = {
      ...previous,
      node_fingerprints: nodes,
      tasks,
      completion,
      status: deriveStatus(nodes, tasks, completion, previous.content_hash, previous.authoring),
    }
    return {
      candidate,
      reason: `task_submit:${submitted.job_id}`,
      changedNodeIds: node ? [node.id] : [],
      invalidatedNodeIds: node?.lifecycle === 'accepted' ? [node.id] : [],
    }
  })
  if (!submitted) throw new Error('生成任务提交失败')
  if (created && submitted.node_id !== CANVAS_EPISODE_TASK_NODE_ID) {
    // Clearing a node acceptance makes every previously complete inputs
    // manifest obsolete even when the root content hash is unchanged. Remove
    // it before the renderer can dispatch regeneration/compose work; the
    // adapter recreates it only after the new accepted set commits.
    const stateFile = await canonicalStatePath(root, request.episode)
    await fs.unlink(path.join(
      path.dirname(stateFile),
      `canvas_inputs_manifest_${validateEpisode(request.episode)}.json`,
    )).catch((error: NodeJS.ErrnoException) => {
      if (error.code !== 'ENOENT') throw error
    })
  }
  return {
    state,
    job_id: submitted.job_id,
    input_hash: submitted.input_hash,
    node_input_hash: submitted.node_id === CANVAS_EPISODE_TASK_NODE_ID
      ? undefined
      : state.node_fingerprints[submitted.node_id]?.input_hash,
    content_hash: submitted.content_hash,
    target_slot: submitted.target_slot,
    target_output_path: submitted.target_output_path,
    candidate_output_path: submitted.candidate_output_path,
    final_target_output_path: submitted.node_id === CANVAS_EPISODE_TASK_NODE_ID
      ? submitted.target_output_path
      : undefined,
    final_candidate_output_path: submitted.node_id === CANVAS_EPISODE_TASK_NODE_ID
      ? submitted.candidate_output_path
      : undefined,
    promotion_required: submitted.promotion_required === true,
    task_status: submitted.status,
    created,
  }
}

export async function updateCanvasTaskStatus(
  root: string,
  request: CanvasTaskStatusRequest,
): Promise<CanvasProductionState> {
  return mutateExistingState(root, request.episode, (previous, now) => {
    const index = previous.tasks.findIndex((task) => task.job_id === request.job_id)
    if (index < 0) throw new Error(`找不到任务: ${request.job_id}`)
    const old = previous.tasks[index]
    // A very fast receipt can settle the task before the renderer's dispatch
    // acknowledgement arrives. Late `running` is then an idempotent ACK, not
    // a reason to turn a verified terminal result into a UI failure.
    if (request.status === 'running' && TERMINAL_TASKS.has(old.status)) {
      return { candidate: previous, reason: `task_running_ack:${old.job_id}` }
    }
    const currentInput = currentTaskInputHash(old, previous.node_fingerprints, previous.content_hash, previous.authoring)
    const status: CanvasProductionTaskStatus = currentInput === old.input_hash ? request.status : 'stale'
    const verifiedLeaseRecovery = old.status === 'failed' && status === 'succeeded' &&
      /lease expired/.test(old.detail || '') && /已验收|verified receipt/.test(request.detail || '')
    if (TERMINAL_TASKS.has(old.status) && old.status !== status && !verifiedLeaseRecovery) {
      throw new Error(`任务已终止: ${old.status}`)
    }
    const tasks = [...previous.tasks]
    tasks[index] = {
      ...old,
      status,
      detail: status === 'stale' ? 'input_hash 已失效' : (request.detail?.trim() || old.detail),
      updated_at: now,
    }
    const candidate = {
      ...previous,
      tasks,
      status: deriveStatus(previous.node_fingerprints, tasks, previous.completion, previous.content_hash, previous.authoring),
    }
    return { candidate, reason: `task_${status}:${old.job_id}`, changedNodeIds: [old.node_id] }
  })
}

export async function acceptCanvasNode(
  root: string,
  request: CanvasNodeAcceptRequest,
): Promise<CanvasProductionState> {
  return mutateExistingState(root, request.episode, (previous, now) => {
    if (previous.content_hash !== request.expected_content_hash) throw new Error('canvas content_hash 已变化，请刷新后重试')
    const node = previous.node_fingerprints[request.node_id]
    if (!node) throw new Error(`找不到画布节点: ${request.node_id}`)
    if (node.input_hash !== request.expected_input_hash) throw new Error('节点 input_hash 已变化，请刷新后重试')
    if (node.qa_blocks > 0) throw new Error('节点仍有 QA block，不能 accepted')
    if (!node.media_fingerprint || !['generated', 'accepted'].includes(node.lifecycle)) {
      throw new Error('节点尚无当前生成媒体，不能 accepted')
    }
    const evidence = normalizedNodeAcceptance(request.evidence)
    if (!evidence || evidence.content_hash !== previous.content_hash || evidence.input_hash !== node.input_hash) {
      throw new Error('节点验收证据未绑定当前 content_hash/input_hash')
    }
    const accepted: CanvasProductionNodeState = {
      ...node,
      lifecycle: 'accepted',
      acceptance: evidence,
      invalidation_reason: undefined,
      invalidated_at_revision: undefined,
      updated_at: now,
    }
    const nodes = { ...previous.node_fingerprints, [node.id]: accepted }
    const completion = refreshedCompletion(previous.completion, previous.authoring, nodes, previous.content_hash, previous.completion.artifact)
    const candidate = {
      ...previous,
      node_fingerprints: nodes,
      completion,
      status: deriveStatus(nodes, previous.tasks, completion, previous.content_hash, previous.authoring),
    }
    return { candidate, reason: `node_accept:${node.id}`, changedNodeIds: [node.id] }
  })
}

export async function acceptCanvasFinal(
  root: string,
  request: CanvasFinalAcceptRequest,
): Promise<CanvasProductionState> {
  return mutateExistingState(root, request.episode, (previous, now) => {
    if (previous.content_hash !== request.expected_content_hash) throw new Error('canvas content_hash 已变化，请刷新后重试')
    const artifact = normalizedFinalEvidence(request.artifact)
    if (!artifact) throw new Error('最终产物证据缺失')
    const blockers = finalBlockers(previous.authoring, previous.node_fingerprints, previous.content_hash, artifact)
    if (blockers.length > 0) throw new Error(`最终完成定义未满足: ${blockers.join(', ')}`)
    const completion: CanvasProductionCompletion = {
      definition: COMPLETION_DEFINITION,
      complete: true,
      bound_content_hash: previous.content_hash,
      artifact,
      blockers: [],
      accepted_at: now,
    }
    const candidate = { ...previous, completion, status: 'complete' as const }
    return { candidate, reason: 'final_accept', changedNodeIds: Object.keys(previous.node_fingerprints) }
  })
}
