import type { SkillTreeEntry } from "../types";

export type FileIconKind = "image" | "video" | "audio" | "markdown" | "json" | "python" | "code" | "generic";

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
  bash: { cls: "file-shell", label: "$" },
  cjs: { cls: "file-js", label: "JS" },
  css: { cls: "file-css", label: "#" },
  csv: { cls: "file-text", label: "CSV" },
  docx: { cls: "file-text", label: "W" },
  env: { cls: "file-config", label: "." },
  html: { cls: "file-html", label: "<>" },
  js: { cls: "file-js", label: "JS" },
  json: { cls: "file-json", kind: "json", label: "{}" },
  jsonl: { cls: "file-json", kind: "json", label: "{}" },
  jsx: { cls: "file-js", label: "JSX" },
  lock: { cls: "file-lock", label: "L" },
  markdown: { cls: "file-md", kind: "markdown", label: "MD" },
  md: { cls: "file-md", kind: "markdown", label: "MD" },
  mdx: { cls: "file-md", kind: "markdown", label: "MD" },
  mjs: { cls: "file-js", label: "JS" },
  pdf: { cls: "file-text", label: "PDF" },
  pptx: { cls: "file-text", label: "P" },
  py: { cls: "file-py", kind: "python" },
  rs: { cls: "file-rs", label: "RS" },
  scss: { cls: "file-css", label: "S" },
  sh: { cls: "file-shell", label: "$" },
  swift: { cls: "file-code", label: "SW" },
  toml: { cls: "file-config", label: "T" },
  ts: { cls: "file-ts", label: "TS" },
  tsx: { cls: "file-ts", label: "TSX" },
  txt: { cls: "file-text", label: "TXT" },
  xml: { cls: "file-html", label: "<>" },
  xlsx: { cls: "file-text", label: "X" },
  yaml: { cls: "file-yaml", label: "Y" },
  yml: { cls: "file-yaml", label: "Y" },
  zsh: { cls: "file-shell", label: "$" },
};

function textIcon(icon: Omit<SkinFileIcon, "kind"> & { kind?: FileIconKind }): SkinFileIcon {
  return { ...icon, kind: icon.kind ?? "code" };
}

export const forgeSkin: SkinPlugin = {
  id: "forge",
  name: "Forge",
  cssVars: {
    "--editor-bg": "#121413",
    "--sidebar-bg": "#191a1c",
    "--surface-bg": "#222325",
    "--bg": "#121413",
    "--bg-2": "#191a1c",
    "--panel": "#222325",
    "--border": "#2d2f33",
    "--text": "#e3e7ed",
    "--muted": "#929ba8",
    "--accent": "#58a6ff",
    "--block": "#ff6f7d",
    "--warn": "#f2c05b",
    "--info": "#58a6ff",
    "--good": "#4ec9b0",
    "--tree-indent-guide": "rgba(128, 128, 128, .34)",
    "--editor-line": "#222325",
    "--editor-selection": "#27496d",
    "--folder-icon": "#78b7ff",
    "--file-icon": "#a8b3c4",
    "--file-code-icon": "#d7ba7d",
    "--file-image-icon": "#c586d9",
    "--file-video-icon": "#ff6f9f",
    "--file-audio-icon": "#89d185",
    "--file-md-icon": "#6bb6ff",
    "--file-json-icon": "#dcdc60",
    "--file-js-icon": "#f1e05a",
    "--file-ts-icon": "#519aba",
    "--file-html-icon": "#e37933",
    "--file-css-icon": "#519aba",
    "--file-python-icon": "#3572a5",
    "--file-rust-icon": "#dea584",
    "--file-shell-icon": "#89d185",
    "--file-yaml-icon": "#c586c0",
    "--file-config-icon": "#a8b3c4",
    "--scm-untracked": "#89d185",
    "--scm-modified": "#cca700",
    "--scm-deleted": "#f48771",
  },
  monacoThemeName: "anime-armory-forge",
  monacoTheme: {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "", foreground: "e3e7ed", background: "121413" },
      { token: "comment", foreground: "7f8a99" },
      { token: "keyword", foreground: "79c0ff" },
      { token: "string", foreground: "ce9178" },
      { token: "number", foreground: "b5cea8" },
    ],
    colors: {
      "editor.background": "#121413",
      "editor.foreground": "#e3e7ed",
      "editorLineNumber.foreground": "#6f7885",
      "editorLineNumber.activeForeground": "#c8d1dc",
      "editorCursor.foreground": "#58a6ff",
      "editor.selectionBackground": "#27496d",
      "editor.inactiveSelectionBackground": "#243343",
      "editor.lineHighlightBackground": "#222325",
      "editorIndentGuide.background1": "#343b45",
      "editorIndentGuide.activeBackground1": "#5a6574",
      "editorGutter.background": "#121413",
    },
  },
  fileIcon(entry) {
    if (entry.is_dir) return { cls: "file-folder", kind: "generic" };
    const lowerName = entry.name.toLowerCase();
    if (lowerName === "vite.config.ts" || lowerName === "vite.config.js") {
      return textIcon({ cls: "file-js", label: "V" });
    }
    if (lowerName === "package.json" || lowerName === "package-lock.json") {
      return textIcon({ cls: "file-js", label: "npm" });
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
    if (lowerName.startsWith(".")) return textIcon({ cls: "file-config", label: "." });
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
