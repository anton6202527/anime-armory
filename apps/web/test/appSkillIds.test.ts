import assert from "node:assert/strict";
import test from "node:test";

import {
  APP_CANVAS_SKILL_IDS,
  canonicalAppSkillId,
  canonicalAppSkillPath,
} from "../src/features/canvas/appSkillIds.ts";

test("current-session standalone app skills use the nested canonical path", () => {
  for (const skillId of Object.values(APP_CANVAS_SKILL_IDS)) {
    assert.equal(canonicalAppSkillId(skillId), skillId);
    assert.equal(canonicalAppSkillPath(skillId), `skills/app/${skillId}/SKILL.md`);
  }
});

test("legacy standalone ids migrate before their current-session path is stored", () => {
  assert.equal(canonicalAppSkillId("n2d-character-turnaround"), APP_CANVAS_SKILL_IDS.characterTurnaround);
  assert.equal(
    canonicalAppSkillPath("n2d-character-turnaround"),
    `skills/app/${APP_CANVAS_SKILL_IDS.characterTurnaround}/SKILL.md`,
  );
});
