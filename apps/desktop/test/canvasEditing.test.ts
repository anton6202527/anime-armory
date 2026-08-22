import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import test, { type TestContext } from 'node:test'
import { readCanvas, writeClipEdit } from '../src/main/services/canvas.ts'

async function project(t: TestContext): Promise<{ root: string; source: string; original: string }> {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'canvas-editing-'))
  t.after(() => fs.rm(root, { recursive: true, force: true }))
  const source = path.join(root, '脚本', '第1集', 'storyboard.json')
  await fs.mkdir(path.dirname(source), { recursive: true })
  const original = `${JSON.stringify({
    title: 'Demo',
    clips: [
      { id: 'CLIP01', number: 1, label: '旧标题', duration: 8, scene: '场景', prompt: '旧提示词' },
      { id: 'CLIP02', number: 2, label: '保留镜头', duration: 6, prompt: '不变' },
    ],
  }, null, 2)}\n`
  await fs.writeFile(source, original)
  return { root, source, original }
}

test('canvas edit snapshots canonical source and stale hashes cannot overwrite it', async (t) => {
  const fixture = await project(t)
  const first = await readCanvas(fixture.root, '第1集', undefined, 'n2d')
  const contentHash = first.canvas?.production?.content_hash
  assert.match(contentHash || '', /^[a-f0-9]{64}$/)

  const saved = await writeClipEdit(
    fixture.root,
    '第1集',
    'CLIP01',
    1,
    { label: '二次创作标题', prompt: '二次创作提示词' },
    'n2d',
    contentHash,
  )
  assert.equal(saved.label, '二次创作标题')
  assert.equal(saved.prompt, '二次创作提示词')
  assert.equal(saved.scene, '场景')
  assert.equal(saved.duration, 8)

  const historyDir = path.join(fixture.root, '生产数据', 'canvas_history', '第1集')
  const snapshots = await fs.readdir(historyDir)
  assert.equal(snapshots.length, 1)
  assert.equal(await fs.readFile(path.join(historyDir, snapshots[0]), 'utf8'), fixture.original)

  await assert.rejects(
    writeClipEdit(
      fixture.root,
      '第1集',
      'CLIP01',
      1,
      { label: '过期覆盖' },
      'n2d',
      contentHash,
    ),
    /画布内容已被更新/,
  )
  const disk = JSON.parse(await fs.readFile(fixture.source, 'utf8')) as { clips: Array<{ label: string }> }
  assert.equal(disk.clips[0].label, '二次创作标题')
})
