#!/usr/bin/env python3
"""Tests for boundary_review.py structured signoff."""
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import boundary_review as BR  # noqa: E402


def _mk_work(raw_text):
    d = tempfile.mkdtemp()
    ep = Path(d) / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "raw.txt").write_text(raw_text, encoding="utf-8")
    return d


RISKY = "她走进屋里。\n然后坐下。\n"


def test_check_blocks_missing_review_for_risky_boundary():
    root = _mk_work(RISKY)
    result = BR.validate(root)
    assert not result["ok"]
    assert any(f["code"] == "missing_boundary_review" for f in result["findings"])


def _sign_all_keep(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    for entry in data["reviews"]:
        entry["decision"] = "keep"
        entry["notes"] = "导演复核：本段语义闭环成立，机器词面为误报。"
        entry["reviewed_by"] = "director-wang"
        entry["semantic_evidence"] = {"reason": "人物选择与后果在相邻段落中完整，保留自然幕界。"}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_draft_then_signed_review_passes():
    root = _mk_work(RISKY)
    BR.draft(root, write=True)
    path = BR.review_path(root)
    _sign_all_keep(path)

    result = BR.validate(root)

    assert result["ok"]
    assert not result["findings"]


def test_raw_change_invalidates_signed_review():
    root = _mk_work(RISKY)
    BR.draft(root, write=True)
    path = BR.review_path(root)
    _sign_all_keep(path)
    (Path(root) / "脚本" / "第1集" / "raw.txt").write_text("她走进屋里。\n然后坐下。\n门外忽然传来哭声，", encoding="utf-8")

    result = BR.validate(root)

    assert not result["ok"]
    assert any(f["code"] in {"stale_boundary_review", "missing_blocker_review"} for f in result["findings"])


def test_accept_risk_cannot_unlock_strict_blocker():
    root = _mk_work(RISKY)
    BR.draft(root, write=True)
    path = BR.review_path(root)
    data = json.loads(path.read_text(encoding="utf-8"))
    for entry in data["reviews"]:
        entry["decision"] = "accept_risk"
        entry["notes"] = "知悉风险。"
        entry["reviewed_by"] = "director-wang"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    result = BR.validate(root)
    assert not result["ok"]
    assert any(f["code"] == "accept_risk_advisory_only" for f in result["findings"])


def test_keep_requires_semantic_evidence_not_generic_notes_only():
    root = _mk_work(RISKY)
    BR.draft(root, write=True)
    path = BR.review_path(root)
    data = json.loads(path.read_text(encoding="utf-8"))
    for entry in data["reviews"]:
        entry["decision"] = "keep"
        entry["notes"] = "已看过，保留。"
        entry["reviewed_by"] = "director-wang"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    result = BR.validate(root)
    assert not result["ok"]
    assert any(f["code"] == "missing_semantic_evidence" for f in result["findings"])


def test_move_boundary_signed_but_not_applied_fails():
    root = _mk_work(RISKY)
    BR.draft(root, write=True)
    path = BR.review_path(root)
    data = json.loads(path.read_text(encoding="utf-8"))
    for entry in data["reviews"]:
        entry["decision"] = "move_boundary"
        entry["notes"] = "声称已移动边界，但没有实施收据。"
        entry["reviewed_by"] = "director-wang"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    result = BR.validate(root)
    assert not result["ok"]
    assert any(f["code"] == "missing_applied_receipt" for f in result["findings"])


def test_mutating_decision_passes_only_after_new_sha_and_mapping_receipt():
    root = _mk_work(RISKY)
    BR.draft(root, write=True)
    path = BR.review_path(root)
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = Path(root) / "脚本" / "第1集" / "raw.txt"
    raw.write_text(RISKY + "改写后仍需导演复核。\n", encoding="utf-8")
    current = {b["blocker_id"]: b for b in BR.current_audit(root)["blockers"]}
    for entry in data["reviews"]:
        blocker = current.get(entry["blocker_id"])
        if not blocker:
            continue
        contract = blocker["boundary_contract"]
        entry["decision"] = "rewrite"
        entry["notes"] = "已按 source unit 映射改写。"
        entry["reviewed_by"] = "director-wang"
        entry["applied_receipt"] = {
            "status": "applied",
            "previous_boundary_contract_sha256": entry["boundary_contract"]["contract_sha256"],
            "new_left_raw_sha256": contract["left_raw_sha256"],
            "new_right_raw_sha256": contract["right_raw_sha256"],
            "source_mapping": [{"from": "U000001-U000002", "to": "第1集"}],
        }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    result = BR.validate(root)
    assert result["ok"], result["findings"]


def test_resolving_blocker_still_requires_mutation_receipt():
    root = _mk_work(RISKY)
    BR.draft(root, write=True)
    path = BR.review_path(root)
    data = json.loads(path.read_text(encoding="utf-8"))
    for entry in data["reviews"]:
        entry["decision"] = "rewrite"
        entry["notes"] = "已重写为完整边界。"
        entry["reviewed_by"] = "director-wang"
    (Path(root) / "脚本" / "第1集" / "raw.txt").write_text(
        "第一章\n他逼问，她反击，原来真相如此！\n",
        encoding="utf-8",
    )
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    result = BR.validate(root)
    assert not result["ok"]
    assert any(f["code"] == "resolved_blocker_missing_applied_receipt" for f in result["findings"])

    current_rows = BR.current_audit(root)["all_rows"]
    for entry in data["reviews"]:
        old = entry["boundary_contract"]
        current = BR.BA._boundary_contract(current_rows, old["from_episode"], old["to_episode"])
        entry["applied_receipt"] = {
            "status": "applied",
            "previous_boundary_contract_sha256": old["contract_sha256"],
            "new_left_raw_sha256": current["left_raw_sha256"],
            "new_right_raw_sha256": current["right_raw_sha256"],
            "source_mapping": [{"from": "U000001-U000002", "to": "第1集"}],
        }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    assert BR.validate(root)["ok"]


def test_machine_redraft_never_overwrites_human_review():
    root = _mk_work(RISKY)
    BR.draft(root, write=True)
    path = BR.review_path(root)
    _sign_all_keep(path)
    before = path.read_text(encoding="utf-8")
    BR.draft(root, write=True)
    assert path.read_text(encoding="utf-8") == before
    assert BR.review_draft_path(root).exists()


def test_record_api_signs_exact_keep_entries_and_preserves_machine_draft():
    root = _mk_work(RISKY)
    drafted = BR.draft(root, write=True)
    machine_before = BR.review_draft_path(root).read_bytes()
    blocker_ids = [row["blocker_id"] for row in drafted["reviews"]]
    assert len(blocker_ids) >= 2  # exact id selection matters when one boundary has multiple codes

    first = BR.record(
        root,
        blocker_ids[0],
        decision="keep",
        notes="语义闭环完整，保留此幕界。",
        reviewer="director-li",
        semantic_evidence={"conflict": "进入房间后立即作出选择", "payoff": "坐下完成动作结果"},
    )
    assert first["ok"]
    human = json.loads(BR.review_path(root).read_text(encoding="utf-8"))
    signed = [row for row in human["reviews"] if row["blocker_id"] == blocker_ids[0]][0]
    untouched = [row for row in human["reviews"] if row["blocker_id"] == blocker_ids[1]][0]
    assert signed["decision"] == "keep"
    assert signed["reviewed_by"] == "director-li"
    assert untouched["decision"] == "pending"
    assert BR.review_draft_path(root).read_bytes() == machine_before

    for blocker_id in blocker_ids[1:]:
        BR.sign(
            root,
            blocker_id,
            decision="keep",
            notes="逐项复核后确认这是词面误报。",
            reviewer="director-li",
            semantic_evidence={"reason": "相邻语句共同形成动作闭环"},
        )
    assert BR.validate(root)["ok"]


def test_record_api_rejects_unknown_or_stale_blocker_contract():
    root = _mk_work(RISKY)
    drafted = BR.draft(root, write=True)
    blocker_id = drafted["reviews"][0]["blocker_id"]
    with pytest.raises(ValueError, match="未知 blocker_id"):
        BR.record(
            root,
            "E9999-END:not_real",
            decision="keep",
            notes="不存在。",
            reviewer="director-li",
            semantic_evidence="不存在",
        )

    (Path(root) / "脚本" / "第1集" / "raw.txt").write_text(
        RISKY + "门外响起脚步声，",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="已陈旧"):
        BR.record(
            root,
            blocker_id,
            decision="keep",
            notes="试图沿用旧合同。",
            reviewer="director-li",
            semantic_evidence="旧证据",
        )


@pytest.mark.parametrize("reviewer", ["", "auto", "agent-reviewer", "bot:director", "自动", "系统-审阅"])
def test_record_api_rejects_empty_or_automated_reviewer(reviewer):
    root = _mk_work(RISKY)
    blocker_id = BR.draft(root, write=True)["reviews"][0]["blocker_id"]
    with pytest.raises(ValueError, match="reviewer"):
        BR.record(
            root,
            blocker_id,
            decision="keep",
            notes="看过。",
            reviewer=reviewer,
            semantic_evidence="语义证据",
        )


def test_record_api_rejects_empty_keep_fields_and_accept_risk():
    root = _mk_work(RISKY)
    blocker_id = BR.draft(root, write=True)["reviews"][0]["blocker_id"]
    common = {"root": root, "blocker_id": blocker_id, "reviewer": "director-li"}
    with pytest.raises(ValueError, match="notes"):
        BR.record(decision="keep", notes="", semantic_evidence="有", **common)
    with pytest.raises(ValueError, match="semantic_evidence"):
        BR.record(decision="keep", notes="已看", semantic_evidence={}, **common)
    with pytest.raises(ValueError, match="accept_risk"):
        BR.record(decision="accept_risk", notes="愿意承担", **common)


def test_record_mutation_requires_changed_raw_and_builds_receipt_from_old_contract():
    root = _mk_work(RISKY)
    drafted = BR.draft(root, write=True)
    blocker_ids = [row["blocker_id"] for row in drafted["reviews"]]
    old_contracts = {row["blocker_id"]: row["boundary_contract"] for row in drafted["reviews"]}
    with pytest.raises(ValueError, match="raw SHA 均未变化"):
        BR.record(
            root,
            blocker_ids[0],
            decision="rewrite",
            notes="尚未实际改写。",
            reviewer="director-li",
            source_mapping=[{"from": "U000001", "to": "第1集"}],
        )
    with pytest.raises(ValueError, match="source_mapping"):
        BR.record(
            root,
            blocker_ids[0],
            decision="rewrite",
            notes="缺映射。",
            reviewer="director-li",
            source_mapping={},
        )

    raw = Path(root) / "脚本" / "第1集" / "raw.txt"
    raw.write_text(RISKY + "她听见门响，立即起身反锁。", encoding="utf-8")
    machine_before = BR.review_draft_path(root).read_bytes()
    for blocker_id in blocker_ids:
        result = BR.record(
            root,
            blocker_id,
            decision="rewrite",
            notes="已按源单元重写边界，并保留人物动机。",
            reviewer="director-li",
            source_mapping=[{"from": "U000001-U000002", "to": "第1集:U000001-U000003"}],
        )
        receipt = result["entry"]["applied_receipt"]
        assert receipt["previous_boundary_contract_sha256"] == old_contracts[blocker_id]["contract_sha256"]
        assert receipt["new_left_raw_sha256"] != old_contracts[blocker_id]["left_raw_sha256"]
        assert result["entry"]["boundary_contract"] == old_contracts[blocker_id]
    assert BR.review_draft_path(root).read_bytes() == machine_before
    assert BR.validate(root)["ok"]


def test_record_cli_reads_source_mapping_file_and_rejects_auto_reviewer(tmp_path, capsys):
    root = _mk_work(RISKY)
    blocker_id = BR.draft(root, write=True)["reviews"][0]["blocker_id"]
    raw = Path(root) / "脚本" / "第1集" / "raw.txt"
    raw.write_text(RISKY + "她改变了边界安排。", encoding="utf-8")
    mapping_path = tmp_path / "mapping.json"
    mapping_path.write_text(
        json.dumps([{"from": "U000001", "to": "第1集:U000001-U000002"}], ensure_ascii=False),
        encoding="utf-8",
    )
    code = BR.main([
        "sign",
        root,
        blocker_id,
        "--decision", "rewrite",
        "--notes", "已实施并复核。",
        "--reviewer", "director-li",
        "--source-mapping-file", str(mapping_path),
        "--json",
    ])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["entry"]["applied_receipt"]["source_mapping"][0]["from"] == "U000001"

    other = [
        row["blocker_id"]
        for row in json.loads(BR.review_path(root).read_text(encoding="utf-8"))["reviews"]
        if row["blocker_id"] != blocker_id
    ][0]
    code = BR.main([
        "record",
        root,
        other,
        "--decision", "rewrite",
        "--notes", "伪自动签收。",
        "--reviewer", "agent-reviewer",
        "--source-mapping-json", '[{"from":"U2","to":"E1"}]',
        "--json",
    ])
    error = json.loads(capsys.readouterr().out)
    assert code == 2
    assert "reviewer" in error["findings"][0]["message"]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
