# Anime Armory - AI Content Creation Factory

Industrial-grade AI content production pipeline for Novels, Anime/Dramas (N2D), Songs, and Music Videos (MV).

## Project Overview

Anime Armory is a collection of automated workflows (Skills) designed to streamline the transition from raw creative ideas to polished digital assets. It operates on parallel production lines:
1.  **Narrative Line:** `novel-author` (Writing/Editing) → `novel2drama` (Anime/Drama Video Production).
2.  **Audio-Visual Line:** `song` (Lyrics/Composition) → `mv` (Music Video Production).
3.  **Advertising Line:** `ad` (Client brief → creative → script → storyboard → image → video → voice → editing/packaging → master). Self-contained `ad-*`; **not split into episodes** (multi-duration cutdowns + multi-aspect deliverables instead), with a built-in 《广告法》(Ad Law) banned-term checker.

The project is built on **Claude Code Skills**, making it highly portable and compatible with various AI agents and local automation scripts.

## Core Architecture

### 1. Skills System (`skills/`)
The engine of the project. Each sub-directory is an atomic "Skill" containing:
-   `SKILL.md`: Metadata, triggers, and step-by-step instructions.
-   `scripts/`: Python or Bash logic implementing the automation.
-   `references/`: Specialized knowledge bases (e.g., fight scene storyboarding, platform limits).

### 2. State Management
Projects are tracked via two local markdown files (stored in project roots like `写小说/<project>/` or `制漫剧/<project>/`):
-   **`_进度.md` (Status):** A state machine tracking the progress of each episode or chapter. Always read this first to determine the next step.
-   **`_设置.md` (Settings):** Project-specific configurations (platforms, models, resolution, languages). This file is private and should not be committed to shared templates.

### 3. Preference Layering
Preferences are resolved in this order:
1.  **Project Level:** `<project_root>/_设置.md` (Overrides everything).
2.  **Global Default:** `.claude/创作偏好-默认.md` (User's personal defaults).
3.  **Interactive:** Prompt the user once, then record to `_设置.md`.

## Key Commands (via AI Agents)

| Line | Entry Point | Primary Tasks |
| :--- | :--- | :--- |
| **Novel** | `/novel-author` | Route to create, fetch, title, spinoff, rewrite, continue, or review. |
| **Drama** | `/novel2drama` | Route to script, voice, image, video, or compose. |
| **Song** | `/song` | Route to lyrics, compose, cover, or review. |
| **MV** | `/mv` | Route to beat detection, image, video, lyric-sync, or compose. |
| **Ad** | `/ad` | Route to craft, concept, script (+Ad-Law check), voice, image (3-layer lockup incl. product), video, or compose (cutdowns + reframes + delivery). |
| **Public** | `/image-faceswap` | Face swapping for images (FaceFusion based). |
| **Public** | `/video-faceswap` | Face swapping for videos (FaceFusion based). |
| **Public** | `/watermark` | Watermark images/videos: compliance AI label (add-only) or brand/logo. faceswap calls it for AI labelling. |

## Technical Stack & Environment

-   **OS:** macOS (Primary development environment).
-   **Python:** 3.14 (System) + Specialized Conda environments:
    -   `cosyvoice`: Audio processing, Whisper, librosa.
    -   `acestep`: Local song composition.
    -   `facefusion`: Face swapping.
-   **Media Tools:**
    -   `ffmpeg`: Heavy lifting for video/audio composition (note: use Pillow for text rendering as the local ffmpeg may lack libass).
    -   `whisper` / `whisperx`: For lyric/subtitle synchronization.
    -   `librosa`: For beat detection.

## Development Conventions

1.  **Independence:** The `mv-*`, `n2d-*`, and `ad-*` lines are strictly independent. Do not share code or skills between them to maintain modularity (each line has its own `*-craft`/contract).
2.  **Non-Hardcoded Platforms:** Never hardcode a specific AI platform (e.g., Suno, Kling) as the only path. Always use the "Choice Point" mechanism via `_偏好约定.md`.
3.  **Progress Tracking:** Every skill that advances a project MUST update the corresponding `_进度.md`.
4.  **Compliance:** All face-swapping and voice-cloning activities must pass the "Compliance Gate" (user authorization + mandatory AI watermark).
5.  **Output Paths:**
    -   `写小说/`: Pure text outputs.
    -   `制漫剧/`: Video/Drama production assets and final MP4.
    -   `写歌/`: Lyrics and WAV/MP3 files.
    -   `制MV/`: MV production assets and final MP4.
    -   `拍广告/`: Ad production assets, master MP4 + cutdowns + multi-aspect deliverables.

## Building and Running

There is no global "build" command. Individual steps are run via their respective scripts:
-   Check `skills/<skill_name>/scripts/` for implementation details.
-   Use `run_shell_command` to execute Python scripts within the appropriate Conda environment.
-   Always verify the current status using `/n2d-progress` or by reading `_进度.md` before initiating a new stage.
