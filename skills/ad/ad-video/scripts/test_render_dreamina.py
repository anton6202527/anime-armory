#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import subprocess
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
# 同名模块防串：另一 render_dreamina（同线其它 skill）先被导入时，按本目录重新加载
_cached = sys.modules.get("render_dreamina")
if _cached is not None and Path(getattr(_cached, "__file__", "")).resolve().parent != _HERE:
    del sys.modules["render_dreamina"]
    import importlib
    importlib.invalidate_caches()
import render_dreamina as rd  # noqa: E402
assert Path(rd.__file__).resolve().parent == _HERE
from ad_video_prompt_compiler import compile_prompt, render_markdown  # noqa: E402

REAL_CONSUME_VIDEO_SPEND = rd.consume_video_spend
REAL_SETTLE_VIDEO_SPEND = rd.settle_video_spend


@pytest.fixture(autouse=True)
def stub_paid_spend_for_legacy_runner_tests(monkeypatch):
    """Existing media tests isolate rendering; dedicated tests below exercise real spend gates."""
    monkeypatch.setattr(rd, "consume_video_spend", lambda *args, **kwargs: {"status": "pass"})
    monkeypatch.setattr(rd, "settle_video_spend", lambda *args, **kwargs: {"status": "pass"})


def test_submit_duration_seedance_clamps_and_ceil():
    assert rd.submit_duration(3.1, "seedance2.0fast") == 4
    assert rd.submit_duration(4.8, "seedance2.0fast") == 5
    assert rd.submit_duration(16.2, "seedance2.0fast") == 15


def test_find_media_url_nested_payload():
    payload = {"result_json": {"videos": [{"video_url": "https://example.com/a.mp4"}]}}
    assert rd._find_media_url(payload) == "https://example.com/a.mp4"


def test_probe_video_output_records_observed_dimensions_fps_and_sha(tmp_path, monkeypatch):
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"returned-media")
    monkeypatch.setattr(rd.shutil, "which", lambda name: "/usr/bin/ffprobe" if name == "ffprobe" else None)
    monkeypatch.setattr(rd.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(
        args[0], 0, json.dumps({"streams": [{
            "width": 1280, "height": 720, "avg_frame_rate": "24000/1001",
        }]}), "",
    ))

    observed = rd.probe_video_output(media)

    assert observed["resolution"] == "1280x720"
    assert observed["fps"] == pytest.approx(23.976024)
    assert observed["output_sha256"] == rd.sha256_file(media)


def test_build_prompt_submits_only_compiled_block(tmp_path):
    p = tmp_path / "镜头01.md"
    compiled = compile_prompt({
        "clip_id": "镜头01",
        "backend": "seedance",
        "mode": "image2video",
        "product_action": "UI 卡片归入今日手账",
        "camera_motion": "缓慢推近手机正面",
        "end_state": "产品主视觉稳定落幅",
        "product_hold": "同一包装结构与 Logo 位置",
    })
    p.write_text(
        "# test\n\n"
        "## 输入帧\n- skip\n\n"
        "## 运镜与动作\nslow push in\n\n"
        "## 产品/品牌身份锁定\nPROD_STARBOX_APP same logo\n\n"
        "## 负向\nno watermark\n\n"
        + render_markdown(compiled),
        encoding="utf-8",
    )
    prompt = rd.build_prompt(p)
    assert prompt == compiled["prompt"]
    assert "slow push in" not in prompt
    assert "PROD_STARBOX_APP" not in prompt
    assert "skip" not in prompt


