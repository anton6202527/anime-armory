import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import { mkdir, mkdtemp, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'

import { closeTestServer, FakeProvider, listenTestServer, testConfig } from './helpers.ts'

async function roots(): Promise<{ skills: string; runtime: string }> {
  const root = await mkdtemp(path.join(os.tmpdir(), 'anime-armory-routes-'))
  const skills = path.join(root, 'skills')
  const runtime = path.join(root, 'runtime')
  await mkdir(path.join(skills, 'n2d-fixture'), { recursive: true })
  await writeFile(
    path.join(skills, 'n2d-fixture', 'SKILL.md'),
    '---\nname: n2d-fixture\ndescription: fixture\n---\n# Fixture\nFollow this skill.\n',
  )
  return { skills, runtime }
}

test('serves health, model, generation and skill registry envelopes', async (context) => {
  const { skills, runtime } = await roots()
  const provider = new FakeProvider()
  const { server, baseUrl } = await listenTestServer(testConfig(skills, runtime), provider)
  context.after(() => closeTestServer(server))

  const readyResponse = await fetch(`${baseUrl}/api/v1/health/ready`)
  assert.equal(readyResponse.status, 200)
  const ready = await readyResponse.json() as Record<string, unknown>
  assert.equal(ready.service, 'anime-armory-backend')
  assert.equal(ready.status, 'ready')

  const authSession = await (await fetch(`${baseUrl}/api/v1/auth/session`)).json() as {
    configured: boolean
    session: unknown
  }
  assert.deepEqual(authSession, { configured: false, session: null })

  const models = await (await fetch(`${baseUrl}/api/v1/ai/models`)).json() as { models: unknown[] }
  assert.equal(models.models.length, 2)

  const generationResponse = await fetch(`${baseUrl}/api/v1/ai/generations`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', origin: 'http://127.0.0.1:4174' },
    body: JSON.stringify({ modality: 'text', model: 'gpt-5.6-terra', prompt: 'hello' }),
  })
  assert.equal(generationResponse.status, 200)
  assert.equal(generationResponse.headers.get('access-control-allow-origin'), 'http://127.0.0.1:4174')
  const generation = await generationResponse.json() as { generation: { text: string } }
  assert.equal(generation.generation.text, 'fake backend result')

  const skillsResponse = await fetch(`${baseUrl}/api/v1/skills`)
  const catalog = await skillsResponse.json() as { skills: Array<{ id: string }> }
  assert.deepEqual(catalog.skills.map((skill) => skill.id), ['n2d-fixture'])
})

test('uses standard errors, explicit CORS, and UUID-only file storage', async (context) => {
  const { skills, runtime } = await roots()
  const { server, baseUrl } = await listenTestServer(testConfig(skills, runtime), new FakeProvider())
  context.after(() => closeTestServer(server))

  const forbidden = await fetch(`${baseUrl}/api/v1/skills`, { headers: { origin: 'https://evil.example' } })
  assert.equal(forbidden.status, 403)
  const forbiddenBody = await forbidden.json() as { error: { code: string; requestId: string } }
  assert.equal(forbiddenBody.error.code, 'origin_forbidden')
  assert.match(forbiddenBody.error.requestId, /^[0-9a-f-]{36}$/)

  const invalid = await fetch(`${baseUrl}/api/v1/works/not-a-uuid/files/not-a-uuid`, {
    method: 'PUT',
    body: 'data',
  })
  assert.equal(invalid.status, 400)

  const workId = randomUUID()
  const fileId = randomUUID()
  const upload = await fetch(`${baseUrl}/api/v1/works/${workId}/files/${fileId}`, {
    method: 'PUT',
    headers: { 'content-type': 'text/plain' },
    body: 'safe bytes',
  })
  assert.equal(upload.status, 200)
  const body = await upload.json() as { file: { workId: string; fileId: string; size: number; sha256: string } }
  assert.deepEqual({ workId: body.file.workId, fileId: body.file.fileId, size: body.file.size }, { workId, fileId, size: 10 })
  assert.match(body.file.sha256, /^[0-9a-f]{64}$/)
  assert.equal(JSON.stringify(body).includes(runtime), false)
})
