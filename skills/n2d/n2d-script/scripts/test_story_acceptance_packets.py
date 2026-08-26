#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import story_acceptance_packets as sap  # noqa: E402
from signoff_contract import new_manifest, profile_spec, record_approval, write_manifest  # noqa: E402


def _sign(root: Path, profile: str, ep: str = "第1集") -> None:
    spec = profile_spec(root, profile, ep)
    payload = new_manifest(
        root, artifact_scope=spec["artifact_scope"], episode=ep, author_id="automation:n2d",
        input_paths=spec["input_paths"], evidence_paths=spec["evidence_paths"], required_role_groups=spec["required_role_groups"],
    )
    roles = ("director",) if profile == "table_read" else ("director", "editor")
    for role in roles:
        payload = record_approval(payload, root, reviewer_id="user:owner", reviewer_role=role, evidence_paths=spec["evidence_paths"])
    write_manifest(root / spec["signoff_path"], payload)


def _write_inputs(root: Path, ep: str = "第1集") -> None:
    ep_dir = root / "脚本" / ep
    ep_dir.mkdir(parents=True)
    (ep_dir / "voiceover.txt").write_text("1. 你终于来了。\n2. 令牌是真的。\n", encoding="utf-8")
    (ep_dir / "storyboard.json").write_text(json.dumps({
        "clips": [
            {"id": "Clip_01", "duration": 4, "dramatic_function": "冷开钩子", "continuity": {"transition": "cut"}},
            {"id": "Clip_02", "duration": 5, "dramatic_function": "反转", "continuity": {"transition": "match_cut"}},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    (ep_dir / "镜头时长.json").write_text(json.dumps({"Clip_01": 4, "Clip_02": 5}, ensure_ascii=False), encoding="utf-8")
    (ep_dir / "字幕_中文.srt").write_text(
        "1\n00:00:00,000 --> 00:00:04,000\n你终于来了。\n\n"
        "2\n00:00:04,000 --> 00:00:09,000\n令牌是真的。\n",
        encoding="utf-8",
    )
    audio = root / "合成" / ep / "配音" / "voice_zh.wav"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"RIFF-guide-voice-test")


def _record_reviews(root: Path, ep: str = "第1集", *, table: bool = True, animatic: bool = True) -> None:
    if animatic:
        sap._ensure_animatic_preview(root, ep)
    if table:
        sap.record_review_execution(
            root, ep, "table_read", reviewer_kind="executor_text_audio", coverage=1.0,
            reviewed_line_count=2, review_notes=["逐句围读，人物口吻可区分。"],
        )
    if animatic:
        sap.record_review_execution(
            root, ep, "animatic", reviewer_kind="executor_visual_audio", coverage=1.0,
            watched_duration_sec=9, review_notes=["完整听看音画与字幕，节奏可读。"],
        )


def test_scaffold_and_check_blocks_draft(tmp_path: Path) -> None:
    _write_inputs(tmp_path)

    sap.scaffold(tmp_path, "1", kind="both")
    report = sap.check(tmp_path, "第1集", kind="both")

    assert report["status"] == "block"
    assert report["summary"]["block"] == 9


def test_confirm_flag_cannot_self_attest_without_execution_receipt(tmp_path: Path) -> None:
    _write_inputs(tmp_path)

    with pytest.raises(ValueError, match="不能自行证明"):
        sap.scaffold(tmp_path, "第1集", kind="table_read", confirmed=True)


def test_confirmed_packets_pass(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    _record_reviews(tmp_path)

    sap.scaffold(tmp_path, "第1集", kind="both", confirmed=True)
    unsigned = sap.check(tmp_path, "第1集", kind="both", write_missing=True)
    assert unsigned["status"] == "block"
    _sign(tmp_path, "table_read")
    _sign(tmp_path, "animatic")
    report = sap.check(tmp_path, "第1集", kind="both", write_missing=True)

    assert report["status"] == "pass"
    assert (tmp_path / "生产数据" / "animatic_第1集.html").is_file()
    animatic = json.loads((tmp_path / "脚本" / "第1集" / "animatic_packet.json").read_text(encoding="utf-8"))
    assert animatic["timeline"]["estimated_total_sec"] == 9


def test_confirmed_packet_blocks_after_storyboard_changes(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    _record_reviews(tmp_path, table=False)
    sap.scaffold(tmp_path, "第1集", kind="animatic", confirmed=True)

    sb = tmp_path / "脚本" / "第1集" / "storyboard.json"
    data = json.loads(sb.read_text(encoding="utf-8"))
    data["clips"].append({"id": "Clip_03", "duration": 2, "dramatic_function": "新转折"})
    sb.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    report = sap.check(tmp_path, "第1集", kind="animatic", write_missing=True)

    assert report["status"] == "block"
    assert any("inputs_fingerprint" in "；".join(row["issues"]) for row in report["files"])


def test_table_read_reports_estimate_only_when_final_timing_is_absent(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    timing = tmp_path / "合成" / "第1集" / "配音" / "timing_estimate.json"
    timing.parent.mkdir(parents=True, exist_ok=True)
    timing.write_text(json.dumps({
        "kind": "n2d_timing_estimate",
        "audio_generated": False,
        "summary": {"duration_sec": 12.5, "line_count": 2},
    }, ensure_ascii=False), encoding="utf-8")

    payload = sap._table_read_payload(tmp_path, "第1集")

    assert payload["read_through"]["timing_status"] == "estimate_only"
    assert payload["inputs"]["timing_estimate"].endswith("timing_estimate.json")


def test_table_read_ignores_premature_story_economy_block(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    out = tmp_path / "生产数据" / "story_economy_audit_第1集.json"
    out.parent.mkdir(parents=True)
    out.write_text(json.dumps({
        "ok": False,
        "findings": [{"severity": "block", "code": "missing_storyboard"}],
    }, ensure_ascii=False), encoding="utf-8")

    payload = sap._table_read_payload(tmp_path, "第1集")

    assert payload["machine_reference"]["story_economy"] == "not_applicable_before_storyboard"


def test_stage2_quality_report_does_not_invalidate_approved_table_read(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    _record_reviews(tmp_path, animatic=False)
    sap.scaffold(tmp_path, "第1集", kind="table_read", confirmed=True)
    _sign(tmp_path, "table_read")

    report_path = tmp_path / "生产数据" / "script_quality_contract_第1集.json"
    report_path.parent.mkdir(parents=True)
    report_path.write_text(json.dumps({"status": "pass"}, ensure_ascii=False), encoding="utf-8")

    report = sap.check(tmp_path, "第1集", kind="table_read")

    assert report["status"] == "pass"
