import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import test, { type TestContext } from 'node:test'
import { deflateSync } from 'node:zlib'
import {
  readCanvasProductionState,
  recordCanvasTaskSubmit,
  updateCanvasTaskStatus,
} from '../src/main/services/canvasProduction.ts'
import {
  acceptCanvasFinalProduct,
  buildCanvasAuthoringInput,
  probeCanvasProductionMedia,
  synchronizeCanvasProduction,
  verifiedNodeAcceptances,
  verifyCanvasQcReceipt,
} from '../src/main/services/canvasProductionAdapter.ts'
import { markCanvasProductionTaskRunning, readCanvas } from '../src/main/services/canvas.ts'
import { canvasCandidateTargetRel } from '../src/shared/canvasTargets.ts'
import type { CanvasData } from '../src/shared/types.ts'

const EPISODE = '第1话'
const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
  'base64',
)

function crc32(bytes: Buffer): number {
  let crc = 0xffffffff
  for (const byte of bytes) {
    crc ^= byte
    for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1))
  }
  return (crc ^ 0xffffffff) >>> 0
}

function pngChunk(kind: string, data: Buffer): Buffer {
  const type = Buffer.from(kind, 'ascii')
  const length = Buffer.alloc(4)
  length.writeUInt32BE(data.length)
  const checksum = Buffer.alloc(4)
  checksum.writeUInt32BE(crc32(Buffer.concat([type, data])))
  return Buffer.concat([length, type, data, checksum])
}

function solidPng(width: number, height: number): Buffer {
  const ihdr = Buffer.alloc(13)
  ihdr.writeUInt32BE(width, 0)
  ihdr.writeUInt32BE(height, 4)
  ihdr[8] = 8
  ihdr[9] = 2
  const row = Buffer.alloc(1 + width * 3, 0x7f)
  row[0] = 0
  return Buffer.concat([
    Buffer.from('89504e470d0a1a0a', 'hex'),
    pngChunk('IHDR', ihdr),
    pngChunk('IDAT', deflateSync(Buffer.concat(Array.from({ length: height }, () => row)))),
    pngChunk('IEND', Buffer.alloc(0)),
  ])
}

const FINAL_PNG = solidPng(256, 256)

function sha256(value: Buffer | string): string {
  return createHash('sha256').update(value).digest('hex')
}

async function project(t: TestContext): Promise<string> {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'canvas-adapter-'))
  t.after(() => fs.rm(root, { recursive: true, force: true }))
  await fs.mkdir(path.join(root, '脚本', EPISODE), { recursive: true })
  await fs.writeFile(path.join(root, '脚本', EPISODE, 'panel_script.json'), `${JSON.stringify({
    kind: 'comic_panel_script',
    version: 2,
    title: '测试',
    panels: [{ panel_id: 'P001', story_function: 'opening', description: '一格完整画面' }],
  }, null, 2)}\n`)
  return root
}

function canvas(root: string, output?: string, revision?: string): CanvasData {
  return {
    source: 'panel_script',
    episode: EPISODE,
    episodes: [EPISODE],
    clips: [{
      id: 'P001',
      number: 1,
      label: 'opening',
      first_frame_abs: output,
      first_frame_exists: Boolean(output),
      video_exists: false,
      frames: output ? [{ role: 'panel', label: '成图', abs: output, exists: true, revision }] : [],
      prompt: '一格完整画面',
      qa: [],
      qa_blocks: 0,
      qa_warnings: 0,
      qa_infos: 0,
    }],
    seams: [],
  }
}

async function videoProject(t: TestContext): Promise<string> {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'canvas-video-adapter-'))
  t.after(() => fs.rm(root, { recursive: true, force: true }))
  await fs.mkdir(path.join(root, '脚本', EPISODE), { recursive: true })
  await fs.writeFile(path.join(root, '脚本', EPISODE, 'storyboard.json'), `${JSON.stringify({
    kind: 'n2d_storyboard',
    version: 1,
    total_duration: 10,
    clips: [{ id: 'CLIP01', label: '完整镜头', duration: 10, prompt: '动作与运镜' }],
  }, null, 2)}\n`)
  return root
}

function videoCanvas(root: string, output?: string): CanvasData {
  return {
    source: 'storyboard',
    episode: EPISODE,
    episodes: [EPISODE],
    total_duration: 10,
    generation_profile: {
      default_aspect_ratio: '16:9',
      default_resolution: '1920x1080',
      default_video_duration: 10,
      audio_policy: 'required',
      image_models: [],
      video_models: [],
    },
    clips: [{
      id: 'CLIP01',
      number: 1,
      label: '完整镜头',
      duration: 10,
      first_frame_exists: false,
      video_abs: output,
      video_exists: Boolean(output),
      frames: [],
      prompt: '动作与运镜',
      qa: [],
      qa_blocks: 0,
      qa_warnings: 0,
      qa_infos: 0,
    }],
    seams: [],
  }
}

async function writeNodeEvidence(
  root: string,
  jobId: string,
  contentHash: string,
  inputHash: string,
  outputRel: string,
  taskInputHash = contentHash,
  direct = true,
  nodeId = 'P001',
  targetSlot = 'panel',
): Promise<void> {
  const output = path.join(root, outputRel)
  const outputSha = sha256(await fs.readFile(output))
  const safeNode = nodeId.replace(/[^\p{L}\p{N}_.-]+/gu, '_')
  const qaRel = `生产数据/node_qc_${jobId}_${safeNode}.json`
  const qa = {
    kind: 'anime_armory_canvas_node_qc',
    version: 1,
    episode: EPISODE,
    job_id: jobId,
    node_id: nodeId,
    target_slot: targetSlot,
    target_output_path: outputRel,
    content_hash: contentHash,
    input_hash: inputHash,
    task_input_hash: taskInputHash,
    output_path: outputRel,
    output_sha256: outputSha,
    qa_blocks: 0,
    verdict: 'pass',
    probe_passed: true,
  }
  await fs.mkdir(path.join(root, '生产数据'), { recursive: true })
  await fs.writeFile(path.join(root, qaRel), `${JSON.stringify(qa, null, 2)}\n`)
  const qaSha = sha256(await fs.readFile(path.join(root, qaRel)))
  const receipt = {
    node_id: nodeId,
    target_slot: targetSlot,
    target_output_path: outputRel,
    content_hash: contentHash,
    input_hash: inputHash,
    task_input_hash: taskInputHash,
    output_path: outputRel,
    output_sha256: outputSha,
    qa_receipt_path: qaRel,
    qa_receipt_sha256: qaSha,
    qa_blocks: 0,
    reviewer_kind: 'delegated',
    verdict: 'accepted',
    job_id: jobId,
    accepted_at: '2026-08-21T00:00:00.000Z',
    probe_passed: true,
  }
  const payload = direct
    ? { kind: 'anime_armory_canvas_node_receipt', version: 1, episode: EPISODE, ...receipt }
    : {
        kind: 'anime_armory_canvas_node_receipts',
        version: 1,
        episode: EPISODE,
        nodes: { [nodeId]: receipt },
      }
  const filename = direct
    ? `canvas_node_receipt_${jobId}_${safeNode}.json`
    : `canvas_node_receipts_${EPISODE}.json`
  await fs.writeFile(path.join(root, '生产数据', filename), `${JSON.stringify(payload, null, 2)}\n`)
}

