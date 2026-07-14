import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import {
  getMediaPort,
  mediaUrl,
  openWorkEntry,
  readEpisodeWorkspace,
  subscribeMediaPort,
} from "../api";
import type { CanvasClip, CanvasData, CanvasFrame, EpisodeWorkspace, LineKey, WorkRoot } from "../types";
import { DecodedImage } from "../mediaPreview/DecodedImage";
import { ReviewPane } from "./QualitySummary";
import { QualityInsightsPane } from "./QualityInsightsPane";
import { useI18n } from "../i18n";

type Translator = ReturnType<typeof useI18n>["t"];

function textValue(value: unknown, t: Translator): string {
  if (value == null || value === "") return "—";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  if (typeof value === "boolean") return value ? t("common.yes") : t("common.no");
  return String(value);
}

function percentValue(value: unknown): string {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  return `${(n * 100).toFixed(1)}%`;
}

function statusTone(status?: string): string {
  if (status === "block") return "block";
  if (status === "warn") return "warn";
  if (status === "pass" || status === "done") return "pass";
  return "info";
}

function metric(m: Record<string, unknown> | undefined, key: string): unknown {
  return m ? m[key] : undefined;
}

function stageMetricValue(value: unknown, t: Translator): string {
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(1);
  return textValue(value, t);
}

function firstExistingFrame(clip: CanvasClip, t: Translator): CanvasFrame | undefined {
  const frame = (clip.frames || []).find((item) => item.exists && item.abs);
  if (frame) return frame;
  if (!clip.first_frame_exists || !clip.first_frame_abs) return undefined;
  return { role: "first", label: t("episode.firstFrame"), abs: clip.first_frame_abs, exists: true };
}

function scoreText(value: unknown): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

function issueTitle(issue: { dimension?: string; message?: string }, t: Translator): string {
  return [issue.dimension, issue.message].filter(Boolean).join(" · ") || t("episode.unnamedIssue");
}

