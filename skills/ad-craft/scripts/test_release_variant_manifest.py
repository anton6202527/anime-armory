import hashlib
import json
from pathlib import Path

import release_variant_manifest as rvm


def _sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    }.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    master = root / "合成" / "成片_主片.mp4"
    master.parent.mkdir(parents=True)
    master.write_bytes(b"current-master")
    digest = _sha(master)
    brief = {
        "brand": "山岚", "product": "咖啡", "platforms": ["TikTok"],
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
                               "checked_at": "2026-07-11", "approved_by": "发布甲",
                               "evidence_file": "合规/ai-label.png"}] if ai else [],
    }
    (root / "需求").mkdir()
    (root / "需求" / "brief.json").write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    (root / "脚本" / "storyboard.json").write_text(json.dumps({"shots": [{
        "shot_id": "S1", "duration": 2, "assets": {"PROD_COFFEE": True, "BRAND_SHANLAN": True},
        "claim_ids": ["claim_01"], "disclosures": [{"claim_id": "claim_01", "text": "品牌档案"}],
    }]}), encoding="utf-8")
    (root / "合成" / "delivery_plan.json").write_text(json.dumps({"deliverables": [{
        "deliverable_id": "master", "kind": "master", "duration": "2s", "aspect": "9:16",
        "expected_path": "合成/成片_主片.mp4", "status": "rendered", "exists": True,
        "target_placements": ["TikTok:auction_in_feed"],
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


def test_ai_label_receipt_is_invalidated_by_media_change(tmp_path):
    root, _ = _project(tmp_path)
    (root / "合成" / "成片_主片.mp4").write_bytes(b"changed-master")
    report = rvm.build(root)
    assert any(row["code"] == "ai_label_receipt_invalid" for row in report["findings"])

