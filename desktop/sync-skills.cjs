#!/usr/bin/env node
// desktop-bundle engine (driven by `r2a`) — copy the REAL skills/ (+ repo maintenance tools) from the repo
// into ./src-tauri/resources/ so they ship INSIDE the packaged .app/.dmg, making
// the desktop app self-contained (install on any machine; no anime-armory
// source checkout needed). Demo works are represented as lightweight catalog
// entries only; users download full examples from the Releases page when needed.
//
// Runs automatically before BOTH `tauri dev` and `tauri build` via tauri.conf.json
// (beforeDevCommand / beforeBuildCommand).
// Extra demo references are OFF BY DEFAULT. Enable them with --demo / --demos,
// R2A_INCLUDE_DEMOS=1, or desktop/bundle-demos.json { "include_demos": true }.
// Run manually via `node sync-skills.cjs [--demo]`.
//
// Consumption (wired in src-tauri): a packaged app whose live checkout is absent
// falls back to <resourceDir>/resources as its skills repo (Rust
// `resolve_repo`); demo_catalog.json is merged into workspace scans as
// name-only sample cards. In dev the live checkout always wins.
const fs = require('fs');
const path = require('path');
const {
  shouldBundlePath,
} = require('../tools/release-safety/demo_safety.cjs');

const repo = path.resolve(__dirname, '..');
const bundle = path.join(__dirname, 'src-tauri', 'resources');
const demoConfigPath = path.join(__dirname, 'bundle-demos.json');

// the 6 creative lines, by product dir under 创作区 (mirror src-tauri/src/commands.rs LINES)
const CREATION_ROOT = '创作区';
const LINES = ['制漫剧', '画漫画', '拍广告', '制MV', '写歌', '写小说'];
const PINNED_WORKS = [
  '创作区/制漫剧/那妖魔是姜大人',
];
const PINNED_LINES = new Set(PINNED_WORKS.map((rel) => rel.split('/')[1]).filter(Boolean));
const FULL_REFERENCE_LINES = new Set(['写小说']);
const DEFAULT_DEMO_DOWNLOAD_URL = process.env.R2A_DEMO_DOWNLOAD_URL
  || process.env.ANIME_ARMORY_DEMO_DOWNLOAD_URL
  || 'https://github.com/anton6202527/anime-armory/releases/latest';

