import {
  createContext,
  lazy,
  Suspense,
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
  BaseEdge,
  Background,
  BackgroundVariant,
  Handle,
  MarkerType,
  MiniMap,
  NodeToolbar,
  Panel,
  Position,
  ReactFlow,
  addEdge,
  getBezierPath,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Connection,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
  type ReactFlowInstance,
} from "@xyflow/react";
import {
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  ArrowUpDown,
  Blocks,
  BookOpen,
  Box,
  BriefcaseBusiness,
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
  Film,
  Filter,
  Folder,
  GripVertical,
  Hand,
  Headphones,
  ImagePlay,
  Info,
  Link2,
  Languages,
  Maximize2,
  Mic2,
  Minimize2,
  MoreHorizontal,
  MousePointer2,
  Music2,
  Paperclip,
  PencilLine,
  Play,
  Plus,
  QrCode,
  RotateCcw,
  Scissors,
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
  X,
  Zap,
} from "lucide-react";
import { BrandIcon } from "../../components/BrandIcon";
import { ComposerAssetPicker } from "../../components/ComposerAssetPicker";
import { LineIcon } from "../../components/LineIcon";
import { SelectMenu } from "../../components/SelectMenu";
import {
  RUNTIME_MODEL_MODALITIES,
  localCodexModelDefinitions,
  runtimeModelDefinitions,
} from "../../catalog/runtimeModels";
import type { ModelDefinition, ModelModality } from "../../catalog/types";
import { MembershipDialog } from "../account/MembershipDialog";
import {
  StandaloneSkillWorkflowOverlay,
  type StandaloneSkillRunRequest,
  type StandaloneWorkflowKind,
} from "./StandaloneSkillWorkflows";
import {
  APP_CANVAS_SKILL_IDS,
  canonicalAppSkillId,
  canonicalAppSkillPath,
  canonicalAppSkillText,
} from "./appSkillIds";
import {
  ScriptWorkflowOverlay as ControlledScriptWorkflowOverlay,
  type ScriptAssetBatchRequest,
  type ScriptAssetBatchResult,
  type ScriptAssetCanvasSelectRequest,
  type ScriptAssetGenerateRequest,
  type ScriptAssetGenerateResult,
  type ScriptAssetUploadRequest,
  type ScriptBatchVideoRequest,
  type ScriptPromptBatchRequest,
  type ScriptPromptBatchResult,
  type ScriptPromptComposeRequest,
  type ScriptPromptComposeResult,
  type ScriptWorkbenchCanvasImage,
  type ScriptWorkbenchImageOptions,
  type ScriptWorkbenchModelOption,
} from "./ScriptWorkflowOverlay";
import {
  SCRIPT_WORKBENCH_MODEL_JSON_INSTRUCTIONS,
  composeScriptWorkbenchPrompt,
  composeScriptWorkbenchVideoPrompt,
  deriveScriptWorkbenchSteps,
  hasDurableScriptWorkbenchByteVerification,
  hasRealScriptWorkbenchAssetSource,
  isScriptWorkbenchReadyForBatchVideo,
  normalizeScriptWorkbench,
  prepareScriptWorkbenchVideoJobs,
  parseScriptWorkbenchModelOutput,
  scriptWorkbenchSha256Bytes,
  scriptWorkbenchShotVideoJobId,
  serializeScriptWorkbench,
  extractScriptWorkbenchJson,
  updateScriptWorkbenchAsset,
  updateScriptWorkbenchJobStatus,
  validateScriptWorkbench,
  type ScriptWorkbenchAsset,
  type ScriptWorkbenchAssetPatch,
  type ScriptWorkbenchByteVerification,
  type ScriptWorkbenchDocument,
  type ScriptWorkbenchShot,
} from "./scriptWorkbenchModel";
import {
  TOOLBOX_CLASSICS,
  TOOLBOX_TEMPLATES,
  type ToolboxClassic,
  type ToolboxTemplate,
} from "./toolboxTemplates";
import { CreateSkillDialog, type CreateSkillFormValues } from "../skill-home/CreateSkillDialog";
import { SKILLS } from "../../catalog/skills";
import { createAgentGateway, probeLocalCodex, type AgentGateway } from "../../lib/agent";
import { discoverCanvasModels, generateCanvasContent, isCanvasGenerationError } from "../../lib/generation";
import {
  buildDirectorSceneFromPrompt,
  createDefaultDirectorScene,
  normalizeDirectorScene,
} from "./director/defaults";
import type {
  DirectorCamera,
  DirectorSceneState,
  DirectorShot,
} from "./director/types";
import {
  loadLocalCanvasDocument,
  saveCloudCanvasDocument,
  saveLocalCanvasDocument,
} from "../../lib/canvasState";
import { isCloudConfigured, persistWorkToCloud } from "../../lib/cloud";
import { localFile, registerLocalFiles, removeLocalFiles } from "../../lib/localFiles";
import { loadWork, saveWork } from "../../lib/work";
import type {
  AgentJob,
  AgentArtifact,
  CanvasDocument,
  CloudWorkState,
  CreationLine,
  DraftAttachment,
  PendingAttachment,
  WebWork,
  WorkCreationConfig,
  WorkExecutor,
} from "../../types";

const DirectorStudio = lazy(() => import("./director/DirectorStudio"));

type CanvasView = "workflow" | "storyboard";
type CanvasTool = "select" | "pan";
type DrawerKind = "add" | "tools" | "assets" | "characters" | "history" | "overview";
type AgentPanelTab = "conversation" | "skills" | "history" | "settings";
type OverlayKind = "shortcuts" | "tutorial" | "share" | "clear-data" | "style-library" | "effect-library";
type RailMenuKind = "move" | "help" | null;
type HelpPanelKind = "customer" | "sales" | "official" | null;
type SharePanelKind = "choices" | "link" | "publish";
type ComposerMenuKind = "assets" | "model" | "skill" | "mode" | null;
type HeaderMenuKind = "board" | "credits" | "profile" | null;
type AgentHeaderPopover = "history" | "share" | null;
type AssetSource = "personal" | "agent";
type AssetTag = "其它" | "人物" | "场景" | "物品" | "风格" | "音效";
type AssetManagerSource = "personal" | "kling";
type AssetManagerCategory = "全部" | AssetTag;
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
  line?: CreationLine;
  creator?: string;
  category?: string;
  guide?: string;
  steps?: string[];
  useCases?: string[];
};
type WorkflowNodeKind = "text" | "script" | "image" | "audio" | "video" | "compose";
type WorkflowNodeStatus = "idle" | "ready" | "running" | "done" | "failed";
type WorkflowNodeVariant = "default" | "libtv-source" | "libtv-generator" | "director" | "script-new" | "script-legacy" | "script-workflow" | "character-workflow" | "first-frame-video-workflow" | "audio-video-workflow";
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
  resultText?: string;
  resultAttachmentId?: string;
  resultMimeType?: string;
  generatedFromPrompt?: string;
  generatedWithModel?: string;
  generationProgress?: number;
  generationError?: string;
  generationRequestId?: string;
  sourceNodeId?: string;
  sourceContext?: string;
  directorScene?: DirectorSceneState;
  scriptWorkbench?: ScriptWorkbenchDocument;
} & Record<string, unknown>;

type WorkflowNode = Node<WorkflowNodeData, "workflow-node">;

type CanvasStarterPreset = {
  id: "story-script" | "character-turnaround" | "first-frame-video" | "audio-video";
  title: string;
  skill: string;
  skillPath: string;
  cover: string;
  nodes: Array<{
    kind: WorkflowNodeKind;
    title: string;
    description: string;
    variant?: WorkflowNodeVariant;
    data?: Partial<WorkflowNodeData>;
  }>;
};

type CanvasNodeActions = {
  update: (nodeId: string, patch: Partial<WorkflowNodeData>) => void;
  run: (nodeId: string) => void;
  cancel: (nodeId: string) => void;
  derive: (nodeId: string, kind: WorkflowNodeKind, variant?: WorkflowNodeVariant) => void;
  resolveAttachment: (attachmentId: string) => Promise<File | undefined>;
  quickAction: (nodeId: string, action: string) => void;
  openDirector: (nodeId: string, options?: { reference?: boolean; runPrompt?: boolean }) => void;
  openScript: (nodeId: string) => void;
  scriptAction: (nodeId: string, action: "regenerate" | "storyboard" | "video" | "download") => void;
  openStandalone: (nodeId: string, workflow: StandaloneWorkflowKind) => void;
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
  | "asset-manager"
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
  | "minimap"
  | "move"
  | "panel"
  | "script"
  | "share"
  | "send"
  | "sparkle"
  | "shortcut"
  | "snap"
  | "text"
  | "tools"
  | "tidy"
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

const CANVAS_SHORTCUT_GROUPS = [
  { title: "创作", items: [["成组", "G"], ["合并分镜组", "⌥ G"], ["解组", "⇧ G"], ["连线", "L"], ["复制节点和连线", "D"], ["生成", "Enter"], ["新建节点", "Tab"], ["节点复制", "Option + 拖动节点"], ["创建副本", "Option + 拖动"]] },
  { title: "缩放", items: [["放大", "⌘ +"], ["缩小", "⌘ −"], ["适应画布", "0"], ["触控板", "双指缩放"], ["鼠标", "滚轮"]] },
  { title: "移动画布", items: [["键盘", "Space"], ["触控板", "双指移动"], ["鼠标", "中键拖动"], ["移动", "V"], ["抓手工具", "H"], ["整理画布", "⌥ ⇧ F"]] },
  { title: "其他", items: [["撤销", "⌘ Z"], ["重做", "⇧ ⌘ Z"], ["删除", "⌫"]] },
] as const;

const stylePreset = (name: string, author: string, uses: string, category = "推荐", model = "Lib Image", commercial = true): PresetDefinition => ({ name, author, uses, category, model, commercial });
const effectPreset = (name: string, author: string, uses: string): PresetDefinition => ({ name, author, uses, category: "推荐", model: "Lib Video 2.0", commercial: true });

// Snapshot of the public catalog cards visible in LibTV on 2026-08-04. Keeping
// the metadata local avoids coupling the canvas to another product's login.
const STYLE_PRESETS: PresetDefinition[] = [
  stylePreset("复古马卡龙", "AI搬砖侠", "359"),
  stylePreset("新中式", "AI搬砖侠", "445", "风格插画"),
  stylePreset("岁月港风", "消息免打扰", "367", "摄影写真"),
  stylePreset("新国韵", "AI萨大法官", "465", "动漫游戏"),
  stylePreset("清风竹林", "消息免打扰", "108", "风格插画"),
  stylePreset("小岛微风", "捏捏AI", "872", "摄影写真", "Midjourney V7"),
  stylePreset("慢门胶片", "vibe fckuing", "274", "摄影写真"),
  stylePreset("曜黑幻境", "鱿鱼chill", "799", "动漫游戏", "Midjourney Niji 7"),
  stylePreset("霸王戏梦", "大葱同学", "171", "风格插画"),
  stylePreset("双重梦境", "孤雌的白日梦", "140", "创意玩法"),
  stylePreset("古风侠影", "管夯工作台", "439", "动漫游戏"),
  stylePreset("莫奈花园", "可可大王", "251", "风格插画"),
  stylePreset("富士之夏", "可可大王", "550", "风格插画"),
  stylePreset("云海", "AI萨大法官", "262", "风格插画", "Midjourney Niji 7"),
  stylePreset("曼岛日落", "大葱同学", "206", "摄影写真"),
  stylePreset("虹光柔映", "江户川阿伟", "116", "风格插画"),
  stylePreset("复古港风", "江户川阿伟", "170", "摄影写真"),
  stylePreset("江湖旧梦", "大葱同学", "574", "动漫游戏"),
  stylePreset("潜梦迷离", "鱿鱼chill", "95", "风格插画"),
  stylePreset("青山", "江户川阿伟", "202", "摄影写真"),
  stylePreset("毛绒织梦", "孤雌的白日梦", "99", "创意玩法", "Midjourney V7"),
  stylePreset("梦核赛博", "AI搬砖侠", "300", "动漫游戏"),
  stylePreset("35MM", "没有工作的天", "346", "摄影写真"),
  stylePreset("赛博蝉鸣", "捏捏AI", "91", "动漫游戏", "Midjourney Niji 7"),
  stylePreset("尼斯的海", "汪往旺", "308", "摄影写真"),
  stylePreset("落日蓝调", "AI萨大法官", "298", "摄影写真"),
  stylePreset("美式卡通", "消息免打扰", "449", "动漫游戏"),
  stylePreset("午夜柔光", "管夯工作台", "118", "摄影写真"),
  stylePreset("银翼梦境", "AI搬砖侠", "273", "动漫游戏"),
  stylePreset("加州旷野", "孤雌的白日梦", "230", "摄影写真"),
  stylePreset("暮紫流年", "凌晨四点实验室", "142", "摄影写真"),
  stylePreset("苍翠低语", "鱿鱼chill", "246", "摄影写真"),
  stylePreset("琉璃幻梦", "omom", "123", "风格插画"),
  stylePreset("寂色朱砂", "可可大王", "72", "摄影写真"),
  stylePreset("90s Film", "苏打绿豆", "79", "摄影写真"),
  stylePreset("粉雾幻境", "vibe fckuing", "166", "摄影写真"),
  stylePreset("墨染幽玄", "消息免打扰", "76", "风格插画"),
  stylePreset("幽梦绮章", "管夯工作台", "148", "风格插画"),
  stylePreset("霓虹小怪兽", "没有工作的天", "77", "动漫游戏"),
  stylePreset("英姿墨彩", "消息免打扰", "136", "风格插画"),
  stylePreset("睡莲晨曦", "大葱同学", "61", "风格插画"),
  stylePreset("麦田黄昏", "苏打绿豆", "41", "摄影写真"),
  stylePreset("黑白极境", "omom", "90", "摄影写真"),
  stylePreset("霓虹残影", "汪往旺", "51", "动漫游戏", "Midjourney Niji 7"),
  stylePreset("怪诞漫画", "vibe fckuing", "118", "动漫游戏"),
  stylePreset("糖衣奇点", "管夯工作台", "67", "创意玩法"),
  stylePreset("8bit", "凌晨四点实验室", "19", "动漫游戏"),
  stylePreset("濑户晴空", "苏打绿豆", "43", "摄影写真"),
  stylePreset("粘土动画", "捏捏AI", "78", "创意玩法"),
  stylePreset("毛毡风", "AI萨大法官", "76", "创意玩法"),
  stylePreset("城市巨人", "vibe fckuing", "542", "创意玩法"),
  stylePreset("巨物奇观", "管夯工作台", "167", "创意玩法"),
  stylePreset("暗光产品", "江户川阿伟", "827", "电商营销"),
  stylePreset("亮调产品", "没有工作的天", "623", "电商营销"),
  stylePreset("原生相机", "孤雌的白日梦", "1500", "摄影写真"),
  stylePreset("CCD风", "AI搬砖侠", "319", "摄影写真"),
  stylePreset("古早dv风", "大葱同学", "150", "摄影写真"),
  stylePreset("J_漫剧素材三视图+大头表情+姿势图", "JM32", "3700", "动漫游戏"),
  stylePreset("Qwen-Image手写文艺艺术字体", "万俊平", "7900", "平面设计", "Qwen Image"),
  stylePreset("漫剧仿真人配角大全【三视图展示】AI短片素人群像", "斑斓和绿荫", "8000", "动漫游戏", "Qwen Image"),
  stylePreset("【摸鱼】3D电商渲染级KV海报_创意视觉表达", "大摸鱼家_Xr", "21.1w", "电商营销", "Qwen Image"),
  stylePreset("东方玄幻武侠修仙世界", "重楼IP视觉", "13.1w", "动漫游戏", "Qwen Image"),
  stylePreset("【摸鱼】创意电商场景_电商产品场景", "大摸鱼家_Xr", "22.4w", "电商营销", "Qwen Image"),
  stylePreset("一键电商产品详情页长图全案｜高转化策划案", "Dave", "1.1w", "电商营销"),
  stylePreset("1912.5D写实人像", "191", "6.6w", "摄影写真"),
  stylePreset("Qwen-Image-Lightning-8steps-V1.1-bf16.safetensors", "87", "59.5w", "创意玩法", "Qwen Image", false),
  stylePreset("Qwen-暗黑哥特风格情侣头像插画", "sonnet", "5.1w", "动漫游戏", "Qwen Image"),
  stylePreset("Qwen-Image-Lightning-8steps-V2.0", "87", "30.4w", "创意玩法", "Qwen Image", false),
  stylePreset("XT日系半厚涂", "夏不吃兔", "3.2w", "风格插画", "Qwen Image", false),
  stylePreset("分镜脚本故事版分镜", "YOUS", "1200", "小说推文"),
  stylePreset("ZOZ_厚涂插画", "之O周", "9.0w", "风格插画", "Qwen Image"),
  stylePreset("【Dave】清新文艺手写字体｜专辑｜影视｜音乐｜综艺｜Logo等海报标题（♥中文控制）书法艺术创意字", "Dave", "13.1w", "平面设计", "Qwen Image"),
  stylePreset("XT古风插画奇幻少女", "夏不吃兔", "6.8w", "风格插画", "Qwen Image"),
  stylePreset("CG动漫角色-Qwen", "尘恢", "10.4w", "动漫游戏", "Qwen Image"),
  stylePreset("破界.玄光极速版 Z-image +qwen", "刀忑", "4.8w", "创意玩法"),
  stylePreset("一键生成人物多视图", "像素农夫DESIGN", "5700", "动漫游戏"),
  stylePreset("豪华公寓.", "奇幻设计", "9.8w", "建筑及室内设计", "Qwen Image"),
  stylePreset("03_Ai艺画室_都市写实Z-image-lora", "长青诗", "5.0w", "摄影写真", "Z Image"),
  stylePreset("Qwen-image-南音浅浅-小红书爆女生立绘02", "南音浅浅", "6.0w", "动漫游戏", "Qwen Image"),
  stylePreset("Qwen-Image字体设计宋体字体设计", "万俊平", "4.2w", "平面设计", "Qwen Image"),
];
const EFFECT_PRESETS: PresetDefinition[] = [
  effectPreset("小蜜蜂运镜", "vibe fckuing", "1900"),
  effectPreset("穿云而入", "管夯工作台", "952"),
  effectPreset("飞跃地平线", "vibe fckuing", "1600"),
  effectPreset("逆转引力", "omom", "341"),
  effectPreset("地球缩放", "孤雌的白日梦", "298"),
  effectPreset("环球缩放", "苏打绿豆", "313"),
  effectPreset("瞳孔推镜", "消息免打扰", "668"),
  effectPreset("俯冲地球", "没有工作的天", "429"),
  effectPreset("产品扫光", "鱿鱼chill", "1600"),
  effectPreset("普拉达换装", "omom", "91"),
  effectPreset("多角度定点", "AI萨大法官", "955"),
  effectPreset("水下慢镜头", "AI萨大法官", "396"),
  effectPreset("试妆特写", "捏捏AI", "131"),
  effectPreset("悬浮缓入", "捏捏AI", "273"),
  effectPreset("微距推镜", "可可大王", "430"),
  effectPreset("直升机揭幕", "汪往旺", "114"),
  effectPreset("山路追击", "AI萨大法官", "303"),
  effectPreset("雪地赛车", "可可大王", "191"),
  effectPreset("City Drive", "捏捏AI", "136"),
  effectPreset("3D解构", "大葱同学", "511"),
  effectPreset("面部环拍", "苏打绿豆", "299"),
  effectPreset("Showroom", "可可大王", "104"),
  effectPreset("饰品特写", "江户川阿伟", "87"),
  effectPreset("巨人俯瞰", "大葱同学", "152"),
  effectPreset("Runway", "AI搬砖侠", "110"),
  effectPreset("AI 编舞", "苏打绿豆", "669"),
  effectPreset("机械姬", "汪往旺", "201"),
  effectPreset("巨星名场面", "管夯工作台", "121"),
  effectPreset("镜面分身", "vibe fckuing", "82"),
  effectPreset("瞳孔异变", "孤雌的白日梦", "76"),
  effectPreset("红毯闪光灯", "汪往旺", "124"),
  effectPreset("赛博化妆师", "AI搬砖侠", "32"),
  effectPreset("星云漩涡", "没有工作的天", "258"),
  effectPreset("控雨术", "AI搬砖侠", "73"),
  effectPreset("燃烧开场", "大葱同学", "92"),
  effectPreset("全景相机", "消息免打扰", "56"),
  effectPreset("星尘降临", "管夯工作台", "220"),
  effectPreset("涡轮运镜", "江户川阿伟", "182"),
  effectPreset("流光展翼", "vibe fckuing", "53"),
  effectPreset("机甲变身", "凌晨四点实验室", "186"),
  effectPreset("升格爆炸", "孤雌的白日梦", "191"),
  effectPreset("子弹时间", "汪往旺", "452"),
  effectPreset("反派登场", "江户川阿伟", "267"),
  effectPreset("双人对打", "AI萨大法官", "540"),
  effectPreset("升格KO", "管夯工作台", "201"),
  effectPreset("驯龙高手", "鱿鱼chill", "158"),
  effectPreset("深海巨兽", "AI搬砖侠", "105"),
  effectPreset("飞鸟解体", "没有工作的天", "207"),
];
const PRESET_CATEGORIES = ["推荐", "Midjourney", "摄影写真", "电商营销", "动漫游戏", "风格插画", "平面设计", "建筑及室内设计", "创意玩法", "文创周边", "小说推文"];
const STYLE_MODEL_FILTERS = ["全部", "Lib Image", "Midjourney V7", "Midjourney Niji 7", "Midjourney V8.1", "General image Pro", "General image V2", "Qwen Image", "Qwen Image Edit", "Z Image", "Seedream 4.5", "Seedream 5.0"];
const EFFECT_MODEL_FILTERS = ["全部", "Lib Video 2.0"];

function nodeRuntimeDefaults(kind: WorkflowNodeKind, variant: WorkflowNodeVariant = "default"): Partial<WorkflowNodeData> {
  if (kind === "image") return { prompt: "", model: variant === "libtv-generator" ? "gpt-image-2" : "Lib Image", imageMode: "文生图", aspectRatio: "16:9", quality: "标准画质", resolution: "2K", outputCount: 1 };
  if (kind === "video") return { prompt: "", model: "2.0", videoMode: "文生视频", aspectRatio: "16:9", resolution: "720P", duration: 5, outputCount: 1, webSearch: true, autoValidate: true };
  if (kind === "audio") return { prompt: "", model: "Minimax-speech-2.8-hd", voice: "少女音色", speed: 1, tone: 0, volume: 1, timbrePitch: 0, timbreIntensity: 0, timbre: 0, audioEffect: "无" };
  if (kind === "script") return {
    prompt: "",
    model: variant === "director" ? "Director 3D" : variant === "script-new" ? "gpt-5.6-terra" : "GVLM 3.1",
    variant,
    ...(variant === "director" ? { directorScene: createDefaultDirectorScene() } : {}),
  };
  if (kind === "text") return { prompt: "", model: variant === "libtv-generator" ? "gpt-5.6-terra" : "GVLM 3.1" };
  return {};
}

const GENERATOR_MODEL_OPTIONS = {
  text: [
    { id: "gpt-5.6-terra", label: "GPT-5.6 Terra" },
    { id: "gpt-5.6-sol", label: "GPT-5.6 Sol" },
    { id: "gpt-5.6-luna", label: "GPT-5.6 Luna" },
    { id: "gpt-5.4-mini", label: "GPT-5.4 Mini" },
  ],
  image: [
    { id: "gpt-image-2", label: "GPT Image 2" },
    { id: "gpt-image-1.5", label: "GPT Image 1.5" },
  ],
} as const;
const MAX_GENERATED_IMAGE_BYTES = 25 * 1024 * 1024;
const MAX_AGENT_ARTIFACT_BYTES = 512 * 1024 * 1024;

function artifactMimeType(artifact: AgentArtifact): string {
  if (artifact.mimeType) return artifact.mimeType;
  if (artifact.kind === "image") return "image/png";
  if (artifact.kind === "video") return "video/mp4";
  if (artifact.kind === "audio") return "audio/mpeg";
  return "text/markdown";
}

async function agentArtifactFile(artifact: AgentArtifact): Promise<File | null> {
  if (artifact.file) return artifact.file;
  const mimeType = artifactMimeType(artifact);
  let blob: Blob;
  if (artifact.base64) {
    if (artifact.base64.length > Math.ceil(MAX_AGENT_ARTIFACT_BYTES * 4 / 3) || !/^[a-zA-Z0-9+/]+={0,2}$/.test(artifact.base64)) return null;
    const binary = window.atob(artifact.base64);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    blob = new Blob([bytes], { type: mimeType });
  } else if (artifact.url) {
    let parsed: URL;
    try {
      parsed = new URL(artifact.url, window.location.href);
    } catch {
      return null;
    }
    if (!['http:', 'https:'].includes(parsed.protocol)) return null;
    const response = await fetch(parsed, { credentials: "omit", redirect: "error" });
    if (!response.ok) return null;
    blob = await response.blob();
  } else {
    return null;
  }
  if (!blob.size || blob.size > MAX_AGENT_ARTIFACT_BYTES) return null;
  return new File([blob], artifact.name, { type: mimeType, lastModified: Date.now() });
}

function generatorModelLabel(modelId: string) {
  return [...GENERATOR_MODEL_OPTIONS.text, ...GENERATOR_MODEL_OPTIONS.image].find((model) => model.id === modelId)?.label ?? modelId;
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

const AGENT_SKILL_LIBRARY: CanvasLibrarySkill[] = SKILLS.map((skill) => ({
  id: skill.id,
  title: skill.title,
  slug: `/${skill.skill}`,
  description: skill.description,
  line: skill.line,
  creator: skill.creator,
  category: skill.category,
  guide: skill.guide,
  steps: skill.steps,
  useCases: skill.useCases,
}));

const CANVAS_MODALITY_LABELS: Record<ModelModality, string> = {
  text: "文字",
  image: "图片",
  video: "视频",
  audio: "音频",
};

function loadCanvasFavoriteSkills() {
  try {
    const stored = JSON.parse(localStorage.getItem("anime-armory.web.favorite-skills") ?? "[]") as unknown;
    if (!Array.isArray(stored)) return new Set<string>();
    return new Set<string>(stored.flatMap((value) => {
      const canonical = typeof value === "string" ? canonicalAppSkillId(value) : null;
      return canonical ? [canonical] : [];
    }));
  } catch {
    return new Set<string>();
  }
}

const AGENT_SKILL_BATCHES = Array.from(
  { length: Math.max(1, Math.ceil(AGENT_SKILL_LIBRARY.length / 4)) },
  (_, batchIndex) => Array.from(
    { length: Math.min(4, AGENT_SKILL_LIBRARY.length) },
    (_, itemIndex) => AGENT_SKILL_LIBRARY[(batchIndex * 4 + itemIndex) % AGENT_SKILL_LIBRARY.length],
  ),
);

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
  { id: "fresh-girl", name: "甜妹/清新少女", detail: "女主 · 女 · 现代 · 青年 · 温柔" },
  { id: "ceo", name: "霸总/精英大佬", detail: "男主 · 男 · 现代 · 青年 · 冷峻" },
  { id: "gentleman", name: "温柔熟男/理想男友", detail: "男主 · 男 · 现代 · 成熟 · 温柔" },
  { id: "heiress", name: "清冷千金/白切黑女主", detail: "女主 · 女 · 现代 · 青年 · 清冷" },
  { id: "ancient-man", name: "古风男主", detail: "男主 · 古风 · 青年 · 英气" },
  { id: "ancient-woman", name: "古风女主", detail: "女主 · 古风 · 青年 · 清雅" },
  { id: "villainess", name: "恶毒女配/白莲花", detail: "女配 · 女 · 现代 · 反派 · 明艳" },
  { id: "father", name: "正派长辈/父", detail: "长辈 · 男 · 现代 · 稳重 · 正派" },
  { id: "mother", name: "正派长辈/母", detail: "长辈 · 女 · 现代 · 温和 · 正派" },
  { id: "relative", name: "反派长辈/势利亲戚", detail: "长辈 · 现代 · 反派 · 强势" },
  { id: "ordinary", name: "生活方式普通人", detail: "配角 · 现代 · 自然 · 生活感" },
  { id: "asian-man", name: "时尚感亚洲男生", detail: "男 · 现代 · 青年 · 时尚 · 都市" },
  { id: "asian-woman", name: "时尚感亚洲女生", detail: "女 · 现代 · 青年 · 时尚 · 都市" },
  { id: "western-man", name: "时尚感欧美男生", detail: "男 · 欧美 · 青年 · 时尚 · 都市" },
  { id: "western-woman", name: "时尚感欧美女生", detail: "女 · 欧美 · 青年 · 时尚 · 都市" },
  { id: "boy", name: "小男孩", detail: "男 · 现代 · 儿童 · 活泼 · 自然" },
  { id: "girl", name: "小女孩", detail: "女 · 现代 · 儿童 · 灵动 · 自然" },
  { id: "asian-woman-cool", name: "时尚感亚洲女生", detail: "女 · 现代 · 青年 · 清冷 · 高级" },
  { id: "asian-man-casual", name: "时尚感亚洲男生", detail: "男 · 现代 · 青年 · 休闲 · 阳光" },
  { id: "western-woman-editorial", name: "时尚感欧美女生", detail: "女 · 欧美 · 青年 · 编辑感 · 高级" },
];

function Icon({ name }: { name: IconName }) {
  let content: ReactNode;
  let viewBox = "0 0 24 24";
  switch (name) {
    case "add": viewBox = "0 0 17 17"; content = <path d="M8.5 0c.5 0 .9.48.9 1.06V7.6h6.54c.58 0 1.06.4 1.06.9s-.48.9-1.06.9H9.4v6.54c0 .58-.4 1.06-.9 1.06s-.9-.48-.9-1.06V9.4H1.06C.48 9.4 0 9 0 8.5s.48-.9 1.06-.9H7.6V1.06C7.6.48 8 0 8.5 0" fill="currentColor" stroke="none" />; break;
    case "move": viewBox = "0 0 16 16"; content = <g transform="translate(.39 .395)"><path d="M.09 1.94A1.45 1.45 0 0 1 1.94.09l12.3 4.4c1.25.45 1.31 2.19.1 2.71l-.21.1a13 13 0 0 0-6.84 6.83l-.09.2a1.46 1.46 0 0 1-2.7-.08zm1.41-.63a.15.15 0 0 0-.19.2l4.4 12.3c.05.14.24.14.3.01l.1-.2a14.4 14.4 0 0 1 7.5-7.52l.21-.09a.16.16 0 0 0 0-.3z" fill="currentColor" stroke="none" /></g>; break;
    case "tools": viewBox = "0 0 17.97 17.97"; content = <path d="M15.65 0a2.3 2.3 0 0 1 2.32 2.32v1.66a2.3 2.3 0 0 1-2.32 2.32h-1.67a2.3 2.3 0 0 1-2.23-1.72l-.27.05H9.82q-.14.01-.15.04-.02 0-.04.15v8.33q.01.14.04.14 0 .03.15.04h1.66q.15 0 .27.06a2.3 2.3 0 0 1 2.23-1.72h1.67a2.3 2.3 0 0 1 2.32 2.31v1.67a2.3 2.3 0 0 1-2.32 2.32h-1.67a2.3 2.3 0 0 1-2.31-2.32V14.6l-.19.03H9.82q-.62 0-1.07-.42a1.5 1.5 0 0 1-.42-1.06V9.63H6.48L6.3 9.6v.22a2.3 2.3 0 0 1-2.32 2.31H2.32A2.3 2.3 0 0 1 0 9.82V8.15a2.3 2.3 0 0 1 2.32-2.32h1.66A2.3 2.3 0 0 1 6.3 8.15v.21l.18-.03h1.85V4.82q0-.62.42-1.07.45-.42 1.07-.42h1.66q.1 0 .19.03V2.32A2.3 2.3 0 0 1 13.98 0zm-1.67 12.97a1 1 0 0 0-1.01 1.01v1.67c0 .56.45 1.02 1.01 1.02h1.67c.56 0 1.02-.46 1.02-1.02v-1.67c0-.56-.46-1.01-1.02-1.01zM2.32 7.13c-.56 0-1.02.46-1.02 1.02v1.67c0 .56.46 1.01 1.02 1.01h1.66c.56 0 1.02-.45 1.02-1.01V8.15c0-.56-.46-1.02-1.02-1.02zM13.98 1.3c-.56 0-1.01.46-1.01 1.02v1.66c0 .56.45 1.02 1.01 1.02h1.67c.56 0 1.02-.46 1.02-1.02V2.32c0-.56-.46-1.02-1.02-1.02z" fill="currentColor" stroke="none" />; break;
    case "assets": viewBox = "0 0 16.61 16.36"; content = <path d="M8.97.75c.55-.8 1.64-1 2.43-.43l4.5 3.24c.73.54.93 1.55.44 2.32l-3 4.7-.1.14 2.14 4.71c.2.44-.12.93-.6.93h-9.1a.65.65 0 0 1-.6-.92l.9-1.98a4.74 4.74 0 1 1-1.22-9.34q.92 0 1.72.32l.07-.13zM6.68 15.06h7.1l-3.55-7.81zM4.76 5.42a3.45 3.45 0 1 0 2.03 6.25l1.42-3.13v-.02a3.46 3.46 0 0 0-3.45-3.1m5.88-4.04a.4.4 0 0 0-.6.1l-2.4 3.57-.02.01q.9.67 1.42 1.69l.6-1.34.05-.08a.65.65 0 0 1 1.14.08l1.78 3.92 2.64-4.15a.4.4 0 0 0-.1-.56z" fill="currentColor" stroke="none" />; break;
    case "character": viewBox = "0 0 18.17 16.5"; content = <path d="M13.25 10A3.25 3.25 0 1 1 10 13.25a.92.92 0 0 0-1.83 0v.17a3.25 3.25 0 1 1-.6-2.05 2.4 2.4 0 0 1 3.03 0A3.3 3.3 0 0 1 13.25 10m-8.33 1.5a1.75 1.75 0 1 0 0 3.5 1.75 1.75 0 0 0 0-3.5m8.33 0c-.9 0-1.65.69-1.74 1.57v.36a1.75 1.75 0 1 0 1.74-1.93M11.52 0a2.4 2.4 0 0 1 2.3 1.5l.05.12v.02l1.6 5.03h1.95a.75.75 0 0 1 0 1.5H.75a.75.75 0 1 1 0-1.5h1.93l1.16-4.08A2.4 2.4 0 0 1 6.17.83h2.91q.21 0 .4-.09l1.06-.5q.46-.22.98-.24m.04 1.5a1 1 0 0 0-.37.09l-1.06.5q-.44.21-.91.24H6.17a.9.9 0 0 0-.88.67L4.23 6.67h9.65l-1.44-4.55-.04-.1a.9.9 0 0 0-.85-.52" fill="currentColor" stroke="none" />; break;
    case "history": viewBox = "0 0 17 17"; content = <path d="M8.5 0a8.5 8.5 0 1 1 0 17 8.5 8.5 0 0 1 0-17m0 1.32a7.18 7.18 0 1 0 0 14.37 7.18 7.18 0 0 0 0-14.37M8.2 4.1c.36 0 .65.3.65.66v3.42q0 .2.15.48.13.21.26.32l.08.06 2.59 1.54a.66.66 0 0 1-.68 1.14l-2.58-1.54a2.4 2.4 0 0 1-.81-.86 2.4 2.4 0 0 1-.33-1.14V4.76c0-.37.3-.66.66-.66" fill="currentColor" stroke="none" />; break;
    case "shortcut": viewBox = "0 0 16 16"; content = <g transform="translate(0 1.4706) scale(.880572)"><path d="M15.75 0a2.4 2.4 0 0 1 2.42 2.42v10a2.4 2.4 0 0 1-2.42 2.41H2.42A2.4 2.4 0 0 1 0 12.42v-10A2.4 2.4 0 0 1 2.42 0zM2.42 1.5c-.5 0-.92.41-.92.92v10c0 .5.41.91.92.91h13.33c.5 0 .92-.4.92-.91v-10c0-.5-.41-.92-.92-.92zM13.25 10a.75.75 0 0 1 0 1.5H4.92a.75.75 0 0 1 0-1.5zm-7.5-3.33a.75.75 0 0 1 0 1.5.75.75 0 1 1 0-1.5m3.34 0a.75.75 0 1 1 0 1.5.75.75 0 1 1 0-1.5m3.34 0a.75.75 0 0 1 0 1.5h-.01a.75.75 0 0 1 0-1.5M4.09 3.33a.75.75 0 0 1 0 1.5.75.75 0 0 1 0-1.5m3.34 0a.75.75 0 0 1 0 1.5h-.01a.75.75 0 0 1 0-1.5m3.33 0a.75.75 0 0 1 0 1.5.75.75 0 0 1 0-1.5m3.33 0a.75.75 0 0 1 0 1.5.75.75 0 0 1 0-1.5" fill="currentColor" stroke="none" /></g>; break;
    case "tutorial": viewBox = "0 0 17 17"; content = <path d="M8.5 0a8.5 8.5 0 1 1 0 17 8.5 8.5 0 0 1 0-17m0 1.3a7.2 7.2 0 1 0 0 14.4 7.2 7.2 0 0 0 0-14.4m.97 12.22h-1.3v-1.3h1.3zM8.6 3.6c.91 0 1.6.35 2.14.85.57.52.84 1.24.84 2.07q-.01.97-.56 1.7l-.01.02-.01.01q-.24.28-.98.94H10q-.3.27-.39.45v.02q-.18.28-.17.5v1.1h-1.3v-1.1c0-.45.16-.85.34-1.16q.24-.42.67-.79.71-.64.83-.78.29-.37.29-.91-.02-.78-.42-1.12c-.34-.31-.72-.5-1.26-.5-.63 0-1.13.25-1.46.6v.01c-.32.33-.5.79-.5 1.46h-1.3q-.01-1.3.74-2.23l.11-.12A3.2 3.2 0 0 1 8.6 3.61" fill="currentColor" stroke="none" />; break;
    case "workflow": content = <><rect x="3" y="4" width="6" height="5" rx="1" /><rect x="15" y="15" width="6" height="5" rx="1" /><path d="M9 6.5h4a4 4 0 0 1 4 4V15" /></>; break;
    case "text": content = <><rect x="5" y="3" width="14" height="18" rx="2" /><path d="M8.5 8h7M8.5 12h7M8.5 16h5" /></>; break;
    case "script": content = <><path d="M6 3h9l3 3v15H6zM15 3v4h4M9 11h6M9 15h6" /></>; break;
    case "image": content = <><rect x="3.5" y="4" width="17" height="16" rx="2" /><circle cx="9" cy="9" r="1.5" /><path d="m5 18 5-5 3 3 2-2 4 4" /></>; break;
    case "audio": content = <><path d="M9 18V6l9-2v12" /><circle cx="6" cy="18" r="3" /><circle cx="15" cy="16" r="3" /></>; break;
    case "video": content = <><rect x="3" y="5" width="14" height="14" rx="2" /><path d="m17 10 4-2v8l-4-2ZM9 9l4 3-4 3z" /></>; break;
    case "compose": content = <><rect x="4" y="4" width="11" height="11" rx="2" /><path d="M9 9h11v11H9z" /></>; break;
    case "copy": content = <><rect x="8" y="8" width="11" height="11" rx="2" /><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3" /></>; break;
    case "download": content = <><path d="M12 4v11m0 0 4-4m-4 4-4-4" /><path d="M5 18v2h14v-2" /></>; break;
    case "asset-manager": content = <path d="M12 5v16m8.001-2A2 2 0 0 0 22 17V5a2 2 0 0 0-1.999-2L16 3.002A5 5 0 0 0 12 5a5 5 0 0 0-4-2H4a2 2 0 0 0-2 2v12a2 2 0 0 0 1.999 2H8a5 5 0 0 1 4 2a5 5 0 0 1 4-2z" />; break;
    case "tidy": viewBox = "0 0 16 16"; content = <g transform="translate(1 1)"><path d="M5.13 8.34c.87 0 1.58.7 1.58 1.57v1.58c0 .87-.7 1.57-1.58 1.57H2.51c-.87 0-1.58-.7-1.58-1.57V9.9c0-.87.7-1.57 1.58-1.57zm6.36-2.1c.87 0 1.58.7 1.58 1.57v3.68c0 .87-.7 1.57-1.58 1.57H8.87c-.87 0-1.58-.7-1.58-1.57V7.8c0-.87.7-1.57 1.58-1.57zM2.46 9.39a.53.53 0 0 0-.48.52v1.58c0 .27.21.5.48.52h2.73a.5.5 0 0 0 .47-.52V9.9c0-.27-.2-.5-.47-.52zm6.4-2.1a.5.5 0 0 0-.52.52v3.73c.03.25.23.45.47.47h2.74a.5.5 0 0 0 .46-.47V7.81a.53.53 0 0 0-.52-.52zM5.14.93c.87 0 1.58.7 1.58 1.57v3.68c0 .87-.7 1.57-1.58 1.57H2.51c-.87 0-1.58-.7-1.58-1.57V2.5c0-.86.7-1.57 1.58-1.57zM2.46 1.98a.53.53 0 0 0-.48.52v3.73c.03.25.23.45.48.47h2.73a.5.5 0 0 0 .47-.47V2.5c0-.27-.2-.5-.47-.52zM11.49.93c.87 0 1.58.7 1.58 1.57v1.58c0 .87-.7 1.57-1.58 1.57H8.87c-.87 0-1.58-.7-1.58-1.57V2.5c0-.86.7-1.57 1.58-1.57zM8.87 1.98a.53.53 0 0 0-.53.52v1.63c.03.27.26.47.53.47h2.62c.27 0 .5-.2.52-.47V2.5a.53.53 0 0 0-.52-.52z" fill="currentColor" stroke="none" /></g>; break;
    case "minimap": viewBox = "0 0 21.8 21.8"; content = <path d="M10.9 0a6.9 6.9 0 0 1 6.9 6.9l-.01.4a10 10 0 0 1-1.82 4.7h1.93a1.9 1.9 0 0 1 1.8 1.3l2 6 .06.22a1.9 1.9 0 0 1-1.64 2.27l-.22.01h-18a1.9 1.9 0 0 1-1.8-2.5l2-6 .06-.14A1.9 1.9 0 0 1 3.9 12h1.93A10 10 0 0 1 4 7.3v-.4A6.9 6.9 0 0 1 10.9 0M3.87 13.8l-.02.02-.04.05-2 6a.1.1 0 0 0 0 .09l.04.03.05.01h18a.1.1 0 0 0 .08-.04l.02-.05v-.04l-2-6-.04-.05-.06-.02h-3.3a27 27 0 0 1-2.55 2.61 1.9 1.9 0 0 1-2.36-.04c-.6-.54-1.54-1.44-2.5-2.57zm7.03-12a5.1 5.1 0 0 0-5.1 5.1c0 1.51.83 3.18 1.95 4.7A24 24 0 0 0 10.9 15l.05-.01a24 24 0 0 0 3.1-3.38C15.17 10.08 16 8.4 16 6.9a5.1 5.1 0 0 0-5.1-5.1m0 2.2a2.9 2.9 0 1 1 0 5.8 2.9 2.9 0 0 1 0-5.8m0 1.8a1.1 1.1 0 1 0 0 2.2 1.1 1.1 0 0 0 0-2.2" fill="currentColor" stroke="none" />; break;
    case "edge": viewBox = "0 0 16 16"; content = <g transform="translate(2.225 1.64)"><path d="M9.28 0a2.28 2.28 0 1 1-2.22 2.8h-4.5a1.52 1.52 0 1 0 0 3.03h6.42a2.57 2.57 0 0 1 0 5.14h-4.5a2.28 2.28 0 1 1 0-1.05h4.5a1.52 1.52 0 0 0 0-3.04H2.57a2.57 2.57 0 0 1 0-5.13h4.5C7.3.75 8.2 0 9.26 0m-7 9.22a1.23 1.23 0 1 0 0 2.45 1.23 1.23 0 0 0 0-2.45m7-8.17a1.22 1.22 0 1 0 0 2.45 1.22 1.22 0 0 0 0-2.45" fill="currentColor" stroke="none" /></g>; break;
    case "snap": content = <path d="m12 15 4 4M2.352 10.648a1.205 1.205 0 0 0 0 1.704l2.296 2.296a1.205 1.205 0 0 0 1.704 0l6.029-6.029a1 1 0 1 1 3 3l-6.029 6.029a1.205 1.205 0 0 0 0 1.704l2.296 2.296a1.205 1.205 0 0 0 1.704 0l6.365-6.367A1 1 0 0 0 8.716 4.282zM5 8l4 4" />; break;
    case "map": content = <><path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3zM9 3v15M15 6v15" /></>; break;
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
  return <svg className={`canvas-icon canvas-icon-${name}`} viewBox={viewBox} aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">{content}</svg>;
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

function makeLibtvReferenceEdge(id: string, source: string, target: string): Edge {
  return {
    id,
    source,
    target,
    type: "libtv-reference",
    markerEnd: undefined,
    animated: false,
    className: "workflow-edge libtv-reference-edge",
  };
}

function LibtvReferenceEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  selected,
}: EdgeProps) {
  const [path] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    curvature: .24,
  });
  return <>
    <BaseEdge
      id={id}
      path={path}
      interactionWidth={22}
      className={`libtv-reference-edge-base${selected ? " is-selected" : ""}`}
    />
    <path d={path} className="libtv-reference-edge-pulse" fill="none" aria-hidden="true" />
  </>;
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

