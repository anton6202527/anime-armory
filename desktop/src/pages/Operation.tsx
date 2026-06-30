import { useEffect, useMemo, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { detectAgents, pickDefaultAgent, readCanvas, unwatchRoot, watchRoot, workSnapshot, workTree } from "../api";
import type { AgentInfo, CanvasData, LineInfo, WorkRoot } from "../types";
import { TerminalPane, type TerminalHandle } from "../components/TerminalPane";
import { AgentBar } from "../components/AgentBar";
import { NextActionStrip } from "../components/NextActionStrip";
import { CanvasPane } from "../components/CanvasPane";
import { KanbanPane } from "../components/KanbanPane";
import { FilesPane } from "../components/FilesPane";
import { useI18n, useLineLabel } from "../i18n";

export function Operation(props: {
  repoRoot: string;
  line: LineInfo;
  root: WorkRoot;
  onBack: () => void;
}) {
  const { repoRoot, line, root, onBack } = props;
  const { t } = useI18n();
  const lineLabel = useLineLabel();
  const [canvas, setCanvas] = useState<CanvasData | null>(null);
  const [ep, setEp] = useState<string>("第1集");
  const [err, setErr] = useState<string>("");
  // left-pane sub-tabs: 文件 (default, every line) + 画布 / 看板 (canvas lines: n2d/ad/mv)
  const isCanvasLine = line.view === "canvas";
  const [tab, setTab] = useState<"files" | "canvas" | "kanban">("files");
  // both 画布 and 看板 are per-episode views driven by canvas data
  const isBoardTab = tab === "canvas" || tab === "kanban";
  // bumped (debounced) whenever the work root changes on disk → re-pull data
  const [refreshKey, setRefreshKey] = useState(0);
  const termRef = useRef<TerminalHandle>(null);
  // auto-enter a default AI agent into this work's terminal, once, on first open
  const [agents, setAgents] = useState<AgentInfo[] | null>(null);
  const [termReady, setTermReady] = useState(false);
  const autoEnteredRef = useRef(false);
  const [activeAgent, setActiveAgent] = useState<AgentInfo | null>(null);
  const activeAgentRef = useRef<AgentInfo | null>(null);
  const [terminalMode, setTerminalMode] = useState<"native" | "agent" | "install">("native");
  const [toast, setToast] = useState<{ id: number; message: string } | null>(null);
  const [workIsEmpty, setWorkIsEmpty] = useState(false);
  const toastSeq = useRef(0);
  const toastTimer = useRef<number | null>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const [rightWidth, setRightWidth] = useState<number | null>(() => {
    const saved = Number(window.localStorage.getItem("aa.op.rightWidth"));
    return Number.isFinite(saved) && saved > 0 ? saved : null;
  });

  function clampRightWidth(width: number, total: number): number {
    const minRight = 320;
    const minLeft = Math.min(420, Math.max(260, total * 0.35));
    const maxRight = Math.max(minRight, total - minLeft);
    return Math.min(maxRight, Math.max(minRight, width));
  }

  function showToast(message: string) {
    if (toastTimer.current) window.clearTimeout(toastTimer.current);
    setToast({ id: ++toastSeq.current, message });
    toastTimer.current = window.setTimeout(() => setToast(null), 1600);
  }

  function enterNativeTerminal(command?: string) {
    autoEnteredRef.current = true;
    activeAgentRef.current = null;
    setActiveAgent(null);
    setTerminalMode("native");
    termRef.current?.switchCommand(command ?? "");
    showToast(command ? t("operation.nativeOpenedWithCd") : t("operation.nativeEntered"));
  }

  function runPromptInAgent(prompt: string) {
    const current = activeAgentRef.current;
    if (current) {
      termRef.current?.runCommand(prompt);
      showToast(t("operation.sentToAgent", { name: current.name }));
      return;
    }

    const def = pickDefaultAgent(agents ?? []);
    if (def) {
      autoEnteredRef.current = true;
      activeAgentRef.current = def;
      setActiveAgent(def);
      setTerminalMode("agent");
      termRef.current?.switchCommand(def.command);
      window.setTimeout(() => termRef.current?.runCommand(prompt), 700);
      showToast(t("operation.startedAgentAndSent", { name: def.name }));
      return;
    }

    termRef.current?.focus();
    showToast(t("operation.noAgent"));
  }

  useEffect(() => {
    return () => {
      if (toastTimer.current) window.clearTimeout(toastTimer.current);
    };
  }, []);

  useEffect(() => {
    if (rightWidth == null) return;
    const sync = () => {
      const body = bodyRef.current;
      if (!body) return;
      const rect = body.getBoundingClientRect();
      const next = clampRightWidth(rightWidth, rect.width);
      if (Math.round(next) !== Math.round(rightWidth)) setRightWidth(next);
    };
    sync();
    window.addEventListener("resize", sync);
    return () => window.removeEventListener("resize", sync);
  }, [rightWidth]);

  useEffect(() => {
    detectAgents()
      .then(setAgents)
      .catch(() => setAgents([]));
  }, []);

  useEffect(() => {
    let alive = true;
    if (line.line !== "n2d") {
      setWorkIsEmpty(false);
      return;
    }
    workTree(root.path)
      .then((tree) => alive && setWorkIsEmpty(tree.length === 0))
      .catch(() => alive && setWorkIsEmpty(false));
    return () => {
      alive = false;
    };
  }, [line.line, root.path, refreshKey]);

  // fire once both the terminal PTY is live and agent detection has answered
  useEffect(() => {
    if (autoEnteredRef.current || !termReady || !agents) return;
    const def = pickDefaultAgent(agents);
    if (def) {
      autoEnteredRef.current = true;
      activeAgentRef.current = def;
      setActiveAgent(def);
      setTerminalMode("agent");
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
  const lastSnapshotRef = useRef<string | null>(null);
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

  // Polling fallback for long-running skills/agents. Native fs events are fast
  // when available, but some generator CLIs write via atomic replace, temp dirs,
  // or external processes that can be missed on a few platforms. This keeps the
  // file tree, canvas, kanban, and next-action strip converging automatically.
  useEffect(() => {
    let alive = true;
    let inFlight = false;
    lastSnapshotRef.current = null;

    const tick = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const snap = await workSnapshot(root.path);
        if (!alive) return;
        const sig = `${snap.signature}:${snap.file_count}:${snap.dir_count}`;
        if (lastSnapshotRef.current == null) {
          lastSnapshotRef.current = sig;
          return;
        }
        if (sig !== lastSnapshotRef.current) {
          lastSnapshotRef.current = sig;
          setRefreshKey((k) => k + 1);
        }
      } catch {
        // Watcher remains the primary path; polling is best-effort.
      } finally {
        inFlight = false;
      }
    };

    tick();
    const interval = window.setInterval(tick, 4000);
    return () => {
      alive = false;
      window.clearInterval(interval);
    };
  }, [root.path]);

  const episodes = canvas?.episodes ?? [];
  const emptyN2dPrompt = useMemo(
    () =>
      workIsEmpty
        ? {
            headline: t("operation.emptyN2dHeadline"),
            prompt:
              t("operation.emptyN2dPrompt", { path: root.path }),
          }
        : null,
    [root.path, t, workIsEmpty],
  );

  function startTerminalResize(ev: React.PointerEvent<HTMLDivElement>) {
    const body = bodyRef.current;
    if (!body) return;
    ev.preventDefault();
    const rect = body.getBoundingClientRect();
    document.body.classList.add("resizing-op-terminal");

    const move = (e: PointerEvent) => {
      const next = clampRightWidth(rect.right - e.clientX, rect.width);
      setRightWidth(next);
      window.localStorage.setItem("aa.op.rightWidth", String(Math.round(next)));
      window.dispatchEvent(new Event("resize"));
    };
    const up = () => {
      document.body.classList.remove("resizing-op-terminal");
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", up);
      window.dispatchEvent(new Event("resize"));
    };
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", up);
  }

  return (
    <div className="op">
      <div className="op-top">
        <button onClick={onBack}>{t("operation.backSeries")}</button>
        <div className="crumb">
          {lineLabel(line)} / <b>{root.name}</b>
        </div>
        {isCanvasLine && isBoardTab && episodes.length > 0 && (
          <div className="ep-switch">
            {episodes.map((e) => (
              <span key={e} className={"ep" + (e === ep ? " active" : "")} onClick={() => setEp(e)}>
                {e}
              </span>
            ))}
          </div>
        )}
        {isCanvasLine && isBoardTab && canvas?.source === "storyboard" && (
          <span className="reason" style={{ color: "var(--warn)" }}>
            {t("operation.storyboardSource")}
          </span>
        )}
      </div>

      <div className="op-body" ref={bodyRef}>
        <div className="op-left">
          <div className="subtabs">
            <span
              className={"subtab" + (tab === "files" ? " active" : "")}
              onClick={() => setTab("files")}
            >
              {t("operation.filesTab")}
            </span>
            {isCanvasLine && (
              <span
                className={"subtab" + (tab === "canvas" ? " active" : "")}
                onClick={() => setTab("canvas")}
              >
                {t("operation.canvasTab")}
              </span>
            )}
            {isCanvasLine && (
              <span
                className={"subtab" + (tab === "kanban" ? " active" : "")}
                onClick={() => setTab("kanban")}
              >
                {t("operation.boardTab")}
              </span>
            )}
          </div>
          <div className="subtab-body">
            {isCanvasLine && isBoardTab ? (
              err ? (
                <div className="stub-view">{t("common.readFailed", { error: err })}</div>
              ) : tab === "kanban" ? (
                <KanbanPane canvas={canvas} root={root} ep={ep} refreshKey={refreshKey} />
              ) : (
                <CanvasPane canvas={canvas} root={root} ep={ep} refreshKey={refreshKey} />
              )
            ) : (
              <FilesPane root={root} refreshKey={refreshKey} onOpenTerminal={enterNativeTerminal} />
            )}
          </div>
        </div>
        <div
          className="op-splitter"
          role="separator"
          aria-orientation="vertical"
          aria-label={t("operation.resizeTerminalAria")}
          title={t("operation.resizeTerminalTitle")}
          onPointerDown={startTerminalResize}
          onDoubleClick={() => {
            setRightWidth(null);
            window.localStorage.removeItem("aa.op.rightWidth");
            window.dispatchEvent(new Event("resize"));
          }}
        />
        <div className="op-right" style={rightWidth ? { width: rightWidth } : undefined}>
          <NextActionStrip
            repoRoot={repoRoot}
            root={root.path}
            ep={ep}
            refreshKey={refreshKey}
            manualPrompt={emptyN2dPrompt}
            onExecutePrompt={runPromptInAgent}
          />
          <AgentBar
            activeAgentId={activeAgent?.id}
            nativeActive={terminalMode === "native"}
            onNativeTerminal={() => enterNativeTerminal()}
            onEnter={(agent) => {
              if (!agent.found && agent.install_command) {
                autoEnteredRef.current = true;
                activeAgentRef.current = null;
                setActiveAgent(null);
                setTerminalMode("install");
                showToast(t("operation.installingAgent", { name: agent.name }));
                termRef.current?.switchCommand(agent.install_command);
                return;
              }
              if (activeAgentRef.current?.id === agent.id) {
                showToast(t("operation.agentAlreadyActive", { name: agent.name }));
                return;
              }
              autoEnteredRef.current = true;
              activeAgentRef.current = agent;
              setActiveAgent(agent);
              setTerminalMode("agent");
              termRef.current?.switchCommand(agent.command);
            }}
          />
          <TerminalPane ref={termRef} cwd={root.path} onReady={() => setTermReady(true)} />
        </div>
      </div>
      {toast && (
        <div key={toast.id} className="op-toast" role="status" aria-live="polite">
          {toast.message}
        </div>
      )}
    </div>
  );
}
