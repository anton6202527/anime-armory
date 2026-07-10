import { execFile } from 'node:child_process'
import type { AgentInfo } from '@shared/types'

const PROBE_TIMEOUT = 8000

interface AgentDef {
  id: string
  name: string
  command: string
  binaries: string[]
  image: AgentInfo['image']
}

const AGENT_DEFS: AgentDef[] = [
  { id: 'claude', name: 'Claude Code', command: 'claude', binaries: ['claude'], image: 'maybe' },
  { id: 'codex', name: 'Codex CLI', command: 'codex', binaries: ['codex'], image: 'maybe' },
  { id: 'opencode', name: 'OpenCode', command: 'opencode', binaries: ['opencode'], image: 'no' },
  { id: 'gemini', name: 'Gemini CLI', command: 'gemini', binaries: ['gemini'], image: 'maybe' },
  { id: 'kimi', name: 'Kimi CLI', command: 'kimi', binaries: ['kimi', 'kimi-cli'], image: 'no' },
]

function runLoginShell(cmd: string, timeout: number): Promise<string> {
  return new Promise((resolve) => {
    const shell = process.env.SHELL || '/bin/zsh'
    const child = execFile(shell, ['-lc', cmd], { timeout }, (_err, stdout) => {
      resolve(stdout ?? '')
    })
    child.stdin?.end()
  })
}

/**
 * Detect installed AI CLIs by probing the user's *login* shell once
 * (so PATH matches what the in-app terminal will see).
 */
export async function detectAgents(): Promise<AgentInfo[]> {
  const binaries = AGENT_DEFS.flatMap((d) => d.binaries)
  const stdout = await runLoginShell(
    binaries.map((b) => `command -v ${b} || true`).join('; '),
    PROBE_TIMEOUT,
  )
  const found = new Map<string, string>()
  for (const line of stdout.split('\n')) {
    const p = line.trim()
    if (!p || !p.startsWith('/')) continue
    const bin = p.split('/').pop() ?? ''
    if (!found.has(bin)) found.set(bin, p)
  }
  const results: AgentInfo[] = []
  for (const def of AGENT_DEFS) {
    const hit = def.binaries.map((b) => found.get(b)).find(Boolean)
    let image = def.image
    if (def.id === 'codex' && hit) {
      const probe = await runLoginShell('codex features list 2>/dev/null || codex plugin list 2>/dev/null || true', PROBE_TIMEOUT)
      if (/image|图/i.test(probe)) image = 'yes'
    }
    results.push({
      id: def.id,
      name: def.name,
      command: def.command,
      found: Boolean(hit),
      path: hit ?? '',
      image: hit ? image : 'no',
      note: hit ? '' : '未检测到,可在终端安装后重试',
    })
  }
  return results
}
