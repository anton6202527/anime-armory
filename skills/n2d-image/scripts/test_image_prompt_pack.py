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


def test_missing_character_card_gets_project_specific_visual_fallback(tmp_path: Path) -> None:
    story = {"clips": [{"character_ids": ["CHAR_WANG_DUN", "CHAR_HE_PINGSHENG"]}]}

    defs = image_prompt_pack.derive_character_defs(tmp_path, story)

    assert defs["CHAR_WANG_DUN"]["name"] == "王敦"
    assert "黑黝黝宽脸" in defs["CHAR_WANG_DUN"]["face"]
    assert "洗得发白的宽松青色道袍" in defs["CHAR_WANG_DUN"]["outfit"]
    assert "角色脸部身份以角色卡为准" not in defs["CHAR_WANG_DUN"]["anchor"]
    assert defs["CHAR_HE_PINGSHENG"]["name"] == "贺平生"
    assert "瘦小少年脸" in defs["CHAR_HE_PINGSHENG"]["face"]


def test_unknown_character_card_fallback_is_drawable_not_placeholder(tmp_path: Path) -> None:
    story = {"clips": [{"character_ids": ["CHAR_UNKNOWN_GUARD"]}]}

    defs = image_prompt_pack.derive_character_defs(tmp_path, story)
    cfg = defs["CHAR_UNKNOWN_GUARD"]

    assert cfg["name"] == "Unknown Guard"
    assert "角色脸部身份以角色卡为准" not in cfg["face"]
    assert "低饱和古装衣袍" in cfg["outfit"]


def test_character_scope_visual_hints_prevent_generic_human_demon(tmp_path: Path) -> None:
    card_dir = tmp_path / "设定库" / "characters"
    card_dir.mkdir(parents=True)
    (card_dir / "CHAR_05_青面郎君.md").write_text(
        "# 角色卡 — 青面郎君（ID: CHAR_05）\n\n"
        "- 身份: 新增青衫狼妖人形姿态，青皮巨狼特征、绿眼、学人踱步，禁止画成俊美人类。\n",
        encoding="utf-8",
    )
    story = {"clips": [{"character_ids": ["CHAR_05"]}]}

    cfg = image_prompt_pack.derive_character_defs(tmp_path, story)["CHAR_05"]

    assert "青皮巨狼特征" in cfg["face"]
    assert "非人狼妖特征必须清晰" in cfg["face"]
    assert "兽化长指" in cfg["accessories"]
    assert "不要把青面郎君换成普通俊美人类" in cfg["drift"]


def test_shots_global_contract_is_not_a_shot_heading(tmp_path: Path) -> None:
    text = image_prompt_pack.shots_md(tmp_path, "第1集", {}, [])

    assert "\n### 剧本可看性全局合同\n" in text
    assert "\n## 剧本可看性全局合同\n" not in text


def test_weapon_refs_are_not_labeled_as_props() -> None:
    refs = image_prompt_pack.shot_refs([], ["WEAPON_PEIJUE_SHORT_BLADE"])

    assert refs
    assert "武器定妆" in refs[0]
    assert "道具定妆" not in refs[0]


