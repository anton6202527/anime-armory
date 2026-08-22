import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import {
  ensureMedia,
  commitCanvasGeneration,
  mediaAllowRoot,
  mediaUrl,
  readSkillFile,
  readCanvasGenerationConfig,
} from "../api";
import { useI18n } from "../i18n";
import type {
  CanvasClip,
  CanvasAgentDispatchContext,
  CanvasAgentDispatchResult,
  CanvasGenerationConfig,
  CanvasGenerationKind,
  CanvasGenerationModel,
  CanvasGenerationProfile,
  LineKey,
} from "../types";
import { DecodedImage } from "../mediaPreview/DecodedImage";

export interface CanvasMediaDetailReference {
  id: string;
  label: string;
  url: string;
  role?: string;
  path?: string;
}

export interface CanvasMediaDetailState {
  kind: CanvasGenerationKind;
  targetSlot: string;
  /** Absolute work path selected by the clicked frame/video target. */
  targetOutputPath: string;
  title: string;
  subtitle?: string;
  prompt?: string;
  mediaUrl?: string;
  references: CanvasMediaDetailReference[];
  anchor: { x: number; y: number };
}

type ToolPanel = "reference" | "mark" | "effects" | "character" | "camera" | "model" | "mode" | "spec" | null;

const VIDEO_MODES = [
  ["text2video", "canvas.generationModeTextVideo"],
  ["project_route", "canvas.generationModeOmni"],
  ["image2video", "canvas.generationModeImageVideo"],
  ["frames2video", "canvas.generationModeFirstLast"],
  ["multiframe2video", "canvas.generationModeMultiFrame"],
  ["multimodal2video", "canvas.generationModeImageReference"],
  ["video2video", "canvas.generationModeFileVideo"],
] as const;

const IMAGE_MODES = [
  ["text2image", "canvas.generationModeTextImage"],
  ["image_reference", "canvas.generationModeImageReference"],
] as const;

const ASPECT_RATIOS = ["Auto", "16:9", "4:3", "1:1", "3:4", "9:16", "21:9"];
const VIDEO_RESOLUTIONS = ["480p", "720p", "1080p", "4K"];
const IMAGE_RESOLUTIONS = ["project", "1K", "2K", "4K"];
const MARKS = ["主体锁定", "构图锁定", "动作强化", "光线锁定"];
const EFFECTS = ["电影光晕", "粒子特效", "体积光", "速度拖影", "景深呼吸", "胶片颗粒"];
const CAMERA_R2_HOST = "pub-0bafc63084d743e78dbe9f72fc918988.r2.dev";

interface CameraMotionOption {
  id: string;
  nameZh: string;
  aliasesZh: string[];
  useWhen: string;
  promptTemplate: string;
  riskLevel: string;
  previewAbs?: string;
  animatedUrl?: string;
}

const CAMERA_MOTION_FALLBACKS: CameraMotionOption[] = [
  { id: "fixed_static", nameZh: "固定机位", aliasesZh: ["固定镜头", "无运镜"], useWhen: "稳定读取表演与画面信息。", promptTemplate: "镜头运动：固定机位。", riskLevel: "low" },
  { id: "dolly_in", nameZh: "镜头前推", aliasesZh: ["推进", "推近"], useWhen: "逼近、揭示或聚焦情绪。", promptTemplate: "镜头运动：推镜头。", riskLevel: "low" },
  { id: "dolly_out", nameZh: "镜头后移", aliasesZh: ["拉远", "后拉"], useWhen: "揭示环境关系或释放情绪。", promptTemplate: "镜头运动：拉镜头。", riskLevel: "low" },
  { id: "truck", nameZh: "横移镜头", aliasesZh: ["横移"], useWhen: "跟随横向行动或展示空间。", promptTemplate: "镜头运动：横移。", riskLevel: "medium" },
  { id: "orbit", nameZh: "环绕拍摄", aliasesZh: ["环绕"], useWhen: "强化主体与空间关系。", promptTemplate: "镜头运动：环绕。", riskLevel: "medium" },
  { id: "follow", nameZh: "跟随拍摄", aliasesZh: ["跟随"], useWhen: "保持运动主体处于视觉中心。", promptTemplate: "镜头运动：跟随。", riskLevel: "medium" },
  { id: "handheld", nameZh: "手持拍摄", aliasesZh: ["手持"], useWhen: "制造临场感与轻微不稳定。", promptTemplate: "镜头运动：手持。", riskLevel: "high" },
];

