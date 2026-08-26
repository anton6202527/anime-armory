import importlib.util
import hashlib
import json
import sys
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).with_name("image_prompt_pack.py")
SPEC = importlib.util.spec_from_file_location("image_prompt_pack", MODULE_PATH)
image_prompt_pack = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = image_prompt_pack
SPEC.loader.exec_module(image_prompt_pack)
visual_reference_policy = sys.modules["visual_reference_policy"]


def test_character_makeup_prompt_requires_neutral_gray_backdrop() -> None:
    old = image_prompt_pack.CHARACTER_DEFS
    image_prompt_pack.CHARACTER_DEFS = {
        "CHAR_TEST": {
            "name": "测试角色", "scope": "本集角色", "form": "常态", "tier": "core",
            "library_tier": "named_minimal", "planned_episode_count": 1,
            "asset_key": "CHAR_TEST__常态", "anchor": "测试角色身份锚",
            "age_context": "成年", "face": "稳定脸型", "hair": "稳定发型",
            "outfit": "项目定义服装", "accessories": "无", "texture": "项目材质",
            "performance_signature": "克制", "relative_scale": "标准体量", "drift": [],
        }
    }
    try:
        prompt = image_prompt_pack.shared_character_prompt()
    finally:
        image_prompt_pack.CHARACTER_DEFS = old

    assert "统一中性灰白/18%灰棚拍背景" in prompt
    assert "无窗、无房间、无家具、无剧情道具" in prompt
    assert "### 定妆图提交口径" in prompt
    for key in ("角色身份：", "年龄/年龄档：", "固定外貌：", "服装妆造：", "定妆要求：", "画风规格：", "禁止："):
        assert key in prompt
    assert "不要雨窗/房间/家具场景" in image_prompt_pack.shared_style_anchor_prompt()
    assert "same studio/rain-window background" not in prompt
    assert "深灰/雨窗影棚背景" not in prompt
    assert "资产包 `角色库/" in prompt
    assert "设定库/character_assets" not in prompt


