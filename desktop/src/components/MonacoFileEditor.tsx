import { useEffect, useMemo, useRef, useState } from "react";
import { writeWorkFile } from "../api";
import { useI18n } from "../i18n";
import { activeSkin } from "../skins";
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
  onDirtyChange,
  onReload,
  onSaved,
}: {
  rootPath: string;
  entry: SkillTreeEntry;
  absPath: string;
  text: string;
  loadVersion: string;
  expectedMtime: number;
  onDirtyChange?: (dirty: boolean) => void;
  onReload: () => void;
  onSaved: (result: WorkFileWriteResult, savedText: string) => void;
}) {
  const { t } = useI18n();
  const containerRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const modelRef = useRef<monaco.editor.ITextModel | null>(null);
  const changeDisposableRef = useRef<monaco.IDisposable | null>(null);
  const currentFileIdRef = useRef("");
  const currentLoadVersionRef = useRef("");
  const cleanTextRef = useRef(text);
  const expectedMtimeRef = useRef(expectedMtime);
  const dirtyRef = useRef(false);
  const saveRef = useRef<() => void>(() => {});
  const [editorReady, setEditorReady] = useState(0);
  const [dirty, setDirty] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>("clean");
  const [error, setError] = useState("");
  const [diskChanged, setDiskChanged] = useState(false);

  const fileId = `${rootPath}\0${entry.path}`;
  const language = useMemo(() => languageForFile(entry.name), [entry.name]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const editor = monaco.editor.create(container, {
      automaticLayout: true,
      bracketPairColorization: { enabled: true },
      cursorBlinking: "smooth",
      fontFamily: "Menlo, Monaco, 'SF Mono', Consolas, monospace",
      fontLigatures: false,
      fontSize: 13,
      glyphMargin: false,
      guides: { indentation: true },
      largeFileOptimizations: true,
      lineHeight: 20,
      minimap: { enabled: false },
      overviewRulerBorder: false,
      renderLineHighlight: "line",
      renderWhitespace: "selection",
      scrollBeyondLastLine: false,
      smoothScrolling: true,
      stickyScroll: { enabled: false },
      tabSize: 2,
      theme: activeSkin.monacoThemeName,
      wordWrap: "on",
    });
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => saveRef.current());
    editorRef.current = editor;
    setEditorReady((n) => n + 1);
    return () => {
      changeDisposableRef.current?.dispose();
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
      const uri = monaco.Uri.file(absPath);
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
      modelRef.current = model;
      changeDisposableRef.current = model.onDidChangeContent(() => {
        const isDirty = model.getValue() !== cleanTextRef.current;
        dirtyRef.current = isDirty;
        setDirty(isDirty);
        onDirtyChange?.(isDirty);
        if (isDirty) setSaveState("dirty");
        else setSaveState("clean");
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
    }
  }, [absPath, editorReady, expectedMtime, fileId, language, loadVersion, onDirtyChange, text]);

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

  const saveLabel =
    saveState === "saving"
      ? t("files.editorSaving")
      : saveState === "saved"
        ? t("files.editorSaved")
        : t("files.editorSave");

  return (
    <div className="monaco-file-editor">
      <div className="editor-toolbar">
        <div className="editor-title" title={entry.path}>
          <span className={"editor-dirty-dot" + (dirty ? " dirty" : "")} aria-hidden="true" />
          <span className="editor-path">{entry.path}</span>
        </div>
        {diskChanged && (
          <button type="button" className="editor-reload" onClick={onReload}>
            {t("files.editorReload")}
          </button>
        )}
        <button
          type="button"
          className="editor-save"
          disabled={!dirty || saveState === "saving"}
          onClick={() => saveRef.current()}
        >
          {saveLabel}
        </button>
      </div>
      {error && <div className="editor-error">{t("files.editorSaveFailed", { error })}</div>}
      <div className="monaco-host" ref={containerRef} />
    </div>
  );
}
