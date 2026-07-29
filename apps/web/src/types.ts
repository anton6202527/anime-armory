export type CreationLine = "novel" | "n2d" | "comic" | "ad" | "mv" | "song";

export type CreationModality = "text" | "image" | "video" | "audio";

export interface WorkCreationConfig {
  skillId?: string;
  skillDefinition?: {
    title: string;
    description: string;
    guide: string;
    steps: string[];
    useCases: string[];
  };
  generationMode: "manual" | "auto";
  model: {
    modality: CreationModality;
    modelId: string;
  };
}

export interface DraftAttachment {
  id: string;
  name: string;
  size: number;
  type: string;
  assetId?: string;
}

export interface PendingAttachment extends DraftAttachment {
  file: File;
}

export type CloudWorkState = "local" | "syncing" | "synced" | "auth-required" | "failed";

export interface WebWork {
  id: string;
  name: string;
  line: CreationLine;
  prompt: string;
  creationConfig?: WorkCreationConfig;
  attachments: DraftAttachment[];
  createdAt: string;
  cloudProjectId?: string;
  cloudState: CloudWorkState;
  cloudError?: string;
}

export type AgentJobState = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export interface AgentJob {
  id: string;
  state: AgentJobState;
  message: string;
  estimatedTokens?: number;
  agentId?: string;
  output?: string;
  workDir?: string;
}
