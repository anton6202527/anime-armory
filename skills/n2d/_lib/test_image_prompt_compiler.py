from __future__ import annotations

import hashlib
import json
from pathlib import Path

from image_prompt_compiler import (
    KIND,
    PROFILE_VERSION,
    compile_image_prompt,
    compile_image_section,
    contract_from_section,
    infer_task_type,
    lint_compiled_prompt,
    lint_compiled_section,
    parse_compiled_markdown,
    render_compiled_markdown,
)


def test_task_inference_does_not_misclassify_character_that_mentions_style_anchor():
    section = """## 姜月初（`CHAR_01/常态`）
**资产身份注册层**：CHAR_01；继承 STYLE_ANCHOR，不得风格漂移。
"""

    assert infer_task_type(
        section,
        mode="shared",
        target_path="出图/共享/图片/定妆_CHAR_01__常态.png",
    ) == "character_catalog"
    assert infer_task_type(
        "## 统一风格锚\nSTYLE_ANCHOR",
        mode="shared",
        target_path="出图/共享/图片/风格锚_暗黑盛唐.png",
    ) == "style_anchor"
    assert infer_task_type(
        "## 虎山神（`BEAST_01/实体_重伤复活`）",
        mode="shared",
        target_path="出图/共享/图片/定妆_BEAST_01__实体_重伤复活.png",
    ) == "character_catalog"
    assert infer_task_type(
        "## 夕照荒野尸场（`LOC_01`）\n常驻主体：`BEAST_01/实体_重伤复活`",
        mode="shared",
        target_path="出图/共享/图片/定妆_场景_夕照荒野尸场.png",
    ) == "scene_asset"


def test_task_inference_keeps_weapon_prop_when_contract_mentions_location_light():
    section = """## 横刀（`WEAPON_01`）
大唐镇魔司制式横刀，单把单刃。
光位继承：LOC_01 低位夕阳从画左后侧逆光。
"""

    assert infer_task_type(
        section,
        mode="shared",
        target_path="出图/共享/图片/定妆_武器_横刀.png",
    ) == "prop_asset"

    payload = compile_image_section(
        section.replace(
            "大唐镇魔司制式横刀，单把单刃。",
            "### 正向 prompt（中文）\n大唐镇魔司制式横刀，暗银直身刀刃，单把单刃；中性浅灰背景，无人、无手、无脸。\n### 负向 prompt\n双持、第二把刀、水印",
        ),
        backend="codex",
        model="GPT Image 2",
        channel="Codex CLI",
        mode="shared",
        target_path="出图/共享/图片/定妆_武器_横刀.png",
        style="暗黑盛唐写实国漫",
        aspect_ratio="9:16",
    )
    assert payload["task_type"] == "prop_asset"
    assert "暗银直身刀刃" in payload["prompt"]
    assert "中性浅灰背景" in payload["prompt"]
    assert "可见手部归属" not in payload["prompt"]


def test_style_anchor_compiler_prioritizes_abstract_control_asset_isolation():
    section = """## STYLE_ANCHOR / 黑赤镇魔·水墨妖谱
### 正向 prompt（中文）
粗粝唐代边塞与写实国漫人物只作为下游适用语境。竖幅分区式视觉语言样板；仅展示抽象色卡、光比阶梯、线条笔触与近裁材质样本；不要人物、动物、妖物、建筑、兵器、道具、环境、文字或剧情动作。
### 负向 prompt
白衣仙女、正式制服提前出现、常态红发金瞳虎纹、巨型毛笔武器、金甲符牌、网红脸、虎妖萌宠化、猎奇伤口、烤字、水印Logo；人物、动物、妖物、建筑、兵器、道具、环境景观、剧情动作、文字、水印、logo。
"""

    payload = compile_image_section(
        section,
        backend="codex",
        model="GPT Image 2",
        channel="Codex CLI",
        mode="shared",
        target_path="出图/共享/图片/风格锚_黑赤镇魔水墨妖谱.png",
        style="黑赤镇魔·水墨妖谱",
        aspect_ratio="9:16",
    )

    prompt = payload["prompt"]
    assert payload["task_type"] == "style_anchor"
    assert "抽象分区式视觉语言样板" in prompt
    assert "色卡、明暗/光比阶梯、线条笔触" in prompt
    assert "人物或清晰人脸" in prompt
    assert "建筑或城寨或具体环境景观" in prompt
    assert "卷轴或地图或书页或可读文字或伪造文字" in prompt


