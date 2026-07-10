#!/usr/bin/env node
// e2a bundle engine — copy the REAL skills/ (+ repo maintenance tools) and
// 创作区 usage manuals from the repo into desktop-electron/resources/ so they
// ship INSIDE the packaged Electron app (electron-builder extraResources),
// making it self-contained (install on any machine; no anime-armory source
// checkout needed). Demo works are not bundled; this script only writes a
// catalog that points the app to GitHub Release zip assets.
//
// Driven by tools/e2a/scripts/e2a_release.sh; run manually via
// `node tools/e2a/scripts/sync_bundle.cjs [--demo]`. Output dir override:
// E2A_BUNDLE_DIR. Extra auto-picked champion seeds are OFF BY DEFAULT
// (--demo / E2A_INCLUDE_DEMOS=1 / tools/e2a/bundle-demos.json).
//
// Consumption: a packaged app whose live checkout is absent falls back to
// <process.resourcesPath>/resources as its skills repo (resolveRepo in
// desktop-electron/src/main/services/workspace.ts). Demo download buttons use
// demo_catalog.json and pull zip assets from Releases on demand. In dev the
// live checkout always wins for skills.
const fs = require('fs');
const path = require('path');
const {
  copyDirSafe,
  shouldBundlePath,
} = require('../../release-safety/demo_safety.cjs');

const repo = path.resolve(__dirname, '..', '..', '..');
const bundle = process.env.E2A_BUNDLE_DIR
  || path.join(repo, 'desktop-electron', 'resources');
const demoConfigPath = path.join(__dirname, '..', 'bundle-demos.json');
const demoWorksConfigPath = path.join(__dirname, '..', 'demo-works.json');

// the 6 creative lines, by product dir under 创作区 (mirror desktop-electron workspace.ts LINES)
const CREATION_ROOT = '创作区';
const LINES = ['制漫剧', '画漫画', '拍广告', '制MV', '写歌', '写小说'];
const MANUAL_RELS = [
  `${CREATION_ROOT}/使用手册.md`,
  `${CREATION_ROOT}/写小说/使用手册.md`,
  `${CREATION_ROOT}/制漫剧/使用手册.md`,
  `${CREATION_ROOT}/画漫画/使用手册.md`,
  `${CREATION_ROOT}/写歌/使用手册.md`,
  `${CREATION_ROOT}/制MV/使用手册.md`,
  `${CREATION_ROOT}/拍广告/使用手册.md`,
];
const FALLBACK_PINNED_WORKS = ['创作区/制漫剧/那妖魔是姜大人'];
const OUTER_SKILL_LINES = new Map([
  ['n2d', '制漫剧'],
  ['comic', '画漫画'],
  ['ad', '拍广告'],
  ['mv', '制MV'],
  ['song', '写歌'],
  ['novel', '写小说'],
]);
const PRODUCT_LINE_KEYS = new Map([...OUTER_SKILL_LINES.entries()].map(([key, product]) => [product, key]));
const RELEASE_REPO = process.env.E2A_TARGET_REPO
  || process.env.R2A_TARGET_REPO
  || process.env.ANIME_ARMORY_RELEASE_REPO
  || 'anton6202527/anime-armory';
const RELEASE_DOWNLOAD_BASE = `https://github.com/${RELEASE_REPO}/releases/latest/download`;

function parseWorkRel(relWork) {
  const parts = relWork.split('/');
  if (parts.length !== 3 || parts[0] !== CREATION_ROOT || !parts[1] || !parts[2]) {
    return null;
  }
  return { root: parts[0], line: parts[1], name: parts[2] };
}

function normalizeDemoWorkEntry(entry) {
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
  throw new Error(`invalid demo work entry: ${JSON.stringify(entry)}`);
}

function loadPinnedWorks() {
  const rawWorks = fs.existsSync(demoWorksConfigPath)
    ? JSON.parse(fs.readFileSync(demoWorksConfigPath, 'utf8')).works
    : FALLBACK_PINNED_WORKS;
  const known = new Set(LINES);
  if (!Array.isArray(rawWorks) || rawWorks.length === 0) {
    return [];
  }
  const works = [];
  const seen = new Set();
  for (const entry of rawWorks) {
    const rel = normalizeDemoWorkEntry(entry);
    const parsed = parseWorkRel(rel);
    if (!parsed) throw new Error(`invalid demo work path: ${rel}`);
    if (!known.has(parsed.line)) throw new Error(`unknown demo line in work path: ${rel}`);
    const src = path.join(repo, rel);
    if (!workHasProgress(src)) {
      console.warn(`[e2a-bundle] 跳过缺失或无 _进度.md 的配置示例: ${rel}`);
      continue;
    }
    if (!seen.has(rel)) {
      seen.add(rel);
      works.push(rel);
    }
  }
  return works;
}

