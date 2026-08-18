import assert from 'node:assert/strict'
import test from 'node:test'

import { SupabaseAuthService } from '../src/auth.ts'

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
  assert.equal(service.configured, false)
})
