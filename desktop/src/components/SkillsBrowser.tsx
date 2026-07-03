import { useEffect, useState } from "react";
import { listSkills, readSkillFile, skillTree } from "../api";
import { useI18n } from "../i18n";
import type { LineInfo, SkillInfo, SkillTreeEntry } from "../types";

/** Shared skills browser used by the modal and the in-work left rail tab. */
export function SkillsBrowser(props: {
  repoRoot: string;
  line: LineInfo;
  onCountChange?: (count: number) => void;
}) {
  const { repoRoot, line, onCountChange } = props;
  const { t } = useI18n();
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [err, setErr] = useState<string>("");
  const [activeIdx, setActiveIdx] = useState<number>(0);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>("");
  const [trees, setTrees] = useState<Record<string, SkillTreeEntry[]>>({});

  useEffect(() => {
    let alive = true;
    setErr("");
    setSkills([]);
    setActiveIdx(0);
    setActiveFile(null);
    setFileContent("");
    setTrees({});
    onCountChange?.(0);

    listSkills(repoRoot, line.line)
      .then((res) => {
        if (!alive) return;
        setSkills(res);
        onCountChange?.(res.length);
        if (res.length > 0) {
          loadTree(res[0]);
          loadFile(res[0], "SKILL.md");
        }
      })
      .catch((e) => {
        if (!alive) return;
        setErr(String(e));
        onCountChange?.(0);
      });
    return () => {
      alive = false;
    };
    // loadTree/loadFile intentionally read fresh state for the selected line.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repoRoot, line.line]);

  function loadTree(s: SkillInfo) {
    if (trees[s.dir]) return;
    skillTree(repoRoot, s.dir)
      .then((tree) => setTrees((prev) => ({ ...prev, [s.dir]: tree })))
      .catch(() => setTrees((prev) => ({ ...prev, [s.dir]: [] })));
  }

  async function loadFile(s: SkillInfo, rel: string) {
    setActiveFile(rel);
    setFileContent(t("common.loading"));
    try {
      const txt = await readSkillFile(repoRoot, s.dir, rel);
      setFileContent(txt);
    } catch (e) {
      setFileContent(t("common.readFailed", { error: String(e) }));
    }
  }

  function selectSkill(idx: number) {
    setActiveIdx(idx);
    const skill = skills[idx];
    loadTree(skill);
    loadFile(skill, "SKILL.md");
  }

  const current = skills[activeIdx];
  const tree = current ? trees[current.dir] : null;

  return (
    <div className="skills-browser">
      <div className="skills-sidebar">
        {skills.map((skill, i) => (
          <div
            key={skill.dir}
            className={"skill-item" + (i === activeIdx ? " active" : "")}
            onClick={() => selectSkill(i)}
          >
            {i === 0 && <div className="dispatch-dot" title={t("skills.dispatcher")} />}
            <span className="skill-name">{skill.name}</span>
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
                  {tree === undefined && <div className="tree-line muted">{t("skills.loadingDir")}</div>}
                  {tree && tree.length === 0 && <div className="tree-line muted">{t("skills.emptyDir")}</div>}
                  {tree?.map((node, idx) => (
                    <div
                      className={
                        "tree-line" +
                        (node.is_dir ? " dir" : "") +
                        (activeFile === node.path ? " active" : "")
                      }
                      key={idx}
                      style={{ paddingLeft: node.depth * 16, cursor: node.is_dir ? "default" : "pointer" }}
                      onClick={() => !node.is_dir && loadFile(current, node.path)}
                    >
                      <span className="tree-icon">{node.is_dir ? "📁" : "📄"}</span>
                      {node.name}
                      {node.is_dir ? "/" : ""}
                    </div>
                  ))}
                </div>
              </div>
              <div className="code-pane">
                <pre className="code-text wrap">{fileContent}</pre>
                {!activeFile && <div className="placeholder">{t("skills.selectFile")}</div>}
              </div>
            </div>
          </>
        )}
        {!current && !err && <div className="empty skills-empty">{t("skills.notFound")}</div>}
        {err && <div className="empty skills-empty">{t("common.readFailed", { error: err })}</div>}
      </div>
    </div>
  );
}
