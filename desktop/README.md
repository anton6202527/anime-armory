# AnimeArmory — Desktop (Tauri + React)

A Tauri 2 + Vite/React/TS desktop shell for the anime-armory creation factory.

## Design Laws

1. Opening a work folder means opening an editable workspace, not a preview gallery. Every text file under the work root must be editable in-app like VS Code; media files can remain preview-only, but text must not require Finder or an external editor for normal work.
2. The editor core is Monaco's text model, not a hand-built DOM text view. Keep the path `file tree -> selected file -> Monaco model -> viewport-rendered editor`; do not render documents as one DOM node per line or character.
3. Large-file behavior must favor stable memory. Keep the file tree virtualized, let Monaco own text buffering/layout/visible-line rendering, and avoid mounting hidden editors for every file until an explicit editor-tab design exists.
4. All file writes go through the Tauri command layer with work-root confinement and external-modification checks. The frontend must not gain broad filesystem write authority.
5. Visual identity is plugin-shaped. Colors, Monaco theme data, and file-icon decisions live behind a skin plugin registry so text, icons, and editor chrome can be swapped without rewriting component logic.
6. Change tracking is archive-based. A work root is compared against its last archived baseline; archiving records the current state as clean and must not trigger repeated recalculation unless the work files change again.

- **Home** → lists creative lines (n2d / comic / ad / mv / song / novel) and their work roots.
- **Operation page** → **left = editable file workspace by default** (plus canvas/kanban/review for visual lines), **right = resizable native terminal** (real PTY) + a read-only "next action" strip.
- The terminal agent bar detects Claude Code / Codex CLI / Gemini CLI / OpenCode. If no paid/specialized agent is installed, OpenCode is shown as an installable open-source fallback; clicking it runs the official installer in the terminal and then launches `opencode`.
- The canvas reads `生产数据/review_ui_第N集.json` when present, else **falls back to `脚本/第N集/storyboard.json`**; comic works additionally fall back to `脚本/第N话/panel_script.json` plus `panel_jobs` / `panel_qc` / consistency reports.
- The file workspace is VS Code-style lazy loading: `work_dir` reads one shallow directory page at a time, the React tree virtualizes visible rows, and large directories use explicit "加载更多" pages instead of sending the whole work tree to the webview.
- File watching is selective: the backend watches the work root plus key text/index directories and throttles event bursts; deep media-heavy outputs rely on the existing snapshot polling fallback.
- The review tab upgrades to a per-episode workspace when `生产数据/episodes/第N集.json` exists, showing metrics, stage status, return-to-stage issues, evidence files, and clip summaries from the stable episode aggregation contract.

This is a **scaffold/spike**. It reuses the repo's existing `--json` contracts as its backend; it does not reimplement skill logic.

## Prerequisites

- **Node ≥ 18** — `npm install` for the frontend deps.
- **Rust ≥ 1.88** — required to build the Tauri shell (some transitive deps need 1.88; 1.87 fails to resolve). `rustup update stable` if older.
  ```sh
  curl --proto '=https' --tlsv1.2 https://sh.rustup.rs -sSf | sh   # if not installed
  rustc --version   # verify ≥ 1.88
  ```
  macOS also needs Xcode Command Line Tools (`xcode-select --install`). Tauri uses the system WebKit — no extra webview download on macOS. The crate **builds + bundles clean** (`.app` + `.dmg`) as of 2026-06.

## Run

```sh
cd desktop
npm install                 # done (frontend deps)
npm run app:dev             # = tauri dev: builds Rust, launches the app, hot-reloads the React side
```
First `tauri dev` compiles the Rust crate (a few minutes once). The skills repo is inferred from the live checkout in dev and falls back to bundled resources in packaged builds. Packaged builds ship full skills plus any configured demo works: existing `创作区` demos from `desktop/demo-works.json`, and demo folders under outer dispatcher skills such as `skills/ad/demo`. Missing series are skipped. First launch seeds bundled works into the app workspace without overwriting user files. To force a dev repo, set `VITE_ANIME_ARMORY_REPO=/absolute/path/to/anime-armory`. The works workspace is chosen at runtime via the "切换工作区…" button (uses the native folder picker).

