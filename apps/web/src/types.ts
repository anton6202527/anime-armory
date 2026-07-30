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

export interface CanvasNodeSnapshot {
  id: string;
  type?: string;
  position: { x: number; y: number };
  data: Record<string, unknown>;
}

export interface CanvasEdgeSnapshot {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string | null;
  targetHandle?: string | null;
  type?: string;
  animated?: boolean;
}

export interface CanvasActivitySnapshot {
  id: string;
  label: string;
  time: string;
}

export interface CanvasRunSnapshot {
  id: string;
  prompt: string;
  state: AgentJobState;
  message: string;
  output?: string;
  time: string;
}

export interface CanvasDocument {
  schemaVersion: 1;
  work: WebWork;
  nodes: CanvasNodeSnapshot[];
  edges: CanvasEdgeSnapshot[];
  viewport: { x: number; y: number; zoom: number };
  preferences: {
    view: "workflow" | "storyboard";
    gridVisible: boolean;
    snapToGrid?: boolean;
    edgesVisible: boolean;
    miniMapVisible: boolean;
    panelOpen: boolean;
    includeCanvasContext: boolean;
    followLatestRun: boolean;
  };
  activeSkill: string | null;
  activity: CanvasActivitySnapshot[];
  runHistory: CanvasRunSnapshot[];
  updatedAt: string;
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
