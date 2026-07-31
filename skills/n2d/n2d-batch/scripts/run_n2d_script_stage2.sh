#!/usr/bin/env bash
# Safe wrapper for n2d-batch script_stage2 rerun tasks.
#
# Required:
#   bash skills/n2d/n2d-batch/scripts/run_n2d_script_stage2.sh <work-root> <episode>
#
# This wrapper only refreshes deterministic script-stage artifacts and audits.
# It never calls image generation or video submission.

set -euo pipefail

ROOT="${1:?work root required}"
EP="${2:?episode required}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PYTHON="${PYTHON:-python3}"

"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/finalize_storyboard.py" "$ROOT" "$EP"
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/validate_timings.py" "$ROOT" "$EP"

"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/shot_intent.py" "$ROOT" "$EP"
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/director_camera_plan.py" "$ROOT" "$EP" --write
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/anchor_planner.py" "$ROOT" "$EP" --write

"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/story_integrity_audit.py" "$ROOT" "$EP" --write --json
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/source_adaptation_audit.py" "$ROOT" "$EP" --strict --json
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/beat_audit.py" "$ROOT" "$EP" --strict --json
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/causal_graph.py" "$ROOT" "$EP" --json
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/scene_turn_audit.py" "$ROOT" "$EP" --json
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/subtext_audit.py" "$ROOT" "$EP" --json
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/shot_grammar_audit.py" "$ROOT" "$EP" --json
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/antecedent_audit.py" "$ROOT" "$EP" --strict --json
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/setup_payoff_ledger.py" "$ROOT" --gate "$EP" --json
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/entity_schedule_audit.py" "$ROOT" "$EP" --json
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/shot_risk_audit.py" "$ROOT" "$EP" --json
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/shot_split_decision.py" "$ROOT" "$EP" --write --json
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/spectacle_contract_audit.py" "$ROOT" "$EP" --strict --json
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/spectacle_plan.py" "$ROOT" "$EP" --write --write-manifests
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/spectacle_sequence_plan.py" "$ROOT" "$EP" --write
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/spectacle_probe_pack.py" "$ROOT" "$EP" --write
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/combat_cue_apex_audit.py" "$ROOT" "$EP"
"$PYTHON" "$REPO_DIR/skills/n2d/n2d-script/scripts/combat_rhythm_audit.py" "$ROOT" "$EP"

"$PYTHON" "$REPO_DIR/skills/n2d/n2d-review/scripts/dialogue_fact_guard.py" "$ROOT" "$EP" --write --json
