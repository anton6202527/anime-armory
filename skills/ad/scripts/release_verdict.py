#!/usr/bin/env python3
"""Build the single SHA-bound final completion verdict for one ad release."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = 1
KIND = "ad_release_verdict"
OUT_REL = Path("生产数据") / "release_verdict.json"
AUTOMATED_REVIEWER_RE = re.compile(
    r"(?:^|[^a-z0-9])(agent|ai|assistant|automation|bot|chatgpt|claude|codex|delegate|listener|"
    r"machine|model|producer|supervisor|system)(?:[^a-z0-9]|$)|"
    r"^(?:代理|制作代理|自动化|机器人|模型|系统|系统代理|执行器)(?:$|[:：/#@])", re.I
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def logical_manifest_sha(value: Mapping[str, Any]) -> str:
    return canonical_sha256({key: child for key, child in value.items() if key != "generated_at" and not str(key).startswith("_")})


def is_human_reviewer(value: Any) -> bool:
    name = str(value or "").strip()
    return bool(name) and not AUTOMATED_REVIEWER_RE.search(name)


def atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if tmp.exists():
            tmp.unlink()


def build_verdict(root: Path) -> dict[str, Any]:
    root = root.resolve()
    variant_path = root / "合规" / "release_variant_manifest.json"
    compliance_path = root / "合规" / "compliance_manifest.json"
    signoff_path = root / "合规" / "human_signoff.json"
    plan_path = root / "合成" / "delivery_plan.json"
    variant = load_json(variant_path, {}) or {}
    compliance = load_json(compliance_path, {}) or {}
    signoff = load_json(signoff_path, {}) or {}
    plan = load_json(plan_path, {}) or {}
    blockers: list[dict[str, str]] = []

    if not variant_path.is_file() or not bool((variant.get("summary") or {}).get("release_ready")):
        blockers.append({"code": "release_variants_not_ready", "message": "当前 release_variant_manifest 未 release-ready"})
    if not compliance_path.is_file() or not bool((compliance.get("summary") or {}).get("release_ready")):
        blockers.append({"code": "compliance_not_ready", "message": "当前 compliance_manifest 未 release-ready"})
    variant_logical = logical_manifest_sha(variant) if isinstance(variant, Mapping) else ""
    if compliance.get("release_variant_manifest_sha256") != variant_logical:
        blockers.append({"code": "compliance_variant_stale", "message": "compliance 未绑定当前 release variant 逻辑摘要"})

    media: dict[str, dict[str, Any]] = {}
    for row in plan.get("deliverables") or []:
        if not isinstance(row, Mapping) or row.get("status") == "cancelled":
            continue
        did = str(row.get("deliverable_id") or "").strip()
        rel = str(row.get("expected_path") or "").strip()
        if not did or not rel:
            blockers.append({"code": "deliverable_contract_missing", "message": "delivery_plan 含缺 ID/path 的未取消交付件"})
            continue
        media[did] = {"path": rel, "sha256": sha256_file(root / rel)}
        if not media[did]["sha256"]:
            blockers.append({"code": "deliverable_media_missing", "message": f"缺当前交付媒体：{did} -> {rel}"})
    if not media:
        blockers.append({"code": "deliverables_missing", "message": "没有可验收的未取消交付件"})

    variants_by_id: dict[str, set[str]] = {}
    for row in variant.get("variants") or []:
        if isinstance(row, Mapping) and row.get("deliverable_id"):
            variants_by_id.setdefault(str(row["deliverable_id"]), set()).add(str(row.get("sha256") or ""))
    for did, current in media.items():
        if current.get("sha256") not in variants_by_id.get(did, set()):
            blockers.append({"code": "release_variant_media_stale", "message": f"release variant 未绑定当前媒体：{did}"})

    reviewer = str(signoff.get("reviewer") or "").strip()
    if not signoff_path.is_file() or not bool((signoff.get("summary") or {}).get("approved")):
        blockers.append({"code": "human_signoff_not_approved", "message": "最终 human_signoff 未批准"})
    if not is_human_reviewer(reviewer):
        blockers.append({"code": "human_signoff_not_human", "message": "最终 human_signoff 缺真实具名人"})
    signed = signoff.get("source_sha256") if isinstance(signoff.get("source_sha256"), Mapping) else {}
    if signed.get("release_variants") != sha256_file(variant_path):
        blockers.append({"code": "human_signoff_variant_stale", "message": "human_signoff 未绑定当前 release variant 文件"})
    if signed.get("compliance_manifest") != sha256_file(compliance_path):
        blockers.append({"code": "human_signoff_compliance_stale", "message": "human_signoff 未绑定当前 compliance 文件"})
    signed_media = signed.get("deliverables") if isinstance(signed.get("deliverables"), Mapping) else {}
    if dict(signed_media) != {did: row.get("sha256") for did, row in media.items()}:
        blockers.append({"code": "human_signoff_media_stale", "message": "human_signoff 未绑定当前全部交付媒体"})

    inputs = {
        "release_variant_manifest": {"path": "合规/release_variant_manifest.json", "sha256": sha256_file(variant_path)},
        "compliance_manifest": {"path": "合规/compliance_manifest.json", "sha256": sha256_file(compliance_path)},
        "human_signoff": {"path": "合规/human_signoff.json", "sha256": sha256_file(signoff_path)},
        "delivery_plan": {"path": "合成/delivery_plan.json", "sha256": sha256_file(plan_path)},
        "media": media,
    }
    release_digest = canonical_sha256({"schema_version": SCHEMA_VERSION, "inputs": inputs})
    complete = not blockers
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "generated_at": now_iso(),
        "project_root": str(root),
        "release_digest": release_digest,
        "status": "complete" if complete else "blocked",
        "complete": complete,
        "component_release_ready": {
            "release_variants": bool((variant.get("summary") or {}).get("release_ready")),
            "compliance": bool((compliance.get("summary") or {}).get("release_ready")),
        },
        "final_human_signoff": {"reviewer": reviewer, "current": not any(row["code"].startswith("human_signoff") for row in blockers)},
        "inputs": inputs,
        "blockers": blockers,
    }


def write_verdict(root: Path, verdict: Mapping[str, Any]) -> Path:
    out = root.resolve() / OUT_REL
    atomic_json(out, verdict)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="ad single SHA-bound release verdict")
    ap.add_argument("project_root")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.project_root).resolve()
    verdict = build_verdict(root)
    if ns.write:
        write_verdict(root, verdict)
    if ns.json:
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
    else:
        print(f"# ad release status={verdict['status']} complete={verdict['complete']} digest={verdict['release_digest']}")
        for row in verdict["blockers"]:
            print(f"- BLOCK [{row['code']}] {row['message']}")
    return 0 if verdict["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
