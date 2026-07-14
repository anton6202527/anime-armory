#!/usr/bin/env node
// Stage the self-contained skills repository, creation manuals and a last-known
// public R2 Demo catalog for Electron packaging. Demo payloads are never copied
// into the app and are never uploaded by e2a.
const fs = require('node:fs')
const path = require('node:path')
const { shouldBundlePath } = require('../../release-safety/demo_safety.cjs')

const repo = path.resolve(__dirname, '..', '..', '..')
const bundle = process.env.E2A_BUNDLE_DIR || path.join(repo, 'apps', 'desktop', 'resources')
const creationRoot = '创作区'
const manuals = [
  `${creationRoot}/使用手册.md`,
  `${creationRoot}/写小说/使用手册.md`,
  `${creationRoot}/制漫剧/使用手册.md`,
  `${creationRoot}/画漫画/使用手册.md`,
  `${creationRoot}/写歌/使用手册.md`,
  `${creationRoot}/制MV/使用手册.md`,
  `${creationRoot}/拍广告/使用手册.md`,
]
const outerSkillNames = new Set(['n2d', 'comic', 'ad', 'mv', 'song', 'novel'])
const catalogSource = path.join(repo, 'infrastructure', 'r2', 'demo-catalog.json')
const demoConfigSource = path.join(repo, 'infrastructure', 'r2', 'demos.json')

function relative(candidate) {
  return path.relative(repo, path.resolve(candidate)).split(path.sep).join('/')
}

function isOuterDemo(candidate) {
  const parts = relative(candidate).split('/')
  return parts[0] === 'skills'
    && outerSkillNames.has(parts[1])
    && ['demo', 'demos', '示例'].includes(parts[2])
}

function filter(candidate) {
  const name = path.basename(candidate)
  if (name === '.DS_Store' || name.endsWith('.pyc') || name.endsWith('.vsix')) return false
  if (isOuterDemo(candidate)) return false
  return shouldBundlePath(candidate, { root: repo })
}

function countFiles(dir) {
  if (!fs.existsSync(dir)) return 0
  let count = 0
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    count += entry.isDirectory() ? countFiles(path.join(dir, entry.name)) : 1
  }
  return count
}

function copyManuals() {
  for (const rel of manuals) {
    const source = path.join(repo, rel)
    if (!fs.existsSync(source)) throw new Error(`Missing creation manual: ${rel}`)
    const destination = path.join(bundle, rel)
    fs.mkdirSync(path.dirname(destination), { recursive: true })
    fs.copyFileSync(source, destination)
  }
}

function loadCatalog() {
  if (!fs.existsSync(catalogSource)) return { schema_version: 1, published_at: null, demos: [] }
  const catalog = JSON.parse(fs.readFileSync(catalogSource, 'utf8'))
  if (catalog?.schema_version !== 1 || !Array.isArray(catalog.demos)) {
    throw new Error('infrastructure/r2/demo-catalog.json is invalid')
  }
  return catalog
}

function catalogUrl() {
  const config = JSON.parse(fs.readFileSync(demoConfigSource, 'utf8'))
  return `${String(config.public_base_url).replace(/\/+$/, '')}/${String(config.catalog_key).replace(/^\/+/, '')}`
}

function main() {
  if (!fs.existsSync(path.join(repo, 'skills', 'README.md'))) {
    throw new Error('Run this script inside the anime-armory repository')
  }
  fs.mkdirSync(bundle, { recursive: true })

  fs.rmSync(path.join(bundle, 'skills'), { recursive: true, force: true })
  fs.cpSync(path.join(repo, 'skills'), path.join(bundle, 'skills'), { recursive: true, filter })

  fs.rmSync(path.join(bundle, 'tools'), { recursive: true, force: true })
  const cleanup = path.join(repo, 'tools', 'shared-cleanup')
  if (fs.existsSync(cleanup)) {
    fs.mkdirSync(path.join(bundle, 'tools'), { recursive: true })
    fs.cpSync(cleanup, path.join(bundle, 'tools', 'shared-cleanup'), { recursive: true, filter })
  }

  fs.rmSync(path.join(bundle, creationRoot), { recursive: true, force: true })
  copyManuals()

  const catalog = loadCatalog()
  fs.writeFileSync(path.join(bundle, 'demo_catalog.json'), `${JSON.stringify(catalog, null, 2)}\n`)
  const manifest = {
    synced_at: new Date().toISOString(),
    skills: countFiles(path.join(bundle, 'skills')),
    tools: countFiles(path.join(bundle, 'tools')),
    manuals: { root: creationRoot, files: manuals.length },
    demo_catalog: {
      entries: catalog.demos.length,
      mode: 'r2-public-download',
      url: catalogUrl(),
    },
    demo_payloads_bundled: false,
  }
  fs.writeFileSync(path.join(bundle, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`)
  console.log(`[e2a-bundle] bundled ${manifest.skills} skill files + ${manifest.tools} tool files + ${manuals.length} manuals`)
  console.log(`[e2a-bundle] R2 Demo fallback entries: ${catalog.demos.length}; payloads are not bundled`)
}

try {
  main()
} catch (error) {
  console.error(`[e2a-bundle] ${error.message || String(error)}`)
  process.exitCode = 1
}
