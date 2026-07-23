import chokidar, { type FSWatcher } from 'chokidar'
import { existsSync } from 'node:fs'
import path from 'node:path'
import type { WebContents } from 'electron'

/**
 * Per-work file watching. Mirrors the Rust watcher's scope: the root itself
 * (shallow) plus the production sub-trees, with a 300ms debounce, emitting
 * `fs-changed { root }` to the renderer.
 */
// Above this many distinct changed directories in one debounce window we stop
// tracking individual dirs and tell the renderer to do a broad refresh — past
// this point the per-dir bookkeeping costs more than it saves.
const MAX_TRACKED_DIRS = 48

export class WatchService {
  private watchers = new Map<string, FSWatcher>()
  private lastEmit = new Map<string, number>()
  private pending = new Map<string, NodeJS.Timeout>()
  // Parent dirs (relative to root, '' for root-level) touched since the last emit.
  // `null` = broad/unknown → renderer refreshes everything it has open.
  private changedDirs = new Map<string, Set<string> | null>()
  private sink: WebContents | null = null

  attach(sink: WebContents) {
    this.sink = sink
  }

  /** Record the parent dir of a changed path so the renderer can refresh only
   *  the affected folders instead of re-listing the whole open tree. */
  private noteChange(root: string, changedPath: string) {
    const existing = this.changedDirs.get(root)
    if (existing === null) return // already broad
    const set = existing ?? new Set<string>()
    const relDir = path.relative(root, path.dirname(changedPath)).split(path.sep).join('/')
    set.add(relDir.startsWith('..') ? '' : relDir)
    if (set.size > MAX_TRACKED_DIRS) {
      this.changedDirs.set(root, null) // too many — fall back to broad refresh
    } else {
      this.changedDirs.set(root, set)
    }
    this.emitChanged(root)
  }

  private emitChanged(root: string) {
    const now = Date.now()
    const last = this.lastEmit.get(root) ?? 0
    const fire = () => {
      this.lastEmit.set(root, Date.now())
      this.pending.delete(root)
      const tracked = this.changedDirs.get(root)
      this.changedDirs.delete(root)
      const dirs = tracked ? [...tracked] : undefined // undefined = broad refresh
      if (this.sink && !this.sink.isDestroyed()) this.sink.send('fs-changed', { root, dirs })
    }
    if (now - last >= 300) {
      fire()
    } else if (!this.pending.has(root)) {
      this.pending.set(root, setTimeout(fire, 300 - (now - last)))
    }
  }

  watch(root: string) {
    if (this.watchers.has(root)) return
    const shallow = [root]
    const deep: string[] = []
    for (const [name, recursive] of [
      ['脚本', true],
      ['设定库', true],
      ['生产数据', false],
      ['生产数据/episodes', false],
      ['生产数据/visuals', false],
      ['出图', false],
      ['出视频', false],
      ['配音', false],
    ] as [string, boolean][]) {
      const p = path.join(root, name)
      if (existsSync(p)) (recursive ? deep : shallow).push(p)
    }
    const watcher = chokidar.watch([...shallow, ...deep], {
      ignoreInitial: true,
      // shallow paths watch one level; chokidar depth applies per glob-less path,
      // so use depth 1 for the shallow set and rely on the explicit deep list.
      depth: 1,
      ignored: (p: string) => {
        const base = path.basename(p)
        return base === '.DS_Store' || base === '__pycache__' || base === '_voicecache' || base === '.git'
      },
    })
    for (const dir of deep) watcher.add(dir) // chokidar dedupes; deep dirs get default depth
    watcher.on('all', (_event: string, changedPath?: string) => {
      if (changedPath) this.noteChange(root, changedPath)
      else this.emitChanged(root)
    })
    this.watchers.set(root, watcher)
  }

  async unwatch(root: string) {
    const w = this.watchers.get(root)
    if (!w) return
    this.watchers.delete(root)
    const t = this.pending.get(root)
    if (t) clearTimeout(t)
    this.pending.delete(root)
    this.changedDirs.delete(root)
    await w.close()
  }

  async disposeAll() {
    await Promise.allSettled([...this.watchers.keys()].map((r) => this.unwatch(r)))
  }
}
