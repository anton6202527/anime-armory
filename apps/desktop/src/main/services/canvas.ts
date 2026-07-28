import fs from 'node:fs/promises'
import { existsSync, realpathSync, statSync, type Dirent } from 'node:fs'
import path from 'node:path'
import type {
  CanvasReadResult,
  CanvasClip,
  CanvasData,
  CanvasFrame,
  CanvasGenerationConfig,
  CanvasGenerationKind,
  CanvasGenerationModel,
  CanvasGenerationProfile,
  CanvasLayout,
  CanvasMetric,
  CanvasNodePosition,
  CanvasQualitySummary,
  CanvasReturnTask,
  CanvasScoreDimension,
  CanvasSeam,
  ClipEditData,
  ClipEditPatch,
  EpisodeWorkspace,
  QaFlag,
} from '@shared/types'
import { isIgnoredName, resolveWithin } from '../util/paths'
import { fnv1a64 } from '../util/hash'

/**
 * Canvas service — TypeScript port of the Tauri canvas commands
 * (desktop/src-tauri/src/commands.rs): read_canvas, read_canvas_layout,
 * write_canvas_layout, read_clip_edit, write_clip_edit, read_episode_workspace.
 *
 * Source-of-truth fallback order for the canvas:
 *   生产数据/review_ui_<ep>.json → 脚本/<ep>/storyboard.json → 脚本/<ep>/panel_script.json
 */

const CANVAS_PROMPT_PREVIEW_LIMIT = 4096

type Json = unknown

// ---------------------------------------------------------------- JSON utils

function isObj(v: Json): v is Record<string, Json> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

function get(v: Json, k: string): Json {
  return isObj(v) ? v[k] : undefined
}

/** Mirrors Rust `s()`: string field or undefined. */
function s(v: Json, k: string): string | undefined {
  const x = get(v, k)
  return typeof x === 'string' ? x : undefined
}

/** Mirrors Rust `n_f64()` / `.as_f64()`: numeric field or undefined. */
function nF64(v: Json, k: string): number | undefined {
  const x = get(v, k)
  return typeof x === 'number' && Number.isFinite(x) ? x : undefined
}

/** Mirrors Rust `n_i64()`: integer field or 0 (serde_json as_i64 is None for floats). */
function nI64(v: Json, k: string): number {
  const x = get(v, k)
  return typeof x === 'number' && Number.isInteger(x) ? x : 0
}

/** Integer field or undefined (Rust `.and_then(|v| v.as_i64())`). */
function iVal(v: Json, k: string): number | undefined {
  const x = get(v, k)
  return typeof x === 'number' && Number.isInteger(x) ? x : undefined
}

function asBool(v: Json): boolean | undefined {
  return typeof v === 'boolean' ? v : undefined
}

function asArray(v: Json): Json[] | undefined {
  return Array.isArray(v) ? v : undefined
}

async function readJson(file: string): Promise<Json | undefined> {
  try {
    return JSON.parse(await fs.readFile(file, 'utf8')) as Json
  } catch {
    return undefined
  }
}

// ---------------------------------------------------------------- text utils

/** Truncate by Unicode code points, appending `…` (mirrors Rust short_text). */
function shortText(value: string, limit: number): string {
  const chars = Array.from(value)
  return chars.length <= limit ? value : `${chars.slice(0, limit).join('')}…`
}

/** Mirrors Rust value_label(): string / number / bool → display label. */
function valueLabel(value: Json): string | undefined {
  if (typeof value === 'string') {
    const t = value.trim()
    if (t) return t
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.abs(value % 1) < Number.EPSILON ? String(Math.trunc(value)) : value.toFixed(2)
  }
  if (typeof value === 'boolean') return value ? '是' : '否'
  return undefined
}

function stringArray(v: Json, k: string, limit: number): string[] {
  const arr = asArray(get(v, k))
  if (!arr) return []
  const out: string[] = []
  for (const item of arr) {
    if (typeof item === 'string') {
      out.push(shortText(item, 180))
      if (out.length >= limit) break
    }
  }
  return out
}

function valueString(v: Json, k: string): string {
  return s(v, k) ?? ''
}

function nonemptyValueString(v: Json, k: string): string | undefined {
  const value = valueString(v, k)
  return value.trim() === '' ? undefined : value
}

function valueStringOr(v: Json, k: string, fallback: string | undefined): string {
  return nonemptyValueString(v, k) ?? fallback ?? ''
}

const pad2 = (n: number): string => String(n).padStart(2, '0')
const pad3 = (n: number): string => String(n).padStart(3, '0')

/** Rust str::trim_end_matches — strips every trailing occurrence. */
function trimEndMatches(value: string, pat: string): string {
  let v = value
  while (pat && v.endsWith(pat)) v = v.slice(0, -pat.length)
  return v
}

// ------------------------------------------------------- episodes & fs paths

/** "第12集" / "第7a集" → 12 / 7 ; fallback large so unparsable names sort last. */
function epNum(name: string): number {
  const digits = name.replace(/[^0-9]/g, '')
  const n = digits === '' ? NaN : Number.parseInt(digits, 10)
  return Number.isSafeInteger(n) ? n : 1_000_000
}

function numberFromId(id: string): number | undefined {
  const digits = id.replace(/[^0-9]/g, '')
  const n = digits === '' ? NaN : Number.parseInt(digits, 10)
  return Number.isSafeInteger(n) ? n : undefined
}

/** Subdirs of 脚本/ starting with 第, sorted by embedded number then name. */
async function listEpisodes(root: string): Promise<string[]> {
  const eps: string[] = []
  try {
    const entries = await fs.readdir(path.join(root, '脚本'), { withFileTypes: true })
    for (const e of entries) {
      if (e.isDirectory() && e.name.startsWith('第')) eps.push(e.name)
    }
  } catch {
    // no 脚本/ dir yet — no episodes
  }
  eps.sort((a, b) => epNum(a) - epNum(b) || (a < b ? -1 : a > b ? 1 : 0))
  return eps
}

function validateEpisodeName(ep: string): void {
  if (ep.trim() === '' || ep.includes('/') || ep.includes('\\') || ep.includes('\0')) {
    throw new Error('非法集名')
  }
}

/** Canonicalized work root; throws the user-facing error if missing. */
function realWorkRoot(root: string): string {
  try {
    const base = realpathSync(root)
    if (!statSync(base).isDirectory()) throw new Error()
    return base
  } catch {
    throw new Error('作品目录不存在')
  }
}

async function productionDirForWrite(root: string): Promise<string> {
  const dir = path.join(realWorkRoot(root), '生产数据')
  await fs.mkdir(dir, { recursive: true })
  return dir
}

function canvasLayoutReadPath(root: string, ep: string): string {
  validateEpisodeName(ep)
  return path.join(realWorkRoot(root), '生产数据', `canvas_layout_${ep}.json`)
}

/** Anti-traversal resolve of an existing file under root; null when absent/invalid. */
function existingWorkPath(root: string, rel: string): string | null {
  try {
    const p = resolveWithin(root, rel)
    return existsSync(p) ? p : null
  } catch {
    return null
  }
}

function storyboardPath(root: string, ep: string): string | null {
  return existingWorkPath(root, `脚本/${ep}/storyboard.json`)
}

function panelScriptPath(root: string, ep: string): string | null {
  return existingWorkPath(root, `脚本/${ep}/panel_script.json`)
}

// ------------------------------------------------ canvas generation profile

