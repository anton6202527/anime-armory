import { useEffect, useState } from "react";
import { readNextAction } from "../api";
import { useI18n } from "../i18n";
import type { NextAction } from "../types";

function PlaceholderNext({
  headline,
  message,
  button,
}: {
  headline: string;
  message: string;
  button: string;
}) {
  return (
    <div className="next-strip next-strip-disabled">
      <span className="headline">{headline}</span>
      <div className="next-placeholder" aria-disabled="true">
        {message}
      </div>
      <button type="button" className="next-execute" disabled>
        {button}
      </button>
    </div>
  );
}

// Read-only "what to do next" strip, driven by `run.py next --json`.
// Shows the headline + the exact command the user can copy into the terminal.
export function NextActionStrip(props: {
  repoRoot: string;
  root: string;
  ep: string;
  refreshKey?: number;
  enabled?: boolean;
  manualPrompt?: {
    headline: string;
    prompt: string;
  } | null;
  onExecutePrompt?: (prompt: string) => void;
}) {
  const { repoRoot, root, ep, refreshKey, enabled = true, manualPrompt, onExecutePrompt } = props;
  const { t } = useI18n();
  const [na, setNa] = useState<NextAction | null>(null);

  useEffect(() => {
    if (!enabled) {
      setNa(null);
      return;
    }
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
  }, [repoRoot, root, ep, refreshKey, enabled, manualPrompt]);

  if (manualPrompt) {
    return <PlaceholderNext headline={t("next.next")} message={manualPrompt.prompt} button={t("next.execute")} />;
  }

  if (!enabled) {
    return <PlaceholderNext headline={t("next.next")} message={t("next.deferred")} button={t("next.execute")} />;
  }
  if (!na) return <PlaceholderNext headline={t("next.next")} message={t("next.loading")} button={t("next.execute")} />;
  if (na.error) {
    return (
      <PlaceholderNext
        headline={t("next.next")}
        message={t("next.unavailable", { error: na.error.slice(0, 80) })}
        button={t("next.execute")}
      />
    );
  }

  const head = na.action_card?.headline || na.frontier?.label || na.stop_reason || "—";
  const cmd = na.action_card?.exact_command;
  if (!cmd) {
    const message = na.action_card?.to_user || (head === "—" ? t("next.noExecutable") : head);
    return <PlaceholderNext headline={t("next.next")} message={message} button={t("next.execute")} />;
  }

  return (
    <div className="next-strip next-strip-executable">
      <span className="headline">{t("next.next")}</span>
      <span className="next-title">{head}</span>
      <code title={t("next.copyCommandTitle")}>{cmd}</code>
      {na.stop_reason && <span className="reason">· {na.stop_reason}</span>}
      <button
        type="button"
        className="next-execute"
        disabled={!onExecutePrompt}
        onClick={() => onExecutePrompt?.(cmd)}
      >
        {t("next.execute")}
      </button>
    </div>
  );
}