def test_compiler_injection_uses_project_aspect_style_and_backend(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text(
        "画幅：16:9\n生图AI：Codex\n生图模型：GPT Image 2\n",
        encoding="utf-8",
    )
    story = {
        "style_contract": {
            "风格名": "二维剪纸动画",
            "视觉基调": "纸张纤维与平面层叠",
            "光色策略": "暖金侧光",
        }
    }
    source = """# 分镜

## 镜头 1
**目标落档**：`出图/第1集/图片/Clip01_first.png`
**导演意图**：角色发现追兵。
**剧本描述**：`CHAR_01/常态` 回头握刀。
### 正向 prompt（中文）
```text
锚点句：CHAR_01 黑发女剑客；
镜头构图：低机位中景；
动作瞬间：回头握刀；
场景光影：雨夜屋脊；
情绪张力：警觉；
画风规格：继承项目风格；
禁止：文字、水印；
```
"""

    rendered = image_prompt_pack.inject_compiled_image_prompts(
        tmp_path, story, source, default_mode="firstframe"
    )

    assert "### 后端编译提交 image prompt" in rendered
    assert "profile=codex_gpt_image_agent_brief" in rendered
    assert "二维剪纸动画" in rendered
    assert "画幅：16:9" in rendered
    assert "9:16" not in rendered
    assert "写实国漫" not in rendered


def test_character_library_tiers_use_story_weight_and_ten_episode_threshold() -> None:
    tier = image_prompt_pack.character_library_tier

    assert tier(scope="主角/全篇长线", narrative_tier="核心长线", episode_count=1) == "core_full"
    assert tier(scope="普通配角", narrative_tier="单集角色", episode_count=10) == "core_full"
    assert tier(scope="多集复现配角", narrative_tier="单集角色", episode_count=3) == "recurring_standard"
    assert tier(scope="第1集具名短线角色", narrative_tier="单集角色", episode_count=1) == "named_minimal"
    assert tier(scope="群像局部", narrative_tier="局部参考", episode_count=12, restricted=True) == "restricted_partial"


def test_negated_main_character_phrase_does_not_upgrade_one_episode_role() -> None:
    scope, narrative_tier = image_prompt_pack.narrative_scope_for(
        "CHAR_MAGISTRATE",
        "只作为本集公务角色，不抢主角视觉重心。",
        "core",
    )

    assert "不抢主角" in scope
    assert narrative_tier == "单集角色"


def test_generic_door_hint_does_not_leak_another_projects_scene() -> None:
    assert image_prompt_pack.ASSET_ID_HINTS == {}


def test_missing_character_card_fails_closed_instead_of_using_demo_fallback(tmp_path: Path) -> None:
    story = {"clips": [{"character_ids": ["CHAR_WANG_DUN", "CHAR_HE_PINGSHENG"]}]}

    with pytest.raises(image_prompt_pack.PromptPackContractError, match="CHAR_WANG_DUN"):
        image_prompt_pack.derive_character_defs(tmp_path, story)


def test_project_character_card_does_not_invent_demo_extra_form(tmp_path: Path) -> None:
    card_dir = tmp_path / "设定库" / "characters"
    card_dir.mkdir(parents=True)
    (card_dir / "姜月初.md").write_text(
        "# 角色卡 — 姜月初（ID: CHAR_01）\n"
        "- 身份：核心主角/全篇长线\n"
        "- 形态变体：囚途残损态\n"
        "- 识别锚点：窄椭圆脸、细长杏眼、乌黑长发\n",
        encoding="utf-8",
    )
    story = {
        "clips": [{"character_ids": ["CHAR_01/镇魔司制服态"]}],
        "asset_requirements": {"characters": ["CHAR_01/镇魔司制服态"]},
    }

    defs = image_prompt_pack.derive_character_defs(tmp_path, story)

    assert defs["CHAR_01"]["form"] == "囚途残损态"
    assert "extra_forms" not in defs["CHAR_01"]


def test_unknown_character_id_fails_closed(tmp_path: Path) -> None:
    story = {"clips": [{"character_ids": ["CHAR_UNKNOWN_GUARD"]}]}

    with pytest.raises(image_prompt_pack.PromptPackContractError, match="CHAR_UNKNOWN_GUARD"):
        image_prompt_pack.derive_character_defs(tmp_path, story)


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


def test_project_local_numeric_character_id_does_not_leak_another_projects_fallback(tmp_path: Path) -> None:
    card_dir = tmp_path / "设定库" / "characters"
    card_dir.mkdir(parents=True)
    (card_dir / "虎山神.md").write_text(
        "# 角色卡 — 虎山神（ID: CHAR_04）\n\n"
        "- 身份：陇右荒野虎妖；百妖谱首次收录对象\n"
        "- 锚点句：吊睛白额虎头人身·小山强肩背·粗壮利爪·胸前贯穿伤与黑妖血。\n",
        encoding="utf-8",
    )
    story = {"clips": [{"character_ids": ["CHAR_04/复生态"]}]}

    cfg = image_prompt_pack.derive_character_defs(tmp_path, story)["CHAR_04"]

    assert cfg["name"] == "虎山神"
    assert "吊睛白额" in cfg["face"]
    assert "非人虎妖真身" in cfg["face"]
    assert "粗硬灰黄黑纹毛发" in cfg["hair"]
    assert "完整虎头人身妖物真身" in cfg["outfit"]
    assert cfg["anchor"].startswith("吊睛白额虎头人身")
    assert "成年古装角色" not in cfg["anchor"]
    assert "陈青源" not in json.dumps(cfg, ensure_ascii=False)
    assert "江湖劲装" not in cfg["outfit"]


def test_classical_tiger_phrase_stays_real_quadruped_without_explicit_demon_wording(tmp_path: Path) -> None:
    story = {
        "clips": [{"character_ids": ["BEAST_TIGER"]}],
        "character_materials": {
            "BEAST_TIGER": {
                "name": "景阳冈猛虎",
                "profile": "本集入镜；成年猛虎真身；吊睛白额、黑黄粗硬毛纹、宽大虎掌与真实兽类骨相。",
            }
        },
    }

    cfg = image_prompt_pack.derive_character_defs(tmp_path, story)["BEAST_TIGER"]
    payload = json.dumps(cfg, ensure_ascii=False)

    assert "成年猛虎真身" in cfg["face"]
    assert "四足" in payload
    assert "虎妖" not in payload
    assert "虎头人身" not in payload
    assert "人形强肩背" not in payload
    assert "普通四足老虎" not in payload


def test_reference_slot_writer_never_creates_hardcoded_numeric_character_card(tmp_path: Path) -> None:
    old_chars = image_prompt_pack.CHARACTER_DEFS
    old_assets = image_prompt_pack.ASSET_DEFS
    try:
        image_prompt_pack.CHARACTER_DEFS = {
            "CHAR_04": {
                "name": "虎山神",
                "scope": "陇右荒野虎妖",
                "form": "常态",
                "tier": "core",
                "library_tier": "recurring_standard",
                "planned_episode_count": 3,
                "asset_key": "CHAR_04__常态",
                "anchor": "吊睛白额虎头人身",
                "face": "非人虎妖真身",
                "hair": "灰黄黑纹毛发",
                "outfit": "虎头人身妖物真身",
                "accessories": "粗壮利爪",
                "relative_scale": "体魄如小山",
                "performance_signature": "傲慢捕食者",
                "drift": ["不要画成人类"],
            }
        }
        image_prompt_pack.ASSET_DEFS = {}
        image_prompt_pack.write_reference_slot_cards(tmp_path, "第1集")
    finally:
        image_prompt_pack.CHARACTER_DEFS = old_chars
        image_prompt_pack.ASSET_DEFS = old_assets

    assert not (tmp_path / "设定库" / "characters" / "陈青源.md").exists()


def test_shots_global_contract_is_not_a_shot_heading(tmp_path: Path) -> None:
    text = image_prompt_pack.shots_md(tmp_path, "第1集", {}, [])

    assert "\n### 剧本可看性全局合同\n" in text
    assert "\n## 剧本可看性全局合同\n" not in text


def test_weapon_refs_are_not_labeled_as_props() -> None:
    old = image_prompt_pack.ASSET_DEFS
    image_prompt_pack.ASSET_DEFS = {
        "WEAPON_TEST": {"path_name": "定妆_武器_测试刀", "type": "weapon"}
    }
    try:
        refs = image_prompt_pack.shot_refs([], ["WEAPON_TEST"])
    finally:
        image_prompt_pack.ASSET_DEFS = old

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
    weapon_positive = image_prompt_pack.shared_asset_positive(defs["WEAPON_TEST"])
    assert "武器拓扑" in weapon_positive
    assert "独立资产档案" in weapon_positive
    assert "无剧情场景、无人、无手、无脸" in weapon_positive
    assert "特效边界" in image_prompt_pack.shared_asset_positive(defs["VFX_TEST"])
    assert "独立特效资产档案" in image_prompt_pack.shared_asset_positive(defs["VFX_TEST"])
    assert "允许且只允许合同声明的受控特效形态" in image_prompt_pack.shared_asset_positive(defs["VFX_TEST"])

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


def test_body_bound_vfx_allows_faceless_anatomy_without_generic_no_hand_conflict() -> None:
    cfg = {
        "id": "VFX_BACKLASH",
        "type": "vfx",
        "name": "道行反噬",
        "positive": "手臂震颤、呼吸失控、轻微血点与肌肉拉扯；不新增虎纹或兽化。",
        "constraints": {
            "face_policy": "faceless",
            "structure": "手臂震颤、呼吸失控、轻微血点与肌肉拉扯。",
        },
    }

    positive = image_prompt_pack.shared_asset_positive(cfg)

    assert image_prompt_pack.asset_is_body_bound_vfx(cfg) is True
    assert "独立身体绑定特效档案" in positive
    assert "允许下巴以下躯干、手臂或手部" in positive
    assert "不得出现头部、清晰人脸、头发" in positive
    assert "无人、无手、无脸" not in positive
    assert "不新增服装形态、兽化特征" in positive


def test_named_saber_gets_single_cutting_edge_and_offset_tip_contract(tmp_path: Path) -> None:
    registry_path = tmp_path / "出图" / "共享" / "asset_registry.json"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(json.dumps({
        "assets": [{
            "id": "WEAPON_01",
            "type": "weapon",
            "name": "横刀",
            "constraints": {"structure": "大唐制式横刀，暗银直身刀刃"},
        }]
    }, ensure_ascii=False), encoding="utf-8")
    story = {"clips": [{"weapon_ids": ["WEAPON_01"]}], "visual_contract": {}}

    weapon = image_prompt_pack.derive_asset_defs(tmp_path, story)["WEAPON_01"]
    topology = image_prompt_pack.flatten_contract_value(weapon["constraints"]["blade_topology"])

    assert "cutting_edge_count=1" in topology
    assert "连续厚钝刀背" in topology
    assert "刀尖偏向刃侧" in topology
    assert "对称剑尖" in topology


def test_project_defined_sabers_get_weapon_profiles_without_demo_alias(tmp_path: Path) -> None:
    story = {
        "clips": [{"object_ids": ["WEAPON_MAIN", "WEAPON_BROKEN"]}],
        "asset_materials": {
            "WEAPON_MAIN": {"name": "制式横刀", "type": "weapon", "profile": "一柄暗银直身单刃横刀"},
            "WEAPON_BROKEN": {"name": "断裂横刀", "type": "weapon", "profile": "一柄断裂的暗银单刃横刀，断口粗粝"},
        },
        "visual_contract": {},
    }

    defs = image_prompt_pack.derive_asset_defs(tmp_path, story)

    assert defs["WEAPON_MAIN"]["alias_of"] == ""
    assert defs["WEAPON_MAIN"]["weapon_like_role"] == "entity_weapon"
    assert defs["WEAPON_MAIN"]["weapon_profile"]["design_intent"]
    assert "cutting_edge_count=1" in image_prompt_pack.flatten_contract_value(
        defs["WEAPON_BROKEN"]["constraints"]["blade_topology"]
    )
    old_defs = image_prompt_pack.ASSET_DEFS
    try:
        image_prompt_pack.ASSET_DEFS = defs
        registry = image_prompt_pack.build_asset_registry(tmp_path)
    finally:
        image_prompt_pack.ASSET_DEFS = old_defs
    prop_saber = next(row for row in registry["assets"] if row["id"] == "WEAPON_MAIN")
    broken_saber = next(row for row in registry["assets"] if row["id"] == "WEAPON_BROKEN")
    assert "alias_of" not in prop_saber
    assert broken_saber["weapon_profile"]["forbidden_drift"]


def test_named_saber_topology_canonicalization_is_idempotent() -> None:
    base = image_prompt_pack.SINGLE_EDGE_BLADE_TOPOLOGY
    custom = "weapon_count=1；single_straight_blade=1；副手不得生成第二把刀。"

    once = image_prompt_pack.canonical_single_edge_topology([base, base, custom])
    twice = image_prompt_pack.canonical_single_edge_topology(once)

    assert once == twice
    assert image_prompt_pack.flatten_contract_value(twice).count(base) == 1
    assert custom in image_prompt_pack.flatten_contract_value(twice)


def test_material_asset_map_reads_compact_shared_asset_bullets(tmp_path: Path) -> None:
    material = tmp_path / "脚本" / "第1集" / "素材清单.md"
    material.parent.mkdir(parents=True)
    material.write_text(
        """# 素材清单
## 共享资产
- `PROP_01/断刀`：暗色旧钢军用直刃，半截、沾血、无华丽纹饰。
- `PROP_02/镇魔司横刀`：同僚尸旁遗落的完整军用横刀，长直刃、无华饰。
- `VFX_01/百妖谱底框`：黑金古卷，内部留空，文字后期 overlay。
""",
        encoding="utf-8",
    )
    story = {"episode": 1}

    assets = image_prompt_pack.material_asset_map(tmp_path, story)

    assert assets["PROP_01"]["name"] == "断刀"
    assert "半截" in assets["PROP_01"]["profile"]
    assert assets["PROP_02"]["name"] == "镇魔司横刀"
    assert assets["VFX_01"]["name"] == "百妖谱底框"


def test_material_asset_map_reads_name_after_backticked_id(tmp_path: Path) -> None:
    material = tmp_path / "脚本" / "第1集" / "素材清单.md"
    material.parent.mkdir(parents=True)
    material.write_text(
        "## 关键道具\n\n- `PROP_DOOR` 武大家木门：北宋小民旧木板门，合门后不自动落闩。\n",
        encoding="utf-8",
    )

    assets = image_prompt_pack.material_asset_map(tmp_path, {"episode": "第1集"})

    assert assets["PROP_DOOR"]["name"] == "武大家木门"
    assert "不自动落闩" in assets["PROP_DOOR"]["profile"]


def test_current_material_truth_replaces_stale_registry_semantics(tmp_path: Path) -> None:
    material = tmp_path / "脚本" / "第1集" / "素材清单.md"
    material.parent.mkdir(parents=True)
    material.write_text(
        "## 关键道具\n\n- `PROP_DOOR` 武大家木门：北宋小民旧木板门，合门后不自动落闩。\n",
        encoding="utf-8",
    )
    registry = tmp_path / "出图" / "共享" / "asset_registry.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps({
            "assets": [{
                "id": "PROP_DOOR",
                "name": "破屋木门",
                "constraints": {"structure": "贺平生杂役小屋的粗糙木门"},
                "scene_dna": {"belonging_anchor": "贺平生杂役小屋"},
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    story = {"episode": "第1集", "clips": [{"object_ids": ["PROP_DOOR"]}], "visual_contract": {}}

    defs = image_prompt_pack.derive_asset_defs(tmp_path, story)

    door = defs["PROP_DOOR"]
    assert door["name"] == "武大家木门"
    assert "不自动落闩" in door["positive"]
    assert "贺平生" not in json.dumps(door, ensure_ascii=False)


def test_material_asset_map_expands_grouped_asset_heading_without_id_alias_pollution(tmp_path: Path) -> None:
    material = tmp_path / "脚本" / "第1集" / "素材清单.md"
    material.parent.mkdir(parents=True)
    material.write_text(
        """# 素材清单
## 道具出图
### PROP_扁担 + PROP_水桶

暗黄老竹扁担；两只同款旧木桶，铁箍暗锈，数量永远是二。

## 风格锚

这段不属于道具描述。
""",
        encoding="utf-8",
    )

    assets = image_prompt_pack.material_asset_map(tmp_path, {"episode": 1})

    assert set(assets) == {"PROP_扁担", "PROP_水桶"}
    assert assets["PROP_扁担"]["name"] == "PROP 扁担"
    assert assets["PROP_水桶"]["name"] == "PROP 水桶"
    assert "两只同款旧木桶" in assets["PROP_扁担"]["profile"]
    assert "两只同款旧木桶" in assets["PROP_水桶"]["profile"]
    assert "+ PROP_水桶" not in assets["PROP_扁担"]["profile"]
    assert "这段不属于道具描述" not in assets["PROP_扁担"]["profile"]


def test_material_asset_map_repairs_stale_group_heading_pollution_from_generated_registry(tmp_path: Path) -> None:
    material = tmp_path / "脚本" / "第1集" / "素材清单.md"
    material.parent.mkdir(parents=True)
    material.write_text(
        "### PROP_扁担 + PROP_水桶\n\n暗黄老竹扁担；两只旧木桶，铁箍暗锈。\n",
        encoding="utf-8",
    )
    registry = tmp_path / "出图" / "共享" / "asset_registry.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({
        "assets": [{
            "id": "PROP_扁担",
            "type": "prop",
            "constraints": {"structure": "+ PROP_水桶"},
            "drift_forbidden": ["不要让+ PROP_水桶结构漂移"],
            "scene_dna": {"landmarks": ["+ PROP_水桶"]},
        }],
    }, ensure_ascii=False), encoding="utf-8")
    story = {"episode": 1, "clips": [{"object_ids": ["PROP_扁担", "PROP_水桶"]}]}

    defs = image_prompt_pack.derive_asset_defs(tmp_path, story)

    assert defs["PROP_扁担"]["positive"].startswith("暗黄老竹扁担")
    assert "+ PROP_水桶" not in json.dumps(defs["PROP_扁担"], ensure_ascii=False)


