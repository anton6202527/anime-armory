import { app, safeStorage, type WebContents } from 'electron'
import { createHash, randomUUID } from 'node:crypto'
import { openAsBlob } from 'node:fs'
import fs from 'node:fs/promises'
import path from 'node:path'
import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import { AssetApiClient } from '@anime-armory/cloud-client'
import type { AssetRecord, CloudProjectRecord } from '@anime-armory/contracts'
import type {
  CloudAuthStatus,
  CloudProjectBinding,
  CloudProjectInfo,
  CloudPublicConfig,
  CloudSyncDirection,
  CloudSyncProgress,
  CloudSyncResult,
} from '@shared/types'

const INTERNAL_DIR = '.anime-armory'
const BINDING_FILE = 'cloud.json'
const SKIP_DIRECTORIES = new Set([
  INTERNAL_DIR,
  '.git',
  '.svn',
  '.hg',
  'node_modules',
  '__pycache__',
  '.pytest_cache',
  '.venv',
  'venv',
])
const SKIP_FILES = new Set(['.DS_Store', 'Thumbs.db', 'desktop.ini'])
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

interface ClientEntry {
  client: SupabaseClient
  storage: EncryptedSessionStorage
  config: CloudPublicConfig
}

interface LocalFile {
  absolutePath: string
  relativePath: string
  name: string
  contentType: string
  size: number
  sha256: string
}

interface FileCandidate {
  absolutePath: string
  relativePath: string
  name: string
  contentType: string
  size: number
}

function normalizeEndpoint(raw: string, field: string): string {
  let url: URL
  try {
    url = new URL(raw.trim())
  } catch {
    throw new Error(`${field} 不是有效 URL`)
  }
  const local = url.hostname === 'localhost' || url.hostname === '127.0.0.1'
  if (url.protocol !== 'https:' && !(local && url.protocol === 'http:')) {
    throw new Error(`${field} 必须使用 HTTPS（本地开发除外）`)
  }
  if (url.username || url.password) throw new Error(`${field} 不能包含 URL 凭据`)
  return url.toString().replace(/\/$/, '')
}

function validateConfig(input: CloudPublicConfig): CloudPublicConfig {
  const supabaseUrl = normalizeEndpoint(input.supabaseUrl, 'Supabase URL')
  const assetApiUrl = normalizeEndpoint(input.assetApiUrl, 'Asset API URL')
  if (new URL(supabaseUrl).hostname !== new URL(assetApiUrl).hostname) {
    throw new Error('Asset API 必须与 Supabase 使用同一主机')
  }
  const supabasePublishableKey = input.supabasePublishableKey.trim()
  if (!supabasePublishableKey || supabasePublishableKey.length > 4096) {
    throw new Error('Supabase Publishable Key 未配置或格式异常')
  }
  return { supabaseUrl, supabasePublishableKey, assetApiUrl }
}

function storageScope(config: CloudPublicConfig): string {
  return createHash('sha256').update(config.supabaseUrl).digest('hex').slice(0, 20)
}

class EncryptedSessionStorage {
  private values: Record<string, string> | null = null

  constructor(private readonly scope: string) {}

  get persistent(): boolean {
    return safeStorage.isEncryptionAvailable()
  }

  private filePath(): string {
    return path.join(app.getPath('userData'), 'cloud', `auth-${this.scope}.bin`)
  }

  private async load(): Promise<Record<string, string>> {
    if (this.values) return this.values
    if (!this.persistent) {
      this.values = {}
      return this.values
    }
    try {
      const encrypted = await fs.readFile(this.filePath())
      const raw = safeStorage.decryptString(encrypted)
      const parsed: unknown = JSON.parse(raw)
      this.values = parsed && typeof parsed === 'object' && !Array.isArray(parsed)
        ? parsed as Record<string, string>
        : {}
    } catch (error) {
      const code = (error as NodeJS.ErrnoException).code
      if (code !== 'ENOENT') console.warn('[cloud] 无法读取加密登录会话，将使用空会话')
      this.values = {}
    }
    return this.values
  }

  private async persist(): Promise<void> {
    if (!this.persistent || !this.values) return
    const file = this.filePath()
    await fs.mkdir(path.dirname(file), { recursive: true, mode: 0o700 })
    const encrypted = safeStorage.encryptString(JSON.stringify(this.values))
    const temp = `${file}.${process.pid}.${randomUUID()}.tmp`
    await fs.writeFile(temp, encrypted, { mode: 0o600 })
    await fs.rename(temp, file)
  }

