export type AiModality = 'text' | 'image'

export interface AiModel {
  id: string
  label: string
  modality: AiModality
  provider: 'cliproxy'
}

export interface AiGenerationRequest {
  modality: AiModality
  model: string
  prompt: string
  aspectRatio?: '1:1' | '2:1' | '3:2' | '2:3' | '4:3' | '3:4' | '16:9' | '9:16'
  quality?: 'standard' | 'high'
  image?: {
    base64: string
    mimeType: 'image/png' | 'image/jpeg' | 'image/webp' | 'image/gif'
  }
}

export type AiGenerationResponse =
  | { modality: 'text'; model: string; text: string }
  | {
      modality: 'image'
      model: string
      image: {
        base64: string
        mimeType: 'image/png' | 'image/jpeg' | 'image/webp' | 'image/gif'
        revisedPrompt?: string
      }
    }

export type CreationLine = 'novel' | 'n2d' | 'comic' | 'ad' | 'mv' | 'song'

export interface SkillDefinitionInput {
  title: string
  description: string
  guide: string
  steps: string[]
  useCases: string[]
}

export interface SkillRunAttachmentInput {
  id: string
  name: string
  mimeType?: string
  assetId?: string
}

export interface CreateSkillRunRequest {
  skillId: string
  workId: string
  projectId?: string
  workName: string
  line: CreationLine
  prompt: string
  generationMode: 'manual' | 'auto'
  idempotencyKey: string
  modelPreference?: string
  attachments?: SkillRunAttachmentInput[]
  skillDefinition?: SkillDefinitionInput
  context?: Record<string, unknown>
}

export type SkillRunState = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'
export type SkillArtifactKind = 'text' | 'image' | 'video' | 'audio'

export interface SkillRunArtifact {
  id: string
  kind: SkillArtifactKind
  name: string
  mimeType?: string
  size?: number
  text?: string
  url?: string
  base64?: string
  assetId?: string
}

export interface SkillRun {
  id: string
  skillId: string
  state: SkillRunState
  message: string
  createdAt: string
  startedAt?: string
  finishedAt?: string
  model?: string
  output?: string
  artifacts?: SkillRunArtifact[]
}

export interface ApiErrorEnvelope {
  error: {
    code: string
    message: string
    requestId: string
  }
}

export interface ReadyHealthResponse {
  service: 'anime-armory-backend'
  version: number
  status: 'ready' | 'degraded'
  provider: {
    id: 'cliproxy'
    status: 'ready' | 'unavailable'
    modelCount: number
  }
  capabilities: {
    aiGeneration: true
    skillRuns: true
    skillRegistry: true
  }
}
