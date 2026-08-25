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
  failCanvasTask,
  markCanvasTaskRunning,
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
import type {
  AgentInfo,
  CanvasAgentDispatchContext,
  CanvasAgentDispatchResult,
  CanvasData,
  LineInfo,
  WorkChangeSummary,
  WorkRoot,
} from "../types";
import {
  TerminalPane,
  type TerminalHandle,
  type TerminalSessionEndReason,
} from "../components/TerminalPane";
import { NextActionStrip } from "../components/NextActionStrip";
import { Codicon } from "../components/Codicon";
import { BreadcrumbHomeIcon } from "../components/BreadcrumbHomeIcon";
import { RailIcon } from "../components/RailIcon";
import { LoadingHint } from "../components/LoadingHint";
import { plainLineLabel, useI18n, useLineLabel } from "../i18n";
import {
  classifyCanvasDispatchReservation,
  decideCanvasJobWatchdog,
  settleEndedCanvasJob,
  shouldRehydrateCanvasJobWatchdog,
  shouldRetryCanvasPromptWrite,
  shouldSettleCanvasJobOnOwnerTeardown,
  takeJobsForEndedSession,
  type CanvasPromptWriteAttempt,
} from "../terminalJobLifecycle";
import {
  deliverInitialPrompt,
  type InitialPromptRequest,
} from "../initialPromptDelivery";
import {
  COLLAPSE_LEFT_SIDEBAR_EVENT,
  FILES_SIDE_COLLAPSE_WIDTH,
  FILES_SIDE_WIDTH_CHANGED_EVENT,
  clampFilesSideWidth,
  commitFilesSideWidth,
  draftFilesSideWidth,
  readCurrentFilesSideWidth,
  readStoredFilesSideWidth,
  scheduleWindowResizeEvent,
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
type PendingCanvasAgentJob = CanvasAgentDispatchContext & {
  sessionId: string;
  line: LineInfo["line"];
  dispatchedAt: number;
};
type CanvasJobSettlementReason = TerminalSessionEndReason | "turn_deadline";
const CANVAS_JOB_WATCHDOG_POLL_MS = 30_000;
const INITIAL_PROMPT_MAX_LAUNCH_ATTEMPTS = 3;
const INITIAL_PROMPT_RETRY_DELAY_MS = 900;

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
  initialPrompt?: InitialPromptRequest;
  onInitialPromptConsumed: (requestId: string) => void;
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
    initialPrompt,
    onInitialPromptConsumed,
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
  const [tab, setTab] = useState<LeftTab>(() => line.view === "canvas" ? "canvas" : "files");
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [sidePanelOpen, setSidePanelOpen] = useState(true);
  // 画布 is a per-episode view driven by canvas data; 质检 is available to every line.
  const shouldReadCanvas = isCanvasLine && (tab === "canvas" || tab === "review");
  // bumped (debounced) whenever the work root changes on disk → re-pull data
  const [refreshKey, setRefreshKey] = useState(0);
  const [changeScanKey, setChangeScanKey] = useState(0);
  // Scope hint for the next FilesPane refresh: which rel dirs actually changed
  // ('' = root-level), or `broad` when the change set is unknown/too large. Lets
  // the tree re-list only the affected open folders instead of the whole tree.
  const fsScopeRef = useRef<{ dirs: Set<string>; broad: boolean }>({ dirs: new Set(), broad: false });
  const [baselineVersion, setBaselineVersion] = useState(0);
  const termRef = useRef<TerminalHandle>(null);
  const changeSummaryEpochRef = useRef(0);
  const canvasSigRef = useRef<string | null>(null);
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
  const initialPromptSentRef = useRef<string | null>(null);
  const initialPromptInFlightRef = useRef<string | null>(null);
  const initialPromptAttemptsRef = useRef<{ requestId: string; count: number } | null>(null);
  const initialPromptRetryTimerRef = useRef<number | null>(null);
  const [initialPromptRetryEpoch, setInitialPromptRetryEpoch] = useState(0);
  const pendingCanvasJobsRef = useRef(new Map<string, PendingCanvasAgentJob>());
  const settlingCanvasJobsRef = useRef(new Set<string>());
  const canvasJobWatchdogTimersRef = useRef(new Map<string, number>());
  const operationMountedRef = useRef(true);
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

  async function runPromptInAgent(
    prompt: string,
    task?: CanvasAgentDispatchContext,
  ): Promise<CanvasAgentDispatchResult> {
    let dispatchReserved = false;
    const nudgeRefresh = () => {
      setRefreshKey((k) => k + 1);
      setChangeScanKey((k) => k + 1);
    };
    const waitForHandle = async (timeoutMs: number) => {
      const deadline = Date.now() + timeoutMs;
      while (Date.now() < deadline) {
        if (termRef.current) return termRef.current;
        await new Promise((resolve) => window.setTimeout(resolve, 80));
      }
      return null;
    };
    const bindTaskToActiveSession = () => {
      if (!task) return null;
      const sessionId = termRef.current?.activeSessionId();
      if (!sessionId) return null;
      const current = pendingCanvasJobsRef.current.get(task.job_id);
      pendingCanvasJobsRef.current.set(task.job_id, {
        ...task,
        sessionId,
        line: line.line,
        dispatchedAt: current?.dispatchedAt ?? Date.now(),
      });
      return sessionId;
    };
    const releaseFailedDispatch = (sessionId: string | null) => {
      if (!task || !sessionId) return;
      const pending = pendingCanvasJobsRef.current.get(task.job_id);
      if (pending?.sessionId === sessionId) {
        pendingCanvasJobsRef.current.delete(task.job_id);
        const timer = canvasJobWatchdogTimersRef.current.get(task.job_id);
        if (timer != null) window.clearTimeout(timer);
        canvasJobWatchdogTimersRef.current.delete(task.job_id);
      }
    };
    const reserveDispatch = async (): Promise<"active" | "succeeded" | "rejected"> => {
      if (!task || dispatchReserved) return "active";
      try {
        // Reserve the durable task before sending bytes to the executor. If
        // Electron dies between these operations, recovery keeps the committed
        // inputs and the bounded lease makes the job retryable; an old prompt
        // can never continue after its inputs were rolled back.
        const state = await markCanvasTaskRunning(task.root, task.episode, task.job_id);
        const status = state.tasks.find((item) => item.job_id === task.job_id)?.status;
        const reservation = classifyCanvasDispatchReservation(status);
        if (reservation !== "active") return reservation;
        dispatchReserved = true;
        return "active";
      } catch {
        return "rejected";
      }
    };
    const writeToActiveSession = async (value: string): Promise<CanvasPromptWriteAttempt> => {
      // Bind before awaiting the IPC write. A very short-lived executor can
      // otherwise exit between the acknowledged write and rememberTask(),
      // leaving its production job permanently running.
      const sessionId = bindTaskToActiveSession();
      if (task && sessionId) {
        const reservation = await reserveDispatch();
        if (reservation !== "active") {
          releaseFailedDispatch(sessionId);
          return reservation;
        }
      }
      const written = await termRef.current?.runCommand(value) ?? false;
      if (!written) releaseFailedDispatch(sessionId);
      else if (task) scheduleCanvasJobWatchdog(task.job_id);
      return written ? "written" : "retry";
    };
    const writeWhenReady = async (value: string, timeoutMs: number): Promise<CanvasPromptWriteAttempt> => {
      const deadline = Date.now() + timeoutMs;
      while (Date.now() < deadline) {
        const attempt = await writeToActiveSession(value);
        if (!shouldRetryCanvasPromptWrite(attempt)) return attempt;
        await new Promise((resolve) => window.setTimeout(resolve, 100));
      }
      return "retry";
    };
    const finishWithoutWrite = (attempt: CanvasPromptWriteAttempt): CanvasAgentDispatchResult | null => {
      if (attempt === "succeeded") {
        showToast(t("operation.canvasTaskAlreadyComplete"));
        nudgeRefresh();
        return "succeeded";
      }
      if (attempt === "rejected") {
        showToast(t("operation.canvasTaskRefreshRequired"));
        nudgeRefresh();
        return "rejected";
      }
      return null;
    };
    const rejectUnsentTask = async (): Promise<CanvasAgentDispatchResult> => {
      if (task) {
        await failCanvasTask(
          task.root,
          task.episode,
          task.job_id,
          "agent dispatch was not acknowledged",
        ).catch(() => undefined);
      }
      showToast(t("operation.agentDispatchFailed"));
      nudgeRefresh();
      return "rejected";
    };
    const current = activeAgentRef.current;
    if (current) {
      const wasVisible = terminalVisible;
      if (!wasVisible) onToggleTerminal();
      const handle = await waitForHandle(4_000);
      if (!handle) {
        return rejectUnsentTask();
      }
      if (wasVisible) {
        const attempt = await writeToActiveSession(prompt);
        if (attempt === "written") {
          showToast(t("operation.sentToAgent", { name: current.name }));
          nudgeRefresh();
          window.setTimeout(nudgeRefresh, 3000);
          return "dispatched";
        }
        const terminal = finishWithoutWrite(attempt);
        if (terminal) return terminal;
      }
      handle.switchCommand(current.command, current.id);
      const attempt = await writeWhenReady(prompt, 8_000);
      if (attempt === "written") {
        showToast(t("operation.sentToAgent", { name: current.name }));
        nudgeRefresh();
        window.setTimeout(nudgeRefresh, 3000);
        return "dispatched";
      }
      const terminal = finishWithoutWrite(attempt);
      if (terminal) return terminal;
      return rejectUnsentTask();
    }

    const def = pickDefaultAgent(agents ?? []);
    if (def) {
      if (!terminalVisible) onToggleTerminal();
      const handle = await waitForHandle(4_000);
      if (!handle) {
        return rejectUnsentTask();
      }
      activeAgentRef.current = def;
      setTerminalMode("agent");
      handle.switchCommand(def.command, def.id);
      const attempt = await writeWhenReady(prompt, 8_000);
      if (attempt === "written") {
        showToast(t("operation.startedAgentAndSent", { name: def.name }));
        nudgeRefresh();
        window.setTimeout(nudgeRefresh, 3800);
        return "dispatched";
      }
      const terminal = finishWithoutWrite(attempt);
      if (terminal) return terminal;
      return rejectUnsentTask();
    }

    termRef.current?.focus();
    showToast(t("operation.noAgent"));
    if (task) {
      await failCanvasTask(task.root, task.episode, task.job_id, "no available agent executor").catch(() => undefined);
      nudgeRefresh();
    }
    return "rejected";
  }

  const scheduleCanvasJobSettlement = useCallback((task: PendingCanvasAgentJob, reason: CanvasJobSettlementReason) => {
    if (settlingCanvasJobsRef.current.has(task.job_id)) return;
    settlingCanvasJobsRef.current.add(task.job_id);
    // A successful agent commonly writes its receipt immediately before a
    // normal exit. Let the filesystem flush, then force a receipt-aware canvas
    // read before deciding whether this lifecycle end is a failure.
    void settleEndedCanvasJob({
      // Forced teardown must reconcile immediately; only a normal process exit
      // needs a short receipt-flush grace period.
      graceMs: reason === "process_exit" ? 2500 : 0,
      wait: (milliseconds) => new Promise((resolve) => window.setTimeout(resolve, milliseconds)),
      readStatus: async () => {
        const result = await readCanvas(task.root, task.episode, task.line);
        return result.canvas?.production?.tasks.find((item) => item.job_id === task.job_id)?.status;
      },
      failActiveTask: () => failCanvasTask(
        task.root,
        task.episode,
        task.job_id,
        `agent PTY ended (${reason}) without a verified receipt`,
      ),
    })
      .catch(() => "unresolved" as const)
      .finally(() => {
        settlingCanvasJobsRef.current.delete(task.job_id);
        if (!operationMountedRef.current) return;
        canvasSigRef.current = null;
        setRefreshKey((key) => key + 1);
      });
  }, []);

  const scheduleCanvasJobWatchdog = useCallback((jobId: string, delayMs = CANVAS_JOB_WATCHDOG_POLL_MS): void => {
    const previousTimer = canvasJobWatchdogTimersRef.current.get(jobId);
    if (previousTimer != null) window.clearTimeout(previousTimer);
    if (!pendingCanvasJobsRef.current.has(jobId)) {
      canvasJobWatchdogTimersRef.current.delete(jobId);
      return;
    }
    const timer = window.setTimeout(() => {
      canvasJobWatchdogTimersRef.current.delete(jobId);
      const pending = pendingCanvasJobsRef.current.get(jobId);
      if (!pending) return;
      void readCanvas(pending.root, pending.episode, pending.line)
        .then((result) => {
          const snapshot = result.canvas?.production?.tasks.find((item) => item.job_id === jobId);
          const decision = decideCanvasJobWatchdog(snapshot ? {
            status: snapshot.status,
            kind: snapshot.kind,
            submittedAt: snapshot.submitted_at,
          } : undefined, Date.now(), pending.dispatchedAt);
          if (decision.action === "unbind") {
            pendingCanvasJobsRef.current.delete(jobId);
            if (operationMountedRef.current) {
              canvasSigRef.current = null;
              setRefreshKey((key) => key + 1);
            }
            return;
          }
          if (decision.action === "fail") {
            pendingCanvasJobsRef.current.delete(jobId);
            scheduleCanvasJobSettlement(pending, "turn_deadline");
            return;
          }
          scheduleCanvasJobWatchdog(jobId, Math.min(CANVAS_JOB_WATCHDOG_POLL_MS, decision.remainingMs));
        })
        .catch(() => scheduleCanvasJobWatchdog(jobId));
    }, Math.max(0, delayMs));
    canvasJobWatchdogTimersRef.current.set(jobId, timer);
  }, [scheduleCanvasJobSettlement]);

  const settleJobsForEndedSession = useCallback((sessionId: string, reason: TerminalSessionEndReason) => {
    for (const task of takeJobsForEndedSession(pendingCanvasJobsRef.current, sessionId)) {
      const timer = canvasJobWatchdogTimersRef.current.get(task.job_id);
      if (timer != null) window.clearTimeout(timer);
      canvasJobWatchdogTimersRef.current.delete(task.job_id);
      scheduleCanvasJobSettlement(task, reason);
    }
  }, [scheduleCanvasJobSettlement]);

  useEffect(() => {
    const production = canvas?.production;
    if (!production) return;
    for (const task of production.tasks) {
      if (!shouldRehydrateCanvasJobWatchdog(
        task.status,
        pendingCanvasJobsRef.current.has(task.job_id),
        settlingCanvasJobsRef.current.has(task.job_id),
      )) continue;
      const durableStartedAt = Date.parse(task.submitted_at);
      pendingCanvasJobsRef.current.set(task.job_id, {
        root: root.path,
        episode: production.episode,
        job_id: task.job_id,
        line: line.line,
        // No renderer session survives a restart. The sentinel keeps this
        // recovered lease out of unrelated live PTY lifecycle claims.
        sessionId: `recovered:${task.job_id}`,
        dispatchedAt: Number.isFinite(durableStartedAt) ? durableStartedAt : Date.now(),
      });
      // Deliberately bypass known-sig reads: the watchdog must force main-side
      // receipt reconciliation and lease expiry even without filesystem events.
      scheduleCanvasJobWatchdog(task.job_id, 0);
    }
  }, [canvas?.production, line.line, root.path, scheduleCanvasJobWatchdog]);

  useEffect(() => {
    operationMountedRef.current = true;
    return () => {
      operationMountedRef.current = false;
      // React may tear Operation down before child cleanup reaches us. Drain
      // every outstanding binding here as a second, idempotent safety net.
      for (const task of pendingCanvasJobsRef.current.values()) {
        // A recovered binding has no PTY owned by this renderer. Navigating
        // away must not turn a still-valid durable job into a false failure;
        // main-side leases and the next mount's watchdog remain authoritative.
        if (!shouldSettleCanvasJobOnOwnerTeardown(task.sessionId)) continue;
        scheduleCanvasJobSettlement(task, "component_unmounted");
      }
      pendingCanvasJobsRef.current.clear();
      for (const timer of canvasJobWatchdogTimersRef.current.values()) window.clearTimeout(timer);
      canvasJobWatchdogTimersRef.current.clear();
    };
  }, [scheduleCanvasJobSettlement]);

  useEffect(() => {
    return () => {
      if (toastTimer.current) window.clearTimeout(toastTimer.current);
      if (initialPromptRetryTimerRef.current != null) {
        window.clearTimeout(initialPromptRetryTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    setTermReady(false);
    activeAgentRef.current = null;
    setTerminalMode("native");
    autoEnteredAgentRootRef.current = null;
  }, [root.path]);

  useEffect(() => {
    initialPromptSentRef.current = null;
    initialPromptInFlightRef.current = null;
    initialPromptAttemptsRef.current = null;
    if (initialPromptRetryTimerRef.current != null) {
      window.clearTimeout(initialPromptRetryTimerRef.current);
      initialPromptRetryTimerRef.current = null;
    }
  }, [initialPrompt?.id]);

  useEffect(() => {
    setSecondaryReady(false);
    if (!active) return;
    const timer = window.setTimeout(() => setSecondaryReady(true), termReady ? 450 : 2400);
    return () => window.clearTimeout(timer);
  }, [active, termReady, root.path]);

  // 空闲预热 Monaco chunk（~7MB 脚本的拉取+解析是"第一次打开文件"顿挫的主源）：
  // 等次级面板就绪后再排到 idle 档，不与终端/画布首屏抢主线程。模块级幂等，
  // 多次进入工作台不重复付费。
  useEffect(() => {
    if (!active || !secondaryReady) return;
    const w = window as Window & {
      requestIdleCallback?: (cb: () => void, opts?: { timeout: number }) => number;
      cancelIdleCallback?: (handle: number) => void;
    };
    const preload = () => {
      void import("../components/MonacoFileEditor").catch(() => {});
    };
    const handle = w.requestIdleCallback
      ? w.requestIdleCallback(preload, { timeout: 4000 })
      : window.setTimeout(preload, 1200);
    return () => {
      if (w.cancelIdleCallback) w.cancelIdleCallback(handle);
      else window.clearTimeout(handle);
    };
  }, [active, secondaryReady]);

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
    scheduleWindowResizeEvent();
    const timer = window.setTimeout(() => scheduleWindowResizeEvent(), 120);
    return () => window.clearTimeout(timer);
  }, [terminalDock]);

  useEffect(() => {
    if (!active || !secondaryReady) return;
    probeAgents(false);
  }, [active, secondaryReady, probeAgents]);

  useEffect(() => {
    if (!terminalVisible) setLeftCollapsed(false);
    scheduleWindowResizeEvent();
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
    const launchRequest = initialPrompt;
    if (launchRequest) {
      const requestId = launchRequest.id;
      if (
        initialPromptSentRef.current === requestId ||
        initialPromptInFlightRef.current === requestId
      ) {
        return;
      }
      const attempts = initialPromptAttemptsRef.current?.requestId === requestId
        ? initialPromptAttemptsRef.current.count
        : 0;
      if (attempts >= INITIAL_PROMPT_MAX_LAUNCH_ATTEMPTS) return;
      const def = pickDefaultAgent(agents);
      const handle = termRef.current;
      if (!def || !handle) return;

      initialPromptInFlightRef.current = requestId;
      initialPromptAttemptsRef.current = { requestId, count: attempts + 1 };
      autoEnteredAgentRootRef.current = root.path;
      activeAgentRef.current = def;
      setTerminalMode("agent");

      void deliverInitialPrompt(
        launchRequest,
        (prompt) => handle.switchCommand(def.command, def.id, prompt),
      ).then((result) => {
        if (!operationMountedRef.current || initialPromptInFlightRef.current !== requestId) return;
        initialPromptInFlightRef.current = null;
        if (result === "delivered") {
          initialPromptSentRef.current = requestId;
          if (initialPromptRetryTimerRef.current != null) {
            window.clearTimeout(initialPromptRetryTimerRef.current);
            initialPromptRetryTimerRef.current = null;
          }
          showToast(t("operation.startedAgentAndSent", { name: def.name }));
          setRefreshKey((key) => key + 1);
          setChangeScanKey((key) => key + 1);
          onInitialPromptConsumed(requestId);
          return;
        }

        const nextAttempt = attempts + 1;
        if (nextAttempt >= INITIAL_PROMPT_MAX_LAUNCH_ATTEMPTS) {
          showToast(t("operation.agentDispatchFailed"));
          return;
        }
        if (initialPromptRetryTimerRef.current != null) {
          window.clearTimeout(initialPromptRetryTimerRef.current);
        }
        initialPromptRetryTimerRef.current = window.setTimeout(() => {
          initialPromptRetryTimerRef.current = null;
          setInitialPromptRetryEpoch((epoch) => epoch + 1);
        }, INITIAL_PROMPT_RETRY_DELAY_MS * nextAttempt);
      });
      return;
    }

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
    void termRef.current?.switchCommand(def.command, def.id);
  }, [
    active,
    secondaryReady,
    termReady,
    agents,
    initialPrompt,
    root.path,
    terminalMode,
    initialPromptRetryEpoch,
    onInitialPromptConsumed,
    t,
  ]);

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
    canvasSigRef.current = null;
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
    // fs events unrelated to the canvas (terminal output, temp files) also bump
    // refreshKey. We pass the last content signature down to the main process:
    // unchanged reads come back as a tiny `{ sig, unchanged }` envelope——no full
    // CanvasData structured-clone over IPC, no renderer-side JSON.stringify of a
    // large payload (both used to run on every fs event and janked the canvas).
    readCanvas(root.path, ep, line.line, canvasSigRef.current || undefined)
      .then((d) => {
        if (!alive) return;
        if (d.unchanged || !d.canvas) {
          canvasSigRef.current = d.sig;
          return;
        }
        canvasSigRef.current = d.sig;
        setCanvas(d.canvas);
        if (d.canvas.episodes.length && !d.canvas.episodes.includes(ep)) setEp(d.canvas.episodes[0]);
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
      if (payload.dirs) for (const d of payload.dirs) fsScopeRef.current.dirs.add(d);
      else fsScopeRef.current.broad = true; // unknown scope → full refresh
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
          fsScopeRef.current.broad = true; // polling can't localize the change
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
      scheduleWindowResizeEvent();
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
      scheduleWindowResizeEvent();
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
      scheduleWindowResizeEvent();
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
      scheduleWindowResizeEvent();
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
      scheduleWindowResizeEvent();
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
      scheduleWindowResizeEvent();
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
                  <LoadingHint className="stub-view" label={t("common.loading")} />
                ) : (
                  <>
                    <div
                      className={
                        "subtab-layer" +
                        (sidePanelOpen && tab !== "files" && tab !== "search" && tab !== "changes" ? " hidden" : "")
                      }
                    >
                      <Suspense fallback={<LoadingHint className="stub-view" label={t("common.loading")} />}>
                        <FilesPane
                          root={root}
                          refreshKey={refreshKey + baselineVersion}
                          fsScopeRef={fsScopeRef}
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
                        <Suspense fallback={<LoadingHint className="stub-view" label={t("common.loading")} />}>
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
                        <Suspense fallback={<LoadingHint className="stub-view" label={t("common.loading")} />}>
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
                            <LoadingHint className="stub-view" label={t("common.loading")} />
                          ) : (
                            <Suspense fallback={<LoadingHint className="stub-view" label={t("common.loading")} />}>
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
                          <Suspense fallback={<LoadingHint className="stub-view" label={t("common.loading")} />}>
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
                          <LoadingHint className="stub-view" label={t("common.loading")} />
                        ) : (
                          <Suspense fallback={<LoadingHint className="stub-view" label={t("common.loading")} />}>
                            <CanvasPane
                              canvas={canvas}
                              root={root}
                              ep={ep}
                              line={line.line}
                              repoRoot={repoRoot}
                              refreshKey={refreshKey}
                              onGeneratePrompt={(prompt, task) => {
                                return runPromptInAgent(prompt, task);
                              }}
                              onCanvasChanged={() => {
                                canvasSigRef.current = null;
                                setRefreshKey((key) => key + 1);
                                setChangeScanKey((key) => key + 1);
                              }}
                            />
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
              scheduleWindowResizeEvent();
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
              scheduleWindowResizeEvent();
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
            onSessionEnd={settleJobsForEndedSession}
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
