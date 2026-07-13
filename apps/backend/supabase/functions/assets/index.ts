import { createClient, type SupabaseClient } from '@supabase/supabase-js'

import {
  type AssetApiRequest,
  type AssetApiResponse,
  type AssetRecord,
  type CompletedPart,
  ContractError,
  DEFAULT_MAX_ASSET_BYTES,
  DEFAULT_MULTIPART_PART_SIZE_BYTES,
  DEFAULT_SINGLE_UPLOAD_LIMIT_BYTES,
  expiresAtFromNow,
  parseAssetApiRequest,
} from '@anime-armory/contracts'
import {
  type AssetRepository,
  DataAccessError,
  SupabaseAssetRepository,
  type UploadSessionRecord,
} from '@anime-armory/data-access'
import {
  type ObjectStore,
  ObjectStoreConfigurationError,
  r2ConfigFromEnv,
  R2ObjectStore,
  type StoredObjectMetadata,
} from '@anime-armory/object-store'

const MEBIBYTE = 1024 * 1024

interface RuntimeConfig {
  maxAssetBytes: number
  accountMaxReservedBytes: number
  maxActiveUploadsPerAccount: number
  singleUploadLimitBytes: number
  multipartPartSizeBytes: number
  signedUrlTtlSeconds: number
  uploadSessionTtlSeconds: number
  allowedOrigins: Set<string>
}

interface RequestContext {
  userClient: SupabaseClient
  userRepository: AssetRepository
  adminRepository: AssetRepository
  accountId: string
  objectStore: ObjectStore
  config: RuntimeConfig
}

class HttpError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'HttpError'
    this.status = status
    this.code = code
  }
}

function envRecord(): Record<string, string | undefined> {
  return {
    R2_ACCOUNT_ID: Deno.env.get('R2_ACCOUNT_ID'),
    R2_ACCESS_KEY_ID: Deno.env.get('R2_ACCESS_KEY_ID'),
    R2_SECRET_ACCESS_KEY: Deno.env.get('R2_SECRET_ACCESS_KEY'),
    R2_BUCKET: Deno.env.get('R2_BUCKET'),
    R2_ENDPOINT: Deno.env.get('R2_ENDPOINT'),
  }
}

function requiredEnv(name: string): string {
  const value = Deno.env.get(name)?.trim()
  if (!value) throw new HttpError(503, 'server_not_configured', `${name} is not configured`)
  return value
}

function supabaseApiKey(options: {
  mapName: string
  singularName: string
  legacyName: string
}): string {
  const keyMap = Deno.env.get(options.mapName)?.trim()
  if (keyMap) {
    try {
      const parsed: unknown = JSON.parse(keyMap)
      if (parsed && typeof parsed === 'object') {
        const defaultKey = (parsed as Record<string, unknown>).default
        if (typeof defaultKey === 'string' && defaultKey.trim()) return defaultKey.trim()
      }
    } catch {
      throw new HttpError(
        503,
        'server_not_configured',
        `${options.mapName} must contain valid JSON`,
      )
    }
    throw new HttpError(503, 'server_not_configured', `${options.mapName} has no default key`)
  }
  return Deno.env.get(options.singularName)?.trim() || requiredEnv(options.legacyName)
}

function integerEnv(name: string, fallback: number, minimum: number, maximum: number): number {
  const raw = Deno.env.get(name)
  if (!raw) return fallback
  const value = Number(raw)
  if (!Number.isSafeInteger(value) || value < minimum || value > maximum) {
    throw new HttpError(
      503,
      'server_not_configured',
      `${name} must be an integer between ${minimum} and ${maximum}`,
    )
  }
  return value
}

