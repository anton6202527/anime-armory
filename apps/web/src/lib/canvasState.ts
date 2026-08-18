import type {
  CanvasDocument,
  CreationLine,
  WebWork,
} from "../types";

const CANVAS_SCHEMA_VERSION = 1;
const canvasKey = (workId: string) => `anime-armory.web.canvas.${workId}`;

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

export async function loadCloudCanvasDocument(_cloudProjectId: string): Promise<CanvasDocument | null> {
  return null;
}

export async function saveCloudCanvasDocument(_cloudProjectId: string, _document: CanvasDocument): Promise<void> {
  // Cloud persistence returns only after a BFF REST resource is implemented.
}

/**
 * Restore a canvas opened from a shared/cross-device URL. The public URL keeps
 * the stable client project key, while Supabase remains authoritative for the
 * internal project id and authorization.
 */
export async function restoreCloudWork(_projectKey: string): Promise<WebWork | null> {
  return null;
}
