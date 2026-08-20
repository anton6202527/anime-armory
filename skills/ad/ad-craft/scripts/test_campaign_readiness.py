import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import campaign_readiness as cr  # noqa: E402


TODAY = date.today().isoformat()


def _evidence(root: Path, name: str) -> str:
    path = root / "证据" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(("evidence:" + name).encode("utf-8"))
    return path.relative_to(root).as_posix()


def _complete_brief(root: Path) -> dict:
    landing_status = _evidence(root, "landing-status.png")
    redirect = _evidence(root, "redirect-chain.txt")
    reconciliation = _evidence(root, "landing-reconciliation.pdf")
    eligibility = _evidence(root, "eligibility-review.pdf")
    tracking = _evidence(root, "pixel-event.png")
    diagnostics = _evidence(root, "pixel-diagnostics.png")
    utm = _evidence(root, "utm-test.txt")
    deep_link_na = _evidence(root, "deep-link-na.md")
    privacy = _evidence(root, "privacy-review.pdf")
    return {
        "schema_version": 2,
        "kind": "ad_brief",
        "campaign_mode": "formal",
        "brand": "星盒",
        "product": "星盒手账 App",
        "offer": "首月 9.9 元",
        "price": "9.9 元",
        "claims": [{"id": "claim_01", "claim": "支持语音整理"}],
        "mandatories": {"endcard_cta": "立即体验"},
        "landing_page": "https://example.test/buy",
        "industry_category": "productivity_software",
        "platforms": ["TikTok"],
        "placements": ["TikTok:auction_in_feed"],
        "release_regions": ["中国大陆"],
        "landing_page_readiness": {
            "status": "verified", "checked_at": TODAY,
            "final_url": "https://example.test/buy", "redirect_status": "no_redirect",
            "evidence_file": landing_status, "redirect_evidence_file": redirect,
        },
        "message_reconciliation": {
            "status": "matched", "landing_page_url": "https://example.test/buy",
            "checked_items": ["offer", "claims", "cta", "price"],
            "not_applicable_items": [], "evidence_file": reconciliation,
            "approved_by": "电商负责人甲", "reviewed_at": TODAY,
        },
        "eligibility_reviews": [{
            "platform": "TikTok", "jurisdiction": "中国大陆",
            "industry_category": "productivity_software", "status": "manual_approved",
            "evidence_file": eligibility, "reviewed_by": "法务甲", "reviewed_at": TODAY,
        }],
        "measurement": {
            "primary_kpi": "CVR", "conversion_event": "purchase",
            "attribution_window": "7d_click_1d_view",
            "tracking_integrations": [{
                "type": "pixel", "platform": "TikTok", "status": "verified",
                "events": ["purchase"], "diagnostics_status": "healthy",
                "diagnostics_checked_at": TODAY,
                "evidence_file": tracking, "diagnostics_evidence_file": diagnostics,
            }],
            "utm": {
                "status": "verified", "source": "tiktok", "medium": "paid_social",
                "campaign": "starbox_launch",
                "example_url": "https://example.test/buy?utm_source=tiktok&utm_medium=paid_social&utm_campaign=starbox_launch",
                "evidence_file": utm,
            },
            "deep_link": {
                "status": "not_applicable", "approved_by": "增长负责人甲",
                "evidence_file": deep_link_na,
            },
            "consent_privacy": {
                "status": "approved", "consent_status": "verified", "privacy_status": "published",
                "privacy_notice_url": "https://example.test/privacy", "evidence_file": privacy,
                "approved_by": "隐私负责人甲", "reviewed_at": TODAY,
            },
        },
    }


def _project(tmp_path: Path, brief: dict) -> Path:
    root = tmp_path / "广告项目"
    (root / "需求").mkdir(parents=True)
    (root / "需求" / "brief.json").write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    return root


def test_complete_formal_campaign_is_release_ready(tmp_path):
    root = tmp_path / "广告项目"
    brief = _complete_brief(root)
    root = _project(tmp_path, brief)

    report = cr.evaluate(root)

    assert report["mode"] == "formal"
    assert report["summary"]["block"] == 0
    assert report["summary"]["release_ready"] is True
    assert report["checks"]["landing_page"]["network_checked_by_this_script"] is False
    assert report["checks"]["measurement"]["tracking_integrations"][0]["valid"] is True
    assert {row["id"] for row in report["official_standards"]} == {
        "google_ads_destination_requirements",
        "tiktok_landing_page_review",
        "google_enhanced_conversions_diagnostics",
    }


def test_sample_gaps_are_warnings_and_never_release_ready(tmp_path):
    root = _project(tmp_path, {"campaign_mode": "sample"})

    report = cr.evaluate(root)

    assert report["summary"]["block"] == 0
    assert report["summary"]["warn"] > 0
    assert report["summary"]["sample_ready_with_warnings"] is True
    assert report["summary"]["release_ready"] is False
    assert all(row["severity"] == "warn" for row in report["findings"])


def test_formal_campaign_fails_closed_across_readiness_scopes(tmp_path):
    root = _project(tmp_path, {"campaign_mode": "formal"})

    report = cr.evaluate(root)
    codes = {row["code"] for row in report["findings"] if row["severity"] == "block"}

    assert report["summary"]["release_ready"] is False
    assert {
        "landing_page_url_missing", "message_reconciliation_unapproved",
        "industry_category_missing", "conversion_event_missing",
        "attribution_window_missing", "tracking_integration_missing",
        "utm_status_unverified", "deep_link_status_unverified",
        "consent_privacy_status_unapproved",
    } <= codes


