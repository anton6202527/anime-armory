import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronDown,
  Copy,
  FileText,
  GripVertical,
  ImagePlay,
  Info,
  MoreHorizontal,
  PencilLine,
  Plus,
  RotateCcw,
  Sparkles,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type DragEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
} from "react";
import {
  addScriptWorkbenchAsset,
  addScriptWorkbenchShot,
  clearScriptWorkbenchAssetSource,
  composeScriptWorkbenchVideoPrompt,
  deriveScriptWorkbenchSteps,
  hasRealScriptWorkbenchAssetSource,
  isScriptWorkbenchReadyForBatchVideo,
  lockScriptWorkbenchStyle,
  removeScriptWorkbenchAsset,
  removeScriptWorkbenchShot,
  reorderScriptWorkbenchShot,
  setScriptWorkbenchGlobalStyle,
  updateScriptWorkbenchAsset,
  updateScriptWorkbenchShot,
  type ScriptWorkbenchAsset,
  type ScriptWorkbenchAssetKind,
  type ScriptWorkbenchAssetPatch,
  type ScriptWorkbenchDocument,
  type ScriptWorkbenchShot,
  type ScriptWorkbenchShotPatch,
} from "./scriptWorkbenchModel";
import "../../styles/script-workbench.css";

export type ScriptWorkbenchStep = 1 | 2 | 3;
export type ScriptPromptComposeMode = "smart" | "concat";
export type ScriptImageQuality = "standard" | "high";

export type ScriptWorkbenchModelOption = {
  id: string;
  label: string;
  description?: string;
  cost?: number;
};

export type ScriptWorkbenchCanvasImage = {
  id: string;
  name: string;
  imageUrl?: string;
  attachmentId?: string;
  nodeId?: string;
  mimeType?: string;
};

export type ScriptWorkbenchImageOptions = {
  modelId: string;
  quality: ScriptImageQuality;
  resolution: "2K" | "4K";
  ratio: "2:1" | "16:9" | "9:16" | "1:1";
};

export type ScriptPromptComposeRequest = {
  nodeId: string;
  workbench: ScriptWorkbenchDocument;
  shot: ScriptWorkbenchShot;
  mode: ScriptPromptComposeMode;
  modelId?: string;
  signal: AbortSignal;
};

export type ScriptPromptComposeResult = { finalPrompt: string };

export type ScriptPromptBatchRequest = {
  nodeId: string;
  workbench: ScriptWorkbenchDocument;
  shotIds: string[];
  mode: ScriptPromptComposeMode;
  modelId?: string;
  signal: AbortSignal;
};

export type ScriptPromptBatchResult = {
  prompts: Array<{ shotId: string; finalPrompt: string }>;
};

export type ScriptAssetGenerateRequest = {
  nodeId: string;
  workbench: ScriptWorkbenchDocument;
  asset: ScriptWorkbenchAsset;
  options: ScriptWorkbenchImageOptions;
  signal: AbortSignal;
};

export type ScriptAssetGenerateResult = { patch: ScriptWorkbenchAssetPatch };

export type ScriptAssetBatchRequest = {
  nodeId: string;
  workbench: ScriptWorkbenchDocument;
  assetIds: string[];
  options: ScriptWorkbenchImageOptions;
  signal: AbortSignal;
};

export type ScriptAssetBatchResult = {
  updates: Array<{ assetId: string; patch: ScriptWorkbenchAssetPatch }>;
};

export type ScriptAssetCanvasSelectRequest = {
  nodeId: string;
  workbench: ScriptWorkbenchDocument;
  asset: ScriptWorkbenchAsset;
  image: ScriptWorkbenchCanvasImage;
  signal: AbortSignal;
};

export type ScriptAssetUploadRequest = {
  nodeId: string;
  workbench: ScriptWorkbenchDocument;
  asset: ScriptWorkbenchAsset;
  file: File;
  signal: AbortSignal;
};

export type ScriptBatchVideoRequest = {
  nodeId: string;
  workbench: ScriptWorkbenchDocument;
  signal: AbortSignal;
};

type MaybePromise<T> = T | Promise<T>;

export interface ScriptWorkflowOverlayProps {
  open: boolean;
  nodeId: string | null;
  workbench: ScriptWorkbenchDocument | null;
  initialDialog?: "video" | null;
  onChange: (workbench: ScriptWorkbenchDocument) => void;
  onClose: () => void;
  promptModels?: ScriptWorkbenchModelOption[];
  imageModels?: ScriptWorkbenchModelOption[];
  canvasImages?: ScriptWorkbenchCanvasImage[];
  onComposePrompt?: (request: ScriptPromptComposeRequest) => MaybePromise<ScriptPromptComposeResult | void>;
  onComposeAllPrompts?: (request: ScriptPromptBatchRequest) => MaybePromise<ScriptPromptBatchResult | void>;
  onGenerateAsset?: (request: ScriptAssetGenerateRequest) => MaybePromise<ScriptAssetGenerateResult | void>;
  onGenerateAssets?: (request: ScriptAssetBatchRequest) => MaybePromise<ScriptAssetBatchResult | void>;
  onSelectCanvasImage?: (request: ScriptAssetCanvasSelectRequest) => MaybePromise<ScriptAssetGenerateResult | void>;
  onUploadAsset?: (request: ScriptAssetUploadRequest) => MaybePromise<ScriptAssetGenerateResult | void>;
  onJumpToAssetNode?: (nodeId: string, asset: ScriptWorkbenchAsset) => void;
  onBatchVideo?: (request: ScriptBatchVideoRequest) => MaybePromise<void>;
}

type ShotEditableField = "duration" | "visual" | "scale" | "lighting" | "dialogue" | "sound" | "camera";
type AssetDialogTab = "generate" | "canvas" | "upload";
type PendingAction =
  | { type: "compose-shot"; id: string }
  | { type: "compose-all" }
  | { type: "generate-asset"; id: string }
  | { type: "generate-assets"; ids: string[] }
  | { type: "select-canvas"; id: string }
  | { type: "upload"; id: string }
  | { type: "batch-video" }
  | null;

type CellEditor = {
  shotId: string;
  field: ShotEditableField;
  draft: string;
};

const SHOT_SCALES = [
  "大远景",
  "远景",
  "全景",
  "中远景",
  "中景",
  "中近景",
  "近景",
  "特写",
  "大特写",
  "头肩景",
  "半身景",
  "全身景",
] as const;

const CAMERA_PRESETS = ["推镜", "拉镜", "摇镜", "跟镜", "俯拍", "仰拍"] as const;
const ASSET_KINDS: ScriptWorkbenchAssetKind[] = ["character", "scene", "prop"];
const ASSET_LABELS: Record<ScriptWorkbenchAssetKind, { title: string; singular: string; empty: string }> = {
  character: { title: "角色", singular: "角色", empty: "生成或上传角色图" },
  scene: { title: "场景", singular: "场景", empty: "生成或上传场景图" },
  prop: { title: "道具", singular: "道具", empty: "生成或上传道具图" },
};

const FIELD_LABELS: Record<ShotEditableField, string> = {
  duration: "时长",
  visual: "画面描述",
  scale: "景别",
  lighting: "光影氛围",
  dialogue: "对白·旁白",
  sound: "音效",
  camera: "运镜",
};

