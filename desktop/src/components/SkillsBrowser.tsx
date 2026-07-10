import { useEffect, useState } from "react";
import { ensureMedia, listSkills, mediaAllowRoot, mediaUrl, readSkillFile, skillTree } from "../api";
import { useI18n } from "../i18n";
import type { LineInfo, SkillInfo, SkillTreeEntry } from "../types";

const IMG = new Set(["png", "jpg", "jpeg", "webp", "gif", "bmp", "svg"]);
const VIDEO = new Set(["mp4", "mov", "webm", "m4v"]);
const AUDIO = new Set(["wav", "mp3", "m4a", "aac", "flac", "ogg"]);

type SkillPreviewKind = "img" | "video" | "audio" | "text";

function ext(name: string): string {
  const i = name.lastIndexOf(".");
  return i < 0 ? "" : name.slice(i + 1).toLowerCase();
}

function previewKind(path: string): SkillPreviewKind {
  const e = ext(path);
  if (IMG.has(e)) return "img";
  if (VIDEO.has(e)) return "video";
  if (AUDIO.has(e)) return "audio";
  return "text";
}

function isPreviewArtifact(path: string): boolean {
  return path.split("/").includes("_preview");
}

function prefersStaticPreview(path: string): boolean {
  const e = ext(path);
  return e === "webp" || e === "gif";
}

function staticPreviewPath(path: string): string {
  const slash = path.lastIndexOf("/");
  const dir = slash < 0 ? "" : path.slice(0, slash);
  const name = slash < 0 ? path : path.slice(slash + 1);
  const dot = name.lastIndexOf(".");
  const stem = dot < 0 ? name : name.slice(0, dot);
  return joinPath(dir, "_preview", `${stem}.jpg`);
}

function joinPath(...parts: string[]): string {
  return parts
    .filter(Boolean)
    .map((part, index) => (index === 0 ? part.replace(/\/+$/, "") : part.replace(/^\/+|\/+$/g, "")))
    .join("/");
}

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
  const [mediaReady, setMediaReady] = useState(false);
  const [useOriginalMedia, setUseOriginalMedia] = useState(false);
  const [staticPreviewMissing, setStaticPreviewMissing] = useState(false);

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
    setUseOriginalMedia(false);
    setStaticPreviewMissing(false);
    const kind = previewKind(rel);
    if (kind !== "text") {
      setFileContent("");
      setMediaReady(false);
      try {
        await ensureMedia();
        await mediaAllowRoot(repoRoot);
        setMediaReady(true);
      } catch (e) {
        setFileContent(t("common.readFailed", { error: String(e) }));
      }
      return;
    }
    setMediaReady(false);
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
  const visibleTree = tree?.filter((node) => !isPreviewArtifact(node.path));
  const activeKind = activeFile ? previewKind(activeFile) : "text";
  const isOptimizedImage = !!activeFile && activeKind === "img" && prefersStaticPreview(activeFile);
  const useStaticPreview = isOptimizedImage && !useOriginalMedia && !staticPreviewMissing;
  const activeMediaRel = activeFile && useStaticPreview ? staticPreviewPath(activeFile) : activeFile;
  const activeAbs = current && activeMediaRel ? joinPath(repoRoot, "skills", current.dir, activeMediaRel) : "";
  const activeMediaSrc = mediaReady && activeAbs ? mediaUrl(activeAbs) : "";

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
                  {visibleTree === undefined && <div className="tree-line muted">{t("skills.loadingDir")}</div>}
                  {visibleTree && visibleTree.length === 0 && <div className="tree-line muted">{t("skills.emptyDir")}</div>}
                  {visibleTree?.map((node, idx) => (
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
                {activeFile && activeKind === "img" && activeMediaSrc ? (
                  <div className="skill-media-preview">
                    {isOptimizedImage && !staticPreviewMissing && (
                      <div className="skill-media-toolbar">
                        <span>{useStaticPreview ? "轻量预览" : "原图"}</span>
                        <button type="button" onClick={() => setUseOriginalMedia((value) => !value)}>
                          {useStaticPreview ? "看原图" : "轻量"}
                        </button>
                      </div>
                    )}
                    <img
                      src={activeMediaSrc}
                      alt={activeFile}
                      decoding="async"
                      onError={() => {
                        if (useStaticPreview) setStaticPreviewMissing(true);
                      }}
                    />
                  </div>
                ) : activeFile && activeKind === "video" && activeMediaSrc ? (
                  <div className="skill-media-preview">
                    <video src={activeMediaSrc} controls preload="metadata" />
                  </div>
                ) : activeFile && activeKind === "audio" && activeMediaSrc ? (
                  <div className="skill-media-preview">
                    <audio src={activeMediaSrc} controls />
                  </div>
                ) : (
                  <pre className="code-text wrap">{fileContent}</pre>
                )}
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
