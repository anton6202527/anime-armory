#!/usr/bin/env bash
# Safe wrapper for n2d-batch compose tasks.
#
# Required:
#   bash skills/n2d/n2d-batch/scripts/run_n2d_compose.sh <work-root> <episode> [zh|en]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
if [[ "${N2D_WRAPPER_SELF_CHECK:-}" == "1" ]]; then
  [[ -f "$REPO_DIR/skills/n2d/run.py" ]] || { echo "invalid repository root: $REPO_DIR" >&2; exit 2; }
  printf '%s\n' "$REPO_DIR"
  exit 0
fi
ROOT="${1:?work root required}"
EP="${2:?episode required}"
LANG="${3:-${N2D_COMPOSE_LANG:-zh}}"

python3 "$REPO_DIR/skills/n2d/n2d-model-router/scripts/mouth_detect.py" "$ROOT" "$EP" --write --json >/dev/null || true
python3 "$REPO_DIR/skills/n2d/n2d-video/scripts/materialize_shared_clips.py" "$ROOT" "$EP"
python3 "$REPO_DIR/skills/n2d/n2d-dashboard/scripts/dashboard.py" gate "$ROOT" "$EP" --stage compose
bash "$REPO_DIR/skills/n2d/n2d-compose/compose.sh" "$ROOT" "$EP" "$LANG"
