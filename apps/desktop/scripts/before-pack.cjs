#!/usr/bin/env node
const { fixPtyPrebuilds } = require('./fix-pty-prebuilds.cjs');

module.exports = async function beforePack() {
  fixPtyPrebuilds();
};
