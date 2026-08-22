import type { CanvasFrame, LineKey } from './types'

export function stableCanvasSlotToken(value: string): string {
  return value.normalize('NFKC').replace(/[^\p{L}\p{N}._-]+/gu, '-').replace(/^-+|-+$/g, '').slice(0, 80) || '1'
}

export function canvasFrameTargetSlot(frame: CanvasFrame, stableIndex: number): string {
  const role = `${frame.role || ''} ${frame.label || ''}`
  if (/panel|成图/i.test(role)) return 'panel'
  if (/^(first|首帧)/i.test(role)) return 'first'
  if (/^(end|last|尾帧)/i.test(role)) return 'end'
  if (Number.isFinite(frame.at_sec)) {
    return `anchor:${stableIndex + 1}:t${Math.round(Number(frame.at_sec) * 1000)}`
  }
  const basename = (frame.abs || '').replace(/\\/g, '/').split('/').at(-1)?.replace(/\.[^.]+$/, '') || ''
  return `anchor:${stableIndex + 1}:${stableCanvasSlotToken(basename || String(stableIndex + 1))}`
}

export function canvasImageTargetRel(episode: string, clipId: string, slot: string): string {
  return `出图/${episode}/${clipId}_${stableCanvasSlotToken(slot)}.png`
}

export function canvasVideoTargetRel(episode: string, clipId: string): string {
  return `出视频/${episode}/${clipId}.mp4`
}

function normalizedCanvasTargetRel(value: string): string {
  const normalized = value.trim().replace(/\\/g, '/').replace(/^\.\//, '')
  const parts = normalized.split('/').filter((part) => part && part !== '.')
  if (!normalized || normalized.startsWith('/') || /^[A-Za-z]:\//.test(normalized) ||
      parts.some((part) => part === '..')) {
    throw new Error('canvas target 必须是作品内相对路径')
  }
  return parts.join('/')
}

/**
 * Candidate media lives below the stable target's own parent directory. That
 * makes the eventual rename same-volume even when a work tree contains mounted
 * output directories. Only Electron main may promote this path to the target.
 */
export function canvasCandidateTargetRel(stableTargetPath: string, jobId: string): string {
  const target = normalizedCanvasTargetRel(stableTargetPath)
  const slash = target.lastIndexOf('/')
  const parent = slash >= 0 ? target.slice(0, slash) : ''
  const basename = slash >= 0 ? target.slice(slash + 1) : target
  const job = stableCanvasSlotToken(jobId)
  return `${parent ? `${parent}/` : ''}.canvas-candidates/${job}/${basename}`
}

/** One deterministic delivery target per visual line/episode. */
export function canvasFinalTargetRel(line: LineKey, episode: string): string | null {
  if (line === 'n2d') return `合成/${episode}/成片_最终.mp4`
  if (line === 'comic') return `排版/${episode}/长图/longstrip.png`
  if (line === 'ad') return '合成/成片_主片.mp4'
  if (line === 'mv') return '成片_MV.mp4'
  return null
}
