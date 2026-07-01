import * as monaco from "monaco-editor/esm/vs/editor/editor.api.js";
import editorWorker from "monaco-editor/esm/vs/editor/editor.worker.js?worker";
import cssWorker from "monaco-editor/esm/vs/language/css/css.worker.js?worker";
import htmlWorker from "monaco-editor/esm/vs/language/html/html.worker.js?worker";
import jsonWorker from "monaco-editor/esm/vs/language/json/json.worker.js?worker";
import tsWorker from "monaco-editor/esm/vs/language/typescript/ts.worker.js?worker";
import "monaco-editor/esm/vs/basic-languages/_.contribution.js";
import "monaco-editor/esm/vs/language/css/monaco.contribution.js";
import "monaco-editor/esm/vs/language/html/monaco.contribution.js";
import "monaco-editor/esm/vs/language/json/monaco.contribution.js";
import "monaco-editor/esm/vs/language/typescript/monaco.contribution.js";
import { activeSkin } from "./skins";

const scope = self as unknown as { MonacoEnvironment?: monaco.Environment };
scope.MonacoEnvironment = {
  getWorker(_workerId: string, label: string) {
    if (label === "json") return new jsonWorker();
    if (label === "css" || label === "scss" || label === "less") return new cssWorker();
    if (label === "html" || label === "handlebars" || label === "razor") return new htmlWorker();
    if (label === "typescript" || label === "javascript") return new tsWorker();
    return new editorWorker();
  },
};

monaco.editor.defineTheme(activeSkin.monacoThemeName, activeSkin.monacoTheme);

export function languageForFile(name: string): string {
  const lower = name.toLowerCase();
  const i = lower.lastIndexOf(".");
  const ext = i < 0 ? "" : lower.slice(i + 1);
  if (["md", "markdown", "mdx"].includes(ext)) return "markdown";
  if (["json", "jsonl"].includes(ext)) return "json";
  if (["js", "jsx", "mjs", "cjs"].includes(ext)) return "javascript";
  if (["ts", "tsx"].includes(ext)) return "typescript";
  if (["css", "scss", "less"].includes(ext)) return ext;
  if (["html", "htm"].includes(ext)) return "html";
  if (["yml", "yaml"].includes(ext)) return "yaml";
  if (["sh", "bash", "zsh"].includes(ext)) return "shell";
  if (ext === "py") return "python";
  if (ext === "rs") return "rust";
  if (ext === "swift") return "swift";
  if (ext === "xml") return "xml";
  if (ext === "toml" || ext === "ini" || ext === "env") return "ini";
  return "plaintext";
}

export { monaco };
