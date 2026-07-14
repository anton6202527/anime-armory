#!/usr/bin/env node
const path = require('path');
const { spawnSync } = require('child_process');

module.exports = async function afterPack(context) {
  if (context.electronPlatformName !== 'darwin') return;

  const product = context.packager.appInfo.productFilename;
  const appPath = path.join(context.appOutDir, `${product}.app`);
  const executable = path.join(appPath, 'Contents', 'MacOS', product);
  const modulePath = path.join(
    appPath,
    'Contents',
    'Resources',
    'app.asar',
    'node_modules',
    'node-pty',
  );
  const probe = `
    const pty = require(${JSON.stringify(modulePath)});
    const child = pty.spawn('/bin/zsh', ['-l'], {
      cwd: '/tmp', env: process.env, cols: 40, rows: 10,
    });
    child.kill();
    setTimeout(() => process.exit(0), 30);
  `;
  const result = spawnSync(executable, ['-e', probe], {
    env: { ...process.env, ELECTRON_RUN_AS_NODE: '1' },
    encoding: 'utf8',
    timeout: 10000,
  });
  if (result.status !== 0) {
    const detail = [result.stdout, result.stderr, result.error?.message].filter(Boolean).join('\n').trim();
    throw new Error(`Packaged node-pty smoke test failed${detail ? `:\n${detail}` : ''}`);
  }
  console.log('[after-pack] packaged node-pty PTY spawn passed');
};
