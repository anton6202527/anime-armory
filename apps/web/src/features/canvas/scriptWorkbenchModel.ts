export const SCRIPT_WORKBENCH_SCHEMA = "n2d-script-workbench/v1" as const;
export const SCRIPT_WORKBENCH_SKILL = "n2d-script-workbench" as const;

export const SCRIPT_WORKBENCH_DEFAULT_TITLE = "未命名故事脚本";
export const SCRIPT_WORKBENCH_DEFAULT_STYLE = "电影级画面，主体一致，细节清晰";

export const SCRIPT_WORKBENCH_STEP_STATES = ["pending", "active", "done"] as const;
export const SCRIPT_WORKBENCH_ASSET_KINDS = ["character", "scene", "prop"] as const;
export const SCRIPT_WORKBENCH_ASSET_STATUSES = ["pending", "generating", "ready", "failed"] as const;
export const SCRIPT_WORKBENCH_ASSET_SOURCES = ["none", "ai", "canvas", "upload"] as const;

export type ScriptWorkbenchStepState = (typeof SCRIPT_WORKBENCH_STEP_STATES)[number];
export type ScriptWorkbenchAssetKind = (typeof SCRIPT_WORKBENCH_ASSET_KINDS)[number];
export type ScriptWorkbenchAssetStatus = (typeof SCRIPT_WORKBENCH_ASSET_STATUSES)[number];
export type ScriptWorkbenchAssetSource = (typeof SCRIPT_WORKBENCH_ASSET_SOURCES)[number];

export type ScriptWorkbenchSteps = {
  shots: ScriptWorkbenchStepState;
  assets: ScriptWorkbenchStepState;
  prompts: ScriptWorkbenchStepState;
};

export type ScriptWorkbenchShot = {
  id: string;
  duration: number;
  visual: string;
  scale: string;
  lighting: string;
  dialogue: string;
  sound: string;
  camera: string;
  final_prompt: string;
  color: string;
};

/**
 * The v1 contract requires the first seven fields. The optional fields are
 * durable canvas evidence used to prove that a `ready` asset has a real image.
 */
export type ScriptWorkbenchAsset = {
  id: string;
  kind: ScriptWorkbenchAssetKind;
  name: string;
  description: string;
  prompt: string;
  status: ScriptWorkbenchAssetStatus;
  source: ScriptWorkbenchAssetSource;
  attachmentId?: string;
  nodeId?: string;
  imageUrl?: string;
  mimeType?: string;
  error?: string;
};

export type ScriptWorkbenchDocument = {
  schema: typeof SCRIPT_WORKBENCH_SCHEMA;
  skill: typeof SCRIPT_WORKBENCH_SKILL;
  title: string;
  global_style: string;
  /** Once any final prompt is composed, LibTV keeps the global style locked. */
  style_locked: boolean;
  steps: ScriptWorkbenchSteps;
  shots: ScriptWorkbenchShot[];
  assets: ScriptWorkbenchAsset[];
};

export type ScriptWorkbenchShotPatch = Partial<Omit<ScriptWorkbenchShot, "id">>;
type ScriptWorkbenchAssetEvidenceKey =
  | "attachmentId"
  | "nodeId"
  | "imageUrl"
  | "mimeType"
  | "error";
export type ScriptWorkbenchAssetPatch = Partial<
  Omit<ScriptWorkbenchAsset, "id" | ScriptWorkbenchAssetEvidenceKey>
> & {
  /** Pass null to explicitly clear optional evidence with exactOptionalPropertyTypes enabled. */
  attachmentId?: string | null;
  nodeId?: string | null;
  imageUrl?: string | null;
  mimeType?: string | null;
  error?: string | null;
};

export type ScriptWorkbenchValidationIssue = {
  path: string;
  message: string;
};

export type ScriptWorkbenchParseResult =
  | { ok: true; document: ScriptWorkbenchDocument }
  | { ok: false; error: ScriptWorkbenchModelParseError };

const SHOT_PROMPT_INPUT_FIELDS = [
  "duration",
  "visual",
  "scale",
  "lighting",
  "dialogue",
  "sound",
  "camera",
] as const satisfies ReadonlyArray<keyof ScriptWorkbenchShot>;

const DEFAULT_STEP_STATE: ScriptWorkbenchSteps = {
  shots: "active",
  assets: "pending",
  prompts: "pending",
};