const CANVAS_STARTER_PRESETS: readonly CanvasStarterPreset[] = [
  {
    id: "story-script",
    title: "故事脚本生成",
    skill: APP_CANVAS_SKILL_IDS.scriptWorkbench,
    skillPath: `skills/app/${APP_CANVAS_SKILL_IDS.scriptWorkbench}/SKILL.md`,
    cover: "/skill-covers/n2d.jpg",
    nodes: [
      {
        kind: "text",
        title: "剧本",
        description: "《我在盛唐写天下》· 古风 / 穿越 / 爽文漫剧",
        variant: "libtv-source",
        data: { prompt: "《我在盛唐写天下》\n类型：古风 / 穿越 / 爽文漫剧\n时长建议：60–90秒\n基调：热血 × 盛唐史诗感 × 爽点节奏\n\n【序幕】现代深夜办公室，沈昭昭加班昏倒。\n【第一幕】她在盛唐金銮殿醒来，被命当殿作诗。\n【第二幕】她吟出惊世诗篇，满殿震动。\n【第三幕】镜头推远，盛唐山河展开。" },
      },
      {
        kind: "script",
        title: "脚本生成器",
        description: "描述故事、剧情片段或创作目标，生成可继续编辑的分镜脚本",
        variant: "script-new",
        data: { prompt: "根据我上传的剧本生成一个完整的故事脚本" },
      },
    ],
  },
  {
    id: "character-turnaround",
    title: "角色三视图",
    skill: APP_CANVAS_SKILL_IDS.characterTurnaround,
    skillPath: `skills/app/${APP_CANVAS_SKILL_IDS.characterTurnaround}/SKILL.md`,
    cover: "/skill-covers/song.jpg",
    nodes: [
      { kind: "image", title: "角色图", description: "上传、选择或生成角色主参考图", data: { imageMode: "图片输入" } },
      {
        kind: "image",
        title: "角色三视图",
        description: "依据角色主参考生成正面、侧面与背面的一致性角色图",
        variant: "character-workflow",
        data: { imageMode: "角色三视图", aspectRatio: "16:9", prompt: "同一角色，正面、侧面、背面三视图，比例与服装细节保持一致" },
      },
    ],
  },
  {
    id: "first-frame-video",
    title: "首帧图生视频",
    skill: APP_CANVAS_SKILL_IDS.firstFrameVideo,
    skillPath: `skills/app/${APP_CANVAS_SKILL_IDS.firstFrameVideo}/SKILL.md`,
    cover: "/skill-covers/mv.jpg",
    nodes: [
      { kind: "image", title: "首帧图片", description: "上传、选择或生成视频的首帧画面", data: { imageMode: "图片输入" } },
      { kind: "video", title: "首帧图生视频", description: "基于首帧延展动作、镜头和环境变化", variant: "first-frame-video-workflow", data: { videoMode: "首帧生成视频", prompt: "基于首帧自然延展动作与运镜，保持主体和场景连续" } },
    ],
  },
  {
    id: "audio-video",
    title: "音频生视频",
    skill: APP_CANVAS_SKILL_IDS.audioVideo,
    skillPath: `skills/app/${APP_CANVAS_SKILL_IDS.audioVideo}/SKILL.md`,
    cover: "/skill-covers/comic.jpg",
    nodes: [
      { kind: "audio", title: "音频输入", description: "上传或选择成品音频，提取节拍、段落和能量变化", data: { model: "音频分析" } },
      { kind: "image", title: "图片", description: "上传、选择或生成音频视频的视觉首帧", data: { imageMode: "图片输入" } },
      { kind: "video", title: "音频生视频", description: "根据节拍与段落生成卡点视频镜头", variant: "audio-video-workflow", data: { videoMode: "音频生视频", prompt: "根据音频节拍、段落与能量变化生成连续卡点画面" } },
    ],
  },
];

function CanvasStarterPresetIcon({ id }: { id: CanvasStarterPreset["id"] }) {
  if (id === "story-script") return <Film size={21} strokeWidth={2} />;
  if (id === "character-turnaround") return <UserRound size={21} strokeWidth={2} />;
  if (id === "first-frame-video") return <ImagePlay size={21} strokeWidth={2} />;
  return <Music2 size={21} strokeWidth={2} />;
}

function initialGraph(work: WebWork): { nodes: WorkflowNode[]; edges: Edge[] } {
  if (!work.prompt.trim() && work.attachments.length === 0) return { nodes: [], edges: [] };
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
  const resolveAttachment = actions?.resolveAttachment;
  const flow = useReactFlow<WorkflowNode, Edge>();
  const [controlMenu, setControlMenu] = useState<"model" | "settings" | "preset" | "voice" | null>(null);
  const [referenceMenuOpen, setReferenceMenuOpen] = useState(false);
  const [dockExpanded, setDockExpanded] = useState(false);
  const [resultAssetUrl, setResultAssetUrl] = useState("");
  const [runtimeModelOptions, setRuntimeModelOptions] = useState<string[]>([]);
  const [modelDiscoveryState, setModelDiscoveryState] = useState<"idle" | "loading" | "failed">("idle");
  const [modelDiscoveryError, setModelDiscoveryError] = useState("");
  const generatorPromptRef = useRef<HTMLTextAreaElement>(null);
  const generatorComposingRef = useRef(false);
  const generatorCompositionGuardRef = useRef(false);
  const generatorCompositionFrameRef = useRef<number | null>(null);
  const variant = data.variant ?? (data.kind === "script" ? "script-new" : "default");
  const isLibtvSource = variant === "libtv-source" && data.kind === "text";
  const isScriptGenerator = variant === "script-new" && data.kind === "script";
  const isLibtvGenerator = variant === "libtv-generator" || isScriptGenerator;
  const isDirector = variant === "director";
  const prompt = typeof data.prompt === "string" ? data.prompt : "";
  const resultText = typeof data.resultText === "string" ? data.resultText : "";
  const resultAttachmentId = typeof data.resultAttachmentId === "string" ? data.resultAttachmentId : "";
  const persistedGenerationProgress = Math.max(0, Math.min(100, Number(data.generationProgress ?? 0)));
  const [liveGenerationProgress, setLiveGenerationProgress] = useState(persistedGenerationProgress);
  const generationProgress = data.status === "running" ? liveGenerationProgress : persistedGenerationProgress;
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
    if (!selected) {
      setControlMenu(null);
      setReferenceMenuOpen(false);
    }
  }, [selected]);

  useEffect(() => {
    if (!selected || !isLibtvGenerator || data.status === "running") return undefined;
    const frame = window.requestAnimationFrame(() => {
      const textarea = generatorPromptRef.current;
      if (!textarea || document.activeElement === textarea) return;
      textarea.focus({ preventScroll: true });
      textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [data.status, isLibtvGenerator, selected]);

  useEffect(() => () => {
    if (generatorCompositionFrameRef.current !== null) {
      window.cancelAnimationFrame(generatorCompositionFrameRef.current);
    }
  }, []);

  useEffect(() => {
    if (data.status !== "running") {
      setLiveGenerationProgress(persistedGenerationProgress);
      return undefined;
    }
    setLiveGenerationProgress(Math.max(4, persistedGenerationProgress));
    const timer = window.setInterval(() => {
      setLiveGenerationProgress((current) => Math.min(92, current + Math.max(1, Math.round((92 - current) * .08))));
    }, 650);
    return () => window.clearInterval(timer);
  }, [data.generationRequestId, data.status, persistedGenerationProgress]);

  useEffect(() => {
    let active = true;
    let objectUrl = "";
    setResultAssetUrl("");
    if (resultAttachmentId) {
      void (resolveAttachment ? resolveAttachment(resultAttachmentId) : localFile(resultAttachmentId)).then((file) => {
        if (!active || !file) return;
        objectUrl = URL.createObjectURL(file);
        setResultAssetUrl(objectUrl);
      });
    }
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [resolveAttachment, resultAttachmentId]);

  const update = (patch: Partial<WorkflowNodeData>) => actions?.update(id, patch);
  const quick = (action: string) => actions?.quickAction(id, action);
  const setPrompt = (value: string) => update(isLibtvGenerator
    ? { prompt: value }
    : { prompt: value, description: value.trim() || data.description });
  const stopPointer = (event: ReactPointerEvent<HTMLElement>) => event.stopPropagation();
  const generatorModality = data.kind === "image" ? "image" : "text";
  const fallbackModelOptions = isLibtvGenerator && data.kind === "image"
    ? GENERATOR_MODEL_OPTIONS.image.map((model) => model.id)
    : isLibtvGenerator && (data.kind === "text" || isScriptGenerator)
      ? GENERATOR_MODEL_OPTIONS.text.map((model) => model.id)
      : data.kind === "image"
        ? ["Lib Image", "Seedream 5.0 Pro", "Midjourney V7", "Qwen Image"]
    : data.kind === "video"
      ? ["2.0", "Lib Video 2.0", "Seedance 2.0", "Veo 3.1"]
      : data.kind === "audio"
        ? ["Minimax-speech-2.8-hd", "CosyVoice 3", "Fish Speech"]
        : ["GVLM 3.1", "Gemini 3 Pro", "GPT-5.2"];
  const modelOptions = isLibtvGenerator ? runtimeModelOptions : fallbackModelOptions;
  const selectedRuntimeModel = runtimeModelOptions.includes(String(data.model ?? "")) ? String(data.model) : "";
  const modelButtonLabel = isLibtvGenerator
    ? selectedRuntimeModel ? generatorModelLabel(selectedRuntimeModel)
      : modelDiscoveryState === "loading" ? "读取模型…"
        : modelDiscoveryState === "failed" ? "模型不可用" : "选择模型"
    : String(data.model ?? modelOptions[0] ?? "未配置模型");

  const loadGeneratorModels = async () => {
    if (!isLibtvGenerator || modelDiscoveryState === "loading") return;
    setModelDiscoveryState("loading");
    setModelDiscoveryError("");
    setRuntimeModelOptions([]);
    try {
      const models = await discoverCanvasModels();
      const options = models.filter((model) => model.modality === generatorModality).map((model) => model.id);
      if (!options.length) throw new Error(`cli-proxy-api 没有共享可用的${generatorModality === "image" ? "图片" : "文本"}模型`);
      setRuntimeModelOptions(options);
      if (!options.includes(String(data.model ?? ""))) update({ model: options[0] });
      setModelDiscoveryState("idle");
    } catch (error) {
      setRuntimeModelOptions([]);
      setModelDiscoveryState("failed");
      setModelDiscoveryError(error instanceof Error ? error.message : "无法读取共享模型");
    }
  };

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

  const downloadGeneratorResult = () => {
    const downloadableText = isLibtvSource ? (prompt || data.description) : resultText;
    if (!downloadableText && !resultAssetUrl) return;
    const href = resultAssetUrl || URL.createObjectURL(new Blob([downloadableText], { type: "text/markdown;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = href;
    const imageExtension = data.resultMimeType === "image/jpeg"
      ? "jpg"
      : data.resultMimeType === "image/webp"
        ? "webp"
        : data.resultMimeType === "image/gif"
          ? "gif"
          : "png";
    const mediaExtension = data.kind === "video" ? (data.resultMimeType === "video/webm" ? "webm" : "mp4")
      : data.kind === "audio" ? (data.resultMimeType === "audio/wav" ? "wav" : data.resultMimeType === "audio/ogg" ? "ogg" : "mp3")
        : data.kind === "image" ? imageExtension : "md";
    anchor.download = `${data.title}.${mediaExtension}`;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    if (!resultAssetUrl) window.setTimeout(() => URL.revokeObjectURL(href), 0);
  };

  const renderLibtvGeneratorBody = () => {
    if (data.status === "running") return <div
      className="libtv-generator-skeleton"
      role="progressbar"
      aria-label="内容生成进度"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(generationProgress)}
      aria-valuetext={`生成中 ${Math.round(generationProgress)}%`}
    >
      {[76, 89, 82, 91, 88, 66, 90, 57, 43].map((width, index) => <i key={`${width}-${index}`} style={{ width: `${width}%` }} />)}
      <span>生成中 {Math.max(1, Math.round(generationProgress))}%…</span>
    </div>;
    if (data.status === "failed") return <div className="libtv-generator-error nodrag nowheel" role="alert"><strong>生成失败</strong><p>{String(data.generationError ?? "模型暂时没有返回结果，请重试。")}</p><button type="button" onClick={() => actions?.run(id)} disabled={!prompt.trim()}>重新生成</button></div>;
    if (data.kind === "image" && resultAssetUrl) return <div className="libtv-generator-image nodrag nowheel"><img src={resultAssetUrl} alt={data.title} /></div>;
    if (data.kind === "video" && resultAssetUrl) return <div className="libtv-generator-video nodrag nowheel"><video src={resultAssetUrl} controls preload="metadata" aria-label={data.title} /></div>;
    if (data.kind === "audio" && resultAssetUrl) return <div className="libtv-generator-audio nodrag nowheel"><Icon name="audio" /><audio src={resultAssetUrl} controls preload="metadata" aria-label={data.title} /></div>;
    if (data.kind === "text" && resultText) return <div className="libtv-generator-text nodrag nowheel"><p>{resultText}</p><i aria-hidden="true" /></div>;
    return <div className="libtv-generator-empty">
      {isScriptGenerator
        ? <span className="libtv-script-placeholder-lines" aria-hidden="true"><i /><i /><i /><i /><i /></span>
        : <Icon name={data.kind} />}
      <span>{data.kind === "image" ? "描述画面后生成图片" : isScriptGenerator ? "描述故事后生成可编辑分镜脚本" : "输入你的灵感，生成一段文本"}</span>
    </div>;
  };

  const renderLibtvSourceBody = () => <div
    className="libtv-source-text nodrag nowheel nopan"
    role="region"
    aria-label={`${data.title}正文，可滚动查看`}
    tabIndex={0}
    onPointerDown={stopPointer}
  >
    <p>{prompt || data.description}</p>
    <i aria-hidden="true" />
  </div>;

  const renderLibtvGeneratorDock = () => <NodeToolbar
    position={Position.Bottom}
    offset={10}
    align="center"
    className={`libtv-node-composer nodrag nowheel nopan${isScriptGenerator ? " is-script-composer" : ""}${dockExpanded ? " is-expanded" : ""}`}
    onPointerDown={stopPointer}
    onMouseDown={(event) => event.stopPropagation()}
    onClick={(event) => event.stopPropagation()}
    onDoubleClick={(event) => event.stopPropagation()}
  >
    <div className="libtv-node-composer-prompt">
      {isScriptGenerator && data.sourceContext && <span className="libtv-node-composer-reference" aria-label="已引用 1 个剧本节点">
        <span>1</span><Icon name="script" />
      </span>}
      <textarea
        ref={generatorPromptRef}
        className="nodrag nowheel nopan"
        aria-label={`${data.title}生成提示词`}
        aria-busy={data.status === "running"}
        readOnly={data.status === "running"}
        value={prompt}
        placeholder={data.kind === "image" ? "描述你想生成的图片，或基于引用内容补充画面要求" : isScriptGenerator ? "描述故事、剧情片段或创作目标，为你生成可编辑的分镜脚本" : "输入你的创作灵感，例如：一个来自未来的机器人，坐在屋顶看星星"}
        onChange={(event) => setPrompt(event.target.value)}
        onPointerDown={(event) => {
          event.stopPropagation();
          if (document.activeElement !== event.currentTarget) event.currentTarget.focus({ preventScroll: true });
        }}
        onMouseDown={(event) => event.stopPropagation()}
        onCompositionStart={() => {
          generatorComposingRef.current = true;
          generatorCompositionGuardRef.current = false;
          if (generatorCompositionFrameRef.current !== null) {
            window.cancelAnimationFrame(generatorCompositionFrameRef.current);
            generatorCompositionFrameRef.current = null;
          }
        }}
        onCompositionEnd={(event) => {
          generatorComposingRef.current = false;
          generatorCompositionGuardRef.current = true;
          setPrompt(event.currentTarget.value);
          generatorCompositionFrameRef.current = window.requestAnimationFrame(() => {
            generatorCompositionGuardRef.current = false;
            generatorCompositionFrameRef.current = null;
          });
        }}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setControlMenu(null);
            setReferenceMenuOpen(false);
            return;
          }
          if (event.key === "Enter" && !event.shiftKey) {
            if (generatorComposingRef.current || generatorCompositionGuardRef.current || event.nativeEvent.isComposing || event.nativeEvent.keyCode === 229) return;
            event.preventDefault();
            if (event.currentTarget.value.trim() && data.status !== "running") actions?.run(id);
          }
        }}
      />
      <button type="button" className="libtv-node-composer-expand" aria-label={dockExpanded ? "收起输入框" : "展开输入框"} onClick={() => setDockExpanded((expanded) => !expanded)}>{dockExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}</button>
    </div>
    <footer>
      <div className="libtv-node-model-wrap">
        <button type="button" className="libtv-node-model" disabled={data.status === "running"} aria-haspopup="menu" aria-expanded={controlMenu === "model"} onClick={() => {
          const opening = controlMenu !== "model";
          setControlMenu(opening ? "model" : null);
          if (opening) void loadGeneratorModels();
        }}><Sparkles size={17} /><span>{modelButtonLabel}</span><ChevronDown size={12} /></button>
        {controlMenu === "model" && <div className="libtv-node-model-menu" role="menu" aria-label="选择生成模型">
          {modelDiscoveryState === "loading" && <p className="libtv-node-model-state">正在读取共享模型…</p>}
          {modelDiscoveryState === "failed" && <p className="libtv-node-model-state is-error">{modelDiscoveryError}</p>}
          {modelOptions.map((model) => <button key={model} type="button" role="menuitem" className={data.model === model ? "is-active" : ""} onClick={() => { update({ model }); setControlMenu(null); }}><span><b>{generatorModelLabel(model)}</b><small>LabuTV 后端 · discovery 已开放</small></span>{data.model === model && <Check size={14} />}</button>)}
        </div>}
      </div>
      <span className="libtv-node-composer-spacer" />
      <button type="button" className="libtv-node-translate" aria-label="优化提示词" title="优化提示词" onClick={() => quick("优化提示词")}><Languages size={17} /></button>
      <span className="libtv-node-credit" title="预计积分"><Zap size={12} fill="currentColor" />6</span>
      <button
        type="button"
        className={`libtv-node-submit${data.status === "running" ? " is-running" : ""}`}
        style={{ "--generation-progress": `${generationProgress * 3.6}deg` } as CSSProperties}
        disabled={!prompt.trim() && data.status !== "running"}
        onClick={() => data.status === "running" ? actions?.cancel(id) : actions?.run(id)}
        aria-label={data.status === "running" ? `取消生成，当前 ${Math.round(generationProgress)}%` : "开始生成"}
      >{data.status === "running" ? <X size={17} /> : <ArrowUp size={19} />}</button>
    </footer>
  </NodeToolbar>;

  const renderReferenceMenu = () => <NodeToolbar
    isVisible={referenceMenuOpen}
    position={Position.Right}
    offset={22}
    align="start"
    role="menu"
    aria-label="引用该节点生成"
    className="libtv-node-reference-menu nodrag nowheel"
    onPointerDown={stopPointer}
    onKeyDown={(event) => { if (event.key === "Escape") setReferenceMenuOpen(false); }}
    onDoubleClick={(event) => event.stopPropagation()}
  >
    <strong>引用该节点生成</strong>
    <button type="button" role="menuitem" onClick={() => { actions?.derive(id, "text", "libtv-generator"); setReferenceMenuOpen(false); }}><Icon name="text" />文本</button>
    <button type="button" role="menuitem" onClick={() => { actions?.derive(id, "image", "libtv-generator"); setReferenceMenuOpen(false); }}><Icon name="image" />图片</button>
    <button type="button" role="menuitem" onClick={() => { actions?.derive(id, "video"); setReferenceMenuOpen(false); }}><Icon name="video" />视频</button>
    <button type="button" role="menuitem" disabled><Scissors size={16} />智能剪辑 <i>Beta</i></button>
    <button type="button" role="menuitem" onClick={() => { actions?.derive(id, "script", "director"); setReferenceMenuOpen(false); }}><Icon name="workflow" />导演台 <i className="is-new">NEW</i></button>
    <button type="button" role="menuitem" disabled><Film size={16} />逐帧拉片 <i className="is-model">SD 2.5</i></button>
    <button type="button" role="menuitem" onClick={() => { actions?.derive(id, "audio"); setReferenceMenuOpen(false); }}><Icon name="audio" />音频</button>
    <button type="button" role="menuitem" onClick={() => { actions?.derive(id, "script", "script-new"); setReferenceMenuOpen(false); }}><Icon name="script" />脚本 <ChevronRight className="libtv-reference-chevron" size={14} /></button>
    <button type="button" role="menuitem" disabled><Link2 size={16} />参考节点</button>
  </NodeToolbar>;

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
        <button type="button" className="workflow-node-model-button" aria-expanded={controlMenu === "model"} onClick={() => setControlMenu((current) => current === "model" ? null : "model")}><span>{modelButtonLabel}</span><ChevronDown size={12} /></button>
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

  const renderScriptWorkflowNode = () => {
    const workbench = normalizeScriptWorkbench(data.scriptWorkbench);
    const steps = deriveScriptWorkbenchSteps(workbench);
    const stepStates = [steps.shots, steps.assets, steps.prompts];
    const workflowReady = isScriptWorkbenchReadyForBatchVideo(workbench);
    return <div className="workflow-script-result nodrag" onPointerDown={stopPointer}>
      <div className="workflow-script-result-actions">
        <button type="button" onClick={() => actions?.scriptAction(id, "regenerate")}><RotateCcw size={13} />重新生成</button>
        <button type="button" disabled={!workflowReady} title={!workflowReady ? "镜头、资产与提示词全部完成后可用" : undefined} onClick={() => actions?.scriptAction(id, "storyboard")}>批量生成分镜</button>
        <button type="button" disabled={!workflowReady} title={!workflowReady ? "镜头、资产与提示词全部完成后可用" : undefined} onClick={() => actions?.scriptAction(id, "video")}>批量生视频</button>
        <button type="button" aria-label="下载脚本 JSON" onClick={() => actions?.scriptAction(id, "download")}><Download size={13} /></button>
      </div>
      <strong>{workbench.title}</strong>
      <small>{workbench.shots.length} 个镜头 · {workbench.assets.length} 个资产</small>
      <small title={workbench.content_sha256}>唯一状态 {workbench.state} · {workbench.content_sha256.slice(0, 12)}</small>
      <div className="workflow-script-result-steps">
        {["确认镜头", "准备资产", "合成提示词"].map((label, index) => <span key={label} className={stepStates[index] === "done" ? "is-done" : stepStates[index] === "active" ? "is-active" : ""}><i>{stepStates[index] === "done" ? <Check size={11} /> : index + 1}</i><b>{label}</b></span>)}
      </div>
      <button type="button" className="workflow-script-open" onClick={() => actions?.openScript(id)}>打开脚本节点 <ArrowRight size={13} /></button>
    </div>;
  };

  const renderStandaloneWorkflowNode = () => {
    const workflow: StandaloneWorkflowKind = variant === "character-workflow"
      ? "character-turnaround"
      : variant === "first-frame-video-workflow"
        ? "first-frame-video"
        : "audio-video";
    const meta = workflow === "character-turnaround"
      ? { title: "角色三视图", steps: ["选择角色图", "完善角色设定", "生成三视图"], icon: <UserRound size={25} /> }
      : workflow === "first-frame-video"
        ? { title: "首帧图生视频", steps: ["选择首帧", "设计运动", "生成视频"], icon: <ImagePlay size={25} /> }
        : { title: "音频生视频", steps: ["导入音频", "节拍与画面", "生成视频"], icon: <Music2 size={25} /> };
    return <div className="workflow-standalone-result nodrag" onPointerDown={stopPointer}>
      <div className="workflow-standalone-visual"><span>{meta.icon}</span><i /><i /><i /></div>
      <strong>{meta.title}</strong>
      <div className="workflow-standalone-steps">{meta.steps.map((label, index) => <span key={label}><i>{index + 1}</i><b>{label}</b></span>)}</div>
      <button type="button" onClick={() => actions?.openStandalone(id, workflow)}>打开工作台 <ArrowRight size={13} /></button>
    </div>;
  };

  const renderDirectorNode = () => <div className="workflow-director-node nodrag" onPointerDown={stopPointer} onDoubleClick={(event) => event.stopPropagation()}>
    <div className="workflow-director-visual">
      <Box size={44} strokeWidth={1.35} />
      <p>在3D空间中搭建场景并进行多视角截图</p>
      <button type="button" onClick={() => actions?.openDirector(id)}>打开导演台</button>
    </div>
    <div className="workflow-director-composer nowheel">
      <textarea
        aria-label={`${data.title}场景描述`}
        placeholder="描述想要搭建的场景，支持通过参考图创建"
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing && event.nativeEvent.keyCode !== 229) {
            event.preventDefault();
            if (prompt.trim()) actions?.openDirector(id, { runPrompt: true });
          }
        }}
      />
      <button type="button" className="workflow-director-add-reference" aria-label="添加参考图" onClick={() => actions?.openDirector(id, { reference: true })}><Plus size={23} /></button>
      <button type="button" className="workflow-director-submit" aria-label="打开导演台搭建场景" disabled={!prompt.trim()} onClick={() => actions?.openDirector(id, { runPrompt: true })}><ArrowUp size={21} /></button>
    </div>
  </div>;

  return (
    <article className={`workflow-node-card kind-${data.kind} variant-${variant}${isScriptGenerator ? " variant-libtv-generator" : ""} status-${data.status}${selected ? ` is-selected${isLibtvGenerator || isLibtvSource || isDirector ? "" : " is-expanded"}` : ""}`}>
      <Handle type="target" position={Position.Left} className="workflow-handle workflow-handle-target">{isLibtvGenerator && <Plus size={11} />}</Handle>
      <header>
        <span className="workflow-node-icon"><Icon name={variant === "director" ? "workflow" : data.kind} /></span>
        <span className="workflow-node-heading"><small>{data.eyebrow}</small><strong>{data.title}</strong></span>
        <i className="workflow-node-status" aria-label={data.status} />
      </header>
      {!selected && !isLibtvGenerator && !isLibtvSource && (data.kind === "image" || data.kind === "video") && (
        <div className={`workflow-node-preview preview-${data.kind}`}><span /><span /><span />{data.kind === "video" && <i><Icon name="video" /></i>}</div>
      )}
      {!selected && data.kind === "audio" && <div className="workflow-node-waveform" aria-hidden="true">{[8, 15, 10, 23, 18, 27, 12, 21, 9, 18, 13, 25, 16, 9].map((height, index) => <i key={`${height}-${index}`} style={{ height }} />)}</div>}
      {isLibtvSource ? renderLibtvSourceBody()
        : isLibtvGenerator ? renderLibtvGeneratorBody()
        : variant === "script-workflow" ? renderScriptWorkflowNode()
        : (variant === "character-workflow" || variant === "first-frame-video-workflow" || variant === "audio-video-workflow") ? renderStandaloneWorkflowNode()
        : isDirector ? renderDirectorNode()
        : selected && data.kind === "compose" ? <div className="workflow-compose-node nodrag" onPointerDown={stopPointer}>{incomingVideoCount ? <><div className="workflow-compose-preview"><Play size={24} /></div><div className="workflow-compose-timeline">{Array.from({ length: incomingVideoCount }).map((_, index) => <span key={index}><i />片段 {index + 1}<small>{String(index * 5).padStart(2, "0")}:00</small></span>)}</div><button type="button" onClick={() => actions?.run(id)}><Icon name="compose" />合成并导出</button></> : <><Icon name="compose" /><strong>空空如也</strong><span>请连接视频节点后操作</span><button type="button" onClick={() => quick("添加视频片段")}><Plus size={14} />添加视频片段</button></>}</div>
          : selected ? renderPromptNode() : <>
            <p>{data.description}</p>
            {data.assetName && <span className="workflow-node-asset">{data.assetName}</span>}
          </>}
      <footer><span>{data.status === "running" ? "生成中…" : data.status === "done" ? "已完成" : data.status === "failed" ? "执行失败" : selected ? "编辑节点参数" : "点击选择节点"}</span><b>•••</b></footer>
      <Handle
        type="source"
        position={Position.Right}
        className="workflow-handle workflow-handle-source"
        aria-label="引用该节点生成"
        role={isLibtvGenerator ? "button" : undefined}
        tabIndex={isLibtvGenerator ? 0 : undefined}
        aria-haspopup={isLibtvGenerator ? "menu" : undefined}
        aria-expanded={isLibtvGenerator ? referenceMenuOpen : undefined}
        onPointerDown={(event) => { if (isLibtvGenerator) event.stopPropagation(); }}
        onClick={(event) => {
          if (!isLibtvGenerator) return;
          event.stopPropagation();
          setReferenceMenuOpen((open) => !open);
        }}
        onKeyDown={(event) => {
          if (!isLibtvGenerator || (event.key !== "Enter" && event.key !== " ")) return;
          event.preventDefault();
          event.stopPropagation();
          setReferenceMenuOpen((open) => !open);
        }}
      >{isLibtvGenerator && <Plus size={11} />}</Handle>
      {isLibtvGenerator && (!isScriptGenerator || data.status !== "running") && renderLibtvGeneratorDock()}
      {isLibtvGenerator && renderReferenceMenu()}
      {isLibtvSource && Boolean(prompt || data.description) && <NodeToolbar position={Position.Top} offset={39} align="center" className="libtv-node-download-toolbar nodrag"><button type="button" aria-label="下载剧本内容" title="下载剧本内容" onPointerDown={stopPointer} onClick={downloadGeneratorResult}><Download size={19} /></button></NodeToolbar>}
      {isLibtvGenerator && !isScriptGenerator && data.status === "done" && (resultText || resultAssetUrl) && <NodeToolbar position={Position.Top} offset={39} align="center" className="libtv-node-download-toolbar nodrag"><button type="button" aria-label="下载生成结果" onClick={downloadGeneratorResult}><Download size={19} /></button></NodeToolbar>}
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
const EDGE_TYPES = { "libtv-reference": LibtvReferenceEdge };

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
      {overviewOpen ? <button type="button" onClick={onOrganize} title="整理画布（⌥ ⇧ F）" aria-label="整理画布"><Icon name="tidy" /></button> : <button type="button" onClick={onOpenOverview} title="资产管理"><Icon name="asset-manager" /><span>资产管理</span></button>}
      <span className="canvas-control-divider" />
      <button type="button" className={miniMapVisible ? "is-active" : ""} onClick={onToggleMiniMap} title="切换小地图" aria-label="切换小地图"><Icon name="minimap" /></button>
      <button type="button" className={edgesVisible ? "is-active" : ""} onClick={onToggleEdges} title="隐藏节点连线" aria-label="隐藏节点连线"><Icon name="edge" /></button>
      <button type="button" className={snapToGridEnabled ? "is-active" : ""} onClick={onToggleSnap} title="网格吸附" aria-pressed={snapToGridEnabled}><Icon name="snap" /></button>
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

function attachmentAssetTag(attachment: DraftAttachment): AssetTag {
  const searchable = `${attachment.name} ${attachment.type}`.toLocaleLowerCase();
  if (attachment.type.startsWith("audio/") || /音效|音乐|配音|audio|sound/.test(searchable)) return "音效";
  if (/人物|角色|人像|character|portrait/.test(searchable)) return "人物";
  if (/场景|背景|环境|scene|background/.test(searchable)) return "场景";
  if (/风格|style|lora/.test(searchable)) return "风格";
  if (/物品|道具|产品|object|product|prop/.test(searchable)) return "物品";
  return "其它";
}

function mergeDraftAttachments(...groups: DraftAttachment[][]): DraftAttachment[] {
  const merged = new Map<string, DraftAttachment>();
  groups.forEach((group) => group.forEach((attachment) => {
    const current = merged.get(attachment.id);
    merged.set(attachment.id, {
      ...current,
      ...attachment,
      ...(!attachment.assetId && current?.assetId ? { assetId: current.assetId } : {}),
    });
  }));
  return [...merged.values()];
}

function sameStringList(value: unknown, expected: string[]): boolean {
  return Array.isArray(value)
    && value.length === expected.length
    && value.every((item, index) => item === expected[index]);
}

function timestamp() {
  return new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date());
}

