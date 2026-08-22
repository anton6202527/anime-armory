import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import test, { type TestContext } from 'node:test'
import {
  CANVAS_EPISODE_TASK_NODE_ID,
  acceptCanvasFinal,
  acceptCanvasNode,
  canvasProductionStatePath,
  computeCanvasContentHash,
  computeCanvasAcceptedInputsSha256,
  computeCanvasNodeFingerprints,
  computeCanvasStageFingerprints,
  computeCanvasTargetFingerprint,
  readCanvasProductionState,
  recordCanvasTaskSubmit,
  stableCanonicalJson,
  syncCanvasProductionState,
  updateCanvasTaskStatus,
} from '../src/main/services/canvasProduction.ts'
import type {
  CanvasAuthoringInput,
  CanvasClip,
  CanvasData,
  CanvasFinalArtifactEvidence,
  CanvasNodeAcceptanceEvidence,
} from '../src/shared/types.ts'
import { canvasFrameTargetSlot } from '../src/shared/canvasTargets.ts'

const EPISODE = '第1集'

async function temporaryProject(t: TestContext): Promise<string> {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'canvas-production-'))
  t.after(async () => {
    await fs.rm(root, { recursive: true, force: true })
  })
  return root
}

function authoring(promptA = 'A prompt', promptB = 'B prompt'): CanvasAuthoringInput {
  return {
    authority: 'storyboard_v2',
    source_rel: `生产数据/分镜/${EPISODE}.json`,
    source_sha256: 'e'.repeat(64),
    settings_sha256: 'f'.repeat(64),
    episode: EPISODE,
    final_stage: 'video',
    clips: [
      {
        id: 'A',
        editable: { prompt: promptA, duration: 4, camera: { move: 'push', speed: 1 } },
        final_target: { slot: 'video', output_path: 'out/A.mp4' },
        asset_ids: ['hero'],
        generation_config_keys: ['video:A'],
      },
      {
        id: 'B',
        editable: { prompt: promptB, duration: 6, camera: { move: 'pan', speed: 2 } },
        final_target: { slot: 'video', output_path: 'out/B.mp4' },
        asset_ids: ['location'],
        generation_config_keys: ['video:B'],
      },
    ],
    assets: [
      { id: 'hero', role: 'character', content_digest: 'sha256:hero-v1', summary: { costume: 'red' } },
      { id: 'location', role: 'location', content_digest: 'sha256:location-v1' },
    ],
    delivery_spec: { resolution: '3840x2160', fps: 24, container: 'mp4' },
    generation_configs: {
      'video:A': { model: 'model-a', seed: 101 },
      'video:B': { model: 'model-b', seed: 202 },
    },
  }
}

function canvasClip(id: string, revision?: string, qaBlocks = 0): CanvasClip {
  const hasMedia = revision !== undefined
  return {
    id,
    number: id === 'A' ? 1 : 2,
    label: `镜头 ${id}`,
    first_frame_abs: hasMedia ? `/evidence/${id}.png` : undefined,
    first_frame_exists: hasMedia,
    video_exists: false,
    frames: hasMedia
      ? [{ role: 'first', label: `${id} first`, abs: `/evidence/${id}.png`, exists: true, revision }]
      : [],
    qa: qaBlocks > 0 ? [{ severity: 'block', dimension: 'identity' }] : [],
    qa_blocks: qaBlocks,
    qa_warnings: 0,
    qa_infos: 0,
  }
}

function canvas(revisions: { A?: string; B?: string }, blocks: { A?: number; B?: number } = {}): CanvasData {
  return {
    source: 'storyboard',
    episode: EPISODE,
    final_stage: 'video',
    episodes: [EPISODE],
    clips: [
      canvasClip('A', revisions.A, blocks.A || 0),
      canvasClip('B', revisions.B, blocks.B || 0),
    ],
    seams: [{ from: 'A', to: 'B' }],
  }
}

