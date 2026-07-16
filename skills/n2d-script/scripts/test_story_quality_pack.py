#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import story_quality_pack as sqp  # noqa: E402


def _write_project(root: Path) -> None:
    ep1 = root / "脚本" / "第1集"
    ep2 = root / "脚本" / "第2集"
    ep1.mkdir(parents=True)
    ep2.mkdir(parents=True)
    (ep1 / "voiceover.txt").write_text("真相到底是谁藏起来？门外突然传来脚步。🪝\n", encoding="utf-8")
    (ep2 / "voiceover.txt").write_text("门外脚步逼近，她必须查清真相。\n", encoding="utf-8")
    (ep2 / "storyboard.json").write_text(json.dumps({
        "clips": [{"id": "Clip_01", "description": "CHAR_01 抬眼", "character_ids": ["CHAR_01"]}]
    }, ensure_ascii=False), encoding="utf-8")
    shared = root / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text(json.dumps({
        "characters": [{
            "id": "CHAR_01",
            "name": "沈念",
            "forms": [{
                "form": "常态",
                "performance_signature": {
                    "micro_expression": "嘴角压住",
                    "gaze": "先避后盯",
                    "stance": "肩背微绷",
                    "habitual_gesture": "攥袖",
                    "speech_rhythm": "短句停顿",
                    "action_style": "慢半拍后突然发力",
                },
            }],
        }]
    }, ensure_ascii=False), encoding="utf-8")


def test_story_quality_pack_builds_questions_boundary_and_cues(tmp_path: Path) -> None:
    _write_project(tmp_path)

    pack = sqp.build_pack(tmp_path, "第2集")

    assert pack["kind"] == sqp.KIND
    assert pack["audience_question_ledger"]["questions"]
    assert pack["boundary_continuation"]["status"] == "pass"
    assert pack["boundary_continuation"]["shared_signals"]
    assert pack["performance_prompt_cues"][0]["clip"] == "Clip_01"
    assert "micro_expression" in pack["performance_prompt_cues"][0]["performance_signature_prompt"][0]["prompt_cue"]


def test_performance_cues_do_not_scan_forbidden_presence_for_empty_character_ids(tmp_path: Path) -> None:
    ep = tmp_path / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "voiceover.txt").write_text("破盆在角落发出微光。\n", encoding="utf-8")
    (ep / "storyboard.json").write_text(json.dumps({
        "clips": [
            {
                "id": "ObjectOnly",
                "description": "旧盆近景",
                "character_ids": [],
                "entity_schedule": {"forbidden_presence": ["CHAR_FORBIDDEN"]},
            },
            {
                "id": "LegacyScheduled",
                "description": "旧格式镜头",
                "entity_schedule": {"characters": ["CHAR_ALLOWED"], "forbidden_presence": ["CHAR_FORBIDDEN"]},
            },
        ]
    }, ensure_ascii=False), encoding="utf-8")
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text(json.dumps({
        "characters": [
            {"id": "CHAR_ALLOWED", "forms": [{"form": "常态", "performance_signature": {"freeform": "可用表演"}}]},
            {"id": "CHAR_FORBIDDEN", "forms": [{"form": "常态", "performance_signature": {"freeform": "不应注入"}}]},
        ]
    }, ensure_ascii=False), encoding="utf-8")

    cues = sqp.performance_prompt_cues(tmp_path, "第1集")

    assert [cue["clip"] for cue in cues] == ["LegacyScheduled"]
    cue_text = json.dumps(cues, ensure_ascii=False)
    assert "CHAR_ALLOWED/常态" in cue_text
    assert "CHAR_FORBIDDEN" not in cue_text


def test_audience_questions_ignore_storyboard_negative_constraints(tmp_path: Path) -> None:
    ep = tmp_path / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "voiceover.txt").write_text("火把摇晃，她沉默地站在官道上。\n", encoding="utf-8")
    (ep / "storyboard.json").write_text(json.dumps({
        "clips": [{
            "id": "Clip_01",
            "label": "火把官道",
            "dramatic_function": "沉默压力落地",
            "template_contract": {
                "negative": ["不要火把变成系统光效", "不要随机文字"]
            },
            "entity_schedule": {
                "forbidden_presence": ["现代手机", "系统面板"]
            },
        }]
    }, ensure_ascii=False), encoding="utf-8")

    ledger = sqp.audience_question_ledger(tmp_path, "第1集")

    assert ledger["questions"] == []


def test_question_context_never_truncates_structured_identifier() -> None:
    text = "x" * 28 + "为何" + " audience_effect 明确尺度 scene LOC_01 后续"
    match = sqp.QUESTION_RE.search(text)
    assert match is not None

    context = sqp._context(text, match)

    assert "LOC_01" in context
    assert not context.endswith("LOC_0")


def test_boundary_continuation_accepts_explicit_hook_bridge(tmp_path: Path) -> None:
    ep1 = tmp_path / "脚本" / "第1集"
    ep2 = tmp_path / "脚本" / "第2集"
    ep1.mkdir(parents=True)
    ep2.mkdir(parents=True)
    (ep1 / "voiceover.txt").write_text("门外突然传来脚步。\n", encoding="utf-8")
    (ep2 / "voiceover.txt").write_text("她低头整理袖口。\n", encoding="utf-8")
    (ep2 / "storyboard.json").write_text(json.dumps({
        "hook_bridge": {
            "from_episode": "第1集",
            "bridge_text": "上一集门外脚步延迟到本集 Clip05 兑现。",
            "answers_prev_hook": "来者是求救的人。"
        },
        "clips": [{"id": "Clip_01", "description": "她整理袖口"}]
    }, ensure_ascii=False), encoding="utf-8")

    boundary = sqp.boundary_continuation(tmp_path, "第2集")

    assert boundary["status"] == "pass"
    assert boundary["hook_bridge"]["from_episode"] == "第1集"
    assert boundary["finding"] is None


def test_story_quality_pack_writes_outputs(tmp_path: Path) -> None:
    _write_project(tmp_path)
    pack = sqp.build_pack(tmp_path, "第2集")
    jp, mp = sqp.write_outputs(tmp_path, "第2集", pack)

    assert jp.exists()
    assert mp.exists()
    assert json.loads(jp.read_text(encoding="utf-8"))["kind"] == sqp.KIND
