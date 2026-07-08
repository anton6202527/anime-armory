"""image_backend_adapter 能力归一与 per-run 刷新证据单测。"""
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
    spec = importlib.util.spec_from_file_location("image_backend_adapter", lib_dir / "image_backend_adapter.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


adapter = _load()


def test_alias_normalizes_to_capability_profile():
    data = adapter.backend_adapter("Nano Banana")
    assert data["canonical"] == "nano_banana"
    assert data["transport"] == "generate_content_parts"
    assert data["supports_high_fidelity_reference"] is True


def test_mask_workload_blocks_backend_without_mask_path():
    codex = adapter.score_backend(adapter.backend_adapter("Codex"), {"needs_mask": True})
    openai = adapter.score_backend(adapter.backend_adapter("OpenAI"), {"needs_mask": True})
    assert codex["verdict"] == "blocked"
    assert any("mask" in item for item in codex["blockers"])
    assert openai["verdict"] != "blocked"


def test_core_long_running_workload_recommends_native_subject_upgrade():
    rec = adapter.recommend_backend(
        "Codex",
        {"core_character": True, "needs_persistent_subject": True, "reference_images": 6},
    )
    assert rec["upgrade_recommended"] is True
    assert rec["recommended"]["backend"] in {"seedream", "kling"}
    assert rec["adapter"]["persistent_subject"] is True


def test_standard_catalog_is_backend_neutral():
    catalog = adapter.standards_catalog()
    ids = {row["id"] for row in catalog["standards"]}
    assert "identity_continuity" in ids
    assert "reference_ingestion" in ids
    assert "codex" not in json_repr(catalog).lower()


def json_repr(value):
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def test_standard_plan_loads_codex_mitigations_for_multi_subject():
    plan = adapter.standard_plan(
        "Codex",
        {"has_characters": True, "characters": 2, "multi_character": True, "closeup": True, "reference_images": 8},
    )
    assert plan["status"] == "mitigations_required"
    text = json_repr(plan)
    assert "split_composite_required" in text
    assert "reference_manifest" in text


def test_standard_plan_uses_native_subject_when_available():
    plan = adapter.standard_plan(
        "Seedream",
        {"has_characters": True, "core_character": True, "reference_images": 6},
    )
    identity = [row for row in plan["standards"] if row["standard"] == "identity_continuity"][0]
    assert identity["status"] == "native"
    assert "persistent_subject" in identity["native_support"]


def test_refresh_evidence_status_lifecycle(tmp_path):
    missing = adapter.refresh_evidence_status(str(tmp_path), "Codex", today=dt.date(2026, 6, 20))
    assert missing["status"] == "missing"

    path = adapter.write_refresh_evidence(
        str(tmp_path),
        "Codex",
        sources=["https://platform.openai.com/docs/guides/image-generation"],
        source_urls=["https://platform.openai.com/docs/guides/image-generation"],
        evidence_kind="official_docs",
        note="checked official guide and local CLI help",
        today="2026-06-20",
    )
    assert path.exists()
    fresh = adapter.refresh_evidence_status(str(tmp_path), "Codex", today=dt.date(2026, 6, 20))
    stale = adapter.refresh_evidence_status(str(tmp_path), "Codex", today=dt.date(2026, 6, 21))
    assert fresh["status"] == "fresh"
    assert fresh["capability_assertions"]["supports_image_reference"]["value"] is True
    assert fresh["capability_assertions"]["supports_image_reference"]["evidence_kind"] == "official_docs"
    assert stale["status"] == "stale"


def test_codex_model_label_distinguishes_exact_model_evidence(tmp_path):
    data = adapter.backend_adapter("Codex")
    assert data["model"] == "GPT Image 2"
    assert data["model_precision"] == "normalized_family"
    assert data["exact_model_evidence_required"] is True

    adapter.write_refresh_evidence(
        str(tmp_path),
        "Codex",
        sources=["OpenAI Images docs + Codex CLI output"],
        source_urls=["https://platform.openai.com/docs/guides/image-generation"],
        evidence_kind="official_docs",
        note="exact model id exposed by this run",
        exact_model_id="gpt-image-2",
        today="2026-07-07",
    )
    fresh = adapter.refresh_evidence_status(str(tmp_path), "Codex", today=dt.date(2026, 7, 7))
    assert fresh["status"] == "fresh"
    assert fresh["capability_assertions"]["exact_model_id"]["value"] == "gpt-image-2"
    assert fresh["capability_assertions"]["model_precision"]["value"] == "provider_model"


def test_image_backend_baseline_detects_project_switch(tmp_path):
    (tmp_path / "_设置.md").write_text("- 生图AI: Codex\n- 生图模型: GPT Image 2\n", encoding="utf-8")
    path = adapter.write_image_backend_baseline(str(tmp_path))
    assert path.exists()
    assert adapter.image_backend_baseline_status(str(tmp_path))["status"] == "matched"

    (tmp_path / "_设置.md").write_text("- 生图AI: Seedream\n- 生图模型: Seedream 4.5\n", encoding="utf-8")
    status = adapter.image_backend_baseline_status(str(tmp_path))
    assert status["status"] == "changed"
    assert "backend" in status["changed_fields"]
    assert status["baseline"]["backend"] == "codex"
    assert status["current"]["backend"] == "seedream"


def test_image_backend_baseline_treats_access_alias_as_same_backend(tmp_path):
    prod = tmp_path / "生产数据"
    prod.mkdir()
    (tmp_path / "_设置.md").write_text("- 生图AI: Codex\n- 生图模型: GPT Image 2\n", encoding="utf-8")
    (prod / "image_backend_baseline.json").write_text(json.dumps({
        "kind": "n2d_image_backend_baseline",
        "version": 1,
        "selection": {
            "backend": "codex",
            "access": "Codex only",
            "image_model": "GPT Image 2",
            "channel": "Codex CLI",
        },
    }, ensure_ascii=False), encoding="utf-8")

    status = adapter.image_backend_baseline_status(str(tmp_path))

    assert status["status"] == "matched"
    assert status["changed_fields"] == []


def test_refresh_evidence_requires_structured_capability_assertions(tmp_path):
    path = adapter.refresh_evidence_path(str(tmp_path), "Codex")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "kind": "n2d_image_backend_refresh_evidence",
        "backend": "codex",
        "verified_at": "2026-06-20",
        "sources": ["official docs"],
        "note": "old freeform evidence only",
    }, ensure_ascii=False), encoding="utf-8")

    status = adapter.refresh_evidence_status(str(tmp_path), "Codex", today=dt.date(2026, 6, 20))

    assert status["status"] == "missing_capability_assertions"


