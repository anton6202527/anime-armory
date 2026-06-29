# -*- coding: utf-8 -*-
"""cd skills/novel/_lib && python3 -m pytest test_repetition.py"""
import repetition as rep


def test_adjacent_chapter_jaccard_identical_vs_distinct():
    a = "他推开门屋里一片漆黑窗外的风卷着雪远处传来钟声她说你终于来了"
    assert rep.adjacent_chapter_jaccard(a, a) == 1.0
    b = "完全不一样的另一段文字讲述清晨阳光洒满整片金色的麦田少年奔跑"
    assert rep.adjacent_chapter_jaccard(a, b) < 0.05
    assert rep.adjacent_chapter_jaccard("短", "短") == 0.0


def test_cross_chapter_flags_near_duplicate():
    shared = "林夜推开斑驳的铁门走进废弃工厂霉味混着铁锈扑面而来他握紧手中的探测仪屏幕幽幽地亮着"
    findings, summary = rep.cross_chapter_repetition([
        (1, shared + "今天他在东侧角落发现了第一块碎片。"),
        (2, shared + "今天他在西侧管道找到了第二块碎片。"),
    ])
    dims = {(s, d) for _, s, d, _, _ in findings}
    assert ("🟡", "跨章重复") in dims
    assert summary["adjacent_max_jaccard"] >= rep.REP_ADJ_JACCARD_YELLOW


def test_cross_chapter_mechanical_opener_and_sentence_reuse():
    opener = "清晨第一缕阳光照进窗棂的时候林夜已经醒了"
    line = "系统冰冷的声音在脑海中响起宿主请完成今日任务否则将受到惩罚"
    chapters = [(n, opener + f"独特情节甲乙丙{n}。{line}。他继续前行。") for n in (1, 2, 3, 4)]
    findings, summary = rep.cross_chapter_repetition(chapters)
    dims = {(s, d) for _, s, d, _, _ in findings}
    assert ("🟡", "机械开篇") in dims
    assert ("🟡", "机械句复用") in dims


def test_cross_chapter_clean_is_silent():
    findings, summary = rep.cross_chapter_repetition([
        (1, "他推开门屋里一片漆黑窗外的风卷着雪远处传来钟声。"),
        (2, "清晨阳光洒满整片金色麦田少年沿着田埂奔跑笑声飞扬。"),
        (3, "深夜的码头汽笛长鸣货轮缓缓驶离港口灯火渐远。"),
    ])
    assert findings == []
    assert summary["adjacent_max_jaccard"] < rep.REP_ADJ_JACCARD_GREEN


def test_retention_prior_levels_and_cap():
    assert rep.retention_prior(None) == {"level": "none", "points": 0, "reasons": []}
    # 干净 → none / 0 分
    clean = {"adjacent_max_jaccard": 0.02, "mechanical_opener_groups": 0, "repeated_sentences": 0}
    assert rep.retention_prior(clean)["level"] == "none"
    assert rep.retention_prior(clean)["points"] == 0
    # 高近重复 + 机械开篇 + 复用句 → high，points 封顶 -3
    bad = {"adjacent_max_jaccard": 0.30, "mechanical_opener_groups": 2, "repeated_sentences": 5}
    out = rep.retention_prior(bad)
    assert out["level"] == "high"
    assert out["points"] == -3
    assert out["reasons"]
    # 轻度 → mild / -1
    mild = {"adjacent_max_jaccard": 0.12, "mechanical_opener_groups": 0, "repeated_sentences": 0}
    assert rep.retention_prior(mild)["level"] == "mild"
    assert rep.retention_prior(mild)["points"] == -1
