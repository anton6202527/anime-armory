import { useEffect, useState } from "react";
import { listSkills } from "../api";
import type { LineInfo, SkillInfo } from "../types";

/** Overlay listing one line's skill roster, parsed live from each SKILL.md. */
export function SkillsModal(props: { repoRoot: string; line: LineInfo; onClose: () => void }) {
  const { repoRoot, line, onClose } = props;
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    setErr("");
    listSkills(repoRoot, line.line)
      .then(setSkills)
      .catch((e) => setErr(String(e)));
  }, [repoRoot, line.line]);

  // close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

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
          {err && <div className="empty">读取失败：{err}</div>}
          {!err && skills.length === 0 && <div className="empty">（未找到 skills）</div>}
          {skills.map((s, i) => (
            <div className="skill-row" key={s.name}>
              <div className="skill-name">
                {i === 0 && <span className="dispatch-tag">调度</span>}
                {s.name}
              </div>
              <div className="skill-desc">{s.description}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
