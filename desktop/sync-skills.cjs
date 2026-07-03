#!/usr/bin/env node
// desktop-bundle engine (driven by `r2a`) — copy the REAL skills/ (+ repo maintenance tools) from the repo
// into ./src-tauri/resources/ so they ship INSIDE the packaged .app/.dmg, making
// the desktop app self-contained (install on any machine; no anime-armory
// source checkout needed). It always bundles the current featured work, and
// optionally bundles each creative line's most-complete work with --demo.
//
// Runs automatically before BOTH `tauri dev` and `tauri build` via tauri.conf.json
// (beforeDevCommand / beforeBuildCommand).
// Extra demos are OFF BY DEFAULT. Enable them with --demo / --demos,
// R2A_INCLUDE_DEMOS=1, or desktop/bundle-demos.json { "include_demos": true }.
// Run manually via `node sync-skills.cjs [--demo]`.
//
// Consumption (wired in src-tauri): a packaged app whose live checkout is absent
// falls back to <resourceDir>/resources as its skills repo (Rust
// `resolve_repo`); bundled demos are seeded once into the user's ~/AnimeArmory
// workspace (Rust `seed_demos`). In dev the live checkout always wins.
const fs = require('fs');
const path = require('path');
const {
  copyDirSafe,
  formatReport,
  scanTree,
  shouldBundlePath,
} = require('../tools/release-safety/demo_safety.cjs');

const repo = path.resolve(__dirname, '..');
const bundle = path.join(__dirname, 'src-tauri', 'resources');
const demoConfigPath = path.join(__dirname, 'bundle-demos.json');

// the 5 creative lines, by product dir under 创作区 (mirror src-tauri/src/commands.rs LINES)
const CREATION_ROOT = '创作区';
const LINES = ['制漫剧', '拍广告', '制MV', '写歌', '写小说'];
const FEATURED_WORK = process.env.R2A_FEATURED_WORK || '创作区/制漫剧/那妖魔是姜大人';

const filter = (src) => {
  const b = path.basename(src);
  if (b === '.DS_Store') return false;
  if (b.endsWith('.pyc') || b.endsWith('.vsix')) return false;
  return shouldBundlePath(src, { root: repo });
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

function configEnablesDemos() {
  if (!fs.existsSync(demoConfigPath)) return false;
  try {
    const cfg = JSON.parse(fs.readFileSync(demoConfigPath, 'utf8'));
    return cfg && cfg.include_demos === true;
  } catch (e) {
    console.warn(`[desktop-bundle] 忽略无效 demo 配置 ${demoConfigPath}: ${e.message}`);
    return false;
  }
}

function envEnablesDemos() {
  const raw = String(process.env.R2A_INCLUDE_DEMOS || '').trim().toLowerCase();
  return ['1', 'true', 'yes', 'y', 'on'].includes(raw);
}

function wantsChampionDemos() {
  return process.argv.includes('--demo')
    || process.argv.includes('--demos')
    || process.argv.includes('--with-demos')
    || envEnablesDemos()
    || configEnablesDemos();
}

function copyWorkIntoDemos(demosDir, relWork, label) {
  const src = path.join(repo, relWork);
  if (!fs.existsSync(src)) {
    console.warn(`[desktop-bundle] 跳过缺失${label}: ${relWork}`);
    return null;
  }
  const dst = path.join(demosDir, relWork);
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  const result = copyDirSafe(src, dst);
  if (result.pre.omitted.length > 0) {
    console.warn(formatReport({
      ...result.pre,
      blocked: [],
      omitted: result.pre.omitted,
    }));
  }
  return {
    rel: relWork,
    files: result.post.scannedFiles,
  };
}

function main() {
  const withDemos = wantsChampionDemos();

  if (!fs.existsSync(path.join(repo, 'skills'))) {
    console.error('[desktop-bundle] 找不到 ../skills —— 必须在 anime-armory 仓库内运行');
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

  // 3) seedable works. Rebuilt every run so old bundled demos cannot linger.
  //    The featured work is always included; --demo adds each line champion.
  const demosDir = path.join(bundle, 'demos');
  let demoPicks = [];
  let featured = null;
  fs.rmSync(demosDir, { recursive: true, force: true });
  fs.mkdirSync(demosDir, { recursive: true });
  featured = copyWorkIntoDemos(demosDir, FEATURED_WORK, '指定作品');
  if (withDemos) {
    demoPicks = champions();
    for (const p of demoPicks) {
      copyWorkIntoDemos(demosDir, path.join(CREATION_ROOT, p.line, p.name), `demo ${p.line}/${p.name}`);
    }
  } else {
    console.log('[desktop-bundle] 额外 demo 未启用（默认只带指定作品；加 --demo / R2A_INCLUDE_DEMOS=1 启用各线冠军）');
  }
  const demoReport = scanTree(demosDir, { includeOmitted: false });
  if (demoReport.blocked.length > 0) {
    console.error(formatReport(demoReport));
    process.exit(1);
  }

  // 4) manifest for the desktop app (resolve_repo / seed_demos read this dir).
  const manifest = {
    synced_at: new Date().toISOString(),
    skills: count(path.join(bundle, 'skills')),
    tools: toolFiles,
    featured_work: featured,
    demos: demoPicks.map((p) => ({ root: CREATION_ROOT, line: p.line, name: p.name, done: p.done })),
    demo_safety: {
      enabled: true,
      path_filter: 'tools/release-safety/demo_safety.cjs',
    },
  };
  fs.writeFileSync(path.join(bundle, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');

  const featuredLine = featured ? `指定作品: ${FEATURED_WORK}` : `指定作品缺失: ${FEATURED_WORK}`;
  const demoLine = withDemos
    ? `+ 额外 demos: ${demoPicks.map((p) => `${p.line}/${p.name}(✅×${p.done})`).join(', ') || '（无作品）'}`
    : '+ 额外 demos: 关闭';
  console.log(`[desktop-bundle] bundled ${manifest.skills} skill files + ${toolFiles} tool files → src-tauri/resources/`);
  console.log(`[desktop-bundle] ${featuredLine}`);
  console.log(`[desktop-bundle] ${demoLine}`);
}

main();
