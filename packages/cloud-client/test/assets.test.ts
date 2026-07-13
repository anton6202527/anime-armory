import assert from 'node:assert/strict'
import test from 'node:test'

import { AssetApiClient, CloudApiError, type AssetUploadSource } from '../src/index.js'

const projectId = '4b2d6f4a-98ce-4c5b-a38d-f0f850a7ab87'
const assetId = '12c443a7-66f6-4196-b812-4bcd78240cb0'

function source(size: number): AssetUploadSource {
  const blob = new Blob([new Uint8Array(size)], { type: 'video/mp4' })
  return {
    name: 'clip.mp4',
    type: blob.type,
    size: blob.size,
    slice: blob.slice.bind(blob),
  }
}

function readyAsset(sizeBytes: number) {
  return {
    id: assetId,
    projectId,
    ownerAccountId: 'd9304575-31c1-4be0-a833-4a8cd04755ff',
    object: { provider: 'r2' as const, bucket: 'private', key: 'key' },
    originalName: 'clip.mp4',
    contentType: 'video/mp4',
    sizeBytes,
    status: 'ready' as const,
    createdAt: '2026-07-13T00:00:00.000Z',
    updatedAt: '2026-07-13T00:00:00.000Z',
  }
}

test('requires a login before calling the cloud API', async () => {
  const client = new AssetApiClient({
    endpoint: 'https://example.test/assets',
    getAccessToken: async () => null,
    fetch: async () => new Response(),
  })

  await assert.rejects(
    client.createUpload(projectId, source(1)),
    (error: unknown) => error instanceof CloudApiError && error.code === 'authentication_required',
  )
})

test('uploads and completes a single object', async () => {
  const requests: string[] = []
  const fetcher: typeof fetch = async (input, init) => {
    const url = String(input)
    requests.push(`${init?.method ?? 'GET'} ${url}`)
    if (url === 'https://r2.test/upload') {
      return new Response(null, { status: 200, headers: { etag: 'single-etag' } })
    }
    const body = JSON.parse(String(init?.body)) as { action: string }
    if (body.action === 'create-upload') {
      return Response.json({
        action: 'create-upload',
        assetId,
        mode: 'single',
        object: { provider: 'r2', bucket: 'private', key: 'key' },
        upload: {
          method: 'PUT',
          url: 'https://r2.test/upload',
          headers: { 'content-type': 'video/mp4' },
          expiresAt: '2026-07-13T00:15:00.000Z',
        },
      })
    }
    return Response.json({ action: 'complete-upload', asset: readyAsset(16) })
  }
  const progress: number[] = []
  const client = new AssetApiClient({
    endpoint: 'https://api.test/assets',
    getAccessToken: async () => 'token',
    fetch: fetcher,
  })

  const asset = await client.uploadAsset({
    projectId,
    source: source(16),
    onProgress: (uploaded) => progress.push(uploaded),
  })

  assert.equal(asset.status, 'ready')
  assert.deepEqual(progress, [0, 16])
  assert.deepEqual(requests, [
    'POST https://api.test/assets',
    'PUT https://r2.test/upload',
    'POST https://api.test/assets',
  ])
})

test('uploads multipart objects and reports progress', async () => {
  const actions: string[] = []
  const fetcher: typeof fetch = async (input, init) => {
    const url = String(input)
    if (url.startsWith('https://r2.test/part/')) {
      return new Response(null, { status: 200, headers: { etag: `etag-${url.split('/').pop()}` } })
    }
    const body = JSON.parse(String(init?.body)) as {
      action: string
      partNumbers?: number[]
      parts?: Array<{ partNumber: number }>
    }
    actions.push(body.action)
    if (body.action === 'create-upload') {
      return Response.json({
        action: 'create-upload',
        assetId,
        mode: 'multipart',
        partSizeBytes: 4,
        object: { provider: 'r2', bucket: 'private', key: 'key' },
      })
    }
    if (body.action === 'sign-parts') {
      return Response.json({
        action: 'sign-parts',
        assetId,
        parts: body.partNumbers?.map((partNumber) => ({
          partNumber,
          upload: {
            method: 'PUT',
            url: `https://r2.test/part/${partNumber}`,
            headers: {},
            expiresAt: '2026-07-13T00:15:00.000Z',
          },
        })),
      })
    }
    assert.deepEqual(body.parts?.map((part) => part.partNumber), [1, 2, 3])
    return Response.json({ action: 'complete-upload', asset: readyAsset(10) })
  }
  const progress: number[] = []
  const client = new AssetApiClient({
    endpoint: 'https://api.test/assets',
    getAccessToken: async () => 'token',
    fetch: fetcher,
    multipartConcurrency: 2,
  })

  await client.uploadAsset({
    projectId,
    source: source(10),
    onProgress: (uploaded) => progress.push(uploaded),
  })

  assert.deepEqual(actions, ['create-upload', 'sign-parts', 'complete-upload'])
  assert.deepEqual(progress, [0, 8, 10])
})
