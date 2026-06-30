import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { LineInfo, LineKey } from "./types";

export type Language = "zh" | "en";

const STORAGE_KEY = "aa.language";

const zh = {
  "language.label": "语言",
  "language.title": "切换界面语言",
  "language.zh": "中文",
  "language.en": "English",
  "source.title": "打开 GitHub 源码",

  "app.initWorkspace": "初始化工作区…",
  "app.workspaceBlockedTitle": "无法选择该工作区",
  "app.workspaceBlockedMessage": "该目录与项目仓库重叠，已拒绝。\n请选择仓库之外的目录作为作品工作区（作品与项目仓库需完全隔离）。",

  "common.home": "首页",
  "common.close": "关闭",
  "common.cancel": "取消",
  "common.create": "创建",
  "common.delete": "删除",
  "common.expand": "展开",
  "common.collapse": "折叠",
  "common.loading": "读取中…",
  "common.readFailed": "读取失败：{error}",
  "common.emptyDir": "空目录",
  "common.workCount": "{count} 部作品",
  "common.scanFailed": "扫描失败：{error}",
  "common.listDelimiter": "，",

  "lineLabel.n2d": "制漫剧 (n2d)",
  "lineLabel.ad": "拍广告 (ad)",
  "lineLabel.mv": "制MV (mv)",
  "lineLabel.song": "写歌 (song)",
  "lineLabel.novel": "写小说 (novel)",

  "home.workspace": "工作区：{path}",
  "home.switchWorkspace": "切换工作区…",
  "home.skillDetails": "技能详情",
  "home.enterCreation": "进入创作区 →",

  "line.backHome": "← 首页",
  "line.deleteWorkTitle": "删除作品",
  "line.deleteWorkMessage": "删除作品「{name}」？\n会移到系统垃圾桶（可恢复），不影响项目仓库。",
  "line.moveToTrash": "移到垃圾桶",
  "line.deleteWorkAria": "删除作品 {name}",
  "line.hasProgress": "● 有进度",
  "line.initialOnly": "○ 仅初始化",
  "line.workNamePlaceholder": "作品名…",
  "line.newWork": "新建作品",

  "tabs.home": "首页",
  "tabs.close": "关闭",

  "operation.backSeries": "← 系列",
  "operation.storyboardSource": "（未出图：画布读自 storyboard.json）",
  "operation.filesTab": "📁 文件",
  "operation.canvasTab": "🎬 画布",
  "operation.boardTab": "📋 看板",
  "operation.resizeTerminalAria": "调整命令行宽度",
  "operation.resizeTerminalTitle": "拖拽调整命令行宽度，双击恢复默认",
  "operation.nativeOpenedWithCd": "已在原生终端打开目录",
  "operation.nativeEntered": "已进入原生终端",
  "operation.sentToAgent": "已发送给 {name}",
  "operation.startedAgentAndSent": "已启动 {name} 并发送下一步",
  "operation.noAgent": "未检测到可用 AI Agent，请先进入一个 agent",
  "operation.installingAgent": "正在安装 {name}",
  "operation.agentAlreadyActive": "当前已经是 {name}",
  "operation.emptyN2dHeadline": "当前项目为空，可以先选择或导入源文本",
  "operation.emptyN2dPrompt": "当前制漫剧项目目录为空：{path}。请指导用户选择或导入合法源文本，说明推荐的源文本存放位置、需要保留的来源/授权记录，以及进入拆集前应检查的最小准备项。",

  "next.next": "下一步",
  "next.execute": "执行",
  "next.loading": "下一步：分析中…",
  "next.unavailable": "run.py 不可用（{error}）",
  "next.copyCommandTitle": "复制到右侧终端",

  "agent.nativeTitle": "进入当前作品目录的原生 shell 终端",
  "agent.nativeTerminal": "原生终端",
  "agent.enter": "进入 →",
  "agent.detecting": "检测中…",
  "agent.notDetected": "未检测到本地 AI Agent CLI（claude / codex / gemini / opencode）",
  "agent.notInstalled": "未安装",
  "agent.defaultTitle": "打开作品时自动进入",
  "agent.default": "默认",
  "agent.installTitle": "在右侧终端里安装并启动",
  "agent.install": "安装",
  "agent.installEnter": "安装 →",
  "agent.image": "生图",
  "agent.refresh": "重新检测",

  "files.jsonError": "JSON 解析失败，已显示原文：{error}",
  "files.newFile": "新建文件",
  "files.newFolder": "新建文件夹",
  "files.createPrompt": "{label}：输入名称",
  "files.renamePrompt": "重命名：输入新名称",
  "files.deleteConfirm": "删除到系统垃圾桶？\n\n{path}",
  "files.changeCount": "{count} 项变动",
  "files.deletedCount": "{count} 项已删除",
  "files.deletedTitle": "已删除：\n{items}",
  "files.noChanges": "无变动",
  "files.changesTitle": "变动",
  "files.archiveAllTitle": "把当前全部变动（含已删除）归档为新基线，清除 U/M 标记",
  "files.archive": "归档",
  "files.dirToggleTitle": "{path} - 点击{action}",
  "files.statusNewTitle": "新增（未归档）",
  "files.statusModifiedTitle": "已修改（未归档）",
  "files.statusDeletedTitle": "已删除（未归档）",
  "files.statusNewAria": "新增",
  "files.statusModifiedAria": "已修改",
  "files.statusDeletedAria": "已删除",
  "files.confirmFolderTitle": "确认此文件夹（归档其内变动）",
  "files.confirmFileTitle": "确认此文件（归档）",
  "files.confirmItemAria": "确认归档此项",
  "files.resizeAria": "调整文件栏宽度",
  "files.resizeTitle": "拖拽调整文件栏宽度，双击恢复默认",
  "files.selectFile": "选择左侧文件查看（文本 / 图片 / 视频 / 音频）。",
  "files.previewFailed": "无法预览：{error}",
  "files.diffLoading": "读取变动明细…",
  "files.diffFailed": "读取变动失败：{error}",
  "files.diffUnavailable": "此文件当前没有可显示的文本对比。",
  "files.diffStats": "+{additions} / -{deletions}",
  "files.diffApprox": "大文件近似对照",
  "files.diffOld": "旧版",
  "files.diffNew": "当前",
  "files.menuNewFile": "新建文件…",
  "files.menuNewFolder": "新建文件夹…",
  "files.menuReveal": "在 Finder 中显示",
  "files.menuOpenFolder": "打开文件夹",
  "files.menuOpen": "打开",
  "files.menuOpenTerminal": "在集成终端中打开",
  "files.menuArchive": "归档变动",
  "files.menuCopyName": "复制名称",
  "files.menuCopyPath": "复制路径",
  "files.menuCopyRelativePath": "复制相对路径",
  "files.menuRename": "重命名…",
  "files.menuDelete": "删除",

  "skills.skills": "技能",
  "skills.close": "关闭",
  "skills.dispatcher": "调度器",
  "skills.loadingDir": "读取目录…",
  "skills.emptyDir": "（空目录）",
  "skills.selectFile": "（选择左侧文件查看代码）",
  "skills.notFound": "未找到技能",
  "skills.enterCreation": "进入创作区 →",

  "canvas.noStoryboard": "本集暂无分镜（storyboard.json 未生成）。",
  "canvas.noImage": "未出图",

  "kanban.todo": "📝 待出图",
  "kanban.image": "🎨 已出图",
  "kanban.video": "🎬 已出视频",
};

