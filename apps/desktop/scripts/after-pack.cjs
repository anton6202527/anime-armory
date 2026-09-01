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

  // Electron's main Mach-O arrives with a linker-generated ad-hoc signature.
  // When no Developer ID is installed electron-builder skips bundle signing,
  // leaving that executable signature without an app-level CodeResources seal.
  // Gatekeeper then reports: "code has no resources but signature indicates
  // they must be present". Seal the complete bundle ad-hoc here. If a real
  // signing identity is configured, electron-builder signs again after this
  // hook and replaces the ad-hoc signature with the Developer ID signature.
  const signResult = spawnSync(
    'codesign',
    ['--force', '--deep', '--sign', '-', '--timestamp=none', appPath],
    { encoding: 'utf8', timeout: 120000 },
  );
  if (signResult.status !== 0) {
    const detail = [signResult.stdout, signResult.stderr, signResult.error?.message]
      .filter(Boolean)
      .join('\n')
      .trim();
    throw new Error(`Ad-hoc bundle signing failed${detail ? `:\n${detail}` : ''}`);
  }

  const verifyResult = spawnSync(
    'codesign',
    ['--verify', '--deep', '--strict', '--verbose=2', appPath],
    { encoding: 'utf8', timeout: 120000 },
  );
  if (verifyResult.status !== 0) {
    const detail = [verifyResult.stdout, verifyResult.stderr, verifyResult.error?.message]
      .filter(Boolean)
      .join('\n')
      .trim();
    throw new Error(`Ad-hoc bundle verification failed${detail ? `:\n${detail}` : ''}`);
  }
  console.log('[after-pack] macOS app bundle ad-hoc signature verified');
};
