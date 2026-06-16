# Anime Armory - AI Content Creation Factory

Industrial-grade AI content production pipeline for turning novels into AI comic-dramas / short-dramas (N2D).

## Project Overview

Anime Armory is a collection of automated workflows (Skills) designed to streamline the transition from raw creative ideas to polished digital assets. It hosts **four parallel creative production lines — n2d / song / mv / ad**. The flagship is **n2d**: turn a novel into an AI comic-drama / short-drama — the `n2d` dispatcher routes script → voice → storyboard → image → video → compose, with cross-cutting skills for identity/LoRA/model-routing/QA/compliance/dashboard. Each line is self-contained and separately packageable (本线 scripts only import their own `_lib`/craft, never `skills/common/` or another line's code; cross-line is optional file/data handoff only).

The project is built on **Claude Code Skills**, making it highly portable and compatible with various AI agents and local automation scripts.

## Core Architecture

### 1. Skills System (`skills/`)
The engine of the project. Each sub-directory is an atomic "Skill" containing:
-   `SKILL.md`: Metadata, triggers, and step-by-step instructions.
-   `scripts/`: Python or Bash logic implementing the automation.
-   `references/`: Specialized knowledge bases (e.g., fight scene storyboarding, platform limits).

### 2. State Management
Projects are tracked via two local markdown files (stored in project roots like `制漫剧/<project>/`):
-   **`_进度.md` (Status):** A state machine tracking the progress of each episode or chapter. Always read this first to determine the next step.
-   **`_设置.md` (Settings):** Project-specific configurations (platforms, models, resolution, languages). This file is private and should not be committed to shared templates.

### 3. Preference Layering
Preferences are resolved in this order:
1.  **Project Level:** `<project_root>/_设置.md` (Overrides everything).
2.  **Global Default:** `创作偏好-默认.md`, `.agents/创作偏好-默认.md`, or `.codex/创作偏好-默认.md` (private user defaults; `.claude/` is legacy-compatible).
3.  **Interactive:** Prompt the user once, then record to `_设置.md`.

## Routing — pick a skill by intent (mirrors `AGENTS.md`)

Match user intent against the table below (and each `SKILL.md`'s Triggers). Recommend skills by **bare name** (write `n2d`, not `/n2d`).

| User wants to | Entry skill (dispatcher → routes to sub-skills) |
|---|---|
| Turn a novel into an AI comic-drama / short-drama (storyboard/voice/image/video/compose) | **`n2d`** (→ n2d-script/voice/image/video/compose) |
| Write a song, edit lyrics, compose, pick takes, cover/voice-swap, review | **`song`** (→ song-lyrics/compose/cover/review …) |
| Make an MV for a song, beat-sync, image/video, karaoke subtitles, compose | **`mv`** (→ mv-script/beat/plan/image/video/compose …) |
| Make an ad / TVC / feed ad / product demo / promo video | **`ad`** (→ ad-concept/script/voice/image/video/compose/review) |
| See project progress / next step, or summarize every n2d project at repo root | **`n2d-progress`** (read-only scan; never writes `_进度.md`) |
| Edit/audit project settings, choice points, or global defaults | **`n2d-settings`** (wraps `_设置.md` read/validate/reset/sync) |
| Check whether skill updates affect a project, plan a rebuild, re-render some images/videos | **`n2d-update`** (snapshot diff + minimal rebuild plan; `media` subcommand for selective image/video refresh) |
| Clean up / slim generated junk | **`tools/shared-cleanup`** (repo dev tool; scans `skills/` by default, `--repo` for whole repo; deletes only low-risk cache/temp and reports saved space) |
| Audit whether lines are still independent / wrongly import a shared layer or another line | **`tools/independence-audit`** (static scan; code-level cross-line dependency fails) |
| Refresh choice-point candidates (are model/backend lists stale?) | per-line **`skills/<line>/_lib/refresh.py`** (only n2d/ad have candidate sources; machine-checks snapshot freshness → live-search verify → edit candidates + bump 采集日期 + log provenance; keeps per-line policy differences un-merged) |

## Technical Stack & Environment

-   **OS:** macOS (Primary development environment).
-   **Python:** 3.14 (System) + Specialized Conda environments:
    -   `cosyvoice`: Voice cloning / character voicing, Whisper, librosa.
    -   `facefusion`: Pixel QC stack (insightface / onnxruntime / buffalo_l).
-   **Media Tools:**
    -   `ffmpeg`: Heavy lifting for video/audio composition (note: use Pillow for text rendering as the local ffmpeg may lack libass).
    -   `whisper` / `whisperx`: For lyric/subtitle synchronization.
    -   `librosa`: For beat detection.

## Development Conventions

> **The authoritative "how to *build* a skill" design law is [`docs/skill-design-principles.md`](docs/skill-design-principles.md)** (cross-line constitution: independence / choice-point adapter / compliance gates / VCS-free delivery / README sync). The points below are a summary — read the constitution before adding or changing a skill. Machine-checkable clauses: `python3 tools/validate_skills.py` (E1 no-git / B2 bare skill names / F1 README index / F3 entry-doc sync) and `tools/independence-audit/scripts/check_independence.py` (line independence).

1.  **Self-contained line:** Each creative line is **separately packageable** — as of the 2026-06 refactor there is **no shared layer** (`skills/common/` deleted; pipeline modules vendored into each line's own `_lib`/craft area; watermark & faceswap skills retired 2026-06). The `tools/independence-audit/scripts/check_independence.py` gate enforces "no `skills/common`, no cross-line import, no `shared-*` reference".
2.  **Non-Hardcoded Platforms:** Never hardcode a specific AI platform (e.g., Suno, Kling) as the only path. Always use the "Choice Point" mechanism via each line's `references/选择点与偏好.md`.
3.  **Progress Tracking:** Every skill that advances a project MUST update the corresponding `_进度.md`.
4.  **Compliance:** Voice-cloning and character-likeness activities must pass the "Compliance Gate" (user authorization required).
5.  **Output Paths:**
    -   `制漫剧/`: Drama production assets — per-episode `出视频/` clips + `合成/` audio/post and final MP4.
    -   `资产库/`: Cross-project reusable asset packs (character archetypes, scenes, props, route experience).

## Building and Running

There is no global "build" command. Individual steps are run via their respective scripts:
-   Check `skills/<skill_name>/scripts/` for implementation details.
-   Use `run_shell_command` to execute Python scripts within the appropriate Conda environment.
-   Always verify the current status using the relevant progress skill such as `n2d-progress`, or by reading `_进度.md` before initiating a new stage.
