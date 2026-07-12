const crypto = require('node:crypto');

const CREATION_ROOT = '创作区';
const LINE_KEY_BY_NAME = new Map([
  ['写小说', 'novel'],
  ['制漫剧', 'n2d'],
  ['画漫画', 'comic'],
  ['写歌', 'song'],
  ['制MV', 'mv'],
  ['拍广告', 'ad'],
]);
const LINE_NAME_BY_KEY = new Map([...LINE_KEY_BY_NAME].map(([name, key]) => [key, name]));

function parseWorkRel(rel) {
  const value = String(rel || '').split('\\').join('/');
  const parts = value.split('/');
  if (
    parts.length !== 3
    || parts[0] !== CREATION_ROOT
    || !LINE_KEY_BY_NAME.has(parts[1])
    || !parts[2]
    || parts.some((part) => part === '.' || part === '..' || /[\0\r\n\t]/.test(part))
  ) {
    throw new Error(`Invalid demo work path: ${rel}`);
  }
  return {
    root: parts[0],
    line: parts[1],
    lineKey: LINE_KEY_BY_NAME.get(parts[1]),
    name: parts[2],
    rel: parts.join('/'),
  };
}

function demoAssetName(rel) {
  const work = parseWorkRel(rel);
  const hash = crypto.createHash('sha256').update(work.rel).digest('hex').slice(0, 8);
  // GitHub Release rewrites non-ASCII asset-name characters (for example,
  // Chinese work names) to dots. Keep the remote identity ASCII-only; the
  // catalog still carries the full human-readable line/work names.
  return `AnimeArmory_demo_${work.lineKey}_${hash}.zip`;
}

function releaseDownloadUrl(repo, tag, assetName) {
  const release = tag
    ? `releases/download/${encodeURIComponent(tag)}`
    : 'releases/latest/download';
  return `https://github.com/${repo}/${release}/${encodeURIComponent(assetName)}`;
}

module.exports = {
  CREATION_ROOT,
  LINE_KEY_BY_NAME,
  LINE_NAME_BY_KEY,
  demoAssetName,
  parseWorkRel,
  releaseDownloadUrl,
};