function acceptance(contentHash: string, inputHash: string, id: string): CanvasNodeAcceptanceEvidence {
  return {
    content_hash: contentHash,
    input_hash: inputHash,
    output_path: `/evidence/${id}.mp4`,
    output_sha256: id === 'A' ? '1'.repeat(64) : '2'.repeat(64),
    qa_receipt_path: `/evidence/${id}.qc.json`,
    qa_receipt_sha256: id === 'A' ? '3'.repeat(64) : '4'.repeat(64),
    qa_blocks: 0,
    reviewer_kind: 'delegated',
    verdict: 'accepted',
    job_id: `job-${id}`,
    accepted_at: '2026-08-21T00:00:00.000Z',
  }
}

function acceptanceMap(input: CanvasAuthoringInput): Record<string, CanvasNodeAcceptanceEvidence> {
  const contentHash = computeCanvasContentHash(input)
  const fingerprints = computeCanvasNodeFingerprints(input)
  return {
    A: acceptance(contentHash, fingerprints.A, 'A'),
    B: acceptance(contentHash, fingerprints.B, 'B'),
  }
}

function finalArtifact(input: CanvasAuthoringInput, qaBlocks = 0): CanvasFinalArtifactEvidence {
  const contentHash = computeCanvasContentHash(input)
  const acceptances = acceptanceMap(input)
  return {
    path: '/evidence/final.mp4',
    exists: true,
    sha256: 'a'.repeat(64),
    content_hash: contentHash,
    inputs_sha256: computeCanvasAcceptedInputsSha256(input, acceptances) || '',
    qa_blocks: qaBlocks,
    qa_receipt_path: '/evidence/final.qc.json',
    qa_receipt_sha256: 'b'.repeat(64),
    probe_passed: true,
    revision: 'final-v1',
  }
}

test('canonical episode hash ignores object/asset order but preserves clip order', () => {
  const first = authoring()
  const reordered: CanvasAuthoringInput = {
    generation_configs: {
      'video:B': { seed: 202, model: 'model-b' },
      'video:A': { seed: 101, model: 'model-a' },
    },
    delivery_spec: { container: 'mp4', fps: 24, resolution: '3840x2160' },
    assets: [
      { id: 'location', content_digest: 'sha256:location-v1', role: 'location' },
      { summary: { costume: 'red' }, content_digest: 'sha256:hero-v1', role: 'character', id: 'hero' },
    ],
    clips: [
      {
        generation_config_keys: ['video:A'],
        asset_ids: ['hero'],
        editable: { camera: { speed: 1, move: 'push' }, duration: 4, prompt: 'A prompt' },
        final_target: { output_path: 'out/A.mp4', slot: 'video' },
        id: 'A',
      },
      {
        editable: { camera: { speed: 2, move: 'pan' }, prompt: 'B prompt', duration: 6 },
        final_target: { slot: 'video', output_path: 'out/B.mp4' },
        id: 'B',
        generation_config_keys: ['video:B'],
        asset_ids: ['location'],
      },
    ],
    episode: EPISODE,
    source_rel: `生产数据/分镜/${EPISODE}.json`,
    source_sha256: 'e'.repeat(64),
    settings_sha256: 'f'.repeat(64),
    authority: 'storyboard_v2',
  }

  const firstHash = computeCanvasContentHash(first)
  assert.match(firstHash, /^[a-f0-9]{64}$/)
  assert.equal(firstHash, computeCanvasContentHash(reordered))
  assert.notEqual(firstHash, computeCanvasContentHash({ ...first, clips: [...first.clips].reverse() }))
  const retargeted = structuredClone(first)
  retargeted.clips[0].final_target.output_path = 'out/A_v2.mp4'
  assert.notEqual(firstHash, computeCanvasContentHash(retargeted))
  assert.equal(stableCanonicalJson({ z: 1, a: { y: 2, x: 3 } }), '{"a":{"x":3,"y":2},"z":1}')
})

