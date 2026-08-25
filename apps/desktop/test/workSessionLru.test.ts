import assert from 'node:assert/strict'
import test from 'node:test'
import {
  MAX_RETAINED_WORK_SESSIONS,
  removeWorkSession,
  touchWorkSession,
} from '../src/renderer/src/workSessionLru.ts'

type Session = { id: string; name: string }

function session(id: string): Session {
  return { id, name: id.toUpperCase() }
}

test('work session pool keeps at most three mounted sessions', () => {
  let sessions: Session[] = []
  for (const id of ['a', 'b', 'c']) {
    sessions = touchWorkSession(sessions, session(id)).sessions
  }

  const result = touchWorkSession(sessions, session('d'))
  assert.equal(MAX_RETAINED_WORK_SESSIONS, 3)
  assert.deepEqual(result.sessions.map((item) => item.id), ['b', 'c', 'd'])
  assert.deepEqual(result.evicted.map((item) => item.id), ['a'])
})

test('visiting an existing work moves it to the MRU edge', () => {
  const initial = [session('a'), session('b'), session('c')]
  const touched = touchWorkSession(initial, { id: 'a', name: 'A updated' })
  assert.deepEqual(touched.sessions.map((item) => item.id), ['b', 'c', 'a'])
  assert.equal(touched.sessions[2]?.name, 'A updated')

  const result = touchWorkSession(touched.sessions, session('d'))
  assert.deepEqual(result.evicted.map((item) => item.id), ['b'])
  assert.deepEqual(result.sessions.map((item) => item.id), ['c', 'a', 'd'])
})

test('removing a work releases its retained session without reordering others', () => {
  const result = removeWorkSession([session('a'), session('b'), session('c')], 'b')
  assert.deepEqual(result.map((item) => item.id), ['a', 'c'])
})
