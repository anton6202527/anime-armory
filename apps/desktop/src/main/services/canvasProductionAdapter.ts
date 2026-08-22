import { createHash, randomUUID } from 'node:crypto'
import { execFile } from 'node:child_process'
import { createReadStream, existsSync } from 'node:fs'
import fs from 'node:fs/promises'
import path from 'node:path'
import { promisify } from 'node:util'
import type {
  CanvasAuthoringAssetSummary,
  CanvasAuthoringInput,
  CanvasData,
  CanvasFinalArtifactEvidence,
  CanvasGenerationKind,
  CanvasNodeAcceptanceEvidence,
  CanvasProductionState,
  CanvasTaskSubmitResult,
  LineKey,
} from '@shared/types'
import {
  canvasCandidateTargetRel,
  canvasFinalTargetRel,
  canvasVideoTargetRel,
  stableCanvasSlotToken,
} from '../../shared/canvasTargets'
import {
  CANVAS_EPISODE_TASK_NODE_ID,
  acceptCanvasFinal,
  computeCanvasContentHash,
  computeCanvasAcceptedInputsSha256,
  computeCanvasNodeFingerprints,
  computeCanvasTargetFingerprint,
  readCanvasProductionState,
  stableCanonicalJson,
  recordCanvasTaskSubmit,
  syncCanvasProductionState,
  updateCanvasTaskStatus,
  withCurrentCanvasCandidatePromotion,
} from './canvasProduction'

const digestCache = new Map<string, Promise<string>>()
const execFileAsync = promisify(execFile)

function safeEpisode(episode: string): string {
  const value = episode.trim()
  if (!value || value.includes('/') || value.includes('\\') || value.includes('\0')) throw new Error('非法集名')
  return value
}

function relativeInside(root: string, value: string): string | null {
  const rel = path.relative(root, value).replaceAll('\\', '/')
  return !rel || rel.startsWith('../') || path.isAbsolute(rel) ? null : rel
}

function statIdentity(stat: Awaited<ReturnType<typeof fs.stat>>): string {
  return `${stat.dev}\0${stat.ino}\0${stat.size}\0${stat.mtimeMs}\0${stat.ctimeMs}`
}

async function streamSha256(file: string): Promise<string> {
  return new Promise<string>((resolve, reject) => {
    const hash = createHash('sha256')
    const stream = createReadStream(file)
    stream.on('data', (chunk) => hash.update(chunk))
    stream.on('error', reject)
    stream.on('end', () => resolve(hash.digest('hex')))
  })
}

async function stableFileSha256(file: string): Promise<string> {
  const before = await fs.stat(file)
  if (!before.isFile()) throw new Error('证据路径不是文件')
  const beforeIdentity = statIdentity(before)
  const digest = await streamSha256(file)
  const after = await fs.stat(file)
  if (beforeIdentity !== statIdentity(after)) throw new Error('文件在 SHA-256 读取期间发生变化')
  return digest
}

async function sha256File(file: string): Promise<string> {
  const stat = await fs.stat(file)
  const key = `${file}\0${statIdentity(stat)}`
  const existing = digestCache.get(key)
  if (existing) return existing
  const pending = stableFileSha256(file).catch((error) => {
    digestCache.delete(key)
    throw error
  })
  digestCache.set(key, pending)
  if (digestCache.size > 1_000) {
    const oldest = digestCache.keys().next().value
    if (oldest) digestCache.delete(oldest)
  }
  return pending
}

interface CanvasMediaMetadata {
  width: number
  height: number
  duration_seconds: number | null
  has_audio: boolean
  has_video: boolean
}

interface CanvasMediaSnapshot {
  file: string
  sha256: string
  size: number
  mtime_ms: number
  stat_identity: string
  metadata: CanvasMediaMetadata
}

interface JsonEvidence {
  document: Record<string, unknown> | null
  sha256: string
}

const mediaSnapshotCache = new Map<string, Promise<CanvasMediaSnapshot>>()

function ffprobePath(): string {
  if (process.env.FFPROBE_PATH) return process.env.FFPROBE_PATH
  const candidates = process.platform === 'win32'
    ? ['ffprobe']
    : ['/opt/homebrew/bin/ffprobe', '/usr/local/bin/ffprobe', '/usr/bin/ffprobe', 'ffprobe']
  return candidates.find((candidate) => !path.isAbsolute(candidate) || existsSync(candidate)) ?? 'ffprobe'
}

async function probeMediaMetadata(file: string): Promise<CanvasMediaMetadata> {
  const { stdout } = await execFileAsync(ffprobePath(), [
    '-v', 'error',
    '-show_entries', 'format=duration:stream=codec_type,width,height,duration',
    '-of', 'json',
    file,
  ], { timeout: 20_000, maxBuffer: 1_000_000 })
  const data = record(JSON.parse(stdout))
  const streams = Array.isArray(data?.streams)
    ? data.streams.map(record).filter((item): item is Record<string, unknown> => item !== null)
    : []
  const visual = streams.find((stream) => stream.codec_type === 'video')
  const formatDuration = Number(record(data?.format)?.duration)
  const streamDurations = streams.map((stream) => Number(stream.duration)).filter((value) => {
    return Number.isFinite(value) && value > 0
  })
  const duration = Number.isFinite(formatDuration) && formatDuration > 0
    ? formatDuration
    : streamDurations.length ? Math.max(...streamDurations) : null
  return {
    width: Number(visual?.width) || 0,
    height: Number(visual?.height) || 0,
    duration_seconds: duration,
    has_audio: streams.some((stream) => stream.codec_type === 'audio'),
    has_video: Boolean(visual),
  }
}

function basicMediaValid(snapshot: CanvasMediaSnapshot): boolean {
  if (!snapshot.metadata.has_video || snapshot.metadata.width <= 0 || snapshot.metadata.height <= 0) return false
  if (/\.(?:mp4|mov|m4v|webm)$/i.test(snapshot.file)) {
    return snapshot.metadata.duration_seconds !== null && snapshot.metadata.duration_seconds > 0
  }
  return true
}

/**
 * One evidence snapshot spans every expensive observation.  Realpath and the
 * full stat identity bracket SHA-256 and ffprobe, so a writer cannot bind the
 * digest of version A to the media metadata of version B.
 */
async function mediaSnapshot(file: string): Promise<CanvasMediaSnapshot> {
  const realBefore = await fs.realpath(file)
  const before = await fs.stat(realBefore)
  if (!before.isFile() || before.size <= 0) throw new Error('媒体证据路径不是非空文件')
  const beforeIdentity = statIdentity(before)
  const key = `${realBefore}\0${beforeIdentity}`
  const cached = mediaSnapshotCache.get(key)
  if (cached) return cached
  const pending = (async () => {
    const digest = await streamSha256(realBefore)
    const metadata = await probeMediaMetadata(realBefore)
    const [realAfter, after] = await Promise.all([fs.realpath(file), fs.stat(realBefore)])
    if (realAfter !== realBefore || statIdentity(after) !== beforeIdentity) {
      throw new Error('媒体文件在 SHA-256 与 ffprobe 快照期间发生变化')
    }
    return {
      file: realBefore,
      sha256: digest,
      size: before.size,
      mtime_ms: before.mtimeMs,
      stat_identity: beforeIdentity,
      metadata,
    }
  })().catch((error) => {
    mediaSnapshotCache.delete(key)
    throw error
  })
  mediaSnapshotCache.set(key, pending)
  if (mediaSnapshotCache.size > 500) {
    const oldest = mediaSnapshotCache.keys().next().value
    if (oldest) mediaSnapshotCache.delete(oldest)
  }
  return pending
}

async function mediaSnapshotStillCurrent(snapshot: CanvasMediaSnapshot): Promise<boolean> {
  const [real, stat] = await Promise.all([
    fs.realpath(snapshot.file).catch(() => ''),
    fs.stat(snapshot.file).catch(() => null),
  ])
  return real === snapshot.file && stat !== null && statIdentity(stat) === snapshot.stat_identity
}

async function readJsonEvidence(file: string): Promise<JsonEvidence> {
  const realBefore = await fs.realpath(file)
  const before = await fs.stat(realBefore)
  if (!before.isFile()) throw new Error('JSON 证据路径不是文件')
  const identity = statIdentity(before)
  const bytes = await fs.readFile(realBefore)
  const after = await fs.stat(realBefore)
  if (identity !== statIdentity(after) || await fs.realpath(file) !== realBefore) {
    throw new Error('JSON 证据在读取期间发生变化')
  }
  return {
    document: record(JSON.parse(bytes.toString('utf8'))),
    sha256: createHash('sha256').update(bytes).digest('hex'),
  }
}

/** Exported for deterministic service-level regression tests; production
 * callers should consume verified receipts rather than this primitive. */
export async function probeCanvasProductionMedia(file: string): Promise<boolean> {
  return mediaSnapshot(file).then(basicMediaValid).catch(() => false)
}

async function readJson(file: string): Promise<unknown> {
  try {
    return JSON.parse(await fs.readFile(file, 'utf8')) as unknown
  } catch {
    return undefined
  }
}

async function existingInside(root: string, value: string): Promise<string | null> {
  if (!value.trim()) return null
  const base = await fs.realpath(root).catch(() => '')
  if (!base) return null
  const candidate = path.isAbsolute(value) ? path.resolve(value) : path.resolve(base, value)
  // Absolute paths emitted by the canvas may use an OS alias such as `/var`
  // while realpath(root) resolves to `/private/var`.  Realpath confinement
  // below is authoritative; applying a pre-realpath lexical check to absolute
  // paths would reject the same inode solely because of that alias.
  if (!path.isAbsolute(value)) {
    const lexical = path.relative(base, candidate)
    if (!lexical || lexical.startsWith('../') || path.isAbsolute(lexical)) return null
  }
  const real = await fs.realpath(candidate).catch(() => '')
  if (!real) return null
  const rel = path.relative(base, real)
  return rel && !rel.startsWith('../') && !path.isAbsolute(rel) ? real : null
}

function record(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null
}

function sourceRel(canvas: CanvasData): string | null {
  if (canvas.source === 'storyboard') return `脚本/${canvas.episode}/storyboard.json`
  if (canvas.source === 'panel_script') return `脚本/${canvas.episode}/panel_script.json`
  return null
}

const SOURCE_RUNTIME_KEYS = new Set([
  'video_out', 'firstframe_png', 'endframe_png', 'midframe_png', 'anchor_png',
  'video_revision', 'revision', 'generated_at', 'updated_at', 'qa', 'qa_flags',
  'score',
])
const MIDFRAME_RUNTIME_KEYS = new Set(['midframe_png', 'anchor_png', 'png', 'path', 'image', 'image_path'])

function authoringOnly(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(authoringOnly)
  const item = record(value)
  if (!item) return value
  return Object.fromEntries(Object.entries(item).flatMap(([key, child]) => {
    // `continuity.midframe` may be an authored control object. Preserve its
    // timing/reason/use fields while recursive runtime path keys are removed;
    // the legacy scalar form is only a generated path and remains excluded.
    if (key === 'midframe') {
      const midframe = record(child)
      if (!midframe) return []
      return [[key, authoringOnly(Object.fromEntries(
        Object.entries(midframe).filter(([midKey]) => !MIDFRAME_RUNTIME_KEYS.has(midKey)),
      ))]]
    }
    return SOURCE_RUNTIME_KEYS.has(key) ? [] : [[key, authoringOnly(child)]]
  }))
}

async function canonicalSource(file: string): Promise<{ document: unknown; sha256: string; raw_sha256: string }> {
  const bytes = await fs.readFile(file)
  const parsed = JSON.parse(bytes.toString('utf8')) as unknown
  const document = authoringOnly(parsed)
  return {
    document,
    sha256: createHash('sha256').update(stableCanonicalJson(document), 'utf8').digest('hex'),
    raw_sha256: createHash('sha256').update(bytes).digest('hex'),
  }
}

