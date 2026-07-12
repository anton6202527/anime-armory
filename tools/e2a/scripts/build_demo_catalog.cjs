#!/usr/bin/env node
const crypto = require('node:crypto');
const fs = require('node:fs');
const fsp = require('node:fs/promises');
const path = require('node:path');
const {
  demoAssetName,
  parseWorkRel,
  releaseDownloadUrl,
} = require('../demo_assets.cjs');

function usage() {
  console.error('Usage: build_demo_catalog.cjs <repo-root> <owner/repo> <tag> <artifact-dir> <output.json> <work-rel>...');
  process.exit(2);
}

function sha256File(file) {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash('sha256');
    const stream = fs.createReadStream(file);
    stream.on('error', reject);
    stream.on('data', (chunk) => hash.update(chunk));
    stream.on('end', () => resolve(hash.digest('hex')));
  });
}

async function main() {
  const [repoRootRaw, releaseRepo, tag, artifactDirRaw, outputRaw, ...rels] = process.argv.slice(2);
  if (!repoRootRaw || !releaseRepo || !tag || !artifactDirRaw || !outputRaw || rels.length === 0) usage();
  const repoRoot = path.resolve(repoRootRaw);
  const artifactDir = path.resolve(artifactDirRaw);
  const output = path.resolve(outputRaw);
  const catalog = [];
  const seen = new Set();

  for (const relRaw of rels) {
    const work = parseWorkRel(relRaw);
    if (seen.has(work.rel)) continue;
    seen.add(work.rel);
    const progress = path.join(repoRoot, work.rel, '_进度.md');
    if (!fs.existsSync(progress)) throw new Error(`Demo work is missing _进度.md: ${work.rel}`);
    const assetName = demoAssetName(work.rel);
    const asset = path.join(artifactDir, assetName);
    const stat = await fsp.stat(asset);
    if (!stat.isFile() || stat.size <= 0) throw new Error(`Demo asset is missing or empty: ${asset}`);
    const progressText = await fsp.readFile(progress, 'utf8');
    catalog.push({
      root: work.root,
      line: work.line,
      line_key: work.lineKey,
      name: work.name,
      rel: work.rel,
      is_demo: true,
      source: 'release-progress-work',
      asset_name: assetName,
      download_url: releaseDownloadUrl(releaseRepo, tag, assetName),
      sha256: await sha256File(asset),
      size: stat.size,
      done: (progressText.match(/✅/g) || []).length,
    });
  }

  catalog.sort((a, b) => a.rel.localeCompare(b.rel, 'zh-Hans-CN'));
  await fsp.mkdir(path.dirname(output), { recursive: true });
  await fsp.writeFile(output, `${JSON.stringify(catalog, null, 2)}\n`);
  console.log(`[e2a] demo catalog: ${catalog.length} works → ${output}`);
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
