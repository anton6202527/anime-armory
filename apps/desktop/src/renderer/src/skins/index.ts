import type { SkillTreeEntry } from "../types";

export type FileIconKind =
  | "audio"
  | "code"
  | "config"
  | "css"
  | "csv"
  | "generic"
  | "html"
  | "image"
  | "javascript"
  | "json"
  | "lock"
  | "markdown"
  | "npm"
  | "pdf"
  | "python"
  | "react"
  | "rust"
  | "shell"
  | "spreadsheet"
  | "text"
  | "typescript"
  | "vite"
  | "video"
  | "word"
  | "xml"
  | "yaml";

export type SkinFileIcon = {
  cls: string;
  kind: FileIconKind;
  label?: string;
};

export type SkinPlugin = {
  id: string;
  name: string;
  cssVars: Record<string, string>;
  monacoThemeName: string;
  monacoTheme: {
    base: "vs" | "vs-dark" | "hc-black" | "hc-light";
    inherit: boolean;
    rules: Array<{ token: string; foreground?: string; background?: string; fontStyle?: string }>;
    colors: Record<string, string>;
  };
  fileIcon(entry: Pick<SkillTreeEntry, "name" | "is_dir">): SkinFileIcon;
};

function ext(name: string): string {
  const i = name.lastIndexOf(".");
  return i < 0 ? "" : name.slice(i + 1).toLowerCase();
}

const fileIconByExt: Record<string, Omit<SkinFileIcon, "kind"> & { kind?: FileIconKind }> = {
  bash: { cls: "file-shell", kind: "shell" },
  cjs: { cls: "file-js", kind: "javascript" },
  css: { cls: "file-css", kind: "css" },
  csv: { cls: "file-csv", kind: "csv" },
  docx: { cls: "file-word", kind: "word" },
  env: { cls: "file-config", kind: "config" },
  html: { cls: "file-html", kind: "html" },
  js: { cls: "file-js", kind: "javascript" },
  json: { cls: "file-json", kind: "json", label: "{}" },
  jsonl: { cls: "file-json", kind: "json", label: "{}" },
  jsx: { cls: "file-react", kind: "react" },
  lock: { cls: "file-lock", kind: "lock" },
  markdown: { cls: "file-md", kind: "markdown", label: "MD" },
  md: { cls: "file-md", kind: "markdown", label: "MD" },
  mdx: { cls: "file-md", kind: "markdown", label: "MD" },
  mjs: { cls: "file-js", kind: "javascript" },
  pdf: { cls: "file-pdf", kind: "pdf" },
  pptx: { cls: "file-text", kind: "text" },
  py: { cls: "file-py", kind: "python" },
  rs: { cls: "file-rs", kind: "rust" },
  scss: { cls: "file-css", kind: "css" },
  sh: { cls: "file-shell", kind: "shell" },
  swift: { cls: "file-code", kind: "code" },
  toml: { cls: "file-config", kind: "config" },
  ts: { cls: "file-ts", kind: "typescript" },
  tsx: { cls: "file-react", kind: "react" },
  txt: { cls: "file-text", kind: "text" },
  xml: { cls: "file-xml", kind: "xml" },
  xlsx: { cls: "file-xls", kind: "spreadsheet" },
  yaml: { cls: "file-yaml", kind: "yaml" },
  yml: { cls: "file-yaml", kind: "yaml" },
  zsh: { cls: "file-shell", kind: "shell" },
};

function textIcon(icon: Omit<SkinFileIcon, "kind"> & { kind?: FileIconKind }): SkinFileIcon {
  return { ...icon, kind: icon.kind ?? "generic" };
}

