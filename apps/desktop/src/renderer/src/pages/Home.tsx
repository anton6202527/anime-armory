import { useEffect, useMemo, useRef, useState } from "react";
import { pickImportFiles, scanWorkspace } from "../api";
import { plainLineLabel, useI18n, useLineLabel } from "../i18n";
import type { LineInfo, LineKey } from "../types";

const LINE_ORDER: LineKey[] = ["novel", "n2d", "comic", "ad", "mv", "song"];
const lineRank = (line: LineKey) => {
  const index = LINE_ORDER.indexOf(line);
  return index === -1 ? LINE_ORDER.length : index;
};

function placeholderKey(line: LineKey) {
  switch (line) {
    case "novel": return "home.hubPlaceholderNovel" as const;
    case "n2d": return "home.hubPlaceholderN2d" as const;
    case "comic": return "home.hubPlaceholderComic" as const;
    case "ad": return "home.hubPlaceholderAd" as const;
    case "mv": return "home.hubPlaceholderMv" as const;
    case "song": return "home.hubPlaceholderSong" as const;
  }
}

function HubBrandIcon() {
  return (
    <svg className="labutv-mark" viewBox="0 0 48 48" aria-hidden="true">
      <rect className="labutv-mark__tile" x="2" y="2" width="44" height="44" rx="13" />
      <path className="labutv-mark__antenna" d="m11.5 16 6.5-5.8 6 5.1 6-5.1 6.5 5.8" />
      <rect className="labutv-mark__body" x="8.5" y="14" width="31" height="26" rx="4" />
      <rect className="labutv-mark__screen" x="12" y="17.5" width="24" height="19" rx="2" />
      <path className="labutv-mark__play" d="m21 21.3 9.6 5.7-9.6 5.7z" />
    </svg>
  );
}

function LineIcon({ line }: { line: LineKey }) {
  const common = { viewBox: "0 0 24 24", "aria-hidden": true } as const;
  if (line === "novel") return <svg {...common}><path d="M4 5.5c3.2-.9 5.8-.3 8 1.8v12c-2.2-2.1-4.8-2.7-8-1.8Zm16 0c-3.2-.9-5.8-.3-8 1.8v12c2.2-2.1 4.8-2.7 8-1.8Z" /></svg>;
  if (line === "n2d") return <svg {...common}><rect x="3.5" y="5" width="17" height="14" rx="2" /><path d="m10 9 6 3-6 3Z" /></svg>;
  if (line === "comic") return <svg {...common}><rect x="4" y="4" width="16" height="16" rx="2" /><path d="M12 4v16M4 12h16" /></svg>;
  if (line === "ad") return <svg {...common}><path d="m4 13 11-5v8L4 13Zm11-3 4-2v8l-4-2M7 14l2 6h4l-2-7" /></svg>;
  if (line === "mv") return <svg {...common}><path d="M9 17V6l10-2v11M9 9l10-2" /><circle cx="6" cy="18" r="3" /><circle cx="16" cy="16" r="3" /></svg>;
  return <svg {...common}><rect x="9" y="3" width="6" height="12" rx="3" /><path d="M5 11v1a7 7 0 0 0 14 0v-1M12 19v3M8 22h8" /></svg>;
}

function FolderIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.5 7.5h6l2-2h9v13h-17Z" /></svg>;
}

function ChevronIcon() {
  return <svg viewBox="0 0 12 12" aria-hidden="true"><path d="m3 4.5 3 3 3-3" /></svg>;
}

function SendIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V5m-6 6 6-6 6 6" /></svg>;
}

function AttachmentIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 3.5h7l4 4v13H7Z" /><path d="M14 3.5v4h4" /></svg>;
}

function fileName(path: string) {
  return path.split(/[\\/]/).filter(Boolean).pop() ?? path;
}

