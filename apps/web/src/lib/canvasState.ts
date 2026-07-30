import type {
  CanvasDocument,
  CreationLine,
  DraftAttachment,
  WebWork,
} from "../types";
import { getSupabaseAccessToken, getSupabaseClient } from "./cloud";

const CANVAS_SCHEMA_VERSION = 1;
const canvasKey = (workId: string) => `anime-armory.web.canvas.${workId}`;

interface CloudProjectLike {
  id: string;
  clientKey: string;
  name: string;
  createdAt: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isCreationLine(value: unknown): value is CreationLine {
  return value === "novel"
    || value === "n2d"
    || value === "comic"
    || value === "ad"
    || value === "mv"
    || value === "song";
}

function isCanvasDocument(value: unknown): value is CanvasDocument {
  if (!isRecord(value) || value.schemaVersion !== CANVAS_SCHEMA_VERSION) return false;
  if (!isRecord(value.work) || typeof value.work.id !== "string" || !isCreationLine(value.work.line)) return false;
  return Array.isArray(value.nodes)
    && Array.isArray(value.edges)
    && isRecord(value.viewport)
    && isRecord(value.preferences)
    && Array.isArray(value.activity)
    && Array.isArray(value.runHistory);
}

export function loadLocalCanvasDocument(workId: string): CanvasDocument | null {
  const raw = localStorage.getItem(canvasKey(workId));
  if (!raw) return null;
  try {
    const value: unknown = JSON.parse(raw);
    return isCanvasDocument(value) ? value : null;
  } catch {
    return null;
  }
}

export function saveLocalCanvasDocument(document: CanvasDocument) {
  localStorage.setItem(canvasKey(document.work.id), JSON.stringify(document));
}

export function removeLocalCanvasDocument(workId: string) {
  localStorage.removeItem(canvasKey(workId));
}

export async function loadCloudCanvasDocument(cloudProjectId: string): Promise<CanvasDocument | null> {
  const client = await getSupabaseClient();
  if (!client) return null;
  const { data, error } = await client
    .from("project_canvases")
    .select("document")
    .eq("project_id", cloudProjectId)
    .maybeSingle();
  if (error) throw error;
  const document = isRecord(data) ? data.document : null;
  return isCanvasDocument(document) ? document : null;
}

export async function saveCloudCanvasDocument(cloudProjectId: string, document: CanvasDocument): Promise<void> {
  const client = await getSupabaseClient();
  if (!client) return;
  const { error } = await client
    .from("project_canvases")
    .upsert({ project_id: cloudProjectId, document }, { onConflict: "project_id" });
  if (error) throw error;
}

function fallbackWork(project: CloudProjectLike, attachments: DraftAttachment[]): WebWork {
  return {
    id: project.clientKey,
    name: project.name,
    line: "n2d",
    prompt: "",
    attachments,
    createdAt: project.createdAt,
    cloudProjectId: project.id,
    cloudState: "synced",
  };
}

/**
 * Restore a canvas opened from a shared/cross-device URL. The public URL keeps
 * the stable client project key, while Supabase remains authoritative for the
 * internal project id and authorization.
 */
export async function restoreCloudWork(projectKey: string): Promise<WebWork | null> {
  const accessToken = await getSupabaseAccessToken();
  const endpoint = import.meta.env.VITE_ASSET_API_URL?.trim();
  if (!accessToken || !endpoint) return null;

  const { AssetApiClient } = await import("@anime-armory/cloud-client");
  const client = new AssetApiClient({
    endpoint,
    getAccessToken: async () => getSupabaseAccessToken(),
  });
  const projects = (await client.listProjects()).projects;
  const project = projects.find((item) => item.clientKey === projectKey || item.id === projectKey);
  if (!project) return null;

  const cloudDocument = await loadCloudCanvasDocument(project.id);
  if (cloudDocument) {
    const work = {
      ...cloudDocument.work,
      id: project.clientKey,
      cloudProjectId: project.id,
      cloudState: "synced" as const,
    };
    saveLocalCanvasDocument({ ...cloudDocument, work });
    return work;
  }

  const assets = (await client.listAssets(project.id)).assets;
  const attachments: DraftAttachment[] = assets.map((asset) => ({
    id: asset.id,
    assetId: asset.id,
    name: asset.originalName,
    size: asset.sizeBytes,
    type: asset.contentType,
  }));
  return fallbackWork(project, attachments);
}
