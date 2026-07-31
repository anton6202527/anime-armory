# -*- coding: utf-8 -*-
"""广告叙事结构/节拍工艺机检（beat_structure_audit）单测。

盯广告领域纪律与 advisory 底线：
  ① 结构位缺失/错位才报（钩子晚/品牌晚/CTA 缺/四段式倒置/屏字读不完/6s 塞太满）；
     CTA/endcard **有意重复绝不报**；
  ② 时长缺失过半不判时间类信号（不臆造节奏问题）；
  ③ 本检永不产 block（Creative heuristics stay advisory）。
"""
import json

import beat_structure_audit as bsa


def _write(root, rel, payload):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _write_storyboard(root, shots, extra=None):
    doc = {"kind": "ad_storyboard", "shots": shots}
    if extra:
        doc.update(extra)
    return _write(root, "脚本/storyboard.json", doc)


def _codes(report):
    return {f["code"] for f in report["findings"]}


def test_missing_storyboard_degrades_not_blocks(tmp_path):
    report = bsa.build(tmp_path)
    assert report["available"] is False
    assert report["summary"]["block"] == 0
    assert "storyboard_missing" in _codes(report)


def test_clean_30s_ecommerce_storyboard_no_warn(tmp_path):
    """结构位齐整的 30s 电商片：钩子≤3s、品牌开场即露、痛点→方案、CTA 收尾、屏字够读 → 零 warn。"""
    _write(tmp_path, "需求/brief.json",
           {"品牌": "洁风", "产品": "洁风无线吸尘器", "campaign_objective": "电商转化"})
    _write(tmp_path, "创意/concept.json", {"key_message": "一键除尘更轻松", "hook_type": "痛点先行"})
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "duration": 3, "shot": "开场痛点提问：地板多久没真正干净过？桌角放着洁风吸尘器",
         "vo": "你的地板多久没真正干净过", "字幕": "地板脏了"},
        {"shot_id": "S2", "duration": 4, "shot": "女主皱眉看地板灰尘", "vo": "灰尘死角天天扫不完", "字幕": "扫不完"},
        {"shot_id": "S3", "duration": 4, "shot": "使用后效果展示：地板发亮", "vo": "洁风开机十秒见效", "字幕": "十秒见效"},
        {"shot_id": "S4", "duration": 4, "shot": "机身细节滑过", "vo": "大吸力静音电机", "字幕": "静音大吸力"},
        {"shot_id": "S5", "duration": 4, "shot": "实测挑战：麦片酱油一次过", "vo": "麦片酱油一次吸净", "字幕": "实测一次过"},
        {"shot_id": "S6", "duration": 4, "shot": "女主微笑瘫在沙发", "vo": "打扫时间省一半", "字幕": "省一半"},
        {"shot_id": "S7", "duration": 4, "shot": "全屋巡航收尾", "vo": "全屋清洁交给它", "字幕": "全屋清洁"},
        {"shot_id": "S8", "duration": 3, "shot": "endcard：logo + slogan，立即购买", "vo": "立即购买", "字幕": "立即购买"},
    ])
    report = bsa.build(tmp_path)
    assert report["summary"]["warn"] == 0, report["findings"]
    assert report["summary"]["block"] == 0
    assert report["abcd"]["score"] == 4  # A钩子≤3s B品牌≤5s C有人 D有CTA


def test_hook_late_when_first_hook_after_window(tmp_path):
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "duration": 4, "shot": "机身匀速滑过地板"},
        {"shot_id": "S2", "duration": 4, "shot": "痛点提问：地板多久没干净过"},
    ])
    report = bsa.build(tmp_path)
    hit = next(f for f in report["findings"] if f["code"] == "hook_late")
    assert hit["severity"] == "warn"


def test_hook_late_skipped_when_durations_mostly_missing(tmp_path):
    # 时长缺失过半：不臆造节奏问题
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "shot": "机身匀速滑过地板"},
        {"shot_id": "S2", "shot": "机身侧面摇移"},
        {"shot_id": "S3", "duration": 30, "shot": "长演示"},
    ])
    assert "hook_late" not in _codes(bsa.build(tmp_path))


def test_brand_entry_late(tmp_path):
    _write(tmp_path, "需求/brief.json", {"产品": "洁风"})
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "duration": 4, "shot": "女主起床"},
        {"shot_id": "S2", "duration": 4, "shot": "阳光洒进客厅"},
        {"shot_id": "S3", "duration": 4, "shot": "洁风吸尘器登场"},
    ])
    hit = next(f for f in bsa.build(tmp_path)["findings"] if f["code"] == "brand_entry_late")
    assert hit["severity"] == "warn"


