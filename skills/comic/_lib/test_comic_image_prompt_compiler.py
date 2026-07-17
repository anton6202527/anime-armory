from comic_image_prompt_compiler import compile_prompt, lint


def contract(backend="GPT Image 2 Codex"):
    return {
        "panel_id": "P001",
        "backend": backend,
        "visible_facts": "主角在祠堂内发现画右下方匕首反光，身体微微后撤",
        "style": "彩色国漫条漫，完成稿，清晰墨线与克制高光",
        "composition": "中景，主角画左看画右，匕首反光是第二视觉焦点",
        "scene_continuity": "香案居中，祠堂门在画右后景，画左上冷窗光",
        "identity_hold": "按已附角色与场景参考保持同一张脸、服装和空间结构",
        "finishing": "人物外轮廓较重，背景 20% 网点，集中线指向匕首",
        "text_strategy": "不生成文字、气泡或文字框；画面上方保留低细节嵌字区",
        "anatomy": "双手、衣袖和匕首落点完整可读，接触关系自然",
        "negative_elements": ["文字", "气泡", "水印", "额外手指", "脸部漂移", "直视读者镜头"],
        "reference_inputs": [{"id": "CHAR_MAIN", "path": "anchor.png"}],
        "canvas": {"width": 1000, "height": 800},
    }


def test_compiler_keeps_visible_art_but_drops_internal_ids_and_paths():
    payload = compile_prompt(contract())
    assert payload["lint"]["errors"] == []
    assert "匕首反光" in payload["prompt"]
    assert "CHAR_MAIN" not in payload["prompt"]
    assert "anchor.png" not in payload["prompt"]
    assert len(payload["prompt"]) < 1400


def test_compiler_sanitizes_ids_embedded_in_visible_contract_fields():
    data = contract()
    data["scene_continuity"] = "继承 LOC_HALL：画左冷窗光；PROP_SWORD 在画右；参考 出图/共享/图片/hall.png"
    data["style"] = "STYLE_GONGBI_V1 细劲工笔"
    payload = compile_prompt(data)
    assert payload["lint"]["errors"] == []
    assert "LOC_HALL" not in payload["prompt"]
    assert "PROP_SWORD" not in payload["prompt"]
    assert "STYLE_GONGBI_V1" not in payload["prompt"]
    assert "hall.png" not in payload["prompt"]
    assert "已登记场景锚" in payload["prompt"]


def test_diffusion_uses_separate_negative_field():
    payload = compile_prompt(contract("Flux ComfyUI"))
    assert payload["negative_prompt"]
    assert "避免：" not in payload["prompt"]


def test_exact_dialogue_and_internal_reference_lint_block():
    payload = compile_prompt(contract())
    payload["prompt"] += " 台词：你好。 LOC_HALL"
    errors = lint(payload)["errors"]
    assert "submit_prompt_contains_exact_dialogue" in errors
    assert "submit_prompt_contains_internal_contract_reference" in errors


def test_semicolon_structured_contract_does_not_trigger_fragmentation_warning():
    data = contract()
    data["scene_continuity"] = "；".join(f"约束{index}" for index in range(30))
    payload = compile_prompt(data)
    assert "submit_prompt_many_clauses" not in payload["lint"]["warnings"]


def test_vfx_registry_token_is_converted_to_public_visual_language():
    data = contract("Dreamina 5.0 Dreamina/即梦官方 CLI")
    data["visible_facts"] = "黑气在殿顶分解为 VFX_108_STARLIGHTS 的暖金光迹"
    payload = compile_prompt(data)
    assert payload["lint"]["errors"] == []
    assert "VFX_108_STARLIGHTS" not in payload["prompt"]
    assert "已登记效果参考" in payload["prompt"]
