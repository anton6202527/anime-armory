import { useMemo, useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { getMediaPort, mediaUrl, subscribeMediaPort } from "../api";
import { useI18n } from "../i18n";
import type { CanvasClip, CanvasFrame } from "../types";
import { QualitySummaryStrip } from "./QualitySummary";
import type { ViewProps } from "../views/registry";

// Kanban board for canvas lines: the same per-episode clips/panels as the
// infinite canvas, laid out by production artifacts. Columns are intentionally
// non-exclusive: a clip with video should still appear in "已出图".
type KanbanColumnKey = "todo" | "image" | "video" | "review";
type KanbanColumn = {
  key: KanbanColumnKey;
  labelKey: "kanban.todo" | "kanban.image" | "kanban.video" | "kanban.review";
  of: (c: CanvasClip) => boolean;
};
const VIDEO_COLUMNS: KanbanColumn[] = [
  { key: "todo", labelKey: "kanban.todo", of: (c) => !hasImage(c) },
  { key: "image", labelKey: "kanban.image", of: hasImage },
  { key: "video", labelKey: "kanban.video", of: (c) => c.video_exists },
];
const COMIC_COLUMNS: KanbanColumn[] = [
  { key: "todo", labelKey: "kanban.todo", of: (c) => !hasImage(c) },
  { key: "image", labelKey: "kanban.image", of: hasImage },
  { key: "review", labelKey: "kanban.review", of: (c) => c.qa_blocks > 0 || c.qa_warnings > 0 || c.qa.length > 0 },
];

function hasImage(clip: CanvasClip): boolean {
  return Boolean(
    (clip.frames || []).some((frame) => frame.exists && frame.abs)
      || (clip.first_frame_exists && clip.first_frame_abs),
  );
}

function imageFrames(clip: CanvasClip): CanvasFrame[] {
  const frames = (clip.frames || []).filter((frame) => frame.exists && frame.abs);
  if (frames.length) return frames;
  if (clip.first_frame_exists && clip.first_frame_abs) {
    return [{
      role: "first",
      label: "首帧",
      abs: clip.first_frame_abs,
      exists: true,
      prompt: clip.prompt,
    }];
  }
  return [];
}

function frameTooltip(clip: CanvasClip, frame?: CanvasFrame): string {
  return [
    frame?.label || clip.label,
    frame?.role ? `role: ${frame.role}` : "",
    frame?.at_sec != null ? `at: ${frame.at_sec}s` : "",
    frame?.abs || "",
    frame?.prompt || clip.prompt || "",
  ].filter(Boolean).join("\n");
}

function clipTooltip(clip: CanvasClip): string {
  return [
    clip.number != null ? `${clip.number}. ${clip.label}` : clip.label,
    clip.scene || "",
    clip.template ? `template: ${clip.template}` : "",
    clip.prompt || "",
  ].filter(Boolean).join("\n");
}

function clipScoreTone(clip: CanvasClip): string {
  if (clip.qa_blocks > 0) return "block";
  if (clip.score == null) return clip.qa_warnings > 0 ? "warn" : "info";
  if (clip.score < 60) return "block";
  if (clip.score < 80 || clip.qa_warnings > 0) return "warn";
  return "pass";
}

function fmtScore(score?: number): string {
  if (score == null) return "—";
  return Number.isInteger(score) ? String(score) : score.toFixed(1);
}

function Card({ clip, kind, refreshKey }: { clip: CanvasClip; kind: KanbanColumnKey; refreshKey: number }) {
  const { t } = useI18n();
  useSyncExternalStore(subscribeMediaPort, getMediaPort);
  const [previewFrame, setPreviewFrame] = useState<CanvasFrame | null>(null);
  const [previewVideo, setPreviewVideo] = useState(false);
  const withRevision = (url: string) => (url ? `${url}&v=${refreshKey}` : "");
  const frames = imageFrames(clip);
  const poster = frames[0]?.abs ? withRevision(mediaUrl(frames[0].abs)) : "";
  const previewUrl = previewFrame?.abs ? withRevision(mediaUrl(previewFrame.abs)) : "";
  const videoUrl = clip.video_exists && clip.video_abs ? withRevision(mediaUrl(clip.video_abs)) : "";
  return (
    <>
    <div className="kanban-card" title={clipTooltip(clip)}>
      {(kind === "image" || kind === "review") && frames.length > 0 && (
        <div className="kanban-frame-grid" aria-label={`${clip.label} frames`}>
          {frames.slice(0, 4).map((frame, idx) => {
            const url = frame.abs ? withRevision(mediaUrl(frame.abs)) : "";
            return (
              <button
                key={`${frame.role}-${frame.abs || idx}`}
                type="button"
                className="kanban-frame"
                title={frameTooltip(clip, frame)}
                onClick={() => setPreviewFrame(frame)}
              >
                <span>{frame.label || frame.role || `帧${idx + 1}`}</span>
                {url && <img src={url} alt={`${clip.label} ${frame.label || idx + 1}`} loading="lazy" />}
              </button>
            );
          })}
        </div>
      )}
      {kind === "video" && clip.video_abs && (
        <button
          type="button"
          className={"kanban-video-thumb" + (videoUrl ? "" : " missing")}
          title={`${videoUrl ? t("canvas.playVideo") : t("canvas.noVideo")}\n${clip.video_abs}\n${clip.prompt || ""}`}
          onClick={() => videoUrl && setPreviewVideo(true)}
        >
          {poster && <img src={poster} alt="" loading="lazy" />}
          <span className="clip-video-play">▶</span>
          <span className="clip-video-label">{videoUrl ? t("canvas.video") : t("canvas.noVideo")}</span>
        </button>
      )}
      <div className="kanban-card-body">
        <div className="label">
          {clip.number != null ? `${clip.number}. ` : ""}
          {clip.label}
        </div>
        <div className="row">
          {clip.duration != null && <span className="chip">{clip.duration}s</span>}
          {clip.rhythm && <span className="chip rhythm">{clip.rhythm}</span>}
          {clip.scene && <span className="chip">{clip.scene}</span>}
        </div>
        {(clip.score != null || clip.qa_blocks > 0 || clip.qa_warnings > 0) && (
          <div className="quality-mini">
            {clip.score != null && <span className={"score-chip " + clipScoreTone(clip)}>{t("review.scoreShort", { score: fmtScore(clip.score) })}</span>}
            {clip.qa_blocks > 0 && <span className="block">{t("review.blocks", { count: clip.qa_blocks })}</span>}
            {clip.qa_warnings > 0 && <span className="warn">{t("review.warnings", { count: clip.qa_warnings })}</span>}
          </div>
        )}
        {clip.qa.length > 0 && (
          <div className="qa">
            {clip.qa.slice(0, 4).map((f, i) => (
              <span key={i} className={"badge " + (f.severity || "info")} title={f.message || ""}>
                {f.dimension || f.severity}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
    {previewFrame && previewUrl && createPortal(
      <div
        className="media-preview-backdrop"
        role="dialog"
        aria-modal="true"
        onClick={() => setPreviewFrame(null)}
      >
        <div className="media-preview" onClick={(event) => event.stopPropagation()}>
          <button type="button" className="media-preview-close" aria-label={t("common.close")} onClick={() => setPreviewFrame(null)}>×</button>
          <img src={previewUrl} alt={`${clip.label} ${previewFrame.label}`} />
          <div className="media-preview-meta">
            <strong>{clip.number != null ? `${clip.number}. ` : ""}{clip.label} · {previewFrame.label}</strong>
            <span>{previewFrame.abs}</span>
            {(previewFrame.prompt || clip.prompt) && <pre>{previewFrame.prompt || clip.prompt}</pre>}
          </div>
        </div>
      </div>,
      document.body,
    )}
    {previewVideo && videoUrl && createPortal(
      <div
        className="media-preview-backdrop"
        role="dialog"
        aria-modal="true"
        onClick={() => setPreviewVideo(false)}
      >
        <div className="media-preview video" onClick={(event) => event.stopPropagation()}>
          <button type="button" className="media-preview-close" aria-label={t("common.close")} onClick={() => setPreviewVideo(false)}>×</button>
          <video src={videoUrl} poster={poster || undefined} controls autoPlay playsInline preload="metadata" />
          <div className="media-preview-meta">
            <strong>{clip.number != null ? `${clip.number}. ` : ""}{clip.label} · {t("canvas.video")}</strong>
            <span>{clip.video_abs}</span>
            {clip.prompt && <pre>{clip.prompt}</pre>}
          </div>
        </div>
      </div>,
      document.body,
    )}
    </>
  );
}

export function KanbanPane({ canvas, refreshKey = 0 }: ViewProps) {
  const { t } = useI18n();
  const groups = useMemo(() => {
    const clips = canvas?.clips ?? [];
    const columns = canvas?.source === "panel_script" ? COMIC_COLUMNS : VIDEO_COLUMNS;
    return columns.map((col) => ({ ...col, clips: clips.filter(col.of) }));
  }, [canvas]);

  if (!canvas || canvas.clips.length === 0) {
    return <div className="stub-view">{t("canvas.noStoryboard")}</div>;
  }

  return (
    <div className="kanban-wrap">
      <QualitySummaryStrip summary={canvas.quality} />
      <div className="kanban-board">
        {groups.map((g) => (
          <div className="kanban-col" key={g.key}>
            <div className="kanban-col-head">
              {t(g.labelKey)} <span className="count">{g.clips.length}</span>
            </div>
            <div className="kanban-col-body">
              {g.clips.length === 0 ? (
                <div className="kanban-empty">—</div>
              ) : (
                g.clips.map((c) => <Card key={c.id} clip={c} kind={g.key} refreshKey={refreshKey} />)
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
