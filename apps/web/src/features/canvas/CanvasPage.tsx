import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
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
} from "@xyflow/react";
import { BrandIcon } from "../../components/BrandIcon";
import { LineIcon } from "../../components/LineIcon";
import { SKILLS } from "../../catalog/skills";
import { createAgentGateway, type AgentGateway } from "../../lib/agent";
import { saveWork } from "../../lib/work";
import type { AgentJob, CreationLine, DraftAttachment, WebWork } from "../../types";

type CanvasView = "workflow" | "storyboard";
type CanvasTool = "select" | "pan";
type DrawerKind = "add" | "tools" | "assets" | "characters" | "history";
type AgentPanelTab = "skills" | "history" | "settings";
type OverlayKind = "shortcuts" | "tutorial";
type WorkflowNodeKind = "text" | "script" | "image" | "audio" | "video" | "compose";
type WorkflowNodeStatus = "idle" | "ready" | "running" | "done" | "failed";

type WorkflowNodeData = {
  kind: WorkflowNodeKind;
  title: string;
  description: string;
  status: WorkflowNodeStatus;
  eyebrow: string;
  assetName?: string;
} & Record<string, unknown>;

type WorkflowNode = Node<WorkflowNodeData, "workflow-node">;

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
  | "compose"
  | "edge"
  | "grid"
  | "history"
  | "image"
  | "map"
  | "move"
  | "panel"
  | "script"
  | "send"
  | "sparkle"
  | "text"
  | "tools"
  | "tutorial"
  | "video"
  | "workflow"
  | "zoom-in"
  | "zoom-out";

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
  { id: "lead", name: "主角", detail: "建立人物外观、性格与动机" },
  { id: "support", name: "重要配角", detail: "补全人物关系与叙事功能" },
  { id: "antagonist", name: "对手", detail: "设计冲突目标与视觉辨识度" },
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
    case "text": content = <><path d="M5 5h14M12 5v14M8 19h8" /></>; break;
    case "script": content = <><path d="M6 3h9l3 3v15H6zM15 3v4h4M9 11h6M9 15h6" /></>; break;
    case "image": content = <><rect x="3.5" y="4" width="17" height="16" rx="2" /><circle cx="9" cy="9" r="1.5" /><path d="m5 18 5-5 3 3 2-2 4 4" /></>; break;
    case "audio": content = <><path d="M9 18V6l9-2v12" /><circle cx="6" cy="18" r="3" /><circle cx="15" cy="16" r="3" /></>; break;
    case "video": content = <><rect x="3" y="5" width="14" height="14" rx="2" /><path d="m17 10 4-2v8l-4-2ZM9 9l4 3-4 3z" /></>; break;
    case "compose": content = <><rect x="4" y="4" width="11" height="11" rx="2" /><path d="M9 9h11v11H9z" /></>; break;
    case "map": content = <><path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3zM9 3v15M15 6v15" /></>; break;
    case "edge": content = <><circle cx="5" cy="17" r="2" /><circle cx="19" cy="7" r="2" /><path d="M7 16c4-1 4-7 10-8" /></>; break;
    case "grid": content = <><path d="M4 4h16v16H4zM4 10h16M4 15h16M10 4v16M15 4v16" /></>; break;
    case "zoom-in": content = <><circle cx="10" cy="10" r="6" /><path d="m15 15 5 5M10 7v6M7 10h6" /></>; break;
    case "zoom-out": content = <><circle cx="10" cy="10" r="6" /><path d="m15 15 5 5M7 10h6" /></>; break;
    case "panel": content = <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M15 4v16M18 9h.01M18 13h.01" /></>; break;
    case "sparkle": content = <><path d="m12 3 1.4 4.2L18 9l-4.6 1.8L12 15l-1.4-4.2L6 9l4.6-1.8zM19 15l.7 2.3L22 18l-2.3.7L19 21l-.7-2.3L16 18l2.3-.7z" /></>; break;
    case "send": content = <><path d="m5 12 14-7-4 14-3-6zM12 13l7-8" /></>; break;
    case "close": content = <><path d="m6 6 12 12M18 6 6 18" /></>; break;
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

