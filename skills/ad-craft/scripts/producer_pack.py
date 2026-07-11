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
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


PACK_KIND = "ad_producer_pack"
PENDING_TOKENS = {"", "待补", "待填写", "待定", "待确认", "tbd", "未定", "未记录", "占位"}
PROD_RE = re.compile(r"\bPROD_[A-Za-z0-9_]*\b")
BRAND_RE = re.compile(r"\bBRAND_[A-Za-z0-9_]*\b")
CHAR_RE = re.compile(r"\bCHAR[_A-Za-z0-9]*\b")
LOC_RE = re.compile(r"\bLOC[_A-Za-z0-9]*\b")


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


def rights_check(brief: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rights = brief.get("rights") if isinstance(brief.get("rights"), Mapping) else {}
    out: List[Dict[str, Any]] = []
    for key in ("talent", "music", "fonts", "assets"):
        value = rights.get(key)
        out.append({
            "item": key,
            "status": "pending" if pending(value) else "declared",
            "detail": value or "",
        })
    return out


def claims_check(brief: Mapping[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    claims = brief.get("claims") or []
    if isinstance(claims, Mapping):
        claims = [claims]
    for idx, claim in enumerate(claims, start=1):
        if isinstance(claim, Mapping):
            text = str(claim.get("claim") or "").strip()
            evidence = claim.get("evidence")
            evidence_file = claim.get("evidence_file") or claim.get("source")
            method = claim.get("method")
            sample = claim.get("sample")
            evidence_date = claim.get("date") or claim.get("evidence_date")
            territory = claim.get("territory")
            approved_by = claim.get("approved_by") or claim.get("legal_owner")
        else:
            text = str(claim).strip()
            evidence = ""
            evidence_file = method = sample = evidence_date = territory = approved_by = ""
        evidence_complete = all(not pending(v) for v in (
            evidence, evidence_file, method, evidence_date, territory, approved_by
        ))
        out.append({
            "id": f"claim_{idx:02d}",
            "claim": text,
            "status": "approved" if evidence_complete else "pending",
            "evidence_status": "approved" if evidence_complete else "pending",
            "evidence": evidence or "",
            "evidence_file": evidence_file or "",
            "method": method or "",
            "sample": sample or "",
            "evidence_date": evidence_date or "",
            "territory": territory or "",
            "approved_by": approved_by or "",
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


def approval_checklist(brief: Mapping[str, Any], shot_list: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    checks = []
    for row in rights_check(brief) + claims_check(brief) + legal_check(brief):
        if row.get("status") == "pending":
            checks.append({"severity": "block", "code": f"approval_pending_{row.get('item') or row.get('id')}", "item": row})
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
        "schema_version": 1,
        "kind": PACK_KIND,
        "project_root": str(root),
        "brand": brief.get("brand") or "",
        "product": brief.get("product") or "",
        "key_message": brief.get("key_message") or "",
        "audience": brief.get("audience") or "",
        "tone": brief.get("tone") or "",
        "big_idea": _extract_section(concept, "Big Idea"),
        "deliverables": deliverables_from_brief(brief, settings),
        "rights": rights_check(brief),
        "claims": claims_check(brief),
        "legal": legal_check(brief),
        "shot_list": shot_list,
        "asset_gaps": asset_gap_list(shot_list, brief),
        "approval_checklist": [],
    }
    pack["approval_checklist"] = approval_checklist(brief, shot_list) + [
        gap for gap in pack["asset_gaps"] if gap.get("severity") == "block"
    ]
    pack["summary"] = {
        "shots": len(shot_list),
        "approval_blocks": sum(1 for row in pack["approval_checklist"] if row.get("severity") == "block"),
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
