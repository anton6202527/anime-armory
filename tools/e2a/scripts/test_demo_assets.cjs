#!/usr/bin/env node
const assert = require('node:assert/strict');
const test = require('node:test');
const {
  demoAssetName,
  releaseDownloadUrl,
} = require('../demo_assets.cjs');

test('demo asset names are stable, ASCII-only, and collision-safe across works', () => {
  const rel = '创作区/制漫剧/那妖魔是姜大人';
  const asset = demoAssetName(rel);
  assert.equal(asset, 'AnimeArmory_demo_n2d_23fcd23e.zip');
  assert.equal(demoAssetName(rel), asset);
  assert.match(asset, /^[A-Za-z0-9._-]+$/);
  assert.notEqual(asset, demoAssetName('创作区/制漫剧/万妖图魔录'));
});

test('line key remains part of the ASCII asset identity', () => {
  const names = [
    '创作区/写小说/同名作品',
    '创作区/制漫剧/同名作品',
    '创作区/画漫画/同名作品',
    '创作区/写歌/同名作品',
    '创作区/制MV/同名作品',
    '创作区/拍广告/同名作品',
  ].map(demoAssetName);
  assert.equal(new Set(names).size, names.length);
  for (const name of names) assert.match(name, /^AnimeArmory_demo_(novel|n2d|comic|song|mv|ad)_[a-f0-9]{8}\.zip$/);
});

test('fixed-tag download URL uses the exact ASCII asset name', () => {
  const asset = demoAssetName('创作区/画漫画/红楼梦');
  assert.equal(
    releaseDownloadUrl('owner/repo', 'electron-v0.1.0', asset),
    `https://github.com/owner/repo/releases/download/electron-v0.1.0/${asset}`,
  );
});
