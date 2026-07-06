import { useEffect, useMemo, useState, type ReactNode } from "react";
import { readWorkFile } from "../api";
import { useI18n } from "../i18n";
import { Codicon } from "./Codicon";

type ProgressStep = {
  message: string;
  skill?: string;
  sourceLine?: string;
};

type ProjectDetails = {
  loading: boolean;
  settingsText: string;
  progressText: string;
  settingsError: string;
  progressError: string;
};

function PlaceholderNext({
  headline,
  message,
  enabled = false,
  action,
}: {
  headline: string;
  message: string;
  enabled?: boolean;
  action?: ReactNode;
}) {
  return (
    <div className={"next-strip next-progress-strip" + (enabled ? "" : " next-strip-disabled")}>
      <span className="headline">{headline}</span>
      <div className="next-progress-value" aria-disabled={!enabled} title={message}>
        <span>{message}</span>
      </div>
      {action}
    </div>
  );
}

function compact(value?: string): string {
  return (value || "").replace(/\s+/g, " ").trim();
}

function stripMarkdown(value: string): string {
  return compact(
    value
      .replace(/\*\*/g, "")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/\[(.*?)\]\((.*?)\)/g, "$1"),
  );
}

function splitRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => stripMarkdown(cell));
}

function isTableSeparator(line: string): boolean {
  const cells = splitRow(line);
  return cells.length > 1 && cells.every((cell) => /^:?-{3,}:?$/.test(cell.trim()));
}

function isDone(value: string): boolean {
  const s = stripMarkdown(value);
  if (!s || s === "—" || s === "-" || /^n\/?a$/i.test(s)) return true;
  if (s.includes("✅") || /\[[xX]\]/.test(s)) return true;
  const ratio = s.match(/^(\d+)\s*\/\s*(\d+)$/);
  if (ratio) return Number(ratio[1]) >= Number(ratio[2]);
  return /^(done|complete|completed|pass|完成|已完成|已定稿)$/.test(s);
}

function parseTables(progress: string): Array<{ headers: string[]; rows: string[][] }> {
  const lines = progress.split(/\r?\n/);
  const tables: Array<{ headers: string[]; rows: string[][] }> = [];
  for (let i = 0; i < lines.length - 1; i += 1) {
    if (!lines[i].trim().startsWith("|") || !isTableSeparator(lines[i + 1])) continue;
    const headers = splitRow(lines[i]);
    const rows: string[][] = [];
    i += 2;
    while (i < lines.length && lines[i].trim().startsWith("|")) {
      const row = splitRow(lines[i]);
      if (row.length === headers.length) rows.push(row);
      i += 1;
    }
    tables.push({ headers, rows });
  }
  return tables;
}

function skillFromText(value: string): string | undefined {
  const match = value.match(/\b(?:n2d|novel|song|mv|ad)(?:-[a-z0-9]+)*\b/i);
  return match?.[0];
}

function stageTableStep(progress: string): ProgressStep | null {
  for (const table of parseTables(progress)) {
    const stageIdx = table.headers.findIndex((h) => h === "阶段");
    const skillIdx = table.headers.findIndex((h) => /^skill$/i.test(h));
    const statusIdx = table.headers.findIndex((h) => h === "状态");
    if (stageIdx < 0 || statusIdx < 0) continue;
    for (const row of table.rows) {
      if (isDone(row[statusIdx])) continue;
      const stage = row[stageIdx];
      const skill = skillIdx >= 0 ? row[skillIdx] : skillFromText(row.join(" "));
      const message = skill ? `${stage} → ${skill}` : stage;
      return {
        message,
        skill,
        sourceLine: row.join(" | "),
      };
    }
  }
  return null;
}

