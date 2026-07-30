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
import { MODEL_GROUPS, getModelById } from "../../catalog/models";
import type { ModelModality } from "../../catalog/types";
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
type AgentPanelTab = "skills" | "history" | "settings";
type OverlayKind = "shortcuts" | "tutorial" | "share" | "clear-data";
type ComposerMenuKind = "model" | "mode" | null;
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
  | "copy"
  | "download"
  | "edge"
  | "fullscreen"
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
    case "copy": content = <><rect x="8" y="8" width="11" height="11" rx="2" /><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3" /></>; break;
    case "download": content = <><path d="M12 4v11m0 0 4-4m-4 4-4-4" /><path d="M5 18v2h14v-2" /></>; break;
    case "map": content = <><path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3zM9 3v15M15 6v15" /></>; break;
    case "edge": content = <><circle cx="5" cy="17" r="2" /><circle cx="19" cy="7" r="2" /><path d="M7 16c4-1 4-7 10-8" /></>; break;
    case "grid": content = <><path d="M4 4h16v16H4zM4 10h16M4 15h16M10 4v16M15 4v16" /></>; break;
    case "zoom-in": content = <><circle cx="10" cy="10" r="6" /><path d="m15 15 5 5M10 7v6M7 10h6" /></>; break;
    case "zoom-out": content = <><circle cx="10" cy="10" r="6" /><path d="m15 15 5 5M7 10h6" /></>; break;
    case "undo": content = <><path d="M9 7 4 12l5 5" /><path d="M5 12h8a6 6 0 0 1 6 6" /></>; break;
    case "redo": content = <><path d="m15 7 5 5-5 5" /><path d="M19 12h-8a6 6 0 0 0-6 6" /></>; break;
    case "fullscreen": content = <><path d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5" /></>; break;
    case "upload": content = <><path d="M12 16V4m0 0L7 9m5-5 5 5" /><path d="M5 14v5h14v-5" /></>; break;
    case "panel": content = <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M15 4v16M18 9h.01M18 13h.01" /></>; break;
    case "sparkle": content = <><path d="m12 3 1.4 4.2L18 9l-4.6 1.8L12 15l-1.4-4.2L6 9l4.6-1.8zM19 15l.7 2.3L22 18l-2.3.7L19 21l-.7-2.3L16 18l2.3-.7z" /></>; break;
    case "send": content = <><path d="m5 12 14-7-4 14-3-6zM12 13l7-8" /></>; break;
    case "share": content = <><circle cx="18" cy="5" r="2.5" /><circle cx="6" cy="12" r="2.5" /><circle cx="18" cy="19" r="2.5" /><path d="m8.2 10.8 7.6-4.5M8.2 13.2l7.6 4.5" /></>; break;
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
  attachments,
  zoom,
  miniMapVisible,
  edgesVisible,
  snapToGridEnabled,
  onOpenOverview,
  onToggleMiniMap,
  onToggleEdges,
  onToggleSnap,
}: {
  attachments: number;
  zoom: number;
  miniMapVisible: boolean;
  edgesVisible: boolean;
  snapToGridEnabled: boolean;
  onOpenOverview: () => void;
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
      <button type="button" onClick={onOpenOverview} title="资产管理"><Icon name="assets" /><span>资产管理</span>{attachments > 0 && <b>{attachments}</b>}</button>
      <span className="canvas-control-divider" />
      <button type="button" className={miniMapVisible ? "is-active" : ""} onClick={onToggleMiniMap} title="显示或隐藏小地图"><Icon name="map" /></button>
      <button type="button" className={edgesVisible ? "is-active" : ""} onClick={onToggleEdges} title="显示或隐藏连线"><Icon name="edge" /></button>
      <button type="button" className={snapToGridEnabled ? "is-active" : ""} onClick={onToggleSnap} title="网格吸附" aria-pressed={snapToGridEnabled}><Icon name="grid" /></button>
      <span className="canvas-control-divider" />
      <button type="button" onClick={() => void flow.zoomOut({ duration: 160 })} title="缩小"><Icon name="zoom-out" /></button>
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
      <button type="button" onClick={() => void flow.zoomIn({ duration: 160 })} title="放大"><Icon name="zoom-in" /></button>
      <button type="button" onClick={() => {
        if (document.fullscreenElement) void document.exitFullscreen();
        else void document.documentElement.requestFullscreen();
      }} title="切换全屏"><Icon name="fullscreen" /></button>
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
  const [drawer, setDrawer] = useState<DrawerKind | null>(null);
  const [overlay, setOverlay] = useState<OverlayKind | null>(null);
  const [notice, setNotice] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [editingNodeId, setEditingNodeId] = useState<string | null>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; nodeId: string } | null>(null);
  const [gridVisible, setGridVisible] = useState(storedDocument?.preferences.gridVisible ?? true);
  const [snapToGridEnabled, setSnapToGridEnabled] = useState(storedDocument?.preferences.snapToGrid ?? false);
  const [edgesVisible, setEdgesVisible] = useState(storedDocument?.preferences.edgesVisible ?? true);
  const [miniMapVisible, setMiniMapVisible] = useState(storedDocument?.preferences.miniMapVisible ?? true);
  const [viewport, setViewport] = useState(storedDocument?.viewport ?? { x: 0, y: 0, zoom: 1 });
  const [zoom, setZoom] = useState(storedDocument?.viewport.zoom ?? 1);
  const [gateway, setGateway] = useState<AgentGateway | null>(null);
  const [prompt, setPrompt] = useState(work.prompt);
  const [activeJob, setActiveJob] = useState<AgentJob | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [panelOpen, setPanelOpen] = useState(storedDocument?.preferences.panelOpen ?? true);
  const [panelTab, setPanelTab] = useState<AgentPanelTab>("skills");
  const [runHistory, setRunHistory] = useState<RunRecord[]>(storedDocument?.runHistory ?? []);
  const [activity, setActivity] = useState<ActivityItem[]>(storedDocument?.activity ?? [
    { id: crypto.randomUUID(), label: "创建作品并初始化工作流", time: timestamp() },
  ]);
  const [includeCanvasContext, setIncludeCanvasContext] = useState(storedDocument?.preferences.includeCanvasContext ?? true);
  const [followLatestRun, setFollowLatestRun] = useState(storedDocument?.preferences.followLatestRun ?? true);
  const [activeSkill, setActiveSkill] = useState<string | null>(storedDocument?.activeSkill ?? work.creationConfig?.skillId ?? null);
  const [creationConfig, setCreationConfig] = useState<WorkCreationConfig>(() => defaultCreationConfig(storedDocument?.work ?? work));
  const [composerMenu, setComposerMenu] = useState<ComposerMenuKind>(null);
  const [modelModality, setModelModality] = useState<ModelModality>(creationConfig.model.modality);
  const [overviewTab, setOverviewTab] = useState<"canvas" | "assets">("canvas");
  const [overviewQuery, setOverviewQuery] = useState("");
  const [syncState, setSyncState] = useState<CloudWorkState>(work.cloudState);
  const [attachments, setAttachments] = useState<DraftAttachment[]>(storedDocument?.work.attachments ?? work.attachments);
  const [cloudProjectId, setCloudProjectId] = useState(work.cloudProjectId ?? storedDocument?.work.cloudProjectId);
  const mountedRef = useRef(true);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const historyRef = useRef<GraphHistoryEntry[]>([cloneGraph(graph.nodes, graph.edges)]);
  const historyIndexRef = useRef(0);
  const restoringHistoryRef = useRef(false);
  const clipboardRef = useRef<GraphHistoryEntry | null>(null);
  const pasteCountRef = useRef(0);
  const [historyAvailability, setHistoryAvailability] = useState({ canUndo: false, canRedo: false });

  const suggestedSkills = useMemo(() => suggestedSkillsFor(work), [work]);
  const editingNode = editingNodeId ? nodes.find((node) => node.id === editingNodeId) ?? null : null;
  const selectedModel = getModelById(creationConfig.model.modelId);
  const overviewNodes = useMemo(() => {
    const query = overviewQuery.trim().toLocaleLowerCase();
    if (!query) return nodes;
    return nodes.filter((node) => `${node.data.title} ${node.data.description} ${node.data.assetName ?? ""}`.toLocaleLowerCase().includes(query));
  }, [nodes, overviewQuery]);
  const cloudLabel = syncState === "synced"
    ? "R2 已同步"
    : syncState === "syncing"
      ? "正在同步…"
      : syncState === "auth-required"
        ? "登录后云同步"
        : syncState === "failed"
          ? "同步失败"
          : "本地草稿";

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
        setComposerMenu(null);
        setContextMenu(null);
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
    setComposerMenu(null);
  }

  function updateNodeData(nodeId: string, patch: Partial<WorkflowNodeData>) {
    setNodes((items) => items.map((node) => node.id === nodeId
      ? { ...node, data: { ...node.data, ...patch } }
      : node));
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

  async function importAssets(fileList: FileList | null) {
    const files = [...(fileList ? Array.from(fileList) : [])];
    if (!files.length) return;
    const pending: PendingAttachment[] = files.map((file) => ({
      id: crypto.randomUUID(),
      name: file.name,
      size: file.size,
      type: file.type || "application/octet-stream",
      file,
    }));
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
    setDrawer("assets");

    if (!isCloudConfigured()) {
      setNotice(`已导入 ${pending.length} 个本地素材`);
      return;
    }
    setSyncState("syncing");
    try {
      const result = await persistWorkToCloud(nextWork, pending);
      if (!mountedRef.current) return;
      setAttachments(result.work.attachments);
      if (result.work.cloudProjectId) setCloudProjectId(result.work.cloudProjectId);
      setSyncState(result.work.cloudState);
      saveWork(result.work);
      setNotice(`已上传 ${pending.length} 个素材`);
    } catch (error) {
      if (!mountedRef.current) return;
      const message = error instanceof Error ? error.message : String(error);
      setSyncState("failed");
      saveWork({ ...nextWork, cloudState: "failed", cloudError: message });
      setNotice(`素材保留在本地，云上传失败：${message}`);
    }
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
    const effectiveWork = {
      ...work,
      name: workName.trim() || "unnamed",
      creationConfig,
      attachments,
      ...(cloudProjectId ? { cloudProjectId } : {}),
    };
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

  return (
    <main className={`creation-canvas-shell tool-${tool}${panelOpen ? " has-agent-panel" : ""}`}>
      <input
        ref={fileInputRef}
        className="canvas-file-input"
        type="file"
        multiple
        aria-label="上传画布素材"
        onChange={(event) => {
          void importAssets(event.currentTarget.files);
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
          <button type="button" className="canvas-board-label" onClick={() => setView((current) => current === "workflow" ? "storyboard" : "workflow")} title="切换画布视图">画布 1 <span>⌄</span></button>
        </div>
        <div className="canvas-view-switch" role="tablist" aria-label="画布视图">
          <button type="button" role="tab" aria-label="工作流" aria-selected={view === "workflow"} className={view === "workflow" ? "is-active" : ""} onClick={() => setView("workflow")}><Icon name="workflow" /></button>
          <button type="button" role="tab" aria-label="故事板" aria-selected={view === "storyboard"} className={view === "storyboard" ? "is-active" : ""} onClick={() => setView("storyboard")}><Icon name="panel" /></button>
        </div>
        <span className="creation-canvas-header-spacer" />
        <div className="canvas-top-actions">
          <span className={`canvas-sync-state state-${syncState}${syncState === "synced" ? " is-synced" : ""}`} title={work.cloudError || cloudLabel} aria-label={cloudLabel}>{cloudLabel}</span>
          <button type="button" className="canvas-header-action" onClick={() => setOverlay("share")} aria-label="发布与分享" title="发布与分享"><Icon name="share" /></button>
          <button type="button" className={panelOpen ? "canvas-panel-toggle is-active" : "canvas-panel-toggle"} onClick={() => setPanelOpen((open) => !open)} aria-label="切换 Agent 面板"><Icon name="panel" /></button>
        </div>
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
            onPaneClick={() => { setSelectedNodeId(null); setContextMenu(null); }}
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
            {miniMapVisible && <MiniMap className="creation-canvas-minimap" pannable zoomable nodeColor={(node) => {
              const typedNode = node as WorkflowNode;
              if (typedNode.data.kind === "image") return "#777984";
              if (typedNode.data.kind === "audio") return "#92949d";
              if (typedNode.data.kind === "video") return "#686a74";
              if (typedNode.data.kind === "compose") return "#92949d";
              return "#585b67";
            }} />}
            <BottomCanvasControls
              attachments={attachments.length}
              zoom={zoom}
              miniMapVisible={miniMapVisible}
              edgesVisible={edgesVisible}
              snapToGridEnabled={snapToGridEnabled}
              onOpenOverview={() => openDrawer("overview")}
              onToggleMiniMap={() => setMiniMapVisible((visible) => !visible)}
              onToggleEdges={() => setEdgesVisible((visible) => !visible)}
              onToggleSnap={() => setSnapToGridEnabled((enabled) => !enabled)}
            />
          </ReactFlow>
        ) : (
          <StoryboardView nodes={nodes} onOpenNode={(nodeId) => setEditingNodeId(nodeId)} />
        )}
      </section>

      {drawer && (
        <aside className={`canvas-drawer canvas-drawer-${drawer}`} aria-label="画布抽屉">
          <header><div><small>CANVAS</small><strong>{drawer === "add" ? "添加节点" : drawer === "tools" ? "工具箱" : drawer === "assets" ? "素材库" : drawer === "characters" ? "角色库" : drawer === "overview" ? "资产管理" : "操作历史"}</strong></div><button type="button" onClick={() => setDrawer(null)} aria-label="关闭抽屉"><Icon name="close" /></button></header>
          {drawer === "overview" && <div className="canvas-overview">
            <nav role="tablist" aria-label="资产管理视图">
              <button type="button" role="tab" aria-selected={overviewTab === "canvas"} className={overviewTab === "canvas" ? "is-active" : ""} onClick={() => setOverviewTab("canvas")}>画布</button>
              <button type="button" role="tab" aria-selected={overviewTab === "assets"} className={overviewTab === "assets" ? "is-active" : ""} onClick={() => setOverviewTab("assets")}>资产</button>
            </nav>
            {overviewTab === "canvas" ? <section className="canvas-overview-nodes">
              <label><Icon name="workflow" /><input aria-label="搜索节点" value={overviewQuery} onChange={(event) => setOverviewQuery(event.target.value)} placeholder="搜索节点" /></label>
              <small>画布元素 · 共 {nodes.length} 节点</small>
              <div>{overviewNodes.map((node) => <button key={node.id} type="button" onClick={() => {
                setView("workflow");
                setNodes((items) => items.map((item) => ({ ...item, selected: item.id === node.id })));
                setSelectedNodeId(node.id);
                setDrawer(null);
              }}><span><Icon name={node.data.kind} /></span><span><b>{node.data.title}</b><small>{node.data.eyebrow} · {node.data.status === "done" ? "已完成" : node.data.status === "ready" ? "可执行" : node.data.status === "running" ? "执行中" : node.data.status === "failed" ? "失败" : "待处理"}</small></span><i>定位</i></button>)}</div>
              {!overviewNodes.length && <div className="canvas-drawer-empty"><Icon name="workflow" /><b>没有匹配的节点</b></div>}
            </section> : <section className="canvas-overview-assets">
              <div className="canvas-asset-actions"><button type="button" onClick={() => fileInputRef.current?.click()}><Icon name="upload" />上传素材</button></div>
              {attachments.map((attachment) => <button key={attachment.id} type="button" onClick={() => addAttachmentNode(attachment)}><span><Icon name={attachmentKind(attachment)} /></span><span><b>{attachment.name}</b><small>{attachment.type || "文件"} · {Math.max(1, Math.round(attachment.size / 1024))} KB</small></span><i>添加到画布</i></button>)}
              {!attachments.length && <div className="canvas-drawer-empty"><Icon name="assets" /><b>暂时没有素材</b><p>上传后可从这里添加到工作流。</p></div>}
            </section>}
          </div>}
          {drawer === "add" && <div className="canvas-drawer-grid">{NODE_LIBRARY.map((item) => {
            const disabled = work.line === "comic" && item.kind === "video";
            return <button key={item.kind} type="button" disabled={disabled} onClick={() => addWorkflowNode(item.kind)}><span><Icon name={item.kind} /></span><b>{item.label}</b><small>{disabled ? "漫画工作流不使用视频节点" : item.description}</small></button>;
          })}</div>}
          {drawer === "tools" && <div className="canvas-tool-list">
            <button type="button" onClick={undoGraph} disabled={!historyAvailability.canUndo}><Icon name="undo" /><span><b>撤销</b><small>恢复到上一次画布状态</small></span></button>
            <button type="button" onClick={redoGraph} disabled={!historyAvailability.canRedo}><Icon name="redo" /><span><b>重做</b><small>重新应用被撤销的操作</small></span></button>
            <button type="button" onClick={duplicateSelectedNodes}><Icon name="copy" /><span><b>创建副本</b><small>复制当前选中的节点和内部连线</small></span></button>
            <button type="button" onClick={organizeNodes}><Icon name="tools" /><span><b>自动整理</b><small>按工作流阶段重新排列节点</small></span></button>
            <button type="button" onClick={() => setNodes((items) => items.map((node) => ({ ...node, selected: true })))}><Icon name="workflow" /><span><b>选择全部</b><small>选中画布上的所有节点</small></span></button>
            <button type="button" onClick={() => setGridVisible((visible) => !visible)}><Icon name="grid" /><span><b>{gridVisible ? "隐藏网格" : "显示网格"}</b><small>切换画布辅助点阵</small></span></button>
            <button type="button" className="is-danger" onClick={deleteSelectedNode}><Icon name="close" /><span><b>删除选中节点</b><small>同时移除与它关联的连线</small></span></button>
          </div>}
          {drawer === "assets" && <div className="canvas-asset-list">
            <div className="canvas-asset-actions"><button type="button" onClick={() => fileInputRef.current?.click()}><Icon name="upload" />上传素材</button></div>
            {attachments.length ? attachments.map((attachment) => <button key={attachment.id} type="button" onClick={() => addAttachmentNode(attachment)}><span><Icon name={attachmentKind(attachment)} /></span><span><b>{attachment.name}</b><small>{attachment.type || "文件"} · {Math.max(1, Math.round(attachment.size / 1024))} KB</small></span><i>添加到画布</i></button>) : <div className="canvas-drawer-empty"><Icon name="assets" /><b>暂时没有素材</b><p>可在这里上传文本、图片、音频或视频。</p></div>}
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
              <label><span>状态</span><select value={editingNode.data.status} onChange={(event) => updateNodeData(editingNode.id, { status: event.target.value as WorkflowNodeStatus })}><option value="idle">待处理</option><option value="ready">可执行</option><option value="running">执行中</option><option value="done">已完成</option><option value="failed">失败</option></select></label>
            </div>
            <footer><button type="button" onClick={() => setEditingNodeId(null)}>完成</button></footer>
          </section>
        </div>
      )}

      {panelOpen && (
        <aside className="canvas-agent-panel">
          <header className="canvas-agent-panel-header"><div><small>{LINE_LABELS[work.line]} · CREATION AGENT</small><strong>新对话</strong></div><span className={gateway && gateway.mode !== "demo" ? "agent-status-dot is-live" : "agent-status-dot"} title={gateway?.label ?? "正在检测 Agent"} /><nav aria-label="对话操作"><button type="button" onClick={() => { setPrompt(""); setActiveJob(null); setPanelTab("skills"); }} aria-label="新建对话" title="新建对话"><Icon name="add" /></button><button type="button" onClick={() => setPanelTab("history")} aria-label="历史对话" title="历史对话"><Icon name="history" /></button><button type="button" onClick={() => setOverlay("share")} aria-label="分享" title="分享"><Icon name="share" /></button><button type="button" onClick={() => setPanelTab("settings")} aria-label="Agent 设置" title="Agent 设置"><Icon name="tools" /></button></nav><button type="button" onClick={() => setPanelOpen(false)} aria-label="关闭 Agent 面板"><Icon name="close" /></button></header>
          <nav className="canvas-agent-tabs" role="tablist" aria-label="Agent 面板">
            <button type="button" role="tab" aria-selected={panelTab === "skills"} className={panelTab === "skills" ? "is-active" : ""} onClick={() => setPanelTab("skills")}>建议 Skill</button>
            <button type="button" role="tab" aria-selected={panelTab === "history"} className={panelTab === "history" ? "is-active" : ""} onClick={() => setPanelTab("history")}>历史{runHistory.length > 0 && <b>{runHistory.length}</b>}</button>
            <button type="button" role="tab" aria-selected={panelTab === "settings"} className={panelTab === "settings" ? "is-active" : ""} onClick={() => setPanelTab("settings")}>设置</button>
          </nav>
          <div className="canvas-agent-panel-body">
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
          <button type="button" className={composerMenu === "model" ? "canvas-composer-config is-active" : "canvas-composer-config"} aria-label="选择模型" title="选择模型" aria-expanded={composerMenu === "model"} onClick={() => setComposerMenu((current) => current === "model" ? null : "model")}><Icon name="image" /><span>{selectedModel?.name ?? "选择模型"}</span></button>
          <button type="button" className="canvas-composer-config" aria-label="Skill" title="Skill" onClick={() => { setPanelOpen(true); setPanelTab("skills"); setComposerMenu(null); }}><Icon name="sparkle" /><span>Skill</span></button>
          <button type="button" className={composerMenu === "mode" ? "canvas-composer-config is-active" : "canvas-composer-config"} aria-label="生成模式" title="生成模式" aria-expanded={composerMenu === "mode"} onClick={() => setComposerMenu((current) => current === "mode" ? null : "mode")}><Icon name="move" /><span>{creationConfig.generationMode === "auto" ? "自动" : "手动"}</span></button>
          <span className="canvas-gateway-label">{gateway?.label ?? "正在检测本地 Agent…"}</span>
          {activeSkill && <button type="button" className="canvas-active-skill" onClick={() => { setActiveSkill(null); setPrompt(""); }}>Skill · {suggestedSkills.find((skill) => skill.id === activeSkill)?.title}<i>×</i></button>}
          <span className="canvas-composer-spacer" />
          <small>Enter 发送 · Shift+Enter 换行</small>
          <button type="button" className="canvas-composer-send" disabled={!gateway || !prompt.trim() || submitting} onClick={() => void submit()} aria-label="发送 Agent 指令">{submitting ? <span className="canvas-submit-spinner">•••</span> : <Icon name="send" />}</button>
        </footer>
        {composerMenu === "model" && <div className="canvas-composer-popover canvas-model-picker" role="dialog" aria-label="选择模型">
          <header><strong>选择模型</strong><button type="button" onClick={() => setComposerMenu(null)} aria-label="关闭"><Icon name="close" /></button></header>
          <nav role="tablist" aria-label="模型类型">{(["text", "image", "video", "audio"] as const).map((modality) => <button key={modality} type="button" role="tab" aria-selected={modelModality === modality} className={modelModality === modality ? "is-active" : ""} onClick={() => setModelModality(modality)}>{modality === "text" ? "文本" : modality === "image" ? "图片" : modality === "video" ? "视频" : "音频"}</button>)}</nav>
          <div>{MODEL_GROUPS[modelModality].map((model) => <button key={model.id} type="button" className={creationConfig.model.modelId === model.id ? "is-selected" : ""} onClick={() => {
            setCreationConfig((current) => ({ ...current, model: { modality: model.modality, modelId: model.id } }));
            setModelModality(model.modality);
            setComposerMenu(null);
            setNotice(`已选择 ${model.name}`);
          }}><span><b>{model.name}</b><small>{model.provider} · {model.description}</small></span>{model.recommended && <i>推荐</i>}</button>)}</div>
        </div>}
        {composerMenu === "mode" && <div className="canvas-composer-popover canvas-mode-picker" role="dialog" aria-label="生成模式">
          <header><strong>生成模式</strong><button type="button" onClick={() => setComposerMenu(null)} aria-label="关闭"><Icon name="close" /></button></header>
          <button type="button" aria-pressed={creationConfig.generationMode === "manual"} className={creationConfig.generationMode === "manual" ? "is-selected" : ""} onClick={() => { setCreationConfig((current) => ({ ...current, generationMode: "manual" })); setComposerMenu(null); }}><span><b>手动模式</b><small>Agent 在每次生成前询问</small></span><i>{creationConfig.generationMode === "manual" ? "✓" : ""}</i></button>
          <button type="button" aria-pressed={creationConfig.generationMode === "auto"} className={creationConfig.generationMode === "auto" ? "is-selected" : ""} onClick={() => { setCreationConfig((current) => ({ ...current, generationMode: "auto" })); setComposerMenu(null); }}><span><b>自动模式</b><small>Agent 按工作流连续推进</small></span><i>{creationConfig.generationMode === "auto" ? "✓" : ""}</i></button>
        </div>}
      </section>

      {overlay && (
        <div className="canvas-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setOverlay(null); }}>
          <section className={`canvas-modal canvas-modal-${overlay}`} role="dialog" aria-modal="true" aria-label={overlay === "shortcuts" ? "快捷键" : overlay === "tutorial" ? "画布教程" : overlay === "share" ? "发布与分享" : "清除本机作品数据"}>
            <header><div><small>{overlay === "share" ? "CANVAS" : overlay === "clear-data" ? "LOCAL DATA" : "CANVAS GUIDE"}</small><strong>{overlay === "shortcuts" ? "快捷键" : overlay === "tutorial" ? "快速上手" : overlay === "share" ? "发布与分享" : "清除本机作品数据"}</strong></div><button type="button" onClick={() => setOverlay(null)} aria-label="关闭"><Icon name="close" /></button></header>
            {overlay === "shortcuts" ? <div className="canvas-shortcut-list"><span><kbd>⌘ Z</kbd><b>撤销</b></span><span><kbd>⇧⌘ Z</kbd><b>重做</b></span><span><kbd>⌘ C</kbd><b>复制节点</b></span><span><kbd>⌘ V</kbd><b>粘贴节点</b></span><span><kbd>⌘ D</kbd><b>创建副本</b></span><span><kbd>⌫</kbd><b>删除节点</b></span><span><kbd>A</kbd><b>打开添加节点</b></span><span><kbd>V</kbd><b>选择工具</b></span><span><kbd>H</kbd><b>移动画布</b></span><span><kbd>G</kbd><b>切换网格吸附</b></span><span><kbd>?</kbd><b>查看快捷键</b></span><span><kbd>Esc</kbd><b>关闭弹层</b></span></div> : overlay === "tutorial" ? <ol className="canvas-tutorial-list"><li><i>1</i><span><b>选择或添加节点</b><small>从左侧添加文本、图片、音频等工作流节点。</small></span></li><li><i>2</i><span><b>连接并整理流程</b><small>拖动节点连接点建立依赖，再用底部整理按钮排列。</small></span></li><li><i>3</i><span><b>让 Agent 执行</b><small>选择右侧建议 Skill，或在底部直接输入下一步任务。</small></span></li></ol> : overlay === "share" ? <div className="canvas-share-actions">
              <button type="button" onClick={() => void copyShareLink()}><span><Icon name="share" /></span><span><b>复制分享链接</b><small>使用当前稳定画布 URL；云端同步后可跨设备恢复。</small></span></button>
              <button type="button" onClick={exportCanvasDocument}><span><Icon name="download" /></span><span><b>导出画布 JSON</b><small>下载节点、连线、视图与 Agent 运行记录的便携副本。</small></span></button>
            </div> : <div className="canvas-clear-data-body"><p>将从这台设备删除当前作品记录、画布快照和关联的本机素材。登录、主题、收藏、其他作品及云端项目不会受影响。</p><div><button type="button" onClick={() => setOverlay(null)}>取消</button><button type="button" className="is-danger" onClick={() => onClearLocalData(attachments.map((attachment) => attachment.id))}>清除本地数据</button></div></div>}
          </section>
        </div>
      )}

      {notice && <div className="canvas-toast" role="status">{notice}</div>}
    </main>
  );
}
