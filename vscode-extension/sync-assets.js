#!/usr/bin/env node
// Copy the REAL skills/ + tools/ + entry docs from the repo into ./assets so they ship
// INSIDE the .vsix — making the extension self-contained (install on any VS Code,
// no anime-armory source checkout needed). Run automatically on `vsce package` via
// the `vscode:prepublish` hook; run manually with `npm run sync-assets`.
//
// Works/创作区 live next to the extension source, not under assets/. Release
// packaging may seed each creative line's champion demo under that work root.
const fs = require('fs');
const path = require('path');

const repo = path.resolve(__dirname, '..');
const assets = path.join(__dirname, 'assets');

const SKIP_NAMES = new Set(['__pycache__', 'node_modules', '.git', '.DS_Store']);
const filter = (src) => {
  const b = path.basename(src);
  if (SKIP_NAMES.has(b)) return false;
  if (b.endsWith('.pyc') || b.endsWith('.vsix')) return false;
  if (fs.lstatSync(src).isSymbolicLink()) return false; // never bundle dangling links
  return true;
};

const count = (dir) => {
  let n = 0;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.isDirectory()) n += count(path.join(dir, e.name));
    else n += 1;
  }
  return n;
};

function main() {
  if (!fs.existsSync(path.join(repo, 'skills'))) {
    console.error('[sync-assets] 找不到 ../skills —— 必须在 anime-armory 仓库内运行');
    process.exit(1);
  }
  fs.rmSync(assets, { recursive: true, force: true });
  fs.mkdirSync(assets, { recursive: true });

  // 1) the core asset: skills/
  fs.cpSync(path.join(repo, 'skills'), path.join(assets, 'skills'), { recursive: true, filter });

  // 2) repo-level maintenance tools
  const cleanupTool = path.join(repo, 'tools', 'shared-cleanup');
  let toolFiles = 0;
  if (fs.existsSync(cleanupTool)) {
    fs.mkdirSync(path.join(assets, 'tools'), { recursive: true });
    fs.cpSync(cleanupTool, path.join(assets, 'tools', 'shared-cleanup'), { recursive: true, filter });
    toolFiles = count(path.join(assets, 'tools', 'shared-cleanup'));
  }

  // 3) public usage docs (flat in assets/). This is the extension README, not
  // the repo overview, so the sidebar stays focused on using the workflow.
  fs.copyFileSync(path.join(__dirname, 'README.md'), path.join(assets, 'README.md'));

  // stamp the snapshot date for display/debugging
  fs.writeFileSync(
    path.join(assets, '_synced_at.txt'),
    new Date().toISOString() + '\n', 'utf8');

  console.log(`[sync-assets] bundled ${count(path.join(assets, 'skills'))} skill files + ${toolFiles} tool files + docs → assets/`);
}

main();
