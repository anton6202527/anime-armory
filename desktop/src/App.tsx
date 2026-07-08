import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { message, open } from "@tauri-apps/plugin-dialog";
import { Home } from "./pages/Home";
import { Line } from "./pages/Line";
import { Operation } from "./pages/Operation";
import { GlobalTooltip } from "./components/GlobalTooltip";
import { TopTabs, type WorkTab } from "./components/TopTabs";
import { Codicon } from "./components/Codicon";
import {
  DEFAULT_REPO,
  defaultWorkspace,
  resolveRepo,
  seedDemos,
  setAppTerminalVisible,
} from "./api";
import { useI18n, type Language } from "./i18n";
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

type FileStatusInfo = {
  root: string;
  path: string;
  name: string;
  kind: string;
  ext: string;
  size: number | null;
  dirty: boolean;
};

function formatFileBytes(value?: number | null): string {
  if (value == null) return "-";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function fileFormatLabel(file: FileStatusInfo): string {
  if (file.ext) return file.ext.toUpperCase();
  if (file.kind) return file.kind.toUpperCase();
  return "TEXT";
}

function AppStatusBar({
  activeTab,
  fileStatus,
  workspaceRoot,
}: {
  activeTab: WorkTab | null;
  fileStatus: FileStatusInfo | null;
  workspaceRoot: string;
}) {
  const { t } = useI18n();
  const hasFile = Boolean(fileStatus?.path);
  const title = activeTab?.root.name ?? t("status.home");
  const filePath = fileStatus?.path ?? "";
  return (
    <div className="statusbar">
      <div className="statusbar-left">
        <span className="statusbar-item statusbar-work" title={activeTab?.root.path ?? workspaceRoot}>
          {title}
        </span>
        {hasFile ? (
          <span className="statusbar-item statusbar-file" title={filePath}>
            {fileStatus?.dirty ? "● " : ""}
            {filePath}
          </span>
        ) : (
          <span className="statusbar-item statusbar-muted">{t("status.noFile")}</span>
        )}
      </div>
      <div className="statusbar-right">
        {hasFile && fileStatus ? (
          <>
            {fileStatus.dirty && <span className="statusbar-item statusbar-warn">{t("status.unsaved")}</span>}
            <span className="statusbar-item">{fileFormatLabel(fileStatus)}</span>
            <span className="statusbar-item">{formatFileBytes(fileStatus.size)}</span>
          </>
        ) : null}
        <button
          type="button"
          className="statusbar-button"
          title={t("status.notifications")}
          aria-label={t("status.notifications")}
        >
          <Codicon name="bell" />
          <span>0</span>
        </button>
      </div>
    </div>
  );
}

export function App() {
  const { setLanguage, t } = useI18n();
  // skills repo (runs the pipeline) — inferred live checkout on a dev machine,
  // else the bundled copy shipped inside the installed app. Separate from the works
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
  const [terminalVisible, setTerminalVisible] = useState(() => {
    return window.localStorage.getItem("aa.terminalVisible") !== "false";
  });
  const [fileStatusByRoot, setFileStatusByRoot] = useState<Record<string, FileStatusInfo | null>>({});
  const [newTerminalRequest, setNewTerminalRequest] = useState({ seq: 0, targetId: null as string | null });
  const activeIdRef = useRef<string | null>(null);
  const tabUseSeq = useRef(0);
  activeIdRef.current = activeId;

  useEffect(() => {
    installSkinPlugin();
  }, []);

  useEffect(() => {
    let alive = true;
    let unlistenLanguage: (() => void) | null = null;
    let unlistenTerminal: (() => void) | null = null;
    listen<Language>("anime-armory:set-language", (event) => {
      if (event.payload === "zh" || event.payload === "en") setLanguage(event.payload);
    })
      .then((fn) => {
        if (alive) unlistenLanguage = fn;
        else fn();
      })
      .catch((e) => console.error("menu language listener failed", e));
    listen<boolean>("anime-armory:toggle-terminal", (event) => {
      setTerminalVisible((visible) => {
        const next = typeof event.payload === "boolean" ? event.payload : !visible;
        window.localStorage.setItem("aa.terminalVisible", String(next));
        return next;
      });
    })
      .then((fn) => {
        if (alive) unlistenTerminal = fn;
        else fn();
      })
      .catch((e) => console.error("menu terminal listener failed", e));
    const unlistenNewTerminalPromise = listen("anime-armory:new-terminal", () => {
      window.localStorage.setItem("aa.terminalVisible", "true");
      setTerminalVisible(true);
      setNewTerminalRequest((request) => ({
        seq: request.seq + 1,
        targetId: activeIdRef.current,
      }));
    });
    let unlistenNewTerminal: (() => void) | null = null;
    unlistenNewTerminalPromise
      .then((fn) => {
        if (alive) unlistenNewTerminal = fn;
        else fn();
      })
      .catch((e) => console.error("menu new terminal listener failed", e));
    return () => {
      alive = false;
      unlistenLanguage?.();
      unlistenTerminal?.();
      unlistenNewTerminal?.();
    };
  }, [setLanguage]);

  useEffect(() => {
    setAppTerminalVisible(terminalVisible).catch((e) => console.error("terminal menu sync failed", e));
  }, [terminalVisible]);

  useEffect(() => {
    const onFileStatus = (event: Event) => {
      const detail = (event as CustomEvent<FileStatusInfo>).detail;
      if (!detail?.root) return;
      setFileStatusByRoot((prev) => ({
        ...prev,
        [detail.root]: detail.path ? detail : null,
      }));
    };
    window.addEventListener("anime-armory:file-status", onFileStatus);
    return () => window.removeEventListener("anime-armory:file-status", onFileStatus);
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

  // resolve the dedicated workspace on boot. seedDemos is a legacy no-op for
  // current builds because full demos are downloaded from Release assets.
  useEffect(() => {
    defaultWorkspace()
      .then(async (ws) => {
        await seedDemos(ws).catch(() => 0); // no-op only if built --no-demos
        setWorkspaceRoot(ws);
      })
      .catch((e) => console.error("workspace resolve failed", e));
  }, []);

  // when the visible layer changes, nudge a resize so the now-shown terminal /
  // canvas refits (hidden tabs stay mounted with display:none)
  useEffect(() => {
    window.dispatchEvent(new Event("resize"));
  }, [activeId, terminalVisible]);

  const pickWorkspace = useCallback(async () => {
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
  }, [repoRoot, t, workspaceRoot]);

  useEffect(() => {
    let alive = true;
    let unlistenSwitchWorkspace: (() => void) | null = null;
    listen("anime-armory:switch-workspace", () => {
      void pickWorkspace();
    })
      .then((fn) => {
        if (alive) unlistenSwitchWorkspace = fn;
        else fn();
      })
      .catch((e) => console.error("menu switch workspace listener failed", e));
    return () => {
      alive = false;
      unlistenSwitchWorkspace?.();
    };
  }, [pickWorkspace]);

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

  function replaceWorkRoot(oldId: string, line: LineInfo, root: WorkRoot) {
    const lastUsedAt = nextTabUse();
    setTabs((prev) =>
      capTabsByLru(
        prev.map((tab) =>
          tab.id === oldId ? { ...tab, id: root.path, line, root, lastUsedAt } : tab,
        ),
      ),
    );
    setActiveId((current) => (current === oldId ? root.path : current));
  }

  if (!workspaceRoot) {
    return <div className="home"><h1>{t("app.name")}</h1><div className="empty">{t("app.initWorkspace")}</div></div>;
  }

  const activeTab = activeId ? tabs.find((tab) => tab.id === activeId) ?? null : null;
  const activeFileStatus = activeId ? fileStatusByRoot[activeId] ?? null : null;

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
              onShowSkills={(line) => setSkillsLine(line)}
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
              terminalVisible={terminalVisible}
              newTerminalRequestSeq={newTerminalRequest.seq}
              newTerminalRequestTargetId={newTerminalRequest.targetId}
              onRootChanged={(root) => replaceWorkRoot(t.id, t.line, root)}
              onCloseTerminal={() => {
                window.localStorage.setItem("aa.terminalVisible", "false");
                setTerminalVisible(false);
              }}
              onToggleTerminal={() => {
                setTerminalVisible((visible) => {
                  const next = !visible;
                  window.localStorage.setItem("aa.terminalVisible", String(next));
                  return next;
                });
              }}
              onBack={() => {
                setActiveId(null);
                setHomeRoute({ kind: "line", line: t.line });
              }}
            />
          </div>
        ))}
      </div>

      <AppStatusBar activeTab={activeTab} fileStatus={activeFileStatus} workspaceRoot={workspaceRoot} />

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
      <GlobalTooltip />
    </div>
  );
}
