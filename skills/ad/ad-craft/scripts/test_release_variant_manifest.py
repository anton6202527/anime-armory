import hashlib
import json
from datetime import date
from pathlib import Path

import release_variant_manifest as rvm
import dependency_graph
import placement_adaptation
import render_profile


def _sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _refresh_release_chain(root: Path):
    """Materialise the canonical plan/QC/profile/adaptation/compose evidence."""
    delivery = {
        "deliverable_id": "master", "label": "主片", "kind": "master", "duration": "2s",
        "aspect": "9:16", "expected_path": "合成/成片_主片.mp4", "status": "rendered",
        "exists": True, "target_placements": ["TikTok:auction_in_feed"],
    }
    profile = render_profile.write_profile(root)
    profile_ref = render_profile.compact_ref(profile)
    adaptation = placement_adaptation.write_report(root, deliverables=[delivery])
    adaptation_item = dict(adaptation["items"][0])
    plan = {
        "schema_version": 5, "kind": "ad_delivery_plan", "project_root": str(root.resolve()),
        "render_profile": profile_ref,
        "placement_adaptation": {
            "path": "生产数据/placement_adaptation.json", "sha256": adaptation["plan_sha256"],
            "summary": adaptation["summary"],
        },
        "summary": {"block": 0},
        "deliverables": [{**delivery, "render_profile": profile_ref,
                          "placement_adaptation": adaptation_item}],
    }
    _write_json(root / "合成" / "delivery_plan.json", plan)
    media_sha = _sha(root / delivery["expected_path"])
    qc = {
        "schema_version": 2, "kind": "ad_delivery_qc",
        "delivery_plan_sha256": rvm.canonical_sha(plan),
        "media_sha256_by_deliverable": {"master": media_sha},
        "render_profile_sha256": profile_ref["sha256"],
        "placement_adaptation_sha256": adaptation["plan_sha256"],
        "adaptation_execution_sha256_by_deliverable": {},
        "items": [{"deliverable_id": "master", "path": delivery["expected_path"],
                   "passed": True, "findings": []}],
        "summary": {"block": 0, "warn": 0, "passed": 1}, "findings": [],
    }
    _write_json(root / "合成" / "delivery_qc.json", qc)
    receipt_path = root / "生产数据" / "dependency_receipts.json"
    if receipt_path.exists():
        receipt_path.unlink()
    acceptance = {
        "schema_version": 1, "kind": "ad_stage_acceptance", "stage": "compose", "mode": "formal",
        "contract_version": dependency_graph.contract.CONTRACT_VERSION,
        "acceptance_version": dependency_graph.contract.STAGE_ACCEPTANCE_VERSION,
        "dependency_snapshot_sha256": dependency_graph.stage_snapshot_sha256(root, "compose"),
        "findings": [], "summary": {"block": 0, "warn": 0, "accepted": True},
    }
    _write_json(root / "生产数据" / "stage_acceptance" / "compose.json", acceptance)
    dependency_graph.accept_stage(root, "compose")


