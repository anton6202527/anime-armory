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
