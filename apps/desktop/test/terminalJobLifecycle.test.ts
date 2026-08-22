import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import test from 'node:test'
import {
  canvasJobHardDeadlineMs,
  classifyCanvasDispatchReservation,
  decideCanvasJobWatchdog,
  settleEndedCanvasJob,
  shouldRehydrateCanvasJobWatchdog,
  shouldRetryCanvasPromptWrite,
  shouldSettleCanvasJobOnOwnerTeardown,
  takeJobsForEndedSession,
  terminalLaunchCommand,
} from '../src/renderer/src/terminalJobLifecycle.ts'

const MINUTE = 60_000
const HOUR = 60 * MINUTE

test('dispatch reservation distinguishes verified success from retry-required terminal states', () => {
  assert.equal(classifyCanvasDispatchReservation('submitted'), 'active')
  assert.equal(classifyCanvasDispatchReservation('running'), 'active')
  assert.equal(classifyCanvasDispatchReservation('succeeded'), 'succeeded')
  assert.equal(classifyCanvasDispatchReservation('failed'), 'rejected')
  assert.equal(classifyCanvasDispatchReservation('stale'), 'rejected')
  assert.equal(classifyCanvasDispatchReservation('cancelled'), 'rejected')
  assert.equal(classifyCanvasDispatchReservation(undefined), 'rejected')
  assert.equal(shouldRetryCanvasPromptWrite('retry'), true)
  assert.equal(shouldRetryCanvasPromptWrite('written'), false)
  assert.equal(shouldRetryCanvasPromptWrite('succeeded'), false)
  assert.equal(shouldRetryCanvasPromptWrite('rejected'), false)
  assert.equal(shouldRehydrateCanvasJobWatchdog('running', false, false), true)
  assert.equal(shouldRehydrateCanvasJobWatchdog('submitted', false, false), true)
  assert.equal(shouldRehydrateCanvasJobWatchdog('succeeded', false, false), false)
  assert.equal(shouldRehydrateCanvasJobWatchdog('failed', false, false), false)
  assert.equal(shouldRehydrateCanvasJobWatchdog('running', true, false), false)
  assert.equal(shouldRehydrateCanvasJobWatchdog('running', false, true), false)
  assert.equal(shouldSettleCanvasJobOnOwnerTeardown('term-123'), true)
  assert.equal(shouldSettleCanvasJobOnOwnerTeardown('recovered:job-123'), false)
})

test('agent launch replaces the shell so agent exit is an observable process exit', () => {
  const agentLaunch = terminalLaunchCommand("sh -c 'exit 7'", true)
  const agent = spawnSync('/bin/sh', ['-c', `${agentLaunch}; printf SHOULD_NOT_RUN`], { encoding: 'utf8' })
  assert.equal(agent.status, 7)
  assert.equal(agent.stdout, '')

  const nativeLaunch = terminalLaunchCommand("sh -c 'exit 7'", false)
  const native = spawnSync('/bin/sh', ['-c', `${nativeLaunch}; printf SHELL_ALIVE`], { encoding: 'utf8' })
  assert.equal(native.status, 0)
  assert.equal(native.stdout, 'SHELL_ALIVE')
})

test('claims an ended session exactly once', () => {
  const jobs = new Map([
    ['job-a', { sessionId: 'term-a', jobId: 'job-a' }],
    ['job-b', { sessionId: 'term-b', jobId: 'job-b' }],
  ])

  assert.deepEqual(takeJobsForEndedSession(jobs, 'term-a').map((job) => job.jobId), ['job-a'])
  assert.deepEqual(takeJobsForEndedSession(jobs, 'term-a'), [])
  assert.deepEqual([...jobs.keys()], ['job-b'])
})

test('retries receipt reconciliation and never fails a reconciled terminal job', async () => {
  let reads = 0
  let failures = 0
  const waits: number[] = []
  const result = await settleEndedCanvasJob({
    graceMs: 2500,
    wait: async (milliseconds) => { waits.push(milliseconds) },
    readStatus: async () => {
      reads += 1
      if (reads === 1) throw new Error('receipt is still being renamed')
      return 'succeeded'
    },
    failActiveTask: async () => { failures += 1 },
  })

  assert.equal(result, 'terminal')
  assert.equal(reads, 2)
  assert.equal(failures, 0)
  assert.deepEqual(waits, [2500, 250])
})

test('fails once only after reconciliation still reports an active job', async () => {
  let failures = 0
  const result = await settleEndedCanvasJob({
    wait: async () => undefined,
    readStatus: async () => 'running',
    failActiveTask: async () => { failures += 1 },
  })

  assert.equal(result, 'failed')
  assert.equal(failures, 1)
})

test('watchdog unbinds terminal receipts and enforces kind-specific hard deadlines', () => {
  const startedAt = Date.parse('2026-08-21T00:00:00.000Z')
  assert.deepEqual(decideCanvasJobWatchdog({
    status: 'succeeded', kind: 'production', submittedAt: new Date(startedAt).toISOString(),
  }, startedAt + 10 * MINUTE, startedAt), { action: 'unbind' })

  assert.deepEqual(decideCanvasJobWatchdog({
    status: 'running', kind: 'image', submittedAt: new Date(startedAt).toISOString(),
  }, startedAt + 45 * MINUTE, startedAt), { action: 'fail' })
  assert.deepEqual(decideCanvasJobWatchdog({
    status: 'running', kind: 'video', submittedAt: new Date(startedAt).toISOString(),
  }, startedAt + 2 * HOUR, startedAt), { action: 'fail' })
  assert.deepEqual(decideCanvasJobWatchdog({
    status: 'running', kind: 'production', submittedAt: new Date(startedAt).toISOString(),
  }, startedAt + 6 * HOUR, startedAt), { action: 'fail' })
  assert.equal(canvasJobHardDeadlineMs('unknown'), 45 * MINUTE)
})
