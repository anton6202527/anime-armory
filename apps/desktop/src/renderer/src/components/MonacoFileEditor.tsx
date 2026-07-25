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

// ── Per-tab document cache（VSCode 语义）────────────────────────────────────
// 此前每次切换文件都 dispose+createModel：已打开 tab 之间来回切也要全文重新
// tokenize，且滚动位置/光标/撤销栈全部丢失——这就是"打开文件稍微卡"的主源。
// 现在 model 以 fileId（rootPath\0relPath）缓存，切回已打开 tab 是 O(1) 的
// setModel + viewState 恢复；未保存的编辑也随 model 存活（切走不再丢改动）。
// 关 tab / 删除 / 改名 / 换作品根时由 FilesPane 调 releaseEditorDocs 归还。
interface CachedDoc {
  model: monaco.editor.ITextModel;
  viewState: monaco.editor.ICodeEditorViewState | null;
  cleanText: string;
  expectedMtime: number;
  loadVersion: string;
  dirty: boolean;
}

const docCache = new Map<string, CachedDoc>();
const DOC_CACHE_MAX = 16; // 全局上限：超出时逐出最久未用且非 dirty、未挂载的 model

function docKey(rootPath: string, relPath: string): string {
  return `${rootPath}\0${relPath}`;
}

function disposeDoc(doc: CachedDoc) {
  if (!doc.model.isDisposed() && !doc.model.isAttachedToEditor()) doc.model.dispose();
}

/** 查缓存里某文件是否带未保存改动（供关 tab 前确认；模块未加载过=必不脏）。 */
export function isEditorDocDirty(rootPath: string, relPath: string): boolean {
  return docCache.get(docKey(rootPath, relPath))?.dirty ?? false;
}

/** Release cached editor models. Omit `paths` to release everything under the root. */
export function releaseEditorDocs(rootPath: string, paths?: string[]) {
  const wanted = paths ? new Set(paths.map((p) => docKey(rootPath, p))) : null;
  for (const [key, doc] of [...docCache]) {
    if (!key.startsWith(`${rootPath}\0`)) continue;
    if (wanted && !wanted.has(key)) continue;
    disposeDoc(doc);
    docCache.delete(key);
  }
}

function evictOverflow(currentKey: string) {
  if (docCache.size <= DOC_CACHE_MAX) return;
  for (const [key, doc] of docCache) {
    if (key === currentKey || doc.dirty) continue;
    if (doc.model.isAttachedToEditor()) continue;
    doc.model.dispose();
    docCache.delete(key);
    if (docCache.size <= DOC_CACHE_MAX) return;
  }
}

