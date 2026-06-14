"""asset_lifecycle 单测——结构化状态机校验（回退/未知态）+ 自由文本兼容。

cd skills/n2d-image/scripts && python3 -m pytest test_asset_lifecycle.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).with_name("asset_lifecycle.py")
spec = importlib.util.spec_from_file_location("asset_lifecycle", SCRIPT)
al = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(al)


def test_is_structured_lifecycle() -> None:
    assert al.is_structured_lifecycle({"states": ["a", "b"]}) is True
    assert al.is_structured_lifecycle("Clip01-05 完整，后摔碎") is False
    assert al.is_structured_lifecycle(None) is False
    assert al.is_structured_lifecycle({"transitions": []}) is False   # 无 states


def test_freetext_lifecycle_is_info_not_block() -> None:
    f = al.validate_lifecycle({"id": "PROP_03", "lifecycle": "Clip01 完整，毒酒倒入后摔碎，后续保持碎瓷"})
    assert len(f) == 1 and f[0]["level"] == "info" and f[0]["code"] == "lifecycle_freetext"


def test_structured_forward_transitions_pass() -> None:
    asset = {"id": "PROP_03", "lifecycle": {
        "states": ["intact", "cracked", "shattered"],
        "transitions": [{"from": "intact", "to": "cracked", "at_clip": "Clip_07"},
                        {"from": "cracked", "to": "shattered", "at_clip": "Clip_09"}]}}
    assert al.validate_lifecycle(asset) == []


def test_state_regression_blocks() -> None:
    # 摔碎的瓶子又"完好" = 回退 → block
    asset = {"id": "PROP_03", "lifecycle": {
        "states": ["intact", "cracked", "shattered"],
        "transitions": [{"from": "shattered", "to": "intact", "at_clip": "Clip_12"}]}}
    codes = {f["code"]: f["level"] for f in al.validate_lifecycle(asset)}
    assert codes.get("lifecycle_regression") == "block"


def test_same_state_transition_blocks() -> None:
    asset = {"id": "PROP_01", "lifecycle": {
        "states": ["a", "b"], "transitions": [{"from": "a", "to": "a"}]}}
    assert any(f["code"] == "lifecycle_regression" for f in al.validate_lifecycle(asset))


def test_unknown_state_blocks() -> None:
    asset = {"id": "VFX_01", "lifecycle": {
        "states": ["lv1", "lv2"], "transitions": [{"from": "lv1", "to": "lv9"}]}}
    codes = {f["code"] for f in al.validate_lifecycle(asset)}
    assert "lifecycle_unknown_to_state" in codes


def test_thin_states_warn() -> None:
    asset = {"id": "PROP_01", "lifecycle": {"states": ["intact"], "transitions": []}}
    assert any(f["code"] == "lifecycle_states_thin" and f["level"] == "warn"
               for f in al.validate_lifecycle(asset))


def test_vfx_forms_and_params() -> None:
    # forms 缺 id → warn；vfx_params 非对象 → warn
    asset = {"id": "VFX_01", "lifecycle": {"states": ["a", "b"], "transitions": []},
             "forms": [{"id": "lv1"}, {"name": "lv2"}], "vfx_params": "暗金"}
    codes = {f["code"] for f in al.validate_lifecycle(asset)}
    assert "form_missing_id" in codes
    assert "vfx_params_type" in codes


def test_validate_registry_and_run(tmp_path: Path) -> None:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "asset_registry.json").write_text(json.dumps({"assets": [
        {"id": "PROP_01", "lifecycle": "自由文本完整→破损"},   # info
        {"id": "PROP_03", "lifecycle": {"states": ["intact", "shattered"],
         "transitions": [{"from": "shattered", "to": "intact"}]}},  # 回退 block
    ]}, ensure_ascii=False), encoding="utf-8")
    res = al.run(tmp_path)
    assert res["available"] is True and res["checked"] == 2 and res["structured"] == 1
    assert res["verdict"] == "block"
    assert al.run(tmp_path / "nope")["available"] is False
