#!/usr/bin/env python3
"""Data-backed gate policy matrix for n2d gate stages."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from n2d_schema import GATE_STAGES
except ImportError:  # pragma: no cover - package import fallback
    from .n2d_schema import GATE_STAGES


KIND = "n2d_gate_policy_matrix"
VERSION = 1
MATRIX_PATH = Path(__file__).with_name("gate_policy_matrix.json")
REQUIRED_STAGE_FIELDS = ("family", "human_boundary", "trace_policy", "required_check_groups")
POLICY_ONLY_STAGES = {"review_acceptance"}


def load_matrix(path: Optional[str] = None) -> Dict[str, Any]:
    src = Path(path) if path else MATRIX_PATH
    return json.loads(src.read_text(encoding="utf-8"))


def validate_matrix(data: Optional[Dict[str, Any]] = None) -> List[str]:
    matrix = data if data is not None else load_matrix()
    errors: List[str] = []
    if matrix.get("kind") != KIND:
        errors.append(f"kind must be {KIND}")
    if matrix.get("version") != VERSION:
        errors.append(f"version must be {VERSION}")
    stages = matrix.get("stages")
    if not isinstance(stages, dict):
        return errors + ["stages must be object"]
    expected = set(GATE_STAGES)
    got = set(stages)
    missing = sorted(expected - got)
    extra = sorted(got - expected - POLICY_ONLY_STAGES)
    if missing:
        errors.append(f"missing stage policies: {', '.join(missing)}")
    if extra:
        errors.append(f"unknown stage policies: {', '.join(extra)}")
    for stage, policy in stages.items():
        if not isinstance(policy, dict):
            errors.append(f"{stage}: policy must be object")
            continue
        for field in REQUIRED_STAGE_FIELDS:
            if field not in policy or policy.get(field) in (None, "", []):
                errors.append(f"{stage}: missing {field}")
        groups = policy.get("required_check_groups")
        if groups is not None and not isinstance(groups, list):
            errors.append(f"{stage}: required_check_groups must be list")
    return errors


def policy_for_stage(stage: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    matrix = data if data is not None else load_matrix()
    policy = (matrix.get("stages") or {}).get(stage)
    return dict(policy or {})


def family_for_stage(stage: str, *, fallback: str = "") -> str:
    return str(policy_for_stage(stage).get("family") or fallback or stage)


def registry_payload() -> Dict[str, Any]:
    matrix = load_matrix()
    return {
        "kind": KIND,
        "version": VERSION,
        "stages": sorted((matrix.get("stages") or {}).keys()),
        "errors": validate_matrix(matrix),
    }
