import { useEffect, useState } from "react";
import { listSkills, readSkillFile, skillTree } from "../api";
import type { LineInfo, SkillInfo, SkillTreeEntry } from "../types";

/** Overlay listing one line's skill roster, parsed live from each SKILL.md.
 *  Split view: sidebar list + detail view (title, desc, and file tree). */
export function SkillsModal(props: {
  repoRoot: string;
  line: LineInfo;
  onClose: () => void;
  onEnter: (line: LineInfo) => void;
}) {
  const { repoRoot, line, onClose, onEnter } = props;
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [err, setErr] = useState<string>("");
  const [activeIdx, setActiveIdx] = useState<number>(0);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>("");

  // dir -> its file tree (cached once loaded)
  const [trees, setTrees] = useState<Record<string, SkillTreeEntry[]>>({});

  useEffect(() => {
    setErr("");
    listSkills(repoRoot, line.line)
      .then((res) => {
        setSkills(res);
        if (res.length > 0) {
          loadTree(res[0]);
          loadFile(res[0], "SKILL.md");
        }
      })
      .catch((e) => setErr(String(e)));
  }, [repoRoot, line.line]);

  // close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  function loadTree(s: SkillInfo) {
    if (trees[s.dir]) return;
    skillTree(repoRoot, s.dir)
      .then((t) => setTrees((prev) => ({ ...prev, [s.dir]: t })))
      .catch(() => setTrees((prev) => ({ ...prev, [s.dir]: [] })));
  }

  async function loadFile(s: SkillInfo, rel: string) {
    setActiveFile(rel);
    setFileContent("读取中…");
    try {
      const txt = await readSkillFile(repoRoot, s.dir, rel);
      setFileContent(txt);
    } catch (e) {
      setFileContent(`读取失败：${e}`);
    }
  }

  function selectSkill(idx: number) {
    setActiveIdx(idx);
    const s = skills[idx];
    loadTree(s);
    loadFile(s, "SKILL.md");
  }

  const current = skills[activeIdx];
  const tree = current ? trees[current.dir] : null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>
            {line.label} · skills <span className="count">{skills.length}</span>
          </h2>
          <button className="modal-close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="modal-body">
          <div className="skills-sidebar">
            {skills.map((s, i) => (
              <div
                key={s.dir}
                className={"skill-item" + (i === activeIdx ? " active" : "")}
                onClick={() => selectSkill(i)}
              >
                {i === 0 && <div className="dispatch-dot" title="调度器" />}
                {s.name}
              </div>
            ))}
          </div>

          <div className="skill-detail">
            {current && (
              <>
                <div className="detail-top">
                  <h1>{current.name}</h1>
                  <div className="desc">{current.description}</div>
                </div>
                <div className="detail-content">
                  <div className="tree-pane">
                    <div className="skill-tree">
                      {tree === undefined && <div className="tree-line muted">读取目录…</div>}
                      {tree && tree.length === 0 && <div className="tree-line muted">（空目录）</div>}
                      {tree?.map((n, j) => (
                        <div
                          className={"tree-line" + (n.is_dir ? " dir" : "") + (activeFile === n.path ? " active" : "")}
                          key={j}
                          style={{ paddingLeft: n.depth * 16, cursor: n.is_dir ? "default" : "pointer" }}
                          onClick={() => !n.is_dir && loadFile(current, n.path)}
                        >
                          <span className="tree-icon">{n.is_dir ? "📁" : "📄"}</span>
                          {n.name}
                          {n.is_dir ? "/" : ""}
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="code-pane">
                    <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 12, lineHeight: 1.5 }}>
                      {fileContent}
                    </pre>
                    {!activeFile && <div className="placeholder">（选择左侧文件查看代码）</div>}
                  </div>
                </div>
              </>
            )}
            {!current && !err && <div className="empty" style={{ padding: 40 }}>未找到 skills</div>}
            {err && <div className="empty" style={{ padding: 40 }}>读取失败：{err}</div>}
          </div>
        </div>
        <div className="modal-foot">
          <button
            className="primary"
            onClick={() => {
              onClose();
              onEnter(line);
            }}
          >
            进入创作区 →
          </button>
        </div>
      </div>
    </div>
  );
}
