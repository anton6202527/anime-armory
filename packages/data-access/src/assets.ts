import type { SupabaseClient } from '@supabase/supabase-js'

import type { AssetRecord, AssetStatus, StorageProvider, UploadMode } from '@anime-armory/contracts'

export interface CreatePendingAssetInput {
  id: string
  projectId: string
  ownerAccountId: string
  provider: StorageProvider
  bucket: string
  objectKey: string
  originalName: string
  relativePath: string
  contentType: string
  sizeBytes: number
  sha256?: string
}

export interface CreateUploadSessionInput {
  assetId: string
  createdBy: string
  mode: UploadMode
  uploadId?: string
  partSizeBytes?: number
  expiresAt: string
}

export interface UploadSessionRecord {
  assetId: string
  createdBy: string
  mode: UploadMode
  uploadId: string | null
  partSizeBytes: number | null
  state: 'pending' | 'uploading' | 'completed' | 'aborted' | 'failed'
  expiresAt: string
}

export interface ReadyAssetInput {
  sizeBytes: number
  contentType: string | null
  etag: string | null
  versionId: string | null
}

export interface AccountAssetUsage {
  reservedBytes: number
  activeUploads: number
}

export interface AssetRepository {
  currentAccountId(): Promise<string>
  getAccountAssetUsage(accountId: string): Promise<AccountAssetUsage>
  createPendingAsset(input: CreatePendingAssetInput): Promise<AssetRecord>
  createUploadSession(input: CreateUploadSessionInput): Promise<UploadSessionRecord>
  getAsset(assetId: string): Promise<AssetRecord | null>
  listReadyAssets(projectId: string): Promise<AssetRecord[]>
  getUploadSession(assetId: string): Promise<UploadSessionRecord | null>
  markAssetReady(assetId: string, input: ReadyAssetInput): Promise<AssetRecord>
  supersedeReadyAssets(projectId: string, relativePath: string, currentAssetId: string): Promise<AssetRecord[]>
  markAssetDeleted(assetId: string): Promise<void>
  markAssetFailed(assetId: string, reason: string): Promise<void>
  markUploadState(assetId: string, state: UploadSessionRecord['state']): Promise<void>
}

export class DataAccessError extends Error {
  readonly operation: string
  readonly causeValue: unknown

  constructor(operation: string, message: string, causeValue?: unknown) {
    super(message)
    this.name = 'DataAccessError'
    this.operation = operation
    this.causeValue = causeValue
  }
}

interface AssetRow {
  id: string
  project_id: string
  owner_account_id: string
  storage_provider: StorageProvider
  storage_bucket: string
  object_key: string
  object_etag: string | null
  object_version_id: string | null
  original_name: string
  relative_path: string
  content_type: string
  size_bytes: number | string
  sha256: string | null
  status: AssetStatus
  created_at: string
  updated_at: string
}

interface UploadSessionRow {
  asset_id: string
  created_by: string
  mode: UploadMode
  upload_id: string | null
  part_size_bytes: number | string | null
  state: UploadSessionRecord['state']
  expires_at: string
}

function asSafeInteger(value: number | string, field: string): number {
  const parsed = typeof value === 'number' ? value : Number(value)
  if (!Number.isSafeInteger(parsed) || parsed < 0) {
    throw new DataAccessError('map-row', `${field} is outside JavaScript's safe integer range`)
  }
  return parsed
}

export function mapAccountAssetUsage(row: {
  reserved_bytes: number | string
  active_uploads: number | string
}): AccountAssetUsage {
  return {
    reservedBytes: asSafeInteger(row.reserved_bytes, 'reserved_bytes'),
    activeUploads: asSafeInteger(row.active_uploads, 'active_uploads'),
  }
}

export function mapAssetRow(row: AssetRow): AssetRecord {
  return {
    id: row.id,
    projectId: row.project_id,
    ownerAccountId: row.owner_account_id,
    object: {
      provider: row.storage_provider,
      bucket: row.storage_bucket,
      key: row.object_key,
      etag: row.object_etag,
      versionId: row.object_version_id,
    },
    originalName: row.original_name,
    relativePath: row.relative_path,
    contentType: row.content_type,
    sizeBytes: asSafeInteger(row.size_bytes, 'size_bytes'),
    sha256: row.sha256,
    status: row.status,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }
}

function mapUploadSessionRow(row: UploadSessionRow): UploadSessionRecord {
  return {
    assetId: row.asset_id,
    createdBy: row.created_by,
    mode: row.mode,
    uploadId: row.upload_id,
    partSizeBytes:
      row.part_size_bytes === null ? null : asSafeInteger(row.part_size_bytes, 'part_size_bytes'),
    state: row.state,
    expiresAt: row.expires_at,
  }
}

function failureMessage(error: { message?: string } | null, fallback: string): string {
  return error?.message || fallback
}

export class SupabaseAssetRepository implements AssetRepository {
  constructor(private readonly client: SupabaseClient) {}

  async currentAccountId(): Promise<string> {
    const { data, error } = await this.client.rpc('current_account_id')
    if (error || typeof data !== 'string') {
      throw new DataAccessError(
        'current-account',
        failureMessage(error, 'No application account is linked to the current user'),
        error,
      )
    }
    return data
  }

