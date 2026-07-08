import { activeSkin, type FileIconKind } from "../skins";
import type { SkillTreeEntry } from "../types";

type FileIconEntry = Pick<SkillTreeEntry, "name" | "is_dir">;

function FileGlyph({ kind, label }: { kind: FileIconKind; label?: string }) {
  if (kind === "python") {
    return (
      <svg viewBox="0 0 18 18" className="seti-svg seti-python" aria-hidden="true">
        <path className="py-top" d="M8.5 2h3.1c1.2 0 2 .8 2 2v2.3H7.8c-1.2 0-2 .8-2 2v1H4.2c-1.1 0-1.9-.8-1.9-1.9V6.7c0-1.1.8-1.9 1.9-1.9h4.3V2Z" />
        <circle className="py-dot-top" cx="10.7" cy="4" r=".7" />
        <path className="py-bottom" d="M9.5 16H6.4c-1.2 0-2-.8-2-2v-2.3h5.8c1.2 0 2-.8 2-2v-1h1.6c1.1 0 1.9.8 1.9 1.9v.7c0 1.1-.8 1.9-1.9 1.9H9.5V16Z" />
        <circle className="py-dot-bottom" cx="7.3" cy="14" r=".7" />
      </svg>
    );
  }
  if (kind === "json") {
    return (
      <svg viewBox="0 0 18 18" className="seti-svg seti-json" aria-hidden="true">
        <path d="M7.3 3.2H6.1c-1 0-1.7.7-1.7 1.7v2.2c0 .8-.5 1.4-1.2 1.4v1c.7 0 1.2.6 1.2 1.4v2.2c0 1 .7 1.7 1.7 1.7h1.2" />
        <path d="M10.7 3.2h1.2c1 0 1.7.7 1.7 1.7v2.2c0 .8.5 1.4 1.2 1.4v1c-.7 0-1.2.6-1.2 1.4v2.2c0 1-.7 1.7-1.7 1.7h-1.2" />
      </svg>
    );
  }
  if (kind === "markdown") {
    return (
      <svg viewBox="0 0 18 18" className="seti-svg seti-markdown" aria-hidden="true">
        <path d="M3 4.5h12v9H3Z" />
        <path d="M5.2 11V7.2l1.6 1.8 1.6-1.8V11" />
        <path d="M11.8 7.2v3.2" />
        <path d="M10.5 9.3 11.8 11l1.3-1.7" />
      </svg>
    );
  }
  if (kind === "video") {
    return (
      <svg viewBox="0 0 18 18" className="seti-svg seti-video" aria-hidden="true">
        <circle cx="9" cy="9" r="8" />
        <path d="M7 5.2 12.2 9 7 12.8Z" />
      </svg>
    );
  }
  if (kind === "image") {
    return (
      <svg viewBox="0 0 18 18" className="seti-svg seti-image" aria-hidden="true">
        <path className="seti-image-back" d="M2.5 4.5h11v10h-11Z" />
        <path className="seti-image-front" d="M5 2.5h11v10H5Z" />
        <circle cx="8" cy="5.6" r="1" />
        <path d="M6.5 11 9.3 8.1l1.9 2 1.4-1.6L15 11Z" />
      </svg>
    );
  }
  if (kind === "generic") {
    return (
      <svg viewBox="0 0 18 18" className="seti-svg seti-generic" aria-hidden="true">
        <path d="M4 2.5h6.5L14 6v9.5H4Z" />
        <path d="M10.5 2.5V6H14" />
      </svg>
    );
  }
  return <span className="seti-text-icon">{label}</span>;
}

export function WorkFileIcon({ entry, collapsed = true }: { entry: FileIconEntry; collapsed?: boolean }) {
  if (entry.is_dir) {
    return (
      <span
        className={"tree-icon folder-icon" + (collapsed ? "" : " open")}
        aria-hidden="true"
      />
    );
  }
  const meta = activeSkin.fileIcon(entry);
  return (
    <span className={`tree-icon file-icon ${meta.cls}`} aria-hidden="true">
      <FileGlyph kind={meta.kind} label={meta.label} />
    </span>
  );
}
