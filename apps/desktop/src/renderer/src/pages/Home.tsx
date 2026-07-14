import { useEffect, useState } from "react";
import { installDemo, listDemoDownloads, scanWorkspace } from "../api";
import { plainLineLabel, useI18n, useLineLabel } from "../i18n";
import { isCloudLine, type DemoDownloadInfo, type LineInfo, type LineKey } from "../types";

// Placeholder cover glyph per line (until real cover art is wired).
const GLYPH: Record<string, string> = {
  n2d: "🎬",
  comic: "🖼️",
  ad: "📣",
  mv: "🎵",
  song: "🎤",
  novel: "📖",
};

// Display order: the two local lines (写小说 / 制漫剧) lead, cloud lines follow.
const LINE_ORDER: LineKey[] = ["novel", "n2d", "comic", "ad", "mv", "song"];
const lineRank = (line: LineKey) => {
  const i = LINE_ORDER.indexOf(line);
  return i === -1 ? LINE_ORDER.length : i;
};

export function Home(props: {
  workspaceRoot: string;
  onPickWorkspace: () => void;
  onShowSkills: (line: LineInfo) => void;
  onEnter: (line: LineInfo) => void;
}) {
  const { workspaceRoot, onShowSkills, onEnter } = props;
  const { t } = useI18n();
  const lineLabel = useLineLabel();
  const [lines, setLines] = useState<LineInfo[]>([]);
  const [demos, setDemos] = useState<DemoDownloadInfo[]>([]);
  const [err, setErr] = useState<string>("");
  // Per-line download state so cloud cards can show progress independently.
  const [downloading, setDownloading] = useState<LineKey | null>(null);
  const [downloadErr, setDownloadErr] = useState<Record<string, string>>({});

  function load() {
    setErr("");
    return Promise.all([scanWorkspace(workspaceRoot), listDemoDownloads(workspaceRoot)])
      .then(([ls, ds]) => {
        setLines([...ls].sort((a, b) => lineRank(a.line) - lineRank(b.line)));
        setDemos(ds);
      })
      .catch((e) => setErr(String(e)));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceRoot]);

  // Cloud works available in R2 but not yet on disk, keyed by line.
  const pendingByLine = (line: LineKey) =>
    demos.filter((d) => d.line_key === line && !d.installed);

  async function downloadLine(line: LineKey) {
    if (downloading) return;
    const pending = pendingByLine(line);
    setDownloadErr((prev) => {
      const next = { ...prev };
      delete next[line];
      return next;
    });
    if (pending.length === 0) return;
    setDownloading(line);
    try {
      // Sequential: each install verifies + unpacks before the next starts.
      for (const demo of pending) {
        await installDemo(workspaceRoot, demo.rel);
      }
      await load();
    } catch (e) {
      setDownloadErr((prev) => ({ ...prev, [line]: t("home.downloadLineFailed", { error: String(e) }) }));
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="home">
      <h1>{t("app.name")}</h1>
      {err && <div className="empty">{t("common.scanFailed", { error: err })}</div>}

      <div className="line-grid">
        {lines.map((line) => {
          const cloud = isCloudLine(line.line);
          const pending = cloud ? pendingByLine(line.line) : [];
          const busy = downloading === line.line;
          const lineErr = downloadErr[line.line];
          // Cloud lines stay locked until at least one work is on disk — only
          // then can the user enter that line's works list.
          const locked = cloud && line.roots.length === 0;
          return (
            <div className={"line-card" + (cloud ? " cloud-line" : "") + (locked ? " locked" : "")} key={line.line}>
              <div className="line-cover">{GLYPH[line.line] ?? "✦"}</div>
              <div className="line-info">
                <div className="line-title">
                  <span className="line-title-main">
                    {plainLineLabel(lineLabel(line))}
                    <span className="line-work-count">
                      · {t("common.workCount", { count: line.roots.length })}
                    </span>
                  </span>
                  {cloud && (
                    busy ? (
                      <span className="line-cloud-note">{t("home.downloadingLine")}</span>
                    ) : lineErr ? (
                      <span className="line-cloud-note error">{lineErr}</span>
                    ) : pending.length > 0 ? (
                      <button
                        type="button"
                        className="line-cloud-note dl-link"
                        title={t("home.downloadLine")}
                        aria-label={t("home.downloadLine")}
                        disabled={downloading !== null}
                        onClick={(e) => {
                          e.stopPropagation();
                          void downloadLine(line.line);
                        }}
                      >
                        <svg
                          className="dl-ico"
                          viewBox="0 0 16 16"
                          width="12"
                          height="12"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          aria-hidden="true"
                        >
                          <path d="M8 2.5v7" />
                          <path d="M5 6.5 8 9.5 11 6.5" />
                          <path d="M3 12.5h10" />
                        </svg>
                        <span className="dl-label">{t("home.downloadLine")}</span>
                      </button>
                    ) : (
                      <span className="line-cloud-note done">{t("home.downloadLineDone")}</span>
                    )
                  )}
                </div>
              </div>
              <div className="card-actions">
                <button onClick={() => onShowSkills(line)}>{t("home.skillDetails")}</button>
                <button
                  className="primary"
                  onClick={() => !locked && onEnter(line)}
                  disabled={locked}
                  title={locked ? t("home.enterLocked") : undefined}
                >
                  {t("home.enterCreation")}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
