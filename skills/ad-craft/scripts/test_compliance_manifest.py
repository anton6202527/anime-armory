import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compliance_manifest as cm  # noqa: E402


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "ad"
    (root / "合规").mkdir(parents=True)
    (root / "需求").mkdir()
    (root / "合规" / "ai_usage.json").write_text(json.dumps({
        "visual_mode": "AI-generated", "video_mode": "AI-generated",
        "image_model": "GPT Image 2", "image_channel": "Codex CLI",
    }), encoding="utf-8")
    (root / "脚本").mkdir()
    (root / "合成").mkdir()
    (root / "证据").mkdir()
    (root / "需求" / "brief.json").write_text(json.dumps({
        "brand": "山岚", "product": "咖啡", "usp": ["48小时内烘焙"], "audience": "白领",
        "campaign_objective": "转化行动", "platforms": ["TikTok"],
        "placements": ["TikTok:auction_in_feed"],
        "platform_safe_zone_evidence": {"TikTok:auction_in_feed": "合规/tiktok-feed.png"},
        "release_regions": ["中国大陆"],
        "claims": [{
            "id": "claim_01", "claim": "48小时内烘焙", "evidence_type": "brand_fact",
            "evidence": "批次记录", "evidence_file": "证据/批次.md", "method": "逐批核验",
            "date": "2026-07-01", "territory": "中国大陆", "approved_by": "法务甲",
        }],
        "rights": {
            "talent": {"status": "not_used", "territory": "中国大陆", "media_scope": "all", "approved_by": "制片甲"},
            "music": {"status": "licensed", "evidence_file": "证据/music.pdf", "territory": "中国大陆",
                      "media_scope": "paid ad", "validity": "2026", "valid_from": "2026-01-01",
                      "valid_until": "2026-12-31", "approved_by": "制片甲"},
            "fonts": {"status": "owned", "evidence_file": "证据/font.pdf", "territory": "中国大陆",
                      "media_scope": "all", "validity": "perpetual", "approved_by": "设计甲"},
            "assets": {"status": "owned", "evidence_file": "证据/assets.md", "territory": "中国大陆",
                       "media_scope": "all", "validity": "owned", "approved_by": "制片甲"},
        },
        "mandatories": {"legal_lines": ["广告"]},
    }, ensure_ascii=False), encoding="utf-8")
    (root / "合规" / "tiktok-feed.png").write_bytes(b"current placement template")
    (root / "合规" / "平台回执.png").write_bytes(b"receipt")
    (root / "证据" / "批次.md").write_text("batch evidence", encoding="utf-8")
    for name in ("music.pdf", "font.pdf", "assets.md"):
        (root / "证据" / name).write_bytes(b"rights")
    (root / "脚本" / "广告脚本.md").write_text("script", encoding="utf-8")
    (root / "脚本" / "storyboard.json").write_text(json.dumps({"shots": [{
        "shot_id": "S1", "duration": 3, "assets": {"PROD_COFFEE": True, "BRAND_SHANLAN": True},
    }]}), encoding="utf-8")
    (root / "脚本" / "广告法机检报告.json").write_text(json.dumps({"summary": {"block": 0, "warn": 0}}), encoding="utf-8")
    (root / "合成" / "成片_主片.mp4").write_bytes(b"master")
    (root / "合成" / "delivery_plan.json").write_text(json.dumps({"deliverables": []}), encoding="utf-8")
    return root


def test_ai_release_requires_platform_declaration_evidence(tmp_path):
    root = _project(tmp_path)
    pending = cm.build(root)
    assert pending["summary"]["release_ready"] is False
    assert any(f["code"] == "platform_declaration_pending" for f in pending["findings"])

    done = cm.build(root, "completed", "合规/平台回执.png", "platform_managed", "preserve", "platform_managed")
    assert done["summary"]["release_ready"] is False
    assert not any(f["code"] == "platform_declaration_pending" for f in done["findings"])
    assert any(f["code"] == "provenance_qc_not_ready" for f in done["findings"])
    assert done["standards"][0]["effective_date"] == "2025-09-01"


def test_stripped_metadata_blocks_ai_release(tmp_path):
    root = _project(tmp_path)
    payload = cm.build(root, "completed", "合规/平台回执.png", "platform_managed", "stripped", "stripped")
    assert any(f["code"] == "metadata_stripped" for f in payload["findings"])


def test_unprovenanced_custom_platform_spec_blocks_release(tmp_path):
    root = _project(tmp_path)
    (root / "需求" / "brief.json").write_text(json.dumps({
        "platforms": ["客户私域"],
        "platform_specs": {"客户私域": {"aspect": "9:16", "safe_area": "client-grid"}},
    }, ensure_ascii=False), encoding="utf-8")
    payload = cm.build(root, "completed", "合规/平台回执.png", "platform_managed", "preserve", "platform_managed")
    assert payload["summary"]["release_ready"] is False
    assert any(f["code"] == "release_custom_platform_provenance_missing" for f in payload["findings"])


def test_overseas_release_requires_named_hash_bound_jurisdiction_review(tmp_path):
    root = _project(tmp_path)
    path = root / "需求" / "brief.json"
    brief = json.loads(path.read_text(encoding="utf-8"))
    brief["release_regions"] = ["北美"]
    for right in brief["rights"].values():
        right["territory"] = "全球"
    path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    missing = cm.build(root, "completed", "合规/平台回执.png", "platform_managed", "preserve", "platform_managed")
    assert any(f["code"] == "jurisdiction_review_missing" for f in missing["findings"])

    evidence = root / "合规" / "north-america-legal.md"
    evidence.write_text("review", encoding="utf-8")
    brief["legal_reviews"] = [{
        "region": "北美", "jurisdictions": ["US", "CA"], "status": "approved",
        "authority": "本地律师复核", "source": "FTC / Competition Bureau official rules",
        "checked_at": "2026-07-11", "approved_by": "律师甲", "evidence_file": "合规/north-america-legal.md",
        "content_sha256": cm.release_content_sha256(root),
    }]
    path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    done = cm.build(root, "completed", "合规/平台回执.png", "platform_managed", "preserve", "platform_managed")
    assert not any(f["code"].startswith("jurisdiction_review") for f in done["findings"])