function parseWorkList(raw) {
  return String(raw || '')
    .split(/[\n,;]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

const REQUIRED_WORKS = (() => {
  const seen = new Set();
  const works = [];
  for (const rel of [
    ...PINNED_WORKS,
    ...parseWorkList(process.env.R2A_FEATURED_WORKS),
    ...parseWorkList(process.env.R2A_FEATURED_WORK),
  ]) {
    if (seen.has(rel)) continue;
    seen.add(rel);
    works.push({
      rel,
      pinned: PINNED_WORKS.includes(rel),
    });
  }
  return works;
})();

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

function lineWorks(line) {
  const lineDir = path.join(repo, CREATION_ROOT, line);
  if (!fs.existsSync(lineDir)) return [];
  return fs.readdirSync(lineDir, { withFileTypes: true })
    .filter((e) => e.isDirectory() && !e.name.startsWith('.') && !e.name.startsWith('_'))
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((e) => ({
      line,
      name: e.name,
      rel: `${CREATION_ROOT}/${line}/${e.name}`,
    }));
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

function doneCount(relWork) {
  const prog = path.join(repo, relWork, '_进度.md');
  try {
    return (fs.readFileSync(prog, 'utf8').match(/✅/g) || []).length;
  } catch (_e) {
    return null;
  }
}

function parseWorkRel(relWork) {
  const parts = relWork.split('/');
  if (parts.length !== 3 || parts[0] !== CREATION_ROOT || !parts[1] || !parts[2]) {
    return null;
  }
  return { root: parts[0], line: parts[1], name: parts[2] };
}

function addCatalogEntry(catalog, relWork, label, opts = {}) {
  const src = path.join(repo, relWork);
  if (!fs.existsSync(src)) {
    const msg = `[desktop-bundle] 缺失${label}: ${relWork}`;
    if (opts.mandatory) {
      console.error(msg);
      process.exit(1);
    }
    console.warn(`[desktop-bundle] 跳过${msg.replace('[desktop-bundle] ', '')}`);
    return null;
  }
  const parsed = parseWorkRel(relWork);
  if (!parsed) {
    console.warn(`[desktop-bundle] 跳过无效作品路径: ${relWork}`);
    return null;
  }
  if (catalog.has(relWork)) {
    return catalog.get(relWork);
  }
  const entry = {
    root: parsed.root,
    line: parsed.line,
    name: parsed.name,
    rel: relWork,
    is_demo: opts.isDemo === true,
    source: opts.source || 'sample',
    download_url: opts.downloadUrl || DEFAULT_DEMO_DOWNLOAD_URL,
  };
  const done = doneCount(relWork);
  if (done !== null) entry.done = done;
  if (opts.pinned) entry.pinned = true;
  catalog.set(relWork, entry);
  return entry;
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

  // 3) sample work references. Old full-work resource dirs are removed on
  //    every run so they cannot sneak back into the app bundle.
  const demosDir = path.join(bundle, 'demos');
  const seedDir = path.join(bundle, 'seed');
  const catalog = new Map();
  let demoPicks = [];
  const requiredWorks = [];
  const seedReferences = [];
  if (withDemos) {
    demoPicks = champions().filter((p) => !PINNED_LINES.has(p.line));
  }
  fs.rmSync(demosDir, { recursive: true, force: true });
  fs.rmSync(seedDir, { recursive: true, force: true });
  for (const work of REQUIRED_WORKS) {
    const entry = addCatalogEntry(catalog, work.rel, work.pinned ? '固定作品' : '指定作品', {
      mandatory: work.pinned,
      isDemo: true,
      source: work.pinned ? 'pinned-demo' : 'featured-demo',
      pinned: work.pinned,
      downloadUrl: DEFAULT_DEMO_DOWNLOAD_URL,
    });
    if (entry) requiredWorks.push(entry);
  }
  if (withDemos) {
    for (const p of demoPicks) {
      const rel = `${CREATION_ROOT}/${p.line}/${p.name}`;
      addCatalogEntry(catalog, rel, `demo ${p.line}/${p.name}`, {
        isDemo: true,
        source: 'line-champion-demo',
        downloadUrl: DEFAULT_DEMO_DOWNLOAD_URL,
      });
    }
    for (const line of FULL_REFERENCE_LINES) {
      for (const work of lineWorks(line)) {
        if (catalog.has(work.rel)) continue;
        const entry = addCatalogEntry(catalog, work.rel, `reference ${work.line}/${work.name}`, {
          isDemo: false,
          source: 'line-reference',
          downloadUrl: DEFAULT_DEMO_DOWNLOAD_URL,
        });
        if (entry) seedReferences.push(entry);
      }
    }
  } else {
    console.log('[desktop-bundle] 额外 demo 引用未启用（默认只带固定示例引用；加 --demo / R2A_INCLUDE_DEMOS=1 启用其它线冠军引用）');
  }
  const demoCatalog = [...catalog.values()].sort((a, b) => a.rel.localeCompare(b.rel));
  fs.writeFileSync(path.join(bundle, 'demo_catalog.json'), JSON.stringify(demoCatalog, null, 2) + '\n');

  // 4) manifest for the desktop app (resolve_repo reads this dir; scan_workspace
  //    reads demo_catalog.json for name-only sample cards).
  const manifest = {
    synced_at: new Date().toISOString(),
    skills: count(path.join(bundle, 'skills')),
    tools: toolFiles,
    featured_work: requiredWorks[0] || null,
    featured_works: requiredWorks,
    demos: demoPicks.map((p) => ({ root: CREATION_ROOT, line: p.line, name: p.name, done: p.done })),
    seed_works: seedReferences.map((w) => ({ root: CREATION_ROOT, line: w.line, name: w.name, rel: w.rel })),
    demo_catalog: {
      entries: demoCatalog.length,
      download_url: DEFAULT_DEMO_DOWNLOAD_URL,
      mode: 'name-reference',
    },
    demo_safety: {
      enabled: true,
      path_filter: 'tools/release-safety/demo_safety.cjs',
    },
  };
  fs.writeFileSync(path.join(bundle, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');

  const featuredLine = `固定示例引用: ${requiredWorks.map((w) => w.rel).join(', ') || '（无）'}`;
  const demoLine = withDemos
    ? `+ 额外 demo 引用: ${demoPicks.map((p) => `${p.line}/${p.name}(✅×${p.done})`).join(', ') || '（无作品）'}`
    : '+ 额外 demo 引用: 关闭';
  const seedLine = withDemos
    ? `+ 非 demo 作品引用: ${seedReferences.map((w) => `${w.line}/${w.name}`).join(', ') || '（无）'}`
    : '+ 非 demo 作品引用: 关闭';
  console.log(`[desktop-bundle] bundled ${manifest.skills} skill files + ${toolFiles} tool files → src-tauri/resources/`);
  console.log(`[desktop-bundle] demo catalog entries: ${demoCatalog.length} → src-tauri/resources/demo_catalog.json`);
  console.log(`[desktop-bundle] ${featuredLine}`);
  console.log(`[desktop-bundle] ${demoLine}`);
  console.log(`[desktop-bundle] ${seedLine}`);
}

main();
