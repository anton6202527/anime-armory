import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { listen } from "@tauri-apps/api/event";
import "@xterm/xterm/css/xterm.css";
import { ptyKill, ptyResize, ptySpawn, ptyWrite } from "../api";
import { useI18n } from "../i18n";
import type { AgentInfo } from "../types";
import { AgentBar } from "./AgentBar";

const b64ToBytes = (b64: string) => Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));

export interface AgentRuntimeStatus {
  model?: string;
  contextWindow?: string;
  contextUsage?: string;
  remainingTokens?: string;
  quota?: string;
  permission?: string;
  updatedAt?: number;
}

/** Imperative handle so parents can drive the live shell (e.g. "进入" an agent). */
export interface TerminalHandle {
  runCommand: (cmd: string) => void;
  switchCommand: (cmd: string, agentId?: string | null) => void;
  focus: () => void;
}

type TerminalPaneProps = {
  cwd: string;
  onReady?: () => void;
  placeholder?: string;
  agents?: AgentInfo[] | null;
  probeEnabled?: boolean;
  onRuntimeStatus?: (status: AgentRuntimeStatus) => void;
  onPermissionNotice?: (notice: string) => void;
  onRefreshAgents?: (force?: boolean) => void;
  onActiveAgentChange?: (agent: AgentInfo | null) => void;
};

type TerminalSessionState = {
  id: string;
  title: string;
  command: string;
  agentId: string | null;
};

type TerminalSessionHandle = {
  runCommand: (cmd: string) => void;
  switchCommand: (cmd: string) => void;
  focus: () => void;
};

let terminalSessionSeq = 0;

function terminalSessionId(): string {
  terminalSessionSeq += 1;
  return `term-${Date.now()}-${terminalSessionSeq}`;
}

function commandTitle(command: string): string {
  const clean = command.trim();
  if (!clean) return "zsh";
  const first = clean.split(/\s+/)[0] || clean;
  return first.split("/").pop() || first;
}

function makeSession(command = "", agentId: string | null = "native"): TerminalSessionState {
  return {
    id: terminalSessionId(),
    title: commandTitle(command),
    command,
    agentId,
  };
}

function cleanTerminalText(value: string): string {
  return value
    .replace(/\x1b\][^\x07]*(?:\x07|\x1b\\)/g, "")
    .replace(/\x1b\[[0-?]*[ -/]*[@-~]/g, "")
    .replace(/\r/g, "\n");
}

function lastMatch(value: string, pattern: RegExp): string | undefined {
  let match: RegExpExecArray | null;
  let last: string | undefined;
  const global = new RegExp(pattern.source, pattern.flags.includes("g") ? pattern.flags : `${pattern.flags}g`);
  while ((match = global.exec(value))) {
    last = match[1] || match[0];
  }
  return last ? last.trim() : undefined;
}

function parseRuntimeStatus(buffer: string): AgentRuntimeStatus {
  const lines = buffer
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);
  const reversed = [...lines].reverse();
  const modelLine = reversed.find(
    (line) =>
      /(opus|sonnet|haiku|claude|max|gpt[-\w.]*|codex|gemini|kimi|moonshot)/i.test(line) &&
      /(context|model|gpt[-\w.]*)/i.test(line),
  );
  const model =
    modelLine?.match(/\b((?:Claude\s+)?(?:Opus|Sonnet|Haiku)[^|,\n]*)/i)?.[1]?.trim() ||
    modelLine?.match(/\b(gpt[-\w.]+(?:\s+(?:low|medium|high|xhigh))?)\b/i)?.[1]?.trim() ||
    modelLine?.match(/\b(Gemini[^|,\n]*)/i)?.[1]?.trim() ||
    modelLine?.match(/\b(Kimi[^|,\n]*|Moonshot[^|,\n]*)/i)?.[1]?.trim() ||
    modelLine?.match(/\b(Codex[^|,\n]*)/i)?.[1]?.trim();
  const contextWindow =
    modelLine?.match(/\(([^)]*context[^)]*)\)/i)?.[1]?.trim() ||
    lastMatch(buffer, /\b([\d.]+\s*[kKmM]?\s*context)\b/i);
  const contextUsage = lastMatch(buffer, /\b(\d{1,3}%\s*context)\b/i);
  const remainingTokens =
    lastMatch(buffer, /\b([\d,]+)\s+tokens?\s+(?:remaining|left)\b/i) ||
    lastMatch(buffer, /\b(?:remaining|left)\s+([\d,]+)\s+tokens?\b/i);
  const quota = reversed.find((line) =>
    /\b(weekly usage limit|usage limit|quota|credits?|tokens? remaining)\b/i.test(line),
  );
  const permission = reversed.find((line) =>
    /\b(bypass permissions on|dangerously[-\s]?skip[-\s]?permissions|auto[-\s]?approve|approval\s*[:=]\s*never|allow all|full access)\b/i.test(line),
  );

  return {
    model,
    contextWindow,
    contextUsage,
    remainingTokens,
    quota: quota && quota.length <= 180 ? quota : undefined,
    permission: permission && permission.length <= 180 ? permission : undefined,
    updatedAt: Date.now(),
  };
}