test('sync invalidates one edited node and never revives its old accepted media', async (t) => {
  const root = await temporaryProject(t)
  const original = authoring()
  const originalAcceptances = acceptanceMap(original)
  const mediaV1 = canvas({ A: 'A-v1', B: 'B-v1' })
  const accepted = await syncCanvasProductionState(root, {
    authoring: original,
    canvas: mediaV1,
    final_artifact: null,
    accepted_nodes: originalAcceptances,
  })
  const oldFingerprints = computeCanvasNodeFingerprints(original)
  assert.equal(accepted.node_fingerprints.A.lifecycle, 'accepted')
  assert.equal(accepted.node_fingerprints.B.lifecycle, 'accepted')

  const edited = authoring('A prompt edited')
  const invalidated = await syncCanvasProductionState(root, {
    authoring: edited,
    canvas: mediaV1,
    final_artifact: null,
    accepted_nodes: { B: originalAcceptances.B },
  })
  assert.equal(invalidated.node_fingerprints.A.lifecycle, 'ready')
  assert.equal(invalidated.node_fingerprints.A.invalidation_reason, 'authoring_input_changed')
  assert.equal(invalidated.node_fingerprints.B.lifecycle, 'accepted')
  assert.notEqual(invalidated.node_fingerprints.A.input_hash, oldFingerprints.A)
  assert.equal(invalidated.node_fingerprints.B.input_hash, oldFingerprints.B)
  assert.deepEqual(invalidated.history.at(-1)?.invalidated_node_ids, ['A'])

  const repeated = await syncCanvasProductionState(root, {
    authoring: edited,
    canvas: mediaV1,
    final_artifact: null,
    accepted_nodes: { B: originalAcceptances.B },
  })
  assert.equal(repeated.revision, invalidated.revision)
  assert.equal(repeated.node_fingerprints.A.lifecycle, 'ready')

  const regenerated = await syncCanvasProductionState(root, {
    authoring: edited,
    canvas: canvas({ A: 'A-v2', B: 'B-v1' }),
    final_artifact: null,
    accepted_nodes: { B: originalAcceptances.B },
  })
  assert.equal(regenerated.node_fingerprints.A.lifecycle, 'generated')
  assert.equal(regenerated.node_fingerprints.B.lifecycle, 'accepted')
})

test('node fingerprints invalidate selectively while every active task binds the root content hash', async (t) => {
  const root = await temporaryProject(t)
  const initial = await syncCanvasProductionState(root, {
    authoring: authoring(),
    canvas: canvas({}),
    final_artifact: null,
  })
  const submittedA = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'A',
    kind: 'video',
    expected_content_hash: initial.content_hash,
  })
  const submittedB = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'B',
    kind: 'video',
    expected_content_hash: initial.content_hash,
  })
  const submittedEpisode = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: CANVAS_EPISODE_TASK_NODE_ID,
    kind: 'one_click_production',
    expected_content_hash: initial.content_hash,
  })
  assert.equal(submittedA.input_hash, initial.node_fingerprints.A.input_hash)
  assert.equal(submittedEpisode.input_hash, initial.content_hash)
  assert.equal(submittedEpisode.state.status, 'running')
  assert.equal(submittedEpisode.state.node_fingerprints.A.lifecycle, 'ready')

  const changed = await syncCanvasProductionState(root, {
    authoring: authoring('A prompt edited'),
    canvas: canvas({}),
    final_artifact: null,
  })
  const tasks = new Map(changed.tasks.map((task) => [task.job_id, task]))
  assert.equal(tasks.get(submittedA.job_id)?.status, 'stale')
  assert.equal(tasks.get(submittedB.job_id)?.status, 'stale')
  assert.equal(tasks.get(submittedEpisode.job_id)?.status, 'stale')
  assert.equal(changed.node_fingerprints.B.input_hash, initial.node_fingerprints.B.input_hash)
  assert.equal(changed.status, 'ready')
})

