import { useEffect, useState } from "react";
import { scanWorkspace } from "../api";
import { plainLineLabel, useI18n, useLineLabel } from "../i18n";
import type { LineInfo, LineKey } from "../types";

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
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    setErr("");
    scanWorkspace(workspaceRoot)
      .then((ls) => setLines([...ls].sort((a, b) => lineRank(a.line) - lineRank(b.line))))
      .catch((e) => setErr(String(e)));
  }, [workspaceRoot]);

  return (
    <div className="home">
      <h1>{t("app.name")}</h1>
      {err && <div className="empty">{t("common.scanFailed", { error: err })}</div>}

      <div className="line-grid">
        {lines.map((line) => (
          <div className="line-card" key={line.line}>
            <div className="line-cover">{GLYPH[line.line] ?? "✦"}</div>
            <div className="line-info">
              <div className="line-title">
                <span className="line-title-main">
                  {plainLineLabel(lineLabel(line))}
                  <span className="line-work-count">
                    · {t("common.workCount", { count: line.roots.length })}
                  </span>
                </span>
              </div>
            </div>
            <div className="card-actions">
              <button onClick={() => onShowSkills(line)}>{t("home.skillDetails")}</button>
              <button className="primary" onClick={() => onEnter(line)}>
                {t("home.enterCreation")}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
