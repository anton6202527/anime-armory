import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import {
  Background,
  BackgroundVariant,
  MiniMap,
  MarkerType,
  Panel,
  ReactFlow,
  type ReactFlowInstance,
  type Edge,
  type Node,
  type NodeChange,
  useReactFlow,
  useViewport,
  useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { readCanvasLayout, readClipEdit, writeCanvasLayout, writeClipEdit } from "../api";
import { ClipNode } from "./ClipNode";
import { Codicon } from "./Codicon";
import { useI18n } from "../i18n";
import type { CanvasClip, CanvasFrame, ClipEditData, ClipEditPatch } from "../types";
import type { ViewProps } from "../views/registry";

const nodeTypes = { clip: ClipNode };
const FLOW_NODE = {
  asset: (id: string) => `asset:${id}`,
  shot: (id: string) => `shot:${id}`,
  frame: (id: string, frameIndex: number) => `frame:${id}:${frameIndex}`,
  video: (id: string) => `video:${id}`,
};
const OLD_LANE_X = {
  shot: 310,
  video: 690,
};
const LANE_X = {
  shot: 410,
  video: 840,
};
const ASSET_ANCHOR_X = LANE_X.shot - 140;
const ROW_H = 490;
const FRAME_NODE_H = 138;
const FRAME_NODE_GAP = 14;
const FRAME_NODE_STEP = FRAME_NODE_H + FRAME_NODE_GAP;
type CanvasNodeVariant = "asset-anchor" | "frame" | "shot" | "video";
type EditableCanvasClip = CanvasClip & {
  variant?: CanvasNodeVariant;
  laneMeta?: string[];
  promptTooltip?: string;
  rootPath?: string;
  onEdit?: () => void;
};
interface CanvasAssetImage {
  id: string;
  label: string;
  abs: string;
  exists: boolean;
  revision?: string;
  prompt?: string;
  clipIds: string[];
  roles: string[];
}

function isReferenceInputFrame(frame: CanvasFrame): boolean {
  const text = `${frame.role || ""} ${frame.label || ""} ${frame.abs || ""}`;
  return /出图[\\/]共享|shared_asset|入参|参考|引用|reference|ref|asset|input|consumed|style/i.test(text);
}

function displayFramesForClip(clip: CanvasClip): CanvasFrame[] {
  const frames = (clip.frames || []).filter((frame) => (frame.abs || frame.exists) && !isReferenceInputFrame(frame));
  if (frames.length) return frames;
  if (clip.first_frame_abs) {
    return [{
      role: "first",
      label: "首帧",
      abs: clip.first_frame_abs,
      exists: clip.first_frame_exists,
      prompt: clip.prompt,
    }];
  }
  return [{
    role: "missing",
    label: clip.label,
    abs: "",
    exists: false,
    prompt: clip.prompt,
  }];
}

function clipRowHeights(clips: CanvasClip[]): number[] {
  return clips.map((clip) => Math.max(ROW_H, displayFramesForClip(clip).length * FRAME_NODE_STEP + 18));
}

function clipRowOffsets(clips: CanvasClip[]): number[] {
  const heights = clipRowHeights(clips);
  let y = 0;
  return heights.map((height) => {
    const current = y;
    y += height;
    return current;
  });
}

function autoFramePosition(rowY: number, frameIndex: number) {
  return { x: LANE_X.shot, y: rowY + frameIndex * FRAME_NODE_STEP };
}

function autoShotPosition(i: number) {
  return { x: LANE_X.shot, y: i * ROW_H };
}

function autoVideoPosition(rowY: number) {
  return { x: LANE_X.video, y: rowY };
}

function autoAssetAnchorPosition(ref: CanvasAssetImage, clips: CanvasClip[], rowOffsets: number[], assetIndex: number) {
  const targetRows = ref.clipIds
    .map((clipId) => clips.findIndex((clip) => clip.id === clipId))
    .filter((index) => index >= 0)
    .map((index) => rowOffsets[index] + FRAME_NODE_H / 2);
  const baseY = targetRows.length
    ? targetRows.reduce((sum, y) => sum + y, 0) / targetRows.length
    : assetIndex * 26;
  return { x: ASSET_ANCHOR_X, y: baseY + ((assetIndex % 7) - 3) * 10 };
}

function positionForNode(id: string, i: number) {
  if (id.startsWith("video:")) return autoVideoPosition(i * ROW_H);
  return autoShotPosition(i);
}

function savedOrAutoPosition(
  id: string,
  saved: { x: number; y: number } | undefined,
  auto: { x: number; y: number },
) {
  if (!saved) return auto;
  if (id.startsWith("shot:") && Math.abs(saved.x - OLD_LANE_X.shot) <= 8) {
    return { ...saved, x: auto.x };
  }
  if (id.startsWith("frame:") && Math.abs(saved.x - OLD_LANE_X.shot) <= 8) {
    return { ...saved, x: auto.x };
  }
  if (id.startsWith("video:") && Math.abs(saved.x - OLD_LANE_X.video) <= 8) {
    return { ...saved, x: auto.x };
  }
  return saved;
}

function isEditableShortcutTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable) return true;
  const tagName = target.tagName.toLowerCase();
  return tagName === "input" || tagName === "textarea" || tagName === "select";
}

