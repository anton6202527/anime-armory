import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { isMacPlatform, onAppEvent } from "./platform/bridge";
import { Home } from "./pages/Home";
import { Line } from "./pages/Line";
import { Operation } from "./pages/Operation";
import { GlobalTooltip } from "./components/GlobalTooltip";
import { BreadcrumbHomeIcon } from "./components/BreadcrumbHomeIcon";
import {
  DEFAULT_REPO,
  createWork,
  defaultWorkspace,
  pickDirectory,
  resolveRepo,
  seedDemos,
  setAppRecentWorks,
  setAppTerminalVisible,
} from "./api";
import { plainLineLabel, useI18n, useLineLabel, type Language } from "./i18n";
import { installSkinPlugin } from "./skins";
import type { LineInfo, WorkRoot } from "./types";

// The non-tab "home" area: the line picker, or one line's works list.
type HomeRoute = { kind: "home" } | { kind: "line"; line: LineInfo };
const MAX_RECENT_WORKS = 4;
const RECENT_WORKS_STORAGE_KEY = "aa.recentWorks";
const NOVEL_ATTACHMENT_EXTENSIONS = new Set(["txt", "md", "markdown", "mdx", "docx", "pdf"]);
const SkillsModal = lazy(() =>
  import("./components/SkillsModal").then((mod) => ({ default: mod.SkillsModal })),
);

function localFileName(path: string): string {
  return path.split(/[\\/]/).filter(Boolean).pop() ?? "";
}

