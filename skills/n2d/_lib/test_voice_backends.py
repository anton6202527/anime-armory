"""voice backend candidate catalog tests."""
from __future__ import annotations

import voice_backends as backends


def test_current_voice_model_aliases_normalize_without_switching_endpoint_contract():
    assert backends.normalize_voice_backend("CosyVoice 3") == "cosyvoice"
    assert backends.normalize_voice_backend("Fish Audio S2 / s2-pro") == "fishspeech"
    assert backends.normalize_voice_backend("IndexTTS-2.5") == "indextts"
    assert backends.spec_by_key("cosyvoice")["env"] == "COSYVOICE_URL"


def test_current_voice_capabilities_are_machine_readable():
    cosy = backends.spec_by_key("cosyvoice")
    fish = backends.spec_by_key("fishspeech")
    index = backends.spec_by_key("indextts")
    assert cosy["model_generation"] == "3"
    assert fish["api_model_id"] == "s2-pro"
    assert tuple(index["duration_factor_range"]) == (0.5, 2.0)
    assert backends.CATALOG_VERIFIED["date"] == "2026-08-26"


def test_legacy_renderer_shape_remains_stable():
    rows = backends.zs_specs_legacy()
    assert rows
    assert all(len(row) == 4 for row in rows)
    assert rows[0][0] == "COSYVOICE_URL"
