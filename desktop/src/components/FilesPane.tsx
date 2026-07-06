import { lazy, Suspense, useEffect, useMemo, useRef, useState, useSyncExternalStore, type CSSProperties } from "react";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import { open } from "@tauri-apps/plugin-dialog";
import {
  createWorkEntry,
  deleteWorkEntry,
  ensureMedia,
  getMediaPort,
  importWorkSources,
  mediaAllowRoot,
  mediaUrl,
  openWorkEntry,
  readWorkFile,
  renameWorkEntry,
  revealWorkEntry,
  subscribeMediaPort,
  workDeleted,
  workDir,
} from "../api";
import { useI18n } from "../i18n";
import { activeSkin, type FileIconKind } from "../skins";
import type { SkillTreeEntry, WorkRoot } from "../types";

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
const TREE_ROW_HEIGHT = 24;
const TREE_BASE_PADDING = 8;
const TREE_INDENT = 14;
const TREE_OVERSCAN = 12;
const TREE_PAGE_LIMIT = 500;
const PREVIEW_CACHE_LIMIT = 4;
const PREVIEW_CACHE_TEXT_LIMIT = 96 * 1024;
const NOVEL_IMPORT_EXTENSIONS = ["txt", "md", "markdown", "mdx", "docx", "pdf"];
const NOVEL_IMPORT_EXTENSIONS_SET = new Set(NOVEL_IMPORT_EXTENSIONS);

type PreviewKind = "img" | "video" | "audio" | "markdown" | "json" | "text";
type ContextMenuState = { x: number; y: number; entry: SkillTreeEntry | null };
type DirPageState = { loaded: number; total: number; hasMore: boolean; loading?: boolean };

function ext(name: string): string {
  const i = name.lastIndexOf(".");
  return i < 0 ? "" : name.slice(i + 1).toLowerCase();
}

function parentRel(path: string): string {
  const i = path.lastIndexOf("/");
  return i < 0 ? "" : path.slice(0, i);
}

