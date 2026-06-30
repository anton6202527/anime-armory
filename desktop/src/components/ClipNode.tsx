import { useSyncExternalStore } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { getMediaPort, mediaUrl, subscribeMediaPort } from "../api";
import { useI18n } from "../i18n";
import type { CanvasClip } from "../types";

// Custom React Flow node = one storyboard Clip card with a frame thumbnail,
// rhythm chip, duration, and QA badges.
export function ClipNode({ data, selected }: NodeProps) {
  const { t } = useI18n();
  const clip = data as unknown as CanvasClip;
  // re-render once the media server port is ready (else thumbs stay "未出图")
  useSyncExternalStore(subscribeMediaPort, getMediaPort);
  const rev = clip.mediaRevision ?? 0;
  const withRevision = (url: string) => (url ? `${url}&v=${rev}` : "");
  const thumb = clip.first_frame_exists && clip.first_frame_abs ? withRevision(mediaUrl(clip.first_frame_abs)) : "";
  const video = clip.video_exists && clip.video_abs ? withRevision(mediaUrl(clip.video_abs)) : "";
  return (
    <div className={"clip-node" + (selected ? " selected" : "")}>
      <Handle type="target" position={Position.Left} />
      <div className="thumb">
        {video ? (
          <video src={video} poster={thumb || undefined} controls preload="none" />
        ) : thumb ? (
          <img src={thumb} alt={clip.label} />
        ) : (
          <span>{t("canvas.noImage")}</span>
        )}
      </div>
      <div className="body">
        <div className="label">
          {clip.number != null ? `${clip.number}. ` : ""}
          {clip.label}
        </div>
        <div className="row">
          {clip.duration != null && <span className="chip">{clip.duration}s</span>}
          {clip.rhythm && <span className="chip rhythm">{clip.rhythm}</span>}
          {clip.template && <span className="chip">{clip.template}</span>}
        </div>
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
  );
}
