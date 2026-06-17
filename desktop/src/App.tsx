import { useEffect, useState } from "react";
import { message, open } from "@tauri-apps/plugin-dialog";
import { Home } from "./pages/Home";
import { Line } from "./pages/Line";
import { Operation } from "./pages/Operation";
import { SkillsModal } from "./components/SkillsModal";
import { TopTabs, type WorkTab } from "./components/TopTabs";
import { DEFAULT_REPO, defaultWorkspace, ensureMedia, mediaAllowRoot, resolveRepo, seedDemos } from "./api";
import type { LineInfo, WorkRoot } from "./types";

// The non-tab "home" area: the line picker, or one line's works list.
type HomeRoute = { kind: "home" } | { kind: "line"; line: LineInfo };

/** True if two paths are equal or one contains the other (string-level guard;
 *  the Rust side does the symlink-resolving authoritative check). */
function pathsOverlap(a: string, b: string): boolean {
  if (!a || !b) return false;
  const norm = (p: string) => p.replace(/\/+$/, "");
  const x = norm(a);
  const y = norm(b);
  return x === y || x.startsWith(y + "/") || y.startsWith(x + "/");
}

export function App() {
  // skills repo (runs the pipeline) — live checkout on a dev machine, else the
  // /tod-bundled copy shipped inside the installed app. Separate from the works
  // workspace. Falls back to DEFAULT_REPO until resolve_repo answers.
  const [repoRoot, setRepoRoot] = useState<string>(DEFAULT_REPO);
  // works workspace (~/AnimeArsenal) — app creates/deletes works here only
  const [workspaceRoot, setWorkspaceRoot] = useState<string>("");
  // non-tab navigation (line picker ↔ a line's works list)
  const [homeRoute, setHomeRoute] = useState<HomeRoute>({ kind: "home" });
  // opened creation windows, one tab each (kept mounted to preserve PTY/canvas)
  const [tabs, setTabs] = useState<WorkTab[]>([]);
  // active tab id, or null = show the home area
  const [activeId, setActiveId] = useState<string | null>(null);
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

  // when the visible layer changes, nudge a resize so the now-shown terminal /
  // canvas refits (hidden tabs stay mounted with display:none)
  useEffect(() => {
    window.dispatchEvent(new Event("resize"));
  }, [activeId]);

  async function pickWorkspace() {
    const picked = await open({ directory: true, multiple: false, defaultPath: workspaceRoot });
    if (typeof picked === "string") {
      // Complete isolation: the works workspace must never overlap the project
      // repo, or app create/delete would mutate the repo's demos. (The Rust
      // commands also hard-block repo paths; this stops the mistake earlier.)
      if (pathsOverlap(picked, repoRoot)) {
        await message(
          "该目录与项目仓库重叠，已拒绝。\n请选择仓库之外的目录作为作品工作区（作品与项目仓库需完全隔离）。",
          { title: "无法选择该工作区", kind: "error" },
        );
        return;
      }
      setWorkspaceRoot(picked);
      setHomeRoute({ kind: "home" });
      setActiveId(null);
    }
  }

  // open (or focus) a work as a top-bar tab
  function openWork(line: LineInfo, root: WorkRoot) {
    const id = root.path;
    setTabs((prev) => (prev.some((t) => t.id === id) ? prev : [...prev, { id, line, root }]));
    setActiveId(id);
  }

  // close a tab; if it was active, fall back to a neighbor tab, else Home
  function closeTab(id: string) {
    setTabs((prev) => {
      const idx = prev.findIndex((t) => t.id === id);
      const next = prev.filter((t) => t.id !== id);
      if (activeId === id) {
        const neighbor = next[idx] ?? next[idx - 1] ?? null;
        setActiveId(neighbor ? neighbor.id : null);
      }
      return next;
    });
  }

  if (!workspaceRoot) {
    return <div className="home"><h1>Anime Arsenal</h1><div className="empty">初始化工作区…</div></div>;
  }

  return (
    <div className="app-shell">
      <TopTabs
        tabs={tabs}
        activeId={activeId}
        onHome={() => {
          setActiveId(null);
          setHomeRoute({ kind: "home" });
        }}
        onSelect={(id) => setActiveId(id)}
        onClose={closeTab}
      />

      <div className="app-body">
        {/* Home area (line picker ↔ a line's works list), shown when no tab active */}
        <div className="layer" style={{ display: activeId === null ? "block" : "none" }}>
          {homeRoute.kind === "line" ? (
            <Line
              workspaceRoot={workspaceRoot}
              repoRoot={repoRoot}
              line={homeRoute.line}
              onBack={() => setHomeRoute({ kind: "home" })}
              onOpen={(root) => openWork(homeRoute.line, root)}
            />
          ) : (
            <Home
              workspaceRoot={workspaceRoot}
              onPickWorkspace={pickWorkspace}
              onShowSkills={(line) => setSkillsLine(line)}
              onEnter={(line) => setHomeRoute({ kind: "line", line })}
            />
          )}
        </div>

        {/* Each opened work stays mounted; only the active one is visible. */}
        {tabs.map((t) => (
          <div className="layer" key={t.id} style={{ display: activeId === t.id ? "block" : "none" }}>
            <Operation
              repoRoot={repoRoot}
              line={t.line}
              root={t.root}
              onBack={() => {
                setActiveId(null);
                setHomeRoute({ kind: "line", line: t.line });
              }}
            />
          </div>
        ))}
      </div>

      {skillsLine && (
        <SkillsModal
          repoRoot={repoRoot}
          line={skillsLine}
          onClose={() => setSkillsLine(null)}
          onEnter={(line) => {
            setSkillsLine(null);
            setActiveId(null);
            setHomeRoute({ kind: "line", line });
          }}
        />
      )}
    </div>
  );
}
