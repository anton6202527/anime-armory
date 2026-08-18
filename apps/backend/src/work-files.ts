import { createHash, randomUUID } from 'node:crypto'
import fsp from 'node:fs/promises'
import path from 'node:path'

import { ApiError } from './errors.ts'

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

function assertUuid(value: string, field: string): void {
  if (!UUID_PATTERN.test(value)) throw new ApiError(400, 'invalid_file_id', `${field} 必须是 UUID`)
}

async function ensureOwnedDirectory(directory: string): Promise<void> {
  await fsp.mkdir(directory, { recursive: true, mode: 0o700 })
  const stat = await fsp.lstat(directory)
  if (!stat.isDirectory() || stat.isSymbolicLink()) {
    throw new ApiError(500, 'runtime_storage_unsafe', 'runtime 存储目录不安全')
  }
}

export class WorkFileStore {
  constructor(readonly root: string) {}

  async put(
    workId: string,
    fileId: string,
    bytes: Buffer,
    mimeType: string | undefined,
  ): Promise<{ workId: string; fileId: string; size: number; sha256: string; mimeType?: string }> {
    assertUuid(workId, 'workId')
    assertUuid(fileId, 'fileId')
    await ensureOwnedDirectory(this.root)
    const workDirectory = path.join(this.root, 'works', workId)
    await ensureOwnedDirectory(workDirectory)
    const destination = path.join(workDirectory, fileId)
    const temporary = path.join(workDirectory, `.${fileId}.${randomUUID()}.tmp`)
    try {
      await fsp.writeFile(temporary, bytes, { flag: 'wx', mode: 0o600 })
      await fsp.rename(temporary, destination)
    } finally {
      await fsp.unlink(temporary).catch(() => undefined)
    }
    const normalizedMimeType = mimeType?.split(';', 1)[0]?.trim().toLowerCase()
    const safeMimeType = normalizedMimeType && /^[a-z0-9][a-z0-9.+-]{0,63}\/[a-z0-9][a-z0-9.+-]{0,127}$/.test(normalizedMimeType)
      ? normalizedMimeType
      : undefined
    return {
      workId,
      fileId,
      size: bytes.length,
      sha256: createHash('sha256').update(bytes).digest('hex'),
      ...(safeMimeType ? { mimeType: safeMimeType } : {}),
    }
  }

  async read(workId: string, fileId: string, maximumBytes: number): Promise<Buffer> {
    assertUuid(workId, 'workId')
    assertUuid(fileId, 'fileId')
    const candidate = path.join(this.root, 'works', workId, fileId)
    let stat
    try {
      stat = await fsp.lstat(candidate)
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        throw new ApiError(404, 'work_file_not_found', '工作文件不存在或尚未上传')
      }
      throw error
    }
    if (!stat.isFile() || stat.isSymbolicLink()) {
      throw new ApiError(404, 'work_file_not_found', '工作文件不存在或尚未上传')
    }
    if (!stat.size || stat.size > maximumBytes) {
      throw new ApiError(413, 'work_file_too_large', '工作文件为空或超过 Skill 输入上限')
    }
    return fsp.readFile(candidate)
  }
}
