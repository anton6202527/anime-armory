import assert from 'node:assert/strict'
import test from 'node:test'

import { DataAccessError, mapAccountAssetUsage, mapAssetRow } from '../src/index.js'

test('maps account asset usage counters safely', () => {
  assert.deepEqual(
    mapAccountAssetUsage({ reserved_bytes: '2048', active_uploads: 3 }),
    { reservedBytes: 2048, activeUploads: 3 },
  )
})

test('maps database rows to provider-neutral asset records', () => {
  const asset = mapAssetRow({
    id: '12c443a7-66f6-4196-b812-4bcd78240cb0',
    project_id: '4b2d6f4a-98ce-4c5b-a38d-f0f850a7ab87',
    owner_account_id: 'd9304575-31c1-4be0-a833-4a8cd04755ff',
    storage_provider: 'r2',
    storage_bucket: 'private',
    object_key: 'projects/p/assets/a/original.mp4',
    object_etag: 'etag',
    object_version_id: null,
    original_name: 'original.mp4',
    content_type: 'video/mp4',
    size_bytes: '1024',
    sha256: null,
    status: 'ready',
    created_at: '2026-07-13T00:00:00.000Z',
    updated_at: '2026-07-13T00:00:00.000Z',
  })

  assert.equal(asset.object.provider, 'r2')
  assert.equal(asset.sizeBytes, 1024)
})

test('rejects bigint values that are unsafe in JavaScript', () => {
  assert.throws(
    () =>
      mapAssetRow({
        id: '12c443a7-66f6-4196-b812-4bcd78240cb0',
        project_id: '4b2d6f4a-98ce-4c5b-a38d-f0f850a7ab87',
        owner_account_id: 'd9304575-31c1-4be0-a833-4a8cd04755ff',
        storage_provider: 'r2',
        storage_bucket: 'private',
        object_key: 'key',
        object_etag: null,
        object_version_id: null,
        original_name: 'file',
        content_type: 'application/octet-stream',
        size_bytes: '9007199254740992',
        sha256: null,
        status: 'ready',
        created_at: '2026-07-13T00:00:00.000Z',
        updated_at: '2026-07-13T00:00:00.000Z',
      }),
    DataAccessError,
  )
})