def test_asset_topology_from_registry_is_written_to_shared_and_shot_prompt(tmp_path: Path) -> None:
    registry_path = tmp_path / "出图" / "共享" / "asset_registry.json"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(json.dumps({
        "assets": [
            {
                "id": "WEAPON_TEST",
                "type": "weapon",
                "name": "测试横刀",
                "constraints": {
                    "structure": "一柄一刃单刃横刀；一侧锋刃，一侧刀背非刃。",
                    "blade_topology": {
                        "weapon_count": 1,
                        "blade_count": 1,
                        "cutting_edge_count": 1,
                        "spine": "刀背非刃",
                    },
                    "vfx_boundary": "刀光只能是半透明光轨，不得变成第二把实体刀刃。",
                    "must_not_have": ["双刃", "第二把刀刃", "刀光变成实体刀刃"],
                },
                "drift_forbidden": ["不要双刃"],
                "weapon_profile": {
                    "blade_topology": "weapon_count=1；blade_count=1；cutting_edge_count=1；刀背非刃。",
                },
            },
            {
                "id": "VFX_TEST",
                "type": "vfx",
                "name": "测试光轨",
                "constraints": {
                    "structure": "半透明五道爪形冷光轨迹，不是实体武器。",
                    "vfx_boundary": "只能表现速度/碰撞边缘光，不具备握柄、护手或金属刀刃。",
                    "must_not_have": ["实体刀刃", "握柄", "护手"],
                },
            },
        ],
    }, ensure_ascii=False), encoding="utf-8")
    clip = {
        "id": "EP01_CLIP01",
        "description": "横刀贴着冷光出鞘。",
        "object_ids": ["WEAPON_TEST"],
        "vfx_ids": ["VFX_TEST"],
    }
    story = {"clips": [clip], "visual_contract": {}, "style_contract": {}}

    defs = image_prompt_pack.derive_asset_defs(tmp_path, story)

    assert "一柄一刃单刃横刀" in defs["WEAPON_TEST"]["positive"]
    assert "刀背非刃" in image_prompt_pack.flatten_contract_value(defs["WEAPON_TEST"]["constraints"]["blade_topology"])
    assert "实体刀刃" in defs["VFX_TEST"]["constraints"]["must_not_have"]
    assert "武器拓扑" in image_prompt_pack.shared_asset_positive(defs["WEAPON_TEST"])
    assert "特效边界" in image_prompt_pack.shared_asset_positive(defs["VFX_TEST"])

    old_assets = image_prompt_pack.ASSET_DEFS
    old_chars = image_prompt_pack.CHARACTER_DEFS
    try:
        image_prompt_pack.ASSET_DEFS = defs
        image_prompt_pack.CHARACTER_DEFS = {}
        shot_text = image_prompt_pack.shot_prompt_section(tmp_path, "第1集", 1, clip, {}, story)
    finally:
        image_prompt_pack.ASSET_DEFS = old_assets
        image_prompt_pack.CHARACTER_DEFS = old_chars

    assert "**资产拓扑锁**" in shot_text
    assert "weapon_count=1" in shot_text
    assert "刀光只能是半透明光轨" in shot_text
    assert "不是实体武器" in shot_text


def test_shot_refs_include_ready_auxiliary_character_angles(tmp_path: Path) -> None:
    image_dir = tmp_path / "出图" / "共享" / "图片"
    image_dir.mkdir(parents=True)
    for name in (
        "定妆_CHAR_TEST__常态.png",
        "定妆_CHAR_TEST__常态_脸部特写_脸锚裁切.png",
        "定妆_CHAR_TEST__常态_45度.png",
        "定妆_CHAR_TEST__常态_侧.png",
        "定妆_CHAR_TEST__常态_半身.png",
        "定妆_GROUP_TEST__常态.png",
        "定妆_GROUP_TEST__常态_手部局部.png",
    ):
        (image_dir / name).write_bytes(b"\x89PNG\r\n\x1a\n")
    old_chars = image_prompt_pack.CHARACTER_DEFS
    try:
        image_prompt_pack.CHARACTER_DEFS = {
            "CHAR_TEST": {"asset_key": "CHAR_TEST__常态", "form": "常态", "tier": "core", "name": "测试角色"},
            "GROUP_TEST": {
                "asset_key": "GROUP_TEST__常态",
                "form": "常态",
                "tier": "restricted_partial",
                "name": "测试群像",
            },
        }
        refs = image_prompt_pack.shot_refs(["CHAR_TEST", "GROUP_TEST"], [], tmp_path)
    finally:
        image_prompt_pack.CHARACTER_DEFS = old_chars

    joined = "\n".join(refs)
    assert "辅助角度锚" in joined
    assert "定妆_CHAR_TEST__常态_45度.png" in joined
    assert "定妆_CHAR_TEST__常态_侧.png" in joined
    assert "定妆_CHAR_TEST__常态_半身.png" in joined
    assert "定妆_CHAR_TEST__常态_背.png" not in joined
    assert "GROUP_TEST" in joined
    assert "定妆_GROUP_TEST__常态_手部局部.png" not in joined


