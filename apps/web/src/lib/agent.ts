import type { CreateSkillRunRequest } from "@anime-armory/contracts";
import type { LocalCodexModelDescriptor } from "../catalog/runtimeModels";
import type { AgentArtifact, AgentJob, AgentJobState, WebWork, WorkCreationConfig, WorkExecutor } from "../types";
import { apiJson } from "./api";
import { discoverCanvasModels } from "./generation";
import { localFile } from "./localFiles";

const HEALTH_TIMEOUT_MS = 5_000;
const LOCAL_CODEX_PROBE_TIMEOUT_MS = 15_000;
const SMALL_RESPONSE_LIMIT_BYTES = 256 * 1024;
const LOCAL_BRIDGE_URL = "http://127.0.0.1:43117/v1";

const localAgentTokens = new Map<string, string>();

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
  readonly mode: "backend" | "local" | "demo";
  readonly label: string;
  submit(input: SubmitAgentJobInput): Promise<AgentJob>;
  status?(jobId: string): Promise<AgentJob>;
}

export interface LocalCodexStatus {
  service: "anime-armory-local-bridge";
  version: number;
  codexName: string;
  models: LocalCodexModelDescriptor[];
}

type ReadyHealth = {
  service?: unknown;
  status?: unknown;
  provider?: { id?: unknown; status?: unknown };
  capabilities?: { skillRuns?: unknown };
};

type LocalBridgeStatus = {
  service?: unknown;
  version?: unknown;
  capabilities?: { localAgentJobs?: unknown };
  agents?: unknown;
  codexModels?: unknown;
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

async function localResponseJson<T>(response: Response): Promise<T> {
  const value: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const outer = record(value);
    const error = record(outer?.error);
    const message = typeof error?.message === "string"
      ? error.message
      : response.status === 403
        ? "桌面端未授权本次本机 Codex 调用"
        : `本地 Codex 请求失败（${response.status}）`;
    throw new Error(message);
  }
  return value as T;
}

/** Read-only probe. It never triggers the native authorization dialog. */
export async function probeLocalCodex(signal?: AbortSignal): Promise<LocalCodexStatus | null> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  signal?.addEventListener("abort", abort, { once: true });
  const timer = window.setTimeout(abort, LOCAL_CODEX_PROBE_TIMEOUT_MS);
  try {
    const value = await localResponseJson<LocalBridgeStatus>(await fetch(`${LOCAL_BRIDGE_URL}/status`, {
      method: "GET",
      signal: controller.signal,
      cache: "no-store",
    }));
    if (value.service !== "anime-armory-local-bridge"
      || value.capabilities?.localAgentJobs !== true
      || !Array.isArray(value.agents)) return null;
    const codex = value.agents.map(record).find((agent) => agent?.id === "codex" && typeof agent.name === "string");
    if (!codex || typeof codex.name !== "string") return null;
    const models = Array.isArray(value.codexModels)
      ? value.codexModels.flatMap((raw): LocalCodexModelDescriptor[] => {
          const model = record(raw);
          const id = typeof model?.id === "string" ? model.id.trim() : "";
          if (!/^[a-zA-Z0-9._/-]{1,160}$/.test(id)) return [];
          return [{
            id,
            name: typeof model?.name === "string" && model.name.trim() ? model.name.trim() : id,
            description: typeof model?.description === "string" ? model.description.trim() : "",
          }];
        })
      : [];
    if (!models.length) return null;
    return {
      service: "anime-armory-local-bridge",
      version: typeof value.version === "number" ? value.version : 0,
      codexName: codex.name,
      models,
    };
  } catch {
    return null;
  } finally {
    window.clearTimeout(timer);
    signal?.removeEventListener("abort", abort);
  }
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

class LocalCodexAgentGateway implements AgentGateway {
  readonly mode = "local" as const;
  readonly label: string;
  private workScope: Pick<WebWork, "id" | "name" | "line"> | null = null;

  constructor(status: LocalCodexStatus) {
    this.label = `本机 · ${status.codexName}（ChatGPT 登录）`;
  }

