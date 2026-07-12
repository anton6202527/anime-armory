#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const {
  CREATION_ROOT,
  LINE_KEY_BY_NAME,
  demoAssetName,
  parseWorkRel,
} = require('../demo_assets.cjs');

const CREATIVE_LINES = ['写小说', '制漫剧', '画漫画', '写歌', '制MV', '拍广告'];
const CONFIG_REL = path.join('tools', 'e2a', 'demo-works.json');

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
        console.warn(`[e2a] skip demo without _进度.md: ${rel}`);
        return null;
      }
      return rel;
    }
  } catch (_e) {
    // fall through to the skip below
  }
  console.warn(`[e2a] skip missing demo work: ${rel}`);
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

function allProgressWorks(root) {
  const picks = [];
  for (const line of CREATIVE_LINES) {
    const lineDir = path.join(root, CREATION_ROOT, line);
    if (!fs.existsSync(lineDir)) continue;
    const works = fs.readdirSync(lineDir, { withFileTypes: true })
      .filter((entry) => entry.isDirectory() && !entry.name.startsWith('.') && !entry.name.startsWith('_'))
      .sort((a, b) => a.name.localeCompare(b.name, 'zh-Hans-CN'));
    for (const work of works) {
      const rel = `${CREATION_ROOT}/${line}/${work.name}`;
      if (fs.existsSync(path.join(lineDir, work.name, '_进度.md'))) picks.push(rel);
    }
  }
  return picks;
}

function main() {
  const args = process.argv.slice(2);
  const rootArg = args.find((arg) => !arg.startsWith('--')) || '.';
  const root = path.resolve(rootArg);
  const allProgress = args.includes('--all-progress');
  const withAssets = args.includes('--assets');
  let picks;
  try {
    picks = allProgress ? allProgressWorks(root) : demoWorks(root);
  } catch (e) {
    console.error(e.message);
    process.exit(1);
  }
  if (picks.length > 0) {
    if (withAssets) {
      console.log(picks.map((rel) => {
        const work = parseWorkRel(rel);
        return [work.rel, LINE_KEY_BY_NAME.get(work.line), demoAssetName(work.rel)].join('\t');
      }).join('\n'));
    } else {
      console.log(picks.join('\n'));
    }
    return;
  }

  process.exit(0);
}

main();
