import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { message, open } from "@tauri-apps/plugin-dialog";
import { Home } from "./pages/Home";
import { Line } from "./pages/Line";
import { Operation } from "./pages/Operation";
import { TopTabs, type WorkTab } from "./components/TopTabs";
import {
  DEFAULT_REPO,
  defaultWorkspace,
  ensureMedia,
  mediaAllowRoot,
  preparePermissions,
  resolveRepo,
  seedDemos,
} from "./api";
import { useI18n } from "./i18n";
import { installSkinPlugin } from "./skins";
import type { LineInfo, WorkRoot } from "./types";

// The non-tab "home" area: the line picker, or one line's works list.
type HomeRoute = { kind: "home" } | { kind: "line"; line: LineInfo };
const MAX_WORK_TABS = 5;
const SkillsModal = lazy(() =>
  import("./components/SkillsModal").then((mod) => ({ default: mod.SkillsModal })),
);

/** True if two paths are equal or one contains the other (string-level guard;
 *  the Rust side does the symlink-resolving authoritative check). */
function pathsOverlap(a: string, b: string): boolean {
  if (!a || !b) return false;
  const norm = (p: string) => p.replace(/\/+$/, "");
  const x = norm(a);
  const y = norm(b);
  return x === y || x.startsWith(y + "/") || y.startsWith(x + "/");
}

function capTabsByLru(tabs: WorkTab[]): WorkTab[] {
  if (tabs.length <= MAX_WORK_TABS) return tabs;
  const drop = new Set(
    [...tabs]
      .sort((a, b) => a.lastUsedAt - b.lastUsedAt)
      .slice(0, tabs.length - MAX_WORK_TABS)
      .map((tab) => tab.id),
  );
  return tabs.filter((tab) => !drop.has(tab.id));
}

export function App() {
  const { t } = useI18n();
  // skills repo (runs the pipeline) — live checkout on a dev machine, else the
  // /tod-bundled copy shipped inside the installed app. Separate from the works
  // workspace. Falls back to DEFAULT_REPO until resolve_repo answers.
  const [repoRoot, setRepoRoot] = useState<string>(DEFAULT_REPO);
  // works workspace (~/AnimeArmory) — app creates/deletes works here only
  const [workspaceRoot, setWorkspaceRoot] = useState<string>("");
  // non-tab navigation (line picker ↔ a line's works list)
  const [homeRoute, setHomeRoute] = useState<HomeRoute>({ kind: "home" });
  // opened creation windows, one tab each (kept mounted to preserve PTY/canvas)
  const [tabs, setTabs] = useState<WorkTab[]>([]);
  // active tab id, or null = show the home area
  const [activeId, setActiveId] = useState<string | null>(null);
  const [skillsLine, setSkillsLine] = useState<LineInfo | null>(null);
  const tabUseSeq = useRef(0);
  const permissionPrepKeyRef = useRef("");

  useEffect(() => {
    installSkinPlugin();
  }, []);

  function nextTabUse() {
    tabUseSeq.current += 1;
    return tabUseSeq.current;
  }

  // resolve the skills repo (dev checkout vs bundled) on boot
  useEffect(() => {
    resolveRepo(DEFAULT_REPO)
      .then((r) => r && setRepoRoot(r))
      .catch((e) => console.error("repo resolve failed", e));
  }, []);

  // resolve the dedicated workspace on boot, then seed each line's champion
  // sample (on by default; re-adds any missing one, never clobbers user work)
  useEffect(() => {
    defaultWorkspace()
      .then((ws) => {
        setWorkspaceRoot(ws);
        seedDemos(ws).catch(() => {}); // no-op only if built --no-demos
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

  // macOS privacy prompts cannot be granted by a DMG installer. Concentrate the
  // required probes at first launch so the user is not interrupted mid-workflow.
  useEffect(() => {
    if (!workspaceRoot) return;
    const key = `aa.permissionPrep.v1:${workspaceRoot}`;
    if (permissionPrepKeyRef.current === key || window.localStorage.getItem(key) === "done") return;
    permissionPrepKeyRef.current = key;

    message(t("app.permissionPrepMessage"), {
      title: t("app.permissionPrepTitle"),
      kind: "info",
    })
      .then(() => preparePermissions(workspaceRoot))
      .then((result) => {
        window.localStorage.setItem(key, "done");
        const failed = result.probes.filter((probe) => !probe.ok);
        if (failed.length === 0) return;
        const items = failed
          .map((probe) => `${probe.label}: ${probe.path || probe.error}`)
          .join("\n");
        return message(t("app.permissionPrepPartialMessage", { items }), {
          title: t("app.permissionPrepPartialTitle"),
          kind: "warning",
        });
      })
      .catch(() => {
        window.localStorage.setItem(key, "done");
      });
  }, [workspaceRoot, t]);

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
          t("app.workspaceBlockedMessage"),
          { title: t("app.workspaceBlockedTitle"), kind: "error" },
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
    const lastUsedAt = nextTabUse();
    setTabs((prev) => {
      const exists = prev.some((tab) => tab.id === id);
      const next = exists
        ? prev.map((tab) => (tab.id === id ? { ...tab, line, root, lastUsedAt } : tab))
        : [...prev, { id, line, root, lastUsedAt }];
      return capTabsByLru(next);
    });
    setActiveId(id);
  }

  function selectTab(id: string) {
    const lastUsedAt = nextTabUse();
    setTabs((prev) => prev.map((tab) => (tab.id === id ? { ...tab, lastUsedAt } : tab)));
    setActiveId(id);
  }

  // close a tab; if it was active, fall back to a neighbor tab, else Home
  function closeTab(id: string) {
    setTabs((prev) => {
      const idx = prev.findIndex((t) => t.id === id);
      const next = prev.filter((t) => t.id !== id);
      setActiveId((current) => {
        if (current !== id) return current;
        const neighbor = next[idx] ?? next[idx - 1] ?? null;
        return neighbor ? neighbor.id : null;
      });
      return next;
    });
  }

  if (!workspaceRoot) {
    return <div className="home"><h1>AnimeArmory</h1><div className="empty">{t("app.initWorkspace")}</div></div>;
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
        onSelect={selectTab}
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
              onDeleted={(root) => closeTab(root.path)}
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
              active={activeId === t.id}
              onBack={() => {
                setActiveId(null);
                setHomeRoute({ kind: "line", line: t.line });
              }}
            />
          </div>
        ))}
      </div>

      {skillsLine && (
        <Suspense fallback={null}>
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
        </Suspense>
      )}
    </div>
  );
}