type I18nKey = keyof typeof zh;

const en: Record<I18nKey, string> = {
  "language.label": "Language",
  "language.title": "Switch interface language",
  "language.zh": "中文",
  "language.en": "English",
  "source.title": "Open GitHub source",

  "app.initWorkspace": "Initializing workspace…",
  "app.workspaceBlockedTitle": "Workspace Not Allowed",
  "app.workspaceBlockedMessage": "That directory overlaps the project repository and was rejected.\nChoose a workspace outside the repository so works and the project stay fully isolated.",

  "common.home": "Home",
  "common.close": "Close",
  "common.cancel": "Cancel",
  "common.create": "Create",
  "common.delete": "Delete",
  "common.expand": "expand",
  "common.collapse": "collapse",
  "common.loading": "Loading…",
  "common.readFailed": "Read failed: {error}",
  "common.emptyDir": "Empty directory",
  "common.workCount": "{count} works",
  "common.scanFailed": "Scan failed: {error}",
  "common.listDelimiter": ", ",

  "lineLabel.n2d": "Comic Drama (n2d)",
  "lineLabel.ad": "Ads (ad)",
  "lineLabel.mv": "Music Video (mv)",
  "lineLabel.song": "Songwriting (song)",
  "lineLabel.novel": "Novels (novel)",

  "home.workspace": "Workspace: {path}",
  "home.switchWorkspace": "Switch Workspace…",
  "home.skillDetails": "Skill Details",
  "home.enterCreation": "Enter Studio →",

  "line.backHome": "← Home",
  "line.deleteWorkTitle": "Delete Work",
  "line.deleteWorkMessage": "Delete work “{name}”?\nIt will be moved to the system Trash and can be restored. The project repo will not be affected.",
  "line.moveToTrash": "Move to Trash",
  "line.deleteWorkAria": "Delete work {name}",
  "line.hasProgress": "● Has progress",
  "line.initialOnly": "○ Initialized only",
  "line.workNamePlaceholder": "Work name…",
  "line.newWork": "New Work",

  "tabs.home": "Home",
  "tabs.close": "Close",

  "operation.backSeries": "← Series",
  "operation.storyboardSource": "(No images yet: canvas is reading storyboard.json)",
  "operation.filesTab": "📁 Files",
  "operation.canvasTab": "🎬 Canvas",
  "operation.boardTab": "📋 Board",
  "operation.resizeTerminalAria": "Resize terminal width",
  "operation.resizeTerminalTitle": "Drag to resize terminal width; double-click to reset",
  "operation.nativeOpenedWithCd": "Opened directory in native terminal",
  "operation.nativeEntered": "Entered native terminal",
  "operation.sentToAgent": "Sent to {name}",
  "operation.startedAgentAndSent": "Started {name} and sent the next prompt",
  "operation.noAgent": "No available AI Agent was detected. Enter an agent first.",
  "operation.installingAgent": "Installing {name}",
  "operation.agentAlreadyActive": "{name} is already active",
  "operation.emptyN2dHeadline": "This project is empty. Choose or import a source text first.",
  "operation.emptyN2dPrompt": "The current comic-drama project directory is empty: {path}. Guide the user to choose or import a lawful source text, explain the recommended source-text location, the source/rights notes to keep, and the minimum preparation checks before episode splitting.",

  "next.next": "Next",
  "next.execute": "Run",
  "next.loading": "Next: analyzing…",
  "next.unavailable": "run.py unavailable ({error})",
  "next.copyCommandTitle": "Copy to the terminal on the right",

  "agent.nativeTitle": "Enter a native shell terminal in the current work directory",
  "agent.nativeTerminal": "Native Terminal",
  "agent.enter": "Enter →",
  "agent.detecting": "Detecting…",
  "agent.notDetected": "No local AI Agent CLI detected (claude / codex / gemini / opencode)",
  "agent.notInstalled": "not installed",
  "agent.defaultTitle": "Auto-enter when opening a work",
  "agent.default": "Default",
  "agent.installTitle": "Install and start in the terminal on the right",
  "agent.install": "Install",
  "agent.installEnter": "Install →",
  "agent.image": "Image",
  "agent.refresh": "Detect again",

  "files.jsonError": "JSON parse failed; showing the original text: {error}",
  "files.newFile": "New File",
  "files.newFolder": "New Folder",
  "files.createPrompt": "{label}: enter a name",
  "files.renamePrompt": "Rename: enter a new name",
  "files.deleteConfirm": "Move to system Trash?\n\n{path}",
  "files.changeCount": "{count} changes",
  "files.deletedCount": "{count} deleted",
  "files.deletedTitle": "Deleted:\n{items}",
  "files.noChanges": "No changes",
  "files.changesTitle": "Changes",
  "files.archiveAllTitle": "Archive all current changes, including deleted files, as the new baseline and clear U/M markers",
  "files.archive": "Archive",
  "files.dirToggleTitle": "{path} - click to {action}",
  "files.statusNewTitle": "New, not archived",
  "files.statusModifiedTitle": "Modified, not archived",
  "files.statusDeletedTitle": "Deleted, not archived",
  "files.statusNewAria": "New",
  "files.statusModifiedAria": "Modified",
  "files.statusDeletedAria": "Deleted",
  "files.confirmFolderTitle": "Confirm this folder and archive changes inside it",
  "files.confirmFileTitle": "Confirm this file and archive it",
  "files.confirmItemAria": "Confirm and archive this item",
  "files.resizeAria": "Resize file pane width",
  "files.resizeTitle": "Drag to resize file pane width; double-click to reset",
  "files.selectFile": "Select a file on the left to preview text, images, video, or audio.",
  "files.previewFailed": "Cannot preview: {error}",
  "files.diffLoading": "Loading change details…",
  "files.diffFailed": "Failed to load changes: {error}",
  "files.diffUnavailable": "No text comparison is available for this file.",
  "files.diffStats": "+{additions} / -{deletions}",
  "files.diffApprox": "Approximate large-file comparison",
  "files.diffOld": "Old",
  "files.diffNew": "Current",
  "files.menuNewFile": "New File…",
  "files.menuNewFolder": "New Folder…",
  "files.menuReveal": "Reveal in Finder",
  "files.menuOpenFolder": "Open Folder",
  "files.menuOpen": "Open",
  "files.menuOpenTerminal": "Open in Integrated Terminal",
  "files.menuArchive": "Archive Changes",
  "files.menuCopyName": "Copy Name",
  "files.menuCopyPath": "Copy Path",
  "files.menuCopyRelativePath": "Copy Relative Path",
  "files.menuRename": "Rename…",
  "files.menuDelete": "Delete",

  "skills.skills": "Skills",
  "skills.close": "Close",
  "skills.dispatcher": "Dispatcher",
  "skills.loadingDir": "Loading directory…",
  "skills.emptyDir": "(Empty directory)",
  "skills.selectFile": "(Select a file on the left to view code)",
  "skills.notFound": "No skills found",
  "skills.enterCreation": "Enter Studio →",

  "canvas.noStoryboard": "No storyboard for this episode yet (storyboard.json has not been generated).",
  "canvas.noImage": "No image yet",

  "kanban.todo": "📝 To Image",
  "kanban.image": "🎨 Image Done",
  "kanban.video": "🎬 Video Done",
};

