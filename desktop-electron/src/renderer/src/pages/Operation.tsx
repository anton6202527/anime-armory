import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { onAppEvent } from "../platform/bridge";
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
import { TerminalPane, type TerminalHandle } from "../components/TerminalPane";
import { NextActionStrip } from "../components/NextActionStrip";
import { Codicon } from "../components/Codicon";
import { BreadcrumbHomeIcon } from "../components/BreadcrumbHomeIcon";
import { RailIcon } from "../components/RailIcon";
import { plainLineLabel, useI18n, useLineLabel } from "../i18n";
import {
  COLLAPSE_LEFT_SIDEBAR_EVENT,
  FILES_SIDE_COLLAPSE_WIDTH,
  FILES_SIDE_WIDTH_CHANGED_EVENT,
  clampFilesSideWidth,
  commitFilesSideWidth,
  draftFilesSideWidth,
  readCurrentFilesSideWidth,
  readStoredFilesSideWidth,
} from "../paneLayout";

const FilesPane = lazy(() =>
  import("../components/FilesPane").then((mod) => ({ default: mod.FilesPane })),
);

const ChangesPane = lazy(() =>
  import("../components/ChangesPane").then((mod) => ({ default: mod.ChangesPane })),
);

const CanvasPane = lazy(() =>
  import("../components/CanvasPane").then((mod) => ({ default: mod.CanvasPane })),
);

const SearchPane = lazy(() =>
  import("../components/SearchPane").then((mod) => ({ default: mod.SearchPane })),
);

const EpisodeWorkspacePane = lazy(() =>
  import("../components/EpisodeWorkspacePane").then((mod) => ({ default: mod.EpisodeWorkspacePane })),
);

const QualityInsightsPane = lazy(() =>
  import("../components/QualityInsightsPane").then((mod) => ({ default: mod.QualityInsightsPane })),
);

const OP_RIGHT_MIN_WIDTH = 72;
const OP_RIGHT_MAX_WIDTH = 340;
const OP_BOTTOM_MIN_HEIGHT = 82;
const OP_BOTTOM_MAX_HEIGHT = 440;
const OP_LEFT_RAIL_WIDTH = 44;
const TERMINAL_SIDE_COLLAPSE_WIDTH = OP_RIGHT_MIN_WIDTH;
const TERMINAL_BOTTOM_COLLAPSE_HEIGHT = OP_BOTTOM_MIN_HEIGHT;
type LeftTab = "files" | "search" | "changes" | "canvas" | "review";
type TerminalDock = "side" | "bottom";

function isMacPlatform(): boolean {
  return /Mac|iPhone|iPad|iPod/.test(window.navigator.platform);
}

