import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import {
  Background,
  Controls,
  MiniMap,
  MarkerType,
  ReactFlow,
  type Edge,
  type Node,
  type NodeChange,
  useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { readCanvasLayout, readClipEdit, writeCanvasLayout, writeClipEdit } from "../api";
import { ClipNode } from "./ClipNode";
import { QualitySummaryStrip } from "./QualitySummary";
import { useI18n } from "../i18n";
import type { CanvasClip, ClipEditData, ClipEditPatch } from "../types";
import type { ViewProps } from "../views/registry";

const nodeTypes = { clip: ClipNode };
const COL_W = 340;
type EditableCanvasClip = CanvasClip & { onEdit?: () => void };

function autoPosition(i: number) {
  return { x: i * COL_W, y: (i % 2) * 70 };
}

function editablePrompt(saved: ClipEditData): string {
  return [
    saved.prompt && `prompt: ${saved.prompt}`,
    saved.image_prompt && `image_prompt: ${saved.image_prompt}`,
    saved.video_prompt && `video_prompt: ${saved.video_prompt}`,
    saved.positive_prompt && `positive_prompt: ${saved.positive_prompt}`,
    saved.negative_prompt && `negative_prompt: ${saved.negative_prompt}`,
  ].filter(Boolean).join("\n");
}

function ClipEditDialog(props: {
  rootPath: string;
  ep: string;
  clip: CanvasClip;
  onClose: () => void;
  onSaved: (data: ClipEditData) => void;
}) {
  const { rootPath, ep, clip, onClose, onSaved } = props;
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [sourceRel, setSourceRel] = useState("");
  const [draft, setDraft] = useState<ClipEditPatch>({
    label: clip.label,
    duration: clip.duration ?? null,
    scene: clip.scene ?? "",
    rhythm: clip.rhythm ?? "",
    template: clip.template ?? "",
    prompt: "",
    image_prompt: "",
    video_prompt: "",
    positive_prompt: "",
    negative_prompt: "",
  });

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError("");
    readClipEdit(rootPath, ep, clip.id, clip.number)
      .then((data) => {
        if (!alive) return;
        setSourceRel(data.source_rel);
        setDraft({
          label: data.label,
          duration: data.duration ?? null,
          scene: data.scene ?? "",
          rhythm: data.rhythm ?? "",
          template: data.template ?? "",
          prompt: data.prompt ?? "",
          image_prompt: data.image_prompt ?? "",
          video_prompt: data.video_prompt ?? "",
          positive_prompt: data.positive_prompt ?? "",
          negative_prompt: data.negative_prompt ?? "",
        });
      })
      .catch((e) => alive && setError(String(e)))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [clip.id, clip.number, ep, rootPath]);

  function setField<K extends keyof ClipEditPatch>(key: K, value: ClipEditPatch[K]) {
    setDraft((prev) => ({ ...prev, [key]: value }));
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      const saved = await writeClipEdit(rootPath, ep, clip.id, clip.number, {
        ...draft,
        label: draft.label.trim(),
        duration: draft.duration && draft.duration > 0 ? draft.duration : null,
      });
      onSaved(saved);
      onClose();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop canvas-edit-backdrop" onClick={onClose}>
      <form className="modal canvas-edit-modal" onClick={(e) => e.stopPropagation()} onSubmit={save}>
        <div className="modal-head">
          <h2>{t("canvas.editTitle")}</h2>
          <button type="button" className="modal-close" title={t("common.close")} onClick={onClose}>×</button>
        </div>
        <div className="canvas-edit-body">
          {loading ? (
            <div className="stub-view">{t("common.loading")}</div>
          ) : (
            <>
              <div className="canvas-edit-source">{sourceRel || t("canvas.editStoryboardOnly")}</div>
              <div className="canvas-edit-grid">
                <label>
                  <span>{t("canvas.editLabel")}</span>
                  <input value={draft.label} onChange={(e) => setField("label", e.target.value)} />
                </label>
                <label>
                  <span>{t("canvas.editDuration")}</span>
                  <input
                    type="number"
                    min="0"
                    step="0.1"
                    value={draft.duration ?? ""}
                    onChange={(e) => setField("duration", e.target.value ? Number(e.target.value) : null)}
                  />
                </label>
                <label>
                  <span>{t("canvas.editScene")}</span>
                  <input value={draft.scene} onChange={(e) => setField("scene", e.target.value)} />
                </label>
                <label>
                  <span>{t("canvas.editRhythm")}</span>
                  <input value={draft.rhythm} onChange={(e) => setField("rhythm", e.target.value)} />
                </label>
                <label>
                  <span>{t("canvas.editTemplate")}</span>
                  <input value={draft.template} onChange={(e) => setField("template", e.target.value)} />
                </label>
              </div>
              <label className="canvas-edit-textarea">
                <span>{t("canvas.editPrompt")}</span>
                <textarea value={draft.prompt} onChange={(e) => setField("prompt", e.target.value)} />
              </label>
              <div className="canvas-edit-grid two">
                <label>
                  <span>image_prompt</span>
                  <textarea value={draft.image_prompt} onChange={(e) => setField("image_prompt", e.target.value)} />
                </label>
                <label>
                  <span>video_prompt</span>
                  <textarea value={draft.video_prompt} onChange={(e) => setField("video_prompt", e.target.value)} />
                </label>
                <label>
                  <span>positive_prompt</span>
                  <textarea value={draft.positive_prompt} onChange={(e) => setField("positive_prompt", e.target.value)} />
                </label>
                <label>
                  <span>negative_prompt</span>
                  <textarea value={draft.negative_prompt} onChange={(e) => setField("negative_prompt", e.target.value)} />
                </label>
              </div>
            </>
          )}
          {error && <div className="editor-error">{t("canvas.editFailed", { error })}</div>}
        </div>
        <div className="modal-foot">
          <button type="button" onClick={onClose}>{t("common.close")}</button>
          <button type="submit" className="primary" disabled={loading || saving}>
            {saving ? t("canvas.editSaving") : t("canvas.editSave")}
          </button>
        </div>
      </form>
    </div>
  );
}

