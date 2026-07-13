import {
  AbortMultipartUploadCommand,
  CompleteMultipartUploadCommand,
  CopyObjectCommand,
  CreateMultipartUploadCommand,
  DeleteObjectCommand,
  GetObjectCommand,
  HeadObjectCommand,
  PutObjectCommand,
  S3Client,
  UploadPartCommand,
} from '@aws-sdk/client-s3'
import { getSignedUrl } from '@aws-sdk/s3-request-presigner'

import { expiresAtFromNow, type SignedRequest } from '@anime-armory/contracts'
import type {
  AbortMultipartInput,
  CompleteMultipartInput,
  CompleteMultipartResult,
  CopyObjectInput,
  DownloadObjectInput,
  MultipartUploadInput,
  ObjectStore,
  SignPartInput,
  StoredObjectMetadata,
  UploadObjectInput,
} from './types.ts'

export interface R2ObjectStoreConfig {
  accountId: string
  accessKeyId: string
  secretAccessKey: string
  bucket: string
  endpoint?: string
}

export class ObjectStoreConfigurationError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ObjectStoreConfigurationError'
  }
}

function requireConfig(value: string | undefined, field: string): string {
  if (!value?.trim()) throw new ObjectStoreConfigurationError(`${field} is required`)
  return value.trim()
}

function normalizeEtag(value: string | undefined): string | null {
  return value?.replace(/^"|"$/g, '') ?? null
}

function contentDisposition(disposition: 'inline' | 'attachment', fileName?: string): string {
  if (!fileName) return disposition
  const fallback = fileName.replace(/[^a-zA-Z0-9._-]+/g, '_').slice(0, 120) || 'download'
  return `${disposition}; filename="${fallback}"; filename*=UTF-8''${encodeURIComponent(fileName)}`
}

