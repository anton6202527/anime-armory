export type CanvasExecutorTaskStatus = string | undefined;

export interface CanvasJobSettlementOptions {
  /** Receipt-aware state read; callers should reconcile receipts in this call. */
  readStatus: () => Promise<CanvasExecutorTaskStatus>;
  failActiveTask: () => Promise<unknown>;
  wait: (milliseconds: number) => Promise<void>;
  graceMs?: number;
  retryDelayMs?: number;
  maxReadAttempts?: number;
}

export type CanvasJobSettlementResult = "failed" | "terminal" | "unresolved";
export type CanvasDispatchReservation = "active" | "succeeded" | "rejected";
export type CanvasPromptWriteAttempt = "written" | "succeeded" | "rejected" | "retry";

/** A terminal task is not permission to claim that prompt bytes were sent. */
export function classifyCanvasDispatchReservation(status: string | undefined): CanvasDispatchReservation {
  if (status === "submitted" || status === "running") return "active";
  if (status === "succeeded") return "succeeded";
  return "rejected";
}

export function shouldRetryCanvasPromptWrite(attempt: CanvasPromptWriteAttempt): boolean {
  return attempt === "retry";
}

export function shouldRehydrateCanvasJobWatchdog(
  status: string | undefined,
  alreadyTracked: boolean,
  settlementInFlight: boolean,
): boolean {
  return (status === "submitted" || status === "running") && !alreadyTracked && !settlementInFlight;
}

/**
 * Recovered bindings have no renderer-owned PTY. Navigating away only stops
 * their local poller; it must not be interpreted as executor interruption.
 */
export function shouldSettleCanvasJobOnOwnerTeardown(sessionId: string): boolean {
  return !sessionId.startsWith("recovered:");
}

const IMAGE_JOB_DEADLINE_MS = 45 * 60 * 1_000;
const VIDEO_JOB_DEADLINE_MS = 2 * 60 * 60 * 1_000;
const PRODUCTION_JOB_DEADLINE_MS = 6 * 60 * 60 * 1_000;

export type CanvasJobWatchdogDecision =
  | { action: "unbind" }
  | { action: "fail" }
  | { action: "poll"; remainingMs: number };

export interface CanvasJobWatchdogSnapshot {
  status?: string;
  kind?: string;
  submittedAt?: string;
}

export type TerminalAgentLaunchPrompt = Readonly<{
  agentId: string;
  prompt: string;
}>;

export type InitialPromptProcessExitOutcome = "completed" | "failed";

export function classifyInitialPromptProcessExit(
  exitCode: number,
  signal?: number,
): InitialPromptProcessExitOutcome {
  return exitCode === 0 && !signal ? "completed" : "failed";
}

export function canvasJobHardDeadlineMs(kind: string | undefined): number {
  if (kind === "video") return VIDEO_JOB_DEADLINE_MS;
  if (kind === "production") return PRODUCTION_JOB_DEADLINE_MS;
  return IMAGE_JOB_DEADLINE_MS;
}

/** Pure watchdog policy used by the renderer's periodic receipt reconciliation. */
export function decideCanvasJobWatchdog(
  snapshot: CanvasJobWatchdogSnapshot | undefined,
  now: number,
  fallbackStartedAt: number,
): CanvasJobWatchdogDecision {
  if (!snapshot || (snapshot.status !== "submitted" && snapshot.status !== "running")) {
    return { action: "unbind" };
  }
  const durableStartedAt = snapshot.submittedAt ? Date.parse(snapshot.submittedAt) : Number.NaN;
  const startedAt = Number.isFinite(durableStartedAt) ? durableStartedAt : fallbackStartedAt;
  const remainingMs = canvasJobHardDeadlineMs(snapshot.kind) - Math.max(0, now - startedAt);
  return remainingMs <= 0 ? { action: "fail" } : { action: "poll", remainingMs };
}

/** Quote one argument for the POSIX login shell used by the PTY. */
export function shellQuoteTerminalArgument(value: string): string {
  return `'${value.replace(/'/g, `'"'"'`)}'`;
}

/**
 * Bind the first prompt to the CLI process launch. This avoids racing a TUI's
 * startup and preserves a multi-line prompt as one argument. Keep the adapter
 * explicit: silently sending the wrong flags to an unknown CLI would make a
 * successful PTY write look like successful prompt delivery.
 */
export function agentCommandWithInitialPrompt(
  command: string,
  request: TerminalAgentLaunchPrompt,
): string {
  const clean = command.trim();
  const prompt = shellQuoteTerminalArgument(request.prompt);
  switch (request.agentId) {
    case "codex":
    case "claude":
      return `${clean} -- ${prompt}`;
    case "opencode":
      return `${clean} --prompt ${prompt}`;
    case "gemini":
      return `${clean} --prompt-interactive ${prompt}`;
    case "kimi":
      return `${clean} --prompt ${prompt}`;
    default:
      throw new Error(`Initial prompt launch is not supported for agent: ${request.agentId}`);
  }
}

export function terminalLaunchCommand(
  command: string,
  agentOwned: boolean,
  initialPrompt?: TerminalAgentLaunchPrompt,
): string {
  const clean = command.trim();
  if (!clean || !agentOwned) return clean;
  const launch = initialPrompt ? agentCommandWithInitialPrompt(clean, initialPrompt) : clean;
  // An agent owns its PTY process lifetime. `exec` replaces the login shell so
  // an agent returning cannot silently fall back to a live shell without an
  // observable pty-exit. Native terminal commands intentionally keep the shell.
  return `exec ${launch}`;
}

/**
 * Reconcile a job after its executor ends. A job is failed only after a
 * successful receipt-aware read still reports it active; unreadable state is
 * left to the durable lease rather than risking a false failure.
 */
export async function settleEndedCanvasJob(
  options: CanvasJobSettlementOptions,
): Promise<CanvasJobSettlementResult> {
  const attempts = Math.max(1, options.maxReadAttempts ?? 3);
  const retryDelay = Math.max(0, options.retryDelayMs ?? 250);
  await options.wait(Math.max(0, options.graceMs ?? 0));

  let status: CanvasExecutorTaskStatus;
  let resolved = false;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      status = await options.readStatus();
      resolved = true;
      break;
    } catch {
      if (attempt + 1 < attempts) await options.wait(retryDelay);
    }
  }
  if (!resolved) return "unresolved";
  if (status !== "submitted" && status !== "running") return "terminal";
  await options.failActiveTask();
  return "failed";
}

/** Atomically claim all jobs for an ended logical terminal session. */
export function takeJobsForEndedSession<T extends { sessionId: string }>(
  jobs: Map<string, T>,
  sessionId: string,
): T[] {
  const claimed: T[] = [];
  for (const [jobId, job] of jobs) {
    if (job.sessionId !== sessionId) continue;
    jobs.delete(jobId);
    claimed.push(job);
  }
  return claimed;
}