def test_refresh_evidence_rejects_bare_capability_values(tmp_path):
    path = adapter.refresh_evidence_path(str(tmp_path), "Codex")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "kind": "n2d_image_backend_refresh_evidence",
        "backend": "codex",
        "verified_at": "2026-06-20",
        "sources": ["official docs"],
        "capability_assertions": {"supports_image_reference": True},
        "note": "old bare capability values",
    }, ensure_ascii=False), encoding="utf-8")

    status = adapter.refresh_evidence_status(str(tmp_path), "Codex", today=dt.date(2026, 6, 20))

    assert status["status"] == "missing_capability_evidence"


def test_sora_cameo_forbids_face_upload_and_requires_authorization():
    a = adapter.backend_adapter("sora")
    assert adapter.forbids_face_reference_upload(a) is True
    assert adapter.requires_cameo_authorization(a) is True
    # 普通可喂脸后端不触发
    codex = adapter.backend_adapter("codex")
    assert adapter.forbids_face_reference_upload(codex) is False
    assert adapter.requires_cameo_authorization(codex) is False


def test_cameo_policy_findings_blocks_face_upload_and_missing_auth():
    sora = adapter.backend_adapter("sora")
    # 喂了脸锚 + 未授权 → 两条 block
    f = adapter.cameo_policy_findings(sora, feeds_face_references=True, authorization_status=None)
    codes = {x["code"] for x in f}
    assert codes == {"cameo_face_upload_forbidden", "cameo_authorization_required"}
    assert all(x["level"] == "block" for x in f)
    # 不喂脸 + 已授权 → 放行（空）
    assert adapter.cameo_policy_findings(sora, feeds_face_references=False, authorization_status="approved") == []
    # 普通后端恒空，即便喂脸
    codex = adapter.backend_adapter("codex")
    assert adapter.cameo_policy_findings(codex, feeds_face_references=True, authorization_status=None) == []


def test_reference_budget_for_reports_per_backend_caps():
    assert adapter.reference_budget_for(adapter.backend_adapter("nano_banana"))["character_refs"] == 5
    assert adapter.reference_budget_for(adapter.backend_adapter("seedream"))["max_total"] == 14
