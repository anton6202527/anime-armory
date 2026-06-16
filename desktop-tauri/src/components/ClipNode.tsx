import { Handle, Position, type NodeProps } from "@xyflow/react";
import { mediaUrl } from "../api";
import type { CanvasClip } from "../types";

// Custom React Flow node = one storyboard Clip card with a frame thumbnail,
// rhythm chip, duration, and QA badges.
export function ClipNode({ data, selected }: NodeProps) {
  const clip = data as unknown as CanvasClip;
  const thumb = clip.first_frame_exists && clip.first_frame_abs ? mediaUrl(clip.first_frame_abs) : "";
  return (
    <div className={"clip-node" + (selected ? " selected" : "")}>
      <Handle type="target" position={Position.Left} />
      <div className="thumb">
        {thumb ? <img src={thumb} alt={clip.label} /> : <span>未出图</span>}
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
