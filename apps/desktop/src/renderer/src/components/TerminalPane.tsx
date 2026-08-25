import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import { Terminal, type IDecoration, type IMarker } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebglAddon } from "@xterm/addon-webgl";
import { onAppEvent, writeClipboardText } from "../platform/bridge";
import "@xterm/xterm/css/xterm.css";
import { pickDefaultAgent, ptyKill, ptyResize, ptySpawn, ptyWrite } from "../api";
import { scheduleWindowResizeEvent } from "../paneLayout";
import { copySelectedTerminalText } from "../terminalClipboard";
import {
  classifyInitialPromptProcessExit,
  terminalLaunchCommand,
} from "../terminalJobLifecycle";
import { useI18n } from "../i18n";
import type { AgentInfo } from "../types";
import { AgentBar } from "./AgentBar";
import { Codicon } from "./Codicon";

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
  /** Resolves true only after the main process wrote to a live PTY. */
  runCommand: (cmd: string) => Promise<boolean>;
  activeSessionId: () => string;
  /**
   * Replaces the active PTY command. When supplied, initialPrompt is bound to
   * that CLI launch and the promise resolves true only after the process stays
   * live through the startup window or exits successfully.
   */
  switchCommand: (cmd: string, agentId?: string | null, initialPrompt?: string) => Promise<boolean>;
  newSession: () => void;
  focus: () => void;
}

export type TerminalSessionEndReason =
  | "process_exit"
  | "command_replaced"
  | "session_closed"
  | "component_unmounted";

type TerminalPaneProps = {
  cwd: string;
  onReady?: () => void;
  placeholder?: string;
  agents?: AgentInfo[] | null;
  probeEnabled?: boolean;
  onRuntimeStatus?: (status: AgentRuntimeStatus) => void;
  onPermissionNotice?: (notice: string) => void;
  onActiveAgentChange?: (agent: AgentInfo | null) => void;
  /** A logical executor lifetime ended; callers must tolerate duplicate lifecycle notifications. */
  onSessionEnd?: (sessionId: string, reason: TerminalSessionEndReason) => void;
};

type TerminalSessionState = {
  id: string;
  title: string;
  command: string;
  agentId: string | null;
};

type TerminalSessionHandle = {
  runCommand: (cmd: string) => Promise<boolean>;
  switchCommand: (cmd: string, agentId: string | null, initialPrompt?: string) => Promise<boolean>;
  focus: () => void;
};

