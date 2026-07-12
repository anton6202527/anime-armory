#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the ad producer pack: a deterministic pre-production control packet.

This is the ad family's traditional-production bridge.  It does not write
creative copy or media; it gathers the client brief, concept, storyboard,
settings, deliverables, legal/rights state, and asset needs into one auditable
packet before paid image/video work starts.

Outputs:
  <root>/生产数据/producer_pack.json
  <root>/生产数据/producer_pack.md
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


PACK_KIND = "ad_producer_pack"
PENDING_TOKENS = {"", "待补", "待填写", "待定", "待确认", "tbd", "未定", "未记录", "占位"}
CLAIM_EVIDENCE_TYPES = {
    "brand_fact", "test_measurement", "statistics_survey", "scientific_literature",
    "comparison", "testimonial", "other",
}
CITED_CLAIM_TYPES = {
    "test_measurement", "statistics_survey", "scientific_literature", "comparison",
}
CLAIM_TYPE_REQUIRED = {
    "test_measurement": (
        "issuer", "issuer_qualification", "method_standard", "test_conditions", "sample",
    ),
    "statistics_survey": (
        "statistical_method", "sample_size", "sample_definition", "representativeness",
        "survey_period", "bias_limitations",
    ),
    "scientific_literature": ("publication", "publication_locator", "applicability_basis"),
    "comparison": ("comparison_target", "comparison_basis", "same_conditions"),
    "testimonial": ("endorser_authorization", "typicality_basis", "material_connection_disclosure"),
}
RIGHTS_STATUSES = {"not_used", "owned", "licensed", "public_domain", "client_supplied"}
PROD_RE = re.compile(r"\bPROD_[A-Za-z0-9_]*\b")
BRAND_RE = re.compile(r"\bBRAND_[A-Za-z0-9_]*\b")
CHAR_RE = re.compile(r"\bCHAR[_A-Za-z0-9]*\b")
LOC_RE = re.compile(r"\bLOC[_A-Za-z0-9]*\b")
CITED_SIGNAL_RE = re.compile(r"(?:\d|%|％|实验|测试|调查|统计|研究|对比|提升|降低)")


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def pending(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        text = value.strip().lower()
        return text in PENDING_TOKENS or any(token and token in text for token in PENDING_TOKENS)
    if isinstance(value, (list, tuple, set)):
        return not value or any(pending(v) for v in value)
    if isinstance(value, Mapping):
        return not value or any(pending(v) for v in value.values())
    return False


def parse_settings(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in read_text(path).splitlines():
        m = re.match(r"\s*([^#\n:：|]+?)\s*[:：]\s*(.+?)\s*$", line)
        if m:
            key = re.sub(r"^[-*]\s*", "", m.group(1).strip())
            out[key] = m.group(2).split("#", 1)[0].strip().strip("`")
    return out


def shots(storyboard: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    raw = storyboard.get("shots") or storyboard.get("clips") or []
    return [s for s in raw if isinstance(s, Mapping)]


def shot_id(shot: Mapping[str, Any], index: int) -> str:
    raw = str(shot.get("shot_id") or shot.get("clip_id") or shot.get("id") or shot.get("clip") or "").strip()
    m = re.search(r"(\d+)", raw)
    if m:
        return f"镜头{int(m.group(1)):02d}"
    if raw:
        return raw
    return f"镜头{index:02d}"


def shot_text(shot: Mapping[str, Any]) -> str:
    parts: List[str] = []
    for key in ("scene", "shot", "frame", "prompt", "description", "desc", "camera", "product_lock"):
        value = shot.get(key)
        if isinstance(value, str):
            parts.append(value)
    return " ".join(parts)


def asset_ids_from_shot(shot: Mapping[str, Any]) -> Dict[str, List[str]]:
    assets = shot.get("assets")
    found: Dict[str, set[str]] = {"brand": set(), "product": set(), "character": set(), "location": set()}
    if isinstance(assets, Mapping):
        for key, value in assets.items():
            if not value:
                continue
            text = str(key)
            if text.startswith("BRAND_"):
                found["brand"].add(text)
            elif text.startswith("PROD_"):
                found["product"].add(text)
            elif text.startswith("CHAR_"):
                found["character"].add(text)
            elif text.startswith("LOC_"):
                found["location"].add(text)
    elif isinstance(assets, Sequence) and not isinstance(assets, (str, bytes)):
        for value in assets:
            text = str(value)
            if text.startswith("BRAND_"):
                found["brand"].add(text)
            elif text.startswith("PROD_"):
                found["product"].add(text)
            elif text.startswith("CHAR_"):
                found["character"].add(text)
            elif text.startswith("LOC_"):
                found["location"].add(text)
    text = shot_text(shot)
    found["brand"].update(BRAND_RE.findall(text))
    found["product"].update(PROD_RE.findall(text))
    found["character"].update(CHAR_RE.findall(text))
    found["location"].update(LOC_RE.findall(text))
    return {k: sorted(v) for k, v in found.items()}


def build_shot_list(storyboard: Mapping[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for idx, shot in enumerate(shots(storyboard), start=1):
        continuity = shot.get("continuity") if isinstance(shot.get("continuity"), Mapping) else {}
        out.append({
            "id": shot_id(shot, idx),
            "duration": shot.get("duration") or shot.get("duration_sec") or shot.get("时长") or 0,
            "scene": shot.get("scene") or shot.get("场景") or "",
            "camera": shot.get("shot") or shot.get("camera") or shot.get("frame") or "",
            "asset_ids": asset_ids_from_shot(shot),
            "product_lock": shot.get("product_lock") or "",
            "needs_end_frame": bool(shot.get("need_end_frame") or shot.get("end_frame") or continuity.get("need_end_frame")),
            "safe_area": shot.get("safe_area") or shot.get("安全区") or {},
        })
    return out


def deliverables_from_brief(brief: Mapping[str, Any], settings: Mapping[str, str]) -> Dict[str, Any]:
    deliverables = brief.get("deliverables") if isinstance(brief.get("deliverables"), Mapping) else {}
    return {
        "master_duration": deliverables.get("master_duration") or settings.get("主片时长") or "30s",
        "aspect": deliverables.get("aspect") or settings.get("交付比例") or "未定",
        "cutdowns": deliverables.get("cutdowns") or [],
        "platforms": brief.get("platforms") or [settings.get("目标平台") or "未定"],
        "release_region": settings.get("发行地区") or "未定",
        "delivery_spec": settings.get("交付规格") or "平台默认",
    }


def rights_check(brief: Mapping[str, Any], root: Optional[Path] = None) -> List[Dict[str, Any]]:
    rights = brief.get("rights") if isinstance(brief.get("rights"), Mapping) else {}
    out: List[Dict[str, Any]] = []
    for key in ("talent", "music", "fonts", "assets"):
        raw = rights.get(key)
        entries = raw if isinstance(raw, list) else [raw]
        if not entries or entries == [None]:
            entries = [{}]
        for pos, value in enumerate(entries, 1):
            item = key if len(entries) == 1 else f"{key}_{pos:02d}"
            if not isinstance(value, Mapping):
                out.append({"item": item, "category": key, "status": "pending", "detail": value or "",
                            "rights_status": "", "missing_fields": ["structured_rights_record"]})
                continue
            rights_status = str(value.get("status") or "").strip().lower()
            evidence_file = value.get("evidence_file") or value.get("license_file") or value.get("source") or ""
            required = ["status", "territory", "media_scope", "approved_by"]
            values = {
                "status": rights_status if rights_status in RIGHTS_STATUSES else "",
                "territory": value.get("territory"), "media_scope": value.get("media_scope"),
                "approved_by": value.get("approved_by"),
            }
            if rights_status != "not_used":
                required.extend(("evidence_file", "validity"))
                values["evidence_file"] = evidence_file
                values["validity"] = value.get("validity") or value.get("valid_until")
            if rights_status == "licensed":
                required.extend(("valid_from", "valid_until"))
                values["valid_from"] = value.get("valid_from")
                values["valid_until"] = value.get("valid_until")
            missing_fields = [field for field in required if pending(values.get(field))]
            if rights_status == "licensed" and not any(field in missing_fields for field in ("valid_from", "valid_until")):
                try:
                    valid_from = date.fromisoformat(str(value.get("valid_from")))
                    valid_until = date.fromisoformat(str(value.get("valid_until")))
                    if valid_from > date.today():
                        missing_fields.append("license_not_yet_valid")
                    if valid_until < date.today():
                        missing_fields.append("license_expired")
                    if valid_until < valid_from:
                        missing_fields.append("license_date_range_invalid")
                except ValueError:
                    missing_fields.append("license_dates_valid")
            evidence_valid = True if rights_status == "not_used" else _queryable(root, evidence_file)
            if evidence_file and not evidence_valid:
                missing_fields.append("evidence_file_exists")
            missing_fields = sorted(set(missing_fields))
            out.append({
                "item": item, "category": key, "status": "declared" if not missing_fields else "pending",
                "rights_status": rights_status, "detail": value.get("detail") or value.get("description") or "",
                "evidence_file": evidence_file, "evidence_file_exists": evidence_valid,
                "territory": value.get("territory") or "", "media_scope": value.get("media_scope") or "",
                "validity": value.get("validity") or value.get("valid_until") or "",
                "valid_from": value.get("valid_from") or "", "valid_until": value.get("valid_until") or "",
                "approved_by": value.get("approved_by") or "", "missing_fields": missing_fields,
            })
    return out


def _claim_value(claim: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in claim and not pending(claim.get(key)):
            return claim.get(key)
    return ""


def _queryable(root: Optional[Path], value: Any) -> bool:
    ref = str(value or "").strip()
    if not ref:
        return False
    if ref.startswith(("https://", "http://", "doi:", "record:")):
        return True
    if root is None:
        return True
    path = Path(ref)
    if not path.is_absolute():
        path = root / path
    return path.is_file()


def claims_check(brief: Mapping[str, Any], root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Normalize and validate claim substantiation.

    `evidence_type` drives conditional evidence.  Numeric/test/statistical cited
    content receives the 2026 SAMR fields; brand facts do not inherit irrelevant
    survey fields.  House structure is stricter than keyword screening but does
    not claim that its field names are statutory wording.
    """
    out: List[Dict[str, Any]] = []
    claims = brief.get("claims") or []
    if isinstance(claims, Mapping):
        claims = [claims]
    for idx, claim in enumerate(claims, start=1):
        if isinstance(claim, Mapping):
            claim_id = str(claim.get("id") or f"claim_{idx:02d}").strip()
            text = str(claim.get("claim") or "").strip()
            evidence_type = str(claim.get("evidence_type") or "").strip().lower()
            evidence = _claim_value(claim, "evidence", "reasonable_basis")
            evidence_file = _claim_value(claim, "evidence_file", "basis_file")
            source_name = _claim_value(claim, "source_name", "issuer_name")
            source_locator = _claim_value(claim, "source_locator", "source_url", "source", "evidence_file", "basis_file")
            method = _claim_value(claim, "method")
            sample = _claim_value(claim, "sample")
            evidence_date = _claim_value(claim, "date", "evidence_date")
            territory = _claim_value(claim, "territory")
            approved_by = _claim_value(claim, "approved_by", "legal_owner")
            applicable_scope = _claim_value(claim, "applicable_scope", "scope")
            validity = _claim_value(claim, "validity", "validity_period", "valid_until")
            display_disclosure = _claim_value(claim, "display_disclosure", "disclosure_text")
            citation_used = bool(claim.get("citation_used") or evidence_type in CITED_CLAIM_TYPES)
        else:
            claim_id = f"claim_{idx:02d}"
            text = str(claim).strip()
            evidence_type = ""
            evidence = evidence_file = source_name = source_locator = method = sample = ""
            evidence_date = territory = approved_by = applicable_scope = validity = display_disclosure = ""
            citation_used = False
            claim = {}
        required = ["claim", "evidence_type", "evidence", "evidence_file", "method",
                    "evidence_date", "territory", "approved_by"]
        values = {
            "claim": text, "evidence_type": evidence_type, "evidence": evidence,
            "evidence_file": evidence_file, "method": method, "evidence_date": evidence_date,
            "territory": territory, "approved_by": approved_by,
        }
        if evidence_type not in CLAIM_EVIDENCE_TYPES:
            values["evidence_type"] = ""
        if citation_used:
            required.extend(("source_name", "source_locator", "applicable_scope", "validity", "display_disclosure"))
            values.update({
                "source_name": source_name, "source_locator": source_locator,
                "applicable_scope": applicable_scope, "validity": validity,
                "display_disclosure": display_disclosure,
            })
        conditional = CLAIM_TYPE_REQUIRED.get(evidence_type, ())
        for key in conditional:
            required.append(key)
            values[key] = _claim_value(claim, key) if isinstance(claim, Mapping) else ""
        missing_fields = [key for key in required if pending(values.get(key))]
        source_queryable = _queryable(root, source_locator) if citation_used else True
        evidence_file_exists = _queryable(root, evidence_file)
        if root is not None and evidence_file and not evidence_file_exists:
            missing_fields.append("evidence_file_exists")
        if citation_used and source_locator and not source_queryable:
            missing_fields.append("source_queryable")
        missing_fields = list(dict.fromkeys(missing_fields))
        evidence_complete = not missing_fields
        classification_warning = ""
        if evidence_type == "brand_fact" and CITED_SIGNAL_RE.search(text):
            classification_warning = "文案含数字/测试/比较信号却标为 brand_fact；仅作启发式提醒，请确认是否应改为检测/统计/比较证据类型"
        out.append({
            "id": claim_id,
            "claim": text,
            "status": "approved" if evidence_complete else "pending",
            "evidence_status": "approved" if evidence_complete else "pending",
            "evidence_type": evidence_type,
            "evidence": evidence or "",
            "evidence_file": evidence_file or "",
            "evidence_file_exists": evidence_file_exists,
            "citation_used": citation_used,
            "source_name": source_name or "",
            "source_locator": source_locator or "",
            "source_queryable": source_queryable,
            "method": method or "",
            "sample": sample or "",
            "evidence_date": evidence_date or "",
            "territory": territory or "",
            "approved_by": approved_by or "",
            "applicable_scope": applicable_scope or "",
            "validity": validity or "",
            "display_disclosure": display_disclosure or "",
            "conditional_evidence": {key: values.get(key) or "" for key in conditional},
            "missing_fields": missing_fields,
            "classification_warning": classification_warning,
        })
    return out


def legal_check(brief: Mapping[str, Any]) -> List[Dict[str, Any]]:
    mandatories = brief.get("mandatories") if isinstance(brief.get("mandatories"), Mapping) else {}
    lines = mandatories.get("legal_lines") if isinstance(mandatories, Mapping) else []
    status = "pending" if pending(lines) else "declared"
    return [{"item": "mandatories.legal_lines", "status": status, "detail": lines or []}]


def asset_gap_list(shot_list: Sequence[Mapping[str, Any]], brief: Mapping[str, Any]) -> List[Dict[str, Any]]:
    has_product = any(row.get("asset_ids", {}).get("product") for row in shot_list)
    has_brand = any(row.get("asset_ids", {}).get("brand") for row in shot_list)
    gaps: List[Dict[str, Any]] = []
    if not has_product:
        gaps.append({
            "severity": "block",
            "code": "missing_product_asset_binding",
            "msg": "storyboard 未绑定任何 PROD_*；产品/界面广告进入出图前必须结构化绑定 hero product。",
        })
    if not has_brand:
        gaps.append({
            "severity": "warn",
            "code": "missing_brand_asset_binding",
            "msg": "storyboard 未绑定 BRAND_*；建议把品牌/logo/end card 作为结构化资产锁定。",
        })
    brand = str(brief.get("brand") or "").strip()
    product = str(brief.get("product") or "").strip()
    if brand and product and has_product:
        gaps.append({
            "severity": "info",
            "code": "product_asset_present",
            "msg": "已检测到产品资产绑定，后续 ad-image/product_qc 可消费。",
        })
    return gaps


def approval_checklist(brief: Mapping[str, Any], shot_list: Sequence[Mapping[str, Any]],
                       root: Optional[Path] = None) -> List[Dict[str, Any]]:
    checks = []
    for row in rights_check(brief, root) + claims_check(brief, root) + legal_check(brief):
        if row.get("status") == "pending":
            missing = row.get("missing_fields") or []
            checks.append({
                "severity": "block", "code": f"approval_pending_{row.get('item') or row.get('id')}",
                "msg": ("claim 依据缺 " + ", ".join(missing)) if missing else "审批项仍为 pending",
                "item": row,
            })
        elif row.get("classification_warning"):
            checks.append({"severity": "warn", "code": f"claim_type_review_{row.get('id')}",
                           "msg": row["classification_warning"], "item": row})
    if not shot_list:
        checks.append({"severity": "block", "code": "shot_list_missing", "msg": "缺 storyboard 镜头清单。"})
    return checks


def build_pack(root: Path) -> Dict[str, Any]:
    root = root.resolve()
    brief = load_json(root / "需求" / "brief.json", {}) or {}
    storyboard = load_json(root / "脚本" / "storyboard.json", {}) or {}
    settings = parse_settings(root / "_设置.md")
    concept = read_text(root / "创意" / "concept.md")
    shot_list = build_shot_list(storyboard)
    pack = {
        "schema_version": 2,
        "kind": PACK_KIND,
        "project_root": str(root),
        "brand": brief.get("brand") or "",
        "product": brief.get("product") or "",
        "key_message": brief.get("key_message") or "",
        "audience": brief.get("audience") or "",
        "tone": brief.get("tone") or "",
        "big_idea": _extract_section(concept, "Big Idea"),
        "deliverables": deliverables_from_brief(brief, settings),
        "rights": rights_check(brief, root),
        "claims": claims_check(brief, root),
        "legal": legal_check(brief),
        "shot_list": shot_list,
        "asset_gaps": asset_gap_list(shot_list, brief),
        "approval_checklist": [],
    }
    pack["approval_checklist"] = approval_checklist(brief, shot_list, root) + [
        gap for gap in pack["asset_gaps"] if gap.get("severity") == "block"
    ]
    pack["summary"] = {
        "shots": len(shot_list),
        "approval_blocks": sum(1 for row in pack["approval_checklist"] if row.get("severity") == "block"),
        "approval_warns": sum(1 for row in pack["approval_checklist"] if row.get("severity") == "warn"),
        "asset_blocks": sum(1 for row in pack["asset_gaps"] if row.get("severity") == "block"),
        "asset_warns": sum(1 for row in pack["asset_gaps"] if row.get("severity") == "warn"),
    }
    return pack


def _extract_section(markdown: str, title: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(title)}\s*$", re.M)
    m = pattern.search(markdown or "")
    if not m:
        return ""
    start = m.end()
    next_header = re.search(r"^##\s+", markdown[start:], re.M)
    end = start + next_header.start() if next_header else len(markdown)
    return markdown[start:end].strip()


def write_markdown(path: Path, pack: Mapping[str, Any]) -> None:
    lines = [
        "# ad producer pack",
        "",
        f"- 品牌: {pack.get('brand') or '未填'}",
        f"- 产品: {pack.get('product') or '未填'}",
        f"- 镜头数: {pack.get('summary', {}).get('shots', 0)}",
        f"- 审批阻断: {pack.get('summary', {}).get('approval_blocks', 0)}",
        "",
        "## Deliverables",
    ]
    deliverables = pack.get("deliverables") or {}
    for key in ("master_duration", "aspect", "cutdowns", "platforms", "release_region", "delivery_spec"):
        lines.append(f"- {key}: {deliverables.get(key)}")
    lines.extend(["", "## Asset Gaps"])
    for row in pack.get("asset_gaps") or []:
        lines.append(f"- {row.get('severity','info').upper()} [{row.get('code')}] {row.get('msg')}")
    lines.extend(["", "## Shot List"])
    for row in pack.get("shot_list") or []:
        assets = row.get("asset_ids") or {}
        flat_assets = ", ".join(v for values in assets.values() for v in values) or "-"
        lines.append(f"- {row.get('id')}: {row.get('duration')}s | {row.get('scene')} | assets: {flat_assets}")
    lines.extend(["", "## Approval Checklist"])
    for row in pack.get("approval_checklist") or []:
        lines.append(f"- {row.get('severity','block').upper()} [{row.get('code')}] {row.get('msg') or row.get('item')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_pack(root: Path, out_json: Optional[Path] = None) -> Dict[str, Any]:
    pack = build_pack(root)
    out_json = out_json or (root / "生产数据" / "producer_pack.json")
    out_md = out_json.with_suffix(".md")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(out_md, pack)
    pack["_json_path"] = str(out_json)
    pack["_md_path"] = str(out_md)
    return pack


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="build ad producer pack")
    ap.add_argument("project_root")
    ap.add_argument("--json", default=None, help="输出 producer_pack.json 路径")
    args = ap.parse_args(argv)
    pack = write_pack(Path(args.project_root), Path(args.json) if args.json else None)
    summary = pack.get("summary") or {}
    print(
        "# producer_pack "
        f"shots={summary.get('shots', 0)} "
        f"approval_blocks={summary.get('approval_blocks', 0)} "
        f"asset_blocks={summary.get('asset_blocks', 0)}"
    )
    print(f"[ok] {pack['_json_path']}")
    return 1 if summary.get("approval_blocks", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
