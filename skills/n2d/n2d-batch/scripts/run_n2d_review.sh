#!/usr/bin/env bash
# Safe wrapper for n2d-batch review tasks.
#
# Required:
#   bash skills/n2d/n2d-batch/scripts/run_n2d_review.sh <work-root> <episode>

set -euo pipefail

ROOT="${1:?work root required}"
EP="${2:?episode required}"
THRESHOLD="${N2D_REVIEW_SCORE_THRESHOLD:-85}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

python3 "$REPO_DIR/skills/n2d/n2d-review/scripts/spectacle_video_qc.py" "$ROOT" "$EP" --write --write-sidecars
python3 "$REPO_DIR/skills/n2d/n2d-review/scripts/motion_reference_library.py" "$ROOT" "$EP" --write
python3 "$REPO_DIR/skills/n2d/n2d-dashboard/scripts/dashboard.py" gate "$ROOT" "$EP" --stage review
python3 "$REPO_DIR/skills/n2d/n2d-score/scripts/score.py" "$ROOT" "$EP" --run-checks --threshold "$THRESHOLD"
python3 "$REPO_DIR/skills/n2d/n2d-review/scripts/consistency_ledger.py" "$ROOT" "$EP"
python3 "$REPO_DIR/skills/n2d/n2d-review-ui/scripts/review_ui.py" "$ROOT" "$EP" --write --export-findings --markdown
