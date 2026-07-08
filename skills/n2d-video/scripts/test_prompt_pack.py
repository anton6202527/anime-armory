from __future__ import annotations

import importlib.util
import json
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
    assert "第0集/Clip_09→第1集/Clip_01" in clips
    assert "boundary_frame=出图/第0集/图片/Clip_09_end.png" in clips
    assert "执行配方 / Execution Recipe" in clips
    assert "执行配方约束" in clips
    assert "frame_inputs=" in clips and "reference_inputs=" in clips and "anchor_consumption=" in clips
    assert "近景升格守卫" in clips
    assert "不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸" in clips
    assert "检查清单（视频三件套自查" in clips
    assert "自检（生成后逐条过" in clips


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
    assert "在场链约束：required_presence=CHAR_02、WEAPON_01" in clips
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
