import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type CSSProperties,
  type ReactNode,
} from "react";
import {
  ArrowUp,
  Box,
  Camera,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  Crosshair,
  Eye,
  EyeOff,
  Film,
  History,
  Image as ImageIcon,
  Layers3,
  Lock,
  Maximize2,
  MousePointer2,
  Move3d,
  PanelLeftClose,
  PanelLeftOpen,
  Pause,
  Play,
  Plus,
  Ratio,
  Rotate3d,
  RotateCcw,
  ScanLine,
  Search,
  Send,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  Unlock,
  Upload,
  UserRound,
  X,
} from "lucide-react";
import {
  DIRECTOR_ACTOR_PRESETS,
  DIRECTOR_CAMERA_PRESETS,
  DIRECTOR_POSE_PRESETS,
  DIRECTOR_POSE_SECTIONS,
  buildDirectorSceneFromPrompt,
  cameraPresetValues,
  createDefaultDirectorScene,
  createDirectorActor,
  createDirectorCamera,
} from "./defaults";
import { DirectorViewport } from "./DirectorViewport";
import type {
  DirectorActor,
  DirectorAspectRatio,
  DirectorCamera,
  DirectorObject,
  DirectorPanel,
  DirectorPoseKey,
  DirectorSceneState,
  DirectorShot,
  DirectorTimelineState,
  DirectorVector3,
  DirectorViewportHandle,
} from "./types";
import "./director.css";

type DirectorStudioProps = {
  nodeTitle: string;
  initialPrompt?: string;
  initialReferenceOpen?: boolean;
  initialRunPrompt?: boolean;
  imageAssets: Array<{ id: string; name: string }>;
  value: DirectorSceneState;
  onChange: (next: DirectorSceneState) => void;
  persistScene?: (next: DirectorSceneState) => Promise<void>;
  onPromptChange?: (prompt: string) => void;
  onClose: (current: DirectorSceneState) => void;
  registerFile: (file: File) => Promise<string>;
  resolveAttachment: (attachmentId: string) => Promise<File | undefined>;
  sendShotToCanvas: (shot: DirectorShot, camera: DirectorCamera) => void;
  buildScene?: (prompt: string, current: DirectorSceneState, signal: AbortSignal) => Promise<DirectorSceneState>;
  generatePanorama?: (prompt: string, signal: AbortSignal) => Promise<string>;
  analyzeReference?: (file: File, current: DirectorSceneState, signal: AbortSignal) => Promise<DirectorSceneState>;
  notify: (message: string) => void;
};

const ASPECT_RATIOS: DirectorAspectRatio[] = ["adaptive", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"];
const TOOL_BUTTONS: Array<{ id: DirectorSceneState["tool"]; label: string; icon: ReactNode }> = [
  { id: "translate", label: "移动", icon: <Move3d size={18} /> },
  { id: "rotate", label: "旋转", icon: <Rotate3d size={18} /> },
  { id: "scale", label: "缩放", icon: <SlidersHorizontal size={18} /> },
];

function cloneScene(value: DirectorSceneState): DirectorSceneState {
  return typeof structuredClone === "function" ? structuredClone(value) : JSON.parse(JSON.stringify(value)) as DirectorSceneState;
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, Number.isFinite(value) ? value : min));
}

const DIRECTOR_IMAGE_TYPES = new Set(["image/png", "image/jpeg", "image/webp"]);
const MAX_DIRECTOR_IMAGE_BYTES = 12 * 1024 * 1024;
const MAX_DIRECTOR_SOURCE_PIXELS = 64 * 1024 * 1024;
const MAX_REFERENCE_IMAGE_EDGE = 4096;
const MAX_REFERENCE_IMAGE_PIXELS = 16 * 1024 * 1024;

type BrowserImageDecoder = {
  tracks: {
    ready: Promise<void>;
    selectedTrack?: { codedWidth: number; codedHeight: number } | null;
  };
  close: () => void;
};

async function imageDimensions(file: File): Promise<{ width: number; height: number }> {
  const Decoder = (globalThis as unknown as {
    ImageDecoder?: new (init: { data: ReadableStream<Uint8Array>; type: string }) => BrowserImageDecoder;
  }).ImageDecoder;
  if (Decoder) {
    const decoder = new Decoder({ data: file.stream(), type: file.type });
    try {
      await decoder.tracks.ready;
      const track = decoder.tracks.selectedTrack;
      if (track?.codedWidth && track.codedHeight) return { width: track.codedWidth, height: track.codedHeight };
    } finally {
      decoder.close();
    }
  }
  const bitmap = await createImageBitmap(file);
  try {
    return { width: bitmap.width, height: bitmap.height };
  } finally {
    bitmap.close();
  }
}

async function canvasBlob(canvas: HTMLCanvasElement, type: string, quality?: number): Promise<Blob> {
  return new Promise((resolve, reject) => canvas.toBlob(
    (blob) => blob ? resolve(blob) : reject(new Error("图片处理失败")),
    type,
    quality,
  ));
}

async function prepareDirectorImage(file: File, mode: "panorama" | "reference"): Promise<File> {
  if (!DIRECTOR_IMAGE_TYPES.has(file.type)) throw new Error("仅支持 PNG、JPG、WEBP 图片");
  if (!file.size || file.size > MAX_DIRECTOR_IMAGE_BYTES) throw new Error("图片不能超过 12MB");
  const { width, height } = await imageDimensions(file);
  if (!width || !height || width * height > MAX_DIRECTOR_SOURCE_PIXELS) throw new Error("图片像素过大，请使用不超过 6400 万像素的图片");

  let bitmap: ImageBitmap;
  let targetWidth: number;
  let targetHeight: number;
  if (mode === "panorama") {
    if (Math.abs(width / height - 2) < .005 && width <= 2048 && height <= 1024) return file;
    targetWidth = 2048;
    targetHeight = 1024;
    const sourceRatio = width / height;
    const cropWidth = sourceRatio > 2 ? height * 2 : width;
    const cropHeight = sourceRatio < 2 ? width / 2 : height;
    bitmap = await createImageBitmap(
      file,
      Math.max(0, Math.round((width - cropWidth) / 2)),
      Math.max(0, Math.round((height - cropHeight) / 2)),
      Math.max(1, Math.round(cropWidth)),
      Math.max(1, Math.round(cropHeight)),
      { resizeWidth: targetWidth, resizeHeight: targetHeight, resizeQuality: "high" },
    );
  } else {
    const scale = Math.min(
      1,
      MAX_REFERENCE_IMAGE_EDGE / Math.max(width, height),
      Math.sqrt(MAX_REFERENCE_IMAGE_PIXELS / (width * height)),
    );
    if (scale >= 1) return file;
    targetWidth = Math.max(1, Math.round(width * scale));
    targetHeight = Math.max(1, Math.round(height * scale));
    bitmap = await createImageBitmap(file, { resizeWidth: targetWidth, resizeHeight: targetHeight, resizeQuality: "high" });
  }

  try {
    const outputType = mode === "panorama" ? "image/jpeg" : "image/webp";
    let outputWidth = targetWidth;
    let outputHeight = targetHeight;
    let blob: Blob | null = null;
    for (let attempt = 0; attempt < 4; attempt += 1) {
      const canvas = document.createElement("canvas");
      canvas.width = outputWidth;
      canvas.height = outputHeight;
      const context = canvas.getContext("2d");
      if (!context) throw new Error("浏览器无法处理这张图片");
      context.drawImage(bitmap, 0, 0, bitmap.width, bitmap.height, 0, 0, outputWidth, outputHeight);
      blob = await canvasBlob(canvas, outputType, Math.max(.72, .92 - attempt * .06));
      if (blob.size <= MAX_DIRECTOR_IMAGE_BYTES) break;
      outputWidth = Math.max(640, Math.round(outputWidth * .78));
      outputHeight = Math.max(360, Math.round(outputHeight * .78));
    }
    if (!blob || blob.size > MAX_DIRECTOR_IMAGE_BYTES) throw new Error("图片优化后仍超过 12MB，请换一张图片");
    const baseName = file.name.replace(/\.[^.]+$/, "").slice(0, 80) || (mode === "panorama" ? "全景图" : "参考图");
    return new File([blob], `${baseName}-${mode === "panorama" ? "2to1" : "optimized"}.${outputType === "image/jpeg" ? "jpg" : "webp"}`, {
      type: outputType,
      lastModified: Date.now(),
    });
  } finally {
    bitmap.close();
  }
}

function keyframeFromObject(object: DirectorObject, time: number): DirectorTimelineState["tracks"][number]["keyframes"][number] {
  return {
    id: `keyframe-${crypto.randomUUID()}`,
    time,
    position: [...object.position] as DirectorVector3,
    rotation: [...object.rotation] as DirectorVector3,
    scale: [...object.scale] as DirectorVector3,
  };
}

function interpolateVector(left: DirectorVector3, right: DirectorVector3, amount: number): DirectorVector3 {
  return left.map((entry, index) => Number((entry + (right[index] - entry) * amount).toFixed(3))) as DirectorVector3;
}