function matrixStep(progress: string): ProgressStep | null {
  const skipHeaders = new Set(["集", "章节", "标题", "字数", "raw", "备注"]);
  for (const table of parseTables(progress)) {
    const first = table.headers[0];
    if (first !== "集" && first !== "章节") continue;
    for (const row of table.rows) {
      for (let i = 1; i < table.headers.length; i += 1) {
        const header = table.headers[i];
        if (skipHeaders.has(header)) continue;
        if (isDone(row[i])) continue;
        const unit = row[0];
        const message = `${unit} → ${header}（${row[i]}）`;
        return {
          message,
          sourceLine: row.join(" | "),
        };
      }
    }
  }
  return null;
}

function todoStep(progress: string): ProgressStep | null {
  const open: Array<{ marker: string; text: string }> = [];
  for (const line of progress.split(/\r?\n/)) {
    const match = line.match(/^\s*[-*]\s+\[([ ~-])\]\s+(.+)$/);
    if (!match) continue;
    open.push({ marker: match[1], text: stripMarkdown(match[2]) });
  }
  const item = open[open.length - 1];
  if (!item) return null;
  const skill = skillFromText(item.text);
  const message = item.text;
  return {
    message,
    skill,
    sourceLine: `[${item.marker}] ${item.text}`,
  };
}