function canonicalSourceFragments(
  canvas: CanvasData,
  document: unknown,
  sourceSha256: string,
): { context: unknown; byId: Map<string, unknown> } {
  const root = record(document)
  const collectionKey = canvas.source === 'panel_script' ? 'panels' : 'clips'
  const entries = Array.isArray(root?.[collectionKey]) ? root[collectionKey] as unknown[] : []
  const context = root
    ? Object.fromEntries(Object.entries(root).filter(([key]) => key !== collectionKey))
    : { unmapped_source_sha256: sourceSha256 }
  const byId = new Map<string, unknown>()
  const duplicates = new Set<string>()
  entries.forEach((entry, index) => {
    const item = record(entry)
    const explicit = canvas.source === 'panel_script'
      ? (typeof item?.panel_id === 'string' ? item.panel_id.trim() : '')
      : (typeof item?.id === 'string' ? item.id.trim() : '')
    const fallback = canvas.source === 'panel_script'
      ? `P${String(index + 1).padStart(3, '0')}`
      : `${canvas.episode}_CLIP${String(index + 1).padStart(2, '0')}`
    const id = explicit || fallback
    if (byId.has(id)) {
      byId.delete(id)
      duplicates.add(id)
    } else if (!duplicates.has(id)) {
      byId.set(id, entry)
    }
  })
  // A missing/ambiguous mapping must invalidate conservatively. Binding the
  // complete source digest to that node prevents a lossy UI projection from
  // reusing media after an unseen source edit.
  for (const clip of canvas.clips) {
    if (!byId.has(clip.id)) byId.set(clip.id, { unmapped_source_sha256: sourceSha256 })
  }
  return { context, byId }
}

async function settingsSha256(root: string): Promise<string> {
  try {
    return await sha256File(path.join(root, '_设置.md'))
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
      return createHash('sha256').update('', 'utf8').digest('hex')
    }
    throw error
  }
}

function expectedDurationSeconds(canvas: CanvasData): number | null {
  if (typeof canvas.total_duration === 'number' && Number.isFinite(canvas.total_duration) && canvas.total_duration > 0) {
    return canvas.total_duration
  }
  const durations = canvas.clips.map((clip) => clip.duration).filter((value): value is number => {
    return typeof value === 'number' && Number.isFinite(value) && value > 0
  })
  return durations.length === canvas.clips.length && durations.length > 0
    ? durations.reduce((total, value) => total + value, 0)
    : null
}

function finalAudioRequirement(value: string): 'required' | 'forbidden' | 'unspecified' {
  const policy = value.trim().toLowerCase()
  if (!policy) return 'unspecified'
  // Only final-delivery language is authoritative here.  A setting such as
  // “无声视频流” governs generated clips and must not accidentally reject a
  // voiced compose master.
  if (/^(?:forbidden|none|no_audio|silent_final|mute_final)$/.test(policy) ||
      /最终(?:成片|母版).*?(?:无声|静音|禁用音轨)|(?:无声|静音).*?最终(?:成片|母版)/.test(policy)) return 'forbidden'
  if (/^(?:required|require|with_audio|must_have_audio)$/.test(policy) ||
      /最终(?:成片|母版).*?(?:必须|保留|包含).*?(?:音频|音轨|声音)|(?:full|locked)_master_song|有声成片/.test(policy)) {
    return 'required'
  }
  return 'unspecified'
}

function isReferenceFrameText(value: string): boolean {
  return /出图[\\/]共享|shared_asset|入参|参考|引用|reference|ref|asset|input|consumed|style/i.test(value)
}

function productionCanvas(line: LineKey, canvas: CanvasData): CanvasData {
  return {
    ...canvas,
    clips: canvas.clips.map((clip) => {
      if (line !== 'comic') {
        return { ...clip, first_frame_abs: undefined, first_frame_exists: false, frames: [] }
      }
      return {
        ...clip,
        video_abs: undefined,
        video_exists: false,
        video_revision: undefined,
        frames: (clip.frames || []).filter((frame) => {
          return !isReferenceFrameText(`${frame.role || ''} ${frame.label || ''} ${frame.abs || ''}`)
        }),
      }
    }),
  }
}

async function canvasWithObservedStableTargets(
  root: string,
  line: LineKey,
  canvas: CanvasData,
  authoring: CanvasAuthoringInput,
): Promise<CanvasData> {
  const targets = new Map(authoring.clips.map((clip) => [clip.id, clip.final_target.output_path]))
  return {
    ...canvas,
    clips: await Promise.all(canvas.clips.map(async (clip) => {
      const targetPath = targets.get(clip.id)
      if (!targetPath) return clip
      const file = await existingInside(root, targetPath)
      if (!file) return clip
      const snapshot = await mediaSnapshot(file).catch(() => null)
      if (!snapshot || !basicMediaValid(snapshot)) return clip
      const revision = `${snapshot.size.toString(16)}-${Math.floor(snapshot.mtime_ms).toString(16)}`
      if (line !== 'comic') {
        return { ...clip, video_abs: snapshot.file, video_exists: true, video_revision: revision }
      }
      let matched = false
      const frames = (clip.frames || []).map((frame) => {
        const rel = frame.abs ? relativeInside(root, frame.abs) : null
        if (rel !== targetPath) return frame
        matched = true
        return { ...frame, abs: snapshot.file, exists: true, revision }
      })
      if (!matched) frames.push({ role: 'panel', label: '成图', abs: snapshot.file, exists: true, revision })
      return { ...clip, frames }
    })),
  }
}

function inputFramesForClip(line: LineKey, clip: CanvasData['clips'][number]) {
  return (clip.frames || []).filter((frame) => {
    if (!frame.abs) return false
    return line === 'comic'
      ? isReferenceFrameText(`${frame.role || ''} ${frame.label || ''} ${frame.abs}`)
      : true
  })
}

function imageInputFramesForClip(line: LineKey, clip: CanvasData['clips'][number]) {
  return inputFramesForClip(line, clip).filter((frame) => {
    return line === 'comic' || isReferenceFrameText(`${frame.role || ''} ${frame.label || ''} ${frame.abs || ''}`)
  })
}

async function assetSummaries(root: string, canvas: CanvasData): Promise<CanvasAuthoringAssetSummary[]> {
  const byId = new Map<string, CanvasAuthoringAssetSummary>()
  const frames = canvas.shared_assets || []
  for (const frame of frames) {
    const abs = frame.abs || ''
    const rel = abs ? relativeInside(root, abs) : null
    const id = rel || `${frame.role || 'asset'}:${frame.label}`
    if (!id || byId.has(id)) continue
    let digest = frame.revision || `missing:${id}`
    if (frame.exists && abs) {
      try {
        digest = await sha256File(abs)
      } catch {
        digest = `unreadable:${id}:${frame.revision || ''}`
      }
    }
    byId.set(id, {
      id,
      role: frame.role || undefined,
      content_digest: digest,
      summary: { label: frame.label, path: rel },
    })
  }
  return [...byId.values()]
}

async function runtimeInputs(root: string, line: LineKey, clip: CanvasData['clips'][number]) {
  return Promise.all(inputFramesForClip(line, clip).map(async (frame) => {
    const rel = frame.abs ? relativeInside(root, frame.abs) : null
    let sha256 = ''
    if (frame.exists && frame.abs) sha256 = await sha256File(frame.abs).catch(() => '')
    return {
      role: frame.role,
      path: rel || frame.abs || '',
      sha256: sha256 || `missing:${rel || frame.abs || frame.label}`,
    }
  }))
}

async function imageRuntimeInputs(root: string, line: LineKey, clip: CanvasData['clips'][number]) {
  const imageClip = { ...clip, frames: imageInputFramesForClip(line, clip) }
  return runtimeInputs(root, line, imageClip)
}

function inferredLegacyTarget(
  line: LineKey,
  canvas: CanvasData,
  key: string,
): { slot: string; outputPath: string } | null {
  for (const clip of canvas.clips) {
    if (key === `video:${clip.id}`) {
      return {
        slot: 'video',
        outputPath: clip.video_abs || '',
      }
    }
    if (key === `image:${clip.id}`) {
      const selected = line === 'comic'
        ? (clip.frames || []).find((frame) => frame.abs && !isReferenceFrameText(`${frame.role} ${frame.label} ${frame.abs}`))
        : (clip.frames || []).find((frame) => frame.abs && /first|首帧/i.test(`${frame.role} ${frame.label}`))
      return {
        slot: line === 'comic' ? 'panel' : 'first',
        outputPath: selected?.abs || '',
      }
    }
  }
  return null
}

async function generationConfigs(
  root: string,
  episode: string,
  line: LineKey,
  canvas: CanvasData,
): Promise<Record<string, unknown>> {
  const raw = record(await readJson(path.join(root, '生产数据', `canvas_generation_controls_${episode}.json`)))
  const configs = record(raw?.configs)
  if (!configs) return {}
  return Object.fromEntries(await Promise.all(Object.entries(configs).map(async ([key, value]) => {
    const item = record(value)
    if (!item) return [key, value]
    const { updated_at: _updatedAt, ...rawStable } = item
    const legacy = inferredLegacyTarget(line, canvas, key)
    const stable = {
      ...rawStable,
      target_slot: typeof rawStable.target_slot === 'string' && rawStable.target_slot.trim()
        ? rawStable.target_slot.trim()
        : legacy?.slot || '',
      target_output_path: typeof rawStable.target_output_path === 'string' && rawStable.target_output_path.trim()
        ? rawStable.target_output_path.trim()
        : legacy?.outputPath
          ? relativeInside(root, legacy.outputPath) || legacy.outputPath
          : '',
    }
    const targetPath = typeof stable.target_output_path === 'string' ? stable.target_output_path : ''
    const targetResolved = targetPath ? path.resolve(root, targetPath) : ''
    const referencePaths = (Array.isArray(rawStable.reference_paths)
      ? rawStable.reference_paths.filter((entry): entry is string => typeof entry === 'string')
      : []).filter((referencePath) => !targetResolved || path.resolve(root, referencePath) !== targetResolved)
    const referenceEvidence = await Promise.all(referencePaths.map(async (referencePath) => {
      const file = await existingInside(root, referencePath)
      return {
        path: referencePath,
        sha256: file ? await sha256File(file).catch(() => '') : '',
      }
    }))
    return [key, { ...stable, reference_paths: referencePaths, reference_evidence: referenceEvidence }]
  })))
}

export async function buildCanvasAuthoringInput(
  root: string,
  line: LineKey,
  canvas: CanvasData,
): Promise<CanvasAuthoringInput | null> {
  const rel = sourceRel(canvas)
  if (!rel) return null
  const source = await canonicalSource(path.join(root, rel))
  if (canvas.source_file_sha256 && canvas.source_file_sha256 !== source.raw_sha256) {
    throw new Error('canvas_projection_source_snapshot_stale')
  }
  const effectiveSettingsSha256 = await settingsSha256(root)
  if (canvas.settings_file_sha256 && canvas.settings_file_sha256 !== effectiveSettingsSha256) {
    throw new Error('canvas_projection_settings_snapshot_stale')
  }
  const sourceFragments = canonicalSourceFragments(canvas, source.document, source.sha256)
  const assets = await assetSummaries(root, canvas)
  const runtimeByClip = new Map(await Promise.all(canvas.clips.map(async (clip) => {
    return [clip.id, await runtimeInputs(root, line, clip)] as const
  })))
  const imageRuntimeByClip = new Map(await Promise.all(canvas.clips.map(async (clip) => {
    return [clip.id, await imageRuntimeInputs(root, line, clip)] as const
  })))
  const assetIdsByPath = new Map(assets.flatMap((asset) => {
    const relPath = record(asset.summary)?.path
    return typeof relPath === 'string' && relPath ? [[relPath, asset.id] as const] : []
  }))
  const configs = await generationConfigs(root, canvas.episode, line, canvas)
  return {
    authority: `${line}:${canvas.source}`,
    source_rel: rel,
    source_sha256: source.sha256,
    settings_sha256: effectiveSettingsSha256,
    episode: canvas.episode,
    final_stage: line === 'comic' ? 'image' : 'video',
    clips: canvas.clips.map((clip) => {
      const declaredFinalOutput = line === 'comic'
        ? (clip.frames || []).find((frame) => frame.abs &&
            !isReferenceFrameText(`${frame.role} ${frame.label} ${frame.abs}`))?.abs
        : clip.video_abs
      const fallbackFinalOutput = line === 'comic'
        ? `出图/${canvas.episode}/panels/${clip.id}.png`
        : canvasVideoTargetRel(canvas.episode, clip.id)
      const finalOutputPath = declaredFinalOutput
        ? relativeInside(root, declaredFinalOutput) || fallbackFinalOutput
        : fallbackFinalOutput
      const boundAssets = inputFramesForClip(line, clip).flatMap((frame) => {
        const relPath = frame.abs ? relativeInside(root, frame.abs) : null
        const id = relPath ? assetIdsByPath.get(relPath) : undefined
        return id ? [id] : []
      })
      return {
        id: clip.id,
        final_target: {
          slot: line === 'comic' ? 'panel' : 'video',
          output_path: finalOutputPath,
        },
        editable: {
          source_context: sourceFragments.context,
          source_clip: sourceFragments.byId.get(clip.id),
          projection: {
            number: clip.number ?? null,
            label: clip.label,
            duration: clip.duration ?? null,
            scene: clip.scene ?? '',
            rhythm: clip.rhythm ?? '',
            template: clip.template ?? '',
            prompt: clip.prompt ?? '',
          },
        },
        runtime_inputs: runtimeByClip.get(clip.id) || [],
        image_runtime_inputs: imageRuntimeByClip.get(clip.id) || [],
        ready: Boolean(clip.id.trim() && (clip.label.trim() || clip.prompt?.trim())),
        asset_ids: boundAssets.length ? [...new Set(boundAssets)] : undefined,
        generation_config_keys: Object.keys(configs).filter((key) => {
          return key === `image:${clip.id}` || key.startsWith(`image:${clip.id}:`) ||
            key === `video:${clip.id}` || key.startsWith(`video:${clip.id}:`)
        }),
      }
    }),
    assets,
    delivery_spec: {
      line,
      aspect_ratio: canvas.generation_profile?.default_aspect_ratio ?? 'project',
      resolution: canvas.generation_profile?.default_resolution ?? 'project',
      image_model: canvas.generation_profile?.default_image_model ?? '',
      video_model: canvas.generation_profile?.default_video_model ?? '',
      audio_policy: canvas.generation_profile?.audio_policy ?? 'unspecified',
      audio_requirement: finalAudioRequirement(canvas.generation_profile?.audio_policy ?? ''),
      expected_duration_seconds: expectedDurationSeconds(canvas),
    },
    generation_configs: configs,
  }
}

