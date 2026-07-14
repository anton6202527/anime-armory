import assert from 'node:assert/strict'
import fsp from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'
import extractZip from 'extract-zip'

import {
  catalogEntry,
  demoAssetName,
  demoObjectKey,
  parseWorkRel,
  publicObjectUrl,
} from './demo_assets.mjs'
import { createDemoZip } from './demo_zip.mjs'

test('demo asset names remain stable and ASCII-only', () => {
  const rel = '创作区/制漫剧/那妖魔是姜大人'
  assert.equal(demoAssetName(rel), 'AnimeArmory_demo_n2d_23fcd23e.zip')
  assert.match(demoAssetName(rel), /^[A-Za-z0-9._-]+$/)
  assert.notEqual(demoAssetName(rel), demoAssetName('创作区/制漫剧/万妖图魔录'))
})

test('immutable R2 keys include the work identity and content digest', () => {
  const digest = 'a'.repeat(64)
  assert.equal(
    demoObjectKey('创作区/画漫画/仙界闭关小能手', digest),
    `demos/v1/comic/5c78a59099c2/${digest}.zip`,
  )
})

test('public object URLs encode each key segment', () => {
  assert.equal(
    publicObjectUrl('https://assets.example.com/', 'demos/v1/a b/file.zip'),
    'https://assets.example.com/demos/v1/a%20b/file.zip',
  )
})

test('catalog entries are anonymous R2 downloads with mandatory integrity metadata', () => {
  const sha256 = 'b'.repeat(64)
  const objectKey = demoObjectKey('创作区/写小说/示例', sha256)
  const entry = catalogEntry({
    rel: '创作区/写小说/示例',
    sha256,
    size: 123,
    publicBaseUrl: 'https://assets.example.com',
    objectKey,
    progressText: '✅\n✅',
  })
  assert.equal(entry.source, 'r2')
  assert.equal(entry.done, 2)
  assert.equal(entry.download_url, `https://assets.example.com/${objectKey}`)
})

test('unsafe work paths are rejected', () => {
  assert.throws(() => parseWorkRel('创作区/制漫剧/../secret'), /Invalid demo work path/)
})

test('Demo ZIPs preserve UTF-8 work names for Electron extraction', async () => {
  const temp = await fsp.mkdtemp(path.join(os.tmpdir(), 'anime-armory-demo-zip-test-'))
  const source = path.join(temp, '创作区')
  const progress = path.join(source, '拍广告', '星盒手账App', '_进度.md')
  const archive = path.join(temp, 'demo.zip')
  const extracted = path.join(temp, 'extracted')
  try {
    await fsp.mkdir(path.dirname(progress), { recursive: true })
    await fsp.writeFile(progress, '# 测试\n', 'utf8')
    await createDemoZip(source, archive, '创作区')
    await extractZip(archive, { dir: extracted })
    assert.equal(
      await fsp.readFile(path.join(extracted, '创作区', '拍广告', '星盒手账App', '_进度.md'), 'utf8'),
      '# 测试\n',
    )
  } finally {
    await fsp.rm(temp, { recursive: true, force: true })
  }
})
