import { useEffect, useState } from "react";
import { scanWorkspace } from "../api";
import type { LineInfo } from "../types";

// Placeholder cover glyph per line (until real cover art is wired).
const GLYPH: Record<string, string> = {
  n2d: "🎬",
  ad: "📣",
  mv: "🎵",
  song: "🎤",
  novel: "📖",
};

export function Home(props: {
  workspaceRoot: string;
  onPickWorkspace: () => void;
  onShowSkills: (line: LineInfo) => void;
  onEnter: (line: LineInfo) => void;
}) {
  const { workspaceRoot, onPickWorkspace, onShowSkills, onEnter } = props;
  const [lines, setLines] = useState<LineInfo[]>([]);
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    setErr("");
    scanWorkspace(workspaceRoot)
      .then(setLines)
      .catch((e) => setErr(String(e)));
  }, [workspaceRoot]);

  return (
    <div className="home">
      <h1>Anime Arsenal</h1>
      <div className="repo">
        <span>workspace: {workspaceRoot}</span>
        <button onClick={onPickWorkspace}>切换工作区…</button>
      </div>
      {err && <div className="empty">扫描失败：{err}</div>}

      <div className="line-grid">
        {lines.map((line) => (
          <div className="line-card" key={line.line}>
            <div className="line-cover">{GLYPH[line.line] ?? "✦"}</div>
            <div className="line-info">
              <div className="line-title">{line.label}</div>
              <div className="line-sub">
                {line.dir.split("/").pop()}/ · {line.roots.length} 部作品
              </div>
            </div>
            <div className="card-actions">
              <button onClick={() => onShowSkills(line)}>skills 详情</button>
              <button className="primary" onClick={() => onEnter(line)}>
                进入创作区 →
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