def test_prompt_safe_forbidden_avoids_wardrobe_false_positive() -> None:
    text = image_prompt_pack.prompt_safe_forbidden(["Q版", "塑料盔甲", "平台录屏UI"])

    assert "塑料硬质防具质感" in text
    assert "塑料盔甲" not in text


def test_summarize_contract_value_does_not_cut_mid_field() -> None:
    text = image_prompt_pack.summarize_contract_value({
        "content_promise": "这个少年为什么刚入门就被当成废物？他会怎样活下去？",
        "content_proposition": "这个少年为什么刚入门就被当成废物？他会怎样活下去？",
        "expected_metric": {"primary": "retention_3s", "target": 0.8},
        "hook_type": "悬念",
        "muted_safe_proof": "关声也能从黑暗大殿围审、少年低位、张老大高位俯视和烧屏“五行灵根？”读懂压迫悬念。",
        "onscreen_text": "十四岁，五行灵根？",
    }, 180)

    assert text.endswith("…")
    assert "onscreen_text=十四" not in text


def test_character_card_identity_parses_metadata_style_card() -> None:
    text = "# 角色卡：女主（待剧情确认姓名后绑定）\n\n- character_id: `CHAR_FEMALE_LEAD`\n"

    name, cid = image_prompt_pack.parse_character_card_identity(text, "女主_待绑定")

    assert name == "女主（待剧情确认姓名后绑定）"
    assert cid == "CHAR_FEMALE_LEAD"


def test_inner_focus_directive_isolates_subject_and_context_entities() -> None:
    clip = {
        "description": "姜月初内心独白：这百妖谱到底是什么。",
        "dramatic_function": "内心戏，表现主角疑惧。",
        "character_ids": ["CHAR_01", "CHAR_02"],
        "object_ids": ["VFX_系统面板"],
    }

    directive = image_prompt_pack.inner_focus_directive(
        clip,
        image_prompt_pack.clip_chars(clip),
        image_prompt_pack.clip_assets(clip),
    )

    assert "内心戏主体隔离" in directive
    assert "画面焦点只给 CHAR_01" in directive
    assert "非焦点主体 CHAR_02" in directive
    assert "不要重复上一镜群像" in directive


def test_non_inner_focus_clip_has_no_inner_focus_directive() -> None:
    clip = {"description": "姜月初抬剑迎敌。", "character_ids": ["CHAR_01", "CHAR_02"]}

    assert image_prompt_pack.inner_focus_directive(clip, image_prompt_pack.clip_chars(clip), []) == ""


def test_style_anchor_prompt_and_overview_inherit_story_style_contract(tmp_path: Path) -> None:
    story = {
        "episode": "第1集",
        "title": "测试",
        "style_contract": {
            "风格名": "国漫写实",
            "视觉基调": "国漫短剧质感",
            "镜头与构图": "竖屏短剧镜头",
            "光色策略": "低饱和冷灰",
            "运动边界": "慢推",
            "风格禁忌": ["照片级毛孔"],
            "style_anchor": ["出图/共享/图片/风格锚_国漫写实.png"],
        },
        "visual_contract": {
            "色调基线": "冷灰",
            "场景光位锚": {},
            "场景轴线视线": {},
            "景别阶梯": "MS->CU",
        },
        "clips": [],
    }

    style_prompt = image_prompt_pack.shared_style_anchor_prompt(story)
    overview = image_prompt_pack.overview_md(tmp_path, "第1集", story, [], 0)

    assert "STYLE_ANCHOR / 国漫写实" in style_prompt
    assert "`出图/共享/图片/风格锚_国漫写实.png`" in style_prompt
    assert "no room set, no window, no furniture" in style_prompt
    assert "style_anchor：`出图/共享/图片/风格锚_国漫写实.png`" in overview


