import { app, Menu, shell, type BrowserWindow, type MenuItemConstructorOptions } from 'electron'

export type AppLanguage = 'zh' | 'en'

const M = {
  zh: {
    downloadLatest: '下载最新 App',
    switchWorkspace: '切换工作区…',
    newTerminal: '新建终端',
    showTerminal: '显示终端面板',
    hideTerminal: '隐藏终端面板',
    recentWorks: '历史打开项目',
    noRecentWorks: '暂无历史项目',
    language: '语言',
    terminal: '终端',
  },
  en: {
    downloadLatest: 'Download Latest App',
    switchWorkspace: 'Switch Workspace…',
    newTerminal: 'New Terminal',
    showTerminal: 'Show Terminal Panel',
    hideTerminal: 'Hide Terminal Panel',
    recentWorks: 'Recent Projects',
    noRecentWorks: 'No Recent Projects',
    language: 'language',
    terminal: 'Terminal',
  },
}

/** Language + terminal-visible state that drives the native menu labels. */
export class AppUiState {
  language: AppLanguage = 'zh'
  terminalVisible = true
  private recentWorks: Array<{ path: string; name: string }> = []
  private win: BrowserWindow | null = null

  attach(win: BrowserWindow) {
    this.win = win
    this.rebuildMenu()
  }

  private send(channel: string, payload?: unknown) {
    if (this.win && !this.win.isDestroyed()) this.win.webContents.send(channel, payload)
  }

  setLanguage(lang: AppLanguage) {
    this.language = lang
    this.rebuildMenu()
  }

  setTerminalVisible(visible: boolean) {
    this.terminalVisible = visible
    this.rebuildMenu()
  }

  setRecentWorks(works: Array<{ path: string; name: string }>) {
    const seen = new Set<string>()
    this.recentWorks = works
      .filter((work) => {
        if (!work.path || !work.name || seen.has(work.path)) return false
        seen.add(work.path)
        return true
      })
      .slice(0, 4)
    this.rebuildMenu()
  }

  rebuildMenu() {
    const t = M[this.language]
    const isMac = process.platform === 'darwin'
    const template: MenuItemConstructorOptions[] = []

    if (isMac) {
      template.push({
        label: app.name,
        submenu: [
          { role: 'about' },
          { type: 'separator' },
          {
            label: t.language,
            submenu: (['zh', 'en'] as AppLanguage[]).map((lang) => ({
              label: lang === 'zh' ? '中文' : 'English',
              type: 'checkbox',
              checked: this.language === lang,
              click: () => {
                this.setLanguage(lang)
                this.send('app:set-language', lang)
              },
            })),
          },
          {
            label: t.downloadLatest,
            click: () => shell.openExternal('https://github.com/anton6202527/anime-armory/releases'),
          },
          { type: 'separator' },
          { role: 'services' },
          { type: 'separator' },
          { role: 'hide' },
          { role: 'hideOthers' },
          { role: 'unhide' },
          { type: 'separator' },
          { role: 'quit' },
        ],
      })
    }

    template.push(
      {
        label: 'File',
        submenu: [
          {
            label: t.switchWorkspace,
            accelerator: 'CmdOrCtrl+O',
            click: () => this.send('app:switch-workspace'),
          },
          {
            label: t.recentWorks,
            submenu: this.recentWorks.length
              ? this.recentWorks.map((work) => ({
                  label: work.name,
                  click: () => this.send('app:open-recent-work', work.path),
                }))
              : [{ label: t.noRecentWorks, enabled: false }],
          },
          { type: 'separator' },
          isMac ? { role: 'close' } : { role: 'quit' },
        ],
      },
      { label: 'Edit', role: 'editMenu' },
      {
        label: 'View',
        submenu: [
          { role: 'togglefullscreen' },
          { role: 'resetZoom' },
          { role: 'zoomIn' },
          { role: 'zoomOut' },
          { type: 'separator' },
          { role: 'toggleDevTools' },
        ],
      },
      {
        label: t.terminal,
        submenu: [
          {
            label: t.newTerminal,
            accelerator: 'CmdOrCtrl+Shift+T',
            click: () => {
              this.setTerminalVisible(true)
              this.send('app:new-terminal')
              this.send('app:toggle-terminal', true)
            },
          },
          {
            label: this.terminalVisible ? t.hideTerminal : t.showTerminal,
            accelerator: 'CmdOrCtrl+J',
            click: () => {
              this.setTerminalVisible(!this.terminalVisible)
              this.send('app:toggle-terminal', this.terminalVisible)
            },
          },
        ],
      },
      { label: 'Window', role: 'windowMenu' },
      {
        label: 'Help',
        role: 'help',
        submenu: [
          {
            label: 'GitHub',
            click: () => shell.openExternal('https://github.com/anton6202527/anime-armory'),
          },
        ],
      },
    )

    Menu.setApplicationMenu(Menu.buildFromTemplate(template))
  }
}
