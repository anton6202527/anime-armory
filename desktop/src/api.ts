// Thin wrappers over the Rust commands + a media-server URL helper.
import { invoke } from "@tauri-apps/api/core";
import type {
  AgentInfo,
  CanvasData,
  CanvasLayout,
  CanvasNodePosition,
  ClipEditData,
  ClipEditPatch,
  EpisodeWorkspace,
  ImportWorkSourcesResult,
  LineInfo,
  NextAction,
  QualityInsights,
  SkillInfo,
  SkillTreeEntry,
  WorkChangeDetail,
  WorkChanges,
  WorkChangeSummary,
  WorkDirListing,
  WorkFileWriteResult,
  WorkSearchResponse,
  WorkSnapshot,
} from "./types";

// Optional dev override for the skills repo. Normally left empty so the Rust
// side can infer the live checkout in dev and fall back to bundled resources in
// packaged builds. Keep this separate from the works workspace.
export const DEFAULT_REPO = import.meta.env.VITE_ANIME_ARMORY_REPO || "";

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

/** The file/folder tree under skills/<dir>/ for the skills-detail view. */
export async function skillTree(repoRoot: string, dir: string): Promise<SkillTreeEntry[]> {
  return invoke<SkillTreeEntry[]>("skill_tree", { repoRoot, dir });
}

/** Read one text file inside a skill (skills/<dir>/<rel>) for the code pane. */
export async function readSkillFile(repoRoot: string, dir: string, rel: string): Promise<string> {
  return invoke<string>("read_skill_file", { repoRoot, dir, rel });
}

/** The full file/folder tree under a work root, for the 文件 viewer tab. */
export async function workTree(root: string): Promise<SkillTreeEntry[]> {
  return invoke<SkillTreeEntry[]>("work_tree", { root });
}

/** One shallow directory page under a work root, for the 文件 viewer tab. */
export async function workDir(
  root: string,
  rel = "",
  offset = 0,
  limit = 500,
): Promise<WorkDirListing> {
  return invoke<WorkDirListing>("work_dir", { root, rel, offset, limit });
}

/** Cheap recursive fingerprint for live-refresh polling; no baseline side effects. */
export async function workSnapshot(root: string): Promise<WorkSnapshot> {
  return invoke<WorkSnapshot>("work_snapshot", { root });
}

/** Root-level emptiness probe; avoids a full file-tree scan on first open. */
export async function workIsEmpty(root: string): Promise<boolean> {
  return invoke<boolean>("work_is_empty", { root });
}

/** Count changed/deleted files without sending the full tree to the frontend. */
export async function workChangeSummary(root: string): Promise<WorkChangeSummary> {
  return invoke<WorkChangeSummary>("work_change_summary", { root });
}

/** Full changed/deleted/added file list against the local archive baseline. */
export async function workChanges(root: string): Promise<WorkChanges> {
  return invoke<WorkChanges>("work_changes", { root });
}

/** Old/new text for one changed file, when the archived baseline has a text snapshot. */
export async function readWorkChange(root: string, rel: string): Promise<WorkChangeDetail> {
  return invoke<WorkChangeDetail>("read_work_change", { root, rel });
}

/** Archive current work-root state as the new clean baseline. */
export async function archiveWorkChanges(root: string): Promise<WorkChangeSummary> {
  return invoke<WorkChangeSummary>("archive_work_changes", { root });
}

/** Archive one changed/deleted file as clean without accepting unrelated changes. */
export async function archiveWorkChange(root: string, rel: string): Promise<WorkChangeSummary> {
  return invoke<WorkChangeSummary>("archive_work_change", { root, rel });
}

/** Read one text file inside a work root (<root>/<rel>) for the file preview. */
export async function readWorkFile(root: string, rel: string): Promise<string> {
  return invoke<string>("read_work_file", { root, rel });
}

/** Write one UTF-8 text file inside a work root. `expectedMtime` prevents
 *  silently overwriting a file regenerated by an external agent while editing. */
export async function writeWorkFile(
  root: string,
  rel: string,
  text: string,
  expectedMtime?: number,
): Promise<WorkFileWriteResult> {
  return invoke<WorkFileWriteResult>("write_work_file", {
    root,
    rel,
    text,
    expectedMtime,
  });
}

/** Baseline files that no longer exist on disk. */
export async function workDeleted(root: string): Promise<string[]> {
  return invoke<string[]>("work_deleted", { root });
}

export async function searchWorkFiles(
  root: string,
  query: string,
  includeContent = true,
  caseSensitive = false,
  wholeWord = false,
  useRegex = false,
): Promise<WorkSearchResponse> {
  return invoke<WorkSearchResponse>("search_work_files", {
    root,
    query,
    includeContent,
    caseSensitive,
    wholeWord,
    useRegex,
  });
}

export async function createWorkEntry(
  root: string,
  parentRel: string,
  name: string,
  kind: "file" | "folder",
): Promise<string> {
  return invoke<string>("create_work_entry", { root, parentRel, name, kind });
}

export async function importWorkSources(root: string, sources: string[]): Promise<string[]> {
  return invoke<string[]>("import_work_sources", { root, sources });
}

