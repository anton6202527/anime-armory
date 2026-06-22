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
    assert data["anchor_consumption_sample"]["consumption_mode"] == "native_multiframe"


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
    assert stale["status"] == "stale"


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
