import importlib.util
import json
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
    assert "### 定妆图提交口径" in prompt
    for key in ("角色身份：", "年龄/年龄档：", "固定外貌：", "服装妆造：", "定妆要求：", "画风规格：", "禁止："):
        assert key in prompt
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


def test_dict_asset_requirements_canonicalize_human_aliases() -> None:
    story = {
        "asset_requirements": {
            "objects": [
                "WEAPON_01 横刀",
                "VFX_系统面板/百妖谱",
                "VFX_系统面板/道行计数overlay",
                "AMBIENT_官道马蹄火把",
            ],
            "locations": ["LOC_01 荒野尸骸战场"],
        },
        "clips": [{
            "location_id": "LOC_01",
            "object_ids": ["WEAPON_01 横刀", "百妖谱", "道行计数overlay"],
        }],
    }

    ids = image_prompt_pack.required_asset_ids(story)
    reqs = image_prompt_pack.asset_req_map(story)

    assert "WEAPON_01" in ids
    assert "VFX_系统面板" in ids
    assert "VFX_道行计数overlay" in ids
    assert "VFX_官道马蹄火把" not in ids
    assert "LOC_01" in ids
    assert all(" " not in aid and "/" not in aid for aid in ids)
    assert reqs["WEAPON_01"]["name"] == "横刀"


def test_material_list_supplies_asset_names_and_prompts(tmp_path: Path) -> None:
    ep_dir = tmp_path / "脚本" / "第2集"
    ep_dir.mkdir(parents=True)
    (ep_dir / "素材清单.md").write_text(
        "\n".join([
            "# 素材清单",
            "",
            "## 关键道具",
            "",
            "### PROP_GREEN_WATER 碧绿灵水",
            "中文 Prompt：满盆碧绿清水，颜色异常但水面安静，清晨冷光反射。",
            "英文 Prompt：basin filled with deep green clear water.",
        ]),
        encoding="utf-8",
    )
    story = {
        "episode": 2,
        "clips": [{"object_ids": ["PROP_GREEN_WATER"]}],
    }

    defs = image_prompt_pack.derive_asset_defs(tmp_path, story)

    assert defs["PROP_GREEN_WATER"]["name"] == "碧绿灵水"
    assert defs["PROP_GREEN_WATER"]["positive"] == "满盆碧绿清水，颜色异常但水面安静，清晨冷光反射。"
    assert "PROP GREEN WATER" not in defs["PROP_GREEN_WATER"]["positive"]


def test_magic_prop_keeps_weapon_profile_in_asset_registry(tmp_path: Path) -> None:
    story = {
        "episode": 2,
        "clips": [{"object_ids": ["PROP_HEI_TAO_PEN"]}],
    }
    old_defs = image_prompt_pack.ASSET_DEFS
    try:
        image_prompt_pack.ASSET_DEFS = image_prompt_pack.derive_asset_defs(tmp_path, story)
        registry = image_prompt_pack.build_asset_registry(tmp_path)
    finally:
        image_prompt_pack.ASSET_DEFS = old_defs

    asset = next(item for item in registry["assets"] if item["id"] == "PROP_HEI_TAO_PEN")

    assert asset["owner"] == "CHAR_HE_PINGSHENG"
    assert asset["weapon_profile"]["combat_usage"].startswith("本集不攻击")
    assert "forbidden_drift" in asset["weapon_profile"]


def test_clip_assets_do_not_bind_plain_alias_from_prose() -> None:
    clip = {
        "description": "姜月初想起百妖谱规则，但本镜不出现面板。",
        "object_ids": ["WEAPON_01 横刀"],
    }

    assert image_prompt_pack.clip_assets(clip) == ["WEAPON_01"]


def test_character_asset_stem_prefers_char_id_makeup_file(tmp_path: Path) -> None:
    img = tmp_path / "出图" / "共享" / "图片" / "定妆_CHAR_01__囚犯初醒态_正面.png"
    img.parent.mkdir(parents=True)
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    stem = image_prompt_pack.character_asset_stem(tmp_path, "CHAR_01", "姜月初", "囚犯初醒态")

    assert stem == "CHAR_01__囚犯初醒态"


def test_shadow_silhouette_word_does_not_make_core_character_partial(tmp_path: Path) -> None:
    card_dir = tmp_path / "设定库" / "characters"
    card_dir.mkdir(parents=True)
    (card_dir / "姜月初.md").write_text(
        "\n".join([
            "# 角色卡 — 姜月初（ID: CHAR_01）",
            "- 身份：主角。",
            "- 固定外貌：东方少女脸。",
            "- 固定服装：灰褐囚服。",
            "- 固定体态：纤细高挑。",
            "- 服装选择评分卡：阶层信号强；剪影朴素但竖屏小图可读。",
            "- **锚点句**：黑色半散长发·灰褐粗布囚服",
        ]),
        encoding="utf-8",
    )
    story = {"clips": [{"character_ids": ["CHAR_01"]}]}

    defs = image_prompt_pack.derive_character_defs(tmp_path, story)

    assert defs["CHAR_01"]["tier"] == "core"


