# -*- coding: utf-8 -*-
"""animatic 预演单测。

盯三条纪律：
  ① 缺首帧/缺实测时长 = block（预演不能拿空画面/猜的节奏凑，传统 PPM 不看半张 board）；
  ② concat 清单按实测时长逐帧停留、末帧补行（ffmpeg concat 语法）；
  ③ manifest 带逐帧 SHA 与 VO 时长对账——输入一变预演即过期，可被 gate 侧车按源文件判 stale。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import animatic  # noqa: E402

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

pytestmark = pytest.mark.skipif(Image is None, reason="需要 Pillow 造首帧夹具")


def _project(tmp_path: Path, with_frames=True) -> Path:
    root = tmp_path / "广告项目"
    (root / "脚本").mkdir(parents=True)
    (root / "出图" / "分镜" / "图片").mkdir(parents=True)
    (root / "脚本" / "镜头时长.json").write_text(json.dumps({
        "shots": [{"clip_id": "镜头01", "duration": 2.5}, {"clip_id": "镜头02", "duration": 3.0}],
    }, ensure_ascii=False), encoding="utf-8")
    if with_frames:
        for sid in ("镜头01", "镜头02"):
            Image.new("RGB", (64, 36), (30, 30, 30)).save(root / "出图" / "分镜" / "图片" / f"{sid}.png")
    return root


def test_missing_frames_block_and_manifest_written(tmp_path):
    root = _project(tmp_path, with_frames=False)
    rc = animatic.main([str(root)])

    assert rc == 1
    manifest = json.loads((root / "生产数据" / "ad_animatic_manifest.json").read_text(encoding="utf-8"))
    assert manifest["rendered"] is False
    codes = [f["code"] for f in manifest["findings"]]
    assert codes.count("first_frame_missing") == 2


def test_missing_duration_blocks(tmp_path):
    root = _project(tmp_path)
    (root / "脚本" / "镜头时长.json").write_text(json.dumps({
        "shots": [{"clip_id": "镜头01"}]}, ensure_ascii=False), encoding="utf-8")
    plan, findings = animatic.build_plan(root)

    assert not plan
    assert any(f["code"] == "shot_duration_missing" for f in findings)


def test_concat_spec_holds_each_frame_for_measured_seconds(tmp_path):
    root = _project(tmp_path)
    plan, findings = animatic.build_plan(root)

    assert not findings and len(plan) == 2
    assert all(item["sha256"] for item in plan)
    spec = animatic.concat_spec(root, plan)
    lines = spec.strip().splitlines()
    assert lines[1] == "duration 2.5"
    assert lines[3] == "duration 3.0"
    assert lines[4] == lines[2]  # 末帧补行


def test_render_invoked_and_av_mismatch_warns(tmp_path, monkeypatch):
    root = _project(tmp_path)
    calls = {}

    def fake_render(r, plan, out_rel, fps, with_audio):
        calls["out"] = out_rel
        (r / out_rel).parent.mkdir(parents=True, exist_ok=True)
        (r / out_rel).write_bytes(b"mp4")

    monkeypatch.setattr(animatic, "render", fake_render)
    monkeypatch.setattr(animatic, "vo_duration", lambda r: 9.9)  # 画面 5.5s vs VO 9.9s
    monkeypatch.setattr(animatic.shutil, "which", lambda name: "/usr/bin/" + name)
    rc = animatic.main([str(root)])

    assert rc == 0 and calls["out"] == animatic.DEFAULT_OUT_REL
    manifest = json.loads((root / "生产数据" / "ad_animatic_manifest.json").read_text(encoding="utf-8"))
    assert manifest["rendered"] is True
    assert any(f["code"] == "animatic_av_mismatch" and f["severity"] == "warn"
               for f in manifest["findings"])
    assert manifest["summary"]["block"] == 0
