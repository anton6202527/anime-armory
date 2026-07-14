import { useEffect, useMemo, useState } from "react";
import { openWorkEntry, readQualityInsights } from "../api";
import { useI18n } from "../i18n";
import type {
  LineKey,
  QualityInsightDimension,
  QualityInsightMetric,
  QualityInsights,
  WorkRoot,
} from "../types";

function fmtScore(score?: number): string {
  if (score == null || !Number.isFinite(score)) return "—";
  return Number.isInteger(score) ? String(score) : score.toFixed(1);
}

function tone(status?: string, blocks = 0, warnings = 0, score?: number): string {
  const value = (status || "").toLowerCase();
  if (blocks > 0 || value.includes("block") || value === "failed" || value === "fail") return "block";
  if (warnings > 0 || value.includes("warn") || value === "needs_revision" || value === "action_required") return "warn";
  if (value === "pass" || value === "ok" || value === "done" || value === "ready" || score != null) return "pass";
  return "info";
}

function metricTone(metric: QualityInsightMetric): string {
  return metric.tone || tone(metric.value);
}

function dimPct(dim: QualityInsightDimension): number {
  if (dim.score == null || !Number.isFinite(dim.score)) return 0;
  const max = dim.max && dim.max > 0 ? dim.max : 100;
  return Math.max(0, Math.min(100, (dim.score / max) * 100));
}

function dimValue(dim: QualityInsightDimension): string {
  if (dim.value) return dim.value;
  if (dim.score == null) return "—";
  if (dim.max && dim.max !== 100) return `${fmtScore(dim.score)} / ${fmtScore(dim.max)}`;
  return fmtScore(dim.score);
}

function hasData(data: QualityInsights | null): boolean {
  if (!data) return false;
  return Boolean(
    data.score != null ||
      data.status ||
      data.verdict ||
      data.metrics.length ||
      data.dimensions.length ||
      data.issues.length ||
      data.tasks.length ||
      data.artifacts.some((item) => item.exists),
  );
}

function sourceLabel(line: LineKey | string, t: ReturnType<typeof useI18n>["t"], ep?: string): string {
  const prefix = line === "novel" ? t("quality.novelSource") : t("quality.productionSource");
  return ep ? `${prefix} · ${ep}` : prefix;
}

