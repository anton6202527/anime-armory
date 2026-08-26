import { useMemo, useRef, useState } from "react";
import { BrandIcon } from "../components/BrandIcon";
import { LineIcon } from "../components/LineIcon";
import { createWebWork, saveWork } from "../lib/work";
import type { CreationLine, PendingAttachment, WebWork } from "../types";

const LINES: Array<{ line: CreationLine; label: string; placeholder: string }> = [
  { line: "novel", label: "写小说", placeholder: "输入题材、人物或一个开场；Agent 会从世界观和故事大纲开始。" },
  { line: "n2d", label: "制漫剧", placeholder: "输入小说、故事或短剧构想；Agent 会从剧本与分镜开始，推进配音、出图、视频和合成。" },
  { line: "comic", label: "画漫画", placeholder: "输入故事、人物或上传小说；Agent 会从分格脚本和页面排版开始。" },
  { line: "ad", label: "拍广告", placeholder: "输入产品、受众和投放目标；Agent 会从创意策略与脚本开始。" },
  { line: "mv", label: "制 MV", placeholder: "输入歌曲、情绪和视觉方向；Agent 会从节奏分析与镜头设计开始。" },
  { line: "song", label: "写歌", placeholder: "输入主题、曲风或一段歌词；Agent 会从词曲方案开始。" },
];

function toAttachment(file: File): PendingAttachment {
  return {
    id: crypto.randomUUID(),
    name: file.name,
    size: file.size,
    type: file.type || "application/octet-stream",
    file,
  };
}

export function HomePage({ onCreate }: { onCreate: (work: WebWork, attachments: PendingAttachment[]) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [line, setLine] = useState<CreationLine>("n2d");
  const [prompt, setPrompt] = useState("");
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const [skillOpen, setSkillOpen] = useState(false);
  const [modelOpen, setModelOpen] = useState(false);
  const selected = useMemo(() => LINES.find((item) => item.line === line) ?? LINES[1], [line]);
  const ready = Boolean(prompt.trim() || attachments.length);

  function submit() {
    if (!ready) return;
    const work = createWebWork(line, prompt, attachments);
    saveWork(work);
    onCreate(work, attachments);
  }

  return (
    <main className="hub-shell" onClick={() => { setSkillOpen(false); setModelOpen(false); }}>
      <section className="hub-content">
        <header className="hub-brand">
          <div className="hub-title-row">
            <span className="brand-icon"><BrandIcon /></span>
            <h1>LabuTV <em>Web</em></h1>
          </div>
          <p>选择对应技能，即刻开始创作吧！</p>
        </header>

        <section className="hub-composer" onClick={(event) => event.stopPropagation()}>
          <textarea
            autoFocus
            value={prompt}
            aria-label="创作需求"
            placeholder={selected.placeholder}
            onChange={(event) => setPrompt(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
              }
            }}
          />

          {attachments.length > 0 && (
            <div className="attachment-row">
              {attachments.map((attachment) => (
                <button key={attachment.id} type="button" title="移除附件" onClick={() => setAttachments((items) => items.filter((item) => item.id !== attachment.id))}>
                  <span>▧</span>{attachment.name}<i>×</i>
                </button>
              ))}
            </div>
          )}

          <div className="composer-toolbar">
            <input
              ref={inputRef}
              type="file"
              multiple
              hidden
              onChange={(event) => {
                const next = Array.from(event.target.files ?? []).map(toAttachment);
                setAttachments((items) => [...items, ...next]);
                event.target.value = "";
              }}
            />
            <button className="icon-button add-button" type="button" aria-label="添加文件" title="添加小说、图片、音频或视频" onClick={() => inputRef.current?.click()}>＋</button>
            <span className="toolbar-divider" />

            <div className="menu-wrap">
              <button type="button" className="toolbar-button" onClick={() => { setModelOpen((open) => !open); setSkillOpen(false); }}>
                <span className="wave-icon">▮▥▮</span><span>全模态模型</span><b>⌄</b>
              </button>
              {modelOpen && (
                <div className="hub-menu model-menu">
                  <small>模型服务</small>
                  <button className="selected" type="button"><span className="menu-orb" /><span><b>全模态 API</b><small>待配置服务端密钥</small></span><i>✓</i></button>
                </div>
              )}
            </div>

            <span className="toolbar-divider" />
            <div className="menu-wrap">
              <button type="button" className="toolbar-button" onClick={() => { setSkillOpen((open) => !open); setModelOpen(false); }}>
                <LineIcon line={line} /><span>{selected.label}</span><b>⌄</b>
              </button>
              {skillOpen && (
                <div className="hub-menu skill-menu">
                  <small>选择创作技能</small>
                  {LINES.map((item) => (
                    <button key={item.line} className={item.line === line ? "selected" : ""} type="button" onClick={() => { setLine(item.line); setSkillOpen(false); }}>
                      <LineIcon line={item.line} /><span><b>{item.label}</b><small>{item.placeholder}</small></span>{item.line === line && <i>✓</i>}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <span className="toolbar-spacer" />
            <button type="button" className="send-button" disabled={!ready} aria-label="开始创作" onClick={submit}>↑</button>
          </div>
        </section>

        <nav className="line-shortcuts" aria-label="创作技能">
          {LINES.map((item) => (
            <button key={item.line} className={item.line === line ? "active" : ""} type="button" onClick={() => setLine(item.line)}>
              <LineIcon line={item.line} /><span>{item.label}</span>
            </button>
          ))}
        </nav>

      </section>
    </main>
  );
}