def _project(tmp_path: Path, *, ai=True):
    root = tmp_path / "ad"
    for rel, content in {
        "脚本/voiceover.txt": "山岚咖啡，立即购买",
        "脚本/字幕_zh.srt": "1\n00:00:00,000 --> 00:00:02,000\n山岚咖啡，立即购买\n",
        "脚本/广告法机检报告.json": json.dumps({"summary": {"block": 0, "warn": 0}}),
        "证据/claim.md": "品牌事实依据",
        "证据/typography.md": "排版复核",
        "合规/tiktok-safe.png": "placement template",
        "合规/ai-label.png": "platform receipt",
        "合规/commercial-disclosure.png": "paid partnership / ad disclosure receipt",
    }.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    master = root / "合成" / "成片_主片.mp4"
    master.parent.mkdir(parents=True)
    master.write_bytes(b"current-master")
    digest = _sha(master)
    brief = {
        "campaign_mode": "formal", "brand": "山岚", "product": "咖啡", "platforms": ["TikTok"],
        "deliverables": {"duration": "2s", "aspect": "9:16"},
        "placements": ["TikTok:auction_in_feed"],
        "platform_safe_zone_evidence": {"TikTok:auction_in_feed": "合规/tiktok-safe.png"},
        "release_regions": ["中国大陆"],
        "claims": [{"id": "claim_01", "claim": "山岚咖啡", "evidence_type": "brand_fact",
                    "evidence": "品牌档案", "evidence_file": "证据/claim.md", "method": "品牌档案核验",
                    "date": "2026-07-01", "territory": "中国大陆", "approved_by": "法务甲"}],
        "rights": {key: {"status": "not_used", "territory": "中国大陆", "media_scope": "all",
                         "approved_by": "制片甲"} for key in ("talent", "music", "fonts", "assets")},
        "mandatories": {"legal_lines": ["广告"], "cta": "立即购买"},
        "ai_label_receipts": [{"deliverable_id": "master", "platform": "TikTok",
                               "placement": "TikTok:auction_in_feed", "asset_sha256": digest,
                               "status": "completed", "label_mode": "platform_managed",
                               "checked_at": date.today().isoformat(), "approved_by": "发布甲",
                               "evidence_file": "合规/ai-label.png"}] if ai else [],
        "commercial_content": {"relationship_type": "brand_owned_paid_ad", "creator_involved": False},
        "commercial_disclosure_receipts": [{
            "deliverable_id": "master", "platform": "TikTok", "placement": "TikTok:auction_in_feed",
            "asset_sha256": digest, "status": "completed",
            "relationship_type": "brand_owned_paid_ad", "disclosure_mode": "platform_paid_ad_label",
            "platform_record_id": "tt-ad-001", "checked_at": date.today().isoformat(), "approved_by": "发布甲",
            "evidence_file": "合规/commercial-disclosure.png",
        }],
    }
    (root / "需求").mkdir()
    (root / "需求" / "brief.json").write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    (root / "脚本" / "storyboard.json").write_text(json.dumps({"shots": [{
        "shot_id": "S1", "duration": 2, "assets": {"PROD_COFFEE": True, "BRAND_SHANLAN": True},
        "claim_ids": ["claim_01"], "disclosures": [{"claim_id": "claim_01", "text": "品牌档案"}],
    }]}), encoding="utf-8")
    locale = {
        "schema_version": 1, "kind": "ad_locale_matrix", "default_locale": "zh-CN",
        "locales": {"zh-CN": {"language": "zh-CN", "jurisdictions": ["中国大陆"],
            "currency": "CNY", "unit_system": "metric", "cta": "立即购买", "legal_lines": ["广告"],
            "voiceover_path": "脚本/voiceover.txt", "subtitle_path": "脚本/字幕_zh.srt",
            "translation_review": {"status": "source_language"},
            "typography_review": {"status": "approved", "approved_by": "设计甲",
                                    "evidence": "证据/typography.md"}}},
        "deliverable_locales": {"master": ["zh-CN"]},
    }
    (root / "合规" / "locale_matrix.json").write_text(json.dumps(locale, ensure_ascii=False), encoding="utf-8")
    (root / "合规" / "ai_usage.json").write_text(json.dumps({
        "visual_mode": "AI-generated" if ai else "live-action",
        "video_mode": "AI-generated" if ai else "live-action",
    }), encoding="utf-8")
    _refresh_release_chain(root)
    return root, digest


def test_release_variant_manifest_binds_full_release_chain(tmp_path):
    root, digest = _project(tmp_path)
    report = rvm.build(root)
    assert report["summary"]["release_ready"] is True
    row = report["variants"][0]
    assert row["sha256"] == digest
    assert row["placements"] == ["TikTok:auction_in_feed"]
    assert row["jurisdictions"] == ["中国大陆"]
    assert row["claims"][0]["disclosures"]
    assert all(right["covered"] for right in row["rights"])
    assert row["ai_label_receipts"][0]["valid"] is True
    assert row["commercial_disclosure_receipts"][0]["valid"] is True


def test_formal_release_fails_closed_when_chain_artifact_is_missing(tmp_path):
    root, _ = _project(tmp_path)
    (root / "合成" / "delivery_qc.json").unlink()
    report = rvm.build(root)
    assert report["summary"]["release_ready"] is False
    assert "release_delivery_qc_schema_invalid" in {row["code"] for row in report["findings"]}


