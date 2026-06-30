import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import {
  archiveWork,
  createWorkEntry,
  deleteWorkEntry,
  ensureMedia,
  getMediaPort,
  mediaAllowRoot,
  mediaUrl,
  openWorkEntry,
  readWorkFile,
  renameWorkEntry,
  revealWorkEntry,
  subscribeMediaPort,
  workDeleted,
  workTree,
} from "../api";
import { useI18n } from "../i18n";
import type { SkillTreeEntry, WorkRoot } from "../types";

// The default "文件" tab for every work: a real directory tree of the work root
// (创作区/<line>/<work>/) on the left, with a preview pane on the right. Text via
// read_work_file; images / video / audio via the localhost media server (same
// channel the canvas thumbnails use). Re-reads on `refreshKey` (fs watch).
const IMG = new Set(["png", "jpg", "jpeg", "webp", "gif", "bmp", "svg"]);
const VIDEO = new Set(["mp4", "mov", "webm", "m4v"]);
const AUDIO = new Set(["wav", "mp3", "m4a", "aac", "flac", "ogg"]);
const MARKDOWN = new Set(["md", "markdown", "mdx"]);
const JSONISH = new Set(["json", "jsonl"]);

type PreviewKind = "img" | "video" | "audio" | "markdown" | "json" | "text";
type ContextMenuState = { x: number; y: number; entry: SkillTreeEntry | null };

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

function fileIconMeta(entry: SkillTreeEntry): { cls: string; label?: string } {
  const kind = previewKind(entry.name);
  if (kind === "img") return { cls: "file-img" };
  if (kind === "video") return { cls: "file-video" };
  if (kind === "audio") return { cls: "file-audio", label: "♪" };
  if (kind === "markdown") return { cls: "file-md", label: "M" };
  if (kind === "json") return { cls: "file-json", label: "{}" };
  return { cls: "file-generic" };
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
  const meta = fileIconMeta(entry);
  return (
    <span className={`tree-icon file-icon ${meta.cls}`} aria-hidden="true">
      {meta.label}
    </span>
  );
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

function formatJsonPreview(
  raw: string,
  name: string,
  t: (key: "files.jsonError", params?: Record<string, string | number>) => string,
): { text: string; error?: string } {
  try {
    if (ext(name) === "jsonl") {
      const lines = raw.split(/\r?\n/);
      const formatted = lines
        .map((line) => {
          if (!line.trim()) return "";
          return JSON.stringify(JSON.parse(line), null, 2);
        })
        .join("\n");
      return { text: formatted };
    }
    return { text: JSON.stringify(JSON.parse(raw), null, 2) };
  } catch (e) {
    return { text: raw, error: t("files.jsonError", { error: String(e) }) };
  }
}

function renderInline(text: string) {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("`") && part.endsWith("`")) return <code key={i}>{part.slice(1, -1)}</code>;
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
    return part;
  });
}

