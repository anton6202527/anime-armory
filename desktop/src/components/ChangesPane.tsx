import { useEffect, useMemo, useRef, useState } from "react";
import { archiveWorkChanges, readWorkChange, workChanges } from "../api";
import { useI18n } from "../i18n";
import { languageForFile, monaco } from "../monaco";
import type { WorkChangeDetail, WorkChangeEntry, WorkChangeSummary, WorkRoot } from "../types";

function fileName(path: string): string {
  const i = path.lastIndexOf("/");
  return i < 0 ? path : path.slice(i + 1);
}

function formatBytes(value?: number | null): string {
  if (value == null) return "-";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function DiffEditor({ detail }: { detail: WorkChangeDetail }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<monaco.editor.IStandaloneDiffEditor | null>(null);
  const modelsRef = useRef<{ original: monaco.editor.ITextModel; modified: monaco.editor.ITextModel } | null>(null);
  const language = useMemo(() => languageForFile(detail.path), [detail.path]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const editor = monaco.editor.createDiffEditor(host, {
      automaticLayout: true,
      diffWordWrap: "on",
      fontFamily: "Menlo, Monaco, 'SF Mono', Consolas, monospace",
      fontSize: 12,
      ignoreTrimWhitespace: false,
      lineHeight: 19,
      minimap: { enabled: false },
      originalEditable: false,
      readOnly: true,
      renderSideBySide: true,
      scrollBeyondLastLine: false,
      theme: "anime-armory-forge",
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

export function ChangesPane({
  root,
  refreshKey,
  summary,
  onArchived,
}: {
  root: WorkRoot;
  refreshKey: number;
  summary: WorkChangeSummary | null;
  onArchived: (summary: WorkChangeSummary) => void;
}) {
  const { t } = useI18n();
  const [changes, setChanges] = useState<WorkChangeEntry[]>([]);
  const [selected, setSelected] = useState("");
  const [detail, setDetail] = useState<WorkChangeDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [archiving, setArchiving] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setErr("");
    workChanges(root.path)
      .then((result) => {
        if (!alive) return;
        setChanges(result.changes);
        setSelected((prev) => {
          if (prev && result.changes.some((change) => change.path === prev)) return prev;
          return result.changes[0]?.path ?? "";
        });
      })
      .catch((e) => alive && setErr(String(e)))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [refreshKey, root.path]);

  useEffect(() => {
    setDetail(null);
    setDetailError("");
    if (!selected) return;
    let alive = true;
    readWorkChange(root.path, selected)
      .then((next) => alive && setDetail(next))
      .catch((e) => alive && setDetailError(String(e)));
    return () => {
      alive = false;
    };
  }, [root.path, selected]);

  async function archive() {
    if (changes.length === 0 || archiving) return;
    const ok = window.confirm(t("changes.archiveConfirm", { count: changes.length }));
    if (!ok) return;
    setArchiving(true);
    setErr("");
    try {
      const result = await archiveWorkChanges(root.path);
      setChanges([]);
      setSelected("");
      setDetail(null);
      onArchived(result);
    } catch (e) {
      setErr(String(e));
    } finally {
      setArchiving(false);
    }
  }

  const selectedEntry = changes.find((change) => change.path === selected) ?? null;
  const count = summary ? summary.changed + summary.deleted : changes.length;
  const kindLabel = {
    added: t("changes.kind.added"),
    modified: t("changes.kind.modified"),
    deleted: t("changes.kind.deleted"),
    unchanged: t("changes.kind.unchanged"),
  };

  return (
    <div className="changes-pane">
      <div className="changes-side">
        <div className="changes-toolbar">
          <span className={"changes-count" + (changes.length ? " dirty" : "")}>
            {loading ? t("common.loading") : t("changes.count", { count })}
          </span>
          <button type="button" disabled={!changes.length || archiving} onClick={archive}>
            {archiving ? t("changes.archiving") : t("changes.archive")}
          </button>
        </div>
        {err && <div className="changes-error">{err}</div>}
        {!loading && !err && changes.length === 0 && (
          <div className="changes-empty">{t("changes.empty")}</div>
        )}
        <div className="changes-list">
          {changes.map((change) => (
            <button
              type="button"
              key={change.path}
              className={"change-row" + (change.path === selected ? " active" : "")}
              onClick={() => setSelected(change.path)}
              title={change.path}
            >
              <span className={`change-kind ${change.kind}`}>{kindLabel[change.kind]}</span>
              <span className="change-name">{fileName(change.path)}</span>
              <span className="change-path">{change.path}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="changes-detail">
        {!selectedEntry ? (
          <div className="changes-empty">{t("changes.select")}</div>
        ) : detailError ? (
          <div className="changes-empty">{t("common.readFailed", { error: detailError })}</div>
        ) : !detail ? (
          <div className="changes-empty">{t("common.loading")}</div>
        ) : !detail.text_available ? (
          <div className="change-meta-only">
            <h3>{detail.path}</h3>
            <p>{detail.message || t("changes.noTextDiff")}</p>
            <div className="change-meta-grid">
              <span>{t("changes.oldSize")}</span>
              <b>{formatBytes(selectedEntry.old_size)}</b>
              <span>{t("changes.newSize")}</span>
              <b>{formatBytes(selectedEntry.new_size)}</b>
            </div>
          </div>
        ) : (
          <DiffEditor detail={detail} />
        )}
      </div>
    </div>
  );
}
