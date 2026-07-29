import { Bot, Check, LoaderCircle, Plus, Sparkles, X } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import type { SkillCategory, SkillMediaType } from "../../catalog/types";
import type { CreationLine } from "../../types";

export interface CreateSkillFormValues {
  title: string;
  description: string;
  line: CreationLine;
  category: SkillCategory;
  mediaType: SkillMediaType;
  guide: string;
  steps: string[];
  useCases: string[];
  visibility: "private" | "public";
}

interface CreateSkillDialogProps {
  open: boolean;
  ownerEmail: string;
  onClose: () => void;
  onCreate: (values: CreateSkillFormValues) => Promise<void>;
}

const LINES: Array<[CreationLine, string]> = [["novel", "小说"], ["n2d", "漫剧"], ["comic", "漫画"], ["ad", "广告"], ["mv", "MV"], ["song", "歌曲"]];
const CATEGORIES: SkillCategory[] = ["故事与文本", "剧本与分镜", "视觉生成", "音频与音乐", "商业创意", "后期与交付", "评审与优化"];
const MEDIA: Array<[SkillMediaType, string]> = [["text", "文字"], ["image", "图片"], ["video", "视频"], ["audio", "音频"], ["mixed", "全模态"]];

export function CreateSkillDialog({ open, ownerEmail, onClose, onCreate }: CreateSkillDialogProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [line, setLine] = useState<CreationLine>("n2d");
  const [category, setCategory] = useState<SkillCategory>("剧本与分镜");
  const [mediaType, setMediaType] = useState<SkillMediaType>("mixed");
  const [guide, setGuide] = useState("");
  const [stepsText, setStepsText] = useState("");
  const [useCasesText, setUseCasesText] = useState("");
  const [visibility, setVisibility] = useState<"private" | "public">("private");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const ready = useMemo(() => title.trim().length >= 2 && description.trim().length >= 8 && guide.trim().length >= 8, [description, guide, title]);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape" && !submitting) onClose(); };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, open, submitting]);

  if (!open) return null;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!ready || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      await onCreate({
        title: title.trim(),
        description: description.trim(),
        line,
        category,
        mediaType,
        guide: guide.trim(),
        steps: stepsText.split("\n").map((value) => value.trim()).filter(Boolean),
        useCases: useCasesText.split(/[，,\n]/).map((value) => value.trim()).filter(Boolean),
        visibility,
      });
      setTitle(""); setDescription(""); setGuide(""); setStepsText(""); setUseCasesText(""); setVisibility("private");
      onClose();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="account-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !submitting) onClose(); }}>
      <section className="create-skill-dialog" role="dialog" aria-modal="true" aria-labelledby="create-skill-title">
        <header><div><span><Sparkles size={17} /></span><div><small>MY SKILL</small><h2 id="create-skill-title">创建 Skill</h2></div></div><button className="dialog-close" type="button" onClick={onClose} aria-label="关闭"><X size={18} /></button></header>
        <form onSubmit={(event) => void submit(event)}>
          <div className="create-skill-owner"><Bot size={16} /><span>创建者</span><b>{ownerEmail}</b></div>
          <div className="form-two-columns">
            <label><span>Skill 名称</span><input autoFocus value={title} maxLength={60} onChange={(event) => setTitle(event.target.value)} placeholder="例如：古风漫画分镜导演" /></label>
            <label><span>所属创作线</span><select value={line} onChange={(event) => setLine(event.target.value as CreationLine)}>{LINES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          </div>
          <label><span>一句话介绍</span><input value={description} maxLength={180} onChange={(event) => setDescription(event.target.value)} placeholder="说明这个 Skill 能帮创作者完成什么" /><small>{description.length}/180</small></label>
          <div className="form-two-columns">
            <label><span>分类</span><select value={category} onChange={(event) => setCategory(event.target.value as SkillCategory)}>{CATEGORIES.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
            <fieldset><legend>输出类型</legend><div className="media-choice">{MEDIA.map(([value, label]) => <button key={value} type="button" className={mediaType === value ? "active" : ""} onClick={() => setMediaType(value)}>{label}</button>)}</div></fieldset>
          </div>
          <label><span>Skill 指令</span><textarea value={guide} maxLength={3000} onChange={(event) => setGuide(event.target.value)} placeholder="告诉 Agent 角色、目标、约束、执行方式与交付标准。" /><small>{guide.length}/3000</small></label>
          <div className="form-two-columns">
            <label><span>工作步骤 <em>每行一项</em></span><textarea className="small" value={stepsText} onChange={(event) => setStepsText(event.target.value)} placeholder={'读取素材\n生成方案\n检查并交付'} /></label>
            <label><span>使用场景 <em>逗号或换行分隔</em></span><textarea className="small" value={useCasesText} onChange={(event) => setUseCasesText(event.target.value)} placeholder="短篇漫画，竖屏连载，IP 改编" /></label>
          </div>
          <div className="visibility-choice"><span><b>可见范围</b><small>{visibility === "private" ? "仅你自己可见" : "其他创作者可以发现和使用"}</small></span><button type="button" className={visibility === "private" ? "active" : ""} onClick={() => setVisibility("private")}><Check size={13} />仅自己</button><button type="button" className={visibility === "public" ? "active" : ""} onClick={() => setVisibility("public")}><Check size={13} />公开</button></div>
          {error && <div className="auth-feedback error" role="alert">{error}</div>}
          <footer><button type="button" onClick={onClose}>取消</button><button className="primary" type="submit" disabled={!ready || submitting}>{submitting ? <LoaderCircle className="spinning" size={16} /> : <><Plus size={16} />创建 Skill</>}</button></footer>
        </form>
      </section>
    </div>
  );
}
