#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_noncharacter_insert_coverage 出片复核闸集成测试。
cd skills/n2d-review/scripts && python -m pytest test_noncharacter_insert_coverage.py -q"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
import gate


def _project(clips, setting_line=None):
    d = tempfile.mkdtemp(prefix="n2d_insert_gate_")
    sb = gate.storyboard_path(d, "第1集")
    os.makedirs(os.path.dirname(sb), exist_ok=True)
    with open(sb, "w", encoding="utf-8") as f:
        json.dump({"clips": clips}, f, ensure_ascii=False)
    if setting_line is not None:
        with open(os.path.join(d, "_设置.md"), "w", encoding="utf-8") as f:
            f.write(setting_line + "\n")
    return d


def _hits(sev):
    return [f for f in gate.findings if f["dim"] == "非人物特写" and f["sev"] == sev]


def _char_clips(n):
    return [{"id": f"Clip_{i:02d}", "continuity": {"shot_size": "MS 中景"}, "desc": f"人物对话{i}"} for i in range(1, n + 1)]


def test_system_expected_uncovered_blocks_when_enforced():
    gate.findings.clear()
    clips = _char_clips(4) + [{"id": "Clip_05", "continuity": {"shot_size": "MCU"}, "desc": "他盯着属性面板发呆"}]
    root = _project(clips, setting_line="- 非人物特写覆盖：启用")
    gate.check_noncharacter_insert_coverage(root, "第1集")
    assert _hits(gate.BLOCK), gate.findings


def test_legacy_no_setting_is_warn_only():
    gate.findings.clear()
    clips = _char_clips(4) + [{"id": "Clip_05", "continuity": {"shot_size": "MCU"}, "desc": "他盯着属性面板发呆"}]
    root = _project(clips, setting_line=None)  # 老项目：无选择点 → 宽限仅提示
    gate.check_noncharacter_insert_coverage(root, "第1集")
    assert not _hits(gate.BLOCK), gate.findings
    assert _hits(gate.WARN), gate.findings


def test_system_covered_no_finding():
    gate.findings.clear()
    clips = _char_clips(4) + [{"id": "Clip_05", "template": "system_panel", "continuity": {"shot_size": "CU"}, "desc": "系统面板底框"}]
    root = _project(clips, setting_line="- 非人物特写覆盖：启用")
    gate.check_noncharacter_insert_coverage(root, "第1集")
    assert not gate.findings, gate.findings


def test_off_mode_silent():
    gate.findings.clear()
    clips = _char_clips(4) + [{"id": "Clip_05", "continuity": {"shot_size": "MCU"}, "desc": "属性面板 系统面板"}]
    root = _project(clips, setting_line="- 非人物特写覆盖：关闭")
    gate.check_noncharacter_insert_coverage(root, "第1集")
    assert not gate.findings, gate.findings


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
