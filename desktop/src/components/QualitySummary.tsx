import { useMemo } from "react";
import { useI18n } from "../i18n";
import type { CanvasQualitySummary } from "../types";

function scoreTone(score?: number, blocks = 0, warnings = 0): string {
  if (blocks > 0) return "block";
  if (score == null) return warnings > 0 ? "warn" : "info";
  if (score < 60) return "block";
  if (score < 80 || warnings > 0) return "warn";
  return "pass";
}

function fmtScore(score?: number): string {
  if (score == null || !Number.isFinite(score)) return "—";
  return Number.isInteger(score) ? String(score) : score.toFixed(1);
}

export function QualitySummaryStrip({ summary }: { summary?: CanvasQualitySummary | null }) {
  const { t } = useI18n();
  if (!summary) return null;
  const tone = scoreTone(summary.score, summary.blocks, summary.warnings);
  return (
    <div className="quality-strip" title={summary.source || ""}>
      <span className={"quality-score " + tone}>{t("review.scoreShort", { score: fmtScore(summary.score) })}</span>
      <span className={summary.blocks ? "block" : ""}>{t("review.blocks", { count: summary.blocks })}</span>
      <span className={summary.warnings ? "warn" : ""}>{t("review.warnings", { count: summary.warnings })}</span>
      <span>{t("review.infos", { count: summary.infos })}</span>
      {summary.metrics.slice(0, 3).map((metric) => (
        <span key={`${metric.label}-${metric.value}`}>{metric.label}: {metric.value}</span>
      ))}
    </div>
  );
}

export function ReviewPane({ summary }: { summary?: CanvasQualitySummary | null }) {
  const { t } = useI18n();
  const topDimensions = useMemo(
    () => (summary?.dimensions ?? []).slice(0, 18),
    [summary?.dimensions],
  );

  if (!summary) {
    return <div className="stub-view">{t("review.noData")}</div>;
  }

  const tone = scoreTone(summary.score, summary.blocks, summary.warnings);
  return (
    <div className="review-pane">
      <div className="review-hero">
        <div className={"review-total " + tone}>
          <span>{t("review.totalScore")}</span>
          <b>{fmtScore(summary.score)}</b>
        </div>
        <div className="review-hero-grid">
          <div><span>{t("review.status")}</span><b>{summary.status || summary.verdict || "—"}</b></div>
          <div><span>{t("review.blocksLabel")}</span><b className={summary.blocks ? "block" : ""}>{summary.blocks}</b></div>
          <div><span>{t("review.warningsLabel")}</span><b className={summary.warnings ? "warn" : ""}>{summary.warnings}</b></div>
          <div><span>{t("review.infosLabel")}</span><b>{summary.infos}</b></div>
        </div>
      </div>

      {summary.metrics.length > 0 && (
        <section className="review-section">
          <h3>{t("review.metrics")}</h3>
          <div className="review-metrics">
            {summary.metrics.map((metric) => (
              <div key={`${metric.label}-${metric.value}`}>
                <span>{metric.label}</span>
                <b>{metric.value}</b>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="review-section">
        <h3>{t("review.dimensions")}</h3>
        <div className="review-dim-list">
          {topDimensions.map((dim) => {
            const dimTone = scoreTone(dim.score, dim.blocks, dim.warnings);
            return (
              <article key={dim.key || dim.label} className={"review-dim " + dimTone}>
                <div className="review-dim-head">
                  <strong>{dim.label}</strong>
                  <span>{fmtScore(dim.score)}</span>
                </div>
                <div className="review-dim-meta">
                  <span>{dim.status || "—"}</span>
                  <span>{t("review.blocks", { count: dim.blocks })}</span>
                  <span>{t("review.warnings", { count: dim.warnings })}</span>
                  {dim.return_to_stage && <span>{t("review.returnTo", { stage: dim.return_to_stage })}</span>}
                </div>
                {dim.evidence.length > 0 && (
                  <div className="review-evidence">
                    {dim.evidence.map((line, idx) => <p key={idx}>{line}</p>)}
                  </div>
                )}
                {dim.rerun_scope && <p className="review-rerun">{dim.rerun_scope}</p>}
              </article>
            );
          })}
        </div>
      </section>

      {summary.tasks.length > 0 && (
        <section className="review-section">
          <h3>{t("review.returnTasks")}</h3>
          <div className="review-task-list">
            {summary.tasks.map((task, idx) => (
              <article key={`${task.return_to_stage || "task"}-${idx}`} className="review-task">
                <div>
                  <strong>{task.return_to_stage || t("review.unknownStage")}</strong>
                  {task.dimensions.length > 0 && <span>{task.dimensions.join(" / ")}</span>}
                </div>
                {task.affected_shots.length > 0 && <p>{t("review.affectedShots", { shots: task.affected_shots.join(", ") })}</p>}
                {task.scope && <p>{task.scope}</p>}
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