def _contract(**overrides):
    data = {
        "task_type": "shot_keyframe",
        "backend": "openai",
        "model": "gpt-image-2",
        "mode": "image_reference",
        "objective": "她在尸骸间惊醒，观众立即读出生死危机",
        "subject": "冷静少女，黑色半散长发，灰褐囚服",
        "composition": "低机位中近景，少女位于画左，视线看向画右虎妖",
        "action": "她一手撑地抬眼，另一手收在胸前",
        "scene": "冷青灰荒野尸场，枯草与低雾",
        "lighting": "画左上冷月散射光，主脸可读",
        "mood": "惊惧压住，身体准备后撤",
        "style": "水墨国风，宣纸肌理，淡彩点染",
        "preserve": ["同一张脸、同一囚服", "场景轴线和冷月光位"],
        "exclude": ["不要文字", "禁止水印", "额外手、断手", "欧美卡通脸"],
        "risk_flags": ["hands", "grounding"],
        "reference_inputs": [
            {"role": "identity", "owner": "CHAR_01", "path": "face.png", "sha256": "a" * 64},
            {"role": "scene", "owner": "LOC_01", "path": "scene.png", "sha256": "b" * 64},
        ],
        "request_params": {"aspect_ratio": "16:9", "size": "1536x1024", "quality": "high"},
    }
    data.update(overrides)
    return data


def test_openai_compiler_keeps_contract_out_of_submit_prompt():
    payload = compile_image_prompt(_contract())

    assert payload["kind"] == KIND
    assert payload["profile"] == "openai_gpt_image_natural_brief"
    assert "动作瞬间：" in payload["prompt"]
    assert "图1作为CHAR_01的identity参考" in payload["prompt"]
    assert "identity_registry" not in payload["prompt"]
    assert "重抽预算" not in payload["prompt"]
    assert "9:16" not in payload["prompt"]
    assert payload["request_params"]["aspect_ratio"] == "16:9"
    assert payload["negative_prompt"] == ""
    assert payload["lint"]["errors"] == []


def test_section_compiler_strips_embedded_production_contract_heading() -> None:
    section = """## 镜头 1
**目标落档**：`出图/第1集/图片/EP01_CLIP01.png`
**剧本描述**：少女从尸场抬眼，手握横刀。
**导演意图**：大表情近景；必须服务剧本可看性合同：先展示不可逆选择，再回到选择前。
**资产身份注册层**：`CHAR_01/常态`。
**多人同框身份槽位**：无。
### 正向 prompt（中文）
身份保持：CHAR_01/常态。
镜头构图：低机位中近景。
动作瞬间：少女抬眼握刀。
场景光影：冷灰荒野侧逆光。
情绪张力：痛苦但已决定。
画风规格：写实国漫。
### 负向 prompt
文字、水印。
"""

    payload = compile_image_section(
        section,
        backend="codex",
        model="GPT Image 2",
        channel="Codex CLI",
        mode="firstframe",
        target_path="出图/第1集/图片/EP01_CLIP01.png",
        aspect_ratio="9:16",
    )

    assert "剧本可看性合同" not in payload["prompt"]
    assert "submit_prompt_leaks_full_production_contract" not in payload["lint"]["errors"]


def test_flux_compiler_is_positive_only():
    payload = compile_image_prompt(_contract(backend="FLUX.2", model="flux-2-pro"))

    assert payload["negative_strategy"] == "positive_only"
    assert payload["negative_prompt"] == ""
    assert "不要" not in payload["prompt"]
    assert "禁止" not in payload["prompt"]
    assert lint_compiled_prompt(payload)["errors"] == []


