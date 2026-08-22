// Shared TS types. These mirror the Rust command return shapes and the
// repo's `--json` contracts (review_ui_第N集.json / storyboard.json / run.py next --json).

export type LineKey = "n2d" | "comic" | "ad" | "mv" | "song" | "novel";

// Storage policy per creative line. "local" lines (写小说 / 制漫剧) keep their
// works on disk by default; "cloud" lines live in R2 and are downloaded on
// demand (Stage 1: reuses the public demo pipeline; Stage 2 adds sign-in +
// per-user upload/sync).
export type LineStorage = "local" | "cloud";
export const LINE_STORAGE: Record<LineKey, LineStorage> = {
  novel: "local",
  n2d: "local",
  comic: "cloud",
  ad: "cloud",
  mv: "cloud",
  song: "cloud",
};
export function isCloudLine(line: LineKey): boolean {
  return LINE_STORAGE[line] === "cloud";
}

export interface WorkRoot {
  name: string;
  path: string; // absolute
  has_progress: boolean;
  is_demo: boolean;
  cover?: string | null; // absolute path to a cover image (from _meta.json), or null
  synopsis?: string | null; // short synopsis text (from _meta.json), or null
}

export interface DemoDownloadInfo {
  line: string;
  line_key: LineKey;
  name: string;
  rel: string;
  asset_name: string;
  download_url: string;
  sha256?: string | null;
  size?: number | null;
  source: string;
  installed: boolean;
  path?: string | null;
}

export interface DemoInstallResult {
  root: WorkRoot;
  already_installed: boolean;
}

export interface LineInfo {
  line: LineKey;
  label: string;
  dir: string; // absolute product dir (创作区/制漫剧/ etc.)
  view: "canvas" | "files" | "audio";
  roots: WorkRoot[];
}

// One skill in a line's roster (parsed from skills/<name>/SKILL.md frontmatter).
export interface SkillInfo {
  name: string;
  description: string;
  dir: string; // directory name under skills/ (used to fetch its file tree)
}

// One node in a skill's directory tree (flat list + depth, dirs before files).
export interface SkillTreeEntry {
  name: string;
  path: string; // relative to the skill dir, e.g. "scripts/market.py"
  depth: number;
  is_dir: boolean;
  size?: number;
  mtime?: number;
  truncated?: boolean;
  // Change marker vs the work's local baseline (work_tree only).
  // The desktop UI only uses this for the aggregate changed-file count.
  status?: string;
}

