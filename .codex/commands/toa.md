---
description: Mirror remote anime-arsenal code or publish AnimeArmory installers from remote source.
argument-hint: "[--demo] [--release [all]] [--no-upload] [--source-ref ref]"
---

Run from the repository root:

```bash
bash scripts/toa_release.sh $ARGUMENTS
```

Command contract:

- `toa`
  - Clone `https://github.com/anton6202527/anime-arsenal` remote `main`.
  - Sync that remote source into `https://github.com/anton6202527/anime-armory` `main`.
  - Remove `创作区/`, private agent files such as `.claude/`, `.codex/`, `.cursor/`, `.agents/`, `CLAUDE.md`, `GEMINI.md`, plus `dist/`, build outputs, `node_modules`, and installer artifacts.
  - Do not build or upload release installers.

- `toa --demo`
  - Clone `https://github.com/anton6202527/anime-arsenal` remote `main`.
  - Sync that remote source into `https://github.com/anton6202527/anime-armory` `main`.
  - Keep each creative line's most-complete demo from `创作区/`; remove the rest of `创作区/`, private agent files such as `.claude/`, `.codex/`, `.cursor/`, `.agents/`, `CLAUDE.md`, `GEMINI.md`, plus `dist/`, build outputs, `node_modules`, and installer artifacts.
  - Pull Git LFS files for the selected demo works before syncing, so demos are real files rather than LFS pointers.
  - Do not build or upload release installers.

- `toa --release`
  - Clone `anime-arsenal` remote `main`.
  - Keep each creative line's most-complete demo from `创作区/` and remove the rest, plus private agent files, `dist/`, generated outputs, and installer artifacts, from the temporary source tree before packaging.
  - Pull Git LFS files for the selected demo works before packaging, so demos are real files rather than LFS pointers.
  - Build only `AnimeArsenal_macos_arm64.dmg`.
  - Upload it to `https://github.com/anton6202527/anime-armory/releases`.
  - Update only that DMG download link in README.
  - Bundle the selected demo works into the release package.
  - Keep local build artifacts in `dist/toa-release-<tag>` while uploading; do not copy them to Desktop.
  - Do not mark this single-asset release as latest.
  - Do not sync source code to `anime-armory`.

- `toa --release all`
  - Clone `anime-arsenal` remote `main`.
  - Keep each creative line's most-complete demo from `创作区/` and remove the rest, plus private agent files, `dist/`, generated outputs, and installer artifacts, from the temporary source tree before packaging.
  - Pull Git LFS files for the selected demo works before packaging, so demos are real files rather than LFS pointers.
  - Build and upload the public all-release package set:
    - `AnimeArsenal_macos_arm64.dmg`
    - `AnimeArsenal_windows.exe`
    - `anime-armory.vsix`
  - Update README download links for those assets.
  - Mark the release as latest.
  - Bundle the selected demo works into each release package, including the VSIX.
  - Keep local build artifacts in `dist/toa-release-<tag>` while uploading; do not copy them to Desktop.
  - Do not sync source code to `anime-armory`.

Useful flags:

- `--demo`: include selected demo works when mirroring source code; release packaging includes demos automatically.
- `--source-ref REF`: build/sync from a specific remote branch or tag.
- `--no-upload`: build locally only in release mode; artifacts stay in `dist/toa-release-<tag>` unless `TOA_OUTPUT_DIR` is set.
- `--no-readme`: skip README link update after upload.
