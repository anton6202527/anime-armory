#!/usr/bin/env node
// Copy the VS Code product subset into ./assets so it ships inside the .vsix.
// This client intentionally bundles only novel / n2d / comic workflows. The
// seed 创作区 mirrors those three lines and contains one source-novel demo.
// Run automatically on `vsce package` via `vscode:prepublish`, or manually with
// `npm run sync-assets`.
const fs = require('fs');
const path = require('path');

const repo = path.resolve(__dirname, '../..');
const assets = path.join(__dirname, 'assets');
const CREATION_ROOT = '创作区';
const SKILL_FAMILIES = ['novel', 'n2d', 'comic'];
const WORK_LINE_DIRS = ['写小说', '制漫剧', '画漫画'];
const MANUAL_RELS = [
  `${CREATION_ROOT}/使用手册.md`,
  `${CREATION_ROOT}/写小说/使用手册.md`,
  `${CREATION_ROOT}/制漫剧/使用手册.md`,
  `${CREATION_ROOT}/画漫画/使用手册.md`,
];
const NOVEL_DEMO_REL = `${CREATION_ROOT}/写小说/那妖魔是姜大人`;

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

function isBundledSkill(name) {
  return SKILL_FAMILIES.some((family) => name === family || name.startsWith(`${family}-`));
}

function copySelectedSkills() {
  const srcRoot = path.join(repo, 'skills');
  const dstRoot = path.join(assets, 'skills');
  fs.mkdirSync(dstRoot, { recursive: true });

  for (const entry of fs.readdirSync(srcRoot, { withFileTypes: true })) {
    if (!entry.isDirectory() || !isBundledSkill(entry.name)) continue;
    fs.cpSync(path.join(srcRoot, entry.name), path.join(dstRoot, entry.name), {
      recursive: true,
      filter,
    });
  }

  fs.writeFileSync(
    path.join(dstRoot, 'README.md'),
    '# VS Code bundled skills\n\n' +
      'This client bundles only the three supported workflow families:\n\n' +
      '- `novel` and `novel-*`\n' +
      '- `n2d` and `n2d-*`\n' +
      '- `comic` and `comic-*`\n\n' +
      'The full repository contains additional workflow families that are not included in this VSIX.\n',
    'utf8',
  );
  return count(dstRoot);
}

function syncSeedWorks() {
  const seedRoot = path.join(__dirname, CREATION_ROOT);
  fs.mkdirSync(seedRoot, { recursive: true });

  for (const entry of fs.readdirSync(seedRoot, { withFileTypes: true })) {
    if (entry.name === '使用手册.md') continue;
    if (entry.isDirectory() && WORK_LINE_DIRS.includes(entry.name)) continue;
    fs.rmSync(path.join(seedRoot, entry.name), { recursive: true, force: true });
  }

  for (const line of WORK_LINE_DIRS) {
    const lineRoot = path.join(seedRoot, line);
    fs.mkdirSync(lineRoot, { recursive: true });
    for (const entry of fs.readdirSync(lineRoot, { withFileTypes: true })) {
      if (entry.name === '使用手册.md') continue;
      fs.rmSync(path.join(lineRoot, entry.name), { recursive: true, force: true });
    }
  }

  const demoSrc = path.join(repo, NOVEL_DEMO_REL);
  if (!fs.existsSync(demoSrc)) {
    console.error(`[sync-assets] 缺少小说 demo，无法打包: ${NOVEL_DEMO_REL}`);
    process.exit(1);
  }
  const demoDst = path.join(__dirname, NOVEL_DEMO_REL);
  fs.cpSync(demoSrc, demoDst, { recursive: true, filter });
  return count(demoDst);
}

function copyManuals(sourceRoot, destRoot, label) {
  let copied = 0;
  for (const rel of MANUAL_RELS) {
    const src = path.join(sourceRoot, rel);
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
    console.error('[sync-assets] 找不到 ../../skills —— 必须在 anime-armory 仓库内运行');
    process.exit(1);
  }
  fs.rmSync(assets, { recursive: true, force: true });
  fs.mkdirSync(assets, { recursive: true });

  // 1) the product skill subset: novel / n2d / comic only.
  const skillFiles = copySelectedSkills();

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

  // 4) rebuild the seed work root, then mirror its three manuals into assets/.
  const demoFiles = syncSeedWorks();
  const manualFiles = copyManuals(__dirname, assets, 'assets/创作区');

  // stamp the snapshot date for display/debugging
  fs.writeFileSync(
    path.join(assets, '_synced_at.txt'),
    new Date().toISOString() + '\n', 'utf8');

  console.log(
    `[sync-assets] bundled ${skillFiles} skill files (${SKILL_FAMILIES.join(', ')}) + ` +
      `${toolFiles} tool files + ${manualFiles} manuals + ${demoFiles} novel demo files + docs → assets/`,
  );
}

main();