def test_conflict_resolution_compresses_repeats_and_rewrites_positive_only_guards():
    payload = compile_image_prompt(_contract(
        backend="flux",
        composition="低机位中景，画幅9:16",
        style="水墨国风，9:16 竖版",
        preserve=["保持场景轴线与冷月光位", "必须保持场景轴线与冷月光位完全一致"],
        policy_guards=[
            "武器入体/接触点铁律：只能有一个明确接触点；禁止出现第二处伤口",
            "本镜已指定胸口/胸前：不得画成腹部、腰部或肩部入刀",
        ],
    ), "flux")

    assert "9:16" not in payload["prompt"]
    assert "exactly one coherent weapon contact" in payload["prompt"]
    assert "upper chest" in payload["prompt"]
    assert "禁止" not in payload["prompt"] and "不得" not in payload["prompt"]
    assert "request_params.aspect_ratio_overrode_composition" in payload["compiler_decisions"]
    assert "request_params.aspect_ratio_overrode_style" in payload["compiler_decisions"]
    assert "repeated_constraints_compressed" in payload["compiler_decisions"]
    assert payload["metrics"]["constraint_compression"]["preserve_output"] == 1
    assert payload["lint"]["errors"] == []


def test_catalog_profile_drops_story_action_without_mutating_source_contract():
    payload = compile_image_prompt(_contract(task_type="character_catalog"))

    assert "动作瞬间：" not in payload["prompt"]
    assert "neutral_catalog_dropped_story_action" in payload["compiler_decisions"]


def test_character_catalog_compiles_makeup_identity_wardrobe_and_reference_boundary():
    section = """## 姜月初（`CHAR_01/常态`）
### 定妆图提交口径
```text
角色身份：CHAR_01/常态；姜月初，年轻东方女性；
年龄/年龄档：十七至二十岁；
固定外貌：鹅蛋脸偏小，长杏眼，长黑发凌乱披散；
服装妆造：灰扑扑粗布囚服，无配饰，无发冠；
定妆要求：中性灰棚拍背景，全身从头到鞋完整；
禁止：黑金铠甲、红裘、金色肩甲、高马尾、华丽发冠；
```
### 正向 prompt（中文）
姜月初角色参考板。
### 负向 prompt
不要文字、水印。
"""
    payload = compile_image_section(
        section,
        backend="codex",
        model="GPT Image 2",
        mode="shared",
        task_type="character_catalog",
        target_path="出图/共享/图片/定妆_CHAR_01__常态.png",
        style="暗黑盛唐写实国漫",
        aspect_ratio="9:16",
        policy_guards=["用户提供的人物/主角参考图默认只作身份与身形锚，不继承参考图衣装"],
    )

    assert "鹅蛋脸偏小" in payload["prompt"]
    assert "灰扑扑粗布囚服" in payload["prompt"]
    assert "中性灰棚拍背景" in payload["prompt"]
    assert "不继承参考图衣装" in payload["prompt"]
    assert "黑金铠甲" in payload["prompt"]


def test_turnaround_catalog_forces_wide_plate_and_drops_story_camera_guards():
    section = """## 姜月初五角 turnaround（`CHAR_01/常态`）
### 定妆图提交口径
```text
角色身份：CHAR_01/常态；姜月初；
固定外貌：乌黑高马尾；
服装妆造：玄黑赤纹窄袖劲装；
定妆要求：正面、前3/4、侧面、后3/4、背面五角同框，全身头脚完整；
```
### 正向 prompt（中文）
五角技术设定板。
"""
    payload = compile_image_section(
        section,
        backend="codex",
        model="GPT Image 2",
        mode="shared",
        task_type="character_catalog",
        target_path="出图/共享/图片/定妆_CHAR_01__常态_三视图.png",
        aspect_ratio="9:16",
        policy_guards=[
            "镜头为旁观者视角：角色不看镜头",
            "武器入体/接触点铁律：只能有一个入体点",
            "共享角色定妆使用统一规格的定妆参考板",
        ],
    )

    assert payload["request_params"]["aspect_ratio"] == "16:9"
    assert "旁观者视角" not in payload["prompt"]
    assert "武器入体" not in payload["prompt"]
    assert "共享角色定妆" in payload["prompt"]


