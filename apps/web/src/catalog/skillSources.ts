import { apiJson } from "../lib/api";
import type { SkillDefinition } from "./types";

const BUILTIN_SERIES_IDS = new Set(["novel", "n2d", "comic", "ad", "mv", "song"]);
const MAX_SOURCE_LIST_BYTES = 2 * 1024 * 1024;
const MAX_SOURCE_FILE_BYTES = 1024 * 1024;

function record(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function unwrap(value: unknown, property: string): unknown {
  const outer = record(value);
  if (!outer) return value;
  if (outer[property] !== undefined) return outer[property];
  const data = record(outer.data);
  return data?.[property] ?? outer.data ?? value;
}

function safeRelativePath(value: unknown): value is string {
  if (typeof value !== "string" || !value || value.length > 1_024 || value.startsWith("/") || value.includes("\\")) {
    return false;
  }
  return !value.split("/").some((segment) => !segment || segment === "." || segment === "..");
}

function compareFiles(left: SkillSourceFile, right: SkillSourceFile) {
  if (left.relativePath === "SKILL.md") return -1;
  if (right.relativePath === "SKILL.md") return 1;
  const leftDepth = left.relativePath.split("/").length;
  const rightDepth = right.relativePath.split("/").length;
  if (leftDepth !== rightDepth) return leftDepth - rightDepth;
  return left.relativePath.localeCompare(right.relativePath);
}

function yamlString(value: string) {
  return JSON.stringify(value);
}

function userSkillSource(skill: SkillDefinition) {
  return [
    "---",
    `name: ${skill.skill}`,
    `description: ${yamlString(skill.description)}`,
    `line: ${skill.line}`,
    `category: ${yamlString(skill.category)}`,
    `media_type: ${skill.mediaType}`,
    "---",
    "",
    `# ${skill.title}`,
    "",
    skill.description,
    "",
    "## Use when",
    "",
    ...skill.useCases.map((item) => `- ${item}`),
    "",
    "## Workflow",
    "",
    ...skill.steps.map((item, index) => `${index + 1}. ${item}`),
    "",
    "## Guide",
    "",
    skill.guide,
    "",
  ].join("\n");
}

export type SkillSourceFile = {
  id: string;
  name: string;
  path: string;
  relativePath: string;
  skillId: string;
  sourcePath: string;
  inlineSource?: string;
  size?: number;
};

export type SkillSourceGroup = {
  id: string;
  name: string;
  path: string;
  files: SkillSourceFile[];
};

function localSkillSourceGroups(skill: SkillDefinition): SkillSourceGroup[] {
  const directoryPath = `my-skills/${skill.skill}`;
  const path = `${directoryPath}/SKILL.md`;
  return [{
    id: skill.skill,
    name: skill.skill,
    path: directoryPath,
    files: [{
      id: path,
      name: "SKILL.md",
      path,
      relativePath: "SKILL.md",
      skillId: skill.id,
      sourcePath: "SKILL.md",
      inlineSource: userSkillSource(skill),
    }],
  }];
}

export async function listSkillSourceGroups(skill: SkillDefinition): Promise<SkillSourceGroup[]> {
  if (!BUILTIN_SERIES_IDS.has(skill.id)) return localSkillSourceGroups(skill);

  const value = await apiJson<unknown>(`/v1/skills/${encodeURIComponent(skill.id)}/sources`, {
    method: "GET",
    timeoutMs: 15_000,
    maxResponseBytes: MAX_SOURCE_LIST_BYTES,
  });
  const sources = unwrap(value, "sources");
  if (!Array.isArray(sources)) throw new Error("后端返回的 Skill 源文件列表格式无效");

  const rootPath = `skills/${skill.line}`;
  const groups = new Map<string, SkillSourceGroup>();
  for (const item of sources) {
    const source = record(item);
    if (!source || !safeRelativePath(source.path)) continue;
    const sourcePath = source.path;
    const segments = sourcePath.split("/");
    const possibleChild = segments[0] ?? "";
    const isChild = possibleChild.startsWith(`${skill.line}-`) && segments.length > 1;
    const groupId = isChild ? possibleChild : skill.id;
    const groupPath = isChild ? `${rootPath}/${possibleChild}` : rootPath;
    const relativePath = isChild ? segments.slice(1).join("/") : sourcePath;
    const group = groups.get(groupId) ?? {
      id: groupId,
      name: groupId,
      path: groupPath,
      files: [],
    };
    group.files.push({
      id: `${skill.id}:${sourcePath}`,
      name: relativePath.split("/").at(-1) ?? relativePath,
      path: `${groupPath}/${relativePath}`,
      relativePath,
      skillId: skill.id,
      sourcePath,
      ...(typeof source.size === "number" && Number.isSafeInteger(source.size) && source.size >= 0
        ? { size: source.size }
        : {}),
    });
    groups.set(groupId, group);
  }

  return [...groups.values()]
    .map((group) => ({ ...group, files: group.files.sort(compareFiles) }))
    .sort((left, right) => {
      if (left.id === skill.id) return -1;
      if (right.id === skill.id) return 1;
      return left.id.localeCompare(right.id);
    });
}

export async function loadSkillSourceFile(file: SkillSourceFile): Promise<string> {
  if (file.inlineSource !== undefined) return file.inlineSource;
  const value = await apiJson<unknown>(
    `/v1/skills/${encodeURIComponent(file.skillId)}/source?path=${encodeURIComponent(file.sourcePath)}`,
    {
      method: "GET",
      timeoutMs: 15_000,
      maxResponseBytes: MAX_SOURCE_FILE_BYTES,
    },
  );
  if (typeof value === "string") return value;
  const source = record(unwrap(value, "source")) ?? record(value);
  if (typeof source?.content !== "string") throw new Error("后端返回的 Skill 源文件格式无效");
  return source.content;
}
