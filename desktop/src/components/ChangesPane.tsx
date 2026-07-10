import { lazy, Suspense, useEffect, useRef, useState, useSyncExternalStore, type PointerEvent as ReactPointerEvent } from "react";
import {
  archiveWorkChange,
  archiveWorkChanges,
  ensureMedia,
  getMediaPort,
  mediaAllowRoot,
  mediaUrl,
  readWorkDocx,
  readWorkChange,
  readWorkFile,
  restoreWorkChange,
  restoreWorkChanges,
  subscribeMediaPort,
  workChanges,
} from "../api";
import { useI18n } from "../i18n";
import {
  COLLAPSE_LEFT_SIDEBAR_EVENT,
  FILES_SIDE_COLLAPSE_WIDTH,
  clampFilesSideWidth,
  clearStoredFilesSideWidth,
  commitFilesSideWidth,
  draftFilesSideWidth,
  readCurrentFilesSideWidth,
} from "../paneLayout";
import type { SkillTreeEntry, WorkChangeDetail, WorkChangeEntry, WorkChangeSummary, WorkRoot } from "../types";
import { Codicon } from "./Codicon";
import { WorkFileIcon } from "./FileIcon";
import { DecodedImage } from "../mediaPreview/DecodedImage";

const ChangesDiffEditor = lazy(() =>
  import("./ChangesDiffEditor").then((mod) => ({ default: mod.ChangesDiffEditor })),
);
const MonacoFileEditor = lazy(() =>
  import("./MonacoFileEditor").then((mod) => ({ default: mod.MonacoFileEditor })),
);

const IMG = new Set(["png", "jpg", "jpeg", "webp", "gif", "bmp", "svg"]);
const VIDEO = new Set(["mp4", "mov", "webm", "m4v"]);
const AUDIO = new Set(["wav", "mp3", "m4a", "aac", "flac", "ogg"]);
type OpenedPreviewKind = "img" | "video" | "audio" | "docx" | "text";

function fileName(path: string): string {
  const i = path.lastIndexOf("/");
  return i < 0 ? path : path.slice(i + 1);
}

function ext(path: string): string {
  const name = fileName(path);
  const i = name.lastIndexOf(".");
  return i < 0 ? "" : name.slice(i + 1).toLowerCase();
}