def test_landed_prop_primary_does_not_impersonate_scale_or_in_hand_views(tmp_path: Path) -> None:
    primary = tmp_path / "出图" / "共享" / "图片" / "定妆_武器_横刀.png"
    primary.parent.mkdir(parents=True)
    primary.write_bytes(b"landed-primary")
    old_defs = image_prompt_pack.ASSET_DEFS
    try:
        image_prompt_pack.ASSET_DEFS = {
            "WEAPON_01": {
                "type": "weapon",
                "name": "横刀",
                "path_name": "定妆_武器_横刀",
                "constraints": {"structure": "单把单刃横刀"},
                "drift": [],
            }
        }
        weapon = image_prompt_pack.build_asset_registry(tmp_path)["assets"][0]
    finally:
        image_prompt_pack.ASSET_DEFS = old_defs

    assert weapon["reference_group"]["primary"]["status"] == "ready"
    assert weapon["reference_group"]["scale_ref"] == {
        "path": "出图/共享/图片/定妆_武器_横刀_比例.png",
        "status": "planned",
    }
    assert weapon["reference_group"]["in_hand"] == {
        "path": "出图/共享/图片/定妆_武器_横刀_手持.png",
        "status": "planned",
    }


def test_large_vehicle_prop_uses_reverse_structure_view_not_absurd_in_hand_board(tmp_path: Path) -> None:
    old_defs = image_prompt_pack.ASSET_DEFS
    try:
        image_prompt_pack.ASSET_DEFS = {
            "PROP_CART": {
                "type": "prop",
                "name": "翻覆囚车",
                "path_name": "定妆_道具_翻覆囚车",
                "positive": "唐代双轮粗木囚车残骸",
                "constraints": {"structure": "一辆翻覆木车"},
                "drift": [],
            }
        }
        cart = image_prompt_pack.build_asset_registry(tmp_path)["assets"][0]
    finally:
        image_prompt_pack.ASSET_DEFS = old_defs

    assert "in_hand" not in cart["reference_group"]
    assert cart["reference_group"]["reverse"] == {
        "path": "出图/共享/图片/定妆_道具_翻覆囚车_反面.png",
        "status": "planned",
    }
    assert cart["reference_group"]["scale_ref"]["path"].endswith("_比例.png")


def test_clip_assets_do_not_promote_offscreen_presence() -> None:
    clip = {
        "object_ids": ["WEAPON_TEST"],
        "entity_schedule": {
            "offscreen_presence": ["VFX_FUTURE_REVEAL"],
        },
        "continuity": {
            "entry_exit": "VFX_FUTURE_REVEAL 只作后段气息，不抢首帧接力。",
        },
    }

    assets = image_prompt_pack.clip_assets(clip)

    assert "WEAPON_TEST" in assets
    assert "VFX_FUTURE_REVEAL" not in assets


def test_pre_reveal_vfx_is_removed_from_shot_prompt(tmp_path: Path) -> None:
    old_assets = image_prompt_pack.ASSET_DEFS
    old_chars = image_prompt_pack.CHARACTER_DEFS
    try:
        image_prompt_pack.ASSET_DEFS = {
            "VFX_FUTURE_REVEAL": {
                "type": "vfx",
                "name": "血虎摹影",
                "path_name": "定妆_特效_血虎摹影",
                "positive": "半透明血虎摹影",
                "constraints": {
                    "reveal_min_clip": 6,
                    "pre_reveal_policy": "Clip06 前不得渲染虎形摹影。",
                    "reveal_terms": ["暗红虎形杀伐气", "血虎", "虎形摹影"],
                },
                "drift": [],
            }
        }
        image_prompt_pack.CHARACTER_DEFS = {}
        clip = {
            "id": "EP01_CLIP02",
            "label": "早段动作",
            "template": "fight_exchange",
            "object_ids": ["VFX_FUTURE_REVEAL"],
            "shots": [{"desc": "姜月初起刀，身后暗红虎形杀伐气短促显现。"}],
            "template_contract": {
                "blocking": "可见主体=CHAR_01、VFX_FUTURE_REVEAL、LOC_01；",
                "beats": ["起刀", "血虎显现"],
            },
        }

        shot_text = image_prompt_pack.shot_prompt_section(tmp_path, "第1集", 2, clip, {}, {"clips": [clip]})
        reveal_text = image_prompt_pack.shot_prompt_section(tmp_path, "第1集", 6, clip, {}, {"clips": [clip] * 6})
    finally:
        image_prompt_pack.ASSET_DEFS = old_assets
        image_prompt_pack.CHARACTER_DEFS = old_chars

    assert "特效定妆" not in shot_text
    assert "身后暗红虎形杀伐气短促显现" not in shot_text
    assert "绑定 `VFX_FUTURE_REVEAL`" not in shot_text
    assert "本镜 Clip02 禁用未到显现时机资产" in shot_text
    assert "不得出现：暗红虎形杀伐气、血虎、虎形摹影" in shot_text
    assert "绑定 `VFX_FUTURE_REVEAL`" in reveal_text


