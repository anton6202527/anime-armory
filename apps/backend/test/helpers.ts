import type { AddressInfo } from 'node:net'
import type { Server } from 'node:http'

import type { AiProvider } from '../src/ai-provider.ts'
import type { SupabaseAuthService } from '../src/auth.ts'
import type { BackendConfig } from '../src/config.ts'
import type { AiGenerationRequest, AiGenerationResponse, AiModel } from '../src/contracts.ts'
import { createBackendServer } from '../src/server.ts'
import { SkillRegistry } from '../src/skill-registry.ts'

export class FakeProvider implements AiProvider {
  readonly id = 'cliproxy' as const
  readonly requests: AiGenerationRequest[] = []

  constructor(
    readonly models: AiModel[] = [
      { id: 'gpt-5.6-terra', label: 'gpt-5.6-terra', modality: 'text', provider: 'cliproxy' },
      { id: 'gpt-image-2', label: 'gpt-image-2', modality: 'image', provider: 'cliproxy' },
    ],
    private readonly response: AiGenerationResponse = {
      modality: 'text',
      model: 'gpt-5.6-terra',
      text: 'fake backend result',
    },
  ) {}

  async listModels(_forceRefresh?: boolean, signal?: AbortSignal): Promise<AiModel[]> {
    if (signal?.aborted) throw new DOMException('aborted', 'AbortError')
    return this.models.map((model) => ({ ...model }))
  }

  async generate(request: AiGenerationRequest, signal?: AbortSignal): Promise<AiGenerationResponse> {
    if (signal?.aborted) throw new DOMException('aborted', 'AbortError')
    this.requests.push(request)
    return structuredClone(this.response)
  }
}

export function testConfig(skillsRoot: string, runtimeRoot: string): BackendConfig {
  return {
    host: '127.0.0.1',
    port: 43_118,
    allowedOrigins: new Set(['http://127.0.0.1:4174']),
    skillsRoot,
    runtimeRoot,
    maxBodyBytes: 2 * 1024 * 1024,
    maxUploadBytes: 1024 * 1024,
    maxConcurrentGenerations: 3,
    maxRequestsPerMinute: 1_000,
  }
}

export async function listenTestServer(
  config: BackendConfig,
  provider: AiProvider,
  auth?: SupabaseAuthService,
): Promise<{ server: Server; baseUrl: string }> {
  const server = createBackendServer({
    config,
    provider,
    registry: new SkillRegistry(config.skillsRoot),
    ...(auth ? { auth } : {}),
  })
  await new Promise<void>((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', () => resolve())
  })
  const address = server.address() as AddressInfo
  return { server, baseUrl: `http://127.0.0.1:${address.port}` }
}

export async function closeTestServer(server: Server): Promise<void> {
  server.closeAllConnections()
  await new Promise<void>((resolve, reject) => server.close((error) => error ? reject(error) : resolve()))
}
