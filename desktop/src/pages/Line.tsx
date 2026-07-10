import { useEffect, useState } from "react";
import { createWork, deleteWork, installDemo, listDemoDownloads, scanWorkspace } from "../api";
import { Codicon } from "../components/Codicon";
import { useI18n, useLineLabel } from "../i18n";
import type { DemoDownloadInfo, LineInfo, WorkRoot } from "../types";

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
  const [availableDemo, setAvailableDemo] = useState<DemoDownloadInfo | null>(null);
  const [installingDemo, setInstallingDemo] = useState(false);

  // re-pull this line's roots (so a freshly created/deleted work shows up)
  function refresh() {
    return Promise.all([scanWorkspace(workspaceRoot), listDemoDownloads(workspaceRoot)])
      .then(([lines, demos]) => {
        const fresh = lines.find((l) => l.line === line.line);
        if (fresh) setRoots(fresh.roots);
        setAvailableDemo(demos.find((demo) => demo.line_key === line.line && !demo.installed) ?? null);
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

  async function downloadDemo() {
    if (installingDemo) return;
    setErr("");
    setInstallingDemo(true);
    try {
      const result = await installDemo(workspaceRoot, line.line);
      const fresh = await refresh();
      const root = fresh?.roots.find((r) => r.path === result.root.path) ?? result.root;
      onOpen(root);
    } catch (e) {
      setErr(t("line.downloadDemoFailed", { error: String(e) }));
    } finally {
      setInstallingDemo(false);
    }
  }

  return (
    <div className="line-page">
      <div className="line-page-top work-nav">
        <button onClick={onBack}>{t("line.backHome")}</button>
        <div className="crumb">
          {lineLabel(line)} <span style={{ color: "var(--muted)" }}>· {line.dir.split("/").pop()}/</span>
        </div>
        <button
          className="work-nav-skill-btn"
          title={t("line.skillsButton")}
          aria-label={t("line.skillsButton")}
          onClick={() => onShowSkills(line)}
        >
          <Codicon name="wrench" />
        </button>
      </div>

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
              <div className="name">{root.name}</div>
              <div className="meta">
                {root.has_progress ? t("line.hasProgress") : t("line.initialOnly")}
              </div>
            </div>
          );
        })}

        {availableDemo && (
          <div
            className={"root-card demo-download-card" + (installingDemo ? " installing" : "")}
            onClick={downloadDemo}
            role="button"
            aria-disabled={installingDemo}
          >
            <div className="demo-download-icon">
              <Codicon name="project" />
            </div>
            <div className="name">
              {installingDemo ? t("line.downloadingDemo") : t("line.downloadDemo")}
            </div>
            <div className="meta">
              {t("line.downloadDemoMeta", { name: availableDemo.name })}
            </div>
          </div>
        )}

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
