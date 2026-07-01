import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("image_prompt_pack.py")
SPEC = importlib.util.spec_from_file_location("image_prompt_pack", MODULE_PATH)
image_prompt_pack = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = image_prompt_pack
SPEC.loader.exec_module(image_prompt_pack)


def test_character_makeup_prompt_requires_neutral_gray_backdrop() -> None:
    prompt = image_prompt_pack.shared_character_prompt()

    assert "统一中性灰白/18%灰棚拍背景" in prompt
    assert "无窗、无房间、无家具、无剧情道具" in prompt
    assert "不要雨窗/房间/家具场景" in image_prompt_pack.shared_style_anchor_prompt()
    assert "same studio/rain-window background" not in prompt
    assert "深灰/雨窗影棚背景" not in prompt


def test_weapon_refs_are_not_labeled_as_props() -> None:
    refs = image_prompt_pack.shot_refs([], ["WEAPON_PEIJUE_SHORT_BLADE"])

    assert refs
    assert "武器定妆" in refs[0]
    assert "道具定妆" not in refs[0]


def test_prompt_safe_forbidden_avoids_wardrobe_false_positive() -> None:
    text = image_prompt_pack.prompt_safe_forbidden(["Q版", "塑料盔甲", "平台录屏UI"])

    assert "塑料硬质防具质感" in text
    assert "塑料盔甲" not in text
