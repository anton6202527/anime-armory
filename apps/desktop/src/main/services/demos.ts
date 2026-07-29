import { app } from 'electron'
import fs from 'node:fs/promises'
import { createReadStream, createWriteStream, existsSync } from 'node:fs'
import { createHash } from 'node:crypto'
import path from 'node:path'
import { Readable } from 'node:stream'
import { pipeline } from 'node:stream/promises'
import extractZip from 'extract-zip'
import type { DemoDownloadInfo, DemoInstallResult, LineKey } from '@shared/types'

const DOWNLOAD_TIMEOUT = 600_000
const CATALOG_DOWNLOAD_TIMEOUT = 10_000
const CATALOG_CACHE_TTL = 5 * 60_000
const DEFAULT_R2_PUBLIC_BASE = 'https://pub-0bafc63084d743e78dbe9f72fc918988.r2.dev'
const R2_PUBLIC_BASE = String(
  process.env.ANIME_ARMORY_DEMO_ASSET_BASE_URL ?? DEFAULT_R2_PUBLIC_BASE,
).replace(/\/+$/, '')
const CATALOG_URL =
  process.env.ANIME_ARMORY_DEMO_CATALOG_URL ?? `${R2_PUBLIC_BASE}/catalog/v1/catalog.json`
const MAX_DEMO_BYTES = 5 * 1024 * 1024 * 1024
const LINE_KEYS = new Set<LineKey>(['n2d', 'comic', 'ad', 'mv', 'song', 'novel'])
const LINE_KEY_BY_NAME: Record<string, LineKey> = {
  制漫剧: 'n2d',
  画漫画: 'comic',
  拍广告: 'ad',
  制MV: 'mv',
  写歌: 'song',
  写小说: 'novel',
}

interface CatalogEntry {
  line?: string
  line_key?: string
  name?: string
  rel?: string
  asset_name?: string
  object_key?: string
  download_url?: string
  sha256?: string
  size?: number
  source?: string
}

let remoteCatalogCache: { at: number; entries: CatalogEntry[] } | null = null
let remoteCatalogPending: Promise<CatalogEntry[]> | null = null

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

function catalogEntries(doc: unknown): CatalogEntry[] {
  if (Array.isArray(doc)) return doc as CatalogEntry[]
  if (doc && typeof doc === 'object' && Array.isArray((doc as { demos?: unknown }).demos)) {
    return (doc as { demos: CatalogEntry[] }).demos
  }
  return []
}

function allowedCatalogOrigin(catalogUrl: string): string | null {
  try {
    const parsed = new URL(catalogUrl)
    if (parsed.protocol !== 'https:' && !(parsed.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(parsed.hostname))) {
      return null
    }
    return parsed.origin
  } catch {
    return null
  }
}

function safeObjectKey(value: unknown): string | null {
  const key = String(value ?? '').trim()
  if (
    !key
    || key.length > 1024
    || key.startsWith('/')
    || key.includes('\\')
    || key.includes('//')
    || key.split('/').some((part) => !part || part === '.' || part === '..' || /[\0\r\n]/.test(part))
    || !key.endsWith('.zip')
  ) return null
  return key
}

