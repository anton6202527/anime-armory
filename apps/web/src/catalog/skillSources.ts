import type { SkillDefinition } from "./types";

const BUILTIN_SERIES_IDS = new Set(["novel", "n2d", "comic", "ad", "mv", "song"]);
const ALL_SKILL_SOURCE_LOADERS = import.meta.glob<string>("../../../../skills/*/SKILL.md", {
  query: "?raw",
  import: "default",
});

function skillNameFromPath(path: string) {
  return path.match(/\/skills\/([^/]+)\/SKILL\.md$/)?.[1] ?? "";
}

function seriesSourceLoaders(skill: SkillDefinition) {
  if (!BUILTIN_SERIES_IDS.has(skill.id)) return [];
  return Object.entries(ALL_SKILL_SOURCE_LOADERS)
    .filter(([path]) => {
      const name = skillNameFromPath(path);
      return name === skill.line || name.startsWith(`${skill.line}-`);
    })
    .sort(([leftPath], [rightPath]) => {
      const left = skillNameFromPath(leftPath);
      const right = skillNameFromPath(rightPath);
      if (left === skill.line) return -1;
      if (right === skill.line) return 1;
      return left.localeCompare(right);
    });
}

function displayPath(path: string) {
  const marker = "/skills/";
  const index = path.lastIndexOf(marker);
  return index >= 0 ? path.slice(index + 1) : path;
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
  source: string;
};

export async function loadSkillSourceFiles(skill: SkillDefinition): Promise<SkillSourceFile[]> {
  const loaders = seriesSourceLoaders(skill);
  if (!loaders.length) {
    const path = `my-skills/${skill.skill}/SKILL.md`;
    return [{ id: path, name: skill.skill, path, source: userSkillSource(skill) }];
  }
  return Promise.all(loaders.map(async ([path, loader]) => {
    const name = skillNameFromPath(path);
    const display = displayPath(path);
    return {
      id: display,
      name,
      path: display,
      source: await loader(),
    };
  }));
}
