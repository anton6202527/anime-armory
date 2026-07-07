import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import {
  getMediaPort,
  mediaUrl,
  openWorkEntry,
  readEpisodeWorkspace,
  subscribeMediaPort,
} from "../api";
import type { CanvasClip, CanvasData, EpisodeWorkspace, LineKey, WorkRoot } from "../types";
import { ReviewPane } from "./QualitySummary";
import { QualityInsightsPane } from "./QualityInsightsPane";

function textValue(value: unknown): string {
  if (value == null || value === "") return "—";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  if (typeof value === "boolean") return value ? "是" : "否";
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

function stageMetricValue(value: unknown): string {
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(1);
  return textValue(value);
}

function firstExistingFrame(clip: CanvasClip): string {
  const frame = (clip.frames || []).find((item) => item.exists && item.abs);
  return frame?.abs || (clip.first_frame_exists ? clip.first_frame_abs || "" : "");
}

function scoreText(value: unknown): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

function issueTitle(issue: { dimension?: string; message?: string }): string {
  return [issue.dimension, issue.message].filter(Boolean).join(" · ") || "未命名问题";
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

  if (loading && !workspace) return <div className="stub-view">读取本集工作台…</div>;
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
          <span>本集状态</span>
          <b>{workspace.status || "—"}</b>
        </div>
        <div className="episode-metric-grid">
          <div><span>阶段完成</span><b>{progress.done_stages ?? 0}/{progress.total_stages ?? 0}</b></div>
          <div><span>下一步</span><b>{workspace.next_action?.label || workspace.next_action?.skill || "—"}</b></div>
          <div><span>机器分</span><b>{scoreText(metric(m, "score"))}</b></div>
          <div><span>成本</span><b>{textValue(metric(m, "cost_text"))}</b></div>
          <div><span>成片时长</span><b>{textValue(metric(m, "runtime_hms"))}</b></div>
          <div><span>生产耗时</span><b>{textValue(metric(m, "duration_hms"))}</b></div>
          <div><span>成片通过率</span><b>{textValue(metric(m, "final_pass_rate_text")) || percentValue(metric(m, "final_pass_rate"))}</b></div>
          <div><span>重抽率</span><b>{textValue(metric(m, "redraw_rate_text")) || percentValue(metric(m, "redraw_rate"))}</b></div>
          <div><span>QA</span><b>{textValue(metric(m, "qa_blockers"))}/{textValue(metric(m, "qa_warnings"))}</b></div>
        </div>
      </section>

      <QualityInsightsPane root={root} line={line} ep={ep} refreshKey={refreshKey} embedded />

      <section className="episode-section">
        <h3>阶段</h3>
        <div className="episode-stage-list">
          {Object.keys(stages).length === 0 ? (
            <div className="episode-empty">暂无阶段数据</div>
          ) : (
            Object.entries(stages).map(([name, state]) => {
              const sm = stageMetrics[name] || {};
              return (
                <div className="episode-stage" key={name}>
                  <strong>{name}</strong>
                  <span className={"episode-pill " + statusTone(state)}>{state}</span>
                  <span>尝试 {stageMetricValue(sm.generation_attempts)}</span>
                  <span>通过 {stageMetricValue(sm.generation_passes)}</span>
                  <span>重抽 {stageMetricValue(sm.redraw_count)}</span>
                  <span>QA {stageMetricValue(sm.qa_blockers)}/{stageMetricValue(sm.qa_warnings)}</span>
                </div>
              );
            })
          )}
        </div>
      </section>

      <section className="episode-section">
        <h3>问题回流</h3>
        {groups.length === 0 ? (
          <div className="episode-empty">暂无阻断问题</div>
        ) : (
          <div className="episode-issue-groups">
            {groups.slice(0, 12).map((group) => (
              <article className="episode-issue-group" key={group.return_to_stage || "review"}>
                <div className="episode-issue-head">
                  <strong>回 {group.return_to_stage || "review"}</strong>
                  <span>{group.counts?.block ?? 0} block / {group.counts?.warn ?? 0} warn</span>
                </div>
                {(group.items ?? []).slice(0, 8).map((issue, idx) => (
                  <div className={"episode-issue " + statusTone(issue.severity)} key={`${issue.source || ""}-${idx}`}>
                    <span className={"episode-pill " + statusTone(issue.severity)}>{issue.severity || "info"}</span>
                    <div>
                      <b>{issueTitle(issue)}</b>
                      {(issue.loc || issue.source) && <p>{[issue.loc, issue.source].filter(Boolean).join(" · ")}</p>}
                      {issue.affected_shots && issue.affected_shots.length > 0 && <p>镜头：{issue.affected_shots.join(", ")}</p>}
                    </div>
                  </div>
                ))}
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="episode-section">
        <h3>镜头概览</h3>
        <div className="episode-clip-grid">
          {clips.map((clip) => {
            const img = firstExistingFrame(clip);
            const url = img ? `${mediaUrl(img)}&v=${refreshKey}` : "";
            const tone = clip.qa_blocks > 0 ? "block" : clip.qa_warnings > 0 ? "warn" : clip.video_exists ? "pass" : "info";
            return (
              <article className={"episode-clip " + tone} key={clip.id}>
                <div className="episode-clip-thumb">
                  {url ? <img src={url} alt={clip.label} loading="lazy" /> : <span>无图</span>}
                </div>
                <div className="episode-clip-body">
                  <strong>{clip.number != null ? `${clip.number}. ` : ""}{clip.label || clip.id}</strong>
                  <p>{clip.duration ?? "—"}s · {clip.scene || "—"}</p>
                  <p>QA {clip.qa_blocks}/{clip.qa_warnings} · 视频 {clip.video_exists ? "有" : "缺"}</p>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="episode-section two-col">
        <div>
          <h3>返工任务</h3>
          {tasks.length === 0 ? (
            <div className="episode-empty">暂无</div>
          ) : (
            tasks.slice(0, 10).map((task, idx) => (
              <div className="episode-task" key={idx}>
                <strong>{textValue(task.return_to_stage || task.source)}</strong>
                <p>{textValue(task.scope)}</p>
              </div>
            ))
          )}
        </div>
        <div>
          <h3>证据文件</h3>
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
              <b>{item.exists ? "打开" : "缺失"}</b>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
