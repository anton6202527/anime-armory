#!/usr/bin/env bash
# Safe wrapper for n2d-batch compose tasks.
#
# Required:
#   bash skills/n2d-batch/scripts/run_n2d_compose.sh <work-root> <episode> [zh|en]

set -euo pipefail

ROOT="${1:?work root required}"
EP="${2:?episode required}"
LANG="${3:-${N2D_COMPOSE_LANG:-zh}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

python3 "$REPO_DIR/skills/n2d-dashboard/scripts/dashboard.py" gate "$ROOT" "$EP" --stage compose
bash "$REPO_DIR/skills/n2d-compose/compose.sh" "$ROOT" "$EP" "$LANG"
