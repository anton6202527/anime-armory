import { shell } from 'electron'
import fs from 'node:fs/promises'
import { Dirent } from 'node:fs'
import path from 'node:path'
import { fnv1a64 } from '../util/hash'
import { decodeTextBuffer, looksBinary } from '../util/text'
import { isIgnoredName, resolveWithin, validateRelPath } from '../util/paths'
import { readDocxText } from '../util/docx'
import type {
  ImportWorkSourcesResult,
  SkillTreeEntry,
  WorkDirListing,
  WorkFileWriteResult,
  WorkSearchResponse,
  WorkSearchResult,
  WorkSnapshot,
} from '@shared/types'
import type { BaselineService } from './baseline'

const TREE_DEPTH_LIMIT = 6
const TREE_ENTRY_LIMIT = 8000
const TREE_LIMIT_MARKER = '__anime_armory_tree_limit__'
const DIR_PAGE_DEFAULT = 500
const SNAPSHOT_LIMIT = 20000
const TEXT_EDIT_LIMIT = 20 * 1024 * 1024
const DOCX_LIMIT = 80 * 1024 * 1024
const CAPTURE_LIMIT = 32 * 1024 * 1024

const SEARCH_FILE_LIMIT = 30000
const SEARCH_RESULT_LIMIT = 300
const SEARCH_MATCHES_PER_FILE = 12
const SEARCH_SIZE_LIMIT = 1024 * 1024
const SEARCH_DEPTH_LIMIT = 10
const SEARCH_PREVIEW_CHARS = 240

const TEXT_EXTENSIONS = new Set([
  'txt', 'md', 'markdown', 'mdx', 'json', 'jsonl', 'yaml', 'yml', 'toml', 'ini', 'env',
  'py', 'rs', 'ts', 'tsx', 'js', 'jsx', 'mjs', 'cjs', 'css', 'scss', 'less', 'html', 'htm',
  'xml', 'svg', 'sh', 'bash', 'zsh', 'csv', 'tsv', 'log', 'srt', 'vtt', 'ass', 'cfg', 'conf',
])

const IMPORT_EXTENSIONS = new Set(['txt', 'md', 'markdown', 'mdx', 'docx', 'pdf'])

function sortDirents(entries: Dirent[]): Dirent[] {
  return entries
    .filter((e) => !isIgnoredName(e.name))
    .sort((a, b) => {
      if (a.isDirectory() !== b.isDirectory()) return a.isDirectory() ? -1 : 1
      return a.name.localeCompare(b.name, 'zh-Hans-CN')
    })
}

export class WorkFsService {
  private textCache = new Map<string, { size: number; mtime: number; text: string }>()

  constructor(private baseline: BaselineService) {}

  private rememberText(key: string, size: number, mtime: number, text: string) {
    if (Buffer.byteLength(text, 'utf8') > 2 * 1024 * 1024) return
    this.textCache.delete(key)
    this.textCache.set(key, { size, mtime, text })
    while (this.textCache.size > 16) {
      const oldest = this.textCache.keys().next().value
      if (!oldest) break
      this.textCache.delete(oldest)
    }
  }

  private invalidateText(abs: string) {
    for (const key of this.textCache.keys()) {
      const cachedAbs = key.startsWith('docx:') ? key.slice(5) : key
      if (cachedAbs === abs || cachedAbs.startsWith(abs + path.sep)) this.textCache.delete(key)
    }
  }

  /** Full recursive tree (flat, dirs first), with baseline change markers. */
  async tree(root: string): Promise<SkillTreeEntry[]> {
    const status = await this.baseline.statusMap(root)
    const out: SkillTreeEntry[] = []
    let count = 0
    let capped = false
    const walk = async (relDir: string, depth: number): Promise<void> => {
      if (depth > TREE_DEPTH_LIMIT || capped) return
      const absDir = relDir ? path.join(root, relDir) : root
      let entries: Dirent[]
      try {
        entries = sortDirents(await fs.readdir(absDir, { withFileTypes: true }))
      } catch {
        return
      }
      for (const ent of entries) {
        if (count >= TREE_ENTRY_LIMIT) {
          capped = true
          return
        }
        const rel = relDir ? `${relDir}/${ent.name}` : ent.name
        const abs = path.join(root, rel)
        const isDir = ent.isDirectory()
        let size = 0
        let mtime = 0
        try {
          const st = await fs.stat(abs)
          size = st.size
          mtime = Math.floor(st.mtimeMs)
        } catch {
          continue
        }
        count++
        out.push({
          name: ent.name,
          path: rel,
          depth,
          is_dir: isDir,
          size,
          mtime,
          status: isDir ? '' : (status.get(rel) ?? ''),
        })
        if (isDir) await walk(rel, depth + 1)
      }
    }
    await walk('', 0)
    if (capped) {
      out.push({ name: TREE_LIMIT_MARKER, path: TREE_LIMIT_MARKER, depth: 0, is_dir: false, truncated: true })
    }
    return out
  }