def test_formal_release_fails_closed_on_stale_qc_binding(tmp_path):
    root, _ = _project(tmp_path)
    path = root / "合成" / "delivery_qc.json"
    qc = json.loads(path.read_text(encoding="utf-8"))
    qc["delivery_plan_sha256"] = "0" * 64
    _write_json(path, qc)
    report = rvm.build(root)
    assert report["summary"]["release_ready"] is False
    assert "release_delivery_qc_plan_stale" in {row["code"] for row in report["findings"]}


def test_formal_release_fails_closed_on_explicit_plan_block(tmp_path):
    root, _ = _project(tmp_path)
    path = root / "合成" / "delivery_plan.json"
    plan = json.loads(path.read_text(encoding="utf-8"))
    plan["summary"]["block"] = 1
    _write_json(path, plan)
    report = rvm.build(root)
    assert report["summary"]["release_ready"] is False
    assert "release_delivery_plan_blocked" in {row["code"] for row in report["findings"]}


def test_formal_release_revalidates_profile_and_adaptation_inputs(tmp_path):
    root, _ = _project(tmp_path)
    (root / "_设置.md").write_text("视频分辨率: 720p\n", encoding="utf-8")
    report = rvm.build(root)
    assert "release_render_profile_stale" in {row["code"] for row in report["findings"]}

    root, _ = _project(tmp_path / "second")
    storyboard_path = root / "脚本" / "storyboard.json"
    storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
    storyboard["shots"][0]["visual_risk_revision"] = 2
    _write_json(storyboard_path, storyboard)
    report = rvm.build(root)
    assert "release_placement_adaptation_stale" in {row["code"] for row in report["findings"]}


def test_formal_release_requires_current_compose_acceptance_and_receipt(tmp_path):
    root, _ = _project(tmp_path)
    (root / "生产数据" / "stage_acceptance" / "compose.json").unlink()
    report = rvm.build(root)
    assert "release_compose_acceptance_missing_or_stale" in {row["code"] for row in report["findings"]}

    root, _ = _project(tmp_path / "second")
    (root / "生产数据" / "dependency_receipts.json").unlink()
    report = rvm.build(root)
    assert "release_compose_receipt_missing_or_stale" in {row["code"] for row in report["findings"]}


def test_ai_label_receipt_is_invalidated_by_media_change(tmp_path):
    root, _ = _project(tmp_path)
    (root / "合成" / "成片_主片.mp4").write_bytes(b"changed-master")
    report = rvm.build(root)
    assert any(row["code"] == "ai_label_receipt_invalid" for row in report["findings"])
    assert any(row["code"] == "commercial_disclosure_receipt_invalid" for row in report["findings"])


def test_ai_label_does_not_substitute_for_commercial_disclosure(tmp_path):
    root, _ = _project(tmp_path)
    brief_path = root / "需求" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["commercial_disclosure_receipts"] = []
    brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")

    report = rvm.build(root)

    assert any(row["code"] == "commercial_disclosure_receipt_missing" for row in report["findings"])
    assert report["summary"]["release_ready"] is False


def test_live_action_still_requires_commercial_disclosure(tmp_path):
    root, _ = _project(tmp_path, ai=False)
    report = rvm.build(root)

    assert report["uses_ai"] is False
    assert report["summary"]["release_ready"] is True
    assert report["variants"][0]["ai_label_receipts"] == []
    assert report["variants"][0]["commercial_disclosure_receipts"][0]["valid"] is True


def test_empty_receipt_scope_is_not_a_cross_platform_wildcard(tmp_path):
    root, _ = _project(tmp_path)
    brief_path = root / "需求" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    for key in ("ai_label_receipts", "commercial_disclosure_receipts"):
        brief[key][0].pop("platform")
        brief[key][0].pop("placement")
    brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")

    report = rvm.build(root)
    codes = {row["code"] for row in report["findings"]}

    assert {"ai_label_receipt_missing", "commercial_disclosure_receipt_missing"} <= codes
    assert report["summary"]["release_ready"] is False


def test_duplicate_exact_receipts_are_ambiguous_not_first_match_wins(tmp_path):
    root, _ = _project(tmp_path)
    brief_path = root / "需求" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["ai_label_receipts"].append(dict(brief["ai_label_receipts"][0]))
    brief["commercial_disclosure_receipts"].append(dict(brief["commercial_disclosure_receipts"][0]))
    brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")

    report = rvm.build(root)
    codes = {row["code"] for row in report["findings"]}

    assert {"ai_label_receipt_ambiguous", "commercial_disclosure_receipt_ambiguous"} <= codes


