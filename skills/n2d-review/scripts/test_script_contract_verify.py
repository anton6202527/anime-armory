#!/usr/bin/env python3
"""Tests for script_contract_verify.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import script_contract_verify as SCV  # noqa: E402


def test_clip_aliases_prefers_clip_number_over_episode_number() -> None:
    aliases = SCV.clip_aliases("EP02_CLIP03")

    assert "镜头 3" in aliases
    assert "Clip03" in aliases
    assert "镜头 2" not in aliases


def _write_contract(root: Path) -> None:
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    contract = {
        "kind": SCV.CONTRACT_KIND,
        "version": 1,
        "episode": "第1集",
        "status": "pass",
        "content_hash": "stable1234",
        "required_consumption_fields": [
            "core_attraction",
            "first_3s_visual_hook",
            "retention_promise_ledger",
            "clip_dramatic_function",
            "audience_question_ledger",
            "performance_cues",
        ],
        "source_sha256": {},
        "signable_fields": {
            "core_attraction": {"category": "强反转", "why_watch": "证据反杀"},
            "first_3s_visual_hook": {"visual_hook": "雨夜血迹"},
            "retention_promise_ledger": [
                {"promise": "干净皂靴是破绽", "payoff": "当众揭穿"}
            ],
            "audience_question_ledger": {
                "questions": [
                    {"question": "凶手是谁", "expected_next_handling": "下一镜给出证据"}
                ]
            },
            "performance_cues": [],
            "clip_dramatic_functions": [
                {
                    "clip_id": "Clip_01",
                    "dramatic_function": "用可视证据提出观众问题",
                    "audience_effect": "立刻担心主角并期待反击",
                },
                {
                    "clip_id": "Clip_02",
                    "dramatic_function": "兑现证据链并释放爽点",
                    "audience_effect": "获得信息回报和情绪释放",
                },
            ],
        },
        "findings": [],
        "summary": {"status": "pass", "blocks": 0, "warnings": 0, "clips": 2},
    }
    (prod / "script_quality_contract_第1集.json").write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")


def _write_prompts(root: Path, *, missing_clip2: bool = False) -> None:
    image_dir = root / "出图" / "第1集" / "prompt"
    video_dir = root / "出视频" / "第1集" / "prompt"
    image_dir.mkdir(parents=True)
    video_dir.mkdir(parents=True)
    clip2_func = "只写剧情描述" if missing_clip2 else "兑现证据链并释放爽点"
    text = f"""# prompt
留存承诺：干净皂靴是破绽；当众揭穿。
观众问题：凶手是谁；下一镜给出证据。

## Clip 01（Clip_01）
剧本可看性合同：戏剧功能=用可视证据提出观众问题；观众效果=立刻担心主角并期待反击。

## Clip 02（Clip_02）
剧本可看性合同：戏剧功能={clip2_func}；观众效果=获得信息回报和情绪释放。
"""
    (image_dir / "01_分镜出图.md").write_text(text, encoding="utf-8")
    (video_dir / "01_clips.md").write_text(text, encoding="utf-8")


def test_verify_prompt_contract_passes(tmp_path: Path) -> None:
    root = tmp_path / "剧"
    _write_contract(root)
    _write_prompts(root)

    report = SCV.verify(root, "第1集", ["出图", "出视频"])

    assert report["summary"]["blocks"] == 0
    assert report["status"] == "pass"


def test_verify_prompt_contract_blocks_missing_clip_field(tmp_path: Path) -> None:
    root = tmp_path / "剧"
    _write_contract(root)
    _write_prompts(root, missing_clip2=True)

    report = SCV.verify(root, "第1集", ["出图"])
    codes = {row["code"] for row in report["findings"]}

    assert "clip_contract_field_missing" in codes
    assert report["summary"]["blocks"] == 1
