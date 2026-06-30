import { useMemo, useSyncExternalStore } from "react";
import { getMediaPort, mediaUrl, subscribeMediaPort } from "../api";
import { useI18n } from "../i18n";
import type { CanvasClip } from "../types";
import type { ViewProps } from "../views/registry";

// Kanban board for canvas lines (n2d/ad/mv): the same per-episode clips as the
// infinite canvas, but laid out as status columns by production stage derived
// from each clip's on-disk state (first frame / video). A produce-progress view.
const COLUMNS: { key: string; labelKey: "kanban.todo" | "kanban.image" | "kanban.video"; of: (c: CanvasClip) => boolean }[] = [
  { key: "todo", labelKey: "kanban.todo", of: (c) => !c.first_frame_exists },
  { key: "image", labelKey: "kanban.image", of: (c) => c.first_frame_exists && !c.video_exists },
  { key: "video", labelKey: "kanban.video", of: (c) => c.video_exists },
];

function Card({ clip, refreshKey }: { clip: CanvasClip; refreshKey: number }) {
  useSyncExternalStore(subscribeMediaPort, getMediaPort);
  const withRevision = (url: string) => (url ? `${url}&v=${refreshKey}` : "");
  const thumb =
    clip.first_frame_exists && clip.first_frame_abs
      ? withRevision(mediaUrl(clip.first_frame_abs))
      : "";
  return (
    <div className="kanban-card">
      {thumb && <div className="kanban-thumb"><img src={thumb} alt={clip.label} /></div>}
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
  );
}

export function KanbanPane({ canvas, refreshKey = 0 }: ViewProps) {
  const { t } = useI18n();
  const groups = useMemo(() => {
    const clips = canvas?.clips ?? [];
    return COLUMNS.map((col) => ({ ...col, clips: clips.filter(col.of) }));
  }, [canvas]);

  if (!canvas || canvas.clips.length === 0) {
    return <div className="stub-view">{t("canvas.noStoryboard")}</div>;
  }

  return (
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
              g.clips.map((c) => <Card key={c.id} clip={c} refreshKey={refreshKey} />)
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
