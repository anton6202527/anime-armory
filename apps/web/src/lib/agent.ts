import type { CreateSkillRunRequest } from "@anime-armory/contracts";
import type { AgentArtifact, AgentJob, AgentJobState, WebWork, WorkCreationConfig } from "../types";
import { apiJson } from "./api";
import { discoverCanvasModels } from "./generation";
import { localFile } from "./localFiles";

const HEALTH_TIMEOUT_MS = 5_000;
const SMALL_RESPONSE_LIMIT_BYTES = 256 * 1024;

type SkillDefinitionInput = NonNullable<WorkCreationConfig["skillDefinition"]>;

export interface SubmitAgentJobInput {
  work: WebWork;
  prompt: string;
  /** The currently selected Skill. Falls back to work.creationConfig.skillId. */
  skillId?: string;
  skillDefinition?: SkillDefinitionInput;
  context?: Record<string, unknown>;
  /** Supply this only when deliberately retrying the same user submission. */
  idempotencyKey?: string;
}

export interface AgentGateway {
  readonly mode: "backend" | "demo";
  readonly label: string;
  submit(input: SubmitAgentJobInput): Promise<AgentJob>;
  status?(jobId: string): Promise<AgentJob>;
}

type ReadyHealth = {
  service?: unknown;
  status?: unknown;
  provider?: { id?: unknown; status?: unknown };
  capabilities?: { skillRuns?: unknown };
};