function selectedNodeOutput(line: LineKey, clip: CanvasData['clips'][number]): string | null {
  if (line === 'comic') {
    return (clip.frames || []).find((frame) => {
      return frame.exists && frame.abs && !isReferenceFrameText(`${frame.role} ${frame.label} ${frame.abs}`)
    })?.abs || null
  }
  return clip.video_exists && clip.video_abs ? clip.video_abs : null
}

function receiptEntries(value: unknown): Record<string, unknown>[] {
  const raw = record(value)?.nodes
  if (Array.isArray(raw)) return raw.map(record).filter((item): item is Record<string, unknown> => item !== null)
  const nodes = record(raw)
  if (!nodes) return []
  return Object.entries(nodes).flatMap(([nodeId, item]) => {
    const entry = record(item)
    return entry ? [{ node_id: nodeId, ...entry }] : []
  })
}

function stringField(value: Record<string, unknown>, key: string): string {
  return typeof value[key] === 'string' ? String(value[key]).trim() : ''
}

function passVerdict(value: unknown): boolean {
  return value === 'pass' || value === 'accepted'
}

function recoverableLeaseFailure(task: CanvasProductionState['tasks'][number]): boolean {
  return task.status === 'failed' && /lease expired/.test(task.detail || '')
}

export interface CanvasQcBinding {
  kind: 'task' | 'node' | 'final'
  episode: string
  jobId: string
  contentHash: string
  inputHash?: string
  taskInputHash?: string
  inputsSha256?: string
  nodeId?: string
  targetSlot?: string
  targetOutputPath?: string
  artifactFile: string
  artifactSha256: string
}

async function verifyCanvasQcReceiptSnapshot(
  root: string,
  qaReceipt: string,
  expected: CanvasQcBinding,
  snapshot: CanvasMediaSnapshot,
): Promise<string | null> {
  const qaFile = await existingInside(root, qaReceipt)
  if (!qaFile) return null
  const evidence = await readJsonEvidence(qaFile).catch(() => null)
  const document = evidence?.document
  const expectedKind = expected.kind === 'final'
    ? 'anime_armory_canvas_final_qc'
    : expected.kind === 'node'
      ? 'anime_armory_canvas_node_qc'
      : 'anime_armory_canvas_task_qc'
  if (!document || document.kind !== expectedKind || document.version !== 1 ||
      document.episode !== expected.episode || stringField(document, 'job_id') !== expected.jobId ||
      stringField(document, 'content_hash') !== expected.contentHash || Number(document.qa_blocks) !== 0 ||
      !passVerdict(document.verdict) || document.probe_passed !== true) return null
  if (expected.nodeId && stringField(document, 'node_id') !== expected.nodeId) return null
  if (expected.inputHash && stringField(document, 'input_hash') !== expected.inputHash) return null
  if (expected.taskInputHash && stringField(document, 'task_input_hash') !== expected.taskInputHash) return null
  if (expected.targetSlot && stringField(document, 'target_slot') !== expected.targetSlot) return null
  if (expected.targetOutputPath && stringField(document, 'target_output_path') !== expected.targetOutputPath) return null
  if (expected.inputsSha256 && stringField(document, 'inputs_sha256') !== expected.inputsSha256) return null
  const shaField = expected.kind === 'final' ? 'artifact_sha256' : 'output_sha256'
  const pathField = expected.kind === 'final' ? 'artifact_path' : 'output_path'
  if (stringField(document, shaField).toLowerCase() !== expected.artifactSha256 ||
      snapshot.sha256 !== expected.artifactSha256 || !basicMediaValid(snapshot)) return null
  const boundArtifact = await existingInside(root, stringField(document, pathField))
  const actualArtifact = await fs.realpath(expected.artifactFile).catch(() => '')
  const targetArtifact = expected.targetOutputPath
    ? await existingInside(root, expected.targetOutputPath)
    : actualArtifact
  if (!boundArtifact || boundArtifact !== actualArtifact || targetArtifact !== actualArtifact ||
      snapshot.file !== actualArtifact || !await mediaSnapshotStillCurrent(snapshot)) return null
  return evidence?.sha256 ?? null
}

export async function verifyCanvasQcReceipt(root: string, qaReceipt: string, expected: CanvasQcBinding): Promise<string | null> {
  const snapshot = await mediaSnapshot(expected.artifactFile).catch(() => null)
  if (!snapshot) return null
  return verifyCanvasQcReceiptSnapshot(root, qaReceipt, expected, snapshot)
}

function taskReceiptEntries(value: unknown): Record<string, unknown>[] {
  const raw = record(value)?.jobs
  if (Array.isArray(raw)) return raw.map(record).filter((item): item is Record<string, unknown> => item !== null)
  const jobs = record(raw)
  if (!jobs) return []
  return Object.entries(jobs).flatMap(([jobId, item]) => {
    const entry = record(item)
    return entry ? [{ job_id: jobId, ...entry }] : []
  })
}

async function directReceiptEntries(
  root: string,
  filenamePrefix: 'canvas_task_receipt_' | 'canvas_node_receipt_',
  expectedKind: 'anime_armory_canvas_task_receipt' | 'anime_armory_canvas_node_receipt',
  episode: string,
): Promise<Record<string, unknown>[]> {
  const dir = path.join(root, '生产数据')
  const names = await fs.readdir(dir).catch((error: NodeJS.ErrnoException) => {
    if (error.code === 'ENOENT') return []
    throw error
  })
  const files = names.filter((name) => name.startsWith(filenamePrefix) && name.endsWith('.json')).sort()
  const documents = await Promise.all(files.map(async (name) => {
    const file = await existingInside(root, path.join('生产数据', name))
    return file ? record(await readJson(file)) : null
  }))
  return documents.filter((document): document is Record<string, unknown> => {
    return document !== null && document.kind === expectedKind && document.version === 1 &&
      document.episode === episode
  })
}

async function generationTaskReceiptEntries(root: string, episode: string): Promise<Record<string, unknown>[]> {
  const aggregate = record(await readJson(path.join(root, '生产数据', `canvas_task_receipts_${episode}.json`)))
  const legacy = aggregate?.kind === 'anime_armory_canvas_task_receipts' && aggregate.version === 1 &&
      aggregate.episode === episode
    ? taskReceiptEntries(aggregate)
    : []
  // Direct receipts are immutable, job-scoped writes and therefore win over a
  // conflicting legacy aggregate without requiring a concurrent RMW update.
  const direct = await directReceiptEntries(root, 'canvas_task_receipt_', 'anime_armory_canvas_task_receipt', episode)
  return [
    ...direct.map((entry) => ({
      ...entry,
      receipt_kind: entry.kind,
      kind: stringField(entry, 'generation_kind') || stringField(entry, 'task_kind'),
    })),
    ...legacy,
  ]
}

async function nodeAcceptanceReceiptEntries(root: string, episode: string): Promise<Record<string, unknown>[]> {
  const aggregate = record(await readJson(path.join(root, '生产数据', `canvas_node_receipts_${episode}.json`)))
  const legacy = aggregate?.kind === 'anime_armory_canvas_node_receipts' && aggregate.version === 1 &&
      aggregate.episode === episode
    ? receiptEntries(aggregate)
    : []
  // A production job may emit one file per node:
  // canvas_node_receipt_<job>_<safe-node-token>.json.  The body remains the
  // authority for job_id/node_id; filenames are only discovery hints.
  return [
    ...await directReceiptEntries(root, 'canvas_node_receipt_', 'anime_armory_canvas_node_receipt', episode),
    ...legacy,
  ]
}

type CandidateReceiptScope = 'task' | 'node' | 'final'

function expectedCandidatePath(targetPath: string, jobId: string): string | null {
  try {
    return targetPath && jobId ? canvasCandidateTargetRel(targetPath, jobId) : null
  } catch {
    return null
  }
}

interface CandidateReceiptDocument {
  scope: CandidateReceiptScope
  file: string
  sha256: string
  document: Record<string, unknown>
}

async function candidateReceiptDocuments(root: string, episode: string): Promise<CandidateReceiptDocument[]> {
  const dir = path.join(root, '生产数据')
  const names = await fs.readdir(dir).catch((error: NodeJS.ErrnoException) => {
    if (error.code === 'ENOENT') return []
    throw error
  })
  const candidates = names.filter((name) => {
    return name.endsWith('.json') && (
      name.startsWith('canvas_task_candidate_receipt_') ||
      name.startsWith('canvas_node_candidate_receipt_') ||
      name.startsWith('canvas_final_candidate_receipt_')
    )
  }).sort()
  const documents = await Promise.all(candidates.map(async (name): Promise<CandidateReceiptDocument | null> => {
    const file = await existingInside(root, path.join('生产数据', name))
    if (!file) return null
    const evidence = await readJsonEvidence(file).catch(() => null)
    const document = evidence?.document
    if (!document || document.version !== 1 || document.episode !== episode) return null
    const scope: CandidateReceiptScope | null = document.kind === 'anime_armory_canvas_task_candidate_receipt'
      ? 'task'
      : document.kind === 'anime_armory_canvas_node_candidate_receipt'
        ? 'node'
        : document.kind === 'anime_armory_canvas_final_candidate_receipt'
          ? 'final'
          : null
    return scope && evidence ? { scope, file, sha256: evidence.sha256, document } : null
  }))
  return documents.filter((item): item is CandidateReceiptDocument => item !== null)
}

interface CandidateQcExpected {
  scope: CandidateReceiptScope
  episode: string
  jobId: string
  contentHash: string
  candidatePath: string
  targetPath: string
  candidateSha256: string
  nodeId?: string
  generationKind?: CanvasGenerationKind
  inputHash?: string
  nodeInputHash?: string
  taskInputHash?: string
  targetSlot?: string
  inputsSha256?: string
}

interface HumanCandidateAcceptance {
  file: string
  sha256: string
  reviewer: string
  accepted_at: string
}