async function writeFinalEvidence(
  root: string,
  jobId: string,
  contentHash: string,
  inputsSha256: string,
  finalRel: string,
): Promise<void> {
  const artifactSha = sha256(await fs.readFile(path.join(root, finalRel)))
  const finalQaRel = `生产数据/final_qc_${jobId}.json`
  const finalQa = {
    kind: 'anime_armory_canvas_final_qc',
    version: 1,
    episode: EPISODE,
    job_id: jobId,
    content_hash: contentHash,
    inputs_sha256: inputsSha256,
    artifact_path: finalRel,
    artifact_sha256: artifactSha,
    qa_blocks: 0,
    verdict: 'pass',
    probe_passed: true,
  }
  await fs.writeFile(path.join(root, finalQaRel), `${JSON.stringify(finalQa, null, 2)}\n`)
  const finalQaSha = sha256(await fs.readFile(path.join(root, finalQaRel)))
  await fs.writeFile(path.join(root, '生产数据', `canvas_compose_receipt_${jobId}.json`), `${JSON.stringify({
    kind: 'anime_armory_canvas_compose_receipt',
    version: 1,
    episode: EPISODE,
    job_id: jobId,
    content_hash: contentHash,
    inputs_sha256: inputsSha256,
    artifact_path: finalRel,
    artifact_sha256: artifactSha,
    qa_receipt_path: finalQaRel,
    qa_receipt_sha256: finalQaSha,
    qa_blocks: 0,
    verdict: 'pass',
    probe_passed: true,
  }, null, 2)}\n`)
}

async function writeCandidateEvidence(root: string, options: {
  scope: 'task' | 'node' | 'final'
  jobId: string
  contentHash: string
  targetPath: string
  candidatePath: string
  nodeId?: string
  generationKind?: 'image' | 'video'
  targetSlot?: string
  inputHash?: string
  nodeInputHash?: string
  taskInputHash?: string
  inputsSha256?: string
  humanAccepted?: boolean
}): Promise<void> {
  const bytes = await fs.readFile(path.join(root, options.candidatePath))
  const candidateSha = sha256(bytes)
  const safe = options.nodeId?.replace(/[^\p{L}\p{N}_.-]+/gu, '_') || ''
  const suffix = safe ? `_${safe}` : ''
  const qcRel = `生产数据/canvas_${options.scope}_candidate_qc_${options.jobId}${suffix}.json`
  const common = {
    version: 1,
    episode: EPISODE,
    job_id: options.jobId,
    node_id: options.nodeId,
    generation_kind: options.generationKind,
    target_slot: options.targetSlot,
    target_output_path: options.targetPath,
    candidate_output_path: options.candidatePath,
    content_hash: options.contentHash,
    input_hash: options.inputHash,
    node_input_hash: options.nodeInputHash,
    task_input_hash: options.taskInputHash,
    inputs_sha256: options.inputsSha256,
    candidate_sha256: candidateSha,
    qa_blocks: 0,
    verdict: 'pass',
    probe_passed: true,
  }
  const qcKind = options.scope === 'final'
    ? 'anime_armory_canvas_final_candidate_qc'
    : options.scope === 'node'
      ? 'anime_armory_canvas_node_candidate_qc'
      : 'anime_armory_canvas_task_candidate_qc'
  await fs.mkdir(path.join(root, '生产数据'), { recursive: true })
  await fs.writeFile(path.join(root, qcRel), `${JSON.stringify({ kind: qcKind, ...common }, null, 2)}\n`)
  let humanAcceptancePath: string | undefined
  let humanAcceptanceSha256: string | undefined
  if (options.humanAccepted) {
    humanAcceptancePath = `生产数据/canvas_candidate_human_acceptance_${options.jobId}${suffix}.json`
    await fs.writeFile(path.join(root, humanAcceptancePath), `${JSON.stringify({
      kind: 'anime_armory_canvas_candidate_human_acceptance',
      ...common,
      reviewer: 'Wesley',
      accepted_at: '2026-08-21T08:00:00+08:00',
      confirmation: {
        kind: 'explicit_current_pixels_acceptance',
        accepted_current_pixels: true,
      },
    }, null, 2)}\n`)
    humanAcceptanceSha256 = sha256(await fs.readFile(path.join(root, humanAcceptancePath)))
  }
  const receiptKind = options.scope === 'final'
    ? 'anime_armory_canvas_final_candidate_receipt'
    : options.scope === 'node'
      ? 'anime_armory_canvas_node_candidate_receipt'
      : 'anime_armory_canvas_task_candidate_receipt'
  const receiptName = `canvas_${options.scope}_candidate_receipt_${options.jobId}${suffix}.json`
  await fs.writeFile(path.join(root, '生产数据', receiptName), `${JSON.stringify({
    kind: receiptKind,
    ...common,
    reviewer_kind: options.scope === 'node' ? 'delegated' : undefined,
    accepted_at: '2026-08-21T00:00:00.000Z',
    qa_receipt_path: qcRel,
    qa_receipt_sha256: sha256(await fs.readFile(path.join(root, qcRel))),
    human_acceptance_path: humanAcceptancePath,
    human_acceptance_sha256: humanAcceptanceSha256,
  }, null, 2)}\n`)
}

async function writeLegacyDirectTaskEvidence(root: string, task: {
  job_id: string
  content_hash: string
  input_hash: string
}, outputRel: string): Promise<void> {
  const outputSha = sha256(await fs.readFile(path.join(root, outputRel)))
  const qaRel = `生产数据/legacy_task_qc_${task.job_id}.json`
  const common = {
    version: 1,
    episode: EPISODE,
    job_id: task.job_id,
    node_id: 'P001',
    generation_kind: 'image',
    target_slot: 'panel',
    target_output_path: outputRel,
    content_hash: task.content_hash,
    input_hash: task.input_hash,
    output_path: outputRel,
    output_sha256: outputSha,
    qa_blocks: 0,
    verdict: 'pass',
    probe_passed: true,
  }
  await fs.mkdir(path.join(root, '生产数据'), { recursive: true })
  await fs.writeFile(path.join(root, qaRel), `${JSON.stringify({ kind: 'anime_armory_canvas_task_qc', ...common }, null, 2)}\n`)
  await fs.writeFile(path.join(root, '生产数据', `canvas_task_receipt_${task.job_id}.json`), `${JSON.stringify({
    kind: 'anime_armory_canvas_task_receipt',
    ...common,
    qa_receipt_path: qaRel,
    qa_receipt_sha256: sha256(await fs.readFile(path.join(root, qaRel))),
  }, null, 2)}\n`)
}

