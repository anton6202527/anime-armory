import { loadEnvFile } from 'node:process'
import { fileURLToPath } from 'node:url'

for (const relativePath of ['../.env.local', '../.env']) {
  try {
    loadEnvFile(fileURLToPath(new URL(relativePath, import.meta.url)))
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error
  }
}