def test_unknown_mode_is_a_hard_block_instead_of_assuming_sample(tmp_path):
    root = _project(tmp_path, {})

    report = cr.evaluate(root)

    assert report["mode"] == "unknown"
    assert any(row["code"] == "campaign_mode_missing" and row["severity"] == "block"
               for row in report["findings"])


def test_external_or_missing_evidence_is_not_treated_as_verified(tmp_path):
    root = tmp_path / "广告项目"
    brief = _complete_brief(root)
    brief["landing_page_readiness"]["evidence_file"] = "https://platform.example/report/123"
    brief["landing_page_readiness"]["redirect_evidence_file"] = "证据/missing.txt"
    root = _project(tmp_path, brief)

    report = cr.evaluate(root)
    landing = report["checks"]["landing_page"]

    assert landing["status_evidence"]["reason"] == "external_reference_not_locally_verified"
    assert landing["redirect_evidence"]["reason"] == "file_missing"
    assert {"landing_page_status_evidence_missing", "landing_page_redirect_evidence_missing"} <= {
        row["code"] for row in report["findings"]
    }


def test_malformed_url_is_reported_instead_of_crashing(tmp_path):
    root = tmp_path / "广告项目"
    brief = _complete_brief(root)
    brief["landing_page"] = "https://example.test:not-a-port/buy"
    root = _project(tmp_path, brief)

    report = cr.evaluate(root)

    assert any(row["code"] == "landing_page_url_invalid" for row in report["findings"])


def test_tracking_event_must_match_conversion_event_and_have_diagnostics(tmp_path):
    root = tmp_path / "广告项目"
    brief = _complete_brief(root)
    integration = brief["measurement"]["tracking_integrations"][0]
    integration["events"] = ["signup"]
    integration["diagnostics_status"] = "pending"
    root = _project(tmp_path, brief)

    report = cr.evaluate(root)
    codes = {row["code"] for row in report["findings"]}

    assert "tracking_event_mismatch" in codes
    assert "tracking_diagnostics_unverified" in codes
    assert "tracking_platform_uncovered" in codes


def test_future_dates_are_not_accepted_as_current_evidence(tmp_path):
    root = tmp_path / "广告项目"
    brief = _complete_brief(root)
    brief["landing_page_readiness"]["checked_at"] = (date.today() + timedelta(days=1)).isoformat()
    brief["eligibility_reviews"][0]["reviewed_at"] = (date.today() + timedelta(days=1)).isoformat()
    root = _project(tmp_path, brief)

    report = cr.evaluate(root)
    codes = {row["code"] for row in report["findings"]}

    assert "landing_page_checked_at_invalid" in codes
    assert "eligibility_review_missing" in codes
    assert report["summary"]["release_ready"] is False


def test_stale_operational_evidence_fails_closed(tmp_path):
    root = tmp_path / "广告项目"
    brief = _complete_brief(root)
    brief["landing_page_readiness"]["checked_at"] = (
        date.today() - timedelta(days=cr.FRESHNESS_DAYS["landing_page"] + 1)).isoformat()
    brief["message_reconciliation"]["reviewed_at"] = (
        date.today() - timedelta(days=cr.FRESHNESS_DAYS["message_reconciliation"] + 1)).isoformat()
    brief["eligibility_reviews"][0]["reviewed_at"] = (
        date.today() - timedelta(days=cr.FRESHNESS_DAYS["eligibility_review"] + 1)).isoformat()
    brief["measurement"]["tracking_integrations"][0]["diagnostics_checked_at"] = (
        date.today() - timedelta(days=cr.FRESHNESS_DAYS["tracking_diagnostics"] + 1)).isoformat()
    brief["measurement"]["consent_privacy"]["reviewed_at"] = (
        date.today() - timedelta(days=cr.FRESHNESS_DAYS["consent_privacy"] + 1)).isoformat()
    root = _project(tmp_path, brief)

    report = cr.evaluate(root)
    codes = {row["code"] for row in report["findings"]}

    assert {
        "landing_page_evidence_stale", "message_reconciliation_stale",
        "eligibility_review_stale", "tracking_diagnostics_stale",
        "consent_privacy_review_stale", "tracking_platform_uncovered",
    } <= codes
    assert report["summary"]["release_ready"] is False


def test_wildcard_review_and_tracking_can_cover_explicit_target_matrix(tmp_path):
    root = tmp_path / "广告项目"
    brief = _complete_brief(root)
    brief["platforms"] = ["TikTok", "YouTube"]
    brief["release_regions"] = ["中国大陆", "新加坡"]
    brief["eligibility_reviews"][0].update({
        "platform": "all", "jurisdiction": "all", "industry_category": "all",
    })
    brief["measurement"]["tracking_integrations"][0]["platform"] = "all"
    root = _project(tmp_path, brief)

    report = cr.evaluate(root)

    assert len(report["checks"]["eligibility"]["coverage"]) == 4
    assert all(row["covered"] for row in report["checks"]["eligibility"]["coverage"])
    assert not any(row["code"] in {"eligibility_review_missing", "tracking_platform_uncovered"}
                   for row in report["findings"])


def test_write_report_outputs_machine_truth_and_human_view(tmp_path):
    root = tmp_path / "广告项目"
    brief = _complete_brief(root)
    root = _project(tmp_path, brief)

    report = cr.write_report(root)
    json_path = Path(report["_json_path"])
    md_path = Path(report["_md_path"])

    assert json_path.is_file() and md_path.is_file()
    disk = json.loads(json_path.read_text(encoding="utf-8"))
    assert disk["kind"] == cr.KIND
    assert disk["policy"]["network_actions"] == "none"
    human_view = md_path.read_text(encoding="utf-8")
    assert "本脚本未访问落地页" in human_view
    assert "Destination requirements" in human_view
    assert "ad-review-checklist-landing-page" in human_view
