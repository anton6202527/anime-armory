import type { AgentJob, WebWork } from "../types";
import { getSupabaseAccessToken } from "./cloud";
import { localFile } from "./localFiles";

const LOCAL_BRIDGE_URL = "http://127.0.0.1:43117/v1";
const LOCAL_AGENT_TOKEN_KEY = "anime-armory.local-agent-token";

export interface SubmitAgentJobInput {
  work: WebWork;
  prompt: string;
}

export interface AgentGateway {
  readonly mode: "local" | "cloud" | "demo";
  readonly label: string;
  submit(input: SubmitAgentJobInput): Promise<AgentJob>;
  status?(jobId: string): Promise<AgentJob>;
}

interface LocalBridgeStatus {
  service: string;
  version: number;
  agents: Array<{ id: string; name: string }>;
  capabilities?: { canvasGeneration?: boolean; localAgentJobs?: boolean };
}

async function responseJson<T>(response: Response): Promise<T> {
  const value: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const record = value && typeof value === "object" ? value as Record<string, unknown> : null;
    const error = record?.error && typeof record.error === "object" ? record.error as Record<string, unknown> : null;
    throw new Error(typeof error?.message === "string" ? error.message : `请求失败（${response.status}）`);
  }
  return value as T;
}

async function probeLocalBridge(): Promise<LocalBridgeStatus | null> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 5000);
  try {
    const response = await fetch(`${LOCAL_BRIDGE_URL}/status`, { signal: controller.signal });
    const status = await responseJson<LocalBridgeStatus>(response);
    return status.service === "anime-armory-local-bridge" ? status : null;
  } catch {
    return null;
  } finally {
    window.clearTimeout(timer);
  }
}

class LocalAgentGateway implements AgentGateway {
  readonly mode = "local" as const;
  readonly label: string;

  constructor(private readonly statusInfo: LocalBridgeStatus) {
    const preferred = statusInfo.agents.find((agent) => agent.id === "codex") ?? statusInfo.agents[0];
    this.label = preferred?.name ? `本地 · ${preferred.name}` : "本地 Agent";
  }

  private async token(forcePair = false): Promise<string> {
    if (!forcePair) {
      const stored = sessionStorage.getItem(LOCAL_AGENT_TOKEN_KEY);
      if (stored) return stored;
    }
    const paired = await responseJson<{ token: string }>(await fetch(`${LOCAL_BRIDGE_URL}/agent/pair`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{}",
    }));
    sessionStorage.setItem(LOCAL_AGENT_TOKEN_KEY, paired.token);
    return paired.token;
  }

  private async authorizedFetch(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
    const token = await this.token();
    const headers = new Headers(init.headers);
    headers.set("authorization", `Bearer ${token}`);
    const response = await fetch(`${LOCAL_BRIDGE_URL}${path}`, { ...init, headers });
    if (response.status === 401 && retry) {
      sessionStorage.removeItem(LOCAL_AGENT_TOKEN_KEY);
      await this.token(true);
      return this.authorizedFetch(path, init, false);
    }
    return response;
  }

  private async uploadLocalSources(work: WebWork): Promise<void> {
    for (const attachment of work.attachments) {
      const file = await localFile(attachment.id);
      if (!file) continue;
      const response = await this.authorizedFetch("/work-files", {
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
      });
      await responseJson(response);
    }
  }

  async submit(input: SubmitAgentJobInput): Promise<AgentJob> {
    await this.uploadLocalSources(input.work);
    const response = await this.authorizedFetch("/agent/jobs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        workId: input.work.id,
        workName: input.work.name,
        line: input.work.line,
        prompt: input.prompt,
        creationConfig: input.work.creationConfig,
        agentId: this.statusInfo.agents.find((agent) => agent.id === "codex")?.id ?? this.statusInfo.agents[0]?.id,
      }),
    });
    return responseJson<AgentJob>(response);
  }

  private async withArtifactFiles(job: AgentJob): Promise<AgentJob> {
    if (!job.artifacts?.length) return job;
    const artifacts = await Promise.all(job.artifacts.map(async (artifact) => {
      if (artifact.text || artifact.url || artifact.base64 || artifact.assetId || artifact.file) return artifact;
      const response = await this.authorizedFetch(`/agent/jobs/${job.id}/artifacts/${artifact.id}`);
      if (!response.ok) return artifact;
      const blob = await response.blob();
      if (!blob.size) return artifact;
      return { ...artifact, file: new File([blob], artifact.name, { type: artifact.mimeType || blob.type, lastModified: Date.now() }) };
    }));
    return { ...job, artifacts };
  }

  async status(jobId: string): Promise<AgentJob> {
    return this.withArtifactFiles(await responseJson<AgentJob>(await this.authorizedFetch(`/agent/jobs/${jobId}`)));
  }
}

class CloudAgentGateway implements AgentGateway {
  readonly mode = "cloud" as const;
  readonly label = "云端全模态 API";

  constructor(private readonly baseUrl: string) {}

  async submit(input: SubmitAgentJobInput): Promise<AgentJob> {
    const accessToken = await getSupabaseAccessToken();
    if (!accessToken) throw new Error("请先登录后再提交云端任务");
    const response = await fetch(`${this.baseUrl.replace(/\/$/, "")}/v1/agent/jobs`, {
      method: "POST",
      headers: {
        authorization: `Bearer ${accessToken}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({
        projectId: input.work.cloudProjectId ?? input.work.id,
        line: input.work.line,
        prompt: input.prompt,
        creationConfig: input.work.creationConfig,
        attachmentIds: input.work.attachments.map((attachment) => attachment.assetId).filter(Boolean),
      }),
    });
    return responseJson<AgentJob>(response);
  }
}

class DemoAgentGateway implements AgentGateway {
  readonly mode = "demo" as const;
  readonly label = "演示模式";

  async submit(): Promise<AgentJob> {
    return {
      id: crypto.randomUUID(),
      state: "failed",
      message: "未连接可执行 Skill 的本地 Agent 或云端服务；任务未提交。请启动最新版桌面端并授权本地 Agent。",
      estimatedTokens: 0,
    };
  }
}

export async function createAgentGateway(): Promise<AgentGateway> {
  const bridge = await probeLocalBridge();
  if (bridge?.capabilities?.localAgentJobs && bridge.agents.length) return new LocalAgentGateway(bridge);
  const cloudUrl = import.meta.env.VITE_AGENT_API_URL?.trim();
  return cloudUrl ? new CloudAgentGateway(cloudUrl) : new DemoAgentGateway();
}
