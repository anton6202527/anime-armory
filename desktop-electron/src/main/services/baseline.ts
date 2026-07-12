import { app } from 'electron'
import fs from 'node:fs/promises'
import { Dirent } from 'node:fs'
import path from 'node:path'
import { fnv1a64, hashPathKey } from '../util/hash'
import { decodeTextBuffer, looksBinary } from '../util/text'
import { isIgnoredName, resolveWithin } from '../util/paths'
import type {
  WorkChangeDetail,
  WorkChangeEntry,
  WorkChanges,
  WorkChangeSummary,
} from '@shared/types'

const BASELINE_FILE_LIMIT = 50000
const SCAN_LIMIT = 30000
const HASH_LIMIT = 1024 * 1024 // content-compare cap
const TEXT_SNAPSHOT_LIMIT = 2 * 1024 * 1024

interface BaselineRecord {
  mtime: number
  size: number
  /** fnv1a64 hex; '' when file was too large to hash */
  hash: string
  text?: string
}

interface BaselineDoc {
  files: Record<string, BaselineRecord>
}

interface ScanEntry {
  rel: string
  size: number
  mtime: number
}

async function walkFiles(root: string, limit: number): Promise<{ files: ScanEntry[]; capped: boolean }> {
  const files: ScanEntry[] = []
  let capped = false
  const stack: string[] = ['']
  while (stack.length > 0) {
    const relDir = stack.pop()!
    const absDir = relDir ? path.join(root, relDir) : root
    let entries: Dirent[]
    try {
      entries = await fs.readdir(absDir, { withFileTypes: true })
    } catch {
      continue
    }
    for (const ent of entries) {
      if (isIgnoredName(ent.name)) continue
      const rel = relDir ? `${relDir}/${ent.name}` : ent.name
      if (ent.isDirectory()) {
        stack.push(rel)
      } else if (ent.isFile()) {
        if (files.length >= limit) {
          capped = true
          continue
        }
        try {
          const st = await fs.stat(path.join(root, rel))
          files.push({ rel, size: st.size, mtime: st.mtimeMs })
        } catch {
          // raced deletion
        }
      }
    }
  }
  return { files, capped }
}

async function snapshotRecord(abs: string, size: number, mtime: number): Promise<BaselineRecord> {
  const rec: BaselineRecord = { mtime, size, hash: '' }
  if (size <= TEXT_SNAPSHOT_LIMIT) {
    try {
      const buf = await fs.readFile(abs)
      if (buf.length <= HASH_LIMIT) rec.hash = fnv1a64(buf)
      if (!looksBinary(buf)) rec.text = decodeTextBuffer(buf)
    } catch {
      // unreadable — keep stat-only record
    }
  }
  return rec
}

/**
 * Baseline snapshots powering the git-like "changes" view. Stored outside the
 * workspace under userData/baselines/<hash16>.json, keyed by work path.
 */
export class BaselineService {
  private docCache = new Map<string, BaselineDoc>()

  private dir(): string {
    return path.join(app.getPath('userData'), 'baselines')
  }

  private fileFor(root: string): string {
    return path.join(this.dir(), `${hashPathKey(path.resolve(root))}.json`)
  }

  private async load(root: string): Promise<BaselineDoc | null> {
    const key = path.resolve(root)
    const cached = this.docCache.get(key)
    if (cached) return cached
    try {
      const raw = await fs.readFile(this.fileFor(root), 'utf8')
      const doc = JSON.parse(raw) as BaselineDoc
      if (!doc || typeof doc.files !== 'object') return null
      this.docCache.set(key, doc)
      return doc
    } catch {
      return null
    }
  }

  private async save(root: string, doc: BaselineDoc): Promise<void> {
    this.docCache.set(path.resolve(root), doc)
    await fs.mkdir(this.dir(), { recursive: true })
    const tmp = this.fileFor(root) + '.tmp'
    await fs.writeFile(tmp, JSON.stringify(doc))
    await fs.rename(tmp, this.fileFor(root))
  }

