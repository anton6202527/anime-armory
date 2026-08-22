import type { DemoDownloadInfo, LineKey, WorkRoot } from './types'

/**
 * Product-owned demo choices.  A remote catalog may temporarily contain more
 * than one package for a line, but the app deliberately presents one demo.
 */
const PREFERRED_DEMO_NAME: Partial<Record<LineKey, string>> = {
  n2d: '那妖魔是姜大人',
}

export function selectLineDemo<T extends { name: string }>(line: LineKey, candidates: readonly T[]): T | null {
  if (candidates.length === 0) return null
  const preferred = PREFERRED_DEMO_NAME[line]
  return (preferred ? candidates.find((candidate) => candidate.name === preferred) : undefined)
    ?? candidates[0]
}

/** Keep at most one downloadable catalog entry per creative line. */
export function selectCatalogDemos(demos: readonly DemoDownloadInfo[]): DemoDownloadInfo[] {
  const selected: DemoDownloadInfo[] = []
  const lines = new Set(demos.map((demo) => demo.line_key))
  for (const line of lines) {
    const demo = selectLineDemo(line, demos.filter((candidate) => candidate.line_key === line))
    if (demo) selected.push(demo)
  }
  return selected
}

/**
 * Resolve installed and downloadable candidates together so a line never
 * renders two DEMO cards. Real works are always preserved.
 */
export function selectVisibleLineDemos(
  line: LineKey,
  roots: readonly WorkRoot[],
  downloads: readonly DemoDownloadInfo[],
): { roots: WorkRoot[]; downloads: DemoDownloadInfo[] } {
  const installed = roots.filter((root) => root.is_demo)
  const available = downloads.filter(
    (demo) => demo.line_key === line && !demo.installed,
  )
  const candidates = [
    ...installed.map((value) => ({ kind: 'installed' as const, name: value.name, value })),
    ...available.map((value) => ({ kind: 'download' as const, name: value.name, value })),
  ]
  const selected = selectLineDemo(line, candidates)

  return {
    roots: roots.filter((root) => !root.is_demo || (selected?.kind === 'installed' && selected.value === root)),
    downloads: selected?.kind === 'download' ? [selected.value] : [],
  }
}
