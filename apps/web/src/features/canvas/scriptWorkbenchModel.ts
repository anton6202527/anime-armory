import { APP_CANVAS_SKILL_IDS } from "./appSkillIds";

export const SCRIPT_WORKBENCH_SCHEMA = "app-script-workbench/v3" as const;
export const SCRIPT_WORKBENCH_SKILL = APP_CANVAS_SKILL_IDS.scriptWorkbench;
export const SCRIPT_WORKBENCH_COMPLETION_DEFINITION = "app-script-workbench/final-master/v2" as const;

export const SCRIPT_WORKBENCH_LEGACY_SCHEMAS = [
  "app-script-workbench/v2",
  "app-script-workbench/v1",
  "n2d-script-workbench/v1",
  "app-n2d-script-workbench/v1",
] as const;

export const SCRIPT_WORKBENCH_DEFAULT_TITLE = "未命名故事脚本";
export const SCRIPT_WORKBENCH_DEFAULT_STYLE = "电影级画面，主体一致，细节清晰";

export const SCRIPT_WORKBENCH_STEP_STATES = ["pending", "active", "done"] as const;
export const SCRIPT_WORKBENCH_ASSET_KINDS = ["character", "scene", "prop"] as const;
export const SCRIPT_WORKBENCH_ASSET_STATUSES = ["pending", "generating", "machine_complete", "accepted", "failed", "stale"] as const;
export const SCRIPT_WORKBENCH_ASSET_SOURCES = ["none", "ai", "canvas", "upload"] as const;
export const SCRIPT_WORKBENCH_STATES = ["draft", "ready", "running", "needs_revision", "blocked", "machine_complete", "complete"] as const;
export const SCRIPT_WORKBENCH_JOB_KINDS = ["asset_image", "shot_image", "shot_video", "master"] as const;
export const SCRIPT_WORKBENCH_JOB_STATUSES = ["draft", "ready", "queued", "running", "succeeded", "failed", "cancelled", "blocked", "stale"] as const;
export const SCRIPT_WORKBENCH_RESULT_REVIEWS = ["pending", "machine_complete", "accepted", "rejected", "stale"] as const;
export const SCRIPT_WORKBENCH_BYTE_VERIFIERS = ["web_attachment", "trusted_backend", "desktop"] as const;

export type ScriptWorkbenchStepState = (typeof SCRIPT_WORKBENCH_STEP_STATES)[number];
export type ScriptWorkbenchAssetKind = (typeof SCRIPT_WORKBENCH_ASSET_KINDS)[number];
export type ScriptWorkbenchAssetStatus = (typeof SCRIPT_WORKBENCH_ASSET_STATUSES)[number];
export type ScriptWorkbenchAssetSource = (typeof SCRIPT_WORKBENCH_ASSET_SOURCES)[number];
export type ScriptWorkbenchState = (typeof SCRIPT_WORKBENCH_STATES)[number];
export type ScriptWorkbenchJobKind = (typeof SCRIPT_WORKBENCH_JOB_KINDS)[number];
export type ScriptWorkbenchJobStatus = (typeof SCRIPT_WORKBENCH_JOB_STATUSES)[number];
export type ScriptWorkbenchResultReview = (typeof SCRIPT_WORKBENCH_RESULT_REVIEWS)[number];
export type ScriptWorkbenchByteVerifier = (typeof SCRIPT_WORKBENCH_BYTE_VERIFIERS)[number];

/**
 * Explicit evidence that a durable source was read and its bytes matched a
 * SHA-256. A path or URL alone is never verification in the browser.
 */
export type ScriptWorkbenchByteVerification = Record<string, unknown> & {
  status: string;
  verifier_kind: string;
  method: string;
  durable_ref: string;
  sha256: string;
  verified_at: string;
};

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

export type ScriptWorkbenchAsset = {
  id: string;
  kind: ScriptWorkbenchAssetKind;
  name: string;
  description: string;
  prompt: string;
  status: ScriptWorkbenchAssetStatus;
  source: ScriptWorkbenchAssetSource;
  sha256: string;
  path?: string;
  attachmentId?: string;
  nodeId?: string;
  imageUrl?: string;
  mimeType?: string;
  error?: string;
  byte_verification?: ScriptWorkbenchByteVerification;
  acceptance_receipt?: ScriptWorkbenchAcceptanceReceipt;
  legacy_acceptance_receipt?: ScriptWorkbenchAcceptanceReceipt;
};

export type ScriptWorkbenchDeliverySpec = {
  container: string;
  mime_type: string;
  aspect_ratio: string;
  resolution: string;
  require_audio: boolean;
};

export type ScriptWorkbenchAcceptanceReceipt = Record<string, unknown> & {
  reviewer_kind: string;
  reviewer_name: string;
  verdict: string;
  content_sha256: string;
  output_sha256: string;
  criteria: string[];
  blocks: string[];
  reviewed_at: string;
  confirmation: {
    kind: string;
    artifact_sha256: string;
    current_pixels_reviewed: boolean;
    decision: string;
    statement: string;
  };
};

export type ScriptWorkbenchMachineReceipt = Record<string, unknown> & {
  reviewer_kind: string;
  verdict: string;
  content_sha256: string;
  output_sha256: string;
  checks: string[];
  blocks: string[];
  completed_at: string;
};

export type ScriptWorkbenchJob = Record<string, unknown> & {
  id: string;
  kind: ScriptWorkbenchJobKind;
  shot_id: string;
  input_sha256: string;
  status: ScriptWorkbenchJobStatus;
  run_id: string;
  error: string;
};

export type ScriptWorkbenchResult = Record<string, unknown> & {
  id: string;
  kind: "shot_video";
  shot_id: string;
  input_sha256: string;
  path: string;
  sha256: string;
  review: ScriptWorkbenchResultReview;
  machine_receipt: ScriptWorkbenchMachineReceipt;
  acceptance_receipt: ScriptWorkbenchAcceptanceReceipt;
  legacy_acceptance_receipt?: ScriptWorkbenchAcceptanceReceipt;
  byte_verification?: ScriptWorkbenchByteVerification;
};

export type ScriptWorkbenchMaster = Record<string, unknown> & {
  status: "pending" | "machine_complete" | "stale";
  input_sha256: string;
  path: string;
  sha256: string;
  mime_type: string;
  duration: number;
  byte_verification?: ScriptWorkbenchByteVerification;
};

export type ScriptWorkbenchQcReceipt = Record<string, unknown> & {
  verdict: "pending" | "pass" | "block" | "stale";
  reviewer_kind: string;
  content_sha256: string;
  master_sha256: string;
  checks: string[];
  blocks: string[];
  notes: string;
  reviewed_at: string;
  receipt_path: string;
  receipt_sha256: string;
  byte_verification?: ScriptWorkbenchByteVerification;
};