function TerminalSessionView({
  cwd,
  session,
  active,
  register,
  onReady,
  onRuntimeStatus,
  onPermissionNotice,
  toolbar,
}: {
  cwd: string;
  session: TerminalSessionState;
  active: boolean;
  register: (id: string, handle: TerminalSessionHandle | null) => void;
  onReady?: () => void;
  onRuntimeStatus?: (status: AgentRuntimeStatus) => void;
  onPermissionNotice?: (notice: string) => void;
  toolbar?: ReactNode;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const ptyIdRef = useRef<number | null>(null);
  const termRef = useRef<Terminal | null>(null);
  const activeRef = useRef(active);
  const onReadyRef = useRef(onReady);
  const onRuntimeStatusRef = useRef(onRuntimeStatus);
  const onPermissionNoticeRef = useRef(onPermissionNotice);
  const switchCommandRef = useRef<(cmd: string) => void>(() => {});
  const scheduleRefitRef = useRef<() => void>(() => {});
  const decoderRef = useRef(new TextDecoder());
  const statusBufferRef = useRef("");
  const lastPermissionNoticeRef = useRef("");

  activeRef.current = active;
  onReadyRef.current = onReady;
  onRuntimeStatusRef.current = onRuntimeStatus;
  onPermissionNoticeRef.current = onPermissionNotice;

  useEffect(() => {
    register(session.id, {
      runCommand: (cmd: string) => {
        if (ptyIdRef.current != null) ptyWrite(ptyIdRef.current, cmd + "\r").catch(() => {});
        termRef.current?.focus();
      },
      switchCommand: (cmd: string) => {
        switchCommandRef.current(cmd);
        termRef.current?.focus();
      },
      focus: () => termRef.current?.focus(),
    });
    return () => register(session.id, null);
  }, [register, session.id]);

  useEffect(() => {
    if (active) {
      scheduleRefitRef.current();
      termRef.current?.focus();
      onRuntimeStatusRef.current?.({});
    }
  }, [active]);

  useEffect(() => {
    if (!hostRef.current) return;
    const term = new Terminal({
      fontSize: 12.5,
      fontFamily: "Menlo, Monaco, monospace",
      cursorBlink: true,
      scrollback: 300,
      theme: { background: "#121413", foreground: "#cccccc" },
    });
    termRef.current = term;
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(hostRef.current);

    let disposed = false;
    let runSeq = 0;
    let frameId: number | null = null;
    const fitTimers: number[] = [];
    const unlisten: Array<() => void> = [];
    const disposables: Array<{ dispose: () => void }> = [];

    const fitToHost = () => {
      if (disposed || !activeRef.current || !hostRef.current) return;
      try {
        fit.fit();
      } catch {
        return;
      }
      const id = ptyIdRef.current;
      if (id != null) ptyResize(id, term.rows, term.cols).catch(() => {});
    };

    const scheduleRefit = () => {
      if (frameId != null) window.cancelAnimationFrame(frameId);
      while (fitTimers.length) {
        const timer = fitTimers.pop();
        if (timer != null) window.clearTimeout(timer);
      }
      frameId = window.requestAnimationFrame(() => {
        frameId = null;
        fitToHost();
      });
      for (const delay of [40, 160, 500]) {
        fitTimers.push(window.setTimeout(fitToHost, delay));
      }
    };
    scheduleRefitRef.current = scheduleRefit;

    function addUnlisten(promise: Promise<() => void>) {
      promise
        .then((fn) => {
          if (disposed) fn();
          else unlisten.push(fn);
        })
        .catch(() => {});
    }

    function publishRuntime(bytes: Uint8Array) {
      const text = cleanTerminalText(decoderRef.current.decode(bytes));
      if (!text.trim()) return;
      statusBufferRef.current = `${statusBufferRef.current}${text}`.slice(-8000);
      const status = parseRuntimeStatus(statusBufferRef.current);
      if (
        activeRef.current &&
        (status.model ||
          status.contextWindow ||
          status.contextUsage ||
          status.remainingTokens ||
          status.quota ||
          status.permission)
      ) {
        onRuntimeStatusRef.current?.(status);
      }
      if (
        activeRef.current &&
        status.permission &&
        status.permission !== lastPermissionNoticeRef.current
      ) {
        lastPermissionNoticeRef.current = status.permission;
        onPermissionNoticeRef.current?.(status.permission);
      }
    }

    async function startSession(command?: string, clear = false) {
      const seq = ++runSeq;
      const previous = ptyIdRef.current;
      ptyIdRef.current = null;
      statusBufferRef.current = "";
      lastPermissionNoticeRef.current = "";
      if (activeRef.current) onRuntimeStatusRef.current?.({});
      if (previous != null) await ptyKill(previous).catch(() => {});
      if (disposed || seq !== runSeq) return;

      if (clear) {
        try {
          term.reset();
          term.clear();
        } catch {
          /* noop */
        }
      }

      try {
        fitToHost();
        const id = await ptySpawn(cwd, Math.max(1, term.rows), Math.max(1, term.cols));
        if (disposed || seq !== runSeq) {
          ptyKill(id).catch(() => {});
          return;
        }
        ptyIdRef.current = id;
        scheduleRefit();
        if (activeRef.current) onReadyRef.current?.();
        if (command) ptyWrite(id, command + "\r").catch(() => {});
      } catch (e) {
        if (!disposed) term.write(`\r\n\x1b[31m[terminal error] ${String(e)}\x1b[0m\r\n`);
      }
    }

    switchCommandRef.current = (cmd: string) => {
      startSession(cmd, true).catch(() => {});
    };

    addUnlisten(
      listen<{ id: number; data: string }>("pty-data", (e) => {
        if (e.payload.id !== ptyIdRef.current) return;
        const bytes = b64ToBytes(e.payload.data);
        term.write(bytes);
        publishRuntime(bytes);
      }),
    );
    addUnlisten(
      listen<{ id: number }>("pty-exit", (e) => {
        if (e.payload.id !== ptyIdRef.current) return;
        ptyIdRef.current = null;
        term.write("\r\n\x1b[90m[process exited]\x1b[0m\r\n");
      }),
    );

    disposables.push(
      term.onData((d) => {
        const id = ptyIdRef.current;
        if (id != null) ptyWrite(id, d).catch(() => {});
      }),
    );
    disposables.push(
      term.onResize(({ rows, cols }) => {
        const id = ptyIdRef.current;
        if (id != null) ptyResize(id, rows, cols).catch(() => {});
      }),
    );

    startSession(session.command).catch(() => {});
    scheduleRefit();

    const refit = () => scheduleRefit();
    window.addEventListener("resize", refit);
    const ro = new ResizeObserver(refit);
    ro.observe(hostRef.current);

    return () => {
      disposed = true;
      runSeq++;
      switchCommandRef.current = () => {};
      scheduleRefitRef.current = () => {};
      window.removeEventListener("resize", refit);
      if (frameId != null) window.cancelAnimationFrame(frameId);
      fitTimers.forEach((timer) => window.clearTimeout(timer));
      ro.disconnect();
      unlisten.forEach((fn) => fn());
      disposables.forEach((d) => d.dispose());
      if (ptyIdRef.current != null) ptyKill(ptyIdRef.current).catch(() => {});
      ptyIdRef.current = null;
      termRef.current = null;
      term.dispose();
    };
  }, [cwd, session.id]);

  return (
    <div className={"terminal-session" + (active ? " active" : "")}>
      {toolbar}
      <div className="terminal-pane" ref={hostRef} />
    </div>
  );
}

// Native terminal: real PTY sessions (Rust portable-pty) bridged to xterm.js.
// Each right-rail entry owns a live PTY, similar to VS Code's terminal list.
export const TerminalPane = forwardRef<TerminalHandle, TerminalPaneProps>(
  function TerminalPane({
    cwd,
    onReady,
    placeholder,
    agents = null,
    probeEnabled = true,
    onRuntimeStatus,
    onPermissionNotice,
    onRefreshAgents,
    onActiveAgentChange,
  }, ref) {
    const { t } = useI18n();
    const [sessions, setSessions] = useState<TerminalSessionState[]>(() => [makeSession()]);
    const [activeId, setActiveId] = useState(() => sessions[0]?.id || "");
    const [runtimeStatusById, setRuntimeStatusById] = useState<Record<string, AgentRuntimeStatus>>({});
    const [placeholderClosed, setPlaceholderClosed] = useState(false);
    const activeIdRef = useRef(activeId);
    const sessionRefs = useRef<Map<string, TerminalSessionHandle>>(new Map());

    activeIdRef.current = activeId;

    const registerSession = useCallback((id: string, handle: TerminalSessionHandle | null) => {
      if (handle) sessionRefs.current.set(id, handle);
      else sessionRefs.current.delete(id);
    }, []);

    useEffect(() => {
      const first = makeSession();
      sessionRefs.current.clear();
      setSessions([first]);
      setActiveId(first.id);
      setRuntimeStatusById({});
      setPlaceholderClosed(false);
      onRuntimeStatus?.({});
    }, [cwd, onRuntimeStatus]);

    useEffect(() => {
      if (!placeholder) setPlaceholderClosed(false);
    }, [placeholder]);

    const agentForSession = useCallback((session: TerminalSessionState | undefined): AgentInfo | null => {
      if (!session || !session.agentId || session.agentId === "native") return null;
      const agent = (agents ?? []).find((item) => item.id === session.agentId);
      return agent?.found ? agent : null;
    }, [agents]);

    useEffect(() => {
      onActiveAgentChange?.(agentForSession(sessions.find((session) => session.id === activeId)));
    }, [activeId, sessions, agentForSession, onActiveAgentChange]);

    const publishRuntimeStatus = useCallback((id: string, status: AgentRuntimeStatus) => {
      setRuntimeStatusById((prev) => ({ ...prev, [id]: status }));
      if (activeIdRef.current === id) onRuntimeStatus?.(status);
    }, [onRuntimeStatus]);

    useImperativeHandle(ref, () => ({
      runCommand: (cmd: string) => {
        sessionRefs.current.get(activeIdRef.current)?.runCommand(cmd);
        sessionRefs.current.get(activeIdRef.current)?.focus();
      },
      switchCommand: (cmd: string, agentId: string | null = "native") => {
        const id = activeIdRef.current;
        setSessions((prev) =>
          prev.map((session) =>
            session.id === id ? { ...session, title: commandTitle(cmd), command: cmd, agentId } : session,
          ),
        );
        setRuntimeStatusById((prev) => ({ ...prev, [id]: {} }));
        sessionRefs.current.get(id)?.switchCommand(cmd);
        sessionRefs.current.get(id)?.focus();
      },
      focus: () => sessionRefs.current.get(activeIdRef.current)?.focus(),
    }));

    function addSession() {
      const next = makeSession();
      setSessions((prev) => [...prev, next]);
      setActiveId(next.id);
      setRuntimeStatusById((prev) => ({ ...prev, [next.id]: {} }));
      onRuntimeStatus?.({});
    }

    function closeSession(id: string) {
      setRuntimeStatusById((statuses) => {
        const nextStatuses = { ...statuses };
        delete nextStatuses[id];
        return nextStatuses;
      });
      setSessions((prev) => {
        const index = prev.findIndex((session) => session.id === id);
        const remaining = prev.filter((session) => session.id !== id);
        if (remaining.length === 0) {
          const replacement = makeSession();
          setActiveId(replacement.id);
          onRuntimeStatus?.({});
          return [replacement];
        }
        if (activeIdRef.current === id) {
          const next = remaining[Math.max(0, index - 1)] || remaining[0];
          setActiveId(next.id);
          onRuntimeStatus?.({});
        }
        return remaining;
      });
    }

    function switchSessionToNative(id: string) {
      setSessions((prev) =>
        prev.map((session) =>
          session.id === id ? { ...session, title: commandTitle(""), command: "", agentId: "native" } : session,
        ),
      );
      setRuntimeStatusById((prev) => ({ ...prev, [id]: {} }));
      sessionRefs.current.get(id)?.switchCommand("");
      sessionRefs.current.get(id)?.focus();
      if (activeIdRef.current === id) {
        onRuntimeStatus?.({});
        onActiveAgentChange?.(null);
      }
    }

    function switchSessionToAgent(id: string, agent: AgentInfo) {
      setSessions((prev) =>
        prev.map((session) =>
          session.id === id
            ? { ...session, title: commandTitle(agent.command), command: agent.command, agentId: agent.id }
            : session,
        ),
      );
      setRuntimeStatusById((prev) => ({ ...prev, [id]: {} }));
      sessionRefs.current.get(id)?.switchCommand(agent.command);
      sessionRefs.current.get(id)?.focus();
      if (activeIdRef.current === id) {
        onRuntimeStatus?.({});
        onActiveAgentChange?.(agent);
      }
    }

    const showPlaceholder = Boolean(placeholder && !placeholderClosed);

    return (
      <div className="terminal-wrap">
        <div className="terminal-sessions-host">
          {sessions.map((session) => (
            <TerminalSessionView
              key={session.id}
              cwd={cwd}
              session={session}
              active={session.id === activeId}
              register={registerSession}
              onReady={onReady}
              onRuntimeStatus={(status) => publishRuntimeStatus(session.id, status)}
              onPermissionNotice={onPermissionNotice}
              toolbar={
                <AgentBar
                  className="terminal-agent-bar"
                  agents={agents}
                  probeEnabled={probeEnabled}
                  activeAgentId={session.agentId === "native" ? null : session.agentId}
                  nativeActive={session.agentId === "native"}
                  runtimeStatus={runtimeStatusById[session.id]}
                  onNativeTerminal={() => switchSessionToNative(session.id)}
                  onRefresh={onRefreshAgents ?? (() => {})}
                  onEnter={(agent) => switchSessionToAgent(session.id, agent)}
                />
              }
            />
          ))}
          {showPlaceholder ? (
            <div className="terminal-placeholder" aria-live="polite">
              <button
                type="button"
                className="terminal-placeholder-close"
                aria-label={t("terminal.closeHint")}
                title={t("terminal.closeHint")}
                onClick={() => setPlaceholderClosed(true)}
              >
                ×
              </button>
              <span>{placeholder}</span>
            </div>
          ) : null}
        </div>
        <aside className="terminal-session-rail" aria-label={t("terminal.sessions")}>
          <div className="terminal-session-tools">
            <button
              type="button"
              className="terminal-session-add"
              title={t("terminal.newSession")}
              aria-label={t("terminal.newSession")}
              onClick={addSession}
            >
              +
            </button>
          </div>
          <div className="terminal-session-list" role="tablist" aria-label={t("terminal.sessions")}>
            {sessions.map((session) => (
              <div
                key={session.id}
                className={"terminal-session-item" + (session.id === activeId ? " active" : "")}
                role="tab"
                tabIndex={0}
                aria-selected={session.id === activeId}
                title={session.title}
                onClick={() => {
                  setActiveId(session.id);
                  onRuntimeStatus?.({});
                }}
                onKeyDown={(event) => {
                  if (event.key !== "Enter" && event.key !== " ") return;
                  event.preventDefault();
                  setActiveId(session.id);
                  onRuntimeStatus?.({});
                }}
              >
                <span className="terminal-session-icon" aria-hidden="true">
                  &gt;_
                </span>
                <span className="terminal-session-title">{session.title}</span>
                <button
                  type="button"
                  className="terminal-session-close"
                  title={t("terminal.closeSession")}
                  aria-label={t("terminal.closeSession")}
                  onClick={(event) => {
                    event.stopPropagation();
                    closeSession(session.id);
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </aside>
      </div>
    );
  },
);