export function Operation(props: {
  repoRoot: string;
  line: LineInfo;
  root: WorkRoot;
  active: boolean;
  terminalVisible: boolean;
  newTerminalRequestSeq: number;
  newTerminalRequestTargetId: string | null;
  onRootChanged: (root: WorkRoot) => void;
  onCloseTerminal: () => void;
  onToggleTerminal: () => void;
  onShowSkills: (line: LineInfo) => void;
  onHome: () => void;
  onBack: () => void;
}) {
  const {
    repoRoot,
    line,
    root,
    active,
    terminalVisible,
    newTerminalRequestSeq,
    newTerminalRequestTargetId,
    onRootChanged,
    onCloseTerminal,
    onToggleTerminal,
    onShowSkills,
    onHome,
    onBack,
  } = props;
  const { t } = useI18n();
  const lineLabel = useLineLabel();
  const [canvas, setCanvas] = useState<CanvasData | null>(null);
  const [ep, setEp] = useState<string>("第1集");
  const [err, setErr] = useState<string>("");
  // left-pane sub-tabs: 文件/搜索/技能/变动 for every line, plus visual 画布 and all-line 质检.
  const isCanvasLine = line.view === "canvas";
  const [tab, setTab] = useState<LeftTab>("files");
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [sidePanelOpen, setSidePanelOpen] = useState(true);
  // 画布 is a per-episode view driven by canvas data; 质检 is available to every line.
  const shouldReadCanvas = isCanvasLine && (tab === "canvas" || tab === "review");
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
  const activeAgentRef = useRef<AgentInfo | null>(null);
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
    if (!Number.isFinite(saved) || saved <= TERMINAL_SIDE_COLLAPSE_WIDTH) return null;
    return Math.min(OP_RIGHT_MAX_WIDTH, Math.max(OP_RIGHT_MIN_WIDTH, saved));
  });
  const [bottomHeight, setBottomHeight] = useState<number | null>(() => {
    const saved = Number(window.localStorage.getItem("aa.op.bottomHeight"));
    if (!Number.isFinite(saved) || saved <= TERMINAL_BOTTOM_COLLAPSE_HEIGHT) return null;
    return Math.min(OP_BOTTOM_MAX_HEIGHT, Math.max(OP_BOTTOM_MIN_HEIGHT, saved));
  });
  const [filesSideWidth, setFilesSideWidth] = useState(readStoredFilesSideWidth);
  const [terminalDock, setTerminalDock] = useState<TerminalDock>(() => {
    return window.localStorage.getItem("aa.op.terminalDock") === "bottom" ? "bottom" : "side";
  });

  function clampRightWidth(width: number, total: number): number {
    const minLeft = Math.min(420, Math.max(260, total * 0.35));
    const availableMax = Math.max(0, total - minLeft);
    const maxRight = Math.min(OP_RIGHT_MAX_WIDTH, availableMax);
    return Math.min(maxRight, Math.max(OP_RIGHT_MIN_WIDTH, width));
  }

  function clampBottomHeight(height: number, total: number): number {
    const minTop = Math.min(360, Math.max(180, total * 0.35));
    const availableMax = Math.max(0, total - minTop);
    const maxBottom = Math.min(OP_BOTTOM_MAX_HEIGHT, availableMax);
    return Math.min(maxBottom, Math.max(OP_BOTTOM_MIN_HEIGHT, height));
  }

  function showToast(message: string) {
    if (toastTimer.current) window.clearTimeout(toastTimer.current);
    setToast({ id: ++toastSeq.current, message });
    toastTimer.current = window.setTimeout(() => setToast(null), 1600);
  }

  function openLeft(nextTab: LeftTab) {
    if (sidePanelOpen && tab === nextTab) {
      setSidePanelOpen(false);
      return;
    }
    showLeft(nextTab);
  }

  function showLeft(nextTab: LeftTab) {
    setTab(nextTab);
    setSidePanelOpen(true);
    setLeftCollapsed(false);
    setFilesSideWidth(readStoredFilesSideWidth());
  }

  const probeAgents = useCallback((force = false) => {
    setAgents(null);
    detectAgents(force)
      .then(setAgents)
      .catch(() => setAgents([]));
  }, []);

  const handleActiveAgentChange = useCallback((agent: AgentInfo | null) => {
    activeAgentRef.current = agent;
    setTerminalMode(agent ? "agent" : "native");
  }, []);

  function enterNativeTerminal(command?: string) {
    activeAgentRef.current = null;
    setTerminalMode("native");
    termRef.current?.switchCommand(command ?? "", "native");
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
      setTerminalMode("agent");
      termRef.current?.switchCommand(def.command, def.id);
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
    setTermReady(false);
    activeAgentRef.current = null;
    setTerminalMode("native");
    autoEnteredAgentRootRef.current = null;
  }, [root.path]);

  useEffect(() => {
    setSecondaryReady(false);
    if (!active) return;
    const timer = window.setTimeout(() => setSecondaryReady(true), termReady ? 450 : 2400);
    return () => window.clearTimeout(timer);
  }, [active, termReady, root.path]);

  useEffect(() => {
    if (rightWidth == null || terminalDock !== "side") return;
    const sync = () => {
      const body = bodyRef.current;
      if (!body) return;
      const rect = body.getBoundingClientRect();
      const next = clampRightWidth(rightWidth, rect.width);
      if (Math.round(next) !== Math.round(rightWidth)) {
        setRightWidth(next);
        window.localStorage.setItem("aa.op.rightWidth", String(Math.round(next)));
      }
    };
    sync();
    window.addEventListener("resize", sync);
    return () => window.removeEventListener("resize", sync);
  }, [rightWidth, terminalDock]);

  useEffect(() => {
    if (bottomHeight == null || terminalDock !== "bottom") return;
    const sync = () => {
      const body = bodyRef.current;
      if (!body) return;
      const rect = body.getBoundingClientRect();
      const next = clampBottomHeight(bottomHeight, rect.height);
      if (Math.round(next) !== Math.round(bottomHeight)) {
        setBottomHeight(next);
        window.localStorage.setItem("aa.op.bottomHeight", String(Math.round(next)));
      }
    };
    sync();
    window.addEventListener("resize", sync);
    return () => window.removeEventListener("resize", sync);
  }, [bottomHeight, terminalDock]);

  useEffect(() => {
    window.localStorage.setItem("aa.op.terminalDock", terminalDock);
    window.dispatchEvent(new Event("resize"));
    const timer = window.setTimeout(() => window.dispatchEvent(new Event("resize")), 120);
    return () => window.clearTimeout(timer);
  }, [terminalDock]);

  useEffect(() => {
    if (!active || !secondaryReady) return;
    probeAgents(false);
  }, [active, secondaryReady, probeAgents]);

  useEffect(() => {
    if (!terminalVisible) setLeftCollapsed(false);
    window.dispatchEvent(new Event("resize"));
  }, [terminalVisible]);

  useEffect(() => {
    const collapseLeftSidebar = () => {
      setSidePanelOpen(false);
      setLeftCollapsed(false);
    };
    window.addEventListener(COLLAPSE_LEFT_SIDEBAR_EVENT, collapseLeftSidebar);
    return () => window.removeEventListener(COLLAPSE_LEFT_SIDEBAR_EVENT, collapseLeftSidebar);
  }, []);

  useEffect(() => {
    if (
      !active ||
      !terminalVisible ||
      newTerminalRequestSeq <= 0 ||
      newTerminalRequestTargetId !== root.path
    ) {
      return;
    }
    const timer = window.setTimeout(() => termRef.current?.newSession(), 0);
    return () => window.clearTimeout(timer);
  }, [active, terminalVisible, newTerminalRequestSeq, newTerminalRequestTargetId, root.path]);

  useEffect(() => {
    setFilesSideWidth(readStoredFilesSideWidth());
    const syncFilesSideWidth = () => setFilesSideWidth(readCurrentFilesSideWidth());
    window.addEventListener(FILES_SIDE_WIDTH_CHANGED_EVENT, syncFilesSideWidth);
    window.addEventListener("resize", syncFilesSideWidth);
    window.addEventListener("storage", syncFilesSideWidth);
    return () => {
      window.removeEventListener(FILES_SIDE_WIDTH_CHANGED_EVENT, syncFilesSideWidth);
      window.removeEventListener("resize", syncFilesSideWidth);
      window.removeEventListener("storage", syncFilesSideWidth);
    };
  }, []);

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
    setTerminalMode("agent");
    termRef.current?.switchCommand(def.command, def.id);
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
    if (!active || !secondaryReady) return;
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
  }, [active, secondaryReady, root.path, changeScanKey, baselineVersion]);

  // load canvas data for the current episode (also re-runs on fs change)
  useEffect(() => {
    let alive = true;
    if (!active || !secondaryReady || !sidePanelOpen || !shouldReadCanvas) return;
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
  }, [active, secondaryReady, sidePanelOpen, shouldReadCanvas, root.path, ep, refreshKey]);

  useEffect(() => {
    if (!active || !secondaryReady || !shouldReadCanvas) return;
    ensureMedia()
      .then(() => mediaAllowRoot(root.path))
      .catch(() => {});
  }, [active, secondaryReady, shouldReadCanvas, root.path]);

  useEffect(() => {
    if (!active || !secondaryReady) return;
    const onKeyDown = (event: KeyboardEvent) => {
      const key = event.key.toLowerCase();
      const cmd = event.metaKey || event.ctrlKey;
      const target = event.target as HTMLElement | null;
      const tag = target?.tagName.toLowerCase();
      const editingText =
        tag === "input" ||
        tag === "textarea" ||
        tag === "select" ||
        target?.isContentEditable;

      if (cmd && event.shiftKey && key === "e") {
        event.preventDefault();
        showLeft("files");
      } else if (cmd && event.shiftKey && key === "f") {
        event.preventDefault();
        showLeft("search");
      } else if ((cmd || event.ctrlKey) && event.shiftKey && key === "g") {
        event.preventDefault();
        showLeft("changes");
      } else if (cmd && !event.shiftKey && key === "b" && !editingText) {
        event.preventDefault();
        setLeftCollapsed((collapsed) => !collapsed);
        setSidePanelOpen((open) => (leftCollapsed ? true : open));
      } else if (cmd && !event.shiftKey && key === "j" && !editingText) {
        event.preventDefault();
        onToggleTerminal();
      } else if (event.ctrlKey && !event.metaKey && !event.shiftKey && event.key === "`") {
        event.preventDefault();
        if (!terminalVisible) onToggleTerminal();
        window.setTimeout(() => termRef.current?.focus(), 100);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [active, leftCollapsed, onToggleTerminal, terminalVisible]);

  // watch the work root; debounce a stream of fs events into one refresh
  const timer = useRef<number | null>(null);
  const lastSnapshotRef = useRef<string | null>(null);
  useEffect(() => {
    if (!active) return;
    watchRoot(root.path).catch(() => {});
    const unlisten = onAppEvent("fs-changed", (payload) => {
      if (payload.root !== root.path) return;
      if (timer.current) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => {
        setRefreshKey((k) => k + 1);
        setChangeScanKey((k) => k + 1);
      }, 400);
    });
    return () => {
      unlisten();
      if (timer.current) window.clearTimeout(timer.current);
      unwatchRoot(root.path).catch(() => {});
    };
  }, [active, root.path]);

  // Polling fallback for long-running skills/agents. Native fs events are fast
  // when available, but some generator CLIs write via atomic replace, temp dirs,
  // or external processes that can be missed on a few platforms. This keeps the
  // file tree, canvas, and next-action strip converging automatically.
  useEffect(() => {
    if (!active || !secondaryReady) return;
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
  const canvasSourceHint =
    canvas?.source === "storyboard"
      ? t("operation.storyboardSource")
      : canvas?.source === "panel_script"
        ? t("operation.panelScriptSource")
        : "";

  function startTerminalResize(ev: ReactPointerEvent<HTMLDivElement>) {
    const body = bodyRef.current;
    if (!body) return;
    ev.preventDefault();
    const splitter = ev.currentTarget;
    const rect = body.getBoundingClientRect();
    const resizingClass = terminalDock === "bottom" ? "resizing-op-terminal-bottom" : "resizing-op-terminal-side";
    document.body.classList.add(resizingClass);
    splitter.classList.add("resizing");
    let latestSize = terminalDock === "bottom"
      ? (bottomHeight ?? rect.height * 0.34)
      : (rightWidth ?? Math.min(OP_RIGHT_MAX_WIDTH, rect.width * 0.42));

    const move = (e: PointerEvent) => {
      if (terminalDock === "bottom") {
        const next = clampBottomHeight(rect.bottom - e.clientY, rect.height);
        latestSize = next;
        setBottomHeight(next);
        window.localStorage.setItem("aa.op.bottomHeight", String(Math.round(next)));
      } else {
        const next = clampRightWidth(rect.right - e.clientX, rect.width);
        latestSize = next;
        setRightWidth(next);
        window.localStorage.setItem("aa.op.rightWidth", String(Math.round(next)));
      }
      window.dispatchEvent(new Event("resize"));
    };
    const up = () => {
      document.body.classList.remove(resizingClass);
      splitter.classList.remove("resizing");
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", up);
      if (terminalDock === "bottom" && latestSize <= TERMINAL_BOTTOM_COLLAPSE_HEIGHT) {
        setBottomHeight(null);
        window.localStorage.removeItem("aa.op.bottomHeight");
        onCloseTerminal();
      } else if (terminalDock === "side" && latestSize <= TERMINAL_SIDE_COLLAPSE_WIDTH) {
        setRightWidth(null);
        window.localStorage.removeItem("aa.op.rightWidth");
        onCloseTerminal();
      }
      window.dispatchEvent(new Event("resize"));
    };
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", up);
  }

  function startCollapsedSidebarResize(ev: ReactPointerEvent<HTMLDivElement>) {
    const left = ev.currentTarget.parentElement;
    if (!left) return;
    ev.preventDefault();
    const splitter = ev.currentTarget;
    const rect = left.getBoundingClientRect();
    const available = Math.max(0, rect.width - OP_LEFT_RAIL_WIDTH);
    document.body.classList.add("resizing-op-left-restore");
    splitter.classList.add("resizing");
    let latestWidth = 0;

    const move = (e: PointerEvent) => {
      const next = clampFilesSideWidth(e.clientX - rect.left - OP_LEFT_RAIL_WIDTH, available);
      latestWidth = next;
      if (next > FILES_SIDE_COLLAPSE_WIDTH) {
        setSidePanelOpen(true);
        setLeftCollapsed(false);
        setFilesSideWidth(next);
        draftFilesSideWidth(next);
      }
      window.dispatchEvent(new Event("resize"));
    };
    const up = () => {
      document.body.classList.remove("resizing-op-left-restore");
      splitter.classList.remove("resizing");
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", up);
      if (latestWidth <= FILES_SIDE_COLLAPSE_WIDTH) {
        setSidePanelOpen(false);
        commitFilesSideWidth(latestWidth);
      } else {
        const committed = commitFilesSideWidth(latestWidth);
        if (committed != null) setFilesSideWidth(committed);
      }
      window.dispatchEvent(new Event("resize"));
    };
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", up);
  }

  function startHiddenTerminalResize(ev: ReactPointerEvent<HTMLDivElement>) {
    const body = bodyRef.current;
    if (!body) return;
    ev.preventDefault();
    const splitter = ev.currentTarget;
    const rect = body.getBoundingClientRect();
    const resizingClass = terminalDock === "bottom" ? "resizing-op-terminal-bottom" : "resizing-op-terminal-restore";
    document.body.classList.add(resizingClass);
    splitter.classList.add("resizing");
    let latestSize = 0;
    let opened = false;

    const move = (e: PointerEvent) => {
      const rawSize = terminalDock === "bottom" ? rect.bottom - e.clientY : rect.right - e.clientX;
      latestSize = rawSize;
      const collapseSize = terminalDock === "bottom" ? TERMINAL_BOTTOM_COLLAPSE_HEIGHT : TERMINAL_SIDE_COLLAPSE_WIDTH;
      if (rawSize > collapseSize) {
        if (!opened) {
          opened = true;
          onToggleTerminal();
        }
        if (terminalDock === "bottom") {
          const next = clampBottomHeight(rawSize, rect.height);
          setBottomHeight(next);
          window.localStorage.setItem("aa.op.bottomHeight", String(Math.round(next)));
        } else {
          const next = clampRightWidth(rawSize, rect.width);
          setRightWidth(next);
          window.localStorage.setItem("aa.op.rightWidth", String(Math.round(next)));
        }
      }
      window.dispatchEvent(new Event("resize"));
    };
    const up = () => {
      document.body.classList.remove(resizingClass);
      splitter.classList.remove("resizing");
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", up);
      const collapseSize = terminalDock === "bottom" ? TERMINAL_BOTTOM_COLLAPSE_HEIGHT : TERMINAL_SIDE_COLLAPSE_WIDTH;
      if (latestSize <= collapseSize) {
        if (terminalDock === "bottom") {
          setBottomHeight(null);
          window.localStorage.removeItem("aa.op.bottomHeight");
        } else {
          setRightWidth(null);
          window.localStorage.removeItem("aa.op.rightWidth");
        }
        if (opened) onCloseTerminal();
      }
      window.dispatchEvent(new Event("resize"));
    };
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", up);
  }

  const dockTarget: TerminalDock = terminalDock === "side" ? "bottom" : "side";
  const dockTitle =
    dockTarget === "bottom" ? t("operation.dockTerminalBottom") : t("operation.dockTerminalSide");
  const resizeTerminalAria =
    terminalDock === "bottom" ? t("operation.resizeTerminalHeightAria") : t("operation.resizeTerminalAria");
  const shortcut = isMacPlatform()
      ? {
        files: "⌘⇧E",
        search: "⌘⇧F",
        changes: "⌃⇧G",
        hidePanel: "⌘J",
      }
    : {
        files: "Ctrl+Shift+E",
        search: "Ctrl+Shift+F",
        changes: "Ctrl+Shift+G",
        hidePanel: "Ctrl+J",
      };
  const shortcutTitle = (label: string, keys: string) => `${label} (${keys})`;
  const terminalPanelStyle =
    terminalDock === "bottom"
      ? undefined
      : rightWidth
        ? { width: rightWidth }
        : undefined;
  const tabHasFileSizedSidebar = tab === "files" || tab === "search" || tab === "changes";
  const bottomDockSidebarWidth =
    !leftCollapsed && sidePanelOpen && tabHasFileSizedSidebar
      ? OP_LEFT_RAIL_WIDTH + filesSideWidth
      : OP_LEFT_RAIL_WIDTH;
  const opBodyStyle = {
    "--op-files-side-width": `${Math.round(filesSideWidth)}px`,
    ...(terminalDock === "bottom"
      ? {
          "--op-bottom-sidebar-width": `${Math.round(bottomDockSidebarWidth)}px`,
          ...(terminalVisible && bottomHeight
            ? { "--op-terminal-bottom-height": `${Math.round(bottomHeight)}px` }
            : {}),
        }
      : {}),
  } as CSSProperties;

  return (
    <div className="op">
      <div className={"op-top work-nav" + (isMacPlatform() ? " work-nav-mac" : "")}>
        <button
          type="button"
          onClick={onHome}
          className="crumb-btn crumb-home-btn"
          title={t("common.home")}
          aria-label={t("common.home")}
        >
          <BreadcrumbHomeIcon />
        </button>
        <span className="crumb-sep">/</span>
        <button onClick={onBack} className="crumb-btn">
          {plainLineLabel(lineLabel(line))}
        </button>
        <span className="crumb-sep">/</span>
        <div className="crumb">
          <b>{root.name}</b>
        </div>
        {isCanvasLine && shouldReadCanvas && episodes.length > 0 && (
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
            {canvasSourceHint && (
              <button
                type="button"
                className="ep-source-info"
                data-tooltip={canvasSourceHint}
                data-tooltip-placement="bottom"
                aria-label={canvasSourceHint}
              >
                <Codicon name="info" />
              </button>
            )}
          </div>
        )}
        <button
          type="button"
          className="work-nav-skill-btn"
          title={t("line.skillsButton")}
          aria-label={t("line.skillsButton")}
          onClick={() => onShowSkills(line)}
        >
          <Codicon name="wrench" />
        </button>
      </div>

      <div
        className={
          "op-body" +
          (leftCollapsed ? " op-body-left-collapsed" : "") +
          (terminalVisible ? ` op-body-terminal-${terminalDock}` : " op-body-terminal-hidden")
        }
        ref={bodyRef}
        style={opBodyStyle}
      >
        <div className={"op-left" + (leftCollapsed ? " collapsed" : "")}>
          <div className="op-left-rail" aria-label={t("operation.leftDeferred")}>
            <button
              type="button"
              className={"rail-tab" + (sidePanelOpen && tab === "files" ? " active" : "")}
              data-tooltip={shortcutTitle(t("operation.filesTab"), shortcut.files)}
              data-tooltip-placement="right"
              aria-label={t("operation.filesTab")}
              onClick={() => openLeft("files")}
            >
              <RailIcon name="files" />
            </button>
            <button
              type="button"
              className={"rail-tab" + (sidePanelOpen && tab === "search" ? " active" : "")}
              data-tooltip={shortcutTitle(t("operation.searchTab"), shortcut.search)}
              data-tooltip-placement="right"
              aria-label={t("operation.searchTab")}
              onClick={() => openLeft("search")}
            >
              <RailIcon name="search" />
            </button>
            <button
              type="button"
              className={
                "rail-tab rail-change" +
                (sidePanelOpen && tab === "changes" ? " active" : "") +
                (changeCount ? " dirty" : "")
              }
              data-tooltip={`${shortcutTitle(t("operation.changesTab"), shortcut.changes)} · ${changeLabel}`}
              data-tooltip-placement="right"
              aria-label={`${t("operation.changesTab")} · ${changeLabel}`}
              onClick={() => openLeft("changes")}
            >
              <RailIcon name="changes" />
              {changeSummary == null ? (
                <span className="rail-badge loading">…</span>
              ) : changeCount > 0 ? (
                <span className="rail-badge">{changeCount > 99 ? "99+" : changeCount}</span>
              ) : null}
            </button>
            {isCanvasLine && (
              <button
                type="button"
                className={"rail-tab" + (sidePanelOpen && tab === "canvas" ? " active" : "")}
                data-tooltip={t("operation.canvasTab")}
                data-tooltip-placement="right"
                aria-label={t("operation.canvasTab")}
                onClick={() => openLeft("canvas")}
              >
                <RailIcon name="canvas" />
              </button>
            )}
            <button
              type="button"
              className={"rail-tab" + (sidePanelOpen && tab === "review" ? " active" : "")}
              data-tooltip={t("operation.reviewTab")}
              data-tooltip-placement="right"
              aria-label={t("operation.reviewTab")}
              onClick={() => openLeft("review")}
            >
              <RailIcon name="review" />
            </button>
          </div>
          {!leftCollapsed && !sidePanelOpen && tabHasFileSizedSidebar && (
            <div
              className="op-left-restore-splitter"
              role="separator"
              aria-orientation="vertical"
              aria-label={t("files.resizeAria")}
              onPointerDown={startCollapsedSidebarResize}
            />
          )}
          {!leftCollapsed && (
            <div className="op-left-content">
              <div className="subtab-body">
                {!secondaryReady ? (
                  <div className="stub-view">{t("common.loading")}</div>
                ) : (
                  <>
                    <div
                      className={
                        "subtab-layer" +
                        (sidePanelOpen && tab !== "files" && tab !== "search" && tab !== "changes" ? " hidden" : "")
                      }
                    >
                      <Suspense fallback={<div className="stub-view">{t("common.loading")}</div>}>
                        <FilesPane
                          root={root}
                          refreshKey={refreshKey + baselineVersion}
                          allowNovelImport={line.line === "n2d" && workIsEmpty}
                          active={active}
                          sideVisible={sidePanelOpen && tab === "files"}
                          reserveSide={sidePanelOpen && (tab === "search" || tab === "changes")}
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
                    </div>
                    {sidePanelOpen && tab === "changes" && (
                      <div className="subtab-layer side-only-layer">
                        <Suspense fallback={<div className="stub-view">{t("common.loading")}</div>}>
                          <ChangesPane
                            root={root}
                            refreshKey={changeScanKey}
                            baselineVersion={baselineVersion}
                            summary={changeSummary}
                            sideOnly
                            onArchived={(summary) => {
                              changeSummaryEpochRef.current += 1;
                              setChangeSummary(summary);
                              setBaselineVersion((version) => version + 1);
                              setChangeScanKey((key) => key + 1);
                            }}
                          />
                        </Suspense>
                      </div>
                    )}
                    {sidePanelOpen && tab === "search" && (
                      <div className="subtab-layer side-only-layer">
                        <Suspense fallback={<div className="stub-view">{t("common.loading")}</div>}>
                          <SearchPane root={root} refreshKey={refreshKey + baselineVersion} sideOnly />
                        </Suspense>
                      </div>
                    )}
                    {sidePanelOpen && tab === "review" && (
                      <div className="subtab-layer">
                        {isCanvasLine ? (
                          err ? (
                            <div className="stub-view">{t("common.readFailed", { error: err })}</div>
                          ) : !canvas ? (
                            <div className="stub-view">{t("common.loading")}</div>
                          ) : (
                            <Suspense fallback={<div className="stub-view">{t("common.loading")}</div>}>
                              <EpisodeWorkspacePane
                                root={root}
                                line={line.line}
                                ep={ep}
                                canvas={canvas}
                                refreshKey={refreshKey}
                              />
                            </Suspense>
                          )
                        ) : (
                          <Suspense fallback={<div className="stub-view">{t("common.loading")}</div>}>
                            <QualityInsightsPane
                              root={root}
                              line={line.line}
                              ep={null}
                              refreshKey={refreshKey + baselineVersion}
                            />
                          </Suspense>
                        )}
                      </div>
                    )}
                    {sidePanelOpen && isCanvasLine && tab === "canvas" && (
                      <div className="subtab-layer">
                        {err ? (
                          <div className="stub-view">{t("common.readFailed", { error: err })}</div>
                        ) : !canvas ? (
                          <div className="stub-view">{t("common.loading")}</div>
                        ) : (
                          <Suspense fallback={<div className="stub-view">{t("common.loading")}</div>}>
                            <CanvasPane canvas={canvas} root={root} ep={ep} refreshKey={refreshKey} />
                          </Suspense>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          )}
        </div>
        {terminalVisible && (
          <div
            className="op-splitter"
            role="separator"
            aria-orientation={terminalDock === "bottom" ? "horizontal" : "vertical"}
            aria-label={resizeTerminalAria}
            onPointerDown={startTerminalResize}
            onDoubleClick={() => {
              if (terminalDock === "bottom") {
                setBottomHeight(null);
                window.localStorage.removeItem("aa.op.bottomHeight");
              } else {
                setRightWidth(null);
                window.localStorage.removeItem("aa.op.rightWidth");
              }
              window.dispatchEvent(new Event("resize"));
            }}
          />
        )}
        {!terminalVisible && (
          <div
            className={`op-terminal-restore-splitter op-terminal-restore-${terminalDock}`}
            role="separator"
            aria-orientation={terminalDock === "bottom" ? "horizontal" : "vertical"}
            aria-label={resizeTerminalAria}
            onPointerDown={startHiddenTerminalResize}
            onDoubleClick={() => {
              onToggleTerminal();
              window.dispatchEvent(new Event("resize"));
            }}
          />
        )}
        <div className="op-right" style={terminalPanelStyle}>
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
            afterSettingsAction={
              <>
                <button
                  type="button"
                  className="project-settings-btn terminal-new-btn"
                  title={t("terminal.newSession")}
                  aria-label={t("terminal.newSession")}
                  onClick={() => termRef.current?.newSession()}
                >
                  <Codicon name="add" />
                </button>
                <button
                  type="button"
                  className={`project-settings-btn terminal-dock-btn terminal-dock-btn-${dockTarget}`}
                  title={dockTitle}
                  aria-label={dockTitle}
                  onClick={() => setTerminalDock(dockTarget)}
                >
                  <Codicon name={dockTarget === "bottom" ? "layoutPanel" : "layoutSidebarRight"} />
                </button>
                <button
                  type="button"
                  className="project-settings-btn terminal-close-btn"
                  title={`${t("terminal.hidePanel")} (${shortcut.hidePanel})`}
                  aria-label={`${t("terminal.hidePanel")} (${shortcut.hidePanel})`}
                  onClick={onCloseTerminal}
                >
                  <Codicon name="close" />
                </button>
              </>
            }
          />
          <TerminalPane
            ref={termRef}
            cwd={root.path}
            onReady={() => setTermReady(true)}
            placeholder={terminalPlaceholder}
            agents={agents}
            probeEnabled={active && secondaryReady}
            onActiveAgentChange={handleActiveAgentChange}
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
