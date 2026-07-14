import { execFile } from 'node:child_process'
import path from 'node:path'

const NEXT_ACTION_TIMEOUT = 30_000

/**
 * Bridge to `skills/n2d/run.py next --json --preview`. Returns raw stdout;
 * the renderer parses it (same contract as the Tauri command).
 */
export function readNextAction(repoRoot: string, root: string, ep: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const script = path.join(repoRoot, 'skills', 'n2d', 'run.py')
    const child = execFile(
      'python3',
      [script, 'next', root, ep, '--json', '--preview'],
      { cwd: repoRoot, timeout: NEXT_ACTION_TIMEOUT, maxBuffer: 8 * 1024 * 1024 },
      (err, stdout, stderr) => {
        if (stdout && stdout.trim()) resolve(stdout)
        else if (err) reject(new Error(stderr.trim() || String(err.message)))
        else resolve(stdout)
      },
    )
    child.stdin?.end()
  })
}