const FOCUSABLE_SELECTOR = [
  "button:not([disabled])",
  "[href]",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function messageForError(error: unknown): string {
  if (error instanceof Error && error.message.trim()) return error.message;
  return "操作失败，请稍后重试";
}

function applyAssetUpdates(
  document: ScriptWorkbenchDocument,
  updates: Array<{ assetId: string; patch: ScriptWorkbenchAssetPatch }>,
): ScriptWorkbenchDocument {
  return updates.reduce(
    (current, update) => updateScriptWorkbenchAsset(current, update.assetId, update.patch),
    document,
  );
}

function applyPromptUpdates(
  document: ScriptWorkbenchDocument,
  prompts: Array<{ shotId: string; finalPrompt: string }>,
): ScriptWorkbenchDocument {
  return prompts.reduce(
    (current, update) => updateScriptWorkbenchShot(current, update.shotId, { final_prompt: update.finalPrompt }),
    document,
  );
}

function removeAssetReferences(document: ScriptWorkbenchDocument, asset: ScriptWorkbenchAsset): ScriptWorkbenchDocument {
  const escapedName = asset.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const reference = new RegExp(`@${escapedName}(?![\\p{L}\\p{N}_-])`, "gu");
  return document.shots.reduce((current, shot) => {
    const patch: ScriptWorkbenchShotPatch = {};
    let referenced = false;
    for (const field of ["visual", "dialogue", "final_prompt"] as const) {
      reference.lastIndex = 0;
      if (reference.test(shot[field])) referenced = true;
      reference.lastIndex = 0;
      const nextValue = shot[field].replace(reference, "").replace(/[ \t]{2,}/g, " ").trim();
      if (nextValue !== shot[field]) patch[field] = nextValue;
    }
    if (referenced) patch.final_prompt = "";
    return Object.keys(patch).length ? updateScriptWorkbenchShot(current, shot.id, patch) : current;
  }, document);
}

function ModalShell({
  className,
  label,
  title,
  onClose,
  children,
}: {
  className: string;
  label: string;
  title: ReactNode;
  onClose: () => void;
  children: ReactNode;
}) {
  const modalRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    const previousActive = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    requestAnimationFrame(() => {
      if (modalRef.current?.contains(document.activeElement)) return;
      const first = modalRef.current?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
      (first ?? modalRef.current)?.focus();
    });
    return () => previousActive?.focus();
  }, []);
  return (
    <div className="script-wb-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section ref={modalRef} tabIndex={-1} className={`script-wb-modal ${className}`} role="dialog" aria-modal="true" aria-label={label}>
        <header>
          <strong>{title}</strong>
          <button type="button" className="script-wb-modal-close" aria-label={`关闭${label}`} onClick={onClose}><X size={16} /></button>
        </header>
        {children}
      </section>
    </div>
  );
}