const MAX_ID_LENGTH = 180;
const MAX_SHORT_TEXT_LENGTH = 2_000;
const MAX_LONG_TEXT_LENGTH = 60_000;

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isOneOf<const T extends readonly string[]>(value: unknown, values: T): value is T[number] {
  return typeof value === "string" && values.includes(value as T[number]);
}

function cleanString(value: unknown, fallback = "", maxLength = MAX_LONG_TEXT_LENGTH): string {
  if (typeof value !== "string" && typeof value !== "number" && typeof value !== "boolean") {
    return fallback;
  }
  const cleaned = String(value).replace(/\u0000/g, "").trim();
  return cleaned ? cleaned.slice(0, maxLength) : fallback;
}

function cleanOptionalString(value: unknown, maxLength = MAX_LONG_TEXT_LENGTH): string | undefined {
  const cleaned = cleanString(value, "", maxLength);
  return cleaned || undefined;
}

function positiveDuration(value: unknown): number {
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return 5;
  return Math.max(5, Math.min(15, Math.round(parsed)));
}

function stableHash(value: string): string {
  // FNV-1a is deterministic across browser/Node and does not require async crypto.
  let hash = 0x811c9dc5;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function createStableScriptWorkbenchId(prefix: "shot" | "asset", index: number, seed: string): string {
  return `${prefix}-${stableHash(`${prefix}:${index}:${seed}`)}`;
}

function uniqueId(candidate: string, fallback: string, seen: Set<string>): string {
  const base = cleanString(candidate, fallback, MAX_ID_LENGTH) || fallback;
  if (!seen.has(base)) {
    seen.add(base);
    return base;
  }
  let suffix = 2;
  while (seen.has(`${base}-${suffix}`)) suffix += 1;
  const result = `${base}-${suffix}`;
  seen.add(result);
  return result;
}

function normalizeShot(raw: UnknownRecord, index: number, seen: Set<string>): ScriptWorkbenchShot {
  const visual = cleanString(raw.visual ?? raw.description, "", MAX_LONG_TEXT_LENGTH);
  const fallbackId = createStableScriptWorkbenchId("shot", index, visual);
  return {
    id: uniqueId(cleanString(raw.id, "", MAX_ID_LENGTH), fallbackId, seen),
    duration: positiveDuration(raw.duration),
    visual,
    scale: cleanString(raw.scale, "中景", MAX_SHORT_TEXT_LENGTH),
    lighting: cleanString(raw.lighting, "自然光，电影感", MAX_LONG_TEXT_LENGTH),
    dialogue: cleanString(raw.dialogue, "", MAX_LONG_TEXT_LENGTH),
    sound: cleanString(raw.sound, "环境底噪", MAX_LONG_TEXT_LENGTH),
    camera: cleanString(raw.camera, "固定机位", MAX_LONG_TEXT_LENGTH),
    final_prompt: cleanString(raw.final_prompt ?? raw.finalPrompt, "", MAX_LONG_TEXT_LENGTH),
    color: cleanString(raw.color, "", MAX_SHORT_TEXT_LENGTH),
  };
}

function normalizeAsset(raw: UnknownRecord, index: number, seen: Set<string>): ScriptWorkbenchAsset {
  const kind = isOneOf(raw.kind, SCRIPT_WORKBENCH_ASSET_KINDS) ? raw.kind : "character";
  const name = cleanString(raw.name, "", MAX_SHORT_TEXT_LENGTH);
  const fallbackId = createStableScriptWorkbenchId("asset", index, `${kind}:${name}`);
  const source = isOneOf(raw.source, SCRIPT_WORKBENCH_ASSET_SOURCES) ? raw.source : "none";
  const requestedStatus = isOneOf(raw.status, SCRIPT_WORKBENCH_ASSET_STATUSES) ? raw.status : "pending";

  const attachmentId = cleanOptionalString(raw.attachmentId ?? raw.attachment_id, MAX_ID_LENGTH);
  const nodeId = cleanOptionalString(raw.nodeId ?? raw.node_id, MAX_ID_LENGTH);
  const imageUrl = cleanOptionalString(raw.imageUrl ?? raw.image_url, MAX_LONG_TEXT_LENGTH);
  const mimeType = cleanOptionalString(raw.mimeType ?? raw.mime_type, MAX_SHORT_TEXT_LENGTH);
  const error = cleanOptionalString(raw.error ?? raw.generationError, MAX_LONG_TEXT_LENGTH);

  const result: ScriptWorkbenchAsset = {
    id: uniqueId(cleanString(raw.id, "", MAX_ID_LENGTH), fallbackId, seen),
    kind,
    name,
    description: cleanString(raw.description, "", MAX_LONG_TEXT_LENGTH),
    prompt: cleanString(raw.prompt, "", MAX_LONG_TEXT_LENGTH),
    status: requestedStatus,
    source,
  };
  if (source !== "none") {
    if (attachmentId !== undefined) result.attachmentId = attachmentId;
    if (nodeId !== undefined) result.nodeId = nodeId;
    if (imageUrl !== undefined) result.imageUrl = imageUrl;
    if (mimeType !== undefined) result.mimeType = mimeType;
  }
  if (error !== undefined) result.error = error;

  if (result.status === "ready" && !hasRealScriptWorkbenchAssetSource(result)) {
    result.status = "pending";
  }
  return result;
}

function isShotComplete(shot: ScriptWorkbenchShot): boolean {
  return (
    Boolean(shot.id.trim()) &&
    Number.isFinite(shot.duration) &&
    shot.duration >= 5 &&
    shot.duration <= 15 &&
    Boolean(shot.visual.trim()) &&
    Boolean(shot.scale.trim()) &&
    Boolean(shot.lighting.trim()) &&
    Boolean(shot.sound.trim()) &&
    Boolean(shot.camera.trim())
  );
}

export function hasRealScriptWorkbenchAssetSource(asset: Pick<ScriptWorkbenchAsset, "source" | "attachmentId" | "nodeId" | "imageUrl">): boolean {
  if (asset.source === "none") return false;
  if (asset.attachmentId?.trim() || asset.nodeId?.trim()) return true;
  const imageUrl = asset.imageUrl?.trim();
  if (!imageUrl) return false;
  return /^(?:https?:\/\/|blob:|data:image\/|\/)/i.test(imageUrl);
}

export function deriveScriptWorkbenchSteps(
  input: Pick<ScriptWorkbenchDocument, "shots" | "assets">,
): ScriptWorkbenchSteps {
  const shotsDone = input.shots.length > 0 && input.shots.every(isShotComplete);
  const assetsDone =
    input.assets.length > 0 &&
    input.assets.every(
      (asset) => asset.status === "ready" && hasRealScriptWorkbenchAssetSource(asset),
    );
  const promptsDone =
    input.shots.length > 0 && input.shots.every((shot) => Boolean(shot.final_prompt.trim()));
  return {
    shots: shotsDone ? "done" : "active",
    assets: assetsDone ? "done" : shotsDone ? "active" : "pending",
    prompts: promptsDone ? "done" : assetsDone ? "active" : "pending",
  };
}

function withDerivedSteps(document: Omit<ScriptWorkbenchDocument, "steps">): ScriptWorkbenchDocument {
  const provisional: ScriptWorkbenchDocument = {
    ...document,
    steps: DEFAULT_STEP_STATE,
  };
  return { ...provisional, steps: deriveScriptWorkbenchSteps(provisional) };
}

export function normalizeScriptWorkbench(raw: unknown): ScriptWorkbenchDocument {
  const record = isRecord(raw) ? raw : {};
  const rawShots = Array.isArray(record.shots) ? record.shots : [];
  const rawAssets = Array.isArray(record.assets) ? record.assets : [];
  const shotIds = new Set<string>();
  const assetIds = new Set<string>();
  const shots = rawShots
    .filter(isRecord)
    .map((shot, index) => normalizeShot(shot, index + 1, shotIds));
  const assets = rawAssets
    .filter(isRecord)
    .map((asset, index) => normalizeAsset(asset, index + 1, assetIds));
  return withDerivedSteps({
    schema: SCRIPT_WORKBENCH_SCHEMA,
    skill: SCRIPT_WORKBENCH_SKILL,
    title: cleanString(record.title, SCRIPT_WORKBENCH_DEFAULT_TITLE, MAX_SHORT_TEXT_LENGTH),
    global_style: cleanString(
      record.global_style ?? record.globalStyle,
      SCRIPT_WORKBENCH_DEFAULT_STYLE,
      MAX_LONG_TEXT_LENGTH,
    ),
    style_locked: record.style_locked === true || record.styleLocked === true,
    shots,
    assets,
  });
}

export function createEmptyScriptWorkbench(
  input: Pick<Partial<ScriptWorkbenchDocument>, "title" | "global_style"> = {},
): ScriptWorkbenchDocument {
  return normalizeScriptWorkbench(input);
}

export function cloneScriptWorkbench(document: ScriptWorkbenchDocument): ScriptWorkbenchDocument {
  return normalizeScriptWorkbench(document);
}

export function serializeScriptWorkbench(document: ScriptWorkbenchDocument, pretty = false): string {
  return JSON.stringify(cloneScriptWorkbench(document), null, pretty ? 2 : undefined);
}

export function updateScriptWorkbenchShot(
  document: ScriptWorkbenchDocument,
  shotId: string,
  patch: ScriptWorkbenchShotPatch,
): ScriptWorkbenchDocument {
  const shots = document.shots.map((shot) => {
    if (shot.id !== shotId) return shot;
    const candidate = normalizeShot({ ...shot, ...patch, id: shot.id }, 1, new Set<string>());
    const invalidatesPrompt = SHOT_PROMPT_INPUT_FIELDS.some(
      (field) => Object.prototype.hasOwnProperty.call(patch, field) && candidate[field] !== shot[field],
    );
    return invalidatesPrompt ? { ...candidate, final_prompt: "" } : candidate;
  });
  return withDerivedSteps({ ...document, shots });
}

export function addScriptWorkbenchShot(
  document: ScriptWorkbenchDocument,
  shot: Partial<Omit<ScriptWorkbenchShot, "id">> & { id?: string } = {},
  atIndex = document.shots.length,
): ScriptWorkbenchDocument {
  const seen = new Set(document.shots.map((item) => item.id));
  const normalized = normalizeShot(
    shot as UnknownRecord,
    document.shots.length + 1,
    seen,
  );
  const index = Math.max(0, Math.min(Math.trunc(atIndex), document.shots.length));
  const shots = [...document.shots];
  shots.splice(index, 0, normalized);
  return withDerivedSteps({ ...document, shots });
}

export function removeScriptWorkbenchShot(
  document: ScriptWorkbenchDocument,
  shotId: string,
): ScriptWorkbenchDocument {
  return withDerivedSteps({
    ...document,
    shots: document.shots.filter((shot) => shot.id !== shotId),
  });
}

export function reorderScriptWorkbenchShot(
  document: ScriptWorkbenchDocument,
  shotId: string,
  toIndex: number,
): ScriptWorkbenchDocument {
  const fromIndex = document.shots.findIndex((shot) => shot.id === shotId);
  if (fromIndex < 0 || !Number.isFinite(toIndex)) return cloneScriptWorkbench(document);
  const shots = [...document.shots];
  const [shot] = shots.splice(fromIndex, 1);
  if (!shot) return cloneScriptWorkbench(document);
  shots.splice(Math.max(0, Math.min(Math.trunc(toIndex), shots.length)), 0, shot);
  return withDerivedSteps({ ...document, shots });
}

export function updateScriptWorkbenchAsset(
  document: ScriptWorkbenchDocument,
  assetId: string,
  patch: ScriptWorkbenchAssetPatch,
): ScriptWorkbenchDocument {
  const assets = document.assets.map((asset) => {
    if (asset.id !== assetId) return asset;
    return normalizeAsset({ ...asset, ...patch, id: asset.id }, 1, new Set<string>());
  });
  return withDerivedSteps({ ...document, assets });
}

export function clearScriptWorkbenchAssetSource(
  document: ScriptWorkbenchDocument,
  assetId: string,
): ScriptWorkbenchDocument {
  return updateScriptWorkbenchAsset(document, assetId, {
    status: "pending",
    source: "none",
    attachmentId: null,
    nodeId: null,
    imageUrl: null,
    mimeType: null,
    error: null,
  });
}

export function addScriptWorkbenchAsset(
  document: ScriptWorkbenchDocument,
  asset: Partial<Omit<ScriptWorkbenchAsset, "id">> & { id?: string },
  atIndex = document.assets.length,
): ScriptWorkbenchDocument {
  const seen = new Set(document.assets.map((item) => item.id));
  const normalized = normalizeAsset(
    asset as UnknownRecord,
    document.assets.length + 1,
    seen,
  );
  const index = Math.max(0, Math.min(Math.trunc(atIndex), document.assets.length));
  const assets = [...document.assets];
  assets.splice(index, 0, normalized);
  return withDerivedSteps({ ...document, assets });
}

export function removeScriptWorkbenchAsset(
  document: ScriptWorkbenchDocument,
  assetId: string,
): ScriptWorkbenchDocument {
  return withDerivedSteps({
    ...document,
    assets: document.assets.filter((asset) => asset.id !== assetId),
  });
}

export function composeScriptWorkbenchPrompt(
  style: string,
  shot: ScriptWorkbenchShot,
): string {
  const parts = [
    cleanString(style),
    `${shot.scale}，${shot.visual}`,
    `光影氛围：${shot.lighting}。`,
  ];
  if (shot.dialogue.trim()) parts.push(`对白与旁白：${shot.dialogue}。`);
  parts.push(
    `音效：${shot.sound}。`,
    `运镜：${shot.camera}。`,
    "主体一致，细节清晰，电影级构图。",
  );
  return parts.map((part) => part.trim()).filter(Boolean).join(" ");
}

export function composeScriptWorkbenchVideoPrompt(
  style: string,
  shot: ScriptWorkbenchShot,
): string {
  if (!shot.final_prompt.trim()) return "";
  return [
    `画面基础：${shot.final_prompt}`,
    `时序规格：${shot.duration}秒。`,
    `画面内容：${shot.visual}`,
    `运镜：${shot.camera}`,
    ...(shot.dialogue.trim() ? [`对白与旁白：${shot.dialogue}`] : []),
    `声音：${shot.sound}`,
    `景别：${shot.scale}`,
    `光影氛围：${shot.lighting}`,
    `视觉风格：${style}`,
  ].join("\n");
}

export function composeAllScriptWorkbenchPrompts(
  document: ScriptWorkbenchDocument,
): ScriptWorkbenchDocument {
  const shots = document.shots.map((shot) => ({
    ...shot,
    final_prompt: composeScriptWorkbenchPrompt(document.global_style, shot),
  }));
  return withDerivedSteps({ ...document, shots });
}

export function setScriptWorkbenchGlobalStyle(
  document: ScriptWorkbenchDocument,
  globalStyle: string,
): ScriptWorkbenchDocument {
  const nextStyle = cleanString(globalStyle, SCRIPT_WORKBENCH_DEFAULT_STYLE, MAX_LONG_TEXT_LENGTH);
  if (nextStyle === document.global_style) return cloneScriptWorkbench(document);
  return withDerivedSteps({
    ...document,
    global_style: nextStyle,
    shots: document.shots.map((shot) => ({ ...shot, final_prompt: "" })),
  });
}

export function lockScriptWorkbenchStyle(document: ScriptWorkbenchDocument): ScriptWorkbenchDocument {
  return document.style_locked ? cloneScriptWorkbench(document) : withDerivedSteps({ ...document, style_locked: true });
}

export function isScriptWorkbenchReadyForBatchVideo(document: ScriptWorkbenchDocument): boolean {
  const steps = deriveScriptWorkbenchSteps(document);
  return steps.shots === "done" && steps.assets === "done" && steps.prompts === "done";
}

export function validateScriptWorkbench(document: unknown): ScriptWorkbenchValidationIssue[] {
  const errors: ScriptWorkbenchValidationIssue[] = [];
  if (!isRecord(document)) return [{ path: "$", message: "JSON 顶层必须是 object" }];
  if (document.schema !== SCRIPT_WORKBENCH_SCHEMA) {
    errors.push({ path: "schema", message: `必须为 ${SCRIPT_WORKBENCH_SCHEMA}` });
  }
  if (document.skill !== SCRIPT_WORKBENCH_SKILL) {
    errors.push({ path: "skill", message: `必须为 ${SCRIPT_WORKBENCH_SKILL}` });
  }
  if (!cleanString(document.title)) errors.push({ path: "title", message: "不能为空" });
  if (!cleanString(document.global_style)) errors.push({ path: "global_style", message: "不能为空" });
  if (typeof document.style_locked !== "boolean") errors.push({ path: "style_locked", message: "必须是 boolean" });

  if (!isRecord(document.steps)) {
    errors.push({ path: "steps", message: "必须是 object" });
  } else {
    for (const key of ["shots", "assets", "prompts"] as const) {
      if (!isOneOf(document.steps[key], SCRIPT_WORKBENCH_STEP_STATES)) {
        errors.push({ path: `steps.${key}`, message: "状态无效" });
      }
    }
  }

  if (!Array.isArray(document.shots) || document.shots.length === 0) {
    errors.push({ path: "shots", message: "至少需要一个镜头" });
  } else {
    const seen = new Set<string>();
    document.shots.forEach((value, index) => {
      const path = `shots[${index}]`;
      if (!isRecord(value)) {
        errors.push({ path, message: "必须是 object" });
        return;
      }
      const id = cleanString(value.id);
      if (!id) errors.push({ path: `${path}.id`, message: "缺失" });
      else if (seen.has(id)) errors.push({ path: `${path}.id`, message: "重复" });
      else seen.add(id);
      const duration = Number(value.duration);
      if (!Number.isFinite(duration) || duration < 5 || duration > 15) {
        errors.push({ path: `${path}.duration`, message: "必须是 5–15 秒的数字" });
      }
      for (const field of ["visual", "scale", "lighting", "sound", "camera"] as const) {
        if (!cleanString(value[field])) errors.push({ path: `${path}.${field}`, message: "缺失" });
      }
      for (const field of ["dialogue", "final_prompt", "color"] as const) {
        if (!(field in value)) errors.push({ path: `${path}.${field}`, message: "缺失" });
      }
    });
  }

  if (!Array.isArray(document.assets)) {
    errors.push({ path: "assets", message: "必须是 array" });
  } else {
    const seen = new Set<string>();
    document.assets.forEach((value, index) => {
      const path = `assets[${index}]`;
      if (!isRecord(value)) {
        errors.push({ path, message: "必须是 object" });
        return;
      }
      const id = cleanString(value.id);
      if (!id) errors.push({ path: `${path}.id`, message: "缺失" });
      else if (seen.has(id)) errors.push({ path: `${path}.id`, message: "重复" });
      else seen.add(id);
      if (!cleanString(value.name)) errors.push({ path: `${path}.name`, message: "缺失" });
      if (!isOneOf(value.kind, SCRIPT_WORKBENCH_ASSET_KINDS)) {
        errors.push({ path: `${path}.kind`, message: "无效" });
      }
      if (!isOneOf(value.status, SCRIPT_WORKBENCH_ASSET_STATUSES)) {
        errors.push({ path: `${path}.status`, message: "无效" });
      }
      if (!isOneOf(value.source, SCRIPT_WORKBENCH_ASSET_SOURCES)) {
        errors.push({ path: `${path}.source`, message: "无效" });
      }
      for (const field of ["description", "prompt"] as const) {
        if (!(field in value)) errors.push({ path: `${path}.${field}`, message: "缺失" });
      }
      if (
        value.status === "ready"
      ) {
        const evidence: Pick<
          ScriptWorkbenchAsset,
          "source" | "attachmentId" | "nodeId" | "imageUrl"
        > = {
          source: isOneOf(value.source, SCRIPT_WORKBENCH_ASSET_SOURCES) ? value.source : "none",
        };
        const attachmentId = cleanOptionalString(value.attachmentId ?? value.attachment_id, MAX_ID_LENGTH);
        const nodeId = cleanOptionalString(value.nodeId ?? value.node_id, MAX_ID_LENGTH);
        const imageUrl = cleanOptionalString(value.imageUrl ?? value.image_url);
        if (attachmentId !== undefined) evidence.attachmentId = attachmentId;
        if (nodeId !== undefined) evidence.nodeId = nodeId;
        if (imageUrl !== undefined) evidence.imageUrl = imageUrl;
        if (!hasRealScriptWorkbenchAssetSource(evidence)) {
          errors.push({ path, message: "ready 时必须有真实图片来源" });
        }
      }
    });
  }
  return errors;
}

export class ScriptWorkbenchModelParseError extends Error {
  readonly causeText: string;

  constructor(message: string, causeText: string) {
    super(message);
    this.name = "ScriptWorkbenchModelParseError";
    this.causeText = causeText;
  }
}

function balancedJsonCandidates(text: string): string[] {
  const candidates: string[] = [];
  for (let start = 0; start < text.length; start += 1) {
    const first = text[start];
    if (first !== "{" && first !== "[") continue;
    const stack = [first];
    let quote: '"' | "'" | null = null;
    let escaped = false;
    for (let index = start + 1; index < text.length; index += 1) {
      const character = text[index];
      if (quote) {
        if (escaped) escaped = false;
        else if (character === "\\") escaped = true;
        else if (character === quote) quote = null;
        continue;
      }
      if (character === '"' || character === "'") {
        quote = character;
        continue;
      }
      if (character === "{" || character === "[") stack.push(character);
      else if (character === "}" || character === "]") {
        const expected = character === "}" ? "{" : "[";
        if (stack.at(-1) !== expected) break;
        stack.pop();
        if (stack.length === 0) {
          candidates.push(text.slice(start, index + 1));
          start = index;
          break;
        }
      }
    }
  }
  return candidates;
}

function stripJsonComments(text: string): string {
  let result = "";
  let quote: '"' | "'" | null = null;
  let escaped = false;
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    const next = text[index + 1];
    if (quote) {
      result += character;
      if (escaped) {
        escaped = false;
        continue;
      }
      if (character === "\\") escaped = true;
      else if (character === quote) quote = null;
      continue;
    }
    if (character === '"' || character === "'") {
      quote = character;
      result += character;
      continue;
    }
    if (character === "/" && next === "/") {
      while (index < text.length && text[index] !== "\n") index += 1;
      result += "\n";
      continue;
    }
    if (character === "/" && next === "*") {
      index += 2;
      while (index < text.length && !(text[index] === "*" && text[index + 1] === "/")) index += 1;
      index += 1;
      continue;
    }
    result += character;
  }
  return result;
}

