import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { mergeCanonicalClipsWithReview, readCanvas } from '../src/main/services/canvas.ts'
import type { CanvasClip, CanvasFrame } from '../src/shared/types.ts'

function frame(label: string, abs: string): CanvasFrame {
  return {
    role: 'first',
    label,
    abs,
    exists: true,
    revision: `revision:${label}`,
  }
}

function clip(overrides: Partial<CanvasClip> & Pick<CanvasClip, 'id' | 'number' | 'label'>): CanvasClip {
  return {
    duration: 8,
    scene: '新场景',
    rhythm: '新节奏',
    template: '新模板',
    first_frame_exists: false,
    video_exists: false,
    frames: [],
    prompt: '新 prompt',
    qa: [],
    qa_blocks: 0,
    qa_warnings: 0,
    qa_infos: 0,
    ...overrides,
  }
}

test('stale review projection cannot roll back canonical edits or shot order', () => {
  const canonical = [
    clip({ id: 'CLIP02', number: 2, label: '编辑后的第二镜', prompt: '第二镜新 prompt' }),
    clip({ id: 'CLIP01', number: 1, label: '编辑后的第一镜', duration: 12, prompt: '第一镜新 prompt' }),
  ]
  const review = [
    clip({
      id: 'CLIP01',
      number: 1,
      label: '过期的第一镜',
      duration: 3,
      scene: '过期场景',
      rhythm: '过期节奏',
      template: '过期模板',
      prompt: '过期 prompt',
      first_frame_abs: '/review/clip01.png',
      first_frame_exists: true,
      video_abs: '/review/clip01.mp4',
      video_exists: true,
      video_revision: 'video:clip01',
      frames: [frame('第一镜媒体', '/review/clip01.png')],
      qa: [{ severity: 'warn', dimension: 'continuity' }],
      score: 72,
      qa_warnings: 1,
    }),
    clip({
      id: 'CLIP02',
      number: 2,
      label: '过期的第二镜',
      prompt: '过期 prompt',
      first_frame_abs: '/review/clip02.png',
      first_frame_exists: true,
      frames: [frame('第二镜媒体', '/review/clip02.png')],
      qa: [{ severity: 'block', dimension: 'identity' }],
      score: 40,
      qa_blocks: 1,
    }),
  ]

  const merged = mergeCanonicalClipsWithReview(canonical, review)

  assert.deepEqual(merged.map((item) => item.id), ['CLIP02', 'CLIP01'])
  assert.deepEqual(merged.map((item) => item.label), ['编辑后的第二镜', '编辑后的第一镜'])
  assert.deepEqual(merged.map((item) => item.prompt), ['第二镜新 prompt', '第一镜新 prompt'])
  assert.equal(merged[1].duration, 12)
  assert.equal(merged[1].scene, '新场景')
  assert.equal(merged[0].first_frame_abs, '/review/clip02.png')
  assert.equal(merged[0].qa_blocks, 1)
  assert.equal(merged[1].video_abs, '/review/clip01.mp4')
  assert.equal(merged[1].qa_warnings, 1)
})

test('review media can match a renamed canonical clip by unique shot number', () => {
  const canonical = [clip({ id: 'RENAMED_CLIP', number: 7, label: '新镜头' })]
  const review = [clip({
    id: 'OLD_CLIP',
    number: 7,
    label: '旧镜头',
    first_frame_abs: '/review/clip07.png',
    first_frame_exists: true,
    frames: [frame('镜头七', '/review/clip07.png')],
    qa: [{ severity: 'info', dimension: 'review' }],
    qa_infos: 1,
  })]

  const [merged] = mergeCanonicalClipsWithReview(canonical, review)

  assert.equal(merged.id, 'RENAMED_CLIP')
  assert.equal(merged.label, '新镜头')
  assert.equal(merged.first_frame_abs, '/review/clip07.png')
  assert.equal(merged.qa_infos, 1)
})

test('ambiguous review numbers are not used as a positional fallback', () => {
  const canonical = [clip({ id: 'CANONICAL', number: 3, label: '权威镜头' })]
  const review = [
    clip({ id: 'OLD_A', number: 3, label: '旧 A', first_frame_abs: '/review/a.png', first_frame_exists: true }),
    clip({ id: 'OLD_B', number: 3, label: '旧 B', first_frame_abs: '/review/b.png', first_frame_exists: true }),
  ]

  const [merged] = mergeCanonicalClipsWithReview(canonical, review)

  assert.equal(merged.first_frame_abs, undefined)
  assert.equal(merged.label, '权威镜头')
})

test('projection source SHA-256 binds the exact storyboard bytes that were parsed', async (t) => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'canvas-projection-source-'))
  t.after(() => fs.rm(root, { recursive: true, force: true }))
  const episode = '第1集'
  const source = path.join(root, '脚本', episode, 'storyboard.json')
  await fs.mkdir(path.dirname(source), { recursive: true })
  const firstBytes = Buffer.from('{"title":"A","clips":[{"id":"C01","label":"first"}]}\n', 'utf8')
  const settingsBytes = Buffer.from('- 画幅：9:16\n- 视频分辨率：1080p\n', 'utf8')
  await fs.writeFile(source, firstBytes)
  await fs.writeFile(path.join(root, '_设置.md'), settingsBytes)

  const first = await readCanvas(root, episode, undefined, 'n2d')
  assert.equal(first.canvas?.title, 'A')
  assert.equal(
    first.canvas?.source_file_sha256,
    createHash('sha256').update(firstBytes).digest('hex'),
  )
  assert.equal(
    first.canvas?.settings_file_sha256,
    createHash('sha256').update(settingsBytes).digest('hex'),
  )

  const secondBytes = Buffer.from(' { "title": "B", "clips": [{"id":"C01","label":"second"}] }\n', 'utf8')
  await fs.writeFile(source, secondBytes)
  const second = await readCanvas(root, episode, undefined, 'n2d')
  assert.equal(second.canvas?.title, 'B')
  assert.equal(second.canvas?.clips[0]?.label, 'second')
  assert.equal(
    second.canvas?.source_file_sha256,
    createHash('sha256').update(secondBytes).digest('hex'),
  )
  assert.notEqual(second.canvas?.source_file_sha256, first.canvas?.source_file_sha256)
})

