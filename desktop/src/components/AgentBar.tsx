import { pickDefaultAgent } from "../api";
import { useI18n } from "../i18n";
import type { AgentInfo } from "../types";

/** Auto-detects local AI agent CLIs and lets the user jump into one in the
 *  terminal. Image-capable (生图) agents get a 🎨 badge. */
export function AgentBar({
  activeAgentId,
  nativeActive,
  agents,
  probeEnabled = true,
  onNativeTerminal,
  onEnter,
  onRefresh,
}: {
  activeAgentId?: string | null;
  nativeActive?: boolean;
  agents: AgentInfo[] | null;
  probeEnabled?: boolean;
  onNativeTerminal: () => void;
  onEnter: (agent: AgentInfo) => void;
  onRefresh: (force?: boolean) => void;
}) {
  const { t } = useI18n();
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

      {!probeEnabled && <span className="ab-hint">{t("agent.deferred")}</span>}
      {probeEnabled && agents === null && <span className="ab-hint">{t("agent.detecting")}</span>}
      {probeEnabled && agents !== null && found.length === 0 && (
        <span className="ab-hint">{t("agent.notDetected")}</span>
      )}

      {(agents ?? [])
        .filter((a) => a.found)
        .map((a) => {
          const img = a.image === "yes" ? "🎨" : a.image === "maybe" ? "🎨?" : "";
          return (
            <button
              key={a.id}
              className={
                "ab-chip" +
                (a.image === "yes" ? " img" : "") +
                (activeAgentId === a.id ? " active" : "")
              }
              title={`${a.command}  ·  ${a.path || t("agent.notInstalled")}\n${a.note}`}
              onClick={() => onEnter(a)}
            >
              <span className="ab-name">{a.name}</span>
              {a.id === defaultId && a.found && (
                <span className="ab-default" title={t("agent.defaultTitle")}>{t("agent.default")}</span>
              )}
              {img && (
                <span className={"ab-img" + (a.image === "maybe" ? " dim" : "")} title={a.note}>
                  {img} {t("agent.image")}
                </span>
              )}
              <span className="ab-enter">{t("agent.enter")}</span>
            </button>
          );
        })}

      <button
        className="ab-refresh"
        title={t("agent.refresh")}
        disabled={!probeEnabled}
        onClick={() => onRefresh(true)}
      >
        ↻
      </button>
    </div>
  );
}
