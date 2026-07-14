#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import scan


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_progress(root: Path, finishing_label: str = "原稿收尾", *, review: str = "✅") -> None:
    (root / "_设置.md").write_text("- 传统原稿流程：启用\n", encoding="utf-8")
    (root / "_进度.md").write_text(
        f"""# 进度

| 话 | 源本/企划 | 漫画脚本 | 缩略分镜 | 页面排版 | {finishing_label} | 出图包 | 出图 | 嵌字合成 | 审查 |
|---|---|---|---|---|---|---|---|---|---|
| 第1话 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | {review} |
""",
        encoding="utf-8",
    )


def scaffold_script_contract(root: Path) -> None:
    contract = {
        "chapter": "第1话",
        "chapter_type": "one_shot",
        "format_profile": "vertical_serial",
        "source_mode": "original",
        "source_spans": [],
        "reader_promise": "promise",
        "core_conflict": "conflict",
        "turning_point": "turn",
        "payoff": "payoff",
        "ending_mode": "complete_closure",
        "budget": {"unit": "panels", "target": 1, "soft_range": [1, 2]},
        "status": "confirmed",
    }
    blueprint = {"kind": "comic_split_blueprint", "version": 2, "status": "confirmed", "chapters": [contract]}
    strategy = {"kind": "comic_adaptation_strategy", "version": 2, "status": "confirmed", "adaptation_boundary": "owned"}
    season = {"kind": "comic_season_arc", "version": 2, "status": "confirmed", "chapters": [{"chapter": "第1话"}]}
    write_json(root / "脚本" / "split_blueprint.json", blueprint)
    write_json(root / "开发包" / "adaptation_strategy.json", strategy)
    write_json(root / "开发包" / "season_arc.json", season)
    panel = {
        "chapter_contract": {"chapter_contract_sha256": scan.canonical_sha256(contract), "status": "confirmed"},
        "visual_contract": {"style_baseline": "ink", "scene_anchors": {}},
        "panels": [],
    }
    write_json(root / "脚本" / "第1话" / "panel_script.json", panel)
    write_json(
        root / "开发包" / "signoff.json",
        {
            "reviewer": "editor",
            "role": "story_editor",
            "time": "2026-07-14T00:00:00Z",
            "file_sha256": {
                "adaptation_strategy": scan.sha256_file(root / "开发包" / "adaptation_strategy.json"),
                "season_arc": scan.sha256_file(root / "开发包" / "season_arc.json"),
                "split_blueprint": scan.sha256_file(root / "脚本" / "split_blueprint.json"),
            },
        },
    )


def write_gate(root: Path, stage: str, *, verdict: str = "pass") -> None:
    report_path = root / "生产数据" / f"comic_gate_{stage}_第1话.json"
    fingerprint = scan.stage_inputs_fingerprint(root, "第1话", stage)
    report = {
        "kind": "comic_gate",
        "chapter": "第1话",
        "stage": stage,
        "verdict": verdict,
        "inputs_fingerprint": fingerprint,
        "summary": {"block_count": 1 if verdict == "block" else 0},
        "findings": [],
    }
    write_json(report_path, report)
    write_json(
        root / "生产数据" / "gate_receipts" / f"{stage}_第1话.json",
        {
            "kind": "comic_gate_receipt",
            "chapter": "第1话",
            "stage": stage,
            "verdict": verdict,
            "execution_authorized": verdict != "block",
            "inputs_fingerprint_sha256": fingerprint["sha256"],
            "report_path": str(report_path.relative_to(root)),
            "report_sha256": scan.sha256_file(report_path),
        },
    )


def test_finishing_column_aliases_are_both_recognized() -> None:
    assert scan.row_stage_state({"原稿收尾": "✅"}, "原稿收尾") == "done"
    assert scan.row_stage_state({"传统收尾": "✅"}, "原稿收尾") == "done"


