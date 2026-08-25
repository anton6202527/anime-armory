import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import pty from 'node-pty'
import type { WebContents } from 'electron'

const nodeRequire = createRequire(import.meta.url)

function ensureMacSpawnHelper(): string | null {
  if (process.platform !== 'darwin') return null
  const packageJson = nodeRequire.resolve('node-pty/package.json')
  const packageRoot = path.dirname(packageJson)
  const virtualHelper = path.join(packageRoot, 'prebuilds', `darwin-${process.arch}`, 'spawn-helper')
  const physicalHelper = virtualHelper.replace(
    `${path.sep}app.asar${path.sep}`,
    `${path.sep}app.asar.unpacked${path.sep}`,
  )
  const helper = fs.existsSync(physicalHelper) ? physicalHelper : virtualHelper
  if (!fs.existsSync(helper)) throw new Error(`node-pty spawn-helper is missing: ${helper}`)
  const mode = fs.statSync(helper).mode
  if ((mode & 0o111) === 0) fs.chmodSync(helper, mode | 0o755)
  return helper
}

interface PtySession {
  proc: pty.IPty
  dataSub: { dispose(): void }
  exitSub: { dispose(): void }
}

/**
 * PTY sessions bridged to the renderer as base64 `pty-data` events
 * (same wire format as the Tauri app, so TerminalPane ports unchanged).
 */
export class PtyService {
  private sessions = new Map<number, PtySession>()
  private nextId = 1
  private sink: WebContents | null = null
  private helperReady = false

  attach(sink: WebContents) {
    this.sink = sink
  }

  private emit(channel: 'pty-data' | 'pty-exit', payload: unknown) {
    if (this.sink && !this.sink.isDestroyed()) this.sink.send(channel, payload)
  }

  spawn(cwd: string, rows: number, cols: number): number {
    if (!this.helperReady) {
      ensureMacSpawnHelper()
      this.helperReady = true
    }
    const shell = process.env.SHELL || (process.platform === 'win32' ? 'powershell.exe' : '/bin/zsh')
    const args = process.platform === 'win32' ? [] : ['-l']
    let proc: pty.IPty
    try {
      proc = pty.spawn(shell, args, {
        name: 'xterm-256color',
        cwd,
        rows: Math.max(1, Math.floor(rows)),
        cols: Math.max(1, Math.floor(cols)),
        env: { ...process.env, TERM: 'xterm-256color' } as Record<string, string>,
      })
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error)
      throw new Error(`Unable to start terminal shell ${shell}: ${detail}`)
    }
    const id = this.nextId++
    const dataSub = proc.onData((data) => {
      this.emit('pty-data', { id, data: Buffer.from(data, 'utf8').toString('base64') })
    })
    const exitSub = proc.onExit(({ exitCode, signal }) => {
      this.emit('pty-exit', { id, exitCode, signal })
      this.sessions.delete(id)
    })
    this.sessions.set(id, { proc, dataSub, exitSub })
    return id
  }

  write(id: number, data: string): true {
    const session = this.sessions.get(id)
    if (!session) throw new Error(`PTY session is not live: ${id}`)
    session.proc.write(data)
    return true
  }

  resize(id: number, rows: number, cols: number) {
    this.sessions.get(id)?.proc.resize(Math.max(1, Math.floor(cols)), Math.max(1, Math.floor(rows)))
  }

  kill(id: number) {
    const s = this.sessions.get(id)
    if (!s) return
    this.sessions.delete(id)
    s.dataSub.dispose()
    s.exitSub.dispose()
    try {
      s.proc.kill()
    } catch {
      // already dead
    }
  }

  disposeAll() {
    for (const id of [...this.sessions.keys()]) this.kill(id)
  }
}
