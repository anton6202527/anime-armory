import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const clipNodeSource = await readFile(
  new URL("../src/components/ClipNode.tsx", import.meta.url),
  "utf8",
);

function openingTagAfter(marker, tag) {
  const markerIndex = clipNodeSource.indexOf(marker);
  assert.notEqual(markerIndex, -1, `missing marker: ${marker}`);
  const sourceAfterMarker = clipNodeSource.slice(markerIndex);
  const match = sourceAfterMarker.match(new RegExp(`<${tag}\\b[\\s\\S]*?>`));
  assert.ok(match, `missing <${tag}> after ${marker}`);
  return match[0];
}

test("dormant video preview leaves pointer-down available for React Flow dragging", () => {
  const tag = openingTagAfter("if (!activated)", "button");

  assert.doesNotMatch(tag, /\bnodrag\b/);
  assert.doesNotMatch(tag, /onPointerDown/);
});

test("video controls still opt out of node dragging", () => {
  const marker = 'className="canvas-video-controls nodrag"';
  const markerIndex = clipNodeSource.indexOf(marker);
  assert.notEqual(markerIndex, -1, `missing marker: ${marker}`);
  const controlsOpening = clipNodeSource.slice(markerIndex, markerIndex + 180);

  assert.match(controlsOpening, /\bnodrag\b/);
  assert.match(controlsOpening, /onPointerDown=\{\(event\) => event\.stopPropagation\(\)\}/);
});