test('missing storyboard uses panel-script fallback and hashes its parsed bytes', async (t) => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'canvas-projection-fallback-'))
  t.after(() => fs.rm(root, { recursive: true, force: true }))
  const episode = '第1集'
  const scriptDir = path.join(root, '脚本', episode)
  await fs.mkdir(scriptDir, { recursive: true })
  const panelBytes = Buffer.from('{"title":"comic","panels":[{"panel_id":"P01","description":"panel"}]}\n')
  await fs.writeFile(path.join(scriptDir, 'panel_script.json'), panelBytes)

  const result = await readCanvas(root, episode, undefined, 'comic')
  assert.equal(result.canvas?.source, 'panel_script')
  assert.equal(
    result.canvas?.source_file_sha256,
    createHash('sha256').update(panelBytes).digest('hex'),
  )
})

test('same-time pathless anchors keep distinct ordinal target slots in projection', async (t) => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'canvas-projection-anchors-'))
  t.after(() => fs.rm(root, { recursive: true, force: true }))
  const episode = '第1集'
  const source = path.join(root, '脚本', episode, 'storyboard.json')
  await fs.mkdir(path.dirname(source), { recursive: true })
  await fs.writeFile(source, JSON.stringify({
    clips: [{
      id: 'C01',
      label: 'anchors',
      continuity: { anchors: [{ at_sec: 1 }, { at_sec: 1 }] },
    }],
  }))

  const result = await readCanvas(root, episode, undefined, 'n2d')
  const anchors = result.canvas?.clips[0]?.frames.filter((frame) => frame.role === 'anchor') ?? []
  assert.equal(anchors.length, 2)
  assert.notEqual(anchors[0].abs, anchors[1].abs)
  assert.ok(anchors[0].abs?.endsWith('/C01_anchor-2-t1000.png'))
  assert.ok(anchors[1].abs?.endsWith('/C01_anchor-3-t1000.png'))
})

test('non-missing project settings read errors are not silently treated as empty settings', async (t) => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'canvas-projection-settings-'))
  t.after(() => fs.rm(root, { recursive: true, force: true }))
  const episode = '第1集'
  await fs.mkdir(path.join(root, '脚本', episode), { recursive: true })
  await fs.writeFile(path.join(root, '脚本', episode, 'storyboard.json'), '{"clips":[]}')
  await fs.mkdir(path.join(root, '_设置.md'))

  await assert.rejects(readCanvas(root, episode, undefined, 'n2d'), (error: unknown) => {
    return (error as NodeJS.ErrnoException).code === 'EISDIR'
  })
})

test('invalid higher-priority canonical source fails closed instead of changing authority', async (t) => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'canvas-projection-invalid-source-'))
  t.after(() => fs.rm(root, { recursive: true, force: true }))
  const episode = '第1集'
  const scriptDir = path.join(root, '脚本', episode)
  await fs.mkdir(scriptDir, { recursive: true })
  await fs.writeFile(path.join(scriptDir, 'storyboard.json'), '{"clips": [')
  await fs.writeFile(path.join(scriptDir, 'panel_script.json'), JSON.stringify({
    panels: [{ panel_id: 'P001', description: 'must not become authority' }],
  }))

  await assert.rejects(readCanvas(root, episode, undefined, 'n2d'), SyntaxError)
})

test('intent recovery never consumes files owned by prefix-overlapping episodes', async (t) => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'canvas-intent-prefix-'))
  t.after(() => fs.rm(root, { recursive: true, force: true }))
  const episode = '第1集'
  const otherEpisodes = [
    `${episode}_特别篇`,
    `${episode}_123e4567-e89b-42d3-a456-426614174000`,
  ]
  await fs.mkdir(path.join(root, '脚本', episode), { recursive: true })
  await fs.writeFile(path.join(root, '脚本', episode, 'storyboard.json'), '{"clips":[]}')
  const productionDir = path.join(root, '生产数据')
  await fs.mkdir(productionDir, { recursive: true })

  const files: string[] = []
  for (const otherEpisode of otherEpisodes) {
    const file = path.join(productionDir, `canvas_generation_intent_${otherEpisode}.json`)
    files.push(file)
    await fs.writeFile(file, JSON.stringify({
      kind: 'anime_armory_canvas_generation_intent',
      version: 1,
      episode: otherEpisode,
      line: 'n2d',
      clip_id: 'OTHER',
      generation_kind: 'image',
      target_slot: 'first',
      target_output_path: `出图/${otherEpisode}/OTHER_first.png`,
      base_content_hash: 'a'.repeat(64),
      base_source_sha256: 'b'.repeat(64),
      base_settings_sha256: 'c'.repeat(64),
      config: {},
      old_controls: null,
      created_at: '2000-01-01T00:00:00.000Z',
      phase: 'prepared',
    }))
  }

  await readCanvas(root, episode, undefined, 'n2d')
  for (const file of files) await fs.access(file)
})