function sceneAtTimelineHead(value: DirectorSceneState, head: number): DirectorSceneState {
  if (!value.timeline.tracks.length) return value;
  const tracks = new Map(value.timeline.tracks.map((track) => [track.objectId, track]));
  return {
    ...value,
    objects: value.objects.map((object) => {
      const frames = tracks.get(object.id)?.keyframes;
      if (!frames?.length) return object;
      const rightIndex = frames.findIndex((frame) => frame.time >= head);
      const right = rightIndex < 0 ? frames[frames.length - 1] : frames[rightIndex];
      const left = rightIndex <= 0 ? frames[0] : frames[rightIndex - 1];
      if (!left || !right) return object;
      const span = Math.max(.0001, right.time - left.time);
      const amount = left === right ? 0 : clamp((head - left.time) / span, 0, 1);
      return {
        ...object,
        position: interpolateVector(left.position, right.position, amount),
        rotation: interpolateVector(left.rotation, right.rotation, amount),
        scale: interpolateVector(left.scale, right.scale, amount),
      } as DirectorObject;
    }),
  };
}

function sceneStructureSignature(value: DirectorSceneState) {
  const {
    panoramaAttachmentId: _panoramaAttachmentId,
    panoramaRotation: _panoramaRotation,
    panoramaRadius: _panoramaRadius,
    ...scene
  } = value.scene;
  return JSON.stringify({
    schema: value.schema,
    aspectRatio: value.aspectRatio,
    activeCameraId: value.activeCameraId,
    objects: value.objects,
    scene,
    timeline: {
      duration: value.timeline.duration,
      loop: value.timeline.loop,
      autoFrame: value.timeline.autoFrame,
      tracks: value.timeline.tracks,
    },
  });
}

function withLatestPanorama(next: DirectorSceneState, latest: DirectorSceneState): DirectorSceneState {
  const selectedObjectId = latest.selectedObjectId && next.objects.some((object) => object.id === latest.selectedObjectId)
    ? latest.selectedObjectId
    : next.selectedObjectId;
  return {
    ...next,
    panel: latest.panel,
    tool: latest.tool,
    viewMode: latest.viewMode,
    compositionGuide: next.aspectRatio === "adaptive" ? false : latest.compositionGuide,
    selectedObjectId,
    scene: {
      ...next.scene,
      panoramaAttachmentId: latest.scene.panoramaAttachmentId,
      panoramaRotation: latest.scene.panoramaRotation,
      panoramaRadius: latest.scene.panoramaRadius,
    },
    timeline: {
      ...next.timeline,
      head: Math.min(latest.timeline.head, next.timeline.duration),
    },
  };
}

function titleForObject(object: DirectorObject) {
  return object.kind === "camera" ? "摄像机" : object.kind === "actor" ? "角色" : "道具";
}

function objectIcon(object: DirectorObject) {
  return object.kind === "camera" ? <Camera size={13} /> : object.kind === "actor" ? <UserRound size={13} /> : <Box size={13} />;
}

function AttachmentImage({ attachmentId, alt, resolveAttachment, onClick }: {
  attachmentId: string;
  alt: string;
  resolveAttachment: DirectorStudioProps["resolveAttachment"];
  onClick?: () => void;
}) {
  const [url, setUrl] = useState("");
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let disposed = false;
    let objectUrl = "";
    setUrl("");
    setFailed(false);
    void resolveAttachment(attachmentId).then((file) => {
      if (disposed) return;
      if (!file) { setFailed(true); return; }
      objectUrl = URL.createObjectURL(file);
      setUrl(objectUrl);
    }).catch(() => { if (!disposed) setFailed(true); });
    return () => {
      disposed = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [attachmentId, resolveAttachment]);
  if (failed) return <span className="director-attachment-loading is-error"><ImageIcon size={17} /><small>图片不可用</small></span>;
  if (!url) return <span className="director-attachment-loading"><ImageIcon size={17} /></span>;
  return <img src={url} alt={alt} onClick={onClick} />;
}

function NumberDraftInput({ value, min, max, suffix = "", ariaLabel, onCommit }: {
  value: number;
  min: number;
  max: number;
  suffix?: string;
  ariaLabel: string;
  onCommit: (value: number) => void;
}) {
  const formatted = `${value}${suffix}`;
  const [draft, setDraft] = useState(formatted);
  useEffect(() => setDraft(formatted), [formatted]);
  const commitDraft = () => {
    const number = Number(draft.replace(suffix, "").trim());
    if (Number.isFinite(number)) onCommit(clamp(number, min, max));
    else setDraft(formatted);
  };
  return <input type="text" inputMode="decimal" aria-label={ariaLabel} value={draft} onChange={(event) => setDraft(event.target.value)} onBlur={commitDraft} onKeyDown={(event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      event.currentTarget.blur();
    } else if (event.key === "Escape") {
      setDraft(formatted);
    }
  }} />;
}

function VectorFields({ label, value, onChange, min = -999, max = 999 }: {
  label: string;
  value: DirectorVector3;
  onChange: (value: DirectorVector3) => void;
  min?: number;
  max?: number;
}) {
  return <div className="director-inspector-group">
    <span>{label}</span>
    <div className="director-vector-fields">
      {(["X", "Y", "Z"] as const).map((axis, index) => <label key={axis}><i>{axis}</i><NumberDraftInput ariaLabel={`${label} ${axis}`} min={min} max={max} value={value[index]} onCommit={(number) => {
        const next = [...value] as DirectorVector3;
        next[index] = number;
        onChange(next);
      }} /></label>)}
    </div>
  </div>;
}

function RangeField({ label, value, min, max, step = 1, suffix = "", onChange }: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  suffix?: string;
  onChange: (value: number) => void;
}) {
  return <div className="director-range-field"><span>{label}</span><div><input aria-label={`${label}滑杆`} type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} /><NumberDraftInput ariaLabel={label} value={value} min={min} max={max} suffix={suffix} onCommit={onChange} /></div></div>;
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return <button type="button" role="switch" aria-checked={checked} className={`director-toggle${checked ? " is-on" : ""}`} onClick={() => onChange(!checked)}><span>{label}</span><i /></button>;
}

function HexColorField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const [draft, setDraft] = useState(value.toUpperCase());
  useEffect(() => setDraft(value.toUpperCase()), [value]);
  const commitDraft = () => {
    if (/^#[0-9A-Fa-f]{6}$/.test(draft)) onChange(draft.toUpperCase());
    else setDraft(value.toUpperCase());
  };
  return <div className="director-color-field"><span>{label}</span><div><input aria-label={`${label}取色器`} type="color" value={value} onChange={(event) => { const next = event.target.value.toUpperCase(); setDraft(next); onChange(next); }} /><input aria-label={`${label}十六进制值`} type="text" value={draft} maxLength={7} onChange={(event) => setDraft(event.target.value)} onBlur={commitDraft} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); event.currentTarget.blur(); } else if (event.key === "Escape") { setDraft(value.toUpperCase()); } }} /></div></div>;
}