function MarkdownPreview({ text }: { text: string }) {
  const nodes: JSX.Element[] = [];
  const lines = text.split(/\r?\n/);
  let code: string[] | null = null;

  const flushCode = (key: number) => {
    if (!code) return;
    nodes.push(
      <pre className="md-code" key={`code-${key}`}>
        <code>{code.join("\n")}</code>
      </pre>,
    );
    code = null;
  };

  lines.forEach((line, i) => {
    const fence = line.match(/^```(.*)$/);
    if (fence) {
      if (code) flushCode(i);
      else {
        code = [];
      }
      return;
    }
    if (code) {
      code.push(line);
      return;
    }

    if (!line.trim()) {
      nodes.push(<div className="md-gap" key={`gap-${i}`} />);
      return;
    }
    const head = line.match(/^(#{1,6})\s+(.+)$/);
    if (head) {
      const level = head[1].length;
      const Tag = `h${level}` as keyof JSX.IntrinsicElements;
      nodes.push(<Tag key={`h-${i}`}>{renderInline(head[2])}</Tag>);
      return;
    }
    const bullet = line.match(/^\s*[-*+]\s+(.+)$/);
    if (bullet) {
      nodes.push(<div className="md-bullet" key={`b-${i}`}>{renderInline(bullet[1])}</div>);
      return;
    }
    const quote = line.match(/^>\s?(.+)$/);
    if (quote) {
      nodes.push(<blockquote key={`q-${i}`}>{renderInline(quote[1])}</blockquote>);
      return;
    }
    if (line.includes("|") && line.trim().startsWith("|")) {
      nodes.push(<pre className="md-table" key={`t-${i}`}>{line}</pre>);
      return;
    }
    nodes.push(<p key={`p-${i}`}>{renderInline(line)}</p>);
  });
  flushCode(lines.length);

  return <div className="markdown-preview">{nodes}</div>;
}

export function FilesPane({
  root,
  refreshKey,
  onOpenTerminal,
}: {
  root: WorkRoot;
  refreshKey: number;
  onOpenTerminal?: (command?: string) => void;
}) {
  const { t } = useI18n();
  const paneRef = useRef<HTMLDivElement>(null);
  const [tree, setTree] = useState<SkillTreeEntry[]>([]);
  const [deleted, setDeleted] = useState<string[]>([]);
  const [collapsedDirs, setCollapsedDirs] = useState<Set<string>>(() => new Set());
  const [sel, setSel] = useState<string>(""); // selected file's rel path
  const [text, setText] = useState<string>("");
  const [err, setErr] = useState<string>("");
  const [menu, setMenu] = useState<ContextMenuState | null>(null);
  const [localRefresh, setLocalRefresh] = useState(0); // bump after archive (no fs event)
  const [archiving, setArchiving] = useState(false);
  const [sideWidth, setSideWidth] = useState<number | null>(() => {
    const saved = Number(window.localStorage.getItem("aa.files.sideWidth"));
    return Number.isFinite(saved) && saved > 0 ? saved : null;
  });
  // re-render once the media server port is ready (else media URLs are empty)
  useSyncExternalStore(subscribeMediaPort, getMediaPort);

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
  }, [root.path]);

  useEffect(() => {
    let alive = true;
    ensureMedia()
      .then(() => mediaAllowRoot(root.path))
      .catch(() => {});
    workTree(root.path)
      .then((t) => alive && setTree(t))
      .catch(() => alive && setTree([]));
    workDeleted(root.path)
      .then((d) => alive && setDeleted(d))
      .catch(() => alive && setDeleted([]));
    return () => {
      alive = false;
    };
  }, [root.path, refreshKey, localRefresh]);

  const changeCount = useMemo(
    () => tree.filter((e) => !e.is_dir && (e.status === "u" || e.status === "m")).length,
    [tree],
  );

  async function confirmEntry(rel?: string) {
    if (archiving) return;
    setArchiving(true);
    try {
      await archiveWork(root.path, rel);
      setLocalRefresh((n) => n + 1);
    } catch {
      /* leave markers in place on failure */
    } finally {
      setArchiving(false);
    }
  }

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
    const nextName = window.prompt(t("files.renamePrompt"), entry.name);
    if (!nextName || nextName === entry.name) return;
    const nextRel = await renameWorkEntry(root.path, entry.path, nextName);
    if (sel === entry.path) setSel(entry.is_dir ? "" : nextRel);
    else if (entry.is_dir && sel.startsWith(`${entry.path}/`)) setSel("");
    refreshFiles();
  }

  async function deleteEntry(entry: SkillTreeEntry) {
    const ok = window.confirm(t("files.deleteConfirm", { path: entry.path }));
    if (!ok) return;
    await deleteWorkEntry(root.path, entry.path);
    if (sel === entry.path || sel.startsWith(`${entry.path}/`)) setSel("");
    refreshFiles();
  }

  const visibleTree = useMemo(() => visibleEntries(tree, collapsedDirs), [tree, collapsedDirs]);
  const selEntry = useMemo(() => tree.find((e) => e.path === sel) || null, [tree, sel]);
  const kind = selEntry ? previewKind(selEntry.name) : "";
  const abs = selEntry ? `${root.path}/${selEntry.path}` : "";
  const mediaRevision = refreshKey + localRefresh;
  const mediaSrc = (path: string) => {
    const url = mediaUrl(path);
    return url ? `${url}&v=${mediaRevision}` : "";
  };
  const jsonPreview = useMemo(
    () => (selEntry && kind === "json" && text ? formatJsonPreview(text, selEntry.name, t) : null),
    [kind, selEntry, t, text],
  );

  // load text previews (image/video/audio stream straight from the media server)
  useEffect(() => {
    setErr("");
    setText("");
    if (!selEntry || kind === "img" || kind === "video" || kind === "audio") return;
    let alive = true;
    readWorkFile(root.path, selEntry.path)
      .then((s) => alive && setText(s))
      .catch((e) => alive && setErr(String(e)));
    return () => {
      alive = false;
    };
  }, [root.path, sel, kind, refreshKey, localRefresh]);

  function toggleDir(path: string) {
    setCollapsedDirs((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }

  function activateEntry(entry: SkillTreeEntry) {
    if (entry.is_dir) {
      toggleDir(entry.path);
      return;
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
  const menuCanArchive = !!menuEntry && (menuEntry.status === "u" || menuEntry.status === "m");

  return (
    <div className="files-pane" ref={paneRef}>
      <div className="files-side" style={sideWidth ? { width: sideWidth } : undefined}>
        <div className="files-toolbar">
          <span className={"files-change-count" + (changeCount || deleted.length ? " dirty" : "")}>
            {changeCount || deleted.length ? (
              <>
                {changeCount > 0 && t("files.changeCount", { count: changeCount })}
                {changeCount > 0 && deleted.length > 0 && t("common.listDelimiter")}
                {deleted.length > 0 && (
                  <span className="files-deleted-count" title={t("files.deletedTitle", { items: deleted.join("\n") })}>
                    {t("files.deletedCount", { count: deleted.length })}
                  </span>
                )}
              </>
            ) : (
              t("files.noChanges")
            )}
          </span>
          <button
            type="button"
            className="files-archive-btn"
            onClick={() => confirmEntry()}
            disabled={archiving || (changeCount === 0 && deleted.length === 0)}
            title={t("files.archiveAllTitle")}
          >
            {t("files.archive")}
          </button>
        </div>
        <div className="files-tree" role="tree" onContextMenu={(event) => openContextMenu(event, null)}>
          {tree.length === 0 && <div className="files-empty">{t("common.emptyDir")}</div>}
          {visibleTree.map((e) => {
            const collapsed = e.is_dir && collapsedDirs.has(e.path);
            const status = e.status === "u" || e.status === "m" ? e.status : "";
            return (
              <div
                key={e.path}
                className={
                  "tree-line" + (e.is_dir ? " dir" : "") + (e.path === sel ? " active" : "")
                }
                style={{ paddingLeft: 8 + e.depth * 14 }}
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
                {status && (
                  <span
                    className={`tree-status ${status}`}
                    title={status === "u" ? t("files.statusNewTitle") : t("files.statusModifiedTitle")}
                    aria-label={status === "u" ? t("files.statusNewAria") : t("files.statusModifiedAria")}
                  >
                    {status === "u" ? "U" : "M"}
                  </span>
                )}
                {status && (
                  <button
                    type="button"
                    className="tree-confirm"
                    onClick={(event) => {
                      event.stopPropagation();
                      confirmEntry(e.path);
                    }}
                    disabled={archiving}
                    title={e.is_dir ? t("files.confirmFolderTitle") : t("files.confirmFileTitle")}
                    aria-label={t("files.confirmItemAria")}
                  >
                    ✓
                  </button>
                )}
              </div>
            );
          })}
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
        ) : kind === "markdown" ? (
          <MarkdownPreview text={text} />
        ) : kind === "json" ? (
          <div className="json-preview">
            {jsonPreview?.error && <div className="json-error">{jsonPreview.error}</div>}
            <pre className="files-text">{jsonPreview?.text ?? text}</pre>
          </div>
        ) : (
          <pre className="files-text">{text}</pre>
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
          {menuCanArchive && (
            <>
              <div className="ctx-sep" />
              <button
                type="button"
                role="menuitem"
                onClick={() => runMenuAction(() => confirmEntry(menuRel))}
              >
                {t("files.menuArchive")}
              </button>
            </>
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
