import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import {
  Background,
  BackgroundVariant,
  Handle,
  MarkerType,
  MiniMap,
  Panel,
  Position,
  ReactFlow,
  addEdge,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Connection,
  type Edge,
  type Node,
  type NodeProps,
  type ReactFlowInstance,
} from "@xyflow/react";
import {
  ArrowUp,
  ArrowUpDown,
  Blocks,
  Box,
  Camera,
  Check,
  ChevronDown,
  ChevronRight,
  CirclePlus,
  Clock3,
  ClipboardPenLine,
  Coins,
  Download,
  ExternalLink,
  Filter,
  Folder,
  Hand,
  Maximize2,
  Mic2,
  Minimize2,
  MoreHorizontal,
  Paperclip,
  Play,
  Plus,
  RotateCcw,
  Search,
  Settings2,
  Share2,
  SlidersHorizontal,
  Sparkles,
  Star,
  Trash2,
  Upload,
  UserRound,
  WandSparkles,
  Wrench,
  X,
} from "lucide-react";
import { BrandIcon } from "../../components/BrandIcon";
import { ComposerAssetPicker } from "../../components/ComposerAssetPicker";
import { LineIcon } from "../../components/LineIcon";
import { MembershipMark } from "../../components/MembershipMark";
import { SelectMenu } from "../../components/SelectMenu";
import { MODEL_GROUPS, getModelById } from "../../catalog/models";
import type { ModelModality } from "../../catalog/types";
import { MembershipDialog } from "../account/MembershipDialog";
import { CreateSkillDialog, type CreateSkillFormValues } from "../skill-home/CreateSkillDialog";
import { SKILLS } from "../../catalog/skills";
import { createAgentGateway, type AgentGateway } from "../../lib/agent";
import {
  loadLocalCanvasDocument,
  saveCloudCanvasDocument,
  saveLocalCanvasDocument,
} from "../../lib/canvasState";
import { isCloudConfigured, persistWorkToCloud } from "../../lib/cloud";
import { registerLocalFiles } from "../../lib/localFiles";
import { saveWork } from "../../lib/work";
import type {
  AgentJob,
  CanvasDocument,
  CloudWorkState,
  CreationLine,
  DraftAttachment,
  PendingAttachment,
  WebWork,
  WorkCreationConfig,
} from "../../types";

type CanvasView = "workflow" | "storyboard";
type CanvasTool = "select" | "pan";
type DrawerKind = "add" | "tools" | "assets" | "characters" | "history" | "overview";
type AgentPanelTab = "conversation" | "skills" | "history" | "settings";
type OverlayKind = "shortcuts" | "tutorial" | "share" | "clear-data" | "style-library" | "effect-library";
type ComposerMenuKind = "assets" | "model" | "skill" | "mode" | null;
type HeaderMenuKind = "board" | "credits" | "profile" | null;
type AgentHeaderPopover = "history" | "share" | null;
type AssetSource = "personal" | "agent";
type AssetTag = "其它" | "人物" | "场景" | "物品" | "风格" | "音效";
type CanvasSkillTab = "common" | "favorite" | "mine";
type CanvasSkillCatalogTab = "skills" | "favorite" | "mine";
type CanvasInsertSubmenu = "script" | "assets" | null;
type CanvasHistorySource = "libtv" | "generator" | "webui" | "comfyui" | "ai-app";
type CanvasHistoryMedia = "image" | "video" | "audio";

type CanvasInsertMenuState = {
  clientX: number;
  clientY: number;
  flowX: number;
  flowY: number;
  submenu: CanvasInsertSubmenu;
  submenuSide: "left" | "right";
};

type CanvasHistoryPickerItem = {
  id: string;
  kind: WorkflowNodeKind;
  title: string;
  description: string;
  source: "attachment" | "node";
  sourceId: string;
};

type CanvasLibrarySkill = {
  id: string;
  title: string;
  slug: string;
  description: string;
  creator?: string;
  category?: string;
  guide?: string;
  steps?: string[];
  useCases?: string[];
};
type WorkflowNodeKind = "text" | "script" | "image" | "audio" | "video" | "compose";
type WorkflowNodeStatus = "idle" | "ready" | "running" | "done" | "failed";
type WorkflowNodeVariant = "default" | "director" | "script-new" | "script-legacy";
type OverviewKindFilter = "all" | WorkflowNodeKind | "director" | "legacy-script";

const OVERVIEW_FILTER_OPTIONS: Array<{ value: OverviewKindFilter; label: string }> = [
  { value: "all", label: "全部" },
  { value: "text", label: "文字" },
  { value: "script", label: "脚本" },
  { value: "image", label: "图片" },
  { value: "audio", label: "音频" },
  { value: "video", label: "视频" },
  { value: "compose", label: "视频合成" },
  { value: "director", label: "导演台" },
  { value: "legacy-script", label: "脚本（旧版）" },
];

const WORKFLOW_STATUS_OPTIONS: Array<{ value: WorkflowNodeStatus; label: string }> = [
  { value: "idle", label: "待处理" },
  { value: "ready", label: "可执行" },
  { value: "running", label: "执行中" },
  { value: "done", label: "已完成" },
  { value: "failed", label: "失败" },
];

type WorkflowNodeData = {
  kind: WorkflowNodeKind;
  title: string;
  description: string;
  status: WorkflowNodeStatus;
  eyebrow: string;
  assetName?: string;
  variant?: WorkflowNodeVariant;
  prompt?: string;
  model?: string;
  imageMode?: string;
  videoMode?: string;
  aspectRatio?: string;
  quality?: string;
  resolution?: string;
  outputCount?: number;
  duration?: number;
  voice?: string;
  speed?: number;
  tone?: number;
  volume?: number;
  timbrePitch?: number;
  timbreIntensity?: number;
  timbre?: number;
  audioEffect?: string;
  webSearch?: boolean;
  autoValidate?: boolean;
} & Record<string, unknown>;

type WorkflowNode = Node<WorkflowNodeData, "workflow-node">;

type CanvasNodeActions = {
  update: (nodeId: string, patch: Partial<WorkflowNodeData>) => void;
  run: (nodeId: string) => void;
  quickAction: (nodeId: string, action: string) => void;
  openDirector: (nodeId: string) => void;
};

type PresetDefinition = {
  name: string;
  author: string;
  category: string;
  uses: string;
  model: string;
  commercial: boolean;
};

const CanvasNodeActionsContext = createContext<CanvasNodeActions | null>(null);

interface SuggestedSkill {
  id: string;
  title: string;
  description: string;
  prompt: string;
}

interface ActivityItem {
  id: string;
  label: string;
  time: string;
}

interface RunRecord {
  id: string;
  prompt: string;
  state: AgentJob["state"];
  message: string;
  output?: string;
  time: string;
}

type IconName =
  | "add"
  | "assets"
  | "audio"
  | "character"
  | "close"
  | "collapse-panel"
  | "compose"
  | "copy"
  | "download"
  | "edge"
  | "grid"
  | "history"
  | "image"
  | "map"
  | "move"
  | "panel"
  | "script"
  | "share"
  | "send"
  | "sparkle"
  | "text"
  | "tools"
  | "tutorial"
  | "redo"
  | "undo"
  | "upload"
  | "video"
  | "workflow";

const LINE_LABELS: Record<CreationLine, string> = {
  novel: "写小说",
  n2d: "制漫剧",
  comic: "画漫画",
  ad: "拍广告",
  mv: "制 MV",
  song: "写歌",
};

const NODE_LIBRARY: Array<{
  kind: WorkflowNodeKind;
  label: string;
  description: string;
  eyebrow: string;
}> = [
  { kind: "text", label: "文本输入", description: "输入故事、提示词或导入源文件", eyebrow: "INPUT" },
  { kind: "script", label: "脚本规划", description: "拆解结构、镜头和生成任务", eyebrow: "SCRIPT" },
  { kind: "image", label: "图片生成", description: "生成角色、场景和关键帧", eyebrow: "IMAGE" },
  { kind: "audio", label: "音频生成", description: "生成配音、音乐与声音设计", eyebrow: "AUDIO" },
  { kind: "video", label: "视频生成", description: "把关键帧转成动态镜头", eyebrow: "VIDEO" },
  { kind: "compose", label: "合成输出", description: "整理素材并导出最终成品", eyebrow: "OUTPUT" },
];

const ADD_NODE_OPTIONS: Array<{
  id: string;
  kind: WorkflowNodeKind;
  label: string;
  badge?: string;
}> = [
  { id: "text", kind: "text", label: "文本" },
  { id: "image", kind: "image", label: "图片" },
  { id: "video", kind: "video", label: "视频" },
  { id: "compose", kind: "compose", label: "视频合成", badge: "Beta" },
  { id: "director", kind: "script", label: "导演台", badge: "NEW" },
  { id: "audio", kind: "audio", label: "音频" },
  { id: "script", kind: "script", label: "脚本" },
  { id: "library", kind: "image", label: "素材库", badge: "NEW" },
];

const TOOLBOX_TEMPLATES = [
  "左弧滑行",
  "电商手机弹出效果",
  "咖啡杯出场",
  "360° 旋转展示",
  "机械臂视角",
  "Live 2D",
  "瞳孔拉近",
  "飞鸟解体",
  "破盒而出",
  "商品震撼登场",
  "反重力漂浮",
  "大师分镜九宫格",
];

const STYLE_PRESETS: PresetDefinition[] = [
  { name: "复古马卡龙", author: "AI搬砖侠", category: "推荐", uses: "359", model: "Lib Image", commercial: true },
  { name: "新中式", author: "AI搬砖侠", category: "推荐", uses: "444", model: "Lib Image", commercial: true },
  { name: "岁月港风", author: "消息免打扰", category: "摄影写真", uses: "354", model: "Lib Image", commercial: true },
  { name: "新国韵", author: "AI萨大法官", category: "动漫游戏", uses: "464", model: "Lib Image", commercial: true },
  { name: "清风竹林", author: "消息免打扰", category: "风格插画", uses: "107", model: "Lib Image", commercial: true },
  { name: "小岛微风", author: "捏捏AI", category: "摄影写真", uses: "870", model: "Midjourney V7", commercial: true },
  { name: "慢门胶片", author: "vibe fckuing", category: "摄影写真", uses: "273", model: "Lib Image", commercial: true },
  { name: "曜黑幻境", author: "鱿鱼chill", category: "动漫游戏", uses: "788", model: "Midjourney Niji 7", commercial: true },
  { name: "霸王戏梦", author: "大葱同学", category: "新中式", uses: "170", model: "Lib Image", commercial: true },
  { name: "莫奈花园", author: "可可大王", category: "风格插画", uses: "241", model: "Lib Image", commercial: true },
  { name: "毛绒织梦", author: "孤雌的白日梦", category: "创意玩法", uses: "99", model: "Midjourney V7", commercial: true },
  { name: "梦核赛博", author: "AI搬砖侠", category: "动漫游戏", uses: "300", model: "Lib Image", commercial: true },
];
const EFFECT_PRESETS: PresetDefinition[] = [
  { name: "小蜜蜂运镜", author: "vibe fckuing", category: "推荐", uses: "1900", model: "Lib Video 2.0", commercial: true },
  { name: "穿云而入", author: "管夯工作台", category: "推荐", uses: "946", model: "Lib Video 2.0", commercial: true },
  { name: "飞跃地平线", author: "vibe fckuing", category: "推荐", uses: "1600", model: "Lib Video 2.0", commercial: true },
  { name: "逆转引力", author: "omom", category: "推荐", uses: "340", model: "Lib Video 2.0", commercial: true },
  { name: "地球缩放", author: "孤雌的白日梦", category: "创意玩法", uses: "296", model: "Lib Video 2.0", commercial: true },
  { name: "瞳孔推镜", author: "消息免打扰", category: "摄影写真", uses: "668", model: "Lib Video 2.0", commercial: true },
  { name: "产品扫光", author: "鱿鱼chill", category: "电商营销", uses: "1600", model: "Lib Video 2.0", commercial: true },
  { name: "水下慢镜头", author: "AI萨大法官", category: "摄影写真", uses: "396", model: "Lib Video 2.0", commercial: true },
  { name: "微距推镜", author: "可可大王", category: "电商营销", uses: "429", model: "Lib Video 2.0", commercial: true },
  { name: "子弹时间", author: "汪往旺", category: "动漫游戏", uses: "449", model: "Lib Video 2.0", commercial: true },
  { name: "星尘降临", author: "管夯工作台", category: "创意玩法", uses: "219", model: "Lib Video 2.0", commercial: true },
  { name: "机甲变身", author: "凌晨四点实验室", category: "动漫游戏", uses: "185", model: "Lib Video 2.0", commercial: true },
];
const PRESET_CATEGORIES = ["推荐", "Midjourney", "摄影写真", "电商营销", "动漫游戏", "风格插画", "平面设计", "建筑及室内设计", "创意玩法", "文创周边", "小说推文"];

function nodeRuntimeDefaults(kind: WorkflowNodeKind, variant: WorkflowNodeVariant = "default"): Partial<WorkflowNodeData> {
  if (kind === "image") return { prompt: "", model: "Lib Image", imageMode: "文生图", aspectRatio: "16:9", quality: "标准画质", resolution: "2K", outputCount: 1 };
  if (kind === "video") return { prompt: "", model: "2.0", videoMode: "文生视频", aspectRatio: "16:9", resolution: "720P", duration: 5, outputCount: 1, webSearch: true, autoValidate: true };
  if (kind === "audio") return { prompt: "", model: "Minimax-speech-2.8-hd", voice: "少女音色", speed: 1, tone: 0, volume: 1, timbrePitch: 0, timbreIntensity: 0, timbre: 0, audioEffect: "无" };
  if (kind === "script") return { prompt: "", model: variant === "director" ? "Director 3D" : "GVLM 3.1", variant };
  if (kind === "text") return { prompt: "", model: "GVLM 3.1" };
  return {};
}
const CANVAS_HISTORY_SOURCES: Array<{ id: CanvasHistorySource; label: string }> = [
  { id: "libtv", label: "LibTV" },
  { id: "generator", label: "Lib生成器" },
  { id: "webui", label: "WebUI" },
  { id: "comfyui", label: "ComfyUI" },
  { id: "ai-app", label: "AI应用" },
];
const CANVAS_HISTORY_MEDIA: Array<{ id: CanvasHistoryMedia; label: string }> = [
  { id: "image", label: "图片" },
  { id: "video", label: "视频" },
  { id: "audio", label: "音频" },
];

const AGENT_SKILL_LIBRARY: CanvasLibrarySkill[] = [
  { id: "pixar", title: "皮克斯动画广告", slug: "/pixar-animated-ad-creator", category: "商业广告", description: "从角色立绘、分镜草图到最终合成带广告歌的完整成片" },
  { id: "viral", title: "爆款拉片复刻", slug: "/viral-video-replicator", category: "商业广告", description: "AI 拆解爆款视频，一键复刻同款" },
  { id: "neo-chinese", title: "新中式美学TVC", slug: "/neo-chinese-aesthetic-tvc", category: "商业广告", description: "从妆造、布景到广告成片的一站式视觉方案" },
  { id: "wuxia", title: "古典武侠电影全流程导演", slug: "/hujinquanwuxia", category: "视觉风格", description: "把模糊的武侠主题转化为视频生产方案" },
  { id: "gameplay", title: "游戏实机PV", slug: "/gameplay-pv-builder", category: "商业广告", description: "UI 像素锚定不形变，打造 3A 级游戏效果" },
  { id: "female-drama", title: "精品女频短剧一键成片", slug: "/xingrannvpin", category: "剧情短片", description: "精品短剧工业化全流程一键出片" },
  { id: "koreeda", title: "是枝裕和电影美学", slug: "/koreeda-film-aesthetic", category: "视觉风格", description: "用日常写实的生活肌理包裹克制轻盈的情感" },
  { id: "wes", title: "韦斯安德森电影美学", slug: "/wes-anderson-aesthetics", category: "视觉风格", description: "深度还原对称构图与标志性视听语言" },
  { id: "narrative", title: "剧情TVC广告片", slug: "/narrative-tvc-creator", category: "商业广告", description: "创作剧情化商品、品牌与服务类 TVC" },
  { id: "western", title: "伊斯特伍德西部片", slug: "/eastwood-western-style", category: "剧情短片", description: "极静对峙后瞬间爆发的枪战大片" },
  { id: "car", title: "一键爽感轰炸流汽车TVC", slug: "/high-impact-car-tvc", category: "商业广告", description: "上传图片或文字即可打造高冲击汽车广告" },
  { id: "travel", title: "旅拍大师", slug: "/cinematic-travel-vlog-maker", category: "剧情短片", description: "把地点、人物参考和文案做成电影感旅拍短片" },
];

const CANVAS_MODALITY_LABELS: Record<ModelModality, string> = {
  text: "文字",
  image: "图片",
  video: "视频",
  audio: "音频",
};

function loadCanvasFavoriteSkills() {
  try {
    return new Set<string>(JSON.parse(localStorage.getItem("anime-armory.web.favorite-skills") ?? "[]") as string[]);
  } catch {
    return new Set<string>();
  }
}

const AGENT_SKILL_BATCHES = [
  AGENT_SKILL_LIBRARY.slice(0, 4),
  AGENT_SKILL_LIBRARY.slice(4, 8),
  AGENT_SKILL_LIBRARY.slice(8, 12),
];

function suggestedSkillsFor(work: WebWork): SuggestedSkill[] {
  const catalogSkills = SKILLS
    .filter((skill) => skill.line === work.line)
    .map((skill) => ({
      id: skill.id,
      title: skill.title,
      description: skill.description,
      prompt: `请使用 ${skill.skill} Skill 处理当前作品。\n\n${skill.guide}`,
    }));
  const custom = work.creationConfig?.skillDefinition;
  if (!custom || !work.creationConfig?.skillId) return catalogSkills;
  return [
    {
      id: work.creationConfig.skillId,
      title: custom.title,
      description: custom.description,
      prompt: `请按我的「${custom.title}」Skill 执行当前作品。\n\n${custom.guide}`,
    },
    ...catalogSkills.filter((skill) => skill.id !== work.creationConfig?.skillId),
  ];
}

const CHARACTER_PRESETS = [
  { id: "fresh-girl", name: "甜妹 / 清新少女", detail: "女主 · 现代 · 青年 · 温柔" },
  { id: "ceo", name: "霸总 / 精英大佬", detail: "男主 · 现代 · 冷峻 · 精英" },
  { id: "gentleman", name: "温柔熟男 / 理想男友", detail: "男主 · 现代 · 温柔 · 成熟" },
  { id: "heiress", name: "清冷千金 / 白切黑女主", detail: "女主 · 现代 · 清冷 · 反差" },
  { id: "ancient-man", name: "古风男主", detail: "男主 · 古风 · 青年 · 英气" },
  { id: "ancient-woman", name: "古风女主", detail: "女主 · 古风 · 青年 · 清雅" },
  { id: "villainess", name: "恶毒女配 / 白莲花", detail: "女配 · 现代 · 反派 · 明艳" },
  { id: "father", name: "正派长辈 / 父", detail: "长辈 · 现代 · 稳重 · 正派" },
  { id: "mother", name: "正派长辈 / 母", detail: "长辈 · 现代 · 温和 · 正派" },
  { id: "relative", name: "反派长辈 / 势利亲戚", detail: "长辈 · 现代 · 反派 · 强势" },
  { id: "ordinary", name: "生活方式普通人", detail: "配角 · 现代 · 自然 · 生活感" },
  { id: "fashion", name: "时尚感亚洲青年", detail: "主角 · 现代 · 时尚 · 都市" },
];

function Icon({ name }: { name: IconName }) {
  let content: ReactNode;
  switch (name) {
    case "add": content = <><path d="M12 5v14M5 12h14" /></>; break;
    case "move": content = <><path d="M12 3v18M3 12h18M12 3l-3 3m3-3 3 3M12 21l-3-3m3 3 3-3M3 12l3-3m-3 3 3 3m15-3-3-3m3 3-3 3" /></>; break;
    case "tools": content = <><path d="M4 7h10M4 17h16M14 7l2-2v4l-2-2ZM10 17l-2-2v4l2-2Z" /></>; break;
    case "assets": content = <><rect x="3.5" y="5" width="17" height="14" rx="2" /><path d="m5 16 4-4 3 3 2-2 5 5M8 9h.01" /></>; break;
    case "character": content = <><circle cx="12" cy="8" r="3" /><path d="M5.5 20c.8-4 3-6 6.5-6s5.7 2 6.5 6" /></>; break;
    case "history": content = <><path d="M4 8V4m0 0h4M4 4l3 3a8 8 0 1 1-2 8" /><path d="M12 8v5l3 2" /></>; break;
    case "tutorial": content = <><path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3V4Z" /><path d="M8 4v13a3 3 0 0 0 3 3M11 8h5M11 12h4" /></>; break;
    case "workflow": content = <><rect x="3" y="4" width="6" height="5" rx="1" /><rect x="15" y="15" width="6" height="5" rx="1" /><path d="M9 6.5h4a4 4 0 0 1 4 4V15" /></>; break;
    case "text": content = <><rect x="5" y="3" width="14" height="18" rx="2" /><path d="M8.5 8h7M8.5 12h7M8.5 16h5" /></>; break;
    case "script": content = <><path d="M6 3h9l3 3v15H6zM15 3v4h4M9 11h6M9 15h6" /></>; break;
    case "image": content = <><rect x="3.5" y="4" width="17" height="16" rx="2" /><circle cx="9" cy="9" r="1.5" /><path d="m5 18 5-5 3 3 2-2 4 4" /></>; break;
    case "audio": content = <><path d="M9 18V6l9-2v12" /><circle cx="6" cy="18" r="3" /><circle cx="15" cy="16" r="3" /></>; break;
    case "video": content = <><rect x="3" y="5" width="14" height="14" rx="2" /><path d="m17 10 4-2v8l-4-2ZM9 9l4 3-4 3z" /></>; break;
    case "compose": content = <><rect x="4" y="4" width="11" height="11" rx="2" /><path d="M9 9h11v11H9z" /></>; break;
    case "copy": content = <><rect x="8" y="8" width="11" height="11" rx="2" /><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3" /></>; break;
    case "download": content = <><path d="M12 4v11m0 0 4-4m-4 4-4-4" /><path d="M5 18v2h14v-2" /></>; break;
    case "map": content = <><path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3zM9 3v15M15 6v15" /></>; break;
    case "edge": content = <><circle cx="5" cy="17" r="2" /><circle cx="19" cy="7" r="2" /><path d="M7 16c4-1 4-7 10-8" /></>; break;
    case "grid": content = <><path d="M4 4h16v16H4zM4 10h16M4 15h16M10 4v16M15 4v16" /></>; break;
    case "undo": content = <><path d="M9 7 4 12l5 5" /><path d="M5 12h8a6 6 0 0 1 6 6" /></>; break;
    case "redo": content = <><path d="m15 7 5 5-5 5" /><path d="M19 12h-8a6 6 0 0 0-6 6" /></>; break;
    case "upload": content = <><path d="M12 16V4m0 0L7 9m5-5 5 5" /><path d="M5 14v5h14v-5" /></>; break;
    case "panel": content = <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M15 4v16M18 9h.01M18 13h.01" /></>; break;
    case "sparkle": content = <><path d="m12 3 1.4 4.2L18 9l-4.6 1.8L12 15l-1.4-4.2L6 9l4.6-1.8zM19 15l.7 2.3L22 18l-2.3.7L19 21l-.7-2.3L16 18l2.3-.7z" /></>; break;
    case "send": content = <><path d="m5 12 14-7-4 14-3-6zM12 13l7-8" /></>; break;
    case "share": content = <><circle cx="18" cy="5" r="2.5" /><circle cx="6" cy="12" r="2.5" /><circle cx="18" cy="19" r="2.5" /><path d="m8.2 10.8 7.6-4.5M8.2 13.2l7.6 4.5" /></>; break;
    case "close": content = <><path d="m6 6 12 12M18 6 6 18" /></>; break;
    case "collapse-panel": content = <><path d="M6 4v16M10 12h9M15 8l4 4-4 4" /></>; break;
  }
  return <svg className={`canvas-icon canvas-icon-${name}`} viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{content}</svg>;
}