def test_scene_asset_keeps_unlabelled_scene_dna_landmarks_axis_and_light():
    section = """## 夕照荒野尸场（`LOC_01`）
### 正向 prompt（中文）
夕照荒野尸场；地貌：陇右风沙荒野、枯草、碎石、无村落；稳定地标：画右上巨岩与远端虎妖尸体；空间轴线：画左下南向逃生通道连接画右上巨岩；光位：低位夕阳从画左后侧逆光，环境冷灰土褐；纯场景，不出现具名角色清晰脸。
### 负向 prompt
禁止现代物件、建筑、竹林、雪山、仙宫、文字和水印。
"""
    payload = compile_image_section(
        section,
        backend="codex",
        model="GPT Image 2",
        mode="shared",
        task_type="scene_asset",
        target_path="出图/共享/图片/定妆_场景_夕照荒野尸场.png",
        style="暗黑盛唐写实国漫",
        aspect_ratio="9:16",
    )

    assert "画右上巨岩" in payload["prompt"]
    assert "远端虎妖尸体" in payload["prompt"]
    assert "画左下南向逃生通道" in payload["prompt"]
    assert "低位夕阳从画左后侧逆光" in payload["prompt"]
    assert "可见手部归属" not in payload["prompt"]
    assert "主检脸" not in payload["prompt"]


def test_imagen_compiler_normalizes_separate_negative_elements():
    payload = compile_image_prompt(_contract(backend="Imagen", model="imagen-3"))

    assert payload["negative_strategy"] == "separate_element_list"
    assert "不要" not in payload["negative_prompt"]
    assert "禁止" not in payload["negative_prompt"]
    assert "文字" in payload["negative_prompt"]


def test_relay_profile_requires_change_and_preserve_boundary():
    payload = compile_image_prompt(_contract(
        task_type="relay_edit",
        mode="tailframe",
        action="只把眼神从惊惧推进到决绝，右手握紧刀柄",
    ))

    assert payload["task_type"] == "relay_edit"
    assert "编辑已提交源帧" in payload["prompt"]
    assert "必须保持不变：" in payload["prompt"]
    assert payload["lint"]["errors"] == []


def test_conditional_anatomy_guards_do_not_inject_feet_into_closeup_without_risk():
    payload = compile_image_prompt(_contract(
        action="她抬眼看向对手",
        composition="眼部特写 ECU",
        risk_flags=["closeup"],
    ))

    assert "主检脸" in payload["prompt"]
    assert "鞋脚" not in payload["prompt"]
    assert "手部归属" not in payload["prompt"]


def test_compiled_markdown_round_trip_keeps_hashes_params_and_refs():
    payload = compile_image_prompt(_contract())
    parsed = parse_compiled_markdown(render_compiled_markdown(payload))

    assert parsed is not None
    assert parsed["kind"] == KIND
    assert parsed["prompt"] == payload["prompt"]
    assert parsed["compiled_request_sha256"] == payload["compiled_request_sha256"]
    assert parsed["request_params"] == payload["request_params"]
    assert parsed["reference_inputs"] == payload["reference_inputs"]


def test_compile_section_uses_selected_style_and_aspect_without_legacy_hardcodes():
    section = """## 镜头 1
**剧本描述**：她回头看向门口。
**导演意图**：表现被追踪的压迫感。
**身份锁定句**：同一角色脸和服装。
**镜头/机位**：MCU，过肩反打。
**光位锚**：画右窗光。
### 正向 prompt（中文）
```text
锚点句：黑色短发少女，蓝色校服；
镜头构图：MCU，过肩反打，竖屏9:16；
动作瞬间：她回头看向门口；
场景光影：雨夜教室，画右窗光；
情绪张力：克制紧张；
画风规格：写实国漫 / 影视级写实短剧质感；
禁止：不要文字、不要水印；
```
### 负向 prompt
不要文字、禁止水印
"""
    payload = compile_image_section(
        section,
        backend="openai",
        model="gpt-image-2",
        mode="image_reference",
        style="二次元赛璐璐，清晰线稿，块面阴影",
        aspect_ratio="16:9",
        request_params={"aspect_ratio": "16:9", "size": "1536x1024"},
    )

    assert "二次元赛璐璐" in payload["prompt"]
    assert "写实国漫" not in payload["prompt"]
    assert "9:16" not in payload["prompt"]
    assert payload["lint"]["errors"] == []


