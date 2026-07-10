#!/usr/bin/env python3
"""Build a machine-readable consistency threshold registry.

The registry is the production-facing view of three inputs:
- conservative default policy rows;
- golden-set threshold calibration (`consistency_threshold_calibration.json`);
- human review calibration recommendations (`consistency_threshold_recommendations.json`).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


KIND = "n2d_consistency_threshold_registry"
VERSION = 2

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import detector_reliability  # noqa: E402

DEFAULT_ROWS = [
    {
        "dimension": "character_consistency",
        "stage": "image",
        "backend": "any",
        "style": "any",
        "threshold_floor": None,
        "evidence_status": "default_policy_only",
        "signoff_policy": "human_review_required_when_machine_uncertain",
        "detector_kind": "numeric",
    },
    {
        "dimension": "outfit_consistency",
        "stage": "image",
        "backend": "any",
        "style": "any",
        "threshold_floor": None,
        "evidence_status": "default_policy_only",
        "signoff_policy": "human_review_required_when_machine_uncertain",
        "detector_kind": "hybrid",
    },
    {
        "dimension": "style_consistency",
        "stage": "image",
        "backend": "any",
        "style": "any",
        "threshold_floor": None,
        "evidence_status": "default_policy_only",
        "signoff_policy": "human_review_required_when_machine_uncertain",
        "detector_kind": "numeric",
    },
    {
        "dimension": "temporal_consistency",
        "stage": "video",
        "backend": "any",
        "style": "any",
        "threshold_floor": None,
        "evidence_status": "default_policy_only",
        "signoff_policy": "human_review_required_when_machine_uncertain",
        "detector_kind": "numeric",
    },
    {"dimension": "scene_geometry_consistency", "stage": "image", "backend": "any", "style": "any", "threshold_floor": None, "evidence_status": "default_policy_only", "signoff_policy": "human_review_required_when_machine_uncertain", "detector_kind": "hybrid"},
    {"dimension": "prop_state_consistency", "stage": "image", "backend": "any", "style": "any", "threshold_floor": None, "evidence_status": "default_policy_only", "signoff_policy": "human_review_required_when_machine_uncertain", "detector_kind": "vlm"},
    {"dimension": "state_pixel_presence", "stage": "image", "backend": "any", "style": "any", "threshold_floor": None, "evidence_status": "default_policy_only", "signoff_policy": "vlm_warn_then_human_confirmation", "detector_kind": "vlm"},
    {"dimension": "seam_continuity", "stage": "video", "backend": "any", "style": "any", "threshold_floor": None, "evidence_status": "default_policy_only", "signoff_policy": "human_review_required_until_calibrated", "detector_kind": "numeric"},
    {"dimension": "intra_clip_identity", "stage": "video", "backend": "any", "style": "any", "threshold_floor": None, "evidence_status": "default_policy_only", "signoff_policy": "human_review_required_until_calibrated", "detector_kind": "numeric"},
    {"dimension": "anchor_adherence", "stage": "video", "backend": "any", "style": "any", "threshold_floor": None, "evidence_status": "default_policy_only", "signoff_policy": "human_review_required_until_calibrated", "detector_kind": "numeric"},
    {"dimension": "motion_physics", "stage": "video", "backend": "any", "style": "any", "threshold_floor": None, "evidence_status": "default_policy_only", "signoff_policy": "vlm_warn_then_human_confirmation", "detector_kind": "vlm"},
    {"dimension": "lip_sync", "stage": "video", "backend": "any", "style": "any", "threshold_floor": None, "evidence_status": "default_policy_only", "signoff_policy": "human_review_required_until_calibrated", "detector_kind": "numeric"},
    {"dimension": "audio_sync", "stage": "compose", "backend": "any", "style": "any", "threshold_floor": None, "evidence_status": "default_policy_only", "signoff_policy": "deterministic_timing_plus_human_spotcheck", "detector_kind": "deterministic"},
    {"dimension": "overlay_text_integrity", "stage": "compose", "backend": "any", "style": "any", "threshold_floor": None, "evidence_status": "default_policy_only", "signoff_policy": "deterministic_contract_plus_ocr_review", "detector_kind": "contract"},
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _first_existing(root: Path, names: Sequence[str]) -> Path:
    for rel in names:
        path = root / rel
        if path.is_file():
            return path
    return root / names[0]


def calibration_path(root: Path) -> Path:
    return _first_existing(
        root,
        (
            "生产数据/consistency_threshold_calibration.json",
            "设定库/consistency_threshold_calibration.json",
        ),
    )


def recommendations_path(root: Path) -> Path:
    return _first_existing(
        root,
        (
            "生产数据/consistency_threshold_recommendations.json",
            "设定库/consistency_threshold_recommendations.json",
        ),
    )


def registry_path(root: Path) -> Path:
    return root / "生产数据" / "consistency_threshold_registry.json"


def _row_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str]:
    return (
        str(row.get("dimension") or "").strip(),
        str(row.get("stage") or "any").strip() or "any",
        str(row.get("backend") or "any").strip() or "any",
        str(row.get("style") or "any").strip() or "any",
    )


def _stage_for_dimension(dim: str) -> str:
    low = str(dim or "").lower()
    if any(key in low for key in ("temporal", "motion", "video", "lip", "audio")):
        return "video"
    return "image"


def _evidence_status(status: str) -> str:
    if status in {"separable", "overlap"}:
        return "calibrated"
    if status == "insufficient_samples":
        return "insufficient_samples"
    return status or "unknown"


def _source_rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def build_registry(root: str) -> Dict[str, Any]:
    root_path = Path(root)
    rows: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    for row in DEFAULT_ROWS:
        item = dict(row)
        item["source"] = "default_policy"
        rows[_row_key(item)] = item

    cal_path = calibration_path(root_path)
    calibration = _load_json(cal_path)
    for cal in calibration.get("calibrations") or []:
        if not isinstance(cal, dict):
            continue
        dim = str(cal.get("dimension") or cal.get("dim") or "").strip()
        if not dim:
            continue
        item = {
            "dimension": dim,
            "stage": str(cal.get("stage") or _stage_for_dimension(dim)),
            "backend": str(cal.get("backend") or "any"),
            "style": str(cal.get("style") or "any"),
            "threshold_floor": cal.get("recommended_floor"),
            "evidence_status": _evidence_status(str(cal.get("status") or "")),
            "calibration_status": cal.get("status"),
            "pass_n": cal.get("pass_n"),
            "fail_n": cal.get("fail_n"),
            "recognizers": cal.get("recognizers") or [],
            "detector_kind": str(cal.get("detector_kind") or "numeric"),
            "auto_block_eligible": bool(cal.get("auto_block_eligible")),
            "calibration_tier": cal.get("calibration_tier") or "exploratory",
            "balanced_accuracy": cal.get("balanced_accuracy"),
            "confusion": cal.get("confusion") or {},
            "source": _source_rel(root_path, cal_path),
            "signoff_policy": (
                "machine_threshold_plus_human_spotcheck"
                if bool(cal.get("auto_block_eligible"))
                else "human_review_required_until_more_golden_samples"
            ),
        }
        rows[_row_key(item)] = item

    rec_path = recommendations_path(root_path)
    recommendations = _load_json(rec_path)
    for rec in recommendations.get("recommendations") or []:
        if not isinstance(rec, dict):
            continue
        dim = str(rec.get("dimension") or rec.get("dim") or "").strip()
        if not dim:
            continue
        matching = [key for key in rows if key[0] == dim]
        if not matching:
            item = {
                "dimension": dim,
                "stage": _stage_for_dimension(dim),
                "backend": "any",
                "style": "any",
                "threshold_floor": None,
                "evidence_status": "recommendation_only",
                "source": _source_rel(root_path, rec_path),
                "signoff_policy": "human_review_required_until_calibrated",
            }
            rows[_row_key(item)] = item
            matching = [_row_key(item)]
        for key in matching:
            rows[key]["production_escalation"] = {
                "direction": rec.get("direction"),
                "counts": rec.get("counts") or {},
                "suggested_action": rec.get("suggested_action") or "",
                "source": _source_rel(root_path, rec_path),
            }
            if rows[key].get("evidence_status") == "default_policy_only":
                rows[key]["evidence_status"] = "recommendation_pending_calibration"

    row_list = sorted(rows.values(), key=lambda r: _row_key(r))
    for row in row_list:
        row.setdefault("detector_kind", "numeric")
        row.setdefault("auto_block_eligible", False)
        row["enforcement"] = detector_reliability.registry_enforcement(row)
    return {
        "kind": KIND,
        "version": VERSION,
        "root": root,
        "generated_at": now_iso(),
        "inputs": {
            "calibration": _source_rel(root_path, cal_path) if cal_path.is_file() else "",
            "recommendations": _source_rel(root_path, rec_path) if rec_path.is_file() else "",
        },
        "rows": row_list,
        "coherence_issues": coherence_issues(row_list),
    }


def coherence_issues(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Cross-row sanity on the assembled floors. A per-backend floor that is LOOSER
    (numerically lower) than the global `backend="any"` floor for the same
    (dimension, stage) is only legitimate when backed by golden-set calibration —
    otherwise it silently weakens the gate for that backend (掣肘四：缺单调校验，
    seedance=0.40 与 any=0.60 共存却无人察觉). Returns a list of issue dicts; empty = coherent.

    Pure function over assembled rows (no IO)."""
    issues: List[Dict[str, Any]] = []
    # Global floor per (dimension, stage) from the backend="any" rows.
    global_floor: Dict[Tuple[str, str], float] = {}
    for row in rows:
        if str(row.get("backend") or "any") != "any":
            continue
        fl = row.get("threshold_floor")
        if isinstance(fl, (int, float)):
            global_floor[(str(row.get("dimension")), str(row.get("stage") or "any"))] = float(fl)
    for row in rows:
        backend = str(row.get("backend") or "any")
        if backend == "any":
            continue
        fl = row.get("threshold_floor")
        if not isinstance(fl, (int, float)):
            continue
        gkey = (str(row.get("dimension")), str(row.get("stage") or "any"))
        gfloor = global_floor.get(gkey)
        if gfloor is None or float(fl) >= gfloor:
            continue
        calibrated = str(row.get("evidence_status") or "") == "calibrated"
        issues.append({
            "dimension": row.get("dimension"),
            "stage": row.get("stage"),
            "backend": backend,
            "backend_floor": float(fl),
            "global_floor": gfloor,
            "severity": "warn" if calibrated else "block",
            "evidence_status": row.get("evidence_status"),
            "message": (
                f"{backend} 后端 floor {float(fl):.3f} 低于全局 {gfloor:.3f}"
                + ("（有 golden-set 标定背书，记录即可）" if calibrated
                   else "——无标定背书的放松会静默削弱该后端的闸门，需补标定或对齐全局。")
            ),
        })
    return issues


def write_registry(root: str) -> str:
    path = registry_path(Path(root))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_registry(root), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="build n2d consistency threshold registry")
    ap.add_argument("root")
    ap.add_argument("--check", action="store_true", help="exit non-zero if no calibrated/recommended rows exist")
    args = ap.parse_args(argv)
    path = write_registry(args.root)
    payload = _load_json(Path(path))
    print(path)
    blocking = [i for i in payload.get("coherence_issues", []) if i.get("severity") == "block"]
    for issue in blocking:
        print(f"  [不连贯] {issue.get('message')}")
    if args.check:
        if blocking:
            return 2  # 无标定背书的后端 floor 放松：闸门被静默削弱，须修
        useful = [
            row for row in payload.get("rows", [])
            if row.get("evidence_status") not in {"default_policy_only"}
        ]
        return 0 if useful else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