export const forgeSkin: SkinPlugin = {
  id: "vscode-dark-modern",
  name: "VS Code Dark Modern",
  cssVars: {
    "--editor-bg": "#1f1f1f",
    "--sidebar-bg": "#181818",
    "--surface-bg": "#2b2b2b",
    "--bg": "#1f1f1f",
    "--bg-2": "#181818",
    "--panel": "#2b2b2b",
    "--border": "#2b2b2b",
    "--text": "#cccccc",
    "--muted": "#9d9d9d",
    "--accent": "#b9bac0",
    "--focus": "#8f8f98",
    "--active-bar": "#a1a1aa",
    "--splitter-active": "#a1a1aa",
    "--activity-fg": "#d7d7d7",
    "--activity-inactive": "#868686",
    "--block": "#f85149",
    "--warn": "#cca700",
    "--info": "#aeb0b8",
    "--good": "#4ec9b0",
    "--tree-indent-guide": "#404040",
    "--editor-line": "#2b2b2b",
    "--editor-selection": "#45464d",
    "--input-bg": "#313131",
    "--input-border": "#3c3c3c",
    "--list-hover-bg": "#2a2d2e",
    "--list-focus-bg": "#37373d",
    "--list-active-bg": "#393a40",
    "--folder-icon": "#bfc0c6",
    "--file-icon": "#d4d7d6",
    "--file-code-icon": "#b9b9be",
    "--file-image-icon": "#c5c5ca",
    "--file-video-icon": "#adadb3",
    "--file-audio-icon": "#d0d0d5",
    "--file-md-icon": "#a6a7ad",
    "--file-json-icon": "#c1c1c6",
    "--file-js-icon": "#c1c1c6",
    "--file-ts-icon": "#a9aab0",
    "--file-html-icon": "#b8b8bd",
    "--file-css-icon": "#a9aab0",
    "--file-python-icon": "#a9aab0",
    "--file-rust-icon": "#6d8086",
    "--file-shell-icon": "#c4c4c8",
    "--file-yaml-icon": "#b0b0b6",
    "--file-config-icon": "#6d8086",
    "--scm-untracked": "#89d185",
    "--scm-modified": "#cca700",
    "--scm-deleted": "#f48771",
    "--menu-bg": "#1f1f1f",
    "--menu-border": "#454545",
    "--menu-hover-bg": "#45464d",
    "--menu-hover-fg": "#ffffff",
    "--dropdown-bg": "#252526",
  },
  monacoThemeName: "anime-armory-forge",
  monacoTheme: {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "", foreground: "cccccc", background: "1f1f1f" },
      { token: "comment", foreground: "6a9955" },
      { token: "keyword", foreground: "569cd6" },
      { token: "string", foreground: "ce9178" },
      { token: "number", foreground: "b5cea8" },
    ],
    colors: {
      "editor.background": "#1f1f1f",
      "editor.foreground": "#cccccc",
      "editorLineNumber.foreground": "#6e7681",
      "editorLineNumber.activeForeground": "#cccccc",
      "editorCursor.foreground": "#ececf0",
      "editor.selectionBackground": "#45464d",
      "editor.inactiveSelectionBackground": "#3a3d41",
      "editor.lineHighlightBackground": "#2b2b2b",
      "editorIndentGuide.background1": "#404040",
      "editorIndentGuide.activeBackground1": "#707070",
      "editorGutter.background": "#1f1f1f",
    },
  },
  fileIcon(entry) {
    if (entry.is_dir) return { cls: "file-folder", kind: "generic" };
    const lowerName = entry.name.toLowerCase();
    if (lowerName === "vite.config.ts" || lowerName === "vite.config.js") {
      return { cls: "file-vite", kind: "vite" };
    }
    if (lowerName === "package.json" || lowerName === "package-lock.json") {
      return { cls: "file-npm", kind: "npm" };
    }
    const e = ext(entry.name);
    if (["png", "jpg", "jpeg", "webp", "gif", "bmp", "svg"].includes(e)) {
      return { cls: "file-img", kind: "image" };
    }
    if (["mp4", "mov", "webm", "m4v"].includes(e)) return { cls: "file-video", kind: "video" };
    if (["wav", "mp3", "m4a", "aac", "flac", "ogg"].includes(e)) {
      return { cls: "file-audio", kind: "audio", label: "♪" };
    }
    const mapped = fileIconByExt[e];
    if (mapped) return textIcon(mapped);
    if (lowerName.startsWith(".")) return { cls: "file-config", kind: "config" };
    return { cls: "file-generic", kind: "generic" };
  },
};

export const skinPlugins = [forgeSkin] as const;
export const activeSkin = skinPlugins[0];

export function installSkinPlugin(plugin: SkinPlugin = activeSkin): void {
  const root = document.documentElement;
  root.dataset.skin = plugin.id;
  for (const [name, value] of Object.entries(plugin.cssVars)) {
    root.style.setProperty(name, value);
  }
}
