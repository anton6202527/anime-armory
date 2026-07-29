import type { SkillDefinition } from "./types";

const BUILTIN_SERIES_IDS = new Set(["novel", "n2d", "comic", "ad", "mv", "song"]);
const ALL_SKILL_FILE_LOADERS = import.meta.glob<string>(
  "../../../../skills/**/*.{md,mdx,txt,json,jsonl,yaml,yml,py,sh,js,cjs,mjs,ts,tsx,css,html,toml,ini,csv}",
  { query: "?raw", import: "default" },
);

type RawSkillFileLoader = () => Promise<string>;

type ParsedSkillPath = {
  skillName: string;
  relativePath: string;
};

function parseSkillPath(path: string): ParsedSkillPath | null {
  const match = path.match(/\/skills\/([^/]+)\/(.+)$/);
  return match ? { skillName: match[1], relativePath: match[2] } : null;
}

function seriesSkillNames(skill: SkillDefinition) {
  if (!BUILTIN_SERIES_IDS.has(skill.id)) return [];
  return [...new Set(Object.keys(ALL_SKILL_FILE_LOADERS).flatMap((path) => {
    const parsed = parseSkillPath(path);
    if (!parsed) return [];
    return parsed.skillName === skill.line || parsed.skillName.startsWith(`${skill.line}-`)
      ? [parsed.skillName]
      : [];
  }))].sort((left, right) => {
    if (left === skill.line) return -1;
    if (right === skill.line) return 1;
    return left.localeCompare(right);
  });
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
  load: RawSkillFileLoader;
};

export type SkillSourceGroup = {
  id: string;
  name: string;
  path: string;
  files: SkillSourceFile[];
};

export function listSkillSourceGroups(skill: SkillDefinition): SkillSourceGroup[] {
  const names = seriesSkillNames(skill);
  if (!names.length) {
    const path = `my-skills/${skill.skill}/SKILL.md`;
    return [{
      id: skill.skill,
      name: skill.skill,
      path: `my-skills/${skill.skill}`,
      files: [{
        id: path,
        name: "SKILL.md",
        path,
        relativePath: "SKILL.md",
        load: async () => userSkillSource(skill),
      }],
    }];
  }

  return names.map((skillName) => {
    const files = Object.entries(ALL_SKILL_FILE_LOADERS).flatMap(([path, load]) => {
      const parsed = parseSkillPath(path);
      if (!parsed || parsed.skillName !== skillName) return [];
      return [{
        id: `skills/${skillName}/${parsed.relativePath}`,
        name: parsed.relativePath.split("/").at(-1) ?? parsed.relativePath,
        path: `skills/${skillName}/${parsed.relativePath}`,
        relativePath: parsed.relativePath,
        load,
      } satisfies SkillSourceFile];
    }).sort(compareFiles);

    return {
      id: skillName,
      name: skillName,
      path: `skills/${skillName}`,
      files,
    };
  });
}

export async function loadSkillSourceFile(file: SkillSourceFile) {
  return file.load();
}
