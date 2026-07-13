export type EditorBreadcrumbCursorStore = {
  getSnapshot: () => number;
  setLine: (line: number) => void;
  subscribe: (listener: () => void) => () => void;
};

export function createEditorBreadcrumbCursorStore(): EditorBreadcrumbCursorStore {
  let line = 1;
  const listeners = new Set<() => void>();
  return {
    getSnapshot: () => line,
    setLine: (nextLine) => {
      const next = Math.max(1, Math.floor(nextLine));
      if (next === line) return;
      line = next;
      for (const listener of listeners) listener();
    },
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}
