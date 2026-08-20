import assert from 'node:assert/strict'
import test from 'node:test'
import {
  copySelectedTerminalText,
  type TerminalSelectionSource,
} from '../src/renderer/src/terminalClipboard.ts'

function selectionSource(hasSelection: boolean, selection: string): TerminalSelectionSource {
  return {
    hasSelection: () => hasSelection,
    getSelection: () => selection,
  }
}

test('copies the exact terminal selection, including Chinese text and line breaks', () => {
  const writes: string[] = []
  const copied = copySelectedTerminalText(
    selectionSource(true, '第一行\n第二行：复制成功'),
    (text) => writes.push(text),
  )

  assert.equal(copied, true)
  assert.deepEqual(writes, ['第一行\n第二行：复制成功'])
})

test('does not write when the terminal has no active selection', () => {
  const writes: string[] = []
  const copied = copySelectedTerminalText(
    selectionSource(false, 'stale selection'),
    (text) => writes.push(text),
  )

  assert.equal(copied, false)
  assert.deepEqual(writes, [])
})

test('does not clear or overwrite the clipboard when a selection is cleared', () => {
  const writes = ['existing clipboard']
  const copied = copySelectedTerminalText(
    selectionSource(true, ''),
    (text) => writes.push(text),
  )

  assert.equal(copied, false)
  assert.deepEqual(writes, ['existing clipboard'])
})
