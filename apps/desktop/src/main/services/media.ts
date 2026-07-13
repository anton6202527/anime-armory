import http from 'node:http'
import { createReadStream, existsSync, realpathSync, statSync } from 'node:fs'
import { mkdir, rename, stat, unlink } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { spawn, type ChildProcess } from 'node:child_process'
import os from 'node:os'
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
  private videoJobs = new Map<string, Promise<string>>()
  private resolvedVideos = new Map<string, string>()
  private workers = new Set<ChildProcess>()

  // Roots accumulate as the user switches works; keep a bounded LRU so a long
  // session doesn't grow the allowlist (and the per-request linear scan) forever.
  private static readonly MAX_ALLOWED_ROOTS = 16

  allowRoot(root: string) {
    try {
      const real = realpathSync(root)
      const idx = this.allowedRoots.indexOf(real)
      if (idx !== -1) this.allowedRoots.splice(idx, 1)
      this.allowedRoots.push(real)
      if (this.allowedRoots.length > MediaService.MAX_ALLOWED_ROOTS) this.allowedRoots.shift()
    } catch {
      throw new Error('目录不存在,无法允许媒体访问')
    }
  }

  private isAllowed(p: string): boolean {
    return this.allowedRoots.some((root) => p === root || p.startsWith(root + path.sep))
  }

  async start(): Promise<number> {
    if (this.server) return this.port
    const server = http.createServer((req, res) => {
      void this.handle(req, res).catch((error) => {
        if (res.headersSent) {
          res.destroy(error instanceof Error ? error : undefined)
          return
        }
        res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' })
        res.end(error instanceof Error ? error.message : String(error))
      })
    })
    await new Promise<void>((resolve, reject) => {
      server.once('error', reject)
      server.listen(0, '127.0.0.1', () => resolve())
    })
    this.server = server
    const addr = server.address()
    this.port = typeof addr === 'object' && addr ? addr.port : 0
    return this.port
  }

  private resolveAllowedFile(raw: string): string | null {
    try {
      const real = realpathSync(raw)
      const st = statSync(real)
      if (!st.isFile() || !this.isAllowed(real)) return null
      return real
    } catch {
      return null
    }
  }

  private toolPath(name: 'ffmpeg' | 'ffprobe'): string {
    const envName = name === 'ffmpeg' ? process.env.FFMPEG_PATH : process.env.FFPROBE_PATH
    if (envName) return envName
    const candidates = process.platform === 'win32'
      ? [name]
      : [`/opt/homebrew/bin/${name}`, `/usr/local/bin/${name}`, `/usr/bin/${name}`, name]
    return candidates.find((candidate) => !path.isAbsolute(candidate) || existsSync(candidate)) ?? name
  }

  private runTool(command: string, args: string[], collectStdout = false): Promise<string> {
    return new Promise((resolve, reject) => {
      const worker = spawn(command, args, {
        windowsHide: true,
        stdio: ['ignore', collectStdout ? 'pipe' : 'ignore', 'pipe'],
      })
      this.workers.add(worker)
      let stdout = ''
      let stderr = ''
      worker.stdout?.on('data', (chunk: Buffer) => {
        if (stdout.length < 2_000_000) stdout += chunk.toString('utf8')
      })
      worker.stderr?.on('data', (chunk: Buffer) => {
        stderr = (stderr + chunk.toString('utf8')).slice(-16_000)
      })
      worker.once('error', (error) => {
        this.workers.delete(worker)
        reject(error)
      })
      worker.once('close', (code) => {
        this.workers.delete(worker)
        if (code === 0) resolve(stdout)
        else reject(new Error(stderr.trim() || `${path.basename(command)} exited with code ${code}`))
      })
    })
  }

  private async browserCanPlay(real: string): Promise<boolean> {
    const ext = path.extname(real).slice(1).toLowerCase()
    try {
      const stdout = await this.runTool(
        this.toolPath('ffprobe'),
        ['-v', 'error', '-show_entries', 'stream=codec_type,codec_name,pix_fmt', '-of', 'json', real],
        true,
      )
      const parsed = JSON.parse(stdout) as {
        streams?: Array<{ codec_type?: string; codec_name?: string; pix_fmt?: string }>
      }
      const streams = parsed.streams ?? []
      const video = streams.find((stream) => stream.codec_type === 'video')
      const audio = streams.filter((stream) => stream.codec_type === 'audio')
      if (!video?.codec_name) return false
      if (ext === 'mp4' || ext === 'm4v') {
        const safePixelFormat = !video.pix_fmt || ['yuv420p', 'yuvj420p', 'nv12'].includes(video.pix_fmt)
        return video.codec_name === 'h264' && safePixelFormat && audio.every((stream) =>
          !stream.codec_name || ['aac', 'mp3'].includes(stream.codec_name),
        )
      }
      if (ext === 'webm') {
        return ['vp8', 'vp9', 'av1'].includes(video.codec_name) && audio.every((stream) =>
          !stream.codec_name || ['opus', 'vorbis'].includes(stream.codec_name),
        )
      }
      return false
    } catch {
      return false
    }
  }

  private async compatibleVideo(real: string): Promise<string> {
    const source = await stat(real)
    const key = createHash('sha256')
      .update(`${real}\0${source.size}\0${source.mtimeMs}`)
      .digest('hex')
    const resolved = this.resolvedVideos.get(key)
    if (resolved) return resolved
    const existing = this.videoJobs.get(key)
    if (existing) return existing
    const cacheDir = path.join(os.tmpdir(), 'anime-armory-media-cache')
    const output = path.join(cacheDir, `${key}.mp4`)
    const job = (async () => {
      if (await this.browserCanPlay(real)) return real
      try {
        const cached = await stat(output)
        if (cached.isFile() && cached.size > 0) return output
      } catch {
        // Cache miss.
      }
      await mkdir(cacheDir, { recursive: true })
      const temp = path.join(cacheDir, `${key}.${process.pid}.${Date.now()}.tmp.mp4`)
      try {
        await this.runTool(this.toolPath('ffmpeg'), [
          '-hide_banner', '-loglevel', 'error', '-y', '-i', real,
          '-map', '0:v:0', '-map', '0:a:0?',
          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
          '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', temp,
        ])
        await rename(temp, output)
        return output
      } catch (error) {
        await unlink(temp).catch(() => {})
        throw error
      }
    })()
    this.videoJobs.set(key, job)
    try {
      const result = await job
      this.resolvedVideos.set(key, result)
      while (this.resolvedVideos.size > 64) {
        const oldest = this.resolvedVideos.keys().next().value
        if (!oldest) break
        this.resolvedVideos.delete(oldest)
      }
      return result
    } finally {
      this.videoJobs.delete(key)
    }
  }

  private serve(req: http.IncomingMessage, res: http.ServerResponse, real: string, mime?: string) {
    const size = statSync(real).size
    const ext = path.extname(real).slice(1).toLowerCase()
    const headers: Record<string, string> = {
      'Content-Type': mime ?? MIME[ext] ?? 'application/octet-stream',
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
      if (req.method === 'HEAD') res.end()
      else createReadStream(real, { start, end }).pipe(res)
      return
    }
    headers['Content-Length'] = String(size)
    res.writeHead(200, headers)
    if (req.method === 'HEAD') res.end()
    else createReadStream(real).pipe(res)
  }

  private async handle(req: http.IncomingMessage, res: http.ServerResponse) {
    const url = new URL(req.url ?? '/', 'http://127.0.0.1')
    if (url.pathname !== '/media' && url.pathname !== '/video') {
      res.writeHead(404).end()
      return
    }
    const raw = url.searchParams.get('path')
    if (!raw) {
      res.writeHead(400).end('missing path')
      return
    }
    const real = this.resolveAllowedFile(raw)
    if (!real) {
      res.writeHead(404).end()
      return
    }
    if (url.pathname === '/video') {
      const compatible = await this.compatibleVideo(real)
      this.serve(req, res, compatible, compatible === real ? undefined : 'video/mp4')
      return
    }
    this.serve(req, res, real)
  }

  dispose() {
    for (const worker of this.workers) worker.kill()
    this.workers.clear()
    this.videoJobs.clear()
    this.resolvedVideos.clear()
    this.server?.close()
    this.server = null
  }
}
