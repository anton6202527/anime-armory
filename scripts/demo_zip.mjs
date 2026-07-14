import fs from 'node:fs'
import fsp from 'node:fs/promises'
import path from 'node:path'
import { pipeline } from 'node:stream/promises'
import yazl from 'yazl'

const FIXED_MTIME = new Date('2020-01-01T00:00:00.000Z')

function archivePath(value) {
  const normalized = String(value).split(path.sep).join('/')
  if (
    !normalized
    || normalized.startsWith('/')
    || normalized.split('/').some((part) => !part || part === '.' || part === '..')
    || /[\0\r\n]/.test(normalized)
  ) {
    throw new Error(`Unsafe ZIP entry path: ${value}`)
  }
  return normalized
}

async function collectEntries(sourceRoot, archiveRoot) {
  const entries = []

  async function walk(absolute, relative) {
    const stat = await fsp.lstat(absolute)
    if (stat.isSymbolicLink()) throw new Error(`Demo ZIP cannot contain symlinks: ${absolute}`)

    const name = archivePath(relative ? `${archiveRoot}/${relative}` : archiveRoot)
    if (stat.isDirectory()) {
      entries.push({ kind: 'directory', name })
      const children = await fsp.readdir(absolute, { withFileTypes: true })
      children.sort((a, b) => Buffer.compare(Buffer.from(a.name), Buffer.from(b.name)))
      for (const child of children) {
        await walk(path.join(absolute, child.name), relative ? `${relative}/${child.name}` : child.name)
      }
      return
    }
    if (!stat.isFile()) throw new Error(`Demo ZIP only supports files and directories: ${absolute}`)
    entries.push({
      kind: 'file',
      name,
      source: absolute,
      executable: Boolean(stat.mode & 0o111),
    })
  }

  await walk(sourceRoot, '')
  return entries
}

/** Create a deterministic ZIP whose entry names are explicitly encoded as UTF-8. */
export async function createDemoZip(sourceRoot, outputFile, archiveRoot = path.basename(sourceRoot)) {
  const source = path.resolve(sourceRoot)
  const rootName = archivePath(archiveRoot)
  const stat = await fsp.lstat(source)
  if (!stat.isDirectory()) throw new Error(`Demo ZIP source is not a directory: ${source}`)
  const entries = await collectEntries(source, rootName)
  const zip = new yazl.ZipFile()
  const writing = pipeline(zip.outputStream, fs.createWriteStream(outputFile, { flags: 'wx' }))

  try {
    for (const entry of entries) {
      if (entry.kind === 'directory') {
        zip.addEmptyDirectory(entry.name, { mtime: FIXED_MTIME, mode: 0o40755 })
      } else {
        zip.addFile(entry.source, entry.name, {
          mtime: FIXED_MTIME,
          mode: entry.executable ? 0o100755 : 0o100644,
          compress: true,
          compressionLevel: 6,
        })
      }
    }
    zip.end()
    await writing
  } catch (error) {
    zip.outputStream.destroy(error)
    await writing.catch(() => {})
    throw error
  }
}