  async getItem(key: string): Promise<string | null> {
    const values = await this.load()
    return values[key] ?? null
  }

  async setItem(key: string, value: string): Promise<void> {
    const values = await this.load()
    values[key] = value
    await this.persist()
  }

  async removeItem(key: string): Promise<void> {
    const values = await this.load()
    delete values[key]
    await this.persist()
  }
}

function toProject(project: CloudProjectRecord): CloudProjectInfo {
  return {
    id: project.id,
    name: project.name,
    clientKey: project.clientKey,
    role: project.role,
    createdAt: project.createdAt,
    updatedAt: project.updatedAt,
  }
}

function mimeType(fileName: string): string {
  const extension = path.extname(fileName).toLowerCase()
  return ({
    '.txt': 'text/plain',
    '.md': 'text/markdown',
    '.json': 'application/json',
    '.yaml': 'application/yaml',
    '.yml': 'application/yaml',
    '.csv': 'text/csv',
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'text/javascript',
    '.ts': 'text/typescript',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.webp': 'image/webp',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.m4a': 'audio/mp4',
    '.flac': 'audio/flac',
    '.mp4': 'video/mp4',
    '.mov': 'video/quicktime',
    '.webm': 'video/webm',
    '.pdf': 'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.zip': 'application/zip',
  } as Record<string, string>)[extension] ?? 'application/octet-stream'
}

function assertOperationId(operationId: string): void {
  if (!/^[a-zA-Z0-9-]{8,80}$/.test(operationId)) throw new Error('同步操作 ID 无效')
}

function throwIfAborted(signal: AbortSignal): void {
  if (signal.aborted) throw new DOMException('同步已取消', 'AbortError')
}

async function sha256File(file: string, signal: AbortSignal): Promise<string> {
  const handle = await fs.open(file, 'r')
  const hash = createHash('sha256')
  const buffer = Buffer.allocUnsafe(1024 * 1024)
  try {
    while (true) {
      throwIfAborted(signal)
      const { bytesRead } = await handle.read(buffer, 0, buffer.length, null)
      if (bytesRead === 0) break
      hash.update(buffer.subarray(0, bytesRead))
    }
    return hash.digest('hex')
  } finally {
    await handle.close()
  }
}

async function validateRoot(root: string): Promise<string> {
  const resolved = await fs.realpath(root)
  const stat = await fs.stat(resolved)
  if (!stat.isDirectory()) throw new Error('作品根路径不是目录')
  return resolved
}

async function collectCandidates(root: string, signal: AbortSignal): Promise<FileCandidate[]> {
  const files: FileCandidate[] = []
  const visit = async (relativeDirectory: string): Promise<void> => {
    throwIfAborted(signal)
    const absoluteDirectory = path.join(root, relativeDirectory)
    const entries = await fs.readdir(absoluteDirectory, { withFileTypes: true })
    entries.sort((left, right) => left.name.localeCompare(right.name, 'zh-Hans-CN'))
    for (const entry of entries) {
      throwIfAborted(signal)
      if (entry.isSymbolicLink()) continue
      if (entry.isDirectory() && SKIP_DIRECTORIES.has(entry.name)) continue
      if (entry.isFile() && SKIP_FILES.has(entry.name)) continue
      const relativePath = path.posix.join(
        ...[relativeDirectory, entry.name].filter(Boolean).map((part) => part.split(path.sep).join('/')),
      )
      const absolutePath = path.join(root, relativePath)
      if (entry.isDirectory()) {
        await visit(relativePath)
      } else if (entry.isFile()) {
        if (relativePath.length > 1024) throw new Error(`相对路径超过 1024 字符：${relativePath}`)
        if (entry.name.length > 255) throw new Error(`文件名超过 255 字符：${relativePath}`)
        const stat = await fs.stat(absolutePath)
        files.push({
          absolutePath,
          relativePath,
          name: entry.name,
          contentType: mimeType(entry.name),
          size: stat.size,
        })
      }
    }
  }
  await visit('')
  return files
}

function bindingPath(root: string): string {
  return path.join(root, INTERNAL_DIR, BINDING_FILE)
}

function isBinding(value: unknown): value is CloudProjectBinding {
  if (!value || typeof value !== 'object') return false
  const record = value as Partial<CloudProjectBinding>
  return record.schemaVersion === 1
    && typeof record.projectId === 'string' && UUID_PATTERN.test(record.projectId)
    && typeof record.clientKey === 'string' && UUID_PATTERN.test(record.clientKey)
    && typeof record.projectName === 'string' && record.projectName.length > 0
    && typeof record.boundAt === 'string'
}

