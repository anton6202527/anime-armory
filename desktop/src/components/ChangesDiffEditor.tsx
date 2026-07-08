import { useEffect, useMemo, useRef } from "react";
import { editorAccessoryOptions, editorThemeName, installEditorAccessories } from "../editorAccessories";
import { languageForFile, monaco } from "../monaco";
import type { WorkChangeDetail } from "../types";

export function ChangesDiffEditor({ detail }: { detail: WorkChangeDetail }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<monaco.editor.IStandaloneDiffEditor | null>(null);
  const modelsRef = useRef<{ original: monaco.editor.ITextModel; modified: monaco.editor.ITextModel } | null>(null);
  const language = useMemo(() => languageForFile(detail.path), [detail.path]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    installEditorAccessories();
    const editor = monaco.editor.createDiffEditor(host, {
      ...editorAccessoryOptions,
      automaticLayout: true,
      diffWordWrap: "on",
      fontFamily: "Menlo, Monaco, 'SF Mono', Consolas, monospace",
      fontSize: 12,
      hideCursorInOverviewRuler: true,
      ignoreTrimWhitespace: false,
      lineHeight: 19,
      minimap: { enabled: false },
      originalEditable: false,
      overviewRulerBorder: false,
      overviewRulerLanes: 0,
      readOnly: true,
      renderSideBySide: true,
      scrollBeyondLastLine: false,
      scrollbar: {
        horizontal: "visible",
        horizontalScrollbarSize: 10,
        horizontalSliderSize: 10,
        useShadows: false,
        vertical: "visible",
        verticalScrollbarSize: 10,
        verticalSliderSize: 10,
      },
      theme: editorThemeName,
    });
    editorRef.current = editor;
    return () => {
      modelsRef.current?.original.dispose();
      modelsRef.current?.modified.dispose();
      editor.dispose();
      editorRef.current = null;
      modelsRef.current = null;
    };
  }, []);

  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    modelsRef.current?.original.dispose();
    modelsRef.current?.modified.dispose();
    const baseUri = monaco.Uri.file(detail.path);
    const original = monaco.editor.createModel(detail.old_text, language, baseUri.with({ scheme: "archive" }));
    const modified = monaco.editor.createModel(detail.new_text, language, baseUri.with({ scheme: "current" }));
    modelsRef.current = { original, modified };
    editor.setModel({ original, modified });
  }, [detail, language]);

  return <div className="change-diff-host" ref={hostRef} />;
}
