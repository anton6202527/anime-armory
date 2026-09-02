import assert from 'node:assert/strict'
import test from 'node:test'

import { SupabaseAuthService } from '../src/auth.ts'
import { ApiError } from '../src/errors.ts'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

test('signs in through Supabase without exposing tokens in the session payload', async () => {
  const requests: string[] = []
  const service = new SupabaseAuthService(
    { supabaseUrl: 'https://project.supabase.co', publishableKey: 'sb_publishable_test_key_1234567890' },
    async (input) => {
      requests.push(String(input))
      return json({
        access_token: 'access-secret',
        refresh_token: 'refresh-secret',
        expires_in: 3600,
        user: { id: 'user-1', email: 'author@example.com' },
      })
    },
  )

  const result = await service.access({ email: 'AUTHOR@example.com', password: 'secret1' }, AbortSignal.timeout(1_000))
  assert.equal(result.action, 'signed-in')
  assert.deepEqual(result.session, { user: { id: 'user-1', email: 'author@example.com' } })
  assert.equal(JSON.stringify(result.session).includes('access-secret'), false)
  assert.equal(result.cookies?.length, 2)
  assert.match(result.cookies?.[0] ?? '', /HttpOnly; SameSite=Lax/)
  assert.match(requests[0] ?? '', /grant_type=password/)
})

test('reports an unconfigured session without contacting Supabase', async () => {
  const service = new SupabaseAuthService(undefined, async () => {
    throw new Error('must not run')
  })
  assert.deepEqual(await service.session(undefined, AbortSignal.timeout(1_000)), { session: null })
  assert.deepEqual(await service.availability(AbortSignal.timeout(1_000)), {
    available: false,
    status: 'unconfigured',
    code: 'auth_not_configured',
    message: '登录服务尚未配置',
  })
  assert.equal(service.configured, false)
})

test('probes the Supabase Auth health endpoint without exposing the publishable key', async () => {
  const requests: Array<{ url: string; key: string | null }> = []
  const service = new SupabaseAuthService(
    { supabaseUrl: 'https://project.supabase.co', publishableKey: 'sb_publishable_test_key_1234567890' },
    async (input, init) => {
      const headers = new Headers(init?.headers)
      requests.push({ url: String(input), key: headers.get('apikey') })
      return json({ version: 'test' })
    },
  )

  assert.deepEqual(await service.availability(AbortSignal.timeout(1_000)), {
    available: true,
    status: 'available',
  })
  assert.deepEqual(requests, [{
    url: 'https://project.supabase.co/auth/v1/health',
    key: 'sb_publishable_test_key_1234567890',
  }])
  assert.equal(JSON.stringify(await service.availability(AbortSignal.timeout(1_000))).includes('sb_publishable'), false)
})

test('reports fetch rejection as an unavailable upstream and preserves an actionable operation error', async () => {
  const service = new SupabaseAuthService(
    { supabaseUrl: 'https://missing.supabase.co', publishableKey: 'sb_publishable_test_key_1234567890' },
    async () => { throw new TypeError('getaddrinfo ENOTFOUND missing.supabase.co') },
  )

  const availability = await service.availability(AbortSignal.timeout(1_000))
  assert.equal(availability.available, false)
  assert.equal(availability.status, 'unavailable')
  assert.equal(availability.code, 'auth_upstream_unavailable')
  assert.equal(JSON.stringify(availability).includes('missing.supabase.co'), false)
  await assert.rejects(
    service.access({ email: 'author@example.com', password: 'secret1' }, AbortSignal.timeout(1_000)),
    (error: unknown) => error instanceof ApiError
      && error.status === 502
      && error.code === 'auth_upstream_unavailable',
  )
})

test('distinguishes an internal upstream timeout from caller cancellation', async () => {
  const waitForAbort: typeof fetch = async (_input, init) => new Promise<Response>((_resolve, reject) => {
    const signal = init?.signal
    if (!signal) return
    if (signal.aborted) {
      reject(signal.reason)
      return
    }
    signal.addEventListener('abort', () => reject(signal.reason), { once: true })
  })
  const service = new SupabaseAuthService(
    { supabaseUrl: 'https://slow.supabase.co', publishableKey: 'sb_publishable_test_key_1234567890' },
    waitForAbort,
    { healthTimeoutMs: 10, requestTimeoutMs: 10 },
  )

  const availability = await service.availability(new AbortController().signal)
  assert.equal(availability.status, 'timeout')
  assert.equal(availability.code, 'auth_upstream_timeout')

  await assert.rejects(
    service.access({ email: 'author@example.com', password: 'secret1' }, new AbortController().signal),
    (error: unknown) => error instanceof ApiError
      && error.status === 504
      && error.code === 'auth_upstream_timeout',
  )

  const controller = new AbortController()
  controller.abort()
  await assert.rejects(
    service.access({ email: 'author@example.com', password: 'secret1' }, controller.signal),
    (error: unknown) => error instanceof ApiError
      && error.status === 499
      && error.code === 'request_cancelled',
  )
})
