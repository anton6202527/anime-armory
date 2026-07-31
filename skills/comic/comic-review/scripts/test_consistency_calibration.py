"""自标定一致性阈值单测（2026-07）。运行：cd skills/comic/comic-review/scripts && python -m pytest test_consistency_calibration.py"""
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).with_name("character_consistency.py")
spec = importlib.util.spec_from_file_location("character_consistency_mod", SCRIPT)
cc = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(cc)


def test_calibrated_ccip_threshold():
    # 组内互距不超过公开阈值 → 用公开阈值
    assert cc.calibrated_ccip_threshold([0.10, 0.15]) == cc.CCIP_SAME_THRESHOLD
    # 风格化角色组内互距 0.24 → 有效阈值放宽到 0.24
    assert cc.calibrated_ccip_threshold([0.16, 0.24]) == 0.24
    # 封顶护栏
    assert cc.calibrated_ccip_threshold([0.9]) == cc.CCIP_CALIBRATED_CAP
    # 无组内对 → 回退公开阈值
    assert cc.calibrated_ccip_threshold([]) == cc.CCIP_SAME_THRESHOLD


def test_calibrated_fingerprint_floor():
    assert cc.calibrated_fingerprint_floor(0.50, [0.6, 0.7]) == 0.50   # 组内都高 → 不放宽
    assert cc.calibrated_fingerprint_floor(0.50, [0.4, 0.6]) == 0.4    # 组内最差 0.4 → 放宽
    assert cc.calibrated_fingerprint_floor(0.50, [0.1]) == cc.FINGERPRINT_FLOOR_MIN  # 下限护栏
    assert cc.calibrated_fingerprint_floor(0.50, []) == 0.50


def test_apply_calibrated_ccip_marks_source():
    ccip = {"available": True, "difference": 0.20, "threshold": 0.178, "same_character": False}
    out = cc.apply_calibrated_ccip(dict(ccip), 0.24)
    assert out["same_character"] is True
    assert out["threshold_source"] == "self_calibrated"
    assert out["threshold_published"] == cc.CCIP_SAME_THRESHOLD
    out2 = cc.apply_calibrated_ccip(dict(ccip), cc.CCIP_SAME_THRESHOLD)
    assert out2["same_character"] is False and out2["threshold_source"] == "published"


def test_valid_current_gold_registry_overrides_published_baseline(tmp_path: Path):
    gold = tmp_path / "生产数据" / "consistency_gold_set.json"
    gold.parent.mkdir(parents=True)
    gold.write_text('{"metrics": {}}', encoding="utf-8")
    registry = {
        "gold_set_path": "生产数据/consistency_gold_set.json",
        "gold_set_sha256": cc.file_sha256(gold),
        "metrics": {"ccip_difference": {"status": "validated", "threshold": 0.21}},
    }
    (gold.parent / "consistency_threshold_registry.json").write_text(json.dumps(registry), encoding="utf-8")
    assert cc.project_ccip_threshold(tmp_path) == (0.21, "gold_set_validated")


def test_changed_gold_set_invalidates_threshold_registry(tmp_path: Path):
    gold = tmp_path / "生产数据" / "consistency_gold_set.json"
    gold.parent.mkdir(parents=True)
    gold.write_text("old", encoding="utf-8")
    registry = {
        "gold_set_path": "生产数据/consistency_gold_set.json",
        "gold_set_sha256": cc.file_sha256(gold),
        "metrics": {"ccip_difference": {"status": "validated", "threshold": 0.21}},
    }
    (gold.parent / "consistency_threshold_registry.json").write_text(json.dumps(registry), encoding="utf-8")
    gold.write_text("new", encoding="utf-8")
    assert cc.project_ccip_threshold(tmp_path) == (cc.CCIP_SAME_THRESHOLD, "published")
