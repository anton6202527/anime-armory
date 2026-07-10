import { app, BrowserWindow, session, shell } from 'electron'
import path from 'node:path'
import { AppUiState } from './menu'
import { createServices, registerIpc } from './ipc'

const ui = new AppUiState()
const services = createServices(ui)

function createWindow(): BrowserWindow {
  const win = new BrowserWindow({
    title: 'Creation Armory',
    width: 1440,
    height: 920,
    minWidth: 980,
    minHeight: 640,
    show: false,
    backgroundColor: '#121413',
    ...(process.platform === 'darwin'
      ? { titleBarStyle: 'hiddenInset' as const, trafficLightPosition: { x: 12, y: 9 } }
      : { titleBarStyle: 'hidden' as const, titleBarOverlay: { color: '#191a1c', symbolColor: '#cccccc', height: 32 } }),
    webPreferences: {
      preload: path.join(import.meta.dirname, '../preload/index.mjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false, // preload uses webUtils; renderer stays isolated
      spellcheck: false,
    },
  })

  win.once('ready-to-show', () => win.show())

  // Headless smoke check: SMOKE_SHOT=<path> captures the rendered window.
  if (process.env.SMOKE_SHOT) {
    win.webContents.on('console-message', (_e, level, message, line, sourceId) => {
      console.log(`[renderer:${level}] ${message} (${sourceId}:${line})`)
    })
    win.webContents.once('did-finish-load', () => {
      setTimeout(async () => {
        const probe = await win.webContents.executeJavaScript(
          `(async () => {
             const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
             const click = (el) => el && el.dispatchEvent(new MouseEvent('click', { bubbles: true }))
             const steps = []
             for (let i = 0; i < 40 && !document.querySelector('.line-card'); i++) await sleep(250)
             steps.push('lineCards=' + document.querySelectorAll('.line-card').length)
             if (${JSON.stringify(Boolean(process.env.SMOKE_DRIVE))}) {
               // enter the FIRST line (n2d, canvas view) and open its demo work
               const enter = document.querySelectorAll('.line-card .card-actions button')[1]
               click(enter || document.querySelector('.line-card'))
               await sleep(1500)
               steps.push('rootCards=' + document.querySelectorAll('.root-card').length)
               click(document.querySelector('.root-card'))
               await sleep(9000)
               steps.push('op=' + Boolean(document.querySelector('.op')))
               steps.push('rail=' + document.querySelectorAll('.rail-tab').length)
               const rails = document.querySelectorAll('.rail-tab')
               click(rails[3]) // canvas tab on canvas lines
               await sleep(6000)
               steps.push('clipNodes=' + document.querySelectorAll('.clip-node').length)
               steps.push('edges=' + document.querySelectorAll('.react-flow__edge').length)
               steps.push('epSelect=' + Boolean(document.querySelector('.ep-select')))
             }
             return JSON.stringify({
               steps,
               errs: window.armorySmokeErrors ? window.armorySmokeErrors() : [],
             })
           })()`,
        )
        console.log('[smoke probe]', probe)
        const image = await win.webContents.capturePage()
        const { writeFileSync } = await import('node:fs')
        writeFileSync(process.env.SMOKE_SHOT!, image.toPNG())
        console.log('[smoke] screenshot written')
      }, 8000)
    })
  }

  // All external navigation goes to the system browser.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http:') || url.startsWith('https:')) shell.openExternal(url)
    return { action: 'deny' }
  })
  win.webContents.on('will-navigate', (e, url) => {
    if (!url.startsWith('http://localhost') && !url.startsWith('file:')) e.preventDefault()
  })

  services.pty.attach(win.webContents)
  services.watch.attach(win.webContents)
  ui.attach(win)

  if (process.env.ELECTRON_RENDERER_URL) {
    win.loadURL(process.env.ELECTRON_RENDERER_URL)
  } else {
    win.loadFile(path.join(import.meta.dirname, '../renderer/index.html'))
  }
  return win
}

app.whenReady().then(() => {
  // Deny every permission request (camera/mic/etc.) — this app needs none.
  session.defaultSession.setPermissionRequestHandler((_wc, _permission, cb) => cb(false))

  registerIpc(services)
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', () => {
  services.pty.disposeAll()
  services.media.dispose()
  void services.watch.disposeAll()
})
