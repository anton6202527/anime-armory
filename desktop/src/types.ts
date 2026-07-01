// Shared TS types. These mirror the Rust command return shapes and the
// repo's `--json` contracts (review_ui_第N集.json / storyboard.json / run.py next --json).

export type LineKey = "n2d" | "ad" | "mv" | "song" | "novel";

export interface WorkRoot {
  name: string;
  path: string; // absolute
  has_progress: boolean;
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

export interface PermissionProbe {
  label: string;
  path: string;
  ok: boolean;
  error: string;
}

export interface PermissionPrepResult {
  probes: PermissionProbe[];
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
  mediaRevision?: number; // frontend cache-buster for regenerated files at the same path
  qa: QaFlag[];
}

export interface CanvasSeam {
  from: string;
  to: string;
  transition?: string;
}

export interface CanvasData {
  source: "review_ui" | "storyboard" | "none";
  episode: string;
  title?: string;
  total_duration?: number;
  episodes: string[]; // all episodes discovered for the switcher
  clips: CanvasClip[];
  seams: CanvasSeam[];
}

// Loose mirror of run.py next --json NextAction.
export interface NextAction {
  frontier?: { ep?: string; stage_key?: string; label?: string; owner?: string };
  stop_reason?: string;
  action_card?: {
    headline?: string;
    to_user?: string;
    exact_command?: string;
  };
  gate?: { blocked?: boolean; return_to_stage?: string; findings_path?: string };
  raw?: unknown;
  error?: string;
}
