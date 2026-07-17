# -*- coding: utf-8 -*-
"""产品镜传统工艺声明机检（product_craft_audit）单测。

盯纪律：① endcard/logo 板豁免（静版要稳不要花）；② 三轴全缺才 warn、缺两轴只 info；
③ advisory——summary.block 恒 0；④ 非产品镜（叙事/人物）完全不判。
"""
import json

import product_craft_audit as pca


def _write(root, shots):
    path = root / "脚本" / "storyboard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"shots": shots}, ensure_ascii=False), encoding="utf-8")


def _codes(report):
    return {f["code"] for f in report["findings"]}


def test_bare_product_shot_warns_and_block_stays_zero(tmp_path):
    _write(tmp_path, [
        {"shot_id": "S1", "shot": "产品放在桌上", "assets": {"PROD_X": True}},
        {"shot_id": "S2", "shot": "女主在客厅走动"},  # 非产品镜不判
    ])
    report = pca.build(tmp_path)

    assert "product_craft_unspecified" in _codes(report)
    hit = next(f for f in report["findings"] if f["code"] == "product_craft_unspecified")
    assert hit["shots"] == ["S1"] and hit["severity"] == "warn"
    assert report["summary"]["block"] == 0


def test_two_axes_missing_is_info_and_full_craft_is_quiet(tmp_path):
    _write(tmp_path, [
        {"shot_id": "S1", "shot": "产品特写", "light": "逆光穿瓶"},  # 有光位，缺质感/角度
        {"shot_id": "S2", "shot": "产品 hero", "light": "侧光塑形",
         "运镜": "低角度仰拍缓慢推轨", "画面": "300fps 升格浇注，微距气泡"},  # 三轴齐
    ])
    report = pca.build(tmp_path)

    infos = [f for f in report["findings"] if f["code"] == "product_craft_thin"]
    assert [f["shots"] for f in infos] == [["S1"]]
    assert "product_craft_unspecified" not in _codes(report)


def test_endcard_exempt_and_missing_storyboard_explicit(tmp_path):
    _write(tmp_path, [
        {"shot_id": "S9", "shot": "endcard CTA 品牌 logo 定格", "assets": {"BRAND_X": True}},
    ])
    report = pca.build(tmp_path)
    assert not report["findings"]
    assert report["inputs"]["product_shots"] == 0

    empty = tmp_path / "无分镜"
    empty.mkdir()
    report2 = pca.build(empty)
    assert report2["available"] is False
    assert "storyboard_missing" in _codes(report2)
