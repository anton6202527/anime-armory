import { useEffect, useState, useSyncExternalStore } from "react";
import {
  createWork,
  deleteWork,
  ensureMedia,
  getMediaPort,
  installDemo,
  listDemoDownloads,
  mediaAllowRoot,
  mediaUrl,
  scanWorkspace,
  subscribeMediaPort,
} from "../api";
import { useI18n } from "../i18n";
import type { DemoDownloadInfo, LineInfo, WorkRoot } from "../types";

/** Placeholder cover glyph per line, shown when a work has no cover image yet
 *  (mirrors the Home line grid so covers read consistently). */
const LINE_GLYPH: Record<string, string> = {
  n2d: "🎬",
  comic: "🖼️",
  ad: "📣",
  mv: "🎵",
  song: "🎤",
  novel: "📖",
};

/** ↓-into-tray download glyph, drawn inline so it matches the design exactly
 *  without depending on codicon font codepoints. */
function DownloadGlyph() {
  return (
    <svg className="demo-download-glyph" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M8 2.5v7M5 7l3 3 3-3M3.5 13h9" />
    </svg>
  );
}

/** Human-readable demo package size (decimal units, matching how download
 *  sizes are usually shown). Empty when the catalog omits a size. */
function formatSize(bytes?: number | null): string {
  if (!bytes || bytes <= 0) return "";
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} GB`;
  if (bytes >= 1e6) return `${Math.round(bytes / 1e6)} MB`;
  if (bytes >= 1e3) return `${Math.round(bytes / 1e3)} KB`;
  return `${bytes} B`;
}

/** A line's 创作区: its existing works + a 新建作品 entry. Works live in the
 *  app's dedicated workspace, fully separate from the skills repo demos. */
export function Line(props: {
  workspaceRoot: string;
  repoRoot: string;
  line: LineInfo;
  onOpen: (root: WorkRoot) => void;
  onDeleted: (root: WorkRoot) => void;
}) {
  const { workspaceRoot, repoRoot, line, onOpen, onDeleted } = props;
  const { t } = useI18n();
  const [roots, setRoots] = useState<WorkRoot[]>(line.roots);
  const [err, setErr] = useState<string>("");
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [pendingDelete, setPendingDelete] = useState<WorkRoot | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [availableDemos, setAvailableDemos] = useState<DemoDownloadInfo[]>([]);
  const [installingDemoRel, setInstallingDemoRel] = useState<string | null>(null);
  // Local media server powers work-cover thumbnails; re-render once its port is up.
  const mediaPort = useSyncExternalStore(subscribeMediaPort, getMediaPort);

  useEffect(() => {
    ensureMedia()
      .then(() => mediaAllowRoot(workspaceRoot))
      .catch(() => { /* covers simply fall back to the glyph placeholder */ });
  }, [workspaceRoot]);

  // re-pull this line's roots (so a freshly created/deleted work shows up)
  function refresh() {
    return Promise.all([scanWorkspace(workspaceRoot), listDemoDownloads(workspaceRoot)])
      .then(([lines, demos]) => {
        const fresh = lines.find((l) => l.line === line.line);
        if (fresh) setRoots(fresh.roots);
        setAvailableDemos(demos.filter((demo) => demo.line_key === line.line && !demo.installed));
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

  async function downloadDemo(demo: DemoDownloadInfo) {
    if (installingDemoRel) return;
    setErr("");
    setInstallingDemoRel(demo.rel);
    try {
      const result = await installDemo(workspaceRoot, demo.rel);
      const fresh = await refresh();
      const root = fresh?.roots.find((r) => r.path === result.root.path) ?? result.root;
      onOpen(root);
    } catch (e) {
      setErr(t("line.downloadDemoFailed", { error: String(e) }));
    } finally {
      setInstallingDemoRel(null);
    }
  }

  return (
    <div className="line-page">
      {err && <div className="empty">{err}</div>}

      <div className="roots">
        {roots.map((root) => {
          return (
            <div
              className={"root-card" + (root.is_demo ? " demo-card" : "")}
              key={root.path}
              onClick={() => onOpen(root)}
            >
              {root.is_demo && (
                <div className="root-demo-badge" title={t("line.demoTitle")}>
                  {t("line.demoBadge")}
                </div>
              )}
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
              <div className="root-main">
                <div className="root-cover">
                  {root.cover && mediaPort ? (
                    <img src={mediaUrl(root.cover)} alt="" loading="lazy" />
                  ) : (
                    <span className="root-cover-fallback" aria-hidden="true">
                      {LINE_GLYPH[line.line] ?? "✦"}
                    </span>
                  )}
                </div>
                <div className="root-text">
                  <div className="name">{root.name}</div>
                  {root.synopsis ? (
                    <div className="synopsis">{root.synopsis}</div>
                  ) : (
                    <div className="meta">
                      {root.has_progress ? t("line.hasProgress") : t("line.initialOnly")}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {availableDemos.map((demo) => {
          const installing = installingDemoRel === demo.rel;
          const disabled = installingDemoRel !== null;
          return (
            <div
              className={"root-card demo-download-card" + (installing ? " installing" : "") + (disabled && !installing ? " disabled" : "")}
              key={demo.rel}
              onClick={() => !disabled && downloadDemo(demo)}
              onKeyDown={(event) => {
                if ((event.key === "Enter" || event.key === " ") && !disabled) {
                  event.preventDefault();
                  void downloadDemo(demo);
                }
              }}
              role="button"
              tabIndex={disabled ? -1 : 0}
              aria-label={t("line.downloadDemoMeta", { name: demo.name })}
              aria-disabled={disabled}
            >
              <div className="root-demo-badge" title={t("line.demoTitle")}>
                {t("line.demoBadge")}
              </div>
              <div className="name">{demo.name}</div>
              {installing && <div className="meta">{t("line.downloadingDemo")}</div>}
              <div className="demo-download-count" title={t("line.downloadDemo")}>
                <DownloadGlyph />
                <span>{formatSize(demo.size)}</span>
              </div>
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
