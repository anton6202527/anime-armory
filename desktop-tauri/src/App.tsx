import { useEffect, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { Home } from "./pages/Home";
import { Operation } from "./pages/Operation";
import { DEFAULT_REPO, ensureMedia } from "./api";
import type { LineInfo, WorkRoot } from "./types";

export interface Selection {
  line: LineInfo;
  root: WorkRoot;
}

export function App() {
  const [repoRoot, setRepoRoot] = useState<string>(DEFAULT_REPO);
  const [sel, setSel] = useState<Selection | null>(null);

  useEffect(() => {
    // boot the media server early (idempotent)
    ensureMedia().catch(() => {});
  }, []);

  async function pickRepo() {
    const picked = await open({ directory: true, multiple: false, defaultPath: repoRoot });
    if (typeof picked === "string") {
      setRepoRoot(picked);
      setSel(null);
    }
  }

  if (sel) {
    return (
      <Operation
        repoRoot={repoRoot}
        line={sel.line}
        root={sel.root}
        onBack={() => setSel(null)}
      />
    );
  }
  return <Home repoRoot={repoRoot} onPickRepo={pickRepo} onOpen={(line, root) => setSel({ line, root })} />;
}
