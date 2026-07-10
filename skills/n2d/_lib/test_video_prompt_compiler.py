from __future__ import annotations

from video_prompt_compiler import (
    KIND,
    compile_video_prompt,
    lint_compiled_prompt,
    parse_compiled_markdown,
    render_compiled_markdown,
)


def _contract(**overrides):
    data = {
        "clip_id": "Clip_01",
        "backend": "seedance",
        "mode": "frames2video",
        "native_audio_policy": "none",
        "primary_action": "她抬眼，握紧刀柄，然后停住。",
        "camera_motion": "缓慢推近，尾端固定",
        "environment_motion": "衣袖只随抬手轻动",
        "rhythm": "克制推进，尾端留半拍",
        "end_state": "眼神定住，刀柄成为画面重心",
        "must_avoid": ["face drift", "extra characters", "text", "watermark"],
        "frame_inputs": ["first.png", "last.png"],
        "reference_inputs": ["CHAR_01/reference_group"],
        "control_inputs": [],
        "audio_inputs": [],
    }
    data.update(overrides)
    return data


def test_seedance_compiler_keeps_submit_prompt_compact_and_motion_first():
    payload = compile_video_prompt(_contract())

    assert payload["kind"] == KIND
    assert payload["profile"] == "zh_motion_first"
    assert "主动作：" in payload["prompt"]
    assert "镜头：" in payload["prompt"]
    assert "identity_registry" not in payload["prompt"]
    assert "video_model_routes" not in payload["prompt"]
    assert len(payload["prompt"]) < 600
    assert payload["lint"]["errors"] == []


def test_runway_compiler_uses_positive_only_prompt():
    payload = compile_video_prompt(_contract(backend="Runway Gen-4"))

    assert payload["profile"] == "runway_motion_positive"
    assert payload["negative_prompt"] == ""
    assert not any(token in payload["prompt"].lower() for token in (" no ", "don't", "do not", "avoid"))
    assert lint_compiled_prompt(payload)["errors"] == []


def test_veo_compiler_keeps_negative_elements_outside_main_prompt():
    payload = compile_video_prompt(_contract(backend="Veo 3.1"))

    assert payload["profile"] == "veo_cinematography"
    assert "face drift" not in payload["prompt"]
    assert "face drift" in payload["negative_prompt"]


def test_native_speech_compiler_requests_only_registered_on_screen_dialogue():
    payload = compile_video_prompt(_contract(
        backend="Veo 3.1",
        mode="native_av",
        native_audio_policy="native_speech",
    ))

    assert "registered on-screen dialogue" in payload["prompt"]
    assert "narration" in payload["prompt"]
    assert payload["lint"]["errors"] == []


def test_compiled_markdown_round_trip_preserves_submit_prompt_and_metadata():
    payload = compile_video_prompt(_contract())
    parsed = parse_compiled_markdown(render_compiled_markdown(payload))

    assert parsed is not None
    assert parsed["kind"] == KIND
    assert parsed["backend"] == "seedance"
    assert parsed["prompt"] == payload["prompt"]
    assert parsed["source_contract_sha256"] == payload["source_contract_sha256"]