  async getAccountAssetUsage(accountId: string): Promise<AccountAssetUsage> {
    const { data, error } = await this.client
      .rpc('account_asset_usage', { target_account_id: accountId })
      .single()
    if (error || !data) {
      throw new DataAccessError(
        'account-asset-usage',
        failureMessage(error, 'Unable to read account asset usage'),
        error,
      )
    }
    return mapAccountAssetUsage(
      data as { reserved_bytes: number | string; active_uploads: number | string },
    )
  }

  async createPendingAsset(input: CreatePendingAssetInput): Promise<AssetRecord> {
    const { data, error } = await this.client
      .from('assets')
      .insert({
        id: input.id,
        project_id: input.projectId,
        owner_account_id: input.ownerAccountId,
        storage_provider: input.provider,
        storage_bucket: input.bucket,
        object_key: input.objectKey,
        original_name: input.originalName,
        relative_path: input.relativePath,
        content_type: input.contentType,
        size_bytes: input.sizeBytes,
        sha256: input.sha256 ?? null,
        status: 'pending',
      })
      .select('*')
      .single()
    if (error || !data) {
      throw new DataAccessError('create-asset', failureMessage(error, 'Unable to create asset'), error)
    }
    return mapAssetRow(data as AssetRow)
  }

  async createUploadSession(input: CreateUploadSessionInput): Promise<UploadSessionRecord> {
    const { data, error } = await this.client
      .from('asset_uploads')
      .insert({
        asset_id: input.assetId,
        created_by: input.createdBy,
        mode: input.mode,
        upload_id: input.uploadId ?? null,
        part_size_bytes: input.partSizeBytes ?? null,
        state: 'uploading',
        expires_at: input.expiresAt,
      })
      .select('*')
      .single()
    if (error || !data) {
      throw new DataAccessError(
        'create-upload-session',
        failureMessage(error, 'Unable to create upload session'),
        error,
      )
    }
    return mapUploadSessionRow(data as UploadSessionRow)
  }

  async getAsset(assetId: string): Promise<AssetRecord | null> {
    const { data, error } = await this.client.from('assets').select('*').eq('id', assetId).maybeSingle()
    if (error) throw new DataAccessError('get-asset', error.message, error)
    return data ? mapAssetRow(data as AssetRow) : null
  }

  async listReadyAssets(projectId: string): Promise<AssetRecord[]> {
    const { data, error } = await this.client
      .from('assets')
      .select('*')
      .eq('project_id', projectId)
      .eq('status', 'ready')
      .is('deleted_at', null)
      .order('relative_path', { ascending: true })
      .order('created_at', { ascending: false })
    if (error) throw new DataAccessError('list-assets', error.message, error)
    return (data ?? []).map((row) => mapAssetRow(row as AssetRow))
  }

  async getUploadSession(assetId: string): Promise<UploadSessionRecord | null> {
    const { data, error } = await this.client
      .from('asset_uploads')
      .select('*')
      .eq('asset_id', assetId)
      .maybeSingle()
    if (error) throw new DataAccessError('get-upload-session', error.message, error)
    return data ? mapUploadSessionRow(data as UploadSessionRow) : null
  }

  async markAssetReady(assetId: string, input: ReadyAssetInput): Promise<AssetRecord> {
    const { data, error } = await this.client
      .from('assets')
      .update({
        status: 'ready',
        size_bytes: input.sizeBytes,
        content_type: input.contentType,
        object_etag: input.etag,
        object_version_id: input.versionId,
        failure_reason: null,
      })
      .eq('id', assetId)
      .select('*')
      .single()
    if (error || !data) {
      throw new DataAccessError('mark-asset-ready', failureMessage(error, 'Unable to update asset'), error)
    }
    return mapAssetRow(data as AssetRow)
  }

  async supersedeReadyAssets(
    projectId: string,
    relativePath: string,
    currentAssetId: string,
  ): Promise<AssetRecord[]> {
    const { data, error } = await this.client
      .from('assets')
      .select('*')
      .eq('project_id', projectId)
      .eq('relative_path', relativePath)
      .eq('status', 'ready')
      .is('deleted_at', null)
      .neq('id', currentAssetId)
    if (error) throw new DataAccessError('list-superseded-assets', error.message, error)
    const previous = (data ?? []).map((row) => mapAssetRow(row as AssetRow))
    if (previous.length === 0) return []

    const { error: updateError } = await this.client
      .from('assets')
      .update({ status: 'deleted', deleted_at: new Date().toISOString() })
      .in('id', previous.map((asset) => asset.id))
    if (updateError) {
      throw new DataAccessError('supersede-assets', updateError.message, updateError)
    }
    return previous
  }

  async markAssetDeleted(assetId: string): Promise<void> {
    const { error } = await this.client
      .from('assets')
      .update({ status: 'deleted', deleted_at: new Date().toISOString() })
      .eq('id', assetId)
    if (error) throw new DataAccessError('delete-asset', error.message, error)
  }

  async markAssetFailed(assetId: string, reason: string): Promise<void> {
    const { error } = await this.client
      .from('assets')
      .update({ status: 'failed', failure_reason: reason.slice(0, 1000) })
      .eq('id', assetId)
    if (error) throw new DataAccessError('mark-asset-failed', error.message, error)
  }

  async markUploadState(assetId: string, state: UploadSessionRecord['state']): Promise<void> {
    const { error } = await this.client
      .from('asset_uploads')
      .update({ state })
      .eq('asset_id', assetId)
    if (error) throw new DataAccessError('mark-upload-state', error.message, error)
  }
}