export async function importN2dNovelSources(root: string, sources: string[]): Promise<ImportWorkSourcesResult> {
  return invoke<ImportWorkSourcesResult>("import_n2d_novel_sources", { root, sources });
}

export async function renameWorkEntry(root: string, rel: string, newName: string): Promise<string> {
  return invoke<string>("rename_work_entry", { root, rel, newName });
}

export async function deleteWorkEntry(root: string, rel: string): Promise<void> {
  return invoke("delete_work_entry", { root, rel });
}

export async function revealWorkEntry(root: string, rel: string): Promise<void> {
  return invoke("reveal_work_entry", { root, rel });
}

export async function openWorkEntry(root: string, rel: string): Promise<void> {
  return invoke("open_work_entry", { root, rel });
}

export async function openSourceRepo(): Promise<void> {
  return invoke("open_source_repo");
}

/** Open a trusted http(s) URL in the system browser. */
export async function openExternalUrl(url: string): Promise<void> {
  return invoke("open_external_url", { url });
}

export async function setAppTerminalVisible(visible: boolean): Promise<void> {
  return invoke("set_app_terminal_visible", { visible });
}

/** Create an empty work folder under a line's product dir; returns its absolute path.
 *  `repoRoot` is passed so the backend can refuse to create inside the project repo. */
export async function createWork(dir: string, repoRoot: string, name: string): Promise<string> {
  return invoke<string>("create_work", { dir, repoRoot, name });
}

/** Resolve (and create) the app's dedicated works workspace (~/AnimeArmory). */
export async function defaultWorkspace(): Promise<string> {
  return invoke<string>("default_workspace");
}

/**
 * Resolve the skills repo: the live `devRepo` checkout if it has skills/ (dev),
 * else the bundled copy shipped inside the app (installed/self-contained).
 */
export async function resolveRepo(devRepo: string): Promise<string> {
  return invoke<string>("resolve_repo", { devRepo });
}

/** Seed bundled sample works into the workspace once; returns count. */
export async function seedDemos(workspaceRoot: string): Promise<number> {
  return invoke<number>("seed_demos", { workspaceRoot });
}

/** Move a work folder to the system Trash; guarded to the workspace root AND
 *  hard-blocked from anything inside the project repo (`repoRoot`). */
export async function deleteWork(
  workspaceRoot: string,
  repoRoot: string,
  path: string,
): Promise<void> {
  return invoke("delete_work", { workspaceRoot, repoRoot, path });
}

// Detect local AI agent CLIs. Machine-global, so cache the result across tabs;
// pass force=true to re-probe (e.g. a manual refresh).
let _agentsCache: Promise<AgentInfo[]> | null = null;
export async function detectAgents(force = false): Promise<AgentInfo[]> {
  if (force || !_agentsCache) {
    _agentsCache = invoke<AgentInfo[]>("detect_agents").catch((e) => {
      _agentsCache = null; // let a later call retry
      throw e;
    });
  }
  return _agentsCache;
}

/** The agent to use for auto-enter / executing a prompt. Priority:
 *  only one installed -> use it; otherwise codex -> image-capable yes -> maybe
 *  -> OpenCode fallback -> any found agent. Null if none installed. */
export function pickDefaultAgent(agents: AgentInfo[]): AgentInfo | null {
  const found = agents.filter((a) => a.found);
  if (found.length === 1) return found[0];
  return (
    found.find((a) => a.id === "codex") ||
    found.find((a) => a.image === "yes") ||
    found.find((a) => a.image === "maybe") ||
    found.find((a) => a.id === "opencode") ||
    found[0] ||
    null
  );
}

export async function readCanvas(root: string, ep: string): Promise<CanvasData> {
  return invoke<CanvasData>("read_canvas", { root, ep });
}

export async function readEpisodeWorkspace(root: string, ep: string): Promise<EpisodeWorkspace | null> {
  return invoke<EpisodeWorkspace | null>("read_episode_workspace", { root, ep });
}

export async function readQualityInsights(
  root: string,
  line: string,
  ep?: string | null,
): Promise<QualityInsights> {
  return invoke<QualityInsights>("read_quality_insights", { root, line, ep: ep ?? null });
}

export async function readCanvasLayout(root: string, ep: string): Promise<CanvasLayout> {
  return invoke<CanvasLayout>("read_canvas_layout", { root, ep });
}

export async function writeCanvasLayout(
  root: string,
  ep: string,
  nodes: CanvasNodePosition[],
): Promise<void> {
  return invoke("write_canvas_layout", { root, ep, nodes });
}

export async function readClipEdit(
  root: string,
  ep: string,
  clipId: string,
  number?: number,
): Promise<ClipEditData> {
  return invoke<ClipEditData>("read_clip_edit", { root, ep, clipId, number });
}

export async function writeClipEdit(
  root: string,
  ep: string,
  clipId: string,
  number: number | undefined,
  patch: ClipEditPatch,
): Promise<ClipEditData> {
  return invoke<ClipEditData>("write_clip_edit", { root, ep, clipId, number, patch });
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
