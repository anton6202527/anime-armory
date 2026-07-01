#!/usr/bin/env python3
"""Tests for script_quality_gate.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import script_quality_gate as SQG  # noqa: E402


def write_project(tmp_path: Path, *, missing_dramatic: bool = False, open_question: bool = False) -> Path:
    root = tmp_path / "剧"
    ep = root / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (root / "生产数据").mkdir(parents=True)
    voice = "门槛血迹被指出，沈砚当众揭穿干净皂靴。"
    if open_question:
        voice = "为什么门槛血迹会消失，所有人都沉默。"
    (ep / "voiceover.txt").write_text(voice, encoding="utf-8")
    (ep / "故事板.md").write_text("Clip 01 冷开场危机\nClip 02 当众揭穿\n", encoding="utf-8")
    (ep / "adaptation_triage.json").write_text(
        json.dumps(
            {
                "kind": "n2d_adaptation_triage",
                "version": 1,
                "scope": "第1集",
                "items": [
                    {
                        "id": "AT_001",
                        "source_span": "raw.txt:1-3",
                        "beat_function": ["冲突起因"],
                        "decision": "dramatize",
                        "reason": "必须成戏",
                        "delivery": "Clip_01-02",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    clip1 = {
        "id": "Clip_01",
        "label": "冷开场危机",
        "duration": 3,
        "description": "雨夜门槛血迹，主角被逼问。",
        "dramatic_function": "用可视证据提出观众问题",
        "audience_effect": "立刻担心主角并期待反击",
    }
    if missing_dramatic:
        clip1.pop("dramatic_function")
    core = {
        "category": "强反转",
        "why_watch": "观众想看主角如何用证据当众反杀",
        "audience_payoff": "压迫兑现为打脸",
    }
    ledger = [
        {
            "hook_id": "H01",
            "promise": "干净皂靴是破绽",
            "payoff_due": "第1集",
            "payoff": "当众揭穿",
        }
    ]
    clip2 = {
        "id": "Clip_02",
        "label": "当众揭穿",
        "duration": 5,
        "description": "主角指出证据，众人反应。",
        "dramatic_function": "兑现证据链并释放爽点",
        "audience_effect": "获得信息回报和情绪释放",
    }
    if open_question:
        core = {
            "category": "悬念",
            "why_watch": "观众想知道血迹为什么消失",
            "audience_payoff": "留下下一集追问",
        }
        ledger = [{"hook_id": "H01", "promise": "血迹为什么消失", "payoff_due": "第2集", "status": "open"}]
        clip2 = {
            "id": "Clip_02",
            "label": "众人沉默",
            "duration": 5,
            "description": "所有人看向门槛，台阶空空。",
            "dramatic_function": "把疑问推到集尾",
            "audience_effect": "让观众想点下一集",
        }
    story = {
        "episode": "第1集",
        "title": "雨夜血证",
        "core_attraction": core,
        "first_3s_visual_hook": {
            "visual_hook": "雨夜门槛血迹 + 干净皂靴",
            "content_promise": "谁杀了人，主角如何翻盘",
            "muted_readable": True,
        },
        "retention_promise_ledger": ledger,
        "clips": [
            clip1,
            clip2,
        ],
    }
    (ep / "storyboard.json").write_text(json.dumps(story, ensure_ascii=False), encoding="utf-8")
    return root


def test_script_quality_contract_passes_and_writes(tmp_path: Path) -> None:
    root = write_project(tmp_path)
    contract = SQG.build_contract(root, "第1集", write_aux=True)
    assert contract["summary"]["blocks"] == 0
    assert contract["content_hash"] == contract["contract_hash"]
    jp, mp = SQG.write_outputs(root, "第1集", contract)
    assert jp.is_file()
    assert mp.is_file()
    written = json.loads(jp.read_text(encoding="utf-8"))
    assert written["kind"] == SQG.KIND
    assert "core_attraction" in written["signable_fields"]


def test_content_hash_ignores_generated_at(tmp_path: Path) -> None:
    root = write_project(tmp_path)
    contract = SQG.build_contract(root, "第1集", write_aux=True)
    changed = dict(contract)
    changed["generated_at"] = "2099-01-01T00:00:00+00:00"

    assert SQG.stable_content_hash(contract) == SQG.stable_content_hash(changed)


def test_missing_clip_dramatic_function_blocks(tmp_path: Path) -> None:
    root = write_project(tmp_path, missing_dramatic=True)
    contract = SQG.build_contract(root, "第1集", write_aux=True)
    codes = {f["code"] for f in contract["findings"] if f["severity"] == "block"}
    assert "clip_dramatic_function_missing" in codes


def test_open_question_without_hook_blocks(tmp_path: Path) -> None:
    root = write_project(tmp_path)
    (root / "生产数据" / "story_quality_pack_第1集.json").write_text(
        json.dumps(
            {
                "kind": "n2d_story_quality_pack",
                "audience_question_ledger": {
                    "questions": [
                        {
                            "question_id": "Q01",
                            "signal": "为什么",
                            "status": "open",
                            "expected_next_handling": "下一集冷开场接住",
                        }
                    ],
                    "findings": [
                        {
                            "severity": "warn",
                            "code": "open_questions_without_hook",
                            "message": "本集留下观众问题，但集尾缺钩子或兑现进展。",
                        }
                    ],
                },
                "performance_prompt_cues": [],
                "summary": {"open_questions": 1},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    contract = SQG.build_contract(root, "第1集", write_aux=False)
    codes = {f["code"] for f in contract["findings"] if f["severity"] == "block"}
    assert "open_questions_without_hook" in codes