test('a new root content hash never reuses an active task even when its node hash is unchanged', async (t) => {
  const root = await temporaryProject(t)
  const original = authoring()
  const initial = await syncCanvasProductionState(root, {
    authoring: original,
    canvas: canvas({}),
    final_artifact: null,
  })
  const first = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'A',
    kind: 'video',
    expected_content_hash: initial.content_hash,
  })

  const refreshedSource = { ...original, source_sha256: 'd'.repeat(64) }
  const refreshed = await syncCanvasProductionState(root, {
    authoring: refreshedSource,
    canvas: canvas({}),
    final_artifact: null,
  })
  assert.notEqual(refreshed.content_hash, initial.content_hash)
  assert.equal(refreshed.node_fingerprints.A.input_hash, initial.node_fingerprints.A.input_hash)
  assert.equal(refreshed.tasks.find((task) => task.job_id === first.job_id)?.status, 'stale')

  const replacement = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'A',
    kind: 'video',
    expected_content_hash: refreshed.content_hash,
  })
  assert.equal(replacement.created, true)
  assert.notEqual(replacement.job_id, first.job_id)
  assert.equal(replacement.content_hash, refreshed.content_hash)
})

test('image target slots have independent identities and never reuse another active frame job', async (t) => {
  const root = await temporaryProject(t)
  const input: CanvasAuthoringInput = {
    ...authoring(),
    generation_configs: {
      ...authoring().generation_configs,
      'image:A:first': { model: 'img', target_slot: 'first', target_output_path: 'out/A_first.png' },
      'image:A:end': { model: 'img', target_slot: 'end', target_output_path: 'out/A_end.png' },
    },
    clips: authoring().clips.map((clip) => clip.id === 'A'
      ? { ...clip, generation_config_keys: ['image:A:first', 'image:A:end', 'video:A'] }
      : clip),
  }
  const initial = await syncCanvasProductionState(root, {
    authoring: input,
    canvas: canvas({}),
    final_artifact: null,
  })
  const firstHash = computeCanvasTargetFingerprint(input, 'A', 'image', 'first', 'out/A_first.png')
  const endHash = computeCanvasTargetFingerprint(input, 'A', 'image', 'end', 'out/A_end.png')
  assert.notEqual(firstHash, endHash)
  const first = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'A',
    kind: 'image',
    target_slot: 'first',
    target_output_path: 'out/A_first.png',
    expected_content_hash: initial.content_hash,
  })
  const end = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'A',
    kind: 'image',
    target_slot: 'end',
    target_output_path: 'out/A_end.png',
    expected_content_hash: initial.content_hash,
  })
  const duplicateFirst = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'A',
    kind: 'image',
    target_slot: 'first',
    target_output_path: 'out/A_first.png',
    expected_content_hash: initial.content_hash,
  })
  assert.notEqual(first.job_id, end.job_id)
  assert.notEqual(first.input_hash, end.input_hash)
  assert.equal(duplicateFirst.job_id, first.job_id)
  assert.equal(duplicateFirst.created, false)
})

test('anchor slots remain distinct for Chinese basenames without timing metadata', () => {
  const first = canvasFrameTargetSlot({
    role: 'anchor', label: '中帧', abs: '/tmp/中帧一.png', exists: false,
  }, 1)
  const second = canvasFrameTargetSlot({
    role: 'anchor', label: '中帧', abs: '/tmp/中帧二.png', exists: false,
  }, 2)
  assert.notEqual(first, second)
  assert.match(first, /中帧一/)
  assert.match(second, /中帧二/)
})

