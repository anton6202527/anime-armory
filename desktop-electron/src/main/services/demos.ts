import { app } from 'electron'
import fs from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { createHash } from 'node:crypto'
import path from 'node:path'
import extractZip from 'extract-zip'
import type { DemoDownloadInfo, DemoInstallResult, LineKey } from '@shared/types'

const DOWNLOAD_TIMEOUT = 600_000
const RELEASE_BASE =
  process.env.ANIME_ARMORY_DEMO_RELEASE_BASE ??
  'https://github.com/anton6202527/anime-armory/releases/latest/download'

interface CatalogEntry {
  line?: string
  line_key?: string
  name?: string
  rel?: string
  asset_name?: string
  download_url?: string
  sha256?: string
  size?: number
  source?: string
}

function originsFile(workspaceRoot: string): string {
  return path.join(workspaceRoot, '.anime-armory', 'demo_origins.json')
}

/** Rel paths (workspace-relative) of works installed as demos. */
export async function readDemoOrigins(workspaceRoot: string): Promise<Set<string>> {
  try {
    const raw = await fs.readFile(originsFile(workspaceRoot), 'utf8')
    const arr = JSON.parse(raw)
    return new Set(Array.isArray(arr) ? arr.filter((x) => typeof x === 'string') : [])
  } catch {
    return new Set()
  }
}

async function addDemoOrigin(workspaceRoot: string, rel: string): Promise<void> {
  const set = await readDemoOrigins(workspaceRoot)
  set.add(rel)
  const file = originsFile(workspaceRoot)
  await fs.mkdir(path.dirname(file), { recursive: true })
  await fs.writeFile(file, JSON.stringify([...set].sort(), null, 2))
}

async function readCatalog(): Promise<CatalogEntry[]> {
  const candidates = [
    path.join(process.resourcesPath ?? '', 'resources', 'demo_catalog.json'),
    path.join(app.getAppPath(), 'resources', 'demo_catalog.json'),
    path.join(app.getAppPath(), '..', 'desktop', 'resources', 'demo_catalog.json'),
  ]
  for (const p of candidates) {
    try {
      const raw = await fs.readFile(p, 'utf8')
      const doc = JSON.parse(raw)
      const list = Array.isArray(doc) ? doc : doc?.demos
      if (Array.isArray(list)) return list
    } catch {
      // try next location
    }
  }
  return []
}

export async function listDemoDownloads(workspaceRoot: string): Promise<DemoDownloadInfo[]> {
  const catalog = await readCatalog()
  return catalog.map((entry) => {
    const key = entry.line_key ?? entry.line ?? ''
    const rel = entry.rel ?? ''
    const abs = rel ? path.join(workspaceRoot, rel) : ''
    return {
      line: entry.line ?? key,
      line_key: key as LineKey,
      name: entry.name ?? key,
      rel,
      asset_name: entry.asset_name ?? `AnimeArmory_demo_${key}.zip`,
      download_url: entry.download_url ?? `${RELEASE_BASE}/AnimeArmory_demo_${key}.zip`,
      sha256: entry.sha256 ?? null,
      size: entry.size ?? null,
      source: entry.source ?? 'release',
      installed: Boolean(abs) && existsSync(path.join(abs, '_进度.md')),
      path: abs || null,
    }
  })
}

async function download(url: string, dest: string): Promise<void> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), DOWNLOAD_TIMEOUT)
  try {
    const res = await fetch(url, {
      signal: controller.signal,
      headers: { 'User-Agent': 'AnimeArmory Desktop' },
    })
    if (!res.ok || !res.body) throw new Error(`下载失败:HTTP ${res.status}`)
    const buf = Buffer.from(await res.arrayBuffer())
    await fs.writeFile(dest, buf)
  } finally {
    clearTimeout(timer)
  }
}

async function sha256File(p: string): Promise<string> {
  const buf = await fs.readFile(p)
  return createHash('sha256').update(buf).digest('hex')
}

async function findProgressRoot(dir: string): Promise<string | null> {
  if (existsSync(path.join(dir, '_进度.md'))) return dir
  const entries = await fs.readdir(dir, { withFileTypes: true })
  for (const ent of entries) {
    if (!ent.isDirectory()) continue
    const found = await findProgressRoot(path.join(dir, ent.name))
    if (found) return found
  }
  return null
}

export async function installDemo(workspaceRoot: string, line: string): Promise<DemoInstallResult> {
  const list = await listDemoDownloads(workspaceRoot)
  const info = list.find((d) => d.line_key === line || d.line === line)
  if (!info) throw new Error(`未找到 ${line} 线的示例作品`)
  const target = path.join(workspaceRoot, info.rel)
  if (existsSync(path.join(target, '_进度.md'))) {
    return {
      root: { name: path.basename(target), path: target, has_progress: true, is_demo: true },
      already_installed: true,
    }
  }
  const cacheDir = path.join(app.getPath('temp'), 'anime-armory', 'demo-downloads', `${line}-${Date.now()}`)
  await fs.mkdir(cacheDir, { recursive: true })
  const zipPath = path.join(cacheDir, info.asset_name)
  await download(info.download_url, zipPath)
  if (info.sha256) {
    const digest = await sha256File(zipPath)
    if (digest.toLowerCase() !== info.sha256.toLowerCase()) {
      throw new Error('示例包校验失败(sha256 不匹配),请重试')
    }
  }
  const extractDir = path.join(cacheDir, 'extracted')
  await extractZip(zipPath, { dir: extractDir })
  const progressRoot = await findProgressRoot(extractDir)
  if (!progressRoot) throw new Error('示例包中未找到 _进度.md,安装中止')
  if (existsSync(target)) {
    // never clobber user content — only fill in if missing
    const entries = await fs.readdir(target).catch(() => [])
    if (entries.length > 0) throw new Error('目标目录已存在且非空,拒绝覆盖')
  }
  await fs.mkdir(path.dirname(target), { recursive: true })
  await fs.cp(progressRoot, target, { recursive: true })
  await addDemoOrigin(workspaceRoot, info.rel.split(path.sep).join('/'))
  return {
    root: { name: path.basename(target), path: target, has_progress: true, is_demo: true },
    already_installed: false,
  }
}

/** Legacy bundled-work seeding — kept as a graceful no-op when no seeds ship. */
export async function seedDemos(_workspaceRoot: string): Promise<number> {
  return 0
}
