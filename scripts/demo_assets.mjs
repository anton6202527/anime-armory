import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'

export const CREATION_ROOT = '创作区'
export const LINE_KEY_BY_NAME = new Map([
  ['写小说', 'novel'],
  ['制漫剧', 'n2d'],
  ['画漫画', 'comic'],
  ['写歌', 'song'],
  ['制MV', 'mv'],
  ['拍广告', 'ad'],
])

export function parseWorkRel(rel) {
  const value = String(rel ?? '').split('\\').join('/')
  const parts = value.split('/')
  if (
    parts.length !== 3
    || parts[0] !== CREATION_ROOT
    || !LINE_KEY_BY_NAME.has(parts[1])
    || !parts[2]
    || parts.some((part) => !part || part === '.' || part === '..' || /[\0\r\n\t]/.test(part))
  ) {
    throw new Error(`Invalid demo work path: ${rel}`)
  }
  return {
    root: parts[0],
    line: parts[1],
    lineKey: LINE_KEY_BY_NAME.get(parts[1]),
    name: parts[2],
    rel: parts.join('/'),
  }
}

export function workRel(entry) {
  if (typeof entry === 'string') return parseWorkRel(entry).rel
  if (!entry || typeof entry !== 'object') throw new Error(`Invalid demo config entry: ${entry}`)
  if (typeof entry.rel === 'string') return parseWorkRel(entry.rel).rel
  return parseWorkRel(`${CREATION_ROOT}/${String(entry.line ?? '').trim()}/${String(entry.name ?? '').trim()}`).rel
}

export function demoAssetName(rel) {
  const work = parseWorkRel(rel)
  const id = crypto.createHash('sha256').update(work.rel).digest('hex').slice(0, 8)
  return `LabuTV_demo_${work.lineKey}_${id}.zip`
}

export function demoObjectKey(rel, sha256) {
  const work = parseWorkRel(rel)
  const digest = String(sha256 ?? '').toLowerCase()
  if (!/^[a-f0-9]{64}$/.test(digest)) throw new Error('Demo SHA-256 must be 64 lowercase hex characters')
  const id = crypto.createHash('sha256').update(work.rel).digest('hex').slice(0, 12)
  return `demos/v1/${work.lineKey}/${id}/${digest}.zip`
}

export function normalizePublicBase(value) {
  const parsed = new URL(String(value ?? '').trim())
  if (parsed.protocol !== 'https:') throw new Error('R2 public base URL must use HTTPS')
  parsed.pathname = parsed.pathname.replace(/\/+$/, '')
  parsed.search = ''
  parsed.hash = ''
  return parsed.toString().replace(/\/$/, '')
}

export function publicObjectUrl(base, objectKey) {
  const normalized = normalizePublicBase(base)
  const safeKey = String(objectKey ?? '').split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/')
  return `${normalized}/${safeKey}`
}

export async function sha256File(file) {
  const hash = crypto.createHash('sha256')
  for await (const chunk of fs.createReadStream(file)) hash.update(chunk)
  return hash.digest('hex')
}

export function countDone(progressText) {
  return (String(progressText ?? '').match(/✅/g) ?? []).length
}

export function catalogEntry({ rel, sha256, size, publicBaseUrl, objectKey, progressText }) {
  const work = parseWorkRel(rel)
  if (!Number.isSafeInteger(size) || size <= 0) throw new Error(`Invalid demo size for ${rel}`)
  return {
    root: work.root,
    line: work.line,
    line_key: work.lineKey,
    name: work.name,
    rel: work.rel,
    is_demo: true,
    source: 'r2',
    asset_name: demoAssetName(work.rel),
    object_key: objectKey,
    download_url: publicObjectUrl(publicBaseUrl, objectKey),
    sha256,
    size,
    done: countDone(progressText),
  }
}

export function resolveInside(root, rel) {
  const base = path.resolve(root)
  const target = path.resolve(base, ...parseWorkRel(rel).rel.split('/'))
  if (!target.startsWith(`${base}${path.sep}`)) throw new Error(`Demo path escapes workspace: ${rel}`)
  return target
}