def test_offscreen_future_vfx_adds_guard_but_not_reference(tmp_path: Path) -> None:
    old_assets = image_prompt_pack.ASSET_DEFS
    old_chars = image_prompt_pack.CHARACTER_DEFS
    try:
        image_prompt_pack.ASSET_DEFS = {
            "VFX_FUTURE_REVEAL": {
                "type": "vfx",
                "name": "未来虎影",
                "constraints": {
                    "reveal_min_clip": 6,
                    "pre_reveal_policy": "Clip06 前只可画外伏笔。",
                    "reveal_terms": ["血虎", "虎影"],
                },
                "drift": [],
            }
        }
        image_prompt_pack.CHARACTER_DEFS = {}
        clip = {
            "id": "EP01_CLIP04",
            "label": "反打桥接",
            "shots": [{"desc": "反派伏身出击，前景尘土压低。"}],
            "entity_schedule": {
                "offscreen_presence": ["VFX_FUTURE_REVEAL"],
            },
        }
        story = {
            "clips": [clip],
            "style_contract": {
                "风格名": "冷灰写实3D国风漫剧",
                "视觉基调": "战斗真实有重量，妖气与血虎虚影克制，不做高饱和页游光效。",
            },
        }

        shot_text = image_prompt_pack.shot_prompt_section(tmp_path, "第1集", 4, clip, {}, story)
    finally:
        image_prompt_pack.ASSET_DEFS = old_assets
        image_prompt_pack.CHARACTER_DEFS = old_chars

    assert "特效定妆" not in shot_text
    assert "绑定 `VFX_FUTURE_REVEAL`" not in shot_text
    assert "本镜 Clip04 禁用未到显现时机资产" in shot_text
    assert "不得出现：血虎、虎影" in shot_text
    assert "妖气与血虎虚影克制" not in shot_text


def test_shot_prompt_consumes_shot_reverse_contract(tmp_path: Path) -> None:
    ep = "第1集"
    (tmp_path / "脚本" / ep).mkdir(parents=True)
    (tmp_path / "脚本" / ep / "shot_reverse_contract.json").write_text(json.dumps({
        "kind": "n2d_shot_reverse_contract",
        "patterns": [{
            "clip_id": "EP01_CLIP02",
            "axis_id": "AXIS_LOC_HALL_CHAR_A_VS_CHAR_B",
            "participants": {
                "A": {"character_id": "CHAR_A", "screen_position": "画左前景", "eyeline_direction": "看画右，不看镜头"},
                "B": {"character_id": "CHAR_B", "screen_position": "画右中景", "eyeline_direction": "看画左，不看镜头"},
            },
            "screen_sides": {"spatial_mode": "left_right"},
            "coverage": {
                "a_ots": "焦点 CHAR_A；CHAR_B 的前景肩部虚化",
                "b_ots": "焦点 CHAR_B；CHAR_A 的前景肩部虚化",
            },
            "camera_coverage": "clean single + OTS + insert",
            "lens_height_distance_match": "50-85mm 中长焦，相近高度和距离",
            "crossing_axis_policy": "禁止越轴；需要建立镜缓冲",
            "buffer_or_reestablishing": "火把插入或双人建立镜",
        }],
    }, ensure_ascii=False), encoding="utf-8")
    clip = {
        "id": "EP01_CLIP02",
        "template": "dialogue_shot_reverse",
        "description": "两人对峙。",
        "character_ids": ["CHAR_A", "CHAR_B"],
        "continuity": {"eyeline": "CHAR_A 看画右，CHAR_B 看画左"},
    }
    story = {"clips": [clip], "visual_contract": {}, "style_contract": {}}
    old_chars = image_prompt_pack.CHARACTER_DEFS
    try:
        image_prompt_pack.CHARACTER_DEFS = {
            "CHAR_A": {"name": "角色A", "asset_key": "CHAR_A__常态", "form": "常态", "tier": "core"},
            "CHAR_B": {"name": "角色B", "asset_key": "CHAR_B__常态", "form": "常态", "tier": "core"},
        }
        text = image_prompt_pack.shot_prompt_section(tmp_path, ep, 2, clip, {}, story)
    finally:
        image_prompt_pack.CHARACTER_DEFS = old_chars

    assert "**正反打合同**" in text
    assert "AXIS_LOC_HALL_CHAR_A_VS_CHAR_B" in text
    assert "谁的肩" not in text
    assert "正反打合同：" in text


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


def test_character_card_identity_parses_id_first_bible_and_beast_card(tmp_path: Path) -> None:
    woman = """# CHAR_01 姜月初｜角色圣经

- 首集年龄档：十七至二十岁视觉区间。
## 身份 DNA
- 年轻东方女性，鹅蛋脸偏小，长杏眼。
- 高挑纤细、四肢修长。
## 首集妆造
- 发型：长黑发凌乱披散。
- 服装：灰扑扑囚服。
## 禁漂项
- 禁止无来源白发兽角。
"""
    beast = """# BEAST_01 虎山神｜妖魔卡

- 角色定位：开篇首妖。
- 形态：虎头人身，体魄雄壮如小山，黑黄毛发。
- 持续伤势：胸膛有洞穿伤。
"""
    card_dir = tmp_path / "设定库" / "characters"
    card_dir.mkdir(parents=True)
    (card_dir / "姜月初.md").write_text(woman, encoding="utf-8")
    (card_dir / "虎山神.md").write_text(beast, encoding="utf-8")

    defs = image_prompt_pack.derive_character_defs(
        tmp_path, {"clips": [{"character_ids": ["CHAR_01", "BEAST_01"]}]}
    )

    assert defs["CHAR_01"]["name"] == "姜月初"
    assert "鹅蛋脸偏小" in defs["CHAR_01"]["face"]
    assert defs["CHAR_01"]["hair"] == "长黑发凌乱披散。"
    assert defs["CHAR_01"]["outfit"] == "灰扑扑囚服。"
    assert "禁止无来源白发兽角。" in defs["CHAR_01"]["drift"]
    assert defs["BEAST_01"]["name"] == "虎山神"
    assert "虎头人身" in defs["BEAST_01"]["face"]


def test_external_visual_manifest_routes_identity_and_style_separately(tmp_path: Path) -> None:
    visual = tmp_path / "设定库" / "参考资料" / "视觉参考"
    visual.mkdir(parents=True)
    identity_rel = "设定库/参考资料/视觉参考/identity.jpg"
    style_rel = "设定库/参考资料/视觉参考/style.jpg"
    (tmp_path / identity_rel).write_bytes(b"identity")
    (tmp_path / style_rel).write_bytes(b"style")
    (visual / "reference_manifest.json").write_text(json.dumps({
        "references": [
            {
                "path": identity_rel,
                "sha256": hashlib.sha256(b"identity").hexdigest(),
                "use_policy": "identity_body_reference",
                "character_ids": ["CHAR_01"],
                "rights_status": "user_owned",
                "eligible_for_generation": True,
                "backend_upload_allowed": True,
                "watermark_present": False,
            },
            {
                "path": style_rel,
                "sha256": hashlib.sha256(b"style").hexdigest(),
                "use_policy": "style_source_only",
                "character_ids": [],
                "rights_status": "authorized",
                "eligible_for_generation": True,
                "backend_upload_allowed": True,
                "watermark_present": False,
            },
        ]
    }), encoding="utf-8")

    identity = image_prompt_pack.external_visual_reference_entries(tmp_path, "CHAR_01", {"name": "姜月初"})
    styles = image_prompt_pack.external_style_reference_entries(tmp_path)

    assert [row["path"] for row in identity] == [identity_rel]
    assert [row["path"] for row in styles] == [style_rel]


def test_external_visual_manifest_fails_closed_for_unsafe_or_tampered_rows(tmp_path: Path) -> None:
    visual = tmp_path / "设定库" / "参考资料" / "视觉参考"
    visual.mkdir(parents=True)
    rel = "设定库/参考资料/视觉参考/identity.jpg"
    payload = b"identity"
    (tmp_path / rel).write_bytes(payload)
    manifest = visual / "reference_manifest.json"
    valid = {
        "path": rel,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "use_policy": "identity_reference",
        "character_ids": ["CHAR_01"],
        "rights_status": "authorized",
        "eligible_for_generation": True,
        "backend_upload_allowed": True,
        "watermark_present": False,
    }
    unsafe_variants = [
        {"use_policy": "analysis_only"},
        {"status": "pending_rights_review"},
        {"rights_status": "pending"},
        {"watermark_present": True},
        {"has_watermark": True},
        {"eligible_for_generation": False},
        {"backend_upload_allowed": False},
        {"sha256": "0" * 64},
        {"watermark_present": None},
    ]

    for mutation in unsafe_variants:
        row = dict(valid)
        row.update(mutation)
        manifest.write_text(json.dumps({"references": [row]}), encoding="utf-8")
        assert image_prompt_pack.external_visual_reference_entries(
            tmp_path, "CHAR_01", {"name": "姜月初"}
        ) == []


def test_legacy_shared_user_reference_without_manifest_is_not_auto_attached(tmp_path: Path) -> None:
    legacy = tmp_path / "出图" / "共享" / "图片" / "CHAR_01_定型参考.png"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"legacy")

    assert image_prompt_pack.external_visual_reference_entries(
        tmp_path, "CHAR_01", {"name": "姜月初"}
    ) == []


