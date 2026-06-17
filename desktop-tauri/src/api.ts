// Thin wrappers over the Rust commands + a media-server URL helper.
import { invoke } from "@tauri-apps/api/core";
import type { CanvasData, LineInfo, NextAction, SkillInfo } from "./types";

// The skills repo (where skills/n2d/run.py + SKILL.md live). Fixed; drives the
// pipeline. Kept SEPARATE from the works workspace below.
export const DEFAULT_REPO = "/Users/wesley/learn/anime-arsenal";

let mediaPort = 0;
const mediaListeners = new Set<() => void>();
export async function ensureMedia(): Promise<number> {
  if (!mediaPort) {
    mediaPort = await invoke<number>("start_media");
    mediaListeners.forEach((l) => l()); // wake components that read the port
  }
  return mediaPort;
}

/** External-store hooks so components re-render once the port is ready. */
export function getMediaPort(): number {
  return mediaPort;
}
export function subscribeMediaPort(cb: () => void): () => void {
  mediaListeners.add(cb);
  return () => {
    mediaListeners.delete(cb);
  };
}

/** Confine the media server to files under this root (path-traversal guard). */
export async function mediaAllowRoot(root: string): Promise<void> {
  return invoke("media_allow_root", { root });
}

/** Build a localhost media URL (range-request capable) for an absolute file path. */
export function mediaUrl(abs: string): string {
  if (!mediaPort) return "";
  return `http://127.0.0.1:${mediaPort}/media?path=${encodeURIComponent(abs)}`;
}

export async function scanWorkspace(repoRoot: string): Promise<LineInfo[]> {
  return invoke<LineInfo[]>("scan_workspace", { repoRoot });
}

/** The skill roster for one creative line (dispatcher + `<line>-*` members). */
export async function listSkills(repoRoot: string, line: string): Promise<SkillInfo[]> {
  return invoke<SkillInfo[]>("list_skills", { repoRoot, line });
}

/** Create an empty work folder under a line's product dir; returns its absolute path. */
export async function createWork(dir: string, name: string): Promise<string> {
  return invoke<string>("create_work", { dir, name });
}

/** Resolve (and create) the app's dedicated works workspace (~/AnimeArsenal). */
export async function defaultWorkspace(): Promise<string> {
  return invoke<string>("default_workspace");
}

/**
 * Resolve the skills repo: the live `devRepo` checkout if it has skills/ (dev),
 * else the /tod-bundled copy shipped inside the app (installed/self-contained).
 */
export async function resolveRepo(devRepo: string): Promise<string> {
  return invoke<string>("resolve_repo", { devRepo });
}

/** Seed the /tod --demos sample works into the workspace once; returns count. */
export async function seedDemos(workspaceRoot: string): Promise<number> {
  return invoke<number>("seed_demos", { workspaceRoot });
}

/** Move a work folder to the system Trash; guarded to the workspace root. */
export async function deleteWork(workspaceRoot: string, path: string): Promise<void> {
  return invoke("delete_work", { workspaceRoot, path });
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