function shellQuote(value: string): string {
  return `'${value.replace(/'/g, `'\\''`)}'`;
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
  return "text";
}

function FileGlyph({ kind, label }: { kind: FileIconKind; label?: string }) {
  if (kind === "video") {
    return (
      <svg viewBox="0 0 18 18" className="seti-svg seti-video" aria-hidden="true">
        <circle cx="9" cy="9" r="8" />
        <path d="M7 5.2 12.2 9 7 12.8Z" />
      </svg>
    );
  }
  if (kind === "image") {
    return (
      <svg viewBox="0 0 18 18" className="seti-svg seti-image" aria-hidden="true">
        <rect x="2.5" y="3" width="13" height="12" rx="1.2" />
        <circle cx="6" cy="6.6" r="1.1" />
        <path d="M4 13 7.2 9.4l2.2 2.3 1.5-1.8L14 13Z" />
      </svg>
    );
  }
  if (kind === "generic") {
    return (
      <svg viewBox="0 0 18 18" className="seti-svg seti-generic" aria-hidden="true">
        <path d="M4 2.5h6.5L14 6v9.5H4Z" />
        <path d="M10.5 2.5V6H14" />
      </svg>
    );
  }
  return <span className="seti-text-icon">{label}</span>;
}

function TreeIcon({ entry, collapsed }: { entry: SkillTreeEntry; collapsed: boolean }) {
  if (entry.is_dir) {
    return (
      <span
        className={"tree-icon folder-icon" + (collapsed ? "" : " open")}
        aria-hidden="true"
      />
    );
  }
  const meta = activeSkin.fileIcon(entry);
  return (
    <span className={`tree-icon file-icon ${meta.cls}`} aria-hidden="true">
      <FileGlyph kind={meta.kind} label={meta.label} />
    </span>
  );
}

function hasChangeStatus(status?: string): boolean {
  return status === "u" || status === "m";
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

export function FilesPane({
  root,
  refreshKey,
  initialChangeCount,
  allowNovelImport = false,
  active = true,
  onImported,
  onOpenTerminal,
}: {
  root: WorkRoot;
  refreshKey: number;
  initialChangeCount?: number;
  allowNovelImport?: boolean;
  active?: boolean;
  onImported?: () => void;
  onOpenTerminal?: (command?: string) => void;
}) {
  const { t } = useI18n();
  const paneRef = useRef<HTMLDivElement>(null);
  const treeScrollRef = useRef<HTMLDivElement>(null);
  const previewCacheRef = useRef<Map<string, string>>(new Map());
  const collapseInitializedRef = useRef(false);
  const dirPagesRef = useRef<Map<string, DirPageState>>(new Map());
  const collapsedDirsRef = useRef<Set<string>>(new Set());
  const [tree, setTree] = useState<SkillTreeEntry[]>([]);
  const [dirPages, setDirPages] = useState<Map<string, DirPageState>>(() => new Map());
  const [deleted, setDeleted] = useState<string[]>([]);
  const [collapsedDirs, setCollapsedDirs] = useState<Set<string>>(() => new Set());
  const [treeScrollTop, setTreeScrollTop] = useState(0);
  const [treeViewportHeight, setTreeViewportHeight] = useState(0);
  const [sel, setSel] = useState<string>(""); // selected file's rel path
  const [text, setText] = useState<string>("");
  const [err, setErr] = useState<string>("");
  const [importNotice, setImportNotice] = useState<string>("");
  const [importing, setImporting] = useState(false);
  const [draggingNovel, setDraggingNovel] = useState(false);
  const [editorDirty, setEditorDirty] = useState(false);
  const [menu, setMenu] = useState<ContextMenuState | null>(null);
  const [localRefresh, setLocalRefresh] = useState(0); // bump after file operations (no fs event)
  const [sideWidth, setSideWidth] = useState<number | null>(() => {
    const saved = Number(window.localStorage.getItem("aa.files.sideWidth"));
    return Number.isFinite(saved) && saved > 0 ? saved : null;
  });
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

  function clampSideWidth(width: number, total: number): number {
    const minSide = total < 500 ? 160 : 220;
    const minPreview = Math.min(320, Math.max(180, total * 0.35));
    const maxSide = Math.max(minSide, total - minPreview);
    return Math.min(maxSide, Math.max(minSide, width));
  }

  useEffect(() => {
    if (sideWidth == null) return;
    const sync = () => {
      const pane = paneRef.current;
      if (!pane) return;
      const rect = pane.getBoundingClientRect();
      const next = clampSideWidth(sideWidth, rect.width);
      if (Math.round(next) !== Math.round(sideWidth)) setSideWidth(next);
    };
    sync();
    window.addEventListener("resize", sync);
    return () => window.removeEventListener("resize", sync);
  }, [sideWidth]);

  useEffect(() => {
    setCollapsedDirs(new Set());
    setSel("");
    setText("");
    setErr("");
    setImportNotice("");
    setImporting(false);
    setDraggingNovel(false);
    setEditorDirty(false);
    setTree([]);
    setDirPages(new Map());
    setDeleted([]);
    setTreeScrollTop(0);
    treeScrollRef.current?.scrollTo({ top: 0 });
    previewCacheRef.current.clear();
    collapseInitializedRef.current = false;
  }, [root.path]);

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

  async function loadDirectory(dir: string, offset = 0, replace = offset === 0): Promise<void> {
    setDirPages((prev) => {
      const next = new Map(prev);
      const old = next.get(dir);
      next.set(dir, { loaded: old?.loaded ?? 0, total: old?.total ?? 0, hasMore: old?.hasMore ?? false, loading: true });
      return next;
    });
    const listing = await workDir(root.path, dir, offset, TREE_PAGE_LIMIT);
    const loaded = listing.offset + listing.entries.length;
    const page: DirPageState = {
      loaded,
      total: listing.total,
      hasMore: listing.has_more,
      loading: false,
    };
    const incoming = listing.has_more ? [...listing.entries, makeLoadMoreEntry(dir, page)] : listing.entries;
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
      return next;
    });
  }

  useEffect(() => {
    let alive = true;
    const timer = window.setTimeout(() => {
      const reload = async () => {
        const loadedOpenDirs = [...dirPagesRef.current.keys()]
          .filter((dir) => dir && !collapsedDirsRef.current.has(dir))
          .sort((a, b) => directChildDepth(a) - directChildDepth(b));
        const [listing, nextDeleted] = await Promise.all([
          workDir(root.path, "", 0, TREE_PAGE_LIMIT).catch(() => ({ entries: [], total: 0, offset: 0, limit: TREE_PAGE_LIMIT, has_more: false })),
          workDeleted(root.path).catch(() => [] as string[]),
        ]);
        if (!alive) return;
        const rootPage: DirPageState = {
          loaded: listing.entries.length,
          total: listing.total,
          hasMore: listing.has_more,
        };
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
          }
        }
        setTree(nextTree);
        setDirPages(nextPages);
        setDeleted(nextDeleted);
        if (!collapseInitializedRef.current) {
          collapseInitializedRef.current = true;
          setCollapsedDirs(new Set(listing.entries.filter((e) => e.is_dir && e.depth === 0).map((e) => e.path)));
        }
      };
      reload();
    }, 120);
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [root.path, refreshKey, localRefresh]);

  const changedFileCount = useMemo(
    () => tree.filter((e) => !e.is_dir && !e.truncated && hasChangeStatus(e.status)).length,
    [tree],
  );
  const scannedChangeCount = changedFileCount + deleted.length;
  const changeCount = initialChangeCount ?? scannedChangeCount;

  function absPath(rel: string): string {
    return rel ? `${root.path}/${rel}` : root.path;
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
      const imported = await importWorkSources(root.path, usable);
      if (imported[0]) setSel(imported[0]);
      setImportNotice(t("files.importedNovel", { count: imported.length }));
      refreshFiles();
      onImported?.();
    } catch (e) {
      setImportNotice(String(e));
    } finally {
      setImporting(false);
      setDraggingNovel(false);
    }
  }

  async function chooseNovelFiles() {
    if (importing) return;
    const picked = await open({
      multiple: true,
      directory: false,
      filters: [
        {
          name: t("files.importDialogName"),
          extensions: NOVEL_IMPORT_EXTENSIONS,
        },
      ],
    });
    const paths = Array.isArray(picked) ? picked : picked ? [picked] : [];
    if (paths.length) await importSources(paths);
  }

  function pathsFromDataTransfer(dataTransfer: DataTransfer): string[] {
    return Array.from(dataTransfer.files)
      .map((file) => (file as File & { path?: string }).path || "")
      .filter(Boolean);
  }

  const canImportNovel = active && allowNovelImport && tree.length === 0;

  useEffect(() => {
    if (!canImportNovel) return;
    const webview = getCurrentWebview();
    let unlisten: (() => void) | null = null;
    webview.onDragDropEvent((event) => {
      if (event.payload.type === "enter" || event.payload.type === "over") {
        setDraggingNovel(true);
      } else if (event.payload.type === "leave") {
        setDraggingNovel(false);
      } else if (event.payload.type === "drop") {
        setDraggingNovel(false);
        importSources(event.payload.paths).catch((e) => setImportNotice(String(e)));
      }
    }).then((fn) => {
      unlisten = fn;
    }).catch(() => {});
    return () => {
      unlisten?.();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canImportNovel, root.path]);

  function openContextMenu(ev: React.MouseEvent, entry: SkillTreeEntry | null) {
    ev.preventDefault();
    ev.stopPropagation();
    if (entry && !entry.is_dir) setSel(entry.path);
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
    if (kind === "file") setSel(rel);
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
    if (sel === entry.path) setSel(entry.is_dir ? "" : nextRel);
    else if (entry.is_dir && sel.startsWith(`${entry.path}/`)) setSel("");
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
    if (sel === entry.path || sel.startsWith(`${entry.path}/`)) setSel("");
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
  const selEntry = useMemo(() => tree.find((e) => e.path === sel) || null, [tree, sel]);
  const kind = selEntry ? previewKind(selEntry.name) : "";
  const abs = selEntry ? `${root.path}/${selEntry.path}` : "";
  const previewVersion = selEntry
    ? `${selEntry.path}:${selEntry.size ?? "unknown"}:${selEntry.mtime ?? "unknown"}`
    : "";
  const mediaRevision = refreshKey + localRefresh;
  const mediaSrc = (path: string) => {
    const url = mediaUrl(path);
    return url ? `${url}&v=${mediaRevision}` : "";
  };

  useEffect(() => {
    if (kind !== "img" && kind !== "video" && kind !== "audio") return;
    ensureMedia()
      .then(() => mediaAllowRoot(root.path))
      .catch(() => {});
  }, [kind, root.path]);

  // load text into Monaco; image/video/audio stream straight from the media server
  useEffect(() => {
    setErr("");
    setText("");
    if (!selEntry || selEntry.truncated || kind === "img" || kind === "video" || kind === "audio") return;
    const cacheKey = `${root.path}\0${previewVersion}`;
    const cached = previewCacheRef.current.get(cacheKey);
    if (cached !== undefined) {
      previewCacheRef.current.delete(cacheKey);
      previewCacheRef.current.set(cacheKey, cached);
      setText(cached);
      return;
    }
    let alive = true;
    readWorkFile(root.path, selEntry.path)
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
        const page = dirPages.get(path);
        if (!page || page.loaded === 0) loadDirectory(path, 0, true).catch(() => {});
      } else {
        next.add(path);
      }
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
      toggleDir(entry.path);
      return;
    }
    if (editorDirty && entry.path !== sel) {
      const ok = window.confirm(t("files.discardUnsavedConfirm", { path: sel }));
      if (!ok) return;
      setEditorDirty(false);
    }
    setSel(entry.path);
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
    const rect = pane.getBoundingClientRect();
    document.body.classList.add("resizing-files-side");

    const move = (e: PointerEvent) => {
      const next = clampSideWidth(e.clientX - rect.left, rect.width);
      setSideWidth(next);
      window.localStorage.setItem("aa.files.sideWidth", String(Math.round(next)));
      window.dispatchEvent(new Event("resize"));
    };
    const up = () => {
      document.body.classList.remove("resizing-files-side");
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", up);
      window.dispatchEvent(new Event("resize"));
    };
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", up);
  }

  const menuEntry = menu?.entry ?? null;
  const menuRel = menuEntry?.path ?? "";
  const menuAbs = absPath(menuRel);
  const menuCanCreate = !menuEntry || menuEntry.is_dir;

  return (
    <div
      className={"files-pane" + (canImportNovel && draggingNovel ? " dragging-import" : "")}
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
      <div className="files-side" style={sideWidth ? { width: sideWidth } : undefined}>
        <div className="files-toolbar">
          <span className={"files-change-count" + (changeCount ? " dirty" : "")}>
            {changeCount ? t("files.changeCount", { count: changeCount }) : t("files.noChanges")}
          </span>
        </div>
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
                return (
                  <div
                    key={e.path}
                    className={
                      "tree-line" + (e.is_dir ? " dir" : "") + (e.path === sel ? " active" : "")
                    }
                    style={{
                      ...treeGuideStyle(e.depth),
                      paddingLeft: TREE_BASE_PADDING + e.depth * TREE_INDENT,
                      transform: `translateY(${index * TREE_ROW_HEIGHT}px)`,
                    }}
                    onClick={() => activateEntry(e)}
                    onContextMenu={(event) => openContextMenu(event, e)}
                    onKeyDown={(event) => onEntryKeyDown(event, e)}
                    role="treeitem"
                    aria-expanded={e.is_dir ? !collapsed : undefined}
                    tabIndex={0}
                    title={
                      e.is_dir
                        ? t("files.dirToggleTitle", {
                            path: e.path,
                            action: collapsed ? t("common.expand") : t("common.collapse"),
                          })
                        : e.path
                    }
                  >
                    <span
                      className={
                        "tree-disclosure" + (e.is_dir ? (collapsed ? " collapsed" : " expanded") : " placeholder")
                      }
                      aria-hidden="true"
                    />
                    <TreeIcon entry={e} collapsed={collapsed} />
                    <span className="tree-label">{e.name}</span>
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
        title={t("files.resizeTitle")}
        onPointerDown={startSideResize}
        onDoubleClick={() => {
          setSideWidth(null);
          window.localStorage.removeItem("aa.files.sideWidth");
          window.dispatchEvent(new Event("resize"));
        }}
      />
      <div className="files-preview">
        {!selEntry ? (
          <div className="files-empty">{t("files.selectFile")}</div>
        ) : kind === "img" ? (
          <div className="files-media">{abs && <img src={mediaSrc(abs)} alt={selEntry.name} />}</div>
        ) : kind === "video" ? (
          <div className="files-media">{abs && <video src={mediaSrc(abs)} controls preload="metadata" />}</div>
        ) : kind === "audio" ? (
          <div className="files-media"><audio src={mediaSrc(abs)} controls /></div>
        ) : err ? (
          <div className="files-empty">{t("files.previewFailed", { error: err })}</div>
        ) : (
          <Suspense fallback={<div className="files-empty">{t("common.loading")}</div>}>
            <MonacoFileEditor
              rootPath={root.path}
              entry={selEntry}
              absPath={abs}
              text={text}
              loadVersion={previewVersion}
              expectedMtime={selEntry.mtime ?? 0}
              onDirtyChange={setEditorDirty}
              onReload={() => {
                setEditorDirty(false);
                previewCacheRef.current.clear();
                refreshFiles();
              }}
              onSaved={(_, savedText) => {
                setText(savedText);
                previewCacheRef.current.clear();
                refreshFiles();
              }}
            />
          </Suspense>
        )}
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