async function readProjectSettings(root: string): Promise<Map<string, string>> {
  let text = ''
  try {
    text = await fs.readFile(path.join(root, '_设置.md'), 'utf8')
  } catch {
    return new Map()
  }
  const settings = new Map<string, string>()
  for (const line of text.split(/\r?\n/)) {
    const match = /^\s*-\s*([^：:#]+?)\s*[：:]\s*(.*?)\s*(?:#.*)?$/.exec(line)
    if (!match) continue
    const key = match[1].trim()
    const value = match[2].trim()
    if (key && value) settings.set(key, value)
  }
  return settings
}

function assertionValue(data: Json, key: string): Json {
  return get(get(get(data, 'capability_assertions'), key), 'value')
}

function assertionBool(data: Json, key: string): boolean | undefined {
  return asBool(assertionValue(data, key))
}

function assertionNumber(data: Json, key: string): number | undefined {
  const value = assertionValue(data, key)
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

function assertionStrings(data: Json, key: string): string[] {
  const value = assertionValue(data, key)
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

function normalizedModelKey(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, '')
}

function modelMatches(model: CanvasGenerationModel, value: string): boolean {
  const needle = normalizedModelKey(value)
  if (!needle) return false
  const haystacks = [model.id, model.label, model.channel ?? ''].map(normalizedModelKey)
  return haystacks.some((item) => item === needle || item.includes(needle) || needle.includes(item))
}

function observedResolutions(data: Json): string[] {
  const text = JSON.stringify(data)
  const values: string[] = []
  for (const match of text.matchAll(/(?:^|[^a-z0-9])(480p|720p|1080p|4k)(?=$|[^a-z0-9])/gi)) {
    const value = match[1].toUpperCase() === '4K' ? '4K' : match[1].toLowerCase()
    if (!values.includes(value)) values.push(value)
  }
  return values
}

async function capabilityModels(
  root: string,
  kind: CanvasGenerationKind
): Promise<CanvasGenerationModel[]> {
  const dir = path.join(root, '生产数据', `${kind}_backend_capabilities`)
  let entries: Dirent[]
  try {
    entries = await fs.readdir(dir, { withFileTypes: true })
  } catch {
    return []
  }
  const models: CanvasGenerationModel[] = []
  for (const entry of entries.filter((item) => item.isFile() && item.name.endsWith('.json')).slice(0, 40)) {
    const data = await readJson(path.join(dir, entry.name))
    const adapter = get(data, 'adapter')
    const id = s(adapter, 'canonical') ?? s(data, 'backend') ?? path.parse(entry.name).name
    const label = s(adapter, 'label') ?? s(adapter, 'model') ?? id
    if (!id.trim() || models.some((model) => model.id === id)) continue
    const referenceInput = get(adapter, 'reference_input')
    const frameControl = get(adapter, 'frame_control')
    const supportsFirst = asBool(get(frameControl, 'supports_first_frame')) ?? assertionBool(data, 'supports_first_frame') ?? false
    const supportsLast = asBool(get(frameControl, 'supports_last_frame')) ?? assertionBool(data, 'supports_last_frame') ?? false
    const maxTimeline = nF64(frameControl, 'max_timeline_frames') ?? assertionNumber(data, 'max_timeline_frames') ?? 0
    const motionCapabilities = assertionStrings(data, 'motion_control_capabilities')
    const generationModes = (asArray(get(adapter, 'generation_modes')) ?? [])
      .filter((item): item is string => typeof item === 'string')
    const nativeReferences =
      (asBool(get(adapter, 'multi_reference')) ?? false) ||
      motionCapabilities.includes('multimodal_reference') ||
      get(referenceInput, 'mode') !== undefined
    const modes = kind === 'video'
      ? [
          'project_route',
          'text2video',
          ...(supportsFirst ? ['image2video'] : []),
          ...(supportsLast ? ['frames2video'] : []),
          ...(maxTimeline > 1 ? ['multiframe2video'] : []),
          ...(nativeReferences ? ['multimodal2video'] : []),
        ]
      : generationModes.length
        ? generationModes
        : ['text2image', ...(nativeReferences ? ['image_reference'] : [])]
    const evidence = s(adapter, 'evidence') ?? s(get(adapter, 'evidence'), 'source')
    const available =
      kind === 'video'
        ? (asBool(get(adapter, 'paid_routing_allowed')) ?? assertionBool(data, 'paid_routing_allowed') ?? true)
        : (asBool(get(adapter, 'auto_runnable')) ?? assertionBool(data, 'auto_runnable') ?? true)
    models.push({
      id,
      label,
      kind,
      channel: s(adapter, 'channel') ?? s(data, 'channel'),
      description: evidence ? shortText(evidence, 150) : undefined,
      available,
      premium: /vip|pro|premium/i.test(`${label} ${JSON.stringify(data).slice(0, 12000)}`),
      min_duration: kind === 'video' ? 4 : undefined,
      max_duration: kind === 'video'
        ? (nF64(adapter, 'max_clip_seconds') ?? assertionNumber(data, 'max_clip_seconds') ?? 15)
        : undefined,
      resolutions: observedResolutions(data),
      modes: Array.from(new Set(modes)),
      native_audio: kind === 'video'
        ? (asBool(get(adapter, 'native_audio')) ?? assertionBool(data, 'native_audio') ?? false)
        : false,
      native_references: nativeReferences,
      source: `生产数据/${kind}_backend_capabilities/${entry.name}`,
    })
  }
  return models
}

function promoteProjectModel(
  models: CanvasGenerationModel[],
  kind: CanvasGenerationKind,
  projectModel: string | undefined,
  channel: string | undefined,
  fallbackId: string | undefined
): string | undefined {
  let preferred = projectModel ? models.find((model) => modelMatches(model, projectModel)) : undefined
  preferred ??= fallbackId ? models.find((model) => modelMatches(model, fallbackId)) : undefined
  if (!preferred && projectModel) {
    preferred = {
      id: fallbackId || normalizedModelKey(projectModel) || 'project-default',
      label: projectModel,
      kind,
      channel,
      description: '来自本作 _设置.md；能力由本线适配层在执行前核验',
      available: true,
      preferred: true,
      premium: /vip|pro|premium/i.test(projectModel),
      min_duration: kind === 'video' ? 4 : undefined,
      max_duration: kind === 'video' ? 15 : undefined,
      resolutions: kind === 'video' ? ['720p'] : [],
      modes: kind === 'video' ? ['project_route', 'image2video'] : ['text2image', 'image_reference'],
      native_audio: false,
      native_references: true,
      source: '_设置.md',
    }
    models.unshift(preferred)
  }
  if (!preferred && models.length) preferred = models[0]
  if (!preferred) {
    preferred = {
      id: 'project-default',
      label: '项目默认 · 自动路由',
      kind,
      channel,
      description: '由当前作品线的设置与适配层决定实际执行后端',
      available: true,
      preferred: true,
      min_duration: kind === 'video' ? 4 : undefined,
      max_duration: kind === 'video' ? 15 : undefined,
      resolutions: kind === 'video' ? ['720p'] : [],
      modes: kind === 'video' ? ['project_route'] : ['text2image'],
      native_audio: false,
      native_references: false,
      source: '_设置.md / 本线适配层',
    }
    models.unshift(preferred)
  }
  preferred.preferred = true
  if (projectModel) preferred.label = projectModel
  if (channel) preferred.channel = channel
  models.sort((a, b) => Number(Boolean(b.preferred)) - Number(Boolean(a.preferred)) || a.label.localeCompare(b.label))
  return preferred.id
}

async function generationProfile(root: string, ep: string): Promise<CanvasGenerationProfile> {
  const settings = await readProjectSettings(root)
  const [imageModels, videoModels, routes, imageBaseline] = await Promise.all([
    capabilityModels(root, 'image'),
    capabilityModels(root, 'video'),
    readJson(path.join(root, '出视频', ep, 'prompt', 'video_model_routes.json')),
    readJson(path.join(root, '生产数据', 'image_backend_baseline.json')),
  ])
  const baselineSelection = get(imageBaseline, 'selection')
  const defaultImageModel = promoteProjectModel(
    imageModels,
    'image',
    settings.get('生图模型') ?? s(baselineSelection, 'image_model') ?? s(baselineSelection, 'adapter_model'),
    settings.get('生图AI') ?? settings.get('生图渠道') ?? s(baselineSelection, 'channel'),
    s(baselineSelection, 'backend')
  )
  const defaultVideoModel = promoteProjectModel(
    videoModels,
    'video',
    settings.get('生视频模型'),
    settings.get('生视频渠道'),
    s(routes, 'default_backend')
  )
  return {
    default_aspect_ratio: settings.get('画幅') ?? settings.get('画面比例') ?? 'Auto',
    default_resolution: settings.get('视频分辨率') ?? '720p',
    default_image_model: defaultImageModel,
    default_video_model: defaultVideoModel,
    default_video_duration: 10,
    audio_policy: settings.get('视频生成音频策略') ?? s(routes, 'video_generation_audio_policy'),
    image_models: imageModels,
    video_models: videoModels,
  }
}

// -------------------------------------------------------- media abs/revision

function relAbs(root: string, rel: string | undefined): { abs?: string; exists: boolean } {
  if (rel === undefined || rel.trim() === '') return { exists: false }
  const abs = path.isAbsolute(rel) ? rel : path.join(root, rel)
  return { abs, exists: existsSync(abs) }
}

/** Cache-buster: `${sizeHex}-${mtimeNanosHex}` (files only). */
function mediaRevision(abs: string | undefined): string | undefined {
  if (abs === undefined) return undefined
  try {
    const st = statSync(abs, { bigint: true })
    if (!st.isFile()) return undefined
    const mtimeNs = st.mtimeNs > 0n ? st.mtimeNs : 0n
    return `${st.size.toString(16)}-${mtimeNs.toString(16)}`
  } catch {
    return undefined
  }
}

// ---------------------------------------------------- prompt-pack extraction

function headingMatchesClip(line: string, clipId: string, number: number | undefined): boolean {
  if (clipId.trim() !== '' && line.includes(clipId)) return true
  if (number !== undefined) {
    const n2 = pad2(number)
    const n3 = pad3(number)
    const candidates = [
      `镜头 ${number}`,
      `镜头${number}`,
      `Clip ${number}`,
      `Clip ${n2}`,
      `Clip${n2}`,
      `Clip_${n2}`,
      `CLIP${n2}`,
      `P${n2}`,
      `P${n3}`,
    ]
    return candidates.some((candidate) => line.includes(candidate))
  }
  return false
}

/** The `## ` section (heading line through just before the next `## `) for a clip. */
function markdownClipSection(
  text: string,
  clipId: string,
  number: number | undefined
): string | undefined {
  const headings: Array<{ start: number; heading: string }> = []
  let pos = 0
  for (const line of text.split(/(?<=\n)/)) {
    if (line.startsWith('## ') && !line.startsWith('### ')) {
      headings.push({ start: pos, heading: line.trimEnd() })
    }
    pos += line.length
  }
  for (let idx = 0; idx < headings.length; idx++) {
    if (headingMatchesClip(headings[idx].heading, clipId, number)) {
      const end = idx + 1 < headings.length ? headings[idx + 1].start : text.length
      return text.slice(headings[idx].start, end)
    }
  }
  return undefined
}

/**
 * Under a matching `### ` subheading, prefer the first non-empty fenced block;
 * otherwise the plain lines up to the next heading.
 */
function fencedOrPlainAfterHeading(section: string, prefixes: string[]): string | undefined {
  const lines = section.split('\n').map((l) => (l.endsWith('\r') ? l.slice(0, -1) : l))
  for (let idx = 0; idx < lines.length; idx++) {
    const heading = lines[idx].trim()
    if (!heading.startsWith('### ') || !prefixes.some((prefix) => heading.includes(prefix))) {
      continue
    }
    const plain: string[] = []
    const fenced: string[] = []
    let inFence = false
    let sawFence = false
    let fencedValue: string | undefined
    for (let j = idx + 1; j < lines.length; j++) {
      const line = lines[j]
      const trimmed = line.trim()
      if (trimmed.startsWith('```')) {
        if (inFence) {
          const value = fenced.join('\n').trim()
          if (value !== '') fencedValue = value
          break
        }
        inFence = true
        sawFence = true
        continue
      }
      if (inFence) {
        fenced.push(line)
        continue
      }
      if (trimmed.startsWith('### ') || trimmed.startsWith('## ')) break
      if (!sawFence) plain.push(line)
    }
    if (fencedValue !== undefined) return fencedValue
    const value = plain.join('\n').trim()
    if (value !== '') return value
  }
  return undefined
}

async function readClipPromptPack(
  root: string,
  rel: string[],
  clipId: string,
  number: number | undefined,
  subheadingPrefixes: string[]
): Promise<string | undefined> {
  let text: string
  try {
    text = await fs.readFile(path.join(root, ...rel), 'utf8')
  } catch {
    return undefined
  }
  const section = markdownClipSection(text, clipId, number)
  if (section === undefined) return undefined
  return fencedOrPlainAfterHeading(section, subheadingPrefixes)
}

// -------------------------------------------------------------- clip prompts

function storyboardShotText(clip: Json): string | undefined {
  const parts: string[] = []
  const shots = asArray(get(clip, 'shots'))
  if (shots) {
    shots.forEach((shot, idx) => {
      const bits: string[] = []
      const t = s(shot, 't')
      if (t !== undefined) bits.push(t)
      const lens = s(shot, 'lens')
      if (lens !== undefined) bits.push(lens)
      const desc = s(shot, 'desc')
      if (desc !== undefined) bits.push(desc)
      if (bits.length > 0) parts.push(`shot ${idx + 1}: ${bits.join(' · ')}`)
    })
  }
  return parts.length > 0 ? parts.join('\n') : undefined
}

function storyboardShotVideoPrompt(clip: Json): string | undefined {
  const parts: string[] = []
  const shots = asArray(get(clip, 'shots'))
  if (shots) {
    shots.forEach((shot, idx) => {
      const prompt = s(shot, 'video_prompt')?.trim()
      if (prompt === undefined || prompt === '') return
      let label = `shot ${idx + 1}`
      const t = s(shot, 't')
      if (t !== undefined) label += ` · ${t}`
      const lens = s(shot, 'lens')
      if (lens !== undefined) label += ` · ${lens}`
      parts.push(`${label}: ${prompt}`)
    })
  }
  return parts.length > 0 ? parts.join('\n') : undefined
}

/** Compact multi-source prompt preview, capped at 4096 code points. */
function clipPrompt(c: Json): string | undefined {
  const parts: string[] = []
  for (const key of ['video_prompt', 'image_prompt', 'prompt', 'positive_prompt', 'negative_prompt']) {
    const v = s(c, key)?.trim()
    if (v !== undefined && v !== '') parts.push(`${key}: ${v}`)
  }
  const shots = asArray(get(c, 'shots'))
  if (shots) {
    shots.forEach((shot, idx) => {
      const bits: string[] = []
      const t = s(shot, 't')
      if (t !== undefined) bits.push(t)
      const lens = s(shot, 'lens')
      if (lens !== undefined) bits.push(lens)
      const desc = s(shot, 'desc')
      if (desc !== undefined) bits.push(desc)
      const prompt = s(shot, 'video_prompt')
      if (prompt !== undefined) bits.push(`video_prompt: ${prompt}`)
      if (bits.length > 0) parts.push(`shot ${idx + 1}: ${bits.join(' · ')}`)
    })
  }
  if (parts.length === 0) return undefined
  const joined = parts.join('\n')
  const chars = Array.from(joined)
  if (chars.length > CANVAS_PROMPT_PREVIEW_LIMIT) {
    return `${chars.slice(0, CANVAS_PROMPT_PREVIEW_LIMIT).join('')}\n…`
  }
  return joined
}

// ------------------------------------------------------------ canvas frames

function pushFrame(
  frames: CanvasFrame[],
  root: string,
  role: string,
  label: string,
  rel: string | undefined,
  atSec: number | undefined,
  prompt: string | undefined
): void {
  const { abs, exists } = relAbs(root, rel)
  frames.push({
    role,
    label,
    abs,
    exists,
    revision: mediaRevision(abs),
    at_sec: atSec,
    prompt,
  })
}

function storyboardFrames(root: string, c: Json): CanvasFrame[] {
  const frames: CanvasFrame[] = []
  pushFrame(frames, root, 'first', '首帧', s(c, 'firstframe_png'), 0.0, undefined)
  const continuity = get(c, 'continuity')
  const anchors = asArray(get(continuity, 'anchors'))
  if (anchors) {
    anchors.forEach((raw, idx) => {
      const rel =
        s(raw, 'anchor_png') ?? s(raw, 'png') ?? s(raw, 'path') ?? s(raw, 'image') ?? s(raw, 'image_path')
      const at = nF64(raw, 'at_sec')
      const reason = s(raw, 'reason')
      const framePrompt =
        reason !== undefined && reason.trim() !== '' ? `reason: ${reason}` : undefined
      pushFrame(frames, root, 'anchor', `中帧${idx + 1}`, rel, at, framePrompt)
    })
  } else {
    const mid = s(continuity, 'midframe') ?? s(c, 'midframe')
    if (mid !== undefined) pushFrame(frames, root, 'anchor', '中帧', mid, undefined, undefined)
  }
  const endRel = s(continuity, 'endframe_png') ?? s(c, 'endframe_png')
  pushFrame(frames, root, 'end', '尾帧', endRel, nF64(c, 'duration'), undefined)

  const seen = new Set<string>()
  return frames.filter((f) => {
    const key = `${f.role}:${f.abs ?? ''}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function reviewAssetFrame(root: string, raw: Json, fallbackLabel: string): CanvasFrame {
  const { abs, exists: existsByPath } = relAbs(root, s(raw, 'path'))
  return {
    role: s(raw, 'role') ?? fallbackLabel,
    label: s(raw, 'label') ?? s(raw, 'name') ?? fallbackLabel,
    abs,
    exists: asBool(get(raw, 'exists')) ?? existsByPath,
    revision: mediaRevision(abs),
    at_sec: nF64(raw, 'at_sec'),
    prompt: undefined,
  }
}

function reviewFrames(root: string, c: Json): CanvasFrame[] {
  const frames: CanvasFrame[] = []
  const anchors = asArray(get(c, 'anchor_frames'))
  if (anchors) {
    for (const raw of anchors) frames.push(reviewAssetFrame(root, raw, '锚帧'))
  }
  if (frames.length === 0) {
    const first = get(c, 'first_frame')
    if (first !== undefined) frames.push(reviewAssetFrame(root, first, '首帧'))
    const end = get(c, 'end_frame')
    if (end !== undefined) frames.push(reviewAssetFrame(root, end, '尾帧'))
  }
  const consumed = asArray(get(c, 'consumed_frames'))
  if (consumed) {
    const seenPaths = new Set<string>()
    for (const f of frames) if (f.abs !== undefined) seenPaths.add(f.abs)
    for (const raw of consumed) {
      const frame = reviewAssetFrame(root, raw, '入参')
      if (frame.abs === undefined || !seenPaths.has(frame.abs)) {
        if (frame.abs !== undefined) seenPaths.add(frame.abs)
        frames.push(frame)
      }
    }
  }
  return frames
}

// --------------------------------------------------------- storyboard source

function fromStoryboard(root: string, ep: string, data: Json): CanvasClip[] {
  const clips = asArray(get(data, 'clips')) ?? []
  return clips.map((c, i) => {
    const prompt = clipPrompt(c)
    const frames = storyboardFrames(root, c)
    const { abs: ffAbs, exists: ffExists } = relAbs(root, s(c, 'firstframe_png'))
    const { abs: vidAbs, exists: vidExists } = relAbs(root, s(c, 'video_out'))
    return {
      id: s(c, 'id') ?? `${ep}_CLIP${pad2(i + 1)}`,
      number: iVal(c, 'number') ?? i + 1,
      label: s(c, 'label') ?? '',
      duration: nF64(c, 'duration'),
      scene: s(c, 'scene'),
      rhythm: s(c, 'rhythm'),
      template: s(c, 'template'),
      first_frame_abs: ffAbs,
      first_frame_exists: ffExists,
      video_abs: vidAbs,
      video_exists: vidExists,
      video_revision: mediaRevision(vidAbs),
      frames,
      prompt,
      qa: [],
      score: undefined,
      qa_blocks: 0,
      qa_warnings: 0,
      qa_infos: 0,
    }
  })
}

function seamsFromClips(clips: CanvasClip[], data: Json): CanvasSeam[] {
  const raw = asArray(get(data, 'clips')) ?? []
  const seams: CanvasSeam[] = []
  for (let i = 0; i + 1 < clips.length; i++) {
    seams.push({
      from: clips[i].id,
      to: clips[i + 1].id,
      transition: s(get(raw[i], 'continuity'), 'transition'),
    })
  }
  return seams
}

function sequentialSeams(clips: CanvasClip[], transition: string | undefined): CanvasSeam[] {
  const seams: CanvasSeam[] = []
  for (let i = 0; i + 1 < clips.length; i++) {
    seams.push({ from: clips[i].id, to: clips[i + 1].id, transition })
  }
  return seams
}

// ------------------------------------------------------------- shared assets

function isSharedAssetRel(rel: string): boolean {
  const norm = rel.replaceAll('\\', '/').toLowerCase()
  return norm.includes('出图/共享/') || norm.includes('/shared/')
}

function isCanvasImagePath(p: string): boolean {
  const ext = path.extname(p).toLowerCase()
  return ext === '.png' || ext === '.jpg' || ext === '.jpeg' || ext === '.webp' || ext === '.gif'
}

async function pushSharedAssetFiles(root: string, dir: string, depth: number, out: CanvasFrame[]): Promise<void> {
  if (depth > 4 || out.length >= 160) return
  let entries: Dirent[]
  try {
    entries = await fs.readdir(dir, { withFileTypes: true })
  } catch {
    return
  }
  const kept = entries
    .filter((e) => !isIgnoredName(e.name))
    .sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0))
  for (const e of kept) {
    if (out.length >= 160) break
    const p = path.join(dir, e.name)
    let isDir = e.isDirectory()
    let isFile = e.isFile()
    if (e.isSymbolicLink()) {
      try {
        const st = await fs.stat(p)
        isDir = st.isDirectory()
        isFile = st.isFile()
      } catch {
        continue
      }
    }
    if (isDir) {
      await pushSharedAssetFiles(root, p, depth + 1, out)
      continue
    }
    if (!isFile || !isCanvasImagePath(p)) continue
    const rel = path.relative(root, p).replaceAll('\\', '/')
    if (!isSharedAssetRel(rel)) continue
    out.push({
      role: 'shared_asset',
      label: path.parse(p).name || '共享资产',
      abs: p,
      exists: true,
      revision: mediaRevision(p),
      at_sec: undefined,
      prompt: rel,
    })
  }
}

/** 定妆库 scan: 出图/共享/{图片,用户参考} (plus the 共享 root), deduped, label-sorted. */
async function sharedAssetFrames(root: string): Promise<CanvasFrame[]> {
  const shared = path.join(root, '出图', '共享')
  const out: CanvasFrame[] = []
  for (const dir of [path.join(shared, '图片'), path.join(shared, '用户参考'), shared]) {
    await pushSharedAssetFiles(root, dir, 0, out)
  }
  const seen = new Set<string>()
  const deduped = out.filter((frame) => {
    if (frame.abs === undefined || seen.has(frame.abs)) return false
    seen.add(frame.abs)
    return true
  })
  deduped.sort((a, b) => (a.label < b.label ? -1 : a.label > b.label ? 1 : 0))
  return deduped
}

// ----------------------------------------------------------- comic panelwork

function comicReferenceLabel(raw: Json): string {
  const id = s(raw, 'id') ?? '共享资产'
  const view = s(raw, 'view')
  if (view !== undefined) {
    const label = trimEndMatches(view, '_path')
    if (label.trim() !== '') return `${id} / ${label}`
  }
  return id
}

function pushComicSharedAssetFrame(
  frames: CanvasFrame[],
  seen: Set<string>,
  root: string,
  id: string,
  view: string,
  rel: string
): void {
  if (!isSharedAssetRel(rel) || seen.has(rel)) return
  seen.add(rel)
  const { abs, exists } = relAbs(root, rel)
  if (!exists) return
  const viewLabel = trimEndMatches(view, '_path')
  frames.push({
    role: 'shared_asset',
    label: viewLabel === '' ? id : `${id} / ${viewLabel}`,
    abs,
    exists,
    revision: mediaRevision(abs),
    at_sec: undefined,
    prompt: `id: ${id}\nview: ${view}\n${rel}`,
  })
}

function comicReferenceFrames(root: string, panel: Json, job: Json | undefined): CanvasFrame[] {
  const frames: CanvasFrame[] = []
  const seen = new Set<string>()
  const refs = asArray(get(job, 'references'))
  if (refs) {
    for (const raw of refs) {
      const rel = s(raw, 'path')
      if (rel === undefined || !isSharedAssetRel(rel)) continue
      if (seen.has(rel)) continue
      seen.add(rel)
      const { abs, exists } = relAbs(root, rel)
      const id = s(raw, 'id')
      const view = s(raw, 'view')
      const promptParts: string[] = []
      if (id !== undefined) promptParts.push(`id: ${id}`)
      if (view !== undefined) promptParts.push(`view: ${view}`)
      promptParts.push(rel)
      frames.push({
        role: 'shared_asset',
        label: comicReferenceLabel(raw),
        abs,
        exists,
        revision: mediaRevision(abs),
        at_sec: undefined,
        prompt: promptParts.join('\n'),
      })
    }
  }

  const sceneId = s(panel, 'scene_anchor_id') ?? s(panel, 'location')
  if (sceneId !== undefined) {
    pushComicSharedAssetFrame(
      frames,
      seen,
      root,
      sceneId,
      'anchor',
      `出图/共享/图片/${sceneId}__anchor.png`
    )
  }
  const panelRefs = asArray(get(panel, 'references'))
  if (panelRefs) {
    for (const raw of panelRefs) {
      if (typeof raw === 'string' && raw.trim() !== '') {
        pushComicSharedAssetFrame(frames, seen, root, raw, 'anchor', `出图/共享/图片/${raw}__anchor.png`)
      }
    }
  }
  return frames
}

async function comicPanelJobs(root: string, ep: string): Promise<Map<string, Json>> {
  const data = await readJson(path.join(root, '出图', ep, 'prompt', 'panel_jobs.json'))
  const jobs = asArray(get(data, 'jobs'))
  const out = new Map<string, Json>()
  if (jobs) {
    for (const job of jobs) {
      const id = s(job, 'panel_id')
      if (id !== undefined) out.set(id, job)
    }
  }
  return out
}

async function comicPanelQc(
  root: string,
  ep: string,
  panelId: string,
  job: Json | undefined
): Promise<Json | undefined> {
  const postQc = get(job, 'post_qc')
  if (isObj(postQc)) return postQc
  return readJson(path.join(root, '生产数据', 'panel_qc', ep, `${panelId}.json`))
}

async function comicFindingsByPanel(root: string, ep: string): Promise<Map<string, Json[]>> {
  const out = new Map<string, Json[]>()
  for (const file of [`consistency_findings_style_${ep}.json`, `comic_consistency_findings_${ep}.json`]) {
    const data = await readJson(path.join(root, '生产数据', file))
    const findings = asArray(get(data, 'findings'))
    if (!findings) continue
    for (const finding of findings) {
      const panelId = s(finding, 'panel_id')
      if (panelId === undefined) continue
      const list = out.get(panelId)
      if (list) list.push(finding)
      else out.set(panelId, [finding])
    }
  }
  return out
}

function comicDialogueLines(panel: Json): string[] {
  const items = asArray(get(panel, 'dialogue'))
  if (!items) return []
  const out: string[] = []
  for (const item of items) {
    const text = s(item, 'text')
    if (text === undefined) continue
    const speaker = s(item, 'speaker') ?? ''
    out.push(speaker.trim() === '' ? text : `${speaker}: ${text}`)
  }
  return out
}

/** Reverse of comicDialogueLines: "说话人：台词" lines → dialogue objects. */
function comicDialogueFromText(input: string): Json[] {
  return input
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line !== '')
    .map((line) => {
      const obj: Record<string, Json> = {}
      let idx = line.indexOf('：')
      if (idx < 0) idx = line.indexOf(':')
      if (idx >= 0) {
        const speaker = line.slice(0, idx).trim()
        const text = line.slice(idx + 1).trim()
        if (speaker !== '') obj['speaker'] = speaker
        obj['text'] = text
      } else {
        obj['text'] = line
      }
      return obj
    })
}

function setDialogueField(obj: Record<string, Json>, input: string): void {
  const values = comicDialogueFromText(input)
  if (values.length === 0) delete obj['dialogue']
  else obj['dialogue'] = values
}

function comicPanelSizeLabel(job: Json | undefined): string | undefined {
  const size = get(job, 'size')
  const w = iVal(size, 'width')
  const h = iVal(size, 'height')
  if (w === undefined || h === undefined) return undefined
  return `${w}x${h}`
}

function comicPanelPrompt(panel: Json, job: Json | undefined): string | undefined {
  const parts: string[] = []
  const desc = s(panel, 'description')
  if (desc !== undefined) parts.push(`description: ${desc}`)
  const notes = s(panel, 'art_notes')
  if (notes !== undefined) parts.push(`art_notes: ${notes}`)
  const dialogue = comicDialogueLines(panel)
  if (dialogue.length > 0) parts.push(`dialogue: ${dialogue.join(' / ')}`)
  const narration = s(panel, 'narration')
  if (narration !== undefined && narration.trim() !== '') parts.push(`narration: ${narration}`)
  const sfx = stringArray(panel, 'sfx', 12)
  if (sfx.length > 0) parts.push(`sfx: ${sfx.join(' / ')}`)
  const jobPrompt = s(job, 'prompt')
  if (jobPrompt !== undefined) parts.push(`image_prompt: ${shortText(jobPrompt, 1200)}`)
  const negative = s(job, 'negative_prompt')
  if (negative !== undefined) parts.push(`negative_prompt: ${shortText(negative, 600)}`)
  if (parts.length === 0) return undefined
  return shortText(parts.join('\n'), CANVAS_PROMPT_PREVIEW_LIMIT)
}

function acceptedManualReview(qc: Json): boolean {
  const status = s(get(qc, 'manual_review'), 'status')
  if (status === undefined) return false
  const lower = status.toLowerCase()
  return lower === 'accepted' || lower === 'pass'
}

function pushComicQcFlags(flags: QaFlag[], qc: Json | undefined): void {
  if (qc === undefined) return
  const accepted = acceptedManualReview(qc)
  const verdict = s(qc, 'verdict') ?? 'info'
  const issues = asArray(get(qc, 'issues'))
  if (issues) {
    for (const issue of issues) {
      flags.push({
        severity: accepted ? 'info' : (s(issue, 'severity') ?? verdict),
        status: accepted ? 'accepted' : verdict,
        dimension: s(issue, 'category') ?? 'panel_qc',
        message: s(issue, 'reason') ?? s(issue, 'message'),
      })
    }
  }
  if (verdict !== 'pass' && flags.length === 0) {
    flags.push({
      severity: accepted ? 'info' : verdict,
      status: s(qc, 'verdict'),
      dimension: 'panel_qc',
      message: '面板后检未通过或需要复核',
    })
  }
  if ((asBool(get(qc, 'manual_review_required')) ?? false) && !accepted) {
    flags.push({
      severity: 'warn',
      status: 'manual_review_required',
      dimension: 'panel_qc',
      message: '需要人工复核',
    })
  }
}

function pushComicFindingFlags(flags: QaFlag[], findings: Json[] | undefined): void {
  if (!findings) return
  for (const finding of findings) {
    flags.push({
      severity: s(finding, 'severity') ?? 'warn',
      status: s(finding, 'status'),
      dimension: s(finding, 'dimension') ?? s(finding, 'code') ?? 'consistency',
      message: s(finding, 'reason') ?? s(finding, 'suggested_fix') ?? s(finding, 'message'),
    })
  }
}

function qaCounts(qa: QaFlag[]): { blocks: number; warnings: number; infos: number } {
  const count = (sev: string): number =>
    qa.filter((f) => f.severity.toLowerCase() === sev || f.status === sev).length
  return { blocks: count('block'), warnings: count('warn'), infos: count('info') }
}

async function fromComicPanelScript(root: string, ep: string, data: Json): Promise<CanvasClip[]> {
  const panels = asArray(get(data, 'panels')) ?? []
  const jobs = await comicPanelJobs(root, ep)
  const findings = await comicFindingsByPanel(root, ep)
  const clips: CanvasClip[] = []
  for (let i = 0; i < panels.length; i++) {
    const panel = panels[i]
    const panelId = s(panel, 'panel_id') ?? `P${pad3(i + 1)}`
    const job = jobs.get(panelId)
    const qc = await comicPanelQc(root, ep, panelId, job)
    const prompt = comicPanelPrompt(panel, job)
    const imageRel = s(job, 'result_path') ?? s(qc, 'path') ?? `出图/${ep}/panels/${panelId}.png`
    const { abs: imageAbs, exists: imageExists } = relAbs(root, imageRel)
    const frames: CanvasFrame[] = [
      {
        role: 'panel',
        label: '成图',
        abs: imageAbs,
        exists: imageExists,
        revision: mediaRevision(imageAbs),
        at_sec: undefined,
        prompt,
      },
      ...comicReferenceFrames(root, panel, job),
    ]
    const qa: QaFlag[] = []
    pushComicQcFlags(qa, qc)
    pushComicFindingFlags(qa, findings.get(panelId))
    const status = s(job, 'status')
    if (status !== undefined && status !== 'ready' && status !== 'done' && status !== 'pass') {
      qa.push({
        severity: 'warn',
        status,
        dimension: 'image_job',
        message: `出图任务状态：${status}`,
      })
    }
    const { blocks: qaBlocks, warnings: qaWarnings, infos: qaInfos } = qaCounts(qa)
    const score =
      qaBlocks > 0
        ? 50.0
        : qaWarnings > 0
          ? 75.0
          : imageExists || qc !== undefined
            ? 100.0
            : undefined
    clips.push({
      id: panelId,
      number: numberFromId(panelId) ?? i + 1,
      label: s(panel, 'story_function') ?? panelId,
      duration: undefined,
      scene: s(panel, 'location'),
      rhythm: s(panel, 'story_function'),
      template: comicPanelSizeLabel(job),
      first_frame_abs: imageAbs,
      first_frame_exists: imageExists,
      video_abs: undefined,
      video_exists: false,
      video_revision: undefined,
      frames,
      prompt,
      qa,
      score,
      qa_blocks: qaBlocks,
      qa_warnings: qaWarnings,
      qa_infos: qaInfos,
    })
  }
  return clips
}

// ---------------------------------------------------------- review_ui source

function insertClipKey(lookup: Map<string, string>, key: string, id: string): void {
  const k = key.trim()
  if (k === '' || id.trim() === '') return
  if (!lookup.has(k)) lookup.set(k, id)
}

function resolveSeamEndpoint(
  raw: string | undefined,
  fallbackIdx: number,
  clips: CanvasClip[],
  lookup: Map<string, string>
): string | undefined {
  if (raw !== undefined) {
    const hit = lookup.get(raw.trim())
    if (hit !== undefined) return hit
  }
  const clip = clips[fallbackIdx]
  if (clip !== undefined && clip.id.trim() !== '') return clip.id
  return undefined
}

function reviewSeamsFromClips(clips: CanvasClip[], data: Json): CanvasSeam[] {
  const lookup = new Map<string, string>()
  for (const clip of clips) {
    insertClipKey(lookup, clip.id, clip.id)
    insertClipKey(lookup, clip.label, clip.id)
    if (clip.number !== undefined) {
      insertClipKey(lookup, String(clip.number), clip.id)
      insertClipKey(lookup, `Clip_${pad2(clip.number)}`, clip.id)
      insertClipKey(lookup, `Clip${pad2(clip.number)}`, clip.id)
    }
  }

  const seams: CanvasSeam[] = []
  const seen = new Set<string>()
  const arr = asArray(get(data, 'seams'))
  if (arr) {
    arr.forEach((sm, idx) => {
      const rawIndex = iVal(sm, 'index')
      const baseIdx = rawIndex !== undefined && rawIndex > 0 ? rawIndex - 1 : idx
      const from = resolveSeamEndpoint(s(sm, 'from'), baseIdx, clips, lookup)
      const to = resolveSeamEndpoint(s(sm, 'to'), baseIdx + 1, clips, lookup)
      if (from !== undefined && to !== undefined && from !== to && !seen.has(`${from}->${to}`)) {
        seen.add(`${from}->${to}`)
        seams.push({ from, to, transition: s(sm, 'transition') })
      }
    })
  }

  if (seams.length === 0) {
    for (let i = 0; i + 1 < clips.length; i++) {
      seams.push({ from: clips[i].id, to: clips[i + 1].id, transition: undefined })
    }
  }
  return seams
}

function fromReviewUi(root: string, data: Json): { clips: CanvasClip[]; seams: CanvasSeam[] } {
  const raw = asArray(get(data, 'clips')) ?? []
  const clips: CanvasClip[] = raw.map((c) => {
    const prompt = clipPrompt(c)
    const frames = reviewFrames(root, c)
    const ff = get(c, 'first_frame')
    const { abs: ffAbs, exists: ffExistsByPath } = relAbs(root, s(ff, 'path'))
    const video = get(c, 'video')
    const { abs: vidAbs, exists: vidExistsByPath } = relAbs(root, s(video, 'path'))
    const qa: QaFlag[] = (asArray(get(c, 'qa_flags')) ?? []).map((f) => ({
      severity: s(f, 'severity') ?? 'info',
      status: s(f, 'status'),
      dimension: s(f, 'dimension'),
      message: s(f, 'message'),
      score: nF64(f, 'score'),
    }))
    const { blocks: qaBlocks, warnings: qaWarnings, infos: qaInfos } = qaCounts(qa)
    let score: number | undefined
    for (const f of qa) {
      if (f.score !== undefined) score = score === undefined ? f.score : Math.min(score, f.score)
    }
    return {
      id: s(c, 'id') ?? '',
      number: iVal(c, 'number'),
      label: s(c, 'label') ?? '',
      duration: nF64(c, 'duration'),
      scene: s(c, 'scene'),
      rhythm: s(c, 'rhythm'),
      template: s(c, 'template'),
      first_frame_abs: ffAbs,
      first_frame_exists: asBool(get(ff, 'exists')) ?? ffExistsByPath,
      video_abs: vidAbs,
      video_exists: asBool(get(video, 'exists')) ?? vidExistsByPath,
      video_revision: mediaRevision(vidAbs),
      frames,
      prompt,
      qa,
      score,
      qa_blocks: qaBlocks,
      qa_warnings: qaWarnings,
      qa_infos: qaInfos,
    }
  })
  return { clips, seams: reviewSeamsFromClips(clips, data) }
}

// ------------------------------------------------------------ quality (n2d)

function scoreDimension(raw: Json): CanvasScoreDimension {
  const evidence: string[] = []
  const arr = asArray(get(raw, 'evidence'))
  if (arr) {
    for (const x of arr) {
      if (typeof x === 'string') {
        evidence.push(shortText(x, 180))
        if (evidence.length >= 4) break
      }
    }
  }
  const rerun = s(raw, 'rerun_scope')
  return {
    key: s(raw, 'key') ?? s(raw, 'dim_key'),
    label: s(raw, 'label') ?? s(raw, 'dim') ?? '未命名维度',
    status: s(raw, 'status'),
    score: nF64(raw, 'score'),
    blocks: Math.max(nI64(raw, 'blocks'), nI64(raw, 'block')),
    warnings: Math.max(nI64(raw, 'warnings'), nI64(raw, 'warn')),
    infos: Math.max(nI64(raw, 'infos'), nI64(raw, 'info')),
    return_to_stage: s(raw, 'return_to_stage'),
    rerun_scope: rerun === undefined ? undefined : shortText(rerun, 260),
    evidence,
  }
}

function scoreDimensions(scoreData: Json | undefined): CanvasScoreDimension[] {
  const arr = asArray(get(scoreData, 'dimensions'))
  if (!arr) return []
  const dims = arr.map(scoreDimension)
  dims.sort(
    (a, b) =>
      b.blocks - a.blocks || b.warnings - a.warnings || (a.score ?? 999) - (b.score ?? 999)
  )
  return dims
}

function returnTasks(scoreData: Json | undefined): CanvasReturnTask[] {
  const arr = asArray(get(scoreData, 'auto_return_tasks'))
  if (!arr) return []
  return arr.slice(0, 8).map((raw) => {
    const scope = s(raw, 'scope')
    return {
      return_to_stage: s(raw, 'return_to_stage'),
      scope: scope === undefined ? undefined : shortText(scope, 360),
      affected_shots: stringArray(raw, 'affected_shots', 12),
      dimensions: stringArray(raw, 'dimensions', 8),
    }
  })
}

function pushMetric(
  metrics: CanvasMetric[],
  alerts: Json,
  label: string,
  key: string,
  suffix: string
): void {
  const value = valueLabel(get(alerts, key))
  if (value !== undefined) metrics.push({ label, value: `${value}${suffix}` })
}

function pushRateMetric(metrics: CanvasMetric[], alerts: Json, label: string, key: string): void {
  const value = get(alerts, key)
  if (typeof value === 'number' && Number.isFinite(value)) {
    metrics.push({ label, value: `${(value * 100).toFixed(1)}%` })
  }
}

async function dashboardMetrics(root: string, ep: string): Promise<CanvasMetric[]> {
  const dash = await readJson(path.join(root, '生产数据', 'dashboard.json'))
  const alerts = get(dash, 'alert_counts')
  if (alerts === undefined) return []
  const alertsEpisode = s(alerts, 'episode')
  if (alertsEpisode !== undefined && alertsEpisode !== ep) return []
  const metrics: CanvasMetric[] = []
  pushRateMetric(metrics, alerts, '成品通过率', 'final_pass_rate')
  pushRateMetric(metrics, alerts, '生成通过率', 'generation_pass_rate')
  pushMetric(metrics, alerts, 'QA阻断', 'qa_blockers', '')
  pushMetric(metrics, alerts, 'QA警告', 'qa_warnings', '')
  pushMetric(metrics, alerts, '一致性阻断', 'consistency_blockers', '')
  pushMetric(metrics, alerts, '一致性警告', 'consistency_warnings', '')
  pushMetric(metrics, alerts, '重抽次数', 'redraw_count', '')
  const costs = get(alerts, 'cost_totals')
  if (isObj(costs)) {
    // serde_json maps iterate key-sorted; keep the same "first two" selection.
    for (const unit of Object.keys(costs).sort().slice(0, 2)) {
      const v = valueLabel(costs[unit])
      if (v !== undefined) metrics.push({ label: `成本 ${unit}`, value: v })
    }
  }
  const stage = s(alerts, 'progress_next_stage')
  if (stage !== undefined) metrics.push({ label: '下一阶段', value: stage })
  return metrics
}

async function qualitySummary(
  root: string,
  ep: string,
  reviewData: Json | undefined
): Promise<CanvasQualitySummary | undefined> {
  const rawReviewScore = get(reviewData, 'score')
  const scoreFromReview = isObj(rawReviewScore) ? rawReviewScore : undefined
  const scoreFromFile = await readJson(path.join(root, '生产数据', `score_${ep}.json`))
  const scoreData = scoreFromReview !== undefined ? scoreFromReview : scoreFromFile
  const findings = await readJson(path.join(root, '生产数据', `review_ui_findings_${ep}.json`))
  const dimensions = scoreDimensions(scoreData)
  const findingsSev = get(get(findings, 'summary'), 'severity')
  const hasSev = findingsSev !== undefined
  const blocks = hasSev
    ? nI64(findingsSev, 'block')
    : dimensions.reduce((acc, d) => acc + d.blocks, 0)
  const warnings = hasSev
    ? nI64(findingsSev, 'warn')
    : dimensions.reduce((acc, d) => acc + d.warnings, 0)
  const infos = hasSev
    ? nI64(findingsSev, 'info')
    : dimensions.reduce((acc, d) => acc + d.infos, 0)
  const score =
    scoreData === undefined
      ? undefined
      : (nF64(scoreData, 'total_score') ?? nF64(scoreData, 'overall_score') ?? nF64(scoreData, 'score'))
  const metrics = await dashboardMetrics(root, ep)
  const scoreSource = s(scoreData, 'source')
  if (scoreSource !== undefined) metrics.push({ label: '评分来源', value: scoreSource })
  const status =
    s(scoreData, 'status') ??
    (blocks > 0
      ? 'block'
      : warnings > 0
        ? 'warn'
        : scoreData !== undefined || findings !== undefined
          ? 'pass'
          : undefined)
  if (scoreData === undefined && findings === undefined && metrics.length === 0) return undefined
  return {
    source:
      scoreFromReview !== undefined
        ? 'review_ui.score'
        : scoreFromFile !== undefined
          ? `生产数据/score_${ep}.json`
          : findings !== undefined
            ? `生产数据/review_ui_findings_${ep}.json`
            : undefined,
    score,
    verdict: s(scoreData, 'verdict'),
    status,
    blocks,
    warnings,
    infos,
    dimensions,
    tasks: returnTasks(scoreData),
    metrics,
  }
}

// ---------------------------------------------------------- quality (comic)

function summaryCount(data: Json | undefined, key: string): number {
  const summary = get(data, 'summary')
  if (summary === undefined) return 0
  return Math.max(
    nI64(summary, key),
    nI64(summary, key.replace('_count', '')),
    nI64(summary, key.replace('block_count', 'block')),
    nI64(summary, key.replace('warn_count', 'warn')),
    nI64(summary, key.replace('info_count', 'info'))
  )
}

function scoreFromStatus(blocks: number, warnings: number, complete: boolean): number | undefined {
  if (blocks > 0) return 50.0
  if (warnings > 0) return 75.0
  if (complete) return 100.0
  return undefined
}

function comicReturnTasksFromFindings(findings: Json | undefined): CanvasReturnTask[] {
  const items = asArray(get(findings, 'findings'))
  if (!items) return []
  return items.slice(0, 12).map((item) => {
    const scope = s(item, 'suggested_fix') ?? s(item, 'reason')
    const panelId = s(item, 'panel_id')
    const dim = s(item, 'dimension') ?? s(item, 'code')
    return {
      return_to_stage: s(item, 'return_to_stage') ?? 'image',
      scope: scope === undefined ? undefined : shortText(scope, 360),
      affected_shots: panelId === undefined ? [] : [panelId],
      dimensions: dim === undefined ? [] : [dim],
    }
  })
}

async function comicQualitySummary(
  root: string,
  ep: string,
  clips: CanvasClip[]
): Promise<CanvasQualitySummary | undefined> {
  if (clips.length === 0) return undefined
  const style = await readJson(path.join(root, '生产数据', `comic_style_consistency_${ep}.json`))
  const findings = await readJson(path.join(root, '生产数据', `consistency_findings_style_${ep}.json`))
  const identity = await readJson(path.join(root, '生产数据', `comic_identity_report_${ep}.json`))
  const jobs = await readJson(path.join(root, '出图', ep, 'prompt', 'panel_jobs.json'))

  const panelCount = clips.length
  const imageCount = clips.filter((clip) => clip.first_frame_exists).length
  const clipBlocks = clips.reduce((acc, clip) => acc + clip.qa_blocks, 0)
  const clipWarnings = clips.reduce((acc, clip) => acc + clip.qa_warnings, 0)
  const clipInfos = clips.reduce((acc, clip) => acc + clip.qa_infos, 0)
  const styleBlocks = Math.max(summaryCount(style, 'block_count'), summaryCount(findings, 'block_count'))
  const styleWarnings = Math.max(summaryCount(style, 'warn_count'), summaryCount(findings, 'warn_count'))
  const styleInfos = Math.max(summaryCount(style, 'info_count'), summaryCount(findings, 'info_count'))
  const identitySummary = get(identity, 'summary')
  const missingRefs = identitySummary === undefined ? 0 : nI64(identitySummary, 'missing_ref_count')
  const rerunTargets = identitySummary === undefined ? 0 : nI64(identitySummary, 'rerun_target_count')

  const blocks = Math.max(clipBlocks, styleBlocks, missingRefs)
  const warnings = Math.max(clipWarnings, styleWarnings, rerunTargets)
  const infos = Math.max(clipInfos, styleInfos)
  const complete = imageCount === panelCount && panelCount > 0 && blocks === 0 && warnings === 0
  const status = blocks > 0 ? 'block' : warnings > 0 ? 'warn' : complete ? 'pass' : 'draft'

  const dimensions: CanvasScoreDimension[] = []
  dimensions.push({
    key: 'panel_qc',
    label: '单格后检',
    status,
    score: scoreFromStatus(clipBlocks, clipWarnings, imageCount > 0),
    blocks: clipBlocks,
    warnings: clipWarnings,
    infos: clipInfos,
    return_to_stage: clipBlocks > 0 || clipWarnings > 0 ? 'image' : undefined,
    rerun_scope: undefined,
    evidence: [`生产数据/panel_qc/${ep}/`, `出图/${ep}/prompt/panel_jobs.json`],
  })
  if (style !== undefined || findings !== undefined) {
    const firstFinding = asArray(get(findings, 'findings'))?.[0]
    const rerunScope =
      firstFinding === undefined
        ? undefined
        : (s(firstFinding, 'suggested_fix') ?? s(firstFinding, 'reason'))
    dimensions.push({
      key: 'style_consistency',
      label: '风格一致性',
      status: s(style, 'verdict') ?? s(findings, 'verdict'),
      score: scoreFromStatus(styleBlocks, styleWarnings, true),
      blocks: styleBlocks,
      warnings: styleWarnings,
      infos: styleInfos,
      return_to_stage: styleBlocks > 0 || styleWarnings > 0 ? 'image' : undefined,
      rerun_scope: rerunScope === undefined ? undefined : shortText(rerunScope, 260),
      evidence: [
        `生产数据/comic_style_consistency_${ep}.json`,
        `生产数据/consistency_findings_style_${ep}.json`,
      ],
    })
  }
  if (identity !== undefined) {
    dimensions.push({
      key: 'identity_references',
      label: '角色参考完整性',
      status: missingRefs > 0 ? 'block' : rerunTargets > 0 ? 'warn' : 'pass',
      score: scoreFromStatus(missingRefs, rerunTargets, true),
      blocks: missingRefs,
      warnings: rerunTargets,
      infos: 0,
      return_to_stage: missingRefs > 0 || rerunTargets > 0 ? 'image' : undefined,
      rerun_scope: undefined,
      evidence: [`生产数据/comic_identity_report_${ep}.json`],
    })
  }

  const metrics: CanvasMetric[] = [
    { label: '分格', value: String(panelCount) },
    { label: '已出图', value: String(imageCount) },
    { label: '待出图', value: String(Math.max(panelCount - imageCount, 0)) },
  ]
  const model = s(jobs, 'model')
  if (model !== undefined) metrics.push({ label: '出图模型', value: model })
  if (existsSync(path.join(root, '生产数据', `panel_contact_sheet_${ep}.jpg`))) {
    metrics.push({ label: '联络图', value: '已生成' })
  }

  return {
    source: `脚本/${ep}/panel_script.json`,
    score: scoreFromStatus(blocks, warnings, complete),
    verdict: status,
    status,
    blocks,
    warnings,
    infos,
    dimensions,
    tasks: comicReturnTasksFromFindings(findings),
    metrics,
  }
}

// ------------------------------------------------------------ canvas assembly

async function buildCanvas(root: string, ep: string): Promise<CanvasData> {
  const out: CanvasData = {
    source: 'none',
    episode: ep,
    episodes: await listEpisodes(root),
    shared_assets: await sharedAssetFrames(root),
    generation_profile: await generationProfile(root, ep),
    clips: [],
    seams: [],
  }

  // 1) review_ui_第N集.json (preferred — has QA + score)
  const review = await readJson(path.join(root, '生产数据', `review_ui_${ep}.json`))
  if (review !== undefined) {
    const { clips, seams } = fromReviewUi(root, review)
    out.source = 'review_ui'
    out.title = s(get(review, 'storyboard'), 'title')
    out.total_duration = nF64(get(review, 'storyboard'), 'total_duration')
    out.quality = await qualitySummary(root, ep, review)
    out.clips = clips
    out.seams = seams
    return out
  }

  // 2) storyboard.json fallback
  const sb = await readJson(path.join(root, '脚本', ep, 'storyboard.json'))
  if (sb !== undefined) {
    const clips = fromStoryboard(root, ep, sb)
    out.seams = seamsFromClips(clips, sb)
    out.title = s(sb, 'title')
    out.total_duration = nF64(sb, 'total_duration')
    out.source = 'storyboard'
    out.clips = clips
    out.quality = await qualitySummary(root, ep, undefined)
    return out
  }

  // 3) comic panel_script.json fallback (画漫画: panels + optional panel jobs/QC)
  const panelScript = await readJson(path.join(root, '脚本', ep, 'panel_script.json'))
  if (panelScript !== undefined) {
    const clips = await fromComicPanelScript(root, ep, panelScript)
    out.seams = sequentialSeams(clips, '下一格')
    out.title = s(panelScript, 'title')
    out.source = 'panel_script'
    out.quality = await comicQualitySummary(root, ep, clips)
    out.clips = clips
    return out
  }

  return out
}

// Single-flight：生成高峰期 fs watcher 每 300ms 一批事件，上一趟 buildCanvas 的目录
// 扫描还没跑完下一趟又进来会重叠烧 I/O；同 (root, ep) 的并发读合并到同一次构建。
const buildInflight = new Map<string, Promise<{ data: CanvasData; sig: string }>>()

function buildCanvasWithSig(root: string, ep: string): Promise<{ data: CanvasData; sig: string }> {
  const key = `${root}\0${ep}`
  const existing = buildInflight.get(key)
  if (existing) return existing
  const task = (async () => {
    let data: CanvasData
    try {
      data = await buildCanvas(root, ep)
    } catch {
      data = { source: 'none', episode: ep, episodes: [], shared_assets: [], clips: [], seams: [] }
    }
    const sig = fnv1a64(Buffer.from(JSON.stringify(data), 'utf8'))
    return { data, sig }
  })().finally(() => {
    buildInflight.delete(key)
  })
  buildInflight.set(key, task)
  return task
}

/** 画布数据 + 内容签名。renderer 带上一次的 sig 来读：未变更时只回 `{ sig, unchanged }`，
 *  省掉整棵 CanvasData 的 IPC 结构化克隆与 renderer 侧反序列化——fs watcher 的多数事件
 *  （终端输出/临时文件）与画布无关，这条短路是画布不卡的主保障。签名在主进程算
 *  （fnv1a64 over JSON），renderer 不再自己 stringify 大 payload。 */
export async function readCanvas(root: string, ep: string, knownSig?: string): Promise<CanvasReadResult> {
  const { data, sig } = await buildCanvasWithSig(root, ep)
  if (knownSig && knownSig === sig) return { sig, unchanged: true }
  return { sig, canvas: data }
}

export async function readEpisodeWorkspace(
  root: string,
  ep: string
): Promise<EpisodeWorkspace | null> {
  try {
    validateEpisodeName(ep)
  } catch {
    return null
  }
  const data = await readJson(path.join(root, '生产数据', 'episodes', `${ep}.json`))
  return (data ?? null) as EpisodeWorkspace | null
}

// -------------------------------------------------------------- canvas layout

/** Strict-ish CanvasLayout parse mirroring the Rust serde struct (extras dropped). */
function parseCanvasLayout(txt: string): CanvasLayout {
  let raw: Json
  try {
    raw = JSON.parse(txt) as Json
  } catch {
    throw new Error('画布布局文件解析失败')
  }
  const version = get(raw, 'version')
  const episode = get(raw, 'episode')
  const updatedAt = get(raw, 'updated_at_epoch_ms')
  const rawNodes = get(raw, 'nodes')
  if (
    !isObj(raw) ||
    typeof version !== 'number' ||
    !Number.isInteger(version) ||
    version < 0 ||
    typeof episode !== 'string' ||
    typeof updatedAt !== 'number' ||
    !Number.isInteger(updatedAt) ||
    updatedAt < 0 ||
    !Array.isArray(rawNodes)
  ) {
    throw new Error('画布布局文件格式非法')
  }
  const nodes: CanvasNodePosition[] = rawNodes.map((n) => {
    const id = get(n, 'id')
    const x = get(n, 'x')
    const y = get(n, 'y')
    if (typeof id !== 'string' || typeof x !== 'number' || typeof y !== 'number') {
      throw new Error('画布布局文件格式非法')
    }
    return { id, x, y }
  })
  return { version, episode, updated_at_epoch_ms: updatedAt, nodes }
}

export async function readCanvasLayout(root: string, ep: string): Promise<CanvasLayout> {
  const file = canvasLayoutReadPath(root, ep)
  let isFile = false
  try {
    isFile = statSync(file).isFile()
  } catch {
    isFile = false
  }
  if (!isFile) {
    return { version: 1, episode: ep, updated_at_epoch_ms: 0, nodes: [] }
  }
  const layout = parseCanvasLayout(await fs.readFile(file, 'utf8'))
  if (layout.episode === '') layout.episode = ep
  return layout
}

export async function writeCanvasLayout(
  root: string,
  ep: string,
  nodes: CanvasNodePosition[]
): Promise<void> {
  validateEpisodeName(ep)
  const file = path.join(await productionDirForWrite(root), `canvas_layout_${ep}.json`)
  const seen = new Set<string>()
  const clean: CanvasNodePosition[] = []
  for (const n of nodes) {
    if (clean.length >= 2_000) break
    if (n.id.trim() === '' || !Number.isFinite(n.x) || !Number.isFinite(n.y) || seen.has(n.id)) {
      continue
    }
    seen.add(n.id)
    clean.push({ id: n.id, x: n.x, y: n.y })
  }
  const layout: CanvasLayout = {
    version: 1,
    episode: ep,
    updated_at_epoch_ms: Date.now(),
    nodes: clean,
  }
  await fs.writeFile(file, `${JSON.stringify(layout, null, 2)}\n`, 'utf8')
}

// ---------------------------------------------------- generation controls

function generationControlsPath(root: string, ep: string): string {
  validateEpisodeName(ep)
  return path.join(realWorkRoot(root), '生产数据', `canvas_generation_controls_${ep}.json`)
}

function cleanGenerationString(value: Json, fallback: string, max = 120): string {
  return typeof value === 'string' && value.trim()
    ? Array.from(value.trim()).slice(0, max).join('')
    : fallback
}

function cleanGenerationList(value: Json, maxItems: number): string[] {
  if (!Array.isArray(value)) return []
  const out: string[] = []
  for (const item of value) {
    if (typeof item !== 'string') continue
    const clean = Array.from(item.trim()).slice(0, 100).join('')
    if (!clean || out.includes(clean)) continue
    out.push(clean)
    if (out.length >= maxItems) break
  }
  return out
}

function cleanGenerationReference(root: string, value: string): string | null {
  const base = realWorkRoot(root)
  let candidate: string
  try {
    candidate = path.isAbsolute(value) ? path.resolve(value) : resolveWithin(base, value)
    if (!existsSync(candidate) || !statSync(candidate).isFile()) return null
    const real = realpathSync(candidate)
    const relativeReal = path.relative(base, real)
    if (relativeReal === '' || relativeReal.startsWith('..') || path.isAbsolute(relativeReal)) return null
    return path.relative(base, candidate).replaceAll('\\', '/')
  } catch {
    return null
  }
}

function sanitizeGenerationConfig(root: string, raw: Json): CanvasGenerationConfig {
  const kind: CanvasGenerationKind = get(raw, 'kind') === 'video' ? 'video' : 'image'
  const rawCount = nI64(raw, 'count')
  const count: 1 | 2 | 4 = rawCount === 2 || rawCount === 4 ? rawCount : 1
  const rawDuration = nF64(raw, 'duration') ?? 10
  const referencePaths = cleanGenerationList(get(raw, 'reference_paths'), 24)
    .map((item) => cleanGenerationReference(root, item))
    .filter((item): item is string => item !== null)
  const promptLanguage = get(raw, 'prompt_language')
  return {
    kind,
    model: cleanGenerationString(get(raw, 'model'), 'project-default'),
    mode: cleanGenerationString(get(raw, 'mode'), kind === 'video' ? 'project_route' : 'text2image'),
    aspect_ratio: cleanGenerationString(get(raw, 'aspect_ratio'), 'Auto', 20),
    resolution: cleanGenerationString(get(raw, 'resolution'), kind === 'video' ? '720p' : 'project', 24),
    duration: Math.round(Math.max(1, Math.min(60, rawDuration)) * 10) / 10,
    audio_enabled: kind === 'video' && Boolean(asBool(get(raw, 'audio_enabled'))),
    count,
    reference_paths: referencePaths,
    marks: cleanGenerationList(get(raw, 'marks'), 12),
    effects: cleanGenerationList(get(raw, 'effects'), 12),
    camera_motion: cleanGenerationString(get(raw, 'camera_motion'), 'none', 40),
    prompt_language: promptLanguage === 'zh' || promptLanguage === 'en' ? promptLanguage : 'project',
    prompt_override: cleanGenerationString(get(raw, 'prompt_override'), '', 12_000),
  }
}

export async function readCanvasGenerationConfig(
  root: string,
  ep: string,
  clipId: string,
  kind: CanvasGenerationKind
): Promise<CanvasGenerationConfig | null> {
  if (!clipId.trim() || clipId.length > 240) throw new Error('非法节点 ID')
  const data = await readJson(generationControlsPath(root, ep))
  const raw = get(get(data, 'configs'), `${kind}:${clipId}`)
  if (!isObj(raw)) return null
  return sanitizeGenerationConfig(root, { ...raw, kind })
}

export async function writeCanvasGenerationConfig(
  root: string,
  ep: string,
  clipId: string,
  config: CanvasGenerationConfig
): Promise<CanvasGenerationConfig> {
  if (!clipId.trim() || clipId.length > 240) throw new Error('非法节点 ID')
  const clean = sanitizeGenerationConfig(root, config)
  await productionDirForWrite(root)
  const file = generationControlsPath(root, ep)
  const current = await readJson(file)
  const configs = isObj(get(current, 'configs')) ? { ...(get(current, 'configs') as Record<string, Json>) } : {}
  configs[`${clean.kind}:${clipId}`] = {
    ...clean,
    updated_at: new Date().toISOString(),
  }
  const payload = {
    kind: 'anime_armory_canvas_generation_controls',
    version: 1,
    episode: ep,
    updated_at: new Date().toISOString(),
    configs,
  }
  const temp = `${file}.${process.pid}.${Date.now()}.tmp`
  await fs.writeFile(temp, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
  await fs.rename(temp, file)
  return clean
}

// ------------------------------------------------------------------ clip edit

/** Locate a clip/panel by id → panel_id → number → id-suffix heuristics. */
function findClipIndex(clips: Json[], clipId: string, number: number | undefined): number {
  for (const key of ['id', 'panel_id']) {
    const idx = clips.findIndex((c) => s(c, key) === clipId)
    if (idx >= 0) return idx
  }
  if (number !== undefined) {
    const byNumber = clips.findIndex((c) => iVal(c, 'number') === number)
    if (byNumber >= 0) return byNumber
    const needle = pad2(number)
    return clips.findIndex((c) => {
      const id = s(c, 'id')
      const panelId = s(c, 'panel_id')
      return (
        (id !== undefined && (id.endsWith(needle) || id.includes(`CLIP${needle}`))) ||
        (panelId !== undefined &&
          (panelId.endsWith(needle) || panelId === `P${pad3(number)}` || panelId === `P${needle}`))
      )
    })
  }
  return -1
}

function setStringField(
  obj: Record<string, Json>,
  key: string,
  value: string,
  removeEmpty: boolean
): void {
  if (removeEmpty && value.trim() === '') delete obj[key]
  else obj[key] = value
}

function splitListText(input: string): string[] {
  return input
    .split(/[\n,，、;；]/)
    .map((part) => part.trim())
    .filter((part) => part !== '')
}

function setStringArrayField(obj: Record<string, Json>, key: string, input: string): void {
  const values = splitListText(input)
  if (values.length === 0) delete obj[key]
  else obj[key] = values
}

const IMAGE_PACK_REL = (ep: string): string[] => ['出图', ep, 'prompt', '01_分镜出图.md']
const VIDEO_PACK_REL = (ep: string): string[] => ['出视频', ep, 'prompt', '01_clips.md']

async function readStoryboardClipEdit(
  root: string,
  file: string,
  ep: string,
  clipId: string,
  number: number | undefined
): Promise<ClipEditData> {
  const data = JSON.parse(await fs.readFile(file, 'utf8')) as Json
  const clips = asArray(get(data, 'clips'))
  if (!clips) throw new Error('storyboard.json 缺 clips 数组')
  const idx = findClipIndex(clips, clipId, number)
  if (idx < 0) throw new Error('找不到对应 Clip，未写入')
  const clip = clips[idx]
  const clipNumber = iVal(clip, 'number') ?? number
  const clipIdentifier = valueString(clip, 'id')
  const imagePositive = await readClipPromptPack(root, IMAGE_PACK_REL(ep), clipIdentifier, clipNumber, [
    '正向 prompt（中文',
    '正向 prompt (中文',
  ])
  const imageNegative = await readClipPromptPack(root, IMAGE_PACK_REL(ep), clipIdentifier, clipNumber, [
    '负向 prompt',
  ])
  const videoPrompt =
    (await readClipPromptPack(root, VIDEO_PACK_REL(ep), clipIdentifier, clipNumber, [
      '视频 prompt（中文',
      '视频 prompt (中文',
    ])) ?? storyboardShotVideoPrompt(clip)
  return {
    source_rel: `脚本/${ep}/storyboard.json`,
    id: clipIdentifier,
    number: clipNumber ?? null,
    label: valueString(clip, 'label'),
    duration: nF64(clip, 'duration') ?? null,
    scene: valueString(clip, 'scene'),
    rhythm: valueString(clip, 'rhythm'),
    template: valueString(clip, 'template'),
    prompt: valueStringOr(clip, 'prompt', clipPrompt(clip) ?? storyboardShotText(clip)),
    image_prompt: valueStringOr(clip, 'image_prompt', imagePositive),
    video_prompt: valueStringOr(clip, 'video_prompt', videoPrompt),
    positive_prompt: valueStringOr(clip, 'positive_prompt', imagePositive),
    negative_prompt: valueStringOr(clip, 'negative_prompt', imageNegative),
  }
}

async function readPanelClipEdit(
  file: string,
  ep: string,
  clipId: string,
  number: number | undefined
): Promise<ClipEditData> {
  const data = JSON.parse(await fs.readFile(file, 'utf8')) as Json
  const panels = asArray(get(data, 'panels'))
  if (!panels) throw new Error('panel_script.json 缺 panels 数组')
  const idx = findClipIndex(panels, clipId, number)
  if (idx < 0) throw new Error('找不到对应分格，未写入')
  const panel = panels[idx]
  const panelId = valueString(panel, 'panel_id')
  // Panel-field mapping: the generic ClipEdit form edits comic-panel fields
  // (template↔characters, prompt↔description, image_prompt↔art_notes,
  //  video_prompt↔narration, positive↔dialogue, negative↔sfx).
  return {
    source_rel: `脚本/${ep}/panel_script.json`,
    id: panelId,
    number: numberFromId(panelId) ?? number ?? null,
    label: valueString(panel, 'story_function'),
    duration: null,
    scene: valueString(panel, 'location'),
    rhythm: valueString(panel, 'story_function'),
    template: stringArray(panel, 'characters', 20).join('、'),
    prompt: valueString(panel, 'description'),
    image_prompt: valueString(panel, 'art_notes'),
    video_prompt: valueString(panel, 'narration'),
    positive_prompt: comicDialogueLines(panel).join('\n'),
    negative_prompt: stringArray(panel, 'sfx', 20).join('、'),
  }
}

export async function readClipEdit(
  root: string,
  ep: string,
  clipId: string,
  num?: number | null
): Promise<ClipEditData> {
  const number = num ?? undefined
  const sb = storyboardPath(root, ep)
  if (sb !== null) return readStoryboardClipEdit(root, sb, ep, clipId, number)
  const ps = panelScriptPath(root, ep)
  if (ps !== null) return readPanelClipEdit(ps, ep, clipId, number)
  throw new Error('找不到 storyboard.json 或 panel_script.json')
}

function normalizePatch(patch: Partial<ClipEditPatch>): ClipEditPatch {
  return {
    label: patch.label ?? '',
    duration: patch.duration ?? null,
    scene: patch.scene ?? '',
    rhythm: patch.rhythm ?? '',
    template: patch.template ?? '',
    prompt: patch.prompt ?? '',
    image_prompt: patch.image_prompt ?? '',
    video_prompt: patch.video_prompt ?? '',
    positive_prompt: patch.positive_prompt ?? '',
    negative_prompt: patch.negative_prompt ?? '',
  }
}

async function writeStoryboardClipEdit(
  file: string,
  root: string,
  ep: string,
  clipId: string,
  number: number | undefined,
  patch: ClipEditPatch
): Promise<ClipEditData> {
  const data = JSON.parse(await fs.readFile(file, 'utf8')) as Json
  const clips = asArray(get(data, 'clips'))
  if (!clips) throw new Error('storyboard.json 缺 clips 数组')
  const idx = findClipIndex(clips, clipId, number)
  if (idx < 0) throw new Error('找不到对应 Clip，未写入')
  const clip = clips[idx]
  if (!isObj(clip)) throw new Error('Clip 不是对象，未写入')

  if (patch.label.trim() === '') throw new Error('标题不能为空')
  setStringField(clip, 'label', patch.label.trim(), false)
  const duration = patch.duration
  if (typeof duration === 'number' && Number.isFinite(duration) && duration > 0) {
    clip['duration'] = duration
  } else {
    delete clip['duration']
  }
  setStringField(clip, 'scene', patch.scene.trim(), true)
  setStringField(clip, 'rhythm', patch.rhythm.trim(), true)
  setStringField(clip, 'template', patch.template.trim(), true)
  setStringField(clip, 'prompt', patch.prompt.trim(), true)
  setStringField(clip, 'image_prompt', patch.image_prompt.trim(), true)
  setStringField(clip, 'video_prompt', patch.video_prompt.trim(), true)
  setStringField(clip, 'positive_prompt', patch.positive_prompt.trim(), true)
  setStringField(clip, 'negative_prompt', patch.negative_prompt.trim(), true)

  await fs.writeFile(file, `${JSON.stringify(data, null, 2)}\n`, 'utf8')
  return readClipEdit(root, ep, clipId, number)
}

async function writePanelClipEdit(
  file: string,
  root: string,
  ep: string,
  clipId: string,
  number: number | undefined,
  patch: ClipEditPatch
): Promise<ClipEditData> {
  const data = JSON.parse(await fs.readFile(file, 'utf8')) as Json
  const panels = asArray(get(data, 'panels'))
  if (!panels) throw new Error('panel_script.json 缺 panels 数组')
  const idx = findClipIndex(panels, clipId, number)
  if (idx < 0) throw new Error('找不到对应分格，未写入')
  const panel = panels[idx]
  if (!isObj(panel)) throw new Error('分格不是对象，未写入')

  const storyFunction = patch.label.trim() === '' ? patch.rhythm.trim() : patch.label.trim()
  if (storyFunction.trim() === '') throw new Error('分格功能不能为空')
  setStringField(panel, 'story_function', storyFunction.trim(), false)
  setStringField(panel, 'location', patch.scene.trim(), true)
  setStringArrayField(panel, 'characters', patch.template.trim())
  setStringField(panel, 'description', patch.prompt.trim(), true)
  setStringField(panel, 'art_notes', patch.image_prompt.trim(), true)
  setStringField(panel, 'narration', patch.video_prompt.trim(), true)
  setDialogueField(panel, patch.positive_prompt.trim())
  setStringArrayField(panel, 'sfx', patch.negative_prompt.trim())

  await fs.writeFile(file, `${JSON.stringify(data, null, 2)}\n`, 'utf8')
  return readClipEdit(root, ep, clipId, number)
}

export async function writeClipEdit(
  root: string,
  ep: string,
  clipId: string,
  num: number | null | undefined,
  patch: Partial<ClipEditPatch>
): Promise<ClipEditData> {
  const number = num ?? undefined
  const full = normalizePatch(patch)
  const sb = storyboardPath(root, ep)
  if (sb !== null) return writeStoryboardClipEdit(sb, root, ep, clipId, number, full)
  const ps = panelScriptPath(root, ep)
  if (ps !== null) return writePanelClipEdit(ps, root, ep, clipId, number, full)
  throw new Error('找不到 storyboard.json 或 panel_script.json')
}
