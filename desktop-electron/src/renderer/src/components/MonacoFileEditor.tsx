import { useEffect, useMemo, useRef, useState } from "react";
import { writeWorkFile } from "../api";
import {
  editorAccessoryOptions,
  editorThemeName,
  installEditorAccessories,
  vscodeEditorFontOptions,
} from "../editorAccessories";
import { useI18n } from "../i18n";
import type { SkillTreeEntry, WorkFileWriteResult } from "../types";
import { languageForFile, monaco } from "../monaco";

type SaveState = "clean" | "dirty" | "saving" | "saved" | "error";

export function MonacoFileEditor({
  rootPath,
  entry,
  absPath,
  text,
  loadVersion,
  expectedMtime,
  navigateTo,
  onContentChange,
  onCursorLineChange,
  onDirtyChange,
  onSaved,
}: {
  rootPath: string;
  entry: SkillTreeEntry;
  absPath: string;
  text: string;
  loadVersion: string;
  expectedMtime: number;
  navigateTo?: { line: number; request: number } | null;
  onContentChange?: (text: string) => void;
  onCursorLineChange?: (line: number) => void;
  onDirtyChange?: (dirty: boolean) => void;
  onSaved: (result: WorkFileWriteResult, savedText: string) => void;
}) {
  const { t } = useI18n();
  const containerRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const modelRef = useRef<monaco.editor.ITextModel | null>(null);
  const changeDisposableRef = useRef<monaco.IDisposable | null>(null);
  const cursorDisposableRef = useRef<monaco.IDisposable | null>(null);
  const cursorFrameRef = useRef<number | null>(null);
  const contentTimerRef = useRef<number | null>(null);
  const onContentChangeRef = useRef(onContentChange);
  const onCursorLineChangeRef = useRef(onCursorLineChange);
  const currentFileIdRef = useRef("");
  const currentLoadVersionRef = useRef("");
  const editorInstanceIdRef = useRef(Math.random().toString(36).slice(2));
  const cleanTextRef = useRef(text);
  const expectedMtimeRef = useRef(expectedMtime);
  const dirtyRef = useRef(false);
  const saveRef = useRef<() => void>(() => {});
  const [editorReady, setEditorReady] = useState(0);
  const [, setDirty] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>("clean");
  const [error, setError] = useState("");
  const [, setDiskChanged] = useState(false);

  const fileId = `${rootPath}\0${entry.path}`;
  const language = useMemo(() => languageForFile(entry.name), [entry.name]);
  onContentChangeRef.current = onContentChange;
  onCursorLineChangeRef.current = onCursorLineChange;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    installEditorAccessories();
    const editor = monaco.editor.create(container, {
      ...editorAccessoryOptions,
      ...vscodeEditorFontOptions,
      automaticLayout: true,
      bracketPairColorization: { enabled: true },
      cursorBlinking: "smooth",
      glyphMargin: false,
      guides: { indentation: true },
      largeFileOptimizations: true,
      minimap: { enabled: false },
      overviewRulerBorder: false,
      renderLineHighlight: "line",
      renderWhitespace: "selection",
      scrollBeyondLastLine: false,
      smoothScrolling: true,
      stickyScroll: { enabled: false },
      tabSize: 2,
      theme: editorThemeName,
      wordWrap: "on",
    });
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => saveRef.current());
    cursorDisposableRef.current = editor.onDidChangeCursorPosition((event) => {
      if (cursorFrameRef.current !== null) window.cancelAnimationFrame(cursorFrameRef.current);
      cursorFrameRef.current = window.requestAnimationFrame(() => {
        cursorFrameRef.current = null;
        onCursorLineChangeRef.current?.(event.position.lineNumber);
      });
    });
    editorRef.current = editor;
    setEditorReady((n) => n + 1);
    return () => {
      changeDisposableRef.current?.dispose();
      cursorDisposableRef.current?.dispose();
      if (cursorFrameRef.current !== null) window.cancelAnimationFrame(cursorFrameRef.current);
      if (contentTimerRef.current !== null) window.clearTimeout(contentTimerRef.current);
      modelRef.current?.dispose();
      editor.dispose();
      editorRef.current = null;
      modelRef.current = null;
    };
  }, []);

  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    if (currentFileIdRef.current !== fileId) {
      changeDisposableRef.current?.dispose();
      modelRef.current?.dispose();
      const uri = monaco.Uri.file(absPath).with({ query: editorInstanceIdRef.current });
      const model = monaco.editor.createModel(text, language, uri);
      cleanTextRef.current = text;
      expectedMtimeRef.current = expectedMtime;
      dirtyRef.current = false;
      currentFileIdRef.current = fileId;
      currentLoadVersionRef.current = loadVersion;
      setDirty(false);
      setDiskChanged(false);
      setError("");
      setSaveState("clean");
      editor.setModel(model);
      onCursorLineChangeRef.current?.(1);
      modelRef.current = model;
      changeDisposableRef.current = model.onDidChangeContent(() => {
        const value = model.getValue();
        const isDirty = value !== cleanTextRef.current;
        dirtyRef.current = isDirty;
        setDirty(isDirty);
        onDirtyChange?.(isDirty);
        if (isDirty) setSaveState("dirty");
        else setSaveState("clean");
        if (contentTimerRef.current !== null) window.clearTimeout(contentTimerRef.current);
        contentTimerRef.current = window.setTimeout(() => {
          contentTimerRef.current = null;
          onContentChangeRef.current?.(value);
        }, 220);
      });
      return;
    }

    if (currentLoadVersionRef.current !== loadVersion) {
      expectedMtimeRef.current = expectedMtime;
      currentLoadVersionRef.current = loadVersion;
      if (dirtyRef.current) {
        setDiskChanged(true);
        return;
      }
      const model = modelRef.current;
      if (!model) return;
      cleanTextRef.current = text;
      model.setValue(text);
      monaco.editor.setModelLanguage(model, language);
      setDirty(false);
      setDiskChanged(false);
      setError("");
      setSaveState("clean");
      onDirtyChange?.(false);
      return;
    }

    const model = modelRef.current;
    if (!model || dirtyRef.current || text === cleanTextRef.current) return;
    cleanTextRef.current = text;
    model.setValue(text);
    monaco.editor.setModelLanguage(model, language);
    setDirty(false);
    setDiskChanged(false);
    setError("");
    setSaveState("clean");
    onDirtyChange?.(false);
  }, [absPath, editorReady, expectedMtime, fileId, language, loadVersion, onDirtyChange, text]);

  useEffect(() => {
    const editor = editorRef.current;
    const model = modelRef.current;
    if (!editor || !model || !navigateTo || currentFileIdRef.current !== fileId) return;
    const line = Math.max(1, Math.min(model.getLineCount(), navigateTo.line));
    editor.setPosition({ lineNumber: line, column: 1 });
    editor.revealLineInCenterIfOutsideViewport(line);
    editor.focus();
  }, [editorReady, fileId, navigateTo?.request]);

  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    const frame = window.requestAnimationFrame(() => editor.layout());
    const timer = window.setTimeout(() => editor.layout(), 80);
    return () => {
      window.cancelAnimationFrame(frame);
      window.clearTimeout(timer);
    };
  }, [editorReady, fileId, loadVersion, text]);

  useEffect(() => {
    saveRef.current = () => {
      const model = modelRef.current;
      if (!model || saveState === "saving" || !dirtyRef.current) return;
      const value = model.getValue();
      setSaveState("saving");
      setError("");
      writeWorkFile(rootPath, entry.path, value, expectedMtimeRef.current)
        .then((result) => {
          cleanTextRef.current = value;
          expectedMtimeRef.current = result.mtime;
          dirtyRef.current = false;
          setDirty(false);
          setDiskChanged(false);
          setSaveState("saved");
          onDirtyChange?.(false);
          onSaved(result, value);
          window.setTimeout(() => setSaveState("clean"), 900);
        })
        .catch((e) => {
          setError(String(e));
          setSaveState("error");
        });
    };
  }, [entry.path, onDirtyChange, onSaved, rootPath, saveState]);

  return (
    <div className="monaco-file-editor">
      {error && <div className="editor-error">{t("files.editorSaveFailed", { error })}</div>}
      <div className="monaco-host" ref={containerRef} />
    </div>
  );
}