function WorkflowNodeCard({ data, selected }: NodeProps<WorkflowNode>) {
  return (
    <article className={`workflow-node-card kind-${data.kind} status-${data.status}${selected ? " is-selected" : ""}`}>
      <Handle type="target" position={Position.Left} className="workflow-handle workflow-handle-target" />
      <header>
        <span className="workflow-node-icon"><Icon name={data.kind} /></span>
        <span className="workflow-node-heading"><small>{data.eyebrow}</small><strong>{data.title}</strong></span>
        <i className="workflow-node-status" aria-label={data.status} />
      </header>
      {(data.kind === "image" || data.kind === "video") && (
        <div className={`workflow-node-preview preview-${data.kind}`}><span /><span /><span />{data.kind === "video" && <i><Icon name="video" /></i>}</div>
      )}
      {data.kind === "audio" && <div className="workflow-node-waveform" aria-hidden="true">{[8, 15, 10, 23, 18, 27, 12, 21, 9, 18, 13, 25, 16, 9].map((height, index) => <i key={`${height}-${index}`} style={{ height }} />)}</div>}
      <p>{data.description}</p>
      {data.assetName && <span className="workflow-node-asset">{data.assetName}</span>}
      <footer><span>{data.status === "running" ? "生成中…" : data.status === "done" ? "已完成" : data.status === "failed" ? "执行失败" : "点击选择节点"}</span><b>•••</b></footer>
      <Handle type="source" position={Position.Right} className="workflow-handle workflow-handle-source" />
    </article>
  );
}

const NODE_TYPES = { "workflow-node": WorkflowNodeCard };

