import { spawn } from 'node:child_process'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const workspaceRoot = fileURLToPath(new URL('..', import.meta.url))
const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm'

export function parseSupabaseEnv(output) {
  const values = new Map()

  for (const line of output.split(/\r?\n/u)) {
    const match = line.match(/^([A-Z][A-Z0-9_]*)=(.*)$/u)
    if (!match) continue

    const [, name, encodedValue] = match
    values.set(name, decodeEnvValue(encodedValue.trim()))
  }

  const url = values.get('API_URL') ?? values.get('SUPABASE_URL') ?? ''
  const publishableKey = values.get('PUBLISHABLE_KEY')
    ?? values.get('ANON_KEY')
    ?? values.get('SUPABASE_PUBLISHABLE_KEY')
    ?? values.get('SUPABASE_ANON_KEY')
    ?? ''

  if (!url || !publishableKey) {
    throw new Error('`supabase status -o env` 没有返回 API_URL 与 ANON_KEY/PUBLISHABLE_KEY。请确认本地 Supabase 已完整启动。')
  }

  let parsedUrl
  try {
    parsedUrl = new URL(url)
  } catch {
    throw new Error('Supabase CLI 返回了无效的 API_URL。')
  }

  if (!isLoopbackHostname(parsedUrl.hostname) || !['http:', 'https:'].includes(parsedUrl.protocol)) {
    throw new Error(`拒绝把非本机 Supabase URL 注入本地后端：${parsedUrl.origin}`)
  }

  return {
    url: parsedUrl.toString().replace(/\/+$/u, ''),
    publishableKey,
  }
}

function isLoopbackHostname(hostname) {
  const normalized = hostname.startsWith('[') && hostname.endsWith(']')
    ? hostname.slice(1, -1)
    : hostname

  return normalized === '127.0.0.1' || normalized === '::1' || normalized === 'localhost'
}

function decodeEnvValue(value) {
  if (value.startsWith('"') && value.endsWith('"')) {
    try {
      return JSON.parse(value)
    } catch {
      throw new Error('Supabase CLI 返回了无法解析的双引号环境变量。')
    }
  }

  if (value.startsWith("'") && value.endsWith("'")) {
    return value.slice(1, -1).replace(/'\\''/gu, "'")
  }

  return value
}

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: workspaceRoot,
      env: {
        ...process.env,
        DO_NOT_TRACK: '1',
        SUPABASE_TELEMETRY_DISABLED: '1',
        ...options.env,
      },
      stdio: options.capture ? ['ignore', 'pipe', 'pipe'] : 'inherit',
    })

    let stdout = ''
    let stderr = ''
    if (options.capture) {
      child.stdout.setEncoding('utf8')
      child.stderr.setEncoding('utf8')
      child.stdout.on('data', (chunk) => { stdout += chunk })
      child.stderr.on('data', (chunk) => { stderr += chunk })
    }

    child.once('error', reject)
    child.once('exit', (code, signal) => {
      resolve({ code, signal, stdout, stderr })
    })
  })
}

async function readLocalSupabaseEnvironment() {
  const status = await run(
    npmCommand,
    ['run', '--silent', 'supabase', '--', 'status', '-o', 'env'],
    { capture: true },
  )

  if (status.code !== 0) return null
  return parseSupabaseEnv(status.stdout)
}

async function ensureLocalSupabase() {
  const runningEnvironment = await readLocalSupabaseEnvironment()
  if (runningEnvironment) return runningEnvironment

  console.error('[LabuTV] 本地 Supabase 尚未就绪，正在启动 Docker 服务栈。首次运行需要下载镜像，可能耗时较长。')
  const start = await run(npmCommand, ['run', 'supabase', '--', 'start'])
  if (start.code !== 0) {
    throw new Error([
      '本地 Supabase 启动失败。',
      '请确认：',
      '  1. Docker Desktop 已启动并完成初始化；',
      '  2. Docker 可以访问镜像仓库（首次运行会下载镜像）；',
      '  3. 端口 54320-54323 未被其他程序占用。',
      '修复后重新运行 `npm run dev:backend:local`；也可用 `npm run supabase -- start` 查看完整启动日志。',
    ].join('\n'))
  }

  const startedEnvironment = await readLocalSupabaseEnvironment()
  if (!startedEnvironment) {
    throw new Error('Supabase CLI 已结束启动，但 `supabase status -o env` 仍不可用。请运行 `npm run supabase -- status` 检查本地服务。')
  }
  return startedEnvironment
}

async function main() {
  let localSupabase
  try {
    localSupabase = await ensureLocalSupabase()
  } catch (error) {
    console.error(`\n[LabuTV] ${error instanceof Error ? error.message : String(error)}`)
    process.exitCode = 1
    return
  }

  console.error(`[LabuTV] 本地 Supabase Auth 已就绪：${localSupabase.url}`)
  console.error('[LabuTV] 匿名密钥只注入本次后端进程，不会写入 .env、日志或 Git。')

  const backend = await run(
    npmCommand,
    ['run', 'dev:backend'],
    {
      env: {
        SUPABASE_URL: localSupabase.url,
        SUPABASE_PUBLISHABLE_KEY: localSupabase.publishableKey,
      },
    },
  )

  if (backend.signal) {
    console.error(`[LabuTV] 后端因信号 ${backend.signal} 退出；本地 Supabase 会继续运行。`)
  }
  process.exitCode = backend.code ?? (backend.signal ? 1 : 0)
}

const invokedPath = process.argv[1] ? resolve(process.argv[1]) : ''
if (invokedPath === fileURLToPath(import.meta.url)) {
  await main()
}