function convertSingleQuotedStrings(text: string): string {
  let result = "";
  let quote: '"' | "'" | null = null;
  let escaped = false;
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (quote === '"') {
      result += character;
      if (escaped) escaped = false;
      else if (character === "\\") escaped = true;
      else if (character === '"') quote = null;
      continue;
    }
    if (quote === "'") {
      if (escaped) {
        result += character === "'" ? "'" : `\\${character}`;
        escaped = false;
      } else if (character === "\\") {
        escaped = true;
      } else if (character === "'") {
        result += '"';
        quote = null;
      } else {
        result += character === '"' ? '\\"' : character;
      }
      continue;
    }
    if (character === "'") {
      quote = "'";
      result += '"';
    } else {
      if (character === '"') quote = '"';
      result += character;
    }
  }
  return result;
}

function quoteUnquotedJsonKeys(text: string): string {
  let result = "";
  let inString = false;
  let escaped = false;
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (inString) {
      result += character;
      if (escaped) escaped = false;
      else if (character === "\\") escaped = true;
      else if (character === '"') inString = false;
      continue;
    }
    if (character === '"') {
      inString = true;
      result += character;
      continue;
    }
    if (character !== "{" && character !== ",") {
      result += character;
      continue;
    }

    result += character;
    let cursor = index + 1;
    while (/\s/.test(text[cursor] ?? "")) cursor += 1;
    const start = cursor;
    if (!/[A-Za-z_$]/.test(text[cursor] ?? "")) continue;
    cursor += 1;
    while (/[\w$-]/.test(text[cursor] ?? "")) cursor += 1;
    const key = text.slice(start, cursor);
    let afterKey = cursor;
    while (/\s/.test(text[afterKey] ?? "")) afterKey += 1;
    if (text[afterKey] !== ":") continue;
    result += `${text.slice(index + 1, start)}"${key}"${text.slice(cursor, afterKey + 1)}`;
    index = afterKey;
  }
  return result;
}