export interface WorkDirListing {
  entries: SkillTreeEntry[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
}

export interface WorkSnapshot {
  signature: string;
  file_count: number;
  dir_count: number;
  capped?: boolean;
}

export interface WorkChangeSummary {
  changed: number;
  deleted: number;
  scanned?: number;
  capped?: boolean;
}

export type WorkChangeKind = "added" | "modified" | "deleted" | "unchanged";

export interface WorkChangeEntry {
  path: string;
  kind: WorkChangeKind;
  old_size?: number | null;
  new_size?: number | null;
  old_mtime?: number | null;
  new_mtime?: number | null;
  text_available: boolean;
}

export interface WorkChanges {
  changes: WorkChangeEntry[];
  scanned?: number;
  capped?: boolean;
}

export interface WorkChangeDetail {
  path: string;
  kind: WorkChangeKind;
  old_text: string;
  new_text: string;
  text_available: boolean;
  message: string;
}

export interface WorkSearchMatch {
  line: number;
  preview: string;
}

export interface WorkSearchResult {
  path: string;
  name: string;
  size: number;
  name_match: boolean;
  matches: WorkSearchMatch[];
}

export interface WorkSearchResponse {
  query: string;
  results: WorkSearchResult[];
  scanned: number;
  capped: boolean;
}

export interface WorkFileWriteResult {
  size: number;
  mtime: number;
}

export interface ImportWorkSourcesResult {
  root: string;
  name: string;
  imported: string[];
}

// One locally-detected AI agent CLI (from the Rust detect_agents command).
export interface AgentInfo {
  id: string;
  name: string;
  command: string; // launch command to run in the terminal
  found: boolean;
  path: string;
  image: "yes" | "maybe" | "no"; // image-generation (生图) capability
  note: string;
}

// QA flag, normalized from review_ui qa_flags / gate findings.
export interface QaFlag {
  severity: "block" | "warn" | "info" | string;
  status?: string;
  dimension?: string;
  message?: string;
  score?: number;
}

export interface CanvasFrame {
  role: string;
  label: string;
  abs?: string;
  exists: boolean;
  revision?: string;
  at_sec?: number;
  prompt?: string;
}

// One clip node on the canvas (normalized in Rust from review_ui or storyboard).
export interface CanvasClip {
  id: string;
  number?: number;
  label: string;
  duration?: number;
  scene?: string;
  rhythm?: string;
  template?: string;
  first_frame_abs?: string; // absolute path, may not exist yet
  first_frame_exists: boolean;
  video_abs?: string;
  video_exists: boolean;
  video_revision?: string;
  frames: CanvasFrame[];
  prompt?: string;
  qa: QaFlag[];
  score?: number;
  qa_blocks: number;
  qa_warnings: number;
  qa_infos: number;
}

export type CanvasGenerationKind = "image" | "video";

/** One project-backed model/backend choice shown in the canvas generation composer. */
export interface CanvasGenerationModel {
  id: string;
  label: string;
  kind: CanvasGenerationKind;
  channel?: string;
  description?: string;
  available: boolean;
  preferred?: boolean;
  premium?: boolean;
  min_duration?: number;
  max_duration?: number;
  resolutions: string[];
  modes: string[];
  native_audio: boolean;
  native_references: boolean;
  source?: string;
}

/** Defaults and verified capabilities derived from the work's settings/routes. */
export interface CanvasGenerationProfile {
  default_aspect_ratio: string;
  default_resolution: string;
  default_image_model?: string;
  default_video_model?: string;
  default_video_duration: number;
  audio_policy?: string;
  image_models: CanvasGenerationModel[];
  video_models: CanvasGenerationModel[];
}

/** Per-node controls persisted under 生产数据/canvas_generation_controls_<集>.json. */
export interface CanvasGenerationConfig {
  kind: CanvasGenerationKind;
  /** Stable media target inside one clip (panel/video/first/end/anchor:*). */
  target_slot: string;
  /** Work-root relative path that this target is allowed to replace. */
  target_output_path: string;
  model: string;
  mode: string;
  aspect_ratio: string;
  resolution: string;
  duration: number;
  audio_enabled: boolean;
  count: 1 | 2 | 4;
  reference_paths: string[];
  marks: string[];
  effects: string[];
  camera_motion: string;
  prompt_language: "project" | "zh" | "en";
  prompt_override: string;
}

export interface CanvasNodePosition {
  id: string;
  x: number;
  y: number;
}

export interface CanvasLayout {
  version: number;
  episode: string;
  updated_at_epoch_ms: number;
  nodes: CanvasNodePosition[];
}

export interface ClipEditData {
  source_rel: string;
  id: string;
  number?: number | null;
  label: string;
  duration?: number | null;
  scene: string;
  rhythm: string;
  template: string;
  prompt: string;
  image_prompt: string;
  video_prompt: string;
  positive_prompt: string;
  negative_prompt: string;
}

export type ClipEditPatch = Omit<ClipEditData, "source_rel" | "id" | "number">;

export interface CanvasSeam {
  from: string;
  to: string;
  transition?: string;
}

export interface CanvasMetric {
  label: string;
  value: string;
}

export interface CanvasScoreDimension {
  key?: string;
  label: string;
  status?: string;
  score?: number;
  blocks: number;
  warnings: number;
  infos: number;
  return_to_stage?: string;
  rerun_scope?: string;
  evidence: string[];
}

export interface CanvasReturnTask {
  return_to_stage?: string;
  scope?: string;
  affected_shots: string[];
  dimensions: string[];
}

export interface CanvasQualitySummary {
  source?: string;
  score?: number;
  verdict?: string;
  status?: string;
  blocks: number;
  warnings: number;
  infos: number;
  dimensions: CanvasScoreDimension[];
  tasks: CanvasReturnTask[];
  metrics: CanvasMetric[];
}

export interface CanvasData {
  source: "review_ui" | "storyboard" | "panel_script" | "none";
  /** SHA-256 of the exact source-file bytes parsed for this projection. */
  source_file_sha256?: string;
  /** SHA-256 of the exact _设置.md bytes used for generation_profile. */
  settings_file_sha256?: string;
  episode: string;
  title?: string;
  total_duration?: number;
  episodes: string[]; // all episodes discovered for the switcher
  shared_assets?: CanvasFrame[];
  clips: CanvasClip[];
  seams: CanvasSeam[];
  quality?: CanvasQualitySummary;
  generation_profile?: CanvasGenerationProfile;
  /** Derived production ledger. Editable content remains owned by source_rel. */
  production?: CanvasProductionState;
}

/** canvas.read 的增量应答：fs 事件多数与画布无关，renderer 带上一次的 sig 来读，
 *  未变更时只回 `{ sig, unchanged }`——省掉整棵 CanvasData 的 IPC 结构化克隆。 */
export interface CanvasReadResult {
  sig: string;
  unchanged?: boolean;
  canvas?: CanvasData;
}

/** One authoritative production state for an episode. Task execution is kept
 *  separate from the creative node lifecycle so a retry never masquerades as
 *  accepted creative work. */
export type CanvasProductionStatus =
  | "draft"
  | "ready"
  | "running"
  | "needs_revision"
  | "blocked"
  | "complete";

export type CanvasNodeLifecycle = "draft" | "ready" | "generated" | "accepted";

export type CanvasProductionTaskStatus =
  | "submitted"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "stale";

/** Editable, production-relevant input. `editable` deliberately stays
 *  adapter-neutral: n2d/comic/ad/mv may retain their own schema without the
 *  persistence layer inventing a second normalized truth. */
export interface CanvasAuthoringClipInput {
  id: string;
  editable: unknown;
  /** Canonical final media slot consumed by episode compose/export. */
  final_target: { slot: string; output_path: string };
  /** Generated/selected upstream media: excluded from the root authoring hash,
   *  included in this node's input hash for selective downstream invalidation. */
  runtime_inputs?: unknown;
  /** Upstream reference bytes for image generation; excludes the image slot
   * that this stage itself produces. */
  image_runtime_inputs?: unknown;
  ready?: boolean;
  /** Undefined is conservative and binds every asset; [] explicitly binds none. */
  asset_ids?: string[];
  /** Undefined is conservative and binds every config; [] explicitly binds none. */
  generation_config_keys?: string[];
}

export interface CanvasAuthoringAssetSummary {
  id: string;
  role?: string;
  /** SHA/revision/digest supplied by the owning adapter. */
  content_digest: string;
  summary?: unknown;
}

export interface CanvasAuthoringInput {
  authority: string;
  source_rel: string;
  /** Canonical JSON SHA-256 of the complete editable source, not a lossy UI projection. */
  source_sha256: string;
  /** SHA-256 of the effective project settings file; empty settings use SHA-256(""). */
  settings_sha256: string;
  episode: string;
  /** The selected output type consumed by episode compose/export. */
  final_stage: CanvasGenerationKind;
  /** Array order is editorial order and therefore hash-significant. */
  clips: CanvasAuthoringClipInput[];
  /** Asset order is not significant; ids and content are. */
  assets: CanvasAuthoringAssetSummary[];
  delivery_spec: unknown;
  generation_configs: Record<string, unknown>;
}

export interface CanvasProductionNodeState {
  id: string;
  /** Final selected-output dependency hash used by acceptance/completion. */
  input_hash: string;
  /** Per-stage execution hashes keep an image job current when its new image
   * becomes the downstream video stage's runtime input. */
  stage_input_hashes: Record<CanvasGenerationKind, string>;
  lifecycle: CanvasNodeLifecycle;
  media_fingerprint?: string;
  qa_blocks: number;
  qa_warnings: number;
  invalidation_reason?: string;
  invalidated_at_revision?: number;
  acceptance?: CanvasNodeAcceptanceEvidence;
  updated_at: string;
}

export interface CanvasNodeAcceptanceEvidence {
  content_hash: string;
  input_hash: string;
  output_path: string;
  output_sha256: string;
  qa_receipt_path: string;
  qa_receipt_sha256: string;
  qa_blocks: 0;
  reviewer_kind: "delegated" | "human";
  verdict: "accepted";
  job_id: string;
  accepted_at: string;
}

export interface CanvasProductionTask {
  job_id: string;
  /** A clip id, or the reserved `__episode__` target for a whole-episode run. */
  node_id: string;
  kind: string;
  /** Optional on legacy/episode tasks; required by new per-media generation jobs. */
  target_slot?: string;
  target_output_path?: string;
  /** New jobs write only this job-scoped sibling candidate. Electron main
   * validates and atomically promotes it to target_output_path. */
  candidate_output_path?: string;
  /** Absent on legacy tasks. True forbids agent-authored stable-path receipts. */
  promotion_required?: boolean;
  status: CanvasProductionTaskStatus;
  input_hash: string;
  content_hash: string;
  submitted_revision: number;
  submitted_at: string;
  updated_at: string;
  detail?: string;
}

export interface CanvasFinalArtifactEvidence {
  path: string;
  exists: boolean;
  sha256: string;
  /** Canonical episode hash used to render this exact artifact. */
  content_hash: string;
  /** SHA-256 of the ordered accepted-node output manifest used by compose/export. */
  inputs_sha256: string;
  qa_blocks: number;
  qa_receipt_path: string;
  qa_receipt_sha256: string;
  probe_passed: boolean;
  revision?: string;
}

export interface CanvasProductionCompletion {
  definition: "canvas.final_product/v1";
  complete: boolean;
  bound_content_hash?: string;
  artifact?: CanvasFinalArtifactEvidence;
  blockers: string[];
  accepted_at?: string;
}

export interface CanvasProductionHistoryEntry {
  revision: number;
  content_hash: string;
  status: CanvasProductionStatus;
  reason: string;
  changed_node_ids: string[];
  invalidated_node_ids: string[];
  created_at: string;
}

export interface CanvasProductionState {
  kind: "anime_armory_canvas_production_state";
  version: 2;
  episode: string;
  revision: number;
  content_hash: string;
  status: CanvasProductionStatus;
  authoring: CanvasAuthoringInput;
  node_fingerprints: Record<string, CanvasProductionNodeState>;
  tasks: CanvasProductionTask[];
  completion: CanvasProductionCompletion;
  history: CanvasProductionHistoryEntry[];
  created_at: string;
  updated_at: string;
}

export interface CanvasProductionSyncRequest {
  authoring: CanvasAuthoringInput;
  canvas: CanvasData;
  /** Explicit null means no current final-product evidence exists. */
  final_artifact: CanvasFinalArtifactEvidence | null;
  /** Cryptographically verified acceptances imported by the owning adapter. */
  accepted_nodes?: Record<string, CanvasNodeAcceptanceEvidence>;
  /** Adapter snapshot revision. When set, stale filesystem snapshots may not
   * overwrite a newer task/config/state commit. Null/0 means no prior state. */
  observed_revision?: number | null;
  reason?: string;
}

export interface CanvasTaskSubmitRequest {
  episode: string;
  /** Clip id, or `__episode__` for an episode-wide one-click run. */
  node_id: string;
  kind: string;
  target_slot?: string;
  target_output_path?: string;
  /** Main-owned staging contract; renderer IPC callers never disable it. */
  promotion_required?: boolean;
  expected_content_hash: string;
  detail?: string;
}

export interface CanvasTaskSubmitResult {
  state: CanvasProductionState;
  job_id: string;
  input_hash: string;
  /** Final selected-node dependency hash; differs from a target task hash. */
  node_input_hash?: string;
  content_hash: string;
  target_slot?: string;
  target_output_path?: string;
  candidate_output_path?: string;
  final_target_output_path?: string;
  final_candidate_output_path?: string;
  promotion_required: boolean;
  /** Snapshot status of the created/reused task for renderer dispatch policy. */
  task_status: CanvasProductionTaskStatus;
  /** False means an identical submitted/running job was reused. */
  created: boolean;
}

export interface CanvasAgentDispatchContext {
  root: string;
  episode: string;
  job_id: string;
}

export type CanvasAgentDispatchResult = "dispatched" | "succeeded" | "rejected";

export interface CanvasGenerationCommitResult {
  config: CanvasGenerationConfig;
  task: CanvasTaskSubmitResult;
}

export interface CanvasTaskStatusRequest {
  episode: string;
  job_id: string;
  status: Exclude<CanvasProductionTaskStatus, "submitted" | "stale">;
  detail?: string;
}

export interface CanvasNodeAcceptRequest {
  episode: string;
  node_id: string;
  expected_content_hash: string;
  expected_input_hash: string;
  evidence: CanvasNodeAcceptanceEvidence;
}

export interface CanvasFinalAcceptRequest {
  episode: string;
  expected_content_hash: string;
  artifact: CanvasFinalArtifactEvidence;
}

export interface QualityInsightMetric {
  label: string;
  value: string;
  tone?: "pass" | "warn" | "block" | "info" | string;
}

export interface QualityInsightDimension {
  key?: string;
  label: string;
  score?: number;
  value?: string;
  max?: number;
  status?: string;
  blocks: number;
  warnings: number;
  infos: number;
  detail?: string;
  evidence: string[];
}

export interface QualityInsightIssue {
  severity: "block" | "warn" | "info" | string;
  dimension?: string;
  title: string;
  message?: string;
  stage?: string;
  path?: string;
  source?: string;
}

export interface QualityInsightTask {
  priority?: string;
  title: string;
  skill?: string;
  stage?: string;
  detail?: string;
}

export interface QualityInsightArtifact {
  label: string;
  path: string;
  exists: boolean;
  kind?: string;
}

export interface QualityInsights {
  line: LineKey | string;
  episode?: string;
  status?: string;
  score?: number;
  verdict?: string;
  blocks: number;
  warnings: number;
  infos: number;
  metrics: QualityInsightMetric[];
  dimensions: QualityInsightDimension[];
  issues: QualityInsightIssue[];
  tasks: QualityInsightTask[];
  artifacts: QualityInsightArtifact[];
  source_files: string[];
}

export interface EpisodeWorkspaceIssue {
  severity?: "block" | "warn" | "info" | string;
  return_to_stage?: string;
  dimension?: string;
  loc?: string;
  message?: string;
  affected_shots?: string[];
  affected_artifacts?: string[];
  source?: string;
}

export interface EpisodeWorkspace {
  kind?: string;
  version?: number;
  root?: string;
  episode?: string;
  generated_at?: string;
  status?: "block" | "warn" | "pass" | string;
  next_action?: { label?: string; skill?: string; [key: string]: unknown };
  progress?: {
    accepted?: boolean;
    done_stages?: number;
    total_stages?: number;
    stages?: Record<string, string>;
  };
  metrics?: Record<string, unknown>;
  stage_metrics?: Record<string, Record<string, unknown>>;
  clip_summary?: {
    total?: number;
    with_video?: number;
    status?: Record<string, number>;
  };
  issues?: {
    total?: number;
    severity?: Record<string, number>;
    groups?: Array<{
      return_to_stage?: string;
      counts?: Record<string, number>;
      items?: EpisodeWorkspaceIssue[];
    }>;
  };
  return_tasks?: Array<Record<string, unknown>>;
  evidence?: Array<{
    label?: string;
    path?: string;
    exists?: boolean;
    url?: string;
  }>;
}

// Loose mirror of run.py next --json NextAction.
export interface NextAction {
  frontier?: { ep?: string; stage_key?: string; label?: string; owner?: string };
  stop_reason?: string;
  action_card?: {
    headline?: string;
    to_user?: string;
    block_reason?: string;
    exact_command?: string;
  };
  gate?: {
    stage?: string;
    blocked?: boolean;
    return_to_stage?: string;
    findings_path?: string;
    rerun_scope?: string;
  };
  raw?: unknown;
  error?: string;
}
