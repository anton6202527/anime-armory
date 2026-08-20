export const APP_CANVAS_SKILL_IDS = {
  scriptWorkbench: "app-script-workbench",
  characterTurnaround: "app-character-turnaround",
  firstFrameVideo: "app-first-frame-video",
  audioVideo: "app-audio-video",
} as const;

export type AppCanvasSkillId = (typeof APP_CANVAS_SKILL_IDS)[keyof typeof APP_CANVAS_SKILL_IDS];

const LEGACY_APP_SKILL_IDS: Readonly<Record<string, AppCanvasSkillId>> = {
  "n2d-script-workbench": APP_CANVAS_SKILL_IDS.scriptWorkbench,
  "app-n2d-script-workbench": APP_CANVAS_SKILL_IDS.scriptWorkbench,
  "n2d-character-turnaround": APP_CANVAS_SKILL_IDS.characterTurnaround,
  "app-n2d-character-turnaround": APP_CANVAS_SKILL_IDS.characterTurnaround,
  "n2d-first-frame-video": APP_CANVAS_SKILL_IDS.firstFrameVideo,
  "app-n2d-first-frame-video": APP_CANVAS_SKILL_IDS.firstFrameVideo,
  "n2d-audio-video": APP_CANVAS_SKILL_IDS.audioVideo,
  "app-n2d-audio-video": APP_CANVAS_SKILL_IDS.audioVideo,
};

const APP_CANVAS_SKILL_ID_SET = new Set<string>(Object.values(APP_CANVAS_SKILL_IDS));

/** Normalize persisted pre-app-prefix IDs without changing unrelated series or user skills. */
export function canonicalAppSkillId(skillId: unknown): string | null {
  if (typeof skillId !== "string" || !skillId) return null;
  return LEGACY_APP_SKILL_IDS[skillId] ?? skillId;
}

export function canonicalAppSkillPath(skillId: unknown): string | null {
  const canonical = canonicalAppSkillId(skillId);
  return canonical && APP_CANVAS_SKILL_ID_SET.has(canonical)
    ? `skills/app/${canonical}/SKILL.md`
    : null;
}

/** Rewrite human-readable persisted labels/paths while keeping legacy IDs hidden from discovery. */
export function canonicalAppSkillText(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  let migrated = value;
  const legacyEntries = Object.entries(LEGACY_APP_SKILL_IDS)
    .sort(([left], [right]) => right.length - left.length);
  for (const [legacy, canonical] of legacyEntries) {
    migrated = migrated.replaceAll(legacy, canonical);
  }
  for (const canonical of APP_CANVAS_SKILL_ID_SET) {
    migrated = migrated.replaceAll(`skills/${canonical}/SKILL.md`, `skills/app/${canonical}/SKILL.md`);
  }
  return migrated;
}
