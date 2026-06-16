// Thin wrappers over the Rust commands + a media-server URL helper.
import { invoke } from "@tauri-apps/api/core";
import type { CanvasData, LineInfo, NextAction } from "./types";

// Default workspace = the anime-arsenal repo root. Change via the folder picker.
export const DEFAULT_REPO = "/Users/wesley/learn/anime-arsenal";

let mediaPort = 0;
export async function ensureMedia(): Promise<number> {
  if (!mediaPort) {
    mediaPort = await invoke<number>("start_media");
  }
  return mediaPort;
}

/** Build a localhost media URL (range-request capable) for an absolute file path. */
export function mediaUrl(abs: string): string {
  if (!mediaPort) return "";
  return `http://127.0.0.1:${mediaPort}/media?path=${encodeURIComponent(abs)}`;
}

export async function scanWorkspace(repoRoot: string): Promise<LineInfo[]> {
  return invoke<LineInfo[]>("scan_workspace", { repoRoot });
}

export async function readCanvas(root: string, ep: string): Promise<CanvasData> {
  return invoke<CanvasData>("read_canvas", { root, ep });
}

export async function readNextAction(
  repoRoot: string,
  root: string,
  ep: string,
): Promise<NextAction> {
  const raw = await invoke<string>("read_next_action", { repoRoot, root, ep });
  try {
    return JSON.parse(raw) as NextAction;
  } catch {
    return { error: raw };
  }
}

// Filesystem watch
export async function watchRoot(root: string): Promise<void> {
  return invoke("watch_root", { root });
}
export async function unwatchRoot(root: string): Promise<void> {
  return invoke("unwatch_root", { root });
}

// PTY
export async function ptySpawn(cwd: string, rows: number, cols: number): Promise<number> {
  return invoke<number>("pty_spawn", { cwd, rows, cols });
}
export async function ptyWrite(id: number, data: string): Promise<void> {
  return invoke("pty_write", { id, data });
}
export async function ptyResize(id: number, rows: number, cols: number): Promise<void> {
  return invoke("pty_resize", { id, rows, cols });
}
export async function ptyKill(id: number): Promise<void> {
  return invoke("pty_kill", { id });
}
