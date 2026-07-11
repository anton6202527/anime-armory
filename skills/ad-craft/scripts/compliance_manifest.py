#!/usr/bin/env python3
"""Build release-facing AI/rights/platform declaration evidence for an ad."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import platform_pack


PENDING = {"", "待补", "未记录", "未定", "tbd", "pending"}


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def pending(value) -> bool:
    return str(value or "").strip().lower() in PENDING


def build(root: Path, declaration_status="pending", declaration_evidence="",
          explicit_label_status="platform_managed", metadata_status="preserve"):
    root = root.resolve()
    usage = load(root / "合规" / "ai_usage.json", {}) or {}
    brief = load(root / "需求" / "brief.json", {}) or {}
    platforms = brief.get("platforms") or []
    if isinstance(platforms, str):
        platforms = [platforms]
    uses_ai = any(str(usage.get(k) or "").lower().startswith("ai-") for k in ("visual_mode", "video_mode"))
    findings = []
    delivery_pack = platform_pack.build_pack(root)
    if not usage:
        findings.append({"severity": "block", "code": "ai_usage_missing", "msg": "缺 ai_usage.json"})
    if uses_ai and pending(declaration_status):
        findings.append({"severity": "block", "code": "platform_declaration_pending",
                         "msg": "AI 广告尚无平台主动声明完成证据；母版可完成，但不可标记发布就绪"})
    if uses_ai and declaration_status == "completed" and pending(declaration_evidence):
        findings.append({"severity": "block", "code": "platform_declaration_evidence_missing",
                         "msg": "声明标记 completed 但缺截图/回执/记录路径"})
    if uses_ai and explicit_label_status == "pending":
        findings.append({"severity": "block", "code": "explicit_label_pending",
                         "msg": "显式标识责任仍为 pending；需确认由生成服务、传播平台或发布方落实"})
    if uses_ai and metadata_status == "stripped":
        findings.append({"severity": "block", "code": "metadata_stripped",
                         "msg": "成片流程声明已剥离生成合成元数据；发布前不得继续流转"})
    for item in delivery_pack.get("findings") or []:
        if item.get("code") in {"platforms_missing", "platform_spec_missing", "safe_zone_asset_pending"}:
            findings.append({"severity": "block", "code": f"release_{item.get('code')}",
                             "msg": str(item.get("msg") or "平台交付规格未闭合")})
    payload = {
        "schema_version": 1,
        "kind": "ad_compliance_manifest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platforms": platforms,
        "release_regions": brief.get("release_regions") or brief.get("release_region") or [],
        "uses_ai": uses_ai,
        "ai_usage_path": "合规/ai_usage.json",
        "platform_declaration": {"status": declaration_status, "evidence": declaration_evidence},
        "explicit_label": {"status": explicit_label_status},
        "metadata": {"status": metadata_status},
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
    ns = ap.parse_args(argv)
    root = Path(ns.project_root)
    payload = build(root, ns.declaration_status, ns.declaration_evidence,
                    ns.explicit_label_status, ns.metadata_status)
    out = root / "合规" / "compliance_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"# compliance manifest block={payload['summary']['block']} release_ready={payload['summary']['release_ready']}")
    print(f"[ok] {out}")
    return 1 if payload["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