export default function DirectorStudio({
  nodeTitle,
  initialPrompt = "",
  initialReferenceOpen = false,
  initialRunPrompt = false,
  imageAssets,
  value,
  onChange,
  persistScene,
  onPromptChange,
  onClose,
  registerFile,
  resolveAttachment,
  sendShotToCanvas,
  buildScene,
  generatePanorama,
  analyzeReference,
  notify,
}: DirectorStudioProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);
  const viewportRef = useRef<DirectorViewportHandle>(null);
  const promptRunningRef = useRef(false);
  const promptAbortRef = useRef<AbortController | null>(null);
  const captureRunningRef = useRef(false);
  const captureOperationRef = useRef(0);
  const panoramaRunningRef = useRef(false);
  const panoramaAbortRef = useRef<AbortController | null>(null);
  const panoramaOperationRef = useRef(0);
  const referenceRunningRef = useRef(false);
  const referenceAbortRef = useRef<AbortController | null>(null);
  const referencePrepareOperationRef = useRef(0);
  const initialPromptStartedRef = useRef(false);
  const mountedRef = useRef(true);
  const panoramaInputRef = useRef<HTMLInputElement>(null);
  const referenceInputRef = useRef<HTMLInputElement>(null);
  const valueRef = useRef(value);
  valueRef.current = value;
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [sceneQuery, setSceneQuery] = useState("");
  const [actorInspectorTab, setActorInspectorTab] = useState<"properties" | "pose">("properties");
  const [prompt, setPrompt] = useState(initialPrompt);
  const [promptRunning, setPromptRunning] = useState(false);
  const [captureRunning, setCaptureRunning] = useState(false);
  const [panoramaRunning, setPanoramaRunning] = useState(false);
  const [webglError, setWebglError] = useState("");
  const [helpMenuOpen, setHelpMenuOpen] = useState(false);
  const [transformMenuOpen, setTransformMenuOpen] = useState(false);
  const [shortcutOpen, setShortcutOpen] = useState(false);
  const [tutorialOpen, setTutorialOpen] = useState(false);
  const [referenceImportOpen, setReferenceImportOpen] = useState(initialReferenceOpen);
  const [referenceMode, setReferenceMode] = useState<"insert" | "replace">("insert");
  const [referenceAttachmentId, setReferenceAttachmentId] = useState<string | null>(null);
  const [referenceTab, setReferenceTab] = useState<"upload" | "history">("upload");
  const [referenceRunning, setReferenceRunning] = useState(false);
  const [referencePreparing, setReferencePreparing] = useState(false);
  const [referenceUrls, setReferenceUrls] = useState<Record<string, string>>({});
  const [previewShot, setPreviewShot] = useState<DirectorShot | null>(null);
  const [timelineOpen, setTimelineOpen] = useState(false);
  const [timelinePlaying, setTimelinePlaying] = useState(false);
  const [timelineHead, setTimelineHead] = useState(value.timeline.head);
  const timelineHeadRef = useRef(value.timeline.head);
  timelineHeadRef.current = timelineHead;
  const [panoramaUrl, setPanoramaUrl] = useState("");
  const [panoramaMode, setPanoramaMode] = useState<"upload" | "history" | "ai">("upload");
  const [panoramaPrompt, setPanoramaPrompt] = useState("");

  const selectedObject = useMemo(() => value.objects.find((object) => object.id === value.selectedObjectId) ?? null, [value.objects, value.selectedObjectId]);
  const activeCamera = useMemo(() => value.objects.find((object): object is DirectorCamera => object.kind === "camera" && object.id === value.activeCameraId) ?? null, [value.activeCameraId, value.objects]);
  const actors = useMemo(() => value.objects.filter((object): object is DirectorActor => object.kind === "actor"), [value.objects]);
  const cameras = useMemo(() => value.objects.filter((object): object is DirectorCamera => object.kind === "camera"), [value.objects]);
  const allShots = useMemo(() => cameras.flatMap((camera) => camera.shots), [cameras]);
  const imageHistory = useMemo(() => {
    const entries = [...imageAssets, ...allShots.map((shot) => ({ id: shot.attachmentId, name: shot.name }))];
    return entries.filter((entry, index) => entries.findIndex((candidate) => candidate.id === entry.id) === index);
  }, [allShots, imageAssets]);
  const referenceEntries = useMemo(() => value.objects.flatMap((object) => object.kind === "prop" && object.referenceAttachmentId
    ? [{ objectId: object.id, attachmentId: object.referenceAttachmentId }]
    : []), [value.objects]);
  const referenceSignature = referenceEntries.map((entry) => `${entry.objectId}:${entry.attachmentId}`).sort().join("|");
  const timelineDuration = value.timeline.duration;
  const timelineLoop = value.timeline.loop;
  const timelineAutoFrame = value.timeline.autoFrame;
  const timelineTracks = value.timeline.tracks;
  const viewportValue = useMemo(() => timelineOpen || timelinePlaying ? sceneAtTimelineHead(value, timelineHead) : value, [timelineHead, timelineOpen, timelinePlaying, value]);
  const timelineSelectedObject = useMemo(() => selectedObject
    ? viewportValue.objects.find((object) => object.id === selectedObject.id) ?? selectedObject
    : null, [selectedObject, viewportValue.objects]);

  const commit = useCallback((next: DirectorSceneState) => {
    valueRef.current = next;
    onChange(next);
  }, [onChange]);
  const patchScene = useCallback((patch: Partial<DirectorSceneState>) => commit({ ...valueRef.current, ...patch }), [commit]);
  const patchSceneSettings = useCallback((patch: Partial<DirectorSceneState["scene"]>) => commit({ ...valueRef.current, scene: { ...valueRef.current.scene, ...patch } }), [commit]);
  const patchTimeline = useCallback((patch: Partial<DirectorSceneState["timeline"]>) => commit({ ...valueRef.current, timeline: { ...valueRef.current.timeline, ...patch } }), [commit]);
  const showDirectorAxis = useCallback((view: "front" | "top" | "right") => {
    if (valueRef.current.viewMode !== "director") patchScene({ viewMode: "director" });
    viewportRef.current?.setAxisView(view);
  }, [patchScene]);
  const resetDirectorView = useCallback(() => {
    if (valueRef.current.viewMode !== "director") patchScene({ viewMode: "director" });
    viewportRef.current?.resetView();
  }, [patchScene]);
  const patchObject = useCallback((objectId: string, patch: Partial<DirectorObject>) => {
    const current = valueRef.current;
    const objects = current.objects.map((object) => object.id === objectId ? { ...object, ...patch } as DirectorObject : object);
    const changedObject = objects.find((object) => object.id === objectId);
    let timeline = current.timeline;
    if (changedObject && timeline.autoFrame) {
      const trackIndex = timeline.tracks.findIndex((track) => track.objectId === objectId);
      if (trackIndex >= 0) {
        const frame = keyframeFromObject(changedObject, timelineHead);
        const tracks = timeline.tracks.map((track, index) => {
          if (index !== trackIndex) return track;
          const keyframes = [...track.keyframes.filter((item) => Math.abs(item.time - timelineHead) > .005), frame].sort((left, right) => left.time - right.time);
          return { ...track, keyframes };
        });
        timeline = { ...timeline, head: timelineHead, tracks };
      }
    }
    commit({ ...current, objects, timeline });
  }, [commit, timelineHead]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      captureOperationRef.current += 1;
      panoramaOperationRef.current += 1;
      referencePrepareOperationRef.current += 1;
      promptAbortRef.current?.abort();
      panoramaAbortRef.current?.abort();
      referenceAbortRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    let disposed = false;
    let objectUrl = "";
    const attachmentId = value.scene.panoramaAttachmentId;
    setPanoramaUrl("");
    if (!attachmentId) return;
    void resolveAttachment(attachmentId).then((file) => {
      if (!file || disposed) return;
      objectUrl = URL.createObjectURL(file);
      setPanoramaUrl(objectUrl);
    }).catch(() => { if (!disposed) notify("全景图素材暂时不可用"); });
    return () => {
      disposed = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [notify, resolveAttachment, value.scene.panoramaAttachmentId]);

  useEffect(() => {
    let disposed = false;
    const objectUrls: string[] = [];
    if (!referenceEntries.length) {
      setReferenceUrls({});
      return;
    }
    void Promise.all(referenceEntries.map(async (entry) => {
      try {
        const file = await resolveAttachment(entry.attachmentId);
        if (!file || disposed) return null;
        const url = URL.createObjectURL(file);
        objectUrls.push(url);
        return [entry.objectId, url] as const;
      } catch {
        return null;
      }
    })).then((entries) => {
      if (!disposed) setReferenceUrls(Object.fromEntries(entries.filter((entry): entry is readonly [string, string] => Boolean(entry))));
    });
    return () => {
      disposed = true;
      objectUrls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [referenceSignature, resolveAttachment]);

  useEffect(() => {
    if (!timelinePlaying) setTimelineHead(value.timeline.head);
  }, [timelinePlaying, value.timeline.head]);

  useEffect(() => {
    if (!timelinePlaying) return;
    let last = performance.now();
    const id = window.setInterval(() => {
      const now = performance.now();
      const delta = (now - last) / 1000;
      last = now;
      const next = timelineHeadRef.current + delta;
      if (next < timelineDuration) {
        timelineHeadRef.current = next;
        setTimelineHead(next);
        return;
      }
      if (timelineLoop) {
        timelineHeadRef.current = 0;
        setTimelineHead(0);
        return;
      }
      timelineHeadRef.current = timelineDuration;
      setTimelineHead(timelineDuration);
      setTimelinePlaying(false);
      patchTimeline({ head: timelineDuration });
    }, 33);
    return () => window.clearInterval(id);
  }, [patchTimeline, timelineDuration, timelineLoop, timelinePlaying]);

  const deleteSelectedObject = useCallback(() => {
    const current = valueRef.current;
    const selected = current.objects.find((object) => object.id === current.selectedObjectId);
    if (!selected) return;
    if (selected.kind === "camera" && current.objects.filter((object) => object.kind === "camera").length === 1) {
      notify("至少保留一个机位");
      return;
    }
    const objects = current.objects.filter((object) => object.id !== selected.id);
    const nextCamera = objects.find((object) => object.kind === "camera");
    const cleanedObjects = objects.map((object) => {
      if (object.kind !== "camera") return object;
      const releasedPosition = object.followTargetId === selected.id && object.followOffset
        ? selected.position.map((entry, index) => Number((entry + object.followOffset![index]).toFixed(2))) as DirectorVector3
        : object.position;
      return {
        ...object,
        position: releasedPosition,
        followTargetId: object.followTargetId === selected.id ? null : object.followTargetId,
        followOffset: object.followTargetId === selected.id ? null : object.followOffset,
        lookAtTargetId: object.lookAtTargetId === selected.id ? null : object.lookAtTargetId,
        lookAtMode: object.lookAtTargetId === selected.id ? "rotation" as const : object.lookAtMode,
      };
    });
    commit({
      ...current,
      objects: cleanedObjects,
      timeline: { ...current.timeline, tracks: current.timeline.tracks.filter((track) => track.objectId !== selected.id) },
      selectedObjectId: cleanedObjects.find((object) => object.kind === "actor")?.id ?? nextCamera?.id ?? null,
      activeCameraId: selected.id === current.activeCameraId ? nextCamera?.id ?? null : current.activeCameraId,
      viewMode: selected.id === current.activeCameraId ? "director" : current.viewMode,
    });
  }, [commit, notify]);

  function closeReferenceDialog() {
    referenceAbortRef.current?.abort();
    referencePrepareOperationRef.current += 1;
    setReferencePreparing(false);
    setReferenceImportOpen(false);
  }

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.matches("input, textarea, select, [contenteditable='true']")) return;
      const key = event.key.toLowerCase();
      if (event.key === "Escape") {
        if (transformMenuOpen) setTransformMenuOpen(false);
        else if (helpMenuOpen) setHelpMenuOpen(false);
        else if (previewShot) setPreviewShot(null);
        else if (referenceImportOpen) closeReferenceDialog();
        else if (shortcutOpen) setShortcutOpen(false);
        else if (tutorialOpen) setTutorialOpen(false);
        else if (timelineOpen) closeTimeline();
        else onClose(valueRef.current);
      } else if (previewShot || referenceImportOpen || shortcutOpen || tutorialOpen) {
        return;
      } else if (event.key === "Backspace" || event.key === "Delete") {
        event.preventDefault();
        deleteSelectedObject();
      } else if (key === "v") patchScene({ tool: "translate" });
      else if (key === "r") patchScene({ tool: "rotate" });
      else if (key === "f") patchScene({ tool: "scale" });
      else if (key === "t") showDirectorAxis("top");
      else if (key === "y") showDirectorAxis("front");
      else if (key === "h") resetDirectorView();
      else if (key === "x") patchSceneSettings({ gridSnap: !valueRef.current.scene.gridSnap });
      else if (key === "c") void captureCurrentView();
      else if (key === "1") patchScene({ viewMode: "director" });
      else if (key === "2") patchScene({ viewMode: "camera" });
    };
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  });

  useEffect(() => {
    restoreFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const focusRoot = () => {
      const root = rootRef.current;
      if (!root) return;
      const nestedDialog = root.querySelector<HTMLElement>(".director-dialog-backdrop [role='dialog'], .director-shot-preview[role='dialog']");
      const scope = nestedDialog ?? root;
      scope.querySelector<HTMLElement>("button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex='0']")?.focus();
    };
    const timer = window.setTimeout(focusRoot, 0);
    const trapFocus = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;
      const root = rootRef.current;
      if (!root) return;
      const nestedDialog = root.querySelector<HTMLElement>(".director-dialog-backdrop [role='dialog'], .director-shot-preview[role='dialog']");
      const scope = nestedDialog ?? root;
      const focusable = [...scope.querySelectorAll<HTMLElement>("button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex='0']")].filter((item) => item.offsetParent !== null);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || !scope.contains(document.activeElement))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !scope.contains(document.activeElement))) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", trapFocus, true);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("keydown", trapFocus, true);
      restoreFocusRef.current?.focus();
    };
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const root = rootRef.current;
      if (!root) return;
      const nestedDialog = root.querySelector<HTMLElement>(".director-dialog-backdrop [role='dialog'], .director-shot-preview[role='dialog']");
      const scope = nestedDialog ?? root;
      if (nestedDialog || !scope.contains(document.activeElement)) scope.querySelector<HTMLElement>("button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex='0']")?.focus();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [previewShot, referenceImportOpen, shortcutOpen, tutorialOpen]);

  async function importPanorama(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const operation = ++panoramaOperationRef.current;
    panoramaAbortRef.current?.abort();
    try {
      const attachmentId = await registerFile(await prepareDirectorImage(file, "panorama"));
      if (operation !== panoramaOperationRef.current) return;
      const current = valueRef.current;
      const next = { ...current, scene: { ...current.scene, panoramaAttachmentId: attachmentId } };
      commit(next);
      await persistScene?.(next);
      notify("全景图已导入导演台");
    } catch (error) {
      notify(error instanceof Error ? error.message : "全景图导入失败");
    }
  }

  async function importReference(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) await registerReferenceFile(file);
  }

  async function applyPanoramaHistory(attachmentId: string) {
    const operation = ++panoramaOperationRef.current;
    panoramaAbortRef.current?.abort();
    try {
      const source = await resolveAttachment(attachmentId);
      if (!source) throw new Error("历史图片暂时不可用");
      const prepared = await prepareDirectorImage(source, "panorama");
      const safeAttachmentId = prepared === source ? attachmentId : await registerFile(prepared);
      if (operation !== panoramaOperationRef.current) return;
      const current = valueRef.current;
      const next = { ...current, scene: { ...current.scene, panoramaAttachmentId: safeAttachmentId } };
      commit(next);
      await persistScene?.(next);
      notify("历史图片已按 2:1 安全尺寸应用");
    } catch (error) {
      notify(error instanceof Error ? error.message : "历史图片应用失败");
    }
  }

  async function registerReferenceFile(file: File) {
    const operation = ++referencePrepareOperationRef.current;
    setReferencePreparing(true);
    setReferenceAttachmentId(null);
    try {
      const attachmentId = await registerFile(await prepareDirectorImage(file, "reference"));
      if (operation === referencePrepareOperationRef.current) setReferenceAttachmentId(attachmentId);
    } catch (error) {
      if (operation === referencePrepareOperationRef.current) notify(error instanceof Error ? error.message : "参考图导入失败");
    } finally {
      if (operation === referencePrepareOperationRef.current && mountedRef.current) setReferencePreparing(false);
    }
  }

  function selectReferenceHistory(attachmentId: string) {
    referencePrepareOperationRef.current += 1;
    setReferencePreparing(false);
    setReferenceAttachmentId(attachmentId);
  }

  async function runPrompt(textOverride?: string) {
    const text = (textOverride ?? prompt).trim();
    if (!text || promptRunningRef.current) return;
    if (referenceRunningRef.current) {
      notify("参考图正在识别，请稍后再搭建场景");
      return;
    }
    promptRunningRef.current = true;
    setPromptRunning(true);
    const controller = new AbortController();
    promptAbortRef.current = controller;
    const startingScene = valueRef.current;
    const startingSignature = sceneStructureSignature(startingScene);
    try {
      const next = buildScene ? await buildScene(text, startingScene, controller.signal) : buildDirectorSceneFromPrompt(text, startingScene);
      if (controller.signal.aborted) return;
      const latestScene = valueRef.current;
      if (sceneStructureSignature(latestScene) !== startingSignature) {
        notify("场景已在生成期间发生变化，本次结果未覆盖当前编辑");
        return;
      }
      const merged = withLatestPanorama(next, latestScene);
      commit(merged);
      await persistScene?.(merged);
      setPrompt(text);
      onPromptChange?.(text);
      notify("场景描述已应用");
    } catch (error) {
      if (!controller.signal.aborted) notify(error instanceof Error ? error.message : "场景搭建失败，请重试");
    } finally {
      promptRunningRef.current = false;
      if (promptAbortRef.current === controller) promptAbortRef.current = null;
      if (mountedRef.current) setPromptRunning(false);
    }
  }

  useEffect(() => {
    if (!initialRunPrompt || initialPromptStartedRef.current || !initialPrompt.trim()) return;
    const timer = window.setTimeout(() => {
      if (initialPromptStartedRef.current) return;
      initialPromptStartedRef.current = true;
      void runPrompt(initialPrompt);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [initialPrompt, initialRunPrompt]);

  async function generateAiPanorama() {
    const text = panoramaPrompt.trim();
    if (!text || !generatePanorama || panoramaRunningRef.current) return;
    const operation = ++panoramaOperationRef.current;
    panoramaAbortRef.current?.abort();
    panoramaRunningRef.current = true;
    setPanoramaRunning(true);
    const controller = new AbortController();
    panoramaAbortRef.current = controller;
    const startingPanoramaId = valueRef.current.scene.panoramaAttachmentId;
    try {
      const attachmentId = await generatePanorama(text, controller.signal);
      if (controller.signal.aborted) return;
      if (operation !== panoramaOperationRef.current) return;
      if (valueRef.current.scene.panoramaAttachmentId !== startingPanoramaId) {
        notify("全景图已生成并保留在历史中；当前场景已使用你后来选择的图片");
        return;
      }
      const current = valueRef.current;
      const next = { ...current, scene: { ...current.scene, panoramaAttachmentId: attachmentId } };
      commit(next);
      await persistScene?.(next);
      notify("AI 全景图已生成并应用到导演台");
    } catch (error) {
      if (!controller.signal.aborted) notify(error instanceof Error ? error.message : "AI 全景图生成失败");
    } finally {
      if (panoramaAbortRef.current === controller) {
        panoramaRunningRef.current = false;
        panoramaAbortRef.current = null;
        if (mountedRef.current) setPanoramaRunning(false);
      }
    }
  }

  async function captureCurrentView(cameraIdOverride?: string) {
    if (!viewportRef.current || captureRunningRef.current) return;
    const operation = ++captureOperationRef.current;
    captureRunningRef.current = true;
    setCaptureRunning(true);
    try {
      const sceneAtCapture = valueRef.current;
      const targetCameraId = cameraIdOverride ?? (sceneAtCapture.viewMode === "camera" ? sceneAtCapture.activeCameraId : null);
      const capture = await viewportRef.current.capture(sceneAtCapture.aspectRatio, targetCameraId ?? undefined);
      if (!mountedRef.current || operation !== captureOperationRef.current) return;
      const initialCamera = sceneAtCapture.objects.find((object): object is DirectorCamera => object.kind === "camera" && object.id === targetCameraId) ?? null;
      const previousShots = initialCamera?.shots ?? [];
      const shotIndex = Math.max(0, ...previousShots.map((shot) => Number(shot.name.match(/-(\d+)$/)?.[1] ?? 0))) + 1;
      const cameraName = initialCamera?.name ?? "当前视角";
      const shotName = `${cameraName}-shot-${String(shotIndex).padStart(2, "0")}`;
      const file = new File([capture.blob], `${shotName}.png`, { type: "image/png", lastModified: Date.now() });
      const attachmentId = await registerFile(file);
      if (!mountedRef.current || operation !== captureOperationRef.current) return;
      const shot: DirectorShot = {
        id: `shot-${crypto.randomUUID()}`,
        name: shotName,
        attachmentId,
        mimeType: "image/png",
        width: capture.width,
        height: capture.height,
        createdAt: new Date().toISOString(),
      };
      let next = cloneScene(valueRef.current);
      let camera = next.objects.find((object): object is DirectorCamera => object.kind === "camera" && object.id === targetCameraId) ?? null;
      if (!camera) {
        camera = createDirectorCamera(next.objects.filter((object) => object.kind === "camera").length, "当前视角", { position: capture.cameraPosition, rotation: capture.cameraRotation, fov: capture.fov });
        next.objects.push(camera);
        next.activeCameraId = camera.id;
      }
      next.objects = next.objects.map((object) => object.id === camera!.id ? { ...camera!, shots: [...camera!.shots, shot] } : object);
      next.selectedObjectId = camera.id;
      next.panel = "scene";
      commit(next);
      await persistScene?.(next);
      if (mountedRef.current && operation === captureOperationRef.current) notify(`${shotName} 已保存`);
    } catch (error) {
      if (mountedRef.current && operation === captureOperationRef.current) notify(error instanceof Error ? error.message : "截图失败，请重试");
    } finally {
      captureRunningRef.current = false;
      if (mountedRef.current && operation === captureOperationRef.current) setCaptureRunning(false);
    }
  }

  function addActor(archetype: DirectorActor["archetype"]) {
    const current = valueRef.current;
    const actor = createDirectorActor(current.objects.filter((object) => object.kind === "actor").length, archetype);
    commit({ ...current, objects: [...current.objects, actor], selectedObjectId: actor.id });
  }

  function addCamera(preset: string) {
    const current = valueRef.current;
    const currentView = preset === "当前视角" ? viewportRef.current?.getCurrentView() : null;
    const camera = createDirectorCamera(
      current.objects.filter((object) => object.kind === "camera").length,
      preset === "当前视角" ? "正面中景" : preset,
      currentView ? { position: currentView.cameraPosition, rotation: currentView.cameraRotation, fov: currentView.fov } : undefined,
    );
    commit({ ...current, objects: [...current.objects, camera], selectedObjectId: camera.id, activeCameraId: camera.id, viewMode: "director" });
  }

  function deleteShot(cameraId: string, shotId: string) {
    const current = valueRef.current;
    commit({ ...current, objects: current.objects.map((object) => object.id === cameraId && object.kind === "camera" ? { ...object, shots: object.shots.filter((shot) => shot.id !== shotId) } : object) });
    if (previewShot?.id === shotId) setPreviewShot(null);
  }

  function setTimelinePosition(next: number) {
    const head = clamp(next, 0, timelineDuration);
    setTimelineHead(head);
    patchTimeline({ head });
  }

  function toggleTimelinePlayback() {
    if (timelinePlaying) {
      setTimelinePlaying(false);
      patchTimeline({ head: timelineHead });
      return;
    }
    if (timelineHead >= timelineDuration) setTimelinePosition(0);
    setTimelinePlaying(true);
  }

  function closeTimeline() {
    setTimelinePlaying(false);
    patchTimeline({ head: timelineHead });
    setTimelineOpen(false);
  }

  function toggleTimelinePanel() {
    if (timelineOpen) closeTimeline();
    else setTimelineOpen(true);
  }

  function setTimelineDurationValue(next: number) {
    const duration = clamp(next, .5, 120);
    const head = Math.min(timelineHead, duration);
    setTimelineHead(head);
    patchTimeline({
      duration,
      head,
      tracks: timelineTracks.map((track) => ({
        ...track,
        keyframes: track.keyframes.map((frame) => ({ ...frame, time: Math.min(frame.time, duration) })).sort((left, right) => left.time - right.time),
      })),
    });
  }

  function addTimelineKeyframe(object: DirectorObject) {
    const frame = keyframeFromObject(object, timelineHead);
    const existing = timelineTracks.find((track) => track.objectId === object.id);
    const tracks = existing
      ? timelineTracks.map((track) => track.objectId === object.id
        ? { ...track, keyframes: [...track.keyframes.filter((item) => Math.abs(item.time - timelineHead) > .005), frame].sort((left, right) => left.time - right.time) }
        : track)
      : [...timelineTracks, { objectId: object.id, keyframes: [frame] }];
    patchTimeline({ head: timelineHead, tracks });
  }

  function patchObjectTransform(objectId: string, transform: Pick<DirectorObject, "position" | "rotation" | "scale">) {
    const object = valueRef.current.objects.find((item) => item.id === objectId);
    if (object?.kind === "camera" && object.followTargetId) {
      const target = valueRef.current.objects.find((item) => item.id === object.followTargetId);
      const followOffset = target ? transform.position.map((entry, index) => Number((entry - target.position[index]).toFixed(2))) as DirectorVector3 : null;
      patchObject(objectId, { ...transform, followOffset, ...(valueRef.current.tool === "rotate" ? { lookAtMode: "rotation", lookAtTargetId: null } : {}) });
      return;
    }
    patchObject(objectId, { ...transform, ...(object?.kind === "camera" && valueRef.current.tool === "rotate" ? { lookAtMode: "rotation", lookAtTargetId: null } : {}) });
  }

  async function applyReference() {
    if (!referenceAttachmentId || referencePreparing || referenceRunningRef.current) return;
    if (promptRunningRef.current) {
      notify("场景正在搭建，请稍后再识别参考图");
      return;
    }
    referenceRunningRef.current = true;
    setReferenceRunning(true);
    const controller = new AbortController();
    referenceAbortRef.current = controller;
    const startingSignature = sceneStructureSignature(valueRef.current);
    try {
      let current = referenceMode === "replace" ? createDefaultDirectorScene() : cloneScene(valueRef.current);
      let analyzed = false;
      let safeReferenceAttachmentId = referenceAttachmentId;
      let referenceFile: File | undefined;
      const sourceFile = await resolveAttachment(referenceAttachmentId);
      if (!sourceFile) throw new Error("参考图暂时不可用");
      const preparedFile = await prepareDirectorImage(sourceFile, "reference");
      const referenceSize = await imageDimensions(preparedFile);
      const referenceRatio = referenceSize.width / referenceSize.height;
      const referenceScale = (referenceRatio >= 1
        ? [3.2, 3.2 / referenceRatio, 1]
        : [3.2 * referenceRatio, 3.2, 1]) as DirectorVector3;
      if (preparedFile !== sourceFile) {
        safeReferenceAttachmentId = await registerFile(preparedFile);
        if (mountedRef.current) setReferenceAttachmentId(safeReferenceAttachmentId);
      }
      referenceFile = preparedFile;
      if (analyzeReference) {
        try {
          current = await analyzeReference(referenceFile, current, controller.signal);
          analyzed = true;
        } catch (error) {
          if (controller.signal.aborted) return;
          notify(`${error instanceof Error ? error.message : "视觉分析失败"}；已保留为站位参考层`);
        }
      }
      if (controller.signal.aborted) return;
      const latestScene = valueRef.current;
      if (sceneStructureSignature(latestScene) !== startingSignature) {
        notify("场景已在识图期间发生变化，本次结果未覆盖当前编辑");
        return;
      }
      const prop: DirectorObject = {
        id: `prop-${crypto.randomUUID()}`,
        kind: "prop",
        name: "站位参考",
        shape: "box",
        position: [0, 1.55, -1.25],
        rotation: [0, 0, 0],
        scale: referenceScale,
        color: "#34485e",
        visible: true,
        locked: true,
        referenceAttachmentId: safeReferenceAttachmentId,
      };
      const next = withLatestPanorama({ ...current, objects: [...current.objects, prop], selectedObjectId: prop.id }, latestScene);
      commit(next);
      await persistScene?.(next);
      setReferenceImportOpen(false);
      notify(analyzed ? "参考图已完成视觉分析并搭建到导演台" : "站位参考层已导入；原图保存在画布资产中");
    } catch (error) {
      if (!controller.signal.aborted) notify(error instanceof Error ? error.message : "参考图导入失败");
    } finally {
      referenceRunningRef.current = false;
      if (referenceAbortRef.current === controller) referenceAbortRef.current = null;
      if (mountedRef.current) setReferenceRunning(false);
    }
  }

  const panel = value.panel;
  const filteredObjects = value.objects.filter((object) => !sceneQuery.trim() || object.name.toLocaleLowerCase().includes(sceneQuery.trim().toLocaleLowerCase()));
  const currentCamera = selectedObject?.kind === "camera" ? selectedObject : activeCamera;

  return <div ref={rootRef} className={`director-studio-root${leftCollapsed ? " is-left-collapsed" : ""}`} role="dialog" aria-modal="true" aria-label="3D导演台" aria-busy={promptRunning || referencePreparing || referenceRunning || panoramaRunning}>
    <aside className={`director-left${leftCollapsed ? " is-collapsed" : ""}`}>
      <header><button type="button" aria-label="关闭导演台" onClick={() => onClose(valueRef.current)}><X size={17} /></button><strong>3D导演台</strong><button type="button" aria-label={leftCollapsed ? "展开" : "收起"} onClick={() => setLeftCollapsed((collapsed) => !collapsed)}>{leftCollapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}</button></header>
      <nav aria-label="导演台工具">
        <button type="button" aria-label="场景" className={panel === "scene" ? "is-active" : ""} onClick={() => patchScene({ panel: "scene" })}><Layers3 size={18} /></button>
        <button type="button" aria-label="添加角色" className={panel === "actors" ? "is-active" : ""} onClick={() => patchScene({ panel: "actors" })}><UserRound size={18} /></button>
        <button type="button" aria-label="添加机位" className={panel === "cameras" ? "is-active" : ""} onClick={() => patchScene({ panel: "cameras" })}><Camera size={18} /></button>
        <button type="button" aria-label="全景图" className={panel === "panorama" ? "is-active" : ""} onClick={() => patchScene({ panel: "panorama" })}><ImageIcon size={18} /></button>
        <button type="button" aria-label="选择画幅比例" className={panel === "ratio" ? "is-active" : ""} onClick={() => patchScene({ panel: "ratio" })}><Ratio size={18} /></button>
        <button type="button" aria-label="AI 识图导入" onClick={() => setReferenceImportOpen(true)}><ScanLine size={18} /></button>
        <span />
        <button type="button" aria-label="帮助" aria-haspopup="menu" aria-expanded={helpMenuOpen} className={helpMenuOpen ? "is-active" : ""} onClick={() => setHelpMenuOpen((open) => !open)}><CircleHelp size={18} /></button>
        {helpMenuOpen && <menu><button type="button" onClick={() => { setShortcutOpen(true); setHelpMenuOpen(false); }}>快捷键</button><button type="button" onClick={() => { setTutorialOpen(true); setHelpMenuOpen(false); }}>使用教程</button></menu>}
      </nav>
      {!leftCollapsed && <section className="director-left-panel">
        {panel === "scene" && <>
          <h2>场景</h2>
          <label className="director-scene-search"><input aria-label="搜索场景对象" placeholder="请输入搜索内容" value={sceneQuery} onChange={(event) => setSceneQuery(event.target.value)} /><Search size={14} /></label>
          <div className="director-scene-tree">{filteredObjects.map((object) => <div key={object.id} className={object.id === value.selectedObjectId ? "is-active" : ""}>
            <button type="button" className="director-scene-object" onClick={() => patchScene({ selectedObjectId: object.id, ...(object.kind === "camera" ? { activeCameraId: object.id } : {}) })}>{objectIcon(object)}<span>{object.name}</span></button>
            <button type="button" aria-label={object.visible ? `隐藏${object.name}` : `显示${object.name}`} onClick={() => patchObject(object.id, { visible: !object.visible })}>{object.visible ? <Eye size={13} /> : <EyeOff size={13} />}</button>
            <button type="button" aria-label={object.locked ? `解锁${object.name}` : `锁定${object.name}`} onClick={() => patchObject(object.id, { locked: !object.locked })}>{object.locked ? <Lock size={13} /> : <Unlock size={13} />}</button>
          </div>)}</div>
        </>}
        {panel === "actors" && <><h2>添加角色</h2><button type="button" className="director-left-wide-action" onClick={() => setReferenceImportOpen(true)}><Upload size={14} />本地上传</button><div className="director-preset-grid director-actor-grid">{DIRECTOR_ACTOR_PRESETS.map((preset) => <button key={preset.id} type="button" onClick={() => addActor(preset.id)}><span><UserRound size={24} /></span><b>{preset.label}</b></button>)}</div></>}
        {panel === "cameras" && <><h2>添加机位</h2><div className="director-preset-grid director-camera-grid">{DIRECTOR_CAMERA_PRESETS.map((preset, index) => <button key={preset} type="button" onClick={() => addCamera(preset)}><span><Camera size={20} /><i>{index ? index : "+"}</i></span><b>{preset}</b></button>)}</div></>}
        {panel === "panorama" && <><h2>全景图</h2><div className="director-panorama-tabs"><button type="button" className={panoramaMode === "upload" ? "is-active" : ""} onClick={() => { setPanoramaMode("upload"); panoramaInputRef.current?.click(); }}><Upload size={14} />本地上传</button><button type="button" className={panoramaMode === "history" ? "is-active" : ""} onClick={() => setPanoramaMode("history")}><History size={14} />历史记录</button><button type="button" className={panoramaMode === "ai" ? "is-active" : ""} onClick={() => setPanoramaMode("ai")}><Sparkles size={14} />AI生成</button></div>
          {panoramaMode === "upload" && <div className="director-panel-empty"><ImageIcon size={25} /><b>导入 2:1 全景图</b><span>支持 JPG、PNG、WEBP</span><button type="button" onClick={() => panoramaInputRef.current?.click()}>选择图片</button></div>}
          {panoramaMode === "history" && <div className="director-history-grid">{imageHistory.length ? imageHistory.map((image) => <button key={image.id} type="button" disabled={panoramaRunning} onClick={() => void applyPanoramaHistory(image.id)}><AttachmentImage attachmentId={image.id} alt={image.name} resolveAttachment={resolveAttachment} /><b>{image.name}</b></button>) : <div className="director-panel-empty"><History size={24} /><b>还没有图片历史</b></div>}</div>}
          {panoramaMode === "ai" && <div className="director-panorama-ai"><textarea placeholder="描述全景环境，例如：雨夜霓虹街道" value={panoramaPrompt} onChange={(event) => setPanoramaPrompt(event.target.value)} /><button type="button" disabled={!panoramaPrompt.trim() || panoramaRunning || !generatePanorama} onClick={() => void generateAiPanorama()}>{panoramaRunning ? <Clock3 size={14} /> : <Sparkles size={14} />}生成 2:1 全景图</button><small>通过共享 GPT 图片模型生成，完成后保存到当前画布资产。</small></div>}
        </>}
        {panel === "ratio" && <><h2>选择画幅比例</h2><div className="director-ratio-grid">{ASPECT_RATIOS.map((ratio) => <button type="button" key={ratio} className={value.aspectRatio === ratio ? "is-active" : ""} onClick={() => patchScene({ aspectRatio: ratio, ...(ratio === "adaptive" ? { compositionGuide: false } : {}) })}><i style={{ "--director-ratio": ratio === "adaptive" ? "1.45" : ratio.replace(":", "/") } as CSSProperties} /><b>{ratio === "adaptive" ? "自适应" : ratio}</b></button>)}</div></>}
      </section>}
    </aside>

    <main className="director-center">
      <div className="director-view-switch" role="group" aria-label="视角模式"><button type="button" className={value.viewMode === "director" ? "is-active" : ""} onClick={() => patchScene({ viewMode: "director", selectedObjectId: null })}>导演视角</button><button type="button" className={value.viewMode === "camera" ? "is-active" : ""} disabled={!activeCamera} onClick={() => activeCamera && patchScene({ viewMode: "camera", selectedObjectId: activeCamera.id })}>机位视角</button></div>
      <DirectorViewport ref={viewportRef} value={viewportValue} panoramaUrl={panoramaUrl} referenceUrls={referenceUrls} onSelect={(objectId) => patchScene({ selectedObjectId: objectId })} onTransform={patchObjectTransform} onWebglError={setWebglError} />
      {webglError && <div className="director-webgl-error"><Box size={28} /><strong>3D 视口不可用</strong><p>{webglError}</p><button type="button" onClick={() => onClose(valueRef.current)}>返回画布</button></div>}
      {activeCamera && value.aspectRatio !== "adaptive" && (value.viewMode === "director" || value.compositionGuide) && <div className={`director-camera-safe-frame ratio-${value.aspectRatio.replace(":", "-")}${value.viewMode === "camera" ? " is-camera-view" : ""}`} aria-hidden="true"><span>{value.aspectRatio}</span>{value.compositionGuide && <i />}</div>}
      <div className="director-view-cube"><div className="director-axis-ball"><button type="button" className="axis-y" aria-label="俯视视角" onClick={() => showDirectorAxis("top")}><span /></button><button type="button" className="axis-x" aria-label="右侧视角" onClick={() => showDirectorAxis("right")}><span /></button><button type="button" className="axis-z" aria-label="正面视角" onClick={() => showDirectorAxis("front")}><span /></button></div><button type="button" onClick={resetDirectorView}>重置视角</button></div>
      <div className="director-bottom-dock">
        <nav aria-label="导演台视口工具">
          <div className="director-transform-picker"><button type="button" aria-label="变换工具" aria-haspopup="menu" aria-expanded={transformMenuOpen} className="is-active" onClick={() => setTransformMenuOpen((open) => !open)}>{value.tool === "rotate" ? <Rotate3d size={18} /> : value.tool === "scale" ? <SlidersHorizontal size={18} /> : <MousePointer2 size={18} />}</button>{transformMenuOpen && <menu>{TOOL_BUTTONS.map((tool) => <button key={tool.id} type="button" className={value.tool === tool.id ? "is-active" : ""} onClick={() => { patchScene({ tool: tool.id }); setTransformMenuOpen(false); }}>{tool.icon}<span>{tool.label}</span></button>)}</menu>}</div>
          <button type="button" aria-label="截图" disabled={captureRunning || Boolean(webglError)} onClick={() => void captureCurrentView()}>{captureRunning ? <Clock3 size={18} /> : <Camera size={18} />}</button>
          <button type="button" aria-label="动画时间轴" className={timelineOpen ? "is-active" : ""} onClick={toggleTimelinePanel}><Film size={18} /></button>
        </nav>
        <div className="director-prompt-dock"><button type="button" aria-label="添加参考图" disabled={promptRunning} onClick={() => setReferenceImportOpen(true)}><Plus size={20} /></button><textarea aria-label="描述想搭建的场景" placeholder="描述想搭建的场景" value={prompt} readOnly={promptRunning} onChange={(event) => { setPrompt(event.target.value); onPromptChange?.(event.target.value); }} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void runPrompt(); } }} /><button type="button" aria-label="发送" disabled={!prompt.trim() || promptRunning || referenceRunning} onClick={() => void runPrompt()}>{promptRunning ? <Clock3 size={17} /> : <ArrowUp size={18} />}</button></div>
      </div>
      {value.aspectRatio !== "adaptive" && <button type="button" className={`director-composition-guide${value.compositionGuide ? " is-active" : ""}`} aria-label="构图参考线" onClick={() => patchScene({ compositionGuide: !value.compositionGuide })}><Crosshair size={16} /></button>}
      {timelineOpen && <section className="director-timeline" aria-label="动画时间轴">
        <header><span className="director-timeline-grip" /><button type="button" aria-label={timelinePlaying ? "暂停" : "播放"} onClick={toggleTimelinePlayback}>{timelinePlaying ? <Pause size={15} /> : <Play size={15} />}</button><button type="button" className={timelineAutoFrame ? "is-active" : ""} aria-pressed={timelineAutoFrame} title="记录后续关键变换" onClick={() => patchTimeline({ autoFrame: !timelineAutoFrame })}>自动帧</button><button type="button" className={timelineLoop ? "is-active" : ""} aria-pressed={timelineLoop} onClick={() => patchTimeline({ loop: !timelineLoop })}>循环播放</button><label>播放头 <input value={timelineHead.toFixed(2)} onChange={(event) => setTimelinePosition(Number(event.target.value))} /></label><label>总时长 <input value={timelineDuration.toFixed(2)} onChange={(event) => setTimelineDurationValue(Number(event.target.value))} /></label><button type="button" disabled={!timelineSelectedObject} onClick={() => timelineSelectedObject && addTimelineKeyframe(timelineSelectedObject)}><Plus size={13} />{timelineSelectedObject && timelineTracks.some((track) => track.objectId === timelineSelectedObject.id) ? "添加关键帧" : "新建轨道"}</button><span /><button type="button" disabled title="视频编码服务接入后开放"><Send size={14} />导出视频 Beta</button><button type="button" aria-label="时间线最小化" onClick={closeTimeline}><ChevronDown size={15} /></button></header>
        <div><aside><button type="button" className="is-active" onClick={() => activeCamera && patchScene({ selectedObjectId: activeCamera.id })}>主机位</button>{timelineTracks.map((track) => <button type="button" key={track.objectId} onClick={() => patchScene({ selectedObjectId: track.objectId })}>{value.objects.find((object) => object.id === track.objectId)?.name ?? track.objectId}</button>)}</aside><main><input aria-label="动画时间轴播放头" type="range" min="0" max={timelineDuration} step="0.01" value={timelineHead} onChange={(event) => setTimelinePosition(Number(event.target.value))} />{timelineTracks.length ? timelineTracks.map((track) => <div className="director-keyframe-track" key={track.objectId}>{track.keyframes.map((frame) => <i key={frame.id} title={`${frame.time.toFixed(2)}s`} style={{ left: `${(frame.time / timelineDuration) * 100}%` }} />)}</div>) : <p>请选择一个角色或者摄像机后，可新建轨道</p>}</main></div>
      </section>}
    </main>

    <aside className="director-inspector">
      <header><strong>{selectedObject ? titleForObject(selectedObject) : "3D场景"}</strong></header>
      {selectedObject?.kind === "actor" && <><nav><button type="button" className={actorInspectorTab === "properties" ? "is-active" : ""} onClick={() => setActorInspectorTab("properties")}>属性</button><button type="button" className={actorInspectorTab === "pose" ? "is-active" : ""} onClick={() => setActorInspectorTab("pose")}>姿势</button></nav><section>
        {actorInspectorTab === "properties" ? <ObjectProperties object={selectedObject} patch={(patch) => patchObject(selectedObject.id, patch)} /> : <ActorPose actor={selectedObject} patch={(patch) => patchObject(selectedObject.id, patch)} />}
      </section></>}
      {selectedObject?.kind === "camera" && <><nav><button type="button" className="is-active">属性</button><button type="button" onClick={() => void captureCurrentView(selectedObject.id)}>截图</button></nav><section><CameraProperties camera={selectedObject} cameras={cameras} actors={actors} patch={(patch) => patchObject(selectedObject.id, patch)} setActive={(cameraId) => patchScene({ activeCameraId: cameraId, selectedObjectId: cameraId })} setCameraView={() => patchScene({ activeCameraId: selectedObject.id, viewMode: value.viewMode === "camera" ? "director" : "camera" })} cameraViewActive={value.viewMode === "camera" && value.activeCameraId === selectedObject.id} />
        <div className="director-shot-section"><h3>相机截图</h3>{selectedObject.shots.map((shot) => <article key={shot.id}><AttachmentImage attachmentId={shot.attachmentId} alt={shot.name} resolveAttachment={resolveAttachment} onClick={() => setPreviewShot(shot)} /><div><button type="button" aria-label={`删除${shot.name}`} onClick={() => deleteShot(selectedObject.id, shot.id)}><Trash2 size={13} /></button><button type="button" aria-label={`发送${shot.name}到画布`} onClick={() => sendShotToCanvas(shot, selectedObject)}><Send size={13} /></button><button type="button" aria-label={`全屏查看${shot.name}`} onClick={() => setPreviewShot(shot)}><Maximize2 size={13} /></button></div><b>{shot.name}</b><small>{shot.width} × {shot.height}</small></article>)}</div>
      </section></>}
      {!selectedObject && <><header className="director-inspector-subhead"><strong>3D场景</strong></header><section><SceneProperties value={value} patchScene={patchSceneSettings} /></section></>}
      {selectedObject?.kind === "prop" && <><nav><button type="button" className="is-active">属性</button></nav><section><ObjectProperties object={selectedObject} patch={(patch) => patchObject(selectedObject.id, patch)} /></section></>}
    </aside>

    <input ref={panoramaInputRef} hidden type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => void importPanorama(event)} />
    <input ref={referenceInputRef} hidden type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => void importReference(event)} />

    {shortcutOpen && <div className="director-dialog-backdrop" onMouseDown={() => setShortcutOpen(false)}><section className="director-shortcut-dialog" role="dialog" aria-label="快捷键" onMouseDown={(event) => event.stopPropagation()}><header><strong>快捷键</strong><button type="button" aria-label="关闭快捷键" onClick={() => setShortcutOpen(false)}><X size={16} /></button></header><div>{[["俯视视角","T"],["重置视角","H"],["移动","V"],["旋转","R"],["缩放","F"],["正面视角","Y"],["网格吸附","X"],["截图","C"],["导演视角","1"],["机位视角","2"],["删除","Delete"]].map(([label,key]) => <p key={label}><span>{label}</span><kbd>{key}</kbd></p>)}</div></section></div>}
    {tutorialOpen && <div className="director-dialog-backdrop" onMouseDown={() => setTutorialOpen(false)}><section className="director-tutorial-dialog" role="dialog" aria-label="使用教程" onMouseDown={(event) => event.stopPropagation()}><header><strong>导演台快速上手</strong><button type="button" aria-label="关闭教程" onClick={() => setTutorialOpen(false)}><X size={16} /></button></header><ol><li><b>添加场景对象</b><span>从左侧加入角色与机位，或导入全景图。</span></li><li><b>完成构图</b><span>在视口选择对象，用移动、旋转、缩放工具调整。</span></li><li><b>设置镜头</b><span>选择机位、画幅和 FOV，切换机位视角确认画面。</span></li><li><b>截图回画布</b><span>点击底部相机，截图后在右栏发送到画布。</span></li></ol><button type="button" onClick={() => setTutorialOpen(false)}>开始搭建</button></section></div>}
    {referenceImportOpen && <div className="director-dialog-backdrop" onMouseDown={closeReferenceDialog}><section className="director-reference-dialog" role="dialog" aria-label="AI 识图导入" onMouseDown={(event) => event.stopPropagation()}><header><strong>AI 识图导入</strong><button type="button" aria-label={referenceRunning ? "取消识图导入" : "关闭识图导入"} onClick={closeReferenceDialog}><X size={16} /></button></header><nav><button type="button" className={referenceTab === "upload" ? "is-active" : ""} disabled={referenceRunning} onClick={() => setReferenceTab("upload")}>本地上传</button><button type="button" className={referenceTab === "history" ? "is-active" : ""} disabled={referenceRunning} onClick={() => setReferenceTab("history")}>历史记录</button></nav>{referenceTab === "upload" ? <button type="button" className="director-reference-drop" disabled={referenceRunning} onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = "copy"; }} onDrop={(event) => { event.preventDefault(); const file = event.dataTransfer.files[0]; if (file) void registerReferenceFile(file); }} onClick={() => referenceInputRef.current?.click()}>{referencePreparing ? <><Clock3 size={24} /><b>正在优化参考图片…</b><span>会自动限制到安全尺寸</span></> : referenceAttachmentId ? <><Check size={24} /><b>参考图片已就绪</b><span>点击或拖拽可重新选择</span></> : <><Upload size={24} /><b>点击上传图片或拖拽本地图片至此上传</b><span>上传后保存到当前画布资产</span></>}</button> : <div className="director-reference-history">{imageHistory.length ? imageHistory.map((image) => <button type="button" key={image.id} className={referenceAttachmentId === image.id ? "is-active" : ""} disabled={referenceRunning} onClick={() => selectReferenceHistory(image.id)}><AttachmentImage attachmentId={image.id} alt={image.name} resolveAttachment={resolveAttachment} /><span>{image.name}</span></button>) : <p>暂无可用图片历史</p>}</div>}<h3>选择是否覆盖场景</h3><div className="director-reference-mode"><button type="button" className={referenceMode === "insert" ? "is-active" : ""} disabled={referenceRunning} onClick={() => setReferenceMode("insert")}><b>插入当前导演台</b><span>保留当前内容，并根据参考图补充角色、机位和站位层</span></button><button type="button" className={referenceMode === "replace" ? "is-active" : ""} disabled={referenceRunning} onClick={() => setReferenceMode("replace")}><b>覆盖当前导演台</b><span>重置场景，再按参考图重新搭建角色与机位</span></button></div><small>共享 GPT 视觉模型会分析人数、角色、动作、机位、时间和画幅；原图同时保留为可隐藏的站位参考层。</small><button type="button" className="director-reference-submit" disabled={!referenceAttachmentId || referencePreparing || referenceRunning || promptRunning} onClick={() => void applyReference()}>{referenceRunning ? <><Clock3 size={14} />正在识图搭建…</> : "生成站位参考"}</button></section></div>}
    {previewShot && <div className="director-shot-preview" role="dialog" aria-label={previewShot.name} onMouseDown={() => setPreviewShot(null)}><section onMouseDown={(event) => event.stopPropagation()}><header><strong>{previewShot.name}</strong><button type="button" aria-label="关闭截图预览" onClick={() => setPreviewShot(null)}><X size={18} /></button></header><AttachmentImage attachmentId={previewShot.attachmentId} alt={previewShot.name} resolveAttachment={resolveAttachment} /></section></div>}
  </div>;
}

