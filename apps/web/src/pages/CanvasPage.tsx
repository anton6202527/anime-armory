import { useEffect, useMemo, useState } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
} from "@xyflow/react";
import { BrandIcon } from "../components/BrandIcon";
import { LineIcon } from "../components/LineIcon";
import { createAgentGateway, type AgentGateway } from "../lib/agent";
import type { AgentJob, CreationLine, WebWork } from "../types";

const LABELS: Record<CreationLine, string> = {
  novel: "写小说",
  n2d: "制漫剧",
  comic: "画漫画",
  ad: "拍广告",
  mv: "制 MV",
  song: "写歌",
};

function initialGraph(work: WebWork): { nodes: Node[]; edges: Edge[] } {
  const sourceLabel = work.attachments[0]?.name || (work.prompt ? "创作需求" : "未命名灵感");
  const common: Node[] = [
    { id: "source", position: { x: 40, y: 190 }, data: { label: sourceLabel }, className: "flow-node source-node" },
    { id: "script", position: { x: 390, y: 190 }, data: { label: work.line === "novel" ? "故事结构" : work.line === "song" ? "词曲方案" : "脚本与分镜" }, className: "flow-node plan-node" },
  ];
  const edges: Edge[] = [{ id: "source-script", source: "source", target: "script", animated: true }];
  if (work.line === "novel") return { nodes: common, edges };

  common.push({ id: "visual", position: { x: 740, y: 100 }, data: { label: work.line === "song" ? "试听版本" : "视觉资产" }, className: "flow-node visual-node" });
  edges.push({ id: "script-visual", source: "script", target: "visual" });

  if (work.line === "comic") {
    common.push({ id: "compose", position: { x: 740, y: 310 }, data: { label: "排版与嵌字" }, className: "flow-node output-node" });
    edges.push({ id: "script-compose", source: "script", target: "compose" }, { id: "visual-compose", source: "visual", target: "compose" });
    return { nodes: common, edges };
  }

  if (work.line !== "song") {
    common.push({ id: "motion", position: { x: 1090, y: 190 }, data: { label: work.line === "ad" ? "广告成片" : "视频与合成" }, className: "flow-node output-node" });
    edges.push({ id: "visual-motion", source: "visual", target: "motion" });
  }
  return { nodes: common, edges };
}

