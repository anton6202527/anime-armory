export type CanvasAssetEdgeSource = {
  nodeId: string;
  targetNodeIds: string[];
};

export type CanvasClipEdgeSource = {
  videoNodeId: string;
  frameNodeIds: string[];
  videoExists: boolean;
};

export type CanvasGraphEdgePlan = {
  id: string;
  source: string;
  target: string;
  className: string;
  zIndex: number;
};

export type CanvasGraphEdgePlanOptions = {
  assetSources: CanvasAssetEdgeSource[];
  clipSources: CanvasClipEdgeSource[];
  visibleNodeIds: ReadonlySet<string>;
  hasVideoLane: boolean;
};

function uniqueVisibleTargets(ids: readonly string[], visibleNodeIds: ReadonlySet<string>): string[] {
  return Array.from(new Set(ids)).filter((id) => visibleNodeIds.has(id));
}

/**
 * Shared-asset wires are useful only when one visible source actually fans out
 * to at least two visible targets. A one-to-one reference does not communicate
 * shared provenance and creates long visual noise, so it remains represented
 * by node metadata but has no wire. Direct frame → video dependencies remain.
 */
export function buildCanvasGraphEdgePlan(options: CanvasGraphEdgePlanOptions): CanvasGraphEdgePlan[] {
  const assetEdges = options.assetSources.flatMap((asset) => {
    if (!options.visibleNodeIds.has(asset.nodeId)) return [];
    const targets = uniqueVisibleTargets(asset.targetNodeIds, options.visibleNodeIds);
    if (targets.length < 2) return [];
    return targets.map((target) => ({
      id: `${asset.nodeId}->${target}`,
      source: asset.nodeId,
      target,
      className: "asset-edge",
      zIndex: 0,
    }));
  });

  if (!options.hasVideoLane) return assetEdges;
  const videoEdges = options.clipSources.flatMap((clip) => {
    if (!options.visibleNodeIds.has(clip.videoNodeId)) return [];
    return uniqueVisibleTargets(clip.frameNodeIds, options.visibleNodeIds).map((source) => ({
      id: `${source}->${clip.videoNodeId}`,
      source,
      target: clip.videoNodeId,
      className: clip.videoExists
        ? "video-edge video-edge-done"
        : "video-edge video-edge-pending",
      zIndex: 1,
    }));
  });
  return [...assetEdges, ...videoEdges];
}