export class CloudService {
  private readonly clients = new Map<string, ClientEntry>()
  private readonly activeSyncs = new Map<string, AbortController>()
  private webContents: WebContents | null = null

  attach(webContents: WebContents): void {
    this.webContents = webContents
  }

  dispose(): void {
    for (const controller of this.activeSyncs.values()) controller.abort()
    this.activeSyncs.clear()
    for (const { client } of this.clients.values()) client.auth.stopAutoRefresh()
    this.clients.clear()
    this.webContents = null
  }

  private clientEntry(rawConfig: CloudPublicConfig): ClientEntry {
    const config = validateConfig(rawConfig)
    const key = `${config.supabaseUrl}\0${config.supabasePublishableKey}`
    const cached = this.clients.get(key)
    if (cached) return cached
    const storage = new EncryptedSessionStorage(storageScope(config))
    const client = createClient(config.supabaseUrl, config.supabasePublishableKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: false,
        storage,
      },
    })
    const entry = { client, storage, config }
    this.clients.set(key, entry)
    return entry
  }

  private async accessToken(config: CloudPublicConfig): Promise<string | null> {
    const { client } = this.clientEntry(config)
    const { data, error } = await client.auth.getSession()
    if (error) throw new Error(`读取登录会话失败：${error.message}`)
    return data.session?.access_token ?? null
  }

  private api(config: CloudPublicConfig): AssetApiClient {
    const entry = this.clientEntry(config)
    return new AssetApiClient({
      endpoint: entry.config.assetApiUrl,
      getAccessToken: () => this.accessToken(entry.config),
      fetch: globalThis.fetch,
    })
  }

  async authStatus(config: CloudPublicConfig): Promise<CloudAuthStatus> {
    const { client, storage } = this.clientEntry(config)
    const { data, error } = await client.auth.getSession()
    if (error) throw new Error(`读取登录状态失败：${error.message}`)
    const user = data.session?.user
    return {
      user: user ? { id: user.id, email: user.email ?? '' } : null,
      sessionPersisted: storage.persistent,
    }
  }

  async signIn(config: CloudPublicConfig, email: string, password: string): Promise<CloudAuthStatus> {
    const normalizedEmail = email.trim()
    if (!/^\S+@\S+\.\S+$/.test(normalizedEmail)) throw new Error('请输入有效邮箱')
    if (!password) throw new Error('请输入密码')
    const { client } = this.clientEntry(config)
    const { error } = await client.auth.signInWithPassword({ email: normalizedEmail, password })
    if (error) throw new Error(`登录失败：${error.message}`)
    return this.authStatus(config)
  }

  async signOut(config: CloudPublicConfig): Promise<void> {
    const { client } = this.clientEntry(config)
    const { error } = await client.auth.signOut({ scope: 'local' })
    if (error) throw new Error(`退出登录失败：${error.message}`)
  }

  async listProjects(config: CloudPublicConfig): Promise<CloudProjectInfo[]> {
    const response = await this.api(config).listProjects()
    return response.projects.map(toProject)
  }

  async getBinding(root: string): Promise<CloudProjectBinding | null> {
    const safeRoot = await validateRoot(root)
    try {
      const parsed: unknown = JSON.parse(await fs.readFile(bindingPath(safeRoot), 'utf8'))
      return isBinding(parsed) ? parsed : null
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') return null
      throw new Error('作品的云端绑定文件损坏或无法读取')
    }
  }

  private async writeBinding(root: string, project: CloudProjectInfo): Promise<CloudProjectBinding> {
    const binding: CloudProjectBinding = {
      schemaVersion: 1,
      projectId: project.id,
      clientKey: project.clientKey,
      projectName: project.name,
      boundAt: new Date().toISOString(),
    }
    const dir = path.join(root, INTERNAL_DIR)
    await fs.mkdir(dir, { recursive: true, mode: 0o700 })
    const target = bindingPath(root)
    const temp = `${target}.${process.pid}.${randomUUID()}.tmp`
    await fs.writeFile(temp, JSON.stringify(binding, null, 2) + '\n', { mode: 0o600 })
    await fs.rename(temp, target)
    return binding
  }

  async bindProject(
    config: CloudPublicConfig,
    root: string,
    projectId: string,
  ): Promise<CloudProjectBinding> {
    if (!UUID_PATTERN.test(projectId)) throw new Error('云端作品 ID 无效')
    const safeRoot = await validateRoot(root)
    const project = (await this.listProjects(config)).find((item) => item.id === projectId)
    if (!project) throw new Error('找不到该云端作品或当前账号无权访问')
    return this.writeBinding(safeRoot, project)
  }

  async unbindProject(root: string): Promise<void> {
    const safeRoot = await validateRoot(root)
    await fs.rm(bindingPath(safeRoot), { force: true })
  }

  cancelSync(operationId: string): void {
    this.activeSyncs.get(operationId)?.abort()
  }

  private emit(progress: CloudSyncProgress): void {
    if (this.webContents && !this.webContents.isDestroyed()) {
      this.webContents.send('cloud-sync-progress', progress)
    }
  }

  private begin(operationId: string): AbortController {
    assertOperationId(operationId)
    if (this.activeSyncs.has(operationId)) throw new Error('该同步任务已在运行')
    const controller = new AbortController()
    this.activeSyncs.set(operationId, controller)
    return controller
  }

  private finish(operationId: string): void {
    this.activeSyncs.delete(operationId)
  }

  private async resolveUploadProject(
    config: CloudPublicConfig,
    root: string,
    projectName: string,
  ): Promise<CloudProjectInfo> {
    const binding = await this.getBinding(root)
    if (binding) {
      const project = (await this.listProjects(config)).find((item) => item.id === binding.projectId)
      if (!project) throw new Error('本地绑定的云端作品不存在或当前账号已失去访问权限')
      return project
    }
    const response = await this.api(config).ensureProject(randomUUID(), projectName)
    const project = toProject(response.project)
    await this.writeBinding(root, project)
    return project
  }

  private async hashCandidates(
    candidates: FileCandidate[],
    operationId: string,
    direction: CloudSyncDirection,
    signal: AbortSignal,
  ): Promise<LocalFile[]> {
    const totalBytes = candidates.reduce((sum, file) => sum + file.size, 0)
    const files: LocalFile[] = []
    for (let index = 0; index < candidates.length; index += 1) {
      const candidate = candidates[index]!
      this.emit({
        operationId,
        direction,
        phase: 'hashing',
        relativePath: candidate.relativePath,
        completedFiles: index,
        totalFiles: candidates.length,
        transferredBytes: 0,
        totalBytes,
      })
      files.push({ ...candidate, sha256: await sha256File(candidate.absolutePath, signal) })
    }
    return files
  }

  async syncUpload(
    config: CloudPublicConfig,
    root: string,
    projectName: string,
    operationId: string,
  ): Promise<CloudSyncResult> {
    const startedAt = Date.now()
    const controller = this.begin(operationId)
    const { signal } = controller
    try {
      const safeRoot = await validateRoot(root)
      const project = await this.resolveUploadProject(config, safeRoot, projectName.trim() || path.basename(safeRoot))
      this.emit({
        operationId,
        direction: 'upload',
        phase: 'scanning',
        completedFiles: 0,
        totalFiles: 0,
        transferredBytes: 0,
        totalBytes: 0,
      })
      const candidates = await collectCandidates(safeRoot, signal)
      const localFiles = await this.hashCandidates(candidates, operationId, 'upload', signal)
      const remoteAssets = (await this.api(config).listAssets(project.id, signal)).assets
      const remoteByPath = new Map(remoteAssets.map((asset) => [asset.relativePath, asset]))
      const changed = localFiles.filter((file) => {
        const remote = remoteByPath.get(file.relativePath)
        return !remote || remote.sha256 !== file.sha256 || remote.sizeBytes !== file.size
      })
      const totalBytes = changed.reduce((sum, file) => sum + file.size, 0)
      let transferredBytes = 0
      let uploadedFiles = 0
      const api = this.api(config)
      for (let index = 0; index < changed.length; index += 1) {
        throwIfAborted(signal)
        const file = changed[index]!
        const blob = await openAsBlob(file.absolutePath, { type: file.contentType })
        const beforeFile = transferredBytes
        await api.uploadAsset({
          projectId: project.id,
          relativePath: file.relativePath,
          source: {
            name: file.name,
            type: file.contentType,
            size: file.size,
            slice: blob.slice.bind(blob),
          },
          sha256: file.sha256,
          signal,
          onProgress: (uploaded) => {
            this.emit({
              operationId,
              direction: 'upload',
              phase: 'uploading',
              relativePath: file.relativePath,
              completedFiles: index,
              totalFiles: changed.length,
              transferredBytes: beforeFile + uploaded,
              totalBytes,
            })
          },
        })
        transferredBytes += file.size
        uploadedFiles += 1
      }
      this.emit({
        operationId,
        direction: 'upload',
        phase: 'finalizing',
        completedFiles: changed.length,
        totalFiles: changed.length,
        transferredBytes,
        totalBytes,
      })
      return {
        project,
        direction: 'upload',
        scannedFiles: localFiles.length,
        uploadedFiles,
        downloadedFiles: 0,
        skippedFiles: localFiles.length - changed.length,
        conflictFiles: [],
        transferredBytes,
        durationMs: Date.now() - startedAt,
      }
    } finally {
      this.finish(operationId)
    }
  }

  private async downloadAsset(
    config: CloudPublicConfig,
    asset: AssetRecord,
    target: string,
    signal: AbortSignal,
    onBytes: (bytes: number) => void,
  ): Promise<void> {
    const signed = await this.api(config).createDownloadUrl(asset.id, 'attachment', signal)
    const response = await fetch(signed.download.url, {
      method: signed.download.method,
      headers: signed.download.headers,
      signal,
    })
    if (!response.ok || !response.body) throw new Error(`下载 ${asset.relativePath} 失败：HTTP ${response.status}`)
    await fs.mkdir(path.dirname(target), { recursive: true })
    const temp = `${target}.${process.pid}.${randomUUID()}.part`
    const handle = await fs.open(temp, 'wx', 0o600)
    const reader = response.body.getReader()
    const hash = createHash('sha256')
    let received = 0
    try {
      while (true) {
        throwIfAborted(signal)
        const { done, value } = await reader.read()
        if (done) break
        await handle.write(value)
        hash.update(value)
        received += value.byteLength
        onBytes(received)
      }
      await handle.close()
      if (received !== asset.sizeBytes) throw new Error(`下载大小不匹配：${asset.relativePath}`)
      if (asset.sha256 && hash.digest('hex') !== asset.sha256) {
        throw new Error(`下载校验失败：${asset.relativePath}`)
      }
      await fs.rename(temp, target)
    } catch (error) {
      await handle.close().catch(() => undefined)
      await fs.rm(temp, { force: true }).catch(() => undefined)
      throw error
    }
  }

  async syncDownload(
    config: CloudPublicConfig,
    root: string,
    projectId: string,
    operationId: string,
  ): Promise<CloudSyncResult> {
    const startedAt = Date.now()
    const controller = this.begin(operationId)
    const { signal } = controller
    try {
      const safeRoot = await validateRoot(root)
      const project = (await this.listProjects(config)).find((item) => item.id === projectId)
      if (!project) throw new Error('找不到该云端作品或当前账号无权访问')
      const assets = (await this.api(config).listAssets(project.id, signal)).assets
      const totalBytes = assets.reduce((sum, asset) => sum + asset.sizeBytes, 0)
      let transferredBytes = 0
      let downloadedFiles = 0
      let skippedFiles = 0
      const conflictFiles: string[] = []
      for (let index = 0; index < assets.length; index += 1) {
        throwIfAborted(signal)
        const asset = assets[index]!
        const target = path.resolve(safeRoot, ...asset.relativePath.split('/'))
        const relativeCheck = path.relative(safeRoot, target)
        if (relativeCheck.startsWith('..') || path.isAbsolute(relativeCheck)) {
          throw new Error(`云端文件路径越界：${asset.relativePath}`)
        }
        let existing = false
        try {
          const stat = await fs.stat(target)
          existing = stat.isFile()
        } catch (error) {
          if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error
        }
        if (existing) {
          const digest = await sha256File(target, signal)
          if (asset.sha256 && digest === asset.sha256) skippedFiles += 1
          else conflictFiles.push(asset.relativePath)
          continue
        }
        const beforeFile = transferredBytes
        await this.downloadAsset(config, asset, target, signal, (received) => {
          this.emit({
            operationId,
            direction: 'download',
            phase: 'downloading',
            relativePath: asset.relativePath,
            completedFiles: index,
            totalFiles: assets.length,
            transferredBytes: beforeFile + received,
            totalBytes,
          })
        })
        transferredBytes += asset.sizeBytes
        downloadedFiles += 1
      }
      await this.writeBinding(safeRoot, project)
      this.emit({
        operationId,
        direction: 'download',
        phase: 'finalizing',
        completedFiles: assets.length,
        totalFiles: assets.length,
        transferredBytes,
        totalBytes,
      })
      return {
        project,
        direction: 'download',
        scannedFiles: assets.length,
        uploadedFiles: 0,
        downloadedFiles,
        skippedFiles,
        conflictFiles,
        transferredBytes,
        durationMs: Date.now() - startedAt,
      }
    } finally {
      this.finish(operationId)
    }
  }
}
