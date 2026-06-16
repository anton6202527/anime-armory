import { useEffect, useRef } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { listen } from "@tauri-apps/api/event";
import "@xterm/xterm/css/xterm.css";
import { ptyKill, ptyResize, ptySpawn, ptyWrite } from "../api";

const b64ToBytes = (b64: string) => Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));

// Native terminal: a real PTY (Rust portable-pty) bridged to xterm.js.
// Spawns a shell in `cwd`; the user runs skill scripts / claude directly.
export function TerminalPane({ cwd }: { cwd: string }) {
  const hostRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!hostRef.current) return;
    const term = new Terminal({
      fontSize: 12.5,
      fontFamily: "Menlo, Monaco, monospace",
      cursorBlink: true,
      theme: { background: "#0b0e14", foreground: "#d6deeb" },
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(hostRef.current);
    try {
      fit.fit();
    } catch {
      /* noop */
    }

    let disposed = false;
    let ptyId: number | null = null;
    const unlisten: Array<() => void> = [];

    (async () => {
      const id = await ptySpawn(cwd, term.rows, term.cols);
      if (disposed) {
        ptyKill(id).catch(() => {});
        return;
      }
      ptyId = id;

      unlisten.push(
        await listen<{ id: number; data: string }>("pty-data", (e) => {
          if (e.payload.id === id) term.write(b64ToBytes(e.payload.data));
        }),
      );
      unlisten.push(
        await listen<{ id: number }>("pty-exit", (e) => {
          if (e.payload.id === id) term.write("\r\n\x1b[90m[process exited]\x1b[0m\r\n");
        }),
      );

      term.onData((d) => ptyWrite(id, d).catch(() => {}));
      term.onResize(({ rows, cols }) => ptyResize(id, rows, cols).catch(() => {}));
    })();

    const refit = () => {
      try {
        fit.fit();
      } catch {
        /* noop */
      }
    };
    window.addEventListener("resize", refit);
    const ro = new ResizeObserver(refit);
    ro.observe(hostRef.current);

    return () => {
      disposed = true;
      window.removeEventListener("resize", refit);
      ro.disconnect();
      unlisten.forEach((fn) => fn());
      if (ptyId != null) ptyKill(ptyId).catch(() => {});
      term.dispose();
    };
  }, [cwd]);

  return <div className="terminal-pane" ref={hostRef} />;
}
