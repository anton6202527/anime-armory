import { useEffect, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { createWork, deleteWork, downloadDemo as downloadDemoWork, scanWorkspace } from "../api";
import { useI18n, useLineLabel } from "../i18n";
import type { DemoDownloadProgress, LineInfo, WorkRoot } from "../types";

/** A line's 创作区: its existing works + a 新建作品 entry. Works live in the
 *  app's dedicated workspace, fully separate from the skills repo demos. */
export function Line(props: {
  workspaceRoot: string;
  repoRoot: string;
  line: LineInfo;
  onBack: () => void;
  onShowSkills: (line: LineInfo) => void;
  onOpen: (root: WorkRoot) => void;
  onDeleted: (root: WorkRoot) => void;
}) {
  const { workspaceRoot, repoRoot, line, onBack, onShowSkills, onOpen, onDeleted } = props;
  const { t } = useI18n();
  const lineLabel = useLineLabel();
  const [roots, setRoots] = useState<WorkRoot[]>(line.roots);
  const [err, setErr] = useState<string>("");
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [pendingDelete, setPendingDelete] = useState<WorkRoot | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [downloads, setDownloads] = useState<Record<string, DemoDownloadProgress>>({});

  // re-pull this line's roots (so a freshly created/deleted work shows up)
  function refresh() {
    return scanWorkspace(workspaceRoot)
      .then((lines) => {
        const fresh = lines.find((l) => l.line === line.line);
        if (fresh) setRoots(fresh.roots);
        return fresh;
      })
      .catch((e) => setErr(String(e)));
  }
  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceRoot, line.line]);

  useEffect(() => {
    if (!pendingDelete) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !deleting) setPendingDelete(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pendingDelete, deleting]);

  useEffect(() => {
    let disposed = false;
    let unlisten: (() => void) | null = null;
    listen<DemoDownloadProgress>("demo-download-progress", (event) => {
      if (disposed) return;
      const progress = event.payload;
      setDownloads((prev) => ({
        ...prev,
        [progress.target_path]: progress,
      }));
    })
      .then((fn) => {
        if (disposed) fn();
        else unlisten = fn;
      })
      .catch(() => {});
    return () => {
      disposed = true;
      unlisten?.();
    };
  }, []);

  async function submitNew() {
    const name = newName.trim();
    if (!name) return;
    setErr("");
    try {
      const path = await createWork(line.dir, repoRoot, name);
      await refresh();
      setCreating(false);
      setNewName("");
      onOpen({ name, path, has_progress: false, is_demo: false });
    } catch (e) {
      setErr(String(e));
    }
  }

  async function confirmRemove() {
    const root = pendingDelete;
    if (!root || deleting) return;
    setErr("");
    setDeleting(true);
    try {
      await deleteWork(workspaceRoot, repoRoot, root.path);
      setPendingDelete(null);
      onDeleted(root);
      await refresh();
    } catch (e) {
      setErr(String(e));
    } finally {
      setDeleting(false);
    }
  }

  async function downloadDemo(root: WorkRoot) {
    if (!root.download_url) return;
    if (downloads[root.path]) return;
    const downloadId = `demo-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setErr("");
    setDownloads((prev) => ({
      ...prev,
      [root.path]: {
        id: downloadId,
        target_path: root.path,
        phase: "resolving",
        received: 0,
        total: null,
        percent: null,
        message: t("line.downloadResolving"),
      },
    }));
    try {
      const downloaded = await downloadDemoWork(
        workspaceRoot,
        repoRoot,
        root.path,
        root.download_url,
        downloadId,
      );
      setRoots((prev) => prev.map((item) => (item.path === root.path ? downloaded : item)));
      await refresh();
    } catch (e) {
      setErr(t("line.downloadDemoFailed", { error: String(e) }));
    } finally {
      setDownloads((prev) => {
        const current = prev[root.path];
        if (current && current.id !== downloadId) return prev;
        const next = { ...prev };
        delete next[root.path];
        return next;
      });
    }
  }

  function downloadLabel(progress: DemoDownloadProgress | undefined): string {
    if (!progress) return t("line.downloadDemo");
    const percent = Number.isFinite(progress.percent ?? NaN)
      ? ` ${Math.round(progress.percent || 0)}%`
      : "";
    if (progress.phase === "extracting") return `${t("line.downloadExtracting")}${percent}`;
    if (progress.phase === "resolving") return t("line.downloadResolving");
    return `${t("line.downloadingDemo")}${percent}`;
  }

  return (
    <div className="line-page">
      <div className="line-page-top">
        <button onClick={onBack}>{t("line.backHome")}</button>
        <div className="crumb">
          {lineLabel(line)} <span style={{ color: "var(--muted)" }}>· {line.dir.split("/").pop()}/</span>
        </div>
        <button className="line-skills-btn" onClick={() => onShowSkills(line)}>
          {t("line.skillsButton")}
        </button>
      </div>

      {err && <div className="empty">{err}</div>}

      <div className="roots">
        {roots.map((root) => {
          const progress = downloads[root.path];
          return (
            <div
              className={
                "root-card"
                + (root.is_demo ? " demo-card" : "")
                + (root.is_reference ? " reference-card" : "")
                + (progress ? " downloading-card" : "")
              }
              key={root.path}
              onClick={() => {
                if (!root.is_reference && !progress) onOpen(root);
              }}
            >
            {root.is_demo && (
              <div className="root-demo-badge" title={t("line.demoTitle")}>
                {t("line.demoBadge")}
              </div>
            )}
            {!root.is_reference && (
              <button
                className="del-btn"
                type="button"
                title={t("line.moveToTrash")}
                aria-label={t("line.deleteWorkAria", { name: root.name })}
                onClick={(e) => {
                  e.stopPropagation();
                  setPendingDelete(root);
                }}
              >
                <span className="del-icon" aria-hidden="true">🗑</span>
              </button>
            )}
            <div className="name">{root.name}</div>
            <div className="meta">
              {progress
                ? downloadLabel(progress)
                : root.is_reference
                ? t("line.referenceOnly")
                : root.has_progress
                  ? t("line.hasProgress")
                  : t("line.initialOnly")}
            </div>
            {root.is_reference && root.download_url && (
              <div className="root-actions">
                <button
                  className="download-demo-btn"
                  type="button"
                  disabled={Boolean(progress)}
                  title={t("line.downloadDemoTitle")}
                  onClick={(e) => {
                    e.stopPropagation();
                    downloadDemo(root);
                  }}
                >
                  {downloadLabel(progress)}
                </button>
                {progress && (
                  <div
                    className={
                      "root-download-progress"
                      + (Number.isFinite(progress.percent ?? NaN) ? "" : " indeterminate")
                    }
                    aria-label={downloadLabel(progress)}
                  >
                    <span style={{ width: `${Math.max(5, Math.min(100, progress.percent ?? 28))}%` }} />
                  </div>
                )}
              </div>
            )}
            </div>
          );
        })}

        {creating ? (
          <div className="root-card new-card editing">
            <input
              autoFocus
              className="new-input"
              placeholder={t("line.workNamePlaceholder")}
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") submitNew();
                if (e.key === "Escape") {
                  setCreating(false);
                  setNewName("");
                }
              }}
            />
            <div className="new-actions">
              <button onClick={submitNew}>{t("common.create")}</button>
              <button onClick={() => { setCreating(false); setNewName(""); }}>{t("common.cancel")}</button>
            </div>
          </div>
        ) : (
          <div className="root-card new-card" onClick={() => setCreating(true)}>
            <div className="plus">＋</div>
            <div className="meta">{t("line.newWork")}</div>
          </div>
        )}
      </div>

      {pendingDelete && (
        <div className="modal-backdrop confirm-backdrop" onClick={() => !deleting && setPendingDelete(null)}>
          <div className="confirm-card" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <div className="confirm-icon" aria-hidden="true">🗑</div>
            <div className="confirm-copy">
              <h2>{t("line.deleteWorkTitle")}</h2>
              <p className="confirm-lead">{t("line.confirmDeleteLead", { name: pendingDelete.name })}</p>
              <p className="confirm-detail">{t("line.confirmDeleteDetail")}</p>
              <div className="confirm-path">{t("line.confirmDeletePath", { path: pendingDelete.path })}</div>
            </div>
            <div className="confirm-actions">
              <button disabled={deleting} onClick={() => setPendingDelete(null)}>
                {t("common.cancel")}
              </button>
              <button className="danger" disabled={deleting} onClick={confirmRemove}>
                {deleting ? t("line.deleting") : t("line.moveToTrash")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
