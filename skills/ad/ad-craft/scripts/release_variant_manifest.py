#!/usr/bin/env python3
"""Bind every final ad variant to placement, locale, law, rights and AI labels."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

import locale_matrix
import platform_pack
import producer_pack


KIND = "ad_release_variant_manifest"
SCHEMA_VERSION = 1
PENDING = {"", "待补", "未定", "未记录", "tbd", "pending"}
GLOBAL_MEDIA_SCOPE = {"all", "all media", "all_media", "全媒体", "数字媒体", "digital", "digital paid media", "paid_social"}


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


def pending(value: Any) -> bool:
    return str(value or "").strip().lower() in PENDING


def valid_checked_at(value: Any):
    try:
        return date.fromisoformat(str(value)[:10]) <= date.today()
    except ValueError:
        return False


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
            if row_placement and row_placement != placement:
                continue
            if row_platform and row_platform.lower() not in {platform.lower(), placement.lower()}:
                continue
            candidates.append(row)
        if not candidates:
            findings.append({"severity": "block", "code": "ai_label_receipt_missing",
                             "msg": f"{did} / {placement} 缺逐素材 AI label receipt"})
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
                             "msg": f"{did} / {placement} AI label receipt 未完成、未绑定当前媒体或证据不可查"})
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
            })
    return {
        "schema_version": SCHEMA_VERSION, "kind": KIND, "generated_at": date.today().isoformat(),
        "uses_ai": uses_ai, "delivery_plan_sha256": sha(root / "合成" / "delivery_plan.json"),
        "locale_matrix_sha256": sha(root / "合规" / "locale_matrix.json"),
        "platform_pack_summary": platform.get("summary") or {}, "variants": variants,
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
