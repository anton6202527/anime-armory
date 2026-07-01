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
  "app.permissionPrepTitle": "首次权限准备",
  "app.permissionPrepMessage": "接下来会集中准备 AnimeArmory 常用权限。若 macOS 弹出 Desktop / Documents / Downloads 等访问授权，请选择允许；这样后续拖入小说、粘贴小说路径、让 AI Agent 处理素材时不会被反复打断。",
  "app.permissionPrepPartialTitle": "部分权限未完成",
  "app.permissionPrepPartialMessage": "以下位置暂时无法访问：\n{items}\n\n如后续仍被系统拦截，请到 系统设置 → 隐私与安全性 → 文件与文件夹 或 完全磁盘访问 中给 AnimeArmory 授权。",

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
  "operation.episodeSelect": "选择集数",
  "operation.expandLeft": "展开左侧面板",
  "operation.collapseLeft": "折叠左侧面板",
  "operation.terminalFirst": "终端优先",
  "operation.leftDeferred": "左侧内容稍后加载",
  "operation.resizeTerminalAria": "调整命令行宽度",
  "operation.resizeTerminalTitle": "拖拽调整命令行宽度，双击恢复默认",
  "operation.nativeOpenedWithCd": "已在原生终端打开目录",
  "operation.nativeEntered": "已进入原生终端",
  "operation.sentToAgent": "已发送给 {name}",
  "operation.startedAgentAndSent": "已启动 {name} 并发送下一步",
  "operation.noAgent": "未检测到可用 AI Agent，请先进入一个 agent",
  "operation.agentAlreadyActive": "当前已经是 {name}",
  "operation.emptyN2dHeadline": "请拖入一本小说或者把小说的路径粘贴到 AI Agent 中，然后直接让它开始制作漫剧吧！",
  "operation.emptyN2dPrompt": "请拖入一本小说或者把小说的路径粘贴到 AI Agent 中，然后直接让它开始制作漫剧吧！",

  "next.next": "下一步",
  "next.execute": "执行",
  "next.deferred": "终端优先启动中，下一步稍后加载…",
  "next.loading": "下一步：分析中…",
  "next.unavailable": "run.py 不可用（{error}）",
  "next.copyCommandTitle": "复制到右侧终端",

  "agent.nativeTitle": "进入当前作品目录的原生 shell 终端",
  "agent.nativeTerminal": "原生终端",
  "agent.enter": "进入 →",
  "agent.detecting": "检测中…",
  "agent.deferred": "终端优先启动中，稍后检测 Agent…",
  "agent.notDetected": "未检测到本地 AI Agent CLI（claude / codex / opencode）",
  "agent.notInstalled": "未安装",
  "agent.defaultTitle": "打开作品时自动进入",
  "agent.default": "默认",
  "agent.image": "生图",
  "agent.refresh": "重新检测",
  "terminal.noAgentPlaceholder": "未检测到可用的本地 AI Agent。可以安装 OpenCode，它支持免费模型；安装后点上方重新检测即可。",

  "files.jsonError": "JSON 解析失败，已显示原文：{error}",
  "files.richPreviewTooLarge": "文件较大，已跳过富文本解析并显示原文。",
  "files.treeCapped": "已显示前 {count} 项，更多文件请在 Finder 中打开或缩小目录查看。",
  "files.newFile": "新建文件",
  "files.newFolder": "新建文件夹",
  "files.createPrompt": "{label}：输入名称",
  "files.renamePrompt": "重命名：输入新名称",
  "files.deleteConfirm": "删除到系统垃圾桶？\n\n{path}",
  "files.changeCount": "{count} 个文件发生变动",
  "files.noChanges": "无变动",
  "files.dirToggleTitle": "{path} - 点击{action}",
  "files.resizeAria": "调整文件栏宽度",
  "files.resizeTitle": "拖拽调整文件栏宽度，双击恢复默认",
  "files.selectFile": "选择左侧文件查看（文本 / 图片 / 视频 / 音频）。",
  "files.previewFailed": "无法预览：{error}",
  "files.menuNewFile": "新建文件…",
  "files.menuNewFolder": "新建文件夹…",
  "files.menuReveal": "在 Finder 中显示",
  "files.menuOpenFolder": "打开文件夹",
  "files.menuOpen": "打开",
  "files.menuOpenTerminal": "在集成终端中打开",
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
  "app.permissionPrepTitle": "First Launch Permissions",
  "app.permissionPrepMessage": "AnimeArmory will now prepare common permissions in one pass. If macOS asks for Desktop, Documents, Downloads, or similar access, choose Allow so dragging novels, pasting novel paths, and running AI agents will not be interrupted later.",
  "app.permissionPrepPartialTitle": "Some Permissions Are Missing",
  "app.permissionPrepPartialMessage": "These locations are not accessible yet:\n{items}\n\nIf macOS blocks them later, grant AnimeArmory access in System Settings → Privacy & Security → Files and Folders or Full Disk Access.",

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
  "operation.episodeSelect": "Select episode",
  "operation.expandLeft": "Expand left panel",
  "operation.collapseLeft": "Collapse left panel",
  "operation.terminalFirst": "Terminal first",
  "operation.leftDeferred": "Left content loads later",
  "operation.resizeTerminalAria": "Resize terminal width",
  "operation.resizeTerminalTitle": "Drag to resize terminal width; double-click to reset",
  "operation.nativeOpenedWithCd": "Opened directory in native terminal",
  "operation.nativeEntered": "Entered native terminal",
  "operation.sentToAgent": "Sent to {name}",
  "operation.startedAgentAndSent": "Started {name} and sent the next prompt",
  "operation.noAgent": "No available AI Agent was detected. Enter an agent first.",
  "operation.agentAlreadyActive": "{name} is already active",
  "operation.emptyN2dHeadline": "Drop in a novel, or paste the novel path into the AI Agent, then ask it to start making the comic drama.",
  "operation.emptyN2dPrompt": "Drop in a novel, or paste the novel path into the AI Agent, then ask it to start making the comic drama.",

  "next.next": "Next",
  "next.execute": "Run",
  "next.deferred": "Starting the terminal first; next action will load shortly…",
  "next.loading": "Next: analyzing…",
  "next.unavailable": "run.py unavailable ({error})",
  "next.copyCommandTitle": "Copy to the terminal on the right",

  "agent.nativeTitle": "Enter a native shell terminal in the current work directory",
  "agent.nativeTerminal": "Native Terminal",
  "agent.enter": "Enter →",
  "agent.detecting": "Detecting…",
  "agent.deferred": "Starting the terminal first; agent detection will run shortly…",
  "agent.notDetected": "No local AI Agent CLI detected (claude / codex / opencode)",
  "agent.notInstalled": "not installed",
  "agent.defaultTitle": "Auto-enter when opening a work",
  "agent.default": "Default",
  "agent.image": "Image",
  "agent.refresh": "Detect again",
  "terminal.noAgentPlaceholder": "No usable local AI Agent was detected. You can install OpenCode, configure a free model, then detect again above.",

  "files.jsonError": "JSON parse failed; showing the original text: {error}",
  "files.richPreviewTooLarge": "Large file; rich preview was skipped and the original text is shown.",
  "files.treeCapped": "Showing the first {count} items. Open the folder in Finder or narrow the directory to see more.",
  "files.newFile": "New File",
  "files.newFolder": "New Folder",
  "files.createPrompt": "{label}: enter a name",
  "files.renamePrompt": "Rename: enter a new name",
  "files.deleteConfirm": "Move to system Trash?\n\n{path}",
  "files.changeCount": "{count} changed files",
  "files.noChanges": "No changes",
  "files.dirToggleTitle": "{path} - click to {action}",
  "files.resizeAria": "Resize file pane width",
  "files.resizeTitle": "Drag to resize file pane width; double-click to reset",
  "files.selectFile": "Select a file on the left to preview text, images, video, or audio.",
  "files.previewFailed": "Cannot preview: {error}",
  "files.menuNewFile": "New File…",
  "files.menuNewFolder": "New Folder…",
  "files.menuReveal": "Reveal in Finder",
  "files.menuOpenFolder": "Open Folder",
  "files.menuOpen": "Open",
  "files.menuOpenTerminal": "Open in Integrated Terminal",
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
