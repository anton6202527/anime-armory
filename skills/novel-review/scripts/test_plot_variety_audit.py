# -*- coding: utf-8 -*-
"""test_plot_variety_audit — 情节节拍多样性机检。

Run: cd skills/novel-review/scripts && python3 -m pytest test_plot_variety_audit.py
"""
import os

import plot_variety_audit as pva


# ── 纯函数：节拍/钩型/开篇型识别 ─────────────────────────────────────────────

def test_dominant_beat_requires_min_hits():
    assert pva.dominant_beat("他淡淡说了一句打脸。") is None            # 单次命中不算主导
    assert pva.dominant_beat("当众打脸，反杀翻盘，全场傻眼。") == "打脸翻盘"


def test_dominant_beat_picks_highest():
    text = "突破！突破！再度突破！顺手打脸。" * 2
    assert pva.dominant_beat(text) == "升级突破"


def test_hook_type_priority_and_none():
    assert pva.hook_type("他抬起头：这是为什么？") == "问句钩"
    assert pva.hook_type("门外，竟是那个早已死去的人。") == "反转钩"
    assert pva.hook_type("平静的一天结束了。大家都睡了。") is None


def test_opening_type():
    assert pva.opening_type("「你来了。」他说。") == "对话开头"
    assert pva.opening_type("翌日，天光微亮。") == "时间开头"
    assert pva.opening_type("他从梦中醒来，睁开眼。") == "醒来开头"
    assert pva.opening_type("大殿之上鸦雀无声。") is None


# ── 信号检测 ────────────────────────────────────────────────────────────────

def test_beat_monotony_run_of_three():
    alerts = []
    seq = [(1, "打脸翻盘"), (2, "打脸翻盘"), (3, "打脸翻盘"), (4, "升级突破")]
    assert pva.detect_beat_monotony(seq, alerts) == 1
    assert alerts[0]["type"] == "beat_monotony" and alerts[0]["chapters"] == [1, 2, 3]
    assert alerts[0]["severity"] == "建议级"


def test_beat_monotony_broken_by_none():
    alerts = []
    seq = [(1, "打脸翻盘"), (2, None), (3, "打脸翻盘"), (4, "打脸翻盘")]
    assert pva.detect_beat_monotony(seq, alerts) == 0    # None（无节拍/豁免章）打断 run


def test_beat_cycle_abab():
    alerts = []
    seq = [(i + 1, b) for i, b in enumerate(
        ["危机压迫", "打脸翻盘", "危机压迫", "打脸翻盘", "危机压迫", "打脸翻盘"])]
    assert pva.detect_beat_cycle(seq, alerts) == 1
    assert alerts[0]["type"] == "beat_cycle_repetition"
    assert "危机压迫→打脸翻盘" in alerts[0]["note"]


def test_beat_cycle_not_flagged_when_varied():
    alerts = []
    seq = [(1, "危机压迫"), (2, "打脸翻盘"), (3, "奇遇馈赠"), (4, "身份揭露"),
           (5, "情感兑现"), (6, "升级突破")]
    assert pva.detect_beat_cycle(seq, alerts) == 0


def test_payoff_gap_commercial_vs_literary():
    seq = [(1, 3), (2, 0), (3, 0), (4, 0), (5, 2)]     # 连续 3 章零爽点
    alerts = []
    assert pva.detect_payoff_gap(seq, alerts, profile=pva.PROFILE_COMMERCIAL) == 1
    assert alerts[0]["severity"] == "建议级" and alerts[0]["chapters"] == [2, 3, 4]
    alerts2 = []
    # 品质向：上限 4，3 章铺垫合法
    assert pva.detect_payoff_gap(seq, alerts2, profile="品质向") == 0


def test_hook_type_repetition_and_opening_repetition():
    alerts = []
    hooks = [(1, "问句钩"), (2, "问句钩"), (3, "问句钩"), (4, "危机钩")]
    assert pva.detect_hook_type_repetition(hooks, alerts) == 1
    assert alerts[0]["severity"] == "info"
    alerts2 = []
    openings = [(i, "对话开头") for i in range(1, 5)]
    assert pva.detect_opening_repetition(openings, alerts2) == 1


# ── analyze() 集成（真实目录结构 + 检测器契约） ───────────────────────────────

def _write_chapters(root, texts):
    d = os.path.join(root, "章节")
    os.makedirs(d, exist_ok=True)
    for i, t in enumerate(texts, 1):
        with open(os.path.join(d, f"第{i:02d}章.md"), "w", encoding="utf-8") as f:
            f.write(t)


def test_analyze_empty_project_skips(tmp_path):
    res = pva.analyze(str(tmp_path))
    assert res["ran"] is False and "skipped" in res


def test_analyze_flags_monotony_and_is_advisory(tmp_path):
    faceslap = "当众打脸，反杀翻盘，众人傻眼求饶。" * 3 + "他冷冷道：还有谁？"
    _write_chapters(str(tmp_path), [faceslap, faceslap, faceslap])
    res = pva.analyze(str(tmp_path))
    assert res["ran"] is True
    assert res["blocking"] == 0                              # advisory 纪律：恒 0
    types = {a["type"] for a in res["alerts"]}
    assert "beat_monotony" in types
    assert all(a["severity"] in ("建议级", "info") for a in res["alerts"])


def test_analyze_reports_per_chapter_beats(tmp_path):
    _write_chapters(str(tmp_path), ["突破！突破！终于突破瓶颈，境界提升。这是为什么？"])
    res = pva.analyze(str(tmp_path))
    row = res["beats"][0]
    assert row["dominant_beat"] == "升级突破"
    assert row["hook_type"] == "问句钩"