export type ScriptWorkbenchMigration = {
  source_schema: string;
  human_acceptance_reconfirmation_required: true;
  legacy_evidence_preserved: true;
};

export type ScriptWorkbenchDocument = {
  schema: typeof SCRIPT_WORKBENCH_SCHEMA;
  skill: typeof SCRIPT_WORKBENCH_SKILL;
  title: string;
  global_style: string;
  acceptance_policy: "delegated" | "human";
  delivery_spec: ScriptWorkbenchDeliverySpec;
  shots: ScriptWorkbenchShot[];
  assets: ScriptWorkbenchAsset[];
  content_sha256: string;
  state: ScriptWorkbenchState;
  jobs: ScriptWorkbenchJob[];
  results: ScriptWorkbenchResult[];
  master: ScriptWorkbenchMaster;
  qc_receipt: ScriptWorkbenchQcReceipt;
  final_acceptance_receipt: ScriptWorkbenchAcceptanceReceipt;
  completion: { definition: typeof SCRIPT_WORKBENCH_COMPLETION_DEFINITION };
  migration?: ScriptWorkbenchMigration;
};

export type ScriptWorkbenchShotPatch = Partial<Omit<ScriptWorkbenchShot, "id">>;
type ScriptWorkbenchAssetEvidenceKey =
  | "path"
  | "attachmentId"
  | "nodeId"
  | "imageUrl"
  | "mimeType"
  | "error"
  | "byte_verification";
export type ScriptWorkbenchAssetPatch = Partial<
  Omit<ScriptWorkbenchAsset, "id" | ScriptWorkbenchAssetEvidenceKey>
> & {
  /** Pass null to explicitly clear optional evidence with exactOptionalPropertyTypes enabled. */
  path?: string | null;
  attachmentId?: string | null;
  nodeId?: string | null;
  imageUrl?: string | null;
  mimeType?: string | null;
  error?: string | null;
  byte_verification?: ScriptWorkbenchByteVerification | null;
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

function cleanStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return [...new Set(value.map((item) => cleanString(item)).filter(Boolean))];
}

function cleanBlocks(value: unknown): string[] {
  if (value === undefined || value === null) return [];
  if (Array.isArray(value)) return cleanStringList(value);
  const text = cleanString(value);
  return text ? [text] : [];
}

function isSha256(value: unknown): value is string {
  return typeof value === "string" && /^[0-9a-f]{64}$/i.test(value);
}

function normalizeByteVerification(raw: unknown): ScriptWorkbenchByteVerification | undefined {
  if (!isRecord(raw)) return undefined;
  return {
    ...raw,
    status: cleanString(raw.status, "unverified", MAX_SHORT_TEXT_LENGTH),
    verifier_kind: cleanString(raw.verifier_kind ?? raw.verifierKind, "", MAX_SHORT_TEXT_LENGTH),
    method: cleanString(raw.method, "", MAX_SHORT_TEXT_LENGTH).toLowerCase(),
    durable_ref: cleanString(raw.durable_ref ?? raw.durableRef, "", MAX_LONG_TEXT_LENGTH),
    sha256: cleanString(raw.sha256 ?? raw.output_sha256, "", 64).toLowerCase(),
    verified_at: cleanString(raw.verified_at ?? raw.verifiedAt, "", MAX_SHORT_TEXT_LENGTH),
  };
}

/**
 * Browser-safe completion evidence. Callers must create this only after they
 * have actually read the durable source bytes and compared their SHA-256.
 */
export function hasDurableScriptWorkbenchByteVerification(
  verification: unknown,
  expectedSha256: string,
): verification is ScriptWorkbenchByteVerification {
  const value = normalizeByteVerification(verification);
  if (!value || !isSha256(expectedSha256)) return false;
  if (
    value.status !== "verified"
    || value.method !== "sha256"
    || !isOneOf(value.verifier_kind, SCRIPT_WORKBENCH_BYTE_VERIFIERS)
    || value.sha256 !== expectedSha256.toLowerCase()
    || !value.durable_ref
    || /^blob:/i.test(value.durable_ref)
    || !Number.isFinite(Date.parse(value.verified_at))
  ) return false;
  return value.verifier_kind !== "web_attachment" || /^attachment:.+/.test(value.durable_ref);
}

function positiveDuration(value: unknown): number {
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return 5;
  return Math.max(5, Math.min(15, Math.round(parsed)));
}

const SHA256_ROUND_CONSTANTS = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]);

function rotateRight(value: number, bits: number): number {
  return (value >>> bits) | (value << (32 - bits));
}

/** Synchronous SHA-256 used by both browser authoring hashes and persisted media bytes. */
export function scriptWorkbenchSha256Bytes(input: Uint8Array): string {
  const bitLength = input.length * 8;
  const paddedLength = Math.ceil((input.length + 9) / 64) * 64;
  const message = new Uint8Array(paddedLength);
  message.set(input);
  message[input.length] = 0x80;
  const view = new DataView(message.buffer);
  view.setUint32(paddedLength - 8, Math.floor(bitLength / 0x100000000));
  view.setUint32(paddedLength - 4, bitLength >>> 0);

  const hash = new Uint32Array([
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
  ]);
  const schedule = new Uint32Array(64);
  for (let offset = 0; offset < message.length; offset += 64) {
    for (let index = 0; index < 16; index += 1) schedule[index] = view.getUint32(offset + index * 4);
    for (let index = 16; index < 64; index += 1) {
      const first = schedule[index - 15] ?? 0;
      const second = schedule[index - 2] ?? 0;
      const sigma0 = rotateRight(first, 7) ^ rotateRight(first, 18) ^ (first >>> 3);
      const sigma1 = rotateRight(second, 17) ^ rotateRight(second, 19) ^ (second >>> 10);
      schedule[index] = ((schedule[index - 16] ?? 0) + sigma0 + (schedule[index - 7] ?? 0) + sigma1) >>> 0;
    }
    let [a, b, c, d, e, f, g, h] = hash;
    for (let index = 0; index < 64; index += 1) {
      const bigSigma1 = rotateRight(e ?? 0, 6) ^ rotateRight(e ?? 0, 11) ^ rotateRight(e ?? 0, 25);
      const choice = ((e ?? 0) & (f ?? 0)) ^ (~(e ?? 0) & (g ?? 0));
      const temporary1 = ((h ?? 0) + bigSigma1 + choice + (SHA256_ROUND_CONSTANTS[index] ?? 0) + (schedule[index] ?? 0)) >>> 0;
      const bigSigma0 = rotateRight(a ?? 0, 2) ^ rotateRight(a ?? 0, 13) ^ rotateRight(a ?? 0, 22);
      const majority = ((a ?? 0) & (b ?? 0)) ^ ((a ?? 0) & (c ?? 0)) ^ ((b ?? 0) & (c ?? 0));
      const temporary2 = (bigSigma0 + majority) >>> 0;
      h = g; g = f; f = e; e = ((d ?? 0) + temporary1) >>> 0;
      d = c; c = b; b = a; a = (temporary1 + temporary2) >>> 0;
    }
    hash[0] = ((hash[0] ?? 0) + (a ?? 0)) >>> 0;
    hash[1] = ((hash[1] ?? 0) + (b ?? 0)) >>> 0;
    hash[2] = ((hash[2] ?? 0) + (c ?? 0)) >>> 0;
    hash[3] = ((hash[3] ?? 0) + (d ?? 0)) >>> 0;
    hash[4] = ((hash[4] ?? 0) + (e ?? 0)) >>> 0;
    hash[5] = ((hash[5] ?? 0) + (f ?? 0)) >>> 0;
    hash[6] = ((hash[6] ?? 0) + (g ?? 0)) >>> 0;
    hash[7] = ((hash[7] ?? 0) + (h ?? 0)) >>> 0;
  }
  return [...hash].map((value) => value.toString(16).padStart(8, "0")).join("");
}

