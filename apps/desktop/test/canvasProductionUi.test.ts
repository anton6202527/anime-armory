import assert from 'node:assert/strict'
import test from 'node:test'
import { buildCanvasProductionPrompt } from '../src/renderer/src/canvasProductionPrompt.ts'
import { deriveCanvasProductionBar } from '../src/renderer/src/components/canvasProductionBarModel.ts'
import type { CanvasProductionState } from '../src/shared/types.ts'

const HASH = 'a'.repeat(64)

function state(): CanvasProductionState {
  const now = '2026-08-21T00:00:00.000Z'
  return {
    kind: 'anime_armory_canvas_production_state',
    version: 2,
    episode: '第1集',
    revision: 3,
    content_hash: HASH,
    status: 'ready',
    authoring: {
      authority: 'n2d:storyboard',
      source_rel: '脚本/第1集/storyboard.json',
      source_sha256: 'b'.repeat(64),
      settings_sha256: 'c'.repeat(64),
      episode: '第1集',
      final_stage: 'video',
      clips: [
        { id: 'CLIP01', editable: { prompt: 'one' }, final_target: { slot: 'video', output_path: '出视频/第1集/CLIP01.mp4' } },
        { id: 'CLIP02', editable: { prompt: 'two' }, final_target: { slot: 'video', output_path: '出视频/第1集/CLIP02.mp4' } },
      ],
      assets: [],
      delivery_spec: { resolution: '1080p' },
      generation_configs: {},
    },
    node_fingerprints: {
      CLIP01: {
        id: 'CLIP01', input_hash: '1'.repeat(64), lifecycle: 'accepted',
        stage_input_hashes: { image: '6'.repeat(64), video: '1'.repeat(64) },
        media_fingerprint: '2'.repeat(64), qa_blocks: 0, qa_warnings: 0, updated_at: now,
      },
      CLIP02: {
        id: 'CLIP02', input_hash: '3'.repeat(64), lifecycle: 'ready',
        stage_input_hashes: { image: '7'.repeat(64), video: '3'.repeat(64) },
        qa_blocks: 0, qa_warnings: 0, updated_at: now,
      },
    },
    tasks: [],
    completion: {
      definition: 'canvas.final_product/v1',
      complete: false,
      blockers: ['node_not_accepted:CLIP02:ready', 'final_artifact_missing'],
    },
    history: [],
    created_at: now,
    updated_at: now,
  }
}

test('production bar has one unambiguous run, accept, then complete action', () => {
  const initial = state()
  assert.equal(deriveCanvasProductionBar(initial).action, 'run')

  const acceptReady: CanvasProductionState = {
    ...initial,
    node_fingerprints: {
      ...initial.node_fingerprints,
      CLIP02: {
        ...initial.node_fingerprints.CLIP02,
        lifecycle: 'accepted',
        media_fingerprint: '4'.repeat(64),
      },
    },
    completion: {
      ...initial.completion,
      artifact: {
        path: '合成/第1集/成片_final.mp4', exists: true,
        sha256: '5'.repeat(64), content_hash: HASH, qa_blocks: 0,
      },
      blockers: [],
    },
  }
  assert.equal(deriveCanvasProductionBar(acceptReady).action, 'accept')
  assert.equal(deriveCanvasProductionBar({
    ...acceptReady,
    status: 'complete',
    completion: { ...acceptReady.completion, complete: true, bound_content_hash: HASH },
  }).action, 'complete')
})

test('one-click prompt binds the structured run and only dirty nodes', () => {
  const promptState: CanvasProductionState = {
    ...state(),
    tasks: [{
      job_id: 'run-123',
      node_id: '__episode__',
      kind: 'production',
      target_slot: 'final',
      target_output_path: '合成/第1集/成片_最终.mp4',
      candidate_output_path: '合成/第1集/.canvas-candidates/run-123/成片_最终.mp4',
      promotion_required: true,
      status: 'submitted',
      input_hash: HASH,
      content_hash: HASH,
      submitted_revision: 3,
      submitted_at: '2026-08-21T00:00:00.000Z',
      updated_at: '2026-08-21T00:00:00.000Z',
    }],
  }
  const prompt = buildCanvasProductionPrompt('n2d', '/works/demo', '第1集', promptState, 'run-123')
  assert.match(prompt, /n2d-supervisor/)
  assert.match(prompt, /run-123/)
  assert.match(prompt, new RegExp(HASH))
  assert.match(prompt, /CLIP02/)
  assert.doesNotMatch(prompt, /当前需要处理的节点：CLIP01/)
  assert.match(prompt, /canvas_node_candidate_receipt/)
  assert.match(prompt, /canvas_final_candidate_receipt/)
  assert.match(prompt, /禁止 agent 直写/)
  assert.match(prompt, /不要手填 accepted\/complete/)
})
