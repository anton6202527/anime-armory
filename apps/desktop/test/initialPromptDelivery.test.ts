import assert from 'node:assert/strict'
import test from 'node:test'
import {
  consumeInitialPromptFromWork,
  consumeInitialPromptRequest,
  createInitialPromptRequest,
  deliverInitialPrompt,
} from '../src/renderer/src/initialPromptDelivery.ts'

test('initial prompt request identity is stable and independent from a work path', () => {
  const first = createInitialPromptRequest('同一条请求', 1_000)
  const second = createInitialPromptRequest('同一条请求', 1_000)

  assert.notEqual(first.id, second.id)
  assert.equal(first.prompt, '同一条请求')
  assert.equal(Object.hasOwn(first, 'root'), false)
})

test('initial prompt is delivered only after the CLI launch outcome is acknowledged', async () => {
  const request = createInitialPromptRequest('第一行\n第二行：$HOME `whoami` \'引号\'', 2_000)
  const received: string[] = []

  const pending = await deliverInitialPrompt(request, async (prompt) => {
    received.push(prompt)
    return false
  })
  const delivered = await deliverInitialPrompt(request, async (prompt) => {
    received.push(prompt)
    return true
  })

  assert.equal(pending, 'pending')
  assert.equal(delivered, 'delivered')
  assert.deepEqual(received, [request.prompt, request.prompt])
})

test('a throwing launch remains pending so the same request can be retried', async () => {
  const request = createInitialPromptRequest('retry me', 3_000)
  const result = await deliverInitialPrompt(request, async () => {
    throw new Error('PTY is switching')
  })

  assert.equal(result, 'pending')
})

test('a late acknowledgement cannot consume a newer launch request', () => {
  const oldRequest = createInitialPromptRequest('old', 4_000)
  const newRequest = createInitialPromptRequest('new', 4_001)

  assert.equal(consumeInitialPromptRequest(newRequest, oldRequest.id), newRequest)
  assert.equal(consumeInitialPromptRequest(newRequest, newRequest.id), undefined)
})

test('renaming a work cannot make its launch acknowledgement miss the request', () => {
  const request = createInitialPromptRequest('rename-safe', 5_000)
  const renamedWork = { id: '/workspace/new-name', initialPrompt: request }

  assert.deepEqual(
    consumeInitialPromptFromWork(renamedWork, request.id),
    { id: '/workspace/new-name', initialPrompt: undefined },
  )
})
