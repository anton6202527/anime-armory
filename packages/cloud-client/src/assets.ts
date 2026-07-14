import type {
  AbortUploadResponse,
  AssetApiRequest,
  AssetApiResponse,
  AssetRecord,
  CompleteUploadResponse,
  CompletedPart,
  CreateDownloadResponse,
  CreateUploadResponse,
  SignPartsResponse,
  SignedRequest,
} from '@anime-armory/contracts'

export interface AssetUploadSource {
  readonly name: string
  readonly type: string
  readonly size: number
  slice(start?: number, end?: number, contentType?: string): Blob
}

export interface AssetApiClientOptions {
  endpoint: string
  getAccessToken: () => Promise<string | null>
  fetch?: typeof globalThis.fetch
  multipartConcurrency?: number
  signedPartBatchSize?: number
}

export interface UploadAssetOptions {
  projectId: string
  source: AssetUploadSource
  sha256?: string
  signal?: AbortSignal
  onProgress?: (uploadedBytes: number, totalBytes: number) => void
}

export class CloudApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(message: string, options: { status?: number; code?: string } = {}) {
    super(message)
    this.name = 'CloudApiError'
    this.status = options.status ?? 0
    this.code = options.code ?? 'cloud_api_error'
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function errorFromPayload(payload: unknown, status: number): CloudApiError {
  if (isRecord(payload) && isRecord(payload.error)) {
    const message = typeof payload.error.message === 'string' ? payload.error.message : 'Cloud request failed'
    const code = typeof payload.error.code === 'string' ? payload.error.code : 'cloud_api_error'
    return new CloudApiError(message, { status, code })
  }
  return new CloudApiError(`Cloud request failed with HTTP ${status}`, { status })
}

function assertResponseAction<T extends AssetApiResponse['action']>(
  response: AssetApiResponse,
  action: T,
): Extract<AssetApiResponse, { action: T }> {
  if (response.action !== action) {
    throw new CloudApiError(`Expected ${action} response, received ${response.action}`, {
      code: 'invalid_response',
    })
  }
  return response as Extract<AssetApiResponse, { action: T }>
}

async function uploadSignedPart(
  fetcher: typeof globalThis.fetch,
  upload: SignedRequest,
  body: Blob,
  signal?: AbortSignal,
): Promise<string> {
  const response = await fetcher(upload.url, {
    method: upload.method,
    headers: upload.headers,
    body,
    ...(signal ? { signal } : {}),
  })
  if (!response.ok) {
    throw new CloudApiError(`Object upload failed with HTTP ${response.status}`, {
      status: response.status,
      code: 'object_upload_failed',
    })
  }
  const etag = response.headers.get('etag')
  if (!etag) {
    throw new CloudApiError('Object storage did not expose an ETag response header', {
      code: 'missing_etag',
    })
  }
  return etag
}

export class AssetApiClient {
  private readonly endpoint: string
  private readonly getAccessToken: () => Promise<string | null>
  private readonly fetcher: typeof globalThis.fetch
  private readonly multipartConcurrency: number
  private readonly signedPartBatchSize: number

  constructor(options: AssetApiClientOptions) {
    this.endpoint = options.endpoint.replace(/\/+$/, '')
    if (!this.endpoint) throw new CloudApiError('Asset API endpoint is required', { code: 'invalid_config' })
    this.getAccessToken = options.getAccessToken
    this.fetcher = options.fetch ?? globalThis.fetch
    this.multipartConcurrency = Math.max(1, Math.min(options.multipartConcurrency ?? 3, 8))
    this.signedPartBatchSize = Math.max(1, Math.min(options.signedPartBatchSize ?? 50, 100))
  }

  private async request(request: AssetApiRequest, signal?: AbortSignal): Promise<AssetApiResponse> {
    const accessToken = await this.getAccessToken()
    if (!accessToken) {
      throw new CloudApiError('Sign in before accessing cloud assets', {
        status: 401,
        code: 'authentication_required',
      })
    }
    const response = await this.fetcher(this.endpoint, {
      method: 'POST',
      headers: {
        authorization: `Bearer ${accessToken}`,
        'content-type': 'application/json',
      },
      body: JSON.stringify(request),
      ...(signal ? { signal } : {}),
    })
    const payload: unknown = await response.json().catch(() => null)
    if (!response.ok) throw errorFromPayload(payload, response.status)
    if (!isRecord(payload) || typeof payload.action !== 'string') {
      throw new CloudApiError('Cloud API returned an invalid response', { code: 'invalid_response' })
    }
    return payload as unknown as AssetApiResponse
  }

