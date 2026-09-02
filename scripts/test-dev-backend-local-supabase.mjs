import assert from 'node:assert/strict'
import test from 'node:test'

import { parseSupabaseEnv } from './dev-backend-local-supabase.mjs'

test('accepts the Supabase CLI IPv4 loopback output', () => {
  assert.deepEqual(
    parseSupabaseEnv([
      'API_URL="http://127.0.0.1:54321"',
      'ANON_KEY="local-anon-key"',
    ].join('\n')),
    {
      url: 'http://127.0.0.1:54321',
      publishableKey: 'local-anon-key',
    },
  )
})

test('accepts localhost with a publishable key', () => {
  assert.deepEqual(
    parseSupabaseEnv([
      'API_URL="http://localhost:54321/"',
      'PUBLISHABLE_KEY="local-publishable-key"',
    ].join('\n')),
    {
      url: 'http://localhost:54321',
      publishableKey: 'local-publishable-key',
    },
  )
})

test('accepts the bracketed IPv6 loopback hostname returned by Node URL', () => {
  assert.equal(new URL('http://[::1]:54321').hostname, '[::1]')
  assert.deepEqual(
    parseSupabaseEnv([
      'API_URL="http://[::1]:54321"',
      'ANON_KEY="local-ipv6-key"',
    ].join('\n')),
    {
      url: 'http://[::1]:54321',
      publishableKey: 'local-ipv6-key',
    },
  )
})

test('rejects hosted and private-LAN Supabase URLs', () => {
  for (const url of [
    'https://example.supabase.co',
    'http://192.168.1.10:54321',
    'http://localhost.example.com:54321',
  ]) {
    assert.throws(
      () => parseSupabaseEnv(`API_URL="${url}"\nANON_KEY="not-used"`),
      /拒绝把非本机 Supabase URL/u,
    )
  }
})

test('requires both a local API URL and an anonymous or publishable key', () => {
  assert.throws(
    () => parseSupabaseEnv('API_URL="http://127.0.0.1:54321"'),
    /没有返回 API_URL 与 ANON_KEY\/PUBLISHABLE_KEY/u,
  )
})
