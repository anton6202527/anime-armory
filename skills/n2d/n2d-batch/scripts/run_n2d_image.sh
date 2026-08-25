#!/usr/bin/env bash
# Safe wrapper for n2d-batch image tasks.
#
# Required:
#   bash skills/n2d/n2d-batch/scripts/run_n2d_image.sh <work-root> <episode>
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
REPO_DIR="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

set +e
python3 "$REPO_DIR/skills/n2d/n2d-dashboard/scripts/dashboard.py" gate "$ROOT" "$EP" --stage image_preflight
PREFLIGHT_CODE=$?
set -e

if [[ "$PREFLIGHT_CODE" -ne 0 ]]; then
  if [[ "${N2D_REASON:-}" == "rerun" && -n "${N2D_AFFECTED_SHOTS:-}" ]]; then
    echo "image_preflight reported blockers; continuing because this is a targeted image rerun for: ${N2D_AFFECTED_SHOTS}" >&2
  else
    exit "$PREFLIGHT_CODE"
  fi
fi

if [[ -z "${N2D_IMAGE_COMMAND:-}" ]]; then
  echo "N2D_IMAGE_COMMAND is required for image generation. Refusing to guess an image backend or paid batch." >&2
  echo "Example: N2D_IMAGE_COMMAND='python3 my_image_runner.py \"\$N2D_ROOT\" \"\$N2D_EPISODE\"' bash $0 \"$ROOT\" \"$EP\"" >&2
  exit 2
fi

# A batch invocation must carry the complete producer-owned paid-boundary expectation.  This
# wrapper is the only supported indirection and must preserve it into the direct producer.
if [[ -n "${N2D_TASK_ID:-}${N2D_IDEMPOTENCY_KEY:-}${N2D_STAGE:-}" ]]; then
  if [[ -z "${N2D_EXPECTED_PAID_REQUESTS_JSON:-}" || \
        -z "${N2D_EXPECTED_PAID_REQUESTS_DIGEST:-}" || \
        -z "${N2D_EXPECTED_AUTHORIZATION_DIGEST:-}" ]]; then
    echo "Batch paid-execution markers are present but the canonical paid expectation is incomplete." >&2
    exit 2
  fi
fi

export N2D_ROOT="$ROOT"
export N2D_EPISODE="$EP"
export N2D_STAGE="image"

# Avoid a login shell: profile startup code is outside the authorized argv/environment contract.
bash -c "$N2D_IMAGE_COMMAND"

python3 "$REPO_DIR/skills/n2d/n2d-dashboard/scripts/dashboard.py" gate "$ROOT" "$EP" --stage image