function normalizeCatalogEntry(entry: CatalogEntry, catalogUrl: string): CatalogEntry | null {
  const rel = String(entry.rel ?? '').split('\\').join('/')
  const parts = rel.split('/')
  if (
    parts.length !== 3
    || parts[0] !== '创作区'
    || !parts[1]
    || !parts[2]
    || parts.some((part) => !part || part === '.' || part === '..' || /[\0\r\n]/.test(part))
  ) return null
  const derivedKey = LINE_KEY_BY_NAME[parts[1]]
  const key = String(entry.line_key ?? derivedKey ?? '') as LineKey
  if (!LINE_KEYS.has(key) || !derivedKey || key !== derivedKey) return null
  const assetName = String(entry.asset_name ?? `LabuTV_demo_${key}.zip`)
  if (!assetName || path.basename(assetName) !== assetName || !assetName.endsWith('.zip')) return null
  const objectKey = safeObjectKey(entry.object_key)
  const base = String(entry.download_url ?? (objectKey ? new URL(objectKey, `${R2_PUBLIC_BASE}/`).toString() : ''))
  const origin = allowedCatalogOrigin(catalogUrl)
  const size = Number(entry.size)
  const sha256 = String(entry.sha256 ?? '').toLowerCase()
  if (!origin || !Number.isSafeInteger(size) || size <= 0 || size > MAX_DEMO_BYTES) return null
  if (!/^[a-f0-9]{64}$/.test(sha256)) return null
  try {
    const parsed = new URL(base)
    if (parsed.origin !== origin || parsed.protocol !== new URL(catalogUrl).protocol) return null
  } catch {
    return null
  }
  return {
    ...entry,
    line: parts[1],
    line_key: key,
    name: parts[2],
    rel: parts.join('/'),
    asset_name: assetName,
    object_key: objectKey ?? undefined,
    download_url: base,
    sha256,
    size,
    source: 'r2',
  }
}

async function readBundledCatalog(): Promise<CatalogEntry[]> {
  const candidates = [
    path.join(process.resourcesPath ?? '', 'resources', 'demo_catalog.json'),
    path.join(app.getAppPath(), 'resources', 'demo_catalog.json'),
  ]
  for (const p of candidates) {
    try {
      const raw = await fs.readFile(p, 'utf8')
      const list = catalogEntries(JSON.parse(raw))
        .map((entry) => normalizeCatalogEntry(entry, CATALOG_URL))
        .filter((entry): entry is CatalogEntry => entry !== null)
      if (list.length > 0) return list
    } catch {
      // try next location
    }
  }
  return []
}

async function fetchCatalog(url: string): Promise<CatalogEntry[]> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), CATALOG_DOWNLOAD_TIMEOUT)
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: { 'User-Agent': 'LabuTV Desktop' },
    })
    if (!response.ok) return []
    return catalogEntries(await response.json())
      .map((entry) => normalizeCatalogEntry(entry, url))
      .filter((entry): entry is CatalogEntry => entry !== null)
  } catch {
    return []
  } finally {
    clearTimeout(timer)
  }
}

async function readRemoteCatalog(): Promise<CatalogEntry[]> {
  const now = Date.now()
  if (remoteCatalogCache && now - remoteCatalogCache.at < CATALOG_CACHE_TTL) {
    return remoteCatalogCache.entries
  }
  if (remoteCatalogPending) return remoteCatalogPending
  remoteCatalogPending = (async () => {
    const entries = await fetchCatalog(CATALOG_URL)
    remoteCatalogCache = { at: Date.now(), entries }
    return entries
  })().finally(() => {
    remoteCatalogPending = null
  })
  return remoteCatalogPending
}

async function readCatalog(): Promise<CatalogEntry[]> {
  const bundled = await readBundledCatalog()
  // Don't block first paint on the network. If a fresh remote catalog is
  // already cached, merge it; otherwise kick off a background refresh (filling
  // the cache for next time) and return bundled immediately. Only wait on the
  // network when there is no bundled catalog to fall back to.
  const now = Date.now()
  let remote: CatalogEntry[] = []
  if (remoteCatalogCache && now - remoteCatalogCache.at < CATALOG_CACHE_TTL) {
    remote = remoteCatalogCache.entries
  } else if (bundled.length === 0) {
    remote = await readRemoteCatalog()
  } else {
    void readRemoteCatalog()
  }
  const merged = new Map<string, CatalogEntry>()
  for (const entry of [...bundled, ...remote]) {
    if (entry.rel) merged.set(entry.rel, entry)
  }
  return [...merged.values()].sort((a, b) => String(a.rel).localeCompare(String(b.rel), 'zh-Hans-CN'))
}

