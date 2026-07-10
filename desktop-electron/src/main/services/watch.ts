import chokidar, { type FSWatcher } from 'chokidar'
import { existsSync } from 'node:fs'
import path from 'node:path'
import type { WebContents } from 'electron'

/**
 * Per-work file watching. Mirrors the Rust watcher's scope: the root itself
 * (shallow) plus the production sub-trees, with a 300ms debounce, emitting
 * `fs-changed { root }` to the renderer.
 */
export class WatchService {
  private watchers = new Map<string, FSWatcher>()
  private lastEmit = new Map<string, number>()
  private pending = new Map<string, NodeJS.Timeout>()
  private sink: WebContents | null = null

  attach(sink: WebContents) {
    this.sink = sink
  }

  private emitChanged(root: string) {
    const now = Date.now()
    const last = this.lastEmit.get(root) ?? 0
    const fire = () => {
      this.lastEmit.set(root, Date.now())
      this.pending.delete(root)
      if (this.sink && !this.sink.isDestroyed()) this.sink.send('fs-changed', { root })
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
    watcher.on('all', (event) => {
      if (event === 'addDir' && event.length === 0) return
      this.emitChanged(root)
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
    await w.close()
  }

  async disposeAll() {
    await Promise.allSettled([...this.watchers.keys()].map((r) => this.unwatch(r)))
  }
}
