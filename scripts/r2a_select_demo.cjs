#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const CREATION_ROOT = '创作区';
const CREATIVE_LINES = ['写小说', '制漫剧', '画漫画', '写歌', '制MV', '拍广告'];
const CONFIG_REL = path.join('desktop', 'demo-works.json');

function parseWorkRel(rel) {
  const parts = String(rel || '').split('/');
  if (parts.length !== 3 || parts[0] !== CREATION_ROOT || !parts[1] || !parts[2]) {
    throw new Error(`Invalid demo work path: ${rel}`);
  }
  return { root: parts[0], line: parts[1], name: parts[2], rel };
}

function normalizeWorkEntry(entry) {
  if (typeof entry === 'string') {
    return entry.trim();
  }
  if (entry && typeof entry === 'object') {
    if (typeof entry.rel === 'string') {
      return entry.rel.trim();
    }
    if (typeof entry.line === 'string' && typeof entry.name === 'string') {
      return `${CREATION_ROOT}/${entry.line.trim()}/${entry.name.trim()}`;
    }
  }
  throw new Error(`Invalid demo work entry: ${JSON.stringify(entry)}`);
}

function fixedWork(root, rel) {
  const abs = path.join(root, rel);
  try {
    if (fs.statSync(abs).isDirectory()) {
      const progress = path.join(abs, '_进度.md');
      if (!fs.existsSync(progress)) {
        console.warn(`[r2a] skip demo without _进度.md: ${rel}`);
        return null;
      }
      return rel;
    }
  } catch (_e) {
    // fall through to the skip below
  }
  console.warn(`[r2a] skip missing demo work: ${rel}`);
  return null;
}

function demoWorks(root) {
  const configPath = path.join(root, CONFIG_REL);
  if (!fs.existsSync(configPath)) {
    return [];
  }
  const cfg = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  const known = new Set(CREATIVE_LINES);
  if (!Array.isArray(cfg.works) || cfg.works.length === 0) {
    return [];
  }

  const picks = [];
  const seen = new Set();
  for (const entry of cfg.works) {
    const rel = normalizeWorkEntry(entry);
    const parsed = parseWorkRel(rel);
    if (!known.has(parsed.line)) {
      throw new Error(`Unknown demo line in work path: ${rel}`);
    }
    if (seen.has(rel)) {
      continue;
    }
    seen.add(rel);
    const selected = fixedWork(root, rel);
    if (selected) {
      picks.push(selected);
    }
  }
  return picks;
}

function main() {
  const root = path.resolve(process.argv[2] || '.');
  let picks;
  try {
    picks = demoWorks(root);
  } catch (e) {
    console.error(e.message);
    process.exit(1);
  }
  if (picks.length > 0) {
    console.log(picks.join('\n'));
    return;
  }

  process.exit(0);
}

main();