function ObjectProperties({ object, patch }: { object: DirectorObject; patch: (patch: Partial<DirectorObject>) => void }) {
  return <div className="director-object-properties">
    <label className="director-inspector-group"><span>名称</span><input type="text" value={object.name} maxLength={120} onChange={(event) => patch({ name: event.target.value })} /></label>
    <VectorFields label="位置" value={object.position} onChange={(position) => patch({ position })} />
    <VectorFields label="旋转" value={object.rotation} min={-360} max={360} onChange={(rotation) => patch({ rotation })} />
    <VectorFields label="缩放" value={object.scale} min={.01} max={100} onChange={(scale) => patch({ scale })} />
    <RangeField label="统一缩放" value={Number(((object.scale[0] + object.scale[1] + object.scale[2]) / 3).toFixed(2))} min={.1} max={5} step={.01} onChange={(scale) => patch({ scale: [scale, scale, scale] })} />
    <HexColorField label="颜色" value={object.color} onChange={(color) => patch({ color })} />
  </div>;
}

function ActorPose({ actor, patch }: { actor: DirectorActor; patch: (patch: Partial<DirectorActor>) => void }) {
  return <div className="director-actor-pose"><h3>姿势预设</h3><div className="director-pose-presets">{DIRECTOR_POSE_PRESETS.map((preset) => <button type="button" key={preset.id} className={actor.posePreset === preset.id ? "is-active" : ""} onClick={() => patch({ posePreset: preset.id })}><UserRound size={18} /><span>{preset.label}</span></button>)}</div><h3>姿势调节</h3>{DIRECTOR_POSE_SECTIONS.map((section) => <section key={section.title}><h4>{section.title}</h4>{section.controls.map((control) => <RangeField key={control.key} label={control.label} value={actor.pose[control.key]} min={control.min ?? -120} max={control.max ?? 120} onChange={(next) => patch({ pose: { ...actor.pose, [control.key as DirectorPoseKey]: next } })} />)}</section>)}</div>;
}

