import { useEffect, useState } from "react";
import { detectAgents, pickDefaultAgent } from "../api";
import { useI18n } from "../i18n";
import type { AgentInfo } from "../types";

/** Auto-detects local AI agent CLIs and lets the user jump into one in the
 *  terminal. Image-capable (生图) agents get a 🎨 badge. */
export function AgentBar({
  activeAgentId,
  nativeActive,
  onNativeTerminal,
  onEnter,
}: {
  activeAgentId?: string | null;
  nativeActive?: boolean;
  onNativeTerminal: () => void;
  onEnter: (agent: AgentInfo) => void;
}) {
  const { t } = useI18n();
  const [agents, setAgents] = useState<AgentInfo[] | null>(null);

  function probe(force = false) {
    setAgents(null);
    detectAgents(force)
      .then(setAgents)
      .catch(() => setAgents([]));
  }
  useEffect(() => probe(false), []);

  const found = (agents ?? []).filter((a) => a.found);
  const defaultId = agents ? pickDefaultAgent(agents)?.id : undefined;

  return (
    <div className="agent-bar">
      <button
        type="button"
        className={"ab-chip native" + (nativeActive ? " active" : "")}
        title={t("agent.nativeTitle")}
        onClick={onNativeTerminal}
      >
        <span className="ab-name">{t("agent.nativeTerminal")}</span>
        <span className="ab-enter">{t("agent.enter")}</span>
      </button>

      {agents === null && <span className="ab-hint">{t("agent.detecting")}</span>}
      {agents !== null && found.length === 0 && (
        <span className="ab-hint">{t("agent.notDetected")}</span>
      )}

      {(agents ?? [])
        .filter((a) => a.found || (a.id === "opencode" && a.install_command))
        .map((a) => {
          const img = a.image === "yes" ? "🎨" : a.image === "maybe" ? "🎨?" : "";
          const install = !a.found && !!a.install_command;
          return (
            <button
              key={a.id}
              className={
                "ab-chip" +
                (a.image === "yes" ? " img" : "") +
                (activeAgentId === a.id ? " active" : "") +
                (install ? " install" : "")
              }
              title={`${install ? a.install_command : a.command}  ·  ${a.path || t("agent.notInstalled")}\n${a.note}`}
              onClick={() => onEnter(a)}
            >
              <span className="ab-name">{a.name}</span>
              {a.id === defaultId && a.found && (
                <span className="ab-default" title={t("agent.defaultTitle")}>{t("agent.default")}</span>
              )}
              {install && <span className="ab-install" title={t("agent.installTitle")}>{t("agent.install")}</span>}
              {img && (
                <span className={"ab-img" + (a.image === "maybe" ? " dim" : "")} title={a.note}>
                  {img} {t("agent.image")}
                </span>
              )}
              <span className="ab-enter">{install ? t("agent.installEnter") : t("agent.enter")}</span>
            </button>
          );
        })}

      <button className="ab-refresh" title={t("agent.refresh")} onClick={() => probe(true)}>
        ↻
      </button>
    </div>
  );
}