// Infinite canvas for n2d/ad/mv: clip nodes laid out left→right with
// 接力链 (continuity) edges between consecutive clips and seam transitions.
export function CanvasPane({ canvas, root, refreshKey = 0 }: ViewProps) {
  const { t } = useI18n();
  const [nodes, setNodes, onNodesChangeBase] = useNodesState<Node>([]);
  const [editing, setEditing] = useState<CanvasClip | null>(null);
  const [layout, setLayout] = useState<Map<string, { x: number; y: number }>>(new Map());
  const nodesRef = useRef<Node[]>([]);

  useEffect(() => {
    nodesRef.current = nodes;
  }, [nodes]);

  const edges = useMemo(() => {
    if (!canvas) return [] as Edge[];
    const nodeIds = new Set(canvas.clips.map((clip) => clip.id));
    const seams = canvas.seams.filter((s) => nodeIds.has(s.from) && nodeIds.has(s.to) && s.from !== s.to);
    const visibleSeams = seams.length
      ? seams
      : canvas.clips.slice(0, -1).map((clip, i) => ({
          from: clip.id,
          to: canvas.clips[i + 1].id,
          transition: "continuity",
        }));
    return visibleSeams.map((s) => ({
      id: `${s.from}->${s.to}`,
      source: s.from,
      target: s.to,
      label: s.transition,
      animated: s.transition === "hard_cut",
      type: "smoothstep",
      zIndex: 1,
      style: { stroke: "#6f86b8", strokeWidth: 1.8 },
      markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: "#6f86b8" },
      labelStyle: { fill: "#bac7e6", fontSize: 10, fontWeight: 600 },
      labelBgStyle: { fill: "#11151f", fillOpacity: 0.9 },
    }));
  }, [canvas]);

  useEffect(() => {
    let alive = true;
    if (!canvas) return;
    readCanvasLayout(root.path, canvas.episode)
      .then((saved) => {
        if (!alive) return;
        setLayout(new Map((saved.nodes || []).map((n) => [n.id, { x: n.x, y: n.y }])));
      })
      .catch(() => alive && setLayout(new Map()));
    return () => {
      alive = false;
    };
  }, [canvas?.episode, root.path]);

  useEffect(() => {
    if (!canvas) {
      setNodes([]);
      return;
    }
    setNodes(canvas.clips.map((clip, i) => ({
      id: clip.id,
      type: "clip",
      position: layout.get(clip.id) ?? autoPosition(i),
      data: {
        ...clip,
        mediaRevision: refreshKey,
        onEdit: () => setEditing(clip),
      } as unknown as Record<string, unknown>,
    })));
  }, [canvas, layout, refreshKey, setNodes]);

  const persistLayout = useCallback((nextNodes: Node[]) => {
    if (!canvas) return;
    const positions = nextNodes.map((node) => ({
      id: node.id,
      x: node.position.x,
      y: node.position.y,
    }));
    writeCanvasLayout(root.path, canvas.episode, positions).catch(() => {});
  }, [canvas, root.path]);

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    onNodesChangeBase(changes);
  }, [onNodesChangeBase]);

  const saveCurrentLayout = useCallback((dragged?: Node) => {
    const next = dragged
      ? nodesRef.current.map((node) => (node.id === dragged.id ? { ...node, position: dragged.position } : node))
      : nodesRef.current;
    setLayout(new Map(next.map((node) => [node.id, { x: node.position.x, y: node.position.y }])));
    persistLayout(next);
  }, [persistLayout]);

  const resetLayout = useCallback(() => {
    if (!canvas) return;
    const next = nodesRef.current.map((node, i) => ({ ...node, position: autoPosition(i) }));
    setLayout(new Map(next.map((node) => [node.id, { x: node.position.x, y: node.position.y }])));
    setNodes(next);
    persistLayout(next);
  }, [canvas, persistLayout, setNodes]);

  const onSavedClip = useCallback((saved: ClipEditData) => {
    setNodes((current) => current.map((node) => {
      if (node.id !== editing?.id) return node;
      const data = node.data as unknown as EditableCanvasClip;
      return {
        ...node,
        data: {
          ...data,
          label: saved.label,
          duration: saved.duration ?? undefined,
          scene: saved.scene,
          rhythm: saved.rhythm,
          template: saved.template,
          prompt: editablePrompt(saved) || data.prompt,
          onEdit: data.onEdit,
        } as unknown as Record<string, unknown>,
      };
    }));
  }, [editing?.id, setNodes]);

  if (!canvas || canvas.clips.length === 0) {
    return <div className="stub-view">{t("canvas.noStoryboard")}</div>;
  }

  return (
    <div className="canvas-wrap">
      <div className="canvas-toolbar">
        <span>{t("canvas.dragHint")}</span>
        <button type="button" onClick={resetLayout}>{t("canvas.resetLayout")}</button>
        <QualitySummaryStrip summary={canvas.quality} />
      </div>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onNodeDragStop={(_, node) => saveCurrentLayout(node)}
        nodesDraggable
        nodesConnectable={false}
        fitView
        minZoom={0.1}
        onlyRenderVisibleElements
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={24} color="#1b2230" />
        <MiniMap pannable zoomable maskColor="rgba(11,14,20,.7)" nodeColor="#2a3450" />
        {/* zoom + interactivity only — the fit/reset ("reload") button is hidden */}
        <Controls showFitView={false} />
      </ReactFlow>
      {editing && (
        <ClipEditDialog
          rootPath={root.path}
          ep={canvas.episode}
          clip={editing}
          onClose={() => setEditing(null)}
          onSaved={onSavedClip}
        />
      )}
    </div>
  );
}
