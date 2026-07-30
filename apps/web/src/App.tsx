import { useEffect, useState } from "react";
import { isAuthConfigured, isCloudConfigured, persistWorkToCloud } from "./lib/cloud";
import { signInOrSignUpWithEmail, subscribeToAuthState, type AuthUser } from "./lib/auth";
import { registerLocalFiles, removeLocalFiles } from "./lib/localFiles";
import { loadWork, removeWork, saveWork, workStorageKey } from "./lib/work";
import { applyTheme, loadTheme, type ThemeMode } from "./lib/theme";
import { BrandIcon } from "./components/BrandIcon";
import { AuthDialog } from "./features/account/AuthDialog";
import { CanvasPage } from "./features/canvas/CanvasPage";
import { SkillHomePage } from "./features/skill-home/SkillHomePage";
import { removeLocalCanvasDocument, restoreCloudWork } from "./lib/canvasState";
import type { PendingAttachment, WebWork } from "./types";

interface CanvasRoute {
  projectId: string;
  spaceId: string;
  guideSource: string;
  legacy: boolean;
}

function readCanvasRoute(): CanvasRoute | null {
  const legacyProjectId = window.location.pathname.match(/^\/work\/([^/]+)\/?$/)?.[1];
  if (legacyProjectId) {
    return { projectId: legacyProjectId, spaceId: "personal", guideSource: "skill", legacy: true };
  }
  if (!/^\/canvas\/?$/.test(window.location.pathname)) return null;
  const params = new URLSearchParams(window.location.search);
  const projectId = params.get("projectId")?.trim();
  if (!projectId) return null;
  return {
    projectId,
    spaceId: params.get("spaceId")?.trim() || "personal",
    guideSource: params.get("guideSource")?.trim() || "skill",
    legacy: false,
  };
}

function canvasUrl(projectId: string, spaceId: string, guideSource = "skill") {
  const params = new URLSearchParams({ guideSource, spaceId, projectId });
  return `/canvas?${params.toString()}`;
}