function runtimeConfig(): RuntimeConfig {
  const allowedOrigins = new Set(
    (Deno.env.get('ASSET_API_ALLOWED_ORIGINS') ?? 'http://localhost:5173,http://localhost:5174')
      .split(',')
      .map((origin) => origin.trim())
      .filter(Boolean),
  )
  return {
    maxAssetBytes: integerEnv(
      'ASSET_MAX_BYTES',
      DEFAULT_MAX_ASSET_BYTES,
      1,
      Number.MAX_SAFE_INTEGER,
    ),
    accountMaxReservedBytes: integerEnv(
      'ASSET_ACCOUNT_MAX_RESERVED_BYTES',
      20 * 1024 * MEBIBYTE,
      1,
      Number.MAX_SAFE_INTEGER,
    ),
    maxActiveUploadsPerAccount: integerEnv(
      'ASSET_MAX_ACTIVE_UPLOADS_PER_ACCOUNT',
      5,
      1,
      100,
    ),
    singleUploadLimitBytes: integerEnv(
      'ASSET_SINGLE_UPLOAD_LIMIT_BYTES',
      DEFAULT_SINGLE_UPLOAD_LIMIT_BYTES,
      5 * MEBIBYTE,
      5 * 1024 * MEBIBYTE,
    ),
    multipartPartSizeBytes: integerEnv(
      'ASSET_MULTIPART_PART_SIZE_BYTES',
      DEFAULT_MULTIPART_PART_SIZE_BYTES,
      5 * MEBIBYTE,
      5 * 1024 * MEBIBYTE,
    ),
    signedUrlTtlSeconds: integerEnv('ASSET_SIGNED_URL_TTL_SECONDS', 900, 60, 3600),
    uploadSessionTtlSeconds: integerEnv('ASSET_UPLOAD_SESSION_TTL_SECONDS', 86400, 900, 604800),
    allowedOrigins,
  }
}

let objectStoreInstance: ObjectStore | undefined

function objectStore(): ObjectStore {
  objectStoreInstance ??= new R2ObjectStore(r2ConfigFromEnv(envRecord()))
  return objectStoreInstance
}

function corsHeaders(request: Request, config: RuntimeConfig): HeadersInit {
  const origin = request.headers.get('origin')
  const allowedOrigin =
    origin && (config.allowedOrigins.has('*') || config.allowedOrigins.has(origin))
      ? (config.allowedOrigins.has('*') ? '*' : origin)
      : null
  return {
    ...(allowedOrigin ? { 'access-control-allow-origin': allowedOrigin } : {}),
    'access-control-allow-headers': 'authorization, apikey, content-type, x-client-info',
    'access-control-allow-methods': 'POST, OPTIONS',
    'access-control-max-age': '86400',
    vary: 'Origin',
  }
}

function jsonResponse(
  request: Request,
  config: RuntimeConfig,
  status: number,
  body: unknown,
  requestId: string,
): Response {
  const headers = new Headers(corsHeaders(request, config))
  headers.set('content-type', 'application/json; charset=utf-8')
  headers.set('x-request-id', requestId)
  return new Response(JSON.stringify(body), { status, headers })
}

function bearerToken(request: Request): string {
  const authorization = request.headers.get('authorization')
  const match = authorization?.match(/^Bearer\s+(.+)$/i)
  if (!match?.[1]) {
    throw new HttpError(401, 'authentication_required', 'Sign in to access cloud assets')
  }
  return match[1]
}

async function requestContext(request: Request, config: RuntimeConfig): Promise<RequestContext> {
  const token = bearerToken(request)
  const supabaseUrl = requiredEnv('SUPABASE_URL')
  const publicKey = supabaseApiKey({
    mapName: 'SUPABASE_PUBLISHABLE_KEYS',
    singularName: 'SUPABASE_PUBLISHABLE_KEY',
    legacyName: 'SUPABASE_ANON_KEY',
  })
  const serviceRoleKey = supabaseApiKey({
    mapName: 'SUPABASE_SECRET_KEYS',
    singularName: 'SUPABASE_SECRET_KEY',
    legacyName: 'SUPABASE_SERVICE_ROLE_KEY',
  })

  const userClient = createClient(supabaseUrl, publicKey, {
    global: { headers: { Authorization: `Bearer ${token}` } },
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
  })
  const { data: authData, error: authError } = await userClient.auth.getUser(token)
  if (authError || !authData.user) {
    throw new HttpError(401, 'invalid_access_token', 'The access token is invalid or expired')
  }

  const adminClient = createClient(supabaseUrl, serviceRoleKey, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
  })
  const userRepository = new SupabaseAssetRepository(userClient)
  const accountId = await userRepository.currentAccountId()

  return {
    userClient,
    userRepository,
    adminRepository: new SupabaseAssetRepository(adminClient),
    accountId,
    objectStore: objectStore(),
    config,
  }
}