function fallbackStep(progress: string): ProgressStep | null {
  const title = progress
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => line.startsWith("#"));
  const message = title ? stripMarkdown(title.replace(/^#+\s*/, "")) : "已读取 _进度.md";
  return {
    message,
  };
}

function parseProgress(progress: string, line: string): ProgressStep | null {
  if (!compact(progress)) return null;
  if (line === "n2d") return matrixStep(progress) || todoStep(progress) || fallbackStep(progress);
  return stageTableStep(progress) || todoStep(progress) || matrixStep(progress) || fallbackStep(progress);
}

function stepLabel(step: ProgressStep | null): string {
  if (!step) return "";
  return step.skill && !step.message.toLowerCase().includes(step.skill.toLowerCase())
    ? `${step.message} → ${step.skill}`
    : step.message;
}

// Current-progress strip, driven by the work root's `_进度.md`.
export function NextActionStrip(props: {
  repoRoot: string;
  line: string;
  root: string;
  ep: string;
  refreshKey?: number;
  enabled?: boolean;
  manualPrompt?: {
    headline: string;
    prompt: string;
  } | null;
  manualPromptExecutable?: boolean;
  missingProgressPrompt?: {
    prompt: string;
  } | null;
  onExecutePrompt?: (prompt: string) => void;
}) {
  const {
    line,
    root,
    refreshKey,
    enabled = true,
    manualPrompt,
    missingProgressPrompt,
  } = props;
  const { t } = useI18n();
  const [step, setStep] = useState<ProgressStep | null>(null);
  const [error, setError] = useState<string>("");
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [details, setDetails] = useState<ProjectDetails>({
    loading: false,
    settingsText: "",
    progressText: "",
    settingsError: "",
    progressError: "",
  });

  const detailStep = useMemo(
    () => (details.progressText ? parseProgress(details.progressText, line) : step),
    [details.progressText, line, step],
  );

  function openProjectDetails() {
    setDetailsOpen(true);
    setDetails({
      loading: true,
      settingsText: "",
      progressText: "",
      settingsError: "",
      progressError: "",
    });
    Promise.allSettled([
      readWorkFile(root, "_设置.md"),
      readWorkFile(root, "_进度.md"),
    ]).then(([settingsResult, progressResult]) => {
      setDetails({
        loading: false,
        settingsText: settingsResult.status === "fulfilled" ? settingsResult.value : "",
        progressText: progressResult.status === "fulfilled" ? progressResult.value : "",
        settingsError: settingsResult.status === "rejected" ? String(settingsResult.reason) : "",
        progressError: progressResult.status === "rejected" ? String(progressResult.reason) : "",
      });
    });
  }

  const settingsButton = (
    <button
      type="button"
      className="project-settings-btn"
      title={t("projectSettings.viewTitle")}
      aria-label={t("projectSettings.viewTitle")}
      onClick={openProjectDetails}
    >
      <Codicon name="settings" />
    </button>
  );

  const detailsModal = detailsOpen ? (
    <div className="modal-backdrop project-settings-backdrop" onClick={() => setDetailsOpen(false)}>
      <div className="project-settings-modal" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <div className="project-settings-head">
          <h2>{t("projectSettings.title")}</h2>
          <button
            type="button"
            className="project-settings-close"
            aria-label={t("common.close")}
            title={t("common.close")}
            onClick={() => setDetailsOpen(false)}
          >
            ×
          </button>
        </div>
        {details.loading ? (
          <div className="project-settings-loading">{t("common.loading")}</div>
        ) : (
          <div className="project-settings-body">
            <section>
              <h3>{t("projectSettings.settingsHeading")}</h3>
              {details.settingsText ? (
                <pre>{details.settingsText}</pre>
              ) : (
                <div className="project-settings-empty">
                  {details.settingsError
                    ? t("projectSettings.settingsMissing", { error: details.settingsError.slice(0, 120) })
                    : t("projectSettings.noSettings")}
                </div>
              )}
            </section>
            <section>
              <h3>{t("projectSettings.progressHeading")}</h3>
              <div className="project-next-summary">
                <span>{t("projectSettings.nextLabel")}</span>
                <b>
                  {stepLabel(detailStep)
                    || (details.progressError
                      ? t("next.unavailable", { error: details.progressError.slice(0, 80) })
                      : t("next.loading"))}
                </b>
              </div>
              {details.progressText ? (
                <pre>{details.progressText}</pre>
              ) : (
                <div className="project-settings-empty">
                  {details.progressError
                    ? t("projectSettings.progressMissing", { error: details.progressError.slice(0, 120) })
                    : t("next.noProgress")}
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  ) : null;

  function withProjectDetails(content: ReactNode) {
    return (
      <>
        {content}
        {detailsModal}
      </>
    );
  }

  useEffect(() => {
    if (!enabled) {
      setStep(null);
      setError("");
      return;
    }
    if (manualPrompt) {
      setStep(null);
      setError("");
      return;
    }
    let alive = true;
    setError("");
    readWorkFile(root, "_进度.md")
      .then((progress) => {
        if (alive) setStep(parseProgress(progress, line));
      })
      .catch((e) => {
        if (alive) {
          setStep(null);
          setError(String(e));
        }
      });
    return () => {
      alive = false;
    };
  }, [line, root, refreshKey, enabled, manualPrompt]);

  useEffect(() => {
    if (!detailsOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDetailsOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [detailsOpen]);

  if (manualPrompt) {
    return withProjectDetails(
      <PlaceholderNext
        headline={t("next.progress")}
        message={manualPrompt.headline || manualPrompt.prompt}
        enabled
        action={settingsButton}
      />,
    );
  }

  if (!enabled) {
    return withProjectDetails(
      <PlaceholderNext headline={t("next.progress")} message={t("next.deferred")} action={settingsButton} />,
    );
  }

  if (error) {
    const missingProgress = /_进度\.md|No such file|os error 2|not found|找不到|不存在/i.test(error);
    if (missingProgress && missingProgressPrompt) {
      return withProjectDetails(
        <PlaceholderNext
          headline={t("next.progress")}
          message={t("next.noProgress")}
          enabled
          action={settingsButton}
        />,
      );
    }
    return withProjectDetails(
      <PlaceholderNext
        headline={t("next.progress")}
        message={t("next.unavailable", { error: error.slice(0, 80) })}
        action={settingsButton}
      />,
    );
  }

  if (!step) {
    return withProjectDetails(
      <PlaceholderNext headline={t("next.progress")} message={t("next.loading")} action={settingsButton} />,
    );
  }

  const progressText = stepLabel(step);
  const title = step.sourceLine ? `${progressText}\n${step.sourceLine}` : progressText;

  return withProjectDetails(
    <div className="next-strip next-progress-strip">
      <span className="headline">{t("next.progress")}</span>
      <div className="next-progress-value" title={title}>
        <span>{progressText}</span>
      </div>
      {settingsButton}
    </div>,
  );
}
