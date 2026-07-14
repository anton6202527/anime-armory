import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import react from '@vitejs/plugin-react'
import { createRequire } from 'node:module'
import { dirname, resolve } from 'node:path'
import type { Plugin } from 'vite'

const require = createRequire(import.meta.url)
const secureDomPurifyModule = resolve(dirname(require.resolve('dompurify')), 'purify.es.mjs')

const secureMonacoDomPurify = {
  name: 'secure-monaco-dompurify',
  enforce: 'pre',
  transform(code) {
    if (
      code.includes('DOMPurify 3.2.7')
      && code.includes("DOMPurify.version = '3.2.7'")
    ) {
      return `export { default } from ${JSON.stringify(secureDomPurifyModule)}`
    }
    return null
  },
} satisfies Plugin

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin({
      exclude: ['@anime-armory/cloud-client', '@anime-armory/contracts'],
    })],
    build: {
      rollupOptions: {
        input: { index: resolve(__dirname, 'src/main/index.ts') },
      },
    },
    resolve: {
      alias: { '@shared': resolve(__dirname, 'src/shared') },
    },
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: {
      rollupOptions: {
        input: { index: resolve(__dirname, 'src/preload/index.ts') },
      },
    },
    resolve: {
      alias: { '@shared': resolve(__dirname, 'src/shared') },
    },
  },
  renderer: {
    plugins: [secureMonacoDomPurify, react()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src/renderer/src'),
        '@shared': resolve(__dirname, 'src/shared'),
      },
    },
    worker: { format: 'es' },
    build: {
      rollupOptions: {
        input: { index: resolve(__dirname, 'src/renderer/index.html') },
        output: {
          manualChunks(id) {
            if (id.includes('monaco-editor')) return 'monaco'
            if (id.includes('@xyflow')) return 'xyflow'
            if (id.includes('@xterm')) return 'xterm'
          },
        },
      },
    },
  },
})
