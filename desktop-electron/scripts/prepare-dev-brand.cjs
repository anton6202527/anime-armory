const { existsSync, utimesSync } = require('node:fs')
const path = require('node:path')
const { execFileSync } = require('node:child_process')

if (process.platform === 'darwin') {
  const plist = path.join(
    __dirname,
    '..',
    'node_modules',
    'electron',
    'dist',
    'Electron.app',
    'Contents',
    'Info.plist',
  )

  if (existsSync(plist)) {
    for (const key of ['CFBundleDisplayName', 'CFBundleName']) {
      execFileSync('/usr/bin/plutil', ['-replace', key, '-string', 'AnimeArmory', plist])
    }
    const now = new Date()
    utimesSync(plist, now, now)
  }
}
