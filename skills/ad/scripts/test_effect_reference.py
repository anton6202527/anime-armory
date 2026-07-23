from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).with_name("effect_reference.py")
SPEC = importlib.util.spec_from_file_location("effect_reference_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
effect_reference = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(effect_reference)

LINE_ROOT = MODULE_PATH.resolve().parents[1]
CAMERA_MANIFEST = LINE_ROOT / "references" / "运镜" / "manifest.json"

# 用户点名要求的特效，逐一必须登记（防止后续误删/漏建）。第一批 25 + 第二批扩充 23。
REQUIRED_EFFECT_ZH = {
    # 第一批 25
    "穿云而入", "飞跃地平线", "逆转引力", "地球缩放", "环球缩放", "瞳孔推镜",
    "俯冲地球", "产品扫光", "普拉达换装", "试装特写", "悬浮缓入", "微距推镜",
    "水下慢镜头", "山路追击", "雪地赛车", "city drive", "面部换拍", "巨星名场面",
    "深海巨兽", "飞鸟解体", "升格KO", "升格爆炸", "子弹时间", "小蜜蜂运镜", "双人对打",
    # 第二批 23（仙侠/科幻/商业/环境规模）
    "御剑飞行", "剑气斩", "破碎虚空", "气场爆发", "巨龙盘旋", "凤凰浴火",
    "纳米装甲合体", "机甲变形", "化尘消散", "液态金属", "超空间跳跃", "时间静止走过",
    "液体飞溅", "化妆品涂抹", "产品分解组装", "香水雾化", "玻璃破碎定格",
    "昼夜流逝", "生长延时", "移轴微缩", "星空银河延时", "末日城市毁灭", "千军万马",
}


def test_manifest_self_check_passes() -> None:
    result = effect_reference.self_check(effect_reference.load_manifest())
    assert result["ok"] is True, result["errors"]
    assert result["effect_count"] == 48


def test_all_requested_effects_present() -> None:
    manifest = effect_reference.load_manifest()
    names = {str(e.get("name_zh")) for e in manifest["effects"]}
    missing = REQUIRED_EFFECT_ZH - names
    assert not missing, f"missing effects: {sorted(missing)}"


def test_resolve_effect_accepts_name_alias_and_id() -> None:
    manifest = effect_reference.load_manifest()
    assert effect_reference.resolve_effect(manifest, "子弹时间")["id"] == "bullet_time"
    assert effect_reference.resolve_effect(manifest, "bullet_time")["name_zh"] == "子弹时间"
    assert effect_reference.resolve_effect(manifest, "换脸转场")["id"] == "face_morph"


def test_resolve_effect_raises_on_unknown() -> None:
    manifest = effect_reference.load_manifest()
    with pytest.raises(effect_reference.EffectReferenceError):
        effect_reference.resolve_effect(manifest, "不存在的特效名")


def test_camera_move_links_resolve_to_real_lexicon_keys() -> None:
    manifest = effect_reference.load_manifest()
    camera = json.loads(CAMERA_MANIFEST.read_text(encoding="utf-8"))
    lexicon_keys = {str(m.get("lexicon_key") or m.get("name_zh")) for m in camera["moves"]}
    static_names = {str(m.get("name_zh")) for m in camera["moves"]}
    valid = lexicon_keys | static_names
    for effect in manifest["effects"]:
        assert effect["camera_move"] in valid, (
            f"{effect['id']} camera_move={effect['camera_move']} 未回链到任何运镜 lexicon_key"
        )


def test_transformation_effects_are_high_identity_risk() -> None:
    manifest = effect_reference.load_manifest()
    by_id = {e["id"]: e for e in manifest["effects"]}
    for eid in ("prada_outfit_change", "face_morph"):
        assert by_id[eid]["identity_risk"] == "high"


def test_every_effect_has_bilingual_core_prompt() -> None:
    manifest = effect_reference.load_manifest()
    for effect in manifest["effects"]:
        assert effect["core_prompt_zh"].strip(), effect["id"]
        assert effect["core_prompt_en"].strip(), effect["id"]