test('image stage excludes its own selected output while video/final stage consumes it', () => {
  const before = authoring()
  before.clips[0].image_runtime_inputs = [{ role: 'character', sha256: 'char-v1' }]
  before.clips[0].runtime_inputs = [{ role: 'first', sha256: 'frame-v1' }]
  const after = structuredClone(before)
  after.clips[0].runtime_inputs = [{ role: 'first', sha256: 'frame-v2' }]

  const beforeStages = computeCanvasStageFingerprints(before)
  const afterStages = computeCanvasStageFingerprints(after)
  assert.equal(beforeStages.A.image, afterStages.A.image)
  assert.notEqual(beforeStages.A.video, afterStages.A.video)
  assert.equal(computeCanvasNodeFingerprints(before).A, beforeStages.A.video)

  const comic = { ...before, final_stage: 'image' as const }
  assert.equal(computeCanvasNodeFingerprints(comic).A, computeCanvasStageFingerprints(comic).A.image)
})

test('identical active jobs are reused once and terminal image success survives downstream invalidation', async (t) => {
  const root = await temporaryProject(t)
  const input = authoring()
  input.clips[0].image_runtime_inputs = [{ role: 'character', sha256: 'char-v1' }]
  input.clips[0].runtime_inputs = [{ role: 'first', sha256: 'frame-v1' }]
  const initial = await syncCanvasProductionState(root, {
    authoring: input,
    canvas: canvas({}),
    final_artifact: null,
  })
  const manifest = path.join(root, '生产数据', `canvas_inputs_manifest_${EPISODE}.json`)
  await fs.writeFile(manifest, JSON.stringify({ content_hash: initial.content_hash, inputs_sha256: 'old' }))
  const first = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'A',
    kind: 'image',
    expected_content_hash: initial.content_hash,
  })
  await assert.rejects(fs.access(manifest), /ENOENT/)
  const reused = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'A',
    kind: 'image',
    expected_content_hash: initial.content_hash,
  })
  assert.equal(first.created, true)
  assert.equal(reused.created, false)
  assert.equal(reused.task_status, 'submitted')
  assert.equal(reused.job_id, first.job_id)
  await updateCanvasTaskStatus(root, {
    episode: EPISODE,
    job_id: first.job_id,
    status: 'running',
    detail: 'dispatch acknowledged',
  })
  const reusedRunning = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'A',
    kind: 'image',
    expected_content_hash: initial.content_hash,
  })
  assert.equal(reusedRunning.created, false)
  assert.equal(reusedRunning.task_status, 'running')
  await updateCanvasTaskStatus(root, {
    episode: EPISODE,
    job_id: first.job_id,
    status: 'succeeded',
    detail: 'verified receipt 已验收',
  })
  const lateRunningAck = await updateCanvasTaskStatus(root, {
    episode: EPISODE,
    job_id: first.job_id,
    status: 'running',
    detail: 'late renderer dispatch acknowledgement',
  })
  assert.equal(lateRunningAck.tasks.find((task) => task.job_id === first.job_id)?.status, 'succeeded')

  const downstreamChanged = structuredClone(input)
  downstreamChanged.clips[0].runtime_inputs = [{ role: 'first', sha256: 'frame-v2' }]
  const synced = await syncCanvasProductionState(root, {
    authoring: downstreamChanged,
    canvas: canvas({}),
    final_artifact: null,
  })
  assert.equal(synced.tasks.find((task) => task.job_id === first.job_id)?.status, 'succeeded')
})

