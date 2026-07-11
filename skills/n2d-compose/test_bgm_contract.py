from pathlib import Path

import importlib.util
import sys

_path = Path(__file__).resolve().parents[1] / "n2d" / "_lib" / "bgm_contract.py"
_spec = importlib.util.spec_from_file_location("n2d_bgm_contract_core_under_test", _path)
assert _spec is not None and _spec.loader is not None
bgm = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = bgm
_spec.loader.exec_module(bgm)


def test_placeholder_requires_explicit_internal_approval(tmp_path):
    payload = bgm.scaffold(tmp_path, "第1集")
    payload["status"] = "confirmed"
    assert {row["code"] for row in bgm.validate(tmp_path, "第1集", payload)} == {"bgm_cues_missing", "bgm_placeholder_unapproved"}
    payload["cues"] = [{"id": "BGM_01", "intent": "压迫感"}]
    payload["placeholder_approval"] = {"approved": True, "approved_by": "producer:a", "scope": "internal_rough_only"}
    assert bgm.validate(tmp_path, "第1集", payload) == []
    assert {row["code"] for row in bgm.validate(tmp_path, "第1集", payload, allow_placeholder=False)} == {
        "bgm_placeholder_not_deliverable"
    }


def test_generated_bgm_requires_model_channel_and_file(tmp_path):
    payload = bgm.scaffold(tmp_path, "第1集")
    payload.update({"status": "confirmed", "strategy": "generated", "cues": [{"intent": "追逐"}]})
    codes = {row["code"] for row in bgm.validate(tmp_path, "第1集", payload)}
    assert "bgm_generation_provenance_missing" in codes and "bgm_generated_file_missing" in codes
    audio = tmp_path / "素材" / "bgm.wav"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"RIFF")
    payload["source"].update({"file": "素材/bgm.wav", "model": "Custom Music Model 1", "channel": "manual"})
    bgm.contract_path(tmp_path, "第1集").parent.mkdir(parents=True, exist_ok=True)
    bgm.contract_path(tmp_path, "第1集").write_text(__import__("json").dumps(payload, ensure_ascii=False), encoding="utf-8")
    codes = {row["code"] for row in bgm.validate(tmp_path, "第1集", payload)}
    assert codes == {"bgm_generation_receipt_missing"}