test('adapter rejects fake media receipts and machine evidence still requires explicit final acceptance', async (t) => {
  const root = await project(t)
  let state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'test_initialize')
  assert.ok(state)
  const submitted = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: '__episode__',
    kind: 'production',
    expected_content_hash: state.content_hash,
  })
  const initialInputHash = state.node_fingerprints.P001.input_hash

  const outputRel = `出图/${EPISODE}/panels/P001.png`
  const output = path.join(root, outputRel)
  await fs.mkdir(path.dirname(output), { recursive: true })
  await fs.writeFile(output, 'not a real image')
  await writeNodeEvidence(
    root, submitted.job_id, state.content_hash, state.node_fingerprints.P001.input_hash, outputRel, submitted.input_hash,
  )
  state = await synchronizeCanvasProduction(root, 'comic', canvas(root, output, 'fake'), 'fake_receipt')
  assert.equal(state?.node_fingerprints.P001.lifecycle, 'generated')
  assert.equal(state?.node_fingerprints.P001.input_hash, initialInputHash)
  assert.equal(state?.tasks.find((task) => task.job_id === submitted.job_id)?.status, 'submitted')
  assert.equal(state?.completion.complete, false)

  await fs.writeFile(output, PNG)
  assert.equal(await probeCanvasProductionMedia(output), true)
  await writeNodeEvidence(
    root, submitted.job_id, state!.content_hash, state!.node_fingerprints.P001.input_hash, outputRel, submitted.input_hash,
  )
  const outputSha = sha256(PNG)
  const nodeQa = path.join(root, '生产数据', `node_qc_${submitted.job_id}_P001.json`)
  const verifiedQaSha = await verifyCanvasQcReceipt(root, nodeQa, {
    kind: 'node',
    episode: EPISODE,
    jobId: submitted.job_id,
    contentHash: state!.content_hash,
    inputHash: state!.node_fingerprints.P001.input_hash,
    taskInputHash: submitted.input_hash,
    nodeId: 'P001',
    targetSlot: 'panel',
    targetOutputPath: outputRel,
    artifactFile: output,
    artifactSha256: outputSha,
  })
  assert.equal(verifiedQaSha, sha256(await fs.readFile(nodeQa)), 'QA semantics and digest bind the same bytes')
  const currentCanvas = canvas(root, output, 'valid')
  const currentAuthoring = await buildCanvasAuthoringInput(root, 'comic', currentCanvas)
  const previous = await readCanvasProductionState(root, EPISODE)
  assert.ok(currentAuthoring && previous)
  const diagnostics: string[] = []
  assert.ok(
    (await verifiedNodeAcceptances(root, 'comic', currentCanvas, currentAuthoring, previous, diagnostics)).P001,
    diagnostics.join(', '),
  )
  state = await synchronizeCanvasProduction(root, 'comic', currentCanvas, 'valid_node_receipt')
  assert.equal(state?.node_fingerprints.P001.input_hash, initialInputHash)
  assert.equal(state?.node_fingerprints.P001.lifecycle, 'accepted')
  const manifest = JSON.parse(await fs.readFile(
    path.join(root, '生产数据', `canvas_inputs_manifest_${EPISODE}.json`),
    'utf8',
  )) as { inputs_sha256: string }

  const finalRel = `排版/${EPISODE}/长图/longstrip.png`
  const finalFile = path.join(root, finalRel)
  await fs.mkdir(path.dirname(finalFile), { recursive: true })
  await fs.writeFile(finalFile, PNG)
  await writeFinalEvidence(root, submitted.job_id, state!.content_hash, manifest.inputs_sha256, finalRel)

  state = await synchronizeCanvasProduction(root, 'comic', canvas(root, output, 'valid'), 'undersized_compose_receipt')
  assert.equal(state?.completion.complete, false, '1x1 final must never satisfy the delivery definition')

  await fs.writeFile(finalFile, FINAL_PNG)
  await writeFinalEvidence(root, submitted.job_id, state!.content_hash, manifest.inputs_sha256, finalRel)

  state = await synchronizeCanvasProduction(root, 'comic', canvas(root, output, 'valid'), 'compose_receipt')
  assert.equal(state?.completion.complete, false)
  assert.deepEqual(state?.completion.blockers, [])
  state = await acceptCanvasFinalProduct(root, 'comic', canvas(root, output, 'valid'), state!.content_hash)
  assert.equal(state.completion.complete, true)
  assert.equal(state?.status, 'complete')
  assert.equal(state?.tasks.find((task) => task.job_id === submitted.job_id)?.status, 'succeeded')
})

test('verified partial node output survives a later production executor failure', async (t) => {
  const root = await project(t)
  let state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'partial_initialize')
  assert.ok(state)
  const submitted = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: '__episode__',
    kind: 'production',
    expected_content_hash: state.content_hash,
  })
  const outputRel = `出图/${EPISODE}/panels/P001.png`
  const output = path.join(root, outputRel)
  await fs.mkdir(path.dirname(output), { recursive: true })
  await fs.writeFile(output, PNG)
  await writeNodeEvidence(
    root,
    submitted.job_id,
    state.content_hash,
    state.node_fingerprints.P001.input_hash,
    outputRel,
    submitted.input_hash,
  )

  state = await synchronizeCanvasProduction(root, 'comic', canvas(root, output, 'partial-v1'), 'partial_receipt')
  assert.equal(state?.node_fingerprints.P001.lifecycle, 'accepted')
  await updateCanvasTaskStatus(root, {
    episode: EPISODE,
    job_id: submitted.job_id,
    status: 'failed',
    detail: 'agent PTY ended (process_exit) without a verified final receipt',
  })

  state = await synchronizeCanvasProduction(root, 'comic', canvas(root, output, 'partial-v1'), 'resume_after_failure')
  assert.equal(state?.tasks.find((task) => task.job_id === submitted.job_id)?.status, 'failed')
  assert.equal(state?.node_fingerprints.P001.lifecycle, 'accepted')
  assert.equal(state?.node_fingerprints.P001.acceptance?.job_id, submitted.job_id)
})

