import { pickDefaultAgent } from "../api";
import { useI18n } from "../i18n";
import type { AgentInfo } from "../types";
import type { AgentRuntimeStatus } from "./TerminalPane";

function imageLabel(agent: AgentInfo, imageText: string): string {
  if (agent.image === "yes") return imageText;
  if (agent.image === "maybe") return `${imageText}?`;
  return "";
}

function statusText(status: AgentRuntimeStatus | undefined, tokenText: (count: string) => string): string {
  if (!status) return "";
  const parts = [
    status.model,
    status.contextWindow,
    status.contextUsage,
    status.remainingTokens ? tokenText(status.remainingTokens) : "",
    status.quota,
  ].filter(Boolean);
  return parts.join(" · ");
}

/** Auto-detects local AI agent CLIs and lets the user jump into one in the
 *  terminal. Missing mainstream agents stay visible but disabled. */
export function AgentBar({
  className = "",
  activeAgentId,
  nativeActive,
  agents,
  runtimeStatus,
  probeEnabled = true,
  onNativeTerminal,
  onEnter,
  onRefresh,
}: {
  className?: string;
  activeAgentId?: string | null;
  nativeActive?: boolean;
  agents: AgentInfo[] | null;
  runtimeStatus?: AgentRuntimeStatus;
  probeEnabled?: boolean;
  onNativeTerminal: () => void;
  onEnter: (agent: AgentInfo) => void;
  onRefresh: (force?: boolean) => void;
}) {
  const { t } = useI18n();
  const defaultAgent = agents ? pickDefaultAgent(agents) : null;
  const selectedId = nativeActive ? "native" : activeAgentId || defaultAgent?.id || "native";
  const selectedAgent = (agents ?? []).find((agent) => agent.id === selectedId);
  const selectedStatus = statusText(runtimeStatus, (count) => t("agent.tokensLeft", { count }));
  const selectedMeta = selectedAgent
    ? [
        selectedAgent.id === defaultAgent?.id ? t("agent.default") : "",
        imageLabel(selectedAgent, t("agent.image")),
        selectedAgent.found ? selectedAgent.path : t("agent.notInstalled"),
      ]
        .filter(Boolean)
        .join(" · ")
    : nativeActive
      ? t("agent.nativeTerminal")
      : "";

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

      <div className="ab-status" title={selectedStatus || selectedMeta || selectedAgent?.note || ""}>
        {!probeEnabled ? (
          <span className="ab-hint">{t("agent.deferred")}</span>
        ) : agents === null ? (
          <span className="ab-hint">{t("agent.detecting")}</span>
        ) : selectedStatus ? (
          <span>{selectedStatus}</span>
        ) : selectedAgent?.found ? (
          <span>{selectedMeta || t("agent.statusWaiting")}</span>
        ) : (
          <span className="ab-hint">{t("agent.statusWaiting")}</span>
        )}
        {runtimeStatus?.permission && <span className="ab-permission">{t("agent.permissionOn")}</span>}
      </div>

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