  private async seed(root: string): Promise<{ scanned: number; capped: boolean }> {
    const { files, capped } = await walkFiles(root, BASELINE_FILE_LIMIT)
    const doc: BaselineDoc = { files: {} }
    for (const f of files) {
      doc.files[f.rel] = await snapshotRecord(path.join(root, f.rel), f.size, f.mtime)
    }
    await this.save(root, doc)
    return { scanned: files.length, capped }
  }

  /** Seeds silently on first contact so a fresh work shows no changes. */
  async ensureSeeded(root: string): Promise<BaselineDoc> {
    const doc = await this.load(root)
    if (doc) return doc
    await this.seed(root)
    return (await this.load(root)) ?? { files: {} }
  }

  private async fileChanged(root: string, entry: ScanEntry, old: BaselineRecord): Promise<boolean> {
    if (entry.size !== old.size) return true
    if (entry.mtime === old.mtime) return false
    if (!old.hash) return true // legacy/oversize record: mtime drift counts as change
    if (entry.size > HASH_LIMIT) return true
    try {
      const buf = await fs.readFile(path.join(root, entry.rel))
      return fnv1a64(buf) !== old.hash
    } catch {
      return true
    }
  }

  /** Change markers for tree decoration: rel → 'u' (new) | 'm' (modified). */
  async statusMap(root: string): Promise<Map<string, string>> {
    const doc = await this.ensureSeeded(root)
    const { files } = await walkFiles(root, SCAN_LIMIT)
    const map = new Map<string, string>()
    for (const f of files) {
      const old = doc.files[f.rel]
      if (!old) map.set(f.rel, 'u')
      else if (await this.fileChanged(root, f, old)) map.set(f.rel, 'm')
    }
    return map
  }

  /** Change markers for an already-listed directory page. Unlike statusMap,
   *  this does not recursively walk the whole work on every folder expand. */
  async statusForEntries(
    root: string,
    entries: Array<{ rel: string; size: number; mtime: number }>,
  ): Promise<Map<string, string>> {
    const doc = await this.ensureSeeded(root)
    const map = new Map<string, string>()
    for (const entry of entries) {
      const old = doc.files[entry.rel]
      if (!old) map.set(entry.rel, 'u')
      else if (await this.fileChanged(root, entry, old)) map.set(entry.rel, 'm')
    }
    return map
  }

  async summary(root: string): Promise<WorkChangeSummary> {
    const existing = await this.load(root)
    if (!existing) {
      const { scanned, capped } = await this.seed(root)
      return { changed: 0, deleted: 0, scanned, capped }
    }
    const { files, capped } = await walkFiles(root, SCAN_LIMIT)
    let changed = 0
    const seen = new Set<string>()
    for (const f of files) {
      seen.add(f.rel)
      const old = existing.files[f.rel]
      if (!old || (await this.fileChanged(root, f, old))) changed++
    }
    let deleted = 0
    for (const rel of Object.keys(existing.files)) {
      if (!seen.has(rel)) deleted++
    }
    return { changed, deleted, scanned: files.length, capped }
  }

