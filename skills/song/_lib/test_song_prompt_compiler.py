from song_prompt_compiler import compile_prompt, lint, render_markdown


def contract(backend="ACE-Step"):
    return {
        "take_id": "take_01",
        "backend": backend,
        "title": "山门之外",
        "style_seed": "国风流行, 燃, 96 BPM, D minor, female vocal, piano and strings",
        "sonic_identity": "克制主歌到开阔大副歌，笛与弦乐交替",
        "emotional_arc": "verse 收住 -> pre-chorus 抬升 -> chorus 释放",
        "hook_intent": "副歌前 30 秒出现可复唱 hook",
        "lyrics": "[verse]\n我从山门一路向前\n\n[chorus]\n仗剑下山闯人间",
        "duration_seconds": 90,
        "contract_context": {"reference_boundaries": "不得复刻旋律或标志性 riff"},
    }


def test_ace_step_compiles_separate_prompt_lyrics_duration():
    payload = compile_prompt(contract())
    assert payload["lint"]["errors"] == []
    assert payload["submit_fields"]["prompt"] == payload["style_prompt"]
    assert payload["submit_fields"]["lyrics"] == payload["lyrics"]
    assert payload["submit_fields"]["audio_duration"] == 90
    assert "reference_boundaries" not in payload["style_prompt"]


def test_suno_field_map_and_exact_lyrics():
    payload = compile_prompt(contract("Suno"))
    assert payload["submit_fields"]["title"] == "山门之外"
    assert payload["submit_fields"]["lyrics"] == contract("Suno")["lyrics"]
    assert "## 后端编译提交字段" in render_markdown(payload)


def test_internal_contract_reference_lint_blocks():
    payload = compile_prompt(contract())
    payload["style_prompt"] += " 读取 素材/reference_pack.md"
    assert "style_prompt_contains_internal_contract_reference" in lint(payload)["errors"]
