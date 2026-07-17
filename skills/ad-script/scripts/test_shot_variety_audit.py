# -*- coding: utf-8 -*-
"""广告分镜视觉多样性机检（shot_variety_audit）单测。

盯广告领域纪律与 advisory 底线：
  ① 产品 beauty / 片尾 endcard / logo·CTA 板等**有意重复镜必须豁免**，绝不误报为构图重复；
  ② 短广告单场景合法——场景/景别单调只 info；
  ③ 本检永不产 block（Creative heuristics stay advisory）。
"""
import json

import shot_variety_audit as sva


def _write_storyboard(root, shots):
    path = root / "脚本" / "storyboard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"kind": "ad_storyboard", "shots": shots}, ensure_ascii=False), encoding="utf-8")
    return path


def _codes(report):
    return {f["code"] for f in report["findings"]}


def test_duplicate_composition_flagged(tmp_path):
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "景别": "中景", "scene": "客厅", "shot_type": "human", "shot": "女主拿起手机看"},
        {"shot_id": "S2", "景别": "中景", "scene": "客厅", "shot_type": "human", "shot": "男主走进门口挥手"},
    ])
    report = sva.build(tmp_path)
    assert "duplicate_shot_composition" in _codes(report)
    assert report["summary"]["block"] == 0


def test_hero_and_endcard_exempt_from_duplicate(tmp_path):
    # 两个产品特写 beauty + 片尾板：都豁免 → 不报构图重复
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "景别": "特写", "scene": "白底", "shot_type": "product", "shot": "产品特写 beauty shot 旋转"},
        {"shot_id": "S2", "景别": "特写", "scene": "白底", "shot_type": "product", "shot": "产品特写展示 logo"},
        {"shot_id": "S3", "景别": "特写", "scene": "片尾板", "shot": "endcard：logo + slogan + CTA"},
    ])
    report = sva.build(tmp_path)
    assert "duplicate_shot_composition" not in _codes(report)
    assert report["inputs"]["exempt_shots"] == 3


def test_duplicate_description_by_similarity(tmp_path):
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "scene": "街道", "shot": "女主在阳光下奔跑穿过城市街道"},
        {"shot_id": "S2", "scene": "公园", "shot": "女主在阳光下奔跑穿过城市街道边"},
    ])
    report = sva.build(tmp_path)
    assert "duplicate_shot_description" in _codes(report)


def test_scene_monotony_info_only_and_needs_length(tmp_path):
    # 10 镜里 9 镜同场景（90%>85%）+ 1 别处 → info（非 warn）
    shots = [{"shot_id": f"S{i}", "scene": "厨房", "景别": f"景{i}", "shot": f"动作{i}描述内容各不同"} for i in range(9)]
    shots.append({"shot_id": "S10", "scene": "客厅", "景别": "远景", "shot": "别处一个镜头描述"})
    _write_storyboard(tmp_path, shots)
    report = sva.build(tmp_path)
    mono = [f for f in report["findings"] if f["code"] == "scene_monotony"]
    assert mono and mono[0]["severity"] == "info"

    # 3 镜（短）同场景 → 不触发（短广告单场景合法）
    _write_storyboard(tmp_path, [{"shot_id": f"S{i}", "scene": "厨房", "景别": f"景{i}"} for i in range(3)])
    report2 = sva.build(tmp_path)
    assert "scene_monotony" not in _codes(report2)


def test_framing_variety_low_info(tmp_path):
    shots = [{"shot_id": f"S{i}", "scene": f"场景{i}", "景别": "中景", "shot": f"不同的画面描述内容第{i}个"} for i in range(5)]
    _write_storyboard(tmp_path, shots)
    report = sva.build(tmp_path)
    fv = [f for f in report["findings"] if f["code"] == "framing_variety_low"]
    assert fv and fv[0]["severity"] == "info"


def test_missing_storyboard_degrades_not_blocks(tmp_path):
    report = sva.build(tmp_path)
    assert report["available"] is False
    assert report["summary"]["block"] == 0
    assert "storyboard_missing" in _codes(report)


