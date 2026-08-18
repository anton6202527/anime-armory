import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import { mkdir, mkdtemp, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'

import { closeTestServer, FakeProvider, listenTestServer, testConfig } from './helpers.ts'

test('runs a registered standalone skill asynchronously through the injected provider', async (context) => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'anime-armory-jobs-'))
  const skills = path.join(root, 'skills')
  await mkdir(path.join(skills, 'n2d-character-turnaround'), { recursive: true })
  await writeFile(
    path.join(skills, 'n2d-character-turnaround', 'SKILL.md'),
    '---\nname: n2d-character-turnaround\ndescription: standalone\n---\n# Turnaround\nUse three views.\n',
  )
  const provider = new FakeProvider()
  const { server, baseUrl } = await listenTestServer(testConfig(skills, path.join(root, 'runtime')), provider)
  context.after(() => closeTestServer(server))

  const create = await fetch(`${baseUrl}/api/v1/skill-runs`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      skillId: 'n2d-character-turnaround',
      projectId: 'project-fixture',
      line: 'n2d',
      prompt: 'Create a turnaround.',
      generationMode: 'auto',
      idempotencyKey: 'fixture-key-0001',
    }),
  })
  assert.equal(create.status, 202)
  const created = await create.json() as { run: { id: string; state: string } }

  let run: { id: string; state: string; output?: string; model?: string; artifacts?: unknown[] } = created.run
  for (let attempt = 0; attempt < 20 && run.state !== 'succeeded'; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 5))
    const response = await fetch(`${baseUrl}/api/v1/skill-runs/${run.id}`)
    run = (await response.json() as { run: typeof run }).run
  }
  assert.equal(run.state, 'succeeded')
  assert.equal(run.model, 'gpt-5.6-terra')
  assert.equal(run.output, 'fake backend result')
  assert.equal(run.artifacts?.length, 1)
  assert.match(provider.requests[0]?.prompt ?? '', /Use three views/)
  assert.equal(JSON.stringify(run).includes(root), false)

  const duplicate = await fetch(`${baseUrl}/api/v1/skill-runs`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      skillId: 'n2d-character-turnaround',
      projectId: 'project-fixture',
      line: 'n2d',
      prompt: 'Create a turnaround.',
      generationMode: 'auto',
      idempotencyKey: 'fixture-key-0001',
    }),
  })
  assert.equal(duplicate.status, 202)
  assert.equal((await duplicate.json() as { run: { id: string } }).run.id, run.id)
})

test('requires a complete definition for user skills', async (context) => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'anime-armory-user-job-'))
  const skills = path.join(root, 'skills')
  await mkdir(skills)
  const { server, baseUrl } = await listenTestServer(testConfig(skills, path.join(root, 'runtime')), new FakeProvider())
  context.after(() => closeTestServer(server))
  const response = await fetch(`${baseUrl}/api/v1/skill-runs`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      skillId: 'user:fixture',
      workId: 'work-fixture',
      line: 'n2d',
      prompt: 'run it',
      generationMode: 'manual',
      idempotencyKey: 'fixture-key-0002',
    }),
  })
  assert.equal(response.status, 400)
  const body = await response.json() as { error: { code: string } }
  assert.equal(body.error.code, 'skill_definition_required')
})

test('loads an uploaded image into a standalone GPT vision request', async (context) => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'anime-armory-image-job-'))
  const skills = path.join(root, 'skills')
  await mkdir(path.join(skills, 'n2d-character-turnaround'), { recursive: true })
  await writeFile(
    path.join(skills, 'n2d-character-turnaround', 'SKILL.md'),
    '---\nname: n2d-character-turnaround\ndescription: standalone\n---\n# Turnaround\nInspect the real reference.\n',
  )
  const provider = new FakeProvider()
  const { server, baseUrl } = await listenTestServer(testConfig(skills, path.join(root, 'runtime')), provider)
  context.after(() => closeTestServer(server))
  const workId = randomUUID()
  const fileId = randomUUID()
  const imageBytes = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10, 1, 2, 3, 4])
  const upload = await fetch(`${baseUrl}/api/v1/works/${workId}/files/${fileId}`, {
    method: 'PUT',
    headers: { 'content-type': 'image/png' },
    body: imageBytes,
  })
  assert.equal(upload.status, 200)

  const create = await fetch(`${baseUrl}/api/v1/skill-runs`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      skillId: 'n2d-character-turnaround',
      workId,
      line: 'n2d',
      prompt: 'Inspect this image.',
      generationMode: 'manual',
      idempotencyKey: 'fixture-image-0001',
      attachments: [{ id: fileId, name: 'reference.png', mimeType: 'image/png' }],
    }),
  })
  const runId = (await create.json() as { run: { id: string } }).run.id
  for (let attempt = 0; attempt < 20 && provider.requests.length === 0; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 5))
  }
  assert.equal(provider.requests[0]?.image?.mimeType, 'image/png')
  assert.deepEqual(Buffer.from(provider.requests[0]?.image?.base64 ?? '', 'base64'), imageBytes)
  const run = await (await fetch(`${baseUrl}/api/v1/skill-runs/${runId}`)).json() as { run: { state: string } }
  assert.equal(run.run.state, 'succeeded')
})

test('fails audio input explicitly instead of fabricating a media result', async (context) => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'anime-armory-audio-job-'))
  const skills = path.join(root, 'skills')
  await mkdir(path.join(skills, 'n2d-audio-video'), { recursive: true })
  await writeFile(
    path.join(skills, 'n2d-audio-video', 'SKILL.md'),
    '---\nname: n2d-audio-video\ndescription: standalone\n---\n# Audio video\nUse the real audio.\n',
  )
  const provider = new FakeProvider()
  const { server, baseUrl } = await listenTestServer(testConfig(skills, path.join(root, 'runtime')), provider)
  context.after(() => closeTestServer(server))
  const create = await fetch(`${baseUrl}/api/v1/skill-runs`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      skillId: 'n2d-audio-video',
      workId: randomUUID(),
      line: 'n2d',
      prompt: 'Analyze this audio.',
      generationMode: 'manual',
      idempotencyKey: 'fixture-audio-0001',
      attachments: [{ id: randomUUID(), name: 'beat.mp3', mimeType: 'audio/mpeg' }],
    }),
  })
  const runId = (await create.json() as { run: { id: string } }).run.id
  let run: { state: string; message: string } = { state: 'queued', message: '' }
  for (let attempt = 0; attempt < 20 && (run.state === 'queued' || run.state === 'running'); attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 5))
    run = (await (await fetch(`${baseUrl}/api/v1/skill-runs/${runId}`)).json() as { run: typeof run }).run
  }
  assert.equal(run.state, 'failed')
  assert.match(run.message, /不支持音频 Skill 输入/)
  assert.equal(provider.requests.length, 0)
})