def test_generation_manifest_check_ignores_analysis_only_but_blocks_active_tamper(tmp_path: Path) -> None:
    visual = tmp_path / "设定库" / "参考资料" / "视觉参考"
    visual.mkdir(parents=True)
    rel = "设定库/参考资料/视觉参考/identity.jpg"
    payload = b"identity"
    source = tmp_path / rel
    source.write_bytes(payload)
    active = {
        "id": "active",
        "path": rel,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "use_policy": "identity_reference",
        "character_ids": ["CHAR_01"],
        "rights_status": "authorized",
        "eligible_for_generation": True,
        "backend_upload_allowed": True,
        "watermark_present": False,
    }
    analysis_only = {
        "id": "research",
        "path": rel,
        "use_policy": "analysis_only",
        "rights_status": "pending",
        "watermark_present": True,
    }
    manifest = visual / "reference_manifest.json"
    manifest.write_text(json.dumps({"references": [analysis_only, active]}), encoding="utf-8")

    assert visual_reference_policy.reference_manifest_generation_issues(tmp_path) == []

    source.write_bytes(b"tampered")
    issues = visual_reference_policy.reference_manifest_generation_issues(tmp_path)
    assert "reference[active]:declared_sha256_mismatch" in issues


def test_reference_cards_use_authored_truth_or_production_snapshots_not_top_level_duplicates(tmp_path: Path) -> None:
    chars = tmp_path / "设定库" / "characters"
    locs = tmp_path / "设定库" / "locations"
    chars.mkdir(parents=True)
    locs.mkdir(parents=True)
    (chars / "姜月初.md").write_text("# CHAR_01 姜月初｜角色圣经\n", encoding="utf-8")
    (locs / "荒野尸场.md").write_text("# LOC_01 荒野尸场｜场景卡\n", encoding="utf-8")

    char_rel = image_prompt_pack.character_reference_card_rel(
        tmp_path, "CHAR_01", {"name": "姜月初", "form": "常态"}
    )
    generated_char_rel = image_prompt_pack.character_reference_card_rel(
        tmp_path, "CHAR_99", {"name": "路人", "form": "常态"}
    )
    scene_rel = image_prompt_pack.asset_reference_card_rel(
        tmp_path, "LOC_01", {"name": "夕照荒野尸场", "type": "scene"}
    )
    prop_rel = image_prompt_pack.asset_reference_card_rel(
        tmp_path, "PROP_01", {"name": "断刀", "type": "prop"}
    )

    assert char_rel == "设定库/characters/姜月初.md"
    assert generated_char_rel.startswith("生产数据/卡片快照/角色/")
    assert scene_rel == "设定库/locations/荒野尸场.md"
    assert prop_rel.startswith("生产数据/卡片快照/资产/")
    assert not any(rel.startswith(("角色卡/", "场景卡/", "道具卡/")) for rel in (char_rel, generated_char_rel, scene_rel, prop_rel))


def test_existing_style_anchor_requires_review_and_preserves_approval(tmp_path: Path) -> None:
    rel = image_prompt_pack.style_anchor_path_for(image_prompt_pack.DEFAULT_STYLE)
    path = tmp_path / rel
    path.parent.mkdir(parents=True)
    path.write_bytes(b"png-placeholder")
    story = {"style_contract": {"风格名": image_prompt_pack.DEFAULT_STYLE}}

    pending = image_prompt_pack.style_anchor_registry(tmp_path, story)
    assert pending["selected_anchor"]["status"] == "review_pending"
    current_sha = image_prompt_pack.sha256_file(path)

    registry_path = tmp_path / image_prompt_pack.STYLE_ANCHOR_REGISTRY_REL
    registry_path.write_text(json.dumps({
        "selected_anchor": {
            "path": rel,
            "status": "approved",
            "human_review": {"reviewer": "user", "png_sha256": current_sha},
            "visual_review": {"reviewer": "executor:codex", "png_sha256": current_sha},
        }
    }), encoding="utf-8")
    approved = image_prompt_pack.style_anchor_registry(tmp_path, story)
    assert approved["selected_anchor"]["status"] == "approved"
    assert approved["selected_anchor"]["human_review"]["reviewer"] == "user"
    assert approved["selected_anchor"]["visual_review"]["reviewer"] == "executor:codex"

    path.write_bytes(b"regenerated-anchor")
    stale = image_prompt_pack.style_anchor_registry(tmp_path, story)
    assert "human_review" not in stale["selected_anchor"]
    assert "visual_review" not in stale["selected_anchor"]


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
    assert "No person, face, animal, creature, building, weapon, prop, environment" in style_prompt
    assert "竖屏短剧镜头" not in style_prompt
    assert "不建立具体地点、前中后景、人物调度或动作叙事" in style_prompt
    assert "style_anchor：`出图/共享/图片/风格锚_国漫写实.png`" in overview


def test_style_anchor_does_not_inherit_story_blocking_or_scene_objects() -> None:
    story = {
        "style_contract": {
            "风格名": "水墨志怪",
            "视觉基调": "粗粝纸墨与冷灰光比",
            "镜头与构图": "前景断刀和尸骸、中景具名角色、后景虎妖与城寨纵深",
            "光色策略": "冷灰主光、朱砂与金色点睛",
        }
    }

    prompt = image_prompt_pack.shared_style_anchor_prompt(story)

    assert "前景断刀" not in prompt
    assert "具名角色" not in prompt
    assert "后景虎妖" not in prompt
    assert "城寨纵深" not in prompt
    assert "不要人物、动物/妖物、建筑、兵器、道具、环境景观" in prompt


def test_style_anchor_registry_marks_existing_anchor_review_pending(tmp_path: Path) -> None:
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
    assert selected["status"] == "review_pending"
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
    assert "VFX_道行计数overlay" not in ids
    assert "VFX_官道马蹄火把" not in ids
    assert "LOC_01" in ids
    assert all(" " not in aid and "/" not in aid for aid in ids)
    assert reqs["WEAPON_01"]["name"] == "横刀"


def test_clip_assets_normalize_prose_suffix_against_offscreen_id() -> None:
    clip = {
        "location_id": "LOC_01",
        "object_ids": ["PROP_02"],
        "scene": "VFX_01退出清晰画面，人物不移动。",
        "entity_schedule": {
            "objects": ["PROP_02"],
            "locations": ["LOC_01"],
            "required_presence": ["PROP_02", "LOC_01"],
            "offscreen_presence": ["VFX_01"],
        },
    }

    ids = image_prompt_pack.clip_assets(clip)

    assert ids == ["LOC_01", "PROP_02"]
    assert "VFX_01退出清晰画面" not in ids


def test_clip_assets_do_not_mint_chinese_prose_suffix_as_asset() -> None:
    clip = {
        "object_ids": ["PROP_旧布包", "PROP_01"],
        "continuity": {
            "entry_exit": "PROP_旧布包在上镜后留在杂役院画外；PROP_01仍未入画。",
        },
    }

    assert image_prompt_pack.clip_assets(clip) == ["PROP_旧布包", "PROP_01"]


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


def test_bare_project_asset_ids_fail_closed_without_definition(tmp_path: Path) -> None:
    story = {"clips": [{"object_ids": ["PROP_IRON_BOWL", "PROP_EMPTY_BUCKETS", "PROP_RUST_LOCK"]}]}

    with pytest.raises(image_prompt_pack.PromptPackContractError, match="PROP_IRON_BOWL"):
        image_prompt_pack.derive_asset_defs(tmp_path, story)


def test_unknown_scene_id_fails_closed_without_scene_definition(tmp_path: Path) -> None:
    story = {"clips": [{"location_id": "LOC_UNKNOWN_HALL"}]}

    with pytest.raises(image_prompt_pack.PromptPackContractError, match="LOC_UNKNOWN_HALL"):
        image_prompt_pack.derive_asset_defs(tmp_path, story)


def test_scene_visual_contract_is_scoped_to_matching_location(tmp_path: Path) -> None:
    story = {
        "clips": [{"location_id": "LOC_01"}, {"location_id": "LOC_02"}],
        "asset_materials": {
            "LOC_01": {"name": "一号场景", "type": "scene", "profile": "入口、木台与灰墙"},
            "LOC_02": {"name": "二号场景", "type": "scene", "profile": "水缸、山路与木门"},
        },
        "visual_contract": {
            "场景光位锚": {
                "LOC_01": {"主光方向": "画左高处", "色温": "4800K冷灰"},
                "LOC_02": {"主光方向": "画右后", "色温": "4300K傍晚"},
            },
            "场景轴线视线": {
                "LOC_01": {"轴线": "入口到木台"},
                "LOC_02": {"轴线": "水缸到山路"},
            },
        },
    }

    defs = image_prompt_pack.derive_asset_defs(tmp_path, story)

    assert "画左高处" in defs["LOC_01"]["constraints"]["light_anchor"]
    assert "画右后" not in defs["LOC_01"]["constraints"]["light_anchor"]
    assert "入口到木台" in defs["LOC_01"]["constraints"]["axis_rules"]
    assert "水缸到山路" not in defs["LOC_01"]["constraints"]["axis_rules"]
    assert "画右后" in defs["LOC_02"]["scene_dna"]["color_lighting_weather"]
    assert "画左高处" not in defs["LOC_02"]["scene_dna"]["color_lighting_weather"]


