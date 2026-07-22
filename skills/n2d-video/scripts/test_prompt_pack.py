from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path


SCRIPT = Path(__file__).with_name("prompt_pack.py")
spec = importlib.util.spec_from_file_location("prompt_pack", SCRIPT)
prompt_pack = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(prompt_pack)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_prompt_pack_builds_overview_and_clip_contract(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    (root / "_设置.md").write_text("制作模式：先出视频后配音\n生视频渠道：Dreamina\n", encoding="utf-8")
    (root / "出图" / ep / "prompt").mkdir(parents=True)
    (root / "出图" / ep / "prompt" / "00_总览.md").write_text(
        """# 第1集 出图总览

## 本集视觉一致性契约
- 色调基线：冷青灰。
- 光位锚：月光左上。
- 轴线：主角画左，反派画右。
- 状态演进：不提前觉醒。
- 景别阶梯：LS→CU。

## 本集基础视觉风格契约
- 风格名：冷灰写实3D国风漫剧
- 视觉基调：克制。
- 镜头与构图：9:16。
- 光色策略：冷月。
- 运动边界：固定/缓推。
- 风格禁忌：不要换脸。
- style_anchor：`出图/共享/图片/风格锚.png`

## 本集可看性签收合同
- 留存承诺账本：promise=她能不能活下去
""",
        encoding="utf-8",
    )
    _write_json(root / "脚本" / ep / "storyboard.json", {
        "style_contract": {"style_anchor": ["出图/共享/图片/风格锚.png"]},
        "clips": [{
            "id": "EP01_CLIP01",
            "label": "冷开",
            "duration": 4.2,
            "scene": "荒野",
            "rhythm": "冷开钩子",
            "dramatic_function": "她发现自己被追杀。",
            "audience_effect": "观众追问她怎么活。",
            "character_ids": ["CHAR_01"],
            "object_ids": ["WEAPON_01"],
            "location_id": "LOC_01",
            "firstframe_png": "出图/第1集/图片/Clip01_first.png",
            "endframe_png": "出图/第1集/图片/Clip01_end.png",
            "continuity": {
                "start_state": "她伏在荒野。",
                "end_state": "她握住刀。",
                "need_endframe": True,
                "transition": "match_cut",
                "expression_span": "中",
            },
            "entity_schedule": {"required_presence": ["CHAR_01"], "forbidden_presence": ["watermark"]},
            "shots": [{"lens": "CU 缓推", "desc": "她抬眼。", "video_prompt": "抬眼握刀。"}],
        }]
    })
    _write_json(root / "出视频" / ep / "prompt" / "video_model_routes.json", {
        "kind": "n2d_video_model_routes",
        "routes": [{
            "clip_id": "Clip_01",
            "shot_type": "dialogue_reaction",
            "primary_backend": "seedance",
            "fallback_backends": ["dreamina"],
            "mode": "frames2video",
            "native_audio_policy": "none",
            "identity_requirement": "reference_group",
            "motion_control": {"level": "none", "required_inputs": [], "failure_modes": []},
            "degrade_plan": "改 MCU/OTS。",
        }],
    })
    _write_json(root / "生产数据" / "identity_adapter_matrix.json", {
        "forms": [{"character_id": "CHAR_01", "form": "常态", "anchor_phrase": "黑发少女", "reference_group": {"front": {"path": "a.png"}}}]
    })
    _write_json(root / "生产数据" / f"mouth_visible_audit_{ep}.json", {"rows": [{"clip_id": "Clip_01", "suggested": True}]})
    _write_json(root / "生产数据" / f"script_quality_contract_{ep}.json", {
        "kind": "n2d_script_quality_contract",
        "signable_fields": {"clip_dramatic_functions": [{
            "clip_id": "EP01_CLIP01",
            "dramatic_function": "她发现自己被追杀。",
            "audience_effect": "观众追问她怎么活。",
        }]}
    })
    _write_json(root / "生产数据" / f"director_camera_plan_{ep}.json", {"kind": "n2d_director_camera_plan"})
    _write_json(root / "生产数据" / f"reference_plan_{ep}.json", {"kind": "n2d_reference_plan"})
    _write_json(root / "脚本" / ep / "continuity_chain.json", {
        "kind": "n2d_continuity_chain",
        "version": 1,
        "episode": ep,
        "status": "confirmed",
        "summary": {"seams": 1, "block": 0, "warn": 0},
        "seams": [{
            "scope": "episode_boundary",
            "from_episode": "第0集",
            "from_clip": "Clip_09",
            "to_episode": ep,
            "to_clip": "Clip_01",
            "transition": "接力",
            "policy": "relay",
            "strictness": "strict",
            "from_end_state": "她倒在荒野边缘。",
            "to_start_state": "她伏在荒野。",
            "required_boundary_frame": "出图/第0集/图片/Clip_09_end.png",
            "next_firstframe": "出图/第1集/图片/Clip01_first.png",
            "issues": [],
            "severity": "pass",
        }],
    })
    _write_json(root / "脚本" / ep / "shot_reverse_contract.json", {
        "kind": "n2d_shot_reverse_contract",
        "patterns": [{
            "clip_id": "EP01_CLIP01",
            "axis_id": "AXIS_LOC_01_CHAR_01_VS_CHAR_02",
            "participants": {
                "A": {"character_id": "CHAR_01", "screen_position": "画左前景", "eyeline_direction": "看画右，不看镜头"},
                "B": {"character_id": "CHAR_02", "screen_position": "画右中景", "eyeline_direction": "看画左，不看镜头"},
            },
            "screen_sides": {"spatial_mode": "left_right"},
            "coverage": {
                "a_ots": "焦点 CHAR_01；CHAR_02 的前景肩部虚化",
                "b_ots": "焦点 CHAR_02；CHAR_01 的前景肩部虚化",
            },
            "camera_coverage": "clean single + OTS + insert",
            "lens_height_distance_match": "50-85mm 中长焦，相近高度和距离",
            "crossing_axis_policy": "禁止越轴；需要建立镜缓冲",
            "buffer_or_reestablishing": "荒野道具插入或双人建立镜",
        }],
    })

    overview, clips = prompt_pack.build(root, ep)

    assert "本集导演一致性契约" in overview
    assert "本集模型路由表" in overview
    assert "本集近景身份风险表" in overview
    assert "风格锚.png" in overview
    assert "## Clip 01（时长 4.200s · EP01_CLIP01 · 冷开）" in clips
    assert "剧本可看性合同" in clips
    assert "她发现自己被追杀。" in clips
    assert "观众追问她怎么活。" in clips
    assert "**运动精修**：" in clips
    assert "原生音画策略" in clips and "mouth_visible=yes" in clips
    assert "接缝执行包 / Handoff Package" in clips
    assert "连续性链路 / Continuity Chain" in clips
    assert "正反打视频合同" in clips
    assert "AXIS_LOC_01_CHAR_01_VS_CHAR_02" in clips
    assert "第0集/Clip_09→第1集/Clip_01" in clips
    assert "boundary_frame=出图/第0集/图片/Clip_09_end.png" in clips

    p0, p1 = prompt_pack.write_outputs(root, ep, overview, clips)
    receipt = prompt_pack.write_consumed_contracts_receipt(root, ep, (p0, p1))
    data = json.loads(receipt.read_text(encoding="utf-8"))
    assert data["kind"] == "n2d_prompt_consumed_contracts"
    assert data["scope"] == "video_prompt"
    assert {row["name"] for row in data["contracts"]} >= {"storyboard", "continuity_chain", "shot_reverse_contract", "script_quality_contract"}
    continuity = next(row for row in data["contracts"] if row["name"] == "continuity_chain")
    assert continuity["exists"] is True and continuity["sha256"]
    shot_reverse = next(row for row in data["contracts"] if row["name"] == "shot_reverse_contract")
    assert shot_reverse["exists"] is True and shot_reverse["sha256"]
    assert all(row["exists"] and row["sha256"] for row in data["prompt_files"])
    assert "执行配方 / Execution Recipe" in clips
    assert "frame_inputs=" in clips and "reference_inputs=" in clips and "anchor_consumption=" in clips
    assert "### 后端编译提交 prompt" in clips
    assert "kind=n2d_compiled_video_prompt" in clips
    assert "profile=zh_motion_first" in clips
    assert "视线表演合同" in clips
    assert "视线与头部朝向：摄影机保持旁观者位置" in clips
    assert "固定机位，锁定轴线与景别，摄影机保持完全静止" in clips
    assert "执行配方约束" not in clips
    submitted = re.search(r"### 后端编译提交 prompt.*?```text\s*(.*?)```", clips, re.S)
    assert submitted is not None
    submit_text = submitted.group(1).strip()
    assert len(submit_text) < 600
    assert "模型路由" not in submit_text
    assert "执行配方" not in submit_text
    assert "identity_registry" not in submit_text
    compiled = prompt_pack.compile_video_prompt({
        "clip_id": "Clip_01",
        "backend": "seedance",
        "mode": "frames2video",
        "primary_action": "抬眼握刀",
        "camera_motion": "缓慢推近",
        "frame_inputs": ["first.png", "last.png"],
    })
    assert len(compiled["prompt"]) < 600
    assert "近景升格守卫" in clips
    assert "不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸" in clips
    assert "检查清单（视频三件套自查" in clips
    assert "自检（生成后逐条过" in clips
    assert "冷月与火把光影轻微随动" not in clips
    assert "低雾/尘土/衣袂/火把烟" not in clips


def test_motion_words_defaults_to_still_camera_without_motivation() -> None:
    amp, energy, camera = prompt_pack.motion_words(
        {"rhythm": "克制铺垫", "shots": [{"lens": "MCU"}]},
        {"shot_type": "dialogue_reaction"},
    )

    assert "固定机位" in camera
    assert "完全静止" in camera
    assert "推近" not in camera


def test_gaze_guard_keeps_character_on_story_target() -> None:
    guard = prompt_pack.gaze_performance_guard(
        {"continuity": {"eyeline": "看画右，不看镜头"}},
        ["CHAR_01"],
        {},
    )

    assert "摄影机保持旁观者位置" in guard
    assert "戏内视线关系持续成立：看画右" in guard
    assert "不看镜头" not in guard


def test_gaze_guard_allows_explicit_pov_direct_address() -> None:
    guard = prompt_pack.gaze_performance_guard(
        {"template": "POV", "gaze_intent": "破第四墙"},
        ["CHAR_01"],
        {},
    )

    assert "明确 POV/破第四墙" in guard
    assert "登记节拍内把视线落到摄影机" in guard


def test_prompt_pack_fills_style_anchor_from_storyboard_when_overview_is_generic(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    (root / "_设置.md").write_text("制作模式：先出视频后配音\n", encoding="utf-8")
    (root / "出图" / ep / "prompt").mkdir(parents=True)
    (root / "出图" / ep / "prompt" / "00_总览.md").write_text(
        """# 第1集 出图总览

## 本集基础视觉风格契约
- 风格名：冷灰写实3D国风漫剧
- style_anchor：继承出图风格锚。
""",
        encoding="utf-8",
    )
    _write_json(root / "脚本" / ep / "storyboard.json", {
        "style_contract": {"style_anchor": ["出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png"]},
        "clips": [],
    })

    overview, _ = prompt_pack.build(root, ep)

    assert "style_anchor：`出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png`" in overview


def test_clip_id_prefers_clip_number_over_episode_number() -> None:
    assert prompt_pack.clip_id("EP03_CLIP01", 99) == "Clip_01"
    assert prompt_pack.clip_id("EP10_CLIP09", 99) == "Clip_09"
    assert prompt_pack.clip_id("Clip_07", 99) == "Clip_07"


def test_native_audio_contract_follows_route_instead_of_hardcoding_silence() -> None:
    line, policy = prompt_pack.native_audio_contract(
        {"mode": "native_av", "native_audio_policy": "native_speech"},
        "yes",
    )

    assert policy == "native_speech"
    assert "audio_intent=native_speech" in line
    assert "speech_policy=native_speech" in line
    assert "compose_policy=保留原片音轨" in line
    assert "no_native_speech" not in line


def test_inner_focus_directive_isolates_video_motion_subject() -> None:
    clip = {
        "description": "姜月初内心独白：这百妖谱到底是什么。",
        "dramatic_function": "内心戏，表现疑惧。",
        "character_ids": ["CHAR_01", "CHAR_02"],
        "object_ids": ["VFX_系统面板"],
    }

    directive = prompt_pack.inner_focus_directive(
        clip,
        [str(x) for x in clip["character_ids"]],
        [str(x) for x in clip["object_ids"]],
    )

    assert "内心戏主体隔离" in directive
    assert "视频运动只服务 CHAR_01" in directive
    assert "非焦点主体 CHAR_02" in directive
    assert "不要重复上一镜群像" in directive


def test_closeup_promotion_guard_requires_closeup_anchor() -> None:
    guard = prompt_pack.closeup_promotion_guard(
        {
            "id": "EP01_CLIP06",
            "description": "裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。",
            "character_ids": ["CHAR_01", "CHAR_02"],
            "shots": [{"lens": "CU 缓推", "desc": "姜月初低头看裴长青。"}],
            "continuity": {"expression_span": "大"},
        },
        {"shot_type": "fight_exchange", "identity_requirement": "reference_group"},
        ["CHAR_01", "CHAR_02"],
        "虎山神咧嘴。",
        "裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。",
        "CU 缓推",
        "轻微推镜头",
        "大",
    )

    assert "近景升格守卫" in guard
    assert "不得把首/中/尾锚帧里脸部很小" in guard
    assert "full image_qc" in guard
    assert "禁止让视频模型补一张新脸" in guard


def test_ending_reaction_hold_guard_keeps_offscreen_character_out_until_cut() -> None:
    guard = prompt_pack.ending_reaction_hold_guard(
        {
            "id": "EP01_CLIP06",
            "label": "横刀落幅",
            "description": "横刀留在地面，衣袖侧背反应，不露姜月初正脸。",
            "continuity": {"end_state": "横刀和手部停住，给下一镜硬切。"},
        },
        ["CHAR_01"],
        "横刀和手部停住，地面物件反应",
        "hard_cut",
    )

    assert "最后 0.5 秒" in guard
    assert "offscreen_presence=CHAR_01" in guard
    assert "不在本 Clip 尾段提前预演下一构图" in guard


def test_prompt_pack_adds_tail_hold_for_offscreen_object_reaction(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    (root / "_设置.md").write_text("制作模式：先出视频后配音\n", encoding="utf-8")
    (root / "出图" / ep / "prompt").mkdir(parents=True)
    (root / "出图" / ep / "prompt" / "00_总览.md").write_text(
        "## 本集基础视觉风格契约\n- style_anchor：`出图/共享/图片/风格锚.png`\n",
        encoding="utf-8",
    )
    _write_json(root / "脚本" / ep / "storyboard.json", {
        "clips": [{
            "id": "EP01_CLIP06",
            "label": "横刀落幅",
            "duration": 6.0,
            "scene": "荒野",
            "dramatic_function": "横刀落地，给下一镜系统开启留白。",
            "audience_effect": "观众看到危机落点。",
            "character_ids": ["CHAR_02"],
            "object_ids": ["WEAPON_01"],
            "firstframe_png": "出图/第1集/图片/Clip06_first.png",
            "continuity": {
                "start_state": "裴长青倒飞。",
                "action": "横刀劈下后落地。",
                "end_state": "横刀和手部停住，衣袖侧背反应。",
                "transition": "hard_cut",
            },
            "entity_schedule": {
                "required_presence": ["CHAR_02", "WEAPON_01"],
                "offscreen_presence": ["CHAR_01"],
            },
            "shots": [{"lens": "OTS 侧背", "desc": "手部和横刀反应。"}],
        }]
    })
    _write_json(root / "出视频" / ep / "prompt" / "video_model_routes.json", {
        "routes": [{"clip_id": "Clip_06", "shot_type": "fight_reaction", "native_audio_policy": "none"}],
    })

    _, clips = prompt_pack.build(root, ep)

    assert "尾端落幅保持" in clips
    assert "最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点" in clips
    assert "offscreen_presence=CHAR_01" in clips
    assert "required_presence=CHAR_02、WEAPON_01" in clips
    assert "offscreen_presence=CHAR_01" in clips
    assert "forbidden_presence" in clips
    assert "不要提前把 offscreen 角色拉回清晰入画" in clips


def test_action_choreography_line_merges_template_contract_fields() -> None:
    route = {
        "shot_type": "mount_ride",
        "degrade_plan": "拆为火把远景、马蹄停下、陈青源下马三帧。",
        "action_choreography": {
            "required": True,
            "required_fields": [
                "beats",
                "speed_curve",
                "spatial_path",
                "camera_path",
                "readability_beats",
                "degrade_plan",
                "keyframe_plan",
                "post_cue_points",
                "physics_guard",
                "mount_contact",
                "gait_cycle",
                "screen_direction",
                "parallax_layers",
                "harness_lock",
            ],
        },
    }
    clip = {
        "template_contract": {
            "beats": ["远景火把压近", "勒缰停马"],
            "screen_direction": "马队由画面深处到画右中景。",
            "harness_lock": "缰绳、鞍具、火把归属清楚。",
            "keyframe_plan": [{"at_sec": 5.0, "frame": "Clip05_a1"}],
            "post_cue_points": [{"at_sec": 14.0, "cue": "勒缰停顿"}],
            "physics_guard": "马、人、缰绳、地面接触关系明确。",
        }
    }

    line = prompt_pack.action_choreography_line(route, clip)

    for key in ("keyframe_plan", "post_cue_points", "physics_guard", "screen_direction", "harness_lock"):
        assert key in line
    assert "勒缰停马" in line
    assert "马、人、缰绳" in line


def test_identity_line_resolves_storyboard_form_binding_by_base_character_id() -> None:
    forms = [{
        "character_id": "CHAR_01",
        "form": "囚途残损态",
        "reference_group": {"front": {"path": "front.png", "status": "ready"}},
        "anchor_phrase": "窄椭圆脸、低束长发",
    }]

    line = prompt_pack.identity_line(forms, ["CHAR_01/囚途残损态"])

    assert "CHAR_01/囚途残损态：reference_group=ready" in line
    assert "registry form 未在 adapter matrix 摘要中命中" not in line
