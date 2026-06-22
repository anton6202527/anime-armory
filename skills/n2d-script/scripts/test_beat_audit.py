#!/usr/bin/env python3
"""Tests for beat_audit.py (Gap4/5 intra-episode retention + 同质化).

Run from this script's own directory:
    cd skills/n2d-script/scripts && python -m pytest test_beat_audit.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import beat_audit as B  # noqa: E402


def _mk_ep(voiceover, secs=None, ep="第1集"):
    d = tempfile.mkdtemp()
    epd = Path(d) / "脚本" / ep
    epd.mkdir(parents=True)
    (epd / "voiceover.txt").write_text(voiceover, encoding="utf-8")
    if secs:
        (epd / "镜头时长.json").write_text(json.dumps(secs, ensure_ascii=False), encoding="utf-8")
    return d


GOOD = """[镜头1·沈念·惊恐·快] 门被推开了！  ⚡钩子
[镜头2·旁白·低沉] 原来害她的是亲妹妹。
[镜头3·沈念·冷冽·快] 我要让真相大白。  💥爽点
[镜头4·沈念·阴狠·慢] 这局，才刚开始。  🪝集尾
"""


def codes(findings):
    return {c for _, c, _ in findings}


def test_good_episode_passes_core_checks():
    root = _mk_ep(GOOD, {"镜头1": 3, "镜头2": 4, "镜头3": 4, "镜头4": 5})
    findings, stats = B.audit_episode(root, "第1集")
    c = codes(findings)
    assert "no_reversal" not in c
    assert "no_ending_hook" not in c
    assert "no_info_payoff" not in c          # 镜2 给了信息回报
    assert stats["has_reversal"] and stats["has_ending_hook"]


def test_pure_emotion_flags_no_info_payoff():
    vo = """[镜头1·沈念·愤怒·快] 打回去！  ⚡钩子
[镜头2·沈念·痛快·快] 反击赢了！  💥爽点
[镜头3·沈念·阴狠·慢] 报仇雪恨。  🪝集尾
"""
    root = _mk_ep(vo)
    findings, _ = B.audit_episode(root, "第1集")
    assert "no_info_payoff" in codes(findings)


def test_missing_ending_and_reversal_flagged():
    vo = """[镜头1·沈念·平静·慢] 今天天气不错。
[镜头2·沈念·平静·慢] 我们去散步吧。
"""
    root = _mk_ep(vo)
    findings, _ = B.audit_episode(root, "第1集")
    c = codes(findings)
    assert "no_ending_hook" in c and "no_reversal" in c


def test_hook_gap_uses_real_seconds():
    vo = """[镜头1·沈念·惊恐·快] 危机来了！  ⚡钩子
[镜头2·旁白·低沉] 漫长的回忆与铺垫。
[镜头3·沈念·冷冽·快] 真相揭开。  💥爽点
[镜头4·沈念·阴狠·慢] 结束了？  🪝集尾
"""
    # 镜2 给 30s → 钩子间隔超 20s
    root = _mk_ep(vo, {"镜头1": 3, "镜头2": 30, "镜头3": 4, "镜头4": 5})
    findings, _ = B.audit_episode(root, "第1集")
    assert "hook_gap" in codes(findings)


def test_series_homogenization_detects_dupes():
    d = tempfile.mkdtemp()
    same = """[镜头1·沈念·愤怒·快] 反击打脸！  ⚡钩子
[镜头2·沈念·痛快·快] 逆袭翻盘碾压！  💥爽点
[镜头3·沈念·阴狠·慢] 原来竟是她。  🪝集尾
"""
    for i in (1, 2):
        epd = Path(d) / "脚本" / f"第{i}集"
        epd.mkdir(parents=True)
        (epd / "voiceover.txt").write_text(same, encoding="utf-8")
    eps, dups = B.audit_series(d)
    assert len(eps) == 2 and dups and dups[0][2] >= 0.8


if __name__ == "__main__":
    import subprocess
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-q"]))
