import { realpathSync } from 'node:fs'
import path from 'node:path'

/** Entries skipped by every tree walk / search / snapshot. */
export const IGNORED_NAMES = new Set([
  '__pycache__',
  '.DS_Store',
  'node_modules',
  '_voicecache',
  '.git',
])

export function isIgnoredName(name: string): boolean {
  return IGNORED_NAMES.has(name)
}

/**
 * Reject absolute paths and any `..`/empty component. Returns the normalized
 * relative path with `/` separators. Mirrors the Rust validate_rel_path.
 */
export function validateRelPath(rel: string): string {
  if (rel.startsWith('/') || /^[A-Za-z]:[\\/]/.test(rel) || rel.startsWith('\\')) {
    throw new Error('非法路径:不允许绝对路径')
  }
  const parts = rel.split(/[\\/]+/)
  const out: string[] = []
  for (const part of parts) {
    if (part === '' || part === '.') continue
    if (part === '..') throw new Error('非法路径:不允许越级访问')
    out.push(part)
  }
  return out.join('/')
}

/** realpath that tolerates non-existing leaves by canonicalizing the parent. */
export function canonicalizeForCreate(p: string): string {
  const parent = path.dirname(p)
  const real = realpathSync(parent)
  return path.join(real, path.basename(p))
}

/**
 * Resolve `rel` under `root` and guarantee containment (anti-traversal),
 * following symlinks on the existing part of the path.
 */
export function resolveWithin(root: string, rel: string): string {
  const cleanRel = validateRelPath(rel)
  const realRoot = realpathSync(root)
  const target = path.join(realRoot, cleanRel)
  let canonical: string
  try {
    canonical = realpathSync(target)
  } catch {
    canonical = canonicalizeForCreate(target)
  }
  if (canonical !== realRoot && !canonical.startsWith(realRoot + path.sep)) {
    throw new Error('非法路径:超出允许范围')
  }
  return canonical
}

export function isInside(parent: string, child: string): boolean {
  const p = path.resolve(parent)
  const c = path.resolve(child)
  return c === p || c.startsWith(p + path.sep)
}

export function pathsOverlap(a: string, b: string): boolean {
  return isInside(a, b) || isInside(b, a)
}