test('a failed production task cannot introduce a node receipt for the first time', async (t) => {
  const root = await project(t)
  let state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'failed_first_initialize')
  assert.ok(state)
  const submitted = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: '__episode__',
    kind: 'production',
    expected_content_hash: state.content_hash,
  })
  const outputRel = `出图/${EPISODE}/panels/P001.png`
  const output = path.join(root, outputRel)
  await fs.mkdir(path.dirname(output), { recursive: true })
  await fs.writeFile(output, PNG)
  await writeNodeEvidence(
    root,
    submitted.job_id,
    state.content_hash,
    state.node_fingerprints.P001.input_hash,
    outputRel,
    submitted.input_hash,
  )
  await updateCanvasTaskStatus(root, {
    episode: EPISODE,
    job_id: submitted.job_id,
    status: 'failed',
    detail: 'agent PTY ended before receipt reconciliation',
  })

  state = await synchronizeCanvasProduction(root, 'comic', canvas(root, output, 'failed-first'), 'failed_first_receipt')
  assert.equal(state?.node_fingerprints.P001.lifecycle, 'generated')
  assert.equal(state?.node_fingerprints.P001.acceptance, undefined)
})

test('an individual comic panel job binds target hash and final node hash independently', async (t) => {
  const root = await project(t)
  let state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'target_job_initialize')
  assert.ok(state)
  const outputRel = `出图/${EPISODE}/panels/P001.png`
  const submitted = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'P001',
    kind: 'image',
    target_slot: 'panel',
    target_output_path: outputRel,
    expected_content_hash: state.content_hash,
  })
  assert.equal(submitted.target_slot, 'panel')
  assert.equal(submitted.target_output_path, outputRel)
  assert.ok(submitted.node_input_hash)
  assert.notEqual(submitted.input_hash, submitted.node_input_hash)

  const output = path.join(root, outputRel)
  await fs.mkdir(path.dirname(output), { recursive: true })
  await fs.writeFile(output, PNG)
  await writeNodeEvidence(
    root,
    submitted.job_id,
    submitted.content_hash,
    submitted.node_input_hash!,
    outputRel,
    submitted.input_hash,
  )
  state = await synchronizeCanvasProduction(root, 'comic', canvas(root, output, 'panel-v1'), 'target_job_receipt')
  assert.equal(state?.node_fingerprints.P001.lifecycle, 'accepted')
  assert.equal(state?.tasks.find((task) => task.job_id === submitted.job_id)?.status, 'succeeded')
})

test('immutable per-job task receipts settle without a shared aggregate RMW', async (t) => {
  const root = await project(t)
  let state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'task_receipt_initialize')
  assert.ok(state)
  const outputRel = `出图/${EPISODE}/panels/P001.png`
  const task = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'P001',
    kind: 'image',
    target_slot: 'panel',
    target_output_path: outputRel,
    expected_content_hash: state.content_hash,
  })
  const output = path.join(root, outputRel)
  await fs.mkdir(path.dirname(output), { recursive: true })
  await fs.writeFile(output, PNG)
  const outputSha = sha256(PNG)
  const qaRel = `生产数据/task_qc_${task.job_id}.json`
  const qa = {
    kind: 'anime_armory_canvas_task_qc',
    version: 1,
    episode: EPISODE,
    job_id: task.job_id,
    node_id: 'P001',
    target_slot: 'panel',
    target_output_path: outputRel,
    content_hash: task.content_hash,
    input_hash: task.input_hash,
    output_path: outputRel,
    output_sha256: outputSha,
    qa_blocks: 0,
    verdict: 'pass',
    probe_passed: true,
  }
  await fs.mkdir(path.join(root, '生产数据'), { recursive: true })
  await fs.writeFile(path.join(root, qaRel), `${JSON.stringify(qa, null, 2)}\n`)
  const receipt = {
    kind: 'anime_armory_canvas_task_receipt',
    version: 1,
    episode: EPISODE,
    job_id: task.job_id,
    node_id: 'P001',
    generation_kind: 'image',
    target_slot: 'panel',
    target_output_path: outputRel,
    content_hash: task.content_hash,
    input_hash: task.input_hash,
    output_path: outputRel,
    output_sha256: outputSha,
    qa_receipt_path: qaRel,
    qa_receipt_sha256: sha256(await fs.readFile(path.join(root, qaRel))),
    qa_blocks: 0,
    verdict: 'pass',
    probe_passed: true,
  }
  await Promise.all([
    fs.writeFile(
      path.join(root, '生产数据', `canvas_task_receipt_${task.job_id}.json`),
      `${JSON.stringify(receipt, null, 2)}\n`,
    ),
    fs.writeFile(
      path.join(root, '生产数据', 'canvas_task_receipt_parallel-decoy.json'),
      `${JSON.stringify({ ...receipt, job_id: 'parallel-decoy', output_sha256: '0'.repeat(64) }, null, 2)}\n`,
    ),
  ])
  state = await synchronizeCanvasProduction(root, 'comic', canvas(root, output, 'task-output'), 'direct_task_receipt')
  assert.equal(state?.tasks.find((item) => item.job_id === task.job_id)?.status, 'succeeded')
})

test('promotion-required task rejects direct receipts and atomically promotes its current candidate', async (t) => {
  const root = await project(t)
  let state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'candidate_initialize')
  assert.ok(state)
  const targetPath = `出图/${EPISODE}/panels/P001.png`
  const task = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'P001',
    kind: 'image',
    target_slot: 'panel',
    target_output_path: targetPath,
    expected_content_hash: state.content_hash,
    promotion_required: true,
  })
  assert.equal(task.candidate_output_path, canvasCandidateTargetRel(targetPath, task.job_id))

  const stable = path.join(root, targetPath)
  await fs.mkdir(path.dirname(stable), { recursive: true })
  await fs.writeFile(stable, PNG)
  await writeLegacyDirectTaskEvidence(root, task, targetPath)
  await writeNodeEvidence(root, task.job_id, task.content_hash, task.node_input_hash!, targetPath, task.input_hash)
  state = await synchronizeCanvasProduction(root, 'comic', canvas(root, stable, 'legacy-direct'), 'direct_forbidden')
  assert.equal(state?.tasks.find((item) => item.job_id === task.job_id)?.status, 'submitted')
  assert.equal(state?.node_fingerprints.P001.lifecycle, 'generated')

  const candidatePath = task.candidate_output_path!
  const candidate = path.join(root, candidatePath)
  await fs.mkdir(path.dirname(candidate), { recursive: true })
  await fs.writeFile(candidate, FINAL_PNG)
  await writeCandidateEvidence(root, {
    scope: 'task',
    jobId: task.job_id,
    contentHash: task.content_hash,
    targetPath,
    candidatePath,
    nodeId: 'P001',
    generationKind: 'image',
    targetSlot: 'panel',
    inputHash: task.input_hash,
    nodeInputHash: task.node_input_hash,
  })
  state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'delegated_candidate_cannot_accept')
  assert.deepEqual(await fs.readFile(stable), PNG)
  await fs.access(candidate)
  assert.equal(state?.tasks.find((item) => item.job_id === task.job_id)?.status, 'submitted')
  assert.equal(state?.node_fingerprints.P001.lifecycle, 'generated')

  await writeCandidateEvidence(root, {
    scope: 'task',
    jobId: task.job_id,
    contentHash: task.content_hash,
    targetPath,
    candidatePath,
    nodeId: 'P001',
    generationKind: 'image',
    targetSlot: 'panel',
    inputHash: task.input_hash,
    nodeInputHash: task.node_input_hash,
    humanAccepted: true,
  })
  state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'human_candidate_promote')
  assert.deepEqual(await fs.readFile(stable), FINAL_PNG)
  await assert.rejects(fs.access(candidate))
  assert.equal(state?.tasks.find((item) => item.job_id === task.job_id)?.status, 'succeeded')
  assert.equal(state?.node_fingerprints.P001.lifecycle, 'accepted')
  const authoritative = JSON.parse(await fs.readFile(
    path.join(root, '生产数据', `canvas_task_receipt_${task.job_id}.json`),
    'utf8',
  )) as Record<string, unknown>
  assert.equal(authoritative.promotion_authority, 'desktop_main_v1')
})

