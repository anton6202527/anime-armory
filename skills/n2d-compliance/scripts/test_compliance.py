from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("compliance.py")
spec = importlib.util.spec_from_file_location("n2d_compliance", SCRIPT)
compliance = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(compliance)


def test_init_manifest_uses_identity_registry_characters(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    reg = root / "出图" / "common"
    reg.mkdir(parents=True)
    (reg / "identity_registry.json").write_text(
        json.dumps({"characters": [{"id": "CHAR_A"}, {"id": "CHAR_B"}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    path = compliance.write_manifest(root, "第1集")
    data = json.loads(path.read_text(encoding="utf-8"))

    ids = [item["character_id"] for item in data["character_likeness"]["characters"]]
    assert ids == ["CHAR_A", "CHAR_B"]
    assert data["ai_disclosure"]["required"] is True


def test_check_manifest_reports_missing_registry_character(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    reg = root / "出图" / "common"
    comp = root / "合规"
    reg.mkdir(parents=True)
    comp.mkdir(parents=True)
    (reg / "identity_registry.json").write_text(
        json.dumps({"characters": [{"id": "CHAR_A"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    data = compliance.default_manifest(root, "第1集")
    data["character_likeness"]["characters"] = []
    (comp / "compliance_manifest.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    issues = compliance.check_manifest(root, "第1集")

    assert any("CHAR_A" in item for item in issues)


def test_check_manifest_requires_rights_fields(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    comp = root / "合规"
    comp.mkdir(parents=True)
    data = compliance.default_manifest(root, "第1集")
    del data["rights"]["adaptation"]
    data["rights"]["source_text"]["evidence"] = ""
    (comp / "compliance_manifest.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    issues = compliance.check_manifest(root, "第1集")

    assert any("rights.adaptation" in item for item in issues)
    assert any("rights.source_text" in item and "evidence" in item for item in issues)


def test_check_manifest_blocks_invalid_rights_status(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    comp = root / "合规"
    comp.mkdir(parents=True)
    data = compliance.default_manifest(root, "第1集")
    data["rights"]["source_text"] = {"status": "pending", "evidence": "作者自有项目"}
    data["rights"]["adaptation"] = {"status": "user_declared", "evidence": "同源改编"}
    data["platform_review"]["targets"][0].update({
        "platform": "抖音",
        "region": "CN",
        "policy_profile": "douyin_ai_disclosure_2026-06-08",
        "profile_checked_at": "2026-06-08",
        "copyright_review": "ready",
        "ai_disclosure_upload": "ready",
        "content_rating_review": "ready",
    })
    (comp / "compliance_manifest.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    issues = compliance.check_manifest(root, "第1集")

    assert any("rights.source_text" in item and "status must be one of" in item and "pending" in item for item in issues)


def test_check_manifest_blocks_invalid_character_voice_ai_and_watermark_status(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    reg = root / "出图" / "common"
    comp = root / "合规"
    reg.mkdir(parents=True)
    comp.mkdir(parents=True)
    (reg / "identity_registry.json").write_text(
        json.dumps({"characters": [{"id": "CHAR_A"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    data = compliance.default_manifest(root, "第1集")
    data["rights"]["source_text"] = {"status": "original", "evidence": "作者自有项目"}
    data["rights"]["adaptation"] = {"status": "original", "evidence": "同源改编"}
    data["character_likeness"]["characters"][0]["status"] = "unknown"
    data["voice"]["status"] = "pending"
    data["ai_disclosure"]["visible_label"]["status"] = "pending"
    data["watermark"]["ai_visible"]["status"] = "pending"
    data["platform_review"]["targets"][0].update({
        "platform": "抖音",
        "region": "CN",
        "policy_profile": "douyin_ai_disclosure_2026-06-08",
        "profile_checked_at": "2026-06-08",
        "copyright_review": "ready",
        "ai_disclosure_upload": "ready",
        "content_rating_review": "ready",
    })
    (comp / "compliance_manifest.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    issues = compliance.check_manifest(root, "第1集")

    assert any("character_likeness.CHAR_A" in item and "unknown" in item for item in issues)
    assert any("voice status" in item and "pending" in item for item in issues)
    assert any("ai_disclosure.visible_label" in item and "pending" in item for item in issues)
    assert any("watermark.ai_visible" in item and "pending" in item for item in issues)


def test_check_manifest_blocks_overseas_target_without_localization(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    comp = root / "合规"
    comp.mkdir(parents=True)
    data = compliance.default_manifest(root, "第1集")
    data["rights"]["source_text"] = {"status": "original", "evidence": "作者自有项目"}
    data["rights"]["adaptation"] = {"status": "original", "evidence": "同源改编"}
    data["platform_review"]["targets"][0].update({
        "platform": "YouTube",
        "region": "US",
        "language": "en",
        "policy_profile": "youtube_ai_disclosure_2026-06-08",
        "profile_checked_at": "2026-06-08",
        "copyright_review": "ready",
        "ai_disclosure_upload": "ready",
        "content_rating_review": "ready",
        "requires_localization": True,
    })
    data["localization"]["status"] = "not_applicable"
    data["localization"]["subtitle_languages"] = ["zh"]
    (comp / "compliance_manifest.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    issues = compliance.check_manifest(root, "第1集")

    assert any("localization.status" in item and "YouTube" in item for item in issues)
    assert any("subtitle_languages" in item and "en" in item for item in issues)


def test_check_manifest_blocks_placeholder_values(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    comp = root / "合规"
    comp.mkdir(parents=True)
    data = compliance.default_manifest(root, "第1集")
    (comp / "compliance_manifest.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    issues = compliance.check_manifest(root, "第1集")

    assert any("rights.source_text" in item and "evidence" in item for item in issues)
    assert any("rights.adaptation" in item and "evidence" in item for item in issues)
    assert any("platform_review.targets[1]" in item and "platform" in item for item in issues)
    assert any("platform_review.targets[1]" in item and "policy_profile" in item for item in issues)


def test_check_manifest_blocks_invalid_platform_review_fields(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    comp = root / "合规"
    comp.mkdir(parents=True)
    data = compliance.default_manifest(root, "第1集")
    data["rights"]["source_text"]["evidence"] = "作者自有项目"
    data["rights"]["adaptation"]["evidence"] = "同源改编"
    data["platform_review"]["targets"][0].update({
        "platform": "not_applicable",
        "region": "ready",
        "policy_profile": "douyin_ai_disclosure",
        "profile_checked_at": "ready",
        "copyright_review": "douyin",
    })
    (comp / "compliance_manifest.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    issues = compliance.check_manifest(root, "第1集")

    assert any("platform" in item and "concrete value" in item for item in issues)
    assert any("region" in item and "concrete value" in item for item in issues)
    assert any("policy_profile" in item and "YYYY-MM-DD" in item for item in issues)
    assert any("profile_checked_at" in item and "YYYY-MM-DD" in item for item in issues)
    assert any("copyright_review" in item and "ready/done/not_applicable" in item for item in issues)


def test_internal_only_downgrades_platform_fields_but_keeps_authorization_blocks(tmp_path: Path) -> None:
    """internal_only：platform_review/localization 域降 INFO（带免检注），授权/AI 标识照常 BLOCK。"""
    root = tmp_path / "制漫剧" / "测试剧"
    comp = root / "合规"
    comp.mkdir(parents=True)
    data = compliance.default_manifest(root, "第1集")
    data["distribution_intent"] = "internal_only"
    data["rights"]["source_text"] = {"status": "original", "evidence": "作者自有项目"}
    data["rights"]["adaptation"] = {"status": "original", "evidence": "同源改编"}
    # 海外目标缺本地化（投放流程会 BLOCK 的场景）
    data["platform_review"]["targets"][0].update({
        "platform": "YouTube",
        "region": "US",
        "language": "en",
        "policy_profile": "youtube_ai_disclosure_2026-06-08",
        "profile_checked_at": "2026-06-08",
        "copyright_review": "ready",
        "ai_disclosure_upload": "ready",
        "content_rating_review": "ready",
        "requires_localization": True,
    })
    data["localization"]["status"] = "not_applicable"
    data["localization"]["subtitle_languages"] = ["zh"]
    # 声音克隆未授权（授权域，internal_only 不豁免）
    data["voice"]["status"] = "unknown"
    (comp / "compliance_manifest.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    issues = compliance.check_manifest(root, "第1集")

    platform_issues = [i for i in issues if "localization" in i or "platform_review" in i]
    assert platform_issues, "平台域问题应仍被报出（只是降级）"
    assert all(i.startswith("INFO ") and "内部 demo 免检" in i for i in platform_issues)
    voice_issues = [i for i in issues if "voice" in i]
    assert voice_issues and all(i.startswith("BLOCK ") for i in voice_issues), "声音授权 internal_only 不豁免"


def _msgs(issues):
    """只取 '<sev> <path>.json: <message>' 的消息体，避开 pytest 临时目录名里的 regulatory_filing 干扰。"""
    return [(i.split(".json: ", 1)[-1], i.split(" ", 1)[0]) for i in issues]


def _full_manifest(compliance, root):
    """A default manifest with the regulatory_filing fields properly filled (releasable)."""
    data = compliance.default_manifest(root, "第1集")
    data["distribution_intent"] = "paid_distribution"
    reg = data["regulatory_filing"]
    reg["tier"] = "其他"
    reg["planning_filing_no"] = "网微剧备字(2026)第001号"
    reg["release_filing_no"] = "网微剧上字(2026)第001号"
    reg["pre_broadcast_review"] = "done"
    reg["filed_at"] = "2026-06-01"
    return data


def test_regulatory_filing_missing_section_blocks(tmp_path):
    root = tmp_path / "制漫剧" / "剧"
    (root / "合规").mkdir(parents=True)
    data = compliance.default_manifest(root, "第1集")
    data["distribution_intent"] = "paid_distribution"
    del data["regulatory_filing"]
    (root / "合规" / "compliance_manifest.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    issues = compliance.check_manifest(root, "第1集")
    assert any("missing regulatory_filing" in m for m, _ in _msgs(issues))


def test_regulatory_filing_pending_blocks_paid(tmp_path):
    root = tmp_path / "制漫剧" / "剧"
    (root / "合规").mkdir(parents=True)
    data = compliance.default_manifest(root, "第1集")
    data["distribution_intent"] = "paid_distribution"  # default reg: pending + TODO 备案号
    (root / "合规" / "compliance_manifest.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    issues = compliance.check_manifest(root, "第1集")
    assert any(sev == "BLOCK" and "pre_broadcast_review" in m for m, sev in _msgs(issues))
    assert any(sev == "BLOCK" and "release_filing_no" in m for m, sev in _msgs(issues))


def test_regulatory_filing_filled_passes(tmp_path):
    root = tmp_path / "制漫剧" / "剧"
    (root / "合规").mkdir(parents=True)
    data = _full_manifest(compliance, root)
    (root / "合规" / "compliance_manifest.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    issues = compliance.check_manifest(root, "第1集")
    assert not any("regulatory_filing" in m for m, _ in _msgs(issues)), [m for m, _ in _msgs(issues) if "regulatory_filing" in m]


def test_regulatory_filing_internal_only_downgrades_to_info(tmp_path):
    root = tmp_path / "制漫剧" / "剧"
    (root / "合规").mkdir(parents=True)
    data = compliance.default_manifest(root, "第1集")
    data["distribution_intent"] = "internal_only"  # default reg pending/TODO
    (root / "合规" / "compliance_manifest.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    issues = compliance.check_manifest(root, "第1集")
    reg_issues = [(m, sev) for m, sev in _msgs(issues) if "regulatory_filing" in m]
    assert reg_issues and all(sev == "INFO" for _, sev in reg_issues), reg_issues


def test_regulatory_filing_not_applicable_needs_reason(tmp_path):
    root = tmp_path / "制漫剧" / "剧"
    (root / "合规").mkdir(parents=True)
    data = compliance.default_manifest(root, "第1集")
    data["distribution_intent"] = "paid_distribution"
    data["regulatory_filing"]["applicable"] = False
    data["regulatory_filing"]["notes"] = ""  # no reason
    (root / "合规" / "compliance_manifest.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    issues = compliance.check_manifest(root, "第1集")
    assert any("applicable=false" in m for m, _ in _msgs(issues))
