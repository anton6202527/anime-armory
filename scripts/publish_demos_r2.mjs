#!/usr/bin/env node
import {
  AbortMultipartUploadCommand,
  CompleteMultipartUploadCommand,
  CreateMultipartUploadCommand,
  S3Client,
  UploadPartCommand,
} from '@aws-sdk/client-s3'
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import fsp from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'

import {
  catalogEntry,
  demoAssetName,
  demoObjectKey,
  normalizePublicBase,
  parseWorkRel,
  resolveInside,
  sha256File,
  workRel,
} from './demo_assets.mjs'
import { createDemoZip } from './demo_zip.mjs'

const require = createRequire(import.meta.url)
const { copyDirSafe } = require('../tools/release-safety/demo_safety.cjs')
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const DEFAULT_CONFIG = path.join(ROOT, 'infrastructure', 'r2', 'demos.json')
const DEFAULT_FALLBACK_CATALOG = path.join(ROOT, 'infrastructure', 'r2', 'demo-catalog.json')
const DEFAULT_OUTPUT = path.join(ROOT, 'dist', 'r2-demos')
const WRANGLER_UPLOAD_LIMIT = 290 * 1024 * 1024
const MULTIPART_PART_SIZE = 64 * 1024 * 1024

function usage() {
  console.log(`Usage: node scripts/publish_demos_r2.mjs [options]

Build safe Demo ZIP files and an integrity-checked R2 catalog.

Options:
  --publish              Upload immutable ZIP files and publish the catalog last
  --workspace <path>     Product workspace (default: ANIME_ARMORY_WORKSPACE or ~/AnimeArmory)
  --config <path>        Demo config (default: infrastructure/r2/demos.json)
  --output <path>        Local artifact directory (default: dist/r2-demos)
  --only <line|rel>      Build one configured Demo (repeatable)
  --help                 Show this help

Uploads up to 290 MiB use the authenticated Wrangler session. Larger ZIPs use
the R2 S3 multipart API and require R2_ACCOUNT_ID, R2_ACCESS_KEY_ID and
R2_SECRET_ACCESS_KEY in the publisher shell only.`)
}

function parseArgs(argv) {
  const result = { publish: false, only: [] }
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i]
    if (arg === '--publish') result.publish = true
    else if (arg === '--help' || arg === '-h') result.help = true
    else if (['--workspace', '--config', '--output', '--only'].includes(arg)) {
      const value = argv[++i]
      if (!value) throw new Error(`${arg} requires a value`)
      if (arg === '--only') result.only.push(value)
      else result[arg.slice(2)] = value
    } else {
      throw new Error(`Unknown argument: ${arg}`)
    }
  }
  return result
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

async function readConfig(file) {
  const value = JSON.parse(await fsp.readFile(file, 'utf8'))
  if (value?.schema_version !== 1) throw new Error('Demo config schema_version must be 1')
  if (!Array.isArray(value.works) || value.works.length === 0) throw new Error('Demo config has no works')
  if (!/^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$/.test(String(value.bucket ?? ''))) {
    throw new Error('Demo config bucket name is invalid')
  }
  const catalogKey = String(value.catalog_key ?? '')
  if (!catalogKey || catalogKey.startsWith('/') || catalogKey.includes('..')) throw new Error('Demo catalog_key is invalid')
  return {
    ...value,
    public_base_url: normalizePublicBase(value.public_base_url),
    catalog_key: catalogKey,
  }
}

async function keepOnlyDirectories(dir, allowed) {
  let entries = []
  try {
    entries = await fsp.readdir(dir, { withFileTypes: true })
  } catch {
    return
  }
  for (const entry of entries) {
    if (entry.isDirectory() && !allowed.has(entry.name)) {
      await fsp.rm(path.join(dir, entry.name), { recursive: true, force: true })
    }
  }
}

async function applyProfile(workDir, profile) {
  if (!profile) return
  if (profile !== 'first-episode') throw new Error(`Unknown Demo profile: ${profile}`)
  await keepOnlyDirectories(path.join(workDir, '出图'), new Set(['第1集']))
  await keepOnlyDirectories(path.join(workDir, '合成'), new Set(['第1集']))
  const voiceDir = path.join(workDir, '合成', '第1集', '配音')
  const voiceFiles = await fsp.readdir(voiceDir, { withFileTypes: true }).catch(() => [])
  await Promise.all(voiceFiles
    .filter((entry) => entry.isFile() && /^line_.*\.wav$/i.test(entry.name))
    .map((entry) => fsp.rm(path.join(voiceDir, entry.name), { force: true })))
}