let terminalSessionSeq = 0;
const MIN_RAIL_WIDTH = 30;
const COMPACT_RAIL_WIDTH = 54;
const DEFAULT_RAIL_WIDTH = MIN_RAIL_WIDTH;
const MAX_RAIL_WIDTH = 260;
const INITIAL_PROMPT_LAUNCH_STABILITY_MS = 1_200;

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
  onSessionEnd,
  toolbar,
}: {
  cwd: string;
  session: TerminalSessionState;
  active: boolean;
  register: (id: string, handle: TerminalSessionHandle | null) => void;
  onReady?: () => void;
  onRuntimeStatus?: (status: AgentRuntimeStatus) => void;
  onPermissionNotice?: (notice: string) => void;
  onSessionEnd?: (reason: TerminalSessionEndReason) => void;
  toolbar?: ReactNode;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const ptyIdRef = useRef<number | null>(null);
  const commandReadyRef = useRef(false);
  const termRef = useRef<Terminal | null>(null);
  const activeRef = useRef(active);
  const onReadyRef = useRef(onReady);
  const onRuntimeStatusRef = useRef(onRuntimeStatus);
  const onPermissionNoticeRef = useRef(onPermissionNotice);
  const onSessionEndRef = useRef(onSessionEnd);
  const switchCommandRef = useRef<(
    cmd: string,
    agentId: string | null,
    initialPrompt?: string,
  ) => Promise<boolean>>(async () => false);
  const scheduleRefitRef = useRef<() => void>(() => {});
  const decoderRef = useRef(new TextDecoder());
  const statusBufferRef = useRef("");
  const lastPermissionNoticeRef = useRef("");

  activeRef.current = active;
  onReadyRef.current = onReady;
  onRuntimeStatusRef.current = onRuntimeStatus;
  onPermissionNoticeRef.current = onPermissionNotice;
  onSessionEndRef.current = onSessionEnd;

  useEffect(() => {
    register(session.id, {
      runCommand: async (cmd: string) => {
        if (ptyIdRef.current == null || !commandReadyRef.current) return false;
        try {
          const written = await ptyWrite(ptyIdRef.current, cmd + "\r");
          termRef.current?.focus();
          return written;
        } catch {
          return false;
        }
      },
      switchCommand: async (cmd: string, agentId: string | null, initialPrompt?: string) => {
        const launched = await switchCommandRef.current(cmd, agentId, initialPrompt);
        termRef.current?.focus();
        return launched;
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
      theme: {
        background: "#1f1f1f",
        foreground: "#cccccc",
        cursor: "#ececf0",
        cursorAccent: "#1f1f1f",
        selectionBackground: "#6c6c7466",
      },
    });
    termRef.current = term;
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(hostRef.current);
    // Optional GPU renderer (opt-in: localStorage aa.terminal.webgl = "1").
    // Kept off by default — WebGL context creation is flaky on hidden /
    // unfocused windows and the DOM renderer matches the Tauri app.
    let webglTimer: number | null = null;
    if (window.localStorage.getItem("aa.terminal.webgl") === "1") {
      const tryLoadWebgl = (attempt = 0) => {
        if (disposed || !termRef.current) return;
        const host = hostRef.current;
        if (!host || host.clientWidth < 2 || host.clientHeight < 2 || !document.hasFocus()) {
          if (attempt < 20) webglTimer = window.setTimeout(() => tryLoadWebgl(attempt + 1), 300);
          return;
        }
        try {
          const webgl = new WebglAddon();
          webgl.onContextLoss(() => webgl.dispose());
          term.loadAddon(webgl);
        } catch {
          /* DOM renderer fallback */
        }
      };
      webglTimer = window.setTimeout(() => tryLoadWebgl(), 120);
    }

    let disposed = false;
    let runSeq = 0;
    let frameId: number | null = null;
    let inputHighlightFrame: number | null = null;
    let inputDecoration: IDecoration | undefined;
    let inputMarker: IMarker | undefined;
    const fitTimers: number[] = [];
    const unlisten: Array<() => void> = [];
    const disposables: Array<{ dispose: () => void }> = [];
    const endedPtyIds = new Set<number>();
    type InitialPromptLaunchOutcome = "live" | "completed" | "failed";
    const initialPromptPtyIds = new Set<number>();
    const earlyInitialPromptExitCodes = new Map<number, { exitCode: number; signal?: number }>();
    const initialPromptLaunchChecks = new Map<number, {
      timer: number;
      resolve: (outcome: InitialPromptLaunchOutcome) => void;
    }>();

    const settleInitialPromptLaunch = (id: number, outcome: InitialPromptLaunchOutcome) => {
      const check = initialPromptLaunchChecks.get(id);
      if (!check) return false;
      initialPromptLaunchChecks.delete(id);
      window.clearTimeout(check.timer);
      check.resolve(outcome);
      return true;
    };

    const verifyInitialPromptLaunch = (id: number, seq: number): Promise<InitialPromptLaunchOutcome> => {
      const earlyExit = earlyInitialPromptExitCodes.get(id);
      if (earlyExit) {
        earlyInitialPromptExitCodes.delete(id);
        initialPromptPtyIds.delete(id);
        return Promise.resolve(
          classifyInitialPromptProcessExit(earlyExit.exitCode, earlyExit.signal),
        );
      }
      return new Promise((resolve) => {
        const timer = window.setTimeout(() => {
          initialPromptLaunchChecks.delete(id);
          initialPromptPtyIds.delete(id);
          resolve(
            !disposed && seq === runSeq && ptyIdRef.current === id ? "live" : "failed",
          );
        }, INITIAL_PROMPT_LAUNCH_STABILITY_MS);
        initialPromptLaunchChecks.set(id, { timer, resolve });
      });
    };

    const notifyPtyEnded = (id: number, reason: TerminalSessionEndReason) => {
      if (endedPtyIds.has(id)) return;
      endedPtyIds.add(id);
      onSessionEndRef.current?.(reason);
    };

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

    const clearInputHighlight = () => {
      inputDecoration?.dispose();
      inputMarker?.dispose();
      inputDecoration = undefined;
      inputMarker = undefined;
    };

    const refreshInputHighlight = () => {
      if (inputHighlightFrame != null) window.cancelAnimationFrame(inputHighlightFrame);
      inputHighlightFrame = window.requestAnimationFrame(() => {
        inputHighlightFrame = null;
        clearInputHighlight();
        if (disposed || !activeRef.current || !hostRef.current?.contains(document.activeElement)) return;
        const marker = term.registerMarker(0);
        if (!marker) return;
        inputMarker = marker;
        inputDecoration = term.registerDecoration({
          marker,
          x: 0,
          width: Math.max(1, term.cols),
          height: 1,
          backgroundColor: "#343438",
          layer: "bottom",
        });
        inputDecoration?.onRender((element) => element.classList.add("terminal-input-line-highlight"));
      });
    };

    const handleTerminalFocus = () => refreshInputHighlight();
    const handleTerminalBlur = () => window.setTimeout(refreshInputHighlight, 0);
    hostRef.current.addEventListener("focusin", handleTerminalFocus);
    hostRef.current.addEventListener("focusout", handleTerminalBlur);

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

    async function startSession(
      command = "",
      clear = false,
      agentId: string | null = "native",
      initialPrompt?: string,
    ): Promise<boolean> {
      const seq = ++runSeq;
      const agentOwned = Boolean(agentId && agentId !== "native");
      const previous = ptyIdRef.current;
      ptyIdRef.current = null;
      commandReadyRef.current = false;
      statusBufferRef.current = "";
      lastPermissionNoticeRef.current = "";
      if (activeRef.current) onRuntimeStatusRef.current?.({});
      if (previous != null) {
        // Replacing an agent/native process ends the executor that owns any
        // jobs dispatched to this logical terminal session. Notify before the
        // asynchronous kill so a fast pty-exit cannot race past settlement.
        notifyPtyEnded(previous, "command_replaced");
        settleInitialPromptLaunch(previous, "failed");
        initialPromptPtyIds.delete(previous);
        earlyInitialPromptExitCodes.delete(previous);
        await ptyKill(previous).catch(() => {});
      }
      if (disposed || seq !== runSeq) return false;

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
          return false;
        }
        ptyIdRef.current = id;
        scheduleRefit();
        const launchCommand = terminalLaunchCommand(
          command,
          agentOwned,
          initialPrompt && agentId ? { agentId, prompt: initialPrompt } : undefined,
        );
        if (initialPrompt) initialPromptPtyIds.add(id);
        if (launchCommand && !await ptyWrite(id, launchCommand + "\r")) {
          throw new Error("PTY rejected terminal launch command");
        }
        if (initialPrompt) {
          const outcome = await verifyInitialPromptLaunch(id, seq);
          if (outcome === "completed") return true;
          if (outcome === "failed") return false;
        }
        if (disposed || seq !== runSeq || ptyIdRef.current !== id) return false;
        commandReadyRef.current = true;
        if (activeRef.current) onReadyRef.current?.();
        return true;
      } catch (e) {
        const failedId = ptyIdRef.current;
        ptyIdRef.current = null;
        commandReadyRef.current = false;
        if (failedId != null) {
          settleInitialPromptLaunch(failedId, "failed");
          initialPromptPtyIds.delete(failedId);
          earlyInitialPromptExitCodes.delete(failedId);
          ptyKill(failedId).catch(() => {});
        }
        if (!disposed) term.write(`\r\n\x1b[31m[terminal error] ${String(e)}\x1b[0m\r\n`);
        return false;
      }
    }

    switchCommandRef.current = (
      cmd: string,
      agentId: string | null,
      initialPrompt?: string,
    ) => {
      return startSession(cmd, true, agentId, initialPrompt).catch(() => false);
    };

    unlisten.push(
      onAppEvent("pty-data", (payload) => {
        if (payload.id !== ptyIdRef.current) return;
        const bytes = b64ToBytes(payload.data);
        term.write(bytes);
        publishRuntime(bytes);
      }),
    );
    unlisten.push(
      onAppEvent("pty-exit", (payload) => {
        if (payload.id !== ptyIdRef.current) return;
        if (initialPromptPtyIds.has(payload.id)) {
          const outcome = classifyInitialPromptProcessExit(payload.exitCode, payload.signal);
          if (!settleInitialPromptLaunch(payload.id, outcome)) {
            earlyInitialPromptExitCodes.set(payload.id, {
              exitCode: payload.exitCode,
              signal: payload.signal,
            });
          }
          initialPromptPtyIds.delete(payload.id);
        }
        ptyIdRef.current = null;
        commandReadyRef.current = false;
        term.write("\r\n\x1b[90m[process exited]\x1b[0m\r\n");
        notifyPtyEnded(payload.id, "process_exit");
      }),
    );

    disposables.push(
      term.onData((d) => {
        const id = ptyIdRef.current;
        if (id != null) ptyWrite(id, d).catch(() => {});
      }),
    );
    disposables.push(
      term.onSelectionChange(() => {
        copySelectedTerminalText(term, writeClipboardText);
      }),
    );
    disposables.push(term.onCursorMove(refreshInputHighlight));
    disposables.push(
      term.onResize(({ rows, cols }) => {
        const id = ptyIdRef.current;
        if (id != null) ptyResize(id, rows, cols).catch(() => {});
        refreshInputHighlight();
      }),
    );

    startSession(session.command, false, session.agentId).catch(() => false);
    scheduleRefit();

    const refit = () => scheduleRefit();
    window.addEventListener("resize", refit);
    const ro = new ResizeObserver(refit);
    ro.observe(hostRef.current);

    return () => {
      disposed = true;
      runSeq++;
      const livePty = ptyIdRef.current;
      ptyIdRef.current = null;
      commandReadyRef.current = false;
      for (const [id, check] of initialPromptLaunchChecks) {
        window.clearTimeout(check.timer);
        check.resolve("failed");
        initialPromptLaunchChecks.delete(id);
      }
      initialPromptPtyIds.clear();
      earlyInitialPromptExitCodes.clear();
      if (livePty != null) notifyPtyEnded(livePty, "component_unmounted");
      switchCommandRef.current = async () => false;
      scheduleRefitRef.current = () => {};
      window.removeEventListener("resize", refit);
      hostRef.current?.removeEventListener("focusin", handleTerminalFocus);
      hostRef.current?.removeEventListener("focusout", handleTerminalBlur);
      if (webglTimer != null) window.clearTimeout(webglTimer);
      if (frameId != null) window.cancelAnimationFrame(frameId);
      if (inputHighlightFrame != null) window.cancelAnimationFrame(inputHighlightFrame);
      clearInputHighlight();
      fitTimers.forEach((timer) => window.clearTimeout(timer));
      ro.disconnect();
      unlisten.forEach((fn) => fn());
      disposables.forEach((d) => d.dispose());
      if (livePty != null) ptyKill(livePty).catch(() => {});
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
    onActiveAgentChange,
    onSessionEnd,
  }, ref) {
    const { t } = useI18n();
    const [sessions, setSessions] = useState<TerminalSessionState[]>(() => [makeSession()]);
    const [activeId, setActiveId] = useState(() => sessions[0]?.id || "");
    const [placeholderClosed, setPlaceholderClosed] = useState(false);
    const [railWidth, setRailWidth] = useState(() => {
      const raw = window.localStorage.getItem("aa.terminalRailWidth");
      if (raw == null) return DEFAULT_RAIL_WIDTH;
      const saved = Number(raw);
      if (!Number.isFinite(saved) || saved < MIN_RAIL_WIDTH) return DEFAULT_RAIL_WIDTH;
      if (saved <= 46) return MIN_RAIL_WIDTH;
      return Math.min(MAX_RAIL_WIDTH, Math.max(MIN_RAIL_WIDTH, saved));
    });
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
      if (activeIdRef.current === id) onRuntimeStatus?.(status);
    }, [onRuntimeStatus]);

    function addSession() {
      const def = pickDefaultAgent(agents ?? []);
      const next = def ? makeSession(def.command, def.id) : makeSession();
      setSessions((prev) => [...prev, next]);
      setActiveId(next.id);
      onRuntimeStatus?.({});
      window.setTimeout(() => sessionRefs.current.get(next.id)?.focus(), 0);
    }

    function startRailResize(ev: ReactPointerEvent<HTMLDivElement>) {
      ev.preventDefault();
      const splitter = ev.currentTarget;
      document.body.classList.add("resizing-terminal-rail");
      splitter.classList.add("resizing");
      const startX = ev.clientX;
      const startWidth = railWidth;

      const move = (event: PointerEvent) => {
        const next = Math.min(MAX_RAIL_WIDTH, Math.max(MIN_RAIL_WIDTH, startWidth + startX - event.clientX));
        setRailWidth(next);
        window.localStorage.setItem("aa.terminalRailWidth", String(Math.round(next)));
        scheduleWindowResizeEvent();
      };
      const up = () => {
        document.body.classList.remove("resizing-terminal-rail");
        splitter.classList.remove("resizing");
        document.removeEventListener("pointermove", move);
        document.removeEventListener("pointerup", up);
        scheduleWindowResizeEvent();
      };
      document.addEventListener("pointermove", move);
      document.addEventListener("pointerup", up);
    }

    useImperativeHandle(ref, () => ({
      runCommand: async (cmd: string) => {
        const written = await (sessionRefs.current.get(activeIdRef.current)?.runCommand(cmd) ?? Promise.resolve(false));
        sessionRefs.current.get(activeIdRef.current)?.focus();
        return written;
      },
      activeSessionId: () => activeIdRef.current,
      switchCommand: async (cmd: string, agentId: string | null = "native", initialPrompt?: string) => {
        const id = activeIdRef.current;
        setSessions((prev) =>
          prev.map((session) =>
            session.id === id ? { ...session, title: commandTitle(cmd), command: cmd, agentId } : session,
          ),
        );
        const session = sessionRefs.current.get(id);
        if (!session) return false;
        const launched = await session.switchCommand(cmd, agentId, initialPrompt);
        session.focus();
        return launched;
      },
      newSession: () => addSession(),
      focus: () => sessionRefs.current.get(activeIdRef.current)?.focus(),
    }));

    function closeSession(id: string) {
      onSessionEnd?.(id, "session_closed");
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
      void sessionRefs.current.get(id)?.switchCommand("", "native");
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
      void sessionRefs.current.get(id)?.switchCommand(agent.command, agent.id);
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
              onSessionEnd={(reason) => onSessionEnd?.(session.id, reason)}
              toolbar={
                <AgentBar
                  className="terminal-agent-bar"
                  agents={agents}
                  probeEnabled={probeEnabled}
                  activeAgentId={session.agentId === "native" ? null : session.agentId}
                  nativeActive={session.agentId === "native"}
                  onNativeTerminal={() => switchSessionToNative(session.id)}
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
        <div
          className="terminal-rail-resizer"
          role="separator"
          aria-orientation="vertical"
          aria-label={t("operation.resizeTerminalAria")}
          onPointerDown={startRailResize}
          onDoubleClick={() => {
            setRailWidth(DEFAULT_RAIL_WIDTH);
            window.localStorage.removeItem("aa.terminalRailWidth");
            scheduleWindowResizeEvent();
          }}
        />
        <aside
          className={"terminal-session-rail" + (railWidth <= COMPACT_RAIL_WIDTH ? " compact" : "")}
          style={{ width: railWidth }}
          aria-label={t("terminal.sessions")}
        >
          <div className="terminal-session-list" role="tablist" aria-label={t("terminal.sessions")}>
            {sessions.map((session) => (
              <div
                key={session.id}
                className={"terminal-session-item" + (session.id === activeId ? " active" : "")}
                role="tab"
                tabIndex={0}
                aria-selected={session.id === activeId}
                aria-label={session.title}
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
                  aria-label={t("terminal.closeSession")}
                  onClick={(event) => {
                    event.stopPropagation();
                    closeSession(session.id);
                  }}
                >
                  <Codicon name="trash" />
                </button>
              </div>
            ))}
          </div>
        </aside>
      </div>
    );
  },
);
