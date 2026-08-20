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
        "campaign_mode": "formal", "brand": "山岚", "product": "咖啡", "usp": ["48小时内烘焙"], "audience": "白领",
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
    assert done["release_variant_manifest_sha256"]
    assert done["release_chain"]["summary"]["block"] > 0
    assert any(f["code"] == "release_variant_manifest_not_ready" for f in done["findings"])
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


def test_self_rendered_explicit_label_requires_plan_entry_at_video_start(tmp_path):
    root = _project(tmp_path)

    # 声明自行烧录但 rendered_text_plan 无标识条目 → 责任空转 block
    report = cm.build(root, "completed", "合规/平台回执.png", "self_rendered", "preserve", "platform_managed")
    assert any(f["code"] == "explicit_label_plan_missing" and f["severity"] == "block"
               for f in report["findings"])

    # 有标识条目但不在起始段 → warn（《标识办法》要求视频起始画面显著提示）
    (root / "合规" / "rendered_text_plan.json").write_text(json.dumps({
        "schema_version": 1, "kind": "ad_rendered_text_plan",
        "checks": [{"id": "master:ai_label", "deliverable_id": "master",
                    "text": "内容由 AI 生成", "start": 8.0, "end": 10.0}],
    }, ensure_ascii=False), encoding="utf-8")
    report2 = cm.build(root, "completed", "合规/平台回执.png", "self_rendered", "preserve", "platform_managed")
    assert not any(f["code"] == "explicit_label_plan_missing" for f in report2["findings"])
    assert any(f["code"] == "explicit_label_not_at_start" and f["severity"] == "warn"
               for f in report2["findings"])

    # 标识条目落在片头 → 链路闭合，两个 code 都不再出现
    (root / "合规" / "rendered_text_plan.json").write_text(json.dumps({
        "schema_version": 1, "kind": "ad_rendered_text_plan",
        "checks": [{"id": "master:ai_label", "deliverable_id": "master",
                    "text": "内容由 AI 生成", "start": 0.0, "end": 3.0}],
    }, ensure_ascii=False), encoding="utf-8")
    report3 = cm.build(root, "completed", "合规/平台回执.png", "self_rendered", "preserve", "platform_managed")
    assert not any(f["code"].startswith("explicit_label_") for f in report3["findings"])


def test_platform_managed_label_skips_burnin_chain_and_unknown_status_warns(tmp_path):
    root = _project(tmp_path)

    report = cm.build(root, "completed", "合规/平台回执.png", "platform_managed", "preserve", "platform_managed")
    assert not any(f["code"].startswith("explicit_label_") for f in report["findings"])

    report2 = cm.build(root, "completed", "合规/平台回执.png", "发布方自己弄", "preserve", "platform_managed")
    assert any(f["code"] == "explicit_label_status_unknown" and f["severity"] == "warn"
               for f in report2["findings"])