test('stale late candidate cannot overwrite the current promoted stable target', async (t) => {
  const root = await project(t)
  let state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'stale_candidate_initialize')
  assert.ok(state)
  const targetPath = `出图/${EPISODE}/panels/P001.png`
  const oldTask = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'P001',
    kind: 'image',
    target_slot: 'panel',
    target_output_path: targetPath,
    expected_content_hash: state.content_hash,
    promotion_required: true,
  })
  const oldNodeInput = oldTask.node_input_hash!

  const script = path.join(root, '脚本', EPISODE, 'panel_script.json')
  const source = JSON.parse(await fs.readFile(script, 'utf8')) as Record<string, unknown>
  const panels = source.panels as Array<Record<string, unknown>>
  panels[0].description = '编辑后的新画布内容'
  await fs.writeFile(script, `${JSON.stringify(source, null, 2)}\n`)
  state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'invalidate_old_candidate')
  assert.equal(state?.tasks.find((item) => item.job_id === oldTask.job_id)?.status, 'stale')
  const currentTask = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'P001',
    kind: 'image',
    target_slot: 'panel',
    target_output_path: targetPath,
    expected_content_hash: state!.content_hash,
    promotion_required: true,
  })
  const currentCandidate = path.join(root, currentTask.candidate_output_path!)
  await fs.mkdir(path.dirname(currentCandidate), { recursive: true })
  await fs.writeFile(currentCandidate, FINAL_PNG)
  await writeCandidateEvidence(root, {
    scope: 'task', jobId: currentTask.job_id, contentHash: currentTask.content_hash,
    targetPath, candidatePath: currentTask.candidate_output_path!, nodeId: 'P001',
    generationKind: 'image', targetSlot: 'panel', inputHash: currentTask.input_hash,
    nodeInputHash: currentTask.node_input_hash, humanAccepted: true,
  })
  state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'promote_current_candidate')
  const stable = path.join(root, targetPath)
  assert.deepEqual(await fs.readFile(stable), FINAL_PNG)

  const oldCandidate = path.join(root, oldTask.candidate_output_path!)
  await fs.mkdir(path.dirname(oldCandidate), { recursive: true })
  await fs.writeFile(oldCandidate, PNG)
  await writeCandidateEvidence(root, {
    scope: 'task', jobId: oldTask.job_id, contentHash: oldTask.content_hash,
    targetPath, candidatePath: oldTask.candidate_output_path!, nodeId: 'P001',
    generationKind: 'image', targetSlot: 'panel', inputHash: oldTask.input_hash,
    nodeInputHash: oldNodeInput, humanAccepted: true,
  })
  await synchronizeCanvasProduction(root, 'comic', canvas(root), 'ignore_stale_late_candidate')
  assert.deepEqual(await fs.readFile(stable), FINAL_PNG)
  await fs.access(oldCandidate)
})

test('new manual node task supersedes an overlapping production terminal for the same canvas revision', async (t) => {
  const root = await project(t)
  let state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'overlap_initialize')
  assert.ok(state)
  const targetPath = `出图/${EPISODE}/panels/P001.png`
  const production = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: '__episode__',
    kind: 'production',
    target_slot: 'final',
    target_output_path: `排版/${EPISODE}/长图/longstrip.png`,
    expected_content_hash: state.content_hash,
    promotion_required: true,
  })
  const manual = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'P001',
    kind: 'image',
    target_slot: 'panel',
    target_output_path: targetPath,
    expected_content_hash: state.content_hash,
    promotion_required: true,
  })
  state = await readCanvasProductionState(root, EPISODE)
  assert.equal(state?.tasks.find((item) => item.job_id === production.job_id)?.status, 'stale')

  const productionCandidate = canvasCandidateTargetRel(targetPath, production.job_id)
  await fs.mkdir(path.dirname(path.join(root, productionCandidate)), { recursive: true })
  await fs.writeFile(path.join(root, productionCandidate), PNG)
  await writeCandidateEvidence(root, {
    scope: 'node', jobId: production.job_id, contentHash: production.content_hash,
    targetPath, candidatePath: productionCandidate, nodeId: 'P001', generationKind: 'image',
    targetSlot: 'panel', inputHash: state!.node_fingerprints.P001.input_hash,
    taskInputHash: production.input_hash, humanAccepted: true,
  })
  await synchronizeCanvasProduction(root, 'comic', canvas(root), 'ignore_superseded_production')
  await assert.rejects(fs.access(path.join(root, targetPath)))
  await fs.access(path.join(root, productionCandidate))

  await fs.mkdir(path.dirname(path.join(root, manual.candidate_output_path!)), { recursive: true })
  await fs.writeFile(path.join(root, manual.candidate_output_path!), FINAL_PNG)
  await writeCandidateEvidence(root, {
    scope: 'task', jobId: manual.job_id, contentHash: manual.content_hash,
    targetPath, candidatePath: manual.candidate_output_path!, nodeId: 'P001', generationKind: 'image',
    targetSlot: 'panel', inputHash: manual.input_hash, nodeInputHash: manual.node_input_hash,
    humanAccepted: true,
  })
  state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'promote_manual_owner')
  assert.deepEqual(await fs.readFile(path.join(root, targetPath)), FINAL_PNG)
  assert.equal(state?.tasks.find((item) => item.job_id === manual.job_id)?.status, 'succeeded')
})