async function requireProjectAccess(
  context: RequestContext,
  projectId: string,
  write: boolean,
): Promise<'owner' | 'editor' | 'viewer'> {
  const { data, error } = await context.userClient
    .from('project_members')
    .select('role')
    .eq('project_id', projectId)
    .eq('account_id', context.accountId)
    .maybeSingle()

  if (error) throw new DataAccessError('authorize-project', error.message, error)
  if (!data) throw new HttpError(404, 'project_not_found', 'Project not found')
  const role = data.role as 'owner' | 'editor' | 'viewer'
  if (write && role === 'viewer') {
    throw new HttpError(403, 'project_write_forbidden', 'Editor access is required')
  }
  return role
}

function assertConfiguredProvider(context: RequestContext, asset: AssetRecord): void {
  if (
    asset.object.provider !== context.objectStore.provider ||
    asset.object.bucket !== context.objectStore.bucket
  ) {
    throw new HttpError(
      409,
      'storage_provider_unavailable',
      `The ${asset.object.provider} storage provider is not configured on this deployment`,
    )
  }
}

async function requireAsset(
  context: RequestContext,
  assetId: string,
  write: boolean,
): Promise<{ asset: AssetRecord; session: UploadSessionRecord | null }> {
  const asset = await context.userRepository.getAsset(assetId)
  if (!asset) throw new HttpError(404, 'asset_not_found', 'Asset not found')
  if (write) await requireProjectAccess(context, asset.projectId, true)
  assertConfiguredProvider(context, asset)
  const session = await context.adminRepository.getUploadSession(assetId)
  return { asset, session }
}

function requireActiveSession(session: UploadSessionRecord | null): UploadSessionRecord {
  if (!session) throw new HttpError(409, 'upload_session_missing', 'Upload session not found')
  if (session.state !== 'uploading') {
    throw new HttpError(409, 'upload_not_active', `Upload is ${session.state}`)
  }
  if (Date.parse(session.expiresAt) <= Date.now()) {
    throw new HttpError(410, 'upload_expired', 'Upload session has expired')
  }
  return session
}

function objectMetadata(
  assetId: string,
  projectId: string,
  accountId: string,
): Record<string, string> {
  return {
    'asset-id': assetId,
    'project-id': projectId,
    'owner-account-id': accountId,
  }
}

function pendingObjectKey(asset: Pick<AssetRecord, 'id' | 'projectId'>): string {
  return `_uploads/${asset.projectId}/${asset.id}`
}

async function createUpload(
  context: RequestContext,
  request: Extract<AssetApiRequest, { action: 'create-upload' }>,
): Promise<AssetApiResponse> {
  await requireProjectAccess(context, request.projectId, true)

  const usage = await context.adminRepository.getAccountAssetUsage(context.accountId)
  if (usage.activeUploads >= context.config.maxActiveUploadsPerAccount) {
    throw new HttpError(
      429,
      'too_many_active_uploads',
      `At most ${context.config.maxActiveUploadsPerAccount} uploads may be active`,
    )
  }
  if (request.sizeBytes > context.config.accountMaxReservedBytes - usage.reservedBytes) {
    throw new HttpError(429, 'storage_quota_exceeded', 'The account storage quota is exceeded')
  }

  const assetId = crypto.randomUUID()
  const objectKey = `projects/${request.projectId}/assets/${assetId}`
  const uploadObjectKey = pendingObjectKey({ id: assetId, projectId: request.projectId })
  const mode = request.sizeBytes <= context.config.singleUploadLimitBytes ? 'single' : 'multipart'
  const metadata = objectMetadata(assetId, request.projectId, context.accountId)
  let uploadId: string | undefined
  let assetCreated = false
  let sessionCreated = false

  try {
    if (mode === 'multipart') {
      const created = await context.objectStore.createMultipartUpload({
        key: uploadObjectKey,
        contentType: request.contentType,
        metadata,
      })
      uploadId = created.uploadId
    }

    const asset = await context.adminRepository.createPendingAsset({
      id: assetId,
      projectId: request.projectId,
      ownerAccountId: context.accountId,
      provider: context.objectStore.provider,
      bucket: context.objectStore.bucket,
      objectKey,
      originalName: request.fileName,
      contentType: request.contentType,
      sizeBytes: request.sizeBytes,
      ...(request.sha256 ? { sha256: request.sha256 } : {}),
    })
    assetCreated = true

    await context.adminRepository.createUploadSession({
      assetId,
      createdBy: context.accountId,
      mode,
      ...(uploadId ? { uploadId } : {}),
      ...(mode === 'multipart' ? { partSizeBytes: context.config.multipartPartSizeBytes } : {}),
      expiresAt: expiresAtFromNow(context.config.uploadSessionTtlSeconds),
    })
    sessionCreated = true

    if (mode === 'multipart') {
      return {
        action: 'create-upload',
        assetId,
        mode,
        object: asset.object,
        partSizeBytes: context.config.multipartPartSizeBytes,
      }
    }

    const upload = await context.objectStore.createUploadUrl({
      key: uploadObjectKey,
      contentType: request.contentType,
      sizeBytes: request.sizeBytes,
      expiresInSeconds: context.config.signedUrlTtlSeconds,
      metadata,
    })
    return { action: 'create-upload', assetId, mode, object: asset.object, upload }
  } catch (error) {
    if (uploadId) {
      await context.objectStore.abortMultipartUpload({ key: uploadObjectKey, uploadId }).catch(() =>
        undefined
      )
    }
    if (sessionCreated) {
      await context.adminRepository.markUploadState(assetId, 'failed').catch(() => undefined)
    }
    if (assetCreated) {
      await context.adminRepository.markAssetFailed(assetId, errorMessage(error)).catch(() =>
        undefined
      )
    }
    throw error
  }
}

