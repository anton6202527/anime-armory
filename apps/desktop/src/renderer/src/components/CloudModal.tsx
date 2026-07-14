import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import {
  cloudAuthStatus,
  cloudBindProject,
  cloudCancelSync,
  cloudGetBinding,
  cloudListProjects,
  cloudSignIn,
  cloudSignOut,
  cloudSyncDownload,
  cloudSyncUpload,
  cloudUnbindProject,
  onCloudSyncProgress,
  type DesktopCloudCapability,
} from "../api";
import { useI18n } from "../i18n";
import type {
  CloudAuthStatus,
  CloudProjectBinding,
  CloudProjectInfo,
  CloudSyncProgress,
  CloudSyncResult,
  WorkRoot,
} from "../types";

interface CloudModalProps {
  capability: DesktopCloudCapability;
  authStatus: CloudAuthStatus | null;
  activeWork: WorkRoot | null;
  onAuthStatus: (status: CloudAuthStatus | null) => void;
  onClose: () => void;
}

function errorText(error: unknown): string {
  if (error instanceof DOMException && error.name === "AbortError") return "同步已取消";
  return error instanceof Error ? error.message : String(error);
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  if (value < 1024 * 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`;
  return `${(value / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export function CloudModal({
  capability,
  authStatus,
  activeWork,
  onAuthStatus,
  onClose,
}: CloudModalProps) {
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [projects, setProjects] = useState<CloudProjectInfo[]>([]);
  const [binding, setBinding] = useState<CloudProjectBinding | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [operationId, setOperationId] = useState<string | null>(null);
  const [progress, setProgress] = useState<CloudSyncProgress | null>(null);
  const [result, setResult] = useState<CloudSyncResult | null>(null);
  const [error, setError] = useState("");

  const config = capability.enabled ? capability.config : null;
  const signedIn = Boolean(authStatus?.user);

  const refreshCloudState = useCallback(async () => {
    if (!config || !authStatus?.user) {
      setProjects([]);
      setBinding(null);
      setSelectedProjectId("");
      return;
    }
    const [nextProjects, nextBinding] = await Promise.all([
      cloudListProjects(config),
      activeWork ? cloudGetBinding(activeWork.path) : Promise.resolve(null),
    ]);
    setProjects(nextProjects);
    setBinding(nextBinding);
    setSelectedProjectId((current) => {
      if (nextBinding && nextProjects.some((project) => project.id === nextBinding.projectId)) {
        return nextBinding.projectId;
      }
      if (current && nextProjects.some((project) => project.id === current)) return current;
      return nextProjects[0]?.id ?? "";
    });
  }, [activeWork, authStatus?.user, config]);

  useEffect(() => {
    if (!config || authStatus !== null) return;
    setBusy(true);
    cloudAuthStatus(config)
      .then(onAuthStatus)
      .catch((reason) => setError(errorText(reason)))
      .finally(() => setBusy(false));
  }, [authStatus, config, onAuthStatus]);

  useEffect(() => {
    refreshCloudState().catch((reason) => setError(errorText(reason)));
  }, [refreshCloudState]);

  useEffect(() => {
    return onCloudSyncProgress((next) => {
      if (next.operationId === operationId) setProgress(next);
    });
  }, [operationId]);

  const progressPercent = useMemo(() => {
    if (!progress) return 0;
    if (progress.totalBytes > 0) return Math.min(100, (progress.transferredBytes / progress.totalBytes) * 100);
    if (progress.totalFiles > 0) return Math.min(100, (progress.completedFiles / progress.totalFiles) * 100);
    return 4;
  }, [progress]);

  const submitSignIn = async (event: FormEvent) => {
    event.preventDefault();
    if (!config) return;
    setBusy(true);
    setError("");
    try {
      const status = await cloudSignIn(config, email, password);
      setPassword("");
      onAuthStatus(status);
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setBusy(false);
    }
  };

  const signOut = async () => {
    if (!config || operationId) return;
    setBusy(true);
    setError("");
    try {
      await cloudSignOut(config);
      onAuthStatus({ user: null, sessionPersisted: authStatus?.sessionPersisted ?? false });
      setProjects([]);
      setBinding(null);
      setResult(null);
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setBusy(false);
    }
  };

  const bindSelected = async () => {
    if (!config || !activeWork || !selectedProjectId) return;
    setBusy(true);
    setError("");
    try {
      const next = await cloudBindProject(config, activeWork.path, selectedProjectId);
      setBinding(next);
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setBusy(false);
    }
  };

  const unbind = async () => {
    if (!activeWork || operationId) return;
    setBusy(true);
    setError("");
    try {
      await cloudUnbindProject(activeWork.path);
      setBinding(null);
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setBusy(false);
    }
  };

  const runSync = async (direction: "upload" | "download") => {
    if (!config || !activeWork || (direction === "download" && !selectedProjectId)) return;
    const id = crypto.randomUUID();
    setOperationId(id);
    setProgress(null);
    setResult(null);
    setError("");
    try {
      const next = direction === "upload"
        ? await cloudSyncUpload(config, activeWork.path, activeWork.name, id)
        : await cloudSyncDownload(config, activeWork.path, selectedProjectId, id);
      setResult(next);
      await refreshCloudState();
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setOperationId(null);
      setProgress(null);
    }
  };

  const cancel = async () => {
    if (!operationId) return;
    await cloudCancelSync(operationId).catch(() => undefined);
  };

  return (
    <div className="modal-backdrop cloud-modal-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !operationId) onClose();
    }}>
      <section className="cloud-modal" role="dialog" aria-modal="true" aria-label={t("cloud.title")}>
        <header className="cloud-modal-head">
          <div>
            <h2>{t("cloud.title")}</h2>
            {authStatus?.user && <span>{t("cloud.account", { email: authStatus.user.email })}</span>}
          </div>
          <button type="button" className="modal-close" disabled={Boolean(operationId)} onClick={onClose}>×</button>
        </header>

        <div className="cloud-modal-body">
          {!capability.enabled ? (
            <div className="cloud-empty">
              <strong>{t("cloud.notConfigured")}</strong>
              <p>{t("cloud.missingConfig", { fields: capability.missing.join(", ") })}</p>
              <code>{t("cloud.configHint")}</code>
            </div>
          ) : !signedIn ? (
            <form className="cloud-login" onSubmit={submitSignIn}>
              <p>{t("cloud.signInIntro")}</p>
              <label>
                <span>{t("cloud.email")}</span>
                <input
                  type="email"
                  autoComplete="username"
                  value={email}
                  disabled={busy}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </label>
              <label>
                <span>{t("cloud.password")}</span>
                <input
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  disabled={busy}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </label>
              <button type="submit" className="primary" disabled={busy || !email || !password}>
                {busy ? t("cloud.signingIn") : t("cloud.signIn")}
              </button>
            </form>
          ) : (
            <>
              {!authStatus?.sessionPersisted && (
                <div className="cloud-notice">{t("cloud.sessionMemoryOnly")}</div>
              )}
              {!activeWork ? (
                <div className="cloud-empty">{t("cloud.noWork")}</div>
              ) : (
                <div className="cloud-sync">
                  <div className="cloud-work-title">{t("cloud.currentWork", { name: activeWork.name })}</div>
                  {binding && <div className="cloud-binding">{t("cloud.bound", { name: binding.projectName })}</div>}

                  <label className="cloud-project-select">
                    <span>{t("cloud.project")}</span>
                    <select
                      value={selectedProjectId}
                      disabled={busy || Boolean(operationId) || projects.length === 0}
                      onChange={(event) => setSelectedProjectId(event.target.value)}
                    >
                      {projects.length === 0 && <option value="">{t("cloud.noProjects")}</option>}
                      {projects.map((project) => (
                        <option key={project.id} value={project.id}>{project.name} · {project.role}</option>
                      ))}
                    </select>
                  </label>

                  <div className="cloud-binding-actions">
                    <button type="button" disabled={!selectedProjectId || busy || Boolean(operationId)} onClick={bindSelected}>
                      {t("cloud.bind")}
                    </button>
                    {binding && (
                      <button type="button" disabled={busy || Boolean(operationId)} onClick={unbind}>
                        {t("cloud.unbind")}
                      </button>
                    )}
                  </div>

                  {!binding && <div className="cloud-new-project">{t("cloud.newProject")}</div>}

                  <div className="cloud-action-card">
                    <button type="button" className="primary" disabled={Boolean(operationId)} onClick={() => runSync("upload")}>
                      {t("cloud.upload")}
                    </button>
                    <p>{t("cloud.uploadHelp")}</p>
                  </div>
                  <div className="cloud-action-card">
                    <button
                      type="button"
                      disabled={Boolean(operationId) || !selectedProjectId}
                      onClick={() => runSync("download")}
                    >
                      {t("cloud.download")}
                    </button>
                    <p>{t("cloud.downloadHelp")}</p>
                  </div>

                  {operationId && progress && (
                    <div className="cloud-progress">
                      <div className="cloud-progress-row">
                        <span>{t(`cloud.phase.${progress.phase}`)}</span>
                        <span>{t("cloud.progress", {
                          done: progress.completedFiles,
                          total: progress.totalFiles,
                          bytes: formatBytes(progress.transferredBytes),
                        })}</span>
                      </div>
                      <div className="cloud-progress-track"><i style={{ width: `${progressPercent}%` }} /></div>
                      {progress.relativePath && <code>{progress.relativePath}</code>}
                      <button type="button" onClick={cancel}>{t("cloud.cancel")}</button>
                    </div>
                  )}

                  {result && (
                    <div className="cloud-result">
                      {result.direction === "upload"
                        ? t("cloud.resultUpload", { uploaded: result.uploadedFiles, skipped: result.skippedFiles })
                        : t("cloud.resultDownload", {
                            downloaded: result.downloadedFiles,
                            skipped: result.skippedFiles,
                            conflicts: result.conflictFiles.length,
                          })}
                      {result.conflictFiles.length > 0 && (
                        <div>{t("cloud.conflicts", { files: result.conflictFiles.slice(0, 8).join(", ") })}</div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {error && <div className="cloud-error">{t("cloud.failed", { error })}</div>}
        </div>

        {signedIn && (
          <footer className="cloud-modal-foot">
            <button type="button" disabled={busy || Boolean(operationId)} onClick={signOut}>{t("cloud.signOut")}</button>
          </footer>
        )}
      </section>
    </div>
  );
}
