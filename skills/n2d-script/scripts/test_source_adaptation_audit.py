#!/usr/bin/env python3
"""Tests for source_adaptation_audit.py."""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import source_adaptation_audit as SA  # noqa: E402


def _mk_ep(raw, voiceover="", storyboard=None, triage=None):
    d = tempfile.mkdtemp()
    ep = Path(d) / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "raw.txt").write_text(raw, encoding="utf-8")
    if voiceover:
        (ep / "voiceover.txt").write_text(voiceover, encoding="utf-8")
    if storyboard is not None:
        (ep / "storyboard.json").write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")
    if triage is not None:
        (ep / "adaptation_triage.json").write_text(json.dumps(triage, ensure_ascii=False), encoding="utf-8")
    return d


RAW = "沈念被逼到宫墙下。门外突然传来系统提示【妖血觉醒】。她发现真相，反击柳娘子！"


def codes(result):
    return {f["code"] for f in result["findings"]}


def test_passes_when_system_term_and_event_are_adapted():
    root = _mk_ep(
        RAW,
        "[镜头1·沈念·惊恐·快] 系统提示【妖血觉醒】。\n"
        "[镜头2·沈念·冷冽·快] 原来柳娘子害我，我要反击！  💥爽点\n"
        "[镜头3·沈念·阴狠·慢] 这局才刚开始。  🪝集尾\n",
    )

    result = SA.audit(root, "第1集")

    assert result["ok"]
    assert codes(result) == set()


def test_missing_bracketed_source_term_is_warned():
    root = _mk_ep(
        RAW,
        "[镜头1·沈念·惊恐·快] 门外传来怪声。\n"
        "[镜头2·沈念·冷冽·快] 我要反击柳娘子！  💥爽点\n",
    )

    result = SA.audit(root, "第1集")

    assert not result["ok"]
    assert "source_term_missing" in codes(result)


def test_missing_adaptation_is_must():
    root = _mk_ep(RAW)

    result = SA.audit(root, "第1集")

    assert not result["ok"]
    assert "missing_adaptation" in codes(result)


def test_key_event_omission_is_warned():
    root = _mk_ep(
        "沈念发现真相：柳娘子下毒害死了她的兄长！她拔剑反击。",
        "[镜头1·旁白·平静·慢] 天色渐晚，院中很安静。\n",
    )

    result = SA.audit(root, "第1集")

    assert not result["ok"]
    assert "source_event_maybe_omitted" in codes(result)


def test_scene_function_loss_is_warned():
    root = _mk_ep(
        "沈念为了保护妹妹决定公开证据，因此暴露身份，被全城通缉。",
        "[镜头1·旁白·平静·慢] 天色渐晚，院中很安静。\n",
    )

    result = SA.audit(root, "第1集")

    assert not result["ok"]
    assert "scene_function_maybe_lost" in codes(result)


def test_logged_detail_rewrite_downgrades_source_term_warning():
    root = _mk_ep(
        RAW,
        "[镜头1·沈念·惊恐·快] 门外血光炸开，她的血脉突然暴走。\n"
        "[镜头2·沈念·冷冽·快] 柳娘子害我，我当场反杀！  💥爽点\n",
        triage={
            "kind": "n2d_adaptation_triage",
            "items": [{
                "id": "AT_001",
                "source_span": "raw.txt:门外突然传来系统提示【妖血觉醒】",
                "decision": "dramatize",
                "change_type": "rewrite_detail",
                "reason": "系统提示改成更强视觉化的血光觉醒，保留觉醒功能并提高短剧开场冲击。",
                "delivery": "voiceover 镜头1 + storyboard Clip_01 用血光暴走替代【妖血觉醒】字面系统音。",
                "adaptation_delta": {
                    "changed_from": "系统提示【妖血觉醒】",
                    "changed_to": "血光炸开，血脉暴走",
                    "preserved_function": ["觉醒", "危机升级", "开场钩子"],
                },
            }],
        },
    )

    result = SA.audit(root, "第1集")

    assert "source_term_missing" not in codes(result)
    assert "source_term_reworked_by_triage" in codes(result)
    assert result["ok"]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