function workTarget(workspaceRoot: string, rel: string): string {
  const workspace = path.resolve(workspaceRoot)
  const target = path.resolve(workspace, ...rel.split('/'))
  if (!target.startsWith(`${workspace}${path.sep}`)) throw new Error('示例作品路径不安全,安装中止')
  return target
}

export async function listDemoDownloads(workspaceRoot: string): Promise<DemoDownloadInfo[]> {
  const catalog = await readCatalog()
  return catalog.map((entry) => {
    const key = entry.line_key ?? entry.line ?? ''
    const rel = entry.rel ?? ''
    const abs = rel ? workTarget(workspaceRoot, rel) : ''
    return {
      line: entry.line ?? key,
      line_key: key as LineKey,
      name: entry.name ?? key,
      rel,
      asset_name: entry.asset_name ?? `LabuTV_demo_${key}.zip`,
      download_url: entry.download_url ?? '',
      sha256: entry.sha256 ?? null,
      size: entry.size ?? null,
      source: entry.source ?? 'r2',
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
      headers: { 'User-Agent': 'LabuTV Desktop' },
    })
    if (!res.ok || !res.body) throw new Error(`下载失败:HTTP ${res.status}`)
    await pipeline(
      Readable.fromWeb(res.body as import('node:stream/web').ReadableStream),
      createWriteStream(dest, { flags: 'wx' }),
    )
  } finally {
    clearTimeout(timer)
  }
}

async function sha256File(p: string): Promise<string> {
  const hash = createHash('sha256')
  for await (const chunk of createReadStream(p)) hash.update(chunk)
  return hash.digest('hex')
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

export async function installDemo(workspaceRoot: string, relOrLine: string): Promise<DemoInstallResult> {
  const list = await listDemoDownloads(workspaceRoot)
  const info = list.find((demo) => demo.rel === relOrLine)
    ?? list.find((demo) => demo.line_key === relOrLine || demo.line === relOrLine)
  if (!info) throw new Error(`未找到示例作品: ${relOrLine}`)
  const target = workTarget(workspaceRoot, info.rel)
  if (existsSync(path.join(target, '_进度.md'))) {
    return {
      root: { name: path.basename(target), path: target, has_progress: true, is_demo: true },
      already_installed: true,
    }
  }
  const cacheKey = createHash('sha256').update(info.rel).digest('hex').slice(0, 12)
  const cacheDir = path.join(app.getPath('temp'), 'anime-armory', 'demo-downloads', `${cacheKey}-${Date.now()}`)
  await fs.mkdir(cacheDir, { recursive: true })
  const zipPath = path.join(cacheDir, info.asset_name)
  try {
    await download(info.download_url, zipPath)
    const downloaded = await fs.stat(zipPath)
    if (info.size && downloaded.size !== info.size) {
      throw new Error(`示例包大小校验失败（期望 ${info.size}，实际 ${downloaded.size}）`)
    }
    const digest = await sha256File(zipPath)
    if (!info.sha256 || digest.toLowerCase() !== info.sha256.toLowerCase()) {
      throw new Error('示例包校验失败(sha256 不匹配),请重试')
    }
    const extractDir = path.join(cacheDir, 'extracted')
    await extractZip(zipPath, { dir: extractDir })
    const expectedRoot = path.join(extractDir, ...info.rel.split('/'))
    const progressRoot = existsSync(path.join(expectedRoot, '_进度.md'))
      ? expectedRoot
      : await findProgressRoot(extractDir)
    if (!progressRoot) throw new Error('示例包中未找到 _进度.md,安装中止')
    if (path.basename(progressRoot) !== info.name) throw new Error('示例包作品名与目录不一致,安装中止')
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
  } finally {
    await fs.rm(cacheDir, { recursive: true, force: true })
  }
}

/** Legacy bundled-work seeding — kept as a graceful no-op when no seeds ship. */
export async function seedDemos(_workspaceRoot: string): Promise<number> {
  return 0
}
