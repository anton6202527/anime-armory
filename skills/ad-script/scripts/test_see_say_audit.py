# -*- coding: utf-8 -*-
"""广告分镜声画对位机检（see_say_audit）单测。

盯 DRTV 领域纪律与 advisory 底线：
  ① 只有 VO 说了**可演示的具体卖点**而画面没有对应物才报——情绪 VO 铺产品 beauty 镜合法；
  ② 片尾 endcard/logo/CTA 板与纯品牌口号 VO 必须豁免，绝不误报；
  ③ 本检永不产 block（Creative heuristics stay advisory）。
"""
import json

import see_say_audit as ssa


def _write_storyboard(root, shots):
    path = root / "脚本" / "storyboard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"kind": "ad_storyboard", "shots": shots}, ensure_ascii=False), encoding="utf-8")
    return path


def _write_brief(root, brief):
    path = root / "需求" / "brief.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    return path


def _codes(report):
    return {f["code"] for f in report["findings"]}


def test_missing_storyboard_degrades_not_blocks(tmp_path):
    report = ssa.build(tmp_path)
    assert report["available"] is False
    assert report["summary"]["block"] == 0
    assert "storyboard_missing" in _codes(report)


def test_concrete_claim_without_visual_flagged(tmp_path):
    # VO 说防水实测，画面却是咖啡店情绪空镜 → see_say_mismatch
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "scene": "咖啡店",
         "vo": "这款手表防水实测五十米深度依然正常运行",
         "shot": "女孩在咖啡店窗边微笑聊天喝咖啡"},
    ])
    report = ssa.build(tmp_path)
    hit = [f for f in report["findings"] if f["code"] == "see_say_mismatch"]
    assert hit and hit[0]["severity"] == "warn"
    assert report["summary"]["block"] == 0


def test_matching_vo_and_visual_clean(tmp_path):
    # 说到即演到：VO 防水实测，画面就在演示防水 → 不报
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "scene": "水下",
         "vo": "这款手表防水实测五十米深度依然正常运行",
         "shot": "手表沉入水中防水实测特写演示"},
    ])
    report = ssa.build(tmp_path)
    assert "see_say_mismatch" not in _codes(report)
    assert report["inputs"]["eligible_shots"] == 1


def test_slogan_over_beauty_shot_exempt(tmp_path):
    # 纯品牌口号 VO 铺产品 beauty 镜：豁免镜 + 口号 VO，双重不判
    _write_brief(tmp_path, {"brand": "净界者", "product": "净界者K1吸尘器", "slogan": "净界者，让生活更美好"})
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "scene": "白底", "shot": "产品特写 beauty shot 旋转展示",
         "vo": "净界者，让生活更美好"},
    ])
    report = ssa.build(tmp_path)
    assert "see_say_mismatch" not in _codes(report)


def test_emotional_vo_without_concrete_claim_not_flagged(tmp_path):
    # 情绪 VO（无具体卖点词）铺生活空镜：合法手法，不要求逐字对画
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "scene": "海边",
         "vo": "有些时刻，值得你放下一切慢慢感受",
         "shot": "女孩赤脚走在海边沙滩上回头"},
    ])
    report = ssa.build(tmp_path)
    assert "see_say_mismatch" not in _codes(report)


def test_brief_product_token_counts_as_concrete(tmp_path):
    # VO 点名产品，画面没有产品也没有相似描述 → 报；画面出现产品 → 不报
    _write_brief(tmp_path, {"brand": "净界者", "product": "K1吸尘器"})
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "scene": "客厅",
         "vo": "K1吸尘器让你的地板焕然一新亮起来",
         "shot": "一家人坐在沙发上开心看电视"},
        {"shot_id": "S2", "scene": "客厅",
         "vo": "K1吸尘器让你的地板焕然一新亮起来",
         "shot": "K1吸尘器滑过地板灰尘瞬间消失"},
    ])
    report = ssa.build(tmp_path)
    flagged = [f["shots"][0] for f in report["findings"] if f["code"] == "see_say_mismatch"]
    assert flagged == ["S1"]


