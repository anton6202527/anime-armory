import type { CanvasProductionState, CanvasProductionStatus } from "../types";

export type CanvasProductionBarAction = "run" | "accept" | "complete";

export interface CanvasProductionBlockerSummary {
  pendingNodes: number;
  nodeQaBlocks: number;
  finalMissing: boolean;
  finalInvalid: boolean;
  finalStale: boolean;
  finalQaBlocks: number;
  other: number;
}

export interface CanvasProductionBarModel {
  action: CanvasProductionBarAction;
  status: CanvasProductionStatus;
  revision: number;
  shortHash: string;
  accepted: number;
  total: number;
  blockers: CanvasProductionBlockerSummary;
}

const SHA256_RE = /^[a-f0-9]{64}$/i;

function isKnownBlocker(blocker: string): boolean {
  return blocker.startsWith("node_not_accepted:")
    || blocker.startsWith("node_qa_block:")
    || blocker === "final_artifact_missing"
    || blocker === "final_artifact_path_missing"
    || blocker === "final_artifact_sha256_invalid"
    || blocker === "final_artifact_content_hash_stale"
    || blocker.startsWith("final_artifact_qa_block:");
}

/** Derive the compact bar without side effects so status/action rules stay testable. */
export function deriveCanvasProductionBar(state: CanvasProductionState): CanvasProductionBarModel {
  const nodes = Object.values(state.node_fingerprints);
  const accepted = nodes.filter((node) => node.lifecycle === "accepted").length;
  const nodeQaBlocks = nodes.reduce((sum, node) => sum + Math.max(0, node.qa_blocks), 0);
  const artifact = state.completion.artifact;
  const finalMissing = !artifact?.exists;
  const finalInvalid = Boolean(
    artifact?.exists && (!artifact.path || !SHA256_RE.test(artifact.sha256)),
  );
  const finalStale = Boolean(
    artifact?.exists && artifact.content_hash !== state.content_hash,
  );
  const finalQaBlocks = Math.max(0, artifact?.qa_blocks ?? 0);
  const allNodesAccepted = accepted === nodes.length;
  const artifactReady = Boolean(
    artifact?.exists
      && artifact.path
      && SHA256_RE.test(artifact.sha256)
      && artifact.content_hash === state.content_hash
      && artifact.qa_blocks === 0,
  );
  const canAccept = !state.completion.complete
    && allNodesAccepted
    && nodeQaBlocks === 0
    && artifactReady
    && state.completion.blockers.length === 0;

  return {
    action: state.completion.complete ? "complete" : canAccept ? "accept" : "run",
    status: state.status,
    revision: state.revision,
    shortHash: state.content_hash.slice(0, 12) || "—",
    accepted,
    total: nodes.length,
    blockers: {
      pendingNodes: nodes.length - accepted,
      nodeQaBlocks,
      finalMissing,
      finalInvalid,
      finalStale,
      finalQaBlocks,
      other: state.completion.blockers.filter((blocker) => !isKnownBlocker(blocker)).length,
    },
  };
}