  async createUpload(
    projectId: string,
    source: AssetUploadSource,
    options: { sha256?: string; signal?: AbortSignal } = {},
  ): Promise<CreateUploadResponse> {
    const response = await this.request(
      {
        action: 'create-upload',
        projectId,
        fileName: source.name,
        contentType: source.type || 'application/octet-stream',
        sizeBytes: source.size,
        ...(options.sha256 ? { sha256: options.sha256 } : {}),
      },
      options.signal,
    )
    return assertResponseAction(response, 'create-upload')
  }

  async completeUpload(
    assetId: string,
    parts?: CompletedPart[],
    signal?: AbortSignal,
  ): Promise<CompleteUploadResponse> {
    const response = await this.request(
      {
        action: 'complete-upload',
        assetId,
        ...(parts ? { parts } : {}),
      },
      signal,
    )
    return assertResponseAction(response, 'complete-upload')
  }

  async abortUpload(assetId: string): Promise<AbortUploadResponse> {
    const response = await this.request({ action: 'abort-upload', assetId })
    return assertResponseAction(response, 'abort-upload')
  }

  async createDownloadUrl(
    assetId: string,
    disposition: 'inline' | 'attachment' = 'inline',
    signal?: AbortSignal,
  ): Promise<CreateDownloadResponse> {
    const response = await this.request(
      { action: 'create-download', assetId, disposition },
      signal,
    )
    return assertResponseAction(response, 'create-download')
  }

  private async signParts(
    assetId: string,
    partNumbers: number[],
    signal?: AbortSignal,
  ): Promise<SignPartsResponse> {
    const response = await this.request({ action: 'sign-parts', assetId, partNumbers }, signal)
    return assertResponseAction(response, 'sign-parts')
  }

  async uploadAsset(options: UploadAssetOptions): Promise<AssetRecord> {
    const { projectId, source, signal, onProgress } = options
    onProgress?.(0, source.size)
    const created = await this.createUpload(projectId, source, {
      ...(options.sha256 ? { sha256: options.sha256 } : {}),
      ...(signal ? { signal } : {}),
    })

    try {
      if (created.mode === 'single') {
        if (!created.upload) {
          throw new CloudApiError('Single upload response is missing its signed request', {
            code: 'invalid_response',
          })
        }
        await uploadSignedPart(
          this.fetcher,
          created.upload,
          source.slice(0, source.size, source.type),
          signal,
        )
        onProgress?.(source.size, source.size)
        return (await this.completeUpload(created.assetId, undefined, signal)).asset
      }

      const partSize = created.partSizeBytes
      if (!partSize || partSize <= 0) {
        throw new CloudApiError('Multipart response is missing partSizeBytes', {
          code: 'invalid_response',
        })
      }
      const partCount = Math.ceil(source.size / partSize)
      const completed: CompletedPart[] = []
      let uploadedBytes = 0

      for (let batchStart = 1; batchStart <= partCount; batchStart += this.signedPartBatchSize) {
        const batchEnd = Math.min(partCount, batchStart + this.signedPartBatchSize - 1)
        const partNumbers = Array.from(
          { length: batchEnd - batchStart + 1 },
          (_, index) => batchStart + index,
        )
        const signed = await this.signParts(created.assetId, partNumbers, signal)

        for (let offset = 0; offset < signed.parts.length; offset += this.multipartConcurrency) {
          const group = signed.parts.slice(offset, offset + this.multipartConcurrency)
          const results = await Promise.all(
            group.map(async ({ partNumber, upload }) => {
              const start = (partNumber - 1) * partSize
              const end = Math.min(source.size, start + partSize)
              const etag = await uploadSignedPart(
                this.fetcher,
                upload,
                source.slice(start, end, source.type),
                signal,
              )
              return { partNumber, etag, bytes: end - start }
            }),
          )
          for (const result of results) {
            completed.push({ partNumber: result.partNumber, etag: result.etag })
            uploadedBytes += result.bytes
          }
          onProgress?.(uploadedBytes, source.size)
        }
      }

      completed.sort((left, right) => left.partNumber - right.partNumber)
      return (await this.completeUpload(created.assetId, completed, signal)).asset
    } catch (error) {
      await this.abortUpload(created.assetId).catch(() => undefined)
      throw error
    }
  }
}
