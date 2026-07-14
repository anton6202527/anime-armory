import { app, BrowserWindow } from 'electron'
import { readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptsDir = path.dirname(fileURLToPath(import.meta.url))
const projectDir = path.dirname(scriptsDir)
const source = path.join(projectDir, 'assets', 'app-icon', 'icon.svg')
const output = path.join(projectDir, 'assets', 'app-icon', 'icon.png')

app.whenReady().then(async () => {
  const window = new BrowserWindow({
    width: 1024,
    height: 1024,
    show: false,
    frame: false,
    transparent: true,
    backgroundColor: '#00000000',
    webPreferences: { offscreen: true },
  })

  window.setContentSize(1024, 1024)
  const svg = await readFile(source, 'utf8')
  const html = `<!doctype html><style>html,body{margin:0;width:100%;height:100%;overflow:hidden;background:transparent}svg{display:block;width:100%;height:100%}</style>${svg}`
  await window.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`)
  const image = await window.webContents.capturePage({ x: 0, y: 0, width: 1024, height: 1024 })
  await writeFile(output, image.toPNG())
  window.destroy()
  app.exit(0)
}).catch((error) => {
  console.error(error)
  app.exit(1)
})
