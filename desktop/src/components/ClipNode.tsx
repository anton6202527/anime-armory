import { useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { getMediaPort, mediaUrl, subscribeMediaPort } from "../api";
import { useI18n } from "../i18n";
import type { CanvasClip, CanvasFrame } from "../types";

type EditableCanvasClip = CanvasClip & { onEdit?: () => void };

function frameTooltip(clip: CanvasClip, frame?: CanvasFrame): string {
  const parts = [
    frame?.label || clip.label,
    frame?.role ? `role: ${frame.role}` : "",
    frame?.at_sec != null ? `at: ${frame.at_sec}s` : "",
    frame?.abs || "",
    frame?.prompt || clip.prompt || "",
  ].filter(Boolean);
  return parts.join("\n");
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

// Custom React Flow node = one storyboard Clip card with a frame thumbnail,
// rhythm chip, duration, and QA badges.
export function ClipNode({ data, selected }: NodeProps) {
  const { t } = useI18n();
  const clip = data as unknown as EditableCanvasClip;
  const [previewFrame, setPreviewFrame] = useState<CanvasFrame | null>(null);
  const [previewVideo, setPreviewVideo] = useState(false);
  // re-render once the media server port is ready (else thumbs stay "未出图")
  useSyncExternalStore(subscribeMediaPort, getMediaPort);
  const rev = clip.mediaRevision ?? 0;
  const withRevision = (url: string) => (url ? `${url}&v=${rev}` : "");
  const frames = (clip.frames || []).filter((frame) => frame.abs || frame.exists);
  const shownFrames = frames.length
    ? frames
    : clip.first_frame_abs
      ? [{
          role: "first",
          label: "首帧",
          abs: clip.first_frame_abs,
          exists: clip.first_frame_exists,
          prompt: clip.prompt,
        }]
      : [];
  const posterFrame = shownFrames.find((frame) => frame.exists && frame.abs);
  const posterUrl = posterFrame?.abs ? withRevision(mediaUrl(posterFrame.abs)) : "";
  const previewUrl = previewFrame?.exists && previewFrame.abs ? withRevision(mediaUrl(previewFrame.abs)) : "";
  const videoUrl = clip.video_exists && clip.video_abs ? withRevision(mediaUrl(clip.video_abs)) : "";
  const clipTooltip = [
    clip.label,
    clip.scene || "",
    clip.template ? `template: ${clip.template}` : "",
    clip.prompt || "",
  ].filter(Boolean).join("\n");
  return (
    <>
    <div className={"clip-node" + (selected ? " selected" : "")} title={clipTooltip}>
      <Handle type="target" position={Position.Left} />
      <div className="frame-strip" aria-label={`${clip.label} frames`}>
        {shownFrames.length ? shownFrames.map((frame, idx) => {
          const url = frame.exists && frame.abs ? withRevision(mediaUrl(frame.abs)) : "";
          const tooltip = frameTooltip(clip, frame);
          return (
            <button
              key={`${frame.role}-${frame.abs || idx}`}
              type="button"
              className={"frame-thumb" + (url ? "" : " missing")}
              title={tooltip}
              onPointerDown={(event) => event.stopPropagation()}
              onClick={(event) => {
                event.stopPropagation();
                if (url) setPreviewFrame(frame);
              }}
            >
              <span className="frame-label">{frame.label || frame.role || `帧${idx + 1}`}</span>
              {url ? <img src={url} alt={`${clip.label} ${frame.label || idx + 1}`} loading="lazy" /> : <span>{t("canvas.noImage")}</span>}
            </button>
          );
        }) : (
          <div className="frame-thumb missing">
            <span>{t("canvas.noImage")}</span>
          </div>
        )}
      </div>
      {clip.video_abs && (
        <button
          type="button"
          className={"clip-video-thumb nodrag" + (videoUrl ? "" : " missing")}
          title={`${videoUrl ? t("canvas.playVideo") : t("canvas.noVideo")}\n${clip.video_abs}`}
          onPointerDown={(event) => event.stopPropagation()}
          onClick={(event) => {
            event.stopPropagation();
            if (videoUrl) setPreviewVideo(true);
          }}
        >
          {posterUrl ? <img src={posterUrl} alt="" loading="lazy" /> : null}
          <span className="clip-video-play">▶</span>
          <span className="clip-video-label">{videoUrl ? t("canvas.video") : t("canvas.noVideo")}</span>
        </button>
      )}
      <div className="body">
        <div className="clip-head">
          <div className="label">
            {clip.number != null ? `${clip.number}. ` : ""}
            {clip.label}
          </div>
          {clip.onEdit && (
            <button
              type="button"
              className="clip-edit-btn nodrag"
              title={t("canvas.editTitle")}
              aria-label={t("canvas.editTitle")}
              onPointerDown={(event) => event.stopPropagation()}
              onClick={(event) => {
                event.stopPropagation();
                clip.onEdit?.();
              }}
            >
              ✎
            </button>
          )}
        </div>
        <div className="row">
          {clip.duration != null && <span className="chip">{clip.duration}s</span>}
          {clip.rhythm && <span className="chip rhythm">{clip.rhythm}</span>}
          {clip.template && <span className="chip">{clip.template}</span>}
        </div>
        {(clip.score != null || clip.qa_blocks > 0 || clip.qa_warnings > 0) && (
          <div className="quality-mini">
            {clip.score != null && <span className={"score-chip " + clipScoreTone(clip)}>{t("review.scoreShort", { score: fmtScore(clip.score) })}</span>}
            {clip.qa_blocks > 0 && <span className="block">{t("review.blocks", { count: clip.qa_blocks })}</span>}
            {clip.qa_warnings > 0 && <span className="warn">{t("review.warnings", { count: clip.qa_warnings })}</span>}
          </div>
        )}
        {clip.scene && <div className="row" style={{ marginTop: 4 }}>{clip.scene}</div>}
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
      <Handle type="source" position={Position.Right} />
    </div>
    {previewFrame && previewUrl && createPortal(
      <div
        className="media-preview-backdrop"
        role="dialog"
        aria-modal="true"
        onPointerDown={(event) => event.stopPropagation()}
        onClick={(event) => {
          event.stopPropagation();
          setPreviewFrame(null);
        }}
      >
        <div className="media-preview" onClick={(event) => event.stopPropagation()}>
          <button type="button" className="media-preview-close" onClick={() => setPreviewFrame(null)}>×</button>
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
        onPointerDown={(event) => event.stopPropagation()}
        onClick={(event) => {
          event.stopPropagation();
          setPreviewVideo(false);
        }}
      >
        <div className="media-preview video" onClick={(event) => event.stopPropagation()}>
          <button type="button" className="media-preview-close" onClick={() => setPreviewVideo(false)}>×</button>
          <video src={videoUrl} poster={posterUrl || undefined} controls autoPlay playsInline preload="metadata" />
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
