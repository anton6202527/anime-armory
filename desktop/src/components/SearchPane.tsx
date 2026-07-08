import { useEffect, useMemo, useState } from "react";
import { openWorkEntry, readWorkFile, revealWorkEntry, searchWorkFiles, writeWorkFile } from "../api";
import { useI18n } from "../i18n";
import type { WorkRoot, WorkSearchResponse } from "../types";
import { Codicon } from "./Codicon";

function formatSize(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function parentPath(path: string): string {
  const idx = path.lastIndexOf("/");
  return idx < 0 ? "" : path.slice(0, idx);
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function SearchPane({
  root,
  refreshKey,
}: {
  root: WorkRoot;
  refreshKey: number;
}) {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [replaceOpen, setReplaceOpen] = useState(true);
  const [replaceText, setReplaceText] = useState("");
  const [caseSensitive, setCaseSensitive] = useState(false);
  const [wholeWord, setWholeWord] = useState(false);
  const [useRegex, setUseRegex] = useState(false);
  const [preserveCase, setPreserveCase] = useState(false);
  const [replaceBusy, setReplaceBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [response, setResponse] = useState<WorkSearchResponse | null>(null);
  const [selectedPath, setSelectedPath] = useState("");

  const results = response?.results ?? [];
  const selected = useMemo(
    () => results.find((result) => result.path === selectedPath) ?? results[0] ?? null,
    [results, selectedPath],
  );

  useEffect(() => {
    setQuery("");
    setReplaceText("");
    setResponse(null);
    setSelectedPath("");
    setErr("");
  }, [root.path]);

  useEffect(() => {
    const clean = query.trim();
    if (!clean) {
      setLoading(false);
      setErr("");
      setResponse(null);
      setSelectedPath("");
      return;
    }
    let alive = true;
    setLoading(true);
    setErr("");
    const timer = window.setTimeout(() => {
      searchWorkFiles(root.path, clean, caseSensitive, wholeWord, useRegex)
        .then((result) => {
          if (!alive) return;
          setResponse(result);
          setSelectedPath((prev) =>
            prev && result.results.some((item) => item.path === prev)
              ? prev
              : result.results[0]?.path ?? "",
          );
        })
        .catch((e) => {
          if (!alive) return;
          setErr(String(e));
          setResponse(null);
          setSelectedPath("");
        })
        .finally(() => {
          if (alive) setLoading(false);
        });
    }, 220);
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [caseSensitive, query, refreshKey, root.path, useRegex, wholeWord]);

  async function runAction(action: () => Promise<void>) {
    try {
      await action();
    } catch (e) {
      window.alert(String(e));
    }
  }

  function replacementPattern(): RegExp | null {
    const clean = query.trim();
    if (!clean) return null;
    const source = useRegex ? clean : escapeRegExp(clean);
    const bounded = wholeWord ? `\\b(?:${source})\\b` : source;
    try {
      return new RegExp(bounded, caseSensitive ? "g" : "gi");
    } catch {
      return null;
    }
  }

  function applyPreserveCase(match: string, replacement: string): string {
    if (!preserveCase || !replacement) return replacement;
    if (match === match.toUpperCase()) return replacement.toUpperCase();
    if (match === match.toLowerCase()) return replacement.toLowerCase();
    if (match[0] === match[0]?.toUpperCase()) {
      return replacement[0]?.toUpperCase() + replacement.slice(1);
    }
    return replacement;
  }

  async function replaceAllResults() {
    const pattern = replacementPattern();
    if (!pattern) {
      window.alert(t("search.invalidPattern"));
      return;
    }
    const targets = results.filter((result) => result.matches.length > 0);
    if (!targets.length) return;
    if (!window.confirm(t("search.replaceConfirm", { count: targets.length }))) return;
    setReplaceBusy(true);
    setErr("");
    let changed = 0;
    try {
      for (const result of targets) {
        const text = await readWorkFile(root.path, result.path);
        const next = text.replace(pattern, (match) => applyPreserveCase(match, replaceText));
        if (next === text) continue;
        await writeWorkFile(root.path, result.path, next);
        changed += 1;
      }
      const clean = query.trim();
      const nextResponse = clean
        ? await searchWorkFiles(root.path, clean, caseSensitive, wholeWord, useRegex)
        : null;
      setResponse(nextResponse);
      setSelectedPath(nextResponse?.results[0]?.path ?? "");
      window.alert(t("search.replaceDone", { count: changed }));
    } catch (e) {
      setErr(String(e));
    } finally {
      setReplaceBusy(false);
    }
  }

  const status =
    !query.trim()
      ? ""
      : loading
        ? t("common.loading")
        : err
          ? err
          : response
            ? t("search.resultCount", { count: results.length, scanned: response.scanned })
            : "";

  return (
    <div className="search-pane">
      <aside className="search-side">
        <div className="search-view-title">
          <span>{t("search.title")}</span>
          <div className="search-view-actions">
            <button
              type="button"
              title={t("search.refresh")}
              aria-label={t("search.refresh")}
              onClick={() => {
                const clean = query.trim();
                if (!clean) return;
                setLoading(true);
                searchWorkFiles(root.path, clean, caseSensitive, wholeWord, useRegex)
                  .then((result) => {
                    setResponse(result);
                    setSelectedPath(result.results[0]?.path ?? "");
                  })
                  .catch((e) => setErr(String(e)))
                  .finally(() => setLoading(false));
              }}
            >
              <Codicon name="refresh" />
            </button>
            <button
              type="button"
              title={t("search.clear")}
              aria-label={t("search.clear")}
              onClick={() => {
                setQuery("");
                setResponse(null);
                setSelectedPath("");
              }}
            >
              <Codicon name="clearAll" />
            </button>
            <button type="button" title={t("search.collapse")} aria-label={t("search.collapse")}>
              <Codicon name="collapseAll" />
            </button>
          </div>
        </div>
        <div className="search-head">
          <div className="search-row">
            <button
              type="button"
              className="search-disclosure"
              title={replaceOpen ? t("common.collapse") : t("common.expand")}
              aria-label={replaceOpen ? t("common.collapse") : t("common.expand")}
              aria-expanded={replaceOpen}
              onClick={() => setReplaceOpen((value) => !value)}
            >
              <Codicon name={replaceOpen ? "chevronDown" : "chevronRight"} />
            </button>
            <div className="search-box">
              <input
                className="search-input"
                value={query}
                placeholder={t("search.searchPlaceholder")}
                aria-label={t("search.searchPlaceholder")}
                onChange={(event) => setQuery(event.target.value)}
              />
              <div className="search-box-actions" aria-label={t("search.options")}>
                <button
                  type="button"
                  className={"search-inline-action search-text-action" + (caseSensitive ? " active" : "")}
                  title={t("search.caseSensitive")}
                  aria-pressed={caseSensitive}
                  onClick={() => setCaseSensitive((value) => !value)}
                >
                  Aa
                </button>
                <button
                  type="button"
                  className={"search-inline-action" + (wholeWord ? " active" : "")}
                  title={t("search.wholeWord")}
                  aria-pressed={wholeWord}
                  onClick={() => setWholeWord((value) => !value)}
                >
                  <Codicon name="wholeWord" />
                </button>
                <button
                  type="button"
                  className={"search-inline-action" + (useRegex ? " active" : "")}
                  title={t("search.regex")}
                  aria-pressed={useRegex}
                  onClick={() => setUseRegex((value) => !value)}
                >
                  <Codicon name="regex" />
                </button>
              </div>
            </div>
          </div>
          {replaceOpen && (
            <div className="search-row search-replace-row">
              <span className="search-disclosure-spacer" />
              <div className="search-box">
                <input
                  className="search-input"
                  value={replaceText}
                  placeholder={t("search.replacePlaceholder")}
                  aria-label={t("search.replacePlaceholder")}
                  onChange={(event) => setReplaceText(event.target.value)}
                />
                <div className="search-box-actions">
                  <button
                    type="button"
                    className={"search-inline-action search-text-action" + (preserveCase ? " active" : "")}
                    title={t("search.preserveCase")}
                    aria-pressed={preserveCase}
                    onClick={() => setPreserveCase((value) => !value)}
                  >
                    AB
                  </button>
                  <button
                    type="button"
                    className="search-inline-action"
                    title={t("search.replaceAll")}
                    aria-label={t("search.replaceAll")}
                    disabled={replaceBusy || !query.trim() || results.every((result) => result.matches.length === 0)}
                    onClick={replaceAllResults}
                  >
                    <Codicon name="replaceAll" />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
        {(status || response?.capped) && (
          <div className={"search-status" + (err ? " error" : "")}>
            {status}
            {response?.capped ? ` · ${t("search.capped")}` : ""}
          </div>
        )}
        <div className="search-results">
          {results.map((result) => (
            <button
              type="button"
              key={result.path}
              className={"search-result" + (selected?.path === result.path ? " active" : "")}
              onClick={() => setSelectedPath(result.path)}
              onDoubleClick={() => runAction(() => openWorkEntry(root.path, result.path))}
              title={result.path}
            >
              <span className="search-result-name">{result.name}</span>
              <span className="search-result-path">{parentPath(result.path)}</span>
              <span className="search-result-meta">
                {result.name_match ? t("search.nameMatch") : ""}
                {result.matches.length ? t("search.matchCount", { count: result.matches.length }) : ""}
              </span>
            </button>
          ))}
        </div>
      </aside>
      <section className="search-detail">
        {!selected ? (
          <div className="search-empty">{query.trim() ? t("search.noResult") : t("search.select")}</div>
        ) : (
          <>
            <div className="search-detail-head">
              <div className="search-detail-title">
                <strong>{selected.name}</strong>
                <span>{selected.path}</span>
              </div>
              <div className="search-detail-actions">
                <span>{formatSize(selected.size)}</span>
                <button type="button" onClick={() => runAction(() => revealWorkEntry(root.path, selected.path))}>
                  {t("files.menuReveal")}
                </button>
                <button type="button" onClick={() => runAction(() => openWorkEntry(root.path, selected.path))}>
                  {t("files.menuOpen")}
                </button>
              </div>
            </div>
            <div className="search-match-list">
              {selected.name_match && (
                <div className="search-match name-hit">
                  <span className="search-match-line">{t("search.fileName")}</span>
                  <code>{selected.path}</code>
                </div>
              )}
              {selected.matches.length === 0 && !selected.name_match ? (
                <div className="search-empty">{t("search.noPreview")}</div>
              ) : (
                selected.matches.map((match) => (
                  <div className="search-match" key={`${selected.path}:${match.line}:${match.preview}`}>
                    <span className="search-match-line">{match.line}</span>
                    <code>{match.preview}</code>
                  </div>
                ))
              )}
            </div>
          </>
        )}
      </section>
    </div>
  );
}