def test_build_prompt_rejects_legacy_uncompiled_contract(tmp_path):
    p = tmp_path / "legacy.md"
    p.write_text("## 运镜与动作\nslow push in\n\n## 负向\nno watermark\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="缺后端编译提交 prompt"):
        rd.build_prompt(p)


def test_render_jobs_with_fake_backend(tmp_path, monkeypatch):
    root = tmp_path / "项目"
    (root / "出视频" / "分镜" / "prompt").mkdir(parents=True)
    (root / "出视频" / "分镜" / "prompt" / "镜头01.md").write_text("## 运镜与动作\nslow", encoding="utf-8")
    (root / "出图" / "分镜" / "图片").mkdir(parents=True)
    (root / "出图" / "分镜" / "图片" / "镜头01.png").write_bytes(b"png")
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
    monkeypatch.setattr(rd, "enforce_gate", lambda root_arg: None)
    monkeypatch.setattr(rd, "build_prompt", lambda path: "compiled prompt")
    source_profile = rd.ad_render_profile.compile_profile(root)["source_generation"]
    monkeypatch.setattr(rd, "probe_video_output", lambda path: {
        "width": source_profile["width"], "height": source_profile["height"],
        "resolution": source_profile["resolution"], "fps": float(source_profile["fps"]),
        "output_sha256": rd.sha256_file(path), "probe": "ffprobe",
    })
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
    (root / "出图" / "分镜" / "图片").mkdir(parents=True)
    (root / "出图" / "分镜" / "图片" / "镜头01.png").write_bytes(b"png")
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
    monkeypatch.setattr(rd, "enforce_gate", lambda root_arg: None)
    monkeypatch.setattr(rd, "build_prompt", lambda path: "compiled prompt")
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
    assert out["jobs"][0]["render_profile_sha256"] == out["jobs"][0]["render_profile"]["sha256"]
    assert out["jobs"][0]["submit_prompt_sha256"]


def test_render_jobs_uses_render_profile_resolution_when_cli_override_is_omitted(tmp_path, monkeypatch):
    root = _video_project(tmp_path, [{
        "job_id": "镜头01", "mode": "image2video",
        "prompt": "出视频/分镜/prompt/镜头01.md",
        "first_frame": "出图/分镜/图片/镜头01.png", "duration": 4.0,
        "expected_output": "出视频/分镜/视频/镜头01.mp4",
    }])
    (root / "_设置.md").write_text(
        "- 出视频规格: 预算充足\n- 视频分辨率: 1080p\n- 交付比例: 16:9\n", encoding="utf-8")
    _quiet_video_env(monkeypatch)
    seen = {}

    def fake_run(job, root_arg, **kwargs):
        seen.update(kwargs)
        return {"gen_status": "success", "submit_id": "sub_1080", "credit_count": 1,
                "_submitted_duration": 4, "_mode": "image2video"}

    def fake_download(payload, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"0" * 100001)

    monkeypatch.setattr(rd, "run_dreamina_video", fake_run)
    monkeypatch.setattr(rd, "download_result", fake_download)
    summary = rd.render_jobs(
        root, only=set(), limit=None, force=False, model_version="seedance2.0fast",
        video_resolution=None, poll=1,
    )

    assert seen["video_resolution"] == "1080p"
    assert summary["video_resolution"] == "1080p"
    assert summary["source_fps"] == 30
    manifest = json.loads((root / "出视频" / "分镜" / "video_jobs_manifest.json").read_text(encoding="utf-8"))
    assert manifest["render_profile"]["source_generation"]["resolution"] == "1920x1080"


def test_render_jobs_rejects_cli_resolution_that_disagrees_with_profile(tmp_path, monkeypatch):
    root = _video_project(tmp_path, [{
        "job_id": "镜头01", "mode": "image2video",
        "prompt": "出视频/分镜/prompt/镜头01.md",
        "first_frame": "出图/分镜/图片/镜头01.png", "duration": 4.0,
        "expected_output": "出视频/分镜/视频/镜头01.mp4",
    }])
    (root / "_设置.md").write_text(
        "- 出视频规格: 预算充足\n- 视频分辨率: 1080p\n- 交付比例: 16:9\n", encoding="utf-8")
    _quiet_video_env(monkeypatch)

    with pytest.raises(RuntimeError, match="唯一规格"):
        rd.render_jobs(
            root, only=set(), limit=None, force=False, model_version="seedance2.0fast",
            video_resolution="720p", poll=1,
        )


def test_run_dreamina_video_rechecks_submit_id_when_initial_status_fail(tmp_path, monkeypatch):
    root = tmp_path / "项目"
    (root / "出视频" / "分镜" / "prompt").mkdir(parents=True)
    (root / "出视频" / "分镜" / "prompt" / "镜头01.md").write_text("## 运镜与动作\nslow", encoding="utf-8")
    (root / "出图" / "分镜" / "图片").mkdir(parents=True)
    (root / "出图" / "分镜" / "图片" / "镜头01.png").write_bytes(b"png")
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
    monkeypatch.setattr(rd, "build_prompt", lambda path: "compiled prompt")
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
    monkeypatch.setattr(rd.time, "sleep", lambda s: None)
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
    assert out["jobs"][0]["status"] == "submitted_stale_profile"
    assert "job_render_profile_stale" in out["jobs"][0]["stale_reasons"]
    assert out["jobs"][0]["last_query_error"] == "timeout"


def test_existing_output_is_not_relabelled_done_after_render_profile_changes(tmp_path, monkeypatch):
    root = _video_project(tmp_path, [{
        "job_id": "镜头01", "mode": "image2video",
        "prompt": "出视频/分镜/prompt/镜头01.md",
        "first_frame": "出图/分镜/图片/镜头01.png", "duration": 4.0,
        "expected_output": "出视频/分镜/视频/镜头01.mp4",
    }])
    _quiet_video_env(monkeypatch)
    monkeypatch.setattr(rd, "run_dreamina_video", lambda job, root_arg, **kwargs: {
        "gen_status": "success", "submit_id": "sub_current", "credit_count": 1,
        "_submitted_duration": 4, "_mode": "image2video",
    })

    def fake_download(payload, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"0" * 100001)

    monkeypatch.setattr(rd, "download_result", fake_download)
    first = rd.render_jobs(
        root, only=set(), limit=None, force=False, model_version="seedance2.0fast",
        video_resolution=None, poll=1,
    )
    assert first["rendered"] == 1

    (root / "_设置.md").write_text(
        "- 出视频规格: 预算充足\n- 视频分辨率: 1080p\n- 交付比例: 16:9\n",
        encoding="utf-8",
    )
    second = rd.render_jobs(
        root, only=set(), limit=None, force=False, model_version="seedance2.0fast",
        video_resolution=None, poll=1,
    )
    job = json.loads((root / "出视频" / "分镜" / "video_jobs_manifest.json").read_text(
        encoding="utf-8"))["jobs"][0]

    assert second["skipped"] == 1
    assert job["status"] == "collected_stale_profile"
    assert "job_render_profile_stale" in job["stale_reasons"]


def test_collected_output_is_rechecked_after_download_before_done(tmp_path, monkeypatch):
    root = _video_project(tmp_path, [{
        "job_id": "镜头01", "mode": "image2video",
        "prompt": "出视频/分镜/prompt/镜头01.md",
        "first_frame": "出图/分镜/图片/镜头01.png", "duration": 4.0,
        "expected_output": "出视频/分镜/视频/镜头01.mp4",
    }])
    _quiet_video_env(monkeypatch)
    monkeypatch.setattr(rd, "run_dreamina_video", lambda job, root_arg, **kwargs: {
        "gen_status": "querying", "_pending_status": "querying",
        "submit_id": "sub_mismatch", "credit_count": 1,
        "_submitted_duration": 4, "_mode": "image2video",
    })
    first = rd.render_jobs(
        root, only=set(), limit=None, force=False, model_version="seedance2.0fast",
        video_resolution=None, poll=0, submit_only=True,
    )
    assert first["submitted"] == 1

    monkeypatch.setattr(rd, "query_dreamina_result", lambda submit_id: {
        "gen_status": "success", "submit_id": submit_id,
    })
    monkeypatch.setattr(rd, "download_result", lambda payload, target: (
        target.parent.mkdir(parents=True, exist_ok=True), target.write_bytes(b"x" * 100001)
    ))
    monkeypatch.setattr(rd, "probe_video_output", lambda path: {
        "width": 1280, "height": 720, "resolution": "1280x720", "fps": 30.0,
        "output_sha256": rd.sha256_file(path), "probe": "ffprobe",
    })
    rd.render_jobs(
        root, only=set(), limit=None, force=False, model_version="seedance2.0fast",
        video_resolution=None, poll=0, collect_only=True,
    )
    job = json.loads((root / "出视频" / "分镜" / "video_jobs_manifest.json").read_text(
        encoding="utf-8"))["jobs"][0]

    assert job["observed_output"]["fps"] == 30.0
    assert job["status"] == "collected_profile_mismatch"
    assert "observed_output_profile_mismatch" in job["stale_reasons"]


# ── 资金安全：submit_id 先落盘 / 下载失败可续跑 / 预算封顶 ────────────────────

def _video_project(tmp_path, jobs):
    root = tmp_path / "项目"
    (root / "出视频" / "分镜" / "prompt").mkdir(parents=True)
    (root / "出图" / "分镜" / "图片").mkdir(parents=True)
    for job in jobs:
        prompt_rel = job.get("prompt")
        if prompt_rel:
            (root / prompt_rel).write_text("## 运镜与动作\nslow", encoding="utf-8")
        frame_rel = job.get("first_frame")
        if frame_rel:
            (root / frame_rel).write_bytes(b"png")
    (root / "出视频" / "分镜" / "video_jobs_manifest.json").write_text(
        json.dumps({"jobs": jobs}, ensure_ascii=False), encoding="utf-8")
    return root


def _quiet_video_env(monkeypatch):
    monkeypatch.setattr(rd, "enforce_gate", lambda root: None)
    monkeypatch.setattr(rd, "build_prompt", lambda path: "compiled prompt")
    monkeypatch.setattr(rd.time, "sleep", lambda s: None)
    def current_observed(path):
        root = path.resolve().parents[3]
        profile = json.loads((root / "生产数据" / "render_profile.json").read_text(encoding="utf-8"))
        source = profile["source_generation"]
        return {
            "width": source["width"], "height": source["height"],
            "resolution": source["resolution"], "fps": float(source["fps"]),
            "output_sha256": rd.sha256_file(path), "probe": "ffprobe",
        }
    monkeypatch.setattr(rd, "probe_video_output", current_observed)


def _render(root, **kwargs):
    args = dict(only=set(), limit=None, force=False, model_version="seedance2.0fast",
                video_resolution="720p", poll=1)
    args.update(kwargs)
    return rd.render_jobs(root, **args)


def test_sync_download_failure_keeps_submit_id_in_manifest(tmp_path, monkeypatch):
    root = _video_project(tmp_path, [{
        "job_id": "镜头01",
        "mode": "image2video",
        "prompt": "出视频/分镜/prompt/镜头01.md",
        "first_frame": "出图/分镜/图片/镜头01.png",
        "duration": 4.0,
        "expected_output": "出视频/分镜/视频/镜头01.mp4",
    }])
    _quiet_video_env(monkeypatch)
    monkeypatch.setattr(rd, "run_dreamina_video", lambda job, root_arg, **kw: {
        "gen_status": "success", "submit_id": "sub_1", "credit_count": 3,
        "_submitted_duration": 4, "_mode": "image2video",
    })

    def broken_download(payload, target):
        raise RuntimeError("net down")

    monkeypatch.setattr(rd, "download_result", broken_download)
    summary = _render(root)
    job = json.loads((root / "出视频" / "分镜" / "video_jobs_manifest.json").read_text(encoding="utf-8"))["jobs"][0]

    assert summary["failed"] == 1
    assert job["submit_id"] == "sub_1"
    assert job["credit_count"] == 3
    assert job["status"] == "collect_pending"  # 重跑走 existing_submit_id 免费取回


def test_max_credits_halts_before_next_paid_submission(tmp_path, monkeypatch):
    root = _video_project(tmp_path, [
        {"job_id": "镜头01", "mode": "image2video", "prompt": "出视频/分镜/prompt/镜头01.md",
         "first_frame": "出图/分镜/图片/镜头01.png", "duration": 4.0,
         "expected_output": "出视频/分镜/视频/镜头01.mp4"},
        {"job_id": "镜头02", "mode": "image2video", "prompt": "出视频/分镜/prompt/镜头02.md",
         "first_frame": "出图/分镜/图片/镜头02.png", "duration": 4.0,
         "expected_output": "出视频/分镜/视频/镜头02.mp4"},
    ])
    _quiet_video_env(monkeypatch)
    calls = []

    def fake_run(job, root_arg, **kwargs):
        calls.append(job.get("job_id"))
        return {"gen_status": "success", "submit_id": f"sub_{len(calls)}", "credit_count": 5,
                "_submitted_duration": 4, "_mode": "image2video"}

    def fake_download(payload, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"0" * 100001)

    monkeypatch.setattr(rd, "run_dreamina_video", fake_run)
    monkeypatch.setattr(rd, "download_result", fake_download)
    summary = _render(root, max_credits=5.0)
    manifest = json.loads((root / "出视频" / "分镜" / "video_jobs_manifest.json").read_text(encoding="utf-8"))

    assert calls == ["镜头01"]  # 第 2 个 job 提交前被预算封顶拦下
    assert summary["rendered"] == 1
    assert summary["budget"]["halted"] is True
    assert summary["budget"]["spent_credits"] == 5.0
    assert summary["budget"]["unrun_jobs"] == ["镜头02"]
    assert manifest["jobs"][1].get("submit_id") is None


def test_unknown_reserved_cost_never_submits_or_consumes(tmp_path, monkeypatch):
    root = _video_project(tmp_path, [{
        "job_id": "镜头01",
        "mode": "image2video",
        "prompt": "出视频/分镜/prompt/镜头01.md",
        "first_frame": "出图/分镜/图片/镜头01.png",
        "duration": 4.0,
        "expected_output": "出视频/分镜/视频/镜头01.mp4",
    }])
    _quiet_video_env(monkeypatch)
    monkeypatch.setattr(rd, "consume_video_spend", REAL_CONSUME_VIDEO_SPEND)
    calls = []
    monkeypatch.setattr(
        rd,
        "run_dreamina_video",
        lambda *args, **kwargs: calls.append("submitted"),
    )

    summary = _render(root)
    job = json.loads((root / "出视频" / "分镜" / "video_jobs_manifest.json").read_text(
        encoding="utf-8"
    ))["jobs"][0]

    assert summary["failed"] == 1
    assert calls == []
    assert not (root / rd.spend_envelope.LEDGER_REL).exists()
    assert "未知 cost" in job["error"]


def test_real_video_spend_envelope_reserves_and_settles_actual(tmp_path, monkeypatch):
    root = _video_project(tmp_path, [{
        "job_id": "镜头01",
        "mode": "image2video",
        "prompt": "出视频/分镜/prompt/镜头01.md",
        "first_frame": "出图/分镜/图片/镜头01.png",
        "duration": 4.0,
        "expected_output": "出视频/分镜/视频/镜头01.mp4",
        "estimated_credit_count": 2,
        "estimated_credit_count_is_upper_bound": True,
        "estimated_credit_count_source": "provider-pricing-snapshot:2026-08-21",
    }])
    _quiet_video_env(monkeypatch)
    monkeypatch.setattr(rd, "consume_video_spend", REAL_CONSUME_VIDEO_SPEND)
    monkeypatch.setattr(rd, "settle_video_spend", REAL_SETTLE_VIDEO_SPEND)
    manifest = json.loads((root / "出视频" / "分镜" / "video_jobs_manifest.json").read_text(
        encoding="utf-8"
    ))
    digest, scope = rd.video_phase_spend_binding(
        root, manifest, model_version="seedance2.0fast", video_resolution="720p"
    )
    approved = rd.spend_envelope.make_envelope(
        root,
        stage="video",
        model="seedance2.0fast",
        channel=rd.SPEND_CHANNEL,
        input_sha256=digest,
        scope=scope,
        max_calls=1,
        max_attempts=1,
        cost_ceiling=2,
        currency="credit",
        approver="client-producer@example.invalid",
        approval_reference="approval-ui:video-phase",
        source_quote="我确认该视频阶段最多使用 2 credit。",
        envelope_id="video-real-integration",
    )
    rd.spend_envelope.write_envelope(
        rd.spend_envelope.default_envelope_path(root, "video"), approved
    )
    monkeypatch.setattr(rd, "run_dreamina_video", lambda *args, **kwargs: {
        "gen_status": "success",
        "submit_id": "sub-real",
        "credit_count": 1,
        "_submitted_duration": 4,
        "_mode": "image2video",
    })

    def fake_download(payload, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"0" * 100001)

    monkeypatch.setattr(rd, "download_result", fake_download)
    summary = _render(root)
    job = json.loads((root / "出视频" / "分镜" / "video_jobs_manifest.json").read_text(
        encoding="utf-8"
    ))["jobs"][0]

    assert summary["rendered"] == 1
    assert job["spend_settlement"]["status"] == "pass"
    assert job["spend_settlement"]["usage"]["cost"] == 1.0


def test_existing_video_query_reconciles_pending_reservation_actual(tmp_path, monkeypatch):
    root = _video_project(tmp_path, [{
        "job_id": "镜头01", "mode": "image2video",
        "prompt": "出视频/分镜/prompt/镜头01.md",
        "first_frame": "出图/分镜/图片/镜头01.png", "duration": 4.0,
        "expected_output": "出视频/分镜/视频/镜头01.mp4",
        "estimated_credit_count": 2,
        "estimated_credit_count_is_upper_bound": True,
        "estimated_credit_count_source": "provider-pricing-snapshot:2026-08-21",
    }])
    _quiet_video_env(monkeypatch)
    monkeypatch.setattr(rd, "settle_video_spend", REAL_SETTLE_VIDEO_SPEND)
    manifest = json.loads((root / "出视频" / "分镜" / "video_jobs_manifest.json").read_text(
        encoding="utf-8"
    ))
    digest, scope = rd.video_phase_spend_binding(
        root, manifest, model_version="seedance2.0fast", video_resolution="720p"
    )
    approved = rd.spend_envelope.make_envelope(
        root, stage="video", model="seedance2.0fast", channel=rd.SPEND_CHANNEL,
        input_sha256=digest, scope=scope, max_calls=1, max_attempts=1,
        cost_ceiling=2, currency="credit", approver="client-producer@example.invalid",
        approval_reference="approval-ui:video-recovery",
        source_quote="我确认该视频恢复路径最多使用 2 credit。",
        envelope_id="video-recovery",
    )
    rd.spend_envelope.write_envelope(
        rd.spend_envelope.default_envelope_path(root, "video"), approved
    )
    job = manifest["jobs"][0]
    REAL_CONSUME_VIDEO_SPEND(
        root, manifest, job, model_version="seedance2.0fast", video_resolution="720p",
        envelope_path=None,
    )
    job["submit_id"] = "sub-recovery"

    result = rd.reconcile_existing_video_spend(
        root,
        job,
        {"submit_id": "sub-recovery", "credit_count": 1},
        envelope_path=None,
        terminal=True,
    )

    assert result["status"] == "pass"
    assert job["credit_count"] == 1.0
    assert job["spend_settlement"]["usage"]["cost"] == 1.0


def test_terminal_existing_video_without_actual_cost_is_not_fully_recovered(
    tmp_path, monkeypatch
):
    root = _video_project(tmp_path, [{
        "job_id": "镜头01", "mode": "image2video",
        "prompt": "出视频/分镜/prompt/镜头01.md",
        "first_frame": "出图/分镜/图片/镜头01.png", "duration": 4.0,
        "expected_output": "出视频/分镜/视频/镜头01.mp4",
        "estimated_credit_count": 2,
        "estimated_credit_count_is_upper_bound": True,
        "estimated_credit_count_source": "provider-pricing-snapshot:2026-08-21",
    }])
    _quiet_video_env(monkeypatch)
    manifest = json.loads((root / "出视频" / "分镜" / "video_jobs_manifest.json").read_text(
        encoding="utf-8"
    ))
    digest, scope = rd.video_phase_spend_binding(
        root, manifest, model_version="seedance2.0fast", video_resolution="720p"
    )
    approved = rd.spend_envelope.make_envelope(
        root, stage="video", model="seedance2.0fast", channel=rd.SPEND_CHANNEL,
        input_sha256=digest, scope=scope, max_calls=1, max_attempts=1,
        cost_ceiling=2, currency="credit", approver="client-producer@example.invalid",
        approval_reference="approval-ui:video-unknown-actual",
        source_quote="我确认该视频阶段最多使用 2 credit。", envelope_id="video-unknown-actual",
    )
    rd.spend_envelope.write_envelope(
        rd.spend_envelope.default_envelope_path(root, "video"), approved
    )
    job = manifest["jobs"][0]
    REAL_CONSUME_VIDEO_SPEND(
        root, manifest, job, model_version="seedance2.0fast", video_resolution="720p",
        envelope_path=None,
    )
    job["submit_id"] = "sub-unknown"

    with pytest.raises(rd.SpendSettlementBlocked, match="actual credit_count"):
        rd.reconcile_existing_video_spend(
            root, job, {"submit_id": "sub-unknown"}, envelope_path=None, terminal=True
        )
    assert job["spend_settlement"]["status"] == "blocked"
