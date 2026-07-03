#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const CREATION_ROOT = '创作区';
const LINES = ['制漫剧', '拍广告', '制MV', '写歌', '写小说'];
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

function demoWorks(root) {
  const picks = [];
  for (const line of LINES) {
    const best = bestProgressWork(root, line);
    if (best) picks.push(best);
  }
  return picks;
}

function main() {
  const root = path.resolve(process.argv[2] || '.');
  const picks = demoWorks(root);
  if (picks.length > 0) {
    console.log(picks.join('\n'));
    return;
  }

  console.error(`No demo work found under ${path.join(root, CREATION_ROOT)}`);
  process.exit(1);
}

main();
