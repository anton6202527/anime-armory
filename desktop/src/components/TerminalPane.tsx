import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { listen } from "@tauri-apps/api/event";
import "@xterm/xterm/css/xterm.css";
import { ptyKill, ptyResize, ptySpawn, ptyWrite } from "../api";

const b64ToBytes = (b64: string) => Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));

/** Imperative handle so parents can drive the live shell (e.g. "进入" an agent). */
export interface TerminalHandle {
  runCommand: (cmd: string) => void;
  switchCommand: (cmd: string) => void;
  focus: () => void;
}

// Native terminal: a real PTY (Rust portable-pty) bridged to xterm.js.
// Spawns a shell in `cwd`; the user runs skill scripts / claude directly.
export const TerminalPane = forwardRef<TerminalHandle, { cwd: string; onReady?: () => void }>(
  function TerminalPane({ cwd, onReady }, ref) {
  const hostRef = useRef<HTMLDivElement>(null);
  const ptyIdRef = useRef<number | null>(null);
  const termRef = useRef<Terminal | null>(null);
  const onReadyRef = useRef(onReady);
  const switchCommandRef = useRef<(cmd: string) => void>(() => {});
  onReadyRef.current = onReady;

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
      theme: { background: "#0b0e14", foreground: "#d6deeb" },
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

    async function startSession(command?: string, clear = false) {
      const seq = ++sessionSeq;
      const previous = ptyIdRef.current;
      ptyIdRef.current = null;
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
        if (e.payload.id === ptyIdRef.current) term.write(b64ToBytes(e.payload.data));
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

  return <div className="terminal-pane" ref={hostRef} />;
});
