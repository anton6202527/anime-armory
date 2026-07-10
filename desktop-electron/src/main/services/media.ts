import http from 'node:http'
import { createReadStream, realpathSync, statSync } from 'node:fs'
import path from 'node:path'

const MIME: Record<string, string> = {
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  webp: 'image/webp',
  gif: 'image/gif',
  bmp: 'image/bmp',
  svg: 'image/svg+xml',
  mp4: 'video/mp4',
  m4v: 'video/mp4',
  mov: 'video/quicktime',
  webm: 'video/webm',
  wav: 'audio/wav',
  mp3: 'audio/mpeg',
  m4a: 'audio/mp4',
  aac: 'audio/aac',
  flac: 'audio/flac',
  ogg: 'audio/ogg',
}

/**
 * Localhost static media server with HTTP Range support (video scrubbing).
 * Same URL contract as the Tauri app: GET /media?path=<encoded abs path>&v=…
 * Serving is confined to explicitly allowed roots.
 */
export class MediaService {
  private server: http.Server | null = null
  private port = 0
  private allowedRoots: string[] = []

  allowRoot(root: string) {
    try {
      const real = realpathSync(root)
      if (!this.allowedRoots.includes(real)) this.allowedRoots.push(real)
    } catch {
      throw new Error('目录不存在,无法允许媒体访问')
    }
  }

  private isAllowed(p: string): boolean {
    return this.allowedRoots.some((root) => p === root || p.startsWith(root + path.sep))
  }

  async start(): Promise<number> {
    if (this.server) return this.port
    const server = http.createServer((req, res) => this.handle(req, res))
    await new Promise<void>((resolve, reject) => {
      server.once('error', reject)
      server.listen(0, '127.0.0.1', () => resolve())
    })
    this.server = server
    const addr = server.address()
    this.port = typeof addr === 'object' && addr ? addr.port : 0
    return this.port
  }

  private handle(req: http.IncomingMessage, res: http.ServerResponse) {
    const url = new URL(req.url ?? '/', 'http://127.0.0.1')
    if (url.pathname !== '/media') {
      res.writeHead(404).end()
      return
    }
    const raw = url.searchParams.get('path')
    if (!raw) {
      res.writeHead(400).end('missing path')
      return
    }
    let real: string
    let size: number
    try {
      real = realpathSync(raw)
      const st = statSync(real)
      if (!st.isFile()) throw new Error('not a file')
      size = st.size
    } catch {
      res.writeHead(404).end()
      return
    }
    if (!this.isAllowed(real)) {
      res.writeHead(403).end()
      return
    }
    const ext = path.extname(real).slice(1).toLowerCase()
    const headers: Record<string, string> = {
      'Content-Type': MIME[ext] ?? 'application/octet-stream',
      'Accept-Ranges': 'bytes',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Range',
      'X-Content-Type-Options': 'nosniff',
    }
    const range = req.headers.range
    const m = range ? /^bytes=(\d+)-(\d*)$/.exec(range) : null
    if (m) {
      const start = Number(m[1])
      const end = m[2] ? Math.min(Number(m[2]), size - 1) : size - 1
      if (start >= size || start > end) {
        res.writeHead(416, { 'Content-Range': `bytes */${size}` }).end()
        return
      }
      headers['Content-Range'] = `bytes ${start}-${end}/${size}`
      headers['Content-Length'] = String(end - start + 1)
      res.writeHead(206, headers)
      createReadStream(real, { start, end }).pipe(res)
    } else {
      headers['Content-Length'] = String(size)
      res.writeHead(200, headers)
      createReadStream(real).pipe(res)
    }
  }

  dispose() {
    this.server?.close()
    this.server = null
  }
}
