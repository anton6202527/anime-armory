import { pickDefaultAgent } from "../api";
import { useI18n } from "../i18n";
import type { AgentInfo } from "../types";

function PaletteIcon() {
  return (
    <svg className="ab-palette-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M12.1 3.3c-5.1 0-8.8 3.4-8.8 8.1 0 4.1 3.1 7.3 7.5 7.3h1.4c.8 0 1.3.5 1.3 1.2 0 .5.4.8.9.8 3.6-.6 6.3-3.7 6.3-7.7 0-5.5-3.7-9.7-8.6-9.7Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <circle cx="8.1" cy="10.3" r="1.35" fill="currentColor" />
      <circle cx="11.3" cy="7.7" r="1.35" fill="currentColor" />
      <circle cx="15.5" cy="9.1" r="1.35" fill="currentColor" />
      <circle cx="16.2" cy="13.2" r="1.35" fill="currentColor" />
    </svg>
  );
}

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
  const selectedImageCapability = selectedAgent?.found ? selectedAgent.image : "no";
  const showImageBadge = selectedImageCapability === "yes" || selectedImageCapability === "maybe";

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
            if (agent?.found) {
              try {
                window.localStorage.setItem("aa.preferredAgentId", agent.id);
              } catch {
                /* preference storage is optional; entering the agent is not */
              }
              onEnter(agent);
            }
          }}
        >
          <option value="native">{t("agent.nativeTerminal")}</option>
          {agents === null && selectedId !== "native" && (
            <option value={selectedId}>{activeAgentId || selectedId}</option>
          )}
          {(agents ?? []).map((agent) => (
            <option key={agent.id} value={agent.id} disabled={!agent.found}>
              {agent.name}
              {!agent.found ? ` (${t("agent.notInstalled")})` : ""}
            </option>
          ))}
        </select>
        {showImageBadge && (
          <span
            className={`ab-image-badge ${selectedImageCapability}`}
            title={selectedImageCapability === "yes" ? t("agent.image") : `${t("agent.image")} ?`}
            aria-label={selectedImageCapability === "yes" ? t("agent.image") : `${t("agent.image")} ?`}
          >
            <PaletteIcon />
          </span>
        )}
      </label>
    </div>
  );
}
