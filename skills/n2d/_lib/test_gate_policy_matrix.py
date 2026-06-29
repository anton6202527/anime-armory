from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import gate_policy_matrix as gpm


def test_gate_policy_matrix_covers_all_gate_stages() -> None:
    assert gpm.validate_matrix() == []
    payload = gpm.registry_payload()
    assert payload["errors"] == []
    assert "image_preflight" in payload["stages"]


def test_gate_policy_family_maps_preflight_to_production_family() -> None:
    assert gpm.family_for_stage("image_preflight") == "image"
    assert gpm.family_for_stage("video_preflight") == "video"