def test_brand_entry_unknown_is_info(tmp_path):
    _write_storyboard(tmp_path, [{"shot_id": "S1", "duration": 4, "shot": "女主起床"}])
    hit = next(f for f in bsa.build(tmp_path)["findings"] if f["code"] == "brand_entry_unknown")
    assert hit["severity"] == "info"


def test_cta_missing(tmp_path):
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "duration": 4, "shot": "女主微笑走过草地"},
        {"shot_id": "S2", "duration": 4, "shot": "机身细节缓推"},
    ])
    hit = next(f for f in bsa.build(tmp_path)["findings"] if f["code"] == "cta_missing")
    assert hit["severity"] == "warn"


def test_cta_repeat_is_never_flagged_and_early_cta_only_info(tmp_path):
    # CTA 反复出现是合法手法：只查缺失/错位；早收的 CTA 也只 info
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "duration": 4, "shot": "开场就喊立即购买"},
        {"shot_id": "S2", "duration": 20, "shot": "机身细节缓推"},
        {"shot_id": "S3", "duration": 6, "shot": "风景空镜收尾"},
    ])
    report = bsa.build(tmp_path)
    assert "cta_missing" not in _codes(report)
    hit = next(f for f in report["findings"] if f["code"] == "cta_not_final")
    assert hit["severity"] == "info"


def test_pain_solution_inverted_only_for_conversion_objective(tmp_path):
    shots = [
        {"shot_id": "S1", "duration": 4, "shot": "使用后效果惊艳：地板发亮"},
        {"shot_id": "S2", "duration": 4, "shot": "痛点：地板灰尘难扫"},
    ]
    # 转化目标 → warn
    _write(tmp_path, "需求/brief.json", {"campaign_objective": "电商带货"})
    _write_storyboard(tmp_path, shots)
    hit = next(f for f in bsa.build(tmp_path)["findings"] if f["code"] == "pain_solution_inverted")
    assert hit["severity"] == "warn"
    # 品牌目标 → 不套四段式模板
    _write(tmp_path, "需求/brief.json", {"campaign_objective": "品牌认知"})
    assert "pain_solution_inverted" not in _codes(bsa.build(tmp_path))


def test_supers_hold_short(tmp_path):
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "duration": 1.5, "花字": "这款吸尘器能把十年老灰一次吸干净真的绝了"},
    ])
    hit = next(f for f in bsa.build(tmp_path)["findings"] if f["code"] == "supers_hold_short")
    assert hit["severity"] == "warn"
    assert "S1" in hit["shots"]


def test_mute_pass_gap_and_global_subtitle_exemption(tmp_path):
    shots = [
        {"shot_id": "S1", "duration": 4, "shot": "女主开机", "vo": "开机十秒见效"},
        {"shot_id": "S2", "duration": 4, "shot": "地板变亮", "vo": "灰尘一扫而空"},
    ]
    _write_storyboard(tmp_path, shots)
    assert "mute_pass_gap" in _codes(bsa.build(tmp_path))
    # 顶层留痕"字幕由合成期统一渲染" → 豁免
    _write_storyboard(tmp_path, shots, extra={"字幕": "合成期统一渲染"})
    assert "mute_pass_gap" not in _codes(bsa.build(tmp_path))


def test_six_second_overstuffed(tmp_path):
    _write_storyboard(tmp_path, [
        {"shot_id": f"S{i}", "duration": 1.2, "shot": text}
        for i, text in enumerate(["女主起床", "喝水", "出门", "跑步", "回头"], start=1)
    ])
    hit = next(f for f in bsa.build(tmp_path)["findings"] if f["code"] == "six_second_overstuffed")
    assert hit["severity"] == "warn"


def test_block_always_zero_even_with_many_warns(tmp_path):
    # 钩子缺 + CTA 缺 + 屏字读不完 + 静音缺兜底：一堆 warn，block 仍恒 0
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "duration": 1.0, "shot": "机身滑过", "vo": "开机即用",
         "花字": "这款吸尘器能把十年老灰一次吸干净真的绝了"},
        {"shot_id": "S2", "duration": 4, "shot": "地板变亮", "vo": "灰尘一扫而空"},
    ])
    report = bsa.build(tmp_path)
    assert report["summary"]["warn"] >= 3
    assert report["summary"]["block"] == 0


def test_advisory_cli_strict_and_write(tmp_path):
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "duration": 4, "shot": "女主微笑走过草地"},
    ])
    assert bsa.main([str(tmp_path), "--write"]) == 0  # 默认 exit 0
    assert bsa.main([str(tmp_path), "--strict"]) == 1  # cta_missing 等 warn → strict 退 1
    assert (tmp_path / "生产数据" / "ad_beat_structure_audit.json").exists()
    assert (tmp_path / "生产数据" / "ad_beat_structure_audit.md").exists()


