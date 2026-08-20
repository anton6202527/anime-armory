#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_dreamina helper tests; no real Dreamina calls."""

import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

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


def test_extract_sections_and_build_prompt(tmp_path):
    path = tmp_path / "镜头01.md"
    path.write_text(
        "# t\n\n"
        "## 画面 prompt\nphone on desk\n\n"
        "## 身份锁定句\n同一 logo\n\n"
        "## 负向\n不要乱码\n",
        encoding="utf-8",
    )
    prompt = rd.build_prompt(path)

    assert "phone on desk" in prompt
    assert "同一 logo" in prompt
    assert "不要乱码" in prompt
    assert "Vertical 9:16" not in prompt


def test_run_dreamina_image_parses_text2image_success():
    payload = {
        "submit_id": "sid",
        "gen_status": "success",
        "result_json": {"images": [{"image_url": "https://example.test/a.png", "width": 1, "height": 2}]},
    }
    with mock.patch("render_dreamina.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess(["dreamina"], 0, json.dumps(payload), "")
        out = rd.run_dreamina_image("prompt", [], ratio="9:16", resolution_type="2k", model_version="5.0", poll=1)

    assert out["submit_id"] == "sid"
    assert run.call_args.args[0][0:2] == ["dreamina", "text2image"]


def test_run_dreamina_image_uses_references():
    payload = {
        "submit_id": "sid", "gen_status": "success",
        "result_json": {"images": [{"image_url": "https://example.test/a.png"}]},
    }
    with mock.patch("render_dreamina.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess(["dreamina"], 0, json.dumps(payload), "")
        rd.run_dreamina_image("prompt", ["/tmp/product.png"], ratio="9:16", resolution_type="2k", model_version="5.0", poll=1)
    cmd = run.call_args.args[0]
    assert cmd[0:2] == ["dreamina", "image2image"]
    assert cmd[cmd.index("--images") + 1] == "/tmp/product.png"


def test_run_dreamina_image_blocks_no_image():
    payload = {"submit_id": "sid", "gen_status": "success", "result_json": {"images": []}}
    with mock.patch("render_dreamina.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess(["dreamina"], 0, json.dumps(payload), "")
        try:
            rd.run_dreamina_image("prompt", [], ratio="9:16", resolution_type="2k", model_version="5.0", poll=1)
        except RuntimeError as exc:
            assert "no image_url" in str(exc)
        else:
            raise AssertionError("expected RuntimeError")


def test_require_dreamina_image_signoff_blocks_by_default(tmp_path):
    try:
        rd.require_dreamina_image_signoff(tmp_path)
    except RuntimeError as exc:
        assert "Codex image2" in str(exc)
        assert "image_backend_override.json" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_require_dreamina_image_signoff_accepts_signed_exception(tmp_path):
    signoff = tmp_path / "合规" / "image_backend_override.json"
    signoff.parent.mkdir(parents=True)
    signoff.write_text(json.dumps({
        "approved": True,
        "scope": "image",
        "backend": "dreamina_official",
        "reason": "用户明确指定",
    }, ensure_ascii=False), encoding="utf-8")

    rd.require_dreamina_image_signoff(tmp_path)


# ── 资金安全：submit_id 落盘 / 免费取回 / 预算封顶 ────────────────────────────

def _image_project(tmp_path, jobs):
    root = tmp_path / "项目"
    (root / "出图" / "分镜").mkdir(parents=True)
    for job in jobs:
        job.setdefault("reference_inputs", ["设定库/ref.png"])
        for rel in job["reference_inputs"]:
            path = root / rel
            # 相邻输出由前一 job 生成；静态母图在测试夹具里先落盘。
            if not str(rel).startswith("出图/分镜/图片/"):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"r" * 2048)
    (root / "出图" / "分镜" / "image_jobs_manifest.json").write_text(
        json.dumps({"jobs": jobs}, ensure_ascii=False), encoding="utf-8")
    return root


def _quiet_render_env(monkeypatch):
    monkeypatch.setattr(rd, "require_dreamina_image_signoff", lambda root: None)
    monkeypatch.setattr(rd, "enforce_gate", lambda root: None)
    monkeypatch.setattr(rd, "build_prompt", lambda path: "compiled prompt")
    monkeypatch.setattr(rd, "prepare_image_receipt", lambda root, manifest, job, index: {"status": "preflight_passed"})
    monkeypatch.setattr(rd, "finish_image_receipt", lambda root, job: {"status": "accepted"})
    monkeypatch.setattr(rd.time, "sleep", lambda s: None)


def _render(root, **kwargs):
    args = dict(only=set(), limit=None, force=False, ratio="9:16",
                resolution_type="2k", model_version="5.0", poll=1)
    args.update(kwargs)
    return rd.render_jobs(root, **args)


def _read_manifest(root):
    return json.loads((root / "出图" / "分镜" / "image_jobs_manifest.json").read_text(encoding="utf-8"))


def test_download_failure_keeps_submit_id_in_manifest(tmp_path, monkeypatch):
    root = _image_project(tmp_path, [{
        "job_id": "镜头01",
        "prompt": "出图/分镜/prompt/镜头01.md",
        "expected_output": "出图/分镜/图片/镜头01.png",
    }])
    _quiet_render_env(monkeypatch)
    payload = {
        "submit_id": "sid_1", "credit_count": 2, "gen_status": "success",
        "result_json": {"images": [{"image_url": "https://example.test/a.png"}]},
    }
    monkeypatch.setattr(rd, "run_dreamina_image", lambda *a, **k: payload)

    def broken_download(url, target):
        raise RuntimeError("net down")

    monkeypatch.setattr(rd, "download", broken_download)
    summary = _render(root)
    job = _read_manifest(root)["jobs"][0]

    assert summary["failed"] == 1
    assert job["submit_id"] == "sid_1"
    assert job["result_url"] == "https://example.test/a.png"
    assert job["credit_count"] == 2
    assert job["status"] == "collect_pending"


def test_rerun_with_existing_submit_id_never_resubmits(tmp_path, monkeypatch):
    root = _image_project(tmp_path, [{
        "job_id": "镜头01",
        "prompt": "出图/分镜/prompt/镜头01.md",
        "expected_output": "出图/分镜/图片/镜头01.png",
        "status": "collect_pending",
        "submit_id": "sid_1",
        "result_url": "https://example.test/a.png",
    }])
    _quiet_render_env(monkeypatch)
    submit = mock.Mock(side_effect=AssertionError("must not resubmit a paid job"))
    monkeypatch.setattr(rd, "run_dreamina_image", submit)
    monkeypatch.setattr(rd, "query_dreamina_result", lambda sid: {
        "submit_id": sid, "gen_status": "success",
        "result_json": {"images": [{"image_url": "https://example.test/a.png"}]},
    })

    def fake_download(url, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"0" * 2048)

    monkeypatch.setattr(rd, "download", fake_download)
    summary = _render(root)
    job = _read_manifest(root)["jobs"][0]

    assert not submit.called
    assert summary["rendered"] == 1 and summary["failed"] == 0
    assert job["status"] == "done"
    assert job["submit_id"] == "sid_1"
    assert (root / "出图" / "分镜" / "图片" / "镜头01.png").exists()


def test_rerun_collect_unavailable_blocks_but_keeps_submit_id(tmp_path, monkeypatch):
    root = _image_project(tmp_path, [{
        "job_id": "镜头01",
        "prompt": "出图/分镜/prompt/镜头01.md",
        "expected_output": "出图/分镜/图片/镜头01.png",
        "status": "collect_pending",
        "submit_id": "sid_1",
    }])
    _quiet_render_env(monkeypatch)
    submit = mock.Mock(side_effect=AssertionError("must not resubmit a paid job"))
    monkeypatch.setattr(rd, "run_dreamina_image", submit)

    def broken_query(sid):
        raise RuntimeError("query timeout")

    monkeypatch.setattr(rd, "query_dreamina_result", broken_query)
    summary = _render(root)
    job = _read_manifest(root)["jobs"][0]

    assert not submit.called
    assert summary["failed"] == 1
    assert job["submit_id"] == "sid_1"
    assert job["status"] == "collect_pending"
    assert "sid_1" in job["error"]


def test_max_credits_halts_before_next_paid_submission(tmp_path, monkeypatch):
    root = _image_project(tmp_path, [
        {"job_id": "镜头01", "prompt": "出图/分镜/prompt/镜头01.md",
         "expected_output": "出图/分镜/图片/镜头01.png"},
        {"job_id": "镜头02", "prompt": "出图/分镜/prompt/镜头02.md",
         "expected_output": "出图/分镜/图片/镜头02.png"},
    ])
    _quiet_render_env(monkeypatch)
    submit = mock.Mock(return_value={
        "submit_id": "sid_1", "credit_count": 2, "gen_status": "success",
        "result_json": {"images": [{"image_url": "https://example.test/a.png"}]},
    })
    monkeypatch.setattr(rd, "run_dreamina_image", submit)

    def fake_download(url, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"0" * 2048)

    monkeypatch.setattr(rd, "download", fake_download)
    summary = _render(root, max_credits=2.0)
    manifest = _read_manifest(root)

    assert submit.call_count == 1  # 第 2 个 job 提交前被预算封顶拦下
    assert summary["rendered"] == 1
    assert summary["budget"]["halted"] is True
    assert summary["budget"]["spent_credits"] == 2.0
    assert summary["budget"]["unrun_jobs"] == ["镜头02"]
    assert manifest["jobs"][1].get("submit_id") is None


def test_runner_stops_after_one_output_until_current_pixel_is_signed(tmp_path, monkeypatch):
    root = _image_project(tmp_path, [
        {"job_id": "镜头01", "prompt": "出图/分镜/prompt/镜头01.md",
         "expected_output": "出图/分镜/图片/镜头01.png", "reference_inputs": ["设定库/ref.png"]},
        {"job_id": "镜头02", "prompt": "出图/分镜/prompt/镜头02.md",
         "expected_output": "出图/分镜/图片/镜头02.png", "reference_inputs": ["出图/分镜/图片/镜头01.png"]},
    ])
    _quiet_render_env(monkeypatch)
    monkeypatch.setattr(rd, "finish_image_receipt", lambda root, job: {"status": "awaiting_human_signoff"})
    submit = mock.Mock(return_value={
        "submit_id": "sid", "credit_count": 1, "gen_status": "success",
        "result_json": {"images": [{"image_url": "https://example.test/a.png"}]},
    })
    monkeypatch.setattr(rd, "run_dreamina_image", submit)

    def fake_download(url, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"0" * 2048)

    monkeypatch.setattr(rd, "download", fake_download)
    summary = _render(root)
    manifest = _read_manifest(root)

    assert submit.call_count == 1
    assert summary["awaiting_human_signoff"] == 1
    assert manifest["jobs"][0]["status"] == "awaiting_human_signoff"
    assert manifest["jobs"][1].get("submit_id") is None