function CameraProperties({ camera, cameras, actors, patch, setActive, setCameraView, cameraViewActive }: {
  camera: DirectorCamera;
  cameras: DirectorCamera[];
  actors: DirectorActor[];
  patch: (patch: Partial<DirectorCamera>) => void;
  setActive: (cameraId: string) => void;
  setCameraView: () => void;
  cameraViewActive: boolean;
}) {
  const lookAtValue = camera.lookAtMode === "object" && camera.lookAtTargetId ? `object:${camera.lookAtTargetId}` : camera.lookAtMode;
  const followedActor = camera.followTargetId ? actors.find((actor) => actor.id === camera.followTargetId) : null;
  const patchPosition = (position: DirectorVector3) => patch({
    position,
    ...(followedActor ? { followOffset: position.map((entry, index) => Number((entry - followedActor.position[index]).toFixed(2))) as DirectorVector3 } : {}),
  });
  return <div className="director-camera-properties">
    <div className="director-camera-fov"><b>FOV {camera.fov}°</b><button type="button" className={cameraViewActive ? "is-active" : ""} aria-label="切换到机位视角" onClick={setCameraView}><Camera size={15} /></button></div>
    <label className="director-inspector-group"><span>名称</span><input value={camera.name} onChange={(event) => patch({ name: event.target.value })} /></label>
    <label className="director-inspector-group"><span>切换机位</span><select value={camera.id} onChange={(event) => setActive(event.target.value)}>{cameras.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
    <VectorFields label="位置" value={camera.position} onChange={patchPosition} />
    <label className="director-inspector-group"><span>跟随目标</span><select value={camera.followTargetId ?? ""} onChange={(event) => {
      const target = actors.find((actor) => actor.id === event.target.value);
      const currentPosition = followedActor && camera.followOffset
        ? followedActor.position.map((entry, index) => Number((entry + camera.followOffset![index]).toFixed(2))) as DirectorVector3
        : camera.position;
      patch({
        followTargetId: target?.id ?? null,
        followOffset: target ? currentPosition.map((entry, index) => Number((entry - target.position[index]).toFixed(2))) as DirectorVector3 : null,
        position: currentPosition,
      });
    }}><option value="">不跟随</option>{actors.map((actor) => <option value={actor.id} key={actor.id}>{actor.name}</option>)}</select></label>
    <VectorFields label="旋转" value={camera.rotation} min={-360} max={360} onChange={(rotation) => patch({ rotation, lookAtMode: "rotation", lookAtTargetId: null })} />
    <label className="director-inspector-group"><span>注视目标</span><select value={lookAtValue} onChange={(event) => {
      if (event.target.value === "rotation") patch({ lookAtMode: "rotation", lookAtTargetId: null });
      else if (event.target.value === "point") patch({ lookAtMode: "point", lookAtTargetId: null });
      else patch({ lookAtMode: "object", lookAtTargetId: event.target.value.replace(/^object:/, "") });
    }}><option value="rotation">按旋转角度</option><option value="point">手动坐标</option>{actors.map((actor) => <option value={`object:${actor.id}`} key={actor.id}>{actor.name}</option>)}</select></label>
    {camera.lookAtMode === "point" && <VectorFields label="注视坐标" value={camera.lookAt} onChange={(lookAt) => patch({ lookAt, lookAtMode: "point", lookAtTargetId: null })} />}
    <RangeField label="视野角度 (FOV)" value={camera.fov} min={15} max={120} onChange={(fov) => patch({ fov })} />
  </div>;
}

function SceneProperties({ value, patchScene }: { value: DirectorSceneState; patchScene: (patch: Partial<DirectorSceneState["scene"]>) => void }) {
  const scene = value.scene;
  return <div className="director-scene-properties"><RangeField label="场景缩放" value={scene.scale} min={.1} max={5} step={.01} suffix="" onChange={(scale) => patchScene({ scale })} /><VectorFields label="场景平移" value={scene.position} onChange={(position) => patchScene({ position })} /><VectorFields label="场景旋转" value={scene.rotation} min={-360} max={360} onChange={(rotation) => patchScene({ rotation })} /><HexColorField label="天空颜色" value={scene.skyColor} onChange={(skyColor) => patchScene({ skyColor })} /><RangeField label="水平旋转" value={scene.panoramaRotation} min={-180} max={180} suffix="°" onChange={(panoramaRotation) => patchScene({ panoramaRotation })} /><RangeField label="球形半径" value={scene.panoramaRadius} min={10} max={120} onChange={(panoramaRadius) => patchScene({ panoramaRadius })} /><Toggle label="角色标签" checked={scene.showLabels} onChange={(showLabels) => patchScene({ showLabels })} /><Toggle label="网格吸附" checked={scene.gridSnap} onChange={(gridSnap) => patchScene({ gridSnap })} /><Toggle label="地面吸附" checked={scene.groundSnap} onChange={(groundSnap) => patchScene({ groundSnap })} /><Toggle label="地面" checked={scene.showGround} onChange={(showGround) => patchScene({ showGround })} />{scene.showGround && <><RangeField label="透明度" value={scene.groundOpacity} min={0} max={1} step={.01} onChange={(groundOpacity) => patchScene({ groundOpacity })} /><RangeField label="高度" value={scene.groundHeight} min={-5} max={5} step={.1} onChange={(groundHeight) => patchScene({ groundHeight })} /></>}</div>;
}
