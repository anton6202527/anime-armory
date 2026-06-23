import json
from pathlib import Path

import router


def _root(tmp_path, settings="- 生视频AI: 即梦\n- 视频模型路由: 自动按镜头路由\n"):
    root = tmp_path / "制漫剧" / "测试剧"
    (root / "脚本" / "第1集").mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n" + settings, encoding="utf-8")
    return root


def _write_storyboard(root: Path, clips):
    p = root / "脚本" / "第1集" / "storyboard.json"
    p.write_text(json.dumps({"episode": 1, "clips": clips}, ensure_ascii=False), encoding="utf-8")
    return p


def test_fight_routes_to_kling_with_seedance_fallback(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 1", "template": "fight_exchange", "scene": "王敦挥剑命中追兵"}])

    plan = router.route_episode(root, "第1集", generated_at="2026-06-08T00:00:00Z")

    route = plan["routes"][0]
    assert route["shot_type"] == "fight_exchange"
    assert route["primary_backend"] == "kling"
    assert "seedance" in route["fallback_backends"]
    assert route["mode"] == "frames2video"
    assert route["motion_control"]["level"] == "required"
    assert route["motion_control"]["manifest_required"] is True
    assert "pose_sequence" in route["motion_control"]["required_inputs"]
    assert route["motion_control"]["manifest_path"].endswith("出视频/第1集/control/Clip_01/motion_control_manifest.json")
    assert route["action_choreography"]["required"] is True
    assert "impact_frame" in route["action_choreography"]["required_fields"]
    assert "action_choreography_required" in route["risk_flags"]
    recipe = route["execution_recipe"]
    assert recipe["execution_backend"] == route["primary_backend"]
    assert recipe["frame_inputs"]["consumption_mode"] == "first_frame"
    assert recipe["reference_inputs"]["motion_reference"]["library_path"] == "生产数据/motion_reference_library.json"
    assert recipe["control_inputs"]["required"] is True
    assert "pose_sequence" in recipe["control_inputs"]["required_inputs"]
    assert recipe["control_inputs"]["manifest_path"].endswith("出视频/第1集/control/Clip_01/motion_control_manifest.json")
    assert recipe["fallback"]["fallback_backends"] == route["fallback_backends"]


def test_spectacle_backend_benchmark_can_override_auto_route(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 1", "template": "fight_exchange", "scene": "王敦挥剑命中追兵"}])
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    (prod / "spectacle_backend_benchmark.json").write_text(json.dumps({
        "kind": "n2d_spectacle_backend_benchmark",
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
    assert route["fallback_backends"][0] == "kling"
    assert route["max_clip_seconds"] == 15
    assert any("执行渠道" in item and "多关键帧" in item for item in route["rationale"])


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
    root = _root(tmp_path, "- 生视频AI: 即梦\n- 视频原生音轨: 低音量混入环境声\n")
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


def test_native_av_mode_leaves_action_shots_unchanged(tmp_path):
    root = _root(tmp_path, "- 生视频AI: 即梦\n- 视频模型路由: 自动按镜头路由\n- 制作模式: 原生音画\n")
    _write_storyboard(root, [{"id": "Clip 1", "template": "fight_exchange", "scene": "挥剑命中追兵"}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "fight_exchange"
    assert route["primary_backend"] == "kling"
    assert route["native_audio_policy"] == "none"


def test_voice_first_mode_keeps_dialogue_no_native_speech(tmp_path):
    # 显式配音先行：对话镜仍不让视频后端生成台词。
    root = _root(tmp_path, "- 生视频AI: 即梦\n- 视频模型路由: 自动按镜头路由\n- 制作模式: 配音先行\n")
    _write_storyboard(root, [{"id": "Clip 1", "template": "dialogue_shot_reverse", "scene": "对话反打台词"}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["mode"] != "native_av"
    assert route["native_audio_policy"] == "none"


def test_fixed_mode_uses_default_backend(tmp_path):
    root = _root(tmp_path, "- 生视频AI: 可灵\n- 视频模型路由: 固定生视频AI\n")
    _write_storyboard(root, [{"id": "Clip 1", "template": "fight_exchange", "scene": "交手命中"}])

    plan = router.route_episode(root, "第1集")
    route = plan["routes"][0]

    assert plan["routing_mode"] == "fixed_default"
    assert plan["default_backend"] == "kling"
    assert route["primary_backend"] == "kling"
    assert route["shot_type"] == "fight_exchange"


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
    assert "native_speech" not in route["risk_flags"]


def test_write_plan_outputs_json_and_markdown(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 1", "scene": "普通单人抬眼"}])
    plan = router.route_episode(root, "第1集")

    paths = router.write_plan(plan, root, "第1集")

    assert paths["json"].is_file()
    assert paths["markdown"].is_file()
    assert "本集模型路由表" in paths["markdown"].read_text(encoding="utf-8")


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
    # kling/dreamina/seedance 带 first_last_frame 或 native_multiframe → True
    assert router.backend_supports_dual_keyframe("kling") is True
    assert router.backend_supports_dual_keyframe("dreamina") is True
    assert router.backend_supports_dual_keyframe("seedance") is False  # 仅 multimodal_reference，非首尾硬约束
    assert router.backend_supports_dual_keyframe("sora") is False


def test_is_relay_clip_signals():
    assert router.is_relay_clip({"transition": "接力"}) is True
    # 规范字段 need_endframe（无下划线）——画板真实数据用的就是这个
    assert router.is_relay_clip({"continuity": {"need_endframe": True}}) is True
    assert router.is_relay_clip({"need_endframe": True}) is True
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
