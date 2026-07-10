# e2a

Repo release tool: build the **Electron desktop app** (`desktop-electron/`) as a
macOS installer plus the per-line **demo zip assets**, and upload them to
anime-armory GitHub Release assets. This is the Electron counterpart of the
Tauri `/r2a` flow (`scripts/r2a_release.sh`) and reuses its building blocks:
demo selection (`scripts/r2a_select_demo.cjs`), the safe payload copier
(`tools/release-safety/demo_safety.cjs`) and the skills bundler
(`desktop/sync-skills.cjs`).

Use when:

- releasing or locally packaging the Electron desktop app
- refreshing the demo zip assets alongside an Electron app release
- asked for "electron 打包 / electron 发版 / e2a"

Run:

```bash
bash tools/e2a/scripts/e2a_release.sh                # Electron DMG + demo zips, upload
bash tools/e2a/scripts/e2a_release.sh --no-upload    # local build only (dist/e2a-release-<tag>)
bash tools/e2a/scripts/e2a_release.sh --apps-only    # DMG only, skip demo zips
bash tools/e2a/scripts/e2a_release.sh --demo-assets  # demo zips only, keep release notes
```

Contract:

- Default builds **both** the app and the demo zip assets (unlike `/r2a`,
  whose default is apps-only — this tool exists for the "Electron app 包括
  对应的 demo" release path).
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
- n2d demo zip is slimmed to first-episode media (same rule as `/r2a`).
  Demo zips are deterministic (fixed timestamps, `zip -X`).
- Artifact names: `AnimeArmory_electron_macos_arm64.dmg`,
  `AnimeArmory_demo_{novel,n2d,comic,song,mv,ad}.zip`, `SHA256SUMS.txt`.
- Default tag `electron-v<desktop-electron/package.json version>`; the release
  is never marked latest and README download links are never rewritten —
  the Tauri `/r2a` flow owns both.
- Packaging: electron-builder emits the `.app` only (`--dir`); the DMG is made
  with `hdiutil` like `/r2a` (electron-builder's dmg target downloads a
  dmgbuild bundle at build time — flaky on restricted networks). Signing is
  ad-hoc (`codesign -s -`) by default; set `E2A_SIGNING_IDENTITY` (and
  optionally `E2A_NOTARY_KEYCHAIN_PROFILE` to notarize + staple) for
  distributable builds.
- Installer files are never committed into the source tree or git history.

Requirements: node/npm, rsync, zip/unzip, hdiutil (macOS), gh (only when
uploading), network for `npm ci` + release upload.