def test_scene_card_resident_subject_id_is_preserved_in_scene_dna(tmp_path: Path) -> None:
    locations = tmp_path / "设定库" / "locations"
    locations.mkdir(parents=True)
    (locations / "荒野尸场.md").write_text(
        """# LOC_01 荒野尸场｜场景卡

- 平面关系：左下逃生通道通往右上巨岩。
- 常驻主体：`BEAST_01/实体_重伤复活`（虎头人身尸体，禁止改成四足虎）。
""",
        encoding="utf-8",
    )
    story = {"clips": [{"location_id": "LOC_01"}]}

    defs = image_prompt_pack.derive_asset_defs(tmp_path, story)
    residents = "；".join(defs["LOC_01"]["scene_dna"]["resident_assets"])

    assert "BEAST_01/实体_重伤复活" in residents
    assert "禁止改成四足虎" in residents


def test_registry_rebuild_preserves_rejected_status_and_review_for_same_path() -> None:
    path = "出图/共享/图片/定妆_场景_荒野.png"
    new = {"path": path, "status": "planned", "human_review": {"status": "pending"}}
    old = {
        "path": path,
        "status": "rejected",
        "human_review": {"status": "rejected", "reason": "常驻妖物物种漂移"},
    }

    merged = image_prompt_pack.preserve_registry_evidence(new, old)

    assert merged["status"] == "rejected"
    assert merged["human_review"]["status"] == "rejected"
    assert merged["human_review"]["reason"] == "常驻妖物物种漂移"


def test_registry_rebuild_preserves_generated_at_when_semantics_match(tmp_path: Path) -> None:
    rel = Path("出图/共享/identity_registry.json")
    path = tmp_path / rel
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "kind": "n2d_identity_registry",
        "generated_at": "2026-07-14T00:00:00+00:00",
        "characters": [],
    }), encoding="utf-8")

    merged = image_prompt_pack.merge_existing_registry_evidence(tmp_path, rel, {
        "kind": "n2d_identity_registry",
        "generated_at": "2026-07-15T00:00:00+00:00",
        "characters": [],
    })

    assert merged["generated_at"] == "2026-07-14T00:00:00+00:00"


def test_registry_rebuild_advances_generated_at_when_semantics_change(tmp_path: Path) -> None:
    rel = Path("出图/共享/identity_registry.json")
    path = tmp_path / rel
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "kind": "n2d_identity_registry",
        "generated_at": "2026-07-14T00:00:00+00:00",
        "characters": [],
    }), encoding="utf-8")

    merged = image_prompt_pack.merge_existing_registry_evidence(tmp_path, rel, {
        "kind": "n2d_identity_registry",
        "generated_at": "2026-07-15T00:00:00+00:00",
        "characters": [{"id": "CHAR_01"}],
    })

    assert merged["generated_at"] == "2026-07-15T00:00:00+00:00"


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
    assert "无脸人台或折叠衣物尺度参考" not in asset_prompt
    assert "继承冷灰夜路光位" not in asset_prompt
    assert "中性浅灰干净背景" in asset_prompt
    assert "资产参考图默认不生成未绑定身份的清晰人物脸" in asset_prompt
    scene_asset = next(item for item in registry["assets"] if item["id"] == "LOC_TEST")
    signature = scene_asset["constraints"]["lighting_signature"]
    assert signature["color_temperature"] == "mixed_cool_warm"
    assert signature["key_light_direction"] == "right"
    assert "mean_hue" not in signature
    assert signature["numeric_measurement"] == "pending_after_landed_frame_qc"


def test_scene_primary_does_not_impersonate_reverse_or_floor_plan(tmp_path: Path) -> None:
    old_defs = image_prompt_pack.ASSET_DEFS
    image_dir = tmp_path / "出图" / "共享" / "图片"
    image_dir.mkdir(parents=True)
    (image_dir / "定妆_场景_县衙案厅.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    try:
        image_prompt_pack.ASSET_DEFS = {
            "LOC_TEST": {
                "type": "scene",
                "name": "县衙案厅",
                "path_name": "定妆_场景_县衙案厅",
                "positive": "地方县衙内厅",
                "negative": "现代物件",
                "constraints": {},
            }
        }
        registry = image_prompt_pack.build_asset_registry(tmp_path)
    finally:
        image_prompt_pack.ASSET_DEFS = old_defs

    scene = registry["assets"][0]
    assert scene["reference_group"]["primary"]["status"] == "ready"
    assert scene["reference_group"]["reverse"]["status"] == "planned"
    assert scene["reference_group"]["reverse"]["path"].endswith("_反打.png")
    assert scene["reference_group"]["floor_plan"]["status"] == "planned"
    assert scene["reference_group"]["floor_plan"]["path"].endswith("_平面图.png")
    assert scene["scene_atlas"]["base_views"]["back"]["status"] == "planned"


def test_magic_prop_keeps_weapon_profile_in_asset_registry(tmp_path: Path) -> None:
    story = {
        "episode": 2,
        "clips": [{"object_ids": ["PROP_HEI_TAO_PEN"]}],
        "asset_requirements": [{
            "asset_id": "PROP_HEI_TAO_PEN", "type": "weapon", "name": "黑陶盆",
            "profile": "可作防御法器的黑陶盆，结构固定",
        }],
    }
    old_defs = image_prompt_pack.ASSET_DEFS
    try:
        image_prompt_pack.ASSET_DEFS = image_prompt_pack.derive_asset_defs(tmp_path, story)
        registry = image_prompt_pack.build_asset_registry(tmp_path)
    finally:
        image_prompt_pack.ASSET_DEFS = old_defs

    asset = next(item for item in registry["assets"] if item["id"] == "PROP_HEI_TAO_PEN")

    assert asset["owner"] == "剧情资产"
    assert asset["weapon_profile"]["combat_usage"]
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


def test_named_minimal_uses_distinct_face_anchor_for_neutral_expression(tmp_path: Path) -> None:
    cfg = {
        "asset_key": "CHAR_MINIMAL__常态",
        "name": "短线角色",
        "form": "常态",
        "library_tier": "named_minimal",
    }

    rg, atlas = image_prompt_pack.full_reference_group(tmp_path, "CHAR_MINIMAL", cfg)

    face_anchor = rg["face_anchor_refs"][0]
    expression = rg["expressions"][0]
    assert expression["emotion"] == "基础"
    assert expression["path"] == face_anchor["path"]
    assert expression["path"].endswith("_脸部特写_脸锚裁切.png")
    assert expression["path"] != rg["front"]["path"]
    assert atlas["expression_refs"][0]["path"] == expression["path"]


def test_core_reference_group_marks_new_turnaround_as_five_angle_board(tmp_path: Path) -> None:
    cfg = {
        "asset_key": "CHAR_CORE__常态",
        "name": "核心角色",
        "form": "常态",
        "library_tier": "core_full",
    }

    rg, _ = image_prompt_pack.full_reference_group(tmp_path, "CHAR_CORE", cfg)

    turnaround = rg["turnaround"]
    assert turnaround["status"] == "planned"
    assert turnaround["layout"] == "five_angle_v1"
    assert turnaround["column_count"] == 5
    assert turnaround["view_order"] == [
        "front", "three_quarter", "side", "rear_three_quarter", "back",
    ]
    assert "rear_three_quarter" in rg
    expression = rg["expressions"][0]
    assert expression["path"].endswith("_表情_六联表.png")
    assert expression["status"] == "planned"
    assert expression["layout"] == "two_by_three_expression_sheet_v1"
    assert expression["derivation"]["method"] == "controlled_multiref_generation"
    assert expression["path"] != rg["front"]["path"]


def test_recurring_reference_group_registers_on_demand_rear_three_quarter_slot(tmp_path: Path) -> None:
    cfg = {
        "asset_key": "CHAR_STANDARD__常态",
        "name": "复现配角",
        "form": "常态",
        "library_tier": "recurring_standard",
    }

    rg, atlas = image_prompt_pack.full_reference_group(tmp_path, "CHAR_STANDARD", cfg)

    assert rg["rear_three_quarter"]["status"] == "planned"
    assert rg["rear_three_quarter"]["path"].endswith("_后45度.png")
    assert atlas["base_views"]["rear_three_quarter"] == rg["rear_three_quarter"]


def test_named_minimal_reference_group_registers_on_demand_angle_slots(tmp_path: Path) -> None:
    cfg = {
        "asset_key": "CHAR_MINIMAL__常态",
        "name": "短线具名角色",
        "form": "常态",
        "library_tier": "named_minimal",
    }

    rg, atlas = image_prompt_pack.full_reference_group(tmp_path, "CHAR_MINIMAL", cfg)

    for field, suffix in {
        "three_quarter": "_45度.png",
        "side": "_侧.png",
        "rear_three_quarter": "_后45度.png",
        "back": "_背.png",
    }.items():
        assert rg[field]["status"] == "planned"
        assert rg[field]["path"].endswith(suffix)
        assert atlas["base_views"][field] == rg[field]


def test_core_reference_group_marks_unlabelled_existing_turnaround_as_unknown(tmp_path: Path) -> None:
    path = tmp_path / "出图" / "共享" / "图片" / "定妆_CHAR_CORE__常态_三视图.png"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"legacy-four-column-board")
    cfg = {
        "asset_key": "CHAR_CORE__常态",
        "name": "核心角色",
        "form": "常态",
        "library_tier": "core_full",
    }

    rg, _ = image_prompt_pack.full_reference_group(tmp_path, "CHAR_CORE", cfg)

    turnaround = rg["turnaround"]
    assert turnaround["status"] == "ready"
    assert turnaround["layout"] == "unknown_existing"
    assert "column_count" not in turnaround
    assert "view_order" not in turnaround


