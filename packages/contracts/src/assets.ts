export const MEBIBYTE = 1024 * 1024
export const DEFAULT_SINGLE_UPLOAD_LIMIT_BYTES = 100 * MEBIBYTE
export const DEFAULT_MULTIPART_PART_SIZE_BYTES = 32 * MEBIBYTE
export const DEFAULT_MAX_ASSET_BYTES = 50 * 1024 * MEBIBYTE
export const MAX_SIGNED_PARTS_PER_REQUEST = 100

export type StorageProvider = 'r2' | 'cos'
export type AssetStatus = 'pending' | 'uploading' | 'ready' | 'failed' | 'deleted'
export type UploadMode = 'single' | 'multipart'
export type ProjectRole = 'owner' | 'editor' | 'viewer'

export interface CloudProjectRecord {
  id: string
  name: string
  clientKey: string
  role: ProjectRole
  createdAt: string
  updatedAt: string
}

export interface StoredObjectRef {
  provider: StorageProvider
  bucket: string
  key: string
  etag?: string | null
  versionId?: string | null
}

export interface AssetRecord {
  id: string
  projectId: string
  ownerAccountId: string
  object: StoredObjectRef
  originalName: string
  relativePath: string
  contentType: string
  sizeBytes: number
  sha256?: string | null
  status: AssetStatus
  createdAt: string
  updatedAt: string
}

export interface EnsureProjectRequest {
  action: 'ensure-project'
  clientKey: string
  name: string
}

export interface ListProjectsRequest {
  action: 'list-projects'
}

export interface ListAssetsRequest {
  action: 'list-assets'
  projectId: string
}

export interface CreateUploadRequest {
  action: 'create-upload'
  projectId: string
  fileName: string
  relativePath: string
  contentType: string
  sizeBytes: number
  sha256?: string
}

export interface DeleteAssetRequest {
  action: 'delete-asset'
  assetId: string
}

export interface SignPartsRequest {
  action: 'sign-parts'
  assetId: string
  partNumbers: number[]
}

export interface CompletedPart {
  partNumber: number
  etag: string
}

export interface CompleteUploadRequest {
  action: 'complete-upload'
  assetId: string
  parts?: CompletedPart[]
}

export interface AbortUploadRequest {
  action: 'abort-upload'
  assetId: string
}

export interface CreateDownloadRequest {
  action: 'create-download'
  assetId: string
  disposition?: 'inline' | 'attachment'
}

export type AssetApiRequest =
  | EnsureProjectRequest
  | ListProjectsRequest
  | ListAssetsRequest
  | CreateUploadRequest
  | SignPartsRequest
  | CompleteUploadRequest
  | AbortUploadRequest
  | CreateDownloadRequest
  | DeleteAssetRequest

export interface SignedRequest {
  url: string
  method: 'PUT' | 'GET'
  headers: Record<string, string>
  expiresAt: string
}

export interface EnsureProjectResponse {
  action: 'ensure-project'
  project: CloudProjectRecord
}

export interface ListProjectsResponse {
  action: 'list-projects'
  projects: CloudProjectRecord[]
}

export interface ListAssetsResponse {
  action: 'list-assets'
  projectId: string
  assets: AssetRecord[]
}

export interface CreateUploadResponse {
  action: 'create-upload'
  assetId: string
  mode: UploadMode
  object: StoredObjectRef
  partSizeBytes?: number
  upload?: SignedRequest
}

export interface SignPartsResponse {
  action: 'sign-parts'
  assetId: string
  parts: Array<{ partNumber: number; upload: SignedRequest }>
}

export interface CompleteUploadResponse {
  action: 'complete-upload'
  asset: AssetRecord
}

export interface AbortUploadResponse {
  action: 'abort-upload'
  assetId: string
  status: 'failed'
}

export interface CreateDownloadResponse {
  action: 'create-download'
  assetId: string
  download: SignedRequest
}

export interface DeleteAssetResponse {
  action: 'delete-asset'
  assetId: string
  status: 'deleted'
}

export type AssetApiResponse =
  | EnsureProjectResponse
  | ListProjectsResponse
  | ListAssetsResponse
  | CreateUploadResponse
  | SignPartsResponse
  | CompleteUploadResponse
  | AbortUploadResponse
  | CreateDownloadResponse
  | DeleteAssetResponse

export class ContractError extends Error {
  readonly field: string | undefined

  constructor(message: string, field?: string) {
    super(message)
    this.name = 'ContractError'
    this.field = field
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function requiredString(
  input: Record<string, unknown>,
  field: string,
  options: { maxLength?: number } = {},
): string {
  const value = input[field]
  if (typeof value !== 'string' || value.trim() === '') {
    throw new ContractError(`${field} must be a non-empty string`, field)
  }
  const normalized = value.trim()
  if (options.maxLength !== undefined && normalized.length > options.maxLength) {
    throw new ContractError(`${field} exceeds ${options.maxLength} characters`, field)
  }
  return normalized
}

function optionalString(
  input: Record<string, unknown>,
  field: string,
  options: { maxLength?: number } = {},
): string | undefined {
  if (input[field] === undefined || input[field] === null || input[field] === '') return undefined
  return requiredString(input, field, options)
}

function positiveInteger(input: Record<string, unknown>, field: string): number {
  const value = input[field]
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value <= 0) {
    throw new ContractError(`${field} must be a positive safe integer`, field)
  }
  return value
}

function nonNegativeInteger(input: Record<string, unknown>, field: string): number {
  const value = input[field]
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) {
    throw new ContractError(`${field} must be a non-negative safe integer`, field)
  }
  return value
}

