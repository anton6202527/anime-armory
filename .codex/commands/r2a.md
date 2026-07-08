---
description: Build AnimeArmory release installers locally and upload them to anime-armory Release assets.
argument-hint: "[--all|--demo-assets] [--with-demo-assets] [--no-upload] [--no-readme] [--readme-link-mode auto|latest|tag]"
---

Run from the repository root:

```bash
bash scripts/r2a_release.sh $ARGUMENTS
```

Command contract:

- `/r2a`
  - Snapshot the current local checkout, excluding git metadata, private agent config, dist/build output, dependency caches, and non-selected creative works.
  - Keep selected demo work references only for the desktop demo catalog; full demo payloads are not copied.
  - Sync the latest bundled skills during packaging.
  - Build only `AnimeArmory_macos_arm64.dmg`.
  - Upload it to `https://github.com/anton6202527/anime-armory/releases` as a Release asset.
  - Update the matching README download link after upload. Single-asset releases are not marked as latest by default, so README uses a fixed tag URL unless overridden.
  - Do not commit installer files into the source tree or git history.

- `/r2a --all`
  - Build locally and upload all public app release assets:
    - `AnimeArmory_macos_arm64.dmg`
    - `AnimeArmory_windows.exe`
    - `anime-armory.vsix`
  - Demo zip assets are not rebuilt. Run `/r2a --demo-assets` separately when demo payloads changed.
  - Desktop packages include release-download demo catalog entries, not full demo payloads.
  - The VS Code extension keeps only its own lightweight bundled seed work root and does not copy the selected desktop demos.
  - Update README download links for the uploaded assets and mark the release as latest. README uses `releases/latest/download/...` by default.

- `/r2a --demo-assets`
  - Build and upload only configured demo zip assets:
    - `AnimeArmory_demo_novel.zip`
    - `AnimeArmory_demo_n2d.zip`
    - `AnimeArmory_demo_comic.zip`
    - `AnimeArmory_demo_song.zip`
    - `AnimeArmory_demo_mv.zip`
    - `AnimeArmory_demo_ad.zip`
  - Does not build app installers, does not update README app links, and does not mark the release latest.
  - Keeps existing release notes when uploading to an existing release; only checksums are refreshed.
  - Use this when demo payloads changed; normal app releases can stay fast.

- `/r2a --all --with-demo-assets`
  - Legacy combined path: builds all app installers plus demo zip assets in one run.
  - This is slower because large demo zips are packaged and uploaded too.

README link policy:

- Fixed, reproducible tag URL: `https://github.com/anton6202527/anime-armory/releases/download/v0.1.0/AnimeArmory_macos_arm64.dmg`
- Always-latest README URL: `https://github.com/anton6202527/anime-armory/releases/latest/download/AnimeArmory_macos_arm64.dmg`

Useful flags:

- `--readme-link-mode auto|latest|tag`: choose README URL style. `auto` means latest for `--all`, fixed tag for single-asset `r2a`.
- `--demo-assets`: build/upload only demo zip assets.
- `--with-demo-assets`: include demo zip assets in an app release.
- `--remote-source --source-ref REF`: build from a specific remote branch or tag instead of the local checkout.
- `--no-upload`: build locally only; artifacts stay in `dist/r2a-release-<tag>` unless `R2A_OUTPUT_DIR` is set.
- `--no-readme`: skip README link update after upload.
