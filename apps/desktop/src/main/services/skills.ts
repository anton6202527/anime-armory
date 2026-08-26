import fs from 'node:fs/promises'
import { Dirent } from 'node:fs'
import path from 'node:path'
import { decodeTextBuffer, looksBinary } from '../util/text'
import { isIgnoredName, resolveWithin } from '../util/paths'
import type { SkillInfo, SkillTreeEntry } from '@shared/types'

const SKILL_FILE_LIMIT = 512 * 1024
const TREE_DEPTH_LIMIT = 6

// These were the pre-migration names of independent canvas/Web App skills.
// Keep legacy ID resolution elsewhere for old projects, but never advertise
// these aliases as members of the n2d production line.
const LEGACY_APP_SKILL_DIRS = new Set([
  'n2d-audio-video',
  'n2d-character-turnaround',
  'n2d-first-frame-video',
  'n2d-script-workbench',
])

function parseFrontmatter(md: string): { name: string; description: string } {
  const m = /^---\r?\n([\s\S]*?)\r?\n---/.exec(md)
  let name = ''
  let description = ''
  if (m) {
    for (const line of m[1].split(/\r?\n/)) {
      const nameMatch = /^name:\s*(.+)$/.exec(line)
      const descMatch = /^description:\s*(.+)$/.exec(line)
      if (nameMatch) name = nameMatch[1].trim().replace(/^["']|["']$/g, '')
      if (descMatch) description = descMatch[1].trim().replace(/^["']|["']$/g, '')
    }
  }
  return { name, description }
}

/** Bare directory name only — no separators or traversal. */
function assertBareName(dir: string) {
  if (!dir || /[\\/]|\.\./.test(dir)) throw new Error('非法技能目录名')
}

export function isSeriesSkillDirectory(dir: string, line: string): boolean {
  return !LEGACY_APP_SKILL_DIRS.has(dir) && (dir === line || dir.startsWith(`${line}-`))
}

export class SkillsService {
  /** skills/<line> + skills/<line>-* — dispatcher first, then alphabetical. */
  async list(repoRoot: string, line: string): Promise<SkillInfo[]> {
    assertBareName(line)
    const skillsDir = path.join(repoRoot, 'skills')
    let entries: Dirent[]
    try {
      entries = await fs.readdir(skillsDir, { withFileTypes: true })
    } catch {
      return []
    }
    const names = entries
      .filter((e) => e.isDirectory() && isSeriesSkillDirectory(e.name, line))
      .map((e) => e.name)
      .sort((a, b) => (a === line ? -1 : b === line ? 1 : a.localeCompare(b)))
    const out: SkillInfo[] = []
    for (const dir of names) {
      let name = dir
      let description = ''
      try {
        const md = await fs.readFile(path.join(skillsDir, dir, 'SKILL.md'), 'utf8')
        const fm = parseFrontmatter(md)
        if (fm.name) name = fm.name
        description = fm.description
      } catch {
        // no SKILL.md — keep directory name
      }
      out.push({ name, description, dir })
    }
    return out
  }

  async tree(repoRoot: string, dir: string): Promise<SkillTreeEntry[]> {
    assertBareName(dir)
    const base = path.join(repoRoot, 'skills', dir)
    const out: SkillTreeEntry[] = []
    const walk = async (relDir: string, depth: number) => {
      if (depth > TREE_DEPTH_LIMIT) return
      const absDir = relDir ? path.join(base, relDir) : base
      let entries: Dirent[]
      try {
        entries = (await fs.readdir(absDir, { withFileTypes: true }))
          .filter((e) => !isIgnoredName(e.name))
          .sort((a, b) => {
            if (a.isDirectory() !== b.isDirectory()) return a.isDirectory() ? -1 : 1
            return a.name.localeCompare(b.name)
          })
      } catch {
        return
      }
      for (const ent of entries) {
        const rel = relDir ? `${relDir}/${ent.name}` : ent.name
        let size = 0
        let mtime = 0
        try {
          const st = await fs.stat(path.join(base, rel))
          size = st.size
          mtime = Math.floor(st.mtimeMs / 1000)
        } catch {
          continue
        }
        out.push({ name: ent.name, path: rel, depth, is_dir: ent.isDirectory(), size, mtime, status: '' })
        if (ent.isDirectory()) await walk(rel, depth + 1)
      }
    }
    await walk('', 0)
    return out
  }

  async readFile(repoRoot: string, dir: string, rel: string): Promise<string> {
    assertBareName(dir)
    const base = path.join(repoRoot, 'skills', dir)
    const abs = resolveWithin(base, rel)
    const st = await fs.stat(abs)
    if (st.size > SKILL_FILE_LIMIT) throw new Error('文件过大,无法预览(上限 512 KB)')
    const buf = await fs.readFile(abs)
    if (looksBinary(buf)) throw new Error('二进制文件,无法预览')
    return decodeTextBuffer(buf)
  }
}
