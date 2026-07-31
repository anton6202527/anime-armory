# -*- coding: utf-8 -*-
"""人物镜表演指令机检（performance_cue_audit）单测。

盯纪律：① 纯产品镜/endcard 不判（表演轴只管有人的镜）；② 三轴全缺才 warn、缺两轴 info；
③ advisory——summary.block 恒 0；④ 三轴齐的人物镜安静。
"""
import json

import performance_cue_audit as pcu


def _write(root, shots):
    path = root / "脚本" / "storyboard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"shots": shots}, ensure_ascii=False), encoding="utf-8")


def _codes(report):
    return {f["code"] for f in report["findings"]}


def test_bare_people_shot_warns_but_product_only_and_endcard_skip(tmp_path):
    _write(tmp_path, [
        {"shot_id": "S1", "shot": "女主站在厨房", "assets": {"CHAR_MOM": True}},   # 三轴全缺
        {"shot_id": "S2", "shot": "产品旋转展示", "assets": {"PROD_X": True}},      # 无人物,不判
        {"shot_id": "S3", "shot": "endcard CTA 主角挥手", "endcard": True},        # endcard 豁免
    ])
    report = pcu.build(tmp_path)

    hit = next(f for f in report["findings"] if f["code"] == "performance_cue_unspecified")
    assert hit["shots"] == ["S1"] and hit["severity"] == "warn"
    assert report["inputs"]["people_shots"] == 1
    assert report["summary"]["block"] == 0


def test_two_axes_missing_info_and_full_cue_quiet(tmp_path):
    _write(tmp_path, [
        {"shot_id": "S1", "shot": "妈妈拿起洗衣液", "情绪": ""},  # 有动作(拿起),缺情绪/视线
        {"shot_id": "S2", "shot": "女主皱着眉刷手机，看到价格眼睛一亮，低头看手里的瓶身，拧开闻了一下"},
    ])
    report = pcu.build(tmp_path)

    infos = [f for f in report["findings"] if f["code"] == "performance_cue_thin"]
    assert [f["shots"] for f in infos] == [["S1"]]
    assert "performance_cue_unspecified" not in _codes(report)


def test_missing_storyboard_explicit(tmp_path):
    report = pcu.build(tmp_path)
    assert report["available"] is False
    assert "storyboard_missing" in _codes(report)