  private async token(forcePair = false): Promise<string> {
    if (!this.workScope) throw new Error("本机 Codex 尚未绑定当前作品");
    if (!forcePair) {
      const existing = localAgentTokens.get(this.workScope.id);
      if (existing) return existing;
    }
    const paired = await localResponseJson<{ token?: unknown }>(await fetch(`${LOCAL_BRIDGE_URL}/agent/pair`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        workId: this.workScope.id,
        workName: this.workScope.name,
        line: this.workScope.line,
        agentId: "codex",
      }),
    }));
    if (typeof paired.token !== "string" || !paired.token) throw new Error("桌面端没有返回有效的本机授权");
    localAgentTokens.set(this.workScope.id, paired.token);
    return paired.token;
  }

  private async authorizedFetch(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
    const token = await this.token();
    const headers = new Headers(init.headers);
    headers.set("authorization", `Bearer ${token}`);
    const response = await fetch(`${LOCAL_BRIDGE_URL}${path}`, { ...init, headers });
    if (response.status === 401 && retry) {
      if (this.workScope) localAgentTokens.delete(this.workScope.id);
      await this.token(true);
      return this.authorizedFetch(path, init, false);
    }
    return response;
  }

  private async uploadLocalSources(work: WebWork): Promise<void> {
    for (const attachment of work.attachments) {
      const file = await localFile(attachment.id);
      if (!file) continue;
      await localResponseJson(await this.authorizedFetch("/work-files", {
        method: "POST",
        headers: {
          "content-type": file.type || "application/octet-stream",
          "x-work-id": work.id,
          "x-work-name": encodeURIComponent(work.name),
          "x-line": work.line,
          "x-file-id": attachment.id,
          "x-file-name": encodeURIComponent(file.name),
        },
        body: file,
      }));
    }
  }

  private localPrompt(input: SubmitAgentJobInput): string {
    const parts = [
      input.skillId ? `请使用 ${input.skillId} skill 完成本次任务。` : "",
      input.skillDefinition ? [
        `用户自定义 Skill：${input.skillDefinition.title}`,
        input.skillDefinition.description,
        input.skillDefinition.guide,
        input.skillDefinition.steps.length ? `步骤：\n${input.skillDefinition.steps.map((step, index) => `${index + 1}. ${step}`).join("\n")}` : "",
      ].filter(Boolean).join("\n") : "",
      input.prompt.trim(),
    ];
    return parts.filter(Boolean).join("\n\n");
  }

  async submit(input: SubmitAgentJobInput): Promise<AgentJob> {
    if (!input.prompt.trim()) throw new Error("请输入任务要求后再提交");
    this.workScope = { id: input.work.id, name: input.work.name, line: input.work.line };
    await this.uploadLocalSources(input.work);
    const response = await this.authorizedFetch("/agent/jobs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        workId: input.work.id,
        workName: input.work.name,
        line: input.work.line,
        prompt: this.localPrompt(input),
        creationConfig: input.work.creationConfig,
        agentId: "codex",
      }),
    });
    return normalizeJob(await localResponseJson(response));
  }

  private async withArtifactFiles(job: AgentJob): Promise<AgentJob> {
    if (!job.artifacts?.length) return job;
    const artifacts = await Promise.all(job.artifacts.map(async (artifact) => {
      if (artifact.text || artifact.url || artifact.base64 || artifact.assetId || artifact.file) return artifact;
      const response = await this.authorizedFetch(`/agent/jobs/${job.id}/artifacts/${artifact.id}`);
      if (!response.ok) return artifact;
      const blob = await response.blob();
      if (!blob.size) return artifact;
      return {
        ...artifact,
        file: new File([blob], artifact.name, {
          type: artifact.mimeType || blob.type,
          lastModified: Date.now(),
        }),
      };
    }));
    return { ...job, artifacts };
  }

  async status(jobId: string): Promise<AgentJob> {
    if (!jobId.trim()) throw new Error("本机 Codex 任务 ID 无效");
    const job = normalizeJob(await localResponseJson(await this.authorizedFetch(`/agent/jobs/${encodeURIComponent(jobId)}`)));
    return this.withArtifactFiles(job);
  }
}

class DemoAgentGateway implements AgentGateway {
  readonly mode = "demo" as const;
  readonly label: string;

  constructor(
    label = "后端未就绪",
    private readonly failureMessage = "LabuTV 后端或 cliproxy 尚未就绪，任务未提交。请启动本地后端后重试。",
  ) {
    this.label = label;
  }

  async submit(): Promise<AgentJob> {
    return {
      id: crypto.randomUUID(),
      state: "failed",
      message: this.failureMessage,
      estimatedTokens: 0,
    };
  }
}

export async function createAgentGateway(executor: WorkExecutor = "backend"): Promise<AgentGateway> {
  if (executor === "local-codex") {
    const status = await probeLocalCodex();
    return status
      ? new LocalCodexAgentGateway(status)
      : new DemoAgentGateway(
          "本机 Codex 未连接",
          "未检测到可用的本机 Codex。请启动最新版 LabuTV 桌面端，并先在终端运行 codex login 完成 ChatGPT 登录；可用额度以当前账号为准。",
        );
  }
  const health = await probeBackend();
  return health ? new BackendAgentGateway(health) : new DemoAgentGateway();
}
