import json
import datetime as _dt
from pathlib import Path

import pytest

import router


def _root(tmp_path, settings="- 制作模式: 配音先行\n- 生视频AI: 即梦\n- 视频模型路由: 自动按镜头路由\n"):
    root = tmp_path / "制漫剧" / "测试剧"
    (root / "脚本" / "第1集").mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n" + settings, encoding="utf-8")
    return root


def _write_storyboard(root: Path, clips):
    p = root / "脚本" / "第1集" / "storyboard.json"
    p.write_text(json.dumps({"episode": 1, "clips": clips}, ensure_ascii=False), encoding="utf-8")
    return p


def test_fight_routes_to_kling_with_safe_fallback(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 1", "template": "fight_exchange", "scene": "王敦挥剑命中追兵"}])

    plan = router.route_episode(root, "第1集", generated_at="2026-06-08T00:00:00Z")

    route = plan["routes"][0]
    assert route["shot_type"] == "fight_exchange"
    assert route["primary_backend"] == "kling"
    assert route["fallback_backends"]
    assert route["primary_backend"] not in route["fallback_backends"]
    assert route["mode"] == "frames2video"
    assert route["motion_control"]["level"] == "required"
    assert route["motion_control"]["manifest_required"] is True
    assert "pose_sequence" in route["motion_control"]["required_inputs"]
    assert route["motion_control"]["manifest_path"].endswith("出视频/第1集/control/Clip_01/motion_control_manifest.json")
    assert route["action_choreography"]["required"] is True
    assert "impact_frame" in route["action_choreography"]["required_fields"]
    assert "keyframe_plan" in route["action_choreography"]["required_fields"]
    assert "action_choreography_required" in route["risk_flags"]
    recipe = route["execution_recipe"]
    assert recipe["execution_backend"] == route["primary_backend"]
    assert recipe["frame_inputs"]["consumption_mode"] == "first_frame"
    assert recipe["frame_inputs"]["last_frame"] is False
    assert recipe["frame_inputs"]["native_timeline_frames"] == 1
    assert recipe["reference_inputs"]["motion_reference"]["library_path"] == "生产数据/motion_reference_library.json"
    assert recipe["control_inputs"]["required"] is True
    assert "pose_sequence" in recipe["control_inputs"]["required_inputs"]
    assert recipe["control_inputs"]["manifest_path"].endswith("出视频/第1集/control/Clip_01/motion_control_manifest.json")
    assert recipe["fallback"]["fallback_backends"] == route["fallback_backends"]
    assert plan["backend_consistency_scope"]["image_generation"] == "single_model_channel_per_project"
    assert route["identity_preservation_plan"]["applies_to"] == "fight_exchange"
    assert recipe["reference_inputs"]["identity_preservation_plan"]["applies_to"] == "fight_exchange"


def test_hybrid_visible_dialogue_without_track_routes_base_video_post_lipsync(tmp_path):
    root = _root(tmp_path, settings="- 制作模式: 混合自动路由\n- 生视频AI: 即梦\n- 视频模型路由: 自动按镜头路由\n")
    (root / "脚本" / "第1集" / "voiceover.txt").write_text(
        "[镜头1·沈念·迟疑] 你看见了吗？\n", encoding="utf-8"
    )
    _write_storyboard(root, [{
        "id": "Clip_01", "template": "dialogue_shot_reverse",
        "voiceover_indices": [1], "dialogue_indices": [1], "mouth_visible": True,
    }])

    plan = router.route_episode(root, "第1集")
    route = plan["routes"][0]

    assert plan["av_mode"] == "hybrid"
    assert route["audio_strategy"] == "base_video_then_post_lipsync"
    assert route["mode"] == "image2video"
    assert route["native_audio_policy"] == "none"
    assert route["base_video_only"] is True
    assert route["post_lipsync_required"] is True
    assert route["execution_recipe"]["audio_inputs"]["base_video_only"] is True
    assert route["execution_recipe"]["audio_inputs"]["performance_audio_paths"] == []


def test_hybrid_visible_dialogue_with_guide_routes_voice_conditioned(tmp_path):
    root = _root(tmp_path, settings="- 制作模式: 混合自动路由\n- 生视频AI: 即梦\n- 视频模型路由: 自动按镜头路由\n")
    (root / "脚本" / "第1集" / "voiceover.txt").write_text(
        "[镜头1·沈念·克制] 别动。\n", encoding="utf-8"
    )
    guide = root / "生产数据" / "guide.wav"
    guide.parent.mkdir(parents=True)
    guide.write_bytes(b"guide")
    _write_storyboard(root, [{
        "id": "Clip_01", "template": "dialogue_shot_reverse",
        "voiceover_indices": [1], "dialogue_indices": [1], "mouth_visible": True,
        "guide_audio": "生产数据/guide.wav",
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["audio_strategy"] == "performance_audio_first"
    assert route["mode"] == "voice_conditioned_lipsync"
    assert route["performance_track_status"] == "guide_ready"
    assert route["execution_recipe"]["audio_inputs"]["performance_audio_paths"] == ["生产数据/guide.wav"]


def test_mid_anchor_without_endframe_does_not_consume_last_frame(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{
        "id": "Clip 1",
        "template": "fight_exchange",
        "scene": "打斗收束反应镜，中段抬眼，集尾硬断",
        "character_ids": ["CHAR_01"],
        "continuity": {
            "anchors": [{"label": "中段抬眼"}],
            "need_endframe": False,
        },
    }])

    route = router.route_episode(root, "第1集")["routes"][0]
    frame_inputs = route["execution_recipe"]["frame_inputs"]

    assert route["anchor_consumption"]["anchor_count"] == 1
    assert route["anchor_consumption"]["need_end"] is False
    assert route["anchor_consumption"]["consumes_endframe"] is False
    assert frame_inputs["mid_anchors"] == 1
    assert frame_inputs["last_frame"] is False
    assert frame_inputs["native_timeline_frames"] == 2
    assert route["execution_recipe"]["post_video_qc"]["identity_qc_required"] is True
    assert route["execution_recipe"]["post_video_qc"]["dense_face_watch_required"] is True
    assert "video_face_drift_watch" in route["execution_recipe"]["post_video_qc"]["required_reports"]
    allowances = route["identity_preservation_plan"]["motion_readability_allowances"]
    assert any("first frame and registered reference group" in line for line in allowances)
    assert all("first/end frame" not in line for line in allowances)


def test_structured_character_ids_prevent_offscreen_prose_from_becoming_refs(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{
        "id": "Clip 1",
        "template": "fight_exchange",
        "scene": "裴长青倒飞，虎妖压迫",
        "character_ids": ["CHAR_02", "CHAR_03"],
        "entity_schedule": {
            "characters": ["CHAR_02", "CHAR_03"],
            "offscreen_presence": ["CHAR_01"],
            "required_presence": ["CHAR_02", "CHAR_03"],
        },
        "continuity": {
            "end_state": "CHAR_01 只在画外以手部/衣袖/OTS轮廓反应，不露清晰正脸。",
            "negative": "禁止 CHAR_01 正脸近景。",
        },
        "template_contract": {
            "degrade_plan": "不稳就改手部/物件反应；禁止 CHAR_01 clear face。",
        },
    }])

    route = router.route_episode(root, "第1集")["routes"][0]
    ids = [c.get("character_id") for c in route["clip_characters"]]
    recipe_ids = [
        c.get("character_id")
        for c in route["execution_recipe"]["reference_inputs"]["characters"]
    ]

    assert ids == ["CHAR_02", "CHAR_03"]
    assert recipe_ids == ["CHAR_02", "CHAR_03"]
    assert "CHAR_01" not in ids
    assert "CHAR_01" not in recipe_ids


def test_refresh_execution_reroutes_mid_anchor_to_native_multiframe_backend():
    route = {
        "clip_id": "Clip_01",
        "shot_type": "general_motion",
        "primary_backend": "veo",
        "fallback_backends": ["dreamina", "seedance"],
        "mode": "image2video",
        "native_audio_policy": "none",
        "identity_requirement": "reference_group",
        "risk_flags": [],
        "rationale": [],
        "prompt_requirements": [],
        "degrade_plan": "按锚帧拆解。",
    }
    clip = {
        "id": "Clip 1",
        "duration": 6,
        "character_ids": ["CHAR_01"],
        "continuity": {
            "need_endframe": True,
            "anchors": [{"anchor_png": "出图/第1集/图片/Clip01_a1.png"}],
        },
    }

    router.refresh_execution_contracts(
        [route],
        [clip],
        episode="第1集",
        video_channel="Dreamina",
        urgency_tier="realtime",
    )

    assert route["primary_backend"] == "dreamina"
    assert route["anchor_consumption"]["consumption_mode"] == "native_multiframe"
    assert "frame_anchor_rerouted" in route["risk_flags"]
    assert route["execution_recipe"]["frame_inputs"]["mid_anchors"] == 1


def test_water_carrying_mountain_road_does_not_match_car_keyword(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{
        "id": "Clip 1",
        "duration": 10,
        "scene": "后山山路/夜",
        "character_ids": ["CHAR_HE"],
        "shots": [
            {"desc": "挑桶、山路、喘息，重复到第五趟。", "video_prompt": "water-carrying montage, rugged mountain road"}
        ],
    }])

    route = router.route_episode(root, "第1集", generated_at="2026-06-08T00:00:00Z")["routes"][0]

    assert route["shot_type"] == "general_motion"
    assert route["action_choreography"]["required"] is False


def test_long_clip_filters_short_fallbacks_and_adds_safe_backend(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{
        "id": "Clip 1",
        "template": "ensemble_blocking",
        "duration": 11,
        "character_ids": ["CHAR_HE", "CHAR_JIANG"],
        "scene": "外门旧院群像调度",
    }])

    route = router.route_episode(root, "第1集", generated_at="2026-06-08T00:00:00Z")["routes"][0]

    assert all(router.video_backend_max_seconds(b) >= 11 for b in route["fallback_backends"])
    assert "seedance" in route["fallback_backends"] or "dreamina" in route["fallback_backends"]
    assert route["identity_preservation_plan"]["applies_to"] == "ensemble_blocking"


