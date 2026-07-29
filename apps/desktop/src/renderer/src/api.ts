// Thin wrappers over the typed IPC bridge + a media-server URL helper.
// Exported names/signatures are kept identical to the Tauri app so the
// component layer ports unchanged; the transport underneath is the typed
// Electron contract in @shared/ipc (channel names checked at compile time).
import { bridge } from "./platform/bridge";
import type {
  AgentInfo,
  CanvasReadResult,
  CanvasLayout,
  CanvasGenerationConfig,
  CanvasGenerationKind,
  CanvasNodePosition,
  ClipEditData,
  ClipEditPatch,
  DemoDownloadInfo,
  DemoInstallResult,
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

const invoke = bridge.invoke.bind(bridge);

// Optional dev override for the skills repo. Normally left empty so the main
// process can infer the live checkout in dev and fall back to bundled
// resources in packaged builds. Keep this separate from the works workspace.
export const DEFAULT_REPO = import.meta.env.VITE_ANIME_ARMORY_REPO || "";

let mediaPort = 0;
let mediaStartPromise: Promise<number> | null = null;
const mediaListeners = new Set<() => void>();
export async function ensureMedia(): Promise<number> {
  if (mediaPort) return mediaPort;
  mediaStartPromise ??= invoke("media.start", undefined)
    .then((port) => {
      mediaPort = port;
      mediaListeners.forEach((listener) => listener());
      return port;
    })
    .finally(() => {
      mediaStartPromise = null;
    });
  return mediaStartPromise;
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
  return invoke("media.allowRoot", { root });
}

/** Build a localhost media URL (range-request capable) for an absolute file path. */
export function mediaUrl(abs: string): string {
  if (!mediaPort) return "";
  return `http://127.0.0.1:${mediaPort}/media?path=${encodeURIComponent(abs)}`;
}

/** Build a URL that probes video codecs and transcodes unsupported inputs in
 *  an out-of-process FFmpeg worker before serving a Range-capable MP4. */
export function videoUrl(abs: string): string {
  if (!mediaPort) return "";
  return `http://127.0.0.1:${mediaPort}/video?path=${encodeURIComponent(abs)}`;
}

export async function scanWorkspace(repoRoot: string): Promise<LineInfo[]> {
  return invoke("workspace.scan", { repoRoot });
}

/** The skill roster for one creative line (dispatcher + `<line>-*` members). */
export async function listSkills(repoRoot: string, line: string): Promise<SkillInfo[]> {
  return invoke("skills.list", { repoRoot, line });
}

/** The file/folder tree under skills/<dir>/ for the skills-detail view. */
export async function skillTree(repoRoot: string, dir: string): Promise<SkillTreeEntry[]> {
  return invoke("skills.tree", { repoRoot, dir });
}

/** Read one text file inside a skill (skills/<dir>/<rel>) for the code pane. */
export async function readSkillFile(repoRoot: string, dir: string, rel: string): Promise<string> {
  return invoke("skills.readFile", { repoRoot, dir, rel });
}

/** The full file/folder tree under a work root, for the 文件 viewer tab. */
export async function workTree(root: string): Promise<SkillTreeEntry[]> {
  return invoke("work.tree", { root });
}

/** One shallow directory page under a work root, for the 文件 viewer tab. */
export async function workDir(
  root: string,
  rel = "",
  offset = 0,
  limit = 500,
): Promise<WorkDirListing> {
  return invoke("work.dir", { root, rel, offset, limit });
}

/** Cheap recursive fingerprint for live-refresh polling; no baseline side effects. */
export async function workSnapshot(root: string): Promise<WorkSnapshot> {
  return invoke("work.snapshot", { root });
}

/** Root-level emptiness probe; avoids a full file-tree scan on first open. */
export async function workIsEmpty(root: string): Promise<boolean> {
  return invoke("work.isEmpty", { root });
}

/** Count changed/deleted files without sending the full tree to the frontend. */
export async function workChangeSummary(root: string): Promise<WorkChangeSummary> {
  return invoke("changes.summary", { root });
}

/** Full changed/deleted/added file list against the local archive baseline. */
export async function workChanges(root: string): Promise<WorkChanges> {
  return invoke("changes.list", { root });
}

/** Old/new text for one changed file, when the archived baseline has a text snapshot. */
export async function readWorkChange(root: string, rel: string): Promise<WorkChangeDetail> {
  return invoke("changes.read", { root, rel });
}

/** Archive current work-root state as the new clean baseline. */
export async function archiveWorkChanges(root: string): Promise<WorkChangeSummary> {
  return invoke("changes.archiveAll", { root });
}

/** Archive one changed/deleted file as clean without accepting unrelated changes. */
export async function archiveWorkChange(root: string, rel: string): Promise<WorkChangeSummary> {
  return invoke("changes.archiveOne", { root, rel });
}

/** Restore all current changed/deleted/added files back to the local clean baseline. */
export async function restoreWorkChanges(root: string): Promise<WorkChangeSummary> {
  return invoke("changes.restoreAll", { root });
}

/** Restore one changed/deleted/added file back to the local clean baseline. */
export async function restoreWorkChange(root: string, rel: string): Promise<WorkChangeSummary> {
  return invoke("changes.restoreOne", { root, rel });
}

/** Read one text file inside a work root (<root>/<rel>) for the file preview. */
export async function readWorkFile(root: string, rel: string): Promise<string> {
  return invoke("work.readFile", { root, rel });
}

/** Extract readable text from a docx file inside a work root. */
export async function readWorkDocx(root: string, rel: string): Promise<string> {
  return invoke("work.readDocx", { root, rel });
}

/** Write one UTF-8 text file inside a work root. `expectedMtime` prevents
 *  silently overwriting a file regenerated by an external agent while editing. */
export async function writeWorkFile(
  root: string,
  rel: string,
  text: string,
  expectedMtime?: number,
): Promise<WorkFileWriteResult> {
  return invoke("work.writeFile", { root, rel, text, expectedMtime });
}

export interface CanvasCaptureSaveResult {
  rel: string;
  path: string;
}

export async function saveCanvasCapture(
  root: string,
  imageData: string,
  label: string,
): Promise<CanvasCaptureSaveResult> {
  return invoke("work.saveCanvasCapture", { root, imageData, label });
}

/** Baseline files that no longer exist on disk. */
export async function workDeleted(root: string): Promise<string[]> {
  return invoke("changes.deleted", { root });
}

export async function searchWorkFiles(
  root: string,
  query: string,
  caseSensitive = false,
  wholeWord = false,
  useRegex = false,
): Promise<WorkSearchResponse> {
  return invoke("work.search", { root, query, caseSensitive, wholeWord, useRegex });
}

export async function createWorkEntry(
  root: string,
  parentRel: string,
  name: string,
  kind: "file" | "folder",
): Promise<string> {
  return invoke("work.createEntry", { root, parentRel, name, kind });
}

export async function importWorkSources(root: string, sources: string[]): Promise<string[]> {
  return invoke("work.importSources", { root, sources });
}

export async function importN2dNovelSources(root: string, sources: string[]): Promise<ImportWorkSourcesResult> {
  return invoke("work.importN2dNovel", { root, sources });
}

export async function renameWorkEntry(root: string, rel: string, newName: string): Promise<string> {
  return invoke("work.renameEntry", { root, rel, newName });
}

export async function deleteWorkEntry(root: string, rel: string): Promise<void> {
  return invoke("work.deleteEntry", { root, rel });
}

export async function revealWorkEntry(root: string, rel: string): Promise<void> {
  return invoke("work.revealEntry", { root, rel });
}

export async function openWorkEntry(root: string, rel: string): Promise<void> {
  return invoke("work.openEntry", { root, rel });
}

export async function openSourceRepo(): Promise<void> {
  return invoke("app.openSourceRepo", undefined);
}

/** Open a trusted http(s) URL in the system browser. */
export async function openExternalUrl(url: string): Promise<void> {
  return invoke("app.openExternalUrl", { url });
}

export async function setAppTerminalVisible(visible: boolean): Promise<void> {
  return invoke("app.setTerminalVisible", { visible });
}

export async function setAppLanguage(language: string): Promise<void> {
  return invoke("app.setLanguage", { language });
}

export async function setAppRecentWorks(works: Array<{ path: string; name: string }>): Promise<void> {
  return invoke("app.setRecentWorks", { works });
}

/** Native directory picker (replaces the Tauri dialog plugin). */
export async function pickDirectory(title?: string): Promise<string | null> {
  return invoke("workspace.pickDirectory", { title });
}

/** Native multi-file picker filtered by extensions. */
export async function pickImportFiles(extensions: string[], title?: string): Promise<string[]> {
  return invoke("work.pickImportFiles", { extensions, title });
}

/** Create an empty work folder under a line's product dir; returns its absolute path.
 *  `repoRoot` is passed so the backend can refuse to create inside the project repo. */
export async function createWork(dir: string, repoRoot: string, name: string): Promise<string> {
  return invoke("workspace.createWork", { dir, repoRoot, name });
}

/** Resolve (and create) the app's dedicated LabuTV works workspace. */
export async function defaultWorkspace(): Promise<string> {
  return invoke("workspace.default", undefined);
}

/**
 * Resolve the skills repo: the live `devRepo` checkout if it has skills/ (dev),
 * else the bundled copy shipped inside the app (installed/self-contained).
 */
export async function resolveRepo(devRepo: string): Promise<string> {
  return invoke("workspace.resolveRepo", { devRepo });
}

/** Seed bundled sample works into the workspace once; returns count. */
export async function seedDemos(workspaceRoot: string): Promise<number> {
  return invoke("demos.seed", { workspaceRoot });
}

/** Available per-line Demo ZIP files published through the public R2 catalog. */
export async function listDemoDownloads(workspaceRoot: string): Promise<DemoDownloadInfo[]> {
  return invoke("demos.list", { workspaceRoot });
}

/** Download one work's Demo ZIP from R2, verify it, install it, and mark it as DEMO. */
export async function installDemo(workspaceRoot: string, rel: string): Promise<DemoInstallResult> {
  return invoke("demos.install", { workspaceRoot, rel });
}

/** Move a work folder to the system Trash; guarded to the workspace root AND
 *  hard-blocked from anything inside the project repo (`repoRoot`). */
export async function deleteWork(
  workspaceRoot: string,
  repoRoot: string,
  path: string,
): Promise<void> {
  return invoke("workspace.deleteWork", { workspaceRoot, repoRoot, path });
}

// Detect local AI agent CLIs. Machine-global, so cache the result across tabs;
// pass force=true to re-probe (e.g. a manual refresh).
let _agentsCache: Promise<AgentInfo[]> | null = null;
export async function detectAgents(force = false): Promise<AgentInfo[]> {
  if (force || !_agentsCache) {
    _agentsCache = invoke("agents.detect", { force }).catch((e) => {
      _agentsCache = null; // let a later call retry
      throw e;
    });
  }
  return _agentsCache;
}

/** The agent to use for auto-enter / executing a prompt. Priority:
 *  only one installed -> use it; otherwise codex -> image-capable yes -> maybe
 *  -> OpenCode fallback -> any found agent. Null if none installed. */
export function pickDefaultAgent(agents: AgentInfo[], preferredId?: string | null): AgentInfo | null {
  const found = agents.filter((a) => a.found);
  let savedPreference = preferredId ?? "";
  if (!savedPreference) {
    try {
      savedPreference = window.localStorage.getItem("aa.preferredAgentId") ?? "";
    } catch {
      savedPreference = "";
    }
  }
  const preferred = found.find((agent) => agent.id === savedPreference);
  if (preferred) return preferred;
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

export async function readCanvas(root: string, ep: string, knownSig?: string): Promise<CanvasReadResult> {
  return invoke("canvas.read", { root, ep, knownSig });
}

export async function readEpisodeWorkspace(root: string, ep: string): Promise<EpisodeWorkspace | null> {
  return invoke("canvas.readEpisodeWorkspace", { root, ep });
}

export async function readQualityInsights(
  root: string,
  line: string,
  ep?: string | null,
): Promise<QualityInsights> {
  return invoke("quality.read", { root, line, ep: ep ?? null });
}

export async function readCanvasLayout(root: string, ep: string): Promise<CanvasLayout> {
  return invoke("canvas.readLayout", { root, ep });
}

export async function writeCanvasLayout(
  root: string,
  ep: string,
  nodes: CanvasNodePosition[],
): Promise<void> {
  return invoke("canvas.writeLayout", { root, ep, nodes });
}

export async function readClipEdit(
  root: string,
  ep: string,
  clipId: string,
  number?: number,
): Promise<ClipEditData> {
  return invoke("canvas.readClipEdit", { root, ep, clipId, number });
}

export async function writeClipEdit(
  root: string,
  ep: string,
  clipId: string,
  number: number | undefined,
  patch: ClipEditPatch,
): Promise<ClipEditData> {
  return invoke("canvas.writeClipEdit", { root, ep, clipId, number, patch });
}

export async function readCanvasGenerationConfig(
  root: string,
  ep: string,
  clipId: string,
  kind: CanvasGenerationKind,
): Promise<CanvasGenerationConfig | null> {
  return invoke("canvas.readGenerationConfig", { root, ep, clipId, kind });
}

export async function writeCanvasGenerationConfig(
  root: string,
  ep: string,
  clipId: string,
  config: CanvasGenerationConfig,
): Promise<CanvasGenerationConfig> {
  return invoke("canvas.writeGenerationConfig", { root, ep, clipId, config });
}

export async function readNextAction(
  repoRoot: string,
  root: string,
  ep: string,
): Promise<NextAction> {
  const raw = await invoke("pipeline.nextAction", { repoRoot, root, ep });
  try {
    return JSON.parse(raw) as NextAction;
  } catch {
    return { error: raw };
  }
}

// Filesystem watch
export async function watchRoot(root: string): Promise<void> {
  return invoke("watch.root", { root });
}
export async function unwatchRoot(root: string): Promise<void> {
  return invoke("watch.unroot", { root });
}

// PTY
export async function ptySpawn(cwd: string, rows: number, cols: number): Promise<number> {
  return invoke("pty.spawn", { cwd, rows, cols });
}
export async function ptyWrite(id: number, data: string): Promise<void> {
  return invoke("pty.write", { id, data });
}
export async function ptyResize(id: number, rows: number, cols: number): Promise<void> {
  return invoke("pty.resize", { id, rows, cols });
}
export async function ptyKill(id: number): Promise<void> {
  return invoke("pty.kill", { id });
}