export function Home(props: {
  workspaceRoot: string;
  onPickWorkspace: () => void;
  onShowSkills: (line: LineInfo) => void;
  onEnter: (line: LineInfo) => void;
  onStart: (line: LineInfo, prompt: string, attachments: string[]) => Promise<void> | void;
}) {
  const { workspaceRoot, onPickWorkspace, onShowSkills, onEnter, onStart } = props;
  const { t } = useI18n();
  const lineLabel = useLineLabel();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [lines, setLines] = useState<LineInfo[]>([]);
  const [selectedLineKey, setSelectedLineKey] = useState<LineKey>("n2d");
  const [prompt, setPrompt] = useState("");
  const [attachments, setAttachments] = useState<string[]>([]);
  const [menu, setMenu] = useState<"skill" | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");
  const [fileErr, setFileErr] = useState("");

  useEffect(() => {
    let alive = true;
    setErr("");
    scanWorkspace(workspaceRoot)
      .then((result) => {
        if (!alive) return;
        const sorted = [...result].sort((a, b) => lineRank(a.line) - lineRank(b.line));
        setLines(sorted);
        setSelectedLineKey((current) => sorted.some((line) => line.line === current) ? current : (sorted[0]?.line ?? current));
      })
      .catch((error) => alive && setErr(String(error)));
    return () => { alive = false; };
  }, [workspaceRoot]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenu(null);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const selectedLine = useMemo(
    () => lines.find((line) => line.line === selectedLineKey) ?? lines[0],
    [lines, selectedLineKey],
  );

  async function chooseFiles() {
    setFileErr("");
    try {
      const picked = await pickImportFiles([], t("home.hubChooseFilesTitle"));
      if (picked.length > 0) {
        setAttachments((current) => Array.from(new Set([...current, ...picked])));
        textareaRef.current?.focus();
      }
    } catch (error) {
      setFileErr(t("home.hubPickFilesFailed", { error: String(error) }));
    }
  }

  async function submit() {
    if (!selectedLine || (!prompt.trim() && attachments.length === 0) || submitting) return;
    setSubmitting(true);
    try {
      await onStart(selectedLine, prompt.trim(), attachments);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="home home-hub" onClick={() => setMenu(null)}>
      <main className="home-hub-main">
        <header className="home-hub-brand">
          <div className="home-hub-title-row">
            <span className="home-hub-logo"><HubBrandIcon /></span>
            <h1>{t("app.name")}</h1>
          </div>
          <p>{t("home.hubSubtitle")}</p>
        </header>

        {err && <div className="home-hub-error">{t("common.scanFailed", { error: err })}</div>}
        {fileErr && <div className="home-hub-error">{fileErr}</div>}

        <section className="home-hub-composer" onClick={(event) => event.stopPropagation()}>
          <textarea
            ref={textareaRef}
            value={prompt}
            aria-label={t("home.hubPromptAria")}
            placeholder={selectedLine ? t(placeholderKey(selectedLine.line)) : t("home.hubPromptAria")}
            onChange={(event) => setPrompt(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void submit();
              }
            }}
          />

          {attachments.length > 0 && <div className="home-hub-attachments" aria-label={t("home.hubAttachedFiles")}>
            {attachments.map((path) => {
              const name = fileName(path);
              return <button type="button" key={path} title={path} aria-label={t("home.hubRemoveFile", { name })} onClick={() => setAttachments((current) => current.filter((item) => item !== path))}>
                <AttachmentIcon /><span>{name}</span><i>×</i>
              </button>;
            })}
          </div>}

          <div className="home-hub-toolbar">
            <button type="button" className="home-hub-tool home-hub-new" title={t("home.hubAddFiles")} aria-label={t("home.hubAddFiles")} disabled={submitting} onClick={() => void chooseFiles()}>+</button>
            <span className="home-hub-divider" />
            <div className="home-hub-menu-wrap">
              <button type="button" className={menu === "skill" ? "home-hub-tool active" : "home-hub-tool"} aria-expanded={menu === "skill"} onClick={() => setMenu((current) => current === "skill" ? null : "skill")}>
                {selectedLine && <LineIcon line={selectedLine.line} />}<span>{selectedLine ? plainLineLabel(lineLabel(selectedLine)) : t("home.hubSkill")}</span><ChevronIcon />
              </button>
              {menu === "skill" && <div className="home-hub-popover skill-menu">
                <strong>{t("home.hubChooseSkill")}</strong>
                {lines.map((line) => <button type="button" key={line.line} className={line.line === selectedLine?.line ? "selected" : ""} onClick={() => { setSelectedLineKey(line.line); setMenu(null); textareaRef.current?.focus(); }}><LineIcon line={line.line} /><span><b>{plainLineLabel(lineLabel(line))}</b><small>{t(placeholderKey(line.line))}</small></span>{line.line === selectedLine?.line && <i>✓</i>}</button>)}
                {selectedLine && <button type="button" className="home-hub-skill-detail" onClick={() => onShowSkills(selectedLine)}>{t("home.skillDetails")}</button>}
              </div>}
            </div>

            <span className="home-hub-divider" />
            <button type="button" className="home-hub-tool" title={workspaceRoot} onClick={onPickWorkspace}><FolderIcon /><span>{t("home.hubWorkspace")}</span></button>
            <span className="home-hub-spacer" />
            <button type="button" className="home-hub-send" aria-label={t("home.hubSend")} title={t("home.hubSend")} disabled={(!prompt.trim() && attachments.length === 0) || !selectedLine || submitting} onClick={() => void submit()}>{submitting ? <span>…</span> : <SendIcon />}</button>
          </div>
        </section>

        <nav className="home-hub-lines" aria-label={t("home.hubSeriesAria")}>
          {lines.map((line) => (
            <button type="button" key={line.line} onClick={() => onEnter(line)}>
              <LineIcon line={line.line} />
              <span>{plainLineLabel(lineLabel(line))}</span>
              <small>{line.roots.length}</small>
            </button>
          ))}
        </nav>
      </main>
    </div>
  );
}