function record(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function unwrap(value: unknown, property?: string): unknown {
  const outer = record(value);
  if (!outer) return value;
  if (property && outer[property] !== undefined) return outer[property];
  const data = record(outer.data);
  if (property && data?.[property] !== undefined) return data[property];
  return outer.data ?? value;
}

function validState(value: unknown): value is AgentJobState {
  return value === "queued" || value === "running" || value === "succeeded"
    || value === "failed" || value === "cancelled";
}

function normalizeArtifacts(value: unknown): AgentArtifact[] | undefined {
  if (!Array.isArray(value)) return undefined;
  return value.flatMap((item) => {
    const artifact = record(item);
    if (!artifact || typeof artifact.id !== "string" || typeof artifact.name !== "string"
      || (artifact.kind !== "text" && artifact.kind !== "image" && artifact.kind !== "video" && artifact.kind !== "audio")) {
      return [];
    }
    return [{
      id: artifact.id,
      kind: artifact.kind,
      name: artifact.name,
      ...(typeof artifact.mimeType === "string" ? { mimeType: artifact.mimeType } : {}),
      ...(typeof artifact.size === "number" && Number.isFinite(artifact.size) ? { size: artifact.size } : {}),
      ...(typeof artifact.text === "string" ? { text: artifact.text } : {}),
      ...(typeof artifact.url === "string" ? { url: artifact.url } : {}),
      ...(typeof artifact.base64 === "string" ? { base64: artifact.base64 } : {}),
      ...(typeof artifact.assetId === "string" ? { assetId: artifact.assetId } : {}),
    } satisfies AgentArtifact];
  });
}

function normalizeJob(value: unknown): AgentJob {
  const job = record(unwrap(value, "run"));
  if (!job || typeof job.id !== "string" || !job.id || !validState(job.state)) {
    throw new Error("后端返回的 Skill 任务格式无效");
  }
  const artifacts = normalizeArtifacts(job.artifacts);
  return {
    id: job.id,
    state: job.state,
    message: typeof job.message === "string" ? job.message : "Skill 任务已提交",
    ...(typeof job.estimatedTokens === "number" && Number.isFinite(job.estimatedTokens)
      ? { estimatedTokens: job.estimatedTokens }
      : {}),
    ...(typeof job.agentId === "string" ? { agentId: job.agentId } : {}),
    ...(typeof job.output === "string" ? { output: job.output } : {}),
    ...(artifacts ? { artifacts } : {}),
  };
}

async function probeBackend(): Promise<ReadyHealth | null> {
  try {
    const value = await apiJson<unknown>("/v1/health/ready", {
      method: "GET",
      timeoutMs: HEALTH_TIMEOUT_MS,
      maxResponseBytes: SMALL_RESPONSE_LIMIT_BYTES,
    });
    const health = unwrap(value) as ReadyHealth;
    return health?.service === "anime-armory-backend"
      && health.status === "ready"
      && health.provider?.status === "ready"
      && health.capabilities?.skillRuns === true
      ? health
      : null;
  } catch {
    return null;
  }
}

class BackendAgentGateway implements AgentGateway {
  readonly mode = "backend" as const;
  readonly label: string;

  constructor(health: ReadyHealth) {
    const provider = typeof health.provider?.id === "string" ? health.provider.id : "AI";
    this.label = `后端 · ${provider}`;
  }

  private async uploadLocalSources(work: WebWork): Promise<void> {
    for (const attachment of work.attachments) {
      if (attachment.assetId) continue;
      const file = await localFile(attachment.id);
      if (!file) continue;
      await apiJson<unknown>(
        `/v1/works/${encodeURIComponent(work.id)}/files/${encodeURIComponent(attachment.id)}`,
        {
          method: "PUT",
          headers: {
            "content-type": file.type || "application/octet-stream",
          },
          body: file,
          timeoutMs: 180_000,
          maxResponseBytes: SMALL_RESPONSE_LIMIT_BYTES,
        },
      );
    }
  }

  async submit(input: SubmitAgentJobInput): Promise<AgentJob> {
    const prompt = input.prompt.trim();
    if (!prompt) throw new Error("请输入任务要求后再提交");
    const skillId = input.skillId?.trim()
      || input.work.creationConfig?.skillId?.trim()
      || input.work.line;
    const skillDefinition = input.skillDefinition ?? input.work.creationConfig?.skillDefinition;
    const model = input.work.creationConfig?.model;
    let modelPreference: string | undefined;
    if (model?.modality === "text" && model.modelId) {
      const discoveredModels = await discoverCanvasModels();
      const selectedModel = discoveredModels.find((candidate) => candidate.modality === "text" && candidate.id === model.modelId);
      if (!selectedModel) {
        throw new Error(`所选文本模型 ${model.modelId} 未由后端 discovery 开放，请重新选择 GPT 模型`);
      }
      modelPreference = selectedModel.id;
    }
    const attachments = input.work.attachments.map((attachment) => ({
      id: attachment.id,
      name: attachment.name,
      ...(attachment.type ? { mimeType: attachment.type } : {}),
      ...(attachment.assetId ? { assetId: attachment.assetId } : {}),
    }));

    await this.uploadLocalSources(input.work);
    const request = {
      skillId,
      workId: input.work.id,
      projectId: input.work.cloudProjectId ?? input.work.id,
      workName: input.work.name,
      line: input.work.line,
      prompt,
      generationMode: input.work.creationConfig?.generationMode ?? "auto",
      idempotencyKey: input.idempotencyKey ?? `${input.work.id}:${crypto.randomUUID()}`,
      ...(modelPreference ? { modelPreference } : {}),
      ...(attachments.length ? { attachments } : {}),
      ...(skillDefinition ? { skillDefinition } : {}),
      context: {
        ...(input.context ?? {}),
        work: {
          id: input.work.id,
          projectId: input.work.cloudProjectId ?? input.work.id,
          name: input.work.name,
          line: input.work.line,
          createdAt: input.work.createdAt,
        },
        ...(model ? { model } : {}),
        attachmentIds: input.work.attachments.map((attachment) => attachment.assetId ?? attachment.id),
      },
    } satisfies CreateSkillRunRequest;
    const value = await apiJson<unknown>("/v1/skill-runs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      timeoutMs: 30_000,
      maxResponseBytes: SMALL_RESPONSE_LIMIT_BYTES,
      body: JSON.stringify(request),
    });
    return normalizeJob(value);
  }

  async status(jobId: string): Promise<AgentJob> {
    if (!jobId.trim()) throw new Error("Skill 任务 ID 无效");
    const value = await apiJson<unknown>(`/v1/skill-runs/${encodeURIComponent(jobId)}`, {
      method: "GET",
      timeoutMs: 15_000,
      maxResponseBytes: 32 * 1024 * 1024,
    });
    return normalizeJob(value);
  }
}

class DemoAgentGateway implements AgentGateway {
  readonly mode = "demo" as const;
  readonly label = "后端未就绪";

  async submit(): Promise<AgentJob> {
    return {
      id: crypto.randomUUID(),
      state: "failed",
      message: "LabuTV 后端或 cliproxy 尚未就绪，任务未提交。请启动本地后端后重试。",
      estimatedTokens: 0,
    };
  }
}

export async function createAgentGateway(): Promise<AgentGateway> {
  const health = await probeBackend();
  return health ? new BackendAgentGateway(health) : new DemoAgentGateway();
}