  async changes(root: string): Promise<WorkChanges> {
    const doc = await this.ensureSeeded(root)
    const { files, capped } = await walkFiles(root, SCAN_LIMIT)
    const out: WorkChangeEntry[] = []
    const seen = new Set<string>()
    for (const f of files) {
      seen.add(f.rel)
      const old = doc.files[f.rel]
      if (!old) {
        out.push({
          path: f.rel,
          kind: 'added',
          old_size: null,
          new_size: f.size,
          old_mtime: null,
          new_mtime: f.mtime,
          text_available: f.size <= TEXT_SNAPSHOT_LIMIT,
        })
      } else if (await this.fileChanged(root, f, old)) {
        out.push({
          path: f.rel,
          kind: 'modified',
          old_size: old.size,
          new_size: f.size,
          old_mtime: old.mtime,
          new_mtime: f.mtime,
          text_available: old.text !== undefined,
        })
      }
    }
    for (const [rel, old] of Object.entries(doc.files)) {
      if (!seen.has(rel)) {
        out.push({
          path: rel,
          kind: 'deleted',
          old_size: old.size,
          new_size: null,
          old_mtime: old.mtime,
          new_mtime: null,
          text_available: old.text !== undefined,
        })
      }
    }
    out.sort((a, b) => a.path.localeCompare(b.path))
    return { changes: out, scanned: files.length, capped }
  }

  async readChange(root: string, rel: string): Promise<WorkChangeDetail> {
    const doc = await this.ensureSeeded(root)
    const old = doc.files[rel]
    const abs = path.join(root, rel)
    let newText = ''
    let exists = false
    let newBinary = false
    try {
      const st = await fs.stat(abs)
      exists = st.isFile()
      if (exists && st.size <= TEXT_SNAPSHOT_LIMIT) {
        const buf = await fs.readFile(abs)
        if (looksBinary(buf)) newBinary = true
        else newText = decodeTextBuffer(buf)
      } else if (exists) {
        newBinary = true
      }
    } catch {
      exists = false
    }
    const kind = !old ? 'added' : exists ? 'modified' : 'deleted'
    const oldAvailable = old ? old.text !== undefined : true
    const textAvailable = oldAvailable && !newBinary
    return {
      path: rel,
      kind,
      old_text: old?.text ?? '',
      new_text: newText,
      text_available: textAvailable,
      message: textAvailable ? '' : '该文件不支持文本对比(二进制或超出大小限制)',
    }
  }

  async archiveAll(root: string): Promise<WorkChangeSummary> {
    await this.seed(root)
    return this.summary(root)
  }

  async archiveOne(root: string, rel: string): Promise<WorkChangeSummary> {
    const doc = await this.ensureSeeded(root)
    const abs = resolveWithin(root, rel)
    try {
      const st = await fs.stat(abs)
      doc.files[rel] = await snapshotRecord(abs, st.size, st.mtimeMs)
    } catch {
      delete doc.files[rel]
    }
    await this.save(root, doc)
    return this.summary(root)
  }

  async restoreAll(root: string): Promise<WorkChangeSummary> {
    const { changes } = await this.changes(root)
    for (const c of changes) {
      await this.restoreEntry(root, c)
    }
    return this.summary(root)
  }

  async restoreOne(root: string, rel: string): Promise<WorkChangeSummary> {
    const { changes } = await this.changes(root)
    const c = changes.find((x) => x.path === rel)
    if (c) await this.restoreEntry(root, c)
    return this.summary(root)
  }

  private async restoreEntry(root: string, c: WorkChangeEntry): Promise<void> {
    const doc = await this.ensureSeeded(root)
    const abs = resolveWithin(root, c.path)
    if (c.kind === 'added') {
      await fs.rm(abs, { force: true })
      return
    }
    const old = doc.files[c.path]
    if (!old || old.text === undefined) {
      throw new Error(`无法还原 ${c.path}:基线缺少文本快照`)
    }
    await fs.mkdir(path.dirname(abs), { recursive: true })
    await fs.writeFile(abs, old.text, 'utf8')
    const st = await fs.stat(abs)
    doc.files[c.path] = { ...old, mtime: st.mtimeMs, size: st.size }
    await this.save(root, doc)
  }

  async deletedPaths(root: string): Promise<string[]> {
    const doc = await this.load(root)
    if (!doc) return []
    const out: string[] = []
    for (const rel of Object.keys(doc.files)) {
      try {
        await fs.access(path.join(root, rel))
      } catch {
        out.push(rel)
      }
    }
    return out.sort()
  }
}
