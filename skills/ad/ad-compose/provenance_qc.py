#!/usr/bin/env python3
"""Verify machine-readable AI provenance on final ad deliverables.

The report probes the actual file with c2patool when available and inspects
container metadata with ffprobe.  A bare metadata_status string is never proof.
When local tooling is unavailable, a per-asset external probe receipt may close
the gap only if it binds the current file SHA and a queryable probe output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path
from typing import Any, Mapping


KIND = "ad_provenance_qc"
SCHEMA_VERSION = 2
MARKER = re.compile(r"c2pa|content.?credential|contentauth|ai.?generated|generated.?ai|synthetic|aigc", re.I)
PROVIDER_KEY = re.compile(r"service.?provider|provider|platform.?name|platform.?code", re.I)
CONTENT_ID_KEY = re.compile(r"content.?id|asset.?id|instance.?id", re.I)
AI_SOURCE = re.compile(r"trainedalgorithmicmedia|compositesynthetic|algorithmicmedia|generative.?ai|ai.?generated|aigc", re.I)


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


def evidence_exists(root: Path, value: Any):
    ref = str(value or "").strip()
    if not ref:
        return False
    if ref.startswith(("https://", "http://", "record:")):
        return True
    path = Path(ref)
    if not path.is_absolute():
        path = root / path
    return path.is_file()


def valid_checked_at(value: Any):
    try:
        return date.fromisoformat(str(value)[:10]) <= date.today()
    except ValueError:
        return False


def ffprobe_metadata(path: Path):
    exe = shutil.which("ffprobe")
    if not exe or not path.is_file():
        return None
    proc = subprocess.run([exe, "-v", "error", "-show_entries", "format_tags:stream_tags", "-of", "json", str(path)],
                          capture_output=True, text=True)
    if proc.returncode:
        return None
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    text = json.dumps(payload, ensure_ascii=False)
    markers = sorted(set(match.group(0) for match in MARKER.finditer(text)))
    assertions = {"ai_generated": bool(markers), "provider_or_platform": bool(PROVIDER_KEY.search(text)),
                  "content_id": bool(CONTENT_ID_KEY.search(text))}
    assertions["complete"] = all(assertions.values())
    return {"payload": payload, "ai_markers": markers, "china_assertions": assertions}


def _c2pa_json_verdict(payload):
    if not isinstance(payload, Mapping):
        return False, ["c2pa_output_not_object"]
    active = payload.get("active_manifest") or payload.get("activeManifest")
    manifests = payload.get("manifests")
    present = bool(active and isinstance(manifests, Mapping) and manifests)
    statuses = payload.get("validation_status") or payload.get("validationStatus") or []
    if isinstance(statuses, Mapping):
        statuses = [statuses]
    errors = []
    for row in statuses if isinstance(statuses, list) else []:
        raw = json.dumps(row, ensure_ascii=False).lower()
        if any(token in raw for token in ("mismatch", "invalid", "failure", "error", "tamper")):
            errors.append(raw[:500])
    if not present:
        errors.append("active_manifest_missing")
    return present and not errors, errors


def c2pa_probe(path: Path):
    exe = shutil.which("c2patool")
    if not exe or not path.is_file():
        return None
    attempts = ([exe, str(path), "--json"], [exe, str(path), "-d"])
    for command in attempts:
        proc = subprocess.run(command, capture_output=True, text=True)
        text = (proc.stdout or proc.stderr or "").strip()
        if proc.returncode == 0 and text and not re.search(r"no manifest|manifest.*not found", text, re.I):
            try:
                payload = json.loads(text)
                verified, errors = _c2pa_json_verdict(payload)
                ai_assertion = bool(AI_SOURCE.search(json.dumps(payload, ensure_ascii=False)))
            except json.JSONDecodeError:
                payload = {"raw": text[:10000]}
                verified = bool(re.search(r"active manifest|content credential", text, re.I) and
                                not re.search(r"invalid|mismatch|failure|error|tamper", text, re.I))
                errors = [] if verified else ["unstructured_probe_not_verified"]
                ai_assertion = bool(AI_SOURCE.search(text))
            return {"verified": verified, "command": command[1:], "manifest": payload,
                    "ai_assertion": ai_assertion, "validation_errors": errors}
    return {"verified": False, "command": attempts[0][1:], "manifest": None,
            "validation_errors": ["manifest_not_found_or_probe_failed"]}


def _uses_ai(usage: Mapping[str, Any]):
    return any(str(usage.get(key) or "").lower().startswith("ai-") for key in ("visual_mode", "video_mode"))


def _receipt(root: Path, brief: Mapping[str, Any], did: str, digest: str | None):
    rows = brief.get("provenance_receipts") if isinstance(brief.get("provenance_receipts"), list) else []
    for row in rows:
        if not isinstance(row, Mapping) or str(row.get("deliverable_id") or "") != did:
            continue
        ref = str(row.get("evidence_file") or "").strip()
        if ref.startswith(("https://", "http://", "record:")):
            claimed = str(row.get("evidence_sha256") or "").strip().lower()
            evidence_sha = claimed if re.fullmatch(r"[0-9a-f]{64}", claimed) else None
        else:
            evidence_path = Path(ref)
            if ref and not evidence_path.is_absolute():
                evidence_path = root / evidence_path
            evidence_sha = sha(evidence_path) if ref else None
        valid = (str(row.get("status") or "").lower() == "verified" and row.get("asset_sha256") == digest and
                 bool(row.get("tool")) and valid_checked_at(row.get("checked_at")) and bool(row.get("approved_by")) and
                 evidence_exists(root, row.get("evidence_file")) and evidence_sha is not None)
        evidence_kind = str(row.get("evidence_kind") or "origin_label_probe")
        cryptographic_valid = bool(
            valid
            and evidence_kind == "c2pa_validation"
            and row.get("signature_valid") is True
            and row.get("manifest_asset_sha256") == digest
        )
        return {
            **dict(row),
            "evidence_kind": evidence_kind,
            "evidence_sha256_actual": evidence_sha,
            "valid": valid,
            "cryptographic_valid": cryptographic_valid,
            "cryptographic_trusted": bool(cryptographic_valid and row.get("signer_trusted") is True),
        }
    return None


def build(root: Path):
    root = root.resolve()
    brief = load(root / "需求" / "brief.json", {}) or {}
    usage = load(root / "合规" / "ai_usage.json", {}) or {}
    plan = load(root / "合成" / "delivery_plan.json", {}) or {}
    uses_ai = _uses_ai(usage)
    findings = []
    items = []
    regions = brief.get("release_regions") or brief.get("release_region") or []
    if isinstance(regions, str):
        regions = [regions]
    for row in plan.get("deliverables") or []:
        if row.get("status") == "cancelled":
            continue
        did = str(row.get("deliverable_id") or "")
        rel = str(row.get("expected_path") or "")
        path = root / rel
        digest = sha(path)
        c2pa = c2pa_probe(path)
        metadata = ffprobe_metadata(path)
        receipt = _receipt(root, brief, did, digest)
        local_c2pa_valid = bool(c2pa and c2pa.get("verified") and c2pa.get("ai_assertion"))
        local_c2pa_trusted = bool(local_c2pa_valid and c2pa.get("signer_trusted") is True)
        metadata_label = bool(metadata and (metadata.get("china_assertions") or {}).get("complete"))
        external_assertions = ((receipt or {}).get("metadata_assertions")
                               if isinstance((receipt or {}).get("metadata_assertions"), Mapping) else {})
        external_label = bool(
            receipt and receipt.get("valid")
            and external_assertions.get("ai_generated")
            and external_assertions.get("provider_or_platform")
            and external_assertions.get("content_id")
        )
        origin_label_compliant = metadata_label or external_label or not uses_ai
        cryptographic_valid = local_c2pa_valid or bool(receipt and receipt.get("cryptographic_valid"))
        cryptographic_trusted = local_c2pa_trusted or bool(receipt and receipt.get("cryptographic_trusted"))
        # Origin labels satisfy disclosure/identification duties; C2PA proves a
        # cryptographically bound provenance chain.  They are reported
        # separately and never upgrade one another's evidence class.
        verified = origin_label_compliant or cryptographic_valid or not uses_ai
        if not digest:
            findings.append({"severity": "block", "code": "provenance_media_missing", "msg": f"{did} 最终媒体缺失/不可哈希"})
        elif uses_ai and not verified:
            findings.append({"severity": "block", "code": "provenance_not_verified",
                             "msg": f"{did} 当前文件未检出机器可读 AI provenance，且无绑定当前 SHA 的外部探测回执"})
        if uses_ai and "中国大陆" in regions:
            assertions = external_assertions
            china_ok = bool(metadata and (metadata.get("china_assertions") or {}).get("complete")) or bool(
                assertions.get("ai_generated") and assertions.get("provider_or_platform") and assertions.get("content_id"))
            if not china_ok:
                findings.append({"severity": "block", "code": "china_implicit_label_unverified",
                                 "msg": f"{did} 未验证中国 AI 标识所需的生成属性、服务/平台标识与内容编号"})
        items.append({"deliverable_id": did, "path": rel, "sha256": digest, "uses_ai": uses_ai,
                      "c2pa": c2pa, "container_metadata": metadata, "external_receipt": receipt,
                      "origin_label_compliant": origin_label_compliant,
                      "cryptographic_provenance_valid": cryptographic_valid,
                      "cryptographic_provenance_trusted": cryptographic_trusted,
                      "verified": verified})
    if uses_ai and not plan.get("deliverables"):
        findings.append({"severity": "block", "code": "provenance_delivery_plan_missing", "msg": "缺 delivery plan，无法逐文件验证 AI provenance"})
    return {
        "schema_version": SCHEMA_VERSION, "kind": KIND,
        "tools": {"c2patool": shutil.which("c2patool") or "", "ffprobe": shutil.which("ffprobe") or ""},
        "standards": [
            {"authority": "official_regulation", "territory": "中国大陆",
             "title": "人工智能生成合成内容标识办法", "effective_date": "2025-09-01",
             "source": "https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm"},
            {"authority": "open_technical_standard", "title": "C2PA Technical Specification 2.4",
             "source": "https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html",
             "checked_at": "2026-08-26"},
        ],
        "items": items, "findings": findings,
        "summary": {"block": sum(f["severity"] == "block" for f in findings),
                    "warn": sum(f["severity"] == "warn" for f in findings),
                    "verified": not any(f["severity"] == "block" for f in findings)},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="verify actual AI provenance metadata/C2PA on final ad files")
    ap.add_argument("project_root")
    ns = ap.parse_args(argv)
    root = Path(ns.project_root).resolve()
    payload = build(root)
    out = root / "合规" / "provenance_qc.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"# provenance QC block={payload['summary']['block']} verified={payload['summary']['verified']}")
    print(f"[ok] {out}")
    return 1 if payload["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
