#!/usr/bin/env bash
# Safe wrapper for n2d-batch video tasks.
#
# Required:
#   bash skills/n2d-batch/scripts/run_n2d_video.sh <work-root> <episode>
#
# Optional environment:
#   N2D_VIDEO_RANGE=06-10          batch range to prepare/submit
#   N2D_VIDEO_BACKEND=dreamina
#   N2D_VIDEO_RESOLUTION=720p
#   N2D_VIDEO_MODEL_VERSION=3.0
#   N2D_VIDEO_AUTO_SUBMIT=1        submit every prepared clip (costly)
#   N2D_VIDEO_SUBMIT_ONE=Clip_06   submit one clip (costly)

set -euo pipefail

ROOT="${1:?work root required}"
EP="${2:?episode required}"
RANGE="${N2D_VIDEO_RANGE:-}"
BACKEND="${N2D_VIDEO_BACKEND:-dreamina}"
RESOLUTION="${N2D_VIDEO_RESOLUTION:-720p}"
MODEL_VERSION="${N2D_VIDEO_MODEL_VERSION:-3.0}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

if [[ -z "$RANGE" ]]; then
  echo "N2D_VIDEO_RANGE is required, e.g. 06-10. Refusing to guess a paid video batch." >&2
  exit 2
fi

python3 "$REPO_DIR/skills/n2d-identity/scripts/identity.py" "$ROOT" --write
python3 "$REPO_DIR/skills/n2d-model-router/scripts/router.py" "$ROOT" "$EP" --write
python3 "$REPO_DIR/skills/n2d-dashboard/scripts/dashboard.py" gate "$ROOT" "$EP" --stage video_preflight

MANIFEST="$(
  python3 "$REPO_DIR/skills/n2d-video/scripts/video_runner.py" prepare "$ROOT" "$EP" \
    --range "$RANGE" \
    --backend "$BACKEND" \
    --resolution "$RESOLUTION" \
    --model-version "$MODEL_VERSION" \
  | sed -n '1p'
)"

echo "video manifest: $MANIFEST"

if [[ "${N2D_VIDEO_AUTO_SUBMIT:-}" == "1" ]]; then
  python3 - "$ROOT" "$MANIFEST" "$REPO_DIR" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

root, manifest, repo_dir = sys.argv[1], sys.argv[2], sys.argv[3]
data = json.loads(Path(manifest).read_text(encoding="utf-8"))
for item in data.get("items", []):
    subprocess.run([
        sys.executable,
        str(Path(repo_dir) / "skills/n2d-video/scripts/video_runner.py"),
        "submit",
        root,
        manifest,
        "--clip",
        item["clip"],
    ], check=True)
PY
elif [[ -n "${N2D_VIDEO_SUBMIT_ONE:-}" ]]; then
  python3 "$REPO_DIR/skills/n2d-video/scripts/video_runner.py" submit "$ROOT" "$MANIFEST" --clip "$N2D_VIDEO_SUBMIT_ONE"
else
  echo "Prepared only. Set N2D_VIDEO_AUTO_SUBMIT=1 or N2D_VIDEO_SUBMIT_ONE=Clip_XX to spend credits."
fi
