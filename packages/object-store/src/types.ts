import type { CompletedPart, SignedRequest, StorageProvider } from '@anime-armory/contracts'

export interface UploadObjectInput {
  key: string
  contentType: string
  sizeBytes: number
  expiresInSeconds: number
  metadata?: Record<string, string>
}

export interface CopyObjectInput {
  sourceKey: string
  destinationKey: string
}

export interface MultipartUploadInput {
  key: string
  contentType: string
  metadata?: Record<string, string>
}

export interface SignPartInput {
  key: string
  uploadId: string
  partNumber: number
  expiresInSeconds: number
}

export interface CompleteMultipartInput {
  key: string
  uploadId: string
  parts: CompletedPart[]
}

export interface AbortMultipartInput {
  key: string
  uploadId: string
}

export interface DownloadObjectInput {
  key: string
  expiresInSeconds: number
  fileName?: string
  disposition?: 'inline' | 'attachment'
}

export interface StoredObjectMetadata {
  key: string
  sizeBytes: number
  contentType: string | null
  etag: string | null
  versionId: string | null
  metadata: Record<string, string>
}

export interface CompleteMultipartResult {
  etag: string | null
  versionId: string | null
}

export interface ObjectStore {
  readonly provider: StorageProvider
  readonly bucket: string
  createUploadUrl(input: UploadObjectInput): Promise<SignedRequest>
  createMultipartUpload(input: MultipartUploadInput): Promise<{ uploadId: string }>
  createPartUploadUrl(input: SignPartInput): Promise<SignedRequest>
  completeMultipartUpload(input: CompleteMultipartInput): Promise<CompleteMultipartResult>
  abortMultipartUpload(input: AbortMultipartInput): Promise<void>
  createDownloadUrl(input: DownloadObjectInput): Promise<SignedRequest>
  headObject(key: string): Promise<StoredObjectMetadata>
  copyObject(input: CopyObjectInput): Promise<void>
  deleteObject(key: string): Promise<void>
}
