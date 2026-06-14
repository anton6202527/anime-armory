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


def test_flight_routes_to_seedance(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 2", "template": "flight", "scene": "御剑飞行，云层向后高速流动"}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "flight"
    assert route["primary_backend"] == "seedance"
    assert route["identity_requirement"] in ("none", "face_lock_or_reference_group")
    assert route["max_clip_seconds"] == 15


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


def test_ensemble_blocking_routes_to_sora(tmp_path):
    # 群像(ensemble) → Sora primary（2026：Sora 2 对 5+/群像最稳，超 Kling 2-3 张脸上限）
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 5", "template": "ensemble_blocking", "scene": "宗门大殿群像站位，门徒队列围住主角"}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "ensemble_blocking"
    assert route["primary_backend"] == "sora"
    assert "kling" in route["fallback_backends"]
    assert "multi_person" in route["risk_flags"]


def test_five_plus_same_frame_routes_to_sora(tmp_path):
    root = _root(tmp_path)
    _write_storyboard(root, [{"id": "Clip 6", "template": "multi_character_same_frame",
                              "scene": "六人对峙同框",
                              "template_contract": {"character_slots": {"A": "", "B": "", "C": "", "D": "", "E": "", "F": ""}}}])
    route = router.route_episode(root, "第1集")["routes"][0]
    assert route["primary_backend"] == "sora"


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
    assert "native_speech" in route["risk_flags"]


def test_native_av_mode_leaves_action_shots_unchanged(tmp_path):
    root = _root(tmp_path, "- 生视频AI: 即梦\n- 视频模型路由: 自动按镜头路由\n- 制作模式: 原生音画\n")
    _write_storyboard(root, [{"id": "Clip 1", "template": "fight_exchange", "scene": "挥剑命中追兵"}])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["shot_type"] == "fight_exchange"
    assert route["primary_backend"] == "kling"
    assert route["native_audio_policy"] == "none"


def test_voice_first_mode_keeps_dialogue_no_native_speech(tmp_path):
    # 默认配音先行：对话镜仍不让视频后端生成台词。
    root = _root(tmp_path)
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


def test_fixed_mode_uses_character_template_for_identity_requirement(tmp_path):
    root = _root(tmp_path, "- 生视频AI: dreamina\n- 视频模型路由: 固定生视频AI\n- 视频备用后端: 无\n")
    _write_storyboard(root, [{
        "id": "EP01_CLIP12",
        "label": "沈念轻笑",
        "scene": "冷宫寝殿/夜/内",
        "template": "dialogue_shot_reverse",
        "template_contract": {
            "blocking": "沈念画左近景，柳娘子在画右压力源方向。",
            "eyeline": "沈念抬眼看画右柳娘子，柳娘子看画左沈念",
        },
    }])

    route = router.route_episode(root, "第1集")["routes"][0]

    assert route["identity_requirement"] == "reference_group"


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
