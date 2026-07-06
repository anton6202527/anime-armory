#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const CREATION_ROOT = '创作区';
const LINES = ['制漫剧', '画漫画', '拍广告', '制MV', '写歌', '写小说'];
const FIXED_WORKS_BY_LINE = {
  '制漫剧': '那妖魔是姜大人',
};
const collator = new Intl.Collator('zh');

function doneCount(file) {
  try {
    return (fs.readFileSync(file, 'utf8').match(/✅/g) || []).length;
  } catch (_e) {
    return -1;
  }
}

function listLineWorks(root, line) {
  const lineDir = path.join(root, CREATION_ROOT, line);
  try {
    return fs.readdirSync(lineDir, { withFileTypes: true })
      .filter((entry) => entry.isDirectory() && !entry.name.startsWith('.') && !entry.name.startsWith('_'))
      .map((entry) => entry.name)
      .sort((a, b) => collator.compare(a, b));
  } catch (_e) {
    return [];
  }
}

function bestProgressWork(root, line) {
  let best = null;
  for (const name of listLineWorks(root, line)) {
    const rel = `${CREATION_ROOT}/${line}/${name}`;
    const done = doneCount(path.join(root, CREATION_ROOT, line, name, '_进度.md'));
    if (done < 0) continue;
    if (!best || done > best.done) {
      best = { rel, done };
    }
  }
  return best && best.rel;
}

function fixedWork(root, line) {
  const name = FIXED_WORKS_BY_LINE[line];
  if (!name) return null;
  const rel = `${CREATION_ROOT}/${line}/${name}`;
  const abs = path.join(root, CREATION_ROOT, line, name);
  try {
    if (fs.statSync(abs).isDirectory()) return rel;
  } catch (_e) {
    // fall through to the explicit error below
  }
  throw new Error(`Fixed demo work is missing: ${rel}`);
}

function demoWorks(root) {
  const picks = [];
  for (const line of LINES) {
    const fixed = fixedWork(root, line);
    if (fixed) {
      picks.push(fixed);
      continue;
    }
    const best = bestProgressWork(root, line);
    if (best) picks.push(best);
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

  console.error(`No demo work found under ${path.join(root, CREATION_ROOT)}`);
  process.exit(1);
}

main();