export function App() {
  const [theme, setTheme] = useState<ThemeMode>(loadTheme);
  const [pendingCreation, setPendingCreation] = useState<{ work: WebWork; attachments: PendingAttachment[] } | null>(null);
  const [creationLoginOpen, setCreationLoginOpen] = useState(false);
  const [canvasAuth, setCanvasAuth] = useState<{ ready: boolean; configured: boolean; user: AuthUser | null }>({
    ready: false,
    configured: isAuthConfigured(),
    user: null,
  });
  const [canvasRoute, setCanvasRoute] = useState<CanvasRoute | null>(readCanvasRoute);
  const [routeLoading, setRouteLoading] = useState(false);
  const [routeError, setRouteError] = useState("");
  const [work, setWork] = useState<WebWork | null>(() => {
    const route = readCanvasRoute();
    return route ? loadWork(route.projectId) : null;
  });

  useEffect(() => {
    const onPopState = () => {
      const route = readCanvasRoute();
      setCanvasRoute(route);
      setRouteError("");
      setWork(route ? loadWork(route.projectId) : null);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      const id = readCanvasRoute()?.projectId;
      if (!id || (event.key && event.key !== workStorageKey(id))) return;
      setWork(loadWork(id));
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  useEffect(() => applyTheme(theme), [theme]);

  useEffect(() => subscribeToAuthState(({ configured, user }) => {
    setCanvasAuth({ ready: true, configured, user });
  }), []);

  useEffect(() => {
    if (!canvasRoute?.legacy || !canvasAuth.ready || !canvasAuth.user) return;
    const spaceId = canvasAuth.user.id;
    const nextUrl = canvasUrl(canvasRoute.projectId, spaceId, canvasRoute.guideSource);
    window.history.replaceState({}, "", nextUrl);
    setCanvasRoute({ ...canvasRoute, spaceId, legacy: false });
  }, [canvasAuth.ready, canvasAuth.user, canvasRoute]);

  useEffect(() => {
    if (!canvasRoute || work || !canvasAuth.ready || !canvasAuth.user) return;
    let disposed = false;
    setRouteLoading(true);
    setRouteError("");
    void restoreCloudWork(canvasRoute.projectId)
      .then((restored) => {
        if (disposed) return;
        if (!restored) {
          setRouteError("没有找到这个作品，或当前账号没有访问权限。");
          return;
        }
        saveWork(restored);
        setWork(restored);
        if (restored.id !== canvasRoute.projectId) {
          const nextRoute = { ...canvasRoute, projectId: restored.id };
          window.history.replaceState({}, "", canvasUrl(nextRoute.projectId, nextRoute.spaceId, nextRoute.guideSource));
          setCanvasRoute(nextRoute);
        }
      })
      .catch((error) => {
        if (!disposed) setRouteError(error instanceof Error ? error.message : String(error));
      })
      .finally(() => {
        if (!disposed) setRouteLoading(false);
      });
    return () => { disposed = true; };
  }, [canvasAuth.ready, canvasAuth.user, canvasRoute, work]);

  function openAuthenticatedWork(nextWork: WebWork, attachments: PendingAttachment[]) {
    registerLocalFiles(attachments);
    const initialWork: WebWork = {
      ...nextWork,
      cloudState: isCloudConfigured() ? "syncing" : "local",
    };
    saveWork(initialWork);
    const spaceId = canvasAuth.user?.id ?? "personal";
    const workUrl = canvasUrl(initialWork.id, spaceId, "skill");
    const opened = window.open(workUrl, "_blank");
    if (opened) opened.opener = null;
    if (!opened) {
      window.history.pushState({}, "", workUrl);
      setCanvasRoute({ projectId: initialWork.id, spaceId, guideSource: "skill", legacy: false });
      setWork(initialWork);
    }
    void persistWorkToCloud(initialWork, attachments)
      .then(({ work: syncedWork }) => {
        saveWork(syncedWork);
        if (!opened) setWork((current) => current?.id === syncedWork.id ? syncedWork : current);
      })
      .catch((error) => {
        const failedWork: WebWork = {
          ...initialWork,
          cloudState: "failed",
          cloudError: String(error),
        };
        saveWork(failedWork);
        if (!opened) setWork((current) => current?.id === failedWork.id ? failedWork : current);
      });
  }

  function openWork(nextWork: WebWork, attachments: PendingAttachment[]) {
    if (!canvasAuth.user) {
      setPendingCreation({ work: nextWork, attachments });
      setCreationLoginOpen(true);
      return;
    }
    openAuthenticatedWork(nextWork, attachments);
  }

  async function authenticate(email: string, password: string) {
    const result = await signInOrSignUpWithEmail({ email, password });
    if (!result.session) throw new Error("登录服务未返回有效会话，请检查邮箱登录配置。");
  }

  async function authenticatePendingCreation(email: string, password: string) {
    await authenticate(email, password);
    const pending = pendingCreation;
    setCreationLoginOpen(false);
    setPendingCreation(null);
    if (pending) openAuthenticatedWork(pending.work, pending.attachments);
    return { message: "登录成功" };
  }

  function openHome() {
    window.history.pushState({}, "", "/");
    setCanvasRoute(null);
    setRouteError("");
    setWork(null);
  }

  function clearCurrentWork(attachmentIds: string[]) {
    if (!work) return;
    removeLocalCanvasDocument(work.id);
    removeWork(work.id);
    void removeLocalFiles(attachmentIds);
    window.history.replaceState({}, "", "/");
    setCanvasRoute(null);
    setRouteError("");
    setWork(null);
  }

  if (canvasRoute && !canvasAuth.ready) return <main className="canvas-auth-gate" aria-label="正在确认登录状态" />;
  if (canvasRoute && !canvasAuth.user) {
    return (
      <main className="canvas-auth-gate">
        <AuthDialog
          open
          configured={canvasAuth.configured}
          onClose={openHome}
          onContinue={async (email, password) => {
            await authenticate(email, password);
            return { message: "登录成功" };
          }}
        />
      </main>
    );
  }
  if (canvasRoute && !work) {
    return (
      <main className="canvas-auth-gate">
        <section className="canvas-route-state" role={routeError ? "alert" : "status"}>
          <BrandIcon />
          <strong>{routeError ? "无法打开作品" : "正在载入画布"}</strong>
          <p>{routeError || (routeLoading ? "正在从 Supabase 恢复项目与画布状态…" : "正在准备项目…")}</p>
          {routeError && <button type="button" onClick={openHome}>返回首页</button>}
        </section>
      </main>
    );
  }
  if (work) return <CanvasPage work={work} onHome={openHome} onClearLocalData={clearCurrentWork} />;
  return (
    <>
      <SkillHomePage onCreate={openWork} theme={theme} onThemeChange={setTheme} />
      <AuthDialog
        open={creationLoginOpen}
        configured={canvasAuth.configured}
        onClose={() => {
          setCreationLoginOpen(false);
          setPendingCreation(null);
        }}
        onContinue={authenticatePendingCreation}
      />
    </>
  );
}