  /** Shallow single-directory page (dirs first, alpha). */
  async dir(root: string, rel = '', offset = 0, limit = DIR_PAGE_DEFAULT): Promise<WorkDirListing> {
    const clampedLimit = Math.min(5000, Math.max(50, Math.floor(limit) || DIR_PAGE_DEFAULT))
    const absDir = rel ? resolveWithin(root, rel) : root
    const cleanRel = rel ? validateRelPath(rel) : ''
    let entries: Dirent[]
    try {
      entries = sortDirents(await fs.readdir(absDir, { withFileTypes: true }))
    } catch {
      throw new Error('目录不存在或不可读')
    }
    const total = entries.length
    const page = entries.slice(offset, offset + clampedLimit)
    const depth = cleanRel ? cleanRel.split('/').length : 0
    const out: SkillTreeEntry[] = []
    const fileEntries: Array<{ rel: string; size: number; mtime: number }> = []
    for (const ent of page) {
      const entryRel = cleanRel ? `${cleanRel}/${ent.name}` : ent.name
      let size = 0
      let mtime = 0
      try {
        const st = await fs.stat(path.join(root, entryRel))
        size = st.size
        mtime = st.mtimeMs
      } catch {
        continue
      }
      out.push({
        name: ent.name,
        path: entryRel,
        depth,
        is_dir: ent.isDirectory(),
        size,
        mtime: Math.floor(mtime),
        status: '',
      })
      if (ent.isFile()) fileEntries.push({ rel: entryRel, size, mtime })
    }
    const status = await this.baseline.statusForEntries(root, fileEntries)
    for (const entry of out) {
      if (!entry.is_dir) entry.status = status.get(entry.path) ?? ''
    }
    return {
      entries: out,
      total,
      offset,
      limit: clampedLimit,
      has_more: offset + clampedLimit < total,
    }
  }

