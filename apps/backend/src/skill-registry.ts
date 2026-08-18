import fsp from 'node:fs/promises'
import path from 'node:path'

import type { CreationLine } from './contracts.ts'
import { ApiError } from './errors.ts'

const SKILL_ID_PATTERN = /^[a-z0-9][a-z0-9-]{0,79}$/
const MAX_SKILL_DOCUMENT_BYTES = 512 * 1024
const MAX_SOURCE_BYTES = 512 * 1024
const MAX_SOURCE_FILES = 5_000
const MAX_SOURCE_DEPTH = 8
const CREATION_LINES = new Set<CreationLine>(['novel', 'n2d', 'comic', 'ad', 'mv', 'song'])
const TEXT_EXTENSIONS = new Set([
  '.css', '.csv', '.html', '.js', '.json', '.md', '.mjs', '.py', '.sh', '.srt', '.toml', '.ts', '.txt', '.yaml', '.yml',
])

export interface SkillSummary {
  id: string
  title: string
  description: string
  line?: CreationLine
  kind: 'line' | 'child' | 'independent'
}

export interface RegisteredSkill extends SkillSummary {
  definition: string
}

export interface SkillSourceSummary {
  path: string
  size: number
}

interface InternalSkill extends RegisteredSkill {
  directory: string
}

function scalar(value: string): string {
  const trimmed = value.trim()
  if (trimmed.length >= 2 && trimmed.startsWith('"') && trimmed.endsWith('"')) {
    try {
      const decoded = JSON.parse(trimmed) as unknown
      return typeof decoded === 'string' ? decoded : trimmed
    } catch {
      return trimmed.slice(1, -1)
    }
  }
  if (trimmed.length >= 2 && trimmed.startsWith("'") && trimmed.endsWith("'")) {
    return trimmed.slice(1, -1).replace(/''/g, "'")
  }
  return trimmed
}

function frontMatter(document: string): Record<string, string> {
  if (!document.startsWith('---\n') && !document.startsWith('---\r\n')) return {}
  const lines = document.split(/\r?\n/)
  const result: Record<string, string> = {}
  for (let index = 1; index < Math.min(lines.length, 200); index += 1) {
    const line = lines[index] ?? ''
    if (line.trim() === '---') break
    const match = line.match(/^([a-zA-Z][a-zA-Z0-9_-]{0,63}):\s*(.*?)\s*$/)
    if (match?.[1] && match[2] !== undefined) result[match[1]] = scalar(match[2])
  }
  return result
}

function inferredLine(id: string, firstSegment: string): CreationLine | undefined {
  if (CREATION_LINES.has(firstSegment as CreationLine)) return firstSegment as CreationLine
  for (const line of CREATION_LINES) {
    if (id === line || id.startsWith(`${line}-`)) return line
  }
  return undefined
}

function contained(root: string, candidate: string): boolean {
  const relative = path.relative(root, candidate)
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))
}

function safeSourcePath(value: string): string {
  if (!value || value.length > 512 || value.includes('\0') || path.isAbsolute(value)) {
    throw new ApiError(400, 'invalid_source_path', 'source path 无效')
  }
  const normalized = path.posix.normalize(value.replaceAll('\\', '/'))
  if (normalized === '.' || normalized === '..' || normalized.startsWith('../') || normalized.includes('/../')) {
    throw new ApiError(400, 'invalid_source_path', 'source path 必须位于 skill 目录内')
  }
  const extension = path.extname(normalized).toLowerCase()
  if (!TEXT_EXTENSIONS.has(extension)) throw new ApiError(415, 'unsupported_source_type', '只允许读取受支持的文本源文件')
  return normalized
}

async function readRegularText(file: string, maximumBytes: number): Promise<string> {
  let stat
  try {
    stat = await fsp.lstat(file)
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') throw new ApiError(404, 'source_not_found', '源文件不存在')
    throw error
  }
  if (!stat.isFile() || stat.isSymbolicLink()) throw new ApiError(404, 'source_not_found', '源文件不存在')
  if (stat.size > maximumBytes) throw new ApiError(413, 'source_too_large', '源文件超过读取上限')
  return fsp.readFile(file, 'utf8')
}

export class SkillRegistry {
  constructor(readonly root: string) {}

