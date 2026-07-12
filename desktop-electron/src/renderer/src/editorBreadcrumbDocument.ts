export type EditorBreadcrumbDocumentSnapshot = {
  path: string;
  text: string;
  revision: number;
};

export type EditorBreadcrumbDocumentStore = {
  getSnapshot: () => EditorBreadcrumbDocumentSnapshot;
  setDocument: (path: string, text: string) => void;
  subscribe: (listener: () => void) => () => void;
};

export function createEditorBreadcrumbDocumentStore(): EditorBreadcrumbDocumentStore {
  let snapshot: EditorBreadcrumbDocumentSnapshot = { path: "", text: "", revision: 0 };
  const listeners = new Set<() => void>();
  return {
    getSnapshot: () => snapshot,
    setDocument: (path, text) => {
      if (snapshot.path === path && snapshot.text === text) return;
      snapshot = { path, text, revision: snapshot.revision + 1 };
      for (const listener of listeners) listener();
    },
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}
