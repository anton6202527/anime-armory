const { existsSync, utimesSync } = require('node:fs')
const path = require('node:path')
const { execFileSync } = require('node:child_process')

if (process.platform === 'darwin') {
  const appDirectory = path.resolve(__dirname, '..')
  const electronDirectory = path.dirname(
    require.resolve('electron/package.json', { paths: [appDirectory] }),
  )
  const plist = path.join(
    electronDirectory,
    'dist',
    'Electron.app',
    'Contents',
    'Info.plist',
  )

  if (existsSync(plist)) {
    for (const key of ['CFBundleDisplayName', 'CFBundleName']) {
      execFileSync('/usr/bin/plutil', ['-replace', key, '-string', 'LabuTV', plist])
    }
    const now = new Date()
    utimesSync(plist, now, now)
  }
}
