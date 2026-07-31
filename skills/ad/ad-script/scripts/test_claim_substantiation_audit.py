# -*- coding: utf-8 -*-
"""承诺-证据配对预检（claim_substantiation_audit）单测。

盯配对纪律与假阳性防线：① 证言/结果句/紧迫话术——有免责/依据即安静，缺才报；
② 价格算术纯数字零假阳性；③ advisory 底线 summary.block 恒 0。
"""
import json

import claim_substantiation_audit as csa


def _write_storyboard(root, shots):
    path = root / "脚本" / "storyboard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"shots": shots}, ensure_ascii=False), encoding="utf-8")


def _write_vo(root, text):
    path = root / "脚本" / "voiceover.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _codes(report):
    return {f["code"] for f in report["findings"]}


def test_missing_artifacts_degrades_not_blocks(tmp_path):
    report = csa.build(tmp_path)
    assert report["available"] is False and report["summary"]["block"] == 0


def test_testimonial_without_disclaimer_flagged(tmp_path):
    _write_vo(tmp_path, "我自从用了这款精华，皮肤真的不一样了。")
    _write_storyboard(tmp_path, [{"shot_id": "C01", "vo": "亲测好用"}])
    report = csa.build(tmp_path)
    assert "testimonial_needs_disclaimer" in _codes(report)
    assert report["summary"]["block"] == 0


def test_testimonial_with_disclaimer_quiet(tmp_path):
    _write_vo(tmp_path, "我自从用了这款精华，皮肤真的不一样了。")
    _write_storyboard(tmp_path, [{"shot_id": "C01", "vo": "亲测好用",
                                  "legal_lines": ["情景演绎，非真实用户体验"]}])
    assert "testimonial_needs_disclaimer" not in _codes(csa.build(tmp_path))


def test_results_claim_needs_disclosure(tmp_path):
    _write_vo(tmp_path, "28天淡化细纹，提升30%弹性。")
    report = csa.build(tmp_path)
    assert "results_claim_no_disclosure" in _codes(report)
    _write_storyboard(tmp_path, [{"shot_id": "C01", "legal_lines": ["依据：XX 实验室测试报告，效果因人而异"]}])
    assert "results_claim_no_disclosure" not in _codes(csa.build(tmp_path))


def test_price_math_mismatch_pure_arithmetic():
    issues = csa.price_math_issues("原价199元 现价139元 全场5折")
    assert issues and "5折" in issues[0]          # 139/199≈7折 ≠ 5折
    assert csa.price_math_issues("原价200元 现价100元 全场5折") == []   # 算术正确安静
    assert csa.price_math_issues("原价100元 现价150元") != []           # 现价高于原价


def test_strikethrough_price_needs_basis(tmp_path):
    _write_vo(tmp_path, "原价299元，现价199元，只要一杯咖啡钱。")
    report = csa.build(tmp_path)
    assert "strikethrough_price_no_basis" in _codes(report)
    _write_vo(tmp_path, "原价299元（七日内最低成交价），现价199元。")
    assert "strikethrough_price_no_basis" not in _codes(csa.build(tmp_path))


def test_urgency_without_substantiation(tmp_path):
    _write_vo(tmp_path, "限时特惠，仅剩50件，手慢无！")
    assert "urgency_no_substantiation" in _codes(csa.build(tmp_path))
    _write_vo(tmp_path, "限时特惠，活动时间至8月1日，库存以页面显示为准。")
    assert "urgency_no_substantiation" not in _codes(csa.build(tmp_path))


def test_induce_click_flagged(tmp_path):
    _write_vo(tmp_path, "点击有惊喜，恭喜获奖！")
    assert "induce_click_reject" in _codes(csa.build(tmp_path))


def test_clean_copy_quiet(tmp_path):
    _write_vo(tmp_path, "把碎片收成一页手账草稿。星盒手账，把今天稳稳收好。")
    report = csa.build(tmp_path)
    assert report["summary"]["warn"] == 0 and report["summary"]["block"] == 0
