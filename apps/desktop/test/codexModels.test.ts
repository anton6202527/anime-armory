import assert from 'node:assert/strict'
import test from 'node:test'
import { parseCodexModelCatalog } from '../src/main/services/agents'

test('Codex model catalog exposes only visible, valid, sorted model slugs', () => {
  const models = parseCodexModelCatalog({
    models: [
      { slug: 'gpt-hidden', display_name: 'Hidden', visibility: 'hide', priority: 0 },
      { slug: 'bad model; whoami', display_name: 'Unsafe', visibility: 'list', priority: 1 },
      { slug: 'gpt-5.6-terra', display_name: 'GPT-5.6-Terra', description: 'Balanced', visibility: 'list', priority: 2 },
      { slug: 'gpt-5.6-sol', display_name: 'GPT-5.6-Sol', description: 'Frontier', visibility: 'list', priority: 1 },
    ],
  })

  assert.deepEqual(models, [
    { id: 'gpt-5.6-sol', name: 'GPT-5.6-Sol', description: 'Frontier', priority: 1 },
    { id: 'gpt-5.6-terra', name: 'GPT-5.6-Terra', description: 'Balanced', priority: 2 },
  ])
})

test('Codex model catalog fails closed for malformed payloads', () => {
  assert.deepEqual(parseCodexModelCatalog(null), [])
  assert.deepEqual(parseCodexModelCatalog({ models: 'not-an-array' }), [])
})