def test_lint_blocks_dangling_reference_and_aspect_conflict():
    payload = compile_image_prompt(_contract(reference_inputs=[]))
    payload["prompt"] += " 参考图3控制角色。画幅9:16。"
    payload["compiled_request_sha256"] = ""
    lint = lint_compiled_prompt(payload)

    assert "prompt_mentions_unattached_reference_index" in lint["errors"]
    assert "prompt_aspect_conflicts_with_request_params" in lint["errors"]


def test_embedded_compiled_section_gate_detects_missing_stale_and_wrong_backend():
    source = """## 镜头 1
**导演意图**：她发现门外有人。
**剧本描述**：她回头并收紧握刀的右手。
### 正向 prompt（中文）
```text
锚点句：黑色短发少女，蓝色校服；
镜头构图：MCU，过肩反打；
动作瞬间：她回头并收紧握刀的右手；
场景光影：雨夜教室，画右窗光；
情绪张力：克制紧张；
画风规格：二次元赛璐璐；
禁止：文字、水印；
```
"""
    payload = compile_image_section(
        source,
        backend="openai",
        model="gpt-image-2",
        mode="firstframe",
        task_type="shot_keyframe",
        request_params={"aspect_ratio": "16:9"},
    )
    embedded = source.rstrip() + "\n\n" + render_compiled_markdown(payload) + "\n"

    assert lint_compiled_section(
        embedded,
        expected_backend="openai",
        allowed_tasks=("shot_keyframe",),
    )["errors"] == []
    assert "missing_compiled_image_request" in lint_compiled_section(source)["errors"]
    assert "compiled_source_contract_stale" in lint_compiled_section(
        embedded.replace("她发现门外有人", "她发现窗外有人", 1)
    )["errors"]
    assert any(
        code.startswith("compiled_backend_mismatch")
        for code in lint_compiled_section(embedded, expected_backend="dreamina")["errors"]
    )


def test_codex_compiler_drops_recursive_block_and_softens_nonviolent_action():
    section = """## Clip_01
**剧本描述**：大殿内的阶层压力。
### 正向 prompt（中文）
```text
锚点句：少年与管事；
动作瞬间：管事用两指弹回木牌，少年承受冲击但不后退；
禁止：断手、断肢、血光、水印；
```
### 后端编译提交 image prompt
上一轮错误残留：武器入体与伤口。
"""
    contract = contract_from_section(
        section,
        backend="codex",
        mode="firstframe",
        task_type="multi_subject",
        target_path="Clip01.png",
        request_params={"aspect_ratio": "9:16"},
    )
    payload = compile_image_prompt(contract, "codex")

    assert "上一轮错误残留" not in payload["prompt"]
    assert "武器入体" not in payload["prompt"]
    assert "点住木牌" in payload["prompt"]
    assert "稳稳站住" in payload["prompt"]
    assert "断手" not in payload["prompt"]
    assert "断肢" not in payload["prompt"]
    assert "血光" not in payload["prompt"]
    assert "人体与手部结构自然完整" in payload["prompt"]
    assert "nonviolent_social_action_softened_for_provider" in payload["compiler_decisions"]


def test_backend_and_task_golden_fixtures():
    fixture_path = Path(__file__).with_name("fixtures") / "image_prompt_compiler_golden.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert fixture["profile_version"] == PROFILE_VERSION
    contract = fixture["contract"]

    for case in fixture["backend_cases"]:
        payload = compile_image_prompt({**contract, "backend": case["backend"]}, case["backend"])
        assert payload["profile"] == case["profile"]
        assert payload["negative_strategy"] == case["negative_strategy"]
        assert hashlib.sha256(payload["prompt"].encode("utf-8")).hexdigest() == case["prompt_sha256"]
        assert hashlib.sha256(payload["negative_prompt"].encode("utf-8")).hexdigest() == case["negative_sha256"]
        assert payload["lint"]["errors"] == []

    for case in fixture["task_cases"]:
        payload = compile_image_prompt({
            **contract,
            "backend": "codex",
            "task_type": case["task_type"],
            "mode": case["task_type"],
        }, "codex")
        assert payload["task_type"] == case["task_type"]
        assert payload["prompt"].startswith(case["opening"])
        assert payload["lint"]["errors"] == []