async function signParts(
  context: RequestContext,
  request: Extract<AssetApiRequest, { action: 'sign-parts' }>,
): Promise<AssetApiResponse> {
  const { asset, session: rawSession } = await requireAsset(context, request.assetId, true)
  const session = requireActiveSession(rawSession)
  if (session.mode !== 'multipart' || !session.uploadId || !session.partSizeBytes) {
    throw new HttpError(409, 'not_multipart_upload', 'This asset does not use multipart upload')
  }
  const partCount = Math.ceil(asset.sizeBytes / session.partSizeBytes)
  if (request.partNumbers.some((partNumber) => partNumber > partCount)) {
    throw new HttpError(400, 'invalid_part_number', `This upload has ${partCount} parts`)
  }

  const parts = await Promise.all(
    request.partNumbers.map(async (partNumber) => ({
      partNumber,
      upload: await context.objectStore.createPartUploadUrl({
        key: pendingObjectKey(asset),
        uploadId: session.uploadId as string,
        partNumber,
        expiresInSeconds: context.config.signedUrlTtlSeconds,
      }),
    })),
  )
  return { action: 'sign-parts', assetId: asset.id, parts }
}

function validateCompletedParts(
  asset: AssetRecord,
  session: UploadSessionRecord,
  parts?: CompletedPart[],
): CompletedPart[] {
  if (session.mode === 'single') {
    if (parts?.length) {
      throw new HttpError(400, 'unexpected_parts', 'Single uploads do not have parts')
    }
    return []
  }
  if (!session.partSizeBytes) {
    throw new HttpError(409, 'invalid_upload_session', 'Part size is missing')
  }
  const expectedCount = Math.ceil(asset.sizeBytes / session.partSizeBytes)
  if (!parts || parts.length !== expectedCount) {
    throw new HttpError(400, 'incomplete_parts', `Expected ${expectedCount} completed parts`)
  }
  for (let index = 0; index < parts.length; index += 1) {
    if (parts[index]?.partNumber !== index + 1) {
      throw new HttpError(
        400,
        'incomplete_parts',
        'Completed parts must be consecutive and start at 1',
      )
    }
  }
  return parts
}

function isNotFoundError(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false
  const record = error as { name?: unknown; $metadata?: { httpStatusCode?: unknown } }
  return record.name === 'NotFound' ||
    record.name === 'NoSuchKey' ||
    record.$metadata?.httpStatusCode === 404
}

async function optionalHead(store: ObjectStore, key: string): Promise<StoredObjectMetadata | null> {
  try {
    return await store.headObject(key)
  } catch (error) {
    if (isNotFoundError(error)) return null
    throw error
  }
}

