#!/usr/bin/env node
// npm strips the exec bit from node-pty's prebuilt spawn-helper, and packaged
// apps run node-pty from prebuilds/ (build/Release is excluded from packages —
// see electron-builder.yml). Without +x, pty.fork dies with "posix_spawnp
// failed" in the packaged app. Restore the bit right after install so
// electron-builder carries it into app.asar.unpacked.
const fs = require('fs');
const path = require('path');

const prebuilds = path.join(__dirname, '..', 'node_modules', 'node-pty', 'prebuilds');
let fixed = 0;
for (const dir of fs.existsSync(prebuilds) ? fs.readdirSync(prebuilds) : []) {
  const helper = path.join(prebuilds, dir, 'spawn-helper');
  if (fs.existsSync(helper)) {
    fs.chmodSync(helper, 0o755);
    fixed += 1;
  }
}
console.log(`[fix-pty-prebuilds] chmod +x spawn-helper in ${fixed} prebuild dir(s)`);
