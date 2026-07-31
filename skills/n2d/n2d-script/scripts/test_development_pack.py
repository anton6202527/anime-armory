#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import development_pack as dp  # noqa: E402
from signoff_contract import new_manifest, profile_spec, record_approval, write_manifest  # noqa: E402


def _confirm_pack(root: Path) -> None:
    dp.scaffold(root, title="测试剧")
    base = root / "开发包"
    for md_name in ("series_bible.md", "pilot_greenlight.md"):
        text = (base / md_name).read_text(encoding="utf-8")
        text = text.replace("status: draft", "status: confirmed")
        text = text.replace("待补", "已填写")
        (base / md_name).write_text(text, encoding="utf-8")
    for js_name in ("adaptation_strategy.json", "season_arc.json", "production_feasibility.json"):
        data = json.loads((base / js_name).read_text(encoding="utf-8"))
        data["status"] = "confirmed"
        blob = json.dumps(data, ensure_ascii=False).replace("待补", "已填写")
        (base / js_name).write_text(json.dumps(json.loads(blob), ensure_ascii=False, indent=2), encoding="utf-8")
    spec = profile_spec(root, "p1")
    payload = new_manifest(
        root, artifact_scope=spec["artifact_scope"], author_id="automation:n2d",
        input_paths=spec["input_paths"], evidence_paths=spec["evidence_paths"],
        required_role_groups=spec["required_role_groups"],
    )
    payload = record_approval(payload, root, reviewer_id="user:owner", reviewer_role="director", evidence_paths=spec["evidence_paths"])
    payload = record_approval(payload, root, reviewer_id="user:owner", reviewer_role="producer", evidence_paths=spec["evidence_paths"])
    write_manifest(root / spec["signoff_path"], payload)


def test_scaffold_creates_five_required_files(tmp_path: Path) -> None:
    result = dp.scaffold(tmp_path, title="测试剧")

    assert result["kind"] == dp.KIND
    for name in dp.REQUIRED_FILES:
        assert (tmp_path / "开发包" / name).exists()


def test_check_blocks_draft_pack(tmp_path: Path) -> None:
    dp.scaffold(tmp_path, title="测试剧")

    report = dp.check(tmp_path)

    assert report["status"] == "block"
    assert report["summary"]["block"] == len(dp.REQUIRED_FILES) + 1


def test_check_passes_confirmed_pack(tmp_path: Path) -> None:
    _confirm_pack(tmp_path)

    report = dp.check(tmp_path)

    assert report["status"] == "pass"
    assert report["summary"]["pass"] == len(dp.REQUIRED_FILES) + 1
