#!/usr/bin/env node
// desktop-bundle engine (driven by `/toa --desktop`) — copy the REAL skills/ (+ repo maintenance tools) from the repo
// into ./src-tauri/resources/ so they ship INSIDE the packaged .app/.dmg, making
// the desktop app self-contained (install on any machine; no anime-arsenal
// source checkout needed). ALSO bundle each creative line's most-complete work
// as a seedable sample so a fresh app is never empty.
//
// Runs automatically before BOTH `tauri dev` and `tauri build` via tauri.conf.json
// (beforeDevCommand / beforeBuildCommand).
// Demos are ON BY DEFAULT; turn them off only with --no-demos or
// desktop/bundle-demos.json { "include_demos": false }.
// Run manually via `/toa --desktop[-demos]` (formerly the /tod slash command), or
// directly `node sync-skills.cjs [--no-demos]`.
//
// Consumption (wired in src-tauri): a packaged app whose live DEFAULT_REPO is
// absent falls back to <resourceDir>/resources as its skills repo (Rust
// `resolve_repo`); bundled demos are seeded once into the user's ~/AnimeArmory
// workspace (Rust `seed_demos`). In dev the live checkout always wins.
const fs = require('fs');
const path = require('path');

const repo = path.resolve(__dirname, '..');
const bundle = path.join(__dirname, 'src-tauri', 'resources');
const demoConfigPath = path.join(__dirname, 'bundle-demos.json');

// the 5 creative lines, by product dir under 创作区 (mirror src-tauri/src/commands.rs LINES)
const CREATION_ROOT = '创作区';
const LINES = ['制漫剧', '拍广告', '制MV', '写歌', '写小说'];

const SKIP_NAMES = new Set(['__pycache__', 'node_modules', '.git', '.DS_Store', '_voicecache']);
const filter = (src) => {
  const b = path.basename(src);
  if (SKIP_NAMES.has(b)) return false;
  if (b.endsWith('.pyc') || b.endsWith('.vsix')) return false;
  if (fs.lstatSync(src).isSymbolicLink()) return false; // never bundle dangling links
  return true;
};

const count = (dir) => {
  if (!fs.existsSync(dir)) return 0;
  let n = 0;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.isDirectory()) n += count(path.join(dir, e.name));
    else n += 1;
  }
  return n;
};

// each line's champion = the work dir whose _进度.md has the most ✅ (done stages)
function champions() {
  const picks = [];
  for (const line of LINES) {
    const lineDir = path.join(repo, CREATION_ROOT, line);
    if (!fs.existsSync(lineDir)) continue;
    let best = null;
    const works = fs.readdirSync(lineDir, { withFileTypes: true })
      .filter((e) => e.isDirectory() && !e.name.startsWith('.') && !e.name.startsWith('_'))
      .sort((a, b) => a.name.localeCompare(b.name));
    for (const e of works) {
      const prog = path.join(lineDir, e.name, '_进度.md');
      if (!fs.existsSync(prog)) continue;
      const done = (fs.readFileSync(prog, 'utf8').match(/✅/g) || []).length;
      if (!best || done > best.done) best = { line, name: e.name, done };
    }
    if (best) picks.push(best);
  }
  return picks;
}

// Demos are ON BY DEFAULT; this only reports an EXPLICIT opt-out written into
// bundle-demos.json ({ "include_demos": false }). Anything else → demos stay on.
function configDisablesDemos() {
  if (!fs.existsSync(demoConfigPath)) return false;
  try {
    const cfg = JSON.parse(fs.readFileSync(demoConfigPath, 'utf8'));
    return cfg && cfg.include_demos === false;
  } catch (e) {
    console.warn(`[desktop-bundle] 忽略无效 demo 配置 ${demoConfigPath}: ${e.message}`);
    return false;
  }
}

function main() {
  // Each line's most-complete work ships as a sample by default (so a fresh app
  // is never empty). Opt out only with --no-demos or include_demos:false.
  const noDemos = process.argv.includes('--no-demos') || configDisablesDemos();
  const withDemos = !noDemos;

  if (!fs.existsSync(path.join(repo, 'skills'))) {
    console.error('[desktop-bundle] 找不到 ../skills —— 必须在 anime-arsenal 仓库内运行');
    process.exit(1);
  }
  fs.mkdirSync(bundle, { recursive: true });

  // 1) skills/ — the core asset. Rebuilt every run (rm + copy → overwrite).
  fs.rmSync(path.join(bundle, 'skills'), { recursive: true, force: true });
  fs.cpSync(path.join(repo, 'skills'), path.join(bundle, 'skills'), { recursive: true, filter });

  // 2) repo-level maintenance tools (shared-cleanup), if present.
  let toolFiles = 0;
  fs.rmSync(path.join(bundle, 'tools'), { recursive: true, force: true });
  const cleanup = path.join(repo, 'tools', 'shared-cleanup');
  if (fs.existsSync(cleanup)) {
    fs.mkdirSync(path.join(bundle, 'tools'), { recursive: true });
    fs.cpSync(cleanup, path.join(bundle, 'tools', 'shared-cleanup'), { recursive: true, filter });
    toolFiles = count(path.join(bundle, 'tools', 'shared-cleanup'));
  }

  // 3) demos — ON BY DEFAULT. Each line's most-complete work, kept under
  //    demos/创作区/<line>/<work>. Rebuilt every run so the champion stays fresh;
  //    opt out (clear) only with --no-demos / include_demos:false.
  const demosDir = path.join(bundle, 'demos');
  let demoPicks = [];
  fs.rmSync(demosDir, { recursive: true, force: true });
  if (withDemos) {
    demoPicks = champions();
    for (const p of demoPicks) {
      const dst = path.join(demosDir, CREATION_ROOT, p.line, p.name);
      fs.mkdirSync(path.dirname(dst), { recursive: true });
      fs.cpSync(path.join(repo, CREATION_ROOT, p.line, p.name), dst, { recursive: true, filter });
    }
  } else {
    console.log('[desktop-bundle] demos 已清空（--no-demos / include_demos:false）');
  }

  // 4) manifest for the desktop app (resolve_repo / seed_demos read this dir).
  const manifest = {
    synced_at: new Date().toISOString(),
    skills: count(path.join(bundle, 'skills')),
    tools: toolFiles,
    demos: demoPicks.map((p) => ({ root: CREATION_ROOT, line: p.line, name: p.name, done: p.done })),
  };
  fs.writeFileSync(path.join(bundle, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');

  const demoLine = withDemos
    ? `+ demos（默认内置各线冠军）: ${demoPicks.map((p) => `${p.line}/${p.name}(✅×${p.done})`).join(', ') || '（无作品）'}`
    : '（demos 已关闭 —— --no-demos / include_demos:false）';
  console.log(`[desktop-bundle] bundled ${manifest.skills} skill files + ${toolFiles} tool files → src-tauri/resources/`);
  console.log(`[desktop-bundle] ${demoLine}`);
}

main();
