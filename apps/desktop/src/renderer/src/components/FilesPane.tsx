import {
  lazy,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  type CSSProperties,
  type WheelEvent,
} from "react";
import { getPathForFile } from "../platform/bridge";
import {
  createWorkEntry,
  deleteWorkEntry,
  ensureMedia,
  getMediaPort,
  importN2dNovelSources,
  importWorkSources,
  mediaAllowRoot,
  mediaUrl,
  videoUrl,
  openWorkEntry,
  pickImportFiles,
  readWorkDocx,
  readWorkFile,
  renameWorkEntry,
  revealWorkEntry,
  subscribeMediaPort,
  workDir,
} from "../api";
import { buildWorkTreeDecorations, type WorkTreeDecoration } from "../explorerDecorations";
import { createEditorBreadcrumbCursorStore } from "../editorBreadcrumbCursor";
import { createEditorBreadcrumbDocumentStore } from "../editorBreadcrumbDocument";
import { useI18n } from "../i18n";
import {
  COLLAPSE_LEFT_SIDEBAR_EVENT,
  FILES_SIDE_COLLAPSE_WIDTH,
  FILES_SIDE_WIDTH_CHANGED_EVENT,
  clampFilesSideWidth,
  clearStoredFilesSideWidth,
  commitFilesSideWidth,
  draftFilesSideWidth,
  readCurrentFilesSideWidthOrNull,
  readStoredFilesSideWidthOrNull,
  scheduleWindowResizeEvent,
} from "../paneLayout";
import type { ImportWorkSourcesResult, SkillTreeEntry, WorkRoot } from "../types";
import { Codicon } from "./Codicon";
import { EditorBreadcrumbs } from "./EditorBreadcrumbs";
import { WorkFileIcon } from "./FileIcon";
import { DecodedImage } from "../mediaPreview/DecodedImage";
import { VideoPreview } from "./VideoPreview";

const MonacoFileEditor = lazy(() =>
  import("./MonacoFileEditor").then((mod) => ({ default: mod.MonacoFileEditor })),
);

// The default "文件" tab for every work: a real directory tree of the work root
// (创作区/<line>/<work>/) on the left, with a preview pane on the right. Text via
// read_work_file; images / video / audio via the localhost media server (same
// channel the canvas thumbnails use). Re-reads on `refreshKey` (fs watch).
const IMG = new Set(["png", "jpg", "jpeg", "webp", "gif", "bmp", "svg"]);
const VIDEO = new Set(["mp4", "mov", "webm", "m4v"]);
const AUDIO = new Set(["wav", "mp3", "m4a", "aac", "flac", "ogg"]);
const MARKDOWN = new Set(["md", "markdown", "mdx"]);
const JSONISH = new Set(["json", "jsonl"]);
const DOCX = new Set(["docx"]);
const TEXT = new Set(["txt", "text", "log", "srt", "csv"]);
const TREE_ROW_HEIGHT = 22;
const TREE_BASE_PADDING = 4;
const TREE_INDENT = 12;
const TREE_OVERSCAN = 12;
const TREE_PAGE_LIMIT = 500;
const PREVIEW_CACHE_LIMIT = 12;
const PREVIEW_CACHE_TEXT_LIMIT = 2 * 1024 * 1024;
const IMAGE_ZOOM_MIN = 0.25;
const IMAGE_ZOOM_MAX = 6;
const IMAGE_STAGE_PADDING = 32;
const NOVEL_IMPORT_EXTENSIONS = ["txt", "md", "markdown", "mdx", "docx", "pdf"];
const NOVEL_IMPORT_EXTENSIONS_SET = new Set(NOVEL_IMPORT_EXTENSIONS);

type PreviewKind = "img" | "video" | "audio" | "markdown" | "json" | "docx" | "text";
type ContextMenuState = { x: number; y: number; entry: SkillTreeEntry | null };
type DirPageState = { loaded: number; total: number; hasMore: boolean; loading?: boolean };
type Size = { width: number; height: number };
type EditorTab = { path: string; pinned: boolean };

function ext(name: string): string {
  const i = name.lastIndexOf(".");
  return i < 0 ? "" : name.slice(i + 1).toLowerCase();
}

function parentRel(path: string): string {
  const i = path.lastIndexOf("/");
  return i < 0 ? "" : path.slice(0, i);
}

function basename(path: string): string {
  const i = path.lastIndexOf("/");
  return i < 0 ? path : path.slice(i + 1);
}

