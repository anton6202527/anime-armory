import { useEffect, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { Home } from "./pages/Home";
import { Line } from "./pages/Line";
import { Operation } from "./pages/Operation";
import { SkillsModal } from "./components/SkillsModal";
import { DEFAULT_REPO, defaultWorkspace, ensureMedia, mediaAllowRoot, resolveRepo, seedDemos } from "./api";
import type { LineInfo, WorkRoot } from "./types";

type Route =
  | { kind: "home" }
  | { kind: "line"; line: LineInfo }
  | { kind: "op"; line: LineInfo; root: WorkRoot };

export function App() {
  // skills repo (runs the pipeline) — live checkout on a dev machine, else the
  // /tod-bundled copy shipped inside the installed app. Separate from the works
  // workspace. Falls back to DEFAULT_REPO until resolve_repo answers.
  const [repoRoot, setRepoRoot] = useState<string>(DEFAULT_REPO);
  // works workspace (~/AnimeArsenal) — app creates/deletes works here only
  const [workspaceRoot, setWorkspaceRoot] = useState<string>("");
  const [route, setRoute] = useState<Route>({ kind: "home" });
  const [skillsLine, setSkillsLine] = useState<LineInfo | null>(null);

  // resolve the skills repo (dev checkout vs bundled) on boot
  useEffect(() => {
    resolveRepo(DEFAULT_REPO)
      .then((r) => r && setRepoRoot(r))
      .catch((e) => console.error("repo resolve failed", e));
  }, []);

  // resolve the dedicated workspace on boot, then seed /tod --demos samples once
  useEffect(() => {
    defaultWorkspace()
      .then((ws) => {
        setWorkspaceRoot(ws);
        seedDemos(ws).catch(() => {}); // no-op unless built with --demos
      })
      .catch((e) => console.error("workspace resolve failed", e));
  }, []);

  // boot the media server (idempotent) and confine it to the works workspace
  useEffect(() => {
    if (!workspaceRoot) return;
    ensureMedia()
      .then(() => mediaAllowRoot(workspaceRoot))
      .catch(() => {});
  }, [workspaceRoot]);

  async function pickWorkspace() {
    const picked = await open({ directory: true, multiple: false, defaultPath: workspaceRoot });
    if (typeof picked === "string") {
      setWorkspaceRoot(picked);
      setRoute({ kind: "home" });
    }
  }

  if (!workspaceRoot) {
    return <div className="home"><h1>Anime Arsenal</h1><div className="empty">初始化工作区…</div></div>;
  }

  let page;
  if (route.kind === "op") {
    page = (
      <Operation
        repoRoot={repoRoot}
        line={route.line}
        root={route.root}
        onBack={() => setRoute({ kind: "line", line: route.line })}
      />
    );
  } else if (route.kind === "line") {
    page = (
      <Line
        workspaceRoot={workspaceRoot}
        line={route.line}
        onBack={() => setRoute({ kind: "home" })}
        onOpen={(root) => setRoute({ kind: "op", line: route.line, root })}
      />
    );
  } else {
    page = (
      <Home
        workspaceRoot={workspaceRoot}
        onPickWorkspace={pickWorkspace}
        onShowSkills={(line) => setSkillsLine(line)}
        onEnter={(line) => setRoute({ kind: "line", line })}
      />
    );
  }

  return (
    <>
      {page}
      {skillsLine && (
        <SkillsModal repoRoot={repoRoot} line={skillsLine} onClose={() => setSkillsLine(null)} />
      )}
    </>
  );
}
