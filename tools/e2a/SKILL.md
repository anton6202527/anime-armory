# e2a

Repository release tool for the Electron desktop installers and VS Code
extension. The safe default builds a local macOS DMG; GitHub Release mutation
only happens with `--up` or `--all`.

Demo ZIP files are deliberately outside this tool. Publish them to Cloudflare
R2 with `npm run demos:publish`.

Use when:

- packaging or releasing the Electron desktop app;
- producing the macOS DMG, Windows installer, or VS Code VSIX;
- asked for "electron 打包 / electron 发版 / e2a".

Run:

```bash
bash tools/e2a/scripts/e2a_release.sh          # macOS DMG, local only
bash tools/e2a/scripts/e2a_release.sh --up     # macOS DMG → GitHub Release
bash tools/e2a/scripts/e2a_release.sh --all    # DMG + Windows EXE + VSIX → GitHub Release
bash tools/e2a/scripts/e2a_release.sh --apps-only --win
bash tools/e2a/scripts/e2a_release.sh --apps-only --win --no-mac
```

Contract:

- e2a never builds or uploads Demo payloads. Legacy Demo flags fail with a
  message directing the maintainer to `npm run demos:publish`.
- The source snapshot excludes git metadata, private agent configuration,
  dependency/build caches, and all product works under `创作区/`. It copies
  only the seven creation manuals needed by the packaged app.
- `scripts/sync_bundle.cjs` stages the skills repository, the supported
  repository maintenance tools, creation manuals, and a last-known R2 catalog
  fallback into `apps/desktop/resources/`. Full Demo payloads are never bundled.
- GitHub Release artifacts are limited to
  `LabuTV_electron_macos_arm64.dmg`,
  `LabuTV_electron_windows.exe`, `anime-armory.vsix`, and
  `SHA256SUMS.txt`.
- `--win` cross-builds an unsigned Windows x64 NSIS installer on macOS.
  `npmRebuild` stays disabled and the packaged node-pty NAPI prebuild is
  validated after packaging.
- Existing releases keep their notes during incremental uploads unless
  `--refresh-notes` is passed. Checksums are merged only for assets that still
  exist remotely.
- Every upload is read back through GitHub metadata and checked for exact
  filename and byte size.
- The default tag is `electron-v<apps/desktop/package.json version>`. Releases
  are not marked latest automatically and README download links are not
  rewritten.
- macOS packages use ad-hoc signing by default. Set `E2A_SIGNING_IDENTITY` and,
  optionally, `E2A_NOTARY_KEYCHAIN_PROFILE` for Developer ID signing and
  notarization. The signed app must pass a launch smoke test before DMG creation.
- Installer files and build output are never committed to git.

Requirements: node/npm/npx, rsync, hdiutil on macOS, unzip for VSIX validation,
and `gh` only when uploading to GitHub Release.
