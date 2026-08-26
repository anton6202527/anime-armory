import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { SkillsService } from '../src/main/services/skills.ts'

const LEGACY_N2D_APP_SKILLS = [
  'n2d-audio-video',
  'n2d-character-turnaround',
  'n2d-first-frame-video',
  'n2d-script-workbench',
]

test('制漫剧技能列表不展示旧的画布技能别名', async () => {
  const repoRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'anime-armory-skills-'))
  const skillNames = ['n2d', 'n2d-image', ...LEGACY_N2D_APP_SKILLS]

  try {
    for (const name of skillNames) {
      const skillDir = path.join(repoRoot, 'skills', name)
      await fs.mkdir(skillDir, { recursive: true })
      await fs.writeFile(
        path.join(skillDir, 'SKILL.md'),
        `---\nname: ${name}\ndescription: test\n---\n`,
        'utf8',
      )
    }

    const skills = await new SkillsService().list(repoRoot, 'n2d')

    assert.deepEqual(skills.map((skill) => skill.dir), ['n2d', 'n2d-image'])
  } finally {
    await fs.rm(repoRoot, { recursive: true, force: true })
  }
})