  private async discover(): Promise<Map<string, InternalSkill>> {
    const result = new Map<string, InternalSkill>()
    let topEntries
    try {
      topEntries = await fsp.readdir(this.root, { withFileTypes: true })
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        throw new ApiError(503, 'skill_registry_unavailable', 'skills 目录不存在')
      }
      throw error
    }
    const candidates: Array<{ directory: string; segments: string[] }> = []
    for (const entry of topEntries) {
      if (!entry.isDirectory() || entry.isSymbolicLink() || entry.name.startsWith('.')) continue
      const directory = path.join(this.root, entry.name)
      candidates.push({ directory, segments: [entry.name] })
      if (!CREATION_LINES.has(entry.name as CreationLine)) continue
      const children = await fsp.readdir(directory, { withFileTypes: true })
      for (const child of children) {
        if (child.isDirectory() && !child.isSymbolicLink() && !child.name.startsWith('.')) {
          candidates.push({ directory: path.join(directory, child.name), segments: [entry.name, child.name] })
        }
      }
    }
    for (const candidate of candidates) {
      const skillFile = path.join(candidate.directory, 'SKILL.md')
      let definition: string
      try {
        definition = await readRegularText(skillFile, MAX_SKILL_DOCUMENT_BYTES)
      } catch (error) {
        if (error instanceof ApiError && error.code === 'source_not_found') continue
        throw error
      }
      const metadata = frontMatter(definition)
      const fallbackId = candidate.segments.at(-1) ?? ''
      const id = metadata.name?.trim() || fallbackId
      if (!SKILL_ID_PATTERN.test(id)) continue
      if (result.has(id)) throw new ApiError(500, 'duplicate_skill_id', `skill ID 重复：${id}`)
      const firstSegment = candidate.segments[0] ?? ''
      const line = inferredLine(id, firstSegment)
      const title = metadata.title?.trim() || id
      const description = (metadata.description?.trim() || '').slice(0, 4_000)
      const kind = candidate.segments.length === 2
        ? 'child'
        : CREATION_LINES.has(firstSegment as CreationLine) ? 'line' : 'independent'
      result.set(id, {
        id,
        title,
        description,
        ...(line ? { line } : {}),
        kind,
        definition,
        directory: candidate.directory,
      })
    }
    return result
  }

  async list(): Promise<SkillSummary[]> {
    const skills = await this.discover()
    return [...skills.values()]
      .map(({ directory: _directory, definition: _definition, ...summary }) => summary)
      .sort((left, right) => left.id.localeCompare(right.id))
  }

  async get(id: string): Promise<RegisteredSkill> {
    if (!SKILL_ID_PATTERN.test(id)) throw new ApiError(400, 'invalid_skill_id', 'skill ID 无效')
    const skill = (await this.discover()).get(id)
    if (!skill) throw new ApiError(404, 'skill_not_found', `找不到 skill：${id}`)
    const { directory: _directory, ...publicSkill } = skill
    return publicSkill
  }

  private async internal(id: string): Promise<InternalSkill> {
    if (!SKILL_ID_PATTERN.test(id)) throw new ApiError(400, 'invalid_skill_id', 'skill ID 无效')
    const skill = (await this.discover()).get(id)
    if (!skill) throw new ApiError(404, 'skill_not_found', `找不到 skill：${id}`)
    return skill
  }

  async listSources(id: string): Promise<SkillSourceSummary[]> {
    const skill = await this.internal(id)
    const rootReal = await fsp.realpath(skill.directory)
    const results: SkillSourceSummary[] = []
    const visit = async (directory: string, depth: number): Promise<void> => {
      if (depth > MAX_SOURCE_DEPTH || results.length >= MAX_SOURCE_FILES) return
      const entries = await fsp.readdir(directory, { withFileTypes: true })
      for (const entry of entries) {
        if (results.length >= MAX_SOURCE_FILES || entry.name.startsWith('.') || entry.isSymbolicLink()) continue
        const absolute = path.join(directory, entry.name)
        if (entry.isDirectory()) {
          await visit(absolute, depth + 1)
          continue
        }
        if (!entry.isFile() || !TEXT_EXTENSIONS.has(path.extname(entry.name).toLowerCase())) continue
        const stat = await fsp.lstat(absolute)
        if (!stat.isFile() || stat.isSymbolicLink() || stat.size > MAX_SOURCE_BYTES) continue
        const real = await fsp.realpath(absolute)
        if (!contained(rootReal, real)) continue
        results.push({ path: path.relative(rootReal, real).split(path.sep).join('/'), size: stat.size })
      }
    }
    await visit(rootReal, 0)
    return results.sort((left, right) => left.path.localeCompare(right.path))
  }

  async readSource(id: string, sourcePath: string): Promise<{ path: string; content: string }> {
    const skill = await this.internal(id)
    const normalized = safeSourcePath(sourcePath)
    const rootReal = await fsp.realpath(skill.directory)
    const candidate = path.join(rootReal, ...normalized.split('/'))
    if (!contained(rootReal, candidate)) throw new ApiError(400, 'invalid_source_path', 'source path 必须位于 skill 目录内')
    const content = await readRegularText(candidate, MAX_SOURCE_BYTES)
    const real = await fsp.realpath(candidate)
    if (!contained(rootReal, real)) throw new ApiError(400, 'invalid_source_path', 'source path 必须位于 skill 目录内')
    return { path: normalized, content }
  }
}

export function isCreationLine(value: unknown): value is CreationLine {
  return typeof value === 'string' && CREATION_LINES.has(value as CreationLine)
}
