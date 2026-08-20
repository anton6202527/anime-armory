#!/usr/bin/env python3
"""Bind every final ad variant to placement, locale, law, rights and disclosures.

AI-origin labels and commercial/paid-partnership disclosures are deliberately
separate evidence chains: one never satisfies the other.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

import locale_matrix
import platform_pack
import producer_pack
import dependency_graph
import placement_adaptation
import render_profile


KIND = "ad_release_variant_manifest"
SCHEMA_VERSION = 2
PENDING = {"", "待补", "未定", "未记录", "tbd", "pending"}
GLOBAL_MEDIA_SCOPE = {"all", "all media", "all_media", "全媒体", "数字媒体", "digital", "digital paid media", "paid_social"}
FORMAL_CAMPAIGN_MODES = {"formal", "launch", "paid", "正式", "正式投放", "付费投放"}
COMMERCIAL_COMPLETE = {"completed"}
CREATOR_AUTH_COMPLETE = {"approved", "completed", "verified"}
SPARK_MODES = {"spark", "non_spark"}
CREATOR_RELATIONSHIP_MARKERS = (
    "creator", "influencer", "paid_partnership", "affiliate", "创作者", "达人", "博主", "付费合作",
)
RELEASE_RECEIPT_MAX_AGE_DAYS = 90


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def sha(path: Path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def logical_manifest_sha(value: Mapping[str, Any]) -> str:
    """Digest a generated manifest without clock-only metadata."""
    return canonical_sha({key: child for key, child in value.items()
                          if key != "generated_at" and not str(key).startswith("_")})


def pending(value: Any) -> bool:
    return str(value or "").strip().lower() in PENDING


def valid_checked_at(value: Any):
    try:
        checked = date.fromisoformat(str(value)[:10])
        return date.today() - timedelta(days=RELEASE_RECEIPT_MAX_AGE_DAYS) <= checked <= date.today()
    except ValueError:
        return False


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _formal_paid(brief: Mapping[str, Any]) -> bool:
    return _norm(brief.get("campaign_mode")) in FORMAL_CAMPAIGN_MODES


def _commercial_context(brief: Mapping[str, Any]) -> dict[str, Any]:
    raw = brief.get("commercial_content") if isinstance(brief.get("commercial_content"), Mapping) else {}
    creator_raw = raw.get("creator_involved", False)
    creator_declared = creator_raw is True or _norm(creator_raw) in {"true", "yes", "1", "是", "涉及"}
    relationship = str(raw.get("relationship_type") or "").strip()
    relationship_norm = _norm(relationship)
    creator_inferred = any(marker in relationship_norm for marker in CREATOR_RELATIONSHIP_MARKERS)
    return {
        "relationship_type": relationship,
        "creator_involved": creator_declared or creator_inferred,
        "creator_involved_declared": creator_declared,
        "creator_inferred_from_relationship": creator_inferred,
        "account_owner": str(raw.get("account_owner") or "").strip(),
    }


def _release_chain_finding(required: bool, code: str, msg: str, path: str):
    return {"severity": "block" if required else "warn", "code": code, "msg": msg, "path": path}


def compose_release_chain(root: Path, plan: Mapping[str, Any] | None = None, *,
                          require_acceptance: bool = True,
                          formal: bool | None = None) -> dict[str, Any]:
    """Validate the deterministic compose-to-release evidence chain.

    Formal paid release is fail closed.  A sample project receives the same
    diagnostics as warnings, so it can remain a non-launchable creative sample
    without fabricating platform/compose acceptance.
    """
    root = root.resolve()
    brief = load(root / "需求" / "brief.json", {}) or {}
    required = _formal_paid(brief) if formal is None else bool(formal)
    plan_path = root / "合成" / "delivery_plan.json"
    plan = dict(plan) if isinstance(plan, Mapping) else (load(plan_path, {}) or {})
    findings: list[dict[str, Any]] = []

    def gap(code: str, msg: str, path: str):
        findings.append(_release_chain_finding(required, code, msg, path))

    plan_summary = plan.get("summary") if isinstance(plan.get("summary"), Mapping) else {}
    plan_digest = canonical_sha(plan)
    if not plan_path.is_file():
        gap("release_delivery_plan_missing", "正式发布缺 canonical delivery_plan.json", "合成/delivery_plan.json")
    if plan.get("kind") != "ad_delivery_plan" or plan.get("schema_version") != 5:
        gap("release_delivery_plan_schema_invalid",
            "正式发布要求 kind=ad_delivery_plan/schema_version=5 的 canonical delivery plan",
            "合成/delivery_plan.json")
    if not isinstance(plan.get("summary"), Mapping) or "block" not in plan_summary:
        gap("release_delivery_plan_summary_missing", "delivery plan 缺机器可判定 summary.block",
            "合成/delivery_plan.json")
    elif int(plan_summary.get("block") or 0) != 0:
        gap("release_delivery_plan_blocked", "delivery plan 先决条件仍有 block",
            "合成/delivery_plan.json")

    active = [row for row in plan.get("deliverables") or []
              if isinstance(row, Mapping) and row.get("status") != "cancelled"]
    expected_media = {
        str(row.get("deliverable_id") or ""): sha(root / str(row.get("expected_path") or ""))
        for row in active if row.get("deliverable_id")
    }
    expected_execution = {
        str(row.get("deliverable_id") or ""): sha(
            root / "生产数据" / "placement_adaptation_receipts"
            / f"{row.get('deliverable_id')}.json")
        for row in active if row.get("deliverable_id") and row.get("kind") == "reframe"
    }
    if not active:
        gap("release_delivery_plan_empty", "delivery plan 无未取消交付件", "合成/delivery_plan.json")

    profile_path = root / "生产数据" / "render_profile.json"
    profile = load(profile_path, {}) or {}
    profile_logical = {key: value for key, value in profile.items()
                       if key != "profile_sha256" and not str(key).startswith("_")}
    profile_digest = canonical_sha(profile_logical) if isinstance(profile, Mapping) and profile else None
    profile_ref = plan.get("render_profile") if isinstance(plan.get("render_profile"), Mapping) else {}
    if profile.get("kind") != render_profile.KIND or profile.get("schema_version") != render_profile.SCHEMA_VERSION:
        gap("release_render_profile_schema_invalid", "缺当前 canonical render_profile schema/kind",
            "生产数据/render_profile.json")
    if not profile_digest or profile.get("profile_sha256") != profile_digest:
        gap("release_render_profile_digest_invalid", "render_profile 自带 logical SHA 与内容不一致",
            "生产数据/render_profile.json")
    if int(((profile.get("summary") or {}).get("block")) or 0):
        gap("release_render_profile_blocked", "render_profile 仍含 block", "生产数据/render_profile.json")
    try:
        fresh_profile = render_profile.compile_profile(root)
    except Exception:
        fresh_profile = {}
    if not profile_digest or fresh_profile.get("profile_sha256") != profile_digest:
        gap("release_render_profile_stale", "render_profile 未绑定当前 brief/settings/platform pack 输入",
            "生产数据/render_profile.json")
    if (profile_ref.get("path") != render_profile.PROFILE_REL
            or profile_ref.get("sha256") != profile_digest):
        gap("release_delivery_profile_binding_stale", "delivery plan 未绑定当前 render_profile logical SHA",
            "合成/delivery_plan.json")
    for row in active:
        row_ref = row.get("render_profile") if isinstance(row.get("render_profile"), Mapping) else {}
        if row_ref.get("path") != render_profile.PROFILE_REL or row_ref.get("sha256") != profile_digest:
            gap("release_delivery_profile_binding_stale",
                f"交付件 {row.get('deliverable_id') or '(missing)'} 未绑定当前 render_profile",
                "合成/delivery_plan.json")

    adaptation_path = root / "生产数据" / "placement_adaptation.json"
    adaptation = load(adaptation_path, {}) or {}
    adaptation_digest = (placement_adaptation.plan_sha(adaptation)
                         if isinstance(adaptation, Mapping) and adaptation else None)
    adaptation_ref = (plan.get("placement_adaptation")
                      if isinstance(plan.get("placement_adaptation"), Mapping) else {})
    if (adaptation.get("kind") != "ad_placement_adaptation_plan"
            or adaptation.get("schema_version") != 1):
        gap("release_placement_adaptation_schema_invalid", "缺 canonical placement_adaptation schema/kind",
            "生产数据/placement_adaptation.json")
    if not adaptation_digest or adaptation.get("plan_sha256") != adaptation_digest:
        gap("release_placement_adaptation_digest_invalid", "placement_adaptation logical SHA 与内容不一致",
            "生产数据/placement_adaptation.json")
    try:
        fresh_adaptation = placement_adaptation.evaluate(root, deliverables=[{
            "deliverable_id": row.get("deliverable_id"), "kind": row.get("kind"),
            "aspect": row.get("aspect"), "duration": row.get("duration"), "label": row.get("label"),
        } for row in active])
    except Exception:
        fresh_adaptation = {}
    if not adaptation_digest or fresh_adaptation.get("plan_sha256") != adaptation_digest:
        gap("release_placement_adaptation_stale",
            "placement_adaptation 未绑定当前 brief/storyboard/platform pack 输入",
            "生产数据/placement_adaptation.json")
    if (int(((adaptation.get("summary") or {}).get("block")) or 0)
            or not bool((adaptation.get("summary") or {}).get("approved"))):
        gap("release_placement_adaptation_blocked", "placement_adaptation 未批准或仍含 block",
            "生产数据/placement_adaptation.json")
    if (adaptation_ref.get("path") != "生产数据/placement_adaptation.json"
            or adaptation_ref.get("sha256") != adaptation_digest):
        gap("release_delivery_adaptation_binding_stale",
            "delivery plan 未绑定当前 placement_adaptation logical SHA", "合成/delivery_plan.json")
    adaptation_by_id = {str(row.get("deliverable_id") or ""): row
                        for row in adaptation.get("items") or [] if isinstance(row, Mapping)}
    for row in active:
        did = str(row.get("deliverable_id") or "")
        if row.get("placement_adaptation") != adaptation_by_id.get(did):
            gap("release_delivery_adaptation_binding_stale",
                f"交付件 {did or '(missing)'} 未绑定当前 placement adaptation item",
                "合成/delivery_plan.json")

    qc_path = root / "合成" / "delivery_qc.json"
    qc = load(qc_path, {}) or {}
    qc_summary = qc.get("summary") if isinstance(qc.get("summary"), Mapping) else {}
    if qc.get("kind") != "ad_delivery_qc" or qc.get("schema_version") != 2:
        gap("release_delivery_qc_schema_invalid", "正式发布要求 kind=ad_delivery_qc/schema_version=2",
            "合成/delivery_qc.json")
    if not isinstance(qc.get("summary"), Mapping) or "block" not in qc_summary:
        gap("release_delivery_qc_summary_missing", "delivery_qc 缺机器可判定 summary.block",
            "合成/delivery_qc.json")
    elif int(qc_summary.get("block") or 0) != 0:
        gap("release_delivery_qc_blocked", "delivery_qc 仍有 block", "合成/delivery_qc.json")
    if qc.get("delivery_plan_sha256") != plan_digest:
        gap("release_delivery_qc_plan_stale", "delivery_qc 未绑定当前 canonical delivery plan",
            "合成/delivery_qc.json")
    if qc.get("render_profile_sha256") != profile_digest:
        gap("release_delivery_qc_profile_stale", "delivery_qc 未绑定当前 render_profile",
            "合成/delivery_qc.json")
    if qc.get("placement_adaptation_sha256") != adaptation_digest:
        gap("release_delivery_qc_adaptation_stale", "delivery_qc 未绑定当前 placement_adaptation",
            "合成/delivery_qc.json")
    qc_media = qc.get("media_sha256_by_deliverable") if isinstance(qc.get("media_sha256_by_deliverable"), Mapping) else {}
    for did, digest in expected_media.items():
        if not digest or qc_media.get(did) != digest:
            gap("release_delivery_qc_media_stale", f"delivery_qc 未绑定当前交付媒体 {did}",
                "合成/delivery_qc.json")
    qc_execution = (qc.get("adaptation_execution_sha256_by_deliverable")
                    if isinstance(qc.get("adaptation_execution_sha256_by_deliverable"), Mapping) else {})
    if dict(qc_execution) != expected_execution:
        gap("release_delivery_qc_execution_receipt_stale",
            "delivery_qc 未精确绑定当前 cross-ratio adaptation execution receipt 字节",
            "合成/delivery_qc.json")
    qc_items: dict[str, list[Mapping[str, Any]]] = {}
    for row in qc.get("items") or []:
        if isinstance(row, Mapping):
            qc_items.setdefault(str(row.get("deliverable_id") or ""), []).append(row)
    for did in expected_media:
        rows = qc_items.get(did) or []
        if len(rows) != 1 or not bool(rows[0].get("passed")):
            gap("release_delivery_qc_deliverable_unaccepted", f"{did} 缺唯一且 passed=true 的 QC 记录",
                "合成/delivery_qc.json")

    compose_status = dependency_graph.compose_acceptance_status(root) if require_acceptance else {
        "accepted": True, "report_valid": True, "receipts_current": True,
        "dependency_snapshot_sha256": dependency_graph.stage_snapshot_sha256(root, "compose"),
    }
    if require_acceptance and not compose_status.get("report_valid"):
        gap("release_compose_acceptance_missing_or_stale",
            "缺当前 formal/accepted compose stage acceptance，或其 dependency snapshot 已变化",
            "生产数据/stage_acceptance/compose.json")
    if require_acceptance and not compose_status.get("receipts_current"):
        gap("release_compose_receipt_missing_or_stale", "compose dependency receipt 缺失或已 stale",
            "生产数据/dependency_receipts.json")

    bindings = {
        "delivery_plan": {"path": "合成/delivery_plan.json", "sha256": plan_digest,
                          "file_sha256": sha(plan_path)},
        "delivery_qc": {"path": "合成/delivery_qc.json", "file_sha256": sha(qc_path),
                        "delivery_plan_sha256": qc.get("delivery_plan_sha256")},
        "render_profile": {"path": render_profile.PROFILE_REL, "sha256": profile_digest,
                           "file_sha256": sha(profile_path)},
        "placement_adaptation": {"path": "生产数据/placement_adaptation.json",
                                 "sha256": adaptation_digest, "file_sha256": sha(adaptation_path)},
        "media_sha256_by_deliverable": expected_media,
        "adaptation_execution_sha256_by_deliverable": expected_execution,
        "compose_acceptance": compose_status,
    }
    return {
        "required": required, "valid": not any(row["severity"] == "block" for row in findings),
        "bindings": bindings, "findings": findings,
        "summary": {"block": sum(row["severity"] == "block" for row in findings),
                    "warn": sum(row["severity"] == "warn" for row in findings)},
    }


def _creator_authorization(root: Path, row: Mapping[str, Any], context: Mapping[str, Any]):
    """Validate creator authorization for one exact placement receipt."""
    spark_mode = _norm(row.get("spark_mode"))
    required = bool(context.get("creator_involved") or spark_mode == "spark")
    if not required:
        return {"required": False, "valid": True, "spark_mode": spark_mode}, []
    findings = []
    auth = row.get("creator_authorization") if isinstance(row.get("creator_authorization"), Mapping) else {}
    evidence_sha = evidence_digest(root, auth.get("evidence_file"), auth.get("evidence_sha256"))
    authorization_id = str(auth.get("authorization_id") or auth.get("spark_authorization_id") or "").strip()
    valid = True
    if pending(context.get("account_owner")):
        findings.append(("commercial_creator_account_owner_missing",
                         "commercial_content.creator_involved=true 时必须声明 account_owner"))
        valid = False
    if context.get("creator_involved") and spark_mode not in SPARK_MODES:
        findings.append(("commercial_spark_mode_missing",
                         "创作者参与的逐 placement 收据必须声明 spark_mode=spark/non_spark"))
        valid = False
    if _norm(auth.get("status")) not in CREATOR_AUTH_COMPLETE:
        findings.append(("commercial_creator_authorization_pending",
                         "创作者参与但 creator_authorization.status 未批准"))
        valid = False
    for key in ("checked_at", "approved_by", "evidence_file"):
        if pending(auth.get(key)):
            findings.append(("commercial_creator_authorization_incomplete",
                             f"creator_authorization 缺 {key}"))
            valid = False
    if not evidence_exists(root, auth.get("evidence_file")) or evidence_sha is None:
        findings.append(("commercial_creator_authorization_evidence_invalid",
                         "创作者授权证据不存在、不可查询或未绑定 SHA"))
        valid = False
    if not valid_checked_at(auth.get("checked_at")):
        findings.append(("commercial_creator_authorization_date_invalid",
                         f"creator_authorization.checked_at 缺失、在未来或早于 {RELEASE_RECEIPT_MAX_AGE_DAYS} 天新鲜度窗口"))
        valid = False
    if spark_mode == "spark" and not authorization_id:
        findings.append(("commercial_spark_authorization_id_missing",
                         "spark 模式必须记录平台 Spark authorization ID"))
        valid = False
    return {
        **dict(auth), "required": required, "spark_mode": spark_mode,
        "authorization_id_actual": authorization_id,
        "evidence_sha256_actual": evidence_sha, "valid": valid,
    }, findings


def evidence_exists(root: Path, value: Any) -> bool:
    ref = str(value or "").strip()
    if not ref:
        return False
    if ref.startswith(("https://", "http://", "record:")):
        return True
    path = Path(ref)
    if not path.is_absolute():
        path = root / path
    return path.is_file()


def evidence_digest(root: Path, ref: Any, claimed: Any = ""):
    value = str(ref or "").strip()
    if value.startswith(("https://", "http://", "record:")):
        digest = str(claimed or "").strip().lower()
        return digest if re.fullmatch(r"[0-9a-f]{64}", digest) else None
    path = Path(value)
    if value and not path.is_absolute():
        path = root / path
    return sha(path) if value else None


def _shots(storyboard: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [row for row in (storyboard.get("shots") or storyboard.get("clips") or []) if isinstance(row, Mapping)]


def _shot_id(row: Mapping[str, Any]) -> str:
    return str(row.get("shot_id") or row.get("clip_id") or row.get("id") or "")


def _kept_shots(root: Path, item: Mapping[str, Any], storyboard: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = _shots(storyboard)
    if item.get("kind") != "cutdown":
        return rows
    duration = str(item.get("duration") or "")
    safe = "".join(ch for ch in duration if ch.isalnum()) or duration.replace(":", "x")
    candidates = [
        root / "合成" / "cutdown" / f"plan_{duration}.json",
        root / "合成" / "cutdown" / f"plan_{safe}.json",
    ]
    plan = next((load(path, {}) for path in candidates if path.is_file()), {}) or {}
    kept = {str(v) for v in plan.get("kept_shots") or []}
    return [row for row in rows if _shot_id(row) in kept] if kept else rows


def _claim_rows(brief: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw = brief.get("claims") or []
    if isinstance(raw, Mapping):
        raw = [raw]
    out = {}
    for pos, row in enumerate(raw, 1):
        if isinstance(row, Mapping):
            out[str(row.get("id") or f"claim_{pos:02d}")] = row
    return out


def _claims_for(shots: Sequence[Mapping[str, Any]], claims: Mapping[str, Mapping[str, Any]]):
    used: set[str] = set()
    disclosures: dict[str, list[dict[str, Any]]] = {}
    for shot in shots:
        raw = shot.get("claim_ids") or []
        if isinstance(raw, str):
            raw = [raw]
        used.update(str(v) for v in raw if str(v))
        rows = shot.get("disclosures") or []
        if isinstance(rows, Mapping):
            rows = [rows]
        for row in rows:
            if not isinstance(row, Mapping) or not row.get("claim_id"):
                continue
            disclosures.setdefault(str(row["claim_id"]), []).append({"shot_id": _shot_id(shot), **dict(row)})
    return [{"claim_id": cid, "claim": str((claims.get(cid) or {}).get("claim") or ""),
             "disclosures": disclosures.get(cid, [])} for cid in sorted(used)]


def _scope_tokens(value: Any) -> set[str]:
    values = value if isinstance(value, list) else [value]
    return {str(v).strip().lower() for v in values if str(v).strip()}


def _right_covers(row: Mapping[str, Any], placements: Sequence[str]) -> bool:
    if row.get("rights_status") == "not_used":
        return True
    tokens = _scope_tokens(row.get("media_scope"))
    if tokens & GLOBAL_MEDIA_SCOPE:
        return True
    for placement in placements:
        platform = placement.split(":", 1)[0].strip().lower()
        if placement.lower() not in tokens and platform not in tokens:
            return False
    return True


def _legal_receipt(root: Path, brief: Mapping[str, Any], jurisdiction: str,
                   did: str, digest: str | None):
    if jurisdiction == "中国大陆":
        law = load(root / "脚本" / "广告法机检报告.json", {}) or {}
        ok = (root / "脚本" / "广告法机检报告.json").is_file() and not law.get("disabled") and int(((law.get("summary") or {}).get("block")) or 0) == 0
        return {"mode": "ad_law_report", "approved": ok, "evidence": "脚本/广告法机检报告.json"}
    reviews = brief.get("legal_reviews") if isinstance(brief.get("legal_reviews"), list) else []
    for row in reviews:
        if not isinstance(row, Mapping):
            continue
        regions = row.get("jurisdictions") or row.get("regions") or row.get("region") or []
        if isinstance(regions, str):
            regions = [regions]
        if jurisdiction not in [str(v) for v in regions]:
            continue
        digest_map = row.get("variant_sha256_by_deliverable") if isinstance(row.get("variant_sha256_by_deliverable"), Mapping) else {}
        bound = row.get("variant_sha256") or digest_map.get(did)
        evidence_sha = evidence_digest(root, row.get("evidence_file"), row.get("evidence_sha256"))
        approved = (str(row.get("status") or "").lower() == "approved" and bound == digest and
                    not pending(row.get("approved_by")) and evidence_exists(root, row.get("evidence_file")) and
                    evidence_sha is not None)
        return {"mode": "jurisdiction_review", "approved": approved, "authority": row.get("authority") or "",
                "source": row.get("source") or "", "checked_at": row.get("checked_at") or "",
                "approved_by": row.get("approved_by") or "", "evidence": row.get("evidence_file") or "",
                "variant_sha256": bound or "", "evidence_sha256": evidence_sha}
    return {"mode": "jurisdiction_review", "approved": False}


def _label_receipts(root: Path, brief: Mapping[str, Any], did: str, digest: str | None,
                    placements: Sequence[str], uses_ai: bool):
    if not uses_ai:
        return [], []
    rows = brief.get("ai_label_receipts") if isinstance(brief.get("ai_label_receipts"), list) else []
    matched = []
    findings = []
    for placement in placements:
        platform = placement.split(":", 1)[0]
        candidates = []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            row_platform = str(row.get("platform") or "")
            row_placement = str(row.get("placement") or "")
            if str(row.get("deliverable_id") or "") != did:
                continue
            # One receipt is valid for one exact final placement.  Empty scope
            # is not a wildcard and cannot be silently reused across platforms.
            if row_placement != placement:
                continue
            if row_platform.lower() != platform.lower():
                continue
            candidates.append(row)
        if not candidates:
            findings.append({"severity": "block", "code": "ai_label_receipt_missing",
                             "msg": f"{did} / {placement} 缺逐素材 AI label receipt"})
            continue
        if len(candidates) != 1:
            findings.append({"severity": "block", "code": "ai_label_receipt_ambiguous",
                             "msg": f"{did} / {placement} 存在 {len(candidates)} 条 AI label receipt；须保留唯一当前记录"})
            continue
        row = candidates[0]
        status = str(row.get("status") or "").lower()
        required = ("label_mode", "checked_at", "approved_by", "evidence_file")
        evidence_sha = evidence_digest(root, row.get("evidence_file"), row.get("evidence_sha256"))
        valid = (status in {"completed", "not_applicable"} and row.get("asset_sha256") == digest and
                 all(not pending(row.get(key)) for key in required) and evidence_exists(root, row.get("evidence_file")) and
                 evidence_sha is not None and valid_checked_at(row.get("checked_at")))
        if status == "not_applicable" and pending(row.get("reason")):
            valid = False
        matched.append({**dict(row), "placement": placement, "evidence_sha256_actual": evidence_sha, "valid": valid})
        if not valid:
            findings.append({"severity": "block", "code": "ai_label_receipt_invalid",
                             "msg": f"{did} / {placement} AI label receipt 未完成、过期、未绑定当前媒体或证据不可查"})
    return matched, findings


def _commercial_receipts(root: Path, brief: Mapping[str, Any], did: str, digest: str | None,
                         placements: Sequence[str]):
    """Validate one commercial disclosure receipt per final placement.

    This applies to AI and non-AI ads alike.  A platform's AI label, provenance
    metadata, or an ``Ad`` badge screenshot stored only in ai_label_receipts is
    not silently reused as evidence of paid partnership/sponsorship disclosure.
    """
    rows = (brief.get("commercial_disclosure_receipts")
            if isinstance(brief.get("commercial_disclosure_receipts"), list) else [])
    context = _commercial_context(brief)
    formal_paid = _formal_paid(brief)
    matched = []
    findings = []
    for placement in placements:
        platform = placement.split(":", 1)[0]
        candidates = []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            if str(row.get("deliverable_id") or "") != did:
                continue
            row_platform = str(row.get("platform") or "")
            row_placement = str(row.get("placement") or "")
            if row_placement != placement:
                continue
            if row_platform.lower() != platform.lower():
                continue
            candidates.append(row)
        if not candidates:
            findings.append({
                "severity": "block", "code": "commercial_disclosure_receipt_missing",
                "msg": f"{did} / {placement} 缺独立 commercial/paid-partnership disclosure receipt；AI label 不能代替",
            })
            continue
        if len(candidates) != 1:
            findings.append({
                "severity": "block", "code": "commercial_disclosure_receipt_ambiguous",
                "msg": f"{did} / {placement} 存在 {len(candidates)} 条商业披露收据；须保留唯一当前记录",
            })
            continue
        row = candidates[0]
        status = str(row.get("status") or "").strip().lower()
        required = ("relationship_type", "disclosure_mode", "checked_at", "approved_by", "evidence_file")
        evidence_sha = evidence_digest(root, row.get("evidence_file"), row.get("evidence_sha256"))
        record_id = str(row.get("platform_record_id") or row.get("ad_id") or row.get("post_id")
                        or row.get("campaign_id") or "").strip()
        valid = (
            status in COMMERCIAL_COMPLETE | {"not_applicable"}
            and row.get("asset_sha256") == digest
            and all(not pending(row.get(key)) for key in required)
            and evidence_exists(root, row.get("evidence_file"))
            and evidence_sha is not None
            and valid_checked_at(row.get("checked_at"))
        )
        row_relationship = str(row.get("relationship_type") or "").strip()
        expected_relationship = str(context.get("relationship_type") or "").strip()
        creator_authorization, creator_findings = _creator_authorization(root, row, context)
        for code, msg in creator_findings:
            findings.append({"severity": "block", "code": code,
                             "msg": f"{did} / {placement} {msg}"})
        if pending(expected_relationship):
            valid = False
            findings.append({
                "severity": "block", "code": "commercial_relationship_missing",
                "msg": f"{did} / {placement} 缺 commercial_content.relationship_type 机器真值",
            })
        elif row_relationship != expected_relationship:
            valid = False
            findings.append({
                "severity": "block", "code": "commercial_relationship_mismatch",
                "msg": f"{did} / {placement} 收据关系 {row_relationship or 'missing'} != brief {expected_relationship}",
            })
        if (context.get("creator_inferred_from_relationship")
                and not context.get("creator_involved_declared")):
            valid = False
            findings.append({
                "severity": "block", "code": "commercial_creator_relationship_declaration_mismatch",
                "msg": f"{did} / {placement} relationship_type 表示创作者合作，但 creator_involved 未显式为 true",
            })
        if formal_paid and status == "not_applicable":
            valid = False
            findings.append({
                "severity": "block", "code": "commercial_disclosure_na_for_formal_paid",
                "msg": f"{did} / {placement} 是正式付费投放，商业内容披露不得标 not_applicable",
            })
        if not creator_authorization.get("valid"):
            valid = False
        if status == "completed" and not record_id:
            valid = False
        if status == "not_applicable" and pending(row.get("reason")):
            valid = False
        matched.append({
            **dict(row), "placement": placement, "platform_record_id_actual": record_id,
            "evidence_sha256_actual": evidence_sha, "commercial_content": context,
            "creator_authorization_actual": creator_authorization, "valid": valid,
        })
        if not valid:
            findings.append({
                "severity": "block", "code": "commercial_disclosure_receipt_invalid",
                "msg": f"{did} / {placement} 商业关系披露未完成/过期、未绑定当前媒体/平台记录，或证据不可查",
            })
    return matched, findings


def build(root: Path) -> dict[str, Any]:
    root = root.resolve()
    brief = load(root / "需求" / "brief.json", {}) or {}
    usage = load(root / "合规" / "ai_usage.json", {}) or {}
    plan = load(root / "合成" / "delivery_plan.json", {}) or {}
    storyboard = load(root / "脚本" / "storyboard.json", {}) or {}
    platform = platform_pack.build_pack(root)
    locale_report = locale_matrix.validate(root, delivery_plan=plan)
    producer = producer_pack.build_pack(root)
    claims = _claim_rows(brief)
    uses_ai = any(str(usage.get(key) or "").lower().startswith("ai-") for key in ("visual_mode", "video_mode"))
    findings: list[dict[str, Any]] = []
    release_chain = compose_release_chain(root, plan, require_acceptance=True)
    findings.extend(release_chain["findings"])
    if locale_report["summary"]["block"]:
        findings.append({"severity": "block", "code": "locale_matrix_block",
                         "msg": f"locale matrix 仍有 block={locale_report['summary']['block']}"})
    if producer.get("summary", {}).get("approval_blocks"):
        findings.append({"severity": "block", "code": "producer_pack_block",
                         "msg": "claim/rights producer pack 尚未批准"})
    locale_rows = locale_report.get("locales") or {}
    locale_map = locale_report.get("deliverable_locales") or {}
    platform_map = platform.get("deliverable_placements") or {}
    variants = []
    active_items = [item for item in (plan.get("deliverables") or [])
                    if isinstance(item, Mapping) and item.get("status") != "cancelled"]
    if not active_items:
        findings.append({"severity": "block", "code": "release_delivery_plan_empty",
                         "msg": "delivery plan 无未取消交付件，不能生成发布变体清单"})
    for item in active_items:
        if item.get("status") == "cancelled":
            continue
        did = str(item.get("deliverable_id") or "")
        rel = str(item.get("expected_path") or "")
        if not did:
            findings.append({"severity": "block", "code": "variant_deliverable_id_missing",
                             "msg": f"交付件缺 deliverable_id：{rel or '(path missing)'}"})
            continue
        digest = sha(root / rel) if rel else None
        placements = list(item.get("target_placements") or platform_map.get(did) or [])
        locales = list(locale_map.get(did) or [])
        if not digest:
            findings.append({"severity": "block", "code": "variant_media_missing", "msg": f"{did} 最终媒体缺失/不可哈希：{rel}"})
        if not placements:
            findings.append({"severity": "block", "code": "variant_placement_missing", "msg": f"{did} 未映射 placement"})
        if not locales:
            findings.append({"severity": "block", "code": "variant_locale_missing", "msg": f"{did} 未映射 locale"})
        selected = _kept_shots(root, item, storyboard)
        claim_rows = _claims_for(selected, claims)
        for claim in claim_rows:
            if not claim["claim"]:
                findings.append({"severity": "block", "code": "variant_claim_unknown",
                                 "msg": f"{did} 引用了 brief.claims 中不存在的 {claim['claim_id']}"})
            if not claim["disclosures"]:
                findings.append({"severity": "block", "code": "variant_claim_disclosure_missing",
                                 "msg": f"{did} claim {claim['claim_id']} 无随版本保留的 disclosure"})
        rights = []
        for right in producer.get("rights") or []:
            covered = right.get("status") == "declared" and _right_covers(right, placements)
            rights.append({"item": right.get("item"), "status": right.get("rights_status"),
                           "evidence_file": right.get("evidence_file"), "media_scope": right.get("media_scope"),
                           "covered": covered})
            if not covered:
                findings.append({"severity": "block", "code": "variant_rights_scope_gap",
                                 "msg": f"{did} 授权 {right.get('item')} 未覆盖实际 placement/media scope"})
        label_receipts, label_findings = _label_receipts(root, brief, did, digest, placements, uses_ai)
        findings.extend(label_findings)
        commercial_receipts, commercial_findings = _commercial_receipts(root, brief, did, digest, placements)
        findings.extend(commercial_findings)
        for locale in locales:
            jurisdiction_rows = list((locale_rows.get(locale) or {}).get("jurisdictions") or [])
            legal = {str(j): _legal_receipt(root, brief, str(j), did, digest) for j in jurisdiction_rows}
            for jurisdiction, receipt in legal.items():
                if not receipt.get("approved"):
                    findings.append({"severity": "block", "code": "variant_legal_review_missing",
                                     "msg": f"{did}/{locale}/{jurisdiction} 法律复核未绑定当前交付媒体 SHA"})
            variants.append({
                "variant_id": f"{did}@{locale}", "deliverable_id": did, "locale": locale,
                "path": rel, "sha256": digest, "kind": item.get("kind"), "aspect": item.get("aspect"),
                "duration": item.get("duration"), "placements": placements,
                "jurisdictions": jurisdiction_rows, "claims": claim_rows, "rights": rights,
                "legal_reviews": legal, "ai_label_receipts": label_receipts,
                "commercial_content": _commercial_context(brief),
                "commercial_disclosure_receipts": commercial_receipts,
            })
    return {
        "schema_version": SCHEMA_VERSION, "kind": KIND, "generated_at": date.today().isoformat(),
        "uses_ai": uses_ai, "delivery_plan_sha256": canonical_sha(plan),
        "delivery_plan_file_sha256": sha(root / "合成" / "delivery_plan.json"),
        "locale_matrix_sha256": sha(root / "合规" / "locale_matrix.json"),
        "platform_pack_summary": platform.get("summary") or {}, "release_chain": release_chain,
        "variants": variants,
        "findings": findings,
        "summary": {"variants": len(variants), "block": sum(f["severity"] == "block" for f in findings),
                    "warn": sum(f["severity"] == "warn" for f in findings),
                    "release_ready": not any(f["severity"] == "block" for f in findings)},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="build per-deliverable ad release variant manifest")
    ap.add_argument("project_root")
    ns = ap.parse_args(argv)
    root = Path(ns.project_root).resolve()
    payload = build(root)
    out = root / "合规" / "release_variant_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"# release variants={payload['summary']['variants']} block={payload['summary']['block']}")
    print(f"[ok] {out}")
    return 1 if payload["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
