#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_dreamina as rd  # noqa: E402


def test_submit_duration_seedance_clamps_and_ceil():
    assert rd.submit_duration(3.1, "seedance2.0fast") == 4
    assert rd.submit_duration(4.8, "seedance2.0fast") == 5
    assert rd.submit_duration(16.2, "seedance2.0fast") == 15


def test_find_media_url_nested_payload():
    payload = {"result_json": {"videos": [{"video_url": "https://example.com/a.mp4"}]}}
    assert rd._find_media_url(payload) == "https://example.com/a.mp4"


def test_build_prompt_extracts_key_sections(tmp_path):
    p = tmp_path / "镜头01.md"
    p.write_text(
        "# test\n\n"
        "## 输入帧\n- skip\n\n"
        "## 运镜与动作\nslow push in\n\n"
        "## 产品/品牌身份锁定\nPROD_STARBOX_APP same logo\n\n"
        "## 负向\nno watermark\n",
        encoding="utf-8",
    )
    prompt = rd.build_prompt(p)
    assert "slow push in" in prompt
    assert "PROD_STARBOX_APP" in prompt
    assert "skip" not in prompt
    assert "commercial ad video" in prompt


def test_render_jobs_with_fake_backend(tmp_path, monkeypatch):
    root = tmp_path / "项目"
    (root / "出视频" / "分镜" / "prompt").mkdir(parents=True)
    (root / "出视频" / "分镜" / "prompt" / "镜头01.md").write_text("## 运镜与动作\nslow", encoding="utf-8")
    manifest = {
        "jobs": [{
            "job_id": "镜头01",
            "mode": "image2video",
            "prompt": "出视频/分镜/prompt/镜头01.md",
            "first_frame": "出图/分镜/图片/镜头01.png",
            "duration": 4.0,
            "expected_output": "出视频/分镜/视频/镜头01.mp4",
        }]
    }
    (root / "出视频" / "分镜" / "video_jobs_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False),
        encoding="utf-8",
    )

    def fake_run(job, root_arg, **kwargs):
        return {"gen_status": "success", "submit_id": "sub_1", "_submitted_duration": 4, "_mode": "image2video"}

    def fake_download(payload, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"0" * 100001)

    monkeypatch.setattr(rd, "run_dreamina_video", fake_run)
    monkeypatch.setattr(rd, "download_result", fake_download)
    summary = rd.render_jobs(
        root,
        only=set(),
        limit=None,
        force=False,
        model_version="seedance2.0fast",
        video_resolution="720p",
        poll=1,
    )
    assert summary["rendered"] == 1
    out = json.loads((root / "出视频" / "分镜" / "video_jobs_manifest.json").read_text(encoding="utf-8"))
    assert out["jobs"][0]["status"] == "done"
    assert (root / "出视频" / "分镜" / "视频" / "镜头01.mp4").exists()


def test_render_jobs_records_pending_submission(tmp_path, monkeypatch):
    root = tmp_path / "项目"
    (root / "出视频" / "分镜" / "prompt").mkdir(parents=True)
    (root / "出视频" / "分镜" / "prompt" / "镜头01.md").write_text("## 运镜与动作\nslow", encoding="utf-8")
    (root / "出视频" / "分镜" / "video_jobs_manifest.json").write_text(
        json.dumps({"jobs": [{
            "job_id": "镜头01",
            "mode": "image2video",
            "prompt": "出视频/分镜/prompt/镜头01.md",
            "first_frame": "出图/分镜/图片/镜头01.png",
            "duration": 4.0,
            "expected_output": "出视频/分镜/视频/镜头01.mp4",
        }]}, ensure_ascii=False),
        encoding="utf-8",
    )

    def fake_run(job, root_arg, **kwargs):
        return {
            "gen_status": "querying",
            "_pending_status": "querying",
            "submit_id": "sub_pending",
            "_submitted_duration": 4,
            "_mode": "image2video",
        }

    monkeypatch.setattr(rd, "run_dreamina_video", fake_run)
    summary = rd.render_jobs(
        root,
        only=set(),
        limit=None,
        force=False,
        model_version="seedance2.0fast",
        video_resolution="720p",
        poll=0,
        submit_only=True,
    )
    out = json.loads((root / "出视频" / "分镜" / "video_jobs_manifest.json").read_text(encoding="utf-8"))
    assert summary["submitted"] == 1
    assert summary["failed"] == 0
    assert out["jobs"][0]["status"] == "submitted"
    assert out["jobs"][0]["submit_id"] == "sub_pending"


def test_run_dreamina_video_rechecks_submit_id_when_initial_status_fail(tmp_path, monkeypatch):
    root = tmp_path / "项目"
    (root / "出视频" / "分镜" / "prompt").mkdir(parents=True)
    (root / "出视频" / "分镜" / "prompt" / "镜头01.md").write_text("## 运镜与动作\nslow", encoding="utf-8")
    calls = []

    def fake_run(cmd, text, capture_output):
        calls.append(cmd)
        if cmd[:2] == ["dreamina", "query_result"]:
            return subprocess.CompletedProcess(cmd, 0, json.dumps({
                "submit_id": "sub_1",
                "gen_status": "querying",
            }), "")
        return subprocess.CompletedProcess(cmd, 0, json.dumps({
            "submit_id": "sub_1",
            "gen_status": "fail",
        }), "")

    monkeypatch.setattr(rd.subprocess, "run", fake_run)
    payload = rd.run_dreamina_video(
        {
            "mode": "image2video",
            "prompt": "出视频/分镜/prompt/镜头01.md",
            "first_frame": "出图/分镜/图片/镜头01.png",
            "duration": 4.0,
        },
        root,
        model_version="seedance2.0fast",
        video_resolution="720p",
        poll=0,
    )
    assert payload["_pending_status"] == "querying"
    assert any(cmd[:2] == ["dreamina", "query_result"] for cmd in calls)


def test_collect_only_query_error_keeps_job_submitted(tmp_path, monkeypatch):
    root = tmp_path / "项目"
    (root / "出视频" / "分镜").mkdir(parents=True)
    (root / "出视频" / "分镜" / "video_jobs_manifest.json").write_text(
        json.dumps({"jobs": [{
            "job_id": "镜头01",
            "clip": "镜头01",
            "submit_id": "sub_1",
            "status": "submitted",
            "expected_output": "出视频/分镜/视频/镜头01.mp4",
        }]}, ensure_ascii=False),
        encoding="utf-8",
    )

    def fake_query(submit_id):
        raise RuntimeError("timeout")

    monkeypatch.setattr(rd, "query_dreamina_result", fake_query)
    summary = rd.render_jobs(
        root,
        only=set(),
        limit=None,
        force=False,
        model_version="seedance2.0fast",
        video_resolution="720p",
        poll=0,
        collect_only=True,
    )
    out = json.loads((root / "出视频" / "分镜" / "video_jobs_manifest.json").read_text(encoding="utf-8"))
    assert summary["pending"] == 1
    assert summary["failed"] == 0
    assert out["jobs"][0]["status"] == "submitted"
    assert out["jobs"][0]["last_query_error"] == "timeout"
