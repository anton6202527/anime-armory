# Anime Arsenal — Desktop (Tauri + React)

A Tauri 2 + Vite/React/TS desktop shell for the anime-arsenal creation factory.

- **Home** → lists creative lines (n2d / ad / mv / song / novel) and their work roots.
- **Operation page** → **left = infinite canvas** (React Flow), **right = native terminal** (real PTY) + a read-only "next action" strip.
- The canvas reads `生产数据/review_ui_第N集.json` when present, else **falls back to `脚本/第N集/storyboard.json`** — so it shows clips even before 出图.

This is a **scaffold/spike**. It reuses the repo's existing `--json` contracts as its backend; it does not reimplement skill logic.

## Prerequisites

- **Node ≥ 18** (have: v26) — already used; `npm install` done.
- **Rust toolchain** (NOT installed yet) — required to build the Tauri shell:
  ```sh
  curl --proto '=https' --tlsv1.2 https://sh.rustup.rs -sSf | sh
  # then restart the shell so ~/.cargo/bin is on PATH
  rustc --version   # verify
  ```
  macOS also needs Xcode Command Line Tools (`xcode-select --install`). Tauri uses the system WebKit — no extra webview download on macOS.

## Run

```sh
cd desktop-tauri
npm install                 # done (frontend deps)
npm run app:dev             # = tauri dev: builds Rust, launches the app, hot-reloads the React side
```
First `tauri dev` compiles the Rust crate (a few minutes once). The default workspace is `/Users/wesley/learn/anime-arsenal` — change it via the "切换工作区…" button (uses the native folder picker).

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
  pages/Operation.tsx        left view / right terminal + episode switcher
  views/registry.tsx         per-line view registry: canvas | files(novel) | audio(song)
  components/CanvasPane.tsx   React Flow: clip nodes + 接力链/seam edges
  components/ClipNode.tsx     clip card: frame thumb, rhythm/duration chips, QA badges
  components/TerminalPane.tsx xterm.js ↔ PTY events
  components/NextActionStrip  run.py next --json → headline + copyable command
  api.ts / types.ts          Tauri invoke wrappers + media-URL helper + shared types
src-tauri/src/
  pty.rs                     portable-pty sessions → base64 over `pty-data` / `pty-exit` events
  media.rs                   127.0.0.1 static server, /media?path=…  (HTTP range for MP4)
  commands.rs                scan_workspace · read_canvas (review_ui→storyboard fallback) · read_next_action
  main.rs                    Tauri builder, command registry, state, dialog plugin
```

### Backend contracts reused (never reparses markdown)
- `read_canvas` → `review_ui_第N集.json` (`clips[]`/`seams[]`/`qa_flags[]`) → fallback `storyboard.json` (`clips[].id/label/duration/scene/rhythm/template/continuity.transition/firstframe_png`).
- `read_next_action` → shells `skills/n2d/run.py next <root> <ep> --json`.
- `scan_workspace` → maps lines to product dirs (制漫剧/拍广告/制MV/写歌/写小说) and lists work roots (`_进度.md` = has progress).

## Implemented vs stubbed (v1)

| Piece | Status |
|---|---|
| Tauri shell + Vite/React/TS | ✅ scaffolded, frontend builds clean |
| Native terminal (portable-pty ↔ xterm) | ✅ written (needs Rust to run) |
| Canvas (React Flow) from review_ui/storyboard | ✅ shows 本宫 第1集 13 clips via storyboard fallback |
| NextAction strip (run.py next --json) | ✅ |
| Media server (range requests) | ✅ images now; video when 出视频 exists |
| Home launcher + folder picker | ✅ |
| novel view (file tree) | ⛔ stub |
| song view (waveform/takes) | ⛔ stub |
| File-watch live refresh | ⛔ TODO (add `notify` crate → emit → re-pull canvas) |
| Interactive canvas editing | ⛔ TODO (v1 is display-only) |

## Known notes
- Rust code is unverified-compiled here (no cargo in this env). The first `tauri dev` is the real check.
- Icons are flat-color placeholders; run `tauri icon` with a real logo before shipping installers.
- The existing Electron app under `../desktop/` is the prior approach; this `desktop-tauri/` is the new direction.