def test_registry_rebuild_preserves_explicit_five_angle_turnaround_layout() -> None:
    path = "出图/共享/图片/定妆_CHAR_CORE__常态_三视图.png"
    new = {"path": path, "status": "ready", "layout": "unknown_existing"}
    old = {
        "path": path,
        "status": "ready",
        "layout": "five_angle_v1",
        "column_count": 5,
        "view_order": ["front", "three_quarter", "side", "rear_three_quarter", "back"],
    }

    merged = image_prompt_pack.preserve_registry_evidence(new, old)

    assert merged["layout"] == "five_angle_v1"
    assert merged["column_count"] == 5
    assert merged["view_order"] == old["view_order"]


def test_registry_rebuild_preserves_actual_generated_derivation() -> None:
    new = {
        "path": "出图/共享/图片/定妆_CHAR_02__常态_后45度.png",
        "status": "ready",
        "derivation": {
            "method": "controlled_multiref_generation",
            "source_path": "出图/共享/图片/定妆_CHAR_02__常态.png",
            "crop_box": [0, 0, 1, 1],
        },
    }
    old = {
        **new,
        "derivation": {
            "method": "controlled_multiref_generation",
            "source_path": "生产数据/reference_enhanced/第1集/定妆_CHAR_02.png",
            "source_sha256": "abc123",
            "crop_box": [0, 0, 1024, 1819],
            "generated_by": "skills/n2d/n2d-image/scripts/codex_image_runner.py",
            "reference_inputs": [{"rel_path": "出图/共享/图片/定妆_CHAR_02__常态.png"}],
        },
    }

    merged = image_prompt_pack.preserve_registry_evidence(new, old)

    assert merged["derivation"] == old["derivation"]


def test_clip_assets_do_not_bind_plain_alias_from_prose() -> None:
    clip = {
        "description": "姜月初想起百妖谱规则，但本镜不出现面板。",
        "object_ids": ["WEAPON_01 横刀"],
    }

    assert image_prompt_pack.clip_assets(clip) == ["WEAPON_01"]


def test_planned_episode_count_honors_explicit_library_tier() -> None:
    assert image_prompt_pack.planned_episode_count(
        "- 计划出场集数：前期多集复现（recurring_standard）", {}, "杂役班长"
    ) == 3
    assert image_prompt_pack.planned_episode_count(
        "- 计划出场集数：长线（core_full）", {}, "主角"
    ) == 10


def test_material_character_map_reads_heading_sections(tmp_path: Path) -> None:
    ep_dir = tmp_path / "脚本" / "第1集"
    ep_dir.mkdir(parents=True)
    (ep_dir / "素材清单.md").write_text(
        "### GROUP_01 杂役背景组\n\n"
        "中文 Prompt：三至五名粗布杂役远后景，脸部不清晰。\n",
        encoding="utf-8",
    )
    rows = image_prompt_pack.material_character_map(
        tmp_path, {"episode": "第1集"}
    )

    assert rows["GROUP_01"]["name"] == "杂役背景组"
    assert "三至五名" in rows["GROUP_01"]["profile"]


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


def test_end_anchor_generation_respects_explicit_seam_taxonomy() -> None:
    assert image_prompt_pack.continuity_needs_end_anchor({
        "continuity": {"seam_mode": "continuous_take_relay"},
    }) is True
    assert image_prompt_pack.continuity_needs_end_anchor({
        "continuity": {"seam_mode": "hard_cut", "need_endframe": True},
    }) is False
    assert image_prompt_pack.continuity_needs_end_anchor({
        "continuity": {"seam_mode": "hard_cut", "end_anchor_required": True},
    }) is True
    assert image_prompt_pack.continuity_needs_end_anchor({"continuity": {}}) is False


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

    old = image_prompt_pack.CHARACTER_DEFS
    image_prompt_pack.CHARACTER_DEFS = {
        "CHAR_SHEN_YAN": {
            "name": "沈砚", "form": "常态", "tier": "core", "asset_key": "CHAR_SHEN_YAN__常态",
            "anchor": "清瘦青年录事", "face": "稳定脸型", "hair": "束发", "outfit": "项目定义服装",
            "accessories": "无", "relative_scale": "标准体量",
        }
    }
    try:
        text = image_prompt_pack.shot_prompt_section(tmp_path, "第1集", 1, clip, {}, {"clips": [clip]})
    finally:
        image_prompt_pack.CHARACTER_DEFS = old

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
    assert "导演意图服务本镜戏剧功能" in text


def test_nonfinal_nonrelay_does_not_need_endframe_exemption(tmp_path: Path) -> None:
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

    assert "这不是豁免" in text
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
    assert "副手/后手必须空手" in directive
    assert "不得生成副刀、短刃、匕首、第二把实体武器" in directive


def test_weapon01_contract_forbids_offhand_secondary_blade(tmp_path: Path) -> None:
    clip = {
        "id": "EP05_CLIP03",
        "description": "姜月初横刀前压，后手护身。",
        "object_ids": ["WEAPON_01"],
    }
    story = {"clips": [clip], "visual_contract": {}, "style_contract": {}}
    story["asset_requirements"] = [{
        "asset_id": "WEAPON_01", "type": "weapon", "name": "项目横刀",
        "profile": "一柄暗银直身单刃横刀",
    }]

    defs = image_prompt_pack.derive_asset_defs(tmp_path, story)
    terms = defs["WEAPON_01"]["constraints"]["must_not_have"]

    assert "副刀" in terms
    assert "短刃" in terms
    assert "匕首" in terms
    assert "副手持刀" in terms

    old_assets = image_prompt_pack.ASSET_DEFS
    try:
        image_prompt_pack.ASSET_DEFS = defs
        lock_line = image_prompt_pack.asset_topology_lock_line(["WEAPON_01"])
    finally:
        image_prompt_pack.ASSET_DEFS = old_assets

    assert "weapon_count=1" in lock_line
    assert "副手/后手不得出现短刃、匕首、副刀或第二把刀" in lock_line
    assert "刀光/光轨/残影只能是半透明运动轨迹" in lock_line


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


def test_face_visibility_keeps_main_face_when_only_nonfocus_target_is_silhouette() -> None:
    directive = image_prompt_pack.face_visibility_directive(
        ["CHAR_01", "CHAR_05"],
        "MS 起刀 → OTS 反派惊惧 → WS 刀光落点",
        "肉盾狼妖以剪影/血尘被劈开。",
    )

    assert "眼鼻嘴三角区清晰" in directive
    assert "非焦点群演、肉盾、远景剪影可无脸处理" in directive
    assert "本镜人物只允许背身" not in directive