def test_style_anchor_registry_marks_existing_anchor_ready(tmp_path: Path) -> None:
    rel = "出图/共享/图片/风格锚_国漫写实.png"
    anchor = tmp_path / rel
    anchor.parent.mkdir(parents=True)
    anchor.write_bytes(b"style-anchor")
    story = {
        "style_contract": {
            "风格名": "国漫写实",
            "style_anchor": [rel],
        }
    }

    registry = image_prompt_pack.style_anchor_registry(tmp_path, story)

    selected = registry["selected_anchor"]
    assert registry["kind"] == "n2d_style_anchor_registry"
    assert selected["path"] == rel
    assert selected["status"] == "ready"
    assert selected["use_policy"] == "style_only"
    assert selected["identity_policy"] == "do_not_clone_face_or_costume"
    assert selected["sha256"] == image_prompt_pack.sha256_file(anchor)


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


def test_project_asset_hints_prevent_ascii_id_display_names(tmp_path: Path) -> None:
    story = {"clips": [{"object_ids": ["PROP_IRON_BOWL", "PROP_EMPTY_BUCKETS", "PROP_RUST_LOCK"]}]}

    defs = image_prompt_pack.derive_asset_defs(tmp_path, story)

    assert defs["PROP_IRON_BOWL"]["name"] == "旧铁碗"
    assert defs["PROP_EMPTY_BUCKETS"]["name"] == "空木桶"
    assert defs["PROP_RUST_LOCK"]["name"] == "生锈铁锁"
    assert defs["PROP_RUST_LOCK"]["weapon_like_role"] == "not_entity_weapon"


def test_derived_scene_drift_uses_generic_continuity_not_stale_wildland(tmp_path: Path) -> None:
    story = {"clips": [{"location_id": "LOC_UNKNOWN_HALL"}]}

    defs = image_prompt_pack.derive_asset_defs(tmp_path, story)
    drift = "；".join(defs["LOC_UNKNOWN_HALL"]["drift"])

    assert "巨岩/尸堆" not in drift
    assert "空间轴线" in drift


def test_shared_scene_and_asset_prompts_expand_registry_constraints(tmp_path: Path) -> None:
    old_defs = image_prompt_pack.ASSET_DEFS
    try:
        image_prompt_pack.ASSET_DEFS = {
            "LOC_TEST": {
                "type": "scene",
                "name": "荒野官道夜路",
                "path_name": "定妆_场景_荒野官道夜路",
                "positive": "荒野官道夜路",
                "negative": "现代物件",
                "constraints": {
                    "layout": "官道纵深从画面下方通向远处",
                    "light_anchor": "冷月主光，右后方火把暖边光",
                    "axis_rules": "反打不越轴",
                },
                "scene_dna": {
                    "landmarks": ["窄土路", "枯草", "乱石"],
                    "resident_assets": ["火把", "马队远影"],
                    "architecture_materials": "泥土官道、枯草、乱石",
                },
            },
            "PROP_TEST": {
                "type": "prop",
                "name": "镇魔司黑衣赤纹",
                "path_name": "定妆_道具_镇魔司黑衣赤纹",
                "positive": "镇魔司黑衣赤纹",
                "negative": "现代物件",
                "constraints": {
                    "structure": "黑色交领窄袖、束腰、衣襟袖口克制暗红纹样",
                    "face_policy": "faceless",
                },
                "scene_dna": {
                    "spatial_layout": "无脸人台或折叠衣物尺度参考",
                    "architecture_materials": "旧布、皮革、暗红纹样",
                    "color_lighting_weather": "继承冷灰夜路光位",
                },
                "owner": "CHAR_01",
                "current_state": "沾血尘但结构完整",
            },
        }

        scene_prompt = image_prompt_pack.shared_scene_prompt({})
        asset_prompt = image_prompt_pack.shared_asset_prompt("prop", "道具定妆", ["PROP_TEST"])
        registry = image_prompt_pack.build_asset_registry(tmp_path)
    finally:
        image_prompt_pack.ASSET_DEFS = old_defs

    assert "官道纵深从画面下方通向远处" in scene_prompt
    assert "冷月主光，右后方火把暖边光" in scene_prompt
    assert "反打不越轴" in scene_prompt
    assert "黑色交领窄袖、束腰、衣襟袖口克制暗红纹样" in asset_prompt
    assert "无脸人台或折叠衣物尺度参考" in asset_prompt
    assert "资产参考图默认不生成未绑定身份的清晰人物脸" in asset_prompt
    scene_asset = next(item for item in registry["assets"] if item["id"] == "LOC_TEST")
    signature = scene_asset["constraints"]["lighting_signature"]
    assert signature["color_temperature"] == "mixed_cool_warm"
    assert signature["key_light_direction"] == "right"
    assert "mean_hue" not in signature
    assert signature["numeric_measurement"] == "pending_after_landed_frame_qc"


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


