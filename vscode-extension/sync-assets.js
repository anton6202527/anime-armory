#!/usr/bin/env node
// Copy the REAL skills/ + tools/ + entry docs + creation manuals from the repo
// into ./assets so they ship INSIDE the .vsix — making the extension
// self-contained (install on any VS Code, no anime-armory source checkout
// needed). Run automatically on `vsce package` via the `vscode:prepublish`
// hook; run manually with `npm run sync-assets`.
//
// Works/创作区 live next to the extension source, not under assets/. Release
// packaging may seed each creative line's champion demo under that work root;
// this script also refreshes the lightweight 使用手册.md files there so the
// extension panel can show them inside the bundled seed work root.
const fs = require('fs');
const path = require('path');

const repo = path.resolve(__dirname, '..');
const assets = path.join(__dirname, 'assets');
const CREATION_ROOT = '创作区';
const MANUAL_RELS = [
  `${CREATION_ROOT}/使用手册.md`,
  `${CREATION_ROOT}/写小说/使用手册.md`,
  `${CREATION_ROOT}/制漫剧/使用手册.md`,
  `${CREATION_ROOT}/画漫画/使用手册.md`,
  `${CREATION_ROOT}/写歌/使用手册.md`,
  `${CREATION_ROOT}/制MV/使用手册.md`,
  `${CREATION_ROOT}/拍广告/使用手册.md`,
];

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

function copyManuals(destRoot, label) {
  let copied = 0;
  for (const rel of MANUAL_RELS) {
    const src = path.join(repo, rel);
    if (!fs.existsSync(src)) {
      console.error(`[sync-assets] 缺少创作区使用手册，无法打包: ${rel}`);
      process.exit(1);
    }
    const dst = path.join(destRoot, rel);
    fs.mkdirSync(path.dirname(dst), { recursive: true });
    fs.copyFileSync(src, dst);
    copied += 1;
  }
  console.log(`[sync-assets] synced ${copied} creation manuals → ${label}`);
  return copied;
}

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

  // 4) creation manuals. assets/ keeps a read-only canonical copy; the extension
  // seed 创作区 keeps the same files visible in the work tree.
  const manualFiles = copyManuals(assets, 'assets/创作区');
  copyManuals(__dirname, 'vscode-extension/创作区');

  // stamp the snapshot date for display/debugging
  fs.writeFileSync(
    path.join(assets, '_synced_at.txt'),
    new Date().toISOString() + '\n', 'utf8');

  console.log(`[sync-assets] bundled ${count(path.join(assets, 'skills'))} skill files + ${toolFiles} tool files + ${manualFiles} manuals + docs → assets/`);
}

main();