Frontend-only (no native shell, for quick UI work):
```sh
npm run dev                 # http://localhost:1420 — Tauri commands are no-ops in a plain browser
```

Build an installer (later — needs full icon set):
```sh
npm run tauri icon src-tauri/icons/icon.png   # regenerate icns/ico from a real 1024² logo
npm run app:build
```

## Architecture

```
src/                         React frontend
  pages/Home.tsx             line + work-root launcher  (scan_workspace)
  pages/Operation.tsx        left file/canvas views / resizable right terminal + episode switcher
  views/registry.tsx         per-line view registry: canvas | files(novel) | audio(song)
  components/CanvasPane.tsx   React Flow: clip/panel nodes + continuity/next-panel edges
  components/ClipNode.tsx     clip card: frame thumb, rhythm/duration chips, QA badges
  components/TerminalPane.tsx xterm.js ↔ PTY events
  components/MonacoFileEditor.tsx Monaco text model + viewport editor + save command
  components/NextActionStrip  run.py next --json → headline + copyable command
  skins/                       plugin-shaped UI skin + file icon mapping + Monaco theme
  api.ts / types.ts          Tauri invoke wrappers + media-URL helper + shared types
src-tauri/src/
  pty.rs                     portable-pty sessions → base64 over `pty-data` / `pty-exit` events
  media.rs                   127.0.0.1 static server, /media?path=…  (HTTP range for MP4)
  commands.rs                scan_workspace · read_canvas (review_ui→storyboard→panel_script fallback) · read_next_action
  main.rs                    Tauri builder, command registry, state, dialog plugin
```

### Backend contracts reused (never reparses markdown)
- `read_canvas` → `review_ui_第N集.json` (`clips[]`/`seams[]`/`qa_flags[]`) → fallback `storyboard.json` (`clips[].id/label/duration/scene/rhythm/template/continuity.transition/firstframe_png`) → comic fallback `panel_script.json` (`panels[]`) with `panel_jobs.json`, `panel_qc`, and comic consistency findings.
- `read_next_action` → shells `skills/n2d/run.py next <root> <ep> --json`.
- `scan_workspace` → maps lines to product dirs under `创作区/` (制漫剧/画漫画/拍广告/制MV/写歌/写小说) and lists work roots (`_进度.md` = has progress).

## Implemented vs stubbed (v1)

| Piece | Status |
|---|---|
| Tauri shell + Vite/React/TS | ✅ scaffolded, frontend builds clean |
| Native terminal (portable-pty ↔ xterm) | ✅ written (needs Rust to run) |
| Canvas (React Flow) from review_ui/storyboard/panel_script | ✅ visual lines show clips or comic panels; node virtualization on |
| NextAction strip (run.py next --json) | ✅ async + 30s timeout (off main thread) |
| Media server (range requests) | ✅ images + inline video (`<video>` when 出视频 exists); path-confined to allowed roots, 4-thread pool |
| Home launcher + folder picker | ✅ |
| File-watch live refresh (`notify` → `fs-changed` → debounced re-pull) | ✅ |
| File tree + previews (`md` / `json` / images / audio / video) | ✅ default tab for every work |
| Monaco text editing (`md` / `json` / scripts / text) | ✅ path-confined save, dirty-state guard, Cmd/Ctrl+S |
| Change diff + archive baseline | ✅ Monaco diff, added/modified/deleted list, one-click archive |
| song view (waveform/takes) | ⛔ stub |
| Interactive canvas editing | ✅ drag positions persist; storyboard clips and comic panels can be edited through guarded Tauri writes |

## Known notes
- The crate compiles + bundles clean (verified via `npm run app:build` → `.app` + `.dmg`).
- Icons are flat-color placeholders; run `tauri icon` with a real logo before shipping installers.
- This Tauri shell (`desktop/`) supersedes the prior Electron app that previously lived here.