let PINNED_WORKS;
try {
  PINNED_WORKS = loadPinnedWorks();
} catch (e) {
  console.error(`[e2a-bundle] ${e.message}`);
  process.exit(1);
}
const PINNED_LINES = new Set(PINNED_WORKS.map((rel) => rel.split('/')[1]).filter(Boolean));
const FULL_REFERENCE_LINES = new Set();

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
    ...parseWorkList(process.env.E2A_FEATURED_WORKS),
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
  if (isOuterSkillDemoPath(src)) return false;
  return shouldBundlePath(src, { root: repo });
};

function isOuterSkillDemoPath(src) {
  const rel = path.relative(repo, path.resolve(src)).split(path.sep).join('/');
  const parts = rel.split('/');
  if (parts[0] !== 'skills' || !OUTER_SKILL_LINES.has(parts[1])) return false;
  return ['demo', 'demos', '示例'].includes(parts[2]);
}

const count = (dir) => {
  if (!fs.existsSync(dir)) return 0;
  let n = 0;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.isDirectory()) n += count(path.join(dir, e.name));
    else n += 1;
  }
  return n;
};

function copyManuals(destRoot) {
  let copied = 0;
  for (const rel of MANUAL_RELS) {
    const src = path.join(repo, rel);
    if (!fs.existsSync(src)) {
      console.error(`[e2a-bundle] 缺少创作区使用手册，无法打包: ${rel}`);
      process.exit(1);
    }
    const dst = path.join(destRoot, rel);
    fs.mkdirSync(path.dirname(dst), { recursive: true });
    fs.copyFileSync(src, dst);
    copied += 1;
  }
  return copied;
}

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
    console.warn(`[e2a-bundle] 忽略无效 demo 配置 ${demoConfigPath}: ${e.message}`);
    return false;
  }
}

function envEnablesDemos() {
  const raw = String(process.env.E2A_INCLUDE_DEMOS || process.env.R2A_INCLUDE_DEMOS || '').trim().toLowerCase();
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
  return doneCountAt(path.join(repo, relWork));
}

function doneCountAt(root) {
  const prog = path.join(root, '_进度.md');
  try {
    return (fs.readFileSync(prog, 'utf8').match(/✅/g) || []).length;
  } catch (_e) {
    return null;
  }
}

function workHasProgress(src) {
  return fs.existsSync(path.join(src, '_进度.md'));
}

function explicitWorkRelFromDemoPath(src) {
  const creation = path.join(src, CREATION_ROOT);
  if (!fs.existsSync(creation)) return [];
  const found = [];
  for (const line of fs.readdirSync(creation, { withFileTypes: true })) {
    if (!line.isDirectory()) continue;
    const lineName = line.name;
    if (!LINES.includes(lineName)) continue;
    const lineDir = path.join(creation, lineName);
    for (const work of fs.readdirSync(lineDir, { withFileTypes: true })) {
      if (!work.isDirectory()) continue;
      const workRoot = path.join(lineDir, work.name);
      if (!workHasProgress(workRoot)) continue;
      found.push({
        rel: `${CREATION_ROOT}/${lineName}/${work.name}`,
        src: workRoot,
      });
    }
  }
  return found;
}

