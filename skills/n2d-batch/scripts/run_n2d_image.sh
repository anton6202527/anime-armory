#!/usr/bin/env bash
# Safe wrapper for n2d-batch image tasks.
#
# Required:
#   bash skills/n2d-batch/scripts/run_n2d_image.sh <work-root> <episode>
#
# Optional environment:
#   N2D_IMAGE_COMMAND='python3 ... "$N2D_ROOT" "$N2D_EPISODE"'
#
# The image stage often involves an agent/platform-specific generator. This
# wrapper standardizes preflight and refuses to spend credits unless the real
# image command is explicitly configured.

set -euo pipefail

ROOT="${1:?work root required}"
EP="${2:?episode required}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

python3 "$REPO_DIR/skills/n2d-dashboard/scripts/dashboard.py" gate "$ROOT" "$EP" --stage image_preflight

if [[ -z "${N2D_IMAGE_COMMAND:-}" ]]; then
  echo "N2D_IMAGE_COMMAND is required for image generation. Refusing to guess an image backend or paid batch." >&2
  echo "Example: N2D_IMAGE_COMMAND='python3 my_image_runner.py \"\$N2D_ROOT\" \"\$N2D_EPISODE\"' bash $0 \"$ROOT\" \"$EP\"" >&2
  exit 2
fi

export N2D_ROOT="$ROOT"
export N2D_EPISODE="$EP"
export N2D_STAGE="image"

bash -lc "$N2D_IMAGE_COMMAND"