def test_majority_mismatch_aggregates_ratio_info(tmp_path):
    shots = [
        {"shot_id": f"S{i}", "scene": "咖啡店",
         "vo": f"实测对比数据显示清洁效率提升第{i}成",
         "shot": "女孩在咖啡店窗边发呆看雨"}
        for i in range(3)
    ]
    _write_storyboard(tmp_path, shots)
    report = ssa.build(tmp_path)
    ratio = [f for f in report["findings"] if f["code"] == "vo_visual_ratio"]
    assert ratio and ratio[0]["severity"] == "info"
    assert report["summary"]["block"] == 0


def test_missing_visual_is_insufficient_not_flagged(tmp_path):
    # 画面没写：不臆造声画错位
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "vo": "这款手表防水实测五十米深度依然正常"},
    ])
    report = ssa.build(tmp_path)
    assert "see_say_mismatch" not in _codes(report)


def test_no_vo_data_reported(tmp_path):
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "scene": "客厅", "shot": "产品滑过地板"},
    ])
    report = ssa.build(tmp_path)
    hit = [f for f in report["findings"] if f["code"] == "no_vo_data"]
    assert hit and hit[0]["severity"] == "info"


def test_advisory_never_blocks_and_cli(tmp_path):
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "scene": "咖啡店",
         "vo": "这款手表防水实测五十米深度依然正常运行",
         "shot": "女孩在咖啡店窗边微笑聊天喝咖啡"},
    ])
    report = ssa.build(tmp_path)
    assert report["summary"]["block"] == 0
    assert report["summary"]["warn"] >= 1
    # 默认 exit 0；--strict 才因 warn 退 1
    assert ssa.main([str(tmp_path), "--write"]) == 0
    assert ssa.main([str(tmp_path), "--strict"]) == 1
    assert (tmp_path / "生产数据" / "ad_see_say_audit.json").exists()
    assert (tmp_path / "生产数据" / "ad_see_say_audit.md").exists()


def test_kind_and_schema(tmp_path):
    _write_storyboard(tmp_path, [{"shot_id": "S1", "scene": "白底", "shot": "产品旋转"}])
    report = ssa.build(tmp_path)
    assert report["kind"] == "ad_see_say_audit"
    assert set(report["summary"]) >= {"block", "warn", "info"}
    # findings 必须用 ad house 的 msg 键
    for f in report["findings"]:
        assert "msg" in f and "severity" in f and "code" in f


# ── 第七轮：信息态桥段 insert 覆盖（info_beat_no_insert）─────────────────────

def test_info_beats_without_insert_flagged(tmp_path):
    _write_brief(tmp_path, {"brand": "洁风", "product": "洁风吸尘器"})
    _write_storyboard(tmp_path, [
        {"shot_id": "C01", "vo": "续航 48 小时，只要 199 元", "shot": "女生坐在沙发上微笑说话"},
        {"shot_id": "C02", "vo": "三档功率 15 种模式", "shot": "女生站在客厅中央比划"},
    ])
    report = ssa.build(tmp_path)
    assert "info_beat_no_insert" in _codes(report)
    assert report["summary"]["block"] == 0


def test_info_beats_with_insert_quiet(tmp_path):
    _write_brief(tmp_path, {"brand": "洁风", "product": "洁风吸尘器"})
    _write_storyboard(tmp_path, [
        {"shot_id": "C01", "vo": "续航 48 小时，只要 199 元", "shot": "女生坐在沙发上微笑说话"},
        {"shot_id": "C02", "vo": "三档功率 15 种模式", "shot": "机身按键特写 手部操作演示"},
    ])
    assert "info_beat_no_insert" not in _codes(ssa.build(tmp_path))


def test_single_info_beat_not_flagged(tmp_path):
    # 信息态句不足 2 句不报（宁缺毋滥）
    _write_brief(tmp_path, {"brand": "洁风"})
    _write_storyboard(tmp_path, [
        {"shot_id": "C01", "vo": "只要 199 元", "shot": "女生微笑"},
        {"shot_id": "C02", "vo": "轻松一点", "shot": "女生瘫在沙发"},
    ])
    assert "info_beat_no_insert" not in _codes(ssa.build(tmp_path))