export function CanvasPage({ work, onHome }: { work: WebWork; onHome: () => void }) {
  const graph = useMemo(() => initialGraph(work), [work]);
  const [nodes, setNodes, onNodesChange] = useNodesState(graph.nodes);
  const [edges, , onEdgesChange] = useEdgesState(graph.edges);
  const [gateway, setGateway] = useState<AgentGateway | null>(null);
  const [prompt, setPrompt] = useState(work.prompt);
  const [job, setJob] = useState<AgentJob | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);

  useEffect(() => {
    let alive = true;
    let timer = 0;
    const refreshGateway = async () => {
      const nextGateway = await createAgentGateway();
      if (!alive) return;
      setGateway(nextGateway);
      timer = window.setTimeout(() => void refreshGateway(), 10_000);
    };
    void refreshGateway();
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, []);
  const cloudLabel = work.cloudState === "synced"
    ? "R2 已同步"
    : work.cloudState === "syncing"
      ? "正在同步…"
      : work.cloudState === "auth-required"
        ? "登录后云同步"
        : work.cloudState === "failed"
          ? "同步失败"
          : "本地草稿";

  async function submit() {
    if (!gateway || !prompt.trim() || submitting) return;
    setSubmitting(true);
    try {
      const nextJob = await gateway.submit({ work, prompt: prompt.trim() });
      setJob(nextJob);
      setNodes((items) => items.map((node) => node.id === "script" ? {
        ...node,
        data: { label: `${String(node.data.label)} · 任务已提交` },
      } : node));
      if (gateway.status && (nextJob.state === "queued" || nextJob.state === "running")) {
        let current = nextJob;
        while (current.state === "queued" || current.state === "running") {
          await new Promise((resolve) => window.setTimeout(resolve, 1200));
          current = await gateway.status(current.id);
          setJob(current);
        }
      }
    } catch (error) {
      setJob({ id: crypto.randomUUID(), state: "failed", message: String(error) });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="canvas-shell">
      <header className="canvas-header">
        <button type="button" className="canvas-brand" onClick={onHome} aria-label="返回首页"><BrandIcon /></button>
        <span className="crumb-separator">/</span>
        <span className="line-crumb"><LineIcon line={work.line} />{LABELS[work.line]}</span>
        <span className="crumb-separator">/</span>
        <strong>{work.name}</strong>
        <span className="header-spacer" />
        <span className={work.cloudState === "synced" ? "mode-pill cloud" : "mode-pill"} title={work.cloudError}>{cloudLabel}</span>
        <button type="button" className="token-pill" title="会员与 Token 计费将在服务端接入">Token —</button>
        <button type="button" className="panel-toggle" onClick={() => setPanelOpen((open) => !open)} aria-label="切换 Agent 面板">☷</button>
      </header>

      <aside className="canvas-rail" aria-label="画布工具">
        <button className="active" type="button" title="工作流">⌘</button>
        <button type="button" title="素材">▧</button>
        <button type="button" title="评论">◌</button>
        <span />
        <button type="button" title="帮助">?</button>
      </aside>

      <section className="flow-stage">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
          fitViewOptions={{ padding: 0.25 }}
          minZoom={0.35}
          maxZoom={1.5}
        >
          <Background variant={BackgroundVariant.Dots} gap={20} size={1.15} color="rgba(120,126,145,.3)" />
          <MiniMap pannable zoomable nodeColor={(node) => node.id === "source" ? "#8d8f99" : node.id === "visual" ? "#656873" : "#383b45"} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </section>

      {panelOpen && (
        <aside className="agent-panel">
          <div className="agent-panel-head">
            <div><small>CREATION AGENT</small><strong>{LABELS[work.line]}工作流</strong></div>
            <span className={gateway && gateway.mode !== "demo" ? "status-dot live" : "status-dot"} />
          </div>
          <div className="agent-context">
            <small>当前作品</small>
            <strong>{work.name}</strong>
            <p>{work.attachments.length ? `已附加 ${work.attachments.length} 个源文件` : "从文字需求开始创作"}</p>
          </div>
          <div className="agent-timeline">
            <div className="done"><i>✓</i><span><b>作品已创建</b><small>画布工作流已准备</small></span></div>
            <div className={job?.state === "succeeded" ? "done" : "current"}><i>{job?.state === "succeeded" ? "✓" : "2"}</i><span><b>提交创作任务</b><small>{job?.message ?? (gateway ? `已连接${gateway.label}` : "正在检测本地 Agent…")}</small></span></div>
            <div className={job?.state === "succeeded" ? "current" : ""}><i>3</i><span><b>生成与审阅</b><small>{gateway?.mode === "local" ? "本地 CLI 完成后刷新作品画布" : "云端模型返回结果后更新画布"}</small></span></div>
          </div>
          {job?.output && <pre className="agent-output" title="本地 Agent 最新输出">{job.output.slice(-4000)}</pre>}
          <div className="agent-security-note"><b>{gateway?.mode === "local" ? "本地桥接已隔离" : "密钥只放服务端"}</b><span>{gateway?.mode === "local" ? "仅在你确认后，将任务发送到本机受控作品目录。" : "浏览器仅提交任务，不会接触模型 API Key。"}</span></div>
        </aside>
      )}

      <section className={panelOpen ? "canvas-command with-panel" : "canvas-command"}>
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
        <div><span>{gateway?.label ?? "正在检测本地 Agent…"}</span><span>Enter 发送 · Shift+Enter 换行</span><button type="button" disabled={!gateway || !prompt.trim() || submitting} onClick={() => void submit()}>{submitting ? "…" : "↑"}</button></div>
      </section>
    </main>
  );
}
