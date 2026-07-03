#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_hook_endings.py — hook_endings 纯函数单测。

  cd skills/novel-review/scripts && python3 -m pytest test_hook_endings.py
"""
import hook_endings as H


# ── ending_text ──────────────────────────────────────────────────────────────

def test_ending_text_takes_tail():
    text = "首段内容。" * 50 + "这是最后一句钩子。"
    end = H.ending_text(text, tail_chars=10)
    assert len(end) <= 10
    assert "钩子" in end


def test_ending_text_strips_trailing_whitespace():
    assert H.ending_text("正文结尾。\n\n   ") == "正文结尾。"


def test_ending_text_empty():
    assert H.ending_text("") == ""
    assert H.ending_text("   \n  ") == ""


def test_ending_text_short_text_returns_all():
    assert H.ending_text("短结尾。", tail_chars=120) == "短结尾。"


# ── hook_score: 强钩子 vs 平淡 ───────────────────────────────────────────────

def test_strong_cliffhanger_scores_high():
    # 悬念词 + 问号 + 危机词 + 省略号 全中 → 高分
    end = "他猛地回头，刀光已经袭来，难道一切都是陷阱……？"
    assert H.hook_score(end) >= 3


def test_flat_descriptive_ending_scores_low():
    end = "夕阳西下，众人收拾好行囊，安然回到了温暖的家中，吃过晚饭便早早睡下了。"
    assert H.hook_score(end) == 0


def test_empty_ending_scores_zero():
    assert H.hook_score("") == 0


# ── hook_score: 逐信号 ───────────────────────────────────────────────────────

def test_signal_suspense_word():
    assert H.hook_score("他没想到事情会变成这样。") == 1
    assert H.hook_score("门后赫然站着那个人。") >= 1


def test_signal_unresolved_question():
    assert H.hook_score("这一切究竟是谁安排的？") == 1
    assert H.hook_score("Who did this?") == 1  # 英文问号也算


def test_signal_ellipsis_or_dash_ending():
    assert H.hook_score("话音未落，远处忽然传来一阵……") == 1
    assert H.hook_score("他张了张嘴，却什么也没说出——") == 1
    # 收尾带引号仍能识别省略号结尾
    assert H.hook_score("他低声道：“别动……”") == 1


def test_signal_crisis_word():
    assert H.hook_score("巨石轰然坠落。") == 1
    assert H.hook_score("那人应声倒下。") == 1


def test_signal_new_character_arrival():
    # 「身影 + 走出」式新人物登场抛信息
    assert H.hook_score("这时，一道身影从暗处缓缓走出。") == 1


def test_signals_stack():
    # 悬念词 + 危机词 两类叠加
    end = "她竟然倒下了。"
    assert H.hook_score(end) == 2


def test_same_signal_counts_once():
    # 多个同类悬念词只 +1，不堆砌刷分
    end = "突然，他竟然没想到，赫然发现真相。"
    assert H.hook_score(end) == 1


# ── ending_band: 普通 vs 黄金三章更严 ────────────────────────────────────────

def test_band_normal_threshold():
    assert H.ending_band(0, is_golden_three=False) == "warn"
    assert H.ending_band(1, is_golden_three=False) == "warn"
    assert H.ending_band(2, is_golden_three=False) == "ok"   # 普通阈值=2


def test_band_golden_three_is_stricter():
    # score=2 普通章过，黄金三章不过（阈值=3）
    assert H.ending_band(2, is_golden_three=False) == "ok"
    assert H.ending_band(2, is_golden_three=True) == "warn"
    assert H.ending_band(3, is_golden_three=True) == "ok"


def test_band_thresholds_match_constants():
    assert H.ending_band(H.WARN_THRESHOLD, is_golden_three=False) == "ok"
    assert H.ending_band(H.WARN_THRESHOLD - 1, is_golden_three=False) == "warn"
    assert H.ending_band(H.GOLDEN_THRESHOLD, is_golden_three=True) == "ok"
    assert H.ending_band(H.GOLDEN_THRESHOLD - 1, is_golden_three=True) == "warn"


# ── analyze: 优雅跳过 + alert shape + 无阻断级 ──────────────────────────────

def test_analyze_graceful_skip_no_chapters(monkeypatch):
    monkeypatch.setattr(H, "list_chapters", lambda project: [])
    res = H.analyze("/nonexistent")
    assert res["ran"] is False
    assert "skipped" in res


def test_analyze_flags_weak_ending_advisory_only(monkeypatch):
    chapters = [
        (1, "c1.txt", "正文。" * 30 + "众人平安回家，安然睡下，一切都结束了。"),       # 黄金三章·平淡 → warn
        (5, "c5.txt", "正文。" * 30 + "他猛地回头，刀光袭来，难道是陷阱……？"),        # 强钩 → ok
    ]
    monkeypatch.setattr(H, "list_chapters", lambda project: chapters)
    res = H.analyze("/x")
    assert res["ran"] is True
    assert res["blocking"] == 0  # 断章永不阻断
    bands = {s["chapter"]: s["band"] for s in res["scored"]}
    assert bands[1] == "warn"
    assert bands[5] == "ok"
    assert len(res["alerts"]) == 1
    a = res["alerts"][0]
    # alert 字段与 logic_sentry 同形
    for key in ("type", "entity", "severity", "chapter", "evidence", "auto", "note"):
        assert key in a
    assert a["type"] == "weak_chapter_ending"
    assert a["severity"] == "建议级"
    assert a["auto"] is True
    assert a["chapter"] == 1


def test_analyze_golden_three_marked(monkeypatch):
    chapters = [(2, "c2.txt", "结尾平淡。"), (9, "c9.txt", "结尾平淡。")]
    monkeypatch.setattr(H, "list_chapters", lambda project: chapters)
    res = H.analyze("/x")
    golden = {s["chapter"]: s["is_golden"] for s in res["scored"]}
    assert golden[2] is True
    assert golden[9] is False
