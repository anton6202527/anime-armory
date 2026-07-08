#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DESKTOP=1
RUN_VSCODE=1
DESKTOP_ARGS=()

usage() {
  cat <<'EOF'
Usage: scripts/sync_bundles.sh [--desktop-only|--vscode-only] [--demo|--demos]

Synchronize bundled skill snapshots and 创作区 usage manuals into:
  - vscode-extension/assets/
  - desktop/src-tauri/resources/

The destination directories are generated artifacts and are intentionally gitignored.
VS Code also refreshes vscode-extension/创作区/使用手册.md files for the bundled seed work root.
--demo adds lightweight desktop sample references only; it does not bundle full demo payloads.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --desktop-only)
      RUN_VSCODE=0
      ;;
    --vscode-only)
      RUN_DESKTOP=0
      ;;
    --demo|--demos|--with-demos)
      DESKTOP_ARGS+=(--demo)
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [[ "$RUN_VSCODE" == "1" ]]; then
  (cd "$ROOT/vscode-extension" && npm run sync-assets)
fi

if [[ "$RUN_DESKTOP" == "1" ]]; then
  if [[ "${#DESKTOP_ARGS[@]}" -gt 0 ]]; then
    (cd "$ROOT/desktop" && npm run sync-skills -- "${DESKTOP_ARGS[@]}")
  else
    (cd "$ROOT/desktop" && npm run sync-skills)
  fi
fi
