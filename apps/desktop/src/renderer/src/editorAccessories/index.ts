import { activeSkin } from "../skins";
import { monaco } from "../monaco";

export const editorThemeName = activeSkin.monacoThemeName;
export const jsonLinesLanguageId = "anime-jsonl";

export const editorAccessoryOptions = {
  occurrencesHighlight: "off",
  renderControlCharacters: false,
  selectionHighlight: false,
  unicodeHighlight: {
    ambiguousCharacters: false,
    includeComments: false,
    includeStrings: false,
    invisibleCharacters: false,
    nonBasicASCII: false,
  },
} satisfies monaco.editor.IEditorOptions;

// Keep text rendering aligned with VS Code's macOS editor defaults.  Defining
// these once also prevents the normal editor and the diff editor from slowly
// drifting apart as their option lists evolve.
export const vscodeEditorFontOptions = {
  fontFamily: "Menlo, Monaco, 'Courier New', monospace",
  fontLigatures: false,
  fontSize: 12,
  fontWeight: "normal",
  letterSpacing: 0,
  lineHeight: 0,
} satisfies monaco.editor.IEditorOptions;

let installed = false;

function installJsonLinesLanguage(): void {
  if (!monaco.languages.getLanguages().some((language) => language.id === jsonLinesLanguageId)) {
    monaco.languages.register({
      id: jsonLinesLanguageId,
      aliases: ["JSON Lines", "jsonl"],
      extensions: [".jsonl"],
    });
  }

  monaco.languages.setMonarchTokensProvider(jsonLinesLanguageId, {
    defaultToken: "",
    tokenPostfix: ".jsonl",
    brackets: [
      { open: "{", close: "}", token: "delimiter.bracket" },
      { open: "[", close: "]", token: "delimiter.array" },
    ],
    tokenizer: {
      root: [
        [/\s+/, ""],
        [/"(?:[^"\\]|\\.)*"(?=\s*:)/, "type.identifier"],
        [/"(?:[^"\\]|\\.)*"/, "string"],
        [/-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/, "number"],
        [/\b(?:true|false)\b/, "keyword"],
        [/\bnull\b/, "constant"],
        [/[{}[\]]/, "@brackets"],
        [/[,:]/, "delimiter"],
      ],
    },
  });
}

function installDarkPlusTheme(): void {
  monaco.editor.defineTheme(editorThemeName, {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "", foreground: "d4d4d4", background: activeSkin.monacoTheme.colors["editor.background"]?.slice(1) ?? "121413" },
      { token: "comment", foreground: "6a9955" },
      { token: "keyword", foreground: "c586c0" },
      { token: "constant", foreground: "569cd6" },
      { token: "number", foreground: "b5cea8" },
      { token: "string", foreground: "ce9178" },
      { token: "string.escape", foreground: "d7ba7d" },
      { token: "regexp", foreground: "d16969" },
      { token: "type", foreground: "4ec9b0" },
      { token: "type.identifier", foreground: "9cdcfe" },
      { token: "class", foreground: "4ec9b0" },
      { token: "interface", foreground: "b8d7a3" },
      { token: "namespace", foreground: "4ec9b0" },
      { token: "function", foreground: "dcdcaa" },
      { token: "method", foreground: "dcdcaa" },
      { token: "variable", foreground: "9cdcfe" },
      { token: "variable.predefined", foreground: "4fc1ff" },
      { token: "property", foreground: "9cdcfe" },
      { token: "operator", foreground: "d4d4d4" },
      { token: "delimiter", foreground: "d4d4d4" },
      { token: "delimiter.bracket", foreground: "ffd700" },
      { token: "delimiter.array", foreground: "da70d6" },
      { token: "tag", foreground: "569cd6" },
      { token: "attribute.name", foreground: "9cdcfe" },
      { token: "attribute.value", foreground: "ce9178" },
      { token: "metatag", foreground: "c586c0" },
      { token: "invalid", foreground: "f44747" },
      { token: "header", foreground: "569cd6", fontStyle: "bold" },
      { token: "strong", foreground: "d7ba7d", fontStyle: "bold" },
      { token: "emphasis", foreground: "c586c0", fontStyle: "italic" },
      { token: "quote", foreground: "6a9955" },
      { token: "link", foreground: "4ec9b0" },
    ],
    colors: {
      ...activeSkin.monacoTheme.colors,
      "editorBracketHighlight.foreground1": "#ffd700",
      "editorBracketHighlight.foreground2": "#b9bac0",
      "editorBracketHighlight.foreground3": "#179fff",
      "editorBracketHighlight.foreground4": "#4ec9b0",
      "editorBracketHighlight.foreground5": "#8f8f98",
      "editorBracketHighlight.foreground6": "#ce9178",
      "editorUnicodeHighlight.border": "#00000000",
      "editorUnicodeHighlight.background": "#00000000",
      "editor.wordHighlightBackground": "#00000000",
      "editor.wordHighlightStrongBackground": "#00000000",
      "editor.wordHighlightBorder": "#00000000",
      "editor.wordHighlightStrongBorder": "#00000000",
    },
  });
  monaco.editor.setTheme(editorThemeName);
}

export function installEditorAccessories(): void {
  if (installed) return;
  installed = true;
  installJsonLinesLanguage();
  installDarkPlusTheme();
}
