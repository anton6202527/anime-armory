"""Golden-project integration: every required ad stage earns a hash receipt."""
import hashlib
import importlib.util
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

import contract
import compliance_manifest
import dependency_graph
import locale_matrix
import progress_set
import release_variant_manifest
import campaign_readiness
import placement_adaptation
import render_profile
import stage_acceptance

_RELEASE_VERDICT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "release_verdict.py"
_RELEASE_VERDICT_SPEC = importlib.util.spec_from_file_location(
    "ad_release_verdict_test", _RELEASE_VERDICT_PATH)
assert _RELEASE_VERDICT_SPEC is not None and _RELEASE_VERDICT_SPEC.loader is not None
ad_release_verdict = importlib.util.module_from_spec(_RELEASE_VERDICT_SPEC)
_RELEASE_VERDICT_SPEC.loader.exec_module(ad_release_verdict)

_REVIEW = Path(__file__).resolve().parents[2] / "ad-review" / "scripts"
sys.path.insert(0, str(_REVIEW))
import human_signoff  # noqa: E402

_COMPOSE = Path(__file__).resolve().parents[2] / "ad-compose"
sys.path.insert(0, str(_COMPOSE))
import provenance_qc  # noqa: E402


TODAY = date.today().isoformat()


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
    video_submit_prompt = "Animate the locked Golden Box product shot"
    ordered = []
    ordered.append(_write(root, "_设置.md", """# 设置
- 生图模型: GPT Image 2
- 生图渠道: Codex CLI
- 配音后端: manual
- 字幕语言: 中文
"""))
    ordered.append(_write(root, "需求/brief.json", {
        "schema_version": 2, "campaign_mode": "formal",
        "brand": "Golden", "product": "Golden Box", "usp": ["整理灵感"],
        "audience": "创作者", "campaign_objective": "转化行动", "key_message": "整理灵感",
        "deliverables": {"duration": "2s", "aspect": "9:16"},
        "offer": "免费体验", "price": "0 元试用", "landing_page": "https://example.test/register",
        "industry_category": "productivity_software",
        "landing_page_readiness": {
            "status": "verified", "checked_at": TODAY,
            "final_url": "https://example.test/register", "redirect_status": "no_redirect",
            "evidence_file": "证据/landing-status.png", "redirect_evidence_file": "证据/redirect-chain.txt",
        },
        "message_reconciliation": {
            "status": "matched", "landing_page_url": "https://example.test/register",
            "checked_items": ["offer", "claims", "cta", "price"], "not_applicable_items": [],
            "evidence_file": "证据/landing-reconciliation.pdf", "approved_by": "增长甲",
            "reviewed_at": TODAY,
        },
        "eligibility_reviews": [{
            "platform": "TikTok", "jurisdiction": "中国大陆",
            "industry_category": "productivity_software", "status": "manual_approved",
            "evidence_file": "证据/eligibility-review.pdf", "reviewed_by": "法务甲",
            "reviewed_at": TODAY,
        }],
        "measurement": {
            "primary_kpi": "CVR", "conversion_event": "完成注册", "attribution_window": "7d_click_1d_view",
            "tracking_integrations": [{
                "type": "pixel", "platform": "TikTok", "status": "verified", "events": ["完成注册"],
                "diagnostics_status": "healthy", "evidence_file": "证据/pixel-event.png",
                "diagnostics_evidence_file": "证据/pixel-diagnostics.png", "diagnostics_checked_at": TODAY,
            }],
            "utm": {"status": "verified", "source": "tiktok", "medium": "paid_social",
                    "campaign": "golden_launch",
                    "example_url": "https://example.test/register?utm_source=tiktok&utm_medium=paid_social&utm_campaign=golden_launch",
                    "evidence_file": "证据/utm-test.txt"},
            "deep_link": {"status": "not_applicable", "approved_by": "增长甲",
                          "evidence_file": "证据/deep-link-na.md"},
            "consent_privacy": {"status": "approved", "consent_status": "verified",
                                "privacy_status": "published", "privacy_notice_url": "https://example.test/privacy",
                                "evidence_file": "证据/privacy-review.pdf", "approved_by": "隐私甲",
                                "reviewed_at": TODAY},
        },
        "platforms": ["TikTok"], "placements": ["TikTok:auction_in_feed"],
        "platform_safe_zone_evidence": {"TikTok:auction_in_feed": "合规/tiktok-safe.png"},
        "release_regions": ["中国大陆"],
        "claims": [{"id": "claim_01", "claim": "整理灵感", "evidence_type": "brand_fact",
                    "evidence": "产品功能清单", "evidence_file": "证据/claim.md", "method": "逐功能核验",
                    "date": "2026-07-01", "territory": "中国大陆", "approved_by": "法务甲"}],
        "rights": {key: {"status": "not_used", "territory": "中国大陆", "media_scope": "all",
                         "approved_by": "制片甲"} for key in ("talent", "music", "fonts", "assets")},
        "mandatories": {"legal_lines": ["广告"], "cta": "立即体验", "endcard_cta": "立即体验"},
        "default_locale": "zh-CN",
    }))
    ordered.append(_write(root, "证据/claim.md", "产品功能清单"))
    ordered.extend([
        _write(root, "证据/typography.md", "设计甲已在最终版式逐项复核"),
        _write(root, "证据/landing-status.png", b"landing available"),
        _write(root, "证据/redirect-chain.txt", "no redirect"),
        _write(root, "证据/landing-reconciliation.pdf", b"offer claim cta price matched"),
        _write(root, "证据/eligibility-review.pdf", b"eligible"),
        _write(root, "证据/pixel-event.png", b"conversion event fired"),
        _write(root, "证据/pixel-diagnostics.png", b"diagnostics healthy"),
        _write(root, "证据/utm-test.txt", "utm verified"),
        _write(root, "证据/deep-link-na.md", "web campaign; deep link not applicable"),
        _write(root, "证据/privacy-review.pdf", b"consent and privacy approved"),
        _write(root, "合规/tiktok-safe.png", b"placement-safe-zone"),
        _write(root, "合规/ai-label.png", b"platform-ai-label-receipt"),
        _write(root, "合规/commercial-disclosure.png", b"platform-commercial-disclosure-receipt"),
        _write(root, "合规/provenance-probe.json", "c2patool/provider metadata probe output"),
        _write(root, "合规/platform-declaration.png", b"platform-declaration-receipt"),
        _write(root, "创意/concept.json", {
            "schema_version": 1, "kind": "ad_concept_pack",
            "big_idea": "整理灵感", "key_message": "整理灵感",
            "creative_route": "功能演示", "objective": "转化行动",
            "hypothesis": "降低整理摩擦能推动目标受众立即体验",
            "kv_direction": "Golden Box 产品特写",
            "usps": [{"id": "USP_01", "text": "整理灵感",
                      "supports_key_message": True, "claim_id": "claim_01"}],
            "storyline": [{"section": "产品演示", "desc": "展示整理灵感",
                           "planned_seconds": 2}],
        }),
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
        _write(root, "设定库/ref.png", b"golden-reference-pixels"),
        _write(root, "出图/分镜/prompt/镜头01.md", "Golden Box product lock"),
        _write(root, "出图/分镜/图片/镜头01.png", b"final-image"),
        _write(root, "出图/分镜/image_jobs_manifest.json", {"jobs": [{
            "job_id": "S1", "status": "done", "model": "GPT Image 2", "channel": "Codex CLI",
            "output": "出图/分镜/图片/镜头01.png",
        }]}),
        _write(root, "出图/分镜/product_qc.json", {"qc_environment": {"precision_level": "full"},
                                                    "summary": {"block": 0, "warn": 0}}),
        _write(root, "出视频/分镜/prompt/镜头01.md",
               "### 后端编译提交 prompt\n"
               "**编译元数据**：kind=ad_compiled_video_prompt; version=1; backend=seedance; mode=image2video\n"
               f"```text\n{video_submit_prompt}\n```\n"),
        _write(root, "出视频/分镜/视频/镜头01.mp4", b"final-clip"),
        _write(root, "出视频/分镜/video_jobs_manifest.json", {"jobs": [{
            "job_id": "S1", "status": "done", "prompt": "出视频/分镜/prompt/镜头01.md",
            "first_frame": "出图/分镜/图片/镜头01.png",
            "output": "出视频/分镜/视频/镜头01.mp4",
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
    # B14 golden evidence: every image is accepted against exact prompt/reference/output bytes
    # plus an explicit current-pixel visual review record.
    image_output_sha = dependency_graph.file_sha(root / "出图" / "分镜" / "图片" / "镜头01.png")
    image_prompt_sha = dependency_graph.file_sha(root / "出图" / "分镜" / "prompt" / "镜头01.md")
    image_ref_sha = dependency_graph.file_sha(root / "设定库" / "ref.png")
    image_review = _write(root, "生产数据/image_job_reviews/S1.json", {
        "reviewer": "审片甲", "decision": "accepted", "output_sha256": image_output_sha,
        "notes": "并排核对产品、品牌文字、场景、光色、构图与连续性，均通过。",
        "checks": {key: "pass" for key in (
            "subject_identity", "product_brand_text", "state_scene_props",
            "style_light_color", "composition_safe_area", "continuity",
        )},
    })
    review_sha = dependency_graph.file_sha(image_review)
    image_receipt = _write(root, "生产数据/image_job_receipts/S1.json", {
        "schema_version": 1, "kind": "ad_image_job_receipt", "job_id": "S1", "status": "accepted",
        "prompt": "出图/分镜/prompt/镜头01.md", "prompt_sha256": image_prompt_sha,
        "reference_inputs": [{"path": "设定库/ref.png", "sha256": image_ref_sha,
                              "purpose": "product_identity", "owner": "PROD_GOLDEN_BOX"}],
        "output": "出图/分镜/图片/镜头01.png", "output_sha256": image_output_sha,
        "visual_review": {"reviewer": "审片甲", "decision": "accepted",
                          "review_file": "生产数据/image_job_reviews/S1.json",
                          "review_file_sha256": review_sha},
    })
    image_manifest_path = root / "出图" / "分镜" / "image_jobs_manifest.json"
    image_manifest = json.loads(image_manifest_path.read_text(encoding="utf-8"))
    image_manifest["jobs"][0].update({
        "prompt": "出图/分镜/prompt/镜头01.md",
        "expected_output": "出图/分镜/图片/镜头01.png",
        "actual_reference_inputs": ["设定库/ref.png"],
        "qc_receipt": "生产数据/image_job_receipts/S1.json",
        "accepted_output_sha256": image_output_sha,
    })
    image_manifest_path.write_text(json.dumps(image_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    ordered.extend([image_review, image_receipt, image_manifest_path])
    delivery_plan_path = root / "合成" / "delivery_plan.json"
    master_sha = dependency_graph.file_sha(root / "合成" / "成片_主片.mp4")
    brief_path = root / "需求" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["ai_label_receipts"] = [{
        "deliverable_id": "master", "platform": "TikTok", "placement": "TikTok:auction_in_feed",
        "asset_sha256": master_sha, "status": "completed", "label_mode": "platform_managed",
        "checked_at": TODAY, "approved_by": "发布甲", "evidence_file": "合规/ai-label.png"}]
    brief["commercial_content"] = {"relationship_type": "brand_owned_paid_ad", "creator_involved": False}
    brief["commercial_disclosure_receipts"] = [{
        "deliverable_id": "master", "platform": "TikTok", "placement": "TikTok:auction_in_feed",
        "asset_sha256": master_sha, "status": "completed",
        "relationship_type": "brand_owned_paid_ad", "disclosure_mode": "platform_paid_ad_label",
        "platform_record_id": "tt-golden-ad-001", "checked_at": TODAY,
        "approved_by": "发布甲", "evidence_file": "合规/commercial-disclosure.png",
    }]
    brief["provenance_receipts"] = [{
        "deliverable_id": "master", "status": "verified", "asset_sha256": master_sha,
        "tool": "c2patool 0.22 + provider metadata API", "checked_at": TODAY,
        "approved_by": "发布甲", "evidence_file": "合规/provenance-probe.json",
        "metadata_assertions": {"ai_generated": True, "provider_or_platform": "OpenAI",
                                "content_id": "golden-asset-001"}}]
    brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    profile = render_profile.write_profile(root)
    render_ref = render_profile.compact_ref(profile)
    legacy_plan = json.loads(delivery_plan_path.read_text(encoding="utf-8"))
    adaptation_report = placement_adaptation.write_report(
        root, deliverables=legacy_plan["deliverables"])
    assert adaptation_report["summary"]["block"] == 0, adaptation_report["findings"]
    adaptation_by_id = {row["deliverable_id"]: row for row in adaptation_report["items"]}
    delivery_plan = {
        "schema_version": 5, "kind": "ad_delivery_plan", "project_root": str(root.resolve()),
        "render_profile": render_ref,
        "placement_adaptation": {
            "path": "生产数据/placement_adaptation.json",
            "sha256": adaptation_report["plan_sha256"],
            "summary": adaptation_report["summary"],
        },
        "summary": {"block": 0},
        "deliverables": [{**row, "render_profile": render_ref,
                          "placement_adaptation": adaptation_by_id[row["deliverable_id"]]}
                         for row in legacy_plan["deliverables"]],
    }
    delivery_plan_path.write_text(json.dumps(delivery_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    delivery_qc_path = root / "合成" / "delivery_qc.json"
    delivery_qc = {
        "schema_version": 2, "kind": "ad_delivery_qc",
        "delivery_plan_sha256": release_variant_manifest.canonical_sha(delivery_plan),
        "media_sha256_by_deliverable": {"master": master_sha},
        "render_profile_sha256": render_ref["sha256"],
        "placement_adaptation_sha256": adaptation_report["plan_sha256"],
        "adaptation_execution_sha256_by_deliverable": {},
        "render_profile": render_ref,
        "items": [{"deliverable_id": "master", "path": "合成/成片_主片.mp4",
                   "passed": True, "findings": []}],
        "summary": {"block": 0, "warn": 0, "passed": 1}, "findings": [],
    }
    delivery_qc_path.write_text(json.dumps(delivery_qc, ensure_ascii=False, indent=2), encoding="utf-8")
    video_manifest_path = root / "出视频" / "分镜" / "video_jobs_manifest.json"
    video_manifest = json.loads(video_manifest_path.read_text(encoding="utf-8"))
    video_manifest["render_profile"] = render_ref
    video_manifest["jobs"][0].update({
        "render_profile": render_ref,
        "render_profile_sha256": render_ref["sha256"],
        "video_resolution": profile["source_generation"]["backend_request_resolution"],
        "requested_source_fps": profile["source_generation"]["fps"],
        "source_fps": profile["source_generation"]["fps"],
        "submit_prompt_sha256": hashlib.sha256(video_submit_prompt.encode("utf-8")).hexdigest(),
        "input_frame_sha256": {"first": dependency_graph.file_sha(
            root / "出图" / "分镜" / "图片" / "镜头01.png"), "end": None},
        "output_sha256": dependency_graph.file_sha(root / "出视频" / "分镜" / "视频" / "镜头01.mp4"),
    })
    video_manifest["jobs"][0]["observed_output"] = {
        "width": profile["source_generation"]["width"],
        "height": profile["source_generation"]["height"],
        "resolution": profile["source_generation"]["resolution"],
        "fps": profile["source_generation"]["fps"],
        "output_sha256": video_manifest["jobs"][0]["output_sha256"],
        "probe": "golden-fixture",
    }
    video_manifest_path.write_text(json.dumps(video_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    ordered.extend([
        root / "生产数据" / "platform_pack.json",
        root / "生产数据" / "render_profile.json",
        root / "生产数据" / "placement_adaptation.json",
        video_manifest_path,
        delivery_plan_path,
        delivery_qc_path,
    ])
    readiness_report = campaign_readiness.write_report(root)
    assert readiness_report["summary"]["release_ready"] is True, readiness_report["findings"]
    locale_report = locale_matrix.validate(root)
    provenance_report = provenance_qc.build(root)
    _write(root, "合规/locale_matrix_validation.json", locale_report)
    _write(root, "合规/provenance_qc.json", provenance_report)
    # Release manifests require a real current formal compose acceptance and
    # content-addressed receipt, so earn the upstream receipts in order first.
    _order(ordered)
    through_compose = [row["key"] for row in contract.stage_table()]
    through_compose = through_compose[:through_compose.index("compose") + 1]
    for stage in through_compose:
        report_path = progress_set.require_stage_acceptance(root, stage)
        accepted = json.loads(report_path.read_text(encoding="utf-8"))
        assert accepted["summary"]["accepted"] is True, (stage, accepted["findings"])
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
    # M0 is a downstream report and must be newer than every readiness/release
    # report and the evidence bytes they consumed.
    _write(root, "合规/ad_review_m0.json", {"summary": {"block": 0, "warn": 0}})
    evidence = {key: "证据/named-final-review.md" for key in human_signoff.CHECKS}
    signoff = human_signoff.build(root, "审片甲", human_signoff.CHECKS, evidence=evidence)
    assert signoff["summary"]["approved"] is True
    _write(root, "合规/human_signoff.json", signoff)
    _write(root, "_进度.md", contract.progress_markdown("Golden Ad"))
    return root


def _ensure_required_acceptances(root: Path):
    required = [row["key"] for row in contract.stage_table() if row["key"] != "feedback"]
    reports = {}
    for stage in required:
        report_path = root / "生产数据" / "stage_acceptance" / f"{stage}.json"
        if not report_path.is_file():
            report_path = progress_set.require_stage_acceptance(root, stage)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["summary"]["accepted"] is True, (stage, report["findings"])
        reports[stage] = report_path
    return required, reports


def test_golden_project_runs_every_required_stage_and_records_current_hashes(tmp_path):
    root = _golden(tmp_path)
    required, reports = _ensure_required_acceptances(root)
    progress = (root / "_进度.md").read_text(encoding="utf-8")
    for stage in required:
        assert reports[stage].is_file()
        progress = progress_set.set_stage_text(progress, stage, "✅", note=f"golden accepted {stage}")
    (root / "_进度.md").write_text(progress, encoding="utf-8")

    graph = dependency_graph.analyze(root)
    for stage in required:
        status = graph["stages"][stage]
        assert status["current"] > 0
        assert status["stale"] == status["unaccepted"] == status["missing"] == 0
    assert all(progress_set.get_stage_status(progress, stage) == "✅" for stage in required)


def test_single_release_verdict_invalidates_on_current_media_mutation(tmp_path):
    root = _golden(tmp_path)
    verdict = ad_release_verdict.build_verdict(root)
    assert verdict["complete"] is True, verdict["blockers"]
    accepted_digest = verdict["release_digest"]

    with (root / "合成" / "成片_主片.mp4").open("ab") as fh:
        fh.write(b"changed-current-master")
    stale = ad_release_verdict.build_verdict(root)
    assert stale["complete"] is False
    assert stale["release_digest"] != accepted_digest
    codes = {row["code"] for row in stale["blockers"]}
    assert "release_variant_media_stale" in codes
    assert "human_signoff_media_stale" in codes


def test_golden_commercial_evidence_mutation_invalidates_handoff_and_review(tmp_path):
    root = _golden(tmp_path)
    _ensure_required_acceptances(root)
    evidence = root / "合规" / "commercial-disclosure.png"
    time.sleep(0.002)
    evidence.write_bytes(b"commercial receipt changed after handoff and signoff")

    graph = dependency_graph.analyze(root)
    nodes = {row["node_id"]: row for row in graph["nodes"]}
    assert nodes["handoff"]["status"] == "stale_input"
    assert nodes["review"]["status"] == "stale_input"

    handoff_report = stage_acceptance.evaluate(root, "handoff")
    assert "release_variant_evidence_stale" in {row["code"] for row in handoff_report["findings"]}
    assert handoff_report["summary"]["accepted"] is False

    review_report = stage_acceptance.evaluate(root, "review")
    codes = {row["code"] for row in review_report["findings"]}
    assert "upstream_dependency_stale" in codes
    assert "machine_review_stale" in codes
    assert review_report["summary"]["accepted"] is False


def test_golden_video_profile_or_observed_media_drift_blocks_video_acceptance(tmp_path):
    root = _golden(tmp_path)
    initial = stage_acceptance.evaluate(root, "video", "formal")
    initial_codes = {row["code"] for row in initial["findings"]}
    assert "video_observed_fps_mismatch" not in initial_codes
    assert "video_render_profile_stale" not in initial_codes

    manifest_path = root / "出视频" / "分镜" / "video_jobs_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["jobs"][0]["observed_output"]["fps"] = 30
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    observed = stage_acceptance.evaluate(root, "video", "formal")
    assert "video_observed_fps_mismatch" in {row["code"] for row in observed["findings"]}

    (root / "_设置.md").write_text(
        "# 设置\n- 生图模型: GPT Image 2\n- 生图渠道: Codex CLI\n"
        "- 出视频规格: 预算充足\n- 视频分辨率: 1080p\n- 交付比例: 9:16\n",
        encoding="utf-8",
    )
    stale = stage_acceptance.evaluate(root, "video", "formal")
    assert "video_render_profile_stale" in {row["code"] for row in stale["findings"]}
