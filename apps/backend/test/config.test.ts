import assert from 'node:assert/strict'
import { mkdtemp, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'

import {
  firstApiKeyFromConfig,
  normalizeCliProxyBaseUrl,
  resolveCliProxyConfiguration,
} from '../src/config.ts'
import { ApiError } from '../src/errors.ts'

test('normalizes loopback and HTTPS cliproxy URLs', () => {
  assert.equal(normalizeCliProxyBaseUrl('http://127.0.0.1:8317/v1/'), 'http://127.0.0.1:8317')
  assert.equal(normalizeCliProxyBaseUrl('https://models.example.test/api'), 'https://models.example.test/api')
  assert.throws(
    () => normalizeCliProxyBaseUrl('http://models.example.test'),
    (error: unknown) => error instanceof ApiError && error.code === 'cliproxy_invalid_config',
  )
})

test('reads only the first valid api key from development config', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'anime-armory-config-'))
  const configPath = path.join(directory, 'cliproxyapi.conf')
  const contents = "port: 8317\napi-keys:\n  - 'test-key-12345'\n  - never-used\n"
  await writeFile(configPath, contents)
  assert.equal(firstApiKeyFromConfig(contents), 'test-key-12345')
  const resolved = await resolveCliProxyConfiguration({}, configPath)
  assert.deepEqual(resolved, { baseUrl: 'http://127.0.0.1:8317', apiKey: 'test-key-12345' })
})

test('rejects browser-visible model secrets', async () => {
  await assert.rejects(
    resolveCliProxyConfiguration({ VITE_CLI_PROXY_API_KEY: 'should-never-exist' }),
    (error: unknown) => error instanceof ApiError && error.code === 'cliproxy_invalid_config',
  )
})