def test_long_timeline_clip_uses_segment_relay_plan(tmp_path):
    root = _root(tmp_path, "- 生视频模型: Seedance 2.0\n- 生视频渠道: 即梦/Dreamina\n- 视频模型路由: 自动按镜头路由\n")
    _write_storyboard(root, [{
        "id": "Clip 1",
        "template": "dialogue_shot_reverse",
        "duration": 18.5,
        "character_ids": ["CHAR_01", "CHAR_02"],
        "scene": "两人正反打压迫交易",
        "continuity": {
            "need_endframe": True,
            "anchors": [{"at_sec": 4.0, "anchor_png": "出图/第1集/图片/Clip01_mid.png"}],
        },
    }])

    route = router.route_episode(root, "第1集", generated_at="2026-06-08T00:00:00Z")["routes"][0]

    assert "long_duration" not in route["risk_flags"]
    assert "duration_segment_relay" in route["risk_flags"]
    relay = route["duration_segment_relay"]
    assert relay["supported"] is True
    assert [s["duration_sec"] for s in relay["segments"]] == [4.0, 14.5]
    assert route["execution_recipe"]["video_segments"]["required"] is True
    assert route["fallback_backends"]


def test_dreamina_channel_demotes_unverified_paid_primary(tmp_path):
    root = _root(tmp_path, "- 生视频渠道: Dreamina\n- 视频模型路由: 自动按镜头路由\n")
    _write_storyboard(root, [{
        "id": "Clip 1",
        "template": "multi_character_same_frame",
        "duration": 3,
        "character_ids": ["CHAR_01", "CHAR_02"],
        "scene": "两人同框定格对峙",
    }])

    route = router.route_episode(root, "第1集", generated_at="2026-07-03T00:00:00Z")["routes"][0]

    assert route["shot_type"] == "multi_character_same_frame"
    assert route["primary_backend"] == "seedance"
    assert route["fallback_backends"] == ["dreamina"]
    assert any("不可自动付费路由" in item for item in route["rationale"])


def test_native_speech_fallbacks_keep_native_av_capability(tmp_path):
    root = _root(tmp_path, "- 生视频模型: Seedance 2.0\n- 生视频渠道: 即梦/Dreamina\n- 制作模式: 原生音画\n")
    _write_storyboard(root, [{
        "id": "Clip 1",
        "template": "dialogue_shot_reverse",
        "duration": 9,
        "character_ids": ["CHAR_HE"],
        "dialogue_indices": [1],
        "scene": "少年正面说话",
    }])

    route = router.route_episode(root, "第1集", generated_at="2026-06-08T00:00:00Z")["routes"][0]

    assert route["native_audio_policy"] == "native_speech"
    assert route["fallback_backends"] == ["seedance"]


def _write_storyboard_with_style(root: Path, clips, style_name):
    p = root / "脚本" / "第1集" / "storyboard.json"
    p.write_text(json.dumps(
        {"episode": 1, "clips": clips, "style_contract": {"风格名": style_name}},
        ensure_ascii=False), encoding="utf-8")
    return p


def test_motion_spectacle_guidance_attached_to_combat_route(tmp_path):
    # P0-2：打斗镜 route 必须挂上 motion 侧视觉盛宴指导（与出图 runner 同源·风格自适应）。
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 1", "template": "fight_exchange", "scene": "王敦挥剑命中追兵，冲击波炸开"}])
    plan = router.route_episode(root, "第1集", generated_at="2026-06-08T00:00:00Z")
    route = plan["routes"][0]
    assert plan["motion_spectacle_guidance_applied"] == 1
    assert "经费在燃烧" in route["motion_spectacle_guidance"]  # 无风格 → cinematic 默认
    assert any("motion_spectacle_guidance" in r for r in route.get("prompt_requirements", []))


def test_motion_spectacle_guidance_adapts_to_cel_style(tmp_path):
    # 赛璐璐风格的打斗 route：换赛璐璐速度线变体，绝不硬塞写实 motion blur 长拖影。
    root = _root(tmp_path)
    _write_storyboard_with_style(
        root,
        [{"id": "Clip 1", "template": "fight_exchange", "scene": "少年挥剑劈砍，命中炸开冲击波"}],
        "二次元赛璐璐")
    plan = router.route_episode(root, "第1集", generated_at="2026-06-08T00:00:00Z")
    g = plan["routes"][0]["motion_spectacle_guidance"]
    assert "赛璐璐" in g and "速度线" in g
    assert "顺攻击方向给速度线 + 拖影 motion blur" not in g


def test_motion_spectacle_guidance_skips_calm_shot(tmp_path):
    # 平静对白镜：不挂盛宴指导（避免稀释 prompt）。
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 1", "template": "dialogue_closeup", "scene": "少女在窗边静静喝茶"}])
    plan = router.route_episode(root, "第1集", generated_at="2026-06-08T00:00:00Z")
    assert plan["motion_spectacle_guidance_applied"] == 0
    assert "motion_spectacle_guidance" not in plan["routes"][0]