function encodePathSegment(value: string): string {
  return encodeURIComponent(value).replace(/[!'()*]/g, (character) =>
    `%${character.charCodeAt(0).toString(16).toUpperCase()}`
  )
}

function copySource(bucket: string, key: string): string {
  const encodedKey = key.split('/').map(encodePathSegment).join('/')
  return `/${encodePathSegment(bucket)}/${encodedKey}`
}

export function r2ConfigFromEnv(env: Record<string, string | undefined>): R2ObjectStoreConfig {
  const accountId = requireConfig(env.R2_ACCOUNT_ID, 'R2_ACCOUNT_ID')
  return {
    accountId,
    accessKeyId: requireConfig(env.R2_ACCESS_KEY_ID, 'R2_ACCESS_KEY_ID'),
    secretAccessKey: requireConfig(env.R2_SECRET_ACCESS_KEY, 'R2_SECRET_ACCESS_KEY'),
    bucket: requireConfig(env.R2_BUCKET, 'R2_BUCKET'),
    endpoint: env.R2_ENDPOINT?.trim() || `https://${accountId}.r2.cloudflarestorage.com`,
  }
}

export class R2ObjectStore implements ObjectStore {
  readonly provider = 'r2' as const
  readonly bucket: string
  private readonly client: S3Client

  constructor(config: R2ObjectStoreConfig) {
    this.bucket = requireConfig(config.bucket, 'bucket')
    const accountId = requireConfig(config.accountId, 'accountId')
    this.client = new S3Client({
      region: 'auto',
      endpoint: config.endpoint?.trim() || `https://${accountId}.r2.cloudflarestorage.com`,
      credentials: {
        accessKeyId: requireConfig(config.accessKeyId, 'accessKeyId'),
        secretAccessKey: requireConfig(config.secretAccessKey, 'secretAccessKey'),
      },
      requestChecksumCalculation: 'WHEN_REQUIRED',
      responseChecksumValidation: 'WHEN_REQUIRED',
    })
  }

  async createUploadUrl(input: UploadObjectInput): Promise<SignedRequest> {
    const metadataHeaders = Object.fromEntries(
      Object.entries(input.metadata ?? {}).map(([key, value]) => [
        `x-amz-meta-${key.toLowerCase()}`,
        value,
      ]),
    )
    const command = new PutObjectCommand({
      Bucket: this.bucket,
      Key: input.key,
      ContentLength: input.sizeBytes,
      ContentType: input.contentType,
      Metadata: input.metadata,
    })
    return {
      method: 'PUT',
      url: await getSignedUrl(this.client, command, {
        expiresIn: input.expiresInSeconds,
        signableHeaders: new Set(['content-type']),
        // R2 does not persist custom metadata that the generic SigV4 signer
        // hoists into query parameters. Keep it in explicit signed headers.
        unhoistableHeaders: new Set(Object.keys(metadataHeaders)),
      }),
      // Browsers set Content-Length from the Blob body and forbid application
      // code from setting it explicitly. It is still part of SignedHeaders.
      headers: { 'content-type': input.contentType, ...metadataHeaders },
      expiresAt: expiresAtFromNow(input.expiresInSeconds),
    }
  }

  async createMultipartUpload(input: MultipartUploadInput): Promise<{ uploadId: string }> {
    const result = await this.client.send(
      new CreateMultipartUploadCommand({
        Bucket: this.bucket,
        Key: input.key,
        ContentType: input.contentType,
        Metadata: input.metadata,
      }),
    )
    if (!result.UploadId) throw new Error('R2 did not return an upload ID')
    return { uploadId: result.UploadId }
  }

  async createPartUploadUrl(input: SignPartInput): Promise<SignedRequest> {
    const command = new UploadPartCommand({
      Bucket: this.bucket,
      Key: input.key,
      UploadId: input.uploadId,
      PartNumber: input.partNumber,
    })
    return {
      method: 'PUT',
      url: await getSignedUrl(this.client, command, { expiresIn: input.expiresInSeconds }),
      headers: {},
      expiresAt: expiresAtFromNow(input.expiresInSeconds),
    }
  }

  async completeMultipartUpload(input: CompleteMultipartInput): Promise<CompleteMultipartResult> {
    const result = await this.client.send(
      new CompleteMultipartUploadCommand({
        Bucket: this.bucket,
        Key: input.key,
        UploadId: input.uploadId,
        MultipartUpload: {
          Parts: input.parts.map((part) => ({ ETag: part.etag, PartNumber: part.partNumber })),
        },
      }),
    )
    return {
      etag: normalizeEtag(result.ETag),
      versionId: result.VersionId ?? null,
    }
  }

  async abortMultipartUpload(input: AbortMultipartInput): Promise<void> {
    await this.client.send(
      new AbortMultipartUploadCommand({
        Bucket: this.bucket,
        Key: input.key,
        UploadId: input.uploadId,
      }),
    )
  }

  async createDownloadUrl(input: DownloadObjectInput): Promise<SignedRequest> {
    const disposition = input.disposition ?? 'inline'
    const command = new GetObjectCommand({
      Bucket: this.bucket,
      Key: input.key,
      ResponseContentDisposition: contentDisposition(disposition, input.fileName),
    })
    return {
      method: 'GET',
      url: await getSignedUrl(this.client, command, { expiresIn: input.expiresInSeconds }),
      headers: {},
      expiresAt: expiresAtFromNow(input.expiresInSeconds),
    }
  }

  async headObject(key: string): Promise<StoredObjectMetadata> {
    const result = await this.client.send(new HeadObjectCommand({ Bucket: this.bucket, Key: key }))
    return {
      key,
      sizeBytes: result.ContentLength ?? 0,
      contentType: result.ContentType ?? null,
      etag: normalizeEtag(result.ETag),
      versionId: result.VersionId ?? null,
      metadata: result.Metadata ?? {},
    }
  }

  async copyObject(input: CopyObjectInput): Promise<void> {
    await this.client.send(
      new CopyObjectCommand({
        Bucket: this.bucket,
        Key: input.destinationKey,
        CopySource: copySource(this.bucket, input.sourceKey),
      }),
    )
  }

  async deleteObject(key: string): Promise<void> {
    await this.client.send(new DeleteObjectCommand({ Bucket: this.bucket, Key: key }))
  }
}
