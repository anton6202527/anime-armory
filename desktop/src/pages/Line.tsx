import { useEffect, useState } from "react";
import { confirm } from "@tauri-apps/plugin-dialog";
import { createWork, deleteWork, scanWorkspace } from "../api";
import { useI18n, useLineLabel } from "../i18n";
import type { LineInfo, WorkRoot } from "../types";

/** A line's 创作区: its existing works + a 新建作品 entry. Works live in the
 *  app's dedicated workspace, fully separate from the skills repo demos. */
export function Line(props: {
  workspaceRoot: string;
  repoRoot: string;
  line: LineInfo;
  onBack: () => void;
  onOpen: (root: WorkRoot) => void;
}) {
  const { workspaceRoot, repoRoot, line, onBack, onOpen } = props;
  const { t } = useI18n();
  const lineLabel = useLineLabel();
  const [roots, setRoots] = useState<WorkRoot[]>(line.roots);
  const [err, setErr] = useState<string>("");
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");

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

  async function submitNew() {
    const name = newName.trim();
    if (!name) return;
    setErr("");
    try {
      const path = await createWork(line.dir, repoRoot, name);
      await refresh();
      setCreating(false);
      setNewName("");
      onOpen({ name, path, has_progress: false });
    } catch (e) {
      setErr(String(e));
    }
  }

  async function remove(root: WorkRoot) {
    const ok = await confirm(t("line.deleteWorkMessage", { name: root.name }), {
      title: t("line.deleteWorkTitle"),
      kind: "warning",
      okLabel: t("line.moveToTrash"),
      cancelLabel: t("common.cancel"),
    });
    if (!ok) return;
    setErr("");
    try {
      await deleteWork(workspaceRoot, repoRoot, root.path);
      await refresh();
    } catch (e) {
      setErr(String(e));
    }
  }

  return (
    <div className="line-page">
      <div className="line-page-top">
        <button onClick={onBack}>{t("line.backHome")}</button>
        <div className="crumb">
          {lineLabel(line)} <span style={{ color: "var(--muted)" }}>· {line.dir.split("/").pop()}/</span>
        </div>
      </div>

      {err && <div className="empty">{err}</div>}

      <div className="roots">
        {roots.map((root) => (
          <div className="root-card" key={root.path} onClick={() => onOpen(root)}>
            <button
              className="del-btn"
              type="button"
              title={t("line.moveToTrash")}
              aria-label={t("line.deleteWorkAria", { name: root.name })}
              onClick={(e) => {
                e.stopPropagation();
                remove(root);
              }}
            >
              <span className="del-icon" aria-hidden="true">🗑</span>
            </button>
            <div className="name">{root.name}</div>
            <div className="meta">{root.has_progress ? t("line.hasProgress") : t("line.initialOnly")}</div>
          </div>
        ))}

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
    </div>
  );
}
