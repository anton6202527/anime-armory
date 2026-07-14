#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DESKTOP=1
RUN_VSCODE=1

usage() {
  cat <<'EOF'
Usage: scripts/sync_bundles.sh [--desktop-only|--vscode-only]

Synchronize bundled skill snapshots and 创作区 usage manuals into:
  - apps/vscode-extension/assets/  (novel/n2d/comic only + one novel demo)
  - apps/desktop/resources/   (skills/manuals + R2 Demo catalog fallback)

The destination directories are generated artifacts and are intentionally gitignored.
VS Code also rebuilds apps/vscode-extension/创作区/ as three work lines; only 写小说 contains the 那妖魔是姜大人 demo.
Demo payloads are published separately with `npm run demos:publish` and are never bundled.
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
  (cd "$ROOT/apps/vscode-extension" && npm run sync-assets)
fi

if [[ "$RUN_DESKTOP" == "1" ]]; then
  node "$ROOT/tools/e2a/scripts/sync_bundle.cjs"
fi
