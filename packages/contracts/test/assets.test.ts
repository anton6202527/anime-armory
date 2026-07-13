import assert from 'node:assert/strict'
import test from 'node:test'

import {
  ContractError,
  DEFAULT_MAX_ASSET_BYTES,
  parseAssetApiRequest,
} from '../src/index.js'

const projectId = '4b2d6f4a-98ce-4c5b-a38d-f0f850a7ab87'
const assetId = '12c443a7-66f6-4196-b812-4bcd78240cb0'

test('parses a create-upload request', () => {
  const parsed = parseAssetApiRequest({
    action: 'create-upload',
    projectId,
    fileName: 'clip.mp4',
    contentType: 'video/mp4',
    sizeBytes: 1024,
    sha256: 'a'.repeat(64),
  })

  assert.equal(parsed.action, 'create-upload')
  assert.equal(parsed.fileName, 'clip.mp4')
  assert.equal(parsed.sha256, 'a'.repeat(64))
})

test('rejects assets above the configured limit', () => {
  assert.throws(
    () =>
      parseAssetApiRequest({
        action: 'create-upload',
        projectId,
        fileName: 'clip.mp4',
        contentType: 'video/mp4',
        sizeBytes: DEFAULT_MAX_ASSET_BYTES + 1,
      }),
    (error: unknown) => error instanceof ContractError && error.field === 'sizeBytes',
  )
})

test('sorts completed multipart parts', () => {
  const parsed = parseAssetApiRequest({
    action: 'complete-upload',
    assetId,
    parts: [
      { partNumber: 2, etag: 'etag-2' },
      { partNumber: 1, etag: 'etag-1' },
    ],
  })

  assert.equal(parsed.action, 'complete-upload')
  assert.deepEqual(parsed.parts?.map((part) => part.partNumber), [1, 2])
})

test('rejects duplicate part numbers', () => {
  assert.throws(() =>
    parseAssetApiRequest({
      action: 'sign-parts',
      assetId,
      partNumbers: [1, 1],
    }),
  )
})