  /** Cheap recursive fingerprint used as a polling fallback. */
  async snapshot(root: string): Promise<WorkSnapshot> {
    let fileCount = 0
    let dirCount = 0
    let capped = false
    const parts: string[] = []
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
        if (fileCount + dirCount >= SNAPSHOT_LIMIT) {
          capped = true
          break
        }
        const rel = relDir ? `${relDir}/${ent.name}` : ent.name
        if (ent.isDirectory()) {
          dirCount++
          stack.push(rel)
        } else {
          fileCount++
          try {
            const st = await fs.stat(path.join(root, rel))
            parts.push(`${rel}:${st.size}:${Math.floor(st.mtimeMs)}`)
          } catch {
            parts.push(rel)
          }
        }
      }
      if (capped) break
    }
    parts.sort()
    return {
      signature: fnv1a64(Buffer.from(parts.join('\n'), 'utf8')),
      file_count: fileCount,
      dir_count: dirCount,
      capped,
    }
  }

  async isEmpty(root: string): Promise<boolean> {
    let entries: Dirent[]
    try {
      entries = await fs.readdir(root, { withFileTypes: true })
    } catch {
      return true
    }
    return entries.every((e) => isIgnoredName(e.name) || e.name.startsWith('.') || e.name.startsWith('_'))
  }

  async readFile(root: string, rel: string): Promise<string> {
    const abs = resolveWithin(root, rel)
    const st = await fs.stat(abs)
    if (st.size > TEXT_EDIT_LIMIT) throw new Error('文件过大,无法以文本方式打开(上限 20 MB)')
    const cached = this.textCache.get(abs)
    if (cached && cached.size === st.size && cached.mtime === st.mtimeMs) {
      this.textCache.delete(abs)
      this.textCache.set(abs, cached)
      return cached.text
    }
    const buf = await fs.readFile(abs)
    if (looksBinary(buf)) throw new Error('二进制文件,无法以文本方式打开')
    const text = decodeTextBuffer(buf)
    this.rememberText(abs, st.size, st.mtimeMs, text)
    return text
  }

  async readDocx(root: string, rel: string): Promise<string> {
    const abs = resolveWithin(root, rel)
    const st = await fs.stat(abs)
    if (st.size > DOCX_LIMIT) throw new Error('docx 文件过大(上限 80 MB)')
    const key = `docx:${abs}`
    const cached = this.textCache.get(key)
    if (cached && cached.size === st.size && cached.mtime === st.mtimeMs) {
      this.textCache.delete(key)
      this.textCache.set(key, cached)
      return cached.text
    }
    const text = await readDocxText(abs)
    this.rememberText(key, st.size, st.mtimeMs, text)
    return text
  }

  async writeFile(root: string, rel: string, text: string, expectedMtime?: number | null): Promise<WorkFileWriteResult> {
    const abs = resolveWithin(root, rel)
    const st = await fs.stat(abs).catch(() => {
      throw new Error('文件不存在,无法保存')
    })
    if (Buffer.byteLength(text, 'utf8') > TEXT_EDIT_LIMIT) throw new Error('内容过大,无法保存(上限 20 MB)')
    if (text.includes('\0')) throw new Error('内容包含非法字符,无法保存')
    if (expectedMtime != null && Math.floor(st.mtimeMs) !== Math.floor(expectedMtime)) {
      throw new Error('文件已被外部修改,请刷新后再保存')
    }
    await fs.writeFile(abs, text, 'utf8')
    const after = await fs.stat(abs)
    this.rememberText(abs, after.size, after.mtimeMs, text)
    return { size: after.size, mtime: Math.floor(after.mtimeMs) }
  }

  async saveCanvasCapture(root: string, imageData: string, label: string): Promise<{ rel: string; path: string }> {
    const prefix = 'data:image/png;base64,'
    if (!imageData.startsWith(prefix)) throw new Error('截图数据格式不支持')
    const b64 = imageData.slice(prefix.length)
    const buf = Buffer.from(b64, 'base64')
    if (buf.length === 0 || buf.length > CAPTURE_LIMIT) throw new Error('截图数据过大或为空')
    const safeLabel = label.replace(/[\\/:*?"<>|\s]+/g, '_').slice(0, 80) || 'capture'
    const rel = `画布/${safeLabel}_${Date.now()}.png`
    const abs = resolveWithin(root, rel)
    await fs.mkdir(path.dirname(abs), { recursive: true })
    await fs.writeFile(abs, buf)
    return { rel, path: abs }
  }

  async createEntry(root: string, parentRel: string, name: string, kind: 'file' | 'folder'): Promise<string> {
    if (!name || /[\\/:*?"<>|]/.test(name) || name === '.' || name === '..') {
      throw new Error('名称包含非法字符')
    }
    const rel = parentRel ? `${validateRelPath(parentRel)}/${name}` : name
    const abs = resolveWithin(root, rel)
    try {
      await fs.access(abs)
      throw new Error('同名文件或文件夹已存在')
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code !== 'ENOENT') throw e
    }
    if (kind === 'folder') {
      await fs.mkdir(abs, { recursive: true })
    } else {
      await fs.mkdir(path.dirname(abs), { recursive: true })
      await fs.writeFile(abs, '', 'utf8')
    }
    return rel
  }

  async renameEntry(root: string, rel: string, newName: string): Promise<string> {
    if (!newName || /[\\/:*?"<>|]/.test(newName) || newName === '.' || newName === '..') {
      throw new Error('名称包含非法字符')
    }
    const abs = resolveWithin(root, rel)
    const cleanRel = validateRelPath(rel)
    const parent = cleanRel.includes('/') ? cleanRel.slice(0, cleanRel.lastIndexOf('/')) : ''
    const newRel = parent ? `${parent}/${newName}` : newName
    const newAbs = resolveWithin(root, newRel)
    try {
      await fs.access(newAbs)
      throw new Error('同名文件或文件夹已存在')
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code !== 'ENOENT') throw e
    }
    await fs.rename(abs, newAbs)
    this.invalidateText(abs)
    return newRel
  }

  async deleteEntry(root: string, rel: string): Promise<void> {
    const cleanRel = validateRelPath(rel)
    if (!cleanRel) throw new Error('不能删除作品根目录')
    const abs = resolveWithin(root, cleanRel)
    this.invalidateText(abs)
    await shell.trashItem(abs)
  }

  async importSources(root: string, sources: string[]): Promise<string[]> {
    const imported: string[] = []
    for (const src of sources) {
      const ext = path.extname(src).slice(1).toLowerCase()
      if (!IMPORT_EXTENSIONS.has(ext)) continue
      let name = path.basename(src)
      let target = path.join(root, name)
      let n = 2
      while (await fs.access(target).then(() => true, () => false)) {
        const stem = name.slice(0, name.length - path.extname(name).length)
        target = path.join(root, `${stem}(${n})${path.extname(name)}`)
        n++
      }
      await fs.copyFile(src, target)
      imported.push(path.basename(target))
    }
    return imported
  }

  /** Single-novel init: rename the empty work dir after the novel and copy it into 小说/. */
  async importN2dNovel(root: string, sources: string[]): Promise<ImportWorkSourcesResult> {
    const src = sources.find((s) => IMPORT_EXTENSIONS.has(path.extname(s).slice(1).toLowerCase()))
    if (!src) throw new Error('未找到可导入的小说文件(支持 txt/md/docx/pdf)')
    const stem = path.basename(src).replace(path.extname(src), '').trim() || '新作品'
    const parent = path.dirname(root)
    let newRoot = root
    let name = path.basename(root)
    const targetRoot = path.join(parent, stem)
    if (targetRoot !== root) {
      try {
        await fs.access(targetRoot)
        // target exists — keep current dir name
      } catch {
        await fs.rename(root, targetRoot)
        newRoot = targetRoot
        name = stem
      }
    }
    const novelDir = path.join(newRoot, '小说')
    await fs.mkdir(novelDir, { recursive: true })
    const dest = path.join(novelDir, path.basename(src))
    await fs.copyFile(src, dest)
    return { root: newRoot, name, imported: [`小说/${path.basename(src)}`] }
  }

  async revealEntry(root: string, rel: string): Promise<void> {
    const abs = rel ? resolveWithin(root, rel) : root
    shell.showItemInFolder(abs)
  }

  async openEntry(root: string, rel: string): Promise<void> {
    const abs = rel ? resolveWithin(root, rel) : root
    const err = await shell.openPath(abs)
    if (err) throw new Error(err)
  }

  async search(
    root: string,
    query: string,
    caseSensitive = false,
    wholeWord = false,
    useRegex = false,
  ): Promise<WorkSearchResponse> {
    const trimmed = query.trim()
    if (!trimmed) return { query, results: [], scanned: 0, capped: false }
    let pattern = useRegex ? trimmed : trimmed.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    if (wholeWord) pattern = `\\b${pattern}\\b`
    let re: RegExp
    try {
      re = new RegExp(pattern, caseSensitive ? '' : 'i')
    } catch {
      throw new Error('正则表达式无效')
    }

    const results: WorkSearchResult[] = []
    let scanned = 0
    let capped = false
    const stack: { rel: string; depth: number }[] = [{ rel: '', depth: 0 }]
    while (stack.length > 0 && results.length < SEARCH_RESULT_LIMIT) {
      const { rel: relDir, depth } = stack.pop()!
      if (depth > SEARCH_DEPTH_LIMIT) continue
      const absDir = relDir ? path.join(root, relDir) : root
      let entries: Dirent[]
      try {
        entries = sortDirents(await fs.readdir(absDir, { withFileTypes: true }))
      } catch {
        continue
      }
      for (const ent of entries) {
        if (results.length >= SEARCH_RESULT_LIMIT) {
          capped = true
          break
        }
        const rel = relDir ? `${relDir}/${ent.name}` : ent.name
        if (ent.isDirectory()) {
          stack.push({ rel, depth: depth + 1 })
          continue
        }
        if (scanned >= SEARCH_FILE_LIMIT) {
          capped = true
          break
        }
        scanned++
        const nameMatch = re.test(ent.name)
        const ext = path.extname(ent.name).slice(1).toLowerCase()
        const matches: { line: number; preview: string }[] = []
        let size = 0
        if (TEXT_EXTENSIONS.has(ext)) {
          try {
            const st = await fs.stat(path.join(root, rel))
            size = st.size
            if (st.size <= SEARCH_SIZE_LIMIT) {
              const buf = await fs.readFile(path.join(root, rel))
              if (!looksBinary(buf)) {
                const lines = decodeTextBuffer(buf).split(/\r?\n/)
                for (let i = 0; i < lines.length && matches.length < SEARCH_MATCHES_PER_FILE; i++) {
                  if (re.test(lines[i])) {
                    matches.push({ line: i + 1, preview: lines[i].trim().slice(0, SEARCH_PREVIEW_CHARS) })
                  }
                }
              }
            }
          } catch {
            // unreadable file — skip content search
          }
        }
        if (nameMatch || matches.length > 0) {
          results.push({ path: rel, name: ent.name, size, name_match: nameMatch, matches })
        }
      }
    }
    return { query, results, scanned, capped }
  }
}