function removeTrailingJsonCommas(text: string): string {
  let result = "";
  let inString = false;
  let escaped = false;
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (inString) {
      result += character;
      if (escaped) escaped = false;
      else if (character === "\\") escaped = true;
      else if (character === '"') inString = false;
      continue;
    }
    if (character === '"') {
      inString = true;
      result += character;
      continue;
    }
    if (character === ",") {
      let cursor = index + 1;
      while (/\s/.test(text[cursor] ?? "")) cursor += 1;
      if (text[cursor] === "}" || text[cursor] === "]") continue;
    }
    result += character;
  }
  return result;
}

function replacePythonJsonLiterals(text: string): string {
  let result = "";
  let inString = false;
  let escaped = false;
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (inString) {
      result += character;
      if (escaped) escaped = false;
      else if (character === "\\") escaped = true;
      else if (character === '"') inString = false;
      continue;
    }
    if (character === '"') {
      inString = true;
      result += character;
      continue;
    }
    const remainder = text.slice(index);
    const match = /^(None|True|False)\b/.exec(remainder);
    if (!match) {
      result += character;
      continue;
    }
    result += match[1] === "None" ? "null" : match[1] === "True" ? "true" : "false";
    index += match[0].length - 1;
  }
  return result;
}

export function repairScriptWorkbenchJson(text: string): string {
  const withoutComments = stripJsonComments(text);
  const withDoubleQuotedStrings = convertSingleQuotedStrings(withoutComments);
  const withQuotedKeys = quoteUnquotedJsonKeys(withDoubleQuotedStrings);
  const withoutTrailingCommas = removeTrailingJsonCommas(withQuotedKeys);
  return replacePythonJsonLiterals(withoutTrailingCommas);
}

