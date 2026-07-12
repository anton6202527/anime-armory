#!/usr/bin/env python3
"""Build release-facing AI/rights/platform declaration evidence for an ad."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import platform_pack
import producer_pack
import locale_matrix
import release_variant_manifest


PENDING = {"", "待补", "未记录", "未定", "tbd", "pending"}


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def pending(value) -> bool:
    return str(value or "").strip().lower() in PENDING


def evidence_exists(root: Path, value) -> bool:
    ref = str(value or "").strip()
    if not ref:
        return False
    if ref.startswith(("https://", "http://", "record:", "doi:")):
        return True
    path = Path(ref)
    if not path.is_absolute():
        path = root / path
    return path.is_file()


def release_content_sha256(root: Path) -> str:
    """One digest binding jurisdiction review to the actual release package."""
    h = hashlib.sha256()
    rels = ["脚本/广告脚本.md", "脚本/storyboard.json", "脚本/voiceover.txt",
            "脚本/字幕_zh.srt", "脚本/字幕_en.srt", "合成/成片_主片.mp4", "合成/delivery_plan.json",
            "合规/locale_matrix.json", "合规/ai_usage.json"]
    plan = load(root / "合成" / "delivery_plan.json", {}) or {}
    for item in plan.get("deliverables") or []:
        if item.get("status") != "cancelled" and item.get("expected_path"):
            rels.append(str(item["expected_path"]))
    for rel in dict.fromkeys(rels):
        path = root / rel
        h.update(rel.encode("utf-8"))
        if not path.is_file():
            h.update(b"<missing>")
            continue
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
    return h.hexdigest()


def normalize_regions(brief, settings):
    raw = brief.get("release_regions") or brief.get("release_region") or settings.get("发行地区") or []
    if isinstance(raw, str):
        raw = [raw]
    return [str(v).strip() for v in raw if str(v).strip() not in {"", "未定"}]


def legal_coverage(root: Path, brief, settings, content_sha):
    regions = normalize_regions(brief, settings)
    reviews = brief.get("legal_reviews") if isinstance(brief.get("legal_reviews"), list) else []
    findings = []
    coverage = []
    if not regions:
        findings.append({"severity": "block", "code": "release_region_missing",
                         "msg": "发布地区未落到具体辖区；泛称“海外/全球市场”不能替代法律适用范围"})
        return regions, coverage, findings
    for region in regions:
        if region == "中国大陆":
            law_path = root / "脚本" / "广告法机检报告.json"
            law = load(law_path, {}) or {}
            try:
                blocks = int(((law.get("summary") or {}).get("block")) or 0)
            except (TypeError, ValueError):
                blocks = -1
            sources = [root / "脚本" / name for name in
                       ("广告脚本.md", "voiceover.txt", "storyboard.json", "字幕_zh.srt", "字幕_en.srt")]
            newest = max((path.stat().st_mtime for path in sources if path.is_file()), default=0)
            stale = law_path.is_file() and law_path.stat().st_mtime + 1e-6 < newest
            ok = law_path.is_file() and not law.get("disabled") and blocks == 0 and not stale
            coverage.append({"region": region, "mode": "ad_law_report", "approved": ok,
                             "evidence": "脚本/广告法机检报告.json", "stale": stale})
            if not ok:
                findings.append({"severity": "block", "code": "cn_ad_law_review_missing",
                                 "msg": "中国大陆发行缺当前有效且 0 block 的广告法机检报告，或报告早于当前脚本/分镜/字幕"})
            continue
        candidates = []
        for row in reviews:
            if not isinstance(row, dict):
                continue
            covered = row.get("regions") or row.get("region") or []
            if isinstance(covered, str):
                covered = [covered]
            if region in [str(v).strip() for v in covered]:
                candidates.append(row)
        if not candidates:
            findings.append({"severity": "block", "code": "jurisdiction_review_missing",
                             "msg": f"{region} 缺逐辖区法律复核；通用广告法关键词屏不能替代本地规则"})
            coverage.append({"region": region, "approved": False})
            continue
        row = candidates[0]
        required = ("status", "authority", "source", "checked_at", "approved_by", "evidence_file", "content_sha256")
        missing = [key for key in required if pending(row.get(key))]
        jurisdictions = row.get("jurisdictions") or []
        if region in {"全球", "北美", "东南亚", "港澳台", "自定义"} and not jurisdictions:
            missing.append("jurisdictions")
        if str(row.get("status") or "").lower() != "approved":
            missing.append("status=approved")
        if row.get("content_sha256") != content_sha:
            missing.append("content_sha256=current_release")
        if not evidence_exists(root, row.get("evidence_file")):
            missing.append("evidence_file_exists")
        try:
            checked = date.fromisoformat(str(row.get("checked_at")))
            if checked > date.today():
                missing.append("checked_at_not_future")
        except ValueError:
            missing.append("checked_at_valid")
        missing = sorted(set(missing))
        approved = not missing
        coverage.append({"region": region, "approved": approved, "authority": row.get("authority") or "",
                         "source": row.get("source") or "", "checked_at": row.get("checked_at") or "",
                         "jurisdictions": jurisdictions, "evidence_file": row.get("evidence_file") or ""})
        if missing:
            findings.append({"severity": "block", "code": "jurisdiction_review_incomplete",
                             "msg": f"{region} 法律复核缺/失效：{', '.join(missing)}"})
    return regions, coverage, findings


def rights_region_coverage(rights_rows, regions):
    findings = []
    coverage = []
    for row in rights_rows or []:
        if row.get("rights_status") == "not_used":
            coverage.append({"item": row.get("item"), "not_used": True, "approved": row.get("status") == "declared"})
            continue
        raw = row.get("territory") or []
        territories = raw if isinstance(raw, list) else [raw]
        normalized = {str(v).strip().lower() for v in territories if str(v).strip()}
        global_scope = bool(normalized & {"全球", "global", "worldwide", "all territories"})
        missing = [] if global_scope else [region for region in regions if region.lower() not in normalized]
        approved = row.get("status") == "declared" and not missing
        coverage.append({"item": row.get("item"), "territories": territories, "missing_regions": missing,
                         "approved": approved})
        if missing:
            findings.append({"severity": "block", "code": "rights_territory_gap",
                             "msg": f"{row.get('item')} 授权地域不覆盖发行地区：{', '.join(missing)}"})
    return coverage, findings


def build(root: Path, declaration_status="pending", declaration_evidence="",
          explicit_label_status="platform_managed", metadata_status="preserve",
          implicit_label_status="pending"):
    root = root.resolve()
    usage = load(root / "合规" / "ai_usage.json", {}) or {}
    brief = load(root / "需求" / "brief.json", {}) or {}
    platforms = brief.get("platforms") or []
    if isinstance(platforms, str):
        platforms = [platforms]
    uses_ai = any(str(usage.get(k) or "").lower().startswith("ai-") for k in ("visual_mode", "video_mode"))
    findings = []
    settings = platform_pack.parse_settings(root / "_设置.md")
    content_sha = release_content_sha256(root)
    delivery_pack = platform_pack.build_pack(root)
    locale_report = locale_matrix.validate(root)
    variant_report = release_variant_manifest.build(root)
    provenance_report = load(root / "合规" / "provenance_qc.json", {}) or {}
    if not usage:
        findings.append({"severity": "block", "code": "ai_usage_missing", "msg": "缺 ai_usage.json"})
    if uses_ai and (pending(usage.get("image_model")) or pending(usage.get("image_channel"))):
        findings.append({"severity": "block", "code": "ai_image_route_missing",
                         "msg": "AI 使用披露缺具体 image_model/image_channel；旧 image_backend/厂商名不可替代"})
    if uses_ai and pending(declaration_status):
        findings.append({"severity": "block", "code": "platform_declaration_pending",
                         "msg": "AI 广告尚无平台主动声明完成证据；母版可完成，但不可标记发布就绪"})
    if uses_ai and declaration_status == "completed" and pending(declaration_evidence):
        findings.append({"severity": "block", "code": "platform_declaration_evidence_missing",
                         "msg": "声明标记 completed 但缺截图/回执/记录路径"})
    if uses_ai and declaration_status == "completed" and not evidence_exists(root, declaration_evidence):
        findings.append({"severity": "block", "code": "platform_declaration_evidence_unavailable",
                         "msg": "平台声明证据路径不存在/不可查询；不能只填一个文件名"})
    if uses_ai and explicit_label_status == "pending":
        findings.append({"severity": "block", "code": "explicit_label_pending",
                         "msg": "显式标识责任仍为 pending；需确认由生成服务、传播平台或发布方落实"})
    if uses_ai and implicit_label_status in {"pending", "stripped"}:
        findings.append({"severity": "block", "code": "implicit_label_pending",
                         "msg": "隐式标识/文件元数据责任未闭合或被剥离；需记录由服务方、平台或发布方落实"})
    if uses_ai and metadata_status == "stripped":
        findings.append({"severity": "block", "code": "metadata_stripped",
                         "msg": "成片流程声明已剥离生成合成元数据；发布前不得继续流转"})
    if locale_report.get("summary", {}).get("block"):
        findings.append({"severity": "block", "code": "locale_matrix_not_ready",
                         "msg": f"locale matrix 仍有 block={locale_report['summary']['block']}"})
    if variant_report.get("summary", {}).get("block") or not variant_report.get("summary", {}).get("release_ready"):
        findings.append({"severity": "block", "code": "release_variant_manifest_not_ready",
                         "msg": f"逐交付版本发布清单 block={variant_report.get('summary', {}).get('block', 'missing')}"})
    provenance_blocks = ((provenance_report.get("summary") or {}).get("block") if provenance_report else None)
    if uses_ai and (provenance_blocks is None or int(provenance_blocks or 0) > 0):
        findings.append({"severity": "block", "code": "provenance_qc_not_ready",
                         "msg": "最终文件尚未通过实际 AI 元数据/C2PA 探测；metadata_status 字符串不能替代证据"})
    for item in delivery_pack.get("findings") or []:
        if (item.get("severity") == "block" or
                item.get("code") in {"platforms_missing", "platform_spec_missing",
                                     "custom_platform_provenance_missing", "safe_zone_asset_pending",
                                     "safe_zone_evidence_missing", "platform_spec_stale",
                                     "platform_spec_date_invalid", "placement_missing", "placement_spec_missing",
                                     "custom_placement_provenance_missing", "safe_zone_evidence_not_placement_specific"}):
            findings.append({"severity": "block", "code": f"release_{item.get('code')}",
                             "msg": str(item.get("msg") or "平台交付规格未闭合")})
    producer = producer_pack.build_pack(root)
    if int(((producer.get("summary") or {}).get("approval_blocks")) or 0):
        findings.append({"severity": "block", "code": "claim_rights_approval_pending",
                         "msg": "producer_pack 的 claim 引证依据/授权/法律声明仍有阻断"})
    regions, legal_reviews, legal_findings = legal_coverage(root, brief, settings, content_sha)
    findings.extend(legal_findings)
    rights_coverage, rights_findings = rights_region_coverage(producer.get("rights") or [], regions)
    findings.extend(rights_findings)
    payload = {
        "schema_version": 2,
        "kind": "ad_compliance_manifest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platforms": platforms,
        "release_regions": regions,
        "release_content_sha256": content_sha,
        "legal_reviews": legal_reviews,
        "rights_coverage": rights_coverage,
        "uses_ai": uses_ai,
        "ai_usage_path": "合规/ai_usage.json",
        "platform_declaration": {"status": declaration_status, "evidence": declaration_evidence},
        "explicit_label": {"status": explicit_label_status},
        "implicit_label": {"status": implicit_label_status},
        "metadata": {"status": metadata_status},
        "locale_matrix_summary": locale_report.get("summary") or {},
        "release_variant_summary": variant_report.get("summary") or {},
        "provenance_qc_summary": provenance_report.get("summary") or {},
        "standards": [{
            "authority": "official_regulation", "territory": "中国大陆",
            "title": "人工智能生成合成内容标识办法", "effective_date": "2025-09-01",
            "checked_at": "2026-07-11",
            "source": "https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm",
            "scope": "显式标识、文件元数据隐式标识、用户声明与传播平台核验责任",
        }, {
            "authority": "official_regulatory_guidance", "territory": "中国大陆",
            "title": "广告引证内容执法指南", "issued": "2026-06",
            "checked_at": "2026-07-11",
            "source": "https://policy.mofcom.gov.cn/claw/clawContent.shtml?id=106104",
            "scope": "引证内容真实性、来源可查询、条件/范围/有效期、数据方法与显著呈现",
        }, {
            "authority": "official_regulation", "territory": "欧盟",
            "title": "EU AI Act Article 50 transparency obligations", "effective_date": "2026-08-02",
            "checked_at": "2026-07-11",
            "source": "https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content",
            "scope": "机器可读标记与 deepfake/特定 AI 内容显式披露",
        }, {
            "authority": "official_platform_guidance", "territory": "Google Ads",
            "title": "Use AI content label settings and disclosures", "checked_at": "2026-07-11",
            "source": "https://support.google.com/google-ads/editor/answer/17231795?hl=en",
            "scope": "逐素材 AI label 状态、可见 overlay 与 C2PA/SynthID 说明",
        }, {
            "authority": "open_technical_standard", "territory": "global",
            "title": "C2PA Technical Specification 2.3", "checked_at": "2026-07-11",
            "source": "https://spec.c2pa.org/specifications/specifications/2.3/specs/_attachments/C2PA_Specification.pdf",
            "scope": "最终媒体机器可读 provenance 的内容绑定与验证",
        }],
        "platform_pack_summary": delivery_pack.get("summary") or {},
        "summary": {
            "block": sum(1 for f in findings if f["severity"] == "block"),
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
            "release_ready": not any(f["severity"] == "block" for f in findings),
        },
        "findings": findings,
    }
    return payload


def main(argv=None):
    ap = argparse.ArgumentParser(description="build ad release compliance manifest")
    ap.add_argument("project_root")
    ap.add_argument("--declaration-status", default="pending", choices=["pending", "completed", "not_applicable"])
    ap.add_argument("--declaration-evidence", default="")
    ap.add_argument("--explicit-label-status", default="platform_managed",
                    choices=["platform_managed", "service_embedded", "publisher_applied", "not_applicable", "pending"])
    ap.add_argument("--metadata-status", default="preserve", choices=["preserve", "not_applicable", "stripped"])
    ap.add_argument("--implicit-label-status", default="pending",
                    choices=["service_embedded", "platform_managed", "publisher_embedded",
                             "preserve_existing", "not_applicable", "pending", "stripped"])
    ns = ap.parse_args(argv)
    root = Path(ns.project_root)
    payload = build(root, ns.declaration_status, ns.declaration_evidence,
                    ns.explicit_label_status, ns.metadata_status, ns.implicit_label_status)
    locale_payload = locale_matrix.validate(root)
    locale_out = root / "合规" / "locale_matrix_validation.json"
    locale_out.parent.mkdir(parents=True, exist_ok=True)
    locale_out.write_text(json.dumps(locale_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    variant_payload = release_variant_manifest.build(root)
    variant_out = root / "合规" / "release_variant_manifest.json"
    variant_out.write_text(json.dumps(variant_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out = root / "合规" / "compliance_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"# compliance manifest block={payload['summary']['block']} release_ready={payload['summary']['release_ready']}")
    print(f"[ok] {out}")
    return 1 if payload["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