export function EpisodeWorkspacePane({
  root,
  line,
  ep,
  canvas,
  refreshKey,
}: {
  root: WorkRoot;
  line: LineKey;
  ep: string;
  canvas: CanvasData | null;
  refreshKey: number;
}) {
  useSyncExternalStore(subscribeMediaPort, getMediaPort);
  const { t } = useI18n();
  const [workspace, setWorkspace] = useState<EpisodeWorkspace | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    readEpisodeWorkspace(root.path, ep)
      .then((data) => {
        if (alive) setWorkspace(data);
      })
      .catch(() => {
        if (alive) setWorkspace(null);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [ep, refreshKey, root.path]);

  const clips = useMemo(() => canvas?.clips ?? [], [canvas?.clips]);

  if (loading && !workspace) return <div className="stub-view">{t("episode.loadingWorkspace")}</div>;
  if (!workspace) {
    return canvas?.quality ? (
      <div className="review-stack">
        <ReviewPane summary={canvas.quality} embedded />
        <QualityInsightsPane root={root} line={line} ep={ep} refreshKey={refreshKey} embedded />
      </div>
    ) : (
      <QualityInsightsPane root={root} line={line} ep={ep} refreshKey={refreshKey} />
    );
  }

  const m = workspace.metrics ?? {};
  const progress = workspace.progress ?? {};
  const stages = progress.stages ?? {};
  const stageMetrics = workspace.stage_metrics ?? {};
  const groups = workspace.issues?.groups ?? [];
  const evidence = workspace.evidence ?? [];
  const tasks = workspace.return_tasks ?? [];
  const status = statusTone(workspace.status);

  return (
    <div className="episode-workspace">
      <section className="episode-hero">
        <div className={"episode-status " + status}>
          <span>{t("episode.status")}</span>
          <b>{workspace.status || "—"}</b>
        </div>
        <div className="episode-metric-grid">
          <div><span>{t("episode.stagesDone")}</span><b>{progress.done_stages ?? 0}/{progress.total_stages ?? 0}</b></div>
          <div><span>{t("next.next")}</span><b>{workspace.next_action?.label || workspace.next_action?.skill || "—"}</b></div>
          <div><span>{t("episode.machineScore")}</span><b>{scoreText(metric(m, "score"))}</b></div>
          <div><span>{t("episode.cost")}</span><b>{textValue(metric(m, "cost_text"), t)}</b></div>
          <div><span>{t("episode.runtime")}</span><b>{textValue(metric(m, "runtime_hms"), t)}</b></div>
          <div><span>{t("episode.productionTime")}</span><b>{textValue(metric(m, "duration_hms"), t)}</b></div>
          <div><span>{t("episode.finalPassRate")}</span><b>{textValue(metric(m, "final_pass_rate_text"), t) || percentValue(metric(m, "final_pass_rate"))}</b></div>
          <div><span>{t("episode.redrawRate")}</span><b>{textValue(metric(m, "redraw_rate_text"), t) || percentValue(metric(m, "redraw_rate"))}</b></div>
          <div><span>QA</span><b>{textValue(metric(m, "qa_blockers"), t)}/{textValue(metric(m, "qa_warnings"), t)}</b></div>
        </div>
      </section>

      <QualityInsightsPane root={root} line={line} ep={ep} refreshKey={refreshKey} embedded />

      <section className="episode-section">
        <h3>{t("episode.stages")}</h3>
        <div className="episode-stage-list">
          {Object.keys(stages).length === 0 ? (
            <div className="episode-empty">{t("episode.noStageData")}</div>
          ) : (
            Object.entries(stages).map(([name, state]) => {
              const sm = stageMetrics[name] || {};
              return (
                <div className="episode-stage" key={name}>
                  <strong>{name}</strong>
                  <span className={"episode-pill " + statusTone(state)}>{state}</span>
                  <span>{t("episode.attempts", { count: stageMetricValue(sm.generation_attempts, t) })}</span>
                  <span>{t("episode.passes", { count: stageMetricValue(sm.generation_passes, t) })}</span>
                  <span>{t("episode.redraws", { count: stageMetricValue(sm.redraw_count, t) })}</span>
                  <span>QA {stageMetricValue(sm.qa_blockers, t)}/{stageMetricValue(sm.qa_warnings, t)}</span>
                </div>
              );
            })
          )}
        </div>
      </section>

      <section className="episode-section">
        <h3>{t("episode.issueReflow")}</h3>
        {groups.length === 0 ? (
          <div className="episode-empty">{t("episode.noBlockingIssues")}</div>
        ) : (
          <div className="episode-issue-groups">
            {groups.slice(0, 12).map((group) => (
              <article className="episode-issue-group" key={group.return_to_stage || "review"}>
                <div className="episode-issue-head">
                  <strong>{t("review.returnTo", { stage: group.return_to_stage || "review" })}</strong>
                  <span>{group.counts?.block ?? 0} block / {group.counts?.warn ?? 0} warn</span>
                </div>
                {(group.items ?? []).slice(0, 8).map((issue, idx) => (
                  <div className={"episode-issue " + statusTone(issue.severity)} key={`${issue.source || ""}-${idx}`}>
                    <span className={"episode-pill " + statusTone(issue.severity)}>{issue.severity || "info"}</span>
                    <div>
                      <b>{issueTitle(issue, t)}</b>
                      {(issue.loc || issue.source) && <p>{[issue.loc, issue.source].filter(Boolean).join(" · ")}</p>}
                      {issue.affected_shots && issue.affected_shots.length > 0 && <p>{t("episode.affectedShots", { shots: issue.affected_shots.join(", ") })}</p>}
                    </div>
                  </div>
                ))}
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="episode-section">
        <h3>{t("episode.clipOverview")}</h3>
        <div className="episode-clip-grid">
          {clips.map((clip) => {
            const frame = firstExistingFrame(clip, t);
            const baseUrl = frame?.abs ? mediaUrl(frame.abs) : "";
            const url = baseUrl && frame?.revision
              ? `${baseUrl}&v=${encodeURIComponent(frame.revision)}`
              : baseUrl;
            const tone = clip.qa_blocks > 0 ? "block" : clip.qa_warnings > 0 ? "warn" : clip.video_exists ? "pass" : "info";
            return (
              <article className={"episode-clip " + tone} key={clip.id}>
                <div className="episode-clip-thumb">
                  {url ? <DecodedImage src={url} alt={clip.label} maxDecodeDimension={640} /> : <span>{t("episode.noImage")}</span>}
                </div>
                <div className="episode-clip-body">
                  <strong>{clip.number != null ? `${clip.number}. ` : ""}{clip.label || clip.id}</strong>
                  <p>{clip.duration ?? "—"}s · {clip.scene || "—"}</p>
                  <p>QA {clip.qa_blocks}/{clip.qa_warnings} · {clip.video_exists ? t("episode.videoReady") : t("episode.videoMissing")}</p>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="episode-section two-col">
        <div>
          <h3>{t("episode.reworkTasks")}</h3>
          {tasks.length === 0 ? (
            <div className="episode-empty">{t("episode.none")}</div>
          ) : (
            tasks.slice(0, 10).map((task, idx) => (
              <div className="episode-task" key={idx}>
                <strong>{textValue(task.return_to_stage || task.source, t)}</strong>
                <p>{textValue(task.scope, t)}</p>
              </div>
            ))
          )}
        </div>
        <div>
          <h3>{t("episode.evidenceFiles")}</h3>
          {evidence.slice(0, 12).map((item, idx) => (
            <button
              key={`${item.path || item.label}-${idx}`}
              type="button"
              className="episode-evidence"
              disabled={!item.exists || !item.path}
              onClick={() => item.path && openWorkEntry(root.path, item.path)}
              title={item.path || ""}
            >
              <span>{item.label || item.path}</span>
              <b>{item.exists ? t("common.open") : t("common.missing")}</b>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