function uuid(input: Record<string, unknown>, field: string): string {
  const value = requiredString(input, field, { maxLength: 36 })
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)) {
    throw new ContractError(`${field} must be a UUID`, field)
  }
  return value
}

function sha256(input: Record<string, unknown>): string | undefined {
  const value = optionalString(input, 'sha256', { maxLength: 64 })
  if (value !== undefined && !/^[0-9a-f]{64}$/i.test(value)) {
    throw new ContractError('sha256 must contain 64 hexadecimal characters', 'sha256')
  }
  return value?.toLowerCase()
}

function relativePath(input: Record<string, unknown>): string {
  const value = requiredString(input, 'relativePath', { maxLength: 1024 })
  if (
    value.startsWith('/') ||
    value.includes('\\') ||
    value.includes('\0') ||
    value.split('/').some((segment) => segment === '' || segment === '.' || segment === '..')
  ) {
    throw new ContractError('relativePath must be a safe normalized relative path', 'relativePath')
  }
  return value
}

export function parseAssetApiRequest(
  value: unknown,
  options: { maxAssetBytes?: number } = {},
): AssetApiRequest {
  if (!isRecord(value)) throw new ContractError('request body must be a JSON object')
  const action = requiredString(value, 'action', { maxLength: 40 })

  switch (action) {
    case 'ensure-project':
      return {
        action,
        clientKey: uuid(value, 'clientKey'),
        name: requiredString(value, 'name', { maxLength: 160 }),
      }
    case 'list-projects':
      return { action }
    case 'list-assets':
      return { action, projectId: uuid(value, 'projectId') }
    case 'create-upload': {
      const sizeBytes = nonNegativeInteger(value, 'sizeBytes')
      const maxAssetBytes = options.maxAssetBytes ?? DEFAULT_MAX_ASSET_BYTES
      if (sizeBytes > maxAssetBytes) {
        throw new ContractError(`sizeBytes exceeds the configured ${maxAssetBytes} byte limit`, 'sizeBytes')
      }
      const contentType = requiredString(value, 'contentType', { maxLength: 255 }).toLowerCase()
      if (!/^[a-z0-9!#$&^_.+-]+\/[a-z0-9!#$&^_.+*-]+$/i.test(contentType)) {
        throw new ContractError('contentType must be a valid MIME type', 'contentType')
      }
      const digest = sha256(value)
      return {
        action,
        projectId: uuid(value, 'projectId'),
        fileName: requiredString(value, 'fileName', { maxLength: 255 }),
        relativePath: relativePath(value),
        contentType,
        sizeBytes,
        ...(digest ? { sha256: digest } : {}),
      }
    }
    case 'sign-parts': {
      const rawParts = value.partNumbers
      if (!Array.isArray(rawParts) || rawParts.length === 0) {
        throw new ContractError('partNumbers must be a non-empty array', 'partNumbers')
      }
      if (rawParts.length > MAX_SIGNED_PARTS_PER_REQUEST) {
        throw new ContractError(
          `partNumbers cannot contain more than ${MAX_SIGNED_PARTS_PER_REQUEST} entries`,
          'partNumbers',
        )
      }
      const partNumbers = rawParts.map((part, index) => {
        if (typeof part !== 'number' || !Number.isInteger(part) || part < 1 || part > 10_000) {
          throw new ContractError(`partNumbers[${index}] must be between 1 and 10000`, 'partNumbers')
        }
        return part
      })
      if (new Set(partNumbers).size !== partNumbers.length) {
        throw new ContractError('partNumbers must not contain duplicates', 'partNumbers')
      }
      return { action, assetId: uuid(value, 'assetId'), partNumbers }
    }
    case 'complete-upload': {
      const assetId = uuid(value, 'assetId')
      if (value.parts === undefined) return { action, assetId }
      if (!Array.isArray(value.parts) || value.parts.length === 0 || value.parts.length > 10_000) {
        throw new ContractError('parts must contain between 1 and 10000 entries', 'parts')
      }
      const parts = value.parts.map((part, index) => {
        if (!isRecord(part)) throw new ContractError(`parts[${index}] must be an object`, 'parts')
        return {
          partNumber: positiveInteger(part, 'partNumber'),
          etag: requiredString(part, 'etag', { maxLength: 512 }),
        }
      })
      parts.sort((left, right) => left.partNumber - right.partNumber)
      if (new Set(parts.map((part) => part.partNumber)).size !== parts.length) {
        throw new ContractError('parts must not contain duplicate part numbers', 'parts')
      }
      return { action, assetId, parts }
    }
    case 'abort-upload':
      return { action, assetId: uuid(value, 'assetId') }
    case 'create-download': {
      const disposition = value.disposition
      if (disposition !== undefined && disposition !== 'inline' && disposition !== 'attachment') {
        throw new ContractError('disposition must be inline or attachment', 'disposition')
      }
      const normalizedDisposition = disposition === 'inline' || disposition === 'attachment'
        ? disposition
        : undefined
      return {
        action,
        assetId: uuid(value, 'assetId'),
        ...(normalizedDisposition ? { disposition: normalizedDisposition } : {}),
      }
    }
    case 'delete-asset':
      return { action, assetId: uuid(value, 'assetId') }
    default:
      throw new ContractError(`unsupported action: ${action}`, 'action')
  }
}

export function expiresAtFromNow(seconds: number, now = Date.now()): string {
  return new Date(now + seconds * 1000).toISOString()
}
