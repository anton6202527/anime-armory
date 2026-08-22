import assert from 'node:assert/strict'
import test from 'node:test'
import {
  selectCatalogDemos,
  selectVisibleLineDemos,
} from '../src/shared/demoPolicy.ts'
import type { DemoDownloadInfo, LineKey, WorkRoot } from '../src/shared/types.ts'

function root(name: string, isDemo = false): WorkRoot {
  return {
    name,
    path: `/workspace/${name}`,
    has_progress: true,
    is_demo: isDemo,
  }
}

function download(line: LineKey, name: string, installed = false): DemoDownloadInfo {
  return {
    line,
    line_key: line,
    name,
    rel: `创作区/${line}/${name}`,
    asset_name: `${line}-${name}.zip`,
    download_url: `https://example.test/${line}-${name}.zip`,
    source: 'test',
    installed,
  }
}

test('制漫剧保留那妖魔是姜大人，并隐藏第二个远程 demo', () => {
  const result = selectVisibleLineDemos(
    'n2d',
    [root('那妖魔是姜大人', true), root('金瓶梅')],
    [download('n2d', '仙界闯关小能手')],
  )

  assert.deepEqual(result.roots.map((item) => item.name), ['那妖魔是姜大人', '金瓶梅'])
  assert.deepEqual(result.downloads, [])
})

test('制漫剧的指定 demo 优先于历史安装的其他 demo', () => {
  const result = selectVisibleLineDemos(
    'n2d',
    [root('仙界闯关小能手', true), root('真实作品')],
    [download('n2d', '那妖魔是姜大人')],
  )

  assert.deepEqual(result.roots.map((item) => item.name), ['真实作品'])
  assert.deepEqual(result.downloads.map((item) => item.name), ['那妖魔是姜大人'])
})

test('每个系列目录最多返回一个 demo', () => {
  const result = selectCatalogDemos([
    download('comic', 'A'),
    download('comic', 'B'),
    download('song', 'C'),
    download('song', 'D'),
  ])

  assert.deepEqual(result.map((item) => `${item.line_key}:${item.name}`), ['comic:A', 'song:C'])
})

test('非 demo 作品始终全部保留', () => {
  const result = selectVisibleLineDemos(
    'comic',
    [root('用户作品A'), root('用户作品B')],
    [download('comic', '示例A'), download('comic', '示例B')],
  )

  assert.deepEqual(result.roots.map((item) => item.name), ['用户作品A', '用户作品B'])
  assert.deepEqual(result.downloads.map((item) => item.name), ['示例A'])
})