def test_kind_and_schema(tmp_path):
    _write_storyboard(tmp_path, [{"shot_id": "S1", "duration": 3, "shot": "痛点提问开场，立即购买"}])
    report = bsa.build(tmp_path)
    assert report["kind"] == "ad_beat_structure_audit"
    assert set(report["summary"]) >= {"block", "warn", "info"}
    assert set(report["abcd"]) >= {"attention", "branding", "connection", "direction", "score"}
    for f in report["findings"]:
        assert "msg" in f and "severity" in f and "code" in f


# ── 第七轮：品牌脉冲露出 / 声音设计缺失 ──────────────────────────────────────

def _pulse_shots(mid_brand=False):
    """30s：品牌开场露出后中段 20s 无品牌/产品在画（mid_brand=True 时中段补一次轻露出）。"""
    shots = [
        {"shot_id": "S1", "duration": 3, "shot": "开场 星盒app 界面特写", "vo": "碎片又散了"},
        {"shot_id": "S2", "duration": 5, "shot": "女生在地铁上疲惫望窗", "vo": "一天太满"},
        {"shot_id": "S3", "duration": 5, "shot": "咖啡店窗边发呆", "vo": "不想整理"},
        {"shot_id": "S4", "duration": 5, "shot": "街头走路空镜", "vo": "都散着"},
        {"shot_id": "S5", "duration": 5, "shot": "夜晚路灯下等车", "vo": "又一天"},
        {"shot_id": "S6", "duration": 4, "shot": "回家路上", "vo": "回家"},
        {"shot_id": "S7", "duration": 3, "shot": "endcard：星盒 logo + 下载", "vo": "立即下载"},
    ]
    if mid_brand:
        shots[3] = {"shot_id": "S4", "duration": 5, "shot": "手机亮起 星盒 通知角标", "vo": "都散着"}
    return shots


def test_brand_pulse_gap_flagged(tmp_path):
    _write(tmp_path, "需求/brief.json", {"品牌": "星盒", "产品": "星盒手账App"})
    _write_storyboard(tmp_path, _pulse_shots())
    report = bsa.build(tmp_path)
    assert "brand_pulse_gap" in _codes(report)
    assert report["summary"]["block"] == 0


def test_brand_pulse_gap_quiet_with_mid_touch(tmp_path):
    _write(tmp_path, "需求/brief.json", {"品牌": "星盒", "产品": "星盒手账App"})
    _write_storyboard(tmp_path, _pulse_shots(mid_brand=True))
    assert "brand_pulse_gap" not in _codes(bsa.build(tmp_path))


def test_branding_monolithic_and_product_as_brand_exempt(tmp_path):
    _write(tmp_path, "需求/brief.json", {"品牌": "洁风", "产品": "洁风吸尘器"})
    # 单段连续压品牌 8s（>6s）但整体占比 <70% → monolithic info
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "duration": 8, "shot": "洁风 logo 大字压屏", "vo": "洁风"},
        {"shot_id": "S2", "duration": 6, "shot": "女生扫地", "vo": "扫不完"},
        {"shot_id": "S3", "duration": 6, "shot": "街景空镜", "vo": "每天如此"},
    ])
    assert "branding_monolithic" in _codes(bsa.build(tmp_path))
    # 产品即品牌（占比 ≥70%）→ 两信号全豁免
    _write_storyboard(tmp_path, [
        {"shot_id": "S1", "duration": 8, "shot": "洁风机身细节", "vo": "细节"},
        {"shot_id": "S2", "duration": 8, "shot": "洁风吸尘器实拍 产品", "vo": "实拍"},
        {"shot_id": "S3", "duration": 4, "shot": "路人回头", "vo": "谁在用"},
    ])
    codes = _codes(bsa.build(tmp_path))
    assert "branding_monolithic" not in codes and "brand_pulse_gap" not in codes


def test_sound_design_missing_info_and_declared_exempt(tmp_path):
    _write(tmp_path, "需求/brief.json", {"品牌": "星盒"})
    _write_storyboard(tmp_path, _pulse_shots())
    report = bsa.build(tmp_path)
    hits = [f for f in report["findings"] if f["code"] == "sound_design_missing"]
    assert hits and hits[0]["severity"] == "info"
    # brief 显式声明无音乐 → 豁免（决定归人，但不许没想过）
    _write(tmp_path, "需求/brief.json", {"品牌": "星盒", "music": "本轮不使用音乐"})
    assert "sound_design_missing" not in _codes(bsa.build(tmp_path))
    # storyboard 里有 BGM 规划 → 安静
    _write(tmp_path, "需求/brief.json", {"品牌": "星盒"})
    _write_storyboard(tmp_path, _pulse_shots(), extra={"music": "轻钢琴 BGM，副歌处渐强"})
    assert "sound_design_missing" not in _codes(bsa.build(tmp_path))