function clipPromptTooltip(clip: CanvasClip): string {
  return [
    clip.number != null ? `${clip.number}. ${clip.label}` : clip.label,
    clip.scene || "",
    clip.template ? `template: ${clip.template}` : "",
    clip.rhythm ? `rhythm: ${clip.rhythm}` : "",
    clip.prompt || "",
  ].filter(Boolean).join("\n");
}

function hashString(value: string): string {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(36);
}

function assetLabel(frame: CanvasFrame, abs: string): string {
  const name = abs.split(/[\\/]/).pop()?.replace(/\.[^.]+$/, "") || frame.label || frame.role || "Reference";
  return frame.label || frame.role || name;
}

function isSharedAssetFrame(frame: CanvasFrame): boolean {
  const abs = (frame.abs || "").replace(/\\/g, "/").toLowerCase();
  const role = (frame.role || "").toLowerCase();
  return role === "shared_asset" || abs.includes("/出图/共享/") || abs.includes("/shared/");
}

function collectSharedAssetImages(sharedAssets: CanvasFrame[], clips: CanvasClip[]): CanvasAssetImage[] {
  const refs = new Map<string, CanvasAssetImage & {
    clipIdSet: Set<string>;
    roleSet: Set<string>;
    firstClipIndex: number;
  }>();
  const ensureAsset = (frame: CanvasFrame, clipIndex = Number.MAX_SAFE_INTEGER) => {
    if (!frame.abs || !isSharedAssetFrame(frame)) return null;
    const current = refs.get(frame.abs) ?? {
      id: `asset-${hashString(frame.abs)}`,
      label: assetLabel(frame, frame.abs),
      abs: frame.abs,
      exists: frame.exists,
      revision: frame.revision,
      prompt: frame.prompt,
      clipIds: [],
      roles: [],
      clipIdSet: new Set<string>(),
      roleSet: new Set<string>(),
      firstClipIndex: clipIndex,
    };
    current.exists = current.exists || frame.exists;
    current.revision = frame.revision || current.revision;
    current.prompt ||= frame.prompt;
    current.firstClipIndex = Math.min(current.firstClipIndex, clipIndex);
    if (frame.role) current.roleSet.add(frame.role);
    if (frame.label) current.roleSet.add(frame.label);
    refs.set(frame.abs, current);
    return current;
  };
  for (const frame of sharedAssets || []) ensureAsset(frame);
  const addFrame = (clip: CanvasClip, frame: CanvasFrame, clipIndex: number) => {
    const current = ensureAsset(frame, clipIndex);
    if (!current) return;
    current.prompt ||= frame.prompt || clip.prompt;
    current.clipIdSet.add(clip.id);
  };
  clips.forEach((clip, clipIndex) => {
    for (const frame of clip.frames || []) addFrame(clip, frame, clipIndex);
  });
  return Array.from(refs.values()).map((ref) => ({
    ...ref,
    clipIds: Array.from(ref.clipIdSet),
    roles: Array.from(ref.roleSet),
  })).sort((a, b) => a.firstClipIndex - b.firstClipIndex || a.label.localeCompare(b.label));
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
          prompt: data.prompt || clip.prompt || "",
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
          <button type="button" className="modal-close" aria-label={t("common.close")} onClick={onClose}>×</button>
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

function CanvasControlDock(props: {
  miniMapOpen: boolean;
  onToggleMiniMap: () => void;
  onResetLayout: () => void;
}) {
  const { miniMapOpen, onToggleMiniMap, onResetLayout } = props;
  const { t } = useI18n();
  const flow = useReactFlow();
  const viewport = useViewport();
  const dockRef = useRef<HTMLDivElement>(null);
  const [zoomMenuOpen, setZoomMenuOpen] = useState(false);
  const [zoomDraft, setZoomDraft] = useState("");
  const zoom = Math.max(0.1, Math.min(8, viewport.zoom));
  const zoomPercent = Math.round(zoom * 100);
  const zoomLabel = `${zoomPercent}%`;
  const shortcutMod = /Mac|iPhone|iPad|iPod/.test(window.navigator.platform) ? "⌘" : "Ctrl";

  const setZoom = useCallback((nextZoom: number) => {
    const bounded = Math.max(0.1, Math.min(8, nextZoom));
    flow.setViewport({ x: viewport.x, y: viewport.y, zoom: bounded }, { duration: 120 });
  }, [flow, viewport.x, viewport.y]);

  function openZoomMenu() {
    setZoomDraft(String(zoomPercent));
    setZoomMenuOpen(true);
  }

  function applyZoomDraft() {
    const value = Number(zoomDraft.replace("%", "").trim());
    if (!Number.isFinite(value)) {
      setZoomDraft(String(zoomPercent));
      return;
    }
    setZoom(value / 100);
  }

  const fitScreen = useCallback(() => {
    flow.fitView({ padding: 0.18, duration: 220 });
    setZoomMenuOpen(false);
  }, [flow]);

  function zoomTo(percent: number) {
    setZoom(percent / 100);
    setZoomDraft(String(percent));
    setZoomMenuOpen(false);
  }

  useEffect(() => {
    if (!zoomMenuOpen) return;
    const onPointerDown = (event: PointerEvent) => {
      const node = dockRef.current;
      if (node && event.target instanceof Node && !node.contains(event.target)) {
        setZoomMenuOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setZoomMenuOpen(false);
    };
    window.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [zoomMenuOpen]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!(event.metaKey || event.ctrlKey) || event.altKey || isEditableShortcutTarget(event.target)) return;
      const key = event.key;
      if (key === "+" || key === "=") {
        event.preventDefault();
        flow.zoomIn({ duration: 120 });
      } else if (key === "-" || key === "_") {
        event.preventDefault();
        flow.zoomOut({ duration: 120 });
      } else if (key === "0") {
        event.preventDefault();
        fitScreen();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [fitScreen, flow]);

  return (
    <Panel position="bottom-left" className="canvas-control-dock">
      <div className="canvas-control-row" ref={dockRef}>
        <button
          type="button"
          className="canvas-control-btn"
          title={t("canvas.resetLayout")}
          aria-label={t("canvas.resetLayout")}
          onClick={onResetLayout}
        >
          <Codicon name="refresh" />
        </button>
        <button
          type="button"
          className={"canvas-control-btn" + (miniMapOpen ? " active" : "")}
          title={t("canvas.minimap")}
          aria-label={t("canvas.minimap")}
          aria-pressed={miniMapOpen}
          onClick={onToggleMiniMap}
        >
          <Codicon name="map" />
        </button>
        <button
          type="button"
          className={"canvas-zoom-trigger" + (zoomMenuOpen ? " active" : "")}
          aria-label={t("canvas.zoom")}
          aria-expanded={zoomMenuOpen}
          onClick={() => (zoomMenuOpen ? setZoomMenuOpen(false) : openZoomMenu())}
        >
          {zoomLabel}
        </button>
        {zoomMenuOpen && (
          <div className="canvas-zoom-menu" role="menu" onPointerDown={(event) => event.stopPropagation()}>
            <label className="canvas-zoom-input-wrap">
              <input
                value={zoomDraft}
                inputMode="numeric"
                aria-label={t("canvas.zoomPercent")}
                onChange={(event) => setZoomDraft(event.target.value)}
                onBlur={applyZoomDraft}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    applyZoomDraft();
                    setZoomMenuOpen(false);
                  }
                }}
              />
              <span>%</span>
            </label>
            <button type="button" className="canvas-zoom-menu-item" onClick={() => flow.zoomIn({ duration: 120 })}>
              <span>{t("canvas.zoomInShort")}</span>
              <kbd>{shortcutMod}</kbd><kbd>+</kbd>
            </button>
            <button type="button" className="canvas-zoom-menu-item" onClick={() => flow.zoomOut({ duration: 120 })}>
              <span>{t("canvas.zoomOutShort")}</span>
              <kbd>{shortcutMod}</kbd><kbd>-</kbd>
            </button>
            <button type="button" className="canvas-zoom-menu-item" onClick={fitScreen}>
              <span>{t("canvas.fitScreen")}</span>
              <kbd>{shortcutMod}</kbd><kbd>0</kbd>
            </button>
            <div className="canvas-zoom-menu-divider" />
            {[50, 100, 800].map((percent) => (
              <button
                key={percent}
                type="button"
                className="canvas-zoom-menu-item"
                onClick={() => zoomTo(percent)}
              >
                <span>{t("canvas.zoomTo", { percent })}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </Panel>
  );
}

// Infinite canvas for visual production lines: character context -> shot nodes -> clip videos.
export function CanvasPane({ canvas, root }: ViewProps) {
  const { t } = useI18n();
  const [nodes, setNodes, onNodesChangeBase] = useNodesState<Node>([]);
  const [editing, setEditing] = useState<CanvasClip | null>(null);
  const [miniMapOpen, setMiniMapOpen] = useState(false);
  const [layoutLoaded, setLayoutLoaded] = useState(false);
  const [layout, setLayout] = useState<Map<string, { x: number; y: number }>>(new Map());
  const nodesRef = useRef<Node[]>([]);
  const layoutRef = useRef<Map<string, { x: number; y: number }>>(new Map());
  const flowRef = useRef<ReactFlowInstance | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const fittedEntryRef = useRef("");
  const pendingFitRef = useRef(false);

  useEffect(() => {
    nodesRef.current = nodes;
  }, [nodes]);

  const assetImages = useMemo(
    () => (canvas ? collectSharedAssetImages(canvas.shared_assets || [], canvas.clips) : []),
    [canvas],
  );
  const hasVideoLane = canvas?.source !== "panel_script";

  const edges = useMemo(() => {
    if (!canvas) return [] as Edge[];
    const firstFrameId = (clipId: string) => FLOW_NODE.frame(clipId, 0);
    const assetEdges = assetImages.flatMap((ref) =>
      ref.clipIds
        .filter((clipId) => canvas.clips.some((clip) => clip.id === clipId))
        .map((clipId) => ({
          id: `${FLOW_NODE.asset(ref.id)}->${firstFrameId(clipId)}`,
          source: FLOW_NODE.asset(ref.id),
          target: firstFrameId(clipId),
          className: "asset-edge",
          type: "default",
          zIndex: 0,
          interactionWidth: 14,
          style: { stroke: "rgba(66, 68, 74, .78)", strokeWidth: 1.6 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 11,
            height: 11,
            color: "rgba(66, 68, 74, .82)",
          },
        } satisfies Edge)),
    );
    const clipVideoEdges = hasVideoLane
      ? canvas.clips.flatMap((clip) => {
          const videoId = FLOW_NODE.video(clip.id);
          return displayFramesForClip(clip).map((_, frameIndex) => ({
            id: `${FLOW_NODE.frame(clip.id, frameIndex)}->${videoId}`,
            source: FLOW_NODE.frame(clip.id, frameIndex),
            target: videoId,
            className: clip.video_exists ? "video-edge video-edge-done" : "video-edge video-edge-pending",
            type: "default",
            zIndex: 1,
            interactionWidth: 14,
            style: {
              stroke: clip.video_exists ? "rgba(82, 116, 154, .64)" : "rgba(139, 121, 72, .62)",
              strokeWidth: 1.35,
            },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              width: 12,
              height: 12,
              color: clip.video_exists ? "rgba(82, 116, 154, .72)" : "rgba(139, 121, 72, .72)",
            },
          } satisfies Edge));
        })
      : [];
    return [...assetEdges, ...clipVideoEdges];
  }, [assetImages, canvas, hasVideoLane]);

  const flowNodes = useMemo(() => {
    if (!canvas) return [] as Node[];
    const rowOffsets = clipRowOffsets(canvas.clips);
    const assetAnchorNodes = assetImages.map((asset, index) => ({
      id: FLOW_NODE.asset(asset.id),
      type: "clip",
      position: autoAssetAnchorPosition(asset, canvas.clips, rowOffsets, index),
      selectable: false,
      draggable: false,
      data: {
        id: FLOW_NODE.asset(asset.id),
        label: asset.label,
        first_frame_exists: false,
        video_exists: false,
        frames: [],
        qa: [],
        qa_blocks: 0,
        qa_warnings: 0,
        qa_infos: 0,
        variant: "asset-anchor",
        __renderKey: hashString(`${asset.id}:${asset.label}:${asset.revision ?? ""}`),
      } as unknown as Record<string, unknown>,
    } satisfies Node));
    const frameNodes = canvas.clips.flatMap((clip, clipIndex) =>
      displayFramesForClip(clip).map((frame, frameIndex) => {
        const id = FLOW_NODE.frame(clip.id, frameIndex);
        const legacyShotPosition = frameIndex === 0
          ? layoutRef.current.get(FLOW_NODE.shot(clip.id))
          : undefined;
        const saved = layoutRef.current.get(id) ?? legacyShotPosition;
        return {
          id,
          type: "clip",
          position: savedOrAutoPosition(id, saved, autoFramePosition(rowOffsets[clipIndex], frameIndex)),
          data: {
            ...clip,
            frames: [frame],
            variant: "frame",
            promptTooltip: clipPromptTooltip(clip),
            __renderKey: hashString(JSON.stringify({ clip, frame })),
            onEdit: () => setEditing(clip),
          } as unknown as Record<string, unknown>,
        } satisfies Node;
      }),
    );
    const videoNodes = hasVideoLane
      ? canvas.clips.map((clip, i) => {
          const id = FLOW_NODE.video(clip.id);
          return {
            id,
            type: "clip",
            position: savedOrAutoPosition(id, layoutRef.current.get(id), autoVideoPosition(rowOffsets[i])),
            data: {
              ...clip,
              variant: "video",
              promptTooltip: clipPromptTooltip(clip),
              __renderKey: hashString(JSON.stringify(clip)),
              rootPath: root.path,
              onEdit: () => setEditing(clip),
            } as unknown as Record<string, unknown>,
          } satisfies Node;
        })
      : [];
    return [...assetAnchorNodes, ...frameNodes, ...videoNodes];
  }, [assetImages, canvas, hasVideoLane, layout, root.path]);

  useEffect(() => {
    let alive = true;
    setLayoutLoaded(false);
    if (!canvas) return;
    readCanvasLayout(root.path, canvas.episode)
      .then((saved) => {
        if (!alive) return;
        const nextLayout = new Map((saved.nodes || []).map((n) => [n.id, { x: n.x, y: n.y }]));
        layoutRef.current = nextLayout;
        setLayout(nextLayout);
        setLayoutLoaded(true);
      })
      .catch(() => {
        if (!alive) return;
        const nextLayout = new Map<string, { x: number; y: number }>();
        layoutRef.current = nextLayout;
        setLayout(nextLayout);
        setLayoutLoaded(true);
      });
    return () => {
      alive = false;
    };
  }, [canvas?.episode, root.path]);

  const fitCanvasView = useCallback((duration = 0) => {
    const flow = flowRef.current;
    if (!flow) {
      pendingFitRef.current = true;
      return;
    }
    pendingFitRef.current = false;
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        flowRef.current?.fitView({ padding: 0.18, duration });
      });
    });
  }, []);

  useEffect(() => {
    if (!canvas) {
      setNodes([]);
      return;
    }
    setNodes((current) => {
      const previous = new Map(current.map((node) => [node.id, node]));
      return flowNodes.map((next) => {
        const old = previous.get(next.id);
        if (!old) return next;
        const oldKey = (old.data as Record<string, unknown>).__renderKey;
        const nextKey = (next.data as Record<string, unknown>).__renderKey;
        if (
          oldKey === nextKey &&
          old.position.x === next.position.x &&
          old.position.y === next.position.y
        ) {
          return old;
        }
        return next;
      });
    });
  }, [canvas, flowNodes, setNodes]);

  useEffect(() => {
    if (!canvas || !layoutLoaded || flowNodes.length === 0) return;
    const entryKey = `${root.path}:${canvas.episode}`;
    if (fittedEntryRef.current === entryKey) return;
    fittedEntryRef.current = entryKey;
    fitCanvasView(0);
  }, [canvas, fitCanvasView, flowNodes.length, layoutLoaded, root.path]);

  const persistLayout = useCallback((nextNodes: Node[]) => {
    if (!canvas) return;
    const positions = nextNodes
      .filter((node) => !node.id.startsWith("lane:") && !node.id.startsWith("asset:"))
      .map((node) => ({
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
    layoutRef.current = new Map(next.map((node) => [node.id, { x: node.position.x, y: node.position.y }]));
    persistLayout(next);
  }, [persistLayout]);

  const resetLayout = useCallback(() => {
    if (!canvas) return;
    const rowOffsets = clipRowOffsets(canvas.clips);
    const next = nodesRef.current.map((node) => {
      if (node.id.startsWith("lane:")) return node;
      if (node.id.startsWith("asset:")) return node;
      const frameMatch = /^frame:(.+):(\d+)$/.exec(node.id);
      if (frameMatch) {
        const clipIndex = Math.max(0, canvas.clips.findIndex((clip) => clip.id === frameMatch[1]));
        return { ...node, position: autoFramePosition(rowOffsets[clipIndex], Number(frameMatch[2])) };
      }
      const baseId = node.id.replace(/^shot:|^video:/, "");
      const i = Math.max(0, canvas.clips.findIndex((clip) => clip.id === baseId));
      return { ...node, position: positionForNode(node.id, rowOffsets[i] / ROW_H) };
    });
    layoutRef.current = new Map(next.map((node) => [node.id, { x: node.position.x, y: node.position.y }]));
    nodesRef.current = next;
    setNodes(next);
    persistLayout(next);
    fitCanvasView(220);
  }, [canvas, fitCanvasView, persistLayout, setNodes]);

  const onSavedClip = useCallback((saved: ClipEditData) => {
    setNodes((current) => current.map((node) => {
      const frameMatch = /^frame:(.+):\d+$/.exec(node.id);
      const baseId = frameMatch?.[1] ?? node.id.replace(/^shot:|^video:/, "");
      if (baseId !== editing?.id) return node;
      const data = node.data as unknown as EditableCanvasClip;
      const nextPrompt = editablePrompt(saved) || data.prompt;
      return {
        ...node,
        data: {
          ...data,
          label: saved.label,
          duration: saved.duration ?? undefined,
          scene: saved.scene,
          rhythm: saved.rhythm,
          template: saved.template,
          prompt: nextPrompt,
          promptTooltip: nextPrompt,
          onEdit: data.onEdit,
        } as unknown as Record<string, unknown>,
      };
    }));
  }, [editing?.id, setNodes]);

  if (!canvas || canvas.clips.length === 0) {
    return <div className="stub-view">{t("canvas.noStoryboard")}</div>;
  }

  return (
    <div className="canvas-wrap" ref={wrapRef}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onMoveStart={() => wrapRef.current?.classList.add("is-interacting")}
        onMoveEnd={() => wrapRef.current?.classList.remove("is-interacting")}
        onNodeDragStart={() => wrapRef.current?.classList.add("is-interacting")}
        onNodeDragStop={(_, node) => {
          wrapRef.current?.classList.remove("is-interacting");
          saveCurrentLayout(node);
        }}
        nodesDraggable
        nodesConnectable={false}
        nodesFocusable={false}
        edgesFocusable={false}
        elevateNodesOnSelect={false}
        onInit={(instance) => {
          flowRef.current = instance;
          if (pendingFitRef.current) fitCanvasView(0);
        }}
        minZoom={0.1}
        maxZoom={8}
        onlyRenderVisibleElements
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={32} size={1.7} color="rgba(96, 101, 108, .72)" />
        {miniMapOpen && (
          <MiniMap
            position="bottom-left"
            className="canvas-minimap"
            pannable
            zoomable
            maskColor="rgba(11,14,20,.7)"
            nodeColor={(node) => {
              if (node.id.startsWith("asset:")) return "transparent";
              if (node.id.startsWith("video:")) return "#6b6b6b";
              if (node.id.startsWith("frame:") || node.id.startsWith("shot:")) return "#575757";
              return "#505050";
            }}
          />
        )}
        <CanvasControlDock
          miniMapOpen={miniMapOpen}
          onToggleMiniMap={() => setMiniMapOpen((value) => !value)}
          onResetLayout={resetLayout}
        />
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
