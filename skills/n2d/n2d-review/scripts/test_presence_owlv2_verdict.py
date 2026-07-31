"""presence_owlv2.asset_verdict 单测——双向在场判定 + 旧 manifest 向后兼容。
torch 仅在 _load() 内惰性导入，asset_verdict 是纯函数，可无重模型直接测。
cd skills/n2d/n2d-review/scripts && python -m pytest test_presence_owlv2_verdict.py
"""
import importlib.util
import os

_spec = importlib.util.spec_from_file_location(
    "presence_owlv2", os.path.join(os.path.dirname(__file__), "backends", "presence_owlv2.py"))
owl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(owl)
av = owl.asset_verdict


# ── 向后兼容：旧 manifest（无 expect）= expect 默认 present ──
def test_legacy_present_default_below_threshold_blocks():
    f = av({"asset": "MARK_x", "phrase": "scar on cheek"}, 0.05, 0.10)
    assert f and f["severity"] == "block" and f["expected"] is True and f["present"] is False
    assert "scar on cheek" in f["message"]


def test_legacy_present_default_above_threshold_is_none():
    assert av({"asset": "MARK_x", "phrase": "scar"}, 0.5, 0.10) is None


# ── 新增：expect="absent"（状态像素契约提前泄露检查）──
def test_expect_absent_present_is_warn_leak():
    f = av({"asset": "MARK_金瞳", "phrase": "golden glowing eyes", "expect": "absent",
            "kind": "state_pixel_premature_leak", "char": "沈念", "state": "金瞳觉醒态"}, 0.7, 0.10)
    assert f and f["severity"] == "warn" and f["present"] is True and f["expected"] is False
    # 透传域字段供 state_continuity 合并用
    assert f["kind"] == "state_pixel_premature_leak" and f["char"] == "沈念" and f["state"] == "金瞳觉醒态"


def test_expect_absent_below_threshold_is_none():
    assert av({"asset": "x", "phrase": "p", "expect": "absent"}, 0.02, 0.10) is None


def test_optional_domain_fields_not_leaked_when_absent():
    f = av({"asset": "MARK_x", "phrase": "scar"}, 0.05, 0.10)
    assert "char" not in f and "state" not in f and "kind" not in f