function record(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function textValue(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.map(textValue).filter(Boolean) : [];
}

function joinPortablePath(...parts: string[]): string {
  const first = parts.find(Boolean) ?? "";
  const separator = first.includes("\\") && !first.includes("/") ? "\\" : "/";
  return parts
    .filter(Boolean)
    .map((part, index) => index === 0
      ? part.replace(/[\\/]+$/, "")
      : part.replace(/^[\\/]+|[\\/]+$/g, ""))
    .join(separator);
}

function safeCameraAssetRel(value: unknown): string {
  const rel = textValue(value).replace(/\\/g, "/");
  if (!rel || rel.startsWith("/") || rel.split("/").some((part) => part === "..")) return "";
  return rel;
}

function safeAnimatedUrl(value: unknown): string {
  const raw = textValue(value);
  if (!raw) return "";
  try {
    const parsed = new URL(raw);
    return parsed.protocol === "https:" && parsed.hostname === CAMERA_R2_HOST ? parsed.toString() : "";
  } catch {
    return "";
  }
}

function parseCameraMotions(raw: string, repoRoot: string, line: LineKey): CameraMotionOption[] {
  const manifest = record(JSON.parse(raw));
  const moves = Array.isArray(manifest?.moves) ? manifest.moves : [];
  return moves.flatMap((value): CameraMotionOption[] => {
    const move = record(value);
    const media = record(move?.media);
    const remote = record(media?.remote);
    const id = textValue(move?.id);
    const nameZh = textValue(move?.name_zh);
    const animatedUrl = safeAnimatedUrl(remote?.url);
    if (!id || !nameZh || !animatedUrl) return [];
    const previewRel = safeCameraAssetRel(media?.preview);
    return [{
      id,
      nameZh,
      aliasesZh: stringList(move?.aliases_zh),
      useWhen: textValue(move?.use_when),
      promptTemplate: textValue(move?.prompt_template),
      riskLevel: textValue(move?.risk_level) || "medium",
      previewAbs: previewRel
        ? joinPortablePath(repoRoot, "skills", line, "references", "运镜", previewRel)
        : undefined,
      animatedUrl,
    }];
  });
}

function ComposerIcon({ name }: { name: "reference" | "mark" | "effects" | "character" | "camera" | "model" | "mode" | "language" | "tune" }) {
  const common = { className: "media-detail-tool-icon", viewBox: "0 0 24 24", "aria-hidden": true } as const;
  switch (name) {
    case "reference":
      return <svg {...common}><path d="M12 5v14M5 12h14" /></svg>;
    case "mark":
      return <svg {...common}><path d="M12 3.8v3.4M12 16.8v3.4M3.8 12h3.4M16.8 12h3.4" /><circle cx="12" cy="12" r="3.4" /><circle cx="12" cy="12" r=".8" /></svg>;
    case "effects":
      return <svg {...common}><path d="m12 3 .9 3.1A4.2 4.2 0 0 0 15.8 9l3.2 1-3.2 1a4.2 4.2 0 0 0-2.9 2.9L12 17l-.9-3.1A4.2 4.2 0 0 0 8.2 11L5 10l3.2-1a4.2 4.2 0 0 0 2.9-2.9Z" /><path d="m18.2 15 .4 1.4a2 2 0 0 0 1.4 1.4l1.4.4-1.4.4a2 2 0 0 0-1.4 1.4l-.4 1.4-.4-1.4a2 2 0 0 0-1.4-1.4l-1.4-.4 1.4-.4a2 2 0 0 0 1.4-1.4Z" /></svg>;
    case "character":
      return <svg {...common}><path d="M12 3.5 19 6.6v5.2c0 4.3-2.8 7.3-7 8.7-4.2-1.4-7-4.4-7-8.7V6.6Z" /><circle cx="12" cy="10" r="2.2" /><path d="M8.5 16c.7-1.7 1.9-2.6 3.5-2.6s2.8.9 3.5 2.6" /></svg>;
    case "camera":
      return <svg {...common}><path d="M4 8V5h3M17 5h3v3M20 16v3h-3M7 19H4v-3" /><rect x="7" y="8" width="7.5" height="8" rx="1.2" /><path d="m14.5 10 3-1.7v7.4l-3-1.7" /></svg>;
    case "model":
      return <svg {...common}><path d="M5 16V8M9.7 19V5M14.3 16V8M19 14v-4" /></svg>;
    case "mode":
      return <svg {...common}><rect x="4" y="5" width="16" height="14" rx="1.8" /><circle cx="9" cy="10" r="1.3" /><path d="m6.5 16 4-4 2.7 2.5 2.2-2 2.6 3.5" /></svg>;
    case "language":
      return <svg {...common}><path d="M4 6h10M9 3v3M6 6c.8 4 3.3 6.8 7 8.4M5 14c3.7-1.5 6.1-4.3 7-8" /><path d="m14 11 3 8M21 11l-3 8M15.3 16h4.4" /></svg>;
    case "tune":
      return <svg {...common}><path d="M4 7h4M12 7h8M4 12h9M17 12h3M4 17h2M10 17h10" /><circle cx="10" cy="7" r="2" /><circle cx="15" cy="12" r="2" /><circle cx="8" cy="17" r="2" /></svg>;
  }
}

function ChevronDownIcon() {
  return <svg className="canvas-generation-chevron" viewBox="0 0 12 12" aria-hidden="true"><path d="m3 4.5 3 3 3-3" /></svg>;
}

function SendIcon() {
  return <svg className="canvas-generation-send-icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M10 15.5v-11M5.8 8.7 10 4.5l4.2 4.2" /></svg>;
}

function AspectRatioIcon({ ratio, className = "" }: { ratio: string; className?: string }) {
  const size: Record<string, [number, number]> = {
    Auto: [10, 8],
    "16:9": [15, 8.5],
    "4:3": [13, 9.5],
    "1:1": [10, 10],
    "3:4": [8.5, 11.5],
    "9:16": [7.5, 13],
    "21:9": [17, 7.5],
  };
  const [width, height] = size[ratio] ?? size.Auto;
  return (
    <svg className={`canvas-aspect-ratio-icon ${className}`.trim()} viewBox="0 0 22 16" aria-hidden="true">
      <rect x={(22 - width) / 2} y={(16 - height) / 2} width={width} height={height} rx="1.25" />
    </svg>
  );
}

function projectRelative(root: string, value?: string): string | null {
  if (!value) return null;
  const normalizedRoot = root.replace(/\\/g, "/").replace(/\/$/, "");
  const normalizedValue = value.replace(/\\/g, "/");
  if (!normalizedValue.startsWith(`${normalizedRoot}/`)) return null;
  return normalizedValue.slice(normalizedRoot.length + 1);
}

function defaultConfig(
  kind: CanvasGenerationKind,
  profile: CanvasGenerationProfile | undefined,
  clip: CanvasClip,
  rootPath: string,
  references: CanvasMediaDetailReference[],
  prompt: string,
  targetSlot: string,
  targetOutputPath: string,
): CanvasGenerationConfig {
  const models = kind === "video" ? profile?.video_models : profile?.image_models;
  const model = kind === "video" ? profile?.default_video_model : profile?.default_image_model;
  const preferred = models?.find((item) => item.id === model) ?? models?.[0];
  const duration = Math.max(1, clip.duration ?? profile?.default_video_duration ?? 10);
  const referencePaths = references
    .map((reference) => projectRelative(rootPath, reference.path))
    .filter((item): item is string => Boolean(item))
    .filter((item) => item !== projectRelative(rootPath, targetOutputPath))
    .slice(0, kind === "video" ? 9 : 24);
  return {
    kind,
    target_slot: targetSlot,
    target_output_path: projectRelative(rootPath, targetOutputPath) ?? "",
    model: model ?? preferred?.id ?? "project-default",
    mode: kind === "video"
      ? (preferred?.modes.includes("project_route") ? "project_route" : preferred?.modes[0] ?? "project_route")
      : (preferred?.modes[0] ?? "text2image"),
    aspect_ratio: profile?.default_aspect_ratio ?? "Auto",
    resolution: kind === "video" ? profile?.default_resolution ?? "720p" : "project",
    duration,
    audio_enabled: false,
    count: 1,
    reference_paths: referencePaths,
    marks: [],
    effects: [],
    camera_motion: "none",
    prompt_language: "project",
    prompt_override: prompt,
  };
}

function generationSkill(line: LineKey, kind: CanvasGenerationKind): string {
  if (line === "n2d") return kind === "video" ? "n2d-video" : "n2d-image";
  if (line === "comic") return "comic-image";
  if (line === "mv") return kind === "video" ? "mv-video" : "mv-image";
  if (line === "ad") return kind === "video" ? "ad-video" : "ad-image";
  return line;
}

function buildGenerationPrompt(
  line: LineKey,
  rootPath: string,
  episode: string,
  clip: CanvasClip,
  config: CanvasGenerationConfig,
  model: CanvasGenerationModel | undefined,
  cameraMotion?: CameraMotionOption,
  task?: {
    jobId: string;
    contentHash: string;
    inputHash: string;
    nodeInputHash: string;
    targetSlot: string;
    targetOutputPath: string;
    candidateOutputPath: string;
  },
): string {
  const skill = generationSkill(line, config.kind);
  const referenceLines = config.reference_paths.length
    ? config.reference_paths.map((item) => `- ${item}`).join("\n")
    : "- 无额外参考图；按节点现有首帧/项目定妆合同执行";
  return [
    `请使用 ${skill}，只处理当前工作流画布中的这个节点并完成真实生成：`,
    `作品目录：${rootPath}`,
    `集/话：${episode}`,
    `节点：${clip.id}${clip.number != null ? `（${clip.number}）` : ""} · ${clip.label}`,
    ...(task ? [
      `画布 job_id：${task.jobId}`,
      `唯一内容哈希：${task.contentHash}`,
      `当前节点 input_hash：${task.inputHash}`,
      `最终节点 node_input_hash：${task.nodeInputHash}`,
      `稳定 target_slot：${task.targetSlot}`,
      `job-scoped candidate（唯一可写）：${task.candidateOutputPath}`,
      `stable target（只读，禁止 agent 直写）：${task.targetOutputPath}`,
    ] : []),
    `媒体类型：${config.kind === "video" ? "视频" : "图片"}`,
    "",
    "本次由用户在画布生成按钮明确提交的参数：",
    `- 模型/后端：${model?.label ?? config.model}${model?.channel ? `（${model.channel}）` : ""}`,
    `- 生成模式：${config.mode}`,
    `- 比例：${config.aspect_ratio}`,
    `- 清晰度：${config.resolution}`,
    ...(config.kind === "video" ? [
      `- 目标时长：${config.duration}s`,
      `- 生成音频：${config.audio_enabled ? "开启" : "关闭"}`,
      `- 运镜：${cameraMotion ? `${cameraMotion.nameZh}（${cameraMotion.id}）` : config.camera_motion}`,
      ...(cameraMotion?.promptTemplate ? [`- 运镜模板：${cameraMotion.promptTemplate}`] : []),
    ] : []),
    `- 生成数量：${config.count}`,
    `- prompt 语言：${config.prompt_language}`,
    `- 标记：${config.marks.join("、") || "无"}`,
    `- 特效：${config.effects.join("、") || "无"}`,
    "- 参考素材：",
    referenceLines,
    "",
    "节点 prompt：",
    config.prompt_override || clip.prompt || "（沿用节点/任务包 prompt）",
    "",
    "执行要求：先读取 _进度.md、_设置.md、本集任务包、适配层、gate 与当前 canvas_state；不得静默换后端。超出模型单段上限时按既有 duration_segment_relay/多关键帧合同拆段；项目要求无声时保持无声。普通选择采用推荐最优解自行继续。",
    `- 每个候选登记 provenance 并跑新鲜 QC；block 只返工当前候选。采用输出必须用真实文件字节计算 SHA-256，并实际运行媒体 probe。`,
    ...(task ? [
      `- 只可写 candidate=${task.candidateOutputPath}，禁止写 stable=${task.targetOutputPath}。对 candidate 真实字节算 SHA-256 并实际 probe；桌面主进程复核当前 task/content/input/node_input/target/QC 后才会同卷原子晋升。`,
      `- 原子写 生产数据/canvas_task_candidate_qc_${task.jobId}.json：kind=anime_armory_canvas_task_candidate_qc，version=1，episode=${episode}，job_id=${task.jobId}，node_id=${clip.id}，generation_kind=${config.kind}，target_slot=${task.targetSlot}，target_output_path=${task.targetOutputPath}，candidate_output_path=${task.candidateOutputPath}，content_hash=${task.contentHash}，input_hash=${task.inputHash}，node_input_hash=${task.nodeInputHash}，candidate_sha256/qa_blocks=0/verdict=pass/probe_passed=true。`,
      `- 再原子写 生产数据/canvas_task_candidate_receipt_${task.jobId}.json：kind=anime_armory_canvas_task_candidate_receipt，version=1，根对象绑定同一组字段，并带 qa_receipt_path/qa_receipt_sha256/qa_blocks=0/verdict=pass/probe_passed=true。不要写 task/node 正式 receipt 或 QC；它们由主进程晋升后生成。`,
      `- 图片触发 B14：技术 QC 后必须把 candidate 当前像素展示给用户；只有用户对 candidate_sha256 显式签收，且独立证据 kind=anime_armory_canvas_candidate_human_acceptance 精确绑定 job/node/generation_kind/target/candidate/content/input/node_input/current SHA、具名 reviewer、带时区 accepted_at 与 confirmation={kind:"explicit_current_pixels_acceptance",accepted_current_pixels:true}，并把文件路径/SHA 写进 candidate receipt 的 human_acceptance_path/human_acceptance_sha256，主进程才会晋升。技术执行者不得代签或伪造 human。视频无签收仅 machine_complete，不等于 accepted。`,
    ] : []),
    "- 内容哈希或任务 input_hash 变化后不得覆盖新修订。完成后回写项目进度与必要产物；终端文字不算 receipt，machine_complete 不算人工验收。",
  ].join("\n");
}

export function CanvasMediaDetailDialog(props: {
  detail: CanvasMediaDetailState;
  clip: CanvasClip;
  line: LineKey;
  repoRoot: string;
  rootPath: string;
  episode: string;
  profile?: CanvasGenerationProfile;
  expectedContentHash?: string;
  onClose: () => void;
  onGeneratePrompt?: (prompt: string, task?: CanvasAgentDispatchContext) => Promise<CanvasAgentDispatchResult>;
}) {
  const { detail, clip, line, repoRoot, rootPath, episode, profile, expectedContentHash, onClose, onGeneratePrompt } = props;
  const { t } = useI18n();
  const references = useMemo<CanvasMediaDetailReference[]>(
    () => detail.references.length
      ? detail.references
      : detail.mediaUrl
        ? [{ id: "current-media", label: detail.title, url: detail.mediaUrl }]
        : [],
    [detail.mediaUrl, detail.references, detail.title],
  );
  const defaults = useMemo(
    () => defaultConfig(
      detail.kind, profile, clip, rootPath, references, detail.prompt ?? "",
      detail.targetSlot, detail.targetOutputPath,
    ),
    [clip, detail.kind, detail.prompt, detail.targetOutputPath, detail.targetSlot, profile, references, rootPath],
  );
  const [draft, setDraft] = useState<CanvasGenerationConfig>(defaults);
  const [loaded, setLoaded] = useState(false);
  const [panel, setPanel] = useState<ToolPanel>(null);
  const [status, setStatus] = useState("");
  const [sending, setSending] = useState(false);
  const [cameraMotions, setCameraMotions] = useState<CameraMotionOption[]>(CAMERA_MOTION_FALLBACKS);
  const [cameraPreviewId, setCameraPreviewId] = useState<string | null>(null);
  const [cameraMediaReady, setCameraMediaReady] = useState(false);

  useEffect(() => {
    let alive = true;
    if (detail.kind !== "video" || !repoRoot) return;
    setCameraMotions(CAMERA_MOTION_FALLBACKS);
    setCameraMediaReady(false);
    Promise.all([
      readSkillFile(repoRoot, line, "references/运镜/manifest.json"),
      ensureMedia().then(() => mediaAllowRoot(repoRoot)),
    ])
      .then(([raw]) => {
        if (!alive) return;
        const parsed = parseCameraMotions(raw, repoRoot, line);
        if (parsed.length) setCameraMotions(parsed);
        setCameraMediaReady(true);
      })
      .catch(() => {
        if (alive) setCameraMediaReady(false);
      });
    return () => { alive = false; };
  }, [detail.kind, line, repoRoot]);

  useEffect(() => {
    let alive = true;
    setLoaded(false);
    setStatus("");
    readCanvasGenerationConfig(
      rootPath,
      episode,
      clip.id,
      detail.kind,
      detail.targetSlot,
      defaults.target_output_path,
    )
      .then((saved) => {
        if (!alive) return;
        const merged = saved ? { ...defaults, ...saved, prompt_override: saved.prompt_override || defaults.prompt_override } : defaults;
        setDraft({
          ...merged,
          target_slot: detail.targetSlot,
          target_output_path: defaults.target_output_path,
          reference_paths: merged.reference_paths.filter((item) => item !== defaults.target_output_path),
        });
      })
      .catch(() => alive && setDraft(defaults))
      .finally(() => alive && setLoaded(true));
    return () => { alive = false; };
  }, [clip.id, defaults, detail.kind, detail.targetSlot, episode, rootPath]);

  function change(updater: (current: CanvasGenerationConfig) => CanvasGenerationConfig) {
    setDraft(updater);
    setStatus("");
  }

  const models = detail.kind === "video" ? profile?.video_models ?? [] : profile?.image_models ?? [];
  const selectedModel = models.find((model) => model.id === draft.model) ?? models[0];
  const modelModes = selectedModel?.modes ?? [];
  const modeOptions = detail.kind === "video" ? VIDEO_MODES : IMAGE_MODES;
  const selectedMode = modeOptions.find(([value]) => value === draft.mode);
  const selectedModeLabel = selectedMode ? t(selectedMode[1]) : draft.mode;
  const audioLocked = detail.kind !== "video" || /无声|关闭|discard|none/i.test(profile?.audio_policy ?? "");
  const durationMin = selectedModel?.min_duration ?? 1;
  const modelDurationMax = selectedModel?.max_duration ?? 15;
  const durationMax = Math.max(modelDurationMax, Math.ceil(clip.duration ?? draft.duration));
  const resolutionOptions = detail.kind === "video" ? VIDEO_RESOLUTIONS : IMAGE_RESOLUTIONS;
  const selectedReferences = new Set(draft.reference_paths);
  const visibleReferences = references.filter((reference) => {
    const relative = projectRelative(rootPath, reference.path);
    return relative ? selectedReferences.has(relative) : true;
  });
  const characterReferences = references.filter((reference) => /角色|人物|character|char[_-]?\d/i.test(`${reference.role ?? ""} ${reference.label}`));
  const selectedCameraMotion = cameraMotions.find((motion) =>
    motion.id === draft.camera_motion
      || motion.nameZh === draft.camera_motion
      || motion.aliasesZh.includes(draft.camera_motion),
  );

  function togglePanel(next: Exclude<ToolPanel, null>) {
    setPanel((current) => current === next ? null : next);
  }

  function toggleListValue(key: "marks" | "effects", value: string) {
    change((current) => {
      const list = current[key];
      return { ...current, [key]: list.includes(value) ? list.filter((item) => item !== value) : [...list, value] };
    });
  }

  function toggleReference(reference: CanvasMediaDetailReference) {
    const relative = projectRelative(rootPath, reference.path);
    if (!relative) return;
    change((current) => ({
      ...current,
      reference_paths: current.reference_paths.includes(relative)
        ? current.reference_paths.filter((item) => item !== relative)
        : [...current.reference_paths, relative].slice(0, detail.kind === "video" ? 9 : 24),
    }));
  }

  function chooseModel(model: CanvasGenerationModel) {
    if (!model.available) return;
    change((current) => {
      const nextMode = model.modes.includes(current.mode)
        ? current.mode
        : model.modes.includes("project_route") ? "project_route" : model.modes[0] ?? current.mode;
      const nextResolution = model.resolutions.length && !model.resolutions.includes(current.resolution)
        ? model.resolutions.includes(profile?.default_resolution ?? "")
          ? profile!.default_resolution
          : model.resolutions[0]
        : current.resolution;
      return {
        ...current,
        model: model.id,
        mode: nextMode,
        resolution: nextResolution,
        duration: Math.min(current.duration, Math.max(model.max_duration ?? current.duration, clip.duration ?? 0)),
        audio_enabled: current.audio_enabled && model.native_audio && !audioLocked,
      };
    });
    setPanel(null);
  }

  async function generate() {
    if (!onGeneratePrompt || sending) return;
    if (!expectedContentHash) {
      setStatus(t("canvas.productionUnavailable"));
      return;
    }
    setSending(true);
    setStatus(t("canvas.generationSending"));
    try {
      const committed = await commitCanvasGeneration(
        rootPath,
        episode,
        line,
        clip.id,
        detail.targetSlot,
        defaults.target_output_path,
        draft,
        expectedContentHash,
      );
      setDraft(committed.config);
      if (!committed.task.created && committed.task.task_status !== "submitted") {
        setStatus(committed.task.task_status === "succeeded"
          ? t("operation.canvasTaskAlreadyComplete")
          : t("canvas.generationTaskSubmitted", { id: committed.task.job_id.slice(0, 8) }));
        return;
      }
      const dispatch = await onGeneratePrompt(buildGenerationPrompt(
        line,
        rootPath,
        episode,
        clip,
        committed.config,
        selectedModel,
        selectedCameraMotion,
        {
          jobId: committed.task.job_id,
          contentHash: committed.task.content_hash,
          inputHash: committed.task.input_hash,
          nodeInputHash: committed.task.node_input_hash ?? committed.task.input_hash,
          targetSlot: committed.task.target_slot ?? detail.targetSlot,
          targetOutputPath: committed.task.target_output_path ?? defaults.target_output_path,
          candidateOutputPath: committed.task.candidate_output_path ?? "",
        },
      ), { root: rootPath, episode, job_id: committed.task.job_id });
      if (dispatch === "rejected") {
        throw new Error(t("operation.agentDispatchFailed"));
      }
      setStatus(dispatch === "succeeded"
        ? t("operation.canvasTaskAlreadyComplete")
        : t("canvas.generationTaskSubmitted", { id: committed.task.job_id.slice(0, 8) }));
    } catch (error) {
      setStatus(t("canvas.generationSaveFailed", { error: String(error) }));
    } finally {
      setSending(false);
    }
  }

  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const width = Math.min(1040, Math.max(700, viewportWidth - 120));
  const height = Math.min(540, Math.max(420, viewportHeight - 170));
  const cardStyle: CSSProperties = {
    width,
    height,
    maxHeight: height,
    left: Math.max(24, (viewportWidth - width) / 2),
    top: Math.max(24, (viewportHeight - height) / 2),
  };

  const renderReferencePicker = (items: CanvasMediaDetailReference[]) => (
    <div className="canvas-generation-reference-picker">
      {items.length ? items.map((reference) => {
        const relative = projectRelative(rootPath, reference.path);
        const selected = relative ? selectedReferences.has(relative) : false;
        return (
          <button
            type="button"
            className={selected ? "selected" : ""}
            key={reference.id}
            disabled={!relative}
            onClick={() => toggleReference(reference)}
          >
            <DecodedImage src={reference.url} alt={reference.label} maxDecodeDimension={256} />
            <span>{reference.label}</span>
            {selected && <b>✓</b>}
          </button>
        );
      }) : <div className="canvas-generation-empty">{t("canvas.generationNoReferences")}</div>}
    </div>
  );

  return createPortal(
    <div className="canvas-media-detail-backdrop" role="dialog" aria-modal="true" onPointerDown={(event) => event.stopPropagation()} onClick={onClose}>
      <div className="canvas-media-detail-card" style={cardStyle} onPointerDown={(event) => event.stopPropagation()} onClick={(event) => event.stopPropagation()}>
        <div className="canvas-media-detail-head">
          <div className="canvas-media-detail-actions">
            <button type="button" className={panel === "reference" ? "canvas-media-detail-pill active" : "canvas-media-detail-pill"} onClick={() => togglePanel("reference")}><ComposerIcon name="reference" />{t("canvas.mediaDetailReference")}</button>
            <button type="button" className={panel === "mark" ? "canvas-media-detail-pill active" : "canvas-media-detail-pill"} onClick={() => togglePanel("mark")}><ComposerIcon name="mark" />{t("canvas.mediaDetailMark")}</button>
            <button type="button" className={panel === "effects" ? "canvas-media-detail-pill active" : "canvas-media-detail-pill"} onClick={() => togglePanel("effects")}><ComposerIcon name="effects" />{t("canvas.mediaDetailEffects")}</button>
            <button type="button" className={panel === "character" ? "canvas-media-detail-pill active" : "canvas-media-detail-pill"} onClick={() => togglePanel("character")}><ComposerIcon name="character" />{t("canvas.mediaDetailCharacterLibrary")}</button>
            {detail.kind === "video" && <button type="button" className={panel === "camera" ? "canvas-media-detail-pill active" : "canvas-media-detail-pill"} onClick={() => togglePanel("camera")}><ComposerIcon name="camera" />{t("canvas.mediaDetailCameraMove")}</button>}
          </div>
        </div>

        {panel && !["model", "mode", "spec"].includes(panel) && (
          <div className={panel === "camera" ? "canvas-generation-tool-popover camera" : "canvas-generation-tool-popover"}>
            {panel === "reference" && renderReferencePicker(references)}
            {panel === "character" && renderReferencePicker(characterReferences.length ? characterReferences : references)}
            {panel === "mark" && <div className="canvas-generation-chip-grid">{MARKS.map((item) => <button type="button" className={draft.marks.includes(item) ? "selected" : ""} key={item} onClick={() => toggleListValue("marks", item)}>{item}</button>)}</div>}
            {panel === "effects" && <div className="canvas-generation-chip-grid">{EFFECTS.map((item) => <button type="button" className={draft.effects.includes(item) ? "selected" : ""} key={item} onClick={() => toggleListValue("effects", item)}>{item}</button>)}</div>}
            {panel === "camera" && <div className="canvas-camera-motion-grid">
              <button type="button" title={t("canvas.generationCameraKeepPrompt")} className={draft.camera_motion === "none" ? "canvas-camera-motion-card none selected" : "canvas-camera-motion-card none"} onClick={() => change((current) => ({ ...current, camera_motion: "none" }))}>
                <span className="canvas-camera-motion-preview">
                  <span className="canvas-camera-motion-none-icon"><ComposerIcon name="camera" /></span>
                  <b className="canvas-camera-motion-title">{t("canvas.generationCameraNone")}</b>
                </span>
              </button>
              {cameraMotions.map((motion) => {
                const selected = motion.id === draft.camera_motion || motion.nameZh === draft.camera_motion || motion.aliasesZh.includes(draft.camera_motion);
                const animated = selected || cameraPreviewId === motion.id;
                const preview = animated && motion.animatedUrl
                  ? motion.animatedUrl
                  : cameraMediaReady && motion.previewAbs ? mediaUrl(motion.previewAbs) : "";
                return <button
                  type="button"
                  className={selected ? "canvas-camera-motion-card selected" : "canvas-camera-motion-card"}
                  key={motion.id}
                  title={[motion.nameZh, motion.useWhen, motion.promptTemplate].filter(Boolean).join("\n")}
                  onMouseEnter={() => setCameraPreviewId(motion.id)}
                  onMouseLeave={() => setCameraPreviewId((current) => current === motion.id ? null : current)}
                  onFocus={() => setCameraPreviewId(motion.id)}
                  onBlur={() => setCameraPreviewId((current) => current === motion.id ? null : current)}
                  onClick={() => change((current) => ({ ...current, camera_motion: motion.id }))}
                >
                  <span className="canvas-camera-motion-preview">
                    {preview ? <img src={preview} alt="" loading="lazy" /> : <ComposerIcon name="camera" />}
                    <b className="canvas-camera-motion-title">{motion.nameZh}</b>
                    {motion.animatedUrl && <em>{animated ? "WEBP" : "▶"}</em>}
                  </span>
                </button>;
              })}
            </div>}
          </div>
        )}

        {visibleReferences.length > 0 && <div className="canvas-media-detail-refs">{visibleReferences.slice(0, 14).map((reference, index) => <button type="button" className="canvas-media-detail-ref selected" key={reference.id} title={reference.label} onClick={() => toggleReference(reference)}><DecodedImage src={reference.url} alt={reference.label} maxDecodeDimension={256} /><span className="canvas-media-detail-ref-index">{index + 1}</span>{reference.role && <span className="canvas-media-detail-ref-role">{reference.role}</span>}</button>)}</div>}

        <div className="canvas-media-detail-text">
          <textarea
            value={draft.prompt_override}
            aria-label={t("canvas.generationPrompt")}
            placeholder={t("canvas.mediaDetailNoPrompt")}
            onChange={(event) => change((current) => ({ ...current, prompt_override: event.target.value }))}
          />
        </div>

        <div className="canvas-generation-composer">
          {panel === "model" && <div className="canvas-generation-popover canvas-generation-model-menu">{models.map((model) => <button type="button" className={model.id === draft.model ? "canvas-generation-model active" : "canvas-generation-model"} key={model.id} disabled={!model.available} onClick={() => chooseModel(model)}><span className="canvas-generation-model-icon"><ComposerIcon name="model" /></span><span><b>{model.label}{model.premium && <em>◆</em>}</b><small>{model.channel || model.description || t("canvas.generationProjectAdapter")}</small></span>{model.max_duration && <i>{model.max_duration}s</i>}</button>)}</div>}
          {panel === "mode" && <div className="canvas-generation-popover canvas-generation-mode-menu"><div className="canvas-generation-popover-title">{t("canvas.generationModeTitle")}</div>{modeOptions.map(([value, key]) => { const enabled = modelModes.includes(value); return <button type="button" className={draft.mode === value ? "active" : ""} key={value} disabled={!enabled} onClick={() => { change((current) => ({ ...current, mode: value })); setPanel(null); }}><ComposerIcon name="mode" />{t(key)}{draft.mode === value && <b>✓</b>}</button>; })}</div>}
          {panel === "spec" && <div className="canvas-generation-popover canvas-generation-spec-menu">
            <section><h4>{t("canvas.generationAspect")}</h4><div className="canvas-generation-option-grid ratios">{ASPECT_RATIOS.map((value) => <button type="button" className={draft.aspect_ratio === value ? "active" : ""} key={value} onClick={() => change((current) => ({ ...current, aspect_ratio: value }))}><AspectRatioIcon ratio={value} />{value}</button>)}</div></section>
            <section><h4>{t("canvas.generationResolution")}</h4><div className="canvas-generation-option-grid resolutions">{resolutionOptions.map((value) => { const supported = !selectedModel?.resolutions.length || selectedModel.resolutions.includes(value) || value === "project"; return <button type="button" className={draft.resolution === value ? "active" : ""} key={value} disabled={!supported} onClick={() => change((current) => ({ ...current, resolution: value }))}>{value === "project" ? t("canvas.generationProjectDefault") : value}</button>; })}</div></section>
            {detail.kind === "video" && <><section><h4>{t("canvas.generationDuration")}</h4><div className="canvas-generation-range"><input type="range" min={durationMin} max={durationMax} step="0.5" value={Math.min(durationMax, Math.max(durationMin, draft.duration))} onChange={(event) => change((current) => ({ ...current, duration: Number(event.target.value) }))} /><output>{draft.duration}s</output></div>{draft.duration > modelDurationMax && <small>{t("canvas.generationRelayHint", { max: modelDurationMax })}</small>}</section><section><h4>{t("canvas.generationAudio")}</h4><div className="canvas-generation-segmented"><button type="button" className={draft.audio_enabled ? "active" : ""} disabled={audioLocked || !selectedModel?.native_audio} onClick={() => change((current) => ({ ...current, audio_enabled: true }))}>{t("canvas.generationOn")}</button><button type="button" className={!draft.audio_enabled ? "active" : ""} onClick={() => change((current) => ({ ...current, audio_enabled: false }))}>{t("canvas.generationOff")}</button></div>{audioLocked && <small>{t("canvas.generationAudioLocked", { policy: profile?.audio_policy ?? "" })}</small>}</section></>}
            <section><h4>{t("canvas.generationCount")}</h4><div className="canvas-generation-segmented">{([1, 2, 4] as const).map((count) => <button type="button" className={draft.count === count ? "active" : ""} key={count} onClick={() => change((current) => ({ ...current, count }))}>{count}{t("canvas.generationCountUnit")}</button>)}</div></section>
          </div>}

          <button type="button" className={panel === "model" ? "canvas-generation-trigger active" : "canvas-generation-trigger"} onClick={() => togglePanel("model")}><ComposerIcon name="model" /><span>{selectedModel?.label ?? t("canvas.generationProjectDefault")}</span><ChevronDownIcon /></button>
          <button type="button" className={panel === "mode" ? "canvas-generation-trigger active" : "canvas-generation-trigger"} onClick={() => togglePanel("mode")}><ComposerIcon name="mode" /><span>{selectedModeLabel}</span><ChevronDownIcon /></button>
          <button type="button" className={panel === "spec" ? "canvas-generation-trigger active" : "canvas-generation-trigger"} onClick={() => togglePanel("spec")}><AspectRatioIcon ratio={draft.aspect_ratio} className="canvas-generation-spec-icon" /><span>{draft.aspect_ratio} · {draft.resolution}{detail.kind === "video" ? ` · ${draft.duration}s` : ""} · {draft.count}{t("canvas.generationCountUnit")}</span><ChevronDownIcon /></button>
          <span className="canvas-generation-spacer" />
          {status && <span className="canvas-generation-status" title={status}>{status}</span>}
          <button type="button" className="canvas-generation-icon-btn" title={t("canvas.generationPromptLanguage")} onClick={() => change((current) => ({ ...current, prompt_language: current.prompt_language === "project" ? "zh" : current.prompt_language === "zh" ? "en" : "project" }))}><ComposerIcon name="language" /><small>{draft.prompt_language === "project" ? "A" : draft.prompt_language.toUpperCase()}</small></button>
          <button type="button" className={panel === "spec" ? "canvas-generation-icon-btn active" : "canvas-generation-icon-btn"} title={t("canvas.generationSettings")} onClick={() => togglePanel("spec")}><ComposerIcon name="tune" /></button>
          <span className="canvas-generation-cost">⚡{draft.count}</span>
          <button type="button" className="canvas-generation-send" aria-label={t("canvas.generationGenerate")} title={t("canvas.generationGenerate")} disabled={!loaded || sending || !onGeneratePrompt || !selectedModel?.available || !expectedContentHash} onClick={generate}>{sending ? "…" : <SendIcon />}</button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
