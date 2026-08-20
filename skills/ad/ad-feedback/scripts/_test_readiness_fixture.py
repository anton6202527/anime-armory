"""Shared formal campaign-readiness fixture for ad-feedback tests."""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path


def _evidence(root: Path, name: str) -> str:
    path = root / "证据" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(("evidence:" + name).encode("utf-8"))
    return path.relative_to(root).as_posix()


def write_formal_readiness(root: Path, primary_kpi: str = "CTR") -> dict:
    today = date.today().isoformat()
    brief = {
        "schema_version": 2, "kind": "ad_brief", "campaign_mode": "formal",
        "brand": "星盒", "product": "星盒手账 App", "offer": "首月 9.9 元",
        "price": "9.9 元", "claims": [{"id": "claim_01", "claim": "支持语音整理"}],
        "mandatories": {"endcard_cta": "立即体验"},
        "landing_page": "https://example.test/buy", "industry_category": "productivity_software",
        "platforms": ["TikTok"], "placements": ["TikTok:auction_in_feed"],
        "release_regions": ["中国大陆"],
        "landing_page_readiness": {
            "status": "verified", "checked_at": today,
            "final_url": "https://example.test/buy", "redirect_status": "no_redirect",
            "evidence_file": _evidence(root, "landing-status.png"),
            "redirect_evidence_file": _evidence(root, "redirect-chain.txt"),
        },
        "message_reconciliation": {
            "status": "matched", "landing_page_url": "https://example.test/buy",
            "checked_items": ["offer", "claims", "cta", "price"], "not_applicable_items": [],
            "evidence_file": _evidence(root, "landing-reconciliation.pdf"),
            "approved_by": "电商负责人甲", "reviewed_at": today,
        },
        "eligibility_reviews": [{
            "platform": "TikTok", "jurisdiction": "中国大陆",
            "industry_category": "productivity_software", "status": "manual_approved",
            "evidence_file": _evidence(root, "eligibility-review.pdf"),
            "reviewed_by": "法务甲", "reviewed_at": today,
        }],
        "measurement": {
            "primary_kpi": primary_kpi, "conversion_event": "purchase",
            "attribution_window": "7d_click_1d_view",
            "tracking_integrations": [{
                "type": "pixel", "platform": "TikTok", "status": "verified",
                "events": ["purchase"], "diagnostics_status": "healthy",
                "diagnostics_checked_at": today,
                "evidence_file": _evidence(root, "pixel-event.png"),
                "diagnostics_evidence_file": _evidence(root, "pixel-diagnostics.png"),
            }],
            "utm": {
                "status": "verified", "source": "tiktok", "medium": "paid_social",
                "campaign": "starbox_launch",
                "example_url": "https://example.test/buy?utm_source=tiktok&utm_medium=paid_social&utm_campaign=starbox_launch",
                "evidence_file": _evidence(root, "utm-test.txt"),
            },
            "deep_link": {
                "status": "not_applicable", "approved_by": "增长负责人甲",
                "evidence_file": _evidence(root, "deep-link-na.md"),
            },
            "consent_privacy": {
                "status": "approved", "consent_status": "verified", "privacy_status": "published",
                "privacy_notice_url": "https://example.test/privacy",
                "evidence_file": _evidence(root, "privacy-review.pdf"),
                "approved_by": "隐私负责人甲", "reviewed_at": today,
            },
        },
    }
    brief_path = root / "需求" / "brief.json"
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")

    craft_scripts = Path(__file__).resolve().parents[2] / "ad-craft" / "scripts"
    if str(craft_scripts) not in sys.path:
        sys.path.insert(0, str(craft_scripts))
    import campaign_readiness
    report = campaign_readiness.evaluate(root, "auto")
    assert report["summary"]["release_ready"] is True
    out = root / "生产数据" / "campaign_readiness.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    return report