def test_advisory_never_blocks_and_cli(tmp_path):
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "景别": "中景", "scene": "客厅", "shot_type": "human", "shot": "aaa"},
        {"shot_id": "S2", "景别": "中景", "scene": "客厅", "shot_type": "human", "shot": "bbb"},
    ])
    report = sva.build(tmp_path)
    assert report["summary"]["block"] == 0
    assert report["summary"]["warn"] >= 1
    # 默认 exit 0；--strict 才因 warn 退 1
    assert sva.main([str(tmp_path), "--write"]) == 0
    assert sva.main([str(tmp_path), "--strict"]) == 1
    assert (tmp_path / "生产数据" / "ad_shot_variety_audit.json").exists()


def test_kind_and_schema(tmp_path):
    _write_storyboard(tmp_path, [{"shot_id": "S1", "景别": "近景", "scene": "白底"}])
    report = sva.build(tmp_path)
    assert report["kind"] == "ad_shot_variety_audit"
    assert set(report["summary"]) >= {"block", "warn", "info"}
    # findings 必须用 ad house 的 msg 键
    for f in report["findings"]:
        assert "msg" in f and "severity" in f and "code" in f


def test_rehook_gap_warns_on_long_ad_without_mid_hooks(tmp_path):
    # 40s 广告：开场钩之后 30s 全是平铺产品演示，没有任何再钩节拍 → warn
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "duration": 5, "scene": "开场", "shot": "痛点提问：你的地板多久没真正干净过"},
        {"shot_id": "S2", "duration": 10, "scene": "客厅", "shot": "产品匀速滑过地板"},
        {"shot_id": "S3", "duration": 10, "scene": "客厅", "shot": "机身侧面缓慢摇移"},
        {"shot_id": "S4", "duration": 10, "scene": "客厅", "shot": "遥控器按键特写缓推"},
        {"shot_id": "S5", "duration": 5, "scene": "片尾", "shot": "endcard CTA 立即购买"},
    ])
    report = sva.build(tmp_path)

    assert "rehook_gap" in _codes(report)
    hit = next(f for f in report["findings"] if f["code"] == "rehook_gap")
    assert hit["severity"] == "warn"
    assert report["summary"]["block"] == 0


def test_rehook_gap_quiet_when_mid_hooks_present(tmp_path):
    # 同样 40s，但中段有对比揭晓再钩 → 不报
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "duration": 5, "scene": "开场", "shot": "痛点提问：地板多久没干净过"},
        {"shot_id": "S2", "duration": 10, "scene": "客厅", "shot": "产品匀速滑过地板"},
        {"shot_id": "S3", "duration": 10, "scene": "客厅", "shot": "before/after 对比揭晓：灰尘槽倒出一整杯"},
        {"shot_id": "S4", "duration": 10, "scene": "客厅", "shot": "实测挑战：麦片酱油一次过"},
        {"shot_id": "S5", "duration": 5, "scene": "片尾", "shot": "endcard CTA 立即购买"},
    ])
    report = sva.build(tmp_path)

    assert "rehook_gap" not in _codes(report)


def test_rehook_gap_skips_short_ads_and_missing_durations(tmp_path):
    # 15s 短广告：一个开场钩就够，不判
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "duration": 5, "scene": "开场", "shot": "平铺开场"},
        {"shot_id": "S2", "duration": 5, "scene": "客厅", "shot": "产品滑过"},
        {"shot_id": "S3", "duration": 5, "scene": "片尾", "shot": "endcard CTA"},
    ])
    assert "rehook_gap" not in _codes(sva.build(tmp_path))

    # 时长字段缺失过半：不臆造节奏问题
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "shot": "平铺开场"},
        {"shot_id": "S2", "shot": "产品滑过"},
        {"shot_id": "S3", "duration": 30, "shot": "长演示"},
    ])
    assert "rehook_gap" not in _codes(sva.build(tmp_path))
