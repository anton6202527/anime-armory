import pty from 'node-pty'
import type { WebContents } from 'electron'

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

  attach(sink: WebContents) {
    this.sink = sink
  }

  private emit(channel: 'pty-data' | 'pty-exit', payload: unknown) {
    if (this.sink && !this.sink.isDestroyed()) this.sink.send(channel, payload)
  }

  spawn(cwd: string, rows: number, cols: number): number {
    const shell = process.env.SHELL || (process.platform === 'win32' ? 'powershell.exe' : '/bin/zsh')
    const args = process.platform === 'win32' ? [] : ['-l']
    const proc = pty.spawn(shell, args, {
      name: 'xterm-256color',
      cwd,
      rows: Math.max(1, Math.floor(rows)),
      cols: Math.max(1, Math.floor(cols)),
      env: { ...process.env, TERM: 'xterm-256color' } as Record<string, string>,
    })
    const id = this.nextId++
    const dataSub = proc.onData((data) => {
      this.emit('pty-data', { id, data: Buffer.from(data, 'utf8').toString('base64') })
    })
    const exitSub = proc.onExit(() => {
      this.emit('pty-exit', { id })
      this.sessions.delete(id)
    })
    this.sessions.set(id, { proc, dataSub, exitSub })
    return id
  }

  write(id: number, data: string) {
    this.sessions.get(id)?.proc.write(data)
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
