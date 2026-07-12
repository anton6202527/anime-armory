/// <reference lib="webworker" />

import type {
  BreadcrumbSymbolRequest,
  BreadcrumbSymbolResponse,
  EditorBreadcrumbSymbol,
  EditorBreadcrumbSymbolKind,
} from "./editorBreadcrumbTypes";

const MAX_SYMBOLS = 600;

function extension(name: string): string {
  const index = name.lastIndexOf(".");
  return index < 0 ? "" : name.slice(index + 1).toLowerCase();
}

function indentation(line: string): number {
  const prefix = line.match(/^[\t ]*/)?.[0] ?? "";
  let width = 0;
  for (const char of prefix) width += char === "\t" ? 2 : 1;
  return width;
}

function collectSymbols(name: string, text: string): EditorBreadcrumbSymbol[] {
  const ext = extension(name);
  const lines = text.split(/\r?\n/);
  const symbols: EditorBreadcrumbSymbol[] = [];
  const push = (symbolName: string, line: number, level: number, kind: EditorBreadcrumbSymbolKind) => {
    const clean = symbolName.trim();
    if (!clean || symbols.length >= MAX_SYMBOLS) return;
    symbols.push({ name: clean.slice(0, 180), line, level: Math.max(1, Math.min(12, level)), kind });
  };

  if (["md", "markdown", "mdx"].includes(ext)) {
    for (let index = 0; index < lines.length && symbols.length < MAX_SYMBOLS; index += 1) {
      const match = lines[index].match(/^\s*(#{1,6})\s+(.+?)\s*#*\s*$/);
      if (match) push(match[2], index + 1, match[1].length, "heading");
    }
    return symbols;
  }

  if (["json", "jsonl", "yaml", "yml", "toml"].includes(ext)) {
    for (let index = 0; index < lines.length && symbols.length < MAX_SYMBOLS; index += 1) {
      const line = lines[index];
      const match = line.match(/^\s*(?:["']([^"']+)["']|([\w.-]+))\s*[:=]/);
      if (!match) continue;
      push(match[1] ?? match[2], index + 1, Math.floor(indentation(line) / 2) + 1, "property");
    }
    return symbols;
  }

  const isPython = ext === "py";
  for (let index = 0; index < lines.length && symbols.length < MAX_SYMBOLS; index += 1) {
    const line = lines[index];
    const level = Math.floor(indentation(line) / 2) + 1;
    if (isPython) {
      const match = line.match(/^\s*(?:async\s+)?(class|def)\s+([A-Za-z_]\w*)/);
      if (match) push(match[2], index + 1, level, match[1] === "class" ? "class" : "function");
      continue;
    }

    const declaration = line.match(
      /^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?(class|interface|enum|namespace|function)\s+([A-Za-z_$][\w$]*)/,
    );
    if (declaration) {
      push(
        declaration[2],
        index + 1,
        level,
        ["class", "interface", "enum", "namespace"].includes(declaration[1]) ? "class" : "function",
      );
      continue;
    }
    const assignedFunction = line.match(
      /^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>/,
    );
    if (assignedFunction) {
      push(assignedFunction[1], index + 1, level, "function");
      continue;
    }
    const method = line.match(/^\s*(?:async\s+)?([A-Za-z_$][\w$]*)\s*\([^;{}]*\)\s*(?::[^={]+)?\s*\{/);
    if (method && !["if", "for", "while", "switch", "catch"].includes(method[1])) {
      push(method[1], index + 1, level, "function");
    }
  }
  return symbols;
}

self.onmessage = (event: MessageEvent<BreadcrumbSymbolRequest>) => {
  const response: BreadcrumbSymbolResponse = {
    id: event.data.id,
    symbols: collectSymbols(event.data.name, event.data.text),
  };
  self.postMessage(response);
};

export {};
