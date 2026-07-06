import { pickDefaultAgent } from "../api";
import { useI18n } from "../i18n";
import type { AgentInfo } from "../types";

/** Auto-detects local AI agent CLIs and lets the user jump into one in the
 *  terminal. Missing mainstream agents stay visible but disabled. */
export function AgentBar({
  className = "",
  activeAgentId,
  nativeActive,
  agents,
  probeEnabled = true,
  onNativeTerminal,
  onEnter,
}: {
  className?: string;
  activeAgentId?: string | null;
  nativeActive?: boolean;
  agents: AgentInfo[] | null;
  probeEnabled?: boolean;
  onNativeTerminal: () => void;
  onEnter: (agent: AgentInfo) => void;
}) {
  const { t } = useI18n();
  const defaultAgent = agents ? pickDefaultAgent(agents) : null;
  const selectedId = nativeActive ? "native" : activeAgentId || defaultAgent?.id || "native";
  const selectedAgent = (agents ?? []).find((agent) => agent.id === selectedId);

  return (
    <div className={["agent-bar", className].filter(Boolean).join(" ")}>
      <label className="ab-select-wrap" title={selectedAgent?.note || t("agent.nativeTitle")}>
        <span className="ab-title">{t("agent.selector")}</span>
        <select
          className="ab-select"
          value={selectedId}
          disabled={!probeEnabled || agents === null}
          onChange={(event) => {
            const value = event.target.value;
            if (value === "native") {
              onNativeTerminal();
              return;
            }
            const agent = (agents ?? []).find((item) => item.id === value);
            if (agent?.found) onEnter(agent);
          }}
        >
          <option value="native">{t("agent.nativeTerminal")}</option>
          {agents === null && selectedId !== "native" && (
            <option value={selectedId}>{activeAgentId || selectedId}</option>
          )}
          {(agents ?? []).map((agent) => (
            <option key={agent.id} value={agent.id} disabled={!agent.found}>
              {agent.name}
              {agent.id === defaultAgent?.id && agent.found ? ` (${t("agent.default")})` : ""}
              {!agent.found ? ` (${t("agent.notInstalled")})` : ""}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