def test_progress_claim_does_not_hide_missing_chapter_contract(tmp_path: Path) -> None:
    write_progress(tmp_path)

    front = scan.summarize_project(tmp_path)["fronts"][0]

    assert front["complete"] is False
    assert front["blocker_code"] == "split_blueprint_missing_or_invalid"
    assert front["next_skill"] == "comic-script"
    assert front["progress_claim"]["next_stage"] == "完成"


def test_stale_development_signoff_is_reported_before_downstream(tmp_path: Path) -> None:
    write_progress(tmp_path, review="")
    scaffold_script_contract(tmp_path)
    strategy_path = tmp_path / "开发包" / "adaptation_strategy.json"
    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    strategy["adaptation_boundary"] = "changed"
    write_json(strategy_path, strategy)

    front = scan.summarize_project(tmp_path)["fronts"][0]

    assert front["blocker_code"] == "development_pack_signoff_stale"
    assert front["next_skill"] == "comic-script"


def test_missing_script_gate_routes_to_review_after_contracts_are_current(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("- 传统原稿流程：启用\n", encoding="utf-8")
    (tmp_path / "_进度.md").write_text(
        "# 进度\n\n"
        "| 话 | 源本/企划 | 漫画脚本 | 缩略分镜 | 页面排版 | 原稿收尾 | 出图包 | 出图 | 嵌字合成 | 审查 |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| 第1话 | ✅ | ✅ | | | | | | | |\n",
        encoding="utf-8",
    )
    scaffold_script_contract(tmp_path)

    front = scan.summarize_project(tmp_path)["fronts"][0]

    assert front["blocker_code"] == "script_gate_receipt_missing"
    assert front["next_skill"] == "comic-review"


def test_name_draft_is_not_treated_as_completed_approval(tmp_path: Path) -> None:
    write_progress(tmp_path, review="")
    scaffold_script_contract(tmp_path)
    write_gate(tmp_path, "script")
    write_json(
        tmp_path / "排版" / "第1话" / "name_board.json",
        {"schema_version": 2, "kind": "comic_name_board", "workflow_status": "draft", "approval": {}},
    )

    front = scan.summarize_project(tmp_path)["fronts"][0]

    assert front["blocker_code"] == "name_not_approved"
    assert front["next_skill"] == "comic-name"


def test_review_marked_done_requires_current_review_receipt(tmp_path: Path) -> None:
    # Directly exercise the receipt rule: the complete table must have a
    # review receipt bound to the exact review inputs.
    write_progress(tmp_path)
    receipt_gap = scan._gate_gap(tmp_path, "第1话", "review")
    assert receipt_gap is not None
    assert receipt_gap["code"] == "review_gate_receipt_missing"
    write_gate(tmp_path, "review")
    assert scan._gate_gap(tmp_path, "第1话", "review") is None
    (tmp_path / "_设置.md").write_text("- 传统原稿流程：启用\n- 页面尺寸：1280xauto\n", encoding="utf-8")
    assert scan._gate_gap(tmp_path, "第1话", "review")["code"] == "review_gate_receipt_stale"


def test_gate_report_must_bind_same_input_fingerprint_as_receipt(tmp_path: Path) -> None:
    write_progress(tmp_path)
    write_gate(tmp_path, "review")
    report_path = tmp_path / "生产数据" / "comic_gate_review_第1话.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["inputs_fingerprint"]["sha256"] = "tampered"
    write_json(report_path, report)
    receipt_path = tmp_path / "生产数据" / "gate_receipts" / "review_第1话.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["report_sha256"] = scan.sha256_file(report_path)
    write_json(receipt_path, receipt)
    assert scan._gate_gap(tmp_path, "第1话", "review")["code"] == "review_gate_report_stale"


def test_disabling_traditional_finishing_does_not_skip_name(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("- 传统原稿流程：关闭\n", encoding="utf-8")
    (tmp_path / "_进度.md").write_text(
        "# 进度\n\n"
        "| 话 | 源本/企划 | 漫画脚本 | 缩略分镜 | 页面排版 | 原稿收尾 | 出图包 | 出图 | 嵌字合成 | 审查 |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| 第1话 | ✅ | ✅ | | | | | | | |\n",
        encoding="utf-8",
    )
    scaffold_script_contract(tmp_path)
    write_gate(tmp_path, "script")

    front = scan.summarize_project(tmp_path)["fronts"][0]

    assert front["next_stage"] == "缩略分镜"
    assert front["next_skill"] == "comic-name"


def identity_asset(asset_type: str, *, model_pack_required: bool = False) -> dict:
    return {
        "id": "CHAR_A" if asset_type == "character" else "MON_A",
        "type": asset_type,
        "model_pack_required": model_pack_required,
        "forms": {"FORM_BASE": {"id": "FORM_BASE"}},
        "outfits": {"OUTFIT_BASE": {"id": "OUTFIT_BASE"}},
        "expressions": {"EXPR_NEUTRAL": {"id": "EXPR_NEUTRAL"}},
        "states": {"STATE_BASE": {"id": "STATE_BASE"}},
        "default_binding": {
            "form_id": "FORM_BASE",
            "outfit_id": "OUTFIT_BASE",
            "expression_id": "EXPR_NEUTRAL",
            "state_id": "STATE_BASE",
        },
    }


def test_monster_model_pack_is_opt_in_but_character_is_not(tmp_path: Path) -> None:
    registry_path = tmp_path / "出图" / "共享" / "identity_registry.json"
    write_json(registry_path, {
        "schema_version": 2,
        "kind": "comic_identity_registry",
        "assets": {"MON_A": identity_asset("monster")},
    })
    assert scan._identity_gaps(tmp_path, "第1话") == []

    monster = identity_asset("monster", model_pack_required=True)
    write_json(registry_path, {"schema_version": 2, "kind": "comic_identity_registry", "assets": {"MON_A": monster}})
    assert scan._identity_gaps(tmp_path, "第1话")[0]["code"] == "model_pack_report_missing_or_invalid"

    write_json(registry_path, {
        "schema_version": 2,
        "kind": "comic_identity_registry",
        "assets": {"CHAR_A": identity_asset("character")},
    })
    assert scan._identity_gaps(tmp_path, "第1话")[0]["code"] == "model_pack_report_missing_or_invalid"


def test_non_restricted_model_pack_signoff_requires_reason_and_matching_character(tmp_path: Path) -> None:
    asset = identity_asset("character")
    asset["library_tier"] = "recurring_standard"
    write_json(tmp_path / "出图" / "共享" / "identity_registry.json", {
        "schema_version": 2, "kind": "comic_identity_registry", "assets": {"CHAR_A": asset},
    })
    write_json(tmp_path / "生产数据" / "comic_model_pack_report.json", {
        "kind": "comic_model_pack_report",
        "summary": {"needs_fix": 0, "needs_approval": 0},
        "characters": [{
            "character_id": "CHAR_A", "readiness": "ready", "model_pack_fingerprint": "fp",
            "view_evidence": [], "signoff": {"status": "current"},
        }],
    })
    write_json(tmp_path / "生产数据" / "comic_model_pack_signoffs" / "CHAR_A.json", {
        "decision": "approved", "character_id": "CHAR_A", "model_pack_fingerprint": "fp",
        "reviewer": "editor", "approved_at": "2026-07-14T00:00:00Z",
        "confirmations": {
            "same_character": True, "correct_view_labels": True, "proportions_aligned": True,
            "baseline_aligned": True, "outfit_and_markers_consistent": True, "neutral_pose_usable": True,
        },
    })
    gaps = scan._identity_gaps(tmp_path, "第1话")
    assert gaps[0]["code"] == "model_pack_signoff_identity_missing"
