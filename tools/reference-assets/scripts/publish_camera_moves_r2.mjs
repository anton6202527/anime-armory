#!/usr/bin/env node
import crypto from 'node:crypto'
import fs from 'node:fs'
import fsp from 'node:fs/promises'
import path from 'node:path'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..')
const DEFAULT_CONFIG = path.join(ROOT, 'infrastructure', 'r2', 'reference-assets.json')
const DEFAULT_OUTPUT = path.join(ROOT, 'dist', 'r2-reference-assets')

function usage() {
  console.log(`Usage: node tools/reference-assets/scripts/publish_camera_moves_r2.mjs [options]

Build and optionally publish immutable camera-movement reference assets.

Options:
  --source <dir>          Directory containing the 23 animated WebPs (required)
  --config <path>         R2 config (default: infrastructure/r2/reference-assets.json)
  --output <path>         Build output (default: dist/r2-reference-assets)
  --write-manifests       Add remote integrity metadata to every line manifest
  --publish               Upload objects and publish the catalog last
  --help                  Show this help
`)
}

function parseArgs(argv) {
  const result = { publish: false, writeManifests: false }
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index]
    if (arg === '--publish') result.publish = true
    else if (arg === '--write-manifests') result.writeManifests = true
    else if (arg === '--help' || arg === '-h') result.help = true
    else if (['--source', '--config', '--output'].includes(arg)) {
      const value = argv[++index]
      if (!value) throw new Error(`${arg} requires a value`)
      result[arg.slice(2)] = value
    } else {
      throw new Error(`Unknown argument: ${arg}`)
    }
  }
  return result
}

function normalizePublicBase(value) {
  const parsed = new URL(String(value ?? '').trim())
  if (parsed.protocol !== 'https:') throw new Error('public_base_url must use HTTPS')
  parsed.pathname = parsed.pathname.replace(/\/+$/, '')
  parsed.search = ''
  parsed.hash = ''
  return parsed.toString().replace(/\/$/, '')
}

function publicObjectUrl(base, objectKey) {
  const safeKey = objectKey.split('/').map((segment) => encodeURIComponent(segment)).join('/')
  return `${normalizePublicBase(base)}/${safeKey}`
}

async function sha256File(file) {
  const hash = crypto.createHash('sha256')
  for await (const chunk of fs.createReadStream(file)) hash.update(chunk)
  return hash.digest('hex')
}

async function readConfig(file) {
  const config = JSON.parse(await fsp.readFile(file, 'utf8'))
  if (config?.schema_version !== 1) throw new Error('reference asset config schema_version must be 1')
  if (!/^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$/.test(String(config.bucket ?? ''))) {
    throw new Error('reference asset bucket name is invalid')
  }
  if (!Array.isArray(config.manifest_paths) || config.manifest_paths.length !== 4) {
    throw new Error('reference asset config must declare the four line manifests')
  }
  if (config.rights?.status !== 'authorized_public_redistribution' || !config.rights?.confirmed_at) {
    throw new Error('public redistribution rights are not confirmed in reference asset config')
  }
  for (const field of ['catalog_key', 'asset_prefix']) {
    const value = String(config[field] ?? '')
    if (!value || value.startsWith('/') || value.includes('..')) throw new Error(`${field} is invalid`)
  }
  return { ...config, public_base_url: normalizePublicBase(config.public_base_url) }
}

async function run(command, args, options = {}) {
  await new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: 'inherit', ...options })
    child.once('error', reject)
    child.once('exit', (code, signal) => {
      if (code === 0) resolve()
      else reject(new Error(`${command} failed${signal ? ` with signal ${signal}` : ` with exit code ${code}`}`))
    })
  })
}

async function wranglerPut({ file, bucket, key, contentType, cacheControl }) {
  await run('npx', [
    'wrangler', 'r2', 'object', 'put', `${bucket}/${key}`,
    '--remote', '--file', file,
    '--content-type', contentType,
    '--cache-control', cacheControl,
  ], { cwd: ROOT })
}

async function loadManifests(config) {
  const records = []
  for (const relativePath of config.manifest_paths) {
    const file = path.resolve(ROOT, relativePath)
    const manifest = JSON.parse(await fsp.readFile(file, 'utf8'))
    if (!Array.isArray(manifest.moves)) throw new Error(`moves missing in ${relativePath}`)
    records.push({ relativePath, file, manifest })
  }
  return records
}

function mediaFilename(move) {
  const value = String(move?.media?.webp ?? move?.media?.remote?.filename ?? '').trim()
  return value ? path.basename(value) : ''
}

function moveIndex(manifest) {
  const result = new Map()
  for (const move of manifest.moves) {
    const filename = mediaFilename(move)
    if (!filename) continue
    if (result.has(filename)) throw new Error(`duplicate media filename in manifest: ${filename}`)
    result.set(filename, move)
  }
  return result
}