async function verifyCandidateQc(
  root: string,
  candidateReceipt: Record<string, unknown>,
  expected: CandidateQcExpected,
  snapshot: CanvasMediaSnapshot,
): Promise<{ file: string; sha256: string } | null> {
  const qaFile = await existingInside(root, stringField(candidateReceipt, 'qa_receipt_path'))
  if (!qaFile) return null
  const evidence = await readJsonEvidence(qaFile).catch(() => null)
  const qa = evidence?.document
  const kind = expected.scope === 'final'
    ? 'anime_armory_canvas_final_candidate_qc'
    : expected.scope === 'node'
      ? 'anime_armory_canvas_node_candidate_qc'
      : 'anime_armory_canvas_task_candidate_qc'
  if (!qa || !evidence || qa.kind !== kind || qa.version !== 1 || qa.episode !== expected.episode ||
      stringField(qa, 'job_id') !== expected.jobId ||
      stringField(qa, 'content_hash') !== expected.contentHash ||
      stringField(qa, 'candidate_output_path') !== expected.candidatePath ||
      stringField(qa, 'target_output_path') !== expected.targetPath ||
      stringField(qa, 'candidate_sha256').toLowerCase() !== expected.candidateSha256 ||
      stringField(candidateReceipt, 'qa_receipt_sha256').toLowerCase() !== evidence.sha256 ||
      Number(qa.qa_blocks) !== 0 || !passVerdict(qa.verdict) || qa.probe_passed !== true ||
      snapshot.sha256 !== expected.candidateSha256 || !basicMediaValid(snapshot) ||
      !await mediaSnapshotStillCurrent(snapshot)) return null
  if (expected.nodeId && (stringField(qa, 'node_id') !== expected.nodeId ||
      stringField(candidateReceipt, 'node_id') !== expected.nodeId)) return null
  if (expected.generationKind && (stringField(qa, 'generation_kind') !== expected.generationKind ||
      stringField(candidateReceipt, 'generation_kind') !== expected.generationKind)) return null
  if (expected.inputHash && (stringField(qa, 'input_hash') !== expected.inputHash ||
      stringField(candidateReceipt, 'input_hash') !== expected.inputHash)) return null
  if (expected.nodeInputHash && (stringField(qa, 'node_input_hash') !== expected.nodeInputHash ||
      stringField(candidateReceipt, 'node_input_hash') !== expected.nodeInputHash)) return null
  if (expected.taskInputHash && (stringField(qa, 'task_input_hash') !== expected.taskInputHash ||
      stringField(candidateReceipt, 'task_input_hash') !== expected.taskInputHash)) return null
  if (expected.targetSlot && (stringField(qa, 'target_slot') !== expected.targetSlot ||
      stringField(candidateReceipt, 'target_slot') !== expected.targetSlot)) return null
  if (expected.inputsSha256 && (stringField(qa, 'inputs_sha256') !== expected.inputsSha256 ||
      stringField(candidateReceipt, 'inputs_sha256') !== expected.inputsSha256)) return null
  return { file: qaFile, sha256: evidence.sha256 }
}

async function verifyHumanCandidateAcceptance(
  root: string,
  candidateReceipt: Record<string, unknown>,
  expected: CandidateQcExpected,
): Promise<HumanCandidateAcceptance | null> {
  const acceptanceFile = await existingInside(root, stringField(candidateReceipt, 'human_acceptance_path'))
  if (!acceptanceFile) return null
  const evidence = await readJsonEvidence(acceptanceFile).catch(() => null)
  const document = evidence?.document
  const confirmation = record(document?.confirmation)
  const reviewer = document ? stringField(document, 'reviewer') : ''
  const acceptedAt = document ? stringField(document, 'accepted_at') : ''
  if (!document || !evidence ||
      document.kind !== 'anime_armory_canvas_candidate_human_acceptance' || document.version !== 1 ||
      document.episode !== expected.episode || stringField(document, 'job_id') !== expected.jobId ||
      stringField(document, 'node_id') !== expected.nodeId ||
      stringField(document, 'generation_kind') !== expected.generationKind ||
      stringField(document, 'target_slot') !== expected.targetSlot ||
      stringField(document, 'target_output_path') !== expected.targetPath ||
      stringField(document, 'candidate_output_path') !== expected.candidatePath ||
      stringField(document, 'candidate_sha256').toLowerCase() !== expected.candidateSha256 ||
      stringField(document, 'content_hash') !== expected.contentHash ||
      (expected.inputHash && stringField(document, 'input_hash') !== expected.inputHash) ||
      (expected.nodeInputHash && stringField(document, 'node_input_hash') !== expected.nodeInputHash) ||
      (expected.taskInputHash && stringField(document, 'task_input_hash') !== expected.taskInputHash) ||
      stringField(candidateReceipt, 'human_acceptance_sha256').toLowerCase() !== evidence.sha256 ||
      !reviewer || /(?:agent|assistant|automation|automated|auto|bot|delegated|machine|模型|自动)/i.test(reviewer) ||
      !/(?:Z|[+-]\d{2}:\d{2})$/.test(acceptedAt) || !Number.isFinite(Date.parse(acceptedAt)) ||
      confirmation?.kind !== 'explicit_current_pixels_acceptance' ||
      confirmation.accepted_current_pixels !== true) return null
  return { file: acceptanceFile, sha256: evidence.sha256, reviewer, accepted_at: acceptedAt }
}

async function atomicallyPromoteCandidate(
  root: string,
  candidatePath: string,
  targetPath: string,
  snapshot: CanvasMediaSnapshot,
): Promise<CanvasMediaSnapshot> {
  const canonicalRoot = await fs.realpath(root)
  const candidateLexical = path.resolve(canonicalRoot, candidatePath)
  const candidateRel = path.relative(canonicalRoot, candidateLexical)
  if (!candidateRel || candidateRel.startsWith('../') || path.isAbsolute(candidateRel)) {
    throw new Error('candidate_promotion_candidate_outside_root')
  }
  const candidateFile = await existingInside(canonicalRoot, candidatePath)
  const targetFile = path.resolve(canonicalRoot, targetPath)
  const targetRel = path.relative(canonicalRoot, targetFile)
  if (!targetRel || targetRel.startsWith('../') || path.isAbsolute(targetRel)) {
    throw new Error('candidate_promotion_target_outside_root')
  }
  await fs.mkdir(path.dirname(targetFile), { recursive: true })
  const targetParent = await fs.realpath(path.dirname(targetFile))
  const parentRel = path.relative(canonicalRoot, targetParent)
  if (parentRel.startsWith('../') || path.isAbsolute(parentRel)) {
    throw new Error('candidate_promotion_target_parent_outside_root')
  }
  if (!await mediaSnapshotStillCurrent(snapshot)) throw new Error('candidate_promotion_candidate_changed')
  // Crash recovery: rename may have completed immediately before Electron
  // persisted its authoritative receipts. If the immutable candidate/QC
  // evidence still binds the exact bytes now at stable target, the operation
  // is idempotently resumed by writing those receipts below.
  if (!candidateFile) {
    const stableFile = await existingInside(canonicalRoot, targetPath)
    const stableLstat = await fs.lstat(targetFile).catch(() => null)
    if (!stableFile || stableFile !== snapshot.file || stableFile !== targetFile || !stableLstat?.isFile() ||
        stableLstat.isSymbolicLink() || stableLstat.nlink !== 1) {
      throw new Error('candidate_promotion_candidate_missing')
    }
    return snapshot
  }
  const candidateLstat = await fs.lstat(candidateLexical).catch(() => null)
  if (candidateFile !== snapshot.file || candidateFile !== candidateLexical || !candidateLstat?.isFile() ||
      candidateLstat.isSymbolicLink() || candidateLstat.nlink !== 1) {
    throw new Error('candidate_promotion_candidate_changed')
  }
  const [candidateStat, parentStat] = await Promise.all([fs.stat(candidateLexical), fs.stat(targetParent)])
  if (candidateStat.dev !== parentStat.dev) throw new Error('candidate_promotion_cross_device')
  await fs.rename(candidateLexical, targetFile)
  const promoted = await mediaSnapshot(targetFile)
  if (promoted.sha256 !== snapshot.sha256 || !basicMediaValid(promoted)) {
    throw new Error('candidate_promotion_post_rename_mismatch')
  }
  return promoted
}

async function writePromotedTaskEvidence(
  root: string,
  state: CanvasProductionState,
  task: CanvasProductionState['tasks'][number],
  candidateReceipt: CandidateReceiptDocument,
  candidateQc: { file: string; sha256: string },
  humanAcceptance: HumanCandidateAcceptance | null,
  promoted: CanvasMediaSnapshot,
): Promise<void> {
  const qaPath = path.join(root, '生产数据', `canvas_task_qc_${task.job_id}_promoted.json`)
  const stablePath = task.target_output_path || ''
  const common = {
    version: 1,
    episode: state.episode,
    job_id: task.job_id,
    node_id: task.node_id,
    generation_kind: task.kind,
    target_slot: task.target_slot,
    target_output_path: stablePath,
    candidate_output_path: task.candidate_output_path,
    content_hash: task.content_hash,
    input_hash: task.input_hash,
    node_input_hash: state.node_fingerprints[task.node_id]?.input_hash,
    output_path: stablePath,
    output_sha256: promoted.sha256,
    candidate_sha256: promoted.sha256,
    candidate_receipt_path: relativeInside(root, candidateReceipt.file) || candidateReceipt.file,
    candidate_receipt_sha256: candidateReceipt.sha256,
    candidate_qa_receipt_path: relativeInside(root, candidateQc.file) || candidateQc.file,
    candidate_qa_receipt_sha256: candidateQc.sha256,
    human_acceptance_path: humanAcceptance
      ? relativeInside(root, humanAcceptance.file) || humanAcceptance.file
      : undefined,
    human_acceptance_sha256: humanAcceptance?.sha256,
    qa_blocks: 0,
    probe_passed: true,
    verdict: 'pass',
    promotion_authority: 'desktop_main_v1',
  }
  await atomicReceipt(qaPath, { kind: 'anime_armory_canvas_task_qc', ...common })
  const qaSha = await stableFileSha256(qaPath)
  const authored = state.authoring.clips.find((clip) => clip.id === task.node_id)
  if (humanAcceptance && authored && task.kind === state.authoring.final_stage && task.target_slot === authored.final_target.slot &&
      stablePath === authored.final_target.output_path) {
    const nodeQaPath = path.join(root, '生产数据', `canvas_node_qc_${task.job_id}_${stableCanvasSlotToken(task.node_id)}_promoted.json`)
    const nodeCommon = {
      ...common,
      kind: 'anime_armory_canvas_node_qc',
      input_hash: state.node_fingerprints[task.node_id].input_hash,
      task_input_hash: task.input_hash,
      reviewer_kind: 'human',
      reviewer: humanAcceptance.reviewer,
      confirmation: { kind: 'explicit_current_pixels_acceptance', accepted_current_pixels: true },
      verdict: 'accepted',
    }
    await atomicReceipt(nodeQaPath, nodeCommon)
    const nodeQaSha = await stableFileSha256(nodeQaPath)
    await atomicReceipt(path.join(root, '生产数据', `canvas_node_receipt_${task.job_id}_${stableCanvasSlotToken(task.node_id)}.json`), {
      ...nodeCommon,
      kind: 'anime_armory_canvas_node_receipt',
      qa_receipt_path: relativeInside(root, nodeQaPath) || nodeQaPath,
      qa_receipt_sha256: nodeQaSha,
      accepted_at: humanAcceptance.accepted_at,
    })
  }
  // Task settlement is the commit marker. For a final-slot generation it is
  // deliberately written after node evidence, so a partial receipt write can
  // always be resumed while the task is still active.
  await atomicReceipt(path.join(root, '生产数据', `canvas_task_receipt_${task.job_id}.json`), {
    kind: 'anime_armory_canvas_task_receipt',
    ...common,
    qa_receipt_path: relativeInside(root, qaPath) || qaPath,
    qa_receipt_sha256: qaSha,
    accepted_at: new Date().toISOString(),
  })
}