export function ScriptWorkflowOverlay({
  open,
  nodeId,
  workbench,
  initialDialog = null,
  onChange,
  onClose,
  promptModels = [],
  imageModels = [],
  canvasImages = [],
  onComposePrompt,
  onComposeAllPrompts,
  onGenerateAsset,
  onGenerateAssets,
  onSelectCanvasImage,
  onUploadAsset,
  onJumpToAssetNode,
  onBatchVideo,
}: ScriptWorkflowOverlayProps) {
  const overlayRef = useRef<HTMLElement | null>(null);
  const documentRef = useRef(workbench);
  const lastOpenedNodeRef = useRef<string | null>(null);
  const actionAbortRef = useRef<AbortController | null>(null);
  const composingRef = useRef(false);
  const [step, setStep] = useState<ScriptWorkbenchStep>(1);
  const [editor, setEditor] = useState<CellEditor | null>(null);
  const [rowMenuId, setRowMenuId] = useState<string | null>(null);
  const [assetMenuId, setAssetMenuId] = useState<string | null>(null);
  const [promptShotId, setPromptShotId] = useState<string | null>(null);
  const [promptMode, setPromptMode] = useState<ScriptPromptComposeMode>("smart");
  const [promptModelId, setPromptModelId] = useState("");
  const [styleOpen, setStyleOpen] = useState(false);
  const [styleDraft, setStyleDraft] = useState("");
  const [newAssetKind, setNewAssetKind] = useState<ScriptWorkbenchAssetKind | null>(null);
  const [newAssetName, setNewAssetName] = useState("");
  const [newAssetDescription, setNewAssetDescription] = useState("");
  const [assetDialogId, setAssetDialogId] = useState<string | null>(null);
  const [assetTab, setAssetTab] = useState<AssetDialogTab>("generate");
  const [batchOpen, setBatchOpen] = useState(false);
  const [batchSelection, setBatchSelection] = useState<string[]>([]);
  const [promptBatchOpen, setPromptBatchOpen] = useState(false);
  const [promptBatchSelection, setPromptBatchSelection] = useState<string[]>([]);
  const [deleteAssetId, setDeleteAssetId] = useState<string | null>(null);
  const [deleteShotId, setDeleteShotId] = useState<string | null>(null);
  const [videoBatchOpen, setVideoBatchOpen] = useState(false);
  const [deleteAssetReferences, setDeleteAssetReferences] = useState<"keep" | "remove">("keep");
  const [imageOptions, setImageOptions] = useState<ScriptWorkbenchImageOptions>({
    modelId: "",
    quality: "standard",
    resolution: "2K",
    ratio: "2:1",
  });
  const [pending, setPending] = useState<PendingAction>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [draggedShotId, setDraggedShotId] = useState<string | null>(null);
  const [dropShotId, setDropShotId] = useState<string | null>(null);
  const [uploadDragging, setUploadDragging] = useState(false);
  const [copyStatus, setCopyStatus] = useState<"idle" | "done" | "failed">("idle");

  documentRef.current = workbench;

  const closeTransientUi = useCallback(() => {
    setEditor(null);
    setRowMenuId(null);
    setAssetMenuId(null);
    setPromptShotId(null);
    setStyleOpen(false);
    setNewAssetKind(null);
    setAssetDialogId(null);
    setBatchOpen(false);
    setPromptBatchOpen(false);
    setDeleteAssetId(null);
    setDeleteShotId(null);
    setVideoBatchOpen(false);
    setActionError(null);
    setCopyStatus("idle");
  }, []);

  useEffect(() => {
    if (!open) return;
    actionAbortRef.current?.abort();
    actionAbortRef.current = null;
    setPending(null);
    if (lastOpenedNodeRef.current !== nodeId) setStep(1);
    lastOpenedNodeRef.current = nodeId;
    closeTransientUi();
    if (initialDialog === "video") setVideoBatchOpen(true);
  }, [closeTransientUi, initialDialog, nodeId, open]);

  useEffect(() => {
    if (!open || !workbench) return;
    const currentSteps = deriveScriptWorkbenchSteps(workbench);
    if (step === 3 && (currentSteps.shots !== "done" || currentSteps.assets !== "done")) {
      setStep(currentSteps.shots === "done" ? 2 : 1);
      setPromptBatchOpen(false);
      setPromptShotId(null);
    } else if (step === 2 && currentSteps.shots !== "done") {
      setStep(1);
      setAssetDialogId(null);
      setBatchOpen(false);
    }
  }, [open, step, workbench]);

  useEffect(() => {
    if (!promptModelId && promptModels[0]) setPromptModelId(promptModels[0].id);
    else if (promptModelId && !promptModels.some((model) => model.id === promptModelId)) {
      setPromptModelId(promptModels[0]?.id ?? "");
    }
  }, [promptModelId, promptModels]);

  useEffect(() => {
    if (!imageOptions.modelId && imageModels[0]) {
      setImageOptions((current) => ({ ...current, modelId: imageModels[0]?.id ?? "" }));
    } else if (imageOptions.modelId && !imageModels.some((model) => model.id === imageOptions.modelId)) {
      setImageOptions((current) => ({ ...current, modelId: imageModels[0]?.id ?? "" }));
    }
  }, [imageModels, imageOptions.modelId]);

  useEffect(() => {
    if (!open) return undefined;
    const previousOverflow = document.body.style.overflow;
    const previousActive = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    document.body.style.overflow = "hidden";
    requestAnimationFrame(() => overlayRef.current?.focus());
    return () => {
      document.body.style.overflow = previousOverflow;
      actionAbortRef.current?.abort();
      previousActive?.focus();
    };
  }, [open]);

  const cancelPending = useCallback(() => {
    actionAbortRef.current?.abort();
    actionAbortRef.current = null;
    setPending(null);
  }, []);

  const closeOverlay = useCallback(() => {
    cancelPending();
    closeTransientUi();
    onClose();
  }, [cancelPending, closeTransientUi, onClose]);

  const commitEditor = useCallback(() => {
    if (!editor || !documentRef.current) return;
    const patch: ScriptWorkbenchShotPatch = editor.field === "duration"
      ? { duration: Math.max(5, Math.min(15, Number(editor.draft) || 5)) }
      : { [editor.field]: editor.draft } as ScriptWorkbenchShotPatch;
    onChange(updateScriptWorkbenchShot(documentRef.current, editor.shotId, patch));
    setEditor(null);
  }, [editor, onChange]);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Tab") {
        const root = overlayRef.current;
        if (!root) return;
        const modalList = root.querySelectorAll<HTMLElement>(".script-wb-modal");
        const focusScope = modalList.item(modalList.length - 1) || root;
        const focusable = [...focusScope.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)]
          .filter((element) => element.offsetParent !== null && !element.hasAttribute("disabled"));
        if (!focusable.length) {
          event.preventDefault();
          root.focus();
          return;
        }
        const first = focusable[0];
        const last = focusable.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
        return;
      }
      if (event.key !== "Escape") return;
      if (event.isComposing || composingRef.current) return;
      event.preventDefault();
      event.stopPropagation();
      if (deleteShotId) setDeleteShotId(null);
      else if (videoBatchOpen) { cancelPending(); setVideoBatchOpen(false); }
      else if (editor) setEditor(null);
      else if (rowMenuId) setRowMenuId(null);
      else if (assetMenuId) setAssetMenuId(null);
      else if (deleteAssetId) setDeleteAssetId(null);
      else if (promptBatchOpen) { cancelPending(); setPromptBatchOpen(false); }
      else if (batchOpen) { cancelPending(); setBatchOpen(false); }
      else if (assetDialogId) { cancelPending(); setAssetDialogId(null); }
      else if (promptShotId) { cancelPending(); setPromptShotId(null); }
      else if (newAssetKind) setNewAssetKind(null);
      else if (styleOpen) setStyleOpen(false);
      else closeOverlay();
    };
    document.addEventListener("keydown", onKeyDown, true);
    return () => document.removeEventListener("keydown", onKeyDown, true);
  }, [assetDialogId, assetMenuId, batchOpen, cancelPending, closeOverlay, deleteAssetId, deleteShotId, editor, newAssetKind, open, promptBatchOpen, promptShotId, rowMenuId, styleOpen, videoBatchOpen]);

  const runAction = useCallback(async (
    nextPending: Exclude<PendingAction, null>,
    action: (signal: AbortSignal) => Promise<void>,
  ) => {
    if (pending || actionAbortRef.current) return;
    const controller = new AbortController();
    actionAbortRef.current = controller;
    setActionError(null);
    setPending(nextPending);
    try {
      await action(controller.signal);
    } catch (error) {
      if (!isAbortError(error)) setActionError(messageForError(error));
    } finally {
      if (actionAbortRef.current === controller) actionAbortRef.current = null;
      setPending((current) => current === nextPending ? null : current);
    }
  }, [pending]);

  if (!open) return null;

  if (!nodeId || !workbench) {
    return (
      <section className="script-wb-overlay" role="dialog" aria-modal="true" aria-label="故事脚本工作台不可用">
        <div className="script-wb-empty">
          <Info size={28} />
          <strong>脚本工作台数据尚未就绪</strong>
          <small>请关闭后重新生成故事脚本。</small>
          <button type="button" className="script-wb-button primary" onClick={closeOverlay}>关闭</button>
        </div>
      </section>
    );
  }

  const steps = deriveScriptWorkbenchSteps(workbench);
  const readyAssets = workbench.assets.filter((asset) => asset.status === "ready" && hasRealScriptWorkbenchAssetSource(asset));
  const generatedCount = readyAssets.length;
  const composedCount = workbench.shots.filter((shot) => shot.final_prompt.trim()).length;
  const completedStages = [steps.shots, steps.assets, steps.prompts].filter((state) => state === "done").length;
  const allAssetsReady = steps.assets === "done";
  const allPromptsReady = steps.prompts === "done";
  const styleLocked = workbench.style_locked;
  const activePromptShot = workbench.shots.find((shot) => shot.id === promptShotId) ?? null;
  const activeAsset = workbench.assets.find((asset) => asset.id === assetDialogId) ?? null;
  const deletingAsset = workbench.assets.find((asset) => asset.id === deleteAssetId) ?? null;
  const deletingShot = workbench.shots.find((shot) => shot.id === deleteShotId) ?? null;
  const selectedPromptModel = promptModels.find((model) => model.id === promptModelId);
  const selectedImageModel = imageModels.find((model) => model.id === imageOptions.modelId);
  const promptCost = promptMode === "smart" ? selectedPromptModel?.cost : 0;
  const promptBatchCost = promptMode === "smart" && selectedPromptModel?.cost !== undefined
    ? selectedPromptModel.cost * promptBatchSelection.length
    : promptMode === "concat" ? 0 : undefined;
  const imageCost = selectedImageModel?.cost;

  const updateShot = (shotId: string, patch: ScriptWorkbenchShotPatch) => {
    onChange(updateScriptWorkbenchShot(workbench, shotId, patch));
  };

  const updateAsset = (assetId: string, patch: ScriptWorkbenchAssetPatch) => {
    onChange(updateScriptWorkbenchAsset(workbench, assetId, patch));
  };

  const openEditor = (shot: ScriptWorkbenchShot, field: ShotEditableField) => {
    setRowMenuId(null);
    setEditor({ shotId: shot.id, field, draft: String(shot[field]) });
  };

  const handleEditorKeyDown = (event: ReactKeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    if (event.nativeEvent.isComposing || event.nativeEvent.keyCode === 229 || composingRef.current) return;
    if (event.key === "Escape") {
      event.stopPropagation();
      setEditor(null);
    } else if ((event.metaKey || event.ctrlKey) && event.key === "Enter" && !composingRef.current) {
      event.preventDefault();
      commitEditor();
    }
  };

  const editorContent = (shot: ScriptWorkbenchShot, field: ShotEditableField) => {
    if (editor?.shotId !== shot.id || editor.field !== field) return null;
    if (field === "scale") {
      return (
        <div className="script-wb-cell-editor script-wb-scale-menu" role="listbox" aria-label="选择景别">
          {SHOT_SCALES.map((scale) => (
            <button key={scale} type="button" role="option" aria-selected={shot.scale === scale} onClick={() => { updateShot(shot.id, { scale }); setEditor(null); }}>
              <span>{scale}</span>{shot.scale === scale && <Check size={13} />}
            </button>
          ))}
        </div>
      );
    }
    const isDuration = field === "duration";
    return (
      <div
        className={`script-wb-cell-editor is-${field}`}
        onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node | null) && !composingRef.current) commitEditor();
        }}
      >
        {isDuration ? (
          <input
            autoFocus
            type="number"
            min={5}
            max={15}
            step={1}
            aria-label="镜头时长（秒）"
            value={editor.draft}
            onChange={(event) => setEditor((current) => current ? { ...current, draft: event.target.value } : current)}
            onKeyDown={handleEditorKeyDown}
            onCompositionStart={() => { composingRef.current = true; }}
            onCompositionEnd={() => { composingRef.current = false; }}
          />
        ) : (
          <textarea
            autoFocus
            aria-label={`编辑${FIELD_LABELS[field]}`}
            value={editor.draft}
            placeholder={field === "lighting" ? "例如：日系青春动漫风、戏剧冲突氛围…" : field === "sound" ? "例如：风声、雨声、脚步声、鼓点……" : field === "camera" ? "例如：推镜、拉镜、摇镜、跟镜……" : undefined}
            onChange={(event) => setEditor((current) => current ? { ...current, draft: event.target.value } : current)}
            onKeyDown={handleEditorKeyDown}
            onCompositionStart={() => { composingRef.current = true; }}
            onCompositionEnd={() => { composingRef.current = false; }}
          />
        )}
        {field === "camera" && <div className="script-wb-camera-presets">{CAMERA_PRESETS.map((preset) => <button key={preset} type="button" onClick={() => setEditor((current) => current ? { ...current, draft: current.draft ? `${current.draft}，${preset}` : preset } : current)}>{preset}</button>)}</div>}
        <div className="script-wb-editor-actions">
          <span>
            {field === "dialogue" && <><button type="button" onClick={() => setEditor((current) => current ? { ...current, draft: current.draft ? `${current.draft}\n台词：` : "台词：" } : current)}>台词</button><button type="button" onClick={() => setEditor((current) => current ? { ...current, draft: current.draft ? `${current.draft}\n[旁白]` : "[旁白]" } : current)}>旁白</button></>}
          </span>
          <button type="button" className="primary" onMouseDown={(event) => event.preventDefault()} onClick={commitEditor}>保存</button>
        </div>
        <small>{isDuration ? "范围 5–15 秒；失焦自动保存" : field === "visual" ? "输入 @ 可引用资产；失焦自动保存" : field === "camera" ? "点击预设可快速补充；失焦自动保存" : "失焦自动保存"}</small>
      </div>
    );
  };

  const renderCell = (shot: ScriptWorkbenchShot, field: Exclude<ShotEditableField, "duration" | "scale">, emptyLabel = "+") => (
    <>
      <button type="button" className={`script-wb-cell-button${shot[field] ? "" : " is-empty"}`} onClick={() => openEditor(shot, field)}>
        <span>{shot[field] || emptyLabel}</span>
      </button>
      {editorContent(shot, field)}
    </>
  );

  const openPrompt = (shotId: string) => {
    setCopyStatus("idle");
    setPromptShotId(shotId);
  };

  const moveShot = (shotId: string, targetIndex: number) => {
    onChange(reorderScriptWorkbenchShot(workbench, shotId, targetIndex));
    setRowMenuId(null);
  };

  const renderShotTable = () => (
    <div className="script-wb-table-scroll">
      <table className="script-wb-table">
        <colgroup>
          <col className="col-number" /><col className="col-duration" /><col className="col-visual" /><col className="col-scale" /><col className="col-light" />
          <col className="col-dialogue" /><col className="col-sound" /><col className="col-camera" /><col className="col-final" /><col className="col-action" />
        </colgroup>
        <thead><tr>{["镜号", "时长", "画面描述", "景别", "光影氛围", "对白·旁白", "音效", "运镜", "最终提示词", "操作"].map((label) => <th key={label} scope="col">{label}</th>)}</tr></thead>
        <tbody>
          {workbench.shots.map((shot, index) => (
            <tr
              key={shot.id}
              data-shot-id={shot.id}
              className={`${shot.color ? `is-${shot.color}` : ""}${draggedShotId === shot.id ? " is-dragging" : ""}${dropShotId === shot.id ? " is-drop-target" : ""}`}
              onDragOver={(event) => { if (draggedShotId) { event.preventDefault(); setDropShotId(shot.id); } }}
              onDrop={(event) => {
                event.preventDefault();
                if (draggedShotId) moveShot(draggedShotId, index);
                setDraggedShotId(null);
                setDropShotId(null);
              }}
            >
              <td><span className="script-wb-shot-number"><button type="button" draggable aria-label={`拖动镜头 ${index + 1}`} className="script-wb-drag-handle" onDragStart={(event) => { event.dataTransfer.effectAllowed = "move"; setDraggedShotId(shot.id); }} onDragEnd={() => { setDraggedShotId(null); setDropShotId(null); }}><GripVertical size={14} /></button>{index + 1}</span></td>
              <td><button type="button" className="script-wb-cell-button" onClick={() => openEditor(shot, "duration")}>{shot.duration}s</button>{editorContent(shot, "duration")}</td>
              <td>{renderCell(shot, "visual")}</td>
              <td><button type="button" className="script-wb-scale-button" aria-haspopup="listbox" aria-expanded={editor?.shotId === shot.id && editor.field === "scale"} onClick={() => openEditor(shot, "scale")}><span>{shot.scale}</span><ChevronDown size={12} /></button>{editorContent(shot, "scale")}</td>
              <td>{renderCell(shot, "lighting")}</td>
              <td>{renderCell(shot, "dialogue")}</td>
              <td>{renderCell(shot, "sound")}</td>
              <td>{renderCell(shot, "camera")}</td>
              <td><button type="button" className={`script-wb-final-button${shot.final_prompt ? " is-ready" : ""}${pending?.type === "compose-shot" && pending.id === shot.id ? " is-pending" : ""}`} onClick={() => openPrompt(shot.id)}>{pending?.type === "compose-shot" && pending.id === shot.id ? <><span className="script-wb-spinner" /> 合成中</> : shot.final_prompt ? "查看提示词" : "待生成提示词"}</button></td>
              <td className="script-wb-action-cell">
                <button type="button" className="script-wb-menu-trigger" aria-label={`镜头 ${index + 1} 操作`} aria-haspopup="menu" aria-expanded={rowMenuId === shot.id} onClick={() => setRowMenuId((current) => current === shot.id ? null : shot.id)}><MoreHorizontal size={16} /></button>
                {rowMenuId === shot.id && <div className="script-wb-menu script-wb-row-menu" role="menu">
                  <small>请选择颜色</small>
                  <div className="script-wb-color-list">{(["", "red", "yellow", "green", "blue", "gray"] as const).map((color) => <button key={color || "clear"} type="button" className={color || "clear"} aria-label={color ? `标记为${color}` : "清除颜色"} onClick={() => { updateShot(shot.id, { color }); setRowMenuId(null); }} />)}</div>
                  <button type="button" role="menuitem" className="danger" onClick={() => { setDeleteShotId(shot.id); setRowMenuId(null); }}><span>删除该行</span><Trash2 size={13} /></button>
                </div>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const openAssetDialog = (assetId: string, tab: AssetDialogTab) => {
    setAssetMenuId(null);
    setAssetDialogId(assetId);
    setAssetTab(tab);
    setUploadDragging(false);
  };

  const addAsset = () => {
    if (!newAssetKind || !newAssetName.trim()) return;
    const description = newAssetDescription.trim();
    onChange(addScriptWorkbenchAsset(workbench, {
      kind: newAssetKind,
      name: newAssetName.trim(),
      description,
      prompt: [newAssetName.trim(), description, workbench.global_style].filter(Boolean).join("，"),
      status: "pending",
      source: "none",
    }));
    setNewAssetKind(null);
    setNewAssetName("");
    setNewAssetDescription("");
  };

  const clearAsset = (assetId: string) => {
    onChange(clearScriptWorkbenchAssetSource(workbench, assetId));
    setAssetMenuId(null);
  };

  const generateAsset = (asset: ScriptWorkbenchAsset) => {
    if (!onGenerateAsset) return;
    if (deriveScriptWorkbenchSteps(documentRef.current ?? workbench).shots !== "done") {
      setActionError("请先补齐并确认全部镜头");
      return;
    }
    void runAction({ type: "generate-asset", id: asset.id }, async (signal) => {
      const result = await onGenerateAsset({ nodeId, workbench: documentRef.current ?? workbench, asset, options: imageOptions, signal });
      if (signal.aborted) return;
      if (result?.patch && documentRef.current) onChange(updateScriptWorkbenchAsset(documentRef.current, asset.id, result.patch));
      setAssetDialogId(null);
    });
  };

  const selectCanvasImage = (asset: ScriptWorkbenchAsset, image: ScriptWorkbenchCanvasImage) => {
    if (!onSelectCanvasImage) return;
    void runAction({ type: "select-canvas", id: asset.id }, async (signal) => {
      const result = await onSelectCanvasImage({ nodeId, workbench: documentRef.current ?? workbench, asset, image, signal });
      if (signal.aborted) return;
      if (result?.patch && documentRef.current) onChange(updateScriptWorkbenchAsset(documentRef.current, asset.id, result.patch));
      setAssetDialogId(null);
    });
  };

  const uploadAsset = (asset: ScriptWorkbenchAsset, file: File | undefined) => {
    if (!file || !onUploadAsset) return;
    if (!file.type.startsWith("image/")) {
      setActionError("请选择 PNG、JPG 或 WEBP 图片文件");
      return;
    }
    void runAction({ type: "upload", id: asset.id }, async (signal) => {
      const result = await onUploadAsset({ nodeId, workbench: documentRef.current ?? workbench, asset, file, signal });
      if (signal.aborted) return;
      if (result?.patch && documentRef.current) onChange(updateScriptWorkbenchAsset(documentRef.current, asset.id, result.patch));
      setAssetDialogId(null);
    });
  };

  const openBatch = () => {
    setBatchSelection(workbench.assets.filter((asset) => asset.status !== "ready" || !hasRealScriptWorkbenchAssetSource(asset)).map((asset) => asset.id));
    setBatchOpen(true);
  };

  const generateAssets = () => {
    if (!onGenerateAssets || !batchSelection.length) return;
    if (deriveScriptWorkbenchSteps(documentRef.current ?? workbench).shots !== "done") {
      setActionError("请先补齐并确认全部镜头");
      return;
    }
    const selected = [...batchSelection];
    void runAction({ type: "generate-assets", ids: selected }, async (signal) => {
      const result = await onGenerateAssets({ nodeId, workbench: documentRef.current ?? workbench, assetIds: selected, options: imageOptions, signal });
      if (signal.aborted) return;
      if (result?.updates && documentRef.current) onChange(applyAssetUpdates(documentRef.current, result.updates));
      setBatchOpen(false);
    });
  };

  const composeShot = (shot: ScriptWorkbenchShot) => {
    if (!onComposePrompt) return;
    const currentSteps = deriveScriptWorkbenchSteps(documentRef.current ?? workbench);
    if (currentSteps.shots !== "done" || currentSteps.assets !== "done") {
      setActionError(currentSteps.shots !== "done" ? "请先补齐并确认全部镜头" : "请先准备全部真实资产");
      return;
    }
    void runAction({ type: "compose-shot", id: shot.id }, async (signal) => {
      const result = await onComposePrompt({
        nodeId,
        workbench: documentRef.current ?? workbench,
        shot,
        mode: promptMode,
        ...(promptMode === "smart" && promptModelId ? { modelId: promptModelId } : {}),
        signal,
      });
      if (signal.aborted) return;
      if (result?.finalPrompt && documentRef.current) {
        onChange(lockScriptWorkbenchStyle(updateScriptWorkbenchShot(documentRef.current, shot.id, { final_prompt: result.finalPrompt })));
      }
    });
  };

  const composeAll = () => {
    if (!onComposeAllPrompts || !promptBatchSelection.length) return;
    const currentSteps = deriveScriptWorkbenchSteps(documentRef.current ?? workbench);
    if (currentSteps.shots !== "done" || currentSteps.assets !== "done") {
      setActionError(currentSteps.shots !== "done" ? "请先补齐并确认全部镜头" : "请先准备全部真实资产");
      return;
    }
    const selected = [...promptBatchSelection];
    void runAction({ type: "compose-all" }, async (signal) => {
      const result = await onComposeAllPrompts({
        nodeId,
        workbench: documentRef.current ?? workbench,
        shotIds: selected,
        mode: promptMode,
        ...(promptMode === "smart" && promptModelId ? { modelId: promptModelId } : {}),
        signal,
      });
      if (signal.aborted) return;
      if (result?.prompts && documentRef.current) {
        onChange(lockScriptWorkbenchStyle(applyPromptUpdates(documentRef.current, result.prompts)));
      }
      setPromptBatchOpen(false);
    });
  };

  const openPromptBatch = () => {
    if (steps.shots !== "done" || steps.assets !== "done") {
      setActionError(steps.shots !== "done" ? "请先补齐并确认全部镜头" : "请先准备全部真实资产");
      return;
    }
    const missing = workbench.shots.filter((shot) => !shot.final_prompt.trim()).map((shot) => shot.id);
    setPromptBatchSelection(missing.length ? missing : workbench.shots.map((shot) => shot.id));
    setPromptBatchOpen(true);
  };

  const submitBatchVideo = () => {
    if (!onBatchVideo || !isScriptWorkbenchReadyForBatchVideo(workbench)) return;
    void runAction({ type: "batch-video" }, async (signal) => {
      await onBatchVideo({ nodeId, workbench: documentRef.current ?? workbench, signal });
      if (!signal.aborted) setVideoBatchOpen(false);
    });
  };

  const copyPrompt = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopyStatus("done");
    } catch {
      setCopyStatus("failed");
    }
  };

  return (
    <section
      ref={overlayRef}
      tabIndex={-1}
      className="script-wb-overlay"
      role="dialog"
      aria-modal="true"
      aria-label={`${workbench.title} · 故事脚本工作台`}
      onPointerDown={(event) => {
        event.stopPropagation();
        const target = event.target as HTMLElement;
        if (!target.closest(".script-wb-row-menu") && !target.closest(".script-wb-action-cell")) setRowMenuId(null);
        if (!target.closest(".script-wb-asset-menu") && !target.closest(".script-wb-asset-card")) setAssetMenuId(null);
      }}
      onKeyDown={(event) => event.stopPropagation()}
    >
      <header className="script-wb-topbar">
        <div className="script-wb-title"><FileText size={15} /><strong>{workbench.title}</strong></div>
        <nav className="script-wb-steps" aria-label="故事脚本制作步骤">
          <button type="button" className={`script-wb-step${step === 1 ? " is-active" : ""}${steps.shots === "done" ? " is-done" : ""}`} aria-current={step === 1 ? "step" : undefined} onClick={() => setStep(1)}><i>{steps.shots === "done" && step !== 1 ? <Check size={13} /> : 1}</i><span><b>确认镜头</b><small>{workbench.shots.length}个镜头已就绪</small></span></button>
          <em className="script-wb-step-line" />
          <button type="button" disabled={steps.shots !== "done"} title={steps.shots !== "done" ? "请先确认完整镜头" : undefined} className={`script-wb-step${step === 2 ? " is-active" : ""}${steps.assets === "done" ? " is-done" : ""}`} aria-current={step === 2 ? "step" : undefined} onClick={() => setStep(2)}><i>{steps.assets === "done" ? <Check size={13} /> : 2}</i><span><b>准备资产</b><small>{generatedCount}/{workbench.assets.length} 已生成、还差 {Math.max(0, workbench.assets.length - generatedCount)} 个</small></span></button>
          <em className="script-wb-step-line" />
          <button type="button" disabled={steps.shots !== "done" || steps.assets !== "done"} title={steps.shots !== "done" ? "请先补齐并确认全部镜头" : steps.assets !== "done" ? "请先准备全部真实资产" : undefined} className={`script-wb-step${step === 3 ? " is-active" : ""}${steps.prompts === "done" ? " is-done" : ""}`} aria-current={step === 3 ? "step" : undefined} onClick={() => setStep(3)}><i>{steps.prompts === "done" ? <Check size={13} /> : 3}</i><span><b>合成提示词</b><small>{composedCount}/{workbench.shots.length} 已合成</small></span></button>
        </nav>
        <div className="script-wb-top-actions">
          <span className="script-wb-view-label">{step === 1 ? "脚本视图" : step === 2 ? "资产视图" : "提示词视图"}<ChevronDown size={13} /></span>
          <button type="button" className="script-wb-stage-status" disabled={!isScriptWorkbenchReadyForBatchVideo(workbench) || !onBatchVideo || Boolean(pending)} title={!onBatchVideo ? "未接入批量视频生成能力" : !isScriptWorkbenchReadyForBatchVideo(workbench) ? "镜头、资产和提示词完成后可用" : undefined} onClick={() => setVideoBatchOpen(true)}>{completedStages}/3 {completedStages === 3 ? "批量生视频" : "完成后可批量生视频"}</button>
          <button type="button" className="script-wb-close" aria-label="关闭故事脚本工作台" title="关闭 (ESC)" onClick={closeOverlay}><X size={18} /></button>
        </div>
      </header>

      {actionError && <div className="script-wb-alert" role="alert">{actionError}</div>}

      <main className="script-wb-main">
        {step === 1 && <>
          {renderShotTable()}
          <footer className="script-wb-footer">
            <button type="button" className="script-wb-button" onClick={() => onChange(addScriptWorkbenchShot(workbench))}><Plus size={15} />添加镜头</button>
            <button type="button" className="script-wb-button primary" disabled={steps.shots !== "done"} title={steps.shots !== "done" ? "请先补齐镜头的画面、景别、光影、音效和运镜" : undefined} onClick={() => setStep(2)}>下一步：准备资产<ArrowRight size={14} /></button>
          </footer>
        </>}

        {step === 2 && <>
          <div className="script-wb-assets-scroll">
            <button type="button" className="script-wb-style-card" disabled={styleLocked} title={styleLocked ? "全局美术风格首次合成后已锁定" : "编辑全局美术风格"} onClick={() => { setStyleDraft(workbench.global_style); setStyleOpen(true); }}><span>全局风格</span><p>{workbench.global_style}</p><i>{styleLocked ? "已锁定" : <PencilLine size={13} />}</i></button>
            {ASSET_KINDS.map((kind) => {
              const assets = workbench.assets.filter((asset) => asset.kind === kind);
              return <section className="script-wb-asset-section" key={kind} aria-labelledby={`script-assets-${kind}`}>
                <h3 id={`script-assets-${kind}`}>{ASSET_LABELS[kind].title}</h3>
                <div className="script-wb-asset-grid">
                  {assets.map((asset) => {
                    const isReady = asset.status === "ready" && hasRealScriptWorkbenchAssetSource(asset);
                    const isPendingGeneration = (pending?.type === "generate-asset" && pending.id === asset.id) || (pending?.type === "generate-assets" && pending.ids.includes(asset.id));
                    const status = isPendingGeneration ? "generating" : isReady ? "ready" : asset.status;
                    return <article className={`script-wb-asset-card is-${status}`} key={asset.id}>
                      <button type="button" className="script-wb-asset-preview" aria-label={`${asset.name}：${isReady ? "查看设定图" : ASSET_LABELS[kind].empty}`} onClick={() => openAssetDialog(asset.id, isReady ? "canvas" : "generate")}>
                        {asset.imageUrl && <img src={asset.imageUrl} alt="" />}
                        <span>{status === "generating" ? <><span className="script-wb-spinner" /><b>生成中</b></> : isReady ? <><Sparkles size={20} /><b>资产已就绪</b></> : status === "failed" ? <><X size={20} /><b>生成失败，点击重试</b></> : ASSET_LABELS[kind].empty}</span>
                      </button>
                      <button type="button" className="script-wb-asset-more" aria-label={`${asset.name}资产操作`} aria-haspopup="menu" aria-expanded={assetMenuId === asset.id} onClick={(event) => { event.stopPropagation(); setAssetMenuId((current) => current === asset.id ? null : asset.id); }}><MoreHorizontal size={15} /></button>
                      {assetMenuId === asset.id && <div className="script-wb-menu script-wb-asset-menu" role="menu" onClick={(event) => event.stopPropagation()}>
                        <button type="button" role="menuitem" onClick={() => openAssetDialog(asset.id, "canvas")}>选择图片</button>
                        <button type="button" role="menuitem" onClick={() => openAssetDialog(asset.id, "generate")}>AI 生{ASSET_LABELS[kind].singular}</button>
                        <button type="button" role="menuitem" disabled={!asset.nodeId || !onJumpToAssetNode} title={!onJumpToAssetNode ? "未接入节点跳转能力" : undefined} onClick={() => { if (asset.nodeId) onJumpToAssetNode?.(asset.nodeId, asset); }}>跳转至节点</button>
                        <button type="button" role="menuitem" disabled={!isReady} onClick={() => clearAsset(asset.id)}>清除图片</button>
                        <button type="button" role="menuitem" className="danger" onClick={() => { setDeleteAssetReferences("keep"); setDeleteAssetId(asset.id); setAssetMenuId(null); }}>删除</button>
                      </div>}
                      <strong>{asset.name}</strong>
                      <p className={asset.error ? "script-wb-asset-error" : ""}>{asset.error || asset.description}</p>
                    </article>;
                  })}
                  <button type="button" className="script-wb-asset-add" aria-label={`新增${ASSET_LABELS[kind].singular}`} onClick={() => { setNewAssetName(""); setNewAssetDescription(""); setNewAssetKind(kind); }}><Plus size={20} /><span>新增</span></button>
                </div>
              </section>;
            })}
          </div>
          <footer className="script-wb-footer">
            <span>检测到 {workbench.assets.length - generatedCount} 个资产没有真实设定图，可手动上传、从当前画布选择或调用图像模型生成。</span>
            <div><button type="button" className="script-wb-button" disabled={!workbench.assets.length || !onGenerateAssets || Boolean(pending)} title={!onGenerateAssets ? "未接入批量资产生成能力" : undefined} onClick={openBatch}><Sparkles size={14} />一键生成所有资产</button><button type="button" className="script-wb-button primary" disabled={!allAssetsReady} title={!allAssetsReady ? "请先准备全部真实资产" : undefined} onClick={() => setStep(3)}>下一步：合成提示词<ArrowRight size={14} /></button></div>
          </footer>
        </>}

        {step === 3 && <>
          {renderShotTable()}
          <footer className="script-wb-footer">
            <button type="button" className="script-wb-button" onClick={() => setStep(2)}><ArrowLeft size={14} />返回准备资产</button>
            <div>
              {!allAssetsReady && <span>尚有 {workbench.assets.length - generatedCount} 个资产未就绪</span>}
              <button type="button" className="script-wb-button primary" disabled={steps.shots !== "done" || steps.assets !== "done" || !workbench.shots.length || !onComposeAllPrompts || Boolean(pending)} title={steps.shots !== "done" ? "请先补齐并确认全部镜头" : steps.assets !== "done" ? "请先准备全部真实资产" : !onComposeAllPrompts ? "未接入批量提示词合成能力" : allPromptsReady ? "可选择镜头并覆盖已有提示词" : undefined} onClick={openPromptBatch}>{allPromptsReady ? <><RotateCcw size={14} />重新合成提示词</> : <><Sparkles size={14} />一键合成全部提示词</>}</button>
            </div>
          </footer>
        </>}
      </main>

      {styleOpen && !styleLocked && <ModalShell className="script-wb-style-modal" label="编辑全局风格" title="编辑全局风格" onClose={() => setStyleOpen(false)}>
        <div><textarea autoFocus value={styleDraft} aria-label="全局美术风格" onChange={(event) => setStyleDraft(event.target.value)} onCompositionStart={() => { composingRef.current = true; }} onCompositionEnd={() => { composingRef.current = false; }} /><p>全局美术风格首次合成后即锁定，后续不可再修改；修改风格会清空已有提示词。</p><div className="script-wb-modal-actions"><button type="button" className="script-wb-button" onClick={() => setStyleOpen(false)}>取消</button><button type="button" className="script-wb-button primary" disabled={!styleDraft.trim()} onClick={() => { onChange(setScriptWorkbenchGlobalStyle(workbench, styleDraft)); setStyleOpen(false); }}>确认</button></div></div>
      </ModalShell>}

      {activePromptShot && <ModalShell className="script-wb-prompt-modal" label={`第 ${workbench.shots.findIndex((shot) => shot.id === activePromptShot.id) + 1} 镜最终提示词`} title={<span>第 {workbench.shots.findIndex((shot) => shot.id === activePromptShot.id) + 1} 镜：最终提示词 <Info size={13} aria-label="提示词由镜头信息、全局风格和所选合成方式生成" /></span>} onClose={() => { cancelPending(); setPromptShotId(null); }}>
        <div className="script-wb-prompt-body">
          <section className="script-wb-prompt-output"><header><strong>分镜提示词</strong><small>{activePromptShot.final_prompt ? "已生成 · 自动保存" : "未生成"}</small></header><textarea aria-label="分镜提示词" value={activePromptShot.final_prompt} disabled={Boolean(pending)} placeholder="点击立即合成提示词，重新点击会覆盖生成。" onChange={(event) => { const next = updateScriptWorkbenchShot(workbench, activePromptShot.id, { final_prompt: event.target.value }); onChange(event.target.value.trim() ? lockScriptWorkbenchStyle(next) : next); }} onCompositionStart={() => { composingRef.current = true; }} onCompositionEnd={() => { composingRef.current = false; }} /></section>
          <section className="script-wb-prompt-output"><header><strong>视频运动提示词</strong><small>{activePromptShot.final_prompt ? "已生成" : "未生成"}</small></header><div className={`script-wb-prompt-preview${activePromptShot.final_prompt ? "" : " is-empty"}`}>{composeScriptWorkbenchVideoPrompt(workbench.global_style, activePromptShot) || "点击立即合成提示词，重新点击会覆盖生成。"}</div></section>
        </div>
        <footer className="script-wb-prompt-footer">
          {promptMode === "smart" && <select className="script-wb-model-select" aria-label="提示词模型" value={promptModelId} disabled={!promptModels.length || Boolean(pending)} onChange={(event) => setPromptModelId(event.target.value)}><option value="">未提供可用模型</option>{promptModels.map((model) => <option key={model.id} value={model.id}>{model.label}{model.description ? ` · ${model.description}` : ""}</option>)}</select>}
          <div className="script-wb-compose-modes"><label><input type="radio" name="script-compose-mode" value="smart" checked={promptMode === "smart"} disabled={Boolean(pending)} onChange={() => setPromptMode("smart")} />智能合成</label><label><input type="radio" name="script-compose-mode" value="concat" checked={promptMode === "concat"} disabled={Boolean(pending)} onChange={() => setPromptMode("concat")} />自动拼接</label></div>
          <small>{promptCost === undefined ? (promptMode === "smart" ? "模型费用由调用方确认" : "免费") : promptCost > 0 ? `✦ ${promptCost}` : "免费"}</small>
          {activePromptShot.final_prompt && <button type="button" className="script-wb-button" title={copyStatus === "done" ? "已复制" : copyStatus === "failed" ? "复制失败" : "复制提示词"} onClick={() => void copyPrompt(activePromptShot.final_prompt)}><Copy size={13} />{copyStatus === "done" ? "已复制" : "复制"}</button>}
          {pending?.type === "compose-shot" && pending.id === activePromptShot.id ? <button type="button" className="script-wb-button" onClick={cancelPending}>取消</button> : <button type="button" className="script-wb-button primary" disabled={Boolean(pending) || !onComposePrompt || steps.shots !== "done" || steps.assets !== "done" || (promptMode === "smart" && !promptModelId)} title={steps.shots !== "done" ? "请先补齐并确认全部镜头" : steps.assets !== "done" ? "请先准备全部真实资产" : !onComposePrompt ? "未接入提示词合成能力" : undefined} onClick={() => composeShot(activePromptShot)}>{activePromptShot.final_prompt ? <><RotateCcw size={13} />重新合成提示词</> : "立即合成提示词"}</button>}
        </footer>
      </ModalShell>}

      {promptBatchOpen && <ModalShell className="script-wb-prompt-batch-modal" label="一键合成全部提示词" title="一键合成全部提示词" onClose={() => { cancelPending(); setPromptBatchOpen(false); }}>
        <div className="script-wb-prompt-batch-list">
          <p>选择需要合成的镜头。已有提示词的镜头默认不选，勾选后会覆盖原内容。</p>
          {workbench.shots.map((shot, index) => <label className="script-wb-prompt-batch-row" key={shot.id}>
            <input type="checkbox" checked={promptBatchSelection.includes(shot.id)} disabled={Boolean(pending)} onChange={(event) => setPromptBatchSelection((selected) => event.target.checked ? [...new Set([...selected, shot.id])] : selected.filter((id) => id !== shot.id))} />
            <span><strong>镜头 {index + 1}<i>{shot.duration}s · {shot.scale}</i>{shot.final_prompt && <em>已有提示词</em>}</strong><p>{shot.visual}</p><small>运镜：{shot.camera}　音效：{shot.sound}</small></span>
          </label>)}
        </div>
        <footer className="script-wb-prompt-batch-footer">
          <label><input type="checkbox" checked={promptBatchSelection.length === workbench.shots.length && workbench.shots.length > 0} disabled={Boolean(pending)} onChange={(event) => setPromptBatchSelection(event.target.checked ? workbench.shots.map((shot) => shot.id) : [])} /><span>已选 {promptBatchSelection.length}/{workbench.shots.length}</span></label>
          <div className="script-wb-compose-modes"><label><input type="radio" name="script-batch-compose-mode" value="smart" checked={promptMode === "smart"} disabled={Boolean(pending)} onChange={() => setPromptMode("smart")} />智能合成</label><label><input type="radio" name="script-batch-compose-mode" value="concat" checked={promptMode === "concat"} disabled={Boolean(pending)} onChange={() => setPromptMode("concat")} />自动拼接</label></div>
          {promptMode === "smart" && <select className="script-wb-model-select" aria-label="批量提示词模型" value={promptModelId} disabled={!promptModels.length || Boolean(pending)} onChange={(event) => setPromptModelId(event.target.value)}><option value="">未提供可用模型</option>{promptModels.map((model) => <option key={model.id} value={model.id}>{model.label}{model.description ? ` · ${model.description}` : ""}</option>)}</select>}
          <span className="script-wb-cost" title="智能合成费用将在回调提交前再次确认"><Sparkles size={13} />{promptBatchCost === undefined ? "待确认" : promptBatchCost > 0 ? promptBatchCost : "免费"}</span>
          {pending?.type === "compose-all" ? <button type="button" className="script-wb-button" onClick={cancelPending}>取消</button> : <button type="button" className="script-wb-button primary" disabled={steps.shots !== "done" || steps.assets !== "done" || !promptBatchSelection.length || !onComposeAllPrompts || (promptMode === "smart" && !promptModelId)} title={steps.shots !== "done" ? "请先补齐并确认全部镜头" : steps.assets !== "done" ? "请先准备全部真实资产" : !onComposeAllPrompts ? "未接入批量提示词合成能力" : promptMode === "smart" ? "确认后由调用方执行最终费用确认" : "自动拼接不会调用付费模型"} onClick={composeAll}>确认合成 ({promptBatchSelection.length})</button>}
        </footer>
      </ModalShell>}

      {newAssetKind && <ModalShell className="script-wb-new-asset-modal" label={`新增${ASSET_LABELS[newAssetKind].singular}`} title={`新增${ASSET_LABELS[newAssetKind].singular}`} onClose={() => setNewAssetKind(null)}>
        <div className="script-wb-new-asset-form"><label>名称<input autoFocus value={newAssetName} placeholder={`请输入${ASSET_LABELS[newAssetKind].singular}名称`} onChange={(event) => setNewAssetName(event.target.value)} onCompositionStart={() => { composingRef.current = true; }} onCompositionEnd={() => { composingRef.current = false; }} /></label><label>描述<textarea value={newAssetDescription} placeholder="补充外观、服装、环境或材质信息" onChange={(event) => setNewAssetDescription(event.target.value)} onCompositionStart={() => { composingRef.current = true; }} onCompositionEnd={() => { composingRef.current = false; }} /></label><div className="script-wb-modal-actions"><button type="button" className="script-wb-button" onClick={() => setNewAssetKind(null)}>取消</button><button type="button" className="script-wb-button primary" disabled={!newAssetName.trim()} onClick={addAsset}>新增</button></div></div>
      </ModalShell>}

      {deletingShot && <ModalShell className="script-wb-delete-shot-modal" label={`删除镜头 ${workbench.shots.findIndex((shot) => shot.id === deletingShot.id) + 1}`} title="删除镜头" onClose={() => setDeleteShotId(null)}>
        <div className="script-wb-confirm-body"><p>确定删除这个镜头吗？镜头内容和已经合成的提示词会一并移除，此操作可通过画布撤销恢复。</p><blockquote>{deletingShot.visual}</blockquote><div className="script-wb-modal-actions"><button type="button" className="script-wb-button" onClick={() => setDeleteShotId(null)}>取消</button><button type="button" className="script-wb-button danger" onClick={() => { onChange(removeScriptWorkbenchShot(workbench, deletingShot.id)); setDeleteShotId(null); }}>确认删除</button></div></div>
      </ModalShell>}

      {videoBatchOpen && <ModalShell className="script-wb-video-modal" label="批量创建视频任务" title="批量创建视频任务" onClose={() => { cancelPending(); setVideoBatchOpen(false); }}>
        <div className="script-wb-confirm-body"><p>将为 {workbench.shots.length} 个镜头创建或同步视频任务，共 {workbench.shots.reduce((total, shot) => total + shot.duration, 0)} 秒。</p><ul><li>每个任务携带最终提示词、时长和已准备资产引用。</li><li>当前本地共享模型仅提供文本与图片能力；未配置视频后端时，任务会明确保持未提交，不会伪造 MP4。</li></ul><div className="script-wb-modal-actions"><button type="button" className="script-wb-button" onClick={() => setVideoBatchOpen(false)}>取消</button>{pending?.type === "batch-video" ? <button type="button" className="script-wb-button" onClick={cancelPending}>停止提交</button> : <button type="button" className="script-wb-button primary" onClick={submitBatchVideo}>确认创建 {workbench.shots.length} 个任务</button>}</div></div>
      </ModalShell>}

      {deletingAsset && <ModalShell className="script-wb-delete-asset-modal" label={`删除资产 ${deletingAsset.name}`} title="删除资产" onClose={() => setDeleteAssetId(null)}>
        <div className="script-wb-delete-asset-body"><p>确定删除资产“{deletingAsset.name}”吗？资产图片与绑定关系会从当前脚本移除。</p><fieldset><legend>如何处理镜头中的 @引用</legend><label><input type="radio" name="script-delete-asset-reference" value="keep" checked={deleteAssetReferences === "keep"} onChange={() => setDeleteAssetReferences("keep")} /><span><strong>保留镜头文本</strong><small>只删除资产，镜头里的文字不变。</small></span></label><label><input type="radio" name="script-delete-asset-reference" value="remove" checked={deleteAssetReferences === "remove"} onChange={() => setDeleteAssetReferences("remove")} /><span><strong>同时移除引用</strong><small>清理画面、对白与提示词中的 @{deletingAsset.name}，相关提示词需重新合成。</small></span></label></fieldset><div className="script-wb-modal-actions"><button type="button" className="script-wb-button" onClick={() => setDeleteAssetId(null)}>取消</button><button type="button" className="script-wb-button danger" onClick={() => { const source = deleteAssetReferences === "remove" ? removeAssetReferences(workbench, deletingAsset) : workbench; onChange(removeScriptWorkbenchAsset(source, deletingAsset.id)); setDeleteAssetId(null); }}>确认删除</button></div></div>
      </ModalShell>}

      {activeAsset && <ModalShell className="script-wb-asset-modal" label={`选择图片（${activeAsset.name}）`} title={`选择图片（${activeAsset.name}）`} onClose={() => { cancelPending(); setAssetDialogId(null); }}>
        <nav className="script-wb-tabs" aria-label="图片来源"><button type="button" disabled={Boolean(pending)} className={assetTab === "generate" ? "is-active" : ""} aria-current={assetTab === "generate" ? "page" : undefined} onClick={() => setAssetTab("generate")}>AI生成</button><button type="button" disabled={Boolean(pending)} className={assetTab === "canvas" ? "is-active" : ""} aria-current={assetTab === "canvas" ? "page" : undefined} onClick={() => setAssetTab("canvas")}>从当前画布选择</button><button type="button" disabled={Boolean(pending)} className={assetTab === "upload" ? "is-active" : ""} aria-current={assetTab === "upload" ? "page" : undefined} onClick={() => setAssetTab("upload")}>本地上传</button></nav>
        {assetTab === "generate" && <div className="script-wb-asset-ai"><textarea aria-label={`${activeAsset.name}生图提示词`} value={activeAsset.prompt} disabled={Boolean(pending)} placeholder="描述角色、场景或道具的外观与风格" onChange={(event) => updateAsset(activeAsset.id, { prompt: event.target.value })} onCompositionStart={() => { composingRef.current = true; }} onCompositionEnd={() => { composingRef.current = false; }} /><footer className="script-wb-asset-options"><select aria-label="图片模型" value={imageOptions.modelId} disabled={!imageModels.length || Boolean(pending)} onChange={(event) => setImageOptions((current) => ({ ...current, modelId: event.target.value }))}><option value="">未提供模型</option>{imageModels.map((model) => <option key={model.id} value={model.id}>{model.label}</option>)}</select><select aria-label="画质" value={imageOptions.quality} disabled={Boolean(pending)} onChange={(event) => setImageOptions((current) => ({ ...current, quality: event.target.value as ScriptImageQuality }))}><option value="standard">标准画质</option><option value="high">高清画质</option></select><select aria-label="分辨率" value={imageOptions.resolution} disabled={Boolean(pending)} onChange={(event) => setImageOptions((current) => ({ ...current, resolution: event.target.value as ScriptWorkbenchImageOptions["resolution"] }))}><option>2K</option><option>4K</option></select><select aria-label="宽高比" value={imageOptions.ratio} disabled={Boolean(pending)} onChange={(event) => setImageOptions((current) => ({ ...current, ratio: event.target.value as ScriptWorkbenchImageOptions["ratio"] }))}><option>2:1</option><option>16:9</option><option>9:16</option><option>1:1</option></select><span title="具体费用由调用方在提交前确认"><Sparkles size={13} />{imageCost ?? "待确认"}</span>{pending?.type === "generate-asset" && pending.id === activeAsset.id ? <button type="button" className="script-wb-button" onClick={cancelPending}>取消</button> : <button type="button" className="script-wb-button primary" disabled={Boolean(pending) || steps.shots !== "done" || !onGenerateAsset || !activeAsset.prompt.trim() || !imageOptions.modelId} title={steps.shots !== "done" ? "请先补齐并确认全部镜头" : !onGenerateAsset ? "未接入资产生成能力" : !imageOptions.modelId ? "未提供可用图像模型" : "由调用方确认费用后提交"} onClick={() => generateAsset(activeAsset)}>确认生成</button>}</footer></div>}
        {assetTab === "canvas" && (canvasImages.length ? <div className="script-wb-canvas-grid">{canvasImages.map((image) => <button type="button" key={image.id} disabled={!onSelectCanvasImage || Boolean(pending)} title={!onSelectCanvasImage ? "未接入画布图片绑定能力" : undefined} onClick={() => selectCanvasImage(activeAsset, image)}>{image.imageUrl ? <img src={image.imageUrl} alt="" /> : <span>图片预览不可用</span>}<span>{image.name}</span></button>)}</div> : <div className="script-wb-empty"><ImagePlay size={26} /><strong>当前画布暂无可选图片</strong><small>生成或上传图片后可在这里选择</small></div>)}
        {assetTab === "upload" && <label className={`script-wb-upload-zone${uploadDragging ? " is-dragging" : ""}`} onDragEnter={(event) => { event.preventDefault(); setUploadDragging(true); }} onDragOver={(event) => event.preventDefault()} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setUploadDragging(false); }} onDrop={(event: DragEvent<HTMLLabelElement>) => { event.preventDefault(); setUploadDragging(false); uploadAsset(activeAsset, event.dataTransfer.files[0]); }}><Upload size={28} /><strong>{pending?.type === "upload" && pending.id === activeAsset.id ? "上传中…" : "拖拽图片到这里，或点击上传"}</strong><small>{onUploadAsset ? "支持 PNG、JPG、WEBP" : "未接入图片上传能力"}</small><input type="file" accept="image/png,image/jpeg,image/webp" disabled={!onUploadAsset || Boolean(pending)} onChange={(event) => { uploadAsset(activeAsset, event.target.files?.[0]); event.currentTarget.value = ""; }} /></label>}
      </ModalShell>}

      {batchOpen && <ModalShell className="script-wb-batch-modal" label="一键生成所有资产" title="一键生成所有资产" onClose={() => { cancelPending(); setBatchOpen(false); }}>
        <div className="script-wb-batch-list">{ASSET_KINDS.map((kind) => { const assets = workbench.assets.filter((asset) => asset.kind === kind); return assets.length ? <section key={kind}><h4>{ASSET_LABELS[kind].title} ({assets.length})</h4>{assets.map((asset) => <label className="script-wb-batch-row" key={asset.id}><input type="checkbox" checked={batchSelection.includes(asset.id)} disabled={Boolean(pending)} onChange={(event) => setBatchSelection((selected) => event.target.checked ? [...new Set([...selected, asset.id])] : selected.filter((id) => id !== asset.id))} /><span><strong>{asset.name}<i>{ASSET_LABELS[kind].singular}</i></strong><textarea value={asset.prompt} aria-label={`${asset.name}生图提示词`} disabled={Boolean(pending)} onChange={(event) => updateAsset(asset.id, { prompt: event.target.value })} onCompositionStart={() => { composingRef.current = true; }} onCompositionEnd={() => { composingRef.current = false; }} /></span></label>)}</section> : null; })}</div>
        <footer className="script-wb-batch-footer"><label><input type="checkbox" checked={batchSelection.length === workbench.assets.length && workbench.assets.length > 0} disabled={Boolean(pending)} onChange={(event) => setBatchSelection(event.target.checked ? workbench.assets.map((asset) => asset.id) : [])} /><span>已选 {batchSelection.length}/{workbench.assets.length}</span></label><div className="script-wb-batch-options"><select aria-label="批量图片模型" value={imageOptions.modelId} disabled={Boolean(pending)} onChange={(event) => setImageOptions((current) => ({ ...current, modelId: event.target.value }))}><option value="">未提供模型</option>{imageModels.map((model) => <option key={model.id} value={model.id}>{model.label}</option>)}</select><select aria-label="批量画质" value={imageOptions.quality} disabled={Boolean(pending)} onChange={(event) => setImageOptions((current) => ({ ...current, quality: event.target.value as ScriptImageQuality }))}><option value="standard">标准画质</option><option value="high">高清画质</option></select><select aria-label="批量分辨率" value={imageOptions.resolution} disabled={Boolean(pending)} onChange={(event) => setImageOptions((current) => ({ ...current, resolution: event.target.value as ScriptWorkbenchImageOptions["resolution"] }))}><option>2K</option><option>4K</option></select><select aria-label="批量宽高比" value={imageOptions.ratio} disabled={Boolean(pending)} onChange={(event) => setImageOptions((current) => ({ ...current, ratio: event.target.value as ScriptWorkbenchImageOptions["ratio"] }))}><option>2:1</option><option>16:9</option><option>9:16</option><option>1:1</option></select></div><span className="script-wb-cost" title="具体费用由调用方在提交前确认"><Sparkles size={13} />{imageCost === undefined ? "待确认" : imageCost * batchSelection.length}</span>{pending?.type === "generate-assets" ? <button type="button" className="script-wb-button" onClick={cancelPending}>取消</button> : <button type="button" className="script-wb-button primary" disabled={steps.shots !== "done" || !batchSelection.length || !onGenerateAssets || !imageOptions.modelId} title={steps.shots !== "done" ? "请先补齐并确认全部镜头" : !onGenerateAssets ? "未接入批量资产生成能力" : !imageOptions.modelId ? "未提供可用图像模型" : "由调用方确认费用后提交"} onClick={generateAssets}>生成 ({batchSelection.length})</button>}</footer>
      </ModalShell>}
    </section>
  );
}
