import { useEffect, useState } from "react";
import { isCloudConfigured, persistWorkToCloud } from "./lib/cloud";
import { registerLocalFiles } from "./lib/localFiles";
import { loadWork, saveWork, workStorageKey } from "./lib/work";
import { applyTheme, loadTheme, type ThemeMode } from "./lib/theme";
import { CanvasPage } from "./features/canvas/CanvasPage";
import { SkillHomePage } from "./features/skill-home/SkillHomePage";
import type { PendingAttachment, WebWork } from "./types";

function routeWorkId() {
  return window.location.pathname.match(/^\/work\/([^/]+)\/?$/)?.[1] ?? null;
}

export function App() {
  const [theme, setTheme] = useState<ThemeMode>(loadTheme);
  const [work, setWork] = useState<WebWork | null>(() => {
    const id = routeWorkId();
    return id ? loadWork(id) : null;
  });

  useEffect(() => {
    const onPopState = () => {
      const id = routeWorkId();
      setWork(id ? loadWork(id) : null);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      const id = routeWorkId();
      if (!id || (event.key && event.key !== workStorageKey(id))) return;
      setWork(loadWork(id));
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  useEffect(() => applyTheme(theme), [theme]);

  function openWork(nextWork: WebWork, attachments: PendingAttachment[]) {
    registerLocalFiles(attachments);
    const initialWork: WebWork = {
      ...nextWork,
      cloudState: isCloudConfigured() ? "syncing" : "local",
    };
    saveWork(initialWork);
    const workUrl = `/work/${initialWork.id}`;
    const opened = window.open(workUrl, "_blank");
    if (opened) opened.opener = null;
    if (!opened) {
      window.history.pushState({}, "", workUrl);
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

  function openHome() {
    window.history.pushState({}, "", "/");
    setWork(null);
  }

  if (work) return <CanvasPage work={work} onHome={openHome} />;
  return <SkillHomePage onCreate={openWork} theme={theme} onThemeChange={setTheme} />;
}
