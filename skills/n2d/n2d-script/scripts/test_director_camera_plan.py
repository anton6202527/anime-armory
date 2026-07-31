"""cd skills/n2d/n2d-script/scripts && python -m pytest test_director_camera_plan.py"""
import json
import datetime as dt

import director_camera_plan as dcp


def _clip(shot="MS 中景", rhythm="", camera="", template="", expression_span=""):
    clip = {
        "clip_id": "Clip_X",
        "rhythm": rhythm,
        "template": template,
        "continuity": {"shot_size": shot},
    }
    if camera:
        clip["camera_motion"] = camera
    if expression_span:
        clip["continuity"]["expression_span"] = expression_span
    return clip


def test_missing_camera_gets_prompt_injections():
    plan = dcp.build_plan({"clips": [_clip("ELS 定场", rhythm="铺垫·压迫")]}, "第1集")
    clip = plan["clips"][0]

    assert plan["summary"]["camera_move_missing"] == 1
    assert clip["findings"][0]["code"] == "camera_move_missing"
    assert "起幅·运动余量" in clip["image_prompt_injection"]
    assert "镜头运动" in clip["video_prompt_injection"]
    assert clip["recommended"]["camera_move_zh"] == "固定机位"
    assert "摄影机保持完全静止" in clip["video_prompt_injection"]["镜头运动"]


def test_unstructured_camera_is_warned():
    clip = _clip("CU 特写", rhythm="反转·打脸", camera="镜头慢慢靠近她然后停下")
    out = dcp.analyze_clip(clip, 1)
    codes = {f["code"] for f in out["findings"]}

    assert "camera_move_unstructured" in codes
    assert out["recommended"]["camera_move_zh"] == "固定机位"


def test_static_camera_is_recognized():
    clip = _clip("MCU 中近景", template="dialogue_shot_reverse", camera="固定机位，轻微呼吸式微动")
    out = dcp.analyze_clip(clip, 1)
    codes = {f["code"] for f in out["findings"]}

    assert "camera_move_unstructured" not in codes
    assert "camera_speed_missing" not in codes
    assert out["normalized_camera"]["is_static"] is True


def test_overactive_closeup_is_warned():
    clip = _clip("CU 特写", rhythm="高潮·觉醒", camera="360 旋转环绕飞行，急速拉近", expression_span="大")
    out = dcp.analyze_clip(clip, 1)
    codes = {f["code"] for f in out["findings"]}

    assert "overactive_closeup" in codes
    assert out["recommended"]["camera_move_zh"] == "固定机位"
    assert out["recommended"]["speed"] == "静止"


def test_write_plan_creates_sidecars(tmp_path):
    root = tmp_path / "作品"
    ep_dir = root / "脚本" / "第1集"
    ep_dir.mkdir(parents=True)
    (ep_dir / "storyboard.json").write_text(
        json.dumps({"clips": [_clip(camera="缓慢推近至 MCU")]}, ensure_ascii=False),
        encoding="utf-8",
    )

    rc = dcp.main([str(root), "第1集", "--write"])

    assert rc == 0
    data = json.loads((root / "生产数据" / "director_camera_plan_第1集.json").read_text(encoding="utf-8"))
    md = (root / "生产数据" / "director_camera_plan_第1集.md").read_text(encoding="utf-8")
    assert data["kind"] == "n2d_director_camera_plan"
    assert "视频注入" in md