async function writePromotedProductionNodeEvidence(
  root: string,
  state: CanvasProductionState,
  task: CanvasProductionState['tasks'][number],
  nodeId: string,
  targetSlot: string,
  targetPath: string,
  candidatePath: string,
  candidateReceipt: CandidateReceiptDocument,
  candidateQc: { file: string; sha256: string },
  humanAcceptance: HumanCandidateAcceptance | null,
  promoted: CanvasMediaSnapshot,
): Promise<void> {
  const safeNode = stableCanvasSlotToken(nodeId)
  const qaPath = path.join(root, '生产数据', `canvas_node_qc_${task.job_id}_${safeNode}_promoted.json`)
  const common = {
    version: 1,
    episode: state.episode,
    job_id: task.job_id,
    node_id: nodeId,
    generation_kind: state.authoring.final_stage,
    target_slot: targetSlot,
    target_output_path: targetPath,
    candidate_output_path: candidatePath,
    content_hash: task.content_hash,
    input_hash: state.node_fingerprints[nodeId].input_hash,
    task_input_hash: task.input_hash,
    output_path: targetPath,
    output_sha256: promoted.sha256,
    candidate_sha256: promoted.sha256,
    candidate_receipt_path: relativeInside(root, candidateReceipt.file) || candidateReceipt.file,
    candidate_receipt_sha256: candidateReceipt.sha256,
    candidate_qa_receipt_path: relativeInside(root, candidateQc.file) || candidateQc.file,
    candidate_qa_receipt_sha256: candidateQc.sha256,
    qa_blocks: 0,
    probe_passed: true,
    reviewer_kind: humanAcceptance ? 'human' : 'machine',
    reviewer: humanAcceptance?.reviewer,
    confirmation: humanAcceptance
      ? { kind: 'explicit_current_pixels_acceptance', accepted_current_pixels: true }
      : undefined,
    human_acceptance_path: humanAcceptance
      ? relativeInside(root, humanAcceptance.file) || humanAcceptance.file
      : undefined,
    human_acceptance_sha256: humanAcceptance?.sha256,
    verdict: humanAcceptance ? 'accepted' : 'machine_complete',
    promotion_authority: 'desktop_main_v1',
  }
  await atomicReceipt(qaPath, {
    kind: humanAcceptance ? 'anime_armory_canvas_node_qc' : 'anime_armory_canvas_node_machine_qc',
    ...common,
  })
  const qaSha = await stableFileSha256(qaPath)
  const receiptPrefix = humanAcceptance ? 'canvas_node_receipt' : 'canvas_node_machine_receipt'
  await atomicReceipt(path.join(root, '生产数据', `${receiptPrefix}_${task.job_id}_${safeNode}.json`), {
    kind: humanAcceptance
      ? 'anime_armory_canvas_node_receipt'
      : 'anime_armory_canvas_node_machine_receipt',
    ...common,
    qa_receipt_path: relativeInside(root, qaPath) || qaPath,
    qa_receipt_sha256: qaSha,
    accepted_at: humanAcceptance?.accepted_at,
  })
}

async function promoteNodeCandidates(
  root: string,
  line: LineKey,
  canvas: CanvasData,
  state: CanvasProductionState | null,
  receipts: CandidateReceiptDocument[],
): Promise<void> {
  if (!state) return
  for (const candidateReceipt of receipts.filter((item) => item.scope === 'task' || item.scope === 'node')) {
    const raw = candidateReceipt.document
    const jobId = stringField(raw, 'job_id')
    const task = state.tasks.find((item) => item.job_id === jobId)
    if (!task || task.promotion_required !== true ||
        (task.status !== 'submitted' && task.status !== 'running')) continue
    const nodeId = stringField(raw, 'node_id')
    const node = state.node_fingerprints[nodeId]
    const authored = state.authoring.clips.find((clip) => clip.id === nodeId)
    const generationKind = stringField(raw, 'generation_kind') as CanvasGenerationKind
    const targetSlot = stringField(raw, 'target_slot')
    const targetPath = stringField(raw, 'target_output_path')
    const candidatePath = stringField(raw, 'candidate_output_path')
    const candidateSha = stringField(raw, 'candidate_sha256').toLowerCase()
    const expectedPath = expectedCandidatePath(targetPath, task.job_id)
    if (!node || !authored || (generationKind !== 'image' && generationKind !== 'video') ||
        stringField(raw, 'content_hash') !== task.content_hash ||
        !expectedPath || candidatePath !== expectedPath || Number(raw.qa_blocks) !== 0 ||
        !passVerdict(raw.verdict) || raw.probe_passed !== true) continue
    const isSingle = candidateReceipt.scope === 'task'
    if (isSingle) {
      if (task.node_id !== nodeId || task.kind !== generationKind || task.target_slot !== targetSlot ||
          task.target_output_path !== targetPath || task.candidate_output_path !== candidatePath ||
          stringField(raw, 'input_hash') !== task.input_hash ||
          stringField(raw, 'node_input_hash') !== node.input_hash) continue
    } else if (task.node_id !== CANVAS_EPISODE_TASK_NODE_ID || task.kind !== 'production' ||
        generationKind !== state.authoring.final_stage || targetSlot !== authored.final_target.slot ||
        targetPath !== authored.final_target.output_path || stringField(raw, 'input_hash') !== node.input_hash ||
        stringField(raw, 'task_input_hash') !== task.input_hash) continue
    const candidateFile = await existingInside(root, candidatePath)
    const recoveryFile = candidateFile || await existingInside(root, targetPath)
    if (!recoveryFile) continue
    const snapshot = await mediaSnapshot(recoveryFile).catch(() => null)
    if (!snapshot || snapshot.sha256 !== candidateSha || !basicMediaValid(snapshot)) continue
    const expected: CandidateQcExpected = {
      scope: candidateReceipt.scope,
      episode: state.episode,
      jobId,
      contentHash: task.content_hash,
      candidatePath,
      targetPath,
      candidateSha256: candidateSha,
      nodeId,
      generationKind,
      inputHash: isSingle ? task.input_hash : node.input_hash,
      nodeInputHash: isSingle ? node.input_hash : undefined,
      taskInputHash: isSingle ? undefined : task.input_hash,
      targetSlot,
    }
    const qc = await verifyCandidateQc(root, raw, expected, snapshot)
    if (!qc) continue
    const humanAcceptance = await verifyHumanCandidateAcceptance(root, raw, expected)
    // B14: every generated image needs explicit acceptance of these exact
    // current pixels before the stable target can change. Video may reach a
    // machine-complete stable artifact, but remains unaccepted without the
    // same human evidence (or a later line-owned human node receipt).
    if (generationKind === 'image' && !humanAcceptance) continue
    await withCurrentCanvasCandidatePromotion(root, {
      episode: state.episode,
      job_id: jobId,
      scope: 'node',
      content_hash: task.content_hash,
      task_input_hash: task.input_hash,
      target_output_path: targetPath,
      candidate_output_path: candidatePath,
      node_id: nodeId,
      node_input_hash: node.input_hash,
      generation_kind: generationKind,
      target_slot: targetSlot,
    }, async (lockedState, lockedTask) => {
      const currentReceipt = await readJsonEvidence(candidateReceipt.file).catch(() => null)
      const currentQc = await readJsonEvidence(qc.file).catch(() => null)
      const currentHuman = humanAcceptance
        ? await readJsonEvidence(humanAcceptance.file).catch(() => null)
        : null
      if (currentReceipt?.sha256 !== candidateReceipt.sha256 || currentQc?.sha256 !== qc.sha256 ||
          (humanAcceptance && currentHuman?.sha256 !== humanAcceptance.sha256) ||
          !await mediaSnapshotStillCurrent(snapshot)) throw new Error('candidate_promotion_evidence_changed')
      const freshAuthoring = await buildCanvasAuthoringInput(root, line, canvas)
      const freshNodes = freshAuthoring ? computeCanvasNodeFingerprints(freshAuthoring) : {}
      const freshTaskInput = freshAuthoring && lockedTask.node_id !== CANVAS_EPISODE_TASK_NODE_ID
        ? computeCanvasTargetFingerprint(
            freshAuthoring,
            lockedTask.node_id,
            generationKind,
            lockedTask.target_slot || generationKind,
            lockedTask.target_output_path || '',
          )
        : freshAuthoring ? computeCanvasContentHash(freshAuthoring) : ''
      if (!freshAuthoring || computeCanvasContentHash(freshAuthoring) !== lockedState.content_hash ||
          freshNodes[nodeId] !== lockedState.node_fingerprints[nodeId]?.input_hash ||
          freshTaskInput !== lockedTask.input_hash) {
        throw new Error('candidate_promotion_filesystem_inputs_stale')
      }
      const promoted = await atomicallyPromoteCandidate(root, candidatePath, targetPath, snapshot)
      if (isSingle) {
        await writePromotedTaskEvidence(
          root, lockedState, lockedTask, candidateReceipt, qc, humanAcceptance, promoted,
        )
      } else {
        await writePromotedProductionNodeEvidence(
          root, lockedState, lockedTask, nodeId, targetSlot, targetPath, candidatePath,
          candidateReceipt, qc, humanAcceptance, promoted,
        )
      }
    }).catch(() => undefined)
  }
}

async function settleVerifiedGenerationTasks(
  root: string,
  state: CanvasProductionState,
): Promise<CanvasProductionState> {
  const receipts = await generationTaskReceiptEntries(root, state.episode)
  if (!receipts.length) return state
  let current = state
  for (const task of state.tasks) {
    if ((task.kind !== 'image' && task.kind !== 'video') ||
        (task.status !== 'submitted' && task.status !== 'running' && !recoverableLeaseFailure(task))) continue
    let settled = false
    for (const raw of receipts.filter((entry) => stringField(entry, 'job_id') === task.job_id)) {
      if (stringField(raw, 'node_id') !== task.node_id || stringField(raw, 'kind') !== task.kind ||
          stringField(raw, 'target_slot') !== (task.target_slot || '') ||
          stringField(raw, 'target_output_path') !== (task.target_output_path || '') ||
          stringField(raw, 'content_hash') !== task.content_hash || stringField(raw, 'input_hash') !== task.input_hash ||
          Number(raw.qa_blocks) !== 0 || !passVerdict(raw.verdict) || raw.probe_passed !== true ||
          (task.promotion_required === true && raw.promotion_authority !== 'desktop_main_v1')) continue
      const output = await existingInside(root, stringField(raw, 'output_path'))
      const qaReceipt = await existingInside(root, stringField(raw, 'qa_receipt_path'))
      if (!output || !qaReceipt) continue
      const snapshot = await mediaSnapshot(output).catch(() => null)
      if (!snapshot || !basicMediaValid(snapshot) ||
          stringField(raw, 'output_sha256').toLowerCase() !== snapshot.sha256) continue
      const qaSha = await verifyCanvasQcReceiptSnapshot(root, qaReceipt, {
        kind: 'task',
        episode: state.episode,
        jobId: task.job_id,
        contentHash: task.content_hash,
        inputHash: task.input_hash,
        nodeId: task.node_id,
        targetSlot: task.target_slot,
        targetOutputPath: task.target_output_path,
        artifactFile: output,
        artifactSha256: snapshot.sha256,
      }, snapshot)
      if (!qaSha || stringField(raw, 'qa_receipt_sha256').toLowerCase() !== qaSha) continue
      settled = true
      break
    }
    if (!settled) continue
    current = await updateCanvasTaskStatus(root, {
      episode: current.episode,
      job_id: task.job_id,
      status: 'succeeded',
      detail: `${task.kind} 输出字节、媒体 probe 与 QC receipt 已验收`,
    })
  }
  return current
}

