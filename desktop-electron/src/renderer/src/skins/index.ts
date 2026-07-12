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
    "--accent": "#0078d4",
    "--active-bar": "#0078d4",
    "--splitter-active": "#0078d4",
    "--activity-fg": "#d7d7d7",
    "--activity-inactive": "#868686",
    "--block": "#f85149",
    "--warn": "#cca700",
    "--info": "#0078d4",
    "--good": "#4ec9b0",
    "--tree-indent-guide": "#404040",
    "--editor-line": "#2b2b2b",
    "--editor-selection": "#04395e",
    "--input-bg": "#313131",
    "--input-border": "#3c3c3c",
    "--list-hover-bg": "#2a2d2e",
    "--list-focus-bg": "#37373d",
    "--list-active-bg": "#04395e",
    "--folder-icon": "#78b7ff",
    "--file-icon": "#d4d7d6",
    "--file-code-icon": "#d7ba7d",
    "--file-image-icon": "#a074c4",
    "--file-video-icon": "#ff6f9f",
    "--file-audio-icon": "#a074c4",
    "--file-md-icon": "#519aba",
    "--file-json-icon": "#cbcb41",
    "--file-js-icon": "#cbcb41",
    "--file-ts-icon": "#519aba",
    "--file-html-icon": "#e37933",
    "--file-css-icon": "#519aba",
    "--file-python-icon": "#519aba",
    "--file-rust-icon": "#6d8086",
    "--file-shell-icon": "#8dc149",
    "--file-yaml-icon": "#a074c4",
    "--file-config-icon": "#6d8086",
    "--scm-untracked": "#89d185",
    "--scm-modified": "#cca700",
    "--scm-deleted": "#f48771",
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
      "editorCursor.foreground": "#0078d4",
      "editor.selectionBackground": "#264f78",
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
