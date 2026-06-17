import { useEffect, useState } from "react";
import { detectAgents, pickDefaultAgent } from "../api";
import type { AgentInfo } from "../types";

/** Auto-detects local AI agent CLIs and lets the user jump into one in the
 *  terminal. Image-capable (生图) agents get a 🎨 badge. */
export function AgentBar({ onEnter }: { onEnter: (cmd: string) => void }) {
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
      <span className="ab-title">AI Agent</span>

      {agents === null && <span className="ab-hint">检测中…</span>}
      {agents !== null && found.length === 0 && (
        <span className="ab-hint">未检测到本地 AI Agent CLI（claude / codex / gemini）</span>
      )}

      {found.map((a) => {
        const img = a.image === "yes" ? "🎨" : a.image === "maybe" ? "🎨?" : "";
        return (
          <button
            key={a.id}
            className={"ab-chip" + (a.image === "yes" ? " img" : "")}
            title={`${a.command}  ·  ${a.path}\n${a.note}`}
            onClick={() => onEnter(a.command)}
          >
            <span className="ab-name">{a.name}</span>
            {a.id === defaultId && <span className="ab-default" title="打开作品时自动进入">默认</span>}
            {img && (
              <span className={"ab-img" + (a.image === "maybe" ? " dim" : "")} title={a.note}>
                {img} 生图
              </span>
            )}
            <span className="ab-enter">进入 →</span>
          </button>
        );
      })}

      <button className="ab-refresh" title="重新检测" onClick={() => probe(true)}>
        ↻
      </button>
    </div>
  );
}
