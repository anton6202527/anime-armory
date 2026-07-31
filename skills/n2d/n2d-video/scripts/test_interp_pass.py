"""interp_pass 单测——fps 解析 / 是否需插判定 / 输出命名 / 挑镜 / plan_episode 集成。

cd skills/n2d/n2d-video/scripts && python3 -m pytest test_interp_pass.py
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path


SCRIPT = Path(__file__).with_name("interp_pass.py")
spec = importlib.util.spec_from_file_location("interp_pass", SCRIPT)
ip = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ip)


def test_parse_fps():
    assert ip.parse_fps("24/1") == 24.0
    assert abs(ip.parse_fps("30000/1001") - 29.97) < 0.01
    assert ip.parse_fps("25") == 25.0
    assert ip.parse_fps("0/0") is None
    assert ip.parse_fps("N/A") is None
    assert ip.parse_fps("") is None
    assert ip.parse_fps("5/0") is None  # 零分母不崩


def test_needs_interpolation():
    # 源 fps 低于目标/1.2 → 插
    need, _ = ip.needs_interpolation(24.0, 30.0, first_frame_only=False)
    assert need is True
    # 源 fps 达标 → 不插（避免过度平滑）
    need2, _ = ip.needs_interpolation(30.0, 30.0, first_frame_only=False)
    assert need2 is False
    # first-frame-only + 源未知 → 插（补平滑）
    need3, r3 = ip.needs_interpolation(None, 30.0, first_frame_only=True)
    assert need3 is True and "first-frame-only" in r3
    # first-frame-only + 源已达标 → 不插
    need4, _ = ip.needs_interpolation(30.0, 30.0, first_frame_only=True)
    assert need4 is False
    # 源未知 + 非弱后端 → 不臆造，不插
    need5, r5 = ip.needs_interpolation(None, 30.0, first_frame_only=False)
    assert need5 is False and "不臆造" in r5
    # 29.97→30 不值得（在 ratio_floor 内）
    need6, _ = ip.needs_interpolation(29.97, 30.0, first_frame_only=False)
    assert need6 is False


def test_interp_output_name():
    assert ip.interp_output_name("出视频/第1集/视频/Clip_03.mp4") == "出视频/第1集/视频/Clip_03_interp.mp4"
    assert ip.interp_output_name("x.MP4") == "x_interp.mp4"  # 大写 .MP4 也正确剥除
    assert ip.interp_output_name("clip.mov") == "clip.mov_interp.mp4"  # 非 mp4 直接追加


def test_clip_id_from_filename():
    assert ip.clip_id_from_filename("Clip_03_打斗.mp4") == "Clip_03"
    assert ip.clip_id_from_filename("clip 7.mp4") == "Clip_07"
    assert ip.clip_id_from_filename("封面.mp4") == "封面"


def test_route_backend_map():
    routes = [{"clip_id": "Clip_01", "primary_backend": "seedance"},
              {"id": "Clip_02", "primary_backend": "dreamina"},
              {"primary_backend": "kling"}]  # 无 id → 丢
    m = ip._route_backend_map(routes)
    assert m["Clip_01"] == "seedance" and m["Clip_02"] == "dreamina"
    assert len(m) == 2


def test_target_fps_from_spec(tmp_path):
    root = tmp_path / "作品"
    root.mkdir()
    (root / "_设置.md").write_text("出视频规格：预算不够\n", encoding="utf-8")
    assert ip.target_fps_from_spec(str(root), None) == 24.0
    assert ip.target_fps_from_spec(str(root), 48.0) == 48.0  # override 优先
    (root / "_设置.md").write_text("出视频规格：预算充足\n", encoding="utf-8")
    assert ip.target_fps_from_spec(str(root), None) == 30.0


def test_build_job_shape():
    j = ip.build_job("Clip_01", "出视频/第1集/视频/Clip_01.mp4", 24.0, 30.0, "seedance", True, "因为x")
    assert j["clip_id"] == "Clip_01" and j["output"].endswith("_interp.mp4")
    assert j["source_fps"] == 24.0 and j["target_fps"] == 30.0 and j["first_frame_only"] is True


def test_plan_episode_missing_video_dir(tmp_path):
    root = tmp_path / "作品"
    root.mkdir()
    plan = ip.plan_episode(str(root), "第1集")
    assert plan["jobs"] == [] and any("先出视频" in n for n in plan["notes"])


def test_plan_episode_lists_clips(tmp_path, monkeypatch):
    root = tmp_path / "作品"
    vid = root / "出视频" / "第1集" / "视频"
    vid.mkdir(parents=True)
    (vid / "Clip_01.mp4").write_bytes(b"x")
    (vid / "Clip_02.mp4").write_bytes(b"x")
    (vid / "Clip_02_interp.mp4").write_bytes(b"x")  # 已插的产物应被排除
    pr = root / "出视频" / "第1集" / "prompt"
    pr.mkdir(parents=True)
    (pr / "video_model_routes.json").write_text(
        json.dumps({"routes": [{"clip_id": "Clip_01", "primary_backend": "seedance"},
                               {"clip_id": "Clip_02", "primary_backend": "dreamina"}]}),
        encoding="utf-8")
    (root / "_设置.md").write_text("出视频规格：预算一般\n", encoding="utf-8")
    # 桩掉 ffprobe：Clip_01 源 24fps，Clip_02 源 30fps
    monkeypatch.setattr(ip, "_ffprobe_fps", lambda p: 24.0 if "Clip_01" in p else 30.0)
    plan = ip.plan_episode(str(root), "第1集")
    job_ids = {j["clip_id"] for j in plan["jobs"]}
    # Clip_01: seedance(first-frame-only) + 24<30 → 插；Clip_02: dreamina(支持多帧) + 30 达标 → 不插
    assert "Clip_01" in job_ids
    assert "Clip_02" not in job_ids
    # _interp.mp4 不被当作待处理 clip
    assert all("interp" not in j["video"] for j in plan["jobs"])