function parseJsonCandidate(candidate: string): unknown {
  try {
    return JSON.parse(candidate) as unknown;
  } catch {
    return JSON.parse(repairScriptWorkbenchJson(candidate)) as unknown;
  }
}

function unwrapModelPayload(value: unknown, depth = 0): unknown {
  if (depth > 5) return value;
  if (typeof value === "string") {
    try {
      return unwrapModelPayload(parseJsonCandidate(value), depth + 1);
    } catch {
      return value;
    }
  }
  if (Array.isArray(value)) return { shots: value };
  if (!isRecord(value) || Array.isArray(value.shots)) return value;
  for (const key of ["workbench", "script", "result", "data", "output", "content"] as const) {
    if (key in value) return unwrapModelPayload(value[key], depth + 1);
  }
  return value;
}

export function extractScriptWorkbenchJson(modelText: string): unknown {
  const text = modelText.replace(/^\uFEFF/, "").trim();
  if (!text) throw new ScriptWorkbenchModelParseError("模型返回了空内容", modelText);
  const candidates = [text];
  for (const match of text.matchAll(/```(?:json|javascript|js)?\s*([\s\S]*?)```/gi)) {
    const candidate = match[1]?.trim();
    if (candidate) candidates.push(candidate);
  }
  candidates.push(...balancedJsonCandidates(text));

  let lastError: unknown;
  for (const candidate of [...new Set(candidates)]) {
    try {
      return unwrapModelPayload(parseJsonCandidate(candidate));
    } catch (error) {
      lastError = error;
    }
  }
  const detail = lastError instanceof Error ? `：${lastError.message}` : "";
  throw new ScriptWorkbenchModelParseError(`无法从模型输出提取有效 JSON${detail}`, modelText);
}

