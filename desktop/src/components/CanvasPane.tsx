import { useMemo } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { ClipNode } from "./ClipNode";
import { useI18n } from "../i18n";
import type { ViewProps } from "../views/registry";

const nodeTypes = { clip: ClipNode };

// Infinite canvas for n2d/ad/mv: clip nodes laid out left→right with
// 接力链 (continuity) edges between consecutive clips and seam transitions.
export function CanvasPane({ canvas, refreshKey = 0 }: ViewProps) {
  const { t } = useI18n();
  const { nodes, edges } = useMemo(() => {
    if (!canvas) return { nodes: [] as Node[], edges: [] as Edge[] };
    const COL_W = 300;
    const nodes: Node[] = canvas.clips.map((clip, i) => ({
      id: clip.id,
      type: "clip",
      position: { x: i * COL_W, y: (i % 2) * 70 }, // gentle stagger for readability
      data: { ...clip, mediaRevision: refreshKey } as unknown as Record<string, unknown>,
    }));
    const edges: Edge[] = canvas.seams.map((s) => ({
      id: `${s.from}->${s.to}`,
      source: s.from,
      target: s.to,
      label: s.transition,
      animated: s.transition === "hard_cut",
      style: { stroke: "#3a4866" },
      labelStyle: { fill: "#8a95ad", fontSize: 10 },
      labelBgStyle: { fill: "#11151f" },
    }));
    return { nodes, edges };
  }, [canvas, refreshKey]);

  if (!canvas || canvas.clips.length === 0) {
    return <div className="stub-view">{t("canvas.noStoryboard")}</div>;
  }

  return (
    <div className="canvas-wrap">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.1}
        onlyRenderVisibleElements
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={24} color="#1b2230" />
        <MiniMap pannable zoomable maskColor="rgba(11,14,20,.7)" nodeColor="#2a3450" />
        {/* zoom + interactivity only — the fit/reset ("reload") button is hidden */}
        <Controls showFitView={false} />
      </ReactFlow>
    </div>
  );
}
