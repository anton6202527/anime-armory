import { readdir, readFile } from 'node:fs/promises'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const assetsDirectory = fileURLToPath(new URL('../apps/desktop/out/renderer/assets/', import.meta.url))
const entries = await readdir(assetsDirectory, { withFileTypes: true })
const javascriptFiles = entries
  .filter((entry) => entry.isFile() && entry.name.endsWith('.js'))
  .map((entry) => entry.name)

if (javascriptFiles.length === 0) {
  throw new Error('Desktop renderer bundle has no JavaScript assets to inspect')
}

const source = (
  await Promise.all(
    javascriptFiles.map((name) => readFile(join(assetsDirectory, name), 'utf8')),
  )
).join('\n')

const safeDomPurify = /DOMPurify 3\.4\.12|\.version\s*=\s*["']3\.4\.12["']/.test(source)
const vulnerableDomPurify = /DOMPurify 3\.(?:1\.7|2\.7)|\.version\s*=\s*["']3\.(?:1\.7|2\.7)["']/.test(source)

if (!safeDomPurify) {
  throw new Error('Desktop renderer bundle does not contain the approved DOMPurify 3.4.12 runtime')
}
if (vulnerableDomPurify) {
  throw new Error('Desktop renderer bundle still contains Monaco\'s vulnerable DOMPurify runtime')
}

console.log('[verify-renderer] DOMPurify 3.4.12 present; vulnerable Monaco copies absent')