function nodeDefinition(kind: WorkflowNodeKind) {
  return NODE_LIBRARY.find((item) => item.kind === kind) ?? NODE_LIBRARY[0];
}

function makeEdge(id: string, source: string, target: string, animated = false): Edge {
  return {
    id,
    source,
    target,
    animated,
    type: "smoothstep",
    markerEnd: { type: MarkerType.ArrowClosed },
    className: "workflow-edge",
  };
}

type WorkflowStagePreset = Pick<WorkflowNodeData, "kind" | "title" | "description" | "eyebrow" | "assetName">;

const WORKFLOW_STAGES: Record<CreationLine, readonly WorkflowStagePreset[]> = {
  novel: [
    { kind: "script", eyebrow: "BLUEPRINT", title: "设定与故事大纲", description: "世界规则、人物弧光与卷章结构", assetName: "开发包/story_bible.md" },
    { kind: "text", eyebrow: "DRAFT", title: "章节正文", description: "按大纲连续生成并维护伏笔状态", assetName: "正文/第1章.md" },
    { kind: "script", eyebrow: "EDIT", title: "专业编辑", description: "结构、节奏、人物与语言返修", assetName: "评审/edit_report.md" },
    { kind: "compose", eyebrow: "DELIVERY", title: "成稿与发布包", description: "汇总正文、设定和修订记录", assetName: "导出/manuscript.md" },
  ],
  n2d: [
    { kind: "script", eyebrow: "SCRIPT", title: "分集脚本与分镜", description: "场次、镜头、对白与生成提示词", assetName: "脚本/第1集/shot_plan.json" },
    { kind: "audio", eyebrow: "VOICE", title: "配音与声音", description: "角色对白、旁白和声音设计", assetName: "配音/第1集/voiceover.wav" },
    { kind: "image", eyebrow: "FRAME", title: "一致性关键画面", description: "定妆、场景与镜头工作图", assetName: "出图/第1集/关键帧/" },
    { kind: "video", eyebrow: "VIDEO", title: "视频镜头", description: "首尾帧、运镜和动态版本", assetName: "出视频/第1集/视频/" },
    { kind: "compose", eyebrow: "MASTER", title: "漫剧成片", description: "时间线、字幕、音乐与成片 QC", assetName: "合成/第1集/master.mp4" },
  ],
  comic: [
    { kind: "script", eyebrow: "SCRIPT", title: "分话与分格脚本", description: "页面、画格、动作、对白与翻页节奏", assetName: "脚本/第1话/panel_script.json" },
    { kind: "text", eyebrow: "BIBLE", title: "角色与场景设定", description: "锁定身份、服装、道具和画风", assetName: "设定库/story_bible.md" },
    { kind: "image", eyebrow: "LAYOUT", title: "页面排版", description: "格框层级、气泡安全区与阅读动线", assetName: "排版/第1话/page_layout.json" },
    { kind: "image", eyebrow: "PANELS", title: "漫画画格", description: "按分格合同生成并完成一致性 QC", assetName: "出图/第1话/画格/" },
    { kind: "compose", eyebrow: "EXPORT", title: "嵌字与漫画导出", description: "对白、拟声、单页与条漫长图", assetName: "导出/第1话/long_strip.png" },
  ],
  ad: [
    { kind: "script", eyebrow: "STRATEGY", title: "广告策略", description: "受众、卖点、证据与转化目标", assetName: "策略/creative_brief.json" },
    { kind: "script", eyebrow: "SCRIPT", title: "广告脚本与镜头表", description: "前三秒钩子、口播、画面与 CTA", assetName: "脚本/shot_list.json" },
    { kind: "image", eyebrow: "VISUAL", title: "广告画面", description: "产品主视觉、场景与关键帧", assetName: "出图/key_visuals/" },
    { kind: "video", eyebrow: "CUT", title: "视频版本", description: "动作镜头、字幕和多尺寸剪辑", assetName: "出视频/variants/" },
    { kind: "compose", eyebrow: "DELIVERY", title: "投放交付包", description: "成片、评分、合规与平台版本", assetName: "导出/campaign_pack/" },
  ],
  mv: [
    { kind: "audio", eyebrow: "BEAT", title: "歌曲与节拍地图", description: "BPM、强拍、能量曲线与段落", assetName: "节拍/beatgrid.json" },
    { kind: "script", eyebrow: "VISION", title: "视觉蓝图与镜头", description: "视觉母题、场景、动作和卡点规划", assetName: "分镜/clip_plan.json" },
    { kind: "image", eyebrow: "FRAME", title: "MV 关键画面", description: "共享定妆和分段分镜图", assetName: "出图/分段分镜/" },
    { kind: "video", eyebrow: "VIDEO", title: "卡点视频片段", description: "按段落和节拍生成、评分与挑版", assetName: "出视频/takes/" },
    { kind: "compose", eyebrow: "MASTER", title: "MV 母版", description: "歌词字幕、音画同步与交付 QC", assetName: "导出/master.mp4" },
  ],
  song: [
    { kind: "text", eyebrow: "LYRICS", title: "创作简报与歌词", description: "主题、听众、Hook 与结构化歌词", assetName: "词/lyrics.md" },
    { kind: "script", eyebrow: "FORM", title: "曲式与旋律草图", description: "段落、和声、速度与 topline 方向", assetName: "歌/song_form.json" },
    { kind: "audio", eyebrow: "TAKES", title: "作曲演唱版本", description: "生成多版歌曲并结构化试听挑选", assetName: "歌/takes/" },
    { kind: "audio", eyebrow: "MIX", title: "混音与母带", description: "人声、编曲、响度和真峰值检查", assetName: "混音/pre_master.wav" },
    { kind: "compose", eyebrow: "RELEASE", title: "歌曲发布包", description: "母版、权益元数据与发布资料", assetName: "导出/release_pack.json" },
  ],
};

function initialGraph(work: WebWork): { nodes: WorkflowNode[]; edges: Edge[] } {
  const sourceName = work.attachments[0]?.name || (work.prompt ? "创作需求" : "未命名灵感");
  const nodes: WorkflowNode[] = [{
    id: "text-source",
    type: "workflow-node",
    position: { x: 40, y: 220 },
    data: { kind: "text", title: sourceName, description: "创作目标、提示词与源文件", status: "done", eyebrow: "INPUT", assetName: work.attachments[0]?.name },
  }];
  const edges: Edge[] = [];
  let previous = "text-source";
  WORKFLOW_STAGES[work.line].forEach((stage, index) => {
    const id = `stage-${index + 1}`;
    nodes.push({
      id,
      type: "workflow-node",
      position: { x: 360 + index * 330, y: 220 },
      data: { ...stage, status: index === 0 ? "ready" : "idle" },
    });
    edges.push(makeEdge(`${previous}-${id}`, previous, id, index === 0));
    previous = id;
  });
  return { nodes, edges };
}

function WorkflowNodeCard({ id, data, selected }: NodeProps<WorkflowNode>) {
  const actions = useContext(CanvasNodeActionsContext);
  const flow = useReactFlow<WorkflowNode, Edge>();
  const [controlMenu, setControlMenu] = useState<"model" | "settings" | "preset" | "voice" | null>(null);
  const variant = data.variant ?? (data.kind === "script" ? "script-new" : "default");
  const prompt = typeof data.prompt === "string" ? data.prompt : "";
  const aspectRatio = String(data.aspectRatio ?? "16:9");
  const quality = String(data.quality ?? "标准画质");
  const resolution = String(data.resolution ?? (data.kind === "video" ? "720P" : "2K"));
  const outputCount = Number(data.outputCount ?? 1);
  const duration = Number(data.duration ?? 5);
  const webSearch = data.webSearch ?? true;
  const autoValidate = data.autoValidate ?? true;
  const incomingVideoCount = data.kind === "compose"
    ? Math.max(Number(data.connectedMediaCount ?? 0), flow.getEdges().filter((edge) => edge.target === id).filter((edge) => flow.getNode(edge.source)?.data.kind === "video").length)
    : 0;

  useEffect(() => {
    if (!selected) setControlMenu(null);
  }, [selected]);

  const update = (patch: Partial<WorkflowNodeData>) => actions?.update(id, patch);
  const quick = (action: string) => actions?.quickAction(id, action);
  const setPrompt = (value: string) => update({ prompt: value, description: value.trim() || data.description });
  const stopPointer = (event: ReactPointerEvent<HTMLElement>) => event.stopPropagation();
  const modelOptions = data.kind === "image"
    ? ["Lib Image", "Seedream 5.0 Pro", "Midjourney V7", "Qwen Image"]
    : data.kind === "video"
      ? ["2.0", "Lib Video 2.0", "Seedance 2.0", "Veo 3.1"]
      : data.kind === "audio"
        ? ["Minimax-speech-2.8-hd", "CosyVoice 3", "Fish Speech"]
        : ["GVLM 3.1", "Gemini 3 Pro", "GPT-5.2"];

  const quickActions = data.kind === "text"
    ? ["自己编写内容", "文生视频", "图片反推提示词", "文字生音乐"]
    : data.kind === "image"
      ? ["图生图", "图片高清", "参考", "标记", "风格"]
      : data.kind === "video"
        ? ["首尾帧生成视频", "首帧生成视频", "参考", "标记", "特效", "角色库", "运镜"]
        : data.kind === "audio"
          ? ["音频生视频", "<#> 停顿", "() 语气词"]
          : variant === "script-legacy"
            ? ["剧本生成分镜脚本", "视频参考生成分镜脚本", "角色生成分镜脚本"]
            : ["剧本生成分镜脚本", "角色生成分镜脚本", "自己编写分镜脚本"];

  const promptPlaceholder = data.kind === "text"
    ? "写下你想讲的故事、场景或角色设定。例如：一个来自未来的机器人，在城市屋顶看星星。"
    : data.kind === "image"
      ? "可直接文字生图，或上传图片输入文字指令对图片进行编辑，如：将背景改为雪夜"
      : data.kind === "video"
        ? "描述你想要生成的画面内容，@引用素材"
        : data.kind === "audio"
          ? "输入要合成的文本"
          : variant === "script-legacy"
            ? "描述剧情或添加角色参考、视频参考等，为你生成分镜脚本"
            : "描述剧情片段、故事，为你生成分镜脚本";

  const renderPromptNode = () => (
    <div className="workflow-node-expanded nodrag nowheel" onPointerDown={stopPointer} onDoubleClick={(event) => event.stopPropagation()}>
      <small className="workflow-node-try-label">尝试：</small>
      <div className="workflow-node-quick-actions">
        {quickActions.map((action) => <button key={action} type="button" onClick={() => quick(action)}>{action}</button>)}
      </div>
      <textarea
        aria-label={`${data.title}输入内容`}
        value={prompt}
        maxLength={data.kind === "audio" ? 50000 : 4000}
        placeholder={promptPlaceholder}
        onChange={(event) => setPrompt(event.target.value)}
      />
      <div className="workflow-node-generator-bar">
        <button type="button" className="workflow-node-model-button" aria-expanded={controlMenu === "model"} onClick={() => setControlMenu((current) => current === "model" ? null : "model")}><span>{String(data.model ?? modelOptions[0])}</span><ChevronDown size={12} /></button>
        {data.kind === "image" && <button type="button" className="workflow-node-settings-button" aria-label="图片生成参数" aria-expanded={controlMenu === "settings"} onClick={() => setControlMenu((current) => current === "settings" ? null : "settings")}><Settings2 size={13} /><span>{aspectRatio} · {quality} · {resolution} · {outputCount}张</span></button>}
        {data.kind === "video" && <>
          <button type="button" className="workflow-node-mode-button" onClick={() => update({ videoMode: data.videoMode === "文生视频" ? "首帧生成视频" : "文生视频" })}>{data.videoMode ?? "文生视频"}</button>
          <button type="button" className="workflow-node-settings-button" aria-label="视频生成参数" aria-expanded={controlMenu === "settings"} onClick={() => setControlMenu((current) => current === "settings" ? null : "settings")}><Settings2 size={13} /><span>{aspectRatio} · {resolution} · {duration}s · {outputCount}个</span></button>
        </>}
        {data.kind === "audio" && <button type="button" className="workflow-node-settings-button" aria-expanded={controlMenu === "voice"} onClick={() => setControlMenu((current) => current === "voice" ? null : "voice")}><Mic2 size={13} /><span>{String(data.voice ?? "少女音色")}</span></button>}
        {data.kind === "image" && <button type="button" className="workflow-node-preset-button" aria-expanded={controlMenu === "preset"} onClick={() => setControlMenu((current) => current === "preset" ? null : "preset")}><Sparkles size={13} />预设</button>}
        <button type="button" className="workflow-node-attach-button" aria-label="添加参考素材" onClick={() => quick("添加参考素材")}><Paperclip size={14} /></button>
        <button type="button" className="workflow-node-run-button" aria-label="开始生成" disabled={!prompt.trim() || data.status === "running"} onClick={() => actions?.run(id)}>{data.status === "running" ? <span className="workflow-node-spinner" /> : <ArrowUp size={15} />}</button>
      </div>
      {data.kind === "audio" && <span className="workflow-node-character-count">{prompt.length}/50000</span>}
      {controlMenu === "model" && <div className="workflow-node-control-popover is-model" role="menu" aria-label="选择节点模型">
        {modelOptions.map((model) => <button key={model} type="button" role="menuitem" className={data.model === model ? "is-active" : ""} onClick={() => { update({ model }); setControlMenu(null); }}><span>{model}</span>{data.model === model && <Check size={13} />}</button>)}
      </div>}
      {controlMenu === "settings" && data.kind === "image" && <div className="workflow-node-control-popover is-settings" role="dialog" aria-label="图片生成参数">
        <strong>图片参数</strong>
        <label><span>画面比例</span><div>{["1:1", "4:3", "3:4", "16:9", "9:16"].map((value) => <button key={value} className={aspectRatio === value ? "is-active" : ""} type="button" onClick={() => update({ aspectRatio: value })}>{value}</button>)}</div></label>
        <label><span>画质</span><div>{["标准画质", "高清画质"].map((value) => <button key={value} className={quality === value ? "is-active" : ""} type="button" onClick={() => update({ quality: value })}>{value}</button>)}</div></label>
        <label><span>分辨率</span><div>{["1K", "2K", "4K"].map((value) => <button key={value} className={resolution === value ? "is-active" : ""} type="button" onClick={() => update({ resolution: value })}>{value}</button>)}</div></label>
        <label><span>生成数量</span><div>{[1, 2, 4].map((value) => <button key={value} className={outputCount === value ? "is-active" : ""} type="button" onClick={() => update({ outputCount: value })}>{value}张</button>)}</div></label>
      </div>}
      {controlMenu === "settings" && data.kind === "video" && <div className="workflow-node-control-popover is-settings" role="dialog" aria-label="视频生成参数">
        <strong>视频参数</strong>
        <label><span>画面比例</span><div>{["16:9", "9:16", "1:1", "4:3"].map((value) => <button key={value} className={aspectRatio === value ? "is-active" : ""} type="button" onClick={() => update({ aspectRatio: value })}>{value}</button>)}</div></label>
        <label><span>清晰度</span><div>{["720P", "1080P"].map((value) => <button key={value} className={resolution === value ? "is-active" : ""} type="button" onClick={() => update({ resolution: value })}>{value}</button>)}</div></label>
        <label><span>时长</span><div>{[5, 8, 10].map((value) => <button key={value} className={duration === value ? "is-active" : ""} type="button" onClick={() => update({ duration: value })}>{value}s</button>)}</div></label>
        <label><span>生成数量</span><div>{[1, 2, 4].map((value) => <button key={value} className={outputCount === value ? "is-active" : ""} type="button" onClick={() => update({ outputCount: value })}>{value}个</button>)}</div></label>
      </div>}
      {controlMenu === "preset" && <div className="workflow-node-control-popover is-preset" role="menu" aria-label="图片预设">
        {["电影感构图", "商业产品摄影", "动漫分镜", "清透人像", "新中式氛围"].map((preset) => <button key={preset} type="button" role="menuitem" onClick={() => { setPrompt(`${preset}，${prompt || "主体清晰，光影细腻"}`); setControlMenu(null); }}><Sparkles size={13} />{preset}</button>)}
      </div>}
      {controlMenu === "voice" && <div className="workflow-node-control-popover is-model" role="menu" aria-label="选择音色">
        {["少女音色", "温柔女声", "磁性男声", "少年音色", "旁白男声"].map((voice) => <button key={voice} type="button" role="menuitem" className={data.voice === voice ? "is-active" : ""} onClick={() => { update({ voice }); setControlMenu(null); }}><span>{voice}</span>{data.voice === voice && <Check size={13} />}</button>)}
      </div>}
      {data.kind === "video" && <details className="workflow-node-advanced" open>
        <summary>高级设置<ChevronDown size={13} /></summary>
        <label><span>联网搜索</span><button type="button" role="switch" aria-checked={webSearch} className={webSearch ? "is-on" : ""} onClick={() => update({ webSearch: !webSearch })}><i /></button></label>
        <label><span>自动校验素材</span><button type="button" role="switch" aria-checked={autoValidate} className={autoValidate ? "is-on" : ""} onClick={() => update({ autoValidate: !autoValidate })}><i /></button></label>
      </details>}
      {data.kind === "audio" && <AudioNodeControls data={data} update={update} />}
    </div>
  );

  return (
    <article className={`workflow-node-card kind-${data.kind} variant-${variant} status-${data.status}${selected ? " is-selected is-expanded" : ""}`}>
      <Handle type="target" position={Position.Left} className="workflow-handle workflow-handle-target" />
      <header>
        <span className="workflow-node-icon"><Icon name={variant === "director" ? "workflow" : data.kind} /></span>
        <span className="workflow-node-heading"><small>{data.eyebrow}</small><strong>{data.title}</strong></span>
        <i className="workflow-node-status" aria-label={data.status} />
      </header>
      {!selected && (data.kind === "image" || data.kind === "video") && (
        <div className={`workflow-node-preview preview-${data.kind}`}><span /><span /><span />{data.kind === "video" && <i><Icon name="video" /></i>}</div>
      )}
      {!selected && data.kind === "audio" && <div className="workflow-node-waveform" aria-hidden="true">{[8, 15, 10, 23, 18, 27, 12, 21, 9, 18, 13, 25, 16, 9].map((height, index) => <i key={`${height}-${index}`} style={{ height }} />)}</div>}
      {selected && variant === "director" ? <div className="workflow-director-node nodrag" onPointerDown={stopPointer}><div><Camera size={26} /><span><i /><i /><i /></span></div><p>在3D空间中搭建场景并进行多视角截图</p><button type="button" onClick={() => actions?.openDirector(id)}><Maximize2 size={14} />打开导演台</button></div>
        : selected && data.kind === "compose" ? <div className="workflow-compose-node nodrag" onPointerDown={stopPointer}>{incomingVideoCount ? <><div className="workflow-compose-preview"><Play size={24} /></div><div className="workflow-compose-timeline">{Array.from({ length: incomingVideoCount }).map((_, index) => <span key={index}><i />片段 {index + 1}<small>{String(index * 5).padStart(2, "0")}:00</small></span>)}</div><button type="button" onClick={() => actions?.run(id)}><Icon name="compose" />合成并导出</button></> : <><Icon name="compose" /><strong>空空如也</strong><span>请连接视频节点后操作</span><button type="button" onClick={() => quick("添加视频片段")}><Plus size={14} />添加视频片段</button></>}</div>
          : selected ? renderPromptNode() : <>
            <p>{data.description}</p>
            {data.assetName && <span className="workflow-node-asset">{data.assetName}</span>}
          </>}
      <footer><span>{data.status === "running" ? "生成中…" : data.status === "done" ? "已完成" : data.status === "failed" ? "执行失败" : selected ? "编辑节点参数" : "点击选择节点"}</span><b>•••</b></footer>
      <Handle type="source" position={Position.Right} className="workflow-handle workflow-handle-source" />
    </article>
  );
}

function AudioNodeControls({ data, update }: { data: WorkflowNodeData; update: (patch: Partial<WorkflowNodeData>) => void }) {
  const controls: Array<{ key: "speed" | "tone" | "volume" | "timbrePitch" | "timbreIntensity" | "timbre"; label: string; min: number; max: number; step: number; fallback: number }> = [
    { key: "speed", label: "语速", min: .5, max: 2, step: .05, fallback: 1 },
    { key: "tone", label: "声调", min: -12, max: 12, step: 1, fallback: 0 },
    { key: "volume", label: "音量", min: .1, max: 2, step: .1, fallback: 1 },
    { key: "timbrePitch", label: "音高", min: -10, max: 10, step: 1, fallback: 0 },
    { key: "timbreIntensity", label: "强度", min: -10, max: 10, step: 1, fallback: 0 },
    { key: "timbre", label: "音色调节", min: -10, max: 10, step: 1, fallback: 0 },
  ];
  return <div className="workflow-audio-controls">
    <header><strong>基础调节</strong><button type="button" onClick={() => update({ speed: 1, tone: 0, volume: 1, timbrePitch: 0, timbreIntensity: 0, timbre: 0, audioEffect: "无" })}><RotateCcw size={12} />一键重置</button></header>
    {controls.map((control, index) => <label key={control.key} className={index === 3 ? "is-section-start" : ""}><span>{index === 3 && <small>音色效果调节</small>}{control.label}</span><input type="range" min={control.min} max={control.max} step={control.step} value={Number(data[control.key] ?? control.fallback)} onChange={(event) => update({ [control.key]: Number(event.target.value) })} /><input aria-label={control.label} type="number" min={control.min} max={control.max} step={control.step} value={Number(data[control.key] ?? control.fallback)} onChange={(event) => update({ [control.key]: Number(event.target.value) })} /></label>)}
    <fieldset><legend>音效</legend>{["无", "空旷回音", "礼堂广播", "电话失真", "电音"].map((effect) => <label key={effect}><input type="radio" name={`effect-${String(data.title)}`} checked={(data.audioEffect ?? "无") === effect} onChange={() => update({ audioEffect: effect })} /><span>{effect}</span></label>)}</fieldset>
  </div>;
}