def test_full_reference_group_prefers_tight_expression_refs(tmp_path: Path) -> None:
    image_dir = tmp_path / "出图" / "共享" / "图片"
    image_dir.mkdir(parents=True)
    for name in (
        "定妆_CHAR_TEST__常态_正面.png",
        "定妆_CHAR_TEST__常态_表情_克制.png",
        "定妆_CHAR_TEST__常态_表情_克制_脸锚裁切.png",
    ):
        (image_dir / name).write_bytes(b"\x89PNG\r\n\x1a\n")

    cfg = {
        "asset_key": "CHAR_TEST__常态",
        "name": "测试角色",
        "form": "常态",
    }

    rg, atlas = image_prompt_pack.full_reference_group(tmp_path, "CHAR_TEST", cfg)

    assert rg["expressions"][0]["path"].endswith("_表情_克制_脸锚裁切.png")
    assert atlas["expression_refs"][0]["path"] == rg["expressions"][0]["path"]
    assert rg["face_anchor_refs"][0]["path"].endswith("_表情_克制_脸锚裁切.png")


def test_clip_assets_do_not_bind_plain_alias_from_prose() -> None:
    clip = {
        "description": "姜月初想起百妖谱规则，但本镜不出现面板。",
        "object_ids": ["WEAPON_01 横刀"],
    }

    assert image_prompt_pack.clip_assets(clip) == ["WEAPON_01"]


def test_continuity_targets_use_explicit_action_anchors() -> None:
    clip = {
        "firstframe_png": "出图/第2集/图片/Clip03_first.png",
        "endframe_png": "出图/第2集/图片/Clip03_end.png",
        "continuity": {
            "need_endframe": True,
            "anchors": [
                {"anchor_png": "出图/第2集/图片/Clip03_a1.png"},
                {"anchor_png": "出图/第2集/图片/Clip03_a2.png"},
            ],
        },
    }

    assert image_prompt_pack.continuity_frame_count(clip) == (4, True, True)

    paths, parts = image_prompt_pack.continuity_target_paths("第2集", 3, clip)

    assert paths == [
        "出图/第2集/图片/Clip03_first.png",
        "出图/第2集/图片/Clip03_a1.png",
        "出图/第2集/图片/Clip03_a2.png",
        "出图/第2集/图片/Clip03_end.png",
    ]
    assert "Clip03_mid.png" not in " ".join(paths)
    assert "动作锚帧 a2" in "；".join(parts)


