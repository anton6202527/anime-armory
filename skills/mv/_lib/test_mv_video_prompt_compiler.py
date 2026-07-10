from mv_video_prompt_compiler import compile_prompt, lint, parse_markdown, render_markdown


def contract(backend="Seedance 2.0"):
    return {
        "clip_id": "Clip_007",
        "backend": backend,
        "mode": "frames2video",
        "primary_action": "主角转身挥剑，衣摆在动作峰值后自然回落",
        "camera_motion": "中景缓推，沿人物运动方向轻微环绕",
        "environment_motion": "逆光粒子在挥剑瞬间扩散",
        "rhythm": "动作峰值对齐 0.8s downbeat，末尾停稳 8 帧",
        "end_state": "剑尖指向画右，视线落向镜头",
        "negative_elements": ["换脸", "换衣", "新增人物", "文字或水印", "原生人声"],
        "frame_inputs": ["first.png", "end.png"],
    }


def test_mv_compiler_is_concise_and_external_audio():
    payload = compile_prompt(contract())
    assert payload["lint"]["errors"] == []
    assert payload["native_audio_policy"] == "external_song_track"
    assert payload["request_controls"]["generate_audio"] is False
    assert "lead_id" not in payload["prompt"]
    assert "first.png" not in payload["prompt"]
    assert len(payload["prompt"]) < 650


def test_runway_is_positive_only():
    payload = compile_prompt(contract("Runway Gen-4"))
    assert payload["negative_prompt"] == ""
    assert payload["lint"]["errors"] == []


def test_markdown_roundtrip_and_internal_path_lint():
    payload = compile_prompt(contract())
    parsed = parse_markdown(render_markdown(payload))
    assert parsed and parsed["prompt"] == payload["prompt"]
    parsed["prompt"] += " 出图/a.png"
    assert "submit_prompt_contains_internal_contract_reference" in lint(parsed)["errors"]
