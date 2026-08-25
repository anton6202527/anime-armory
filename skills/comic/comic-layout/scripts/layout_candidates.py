#!/usr/bin/env python3
"""Generate and rank multiple deterministic Comic layout candidates."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("comic_layout_candidate_builder", HERE / "build_layout.py")
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(builder)


PARAMETERS = (
    {"candidate_id": "balanced", "max_segment_height": 16000, "gutter": 140},
    {"candidate_id": "fast_read", "max_segment_height": 12000, "gutter": 96},
    {"candidate_id": "dramatic_pause", "max_segment_height": 18000, "gutter": 190},
)


def _sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def score(layout: Mapping[str, Any]) -> dict[str, Any]:
    panels = [panel for segment in layout.get("segments") or [] for panel in segment.get("panels") or [] if isinstance(panel, Mapping)]
    eye_path = sum(bool(panel.get("eye_flow_entry") or panel.get("eye_flow_exit")) for panel in panels)
    bubble_slots = sum(len(panel.get("bubble_slots") or []) for panel in panels)
    overflow_risk = sum(len(panel.get("bubble_slots") or []) > 4 for panel in panels)
    safe_area = sum(all(int(panel.get(key) or 0) >= 0 for key in ("x", "y", "w", "h")) for panel in panels)
    page_turns = sum(bool(panel.get("page_turn_hook")) for panel in panels)
    shapes = [str(panel.get("panel_shape") or "standard") for panel in panels]
    repetition = max(0, len(shapes) - len(set(shapes)))
    total = 50 + eye_path * 2 + safe_area + page_turns * 3 - overflow_risk * 8 - repetition
    return {
        "total": total, "eye_path_contracts": eye_path, "bubble_slot_count": bubble_slots,
        "bubble_overflow_risk": overflow_risk, "safe_area_panels": safe_area,
        "page_turn_hooks": page_turns, "repeated_composition_penalty": repetition,
    }


def build(root: Path, chapter: str) -> dict[str, Any]:
    name = builder.load_json(root / "排版" / chapter / "name_board.json")
    protected = any(str(page.get("spread_id") or "").strip() for page in name.get("pages") or [] if isinstance(page, Mapping))
    candidates = []
    for params in PARAMETERS:
        layout = builder.build_layout(root, chapter, params["max_segment_height"], params["gutter"])
        candidates.append({**params, "layout_sha256": _sha(layout), "score": score(layout), "layout": layout})
    candidates.sort(key=lambda row: (-row["score"]["total"], row["candidate_id"]))
    return {
        "schema_version": 1, "kind": "comic_layout_candidates", "chapter": chapter,
        "input_bindings": {
            "panel_script_sha256": builder.sha256_file(root / "脚本" / chapter / "panel_script.json"),
            "name_board_sha256": builder.sha256_file(root / "排版" / chapter / "name_board.json"),
            "settings_sha256": builder.sha256_file(root / "_设置.md"),
        },
        "protected_complex_layout": protected,
        "selection_policy": "human_required_for_spreads" if protected else "highest_deterministic_score_may_apply_under_delegated_editorial_policy",
        "recommended_candidate_id": candidates[0]["candidate_id"], "candidates": candidates,
    }


def write(root: Path, chapter: str, payload: Mapping[str, Any], *, apply_best: bool) -> tuple[Path, Path | None]:
    path = root / "排版" / chapter / "layout_candidates.json"; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    selection = None
    if apply_best:
        if payload.get("protected_complex_layout"):
            raise ValueError("spread/complex layout is protected and cannot auto-apply")
        best = (payload.get("candidates") or [])[0]
        selection = path.with_name("layout_candidate_selection.json")
        record = {
            "schema_version": 1, "kind": "comic_layout_candidate_selection", "chapter": chapter,
            "candidate_id": best["candidate_id"], "max_segment_height": best["max_segment_height"], "gutter": best["gutter"],
            "layout_sha256": best["layout_sha256"], "score": best["score"],
            "input_bindings": payload["input_bindings"], "human_signoff": False,
        }
        selection.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path, selection


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("project_root"); parser.add_argument("--chapter", default="第1话"); parser.add_argument("--apply-best", action="store_true"); parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv); root = Path(args.project_root).expanduser().resolve()
    try: payload = build(root, args.chapter); outputs = write(root, args.chapter, payload, apply_best=args.apply_best)
    except (ValueError, builder.LayoutError) as exc: print(f"[err] {exc}"); return 2
    if args.json: print(json.dumps({"report": payload, "outputs": [str(item) for item in outputs if item]}, ensure_ascii=False, indent=2))
    else: print(f"recommended={payload['recommended_candidate_id']} protected={payload['protected_complex_layout']}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