export function QualityInsightsPane({
  root,
  line,
  ep,
  refreshKey = 0,
  embedded = false,
}: {
  root: WorkRoot;
  line: LineKey;
  ep?: string | null;
  refreshKey?: number;
  embedded?: boolean;
}) {
  const { t } = useI18n();
  const [data, setData] = useState<QualityInsights | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError("");
    readQualityInsights(root.path, line, ep)
      .then((next) => {
        if (alive) setData(next);
      })
      .catch((e) => {
        if (alive) {
          setData(null);
          setError(String(e));
        }
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [ep, line, refreshKey, root.path]);

  const visibleIssues = useMemo(() => data?.issues.slice(0, 18) ?? [], [data?.issues]);
  const visibleTasks = useMemo(() => data?.tasks.slice(0, 12) ?? [], [data?.tasks]);
  const visibleArtifacts = useMemo(
    () => data?.artifacts.filter((item) => item.exists || item.kind !== "visual").slice(0, 16) ?? [],
    [data?.artifacts],
  );

  if (loading && !data) {
    return <div className={embedded ? "quality-insights embedded" : "quality-insights-pane"}>{t("common.loading")}</div>;
  }
  if (error) {
    return (
      <div className={embedded ? "quality-insights embedded" : "quality-insights-pane"}>
        <div className="stub-view">{t("common.readFailed", { error })}</div>
      </div>
    );
  }
  if (!hasData(data)) {
    return (
      <div className={embedded ? "quality-insights embedded" : "quality-insights-pane"}>
        <div className="stub-view">{t("quality.noData")}</div>
      </div>
    );
  }

  const summaryTone = tone(data?.status || data?.verdict, data?.blocks ?? 0, data?.warnings ?? 0, data?.score);
  return (
    <div className={embedded ? "quality-insights embedded" : "quality-insights-pane"}>
      <section className="qi-hero">
        <div className={"qi-score " + summaryTone}>
          <span>{sourceLabel(line, t, data?.episode || ep || undefined)}</span>
          <b>{fmtScore(data?.score)}</b>
          <em>{data?.verdict || data?.status || "—"}</em>
        </div>
        <div className="qi-metric-grid">
          <div><span>{t("review.status")}</span><b>{data?.status || "—"}</b></div>
          <div><span>{t("review.blocksLabel")}</span><b className={(data?.blocks ?? 0) ? "block" : ""}>{data?.blocks ?? 0}</b></div>
          <div><span>{t("review.warningsLabel")}</span><b className={(data?.warnings ?? 0) ? "warn" : ""}>{data?.warnings ?? 0}</b></div>
          <div><span>{t("review.infosLabel")}</span><b>{data?.infos ?? 0}</b></div>
          {(data?.metrics ?? []).slice(0, 12).map((metric) => (
            <div key={`${metric.label}-${metric.value}`}>
              <span>{metric.label}</span>
              <b className={metricTone(metric)}>{metric.value}</b>
            </div>
          ))}
        </div>
      </section>

      {(data?.dimensions ?? []).length > 0 && (
        <section className="qi-section">
          <h3>{t("quality.dimensionHeatmap")}</h3>
          <div className="qi-dimension-list">
            {data!.dimensions.map((dim) => {
              const dimTone = tone(dim.status, dim.blocks, dim.warnings, dim.score);
              return (
                <article className={"qi-dimension " + dimTone} key={`${dim.key || dim.label}-${dim.value || dim.score || ""}`}>
                  <div className="qi-dim-head">
                    <strong>{dim.label}</strong>
                    <span>{dimValue(dim)}</span>
                  </div>
                  <div className="qi-bar" aria-hidden="true">
                    <i style={{ width: `${dimPct(dim)}%` }} />
                  </div>
                  <div className="qi-dim-meta">
                    <span>{dim.status || dimTone}</span>
                    <span>{t("review.blocks", { count: dim.blocks })}</span>
                    <span>{t("review.warnings", { count: dim.warnings })}</span>
                    {dim.infos > 0 && <span>{t("review.infos", { count: dim.infos })}</span>}
                  </div>
                  {dim.detail && <p>{dim.detail}</p>}
                  {dim.evidence.length > 0 && <small>{dim.evidence.slice(0, 3).join(" · ")}</small>}
                </article>
              );
            })}
          </div>
        </section>
      )}

      <section className="qi-section two-col">
        <div>
          <h3>{t("quality.issueQueue")}</h3>
          {visibleIssues.length === 0 ? (
            <div className="episode-empty">{t("quality.noIssues")}</div>
          ) : (
            <div className="qi-issue-list">
              {visibleIssues.map((issue, idx) => (
                <article className={"qi-issue " + tone(issue.severity)} key={`${issue.title}-${idx}`}>
                  <span>{issue.severity}</span>
                  <div>
                    <strong>{issue.dimension ? `${issue.dimension} · ${issue.title}` : issue.title}</strong>
                    {issue.message && <p>{issue.message}</p>}
                    {(issue.stage || issue.path || issue.source) && (
                      <small>{[issue.stage && t("review.returnTo", { stage: issue.stage }), issue.path, issue.source].filter(Boolean).join(" · ")}</small>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
        <div>
          <h3>{t("quality.reworkEvidence")}</h3>
          {visibleTasks.length === 0 ? (
            <div className="episode-empty">{t("quality.noReturnTasks")}</div>
          ) : (
            visibleTasks.map((task, idx) => (
              <article className="qi-task" key={`${task.title}-${idx}`}>
                <strong>{task.title}</strong>
                <p>{[task.priority, task.skill, task.stage && t("review.returnTo", { stage: task.stage })].filter(Boolean).join(" · ")}</p>
                {task.detail && <small>{task.detail}</small>}
              </article>
            ))
          )}
          <div className="qi-artifacts">
            {visibleArtifacts.map((artifact) => (
              <button
                type="button"
                key={artifact.path}
                disabled={!artifact.exists}
                title={artifact.path}
                onClick={() => openWorkEntry(root.path, artifact.path)}
              >
                <span>{artifact.label}</span>
                <b>{artifact.exists ? t("common.open") : t("common.missing")}</b>
              </button>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