function BottomCanvasControls({
  attachments,
  zoom,
  miniMapVisible,
  edgesVisible,
  gridVisible,
  onOpenAssets,
  onOrganize,
  onToggleMiniMap,
  onToggleEdges,
  onToggleGrid,
}: {
  attachments: number;
  zoom: number;
  miniMapVisible: boolean;
  edgesVisible: boolean;
  gridVisible: boolean;
  onOpenAssets: () => void;
  onOrganize: () => void;
  onToggleMiniMap: () => void;
  onToggleEdges: () => void;
  onToggleGrid: () => void;
}) {
  const flow = useReactFlow<WorkflowNode, Edge>();
  return (
    <Panel position="bottom-center" className="canvas-bottom-controls">
      <button type="button" onClick={onOpenAssets} title="打开素材库"><Icon name="assets" /><span>资产</span>{attachments > 0 && <b>{attachments}</b>}</button>
      <button type="button" onClick={() => { onOrganize(); window.setTimeout(() => void flow.fitView({ padding: 0.2, duration: 240 }), 30); }} title="自动整理节点"><Icon name="tools" /><span>整理</span></button>
      <span className="canvas-control-divider" />
      <button type="button" className={miniMapVisible ? "is-active" : ""} onClick={onToggleMiniMap} title="显示或隐藏小地图"><Icon name="map" /></button>
      <button type="button" className={edgesVisible ? "is-active" : ""} onClick={onToggleEdges} title="显示或隐藏连线"><Icon name="edge" /></button>
      <button type="button" className={gridVisible ? "is-active" : ""} onClick={onToggleGrid} title="显示或隐藏网格"><Icon name="grid" /></button>
      <span className="canvas-control-divider" />
      <button type="button" onClick={() => void flow.zoomOut({ duration: 160 })} title="缩小"><Icon name="zoom-out" /></button>
      <button type="button" className="canvas-zoom-value" onClick={() => void flow.fitView({ padding: 0.2, duration: 240 })} title="适应画布">{Math.round(zoom * 100)}%</button>
      <button type="button" onClick={() => void flow.zoomIn({ duration: 160 })} title="放大"><Icon name="zoom-in" /></button>
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

export function CanvasPage({ work, onHome }: { work: WebWork; onHome: () => void }) {
  const graph = useMemo(() => initialGraph(work), [work.id, work.line]);
  const [nodes, setNodes, onNodesChange] = useNodesState<WorkflowNode>(graph.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(graph.edges);
  const [workName, setWorkName] = useState(work.name);
  const [view, setView] = useState<CanvasView>("workflow");
  const [tool, setTool] = useState<CanvasTool>("select");
  const [drawer, setDrawer] = useState<DrawerKind | null>(null);
  const [overlay, setOverlay] = useState<OverlayKind | null>(null);
  const [notice, setNotice] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [gridVisible, setGridVisible] = useState(true);
  const [edgesVisible, setEdgesVisible] = useState(true);
  const [miniMapVisible, setMiniMapVisible] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [gateway, setGateway] = useState<AgentGateway | null>(null);
  const [prompt, setPrompt] = useState(work.prompt);
  const [activeJob, setActiveJob] = useState<AgentJob | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);
  const [panelTab, setPanelTab] = useState<AgentPanelTab>("skills");
  const [runHistory, setRunHistory] = useState<RunRecord[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([
    { id: crypto.randomUUID(), label: "创建作品并初始化工作流", time: timestamp() },
  ]);
  const [includeCanvasContext, setIncludeCanvasContext] = useState(true);
  const [followLatestRun, setFollowLatestRun] = useState(true);
  const [activeSkill, setActiveSkill] = useState<string | null>(work.creationConfig?.skillId ?? null);
  const mountedRef = useRef(true);

  const suggestedSkills = useMemo(() => suggestedSkillsFor(work), [work]);
  const cloudLabel = work.cloudState === "synced"
    ? "R2 已同步"
    : work.cloudState === "syncing"
      ? "正在同步…"
      : work.cloudState === "auth-required"
        ? "登录后云同步"
        : work.cloudState === "failed"
          ? "同步失败"
          : "本地草稿";

  const addActivity = useCallback((label: string) => {
    setActivity((items) => [{ id: crypto.randomUUID(), label, time: timestamp() }, ...items].slice(0, 30));
  }, []);

  useEffect(() => {
    setNodes(graph.nodes);
    setEdges(graph.edges);
    setSelectedNodeId(null);
    setWorkName(work.name);
    setPrompt(work.prompt);
  }, [graph, setEdges, setNodes, work.name, work.prompt]);

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
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.matches("input, textarea, [contenteditable='true']")) {
        if (event.key === "Escape") target.blur();
        return;
      }
      if (event.key === "Escape") {
        setDrawer(null);
        setOverlay(null);
      } else if (event.key.toLowerCase() === "a") {
        setDrawer("add");
      } else if (event.key.toLowerCase() === "v") {
        setTool("select");
      } else if (event.key.toLowerCase() === "h") {
        setTool("pan");
      } else if (event.key.toLowerCase() === "g") {
        setGridVisible((visible) => !visible);
      } else if (event.key === "?") {
        setOverlay("shortcuts");
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  function persistName() {
    const name = workName.trim() || "unnamed";
    setWorkName(name);
    if (name !== work.name) {
      saveWork({ ...work, name });
      addActivity(`作品重命名为「${name}」`);
    }
  }

  function openDrawer(kind: DrawerKind) {
    setDrawer((current) => current === kind ? null : kind);
    setOverlay(null);
  }

  function addWorkflowNode(kind: WorkflowNodeKind, options?: { title?: string; assetName?: string }) {
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
      position: anchor ? { x: anchor.position.x + 310, y: anchor.position.y + 42 } : { x: 120, y: 140 },
      data: {
        kind,
        title: options?.title ?? definition.label,
        description: definition.description,
        status: "idle",
        eyebrow: definition.eyebrow,
        ...(options?.assetName ? { assetName: options.assetName } : {}),
      },
    };
    setNodes((items) => [...items.map((node) => ({ ...node, selected: false })), { ...nextNode, selected: true }]);
    if (anchor) setEdges((items) => addEdge(makeEdge(`edge-${crypto.randomUUID()}`, anchor.id, id), items));
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
    if (!selectedNodeId) {
      setNotice("请先选择一个节点");
      return;
    }
    setNodes((items) => items.filter((node) => node.id !== selectedNodeId));
    setEdges((items) => items.filter((edge) => edge.source !== selectedNodeId && edge.target !== selectedNodeId));
    setSelectedNodeId(null);
    addActivity("删除选中节点");
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
    const cleanPrompt = prompt.trim();
    if (!gateway || !cleanPrompt || submitting) return;
    const stageNode = nodes.find((node) => node.id !== "text-source" && (node.data.status === "ready" || node.data.status === "idle"));
    setSubmitting(true);
    setPanelOpen(true);
    if (followLatestRun) setPanelTab("history");
    if (stageNode) setNodes((items) => items.map((node) => node.id === stageNode.id ? { ...node, data: { ...node.data, status: "running" } } : node));
    const effectiveWork = { ...work, name: workName.trim() || "unnamed" };
    saveWork(effectiveWork);
    try {
      const taskPrompt = includeCanvasContext
        ? `${cleanPrompt}\n\n[画布上下文] 当前共有 ${nodes.length} 个节点、${edges.length} 条连线。`
        : cleanPrompt;
      let current = await gateway.submit({ work: effectiveWork, prompt: taskPrompt });
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

  return (
    <main className={`creation-canvas-shell tool-${tool}${panelOpen ? " has-agent-panel" : ""}`}>
      <header className="creation-canvas-header">
        <button type="button" className="creation-canvas-brand" onClick={onHome} aria-label="返回首页"><BrandIcon /></button>
        <span className="creation-canvas-crumb">/</span>
        <span className="creation-canvas-line"><LineIcon line={work.line} />{LINE_LABELS[work.line]}</span>
        <span className="creation-canvas-crumb">/</span>
        <input
          className="creation-canvas-name"
          value={workName}
          aria-label="作品名称"
          onChange={(event) => setWorkName(event.target.value)}
          onBlur={persistName}
          onKeyDown={(event) => { if (event.key === "Enter") event.currentTarget.blur(); }}
        />
        <div className="canvas-view-switch" role="tablist" aria-label="画布视图">
          <button type="button" role="tab" aria-selected={view === "workflow"} className={view === "workflow" ? "is-active" : ""} onClick={() => setView("workflow")}><Icon name="workflow" />工作流</button>
          <button type="button" role="tab" aria-selected={view === "storyboard"} className={view === "storyboard" ? "is-active" : ""} onClick={() => { setView("storyboard"); setNotice("故事板即将开放"); }}>故事板<small>即将开放</small></button>
        </div>
        <span className="creation-canvas-header-spacer" />
        <span className={work.cloudState === "synced" ? "canvas-sync-state is-synced" : "canvas-sync-state"} title={work.cloudError}>{cloudLabel}</span>
        <button type="button" className="canvas-token-button" title="会员与 Token 计费将在服务端接入">Token —</button>
        <button type="button" className={panelOpen ? "canvas-panel-toggle is-active" : "canvas-panel-toggle"} onClick={() => setPanelOpen((open) => !open)} aria-label="切换 Agent 面板"><Icon name="panel" /></button>
      </header>

      <aside className="creation-canvas-rail" aria-label="画布工具">
        <button type="button" className={drawer === "add" ? "is-active" : ""} title="添加节点（A）" onClick={() => openDrawer("add")}><Icon name="add" /><span>添加</span></button>
        <button type="button" className={tool === "pan" ? "is-active" : ""} title="移动画布（H）" onClick={() => { setTool((current) => current === "pan" ? "select" : "pan"); setDrawer(null); }}><Icon name="move" /><span>移动</span></button>
        <button type="button" className={drawer === "tools" ? "is-active" : ""} title="工具箱" onClick={() => openDrawer("tools")}><Icon name="tools" /><span>工具箱</span></button>
        <button type="button" className={drawer === "assets" ? "is-active" : ""} title="素材库" onClick={() => openDrawer("assets")}><Icon name="assets" /><span>素材</span></button>
        <button type="button" className={drawer === "characters" ? "is-active" : ""} title="角色库" onClick={() => openDrawer("characters")}><Icon name="character" /><span>角色</span></button>
        <button type="button" className={drawer === "history" ? "is-active" : ""} title="操作历史" onClick={() => openDrawer("history")}><Icon name="history" /><span>历史</span></button>
        <span className="creation-canvas-rail-spacer" />
        <button type="button" title="快捷键（?）" onClick={() => setOverlay("shortcuts")}><span className="shortcut-glyph">⌘</span><span>快捷键</span></button>
        <button type="button" title="画布教程" onClick={() => setOverlay("tutorial")}><Icon name="tutorial" /><span>教程</span></button>
      </aside>

      <section className="creation-canvas-stage">
        {view === "workflow" ? (
          <ReactFlow<WorkflowNode, Edge>
            nodes={nodes}
            edges={edgesVisible ? edges : []}
            nodeTypes={NODE_TYPES}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={(_, node) => setSelectedNodeId(node.id)}
            onPaneClick={() => setSelectedNodeId(null)}
            onMove={(_, viewport) => setZoom(viewport.zoom)}
            nodesDraggable={tool === "select"}
            nodesConnectable={tool === "select" && edgesVisible}
            elementsSelectable={tool === "select"}
            panOnDrag={tool === "pan" ? true : [1, 2]}
            selectionOnDrag={tool === "select"}
            fitView
            fitViewOptions={{ padding: 0.18 }}
            minZoom={0.25}
            maxZoom={2}
            defaultEdgeOptions={{ type: "smoothstep", markerEnd: { type: MarkerType.ArrowClosed } }}
          >
            {gridVisible && <Background variant={BackgroundVariant.Dots} gap={20} size={1.1} color="rgba(133,137,151,.28)" />}
            {miniMapVisible && <MiniMap className="creation-canvas-minimap" pannable zoomable nodeColor={(node) => {
              const typedNode = node as WorkflowNode;
              if (typedNode.data.kind === "image") return "#795cff";
              if (typedNode.data.kind === "audio") return "#de7bff";
              if (typedNode.data.kind === "video") return "#5aa8ff";
              if (typedNode.data.kind === "compose") return "#48c9a5";
              return "#585b67";
            }} />}
            <BottomCanvasControls
              attachments={work.attachments.length}
              zoom={zoom}
              miniMapVisible={miniMapVisible}
              edgesVisible={edgesVisible}
              gridVisible={gridVisible}
              onOpenAssets={() => openDrawer("assets")}
              onOrganize={organizeNodes}
              onToggleMiniMap={() => setMiniMapVisible((visible) => !visible)}
              onToggleEdges={() => setEdgesVisible((visible) => !visible)}
              onToggleGrid={() => setGridVisible((visible) => !visible)}
            />
          </ReactFlow>
        ) : (
          <div className="canvas-storyboard-coming-soon">
            <span><Icon name="image" /></span>
            <small>STORYBOARD</small>
            <h2>故事板即将开放</h2>
            <p>后续可在这里按镜头审阅首尾帧、对白、运镜和生成版本。</p>
            <button type="button" onClick={() => setView("workflow")}>返回工作流</button>
          </div>
        )}
      </section>

      {drawer && (
        <aside className={`canvas-drawer canvas-drawer-${drawer}`} aria-label="画布抽屉">
          <header><div><small>CANVAS</small><strong>{drawer === "add" ? "添加节点" : drawer === "tools" ? "工具箱" : drawer === "assets" ? "素材库" : drawer === "characters" ? "角色库" : "操作历史"}</strong></div><button type="button" onClick={() => setDrawer(null)} aria-label="关闭抽屉"><Icon name="close" /></button></header>
          {drawer === "add" && <div className="canvas-drawer-grid">{NODE_LIBRARY.map((item) => {
            const disabled = work.line === "comic" && item.kind === "video";
            return <button key={item.kind} type="button" disabled={disabled} onClick={() => addWorkflowNode(item.kind)}><span><Icon name={item.kind} /></span><b>{item.label}</b><small>{disabled ? "漫画工作流不使用视频节点" : item.description}</small></button>;
          })}</div>}
          {drawer === "tools" && <div className="canvas-tool-list">
            <button type="button" onClick={organizeNodes}><Icon name="tools" /><span><b>自动整理</b><small>按工作流阶段重新排列节点</small></span></button>
            <button type="button" onClick={() => setNodes((items) => items.map((node) => ({ ...node, selected: true })))}><Icon name="workflow" /><span><b>选择全部</b><small>选中画布上的所有节点</small></span></button>
            <button type="button" onClick={() => setGridVisible((visible) => !visible)}><Icon name="grid" /><span><b>{gridVisible ? "隐藏网格" : "显示网格"}</b><small>切换画布辅助点阵</small></span></button>
            <button type="button" className="is-danger" onClick={deleteSelectedNode}><Icon name="close" /><span><b>删除选中节点</b><small>同时移除与它关联的连线</small></span></button>
          </div>}
          {drawer === "assets" && <div className="canvas-asset-list">
            {work.attachments.length ? work.attachments.map((attachment) => <button key={attachment.id} type="button" onClick={() => addAttachmentNode(attachment)}><span><Icon name={attachmentKind(attachment)} /></span><span><b>{attachment.name}</b><small>{attachment.type || "文件"} · {Math.max(1, Math.round(attachment.size / 1024))} KB</small></span><i>添加到画布</i></button>) : <div className="canvas-drawer-empty"><Icon name="assets" /><b>暂时没有素材</b><p>可返回首页重新创建作品并添加源文件。</p></div>}
          </div>}
          {drawer === "characters" && <div className="canvas-character-list">
            {CHARACTER_PRESETS.map((character, index) => <button key={character.id} type="button" onClick={() => addWorkflowNode("text", { title: character.name, assetName: `角色 ${index + 1}` })}><span className="canvas-character-avatar">{character.name.slice(0, 1)}</span><span><b>{character.name}</b><small>{character.detail}</small></span><i>＋</i></button>)}
          </div>}
          {drawer === "history" && <div className="canvas-activity-list">
            <div className="canvas-history-actions"><button type="button" onClick={resetWorkflow}>恢复初始布局</button><button type="button" onClick={() => setActivity([])}>清空记录</button></div>
            {activity.length ? activity.map((item) => <div key={item.id}><i /><span><b>{item.label}</b><small>{item.time}</small></span></div>) : <div className="canvas-drawer-empty"><Icon name="history" /><b>暂无操作记录</b></div>}
          </div>}
        </aside>
      )}

      {panelOpen && (
        <aside className="canvas-agent-panel">
          <header className="canvas-agent-panel-header"><div><small>CREATION AGENT</small><strong>{LINE_LABELS[work.line]}助手</strong></div><span className={gateway && gateway.mode !== "demo" ? "agent-status-dot is-live" : "agent-status-dot"} title={gateway?.label ?? "正在检测 Agent"} /><button type="button" onClick={() => setPanelOpen(false)} aria-label="关闭 Agent 面板"><Icon name="close" /></button></header>
          <nav className="canvas-agent-tabs" role="tablist" aria-label="Agent 面板">
            <button type="button" role="tab" aria-selected={panelTab === "skills"} className={panelTab === "skills" ? "is-active" : ""} onClick={() => setPanelTab("skills")}>建议 Skill</button>
            <button type="button" role="tab" aria-selected={panelTab === "history"} className={panelTab === "history" ? "is-active" : ""} onClick={() => setPanelTab("history")}>历史{runHistory.length > 0 && <b>{runHistory.length}</b>}</button>
            <button type="button" role="tab" aria-selected={panelTab === "settings"} className={panelTab === "settings" ? "is-active" : ""} onClick={() => setPanelTab("settings")}>设置</button>
          </nav>
          <div className="canvas-agent-panel-body">
            {panelTab === "skills" && <section className="canvas-skill-suggestions">
              <div className="canvas-agent-context"><small>当前作品</small><strong>{workName || "unnamed"}</strong><p>{work.attachments.length ? `已关联 ${work.attachments.length} 个源文件` : "从文字需求开始创作"}</p></div>
              <h3><Icon name="sparkle" />下一步建议</h3>
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
            </section>}
          </div>
        </aside>
      )}

      <section className={panelOpen ? "canvas-agent-composer with-panel" : "canvas-agent-composer"}>
        <textarea
          value={prompt}
          aria-label="Agent 指令"
          placeholder="告诉 Agent 下一步要制作什么…"
          onChange={(event) => setPrompt(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submit();
            }
          }}
        />
        <footer>
          <button type="button" className="canvas-composer-asset" title="选择素材" onClick={() => openDrawer("assets")}><Icon name="assets" /></button>
          <span>{gateway?.label ?? "正在检测本地 Agent…"}</span>
          {activeSkill && <button type="button" className="canvas-active-skill" onClick={() => { setActiveSkill(null); setPrompt(""); }}>Skill · {suggestedSkills.find((skill) => skill.id === activeSkill)?.title}<i>×</i></button>}
          <span className="canvas-composer-spacer" />
          <small>Enter 发送 · Shift+Enter 换行</small>
          <button type="button" className="canvas-composer-send" disabled={!gateway || !prompt.trim() || submitting} onClick={() => void submit()} aria-label="发送 Agent 指令">{submitting ? <span className="canvas-submit-spinner">•••</span> : <Icon name="send" />}</button>
        </footer>
      </section>

      {overlay && (
        <div className="canvas-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setOverlay(null); }}>
          <section className={`canvas-modal canvas-modal-${overlay}`} role="dialog" aria-modal="true" aria-label={overlay === "shortcuts" ? "快捷键" : "画布教程"}>
            <header><div><small>CANVAS GUIDE</small><strong>{overlay === "shortcuts" ? "快捷键" : "快速上手"}</strong></div><button type="button" onClick={() => setOverlay(null)} aria-label="关闭"><Icon name="close" /></button></header>
            {overlay === "shortcuts" ? <div className="canvas-shortcut-list"><span><kbd>A</kbd><b>打开添加节点</b></span><span><kbd>V</kbd><b>选择工具</b></span><span><kbd>H</kbd><b>移动画布</b></span><span><kbd>G</kbd><b>显示或隐藏网格</b></span><span><kbd>?</kbd><b>查看快捷键</b></span><span><kbd>Esc</kbd><b>关闭弹层</b></span></div> : <ol className="canvas-tutorial-list"><li><i>1</i><span><b>选择或添加节点</b><small>从左侧添加文本、图片、音频等工作流节点。</small></span></li><li><i>2</i><span><b>连接并整理流程</b><small>拖动节点连接点建立依赖，再用底部整理按钮排列。</small></span></li><li><i>3</i><span><b>让 Agent 执行</b><small>选择右侧建议 Skill，或在底部直接输入下一步任务。</small></span></li></ol>}
          </section>
        </div>
      )}

      {notice && <div className="canvas-toast" role="status">{notice}</div>}
    </main>
  );
}
