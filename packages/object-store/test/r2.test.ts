import assert from 'node:assert/strict'
import test from 'node:test'

import { CopyObjectCommand } from '@aws-sdk/client-s3'

import {
  ObjectStoreConfigurationError,
  R2ObjectStore,
  r2ConfigFromEnv,
  type ObjectStore,
} from '../src/index.js'

function createStore(): R2ObjectStore {
  return new R2ObjectStore({
    accountId: 'account',
    accessKeyId: 'access',
    secretAccessKey: 'secret',
    bucket: 'bucket',
  })
}

test('builds an R2 configuration from server-only environment variables', () => {
  const config = r2ConfigFromEnv({
    R2_ACCOUNT_ID: 'account',
    R2_ACCESS_KEY_ID: 'access',
    R2_SECRET_ACCESS_KEY: 'secret',
    R2_BUCKET: 'bucket',
  })

  assert.equal(config.endpoint, 'https://account.r2.cloudflarestorage.com')
  assert.equal(config.bucket, 'bucket')
})

test('rejects an incomplete R2 environment', () => {
  assert.throws(
    () => r2ConfigFromEnv({ R2_ACCOUNT_ID: 'account' }),
    ObjectStoreConfigurationError,
  )
})

test('constructs the adapter without contacting R2', () => {
  const store = createStore()

  assert.equal(store.provider, 'r2')
  assert.equal(store.bucket, 'bucket')
})

test('signs the declared object size into an upload URL', async () => {
  const store = createStore()
  const upload = await store.createUploadUrl({
    key: 'assets/example.bin',
    contentType: 'application/octet-stream',
    sizeBytes: 4096,
    expiresInSeconds: 60,
    metadata: { 'asset-id': 'asset-123' },
  })

  const signedHeaders = new URL(upload.url).searchParams.get('X-Amz-SignedHeaders')?.split(';')
  assert.ok(signedHeaders?.includes('content-length'))
  assert.ok(signedHeaders?.includes('content-type'))
  assert.ok(signedHeaders?.includes('x-amz-meta-asset-id'))
  assert.equal(new URL(upload.url).searchParams.has('x-amz-meta-asset-id'), false)
  assert.equal(upload.headers['content-length'], undefined)
  assert.equal(upload.headers['x-amz-meta-asset-id'], 'asset-123')
})

test('copies an object through the ObjectStore contract with an encoded source', async () => {
  const store: ObjectStore = createStore()
  let sentCommand: unknown
  const client = (store as R2ObjectStore as unknown as {
    client: { send(command: unknown): Promise<unknown> }
  }).client
  client.send = async (command) => {
    sentCommand = command
    return {}
  }

  await store.copyObject({
    sourceKey: "source folder/it's ready (final).png",
    destinationKey: 'published/final.png',
  })

  assert.ok(sentCommand instanceof CopyObjectCommand)
  assert.deepEqual(sentCommand.input, {
    Bucket: 'bucket',
    Key: 'published/final.png',
    CopySource: '/bucket/source%20folder/it%27s%20ready%20%28final%29.png',
  })
})
