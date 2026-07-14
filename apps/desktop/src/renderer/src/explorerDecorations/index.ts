import type { SkillTreeEntry } from "../types";

export type WorkTreeDecorationKind = "untracked" | "modified" | "deleted";

export type WorkTreeDecoration = {
  kind: WorkTreeDecorationKind;
  marker: "U" | "M" | "D";
  rollup: boolean;
};

const PRIORITY: Record<WorkTreeDecorationKind, number> = {
  deleted: 3,
  modified: 2,
  untracked: 1,
};

function kindFromStatus(status?: string): WorkTreeDecorationKind | null {
  switch (status) {
    case "u":
    case "added":
    case "untracked":
      return "untracked";
    case "m":
    case "modified":
      return "modified";
    case "d":
    case "deleted":
      return "deleted";
    default:
      return null;
  }
}

function markerForKind(kind: WorkTreeDecorationKind): WorkTreeDecoration["marker"] {
  if (kind === "modified") return "M";
  if (kind === "deleted") return "D";
  return "U";
}

function parentPaths(rel: string): string[] {
  const parents: string[] = [];
  let cursor = rel;
  while (true) {
    const idx = cursor.lastIndexOf("/");
    if (idx <= 0) return parents;
    cursor = cursor.slice(0, idx);
    parents.push(cursor);
  }
}

function chooseKind(
  current: WorkTreeDecorationKind | undefined,
  incoming: WorkTreeDecorationKind,
): WorkTreeDecorationKind {
  if (!current || PRIORITY[incoming] > PRIORITY[current]) return incoming;
  return current;
}

function setDecoration(
  out: Map<string, WorkTreeDecoration>,
  path: string,
  kind: WorkTreeDecorationKind,
  rollup: boolean,
) {
  const existing = out.get(path);
  const nextKind = chooseKind(existing?.kind, kind);
  out.set(path, {
    kind: nextKind,
    marker: markerForKind(nextKind),
    rollup: Boolean(existing?.rollup && existing.kind === nextKind) || rollup,
  });
}

export function buildWorkTreeDecorations(entries: SkillTreeEntry[]): Map<string, WorkTreeDecoration> {
  const out = new Map<string, WorkTreeDecoration>();
  const knownDirs = new Set(entries.filter((entry) => entry.is_dir).map((entry) => entry.path));

  for (const entry of entries) {
    if (entry.truncated) continue;
    const kind = kindFromStatus(entry.status);
    if (!kind) continue;

    setDecoration(out, entry.path, kind, entry.is_dir);
    if (!entry.is_dir) {
      for (const parent of parentPaths(entry.path)) {
        if (knownDirs.has(parent)) setDecoration(out, parent, kind, true);
      }
    }
  }

  return out;
}
