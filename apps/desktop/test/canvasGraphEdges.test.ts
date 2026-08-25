import assert from 'node:assert/strict'
import test from 'node:test'
import { buildCanvasGraphEdgePlan } from '../src/renderer/src/canvasGraphEdges.ts'

test('shared asset wires require one visible source with at least two visible targets', () => {
  const visibleNodeIds = new Set(['asset:shared', 'asset:single', 'frame:a:0', 'frame:b:0'])
  const edges = buildCanvasGraphEdgePlan({
    assetSources: [
      { nodeId: 'asset:shared', targetNodeIds: ['frame:a:0', 'frame:b:0'] },
      { nodeId: 'asset:single', targetNodeIds: ['frame:a:0'] },
    ],
    clipSources: [],
    visibleNodeIds,
    hasVideoLane: false,
  })

  assert.deepEqual(edges.map((edge) => edge.id), [
    'asset:shared->frame:a:0',
    'asset:shared->frame:b:0',
  ])
})

test('missing endpoints cannot create a shared-source wire', () => {
  const edges = buildCanvasGraphEdgePlan({
    assetSources: [{
      nodeId: 'asset:shared',
      targetNodeIds: ['frame:a:0', 'frame:missing:0'],
    }],
    clipSources: [],
    visibleNodeIds: new Set(['asset:shared', 'frame:a:0']),
    hasVideoLane: false,
  })

  assert.deepEqual(edges, [])
})

test('metadata-only shared sources never create wires without a visible source node', () => {
  const edges = buildCanvasGraphEdgePlan({
    assetSources: [{
      nodeId: 'asset:hidden-anchor',
      targetNodeIds: ['frame:a:0', 'frame:b:0'],
    }],
    clipSources: [],
    visibleNodeIds: new Set(['frame:a:0', 'frame:b:0']),
    hasVideoLane: false,
  })

  assert.deepEqual(edges, [])
})

test('direct visible frame-to-video dependencies remain and dangling ones are filtered', () => {
  const edges = buildCanvasGraphEdgePlan({
    assetSources: [],
    clipSources: [{
      videoNodeId: 'video:a',
      frameNodeIds: ['frame:a:0', 'frame:a:1', 'frame:missing:0'],
      videoExists: true,
    }],
    visibleNodeIds: new Set(['video:a', 'frame:a:0', 'frame:a:1']),
    hasVideoLane: true,
  })

  assert.deepEqual(edges.map((edge) => [edge.source, edge.target, edge.className]), [
    ['frame:a:0', 'video:a', 'video-edge video-edge-done'],
    ['frame:a:1', 'video:a', 'video-edge video-edge-done'],
  ])
})
