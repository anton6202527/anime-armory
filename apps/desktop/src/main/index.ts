import { app, BrowserWindow, session, shell } from 'electron'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { AppUiState } from './menu'
import { createServices, registerIpc } from './ipc'

const ui = new AppUiState()
const services = createServices(ui)
const productName = 'AnimeArmory'

// Electron uses its own name and icon while running an unpackaged build.
// Set both explicitly so local development looks like the shipped product.
app.setName(productName)

function developmentIconPath(): string | undefined {
  if (app.isPackaged) return undefined
  const icon = path.join(app.getAppPath(), 'assets', 'app-icon', 'icon.png')
  return existsSync(icon) ? icon : undefined
}

function createWindow(): BrowserWindow {
  const icon = developmentIconPath()
  const smokeDemos = process.env.SMOKE_DEMOS === '1'
  const smokeDemoInstall = smokeDemos && process.env.SMOKE_DEMO_INSTALL === '1'
  // Demo smoke only verifies the public catalog UI. Never let the legacy
  // workspace smoke click a Demo download card in the same run.
  const smokeDrive = !smokeDemos && process.env.SMOKE_DRIVE === '1'
  const win = new BrowserWindow({
    title: productName,
    ...(icon ? { icon } : {}),
    width: 1440,
    height: 920,
    minWidth: 980,
    minHeight: 640,
    show: false,
    backgroundColor: '#1f1f1f',
    ...(process.platform === 'darwin'
      ? { titleBarStyle: 'hiddenInset' as const, trafficLightPosition: { x: 12, y: 9 } }
      : { titleBarStyle: 'hidden' as const, titleBarOverlay: { color: '#181818', symbolColor: '#cccccc', height: 32 } }),
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
             steps.push('smokeDemos=${smokeDemos}')
             steps.push('smokeDrive=${smokeDrive}')
             for (let i = 0; i < 80 && !document.querySelector('.line-card'); i++) await sleep(250)
             steps.push('lineCards=' + document.querySelectorAll('.line-card').length)
             if (${smokeDemos}) {
               // The ad Demo is intentionally tiny, so install smoke can test
               // download + checksum + extraction without pulling a large work.
               const lineCard = document.querySelectorAll('.line-card')[${smokeDemoInstall ? 2 : 0}]
               click(lineCard?.querySelector('.card-actions .primary') || lineCard)
               for (let i = 0; i < 40 && !document.querySelector('.demo-download-card'); i++) await sleep(250)
               steps.push('demoDownloads=' + document.querySelectorAll('.demo-download-card').length)
               steps.push('cloudEntry=' + Boolean(document.querySelector('.statusbar-cloud, .cloud-modal, .cloud-login')))
               if (${smokeDemoInstall}) {
                 click(document.querySelector('.demo-download-card'))
                 for (let i = 0; i < 80 && !document.querySelector('.root-demo-badge'); i++) await sleep(250)
                 steps.push('installedDemo=' + Boolean(document.querySelector('.root-demo-badge')))
               }
             }
             if (${smokeDrive}) {
               // enter the FIRST line (n2d, canvas view) and open its demo work
               const enter = document.querySelectorAll('.line-card .card-actions button')[1]
               click(enter || document.querySelector('.line-card'))
               await sleep(1500)
               steps.push('rootCards=' + document.querySelectorAll('.root-card').length)
               click(document.querySelector('.root-card'))
               await sleep(9000)
               steps.push('op=' + Boolean(document.querySelector('.op')))
               steps.push('rail=' + document.querySelectorAll('.rail-tab').length)
               if (${JSON.stringify(Boolean(process.env.SMOKE_FILES))}) {
                 for (let i = 0; i < 30 && !document.querySelector('.tree-line:not(.dir):not(.tree-limit)'); i++) await sleep(250)
                 const fileRows = Array.from(document.querySelectorAll('.tree-line:not(.dir):not(.tree-limit)') || [])
                 const markdownRow = fileRows.find((row) => /\.md\s*$/.test(row.textContent || ''))
                 click(markdownRow || fileRows[0])
                 await sleep(2500)
                 steps.push('fileBreadcrumb=' + Boolean(document.querySelector('.files-editor-breadcrumb')))
                 steps.push('breadcrumbParts=' + document.querySelectorAll('.files-breadcrumb-item').length)
                 steps.push('symbolParts=' + document.querySelectorAll('.files-breadcrumb-item.symbol').length)
                 click(document.querySelector('.files-breadcrumb-item.symbol') || document.querySelector('.files-breadcrumb-item.current'))
                 await sleep(800)
                 steps.push('pickerRows=' + document.querySelectorAll('.files-breadcrumb-picker-row').length)
               } else {
                 const rails = document.querySelectorAll('.rail-tab')
                 click(rails[3]) // canvas tab on canvas lines
                 await sleep(6000)
                 steps.push('clipNodes=' + document.querySelectorAll('.clip-node').length)
                 steps.push('edges=' + document.querySelectorAll('.react-flow__edge').length)
                 steps.push('epSelect=' + Boolean(document.querySelector('.ep-select')))
               }
             }
             return JSON.stringify({
               steps,
               errs: window.armorySmokeErrors ? window.armorySmokeErrors() : [],
             })
           })()`,
        )
        console.log('[smoke probe]', probe)
        const recheck = await win.webContents.executeJavaScript(
          `JSON.stringify({
             op: Boolean(document.querySelector('.op')),
             demoDownloads: document.querySelectorAll('.demo-download-card').length,
             cloudEntry: Boolean(document.querySelector('.statusbar-cloud, .cloud-modal, .cloud-login')),
             status: (document.querySelector('.statusbar')?.textContent || '').slice(0, 40),
           })`,
        )
        console.log('[smoke recheck]', recheck)
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
    let allowed = false
    try {
      const u = new URL(url)
      allowed = u.protocol === 'file:' || (u.protocol === 'http:' && (u.hostname === 'localhost' || u.hostname === '127.0.0.1'))
    } catch {
      // unparsable URL — deny
    }
    if (!allowed) e.preventDefault()
  })

  services.pty.attach(win.webContents)
  services.watch.attach(win.webContents)
  ui.attach(win)

  // On macOS the app outlives its window (window-all-closed does not quit),
  // so shells and file watchers opened by this window must die with it or
  // every close/reopen cycle leaks processes and watchers.
  win.on('closed', () => {
    services.pty.disposeAll()
    void services.watch.disposeAll()
  })

  if (process.env.ELECTRON_RENDERER_URL) {
    win.loadURL(process.env.ELECTRON_RENDERER_URL)
  } else {
    win.loadFile(path.join(import.meta.dirname, '../renderer/index.html'))
  }
  return win
}

app.whenReady().then(() => {
  const icon = developmentIconPath()
  if (process.platform === 'darwin' && icon) app.dock?.setIcon(icon)

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
