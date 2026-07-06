import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import {
  detectAgents,
  pickDefaultAgent,
  readCanvas,
  ensureMedia,
  mediaAllowRoot,
  unwatchRoot,
  watchRoot,
  workChangeSummary,
  workIsEmpty as checkWorkIsEmpty,
  workSnapshot,
} from "../api";
import type { AgentInfo, CanvasData, LineInfo, WorkChangeSummary, WorkRoot } from "../types";
import { TerminalPane, type AgentRuntimeStatus, type TerminalHandle } from "../components/TerminalPane";
import { AgentBar } from "../components/AgentBar";
import { NextActionStrip } from "../components/NextActionStrip";
import { KanbanPane } from "../components/KanbanPane";
import { EpisodeWorkspacePane } from "../components/EpisodeWorkspacePane";
import { SkillsBrowser } from "../components/SkillsBrowser";
import { useI18n, useLineLabel } from "../i18n";

const FilesPane = lazy(() =>
  import("../components/FilesPane").then((mod) => ({ default: mod.FilesPane })),
);

const ChangesPane = lazy(() =>
  import("../components/ChangesPane").then((mod) => ({ default: mod.ChangesPane })),
);

const CanvasPane = lazy(() =>
  import("../components/CanvasPane").then((mod) => ({ default: mod.CanvasPane })),
);

