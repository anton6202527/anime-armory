#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic campaign launch-readiness audit for the ad line.

The checker deliberately does *not* fetch a landing page, call an ad platform,
or pretend that a pixel/event was observed.  It validates structured declarations
and project-local evidence supplied by the publisher/measurement owner.

Outputs:
  <root>/生产数据/campaign_readiness.json
  <root>/生产数据/campaign_readiness.md

Formal launch is fail-closed.  A pure sample/demo may carry the same gaps as
warnings, but can never be reported as release-ready.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence
from urllib.parse import parse_qs, urlsplit, urlunsplit


KIND = "ad_campaign_readiness"
PENDING = {
    "", "待补", "待填写", "待定", "待确认", "未定", "未记录", "占位",
    "pending", "tbd", "unknown", "unavailable", "不可用",
}
FORMAL_MODES = {"formal", "launch", "paid", "正式", "正式投放", "付费投放"}
SAMPLE_MODES = {"sample", "demo", "rough", "preview", "样片", "纯样片", "预览"}
PASS_STATUSES = {"approved", "available", "active", "verified", "passed", "pass", "healthy", "ready"}
NOT_APPLICABLE = {"not_applicable", "not-applicable", "n/a", "na", "不适用"}
TRACKING_TYPES = {"tag", "pixel", "sdk", "capi"}
TRACKING_ALIASES = {
    "gtm": "tag", "web_tag": "tag", "site_tag": "tag",
    "conversion_api": "capi", "conversions_api": "capi", "server_api": "capi",
}
ELIGIBILITY_PASS = {"approved", "allowed", "eligible", "not_restricted", "manual_approved", "not_applicable"}
ELIGIBILITY_FAIL = {"rejected", "prohibited", "restricted", "ineligible", "denied"}
ITEM_ALIASES = {"claim": "claims", "offer": "offer", "cta": "cta", "price": "price", "pricing": "price"}
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FRESHNESS_DAYS = {
    "landing_page": 30,
    "message_reconciliation": 30,
    "eligibility_review": 45,
    "tracking_diagnostics": 14,
    "consent_privacy": 90,
}
OFFICIAL_STANDARDS = [
    {
        "id": "google_ads_destination_requirements",
        "authority": "Google Ads",
        "title": "Destination requirements",
        "url": "https://support.google.com/adspolicy/answer/6368661?hl=en",
        "applies_to": ["landing_page", "routing"],
    },
    {
        "id": "tiktok_landing_page_review",
        "authority": "TikTok for Business",
        "title": "Best practices for your landing page",
        "url": "https://ads.tiktok.com/help/article/ad-review-checklist-landing-page?lang=en",
        "applies_to": ["landing_page", "reconciliation", "eligibility"],
    },
    {
        "id": "google_enhanced_conversions_diagnostics",
        "authority": "Google Ads",
        "title": "About the enhanced conversions for leads diagnostics report",
        "url": "https://support.google.com/google-ads/answer/15249267?hl=en",
        "applies_to": ["measurement", "tracking_diagnostics"],
    },
]


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def pending(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return _norm(value) in PENDING
    if isinstance(value, Mapping):
        return not value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return not value
    return False


def load_json(path: Path) -> tuple[Dict[str, Any], str]:
    if not path.is_file():
        return {}, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, f"invalid: {exc}"
    if not isinstance(payload, dict):
        return {}, "invalid: root must be an object"
    return payload, ""


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_settings(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        match = re.match(r"\s*[-*]?\s*([^#\n:：|]+?)\s*[:：]\s*(.+?)\s*$", line)
        if match:
            out[match.group(1).strip()] = match.group(2).split("#", 1)[0].strip().strip("`")
    return out


def _inside_project(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def evidence_record(root: Path, value: Any) -> Dict[str, Any]:
    """Validate a project-local evidence file without making network calls."""
    ref = str(value or "").strip()
    row: Dict[str, Any] = {
        "declared": bool(ref), "ref": ref, "local": False, "within_project": False,
        "exists": False, "valid": False, "sha256": "", "reason": "",
    }
    if not ref:
        row["reason"] = "missing"
        return row
    if ref.startswith(("http://", "https://", "record:", "doi:")):
        row["reason"] = "external_reference_not_locally_verified"
        return row
    candidate = Path(ref)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        candidate = candidate.resolve()
    except OSError:
        row["reason"] = "unresolvable"
        return row
    row["local"] = True
    row["within_project"] = _inside_project(candidate, root)
    if not row["within_project"]:
        row["reason"] = "outside_project"
        return row
    row["exists"] = candidate.is_file()
    if not row["exists"]:
        row["reason"] = "file_missing"
        return row
    row["valid"] = True
    row["ref"] = candidate.relative_to(root).as_posix()
    row["sha256"] = file_sha256(candidate)
    return row


def valid_http_url(value: Any) -> bool:
    try:
        parts = urlsplit(str(value or "").strip())
        # Accessing .port performs urllib's numeric/range validation.
        _ = parts.port
    except ValueError:
        return False
    return parts.scheme.lower() in {"http", "https"} and bool(parts.netloc) and not bool(parts.username or parts.password)


def canonical_http_url(value: Any) -> str:
    if not valid_http_url(value):
        return ""
    parts = urlsplit(str(value).strip())
    host = (parts.hostname or "").lower()
    port = f":{parts.port}" if parts.port else ""
    path = parts.path or "/"
    return urlunsplit((parts.scheme.lower(), host + port, path.rstrip("/") or "/", parts.query, ""))


def valid_any_deep_link(value: Any) -> bool:
    try:
        parts = urlsplit(str(value or "").strip())
    except ValueError:
        return False
    return bool(parts.scheme and (parts.netloc or parts.path)) and not bool(parts.username or parts.password)


def date_age_days(value: Any, *, today: Optional[date] = None) -> Optional[int]:
    text = str(value or "").strip()
    if not ISO_DATE_RE.fullmatch(text):
        return None
    try:
        checked = date.fromisoformat(text)
    except ValueError:
        return None
    return ((today or date.today()) - checked).days


def valid_date(value: Any) -> bool:
    age = date_age_days(value)
    return age is not None and age >= 0


def date_is_fresh(value: Any, max_age_days: int) -> bool:
    age = date_age_days(value)
    return age is not None and 0 <= age <= max_age_days


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return list(value)
    if value in (None, ""):
        return []
    return [value]


def _unique_strings(values: Iterable[Any]) -> list[str]:
    out: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def target_platforms(brief: Mapping[str, Any]) -> list[str]:
    values = _as_list(brief.get("platforms"))
    placements = brief.get("placements") or []
    if isinstance(placements, Mapping):
        values.extend(placements.keys())
    else:
        for item in _as_list(placements):
            if isinstance(item, Mapping):
                values.append(item.get("platform"))
            else:
                values.append(str(item).partition(":")[0])
    return _unique_strings(values)


def target_jurisdictions(brief: Mapping[str, Any], settings: Mapping[str, str]) -> list[str]:
    values = _as_list(brief.get("release_regions") or brief.get("jurisdictions"))
    setting = settings.get("发行地区") or settings.get("广告法地区") or ""
    if setting and _norm(setting) not in PENDING:
        values.append(setting)
    return _unique_strings(values)


def normalize_mode(brief: Mapping[str, Any], override: str = "auto") -> tuple[str, str]:
    raw: Any = override
    if override == "auto":
        nested = _as_mapping(brief.get("campaign_readiness"))
        raw = brief.get("campaign_mode") or nested.get("mode") or ""
    norm = _norm(raw)
    if norm in FORMAL_MODES:
        return "formal", str(raw)
    if norm in SAMPLE_MODES:
        return "sample", str(raw)
    return "unknown", str(raw or "")


class Audit:
    def __init__(self, mode: str):
        self.mode = mode
        self.findings: list[Dict[str, Any]] = []

    def gap(self, scope: str, code: str, msg: str, *, field: str = "", detail: Any = None,
            hard: bool = False) -> None:
        severity = "block" if hard or self.mode != "sample" else "warn"
        row: Dict[str, Any] = {"severity": severity, "scope": scope, "code": code, "msg": msg}
        if field:
            row["field"] = field
        if detail is not None:
            row["detail"] = detail
        self.findings.append(row)

    def warn(self, scope: str, code: str, msg: str, *, field: str = "", detail: Any = None) -> None:
        row: Dict[str, Any] = {"severity": "warn", "scope": scope, "code": code, "msg": msg}
        if field:
            row["field"] = field
        if detail is not None:
            row["detail"] = detail
        self.findings.append(row)


def check_landing_page(root: Path, brief: Mapping[str, Any], audit: Audit) -> Dict[str, Any]:
    raw_url = brief.get("landing_page")
    if isinstance(raw_url, Mapping):
        url = str(raw_url.get("url") or "").strip()
    else:
        url = str(raw_url or "").strip()
    record = _as_mapping(brief.get("landing_page_readiness"))
    if not record:
        record = _as_mapping(_as_mapping(brief.get("campaign_readiness")).get("landing_page"))
    status = _norm(record.get("status"))
    final_url = str(record.get("final_url") or "").strip()
    redirect_status = _norm(record.get("redirect_status"))
    checked_at = str(record.get("checked_at") or "").strip()
    status_evidence = evidence_record(root, record.get("evidence_file") or record.get("status_evidence_file"))
    redirect_evidence = evidence_record(root, record.get("redirect_evidence_file"))

    if not url:
        audit.gap("landing_page", "landing_page_url_missing", "未声明 landing_page URL。", field="landing_page")
    elif not valid_http_url(url):
        audit.gap("landing_page", "landing_page_url_invalid", "landing_page 必须是无内嵌账号密码的 http(s) URL。",
                  field="landing_page", detail=url)
    if status not in PASS_STATUSES:
        audit.gap("landing_page", "landing_page_status_unverified", "缺落地页可用状态（available/verified/passed）证据。",
                  field="landing_page_readiness.status", detail=status or "missing")
    if not valid_http_url(final_url):
        audit.gap("landing_page", "landing_page_final_url_invalid", "须记录本地检查得到的最终 URL。",
                  field="landing_page_readiness.final_url", detail=final_url or "missing")
    if redirect_status not in {"verified", "passed", "no_redirect", "none"}:
        audit.gap("landing_page", "landing_page_redirect_status_unverified", "须声明 redirect_status=verified/passed/no_redirect。",
                  field="landing_page_readiness.redirect_status", detail=redirect_status or "missing")
    if not status_evidence["valid"]:
        audit.gap("landing_page", "landing_page_status_evidence_missing", "落地页状态证据必须是项目内真实文件。",
                  field="landing_page_readiness.evidence_file", detail=status_evidence)
    if not redirect_evidence["valid"]:
        audit.gap("landing_page", "landing_page_redirect_evidence_missing", "跳转链/无跳转结论须绑定项目内证据文件。",
                  field="landing_page_readiness.redirect_evidence_file", detail=redirect_evidence)
    if not valid_date(checked_at):
        audit.gap("landing_page", "landing_page_checked_at_invalid", "落地页检查日期须为不晚于今天的 YYYY-MM-DD。",
                  field="landing_page_readiness.checked_at", detail=checked_at or "missing")
    elif not date_is_fresh(checked_at, FRESHNESS_DAYS["landing_page"]):
        audit.gap("landing_page", "landing_page_evidence_stale",
                  f"落地页状态/跳转证据超过 {FRESHNESS_DAYS['landing_page']} 天，须重新核验。",
                  field="landing_page_readiness.checked_at", detail={"checked_at": checked_at,
                                                                       "age_days": date_age_days(checked_at)})
    if valid_http_url(url) and valid_http_url(final_url):
        source_host = (urlsplit(url).hostname or "").lower()
        final_host = (urlsplit(final_url).hostname or "").lower()
        if source_host != final_host and redirect_status in {"no_redirect", "none"}:
            audit.gap("landing_page", "landing_page_redirect_contradiction",
                      "初始 URL 与最终 URL 域名不同，但记录声称无跳转。", detail={"source": source_host, "final": final_host})
    return {
        "url": url, "url_valid": valid_http_url(url), "status": status, "checked_at": checked_at,
        "evidence_age_days": date_age_days(checked_at),
        "final_url": final_url, "final_url_valid": valid_http_url(final_url),
        "redirect_status": redirect_status, "status_evidence": status_evidence,
        "redirect_evidence": redirect_evidence,
        "network_checked_by_this_script": False,
    }


def _message_sources(brief: Mapping[str, Any]) -> Dict[str, Any]:
    mandatories = _as_mapping(brief.get("mandatories"))
    offer = brief.get("offer")
    price = brief.get("price") or brief.get("pricing")
    if isinstance(offer, Mapping):
        price = price or offer.get("price") or offer.get("pricing")
        offer = offer.get("text") or offer.get("offer") or offer.get("name")
    claims = [row for row in _as_list(brief.get("claims")) if not pending(row)]
    return {
        "offer": offer or "", "claims": claims,
        "cta": mandatories.get("endcard_cta") or brief.get("cta") or "",
        "price": price or "",
    }


def _normalized_items(values: Any) -> set[str]:
    out: set[str] = set()
    for raw in _as_list(values):
        key = ITEM_ALIASES.get(_norm(raw), _norm(raw))
        if key:
            out.add(key)
    return out


def check_reconciliation(root: Path, brief: Mapping[str, Any], landing: Mapping[str, Any],
                         audit: Audit) -> Dict[str, Any]:
    record = _as_mapping(brief.get("message_reconciliation"))
    if not record:
        record = _as_mapping(_as_mapping(brief.get("campaign_readiness")).get("message_reconciliation"))
    sources = _message_sources(brief)
    checked = _normalized_items(record.get("checked_items"))
    not_applicable = _normalized_items(record.get("not_applicable_items"))
    status = _norm(record.get("status"))
    evidence = evidence_record(root, record.get("evidence_file"))
    reviewed_at = str(record.get("reviewed_at") or "").strip()
    approved_by = str(record.get("approved_by") or "").strip()
    bound_url = str(record.get("landing_page_url") or "").strip()

    dispositions: Dict[str, str] = {}
    for item in ("offer", "claims", "cta", "price"):
        present = not pending(sources[item])
        if present and item in not_applicable:
            audit.gap("reconciliation", "reconciliation_item_incorrectly_na",
                      f"brief 已有 {item}，不能在落地页对账中标为不适用。", field=f"message_reconciliation.{item}")
        if present and item not in checked:
            audit.gap("reconciliation", "reconciliation_item_unchecked",
                      f"brief 中的 {item} 尚未与落地页逐项对账。", field="message_reconciliation.checked_items")
        if not present and item not in not_applicable:
            audit.gap("reconciliation", "reconciliation_item_unaccounted",
                      f"{item} 无源值；须补 brief 或在具名对账中明确 not_applicable。",
                      field="message_reconciliation.not_applicable_items")
        dispositions[item] = "checked" if item in checked else "not_applicable" if item in not_applicable else "missing"

    if status not in {"matched", "approved", "verified", "passed"}:
        audit.gap("reconciliation", "message_reconciliation_unapproved", "offer/claim/CTA/价格与落地页的对账状态未通过。",
                  field="message_reconciliation.status", detail=status or "missing")
    if not evidence["valid"]:
        audit.gap("reconciliation", "message_reconciliation_evidence_missing", "对账须绑定项目内截图/导出/签字记录。",
                  field="message_reconciliation.evidence_file", detail=evidence)
    if pending(approved_by):
        audit.gap("reconciliation", "message_reconciliation_reviewer_missing", "对账缺具名批准人。",
                  field="message_reconciliation.approved_by")
    if not valid_date(reviewed_at):
        audit.gap("reconciliation", "message_reconciliation_date_invalid", "对账日期须为不晚于今天的 YYYY-MM-DD。",
                  field="message_reconciliation.reviewed_at", detail=reviewed_at or "missing")
    elif not date_is_fresh(reviewed_at, FRESHNESS_DAYS["message_reconciliation"]):
        audit.gap("reconciliation", "message_reconciliation_stale",
                  f"落地页商业信息对账超过 {FRESHNESS_DAYS['message_reconciliation']} 天，须重新核验。",
                  field="message_reconciliation.reviewed_at",
                  detail={"reviewed_at": reviewed_at, "age_days": date_age_days(reviewed_at)})
    if not valid_http_url(bound_url) or canonical_http_url(bound_url) != canonical_http_url(landing.get("url")):
        audit.gap("reconciliation", "message_reconciliation_url_unbound", "对账记录必须绑定当前 landing_page URL。",
                  field="message_reconciliation.landing_page_url", detail=bound_url or "missing")
    return {
        "status": status, "landing_page_url": bound_url, "reviewed_at": reviewed_at,
        "review_age_days": date_age_days(reviewed_at),
        "approved_by": approved_by, "sources": sources, "dispositions": dispositions,
        "checked_items": sorted(checked), "not_applicable_items": sorted(not_applicable), "evidence": evidence,
    }


def _review_matches(row: Mapping[str, Any], platform: str, jurisdiction: str, category: str) -> bool:
    wild = {"*", "all", "全部", "所有"}
    row_platform = _norm(row.get("platform"))
    row_jurisdiction = _norm(row.get("jurisdiction") or row.get("region"))
    row_category = _norm(row.get("industry_category") or row.get("category"))
    return (
        (row_platform == _norm(platform) or row_platform in wild)
        and (row_jurisdiction == _norm(jurisdiction) or row_jurisdiction in wild)
        and (row_category == _norm(category) or row_category in wild)
    )


def _review_specificity(row: Mapping[str, Any], platform: str, jurisdiction: str, category: str) -> int:
    return sum([
        _norm(row.get("platform")) == _norm(platform),
        _norm(row.get("jurisdiction") or row.get("region")) == _norm(jurisdiction),
        _norm(row.get("industry_category") or row.get("category")) == _norm(category),
    ])


def check_eligibility(root: Path, brief: Mapping[str, Any], settings: Mapping[str, str],
                      audit: Audit) -> Dict[str, Any]:
    category = str(brief.get("industry_category") or "").strip()
    platforms = target_platforms(brief)
    jurisdictions = target_jurisdictions(brief, settings)
    raw_reviews = brief.get("eligibility_reviews")
    if raw_reviews is None:
        raw_reviews = _as_mapping(brief.get("campaign_readiness")).get("eligibility_reviews")
    reviews = [row for row in _as_list(raw_reviews) if isinstance(row, Mapping)]
    normalized_reviews: list[Dict[str, Any]] = []
    for row in reviews:
        normalized_reviews.append({
            **dict(row), "status": _norm(row.get("status")),
            "evidence": evidence_record(root, row.get("evidence_file")),
        })

    if pending(category):
        audit.gap("eligibility", "industry_category_missing", "缺 industry_category，无法判断受限行业准入。",
                  field="industry_category")
    if not platforms:
        audit.gap("eligibility", "eligibility_platform_missing", "缺实际目标平台，无法建立准入覆盖矩阵。",
                  field="platforms/placements")
    if not jurisdictions:
        audit.gap("eligibility", "eligibility_jurisdiction_missing", "缺具体发行辖区，不能用“海外/跨平台”代替。",
                  field="release_regions")

    coverage: list[Dict[str, Any]] = []
    if not pending(category):
        for platform in platforms:
            for jurisdiction in jurisdictions:
                candidates = [row for row in normalized_reviews if _review_matches(row, platform, jurisdiction, category)]
                if candidates:
                    best_score = max(_review_specificity(row, platform, jurisdiction, category) for row in candidates)
                    candidates = [row for row in candidates if _review_specificity(row, platform, jurisdiction, category) == best_score]
                    selected = next((row for row in candidates if row.get("status") in ELIGIBILITY_FAIL), candidates[0])
                else:
                    selected = None
                selected_age = date_age_days(selected.get("reviewed_at")) if selected else None
                selected_date_valid = bool(selected_age is not None and selected_age >= 0)
                selected_date_fresh = bool(
                    selected_date_valid and selected_age <= FRESHNESS_DAYS["eligibility_review"])
                valid = bool(
                    selected and selected.get("status") in ELIGIBILITY_PASS
                    and selected.get("evidence", {}).get("valid")
                    and not pending(selected.get("reviewed_by") or selected.get("approved_by"))
                    and selected_date_fresh
                )
                coverage.append({
                    "platform": platform, "jurisdiction": jurisdiction, "industry_category": category,
                    "covered": valid, "selected_review": selected, "review_age_days": selected_age,
                })
                if selected and selected.get("status") in ELIGIBILITY_FAIL:
                    audit.gap("eligibility", "industry_or_platform_ineligible",
                              f"{platform} × {jurisdiction} 的准入复核结果为 {selected.get('status')}。",
                              detail={"platform": platform, "jurisdiction": jurisdiction, "status": selected.get("status")})
                elif selected and selected_date_valid and not selected_date_fresh:
                    audit.gap("eligibility", "eligibility_review_stale",
                              f"{platform} × {jurisdiction} 的行业准入复核超过 "
                              f"{FRESHNESS_DAYS['eligibility_review']} 天。",
                              field="eligibility_reviews.reviewed_at",
                              detail={"platform": platform, "jurisdiction": jurisdiction,
                                      "age_days": selected_age})
                elif not valid:
                    audit.gap("eligibility", "eligibility_review_missing",
                              f"{platform} × {jurisdiction} 缺当前行业准入/人工复核证据、具名复核人或日期。",
                              field="eligibility_reviews", detail={"platform": platform, "jurisdiction": jurisdiction})
    return {
        "industry_category": category, "platforms": platforms, "jurisdictions": jurisdictions,
        "reviews": normalized_reviews, "coverage": coverage,
    }


def _event_values(row: Mapping[str, Any]) -> list[str]:
    values = _as_list(row.get("events"))
    if row.get("conversion_event") or row.get("event"):
        values.append(row.get("conversion_event") or row.get("event"))
    return [_norm(value) for value in values if not pending(value)]


def _platform_matches(declared: Any, platform: str) -> bool:
    value = _norm(declared)
    return value == _norm(platform) or value in {"*", "all", "全部", "所有", "cross_platform"}


def check_measurement(root: Path, brief: Mapping[str, Any], audit: Audit) -> Dict[str, Any]:
    measurement = _as_mapping(brief.get("measurement"))
    event = str(measurement.get("conversion_event") or "").strip()
    attribution = str(measurement.get("attribution_window") or "").strip()
    integrations_raw = measurement.get("tracking_integrations") or measurement.get("integrations") or []
    if not integrations_raw and isinstance(measurement.get("tracking"), Mapping):
        integrations_raw = [measurement.get("tracking")]
    integrations = [row for row in _as_list(integrations_raw) if isinstance(row, Mapping)]
    platforms = target_platforms(brief)
    normalized: list[Dict[str, Any]] = []

    if pending(event):
        audit.gap("measurement", "conversion_event_missing", "正式投放前必须声明 conversion_event。",
                  field="measurement.conversion_event")
    if pending(attribution):
        audit.gap("measurement", "attribution_window_missing", "缺归因窗，投放结果无法按同一口径解释。",
                  field="measurement.attribution_window")

    for index, source in enumerate(integrations, 1):
        kind = TRACKING_ALIASES.get(_norm(source.get("type")), _norm(source.get("type")))
        status = _norm(source.get("status"))
        diagnostics_status = _norm(source.get("diagnostics_status"))
        diagnostics_checked_at = str(source.get("diagnostics_checked_at") or source.get("checked_at") or "").strip()
        proof = evidence_record(root, source.get("evidence_file"))
        diagnostics_proof = evidence_record(root, source.get("diagnostics_evidence_file"))
        events = _event_values(source)
        valid = True
        if kind not in TRACKING_TYPES:
            audit.gap("measurement", "tracking_type_invalid", "tracking integration type 必须是 tag/pixel/sdk/capi。",
                      field=f"measurement.tracking_integrations[{index}].type", detail=kind or "missing")
            valid = False
        if status not in PASS_STATUSES:
            audit.gap("measurement", "tracking_status_unverified", "tracking integration 尚未 verified/active/passed。",
                      field=f"measurement.tracking_integrations[{index}].status", detail=status or "missing")
            valid = False
        if diagnostics_status not in PASS_STATUSES:
            audit.gap("measurement", "tracking_diagnostics_unverified", "tag/pixel/SDK/CAPI diagnostics 未通过。",
                      field=f"measurement.tracking_integrations[{index}].diagnostics_status",
                      detail=diagnostics_status or "missing")
            valid = False
        if not valid_date(diagnostics_checked_at):
            audit.gap("measurement", "tracking_checked_at_invalid",
                      "tracking diagnostics 日期须为不晚于今天的 YYYY-MM-DD。",
                      field=f"measurement.tracking_integrations[{index}].diagnostics_checked_at",
                      detail=diagnostics_checked_at or "missing")
            valid = False
        elif not date_is_fresh(diagnostics_checked_at, FRESHNESS_DAYS["tracking_diagnostics"]):
            audit.gap("measurement", "tracking_diagnostics_stale",
                      f"tracking diagnostics 超过 {FRESHNESS_DAYS['tracking_diagnostics']} 天，须重新验证事件回传。",
                      field=f"measurement.tracking_integrations[{index}].diagnostics_checked_at",
                      detail={"checked_at": diagnostics_checked_at,
                              "age_days": date_age_days(diagnostics_checked_at)})
            valid = False
        if not proof["valid"]:
            audit.gap("measurement", "tracking_evidence_missing", "tracking 安装/事件证据必须是项目内文件。",
                      field=f"measurement.tracking_integrations[{index}].evidence_file", detail=proof)
            valid = False
        if not diagnostics_proof["valid"]:
            audit.gap("measurement", "tracking_diagnostics_evidence_missing", "diagnostics 须绑定项目内导出或截图。",
                      field=f"measurement.tracking_integrations[{index}].diagnostics_evidence_file",
                      detail=diagnostics_proof)
            valid = False
        if not pending(event) and _norm(event) not in events:
            audit.gap("measurement", "tracking_event_mismatch", "tracking integration 未绑定 brief 的 conversion_event。",
                      field=f"measurement.tracking_integrations[{index}].events",
                      detail={"expected": event, "declared": events})
            valid = False
        platform = str(source.get("platform") or "").strip()
        if pending(platform):
            audit.gap("measurement", "tracking_platform_missing", "tracking integration 缺 platform/all 作用域。",
                      field=f"measurement.tracking_integrations[{index}].platform")
            valid = False
        normalized.append({
            **dict(source), "type": kind, "status": status, "diagnostics_status": diagnostics_status,
            "diagnostics_checked_at": diagnostics_checked_at,
            "diagnostics_age_days": date_age_days(diagnostics_checked_at),
            "events": events, "evidence": proof, "diagnostics_evidence": diagnostics_proof, "valid": valid,
        })

    if not normalized:
        audit.gap("measurement", "tracking_integration_missing", "缺 tag/pixel/SDK/CAPI 安装与 diagnostics 记录。",
                  field="measurement.tracking_integrations")
    for platform in platforms:
        if not any(row.get("valid") and _platform_matches(row.get("platform"), platform) for row in normalized):
            audit.gap("measurement", "tracking_platform_uncovered", f"{platform} 缺可验证的 tracking integration 覆盖。",
                      field="measurement.tracking_integrations", detail=platform)
    return {
        "conversion_event": event, "attribution_window": attribution,
        "tracking_integrations": normalized, "platforms": platforms,
    }


def _not_applicable_record(record: Mapping[str, Any]) -> bool:
    return _norm(record.get("status")) in NOT_APPLICABLE


def check_utm_deep_link(root: Path, brief: Mapping[str, Any], audit: Audit) -> Dict[str, Any]:
    measurement = _as_mapping(brief.get("measurement"))
    utm = _as_mapping(measurement.get("utm") or brief.get("utm"))
    deep = _as_mapping(measurement.get("deep_link") or brief.get("deep_link"))
    utm_status = _norm(utm.get("status"))
    utm_evidence = evidence_record(root, utm.get("evidence_file"))
    utm_url = str(utm.get("example_url") or utm.get("url") or "").strip()
    query = parse_qs(urlsplit(utm_url).query) if valid_http_url(utm_url) else {}
    params = _as_mapping(utm.get("parameters"))
    utm_values = {
        "source": utm.get("source") or params.get("source") or (query.get("utm_source") or [""])[0],
        "medium": utm.get("medium") or params.get("medium") or (query.get("utm_medium") or [""])[0],
        "campaign": utm.get("campaign") or params.get("campaign") or (query.get("utm_campaign") or [""])[0],
    }
    if _not_applicable_record(utm):
        if pending(utm.get("approved_by")) or not utm_evidence["valid"]:
            audit.gap("routing", "utm_na_unapproved", "UTM 标为不适用时仍须具名批准并绑定证据。",
                      field="measurement.utm")
    else:
        if utm_status not in {"verified", "approved", "passed", "ready"}:
            audit.gap("routing", "utm_status_unverified", "UTM 状态未通过。", field="measurement.utm.status")
        if not valid_http_url(utm_url):
            audit.gap("routing", "utm_example_url_invalid", "须提供含 UTM 的有效 example_url。",
                      field="measurement.utm.example_url", detail=utm_url or "missing")
        for key, value in utm_values.items():
            if pending(value):
                audit.gap("routing", "utm_parameter_missing", f"缺 utm_{key}。", field=f"measurement.utm.{key}")
        if not utm_evidence["valid"]:
            audit.gap("routing", "utm_evidence_missing", "UTM 测试/解析证据必须是项目内文件。",
                      field="measurement.utm.evidence_file", detail=utm_evidence)

    deep_status = _norm(deep.get("status"))
    deep_evidence = evidence_record(root, deep.get("evidence_file"))
    deep_url = str(deep.get("url") or "").strip()
    fallback_url = str(deep.get("fallback_url") or "").strip()
    if _not_applicable_record(deep):
        if pending(deep.get("approved_by")) or not deep_evidence["valid"]:
            audit.gap("routing", "deep_link_na_unapproved", "deep link 标为不适用时须具名批准并绑定证据。",
                      field="measurement.deep_link")
    else:
        if deep_status not in {"verified", "approved", "passed", "ready"}:
            audit.gap("routing", "deep_link_status_unverified", "deep link 状态未通过。",
                      field="measurement.deep_link.status")
        if not valid_any_deep_link(deep_url):
            audit.gap("routing", "deep_link_url_invalid", "deep link URL/scheme 无效。",
                      field="measurement.deep_link.url", detail=deep_url or "missing")
        if not valid_http_url(fallback_url):
            audit.gap("routing", "deep_link_fallback_invalid", "deep link 须有有效 http(s) fallback URL。",
                      field="measurement.deep_link.fallback_url", detail=fallback_url or "missing")
        if not deep_evidence["valid"]:
            audit.gap("routing", "deep_link_evidence_missing", "deep link/fallback 测试须绑定项目内证据。",
                      field="measurement.deep_link.evidence_file", detail=deep_evidence)
    return {
        "utm": {"status": utm_status, "not_applicable": _not_applicable_record(utm),
                "example_url": utm_url, "parameters": utm_values, "evidence": utm_evidence},
        "deep_link": {"status": deep_status, "not_applicable": _not_applicable_record(deep),
                      "url": deep_url, "fallback_url": fallback_url, "evidence": deep_evidence},
    }


def check_consent_privacy(root: Path, brief: Mapping[str, Any], audit: Audit) -> Dict[str, Any]:
    measurement = _as_mapping(brief.get("measurement"))
    record = _as_mapping(measurement.get("consent_privacy") or brief.get("consent_privacy"))
    status = _norm(record.get("status"))
    consent_status = _norm(record.get("consent_status") or record.get("consent_mode_status"))
    privacy_status = _norm(record.get("privacy_status") or record.get("privacy_notice_status"))
    privacy_url = str(record.get("privacy_notice_url") or "").strip()
    evidence = evidence_record(root, record.get("evidence_file"))
    approved_by = str(record.get("approved_by") or "").strip()
    reviewed_at = str(record.get("reviewed_at") or "").strip()

    if status not in {"approved", "verified", "passed", "ready"}:
        audit.gap("privacy", "consent_privacy_status_unapproved", "consent/privacy 总体状态未批准。",
                  field="measurement.consent_privacy.status")
    if consent_status not in PASS_STATUSES | NOT_APPLICABLE:
        audit.gap("privacy", "consent_status_unverified", "consent/consent mode 状态未验证或明确不适用。",
                  field="measurement.consent_privacy.consent_status")
    if privacy_status not in {"approved", "verified", "published", "passed", "ready"}:
        audit.gap("privacy", "privacy_status_unverified", "隐私声明状态未发布/核验。",
                  field="measurement.consent_privacy.privacy_status")
    if not valid_http_url(privacy_url):
        audit.gap("privacy", "privacy_notice_url_invalid", "须提供有效隐私声明 URL。",
                  field="measurement.consent_privacy.privacy_notice_url", detail=privacy_url or "missing")
    if not evidence["valid"]:
        audit.gap("privacy", "consent_privacy_evidence_missing", "consent/privacy 复核须绑定项目内证据。",
                  field="measurement.consent_privacy.evidence_file", detail=evidence)
    if pending(approved_by):
        audit.gap("privacy", "consent_privacy_reviewer_missing", "consent/privacy 复核缺具名批准人。",
                  field="measurement.consent_privacy.approved_by")
    if not valid_date(reviewed_at):
        audit.gap("privacy", "consent_privacy_date_invalid", "consent/privacy 复核日期须为不晚于今天的 YYYY-MM-DD。",
                  field="measurement.consent_privacy.reviewed_at", detail=reviewed_at or "missing")
    elif not date_is_fresh(reviewed_at, FRESHNESS_DAYS["consent_privacy"]):
        audit.gap("privacy", "consent_privacy_review_stale",
                  f"consent/privacy 复核超过 {FRESHNESS_DAYS['consent_privacy']} 天，须重新确认。",
                  field="measurement.consent_privacy.reviewed_at",
                  detail={"reviewed_at": reviewed_at, "age_days": date_age_days(reviewed_at)})
    return {
        "status": status, "consent_status": consent_status, "privacy_status": privacy_status,
        "privacy_notice_url": privacy_url, "approved_by": approved_by, "reviewed_at": reviewed_at,
        "review_age_days": date_age_days(reviewed_at),
        "evidence": evidence,
    }


def evaluate(root: Path, mode: str = "auto") -> Dict[str, Any]:
    root = root.resolve()
    brief_path = root / "需求" / "brief.json"
    brief, brief_error = load_json(brief_path)
    normalized_mode, declared_mode = normalize_mode(brief, mode)
    audit = Audit(normalized_mode)
    if brief_error:
        audit.gap("contract", "brief_unreadable", "需求/brief.json 缺失或不是有效 JSON 对象。",
                  field="需求/brief.json", detail=brief_error, hard=True)
    if normalized_mode == "unknown":
        audit.gap("contract", "campaign_mode_missing", "须显式声明 campaign_mode=formal 或 sample；未知模式按正式投放阻断。",
                  field="campaign_mode", detail=declared_mode or "missing", hard=True)
    settings = parse_settings(root / "_设置.md")
    landing = check_landing_page(root, brief, audit)
    reconciliation = check_reconciliation(root, brief, landing, audit)
    eligibility = check_eligibility(root, brief, settings, audit)
    measurement = check_measurement(root, brief, audit)
    routing = check_utm_deep_link(root, brief, audit)
    privacy = check_consent_privacy(root, brief, audit)
    counts = {
        severity: sum(row["severity"] == severity for row in audit.findings)
        for severity in ("block", "warn", "info")
    }
    scopes: Dict[str, Dict[str, Any]] = {}
    for scope in ("contract", "landing_page", "reconciliation", "eligibility", "measurement", "routing", "privacy"):
        rows = [row for row in audit.findings if row["scope"] == scope]
        scopes[scope] = {
            "block": sum(row["severity"] == "block" for row in rows),
            "warn": sum(row["severity"] == "warn" for row in rows),
            "status": "block" if any(row["severity"] == "block" for row in rows)
                      else "warn" if rows else "pass",
        }
    release_ready = normalized_mode == "formal" and counts["block"] == 0
    return {
        "schema_version": 1, "kind": KIND,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(root), "brief_path": "需求/brief.json",
        "brief_sha256": file_sha256(brief_path) if brief_path.is_file() else "",
        "mode": normalized_mode, "declared_mode": declared_mode,
        "policy": {
            "formal": "fail_closed",
            "sample": "readiness gaps are warnings; sample is never release-ready",
            "network_actions": "none",
            "evidence_boundary": "project-local files only; external URLs/records are not treated as locally verified evidence",
            "freshness_days": FRESHNESS_DAYS,
        },
        "official_standards": [
            {**row, "catalog_checked_at": date.today().isoformat(),
             "use": "reference metadata only; this audit does not fetch or simulate platform review"}
            for row in OFFICIAL_STANDARDS
        ],
        "checks": {
            "landing_page": landing, "message_reconciliation": reconciliation,
            "eligibility": eligibility, "measurement": measurement,
            "routing": routing, "consent_privacy": privacy,
        },
        "scope_summary": scopes,
        "summary": {
            **counts, "approved_for_mode": counts["block"] == 0,
            "release_ready": release_ready,
            "sample_ready_with_warnings": normalized_mode == "sample" and counts["block"] == 0,
        },
        "findings": audit.findings,
        "limitations": [
            "本脚本没有访问落地页，URL 可达性/移动端体验/跳转结论只核验用户提供的项目内证据。",
            "本脚本没有调用广告平台，行业准入、事件回传、diagnostics、consent 与隐私状态只核验结构化声明和本地证据。",
        ],
    }


def _md_cell(value: Any) -> str:
    return str(value if value not in (None, "") else "—").replace("|", "\\|").replace("\n", " ")


def write_markdown(path: Path, report: Mapping[str, Any]) -> None:
    summary = _as_mapping(report.get("summary"))
    lines = [
        "# Campaign Readiness",
        "",
        f"- 模式: `{report.get('mode')}`",
        f"- 正式投放 release-ready: `{str(bool(summary.get('release_ready'))).lower()}`",
        f"- BLOCK / WARN: {summary.get('block', 0)} / {summary.get('warn', 0)}",
        "- 证据边界: 仅核验项目内文件；本脚本未访问落地页、广告平台或埋点后台。",
        "",
        "## Scope Summary",
        "",
        "| Scope | Status | Block | Warn |",
        "|---|---:|---:|---:|",
    ]
    for scope, row in _as_mapping(report.get("scope_summary")).items():
        row = _as_mapping(row)
        lines.append(f"| {_md_cell(scope)} | {_md_cell(row.get('status'))} | {row.get('block', 0)} | {row.get('warn', 0)} |")
    lines.extend(["", "## Official Standards", "", "| Authority | Standard | Applies to |", "|---|---|---|"])
    for row in report.get("official_standards") or []:
        applies_to = ", ".join(str(value) for value in row.get("applies_to") or [])
        title = f"[{_md_cell(row.get('title'))}]({_md_cell(row.get('url'))})"
        lines.append(f"| {_md_cell(row.get('authority'))} | {title} | {_md_cell(applies_to)} |")
    lines.extend(["", "## Findings", "", "| Severity | Scope | Code | Message |", "|---|---|---|---|"])
    findings = report.get("findings") or []
    if findings:
        for row in findings:
            lines.append(
                f"| {_md_cell(row.get('severity'))} | {_md_cell(row.get('scope'))} | "
                f"`{_md_cell(row.get('code'))}` | {_md_cell(row.get('msg'))} |"
            )
    else:
        lines.append("| info | all | `ready` | 结构化检查与本地证据检查均通过。 |")
    lines.extend(["", "## Limitations", ""])
    for item in report.get("limitations") or []:
        lines.append(f"- {item}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(root: Path, mode: str = "auto", out_json: Optional[Path] = None) -> Dict[str, Any]:
    root = root.resolve()
    report = evaluate(root, mode)
    out_json = (out_json.resolve() if out_json else root / "生产数据" / "campaign_readiness.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md = out_json.with_suffix(".md")
    write_markdown(out_md, report)
    report["_json_path"] = str(out_json)
    report["_md_path"] = str(out_md)
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="validate ad campaign launch readiness from local evidence")
    ap.add_argument("project_root")
    ap.add_argument("--mode", default="auto", choices=("auto", "formal", "sample"),
                    help="auto 读取 brief.campaign_mode；未知模式按正式投放阻断")
    ap.add_argument("--json", default=None, help="自定义 JSON 输出路径；Markdown 写同名 .md")
    ns = ap.parse_args(argv)
    report = write_report(Path(ns.project_root), ns.mode, Path(ns.json) if ns.json else None)
    summary = report["summary"]
    print(
        "# campaign_readiness "
        f"mode={report['mode']} release_ready={summary['release_ready']} "
        f"block={summary['block']} warn={summary['warn']}"
    )
    print(f"[ok] {report['_json_path']}")
    return 1 if summary["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
