# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`anime-armory` is **not** an application — it's a library of Claude Code **skills** that form the **n2d** creation + production factory: 小说→制漫剧 (novel → AI comic-drama). The "source code" is the skills under `skills/`; the top-level Chinese folder `创作区/制漫剧/` holds **demo outputs**, not application data.

Orientation order: `AGENTS.md` (tool-neutral entry, has the intent→skill routing table) → `skills/README.md` (skill index) → individual `skills/<name>/SKILL.md`. `README.md` is the project overview. Don't duplicate those here — read them. `GEMINI.md` is a per-tool mirror of `AGENTS.md` — if you change the routing table or entry doc, keep it in sync. Deeper design notes that don't belong in a skill live under `docs/` (e.g. `docs/n2d-声音工程化方案.md`, the voice-engineering rationale behind `n2d-voice`).

## Architecture (the parts that span multiple files)

**One self-contained, separately-packageable line, dispatcher-routed.** The `n2d` **dispatcher skill** does no work itself — it inspects the work-folder root, reads `_进度.md`, and routes to a stage skill. **As of the 2026-06 full-independence refactor there is NO shared layer**: `skills/common/` is deleted, all pipeline modules are vendored into `skills/n2d/_lib/`. (Per-line faceswap/watermark skills were retired 2026-06.) The independence gate `tools/independence-audit/scripts/check_independence.py` enforces "no `skills/common`, no cross-line import, no `shared-*` reference". Repo-level meta-tools that aren't owned by a creative line stay single-copy under `tools/`; line-owned progress skills such as `n2d-progress` remain normal workflow skills. Update/rebuild planning lives in the n2d line as `n2d-update` (its `media` subcommand plans selective image/video refresh) — the old cross-line `update` dispatcher was retired 2026-06.

**`skills/` is flat, grouped by name prefix** (`n2d-*`). A SKILL.md's frontmatter `description` + the `Triggers`/`Use when` lines **are the routing logic** — match user intent against them. `.claude/skills → ../skills` is a symlink so Claude Code auto-discovers them.

**n2d-supervisor is the agentic layer, not a replacement state machine.** It consumes `skills/n2d/run.py next --json`, uses context packs / creative loops / action contracts, and dispatches a few specialists; it must not bypass `_进度.md`, gates, batch, dashboard, or stage skills.

**n2d is the flagship pipeline** and has two non-obvious ordering decisions worth knowing before touching `n2d-*`:
- **Voice-first**: `n2d-voice` runs *before* storyboard. It produces a per-line **measured-duration list** (`时长清单`) that then drives shot durations — so `n2d-script` is run twice (script pass, then storyboard pass after voice).
- **Two-layer image gen**: `n2d-image` first builds a shared 定妆库 (locked character faces / scenes / style) and only then per-shot frames, to keep characters consistent across shots. Stage order: `n2d-script`(改编) → `n2d-voice` → `n2d-script`(分镜) → `n2d-image` → `n2d-video` → `n2d-compose`.
- **`出视频/` vs `合成/` split (2026)**: `出视频/第N集/` holds ONLY the per-shot clips (`视频/`) + video prompts (`prompt/`). Everything audio/post — `配音/` (n2d-voice output, incl. `时长清单.json`), `_voicecache/`, compose `_work/`, the final `成片_*.mp4`, and optional watermark output — lives in the sibling `合成/第N集/`. compose reads clips from `出视频/`, voice from `合成/`, and writes 成片 to `合成/`. `n2d-compose` can optionally call `watermark` after 成片 (`水印` choice point).

**Per-work state lives in two sibling files** at each work root (`创作区/制漫剧/<剧名>/`):
- `_进度.md` — the **state machine**. Read it first to know what stage a work is at; write it back when a stage completes.
- `_设置.md` — the **private per-work choices** (platform/backend/resolution/voice…), authoritative.

**Generic skill, private choice.** Skills must NOT hardcode a single platform/backend/resolution. Anything "let the user pick" is a *choice point*, resolved via each line's `<line>-craft/references/选择点与偏好.md` (n2d: `n2d/references/选择点与偏好.md`): read `<work>/_设置.md` → else a private global default such as `创作偏好-默认.md`, `.agents/创作偏好-默认.md`, or `.codex/创作偏好-默认.md` (`.claude/` is legacy-compatible) → else ask once, then persist and reuse silently. Exception: compliance / irreversible / costly points are re-confirmed every time even if recorded.