def test_body_grounding_directive_prevents_buried_closeup_crop() -> None:
    clip = {
        "label": "读懂长久买卖",
        "continuity": {"shot_size": "CU 低声盘算→INSERT 横刀与掌心"},
    }

    directive = image_prompt_pack.body_grounding_directive(
        clip,
        "CU 低声盘算→INSERT 横刀与掌心",
        "姜月初盯着空面板消散的位置，眼神从惊惧转为计算。",
    )

    assert "裁切必须明确" in directive
    assert "似蹲非蹲" in directive
    assert "半截埋进地里" in directive


def test_body_grounding_directive_requires_readable_knees_for_kneel() -> None:
    directive = image_prompt_pack.body_grounding_directive(
        {"label": "替裴合眼"},
        "中景",
        "姜月初走回裴长青身边，尸场恢复冷灰，她蹲下替他合眼。",
    )

    assert "双膝/小腿/脚靴" in directive
    assert "埋进土里" in directive
    assert "身体接触面" in directive
    assert "不埋入" in directive
    assert "不穿模" in directive
    assert "不融合" in directive


def test_anatomy_integrity_directive_supplies_lint_contract() -> None:
    directive = image_prompt_pack.anatomy_integrity_directive(["CHAR_01"], "MS 俯拍")

    assert "人体完整性/解剖完整性" in directive
    assert "可见身体范围" in directive
    assert "画幅裁切" in directive
    assert "额外手" in directive
    assert "身体埋入" in directive


def test_lens_defaults_supply_physical_camera_parameters() -> None:
    assert image_prompt_pack.lens_with_physical_defaults("CU 近景反打", "抬眼") == "CU 近景反打；物理镜头参数：85mm, f/1.8"
    assert image_prompt_pack.lens_with_physical_defaults("MS 中景", "") == "MS 中景；物理镜头参数：50mm, f/2.8"
    assert image_prompt_pack.lens_with_physical_defaults("LS 全景", "") == "LS 全景；物理镜头参数：24mm, f/5.6"
    assert image_prompt_pack.lens_with_physical_defaults("CU 近景 90mm f/2", "") == "CU 近景 90mm f/2"


def test_shot_prompt_section_emits_identity_lock_phrase_and_lens_params(tmp_path: Path) -> None:
    clip = {
        "id": "EP01_CLIP01",
        "label": "近景反打",
        "character_ids": ["CHAR_SHEN_YAN"],
        "continuity": {"shot_size": "CU 近景"},
        "description": "沈砚抬眼看向证据。",
    }

    text = image_prompt_pack.shot_prompt_section(tmp_path, "第1集", 1, clip, {}, {"clips": [clip]})

    assert "**身份锁定句**" in text
    assert "\n身份保持：" in text
    assert "\n身份锁定句：" in text
    assert "`CHAR_SHEN_YAN/常态` 必须与人物定妆和脸部特写参考保持同一张脸" in text
    assert "物理镜头参数：85mm, f/1.8" in text


def test_shot_prompt_section_sanitizes_false_screen_director_injection(tmp_path: Path) -> None:
    clip = {
        "id": "EP01_CLIP05",
        "label": "挑水压迫蒙太奇",
        "template": "labor_montage",
        "character_ids": ["CHAR_HE_PINGSHENG"],
        "object_ids": ["PROP_WATER_BUCKETS"],
        "continuity": {"shot_size": "CU", "need_endframe": True},
        "description": "扁担压肩、水桶溢水、脚步打滑三连剪。",
    }
    drow = {"image_prompt_injection": {
        "镜头/机位": "CU",
        "起幅·运动余量": "为「固定机位，锁定屏幕/光幕平面，不漂移，只允许轻微呼吸式微动」预留前景/背景运动余量。",
        "导演意图": "屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。",
    }}

    text = image_prompt_pack.shot_prompt_section(tmp_path, "第1集", 1, clip, drow, {"clips": [clip]})

    assert "屏幕/面板镜" not in text
    assert "锁定屏幕/光幕平面" not in text
    assert "挑水蒙太奇以身体代价为第一目标" in text


