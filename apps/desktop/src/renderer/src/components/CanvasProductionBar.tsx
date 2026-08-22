import type { CanvasProductionState, CanvasProductionStatus } from "../types";
import { useI18n } from "../i18n";
import { deriveCanvasProductionBar } from "./canvasProductionBarModel";
export { deriveCanvasProductionBar } from "./canvasProductionBarModel";

function statusKey(status: CanvasProductionStatus) {
  return `canvas.production.status.${status}` as const;
}

export function CanvasProductionBar({
  state,
  busy = false,
  onRun,
  onAccept,
}: {
  state: CanvasProductionState;
  busy?: boolean;
  onRun: () => void;
  onAccept: () => void;
}) {
  const { t } = useI18n();
  const model = deriveCanvasProductionBar(state);
  const blockerParts: string[] = [];
  if (model.blockers.pendingNodes > 0) {
    blockerParts.push(t("canvas.production.blockerPending", { count: model.blockers.pendingNodes }));
  }
  if (model.blockers.nodeQaBlocks > 0) {
    blockerParts.push(t("canvas.production.blockerNodeQa", { count: model.blockers.nodeQaBlocks }));
  }
  if (model.blockers.finalMissing) blockerParts.push(t("canvas.production.blockerFinalMissing"));
  if (model.blockers.finalInvalid) blockerParts.push(t("canvas.production.blockerFinalInvalid"));
  if (model.blockers.finalStale) blockerParts.push(t("canvas.production.blockerFinalStale"));
  if (model.blockers.finalQaBlocks > 0) {
    blockerParts.push(t("canvas.production.blockerFinalQa", { count: model.blockers.finalQaBlocks }));
  }
  if (model.blockers.other > 0) {
    blockerParts.push(t("canvas.production.blockerOther", { count: model.blockers.other }));
  }
  const blockerText = model.action === "complete"
    ? t("canvas.production.definitionSatisfied")
    : model.action === "accept"
      ? t("canvas.production.awaitingAcceptance")
      : blockerParts.join(t("common.listDelimiter")) || t("canvas.production.criteriaPending");
  const fullTitle = [
    `${t("canvas.production.hash")}: ${state.content_hash}`,
    `${t("canvas.production.definition")}: ${state.completion.definition}`,
    ...state.completion.blockers,
  ].join("\n");

  return (
    <div
      className={`canvas-production-bar status-${model.status}`}
      aria-busy={busy}
      title={fullTitle}
    >
      <span className="canvas-production-state">
        <i aria-hidden="true" />
        {t(statusKey(model.status))}
      </span>
      <span className="canvas-production-meta">
        <span>{t("canvas.production.revision", { revision: model.revision })}</span>
        <code>{model.shortHash}</code>
        <span>{t("canvas.production.accepted", { accepted: model.accepted, total: model.total })}</span>
      </span>
      <span className="canvas-production-blockers">{blockerText}</span>
      {model.action === "complete" ? (
        <span className="canvas-production-complete">{t("canvas.production.complete")}</span>
      ) : (
        <button
          type="button"
          className="canvas-production-action nodrag nopan"
          disabled={busy || model.status === "running"}
          onClick={model.action === "accept" ? onAccept : onRun}
        >
          {busy || model.status === "running"
            ? t("canvas.production.busy")
            : model.action === "accept"
              ? t("canvas.production.acceptFinal")
              : t("canvas.production.run")}
        </button>
      )}
    </div>
  );
}
