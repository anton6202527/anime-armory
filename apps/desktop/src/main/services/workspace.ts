import { app, dialog, shell } from 'electron'
import fs from 'node:fs/promises'
import { existsSync } from 'node:fs'
import path from 'node:path'
import os from 'node:os'
import { isInside } from '../util/paths'
import type { LineInfo, LineKey, WorkRoot } from '@shared/types'
import { readDemoOrigins } from './demos'

interface LineDef {
  line: LineKey
  dir: string
  view: 'canvas' | 'files' | 'audio'
}

/** Pull the card cover + synopsis from a work's `_meta.json`, if present.
 *  Cover is resolved to an absolute path, confined within the work dir and
 *  required to exist; synopsis is trimmed and length-capped. Missing or
 *  malformed metadata degrades to nulls. */
async function readWorkCard(workDir: string): Promise<{ cover: string | null; synopsis: string | null }> {
  try {
    const meta = JSON.parse(await fs.readFile(path.join(workDir, '_meta.json'), 'utf8'))
    let cover: string | null = null
    const rawCover = typeof meta?.cover === 'string' ? meta.cover.trim() : ''
    if (rawCover) {
      const abs = path.resolve(workDir, ...rawCover.split(/[\\/]+/))
      if ((abs === workDir || abs.startsWith(`${workDir}${path.sep}`)) && existsSync(abs)) cover = abs
    }
    const rawSyn = typeof meta?.synopsis === 'string' ? meta.synopsis.trim() : ''
    return { cover, synopsis: rawSyn ? rawSyn.slice(0, 240) : null }
  } catch {
    return { cover: null, synopsis: null }
  }
}

/** The six creative lines and their product folders under 创作区/. */
export const LINES: LineDef[] = [
  { line: 'n2d', dir: '制漫剧', view: 'canvas' },
  { line: 'comic', dir: '画漫画', view: 'canvas' },
  { line: 'ad', dir: '拍广告', view: 'canvas' },
  { line: 'mv', dir: '制MV', view: 'canvas' },
  { line: 'song', dir: '写歌', view: 'audio' },
  { line: 'novel', dir: '写小说', view: 'files' },
]

const LINE_LABELS: Record<LineKey, string> = {
  n2d: '制漫剧 (n2d)',
  comic: '画漫画 (comic)',
  ad: '拍广告 (ad)',
  mv: '制MV (mv)',
  song: '写歌 (song)',
  novel: '写小说 (novel)',
}

export class WorkspaceService {
  async defaultWorkspace(): Promise<string> {
    const override = process.env.ANIME_ARMORY_WORKSPACE?.trim()
    const dir = override ? path.resolve(override) : path.join(os.homedir(), 'AnimeArmory')
    await fs.mkdir(dir, { recursive: true })
    return dir
  }

  /** Resolve the skills repo: override → env → walk up from cwd → bundled resources. */
  async resolveRepo(devRepo: string): Promise<string> {
    const hasSkills = (p: string) => existsSync(path.join(p, 'skills', 'README.md'))
    if (devRepo && hasSkills(devRepo)) return devRepo
    const env = process.env.ANIME_ARMORY_REPO
    if (env && hasSkills(env)) return env
    let cur = process.cwd()
    for (let i = 0; i < 8; i++) {
      if (hasSkills(cur)) return cur
      const parent = path.dirname(cur)
      if (parent === cur) break
      cur = parent
    }
    const bundled = path.join(process.resourcesPath ?? '', 'resources')
    if (hasSkills(bundled)) return bundled
    return devRepo
  }

  async scan(workspaceRoot: string): Promise<LineInfo[]> {
    const demoOrigins = await readDemoOrigins(workspaceRoot)
    const out: LineInfo[] = []
    for (const def of LINES) {
      const dir = path.join(workspaceRoot, '创作区', def.dir)
      const roots: WorkRoot[] = []
      let entries: string[] = []
      try {
        entries = await fs.readdir(dir)
      } catch {
        // product dir absent — line still listed with no works
      }
      for (const name of entries.sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'))) {
        if (name.startsWith('.') || name.startsWith('_')) continue
        const p = path.join(dir, name)
        try {
          const st = await fs.stat(p)
          if (!st.isDirectory()) continue
        } catch {
          continue
        }
        const rel = path.relative(workspaceRoot, p).split(path.sep).join('/')
        const card = await readWorkCard(p)
        roots.push({
          name,
          path: p,
          has_progress: existsSync(path.join(p, '_进度.md')),
          is_demo: demoOrigins.has(rel),
          cover: card.cover,
          synopsis: card.synopsis,
        })
      }
      roots.sort((a, b) => (a.is_demo === b.is_demo ? a.name.localeCompare(b.name, 'zh-Hans-CN') : a.is_demo ? -1 : 1))
      out.push({ line: def.line, label: LINE_LABELS[def.line], dir, view: def.view, roots })
    }
    return out
  }

  async createWork(dir: string, repoRoot: string, name: string): Promise<string> {
    if (!name || /[\\/:*?"<>|]/.test(name) || name === '.' || name === '..') {
      throw new Error('作品名称包含非法字符')
    }
    if (repoRoot && isInside(repoRoot, dir)) {
      throw new Error('不能在技能仓库内创建作品')
    }
    const target = path.join(dir, name)
    if (existsSync(target)) throw new Error('同名作品已存在')
    await fs.mkdir(target, { recursive: true })
    return target
  }

  async deleteWork(workspaceRoot: string, repoRoot: string, workPath: string): Promise<void> {
    if (!isInside(workspaceRoot, workPath)) throw new Error('该目录不在工作区内,拒绝删除')
    if (repoRoot && isInside(repoRoot, workPath)) throw new Error('该目录属于技能仓库,拒绝删除')
    if (path.resolve(workPath) === path.resolve(workspaceRoot)) throw new Error('不能删除工作区根目录')
    await shell.trashItem(workPath)
  }

  async pickDirectory(title?: string): Promise<string | null> {
    const res = await dialog.showOpenDialog({
      title: title ?? '选择文件夹',
      properties: ['openDirectory', 'createDirectory'],
      defaultPath: app.getPath('home'),
    })
    return res.canceled || res.filePaths.length === 0 ? null : res.filePaths[0]
  }

  async pickImportFiles(extensions: string[], title?: string): Promise<string[]> {
    const res = await dialog.showOpenDialog({
      title: title ?? '选择文件',
      properties: ['openFile', 'multiSelections'],
      filters: extensions.length > 0 ? [{ name: '支持的文件', extensions }] : undefined,
    })
    return res.canceled ? [] : res.filePaths
  }
}