def test_nonfinal_endframe_exemption_is_not_called_final_shot(tmp_path: Path) -> None:
    clips = [
        {
            "id": "EP01_CLIP01",
            "character_ids": ["CHAR_HE_PINGSHENG"],
            "continuity": {
                "shot_size": "CU",
                "need_endframe": False,
                "endframe_exempt_reason": "快闪到夜路为空间跳转，用空镜缓冲。",
            },
            "description": "破旧包袱快闪。",
        },
        {
            "id": "EP01_CLIP02",
            "character_ids": ["CHAR_HE_PINGSHENG"],
            "continuity": {"shot_size": "CU", "need_endframe": False},
            "description": "最终硬断。",
        },
    ]

    text = image_prompt_pack.shot_prompt_section(tmp_path, "第1集", 1, clips[0], {}, {"clips": clips})

    assert "本镜尾帧豁免" in text
    assert "末镜无尾帧" not in text


def test_hand_ownership_directive_supplies_lint_contract() -> None:
    directive = image_prompt_pack.hand_ownership_directive(
        ["CHAR_01", "CHAR_02"],
        ["WEAPON_01"],
        "姜月初蹲下替裴长青合眼。",
    )

    assert "手部归属" in directive
    assert "同侧手腕" in directive
    assert "同侧前臂" in directive
    assert "接触点" in directive
    assert "CHAR_01" in directive


def test_face_visibility_directive_supplies_codex_dark_vfx_guard() -> None:
    directive = image_prompt_pack.face_visibility_directive(
        ["CHAR_01"],
        "CU 近景",
        "黑烟暗光特效压脸，角色低声盘算。",
    )

    assert "眼鼻嘴三角区清晰" in directive
    assert "不得遮住眼鼻嘴" in directive
    assert "不得遮住五官" in directive
    assert "不得重画脸" in directive


def test_existing_asset_bundle_creates_missing_sections(tmp_path: Path) -> None:
    cfg = {
        "name": "姜月初",
        "scope": "主角",
        "asset_bundle": {
            "manifest": "设定库/character_assets/CHAR_01__姜月初/manifest.json",
            "package_dir": "设定库/character_assets/CHAR_01__姜月初",
        },
    }

    bundle = image_prompt_pack.ensure_asset_bundle(tmp_path, "CHAR_01", cfg)

    for sec in ("reference", "prompts", "lora", "voice", "adapters", "qc"):
        assert sec in bundle["sections"]
        assert (tmp_path / bundle["sections"][sec]).is_dir()


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


def test_char01_gets_character_level_longline_scope_and_tier(tmp_path: Path) -> None:
    card_dir = tmp_path / "设定库" / "characters"
    card_dir.mkdir(parents=True)
    (card_dir / "姜月初.md").write_text(
        "\n".join([
            "# 角色卡 — 姜月初（ID: CHAR_01）",
            "- 身份：二十一世纪现代人穿越者；百妖谱宿主。",
            "- 固定外貌：东方少女脸。",
            "- 固定服装：灰褐囚服。",
            "- **锚点句**：黑色半散长发·灰褐粗布囚服",
        ]),
        encoding="utf-8",
    )
    story = {"clips": [{"character_ids": ["CHAR_01"]}]}

    defs = image_prompt_pack.derive_character_defs(tmp_path, story)
    assert "核心主角/全篇长线" in defs["CHAR_01"]["scope"]
    assert defs["CHAR_01"]["narrative_tier"] == "核心长线"

    old_defs = image_prompt_pack.CHARACTER_DEFS
    try:
        image_prompt_pack.CHARACTER_DEFS = defs
        registry = image_prompt_pack.build_identity_registry(tmp_path)
    finally:
        image_prompt_pack.CHARACTER_DEFS = old_defs

    char = registry["characters"][0]
    assert char["id"] == "CHAR_01"
    assert char["tier"] == "核心长线"
    assert "核心主角/全篇长线" in char["scope"]


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