async function failInvalidObject(
  context: RequestContext,
  asset: AssetRecord,
  message: string,
): Promise<never> {
  await Promise.all(
    [pendingObjectKey(asset), asset.object.key].map((key) =>
      context.objectStore.deleteObject(key).catch(() => undefined)
    ),
  )
  await context.adminRepository.markUploadState(asset.id, 'failed').catch(() => undefined)
  await context.adminRepository.markAssetFailed(asset.id, message).catch(() => undefined)
  throw new HttpError(422, 'uploaded_object_invalid', message)
}

async function completeUpload(
  context: RequestContext,
  request: Extract<AssetApiRequest, { action: 'complete-upload' }>,
): Promise<AssetApiResponse> {
  const { asset, session: rawSession } = await requireAsset(context, request.assetId, true)
  if (asset.status === 'ready') {
    await context.adminRepository.markUploadState(asset.id, 'completed').catch(() => undefined)
    await context.objectStore.deleteObject(pendingObjectKey(asset)).catch(() => undefined)
    return { action: 'complete-upload', asset }
  }
  if (asset.status === 'failed' || asset.status === 'deleted') {
    throw new HttpError(409, 'asset_not_uploadable', `Asset is ${asset.status}`)
  }

  const session = requireActiveSession(rawSession)
  const parts = validateCompletedParts(asset, session, request.parts)
  const uploadObjectKey = pendingObjectKey(asset)
  let storedObject = await optionalHead(context.objectStore, uploadObjectKey)

  if (!storedObject && session.mode === 'multipart') {
    if (!session.uploadId) {
      throw new HttpError(409, 'invalid_upload_session', 'Upload ID is missing')
    }
    await context.objectStore.completeMultipartUpload({
      key: uploadObjectKey,
      uploadId: session.uploadId,
      parts,
    })
    storedObject = await context.objectStore.headObject(uploadObjectKey)
  }

  if (!storedObject) {
    throw new HttpError(409, 'object_not_uploaded', 'The object has not been uploaded yet')
  }
  if (storedObject.metadata['asset-id'] !== asset.id) {
    return failInvalidObject(context, asset, 'Uploaded object metadata does not match the asset')
  }
  if (storedObject.sizeBytes !== asset.sizeBytes) {
    return failInvalidObject(
      context,
      asset,
      `Uploaded object size is ${storedObject.sizeBytes}; expected ${asset.sizeBytes}`,
    )
  }
  if (
    storedObject.contentType &&
    storedObject.contentType.toLowerCase() !== asset.contentType.toLowerCase()
  ) {
    return failInvalidObject(
      context,
      asset,
      'Uploaded object content type does not match the asset',
    )
  }

  await context.objectStore.copyObject({
    sourceKey: uploadObjectKey,
    destinationKey: asset.object.key,
  })
  const finalObject = await context.objectStore.headObject(asset.object.key)
  if (
    finalObject.metadata['asset-id'] !== asset.id ||
    finalObject.sizeBytes !== asset.sizeBytes ||
    (finalObject.contentType &&
      finalObject.contentType.toLowerCase() !== asset.contentType.toLowerCase())
  ) {
    return failInvalidObject(context, asset, 'Promoted object does not match the uploaded asset')
  }

  const readyAsset = await context.adminRepository.markAssetReady(asset.id, {
    sizeBytes: finalObject.sizeBytes,
    contentType: finalObject.contentType ?? asset.contentType,
    etag: finalObject.etag,
    versionId: finalObject.versionId,
  })
  await context.adminRepository.markUploadState(asset.id, 'completed')
  await context.objectStore.deleteObject(uploadObjectKey).catch(() => undefined)
  return { action: 'complete-upload', asset: readyAsset }
}

async function abortUpload(
  context: RequestContext,
  request: Extract<AssetApiRequest, { action: 'abort-upload' }>,
): Promise<AssetApiResponse> {
  const { asset, session } = await requireAsset(context, request.assetId, true)
  if (asset.status === 'ready') {
    throw new HttpError(409, 'asset_already_ready', 'A completed asset cannot be aborted')
  }

  if (session?.mode === 'multipart' && session.uploadId && session.state === 'uploading') {
    await context.objectStore.abortMultipartUpload({
      key: pendingObjectKey(asset),
      uploadId: session.uploadId,
    })
  } else {
    await context.objectStore.deleteObject(pendingObjectKey(asset))
  }
  if (session) await context.adminRepository.markUploadState(asset.id, 'aborted')
  await context.adminRepository.markAssetFailed(asset.id, 'Upload aborted by the user')
  return { action: 'abort-upload', assetId: asset.id, status: 'failed' }
}