export function Operation(props: {
  repoRoot: string;
  line: LineInfo;
  root: WorkRoot;
  active: boolean;
  onRootChanged: (root: WorkRoot) => void;
  onBack: () => void;
}) {
  const { repoRoot, line, root, active, onRootChanged, onBack } = props;
  const { t } = useI18n();
  const lineLabel = useLineLabel();
  const [canvas, setCanvas] = useState<CanvasData | null>(null);
  const [ep, setEp] = useState<string>("第1集");
  const [err, setErr] = useState<string>("");
  // left-pane sub-tabs: 文件 (default, every line) + 画布 / 看板 (canvas lines: n2d/ad/mv)
  const isCanvasLine = line.view === "canvas";
  const [tab, setTab] = useState<"files" | "skills" | "changes" | "canvas" | "kanban" | "review">("files");
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  // both 画布 and 看板 are per-episode views driven by canvas data
  const isBoardTab = tab === "canvas" || tab === "kanban" || tab === "review";
  // bumped (debounced) whenever the work root changes on disk → re-pull data
  const [refreshKey, setRefreshKey] = useState(0);
  const [changeScanKey, setChangeScanKey] = useState(0);
  const [baselineVersion, setBaselineVersion] = useState(0);
  const termRef = useRef<TerminalHandle>(null);
  const changeSummaryEpochRef = useRef(0);
  // default agent is started lazily only when the user executes a prompt
  const [agents, setAgents] = useState<AgentInfo[] | null>(null);
  const [termReady, setTermReady] = useState(false);
  const [secondaryReady, setSecondaryReady] = useState(false);
  const [activeAgent, setActiveAgent] = useState<AgentInfo | null>(null);
  const activeAgentRef = useRef<AgentInfo | null>(null);
  const [agentRuntimeStatus, setAgentRuntimeStatus] = useState<AgentRuntimeStatus>({});
  const [terminalMode, setTerminalMode] = useState<"native" | "agent">("native");
  const [toast, setToast] = useState<{ id: number; message: string } | null>(null);
  const [workIsEmpty, setWorkIsEmpty] = useState(false);
  const [changeSummary, setChangeSummary] = useState<WorkChangeSummary | null>(null);
  const toastSeq = useRef(0);
  const toastTimer = useRef<number | null>(null);
  const autoEnteredAgentRootRef = useRef<string | null>(null);
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

  function openLeft(nextTab: "files" | "skills" | "changes" | "canvas" | "kanban" | "review") {
    setTab(nextTab);
    setLeftCollapsed(false);
  }

  const probeAgents = useCallback((force = false) => {
    setAgents(null);
    detectAgents(force)
      .then(setAgents)
      .catch(() => setAgents([]));
  }, []);

  function enterNativeTerminal(command?: string) {
    activeAgentRef.current = null;
    setActiveAgent(null);
    setAgentRuntimeStatus({});
    setTerminalMode("native");
    termRef.current?.switchCommand(command ?? "");
    showToast(command ? t("operation.nativeOpenedWithCd") : t("operation.nativeEntered"));
  }

  function runPromptInAgent(prompt: string) {
    const nudgeRefresh = () => {
      setRefreshKey((k) => k + 1);
      setChangeScanKey((k) => k + 1);
    };
    const current = activeAgentRef.current;
    if (current) {
      termRef.current?.runCommand(prompt);
      showToast(t("operation.sentToAgent", { name: current.name }));
      nudgeRefresh();
      window.setTimeout(nudgeRefresh, 3000);
      return;
    }

    const def = pickDefaultAgent(agents ?? []);
    if (def) {
      activeAgentRef.current = def;
      setActiveAgent(def);
      setAgentRuntimeStatus({});
      setTerminalMode("agent");
      termRef.current?.switchCommand(def.command);
      window.setTimeout(() => termRef.current?.runCommand(prompt), 700);
      showToast(t("operation.startedAgentAndSent", { name: def.name }));
      nudgeRefresh();
      window.setTimeout(nudgeRefresh, 3800);
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
    setSecondaryReady(false);
    if (!active) return;
    const timer = window.setTimeout(() => setSecondaryReady(true), termReady ? 450 : 2400);
    return () => window.clearTimeout(timer);
  }, [active, termReady, root.path]);

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
    if (!active || !secondaryReady) return;
    probeAgents(false);
  }, [active, secondaryReady, probeAgents]);

  useEffect(() => {
    if (!active || !secondaryReady || !termReady || agents === null) return;
    if (autoEnteredAgentRootRef.current === root.path) return;
    if (activeAgentRef.current || terminalMode !== "native") {
      autoEnteredAgentRootRef.current = root.path;
      return;
    }
    const def = pickDefaultAgent(agents);
    if (!def) return;
    autoEnteredAgentRootRef.current = root.path;
    activeAgentRef.current = def;
    setActiveAgent(def);
    setAgentRuntimeStatus({});
    setTerminalMode("agent");
    termRef.current?.switchCommand(def.command);
  }, [active, secondaryReady, termReady, agents, root.path, terminalMode]);

  useEffect(() => {
    let alive = true;
    if (!active || !secondaryReady || line.line !== "n2d") {
      setWorkIsEmpty(false);
      return;
    }
    checkWorkIsEmpty(root.path)
      .then((empty) => alive && setWorkIsEmpty(empty))
      .catch(() => alive && setWorkIsEmpty(false));
    return () => {
      alive = false;
    };
  }, [active, secondaryReady, line.line, root.path, refreshKey]);

  useEffect(() => {
    setChangeSummary(null);
  }, [root.path]);

  useEffect(() => {
    if (!active) return;
    let alive = true;
    const epoch = ++changeSummaryEpochRef.current;
    workChangeSummary(root.path)
      .then((summary) => {
        if (alive && epoch === changeSummaryEpochRef.current) setChangeSummary(summary);
      })
      .catch(() => {
        if (alive && epoch === changeSummaryEpochRef.current) setChangeSummary({ changed: 0, deleted: 0 });
      });
    return () => {
      alive = false;
    };
  }, [active, root.path, changeScanKey, baselineVersion]);

  // load canvas data for the current episode (also re-runs on fs change)
  useEffect(() => {
    let alive = true;
    if (!active || !secondaryReady || leftCollapsed || !isCanvasLine || !isBoardTab) return;
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
  }, [active, secondaryReady, leftCollapsed, isCanvasLine, isBoardTab, root.path, ep, refreshKey]);

  useEffect(() => {
    if (!active || !secondaryReady || !isCanvasLine || !isBoardTab) return;
    ensureMedia()
      .then(() => mediaAllowRoot(root.path))
      .catch(() => {});
  }, [active, secondaryReady, isCanvasLine, isBoardTab, root.path]);

  // watch the work root; debounce a stream of fs events into one refresh
  const timer = useRef<number | null>(null);
  const lastSnapshotRef = useRef<string | null>(null);
  useEffect(() => {
    if (!active) return;
    watchRoot(root.path).catch(() => {});
    let unlisten: (() => void) | null = null;
    listen<{ root: string }>("fs-changed", (e) => {
      if (e.payload.root !== root.path) return;
      if (timer.current) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => {
        setRefreshKey((k) => k + 1);
        setChangeScanKey((k) => k + 1);
      }, 400);
    }).then((fn) => (unlisten = fn));
    return () => {
      unlisten?.();
      if (timer.current) window.clearTimeout(timer.current);
      unwatchRoot(root.path).catch(() => {});
    };
  }, [active, root.path]);

  // Polling fallback for long-running skills/agents. Native fs events are fast
  // when available, but some generator CLIs write via atomic replace, temp dirs,
  // or external processes that can be missed on a few platforms. This keeps the
  // file tree, canvas, kanban, and next-action strip converging automatically.
  useEffect(() => {
    if (!active) return;
    let alive = true;
    let inFlight = false;
    let initialTimer: number | null = null;
    lastSnapshotRef.current = null;

    const tick = async () => {
      if (document.hidden) return;
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
          setChangeScanKey((k) => k + 1);
        }
      } catch {
        // Watcher remains the primary path; polling is best-effort.
      } finally {
        inFlight = false;
      }
    };
    const tickWhenVisible = () => {
      if (!document.hidden) tick();
    };

    initialTimer = window.setTimeout(tick, 250);
    const interval = window.setInterval(tick, 15000);
    document.addEventListener("visibilitychange", tickWhenVisible);
    return () => {
      alive = false;
      if (initialTimer != null) window.clearTimeout(initialTimer);
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", tickWhenVisible);
    };
  }, [active, secondaryReady, root.path]);

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
  const missingProgressPrompt = useMemo(
    () =>
      line.line === "n2d" && !workIsEmpty
        ? {
            prompt: t("operation.n2dBootstrapPrompt", { path: root.path }),
          }
        : null,
    [line.line, root.path, t, workIsEmpty],
  );
  const changeCount = (changeSummary?.changed ?? 0) + (changeSummary?.deleted ?? 0);
  const changeLabel =
    changeSummary == null
      ? t("operation.leftDeferred")
      : changeCount
        ? t("files.changeCount", { count: changeCount })
        : t("files.noChanges");
  const hasDetectedAgent = (agents ?? []).some((agent) => agent.found);
  const terminalPlaceholder =
    terminalMode === "native" && agents !== null && !hasDetectedAgent
      ? t("terminal.noAgentPlaceholder")
      : undefined;

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
            <select
              className="ep-select"
              value={episodes.includes(ep) ? ep : episodes[0]}
              aria-label={t("operation.episodeSelect")}
              title={t("operation.episodeSelect")}
              onChange={(event) => setEp(event.target.value)}
            >
              {episodes.map((e) => (
                <option key={e} value={e}>
                  {e}
                </option>
              ))}
            </select>
          </div>
        )}
        {isCanvasLine && isBoardTab && canvas?.source === "storyboard" && (
          <span className="reason" style={{ color: "var(--warn)" }}>
            {t("operation.storyboardSource")}
          </span>
        )}
      </div>

      <div className={"op-body" + (leftCollapsed ? " op-body-left-collapsed" : "")} ref={bodyRef}>
        <div className={"op-left" + (leftCollapsed ? " collapsed" : "")}>
          <div className="op-left-rail" aria-label={t("operation.leftDeferred")}>
            <button
              type="button"
              className={"rail-tab" + (tab === "files" ? " active" : "")}
              title={t("operation.filesTab")}
              aria-label={t("operation.filesTab")}
              onClick={() => openLeft("files")}
            >
              📁
            </button>
            <button
              type="button"
              className={"rail-tab rail-skills" + (tab === "skills" ? " active" : "")}
              title={t("operation.skillsTab")}
              aria-label={t("operation.skillsTab")}
              onClick={() => openLeft("skills")}
            >
              <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
                <path d="M3.2 4.4 8 2l4.8 2.4L8 6.8 3.2 4.4Z" />
                <path d="M3.2 8 8 5.6 12.8 8 8 10.4 3.2 8Z" />
                <path d="M3.2 11.6 8 9.2l4.8 2.4L8 14 3.2 11.6Z" />
              </svg>
            </button>
            {isCanvasLine && (
              <button
                type="button"
                className={"rail-tab" + (tab === "canvas" ? " active" : "")}
                title={t("operation.canvasTab")}
                aria-label={t("operation.canvasTab")}
                onClick={() => openLeft("canvas")}
              >
                🎬
              </button>
            )}
            {isCanvasLine && (
              <button
                type="button"
                className={"rail-tab" + (tab === "kanban" ? " active" : "")}
                title={t("operation.boardTab")}
                aria-label={t("operation.boardTab")}
                onClick={() => openLeft("kanban")}
              >
                📋
              </button>
            )}
            {isCanvasLine && (
              <button
                type="button"
                className={"rail-tab" + (tab === "review" ? " active" : "")}
                title={t("operation.reviewTab")}
                aria-label={t("operation.reviewTab")}
                onClick={() => openLeft("review")}
              >
                ⚠
              </button>
            )}
            <button
              type="button"
              className={"rail-tab rail-change" + (tab === "changes" ? " active" : "") + (changeCount ? " dirty" : "")}
              title={`${t("operation.changesTab")} · ${changeLabel}`}
              aria-label={`${t("operation.changesTab")} · ${changeLabel}`}
              onClick={() => openLeft("changes")}
            >
              <span className="rail-change-icon" aria-hidden="true">
                <svg viewBox="0 0 16 16" focusable="false">
                  <path d="M4.5 2.5h7" />
                  <path d="M4.5 8h7" />
                  <path d="M4.5 13.5h7" />
                  <path d="M2.5 4.5v-2h2" />
                  <path d="M13.5 6v2h-2" />
                  <path d="M2.5 11.5v2h2" />
                </svg>
              </span>
              {changeSummary == null ? (
                <span className="rail-badge loading">…</span>
              ) : changeCount > 0 ? (
                <span className="rail-badge">{changeCount > 99 ? "99+" : changeCount}</span>
              ) : null}
            </button>
            <button
              type="button"
              className="rail-tab rail-toggle"
              title={t("operation.collapseLeft")}
              aria-label={t("operation.collapseLeft")}
              onClick={() => setLeftCollapsed((value) => !value)}
            >
              {leftCollapsed ? "›" : "‹"}
            </button>
          </div>
          {!leftCollapsed && (
            <div className="op-left-content">
              <div className="subtab-body">
                {!secondaryReady ? (
                  <div className="stub-view">{t("common.loading")}</div>
                ) : tab === "changes" ? (
                  <Suspense fallback={<div className="stub-view">{t("common.loading")}</div>}>
                    <ChangesPane
                      root={root}
                      refreshKey={changeScanKey}
                      baselineVersion={baselineVersion}
                      summary={changeSummary}
                      onArchived={(summary) => {
                        changeSummaryEpochRef.current += 1;
                        setChangeSummary(summary);
                        setBaselineVersion((version) => version + 1);
                        setChangeScanKey((key) => key + 1);
                      }}
                    />
                  </Suspense>
                ) : tab === "skills" ? (
                  <SkillsBrowser repoRoot={repoRoot} line={line} />
                ) : isCanvasLine && isBoardTab ? (
                  err ? (
                    <div className="stub-view">{t("common.readFailed", { error: err })}</div>
                  ) : !canvas ? (
                    <div className="stub-view">{t("common.loading")}</div>
                  ) : tab === "review" ? (
                    <EpisodeWorkspacePane root={root} ep={ep} canvas={canvas} refreshKey={refreshKey} />
                  ) : tab === "kanban" ? (
                    <KanbanPane canvas={canvas} root={root} ep={ep} refreshKey={refreshKey} />
                  ) : (
                    <Suspense fallback={<div className="stub-view">{t("common.loading")}</div>}>
                      <CanvasPane canvas={canvas} root={root} ep={ep} refreshKey={refreshKey} />
                    </Suspense>
                  )
                ) : (
                  <Suspense fallback={<div className="stub-view">{t("common.loading")}</div>}>
                    <FilesPane
                      root={root}
                      refreshKey={refreshKey + baselineVersion}
                      initialChangeCount={changeSummary == null ? undefined : changeCount}
                      allowNovelImport={line.line === "n2d" && workIsEmpty}
                      active={active}
                      onImported={(result) => {
                        if (result.root !== root.path || result.name !== root.name) {
                          onRootChanged({
                            name: result.name,
                            path: result.root,
                            has_progress: false,
                            is_demo: root.is_demo,
                          });
                        }
                        setRefreshKey((key) => key + 1);
                        setChangeScanKey((key) => key + 1);
                      }}
                      onOpenTerminal={enterNativeTerminal}
                    />
                  </Suspense>
                )}
              </div>
            </div>
          )}
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
            line={line.line}
            root={root.path}
            ep={ep}
            refreshKey={refreshKey + baselineVersion}
            enabled={active && secondaryReady}
            manualPrompt={emptyN2dPrompt}
            manualPromptExecutable={false}
            missingProgressPrompt={missingProgressPrompt}
            onExecutePrompt={runPromptInAgent}
          />
          <AgentBar
            agents={agents}
            probeEnabled={active && secondaryReady}
            activeAgentId={activeAgent?.id}
            nativeActive={terminalMode === "native"}
            runtimeStatus={agentRuntimeStatus}
            onNativeTerminal={() => enterNativeTerminal()}
            onRefresh={probeAgents}
            onEnter={(agent) => {
              if (activeAgentRef.current?.id === agent.id) {
                showToast(t("operation.agentAlreadyActive", { name: agent.name }));
                return;
              }
              activeAgentRef.current = agent;
              setActiveAgent(agent);
              setAgentRuntimeStatus({});
              setTerminalMode("agent");
              termRef.current?.switchCommand(agent.command);
            }}
          />
          <TerminalPane
            ref={termRef}
            cwd={root.path}
            onReady={() => setTermReady(true)}
            placeholder={terminalPlaceholder}
            onRuntimeStatus={setAgentRuntimeStatus}
            onPermissionNotice={(notice) => showToast(t("operation.agentPermissionNotice", { notice }))}
          />
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
