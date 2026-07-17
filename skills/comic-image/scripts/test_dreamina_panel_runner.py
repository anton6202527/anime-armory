from pathlib import Path
import importlib.util
import json


MODULE_PATH = Path(__file__).with_name("dreamina_panel_runner.py")
SPEC = importlib.util.spec_from_file_location("comic_dreamina_panel_runner", MODULE_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_nearest_supported_ratio() -> None:
    assert runner.nearest_supported_ratio({"width": 1296, "height": 1040}) == "4:3"
    assert runner.nearest_supported_ratio({"width": 1080, "height": 620}) == "16:9"
    assert runner.nearest_supported_ratio({"width": 1296, "height": 1232}) == "1:1"


def test_normalize_panel_outputs_exact_size(tmp_path: Path) -> None:
    from PIL import Image

    source = tmp_path / "source.png"
    target = tmp_path / "target.png"
    Image.new("RGB", (1600, 1200), (30, 40, 50)).save(source)

    result = runner.normalize_panel(source, target, {"width": 1296, "height": 1040})

    assert Image.open(target).size == (1296, 1040)
    assert result["source_size"] == {"width": 1600, "height": 1200}
    assert result["target_size"] == {"width": 1296, "height": 1040}


def test_extra_required_view_can_be_omitted_when_subject_is_represented() -> None:
    selected = [
        {"id": "CHAR_HONG_XIN", "role": "front", "required": True},
        {"id": "STYLE_SHUIHU", "role": "style", "required": True},
    ]
    omitted = [
        {"id": "CHAR_HONG_XIN", "role": "face", "required": True},
        {"id": "PROP_SILVER_CENSER", "role": "prop", "required": True},
    ]

    assert runner.unrepresented_required_ids(selected, omitted) == {"PROP_SILVER_CENSER"}


def test_build_prompt_accepts_dreamina_compiled_job() -> None:
    submit_prompt = (
        "生成一张铺满画布的单格无字漫画画面。"
        "画面事实：黎明中的北宋宫城与紫宸殿在薄雾中显现。"
        "画风与稿层：宋画工笔淡彩、国漫写实人物、低饱和矿物色彩色完成稿。"
    )
    material = {
        "submit_prompt_sha256": runner.hashlib.sha256(submit_prompt.encode("utf-8")).hexdigest(),
        "size": {"width": 1296, "height": 1040},
        "references": [],
        "character_bindings": [],
        "panel_plan_sha256": "",
    }
    execution_hash = runner.hashlib.sha256(
        json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    job = {
        "panel_id": "P001",
        "size": material["size"],
        "prompt_source_kind": "compiled_submit_prompt",
        "prompt_compiler": {
            "kind": runner.shared.COMPILER_KIND,
            "version": runner.shared.COMPILER_VERSION,
            "profile_version": "test",
            "profile": "zh_comic_reference_first",
            "backend": "seedream",
            "language": "zh",
        },
        "submit_prompt": submit_prompt,
        "prompt": submit_prompt,
        "negative_prompt": "",
        "source_contract_sha256": "a" * 64,
        "submit_prompt_sha256": material["submit_prompt_sha256"],
        "execution_input_sha256": execution_hash,
        "consumed_contracts": {"reference_plan": {"panel_plan_sha256": ""}},
        "references": [],
        "character_bindings": [],
    }

    prompt = runner.build_prompt(job, [], "4:3", correction="卷轴表面保持纯色，不生成任何字符。")

    assert "Dreamina" not in prompt
    assert "1296x1040" in prompt
    assert submit_prompt in prompt
    assert "卷轴表面保持纯色" in prompt