async function createDownload(
  context: RequestContext,
  request: Extract<AssetApiRequest, { action: 'create-download' }>,
): Promise<AssetApiResponse> {
  const { asset } = await requireAsset(context, request.assetId, false)
  if (asset.status !== 'ready') {
    throw new HttpError(409, 'asset_not_ready', `Asset is ${asset.status}`)
  }
  const download = await context.objectStore.createDownloadUrl({
    key: asset.object.key,
    expiresInSeconds: context.config.signedUrlTtlSeconds,
    fileName: asset.originalName,
    disposition: request.disposition ?? 'inline',
  })
  return { action: 'create-download', assetId: asset.id, download }
}

async function dispatch(
  context: RequestContext,
  request: AssetApiRequest,
): Promise<AssetApiResponse> {
  switch (request.action) {
    case 'create-upload':
      return createUpload(context, request)
    case 'sign-parts':
      return signParts(context, request)
    case 'complete-upload':
      return completeUpload(context, request)
    case 'abort-upload':
      return abortUpload(context, request)
    case 'create-download':
      return createDownload(context, request)
  }
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Unknown error'
}

function publicError(error: unknown): { status: number; code: string; message: string } {
  if (error instanceof HttpError) {
    return { status: error.status, code: error.code, message: error.message }
  }
  if (error instanceof ContractError) {
    return { status: 400, code: 'invalid_request', message: error.message }
  }
  if (error instanceof ObjectStoreConfigurationError) {
    return { status: 503, code: 'object_store_not_configured', message: error.message }
  }
  if (error instanceof DataAccessError && error.operation === 'current-account') {
    return { status: 403, code: 'account_not_linked', message: error.message }
  }
  return { status: 500, code: 'internal_error', message: 'The cloud asset request failed' }
}

Deno.serve(async (request) => {
  const requestId = crypto.randomUUID()
  let config: RuntimeConfig
  try {
    config = runtimeConfig()
  } catch (error) {
    const fallbackConfig: RuntimeConfig = {
      maxAssetBytes: DEFAULT_MAX_ASSET_BYTES,
      accountMaxReservedBytes: 20 * 1024 * MEBIBYTE,
      maxActiveUploadsPerAccount: 5,
      singleUploadLimitBytes: DEFAULT_SINGLE_UPLOAD_LIMIT_BYTES,
      multipartPartSizeBytes: DEFAULT_MULTIPART_PART_SIZE_BYTES,
      signedUrlTtlSeconds: 900,
      uploadSessionTtlSeconds: 86400,
      allowedOrigins: new Set(),
    }
    const responseError = publicError(error)
    return jsonResponse(
      request,
      fallbackConfig,
      responseError.status,
      { error: responseError },
      requestId,
    )
  }

  const origin = request.headers.get('origin')
  if (origin && !config.allowedOrigins.has('*') && !config.allowedOrigins.has(origin)) {
    return jsonResponse(
      request,
      config,
      403,
      { error: { code: 'origin_forbidden', message: 'This origin is not allowed' } },
      requestId,
    )
  }
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders(request, config) })
  }
  if (request.method !== 'POST') {
    return jsonResponse(
      request,
      config,
      405,
      { error: { code: 'method_not_allowed', message: 'Use POST for this endpoint' } },
      requestId,
    )
  }

  try {
    const body: unknown = await request.json().catch(() => {
      throw new HttpError(400, 'invalid_json', 'Request body must be valid JSON')
    })
    const parsed = parseAssetApiRequest(body, { maxAssetBytes: config.maxAssetBytes })
    const context = await requestContext(request, config)
    const response = await dispatch(context, parsed)
    return jsonResponse(request, config, 200, response, requestId)
  } catch (error) {
    const responseError = publicError(error)
    if (responseError.status >= 500) {
      console.error(JSON.stringify({ requestId, error: errorMessage(error) }))
    }
    return jsonResponse(request, config, responseError.status, { error: responseError }, requestId)
  }
})