export function MonacoFileEditor({
  rootPath,
  entry,
  absPath,
  text,
  textReady,
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
  /** False while FilesPane is still reading the file from disk——磁盘文本未到位
   *  时绝不能拿空串覆盖缓存 model（否则切回 tab 会闪空/丢内容）。 */
  textReady: boolean;
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
  const onDirtyChangeRef = useRef(onDirtyChange);
  const currentFileIdRef = useRef("");
  const currentLoadVersionRef = useRef("");
  const cleanTextRef = useRef(text);
  const expectedMtimeRef = useRef(expectedMtime);
  const dirtyRef = useRef(false);
  const saveRef = useRef<() => void>(() => {});
  const [editorReady, setEditorReady] = useState(0);
  const [, setDirty] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>("clean");
  const [error, setError] = useState("");
  const [, setDiskChanged] = useState(false);

  const fileId = docKey(rootPath, entry.path);
  const language = useMemo(() => languageForFile(entry.name), [entry.name]);
  onContentChangeRef.current = onContentChange;
  onCursorLineChangeRef.current = onCursorLineChange;
  onDirtyChangeRef.current = onDirtyChange;

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
      // 卸载时保存当前 tab 的视图状态供回来时恢复；model 留在缓存里
      // （归还统一走 releaseEditorDocs——由 FilesPane 在关 tab/换根时调用）。
      const doc = docCache.get(currentFileIdRef.current);
      if (doc && editor.getModel() === doc.model) {
        doc.viewState = editor.saveViewState();
        doc.dirty = dirtyRef.current;
        doc.cleanText = cleanTextRef.current;
        doc.expectedMtime = expectedMtimeRef.current;
      }
      editor.setModel(null);
      editor.dispose();
      editorRef.current = null;
      modelRef.current = null;
    };
  }, []);

  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;

    const markClean = (doc: CachedDoc) => {
      dirtyRef.current = false;
      setDirty(false);
      setDiskChanged(false);
      setError("");
      setSaveState("clean");
      doc.dirty = false;
      onDirtyChangeRef.current?.(false);
    };

    // ── 文件切换：缓存命中 = setModel + viewState 恢复（零 tokenize）────────
    if (currentFileIdRef.current !== fileId) {
      const outgoing = docCache.get(currentFileIdRef.current);
      const oldModel = modelRef.current;
      if (outgoing && oldModel === outgoing.model) {
        outgoing.viewState = editor.saveViewState();
        outgoing.dirty = dirtyRef.current;
        outgoing.cleanText = cleanTextRef.current;
        outgoing.expectedMtime = expectedMtimeRef.current;
      }
      changeDisposableRef.current?.dispose();

      let doc = docCache.get(fileId);
      if (!doc) {
        const uri = monaco.Uri.file(absPath).with({ query: rootPath });
        const initialText = textReady ? text : "";
        const model = monaco.editor.getModel(uri) ?? monaco.editor.createModel(initialText, language, uri);
        // 罕见路径：同 URI 的 model 还活着（释放时正挂在编辑器上）——重开时对齐内容。
        if (textReady && model.getValue() !== initialText) model.setValue(initialText);
        doc = {
          model,
          viewState: null,
          cleanText: initialText,
          expectedMtime,
          // 文本未就绪时留空版本号：文本到位后走下方 loadVersion 对账写入。
          loadVersion: textReady ? loadVersion : "",
          dirty: false,
        };
        docCache.set(fileId, doc);
        evictOverflow(fileId);
      } else {
        // LRU bump
        docCache.delete(fileId);
        docCache.set(fileId, doc);
      }

      cleanTextRef.current = doc.cleanText;
      expectedMtimeRef.current = doc.expectedMtime;
      dirtyRef.current = doc.dirty;
      currentFileIdRef.current = fileId;
      currentLoadVersionRef.current = doc.loadVersion;
      setDirty(doc.dirty);
      setDiskChanged(false);
      setError("");
      setSaveState(doc.dirty ? "dirty" : "clean");
      onDirtyChangeRef.current?.(doc.dirty);
      editor.setModel(doc.model);
      if (doc.viewState) editor.restoreViewState(doc.viewState);
      monaco.editor.setModelLanguage(doc.model, language);
      onCursorLineChangeRef.current?.(editor.getPosition()?.lineNumber ?? 1);
      modelRef.current = doc.model;
      // 旧 model 已被 releaseEditorDocs 从缓存移除（关 tab 场景）→ 此刻已脱离
      // 编辑器，补一次 dispose 防泄漏。
      if (!outgoing && oldModel && oldModel !== doc.model && !oldModel.isDisposed()) {
        oldModel.dispose();
      }
      const boundDoc = doc;
      changeDisposableRef.current = boundDoc.model.onDidChangeContent(() => {
        const value = boundDoc.model.getValue();
        const isDirty = value !== cleanTextRef.current;
        dirtyRef.current = isDirty;
        boundDoc.dirty = isDirty;
        setDirty(isDirty);
        onDirtyChangeRef.current?.(isDirty);
        setSaveState(isDirty ? "dirty" : "clean");
        if (contentTimerRef.current !== null) window.clearTimeout(contentTimerRef.current);
        contentTimerRef.current = window.setTimeout(() => {
          contentTimerRef.current = null;
          onContentChangeRef.current?.(value);
        }, 220);
      });
      // 不 return：新建（空 model）场景下若文本已就绪，继续走下方对账立即填充。
    }

    const doc = docCache.get(fileId);
    const model = modelRef.current;
    if (!doc || !model || !textReady) return;

    // ── 磁盘版本对账：mtime/size 变了才动 model；dirty 时只提示不覆盖 ────────
    if (currentLoadVersionRef.current !== loadVersion) {
      expectedMtimeRef.current = expectedMtime;
      doc.expectedMtime = expectedMtime;
      currentLoadVersionRef.current = loadVersion;
      doc.loadVersion = loadVersion;
      if (dirtyRef.current) {
        setDiskChanged(true);
        return;
      }
      cleanTextRef.current = text;
      doc.cleanText = text;
      if (model.getValue() !== text) model.setValue(text);
      monaco.editor.setModelLanguage(model, language);
      markClean(doc);
      return;
    }

    // 同版本下的外部文本更新（如保存回写）：干净时对齐即可。
    if (dirtyRef.current || text === cleanTextRef.current) return;
    cleanTextRef.current = text;
    doc.cleanText = text;
    if (model.getValue() !== text) model.setValue(text);
    monaco.editor.setModelLanguage(model, language);
    markClean(doc);
  }, [absPath, editorReady, expectedMtime, fileId, language, loadVersion, rootPath, text, textReady]);

  useEffect(() => {
    const editor = editorRef.current;
    const model = modelRef.current;
    if (!editor || !model || !navigateTo || currentFileIdRef.current !== fileId) return;
    const line = Math.max(1, Math.min(model.getLineCount(), navigateTo.line));
    editor.setPosition({ lineNumber: line, column: 1 });
    editor.revealLineInCenterIfOutsideViewport(line);
    editor.focus();
  }, [editorReady, fileId, navigateTo?.request]);

  // 文件切换后校正一次布局（容器可能随预览类型切换变了尺寸）；
  // 日常尺寸变化交给 automaticLayout，不再在每次文本变更时重排。
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    const frame = window.requestAnimationFrame(() => editor.layout());
    return () => window.cancelAnimationFrame(frame);
  }, [editorReady, fileId]);

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
          const doc = docCache.get(currentFileIdRef.current);
          if (doc) {
            doc.cleanText = value;
            doc.expectedMtime = result.mtime;
            doc.dirty = false;
          }
          setDirty(false);
          setDiskChanged(false);
          setSaveState("saved");
          onDirtyChangeRef.current?.(false);
          onSaved(result, value);
          window.setTimeout(() => setSaveState("clean"), 900);
        })
        .catch((e) => {
          setError(String(e));
          setSaveState("error");
        });
    };
  }, [entry.path, onSaved, rootPath, saveState]);

  return (
    <div className="monaco-file-editor">
      {error && <div className="editor-error">{t("files.editorSaveFailed", { error })}</div>}
      <div className="monaco-host" ref={containerRef} />
    </div>
  );
}
