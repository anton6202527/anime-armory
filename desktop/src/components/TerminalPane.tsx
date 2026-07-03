import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { listen } from "@tauri-apps/api/event";
import "@xterm/xterm/css/xterm.css";
import { ptyKill, ptyResize, ptySpawn, ptyWrite } from "../api";

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
  switchCommand: (cmd: string) => void;
  focus: () => void;
}

type TerminalPaneProps = {
  cwd: string;
  onReady?: () => void;
  placeholder?: string;
  onRuntimeStatus?: (status: AgentRuntimeStatus) => void;
  onPermissionNotice?: (notice: string) => void;
};

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

// Native terminal: a real PTY (Rust portable-pty) bridged to xterm.js.
// Spawns a shell in `cwd`; the user runs skill scripts / claude directly.
export const TerminalPane = forwardRef<TerminalHandle, TerminalPaneProps>(
  function TerminalPane({ cwd, onReady, placeholder, onRuntimeStatus, onPermissionNotice }, ref) {
  const hostRef = useRef<HTMLDivElement>(null);
  const ptyIdRef = useRef<number | null>(null);
  const termRef = useRef<Terminal | null>(null);
  const onReadyRef = useRef(onReady);
  const onRuntimeStatusRef = useRef(onRuntimeStatus);
  const onPermissionNoticeRef = useRef(onPermissionNotice);
  const switchCommandRef = useRef<(cmd: string) => void>(() => {});
  const decoderRef = useRef(new TextDecoder());
  const statusBufferRef = useRef("");
  const lastPermissionNoticeRef = useRef("");
  onReadyRef.current = onReady;
  onRuntimeStatusRef.current = onRuntimeStatus;
  onPermissionNoticeRef.current = onPermissionNotice;

  useImperativeHandle(ref, () => ({
    runCommand: (cmd: string) => {
      if (ptyIdRef.current != null) ptyWrite(ptyIdRef.current, cmd + "\r").catch(() => {});
      termRef.current?.focus();
    },
    switchCommand: (cmd: string) => {
      switchCommandRef.current(cmd);
      termRef.current?.focus();
    },
    focus: () => termRef.current?.focus(),
  }));

  useEffect(() => {
    if (!hostRef.current) return;
    const term = new Terminal({
      fontSize: 12.5,
      fontFamily: "Menlo, Monaco, monospace",
      cursorBlink: true,
      theme: { background: "#121413", foreground: "#cccccc" },
    });
    termRef.current = term;
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(hostRef.current);

    let disposed = false;
    let sessionSeq = 0;
    let frameId: number | null = null;
    const fitTimers: number[] = [];
    const unlisten: Array<() => void> = [];
    const disposables: Array<{ dispose: () => void }> = [];

    const fitToHost = () => {
      if (disposed || !hostRef.current) return;
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

    function addUnlisten(promise: Promise<() => void>) {
      promise
        .then((fn) => {
          if (disposed) fn();
          else unlisten.push(fn);
        })
        .catch(() => {});
    }

    function handleTerminalOutput(bytes: Uint8Array) {
      const text = cleanTerminalText(decoderRef.current.decode(bytes));
      if (!text.trim()) return;
      statusBufferRef.current = `${statusBufferRef.current}${text}`.slice(-8000);
      const status = parseRuntimeStatus(statusBufferRef.current);
      if (
        status.model ||
        status.contextWindow ||
        status.contextUsage ||
        status.remainingTokens ||
        status.quota ||
        status.permission
      ) {
        onRuntimeStatusRef.current?.(status);
      }
      if (status.permission && status.permission !== lastPermissionNoticeRef.current) {
        lastPermissionNoticeRef.current = status.permission;
        onPermissionNoticeRef.current?.(status.permission);
      }
    }

    async function startSession(command?: string, clear = false) {
      const seq = ++sessionSeq;
      const previous = ptyIdRef.current;
      ptyIdRef.current = null;
      statusBufferRef.current = "";
      lastPermissionNoticeRef.current = "";
      onRuntimeStatusRef.current?.({});
      if (previous != null) await ptyKill(previous).catch(() => {});
      if (disposed || seq !== sessionSeq) return;

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
        const id = await ptySpawn(cwd, term.rows, term.cols);
        if (disposed || seq !== sessionSeq) {
          ptyKill(id).catch(() => {});
          return;
        }
        ptyIdRef.current = id;
        scheduleRefit();
        onReadyRef.current?.(); // PTY live — parent may now auto-run a command
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
        handleTerminalOutput(bytes);
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

    startSession().catch(() => {});

    scheduleRefit();

    const refit = () => scheduleRefit();
    window.addEventListener("resize", refit);
    const ro = new ResizeObserver(refit);
    ro.observe(hostRef.current);

    return () => {
      disposed = true;
      sessionSeq++;
      switchCommandRef.current = () => {};
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
  }, [cwd]);

  return (
    <div className="terminal-wrap">
      <div className="terminal-pane" ref={hostRef} />
      {placeholder ? (
        <div className="terminal-placeholder" aria-live="polite">
          {placeholder}
        </div>
      ) : null}
    </div>
  );
});