export async function verifiedNodeAcceptances(
  root: string,
  line: LineKey,
  canvas: CanvasData,
  authoring: CanvasAuthoringInput,
  previous: CanvasProductionState | null,
  diagnostics?: string[],
): Promise<Record<string, CanvasNodeAcceptanceEvidence>> {
  if (!previous) {
    diagnostics?.push('state:missing_previous_state')
    return {}
  }
  const receipts = await nodeAcceptanceReceiptEntries(root, canvas.episode)
  if (!receipts.length) {
    diagnostics?.push('receipt:invalid_document_envelope')
    return {}
  }
  const inputHashes = computeCanvasNodeFingerprints(authoring)
  const authoredClips = new Map(authoring.clips.map((clip) => [clip.id, clip]))
  const clips = new Map(canvas.clips.map((clip) => [clip.id, clip]))
  const out: Record<string, CanvasNodeAcceptanceEvidence> = {}

  for (const raw of receipts) {
    const nodeId = stringField(raw, 'node_id')
    if (out[nodeId]) continue
    const clip = clips.get(nodeId)
    const output = clip ? selectedNodeOutput(line, clip) : null
    const target = authoredClips.get(nodeId)?.final_target
    const outputFile = output ? await existingInside(root, output) : null
    const receiptOutput = await existingInside(root, stringField(raw, 'output_path'))
    const qaReceipt = await existingInside(root, stringField(raw, 'qa_receipt_path'))
    if (!clip || !target || !outputFile || !receiptOutput || outputFile !== receiptOutput || !qaReceipt ||
        stringField(raw, 'target_slot') !== target.slot ||
        stringField(raw, 'target_output_path') !== target.output_path) {
      diagnostics?.push(`${nodeId || 'unknown'}:output_or_qa_path_mismatch`)
      continue
    }
    const reviewerKind = raw.reviewer_kind === 'human'
      ? 'human'
      : raw.reviewer_kind === 'delegated' ? 'delegated' : null
    const jobId = stringField(raw, 'job_id')
    const acceptedAt = stringField(raw, 'accepted_at')
    const receiptContentHash = stringField(raw, 'content_hash')
    const matchingTasks = previous.tasks.filter((task) => {
      const targetMatches = task.node_id === CANVAS_EPISODE_TASK_NODE_ID ||
        (task.node_id === nodeId && task.kind === authoring.final_stage &&
          task.target_slot === target.slot && task.target_output_path === target.output_path)
      return targetMatches
    }).sort((a, b) => b.submitted_at.localeCompare(a.submitted_at))
    const receiptTask = matchingTasks.find((task) => task.job_id === jobId)
    const eligibleTasks = matchingTasks.filter((task) => {
      return !['failed', 'cancelled', 'stale'].includes(task.status) || recoverableLeaseFailure(task)
    })
    const priorAcceptance = previous.node_fingerprints[nodeId]?.acceptance
    const carriesAcceptedOutput = priorAcceptance?.job_id === jobId &&
      priorAcceptance.input_hash === inputHashes[nodeId]
    // A production executor can fail after it has durably committed and the
    // state has accepted some node receipts. Preserve only that already-recorded
    // evidence; a failed job is never allowed to introduce a new acceptance.
    // The prior evidence is compared byte-for-byte again after media/QC checks.
    const carriesFailedProductionOutput = Boolean(
      carriesAcceptedOutput && receiptTask?.node_id === CANVAS_EPISODE_TASK_NODE_ID &&
      receiptTask.kind === 'production' && receiptTask.status === 'failed',
    )
    const carriesStaleOutput = Boolean(carriesAcceptedOutput && receiptTask?.status === 'stale')
    const carriesEligibleOutput = Boolean(
      carriesAcceptedOutput && eligibleTasks.some((task) => task.job_id === jobId),
    )
    const mayUseReceipt = carriesFailedProductionOutput || carriesStaleOutput || carriesEligibleOutput ||
      (!carriesAcceptedOutput && eligibleTasks[0]?.job_id === jobId)
    if (!jobId || !acceptedAt || !receiptTask ||
        !mayUseReceipt ||
        receiptContentHash !== receiptTask.content_hash || !reviewerKind ||
        raw.verdict !== 'accepted' || Number(raw.qa_blocks) !== 0 || raw.probe_passed !== true ||
        (receiptTask.promotion_required === true &&
          (raw.promotion_authority !== 'desktop_main_v1' || reviewerKind !== 'human'))) {
      diagnostics?.push(`${nodeId}:task_or_acceptance_binding_mismatch`)
      continue
    }
    const snapshot = await mediaSnapshot(outputFile).catch(() => null)
    const outputSha = snapshot?.sha256 || ''
    if (stringField(raw, 'input_hash') !== inputHashes[nodeId] ||
        stringField(raw, 'task_input_hash') !== receiptTask.input_hash ||
        !snapshot || !basicMediaValid(snapshot) || stringField(raw, 'output_sha256').toLowerCase() !== outputSha) {
      diagnostics?.push(`${nodeId}:input_or_output_hash_mismatch`)
      continue
    }
    if (receiptTask.promotion_required === true) {
      const candidatePath = expectedCandidatePath(target.output_path, receiptTask.job_id)
      const human = candidatePath ? await verifyHumanCandidateAcceptance(root, raw, {
        scope: receiptTask.node_id === CANVAS_EPISODE_TASK_NODE_ID ? 'node' : 'task',
        episode: canvas.episode,
        jobId,
        contentHash: receiptContentHash,
        candidatePath,
        targetPath: target.output_path,
        candidateSha256: outputSha,
        nodeId,
        generationKind: authoring.final_stage,
        inputHash: receiptTask.node_id === CANVAS_EPISODE_TASK_NODE_ID
          ? inputHashes[nodeId]
          : receiptTask.input_hash,
        nodeInputHash: receiptTask.node_id === CANVAS_EPISODE_TASK_NODE_ID
          ? undefined
          : inputHashes[nodeId],
        taskInputHash: receiptTask.node_id === CANVAS_EPISODE_TASK_NODE_ID
          ? receiptTask.input_hash
          : undefined,
        targetSlot: target.slot,
      }) : null
      if (!human) {
        diagnostics?.push(`${nodeId}:human_current_pixels_acceptance_missing`)
        continue
      }
    }
    const qaSha = await verifyCanvasQcReceiptSnapshot(root, qaReceipt, {
      kind: 'node',
      episode: canvas.episode,
      jobId,
      contentHash: receiptContentHash,
      inputHash: inputHashes[nodeId],
      taskInputHash: receiptTask.input_hash,
      nodeId,
      targetSlot: target.slot,
      targetOutputPath: target.output_path,
      artifactFile: outputFile,
      artifactSha256: outputSha,
    }, snapshot)
    if (!qaSha || stringField(raw, 'qa_receipt_sha256').toLowerCase() !== qaSha) {
      diagnostics?.push(`${nodeId}:qc_receipt_binding_mismatch`)
      continue
    }
    const normalizedOutputPath = relativeInside(root, outputFile) || outputFile
    const normalizedQaPath = relativeInside(root, qaReceipt) || qaReceipt
    if ((carriesFailedProductionOutput || carriesStaleOutput) && (!priorAcceptance ||
        priorAcceptance.content_hash !== receiptContentHash || priorAcceptance.output_path !== normalizedOutputPath ||
        priorAcceptance.output_sha256 !== outputSha || priorAcceptance.qa_receipt_path !== normalizedQaPath ||
        priorAcceptance.qa_receipt_sha256 !== qaSha || priorAcceptance.accepted_at !== acceptedAt ||
        priorAcceptance.reviewer_kind !== reviewerKind || priorAcceptance.verdict !== 'accepted')) {
      diagnostics?.push(`${nodeId}:failed_task_prior_acceptance_mismatch`)
      continue
    }
    out[nodeId] = {
      content_hash: receiptContentHash,
      input_hash: inputHashes[nodeId],
      output_path: normalizedOutputPath,
      output_sha256: outputSha,
      qa_receipt_path: normalizedQaPath,
      qa_receipt_sha256: qaSha,
      qa_blocks: 0,
      reviewer_kind: reviewerKind,
      verdict: 'accepted',
      job_id: jobId,
      accepted_at: acceptedAt,
    }
  }
  return out
}

async function newestFile(dir: string, accept: (name: string) => boolean): Promise<string | null> {
  let entries: string[]
  try {
    entries = await fs.readdir(dir)
  } catch {
    return null
  }
  const candidates = await Promise.all(entries.filter(accept).map(async (name) => {
    const file = path.join(dir, name)
    try {
      const stat = await fs.stat(file)
      return stat.isFile() && stat.size > 0 ? { file, mtime: stat.mtimeMs } : null
    } catch {
      return null
    }
  }))
  return candidates.filter((item): item is { file: string; mtime: number } => item !== null)
    .sort((a, b) => b.mtime - a.mtime)[0]?.file ?? null
}

async function comicFinal(root: string, episode: string): Promise<string | null> {
  const manifest = record(await readJson(path.join(root, '排版', episode, 'export_manifest.json')))
  const rendered = Array.isArray(manifest?.rendered) ? manifest.rendered : []
  // A multi-file page set is not a unique final master. Prefer an explicit
  // single export or the canonical longstrip below.
  for (const item of rendered.length === 1 ? rendered : []) {
    const rel = typeof record(item)?.path === 'string' ? String(record(item)?.path) : ''
    if (!rel) continue
    const file = await existingInside(root, rel)
    if (file) return file
  }
  return newestFile(path.join(root, '排版', episode, '长图'), (name) => /^longstrip\.(?:webp|png|jpe?g)$/i.test(name))
}

async function finalArtifactPath(root: string, line: LineKey, episode: string): Promise<string | null> {
  if (line === 'n2d') {
    return newestFile(path.join(root, '合成', episode), (name) => /^成片_.*\.(?:mp4|mov)$/i.test(name) && !/preview|rough|tmp/i.test(name))
  }
  if (line === 'comic') return comicFinal(root, episode)
  if (line === 'ad') {
    const file = path.join(root, '合成', '成片_主片.mp4')
    return existsSync(file) ? file : null
  }
  if (line === 'mv') {
    const file = path.join(root, '成片_MV.mp4')
    return existsSync(file) ? file : null
  }
  return null
}

async function legalFinalArtifact(root: string, line: LineKey, episode: string, file: string): Promise<boolean> {
  const canonicalRoot = await fs.realpath(root).catch(() => '')
  const rel = canonicalRoot ? relativeInside(canonicalRoot, file) : null
  if (!rel) return false
  const normalizedEpisode = safeEpisode(episode)
  if (line === 'n2d') {
    return path.posix.dirname(rel) === `合成/${normalizedEpisode}` &&
      /^成片_.*\.(?:mp4|mov)$/i.test(path.posix.basename(rel)) && !/preview|rough|tmp/i.test(rel)
  }
  if (line === 'ad') return rel === '合成/成片_主片.mp4'
  if (line === 'mv') return rel === '成片_MV.mp4'
  if (line !== 'comic') return false
  if (path.posix.dirname(rel) === `排版/${normalizedEpisode}/长图` &&
      /^longstrip\.(?:webp|png|jpe?g)$/i.test(path.posix.basename(rel))) return true
  const manifest = record(await readJson(path.join(root, '排版', normalizedEpisode, 'export_manifest.json')))
  const rendered = Array.isArray(manifest?.rendered) ? manifest.rendered : []
  if (rendered.length !== 1 || !rel.startsWith(`排版/${normalizedEpisode}/`)) return false
  const declared = typeof record(rendered[0])?.path === 'string' ? String(record(rendered[0])?.path) : ''
  const declaredFile = declared ? await existingInside(root, declared) : null
  return declaredFile === file
}

function concreteAspectRatio(value: unknown): number | null {
  if (typeof value !== 'string') return null
  const match = value.trim().match(/^(\d+(?:\.\d+)?)\s*[:/]\s*(\d+(?:\.\d+)?)$/)
  if (!match) return null
  const width = Number(match[1])
  const height = Number(match[2])
  return width > 0 && height > 0 ? width / height : null
}

function concreteResolution(value: unknown): { width?: number; height?: number; short_side?: number } | null {
  if (typeof value !== 'string') return null
  const normalized = value.trim().toLowerCase()
  if (!normalized || /^(?:auto|project|default|original|source|unknown|自适应|项目)$/.test(normalized)) return null
  const exact = normalized.match(/^(\d{2,5})\s*[x×]\s*(\d{2,5})$/)
  if (exact) return { width: Number(exact[1]), height: Number(exact[2]) }
  if (/^(?:4k|uhd|2160p)$/.test(normalized)) return { short_side: 2160 }
  if (/^(?:2k|qhd|1440p)$/.test(normalized)) return { short_side: 1440 }
  if (/^(?:fhd|1080p)$/.test(normalized)) return { short_side: 1080 }
  if (/^(?:hd|720p)$/.test(normalized)) return { short_side: 720 }
  return null
}

function finalMediaMeetsDeliverySpec(
  line: LineKey,
  authoring: CanvasAuthoringInput,
  snapshot: CanvasMediaSnapshot,
): boolean {
  if (!basicMediaValid(snapshot)) return false
  const { width, height, duration_seconds: duration, has_audio: hasAudio } = snapshot.metadata
  if (line === 'comic') return width >= 256 && height >= 256

  const spec = record(authoring.delivery_spec)
  const aspect = concreteAspectRatio(spec?.aspect_ratio)
  if (aspect && Math.abs((width / height) - aspect) / aspect > 0.02) return false
  const resolution = concreteResolution(spec?.resolution)
  if (resolution?.width && resolution.height &&
      (Math.abs(width - resolution.width) > 2 || Math.abs(height - resolution.height) > 2)) return false
  if (resolution?.short_side && Math.abs(Math.min(width, height) - resolution.short_side) > 2) return false

  const expectedDuration = Number(spec?.expected_duration_seconds)
  if (Number.isFinite(expectedDuration) && expectedDuration > 0) {
    if (duration === null || Math.abs(duration - expectedDuration) > Math.max(1, expectedDuration * 0.05)) return false
  }
  const audioRequirement = spec?.audio_requirement
  if (audioRequirement === 'required' && !hasAudio) return false
  if (audioRequirement === 'forbidden' && hasAudio) return false
  return true
}

