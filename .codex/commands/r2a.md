---
description: Build AnimeArmory release installers locally and upload them to anime-armory Release assets.
argument-hint: "[--all] [--no-upload] [--no-readme] [--readme-link-mode auto|latest|tag]"
---

Run from the repository root:

```bash
bash scripts/r2a_release.sh $ARGUMENTS
```

Command contract:

- `/r2a`
  - Snapshot the current local checkout, excluding git metadata, private agent config, dist/build output, dependency caches, and non-selected creative works.
  - Bundle one full desktop demo seed work: `创作区/制漫剧/那妖魔是姜大人`.
  - Sync the latest bundled skills during packaging.
  - Build only `AnimeArmory_macos_arm64.dmg`.
  - Upload it to `https://github.com/anton6202527/anime-armory/releases` as a Release asset.
  - Update the matching README download link after upload. Single-asset releases are not marked as latest by default, so README uses a fixed tag URL unless overridden.
  - Do not commit installer files into the source tree or git history.

- `/r2a --all`
  - Build locally and upload all public release assets:
    - `AnimeArmory_macos_arm64.dmg`
    - `AnimeArmory_windows.exe`
    - `anime-armory.vsix`
  - Desktop packages include one full demo seed work: `创作区/制漫剧/那妖魔是姜大人`.
  - The VS Code extension keeps only its own lightweight bundled seed work root and does not copy the selected desktop demos.
  - Update README download links for the uploaded assets and mark the release as latest. README uses `releases/latest/download/...` by default.

README link policy:

- Fixed, reproducible tag URL: `https://github.com/anton6202527/anime-armory/releases/download/v0.1.0/AnimeArmory_macos_arm64.dmg`
- Always-latest README URL: `https://github.com/anton6202527/anime-armory/releases/latest/download/AnimeArmory_macos_arm64.dmg`

Useful flags:

- `--readme-link-mode auto|latest|tag`: choose README URL style. `auto` means latest for `--all`, fixed tag for single-asset `r2a`.
- `--remote-source --source-ref REF`: build from a specific remote branch or tag instead of the local checkout.
- `--no-upload`: build locally only; artifacts stay in `dist/r2a-release-<tag>` unless `R2A_OUTPUT_DIR` is set.
- `--no-readme`: skip README link update after upload.