function cleanWorkName(value: string): string {
  return value
    .replace(/[\\/:*?"<>|]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/[. ]+$/g, "")
    .slice(0, 40);
}

function novelTitleFromAttachments(attachments: string[]): string {
  for (const path of attachments) {
    const name = localFileName(path);
    const dot = name.lastIndexOf(".");
    if (dot <= 0) continue;
    const extension = name.slice(dot + 1).toLowerCase();
    if (!NOVEL_ATTACHMENT_EXTENSIONS.has(extension)) continue;
    const title = cleanWorkName(name.slice(0, dot));
    if (title) return title;
  }
  return "";
}

function workNameFromPrompt(prompt: string): string {
  const cleanPrompt = prompt.trim();
  if (!cleanPrompt) return "";

  const bookTitle = cleanPrompt.match(/[《「『“]([^》」』”\n]{1,40})[》」』”]/)?.[1];
  if (bookTitle) return cleanWorkName(bookTitle);
  const quotedTitle = cleanPrompt.match(/["']([^"'\n]{1,40})["']/)?.[1];
  if (quotedTitle) return cleanWorkName(quotedTitle);

  const firstLine = cleanPrompt.split(/\r?\n/).map((line) => line.trim()).find(Boolean) ?? "";
  const firstSentence = firstLine.split(/[。！？!?]/, 1)[0]?.trim() ?? "";
  const adaptationSource = firstSentence.match(/^(.{1,30}?)(?:制作|改编|做|画)成(?:一部|一个)?/)?.[1]
    ?.replace(/^(?:请|麻烦|帮我|帮忙|开始)/, "")
    .trim();
  if (adaptationSource) return cleanWorkName(adaptationSource);

  return cleanWorkName(
    firstSentence
      .replace(/^(?:请|麻烦|帮我|帮忙)/, "")
      .replace(/^开始/, "")
      .trim(),
  );
}

function hubWorkBaseName(prompt: string, attachments: string[]): string {
  return novelTitleFromAttachments(attachments) || workNameFromPrompt(prompt) || "unnamed";
}

function isDuplicateWorkError(error: unknown): boolean {
  const message = String(error).toLowerCase();
  return message.includes("同名作品已存在") || message.includes("already exists") || message.includes("eexist");
}

/** True if two paths are equal or one contains the other (string-level guard;
 *  the Rust side does the symlink-resolving authoritative check). */
function pathsOverlap(a: string, b: string): boolean {
  if (!a || !b) return false;
  const norm = (p: string) => p.replace(/\/+$/, "");
  const x = norm(a);
  const y = norm(b);
  return x === y || x.startsWith(y + "/") || y.startsWith(x + "/");
}

type RecentWork = {
  line: Pick<LineInfo, "line" | "label" | "dir" | "view">;
  root: WorkRoot;
};

function isRecentWork(value: unknown): value is RecentWork {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<RecentWork>;
  const line = item.line as Partial<RecentWork["line"]> | undefined;
  const root = item.root as Partial<WorkRoot> | undefined;
  return Boolean(
    line &&
      typeof line.line === "string" &&
      typeof line.label === "string" &&
      typeof line.dir === "string" &&
      (line.view === "canvas" || line.view === "files" || line.view === "audio") &&
      root &&
      typeof root.name === "string" &&
      typeof root.path === "string" &&
      typeof root.has_progress === "boolean" &&
      typeof root.is_demo === "boolean",
  );
}

function readRecentWorks(): RecentWork[] {
  try {
    const parsed: unknown = JSON.parse(window.localStorage.getItem(RECENT_WORKS_STORAGE_KEY) ?? "[]");
    if (!Array.isArray(parsed)) return [];
    const seen = new Set<string>();
    return parsed
      .filter(isRecentWork)
      .filter((work) => {
        if (!work.root.path || seen.has(work.root.path)) return false;
        seen.add(work.root.path);
        return true;
      })
      .slice(0, MAX_RECENT_WORKS);
  } catch {
    return [];
  }
}

function makeRecentWork(line: LineInfo, root: WorkRoot): RecentWork {
  return {
    line: { line: line.line, label: line.label, dir: line.dir, view: line.view },
    root,
  };
}

function lineFromRecent(work: RecentWork): LineInfo {
  return { ...work.line, roots: [work.root] };
}

type OpenWork = {
  id: string;
  line: LineInfo;
  root: WorkRoot;
  initialPrompt?: string;
};

export function App() {
  const { setLanguage, t } = useI18n();
  const lineLabel = useLineLabel();
  // skills repo (runs the pipeline) — inferred live checkout on a dev machine,
  // else the bundled copy shipped inside the installed app. Separate from the works
  // workspace. Falls back to DEFAULT_REPO until resolve_repo answers.
  const [repoRoot, setRepoRoot] = useState<string>(DEFAULT_REPO);
  // Dedicated LabuTV works workspace — app creates/deletes works here only.
  const [workspaceRoot, setWorkspaceRoot] = useState<string>("");
  // non-tab navigation (line picker ↔ a line's works list)
  const [homeRoute, setHomeRoute] = useState<HomeRoute>({ kind: "home" });
  // One active work at a time. Previously opened works live in the native
  // File > Recent Projects menu instead of remaining mounted as top tabs.
  const [activeWork, setActiveWork] = useState<OpenWork | null>(null);
  const [recentWorks, setRecentWorks] = useState<RecentWork[]>(readRecentWorks);
  const activeId = activeWork?.id ?? null;
  const [skillsLine, setSkillsLine] = useState<LineInfo | null>(null);
  const [terminalVisible, setTerminalVisible] = useState(() => {
    return window.localStorage.getItem("aa.terminalVisible") !== "false";
  });
  const [newTerminalRequest, setNewTerminalRequest] = useState({ seq: 0, targetId: null as string | null });
  const activeIdRef = useRef<string | null>(null);
  const recentWorksRef = useRef(recentWorks);
  activeIdRef.current = activeId;
  recentWorksRef.current = recentWorks;

  useEffect(() => {
    installSkinPlugin();
  }, []);

  useEffect(() => {
    const unlistenLanguage = onAppEvent("app:set-language", (payload) => {
      if (payload === "zh" || payload === "en") setLanguage(payload as Language);
    });
    const unlistenTerminal = onAppEvent("app:toggle-terminal", (payload) => {
      setTerminalVisible((visible) => {
        const next = typeof payload === "boolean" ? payload : !visible;
        window.localStorage.setItem("aa.terminalVisible", String(next));
        return next;
      });
    });
    const unlistenNewTerminal = onAppEvent("app:new-terminal", () => {
      window.localStorage.setItem("aa.terminalVisible", "true");
      setTerminalVisible(true);
      setNewTerminalRequest((request) => ({
        seq: request.seq + 1,
        targetId: activeIdRef.current,
      }));
    });
    return () => {
      unlistenLanguage();
      unlistenTerminal();
      unlistenNewTerminal();
    };
  }, [setLanguage]);

  useEffect(() => {
    setAppTerminalVisible(terminalVisible).catch((e) => console.error("terminal menu sync failed", e));
  }, [terminalVisible]);

  useEffect(() => {
    window.localStorage.setItem(RECENT_WORKS_STORAGE_KEY, JSON.stringify(recentWorks));
    setAppRecentWorks(recentWorks.map((work) => ({ path: work.root.path, name: work.root.name }))).catch((e) =>
      console.error("recent works menu sync failed", e),
    );
  }, [recentWorks]);

  useEffect(() => {
    return onAppEvent("app:open-recent-work", (path) => {
      const work = recentWorksRef.current.find((item) => item.root.path === path);
      if (work) openWork(lineFromRecent(work), work.root);
    });
  }, []);

  function rememberWork(line: LineInfo, root: WorkRoot) {
    setRecentWorks((prev) => [
      makeRecentWork(line, root),
      ...prev.filter((work) => work.root.path !== root.path),
    ].slice(0, MAX_RECENT_WORKS));
  }

  function forgetWork(path: string) {
    setRecentWorks((prev) => prev.filter((work) => work.root.path !== path));
  }

  // resolve the skills repo (dev checkout vs bundled) on boot
  useEffect(() => {
    resolveRepo(DEFAULT_REPO)
      .then((r) => r && setRepoRoot(r))
      .catch((e) => console.error("repo resolve failed", e));
  }, []);

  // Resolve the dedicated workspace on boot. seedDemos is a legacy no-op for
  // current builds because full demos are downloaded from Cloudflare R2.
  useEffect(() => {
    defaultWorkspace()
      .then(async (ws) => {
        await seedDemos(ws).catch(() => 0); // no-op only if built --no-demos
        setWorkspaceRoot(ws);
      })
      .catch((e) => console.error("workspace resolve failed", e));
  }, []);

  // When navigation or terminal visibility changes, nudge a resize so the
  // newly shown terminal/canvas refits.
  useEffect(() => {
    window.dispatchEvent(new Event("resize"));
  }, [activeId, terminalVisible]);

  const pickWorkspace = useCallback(async () => {
    const picked = await pickDirectory();
    if (typeof picked === "string" && picked) {
      // Complete isolation: the works workspace must never overlap the project
      // repo, or app create/delete would mutate the repo's demos. (The main
      // process also hard-blocks repo paths; this stops the mistake earlier.)
      if (pathsOverlap(picked, repoRoot)) {
        window.alert(`${t("app.workspaceBlockedTitle")}\n${t("app.workspaceBlockedMessage")}`);
        return;
      }
      setWorkspaceRoot(picked);
      setHomeRoute({ kind: "home" });
      setActiveWork(null);
    }
  }, [repoRoot, t]);

  useEffect(() => {
    return onAppEvent("app:switch-workspace", () => {
      void pickWorkspace();
    });
  }, [pickWorkspace]);

  // Opening another work replaces the current work. The previous one remains
  // available from the native recent-projects menu.
  function openWork(line: LineInfo, root: WorkRoot, initialPrompt?: string) {
    setActiveWork({ id: root.path, line, root, initialPrompt });
    rememberWork(line, root);
  }

  async function startFromHub(line: LineInfo, prompt: string, attachments: string[]) {
    const cleanPrompt = prompt.trim();
    if (!cleanPrompt && attachments.length === 0) return;
    const baseName = hubWorkBaseName(cleanPrompt, attachments);
    let root: WorkRoot | null = null;
    try {
      for (let index = 1; index <= 999; index += 1) {
        const name = index === 1 ? baseName : `${baseName} (${index})`;
        try {
          const path = await createWork(line.dir, repoRoot, name);
          root = { name, path, has_progress: false, is_demo: false };
          break;
        } catch (error) {
          if (isDuplicateWorkError(error)) continue;
          throw error;
        }
      }
      if (!root) throw new Error("无法生成不重复的作品名称");
    } catch (error) {
      console.error("hub create work failed", error);
      setHomeRoute({ kind: "line", line });
      return;
    }
    const routedPrompt = [
      `请使用 ${line.line} 处理当前作品中的以下需求。`,
      "先读取 _进度.md 与 _设置.md，遵循本线状态机、选择点、适配层和 gate。",
      "",
      cleanPrompt || "请结合用户附加的文件开始创作。",
      ...(attachments.length > 0 ? [
        "",
        "用户从首页附加了以下本地文件：",
        ...attachments.map((path) => `- ${path}`),
        "请先检查这些文件，并按所选创作线的约定将需要的素材导入当前作品后再继续。",
      ] : []),
    ].join("\n");
    window.localStorage.setItem("aa.terminalVisible", "true");
    setTerminalVisible(true);
    openWork(line, root, routedPrompt);
  }

  function closeWork(id: string) {
    setActiveWork((current) => (current?.id === id ? null : current));
  }

  function replaceWorkRoot(oldId: string, line: LineInfo, root: WorkRoot) {
    setActiveWork((current) =>
      current?.id === oldId ? { id: root.path, line, root } : current,
    );
    setRecentWorks((prev) => [
      makeRecentWork(line, root),
      ...prev.filter((work) => work.root.path !== oldId && work.root.path !== root.path),
    ].slice(0, MAX_RECENT_WORKS));
  }

  if (!workspaceRoot) {
    return <div className="home"><h1>{t("app.name")}</h1><div className="empty">{t("app.initWorkspace")}</div></div>;
  }


  return (
    <div className="app-shell">
      {!activeWork && (
        <div className={"window-titlebar" + (isMacPlatform ? " window-titlebar-mac" : "") + (homeRoute.kind === "home" ? " window-titlebar-hub" : "")}>
          {homeRoute.kind === "line" && (
            <>
              <button
                type="button"
                className="crumb-btn crumb-home-btn"
                title={t("common.home")}
                aria-label={t("common.home")}
                onClick={() => setHomeRoute({ kind: "home" })}
              >
                <BreadcrumbHomeIcon />
              </button>
              <span className="crumb-sep">/</span>
              <span className="crumb current"><b>{plainLineLabel(lineLabel(homeRoute.line))}</b></span>
            </>
          )}
        </div>
      )}

      <div className="app-body">
        {/* Home area (line picker ↔ a line's works list), shown when no work is open. */}
        <div className="layer" style={{ display: activeId === null ? "block" : "none" }}>
          {homeRoute.kind === "line" ? (
            <Line
              workspaceRoot={workspaceRoot}
              repoRoot={repoRoot}
              line={homeRoute.line}
              onOpen={(root) => openWork(homeRoute.line, root)}
              onDeleted={(root) => {
                closeWork(root.path);
                forgetWork(root.path);
              }}
            />
          ) : (
            <Home
              workspaceRoot={workspaceRoot}
              onPickWorkspace={pickWorkspace}
              onShowSkills={(line) => setSkillsLine(line)}
              onEnter={(line) => setHomeRoute({ kind: "line", line })}
              onStart={startFromHub}
            />
          )}
        </div>

        {activeWork && (
          <div className="layer" key={activeWork.id}>
            <Operation
              repoRoot={repoRoot}
              line={activeWork.line}
              root={activeWork.root}
              active
              terminalVisible={terminalVisible}
              newTerminalRequestSeq={newTerminalRequest.seq}
              newTerminalRequestTargetId={newTerminalRequest.targetId}
              initialPrompt={activeWork.initialPrompt}
              onRootChanged={(root) => replaceWorkRoot(activeWork.id, activeWork.line, root)}
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
              onShowSkills={(line) => setSkillsLine(line)}
              onHome={() => {
                setActiveWork(null);
                setHomeRoute({ kind: "home" });
              }}
              onBack={() => {
                setActiveWork(null);
                setHomeRoute({ kind: "line", line: activeWork.line });
              }}
            />
          </div>
        )}
      </div>

      {skillsLine && (
        <Suspense fallback={null}>
          <SkillsModal
            repoRoot={repoRoot}
            line={skillsLine}
            onClose={() => setSkillsLine(null)}
          />
        </Suspense>
      )}
      <GlobalTooltip />
    </div>
  );
}
