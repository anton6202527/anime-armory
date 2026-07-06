// Shared TS types. These mirror the Rust command return shapes and the
// repo's `--json` contracts (review_ui_第N集.json / storyboard.json / run.py next --json).

export type LineKey = "n2d" | "comic" | "ad" | "mv" | "song" | "novel";

export interface WorkRoot {
  name: string;
  path: string; // absolute
  has_progress: boolean;
  is_demo: boolean;
  is_reference?: boolean;
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
  frames: CanvasFrame[];
  prompt?: string;
  mediaRevision?: number; // frontend cache-buster for regenerated files at the same path
  qa: QaFlag[];
  score?: number;
  qa_blocks: number;
  qa_warnings: number;
  qa_infos: number;
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
  source: "review_ui" | "storyboard" | "none";
  episode: string;
  title?: string;
  total_duration?: number;
  episodes: string[]; // all episodes discovered for the switcher
  clips: CanvasClip[];
  seams: CanvasSeam[];
  quality?: CanvasQualitySummary;
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