test('promotion recovers idempotently after rename but before authoritative receipt write', async (t) => {
  const root = await project(t)
  const state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'recovery_initialize')
  assert.ok(state)
  const targetPath = `出图/${EPISODE}/panels/P001.png`
  const task = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'P001',
    kind: 'image',
    target_slot: 'panel',
    target_output_path: targetPath,
    expected_content_hash: state.content_hash,
    promotion_required: true,
  })
  const candidate = path.join(root, task.candidate_output_path!)
  const stable = path.join(root, targetPath)
  await fs.mkdir(path.dirname(candidate), { recursive: true })
  await fs.mkdir(path.dirname(stable), { recursive: true })
  await fs.writeFile(candidate, FINAL_PNG)
  await writeCandidateEvidence(root, {
    scope: 'task', jobId: task.job_id, contentHash: task.content_hash,
    targetPath, candidatePath: task.candidate_output_path!, nodeId: 'P001',
    generationKind: 'image', targetSlot: 'panel', inputHash: task.input_hash,
    nodeInputHash: task.node_input_hash, humanAccepted: true,
  })
  // Simulate the process dying in the narrow window after atomic rename.
  await fs.rename(candidate, stable)
  const recovered = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'recover_promoted_bytes')
  assert.equal(recovered?.tasks.find((item) => item.job_id === task.job_id)?.status, 'succeeded')
  assert.equal(recovered?.node_fingerprints.P001.lifecycle, 'accepted')
  const receipt = JSON.parse(await fs.readFile(
    path.join(root, '生产数据', `canvas_task_receipt_${task.job_id}.json`),
    'utf8',
  )) as Record<string, unknown>
  assert.equal(receipt.promotion_authority, 'desktop_main_v1')
  assert.equal(receipt.output_sha256, sha256(FINAL_PNG))
})

test('candidate symlink cannot be promoted or modify the stable target', async (t) => {
  const root = await project(t)
  const state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'symlink_candidate_initialize')
  assert.ok(state)
  const targetPath = `出图/${EPISODE}/panels/P001.png`
  const task = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'P001',
    kind: 'image',
    target_slot: 'panel',
    target_output_path: targetPath,
    expected_content_hash: state.content_hash,
    promotion_required: true,
  })
  const stable = path.join(root, targetPath)
  const source = path.join(root, 'symlink-source.png')
  const candidate = path.join(root, task.candidate_output_path!)
  await fs.mkdir(path.dirname(stable), { recursive: true })
  await fs.mkdir(path.dirname(candidate), { recursive: true })
  await fs.writeFile(stable, PNG)
  await fs.writeFile(source, FINAL_PNG)
  await fs.symlink(source, candidate)
  await writeCandidateEvidence(root, {
    scope: 'task', jobId: task.job_id, contentHash: task.content_hash,
    targetPath, candidatePath: task.candidate_output_path!, nodeId: 'P001',
    generationKind: 'image', targetSlot: 'panel', inputHash: task.input_hash,
    nodeInputHash: task.node_input_hash, humanAccepted: true,
  })
  const after = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'reject_symlink_candidate')
  assert.deepEqual(await fs.readFile(stable), PNG)
  assert.equal((await fs.lstat(candidate)).isSymbolicLink(), true)
  assert.equal(after?.tasks.find((item) => item.job_id === task.job_id)?.status, 'submitted')
})

test('production node and final master use candidates before explicit final acceptance', async (t) => {
  const root = await project(t)
  let state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'production_candidate_initialize')
  assert.ok(state)
  const finalTarget = `排版/${EPISODE}/长图/longstrip.png`
  const task = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: '__episode__',
    kind: 'production',
    target_slot: 'final',
    target_output_path: finalTarget,
    expected_content_hash: state.content_hash,
    promotion_required: true,
  })
  const nodeTarget = `出图/${EPISODE}/panels/P001.png`
  const nodeCandidate = canvasCandidateTargetRel(nodeTarget, task.job_id)
  await fs.mkdir(path.dirname(path.join(root, nodeCandidate)), { recursive: true })
  await fs.writeFile(path.join(root, nodeCandidate), PNG)
  await writeCandidateEvidence(root, {
    scope: 'node', jobId: task.job_id, contentHash: task.content_hash,
    targetPath: nodeTarget, candidatePath: nodeCandidate, nodeId: 'P001',
    generationKind: 'image', targetSlot: 'panel',
    inputHash: state.node_fingerprints.P001.input_hash, taskInputHash: task.input_hash,
    humanAccepted: true,
  })
  state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'promote_production_node')
  assert.equal(state?.node_fingerprints.P001.lifecycle, 'accepted')
  const manifest = JSON.parse(await fs.readFile(
    path.join(root, '生产数据', `canvas_inputs_manifest_${EPISODE}.json`),
    'utf8',
  )) as { inputs_sha256: string }

  const finalCandidate = task.final_candidate_output_path!
  await fs.mkdir(path.dirname(path.join(root, finalCandidate)), { recursive: true })
  await fs.writeFile(path.join(root, finalCandidate), FINAL_PNG)
  await writeCandidateEvidence(root, {
    scope: 'final', jobId: task.job_id, contentHash: task.content_hash,
    targetPath: finalTarget, candidatePath: finalCandidate,
    taskInputHash: task.input_hash, inputsSha256: manifest.inputs_sha256,
  })
  state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'promote_final_candidate')
  assert.equal(state?.completion.complete, false, 'machine-complete master is not human final acceptance')
  assert.deepEqual(state?.completion.blockers, [])
  state = await acceptCanvasFinalProduct(root, 'comic', canvas(root), state!.content_hash)
  assert.equal(state.completion.complete, true)
  assert.equal(state?.tasks.find((item) => item.job_id === task.job_id)?.status, 'succeeded')
  assert.deepEqual(await fs.readFile(path.join(root, finalTarget)), FINAL_PNG)
  const compose = JSON.parse(await fs.readFile(
    path.join(root, '生产数据', `canvas_compose_receipt_${task.job_id}_promoted.json`),
    'utf8',
  )) as Record<string, unknown>
  assert.equal(compose.promotion_authority, 'desktop_main_v1')
})

