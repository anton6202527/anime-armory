import { useEffect, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { detectAgents, pickDefaultAgent, readCanvas, unwatchRoot, watchRoot } from "../api";
import type { AgentInfo, CanvasData, LineInfo, WorkRoot } from "../types";
import { TerminalPane, type TerminalHandle } from "../components/TerminalPane";
import { AgentBar } from "../components/AgentBar";
import { NextActionStrip } from "../components/NextActionStrip";
import { viewForLine } from "../views/registry";

export function Operation(props: {
  repoRoot: string;
  line: LineInfo;
  root: WorkRoot;
  onBack: () => void;
}) {
  const { repoRoot, line, root, onBack } = props;
  const [canvas, setCanvas] = useState<CanvasData | null>(null);
  const [ep, setEp] = useState<string>("第1集");
  const [err, setErr] = useState<string>("");
  // bumped (debounced) whenever the work root changes on disk → re-pull data
  const [refreshKey, setRefreshKey] = useState(0);
  const termRef = useRef<TerminalHandle>(null);
  // auto-enter a default AI agent into this work's terminal, once, on first open
  const [agents, setAgents] = useState<AgentInfo[] | null>(null);
  const [termReady, setTermReady] = useState(false);
  const autoEnteredRef = useRef(false);

  useEffect(() => {
    detectAgents()
      .then(setAgents)
      .catch(() => setAgents([]));
  }, []);

  // fire once both the terminal PTY is live and agent detection has answered
  useEffect(() => {
    if (autoEnteredRef.current || !termReady || !agents) return;
    const def = pickDefaultAgent(agents);
    if (def) {
      autoEnteredRef.current = true;
      termRef.current?.runCommand(def.command);
    }
  }, [termReady, agents]);

  // load canvas data for the current episode (also re-runs on fs change)
  useEffect(() => {
    let alive = true;
    readCanvas(root.path, ep)
      .then((d) => {
        if (!alive) return;
        setCanvas(d);
        if (d.episodes.length && !d.episodes.includes(ep)) setEp(d.episodes[0]);
      })
      .catch((e) => alive && setErr(String(e)));
    return () => {
      alive = false;
    };
  }, [root.path, ep, refreshKey]);

  // watch the work root; debounce a stream of fs events into one refresh
  const timer = useRef<number | null>(null);
  useEffect(() => {
    watchRoot(root.path).catch(() => {});
    let unlisten: (() => void) | null = null;
    listen<{ root: string }>("fs-changed", (e) => {
      if (e.payload.root !== root.path) return;
      if (timer.current) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setRefreshKey((k) => k + 1), 400);
    }).then((fn) => (unlisten = fn));
    return () => {
      unlisten?.();
      if (timer.current) window.clearTimeout(timer.current);
      unwatchRoot(root.path).catch(() => {});
    };
  }, [root.path]);

  const episodes = canvas?.episodes ?? [];
  const View = viewForLine(line.view);

  return (
    <div className="op">
      <div className="op-top">
        <button onClick={onBack}>← 系列</button>
        <div className="crumb">
          {line.label} / <b>{root.name}</b>
        </div>
        {episodes.length > 0 && (
          <div className="ep-switch">
            {episodes.map((e) => (
              <span key={e} className={"ep" + (e === ep ? " active" : "")} onClick={() => setEp(e)}>
                {e}
              </span>
            ))}
          </div>
        )}
        {canvas?.source === "storyboard" && (
          <span className="reason" style={{ color: "var(--warn)" }}>
            （未出图：画布读自 storyboard.json）
          </span>
        )}
      </div>

      <div className="op-body">
        <div className="op-left">
          {err ? <div className="stub-view">读取失败：{err}</div> : <View canvas={canvas} root={root} ep={ep} />}
        </div>
        <div className="op-right">
          <NextActionStrip repoRoot={repoRoot} root={root.path} ep={ep} refreshKey={refreshKey} />
          <AgentBar onEnter={(cmd) => termRef.current?.runCommand(cmd)} />
          <TerminalPane ref={termRef} cwd={root.path} onReady={() => setTermReady(true)} />
        </div>
      </div>
    </div>
  );
}
