from __future__ import annotations

import json
from pathlib import Path

import continuity_audit


def write_chapter(root: Path, chapter: str, contract: dict) -> None:
    path = root / "脚本" / chapter / "panel_script.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"chapter_contract": contract, "panels": [{"panel_id": "P001"}]}, ensure_ascii=False),
        encoding="utf-8",
    )


def base_contract(*, location: str = "home", exit_location: str = "home", delta: list | None = None) -> dict:
    return {
        "entry_state": {"entities": {"CHAR_A": {"location": location, "outfit_id": "OUTFIT_A"}}},
        "continuity_delta": delta or [],
        "exit_state": {"entities": {"CHAR_A": {"location": exit_location, "outfit_id": "OUTFIT_A"}}},
    }


def test_valid_transition_and_next_chapter_handoff(tmp_path: Path) -> None:
    transition = [{
        "entity_id": "CHAR_A", "field": "location", "from": "home", "to": "street",
        "panel_id": "P001", "reason": "角色出门",
    }]
    write_chapter(tmp_path, "第1话", base_contract(exit_location="street", delta=transition))
    write_chapter(tmp_path, "第2话", base_contract(location="street", exit_location="street"))
    report = continuity_audit.audit(tmp_path)
    assert report["verdict"] == "pass"


def test_unexplained_exit_change_blocks(tmp_path: Path) -> None:
    write_chapter(tmp_path, "第1话", base_contract(exit_location="street"))
    report = continuity_audit.audit(tmp_path)
    assert {item["code"] for item in report["findings"]} == {"chapter_exit_state_unexplained"}


def test_next_chapter_state_regression_blocks(tmp_path: Path) -> None:
    transition = [{
        "entity_id": "CHAR_A", "field": "location", "from": "home", "to": "street",
        "panel_id": "P001", "reason": "角色出门",
    }]
    write_chapter(tmp_path, "第1话", base_contract(exit_location="street", delta=transition))
    write_chapter(tmp_path, "第2话", base_contract(location="home", exit_location="home"))
    report = continuity_audit.audit(tmp_path)
    assert "chapter_entry_state_mismatch" in {item["code"] for item in report["findings"]}


def test_transition_requires_existing_panel(tmp_path: Path) -> None:
    transition = [{
        "entity_id": "PROP_SWORD", "field": "condition", "from": "intact", "to": "broken",
        "panel_id": "P999", "reason": "战斗中折断",
    }]
    contract = {
        "entry_state": {"entities": {"PROP_SWORD": {"condition": "intact"}}},
        "continuity_delta": transition,
        "exit_state": {"entities": {"PROP_SWORD": {"condition": "broken"}}},
    }
    write_chapter(tmp_path, "第1话", contract)
    report = continuity_audit.audit(tmp_path)
    assert "continuity_transition_panel_missing" in {item["code"] for item in report["findings"]}


def test_blueprint_contract_requires_current_panel_script_receipt(tmp_path: Path) -> None:
    contract = {
        "chapter": "第1话",
        **base_contract(),
    }
    blueprint = tmp_path / "脚本" / "split_blueprint.json"
    blueprint.parent.mkdir(parents=True)
    blueprint.write_text(json.dumps({"chapters": [contract]}, ensure_ascii=False), encoding="utf-8")
    path = tmp_path / "脚本" / "第1话" / "panel_script.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "chapter_contract": {
                    "path": "脚本/split_blueprint.json",
                    "chapter_contract_sha256": "stale",
                    "status": "confirmed",
                },
                "panels": [{"panel_id": "P001"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    report = continuity_audit.audit(tmp_path)
    assert "chapter_contract_receipt_stale" in {item["code"] for item in report["findings"]}


def test_next_entry_cannot_silently_drop_previous_exit_fact() -> None:
    findings = continuity_audit.compare_previous_exit(
        {"CHAR_A": {"location": "street", "outfit_id": "OUTFIT_A"}},
        {"CHAR_A": {"outfit_id": "OUTFIT_A"}},
        "第2话",
    )
    assert "chapter_entry_state_missing_previous_fact" in {item["code"] for item in findings}