function canonicalize(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (!isRecord(value)) return value;
  return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonicalize(value[key])]));
}

export function scriptWorkbenchCanonicalContent(
  document: Pick<ScriptWorkbenchDocument, "title" | "global_style" | "acceptance_policy" | "delivery_spec" | "shots" | "assets">,
): UnknownRecord {
  return {
    acceptance_policy: document.acceptance_policy,
    assets: document.assets.map((asset) => ({
      id: asset.id,
      kind: asset.kind,
      name: asset.name,
      description: asset.description,
      prompt: asset.prompt,
      sha256: asset.sha256,
    })),
    delivery_spec: document.delivery_spec,
    global_style: document.global_style,
    shots: document.shots.map(({ color: _color, ...shot }) => shot),
    title: document.title,
  };
}

export function computeScriptWorkbenchContentSha256(
  document: Pick<ScriptWorkbenchDocument, "title" | "global_style" | "acceptance_policy" | "delivery_spec" | "shots" | "assets">,
): string {
  const canonical = JSON.stringify(canonicalize(scriptWorkbenchCanonicalContent(document)));
  return scriptWorkbenchSha256Bytes(new TextEncoder().encode(canonical));
}

export function createStableScriptWorkbenchId(prefix: "shot" | "asset", index: number, seed: string): string {
  const digest = scriptWorkbenchSha256Bytes(new TextEncoder().encode(`${prefix}:${index}:${seed}`));
  return `${prefix}-${digest.slice(0, 10)}`;
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

function normalizeAsset(
  raw: UnknownRecord,
  index: number,
  seen: Set<string>,
  preserveLegacyMachineEvidence = false,
): ScriptWorkbenchAsset {
  const kind = isOneOf(raw.kind, SCRIPT_WORKBENCH_ASSET_KINDS) ? raw.kind : "character";
  const name = cleanString(raw.name, "", MAX_SHORT_TEXT_LENGTH);
  const fallbackId = createStableScriptWorkbenchId("asset", index, `${kind}:${name}`);
  const source = isOneOf(raw.source, SCRIPT_WORKBENCH_ASSET_SOURCES) ? raw.source : "none";
  const requestedStatus = raw.status === "ready"
    ? "machine_complete"
    : isOneOf(raw.status, SCRIPT_WORKBENCH_ASSET_STATUSES) ? raw.status : "pending";

  const attachmentId = cleanOptionalString(raw.attachmentId ?? raw.attachment_id, MAX_ID_LENGTH);
  const nodeId = cleanOptionalString(raw.nodeId ?? raw.node_id, MAX_ID_LENGTH);
  const imageUrl = cleanOptionalString(raw.imageUrl ?? raw.image_url, MAX_LONG_TEXT_LENGTH);
  const mimeType = cleanOptionalString(raw.mimeType ?? raw.mime_type, MAX_SHORT_TEXT_LENGTH);
  const error = cleanOptionalString(raw.error ?? raw.generationError, MAX_LONG_TEXT_LENGTH);
  const path = cleanOptionalString(raw.path, MAX_LONG_TEXT_LENGTH);
  const byteVerification = normalizeByteVerification(raw.byte_verification ?? raw.byteVerification);

  const result: ScriptWorkbenchAsset = {
    id: uniqueId(cleanString(raw.id, "", MAX_ID_LENGTH), fallbackId, seen),
    kind,
    name,
    description: cleanString(raw.description, "", MAX_LONG_TEXT_LENGTH),
    prompt: cleanString(raw.prompt, "", MAX_LONG_TEXT_LENGTH),
    status: requestedStatus,
    source,
    sha256: cleanString(raw.sha256 ?? raw.content_sha256, "", 64).toLowerCase(),
  };
  // Keep locators as recoverable evidence even when an old document omitted
  // `source`; source=none still prevents the locator from counting as proof.
  if (path !== undefined) result.path = path;
  if (attachmentId !== undefined) result.attachmentId = attachmentId;
  if (nodeId !== undefined) result.nodeId = nodeId;
  if (imageUrl !== undefined) result.imageUrl = imageUrl;
  if (mimeType !== undefined) result.mimeType = mimeType;
  if (error !== undefined) result.error = error;
  if (byteVerification !== undefined) result.byte_verification = byteVerification;
  if (isRecord(raw.acceptance_receipt ?? raw.acceptanceReceipt ?? raw.acceptance)) {
    result.acceptance_receipt = normalizeAcceptanceReceipt(raw.acceptance_receipt ?? raw.acceptanceReceipt ?? raw.acceptance);
  }
  if (isRecord(raw.legacy_acceptance_receipt)) {
    result.legacy_acceptance_receipt = normalizeAcceptanceReceipt(raw.legacy_acceptance_receipt);
  }

  if (
    !preserveLegacyMachineEvidence
    && ["machine_complete", "accepted"].includes(result.status)
    && !hasRealScriptWorkbenchAssetSource(result)
  ) {
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

function normalizeDeliverySpec(raw: unknown): ScriptWorkbenchDeliverySpec {
  const source = isRecord(raw) ? raw : {};
  return {
    container: cleanString(source.container, "mp4", MAX_SHORT_TEXT_LENGTH).toLowerCase(),
    mime_type: cleanString(source.mime_type ?? source.mimeType, "video/mp4", MAX_SHORT_TEXT_LENGTH).toLowerCase(),
    aspect_ratio: cleanString(source.aspect_ratio ?? source.aspectRatio, "16:9", MAX_SHORT_TEXT_LENGTH),
    resolution: cleanString(source.resolution, "project", MAX_SHORT_TEXT_LENGTH),
    require_audio: source.require_audio === true || source.requireAudio === true,
  };
}

function normalizeAcceptanceReceipt(raw: unknown): ScriptWorkbenchAcceptanceReceipt {
  const source = isRecord(raw) ? raw : {};
  const rawConfirmation = isRecord(source.confirmation) ? source.confirmation : {};
  return {
    ...source,
    reviewer_kind: cleanString(source.reviewer_kind ?? source.reviewerKind, "", MAX_SHORT_TEXT_LENGTH),
    reviewer_name: cleanString(source.reviewer_name ?? source.reviewerName ?? source.reviewer, "", MAX_SHORT_TEXT_LENGTH),
    verdict: cleanString(source.verdict, "pending", MAX_SHORT_TEXT_LENGTH),
    content_sha256: cleanString(source.content_sha256 ?? source.input_sha256, "", 64).toLowerCase(),
    output_sha256: cleanString(source.output_sha256, "", 64).toLowerCase(),
    criteria: cleanStringList(source.criteria),
    blocks: cleanBlocks(source.blocks),
    reviewed_at: cleanString(source.reviewed_at ?? source.reviewedAt, "", MAX_SHORT_TEXT_LENGTH),
    confirmation: {
      kind: cleanString(rawConfirmation.kind, "", MAX_SHORT_TEXT_LENGTH),
      artifact_sha256: cleanString(rawConfirmation.artifact_sha256 ?? rawConfirmation.output_sha256, "", 64).toLowerCase(),
      current_pixels_reviewed: rawConfirmation.current_pixels_reviewed === true,
      decision: cleanString(rawConfirmation.decision, "", MAX_SHORT_TEXT_LENGTH),
      statement: cleanString(rawConfirmation.statement, "", MAX_LONG_TEXT_LENGTH),
    },
  };
}

function normalizeMachineReceipt(raw: unknown): ScriptWorkbenchMachineReceipt {
  const source = isRecord(raw) ? raw : {};
  return {
    ...source,
    reviewer_kind: cleanString(source.reviewer_kind ?? source.reviewerKind, "", MAX_SHORT_TEXT_LENGTH),
    verdict: cleanString(source.verdict, "pending", MAX_SHORT_TEXT_LENGTH),
    content_sha256: cleanString(source.content_sha256 ?? source.input_sha256, "", 64).toLowerCase(),
    output_sha256: cleanString(source.output_sha256, "", 64).toLowerCase(),
    checks: cleanStringList(source.checks ?? source.criteria),
    blocks: cleanBlocks(source.blocks),
    completed_at: cleanString(source.completed_at ?? source.reviewed_at ?? source.reviewedAt, "", MAX_SHORT_TEXT_LENGTH),
  };
}

function normalizeJob(raw: UnknownRecord, index: number): ScriptWorkbenchJob {
  const kind = isOneOf(raw.kind, SCRIPT_WORKBENCH_JOB_KINDS) ? raw.kind : "shot_video";
  const status = isOneOf(raw.status, SCRIPT_WORKBENCH_JOB_STATUSES) ? raw.status : "draft";
  return {
    ...raw,
    id: cleanString(raw.id, `job-${index}`, MAX_ID_LENGTH),
    kind,
    shot_id: cleanString(raw.shot_id ?? raw.shotId, "", MAX_ID_LENGTH),
    input_sha256: cleanString(raw.input_sha256 ?? raw.content_sha256, "", 64).toLowerCase(),
    status,
    run_id: cleanString(raw.run_id ?? raw.runId, "", MAX_ID_LENGTH),
    error: cleanString(raw.error, "", MAX_LONG_TEXT_LENGTH),
  };
}

function normalizeResult(raw: UnknownRecord, index: number): ScriptWorkbenchResult {
  const review = isOneOf(raw.review, SCRIPT_WORKBENCH_RESULT_REVIEWS) ? raw.review : "pending";
  const shotId = cleanString(raw.shot_id ?? raw.shotId, "", MAX_ID_LENGTH);
  const result: ScriptWorkbenchResult = {
    ...raw,
    id: cleanString(raw.id, `result-${index}-${shotId || "shot"}`, MAX_ID_LENGTH),
    kind: "shot_video",
    shot_id: shotId,
    input_sha256: cleanString(raw.input_sha256 ?? raw.content_sha256, "", 64).toLowerCase(),
    path: cleanString(raw.path, "", MAX_LONG_TEXT_LENGTH),
    sha256: cleanString(raw.sha256 ?? raw.output_sha256, "", 64).toLowerCase(),
    review,
    machine_receipt: normalizeMachineReceipt(raw.machine_receipt ?? raw.machineReceipt),
    acceptance_receipt: normalizeAcceptanceReceipt(raw.acceptance_receipt ?? raw.acceptanceReceipt ?? raw.acceptance),
  };
  const byteVerification = normalizeByteVerification(raw.byte_verification ?? raw.byteVerification);
  if (byteVerification !== undefined) result.byte_verification = byteVerification;
  if (isRecord(raw.legacy_acceptance_receipt)) {
    result.legacy_acceptance_receipt = normalizeAcceptanceReceipt(raw.legacy_acceptance_receipt);
  }
  return result;
}

function normalizeMaster(raw: unknown): ScriptWorkbenchMaster {
  const source = isRecord(raw) ? raw : {};
  const status = source.status === "ready"
    ? "machine_complete"
    : isOneOf(source.status, ["pending", "machine_complete", "stale"] as const) ? source.status : "pending";
  const duration = Number(source.duration);
  const result: ScriptWorkbenchMaster = {
    ...source,
    status,
    input_sha256: cleanString(source.input_sha256 ?? source.content_sha256, "", 64).toLowerCase(),
    path: cleanString(source.path, "", MAX_LONG_TEXT_LENGTH),
    sha256: cleanString(source.sha256 ?? source.output_sha256, "", 64).toLowerCase(),
    mime_type: cleanString(source.mime_type ?? source.mimeType, "video/mp4", MAX_SHORT_TEXT_LENGTH).toLowerCase(),
    duration: Number.isFinite(duration) && duration >= 0 ? duration : 0,
  };
  const byteVerification = normalizeByteVerification(source.byte_verification ?? source.byteVerification);
  if (byteVerification !== undefined) result.byte_verification = byteVerification;
  return result;
}

function normalizeQcReceipt(raw: unknown): ScriptWorkbenchQcReceipt {
  const source = isRecord(raw) ? raw : {};
  const verdict = isOneOf(source.verdict, ["pending", "pass", "block", "stale"] as const) ? source.verdict : "pending";
  const result: ScriptWorkbenchQcReceipt = {
    ...source,
    verdict,
    reviewer_kind: cleanString(source.reviewer_kind ?? source.reviewerKind, "", MAX_SHORT_TEXT_LENGTH),
    content_sha256: cleanString(source.content_sha256, "", 64).toLowerCase(),
    master_sha256: cleanString(source.master_sha256 ?? source.output_sha256, "", 64).toLowerCase(),
    checks: cleanStringList(source.checks),
    blocks: cleanBlocks(source.blocks),
    notes: cleanString(source.notes, "", MAX_LONG_TEXT_LENGTH),
    reviewed_at: cleanString(source.reviewed_at ?? source.reviewedAt, "", MAX_SHORT_TEXT_LENGTH),
    receipt_path: cleanString(source.receipt_path ?? source.receiptPath, "", MAX_LONG_TEXT_LENGTH),
    receipt_sha256: cleanString(source.receipt_sha256 ?? source.receiptSha256, "", 64).toLowerCase(),
  };
  const byteVerification = normalizeByteVerification(source.byte_verification ?? source.byteVerification);
  if (byteVerification !== undefined) result.byte_verification = byteVerification;
  return result;
}

export function hasRealScriptWorkbenchAssetSource(asset: Pick<ScriptWorkbenchAsset, "source" | "sha256" | "path" | "attachmentId" | "nodeId" | "imageUrl" | "byte_verification">): boolean {
  if (asset.source === "none" || !isSha256(asset.sha256)) return false;
  if (!hasDurableScriptWorkbenchByteVerification(asset.byte_verification, asset.sha256)) return false;
  if (asset.path?.trim() || asset.attachmentId?.trim() || asset.nodeId?.trim()) return true;
  const imageUrl = asset.imageUrl?.trim();
  if (!imageUrl) return false;
  return /^(?:https?:\/\/|data:image\/|\/)/i.test(imageUrl) && !imageUrl.startsWith("blob:");
}

export function deriveScriptWorkbenchSteps(
  input: Pick<ScriptWorkbenchDocument, "shots" | "assets">,
): ScriptWorkbenchSteps {
  const shotsDone = input.shots.length > 0 && input.shots.every(isShotComplete);
  const assetsDone =
    shotsDone && input.assets.every(
      (asset) => ["machine_complete", "accepted"].includes(asset.status) && hasRealScriptWorkbenchAssetSource(asset),
    );
  const promptsDone =
    input.shots.length > 0 && input.shots.every((shot) => Boolean(shot.final_prompt.trim()));
  return {
    shots: shotsDone ? "done" : "active",
    assets: assetsDone ? "done" : shotsDone ? "active" : "pending",
    prompts: promptsDone ? "done" : assetsDone ? "active" : "pending",
  };
}

function hasTimezoneTimestamp(value: string): boolean {
  return /(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value));
}

function isNamedHuman(value: string): boolean {
  const reviewer = value.trim();
  return reviewer.length >= 2 && !/(?:agent|delegate|auto|robot|system|model|助手|代理)/iu.test(reviewer);
}

function humanReceiptPasses(receipt: ScriptWorkbenchAcceptanceReceipt, contentSha: string, outputSha: string): boolean {
  return receipt.reviewer_kind === "human"
    && isNamedHuman(receipt.reviewer_name)
    && receipt.verdict === "accepted"
    && receipt.content_sha256 === contentSha
    && receipt.output_sha256 === outputSha
    && receipt.criteria.length > 0
    && receipt.blocks.length === 0
    && hasTimezoneTimestamp(receipt.reviewed_at)
    && receipt.confirmation.kind === "current_artifact_bytes"
    && receipt.confirmation.artifact_sha256 === outputSha
    && receipt.confirmation.current_pixels_reviewed
    && receipt.confirmation.decision === "accept"
    && Boolean(receipt.confirmation.statement.trim());
}

function machineReceiptPasses(receipt: ScriptWorkbenchMachineReceipt, contentSha: string, outputSha: string): boolean {
  return ["delegated_agent", "human"].includes(receipt.reviewer_kind)
    && receipt.verdict === "pass"
    && receipt.content_sha256 === contentSha
    && receipt.output_sha256 === outputSha
    && receipt.checks.length > 0
    && receipt.blocks.length === 0;
}

function assetIsAccepted(asset: ScriptWorkbenchAsset, document: ScriptWorkbenchDocument): boolean {
  return asset.status === "accepted"
    && hasRealScriptWorkbenchAssetSource(asset)
    && asset.acceptance_receipt !== undefined
    && humanReceiptPasses(asset.acceptance_receipt, document.content_sha256, asset.sha256);
}

function resultIsMachineComplete(result: ScriptWorkbenchResult, document: ScriptWorkbenchDocument): boolean {
  return ["machine_complete", "accepted"].includes(result.review)
    && result.input_sha256 === document.content_sha256
    && Boolean(result.path)
    && isSha256(result.sha256)
    && hasDurableScriptWorkbenchByteVerification(result.byte_verification, result.sha256)
    && machineReceiptPasses(result.machine_receipt, document.content_sha256, result.sha256);
}

function resultIsAccepted(result: ScriptWorkbenchResult, document: ScriptWorkbenchDocument): boolean {
  const receipt = result.acceptance_receipt;
  return result.review === "accepted"
    && resultIsMachineComplete(result, document)
    && humanReceiptPasses(receipt, document.content_sha256, result.sha256);
}

function masterIsReady(document: ScriptWorkbenchDocument): boolean {
  return document.master.status === "machine_complete"
    && document.master.input_sha256 === document.content_sha256
    && Boolean(document.master.path)
    && isSha256(document.master.sha256)
    && hasDurableScriptWorkbenchByteVerification(document.master.byte_verification, document.master.sha256);
}

function qcReceiptPasses(document: ScriptWorkbenchDocument): boolean {
  const receipt = document.qc_receipt;
  return receipt.verdict === "pass"
    && receipt.content_sha256 === document.content_sha256
    && receipt.master_sha256 === document.master.sha256
    && Boolean(receipt.receipt_path)
    && isSha256(receipt.receipt_sha256)
    && hasDurableScriptWorkbenchByteVerification(receipt.byte_verification, receipt.receipt_sha256)
    && receipt.checks.length > 0
    && receipt.blocks.length === 0
    && ["delegated_agent", "human"].includes(receipt.reviewer_kind);
}

function finalAcceptancePasses(document: ScriptWorkbenchDocument): boolean {
  return humanReceiptPasses(
    document.final_acceptance_receipt,
    document.content_sha256,
    document.master.sha256,
  );
}

export function scriptWorkbenchMachineCompletionGaps(document: ScriptWorkbenchDocument): string[] {
  const gaps: string[] = [];
  if (!document.shots.length) gaps.push("至少需要一个镜头");
  for (const shot of document.shots) {
    if (!isShotComplete(shot)) gaps.push(`镜头 ${shot.id} 的制作字段未补齐`);
    if (!shot.final_prompt.trim()) gaps.push(`镜头 ${shot.id} 缺最终提示词`);
  }
  for (const asset of document.assets) {
    if (!assetIsAccepted(asset, document)) {
      gaps.push(`资产 ${asset.id} 缺具名真人对当前图片字节的验收回执`);
    }
  }
  for (const shot of document.shots) {
    if (!document.results.some((result) => result.shot_id === shot.id && resultIsMachineComplete(result, document))) {
      gaps.push(`镜头 ${shot.id} 缺少绑定当前内容哈希且字节已验证的 machine_complete 视频`);
    }
  }
  const activeJobs = document.jobs.filter((job) => job.input_sha256 === document.content_sha256);
  if (activeJobs.some((job) => ["queued", "running", "blocked"].includes(job.status))) gaps.push("仍有当前版本任务未结束或被硬闸阻断");
  if (!masterIsReady(document)) gaps.push("最终母版不存在、字节未验证或未绑定当前内容哈希");
  if (!qcReceiptPasses(document)) gaps.push("最终 QC 收据未通过、收据字节未验证或未同时绑定内容与母版 SHA");
  return [...new Set(gaps)];
}

export function scriptWorkbenchCompletionGaps(document: ScriptWorkbenchDocument): string[] {
  const gaps = scriptWorkbenchMachineCompletionGaps(document);
  if (!finalAcceptancePasses(document)) gaps.push("最终母版缺具名真人、带时区且绑定当前字节 SHA 的显式验收回执");
  return [...new Set(gaps)];
}

function deriveState(document: ScriptWorkbenchDocument): ScriptWorkbenchState {
  if (scriptWorkbenchCompletionGaps(document).length === 0) return "complete";
  if (scriptWorkbenchMachineCompletionGaps(document).length === 0) return "machine_complete";
  const jobs = document.jobs.filter((job) => job.input_sha256 === document.content_sha256);
  if (jobs.some((job) => job.status === "blocked")) return "blocked";
  if (jobs.some((job) => job.status === "queued" || job.status === "running")) return "running";
  const results = document.results.filter((result) => result.input_sha256 === document.content_sha256);
  if (
    jobs.some((job) => job.status === "failed")
    || results.some((result) => result.review === "rejected")
    || results.some((result) => result.review === "accepted" && !resultIsAccepted(result, document))
    || results.some((result) => ["machine_complete", "accepted"].includes(result.review) && !resultIsMachineComplete(result, document))
    || (document.master.status === "machine_complete" && !masterIsReady(document))
    || (document.qc_receipt.verdict === "pass" && !qcReceiptPasses(document))
    || document.qc_receipt.verdict === "block"
  ) return "needs_revision";
  const authoringReady = document.shots.length > 0
    && document.shots.every((shot) => isShotComplete(shot) && Boolean(shot.final_prompt.trim()))
    && document.assets.every((asset) => ["machine_complete", "accepted"].includes(asset.status) && hasRealScriptWorkbenchAssetSource(asset));
  return authoringReady ? "ready" : "draft";
}

function staleRuntime(document: ScriptWorkbenchDocument): ScriptWorkbenchDocument {
  return {
    ...document,
    jobs: document.jobs.map((job) => ({ ...job, status: "stale" })),
    results: document.results.map((result) => ({ ...result, review: "stale" })),
    master: document.master.path || document.master.sha256 || document.master.input_sha256
      ? { ...document.master, status: "stale" }
      : document.master,
    qc_receipt: document.qc_receipt.verdict === "pending"
      ? document.qc_receipt
      : { ...document.qc_receipt, verdict: "stale" },
    final_acceptance_receipt: document.final_acceptance_receipt.verdict === "pending"
      ? document.final_acceptance_receipt
      : { ...document.final_acceptance_receipt, verdict: "stale" },
  };
}

export function refreshScriptWorkbench(document: ScriptWorkbenchDocument): ScriptWorkbenchDocument {
  const contentSha256 = computeScriptWorkbenchContentSha256(document);
  let refreshed = document.content_sha256 && document.content_sha256 !== contentSha256
    ? staleRuntime(document)
    : document;
  refreshed = {
    ...refreshed,
    content_sha256: contentSha256,
    jobs: refreshed.jobs.map((job) => job.input_sha256 && job.input_sha256 !== contentSha256 ? { ...job, status: "stale" } : job),
    results: refreshed.results.map((result) => result.input_sha256 && result.input_sha256 !== contentSha256 ? { ...result, review: "stale" } : result),
    master: refreshed.master.input_sha256 && refreshed.master.input_sha256 !== contentSha256 ? { ...refreshed.master, status: "stale" } : refreshed.master,
    completion: { definition: SCRIPT_WORKBENCH_COMPLETION_DEFINITION },
  };
  if (
    refreshed.qc_receipt.verdict === "pass"
    && (refreshed.qc_receipt.content_sha256 !== contentSha256 || refreshed.qc_receipt.master_sha256 !== refreshed.master.sha256 || refreshed.master.status !== "machine_complete")
  ) refreshed = { ...refreshed, qc_receipt: { ...refreshed.qc_receipt, verdict: "stale" } };
  if (refreshed.final_acceptance_receipt.verdict === "accepted" && !finalAcceptancePasses(refreshed)) {
    refreshed = { ...refreshed, final_acceptance_receipt: { ...refreshed.final_acceptance_receipt, verdict: "stale" } };
  }
  return { ...refreshed, state: deriveState(refreshed) };
}

export function normalizeScriptWorkbench(raw: unknown): ScriptWorkbenchDocument {
  const record = isRecord(raw) ? raw : {};
  const rawShots = Array.isArray(record.shots) ? record.shots : [];
  const rawAssets = Array.isArray(record.assets) ? record.assets : [];
  const current = record.schema === SCRIPT_WORKBENCH_SCHEMA && (record.skill === undefined || record.skill === SCRIPT_WORKBENCH_SKILL);
  const legacySchema = SCRIPT_WORKBENCH_LEGACY_SCHEMAS.some((schema) => schema === record.schema);
  const legacySkill = record.skill === "n2d-script-workbench" || record.skill === "app-n2d-script-workbench";
  const legacy = legacySchema || legacySkill;
  const previousMigration = current && isRecord(record.migration)
    && record.migration.human_acceptance_reconfirmation_required === true
    && record.migration.legacy_evidence_preserved === true
    ? {
        source_schema: cleanString(record.migration.source_schema, "unknown", MAX_SHORT_TEXT_LENGTH),
        human_acceptance_reconfirmation_required: true as const,
        legacy_evidence_preserved: true as const,
      }
    : undefined;
  const preserveLegacyMachineEvidence = legacy || previousMigration !== undefined;
  const runtimeCompatible = current || legacy;
  const shotIds = new Set<string>();
  const assetIds = new Set<string>();
  const rawShotRecords = rawShots.filter(isRecord);
  const rawAssetRecords = rawAssets.filter(isRecord);
  const shots = rawShotRecords
    .map((shot, index) => normalizeShot(shot, index + 1, shotIds));
  let assets = rawAssetRecords
    .map((asset, index) => normalizeAsset(asset, index + 1, assetIds, preserveLegacyMachineEvidence));
  const jobs = runtimeCompatible && Array.isArray(record.jobs) ? record.jobs.filter(isRecord).map(normalizeJob) : [];
  let results = runtimeCompatible && Array.isArray(record.results) ? record.results.filter(isRecord).map(normalizeResult) : [];
  if (legacy) {
    assets = assets.map((asset, index) => {
      const rawAsset = rawAssetRecords[index];
      const legacyReceipt = normalizeAcceptanceReceipt(
        rawAsset?.acceptance_receipt ?? rawAsset?.acceptanceReceipt ?? rawAsset?.acceptance,
      );
      return {
        ...asset,
        ...(rawAsset?.status === "accepted" ? {
          status: "machine_complete" as const,
          legacy_acceptance_receipt: legacyReceipt,
        } : {}),
        acceptance_receipt: normalizeAcceptanceReceipt(undefined),
      };
    });
    results = results.map((result) => {
      const legacyReceipt = result.acceptance_receipt;
      if (result.review !== "accepted") {
        return { ...result, acceptance_receipt: normalizeAcceptanceReceipt(undefined) };
      }
      return {
        ...result,
        legacy_acceptance_receipt: legacyReceipt,
        review: "machine_complete" as const,
        machine_receipt: normalizeMachineReceipt({
          reviewer_kind: legacyReceipt.reviewer_kind,
          verdict: legacyReceipt.verdict === "accepted" ? "pass" : "pending",
          content_sha256: legacyReceipt.content_sha256,
          output_sha256: legacyReceipt.output_sha256,
          checks: legacyReceipt.criteria,
          blocks: legacyReceipt.blocks,
          completed_at: legacyReceipt.reviewed_at,
        }),
        acceptance_receipt: normalizeAcceptanceReceipt(undefined),
      };
    });
  }
  const acceptancePolicy = record.acceptance_policy === "human" || record.acceptancePolicy === "human" ? "human" : "delegated";
  const document: ScriptWorkbenchDocument = {
    schema: SCRIPT_WORKBENCH_SCHEMA,
    skill: SCRIPT_WORKBENCH_SKILL,
    title: cleanString(record.title, SCRIPT_WORKBENCH_DEFAULT_TITLE, MAX_SHORT_TEXT_LENGTH),
    global_style: cleanString(
      record.global_style ?? record.globalStyle,
      SCRIPT_WORKBENCH_DEFAULT_STYLE,
      MAX_LONG_TEXT_LENGTH,
    ),
    acceptance_policy: acceptancePolicy,
    delivery_spec: normalizeDeliverySpec(record.delivery_spec ?? record.deliverySpec),
    shots,
    assets,
    content_sha256: runtimeCompatible ? cleanString(record.content_sha256, "", 64).toLowerCase() : "",
    state: current && isOneOf(record.state, SCRIPT_WORKBENCH_STATES) ? record.state : "draft",
    jobs,
    results,
    master: normalizeMaster(runtimeCompatible ? record.master : undefined),
    qc_receipt: normalizeQcReceipt(runtimeCompatible ? record.qc_receipt : undefined),
    final_acceptance_receipt: normalizeAcceptanceReceipt(current ? record.final_acceptance_receipt : undefined),
    completion: { definition: SCRIPT_WORKBENCH_COMPLETION_DEFINITION },
  };
  const migration = legacy ? {
    source_schema: cleanString(record.schema, "unknown", MAX_SHORT_TEXT_LENGTH),
    human_acceptance_reconfirmation_required: true as const,
    legacy_evidence_preserved: true as const,
  } : previousMigration;
  if (migration !== undefined) document.migration = migration;
  return refreshScriptWorkbench(document);
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
  return refreshScriptWorkbench({ ...document, shots });
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
  return refreshScriptWorkbench({ ...document, shots });
}

export function removeScriptWorkbenchShot(
  document: ScriptWorkbenchDocument,
  shotId: string,
): ScriptWorkbenchDocument {
  return refreshScriptWorkbench({
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
  return refreshScriptWorkbench({ ...document, shots });
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
  return refreshScriptWorkbench({ ...document, assets });
}

export function clearScriptWorkbenchAssetSource(
  document: ScriptWorkbenchDocument,
  assetId: string,
): ScriptWorkbenchDocument {
  return updateScriptWorkbenchAsset(document, assetId, {
    status: "pending",
    source: "none",
    sha256: "",
    path: null,
    attachmentId: null,
    nodeId: null,
    imageUrl: null,
    mimeType: null,
    error: null,
    byte_verification: null,
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
  return refreshScriptWorkbench({ ...document, assets });
}

export function removeScriptWorkbenchAsset(
  document: ScriptWorkbenchDocument,
  assetId: string,
): ScriptWorkbenchDocument {
  return refreshScriptWorkbench({
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
  return refreshScriptWorkbench({ ...document, shots });
}

export function setScriptWorkbenchGlobalStyle(
  document: ScriptWorkbenchDocument,
  globalStyle: string,
): ScriptWorkbenchDocument {
  const nextStyle = cleanString(globalStyle, SCRIPT_WORKBENCH_DEFAULT_STYLE, MAX_LONG_TEXT_LENGTH);
  if (nextStyle === document.global_style) return cloneScriptWorkbench(document);
  return refreshScriptWorkbench({
    ...document,
    global_style: nextStyle,
    shots: document.shots.map((shot) => ({ ...shot, final_prompt: "" })),
  });
}

export function isScriptWorkbenchReadyForBatchVideo(document: ScriptWorkbenchDocument): boolean {
  const steps = deriveScriptWorkbenchSteps(document);
  return steps.shots === "done" && steps.assets === "done" && steps.prompts === "done";
}

export function scriptWorkbenchShotVideoJobId(document: ScriptWorkbenchDocument, shotId: string): string {
  const shotDigest = scriptWorkbenchSha256Bytes(new TextEncoder().encode(shotId)).slice(0, 10);
  return `job-shot-video-${document.content_sha256.slice(0, 12)}-${shotDigest}`;
}

/** Create durable ready-to-submit video jobs without claiming that a backend accepted them. */
export function prepareScriptWorkbenchVideoJobs(document: ScriptWorkbenchDocument): ScriptWorkbenchDocument {
  const current = refreshScriptWorkbench(document);
  const jobs = [...current.jobs];
  for (const shot of current.shots) {
    const existingIndex = jobs.findIndex((job) => (
      job.kind === "shot_video"
      && job.shot_id === shot.id
      && job.input_sha256 === current.content_sha256
    ));
    if (existingIndex >= 0) {
      const existing = jobs[existingIndex];
      if (existing && ["draft", "failed", "cancelled", "stale"].includes(existing.status)) {
        jobs[existingIndex] = { ...existing, status: "ready", error: "" };
      }
      continue;
    }
    jobs.push({
      id: scriptWorkbenchShotVideoJobId(current, shot.id),
      kind: "shot_video",
      shot_id: shot.id,
      input_sha256: current.content_sha256,
      status: "ready",
      run_id: "",
      error: "",
    });
  }
  return refreshScriptWorkbench({ ...current, jobs });
}

export function updateScriptWorkbenchJobStatus(
  document: ScriptWorkbenchDocument,
  jobId: string,
  status: ScriptWorkbenchJobStatus,
  error = "",
): ScriptWorkbenchDocument {
  return refreshScriptWorkbench({
    ...document,
    jobs: document.jobs.map((job) => job.id === jobId ? { ...job, status, error } : job),
  });
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
  if ("style_locked" in document || "styleLocked" in document) errors.push({ path: "style_locked", message: "v3 不持久化风格锁" });
  if ("steps" in document) errors.push({ path: "steps", message: "v3 阶段进度只能由界面派生" });
  if (!isOneOf(document.state, SCRIPT_WORKBENCH_STATES)) errors.push({ path: "state", message: "状态无效" });
  if (document.acceptance_policy !== "delegated" && document.acceptance_policy !== "human") {
    errors.push({ path: "acceptance_policy", message: "必须为 delegated 或 human" });
  }
  if (!isRecord(document.delivery_spec)) errors.push({ path: "delivery_spec", message: "必须是 object" });

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
        value.status === "machine_complete" || value.status === "accepted"
      ) {
        const evidence: Pick<
          ScriptWorkbenchAsset,
          "source" | "sha256" | "path" | "attachmentId" | "nodeId" | "imageUrl" | "byte_verification"
        > = {
          source: isOneOf(value.source, SCRIPT_WORKBENCH_ASSET_SOURCES) ? value.source : "none",
          sha256: cleanString(value.sha256, "", 64).toLowerCase(),
        };
        const sourcePath = cleanOptionalString(value.path);
        const attachmentId = cleanOptionalString(value.attachmentId ?? value.attachment_id, MAX_ID_LENGTH);
        const nodeId = cleanOptionalString(value.nodeId ?? value.node_id, MAX_ID_LENGTH);
        const imageUrl = cleanOptionalString(value.imageUrl ?? value.image_url);
        const byteVerification = normalizeByteVerification(value.byte_verification ?? value.byteVerification);
        if (sourcePath !== undefined) evidence.path = sourcePath;
        if (attachmentId !== undefined) evidence.attachmentId = attachmentId;
        if (nodeId !== undefined) evidence.nodeId = nodeId;
        if (imageUrl !== undefined) evidence.imageUrl = imageUrl;
        if (byteVerification !== undefined) evidence.byte_verification = byteVerification;
        if (!hasRealScriptWorkbenchAssetSource(evidence)) {
          errors.push({ path, message: "machine_complete 时必须有可持久来源、64 位内容 SHA 与字节验证证据" });
        }
      }
    });
  }
  if (!Array.isArray(document.jobs)) errors.push({ path: "jobs", message: "必须是 array" });
  if (!Array.isArray(document.results)) {
    errors.push({ path: "results", message: "必须是 array" });
  }
  if (!isRecord(document.master)) errors.push({ path: "master", message: "必须是 object" });
  if (!isRecord(document.qc_receipt)) errors.push({ path: "qc_receipt", message: "必须是 object" });
  if (!isRecord(document.final_acceptance_receipt)) errors.push({ path: "final_acceptance_receipt", message: "必须是 object" });
  if (!isRecord(document.completion) || document.completion.definition !== SCRIPT_WORKBENCH_COMPLETION_DEFINITION) {
    errors.push({ path: "completion.definition", message: `必须为 ${SCRIPT_WORKBENCH_COMPLETION_DEFINITION}` });
  }
  const normalized = normalizeScriptWorkbench(document);
  normalized.results.forEach((result, index) => {
    if (result.review === "accepted" && !resultIsAccepted(result, normalized)) {
      errors.push({ path: `results[${index}]`, message: "accepted 视频必须绑定当前哈希、有效签收与可持久字节验证证据" });
    }
    if (result.review === "machine_complete" && !resultIsMachineComplete(result, normalized)) {
      errors.push({ path: `results[${index}]`, message: "machine_complete 视频必须绑定当前哈希、机器检查与可持久字节验证证据" });
    }
  });
  normalized.assets.forEach((asset, index) => {
    if (asset.status === "accepted" && !assetIsAccepted(asset, normalized)) {
      errors.push({ path: `assets[${index}]`, message: "accepted 图片必须有具名真人、带时区且绑定当前字节 SHA 的回执" });
    }
  });
  if (normalized.master.status === "machine_complete" && !masterIsReady(normalized)) {
    errors.push({ path: "master", message: "machine_complete 母版必须绑定当前哈希与可持久字节验证证据" });
  }
  if (normalized.qc_receipt.verdict === "pass" && !qcReceiptPasses(normalized)) {
    errors.push({ path: "qc_receipt", message: "pass 收据必须绑定当前母版与可持久收据字节验证证据" });
  }
  if (normalized.final_acceptance_receipt.verdict === "accepted" && !finalAcceptancePasses(normalized)) {
    errors.push({ path: "final_acceptance_receipt", message: "accepted 必须由具名真人显式绑定当前母版字节 SHA" });
  }
  if (document.content_sha256 !== normalized.content_sha256) {
    errors.push({ path: "content_sha256", message: "与规范化 authoring 内容不一致" });
  }
  if (document.state !== normalized.state) errors.push({ path: "state", message: `应由唯一完成定义派生为 ${normalized.state}` });
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
{"schema":"${SCRIPT_WORKBENCH_SCHEMA}","skill":"${SCRIPT_WORKBENCH_SKILL}","title":"脚本标题","global_style":"全局美术风格","acceptance_policy":"delegated","delivery_spec":{"container":"mp4","mime_type":"video/mp4","aspect_ratio":"16:9","resolution":"project","require_audio":true},"shots":[{"id":"shot-1","duration":5,"visual":"画面描述","scale":"中景","lighting":"光影氛围","dialogue":"对白或旁白，可为空","sound":"音效","camera":"运镜","final_prompt":"","color":""}],"assets":[{"id":"asset-1","kind":"character","name":"资产名","description":"资产描述","prompt":"资产生图提示词","status":"pending","source":"none","sha256":""}],"jobs":[],"results":[]}。
不要输出 steps 或 style_locked；state、content_sha256、master、qc_receipt 与 completion 由工作台归一化器计算。kind 只能是 character、scene、prop；新资产必须为 status=pending、source=none、sha256 为空。镜头 id 与资产 id 必须稳定且唯一。`;
