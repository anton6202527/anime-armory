import { useEffect, useState } from "react";
import { readNextAction, readWorkFile } from "../api";
import { useI18n } from "../i18n";
import type { NextAction } from "../types";

type ProgressStep = {
  headline: string;
  message: string;
  executePrompt: string;
  commandPreview?: string;
  ep?: string;
  skill?: string;
  sourceLine?: string;
};

function PlaceholderNext({
  headline,
  message,
  button,
  enabled = false,
  field = false,
  onExecute,
}: {
  headline: string;
  message: string;
  button: string;
  enabled?: boolean;
  field?: boolean;
  onExecute?: () => void;
}) {
  return (
    <div className={"next-strip" + (enabled ? " next-strip-executable" : " next-strip-disabled")}>
      <span className="headline">{headline}</span>
      <div className={"next-placeholder" + (field ? " next-placeholder-field" : "")} aria-disabled={!enabled}>
        <span>{message}</span>
      </div>
      <button type="button" className="next-execute" disabled={!enabled} onClick={onExecute}>
        {button}
      </button>
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

function progressPrompt(step: {
  message: string;
  skill?: string;
  sourceLine?: string;
}): string {
  const parts = [
    `请读取当前作品目录的 _进度.md，按当前进度继续执行第一步：${step.message}。`,
  ];
  if (step.skill) parts.push(`优先使用 ${step.skill}。`);
  if (step.sourceLine) parts.push(`进度原文：${step.sourceLine}`);
  parts.push("完成后按项目约定回写 _进度.md，并刷新必要产物。");
  return parts.join(" ");
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
        headline: "当前进度",
        message,
        skill,
        sourceLine: row.join(" | "),
        executePrompt: progressPrompt({ message, skill, sourceLine: row.join(" | ") }),
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
          headline: "当前进度",
          message,
          ep: first === "集" ? unit : undefined,
          sourceLine: row.join(" | "),
          executePrompt: progressPrompt({ message, sourceLine: row.join(" | ") }),
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
    headline: "当前进度",
    message,
    skill,
    sourceLine: `[${item.marker}] ${item.text}`,
    executePrompt: progressPrompt({ message, skill, sourceLine: `[${item.marker}] ${item.text}` }),
  };
}

function fallbackStep(progress: string): ProgressStep | null {
  const title = progress
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => line.startsWith("#"));
  const message = title ? stripMarkdown(title.replace(/^#+\s*/, "")) : "已读取 _进度.md";
  return {
    headline: "当前进度",
    message,
    executePrompt: progressPrompt({ message }),
  };
}

function parseProgress(progress: string, line: string): ProgressStep | null {
  if (!compact(progress)) return null;
  if (line === "n2d") return matrixStep(progress) || todoStep(progress) || fallbackStep(progress);
  return stageTableStep(progress) || todoStep(progress) || matrixStep(progress) || fallbackStep(progress);
}

function blockReason(
  na: NextAction,
  t: (key: "next.blockReason", vars?: Record<string, string | number>) => string,
): string {
  const fromCard = compact(na.action_card?.block_reason);
  if (fromCard) return t("next.blockReason", { reason: fromCard });
  const gate = na.gate;
  if (gate?.blocked) {
    const parts = [
      gate.stage ? `gate=${gate.stage}` : "",
      gate.return_to_stage ? `return_to=${gate.return_to_stage}` : "",
      gate.rerun_scope || "",
      gate.findings_path ? `findings=${gate.findings_path}` : "",
    ].filter(Boolean);
    if (parts.length) return t("next.blockReason", { reason: parts.join(" · ") });
  }
  const toUser = compact(na.action_card?.to_user);
  if (na.stop_reason?.startsWith("blocked") && toUser) {
    return t("next.blockReason", { reason: toUser });
  }
  return "";
}

function mergeNextAction(
  step: ProgressStep,
  na: NextAction | null,
  t: (key: "next.blockReason", vars?: Record<string, string | number>) => string,
): ProgressStep {
  if (!na || na.error) return step;
  const cmd = compact(na.action_card?.exact_command);
  const head = compact(na.action_card?.headline) || step.message;
  const reason = blockReason(na, t);
  const toUser = compact(na.action_card?.to_user);
  const owner = compact(na.frontier?.owner);
  const skill = owner || step.skill;
  const message = `${step.message}${skill ? ` → ${skill}` : ""}`;
  const title = reason ? `${head} · ${reason}` : head;
  if (!cmd && !toUser) return { ...step, skill, message, commandPreview: title };
  const executePrompt = cmd || progressPrompt({ message, skill, sourceLine: toUser || step.sourceLine });
  return {
    ...step,
    skill,
    message,
    commandPreview: cmd || title,
    executePrompt,
  };
}

// Current-progress strip, driven by the work root's `_进度.md`.
// n2d gets an extra run.py lookup after the global frontier is derived.
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
    repoRoot,
    line,
    root,
    ep,
    refreshKey,
    enabled = true,
    manualPrompt,
    manualPromptExecutable = true,
    missingProgressPrompt,
    onExecutePrompt,
  } = props;
  const { t } = useI18n();
  const [step, setStep] = useState<ProgressStep | null>(null);
  const [error, setError] = useState<string>("");

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
      .then(async (progress) => {
        let next = parseProgress(progress, line);
        if (line === "n2d" && next?.ep) {
          try {
            next = mergeNextAction(next, await readNextAction(repoRoot, root, next.ep), t);
          } catch {
            // The progress-derived prompt remains usable if run.py is unavailable.
          }
        }
        if (alive) setStep(next);
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
  }, [repoRoot, line, root, ep, refreshKey, enabled, manualPrompt, t]);

  if (manualPrompt) {
    return (
      <PlaceholderNext
        headline={t("next.next")}
        message={manualPrompt.prompt}
        button={t("next.execute")}
        field
        enabled={manualPromptExecutable && Boolean(onExecutePrompt)}
        onExecute={manualPromptExecutable ? () => onExecutePrompt?.(manualPrompt.prompt) : undefined}
      />
    );
  }

  if (!enabled) {
    return <PlaceholderNext headline={t("next.next")} message={t("next.deferred")} button={t("next.execute")} field />;
  }
  if (error) {
    const missingProgress = /_进度\.md|No such file|os error 2|not found|找不到|不存在/i.test(error);
    if (missingProgress && missingProgressPrompt) {
      return (
        <PlaceholderNext
          headline={t("next.next")}
          message={missingProgressPrompt.prompt}
          button={t("next.execute")}
          field
          enabled={Boolean(onExecutePrompt)}
          onExecute={() => onExecutePrompt?.(missingProgressPrompt.prompt)}
        />
      );
    }
    return (
      <PlaceholderNext
        headline={t("next.next")}
        message={t("next.unavailable", { error: error.slice(0, 80) })}
        button={t("next.execute")}
        field
      />
    );
  }
  if (!step) {
    return <PlaceholderNext headline={t("next.next")} message={t("next.loading")} button={t("next.execute")} field />;
  }

  const title = step.commandPreview ? `${step.message} · ${step.commandPreview}` : step.message;
  const preview = step.commandPreview || step.skill || t("next.readProgress");

  return (
    <div className="next-strip next-strip-executable">
      <span className="headline">{t("next.next")}</span>
      <code className="next-command" title={t("next.copyCommandTitle")}>{preview}</code>
      <span className="next-title" title={title}>{title}</span>
      <button
        type="button"
        className="next-execute"
        disabled={!onExecutePrompt}
        onClick={() => onExecutePrompt?.(step.executePrompt)}
      >
        {t("next.execute")}
      </button>
    </div>
  );
}