def test_character_makeup_prompt_expands_age_from_roster(tmp_path: Path) -> None:
    card_dir = tmp_path / "设定库" / "characters"
    card_dir.mkdir(parents=True)
    (card_dir / "贺平生.md").write_text(
        "\n".join([
            "# 角色卡 — 贺平生（ID: CHAR_HE_PINGSHENG）",
            "- 身份：主角。",
            "- 固定服装：粗布短褐杂役服。",
            "- **锚点句**：清瘦东方少年·粗布短褐杂役服",
        ]),
        encoding="utf-8",
    )
    (card_dir / "_角色总表.md").write_text(
        "\n".join([
            "# 角色卡总表",
            "",
            "## 贺平生",
            "- 当前状态：十四岁，刚进入秀竹峰杂役班。",
            "- 视觉特征（脸/发/瞳/体型/服装）：十四岁东方少年脸，五官干净但带长期缺资源的清瘦感；黑发简单束起；深色瞳孔；约155-160cm；粗布短褐杂役服。",
        ]),
        encoding="utf-8",
    )
    story = {"clips": [{"character_ids": ["CHAR_HE_PINGSHENG"]}]}

    defs = image_prompt_pack.derive_character_defs(tmp_path, story)

    assert defs["CHAR_HE_PINGSHENG"]["age_context"] == "十四岁"
    assert "十四岁东方少年脸" in defs["CHAR_HE_PINGSHENG"]["face"]

    original = image_prompt_pack.CHARACTER_DEFS
    try:
        image_prompt_pack.CHARACTER_DEFS = defs
        prompt = image_prompt_pack.shared_character_prompt()
    finally:
        image_prompt_pack.CHARACTER_DEFS = original

    assert "**年龄/年龄档**：十四岁" in prompt
    assert "十四岁东方少年脸" in prompt


def test_derive_character_defs_keeps_registered_cards_not_only_current_story(tmp_path: Path) -> None:
    card_dir = tmp_path / "设定库" / "characters"
    card_dir.mkdir(parents=True)
    (card_dir / "甲.md").write_text(
        "\n".join([
            "# 角色卡 — 甲（ID: CHAR_ALPHA）",
            "- 身份：本集角色。",
            "- 固定外貌：少年脸。",
            "- 固定服装：青衣。",
            "- **锚点句**：甲·少年脸·青衣",
        ]),
        encoding="utf-8",
    )
    (card_dir / "乙.md").write_text(
        "\n".join([
            "# 角色卡 — 乙（ID: CHAR_BETA）",
            "- 身份：系列角色。",
            "- 固定外貌：中年脸。",
            "- 固定服装：灰衣。",
            "- **锚点句**：乙·中年脸·灰衣",
        ]),
        encoding="utf-8",
    )
    story = {"clips": [{"character_ids": ["CHAR_ALPHA"]}]}

    defs = image_prompt_pack.derive_character_defs(tmp_path, story)

    assert "CHAR_ALPHA" in defs
    assert "CHAR_BETA" in defs


def test_state_lock_line_resolves_character_and_asset_names() -> None:
    original_chars = image_prompt_pack.CHARACTER_DEFS
    original_assets = image_prompt_pack.ASSET_DEFS
    try:
        image_prompt_pack.CHARACTER_DEFS = {"CHAR_HE": {"name": "贺平生"}}
        image_prompt_pack.ASSET_DEFS = {"PROP_BASIN": {"name": "黑陶破盆"}}
        story = {
            "visual_contract": {
                "角色状态演进": {
                    "贺平生": [{"自": "镜头3", "状态": "初见破盆异状时茫然。", "保持": "镜头3"}],
                    "黑陶破盆": [{"自": "镜头1", "状态": "满盆碧绿灵水，盆底微绿亮点。", "保持": "至镜头7"}],
                }
            }
        }

        line = image_prompt_pack.state_lock_line(story, ["CHAR_HE"], 3, ["PROP_BASIN"])
    finally:
        image_prompt_pack.CHARACTER_DEFS = original_chars
        image_prompt_pack.ASSET_DEFS = original_assets

    assert "`CHAR_HE`: 初见破盆异状时茫然。" in line
    assert "`PROP_BASIN`: 满盆碧绿灵水，盆底微绿亮点。" in line


def test_static_identity_strips_episode_dynamic_state() -> None:
    text = "十四岁东方少年脸，约155-160cm，肩颈瘦，挑水后有压痕；粗布短褐杂役服"

    out = image_prompt_pack.sanitize_static_identity_text(text)

    assert "挑水后有压痕" not in out
    assert "肩颈瘦" in out


def test_sanitize_future_state_removes_camera_gaze_language() -> None:
    text = "姜月初半身侧对镜头，百妖谱面板悬在她身侧；虎妖直视主镜头。"

    out = image_prompt_pack.sanitize_future_state_text(text, 7)

    assert "侧对镜头" not in out
    assert "直视主镜头" not in out
    assert "视线不看镜头" in out