const NODE_TYPES = { "workflow-node": WorkflowNodeCard };

function StoryboardView({
  nodes,
  onOpenNode,
}: {
  nodes: WorkflowNode[];
  onOpenNode: (nodeId: string) => void;
}) {
  const lanes: Array<{ key: string; title: string; icon: IconName; nodes: WorkflowNode[] }> = [
    { key: "text", title: "文本", icon: "script", nodes: nodes.filter((node) => node.data.kind === "text" || node.data.kind === "script") },
    { key: "image", title: "图片", icon: "image", nodes: nodes.filter((node) => node.data.kind === "image") },
    { key: "media", title: "音视频", icon: "video", nodes: nodes.filter((node) => node.data.kind === "audio" || node.data.kind === "video" || node.data.kind === "compose") },
  ];
  return (
    <div className="canvas-storyboard" aria-label="故事板">
      {lanes.map((lane) => (
        <section key={lane.key} className={`canvas-storyboard-lane lane-${lane.key}`}>
          <header><span><Icon name={lane.icon} /></span><strong>{lane.title}</strong><small>{lane.nodes.length}</small></header>
          <div>
            {lane.nodes.map((node) => (
              <button key={node.id} type="button" className={`canvas-storyboard-card kind-${node.data.kind}`} onClick={() => onOpenNode(node.id)}>
                {(node.data.kind === "image" || node.data.kind === "video") && <span className="canvas-storyboard-preview"><i /><i /><i />{node.data.kind === "video" && <b><Icon name="video" /></b>}</span>}
                {node.data.kind === "audio" && <span className="canvas-storyboard-audio">{[9, 18, 12, 25, 15, 21, 10, 17, 13].map((height, index) => <i key={`${height}-${index}`} style={{ height }} />)}</span>}
                <span className="canvas-storyboard-copy"><small>{node.data.eyebrow}</small><strong>{node.data.title}</strong><p>{node.data.description}</p>{node.data.assetName && <em>{node.data.assetName}</em>}</span>
                <i className={`canvas-storyboard-status status-${node.data.status}`}>{node.data.status === "done" ? "已完成" : node.data.status === "running" ? "生成中" : node.data.status === "failed" ? "失败" : node.data.status === "ready" ? "可执行" : "待处理"}</i>
              </button>
            ))}
            {!lane.nodes.length && <div className="canvas-storyboard-empty"><Icon name={lane.icon} /><span>暂无{lane.title}节点</span></div>}
          </div>
        </section>
      ))}
    </div>
  );
}

function BottomCanvasControls({
  zoom,
  miniMapVisible,
  edgesVisible,
  snapToGridEnabled,
  overviewOpen,
  onOpenOverview,
  onOrganize,
  onToggleMiniMap,
  onToggleEdges,
  onToggleSnap,
}: {
  zoom: number;
  miniMapVisible: boolean;
  edgesVisible: boolean;
  snapToGridEnabled: boolean;
  overviewOpen: boolean;
  onOpenOverview: () => void;
  onOrganize: () => void;
  onToggleMiniMap: () => void;
  onToggleEdges: () => void;
  onToggleSnap: () => void;
}) {
  const flow = useReactFlow<WorkflowNode, Edge>();
  const [zoomMenuOpen, setZoomMenuOpen] = useState(false);
  const [zoomInput, setZoomInput] = useState(() => String(Math.round(zoom * 100)));

  useEffect(() => {
    if (!zoomMenuOpen) setZoomInput(String(Math.round(zoom * 100)));
  }, [zoom, zoomMenuOpen]);

  const applyZoom = (percent: number) => {
    const normalized = Math.min(800, Math.max(10, percent));
    setZoomInput(String(Math.round(normalized)));
    void flow.zoomTo(normalized / 100, { duration: 180 });
    setZoomMenuOpen(false);
  };

  return (
    <Panel position="bottom-left" className="canvas-bottom-controls">
      {overviewOpen ? <button type="button" onClick={onOrganize} title="整理画布（⌥ ⇧ F）" aria-label="整理画布"><Icon name="tools" /></button> : <button type="button" onClick={onOpenOverview} title="资产管理"><Icon name="assets" /><span>资产管理</span></button>}
      <span className="canvas-control-divider" />
      <button type="button" className={miniMapVisible ? "is-active" : ""} onClick={onToggleMiniMap} title="切换小地图" aria-label="切换小地图"><Icon name="map" /></button>
      <button type="button" className={edgesVisible ? "is-active" : ""} onClick={onToggleEdges} title="隐藏节点连线" aria-label="隐藏节点连线"><Icon name="edge" /></button>
      <button type="button" className={snapToGridEnabled ? "is-active" : ""} onClick={onToggleSnap} title="网格吸附" aria-pressed={snapToGridEnabled}><Icon name="grid" /></button>
      <span className="canvas-control-divider" />
      <span className="canvas-zoom-menu-wrap">
        <button type="button" className="canvas-zoom-value" onClick={() => setZoomMenuOpen((open) => !open)} aria-label="缩放选项" aria-haspopup="menu" aria-expanded={zoomMenuOpen}>{Math.round(zoom * 100)}%</button>
        {zoomMenuOpen && <div className="canvas-zoom-menu" role="menu" aria-label="缩放选项">
          <label><input aria-label="缩放比例" inputMode="numeric" value={zoomInput} onChange={(event) => setZoomInput(event.target.value.replace(/\D/g, "").slice(0, 3))} onKeyDown={(event) => { if (event.key === "Enter") applyZoom(Number(zoomInput) || 100); }} /><span>%</span></label>
          <button type="button" role="menuitem" onClick={() => void flow.zoomIn({ duration: 160 })}><span>放大</span><kbd>⌘ +</kbd></button>
          <button type="button" role="menuitem" onClick={() => void flow.zoomOut({ duration: 160 })}><span>缩小</span><kbd>⌘ −</kbd></button>
          <button type="button" role="menuitem" onClick={() => { void flow.fitView({ padding: 0.2, duration: 240 }); setZoomMenuOpen(false); }}><span>适合屏幕</span><kbd>⌘ 0</kbd></button>
          {[10, 50, 100, 800].map((percent) => <button key={percent} type="button" role="menuitem" onClick={() => applyZoom(percent)}><span>缩放至 {percent}%</span></button>)}
        </div>}
      </span>
    </Panel>
  );
}

function attachmentKind(attachment: DraftAttachment): WorkflowNodeKind {
  if (attachment.type.startsWith("image/")) return "image";
  if (attachment.type.startsWith("audio/")) return "audio";
  if (attachment.type.startsWith("video/")) return "video";
  return "text";
}

function timestamp() {
  return new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date());
}

interface GraphHistoryEntry {
  nodes: WorkflowNode[];
  edges: Edge[];
}

function cloneGraph(nodes: WorkflowNode[], edges: Edge[]): GraphHistoryEntry {
  return {
    nodes: nodes.map((node) => ({
      ...node,
      position: { ...node.position },
      data: { ...node.data },
    })),
    edges: edges.map((edge) => ({ ...edge })),
  };
}

function graphSignature(nodes: WorkflowNode[], edges: Edge[]) {
  return JSON.stringify({
    nodes: nodes.map((node) => ({ id: node.id, position: node.position, data: node.data })),
    edges: edges.map((edge) => ({ id: edge.id, source: edge.source, target: edge.target })),
  });
}

function defaultCreationConfig(work: WebWork): WorkCreationConfig {
  if (work.creationConfig) return work.creationConfig;
  const fallback = MODEL_GROUPS.text[0];
  return {
    generationMode: "auto",
    model: {
      modality: "text",
      modelId: fallback?.id ?? "",
      ...(fallback?.providerSpec ? { providerSpec: fallback.providerSpec } : {}),
    },
  };
}

