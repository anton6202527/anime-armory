import { activeSkin, type FileIconKind } from "../skins";
import type { SkillTreeEntry } from "../types";

type FileIconEntry = Pick<SkillTreeEntry, "name" | "is_dir">;

const setiGlyphByKind: Record<FileIconKind, number> = {
  audio: 0xe005,
  code: 0xe023,
  config: 0xe019,
  css: 0xe01d,
  csv: 0xe01e,
  generic: 0xe023,
  html: 0xe048,
  image: 0xe04c,
  javascript: 0xe051,
  json: 0xe055,
  lock: 0xe05d,
  markdown: 0xe060,
  npm: 0xe067,
  pdf: 0xe06d,
  python: 0xe07b,
  react: 0xe07d,
  rust: 0xe082,
  shell: 0xe089,
  spreadsheet: 0xe0a4,
  text: 0xe023,
  typescript: 0xe099,
  vite: 0xe09c,
  video: 0xe09b,
  word: 0xe0a3,
  xml: 0xe0a5,
  yaml: 0xe0a7,
};

function FileGlyph({ kind, label }: { kind: FileIconKind; label?: string }) {
  const glyph = setiGlyphByKind[kind];
  return <span className="seti-font-icon">{glyph ? String.fromCharCode(glyph) : label}</span>;
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
