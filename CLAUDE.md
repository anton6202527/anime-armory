# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`anime-armory` is **not** an application — it's a library of ~29 Claude Code **skills** that form a creation + production factory: 写小说→制漫剧 (novel → AI comic-drama) and 写歌→制MV (song → AI music video). The "source code" is the skills under `skills/`; the top-level Chinese folders (`写小说/` `制漫剧/` `写歌/` `制MV/`) are **demo outputs**, not application data.

Orientation order: `AGENTS.md` (tool-neutral entry, has the intent→skill routing table) → `skills/README.md` (skill index) → individual `skills/<name>/SKILL.md`. `README.md` is the project overview. Don't duplicate those here — read them.

## Architecture (the parts that span multiple files)

**Four self-contained lines, dispatcher-routed.** Each line has one **dispatcher skill** (`novel-author` / `novel2drama` / `song` / `mv`) that does no work itself — it inspects the work-folder root, reads `_进度.md`, and routes to a stage skill. The lines are **independent**: `mv-*` does NOT reuse `n2d-*`, etc. They connect only at the *finished-artifact* level (a song file feeds the MV line), never as skill dependencies. Faceswap (`video-faceswap` / `image-faceswap`) is a shared capability any line may call.

**`skills/` is flat, grouped by name prefix** (`novel-*`, `n2d-*`, `song-*`, `mv-*`). A SKILL.md's frontmatter `description` + the `Triggers`/`Use when` lines **are the routing logic** — match user intent against them. `.claude/skills → ../skills` is a symlink so Claude Code auto-discovers them.

**novel2drama is the flagship pipeline** and has two non-obvious ordering decisions worth knowing before touching `n2d-*`:
- **Voice-first**: `n2d-voice` runs *before* storyboard. It produces a per-line **measured-duration list** (`时长清单`) that then drives shot durations — so `n2d-script` is run twice (script pass, then storyboard pass after voice).
- **Two-layer image gen**: `n2d-image` first builds a shared 定妆库 (locked character faces / scenes / style) and only then per-shot frames, to keep characters consistent across shots. Stage order: `n2d-script`(改编) → `n2d-voice` → `n2d-script`(分镜) → `n2d-image` → `n2d-video` → `n2d-compose`.

**Per-work state lives in two sibling files** at each work root (`制漫剧/<剧名>/`, `写歌/<曲名>/`, etc.):
- `_进度.md` — the **state machine**. Read it first to know what stage a work is at; write it back when a stage completes.
- `_设置.md` — the **private per-work choices** (platform/backend/resolution/voice…), authoritative.

**Generic skill, private choice.** Skills must NOT hardcode a single platform/backend/resolution. Anything "let the user pick" is a *choice point*, resolved via `skills/_偏好约定.md`: read `<work>/_设置.md` → else the global default `.claude/创作偏好-默认.md` (prefill + tell the user once) → else ask once, then persist and reuse silently. Exception: compliance / irreversible / costly points are re-confirmed every time even if recorded.

## Commands & environment

There is **no build, no lint, no package manager, no central test runner.** Skill scripts are plain Python/bash invoked individually.

**Heavy AI steps need out-of-repo conda envs** (model weights live in `~/CosyVoice`, `~/ACE-Step`, `~/facefusion`, etc.):
- `cosyvoice` (also has librosa/whisper), `acestep`, `fish-speech`, `facefusion`.
- System Python 3.14 + PEP 668 cannot install the heavy deps — run audio/video scripts inside the matching conda env. Per-skill gotchas are in each `skills/<name>/references/`.

**ffmpeg here is a stripped build with no libass/drawtext** — subtitles are rendered to PNG via Pillow and overlaid (see `n2d-compose/render_subs.py`, `mv-compose/render_lyrics.py`). Don't write `subtitles=`/`drawtext` filters expecting them to work.

**Tests** are standalone pytest files that import their sibling module by relative path — run them *from the script's own directory*:
```bash
cd skills/n2d-script && python -m pytest test_finalize_storyboard.py
cd skills/novel-fetch/scripts/tests && python -m pytest test_fetch_novel.py
```

## Hard conventions

- **Editing the skill set** (add/remove/change a skill's responsibility) → you MUST update the `skills/README.md` index in the same change.
- **Compliance gates are non-negotiable**: faceswap/voice-clone only on self / authorized / synthetic faces, with forced AI-identification watermark; cloning a real singer's voice needs authorization (2026 opt-in). Lyrics/novels default to public-domain / owned / licensed sources. Never strip the AI-ident mark.
- **Existing works are demos** — keep them; do not suggest deleting them or adding them to `.gitignore` (that decision is already made; see `TODO.md` for the optional strip-to-template path).
- Commits go directly to `main` (not a PR flow).
