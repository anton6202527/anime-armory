from ad_video_prompt_compiler import compile_prompt, parse_markdown, render_markdown


def contract(**overrides):
    data = {
        "clip_id": "镜头01",
        "backend": "seedance",
        "mode": "frames2video",
        "product_action": "卡片从待办区平滑归入今日手账",
        "camera_motion": "沿手机正面缓慢推近，尾端固定",
        "environment_motion": "手指与卡片只做轻微视差",
        "end_state": "产品 UI 稳定停在中心安全区",
        "product_hold": "同一包装结构、Logo 位置、品牌色与产品比例",
        "text_strategy": "首帧已有文字区域保持稳定；CTA 与法律文字由后期叠加",
        "negative_elements": ["logo deformation", "random text", "extra products"],
    }
    data.update(overrides)
    return data


def test_ad_compiler_is_concise_and_keeps_contract_metadata_out_of_prompt():
    payload = compile_prompt(contract())
    assert payload["lint"]["errors"] == []
    assert len(payload["prompt"]) < 650
    assert "route_reason" not in payload["prompt"]
    assert "PROD_" not in payload["prompt"]
    assert "产品主动作" in payload["prompt"] and "镜头：" in payload["prompt"]


def test_runway_ad_prompt_is_positive_only():
    payload = compile_prompt(contract(backend="Runway Gen-4"))
    assert payload["negative_prompt"] == ""
    assert payload["lint"]["errors"] == []


def test_ad_compiler_markdown_round_trip():
    payload = compile_prompt(contract(backend="Veo 3.1"))
    parsed = parse_markdown(render_markdown(payload))
    assert parsed is not None
    assert parsed["kind"] == "ad_compiled_video_prompt"
    assert parsed["prompt"] == payload["prompt"]
    assert parsed["negative_prompt"] == payload["negative_prompt"]