function inferSkillDemoWorks(skillName, demoRoot) {
  const line = OUTER_SKILL_LINES.get(skillName);
  if (!line || !fs.existsSync(demoRoot)) return [];

  const explicit = explicitWorkRelFromDemoPath(demoRoot);
  if (explicit.length > 0) return explicit;

  if (workHasProgress(demoRoot)) {
    return [{ rel: `${CREATION_ROOT}/${line}/${path.basename(demoRoot)}`, src: demoRoot }];
  }

  const found = [];
  for (const entry of fs.readdirSync(demoRoot, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    if (!entry.isDirectory() || entry.name.startsWith('.') || entry.name.startsWith('_')) continue;
    const child = path.join(demoRoot, entry.name);
    if (workHasProgress(child)) {
      found.push({ rel: `${CREATION_ROOT}/${line}/${entry.name}`, src: child });
      continue;
    }
    if (LINES.includes(entry.name)) {
      for (const work of fs.readdirSync(child, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
        if (!work.isDirectory() || work.name.startsWith('.') || work.name.startsWith('_')) continue;
        const workRoot = path.join(child, work.name);
        if (workHasProgress(workRoot)) {
          found.push({ rel: `${CREATION_ROOT}/${entry.name}/${work.name}`, src: workRoot });
        }
      }
    }
  }
  return found;
}

function outerSkillDemoWorks() {
  const found = [];
  for (const skillName of OUTER_SKILL_LINES.keys()) {
    for (const demoDirName of ['demo', 'demos', '示例']) {
      const demoRoot = path.join(repo, 'skills', skillName, demoDirName);
      found.push(...inferSkillDemoWorks(skillName, demoRoot));
    }
  }
  return found;
}

function addCatalogEntry(catalog, relWork, label, opts = {}) {
  const src = opts.src || path.join(repo, relWork);
  if (!fs.existsSync(src)) {
    const msg = `[e2a-bundle] 缺失${label}: ${relWork}`;
    if (opts.mandatory) {
      console.error(msg);
      process.exit(1);
    }
    console.warn(`[e2a-bundle] 跳过${msg.replace('[e2a-bundle] ', '')}`);
    return null;
  }
  const parsed = parseWorkRel(relWork);
  if (!parsed) {
    console.warn(`[e2a-bundle] 跳过无效作品路径: ${relWork}`);
    return null;
  }
  if (catalog.has(relWork)) {
    return catalog.get(relWork);
  }
  const lineKey = PRODUCT_LINE_KEYS.get(parsed.line);
  const assetName = lineKey ? `AnimeArmory_demo_${lineKey}.zip` : null;
  const entry = {
    root: parsed.root,
    line: parsed.line,
    line_key: lineKey || null,
    name: parsed.name,
    rel: relWork,
    is_demo: opts.isDemo === true,
    source: opts.source || 'sample',
  };
  if (assetName) {
    entry.asset_name = assetName;
    entry.download_url = `${RELEASE_DOWNLOAD_BASE}/${assetName}`;
  }
  const done = opts.src ? doneCountAt(opts.src) : doneCount(relWork);
  if (done !== null) entry.done = done;
  if (opts.pinned) entry.pinned = true;
  catalog.set(relWork, entry);
  return entry;
}

function copyDemoWork(relWork, sourceLabel) {
  const src = path.join(repo, relWork);
  copyDemoWorkFrom(src, relWork, sourceLabel);
}

function copyDemoWorkFrom(src, relWork, sourceLabel) {
  const dst = path.join(bundle, 'demos', relWork);
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  copyDirSafe(src, dst);
  console.log(`[e2a-bundle] bundled full ${sourceLabel}: ${relWork}`);
}

function main() {
  const withDemos = wantsChampionDemos();

  if (!fs.existsSync(path.join(repo, 'skills'))) {
    console.error('[e2a-bundle] 找不到 skills/ —— 必须在 anime-armory 仓库内运行');
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

  // 3) 创作区 usage manuals. These are docs only, not demo payloads.
  fs.rmSync(path.join(bundle, CREATION_ROOT), { recursive: true, force: true });
  const manualFiles = copyManuals(bundle);

  // 4) sample works. Only metadata is bundled. Full demos live in GitHub
  //    Release assets and are downloaded into the workspace when the user asks.
  const demosDir = path.join(bundle, 'demos');
  const seedDir = path.join(bundle, 'seed');
  const catalog = new Map();
  let demoPicks = [];
  const requiredWorks = [];
  const skillDemoWorks = outerSkillDemoWorks();
  const seedReferences = [];
  if (withDemos) {
    demoPicks = champions().filter((p) => !PINNED_LINES.has(p.line));
  }
  fs.rmSync(demosDir, { recursive: true, force: true });
  fs.rmSync(seedDir, { recursive: true, force: true });
  for (const work of REQUIRED_WORKS) {
    const entry = addCatalogEntry(catalog, work.rel, work.pinned ? '配置作品' : '指定作品', {
      mandatory: false,
      isDemo: true,
      source: work.pinned ? 'configured-demo' : 'featured-demo',
      pinned: work.pinned,
    });
    if (entry) {
      requiredWorks.push(entry);
    }
  }
  for (const work of skillDemoWorks) {
    if (catalog.has(work.rel)) continue;
    const entry = addCatalogEntry(catalog, work.rel, `outer skill demo ${work.rel}`, {
      isDemo: true,
      source: 'outer-skill-demo',
      src: work.src,
    });
    if (entry) {
      const done = doneCountAt(work.src);
      if (done !== null) entry.done = done;
    }
  }
  if (withDemos) {
    for (const p of demoPicks) {
      const rel = `${CREATION_ROOT}/${p.line}/${p.name}`;
      const entry = addCatalogEntry(catalog, rel, `demo ${p.line}/${p.name}`, {
        isDemo: true,
        source: 'line-champion-demo',
      });
      if (entry) {
        // Catalog-only; release packaging owns the full zip payload.
      }
    }
    for (const line of FULL_REFERENCE_LINES) {
      for (const work of lineWorks(line)) {
        if (catalog.has(work.rel)) continue;
        const entry = addCatalogEntry(catalog, work.rel, `reference ${work.line}/${work.name}`, {
          isDemo: false,
          source: 'line-reference',
        });
        if (entry) seedReferences.push(entry);
      }
    }
  } else {
    console.log('[e2a-bundle] 额外 demo 种子未启用（默认只带配置示例种子；加 --demo / E2A_INCLUDE_DEMOS=1 启用其它线冠军种子）');
  }
  const demoCatalog = [...catalog.values()].sort((a, b) => a.rel.localeCompare(b.rel));
  fs.writeFileSync(path.join(bundle, 'demo_catalog.json'), JSON.stringify(demoCatalog, null, 2) + '\n');

  // 5) manifest for the desktop app. scan_workspace only uses demo_catalog.json
  //    to tag real on-disk works as demos when origins metadata is absent.
  const manifest = {
    synced_at: new Date().toISOString(),
    skills: count(path.join(bundle, 'skills')),
    tools: toolFiles,
    manuals: {
      root: CREATION_ROOT,
      files: manualFiles,
    },
    featured_work: requiredWorks[0] || null,
    featured_works: requiredWorks,
    demos: demoPicks.map((p) => ({ root: CREATION_ROOT, line: p.line, name: p.name, done: p.done })),
    seed_works: seedReferences.map((w) => ({ root: CREATION_ROOT, line: w.line, name: w.name, rel: w.rel })),
    demo_catalog: {
      entries: demoCatalog.length,
      mode: 'release-download',
      release_repo: RELEASE_REPO,
    },
    demo_safety: {
      enabled: true,
      path_filter: 'tools/release-safety/demo_safety.cjs',
    },
  };
  fs.writeFileSync(path.join(bundle, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');

  const featuredLine = `配置示例种子: ${requiredWorks.map((w) => w.rel).join(', ') || '（无）'}`;
  const skillDemoLine = `+ 外层 skill demo catalog: ${skillDemoWorks.map((w) => w.rel).join(', ') || '（无）'}`;
  const demoLine = withDemos
    ? `+ 额外 demo 种子: ${demoPicks.map((p) => `${p.line}/${p.name}(✅×${p.done})`).join(', ') || '（无作品）'}`
    : '+ 额外 demo 种子: 关闭';
  const seedLine = withDemos
    ? `+ 非 demo 作品引用: ${seedReferences.map((w) => `${w.line}/${w.name}`).join(', ') || '（无）'}`
    : '+ 非 demo 作品引用: 关闭';
  console.log(`[e2a-bundle] bundled ${manifest.skills} skill files + ${toolFiles} tool files + ${manualFiles} manuals → ${path.relative(repo, bundle) || bundle}/`);
  console.log(`[e2a-bundle] demo catalog entries: ${demoCatalog.length} → ${path.relative(repo, bundle) || bundle}/demo_catalog.json`);
  console.log(`[e2a-bundle] full demo payloads are release assets, not app resources: ${RELEASE_DOWNLOAD_BASE}/AnimeArmory_demo_<line>.zip`);
  console.log(`[e2a-bundle] ${featuredLine}`);
  console.log(`[e2a-bundle] ${skillDemoLine}`);
  console.log(`[e2a-bundle] ${demoLine}`);
  console.log(`[e2a-bundle] ${seedLine}`);
}

main();
