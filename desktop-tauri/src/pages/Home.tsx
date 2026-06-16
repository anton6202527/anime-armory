import { useEffect, useState } from "react";
import { scanWorkspace } from "../api";
import type { LineInfo, WorkRoot } from "../types";

export function Home(props: {
  repoRoot: string;
  onPickRepo: () => void;
  onOpen: (line: LineInfo, root: WorkRoot) => void;
}) {
  const { repoRoot, onPickRepo, onOpen } = props;
  const [lines, setLines] = useState<LineInfo[]>([]);
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    setErr("");
    scanWorkspace(repoRoot)
      .then(setLines)
      .catch((e) => setErr(String(e)));
  }, [repoRoot]);

  return (
    <div className="home">
      <h1>Anime Arsenal</h1>
      <div className="repo">
        <span>workspace: {repoRoot}</span>
        <button onClick={onPickRepo}>切换工作区…</button>
      </div>
      {err && <div className="empty">扫描失败：{err}</div>}
      {lines.map((line) => (
        <div className="line-block" key={line.line}>
          <h2>
            {line.label} <span style={{ color: "var(--muted)", fontWeight: 400 }}>· {line.dir.split("/").pop()}/ · {line.view}</span>
          </h2>
          {line.roots.length === 0 ? (
            <div className="empty">（暂无作品）</div>
          ) : (
            <div className="roots">
              {line.roots.map((root) => (
                <div className="root-card" key={root.path} onClick={() => onOpen(line, root)}>
                  <div className="name">{root.name}</div>
                  <div className="meta">{root.has_progress ? "● 有进度" : "○ 仅初始化"}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
