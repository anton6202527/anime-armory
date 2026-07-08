import { lazy, Suspense, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import {
  archiveWorkChange,
  archiveWorkChanges,
  readWorkChange,
  restoreWorkChange,
  restoreWorkChanges,
  workChanges,
} from "../api";
import { useI18n } from "../i18n";
import type { WorkChangeDetail, WorkChangeEntry, WorkChangeSummary, WorkRoot } from "../types";
import { Codicon } from "./Codicon";
import { WorkFileIcon } from "./FileIcon";

const ChangesDiffEditor = lazy(() =>
  import("./ChangesDiffEditor").then((mod) => ({ default: mod.ChangesDiffEditor })),
);

function fileName(path: string): string {
  const i = path.lastIndexOf("/");
  return i < 0 ? path : path.slice(i + 1);
}

function formatBytes(value?: number | null): string {
  if (value == null) return "-";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

export function ChangesPane({
  root,
  refreshKey,
  baselineVersion,
  summary,
  onArchived,
  onOpenFile,
}: {
  root: WorkRoot;
  refreshKey: number;
  baselineVersion: number;
  summary: WorkChangeSummary | null;
  onArchived: (summary: WorkChangeSummary) => void;
  onOpenFile: (path: string) => void;
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
  const paneRef = useRef<HTMLDivElement>(null);
  const scanEpochRef = useRef(0);
  const detailEpochRef = useRef(0);

  useEffect(() => {
    let alive = true;
    const epoch = ++scanEpochRef.current;
    setLoading(true);
    setErr("");
    workChanges(root.path)
      .then((result) => {
        if (!alive || epoch !== scanEpochRef.current) return;
        setChanges(result.changes);
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

  function clampSideWidth(width: number, total: number): number {
    const minSide = total < 500 ? 160 : 220;
    const minPreview = Math.min(320, Math.max(180, total * 0.35));
    const maxSide = Math.max(minSide, total - minPreview);
    return Math.min(maxSide, Math.max(minSide, width));
  }

  function startSideResize(ev: ReactPointerEvent<HTMLDivElement>) {
    const pane = paneRef.current;
    if (!pane) return;
    ev.preventDefault();
    const rect = pane.getBoundingClientRect();
    document.body.classList.add("resizing-changes-side");

    const move = (e: PointerEvent) => {
      const next = clampSideWidth(e.clientX - rect.left, rect.width);
      window.localStorage.setItem("aa.files.sideWidth", String(Math.round(next)));
      window.dispatchEvent(new Event("anime-armory:files-side-width-changed"));
      window.dispatchEvent(new Event("resize"));
    };
    const up = () => {
      document.body.classList.remove("resizing-changes-side");
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", up);
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
  const count = summary ? summary.changed + summary.deleted : changes.length;
  const kindLabel = {
    added: t("changes.kind.added"),
    modified: t("changes.kind.modified"),
    deleted: t("changes.kind.deleted"),
    unchanged: t("changes.kind.unchanged"),
  };

  return (
    <div className="changes-pane" ref={paneRef}>
      <div className="changes-side">
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
                onClick={() => setSelected(change.path)}
                onDoubleClick={() => onOpenFile(change.path)}
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
                  title={t("changes.openFileTitle")}
                  aria-label={t("changes.openFileTitle")}
                  onClick={() => onOpenFile(change.path)}
                >
                  <Codicon name="goToFile" />
                </button>
                <button
                  type="button"
                  className="change-row-action"
                  disabled={archiving || !!archivingPath || restoring || !!restoringPath}
                  title={t("changes.restoreOneTitle", { path: change.path })}
                  aria-label={t("changes.restoreOneTitle", { path: change.path })}
                  onClick={() => restoreOne(change.path)}
                >
                  {restoringPath === change.path ? "…" : <Codicon name="discard" />}
                </button>
                <button
                  type="button"
                  className="change-row-action"
                  disabled={archiving || !!archivingPath || restoring || !!restoringPath}
                  title={t("changes.archiveOneTitle", { path: change.path })}
                  aria-label={t("changes.archiveOneTitle", { path: change.path })}
                  onClick={() => archiveOne(change.path)}
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
          window.localStorage.removeItem("aa.files.sideWidth");
          window.dispatchEvent(new Event("anime-armory:files-side-width-changed"));
          window.dispatchEvent(new Event("resize"));
        }}
      />
      <div className="changes-detail">
        {!selectedEntry ? (
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