function generatedImageFile(base64: string, mimeType: string, title: string): File {
  const binary = window.atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  const extension = mimeType === "image/jpeg" ? "jpg" : mimeType === "image/webp" ? "webp" : mimeType === "image/gif" ? "gif" : "png";
  const safeTitle = title.replace(/[\\/:*?"<>|]/g, " ").replace(/\s+/g, " ").trim().slice(0, 60) || "生成图片";
  return new File([bytes], `${safeTitle}-${Date.now()}.${extension}`, { type: mimeType, lastModified: Date.now() });
}

async function generatedScriptAssetFile(
  base64: string,
  mimeType: string,
  title: string,
  ratio: "2:1" | "16:9" | "9:16" | "1:1",
  resolution: "2K" | "4K",
  quality: "standard" | "high",
  signal: AbortSignal,
): Promise<File> {
  const source = generatedImageFile(base64, mimeType, title);
  const bitmap = await createImageBitmap(source);
  try {
    if (signal.aborted) throw new DOMException("资产生成已取消", "AbortError");
    const ratioValue = ratio === "2:1" ? 2 : ratio === "16:9" ? 16 / 9 : ratio === "9:16" ? 9 / 16 : 1;
    const longEdge = resolution === "4K" ? 4096 : 2048;
    const width = ratioValue >= 1 ? longEdge : Math.max(1, Math.round(longEdge * ratioValue));
    const height = ratioValue >= 1 ? Math.max(1, Math.round(longEdge / ratioValue)) : longEdge;
    const sourceRatio = bitmap.width / Math.max(1, bitmap.height);
    let sx = 0;
    let sy = 0;
    let sw = bitmap.width;
    let sh = bitmap.height;
    if (sourceRatio > ratioValue) {
      sw = bitmap.height * ratioValue;
      sx = (bitmap.width - sw) / 2;
    } else if (sourceRatio < ratioValue) {
      sh = bitmap.width / ratioValue;
      sy = (bitmap.height - sh) / 2;
    }
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("无法创建资产图处理画布");
    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = "high";
    context.drawImage(bitmap, sx, sy, sw, sh, 0, 0, width, height);
    if (signal.aborted) throw new DOMException("资产生成已取消", "AbortError");
    const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(
      (result) => result ? resolve(result) : reject(new Error("资产图编码失败")),
      "image/jpeg",
      quality === "high" ? .95 : .9,
    ));
    if (!blob.size || blob.size > MAX_GENERATED_IMAGE_BYTES) {
      throw new Error("资产图编码后为空或超过 25MB，请降低分辨率或画质后重试");
    }
    if (signal.aborted) throw new DOMException("资产生成已取消", "AbortError");
    const safeTitle = title.replace(/[\\/:*?"<>|]/g, " ").replace(/\s+/g, " ").trim().slice(0, 60) || "故事资产";
    return new File([blob], `${safeTitle}-${resolution}-${Date.now()}.jpg`, { type: "image/jpeg", lastModified: Date.now() });
  } finally {
    bitmap.close();
  }
}

async function scriptWorkbenchBlobSha256(blob: Blob): Promise<string> {
  return scriptWorkbenchSha256Bytes(new Uint8Array(await blob.arrayBuffer()));
}

function scriptWorkbenchAttachmentVerification(
  attachmentId: string,
  sha256: string,
): ScriptWorkbenchByteVerification {
  return {
    status: "verified",
    verifier_kind: "web_attachment",
    method: "sha256",
    durable_ref: `attachment:${attachmentId}`,
    sha256,
    verified_at: new Date().toISOString(),
  };
}

async function generatedPanoramaFile(base64: string, mimeType: string, title: string): Promise<File> {
  const source = generatedImageFile(base64, mimeType, title);
  const bitmap = await createImageBitmap(source);
  try {
    const width = 2048;
    const height = 1024;
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("无法创建全景图处理画布");
    const sourceRatio = bitmap.width / Math.max(1, bitmap.height);
    let sx = 0;
    let sy = 0;
    let sw = bitmap.width;
    let sh = bitmap.height;
    if (sourceRatio > 2) {
      sw = bitmap.height * 2;
      sx = (bitmap.width - sw) / 2;
    } else if (sourceRatio < 2) {
      sh = bitmap.width / 2;
      sy = (bitmap.height - sh) / 2;
    }
    context.drawImage(bitmap, sx, sy, sw, sh, 0, 0, width, height);
    const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob((result) => result ? resolve(result) : reject(new Error("全景图编码失败")), "image/png"));
    const safeTitle = title.replace(/[\\/:*?"<>|]/g, " ").replace(/\s+/g, " ").trim().slice(0, 60) || "AI全景图";
    return new File([blob], `${safeTitle}-${Date.now()}.png`, { type: "image/png", lastModified: Date.now() });
  } finally {
    bitmap.close();
  }
}

async function fileBase64(file: File, signal: AbortSignal): Promise<string> {
  if (file.size > 12 * 1024 * 1024) throw new Error("参考图片不能超过 12MB");
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    const abort = () => reader.abort();
    signal.addEventListener("abort", abort, { once: true });
    reader.onload = () => {
      signal.removeEventListener("abort", abort);
      const dataUrl = typeof reader.result === "string" ? reader.result : "";
      const base64 = dataUrl.slice(dataUrl.indexOf(",") + 1);
      if (!base64) reject(new Error("参考图片读取失败"));
      else resolve(base64);
    };
    reader.onerror = () => {
      signal.removeEventListener("abort", abort);
      reject(new Error("参考图片读取失败"));
    };
    reader.onabort = () => {
      signal.removeEventListener("abort", abort);
      reject(new DOMException("视觉分析已取消", "AbortError"));
    };
    reader.readAsDataURL(file);
  });
}

async function referenceImageCollage(files: File[], signal: AbortSignal): Promise<File> {
  const usable = files.filter((file) => file.type.startsWith("image/")).slice(0, 6);
  if (!usable.length) throw new Error("参考资产没有可读取的图片");
  if (usable.length === 1 && /^image\/(?:png|jpeg|webp)$/.test(usable[0].type) && usable[0].size <= 12 * 1024 * 1024) {
    return usable[0];
  }
  const columns = Math.min(3, Math.ceil(Math.sqrt(usable.length)));
  const rows = Math.ceil(usable.length / columns);
  const cell = 512;
  const canvas = document.createElement("canvas");
  canvas.width = columns * cell;
  canvas.height = rows * cell;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("无法创建参考资产拼图");
  context.fillStyle = "#1b1c1f";
  context.fillRect(0, 0, canvas.width, canvas.height);
  for (let index = 0; index < usable.length; index += 1) {
    if (signal.aborted) throw new DOMException("图片生成已取消", "AbortError");
    const bitmap = await createImageBitmap(usable[index]);
    try {
      const scale = Math.min((cell - 24) / bitmap.width, (cell - 24) / bitmap.height);
      const width = Math.max(1, Math.round(bitmap.width * scale));
      const height = Math.max(1, Math.round(bitmap.height * scale));
      const x = (index % columns) * cell + Math.round((cell - width) / 2);
      const y = Math.floor(index / columns) * cell + Math.round((cell - height) / 2);
      context.drawImage(bitmap, x, y, width, height);
    } finally {
      bitmap.close();
    }
  }
  const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(
    (result) => result ? resolve(result) : reject(new Error("参考资产拼图编码失败")),
    "image/jpeg",
    .9,
  ));
  if (signal.aborted) throw new DOMException("图片生成已取消", "AbortError");
  if (!blob.size || blob.size > 12 * 1024 * 1024) throw new Error("参考资产拼图超过 12MB");
  return new File([blob], `script-reference-${Date.now()}.jpg`, { type: "image/jpeg", lastModified: Date.now() });
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

function isTransientGenerationNode(data: WorkflowNodeData): boolean {
  return data.variant === "libtv-generator" || data.variant === "script-new";
}

function copyableWorkflowNodeData(data: WorkflowNodeData): WorkflowNodeData {
  if (!isTransientGenerationNode(data) || data.status !== "running") return { ...data };
  const hasResult = Boolean(data.resultText || data.resultAttachmentId);
  return {
    ...data,
    status: hasResult ? "done" : "idle",
    generationProgress: hasResult ? 100 : 0,
    generationRequestId: undefined,
    generationError: undefined,
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
  return {
    generationMode: "auto",
    model: {
      modality: "text",
      modelId: "",
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
    if (!storedDocument) return initialGraph(work);
    if (!storedDocument.nodes.length) return { nodes: [], edges: [] };
    const storedNodes: WorkflowNode[] = storedDocument.nodes.map((node): WorkflowNode => {
      const storedData = node.data as WorkflowNodeData;
      const canonicalStoredSkillId = canonicalAppSkillId(storedData.skillId);
      const canonicalStoredSkillPath = canonicalAppSkillPath(canonicalStoredSkillId)
        ?? canonicalAppSkillText(storedData.skillPath);
      const canonicalStoredAssetName = canonicalAppSkillText(storedData.assetName);
      let data = (
        canonicalStoredSkillId !== (storedData.skillId ?? null)
        || canonicalStoredSkillPath !== storedData.skillPath
        || canonicalStoredAssetName !== storedData.assetName
      ) ? {
          ...storedData,
          ...(canonicalStoredSkillId ? { skillId: canonicalStoredSkillId } : {}),
          ...(canonicalStoredSkillPath ? { skillPath: canonicalStoredSkillPath } : {}),
          ...(canonicalStoredAssetName ? { assetName: canonicalStoredAssetName } : {}),
        } : storedData;
      if (data.skillId === "n2d-script") {
        data = {
          ...data,
          assetName: data.assetName === "Skill · n2d-script" ? `Skill · ${APP_CANVAS_SKILL_IDS.scriptWorkbench}` : data.assetName,
          skillId: APP_CANVAS_SKILL_IDS.scriptWorkbench,
          skillPath: `skills/app/${APP_CANVAS_SKILL_IDS.scriptWorkbench}/SKILL.md`,
        };
      } else if (data.skillId === "comic-identity" && ["角色图", "角色三视图"].includes(data.title)) {
        data = { ...data, ...(data.title === "角色三视图" ? { variant: "character-workflow" as const } : {}), assetName: `Skill · ${APP_CANVAS_SKILL_IDS.characterTurnaround}`, skillId: APP_CANVAS_SKILL_IDS.characterTurnaround, skillPath: `skills/app/${APP_CANVAS_SKILL_IDS.characterTurnaround}/SKILL.md` };
      } else if (data.skillId === "n2d-video" && ["首帧图片", "首帧图生视频"].includes(data.title)) {
        data = { ...data, ...(data.title === "首帧图生视频" ? { variant: "first-frame-video-workflow" as const } : {}), assetName: `Skill · ${APP_CANVAS_SKILL_IDS.firstFrameVideo}`, skillId: APP_CANVAS_SKILL_IDS.firstFrameVideo, skillPath: `skills/app/${APP_CANVAS_SKILL_IDS.firstFrameVideo}/SKILL.md` };
      } else if (data.skillId === "mv" && ["音频输入", "图片", "音频生视频"].includes(data.title)) {
        data = { ...data, ...(data.title === "音频生视频" ? { variant: "audio-video-workflow" as const } : {}), assetName: `Skill · ${APP_CANVAS_SKILL_IDS.audioVideo}`, skillId: APP_CANVAS_SKILL_IDS.audioVideo, skillPath: `skills/app/${APP_CANVAS_SKILL_IDS.audioVideo}/SKILL.md` };
      }
      if (data.variant === "director") {
        data = {
          ...data,
          directorScene: normalizeDirectorScene(data.directorScene),
        };
      }
      if (data.variant === "script-workflow") {
        data = {
          ...data,
          scriptWorkbench: normalizeScriptWorkbench(data.scriptWorkbench),
        };
      }
      if (
        data.kind === "video"
        && data.status === "done"
        && data.skillId === APP_CANVAS_SKILL_IDS.firstFrameVideo
        && typeof data.scriptSourceNodeId === "string"
        && !data.resultAttachmentId
      ) {
        data = {
          ...data,
          status: "ready",
          assetName: undefined,
          generationError: "旧版本曾把未提交的视频任务标为完成，现已恢复为待提交。",
        };
      }
      if (isTransientGenerationNode(data) && data.status === "running") {
        data = {
          ...data,
          status: "failed",
          generationProgress: 0,
          generationRequestId: undefined,
          generationError: "上次生成在页面关闭时中断，请重新提交。",
        };
      }
      return {
        ...node,
        type: "workflow-node" as const,
        data,
      };
    });
    const legacyScriptResults = new Map(storedNodes
      .filter((node) => {
        if (node.data.variant !== "script-workflow" || typeof node.data.sourceNodeId !== "string") return false;
        return storedNodes.some((source) => source.id === node.data.sourceNodeId && source.data.variant === "script-new");
      })
      .map((node) => [String(node.data.sourceNodeId), node]));
    const mergedStoredNodes = storedNodes
      .filter((node) => ![...legacyScriptResults.values()].some((result) => result.id === node.id))
      .map((node) => {
        const legacyResult = legacyScriptResults.get(node.id);
        if (!legacyResult || node.data.variant !== "script-new") return node;
        return {
          ...node,
          selected: node.selected || legacyResult.selected,
          data: {
            ...node.data,
            ...legacyResult.data,
            prompt: node.data.prompt,
            sourceNodeId: node.data.sourceNodeId,
            sourceContext: node.data.sourceContext,
          },
        };
      });
    const legacyResultIds = new Set([...legacyScriptResults.values()].map((node) => node.id));
    const mergedStoredEdges = storedDocument.edges
      .filter((edge) => !(legacyScriptResults.has(edge.source) && legacyResultIds.has(edge.target)))
      .map((edge) => ({
        ...edge,
        source: legacyResultIds.has(edge.source)
          ? String(storedNodes.find((node) => node.id === edge.source)?.data.sourceNodeId ?? edge.source)
          : edge.source,
        target: legacyResultIds.has(edge.target)
          ? String(storedNodes.find((node) => node.id === edge.target)?.data.sourceNodeId ?? edge.target)
          : edge.target,
      }))
      .filter((edge) => edge.source !== edge.target);
    const scriptReferenceEdges = mergedStoredEdges.filter((edge) => (
      mergedStoredNodes.find((node) => node.id === edge.target)?.data.variant === "script-new"
    ));
    const scriptSourceIds = new Set(scriptReferenceEdges.map((edge) => edge.source));
    const normalizedNodes = mergedStoredNodes.map((node) => {
      const incomingScriptEdge = scriptReferenceEdges.find((edge) => edge.target === node.id);
      if (incomingScriptEdge) {
        const source = mergedStoredNodes.find((candidate) => candidate.id === incomingScriptEdge.source);
        return {
          ...node,
          position: source ? { x: source.position.x + 730, y: source.position.y - 94 } : node.position,
          data: {
            ...node.data,
            prompt: node.data.prompt === "请把以下故事构想生成可执行的分镜脚本："
              ? "根据我上传的剧本生成一个完整的故事脚本"
              : node.data.prompt,
            sourceNodeId: source?.id,
            sourceContext: String(source?.data.resultText ?? source?.data.prompt ?? source?.data.description ?? ""),
          },
        };
      }
      if (scriptSourceIds.has(node.id) && node.data.kind === "text" && node.data.skillId === APP_CANVAS_SKILL_IDS.scriptWorkbench) {
        return {
          ...node,
          data: {
            ...node.data,
            title: "剧本",
            variant: "libtv-source" as const,
            status: "done" as const,
          },
        };
      }
      return node;
    });
    const storedEdges = mergedStoredEdges.map((edge) => {
      const target = normalizedNodes.find((node) => node.id === edge.target);
      const isLibtvReference = target?.data.sourceNodeId === edge.source && typeof target.data.sourceContext === "string";
      return {
        ...edge,
        type: isLibtvReference ? "libtv-reference" : edge.type ?? "smoothstep",
        animated: isLibtvReference ? false : edge.animated,
        markerEnd: isLibtvReference ? undefined : { type: MarkerType.ArrowClosed },
        className: isLibtvReference ? "workflow-edge libtv-reference-edge" : "workflow-edge",
      };
    });
    return { nodes: normalizedNodes, edges: storedEdges };
  }, [storedDocument, work.id, work.line]);
  const [nodes, setNodes, onNodesChange] = useNodesState<WorkflowNode>(graph.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(graph.edges);
  const [workName, setWorkName] = useState(storedDocument?.work.name ?? work.name);
  const [view, setView] = useState<CanvasView>(storedDocument?.preferences.view ?? "workflow");
  const [tool, setTool] = useState<CanvasTool>("select");
  const [drawer, setDrawer] = useState<DrawerKind | null>(null);
  const [toolboxTab, setToolboxTab] = useState<"mine" | "classic">("mine");
  const [toolboxGuideOpen, setToolboxGuideOpen] = useState(false);
  const [toolboxDetail, setToolboxDetail] = useState<ToolboxTemplate | null>(null);
  const [toolboxClassicDetail, setToolboxClassicDetail] = useState<ToolboxClassic | null>(null);
  const [overlay, setOverlay] = useState<OverlayKind | null>(null);
  const [railMenu, setRailMenu] = useState<RailMenuKind>(null);
  const [helpPanel, setHelpPanel] = useState<HelpPanelKind>(null);
  const [helpMessage, setHelpMessage] = useState("");
  const [helpMessages, setHelpMessages] = useState<Array<{ sender: "bot" | "user"; text: string }>>([
    { sender: "bot", text: "您好，请问有什么可以帮助您？" },
  ]);
  const [sharePanel, setSharePanel] = useState<SharePanelKind>("choices");
  const [addDrawerSubmenu, setAddDrawerSubmenu] = useState<"script" | null>(null);
  const [canvasInsertMenu, setCanvasInsertMenu] = useState<CanvasInsertMenuState | null>(null);
  const [canvasHistoryPickerOpen, setCanvasHistoryPickerOpen] = useState(false);
  const [canvasHistorySource, setCanvasHistorySource] = useState<CanvasHistorySource>("libtv");
  const [canvasHistoryMedia, setCanvasHistoryMedia] = useState<CanvasHistoryMedia>("image");
  const [canvasHistorySelection, setCanvasHistorySelection] = useState<string[]>([]);
  const [historyInsertPoint, setHistoryInsertPoint] = useState<{ x: number; y: number } | null>(null);
  const [pendingUploadPoint, setPendingUploadPoint] = useState<{ x: number; y: number } | null>(null);
  const [libraryInsertPoint, setLibraryInsertPoint] = useState<{ x: number; y: number } | null>(null);
  const [directorStudioNodeId, setDirectorStudioNodeId] = useState<string | null>(null);
  const [directorReferenceNodeId, setDirectorReferenceNodeId] = useState<string | null>(null);
  const [directorRunPromptNodeId, setDirectorRunPromptNodeId] = useState<string | null>(null);
  const [scriptWorkflowNodeId, setScriptWorkflowNodeId] = useState<string | null>(null);
  const [scriptWorkflowInitialDialog, setScriptWorkflowInitialDialog] = useState<"video" | null>(null);
  const [scriptPromptModels, setScriptPromptModels] = useState<ScriptWorkbenchModelOption[]>([]);
  const [scriptImageModels, setScriptImageModels] = useState<ScriptWorkbenchModelOption[]>([]);
  const [scriptCanvasImages, setScriptCanvasImages] = useState<ScriptWorkbenchCanvasImage[]>([]);
  const [standaloneWorkflow, setStandaloneWorkflow] = useState<{ nodeId: string; workflow: StandaloneWorkflowKind } | null>(null);
  const [libraryTab, setLibraryTab] = useState<"square" | "favorite" | "recent">("square");
  const [libraryQuery, setLibraryQuery] = useState("");
  const [libraryCategory, setLibraryCategory] = useState("推荐");
  const [libraryCommercialOnly, setLibraryCommercialOnly] = useState(false);
  const [libraryFavorites, setLibraryFavorites] = useState<Set<string>>(() => new Set());
  const [libraryRecent, setLibraryRecent] = useState<string[]>([]);
  const [libraryDetail, setLibraryDetail] = useState<PresetDefinition | null>(null);
  const [libraryMinimized, setLibraryMinimized] = useState(false);
  const [libraryModelFilter, setLibraryModelFilter] = useState("全部");
  const [libraryModelMenuOpen, setLibraryModelMenuOpen] = useState(false);
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
  const [panelOpen, setPanelOpen] = useState(storedDocument?.preferences.panelOpen ?? false);
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
  const [activeSkill, setActiveSkill] = useState<string | null>(
    canonicalAppSkillId(storedDocument?.activeSkill ?? work.creationConfig?.skillId ?? null),
  );
  const [creationConfig, setCreationConfig] = useState<WorkCreationConfig>(() => {
    const initial = defaultCreationConfig(storedDocument?.work ?? work);
    const skillId = canonicalAppSkillId(initial.skillId);
    return skillId && skillId !== initial.skillId ? { ...initial, skillId } : initial;
  });
  const [composerMenu, setComposerMenu] = useState<ComposerMenuKind>(null);
  const [composerAttachmentIds, setComposerAttachmentIds] = useState<string[]>(() => (storedDocument?.work.attachments ?? work.attachments).map((attachment) => attachment.id));
  const [membershipOpen, setMembershipOpen] = useState(false);
  const [modelModality, setModelModality] = useState<ModelModality>(creationConfig.model.modality);
  const [runtimeModels, setRuntimeModels] = useState<ModelDefinition[]>([]);
  const [localCodexModels, setLocalCodexModels] = useState<ModelDefinition[]>([]);
  const [runtimeModelsState, setRuntimeModelsState] = useState<"idle" | "loading" | "ready" | "unavailable">("idle");
  const [localCodexState, setLocalCodexState] = useState<"idle" | "loading" | "ready" | "unavailable">(
    (creationConfig.executor ?? "backend") === "local-codex" ? "loading" : "idle",
  );
  const [localCodexProbeRequested, setLocalCodexProbeRequested] = useState(
    (creationConfig.executor ?? "backend") === "local-codex",
  );
  const [runtimeModelsRefresh, setRuntimeModelsRefresh] = useState(0);
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
  const [assetManagerOpen, setAssetManagerOpen] = useState(false);
  const [assetManagerSource, setAssetManagerSource] = useState<AssetManagerSource>("personal");
  const [assetManagerQuery, setAssetManagerQuery] = useState("");
  const [assetManagerCategory, setAssetManagerCategory] = useState<AssetManagerCategory>("全部");
  const [assetManagerBatchMode, setAssetManagerBatchMode] = useState(false);
  const [assetManagerSelectedIds, setAssetManagerSelectedIds] = useState<string[]>([]);
  const [assetManagerNewMenuOpen, setAssetManagerNewMenuOpen] = useState(false);
  const [leftSidebarWidth, setLeftSidebarWidth] = useState(280);
  const [agentPanelWidth, setAgentPanelWidth] = useState(448);
  const [selectedCharacterId, setSelectedCharacterId] = useState(CHARACTER_PRESETS[0].id);
  const [characterRecentOnly, setCharacterRecentOnly] = useState(false);
  const [recentCharacterIds, setRecentCharacterIds] = useState<string[]>([CHARACTER_PRESETS[0].id]);
  const [historyMediaKind, setHistoryMediaKind] = useState<"image" | "video" | "audio">("image");
  const [, setSyncState] = useState<CloudWorkState>(work.cloudState);
  const [attachments, setAttachments] = useState<DraftAttachment[]>(storedDocument?.work.attachments ?? work.attachments);
  const attachmentsRef = useRef(attachments);
  const [cloudProjectId, setCloudProjectId] = useState(work.cloudProjectId ?? storedDocument?.work.cloudProjectId);
  const mountedRef = useRef(true);
  const workClearedRef = useRef(false);
  const activeWorkIdRef = useRef(work.id);
  const generationRequestsRef = useRef(new Map<string, string>());
  const generationAbortControllersRef = useRef(new Map<string, AbortController>());
  const materializedAgentJobsRef = useRef(new Set<string>());
  const promptOptimizationRequestsRef = useRef(new Map<string, string>());
  const promptOptimizationAbortControllersRef = useRef(new Map<string, AbortController>());
  const nodesRef = useRef(nodes);
  nodesRef.current = nodes;
  const edgesRef = useRef(edges);
  edgesRef.current = edges;
  const attachmentSyncQueueRef = useRef<Promise<void>>(Promise.resolve());
  const cloudDocumentWriteQueueRef = useRef<Promise<void>>(Promise.resolve());
  const unsyncedAttachmentIdsRef = useRef(new Set(
    isCloudConfigured() ? attachments.filter((attachment) => !attachment.assetId).map((attachment) => attachment.id) : [],
  ));
  const attachmentSyncTaskCountRef = useRef(0);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const promptRef = useRef<HTMLTextAreaElement | null>(null);
  const historyRef = useRef<GraphHistoryEntry[]>([cloneGraph(graph.nodes, graph.edges)]);
  const historyIndexRef = useRef(0);
  const restoringHistoryRef = useRef(false);
  const clipboardRef = useRef<GraphHistoryEntry | null>(null);
  const pasteCountRef = useRef(0);
  const flowInstanceRef = useRef<ReactFlowInstance<WorkflowNode, Edge> | null>(null);
  const characterCarouselRef = useRef<HTMLDivElement | null>(null);
  const [historyAvailability, setHistoryAvailability] = useState({ canUndo: false, canRedo: false });
  const activeDirectorNode = useMemo(() => directorStudioNodeId
    ? nodes.find((node) => node.id === directorStudioNodeId && node.data.variant === "director") ?? null
    : null, [directorStudioNodeId, nodes]);
  const activeDirectorScene = useMemo(() => activeDirectorNode
    ? normalizeDirectorScene(activeDirectorNode.data.directorScene)
    : null, [activeDirectorNode]);
  const activeScriptNode = useMemo(() => scriptWorkflowNodeId
    ? nodes.find((node) => node.id === scriptWorkflowNodeId && node.data.variant === "script-workflow") ?? null
    : null, [nodes, scriptWorkflowNodeId]);
  const activeScriptWorkbench = useMemo(() => activeScriptNode
    ? normalizeScriptWorkbench(activeScriptNode.data.scriptWorkbench)
    : null, [activeScriptNode]);
  const presentedScriptWorkbench = useMemo(() => activeScriptWorkbench ? {
    ...activeScriptWorkbench,
    assets: activeScriptWorkbench.assets.map((asset) => {
      const preview = scriptCanvasImages.find((image) => image.attachmentId === asset.attachmentId)?.imageUrl;
      return preview ? { ...asset, imageUrl: preview } : asset;
    }),
  } : null, [activeScriptWorkbench, scriptCanvasImages]);

  const cancelGenerationRequest = useCallback((nodeId: string) => {
    generationAbortControllersRef.current.get(nodeId)?.abort();
    generationAbortControllersRef.current.delete(nodeId);
    generationRequestsRef.current.delete(nodeId);
    promptOptimizationAbortControllersRef.current.get(nodeId)?.abort();
    promptOptimizationAbortControllersRef.current.delete(nodeId);
    promptOptimizationRequestsRef.current.delete(nodeId);
  }, []);

  const cancelAllGenerationRequests = useCallback(() => {
    generationAbortControllersRef.current.forEach((controller) => controller.abort());
    generationAbortControllersRef.current.clear();
    generationRequestsRef.current.clear();
    promptOptimizationAbortControllersRef.current.forEach((controller) => controller.abort());
    promptOptimizationAbortControllersRef.current.clear();
    promptOptimizationRequestsRef.current.clear();
  }, []);

  const enqueueCloudDocumentWrite = useCallback((projectId: string, workId: string) => {
    const isStale = () => workClearedRef.current || activeWorkIdRef.current !== workId;
    const writeLatest = async () => {
      if (isStale()) return;
      const document = loadLocalCanvasDocument(workId);
      if (!document) return;
      const missingIds = document.work.attachments.filter((attachment) => !attachment.assetId).map((attachment) => attachment.id);
      const hasUnsynced = missingIds.length > 0 || unsyncedAttachmentIdsRef.current.size > 0;
      const projectedState: CloudWorkState = attachmentSyncTaskCountRef.current > 0
        ? "syncing"
        : hasUnsynced ? "failed" : "synced";
      const projectedError = projectedState === "failed" ? `仍有 ${Math.max(missingIds.length, unsyncedAttachmentIdsRef.current.size)} 个素材未同步` : undefined;
      const documentToWrite: CanvasDocument = {
        ...document,
        work: {
          ...document.work,
          cloudProjectId: projectId,
          cloudState: projectedState,
          cloudError: projectedError,
        },
      };
      try {
        await saveCloudCanvasDocument(projectId, documentToWrite);
      } catch (error) {
        if (isStale()) return;
        const message = error instanceof Error ? error.message : String(error);
        const latestWork = loadWork(workId) ?? document.work;
        const failedWork: WebWork = {
          ...latestWork,
          cloudProjectId: projectId,
          cloudState: "failed",
          cloudError: message,
        };
        saveWork(failedWork);
        const latestDocument = loadLocalCanvasDocument(workId);
        if (latestDocument) {
          saveLocalCanvasDocument({
            ...latestDocument,
            work: {
              ...latestDocument.work,
              ...failedWork,
              attachments: mergeDraftAttachments(latestDocument.work.attachments, failedWork.attachments),
            },
          });
        }
        if (mountedRef.current && activeWorkIdRef.current === workId) setSyncState("failed");
        throw error;
      }
      if (isStale()) return;
      const latestDocument = loadLocalCanvasDocument(workId) ?? documentToWrite;
      const latestWork = loadWork(workId) ?? latestDocument.work;
      const latestAttachments = mergeDraftAttachments(latestWork.attachments, latestDocument.work.attachments);
      const latestMissingIds = latestAttachments.filter((attachment) => !attachment.assetId).map((attachment) => attachment.id);
      const stillUnsynced = latestMissingIds.length > 0 || unsyncedAttachmentIdsRef.current.size > 0;
      const finalState: CloudWorkState = attachmentSyncTaskCountRef.current > 0
        ? "syncing"
        : stillUnsynced ? "failed" : "synced";
      const finalError = finalState === "failed" ? `仍有 ${Math.max(latestMissingIds.length, unsyncedAttachmentIdsRef.current.size)} 个素材未同步` : undefined;
      const finalWork: WebWork = {
        ...latestWork,
        attachments: latestAttachments,
        cloudProjectId: projectId,
        cloudState: finalState,
        cloudError: finalError,
      };
      saveWork(finalWork);
      saveLocalCanvasDocument({
        ...latestDocument,
        work: {
          ...latestDocument.work,
          attachments: latestAttachments,
          cloudProjectId: projectId,
          cloudState: finalState,
          cloudError: finalError,
        },
      });
      if (mountedRef.current && activeWorkIdRef.current === workId) setSyncState(finalState);
    };
    const queued = cloudDocumentWriteQueueRef.current.then(writeLatest, writeLatest);
    cloudDocumentWriteQueueRef.current = queued.catch(() => undefined);
    return queued;
  }, []);

  const resolveCanvasAttachment = useCallback(async (attachmentId: string): Promise<File | undefined> => {
    const local = await localFile(attachmentId);
    if (local) return local;
    return undefined;
  }, []);

  useEffect(() => {
    if (!activeScriptNode || !activeScriptWorkbench) return undefined;
    const candidates = activeScriptWorkbench.assets.flatMap((asset) => {
      if (asset.source === "none" || hasDurableScriptWorkbenchByteVerification(asset.byte_verification, asset.sha256)) return [];
      const linkedAttachment = asset.attachmentId
        ?? (asset.nodeId ? nodes.find((node) => node.id === asset.nodeId)?.data.resultAttachmentId : undefined);
      return typeof linkedAttachment === "string" && linkedAttachment ? [{ assetId: asset.id, attachmentId: linkedAttachment, source: asset.source }] : [];
    });
    if (!candidates.length) return undefined;
    let cancelled = false;
    void Promise.all(candidates.map(async ({ assetId, attachmentId, source }) => {
      const file = await resolveCanvasAttachment(attachmentId);
      return file ? { assetId, attachmentId, source, sha256: await scriptWorkbenchBlobSha256(file) } : null;
    })).then((items) => {
      if (cancelled) return;
      const latestRaw = nodesRef.current.find((node) => node.id === activeScriptNode.id)?.data.scriptWorkbench;
      if (!latestRaw) return;
      let next = normalizeScriptWorkbench(latestRaw);
      let changed = false;
      for (const item of items) {
        if (!item) continue;
        const asset = next.assets.find((candidate) => candidate.id === item.assetId);
        if (
          !asset
          || asset.source !== item.source
          || (asset.attachmentId && asset.attachmentId !== item.attachmentId)
          || hasDurableScriptWorkbenchByteVerification(asset.byte_verification, asset.sha256)
        ) continue;
        next = updateScriptWorkbenchAsset(next, item.assetId, {
          attachmentId: item.attachmentId,
          sha256: item.sha256,
          status: "machine_complete",
          byte_verification: scriptWorkbenchAttachmentVerification(item.attachmentId, item.sha256),
        });
        changed = true;
      }
      if (changed) commitScriptWorkbench(activeScriptNode.id, next);
    });
    return () => { cancelled = true; };
  }, [activeScriptNode, activeScriptWorkbench, nodes, resolveCanvasAttachment]);

  useEffect(() => {
    if (!scriptWorkflowNodeId) {
      setScriptPromptModels([]);
      setScriptImageModels([]);
      return undefined;
    }
    const controller = new AbortController();
    void discoverCanvasModels(controller.signal).then((models) => {
      if (controller.signal.aborted) return;
      setScriptPromptModels(models.filter((model) => model.modality === "text").map((model) => ({
        id: model.id,
        label: generatorModelLabel(model.id),
        description: "本机共享模型 · 实际费用由代理提供方确认",
      })));
      setScriptImageModels(models.filter((model) => model.modality === "image").map((model) => ({
        id: model.id,
        label: generatorModelLabel(model.id),
        description: "本机共享模型 · 实际费用由代理提供方确认",
      })));
    }).catch((error) => {
      if (controller.signal.aborted) return;
      setScriptPromptModels([]);
      setScriptImageModels([]);
      setNotice(`无法读取本地共享模型：${error instanceof Error ? error.message : String(error)}`);
    });
    return () => controller.abort();
  }, [scriptWorkflowNodeId]);

  useEffect(() => {
    if (!scriptWorkflowNodeId) {
      setScriptCanvasImages([]);
      return undefined;
    }
    let active = true;
    const objectUrls: string[] = [];
    const nodeByAttachmentId = new Map<string, WorkflowNode>();
    nodes.forEach((node) => {
      if (node.data.kind !== "image" || typeof node.data.resultAttachmentId !== "string") return;
      nodeByAttachmentId.set(node.data.resultAttachmentId, node);
    });
    const candidates = attachments.filter((attachment) => attachment.type.startsWith("image/"));
    void Promise.all(candidates.map(async (attachment): Promise<ScriptWorkbenchCanvasImage> => {
      const sourceNode = nodeByAttachmentId.get(attachment.id);
      const file = await resolveCanvasAttachment(attachment.id);
      const imageUrl = file ? URL.createObjectURL(file) : undefined;
      if (imageUrl) objectUrls.push(imageUrl);
      return {
        id: attachment.id,
        name: sourceNode?.data.title ?? attachment.name,
        attachmentId: attachment.id,
        mimeType: attachment.type,
        ...(sourceNode ? { nodeId: sourceNode.id } : {}),
        ...(imageUrl ? { imageUrl } : {}),
      };
    })).then((items) => {
      if (active) setScriptCanvasImages(items);
    });
    return () => {
      active = false;
      objectUrls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [attachments, nodes, resolveCanvasAttachment, scriptWorkflowNodeId]);

  const suggestedSkills = useMemo(() => suggestedSkillsFor(work), [work]);
  const editingNode = editingNodeId ? nodes.find((node) => node.id === editingNodeId) ?? null : null;
  const selectedExecutor = creationConfig.executor ?? "backend";
  const selectableModelGroups = useMemo<Record<ModelModality, ModelDefinition[]>>(() => ({
    text: selectedExecutor === "local-codex"
      ? localCodexModels
      : runtimeModels.filter((model) => model.modality === "text"),
    image: selectedExecutor === "local-codex" ? [] : runtimeModels.filter((model) => model.modality === "image"),
    video: [],
    audio: [],
  }), [localCodexModels, runtimeModels, selectedExecutor]);
  const selectedModel = Object.values(selectableModelGroups).flat().find((model) => (
    model.id === creationConfig.model.modelId || model.modelId === creationConfig.model.modelId
  ));
  function chooseModelExecutor(next: WorkExecutor) {
    if (next === "local-codex") {
      setLocalCodexProbeRequested(true);
      setModelModality("text");
      setCreationConfig((current) => {
        const selected = localCodexModels.find((model) => model.id === current.model.modelId) ?? localCodexModels[0];
        return {
          ...current,
          executor: next,
          model: selected ? { modality: "text", modelId: selected.modelId ?? selected.id } : { modality: "text", modelId: "" },
        };
      });
      return;
    }
    const candidates = runtimeModels.filter((model) => model.modality === modelModality);
    const nextModality = candidates.length
      ? modelModality
      : runtimeModels.some((model) => model.modality === "text") ? "text" : "image";
    setModelModality(nextModality);
    setCreationConfig((current) => {
      const models = runtimeModels.filter((model) => model.modality === nextModality);
      const selected = models.find((model) => model.id === current.model.modelId) ?? models[0];
      return {
        ...current,
        executor: next,
        model: selected
          ? { modality: selected.modality, modelId: selected.modelId ?? selected.id, ...(selected.providerSpec ? { providerSpec: selected.providerSpec } : {}) }
          : { modality: nextModality, modelId: "" },
      };
    });
  }
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
  const visibleCharacterPresets = characterRecentOnly
    ? CHARACTER_PRESETS.filter((character) => recentCharacterIds.includes(character.id))
    : CHARACTER_PRESETS;
  const canvasSkillLibrary = useMemo(
    () => [
      ...AGENT_SKILL_LIBRARY.filter((skill) => !skill.line || skill.line === work.line),
      ...canvasCustomSkills.filter((skill) => !skill.line || skill.line === work.line),
    ],
    [canvasCustomSkills, work.line],
  );
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
  const visibleManagedAssets = useMemo(() => {
    const query = assetManagerQuery.trim().toLocaleLowerCase();
    return attachments.filter((attachment) => {
      if (assetManagerCategory !== "全部" && attachmentAssetTag(attachment) !== assetManagerCategory) return false;
      return !query || `${attachment.name} ${attachment.type}`.toLocaleLowerCase().includes(query);
    });
  }, [assetManagerCategory, assetManagerQuery, attachments]);
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
      if (libraryModelFilter !== "全部" && preset.model !== libraryModelFilter) return false;
      if (libraryCommercialOnly && !preset.commercial) return false;
      return !query || `${preset.name} ${preset.author} ${preset.model}`.toLocaleLowerCase().includes(query);
    });
  }, [activePresetLibrary, libraryCategory, libraryCommercialOnly, libraryFavorites, libraryModelFilter, libraryQuery, libraryRecent, libraryTab]);
  const composerAttachments = useMemo(
    () => attachments.filter((attachment) => composerAttachmentIds.includes(attachment.id)),
    [attachments, composerAttachmentIds],
  );
  const composerReady = Boolean(selectedModel)
    && Boolean(prompt.trim() || composerAttachments.length || activeSkill || selectedModel);
  const showAgentStarter = isNewConversation || !activeJob;
  const addActivity = useCallback((label: string) => {
    setActivity((items) => [{ id: crypto.randomUUID(), label, time: timestamp() }, ...items].slice(0, 30));
  }, []);

  useEffect(() => {
    activeWorkIdRef.current = work.id;
    workClearedRef.current = false;
    unsyncedAttachmentIdsRef.current.clear();
    if (isCloudConfigured()) {
      work.attachments.forEach((attachment) => {
        if (!attachment.assetId) unsyncedAttachmentIdsRef.current.add(attachment.id);
      });
    }
    cancelAllGenerationRequests();
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
    if ((nextConfig.executor ?? "backend") === "local-codex") setLocalCodexProbeRequested(true);
  }, [cancelAllGenerationRequests, graph, setEdges, setNodes, storedDocument, work.id, work.name, work.prompt]);

  useEffect(() => setSyncState(work.cloudState), [work.cloudState]);

  useEffect(() => {
    attachmentsRef.current = attachments;
    if (!isCloudConfigured()) {
      unsyncedAttachmentIdsRef.current.clear();
      return;
    }
    const currentIds = new Set(attachments.map((attachment) => attachment.id));
    attachments.forEach((attachment) => {
      if (attachment.assetId) unsyncedAttachmentIdsRef.current.delete(attachment.id);
      else unsyncedAttachmentIdsRef.current.add(attachment.id);
    });
    [...unsyncedAttachmentIdsRef.current].forEach((attachmentId) => {
      if (!currentIds.has(attachmentId)) unsyncedAttachmentIdsRef.current.delete(attachmentId);
    });
  }, [attachments]);

  useEffect(() => {
    if (!isCloudConfigured()) return undefined;
    let cancelled = false;
    let timer = 0;
    let attempts = 0;
    const retryDelays = [1_200, 5_000, 15_000, 45_000];
    const schedule = (delay: number) => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => void retryMissingAttachments(), delay);
    };
    const retryMissingAttachments = async () => {
      if (cancelled || workClearedRef.current || activeWorkIdRef.current !== work.id || attempts >= retryDelays.length) return;
      if (attachmentSyncTaskCountRef.current > 0) {
        schedule(1_200);
        return;
      }
      const missing = attachmentsRef.current.filter((attachment) => !attachment.assetId);
      if (!missing.length) return;
      const pending = (await Promise.all(missing.map(async (attachment) => {
        const file = await localFile(attachment.id);
        return file ? { ...attachment, file } : null;
      }))).filter((attachment): attachment is PendingAttachment => attachment !== null);
      if (cancelled || workClearedRef.current || activeWorkIdRef.current !== work.id || !pending.length) return;
      attempts += 1;
      await syncAttachmentsToCloud(pending, attachmentsRef.current, { silent: true });
      if (!cancelled && attachmentsRef.current.some((attachment) => !attachment.assetId) && attempts < retryDelays.length) {
        schedule(retryDelays[attempts]);
      }
    };
    const retryWhenOnline = () => {
      attempts = 0;
      schedule(0);
    };
    window.addEventListener("online", retryWhenOnline);
    schedule(retryDelays[0]);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      window.removeEventListener("online", retryWhenOnline);
    };
  }, [attachments, cloudProjectId, work.id]);

  useEffect(() => {
    if (work.cloudProjectId) setCloudProjectId(work.cloudProjectId);
    setAttachments((current) => mergeDraftAttachments(current, work.attachments));
  }, [work.attachments, work.cloudProjectId]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      cancelAllGenerationRequests();
    };
  }, [cancelAllGenerationRequests]);

  useEffect(() => {
    let disposed = false;
    let timer = 0;
    const refresh = async () => {
      const next = await createAgentGateway(creationConfig.executor ?? "backend");
      if (disposed) return;
      setGateway(next);
      timer = window.setTimeout(() => void refresh(), 12_000);
    };
    void refresh();
    return () => {
      disposed = true;
      window.clearTimeout(timer);
    };
  }, [creationConfig.executor]);

  useEffect(() => {
    const controller = new AbortController();
    setRuntimeModelsState("loading");
    if (localCodexProbeRequested) setLocalCodexState("loading");
    setRuntimeModels([]);
    if (localCodexProbeRequested) setLocalCodexModels([]);
    void Promise.allSettled([
      discoverCanvasModels(controller.signal),
      localCodexProbeRequested ? probeLocalCodex(controller.signal) : Promise.resolve(null),
    ]).then(([backendResult, localResult]) => {
        if (controller.signal.aborted) return;
        const discovered = backendResult.status === "fulfilled"
          ? runtimeModelDefinitions(backendResult.value)
          : [];
        const localDiscovered = localCodexProbeRequested && localResult.status === "fulfilled" && localResult.value
          ? localCodexModelDefinitions(localResult.value.models)
          : [];
        const localReady = localDiscovered.length > 0;
        setRuntimeModels(discovered);
        if (localCodexProbeRequested) setLocalCodexModels(localDiscovered);
        setRuntimeModelsState(backendResult.status === "fulfilled" ? "ready" : "unavailable");
        if (localCodexProbeRequested) setLocalCodexState(localReady ? "ready" : "unavailable");
        setCreationConfig((current) => {
          const currentExecutor = current.executor ?? "backend";
          const source = currentExecutor === "local-codex" ? localDiscovered : discovered;
          const exact = source.find((model) => model.id === current.model.modelId || model.modelId === current.model.modelId);
          const fallback = exact
            ?? source.find((model) => model.modality === current.model.modality)
            ?? source.find((model) => model.modality === "text")
            ?? source.find((model) => model.modality === "image")
            ?? (!current.executor
              ? discovered.find((model) => model.modality === "text") ?? localDiscovered[0] ?? discovered.find((model) => model.modality === "image")
              : undefined);
          if (!fallback) return current;
          const modelId = fallback.modelId ?? fallback.id;
          const executor: WorkExecutor = source.includes(fallback)
            ? currentExecutor
            : localDiscovered.includes(fallback) ? "local-codex" : "backend";
          if (current.model.modality === fallback.modality && current.model.modelId === modelId
            && !current.model.providerSpec && (current.executor ?? "backend") === executor) {
            return current;
          }
          return { ...current, executor, model: { modality: fallback.modality, modelId } };
        });
        setModelModality((current) => creationConfig.executor === "local-codex"
          ? "text"
          : discovered.some((model) => model.modality === current)
            ? current
            : discovered.some((model) => model.modality === "text") || localReady ? "text" : "image");
      });
    return () => controller.abort();
  }, [localCodexProbeRequested, runtimeModelsRefresh]);

  useEffect(() => {
    if (!notice) return undefined;
    const timer = window.setTimeout(() => setNotice(""), 2600);
    return () => window.clearTimeout(timer);
  }, [notice]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const updatedAt = new Date().toISOString();
      const latestWork = loadWork(work.id) ?? work;
      const stableAttachments = mergeDraftAttachments(latestWork.attachments, attachmentsRef.current, attachments);
      const hasUnsyncedAttachments = stableAttachments.some((attachment) => !attachment.assetId)
        || unsyncedAttachmentIdsRef.current.size > 0;
      const effectiveCloudProjectId = cloudProjectId ?? latestWork.cloudProjectId;
      const nextCloudState: CloudWorkState = effectiveCloudProjectId
        ? hasUnsyncedAttachments && attachmentSyncTaskCountRef.current === 0 ? "failed" : "syncing"
        : latestWork.cloudState;
      const nextWork: WebWork = {
        ...latestWork,
        name: workName.trim() || "unnamed",
        creationConfig,
        attachments: stableAttachments,
        ...(effectiveCloudProjectId ? { cloudProjectId: effectiveCloudProjectId } : {}),
        cloudState: nextCloudState,
        cloudError: nextCloudState === "failed" ? `仍有 ${Math.max(stableAttachments.filter((attachment) => !attachment.assetId).length, unsyncedAttachmentIdsRef.current.size)} 个素材未同步` : undefined,
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
      if (!effectiveCloudProjectId) return;
      setSyncState(nextCloudState);
      void enqueueCloudDocumentWrite(effectiveCloudProjectId, work.id).catch(() => undefined);
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
    enqueueCloudDocumentWrite,
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
      const stableNodes = nodes.map((node) => {
        if (!isTransientGenerationNode(node.data) || node.data.status !== "running") return node;
        const previousData = current?.nodes.find((item) => item.id === node.id)?.data;
        return {
          ...node,
          data: previousData ?? {
            ...node.data,
            status: "idle" as const,
            generationProgress: 0,
            generationRequestId: undefined,
            generationError: undefined,
          },
        };
      });
      if (current && graphSignature(current.nodes, current.edges) === graphSignature(stableNodes, edges)) return;
      const nextHistory = historyRef.current.slice(0, historyIndexRef.current + 1);
      nextHistory.push(cloneGraph(stableNodes, edges));
      historyRef.current = nextHistory.slice(-60);
      historyIndexRef.current = historyRef.current.length - 1;
      setHistoryAvailability({ canUndo: historyIndexRef.current > 0, canRedo: false });
    }, 260);
    return () => window.clearTimeout(timer);
  }, [edges, nodes]);

  const restoreHistory = useCallback((nextIndex: number) => {
    const entry = historyRef.current[nextIndex];
    if (!entry) return;
    cancelAllGenerationRequests();
    restoringHistoryRef.current = true;
    historyIndexRef.current = nextIndex;
    const graphCopy = cloneGraph(entry.nodes, entry.edges);
    setNodes(graphCopy.nodes.map((node) => isTransientGenerationNode(node.data) && node.data.status === "running"
      ? {
          ...node,
          data: {
            ...node.data,
            status: "failed",
            generationProgress: 0,
            generationRequestId: undefined,
            generationError: "生成已被撤销或重做操作中断，请重新提交。",
          },
        }
      : node));
    setEdges(graphCopy.edges);
    setSelectedNodeId(null);
    setHistoryAvailability({
      canUndo: nextIndex > 0,
      canRedo: nextIndex < historyRef.current.length - 1,
    });
  }, [cancelAllGenerationRequests, setEdges, setNodes]);

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
    const copyableNodes = selected.map((node) => ({ ...node, data: copyableWorkflowNodeData(node.data) }));
    clipboardRef.current = cloneGraph(
      copyableNodes,
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
      if (directorStudioNodeId) return;
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
        if (assetManagerOpen) {
          setAssetManagerOpen(false);
          setAssetManagerNewMenuOpen(false);
          setAssetManagerSelectedIds([]);
          return;
        }
        setDrawer(null);
        setOverlay(null);
        setRailMenu(null);
        setHelpPanel(null);
        setAddDrawerSubmenu(null);
        setLibraryInsertPoint(null);
        setLibraryDetail(null);
        setDirectorStudioNodeId(null);
        setDirectorReferenceNodeId(null);
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
  }, [assetManagerOpen, copySelectedNodes, directorStudioNodeId, duplicateSelectedNodes, pasteNodes, redoGraph, setNodes, undoGraph]);

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
    if (kind !== "tools") {
      setToolboxGuideOpen(false);
      setToolboxDetail(null);
      setToolboxClassicDetail(null);
    }
    setAddDrawerSubmenu(null);
    setOverlay(null);
    setRailMenu(null);
    setHelpPanel(null);
    setContextMenu(null);
    setOverviewNodeMenu(null);
    setOverviewFilterOpen(false);
    setComposerMenu(null);
  }

  function selectCharacter(characterId: string) {
    setSelectedCharacterId(characterId);
    setRecentCharacterIds((ids) => [characterId, ...ids.filter((id) => id !== characterId)].slice(0, 12));
  }

  function scrollCharacterCarousel(direction: -1 | 1) {
    characterCarouselRef.current?.scrollBy({ left: direction * 560, behavior: "smooth" });
  }

  function openAssetManager() {
    setAssetManagerOpen(true);
    setAssetManagerSource("personal");
    setAssetManagerQuery("");
    setAssetManagerCategory("全部");
    setAssetManagerBatchMode(false);
    setAssetManagerSelectedIds([]);
    setAssetManagerNewMenuOpen(false);
    setOverviewNodeMenu(null);
    setOverviewFilterOpen(false);
  }

  function toggleManagedAsset(assetId: string) {
    setAssetManagerSelectedIds((selected) => selected.includes(assetId)
      ? selected.filter((id) => id !== assetId)
      : [...selected, assetId]);
  }

  function sendManagedAssetsToCanvas() {
    const folderSelected = assetManagerSelectedIds.includes("folder:unclassified");
    const selectedAssets = folderSelected
      ? visibleManagedAssets
      : visibleManagedAssets.filter((attachment) => assetManagerSelectedIds.includes(attachment.id));
    if (!selectedAssets.length) {
      setNotice(folderSelected ? "待分类资产中暂无可发送素材" : "请先选择要发送的资产");
      return;
    }
    selectedAssets.forEach(addAttachmentNode);
    setDrawer("overview");
    setAssetManagerOpen(false);
    setAssetManagerSelectedIds([]);
    setNotice(`已发送 ${selectedAssets.length} 个资产到画布`);
  }

  function updateNodeData(nodeId: string, patch: Partial<WorkflowNodeData>) {
    setNodes((items) => items.map((node) => node.id === nodeId
      ? { ...node, data: { ...node.data, ...patch } }
      : node));
  }

  function openDirectorStudio(nodeId: string, options?: { reference?: boolean; runPrompt?: boolean }) {
    const node = nodes.find((item) => item.id === nodeId);
    if (!node || node.data.variant !== "director") return;
    if (!node.data.directorScene) {
      updateNodeData(nodeId, { directorScene: createDefaultDirectorScene() });
    }
    setDirectorReferenceNodeId(options?.reference ? nodeId : null);
    setDirectorRunPromptNodeId(options?.runPrompt ? nodeId : null);
    setDirectorStudioNodeId(nodeId);
  }

  function nextGeneratorTitle(kind: WorkflowNodeKind) {
    const label = kind === "text" ? "文本节点" : kind === "image" ? "图片节点" : kind === "video" ? "视频节点" : kind === "audio" ? "音频节点" : kind === "script" ? "脚本节点" : "合成节点";
    const count = nodes.filter((node) => node.data.kind === kind && node.data.variant === "libtv-generator").length;
    return `${label} ${count + 1}`;
  }

  function addLinkedNode(sourceId: string, kind: WorkflowNodeKind, title: string, description: string, prompt = "", variant: WorkflowNodeVariant = "default", selectNext = true): string | null {
    const source = nodes.find((node) => node.id === sourceId);
    if (!source) return null;
    const definition = nodeDefinition(kind);
    const id = `${kind}-${crypto.randomUUID()}`;
    const nextNode: WorkflowNode = {
      id,
      type: "workflow-node",
      selected: selectNext,
      position: { x: source.position.x + 430, y: source.position.y + 34 },
      data: {
        ...nodeRuntimeDefaults(kind, variant),
        kind,
        title,
        description,
        prompt,
        status: "idle",
        eyebrow: definition.eyebrow,
        variant,
        sourceNodeId: sourceId,
        sourceContext: String(source.data.resultText ?? source.data.generatedFromPrompt ?? source.data.prompt ?? source.data.description ?? ""),
      },
    };
    setNodes((items) => [...items.map((node) => ({ ...node, selected: selectNext ? false : node.id === sourceId })), nextNode]);
    setEdges((items) => addEdge(makeLibtvReferenceEdge(`edge-${crypto.randomUUID()}`, sourceId, id), items));
    setSelectedNodeId(selectNext ? id : sourceId);
    addActivity(`从「${source.data.title}」创建${title}`);
    return id;
  }

  function deriveWorkflowNode(sourceId: string, kind: WorkflowNodeKind, variant: WorkflowNodeVariant = "default") {
    const source = nodes.find((node) => node.id === sourceId);
    if (!source) return;
    const context = String(source.data.resultText ?? source.data.generatedFromPrompt ?? source.data.prompt ?? source.data.description ?? "").trim();
    const prompt = kind === "image"
      ? context
      : kind === "text"
        ? (context ? `基于以下内容继续创作：\n\n${context}` : "")
        : context;
    const title = variant === "director" ? "导演台" : variant === "script-new" ? "脚本节点" : variant === "libtv-generator" ? nextGeneratorTitle(kind) : nodeDefinition(kind).label;
    const description = kind === "image" ? "引用上游内容生成图片" : kind === "text" ? "引用上游内容继续生成文本" : `引用「${source.data.title}」继续生成`;
    addLinkedNode(sourceId, kind, title, description, prompt, variant, variant !== "libtv-generator");
  }

  function sendDirectorShotToCanvas(sourceNodeId: string, shot: DirectorShot, camera: DirectorCamera) {
    const source = nodes.find((node) => node.id === sourceNodeId);
    if (!source) return;
    const imageNodeId = `image-${crypto.randomUUID()}`;
    const directorAspect = source.data.directorScene?.aspectRatio;
    const imageNode: WorkflowNode = {
      id: imageNodeId,
      type: "workflow-node",
      selected: true,
      position: { x: source.position.x + 430, y: source.position.y + 34 },
      data: {
        ...nodeRuntimeDefaults("image", "libtv-generator"),
        kind: "image",
        title: nextGeneratorTitle("image"),
        description: `${camera.name} · ${shot.width} × ${shot.height}`,
        prompt: String(source.data.prompt ?? ""),
        status: "done",
        eyebrow: nodeDefinition("image").eyebrow,
        variant: "libtv-generator",
        sourceNodeId,
        sourceContext: String(source.data.prompt ?? source.data.description ?? ""),
        generationProgress: 100,
        resultAttachmentId: shot.attachmentId,
        resultMimeType: shot.mimeType,
        generatedFromPrompt: String(source.data.prompt ?? ""),
        generatedWithModel: "Director 3D",
        assetName: `${shot.name}.png`,
        aspectRatio: directorAspect && directorAspect !== "adaptive" ? directorAspect : "16:9",
      },
    };
    const nextNodes = [...nodes.map((node) => ({ ...node, selected: false })), imageNode];
    const nextEdges = addEdge(makeLibtvReferenceEdge(`edge-${crypto.randomUUID()}`, sourceNodeId, imageNodeId), edges);
    setNodes(nextNodes);
    setEdges(nextEdges);
    setSelectedNodeId(imageNodeId);
    addActivity(`从「${source.data.title}」创建${imageNode.data.title}`);
    void persistGeneratorNodeSnapshot(imageNodeId, {}, attachmentsRef.current, nextNodes, nextEdges, { replaceGraph: true });
    setNotice(`已将「${shot.name}」发送到画布`);
  }

  function handleNodeQuickAction(nodeId: string, action: string) {
    const node = nodes.find((item) => item.id === nodeId);
    if (!node) return;
    const currentPrompt = typeof node.data.prompt === "string" ? node.data.prompt : "";
    if (action === "优化提示词") {
      const sourcePrompt = currentPrompt.trim();
      if (!sourcePrompt) {
        setNotice("请先输入需要优化的提示词");
        return;
      }
      promptOptimizationAbortControllersRef.current.get(nodeId)?.abort();
      const controller = new AbortController();
      const requestId = crypto.randomUUID();
      promptOptimizationAbortControllersRef.current.set(nodeId, controller);
      promptOptimizationRequestsRef.current.set(nodeId, requestId);
      setNotice("正在使用共享 GPT 优化提示词…");
      void (async () => {
        try {
          const models = (await discoverCanvasModels(controller.signal)).filter((model) => model.modality === "text");
          const requestedModel = typeof node.data.model === "string" ? models.find((model) => model.id === node.data.model) : undefined;
          const model = requestedModel ?? ["gpt-5.6-terra", "gpt-5.6-sol", "gpt-5.6-luna", "gpt-5.5", "gpt-5.4-mini"]
            .map((id) => models.find((candidate) => candidate.id === id))
            .find(Boolean) ?? models[0];
          if (!model) throw new Error("cli-proxy-api 没有共享可用的 GPT 文本模型");
          const result = await generateCanvasContent({
            modality: "text",
            model: model.id,
            signal: controller.signal,
            prompt: [
              "你是专业的 AI 影视生成提示词编辑器。只输出优化后的中文提示词，不要标题、引号、解释或 Markdown。",
              "保持用户原意和主体身份，补全可执行的主体、动作、场景、镜头、构图、光线、色彩与质感；不要凭空加入用户未要求的角色、品牌或文字。",
              `原提示词：${sourcePrompt}`,
            ].join("\n"),
          });
          if (result.modality !== "text") throw new Error("GPT 模型没有返回优化文本");
          if (promptOptimizationRequestsRef.current.get(nodeId) !== requestId || controller.signal.aborted) return;
          const latestNode = nodesRef.current.find((item) => item.id === nodeId);
          if (!latestNode || String(latestNode.data.prompt ?? "").trim() !== sourcePrompt) {
            setNotice("提示词已在优化期间改变，本次结果未覆盖当前输入");
            return;
          }
          const optimizedPrompt = result.text.trim().slice(0, 12_000);
          if (!optimizedPrompt) throw new Error("GPT 返回了空提示词");
          updateNodeData(nodeId, { prompt: optimizedPrompt });
          await persistGeneratorNodeSnapshot(nodeId, { prompt: optimizedPrompt });
          setNotice(optimizedPrompt === sourcePrompt ? "提示词已经足够清晰" : "提示词已由共享 GPT 优化");
        } catch (error) {
          if (!controller.signal.aborted) setNotice(`提示词优化失败：${error instanceof Error ? error.message : String(error)}`);
        } finally {
          if (promptOptimizationRequestsRef.current.get(nodeId) === requestId) {
            promptOptimizationRequestsRef.current.delete(nodeId);
            promptOptimizationAbortControllersRef.current.delete(nodeId);
          }
        }
      })();
      return;
    }
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

  async function persistGeneratorNodeSnapshot(
    nodeId: string,
    patch: Partial<WorkflowNodeData>,
    nextAttachments = attachmentsRef.current,
    snapshotNodes = nodes,
    snapshotEdges = edges,
    options: { writeCloud?: boolean; replaceGraph?: boolean } = {},
  ) {
    if (workClearedRef.current || activeWorkIdRef.current !== work.id) return;
    if (!options.replaceGraph && !nodesRef.current.some((item) => item.id === nodeId)) return;
    const current = loadLocalCanvasDocument(work.id) ?? {
      schemaVersion: 1,
      work,
      nodes: snapshotNodes.map((item) => ({
        id: item.id,
        type: item.type,
        position: item.position,
        data: item.data,
      })),
      edges: snapshotEdges.map((edge) => ({
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
      updatedAt: new Date().toISOString(),
    } satisfies CanvasDocument;
    const mergedAttachments = mergeDraftAttachments(current.work.attachments, nextAttachments);
    const nextDocumentWork: WebWork = {
      ...current.work,
      name: workName.trim() || "unnamed",
      creationConfig,
      attachments: mergedAttachments,
      ...(cloudProjectId ? { cloudProjectId } : {}),
    };
    const replaceGraph = options.replaceGraph === true || !current.nodes.some((item) => item.id === nodeId);
    saveLocalCanvasDocument({
      ...current,
      work: nextDocumentWork,
      nodes: replaceGraph
        ? snapshotNodes.map((item) => ({
            id: item.id,
            type: item.type,
            position: item.position,
            data: item.id === nodeId ? { ...item.data, ...patch } : item.data,
          }))
        : current.nodes.map((item) => item.id === nodeId ? { ...item, data: { ...item.data, ...patch } } : item),
      edges: replaceGraph
        ? snapshotEdges.map((edge) => ({
            id: edge.id,
            source: edge.source,
            target: edge.target,
            sourceHandle: edge.sourceHandle,
            targetHandle: edge.targetHandle,
            type: edge.type,
            animated: edge.animated,
          }))
        : current.edges,
      updatedAt: new Date().toISOString(),
    });
    saveWork(nextDocumentWork);
    if (cloudProjectId && options.writeCloud !== false) await enqueueCloudDocumentWrite(cloudProjectId, work.id).catch(() => undefined);
  }

  function syncAttachmentsToCloud(
    pendingAttachments: PendingAttachment[],
    nextAttachments: DraftAttachment[],
    messages?: { success?: string; local?: string; failurePrefix?: string; silent?: boolean },
  ) {
    if (!isCloudConfigured() || !pendingAttachments.length) return Promise.resolve();
    const syncWorkId = work.id;
    const isStale = () => workClearedRef.current || activeWorkIdRef.current !== syncWorkId;
    pendingAttachments.forEach((attachment) => unsyncedAttachmentIdsRef.current.add(attachment.id));
    attachmentSyncTaskCountRef.current += 1;
    let taskReleased = false;
    const releaseTask = () => {
      if (taskReleased) return;
      taskReleased = true;
      attachmentSyncTaskCountRef.current = Math.max(0, attachmentSyncTaskCountRef.current - 1);
    };
    const performSync = async () => {
      try {
        if (isStale()) return;
        const currentWork = loadWork(syncWorkId) ?? work;
        const queuedAttachments = mergeDraftAttachments(currentWork.attachments, attachmentsRef.current, nextAttachments);
        const retryById = new Map(pendingAttachments.map((attachment) => [attachment.id, attachment]));
        for (const attachment of queuedAttachments) {
          if (attachment.assetId || retryById.has(attachment.id)) continue;
          const file = await localFile(attachment.id);
          if (file) retryById.set(attachment.id, { ...attachment, file });
        }
        if (isStale()) return;
        const attachmentsToUpload = [...retryById.values()];
        attachmentsToUpload.forEach((attachment) => unsyncedAttachmentIdsRef.current.add(attachment.id));
        const nextWork: WebWork = {
          ...currentWork,
          attachments: queuedAttachments,
          ...((currentWork.cloudProjectId ?? cloudProjectId) ? { cloudProjectId: currentWork.cloudProjectId ?? cloudProjectId } : {}),
          cloudState: "syncing",
          cloudError: undefined,
        };
        if (mountedRef.current) setSyncState("syncing");
        saveWork(nextWork);
        const result = await persistWorkToCloud(nextWork, attachmentsToUpload);
        if (isStale()) return;
        const pendingIds = new Set(attachmentsToUpload.map((attachment) => attachment.id));
        const uploaded = result.work.attachments.filter((item) => pendingIds.has(item.id) && item.assetId);
        const mergedAttachments = mergeDraftAttachments(
          attachmentsRef.current,
          queuedAttachments,
          nextAttachments,
          uploaded,
        );
        attachmentsRef.current = mergedAttachments;
        uploaded.forEach((attachment) => unsyncedAttachmentIdsRef.current.delete(attachment.id));
        const currentIds = new Set(mergedAttachments.map((attachment) => attachment.id));
        mergedAttachments.forEach((attachment) => {
          if (attachment.assetId) unsyncedAttachmentIdsRef.current.delete(attachment.id);
          else unsyncedAttachmentIdsRef.current.add(attachment.id);
        });
        [...unsyncedAttachmentIdsRef.current].forEach((attachmentId) => {
          if (!currentIds.has(attachmentId)) unsyncedAttachmentIdsRef.current.delete(attachmentId);
        });
        releaseTask();
        const latestWork = loadWork(syncWorkId) ?? nextWork;
        const incompleteCount = mergedAttachments.filter((attachment) => !attachment.assetId).length;
        const finalCloudState: CloudWorkState = result.state === "auth-required"
          ? "auth-required"
          : result.state === "local"
            ? "local"
            : attachmentSyncTaskCountRef.current > 0
              ? "syncing"
              : incompleteCount || unsyncedAttachmentIdsRef.current.size ? "failed" : "synced";
        const finalCloudError = finalCloudState === "failed"
          ? `仍有 ${Math.max(incompleteCount, unsyncedAttachmentIdsRef.current.size)} 个素材未同步`
          : undefined;
        const persistedWork: WebWork = {
          ...latestWork,
          attachments: mergeDraftAttachments(latestWork.attachments, mergedAttachments),
          ...(result.work.cloudProjectId ? { cloudProjectId: result.work.cloudProjectId } : {}),
          cloudState: finalCloudState,
          cloudError: finalCloudError,
        };
        saveWork(persistedWork);

        const currentDocument = loadLocalCanvasDocument(syncWorkId);
        const persistedDocument = currentDocument ? {
          ...currentDocument,
          work: {
            ...currentDocument.work,
            name: persistedWork.name,
            attachments: mergeDraftAttachments(currentDocument.work.attachments, mergedAttachments),
            ...(persistedWork.cloudProjectId ? { cloudProjectId: persistedWork.cloudProjectId } : {}),
            cloudState: persistedWork.cloudState,
            cloudError: persistedWork.cloudError,
          },
          updatedAt: new Date().toISOString(),
        } satisfies CanvasDocument : null;
        if (persistedDocument) saveLocalCanvasDocument(persistedDocument);

        if (mountedRef.current) {
          setAttachments(mergedAttachments);
          if (persistedWork.cloudProjectId) setCloudProjectId(persistedWork.cloudProjectId);
        }
        if (persistedWork.cloudProjectId && persistedDocument) {
          await enqueueCloudDocumentWrite(persistedWork.cloudProjectId, syncWorkId);
        }
        if (!isStale() && mountedRef.current) {
          setSyncState(persistedWork.cloudState);
          if (!messages?.silent) {
            if (persistedWork.cloudState === "synced" && messages?.success) setNotice(messages.success);
            else if ((persistedWork.cloudState === "auth-required" || persistedWork.cloudState === "local") && messages?.local) setNotice(messages.local);
            else if (persistedWork.cloudState === "failed") setNotice(`${messages?.failurePrefix ?? "素材已保存在本机，云同步失败"}：${persistedWork.cloudError}`);
          }
        }
      } catch (error) {
        if (isStale()) return;
        const message = error instanceof Error ? error.message : String(error);
        const latestWork = loadWork(syncWorkId) ?? work;
        const failedWork: WebWork = {
          ...latestWork,
          attachments: mergeDraftAttachments(latestWork.attachments, attachmentsRef.current, nextAttachments),
          cloudState: "failed",
          cloudError: message,
        };
        saveWork(failedWork);
        const currentDocument = loadLocalCanvasDocument(syncWorkId);
        if (currentDocument) {
          saveLocalCanvasDocument({
            ...currentDocument,
            work: {
              ...currentDocument.work,
              attachments: mergeDraftAttachments(currentDocument.work.attachments, attachmentsRef.current),
              ...(failedWork.cloudProjectId ? { cloudProjectId: failedWork.cloudProjectId } : {}),
              cloudState: "failed",
              cloudError: message,
            },
            updatedAt: new Date().toISOString(),
          });
        }
        if (mountedRef.current) {
          setSyncState("failed");
          if (!messages?.silent) setNotice(`${messages?.failurePrefix ?? "素材已保存在本机，云同步失败"}：${message}`);
        }
      } finally {
        releaseTask();
      }
    };
    const queued = attachmentSyncQueueRef.current.then(performSync, performSync);
    attachmentSyncQueueRef.current = queued.catch(() => undefined);
    return queued;
  }

  async function resolveSharedCanvasModel(
    modality: "text" | "image",
    requestedModel: string | undefined,
    signal: AbortSignal,
  ): Promise<string> {
    const models = (await discoverCanvasModels(signal)).filter((model) => model.modality === modality);
    if (!models.length) throw new Error(`cli-proxy-api 没有共享可用的${modality === "image" ? "图片" : "文本"}模型`);
    const preferences = modality === "image"
      ? GENERATOR_MODEL_OPTIONS.image.map((model) => model.id)
      : GENERATOR_MODEL_OPTIONS.text.map((model) => model.id);
    return models.find((model) => model.id === requestedModel)?.id
      ?? preferences.find((modelId) => models.some((model) => model.id === modelId))
      ?? models[0].id;
  }

  async function runBackendSkillText(
    skillId: string,
    promptText: string,
    signal: AbortSignal,
    context: Record<string, unknown>,
  ): Promise<{ text: string; model: string }> {
    const model = await resolveSharedCanvasModel("text", creationConfig.model.modelId, signal);
    let submissionGateway = gateway?.mode === "backend" ? gateway : await createAgentGateway("backend");
    if (submissionGateway.mode === "demo") submissionGateway = await createAgentGateway("backend");
    if (submissionGateway.mode === "demo") throw new Error("后端 AI / Skill 服务尚未就绪");
    if (!mountedRef.current || signal.aborted) throw new DOMException("Skill 运行已取消", "AbortError");
    setGateway(submissionGateway);

    const effectiveWork: WebWork = {
      ...work,
      name: workName.trim() || "unnamed",
      creationConfig: {
        ...creationConfig,
        skillId,
        executor: "backend",
        model: { modality: "text", modelId: model },
      },
      attachments: [],
      ...(cloudProjectId ? { cloudProjectId } : {}),
    };
    let current = await submissionGateway.submit({
      work: effectiveWork,
      prompt: promptText,
      skillId,
      context,
    });
    setActiveJob(current);
    updateRun(current, promptText);

    if (submissionGateway.status) {
      for (let attempt = 0; attempt < 300 && (current.state === "queued" || current.state === "running"); attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 1200));
        if (!mountedRef.current || signal.aborted) throw new DOMException("Skill 运行已取消", "AbortError");
        current = await submissionGateway.status(current.id);
        setActiveJob(current);
        updateRun(current, promptText);
      }
    }
    if (current.state !== "succeeded") {
      throw new Error(current.state === "queued" || current.state === "running"
        ? "后端 Skill 运行超时"
        : current.message || `后端 Skill 任务${current.state}`);
    }
    const text = current.output?.trim()
      || current.artifacts?.find((artifact) => artifact.kind === "text" && artifact.text?.trim())?.text?.trim()
      || "";
    if (!text) throw new Error("后端 Skill 没有返回文本结果");
    return { text, model };
  }

  function scriptSourceText(node: WorkflowNode): string {
    const incoming = edgesRef.current
      .filter((edge) => edge.target === node.id)
      .map((edge) => nodesRef.current.find((candidate) => candidate.id === edge.source))
      .filter((candidate): candidate is WorkflowNode => Boolean(candidate));
    const blocks = [
      typeof node.data.sourceContext === "string" ? node.data.sourceContext : "",
      ...incoming.map((candidate) => String(
        candidate.data.resultText
        ?? candidate.data.generatedFromPrompt
        ?? candidate.data.prompt
        ?? candidate.data.description
        ?? "",
      )),
    ].map((value) => value.trim()).filter(Boolean);
    const combined = [...new Set(blocks)].join("\n\n--- 上游素材 ---\n\n");
    if (combined.length <= 14_000) return combined;
    return `${combined.slice(0, 9_000)}\n\n……（中段因本地模型输入上限省略）……\n\n${combined.slice(-5_000)}`;
  }

  function setGraphImmediately(nextNodes: WorkflowNode[], nextEdges: Edge[]) {
    nodesRef.current = nextNodes;
    edgesRef.current = nextEdges;
    setNodes(nextNodes);
    setEdges(nextEdges);
  }

  function commitScriptWorkbench(nodeId: string, nextWorkbench: ScriptWorkbenchDocument, writeCloud = false) {
    const normalized = normalizeScriptWorkbench(nextWorkbench);
    const previousRaw = nodesRef.current.find((node) => node.id === nodeId)?.data.scriptWorkbench;
    const previousHash = previousRaw ? normalizeScriptWorkbench(previousRaw).content_sha256 : "";
    const authoringChanged = Boolean(previousHash && previousHash !== normalized.content_sha256);
    const patch: Partial<WorkflowNodeData> = {
      scriptWorkbench: normalized,
      title: normalized.title,
      description: `${normalized.shots.length}个镜头 · ${normalized.assets.length}个资产 · 状态 ${normalized.state}`,
      assetName: `${normalized.shots.length}个镜头`,
      status: "done",
    };
    const nextNodes = nodesRef.current.map((node) => {
      if (node.id === nodeId) return { ...node, data: { ...node.data, ...patch } };
      const linked = node.data.scriptSourceNodeId === nodeId || node.data.storyboardSourceNodeId === nodeId;
      const isRetainedAssetSource = normalized.assets.some((asset) => asset.nodeId === node.id && asset.sha256);
      if (!authoringChanged || !linked || isRetainedAssetSource) return node;
      cancelGenerationRequest(node.id);
      return {
        ...node,
        data: {
          ...node.data,
          status: node.data.kind === "video" ? "ready" as const : "idle" as const,
          generationProgress: 0,
          generationRequestId: undefined,
          resultAttachmentId: undefined,
          resultMimeType: undefined,
          resultText: undefined,
          generatedFromPrompt: undefined,
          assetName: undefined,
          generationError: "上游制作内容已更新，请按新内容哈希同步后重新生成。",
        },
      };
    });
    nodesRef.current = nextNodes;
    setNodes(nextNodes);
    void persistGeneratorNodeSnapshot(
      nodeId,
      patch,
      attachmentsRef.current,
      nextNodes,
      edgesRef.current,
      { writeCloud, replaceGraph: true },
    );
  }

  async function parseOrRepairScriptWorkbench(
    modelText: string,
    model: string,
    signal: AbortSignal,
  ): Promise<ScriptWorkbenchDocument> {
    try {
      const parsed = parseScriptWorkbenchModelOutput(modelText);
      if (!parsed.assets.length) throw new Error("脚本没有生成角色、场景或道具资产");
      return parsed;
    } catch (firstError) {
      const repair = await generateCanvasContent({
        modality: "text",
        model,
        signal,
        prompt: [
          "修复下面的故事脚本 JSON。严格按给定契约补齐字段、至少保留一个镜头和一个真实待准备资产；只返回 JSON，不要解释。",
          SCRIPT_WORKBENCH_MODEL_JSON_INSTRUCTIONS,
          `首次解析错误：${firstError instanceof Error ? firstError.message : String(firstError)}`,
          "待修复内容：",
          modelText.slice(0, 16_000),
        ].join("\n\n"),
      });
      if (repair.modality !== "text") throw new Error("文本模型没有返回修复结果");
      const parsed = parseScriptWorkbenchModelOutput(repair.text);
      if (!parsed.assets.length) throw new Error("修复后的脚本仍没有可准备资产");
      return parsed;
    }
  }

  async function runScriptWorkbenchGeneratorNode(node: WorkflowNode, force = false) {
    const latestSource = nodesRef.current.find((candidate) => candidate.id === node.id);
    if (!latestSource || latestSource.data.status === "running") return;
    const existingResult = latestSource.data.variant === "script-workflow"
      ? latestSource
      : nodesRef.current.find((candidate) => candidate.data.variant === "script-workflow" && candidate.data.sourceNodeId === node.id);
    if (existingResult && !force) {
      const selected = nodesRef.current.map((candidate) => ({ ...candidate, selected: candidate.id === existingResult.id }));
      nodesRef.current = selected;
      setNodes(selected);
      setSelectedNodeId(existingResult.id);
      setNotice("脚本已生成，打开结果节点继续编辑");
      return;
    }

    const userPrompt = String(latestSource.data.prompt ?? "").trim().slice(0, 4_000);
    const sourceText = scriptSourceText(latestSource);
    if (!userPrompt && !sourceText) {
      setNotice("请先输入故事内容或连接一个文本节点");
      return;
    }

    const requestId = crypto.randomUUID();
    cancelGenerationRequest(node.id);
    const controller = new AbortController();
    generationRequestsRef.current.set(node.id, requestId);
    generationAbortControllersRef.current.set(node.id, controller);
    const runningPatch: Partial<WorkflowNodeData> = {
      status: "running",
      variant: "script-new",
      title: "脚本生成器",
      generationProgress: 4,
      generationError: undefined,
      generationRequestId: requestId,
      skillId: APP_CANVAS_SKILL_IDS.scriptWorkbench,
      skillPath: `skills/app/${APP_CANVAS_SKILL_IDS.scriptWorkbench}/SKILL.md`,
    };
    const runningNodes = nodesRef.current.map((candidate) => candidate.id === node.id
      ? { ...candidate, data: { ...candidate.data, ...runningPatch } }
      : candidate);
    nodesRef.current = runningNodes;
    setNodes(runningNodes);
    void persistGeneratorNodeSnapshot(node.id, runningPatch, attachmentsRef.current, runningNodes, edgesRef.current, { writeCloud: false });
    addActivity(`开始通过后端 Skill 拆解「${latestSource.data.title}」`);
    setNotice(`正在通过 ${APP_CANVAS_SKILL_IDS.scriptWorkbench} 生成可编辑镜头…`);

    try {
      const generation = await runBackendSkillText(
        APP_CANVAS_SKILL_IDS.scriptWorkbench,
        [
          "你是专业漫剧故事脚本与分镜导演。把用户故事拆成可持续编辑、生成、返修与质检的制作工作台 authoring 数据。",
          "要求：通常生成 8–20 个镜头；每镜 5–15 秒；镜头描述具体可视；资产去重并覆盖主要角色、场景、关键道具；不要复制不在原故事中的受版权保护内容。",
          "final_prompt 先留空，资产必须是 status=pending、source=none。",
          SCRIPT_WORKBENCH_MODEL_JSON_INSTRUCTIONS,
          `用户操作指令：${userPrompt || "根据上游故事生成完整分镜脚本"}`,
          sourceText ? `故事与上游素材：\n${sourceText}` : "",
        ].filter(Boolean).join("\n\n"),
        controller.signal,
        { sourceNodeId: node.id, workflow: "script-workbench" },
      );
      if (generationRequestsRef.current.get(node.id) !== requestId) return;
      const workbench = await parseOrRepairScriptWorkbench(generation.text, generation.model, controller.signal);
      const issues = validateScriptWorkbench(workbench);
      if (issues.length) throw new Error(`脚本合同校验失败：${issues.slice(0, 3).map((issue) => `${issue.path} ${issue.message}`).join("；")}`);
      if (!mountedRef.current || generationRequestsRef.current.get(node.id) !== requestId) return;

      const currentNodes = nodesRef.current;
      const resultData: WorkflowNodeData = {
        ...latestSource.data,
        kind: "script",
        title: workbench.title,
        description: `${workbench.shots.length}个镜头 · ${workbench.assets.length}个资产 · 状态 ${workbench.state}`,
        status: "done",
        eyebrow: "脚本",
        variant: "script-workflow",
        skillId: APP_CANVAS_SKILL_IDS.scriptWorkbench,
        skillPath: `skills/app/${APP_CANVAS_SKILL_IDS.scriptWorkbench}/SKILL.md`,
        assetName: `${workbench.shots.length}个镜头`,
        scriptWorkbench: workbench,
        generatedWithModel: generation.model,
        generatedFromPrompt: userPrompt,
        generationProgress: 100,
        generationRequestId: undefined,
        generationError: undefined,
        model: generation.model,
      };
      const nextNodes = currentNodes.map((candidate) => candidate.id === node.id
        ? { ...candidate, selected: true, data: resultData }
        : { ...candidate, selected: false });
      setGraphImmediately(nextNodes, edgesRef.current);
      setSelectedNodeId(node.id);
      await persistGeneratorNodeSnapshot(node.id, resultData, attachmentsRef.current, nextNodes, edgesRef.current, { replaceGraph: true });
      generationRequestsRef.current.delete(node.id);
      generationAbortControllersRef.current.delete(node.id);
      addActivity(`完成「${workbench.title}」脚本拆镜`);
      setNotice(`已生成 ${workbench.shots.length} 个镜头，打开脚本节点继续`);
      window.requestAnimationFrame(() => void flowInstanceRef.current?.fitView({ nodes: [{ id: node.id }], padding: .38, maxZoom: 1, duration: 300 }));
    } catch (error) {
      if (!mountedRef.current || generationRequestsRef.current.get(node.id) !== requestId) return;
      generationRequestsRef.current.delete(node.id);
      generationAbortControllersRef.current.delete(node.id);
      const message = isCanvasGenerationError(error) ? error.message : error instanceof Error ? error.message : "脚本生成失败";
      const failedPatch: Partial<WorkflowNodeData> = {
        status: latestSource.data.scriptWorkbench ? "done" : "failed",
        ...(latestSource.data.scriptWorkbench ? {
          variant: "script-workflow",
          title: normalizeScriptWorkbench(latestSource.data.scriptWorkbench).title,
        } : {}),
        generationProgress: 0,
        generationRequestId: undefined,
        generationError: message,
      };
      const nextNodes = nodesRef.current.map((candidate) => candidate.id === node.id
        ? { ...candidate, data: { ...candidate.data, ...failedPatch } }
        : candidate);
      nodesRef.current = nextNodes;
      setNodes(nextNodes);
      void persistGeneratorNodeSnapshot(node.id, failedPatch, attachmentsRef.current, nextNodes, edgesRef.current);
      addActivity(`「${latestSource.data.title}」脚本生成失败`);
      setNotice(message);
    }
  }

  async function generatorReferenceInput(
    node: WorkflowNode,
    signal: AbortSignal,
  ): Promise<{ base64: string; mimeType: string } | undefined> {
    const directIds = Array.isArray(node.data.referenceAttachmentIds)
      ? node.data.referenceAttachmentIds.filter((value): value is string => typeof value === "string" && Boolean(value))
      : [];
    const nodeIds = Array.isArray(node.data.referenceNodeIds)
      ? node.data.referenceNodeIds.filter((value): value is string => typeof value === "string" && Boolean(value))
      : [];
    let imageUrls = Array.isArray(node.data.referenceImageUrls)
      ? node.data.referenceImageUrls.filter((value): value is string => typeof value === "string" && Boolean(value))
      : [];
    const linkedIds = nodeIds.flatMap((nodeId) => {
      const attachmentId = nodesRef.current.find((candidate) => candidate.id === nodeId)?.data.resultAttachmentId;
      return typeof attachmentId === "string" && attachmentId ? [attachmentId] : [];
    });
    let attachmentIds = [...new Set([...directIds, ...linkedIds])];
    const scriptAssetIds = Array.isArray(node.data.scriptAssetIds)
      ? node.data.scriptAssetIds.filter((value): value is string => typeof value === "string" && Boolean(value))
      : [];
    const scriptSourceNodeId = String(node.data.storyboardSourceNodeId ?? node.data.scriptSourceNodeId ?? node.data.sourceNodeId ?? "");
    const scriptSource = scriptSourceNodeId
      ? nodesRef.current.find((candidate) => candidate.id === scriptSourceNodeId)
      : undefined;
    if (scriptAssetIds.length && scriptSource?.data.scriptWorkbench) {
      const workbench = normalizeScriptWorkbench(scriptSource.data.scriptWorkbench);
      const selectedAssets = scriptAssetIds.flatMap((assetId) => {
        const asset = workbench.assets.find((candidate) => candidate.id === assetId);
        return asset ? [asset] : [];
      });
      const missingAssets: string[] = [];
      const currentAttachmentIds: string[] = [];
      const currentImageUrls: string[] = [];
      for (const asset of selectedAssets) {
        const linkedAttachmentId = asset.nodeId
          ? String(nodesRef.current.find((candidate) => candidate.id === asset.nodeId)?.data.resultAttachmentId ?? "")
          : "";
        const attachmentId = linkedAttachmentId || asset.attachmentId || "";
        if (attachmentId) currentAttachmentIds.push(attachmentId);
        else if (asset.imageUrl) currentImageUrls.push(asset.imageUrl);
        else missingAssets.push(asset.name);
      }
      if (selectedAssets.length !== scriptAssetIds.length) missingAssets.push("已删除的脚本资产");
      if (missingAssets.length) throw new Error(`参考资产已失效：${[...new Set(missingAssets)].join("、")}`);
      attachmentIds = [...new Set(currentAttachmentIds)];
      imageUrls = [...new Set(currentImageUrls)];
    }
    if (!attachmentIds.length && !imageUrls.length) return undefined;
    const files: File[] = [];
    const missingAttachmentIds: string[] = [];
    for (const attachmentId of attachmentIds) {
      if (signal.aborted) throw new DOMException("图片生成已取消", "AbortError");
      const file = await resolveCanvasAttachment(attachmentId);
      if (file?.type.startsWith("image/")) files.push(file);
      else missingAttachmentIds.push(attachmentId);
    }
    if (missingAttachmentIds.length) throw new Error(`有 ${missingAttachmentIds.length} 个参考资产已失效，请在脚本工作台重新选择图片`);
    for (const imageUrl of imageUrls) {
      if (files.length >= 6) break;
      if (signal.aborted) throw new DOMException("图片生成已取消", "AbortError");
      const response = await fetch(imageUrl, { signal, credentials: imageUrl.startsWith(location.origin) || imageUrl.startsWith("/") ? "same-origin" : "omit" });
      if (!response.ok) throw new Error(`参考资产读取失败（${response.status}）`);
      const blob = await response.blob();
      if (!blob.type.startsWith("image/") || !blob.size || blob.size > MAX_GENERATED_IMAGE_BYTES) {
        throw new Error("参考资产不是有效图片或超过 25MB");
      }
      files.push(new File([blob], `reference-${files.length + 1}`, { type: blob.type, lastModified: Date.now() }));
    }
    if (!files.length) throw new Error("参考资产已失效，请在脚本工作台重新选择图片");
    const reference = await referenceImageCollage(files, signal);
    return { base64: await fileBase64(reference, signal), mimeType: reference.type };
  }

  async function runLibtvGeneratorNode(node: WorkflowNode) {
    const prompt = typeof node.data.prompt === "string" ? node.data.prompt.trim() : "";
    if (!prompt || node.data.status === "running" || (node.data.kind !== "text" && node.data.kind !== "image")) return;
    const textNodeInstruction = [
      "你正在为创作画布生成一个文本节点。请直接执行用户输入；如果用户只给出主题、人物或场景，请将其扩写为结构完整、可直接使用的中文创作文本。",
      "除非用户明确指定其他长度或格式，正文控制在 600–1200 个汉字。只输出结果本身，不解释创作过程。",
      "",
      "用户输入：",
    ].join("\n");
    const modelPrompt = node.data.kind === "text" && textNodeInstruction.length + prompt.length <= 24_000
      ? `${textNodeInstruction}\n${prompt}`
      : prompt;
    const requestedModel = String(node.data.model ?? (node.data.kind === "image" ? "gpt-image-2" : "gpt-5.6-terra"));
    const requestId = crypto.randomUUID();
    cancelGenerationRequest(node.id);
    const requestController = new AbortController();
    generationRequestsRef.current.set(node.id, requestId);
    generationAbortControllersRef.current.set(node.id, requestController);
    setNodes((items) => items.map((item) => item.id === node.id ? {
      ...item,
      data: {
        ...item.data,
        status: "running",
        generationProgress: 4,
        generationError: undefined,
        generationRequestId: requestId,
      },
    } : item));
    setNotice(`${node.data.title} 正在生成…`);

    try {
      const discoveredModels = await discoverCanvasModels(requestController.signal);
      if (!mountedRef.current || generationRequestsRef.current.get(node.id) !== requestId) return;
      const availableModels = discoveredModels.filter((model) => model.modality === node.data.kind);
      if (!availableModels.length) {
        throw new Error(`cli-proxy-api 没有共享可用的${node.data.kind === "image" ? "图片" : "文本"}模型`);
      }
      const preferredModelIds = node.data.kind === "image"
        ? GENERATOR_MODEL_OPTIONS.image.map((model) => model.id)
        : GENERATOR_MODEL_OPTIONS.text.map((model) => model.id);
      const effectiveModel = availableModels.find((model) => model.id === requestedModel)?.id
        ?? preferredModelIds.find((modelId) => availableModels.some((model) => model.id === modelId))
        ?? availableModels[0].id;
      setNodes((items) => items.map((item) => item.id === node.id && item.data.generationRequestId === requestId
        ? { ...item, data: { ...item.data, model: effectiveModel } }
        : item));
      addActivity(`开始使用 ${effectiveModel} 生成「${node.data.title}」`);
      const referenceInput = node.data.kind === "image"
        ? await generatorReferenceInput(node, requestController.signal)
        : undefined;
      if (!mountedRef.current || generationRequestsRef.current.get(node.id) !== requestId) return;
      const result = await generateCanvasContent({
        modality: node.data.kind,
        model: effectiveModel,
        prompt: referenceInput
          ? `${modelPrompt}\n\n必须以输入参考图中的角色、服装、场景和道具为视觉依据，保持主体身份一致；参考图可能是多资产拼图。`
          : modelPrompt,
        signal: requestController.signal,
        ...(node.data.kind === "image" ? { aspectRatio: String(node.data.aspectRatio ?? "16:9") } : {}),
        ...(referenceInput ? { image: referenceInput } : {}),
      });
      if (!mountedRef.current || generationRequestsRef.current.get(node.id) !== requestId) return;

      if (result.modality === "text") {
        const resultPatch: Partial<WorkflowNodeData> = {
          status: "done",
          generationProgress: 100,
          generationRequestId: undefined,
          generationError: undefined,
          resultText: result.text,
          resultAttachmentId: undefined,
          resultMimeType: undefined,
          generatedFromPrompt: prompt,
          generatedWithModel: effectiveModel,
          description: result.text.slice(0, 160),
          assetName: `${node.data.title}.md`,
        };
        const nextNodes = nodesRef.current.map((item) => item.id === node.id && item.data.generationRequestId === requestId ? {
          ...item,
          data: { ...item.data, ...resultPatch },
        } : item);
        nodesRef.current = nextNodes;
        setNodes(nextNodes);
        await persistGeneratorNodeSnapshot(node.id, resultPatch, attachmentsRef.current, nextNodes, edgesRef.current);
        if (generationRequestsRef.current.get(node.id) !== requestId) return;
      } else {
        const file = generatedImageFile(result.image.base64, result.image.mimeType, node.data.title);
        const attachmentId = crypto.randomUUID();
        const attachment: PendingAttachment = {
          id: attachmentId,
          name: file.name,
          size: file.size,
          type: file.type,
          file,
        };
        await registerLocalFiles([attachment]);
        if (!mountedRef.current || generationRequestsRef.current.get(node.id) !== requestId || requestController.signal.aborted) {
          await removeLocalFiles([attachmentId]);
          return;
        }
        const metadata: DraftAttachment = {
          id: attachment.id,
          name: attachment.name,
          size: attachment.size,
          type: attachment.type,
        };
        const nextAttachments = [...attachmentsRef.current.filter((item) => item.id !== attachmentId), metadata];
        attachmentsRef.current = nextAttachments;
        setAttachments(nextAttachments);
        const resultPatch: Partial<WorkflowNodeData> = {
          status: "done",
          generationProgress: 100,
          generationRequestId: undefined,
          generationError: undefined,
          resultText: undefined,
          resultAttachmentId: attachmentId,
          resultMimeType: result.image.mimeType,
          generatedFromPrompt: result.image.revisedPrompt || prompt,
          generatedWithModel: effectiveModel,
          description: result.image.revisedPrompt || prompt,
          assetName: file.name,
        };
        const nextNodes = nodesRef.current.map((item) => item.id === node.id && item.data.generationRequestId === requestId ? {
          ...item,
          data: { ...item.data, ...resultPatch },
        } : item);
        nodesRef.current = nextNodes;
        setNodes(nextNodes);
        await persistGeneratorNodeSnapshot(node.id, resultPatch, nextAttachments, nextNodes, edgesRef.current);
        if (generationRequestsRef.current.get(node.id) !== requestId) return;
        void syncAttachmentsToCloud([attachment], nextAttachments, {
          failurePrefix: "图片已保存在本机，云同步失败",
        });
      }
      generationRequestsRef.current.delete(node.id);
      generationAbortControllersRef.current.delete(node.id);
      addActivity(`完成「${node.data.title}」`);
      setNotice(`${node.data.title} 已完成`);
    } catch (error) {
      if (!mountedRef.current || generationRequestsRef.current.get(node.id) !== requestId) return;
      generationRequestsRef.current.delete(node.id);
      generationAbortControllersRef.current.delete(node.id);
      const message = isCanvasGenerationError(error)
        ? error.message
        : error instanceof Error ? error.message : "生成失败，请稍后重试。";
      const failedPatch: Partial<WorkflowNodeData> = {
        status: "failed",
        generationProgress: 0,
        generationRequestId: undefined,
        generationError: message,
      };
      const nextNodes = nodesRef.current.map((item) => item.id === node.id && item.data.generationRequestId === requestId ? {
        ...item,
        data: { ...item.data, ...failedPatch },
      } : item);
      nodesRef.current = nextNodes;
      setNodes(nextNodes);
      void persistGeneratorNodeSnapshot(node.id, failedPatch, attachmentsRef.current, nextNodes, edgesRef.current);
      addActivity(`「${node.data.title}」生成失败`);
      setNotice(message);
    }
  }

  function runWorkflowNode(nodeId: string) {
    const node = nodes.find((item) => item.id === nodeId);
    if (!node || node.data.status === "running") return;
    if (node.data.variant === "libtv-generator" && (node.data.kind === "text" || node.data.kind === "image")) {
      void runLibtvGeneratorNode(node);
      return;
    }
    if (node.data.variant === "character-workflow" || node.data.variant === "first-frame-video-workflow" || node.data.variant === "audio-video-workflow") {
      setStandaloneWorkflow({
        nodeId,
        workflow: node.data.variant === "character-workflow" ? "character-turnaround" : node.data.variant === "first-frame-video-workflow" ? "first-frame-video" : "audio-video",
      });
      return;
    }
    if (node.data.variant === "script-workflow") {
      setScriptWorkflowInitialDialog(null);
      setScriptWorkflowNodeId(nodeId);
      return;
    }
    if (node.data.kind === "script" && node.data.variant === "script-new") {
      void runScriptWorkbenchGeneratorNode(node);
      return;
    }
    if (node.data.kind === "video") {
      const failedPatch: Partial<WorkflowNodeData> = {
        status: "failed",
        generationError: "当前本地共享模型只提供文本和图片能力；视频生成后端尚未接入，任务未提交。",
      };
      const scriptSourceNodeId = typeof node.data.scriptSourceNodeId === "string" ? node.data.scriptSourceNodeId : "";
      const scriptJobId = typeof node.data.scriptJobId === "string" ? node.data.scriptJobId : "";
      const sourceWorkbench = scriptSourceNodeId
        ? nodesRef.current.find((item) => item.id === scriptSourceNodeId)?.data.scriptWorkbench
        : undefined;
      if (sourceWorkbench && scriptJobId) {
        commitScriptWorkbench(
          scriptSourceNodeId,
          updateScriptWorkbenchJobStatus(
            normalizeScriptWorkbench(sourceWorkbench),
            scriptJobId,
            "failed",
            "视频生成后端尚未接入，任务未提交。",
          ),
        );
      }
      const nextNodes = nodesRef.current.map((item) => item.id === nodeId
        ? { ...item, data: { ...item.data, ...failedPatch } }
        : item);
      nodesRef.current = nextNodes;
      setNodes(nextNodes);
      void persistGeneratorNodeSnapshot(nodeId, failedPatch, attachmentsRef.current, nextNodes, edgesRef.current);
      addActivity(`「${node.data.title}」未提交：视频后端未接入`);
      setNotice("视频后端尚未接入；已保留真实任务参数，没有伪造生成结果");
      return;
    }
    const failedPatch: Partial<WorkflowNodeData> = {
      status: "failed",
      generationError: "当前节点没有对应的后端 REST 执行适配器，任务未提交。",
    };
    const nextNodes = nodesRef.current.map((item) => item.id === nodeId
      ? { ...item, data: { ...item.data, ...failedPatch } }
      : item);
    nodesRef.current = nextNodes;
    setNodes(nextNodes);
    void persistGeneratorNodeSnapshot(nodeId, failedPatch, attachmentsRef.current, nextNodes, edgesRef.current);
    addActivity(`「${node.data.title}」未提交：缺少后端适配器`);
    setNotice("该节点尚未接入后端 REST 执行适配器；没有生成伪造结果");
  }

  function cancelWorkflowGeneration(nodeId: string) {
    const node = nodesRef.current.find((candidate) => candidate.id === nodeId);
    if (!node || node.data.status !== "running") return;
    cancelGenerationRequest(nodeId);
    const patch: Partial<WorkflowNodeData> = {
      status: node.data.scriptWorkbench ? "done" : "failed",
      ...(node.data.scriptWorkbench ? {
        variant: "script-workflow",
        title: normalizeScriptWorkbench(node.data.scriptWorkbench).title,
      } : {}),
      generationProgress: 0,
      generationRequestId: undefined,
      generationError: "生成已由用户取消，可随时重新提交。",
    };
    const nextNodes = nodesRef.current.map((candidate) => candidate.id === nodeId
      ? { ...candidate, data: { ...candidate.data, ...patch } }
      : candidate);
    nodesRef.current = nextNodes;
    setNodes(nextNodes);
    void persistGeneratorNodeSnapshot(nodeId, patch, attachmentsRef.current, nextNodes, edgesRef.current, { writeCloud: false });
    setNotice("已取消生成");
  }

  function createBatchVideoNodes(scriptNodeId: string) {
    const sourceNode = nodesRef.current.find((node) => node.id === scriptNodeId);
    if (!sourceNode) return;
    const workbench = prepareScriptWorkbenchVideoJobs(normalizeScriptWorkbench(sourceNode.data.scriptWorkbench));
    commitScriptWorkbench(scriptNodeId, workbench);
    const scriptNode = nodesRef.current.find((node) => node.id === scriptNodeId);
    if (!scriptNode) return;
    const shots = workbench.shots;
    const existingByShot = new Map(nodesRef.current
      .filter((node) => node.data.kind === "video" && node.data.scriptSourceNodeId === scriptNodeId && typeof node.data.scriptShotId === "string")
      .map((node) => [String(node.data.scriptShotId), node]));
    const updatedNodes = nodesRef.current.map((node) => {
      if (node.data.kind !== "video" || node.data.scriptSourceNodeId !== scriptNodeId) return { ...node, selected: false };
      const shot = shots.find((candidate) => candidate.id === node.data.scriptShotId);
      if (!shot) return { ...node, selected: false };
      const references = scriptAssetReferences(workbench, shot);
      const prompt = composeScriptWorkbenchVideoPrompt(workbench.global_style, shot) || shot.final_prompt || shot.visual;
      const changed = node.data.prompt !== prompt
        || Number(node.data.duration) !== shot.duration
        || node.data.scriptContentSha256 !== workbench.content_sha256
        || !sameStringList(node.data.referenceAttachmentIds, references.attachmentIds)
        || !sameStringList(node.data.referenceNodeIds, references.nodeIds)
        || !sameStringList(node.data.referenceImageUrls, references.imageUrls)
        || !sameStringList(node.data.scriptAssetIds, references.assetIds);
      if (changed) cancelGenerationRequest(node.id);
      return {
        ...node,
        selected: false,
        data: {
          ...node.data,
          title: `镜头 ${String(shots.indexOf(shot) + 1).padStart(2, "0")}`,
          description: `${shot.duration}s · ${shot.scale} · ${shot.visual.slice(0, 54)}…`,
          prompt,
          duration: shot.duration,
          referenceAttachmentIds: references.attachmentIds,
          referenceNodeIds: references.nodeIds,
          referenceImageUrls: references.imageUrls,
          scriptAssetIds: references.assetIds,
          scriptJobId: scriptWorkbenchShotVideoJobId(workbench, shot.id),
          scriptContentSha256: workbench.content_sha256,
          ...(changed ? {
            status: "ready" as const,
            generationProgress: 0,
            generationRequestId: undefined,
            resultAttachmentId: undefined,
            resultMimeType: undefined,
            assetName: undefined,
            generationError: undefined,
          } : {}),
        },
      };
    });
    const createdNodes = shots.filter((shot) => !existingByShot.has(shot.id)).map((shot): WorkflowNode => {
      const references = scriptAssetReferences(workbench, shot);
      const shotIndex = Math.max(0, shots.findIndex((candidate) => candidate.id === shot.id));
      return {
      id: `script-video-${crypto.randomUUID()}`,
      type: "workflow-node",
      position: { x: scriptNode.position.x + 420 + (shotIndex % 4) * 300, y: scriptNode.position.y - 170 + Math.floor(shotIndex / 4) * 250 },
      data: {
        ...nodeRuntimeDefaults("video"),
        kind: "video",
        title: `镜头 ${String(shotIndex + 1).padStart(2, "0")}`,
        description: `${shot.duration}s · ${shot.scale} · ${shot.visual.slice(0, 54)}…`,
        prompt: composeScriptWorkbenchVideoPrompt(workbench.global_style, shot) || shot.final_prompt || shot.visual,
        status: "ready",
        eyebrow: "视频镜头",
        videoMode: "首帧生成视频",
        duration: shot.duration,
        referenceAttachmentIds: references.attachmentIds,
        referenceNodeIds: references.nodeIds,
        referenceImageUrls: references.imageUrls,
        scriptAssetIds: references.assetIds,
        scriptJobId: scriptWorkbenchShotVideoJobId(workbench, shot.id),
        scriptContentSha256: workbench.content_sha256,
        skillId: APP_CANVAS_SKILL_IDS.firstFrameVideo,
        skillPath: `skills/app/${APP_CANVAS_SKILL_IDS.firstFrameVideo}/SKILL.md`,
        scriptSourceNodeId: scriptNodeId,
        scriptShotId: shot.id,
      },
    }});
    if (createdNodes.length || existingByShot.size) {
      const nextNodes = [...updatedNodes, ...createdNodes];
      const nextEdges = [...edgesRef.current, ...createdNodes.map((createdNode) => makeEdge(`edge-${crypto.randomUUID()}`, scriptNodeId, createdNode.id))];
      setGraphImmediately(nextNodes, nextEdges);
      void persistGeneratorNodeSnapshot(scriptNodeId, {}, attachmentsRef.current, nextNodes, nextEdges, { replaceGraph: true });
      setSelectedNodeId(createdNodes[0]?.id ?? existingByShot.values().next().value?.id ?? null);
      addActivity(`已同步 ${shots.length} 个视频生成任务`);
      setNotice(createdNodes.length ? `已创建 ${createdNodes.length} 个视频任务，其余任务已同步` : "视频任务参数已同步");
    } else {
      setNotice("批量视频节点已存在");
    }
    setScriptWorkflowInitialDialog(null);
    setScriptWorkflowNodeId(null);
    window.requestAnimationFrame(() => void flowInstanceRef.current?.fitView({ padding: .18, maxZoom: .85, duration: 360 }));
  }

  function createScriptAssetImageNode(
    scriptNodeId: string,
    asset: ScriptWorkbenchAsset,
    attachmentId: string,
    mimeType: string,
    promptText: string,
    model: string,
    options?: ScriptWorkbenchImageOptions,
  ): string {
    const scriptNode = nodesRef.current.find((node) => node.id === scriptNodeId);
    if (!scriptNode) throw new Error("脚本结果节点已不存在");
    const existing = nodesRef.current.find((node) => node.data.scriptAssetId === asset.id && node.data.scriptSourceNodeId === scriptNodeId);
    const imageIndex = nodesRef.current.filter((node) => node.data.scriptSourceNodeId === scriptNodeId && node.data.kind === "image").length;
    const nodeId = existing?.id ?? `script-asset-image-${crypto.randomUUID()}`;
    if (existing) cancelGenerationRequest(existing.id);
    const data: WorkflowNodeData = {
      ...nodeRuntimeDefaults("image", "libtv-generator"),
      kind: "image",
      title: asset.name,
      description: asset.description || promptText,
      prompt: promptText,
      status: "done",
      eyebrow: asset.kind === "character" ? "角色资产" : asset.kind === "scene" ? "场景资产" : "道具资产",
      variant: "libtv-generator",
      sourceNodeId: scriptNodeId,
      sourceContext: promptText,
      resultAttachmentId: attachmentId,
      resultMimeType: mimeType,
      generatedFromPrompt: promptText,
      generatedWithModel: model,
      generationProgress: 100,
      generationRequestId: undefined,
      generationError: undefined,
      ...(options ? { aspectRatio: options.ratio, resolution: options.resolution, quality: options.quality } : {}),
      assetName: attachmentsRef.current.find((item) => item.id === attachmentId)?.name ?? `${asset.name}.png`,
      scriptSourceNodeId: scriptNodeId,
      scriptAssetId: asset.id,
    };
    const imageNode: WorkflowNode = existing ? { ...existing, data: { ...existing.data, ...data } } : {
      id: nodeId,
      type: "workflow-node",
      position: {
        x: scriptNode.position.x + 430 + (imageIndex % 4) * 300,
        y: scriptNode.position.y - 120 + Math.floor(imageIndex / 4) * 250,
      },
      data,
    };
    const nextNodes = existing
      ? nodesRef.current.map((node) => node.id === nodeId ? imageNode : node)
      : [...nodesRef.current, imageNode];
    const nextEdges = edgesRef.current.some((edge) => edge.source === scriptNodeId && edge.target === nodeId)
      ? edgesRef.current
      : [...edgesRef.current, makeEdge(`edge-${crypto.randomUUID()}`, scriptNodeId, nodeId, true)];
    setGraphImmediately(nextNodes, nextEdges);
    return nodeId;
  }

  async function generateScriptAssetPatch(
    request: ScriptAssetGenerateRequest,
  ): Promise<ScriptWorkbenchAssetPatch> {
    const model = await resolveSharedCanvasModel("image", request.options.modelId, request.signal);
    const result = await generateCanvasContent({
      modality: "image",
      model,
      signal: request.signal,
      aspectRatio: request.options.ratio,
      quality: request.options.quality,
      prompt: [
        request.asset.prompt || `${request.asset.name}，${request.asset.description}`,
        `资产类型：${request.asset.kind === "character" ? "角色设定" : request.asset.kind === "scene" ? "空场景设定" : "道具设定"}。`,
        `全局风格：${request.workbench.global_style}。`,
        `目标规格：${request.options.resolution}，${request.options.quality === "high" ? "高清精细" : "标准画质"}，画幅 ${request.options.ratio}。`,
        "主体一致、细节清晰，不要文字、水印或拼写标注。",
      ].join("\n"),
    });
    if (result.modality !== "image") throw new Error("图片模型没有返回资产图");
    if (request.signal.aborted) throw new DOMException("资产生成已取消", "AbortError");
    const file = await generatedScriptAssetFile(
      result.image.base64,
      result.image.mimeType,
      request.asset.name,
      request.options.ratio,
      request.options.resolution,
      request.options.quality,
      request.signal,
    );
    if (request.signal.aborted) throw new DOMException("资产生成已取消", "AbortError");
    const sha256 = await scriptWorkbenchBlobSha256(file);
    if (request.signal.aborted) throw new DOMException("资产生成已取消", "AbortError");
    const [attachmentId] = await importAssetFiles([file], false, { awaitCloud: false, signal: request.signal });
    if (request.signal.aborted) throw new DOMException("资产生成已取消", "AbortError");
    if (!attachmentId) throw new Error("资产图片保存失败");
    const nodeId = createScriptAssetImageNode(
      request.nodeId,
      request.asset,
      attachmentId,
      file.type,
      result.image.revisedPrompt || request.asset.prompt,
      model,
      request.options,
    );
    return {
      status: "machine_complete",
      source: "ai",
      sha256,
      attachmentId,
      nodeId,
      mimeType: file.type,
      byte_verification: scriptWorkbenchAttachmentVerification(attachmentId, sha256),
      error: null,
    };
  }

  async function generateScriptAsset(request: ScriptAssetGenerateRequest): Promise<ScriptAssetGenerateResult> {
    try {
      const patch = await generateScriptAssetPatch(request);
      const latest = nodesRef.current.find((node) => node.id === request.nodeId)?.data.scriptWorkbench;
      commitScriptWorkbench(request.nodeId, updateScriptWorkbenchAsset(normalizeScriptWorkbench(latest ?? request.workbench), request.asset.id, patch));
      return { patch };
    } catch (error) {
      if (request.signal.aborted) throw error;
      const message = error instanceof Error ? error.message : String(error);
      const latest = nodesRef.current.find((node) => node.id === request.nodeId)?.data.scriptWorkbench;
      commitScriptWorkbench(request.nodeId, updateScriptWorkbenchAsset(normalizeScriptWorkbench(latest ?? request.workbench), request.asset.id, {
        status: "failed",
        source: "none",
        error: message,
      }));
      throw error;
    }
  }

  async function generateScriptAssets(request: ScriptAssetBatchRequest): Promise<ScriptAssetBatchResult> {
    const updates: ScriptAssetBatchResult["updates"] = [];
    for (const assetId of request.assetIds) {
      if (request.signal.aborted) throw new DOMException("批量资产生成已取消", "AbortError");
      const asset = request.workbench.assets.find((candidate) => candidate.id === assetId);
      if (!asset) continue;
      try {
        const patch = await generateScriptAssetPatch({
          nodeId: request.nodeId,
          workbench: request.workbench,
          asset,
          options: request.options,
          signal: request.signal,
        });
        updates.push({ assetId, patch });
        const latest = nodesRef.current.find((node) => node.id === request.nodeId)?.data.scriptWorkbench;
        commitScriptWorkbench(request.nodeId, updateScriptWorkbenchAsset(normalizeScriptWorkbench(latest ?? request.workbench), assetId, patch));
      } catch (error) {
        if (request.signal.aborted) throw error;
        const failedPatch: ScriptWorkbenchAssetPatch = {
          status: "failed",
          source: "none",
          error: error instanceof Error ? error.message : String(error),
        };
        updates.push({
          assetId,
          patch: failedPatch,
        });
        const latest = nodesRef.current.find((node) => node.id === request.nodeId)?.data.scriptWorkbench;
        commitScriptWorkbench(request.nodeId, updateScriptWorkbenchAsset(normalizeScriptWorkbench(latest ?? request.workbench), assetId, failedPatch));
      }
    }
    return { updates };
  }

  async function selectScriptCanvasImage(request: ScriptAssetCanvasSelectRequest): Promise<ScriptAssetGenerateResult> {
    if (request.signal.aborted) throw new DOMException("选择已取消", "AbortError");
    const attachmentId = request.image.attachmentId
      ?? (request.image.nodeId ? String(nodesRef.current.find((node) => node.id === request.image.nodeId)?.data.resultAttachmentId ?? "") : "");
    if (!attachmentId) throw new Error("所选画布图片没有可持久化的素材引用");
    const sourceFile = await resolveCanvasAttachment(attachmentId);
    if (!sourceFile) throw new Error("所选画布图片的真实字节不可读取，不能建立内容 SHA");
    const sha256 = await scriptWorkbenchBlobSha256(sourceFile);
    if (request.signal.aborted) throw new DOMException("选择已取消", "AbortError");
    return {
      patch: {
        status: "machine_complete",
        source: "canvas",
        sha256,
        attachmentId,
        ...(request.image.nodeId ? { nodeId: request.image.nodeId } : {}),
        ...(request.image.mimeType ? { mimeType: request.image.mimeType } : {}),
        byte_verification: scriptWorkbenchAttachmentVerification(attachmentId, sha256),
        error: null,
      },
    };
  }

  async function uploadScriptAsset(request: ScriptAssetUploadRequest): Promise<ScriptAssetGenerateResult> {
    if (!/^image\/(?:png|jpeg|webp)$/.test(request.file.type)) throw new Error("仅支持 PNG、JPG、WEBP 图片");
    if (request.file.size > MAX_GENERATED_IMAGE_BYTES) throw new Error("图片不能超过 25MB");
    const [attachmentId] = await importAssetFiles([request.file], false, {
      awaitCloud: false,
      signal: request.signal,
    });
    if (request.signal.aborted) throw new DOMException("上传已取消", "AbortError");
    if (!attachmentId) throw new Error("本地图片保存失败");
    const sha256 = await scriptWorkbenchBlobSha256(request.file);
    if (request.signal.aborted) throw new DOMException("上传已取消", "AbortError");
    const nodeId = createScriptAssetImageNode(
      request.nodeId,
      request.asset,
      attachmentId,
      request.file.type,
      request.asset.prompt || request.asset.description,
      "本地上传",
    );
    const patch: ScriptWorkbenchAssetPatch = {
      status: "machine_complete",
      source: "upload",
      sha256,
      attachmentId,
      nodeId,
      mimeType: request.file.type,
      byte_verification: scriptWorkbenchAttachmentVerification(attachmentId, sha256),
      error: null,
    };
    const latest = nodesRef.current.find((node) => node.id === request.nodeId)?.data.scriptWorkbench;
    commitScriptWorkbench(
      request.nodeId,
      updateScriptWorkbenchAsset(normalizeScriptWorkbench(latest ?? request.workbench), request.asset.id, patch),
    );
    return { patch };
  }

  async function composeScriptPrompt(request: ScriptPromptComposeRequest): Promise<ScriptPromptComposeResult> {
    if (request.mode === "concat") {
      return { finalPrompt: composeScriptWorkbenchPrompt(request.workbench.global_style, request.shot) };
    }
    const model = await resolveSharedCanvasModel("text", request.modelId, request.signal);
    const result = await generateCanvasContent({
      modality: "text",
      model,
      signal: request.signal,
      prompt: [
        "你是电影分镜提示词专家。根据给定镜头与资产，把信息合成为一段可直接用于分镜生图的中文提示词。只输出最终提示词，不解释，不使用 Markdown。",
        `全局风格：${request.workbench.global_style}`,
        `可用资产：${request.workbench.assets.map((asset) => `${asset.name}（${asset.description}）`).join("；")}`,
        `镜头 JSON：${JSON.stringify(request.shot)}`,
        "保留镜头动作、景别、光影、对白语境、声音氛围和运镜意图；主体身份和服装必须一致。",
      ].join("\n\n"),
    });
    if (result.modality !== "text" || !result.text.trim()) throw new Error("提示词模型没有返回内容");
    return { finalPrompt: result.text.trim() };
  }

  async function composeAllScriptPrompts(request: ScriptPromptBatchRequest): Promise<ScriptPromptBatchResult> {
    const shots = request.workbench.shots.filter((shot) => request.shotIds.includes(shot.id));
    if (request.mode === "concat") {
      return {
        prompts: shots.map((shot) => ({
          shotId: shot.id,
          finalPrompt: composeScriptWorkbenchPrompt(request.workbench.global_style, shot),
        })),
      };
    }
    const model = await resolveSharedCanvasModel("text", request.modelId, request.signal);
    const compactShots = shots.map((shot) => ({
      id: shot.id,
      duration: shot.duration,
      visual: shot.visual.slice(0, 900),
      scale: shot.scale,
      lighting: shot.lighting.slice(0, 500),
      dialogue: shot.dialogue.slice(0, 500),
      sound: shot.sound.slice(0, 300),
      camera: shot.camera.slice(0, 300),
    }));
    const result = await generateCanvasContent({
      modality: "text",
      model,
      signal: request.signal,
      prompt: [
        "你是电影分镜提示词专家。为每个镜头生成一段可直接生图的中文提示词。只返回 JSON，不要 Markdown。",
        '返回格式：{"prompts":[{"shotId":"原镜头id","finalPrompt":"最终提示词"}]}。必须逐一覆盖输入中的每个 shotId，不得新增或改写 id。',
        `全局风格：${request.workbench.global_style}`,
        `可用资产：${request.workbench.assets.map((asset) => `${asset.name}（${asset.description.slice(0, 300)}）`).join("；")}`,
        `镜头：${JSON.stringify(compactShots)}`,
      ].join("\n\n"),
    });
    if (result.modality !== "text") throw new Error("提示词模型没有返回 JSON");
    const payload = extractScriptWorkbenchJson(result.text);
    const record = payload && typeof payload === "object" && !Array.isArray(payload) ? payload as Record<string, unknown> : null;
    const rawPrompts = Array.isArray(record?.prompts) ? record.prompts : [];
    const allowedIds = new Set(shots.map((shot) => shot.id));
    const prompts = rawPrompts.flatMap((value) => {
      if (!value || typeof value !== "object" || Array.isArray(value)) return [];
      const item = value as Record<string, unknown>;
      const shotId = typeof item.shotId === "string" ? item.shotId : "";
      const finalPrompt = typeof item.finalPrompt === "string" ? item.finalPrompt.trim() : "";
      return shotId && allowedIds.has(shotId) && finalPrompt ? [{ shotId, finalPrompt }] : [];
    });
    const promptIds = new Set(prompts.map((item) => item.shotId));
    if (prompts.length !== shots.length || promptIds.size !== shots.length || shots.some((shot) => !promptIds.has(shot.id))) {
      throw new Error(`批量提示词返回不完整或包含重复镜头（${promptIds.size}/${shots.length}）`);
    }
    return { prompts };
  }

  function sanitizePresentedWorkbench(workbench: ScriptWorkbenchDocument): ScriptWorkbenchDocument {
    return normalizeScriptWorkbench({
      ...workbench,
      assets: workbench.assets.map((asset) => {
        if (!asset.imageUrl?.startsWith("blob:")) return asset;
        const { imageUrl: _previewUrl, ...persisted } = asset;
        return persisted;
      }),
    });
  }

  function closeScriptWorkbench() {
    const activeId = scriptWorkflowNodeId;
    if (activeId) {
      const latest = nodesRef.current.find((node) => node.id === activeId);
      if (latest?.data.scriptWorkbench) commitScriptWorkbench(activeId, normalizeScriptWorkbench(latest.data.scriptWorkbench), true);
    }
    setScriptWorkflowInitialDialog(null);
    setScriptWorkflowNodeId(null);
  }

  function jumpToScriptAssetNode(nodeId: string) {
    if (!nodesRef.current.some((node) => node.id === nodeId)) {
      setNotice("关联图片节点已被删除");
      return;
    }
    const nextNodes = nodesRef.current.map((node) => ({ ...node, selected: node.id === nodeId }));
    nodesRef.current = nextNodes;
    setNodes(nextNodes);
    setSelectedNodeId(nodeId);
    setScriptWorkflowInitialDialog(null);
    setScriptWorkflowNodeId(null);
    window.requestAnimationFrame(() => void flowInstanceRef.current?.fitView({ nodes: [{ id: nodeId }], padding: .55, maxZoom: 1.1, duration: 280 }));
  }

  function scriptAssetReferences(workbench: ScriptWorkbenchDocument, shot: ScriptWorkbenchShot) {
    const searchable = [shot.visual, shot.dialogue, shot.final_prompt].join("\n");
    const ready = workbench.assets.filter((asset) => ["machine_complete", "accepted"].includes(asset.status) && hasRealScriptWorkbenchAssetSource(asset));
    const explicitlyReferenced = ready.filter((asset) => {
      const escapedName = asset.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return new RegExp(`@${escapedName}(?![\\p{L}\\p{N}_-])`, "u").test(searchable);
    });
    // The image bridge composes at most six references into one model input.
    // Keep task metadata aligned with the images that will actually be sent.
    const selected = (explicitlyReferenced.length ? explicitlyReferenced : ready).slice(0, 6);
    const currentSources = selected.map((asset) => {
      const linkedAttachmentId = asset.nodeId
        ? String(nodesRef.current.find((candidate) => candidate.id === asset.nodeId)?.data.resultAttachmentId ?? "")
        : "";
      const attachmentId = linkedAttachmentId || asset.attachmentId || "";
      return {
        attachmentId,
        imageUrl: attachmentId ? "" : asset.imageUrl || "",
      };
    });
    return {
      attachmentIds: [...new Set(currentSources.flatMap(({ attachmentId }) => attachmentId ? [attachmentId] : []))],
      nodeIds: selected.flatMap((asset) => asset.nodeId ? [asset.nodeId] : []),
      imageUrls: [...new Set(currentSources.flatMap(({ imageUrl }) => imageUrl ? [imageUrl] : []))],
      assetIds: selected.map((asset) => asset.id),
    };
  }

  function createBatchStoryboardNodes(scriptNodeId: string, workbench: ScriptWorkbenchDocument) {
    const scriptNode = nodesRef.current.find((node) => node.id === scriptNodeId);
    if (!scriptNode) return;
    const existingByShot = new Map(nodesRef.current
      .filter((node) => node.data.storyboardSourceNodeId === scriptNodeId && typeof node.data.scriptShotId === "string")
      .map((node) => [String(node.data.scriptShotId), node]));
    const updatedNodes = nodesRef.current.map((node) => {
      if (node.data.storyboardSourceNodeId !== scriptNodeId) return { ...node, selected: false };
      const shot = workbench.shots.find((candidate) => candidate.id === node.data.scriptShotId);
      if (!shot?.final_prompt.trim()) return { ...node, selected: false };
      const references = scriptAssetReferences(workbench, shot);
      const changed = node.data.prompt !== shot.final_prompt
        || node.data.scriptContentSha256 !== workbench.content_sha256
        || !sameStringList(node.data.referenceAttachmentIds, references.attachmentIds)
        || !sameStringList(node.data.referenceNodeIds, references.nodeIds)
        || !sameStringList(node.data.referenceImageUrls, references.imageUrls)
        || !sameStringList(node.data.scriptAssetIds, references.assetIds);
      if (changed) cancelGenerationRequest(node.id);
      return {
        ...node,
        selected: false,
        data: {
          ...node.data,
          title: `分镜 ${String(workbench.shots.indexOf(shot) + 1).padStart(2, "0")}`,
          description: `${shot.scale} · ${shot.visual.slice(0, 70)}`,
          prompt: shot.final_prompt,
          sourceContext: shot.final_prompt,
          referenceAttachmentIds: references.attachmentIds,
          referenceNodeIds: references.nodeIds,
          referenceImageUrls: references.imageUrls,
          scriptAssetIds: references.assetIds,
          scriptContentSha256: workbench.content_sha256,
          ...(changed ? {
            status: "idle" as const,
            generationProgress: 0,
            generationRequestId: undefined,
            resultAttachmentId: undefined,
            resultMimeType: undefined,
            assetName: undefined,
            generationError: undefined,
          } : {}),
        },
      };
    });
    const created = workbench.shots.filter((shot) => shot.final_prompt.trim() && !existingByShot.has(shot.id)).map((shot): WorkflowNode => {
      const references = scriptAssetReferences(workbench, shot);
      const shotIndex = Math.max(0, workbench.shots.findIndex((candidate) => candidate.id === shot.id));
      return {
      id: `script-storyboard-${crypto.randomUUID()}`,
      type: "workflow-node",
      position: { x: scriptNode.position.x + 430 + (shotIndex % 4) * 300, y: scriptNode.position.y - 170 + Math.floor(shotIndex / 4) * 250 },
      data: {
        ...nodeRuntimeDefaults("image", "libtv-generator"),
        kind: "image",
        title: `分镜 ${String(shotIndex + 1).padStart(2, "0")}`,
        description: `${shot.scale} · ${shot.visual.slice(0, 70)}`,
        prompt: shot.final_prompt,
        status: "idle",
        eyebrow: "分镜画面",
        variant: "libtv-generator",
        sourceNodeId: scriptNodeId,
        sourceContext: shot.final_prompt,
        aspectRatio: "16:9",
        referenceAttachmentIds: references.attachmentIds,
        referenceNodeIds: references.nodeIds,
        referenceImageUrls: references.imageUrls,
        scriptAssetIds: references.assetIds,
        scriptContentSha256: workbench.content_sha256,
        storyboardSourceNodeId: scriptNodeId,
        scriptShotId: shot.id,
      },
    }});
    if (!created.length && !existingByShot.size) {
      setNotice("没有可创建的分镜图片任务");
      return;
    }
    const nextNodes = [...updatedNodes, ...created];
    const nextEdges = [...edgesRef.current, ...created.map((node) => makeEdge(`edge-${crypto.randomUUID()}`, scriptNodeId, node.id, true))];
    setGraphImmediately(nextNodes, nextEdges);
    setSelectedNodeId(created[0]?.id ?? null);
    void persistGeneratorNodeSnapshot(scriptNodeId, {}, attachmentsRef.current, nextNodes, nextEdges, { replaceGraph: true });
    setScriptWorkflowInitialDialog(null);
    setScriptWorkflowNodeId(null);
    setNotice(created.length ? `已创建 ${created.length} 个分镜图片任务，其余任务已同步` : "分镜图片任务参数已同步");
    const focusNodes = created.length ? created : [...existingByShot.values()];
    window.requestAnimationFrame(() => void flowInstanceRef.current?.fitView({ nodes: focusNodes.map((node) => ({ id: node.id })), padding: .25, maxZoom: .9, duration: 320 }));
  }

  function handleScriptNodeAction(nodeId: string, action: "regenerate" | "storyboard" | "video" | "download") {
    const resultNode = nodesRef.current.find((node) => node.id === nodeId && node.data.variant === "script-workflow");
    if (!resultNode) return;
    const workbench = normalizeScriptWorkbench(resultNode.data.scriptWorkbench);
    if (action === "download") {
      const url = URL.createObjectURL(new Blob([serializeScriptWorkbench(workbench, true)], { type: "application/json;charset=utf-8" }));
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${workbench.title.replace(/[\\/:*?"<>|]/g, " ").trim() || "故事脚本"}.json`;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      return;
    }
    if (action === "storyboard") {
      if (!isScriptWorkbenchReadyForBatchVideo(workbench)) {
        setNotice("请先完成镜头、真实资产与全部提示词");
        return;
      }
      createBatchStoryboardNodes(nodeId, workbench);
      return;
    }
    if (action === "video") {
      if (!isScriptWorkbenchReadyForBatchVideo(workbench)) {
        setNotice("请先完成镜头、真实资产与全部提示词");
        return;
      }
      setScriptWorkflowInitialDialog("video");
      setScriptWorkflowNodeId(nodeId);
      return;
    }
    if (!window.confirm("重新生成会覆盖当前三步脚本内容，是否继续？")) return;
    void runScriptWorkbenchGeneratorNode(resultNode, true);
  }

  function batchVideoFromWorkbench(request: ScriptBatchVideoRequest) {
    if (request.signal.aborted) return;
    createBatchVideoNodes(request.nodeId);
  }

  async function runStandaloneWorkflow(request: StandaloneSkillRunRequest) {
    const sourceNode = nodesRef.current.find((node) => node.id === request.nodeId);
    if (!sourceNode) throw new Error("发起任务的画布节点已不存在");
    if (!request.sourceFile) throw new Error("请先上传真实输入文件；占位素材不会提交到后端");

    const [sourceAttachmentId] = await importAssetFiles([request.sourceFile], false, { awaitCloud: false });
    if (!sourceAttachmentId) throw new Error("输入文件未能保存到当前作品");

    const standaloneGatewayMode = creationConfig.executor === "local-codex" ? "local" : "backend";
    let submissionGateway = gateway?.mode === standaloneGatewayMode
      ? gateway
      : await createAgentGateway(creationConfig.executor ?? "backend");
    if (!mountedRef.current) throw new Error("画布已关闭");
    if (submissionGateway.mode === "demo") {
      submissionGateway = await createAgentGateway(creationConfig.executor ?? "backend");
      if (!mountedRef.current) throw new Error("画布已关闭");
    }
    setGateway(submissionGateway);
    setPanelOpen(true);
    setPanelTab("history");
    const standaloneSkillPath = canonicalAppSkillPath(request.skillId)
      ?? `skills/${canonicalAppSkillId(request.skillId) ?? request.skillId}/SKILL.md`;
    setNodes((items) => items.map((node) => node.id === request.nodeId
      ? { ...node, data: { ...node.data, status: "running", generationError: undefined, skillId: canonicalAppSkillId(request.skillId) ?? request.skillId, skillPath: standaloneSkillPath } }
      : node));

    const effectiveWork = {
      ...work,
      name: workName.trim() || "unnamed",
      creationConfig,
      attachments: attachmentsRef.current,
      ...(cloudProjectId ? { cloudProjectId } : {}),
    };
    saveWork(effectiveWork);
    let latestJob: AgentJob | null = null;
    try {
      let current = await submissionGateway.submit({
        work: effectiveWork,
        prompt: request.prompt,
        skillId: request.skillId,
        context: {
          standaloneWorkflow: request.workflow,
          sourceNodeId: request.nodeId,
          sourceAttachmentId,
          ...request.context,
        },
      });
      latestJob = current;
      if (!mountedRef.current) throw new Error("画布已关闭");
      setActiveJob(current);
      updateRun(current, request.prompt);
      addActivity(`向后端提交 Skill：${request.skillId}`);

      if (submissionGateway.status && (current.state === "queued" || current.state === "running")) {
        for (let attempt = 0; attempt < 300 && (current.state === "queued" || current.state === "running"); attempt += 1) {
          await new Promise((resolve) => window.setTimeout(resolve, 1200));
          if (!mountedRef.current) throw new Error("画布已关闭");
          current = await submissionGateway.status(current.id);
          latestJob = current;
          setActiveJob(current);
          updateRun(current, request.prompt);
        }
      }

      if (current.state !== "succeeded") {
        const message = current.state === "queued" || current.state === "running"
          ? "后端 Skill 运行超时，请稍后重试"
          : current.message || `后端 Skill 任务${current.state}`;
        throw new Error(message);
      }
      const inserted = await materializeAgentArtifacts(current);
      if (!inserted) throw new Error("后端任务成功，但没有返回可展示的产物");
      setNodes((items) => items.map((node) => node.id === request.nodeId
        ? { ...node, data: { ...node.data, status: "done", generationError: undefined, assetName: `Skill · ${request.skillId}` } }
        : node));
      addActivity(`后端 Skill 完成：${request.skillId}`);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : String(cause);
      if (mountedRef.current) {
        if (!latestJob) {
          const failed: AgentJob = { id: crypto.randomUUID(), state: "failed", message };
          setActiveJob(failed);
          updateRun(failed, request.prompt);
        }
        setNodes((items) => items.map((node) => node.id === request.nodeId
          ? { ...node, data: { ...node.data, status: "failed", generationError: message, assetName: `Skill 失败 · ${request.skillId}` } }
          : node));
      }
      throw cause;
    }
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
      data: { ...copyableWorkflowNodeData(source.data), title: `${source.data.title} 副本` },
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
    data?: Partial<WorkflowNodeData>;
  }) {
    if (work.line === "comic" && kind === "video") {
      setNotice("漫画工作流不包含视频节点");
      return;
    }
    const definition = nodeDefinition(kind);
    const variant = options?.variant ?? "default";
    const anchor = nodes.find((node) => node.id === selectedNodeId) ?? nodes[nodes.length - 1];
    const id = `${kind}-${crypto.randomUUID()}`;
    const title = variant === "libtv-generator" ? nextGeneratorTitle(kind) : options?.title ?? definition.label;
    const nextNode: WorkflowNode = {
      id,
      type: "workflow-node",
      position: options?.position ?? (anchor ? { x: anchor.position.x + 310, y: anchor.position.y + 42 } : { x: 120, y: 140 }),
      data: {
        ...nodeRuntimeDefaults(kind, variant),
        kind,
        title,
        description: options?.description ?? definition.description,
        status: "idle",
        eyebrow: definition.eyebrow,
        variant,
        ...(options?.prompt !== undefined ? { prompt: options.prompt } : {}),
        ...(options?.assetName ? { assetName: options.assetName } : {}),
        ...options?.data,
      },
    };
    setNodes((items) => [...items.map((node) => ({ ...node, selected: false })), { ...nextNode, selected: true }]);
    if (anchor && options?.connectToAnchor !== false) setEdges((items) => addEdge(makeEdge(`edge-${crypto.randomUUID()}`, anchor.id, id), items));
    setSelectedNodeId(id);
    setDrawer(null);
    addActivity(`添加${title}节点`);
  }

  function applyToolboxTemplate(template: ToolboxTemplate) {
    const stageBounds = document.querySelector<HTMLElement>(".creation-canvas-stage .react-flow")?.getBoundingClientRect();
    const screenCenter = stageBounds
      ? { x: stageBounds.left + stageBounds.width / 2, y: stageBounds.top + stageBounds.height / 2 }
      : { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    const flowCenter = flowInstanceRef.current?.screenToFlowPosition(screenCenter) ?? screenCenter;
    const origin = { x: flowCenter.x - 445, y: flowCenter.y - (template.recipe === "storyboard" ? 315 : 150) };
    const batchId = `${template.id}-${crypto.randomUUID()}`;

    const makeTemplateNode = (
      part: string,
      kind: WorkflowNodeKind,
      position: { x: number; y: number },
      title: string,
      description: string,
      status: WorkflowNodeStatus,
      patch: Partial<WorkflowNodeData> = {},
    ): WorkflowNode => {
      const definition = nodeDefinition(kind);
      return {
        id: `toolbox-${batchId}-${part}`,
        type: "workflow-node",
        position,
        selected: false,
        data: {
          ...nodeRuntimeDefaults(kind),
          kind,
          title,
          description,
          status,
          eyebrow: definition.eyebrow,
          variant: "default",
          assetName: `工具箱 · ${template.title}`,
          toolboxTemplateId: template.id,
          toolboxTemplateTitle: template.title,
          ...patch,
        },
      };
    };

    let createdNodes: WorkflowNode[];
    let createdEdges: Edge[];

    if (template.recipe === "storyboard") {
      const brief = makeTemplateNode("brief", "text", { x: origin.x, y: origin.y + 70 }, template.inputLabel, "输入故事梗概、人物关系与希望强调的情节。", "ready", { prompt: "故事简述：" });
      const roleA = makeTemplateNode("role-a", "image", { x: origin.x, y: origin.y + 300 }, "上传角色图", "可选：上传主要角色参考，锁定人物身份与服装。", "ready", { imageMode: "图片输入" });
      const roleB = makeTemplateNode("role-b", "image", { x: origin.x, y: origin.y + 530 }, "上传角色图", "可选：上传第二角色参考，用于双人镜头连续性。", "ready", { imageMode: "图片输入" });
      const promptNode = makeTemplateNode("prompt", "script", { x: origin.x + 345, y: origin.y + 180 }, "九宫格分镜生成器", template.description, "ready", { prompt: template.prompt });
      const result = makeTemplateNode("result", "image", { x: origin.x + 690, y: origin.y + 180 }, template.resultLabel, "生成后可继续拆分宫格、编辑单镜头并发送到视频节点。", "idle", { prompt: template.prompt, imageMode: "文生图", aspectRatio: "16:9", resolution: "2K" });
      createdNodes = [brief, roleA, roleB, promptNode, { ...result, selected: true }];
      createdEdges = [
        makeEdge(`edge-${crypto.randomUUID()}`, brief.id, promptNode.id),
        makeEdge(`edge-${crypto.randomUUID()}`, roleA.id, promptNode.id),
        makeEdge(`edge-${crypto.randomUUID()}`, roleB.id, promptNode.id),
        makeEdge(`edge-${crypto.randomUUID()}`, promptNode.id, result.id, true),
      ];
    } else if (template.recipe === "interior") {
      const input = makeTemplateNode("input", "image", { x: origin.x, y: origin.y + 80 }, template.inputLabel, "上传需要改造的真实空间照片，保留原始视角和结构。", "ready", { imageMode: "图片输入" });
      const promptNode = makeTemplateNode("prompt", "text", { x: origin.x + 340, y: origin.y }, "装修要求", template.description, "ready", { prompt: template.prompt });
      const result = makeTemplateNode("result", "image", { x: origin.x + 680, y: origin.y + 80 }, template.resultLabel, "根据原空间结构与装修要求生成可继续编辑的效果图。", "idle", { prompt: template.prompt, imageMode: "参考图生图", aspectRatio: "16:9", resolution: "2K" });
      createdNodes = [input, promptNode, { ...result, selected: true }];
      createdEdges = [
        makeEdge(`edge-${crypto.randomUUID()}`, input.id, result.id),
        makeEdge(`edge-${crypto.randomUUID()}`, promptNode.id, result.id, true),
      ];
    } else {
      const input = makeTemplateNode("input", "image", { x: origin.x, y: origin.y + 95 }, template.inputLabel, "上传或从当前画布选择要应用模板的主参考图。", "ready", { imageMode: "图片输入" });
      const promptNode = makeTemplateNode("prompt", "text", { x: origin.x + 335, y: origin.y }, "提示词（勿修改）", template.description, "ready", { prompt: template.prompt });
      const result = makeTemplateNode("result", "video", { x: origin.x + 670, y: origin.y + 95 }, template.resultLabel, "参考图与模板提示词均连接后即可生成视频。", "idle", { prompt: template.prompt, videoMode: "首帧生成视频", model: "Lib Video 2.0", aspectRatio: "16:9", resolution: "720P", outputCount: 2, duration: 5 });
      createdNodes = [input, promptNode, { ...result, selected: true }];
      createdEdges = [
        makeEdge(`edge-${crypto.randomUUID()}`, input.id, result.id),
        makeEdge(`edge-${crypto.randomUUID()}`, promptNode.id, result.id, true),
      ];
    }

    const resultNode = createdNodes[createdNodes.length - 1];
    setNodes((items) => [...items.map((node) => ({ ...node, selected: false })), ...createdNodes]);
    setEdges((items) => [...items, ...createdEdges]);
    setSelectedNodeId(resultNode.id);
    setDrawer(null);
    setToolboxGuideOpen(false);
    setToolboxDetail(null);
    setToolboxClassicDetail(null);
    addActivity(`使用工具箱模板「${template.title}」创建 ${createdNodes.length} 个节点`);
    setNotice(`已使用「${template.title}」模板`);
    window.requestAnimationFrame(() => void flowInstanceRef.current?.fitView({ nodes: createdNodes.map((node) => ({ id: node.id })), padding: .28, maxZoom: .92, duration: 360 }));
  }

  function applyToolboxClassic(template: ToolboxClassic) {
    applyToolboxTemplate({
      id: `classic-${template.id}`,
      title: template.title,
      description: template.description,
      cover: template.cover,
      category: "分镜",
      recipe: "video",
      inputLabel: "上传替换素材",
      resultLabel: "视频生成结果",
      prompt: `分析「${template.title}」的场面调度、景别变化、动作节奏与人物反应关系，使用用户上传的新角色和新场景重构同类叙事节奏；保留喜剧或戏剧结构，不复刻原片人物外貌、台词和受版权保护画面。`,
    });
  }

  function applyCanvasStarterPreset(preset: CanvasStarterPreset) {
    const stageBounds = document.querySelector<HTMLElement>(".creation-canvas-stage .react-flow")?.getBoundingClientRect();
    const screenCenter = stageBounds
      ? { x: stageBounds.left + stageBounds.width / 2, y: stageBounds.top + stageBounds.height / 2 }
      : { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    const flowCenter = flowInstanceRef.current?.screenToFlowPosition(screenCenter) ?? screenCenter;
    const nodeGap = preset.id === "story-script" ? 730 : 330;
    const recipeWidth = (preset.id === "story-script" ? 310 : 248) + Math.max(0, preset.nodes.length - 1) * nodeGap;
    const originX = flowCenter.x - recipeWidth / 2;
    const originY = flowCenter.y - 94;
    const createdNodes = preset.nodes.map((item, index): WorkflowNode => {
      const definition = nodeDefinition(item.kind);
      const id = `${preset.id}-${crypto.randomUUID()}`;
      return {
        id,
        type: "workflow-node",
        position: {
          x: originX + index * nodeGap,
          y: preset.id === "story-script" ? originY + (index === 0 ? 46 : -48) : originY,
        },
        selected: index === preset.nodes.length - 1,
        data: {
          ...nodeRuntimeDefaults(item.kind, item.variant),
          ...item.data,
          kind: item.kind,
          title: item.title,
          description: item.description,
          status: index === 0 ? "done" : "idle",
          eyebrow: definition.eyebrow,
          variant: item.variant ?? "default",
          assetName: `Skill · ${preset.skill}`,
          skillId: preset.skill,
          skillPath: preset.skillPath,
        },
      };
    });
    if (preset.id === "story-script" && createdNodes[0] && createdNodes[1]) {
      const source = createdNodes[0];
      const sourceContext = String(source.data.resultText ?? source.data.prompt ?? source.data.description ?? "");
      createdNodes[1] = {
        ...createdNodes[1],
        data: {
          ...createdNodes[1].data,
          sourceNodeId: source.id,
          sourceContext,
        },
      };
    }
    const createdEdges = createdNodes.slice(1).map((node, index) => preset.id === "story-script" && index === 0
      ? makeLibtvReferenceEdge(`starter-edge-${crypto.randomUUID()}`, createdNodes[index].id, node.id)
      : makeEdge(`starter-edge-${crypto.randomUUID()}`, createdNodes[index].id, node.id, index === 0));
    setNodes((items) => [...items.map((node) => ({ ...node, selected: false })), ...createdNodes]);
    setEdges((items) => [...items, ...createdEdges]);
    setSelectedNodeId(createdNodes.at(-1)?.id ?? null);
    setDrawer(null);
    setView("workflow");
    addActivity(`使用「${preset.title}」快捷工作流（${preset.skill}）`);
    setNotice(`已添加「${preset.title}」工作流`);
    window.requestAnimationFrame(() => {
      void flowInstanceRef.current?.fitView({ nodes: createdNodes.map((node) => ({ id: node.id })), padding: .5, maxZoom: 1, duration: 280 });
    });
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
    const effectiveVariant = variant === "default" && (kind === "text" || kind === "image") ? "libtv-generator" : variant;
    addWorkflowNode(kind, {
      title,
      description,
      variant: effectiveVariant,
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

  function openDrawerHistoryPicker() {
    setHistoryInsertPoint(null);
    setCanvasHistorySource("libtv");
    setCanvasHistoryMedia("image");
    setCanvasHistorySelection([]);
    setCanvasHistoryPickerOpen(true);
    setDrawer(null);
    setAddDrawerSubmenu(null);
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

  async function importAssetFiles(files: File[], openAssetsDrawer: boolean, options?: { awaitCloud?: boolean; signal?: AbortSignal }): Promise<string[]> {
    if (!files.length) return [];
    const importWorkId = work.id;
    const isStale = () => Boolean(options?.signal?.aborted) || workClearedRef.current || activeWorkIdRef.current !== importWorkId;
    if (isStale()) return [];
    const pending: PendingAttachment[] = files.map((file) => ({
      id: crypto.randomUUID(),
      name: file.name,
      size: file.size,
      type: file.type || "application/octet-stream",
      file,
    }));
    const pendingIds = pending.map((attachment) => attachment.id);
    await registerLocalFiles(pending);
    if (isStale()) {
      await removeLocalFiles(pendingIds);
      return [];
    }
    const importedMetadata = pending.map(({ id, name, size, type }) => ({ id, name, size, type }));
    const nextAttachments = mergeDraftAttachments(attachmentsRef.current, importedMetadata);
    attachmentsRef.current = nextAttachments;
    setAttachments(nextAttachments);
    const currentWork = loadWork(work.id) ?? work;
    const nextWork: WebWork = {
      ...currentWork,
      name: workName.trim() || "unnamed",
      creationConfig,
      attachments: nextAttachments,
      ...((currentWork.cloudProjectId ?? cloudProjectId) ? { cloudProjectId: currentWork.cloudProjectId ?? cloudProjectId } : {}),
      cloudState: isCloudConfigured() ? "syncing" : "local",
    };
    saveWork(nextWork);
    addActivity(`导入 ${pending.length} 个素材`);
    if (openAssetsDrawer) setDrawer("assets");

    if (!isCloudConfigured()) {
      setNotice(`已导入 ${pending.length} 个本地素材`);
      return pendingIds;
    }
    const cloudSync = syncAttachmentsToCloud(pending, nextAttachments, {
      success: `已上传 ${pending.length} 个素材`,
      local: `已导入 ${pending.length} 个本地素材，登录后可同步`,
      failurePrefix: "素材保留在本地，云上传失败",
    });
    if (options?.awaitCloud === false) {
      void cloudSync.catch(() => undefined);
      return pendingIds;
    }
    await cloudSync;
    return pendingIds;
  }

  async function registerDirectorFile(file: File): Promise<string> {
    const [attachmentId] = await importAssetFiles([file], false, { awaitCloud: false });
    if (!attachmentId) throw new Error("导演台素材保存失败");
    return attachmentId;
  }

  async function materializeAgentArtifacts(job: AgentJob): Promise<number> {
    if (materializedAgentJobsRef.current.has(job.id)) return 0;
    const artifacts: AgentArtifact[] = job.artifacts?.length ? job.artifacts : job.output?.trim() ? [{
      id: "agent-output",
      kind: "text",
      name: `${activeSkillTitle || "Skill"} 运行结果`,
      mimeType: "text/markdown",
      text: job.output.slice(-200_000),
    }] : [];
    if (!artifacts.length) return 0;
    materializedAgentJobsRef.current.add(job.id);
    const stageBounds = document.querySelector<HTMLElement>(".creation-canvas-stage .react-flow")?.getBoundingClientRect();
    const screenOrigin = stageBounds
      ? { x: stageBounds.left + Math.min(230, stageBounds.width * .2), y: stageBounds.top + 150 }
      : { x: 160, y: 160 };
    const flowOrigin = flowInstanceRef.current?.screenToFlowPosition(screenOrigin) ?? screenOrigin;
    let inserted = 0;

    for (const artifact of artifacts.slice(0, 100)) {
      if (!artifact || !artifact.id || !artifact.name || !["text", "image", "video", "audio"].includes(artifact.kind)) continue;
      let resultText = artifact.kind === "text" ? artifact.text?.trim() ?? "" : "";
      let attachmentId = "";
      let mimeType = artifactMimeType(artifact);

      if (artifact.assetId) {
        const attachment: DraftAttachment = {
          id: `agent-${job.id}-${artifact.id}`,
          name: artifact.name,
          size: Math.max(0, artifact.size ?? 0),
          type: mimeType,
          assetId: artifact.assetId,
        };
        const nextAttachments = mergeDraftAttachments(attachmentsRef.current, [attachment]);
        attachmentsRef.current = nextAttachments;
        setAttachments(nextAttachments);
        attachmentId = attachment.id;
      } else if (!resultText || artifact.kind !== "text") {
        const file = await agentArtifactFile(artifact).catch(() => null);
        if (file) {
          mimeType = file.type || mimeType;
          if (artifact.kind === "text" && file.size <= 4 * 1024 * 1024) resultText = (await file.text()).trim();
          else [attachmentId] = await importAssetFiles([file], false, { awaitCloud: false });
        }
      }

      if (artifact.kind === "text" ? !resultText : !attachmentId) continue;
      const position = {
        x: flowOrigin.x + (inserted % 2) * 350,
        y: flowOrigin.y + Math.floor(inserted / 2) * 270,
      };
      addWorkflowNode(artifact.kind, {
        title: artifact.name,
        description: `由 Skill 自动产出 · ${activeSkillTitle || "Agent"}`,
        assetName: "Skill 产物 · 已自动添加",
        variant: "libtv-generator",
        position,
        connectToAnchor: false,
        data: {
          status: "done",
          resultText: resultText || undefined,
          resultAttachmentId: attachmentId || undefined,
          resultMimeType: mimeType,
          generatedWithModel: selectedModel?.name || creationConfig.model.modelId,
          agentJobId: job.id,
          agentArtifactId: artifact.id,
        },
      });
      inserted += 1;
    }

    if (inserted) {
      setDrawer(null);
      setView("workflow");
      addActivity(`Skill 产物已自动添加到画布（${inserted} 项）`);
      setNotice(`已将 ${inserted} 项 Skill 产物添加到左侧画布`);
    }
    return inserted;
  }

  async function buildDirectorSceneWithModel(prompt: string, current: DirectorSceneState, signal: AbortSignal): Promise<DirectorSceneState> {
    try {
      const models = (await discoverCanvasModels(signal)).filter((model) => model.modality === "text");
      const model = ["gpt-5.6-terra", "gpt-5.6-sol", "gpt-5.6-luna", "gpt-5.5", "gpt-5.4-mini"]
        .map((id) => models.find((item) => item.id === id))
        .find(Boolean) ?? models[0];
      if (!model) throw new Error("cli-proxy-api 没有共享可用的 GPT 文本模型");
      const result = await generateCanvasContent({
        modality: "text",
        model: model.id,
        signal,
        prompt: [
          "你是 3D 导演台场景解析器。根据原始描述，只输出一行中文标签，不要解释。",
          "标签必须从这些值中选择：人数=单人/两名/三名/人群；角色=男性/女性/一男一女/儿童/少年/健硕；机位=正面中景/正面特写/正面全景/侧面跟拍/侧面近景/背面中景/俯拍/低角度/过肩/鸟瞰/荷兰角；动作=站立/行走/跑步/坐姿/格斗/招手；时间=白天/黄昏/夜晚；画幅=21:9/16:9/4:3/1:1/3:4/9:16。",
          `原始描述：${prompt}`,
        ].join("\n"),
      });
      if (result.modality !== "text") throw new Error("GPT 模型没有返回场景解析文本");
      return buildDirectorSceneFromPrompt(`${prompt}\n模型解析标签：${result.text.slice(0, 4_000)}`, current);
    } catch (error) {
      if (signal.aborted) throw error;
      throw new Error(`共享 GPT 场景解析失败：${error instanceof Error ? error.message : String(error)}`);
    }
  }

  async function generateDirectorPanorama(prompt: string, signal: AbortSignal): Promise<string> {
    const models = (await discoverCanvasModels(signal)).filter((model) => model.modality === "image");
    const model = ["gpt-image-2", "gpt-image-1.5"].map((id) => models.find((item) => item.id === id)).find(Boolean) ?? models[0];
    if (!model) throw new Error("cli-proxy-api 没有共享可用的图片模型");
    const result = await generateCanvasContent({
      modality: "image",
      model: model.id,
      signal,
      aspectRatio: "16:9",
      prompt: `生成可包裹 3D 场景的 360 度等距柱状投影（equirectangular）全景环境图，左右边缘必须无缝衔接，不要人物、文字、边框或水印。场景：${prompt}`,
    });
    if (result.modality !== "image") throw new Error("图片模型没有返回全景图");
    const file = await generatedPanoramaFile(result.image.base64, result.image.mimeType, "AI全景图");
    return registerDirectorFile(file);
  }

  async function analyzeDirectorReference(file: File, current: DirectorSceneState, signal: AbortSignal): Promise<DirectorSceneState> {
    if (!/^image\/(?:png|jpeg|webp|gif)$/.test(file.type)) throw new Error("参考图格式不支持视觉分析");
    const models = (await discoverCanvasModels(signal)).filter((model) => model.modality === "text");
    const model = ["gpt-5.6-terra", "gpt-5.6-sol", "gpt-5.6-luna", "gpt-5.5", "gpt-5.4-mini"]
      .map((id) => models.find((item) => item.id === id))
      .find(Boolean) ?? models[0];
    if (!model) throw new Error("cli-proxy-api 没有可用于识图的 GPT 模型");
    const result = await generateCanvasContent({
      modality: "text",
      model: model.id,
      signal,
      image: { base64: await fileBase64(file, signal), mimeType: file.type },
      prompt: [
        "分析参考图片，并把它归纳成可编辑的 3D 导演台场景。只输出一行中文标签，不要解释。",
        "标签必须包括：人数=单人/两名/三名/人群；角色=男性/女性/一男一女/儿童/少年/健硕；机位=正面中景/正面特写/正面全景/侧面跟拍/侧面近景/背面中景/俯拍全景/45°俯拍/低角度仰拍/低角度广角/过肩镜头/过肩镜头（右）/鸟瞰/荷兰角；动作=站立/行走/跑步/坐姿/格斗/招手；时间=白天/黄昏/夜晚；画幅=21:9/16:9/4:3/1:1/3:4/9:16。",
        "无法确定时选择最接近项，不要虚构图片中不存在的人物。",
      ].join("\n"),
    });
    if (result.modality !== "text") throw new Error("视觉模型没有返回场景分析");
    return buildDirectorSceneFromPrompt(`参考图视觉分析：${result.text.slice(0, 4_000)}`, current);
  }

  async function importAssets(fileList: FileList | null) {
    return importAssetFiles(fileList ? Array.from(fileList) : [], true);
  }

  async function uploadComposerAssets(files: File[]) {
    const ids = await importAssetFiles(files, false);
    if (ids.length && mountedRef.current && !workClearedRef.current) {
      setComposerAttachmentIds((current) => [...new Set([...current, ...ids])]);
    }
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
    selectedIds.forEach((nodeId) => {
      cancelGenerationRequest(nodeId);
    });
    const nextNodes = nodesRef.current.filter((node) => !selectedIds.has(node.id));
    const nextEdges = edgesRef.current.filter((edge) => !selectedIds.has(edge.source) && !selectedIds.has(edge.target));
    setGraphImmediately(nextNodes, nextEdges);
    void persistGeneratorNodeSnapshot("graph-delete", {}, attachmentsRef.current, nextNodes, nextEdges, { replaceGraph: true });
    setSelectedNodeId(null);
    addActivity(`删除 ${selectedIds.size} 个节点`);
  }

  function deleteOverviewNode(nodeId: string) {
    const node = nodes.find((item) => item.id === nodeId);
    if (!node) return;
    cancelGenerationRequest(nodeId);
    const nextNodes = nodesRef.current.filter((item) => item.id !== nodeId);
    const nextEdges = edgesRef.current.filter((edge) => edge.source !== nodeId && edge.target !== nodeId);
    setGraphImmediately(nextNodes, nextEdges);
    void persistGeneratorNodeSnapshot("graph-delete", {}, attachmentsRef.current, nextNodes, nextEdges, { replaceGraph: true });
    if (selectedNodeId === nodeId) setSelectedNodeId(null);
    setOverviewNodeMenu(null);
    addActivity(`删除节点「${node.data.title}」`);
    setNotice(`已删除「${node.data.title}」`);
  }

  function resetWorkflow() {
    cancelAllGenerationRequests();
    setNodes(graph.nodes);
    setEdges(graph.edges);
    setSelectedNodeId(null);
    addActivity("恢复初始工作流");
  }

  function clearCurrentLocalWork() {
    workClearedRef.current = true;
    cancelAllGenerationRequests();
    onClearLocalData(attachmentsRef.current.map((attachment) => attachment.id));
  }

  function useSuggestedSkill(skill: SuggestedSkill) {
    setActiveSkill(skill.id);
    setPrompt(skill.prompt);
    setPanelOpen(true);
    setPanelTab("skills");
    addActivity(`选择建议 Skill：${skill.title}`);
    focusComposer();
  }

  function focusComposer() {
    window.requestAnimationFrame(() => {
      const input = promptRef.current;
      if (!input) return;
      input.focus();
      input.setSelectionRange(input.value.length, input.value.length);
    });
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
    focusComposer();
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
      line: work.line,
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
    const sourceState = selectedExecutor === "local-codex" ? localCodexState : runtimeModelsState;
    if (!selectedModel || sourceState !== "ready") {
      setNotice(selectedExecutor === "local-codex"
        ? "本机 Codex 不可用，请启动桌面端并确认 Codex 已使用 ChatGPT 登录"
        : runtimeModelsState === "unavailable" ? "后端模型服务不可用，请稍后重试" : "正在读取后端可用模型，请稍候");
      setComposerMenu("model");
      return;
    }
    const expectedGatewayMode = selectedExecutor === "local-codex" ? "local" : "backend";
    let submissionGateway = gateway;
    if (submissionGateway.mode !== expectedGatewayMode) {
      submissionGateway = await createAgentGateway(selectedExecutor);
      if (!mountedRef.current) return;
      setGateway(submissionGateway);
    }
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
      const selectedUserSkillDefinition = activeSkill?.startsWith("user:") && activeLibrarySkill?.id === activeSkill
        ? {
            title: activeLibrarySkill.title,
            description: activeLibrarySkill.description,
            guide: activeLibrarySkill.guide?.trim() || activeLibrarySkill.description,
            steps: activeLibrarySkill.steps ?? [],
            useCases: activeLibrarySkill.useCases ?? [],
          }
        : undefined;
      let current = await submissionGateway.submit({
        work: submittedWork,
        prompt: contextParts.join("\n\n"),
        skillId: canonicalAppSkillId(activeSkill ?? creationConfig.skillId) ?? work.line,
        ...(selectedUserSkillDefinition ? { skillDefinition: selectedUserSkillDefinition } : {}),
      });
      if (!mountedRef.current) return;
      setActiveJob(current);
      updateRun(current, cleanPrompt);
      addActivity("向 Agent 提交创作任务");

      if (submissionGateway.status && (current.state === "queued" || current.state === "running")) {
        for (let attempt = 0; attempt < 300 && (current.state === "queued" || current.state === "running"); attempt += 1) {
          await new Promise((resolve) => window.setTimeout(resolve, 1200));
          if (!mountedRef.current) return;
          current = await submissionGateway.status(current.id);
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
      if (current.state === "succeeded") {
        addActivity("Agent 完成创作任务");
        await materializeAgentArtifacts(current);
      }
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
    } catch {
      setNotice("浏览器未允许复制，请从地址栏复制链接");
    }
  }

  function sendHelpMessage(message = helpMessage) {
    const cleanMessage = message.trim();
    if (!cleanMessage) return;
    setHelpMessages((items) => [
      ...items,
      { sender: "user", text: cleanMessage },
      { sender: "bot", text: "已收到，我们会尽快为您处理。也可以继续补充问题细节。" },
    ]);
    setHelpMessage("");
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
    <main style={{ "--canvas-panel-width": `${agentPanelWidth}px`, "--canvas-asset-drawer-width": `${leftSidebarWidth}px` } as CSSProperties} className={`creation-canvas-shell tool-${tool}${panelOpen ? " has-agent-panel" : ""}${view === "workflow" && miniMapVisible ? " has-minimap" : ""}${drawer === "overview" ? " has-asset-drawer has-overview-drawer" : ""}`} onClick={(event) => { if (headerMenu) setHeaderMenu(null); const target = event.target as HTMLElement; if (railMenu && !target.closest(".canvas-rail-popover") && !target.closest(".creation-canvas-rail") && !target.closest(".canvas-help-contact")) { setRailMenu(null); if (railMenu === "help") setHelpPanel(null); } if (canvasInsertMenu && !target.closest(".canvas-insert-menu")) setCanvasInsertMenu(null); if (composerMenu && !target.closest(".canvas-home-composer")) setComposerMenu(null); if (overviewNodeMenu && !target.closest(".canvas-overview-node-menu") && !target.closest(".canvas-overview-node-more")) setOverviewNodeMenu(null); }}>
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
            if (assetManagerOpen) void importAssetFiles(files, false);
            else void importAssets(event.currentTarget.files);
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
          <button type="button" aria-label="发布与分享" aria-expanded={overlay === "share"} onClick={() => { setSharePanel("choices"); setOverlay("share"); setRailMenu(null); setHelpPanel(null); }}><Share2 size={16} /><span>发布与分享</span></button>
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
        <button type="button" className={railMenu === "move" ? "is-active" : ""} aria-label="移动" aria-expanded={railMenu === "move"} title="移动工具" onClick={() => { setRailMenu((current) => current === "move" ? null : "move"); setDrawer(null); setOverlay(null); setHelpPanel(null); }}><Icon name="move" /><span>移动</span></button>
        <button type="button" className={drawer === "tools" ? "is-active" : ""} aria-label="打开工具箱" title="打开工具箱" onClick={() => openDrawer("tools")}><Icon name="tools" /><span>打开工具箱</span></button>
        <button type="button" className={drawer === "assets" ? "is-active" : ""} aria-label="素材库" title="素材库" onClick={() => openDrawer("assets")}><Icon name="assets" /><span>素材库</span></button>
        <button type="button" className={drawer === "characters" ? "is-active" : ""} aria-label="角色库" title="角色库" onClick={() => openDrawer("characters")}><Icon name="character" /><span>角色库</span></button>
        <button type="button" className={drawer === "history" ? "is-active" : ""} aria-label="历史记录" title="历史记录" onClick={() => openDrawer("history")}><Icon name="history" /><span>历史记录</span></button>
        <span className="creation-canvas-rail-spacer" />
        <button type="button" className={overlay === "shortcuts" ? "is-active" : ""} aria-label="快捷键" aria-pressed={overlay === "shortcuts"} title="快捷键（?）" onClick={() => { setOverlay((current) => current === "shortcuts" ? null : "shortcuts"); setRailMenu(null); setHelpPanel(null); }}><Icon name="shortcut" /><span>快捷键</span></button>
        <button type="button" className={railMenu === "help" ? "is-active" : ""} aria-label="教程" aria-expanded={railMenu === "help"} title="帮助与教程" onClick={() => { if (railMenu === "help") { setRailMenu(null); setHelpPanel(null); } else { setRailMenu("help"); } setDrawer(null); setOverlay(null); }}><Icon name="tutorial" /><span>教程</span></button>
      </aside>

      {railMenu === "move" && <div className="canvas-rail-popover canvas-move-menu" role="menu" aria-label="移动工具">
        <button type="button" role="menuitemradio" aria-checked={tool === "select"} className={tool === "select" ? "is-active" : ""} onClick={() => { setTool("select"); setRailMenu(null); }}><Icon name="move" /><span>移动</span><kbd>V</kbd></button>
        <button type="button" role="menuitemradio" aria-checked={tool === "pan"} className={tool === "pan" ? "is-active" : ""} onClick={() => { setTool("pan"); setRailMenu(null); }}><Hand size={15} /><span>抓手工具</span><kbd>H</kbd></button>
      </div>}

      {railMenu === "help" && <div className="canvas-rail-popover canvas-help-menu" role="menu" aria-label="帮助与教程">
        <button type="button" role="menuitem" onClick={() => { setRailMenu(null); setHelpPanel(null); setOverlay("tutorial"); }}><BookOpen size={15} /><span>使用教程</span></button>
        <button type="button" role="menuitem" aria-pressed={helpPanel === "customer"} className={helpPanel === "customer" ? "is-active" : ""} onClick={() => setHelpPanel((current) => current === "customer" ? null : "customer")}><Headphones size={15} /><span>联系客服</span></button>
        <button type="button" role="menuitem" aria-pressed={helpPanel === "sales"} className={helpPanel === "sales" ? "is-active" : ""} onClick={() => setHelpPanel((current) => current === "sales" ? null : "sales")}><BriefcaseBusiness size={15} /><span>联系销售</span></button>
        <button type="button" role="menuitem" aria-pressed={helpPanel === "official"} className={helpPanel === "official" ? "is-active" : ""} onClick={() => setHelpPanel((current) => current === "official" ? null : "official")}><QrCode size={15} /><span>关注公众号</span></button>
      </div>}

      {helpPanel === "customer" && <section className="canvas-help-contact canvas-help-customer" role="dialog" aria-label="联系客服">
        <header><span><i><Headphones size={16} /></i><b>机器人 为您服务</b></span><button type="button" aria-label="关闭客服" onClick={() => setHelpPanel(null)}><X size={16} /></button></header>
        <div className="canvas-help-chat-log">
          {helpMessages.map((message, index) => <p key={`${message.sender}-${index}`} className={message.sender === "user" ? "is-user" : "is-bot"}>{message.text}</p>)}
          <section><span>热门问题</span>{["如何开发票？", "你们有客户端吗？", "如何取消续订？", "积分有效期规则", "人工客服工作时间"].map((question) => <button type="button" key={question} onClick={() => sendHelpMessage(question)}>{question}</button>)}</section>
        </div>
        <form onSubmit={(event) => { event.preventDefault(); sendHelpMessage(); }}><input value={helpMessage} onChange={(event) => setHelpMessage(event.target.value)} aria-label="输入客服消息" placeholder="输入消息..." /><button type="submit" disabled={!helpMessage.trim()} aria-label="发送客服消息"><ArrowUp size={15} /></button></form>
        <small>客服工作时间 09:00–22:00</small>
      </section>}

      {(helpPanel === "sales" || helpPanel === "official") && <section className="canvas-help-contact canvas-help-qr" role="dialog" aria-label={helpPanel === "sales" ? "联系销售二维码" : "关注公众号二维码"}>
        <span title={helpPanel === "sales" ? "微信扫码联系销售" : "微信扫码关注公众号"}><QrCode size={124} strokeWidth={1.2} /></span>
      </section>}

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
          <CanvasNodeActionsContext.Provider value={{ update: updateNodeData, run: runWorkflowNode, cancel: cancelWorkflowGeneration, derive: deriveWorkflowNode, resolveAttachment: resolveCanvasAttachment, quickAction: handleNodeQuickAction, openDirector: openDirectorStudio, openScript: (nodeId) => { setScriptWorkflowInitialDialog(null); setScriptWorkflowNodeId(nodeId); }, scriptAction: handleScriptNodeAction, openStandalone: (nodeId, workflow) => setStandaloneWorkflow({ nodeId, workflow }) }}>
          <ReactFlow<WorkflowNode, Edge>
            nodes={nodes}
            edges={edgesVisible ? edges : []}
            onInit={(instance) => { flowInstanceRef.current = instance; }}
            nodeTypes={NODE_TYPES}
            edgeTypes={EDGE_TYPES}
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
            fitViewOptions={{ padding: 0.18, maxZoom: 1 }}
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
            {nodes.length === 0 && (
              <Panel position="top-center" className="canvas-empty-start" aria-label="画布快速开始">
                <p><MousePointer2 size={20} fill="currentColor" />双击画布 自由生成节点</p>
                <div>
                  {CANVAS_STARTER_PRESETS.map((preset) => (
                    <button
                      key={preset.id}
                      type="button"
                      className={`canvas-empty-preset preset-${preset.id}`}
                      style={{ "--canvas-starter-cover": `url("${preset.cover}")` } as CSSProperties}
                      aria-label={`使用${preset.title}，对应 Skill ${preset.skill}`}
                      title={`对应项目 Skill：${preset.skill}`}
                      onClick={() => applyCanvasStarterPreset(preset)}
                    >
                      <CanvasStarterPresetIcon id={preset.id} />
                      <span>{preset.title}</span>
                      <em>去生成</em>
                    </button>
                  ))}
                </div>
              </Panel>
            )}
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
              <button type="button" role="menuitem" onClick={() => { setLibraryInsertPoint({ x: canvasInsertMenu.flowX, y: canvasInsertMenu.flowY }); setCanvasInsertMenu(null); setLibraryTab("square"); setLibraryCategory("推荐"); setLibraryQuery(""); setLibraryModelFilter("全部"); setLibraryModelMenuOpen(false); setLibraryMinimized(false); setOverlay("style-library"); }}><span>风格库</span></button>
              <button type="button" role="menuitem" onClick={() => { setLibraryInsertPoint({ x: canvasInsertMenu.flowX, y: canvasInsertMenu.flowY }); setCanvasInsertMenu(null); setLibraryTab("square"); setLibraryCategory("推荐"); setLibraryQuery(""); setLibraryModelFilter("全部"); setLibraryModelMenuOpen(false); setLibraryMinimized(false); setOverlay("effect-library"); }}><span>特效库</span></button>
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
              <button type="button" className="canvas-overview-collapse" aria-label="资产管理" title="资产管理" aria-haspopup="dialog" aria-expanded={assetManagerOpen} onClick={openAssetManager}><Icon name="asset-manager" /></button>
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
            <div>{ADD_NODE_OPTIONS.map((item) => <button key={item.id} type="button" className={item.id === "script" && addDrawerSubmenu === "script" ? "is-active" : ""} aria-expanded={item.id === "script" ? addDrawerSubmenu === "script" : undefined} onClick={() => { if (item.id === "script") { setAddDrawerSubmenu((current) => current === "script" ? null : "script"); return; } if (item.id === "library") { setDrawer("assets"); return; } addWorkflowNode(item.kind, { title: item.label, ...((item.id === "text" || item.id === "image") ? { variant: "libtv-generator" as const } : {}), ...(item.id === "director" ? { description: "在3D空间中搭建场景并进行多视角截图", variant: "director" as const } : {}) }); }}><span><Icon name={item.id === "director" ? "workflow" : item.kind} /></span><b>{item.label}</b>{item.badge && <i>{item.badge}</i>}{(item.id === "script" || item.id === "library") && <ChevronRight size={14} />}</button>)}</div>
            {addDrawerSubmenu === "script" && <div className="canvas-add-script-submenu" role="menu" aria-label="脚本类型"><button type="button" role="menuitem" onClick={() => addWorkflowNode("script", { title: "脚本生成器", description: "描述剧情片段、故事，为你生成分镜脚本", variant: "script-new" })}><span>脚本</span><i>NEW</i></button><button type="button" role="menuitem" onClick={() => addWorkflowNode("script", { title: "脚本生成器", description: "描述剧情或添加角色参考、视频参考等，为你生成分镜脚本", variant: "script-legacy" })}><span>脚本（旧版）</span><i>Beta</i></button></div>}
            <small>添加资源</small>
            <button type="button" className="canvas-add-resource" onClick={() => { setPendingUploadPoint(null); fileInputRef.current?.click(); }}><Upload size={16} /><b>上传</b></button>
            <button type="button" className="canvas-add-resource" onClick={openDrawerHistoryPicker}><Icon name="history" /><b>从生成历史选择</b></button>
          </div>}
          {drawer === "tools" && <div className="canvas-toolbox-gallery">
            <nav role="tablist" aria-label="工具箱分类">
              <button type="button" role="tab" aria-selected={toolboxTab === "mine"} className={toolboxTab === "mine" ? "is-active" : ""} onClick={() => { setToolboxTab("mine"); setToolboxGuideOpen(false); setToolboxClassicDetail(null); }}>我的工具箱</button>
              <button type="button" className={toolboxGuideOpen ? "is-active" : ""} aria-haspopup="dialog" aria-expanded={toolboxGuideOpen} onClick={() => { setToolboxGuideOpen((open) => !open); setToolboxDetail(null); setToolboxClassicDetail(null); }}><Info size={12} />工具箱模板说明</button>
              <button type="button" role="tab" aria-selected={toolboxTab === "classic"} className={toolboxTab === "classic" ? "is-active" : ""} onClick={() => { setToolboxTab("classic"); setToolboxGuideOpen(false); setToolboxDetail(null); }}>周星驰经典名场面</button>
            </nav>

            {toolboxGuideOpen && <section className="canvas-toolbox-guide-popover" role="dialog" aria-label="工具箱模板说明">
              <button type="button" aria-label="关闭工具箱模板说明" onClick={() => setToolboxGuideOpen(false)}><X size={14} /></button>
              <Info size={18} />
              <div><strong>工具箱模板说明</strong><p>使用工具箱模板加速创作，快速构建你的专属工具箱。点击封面可查看用途、输入和生成节点，点击“使用”会把整套可编辑节点发送到当前画布。</p><a href="https://liblibai.feishu.cn/wiki/Loxfw6XHziYRk0kKzdjcFfp9nhb#share-EGsydYnauomw6rxz7SAc313Bnfh" target="_blank" rel="noreferrer">查看详细教程 <ExternalLink size={12} /></a></div>
            </section>}

            {toolboxTab === "mine" ? <div className="canvas-toolbox-grid">
              {TOOLBOX_TEMPLATES.map((template, index) => <article key={template.id} className="canvas-toolbox-card" title={template.description}>
                <div className="canvas-toolbox-preview">
                  <img src={template.cover} alt={`【预设】${template.title}`} loading="lazy" />
                  <em>{String(index + 1).padStart(2, "0")}</em>
                  <button type="button" className="canvas-toolbox-preview-use" onClick={() => applyToolboxTemplate(template)}><WandSparkles size={14} />使用</button>
                </div>
                <footer><button type="button" className="canvas-toolbox-title" onClick={() => { setToolboxDetail(template); setToolboxGuideOpen(false); }}><b>{template.title}</b></button><button type="button" onClick={() => applyToolboxTemplate(template)}>使用</button></footer>
              </article>)}
            </div> : <section className="canvas-toolbox-classics" aria-label="周星驰经典名场面">
              <header><div><strong>周星驰经典名场面</strong><small>选择场面后会创建可替换角色、场景和提示词的参考工作流</small></div><span>{TOOLBOX_CLASSICS.length} 个模板</span></header>
              <div>{TOOLBOX_CLASSICS.map((template) => <article key={template.id}>
                <button type="button" className="canvas-toolbox-classic-cover" onClick={() => { setToolboxClassicDetail(template); setToolboxGuideOpen(false); }}><img src={template.cover} alt={template.title} loading="lazy" /><span><Info size={14} />查看详情</span></button>
                <footer><button type="button" onClick={() => setToolboxClassicDetail(template)}><b>{template.title}</b><small>{template.description}</small></button><button type="button" onClick={() => applyToolboxClassic(template)}>使用</button></footer>
              </article>)}</div>
            </section>}

            {toolboxDetail && <section className="canvas-toolbox-detail" role="dialog" aria-modal="true" aria-label={`${toolboxDetail.title}详情`}>
              <button type="button" className="canvas-toolbox-detail-close" aria-label="关闭工具详情" onClick={() => setToolboxDetail(null)}><X size={16} /></button>
              <figure><img src={toolboxDetail.cover} alt={toolboxDetail.title} /><span>{toolboxDetail.category}</span></figure>
              <div><small>TOOLBOX PRESET</small><h3>{toolboxDetail.title}</h3><p>{toolboxDetail.description}</p><dl><div><dt>输入</dt><dd>{toolboxDetail.inputLabel}</dd></div><div><dt>输出</dt><dd>{toolboxDetail.resultLabel}</dd></div><div><dt>节点</dt><dd>{toolboxDetail.recipe === "storyboard" ? "故事 + 角色参考 + 分镜 + 结果" : "参考素材 + 模板提示词 + 生成结果"}</dd></div></dl><blockquote>{toolboxDetail.prompt}</blockquote><footer><button type="button" onClick={() => setToolboxDetail(null)}>返回</button><button type="button" onClick={() => applyToolboxTemplate(toolboxDetail)}><WandSparkles size={14} />使用模板</button></footer></div>
            </section>}

            {toolboxClassicDetail && <section className="canvas-toolbox-detail" role="dialog" aria-modal="true" aria-label={`${toolboxClassicDetail.title}详情`}>
              <button type="button" className="canvas-toolbox-detail-close" aria-label="关闭经典名场面详情" onClick={() => setToolboxClassicDetail(null)}><X size={16} /></button>
              <figure><img src={toolboxClassicDetail.cover} alt={toolboxClassicDetail.title} /><span>经典场面</span></figure>
              <div><small>SCENE REFERENCE</small><h3>{toolboxClassicDetail.title}</h3><p>{toolboxClassicDetail.description}</p><dl><div><dt>输入</dt><dd>替换角色或场景素材</dd></div><div><dt>输出</dt><dd>可编辑的视频模板节点</dd></div><div><dt>处理</dt><dd>提取调度与节奏，不复制原片台词和人物外貌</dd></div></dl><footer><button type="button" onClick={() => setToolboxClassicDetail(null)}>返回</button><button type="button" onClick={() => applyToolboxClassic(toolboxClassicDetail)}><WandSparkles size={14} />使用模板</button></footer></div>
            </section>}
          </div>}
          {drawer === "assets" && <div className="canvas-library-menu">
            <button type="button" onClick={() => { setDrawer(null); setLibraryTab("square"); setLibraryCategory("推荐"); setLibraryQuery(""); setLibraryModelFilter("全部"); setLibraryModelMenuOpen(false); setLibraryMinimized(false); setOverlay("style-library"); }}><span><Sparkles size={19} /></span><span><b>风格库</b><small>新增风格节点 <i>NEW</i></small></span><ChevronDown size={15} /></button>
            <button type="button" onClick={() => { setDrawer(null); setLibraryTab("square"); setLibraryCategory("推荐"); setLibraryQuery(""); setLibraryModelFilter("全部"); setLibraryModelMenuOpen(false); setLibraryMinimized(false); setOverlay("effect-library"); }}><span><WandSparkles size={19} /></span><span><b>特效库</b><small>新增特效节点 <i>NEW</i></small></span><ChevronDown size={15} /></button>
          </div>}
          {drawer === "characters" && <div className="canvas-character-library">
            <section className="canvas-character-feature"><div className="canvas-character-copy"><small>当前角色</small><h2>{selectedCharacter.name}</h2><p>{selectedCharacter.detail}</p><p>保持人物外貌、气质与服装在后续镜头中的连续一致，可随时在节点中继续调整。</p><button type="button" onClick={() => { addWorkflowNode("text", { title: selectedCharacter.name, description: selectedCharacter.detail, assetName: "角色参考" }); setNotice(`已将「${selectedCharacter.name}」应用至画布`); }}>应用至画布</button></div><div className="canvas-character-previews">{["立绘", "脸部近景", "表情参考", "三视图"].map((label, index) => <span key={label} className={`character-preview-${index}`}><UserRound size={38} /><b>{label}</b></span>)}</div></section>
            <header><strong>角色筛选</strong><label><input type="checkbox" checked={characterRecentOnly} onChange={(event) => setCharacterRecentOnly(event.target.checked)} /> 最近使用</label></header>
            <div className="canvas-character-carousel-shell"><button type="button" className="canvas-character-carousel-arrow is-prev" aria-label="prev" onClick={() => scrollCharacterCarousel(-1)}><ChevronRight size={17} /></button><div ref={characterCarouselRef} className="canvas-character-carousel">{visibleCharacterPresets.map((character) => <button key={character.id} type="button" className={selectedCharacterId === character.id ? "is-selected" : ""} onClick={() => selectCharacter(character.id)}><span><UserRound size={25} /></span><b>{character.name}</b><small>{character.detail}</small></button>)}</div><button type="button" className="canvas-character-carousel-arrow is-next" aria-label="next" onClick={() => scrollCharacterCarousel(1)}><ChevronRight size={17} /></button></div>
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

      {assetManagerOpen && (
        <div className="canvas-asset-manager-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.target !== event.currentTarget) return;
          setAssetManagerOpen(false);
          setAssetManagerNewMenuOpen(false);
          setAssetManagerSelectedIds([]);
        }}>
          <section className="canvas-asset-manager-modal" role="dialog" aria-modal="true" aria-label="资产管理" onMouseDown={(event) => event.stopPropagation()}>
            <header><strong>资产管理</strong><button type="button" aria-label="关闭资产管理" onClick={() => { setAssetManagerOpen(false); setAssetManagerNewMenuOpen(false); setAssetManagerSelectedIds([]); }}><X size={17} /></button></header>
            <div className="canvas-asset-manager-body">
              <aside aria-label="资产库">
                <button type="button" className={assetManagerSource === "personal" ? "is-active" : ""} onClick={() => { setAssetManagerSource("personal"); setAssetManagerSelectedIds([]); setAssetManagerNewMenuOpen(false); }}><Folder size={15} />个人资产库</button>
                <button type="button" className={assetManagerSource === "kling" ? "is-active" : ""} onClick={() => { setAssetManagerSource("kling"); setAssetManagerSelectedIds([]); setAssetManagerNewMenuOpen(false); }}><UserRound size={15} />可灵主体库</button>
              </aside>
              <main>
                <h3>{assetManagerSource === "personal" ? "个人资产库" : "可灵主体库"}</h3>
                {assetManagerSource === "personal" ? <>
                  <div className="canvas-asset-manager-toolbar">
                    <label><input autoFocus aria-label="搜索个人资产库" placeholder="请输入搜索内容" value={assetManagerQuery} onChange={(event) => setAssetManagerQuery(event.target.value)} /><Search size={15} /></label>
                    <button type="button" className={assetManagerBatchMode ? "is-active" : ""} onClick={() => { setAssetManagerBatchMode((enabled) => !enabled); setAssetManagerSelectedIds([]); }}>{assetManagerBatchMode ? "退出批量" : "批量操作"}</button>
                    <span className="canvas-asset-manager-new-wrap"><button type="button" className="is-primary" aria-expanded={assetManagerNewMenuOpen} onClick={() => setAssetManagerNewMenuOpen((open) => !open)}><Plus size={15} />新建</button>{assetManagerNewMenuOpen && <span className="canvas-asset-manager-new-menu" role="menu"><button type="button" role="menuitem" onClick={() => { setPendingUploadPoint(null); setAssetManagerNewMenuOpen(false); fileInputRef.current?.click(); }}><Upload size={14} />上传素材</button><button type="button" role="menuitem" onClick={() => { setOverviewAssetGroupName("新建文件夹"); setAssetManagerNewMenuOpen(false); setNotice("已新建资产文件夹"); }}><Folder size={14} />新建文件夹</button></span>}</span>
                  </div>
                  <nav className="canvas-asset-manager-categories" aria-label="资产分类">{(["全部", "其它", "人物", "场景", "物品", "风格", "音效"] as AssetManagerCategory[]).map((category) => <button key={category} type="button" className={assetManagerCategory === category ? "is-active" : ""} onClick={() => { setAssetManagerCategory(category); setAssetManagerSelectedIds([]); setAssetManagerNewMenuOpen(false); }}>{category}</button>)}</nav>
                  <div className="canvas-asset-manager-grid">
                    {(assetManagerCategory === "全部" || assetManagerCategory === "其它") && (!assetManagerQuery.trim() || overviewAssetGroupName.toLocaleLowerCase().includes(assetManagerQuery.trim().toLocaleLowerCase())) && <button type="button" className={assetManagerSelectedIds.includes("folder:unclassified") ? "canvas-managed-folder is-selected" : "canvas-managed-folder"} onClick={() => toggleManagedAsset("folder:unclassified")}><span><Folder size={40} />{assetManagerSelectedIds.includes("folder:unclassified") && <i><Check size={13} /></i>}</span><b>{overviewAssetGroupName}</b><small>2026-08-03</small></button>}
                    {visibleManagedAssets.map((attachment) => <button key={attachment.id} type="button" className={assetManagerSelectedIds.includes(attachment.id) ? "canvas-managed-asset is-selected" : "canvas-managed-asset"} onClick={() => toggleManagedAsset(attachment.id)}><span><Icon name={attachmentKind(attachment)} />{assetManagerSelectedIds.includes(attachment.id) && <i><Check size={13} /></i>}</span><b>{attachment.name}</b><small>{attachmentAssetTag(attachment)} · {Math.max(1, Math.round(attachment.size / 1024))} KB</small></button>)}
                    {!visibleManagedAssets.length && !((assetManagerCategory === "全部" || assetManagerCategory === "其它") && (!assetManagerQuery.trim() || overviewAssetGroupName.toLocaleLowerCase().includes(assetManagerQuery.trim().toLocaleLowerCase()))) && <div className="canvas-asset-manager-empty"><Folder size={28} /><strong>没有找到相关资产</strong><span>换个分类或关键词试试</span></div>}
                  </div>
                  <footer><button type="button" className="canvas-asset-manager-send" disabled={!assetManagerSelectedIds.length} onClick={sendManagedAssetsToCanvas}>发送到画布</button><span /><button type="button" disabled aria-label="上一页"><ChevronRight size={13} /></button><button type="button" className="is-current">1</button><button type="button" disabled aria-label="下一页"><ChevronRight size={13} /></button><button type="button">20条/页 <ChevronDown size={12} /></button></footer>
                </> : <div className="canvas-asset-manager-kling-empty"><UserRound size={32} /><strong>暂无可灵主体</strong><span>创建的主体会集中显示在这里</span><button type="button" onClick={() => setNotice("可灵主体创建入口已打开")}>创建主体</button></div>}
              </main>
            </div>
          </section>
        </div>
      )}

      {activeDirectorNode && activeDirectorScene && (
        <Suspense fallback={<div className="canvas-director-loading" role="status"><Clock3 size={22} />正在加载 3D 导演台…</div>}>
          <DirectorStudio
            nodeTitle={activeDirectorNode.data.title}
            initialPrompt={String(activeDirectorNode.data.prompt ?? "")}
            initialReferenceOpen={directorReferenceNodeId === activeDirectorNode.id}
            initialRunPrompt={directorRunPromptNodeId === activeDirectorNode.id}
            imageAssets={attachments.filter((attachment) => attachment.type.startsWith("image/")).map((attachment) => ({ id: attachment.id, name: attachment.name }))}
            value={activeDirectorScene}
            onChange={(directorScene) => {
              updateNodeData(activeDirectorNode.id, { directorScene });
              void persistGeneratorNodeSnapshot(
                activeDirectorNode.id,
                { directorScene },
                attachmentsRef.current,
                nodes,
                edges,
                { writeCloud: false },
              );
            }}
            persistScene={(directorScene) => persistGeneratorNodeSnapshot(activeDirectorNode.id, { directorScene })}
            onPromptChange={(nextPrompt) => {
              updateNodeData(activeDirectorNode.id, { prompt: nextPrompt });
              void persistGeneratorNodeSnapshot(
                activeDirectorNode.id,
                { prompt: nextPrompt },
                attachmentsRef.current,
                nodes,
                edges,
                { writeCloud: false },
              );
            }}
            onClose={(directorScene) => {
              void persistGeneratorNodeSnapshot(activeDirectorNode.id, { directorScene });
              setDirectorStudioNodeId(null);
              setDirectorReferenceNodeId(null);
              setDirectorRunPromptNodeId(null);
            }}
            registerFile={registerDirectorFile}
            resolveAttachment={resolveCanvasAttachment}
            sendShotToCanvas={(shot, camera) => sendDirectorShotToCanvas(activeDirectorNode.id, shot, camera)}
            buildScene={buildDirectorSceneWithModel}
            generatePanorama={generateDirectorPanorama}
            analyzeReference={analyzeDirectorReference}
            notify={setNotice}
          />
        </Suspense>
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
            {panelTab === "conversation" && (showAgentStarter ? <section className="canvas-agent-starter"><header><p><Sparkles size={14} />用 Skill，开启今天的故事</p><button type="button" hidden aria-hidden="true" tabIndex={-1} onClick={() => setSkillBatchIndex((index) => (index + 1) % AGENT_SKILL_BATCHES.length)}><RotateCcw size={12} />换一批</button></header><div>{AGENT_SKILL_BATCHES[skillBatchIndex % AGENT_SKILL_BATCHES.length].map((skill) => <button key={skill.id} type="button" aria-label={`使用 Skill ${skill.title}`} onClick={() => useLibrarySkill(skill)}><span className={`canvas-agent-starter-cover line-${skill.line ?? work.line}`}><LineIcon line={skill.line ?? work.line} /></span><span><b>{skill.title}</b><small>{skill.slug}</small></span></button>)}</div></section> : <section className="canvas-agent-conversation-blank" aria-label="当前对话" />)}
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
              <div className="canvas-agent-security"><b>密钥只保存在服务端</b><p>浏览器只提交 REST 任务，不会接触模型 API Key。</p></div>
              <button type="button" className="canvas-clear-data-button" onClick={() => setOverlay("clear-data")}><Icon name="close" /><span><b>清除本机作品数据</b><small>删除当前作品、画布快照和本机素材</small></span></button>
            </section>}
          </div>
          <div className="canvas-sidebar-resizer canvas-sidebar-resizer-right" role="separator" aria-label="调整 AI 助手面板宽度" onPointerDown={(event) => { event.preventDefault(); beginSidebarResize("right", event.clientX); }} />
        </aside>
      )}

      {panelOpen ? (
        <section className="skill-composer canvas-home-composer" onClick={(event) => event.stopPropagation()}>
          <div className={`composer-prompt-row${activeSkill || selectedModel ? " has-selection" : ""}`}>
            {selectedModel && (
              <div className="composer-selected-token">
                <button className="token-main" type="button" title="更换模型" onClick={() => setComposerMenu(composerMenu === "model" ? null : "model")}>
                  <Box size={15} /><span>{selectedModel.name}</span>
                </button>
                <button className="token-remove" type="button" title="移除模型" aria-label={`移除 ${selectedModel.name}`} onClick={() => { setCreationConfig((current) => ({ ...current, model: { ...current.model, modelId: "" } })); focusComposer(); }}><X size={12} /></button>
              </div>
            )}
            {activeSkill && activeSkillTitle && (
              <div className="composer-selected-token">
                <button className="token-main" type="button" title="更换 Skill" onClick={() => setComposerMenu(composerMenu === "skill" ? null : "skill")}>
                  <ClipboardPenLine size={15} /><span>{activeSkillTitle}</span>
                </button>
                <button className="token-remove" type="button" title="移除 Skill" aria-label={`移除 ${activeSkillTitle}`} onClick={() => { setActiveSkill(null); focusComposer(); }}><X size={12} /></button>
              </div>
            )}
            <textarea
              ref={promptRef}
              value={prompt}
              aria-label="创作需求"
              placeholder={prompt || activeSkill || selectedModel ? "" : "开始你的创作，或者 @ 引用工作流/节点/资源"}
              onChange={(event) => setPrompt(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Escape") {
                  setComposerMenu(null);
                  return;
                }
                if (event.key === "Backspace" && !prompt) {
                  event.preventDefault();
                  if (activeSkill) setActiveSkill(null);
                  else if (selectedModel) setCreationConfig((current) => ({ ...current, model: { ...current.model, modelId: "" } }));
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
              <button className={composerMenu === "model" ? "composer-menu-button icon-only active" : "composer-menu-button icon-only"} type="button" title="选择模型" aria-label="选择模型" aria-expanded={composerMenu === "model"} onClick={() => {
                const opening = composerMenu !== "model";
                setComposerMenu(opening ? "model" : null);
                if (opening && !localCodexProbeRequested) setLocalCodexProbeRequested(true);
                if (opening && (runtimeModelsState === "unavailable" || localCodexState === "unavailable")) setRuntimeModelsRefresh((current) => current + 1);
              }}>
                <Box size={18} strokeWidth={1.6} />
              </button>
              {composerMenu === "model" && (
                <div className="floating-panel model-picker" role="dialog" aria-label="选择模型">
                  <div className="floating-panel-title"><strong>选择模型</strong></div>
                  <div className="model-executor-tabs" aria-label="模型调用方式">
                    <button type="button" className={selectedExecutor === "backend" ? "active" : ""} aria-pressed={selectedExecutor === "backend"} onClick={() => chooseModelExecutor("backend")}>后端服务</button>
                    <button type="button" className={selectedExecutor === "local-codex" ? "active" : ""} aria-pressed={selectedExecutor === "local-codex"} onClick={() => chooseModelExecutor("local-codex")}>
                      本机 Codex（订阅）
                      <i className={`state-${localCodexState}`} />
                    </button>
                  </div>
                  <div className="segmented-tabs" role="tablist">
                    {RUNTIME_MODEL_MODALITIES.map((item) => (
                      <button key={item} className={modelModality === item ? "active" : ""} type="button" role="tab" aria-selected={modelModality === item} onClick={() => { if (item !== "text" && selectedExecutor === "local-codex") chooseModelExecutor("backend"); setModelModality(item); }}>{CANVAS_MODALITY_LABELS[item]}</button>
                    ))}
                  </div>
                  <div className="model-section-label">{CANVAS_MODALITY_LABELS[modelModality]}</div>
                  {(modelModality === "text" || modelModality === "image") && (
                    <div className={`model-runtime-status state-${selectedExecutor === "local-codex" ? localCodexState : runtimeModelsState}`}>
                      <i />
                      {selectedExecutor === "local-codex"
                        ? localCodexState === "loading"
                          ? "正在读取本机 Codex 模型…"
                          : localCodexState === "ready"
                            ? `当前 ChatGPT 账号已发现 ${localCodexModels.length} 个可选 Codex 模型`
                            : "未检测到桌面端，或 Codex 尚未使用 ChatGPT 登录"
                        : runtimeModelsState === "loading"
                          ? "正在读取后端开放模型…"
                          : runtimeModelsState === "ready"
                            ? `后端已连接 ${runtimeModels.filter((model) => model.modality === modelModality).length} 个可调用模型`
                            : runtimeModelsState === "unavailable"
                              ? "后端模型服务当前不可用"
                              : "连接后端后会显示实际开放模型"}
                    </div>
                  )}
                  <p className="model-runtime-note">本机 Codex 是执行方式：使用桌面端已登录的 ChatGPT 账号运行完整 Skill/文本 Agent，额度以该账号为准；首次提交会弹出桌面授权。图片与视频直接生成仍走后端。</p>
                  <div className="model-list">
                    {selectableModelGroups[modelModality].map((model) => (
                      <div key={`${selectedExecutor}:${model.id}`} className="model-row">
                        <button className="model-row-main" type="button" onClick={() => {
                          setCreationConfig((current) => ({
                            ...current,
                            executor: selectedExecutor,
                            model: { modality: model.modality, modelId: model.modelId ?? model.id, ...(model.providerSpec ? { providerSpec: model.providerSpec } : {}) },
                          }));
                          setModelModality(model.modality);
                          setComposerMenu(null);
                          setNotice(`已选择 ${model.name}`);
                          focusComposer();
                        }}>
                          <span className={`model-mark provider-${model.provider.toLocaleLowerCase().replace(/\W+/g, "-")}`}>{model.name.slice(0, 1)}</span>
                          <span className="model-copy">
                            <span className="model-name">
                              <b>{model.name}</b>
                              <em className={selectedExecutor === "local-codex" ? `model-local-badge state-${localCodexState}` : "model-connected-badge"}>
                                {selectedExecutor === "local-codex"
                                  ? localCodexState === "ready" ? "本机可用" : localCodexState === "loading" ? "检测中" : "需桌面端"
                                  : "已连接"}
                              </em>
                            </span>
                            <small>{model.description}</small>
                          </span>
                          <Plus size={16} />
                        </button>
                      </div>
                    ))}
                    {(selectedExecutor === "local-codex" ? localCodexState : runtimeModelsState) !== "loading" && !selectableModelGroups[modelModality].length && (
                      <p className="model-runtime-empty">当前调用方式暂无可用{CANVAS_MODALITY_LABELS[modelModality]}模型。</p>
                    )}
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
                          <span className="picker-skill-icon"><LineIcon line={skill.line ?? work.line} /></span>
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
                <RotateCcw size={18} strokeWidth={1.6} />
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
      ) : null}

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
        <div className="canvas-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) { setOverlay(null); setSharePanel("choices"); setLibraryInsertPoint(null); setLibraryDetail(null); setLibraryModelMenuOpen(false); } }}>
          <section className={`canvas-modal canvas-modal-${overlay}${overlay === "share" ? ` share-${sharePanel}` : ""}${libraryMinimized && (overlay === "style-library" || overlay === "effect-library") ? " is-minimized" : ""}`} role="dialog" aria-modal="true" aria-label={overlay === "shortcuts" ? "快捷键" : overlay === "tutorial" ? "画布教程" : overlay === "share" ? sharePanel === "link" ? "分享链接" : sharePanel === "publish" ? "发布作品到LibTV" : "发布与分享" : overlay === "style-library" ? "风格库" : overlay === "effect-library" ? "特效库" : "清除本机作品数据"}>
            <header><div><small>{overlay === "share" ? "CANVAS" : overlay === "clear-data" ? "LOCAL DATA" : overlay === "style-library" || overlay === "effect-library" ? "ASSET LIBRARY" : "CANVAS GUIDE"}</small><strong>{overlay === "shortcuts" ? "快捷键" : overlay === "tutorial" ? "快速上手" : overlay === "share" ? sharePanel === "link" ? "分享链接" : sharePanel === "publish" ? "发布作品到LibTV" : "发布与分享" : overlay === "style-library" ? "风格库" : overlay === "effect-library" ? "特效库" : "清除本机作品数据"}</strong></div>{overlay === "share" && sharePanel !== "choices" && <button type="button" onClick={() => setSharePanel("choices")} aria-label="返回发布与分享"><ArrowLeft size={14} /></button>}{(overlay === "style-library" || overlay === "effect-library") && <button type="button" onClick={() => setLibraryMinimized((minimized) => !minimized)} aria-label={libraryMinimized ? "展开素材库" : "最小化素材库"}>{libraryMinimized ? <Maximize2 size={15} /> : <Minimize2 size={15} />}</button>}<button type="button" onClick={() => { setOverlay(null); setSharePanel("choices"); setLibraryInsertPoint(null); setLibraryDetail(null); setLibraryModelMenuOpen(false); }} aria-label="关闭"><Icon name="close" /></button></header>
            {overlay === "shortcuts" ? <div className="canvas-shortcut-list">{CANVAS_SHORTCUT_GROUPS.map((group) => <section key={group.title}><h3>{group.title}</h3>{group.items.map(([label, keys]) => <span key={`${group.title}-${label}`}><b>{label}</b><kbd>{keys}</kbd></span>)}</section>)}</div> : overlay === "tutorial" ? <ol className="canvas-tutorial-list"><li><i>1</i><span><b>选择或添加节点</b><small>从左侧添加文本、图片、音频等工作流节点。</small></span></li><li><i>2</i><span><b>连接并整理流程</b><small>拖动节点连接点建立依赖，再用底部整理按钮排列。</small></span></li><li><i>3</i><span><b>让 Agent 执行</b><small>选择右侧建议 Skill，或在底部直接输入下一步任务。</small></span></li></ol> : overlay === "share" && sharePanel === "choices" ? <div className="canvas-share-actions">
              <button type="button" onClick={() => setSharePanel("publish")}><span><Upload size={17} /></span><span><b>在LibTV上发布</b><small>发布你的作品和创作过程，让更多创作者看到。</small></span></button>
              <button type="button" onClick={() => setSharePanel("link")}><span><Link2 size={17} /></span><span><b>分享链接</b><small>拥有此链接的人可以查看并复制你的画布。</small></span></button>
            </div> : overlay === "share" && sharePanel === "link" ? <div className="canvas-share-link-panel">
              <label><span>画布链接</span><div><Link2 size={15} /><code>{window.location.href}</code><button type="button" onClick={() => void copyShareLink()}>复制链接</button></div></label>
              <section><strong>访问权限设置</strong><span>选择范围</span><button type="button" onClick={() => setNotice("当前画布仅自己可见")}>仅自己可见 <ChevronDown size={14} /></button></section>
            </div> : overlay === "share" ? <form className="canvas-publish-form" onSubmit={(event) => { event.preventDefault(); setNotice("发布信息已保存；正式投稿服务暂未接入"); setOverlay(null); setSharePanel("choices"); }}>
              <div className="canvas-publish-intro"><strong>发布作品到LibTV</strong><p>您的作品将展示到LibTV Show，方便大家交流使用</p></div>
              <div className="canvas-publish-media"><button type="button" onClick={() => fileInputRef.current?.click()}><Play size={20} /><span>选择视频</span></button><button type="button" onClick={() => fileInputRef.current?.click()}><Upload size={20} /><span>选择封面<small>建议上传横版图片</small></span></button><span><Icon name="workflow" /><b>当前画布</b><small>画布 1</small></span></div>
              <label><span>作品名称 *</span><input required aria-label="请输入作品名称" defaultValue={workName.trim() || "画布 1"} /></label>
              <label><span>作品描述 *</span><textarea required aria-label="请输入作品描述" /></label>
              <label><span>活动标签</span><input aria-label="不参与" defaultValue="不参与" /></label>
              <label><span>参赛赛道</span><input aria-label="请选择参赛单元" disabled placeholder="请选择参赛单元" /></label>
              <label><span>社媒链接</span><input aria-label="请添加您在社媒发布该作品的链接" placeholder="请添加您在社媒发布该作品的链接" /></label>
              <div className="canvas-publish-switches"><label><span>公开画布</span><input type="checkbox" role="switch" defaultChecked /></label><label><span>公开 Agent 对话</span><input type="checkbox" role="switch" defaultChecked /></label></div>
              <label className="canvas-publish-agreement"><input type="checkbox" defaultChecked />点击发布即代表同意《LibTV创作许可服务协议》</label>
              <button type="submit" className="canvas-publish-submit">发布并投稿</button>
            </form> : overlay === "style-library" || overlay === "effect-library" ? <div className="canvas-preset-library">
              <nav role="tablist" aria-label="素材库分类">
                <button type="button" role="tab" aria-selected={libraryTab === "square"} className={libraryTab === "square" ? "is-active" : ""} onClick={() => setLibraryTab("square")}>{overlay === "style-library" ? "风格广场" : "特效广场"}</button>
                <button type="button" role="tab" aria-selected={libraryTab === "favorite"} className={libraryTab === "favorite" ? "is-active" : ""} onClick={() => setLibraryTab("favorite")}>我的收藏</button>
                <button type="button" role="tab" aria-selected={libraryTab === "recent"} className={libraryTab === "recent" ? "is-active" : ""} onClick={() => setLibraryTab("recent")}>最近使用</button>
                <label><Search size={15} /><input aria-label={overlay === "style-library" ? "搜索风格名称、作者" : "搜索特效名称、作者"} value={libraryQuery} onChange={(event) => setLibraryQuery(event.target.value)} placeholder={overlay === "style-library" ? "搜索风格名称、作者" : "搜索特效名称、作者"} /></label>
              </nav>
              <aside>{(overlay === "effect-library" ? ["推荐"] : PRESET_CATEGORIES).map((category) => <button key={category} type="button" className={libraryCategory === category ? "is-active" : ""} onClick={() => setLibraryCategory(category)}>{category}</button>)}</aside>
              <section><header><label><input type="checkbox" checked={libraryCommercialOnly} onChange={(event) => setLibraryCommercialOnly(event.target.checked)} /> 仅看可商用</label><div className="canvas-preset-model-filter"><button type="button" aria-expanded={libraryModelMenuOpen} onClick={() => setLibraryModelMenuOpen((open) => !open)}>{libraryModelFilter} <ChevronDown size={13} /></button>{libraryModelMenuOpen && <div role="menu" aria-label="模型筛选">{(overlay === "style-library" ? STYLE_MODEL_FILTERS : EFFECT_MODEL_FILTERS).map((model) => <button key={model} type="button" role="menuitem" className={libraryModelFilter === model ? "is-active" : ""} onClick={() => { setLibraryModelFilter(model); setLibraryModelMenuOpen(false); }}>{model}</button>)}</div>}</div></header>
                {visibleLibraryPresets.length ? <div>{visibleLibraryPresets.map((preset, index) => <article key={preset.name} className="canvas-preset-card" onClick={() => {
                  addWorkflowNode(overlay === "style-library" ? "image" : "video", { title: preset.name, description: overlay === "style-library" ? `应用「${preset.name}」风格生成画面` : `应用「${preset.name}」视频特效`, prompt: preset.name, position: libraryInsertPoint ?? undefined, connectToAnchor: !libraryInsertPoint });
                  setLibraryRecent((items) => [preset.name, ...items.filter((item) => item !== preset.name)].slice(0, 20));
                  setLibraryInsertPoint(null);
                  setOverlay(null);
                  setNotice(`已添加「${preset.name}」节点`);
                }}>
                  <span className={`canvas-preset-preview preview-${index % 6}`}><Sparkles size={25} /><i>{preset.model}</i><div><button type="button" aria-label={libraryFavorites.has(preset.name) ? `取消收藏${preset.name}` : `收藏${preset.name}`} className={libraryFavorites.has(preset.name) ? "is-active" : ""} onClick={(event) => { event.stopPropagation(); setLibraryFavorites((items) => { const next = new Set(items); if (next.has(preset.name)) next.delete(preset.name); else next.add(preset.name); return next; }); }}><Star size={14} fill={libraryFavorites.has(preset.name) ? "currentColor" : "none"} /></button><button type="button" aria-label={`${preset.name}详情`} onClick={(event) => { event.stopPropagation(); setLibraryDetail(preset); }}><Info size={14} /></button></div></span>
                  <b>{preset.name}</b><small><span>{preset.commercial ? "商用" : "非商用"}</span>{preset.author}<i />{preset.uses}</small>
                </article>)}</div> : <div className="canvas-preset-empty"><Search size={24} /><strong>没有找到相关素材</strong><span>换个分类或关键词试试</span></div>}
              </section>
              {libraryDetail && <div className="canvas-preset-detail" role="dialog" aria-label={`${libraryDetail.name}详情`}><button type="button" aria-label="关闭素材详情" onClick={() => setLibraryDetail(null)}><X size={16} /></button><div className="canvas-preset-detail-preview"><Sparkles size={42} /></div><section><small>{libraryDetail.model}</small><h3>{libraryDetail.name}</h3><p>由 {libraryDetail.author} 创作，可直接作为{overlay === "style-library" ? "图片风格参考" : "视频镜头特效"}添加到当前画布。</p><dl><div><dt>授权</dt><dd>{libraryDetail.commercial ? "支持商用" : "仅个人使用"}</dd></div><div><dt>使用次数</dt><dd>{libraryDetail.uses}</dd></div><div><dt>分类</dt><dd>{libraryDetail.category}</dd></div></dl><button type="button" onClick={() => { addWorkflowNode(overlay === "style-library" ? "image" : "video", { title: libraryDetail.name, description: `来自素材库 · ${libraryDetail.author}`, prompt: libraryDetail.name, position: libraryInsertPoint ?? undefined, connectToAnchor: !libraryInsertPoint }); setLibraryRecent((items) => [libraryDetail.name, ...items.filter((item) => item !== libraryDetail.name)]); setLibraryDetail(null); setLibraryInsertPoint(null); setOverlay(null); }}>添加到画布</button></section></div>}
            </div> : <div className="canvas-clear-data-body"><p>将从这台设备删除当前作品记录、画布快照和关联的本机素材。登录、主题、收藏、其他作品及云端项目不会受影响。</p><div><button type="button" onClick={() => setOverlay(null)}>取消</button><button type="button" className="is-danger" onClick={clearCurrentLocalWork}>清除本地数据</button></div></div>}
          </section>
        </div>
      )}

      <ControlledScriptWorkflowOverlay
        open={Boolean(scriptWorkflowNodeId)}
        nodeId={scriptWorkflowNodeId}
        workbench={presentedScriptWorkbench}
        initialDialog={scriptWorkflowInitialDialog}
        onChange={(nextWorkbench) => {
          if (scriptWorkflowNodeId) commitScriptWorkbench(scriptWorkflowNodeId, sanitizePresentedWorkbench(nextWorkbench));
        }}
        onClose={closeScriptWorkbench}
        promptModels={scriptPromptModels}
        imageModels={scriptImageModels}
        canvasImages={scriptCanvasImages}
        onComposePrompt={composeScriptPrompt}
        onComposeAllPrompts={composeAllScriptPrompts}
        onGenerateAsset={generateScriptAsset}
        onGenerateAssets={generateScriptAssets}
        onSelectCanvasImage={selectScriptCanvasImage}
        onUploadAsset={uploadScriptAsset}
        onJumpToAssetNode={(nodeId) => jumpToScriptAssetNode(nodeId)}
        onBatchVideo={batchVideoFromWorkbench}
      />

      <StandaloneSkillWorkflowOverlay
        open={Boolean(standaloneWorkflow)}
        nodeId={standaloneWorkflow?.nodeId ?? null}
        workflow={standaloneWorkflow?.workflow ?? null}
        onClose={() => setStandaloneWorkflow(null)}
        onRun={runStandaloneWorkflow}
      />

      <MembershipDialog open={membershipOpen} onClose={() => setMembershipOpen(false)} onPurchase={(label) => { setMembershipOpen(false); setNotice(`已选择${label}，支付服务接入后即可购买`); }} />

      {notice && <div className="canvas-toast" role="status">{notice}</div>}
    </main>
  );
}