async function finalArtifactEvidence(
  root: string,
  snapshot: CanvasMediaSnapshot,
  contentHash: string,
  inputsSha256: string,
  canvasBlocks: number,
  verified: Record<string, unknown> | null,
): Promise<CanvasFinalArtifactEvidence> {
  const canonicalRoot = await fs.realpath(root).catch(() => root)
  return {
    path: relativeInside(canonicalRoot, snapshot.file) || snapshot.file,
    exists: true,
    sha256: snapshot.sha256,
    content_hash: verified ? contentHash : '',
    inputs_sha256: verified ? inputsSha256 : '',
    qa_blocks: verified ? canvasBlocks : Math.max(1, canvasBlocks),
    qa_receipt_path: verified ? stringField(verified, 'qa_receipt_path') : '',
    qa_receipt_sha256: verified ? stringField(verified, 'qa_receipt_sha256').toLowerCase() : '',
    probe_passed: Boolean(verified),
    revision: `${snapshot.size.toString(16)}-${Math.floor(snapshot.mtime_ms).toString(16)}`,
  }
}

async function finalReceiptDocuments(root: string, episode: string): Promise<Record<string, unknown>[]> {
  const dir = path.join(root, '生产数据')
  const names = await fs.readdir(dir).catch((error: NodeJS.ErrnoException) => {
    if (error.code === 'ENOENT') return []
    throw error
  })
  const files = names.filter((name) => {
    return (name.startsWith('canvas_compose_receipt_') || name.startsWith('canvas_final_receipt_')) &&
      name.endsWith('.json')
  }).sort()
  const documents = await Promise.all(files.map(async (name) => {
    const file = await existingInside(root, path.join('生产数据', name))
    return file ? record(await readJson(file)) : null
  }))
  return documents.filter((receipt): receipt is Record<string, unknown> => {
    return receipt !== null && receipt.version === 1 && receipt.episode === episode &&
      (receipt.kind === 'anime_armory_canvas_final_receipt' ||
        receipt.kind === 'anime_armory_canvas_compose_receipt')
  })
}

async function finalEvidence(
  root: string,
  line: LineKey,
  canvas: CanvasData,
  authoring: CanvasAuthoringInput,
  acceptances: Record<string, CanvasNodeAcceptanceEvidence>,
  productionState: CanvasProductionState | null,
): Promise<CanvasFinalArtifactEvidence | null> {
  const contentHash = computeCanvasContentHash(authoring)
  const inputsSha256 = computeCanvasAcceptedInputsSha256(authoring, acceptances) || ''
  const productionTasks = (productionState?.tasks || []).filter((task) => {
    return task.node_id === CANVAS_EPISODE_TASK_NODE_ID && task.kind === 'production' &&
      task.content_hash === contentHash &&
      (!['failed', 'cancelled', 'stale'].includes(task.status) || recoverableLeaseFailure(task))
  }).sort((a, b) => b.submitted_at.localeCompare(a.submitted_at))
  const receipts = await finalReceiptDocuments(root, canvas.episode)
  const canvasBlocks = Math.max(0, canvas.quality?.blocks || 0, ...canvas.clips.map((clip) => clip.qa_blocks || 0))
  // Receipt-first resolution is intentional: a newer corrupt/temp render must
  // not hide the older master that the latest production job actually bound.
  for (const receipt of receipts) {
    const receiptKind = receipt.kind
    const validKind = receiptKind === 'anime_armory_canvas_final_receipt' ||
      receiptKind === 'anime_armory_canvas_compose_receipt'
    const jobId = stringField(receipt, 'job_id')
    const receiptTask = productionTasks.find((task) => task.job_id === jobId)
    if (!validKind || receipt.version !== 1 || receipt.episode !== canvas.episode ||
        !jobId || productionTasks[0]?.job_id !== jobId ||
        (receiptTask?.promotion_required === true && receipt.promotion_authority !== 'desktop_main_v1')) continue
    const artifactFile = await existingInside(root, stringField(receipt, 'artifact_path'))
    const qaReceipt = await existingInside(root, stringField(receipt, 'qa_receipt_path'))
    if (!artifactFile || !await legalFinalArtifact(root, line, canvas.episode, artifactFile) || !qaReceipt) continue
    const snapshot = await mediaSnapshot(artifactFile).catch(() => null)
    if (!snapshot || !finalMediaMeetsDeliverySpec(line, authoring, snapshot)) continue
    if (!inputsSha256 || receipt.content_hash !== contentHash || receipt.inputs_sha256 !== inputsSha256 ||
        stringField(receipt, 'artifact_sha256').toLowerCase() !== snapshot.sha256 ||
        Number(receipt.qa_blocks) !== 0 || receipt.probe_passed !== true ||
        !['pass', 'accepted', 'machine_complete'].includes(String(receipt.verdict || ''))) continue
    const qaSha = await verifyCanvasQcReceiptSnapshot(root, qaReceipt, {
      kind: 'final',
      episode: canvas.episode,
      jobId,
      contentHash,
      inputsSha256,
      artifactFile,
      artifactSha256: snapshot.sha256,
    }, snapshot)
    if (!qaSha || stringField(receipt, 'qa_receipt_sha256').toLowerCase() !== qaSha) continue
    return finalArtifactEvidence(root, snapshot, contentHash, inputsSha256, canvasBlocks, receipt)
  }
  const fallback = await finalArtifactPath(root, line, canvas.episode)
  if (!fallback) return null
  const snapshot = await mediaSnapshot(fallback).catch(() => null)
  if (!snapshot) return null
  return finalArtifactEvidence(root, snapshot, contentHash, inputsSha256, canvasBlocks, null)
}

async function promoteFinalCandidate(
  root: string,
  line: LineKey,
  canvas: CanvasData,
  authoring: CanvasAuthoringInput,
  state: CanvasProductionState,
  receipts: CandidateReceiptDocument[],
): Promise<boolean> {
  const stableTarget = canvasFinalTargetRel(line, state.episode)
  if (!stableTarget) return false
  const stateAcceptances = Object.fromEntries(Object.entries(state.node_fingerprints).flatMap(([id, node]) => {
    return node.acceptance ? [[id, node.acceptance] as const] : []
  }))
  const inputsSha256 = computeCanvasAcceptedInputsSha256(authoring, stateAcceptances)
  if (!inputsSha256) return false
  for (const candidateReceipt of receipts.filter((item) => item.scope === 'final')) {
    const raw = candidateReceipt.document
    const jobId = stringField(raw, 'job_id')
    const task = state.tasks.find((item) => item.job_id === jobId)
    if (!task || task.promotion_required !== true || task.node_id !== CANVAS_EPISODE_TASK_NODE_ID ||
        task.kind !== 'production' || (task.status !== 'submitted' && task.status !== 'running')) continue
    const targetPath = stringField(raw, 'target_output_path')
    const candidatePath = stringField(raw, 'candidate_output_path')
    const candidateSha = stringField(raw, 'candidate_sha256').toLowerCase()
    const expectedPath = expectedCandidatePath(stableTarget, task.job_id)
    if (targetPath !== stableTarget || task.target_output_path !== stableTarget ||
        task.candidate_output_path !== candidatePath ||
        !expectedPath || candidatePath !== expectedPath ||
        stringField(raw, 'content_hash') !== task.content_hash ||
        stringField(raw, 'task_input_hash') !== task.input_hash ||
        stringField(raw, 'inputs_sha256') !== inputsSha256 || Number(raw.qa_blocks) !== 0 ||
        !passVerdict(raw.verdict) || raw.probe_passed !== true) continue
    const candidateFile = await existingInside(root, candidatePath)
    const recoveryFile = candidateFile || await existingInside(root, targetPath)
    if (!recoveryFile) continue
    const snapshot = await mediaSnapshot(recoveryFile).catch(() => null)
    if (!snapshot || snapshot.sha256 !== candidateSha ||
        !finalMediaMeetsDeliverySpec(line, authoring, snapshot)) continue
    const qc = await verifyCandidateQc(root, raw, {
      scope: 'final',
      episode: state.episode,
      jobId,
      contentHash: task.content_hash,
      candidatePath,
      targetPath,
      candidateSha256: candidateSha,
      taskInputHash: task.input_hash,
      inputsSha256,
    }, snapshot)
    if (!qc) continue
    let promoted = false
    await withCurrentCanvasCandidatePromotion(root, {
      episode: state.episode,
      job_id: task.job_id,
      scope: 'final',
      content_hash: task.content_hash,
      task_input_hash: task.input_hash,
      target_output_path: targetPath,
      candidate_output_path: candidatePath,
      inputs_sha256: inputsSha256,
    }, async (lockedState, lockedTask) => {
      const currentReceipt = await readJsonEvidence(candidateReceipt.file).catch(() => null)
      const currentQc = await readJsonEvidence(qc.file).catch(() => null)
      if (currentReceipt?.sha256 !== candidateReceipt.sha256 || currentQc?.sha256 !== qc.sha256 ||
          !await mediaSnapshotStillCurrent(snapshot)) throw new Error('candidate_promotion_evidence_changed')
      const freshAuthoring = await buildCanvasAuthoringInput(root, line, canvas)
      if (!freshAuthoring || computeCanvasContentHash(freshAuthoring) !== lockedState.content_hash) {
        throw new Error('candidate_promotion_filesystem_inputs_stale')
      }
      for (const clip of freshAuthoring.clips) {
        const acceptance = lockedState.node_fingerprints[clip.id]?.acceptance
        const receiptTask = acceptance
          ? lockedState.tasks.find((item) => item.job_id === acceptance.job_id)
          : undefined
        const output = acceptance ? await existingInside(root, acceptance.output_path) : null
        const outputSnapshot = output ? await mediaSnapshot(output).catch(() => null) : null
        if (!acceptance || !receiptTask || !output || !outputSnapshot || !basicMediaValid(outputSnapshot) ||
            outputSnapshot.sha256 !== acceptance.output_sha256 ||
            !await mediaSnapshotStillCurrent(outputSnapshot)) {
          throw new Error('candidate_promotion_final_input_changed')
        }
        const qaSha = await verifyCanvasQcReceiptSnapshot(root, acceptance.qa_receipt_path, {
          kind: 'node',
          episode: lockedState.episode,
          jobId: acceptance.job_id,
          contentHash: acceptance.content_hash,
          inputHash: lockedState.node_fingerprints[clip.id].input_hash,
          taskInputHash: receiptTask.input_hash,
          nodeId: clip.id,
          targetSlot: clip.final_target.slot,
          targetOutputPath: clip.final_target.output_path,
          artifactFile: output,
          artifactSha256: outputSnapshot.sha256,
        }, outputSnapshot)
        if (!qaSha || qaSha !== acceptance.qa_receipt_sha256) {
          throw new Error('candidate_promotion_final_input_qc_changed')
        }
      }
      const output = await atomicallyPromoteCandidate(root, candidatePath, targetPath, snapshot)
      if (!finalMediaMeetsDeliverySpec(line, lockedState.authoring, output)) {
        throw new Error('candidate_promotion_final_delivery_spec_mismatch')
      }
      const qaPath = path.join(root, '生产数据', `canvas_final_qc_${lockedTask.job_id}_promoted.json`)
      const common = {
        version: 1,
        episode: lockedState.episode,
        job_id: lockedTask.job_id,
        content_hash: lockedTask.content_hash,
        task_input_hash: lockedTask.input_hash,
        inputs_sha256: inputsSha256,
        target_output_path: targetPath,
        candidate_output_path: candidatePath,
        artifact_path: targetPath,
        artifact_sha256: output.sha256,
        candidate_receipt_path: relativeInside(root, candidateReceipt.file) || candidateReceipt.file,
        candidate_receipt_sha256: candidateReceipt.sha256,
        candidate_qa_receipt_path: relativeInside(root, qc.file) || qc.file,
        candidate_qa_receipt_sha256: qc.sha256,
        qa_blocks: 0,
        probe_passed: true,
        promotion_authority: 'desktop_main_v1',
      }
      await atomicReceipt(qaPath, { kind: 'anime_armory_canvas_final_qc', ...common, verdict: 'pass' })
      const qaSha = await stableFileSha256(qaPath)
      await atomicReceipt(path.join(root, '生产数据', `canvas_compose_receipt_${lockedTask.job_id}_promoted.json`), {
        kind: 'anime_armory_canvas_compose_receipt',
        ...common,
        qa_receipt_path: relativeInside(root, qaPath) || qaPath,
        qa_receipt_sha256: qaSha,
        verdict: 'machine_complete',
        accepted_at: new Date().toISOString(),
      })
      promoted = true
    }).catch(() => undefined)
    if (promoted) return true
  }
  return false
}

