# e2a

Repo release tool: build the **Electron desktop app** (`desktop-electron/`) or
the per-line **demo zip assets**. The safe default is a local macOS DMG;
uploading is enabled only by `--up`, `--demos`, or `--all`. Successor of the retired Tauri `/r2a`
flow; fully self-contained under `tools/e2a/`:

- `scripts/e2a_release.sh` — snapshot → build → zip → upload orchestrator
- `scripts/select_demo.cjs` — selected demo works (config `demo-works.json`)
- `scripts/sync_bundle.cjs` — bundles skills/tools/manuals + `demo_catalog.json`
  into `desktop-electron/resources/` (electron-builder `extraResources`)
- shared safe payload copier: `tools/release-safety/demo_safety.cjs`

Use when:

- releasing or locally packaging the Electron desktop app
- refreshing the demo zip assets alongside an Electron app release
- asked for "electron 打包 / electron 发版 / e2a"

Run:

```bash
bash tools/e2a/scripts/e2a_release.sh          # DMG only, local; never uploads
bash tools/e2a/scripts/e2a_release.sh --up     # DMG only, then upload
bash tools/e2a/scripts/e2a_release.sh --demos  # demo zips only, then upload
bash tools/e2a/scripts/e2a_release.sh --all    # DMG + Windows exe + VSIX, upload; no demos
bash tools/e2a/scripts/e2a_release.sh --apps-only --win           # local DMG + Windows exe
bash tools/e2a/scripts/e2a_release.sh --apps-only --win --no-mac  # Windows exe only
```

Contract:

- The four primary modes are intentionally distinct: default = local DMG only;
  `--up` = DMG upload; `--demos` = demo zip upload; `--all` = every desktop
  installer (macOS + Windows) plus the VS Code VSIX uploaded without demo zips. Primary modes are
  mutually exclusive. Advanced legacy flags remain available for incremental
  or local packaging.
- Snapshot of the local checkout excludes git metadata, private agent config
  (`.claude/ .codex/ …`, `CLAUDE.md`/`GEMINI.md`), build output
  (`dist/ out/ release/ target/ node_modules/`), and all of `创作区/` except
  `_进度.md` references of the selected demo works plus the creation manuals.
  Full demo payloads never enter the snapshot (keeps the app bundle slim);
  demo zips copy them straight from the checkout via the release-safety
  copier.
- App bundle ships the skills repo + manuals + `demo_catalog.json` via
  electron-builder `extraResources` — the packaged app resolves them at
  `process.resourcesPath/resources`, matching `resolve_repo`/demo download in
  `desktop-electron/src/main/services/{workspace,demos}.ts`. Full demo
  payloads are **not** bundled; the app downloads the zips from Releases.
- n2d demo zip is slimmed to first-episode media (rule inherited from the
  retired `/r2a`). Demo zips are deterministic (fixed timestamps, `zip -X`).
- Artifact names: `AnimeArmory_electron_macos_arm64.dmg`,
  `AnimeArmory_electron_windows.exe` (`--win`),
  `anime-armory.vsix` (`--vscode` or `--all`),
  `AnimeArmory_demo_{novel,n2d,comic,song,mv,ad}.zip`, `SHA256SUMS.txt`.
- `--win` cross-builds the Windows x64 NSIS installer on macOS: electron-builder
  downloads its nsis/winCodeSign toolchains (cached after first run), native
  rebuild is disabled (`npmRebuild: false`) and node-pty runs from its bundled
  win32 NAPI prebuilds (`node_modules/node-pty/build` is excluded from packages
  so the host-built binary can't shadow them). The exe is unsigned.
- Release notes are written on release creation; on an existing release,
  incremental uploads (`--win --no-mac`, `--demos`) keep the notes —
  pass `--refresh-notes` to overwrite.
- Default tag `electron-v<desktop-electron/package.json version>`; the release
  is not marked latest by default and README download links are not rewritten
  by the tool — update them manually when publishing a user-facing release.
- Packaging: electron-builder emits the `.app` only (`--dir`); the DMG is made
  with `hdiutil` (electron-builder's dmg target downloads a dmgbuild bundle
  at build time — flaky on restricted networks). Signing is
  ad-hoc (`codesign -s -`) by default; set `E2A_SIGNING_IDENTITY` (and
  optionally `E2A_NOTARY_KEYCHAIN_PROFILE` to notarize + staple) for
  distributable builds.
- Installer files are never committed into the source tree or git history.

Requirements: node/npm/npx, rsync, zip/unzip, hdiutil (macOS), gh (only when
uploading), network for `npm ci`, `@vscode/vsce`, and release upload.
