#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const FIXED_WORKS = [
  '创作区/制漫剧/那妖魔是姜大人',
];

function fixedWork(root, rel) {
  const abs = path.join(root, rel);
  try {
    if (fs.statSync(abs).isDirectory()) return rel;
  } catch (_e) {
    // fall through to the explicit error below
  }
  throw new Error(`Fixed demo work is missing: ${rel}`);
}

function demoWorks(root) {
  const picks = [];
  for (const rel of FIXED_WORKS) {
    picks.push(fixedWork(root, rel));
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

  console.error(`No fixed demo work found under ${root}`);
  process.exit(1);
}

main();
