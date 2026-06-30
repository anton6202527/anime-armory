"""audio_continuity 单测——VEA 情绪弧 / ACC 口音 / BGM 衔接 纯函数 + 端到端。

cd skills/n2d-review/scripts && python3 -m pytest test_audio_continuity.py
"""
from __future__ import annotations

from pathlib import Path

import audio_continuity as a


# ── 纯函数 ──────────────────────────────────────────────────────────────────

def test_classify_emo():
    assert a.classify_emo("惊恐") == "fearful"
    assert a.classify_emo("哭求") == "sad"
    assert a.classify_emo("冷冽") == "serious"
    assert a.classify_emo("平静") == "neutral"


def test_parse_voiceover_only_three_field_lines():
    txt = ("# 标题\n[镜头5·小禾·惊恐·快] 娘娘！救命！\n"
           "[镜头7·沈念·平静] 我恨你们，血债血偿！\n普通行不解析\n")
    lines = a.parse_voiceover(txt)
    assert [l["shot"] for l in lines] == [5, 7]
    assert lines[0]["role"] == "小禾" and lines[0]["emotion"] == "惊恐"


def test_vea_flags_strong_line_with_flat_tag():
    lines = [
        {"shot": 5, "role": "小禾", "emotion": "惊恐", "line": "救命啊！"},     # tag 强→不报
        {"shot": 7, "role": "沈念", "emotion": "平静", "line": "我恨你们，血债血偿！"},  # 强台词×平淡→报
    ]
    rows = a.vea_findings(lines)
    assert len(rows) == 1 and rows[0]["shot"] == "镜头7" and rows[0]["verdict"] == "warn"


def test_vea_flags_missing_emotion_tag():
    rows = a.vea_findings([{"shot": 3, "role": "沈念", "emotion": "", "line": "随便一句"}])
    assert rows[0]["verdict"] == "warn" and "缺情绪标注" in rows[0]["message"]


def test_line_is_strong():
    assert a.line_is_strong("住手！放开她！")
    assert a.line_is_strong("我恨你") and a.line_is_strong("呜呜哭")
    assert not a.line_is_strong("今日天气尚可，随我去御花园。")


def test_accent_findings_conflict_and_lock():
    rows = a.accent_findings({"沈念": {"voice_key": "A", "accent": "古风腔"},
                              "柳娘子": {"voice_key": "A", "口音": "尖利"}})
    assert any(r["verdict"] == "warn" and "冲突口音" in r["message"] for r in rows)
    assert sum(1 for r in rows if r["verdict"] == "info") == 2     # 两个锁口音提醒
    assert a.accent_findings(None) == []                          # 无 voicemap 不报


def test_bgm_findings_tempo_whiplash():
    warn = a.bgm_findings("- 开场：留白空灵舒缓\n- 高潮：加速重击鼓点")
    assert len(warn) == 1 and warn[0]["verdict"] == "warn"
    # 有过渡词 → 不报
    assert a.bgm_findings("- 开场：留白\n- 渐渐加速推向高潮重击") == []
    # 同速度相邻 → 不报
    assert a.bgm_findings("- A：舒缓慢\n- B：空灵留白") == []


# ── 端到端 ──────────────────────────────────────────────────────────────────

def test_analyze_skips_without_voiceover(tmp_path: Path):
    rep = a.analyze(str(tmp_path / "剧"), "第1集")
    assert rep["available"] is False and rep["vea"] == []


def test_analyze_end_to_end(tmp_path: Path):
    root = tmp_path / "剧"
    (root / "脚本" / "第1集").mkdir(parents=True)
    (root / "脚本" / "第1集" / "voiceover.txt").write_text(
        "[镜头1·沈念·平静] 我恨你们，血债血偿！\n[镜头2·旁白·低沉] 夜色渐深。\n", encoding="utf-8")
    (root / "脚本" / "第1集" / "bgm.txt").write_text(
        "- 开场：留白空灵\n- 高潮：加速重击鼓点\n", encoding="utf-8")
    (root / "设定库").mkdir(parents=True)
    (root / "设定库" / "voicemap.json").write_text(
        '{"沈念":{"voice_key":"A","accent":"古风腔"},"柳娘子":{"voice_key":"A","accent":"尖利"}}',
        encoding="utf-8")
    rep = a.analyze(str(root), "第1集")
    assert rep["available"] is True
    assert any(r["verdict"] == "warn" for r in rep["vea"])   # 镜头1 强台词×平淡
    assert any(r["verdict"] == "warn" for r in rep["acc"])   # voice_key A 口音冲突
    assert any(r["verdict"] == "warn" for r in rep["bgm"])   # 速度whiplash


def test_emotion_audio_reconcile_flags_strong_but_quiet():
    lines = [
        {"shot": 1, "role": "沈念", "emotion": "愤怒", "line": "我恨你们，血债血偿！"},
        {"shot": 2, "role": "沈念", "emotion": "平静", "line": "走吧。"},
        {"shot": 3, "role": "旁白", "emotion": "低沉", "line": "夜色渐深。"},
        {"shot": 4, "role": "沈念", "emotion": "平静", "line": "嗯。"},
    ]
    flow = [
        {"shot": 1, "energy": {"energy_score": 0.10}, "emotion_applied": "angry"},  # 强情绪却垫底
        {"shot": 2, "energy": {"energy_score": 0.50}},
        {"shot": 3, "energy": {"energy_score": 0.60}},
        {"shot": 4, "energy": {"energy_score": 0.70}},
    ]
    rows = a.emotion_audio_findings(lines, flow)
    assert any(r["verdict"] == "warn" and "镜头1" in r["shot"] for r in rows)


def test_emotion_audio_reconcile_skips_flat_energy():
    lines = [{"shot": i, "role": "沈念", "emotion": "愤怒", "line": "我恨你们！"} for i in range(1, 5)]
    flow = [{"shot": i, "energy": {"energy_score": 0.30}} for i in range(1, 5)]  # 无起伏（占位/say）
    assert a.emotion_audio_findings(lines, flow) == []


def test_emotion_audio_reconcile_strong_loud_ok():
    lines = [
        {"shot": 1, "role": "沈念", "emotion": "愤怒", "line": "我恨你们！"},
        {"shot": 2, "role": "沈念", "emotion": "平静", "line": "走吧。"},
        {"shot": 3, "role": "旁白", "emotion": "低沉", "line": "夜色。"},
        {"shot": 4, "role": "沈念", "emotion": "平静", "line": "嗯。"},
    ]
    flow = [
        {"shot": 1, "energy": {"energy_score": 0.90}},  # 强情绪且响 → 不报
        {"shot": 2, "energy": {"energy_score": 0.10}},
        {"shot": 3, "energy": {"energy_score": 0.20}},
        {"shot": 4, "energy": {"energy_score": 0.30}},
    ]
    assert a.emotion_audio_findings(lines, flow) == []


def test_emotion_audio_reconcile_too_few_segments():
    lines = [{"shot": 1, "role": "沈念", "emotion": "愤怒", "line": "恨！"}]
    flow = [{"shot": 1, "energy": {"energy_score": 0.0}}]
    assert a.emotion_audio_findings(lines, flow) == []
