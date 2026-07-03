from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("preventive_contracts.py")
spec = importlib.util.spec_from_file_location("preventive_contracts", SCRIPT)
preventive_contracts = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(preventive_contracts)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _storyboard(root: Path, episode: str = "第1集") -> None:
    _write_json(root / "脚本" / episode / "storyboard.json", {
        "kind": "n2d_storyboard",
        "version": 1,
        "clips": [{
            "clip_id": "Clip_01",
            "description": "CHAR_A 握住 PROP_SWORD 与 CHAR_B 近距离对峙，并说出台词。",
            "character_ids": ["CHAR_A", "CHAR_B"],
            "prop_ids": ["PROP_SWORD"],
            "dialogue_indices": [1],
            "dramatic_function": "兑现本集承诺并抬高阻碍",
            "editing_intent": "用近景反打切到集尾钩",
        }],
    })


def _confirmed_contract(root: Path, episode: str = "第1集") -> None:
    _write_json(root / "脚本" / episode / "preventive_contracts.json", {
        "kind": "n2d_preventive_contracts",
        "version": 1,
        "episode": episode,
        "status": "confirmed",
        "episode_promise": {
            "opening_hook": "她发现令牌失踪。",
            "promise": "本集承诺找出内鬼。",
            "obstacle": "同伴阻拦且敌人逼近。",
            "payoff_or_progress": "确认令牌在 CHAR_B 手里。",
            "cliffhanger": "CHAR_B 举剑指向她。",
        },
        "shots": [{
            "clip_id": "Clip_01",
            "dramatic_function": "兑现本集承诺并抬高阻碍",
            "editing_intent": "用近景反打切到集尾钩",
        }],
        "reference_slots": {
            "characters": [
                {"id": "CHAR_A", "reference_slots": ["front", "side", "expression"], "identity_strategy": "same-source multi-view lock"},
                {"id": "CHAR_B", "reference_slots": ["front", "side", "expression"], "identity_strategy": "same-source multi-view lock"},
            ],
            "assets": [
                {"id": "PROP_SWORD", "reference_slots": ["front", "handheld"], "lock_strategy": "shape constraints"},
            ],
            "scenes": [],
        },
        "interaction_physics": [{
            "clip_id": "Clip_01",
            "action_decomposition": ["CHAR_A 抬手", "CHAR_A 握住剑柄", "CHAR_B 后撤"],
            "contact_points": ["CHAR_A right hand -> PROP_SWORD hilt"],
            "screen_positions": ["CHAR_A left foreground", "CHAR_B right midground"],
            "degrade_plan": "拆成手部特写 + 反打",
        }],
        "audio_timing": {
            "mode": "先出视频后配音",
            "post_dub": {"fit_strategy": "fit voice to locked clip duration", "overflow_policy": "overflow returns to video"},
            "native_av_policy": {"lipsync_policy": "none", "subtitle_policy": "compose overlay", "voice_identity_policy": "n2d-voice"},
            "dialogue_closeups": [{
                "clip_id": "Clip_01",
                "timing_source": "voiceover index 1 estimated slot",
                "mouth_policy": "mouth visible but final lipsync in compose",
                "subtitle_policy": "compose overlay",
                "voice_or_native_policy": "post_dub voice",
            }],
        },
    })


def test_episode_promise_gate_scaffolds_and_blocks_draft(tmp_path: Path) -> None:
    report = preventive_contracts.build_report(tmp_path, "第1集", stage="script_stage2", write_missing=True)

    assert report["status"] == "blocked"
    assert report["scaffolded"] is True
    assert (tmp_path / "脚本" / "第1集" / "preventive_contracts.json").is_file()
    assert any(f["gate"] == "episode_promise_gate" for f in report["findings"])


def test_shot_intent_gate_blocks_missing_clip_intent(tmp_path: Path) -> None:
    _write_json(tmp_path / "脚本" / "第1集" / "storyboard.json", {
        "clips": [{"clip_id": "Clip_01", "description": "她推门。"}],
    })
    _write_json(tmp_path / "脚本" / "第1集" / "preventive_contracts.json", {
        "kind": "n2d_preventive_contracts",
        "version": 1,
        "episode": "第1集",
        "status": "confirmed",
        "shots": [{"clip_id": "Clip_01"}],
    })
    report = preventive_contracts.build_report(tmp_path, "第1集", stage="image_prompt")

    assert report["status"] == "blocked"
    assert "shot_intent_gate" in {f["gate"] for f in report["findings"]}


def test_reference_physics_and_audio_gates_pass_with_confirmed_contract(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("- 制作模式: 先出视频后配音\n", encoding="utf-8")
    _storyboard(tmp_path)
    _confirmed_contract(tmp_path)

    image = preventive_contracts.build_report(tmp_path, "第1集", stage="image")
    video = preventive_contracts.build_report(tmp_path, "第1集", stage="video_prompt")
    compose = preventive_contracts.build_report(tmp_path, "第1集", stage="compose")

    assert image["status"] == "pass"
    assert video["status"] == "pass"
    assert compose["status"] == "pass"


def test_pilot_release_gate_blocks_first_episode_without_acceptance(tmp_path: Path) -> None:
    report = preventive_contracts.build_report(tmp_path, "第1集", stage="review")

    assert report["status"] == "blocked"
    assert report["findings"][0]["gate"] == "pilot_release_gate"
