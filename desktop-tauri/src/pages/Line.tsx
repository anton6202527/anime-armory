import { useEffect, useState } from "react";
import { confirm } from "@tauri-apps/plugin-dialog";
import { createWork, deleteWork, scanWorkspace } from "../api";
import type { LineInfo, WorkRoot } from "../types";

/** A line's 创作区: its existing works + a 新建作品 entry. Works live in the
 *  app's dedicated workspace, fully separate from the skills repo demos. */
export function Line(props: {
  workspaceRoot: string;
  line: LineInfo;
  onBack: () => void;
  onOpen: (root: WorkRoot) => void;
}) {
  const { workspaceRoot, line, onBack, onOpen } = props;
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
      const path = await createWork(line.dir, name);
      await refresh();
      setCreating(false);
      setNewName("");
      onOpen({ name, path, has_progress: false });
    } catch (e) {
      setErr(String(e));
    }
  }

  async function remove(root: WorkRoot) {
    const ok = await confirm(`删除作品「${root.name}」？\n会移到系统垃圾桶（可恢复），不影响项目仓库。`, {
      title: "删除作品",
      kind: "warning",
      okLabel: "移到垃圾桶",
      cancelLabel: "取消",
    });
    if (!ok) return;
    setErr("");
    try {
      await deleteWork(workspaceRoot, root.path);
      await refresh();
    } catch (e) {
      setErr(String(e));
    }
  }

  return (
    <div className="line-page">
      <div className="line-page-top">
        <button onClick={onBack}>← 首页</button>
        <div className="crumb">
          {line.label} <span style={{ color: "var(--muted)" }}>· {line.dir.split("/").pop()}/</span>
        </div>
      </div>

      {err && <div className="empty">{err}</div>}

      <div className="roots">
        {roots.map((root) => (
          <div className="root-card" key={root.path} onClick={() => onOpen(root)}>
            <button
              className="del-btn"
              title="删除作品"
              onClick={(e) => {
                e.stopPropagation();
                remove(root);
              }}
            >
              ✕
            </button>
            <div className="name">{root.name}</div>
            <div className="meta">{root.has_progress ? "● 有进度" : "○ 仅初始化"}</div>
          </div>
        ))}

        {creating ? (
          <div className="root-card new-card editing">
            <input
              autoFocus
              className="new-input"
              placeholder="作品名…"
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
              <button onClick={submitNew}>创建</button>
              <button onClick={() => { setCreating(false); setNewName(""); }}>取消</button>
            </div>
          </div>
        ) : (
          <div className="root-card new-card" onClick={() => setCreating(true)}>
            <div className="plus">＋</div>
            <div className="meta">新建作品</div>
          </div>
        )}
      </div>
    </div>
  );
}
