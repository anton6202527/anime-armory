import fs from 'node:fs/promises'
import path from 'node:path'
import type { QualityInsights, QualityInsightDimension } from '@shared/types'

/**
 * Quality insights aggregator — TypeScript port of the Tauri
 * `read_quality_insights` command (desktop/src-tauri/src/commands.rs).
 *
 * novel line: 评分/score_report.json + 审稿/review_report.json +
 * 合规/compliance_profile.json(.md) + 生产数据/novel_dashboard.json + visuals.
 * other lines: 生产数据/dashboard.json + yield_summary.json + prefixed
 * finding JSONs under 生产数据/ (episode-filtered).
 */

type Json = unknown

interface CatalogArtifact {
  path?: string
  name?: string
  extension?: string
  role?: string
  unit?: string
  status?: string
  size_bytes?: number
  disposable?: boolean
}

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

/** Mirrors Rust `n_f64()`: numeric field or undefined. */
function nF64(v: Json, k: string): number | undefined {
  const x = get(v, k)
  return typeof x === 'number' && Number.isFinite(x) ? x : undefined
}

/** Mirrors Rust `n_i64()`: integer field or 0 (serde_json as_i64 is None for floats). */
function nI64(v: Json, k: string): number {
  const x = get(v, k)
  return typeof x === 'number' && Number.isInteger(x) ? x : 0
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

async function pathExists(file: string): Promise<boolean> {
  try {
    await fs.stat(file)
    return true
  } catch {
    return false
  }
}

async function isFile(file: string): Promise<boolean> {
  try {
    return (await fs.stat(file)).isFile()
  } catch {
    return false
  }
}

// ---------------------------------------------------------- text/label utils

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
    return Math.abs(value % 1) < Number.EPSILON
      ? String(Math.trunc(value))
      : value.toFixed(2)
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

function ratioMetric(value: number | undefined): string | undefined {
  return value === undefined ? undefined : `${(value * 100).toFixed(1)}%`
}

function scoreLabel(value: number | undefined): string | undefined {
  if (value === undefined) return undefined
  return Math.abs(value % 1) < Number.EPSILON
    ? String(Math.trunc(value))
    : value.toFixed(1)
}

function bytesLabel(value: number | undefined): string | undefined {
  if (value === undefined || !Number.isFinite(value)) return undefined
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let amount = Math.max(0, value)
  let idx = 0
  while (amount >= 1024 && idx < units.length - 1) {
    amount /= 1024
    idx += 1
  }
  return `${amount >= 10 || idx === 0 ? amount.toFixed(0) : amount.toFixed(1)} ${units[idx]}`
}

// ----------------------------------------------------------- tone/status law

function severityTone(raw: string | undefined): string {
  const value = (raw ?? 'info').toLowerCase()
  if (
    value.includes('block') ||
    value.includes('blocking') ||
    value === 'critical' ||
    value === 'error' ||
    value === 'fail' ||
    value === 'failed'
  ) {
    return 'block'
  }
  if (
    value.includes('warn') ||
    value === 'action_required' ||
    value === 'needs_revision' ||
    value === 'suggestion' ||
    value === 'should'
  ) {
    return 'warn'
  }
  if (value === 'pass' || value === 'ok' || value === 'done' || value === 'accepted') {
    return 'pass'
  }
  return 'info'
}

function statusFromCounts(
  blocks: number,
  warnings: number,
  score: number | undefined,
): string | undefined {
  if (blocks > 0) return 'block'
  if (warnings > 0) return 'warn'
  if (score !== undefined) return 'pass'
  return undefined
}

function scoreFromStatus(
  blocks: number,
  warnings: number,
  complete: boolean,
): number | undefined {
  if (blocks > 0) return 50.0
  if (warnings > 0) return 75.0
  if (complete) return 100.0
  return undefined
}

// -------------------------------------------------------------- accumulators

function pushInsightMetric(
  out: QualityInsights,
  label: string,
  value: string | undefined,
  tone?: string,
): void {
  if (value === undefined || !value.trim()) return
  out.metrics.push({ label, value, tone })
}

async function pushInsightArtifact(
  out: QualityInsights,
  root: string,
  label: string,
  rel: string,
  kind: string,
): Promise<void> {
  if (!rel.trim()) return
  const exists = await pathExists(path.join(root, rel))
  out.artifacts.push({ label, path: rel, exists, kind })
}

async function pushSourceFile(
  out: QualityInsights,
  root: string,
  rel: string,
  label: string,
): Promise<boolean> {
  if (await isFile(path.join(root, rel))) {
    if (!out.source_files.includes(rel)) out.source_files.push(rel)
    await pushInsightArtifact(out, root, label, rel, 'evidence')
    return true
  }
  return false
}

function insightCountsFromSummary(
  summary: Json,
): [blocks: number, warnings: number, infos: number] {
  if (summary === undefined || summary === null) return [0, 0, 0]
  const sev = get(summary, 'severity')
  const blocks = Math.max(
    sev !== undefined ? nI64(sev, 'block') : 0,
    nI64(summary, 'block'),
    nI64(summary, 'blocks'),
    nI64(summary, 'block_count'),
    nI64(summary, 'blocking_count'),
    nI64(summary, 'qa_blockers'),
    nI64(summary, 'consistency_blockers'),
  )
  const warnings = Math.max(
    sev !== undefined ? nI64(sev, 'warn') : 0,
    nI64(summary, 'warn'),
    nI64(summary, 'warnings'),
    nI64(summary, 'warn_count'),
    nI64(summary, 'warning_count'),
    nI64(summary, 'suggestion_count'),
    nI64(summary, 'qa_warnings'),
    nI64(summary, 'consistency_warnings'),
  )
  const infos = Math.max(
    sev !== undefined ? nI64(sev, 'info') : 0,
    nI64(summary, 'infos'),
    nI64(summary, 'info_count'),
    nI64(summary, 'polish_count'),
  )
  return [blocks, warnings, infos]
}

function pushTaskFromValue(out: QualityInsights, raw: Json): void {
  const title =
    s(raw, 'action') ??
    s(raw, 'title') ??
    s(raw, 'scope') ??
    s(raw, 'fix_hint') ??
    s(raw, 'suggested_fix') ??
    '未命名返工任务'
  const detail =
    s(raw, 'dimension') ?? s(raw, 'reason') ?? s(raw, 'message')
  out.tasks.push({
    priority: s(raw, 'priority'),
    title: shortText(title, 180),
    skill: s(raw, 'recommended_skill') ?? s(raw, 'skill'),
    stage: s(raw, 'return_to_stage') ?? s(raw, 'stage'),
    detail: detail !== undefined ? shortText(detail, 260) : undefined,
  })
}

function pushIssueFromValue(out: QualityInsights, raw: Json): void {
  const severity =
    asBool(get(raw, 'blocking')) === true
      ? 'block'
      : severityTone(s(raw, 'severity') ?? s(raw, 'sev') ?? s(raw, 'status'))
  const title =
    s(raw, 'problem') ??
    s(raw, 'reason') ??
    s(raw, 'message') ??
    s(raw, 'msg') ??
    s(raw, 'code') ??
    s(raw, 'id') ??
    '未命名问题'
  const affectedFirst = asArray(get(raw, 'affected_files'))?.[0]
  const issuePath =
    s(raw, 'loc') ??
    s(raw, 'path') ??
    s(raw, 'artifact') ??
    (typeof affectedFirst === 'string' ? affectedFirst : undefined)
  const message =
    s(raw, 'fix_hint') ??
    s(raw, 'suggested_fix') ??
    s(raw, 'evidence') ??
    s(raw, 'rerun_scope')
  out.issues.push({
    severity,
    dimension: s(raw, 'dimension') ?? s(raw, 'dim') ?? s(raw, 'category'),
    title: shortText(title, 160),
    message: message !== undefined ? shortText(message, 280) : undefined,
    stage: s(raw, 'return_to_stage') ?? s(raw, 'gate_stage'),
    path: issuePath,
    source: s(raw, 'source'),
  })
}

function pushDimensionsFromByDim(
  out: QualityInsights,
  sourceLabel: string,
  byDim: Json,
): void {
  if (!isObj(byDim)) return
  const dims: QualityInsightDimension[] = Object.entries(byDim).map(
    ([key, raw]) => {
      const blocks = Math.max(nI64(raw, 'block'), nI64(raw, 'blocks'))
      const warnings = Math.max(
        nI64(raw, 'warn'),
        nI64(raw, 'warning'),
        nI64(raw, 'warnings'),
      )
      const infos = Math.max(nI64(raw, 'info'), nI64(raw, 'infos'))
      return {
        key,
        label: key,
        score: scoreFromStatus(blocks, warnings, true),
        value: `${blocks}/${warnings}/${infos}`,
        max: 100.0,
        status: statusFromCounts(blocks, warnings, 100.0),
        blocks,
        warnings,
        infos,
        detail: 'block / warn / info',
        evidence: [sourceLabel],
      }
    },
  )
  dims.sort(
    (a, b) => b.blocks - a.blocks || b.warnings - a.warnings || b.infos - a.infos,
  )
  out.dimensions.push(...dims.slice(0, 14))
}

function collectTasksFromArray(
  out: QualityInsights,
  data: Json,
  key: string,
  limit: number,
): void {
  const items = asArray(get(data, key))
  if (!items) return
  for (const item of items.slice(0, limit)) pushTaskFromValue(out, item)
}

function collectIssuesFromArray(
  out: QualityInsights,
  data: Json,
  key: string,
  limit: number,
): void {
  const items = asArray(get(data, key))
  if (!items) return
  for (const item of items.slice(0, limit)) pushIssueFromValue(out, item)
}

// ------------------------------------------------------------- novel branch

async function collectNovelScore(root: string, out: QualityInsights): Promise<void> {
  const rel = '评分/score_report.json'
  const scoreData = await readJson(path.join(root, rel))
  if (scoreData === undefined) return
  await pushSourceFile(out, root, rel, '小说评分')
  out.score =
    nF64(scoreData, 'total_score') ?? nF64(scoreData, 'overall_score') ?? out.score
  out.verdict = s(scoreData, 'verdict') ?? out.verdict
  out.status = s(scoreData, 'production_decision') ?? out.status
  pushInsightMetric(out, '评分档', s(scoreData, 'target_platform'))
  pushInsightMetric(out, '评分', scoreLabel(out.score), 'pass')
  pushInsightMetric(out, '判定', s(scoreData, 'verdict'))
  const scope = get(scoreData, 'scope')
  if (scope !== undefined) {
    const chapterCount = get(scope, 'chapter_count')
    pushInsightMetric(
      out,
      '章节数',
      chapterCount !== undefined ? valueLabel(chapterCount) : undefined,
    )
  }
  const scores = asArray(get(scoreData, 'scores'))
  if (scores) {
    for (const item of scores.slice(0, 12)) {
      const label = s(item, 'dimension_label') ?? s(item, 'dimension') ?? '评分维度'
      const score = nF64(item, 'raw_score') ?? nF64(item, 'score')
      const evidence: string[] = []
      const ev = s(item, 'evidence')
      if (ev !== undefined) evidence.push(shortText(ev, 180))
      const improve = s(item, 'improve_by')
      if (improve !== undefined) evidence.push(shortText(improve, 180))
      const warn = (score ?? 10.0) < 7.0 ? 1 : 0
      const weighted = nF64(item, 'weighted_score')
      const comment = s(item, 'comment')
      out.dimensions.push({
        key: s(item, 'dimension'),
        label,
        score,
        value: weighted !== undefined ? `加权 ${weighted.toFixed(1)}` : undefined,
        max: 10.0,
        status: statusFromCounts(0, warn, score),
        blocks: 0,
        warnings: warn,
        infos: 0,
        detail: comment !== undefined ? shortText(comment, 260) : undefined,
        evidence,
      })
    }
  }
  const checks: Array<[string, string]> = [
    ['title_check', '标题侧'],
    ['adaptation_check', '转制潜力'],
  ]
  for (const [key, label] of checks) {
    const check = get(scoreData, key)
    if (!isObj(check)) continue
    const score = nF64(check, 'total')
    const max = nF64(check, 'max_total')
    const riskyRaw =
      get(check, 'needs_rename') !== undefined
        ? get(check, 'needs_rename')
        : get(check, 'low_potential')
    const risky = asBool(riskyRaw) ?? false
    const comment = s(check, 'comment')
    out.dimensions.push({
      key,
      label,
      score,
      value: max !== undefined ? `/ ${max.toFixed(0)}` : undefined,
      max,
      status: risky ? 'warn' : 'pass',
      blocks: 0,
      warnings: risky ? 1 : 0,
      infos: 0,
      detail: comment !== undefined ? shortText(comment, 280) : undefined,
      evidence: [rel],
    })
  }
  const prior = get(scoreData, 'repetition_prior')
  if (prior !== undefined) {
    const level =
      s(get(prior, 'prior'), 'level') ?? s(get(prior, 'summary'), 'prior_level')
    pushInsightMetric(out, '重复/机械先验', level)
    const summary = get(prior, 'summary')
    if (summary !== undefined) {
      const jaccard = nF64(summary, 'adjacent_max_jaccard')
      pushInsightMetric(
        out,
        '相邻最高重复',
        jaccard !== undefined ? `${(jaccard * 100).toFixed(2)}%` : undefined,
      )
      const lowComp = get(summary, 'low_chapter_compression_count')
      pushInsightMetric(
        out,
        '低压缩章节',
        lowComp !== undefined ? valueLabel(lowComp) : undefined,
      )
    }
  }
  const deductions = asArray(get(scoreData, 'deductions'))
  if (deductions) {
    for (const item of deductions.slice(0, 6)) {
      const reason = s(item, 'reason')
      out.issues.push({
        severity: 'warn',
        dimension: 'score_deduction',
        title: s(item, 'item') ?? '扣分项',
        message: reason !== undefined ? shortText(reason, 260) : undefined,
        stage: 'score',
        path: rel,
        source: 'novel-score',
      })
    }
  }
  collectTasksFromArray(out, scoreData, 'next_actions', 8)
}

async function collectNovelReview(root: string, out: QualityInsights): Promise<void> {
  const rel = '审稿/review_report.json'
  const reviewData = await readJson(path.join(root, rel))
  if (reviewData === undefined) return
  await pushSourceFile(out, root, rel, '小说审稿')
  const summary = get(reviewData, 'summary')
  if (summary !== undefined) {
    const blocks = Math.max(nI64(summary, 'blocking_count'), nI64(summary, 'block_count'))
    const warnings = Math.max(
      nI64(summary, 'suggestion_count'),
      nI64(summary, 'warning_count'),
    )
    const infos = Math.max(nI64(summary, 'polish_count'), nI64(summary, 'info_count'))
    out.blocks += blocks
    out.warnings += warnings
    out.infos += infos
    out.dimensions.push({
      key: 'novel_review',
      label: '审稿问题',
      score: scoreFromStatus(blocks, warnings, true),
      value: `${blocks + warnings + infos} 项`,
      max: 100.0,
      status: s(summary, 'verdict') ?? statusFromCounts(blocks, warnings, 100.0),
      blocks,
      warnings,
      infos,
      detail: 'blocking / suggestion / polish',
      evidence: [rel],
    })
  }
  collectIssuesFromArray(out, reviewData, 'findings', 12)
  collectTasksFromArray(out, reviewData, 'next_actions', 8)
}

async function collectNovelCompliance(
  root: string,
  out: QualityInsights,
): Promise<void> {
  const rel = '合规/compliance_profile.json'
  const data = await readJson(path.join(root, rel))
  if (data === undefined) {
    await pushSourceFile(out, root, '合规/compliance_profile.md', '合规 Profile')
    return
  }
  await pushSourceFile(out, root, rel, '合规 Profile')
  const blocking = get(data, 'blocking')
  pushInsightMetric(
    out,
    '合规阻断',
    blocking !== undefined ? valueLabel(blocking) : undefined,
  )
  const warning = get(data, 'warning')
  pushInsightMetric(
    out,
    '合规提醒',
    warning !== undefined ? valueLabel(warning) : undefined,
  )
  const axes = get(data, 'target_axes')
  if (isObj(axes)) {
    const enabled = Object.entries(axes)
      .filter(([, value]) => asBool(value) === true)
      .map(([key]) => key)
    if (enabled.length > 0) pushInsightMetric(out, '发布轴', enabled.join(' / '))
  }
  const reqs = asArray(get(data, 'requirements'))
  if (reqs) {
    for (const req of reqs.slice(0, 12)) {
      const status = s(req, 'status')
      const severity = s(req, 'severity')
      const ok =
        status !== undefined &&
        (status === 'ok' || status === 'pass' || status === 'done' || status === 'confirmed')
      const tone = ok ? 'pass' : severityTone(severity ?? status)
      const blocks = tone === 'block' ? 1 : 0
      const warnings = tone === 'warn' ? 1 : 0
      out.blocks += blocks
      out.warnings += warnings
      const reason = s(req, 'reason')
      out.dimensions.push({
        key: s(req, 'id'),
        label: s(req, 'title') ?? s(req, 'id') ?? '合规项',
        score: scoreFromStatus(blocks, warnings, true),
        value: status,
        max: 100.0,
        status: tone,
        blocks,
        warnings,
        infos: tone === 'info' ? 1 : 0,
        detail: reason !== undefined ? shortText(reason, 260) : undefined,
        evidence: stringArray(req, 'evidence_source_ids', 4),
      })
      if (tone !== 'pass') {
        out.issues.push({
          severity: tone,
          dimension: 'compliance',
          title: s(req, 'title') ?? s(req, 'id') ?? '合规待办',
          message: reason !== undefined ? shortText(reason, 280) : undefined,
          stage: 'release',
          path: rel,
          source: 'compliance_profile',
        })
      }
    }
  }
}

async function collectNovelDashboard(
  root: string,
  out: QualityInsights,
): Promise<void> {
  const rel = '生产数据/novel_dashboard.json'
  const data = await readJson(path.join(root, rel))
  if (data === undefined) return
  await pushSourceFile(out, root, rel, '小说看板')
  const stageCounts = get(data, 'stage_counts')
  if (isObj(stageCounts)) {
    for (const [key, value] of Object.entries(stageCounts)) {
      pushInsightMetric(out, `阶段 ${key}`, valueLabel(value))
    }
  }
  const release = get(data, 'release')
  if (release !== undefined) {
    const readyBool = asBool(get(release, 'release_ready'))
    const ready =
      readyBool === undefined ? undefined : readyBool ? 'ready' : 'not ready'
    pushInsightMetric(out, '导出状态', ready)
    const blockers = nI64(release, 'blocker_count')
    out.blocks += blockers
    pushInsightMetric(out, '导出阻断', String(blockers))
  }
  const revision = get(data, 'revision')
  if (revision !== undefined) {
    const taskCount = get(revision, 'task_count')
    pushInsightMetric(
      out,
      '修订任务',
      taskCount !== undefined ? valueLabel(taskCount) : undefined,
    )
    const conflicts = get(revision, 'conflicts')
    pushInsightMetric(
      out,
      '修订冲突',
      conflicts !== undefined ? valueLabel(conflicts) : undefined,
    )
  }
  const visualRels = [
    '生产数据/novel_dashboard.html',
    '生产数据/visuals/novel_review_heatmap.html',
    '生产数据/visuals/novel_revision_kanban.html',
    '生产数据/visuals/novel_emotion_curve.html',
    '生产数据/visuals/novel_foreshadow_ledger.html',
    '生产数据/visuals/novel_relationship_timeline.html',
  ]
  for (const visualRel of visualRels) {
    const base = visualRel.split('/').pop() ?? visualRel
    await pushInsightArtifact(out, root, base, visualRel, 'visual')
  }
}

// ----------------------------------------------------------- generic branch

function selectDashboardEpisode(data: Json, ep: string | undefined): Json {
  const episodes = asArray(get(data, 'episodes'))
  if (!episodes) return undefined
  if (ep !== undefined) {
    const found = episodes.find((item) => s(item, 'episode') === ep)
    if (found !== undefined) return found
  }
  return episodes.length > 0 ? episodes[episodes.length - 1] : undefined
}

async function collectDashboardInsights(
  root: string,
  out: QualityInsights,
  ep: string | undefined,
): Promise<void> {
  const rel = '生产数据/dashboard.json'
  const data = await readJson(path.join(root, rel))
  if (data === undefined) return
  await pushSourceFile(out, root, rel, '生产看板')
  const epData = selectDashboardEpisode(data, ep)
  if (epData !== undefined) {
    out.episode = s(epData, 'episode') ?? out.episode
    pushInsightMetric(out, '成品通过率', ratioMetric(nF64(epData, 'final_pass_rate')))
    pushInsightMetric(
      out,
      '生成通过率',
      ratioMetric(nF64(epData, 'generation_pass_rate')),
    )
    const attempts = get(epData, 'generation_attempts')
    pushInsightMetric(
      out,
      '尝试',
      attempts !== undefined ? valueLabel(attempts) : undefined,
    )
    const redraws = get(epData, 'redraw_count')
    pushInsightMetric(out, '重抽', redraws !== undefined ? valueLabel(redraws) : undefined)
    pushInsightMetric(out, '耗时', s(epData, 'duration_hms'))
    const costs = get(epData, 'cost_totals')
    if (isObj(costs)) {
      for (const [unit, value] of Object.entries(costs).slice(0, 3)) {
        pushInsightMetric(out, `成本 ${unit}`, valueLabel(value))
      }
    }
    const qaBlocks = nI64(epData, 'qa_blockers')
    const qaWarnings = nI64(epData, 'qa_warnings')
    const consistencyBlocks = nI64(epData, 'consistency_blockers')
    const consistencyWarnings = nI64(epData, 'consistency_warnings')
    out.blocks += qaBlocks + consistencyBlocks
    out.warnings += qaWarnings + consistencyWarnings
    const finalRate = nF64(epData, 'final_pass_rate')
    out.dimensions.push({
      key: 'final_pass_rate',
      label: '成片通过率',
      score: finalRate !== undefined ? finalRate * 100.0 : undefined,
      value: ratioMetric(finalRate),
      max: 100.0,
      status: statusFromCounts(qaBlocks, qaWarnings, 100.0),
      blocks: qaBlocks,
      warnings: qaWarnings,
      infos: 0,
      detail: 'QA blockers / warnings',
      evidence: [rel],
    })
    const genRate = nF64(epData, 'generation_pass_rate')
    out.dimensions.push({
      key: 'generation_pass_rate',
      label: '生成通过率',
      score: genRate !== undefined ? genRate * 100.0 : undefined,
      value: ratioMetric(genRate),
      max: 100.0,
      status: statusFromCounts(0, nI64(epData, 'generation_fails'), 100.0),
      blocks: 0,
      warnings: nI64(epData, 'generation_fails'),
      infos: 0,
      detail: 'generation_passes / generation_attempts',
      evidence: [rel],
    })
    out.dimensions.push({
      key: 'consistency',
      label: '一致性',
      score: scoreFromStatus(consistencyBlocks, consistencyWarnings, true),
      value: `${consistencyBlocks}/${consistencyWarnings}`,
      max: 100.0,
      status: statusFromCounts(consistencyBlocks, consistencyWarnings, 100.0),
      blocks: consistencyBlocks,
      warnings: consistencyWarnings,
      infos: 0,
      detail: 'consistency blockers / warnings',
      evidence: [rel],
    })
  } else {
    const alerts = get(data, 'alert_counts')
    if (alerts !== undefined) {
      const [blocks, warnings, infos] = insightCountsFromSummary(alerts)
      out.blocks += blocks
      out.warnings += warnings
      out.infos += infos
      pushInsightMetric(out, '成品通过率', ratioMetric(nF64(alerts, 'final_pass_rate')))
      pushInsightMetric(
        out,
        '生成通过率',
        ratioMetric(nF64(alerts, 'generation_pass_rate')),
      )
      pushInsightMetric(out, '下一阶段', s(alerts, 'progress_next_stage'))
    }
  }
}

async function collectYieldInsights(root: string, out: QualityInsights): Promise<void> {
  const rel = '生产数据/yield_summary.json'
  const data = await readJson(path.join(root, rel))
  if (data === undefined) return
  await pushSourceFile(out, root, rel, '出图产能')
  pushInsightMetric(out, '可用率', ratioMetric(nF64(data, 'usable_yield')))
  pushInsightMetric(out, '重抽率', ratioMetric(nF64(data, 'reroll_rate')))
  const candidates = get(data, 'total_candidates')
  pushInsightMetric(
    out,
    '候选数',
    candidates !== undefined ? valueLabel(candidates) : undefined,
  )
  const usable = nF64(data, 'usable_yield')
  const warn = (usable ?? 1.0) < 0.8 ? 1 : 0
  out.dimensions.push({
    key: 'usable_yield',
    label: '候选可用率',
    score: usable !== undefined ? usable * 100.0 : undefined,
    value: ratioMetric(usable),
    max: 100.0,
    status: statusFromCounts(0, warn, 100.0),
    blocks: 0,
    warnings: warn,
    infos: 0,
    detail: 'survivors / candidates',
    evidence: [rel],
  })
}

async function collectArtifactCatalog(
  root: string,
  out: QualityInsights,
  ep: string | undefined,
): Promise<string[] | undefined> {
  const rel = '生产数据/artifact_catalog.json'
  const data = await readJson(path.join(root, rel))
  if (!isObj(data) || s(data, 'kind') !== 'artifact_catalog' || s(data, 'status') !== 'ready') {
    return undefined
  }
  const rawArtifacts = asArray(get(data, 'artifacts'))
  if (!rawArtifacts) return undefined
  await pushSourceFile(out, root, rel, '资产索引')
  const summary = get(data, 'summary')
  pushInsightMetric(out, '索引资产', valueLabel(get(summary, 'artifact_count')))
  pushInsightMetric(out, '作品占用', bytesLabel(nF64(summary, 'total_bytes')))
  pushInsightMetric(out, '可清理', bytesLabel(nF64(summary, 'disposable_bytes')))
  const invalid = nI64(summary, 'invalid_count')
  if (invalid > 0) {
    out.blocks += invalid
    out.issues.push({
      severity: 'block',
      dimension: 'artifact_integrity',
      title: `${invalid} 个无效资产`,
      message: 'artifact catalog 标记了零字节或无效生产产物，请先运行对应系列 doctor。',
      stage: 'production',
      path: rel,
      source: 'artifact_catalog',
    })
  }
  const qcPaths: string[] = []
  for (const raw of rawArtifacts) {
    if (!isObj(raw)) continue
    const artifact = raw as CatalogArtifact
    const artifactPath = typeof artifact.path === 'string' ? artifact.path : undefined
    if (!artifactPath || artifact.status === 'invalid') continue
    const unitMatches = ep === undefined || artifact.unit === undefined || artifact.unit === ep || artifactPath.includes(ep)
    if (!unitMatches) continue
    if (artifact.role === 'view') {
      await pushInsightArtifact(out, root, artifact.name ?? path.basename(artifactPath), artifactPath, 'visual')
    }
    if (artifact.role === 'qc' && artifact.extension === '.json') qcPaths.push(artifactPath)
  }
  return qcPaths.sort()
}

async function collectFindingJson(
  root: string,
  out: QualityInsights,
  rel: string,
  data: Json,
): Promise<void> {
  await pushSourceFile(out, root, rel, rel)
  const summary = get(data, 'summary')
  const [blocks, warnings, infos] = insightCountsFromSummary(summary)
  out.blocks += blocks
  out.warnings += warnings
  out.infos += infos
  if (blocks > 0 || warnings > 0 || infos > 0) {
    const base = rel.split('/').pop() ?? rel
    out.dimensions.push({
      key: rel,
      label: base.endsWith('.json') ? base.slice(0, -'.json'.length) : base,
      score: scoreFromStatus(blocks, warnings, true),
      value: `${blocks}/${warnings}/${infos}`,
      max: 100.0,
      status: statusFromCounts(blocks, warnings, 100.0),
      blocks,
      warnings,
      infos,
      detail: 'block / warn / info',
      evidence: [rel],
    })
  }
  pushDimensionsFromByDim(out, rel, get(summary, 'by_dim'))
  collectIssuesFromArray(out, data, 'findings', 10)
  collectIssuesFromArray(out, data, 'issues', 10)
  collectTasksFromArray(out, data, 'auto_return_tasks', 6)
  collectTasksFromArray(out, data, 'return_tasks', 6)
  collectTasksFromArray(out, data, 'next_actions', 6)
}

const PRODUCTION_JSON_PREFIXES = [
  'gate_findings',
  'review_ui_findings',
  'release_verdict',
  'comic_review',
  'comic_style_consistency',
  'comic_identity_report',
  'consistency_findings',
  'raw_bubble_acceptance',
  'style_consistency_acceptance',
  'image_qc',
  'video_qc',
  'score_',
]

function shouldCollectProductionJson(name: string, ep: string | undefined): boolean {
  if (!name.endsWith('.json')) return false
  if (!PRODUCTION_JSON_PREFIXES.some((prefix) => name.startsWith(prefix))) return false
  if (ep !== undefined && name.includes('第')) return name.includes(ep)
  return true
}

async function collectGenericProduction(
  root: string,
  out: QualityInsights,
  ep: string | undefined,
  catalogQcPaths: string[] | undefined,
): Promise<void> {
  await collectDashboardInsights(root, out, ep)
  await collectYieldInsights(root, out)
  let findingRels: string[] = []
  if (catalogQcPaths !== undefined) {
    findingRels = catalogQcPaths
  } else {
    const prod = path.join(root, '生产数据')
    let entries
    try {
      entries = await fs.readdir(prod, { withFileTypes: true })
    } catch {
      return
    }
    const names: string[] = []
    for (const entry of entries) {
      if (!shouldCollectProductionJson(entry.name, ep)) continue
      // Legacy fallback for projects without a ready artifact catalog.
      if (entry.isFile() || (await isFile(path.join(prod, entry.name)))) names.push(entry.name)
    }
    findingRels = names.sort().map((name) => `生产数据/${name}`)
  }
  for (const rel of findingRels.slice(0, 24)) {
    const data = await readJson(path.join(root, rel))
    if (data !== undefined) {
      await collectFindingJson(root, out, rel, data)
    }
  }
  const evidenceRels = [
    '合规/compliance_manifest.json',
    '合规/AI使用说明.md',
    '生产数据/dashboard.html',
    '生产数据/board.html',
    '生产数据/dashboard.md',
  ]
  for (const rel of evidenceRels) {
    const base = rel.split('/').pop() ?? rel
    await pushInsightArtifact(out, root, base, rel, 'evidence')
  }
}

// ------------------------------------------------------------------ finalize

function finalizeQualityInsights(out: QualityInsights): void {
  out.issues.length = Math.min(out.issues.length, 28)
  out.tasks.length = Math.min(out.tasks.length, 18)
  out.metrics.length = Math.min(out.metrics.length, 28)
  out.dimensions.sort(
    (a, b) =>
      b.blocks - a.blocks ||
      b.warnings - a.warnings ||
      (a.score ?? 999.0) - (b.score ?? 999.0),
  )
  out.dimensions.length = Math.min(out.dimensions.length, 24)
  const seen = new Set<string>()
  out.artifacts = out.artifacts.filter((item) => {
    if (seen.has(item.path)) return false
    seen.add(item.path)
    return true
  })
  out.artifacts.length = Math.min(out.artifacts.length, 24)
  if (out.status === undefined) {
    out.status = statusFromCounts(out.blocks, out.warnings, out.score)
  }
}

function validEpisodeName(ep: string): boolean {
  return !(
    !ep.trim() ||
    ep.includes('/') ||
    ep.includes('\\') ||
    ep.includes('\0')
  )
}

function emptyInsights(line: string, episode: string | undefined): QualityInsights {
  return {
    line,
    episode,
    status: undefined,
    score: undefined,
    verdict: undefined,
    blocks: 0,
    warnings: 0,
    infos: 0,
    metrics: [],
    dimensions: [],
    issues: [],
    tasks: [],
    artifacts: [],
    source_files: [],
  }
}

async function buildQualityInsights(
  root: string,
  line: string,
  ep: string | undefined,
): Promise<QualityInsights> {
  const cleanEp =
    ep !== undefined && validEpisodeName(ep) && ep.trim() ? ep : undefined
  const out = emptyInsights(line, cleanEp)
  const catalogQcPaths = await collectArtifactCatalog(root, out, cleanEp)
  if (line === 'novel') {
    await collectNovelScore(root, out)
    await collectNovelReview(root, out)
    await collectNovelCompliance(root, out)
    await collectNovelDashboard(root, out)
  } else {
    await collectGenericProduction(root, out, cleanEp, catalogQcPaths)
  }
  finalizeQualityInsights(out)
  return out
}

// ------------------------------------------------------------------- public

export async function readQualityInsights(
  root: string,
  line: string,
  ep?: string | null,
): Promise<QualityInsights> {
  const epValue = ep ?? undefined
  try {
    return await buildQualityInsights(root, line, epValue)
  } catch {
    const fallback = emptyInsights(line, epValue)
    fallback.status = 'error'
    return fallback
  }
}