async function normalizeTimestamps(root) {
  const fixed = new Date('2020-01-01T00:00:00.000Z')
  async function walk(current) {
    const stat = await fsp.lstat(current)
    if (stat.isSymbolicLink()) return
    if (stat.isDirectory()) {
      for (const entry of await fsp.readdir(current)) await walk(path.join(current, entry))
    }
    await fsp.utimes(current, fixed, fixed)
  }
  await walk(root)
}

function selected(entry, selectors) {
  if (selectors.length === 0) return true
  const work = parseWorkRel(workRel(entry))
  return selectors.some((selector) => selector === work.rel || selector === work.lineKey || selector === work.line)
}

async function buildDemo({ entry, workspace, output }) {
  const rel = workRel(entry)
  const work = parseWorkRel(rel)
  const source = resolveInside(workspace, rel)
  const progressFile = path.join(source, '_进度.md')
  const progressText = await fsp.readFile(progressFile, 'utf8').catch(() => null)
  if (progressText === null) throw new Error(`Demo is missing _进度.md: ${source}`)

  const temp = await fsp.mkdtemp(path.join(os.tmpdir(), `anime-armory-demo-${work.lineKey}-`))
  const stagedWork = path.join(temp, rel)
  const assetName = demoAssetName(rel)
  const asset = path.join(output, assetName)
  try {
    await fsp.mkdir(path.dirname(stagedWork), { recursive: true })
    copyDirSafe(source, stagedWork)
    await applyProfile(stagedWork, entry.profile)
    await normalizeTimestamps(path.join(temp, '创作区'))
    await fsp.rm(asset, { force: true })
    await createDemoZip(path.join(temp, '创作区'), asset, '创作区')
    const stat = await fsp.stat(asset)
    const sha256 = await sha256File(asset)
    const objectKey = demoObjectKey(rel, sha256)
    return {
      file: asset,
      objectKey,
      entry: catalogEntry({
        rel,
        sha256,
        size: stat.size,
        publicBaseUrl: entry.public_base_url,
        objectKey,
        progressText,
      }),
    }
  } finally {
    await fsp.rm(temp, { recursive: true, force: true })
  }
}

function s3Credentials() {
  const accountId = process.env.R2_ACCOUNT_ID?.trim()
  const accessKeyId = process.env.R2_ACCESS_KEY_ID?.trim()
  const secretAccessKey = process.env.R2_SECRET_ACCESS_KEY?.trim()
  if (!accountId || !accessKeyId || !secretAccessKey) return null
  return { accountId, accessKeyId, secretAccessKey }
}

async function multipartUpload({ file, bucket, key, contentType, cacheControl, contentDisposition }) {
  const credentials = s3Credentials()
  if (!credentials) {
    throw new Error(
      `${path.basename(file)} exceeds Wrangler's safe upload size. Set R2_ACCOUNT_ID, `
      + 'R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY in the publisher shell, then retry.',
    )
  }
  const client = new S3Client({
    region: 'auto',
    endpoint: `https://${credentials.accountId}.r2.cloudflarestorage.com`,
    credentials: {
      accessKeyId: credentials.accessKeyId,
      secretAccessKey: credentials.secretAccessKey,
    },
    requestChecksumCalculation: 'WHEN_REQUIRED',
    responseChecksumValidation: 'WHEN_REQUIRED',
  })
  const created = await client.send(new CreateMultipartUploadCommand({
    Bucket: bucket,
    Key: key,
    ContentType: contentType,
    CacheControl: cacheControl,
    ContentDisposition: contentDisposition,
  }))
  if (!created.UploadId) throw new Error('R2 did not return a multipart upload ID')
  try {
    const size = (await fsp.stat(file)).size
    const parts = []
    for (let start = 0, partNumber = 1; start < size; start += MULTIPART_PART_SIZE, partNumber += 1) {
      const end = Math.min(start + MULTIPART_PART_SIZE, size) - 1
      console.log(`[r2-demo] uploading ${path.basename(file)} part ${partNumber}/${Math.ceil(size / MULTIPART_PART_SIZE)}`)
      const result = await client.send(new UploadPartCommand({
        Bucket: bucket,
        Key: key,
        UploadId: created.UploadId,
        PartNumber: partNumber,
        Body: fs.createReadStream(file, { start, end }),
        ContentLength: end - start + 1,
      }))
      if (!result.ETag) throw new Error(`R2 did not return an ETag for part ${partNumber}`)
      parts.push({ ETag: result.ETag, PartNumber: partNumber })
    }
    await client.send(new CompleteMultipartUploadCommand({
      Bucket: bucket,
      Key: key,
      UploadId: created.UploadId,
      MultipartUpload: { Parts: parts },
    }))
  } catch (error) {
    await client.send(new AbortMultipartUploadCommand({
      Bucket: bucket,
      Key: key,
      UploadId: created.UploadId,
    })).catch(() => {})
    throw error
  } finally {
    client.destroy()
  }
}