function formatBytes(value?: number | null): string {
  if (value == null) return "-";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function openedPreviewKind(path: string): OpenedPreviewKind {
  const e = ext(path);
  if (IMG.has(e)) return "img";
  if (VIDEO.has(e)) return "video";
  if (AUDIO.has(e)) return "audio";
  if (e === "docx") return "docx";
  return "text";
}

export function ChangesPane({
  root,
  refreshKey,
  baselineVersion,
  summary,
  onArchived,
}: {
  root: WorkRoot;
  refreshKey: number;
  baselineVersion: number;
  summary: WorkChangeSummary | null;
  onArchived: (summary: WorkChangeSummary) => void;
}) {
  const { t } = useI18n();
  const [changes, setChanges] = useState<WorkChangeEntry[]>([]);
  const [selected, setSelected] = useState("");
  const [detail, setDetail] = useState<WorkChangeDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [archiving, setArchiving] = useState(false);
  const [archivingPath, setArchivingPath] = useState("");
  const [restoring, setRestoring] = useState(false);
  const [restoringPath, setRestoringPath] = useState("");
  const [err, setErr] = useState("");
  const [openedPath, setOpenedPath] = useState("");
  const [openedText, setOpenedText] = useState("");
  const [openedError, setOpenedError] = useState("");
  const [openedLoading, setOpenedLoading] = useState(false);
  const [openedDirty, setOpenedDirty] = useState(false);
  const [openedReloadKey, setOpenedReloadKey] = useState(0);
  const paneRef = useRef<HTMLDivElement>(null);
  const scanEpochRef = useRef(0);
  const detailEpochRef = useRef(0);
  const openedEpochRef = useRef(0);
  useSyncExternalStore(subscribeMediaPort, getMediaPort);
  const openedKind = openedPath ? openedPreviewKind(openedPath) : "";

  useEffect(() => {
    let alive = true;
    const epoch = ++scanEpochRef.current;
    setLoading(true);
    setErr("");
    workChanges(root.path)
      .then((result) => {
        if (!alive || epoch !== scanEpochRef.current) return;
        setChanges(result.changes);
        setOpenedPath((prev) => (prev && result.changes.some((change) => change.path === prev && change.kind !== "deleted") ? prev : ""));
        setSelected((prev) => {
          if (prev && result.changes.some((change) => change.path === prev)) return prev;
          return result.changes[0]?.path ?? "";
        });
      })
      .catch((e) => {
        if (alive && epoch === scanEpochRef.current) setErr(String(e));
      })
      .finally(() => {
        if (alive && epoch === scanEpochRef.current) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [refreshKey, root.path, baselineVersion]);

  useEffect(() => {
    const epoch = ++detailEpochRef.current;
    setDetail(null);
    setDetailError("");
    if (!selected) return;
    let alive = true;
    readWorkChange(root.path, selected)
      .then((next) => {
        if (alive && epoch === detailEpochRef.current) setDetail(next);
      })
      .catch((e) => {
        if (alive && epoch === detailEpochRef.current) setDetailError(String(e));
      });
    return () => {
      alive = false;
    };
  }, [root.path, selected]);

  useEffect(() => {
    const epoch = ++openedEpochRef.current;
    setOpenedText("");
    setOpenedError("");
    setOpenedDirty(false);
    if (!openedPath) {
      setOpenedLoading(false);
      return;
    }
    if (openedKind === "img" || openedKind === "video" || openedKind === "audio") {
      setOpenedLoading(false);
      return;
    }
    let alive = true;
    setOpenedLoading(true);
    const reader = openedKind === "docx" ? readWorkDocx : readWorkFile;
    reader(root.path, openedPath)
      .then((text) => {
        if (alive && epoch === openedEpochRef.current) setOpenedText(text);
      })
      .catch((e) => {
        if (alive && epoch === openedEpochRef.current) setOpenedError(String(e));
      })
      .finally(() => {
        if (alive && epoch === openedEpochRef.current) setOpenedLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [openedKind, openedPath, openedReloadKey, root.path]);

  useEffect(() => {
    if (openedKind !== "img" && openedKind !== "video" && openedKind !== "audio") return;
    ensureMedia()
      .then(() => mediaAllowRoot(root.path))
      .catch((e) => setOpenedError(String(e)));
  }, [openedKind, root.path]);

  function confirmCloseOpened(nextPath?: string): boolean {
    if (!openedDirty || nextPath === openedPath) return true;
    return window.confirm(t("files.discardUnsavedConfirm", { path: openedPath }));
  }

  function selectChange(path: string) {
    if (!confirmCloseOpened("")) return;
    setOpenedPath("");
    setSelected(path);
  }

  function openChangedFile(change: WorkChangeEntry) {
    if (change.kind === "deleted") return;
    if (!confirmCloseOpened(change.path)) return;
    const kind = openedPreviewKind(change.path);
    setSelected(change.path);
    setOpenedText("");
    setOpenedError("");
    setOpenedDirty(false);
    setOpenedLoading(kind !== "img" && kind !== "video" && kind !== "audio");
    setOpenedPath(change.path);
    setOpenedReloadKey((key) => key + 1);
    window.setTimeout(() => window.dispatchEvent(new Event("resize")), 0);
  }

  function applyChangeList(nextChanges: WorkChangeEntry[], preferredSelected?: string) {
    setChanges(nextChanges);
    setSelected((prev) => {
      if (preferredSelected && nextChanges.some((change) => change.path === preferredSelected)) {
        return preferredSelected;
      }
      if (prev && nextChanges.some((change) => change.path === prev)) return prev;
      return nextChanges[0]?.path ?? "";
    });
  }

  function startSideResize(ev: ReactPointerEvent<HTMLDivElement>) {
    const pane = paneRef.current;
    if (!pane) return;
    ev.preventDefault();
    const splitter = ev.currentTarget;
    const rect = pane.getBoundingClientRect();
    document.body.classList.add("resizing-changes-side");
    splitter.classList.add("resizing");
    let latestWidth = readCurrentFilesSideWidth();

    const move = (e: PointerEvent) => {
      const next = clampFilesSideWidth(e.clientX - rect.left, rect.width);
      latestWidth = next;
      draftFilesSideWidth(next);
      window.dispatchEvent(new Event("resize"));
    };
    const up = () => {
      document.body.classList.remove("resizing-changes-side");
      splitter.classList.remove("resizing");
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", up);
      if (latestWidth <= FILES_SIDE_COLLAPSE_WIDTH) {
        clearStoredFilesSideWidth();
        window.dispatchEvent(new Event(COLLAPSE_LEFT_SIDEBAR_EVENT));
      } else {
        commitFilesSideWidth(latestWidth);
      }
      window.dispatchEvent(new Event("resize"));
    };
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", up);
  }

  async function refreshAfterArchive(result: WorkChangeSummary, preferredSelected?: string) {
    const epoch = ++scanEpochRef.current;
    const latest = await workChanges(root.path).catch(() => null);
    if (latest && epoch === scanEpochRef.current) {
      applyChangeList(latest.changes, preferredSelected);
      onArchived({
        changed: latest.changes.filter((change) => change.kind !== "deleted").length,
        deleted: latest.changes.filter((change) => change.kind === "deleted").length,
        scanned: latest.scanned,
        capped: latest.capped,
      });
      return;
    }
    onArchived(result);
  }

  async function archive() {
    if (changes.length === 0 || archiving || archivingPath || restoring || restoringPath) return;
    const ok = window.confirm(t("changes.archiveConfirm", { count: changes.length }));
    if (!ok) return;
    setArchiving(true);
    setErr("");
    scanEpochRef.current += 1;
    detailEpochRef.current += 1;
    try {
      const result = await archiveWorkChanges(root.path);
      setChanges([]);
      setSelected("");
      setDetail(null);
      setOpenedPath("");
      await refreshAfterArchive(result);
    } catch (e) {
      setErr(String(e));
    } finally {
      setArchiving(false);
    }
  }

  async function archiveOne(path: string) {
    if (!path || archiving || archivingPath || restoring || restoringPath) return;
    setArchivingPath(path);
    setErr("");
    detailEpochRef.current += 1;
    try {
      const result = await archiveWorkChange(root.path, path);
      if (selected === path) {
        setDetail(null);
        setDetailError("");
      }
      if (openedPath === path) setOpenedPath("");
      await refreshAfterArchive(result, selected === path ? undefined : selected);
    } catch (e) {
      setErr(String(e));
    } finally {
      setArchivingPath("");
    }
  }

  async function restore() {
    if (changes.length === 0 || archiving || archivingPath || restoring || restoringPath) return;
    const ok = window.confirm(t("changes.restoreConfirm", { count: changes.length }));
    if (!ok) return;
    setRestoring(true);
    setErr("");
    scanEpochRef.current += 1;
    detailEpochRef.current += 1;
    try {
      const result = await restoreWorkChanges(root.path);
      setChanges([]);
      setSelected("");
      setDetail(null);
      setOpenedPath("");
      await refreshAfterArchive(result);
    } catch (e) {
      setErr(String(e));
      setChangeRescan();
    } finally {
      setRestoring(false);
    }
  }

  async function restoreOne(path: string) {
    if (!path || archiving || archivingPath || restoring || restoringPath) return;
    const ok = window.confirm(t("changes.restoreOneConfirm", { path }));
    if (!ok) return;
    setRestoringPath(path);
    setErr("");
    detailEpochRef.current += 1;
    try {
      const result = await restoreWorkChange(root.path, path);
      if (selected === path) {
        setDetail(null);
        setDetailError("");
      }
      if (openedPath === path) setOpenedPath("");
      await refreshAfterArchive(result, selected === path ? undefined : selected);
    } catch (e) {
      setErr(String(e));
      setChangeRescan();
    } finally {
      setRestoringPath("");
    }
  }

  function setChangeRescan() {
    const epoch = ++scanEpochRef.current;
    workChanges(root.path)
      .then((latest) => {
        if (epoch === scanEpochRef.current) applyChangeList(latest.changes);
      })
      .catch(() => {});
  }

  const selectedEntry = changes.find((change) => change.path === selected) ?? null;
  const openedEntry = changes.find((change) => change.path === openedPath && change.kind !== "deleted") ?? null;
  const openedAbs = openedEntry ? `${root.path}/${openedEntry.path}` : "";
  const openedMediaUrl = openedAbs ? mediaUrl(openedAbs) : "";
  const openedMediaSrc = openedMediaUrl ? `${openedMediaUrl}&v=${openedEntry?.new_mtime ?? 0}` : "";
  const openedEditorEntry: SkillTreeEntry | null = openedEntry ? {
    name: fileName(openedEntry.path),
    path: openedEntry.path,
    depth: 0,
    is_dir: false,
    size: openedEntry.new_size ?? undefined,
    mtime: openedEntry.new_mtime ?? undefined,
    status: openedEntry.kind,
  } : null;
  const count = summary ? summary.changed + summary.deleted : changes.length;
  const showToolbar = loading || changes.length > 0 || archiving || restoring || Boolean(archivingPath || restoringPath);
  const kindLabel = {
    added: t("changes.kind.added"),
    modified: t("changes.kind.modified"),
    deleted: t("changes.kind.deleted"),
    unchanged: t("changes.kind.unchanged"),
  };

  return (
    <div className="changes-pane" ref={paneRef}>
      <div className="changes-side">
        {showToolbar && (
          <div className="changes-toolbar">
            <span className="changes-toolbar-spacer" aria-hidden="true" />
            <span className={"changes-count" + (changes.length ? " dirty" : "")}>
              {loading ? t("common.loading") : count}
            </span>
            <button
              type="button"
              className="changes-action"
              disabled={!changes.length || archiving || !!archivingPath || restoring || !!restoringPath}
              title={t("changes.restoreAllTitle")}
              aria-label={t("changes.restoreAllTitle")}
              onClick={restore}
            >
              {restoring ? "…" : <Codicon name="discard" />}
            </button>
            <button
              type="button"
              className="changes-action"
              disabled={!changes.length || archiving || !!archivingPath || restoring || !!restoringPath}
              title={t("changes.archiveAllTitle")}
              aria-label={t("changes.archiveAllTitle")}
              onClick={archive}
            >
              {archiving ? "…" : <Codicon name="add" />}
            </button>
          </div>
        )}
        {err && <div className="changes-error">{err}</div>}
        {!loading && !err && changes.length === 0 && (
          <div className="changes-empty">{t("changes.empty")}</div>
        )}
        <div className="changes-list">
          {changes.map((change) => (
            <div
              key={change.path}
              className={"change-row-wrap" + (change.path === selected ? " active" : "")}
            >
              <button
                type="button"
                className="change-row"
                onClick={() => selectChange(change.path)}
                onDoubleClick={() => openChangedFile(change)}
              >
                <WorkFileIcon entry={{ name: fileName(change.path), is_dir: false }} />
                <span className="change-name">{fileName(change.path)}</span>
                <span className={`change-status ${change.kind}`}>{kindLabel[change.kind]}</span>
                <span className="change-path">{change.path}</span>
              </button>
              <div className="change-row-actions">
                <button
                  type="button"
                  className="change-row-action"
                  disabled={change.kind === "deleted"}
                  title={t("changes.openFileTitle")}
                  aria-label={t("changes.openFileTitle")}
                  onPointerDown={(event) => event.stopPropagation()}
                  onClick={(event) => {
                    event.stopPropagation();
                    openChangedFile(change);
                  }}
                >
                  <Codicon name="goToFile" />
                </button>
                <button
                  type="button"
                  className="change-row-action"
                  disabled={archiving || !!archivingPath || restoring || !!restoringPath}
                  title={t("changes.restoreOneTitle", { path: change.path })}
                  aria-label={t("changes.restoreOneTitle", { path: change.path })}
                  onPointerDown={(event) => event.stopPropagation()}
                  onClick={(event) => {
                    event.stopPropagation();
                    restoreOne(change.path);
                  }}
                >
                  {restoringPath === change.path ? "…" : <Codicon name="discard" />}
                </button>
                <button
                  type="button"
                  className="change-row-action"
                  disabled={archiving || !!archivingPath || restoring || !!restoringPath}
                  title={t("changes.archiveOneTitle", { path: change.path })}
                  aria-label={t("changes.archiveOneTitle", { path: change.path })}
                  onPointerDown={(event) => event.stopPropagation()}
                  onClick={(event) => {
                    event.stopPropagation();
                    archiveOne(change.path);
                  }}
                >
                  {archivingPath === change.path ? "…" : <Codicon name="add" />}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div
        className="changes-splitter"
        role="separator"
        aria-orientation="vertical"
        aria-label={t("files.resizeAria")}
        onPointerDown={startSideResize}
        onDoubleClick={() => {
          clearStoredFilesSideWidth();
          window.dispatchEvent(new Event("resize"));
        }}
      />
      <div className="changes-detail">
        {openedEntry && openedEditorEntry ? (
          <div className="changes-file-view">
            <div className="files-document-toolbar">
              <WorkFileIcon entry={{ name: fileName(openedEntry.path), is_dir: false }} />
              <span className="files-document-title" title={openedEntry.path}>{fileName(openedEntry.path)}</span>
              {openedKind === "docx" && <span className="files-document-badge">{t("files.docxReadonly")}</span>}
              <button
                type="button"
                className="changes-detail-close"
                aria-label={t("common.close")}
                onClick={() => {
                  if (confirmCloseOpened("")) setOpenedPath("");
                }}
              >
                <Codicon name="close" />
              </button>
            </div>
            <div className="changes-file-body">
              {openedError ? (
                <div className="changes-empty">{t("files.previewFailed", { error: openedError })}</div>
              ) : openedKind === "img" ? (
                openedMediaSrc ? (
                  <div className="files-media">
                    <DecodedImage
                      src={openedMediaSrc}
                      alt={fileName(openedEntry.path)}
                      loading="eager"
                      maxDecodeDimension={4096}
                    />
                  </div>
                ) : (
                  <div className="changes-empty">{t("common.loading")}</div>
                )
              ) : openedKind === "video" ? (
                openedMediaSrc ? (
                  <div className="files-media"><video src={openedMediaSrc} controls preload="metadata" /></div>
                ) : (
                  <div className="changes-empty">{t("common.loading")}</div>
                )
              ) : openedKind === "audio" ? (
                openedMediaSrc ? (
                  <div className="files-media"><audio src={openedMediaSrc} controls /></div>
                ) : (
                  <div className="changes-empty">{t("common.loading")}</div>
                )
              ) : openedKind === "docx" ? (
                openedLoading ? (
                  <div className="changes-empty">{t("common.loading")}</div>
                ) : (
                  <pre className="files-document-text">{openedText}</pre>
                )
              ) : openedLoading ? (
                <div className="changes-empty">{t("common.loading")}</div>
              ) : (
                <Suspense fallback={<div className="changes-empty">{t("common.loading")}</div>}>
                  <MonacoFileEditor
                    key={`changes:${openedEntry.path}:${openedEntry.new_mtime ?? 0}:${openedReloadKey}:${openedText.length}`}
                    rootPath={root.path}
                    entry={openedEditorEntry}
                    absPath={openedAbs}
                    text={openedText}
                    loadVersion={`${openedEntry.path}:${openedEntry.new_size ?? "unknown"}:${openedEntry.new_mtime ?? "unknown"}:${openedReloadKey}`}
                    expectedMtime={openedEntry.new_mtime ?? 0}
                    onDirtyChange={setOpenedDirty}
                    onSaved={(_, savedText) => {
                      setOpenedText(savedText);
                      setOpenedDirty(false);
                      setChangeRescan();
                    }}
                  />
                </Suspense>
              )}
            </div>
          </div>
        ) : !selectedEntry ? (
          <div className="changes-empty">{t("changes.select")}</div>
        ) : detailError ? (
          <div className="changes-empty">{t("common.readFailed", { error: detailError })}</div>
        ) : !detail ? (
          <div className="changes-empty">{t("common.loading")}</div>
        ) : !detail.text_available ? (
          <div className="change-meta-only">
            <h3>{detail.path}</h3>
            <p>{detail.message || t("changes.noTextDiff")}</p>
            <div className="change-meta-grid">
              <span>{t("changes.oldSize")}</span>
              <b>{formatBytes(selectedEntry.old_size)}</b>
              <span>{t("changes.newSize")}</span>
              <b>{formatBytes(selectedEntry.new_size)}</b>
            </div>
          </div>
        ) : (
          <Suspense fallback={<div className="changes-empty">{t("common.loading")}</div>}>
            <ChangesDiffEditor detail={detail} />
          </Suspense>
        )}
      </div>
    </div>
  );
}