## Commands & environment

There is **no build, no lint, no package manager.** Skill scripts are plain Python/bash invoked individually. There is now one **optional aggregate regression gate** — `bash tools/run_all_checks.sh` (full `pytest skills/`/`tools/` + governance checks in a single exit code; see Hard conventions). It does not replace running an individual skill's own pytest from its directory; it's the "did I break anything repo-wide" gate used by CI and the pre-commit hook.

**Heavy AI steps need out-of-repo conda envs** (model weights live in `~/CosyVoice`, `~/ACE-Step`, `~/facefusion`, etc.):
- `cosyvoice` (also has librosa/whisper), `acestep`, `fish-speech`, `facefusion`.
- System Python 3.14 + PEP 668 cannot install the heavy deps — run audio/video scripts inside the matching conda env. Per-skill gotchas are in each `skills/<name>/references/`.

**ffmpeg here is a stripped build with no libass/drawtext** — subtitles are rendered to PNG via Pillow and overlaid (see `n2d-compose/render_subs.py`). Don't write `subtitles=`/`drawtext` filters expecting them to work.

**Tests** are standalone pytest files that import their sibling module by relative path — run them *from the script's own directory* (no central runner; the file's own docstring states its cd path). Coverage is sparse: only the few skills with non-trivial pure-Python logic have tests — the storyboard/voice-fit math (`n2d-script`, `n2d-compose`), the image-QC / asset-impact / drift-risk / lifecycle calc (`n2d-image`), the contract-inheritance diff (`n2d-video`), and the QA mechanical-check engine (`n2d-review`). Examples:
```bash
cd skills/n2d-script && python -m pytest test_finalize_storyboard.py
cd skills/n2d-image/scripts && python -m pytest test_image_qc.py
cd skills/n2d-video/scripts && python -m pytest test_inherit_contract.py
cd skills/n2d-review/scripts && python -m pytest test_gate.py
```

## Hard conventions

**Design law has one authoritative home: [`docs/skill-design-principles.md`](docs/skill-design-principles.md)** — the cross-line "how to *build* a skill" constitution (independence, generic-skill/private-choice, choice-point-as-adapter, compliance gates, VCS-free delivery, README-sync). Read it before adding/changing a skill. **Don't restate it here or per-skill** — point to it. Machine-checkable clauses are enforced:
- `python3 tools/validate_skills.py` — E1 VCS-free (no git state checks in skills), B2 bare skill names, B7 character makeup base pack, B9 persistent-subject-vs-project-memory split, F1 `skills/README.md` index sync, F3 entry-doc sync.
- `python3 tools/independence-audit/scripts/check_independence.py` — A1/F2 line independence (no `skills/common`, no cross-line import).
- `bash tools/run_all_checks.sh` — **repo-level regression gate**: runs the two governance checks above + full `pytest skills/`/`tools/` in one exit code. CI (`.github/workflows/ci.yml`) runs it on every push/PR; install the local pre-commit fast subset with `git config core.hooksPath .githooks`. Use `--fast`/`--changed` for the pre-commit subset. This is the one place to run "did my change break anything"; heavy-conda-dep tests skip gracefully so it stays green without model weights.

Quick reminders of the highest-stakes clauses (full text + rationale in the constitution):
- **Edit the skill set → update `skills/README.md` in the same change** (F1).
- **Choice points are dated candidate snapshots, routed through the adapter layer, never hardcoded** (C1/C2); compliance/irreversible/costly points re-confirm every time.
- **Main flow never hard-binds a backend or requires an install** (C4): heavy deps (model weights, conda envs, paid APIs, local CLIs) go through the line's adapter layer; missing/uninstalled deps must degrade gracefully (still emit a stable job pack + tell the user what to install via `references/`), never hard-fail the pipeline.
- **Compliance is non-negotiable** (D1): voice-clone only on self/authorized voices (2026 opt-in); source novels default to public-domain/owned/licensed. (Note: forced AI-identification/watermark enforcement was **retired from the n2d pipeline 2026-06** — handled outside the tool now; see `n2d-compliance`.)

Claude-Code-operational rules not in the constitution:
- **Existing works are demos** — keep the `创作区/制漫剧/` demos; do not suggest deleting them or adding them to `.gitignore` (that decision is already made; see `TODO.md` for the optional strip-to-template path).
- Commits go directly to `main` (not a PR flow).
