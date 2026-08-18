import assert from 'node:assert/strict'
import { mkdir, mkdtemp, symlink, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'

import { ApiError } from '../src/errors.ts'
import { SkillRegistry } from '../src/skill-registry.ts'

async function fixture(): Promise<string> {
  const root = await mkdtemp(path.join(os.tmpdir(), 'anime-armory-skills-'))
  await mkdir(path.join(root, 'n2d', 'n2d-fixture', 'references'), { recursive: true })
  await writeFile(path.join(root, 'n2d', 'SKILL.md'), '---\nname: n2d\ndescription: dispatcher\n---\n# n2d\n')
  await writeFile(
    path.join(root, 'n2d', 'n2d-fixture', 'SKILL.md'),
    '---\nname: n2d-fixture\ndescription: fixture skill\n---\n# Fixture\nReal instructions.\n',
  )
  await writeFile(path.join(root, 'n2d', 'n2d-fixture', 'references', 'guide.md'), '# Guide\n')
  await writeFile(path.join(root, 'n2d', 'n2d-fixture', 'references', 'secret.bin'), 'not exposed')
  await symlink(path.join(root, 'n2d', 'SKILL.md'), path.join(root, 'n2d', 'n2d-fixture', 'references', 'link.md'))
  return root
}

test('discovers line, child, and safe text sources without exposing paths', async () => {
  const root = await fixture()
  const registry = new SkillRegistry(root)
  const skills = await registry.list()
  assert.deepEqual(skills.map((skill) => skill.id), ['n2d', 'n2d-fixture'])
  const fixtureSkill = await registry.get('n2d-fixture')
  assert.equal(fixtureSkill.line, 'n2d')
  assert.match(fixtureSkill.definition, /Real instructions/)
  assert.equal(JSON.stringify(fixtureSkill).includes(root), false)
  const sources = await registry.listSources('n2d-fixture')
  assert.deepEqual(sources.map((source) => source.path), ['references/guide.md', 'SKILL.md'])
  assert.equal((await registry.readSource('n2d-fixture', 'references/guide.md')).content, '# Guide\n')
})

test('rejects source traversal and unsupported extensions', async () => {
  const registry = new SkillRegistry(await fixture())
  await assert.rejects(
    registry.readSource('n2d-fixture', '../SKILL.md'),
    (error: unknown) => error instanceof ApiError && error.code === 'invalid_source_path',
  )
  await assert.rejects(
    registry.readSource('n2d-fixture', 'references/secret.bin'),
    (error: unknown) => error instanceof ApiError && error.code === 'unsupported_source_type',
  )
})