test('final acceptance enforces the current hash, node acceptance, artifact hash, and QA', async (t) => {
  const root = await temporaryProject(t)
  const input = authoring()
  let state = await syncCanvasProductionState(root, {
    authoring: input,
    canvas: canvas({ A: 'A-v1', B: 'B-v1' }),
    final_artifact: null,
  })
  await assert.rejects(
    acceptCanvasFinal(root, {
      episode: EPISODE,
      expected_content_hash: state.content_hash,
      artifact: finalArtifact(input),
    }),
    /node_not_accepted/,
  )

  state = await acceptCanvasNode(root, {
    episode: EPISODE,
    node_id: 'A',
    expected_content_hash: state.content_hash,
    expected_input_hash: state.node_fingerprints.A.input_hash,
    evidence: acceptance(state.content_hash, state.node_fingerprints.A.input_hash, 'A'),
  })
  state = await acceptCanvasNode(root, {
    episode: EPISODE,
    node_id: 'B',
    expected_content_hash: state.content_hash,
    expected_input_hash: state.node_fingerprints.B.input_hash,
    evidence: acceptance(state.content_hash, state.node_fingerprints.B.input_hash, 'B'),
  })

  await assert.rejects(
    acceptCanvasFinal(root, {
      episode: EPISODE,
      expected_content_hash: '0'.repeat(64),
      artifact: finalArtifact(input),
    }),
    /content_hash 已变化/,
  )
  await assert.rejects(
    acceptCanvasFinal(root, {
      episode: EPISODE,
      expected_content_hash: state.content_hash,
      artifact: finalArtifact(input, 1),
    }),
    /final_artifact_qa_block/,
  )
  await assert.rejects(
    acceptCanvasFinal(root, {
      episode: EPISODE,
      expected_content_hash: state.content_hash,
      artifact: { ...finalArtifact(input), sha256: 'not-a-sha' },
    }),
    /final_artifact_sha256_invalid/,
  )
  await assert.rejects(
    acceptCanvasFinal(root, {
      episode: EPISODE,
      expected_content_hash: state.content_hash,
      artifact: { ...finalArtifact(input), qa_receipt_path: '', qa_receipt_sha256: '', probe_passed: false },
    }),
    /final_artifact_qa_receipt_missing|final_artifact_probe_failed/,
  )

  const artifact = finalArtifact(input)
  state = await acceptCanvasFinal(root, {
    episode: EPISODE,
    expected_content_hash: state.content_hash,
    artifact,
  })
  assert.equal(state.status, 'complete')
  assert.equal(state.completion.complete, true)
  assert.deepEqual(state.completion.blockers, [])

  const invalidated = await syncCanvasProductionState(root, {
    authoring: authoring('A prompt edited'),
    canvas: canvas({ A: 'A-v1', B: 'B-v1' }),
    final_artifact: artifact,
  })
  assert.equal(invalidated.completion.complete, false)
  assert.equal(invalidated.status, 'needs_revision')
  assert.ok(invalidated.completion.blockers.includes('final_artifact_content_hash_stale'))
})

test('atomic serial writes preserve concurrent jobs and restart reads valid JSON', async (t) => {
  const root = await temporaryProject(t)
  const initial = await syncCanvasProductionState(root, {
    authoring: authoring(),
    canvas: canvas({}),
    final_artifact: null,
  })
  const count = 24
  const results = await Promise.all(Array.from({ length: count }, (_, index) => {
    return recordCanvasTaskSubmit(root, {
      episode: EPISODE,
      node_id: index % 3 === 0 ? CANVAS_EPISODE_TASK_NODE_ID : (index % 2 === 0 ? 'A' : 'B'),
      kind: `generation-${index}`,
      expected_content_hash: initial.content_hash,
      detail: `job-${index}`,
    })
  }))

  assert.equal(new Set(results.map((result) => result.job_id)).size, count)
  const restarted = await readCanvasProductionState(root, EPISODE)
  assert.ok(restarted)
  assert.equal(restarted.tasks.length, count)
  assert.equal(restarted.revision, initial.revision + count)
  assert.equal(restarted.history.length, restarted.revision)

  const file = canvasProductionStatePath(root, EPISODE)
  const diskValue = JSON.parse(await fs.readFile(file, 'utf8')) as { revision: number; tasks: unknown[] }
  assert.equal(diskValue.revision, restarted.revision)
  assert.equal(diskValue.tasks.length, count)
  const leftovers = (await fs.readdir(path.dirname(file))).filter((name) => name.includes('.tmp'))
  assert.deepEqual(leftovers, [])
})