export function CanvasPage({
  work,
  onHome,
  onClearLocalData,
}: {
  work: WebWork;
  onHome: () => void;
  onClearLocalData: (attachmentIds: string[]) => void;
}) {
  const storedDocument = useMemo(() => loadLocalCanvasDocument(work.id), [work.id]);
  const graph = useMemo(() => {
    if (!storedDocument?.nodes.length) return initialGraph(work);
    const storedNodes = storedDocument.nodes.map((node) => ({
      ...node,
      type: "workflow-node" as const,
      data: node.data as WorkflowNodeData,
    }));
    const storedEdges = storedDocument.edges.map((edge) => ({
      ...edge,
      type: edge.type ?? "smoothstep",
      markerEnd: { type: MarkerType.ArrowClosed },
      className: "workflow-edge",
    }));
    return { nodes: storedNodes, edges: storedEdges };
  }, [storedDocument, work.id, work.line]);
  const [nodes, setNodes, onNodesChange] = useNodesState<WorkflowNode>(graph.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(graph.edges);
  const [workName, setWorkName] = useState(storedDocument?.work.name ?? work.name);
  const [view, setView] = useState<CanvasView>(storedDocument?.preferences.view ?? "workflow");
  const [tool, setTool] = useState<CanvasTool>("select");
  const [drawer, setDrawer] = useState<DrawerKind | null>("overview");
  const [overlay, setOverlay] = useState<OverlayKind | null>(null);
  const [canvasInsertMenu, setCanvasInsertMenu] = useState<CanvasInsertMenuState | null>(null);
  const [canvasHistoryPickerOpen, setCanvasHistoryPickerOpen] = useState(false);
  const [canvasHistorySource, setCanvasHistorySource] = useState<CanvasHistorySource>("libtv");
  const [canvasHistoryMedia, setCanvasHistoryMedia] = useState<CanvasHistoryMedia>("image");
  const [canvasHistorySelection, setCanvasHistorySelection] = useState<string[]>([]);
  const [historyInsertPoint, setHistoryInsertPoint] = useState<{ x: number; y: number } | null>(null);
  const [pendingUploadPoint, setPendingUploadPoint] = useState<{ x: number; y: number } | null>(null);
  const [libraryInsertPoint, setLibraryInsertPoint] = useState<{ x: number; y: number } | null>(null);
  const [directorStudioNodeId, setDirectorStudioNodeId] = useState<string | null>(null);
  const [directorCameraPreset, setDirectorCameraPreset] = useState("正面机位");
  const [directorShotCount, setDirectorShotCount] = useState(0);
  const [libraryTab, setLibraryTab] = useState<"square" | "favorite" | "recent">("square");
  const [libraryQuery, setLibraryQuery] = useState("");
  const [libraryCategory, setLibraryCategory] = useState("推荐");
  const [libraryCommercialOnly, setLibraryCommercialOnly] = useState(false);
  const [libraryFavorites, setLibraryFavorites] = useState<Set<string>>(() => new Set());
  const [libraryRecent, setLibraryRecent] = useState<string[]>([]);
  const [libraryDetail, setLibraryDetail] = useState<PresetDefinition | null>(null);
  const [libraryMinimized, setLibraryMinimized] = useState(false);
  const [headerMenu, setHeaderMenu] = useState<HeaderMenuKind>(null);
  const [overviewBoardMenu, setOverviewBoardMenu] = useState(false);
  const [overviewBoardMoreOpen, setOverviewBoardMoreOpen] = useState(false);
  const [notice, setNotice] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [editingNodeId, setEditingNodeId] = useState<string | null>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; nodeId: string } | null>(null);
  const [gridVisible, setGridVisible] = useState(storedDocument?.preferences.gridVisible ?? true);
  const [snapToGridEnabled, setSnapToGridEnabled] = useState(storedDocument?.preferences.snapToGrid ?? false);
  const [edgesVisible, setEdgesVisible] = useState(storedDocument?.preferences.edgesVisible ?? true);
  const [miniMapVisible, setMiniMapVisible] = useState(storedDocument?.preferences.miniMapVisible ?? false);
  const [viewport, setViewport] = useState(storedDocument?.viewport ?? { x: 0, y: 0, zoom: 1 });
  const [zoom, setZoom] = useState(storedDocument?.viewport.zoom ?? 1);
  const [gateway, setGateway] = useState<AgentGateway | null>(null);
  const [prompt, setPrompt] = useState(work.prompt);
  const [activeJob, setActiveJob] = useState<AgentJob | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [panelOpen, setPanelOpen] = useState(storedDocument?.preferences.panelOpen ?? true);
  const [panelTab, setPanelTab] = useState<AgentPanelTab>("conversation");
  const [isNewConversation, setIsNewConversation] = useState(false);
  const [agentHeaderPopover, setAgentHeaderPopover] = useState<AgentHeaderPopover>(null);
  const [agentSettingsOpen, setAgentSettingsOpen] = useState(false);
  const [agentAutoMedia, setAgentAutoMedia] = useState(true);
  const [agentBrowserNotifications, setAgentBrowserNotifications] = useState(true);
  const [agentNotificationSound, setAgentNotificationSound] = useState(true);
  const [skillBatchIndex, setSkillBatchIndex] = useState(0);
  const [skillPickerTab, setSkillPickerTab] = useState<CanvasSkillTab>("common");
  const [skillPickerQuery, setSkillPickerQuery] = useState("");
  const [skillDetailId, setSkillDetailId] = useState<string | null>(null);
  const [canvasFavoriteSkills, setCanvasFavoriteSkills] = useState<Set<string>>(loadCanvasFavoriteSkills);
  const [canvasCustomSkills, setCanvasCustomSkills] = useState<CanvasLibrarySkill[]>([]);
  const [canvasCreateSkillOpen, setCanvasCreateSkillOpen] = useState(false);
  const [allCanvasSkillsOpen, setAllCanvasSkillsOpen] = useState(false);
  const [canvasSkillCatalogTab, setCanvasSkillCatalogTab] = useState<CanvasSkillCatalogTab>("skills");
  const [canvasSkillCatalogCategory, setCanvasSkillCatalogCategory] = useState("全部");
  const [canvasSkillCatalogQuery, setCanvasSkillCatalogQuery] = useState("");
  const [runHistory, setRunHistory] = useState<RunRecord[]>(storedDocument?.runHistory ?? []);
  const [activity, setActivity] = useState<ActivityItem[]>(storedDocument?.activity ?? [
    { id: crypto.randomUUID(), label: "创建作品并初始化工作流", time: timestamp() },
  ]);
  const [includeCanvasContext, setIncludeCanvasContext] = useState(storedDocument?.preferences.includeCanvasContext ?? true);
  const [followLatestRun, setFollowLatestRun] = useState(storedDocument?.preferences.followLatestRun ?? true);
  const [activeSkill, setActiveSkill] = useState<string | null>(storedDocument?.activeSkill ?? work.creationConfig?.skillId ?? null);
  const [creationConfig, setCreationConfig] = useState<WorkCreationConfig>(() => defaultCreationConfig(storedDocument?.work ?? work));
  const [composerMenu, setComposerMenu] = useState<ComposerMenuKind>(null);
  const [composerAttachmentIds, setComposerAttachmentIds] = useState<string[]>(() => (storedDocument?.work.attachments ?? work.attachments).map((attachment) => attachment.id));
  const [membershipOpen, setMembershipOpen] = useState(false);
  const [modelModality, setModelModality] = useState<ModelModality>(creationConfig.model.modality);
  const [overviewTab, setOverviewTab] = useState<"canvas" | "assets">("canvas");
  const [overviewQuery, setOverviewQuery] = useState("");
  const [overviewSearchOpen, setOverviewSearchOpen] = useState(false);
  const [overviewFilter, setOverviewFilter] = useState<OverviewKindFilter>("all");
  const [overviewFilterOpen, setOverviewFilterOpen] = useState(false);
  const [overviewSortAscending, setOverviewSortAscending] = useState(true);
  const [overviewNodeMenu, setOverviewNodeMenu] = useState<{ nodeId: string; x: number; y: number } | null>(null);
  const [renamingOverviewNodeId, setRenamingOverviewNodeId] = useState<string | null>(null);
  const [overviewRenameValue, setOverviewRenameValue] = useState("");
  const [overviewAssetSource, setOverviewAssetSource] = useState<AssetSource>("personal");
  const [overviewAssetQuery, setOverviewAssetQuery] = useState("");
  const [overviewAssetFilterOpen, setOverviewAssetFilterOpen] = useState(false);
  const [overviewAssetTags, setOverviewAssetTags] = useState<AssetTag[]>([]);
  const [overviewAssetGroupMenuOpen, setOverviewAssetGroupMenuOpen] = useState(false);
  const [overviewAssetGroupName, setOverviewAssetGroupName] = useState("待分类资产");
  const [renamingAssetGroup, setRenamingAssetGroup] = useState(false);
  const [leftSidebarWidth, setLeftSidebarWidth] = useState(280);
  const [agentPanelWidth, setAgentPanelWidth] = useState(448);
  const [selectedCharacterId, setSelectedCharacterId] = useState(CHARACTER_PRESETS[0].id);
  const [historyMediaKind, setHistoryMediaKind] = useState<"image" | "video" | "audio">("image");
  const [, setSyncState] = useState<CloudWorkState>(work.cloudState);
  const [attachments, setAttachments] = useState<DraftAttachment[]>(storedDocument?.work.attachments ?? work.attachments);
  const [cloudProjectId, setCloudProjectId] = useState(work.cloudProjectId ?? storedDocument?.work.cloudProjectId);
  const mountedRef = useRef(true);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const historyRef = useRef<GraphHistoryEntry[]>([cloneGraph(graph.nodes, graph.edges)]);
  const historyIndexRef = useRef(0);
  const restoringHistoryRef = useRef(false);
  const clipboardRef = useRef<GraphHistoryEntry | null>(null);
  const pasteCountRef = useRef(0);
  const flowInstanceRef = useRef<ReactFlowInstance<WorkflowNode, Edge> | null>(null);
  const [historyAvailability, setHistoryAvailability] = useState({ canUndo: false, canRedo: false });

  const suggestedSkills = useMemo(() => suggestedSkillsFor(work), [work]);
  const editingNode = editingNodeId ? nodes.find((node) => node.id === editingNodeId) ?? null : null;
  const selectedModel = getModelById(creationConfig.model.modelId);
  const overviewNodes = useMemo(() => {
    const query = overviewQuery.trim().toLocaleLowerCase();
    return nodes
      .filter((node) => overviewFilter === "all" || node.data.kind === overviewFilter || ((overviewFilter === "director" || overviewFilter === "legacy-script") && node.data.kind === "script"))
      .filter((node) => !query || `${node.data.title} ${node.data.description} ${node.data.assetName ?? ""}`.toLocaleLowerCase().includes(query))
      .sort((a, b) => overviewSortAscending
        ? a.data.title.localeCompare(b.data.title, "zh-CN")
        : b.data.title.localeCompare(a.data.title, "zh-CN"));
  }, [nodes, overviewFilter, overviewQuery, overviewSortAscending]);
  const selectedCharacter = CHARACTER_PRESETS.find((character) => character.id === selectedCharacterId) ?? CHARACTER_PRESETS[0];
  const canvasSkillLibrary = useMemo(() => [...AGENT_SKILL_LIBRARY, ...canvasCustomSkills], [canvasCustomSkills]);
  const selectedSkillDetail = canvasSkillLibrary.find((skill) => skill.id === skillDetailId) ?? null;
  const activeLibrarySkill = canvasSkillLibrary.find((skill) => skill.id === activeSkill) ?? null;
  const activeSuggestedSkill = suggestedSkills.find((skill) => skill.id === activeSkill) ?? null;
  const activeSkillTitle = activeLibrarySkill?.title ?? activeSuggestedSkill?.title ?? "";
  const visibleSkillLibrary = useMemo(() => {
    const query = skillPickerQuery.trim().toLocaleLowerCase();
    const source = skillPickerTab === "favorite"
      ? canvasSkillLibrary.filter((skill) => canvasFavoriteSkills.has(skill.id))
      : skillPickerTab === "mine"
        ? canvasCustomSkills
        : canvasSkillLibrary;
    return source.filter((skill) => !query || `${skill.title} ${skill.slug} ${skill.description}`.toLocaleLowerCase().includes(query));
  }, [canvasCustomSkills, canvasFavoriteSkills, canvasSkillLibrary, skillPickerQuery, skillPickerTab]);
  const canvasCatalogSkills = useMemo(() => {
    const query = canvasSkillCatalogQuery.trim().toLocaleLowerCase();
    const source = canvasSkillCatalogTab === "favorite"
      ? canvasSkillLibrary.filter((skill) => canvasFavoriteSkills.has(skill.id))
      : canvasSkillCatalogTab === "mine"
        ? canvasCustomSkills
        : canvasSkillLibrary;
    return source
      .filter((skill) => canvasSkillCatalogTab !== "skills" || canvasSkillCatalogCategory === "全部" || skill.category === canvasSkillCatalogCategory)
      .filter((skill) => !query || `${skill.title} ${skill.slug} ${skill.description}`.toLocaleLowerCase().includes(query));
  }, [canvasCustomSkills, canvasFavoriteSkills, canvasSkillCatalogCategory, canvasSkillCatalogQuery, canvasSkillCatalogTab, canvasSkillLibrary]);
  const visibleOverviewAssets = useMemo(() => {
    const query = overviewAssetQuery.trim().toLocaleLowerCase();
    return attachments.filter((attachment) => !query || `${attachment.name} ${attachment.type}`.toLocaleLowerCase().includes(query));
  }, [attachments, overviewAssetQuery]);
  const historyAssets = useMemo(() => nodes.filter((node) => {
    if (historyMediaKind === "image") return node.data.kind === "image" || node.data.kind === "text" || node.data.kind === "script";
    return node.data.kind === historyMediaKind;
  }), [historyMediaKind, nodes]);
  const canvasHistoryPickerItems = useMemo<CanvasHistoryPickerItem[]>(() => {
    if (canvasHistorySource !== "libtv") return [];
    const attachmentItems = attachments
      .filter((attachment) => attachmentKind(attachment) === canvasHistoryMedia)
      .map((attachment) => ({
        id: `attachment:${attachment.id}`,
        kind: attachmentKind(attachment),
        title: attachment.name,
        description: attachment.type || "本地素材",
        source: "attachment" as const,
        sourceId: attachment.id,
      }));
    const nodeItems = nodes
      .filter((node) => node.data.kind === canvasHistoryMedia)
      .map((node) => ({
        id: `node:${node.id}`,
        kind: node.data.kind,
        title: node.data.title,
        description: node.data.description,
        source: "node" as const,
        sourceId: node.id,
      }));
    return [...attachmentItems, ...nodeItems].slice(0, 30);
  }, [attachments, canvasHistoryMedia, canvasHistorySource, nodes]);
  const activePresetLibrary = overlay === "effect-library" ? EFFECT_PRESETS : STYLE_PRESETS;
  const visibleLibraryPresets = useMemo(() => {
    const query = libraryQuery.trim().toLocaleLowerCase();
    return activePresetLibrary.filter((preset) => {
      if (libraryTab === "favorite" && !libraryFavorites.has(preset.name)) return false;
      if (libraryTab === "recent" && !libraryRecent.includes(preset.name)) return false;
      if (libraryCategory !== "推荐" && preset.category !== libraryCategory) return false;
      if (libraryCommercialOnly && !preset.commercial) return false;
      return !query || `${preset.name} ${preset.author} ${preset.model}`.toLocaleLowerCase().includes(query);
    });
  }, [activePresetLibrary, libraryCategory, libraryCommercialOnly, libraryFavorites, libraryQuery, libraryRecent, libraryTab]);
  const composerAttachments = useMemo(
    () => attachments.filter((attachment) => composerAttachmentIds.includes(attachment.id)),
    [attachments, composerAttachmentIds],
  );
  const composerReady = Boolean(prompt.trim() || composerAttachments.length || activeSkill || selectedModel);
  const addActivity = useCallback((label: string) => {
    setActivity((items) => [{ id: crypto.randomUUID(), label, time: timestamp() }, ...items].slice(0, 30));
  }, []);

  useEffect(() => {
    setNodes(graph.nodes);
    setEdges(graph.edges);
    historyRef.current = [cloneGraph(graph.nodes, graph.edges)];
    historyIndexRef.current = 0;
    setHistoryAvailability({ canUndo: false, canRedo: false });
    setSelectedNodeId(null);
    setWorkName(storedDocument?.work.name ?? work.name);
    setPrompt(storedDocument?.work.prompt ?? work.prompt);
    const nextConfig = defaultCreationConfig(storedDocument?.work ?? work);
    setCreationConfig(nextConfig);
    setModelModality(nextConfig.model.modality);
  }, [graph, setEdges, setNodes, storedDocument, work.name, work.prompt]);

  useEffect(() => setSyncState(work.cloudState), [work.cloudState]);

  useEffect(() => {
    if (work.cloudProjectId) setCloudProjectId(work.cloudProjectId);
    setAttachments((current) => {
      const merged = new Map(current.map((attachment) => [attachment.id, attachment]));
      work.attachments.forEach((attachment) => merged.set(attachment.id, attachment));
      return [...merged.values()];
    });
  }, [work.attachments, work.cloudProjectId]);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  useEffect(() => {
    let disposed = false;
    let timer = 0;
    const refresh = async () => {
      const next = await createAgentGateway();
      if (disposed) return;
      setGateway(next);
      timer = window.setTimeout(() => void refresh(), 12_000);
    };
    void refresh();
    return () => {
      disposed = true;
      window.clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    if (!notice) return undefined;
    const timer = window.setTimeout(() => setNotice(""), 2600);
    return () => window.clearTimeout(timer);
  }, [notice]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const updatedAt = new Date().toISOString();
      const nextWork: WebWork = {
        ...work,
        name: workName.trim() || "unnamed",
        creationConfig,
        attachments,
        ...(cloudProjectId ? { cloudProjectId } : {}),
        cloudState: cloudProjectId ? "syncing" : work.cloudState,
      };
      const document: CanvasDocument = {
        schemaVersion: 1,
        work: nextWork,
        nodes: nodes.map((node) => ({
          id: node.id,
          type: node.type,
          position: node.position,
          data: node.data,
        })),
        edges: edges.map((edge) => ({
          id: edge.id,
          source: edge.source,
          target: edge.target,
          sourceHandle: edge.sourceHandle,
          targetHandle: edge.targetHandle,
          type: edge.type,
          animated: edge.animated,
        })),
        viewport,
        preferences: {
          view,
          gridVisible,
          snapToGrid: snapToGridEnabled,
          edgesVisible,
          miniMapVisible,
          panelOpen,
          includeCanvasContext,
          followLatestRun,
        },
        activeSkill,
        activity,
        runHistory,
        updatedAt,
      };

      saveLocalCanvasDocument(document);
      saveWork(nextWork);
      if (!cloudProjectId) return;
      setSyncState("syncing");
      void saveCloudCanvasDocument(cloudProjectId, document)
        .then(() => {
          if (!mountedRef.current) return;
          setSyncState("synced");
          saveWork({ ...nextWork, cloudState: "synced", cloudError: undefined });
        })
        .catch((error) => {
          if (!mountedRef.current) return;
          const message = error instanceof Error ? error.message : String(error);
          setSyncState("failed");
          saveWork({ ...nextWork, cloudState: "failed", cloudError: message });
        });
    }, 650);
    return () => window.clearTimeout(timer);
  }, [
    activeSkill,
    activity,
    attachments,
    cloudProjectId,
    creationConfig,
    edges,
    edgesVisible,
    followLatestRun,
    gridVisible,
    includeCanvasContext,
    miniMapVisible,
    nodes,
    panelOpen,
    runHistory,
    snapToGridEnabled,
    view,
    viewport,
    work,
    workName,
  ]);

  useEffect(() => {
    if (restoringHistoryRef.current) {
      restoringHistoryRef.current = false;
      return undefined;
    }
    const timer = window.setTimeout(() => {
      const current = historyRef.current[historyIndexRef.current];
      if (current && graphSignature(current.nodes, current.edges) === graphSignature(nodes, edges)) return;
      const nextHistory = historyRef.current.slice(0, historyIndexRef.current + 1);
      nextHistory.push(cloneGraph(nodes, edges));
      historyRef.current = nextHistory.slice(-60);
      historyIndexRef.current = historyRef.current.length - 1;
      setHistoryAvailability({ canUndo: historyIndexRef.current > 0, canRedo: false });
    }, 260);
    return () => window.clearTimeout(timer);
  }, [edges, nodes]);

  const restoreHistory = useCallback((nextIndex: number) => {
    const entry = historyRef.current[nextIndex];
    if (!entry) return;
    restoringHistoryRef.current = true;
    historyIndexRef.current = nextIndex;
    const graphCopy = cloneGraph(entry.nodes, entry.edges);
    setNodes(graphCopy.nodes);
    setEdges(graphCopy.edges);
    setSelectedNodeId(null);
    setHistoryAvailability({
      canUndo: nextIndex > 0,
      canRedo: nextIndex < historyRef.current.length - 1,
    });
  }, [setEdges, setNodes]);

  const undoGraph = useCallback(() => {
    if (historyIndexRef.current <= 0) return;
    restoreHistory(historyIndexRef.current - 1);
    addActivity("撤销画布操作");
  }, [addActivity, restoreHistory]);

  const redoGraph = useCallback(() => {
    if (historyIndexRef.current >= historyRef.current.length - 1) return;
    restoreHistory(historyIndexRef.current + 1);
    addActivity("重做画布操作");
  }, [addActivity, restoreHistory]);

  const copySelectedNodes = useCallback(() => {
    const selected = nodes.filter((node) => node.selected || node.id === selectedNodeId);
    if (!selected.length) return false;
    const selectedIds = new Set(selected.map((node) => node.id));
    clipboardRef.current = cloneGraph(
      selected,
      edges.filter((edge) => selectedIds.has(edge.source) && selectedIds.has(edge.target)),
    );
    pasteCountRef.current = 0;
    setNotice(`已复制 ${selected.length} 个节点`);
    return true;
  }, [edges, nodes, selectedNodeId]);

  const pasteNodes = useCallback(() => {
    const source = clipboardRef.current;
    if (!source?.nodes.length) return;
    pasteCountRef.current += 1;
    const offset = 28 * pasteCountRef.current;
    const idMap = new Map(source.nodes.map((node) => [node.id, `${node.data.kind ?? "node"}-${crypto.randomUUID()}`]));
    const pastedNodes = source.nodes.map((node) => ({
      ...node,
      id: idMap.get(node.id)!,
      selected: true,
      position: { x: node.position.x + offset, y: node.position.y + offset },
      data: { ...node.data },
    }));
    const pastedEdges = source.edges.flatMap((edge) => {
      const nextSource = idMap.get(edge.source);
      const nextTarget = idMap.get(edge.target);
      return nextSource && nextTarget ? [{
        ...edge,
        id: `edge-${crypto.randomUUID()}`,
        source: nextSource,
        target: nextTarget,
      }] : [];
    });
    setNodes((items) => [...items.map((node) => ({ ...node, selected: false })), ...pastedNodes]);
    setEdges((items) => [...items, ...pastedEdges]);
    setSelectedNodeId(pastedNodes[0]?.id ?? null);
    addActivity(`粘贴 ${pastedNodes.length} 个节点`);
  }, [addActivity, setEdges, setNodes]);

  const duplicateSelectedNodes = useCallback(() => {
    if (copySelectedNodes()) pasteNodes();
  }, [copySelectedNodes, pasteNodes]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.matches("input, textarea, [contenteditable='true']")) {
        if (event.key === "Escape") target.blur();
        return;
      }
      const command = event.metaKey || event.ctrlKey;
      const key = event.key.toLowerCase();
      if (command && key === "z") {
        event.preventDefault();
        if (event.shiftKey) redoGraph();
        else undoGraph();
      } else if (command && key === "c") {
        if (copySelectedNodes()) event.preventDefault();
      } else if (command && key === "v") {
        if (clipboardRef.current) {
          event.preventDefault();
          pasteNodes();
        }
      } else if (command && key === "d") {
        event.preventDefault();
        duplicateSelectedNodes();
      } else if (command && key === "a") {
        event.preventDefault();
        setNodes((items) => items.map((node) => ({ ...node, selected: true })));
      } else if (event.key === "Backspace" || event.key === "Delete") {
        event.preventDefault();
        deleteSelectedNode();
      } else if (event.key === "Escape") {
        setDrawer(null);
        setOverlay(null);
        setLibraryInsertPoint(null);
        setLibraryDetail(null);
        setDirectorStudioNodeId(null);
        setCanvasInsertMenu(null);
        setCanvasHistoryPickerOpen(false);
        setCanvasHistorySelection([]);
        setComposerMenu(null);
        setContextMenu(null);
        setOverviewNodeMenu(null);
        setOverviewFilterOpen(false);
      } else if (key === "a") {
        setDrawer("add");
      } else if (key === "v") {
        setTool("select");
      } else if (key === "h") {
        setTool("pan");
      } else if (key === "g") {
        setSnapToGridEnabled((enabled) => !enabled);
      } else if (event.key === "?") {
        setOverlay("shortcuts");
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [copySelectedNodes, duplicateSelectedNodes, pasteNodes, redoGraph, setNodes, undoGraph]);

  function persistName() {
    const name = workName.trim() || "unnamed";
    setWorkName(name);
    if (name !== work.name) {
      saveWork({ ...work, name, creationConfig, attachments, ...(cloudProjectId ? { cloudProjectId } : {}) });
      addActivity(`作品重命名为「${name}」`);
    }
  }

  function openDrawer(kind: DrawerKind) {
    setDrawer((current) => current === kind ? null : kind);
    setOverlay(null);
    setContextMenu(null);
    setOverviewNodeMenu(null);
    setOverviewFilterOpen(false);
    setComposerMenu(null);
  }

  function updateNodeData(nodeId: string, patch: Partial<WorkflowNodeData>) {
    setNodes((items) => items.map((node) => node.id === nodeId
      ? { ...node, data: { ...node.data, ...patch } }
      : node));
  }

  function addLinkedNode(sourceId: string, kind: WorkflowNodeKind, title: string, description: string, prompt = "") {
    const source = nodes.find((node) => node.id === sourceId);
    if (!source) return;
    const definition = nodeDefinition(kind);
    const id = `${kind}-${crypto.randomUUID()}`;
    const nextNode: WorkflowNode = {
      id,
      type: "workflow-node",
      selected: true,
      position: { x: source.position.x + 430, y: source.position.y + 34 },
      data: {
        ...nodeRuntimeDefaults(kind),
        kind,
        title,
        description,
        prompt,
        status: "idle",
        eyebrow: definition.eyebrow,
        variant: "default",
      },
    };
    setNodes((items) => [...items.map((node) => ({ ...node, selected: false })), nextNode]);
    setEdges((items) => addEdge(makeEdge(`edge-${crypto.randomUUID()}`, sourceId, id, true), items));
    setSelectedNodeId(id);
    addActivity(`从「${source.data.title}」创建${title}`);
  }

  function handleNodeQuickAction(nodeId: string, action: string) {
    const node = nodes.find((item) => item.id === nodeId);
    if (!node) return;
    const currentPrompt = typeof node.data.prompt === "string" ? node.data.prompt : "";
    if (action === "添加视频片段") {
      const id = `video-${crypto.randomUUID()}`;
      const videoNode: WorkflowNode = {
        id,
        type: "workflow-node",
        selected: true,
        position: { x: node.position.x - 430, y: node.position.y + 20 },
        data: { ...nodeRuntimeDefaults("video"), kind: "video", title: "视频片段", description: "生成或导入待合成的视频片段", status: "idle", eyebrow: "VIDEO", variant: "default" },
      };
      setNodes((items) => [...items.map((item) => item.id === nodeId
        ? { ...item, selected: false, data: { ...item.data, connectedMediaCount: Number(item.data.connectedMediaCount ?? 0) + 1 } }
        : { ...item, selected: false }), videoNode]);
      setEdges((items) => addEdge(makeEdge(`edge-${crypto.randomUUID()}`, id, nodeId, true), items));
      setSelectedNodeId(id);
      addActivity("为视频合成添加片段");
      return;
    }
    if (action === "文生视频" || action === "音频生视频") {
      addLinkedNode(nodeId, "video", "视频节点", action === "音频生视频" ? "根据音频节奏与语义生成视频" : "根据文字描述生成视频", currentPrompt);
      return;
    }
    if (action === "图片反推提示词") {
      addLinkedNode(nodeId, "image", "图片参考", "上传图片并反推画面提示词", "分析画面主体、构图、光线、色彩与风格");
      return;
    }
    if (action === "文字生音乐") {
      addLinkedNode(nodeId, "audio", "音乐节点", "根据文字描述生成音乐", currentPrompt);
      return;
    }
    if (action === "添加参考素材" || action === "参考" || action === "角色库") {
      if (action === "添加参考素材") {
        setPendingUploadPoint({ x: node.position.x + 28, y: node.position.y + 28 });
        fileInputRef.current?.click();
      } else {
        setDrawer(action === "角色库" ? "characters" : "assets");
      }
      return;
    }
    if (action === "风格" || action === "特效") {
      setLibraryInsertPoint({ x: node.position.x + 430, y: node.position.y });
      setLibraryTab("square");
      setLibraryCategory("推荐");
      setLibraryQuery("");
      setLibraryMinimized(false);
      setOverlay(action === "风格" ? "style-library" : "effect-library");
      return;
    }
    if (action === "<#> 停顿" || action === "() 语气词") {
      updateNodeData(nodeId, { prompt: `${currentPrompt}${currentPrompt ? " " : ""}${action === "<#> 停顿" ? "<#0.5#>" : "(轻笑)"}` });
      return;
    }
    const promptByAction: Record<string, string> = {
      "自己编写内容": currentPrompt,
      "图生图": "参考已上传图片，保持主体一致并按以下要求重新创作：",
      "图片高清": "增强图片细节与清晰度，保持构图和主体不变",
      "标记": `${currentPrompt}${currentPrompt ? "\n" : ""}@素材 `,
      "首尾帧生成视频": "连接首帧与尾帧，生成自然连续的镜头运动",
      "首帧生成视频": "基于首帧延展动作、镜头和环境变化",
      "运镜": `${currentPrompt}${currentPrompt ? "，" : ""}电影级推拉摇移运镜，运动自然稳定`,
      "剧本生成分镜脚本": "请将以下剧情拆解为可执行的分镜脚本，包含景别、机位、动作、对白和时长：",
      "视频参考生成分镜脚本": "分析参考视频的镜头结构，并生成可编辑的分镜脚本：",
      "角色生成分镜脚本": "围绕已引用角色生成连续一致的分镜脚本：",
      "自己编写分镜脚本": currentPrompt,
    };
    updateNodeData(nodeId, {
      prompt: promptByAction[action] ?? currentPrompt,
      ...(action.includes("生成视频") ? { videoMode: action } : {}),
      ...(action === "图生图" ? { imageMode: action } : {}),
    });
  }

  function runWorkflowNode(nodeId: string) {
    const node = nodes.find((item) => item.id === nodeId);
    if (!node || node.data.status === "running") return;
    updateNodeData(nodeId, { status: "running" });
    addActivity(`开始执行「${node.data.title}」`);
    setNotice(`${node.data.title} 正在生成…`);
    window.setTimeout(() => {
      const extension = node.data.kind === "image" ? "png" : node.data.kind === "audio" ? "wav" : node.data.kind === "video" || node.data.kind === "compose" ? "mp4" : "md";
      updateNodeData(nodeId, { status: "done", assetName: `生成历史/${node.data.title}.${extension}` });
      addActivity(`完成「${node.data.title}」`);
      setNotice(`${node.data.title} 已完成`);
    }, 900);
  }

  function locateOverviewNode(node: WorkflowNode) {
    setView("workflow");
    setNodes((items) => items.map((item) => ({ ...item, selected: item.id === node.id })));
    setSelectedNodeId(node.id);
    setOverviewNodeMenu(null);
    void flowInstanceRef.current?.setCenter(node.position.x + 124, node.position.y + 74, {
      zoom: Math.max(zoom, .9),
      duration: 260,
    });
  }

  function beginOverviewRename(node: WorkflowNode) {
    setOverviewNodeMenu(null);
    setRenamingOverviewNodeId(node.id);
    setOverviewRenameValue(node.data.title);
  }

  function commitOverviewRename(nodeId: string) {
    const name = overviewRenameValue.trim();
    if (name) {
      updateNodeData(nodeId, { title: name });
      addActivity(`节点重命名为「${name}」`);
    }
    setRenamingOverviewNodeId(null);
    setOverviewRenameValue("");
  }

  function duplicateOverviewNode(nodeId: string) {
    const source = nodes.find((node) => node.id === nodeId);
    if (!source) return;
    const copyId = `${source.data.kind}-${crypto.randomUUID()}`;
    const copy: WorkflowNode = {
      ...source,
      id: copyId,
      selected: true,
      position: { x: source.position.x + 34, y: source.position.y + 34 },
      data: { ...source.data, title: `${source.data.title} 副本` },
    };
    setNodes((items) => [...items.map((node) => ({ ...node, selected: false })), copy]);
    setSelectedNodeId(copyId);
    setOverviewNodeMenu(null);
    addActivity(`复制节点「${source.data.title}」`);
  }

  function askAgentForNode(nodeId: string) {
    const node = nodes.find((item) => item.id === nodeId);
    if (!node) return;
    setPrompt(`请处理画布节点「${node.data.title}」。\n\n目标：${node.data.description}${node.data.assetName ? `\n关联资产：${node.data.assetName}` : ""}`);
    setPanelOpen(true);
    setPanelTab("skills");
    setComposerMenu(null);
    setContextMenu(null);
    addActivity(`为节点「${node.data.title}」准备 Agent 指令`);
  }

  function addWorkflowNode(kind: WorkflowNodeKind, options?: {
    title?: string;
    description?: string;
    assetName?: string;
    position?: { x: number; y: number };
    connectToAnchor?: boolean;
    variant?: WorkflowNodeVariant;
    prompt?: string;
  }) {
    if (work.line === "comic" && kind === "video") {
      setNotice("漫画工作流不包含视频节点");
      return;
    }
    const definition = nodeDefinition(kind);
    const anchor = nodes.find((node) => node.id === selectedNodeId) ?? nodes[nodes.length - 1];
    const id = `${kind}-${crypto.randomUUID()}`;
    const nextNode: WorkflowNode = {
      id,
      type: "workflow-node",
      position: options?.position ?? (anchor ? { x: anchor.position.x + 310, y: anchor.position.y + 42 } : { x: 120, y: 140 }),
      data: {
        ...nodeRuntimeDefaults(kind, options?.variant),
        kind,
        title: options?.title ?? definition.label,
        description: options?.description ?? definition.description,
        status: "idle",
        eyebrow: definition.eyebrow,
        variant: options?.variant ?? "default",
        ...(options?.prompt !== undefined ? { prompt: options.prompt } : {}),
        ...(options?.assetName ? { assetName: options.assetName } : {}),
      },
    };
    setNodes((items) => [...items.map((node) => ({ ...node, selected: false })), { ...nextNode, selected: true }]);
    if (anchor && options?.connectToAnchor !== false) setEdges((items) => addEdge(makeEdge(`edge-${crypto.randomUUID()}`, anchor.id, id), items));
    setSelectedNodeId(id);
    setDrawer(null);
    addActivity(`添加${options?.title ?? definition.label}节点`);
  }

  function addAttachmentNode(attachment: DraftAttachment) {
    const kind = attachmentKind(attachment);
    if (kind === "video" && work.line === "comic") {
      setNotice("漫画画布暂不支持视频节点");
      return;
    }
    addWorkflowNode(kind, { title: attachment.name, assetName: `${Math.max(1, Math.round(attachment.size / 1024))} KB` });
  }

  function addNodeFromCanvasInsert(kind: WorkflowNodeKind, title: string, description: string, variant: WorkflowNodeVariant = "default") {
    if (!canvasInsertMenu) return;
    addWorkflowNode(kind, {
      title,
      description,
      variant,
      position: { x: canvasInsertMenu.flowX, y: canvasInsertMenu.flowY },
      connectToAnchor: false,
    });
    setCanvasInsertMenu(null);
  }

  function openCanvasHistoryPicker() {
    if (!canvasInsertMenu) return;
    setHistoryInsertPoint({ x: canvasInsertMenu.flowX, y: canvasInsertMenu.flowY });
    setCanvasHistorySource("libtv");
    setCanvasHistoryMedia("image");
    setCanvasHistorySelection([]);
    setCanvasHistoryPickerOpen(true);
    setCanvasInsertMenu(null);
  }

  function toggleCanvasHistoryItem(itemId: string) {
    setCanvasHistorySelection((current) => {
      if (current.includes(itemId)) return current.filter((id) => id !== itemId);
      if (current.length >= 10) {
        setNotice("一次最多选择 10 项");
        return current;
      }
      return [...current, itemId];
    });
  }

  function confirmCanvasHistorySelection() {
    if (!canvasHistorySelection.length) return;
    const base = historyInsertPoint ?? { x: 120, y: 140 };
    const selected = canvasHistoryPickerItems.filter((item) => canvasHistorySelection.includes(item.id));
    selected.forEach((item, index) => {
      addWorkflowNode(item.kind, {
        title: item.title,
        description: item.description,
        assetName: item.source === "attachment" ? "生成历史素材" : "生成历史节点",
        position: { x: base.x + index * 34, y: base.y + index * 34 },
        connectToAnchor: false,
      });
    });
    setCanvasHistoryPickerOpen(false);
    setCanvasHistorySelection([]);
    setHistoryInsertPoint(null);
    setNotice(`已从生成历史添加 ${selected.length} 项`);
  }

  async function importAssetFiles(files: File[], openAssetsDrawer: boolean): Promise<string[]> {
    if (!files.length) return [];
    const pending: PendingAttachment[] = files.map((file) => ({
      id: crypto.randomUUID(),
      name: file.name,
      size: file.size,
      type: file.type || "application/octet-stream",
      file,
    }));
    const pendingIds = pending.map((attachment) => attachment.id);
    registerLocalFiles(pending);
    const nextAttachments: DraftAttachment[] = [
      ...attachments,
      ...pending.map(({ id, name, size, type }) => ({ id, name, size, type })),
    ];
    setAttachments(nextAttachments);
    const nextWork: WebWork = {
      ...work,
      name: workName.trim() || "unnamed",
      creationConfig,
      attachments: nextAttachments,
      ...(cloudProjectId ? { cloudProjectId } : {}),
      cloudState: isCloudConfigured() ? "syncing" : "local",
    };
    saveWork(nextWork);
    addActivity(`导入 ${pending.length} 个素材`);
    if (openAssetsDrawer) setDrawer("assets");

    if (!isCloudConfigured()) {
      setNotice(`已导入 ${pending.length} 个本地素材`);
      return pendingIds;
    }
    setSyncState("syncing");
    try {
      const result = await persistWorkToCloud(nextWork, pending);
      if (!mountedRef.current) return pendingIds;
      setAttachments(result.work.attachments);
      if (result.work.cloudProjectId) setCloudProjectId(result.work.cloudProjectId);
      setSyncState(result.work.cloudState);
      saveWork(result.work);
      setNotice(`已上传 ${pending.length} 个素材`);
    } catch (error) {
      if (!mountedRef.current) return pendingIds;
      const message = error instanceof Error ? error.message : String(error);
      setSyncState("failed");
      saveWork({ ...nextWork, cloudState: "failed", cloudError: message });
      setNotice(`素材保留在本地，云上传失败：${message}`);
    }
    return pendingIds;
  }

  async function importAssets(fileList: FileList | null) {
    return importAssetFiles(fileList ? Array.from(fileList) : [], true);
  }

  async function uploadComposerAssets(files: File[]) {
    const ids = await importAssetFiles(files, false);
    if (ids.length) setComposerAttachmentIds((current) => [...new Set([...current, ...ids])]);
    return ids;
  }

  function organizeNodes() {
    const columns: Record<WorkflowNodeKind, number> = { text: 0, script: 1, image: 2, audio: 2, video: 3, compose: 4 };
    const rows = new Map<number, number>();
    setNodes((items) => items.map((node) => {
      const column = columns[node.data.kind];
      const row = rows.get(column) ?? 0;
      rows.set(column, row + 1);
      return { ...node, position: { x: 60 + column * 330, y: 100 + row * 250 } };
    }));
    addActivity("自动整理画布节点");
  }

  function deleteSelectedNode() {
    const selectedIds = new Set(nodes
      .filter((node) => node.selected || node.id === selectedNodeId)
      .map((node) => node.id));
    if (!selectedIds.size) {
      setNotice("请先选择一个节点");
      return;
    }
    setNodes((items) => items.filter((node) => !selectedIds.has(node.id)));
    setEdges((items) => items.filter((edge) => !selectedIds.has(edge.source) && !selectedIds.has(edge.target)));
    setSelectedNodeId(null);
    addActivity(`删除 ${selectedIds.size} 个节点`);
  }

  function deleteOverviewNode(nodeId: string) {
    const node = nodes.find((item) => item.id === nodeId);
    if (!node) return;
    setNodes((items) => items.filter((item) => item.id !== nodeId));
    setEdges((items) => items.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
    if (selectedNodeId === nodeId) setSelectedNodeId(null);
    setOverviewNodeMenu(null);
    addActivity(`删除节点「${node.data.title}」`);
    setNotice(`已删除「${node.data.title}」`);
  }

  function resetWorkflow() {
    setNodes(graph.nodes);
    setEdges(graph.edges);
    setSelectedNodeId(null);
    addActivity("恢复初始工作流");
  }

  function useSuggestedSkill(skill: SuggestedSkill) {
    setActiveSkill(skill.id);
    setPrompt(skill.prompt);
    setPanelOpen(true);
    setPanelTab("skills");
    addActivity(`选择建议 Skill：${skill.title}`);
  }

  function useLibrarySkill(skill: CanvasLibrarySkill) {
    setActiveSkill(skill.id);
    setPanelOpen(true);
    setPanelTab("conversation");
    setComposerMenu(null);
    setSkillDetailId(null);
    setAllCanvasSkillsOpen(false);
    setNotice(`已添加「${skill.title}」`);
    addActivity(`选择 Skill：${skill.title}`);
  }

  function toggleCanvasSkillFavorite(skillId: string) {
    setCanvasFavoriteSkills((current) => {
      const next = new Set(current);
      if (next.has(skillId)) next.delete(skillId);
      else next.add(skillId);
      localStorage.setItem("anime-armory.web.favorite-skills", JSON.stringify([...next]));
      return next;
    });
  }

  async function createCanvasSkill(values: CreateSkillFormValues) {
    const skill: CanvasLibrarySkill = {
      id: `user:${crypto.randomUUID()}`,
      title: values.title,
      slug: `/${values.title.trim().toLocaleLowerCase().replace(/\s+/g, "-")}`,
      description: values.description,
      creator: "我的 Skill",
      category: values.category,
      guide: values.guide,
      steps: values.steps,
      useCases: values.useCases,
    };
    setCanvasCustomSkills((items) => [skill, ...items]);
    setActiveSkill(skill.id);
    setSkillPickerTab("mine");
    setNotice(`已创建「${skill.title}」`);
  }

  function deleteCanvasSkill(skill: CanvasLibrarySkill) {
    if (!skill.id.startsWith("user:")) return;
    setCanvasCustomSkills((items) => items.filter((item) => item.id !== skill.id));
    if (activeSkill === skill.id) setActiveSkill(null);
    setSkillDetailId(null);
    setNotice(`已删除「${skill.title}」`);
  }

  function updateRun(job: AgentJob, submittedPrompt: string) {
    setRunHistory((items) => {
      const existing = items.find((item) => item.id === job.id);
      const next: RunRecord = {
        id: job.id,
        prompt: submittedPrompt,
        state: job.state,
        message: job.message,
        output: job.output,
        time: existing?.time ?? timestamp(),
      };
      return existing ? items.map((item) => item.id === job.id ? next : item) : [next, ...items].slice(0, 20);
    });
  }

  async function submit() {
    const cleanPrompt = prompt.trim()
      || (activeLibrarySkill ? `请使用 ${activeLibrarySkill.slug} Skill 处理当前作品。\n\n${activeLibrarySkill.description}` : "")
      || (activeSuggestedSkill ? activeSuggestedSkill.prompt : "")
      || (composerAttachments.length ? "请根据已选素材和当前画布继续创作。" : "")
      || (selectedModel ? `请使用 ${selectedModel.name} 开始创作。` : "");
    if (!gateway || !cleanPrompt || submitting) return;
    const stageNode = nodes.find((node) => node.id !== "text-source" && (node.data.status === "ready" || node.data.status === "idle"));
    setSubmitting(true);
    setPanelOpen(true);
    if (followLatestRun) setPanelTab("history");
    if (stageNode) setNodes((items) => items.map((node) => node.id === stageNode.id ? { ...node, data: { ...node.data, status: "running" } } : node));
    const effectiveWork = {
      ...work,
      name: workName.trim() || "unnamed",
      creationConfig,
      attachments,
      ...(cloudProjectId ? { cloudProjectId } : {}),
    };
    saveWork(effectiveWork);
    try {
      const contextParts = [cleanPrompt];
      if (includeCanvasContext) contextParts.push(`[画布上下文] 当前共有 ${nodes.length} 个节点、${edges.length} 条连线。`);
      if (composerAttachments.length) contextParts.push(`[本次引用素材] ${composerAttachments.map((attachment) => attachment.name).join("、")}`);
      const submittedWork = composerAttachments.length ? { ...effectiveWork, attachments: composerAttachments } : effectiveWork;
      let current = await gateway.submit({ work: submittedWork, prompt: contextParts.join("\n\n") });
      if (!mountedRef.current) return;
      setActiveJob(current);
      updateRun(current, cleanPrompt);
      addActivity("向 Agent 提交创作任务");

      if (gateway.status && (current.state === "queued" || current.state === "running")) {
        for (let attempt = 0; attempt < 300 && (current.state === "queued" || current.state === "running"); attempt += 1) {
          await new Promise((resolve) => window.setTimeout(resolve, 1200));
          if (!mountedRef.current) return;
          current = await gateway.status(current.id);
          setActiveJob(current);
          updateRun(current, cleanPrompt);
        }
      }

      if (!mountedRef.current) return;
      const finalStatus: WorkflowNodeStatus = current.state === "succeeded" ? "done" : current.state === "failed" ? "failed" : "ready";
      if (stageNode) setNodes((items) => {
        const stageIndex = items.findIndex((node) => node.id === stageNode.id);
        return items.map((node, index) => {
          if (node.id === stageNode.id) return { ...node, data: { ...node.data, status: finalStatus } };
          if (current.state === "succeeded" && index === stageIndex + 1 && node.data.status === "idle") return { ...node, data: { ...node.data, status: "ready" } };
          return node;
        });
      });
      if (current.state === "succeeded") addActivity("Agent 完成创作任务");
    } catch (error) {
      if (!mountedRef.current) return;
      const failed: AgentJob = { id: crypto.randomUUID(), state: "failed", message: error instanceof Error ? error.message : String(error) };
      setActiveJob(failed);
      updateRun(failed, cleanPrompt);
      if (stageNode) setNodes((items) => items.map((node) => node.id === stageNode.id ? { ...node, data: { ...node.data, status: "failed" } } : node));
    } finally {
      if (mountedRef.current) setSubmitting(false);
    }
  }

  const onConnect = useCallback((connection: Connection) => {
    setEdges((items) => addEdge({ ...connection, type: "smoothstep", markerEnd: { type: MarkerType.ArrowClosed }, className: "workflow-edge" }, items));
    addActivity("连接两个工作流节点");
  }, [addActivity, setEdges]);

  async function copyShareLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setNotice("画布链接已复制");
      setOverlay(null);
    } catch {
      setNotice("浏览器未允许复制，请从地址栏复制链接");
    }
  }

  function exportCanvasDocument() {
    const document = loadLocalCanvasDocument(work.id);
    if (!document) {
      setNotice("画布正在保存，请稍后再试");
      return;
    }
    const blob = new Blob([JSON.stringify(document, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = window.document.createElement("a");
    link.href = url;
    link.download = `${(workName.trim() || "canvas").replace(/[\\/:*?\"<>|]/g, "_")}.canvas.json`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
    setNotice("画布 JSON 已导出");
    setOverlay(null);
  }

  function beginSidebarResize(side: "left" | "right", startX: number) {
    const startWidth = side === "left" ? leftSidebarWidth : agentPanelWidth;
    const onMove = (event: PointerEvent) => {
      const delta = event.clientX - startX;
      if (side === "left") setLeftSidebarWidth(Math.min(420, Math.max(240, startWidth + delta)));
      else setAgentPanelWidth(Math.min(620, Math.max(360, startWidth - delta)));
    };
    const onEnd = () => {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onEnd);
    };
    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerup", onEnd, { once: true });
  }

  return (
    <main style={{ "--canvas-panel-width": `${agentPanelWidth}px`, "--canvas-asset-drawer-width": `${leftSidebarWidth}px` } as CSSProperties} className={`creation-canvas-shell tool-${tool}${panelOpen ? " has-agent-panel" : ""}${view === "workflow" && miniMapVisible ? " has-minimap" : ""}${drawer === "overview" ? " has-asset-drawer has-overview-drawer" : ""}`} onClick={(event) => { if (headerMenu) setHeaderMenu(null); const target = event.target as HTMLElement; if (canvasInsertMenu && !target.closest(".canvas-insert-menu")) setCanvasInsertMenu(null); if (composerMenu && !target.closest(".canvas-home-composer")) setComposerMenu(null); if (overviewNodeMenu && !target.closest(".canvas-overview-node-menu") && !target.closest(".canvas-overview-node-more")) setOverviewNodeMenu(null); }}>
      <input
        ref={fileInputRef}
        className="canvas-file-input"
        type="file"
        multiple
        aria-label="上传画布素材"
        onChange={(event) => {
          const files = event.currentTarget.files ? Array.from(event.currentTarget.files) : [];
          const insertPoint = pendingUploadPoint;
          if (insertPoint && files.length) {
            void importAssetFiles(files, false);
            files.forEach((file, index) => {
              const attachment = { id: crypto.randomUUID(), name: file.name, size: file.size, type: file.type || "application/octet-stream" };
              addWorkflowNode(attachmentKind(attachment), {
                title: file.name,
                description: "从本地上传到画布",
                assetName: `${Math.max(1, Math.round(file.size / 1024))} KB`,
                position: { x: insertPoint.x + index * 34, y: insertPoint.y + index * 34 },
                connectToAnchor: false,
              });
            });
            setNotice(`已上传并添加 ${files.length} 个节点`);
          } else {
            void importAssets(event.currentTarget.files);
          }
          setPendingUploadPoint(null);
          event.currentTarget.value = "";
        }}
      />
      <header className="creation-canvas-header">
        <div className="creation-canvas-project-cluster">
          <button type="button" className="creation-canvas-brand" onClick={onHome} aria-label="返回首页"><BrandIcon /><span>⌄</span></button>
          <label className="creation-canvas-project-name"><LineIcon line={work.line} /><input
            className="creation-canvas-name"
            value={workName}
            aria-label="作品名称"
            onChange={(event) => setWorkName(event.target.value)}
            onBlur={persistName}
            onKeyDown={(event) => { if (event.key === "Enter") event.currentTarget.blur(); }}
          /></label>
          <button type="button" className="canvas-board-label" aria-expanded={headerMenu === "board"} onClick={(event) => { event.stopPropagation(); setHeaderMenu((current) => current === "board" ? null : "board"); }} title="画布菜单">画布 1 <ChevronDown size={13} /></button>
        </div>
        <div className="canvas-view-switch" role="tablist" aria-label="画布视图">
          <button type="button" role="tab" aria-label="工作流" aria-selected={view === "workflow"} className={view === "workflow" ? "is-active" : ""} onClick={() => setView("workflow")}><Icon name="workflow" /></button>
          <button type="button" role="tab" aria-label="故事板" aria-selected={view === "storyboard"} className={view === "storyboard" ? "is-active" : ""} onClick={() => setView("storyboard")}><Icon name="panel" /></button>
        </div>
        <nav className="creation-canvas-header-actions" aria-label="项目操作">
          <button type="button" onClick={() => setOverlay("share")}><Share2 size={16} /><span>发布与分享</span></button>
          <button type="button" aria-label="积分" aria-expanded={headerMenu === "credits"} onClick={(event) => { event.stopPropagation(); setHeaderMenu((current) => current === "credits" ? null : "credits"); }}><Coins size={16} /><span>6</span></button>
          <button type="button" className="canvas-profile-button" aria-label="账户" aria-expanded={headerMenu === "profile"} onClick={(event) => { event.stopPropagation(); setHeaderMenu((current) => current === "profile" ? null : "profile"); }}><UserRound size={16} /></button>
          {!panelOpen && <button type="button" onClick={() => setPanelOpen(true)} aria-label="打开 Agent"><Sparkles size={16} /><span>Agent</span></button>}
        </nav>
        {headerMenu === "board" && <div className="canvas-header-menu canvas-board-menu" onClick={(event) => event.stopPropagation()} role="menu" aria-label="画布菜单">
          <button type="button" className="is-selected" role="menuitem" onClick={() => setHeaderMenu(null)}><span><Icon name="workflow" />画布 1</span><Check size={15} /></button>
          <button type="button" role="menuitem" onClick={() => { setHeaderMenu(null); setNotice("已创建新画布，可继续添加节点"); setNodes([]); setEdges([]); }}><span><Icon name="add" />新建画布</span></button>
          <button type="button" role="menuitem" onClick={() => { setHeaderMenu(null); setNotice("已复制当前画布"); }}><span><Icon name="copy" />复制当前画布</span></button>
        </div>}
        {headerMenu === "credits" && <div className="canvas-header-menu canvas-credits-menu" onClick={(event) => event.stopPropagation()} role="dialog" aria-label="积分明细"><strong>积分余额</strong><b>6</b><p>生成任务会显示预计消耗；会员充值功能按需求暂不接入。</p></div>}
        {headerMenu === "profile" && <div className="canvas-header-menu canvas-profile-menu" onClick={(event) => event.stopPropagation()} role="menu" aria-label="账户菜单"><button type="button" role="menuitem" onClick={() => setNotice("个人设置已打开")}>个人设置</button><button type="button" role="menuitem" onClick={() => setNotice("反馈入口已打开")}>帮助与反馈</button></div>}
      </header>

      <aside className="creation-canvas-rail" aria-label="画布工具">
        <button type="button" className={drawer === "add" ? "is-active" : ""} aria-label="添加节点" title="添加节点（A）" onClick={() => openDrawer("add")}><Icon name="add" /><span>添加节点</span></button>
        <button type="button" className={tool === "pan" ? "is-active" : ""} aria-label="移动" title="移动画布（H）" onClick={() => { setTool((current) => current === "pan" ? "select" : "pan"); setDrawer(null); }}><Icon name="move" /><span>移动</span></button>
        <button type="button" className={drawer === "tools" ? "is-active" : ""} aria-label="打开工具箱" title="打开工具箱" onClick={() => openDrawer("tools")}><Icon name="tools" /><span>打开工具箱</span></button>
        <button type="button" className={drawer === "assets" ? "is-active" : ""} aria-label="素材库" title="素材库" onClick={() => openDrawer("assets")}><Icon name="assets" /><span>素材库</span></button>
        <button type="button" className={drawer === "characters" ? "is-active" : ""} aria-label="角色库" title="角色库" onClick={() => openDrawer("characters")}><Icon name="character" /><span>角色库</span></button>
        <button type="button" className={drawer === "history" ? "is-active" : ""} aria-label="历史记录" title="历史记录" onClick={() => openDrawer("history")}><Icon name="history" /><span>历史记录</span></button>
        <span className="creation-canvas-rail-spacer" />
        <button type="button" aria-label="快捷键" title="快捷键（?）" onClick={() => setOverlay("shortcuts")}><span className="shortcut-glyph">⌘</span><span>快捷键</span></button>
        <button type="button" aria-label="教程" title="画布教程" onClick={() => setOverlay("tutorial")}><Icon name="tutorial" /><span>教程</span></button>
      </aside>

      <section
        className="creation-canvas-stage"
        onDoubleClickCapture={(event) => {
          const target = event.target as HTMLElement;
          if (!target.classList.contains("react-flow__pane")) return;
          event.preventDefault();
          event.stopPropagation();
          const position = flowInstanceRef.current?.screenToFlowPosition({ x: event.clientX, y: event.clientY }) ?? { x: event.clientX, y: event.clientY };
          setCanvasInsertMenu({
            clientX: Math.max(8, Math.min(event.clientX, window.innerWidth - 208)),
            clientY: Math.max(8, Math.min(event.clientY, window.innerHeight - 458)),
            flowX: position.x,
            flowY: position.y,
            submenu: null,
            submenuSide: event.clientX > window.innerWidth - 404 ? "left" : "right",
          });
          setContextMenu(null);
          setComposerMenu(null);
        }}
      >
        {view === "workflow" ? (
          <CanvasNodeActionsContext.Provider value={{ update: updateNodeData, run: runWorkflowNode, quickAction: handleNodeQuickAction, openDirector: setDirectorStudioNodeId }}>
          <ReactFlow<WorkflowNode, Edge>
            nodes={nodes}
            edges={edgesVisible ? edges : []}
            onInit={(instance) => { flowInstanceRef.current = instance; }}
            nodeTypes={NODE_TYPES}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={(_, node) => { setSelectedNodeId(node.id); setContextMenu(null); }}
            onNodeDoubleClick={(_, node) => { setEditingNodeId(node.id); setContextMenu(null); }}
            onNodeContextMenu={(event, node) => {
              event.preventDefault();
              setNodes((items) => items.map((item) => ({ ...item, selected: item.id === node.id })));
              setSelectedNodeId(node.id);
              setContextMenu({
                x: Math.min(event.clientX, window.innerWidth - 190),
                y: Math.min(event.clientY, window.innerHeight - 190),
                nodeId: node.id,
              });
            }}
            onSelectionChange={({ nodes: selectedNodes }) => setSelectedNodeId(selectedNodes.at(-1)?.id ?? null)}
            onPaneClick={() => { setSelectedNodeId(null); setContextMenu(null); setOverviewNodeMenu(null); setCanvasInsertMenu(null); }}
            onMove={(_, nextViewport) => setZoom(nextViewport.zoom)}
            onMoveEnd={(_, nextViewport) => setViewport(nextViewport)}
            snapToGrid={snapToGridEnabled}
            snapGrid={[20, 20]}
            nodesDraggable={tool === "select"}
            nodesConnectable={tool === "select" && edgesVisible}
            elementsSelectable={tool === "select"}
            panOnDrag={tool === "pan" ? true : [1, 2]}
            selectionOnDrag={tool === "select"}
            fitView={!storedDocument}
            defaultViewport={storedDocument?.viewport}
            fitViewOptions={{ padding: 0.18 }}
            minZoom={0.1}
            maxZoom={8}
            defaultEdgeOptions={{ type: "smoothstep", markerEnd: { type: MarkerType.ArrowClosed } }}
          >
            {gridVisible && <Background variant={BackgroundVariant.Dots} gap={20} size={1.1} color="rgba(133,137,151,.28)" />}
            {miniMapVisible && <MiniMap position="bottom-left" className="creation-canvas-minimap" pannable zoomable nodeColor={(node) => {
              const typedNode = node as WorkflowNode;
              if (typedNode.data.kind === "image") return "#777984";
              if (typedNode.data.kind === "audio") return "#92949d";
              if (typedNode.data.kind === "video") return "#686a74";
              if (typedNode.data.kind === "compose") return "#92949d";
              return "#585b67";
            }} />}
            <BottomCanvasControls
              zoom={zoom}
              miniMapVisible={miniMapVisible}
              edgesVisible={edgesVisible}
              snapToGridEnabled={snapToGridEnabled}
              overviewOpen={drawer === "overview"}
              onOpenOverview={() => openDrawer("overview")}
              onOrganize={organizeNodes}
              onToggleMiniMap={() => setMiniMapVisible((visible) => !visible)}
              onToggleEdges={() => setEdgesVisible((visible) => !visible)}
              onToggleSnap={() => setSnapToGridEnabled((enabled) => !enabled)}
            />
          </ReactFlow>
          </CanvasNodeActionsContext.Provider>
        ) : (
          <StoryboardView nodes={nodes} onOpenNode={(nodeId) => setEditingNodeId(nodeId)} />
        )}
      </section>

      {canvasInsertMenu && (
        <section
          className={`canvas-insert-menu submenu-${canvasInsertMenu.submenuSide}`}
          style={{ left: canvasInsertMenu.clientX, top: canvasInsertMenu.clientY }}
          role="dialog"
          aria-label="添加节点菜单"
          onClick={(event) => event.stopPropagation()}
          onDoubleClick={(event) => event.stopPropagation()}
        >
          <h4>添加节点</h4>
          <button type="button" onClick={() => addNodeFromCanvasInsert("text", "文本节点", "输入文字、提示词或创作需求")}><Icon name="text" /><span>文本</span></button>
          <button type="button" onClick={() => addNodeFromCanvasInsert("image", "图片节点", "生成或编辑图片素材")}><Icon name="image" /><span>图片</span></button>
          <button type="button" onClick={() => addNodeFromCanvasInsert("video", "视频节点", "生成或编辑动态视频镜头")}><Icon name="video" /><span>视频</span></button>
          <button type="button" onClick={() => addNodeFromCanvasInsert("compose", "视频合成", "组合视频、音频、字幕并导出成片")}><Icon name="compose" /><span>视频合成</span><i className="canvas-insert-badge is-beta">Beta</i></button>
          <button type="button" onClick={() => addNodeFromCanvasInsert("script", "导演台", "在3D空间中搭建场景并进行多视角截图", "director")}><Icon name="workflow" /><span>导演台</span><i className="canvas-insert-badge is-new">NEW</i></button>
          <button type="button" onClick={() => addNodeFromCanvasInsert("audio", "音频节点", "生成配音、音乐或声音设计")}><Icon name="audio" /><span>音频</span></button>
          <div className="canvas-insert-menu-item">
            <button type="button" className={canvasInsertMenu.submenu === "script" ? "is-active" : ""} aria-expanded={canvasInsertMenu.submenu === "script"} onClick={() => setCanvasInsertMenu((current) => current ? { ...current, submenu: current.submenu === "script" ? null : "script" } : current)}><Icon name="script" /><span>脚本</span><ChevronRight size={14} /></button>
            {canvasInsertMenu.submenu === "script" && <div className="canvas-insert-submenu" role="menu" aria-label="脚本类型">
              <button type="button" role="menuitem" onClick={() => addNodeFromCanvasInsert("script", "脚本生成器", "描述剧情片段、故事，为你生成分镜脚本", "script-new")}><span>脚本</span><i className="canvas-insert-badge is-new">NEW</i></button>
              <button type="button" role="menuitem" onClick={() => addNodeFromCanvasInsert("script", "脚本生成器", "描述剧情或添加角色参考、视频参考等，为你生成分镜脚本", "script-legacy")}><span>脚本（旧版）</span><i className="canvas-insert-badge is-beta">Beta</i></button>
            </div>}
          </div>
          <div className="canvas-insert-menu-item">
            <button type="button" className={canvasInsertMenu.submenu === "assets" ? "is-active" : ""} aria-expanded={canvasInsertMenu.submenu === "assets"} onClick={() => setCanvasInsertMenu((current) => current ? { ...current, submenu: current.submenu === "assets" ? null : "assets" } : current)}><Icon name="assets" /><span>素材库</span><i className="canvas-insert-badge is-new">NEW</i><ChevronRight size={14} /></button>
            {canvasInsertMenu.submenu === "assets" && <div className="canvas-insert-submenu" role="menu" aria-label="素材库类型">
              <button type="button" role="menuitem" onClick={() => { setLibraryInsertPoint({ x: canvasInsertMenu.flowX, y: canvasInsertMenu.flowY }); setCanvasInsertMenu(null); setLibraryTab("square"); setLibraryCategory("推荐"); setLibraryQuery(""); setLibraryMinimized(false); setOverlay("style-library"); }}><span>风格库</span></button>
              <button type="button" role="menuitem" onClick={() => { setLibraryInsertPoint({ x: canvasInsertMenu.flowX, y: canvasInsertMenu.flowY }); setCanvasInsertMenu(null); setLibraryTab("square"); setLibraryCategory("推荐"); setLibraryQuery(""); setLibraryMinimized(false); setOverlay("effect-library"); }}><span>特效库</span></button>
            </div>}
          </div>
          <h4>添加资源</h4>
          <button type="button" onClick={() => { setPendingUploadPoint({ x: canvasInsertMenu.flowX, y: canvasInsertMenu.flowY }); setCanvasInsertMenu(null); fileInputRef.current?.click(); }}><Upload size={17} /><span>上传</span></button>
          <button type="button" onClick={openCanvasHistoryPicker}><Sparkles size={16} /><span>从生成历史选择</span></button>
        </section>
      )}

      {drawer && (
        <aside className={`canvas-drawer canvas-drawer-${drawer}`} aria-label="画布抽屉">
          {drawer === "overview" ? <header className="canvas-overview-shell-header">
            <button type="button" className="canvas-overview-brand" onClick={onHome} aria-label="返回首页"><BrandIcon /><span>⌄</span></button>
            <div><strong>{workName.trim() && workName !== "unnamed" ? workName : "未命名工作区"}</strong><i /><button type="button" aria-expanded={overviewBoardMenu} onClick={() => { setOverviewBoardMenu((open) => !open); setOverviewBoardMoreOpen(false); }}>画布 1 <span>⌄</span></button></div>
          </header> : <header><div><small>CANVAS</small><strong>{drawer === "add" ? "添加节点" : drawer === "tools" ? "工具箱" : drawer === "assets" ? "素材库" : drawer === "characters" ? "角色库" : "操作历史"}</strong></div><button type="button" onClick={() => setDrawer(null)} aria-label="关闭抽屉"><Icon name="close" /></button></header>}
          {drawer === "overview" && overviewBoardMenu && <div className="canvas-overview-board-menu" role="dialog" aria-label="画布 1"><header><strong>画布</strong><button type="button" aria-label="新建画布" onClick={() => { setNodes([]); setEdges([]); setOverviewBoardMenu(false); setNotice("已新建画布"); }}><Icon name="add" /></button></header><article><button type="button" onClick={() => setOverviewBoardMenu(false)}><Icon name="workflow" /><span>画布 1</span></button><button type="button" aria-label="画布更多操作" aria-expanded={overviewBoardMoreOpen} onClick={() => setOverviewBoardMoreOpen((open) => !open)}><MoreHorizontal size={16} /></button></article>{overviewBoardMoreOpen && <div role="menu" aria-label="画布更多操作"><button type="button" role="menuitem" onClick={() => setNotice("已在新窗口打开画布") }><ExternalLink size={14} />在新窗口打开</button><button type="button" role="menuitem" onClick={() => { setOverviewBoardMenu(false); setNotice("双击画布名称即可重命名"); }}>重命名画布</button><button type="button" role="menuitem" onClick={() => { setOverviewBoardMenu(false); setNotice("已复制画布"); }}><Icon name="copy" />复制画布</button><button type="button" role="menuitem" disabled><Trash2 size={14} />删除画布</button></div>}</div>}
          {drawer === "overview" && <div className="canvas-overview">
            <nav role="tablist" aria-label="资产管理视图">
              <button type="button" role="tab" aria-selected={overviewTab === "canvas"} className={overviewTab === "canvas" ? "is-active" : ""} onClick={() => setOverviewTab("canvas")}>画布</button>
              <button type="button" role="tab" aria-selected={overviewTab === "assets"} className={overviewTab === "assets" ? "is-active" : ""} onClick={() => setOverviewTab("assets")}>资产</button>
              <button type="button" className="canvas-overview-collapse" aria-label="收起资产管理" title="收起资产管理" onClick={() => { setDrawer(null); setOverviewNodeMenu(null); setOverviewFilterOpen(false); }}><Icon name="map" /></button>
            </nav>
            {overviewTab === "canvas" ? <section className="canvas-overview-nodes">
              <header className="canvas-overview-list-toolbar">
                <button type="button" className="canvas-overview-sort" title={overviewSortAscending ? "按名称倒序" : "按名称正序"} onClick={() => setOverviewSortAscending((ascending) => !ascending)}>画布元素 <ArrowUpDown size={13} className={overviewSortAscending ? "" : "is-desc"} /></button>
                <div className="canvas-overview-filter"><button type="button" aria-expanded={overviewFilterOpen} onClick={() => setOverviewFilterOpen((open) => !open)}>{OVERVIEW_FILTER_OPTIONS.find((option) => option.value === overviewFilter)?.label ?? "全部"}<span>⌄</span></button>{overviewFilterOpen && <div role="menu">{OVERVIEW_FILTER_OPTIONS.map((option) => <button key={option.value} type="button" role="menuitem" className={overviewFilter === option.value ? "is-active" : ""} onClick={() => { setOverviewFilter(option.value); setOverviewFilterOpen(false); }}>{option.label}</button>)}</div>}</div>
                <button type="button" className={overviewSearchOpen ? "canvas-overview-search-toggle is-active" : "canvas-overview-search-toggle"} aria-label="搜索画布元素" onClick={() => setOverviewSearchOpen((open) => { if (open) setOverviewQuery(""); return !open; })}><Search size={17} /></button>
              </header>
              {overviewSearchOpen && <label className="canvas-overview-search"><Search size={14} /><input autoFocus aria-label="搜索节点" value={overviewQuery} onChange={(event) => setOverviewQuery(event.target.value)} placeholder="搜索画布元素" /><button type="button" aria-label="关闭搜索" onClick={() => { setOverviewQuery(""); setOverviewSearchOpen(false); }}><X size={13} /></button></label>}
              <div className="canvas-overview-node-list">{overviewNodes.map((node) => <article key={node.id} className={selectedNodeId === node.id ? "is-selected" : ""}>
                <button type="button" className="canvas-overview-node-icon" aria-label={`定位${node.data.title}`} onClick={() => locateOverviewNode(node)}><Icon name={node.data.kind} /></button>
                <span>{renamingOverviewNodeId === node.id ? <input autoFocus value={overviewRenameValue} aria-label="节点名称" onChange={(event) => setOverviewRenameValue(event.target.value)} onBlur={() => commitOverviewRename(node.id)} onKeyDown={(event) => { if (event.key === "Enter") event.currentTarget.blur(); if (event.key === "Escape") { setRenamingOverviewNodeId(null); setOverviewRenameValue(""); } }} /> : <b>{node.data.title}</b>}</span>
                <button type="button" className="canvas-overview-node-more" aria-label={`${node.data.title}更多操作`} aria-expanded={overviewNodeMenu?.nodeId === node.id} onClick={(event) => { const rect = event.currentTarget.getBoundingClientRect(); setOverviewNodeMenu((current) => current?.nodeId === node.id ? null : { nodeId: node.id, x: Math.min(rect.left, window.innerWidth - 188), y: rect.bottom + 6 }); }}><MoreHorizontal size={16} /></button>
                <button type="button" className="canvas-overview-node-locate" aria-label={`定位${node.data.title}`} title="定位" onClick={() => locateOverviewNode(node)}><Icon name="send" /></button>
              </article>)}</div>
              {!overviewNodes.length && <div className="canvas-drawer-empty"><Icon name="workflow" /><b>没有匹配的节点</b></div>}
              <footer className="canvas-overview-node-footer"><button type="button" aria-label="收起节点侧栏" title="收起节点侧栏" onClick={() => setDrawer(null)}><Icon name="collapse-panel" /></button><span>共 {overviewNodes.length} 节点</span></footer>
            </section> : <section className="canvas-overview-assets canvas-sidebar-assets">
              <nav role="tablist" aria-label="资产来源"><button type="button" role="tab" aria-selected={overviewAssetSource === "personal"} className={overviewAssetSource === "personal" ? "is-active" : ""} onClick={() => setOverviewAssetSource("personal")}>个人</button><button type="button" role="tab" aria-selected={overviewAssetSource === "agent"} className={overviewAssetSource === "agent" ? "is-active" : ""} onClick={() => setOverviewAssetSource("agent")}>Agent</button></nav>
              {overviewAssetSource === "agent" ? <div className="canvas-sidebar-agent-assets"><Sparkles size={22} /><p>暂无素材</p><small>Agent 生成的素材会出现在这里</small></div> : <>
                <header><label><Search size={14} /><input aria-label="搜索资产" placeholder="请输入搜索内容" value={overviewAssetQuery} onChange={(event) => setOverviewAssetQuery(event.target.value)} /></label><button type="button" aria-label="筛选素材类型" aria-expanded={overviewAssetFilterOpen} onClick={() => setOverviewAssetFilterOpen((open) => !open)}><Filter size={15} /></button></header>
                {overviewAssetFilterOpen && <div className="canvas-asset-tag-filter" role="menu" aria-label="筛选素材类型"><small>标签</small><div>{(["其它", "人物", "场景", "物品", "风格", "音效"] as AssetTag[]).map((tag) => <button key={tag} type="button" className={overviewAssetTags.includes(tag) ? "is-active" : ""} onClick={() => setOverviewAssetTags((tags) => tags.includes(tag) ? tags.filter((item) => item !== tag) : [...tags, tag])}>{tag}</button>)}</div><footer><button type="button" onClick={() => setOverviewAssetTags([])}>清空</button><button type="button" onClick={() => setOverviewAssetFilterOpen(false)}>应用</button></footer></div>}
                <article className="canvas-asset-folder-row"><button type="button" onClick={() => setNotice(`${overviewAssetGroupName} · ${visibleOverviewAssets.length} 项`)}>{renamingAssetGroup ? <input autoFocus aria-label="资产分组名称" value={overviewAssetGroupName} onChange={(event) => setOverviewAssetGroupName(event.target.value)} onBlur={() => setRenamingAssetGroup(false)} onKeyDown={(event) => { if (event.key === "Enter") event.currentTarget.blur(); }} /> : <><span><Folder size={17} /></span><b>{overviewAssetGroupName}</b></>}</button><button type="button" aria-label="资产分组更多操作" aria-expanded={overviewAssetGroupMenuOpen} onClick={() => setOverviewAssetGroupMenuOpen((open) => !open)}><MoreHorizontal size={16} /></button></article>
                {overviewAssetGroupMenuOpen && <div className="canvas-asset-group-menu" role="menu" aria-label="资产分组更多操作"><button type="button" role="menuitem" onClick={() => { setComposerAttachmentIds(visibleOverviewAssets.map((asset) => asset.id)); setPanelOpen(true); setOverviewAssetGroupMenuOpen(false); setNotice("已应用到 Agent"); }}>应用到 Agent</button><button type="button" role="menuitem" onClick={() => { visibleOverviewAssets.forEach(addAttachmentNode); setOverviewAssetGroupMenuOpen(false); }}>发送到画布</button><button type="button" role="menuitem" onClick={() => { setRenamingAssetGroup(true); setOverviewAssetGroupMenuOpen(false); }}>重命名</button><button type="button" role="menuitem" onClick={() => { setOverviewAssetGroupMenuOpen(false); setNotice(visibleOverviewAssets.length ? "文件夹内还有资产，暂时不能删除" : "默认资产分组不可删除"); }}>删除</button></div>}
                <div className="canvas-sidebar-asset-list">{visibleOverviewAssets.map((attachment) => <button key={attachment.id} type="button" onClick={() => addAttachmentNode(attachment)}><span><Icon name={attachmentKind(attachment)} /></span><span><b>{attachment.name}</b><small>{attachment.type || "文件"}</small></span></button>)}</div>
              </>}
            </section>}
          </div>}
          {drawer === "add" && <div className="canvas-add-menu">
            <small>添加节点</small>
            <div>{ADD_NODE_OPTIONS.map((item) => <button key={item.id} type="button" onClick={() => { if (item.id === "library") { setDrawer("assets"); return; } addWorkflowNode(item.kind, { title: item.label }); }}><span><Icon name={item.kind} /></span><b>{item.label}</b>{item.badge && <i>{item.badge}</i>}</button>)}</div>
            <small>添加资源</small>
            <button type="button" className="canvas-add-resource" onClick={() => { setPendingUploadPoint(null); fileInputRef.current?.click(); }}><Upload size={16} /><b>上传</b></button>
            <button type="button" className="canvas-add-resource" onClick={() => setDrawer("history")}><Icon name="history" /><b>从生成历史选择</b></button>
          </div>}
          {drawer === "tools" && <div className="canvas-toolbox-gallery">
            <nav><button type="button" className="is-active">我的工具箱</button><button type="button" onClick={() => setNotice("模板会自动生成一组可编辑节点")}>工具箱模板说明</button><button type="button" onClick={() => setNotice("已切换至周星驰经典名场面模板")}>周星驰经典名场面</button></nav>
            <div>{TOOLBOX_TEMPLATES.map((name, index) => <article key={name}><span className={`canvas-toolbox-preview preview-${index % 6}`}><WandSparkles size={21} /><em>{String(index + 1).padStart(2, "0")}</em></span><footer><b>{name}</b><button type="button" onClick={() => { addWorkflowNode(index === TOOLBOX_TEMPLATES.length - 1 ? "script" : "video", { title: name, description: "由工具箱模板创建，可继续修改输入与参数" }); setNotice(`已使用「${name}」模板`); }}>使用</button></footer></article>)}</div>
          </div>}
          {drawer === "assets" && <div className="canvas-library-menu">
            <button type="button" onClick={() => { setDrawer(null); setLibraryTab("square"); setLibraryCategory("推荐"); setLibraryQuery(""); setLibraryMinimized(false); setOverlay("style-library"); }}><span><Sparkles size={19} /></span><span><b>风格库</b><small>新增风格节点 <i>NEW</i></small></span><ChevronDown size={15} /></button>
            <button type="button" onClick={() => { setDrawer(null); setLibraryTab("square"); setLibraryCategory("推荐"); setLibraryQuery(""); setLibraryMinimized(false); setOverlay("effect-library"); }}><span><WandSparkles size={19} /></span><span><b>特效库</b><small>新增特效节点 <i>NEW</i></small></span><ChevronDown size={15} /></button>
          </div>}
          {drawer === "characters" && <div className="canvas-character-library">
            <section className="canvas-character-feature"><div className="canvas-character-copy"><small>当前角色</small><h2>{selectedCharacter.name}</h2><p>{selectedCharacter.detail}</p><p>保持人物外貌、气质与服装在后续镜头中的连续一致，可随时在节点中继续调整。</p><button type="button" onClick={() => { addWorkflowNode("text", { title: selectedCharacter.name, description: selectedCharacter.detail, assetName: "角色参考" }); setNotice(`已将「${selectedCharacter.name}」应用至画布`); }}>应用至画布</button></div><div className="canvas-character-previews">{["立绘", "脸部近景", "表情参考", "三视图"].map((label, index) => <span key={label} className={`character-preview-${index}`}><UserRound size={38} /><b>{label}</b></span>)}</div></section>
            <header><strong>角色筛选</strong><label><input type="checkbox" /> 仅看最近使用</label></header>
            <div className="canvas-character-carousel">{CHARACTER_PRESETS.map((character) => <button key={character.id} type="button" className={selectedCharacterId === character.id ? "is-selected" : ""} onClick={() => setSelectedCharacterId(character.id)}><span><UserRound size={25} /></span><b>{character.name}</b><small>{character.detail}</small></button>)}</div>
          </div>}
          {drawer === "history" && <div className="canvas-history-library">
            <nav role="tablist" aria-label="历史资产类型">{(["image", "video", "audio"] as const).map((kind) => <button key={kind} type="button" role="tab" aria-selected={historyMediaKind === kind} className={historyMediaKind === kind ? "is-active" : ""} onClick={() => setHistoryMediaKind(kind)}>{kind === "image" ? "图片历史" : kind === "video" ? "视频历史" : "音频历史"}<i>{nodes.filter((node) => kind === "image" ? ["image", "text", "script"].includes(node.data.kind) : node.data.kind === kind).length}</i></button>)}</nav>
            <div className="canvas-history-toolbar"><button type="button"><ArrowUpDown size={14} />时间降序</button><button type="button" onClick={resetWorkflow}>恢复初始布局</button><button type="button" onClick={() => setActivity([])}>批量操作</button></div>
            <section><h3>2026-08-03</h3><div>{historyAssets.map((node, index) => <article key={node.id}><span className={`canvas-history-preview preview-${index % 5}`}><Icon name={node.data.kind} /></span><b>{node.data.title}</b><small>{node.data.description}</small><footer><button type="button" onClick={() => setEditingNodeId(node.id)}>查看</button><button type="button" onClick={() => duplicateOverviewNode(node.id)}>使用</button><button type="button" onClick={exportCanvasDocument}><Download size={14} />下载</button></footer></article>)}</div>{!historyAssets.length && <div className="canvas-drawer-empty"><Icon name="history" /><b>暂无{historyMediaKind === "video" ? "视频" : historyMediaKind === "audio" ? "音频" : "图片"}历史</b></div>}</section>
          </div>}
          {drawer === "overview" && <div className="canvas-sidebar-resizer canvas-sidebar-resizer-left" role="separator" aria-label="调整工作区面板宽度" onPointerDown={(event) => { event.preventDefault(); beginSidebarResize("left", event.clientX); }} />}
        </aside>
      )}

      {overviewNodeMenu && (() => {
        const node = nodes.find((item) => item.id === overviewNodeMenu.nodeId);
        return node ? <div className="canvas-overview-node-menu" style={{ left: overviewNodeMenu.x, top: overviewNodeMenu.y }} role="menu" aria-label={`${node.data.title}操作`}>
          <button type="button" role="menuitem" onClick={() => beginOverviewRename(node)}>重命名</button>
          <button type="button" role="menuitem" onClick={() => duplicateOverviewNode(node.id)}>复制</button>
          <button type="button" role="menuitem" className="is-danger" onClick={() => deleteOverviewNode(node.id)}>删除</button>
        </div> : null;
      })()}

      {contextMenu && (
        <div className="canvas-node-context-menu" style={{ left: contextMenu.x, top: contextMenu.y }} role="menu" aria-label="节点操作">
          <button type="button" role="menuitem" onClick={() => { setEditingNodeId(contextMenu.nodeId); setContextMenu(null); }}><Icon name="text" />编辑详情</button>
          <button type="button" role="menuitem" onClick={() => { duplicateSelectedNodes(); setContextMenu(null); }}><Icon name="copy" />创建副本</button>
          <button type="button" role="menuitem" onClick={() => askAgentForNode(contextMenu.nodeId)}><Icon name="sparkle" />让 Agent 处理</button>
          <span />
          <button type="button" role="menuitem" className="is-danger" onClick={() => { deleteSelectedNode(); setContextMenu(null); }}><Icon name="close" />删除节点</button>
        </div>
      )}

      {editingNode && (
        <div className="canvas-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setEditingNodeId(null); }}>
          <section className="canvas-modal canvas-node-editor" role="dialog" aria-modal="true" aria-label="编辑节点">
            <header><div><small>{editingNode.data.eyebrow}</small><strong>编辑节点</strong></div><button type="button" onClick={() => setEditingNodeId(null)} aria-label="关闭"><Icon name="close" /></button></header>
            <div className="canvas-node-editor-body">
              <label><span>标题</span><input value={editingNode.data.title} onChange={(event) => updateNodeData(editingNode.id, { title: event.target.value })} /></label>
              <label><span>说明</span><textarea value={editingNode.data.description} onChange={(event) => updateNodeData(editingNode.id, { description: event.target.value })} /></label>
              <label><span>关联资产</span><input value={editingNode.data.assetName ?? ""} placeholder="可选" onChange={(event) => updateNodeData(editingNode.id, { assetName: event.target.value || undefined })} /></label>
              <div className="canvas-node-editor-field"><span>状态</span><SelectMenu ariaLabel="节点状态" value={editingNode.data.status} options={WORKFLOW_STATUS_OPTIONS} onChange={(status) => updateNodeData(editingNode.id, { status })} /></div>
            </div>
            <footer><button type="button" onClick={() => setEditingNodeId(null)}>完成</button></footer>
          </section>
        </div>
      )}

      {directorStudioNodeId && (
        <div className="canvas-director-backdrop" role="presentation">
          <section className="canvas-director-studio" role="dialog" aria-modal="true" aria-label="导演台">
            <header>
              <div><span><Camera size={17} /></span><strong>导演台</strong><small>3D 场景 · 多视角截图</small></div>
              <nav><button type="button" onClick={() => setNotice("场景文件选择器已打开")}><Upload size={14} />导入场景</button><button type="button" className="is-primary" onClick={() => { setDirectorShotCount((count) => count + 1); setNotice(`已保存${directorCameraPreset}截图`); }}><Camera size={14} />多视角截图</button><button type="button" aria-label="关闭导演台" onClick={() => setDirectorStudioNodeId(null)}><X size={17} /></button></nav>
            </header>
            <div className="canvas-director-body">
              <aside className="canvas-director-objects">
                <strong>场景对象</strong>
                {["环境 · 城市屋顶", "角色 · 主角", "道具 · 望远镜", "灯光 · 主光", "摄影机 · Camera 01"].map((item, index) => <button key={item} type="button" className={index === 4 ? "is-active" : ""} onClick={() => setNotice(`已选择${item}`)}><span>{index === 0 ? <Box size={14} /> : index === 1 ? <UserRound size={14} /> : index === 4 ? <Camera size={14} /> : <Sparkles size={14} />}</span>{item}</button>)}
                <button type="button" className="canvas-director-add-object" onClick={() => setNotice("已新建空场景对象")}><Plus size={14} />添加对象</button>
              </aside>
              <section className="canvas-director-viewport">
                <div className="director-toolbar"><button type="button" className="is-active">移动</button><button type="button">旋转</button><button type="button">缩放</button><span /><button type="button">透视</button><button type="button">网格</button></div>
                <div className={`director-stage camera-${directorCameraPreset === "正面机位" ? "front" : directorCameraPreset === "侧面机位" ? "side" : "top"}`}>
                  <div className="director-grid-floor" />
                  <div className="director-character"><i /><b /><span /></div>
                  <div className="director-prop" />
                  <div className="director-camera-frame"><span>16:9</span><i>REC</i></div>
                  <div className="director-light-cone" />
                </div>
                <footer><span>Camera 01</span><b>{directorCameraPreset}</b><span>截图 {directorShotCount}</span></footer>
              </section>
              <aside className="canvas-director-inspector">
                <strong>摄影机</strong>
                <label><span>机位预设</span><div>{["正面机位", "侧面机位", "俯视机位"].map((preset) => <button key={preset} type="button" className={directorCameraPreset === preset ? "is-active" : ""} onClick={() => setDirectorCameraPreset(preset)}>{preset.replace("机位", "")}</button>)}</div></label>
                <fieldset><legend>Transform</legend>{["位置 X", "位置 Y", "位置 Z", "旋转 X", "旋转 Y", "旋转 Z"].map((label, index) => <label key={label}><span>{label}</span><input type="number" defaultValue={index === 2 ? 8 : index === 4 ? 180 : 0} /></label>)}</fieldset>
                <fieldset><legend>镜头</legend><label><span>焦距</span><input type="range" min="18" max="120" defaultValue="50" /><small>50mm</small></label><label><span>景深</span><input type="range" min="0" max="100" defaultValue="32" /><small>32%</small></label><label><span>曝光</span><input type="range" min="-3" max="3" step="0.1" defaultValue="0" /><small>0.0</small></label></fieldset>
                <button type="button" className="canvas-director-capture" onClick={() => { setDirectorShotCount((count) => count + 1); setNotice(`已保存${directorCameraPreset}截图`); }}><Camera size={15} />保存当前视角</button>
              </aside>
            </div>
          </section>
        </div>
      )}

      {panelOpen && (
        <aside className="canvas-agent-panel">
          <header className="canvas-agent-panel-header"><div><strong>{isNewConversation ? "新对话" : "未命名对话 2026/8/3 14:47"}</strong></div><nav aria-label="对话操作"><button type="button" disabled={isNewConversation} onClick={() => { setPrompt(""); setActiveJob(null); setPanelTab("conversation"); setIsNewConversation(true); setAgentHeaderPopover(null); }} aria-label={isNewConversation ? "当前已是新对话" : "新建对话"} title="新建对话"><CirclePlus size={15} /></button><button type="button" className={agentHeaderPopover === "history" ? "is-active" : ""} onClick={() => setAgentHeaderPopover((current) => current === "history" ? null : "history")} aria-label="历史对话" title="历史对话"><Clock3 size={15} /></button><button type="button" disabled={isNewConversation} className={agentHeaderPopover === "share" ? "is-active" : ""} onClick={() => setAgentHeaderPopover((current) => current === "share" ? null : "share")} aria-label={isNewConversation ? "新对话无法分享" : "分享"} title="分享"><Share2 size={15} /></button><button type="button" onClick={() => { setAgentSettingsOpen(true); setAgentHeaderPopover(null); }} aria-label="Agent 设置" title="Agent 设置"><SlidersHorizontal size={15} /></button><button type="button" onClick={() => { setComposerMenu("skill"); setAgentHeaderPopover(null); }} aria-label="CLI & Skill" title="CLI & Skill"><Blocks size={15} /></button></nav><button type="button" className="canvas-agent-panel-close" onClick={() => { setPanelOpen(false); setAgentHeaderPopover(null); }} aria-label="关闭 Agent 面板" title="关闭"><Icon name="collapse-panel" /></button></header>
          {agentHeaderPopover === "history" && <div className="canvas-agent-header-popover canvas-agent-history-popover" role="dialog" aria-label="历史对话"><strong>历史对话</strong><article><button type="button" onClick={() => { setIsNewConversation(false); setAgentHeaderPopover(null); setPanelTab("conversation"); }}><b>未命名对话 2026/8/3 14:47</b><small>15:35</small></button><button type="button" aria-label="删除未命名对话" onClick={() => setNotice("对话已从历史列表移除")}><Trash2 size={14} /></button></article>{runHistory.slice(0, 4).map((run) => <article key={run.id}><button type="button" onClick={() => { setPanelTab("history"); setAgentHeaderPopover(null); }}><b>{run.prompt.slice(0, 24)}</b><small>{run.time}</small></button><button type="button" aria-label={`删除${run.prompt}`} onClick={() => setRunHistory((items) => items.filter((item) => item.id !== run.id))}><Trash2 size={14} /></button></article>)}</div>}
          {agentHeaderPopover === "share" && <div className="canvas-agent-header-popover canvas-agent-share-popover" role="dialog" aria-label="分享"><strong>分享当前对话</strong><b>公开浏览权限</b><p>点击下方按钮生成链接。有链接的人可以浏览对话内容，不可编辑。</p><button type="button" onClick={() => { void navigator.clipboard.writeText(`${window.location.href}#conversation`); setNotice("对话分享链接已生成并复制"); setAgentHeaderPopover(null); }}>生成分享链接</button></div>}
          <nav className="canvas-agent-tabs" role="tablist" aria-label="Agent 面板">
            <button type="button" role="tab" aria-selected={panelTab === "skills"} className={panelTab === "skills" ? "is-active" : ""} onClick={() => setPanelTab("skills")}>建议 Skill</button>
            <button type="button" role="tab" aria-selected={panelTab === "history"} className={panelTab === "history" ? "is-active" : ""} onClick={() => setPanelTab("history")}>历史{runHistory.length > 0 && <b>{runHistory.length}</b>}</button>
            <button type="button" role="tab" aria-selected={panelTab === "settings"} className={panelTab === "settings" ? "is-active" : ""} onClick={() => setPanelTab("settings")}>设置</button>
          </nav>
          <div className="canvas-agent-panel-body">
            {panelTab === "conversation" && (isNewConversation ? <section className="canvas-agent-starter"><header><p>说个想法。或者，选个 Skill</p><button type="button" onClick={() => setSkillBatchIndex((index) => (index + 1) % AGENT_SKILL_BATCHES.length)}>换一批</button></header><div>{AGENT_SKILL_BATCHES[skillBatchIndex].map((skill) => <button key={skill.id} type="button" onClick={() => useLibrarySkill(skill)}><span><Sparkles size={16} /></span><span><b>{skill.title}</b><small>{skill.slug}</small></span></button>)}</div></section> : <section className="canvas-agent-conversation-blank" aria-label="当前对话" />)}
            {panelTab === "skills" && <section className="canvas-skill-suggestions">
              <div className="canvas-agent-context"><small>当前作品</small><strong>{workName || "unnamed"}</strong><p>{attachments.length ? `已关联 ${attachments.length} 个源文件` : "从文字需求开始创作"}</p></div>
              <h3><Icon name="sparkle" />Skill 全开，故事走起</h3>
              {suggestedSkills.map((skill) => <button key={skill.id} type="button" className={activeSkill === skill.id ? "is-active" : ""} onClick={() => useSuggestedSkill(skill)}><span><b>{skill.title}</b><small>{skill.description}</small></span><i>使用</i></button>)}
            </section>}
            {panelTab === "history" && <section className="canvas-run-history">
              {activeJob?.output && <pre className="canvas-agent-output" title="Agent 最新输出">{activeJob.output.slice(-6000)}</pre>}
              {runHistory.length ? runHistory.map((run) => <article key={run.id} className={`run-${run.state}`}><header><span>{run.state === "succeeded" ? "✓" : run.state === "failed" ? "!" : "•"}</span><b>{run.state === "running" ? "执行中" : run.state === "queued" ? "排队中" : run.state === "succeeded" ? "已完成" : run.state === "failed" ? "失败" : "已取消"}</b><time>{run.time}</time></header><p>{run.prompt}</p><small>{run.message}</small></article>) : <div className="canvas-drawer-empty"><Icon name="history" /><b>还没有 Agent 任务</b><p>在下方输入框发送第一条创作指令。</p></div>}
            </section>}
            {panelTab === "settings" && <section className="canvas-agent-settings">
              <div className="canvas-gateway-card"><span className={gateway && gateway.mode !== "demo" ? "agent-status-dot is-live" : "agent-status-dot"} /><span><small>当前执行环境</small><b>{gateway?.label ?? "正在检测本地 Agent…"}</b></span></div>
              <label><span><b>附带画布上下文</b><small>发送节点数和连线信息，帮助 Agent 理解当前进度</small></span><input type="checkbox" checked={includeCanvasContext} onChange={(event) => setIncludeCanvasContext(event.target.checked)} /></label>
              <label><span><b>自动查看最新任务</b><small>提交后自动切换到历史与实时输出</small></span><input type="checkbox" checked={followLatestRun} onChange={(event) => setFollowLatestRun(event.target.checked)} /></label>
              <div className="canvas-agent-security"><b>{gateway?.mode === "local" ? "本地桥接已隔离" : "密钥只保存在服务端"}</b><p>{gateway?.mode === "local" ? "任务只在授权后发送到受控作品目录。" : "浏览器不会接触模型 API Key。"}</p></div>
              <button type="button" className="canvas-clear-data-button" onClick={() => setOverlay("clear-data")}><Icon name="close" /><span><b>清除本机作品数据</b><small>删除当前作品、画布快照和本机素材</small></span></button>
            </section>}
          </div>
          <div className="canvas-sidebar-resizer canvas-sidebar-resizer-right" role="separator" aria-label="调整 AI 助手面板宽度" onPointerDown={(event) => { event.preventDefault(); beginSidebarResize("right", event.clientX); }} />
        </aside>
      )}

      {panelOpen ? (
        <section className="skill-composer canvas-home-composer" onClick={(event) => event.stopPropagation()}>
          <div className="composer-prompt-row">
            {activeSkill && activeSkillTitle && (
              <div className="composer-selected-token">
                <button className="token-main" type="button" title="更换 Skill" onClick={() => setComposerMenu(composerMenu === "skill" ? null : "skill")}>
                  <LineIcon line={work.line} /><span>{activeSkillTitle}</span>
                </button>
                <button className="token-remove" type="button" title="移除 Skill" aria-label={`移除 ${activeSkillTitle}`} onClick={() => setActiveSkill(null)}><X size={12} /></button>
              </div>
            )}
            {selectedModel && (
              <div className="composer-selected-token">
                <button className="token-main" type="button" title="更换模型" onClick={() => setComposerMenu(composerMenu === "model" ? null : "model")}>
                  <Box size={15} /><span>{selectedModel.name}</span>
                </button>
                <button className="token-remove" type="button" title="移除模型" aria-label={`移除 ${selectedModel.name}`} onClick={() => setCreationConfig((current) => ({ ...current, model: { ...current.model, modelId: "" } }))}><X size={12} /></button>
              </div>
            )}
            <textarea
              value={prompt}
              aria-label="创作需求"
              placeholder={prompt || activeSkill || selectedModel ? "" : "请输入你的创作灵感，或从下方挑选一个 Skill 开始"}
              onChange={(event) => setPrompt(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Escape") {
                  setComposerMenu(null);
                  return;
                }
                if (event.key === "Backspace" && !prompt) {
                  event.preventDefault();
                  if (selectedModel) setCreationConfig((current) => ({ ...current, model: { ...current.model, modelId: "" } }));
                  else if (activeSkill) setActiveSkill(null);
                  return;
                }
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void submit();
                }
              }}
            />
          </div>

          <div className="composer-inline-choices" aria-label="创作设置">
            <div className="composer-menu-wrap model-menu-wrap">
              <button className={composerMenu === "model" ? "composer-menu-button icon-only active" : "composer-menu-button icon-only"} type="button" title="选择模型" aria-label="选择模型" aria-expanded={composerMenu === "model"} onClick={() => setComposerMenu(composerMenu === "model" ? null : "model")}>
                <Box size={18} strokeWidth={1.6} />
              </button>
              {composerMenu === "model" && (
                <div className="floating-panel model-picker" role="dialog" aria-label="选择模型">
                  <div className="floating-panel-title"><strong>选择模型</strong></div>
                  <div className="segmented-tabs" role="tablist">
                    {(Object.keys(CANVAS_MODALITY_LABELS) as ModelModality[]).map((item) => (
                      <button key={item} className={modelModality === item ? "active" : ""} type="button" role="tab" aria-selected={modelModality === item} onClick={() => setModelModality(item)}>{CANVAS_MODALITY_LABELS[item]}</button>
                    ))}
                  </div>
                  <div className="model-section-label">{CANVAS_MODALITY_LABELS[modelModality]}</div>
                  <div className="model-list">
                    {MODEL_GROUPS[modelModality].map((model) => (
                      <div key={model.id} className="model-row">
                        <button className="model-row-main" type="button" onClick={() => {
                          setCreationConfig((current) => ({ ...current, model: { modality: model.modality, modelId: model.id, ...(model.providerSpec ? { providerSpec: model.providerSpec } : {}) } }));
                          setModelModality(model.modality);
                          setComposerMenu(null);
                          setNotice(`已选择 ${model.name}`);
                        }}>
                          <span className={`model-mark provider-${model.provider.toLocaleLowerCase().replace(/\W+/g, "-")}`}>{model.name.slice(0, 1)}</span>
                          <span className="model-copy">
                            <span className="model-name"><b>{model.name}</b>{model.premium && <span className="model-membership-mark" role="button" tabIndex={0} aria-label={`查看 ${model.name} 的会员积分方案`} onClick={(event) => { event.stopPropagation(); setComposerMenu(null); setMembershipOpen(true); }} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); event.stopPropagation(); setComposerMenu(null); setMembershipOpen(true); } }}><MembershipMark /></span>}</span>
                            <small>{model.description}</small>
                          </span>
                          <Plus size={16} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="composer-menu-wrap skill-menu-wrap">
              <button className={composerMenu === "skill" ? "composer-menu-button icon-only active" : "composer-menu-button icon-only"} type="button" title="选择 Skill" aria-label="选择 Skill" aria-expanded={composerMenu === "skill"} onClick={() => setComposerMenu(composerMenu === "skill" ? null : "skill")}>
                <ClipboardPenLine size={18} strokeWidth={1.6} />
              </button>
              {composerMenu === "skill" && (
                <div className="floating-panel skill-picker" role="dialog" aria-label="选择 Skill">
                  <div className="skill-picker-heading">
                    <strong>Skill</strong>
                    <div className="skill-picker-heading-actions">
                      <button type="button" onClick={() => { setComposerMenu(null); setCanvasCreateSkillOpen(true); }}><Plus size={14} />创建</button>
                      <button type="button" onClick={() => { setComposerMenu(null); setCanvasSkillCatalogTab("skills"); setCanvasSkillCatalogCategory("全部"); setCanvasSkillCatalogQuery(""); setAllCanvasSkillsOpen(true); }}>全部</button>
                    </div>
                  </div>
                  <div className="skill-picker-toolbar">
                    <div className="skill-picker-tabs">
                      {([["common", "通用"], ["favorite", "收藏"], ["mine", "我的"]] as const).map(([key, label]) => (
                        <button key={key} className={skillPickerTab === key ? "active" : ""} type="button" onClick={() => setSkillPickerTab(key)}>{label}</button>
                      ))}
                    </div>
                    <label className="panel-search"><Search size={15} /><input aria-label="搜索 Skill" value={skillPickerQuery} onChange={(event) => setSkillPickerQuery(event.target.value)} placeholder="搜索 Skill" /></label>
                  </div>
                  <div className="skill-picker-list">
                    {visibleSkillLibrary.map((skill) => (
                      <div className="skill-picker-row" key={skill.id}>
                        <button type="button" className="skill-picker-main" onClick={() => useLibrarySkill(skill)}>
                          <span className="picker-skill-icon"><Wrench size={15} /></span>
                          <span className="skill-picker-copy">
                            <span className="skill-picker-name"><b>{skill.title}</b><small>{skill.id.startsWith("user:") ? "我的 Skill" : skill.slug}</small></span>
                            <em>{skill.description}</em>
                          </span>
                        </button>
                        <button type="button" className="skill-picker-detail" onClick={() => { setComposerMenu(null); setSkillDetailId(skill.id); }}>详情</button>
                      </div>
                    ))}
                    {!visibleSkillLibrary.length && <div className="picker-empty">没有匹配的 Skill</div>}
                    {skillPickerTab === "common" && !skillPickerQuery.trim() && (
                      <button className="skill-picker-view-all" type="button" onClick={() => { setComposerMenu(null); setCanvasSkillCatalogTab("skills"); setCanvasSkillCatalogCategory("全部"); setCanvasSkillCatalogQuery(""); setAllCanvasSkillsOpen(true); }}>没找到合适的？查看全部 Skill <ChevronRight size={14} /></button>
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="composer-menu-wrap compact mode-menu-wrap">
              <button className={composerMenu === "mode" ? "composer-menu-button icon-only active" : "composer-menu-button icon-only"} type="button" title={creationConfig.generationMode === "auto" ? "自动模式" : "手动模式"} aria-label={creationConfig.generationMode === "auto" ? "自动模式" : "手动模式"} aria-expanded={composerMenu === "mode"} onClick={() => setComposerMenu(composerMenu === "mode" ? null : "mode")}>
                <Hand size={18} strokeWidth={1.6} />
              </button>
              {composerMenu === "mode" && (
                <div className="floating-panel mode-picker" role="dialog" aria-label="生成模式">
                  <strong>生成模式</strong>
                  <button className={creationConfig.generationMode === "manual" ? "selected" : ""} type="button" onClick={() => { setCreationConfig((current) => ({ ...current, generationMode: "manual" })); setComposerMenu(null); }}><span className="mode-option-copy"><b>手动模式</b><small>Agent 在每次生成前询问</small></span><span className="mode-selection-mark" aria-hidden="true">{creationConfig.generationMode === "manual" && <Check size={15} />}</span></button>
                  <button className={creationConfig.generationMode === "auto" ? "selected" : ""} type="button" onClick={() => { setCreationConfig((current) => ({ ...current, generationMode: "auto" })); setComposerMenu(null); }}><span className="mode-option-copy"><b>自动模式</b><small>Agent 按工作流连续推进</small></span><span className="mode-selection-mark" aria-hidden="true">{creationConfig.generationMode === "auto" && <Check size={15} />}</span></button>
                </div>
              )}
            </div>
          </div>

          {composerAttachments.length > 0 && (
            <div className="composer-attachments">
              {composerAttachments.map((attachment) => (
                <button key={attachment.id} type="button" onClick={() => setComposerAttachmentIds((ids) => ids.filter((id) => id !== attachment.id))}>
                  <Paperclip size={14} /><span>{attachment.name}</span><X size={13} />
                </button>
              ))}
            </div>
          )}
          <div className="skill-composer-toolbar">
            <ComposerAssetPicker
              assets={attachments}
              selectedIds={composerAttachmentIds}
              menuOpen={composerMenu === "assets"}
              onMenuOpenChange={(open) => setComposerMenu(open ? "assets" : null)}
              onUpload={uploadComposerAssets}
              onSelectionChange={setComposerAttachmentIds}
              buttonClassName="composer-icon-button"
            />
            <span className="composer-toolbar-hint">回车开始 · Shift + 回车换行</span>
            <span className="composer-grow" />
            <button className="composer-submit" type="button" disabled={!gateway || !composerReady || submitting} onClick={() => void submit()} aria-label="开始创作">{submitting ? <span className="canvas-submit-spinner">•••</span> : <ArrowUp size={21} />}</button>
          </div>
        </section>
      ) : <button type="button" className="canvas-agent-collapsed-hint" onClick={() => setPanelOpen(true)}>开始你的创作，或者 @ 引用工作流/节点/资源</button>}

      {canvasHistoryPickerOpen && (
        <div className="canvas-modal-backdrop canvas-history-picker-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) { setCanvasHistoryPickerOpen(false); setCanvasHistorySelection([]); setHistoryInsertPoint(null); } }}>
          <section className="canvas-history-picker" role="dialog" aria-modal="true" aria-label={`选择${CANVAS_HISTORY_MEDIA.find((item) => item.id === canvasHistoryMedia)?.label ?? "素材"}`}>
            <header>
              <strong>选择{CANVAS_HISTORY_MEDIA.find((item) => item.id === canvasHistoryMedia)?.label ?? "素材"}</strong>
              <button type="button" aria-label="关闭生成历史" onClick={() => { setCanvasHistoryPickerOpen(false); setCanvasHistorySelection([]); setHistoryInsertPoint(null); }}><X size={20} /></button>
            </header>
            <div className="canvas-history-picker-toolbar">
              <nav className="canvas-history-source-tabs" aria-label="生成历史来源">
                {CANVAS_HISTORY_SOURCES.map((source) => <button key={source.id} type="button" className={canvasHistorySource === source.id ? "is-active" : ""} onClick={() => { setCanvasHistorySource(source.id); setCanvasHistorySelection([]); }}>{source.label}</button>)}
              </nav>
              <span>已选 <b>{canvasHistorySelection.length}/10</b> 张</span>
            </div>
            <nav className="canvas-history-media-tabs" aria-label="生成历史类型">
              {CANVAS_HISTORY_MEDIA.map((media) => <button key={media.id} type="button" className={canvasHistoryMedia === media.id ? "is-active" : ""} onClick={() => { setCanvasHistoryMedia(media.id); setCanvasHistorySelection([]); }}>{media.label}</button>)}
            </nav>
            <div className="canvas-history-picker-content">
              {canvasHistoryPickerItems.length ? <div className="canvas-history-picker-grid">
                {canvasHistoryPickerItems.map((item, index) => {
                  const selected = canvasHistorySelection.includes(item.id);
                  return <button key={item.id} type="button" className={selected ? "is-selected" : ""} aria-pressed={selected} onClick={() => toggleCanvasHistoryItem(item.id)}>
                    <span className={`canvas-history-picker-preview preview-${index % 6}`}><Icon name={item.kind} /><i>{selected && <Check size={15} />}</i></span>
                    <span><b>{item.title}</b><small>{item.description}</small></span>
                  </button>;
                })}
              </div> : <div className="canvas-history-picker-empty"><Icon name={canvasHistoryMedia} /><strong>暂无{CANVAS_HISTORY_MEDIA.find((item) => item.id === canvasHistoryMedia)?.label}历史</strong><span>{canvasHistorySource === "libtv" ? "生成或上传素材后会显示在这里" : `连接 ${CANVAS_HISTORY_SOURCES.find((item) => item.id === canvasHistorySource)?.label} 后即可选择`}</span></div>}
            </div>
            <footer>
              <div className="canvas-history-pagination"><button type="button" disabled aria-label="上一页">‹</button><button type="button" className="is-active">1</button><button type="button" disabled aria-label="下一页">›</button><span>15条/页</span><span>跳至</span><input aria-label="跳转页码" value="1" readOnly /><span>页</span></div>
              <button type="button" className="canvas-history-confirm" disabled={!canvasHistorySelection.length} onClick={confirmCanvasHistorySelection}>确定</button>
            </footer>
          </section>
        </div>
      )}

      {agentSettingsOpen && <div className="canvas-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setAgentSettingsOpen(false); }}><section className="canvas-modal canvas-agent-settings-dialog" role="dialog" aria-modal="true" aria-label="Agent 设置"><header><div><strong>Agent 设置</strong></div><button type="button" onClick={() => setAgentSettingsOpen(false)} aria-label="关闭"><Icon name="close" /></button></header><div className="canvas-agent-settings-dialog-body"><div className="canvas-agent-free-notice"><Sparkles size={16} />非会员每天免费对话 3 轮，即刻体验！</div><small>协作模式</small><label><span><b>自动生成图片/视频</b><p>开启后，Agent 可直接消耗积分，提交图片/视频生成，无需逐次确认</p></span><input type="checkbox" role="switch" aria-label="自动生成图片/视频" checked={agentAutoMedia} onChange={(event) => setAgentAutoMedia(event.target.checked)} /></label><small>通知设置</small><label><span><b>浏览器通知</b><p>Agent 回复完成后，会在系统通知提醒</p></span><input type="checkbox" role="switch" aria-label="浏览器通知" checked={agentBrowserNotifications} onChange={(event) => setAgentBrowserNotifications(event.target.checked)} /></label><label><span><b>通知声音</b><p>开启后，收到通知时播放提示音</p></span><input type="checkbox" role="switch" aria-label="通知声音" checked={agentNotificationSound} onChange={(event) => setAgentNotificationSound(event.target.checked)} /></label></div><footer><button type="button" onClick={() => setAgentSettingsOpen(false)}>取消</button><button type="button" onClick={() => { setAgentSettingsOpen(false); setNotice("Agent 设置已保存"); }}>完成</button></footer></section></div>}

      {allCanvasSkillsOpen && (
        <div className="modal-backdrop skill-catalog-backdrop" role="presentation" onMouseDown={() => setAllCanvasSkillsOpen(false)}>
          <section className="skill-catalog-modal" role="dialog" aria-modal="true" aria-label="全部 Skill" onMouseDown={(event) => event.stopPropagation()}>
            <button className="skill-catalog-close" type="button" aria-label="关闭全部 Skill" onClick={() => setAllCanvasSkillsOpen(false)}><X size={14} /></button>
            <div className="skill-catalog-scroll">
              <header className="skill-catalog-header">
                <nav className="skill-catalog-tabs" aria-label="Skill 分类">
                  {([["skills", "Skill"], ["favorite", "收藏"], ["mine", "我的"]] as const).map(([key, label]) => (
                    <button key={key} className={canvasSkillCatalogTab === key ? "active" : ""} type="button" onClick={() => { setCanvasSkillCatalogTab(key); setCanvasSkillCatalogQuery(""); }}>{label}</button>
                  ))}
                </nav>
                {canvasSkillCatalogTab === "skills" && (
                  <div className="skill-catalog-toolbar">
                    <div className="skill-catalog-categories">
                      {["全部", "商业广告", "剧情短片", "视觉风格"].map((item) => <button key={item} className={canvasSkillCatalogCategory === item ? "active" : ""} type="button" onClick={() => setCanvasSkillCatalogCategory(item)}>{item}</button>)}
                    </div>
                    <label className="skill-catalog-search"><Search size={14} /><input aria-label="搜索全部 Skill" value={canvasSkillCatalogQuery} onChange={(event) => setCanvasSkillCatalogQuery(event.target.value)} placeholder="搜索 Skill" /></label>
                  </div>
                )}
              </header>
              {canvasCatalogSkills.length ? (
                <div className="skill-catalog-grid">
                  {canvasCatalogSkills.map((skill) => (
                    <article className="skill-catalog-card" key={skill.id} onClick={() => setSkillDetailId(skill.id)}>
                      <div className={`skill-catalog-cover skill-cover-${work.line}`}>
                        <img src={`/skill-covers/${work.line}.jpg`} alt="" loading="lazy" draggable={false} />
                        <span>{work.line === "novel" ? "文字" : work.line === "song" ? "音频" : work.line === "comic" ? "图片" : "视频"}</span>
                      </div>
                      <div className="skill-catalog-copy">
                        <h3>{skill.title}</h3>
                        <p>{skill.description}</p>
                        <footer><span>{skill.creator ?? "Jookei"}</span><i aria-hidden="true" /><span><UserRound size={12} />1.5w</span></footer>
                      </div>
                      <div className="skill-catalog-actions">
                        <button type="button" title={canvasFavoriteSkills.has(skill.id) ? "取消收藏" : "收藏"} aria-label={canvasFavoriteSkills.has(skill.id) ? "取消收藏" : "收藏"} className={canvasFavoriteSkills.has(skill.id) ? "active" : ""} onClick={(event) => { event.stopPropagation(); toggleCanvasSkillFavorite(skill.id); }}><Star size={14} fill={canvasFavoriteSkills.has(skill.id) ? "currentColor" : "none"} /></button>
                        <button type="button" className="use" onClick={(event) => { event.stopPropagation(); useLibrarySkill(skill); }}>使用</button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="skill-catalog-empty"><Search size={28} /><strong>没有找到相关 Skill</strong><span>换个分类或关键词试试</span></div>
              )}
            </div>
          </section>
        </div>
      )}

      {selectedSkillDetail && (
        <div className="modal-backdrop skill-detail-backdrop" role="presentation" onMouseDown={() => setSkillDetailId(null)}>
          <section className="skill-detail-modal" role="dialog" aria-modal="true" aria-label={selectedSkillDetail.title} onMouseDown={(event) => event.stopPropagation()}>
            <button className="modal-close" type="button" aria-label="关闭" onClick={() => setSkillDetailId(null)}><X size={12} /></button>
            <header className="libtv-detail-header">
              <div className="libtv-detail-heading">
                <h2>{selectedSkillDetail.title}</h2>
                <div className="libtv-detail-meta">
                  <span className="detail-author-avatar">{(selectedSkillDetail.creator ?? "Jookei").slice(0, 1).toUpperCase()}</span>
                  <span>{selectedSkillDetail.creator ?? "Jookei"}</span><i aria-hidden="true" />
                  <span>{selectedSkillDetail.category ?? "商业广告"}</span><i aria-hidden="true" />
                  <span><UserRound size={13} />1.5w</span><i aria-hidden="true" />
                  <span><Star size={13} />{canvasFavoriteSkills.has(selectedSkillDetail.id) ? 626 : 625}</span>
                </div>
              </div>
              <div className="libtv-detail-actions">
                <button type="button" aria-label="分享" title="分享" onClick={() => { void navigator.clipboard?.writeText(window.location.href); setNotice("页面链接已复制"); }}><Share2 size={16} /></button>
                <button className={canvasFavoriteSkills.has(selectedSkillDetail.id) ? "active" : ""} type="button" aria-label={canvasFavoriteSkills.has(selectedSkillDetail.id) ? "取消收藏" : "收藏"} title={canvasFavoriteSkills.has(selectedSkillDetail.id) ? "取消收藏" : "收藏"} onClick={() => toggleCanvasSkillFavorite(selectedSkillDetail.id)}><Star size={16} fill={canvasFavoriteSkills.has(selectedSkillDetail.id) ? "currentColor" : "none"} /></button>
                {selectedSkillDetail.id.startsWith("user:") && <button className="danger" type="button" aria-label="删除" title="删除" onClick={() => deleteCanvasSkill(selectedSkillDetail)}><Trash2 size={15} /></button>}
                <button className="primary" type="button" onClick={() => useLibrarySkill(selectedSkillDetail)}>添加 Skill</button>
              </div>
            </header>
            <div className="libtv-detail-body">
              <section className="libtv-detail-info">
                <h3>简介</h3>
                <dl>
                  <div><dt>介绍</dt><dd>{selectedSkillDetail.description}</dd></div>
                  <div><dt>使用场景</dt><dd>{(selectedSkillDetail.useCases ?? ["短片制作", "广告创意", "社交媒体内容"]).join("、")}</dd></div>
                  <div><dt>工作流</dt><dd>{(selectedSkillDetail.steps ?? ["创意分析", "素材规划", "分镜生成", "成片交付"]).join(" → ")}</dd></div>
                  <div><dt>如何使用</dt><dd>{selectedSkillDetail.guide ?? "提供主题、角色、画面比例和时长，Agent 会依次规划素材、分镜、生成节点和最终交付。"}</dd></div>
                  <div><dt>输出内容</dt><dd>{work.line === "novel" ? "文字" : work.line === "song" ? "音频" : work.line === "comic" ? "图片" : "视频"}</dd></div>
                </dl>
              </section>
              <section className="libtv-detail-source">
                <h3>Skill</h3>
                <div className="libtv-workflow-preview">{(selectedSkillDetail.steps ?? ["创意分析", "素材规划", "分镜生成", "成片交付"]).map((step, index) => <span key={`${step}-${index}`}><b>{index + 1}</b>{step}</span>)}</div>
              </section>
            </div>
          </section>
        </div>
      )}

      <CreateSkillDialog
        open={canvasCreateSkillOpen}
        ownerEmail="本地创作者"
        onClose={() => setCanvasCreateSkillOpen(false)}
        onCreate={createCanvasSkill}
      />

      {overlay && (
        <div className="canvas-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) { setOverlay(null); setLibraryInsertPoint(null); setLibraryDetail(null); } }}>
          <section className={`canvas-modal canvas-modal-${overlay}${libraryMinimized && (overlay === "style-library" || overlay === "effect-library") ? " is-minimized" : ""}`} role="dialog" aria-modal="true" aria-label={overlay === "shortcuts" ? "快捷键" : overlay === "tutorial" ? "画布教程" : overlay === "share" ? "发布与分享" : overlay === "style-library" ? "风格库" : overlay === "effect-library" ? "特效库" : "清除本机作品数据"}>
            <header><div><small>{overlay === "share" ? "CANVAS" : overlay === "clear-data" ? "LOCAL DATA" : overlay === "style-library" || overlay === "effect-library" ? "ASSET LIBRARY" : "CANVAS GUIDE"}</small><strong>{overlay === "shortcuts" ? "快捷键" : overlay === "tutorial" ? "快速上手" : overlay === "share" ? "发布与分享" : overlay === "style-library" ? "风格库" : overlay === "effect-library" ? "特效库" : "清除本机作品数据"}</strong></div>{(overlay === "style-library" || overlay === "effect-library") && <button type="button" onClick={() => setLibraryMinimized((minimized) => !minimized)} aria-label={libraryMinimized ? "展开素材库" : "最小化素材库"}>{libraryMinimized ? <Maximize2 size={15} /> : <Minimize2 size={15} />}</button>}<button type="button" onClick={() => { setOverlay(null); setLibraryInsertPoint(null); setLibraryDetail(null); }} aria-label="关闭"><Icon name="close" /></button></header>
            {overlay === "shortcuts" ? <div className="canvas-shortcut-list"><span><kbd>⌘ Z</kbd><b>撤销</b></span><span><kbd>⇧⌘ Z</kbd><b>重做</b></span><span><kbd>⌘ C</kbd><b>复制节点</b></span><span><kbd>⌘ V</kbd><b>粘贴节点</b></span><span><kbd>⌘ D</kbd><b>创建副本</b></span><span><kbd>⌫</kbd><b>删除节点</b></span><span><kbd>A</kbd><b>打开添加节点</b></span><span><kbd>V</kbd><b>选择工具</b></span><span><kbd>H</kbd><b>移动画布</b></span><span><kbd>G</kbd><b>切换网格吸附</b></span><span><kbd>?</kbd><b>查看快捷键</b></span><span><kbd>Esc</kbd><b>关闭弹层</b></span></div> : overlay === "tutorial" ? <ol className="canvas-tutorial-list"><li><i>1</i><span><b>选择或添加节点</b><small>从左侧添加文本、图片、音频等工作流节点。</small></span></li><li><i>2</i><span><b>连接并整理流程</b><small>拖动节点连接点建立依赖，再用底部整理按钮排列。</small></span></li><li><i>3</i><span><b>让 Agent 执行</b><small>选择右侧建议 Skill，或在底部直接输入下一步任务。</small></span></li></ol> : overlay === "share" ? <div className="canvas-share-actions">
              <button type="button" onClick={() => void copyShareLink()}><span><Icon name="share" /></span><span><b>复制分享链接</b><small>使用当前稳定画布 URL；云端同步后可跨设备恢复。</small></span></button>
              <button type="button" onClick={exportCanvasDocument}><span><Icon name="download" /></span><span><b>导出画布 JSON</b><small>下载节点、连线、视图与 Agent 运行记录的便携副本。</small></span></button>
            </div> : overlay === "style-library" || overlay === "effect-library" ? <div className="canvas-preset-library">
              <nav role="tablist" aria-label="素材库分类">
                <button type="button" role="tab" aria-selected={libraryTab === "square"} className={libraryTab === "square" ? "is-active" : ""} onClick={() => setLibraryTab("square")}>{overlay === "style-library" ? "风格广场" : "特效广场"}</button>
                <button type="button" role="tab" aria-selected={libraryTab === "favorite"} className={libraryTab === "favorite" ? "is-active" : ""} onClick={() => setLibraryTab("favorite")}>我的收藏</button>
                <button type="button" role="tab" aria-selected={libraryTab === "recent"} className={libraryTab === "recent" ? "is-active" : ""} onClick={() => setLibraryTab("recent")}>最近使用</button>
                <label><Search size={15} /><input aria-label="搜索素材" value={libraryQuery} onChange={(event) => setLibraryQuery(event.target.value)} placeholder={overlay === "style-library" ? "搜索风格名称、作者" : "搜索特效名称、作者"} /></label>
              </nav>
              <aside>{(overlay === "effect-library" ? ["推荐"] : PRESET_CATEGORIES).map((category) => <button key={category} type="button" className={libraryCategory === category ? "is-active" : ""} onClick={() => setLibraryCategory(category)}>{category}</button>)}</aside>
              <section><header><label><input type="checkbox" checked={libraryCommercialOnly} onChange={(event) => setLibraryCommercialOnly(event.target.checked)} /> 仅看可商用</label><button type="button">全部 <ChevronDown size={13} /></button></header>
                {visibleLibraryPresets.length ? <div>{visibleLibraryPresets.map((preset, index) => <article key={preset.name} className="canvas-preset-card" onClick={() => {
                  addWorkflowNode(overlay === "style-library" ? "image" : "video", { title: preset.name, description: overlay === "style-library" ? `应用「${preset.name}」风格生成画面` : `应用「${preset.name}」视频特效`, prompt: preset.name, position: libraryInsertPoint ?? undefined, connectToAnchor: !libraryInsertPoint });
                  setLibraryRecent((items) => [preset.name, ...items.filter((item) => item !== preset.name)].slice(0, 20));
                  setLibraryInsertPoint(null);
                  setOverlay(null);
                  setNotice(`已添加「${preset.name}」节点`);
                }}>
                  <span className={`canvas-preset-preview preview-${index % 6}`}><Sparkles size={25} /><i>{preset.model}</i><div><button type="button" aria-label={libraryFavorites.has(preset.name) ? `取消收藏${preset.name}` : `收藏${preset.name}`} className={libraryFavorites.has(preset.name) ? "is-active" : ""} onClick={(event) => { event.stopPropagation(); setLibraryFavorites((items) => { const next = new Set(items); if (next.has(preset.name)) next.delete(preset.name); else next.add(preset.name); return next; }); }}><Star size={14} fill={libraryFavorites.has(preset.name) ? "currentColor" : "none"} /></button><button type="button" onClick={(event) => { event.stopPropagation(); setLibraryDetail(preset); }}>详情</button></div></span>
                  <b>{preset.name}</b><small><span>{preset.commercial ? "商用" : "非商用"}</span>{preset.author}<i />{preset.uses}</small>
                </article>)}</div> : <div className="canvas-preset-empty"><Search size={24} /><strong>没有找到相关素材</strong><span>换个分类或关键词试试</span></div>}
              </section>
              {libraryDetail && <div className="canvas-preset-detail" role="dialog" aria-label={`${libraryDetail.name}详情`}><button type="button" aria-label="关闭素材详情" onClick={() => setLibraryDetail(null)}><X size={16} /></button><div className="canvas-preset-detail-preview"><Sparkles size={42} /></div><section><small>{libraryDetail.model}</small><h3>{libraryDetail.name}</h3><p>由 {libraryDetail.author} 创作，可直接作为{overlay === "style-library" ? "图片风格参考" : "视频镜头特效"}添加到当前画布。</p><dl><div><dt>授权</dt><dd>{libraryDetail.commercial ? "支持商用" : "仅个人使用"}</dd></div><div><dt>使用次数</dt><dd>{libraryDetail.uses}</dd></div><div><dt>分类</dt><dd>{libraryDetail.category}</dd></div></dl><button type="button" onClick={() => { addWorkflowNode(overlay === "style-library" ? "image" : "video", { title: libraryDetail.name, description: `来自素材库 · ${libraryDetail.author}`, prompt: libraryDetail.name, position: libraryInsertPoint ?? undefined, connectToAnchor: !libraryInsertPoint }); setLibraryRecent((items) => [libraryDetail.name, ...items.filter((item) => item !== libraryDetail.name)]); setLibraryDetail(null); setLibraryInsertPoint(null); setOverlay(null); }}>添加到画布</button></section></div>}
            </div> : <div className="canvas-clear-data-body"><p>将从这台设备删除当前作品记录、画布快照和关联的本机素材。登录、主题、收藏、其他作品及云端项目不会受影响。</p><div><button type="button" onClick={() => setOverlay(null)}>取消</button><button type="button" className="is-danger" onClick={() => onClearLocalData(attachments.map((attachment) => attachment.id))}>清除本地数据</button></div></div>}
          </section>
        </div>
      )}

      <MembershipDialog open={membershipOpen} onClose={() => setMembershipOpen(false)} onPurchase={(label) => { setMembershipOpen(false); setNotice(`已选择${label}，支付服务接入后即可购买`); }} />

      {notice && <div className="canvas-toast" role="status">{notice}</div>}
    </main>
  );
}
