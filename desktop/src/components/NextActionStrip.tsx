import { useEffect, useState } from "react";
import { readNextAction } from "../api";
import { useI18n } from "../i18n";
import type { NextAction } from "../types";

// Read-only "what to do next" strip, driven by `run.py next --json`.
// Shows the headline + the exact command the user can copy into the terminal.
export function NextActionStrip(props: {
  repoRoot: string;
  root: string;
  ep: string;
  refreshKey?: number;
  manualPrompt?: {
    headline: string;
    prompt: string;
  } | null;
  onExecutePrompt?: (prompt: string) => void;
}) {
  const { repoRoot, root, ep, refreshKey, manualPrompt, onExecutePrompt } = props;
  const { t } = useI18n();
  const [na, setNa] = useState<NextAction | null>(null);

  useEffect(() => {
    if (manualPrompt) {
      setNa(null);
      return;
    }
    let alive = true;
    readNextAction(repoRoot, root, ep)
      .then((d) => alive && setNa(d))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [repoRoot, root, ep, refreshKey, manualPrompt]);

  if (manualPrompt) {
    return (
      <div className="next-strip next-strip-manual">
        <span className="headline">{t("next.next")}</span>
        <span>{manualPrompt.headline}</span>
        <code title={manualPrompt.prompt}>{manualPrompt.prompt}</code>
        <button
          type="button"
          className="next-execute"
          onClick={() => onExecutePrompt?.(manualPrompt.prompt)}
        >
          {t("next.execute")}
        </button>
      </div>
    );
  }

  if (!na) return <div className="next-strip reason">{t("next.loading")}</div>;
  if (na.error) return <div className="next-strip reason">{t("next.unavailable", { error: na.error.slice(0, 80) })}</div>;

  const head = na.action_card?.headline || na.frontier?.label || na.stop_reason || "—";
  const cmd = na.action_card?.exact_command;
  return (
    <div className="next-strip">
      <span className="headline">{t("next.next")}</span>
      <span>{head}</span>
      {cmd && <code title={t("next.copyCommandTitle")}>{cmd}</code>}
      {na.stop_reason && <span className="reason">· {na.stop_reason}</span>}
    </div>
  );
}