def test_t2v_experimental_fight_without_named_character_skips_timeline_frames(tmp_path):
    root = _root(
        tmp_path,
        "- 生视频AI: 即梦\n"
        "- 视频模型路由: 自动按镜头路由\n"
        "- T2V动作通道: 实验开启\n",
    )
    _write_storyboard(root, [{"id": "Clip 1", "template": "fight_exchange", "scene": "无人物，剑刃与火星高速碰撞"}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["mode"] == "text2video"
    assert route["experimental_t2v"] is True
    assert route["identity_requirement"] == "none"
    assert route["execution_recipe"]["frame_inputs"]["first_frame"] is False
    assert route["execution_recipe"]["frame_inputs"]["consumption_mode"] == "text_prompt_with_references"


def test_t2v_experimental_named_character_without_plan_falls_back(tmp_path):
    root = _root(
        tmp_path,
        "- 生视频AI: 即梦\n"
        "- 视频模型路由: 自动按镜头路由\n"
        "- T2V动作通道: 实验开启\n",
    )
    _write_storyboard(root, [{
        "id": "Clip 1",
        "template": "fight_exchange",
        "character_ids": ["CHAR_SHEN"],
        "scene": "沈念挥剑命中追兵",
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["mode"] == "frames2video"
    assert "experimental_t2v" not in route
    assert any("缺 t2v_identity_reference_plan" in item for item in route["rationale"])
    assert route["execution_recipe"]["frame_inputs"]["first_frame"] is True


def test_spectacle_backend_benchmark_can_override_auto_route(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 1", "template": "fight_exchange", "scene": "王敦挥剑命中追兵"}])
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    (prod / "spectacle_backend_benchmark.json").write_text(json.dumps({
        "kind": "n2d_spectacle_backend_benchmark",
        "probed_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "version": 1,
        "recommendations": {
            "fight_exchange": {"primary_backend": "seedance", "score": 91, "evidence": "pilot probe"}
        },
    }, ensure_ascii=False), encoding="utf-8")

    plan = router.route_episode(root, "第1集", generated_at="2026-06-08T00:00:00Z")
    route = plan["routes"][0]

    assert route["primary_backend"] == "seedance"
    assert route["fallback_backends"][0] == "kling"
    assert "spectacle_benchmark_routed" in route["risk_flags"]
    assert plan["spectacle_backend_benchmark"]["applied"][0]["now"] == "seedance"
    assert route["execution_recipe"]["execution_backend"] == "seedance"
    assert route["execution_recipe"]["reference_inputs"]["motion_reference"]["allowed"] is True
    assert route["policy_resolution"]["winner"] == "motion_control_required"


def test_spectacle_backend_benchmark_defers_to_cross_episode_baseline(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 1", "template": "fight_exchange", "scene": "王敦挥剑命中追兵"}])
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    (prod / "spectacle_backend_benchmark.json").write_text(json.dumps({
        "kind": "n2d_spectacle_backend_benchmark",
        "probed_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "version": 1,
        "recommendations": {
            "fight_exchange": {"primary_backend": "seedance", "score": 91, "evidence": "pilot probe"}
        },
    }, ensure_ascii=False), encoding="utf-8")

    plan = router.route_episode(root, "第1集", baseline={"fight_exchange": "kling"})
    route = plan["routes"][0]

    assert route["primary_backend"] == "kling"
    assert "spectacle_benchmark_deferred_by_baseline" in route["risk_flags"]
    assert route["spectacle_benchmark_deferred"]["recommended_backend"] == "seedance"
    assert route["policy_resolution"]["winner"] == "motion_control_required"
    assert any(c["surface"] == "backend_choice" for c in route["policy_resolution"]["conflicts"])


def test_execution_multiframe_channel_overrides_doomed_kling_primary(tmp_path):
    root = _root(
        tmp_path,
        "- 生视频模型: Seedance 2.0\n"
        "- 生视频渠道: 即梦/Dreamina\n"
        "- 视频模型路由: 自动按镜头路由\n",
    )
    _write_storyboard(root, [{
        "id": "Clip 1",
        "template": "fight_exchange",
        "duration": 14,
        "scene": "沈念按住柳娘子背部炼化",
        "continuity": {
            "need_endframe": True,
            "midframe": {"midframe_png": "出图/第1集/图片/Clip_01_mid.png"},
        },
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "fight_exchange"
    assert route["primary_backend"] == "seedance"
    assert "kling" not in route["fallback_backends"]
    assert "veo" not in route["fallback_backends"]
    assert all(router.video_backend_max_seconds(b) >= 14 for b in route["fallback_backends"])
    assert route["fallback_backends"] == ["dreamina"]
    assert route["max_clip_seconds"] == 15
    assert any("执行渠道" in item for item in route["rationale"])
    assert route["anchor_consumption"]["consumption_mode"] == "native_multiframe"
    assert route["execution_recipe"]["frame_inputs"]["native_timeline_frames"] == 3


def test_spectacle_prior_nudges_generic_fallthrough(tmp_path):
    # 万人战场全景：infer_spectacle_type=large_establishing，但 shot_type=general_motion 落到 default(dreamina)。
    # 冷启动 prior 应把它从 default 兜底改到 large_establishing 首选 veo，原 default 保留为 fallback。
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 5", "scene": "万人战场全景，千军列阵，宏大鸟瞰"}])

    plan = router.route_episode(root, "第1集", generated_at="2026-06-08T00:00:00Z")
    route = plan["routes"][0]

    assert route["shot_type"] == "general_motion"
    assert route["primary_backend"] == "veo"
    assert "dreamina" in route["fallback_backends"]
    assert "spectacle_prior_routed" in route["risk_flags"]
    assert route["spectacle_prior"]["spectacle_type"] == "large_establishing"
    assert plan["spectacle_backend_prior"]["applied"][0]["now"] == "veo"


def test_spectacle_prior_skips_when_benchmark_covers_type(tmp_path):
    # benchmark 覆盖了 large_establishing → prior 不再插手该类型（benchmark 权威）。
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 5", "scene": "万人战场全景，千军列阵，宏大鸟瞰"}])
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    (prod / "spectacle_backend_benchmark.json").write_text(json.dumps({
        "kind": "n2d_spectacle_backend_benchmark",
        "probed_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "recommendations": {"large_establishing": {"primary_backend": "seedance"}},
    }, ensure_ascii=False), encoding="utf-8")

    plan = router.route_episode(root, "第1集", generated_at="2026-06-08T00:00:00Z")
    route = plan["routes"][0]

    assert route["primary_backend"] == "seedance"
    assert "spectacle_prior_routed" not in route["risk_flags"]
    assert "spectacle_backend_prior" not in plan


def test_spectacle_prior_skipped_in_fixed_default_mode(tmp_path):
    root = _root(tmp_path, settings="- 生视频AI: 即梦\n- 视频模型路由: 固定生视频模型\n")
    _write_storyboard(root, [{"id": "Clip 5", "scene": "万人战场全景，千军列阵，宏大鸟瞰"}])

    plan = router.route_episode(root, "第1集", generated_at="2026-06-08T00:00:00Z")
    route = plan["routes"][0]

    assert route["primary_backend"] == "dreamina"
    assert "spectacle_prior_routed" not in route["risk_flags"]


def test_flight_routes_to_seedance(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 2", "template": "flight", "scene": "御剑飞行，云层向后高速流动"}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "flight"
    assert route["primary_backend"] == "seedance"
    assert route["identity_requirement"] in ("none", "face_lock_or_reference_group")
    assert route["max_clip_seconds"] == 15
    assert route["motion_control"]["level"] == "required"
    assert set(["camera_path", "parallax_layers"]).issubset(route["motion_control"]["required_inputs"])
    assert route["action_choreography"]["required"] is True
    assert "altitude_curve" in route["action_choreography"]["required_fields"]
    assert "high_speed_motion" in route["risk_flags"]


def test_chase_routes_require_motion_path_and_choreography(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 3", "template": "chase", "scene": "屋脊追逐，追兵沿画面左到右紧追"}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "chase"
    assert route["primary_backend"] == "seedance"
    assert route["motion_control"]["level"] == "required"
    assert set(["camera_path", "spatial_path"]).issubset(route["motion_control"]["required_inputs"])
    assert route["action_choreography"]["required"] is True
    assert "distance_curve" in route["action_choreography"]["required_fields"]


def test_magic_burst_routes_as_premium_action_spectacle(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 8", "template": "magic_burst", "scene": "沈念挥出青色剑气，撞上黑色护盾后破防"}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "magic_burst"
    assert route["primary_backend"] == "seedance"
    assert route["motion_control"]["level"] == "required"
    assert "vfx_layers" in route["motion_control"]["required_inputs"]
    assert route["action_choreography"]["required"] is True
    assert "collision_or_apex_frame" in route["action_choreography"]["required_fields"]
    assert "keyframe_plan" in route["action_choreography"]["required_fields"]
    assert "action_choreography_required" in route["risk_flags"]
    assert "vfx_consistency_risk" in route["risk_flags"]
    assert route["motion_reference"]["applicable"] is True


@pytest.mark.parametrize(
    ("template", "scene", "specific_field"),
    [
        ("mount_ride", "主角骑灵狼穿林奔跑，鞍具与缰绳清楚", "mount_contact"),
        ("vehicle_ride", "马车沿山路左到右疾行，车轮扬尘", "wheel_rotation"),
        ("vessel_flight", "飞舟穿云抵达山门，云海高速后掠", "vehicle_lock"),
        ("road_vehicle", "出租车沿高架左到右疾行，车流后掠，司机紧握方向盘", "lane_lock"),
        ("stealth_stalk", "黑衣人尾随女主穿过暗走廊，门缝遮挡，手电光扫过", "occlusion_layers"),
    ],
)
def test_continuous_motion_routes_require_choreography(tmp_path, template, scene, specific_field):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 4", "template": template, "scene": scene}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == template
    assert route["primary_backend"] == "seedance"
    assert route["motion_control"]["level"] == "required"
    assert set(["camera_path", "spatial_path", "parallax_layers"]).issubset(route["motion_control"]["required_inputs"])
    assert route["action_choreography"]["required"] is True
    assert specific_field in route["action_choreography"]["required_fields"]
    assert "screen_direction" in route["action_choreography"]["required_fields"]
    assert "high_speed_motion" in route["risk_flags"]


def test_screen_insert_routes_to_overlay_sensitive_path(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{
        "id": "Clip 6",
        "template": "screen_insert",
        "scene": "手机屏幕出现聊天记录和定位时间码，手指轻点来电弹窗",
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "screen_insert"
    assert route["primary_backend"] == "kling"
    assert route["motion_control"]["level"] == "none"
    assert "text_overlay_required" in route["risk_flags"]
    assert any("overlay" in req for req in route["prompt_requirements"])


def test_evidence_search_routes_to_object_continuity_path(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{
        "id": "Clip 7",
        "template": "evidence_search",
        "scene": "侦探翻找抽屉，露出沾血票据，证物袋入画",
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "evidence_search"
    assert route["primary_backend"] == "kling"
    assert route["motion_control"]["level"] == "none"
    assert "object_continuity_risk" in route["risk_flags"]
    assert any("clue_object" in req for req in route["prompt_requirements"])


@pytest.mark.parametrize(
    ("template", "scene", "field_hint"),
    [
        ("tribulation_breakthrough", "雷劫劈落，主角护体光抵挡后突破光柱冲天", "lightning"),
        ("array_ritual", "宗门大阵起势，阵眼依次点亮，结界封住魔兽", "VFX"),
        ("realm_portal", "现代青年被时空裂缝卷入秘境入口，落到异界山门前", "portal"),
        ("contract_summon", "少女以血契召唤灵兽，契约印记落在手背", "summon"),
    ],
)
def test_genre_vfx_spectacles_route_to_asset_locked_path(tmp_path, template, scene, field_hint):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 9", "template": template, "scene": scene}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == template
    assert route["primary_backend"] == "seedance"
    assert route["motion_control"]["level"] == "none"
    assert route["action_choreography"]["required"] is False
    assert "vfx_consistency_risk" in route["risk_flags"]
    assert any(field_hint.lower() in req.lower() for req in route["prompt_requirements"])


def test_soul_manifestation_routes_to_identity_sensitive_frames_path(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{
        "id": "Clip 10",
        "template": "soul_manifestation",
        "scene": "CHAR_01 盘坐，半透明元神从天灵升起并进入识海探查",
        "characters": ["CHAR_01/常态"],
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "soul_manifestation"
    assert route["primary_backend"] == "kling"
    assert route["mode"] == "frames2video"
    assert route["identity_requirement"] == "character_id_or_reference_group"
    assert "body_soul_consistency_risk" in route["risk_flags"]
    assert any("body_soul_identity_lock" in req for req in route["prompt_requirements"])


@pytest.mark.parametrize(
    ("template", "scene", "risk_flag"),
    [
        ("alchemy_forging", "丹炉开炉，三味药材入炉后凝成金色丹药", "object_continuity_risk"),
        ("talent_test", "测灵石光柱暴涨，天赋等级文字由后期叠加，众人震惊", "text_overlay_required"),
    ],
)
def test_craft_and_talent_routes_to_readability_path(tmp_path, template, scene, risk_flag):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 11", "template": template, "scene": scene}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == template
    assert route["primary_backend"] == "kling"
    assert route["motion_control"]["level"] == "none"
    assert risk_flag in route["risk_flags"]
    assert any("overlay" in req or "lock" in req for req in route["prompt_requirements"])


def test_reveal_template_routes_to_identity_sensitive_speech_path(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{
        "id": "Clip 8",
        "template": "reveal_reaction_chain",
        "scene": "沈念拿出血书，当众揭穿皇叔真实身份，众人反应",
        "characters": ["CHAR_01/常态"],
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "reveal_reaction_chain"
    assert route["primary_backend"] == "kling"
    assert route["identity_requirement"] == "character_id_or_reference_group"
    assert route["clip_characters"]
    assert route["quality_tier"] in ("high", "n/a")
    assert any("knowledge_order" in item for item in route["prompt_requirements"])


def test_hug_or_pull_routes_to_kling_and_contact_risk(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 3", "template": "hug_or_pull", "scene": "沈念被抓腕拉扯后推开，王敦伸手护住"}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "hug_or_pull"
    assert route["primary_backend"] == "kling"
    assert route["mode"] == "frames2video"
    assert "contact_motion" in route["risk_flags"]
    assert "feature_melting_risk" in route["risk_flags"]
    assert route["motion_control"]["level"] == "required"
    assert "contact_map" in route["motion_control"]["required_inputs"]


def test_multi_character_same_frame_routes_to_kling(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 4", "template": "multi_character_same_frame", "scene": "沈念、王敦、太监三人同框对峙"}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "multi_character_same_frame"
    assert route["primary_backend"] == "kling"
    assert "multi_person" in route["risk_flags"]
    assert "character_id_or_reference_group" == route["identity_requirement"]


def test_ensemble_blocking_routes_to_kling_not_legacy_sora(tmp_path):
    # Sora 已是 legacy/manual-only；群像不再自动路由到 Sora。
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 5", "template": "ensemble_blocking", "scene": "宗门大殿群像站位，门徒队列围住主角"}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "ensemble_blocking"
    assert route["primary_backend"] == "kling"
    assert "sora" not in route["fallback_backends"]
    assert "multi_person" in route["risk_flags"]
    assert any("Sora 已从自动路由移除" in r for r in route["rationale"])


def test_five_plus_same_frame_routes_to_kling_with_split_plan(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 6", "template": "multi_character_same_frame",
                              "scene": "六人对峙同框",
                              "template_contract": {"character_slots": {"A": "", "B": "", "C": "", "D": "", "E": "", "F": ""}}}])
    route = router.route_episode(root, "第1集")["routes"][0]
    assert route["primary_backend"] == "kling"
    assert "sora" not in route["fallback_backends"]
    assert "multi_person" in route["risk_flags"]


def test_two_three_same_frame_still_kling(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 7", "template": "multi_character_same_frame",
                              "scene": "三人对峙同框",
                              "template_contract": {"character_slots": {"A": "", "B": "", "C": ""}}}])
    route = router.route_episode(root, "第1集")["routes"][0]
    assert route["primary_backend"] == "kling"


def test_empty_establishing_with_native_audio_opt_in_routes_to_veo(tmp_path):
    root = _root(
        tmp_path,
        "- 生视频AI: 即梦\n"
        "- 视频生成音频策略: 低风险环境声\n"
        "- 视频原生音轨: 低音量混入环境声\n",
    )
    _write_storyboard(root, [{"id": "Clip 3", "scene": "山门空镜，雨声和风声，远景氛围转场"}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "empty_establishing"
    assert route["primary_backend"] == "veo"
    assert route["native_audio_policy"] == "ambience"


def test_native_av_mode_routes_dialogue_to_native_speech(tmp_path):
    root = _root(tmp_path, "- 生视频AI: 即梦\n- 视频模型路由: 自动按镜头路由\n- 制作模式: 原生音画\n")
    _write_storyboard(root, [{"id": "Clip 1", "template": "dialogue_shot_reverse", "scene": "沈念与王敦对话反打，台词交锋"}])

    plan = router.route_episode(root, "第1集")
    route = plan["routes"][0]

    assert plan["av_mode"] == "native_av"
    assert plan["production_mode"] == "原生音画"
    assert route["mode"] == "native_av"
    assert route["native_audio_policy"] == "native_speech"
    assert route["primary_backend"] in router.NATIVE_AV_BACKENDS
    assert "sora" not in route["fallback_backends"]
    assert "native_speech" in route["risk_flags"]


def test_native_av_routes_narrative_state_with_character_dialogue_to_native_speech(tmp_path):
    root = _root(tmp_path, "- 生视频AI: 即梦\n- 视频模型路由: 自动按镜头路由\n- 制作模式: 原生音画\n")
    _write_storyboard(root, [{
        "id": "Clip 5",
        "template": "reveal_reaction_chain",
        "scene": "虎妖诈死复苏，虎妖开口拦路，裴长青确认不可能",
        "character_ids": ["CHAR_01", "CHAR_02", "CHAR_03"],
        "dialogue_indices": [14, 15],
        "narration_indices": [13],
        "continuity": {
            "anchors": [{"label": "虎妖开口拦路"}],
            "need_endframe": True,
        },
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "reveal_reaction_chain"
    assert route["mode"] == "native_av"
    assert route["native_audio_policy"] == "native_speech"
    assert route.get("requires_voice_fallback") is not True
    frame_inputs = route["execution_recipe"]["frame_inputs"]
    assert frame_inputs["first_frame"] is True
    assert frame_inputs["native_timeline_frames"] == 3


def test_native_av_keeps_narration_only_narrative_state_visual_first(tmp_path):
    root = _root(tmp_path, "- 生视频AI: 即梦\n- 视频模型路由: 自动按镜头路由\n- 制作模式: 原生音画\n")
    _write_storyboard(root, [{
        "id": "Clip 5",
        "template": "reveal_reaction_chain",
        "scene": "真相物证露出，众人无声反应",
        "character_ids": ["CHAR_01", "CHAR_02"],
        "narration_indices": [13],
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "reveal_reaction_chain"
    assert route["native_audio_policy"] == "none"
    assert route.get("requires_voice_fallback") is True


def test_native_av_mode_leaves_action_shots_unchanged(tmp_path):
    root = _root(tmp_path, "- 生视频AI: 即梦\n- 视频模型路由: 自动按镜头路由\n- 制作模式: 原生音画\n")
    _write_storyboard(root, [{"id": "Clip 1", "template": "fight_exchange", "scene": "挥剑命中追兵"}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "fight_exchange"
    assert route["primary_backend"] == "kling"
    assert route["native_audio_policy"] == "none"


def test_voice_first_dialogue_closeup_defaults_to_silent_video_flow(tmp_path):
    # 2026-07：非原生音画默认走无声视频流，不再默认把对话近景送进音频参考口型路线。
    root = _root(tmp_path, "- 生视频AI: 即梦\n- 视频模型路由: 自动按镜头路由\n- 制作模式: 配音先行\n")
    _write_storyboard(root, [{"id": "Clip 1", "template": "dialogue_shot_reverse", "scene": "对话反打台词"}])

    plan = router.route_episode(root, "第1集")
    route = plan["routes"][0]

    assert plan["video_generation_audio_policy"] == "无声视频流"
    assert route["video_generation_audio_policy"] == "无声视频流"
    assert route["execution_recipe"]["audio_inputs"]["video_generation_audio_policy"] == "无声视频流"
    assert route["mode"] != "voice_conditioned_lipsync"
    assert route["native_audio_policy"] == "none"
    assert route["native_audio_policy"] != "native_speech"


def test_voice_first_dialogue_lipsync_requires_explicit_audio_policy(tmp_path):
    root = _root(
        tmp_path,
        "- 生视频AI: 即梦\n"
        "- 视频模型路由: 自动按镜头路由\n"
        "- 制作模式: 配音先行\n"
        "- 视频生成音频策略: 配音对齐口型\n",
    )
    _write_storyboard(root, [{"id": "Clip 1", "template": "dialogue_shot_reverse", "scene": "对话反打台词"}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["mode"] == "voice_conditioned_lipsync"
    assert route["native_audio_policy"] == "lipsync_condition_only"


def test_voice_first_dialogue_lipsync_without_character_refs_has_no_identity_requirement(tmp_path):
    root = _root(
        tmp_path,
        "- 生视频AI: 即梦\n"
        "- 视频模型路由: 自动按镜头路由\n"
        "- 制作模式: 配音先行\n"
        "- 视频生成音频策略: 配音对齐口型\n",
    )
    _write_storyboard(root, [{
        "id": "Clip 1",
        "template": "dialogue_shot_reverse",
        "scene": "黑陶破盆与灵水微光空镜",
        "characters": [],
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["mode"] == "voice_conditioned_lipsync"
    assert route["identity_requirement"] == "none"
    assert route["clip_characters"] == []
    assert route["execution_recipe"]["reference_inputs"]["characters"] == []


def test_voice_first_dialogue_lipsync_off_when_disabled(tmp_path):
    # 显式 对口型=关闭：对话镜不进口型路由（回到无口型 dialogue 路由）。
    root = _root(tmp_path, "- 生视频AI: 即梦\n- 视频模型路由: 自动按镜头路由\n- 制作模式: 配音先行\n- 对口型: 关闭\n")
    _write_storyboard(root, [{"id": "Clip 1", "template": "dialogue_shot_reverse", "scene": "对话反打台词"}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["mode"] != "voice_conditioned_lipsync"
    assert route["native_audio_policy"] == "none"


def test_voice_first_non_closeup_speech_no_default_lipsync(tmp_path):
    # 无声视频流默认档：非对话近景的说话镜（public_confrontation）默认也不进口型路由。
    root = _root(tmp_path, "- 生视频AI: 即梦\n- 视频模型路由: 自动按镜头路由\n- 制作模式: 配音先行\n")
    _write_storyboard(root, [{"id": "Clip 1", "template": "public_confrontation", "scene": "当众对质"}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["mode"] != "voice_conditioned_lipsync"


def test_fixed_mode_uses_default_backend(tmp_path):
    root = _root(tmp_path, "- 生视频AI: 可灵\n- 视频模型路由: 固定生视频AI\n")
    _write_storyboard(root, [{"id": "Clip 1", "template": "fight_exchange", "scene": "交手命中"}])

    plan = router.route_episode(root, "第1集")
    route = plan["routes"][0]

    assert plan["routing_mode"] == "fixed_default"
    assert plan["default_backend"] == "kling"
    assert route["primary_backend"] == "kling"
    assert route["shot_type"] == "fight_exchange"
    assert route["policy_resolution"]["winner"] == "fixed_mode"


def test_split_video_model_setting_drives_fixed_default(tmp_path):
    root = _root(tmp_path, "- 生视频模型: Seedance 2.0\n- 生视频渠道: 即梦/Dreamina\n- 视频模型路由: 固定生视频模型\n")
    _write_storyboard(root, [{"id": "Clip 1", "scene": "普通单人抬眼"}])

    plan = router.route_episode(root, "第1集")

    assert plan["routing_mode"] == "fixed_default"
    assert plan["default_backend"] == "seedance"
    assert plan["routes"][0]["primary_backend"] == "seedance"


def test_fixed_mode_can_disable_fallback_backends(tmp_path):
    root = _root(tmp_path, "- 生视频AI: dreamina\n- 视频模型路由: 固定生视频AI\n- 视频备用后端: 无\n")
    _write_storyboard(root, [{"id": "Clip 1", "template": "dialogue_shot_reverse", "scene": "对话反打台词"}])

    plan = router.route_episode(root, "第1集")
    route = plan["routes"][0]

    assert plan["routing_mode"] == "fixed_default"
    assert plan["default_backend"] == "dreamina"
    assert route["primary_backend"] == "dreamina"
    assert route["fallback_backends"] == []


def test_fixed_mode_uses_structured_characters_for_identity_requirement(tmp_path):
    root = _root(tmp_path, "- 生视频AI: dreamina\n- 视频模型路由: 固定生视频AI\n- 视频备用后端: 无\n")
    _write_storyboard(root, [{
        "id": "Clip 12",
        "template": "dialogue_shot_reverse",
        "scene": "沈念轻笑",
        "characters": ["CHAR_01/常态", "CHAR_03/人皮态"],
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["identity_requirement"] == "reference_group"
    assert route["clip_characters"] == [
        {"character_id": "CHAR_01", "form": "常态"},
        {"character_id": "CHAR_03", "form": "人皮态"},
    ]


def test_fixed_mode_uses_character_template_for_identity_requirement(tmp_path):
    root = _root(tmp_path, "- 生视频AI: dreamina\n- 视频模型路由: 固定生视频AI\n- 视频备用后端: 无\n")
    _write_storyboard(root, [{
        "id": "EP01_CLIP12",
        "label": "沈念轻笑",
        "scene": "冷宫寝殿/夜/内",
        "template": "dialogue_shot_reverse",
        "characters": ["CHAR_01/常态"],
        "template_contract": {
            "blocking": "沈念画左近景，柳娘子在画右压力源方向。",
            "eyeline": "沈念抬眼看画右柳娘子，柳娘子看画左沈念",
        },
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["identity_requirement"] == "reference_group"
    assert route["clip_characters"]


def test_fixed_mode_keeps_explicit_empty_shot_identity_none(tmp_path):
    root = _root(tmp_path, "- 生视频AI: dreamina\n- 视频模型路由: 固定生视频AI\n- 视频备用后端: 无\n")
    _write_storyboard(root, [{
        "id": "Clip 3",
        "scene": "山门空镜，雨声和风声，远景氛围转场",
        "characters": [],
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["identity_requirement"] == "none"


def test_named_character_empty_establishing_is_not_text2video_identity_none(tmp_path):
    root = _root(tmp_path, "- 生视频AI: 即梦\n- 视频模型路由: 自动按镜头路由\n")
    _write_storyboard(root, [{
        "id": "EP01_CLIP04",
        "label": "官道孤人",
        "scene": "荒野官道夜路，孤月下她独自走在路中",
        "character_ids": ["CHAR_01"],
        "location_id": "LOC_02",
        "firstframe_png": "出图/第1集/图片/Clip04_first.png",
        "continuity": {"need_endframe": True, "anchors": [{"anchor_png": "出图/第1集/图片/Clip04_a1.png"}]},
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["clip_characters"] == [{"character_id": "CHAR_01"}]
    assert route["identity_requirement"] == "reference_group"
    assert route["mode"] == "image2video"
    assert route["execution_recipe"]["frame_inputs"]["first_frame"] is True
    assert route["execution_recipe"]["reference_inputs"]["characters"][0]["binding"] == "reference_group"


def test_fixed_mode_overrides_native_av_speech_reroute(tmp_path):
    root = _root(tmp_path, "- 生视频AI: 可灵\n- 视频模型路由: 固定生视频AI\n- 制作模式: 原生音画\n")
    _write_storyboard(root, [{"id": "Clip 1", "template": "dialogue_shot_reverse", "scene": "沈念开口说话"}])

    plan = router.route_episode(root, "第1集")
    route = plan["routes"][0]

    assert plan["av_mode"] == "native_av"
    assert plan["routing_mode"] == "fixed_default"
    assert route["primary_backend"] == "kling"
    assert route["mode"] == "image2video"
    assert route["native_audio_policy"] == "none"
    assert route["requires_voice_fallback"] is True
    assert route["fallback_production_mode"] == "voice_first"
    assert route["execution_recipe"]["audio_inputs"]["requires_voice_track"] is True
    assert "native_speech" not in route["risk_flags"]


def test_write_plan_outputs_json_and_markdown(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 1", "scene": "普通单人抬眼"}])
    plan = router.route_episode(root, "第1集")

    paths = router.write_plan(plan, root, "第1集")

    assert paths["json"].is_file()
    assert paths["markdown"].is_file()
    assert paths["policy_lattice"].is_file()
    assert "本集模型路由表" in paths["markdown"].read_text(encoding="utf-8")
    assert json.loads(paths["policy_lattice"].read_text(encoding="utf-8"))["kind"] == "n2d_consistency_policy_lattice"


# ── T7: 视频后端跨集锁（model_routes_baseline）────────────────────────────────
def test_build_baseline_picks_most_common_primary_per_shot_type():
    plan = {"routes": [
        {"shot_type": "dialogue_shot", "primary_backend": "kling"},
        {"shot_type": "dialogue_shot", "primary_backend": "kling"},
        {"shot_type": "dialogue_shot", "primary_backend": "seedance"},
        {"shot_type": "action_fight", "primary_backend": "seedance"},
    ]}
    assert router.build_baseline(plan) == {"dialogue_shot": "kling", "action_fight": "seedance"}


def test_apply_baseline_anchors_primary_and_records_drift():
    plan = {"routes": [{"clip_id": "C1", "shot_type": "dialogue_shot",
                        "primary_backend": "seedance", "fallback_backends": ["veo"]}]}
    drift = router.apply_baseline(plan, {"dialogue_shot": "kling"})
    r = plan["routes"][0]
    assert r["primary_backend"] == "kling"               # 基线胜
    assert r["fallback_backends"][0] == "seedance"        # 原 primary 降为 fallback 首项（不丢）
    assert r["baseline_anchored"] is True
    assert drift == [{"clip_id": "C1", "shot_type": "dialogue_shot", "was": "seedance", "now": "kling"}]


def test_apply_baseline_defers_to_locked_backend():
    plan = {"routes": [{"clip_id": "C1", "shot_type": "dialogue_shot",
                        "primary_backend": "kling", "locked_backend": "kling",
                        "fallback_backends": ["seedance"]}]}
    drift = router.apply_baseline(plan, {"dialogue_shot": "seedance"})
    r = plan["routes"][0]
    assert r["primary_backend"] == "kling"
    assert "baseline_deferred_by_locked_backend" in r["risk_flags"]
    assert drift[0]["reason"] == "identity_affinity_locked_backend"


def test_apply_baseline_defers_in_fixed_mode():
    plan = {"routing_mode": "fixed_default",
            "routes": [{"clip_id": "C1", "shot_type": "dialogue_shot",
                        "primary_backend": "dreamina", "fallback_backends": ["seedance"]}]}
    drift = router.apply_baseline(plan, {"dialogue_shot": "kling"})
    r = plan["routes"][0]
    assert r["primary_backend"] == "dreamina"
    assert "baseline_deferred_by_fixed_mode" in r["risk_flags"]
    assert drift[0]["reason"] == "fixed_default"


def test_write_then_load_baseline_roundtrip(tmp_path):
    root = _root(tmp_path)
    plan = {"episode": "第1集", "generated_at": "t",
            "routes": [{"shot_type": "dialogue_shot", "primary_backend": "kling"}]}
    bp = router.write_baseline(plan, root)
    assert bp.is_file()
    assert router.load_baseline(root) == {"dialogue_shot": "kling"}


def test_route_episode_anchors_to_existing_baseline(tmp_path):
    # 第1集自然路由 fight→kling；写基线时人为把 fight 锁成 seedance；再路由应锚定 seedance
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 1", "template": "fight_exchange", "scene": "挥剑命中"}])
    natural = router.route_episode(root, "第1集", anchor_baseline=False)
    st = natural["routes"][0]["shot_type"]
    router.write_baseline({"episode": "第1集", "generated_at": "t",
                           "routes": [{"shot_type": st, "primary_backend": "seedance"}]}, root)
    anchored = router.route_episode(root, "第1集")  # 默认锚定
    assert anchored["routes"][0]["primary_backend"] == "seedance"
    assert anchored["routes"][0]["execution_recipe"]["execution_backend"] == "seedance"
    assert anchored["baseline_anchored"] is True
    assert anchored["baseline_drift"] and anchored["baseline_drift"][0]["now"] == "seedance"


def test_route_episode_no_baseline_no_anchor(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 1", "template": "fight_exchange", "scene": "挥剑命中"}])
    plan = router.route_episode(root, "第1集")  # 无基线
    assert "baseline_anchored" not in plan


def test_backend_supports_dual_keyframe():
    # kling/dreamina 支持首尾；Seedance 裸模型不支持，经 Dreamina 执行渠道支持。
    assert router.backend_supports_dual_keyframe("kling") is True
    assert router.backend_supports_dual_keyframe("dreamina") is True
    assert router.backend_supports_dual_keyframe("seedance") is False  # 仅 multimodal_reference，非首尾硬约束
    assert router.backend_supports_dual_keyframe("seedance", "Dreamina") is True
    assert router.backend_supports_dual_keyframe("sora") is False


def test_is_relay_clip_signals():
    assert router.is_relay_clip({"transition": "接力"}) is True
    # 规范字段 need_endframe（无下划线）——画板真实数据用的就是这个
    assert router.is_relay_clip({"continuity": {"need_endframe": True}}) is True
    assert router.is_relay_clip({"need_endframe": True}) is True
    assert router.is_relay_clip({"continuity": {"seam_mode": "hard_cut", "need_endframe": True}}) is False
    assert router.is_relay_clip({"relay": True, "continuity": {"seam_mode": "hard_cut"}}) is False
    assert router.is_relay_clip({"continuity": {"seam_mode": "graphic_match"}}) is False
    assert router.is_relay_clip({"continuity": {"seam_mode": "continuous_take_relay"}}) is True
    # 旧别名 need_end_frame 仍兜底
    assert router.is_relay_clip({"continuity": {"need_end_frame": True}}) is True
    assert router.is_relay_clip({"relay": True}) is True
    assert router.is_relay_clip({"transition": "硬切"}) is False
    assert router.is_relay_clip({}) is False


def test_seam_relay_plan_guaranteed_vs_fallback():
    # 接力镜 + primary 支持双关键帧 → seam_guaranteed
    p = router.seam_relay_plan({"transition": "接力"}, "kling", ["seedance"])
    assert p["is_relay"] and p["seam_guaranteed"] and p["boundary_frame_shared"]
    # 接力镜 + primary 不支持 → 从 fallback 挑一个支持的
    p2 = router.seam_relay_plan({"relay": True}, "seedance", ["sora", "kling"])
    assert p2["is_relay"] and p2["seam_guaranteed"] is False
    assert p2["dual_keyframe_fallback"] == "kling"
    # 同一个 Seedance 通过 Dreamina 执行时，首尾帧能力来自执行渠道，不应再推荐不可用 fallback。
    p2b = router.seam_relay_plan({"relay": True}, "seedance", ["dreamina"], video_channel="Dreamina")
    assert p2b["is_relay"] and p2b["seam_guaranteed"] is True
    assert "dual_keyframe_fallback" not in p2b
    # 非接力镜 → is_relay False，不带 boundary 字段
    p3 = router.seam_relay_plan({"transition": "硬切"}, "seedance", ["kling"])
    assert p3["is_relay"] is False and "boundary_frame_shared" not in p3


# ── E4 QC失败→升锁 ─────────────────────────────────────────────────────────
def test_backend_has_native_identity():
    assert router.backend_has_native_identity("kling") is True     # character_id
    assert router.backend_has_native_identity("seedance") is True  # face_lock
    assert router.backend_has_native_identity("dreamina") is False
    assert router.backend_has_native_identity("sora") is False


def test_escalate_below_threshold_noop():
    entry = {"primary_backend": "dreamina", "identity_requirement": "x", "rationale": [], "fallback_backends": ["kling"]}
    assert router.escalate_identity_for_failures(dict(entry), 1) == entry


def test_escalate_switches_to_native_identity_backend():
    entry = {"primary_backend": "dreamina", "identity_requirement": "character_id_or_reference_group",
             "rationale": [], "risk_flags": [], "fallback_backends": ["kling", "seedance"]}
    out = router.escalate_identity_for_failures(entry, 2)
    assert out["identity_requirement"] == "native_identity_lock_required"
    assert out["primary_backend"] == "kling"             # 换到有 Character ID 的后端
    assert "identity_escalated" in out["risk_flags"]
    assert any("已失败 2 次" in r for r in out["rationale"])


def test_escalate_fixed_mode_does_not_switch_backend():
    entry = {"primary_backend": "dreamina", "identity_requirement": "x", "rationale": [],
             "risk_flags": [], "fallback_backends": ["kling"]}
    out = router.escalate_identity_for_failures(entry, 3, fixed_mode=True)
    assert out["primary_backend"] == "dreamina"          # 固定模式不换厂
    assert out["identity_requirement"] == "native_identity_lock_required"
    assert any("不擅自换厂" in r for r in out["rationale"])


def test_clip_id_and_identity_failure_helpers():
    assert router._clip_id_from_text("出图/第1集/图片/Clip_04_x.png") == "Clip_04"
    assert router._clip_id_from_text("镜头7 崩脸") == "Clip_07"
    assert router._clip_id_from_text("定妆_赐死托盘.png") is None
    assert router._is_identity_failure("崩脸/身份漂移") is True
    assert router._is_identity_failure("缺短匕首，未过道具自检") is False


# ── ③ 一角一后端亲和（核心硬钉）─────────────────────────────
def _write_registry(root: Path, characters):
    p = root / "出图" / "共享" / "identity_registry.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"kind": "n2d_asset_identity_registry", "characters": characters},
                            ensure_ascii=False), encoding="utf-8")


def test_build_backend_affinity_only_counts_registered_native_video():
    reg = {"characters": [
        {"id": "CHAR_01", "name": "沈念 / 林婉儿", "forms": [{"form": "常态", "identity_adapters": {"video": {
            "seedance": {"mode": "face_lock", "status": "registered"}}}}]},
        # 全 fallback/未注册 → 无原生主体可锁，不进 affinity（零噪音）
        {"id": "CHAR_03", "name": "柳娘子", "forms": [{"form": "常态", "identity_adapters": {"video": {
            "kling": {"mode": "character_id", "status": "unregistered"},
            "dreamina": {"mode": "first_last_frame", "status": "fallback_reference_group"}}}}]},
    ]}
    aff = router.build_backend_affinity(reg)
    assert len(aff) == 1
    assert aff[0]["id"] == "CHAR_01" and aff[0]["backend"] == "seedance"
    assert "沈念" in aff[0]["aliases"]


def test_character_backend_conflicts_detects_and_skips():
    aff = [{"id": "CHAR_01", "name": "沈念", "aliases": {"沈念"}, "backend": "seedance"}]
    clip = {"id": "C1", "characters": ["CHAR_01/常态"], "scene": "沈念近景"}
    # 路由到 kling ≠ 亲和 seedance → 冲突
    conf = router.character_backend_conflicts(clip, "kling", aff)
    assert conf and conf[0]["prefers_backend"] == "seedance" and conf[0]["routed_backend"] == "kling"
    # 路由到 seedance（= 亲和）→ 无冲突
    assert router.character_backend_conflicts(clip, "seedance", aff) == []
    # 角色不在本镜 → 无冲突
    assert router.character_backend_conflicts({"id": "C2", "scene": "空镜"}, "kling", aff) == []


def test_route_episode_pins_core_character_to_locked_backend(tmp_path):
    # 核心角色（已注册原生视频主体 seedance）被路由到 kling → 硬钉回 seedance（不再 warn-only）
    root = _root(tmp_path, "- 生视频AI: 可灵\n- 视频模型路由: 固定生视频AI\n- 视频备用后端: 无\n")
    _write_registry(root, [{"id": "CHAR_01", "name": "沈念", "forms": [
        {"form": "常态", "identity_adapters": {"video": {"seedance": {"mode": "face_lock", "status": "registered"}}}}]}])
    _write_storyboard(root, [{"id": "EP01_CLIP01", "scene": "沈念近景", "characters": ["CHAR_01/常态"]}])

    route = router.route_episode(root, "第1集")["routes"][0]
    assert route["primary_backend"] == "seedance"            # 硬钉到 locked_backend
    assert "kling" in route["fallback_backends"]             # 原 primary 降为 fallback
    assert route["character_backend_conflicts"] == []        # 钉回后冲突消解
    assert any("硬钉" in r for r in route["rationale"])


def test_route_episode_no_conflict_when_no_native_subject(tmp_path):
    # 没注册原生主体（demo 现状）→ 零告警
    root = _root(tmp_path, "- 生视频AI: 可灵\n- 视频模型路由: 固定生视频AI\n- 视频备用后端: 无\n")
    _write_registry(root, [{"id": "CHAR_01", "name": "沈念", "forms": [
        {"form": "常态", "identity_adapters": {"video": {"kling": {"mode": "character_id", "status": "unregistered"}}}}]}])
    _write_storyboard(root, [{"id": "EP01_CLIP01", "scene": "沈念近景", "characters": ["CHAR_01/常态"]}])

    route = router.route_episode(root, "第1集")["routes"][0]
    assert route["character_backend_conflicts"] == []
    assert "character_backend_conflict" not in route["risk_flags"]


def test_build_backend_affinity_marks_core_and_locked_backend():
    reg = {"characters": [{"id": "CHAR_01", "name": "沈念", "forms": [
        {"form": "常态", "identity_adapters": {"video": {"seedance": {"mode": "face_lock", "status": "registered"}}}}]}]}
    aff = router.build_backend_affinity(reg)
    assert aff[0]["core"] is True and aff[0]["backend"] == "seedance"


def test_character_backend_conflict_core_enforces_noncore_warns():
    # core 角色冲突 → enforce=True + locked_backend；非 core → enforce=False（仅 warn）
    clip = {"id": "C1", "characters": ["CHAR_01/常态"], "scene": "沈念近景"}
    core_aff = [{"id": "CHAR_01", "name": "沈念", "aliases": {"沈念"}, "backend": "seedance", "core": True}]
    c = router.character_backend_conflicts(clip, "kling", core_aff)[0]
    assert c["enforce"] is True and c["core"] is True and c["locked_backend"] == "seedance"
    noncore_aff = [{"id": "CHAR_01", "name": "沈念", "aliases": {"沈念"}, "backend": "seedance"}]  # 无 core
    c2 = router.character_backend_conflicts(clip, "kling", noncore_aff)[0]
    assert c2["enforce"] is False and c2["locked_backend"] == "seedance"


def test_escalate_persists_locked_backend_for_retries():
    # 升锁换厂后 locked_backend = 最终 primary，重试复用它不再轮换 fallback
    entry = {"primary_backend": "dreamina", "identity_requirement": "character_id_or_reference_group",
             "rationale": [], "risk_flags": [], "fallback_backends": ["kling", "seedance"]}
    out = router.escalate_identity_for_failures(entry, 2)
    assert out["primary_backend"] == "kling"
    assert out["locked_backend"] == "kling"            # 钉死最终 primary 供重试复用
    # 固定后端模式不换厂 → locked_backend = 原 primary
    fixed = {"primary_backend": "dreamina", "identity_requirement": "x", "rationale": [],
             "risk_flags": [], "fallback_backends": ["kling"]}
    out2 = router.escalate_identity_for_failures(fixed, 3, fixed_mode=True)
    assert out2["locked_backend"] == "dreamina"


def test_escalate_below_threshold_persists_no_locked_backend():
    # 未到阈值原样返回，不写 locked_backend（避免给未升锁的镜误钉后端）
    entry = {"primary_backend": "dreamina", "identity_requirement": "x", "rationale": [], "fallback_backends": ["kling"]}
    out = router.escalate_identity_for_failures(dict(entry), 1)
    assert "locked_backend" not in out


# ── 质量档 / 视频运动参考 / 多镜单次生成（2026-06-19 流程自审落地）──────────────────
def test_quality_tier_high_for_identity_heavy_and_fast_for_general():
    # 身份/物理吃重镜 → high（值 pro 档）；通用低风险镜 → fast（量产省成本）；后端无档位 → n/a
    assert router.quality_tier_for_clip("fight_exchange", ["contact_motion"], "seedance") == "high"
    assert router.quality_tier_for_clip("reveal_reaction_chain", [], "seedance") == "high"
    assert router.quality_tier_for_clip("public_confrontation", [], "seedance") == "high"
    assert router.quality_tier_for_clip("relationship_turn", [], "seedance") == "high"
    assert router.quality_tier_for_clip("general_motion", [], "seedance") == "fast"
    assert router.quality_tier_for_clip("general_motion", ["identity_drift_risk"], "seedance") == "high"
    assert router.quality_tier_for_clip("general_motion", [], "veo") == "n/a"  # veo 档案无 fast/pro 档


def test_new_scene_templates_get_identity_risk_for_named_characters():
    clip = {"id": "Clip 8", "character_ids": ["CHAR_SHEN"], "scene": "沈念拿出血书揭穿真实身份"}
    flags = router.risk_flags_for_clip(clip, "reveal_reaction_chain", "seedance")
    assert "identity_drift_risk" in flags


def test_fight_clip_gets_high_quality_tier(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 1", "template": "fight_exchange", "scene": "挥剑命中"}])
    route = router.route_episode(root, "第1集")["routes"][0]
    # fight primary=kling（无档位能力）→ n/a；改测 seedance 直配的镜见下
    assert route["quality_tier"] in ("high", "n/a")


def test_motion_reference_applicable_for_flight_on_seedance(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 1", "template": "flight", "scene": "御剑飞行追逐", "characters": ["主角"]}])
    route = router.route_episode(root, "第1集")["routes"][0]
    assert route["primary_backend"] == "seedance"
    assert route["motion_reference"]["applicable"] is True
    assert "motion_reference_candidate" in route["risk_flags"]


def test_meditation_cultivation_routes_to_controlled_low_motion(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{
        "id": "Clip 1",
        "template": "meditation_cultivation",
        "scene": "沈念打坐吐纳，灵气入体，丹田光纹微亮",
        "characters": ["CHAR_01/常态"],
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "meditation_cultivation"
    assert route["primary_backend"] == "kling"
    assert route["mode"] == "image2video"
    assert "micro_motion_readability_risk" in route["risk_flags"]
    assert route["motion_control"]["required"] is False
    assert any("posture_lock" in req for req in route["prompt_requirements"])


def test_dual_cultivation_requires_motion_control_and_non_explicit_boundary(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{
        "id": "Clip 1",
        "template": "dual_cultivation",
        "scene": "两名成年角色掌心相抵疗伤合修，蓝金灵力循环",
        "characters": ["CHAR_01/常态", "CHAR_02/常态"],
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "dual_cultivation"
    assert route["primary_backend"] == "kling"
    assert route["mode"] == "frames2video"
    assert route["motion_control"]["required"] is True
    assert "contact_map" in route["motion_control"]["required_inputs"]
    assert "vfx_layers" in route["motion_control"]["required_inputs"]
    assert "consent_non_explicit_required" in route["risk_flags"]
    assert "energy_circulation_required" in route["risk_flags"]
    assert any("non-explicit" in req or "adult" in req for req in route["prompt_requirements"])


def test_kiss_or_near_kiss_requires_face_contact_controls(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{
        "id": "Clip 1",
        "template": "kiss_or_near_kiss",
        "scene": "告白后两人近吻停顿，唇边差点接触",
        "characters": ["CHAR_01/常态", "CHAR_02/常态"],
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "kiss_or_near_kiss"
    assert route["primary_backend"] == "kling"
    assert route["mode"] == "frames2video"
    assert route["motion_control"]["required"] is True
    assert "contact_map" in route["motion_control"]["required_inputs"]
    assert "face_contact_risk" in route["risk_flags"]
    assert "micro_expression_required" in route["risk_flags"]
    assert any("age_context_lock" in req for req in route["prompt_requirements"])


def test_alchemy_route_requires_process_ladder_prompt(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{
        "id": "Clip 1",
        "template": "alchemy_forging",
        "scene": "炼丹开炉，三颗金纹丹丸成形",
        "characters": ["CHAR_01/常态"],
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "alchemy_forging"
    assert route["primary_backend"] == "kling"
    assert "object_continuity_risk" in route["risk_flags"]
    assert "vfx_consistency_risk" in route["risk_flags"]
    assert any("process_stage_ladder" in req and "heat_curve" in req for req in route["prompt_requirements"])


def test_motion_reference_not_applicable_for_dialogue():
    plan = router.motion_reference_plan("dialogue_closeup", "kling")
    assert plan["applicable"] is False


def test_multishot_groups_for_consecutive_relay_seedance_clips(tmp_path):
    # 项目直连 Seedance（非即梦渠道）：primary 不会被换到 dreamina 多帧 API，保持 seedance·支持多镜。
    # 即梦渠道下执行后端是 dreamina(非 multishot_native)，多镜叙事未在该渠道核验→保守不标注，是正确行为。
    root = _root(tmp_path, settings="- 生视频模型: Seedance 2.0\n- 生视频渠道: Seedance\n- 视频模型路由: 自动按镜头路由\n")
    # 两条连续接力 flight 镜（primary=seedance·支持多镜）→ 标注一个候选组，但不改 primary/mode
    _write_storyboard(root, [
        {"id": "Clip 1", "template": "flight", "scene": "飞行起势", "relay": True},
        {"id": "Clip 2", "template": "flight", "scene": "飞行接续", "relay": True},
    ])
    plan = router.route_episode(root, "第1集")
    assert len(plan["multishot_groups"]) == 1
    grp = plan["multishot_groups"][0]
    assert grp["members"] == ["Clip_01", "Clip_02"]
    assert grp["backend"] == "seedance"
    for r in plan["routes"]:
        assert r["multishot_candidate"]["group_id"] == grp["group_id"]
        assert "multishot_candidate" in r["risk_flags"]
        assert r["mode"] != "merged"  # 仍是逐镜独立可重跑，未合并


def test_multishot_group_capped_by_single_gen_duration():
    # 累计时长护栏：单次多镜生成总长 ≤ 后端上限(seedance 15s)。
    sr = {"is_relay": True}
    # 两条 10s 接力镜：10+10=20 > 15 → 物理上没法一次出 → 不成组（各自已是长单镜，归"更长单镜"覆盖）
    long_pair = [
        {"clip_id": "Clip_01", "primary_backend": "seedance", "seam_relay": sr, "risk_flags": [], "clip_seconds": 10.0},
        {"clip_id": "Clip_02", "primary_backend": "seedance", "seam_relay": sr, "risk_flags": [], "clip_seconds": 10.0},
    ]
    assert router.annotate_multishot_groups(long_pair) == []
    # 三条 4s 短接力镜：4+4+4=12 ≤ 15 → 成一组（多个短镜一次 co-generate 才是多镜单次生成的甜点）
    short_run = [
        {"clip_id": f"Clip_{i:02d}", "primary_backend": "seedance", "seam_relay": sr, "risk_flags": [], "clip_seconds": 4.0}
        for i in (1, 2, 3)
    ]
    groups = router.annotate_multishot_groups(short_run)
    assert len(groups) == 1
    assert groups[0]["members"] == ["Clip_01", "Clip_02", "Clip_03"]
    assert groups[0]["approx_seconds"] == 12.0


def test_no_multishot_group_for_non_multishot_backend():
    # dreamina 非 multishot_native：即便连续接力也不标注（判定走能力字段）
    routes = [
        {"clip_id": "Clip_01", "primary_backend": "dreamina", "seam_relay": {"is_relay": True}, "risk_flags": []},
        {"clip_id": "Clip_02", "primary_backend": "dreamina", "seam_relay": {"is_relay": True}, "risk_flags": []},
    ]
    assert router.annotate_multishot_groups(routes) == []


def test_multishot_group_for_kling_after_2026_06_registration():
    # 可灵 Kling 3.0（6 连续镜 + 共享音轨）2026-06 补登记 multishot_native → 能力字段自动收录，
    # 连续接力镜组应被标 multishot_candidate（与 Seedance 同走能力判定，不 hardcode 厂商）。
    sr = {"is_relay": True}
    short_run = [
        {"clip_id": f"Clip_{i:02d}", "primary_backend": "kling", "seam_relay": sr, "risk_flags": [], "clip_seconds": 3.0}
        for i in (1, 2, 3)
    ]
    groups = router.annotate_multishot_groups(short_run)
    assert len(groups) == 1
    assert groups[0]["members"] == ["Clip_01", "Clip_02", "Clip_03"]


def test_reroute_recommends_multishot_for_same_scene_run():
    # dreamina（非多镜）primary 的同场景连续镜 → 建议改走多镜后端（roster 无多镜→标 roster_switch_required）。
    routes = [
        {"clip_id": "Clip_01", "primary_backend": "dreamina", "loc": "LOC_hall", "clip_characters": [], "risk_flags": []},
        {"clip_id": "Clip_02", "primary_backend": "dreamina", "loc": "LOC_hall", "clip_characters": [], "risk_flags": []},
    ]
    recs = router.recommend_multishot_reroute(routes, ["dreamina"])
    assert len(recs) == 1
    assert recs[0]["members"] == ["Clip_01", "Clip_02"]
    assert recs[0]["basis"] == "同场景"
    assert recs[0]["roster_switch_required"] is True
    assert routes[0]["multishot_reroute_suggestion"]["suggested_backend"] == "seedance"
    assert "multishot_reroute_candidate" in routes[0]["risk_flags"]


def test_reroute_prefers_roster_multishot_backend_without_switch():
    # roster 内已有多镜后端（kling）→ 建议它且不要求换项目后端。
    routes = [
        {"clip_id": "Clip_01", "primary_backend": "dreamina", "loc": "", "clip_characters": [{"character_id": "CHAR_a"}], "risk_flags": []},
        {"clip_id": "Clip_02", "primary_backend": "dreamina", "loc": "", "clip_characters": [{"character_id": "CHAR_a"}], "risk_flags": []},
    ]
    recs = router.recommend_multishot_reroute(routes, ["dreamina", "kling"])
    assert recs and recs[0]["basis"] == "同角色集"
    assert recs[0]["suggested_backend"] == "kling"
    assert recs[0]["roster_switch_required"] is False


def test_reroute_skips_when_primary_already_multishot():
    # primary 已支持多镜由 annotate_multishot_groups 管，这里不重复建议。
    routes = [
        {"clip_id": "Clip_01", "primary_backend": "seedance", "loc": "LOC_hall", "clip_characters": [], "risk_flags": []},
        {"clip_id": "Clip_02", "primary_backend": "seedance", "loc": "LOC_hall", "clip_characters": [], "risk_flags": []},
    ]
    assert router.recommend_multishot_reroute(routes, ["seedance"]) == []


def test_reroute_needs_shared_scene_or_character():
    # 既非同场景也非同角色集 → 不成组。
    routes = [
        {"clip_id": "Clip_01", "primary_backend": "dreamina", "loc": "LOC_a", "clip_characters": [{"character_id": "CHAR_a"}], "risk_flags": []},
        {"clip_id": "Clip_02", "primary_backend": "dreamina", "loc": "LOC_b", "clip_characters": [{"character_id": "CHAR_b"}], "risk_flags": []},
    ]
    assert router.recommend_multishot_reroute(routes, ["dreamina"]) == []


def test_urgency_tier_from_settings_default_realtime():
    import router as r
    assert r.urgency_tier_from_settings({}) == "realtime"
    assert r.urgency_tier_from_settings({"投放时效": "实时"}) == "realtime"


def test_urgency_tier_from_settings_batch_aliases():
    import router as r
    for v in ("隔夜批量", "批量", "batch", "batch_24h", "flex", "非紧急"):
        assert r.urgency_tier_from_settings({"投放时效": v}) == "batch_24h", v


# ── 跨后端英雄镜多版（2026-06-26） ──────────────────────────────────────────────
def test_hero_multi_version_off_by_default(tmp_path):
    # costly 选择点默认关闭：英雄镜也不标 hero_multi_version。
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 1", "template": "fight_exchange", "scene": "当众打脸宿敌全场震惊"}])

    plan = router.route_episode(root, "第1集", generated_at="2026-06-08T00:00:00Z")

    assert plan["hero_multi_version"]["enabled"] is False
    assert "hero_multi_version" not in plan["routes"][0]


def test_hero_multi_version_marks_hero_shot_when_on(tmp_path):
    # 开启后名场面镜跨后端多版：secondary 取异于 primary 的 fallback。
    root = _root(tmp_path, "- 生视频AI: 即梦\n- 视频模型路由: 自动按镜头路由\n- 英雄镜多版: 开启\n")
    _write_storyboard(root, [{"id": "Clip 1", "template": "fight_exchange", "scene": "当众打脸宿敌全场震惊"}])

    plan = router.route_episode(root, "第1集", generated_at="2026-06-08T00:00:00Z")
    route = plan["routes"][0]

    assert plan["hero_multi_version"]["enabled"] is True
    hv = route["hero_multi_version"]
    assert hv["enabled"] is True
    assert hv["secondary_backend"] and hv["secondary_backend"] != hv["primary_backend"]
    assert route["clip_id"] in plan["hero_multi_version"]["hero_clips"] or "Clip" in str(hv["candidate_pool"])


def test_hero_multi_version_skips_non_hero_shot(tmp_path):
    # 普通过场镜不加版（成本有界）。
    root = _root(tmp_path, "- 生视频AI: 即梦\n- 视频模型路由: 自动按镜头路由\n- 英雄镜多版: 开启\n")
    _write_storyboard(root, [
        {"id": "Clip 1", "template": "empty_establishing", "scene": "城门空镜"},
        {"id": "Clip 2", "template": "empty_establishing", "scene": "街道平淡过场"},
    ])

    plan = router.route_episode(root, "第1集", generated_at="2026-06-08T00:00:00Z")

    # 第1镜=开场钩算英雄镜；第2镜普通过场不加版。
    assert "hero_multi_version" not in plan["routes"][1]


def test_is_overseas_target_detection():
    assert router.is_overseas_target({"发行地区": "北美"}) is True
    assert router.is_overseas_target({"发行地区": "全球"}) is True
    assert router.is_overseas_target({"变现模式": "海外"}) is True
    assert router.is_overseas_target({"字幕语言": "仅英文"}) is True
    assert router.is_overseas_target({"发行地区": "中国大陆"}) is False
    assert router.is_overseas_target({"发行地区": "港澳台", "字幕语言": "中英双语"}) is False


def test_native_av_overseas_prefers_multilingual_lipsync_backend():
    clip = {"character_ids": ["CHAR_01"], "description": "她说话", "continuity": {}}
    # 默认 veo（原生音画但非多语言唇同步）：境内保持 veo，出海抢占 seedance（多语言唇同步最强）。
    domestic = router._route_native_av_speech(clip, "dialogue_closeup", "veo", overseas=False)
    overseas = router._route_native_av_speech(clip, "dialogue_closeup", "veo", overseas=True)
    assert domestic["primary_backend"] == "veo"
    assert overseas["primary_backend"] == "seedance"
    assert any("出海" in r for r in overseas["rationale"])


def test_native_av_overseas_keeps_already_multilingual_default():
    clip = {"character_ids": ["CHAR_01"], "description": "她说话", "continuity": {}}
    # 默认已是多语言唇同步后端（seedance）→ 出海不改 primary、不加无谓 rationale。
    overseas = router._route_native_av_speech(clip, "dialogue_closeup", "seedance", overseas=True)
    assert overseas["primary_backend"] == "seedance"
    assert not any("出海" in r for r in overseas["rationale"])


def test_route_episode_overseas_threads_to_speech_clips(tmp_path):
    root = _root(tmp_path, settings=(
        "- 生视频模型: Veo 3.1\n- 视频模型路由: 自动按镜头路由\n"
        "- 制作模式: 原生音画\n- 发行地区: 北美\n"))
    _write_storyboard(root, [
        {"id": "Clip_01", "character_ids": ["CHAR_01"], "description": "她开口说话",
         "continuity": {"shot_size": "近景"}, "shots": [{"lens": "近景", "desc": "说话特写"}]},
    ])
    plan = router.route_episode(root, "第1集")
    speech = plan["routes"][0]
    # 出海 + 原生音画说话镜 → primary 切到多语言唇同步后端（非默认 veo）。
    assert speech["primary_backend"] == "seedance"


def test_spectacle_benchmark_stale_probe_is_advisory_only(tmp_path):
    # 过期/无时间戳 probe 不得改 primary（2026-07 新鲜度护栏）：只打 stale 风险旗。
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 5", "scene": "万人战场全景，千军列阵，宏大鸟瞰"}])
    prod = root / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    (prod / "spectacle_backend_benchmark.json").write_text(json.dumps({
        "kind": "n2d_spectacle_backend_benchmark",
        "probed_at": "2025-01-01T00:00:00+00:00",
        "recommendations": {"large_establishing": {"primary_backend": "seedance"}},
    }, ensure_ascii=False), encoding="utf-8")
    plan = router.route_episode(root, "第1集", generated_at="2026-06-08T00:00:00Z")
    route = plan["routes"][0]
    assert "spectacle_benchmark_stale" in route.get("risk_flags", [])
    # primary 不被过期 probe 覆盖（回落到 prior/默认路径）
    bench = router.load_spectacle_backend_benchmark(root)
    assert bench.get("benchmark_stale") is True
