"""Golden-project integration: every required ad stage earns a hash receipt."""
import json
import os
import sys
import time
from pathlib import Path

import contract
import compliance_manifest
import dependency_graph
import locale_matrix
import progress_set
import release_variant_manifest

_REVIEW = Path(__file__).resolve().parents[2] / "ad-review" / "scripts"
sys.path.insert(0, str(_REVIEW))
import human_signoff  # noqa: E402

_COMPOSE = Path(__file__).resolve().parents[2] / "ad-compose"
sys.path.insert(0, str(_COMPOSE))
import provenance_qc  # noqa: E402


def _write(root: Path, rel: str, value):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, (dict, list)):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    elif isinstance(value, str):
        path.write_text(value, encoding="utf-8")
    else:
        path.write_bytes(value)
    return path


def _order(paths):
    """Give freshness checks deterministic, pipeline-ordered mtimes."""
    base = time.time_ns() - 10_000_000_000
    for pos, path in enumerate(paths):
        stamp = base + pos * 10_000_000
        os.utime(path, ns=(stamp, stamp))


def _golden(tmp_path: Path):
    root = tmp_path / "golden-ad"
    root.mkdir()
    ordered = []
    ordered.append(_write(root, "_设置.md", """# 设置
- 生图模型: GPT Image 2
- 生图渠道: Codex CLI
- 配音后端: manual
- 字幕语言: 中文
"""))
    ordered.append(_write(root, "需求/brief.json", {
        "schema_version": 2, "brand": "Golden", "product": "Golden Box", "usp": ["整理灵感"],
        "audience": "创作者", "campaign_objective": "转化行动", "key_message": "整理灵感",
        "measurement": {"primary_kpi": "CVR", "conversion_event": "完成注册"},
        "platforms": ["TikTok"], "placements": ["TikTok:auction_in_feed"],
        "platform_safe_zone_evidence": {"TikTok:auction_in_feed": "合规/tiktok-safe.png"},
        "release_regions": ["中国大陆"],
        "claims": [{"id": "claim_01", "claim": "整理灵感", "evidence_type": "brand_fact",
                    "evidence": "产品功能清单", "evidence_file": "证据/claim.md", "method": "逐功能核验",
                    "date": "2026-07-01", "territory": "中国大陆", "approved_by": "法务甲"}],
        "rights": {key: {"status": "not_used", "territory": "中国大陆", "media_scope": "all",
                         "approved_by": "制片甲"} for key in ("talent", "music", "fonts", "assets")},
        "mandatories": {"legal_lines": ["广告"], "cta": "立即体验"},
        "default_locale": "zh-CN",
    }))
    ordered.append(_write(root, "证据/claim.md", "产品功能清单"))
    ordered.extend([
        _write(root, "证据/typography.md", "设计甲已在最终版式逐项复核"),
        _write(root, "合规/tiktok-safe.png", b"placement-safe-zone"),
        _write(root, "合规/ai-label.png", b"platform-ai-label-receipt"),
        _write(root, "合规/provenance-probe.json", "c2patool/provider metadata probe output"),
        _write(root, "合规/platform-declaration.png", b"platform-declaration-receipt"),
        _write(root, "创意/concept.md", "# Big Idea\n整理灵感\n## 一句话主张\n整理灵感\n## 广告目标\n转化\n## 创意假设\n减少摩擦\n## 强制项\nlogo、法律声明"),
        _write(root, "创意/创意脚本.md", "Big Idea / key message / campaign objective / hypothesis / mandatories"),
        _write(root, "脚本/广告脚本.md", "S1：展示产品。字幕：整理灵感。"),
        _write(root, "脚本/voiceover.txt", "整理灵感，立即体验。广告。"),
        _write(root, "脚本/时间轴.json", [{"start": 0, "end": 2, "shot_id": "S1"}]),
        _write(root, "配音/line_01.wav", b"line-audio"),
        _write(root, "配音/vo.wav", b"full-voice"),
        _write(root, "配音/时长清单.json", {"has_placeholder": False, "lines": [
            {"idx": 1, "seconds": 2.0, "voice_key": "VO_GOLDEN", "line_wav": "line_01.wav"}
        ]}),
        _write(root, "配音/voice_qc.json", {"qc_environment": {"precision_level": "full"},
                                             "summary": {"block": 0, "warn": 0}}),
        _write(root, "脚本/storyboard.json", {"shots": [{
            "shot_id": "S1", "duration": 2, "frame": "Golden Box 整理灵感，立即体验",
            "assets": {"PROD_GOLDEN_BOX": True, "BRAND_GOLDEN": True},
            "claim_ids": ["claim_01"],
            "disclosures": [{"claim_id": "claim_01", "text": "产品功能清单"}],
            "legal_lines": ["广告"],
        }]}),
        _write(root, "脚本/字幕_zh.srt", "1\n00:00:00,000 --> 00:00:02,000\n整理灵感，立即体验。广告。\n"),
        _write(root, "脚本/镜头时长.json", {"schema_version": 2, "standards": {"cited_content": True},
                                             "findings": [], "summary": {"block": 0, "warn": 0}}),
        _write(root, "脚本/广告法机检报告.json", {"summary": {"block": 0, "warn": 0}}),
        _write(root, "出图/分镜/prompt/镜头01.md", "Golden Box product lock"),
        _write(root, "出图/分镜/图片/镜头01.png", b"final-image"),
        _write(root, "出图/分镜/image_jobs_manifest.json", {"jobs": [{
            "job_id": "S1", "status": "done", "model": "GPT Image 2", "channel": "Codex CLI",
            "output": "出图/分镜/图片/镜头01.png",
        }]}),
        _write(root, "出图/分镜/product_qc.json", {"qc_environment": {"precision_level": "full"},
                                                    "summary": {"block": 0, "warn": 0}}),
        _write(root, "出视频/分镜/prompt/镜头01.md", "Animate locked Golden Box"),
        _write(root, "出视频/分镜/视频/镜头01.mp4", b"final-clip"),
        _write(root, "出视频/分镜/video_jobs_manifest.json", {"jobs": [{
            "job_id": "S1", "status": "done", "output": "出视频/分镜/视频/镜头01.mp4",
        }]}),
        _write(root, "出视频/分镜/contract_inheritance.json", {"summary": {"block": 0, "warn": 0}}),
        _write(root, "出视频/分镜/video_qc.json", {"qc_environment": {"precision_level": "full"},
                                                    "summary": {"block": 0, "warn": 0}}),
        _write(root, "合成/成片_主片.mp4", b"final-master"),
        _write(root, "合成/delivery_plan.json", {"deliverables": [{
            "deliverable_id": "master", "kind": "master", "duration": "2s", "aspect": "9:16",
            "status": "rendered", "exists": True, "expected_path": "合成/成片_主片.mp4",
            "target_placements": ["TikTok:auction_in_feed"],
        }]}),
        _write(root, "合成/delivery_qc.json", {"items": [{"deliverable_id": "master", "passed": True}],
                                               "summary": {"block": 0, "warn": 0}}),
        _write(root, "合成/color_preflight.json", {"summary": {"block": 0, "warn": 0}}),
        _write(root, "合成/accessibility_qc.json", {"summary": {"block": 0, "warn": 0}}),
        _write(root, "合规/rendered_text_plan.json", {"checks": [{"id": "master:subtitle:1"}]}),
        _write(root, "合成/rendered_text_qc.json", {"summary": {"block": 0, "warn": 0}}),
        _write(root, "合成/asr_consistency.json", {"summary": {"block": 0, "warn": 0}}),
        _write(root, "合规/ai_usage.json", {"visual_mode": "AI-generated", "video_mode": "AI-generated",
                                            "image_model": "GPT Image 2", "image_channel": "Codex CLI"}),
        _write(root, "合规/locale_matrix.json", {
            "schema_version": 1, "kind": "ad_locale_matrix", "default_locale": "zh-CN",
            "locales": {"zh-CN": {"language": "zh-CN", "jurisdictions": ["中国大陆"],
                "currency": "CNY", "unit_system": "metric", "cta": "立即体验", "legal_lines": ["广告"],
                "voiceover_path": "脚本/voiceover.txt", "subtitle_path": "脚本/字幕_zh.srt",
                "translation_review": {"status": "source_language"},
                "typography_review": {"status": "approved", "approved_by": "设计甲",
                                      "evidence": "证据/typography.md"}}},
            "deliverable_locales": {"master": ["zh-CN"]}}),
        _write(root, "合规/locale_matrix_validation.json", {"summary": {"block": 0, "warn": 0}}),
        _write(root, "合规/provenance_qc.json", {"summary": {"block": 0, "warn": 0}}),
        _write(root, "合规/release_variant_manifest.json", {"summary": {"block": 0, "warn": 0,
                                                                          "release_ready": True}}),
        _write(root, "合规/compliance_manifest.json", {"summary": {"block": 0, "warn": 0,
                                                                     "release_ready": True}}),
        _write(root, "生产数据/final_media_contact_sheets/PROD_GOLDEN_BOX.jpg", b"contact-sheet"),
        _write(root, "生产数据/final_media_consistency.json", {"assets": {
            "PROD_GOLDEN_BOX": {"contact_sheet": {
                "path": "生产数据/final_media_contact_sheets/PROD_GOLDEN_BOX.jpg"}}
        }, "summary": {"block": 0, "warn": 0}}),
        _write(root, "生产数据/consistency_findings.json", {"summary": {"block": 0, "warn": 0}}),
        _write(root, "合规/ad_review_m0.json", {"summary": {"block": 0, "warn": 0}}),
        _write(root, "证据/named-final-review.md", "审片甲逐项核对全部最终媒体"),
    ])
    master_sha = dependency_graph.file_sha(root / "合成" / "成片_主片.mp4")
    brief_path = root / "需求" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["ai_label_receipts"] = [{
        "deliverable_id": "master", "platform": "TikTok", "placement": "TikTok:auction_in_feed",
        "asset_sha256": master_sha, "status": "completed", "label_mode": "platform_managed",
        "checked_at": "2026-07-11", "approved_by": "发布甲", "evidence_file": "合规/ai-label.png"}]
    brief["provenance_receipts"] = [{
        "deliverable_id": "master", "status": "verified", "asset_sha256": master_sha,
        "tool": "c2patool 0.22 + provider metadata API", "checked_at": "2026-07-11",
        "approved_by": "发布甲", "evidence_file": "合规/provenance-probe.json",
        "metadata_assertions": {"ai_generated": True, "provider_or_platform": "OpenAI",
                                "content_id": "golden-asset-001"}}]
    brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    locale_report = locale_matrix.validate(root)
    provenance_report = provenance_qc.build(root)
    _write(root, "合规/locale_matrix_validation.json", locale_report)
    _write(root, "合规/provenance_qc.json", provenance_report)
    variant_report = release_variant_manifest.build(root)
    _write(root, "合规/release_variant_manifest.json", variant_report)
    compliance_report = compliance_manifest.build(
        root, "completed", "合规/platform-declaration.png", "platform_managed", "preserve", "platform_managed")
    _write(root, "合规/compliance_manifest.json", compliance_report)
    assert locale_report["summary"]["block"] == 0
    assert provenance_report["summary"]["block"] == 0
    assert variant_report["summary"]["block"] == 0, variant_report["findings"]
    assert compliance_report["summary"]["release_ready"] is True, compliance_report["findings"]
    _order(ordered)
    evidence = {key: "证据/named-final-review.md" for key in human_signoff.CHECKS}
    signoff = human_signoff.build(root, "审片甲", human_signoff.CHECKS, evidence=evidence)
    assert signoff["summary"]["approved"] is True
    _write(root, "合规/human_signoff.json", signoff)
    _write(root, "_进度.md", contract.progress_markdown("Golden Ad"))
    return root


def test_golden_project_runs_every_required_stage_and_records_current_hashes(tmp_path):
    root = _golden(tmp_path)
    required = [row["key"] for row in contract.stage_table() if row["key"] != "feedback"]
    progress = (root / "_进度.md").read_text(encoding="utf-8")
    for stage in required:
        report_path = progress_set.require_stage_acceptance(root, stage)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["summary"]["accepted"] is True, (stage, report["findings"])
        progress = progress_set.set_stage_text(progress, stage, "✅", note=f"golden accepted {stage}")
    (root / "_进度.md").write_text(progress, encoding="utf-8")

    graph = dependency_graph.analyze(root)
    for stage in required:
        status = graph["stages"][stage]
        assert status["current"] > 0
        assert status["stale"] == status["unaccepted"] == status["missing"] == 0
    assert all(progress_set.get_stage_status(progress, stage) == "✅" for stage in required)