export function parseScriptWorkbenchModelOutput(modelText: string): ScriptWorkbenchDocument {
  const extracted = extractScriptWorkbenchJson(modelText);
  if (!isRecord(extracted)) {
    throw new ScriptWorkbenchModelParseError("模型 JSON 顶层必须是 object", modelText);
  }
  const document = normalizeScriptWorkbench(extracted);
  if (document.shots.length === 0) {
    throw new ScriptWorkbenchModelParseError("模型 JSON 未包含有效的 shots 镜头数组", modelText);
  }
  return document;
}

export function tryParseScriptWorkbenchModelOutput(modelText: string): ScriptWorkbenchParseResult {
  try {
    return { ok: true, document: parseScriptWorkbenchModelOutput(modelText) };
  } catch (error) {
    return {
      ok: false,
      error:
        error instanceof ScriptWorkbenchModelParseError
          ? error
          : new ScriptWorkbenchModelParseError(
              error instanceof Error ? error.message : "模型输出解析失败",
              modelText,
            ),
    };
  }
}

export const SCRIPT_WORKBENCH_MODEL_JSON_INSTRUCTIONS = `仅返回 JSON，不要使用 Markdown 代码块。顶层结构必须为：
{"schema":"${SCRIPT_WORKBENCH_SCHEMA}","skill":"${SCRIPT_WORKBENCH_SKILL}","title":"脚本标题","global_style":"全局美术风格","style_locked":false,"shots":[{"id":"shot-1","duration":5,"visual":"画面描述","scale":"中景","lighting":"光影氛围","dialogue":"对白或旁白，可为空","sound":"音效","camera":"运镜","final_prompt":"","color":""}],"assets":[{"id":"asset-1","kind":"character","name":"资产名","description":"资产描述","prompt":"资产生图提示词","status":"pending","source":"none"}]}。
kind 只能是 character、scene、prop；新资产必须为 status=pending、source=none。镜头 id 与资产 id 必须稳定且唯一。`;
