#!/usr/bin/env python3
"""tension_mix 纯函数单测。从脚本自身目录跑：
    cd skills/n2d-compose && python -m pytest test_tension_mix.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tension_mix as tm  # noqa: E402


def test_tension_gain_climax_loud_detail_quiet():
    assert tm.tension_gain("爽点·碎切") == 0.95      # 爽点顶上去
    assert tm.tension_gain("爆发·CU") == 0.95
    assert tm.tension_gain("悬念·细节") == 0.40      # 细节压下来
    assert tm.tension_gain("留白·定格") == 0.36
    assert tm.tension_gain("铺垫·长镜") == 0.58


def test_tension_gain_default_and_empty():
    assert tm.tension_gain("没有张力词") == tm.DEFAULT_GAIN
    assert tm.tension_gain(None) == tm.DEFAULT_GAIN


def test_build_segments_accumulates_time():
    clips = [
        {"id": "C1", "duration": "4.0", "rhythm": "铺垫·长镜"},
        {"id": "C2", "duration": 2.0, "rhythm": "爽点·碎切"},
        {"id": "C3", "duration": 0, "rhythm": "x"},        # 0 时长跳过
    ]
    segs = tm.build_segments(clips)
    assert len(segs) == 2
    assert segs[0]["start"] == 0.0 and segs[0]["end"] == 4.0 and segs[0]["gain"] == 0.58
    assert segs[1]["start"] == 4.0 and segs[1]["end"] == 6.0 and segs[1]["gain"] == 0.95


def test_build_volume_expr_nested_and_default():
    segs = [{"start": 0.0, "end": 4.0, "gain": 0.58, "rhythm": "", "id": ""},
            {"start": 4.0, "end": 6.0, "gain": 0.95, "rhythm": "", "id": ""}]
    expr = tm.build_volume_expr(segs)
    assert expr == "if(between(t,0,4),0.58,if(between(t,4,6),0.95,0.6))"
    assert tm.build_volume_expr([]) == "0.6"   # 无分段 → 默认增益常数


def test_expr_is_ffmpeg_safe_chars():
    segs = tm.build_segments([{"id": "C1", "duration": "3.5", "rhythm": "爽点·CU硬切"}])
    expr = tm.build_volume_expr(segs)
    # 只含 ffmpeg volume eval 允许的字符（数字/between/if/逗号/括号/点），无空格/引号
    assert " " not in expr and "'" not in expr and '"' not in expr
    assert expr.startswith("if(between(t,0,3.5),0.95,")
