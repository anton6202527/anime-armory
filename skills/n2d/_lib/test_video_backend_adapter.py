"""video_backend_adapter 能力归一与 per-run 刷新证据单测。"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path


def _load():
    lib_dir = Path(__file__).resolve().parent
    if str(lib_dir) not in sys.path:
        sys.path.insert(0, str(lib_dir))
    spec = importlib.util.spec_from_file_location("video_backend_adapter", lib_dir / "video_backend_adapter.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


adapter = _load()


def test_alias_normalizes_to_execution_profile():
    data = adapter.backend_adapter("Seedance 2.0", "即梦/Dreamina")
    assert data["canonical"] == "seedance"
    assert data["execution_backend"] == "dreamina"
    assert data["capability_confidence"]["confidence"] == "evidence"
    assert data["paid_routing_allowed"] is True
    assert data["anchor_consumption_sample"]["consumption_mode"] == "native_multiframe"
    assert data["control_idiom"] == "structured_multi_prompt"


def test_manual_backend_skips_refresh_requirement(tmp_path):
    status = adapter.refresh_evidence_status(str(tmp_path), "manual", today=dt.date(2026, 6, 21))
    assert status["status"] == "skipped"


def test_refresh_evidence_status_lifecycle(tmp_path):
    missing = adapter.refresh_evidence_status(
        str(tmp_path),
        "Veo 3.1",
        "Google Gemini API",
        today=dt.date(2026, 6, 21),
    )
    assert missing["status"] == "missing"

    path = adapter.write_refresh_evidence(
        str(tmp_path),
        "Veo 3.1",
        channel="Google Gemini API",
        sources=["Google Gemini API Veo docs"],
        source_urls=["https://ai.google.dev/gemini-api/docs/video"],
        evidence_kind="official_docs",
        note="checked model, first/last frame, native audio and duration limits",
        today="2026-06-21",
    )
    assert path.exists()
    fresh = adapter.refresh_evidence_status(
        str(tmp_path),
        "Veo 3.1",
        "Google Gemini API",
        today=dt.date(2026, 6, 21),
    )
    stale = adapter.refresh_evidence_status(
        str(tmp_path),
        "Veo 3.1",
        "Google Gemini API",
        today=dt.date(2026, 6, 22),
    )
    assert fresh["status"] == "fresh"
    assert fresh["capability_assertions"]["supports_last_frame"]["value"] is True
    assert fresh["capability_assertions"]["supports_last_frame"]["source"] == "Google Gemini API Veo docs"
    assert fresh["capability_assertions"]["native_av"]["value"] is True
    assert fresh["capability_assertions"]["native_audio"]["value"] is True
    assert stale["status"] == "stale"


def test_control_idiom_requires_fresh_evidence(tmp_path):
    missing = adapter.resolve_control_idiom(str(tmp_path), "Kling 3.0", "可灵/Kling", today=dt.date(2026, 6, 21))
    assert missing["control_idiom"] == "natural_language"
    assert missing["source"] == "fallback_no_fresh_evidence"

    adapter.write_refresh_evidence(
        str(tmp_path),
        "Kling 3.0",
        channel="可灵/Kling",
        sources=["Kling API docs"],
        evidence_kind="official_docs",
        note="motion brush verified",
        today="2026-06-21",
    )
    fresh = adapter.resolve_control_idiom(str(tmp_path), "Kling 3.0", "可灵/Kling", today=dt.date(2026, 6, 21))
    assert fresh["control_idiom"] == "motion_brush_on_firstframe"
    assert fresh["source"] == "per_run_evidence"


def test_route_native_audio_profile_reads_video_routes(tmp_path):
    routes_dir = tmp_path / "出视频" / "第1集" / "prompt"
    routes_dir.mkdir(parents=True)
    (routes_dir / "video_model_routes.json").write_text(json.dumps({
        "kind": "n2d_video_model_routes",
        "routes": [
            {"clip_id": "Clip_01", "primary_backend": "Veo 3.1", "native_audio_policy": "native_speech", "mode": "native_av"},
            {"clip_id": "Clip_02", "primary_backend": "Dreamina", "native_audio_policy": "none", "mode": "image2video"},
        ],
    }, ensure_ascii=False), encoding="utf-8")

    profile = adapter.route_native_audio_profile(str(tmp_path), "第1集")

    assert profile["native_audio"] is True
    assert profile["hits"][0]["clip_id"] == "Clip_01"


def test_dreamina_refresh_evidence_includes_cli_snapshot(tmp_path):
    path = adapter.write_refresh_evidence(
        str(tmp_path),
        "Seedance 2.0",
        channel="即梦/Dreamina",
        sources=["n2d static profile"],
        evidence_kind="cli_snapshot",
        today="2026-06-26",
    )
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["cli_snapshot_evidence"]
    assert data["cli_snapshot_evidence"][0]["cli"] == "dreamina"
    assert any(str(src).startswith("cli_snapshot:dreamina@") for src in data["sources"])


def test_refresh_evidence_requires_structured_capability_assertions(tmp_path):
    path = adapter.refresh_evidence_path(str(tmp_path), "Veo 3.1", "Google Gemini API")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "kind": "n2d_video_backend_refresh_evidence",
        "backend": "veo",
        "channel": "google_gemini_api",
        "verified_at": "2026-06-21",
        "sources": ["official docs"],
        "note": "old freeform evidence only",
    }, ensure_ascii=False), encoding="utf-8")

    status = adapter.refresh_evidence_status(
        str(tmp_path),
        "Veo 3.1",
        "Google Gemini API",
        today=dt.date(2026, 6, 21),
    )

    assert status["status"] == "missing_capability_assertions"


def test_refresh_evidence_rejects_bare_capability_values(tmp_path):
    path = adapter.refresh_evidence_path(str(tmp_path), "Veo 3.1", "Google Gemini API")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "kind": "n2d_video_backend_refresh_evidence",
        "backend": "veo",
        "channel": "google_gemini_api",
        "verified_at": "2026-06-21",
        "sources": ["official docs"],
        "capability_assertions": {"supports_last_frame": True},
        "note": "old bare capability values",
    }, ensure_ascii=False), encoding="utf-8")

    status = adapter.refresh_evidence_status(
        str(tmp_path),
        "Veo 3.1",
        "Google Gemini API",
        today=dt.date(2026, 6, 21),
    )

    assert status["status"] == "missing_capability_evidence"


def test_parse_capability_overrides_coerces_values():
    out = adapter.parse_capability_overrides([
        "supports_last_frame=false",
        "max_clip_seconds=12",
        "motion_control_capabilities=pose,depth",
    ])
    assert out["supports_last_frame"] is False
    assert out["max_clip_seconds"] == 12
    assert out["motion_control_capabilities"] == ["pose", "depth"]


# ── 付费出视频前后端连通性探针（与 image_backends.probe_backend 同状态语义）──
def test_probe_video_unknown_when_no_health_url():
    # 默认无健康端点 url → unknown（gate 降级 WARN，graceful，不假 BLOCK）
    status, _ = adapter.probe_video_backend("即梦/Dreamina", env={})
    assert status == "unknown"


def test_probe_video_skip_flag_is_unknown():
    status, detail = adapter.probe_video_backend("即梦/Dreamina", env={"N2D_SKIP_BACKEND_PROBE": "1"})
    assert status == "unknown" and "N2D_SKIP_BACKEND_PROBE" in detail


def test_probe_video_manual_or_off_is_unknown():
    assert adapter.probe_video_backend("人工", env={})[0] == "unknown"
    assert adapter.probe_video_backend("", env={})[0] == "unknown"


def test_probe_video_unrecognized_channel_is_unknown_not_down():
    # 不认识的渠道=探不了≠不可达：必须 unknown，不能假 BLOCK
    assert adapter.probe_video_backend("某不存在后端", env={})[0] == "unknown"


def test_probe_video_health_url_502_is_down():
    # 导出健康端点 + 探针返回 502 → down（gate BLOCK）
    status, detail = adapter.probe_video_backend(
        "即梦/Dreamina",
        env={"N2D_VIDEO_BACKEND_BASE_URL": "http://10.0.0.1:9"},
        http_runner=lambda url, timeout: ("down", "HTTP 502"))
    assert status == "down" and "502" in detail


def test_probe_video_per_backend_url_overrides_generic():
    # 后端专属 *_BASE_URL 优先于通用 N2D_VIDEO_BACKEND_BASE_URL
    seen = {}
    def runner(url, timeout):
        seen["url"] = url
        return ("ok", "")
    status, _ = adapter.probe_video_backend(
        "kling",
        env={"N2D_VIDEO_KLING_BASE_URL": "http://kling.internal",
             "N2D_VIDEO_BACKEND_BASE_URL": "http://generic.internal"},
        http_runner=runner)
    assert status == "ok" and seen["url"].startswith("http://kling.internal")
