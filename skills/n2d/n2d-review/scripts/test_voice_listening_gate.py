import json
from pathlib import Path

import gate
from gates import voice as voice_gate


va = voice_gate.voice_quality


def _voice_contract(root: Path, *, key_line: bool = True):
    out = root / "合成" / "第1集" / "配音"
    wav_dir = out / "voice"
    wav_dir.mkdir(parents=True)
    (wav_dir / "line_00.wav").write_bytes(b"current-take")
    manifest = [{
        "idx": 0,
        "角色": "甲",
        "文本": "别回头！" if key_line else "天气很好",
        "情绪": "紧张" if key_line else "neutral",
        "钩子": "cold_open" if key_line else "",
        "line_wav": "line_00.wav",
    }]
    manifest_path = out / "时长清单.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    plan_path = out / "key_line_best_of_n_plan.json"
    plan_path.write_text(
        json.dumps(va.build_key_line_best_of_n_plan(manifest, manifest_path=manifest_path), ensure_ascii=False),
        encoding="utf-8",
    )
    return out, wav_dir, manifest, manifest_path, plan_path


def test_compose_gate_blocks_missing_key_line_listening_receipt(tmp_path: Path) -> None:
    out, _, _, _, _ = _voice_contract(tmp_path)
    gate.findings.clear()

    gate.check_voice_listening_receipt(str(tmp_path), "第1集", "compose")

    hits = [row for row in gate.findings if row["dim"] == "关键句实际听辨"]
    assert hits and hits[0]["sev"] == gate.BLOCK
    assert "不得自动补签" in hits[0]["msg"]
    assert str(out / "voice_listening_receipt.json") == hits[0]["loc"]


def test_compose_and_review_gate_accept_current_hash_bound_receipt(tmp_path: Path) -> None:
    out, wav_dir, manifest, manifest_path, plan_path = _voice_contract(tmp_path)
    va.record_listening_receipt(
        wav_dir,
        manifest,
        out / "voice_listening_receipt.json",
        reviewer_kind="executor_audio",
        listened_indices=[0],
        review_notes=["实际听辨当前关键句，咬字与情绪清楚。"],
        manifest_path=manifest_path,
        plan_path=plan_path,
    )

    for stage in ("compose", "review"):
        gate.findings.clear()
        gate.check_voice_listening_receipt(str(tmp_path), "第1集", stage)
        assert not [row for row in gate.findings if row["dim"] == "关键句实际听辨"]


def test_review_gate_rejects_forged_or_stale_receipt(tmp_path: Path) -> None:
    out, wav_dir, manifest, manifest_path, plan_path = _voice_contract(tmp_path)
    receipt_path = out / "voice_listening_receipt.json"
    va.record_listening_receipt(
        wav_dir,
        manifest,
        receipt_path,
        reviewer_kind="human",
        listened_indices=[0],
        review_notes=["实际听辨当前关键句。"],
        manifest_path=manifest_path,
        plan_path=plan_path,
    )
    forged = json.loads(receipt_path.read_text(encoding="utf-8"))
    forged["reviewer_kind"] = "robot"
    forged["listened_lines"][0]["sha256"] = "0" * 64
    receipt_path.write_text(json.dumps(forged, ensure_ascii=False), encoding="utf-8")
    gate.findings.clear()

    gate.check_voice_listening_receipt(str(tmp_path), "第1集", "review")

    hits = [row for row in gate.findings if row["dim"] == "关键句实际听辨"]
    assert hits and hits[0]["sev"] == gate.BLOCK
    assert "reviewer_kind" in hits[0]["msg"]
    assert "SHA" in hits[0]["msg"]


def test_no_key_line_is_not_applicable_and_does_not_block_gate(tmp_path: Path) -> None:
    _voice_contract(tmp_path, key_line=False)
    gate.findings.clear()

    gate.check_voice_listening_receipt(str(tmp_path), "第1集", "compose")

    assert not [row for row in gate.findings if row["dim"] == "关键句实际听辨"]