test('a leftover generation intent rolls back config and fails its undispatched submitted task', async (t) => {
  const root = await project(t)
  const outputRel = `出图/${EPISODE}/panels/P001.png`
  const config = {
    kind: 'image' as const,
    target_slot: 'panel',
    target_output_path: outputRel,
    model: 'project-default',
    mode: 'text2image',
    aspect_ratio: '1:1',
    resolution: 'project',
    duration: 10,
    audio_enabled: false,
    count: 1 as const,
    reference_paths: [],
    marks: [],
    effects: [],
    camera_motion: 'none',
    prompt_language: 'project' as const,
    prompt_override: 'panel prompt',
  }
  const controls = {
    kind: 'anime_armory_canvas_generation_controls',
    version: 2,
    episode: EPISODE,
    configs: { 'image:P001:panel': config },
  }
  await fs.mkdir(path.join(root, '生产数据'), { recursive: true })
  const controlsFile = path.join(root, '生产数据', `canvas_generation_controls_${EPISODE}.json`)
  await fs.writeFile(controlsFile, `${JSON.stringify(controls, null, 2)}\n`)
  let state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'intent_test_state')
  assert.ok(state)
  const submitted = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'P001',
    kind: 'image',
    target_slot: 'panel',
    target_output_path: outputRel,
    expected_content_hash: state.content_hash,
  })
  const intentFile = path.join(root, '生产数据', `canvas_generation_intent_${EPISODE}.json`)
  await fs.writeFile(intentFile, `${JSON.stringify({
    kind: 'anime_armory_canvas_generation_intent',
    version: 1,
    episode: EPISODE,
    line: 'comic',
    clip_id: 'P001',
    generation_kind: 'image',
    target_slot: 'panel',
    target_output_path: outputRel,
    base_content_hash: state.content_hash,
    base_source_sha256: state.authoring.source_sha256,
    base_settings_sha256: state.authoring.settings_sha256,
    config,
    old_controls: null,
    created_at: '2000-01-01T00:00:00.000Z',
  }, null, 2)}\n`)

  await readCanvas(root, EPISODE, undefined, 'comic')
  await assert.rejects(fs.access(controlsFile))
  await assert.rejects(fs.access(intentFile))
  state = await readCanvasProductionState(root, EPISODE)
  assert.equal(state?.tasks.find((task) => task.job_id === submitted.job_id)?.status, 'failed')
})

test('storyboard midframe object preserves authored controls while projecting midframe_png', async (t) => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'canvas-midframe-'))
  t.after(() => fs.rm(root, { recursive: true, force: true }))
  await fs.mkdir(path.join(root, '脚本', EPISODE), { recursive: true })
  await fs.writeFile(path.join(root, '脚本', EPISODE, 'storyboard.json'), `${JSON.stringify({
    clips: [{
      id: 'CLIP01',
      label: 'midframe contract',
      prompt: 'prompt',
      continuity: {
        midframe: {
          midframe_png: `出图/${EPISODE}/CLIP01_mid.png`,
          at_sec: 3.25,
          split_at_sec: 3.5,
          reason: '动作转折',
          use: 'relay',
        },
      },
    }, {
      id: 'CLIP02',
      label: 'missing anchor paths',
      prompt: 'prompt 2',
      continuity: { anchors: [{ reason: '无声明路径锚帧' }] },
    }],
  }, null, 2)}\n`)
  const result = await readCanvas(root, EPISODE, undefined, 'n2d')
  const clip = result.canvas?.clips[0]
  assert.ok(clip?.first_frame_abs?.endsWith(`/出图/${EPISODE}/CLIP01_first.png`))
  assert.ok(clip?.video_abs?.endsWith(`/出视频/${EPISODE}/CLIP01.mp4`))
  assert.ok(clip?.frames.find((frame) => frame.role === 'end')?.abs?.endsWith(`/出图/${EPISODE}/CLIP01_end.png`))
  const missingAnchor = result.canvas?.clips[1]?.frames.find((frame) => frame.role === 'anchor')
  assert.ok(missingAnchor?.abs?.endsWith(`/出图/${EPISODE}/CLIP02_anchor-2-2.png`))
  const mid = result.canvas?.clips[0]?.frames.find((frame) => frame.role === 'anchor')
  assert.equal(mid?.at_sec, 3.25)
  assert.ok(mid?.abs?.endsWith(`/出图/${EPISODE}/CLIP01_mid.png`))
  assert.match(mid?.prompt || '', /动作转折/)

  const authoring = result.canvas ? await buildCanvasAuthoringInput(root, 'n2d', result.canvas) : null
  const source = JSON.stringify(authoring?.clips[0]?.editable)
  assert.match(source, /动作转折/)
  assert.match(source, /relay/)
  assert.doesNotMatch(source, /midframe_png/)

  await fs.mkdir(path.join(root, '出图', EPISODE), { recursive: true })
  await fs.mkdir(path.join(root, '出视频', EPISODE), { recursive: true })
  await fs.writeFile(path.join(root, '出图', EPISODE, 'CLIP01_first.png'), PNG)
  await fs.writeFile(path.join(root, '出视频', EPISODE, 'CLIP01.mp4'), 'video-bytes')
  const refreshed = await readCanvas(root, EPISODE, undefined, 'n2d')
  assert.equal(refreshed.canvas?.clips[0]?.first_frame_exists, true)
  assert.equal(refreshed.canvas?.clips[0]?.video_exists, true)
  const refreshedAuthoring = refreshed.canvas
    ? await buildCanvasAuthoringInput(root, 'n2d', refreshed.canvas)
    : null
  assert.equal(refreshedAuthoring?.clips[0]?.final_target.output_path, `出视频/${EPISODE}/CLIP01.mp4`)
  assert.match(JSON.stringify(refreshedAuthoring?.clips[0]?.runtime_inputs), /CLIP01_first\.png/)
})

test('renderer running acknowledgement clears a committed generation intent', async (t) => {
  const root = await project(t)
  const outputRel = `出图/${EPISODE}/panels/P001.png`
  const state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'ack_initialize')
  assert.ok(state)
  const submitted = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: 'P001',
    kind: 'image',
    target_slot: 'panel',
    target_output_path: outputRel,
    expected_content_hash: state.content_hash,
  })
  const intentFile = path.join(root, '生产数据', `canvas_generation_intent_${EPISODE}.json`)
  await fs.mkdir(path.dirname(intentFile), { recursive: true })
  await fs.writeFile(intentFile, `${JSON.stringify({
    kind: 'anime_armory_canvas_generation_intent',
    version: 1,
    episode: EPISODE,
    line: 'comic',
    clip_id: 'P001',
    generation_kind: 'image',
    target_slot: 'panel',
    target_output_path: outputRel,
    base_content_hash: state.content_hash,
    base_source_sha256: state.authoring.source_sha256,
    base_settings_sha256: state.authoring.settings_sha256,
    config: {},
    old_controls: null,
    created_at: new Date().toISOString(),
    owner_pid: process.pid,
    phase: 'task_committed',
    job_id: submitted.job_id,
  }, null, 2)}\n`)
  const otherIntentFile = path.join(root, '生产数据', `canvas_generation_intent_${EPISODE}_other.json`)
  const otherIntent = JSON.parse(await fs.readFile(intentFile, 'utf8')) as Record<string, unknown>
  await fs.writeFile(otherIntentFile, `${JSON.stringify({
    ...otherIntent,
    clip_id: 'OTHER',
    target_slot: 'first',
    target_output_path: `出图/${EPISODE}/OTHER_first.png`,
    job_id: 'other-job',
  }, null, 2)}\n`)
  await markCanvasProductionTaskRunning(root, EPISODE, submitted.job_id)
  await assert.rejects(fs.access(intentFile))
  await fs.access(otherIntentFile)
  const current = await readCanvasProductionState(root, EPISODE)
  assert.equal(current?.tasks.find((task) => task.job_id === submitted.job_id)?.status, 'running')
})

