export const MAX_RETAINED_WORK_SESSIONS = 3;

export type WorkSessionIdentity = {
  id: string;
};

export type WorkSessionTouchResult<T extends WorkSessionIdentity> = {
  sessions: T[];
  evicted: T[];
};

/**
 * Keep work sessions ordered from least to most recently used.
 * Touching an existing work moves it to the MRU edge; adding beyond the
 * capacity evicts the oldest mounted workbench, which in turn owns the PTY.
 */
export function touchWorkSession<T extends WorkSessionIdentity>(
  sessions: readonly T[],
  next: T,
  capacity = MAX_RETAINED_WORK_SESSIONS,
): WorkSessionTouchResult<T> {
  const boundedCapacity = Math.max(1, Math.floor(capacity));
  const ordered = [...sessions.filter((session) => session.id !== next.id), next];
  const overflow = Math.max(0, ordered.length - boundedCapacity);
  return {
    sessions: ordered.slice(overflow),
    evicted: ordered.slice(0, overflow),
  };
}

export function removeWorkSession<T extends WorkSessionIdentity>(
  sessions: readonly T[],
  id: string,
): T[] {
  return sessions.filter((session) => session.id !== id);
}