async function wranglerPut({ file, bucket, key, contentType, cacheControl, contentDisposition }) {
  const args = [
    'wrangler', 'r2', 'object', 'put', `${bucket}/${key}`,
    '--remote', '--file', file,
    '--content-type', contentType,
    '--cache-control', cacheControl,
  ]
  if (contentDisposition) args.push('--content-disposition', contentDisposition)
  await run('npx', args, { cwd: ROOT })
}

async function uploadFile(options) {
  const size = (await fsp.stat(options.file)).size
  if (size > WRANGLER_UPLOAD_LIMIT) await multipartUpload(options)
  else await wranglerPut(options)
}

async function main() {
  const args = parseArgs(process.argv.slice(2))
  if (args.help) {
    usage()
    return
  }
  const configFile = path.resolve(args.config ?? DEFAULT_CONFIG)
  const config = await readConfig(configFile)
  const workspace = path.resolve(args.workspace ?? process.env.ANIME_ARMORY_WORKSPACE ?? path.join(os.homedir(), 'AnimeArmory'))
  const output = path.resolve(args.output ?? DEFAULT_OUTPUT)
  const works = config.works.filter((entry) => selected(entry, args.only))
  if (works.length === 0) throw new Error('No configured Demo matched --only')
  await fsp.rm(output, { recursive: true, force: true })
  await fsp.mkdir(output, { recursive: true })

  const built = []
  for (const raw of works) {
    const entry = { ...raw, public_base_url: config.public_base_url }
    console.log(`[r2-demo] building ${workRel(entry)}`)
    built.push(await buildDemo({ entry, workspace, output }))
  }
  const catalog = {
    schema_version: 1,
    published_at: new Date().toISOString(),
    demos: built.map((item) => item.entry).sort((a, b) => a.rel.localeCompare(b.rel, 'zh-Hans-CN')),
  }
  const catalogFile = path.join(output, 'catalog.json')
  await fsp.writeFile(catalogFile, `${JSON.stringify(catalog, null, 2)}\n`)

  if (args.publish) {
    for (const item of built) {
      console.log(`[r2-demo] publishing ${item.entry.rel} -> r2://${config.bucket}/${item.objectKey}`)
      await uploadFile({
        file: item.file,
        bucket: config.bucket,
        key: item.objectKey,
        contentType: 'application/zip',
        cacheControl: 'public, max-age=31536000, immutable',
        contentDisposition: `attachment; filename="${item.entry.asset_name}"`,
      })
    }
    console.log(`[r2-demo] publishing catalog last -> r2://${config.bucket}/${config.catalog_key}`)
    await wranglerPut({
      file: catalogFile,
      bucket: config.bucket,
      key: config.catalog_key,
      contentType: 'application/json; charset=utf-8',
      cacheControl: 'public, max-age=60, must-revalidate',
    })
    if (configFile === DEFAULT_CONFIG && args.only.length === 0 && works.length === config.works.length) {
      await fsp.copyFile(catalogFile, DEFAULT_FALLBACK_CATALOG)
      console.log(`[r2-demo] synced desktop fallback catalog -> ${DEFAULT_FALLBACK_CATALOG}`)
    }
  }

  console.log(`[r2-demo] ${built.length} Demo(s) built in ${output}`)
  console.log(`[r2-demo] catalog: ${catalogFile}`)
  if (!args.publish) console.log('[r2-demo] build only; add --publish to upload to R2')
}

main().catch((error) => {
  console.error(`[r2-demo] ${error.stack || error.message || String(error)}`)
  process.exitCode = 1
})