def test_backend_control_uses_kling_motion_brush_when_evidence_is_fresh(tmp_path):
    root = tmp_path / "作品"
    ep_dir = root / "脚本" / "第1集"
    route_dir = root / "出视频" / "第1集" / "prompt"
    ep_dir.mkdir(parents=True)
    route_dir.mkdir(parents=True)
    clip = _clip(camera="快速跟拍", template="fight_exchange", rhythm="高潮·爽点")
    clip["clip_id"] = "Clip_01"
    (ep_dir / "storyboard.json").write_text(json.dumps({"clips": [clip]}, ensure_ascii=False), encoding="utf-8")
    (route_dir / "video_model_routes.json").write_text(json.dumps({
        "routes": [{"clip_id": "Clip_01", "primary_backend": "Kling 3.0"}],
    }, ensure_ascii=False), encoding="utf-8")
    dcp.video_backend_adapter.write_refresh_evidence(
        str(root),
        "Kling 3.0",
        sources=["Kling API docs"],
        evidence_kind="official_docs",
        note="motion brush verified",
        today=dt.date.today().isoformat(),
    )

    plan = dcp.build_plan(json.loads((ep_dir / "storyboard.json").read_text(encoding="utf-8")), "第1集", str(root))
    out = plan["clips"][0]

    assert out["backend_control"]["control_idiom"] == "motion_brush_on_firstframe"
    assert "motion brush" in out["video_prompt_injection"]["后端控制写法"]


def test_backend_control_degrades_to_natural_language_without_evidence(tmp_path):
    root = tmp_path / "作品"
    route_dir = root / "出视频" / "第1集" / "prompt"
    route_dir.mkdir(parents=True)
    clip = _clip(camera="快速跟拍")
    clip["clip_id"] = "Clip_01"
    (route_dir / "video_model_routes.json").write_text(json.dumps({
        "routes": [{"clip_id": "Clip_01", "primary_backend": "Kling 3.0"}],
    }, ensure_ascii=False), encoding="utf-8")

    plan = dcp.build_plan({"clips": [clip]}, "第1集", str(root))

    assert plan["clips"][0]["backend_control"]["control_idiom"] == "natural_language"
    assert "自然语言运镜" in plan["clips"][0]["video_prompt_injection"]["后端控制写法"]


def test_subtitle_overlay_does_not_make_clip_screen_insert():
    clip = _clip("CU 特写", template="labor_montage", rhythm="压迫·爽点")
    clip["subtitle_lines"] = [{"render_policy": "compose_overlay_only", "text": "第五趟"}]
    clip["description"] = "扁担压肩、水桶溢水、脚步打滑三连剪。"

    out = dcp.analyze_clip(clip, 1)

    assert dcp.classify_clip(clip)["screen"] is False
    assert "屏幕/面板镜" not in out["recommended"]["reason"]


def test_real_screen_insert_still_gets_screen_camera():
    clip = _clip("CU 插入", template="screen_insert")
    clip["template_contract"] = {
        "template_id": "screen_insert",
        "screen_content_ref": "系统面板",
        "text_layer": "overlay",
    }

    out = dcp.analyze_clip(clip, 1)

    assert dcp.classify_clip(clip)["screen"] is True
    assert out["recommended"]["camera_move_zh"] == "固定机位"
    assert "屏幕/面板镜" in out["recommended"]["reason"]


def test_explicit_camera_motivation_allows_one_controlled_push():
    clip = _clip("CU 特写", rhythm="反转·打脸")
    clip["camera_motivation"] = "从人物反应转向刚被发现的物证"

    out = dcp.analyze_clip(clip, 1)

    assert out["recommended"]["camera_move_zh"] == "推镜头"
    assert "从人物反应转向刚被发现的物证" in out["recommended"]["reason"]


def test_unmotivated_direct_camera_gaze_is_warned_and_guarded():
    clip = _clip("MCU 中近景", template="dialogue_shot_reverse")
    clip["description"] = "她忽然正面直视镜头说出真相。"

    out = dcp.analyze_clip(clip, 1)
    codes = {f["code"] for f in out["findings"]}

    assert "unmotivated_direct_camera_gaze" in codes
    assert "戏内对手/道具/动作落点" in out["video_prompt_injection"]["视线表演"]


def test_pov_direct_gaze_is_an_explicit_exception():
    clip = _clip("CU 特写", template="POV")
    clip["gaze_intent"] = "破第四墙，对镜讲话"
    clip["description"] = "她直视镜头。"

    out = dcp.analyze_clip(clip, 1)
    codes = {f["code"] for f in out["findings"]}

    assert "unmotivated_direct_camera_gaze" not in codes
    assert "登记节拍内把视线落到摄影机" in out["video_prompt_injection"]["视线表演"]