function shellQuote(value: string): string {
  return `'${value.replace(/'/g, `'\\''`)}'`;
}

function clampImageZoom(value: number): number {
  return Math.min(IMAGE_ZOOM_MAX, Math.max(IMAGE_ZOOM_MIN, Number(value.toFixed(2))));
}

async function copyText(value: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(value);
    return;
  } catch {
    const ta = document.createElement("textarea");
    ta.value = value;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
  }
}

function previewKind(name: string): PreviewKind {
  const e = ext(name);
  if (IMG.has(e)) return "img";
  if (VIDEO.has(e)) return "video";
  if (AUDIO.has(e)) return "audio";
  if (MARKDOWN.has(e)) return "markdown";
  if (JSONISH.has(e)) return "json";
  if (DOCX.has(e)) return "docx";
  if (TEXT.has(e)) return "text";
  return "text";
}

function treeGuideStyle(depth: number): CSSProperties {
  if (depth <= 0) return {};
  const guide = "linear-gradient(var(--tree-indent-guide), var(--tree-indent-guide))";
  const images = Array.from({ length: depth }, () => guide).join(", ");
  const positions = Array.from(
    { length: depth },
    (_, i) => `${TREE_BASE_PADDING + 6 + i * TREE_INDENT}px 0`,
  ).join(", ");
  return {
    backgroundImage: images,
    backgroundPosition: positions,
    backgroundRepeat: "no-repeat",
    backgroundSize: "1px 100%",
  };
}

function visibleEntries(tree: SkillTreeEntry[], collapsedDirs: Set<string>): SkillTreeEntry[] {
  const out: SkillTreeEntry[] = [];
  let collapsedAncestorDepth: number | null = null;

  for (const entry of tree) {
    if (collapsedAncestorDepth !== null) {
      if (entry.depth > collapsedAncestorDepth) continue;
      collapsedAncestorDepth = null;
    }

    out.push(entry);
    if (entry.is_dir && collapsedDirs.has(entry.path)) {
      collapsedAncestorDepth = entry.depth;
    }
  }

  return out;
}

function subtreeEndIndex(tree: SkillTreeEntry[], dir: string): number {
  if (!dir) return tree.length;
  const idx = tree.findIndex((entry) => entry.path === dir);
  if (idx < 0) return tree.length;
  let end = idx + 1;
  while (end < tree.length && tree[end].path.startsWith(`${dir}/`)) end += 1;
  return end;
}

function directChildDepth(dir: string): number {
  if (!dir) return 0;
  return dir.split("/").filter(Boolean).length;
}

function loadMorePath(dir: string): string {
  return dir ? `${dir}/__anime_armory_load_more__` : "__anime_armory_load_more__";
}

function isLoadMoreEntry(entry: SkillTreeEntry): boolean {
  return Boolean(entry.truncated) && entry.path.endsWith("__anime_armory_load_more__");
}

function makeLoadMoreEntry(dir: string, page: DirPageState): SkillTreeEntry {
  return {
    name: "加载更多...",
    path: loadMorePath(dir),
    depth: directChildDepth(dir),
    is_dir: false,
    truncated: true,
    size: page.total,
    mtime: page.loaded,
    status: "",
  };
}

function decorationTitle(
  t: ReturnType<typeof useI18n>["t"],
  entry: SkillTreeEntry,
  decoration: WorkTreeDecoration,
): string {
  const kind =
    decoration.kind === "modified"
      ? t("files.decoration.modified")
      : decoration.kind === "deleted"
        ? t("files.decoration.deleted")
        : t("files.decoration.untracked");
  return entry.is_dir || decoration.rollup
    ? t("files.decoration.folderTitle", { path: entry.path, kind })
    : t("files.decoration.fileTitle", { path: entry.path, kind });
}

export function FilesPane({
  root,
  refreshKey,
  allowNovelImport = false,
  active = true,
  sideVisible = true,
  reserveSide = false,
  onImported,
  onOpenTerminal,
}: {
  root: WorkRoot;
  refreshKey: number;
  allowNovelImport?: boolean;
  active?: boolean;
  sideVisible?: boolean;
  reserveSide?: boolean;
  onImported?: (result: ImportWorkSourcesResult) => void;
  onOpenTerminal?: (command?: string) => void;
}) {
  const { t } = useI18n();
  const paneRef = useRef<HTMLDivElement>(null);
  const treeScrollRef = useRef<HTMLDivElement>(null);
  const imageStageRef = useRef<HTMLDivElement>(null);
  const previewCacheRef = useRef<Map<string, string>>(new Map());
  const knownDirsRef = useRef<Set<string>>(new Set());
  const treeMutationRef = useRef(0);
  const dirPagesRef = useRef<Map<string, DirPageState>>(new Map());
  const collapsedDirsRef = useRef<Set<string>>(new Set());
  const [tree, setTree] = useState<SkillTreeEntry[]>([]);
  const [dirPages, setDirPages] = useState<Map<string, DirPageState>>(() => new Map());
  const [collapsedDirs, setCollapsedDirs] = useState<Set<string>>(() => new Set());
  const [treeScrollTop, setTreeScrollTop] = useState(0);
  const [treeViewportHeight, setTreeViewportHeight] = useState(0);
  const [sel, setSel] = useState<string>(""); // selected file's rel path
  const [tabs, setTabs] = useState<EditorTab[]>([]);
  const [focusedPath, setFocusedPath] = useState<string>("");
  const [text, setText] = useState<string>("");
  const [err, setErr] = useState<string>("");
  const [importNotice, setImportNotice] = useState<string>("");
  const [importing, setImporting] = useState(false);
  const [draggingNovel, setDraggingNovel] = useState(false);
  const [editorDirty, setEditorDirty] = useState(false);
  const [editorNavigation, setEditorNavigation] = useState<{ line: number; request: number } | null>(null);
  const editorCursorStore = useMemo(createEditorBreadcrumbCursorStore, [root.path]);
  const editorDocumentStore = useMemo(createEditorBreadcrumbDocumentStore, [root.path]);
  const [menu, setMenu] = useState<ContextMenuState | null>(null);
  const [imageZoom, setImageZoom] = useState(1);
  const [imageNatural, setImageNatural] = useState<Size | null>(null);
  const [imageViewport, setImageViewport] = useState<Size>({ width: 0, height: 0 });
  const [localRefresh, setLocalRefresh] = useState(0); // bump after file operations (no fs event)
  const [sideWidth, setSideWidth] = useState<number | null>(readStoredFilesSideWidthOrNull);
  // re-render once the media server port is ready (else media URLs are empty)
  useSyncExternalStore(subscribeMediaPort, getMediaPort);

  useEffect(() => {
    dirPagesRef.current = dirPages;
  }, [dirPages]);

  useEffect(() => {
    collapsedDirsRef.current = collapsedDirs;
  }, [collapsedDirs]);

  useEffect(() => {
    if (!menu) return;
    const close = () => setMenu(null);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenu(null);
    };
    window.addEventListener("click", close);
    window.addEventListener("resize", close);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("resize", close);
      window.removeEventListener("keydown", onKey);
    };
  }, [menu]);

  useEffect(() => {
    const syncSharedSideWidth = () => {
      setSideWidth(readCurrentFilesSideWidthOrNull());
    };
    window.addEventListener(FILES_SIDE_WIDTH_CHANGED_EVENT, syncSharedSideWidth);
    window.addEventListener("storage", syncSharedSideWidth);
    window.addEventListener("resize", syncSharedSideWidth);
    return () => {
      window.removeEventListener(FILES_SIDE_WIDTH_CHANGED_EVENT, syncSharedSideWidth);
      window.removeEventListener("storage", syncSharedSideWidth);
      window.removeEventListener("resize", syncSharedSideWidth);
    };
  }, []);

  useEffect(() => {
    // FilesPane stays mounted while another left-rail pane is active so open
    // editors keep their state. A hidden layer has a zero-sized bounding box;
    // measuring it would clamp the shared sidebar width to zero and make the
    // Files pane reopen at a different width than Changes/Search.
    if (!sideVisible || sideWidth == null) return;
    const sync = () => {
      const pane = paneRef.current;
      if (!pane) return;
      const rect = pane.getBoundingClientRect();
      const next = clampFilesSideWidth(sideWidth, rect.width);
      if (Math.round(next) !== Math.round(sideWidth)) setSideWidth(next);
    };
    sync();
    window.addEventListener("resize", sync);
    return () => window.removeEventListener("resize", sync);
  }, [sideVisible, sideWidth]);

  useEffect(() => {
    setCollapsedDirs(new Set());
    setSel("");
    setTabs([]);
    setFocusedPath("");
    setText("");
    setErr("");
    setImportNotice("");
    setImporting(false);
    setDraggingNovel(false);
    setEditorDirty(false);
    editorCursorStore.setLine(1);
    setEditorNavigation(null);
    setTree([]);
    setDirPages(new Map());
    setTreeScrollTop(0);
    treeScrollRef.current?.scrollTo({ top: 0 });
    previewCacheRef.current.clear();
    knownDirsRef.current.clear();
    treeMutationRef.current += 1;
  }, [editorCursorStore, root.path]);

  useEffect(() => {
    editorCursorStore.setLine(1);
    setEditorNavigation(null);
  }, [editorCursorStore, sel]);

  useEffect(() => {
    const el = treeScrollRef.current;
    if (!el) return;
    const measure = () => setTreeViewportHeight(el.clientHeight);
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    window.addEventListener("resize", measure);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [root.path]);

  function registerDiscoveredDirectories(entries: SkillTreeEntry[]) {
    const next = new Set(collapsedDirsRef.current);
    let changed = false;
    for (const entry of entries) {
      if (!entry.is_dir || knownDirsRef.current.has(entry.path)) continue;
      knownDirsRef.current.add(entry.path);
      next.add(entry.path);
      changed = true;
    }
    if (!changed) return;
    collapsedDirsRef.current = next;
    setCollapsedDirs(next);
  }

  async function loadDirectory(dir: string, offset = 0, replace = offset === 0): Promise<void> {
    treeMutationRef.current += 1;
    setDirPages((prev) => {
      const next = new Map(prev);
      const old = next.get(dir);
      next.set(dir, { loaded: old?.loaded ?? 0, total: old?.total ?? 0, hasMore: old?.hasMore ?? false, loading: true });
      dirPagesRef.current = next;
      return next;
    });
    let listing: Awaited<ReturnType<typeof workDir>>;
    try {
      listing = await workDir(root.path, dir, offset, TREE_PAGE_LIMIT);
    } catch (error) {
      setDirPages((prev) => {
        const next = new Map(prev);
        const old = next.get(dir);
        if (old) next.set(dir, { ...old, loading: false });
        dirPagesRef.current = next;
        return next;
      });
      throw error;
    }
    const loaded = listing.offset + listing.entries.length;
    const page: DirPageState = {
      loaded,
      total: listing.total,
      hasMore: listing.has_more,
      loading: false,
    };
    const incoming = listing.has_more ? [...listing.entries, makeLoadMoreEntry(dir, page)] : listing.entries;
    registerDiscoveredDirectories(listing.entries);
    setTree((prev) => {
      const markerPath = loadMorePath(dir);
      if (!dir) {
        const withoutMarker = prev.filter((entry) => entry.path !== markerPath);
        if (replace) return incoming;
        return [...withoutMarker, ...incoming];
      }
      const parentIndex = prev.findIndex((entry) => entry.path === dir);
      if (parentIndex < 0) return prev;
      if (replace) {
        const kept = prev.filter((entry) => entry.path === dir || !entry.path.startsWith(`${dir}/`));
        const idx = kept.findIndex((entry) => entry.path === dir);
        return [...kept.slice(0, idx + 1), ...incoming, ...kept.slice(idx + 1)];
      }
      const withoutMarker = prev.filter((entry) => entry.path !== markerPath);
      const end = subtreeEndIndex(withoutMarker, dir);
      return [...withoutMarker.slice(0, end), ...incoming, ...withoutMarker.slice(end)];
    });
    setDirPages((prev) => {
      const next = new Map(prev);
      next.set(dir, page);
      dirPagesRef.current = next;
      return next;
    });
  }

  useEffect(() => {
    let alive = true;
    const timer = window.setTimeout(() => {
      const reload = async () => {
        const mutationAtStart = treeMutationRef.current;
        const loadedOpenDirs = [...dirPagesRef.current.keys()]
          .filter((dir) => dir && !collapsedDirsRef.current.has(dir))
          .sort((a, b) => directChildDepth(a) - directChildDepth(b));
        const listing = await workDir(root.path, "", 0, TREE_PAGE_LIMIT).catch(() => ({
          entries: [],
          total: 0,
          offset: 0,
          limit: TREE_PAGE_LIMIT,
          has_more: false,
        }));
        if (!alive) return;
        const rootPage: DirPageState = {
          loaded: listing.entries.length,
          total: listing.total,
          hasMore: listing.has_more,
        };
        registerDiscoveredDirectories(listing.entries);
        let nextTree = listing.has_more ? [...listing.entries, makeLoadMoreEntry("", rootPage)] : listing.entries;
        const nextPages = new Map<string, DirPageState>([["", rootPage]]);
        const rootDirs = new Set(listing.entries.filter((entry) => entry.is_dir).map((entry) => entry.path));
        for (const dir of loadedOpenDirs) {
          const top = dir.split("/")[0];
          if (!rootDirs.has(top)) continue;
          const sub = await workDir(root.path, dir, 0, TREE_PAGE_LIMIT).catch(() => null);
          if (!alive || !sub) return;
          const page: DirPageState = {
            loaded: sub.entries.length,
            total: sub.total,
            hasMore: sub.has_more,
          };
          const incoming = sub.has_more ? [...sub.entries, makeLoadMoreEntry(dir, page)] : sub.entries;
          const idx = nextTree.findIndex((entry) => entry.path === dir);
          if (idx >= 0) {
            const end = subtreeEndIndex(nextTree, dir);
            nextTree = [...nextTree.slice(0, idx + 1), ...incoming, ...nextTree.slice(end)];
            nextPages.set(dir, page);
            registerDiscoveredDirectories(sub.entries);
          }
        }
        if (mutationAtStart !== treeMutationRef.current) return;
        setTree(nextTree);
        dirPagesRef.current = nextPages;
        setDirPages(nextPages);
      };
      reload();
    }, 120);
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [root.path, refreshKey, localRefresh]);

  const treeDecorations = useMemo(() => buildWorkTreeDecorations(tree), [tree]);
  const treeByPath = useMemo(() => new Map(tree.map((entry) => [entry.path, entry])), [tree]);

  function absPath(rel: string): string {
    return rel ? `${root.path}/${rel}` : root.path;
  }

  function entryForPath(path: string): SkillTreeEntry | null {
    if (!path) return null;
    const entry = treeByPath.get(path);
    if (entry) return entry;
    return {
      name: basename(path),
      path,
      depth: path.split("/").filter(Boolean).length - 1,
      is_dir: false,
      status: "",
    };
  }

  function entryTerminalDir(entry: SkillTreeEntry | null): string {
    if (!entry) return root.path;
    return entry.is_dir ? absPath(entry.path) : absPath(parentRel(entry.path));
  }

  function contextParentRel(entry: SkillTreeEntry | null): string {
    if (!entry) return "";
    return entry.is_dir ? entry.path : parentRel(entry.path);
  }

  function refreshFiles() {
    setLocalRefresh((n) => n + 1);
  }

  function isSupportedImportPath(path: string): boolean {
    const dot = path.lastIndexOf(".");
    if (dot < 0) return false;
    return NOVEL_IMPORT_EXTENSIONS_SET.has(path.slice(dot + 1).toLowerCase());
  }

  async function importSources(sources: string[]) {
    const usable = sources.filter(isSupportedImportPath);
    if (usable.length === 0) {
      setImportNotice(t("files.importUnsupported"));
      return;
    }
    setImporting(true);
    setImportNotice("");
    try {
      const result = allowNovelImport
        ? await importN2dNovelSources(root.path, usable)
        : {
            root: root.path,
            name: root.name,
            imported: await importWorkSources(root.path, usable),
          };
      const imported = result.imported;
      if (imported[0]) {
        openFileTab(imported[0], true);
      }
      setImportNotice(t("files.importedNovel", { count: imported.length }));
      onImported?.(result);
      if (result.root === root.path) refreshFiles();
    } catch (e) {
      setImportNotice(String(e));
    } finally {
      setImporting(false);
      setDraggingNovel(false);
    }
  }

  async function chooseNovelFiles() {
    if (importing) return;
    const paths = await pickImportFiles(NOVEL_IMPORT_EXTENSIONS, t("files.importDialogName"));
    if (paths.length) await importSources(paths);
  }

  function pathsFromDataTransfer(dataTransfer: DataTransfer): string[] {
    return Array.from(dataTransfer.files)
      .map((file) => {
        try {
          return getPathForFile(file);
        } catch {
          return "";
        }
      })
      .filter(Boolean);
  }

  const canImportNovel = active && allowNovelImport && tree.length === 0;

  function confirmDiscardForSwitch(nextPath: string): boolean {
    if (!editorDirty || nextPath === sel) return true;
    const ok = window.confirm(t("files.discardUnsavedConfirm", { path: sel }));
    if (ok) setEditorDirty(false);
    return ok;
  }

  function openFileTab(path: string, pinned: boolean) {
    if (!path || !confirmDiscardForSwitch(path)) return;
    setFocusedPath(path);
    setSel(path);
    setTabs((prev) => {
      const existingIndex = prev.findIndex((tab) => tab.path === path);
      if (existingIndex >= 0) {
        return prev.map((tab, index) =>
          index === existingIndex ? { ...tab, pinned: tab.pinned || pinned } : tab,
        );
      }
      if (pinned) return [...prev, { path, pinned: true }];
      const previewIndex = prev.findIndex((tab) => !tab.pinned);
      if (previewIndex < 0) return [...prev, { path, pinned: false }];
      const next = [...prev];
      next[previewIndex] = { path, pinned: false };
      return next;
    });
  }

  useEffect(() => {
    const onOpenFile = (event: Event) => {
      const detail = (event as CustomEvent<{ root: string; path: string; pinned?: boolean }>).detail;
      if (!detail || detail.root !== root.path || !detail.path) return;
      openFileTab(detail.path, detail.pinned !== false);
    };
    window.addEventListener("anime-armory:open-work-file", onOpenFile);
    return () => window.removeEventListener("anime-armory:open-work-file", onOpenFile);
  }, [editorDirty, root.path, sel]);

  function closeEditorTab(path: string) {
    const index = tabs.findIndex((tab) => tab.path === path);
    if (index < 0) return;
    if (editorDirty && sel === path) {
      const ok = window.confirm(t("files.discardUnsavedConfirm", { path }));
      if (!ok) return;
      setEditorDirty(false);
    }
    const nextTabs = tabs.filter((tab) => tab.path !== path);
    setTabs(nextTabs);
    if (sel !== path) return;
    const nextActive = nextTabs[Math.min(index, nextTabs.length - 1)] ?? null;
    setSel(nextActive?.path ?? "");
    setFocusedPath(nextActive?.path ?? "");
    if (!nextActive) {
      setText("");
      setErr("");
    }
  }

  function removeEntryTabs(entry: SkillTreeEntry) {
    const matches = (path: string) => path === entry.path || (entry.is_dir && path.startsWith(`${entry.path}/`));
    const removedActive = sel ? matches(sel) : false;
    const firstRemovedIndex = Math.max(0, tabs.findIndex((tab) => matches(tab.path)));
    const nextTabs = tabs.filter((tab) => !matches(tab.path));
    setTabs(nextTabs);
    if (removedActive) {
      const nextActive = nextTabs[Math.min(firstRemovedIndex, nextTabs.length - 1)] ?? null;
      setSel(nextActive?.path ?? "");
      setFocusedPath(nextActive?.path ?? "");
      setEditorDirty(false);
      if (!nextActive) {
        setText("");
        setErr("");
      }
    }
  }

  function renameOpenTabs(entry: SkillTreeEntry, nextRel: string) {
    const renamedPath = (path: string): string | null => {
      if (path === entry.path) return entry.is_dir ? null : nextRel;
      if (entry.is_dir && path.startsWith(`${entry.path}/`)) return `${nextRel}${path.slice(entry.path.length)}`;
      return path;
    };
    setTabs((prev) =>
      prev
        .map((tab) => {
          const path = renamedPath(tab.path);
          return path ? { ...tab, path } : null;
        })
        .filter((tab): tab is EditorTab => Boolean(tab)),
    );
    if (sel) {
      const nextSel = renamedPath(sel);
      setSel(nextSel ?? "");
    }
    if (focusedPath) {
      const nextFocused = renamedPath(focusedPath);
      setFocusedPath(nextFocused ?? "");
    }
  }

  useEffect(() => {
    if (!canImportNovel) return;
    // OS-level file drop via HTML5 DnD; absolute paths come from the preload
    // webUtils helper (File.path was removed from Electron).
    const onDragOver = (ev: DragEvent) => {
      if (!ev.dataTransfer?.types.includes("Files")) return;
      ev.preventDefault();
      setDraggingNovel(true);
    };
    const onDragLeave = (ev: DragEvent) => {
      if (ev.relatedTarget === null) setDraggingNovel(false);
    };
    const onDrop = (ev: DragEvent) => {
      if (!ev.dataTransfer) return;
      ev.preventDefault();
      setDraggingNovel(false);
      const paths = pathsFromDataTransfer(ev.dataTransfer);
      if (paths.length) importSources(paths).catch((e) => setImportNotice(String(e)));
    };
    window.addEventListener("dragover", onDragOver);
    window.addEventListener("dragleave", onDragLeave);
    window.addEventListener("drop", onDrop);
    return () => {
      window.removeEventListener("dragover", onDragOver);
      window.removeEventListener("dragleave", onDragLeave);
      window.removeEventListener("drop", onDrop);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canImportNovel, root.path]);

  function openContextMenu(ev: React.MouseEvent, entry: SkillTreeEntry | null) {
    ev.preventDefault();
    ev.stopPropagation();
    if (entry) setFocusedPath(entry.path);
    setMenu({
      x: Math.min(ev.clientX, Math.max(0, window.innerWidth - 260)),
      y: Math.min(ev.clientY, Math.max(0, window.innerHeight - 360)),
      entry,
    });
  }

  async function runMenuAction(action: () => Promise<void> | void) {
    setMenu(null);
    try {
      await action();
    } catch (e) {
      window.alert(String(e));
    }
  }

  async function createEntry(parentEntry: SkillTreeEntry | null, kind: "file" | "folder") {
    const label = kind === "file" ? t("files.newFile") : t("files.newFolder");
    const name = window.prompt(t("files.createPrompt", { label }));
    if (!name) return;
    const parent = contextParentRel(parentEntry);
    const rel = await createWorkEntry(root.path, parent, name, kind);
    setCollapsedDirs((prev) => {
      const next = new Set(prev);
      if (parent) next.delete(parent);
      return next;
    });
    if (kind === "file") openFileTab(rel, true);
    else setFocusedPath(rel);
    refreshFiles();
  }

  async function renameEntry(entry: SkillTreeEntry) {
    if (editorDirty && (sel === entry.path || sel.startsWith(`${entry.path}/`))) {
      const ok = window.confirm(t("files.discardUnsavedConfirm", { path: sel }));
      if (!ok) return;
      setEditorDirty(false);
    }
    const nextName = window.prompt(t("files.renamePrompt"), entry.name);
    if (!nextName || nextName === entry.name) return;
    const nextRel = await renameWorkEntry(root.path, entry.path, nextName);
    renameOpenTabs(entry, nextRel);
    refreshFiles();
  }

  async function deleteEntry(entry: SkillTreeEntry) {
    if (editorDirty && (sel === entry.path || sel.startsWith(`${entry.path}/`))) {
      const ok = window.confirm(t("files.discardUnsavedConfirm", { path: sel }));
      if (!ok) return;
      setEditorDirty(false);
    }
    const ok = window.confirm(t("files.deleteConfirm", { path: entry.path }));
    if (!ok) return;
    await deleteWorkEntry(root.path, entry.path);
    removeEntryTabs(entry);
    if (focusedPath === entry.path || focusedPath.startsWith(`${entry.path}/`)) setFocusedPath("");
    refreshFiles();
  }

  const visibleTree = useMemo(() => visibleEntries(tree, collapsedDirs), [tree, collapsedDirs]);
  const treeViewport = treeViewportHeight || 480;
  const treeStartIndex = Math.max(0, Math.floor(treeScrollTop / TREE_ROW_HEIGHT) - TREE_OVERSCAN);
  const treeEndIndex = Math.min(
    visibleTree.length,
    Math.ceil((treeScrollTop + treeViewport) / TREE_ROW_HEIGHT) + TREE_OVERSCAN,
  );
  const virtualRows = useMemo(
    () =>
      visibleTree
        .slice(treeStartIndex, treeEndIndex)
        .map((entry, offset) => ({ entry, index: treeStartIndex + offset })),
    [treeEndIndex, treeStartIndex, visibleTree],
  );
  const virtualTreeHeight = visibleTree.length * TREE_ROW_HEIGHT;
  const selEntry = useMemo(() => entryForPath(sel), [treeByPath, sel]);
  const kind = selEntry ? previewKind(selEntry.name) : "";
  const abs = selEntry ? `${root.path}/${selEntry.path}` : "";
  const previewVersion = selEntry
    ? `${selEntry.path}:${selEntry.size ?? "unknown"}:${selEntry.mtime ?? "unknown"}`
    : "";
  const mediaSrc = (path: string) => {
    const url = kind === "video" ? videoUrl(path) : mediaUrl(path);
    return url ? `${url}&v=${encodeURIComponent(previewVersion)}` : "";
  };

  useEffect(() => {
    const symbolText = kind === "img" || kind === "video" || kind === "audio" || kind === "docx" ? "" : text;
    editorDocumentStore.setDocument(selEntry?.path ?? "", symbolText);
  }, [editorDocumentStore, kind, selEntry?.path, text]);

  useEffect(() => {
    window.dispatchEvent(
      new CustomEvent("anime-armory:file-status", {
        detail: selEntry
          ? {
              root: root.path,
              path: selEntry.path,
              name: selEntry.name,
              kind,
              ext: ext(selEntry.name),
              size: selEntry.size ?? null,
              dirty: editorDirty,
            }
          : {
              root: root.path,
              path: "",
              name: "",
              kind: "",
              ext: "",
              size: null,
              dirty: false,
            },
      }),
    );
  }, [editorDirty, kind, root.path, selEntry?.name, selEntry?.path, selEntry?.size]);

  useEffect(() => {
    if (kind !== "img") return;
    const el = imageStageRef.current;
    if (!el) return;
    const measure = () => {
      setImageViewport({ width: el.clientWidth, height: el.clientHeight });
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    window.addEventListener("resize", measure);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [kind, previewVersion]);

  useEffect(() => {
    setImageZoom(1);
    setImageNatural(null);
  }, [kind, previewVersion]);

  const imageBaseScale = useMemo(() => {
    if (!imageNatural || imageViewport.width <= 0 || imageViewport.height <= 0) return 1;
    const innerWidth = Math.max(1, imageViewport.width - IMAGE_STAGE_PADDING);
    const innerHeight = Math.max(1, imageViewport.height - IMAGE_STAGE_PADDING);
    return Math.max(0.01, Math.min(1, innerWidth / imageNatural.width, innerHeight / imageNatural.height));
  }, [imageNatural, imageViewport.height, imageViewport.width]);
  const imageDisplayScale = imageBaseScale * imageZoom;
  const imageDisplaySize = imageNatural
    ? {
        width: Math.max(1, Math.round(imageNatural.width * imageDisplayScale)),
        height: Math.max(1, Math.round(imageNatural.height * imageDisplayScale)),
      }
    : null;
  const imageFrameStyle: CSSProperties | undefined = imageDisplaySize
    ? {
        width: Math.max(imageDisplaySize.width, Math.max(0, imageViewport.width - IMAGE_STAGE_PADDING)),
        height: Math.max(imageDisplaySize.height, Math.max(0, imageViewport.height - IMAGE_STAGE_PADDING)),
      }
    : undefined;
  const imageStyle: CSSProperties | undefined = imageDisplaySize
    ? { width: imageDisplaySize.width, height: imageDisplaySize.height }
    : undefined;
  const imageZoomPercent = Math.round(imageZoom * 100);

  function zoomImage(multiplier: number) {
    setImageZoom((value) => clampImageZoom(value * multiplier));
  }

  function resetImageZoom() {
    setImageZoom(1);
  }

  function onImageWheel(event: WheelEvent<HTMLDivElement>) {
    if (!event.ctrlKey && !event.metaKey) return;
    event.preventDefault();
    zoomImage(event.deltaY < 0 ? 1.12 : 1 / 1.12);
  }

  useEffect(() => {
    if (kind !== "img" && kind !== "video" && kind !== "audio") return;
    ensureMedia()
      .then(() => mediaAllowRoot(root.path))
      .catch(() => {});
  }, [kind, root.path]);

  // Load text-like files into Monaco; docx uses a backend document parser.
  // Media files stream straight from the media server.
  useEffect(() => {
    setErr("");
    if (!selEntry || selEntry.truncated || kind === "img" || kind === "video" || kind === "audio") return;
    const cacheKey = `${root.path}\0${previewVersion}`;
    const cached = previewCacheRef.current.get(cacheKey);
    if (cached !== undefined) {
      previewCacheRef.current.delete(cacheKey);
      previewCacheRef.current.set(cacheKey, cached);
      setText(cached);
      return;
    }
    setText("");
    let alive = true;
    const reader = kind === "docx" ? readWorkDocx : readWorkFile;
    reader(root.path, selEntry.path)
      .then((s) => {
        if (!alive) return;
        setText(s);
        if (s.length <= PREVIEW_CACHE_TEXT_LIMIT) {
          const cache = previewCacheRef.current;
          cache.set(cacheKey, s);
          while (cache.size > PREVIEW_CACHE_LIMIT) {
            const first = cache.keys().next().value;
            if (first === undefined) break;
            cache.delete(first);
          }
        }
      })
      .catch((e) => alive && setErr(String(e)));
    return () => {
      alive = false;
    };
  }, [root.path, previewVersion, kind]);

  function toggleDir(path: string) {
    setCollapsedDirs((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
        const page = dirPagesRef.current.get(path);
        if (!page || page.loaded === 0) loadDirectory(path, 0, true).catch(() => {});
      } else {
        next.add(path);
      }
      collapsedDirsRef.current = next;
      return next;
    });
  }

  function activateEntry(entry: SkillTreeEntry) {
    if (isLoadMoreEntry(entry)) {
      const dir = parentRel(entry.path);
      const page = dirPages.get(dir);
      if (page && !page.loading && page.hasMore) {
        loadDirectory(dir, page.loaded, false).catch(() => {});
      }
      return;
    }
    if (entry.truncated) return;
    if (entry.is_dir) {
      setFocusedPath(entry.path);
      toggleDir(entry.path);
      return;
    }
    openFileTab(entry.path, false);
  }

  function pinEntryTab(entry: SkillTreeEntry) {
    if (entry.truncated || entry.is_dir || isLoadMoreEntry(entry)) return;
    openFileTab(entry.path, true);
  }

  function onEntryKeyDown(e: React.KeyboardEvent<HTMLDivElement>, entry: SkillTreeEntry) {
    if (e.key !== "Enter" && e.key !== " ") return;
    e.preventDefault();
    activateEntry(entry);
  }

  function startSideResize(ev: React.PointerEvent<HTMLDivElement>) {
    const pane = paneRef.current;
    if (!pane) return;
    ev.preventDefault();
    const splitter = ev.currentTarget;
    const rect = pane.getBoundingClientRect();
    document.body.classList.add("resizing-files-side");
    splitter.classList.add("resizing");
    let latestWidth = sideWidth ?? 280;

    const move = (e: PointerEvent) => {
      const next = clampFilesSideWidth(e.clientX - rect.left, rect.width);
      latestWidth = next;
      setSideWidth(next);
      draftFilesSideWidth(next);
      scheduleWindowResizeEvent();
    };
    const up = () => {
      document.body.classList.remove("resizing-files-side");
      splitter.classList.remove("resizing");
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", up);
      if (latestWidth <= FILES_SIDE_COLLAPSE_WIDTH) {
        setSideWidth(null);
        clearStoredFilesSideWidth();
        window.dispatchEvent(new Event(COLLAPSE_LEFT_SIDEBAR_EVENT));
      } else {
        const committed = commitFilesSideWidth(latestWidth);
        if (committed != null) setSideWidth(committed);
      }
      scheduleWindowResizeEvent();
    };
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", up);
  }

  const menuEntry = menu?.entry ?? null;
  const menuRel = menuEntry?.path ?? "";
  const menuAbs = absPath(menuRel);
  const menuCanCreate = !menuEntry || menuEntry.is_dir;
  const filesSideStyle = sideWidth != null ? { width: sideWidth, flexBasis: sideWidth } : undefined;

  return (
    <div
      className={
        "files-pane" +
        (sideVisible ? "" : " files-pane-side-hidden") +
        (reserveSide ? " files-pane-side-reserved" : "") +
        (canImportNovel && draggingNovel ? " dragging-import" : "")
      }
      ref={paneRef}
      onDragOver={(event) => {
        if (!canImportNovel) return;
        event.preventDefault();
        setDraggingNovel(true);
      }}
      onDragLeave={(event) => {
        if (!canImportNovel || event.currentTarget.contains(event.relatedTarget as Node | null)) return;
        setDraggingNovel(false);
      }}
      onDrop={(event) => {
        if (!canImportNovel) return;
        event.preventDefault();
        const paths = pathsFromDataTransfer(event.dataTransfer);
        if (paths.length) {
          importSources(paths).catch((e) => setImportNotice(String(e)));
        } else {
          setImportNotice(t("files.importDropPathUnavailable"));
        }
      }}
    >
      {sideVisible && (
        <>
          <div className="files-side" style={filesSideStyle}>
            <div
              className="files-tree"
              role="tree"
              ref={treeScrollRef}
              onScroll={(event) => setTreeScrollTop(event.currentTarget.scrollTop)}
              onContextMenu={(event) => openContextMenu(event, null)}
            >
              {tree.length === 0 && (
                <div className={"files-empty" + (canImportNovel ? " import-empty" : "")}>
                  {canImportNovel ? (
                    <>
                      <div className="import-empty-title">{t("files.importNovelTitle")}</div>
                      <div className="import-empty-hint">{t("files.importNovelHint")}</div>
                      <button type="button" className="import-file-btn" disabled={importing} onClick={chooseNovelFiles}>
                        {importing ? t("files.importing") : t("files.importNovelButton")}
                      </button>
                      {importNotice && <div className="import-empty-notice">{importNotice}</div>}
                    </>
                  ) : (
                    t("common.emptyDir")
                  )}
                </div>
              )}
              {tree.length > 0 && (
                <div className="files-tree-spacer" style={{ height: virtualTreeHeight }}>
                  {virtualRows.map(({ entry: e, index }) => {
                    if (e.truncated) {
                      return (
                        <div
                          key={e.path}
                          className="tree-line tree-limit"
                          style={{ transform: `translateY(${index * TREE_ROW_HEIGHT}px)` }}
                          role="note"
                          title={t("files.treeCapped", { count: e.size ?? visibleTree.length })}
                        >
                          <span className="tree-disclosure placeholder" aria-hidden="true" />
                          <span className="tree-label">
                            {t("files.treeCapped", { count: e.size ?? visibleTree.length })}
                          </span>
                        </div>
                      );
                    }
                    const collapsed = e.is_dir && collapsedDirs.has(e.path);
                    const active = e.path === sel || e.path === focusedPath;
                    const decoration = treeDecorations.get(e.path);
                    return (
                      <div
                        key={e.path}
                        className={
                          "tree-line" +
                          (e.is_dir ? " dir" : "") +
                          (active ? " active" : "") +
                          (decoration ? ` decorated decoration-${decoration.kind}` : "")
                        }
                        style={{
                          ...treeGuideStyle(e.depth),
                          paddingLeft: TREE_BASE_PADDING + e.depth * TREE_INDENT,
                          transform: `translateY(${index * TREE_ROW_HEIGHT}px)`,
                        }}
                        onClick={() => activateEntry(e)}
                        onDoubleClick={() => pinEntryTab(e)}
                        onContextMenu={(event) => openContextMenu(event, e)}
                        onKeyDown={(event) => onEntryKeyDown(event, e)}
                        role="treeitem"
                        aria-expanded={e.is_dir ? !collapsed : undefined}
                        aria-selected={active}
                        tabIndex={0}
                        title={e.is_dir ? undefined : e.path}
                      >
                        <span
                          className={
                            "tree-disclosure" + (e.is_dir ? (collapsed ? " collapsed" : " expanded") : " placeholder")
                          }
                          aria-hidden="true"
                        />
                        <WorkFileIcon entry={e} collapsed={collapsed} />
                        <span className="tree-label">{e.name}</span>
                        {decoration && (
                          <span
                            className={"tree-decoration" + (e.is_dir || decoration.rollup ? " rollup" : "")}
                            title={decorationTitle(t, e, decoration)}
                            aria-label={decorationTitle(t, e, decoration)}
                          >
                            {e.is_dir || decoration.rollup ? "" : decoration.marker}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
          <div
            className="files-splitter"
            role="separator"
            aria-orientation="vertical"
            aria-label={t("files.resizeAria")}
            onPointerDown={startSideResize}
            onDoubleClick={() => {
              setSideWidth(null);
              clearStoredFilesSideWidth();
              scheduleWindowResizeEvent();
            }}
          />
        </>
      )}
      <div className="files-preview">
        {tabs.length > 0 && (
          <div className="files-editor-tabs" role="tablist" aria-label={t("files.openEditors")}>
            {tabs.map((editorTab) => {
              const tabEntry = entryForPath(editorTab.path);
              if (!tabEntry) return null;
              const activeTab = editorTab.path === sel;
              const decoration = treeDecorations.get(editorTab.path);
              return (
                <div
                  key={editorTab.path}
                  className={
                    "files-editor-tab" +
                    (activeTab ? " active" : "") +
                    (editorTab.pinned ? "" : " preview") +
                    (decoration ? ` decoration-${decoration.kind}` : "")
                  }
                  role="tab"
                  aria-selected={activeTab}
                  tabIndex={0}
                  title={editorTab.path}
                  onClick={() => openFileTab(editorTab.path, editorTab.pinned)}
                  onDoubleClick={() => openFileTab(editorTab.path, true)}
                  onKeyDown={(event) => {
                    if (event.key !== "Enter" && event.key !== " ") return;
                    event.preventDefault();
                    openFileTab(editorTab.path, editorTab.pinned);
                  }}
                >
                  <WorkFileIcon entry={tabEntry} collapsed />
                  <span className="editor-tab-label">{tabEntry.name}</span>
                  {decoration && !tabEntry.is_dir && (
                    <span className="editor-tab-decoration" title={decorationTitle(t, tabEntry, decoration)}>
                      {decoration.marker}
                    </span>
                  )}
                  <button
                    type="button"
                    className="editor-tab-close"
                    aria-label={t("files.closeEditor", { path: editorTab.path })}
                    title={t("files.closeEditor", { path: editorTab.path })}
                    onClick={(event) => {
                      event.stopPropagation();
                      closeEditorTab(editorTab.path);
                    }}
                  >
                    <Codicon name="close" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
        {selEntry && (
          <EditorBreadcrumbs
            rootName={root.name}
            rootPath={root.path}
            entry={selEntry}
            documentStore={editorDocumentStore}
            contentVersion={previewVersion}
            directoryVersion={`${refreshKey}:${localRefresh}`}
            cursorStore={editorCursorStore}
            onOpenFile={(path) => openFileTab(path, true)}
            onNavigateLine={(line) => {
              setEditorNavigation((current) => ({ line, request: (current?.request ?? 0) + 1 }));
            }}
          />
        )}
        <div className="files-preview-content">
          {!selEntry ? (
            <div className="files-editor-empty">
              <div className="files-editor-empty-title">{t("files.emptyEditorTitle")}</div>
              <div className="files-editor-empty-hint">{t("files.emptyEditorHint")}</div>
            </div>
          ) : kind === "img" ? (
            <div className="files-image-preview">
              <div className="files-image-toolbar">
                <span className="files-image-title" title={selEntry.path}>{selEntry.name}</span>
                <div className="files-image-controls">
                  <button
                    type="button"
                    aria-label={t("files.zoomOut")}
                    title={t("files.zoomOut")}
                    disabled={!imageNatural || imageZoom <= IMAGE_ZOOM_MIN}
                    onClick={() => zoomImage(1 / 1.2)}
                  >
                    −
                  </button>
                  <button
                    type="button"
                    className="files-image-zoom-value"
                    aria-label={t("files.zoomReset")}
                    title={t("files.zoomReset")}
                    disabled={!imageNatural}
                    onClick={resetImageZoom}
                  >
                    {imageZoomPercent}%
                  </button>
                  <button
                    type="button"
                    aria-label={t("files.zoomIn")}
                    title={t("files.zoomIn")}
                    disabled={!imageNatural || imageZoom >= IMAGE_ZOOM_MAX}
                    onClick={() => zoomImage(1.2)}
                  >
                    +
                  </button>
                </div>
              </div>
              <div className="files-media files-image-stage" ref={imageStageRef} onWheel={onImageWheel}>
                {abs && (
                  <div className="files-image-frame" style={imageFrameStyle}>
                    <DecodedImage
                      className="files-zoom-image"
                      src={mediaSrc(abs)}
                      alt={selEntry.name}
                      style={imageStyle}
                      loading="eager"
                      onDecoded={(metadata) => {
                        setImageNatural({
                          width: metadata.width,
                          height: metadata.height,
                        });
                      }}
                    />
                  </div>
                )}
              </div>
            </div>
          ) : kind === "video" ? (
            <div className="files-media">{abs && <VideoPreview src={mediaSrc(abs)} />}</div>
          ) : kind === "audio" ? (
            <div className="files-media"><audio src={mediaSrc(abs)} controls /></div>
          ) : err ? (
            <div className="files-empty">{t("files.previewFailed", { error: err })}</div>
          ) : kind === "docx" ? (
            <div className="files-document-preview">
              <div className="files-document-toolbar">
                <WorkFileIcon entry={selEntry} collapsed />
                <span className="files-document-title" title={selEntry.path}>{selEntry.name}</span>
                <span className="files-document-badge">{t("files.docxReadonly")}</span>
              </div>
              {text ? (
                <pre className="files-document-text">{text}</pre>
              ) : (
                <div className="files-empty">{t("common.loading")}</div>
              )}
            </div>
          ) : (
            <Suspense fallback={<div className="files-empty">{t("common.loading")}</div>}>
              <MonacoFileEditor
                rootPath={root.path}
                entry={selEntry}
                absPath={abs}
                text={text}
                loadVersion={previewVersion}
                expectedMtime={selEntry.mtime ?? 0}
                navigateTo={editorNavigation}
                onCursorLineChange={editorCursorStore.setLine}
                onContentChange={(value) => editorDocumentStore.setDocument(selEntry.path, value)}
                onDirtyChange={setEditorDirty}
                onSaved={(_, savedText) => {
                  setText(savedText);
                  previewCacheRef.current.clear();
                  refreshFiles();
                }}
              />
            </Suspense>
          )}
        </div>
      </div>
      {menu && (
        <div
          className="file-context-menu"
          style={{ left: menu.x, top: menu.y }}
          onClick={(event) => event.stopPropagation()}
          onContextMenu={(event) => event.preventDefault()}
          role="menu"
        >
          {menuCanCreate && (
            <>
              <button
                type="button"
                role="menuitem"
                onClick={() => runMenuAction(() => createEntry(menuEntry, "file"))}
              >
                {t("files.menuNewFile")}
              </button>
              <button
                type="button"
                role="menuitem"
                onClick={() => runMenuAction(() => createEntry(menuEntry, "folder"))}
              >
                {t("files.menuNewFolder")}
              </button>
              <div className="ctx-sep" />
            </>
          )}
          <button
            type="button"
            role="menuitem"
            onClick={() => runMenuAction(() => revealWorkEntry(root.path, menuRel))}
          >
            {t("files.menuReveal")}
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={() => runMenuAction(() => openWorkEntry(root.path, menuRel))}
          >
            {menuEntry?.is_dir || !menuEntry ? t("files.menuOpenFolder") : t("files.menuOpen")}
          </button>
          {onOpenTerminal && (
            <button
              type="button"
              role="menuitem"
              onClick={() => runMenuAction(() => onOpenTerminal(`cd ${shellQuote(entryTerminalDir(menuEntry))}`))}
            >
              {t("files.menuOpenTerminal")}
            </button>
          )}
          <div className="ctx-sep" />
          {menuEntry && (
            <button
              type="button"
              role="menuitem"
              onClick={() => runMenuAction(() => copyText(menuEntry.name))}
            >
              {t("files.menuCopyName")}
            </button>
          )}
          <button type="button" role="menuitem" onClick={() => runMenuAction(() => copyText(menuAbs))}>
            {t("files.menuCopyPath")}
          </button>
          {menuEntry && (
            <button type="button" role="menuitem" onClick={() => runMenuAction(() => copyText(menuRel))}>
              {t("files.menuCopyRelativePath")}
            </button>
          )}
          {menuEntry && (
            <>
              <div className="ctx-sep" />
              <button
                type="button"
                role="menuitem"
                onClick={() => runMenuAction(() => renameEntry(menuEntry))}
              >
                {t("files.menuRename")}
              </button>
              <button
                type="button"
                role="menuitem"
                className="danger"
                onClick={() => runMenuAction(() => deleteEntry(menuEntry))}
              >
                {t("files.menuDelete")}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