test('an incomplete accepted set removes an old inputs manifest after state CAS', async (t) => {
  const root = await project(t)
  const file = path.join(root, '生产数据', `canvas_inputs_manifest_${EPISODE}.json`)
  await fs.mkdir(path.dirname(file), { recursive: true })
  await fs.writeFile(file, '{"kind":"stale-complete-manifest"}\n')
  const state = await synchronizeCanvasProduction(root, 'comic', canvas(root), 'manifest_cleanup')
  assert.equal(state?.node_fingerprints.P001.lifecycle, 'ready')
  await assert.rejects(fs.access(file))
})

test('projection source and settings snapshots cannot be mixed across reads', async (t) => {
  const root = await project(t)
  await assert.rejects(
    buildCanvasAuthoringInput(root, 'comic', { ...canvas(root), source_file_sha256: '0'.repeat(64) }),
    /canvas_projection_source_snapshot_stale/,
  )
  await fs.writeFile(path.join(root, '_设置.md'), '画幅: 16:9\n')
  await assert.rejects(
    buildCanvasAuthoringInput(root, 'comic', { ...canvas(root), settings_file_sha256: 'f'.repeat(64) }),
    /canvas_projection_settings_snapshot_stale/,
  )
})

test('final video enforces concrete delivery specs and receipt-first selection', { concurrency: false }, async (t) => {
  const root = await videoProject(t)
  const probe = path.join(root, 'fixture-ffprobe.sh')
  await fs.writeFile(probe, `#!/bin/sh
for value in "$@"; do target="$value"; done
case "$target" in
  *bad-spec*|*junk*)
    printf '%s\\n' '{"streams":[{"codec_type":"video","width":1280,"height":720,"duration":"4"}],"format":{"duration":"4"}}'
    ;;
  *)
    printf '%s\\n' '{"streams":[{"codec_type":"video","width":1920,"height":1080,"duration":"10"},{"codec_type":"audio","duration":"10"}],"format":{"duration":"10"}}'
    ;;
esac
`)
  await fs.chmod(probe, 0o755)
  const previousProbe = process.env.FFPROBE_PATH
  process.env.FFPROBE_PATH = probe
  t.after(() => {
    if (previousProbe === undefined) delete process.env.FFPROBE_PATH
    else process.env.FFPROBE_PATH = previousProbe
  })

  let state = await synchronizeCanvasProduction(root, 'n2d', videoCanvas(root), 'video_initialize')
  assert.ok(state)
  const submitted = await recordCanvasTaskSubmit(root, {
    episode: EPISODE,
    node_id: '__episode__',
    kind: 'production',
    expected_content_hash: state.content_hash,
  })
  const nodeRel = `出视频/${EPISODE}/CLIP01.mp4`
  const nodeFile = path.join(root, nodeRel)
  await fs.mkdir(path.dirname(nodeFile), { recursive: true })
  await fs.writeFile(nodeFile, 'stable-node-video')
  await writeNodeEvidence(
    root,
    submitted.job_id,
    state.content_hash,
    state.node_fingerprints.CLIP01.input_hash,
    nodeRel,
    submitted.input_hash,
    true,
    'CLIP01',
    'video',
  )
  state = await synchronizeCanvasProduction(root, 'n2d', videoCanvas(root, nodeFile), 'video_node_receipt')
  assert.equal(state?.node_fingerprints.CLIP01.lifecycle, 'accepted')
  const manifest = JSON.parse(await fs.readFile(
    path.join(root, '生产数据', `canvas_inputs_manifest_${EPISODE}.json`),
    'utf8',
  )) as { inputs_sha256: string }

  const badRel = `合成/${EPISODE}/成片_bad-spec.mp4`
  await fs.mkdir(path.dirname(path.join(root, badRel)), { recursive: true })
  await fs.writeFile(path.join(root, badRel), 'wrong-resolution-duration-and-audio')
  await writeFinalEvidence(root, submitted.job_id, state!.content_hash, manifest.inputs_sha256, badRel)
  state = await synchronizeCanvasProduction(root, 'n2d', videoCanvas(root, nodeFile), 'bad_video_spec')
  assert.equal(state?.completion.complete, false)

  const goodRel = `合成/${EPISODE}/成片_good.mp4`
  const goodFile = path.join(root, goodRel)
  await fs.writeFile(goodFile, 'correct-master')
  await writeFinalEvidence(root, submitted.job_id, state!.content_hash, manifest.inputs_sha256, goodRel)
  const junkRel = `合成/${EPISODE}/成片_junk.mp4`
  const junkFile = path.join(root, junkRel)
  await fs.writeFile(junkFile, 'newer-but-invalid-master')
  const now = new Date()
  await fs.utimes(goodFile, new Date(now.getTime() - 10_000), new Date(now.getTime() - 10_000))
  await fs.utimes(junkFile, now, now)

  state = await synchronizeCanvasProduction(root, 'n2d', videoCanvas(root, nodeFile), 'receipt_first_good_master')
  assert.equal(state?.completion.complete, false)
  assert.deepEqual(state?.completion.blockers, [])
  assert.equal(state?.completion.artifact?.path, goodRel)

  state = await acceptCanvasFinalProduct(root, 'n2d', videoCanvas(root, nodeFile), state!.content_hash)
  assert.equal(state?.completion.complete, true)
  assert.equal(state?.completion.artifact?.path, goodRel)
})

test('media evidence rejects a file changed between hashing and ffprobe', { concurrency: false }, async (t) => {
  const root = await project(t)
  const file = path.join(root, 'changing.png')
  await fs.writeFile(file, FINAL_PNG)
  const probe = path.join(root, 'mutating-ffprobe.sh')
  await fs.writeFile(probe, `#!/bin/sh
for value in "$@"; do target="$value"; done
printf 'mutated-after-hash' >> "$target"
printf '%s\\n' '{"streams":[{"codec_type":"video","width":256,"height":256}],"format":{}}'
`)
  await fs.chmod(probe, 0o755)
  const previous = process.env.FFPROBE_PATH
  process.env.FFPROBE_PATH = probe
  t.after(() => {
    if (previous === undefined) delete process.env.FFPROBE_PATH
    else process.env.FFPROBE_PATH = previous
  })
  assert.equal(await probeCanvasProductionMedia(file), false)
})