async function buildAssets({ source, config, manifests }) {
  const filenames = (await fsp.readdir(source, { withFileTypes: true }))
    .filter((entry) => entry.isFile() && entry.name.toLowerCase().endsWith('.webp'))
    .map((entry) => entry.name)
    .sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'))
  if (filenames.length !== 23) throw new Error(`expected 23 camera WebPs, found ${filenames.length} in ${source}`)

  const canonical = moveIndex(manifests[0].manifest)
  if (canonical.size !== filenames.length) throw new Error('canonical manifest media count does not match source WebPs')
  for (const record of manifests.slice(1)) {
    const current = moveIndex(record.manifest)
    if (current.size !== canonical.size || [...canonical.keys()].some((name) => !current.has(name))) {
      throw new Error(`camera media set drifted in ${record.relativePath}`)
    }
  }

  const assets = []
  for (const filename of filenames) {
    const file = path.join(source, filename)
    const sha256 = await sha256File(file)
    const size = (await fsp.stat(file)).size
    const objectKey = `${config.asset_prefix}/${sha256}.webp`
    const move = canonical.get(filename)
    if (!move) throw new Error(`source file is not declared in manifest: ${filename}`)
    assets.push({
      id: move.id,
      name_zh: move.name_zh,
      filename,
      file,
      sha256,
      bytes: size,
      content_type: 'image/webp',
      object_key: objectKey,
      download_url: publicObjectUrl(config.public_base_url, objectKey),
    })
  }
  return assets
}

async function updateManifests({ manifests, assets, config }) {
  const byFilename = new Map(assets.map((asset) => [asset.filename, asset]))
  const today = new Date().toISOString().slice(0, 10)
  for (const record of manifests) {
    record.manifest.schema_version = 2
    record.manifest.updated_at = today
    record.manifest.source_summary = '23 个已授权公开再分发的 animated WebP 使用内容寻址 R2 按需下载；本地保留首帧与五帧 contact sheet。另有 10 个高价值镜头控制项暂无视觉动画。'
    record.manifest.media_policy = {
      mode: 'local_contact_sheet_remote_animation',
      download: 'on_demand',
      cache_scope: 'user_cache_outside_repo',
      offline_fallback: 'structured_manifest_and_local_contact_sheet',
      integrity: 'bytes_and_sha256_required',
      catalog_url: publicObjectUrl(config.public_base_url, config.catalog_key),
      rights: config.rights,
    }
    for (const move of record.manifest.moves) {
      const filename = mediaFilename(move)
      if (!filename) continue
      const asset = byFilename.get(filename)
      if (!asset) throw new Error(`catalog asset missing for ${filename}`)
      const contactPath = path.join(path.dirname(record.file), '_contact', `${path.parse(filename).name}.jpg`)
      const preview = String(move.media?.preview ?? '').trim()
      const source = String(move.media?.source ?? 'user_provided').trim()
      const media = {
        preview,
        contact_sheet: `_contact/${path.parse(filename).name}.jpg`,
        source,
        remote: {
          filename,
          url: asset.download_url,
          object_key: asset.object_key,
          sha256: asset.sha256,
          bytes: asset.bytes,
          content_type: asset.content_type,
        },
      }
      if (await fsp.stat(contactPath).then(() => true).catch(() => false)) {
        media.contact_sheet_sha256 = await sha256File(contactPath)
        media.contact_sheet_bytes = (await fsp.stat(contactPath)).size
      } else {
        throw new Error(`contact sheet missing: ${path.relative(ROOT, contactPath)}`)
      }
      move.media = media
    }
    await fsp.writeFile(record.file, `${JSON.stringify(record.manifest, null, 2)}\n`)
    console.log(`[camera-r2] updated ${record.relativePath}`)
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2))
  if (args.help) return usage()
  if (!args.source) throw new Error('--source is required')
  const source = path.resolve(args.source)
  const configFile = path.resolve(args.config ?? DEFAULT_CONFIG)
  const output = path.resolve(args.output ?? DEFAULT_OUTPUT)
  const config = await readConfig(configFile)
  const manifests = await loadManifests(config)
  const assets = await buildAssets({ source, config, manifests })
  const catalog = {
    schema_version: 1,
    kind: 'anime_armory_camera_move_assets',
    published_at: new Date().toISOString(),
    rights: config.rights,
    assets: assets.map(({ file, ...asset }) => asset),
  }

  await fsp.mkdir(output, { recursive: true })
  const catalogFile = path.join(output, 'camera-moves-catalog.json')
  await fsp.writeFile(catalogFile, `${JSON.stringify(catalog, null, 2)}\n`)
  if (args.writeManifests) await updateManifests({ manifests, assets, config })

  if (args.publish) {
    for (const asset of assets) {
      console.log(`[camera-r2] publishing ${asset.filename} -> r2://${config.bucket}/${asset.object_key}`)
      await wranglerPut({
        file: asset.file,
        bucket: config.bucket,
        key: asset.object_key,
        contentType: asset.content_type,
        cacheControl: 'public, max-age=31536000, immutable',
      })
    }
    console.log(`[camera-r2] publishing catalog last -> r2://${config.bucket}/${config.catalog_key}`)
    await wranglerPut({
      file: catalogFile,
      bucket: config.bucket,
      key: config.catalog_key,
      contentType: 'application/json; charset=utf-8',
      cacheControl: 'public, max-age=300, must-revalidate',
    })
  }

  console.log(`[camera-r2] ${assets.length} immutable object(s) prepared`)
  console.log(`[camera-r2] catalog: ${catalogFile}`)
  if (!args.publish) console.log('[camera-r2] build only; add --publish to upload to R2')
}

main().catch((error) => {
  console.error(`[camera-r2] ${error.stack || error.message || String(error)}`)
  process.exitCode = 1
})
