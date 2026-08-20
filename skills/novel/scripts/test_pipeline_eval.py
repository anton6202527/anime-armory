#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile


HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.abspath(os.path.join(HERE, "..", "_lib"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from novel_pipeline import dry_run_plan, record_human_stage_approval  # noqa: E402
from craft_profile import build_craft_contract_snapshot  # noqa: E402


CASES = os.path.join(HERE, "tests", "golden_pipeline_cases.json")


def _write_fixture(root: str, rel_path: str, value) -> None:
    path = os.path.join(root, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if isinstance(value, (dict, list)):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(value))


def _bind_dynamic_contract_snapshots(root: str) -> None:
    """Hydrate hashes that cannot be stored in a portable golden fixture."""
    path = os.path.join(root, "设定", "manuscript_map_check.json")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    payload["project_root"] = root
    payload["source_snapshot"] = build_craft_contract_snapshot(root, "genre_novel")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def test_golden_pipeline_cases_keep_next_stage_contract():
    with open(CASES, encoding="utf-8") as f:
        cases = json.load(f)
    for case in cases:
        with tempfile.TemporaryDirectory() as root:
            for rel_path, value in case["files"].items():
                _write_fixture(root, rel_path, value)
            _bind_dynamic_contract_snapshots(root)
            for stage_key in ("blueprint", "setting"):
                if stage_key in case["expected_done"]:
                    record_human_stage_approval(
                        root,
                        stage_key,
                        approved_by="golden-fixture-author",
                        note=f"golden case {case['name']}",
                    )

            plan = dry_run_plan(root)
            assert plan["next_stage"] == case["expected_next_stage"], case["name"]
            by_key = {stage["key"]: stage for stage in plan["stages"]}
            for key in case["expected_done"]:
                assert by_key[key]["status"] == "done", f"{case['name']}:{key}"