def test_release_receipts_expire_after_house_freshness_window(tmp_path):
    root, _ = _project(tmp_path)
    brief_path = root / "需求" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["ai_label_receipts"][0]["checked_at"] = "2020-01-01"
    brief["commercial_disclosure_receipts"][0]["checked_at"] = "2020-01-01"
    brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")

    report = rvm.build(root)
    codes = {row["code"] for row in report["findings"]}

    assert {"ai_label_receipt_invalid", "commercial_disclosure_receipt_invalid"} <= codes
    assert report["summary"]["release_ready"] is False


def test_commercial_relationship_must_match_brief_machine_truth(tmp_path):
    root, _ = _project(tmp_path)
    brief_path = root / "需求" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["commercial_disclosure_receipts"][0]["relationship_type"] = "creator_paid_partnership"
    brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")

    report = rvm.build(root)

    assert any(row["code"] == "commercial_relationship_mismatch" for row in report["findings"])
    assert report["summary"]["release_ready"] is False


def test_formal_paid_commercial_disclosure_cannot_be_not_applicable(tmp_path):
    root, _ = _project(tmp_path)
    brief_path = root / "需求" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    receipt = brief["commercial_disclosure_receipts"][0]
    receipt.update({"status": "not_applicable", "reason": "brand-owned media"})
    brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")

    report = rvm.build(root)

    assert any(row["code"] == "commercial_disclosure_na_for_formal_paid" for row in report["findings"])
    assert report["summary"]["release_ready"] is False


def test_creator_partnership_requires_authorization_and_spark_mode(tmp_path):
    root, _ = _project(tmp_path)
    brief_path = root / "需求" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["commercial_content"] = {
        "relationship_type": "creator_paid_partnership", "creator_involved": True,
        "account_owner": "creator@example",
    }
    brief["commercial_disclosure_receipts"][0]["relationship_type"] = "creator_paid_partnership"
    brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")

    report = rvm.build(root)
    codes = {row["code"] for row in report["findings"]}

    assert "commercial_spark_mode_missing" in codes
    assert "commercial_creator_authorization_pending" in codes
    assert report["summary"]["release_ready"] is False


def test_creator_relationship_cannot_bypass_authorization_with_false_flag(tmp_path):
    root, _ = _project(tmp_path)
    brief_path = root / "需求" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["commercial_content"] = {
        "relationship_type": "creator_paid_partnership", "creator_involved": False,
        "account_owner": "creator@example",
    }
    brief["commercial_disclosure_receipts"][0].update({
        "relationship_type": "creator_paid_partnership", "spark_mode": "spark",
    })
    brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")

    report = rvm.build(root)
    codes = {row["code"] for row in report["findings"]}

    assert "commercial_creator_relationship_declaration_mismatch" in codes
    assert "commercial_creator_authorization_pending" in codes
    assert "commercial_spark_authorization_id_missing" in codes
    assert report["summary"]["release_ready"] is False


def test_creator_spark_receipt_passes_only_with_bound_authorization_evidence(tmp_path):
    root, _ = _project(tmp_path)
    authorization = root / "合规" / "creator-authorization.png"
    authorization.write_bytes(b"spark authorization receipt")
    brief_path = root / "需求" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["commercial_content"] = {
        "relationship_type": "creator_paid_partnership", "creator_involved": True,
        "account_owner": "creator@example",
    }
    receipt = brief["commercial_disclosure_receipts"][0]
    receipt.update({
        "relationship_type": "creator_paid_partnership", "spark_mode": "spark",
        "creator_authorization": {
            "status": "approved", "authorization_id": "spark-auth-001",
            "checked_at": date.today().isoformat(), "approved_by": "创作者与品牌双方",
            "evidence_file": "合规/creator-authorization.png",
        },
    })
    brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    _refresh_release_chain(root)

    report = rvm.build(root)

    assert report["summary"]["release_ready"] is True, report["findings"]
    actual = report["variants"][0]["commercial_disclosure_receipts"][0]["creator_authorization_actual"]
    assert actual["valid"] is True
    assert actual["authorization_id_actual"] == "spark-auth-001"