async function writeAcceptedInputsManifest(
  root: string,
  authoring: CanvasAuthoringInput,
  acceptances: Record<string, CanvasNodeAcceptanceEvidence>,
  expectedState?: CanvasProductionState,
): Promise<string | null> {
  const file = path.join(root, '生产数据', `canvas_inputs_manifest_${authoring.episode}.json`)
  const inputsSha256 = computeCanvasAcceptedInputsSha256(authoring, acceptances)
  if (!inputsSha256) {
    await fs.unlink(file).catch((error: NodeJS.ErrnoException) => {
      if (error.code !== 'ENOENT') throw error
    })
    return null
  }
  const fingerprints = computeCanvasNodeFingerprints(authoring)
  const inputs = authoring.clips.map((clip) => ({
    id: clip.id,
    input_hash: fingerprints[clip.id],
    output_path: acceptances[clip.id].output_path,
    output_sha256: acceptances[clip.id].output_sha256,
  }))
  const payload = {
    kind: 'anime_armory_canvas_inputs_manifest',
    version: 1,
    episode: authoring.episode,
    content_hash: computeCanvasContentHash(authoring),
    canonical_rule: 'SHA-256(UTF-8 compact JSON of ordered [{id,input_hash,output_sha256}] with object keys sorted)',
    digest_payload: inputs.map(({ id, input_hash, output_sha256 }) => ({ id, input_hash, output_sha256 })),
    inputs,
    inputs_sha256: inputsSha256,
    state_revision: expectedState?.revision ?? null,
  }
  if (expectedState) {
    const current = await readCanvasProductionState(root, authoring.episode)
    const currentAcceptances = Object.fromEntries(Object.entries(current?.node_fingerprints || {}).flatMap(([id, node]) => {
      return node.acceptance ? [[id, node.acceptance] as const] : []
    }))
    if (!current || current.revision !== expectedState.revision || current.content_hash !== expectedState.content_hash ||
        computeCanvasAcceptedInputsSha256(current.authoring, currentAcceptances) !== inputsSha256) {
      await fs.unlink(file).catch((error: NodeJS.ErrnoException) => {
        if (error.code !== 'ENOENT') throw error
      })
      return null
    }
  }
  const existing = record(await readJson(file))
  const existingComparable = existing
    ? Object.fromEntries(Object.entries(existing).filter(([key]) => key !== 'created_at'))
    : null
  if (stableCanonicalJson(existingComparable) !== stableCanonicalJson(payload)) {
    await atomicReceipt(file, { ...payload, created_at: new Date().toISOString() })
  }
  if (expectedState) {
    const after = await readCanvasProductionState(root, authoring.episode)
    if (!after || after.revision !== expectedState.revision || after.content_hash !== expectedState.content_hash) {
      await fs.unlink(file).catch((error: NodeJS.ErrnoException) => {
        if (error.code !== 'ENOENT') throw error
      })
      return null
    }
  }
  return inputsSha256
}

async function settleCompletedTasks(root: string, state: CanvasProductionState): Promise<CanvasProductionState> {
  let current = state
  for (const task of state.tasks) {
    if (task.status !== 'submitted' && task.status !== 'running' && !recoverableLeaseFailure(task)) continue
    const node = current.node_fingerprints[task.node_id]
    const productionDone = task.kind === 'production' && current.completion.blockers.length === 0
    const nodeDone = task.kind === current.authoring.final_stage && node?.lifecycle === 'accepted' &&
      node.acceptance?.job_id === task.job_id
    if (!productionDone && !nodeDone) continue
    current = await updateCanvasTaskStatus(root, {
      episode: current.episode,
      job_id: task.job_id,
      status: 'succeeded',
      detail: productionDone ? '最终媒体、probe 与 QC receipt 已验收' : '当前节点媒体与 QC 已验收',
    })
  }
  return current
}

const SUBMITTED_LEASE_MS = 10 * 60 * 1_000
const RUNNING_LEASE_BY_KIND_MS: Record<string, number> = {
  image: 45 * 60 * 1_000,
  video: 2 * 60 * 60 * 1_000,
  production: 6 * 60 * 60 * 1_000,
}

async function expireUnresponsiveTasks(root: string, state: CanvasProductionState): Promise<CanvasProductionState> {
  let current = state
  const now = Date.now()
  for (const task of state.tasks) {
    if (task.status !== 'submitted' && task.status !== 'running') continue
    const timestamp = Date.parse(task.status === 'submitted' ? task.submitted_at : task.updated_at)
    const lease = task.status === 'submitted'
      ? SUBMITTED_LEASE_MS
      : RUNNING_LEASE_BY_KIND_MS[task.kind] ?? RUNNING_LEASE_BY_KIND_MS.image
    if (!Number.isFinite(timestamp) || now - timestamp <= lease) continue
    current = await updateCanvasTaskStatus(root, {
      episode: current.episode,
      job_id: task.job_id,
      status: 'failed',
      detail: task.status === 'submitted'
        ? 'executor dispatch acknowledgement lease expired'
        : 'executor receipt lease expired; safe to retry with a new job',
    })
  }
  return current
}

export async function synchronizeCanvasProduction(
  root: string,
  line: LineKey,
  canvas: CanvasData,
  reason = 'canvas_read',
): Promise<CanvasProductionState | undefined> {
  safeEpisode(canvas.episode)
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const authoring = await buildCanvasAuthoringInput(root, line, canvas)
    if (!authoring || authoring.clips.length === 0) {
      await fs.unlink(path.join(root, '生产数据', `canvas_inputs_manifest_${canvas.episode}.json`)).catch(
        (error: NodeJS.ErrnoException) => {
          if (error.code !== 'ENOENT') throw error
        },
      )
      return undefined
    }
    let previous = await readCanvasProductionState(root, canvas.episode)
    const candidateReceipts = await candidateReceiptDocuments(root, canvas.episode)
    await promoteNodeCandidates(root, line, canvas, previous, candidateReceipts)
    const observedCanvas = await canvasWithObservedStableTargets(root, line, canvas, authoring)
    if (previous) previous = await settleVerifiedGenerationTasks(root, previous)
    const acceptedNodes = await verifiedNodeAcceptances(root, line, observedCanvas, authoring, previous)
    let artifact = await finalEvidence(root, line, observedCanvas, authoring, acceptedNodes, previous)
    try {
      let state = await syncCanvasProductionState(root, {
        authoring,
        canvas: productionCanvas(line, observedCanvas),
        final_artifact: artifact,
        accepted_nodes: acceptedNodes,
        observed_revision: previous?.revision ?? null,
        reason,
      })
      if (await promoteFinalCandidate(root, line, observedCanvas, state.authoring, state, candidateReceipts)) {
        const promotedAcceptances = Object.fromEntries(Object.entries(state.node_fingerprints).flatMap(([id, node]) => {
          return node.acceptance ? [[id, node.acceptance] as const] : []
        }))
        artifact = await finalEvidence(root, line, observedCanvas, state.authoring, promotedAcceptances, state)
        state = await syncCanvasProductionState(root, {
          authoring: state.authoring,
          canvas: productionCanvas(line, observedCanvas),
          final_artifact: artifact,
          accepted_nodes: promotedAcceptances,
          observed_revision: state.revision,
          reason: `${reason}:final_candidate_promoted`,
        })
      }
      // Machine-complete media is intentionally not human final acceptance.
      // The explicit CanvasProductionBar acceptance action is the only path
      // that may satisfy the final product completion predicate.
      state = await settleCompletedTasks(root, state)
      state = await expireUnresponsiveTasks(root, state)
      const stateAcceptances = Object.fromEntries(Object.entries(state.node_fingerprints).flatMap(([id, node]) => {
        return node.acceptance ? [[id, node.acceptance] as const] : []
      }))
      await writeAcceptedInputsManifest(root, state.authoring, stateAcceptances, state)
      return state
    } catch (error) {
      if (String(error).includes('canvas_state_snapshot_stale') && attempt < 2) continue
      throw error
    }
  }
  throw new Error('canvas state 持续变化，无法取得一致快照')
}

export async function submitCanvasProductionTask(
  root: string,
  line: LineKey,
  canvas: CanvasData,
  clipId: string,
  kind: CanvasGenerationKind | 'production',
  expectedContentHash: string,
  targetSlot?: string,
  targetOutputPath?: string,
): Promise<CanvasTaskSubmitResult> {
  const state = await synchronizeCanvasProduction(root, line, canvas, 'before_task_submit')
  if (!state) throw new Error('当前画布没有可提交的制作状态')
  const finalTarget = kind === 'production' ? canvasFinalTargetRel(line, canvas.episode) : null
  if (kind === 'production' && !finalTarget) throw new Error(`当前 ${line} 作品线没有可晋升的最终成品槽`)
  if (kind !== 'production' && (!targetSlot?.trim() || !targetOutputPath?.trim())) {
    throw new Error('生成任务缺少稳定 target slot/path，不能创建隔离 candidate')
  }
  return recordCanvasTaskSubmit(root, {
    episode: canvas.episode,
    node_id: clipId,
    kind,
    target_slot: kind === 'production' ? 'final' : targetSlot,
    target_output_path: kind === 'production' ? finalTarget || undefined : targetOutputPath,
    expected_content_hash: expectedContentHash,
    promotion_required: true,
  })
}

export { CANVAS_EPISODE_TASK_NODE_ID }

async function atomicReceipt(file: string, payload: unknown): Promise<void> {
  await fs.mkdir(path.dirname(file), { recursive: true })
  const temp = `${file}.${process.pid}.${randomUUID()}.tmp`
  try {
    await fs.writeFile(temp, `${JSON.stringify(payload, null, 2)}\n`, { encoding: 'utf8', mode: 0o600 })
    await fs.rename(temp, file)
  } finally {
    await fs.unlink(temp).catch(() => undefined)
  }
}

export async function acceptCanvasFinalProduct(
  root: string,
  line: LineKey,
  canvas: CanvasData,
  expectedContentHash: string,
): Promise<CanvasProductionState> {
  const authoring = await buildCanvasAuthoringInput(root, line, canvas)
  if (!authoring) throw new Error('当前画布没有权威创作源')
  const state = await synchronizeCanvasProduction(root, line, canvas, 'before_final_accept')
  if (!state || state.content_hash !== expectedContentHash) throw new Error('画布内容已变化，请刷新后重试')
  const acceptances = Object.fromEntries(Object.entries(state.node_fingerprints).flatMap(([id, node]) => {
    return node.acceptance ? [[id, node.acceptance]] : []
  }))
  const artifact = await finalEvidence(root, line, canvas, authoring, acceptances, state)
  if (!artifact) throw new Error('最终成品文件不存在')
  const productionJob = [...state.tasks].reverse().find((task) => {
    return task.node_id === CANVAS_EPISODE_TASK_NODE_ID && task.kind === 'production' &&
      task.content_hash === state.content_hash && !['failed', 'cancelled', 'stale'].includes(task.status)
  })
  if (!productionJob) throw new Error('最终成品缺少当前一键制作任务')
  const accepted = await acceptCanvasFinal(root, {
    episode: canvas.episode,
    expected_content_hash: expectedContentHash,
    artifact,
  })
  await atomicReceipt(path.join(root, '生产数据', `canvas_final_receipt_${productionJob.job_id}.json`), {
    kind: 'anime_armory_canvas_final_receipt',
    version: 1,
    episode: canvas.episode,
    job_id: productionJob.job_id,
    content_hash: accepted.content_hash,
    inputs_sha256: artifact.inputs_sha256,
    artifact_path: artifact.path,
    artifact_sha256: artifact.sha256,
    qa_blocks: artifact.qa_blocks,
    qa_receipt_path: artifact.qa_receipt_path,
    qa_receipt_sha256: artifact.qa_receipt_sha256,
    probe_passed: artifact.probe_passed,
    verdict: 'accepted',
    accepted_at: accepted.completion.accepted_at,
    reviewer_kind: 'human',
    reviewer: 'desktop_user',
    confirmation: {
      kind: 'explicit_final_artifact_acceptance',
      accepted_current_artifact: true,
    },
    promotion_authority: 'desktop_main_v1',
    acceptance: 'explicit_desktop_user',
  })
  return accepted
}