const DICTS: Record<Language, Record<I18nKey, string>> = { zh, en };

type Params = Record<string, string | number>;

function interpolate(template: string, params?: Params): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (_, key) => String(params[key] ?? ""));
}

function readInitialLanguage(): Language {
  if (typeof window === "undefined") return "zh";
  return window.localStorage.getItem(STORAGE_KEY) === "en" ? "en" : "zh";
}

type I18nContextValue = {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: I18nKey, params?: Params) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(() => readInitialLanguage());

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, language);
  }, [language]);

  const t = useCallback(
    (key: I18nKey, params?: Params) => interpolate(DICTS[language][key] ?? key, params),
    [language],
  );

  const value = useMemo(() => ({ language, setLanguage, t }), [language, t]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used inside I18nProvider");
  return ctx;
}

const LINE_LABEL_KEYS: Record<LineKey, I18nKey> = {
  n2d: "lineLabel.n2d",
  ad: "lineLabel.ad",
  mv: "lineLabel.mv",
  song: "lineLabel.song",
  novel: "lineLabel.novel",
};

export function useLineLabel() {
  const { t } = useI18n();
  return useCallback((line: Pick<LineInfo, "line" | "label">) => t(LINE_LABEL_KEYS[line.line]), [t]);
}

export function LanguageSwitcher() {
  const { language, setLanguage, t } = useI18n();
  return (
    <label className="language-switch" title={t("language.title")}>
      <select
        value={language}
        aria-label={t("language.title")}
        onChange={(event) => setLanguage(event.target.value as Language)}
      >
        <option value="zh">{t("language.zh")}</option>
        <option value="en">{t("language.en")}</option>
      </select>
    </label>
  );
}