def test_existing_asset_bundle_creates_missing_sections(tmp_path: Path) -> None:
    cfg = {
        "name": "姜月初",
        "scope": "主角",
        "asset_bundle": {
            "manifest": "角色库/CHAR_01__姜月初/manifest.json",
            "package_dir": "角色库/CHAR_01__姜月初",
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
            "- 身份：核心主角/全篇长线；二十一世纪现代人穿越者。",
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


def test_derive_character_defs_only_emits_entities_required_by_current_story(tmp_path: Path) -> None:
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
    assert "CHAR_BETA" not in defs


def test_derive_character_defs_collapses_legacy_id_alias_by_material_name(tmp_path: Path) -> None:
    card_dir = tmp_path / "设定库" / "characters"
    card_dir.mkdir(parents=True)
    (card_dir / "武松.md").write_text(
        "\n".join([
            "# 角色卡 — 武松（ID: CHAR_WU_SONG）",
            "- 身份：都头。",
            "- 固定外貌：方颌浓眉。",
            "- 固定服装：深靛都头服。",
            "- **锚点句**：方颌浓眉·深靛都头服",
        ]),
        encoding="utf-8",
    )
    material = tmp_path / "脚本" / "第1集" / "素材清单.md"
    material.parent.mkdir(parents=True)
    material.write_text(
        "### CHAR_WUSONG 武松 @ 都头态\n\n中文 Prompt：方颌浓眉的都头。\n",
        encoding="utf-8",
    )
    story = {"episode": "第1集", "clips": [{"character_ids": ["CHAR_WUSONG/都头态"]}]}

    defs = image_prompt_pack.derive_character_defs(tmp_path, story)

    assert "CHAR_WUSONG" in defs
    assert "CHAR_WU_SONG" not in defs
    assert defs["CHAR_WUSONG"]["name"] == "武松"
    assert "方颌浓眉" in defs["CHAR_WUSONG"]["face"]


def test_derive_character_defs_keeps_beast_out_of_human_costume_fallback(tmp_path: Path) -> None:
    material = tmp_path / "脚本" / "第1集" / "素材清单.md"
    material.parent.mkdir(parents=True)
    material.write_text(
        "### BEAST_TIGER 猛虎 @ 扑击态\n\n中文 Prompt：吊睛白额猛虎扑击。\n",
        encoding="utf-8",
    )
    story = {"episode": "第1集", "clips": [{"character_ids": ["BEAST_TIGER/扑击态"]}]}

    defs = image_prompt_pack.derive_character_defs(tmp_path, story)
    tiger = defs["BEAST_TIGER"]
    rendered = json.dumps(tiger, ensure_ascii=False)

    assert any(token in tiger["face"] for token in ("猛虎", "虎首", "非人"))
    assert "成年古装角色" not in rendered
    assert "古装衣袍" not in tiger["outfit"]
    assert "铠甲" not in tiger["outfit"]


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


def test_state_lock_uses_clip_form_hint_across_cold_open_time_jump() -> None:
    story = {
        "visual_contract": {
            "角色状态演进": {
                "CHAR_01": "囚途残损无血→面颊血污→杀裴后人血增加",
                "CHAR_04": "贯穿伤伪死→带伤复生→扑击",
            }
        },
        "clips": [
            {"character_ids": ["CHAR_01/囚途残损态", "CHAR_04/复生态焦外"]},
            {"character_ids": ["CHAR_01/囚途残损态", "CHAR_04/伪死态"]},
        ],
    }

    cold_open = image_prompt_pack.state_lock_line(story, ["CHAR_01", "CHAR_04"], 1)
    ten_minutes_earlier = image_prompt_pack.state_lock_line(story, ["CHAR_01", "CHAR_04"], 2)

    assert "`CHAR_04`: 带伤复生。" in cold_open
    assert "`CHAR_01`: 囚途残损无血。" in ten_minutes_earlier
    assert "`CHAR_04`: 贯穿伤伪死。" in ten_minutes_earlier
    assert "面颊血污" not in ten_minutes_earlier
    assert "带伤复生" not in ten_minutes_earlier


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


def test_write_consumed_contracts_receipt_records_image_prompt_inputs(tmp_path: Path) -> None:
    ep = "第1集"
    files = {
        f"脚本/{ep}/storyboard.json": {"clips": [{"id": "Clip_01"}]},
        f"脚本/{ep}/continuity_chain.json": {"kind": "n2d_continuity_chain", "seams": []},
        f"脚本/{ep}/shot_reverse_contract.json": {"kind": "n2d_shot_reverse_contract", "patterns": []},
        f"生产数据/script_quality_contract_{ep}.json": {"kind": "n2d_script_quality_contract"},
        f"生产数据/director_camera_plan_{ep}.json": {"kind": "n2d_director_camera_plan"},
        f"生产数据/reference_plan_{ep}.json": {"kind": "n2d_reference_plan"},
        f"出图/{ep}/prompt/00_总览.md": "# overview\n",
        f"出图/{ep}/prompt/01_分镜出图.md": "# shots\n",
    }
    for rel, payload in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    receipt = image_prompt_pack.write_consumed_contracts_receipt(tmp_path, ep)
    data = json.loads(receipt.read_text(encoding="utf-8"))

    assert data["kind"] == "n2d_prompt_consumed_contracts"
    assert data["scope"] == "image_prompt"
    assert {row["name"] for row in data["contracts"]} == {
        "storyboard",
        "continuity_chain",
        "shot_reverse_contract",
        "script_quality_contract",
        "director_camera_plan",
        "reference_plan",
    }
    assert all(row["exists"] and row["sha256"] for row in data["contracts"])
    assert all(row["exists"] and row["sha256"] for row in data["prompt_files"])
    assert data["input_fingerprint"]["kind"] == "n2d_content_fingerprint"
    assert data["input_fingerprint"]["sha256"]

    (tmp_path / "_设置.md").write_text("- 基础视觉风格: 水墨\n", encoding="utf-8")
    registry = tmp_path / "出图" / "共享" / "identity_registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text('{"kind":"n2d_identity_registry","version":1,"characters":[]}', encoding="utf-8")
    changed = json.loads(image_prompt_pack.write_consumed_contracts_receipt(tmp_path, ep).read_text(encoding="utf-8"))
    assert changed["input_fingerprint"]["sha256"] != data["input_fingerprint"]["sha256"]
    assert "_设置.md" in changed["input_fingerprint"]["source_patterns"]
    assert "出图/共享/identity_registry.json" in changed["input_fingerprint"]["source_patterns"]


def test_future_asset_guard_inherits_hidden_asset_forbidden_terms() -> None:
    original_assets = image_prompt_pack.ASSET_DEFS
    try:
        image_prompt_pack.ASSET_DEFS = {
            "VFX_FUTURE": {
                "type": "vfx",
                "name": "未来虎影",
                "constraints": {
                    "reveal_min_clip": 6,
                    "pre_reveal_policy": "Clip06 前只能画外伏笔。",
                    "reveal_terms": ["血虎", "虎影"],
                    "must_not_have": ["随机改色", "遮挡主体脸"],
                },
                "drift": ["不要现代科幻UI"],
            }
        }

        line = image_prompt_pack.future_asset_guard_line(["VFX_FUTURE"], 2)
    finally:
        image_prompt_pack.ASSET_DEFS = original_assets

    assert "Clip02 禁用未到显现时机资产" in line
    assert "血虎" in line
    assert "随机改色" in line
    assert "遮挡主体脸" in line
    assert "不要现代科幻UI" in line


def test_clip_chars_normalizes_episode_state_to_registry_base_id() -> None:
    clip = {
        "character_ids": [
            "CHAR_01/囚途残损态",
            "CHAR_02/濒死态",
            "CHAR_01/囚途染血态",
        ]
    }

    assert image_prompt_pack.clip_chars(clip) == ["CHAR_01", "CHAR_02"]


# ── 身份哈希 seed：同 (身份ID, 形态) 恒定，与角色排序/位置无关（fixed_pool 承诺兑现）──


def test_identity_seed_base_stable_and_order_independent() -> None:
    a1 = image_prompt_pack.identity_seed_base("CHAR_01", "常态")
    a2 = image_prompt_pack.identity_seed_base("CHAR_01", "常态")
    assert a1 == a2, "同身份+形态必须恒定"
    assert image_prompt_pack.identity_seed_base("CHAR_02", "常态") != a1
    assert image_prompt_pack.identity_seed_base("CHAR_01", "战损") != a1


def test_identity_seed_base_range_leaves_pool_headroom() -> None:
    for cid in ("CHAR_01", "CHAR_99", "PROP_横刀", "SCENE_虎山"):
        base = image_prompt_pack.identity_seed_base(cid, "常态")
        assert 10_000 <= base < 2**31 - 100
        ctrl = image_prompt_pack.generation_control(base)
        assert ctrl["seed_pool"] == [base + i for i in range(6)]
        assert all(0 < s < 2**31 for s in ctrl["seed_pool"])
        assert ctrl["usage"]["turnaround"] == base
