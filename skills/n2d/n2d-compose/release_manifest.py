#!/usr/bin/env python3
"""Build/check an episode release manifest for n2d.

The manifest is the release-boundary surface.  It summarizes the master asset,
compliance status, review/signoff evidence, and platform labeling/provenance
todos without blocking the upstream compose pipeline.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = SCRIPT_DIR.parent
COMPLIANCE_PATH = SKILLS_DIR / "n2d-compliance" / "scripts" / "compliance.py"
spec = importlib.util.spec_from_file_location("n2d_compliance_for_release_manifest", COMPLIANCE_PATH)
compliance = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(compliance)

N2D_SCRIPTS = SKILLS_DIR / "scripts"
if str(N2D_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(N2D_SCRIPTS))
import artifact_lineage  # noqa: E402

N2D_LIB = SKILLS_DIR / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))
import acceptance_contract  # noqa: E402
try:
    from skill_snapshot import fingerprint_is_fresh  # noqa: E402
except Exception:  # pragma: no cover - 缺依赖时优雅降级为「无法校验」
    fingerprint_is_fresh = None  # type: ignore[assignment]


KIND = "n2d_release_manifest"
VERSION = 1
PLATFORM_ALIASES = {
    "douyin": "douyin",
    "抖音": "douyin",
    "kuaishou": "kuaishou",
    "快手": "kuaishou",
    "bilibili": "bilibili",
    "b站": "bilibili",
    "哔哩哔哩": "bilibili",
    "youtube": "youtube",
    "yt": "youtube",
    "tiktok": "tiktok",
    "tik tok": "tiktok",
}
PLATFORM_REQUIRED_FIELDS = (
    "ai_label",
    "machine_readable",
    "platform_disclosure",
    "subtitle",
    "cover",
    "audio_rights",
    "authorization",
)


def production_dir(root: Path) -> Path:
    return root / "生产数据"


def release_manifest_path(root: Path, episode: str) -> Path:
    return root / "合规" / f"release_manifest_{episode}.json"


def release_manifest_md_path(root: Path, episode: str) -> Path:
    return root / "合规" / f"release_manifest_{episode}.md"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relpath(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_events(root: Path) -> List[Dict[str, Any]]:
    path = production_dir(root) / "production_events.jsonl"
    if not path.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows


def nested(event: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = event.get(key)
    return value if isinstance(value, dict) else {}


def event_value_any(event: Dict[str, Any], *keys: str) -> Any:
    sources = (event, nested(event, "generation"), nested(event, "meta"), nested(event, "cost"))
    for key in keys:
        for source in sources:
            value = source.get(key) if isinstance(source, dict) else None
            if value not in (None, "", [], {}):
                return value
    return ""


def has_real_value(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    low = text.lower()
    return not (low.startswith("todo") or low in {"pending", "unknown", "n/a", "na", "待补", "未定"})


def _rel_if_exists(root: Path, raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    path = Path(text)
    full = path if path.is_absolute() else root / path
    return relpath(root, full) if full.is_file() else ""


def provider_watermark_rows(root: Path, episode: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for event in load_events(root):
        if str(event.get("episode") or "").strip() != episode:
            continue
        if str(event.get("stage") or "").strip() != "video":
            continue
        if str(event.get("event") or "").strip() not in {"generation", "redraw"}:
            continue
        text = " ".join(str(event_value_any(event, key)) for key in ("provider", "model", "channel", "backend_version")).lower()
        if not text.strip():
            continue
        raw_watermark = event_value_any(event, "provider_watermark", "digital_watermark", "watermark", "synthid")
        raw_text = str(raw_watermark or "").lower()
        if "veo" in text or "google" in text or "gemini" in text:
            status = "present" if raw_watermark is True or "synthid" in raw_text or raw_text in {"present", "applied", "yes", "true"} else "expected_unverified"
            rows.append({
                "asset": event_value_any(event, "asset"),
                "provider": event_value_any(event, "provider"),
                "model": event_value_any(event, "model"),
                "channel": event_value_any(event, "channel"),
                "watermark": "SynthID",
                "status": status,
                "note": "Google/Veo outputs are expected to carry SynthID; production event should record verification when possible.",
            })
    return rows


def normalize_platform(value: Any) -> str:
    text = str(value or "").strip()
    return PLATFORM_ALIASES.get(text.lower(), PLATFORM_ALIASES.get(text, text.lower() or "unknown"))


def has_subtitle_asset(root: Path, episode: str) -> str:
    candidates = [
        root / "脚本" / episode / "字幕_中文.srt",
        root / "合成" / episode / "字幕_中文.srt",
        root / "合成" / episode / f"{episode}.srt",
    ]
    for path in candidates:
        if path.is_file():
            return relpath(root, path)
    for path in sorted((root / "合成" / episode).glob("*.srt")) if (root / "合成" / episode).is_dir() else []:
        return relpath(root, path)
    return ""


def has_cover_asset(root: Path, episode: str) -> str:
    roots = [root / "合成" / episode, root / "出图" / episode, root / "出图" / episode / "图片"]
    patterns = ("*封面*.png", "*封面*.jpg", "*cover*.png", "*cover*.jpg")
    for base in roots:
        if not base.is_dir():
            continue
        for pattern in patterns:
            hits = sorted(base.glob(pattern))
            if hits:
                return relpath(root, hits[0])
    return ""


def audio_rights_ready(compliance_data: Dict[str, Any]) -> bool:
    rights = compliance_data.get("rights") if isinstance(compliance_data.get("rights"), dict) else {}
    for key in ("music_bgm", "sfx"):
        row = rights.get(key) if isinstance(rights.get(key), dict) else {}
        status = str(row.get("status") or "").strip()
        if not status:
            return False
        if status in getattr(compliance, "RIGHTS_EVIDENCE_REQUIRED", set()) and not has_real_value(row.get("evidence")):
            return False
    return True


def authorization_ready(compliance_issues: Sequence[str]) -> bool:
    blocking = [str(item) for item in compliance_issues if str(item).startswith("BLOCK")]
    sensitive = ("rights.", "character_likeness", "voice", "cameo", "authorization")
    return not any(any(key in item for key in sensitive) for item in blocking)


def c2pa_validation_summary(root: Path, raw_path: Any) -> Dict[str, Any]:
    """Distinguish file presence from a current C2PA validation receipt.

    n2d does not implement cryptographic C2PA verification itself.  A validator
    wrapper records its result in the referenced JSON; a crJSON derived view is
    explicitly not treated as independently verifiable proof.
    """
    rel = _rel_if_exists(root, raw_path)
    if not rel:
        return {"c2pa_manifest": "", "status": "missing", "spec_version": "", "valid": False, "well_formed": False, "trusted": False}
    path = root / rel
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data = data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        data = {}
    validation = data.get("validation") if isinstance(data.get("validation"), dict) else data
    spec_version = str(validation.get("spec_version") or data.get("spec_version") or "")
    well_formed = validation.get("well_formed") is True
    valid = validation.get("valid") is True
    trusted = validation.get("trusted") is True
    fmt = str(validation.get("format") or data.get("format") or "").lower()
    asset_sha = str(validation.get("asset_sha256") or data.get("asset_sha256") or "")
    if fmt == "crjson" and not str(validation.get("source_manifest") or data.get("source_manifest") or ""):
        status = "derived_view_unverified"
        valid = False
    elif well_formed and valid and len(asset_sha) == 64:
        status = "trusted" if trusted else "valid_untrusted"
    elif validation.get("valid") is False or validation.get("well_formed") is False:
        status = "invalid"
    else:
        status = "present_unverified"
    return {
        "c2pa_manifest": rel,
        "status": status,
        "spec_version": spec_version,
        "well_formed": well_formed,
        "valid": valid,
        "trusted": trusted,
        "asset_sha256": asset_sha,
        "format": fmt,
        "profile_target": "C2PA 2.4 (April 2026)",
    }


def transparency_summary(root: Path, episode: str, compliance_data: Optional[Dict[str, Any]], *, stage: str) -> Dict[str, Any]:
    data = compliance_data if isinstance(compliance_data, dict) else {}
    ai = data.get("ai_labeling") if isinstance(data.get("ai_labeling"), dict) else {}
    label = ai.get("explicit_label") if isinstance(ai.get("explicit_label"), dict) else {}
    meta = ai.get("implicit_metadata") if isinstance(ai.get("implicit_metadata"), dict) else {}
    watermark = ai.get("digital_watermark") if isinstance(ai.get("digital_watermark"), dict) else {}
    platform = ai.get("platform_disclosure") if isinstance(ai.get("platform_disclosure"), dict) else {}
    provider_rows = provider_watermark_rows(root, episode)
    c2pa_manifest = (
        meta.get("c2pa_manifest")
        or ai.get("c2pa_manifest")
        or ai.get("content_credentials_manifest")
        or watermark.get("c2pa_manifest")
    )
    c2pa = c2pa_validation_summary(root, c2pa_manifest)
    machine_readable = bool(
        meta.get("applied") is True
        or c2pa.get("status") in {"trusted", "valid_untrusted"}
        or any(r.get("status") == "present" for r in provider_rows)
    )
    internal = compliance.is_internal_distribution(data) if hasattr(compliance, "is_internal_distribution") else False
    intent = str(data.get("distribution_intent") or "").strip().lower()
    strict = (not internal) and (stage in {"review", "release"} or intent == "paid_distribution")

    blocks: List[str] = []
    infos: List[str] = []
    applicable = ai.get("applicable") is not False
    if applicable:
        if str(label.get("status") or "").strip() != "done":
            msg = "AI 显式标识未确认已落片：ai_labeling.explicit_label.status 应为 done"
            (blocks if strict else infos).append(msg)
        if not machine_readable:
            msg = "缺机器可读 AI 标识/来源信号：implicit_metadata.applied=true、C2PA/Content Credentials manifest 或已验证 provider watermark 至少一项"
            (blocks if strict else infos).append(msg)
        if c2pa.get("status") in {"present_unverified", "derived_view_unverified", "invalid"}:
            infos.append(
                f"C2PA 文件状态={c2pa.get('status')}，不能仅凭存在或 crJSON 派生视图当作有效 Content Credentials；"
                "请用 C2PA 2.4 验证器写 valid/well_formed/trusted 与 asset_sha256 收据"
            )
        if provider_rows and any(r.get("status") == "expected_unverified" for r in provider_rows):
            infos.append("Veo/Google 视频预计含 SynthID，但 production_events 未记录已验证 provider_watermark=SynthID；发布前建议补验证记录")
    if not has_real_value(platform.get("status")):
        infos.append("平台侧 AIGC 披露状态未登记；发布前按目标平台补 platform_disclosure.status")

    return {
        "applicable": applicable,
        "strict": strict,
        "explicit_label": {
            "status": label.get("status") or "",
            "text": label.get("text") or "",
            "position": label.get("position") or "",
            "prominent_label_spec": label.get("prominent_label_spec") or "",
        },
        "implicit_metadata": {
            "spec": meta.get("spec") or "",
            "applied": meta.get("applied") is True,
            "service_provider_code_present": has_real_value(meta.get("service_provider_code")),
            "content_id_present": has_real_value(meta.get("content_id")),
        },
        "content_credentials": c2pa,
        "digital_watermark": {
            "status": watermark.get("status") or "",
            "provider_watermarks": provider_rows,
        },
        "platform_disclosure": platform,
        "machine_readable_present": machine_readable,
        "blocks": blocks,
        "infos": infos,
    }


def platform_release_checklist(
    root: Path,
    episode: str,
    compliance_data: Optional[Dict[str, Any]],
    transparency: Dict[str, Any],
    compliance_issues: Sequence[str],
    *,
    stage: str,
) -> Dict[str, Any]:
    data = compliance_data if isinstance(compliance_data, dict) else {}
    internal = compliance.is_internal_distribution(data) if hasattr(compliance, "is_internal_distribution") else False
    intent = str(data.get("distribution_intent") or "").strip().lower()
    strict = (not internal) and (stage in {"review", "release"} or intent == "paid_distribution")
    targets = ((data.get("platform_review") or {}).get("targets") or []) if isinstance(data.get("platform_review"), dict) else []
    if not isinstance(targets, list) or not targets:
        targets = [{"platform": "unknown", "region": "", "language": ""}]
    subtitle = has_subtitle_asset(root, episode)
    cover = has_cover_asset(root, episode)
    label = transparency.get("explicit_label") if isinstance(transparency.get("explicit_label"), dict) else {}
    platform_disclosure = transparency.get("platform_disclosure") if isinstance(transparency.get("platform_disclosure"), dict) else {}
    base_checks = {
        "ai_label": str(label.get("status") or "") == "done",
        "machine_readable": transparency.get("machine_readable_present") is True,
        "platform_disclosure": has_real_value(platform_disclosure.get("status")),
        "subtitle": bool(subtitle),
        "cover": bool(cover),
        "audio_rights": audio_rights_ready(data),
        "authorization": authorization_ready(compliance_issues),
    }
    evidence = {
        "subtitle": subtitle,
        "cover": cover,
        "c2pa_manifest": (transparency.get("content_credentials") or {}).get("c2pa_manifest") if isinstance(transparency.get("content_credentials"), dict) else "",
        "provider_watermarks": (transparency.get("digital_watermark") or {}).get("provider_watermarks") if isinstance(transparency.get("digital_watermark"), dict) else [],
    }
    rows: List[Dict[str, Any]] = []
    blocks: List[str] = []
    infos: List[str] = []
    for idx, target in enumerate(targets, 1):
        target = target if isinstance(target, dict) else {}
        platform_raw = target.get("platform") or "unknown"
        platform = normalize_platform(platform_raw)
        checks = dict(base_checks)
        missing = [name for name in PLATFORM_REQUIRED_FIELDS if not checks.get(name)]
        row = {
            "platform": platform,
            "platform_raw": platform_raw,
            "region": target.get("region") or "",
            "language": target.get("language") or "",
            "checks": checks,
            "missing": missing,
            "evidence": evidence,
        }
        rows.append(row)
        if missing:
            msg = f"platform checklist {platform or idx} missing: {', '.join(missing)}"
            (blocks if strict else infos).append(msg)
    return {
        "strict": strict,
        "required_fields": list(PLATFORM_REQUIRED_FIELDS),
        "targets": rows,
        "blocks": blocks,
        "infos": infos,
    }


def find_master_asset(root: Path, episode: str, explicit: Optional[str] = None) -> Optional[Path]:
    return acceptance_contract.find_master_asset(root, episode, explicit)


def issue_counts(issues: Iterable[str]) -> Dict[str, int]:
    counts = {"block": 0, "info": 0, "warn": 0}
    for item in issues:
        prefix = str(item).split(" ", 1)[0].lower()
        if prefix in counts:
            counts[prefix] += 1
        elif prefix == "block":
            counts["block"] += 1
    return counts


def gate_findings(root: Path, episode: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in sorted(production_dir(root).glob(f"gate_findings_*_{episode}.json")):
        data = load_json(path)
        if not isinstance(data, dict):
            continue
        for finding in data.get("findings") or []:
            if isinstance(finding, dict):
                row = dict(finding)
                row["source_path"] = relpath(root, path)
                rows.append(row)
    return rows


def score_summary(root: Path, episode: str) -> Dict[str, Any]:
    path = production_dir(root) / f"score_{episode}.json"
    data = load_json(path)
    if not isinstance(data, dict):
        return {"available": False, "path": relpath(root, path)}
    return {
        "available": True,
        "path": relpath(root, path),
        "status": data.get("status") or data.get("verdict") or "",
        "score": data.get("score") or data.get("total_score"),
        "threshold": data.get("threshold"),
    }


def review_signoff(root: Path, episode: str) -> Dict[str, Any]:
    """Compatibility presentation for callers that used the old helper name.

    Whole-episode acceptance is now exclusively the canonical hash-bound
    receipt.  A legacy signoff is surfaced as migration input, never as a
    release-ready approval.  Advisory signoffs are not read at all.
    """
    result = acceptance_contract.check_acceptance(root, episode)
    if result.get("available"):
        return {
            "available": True,
            "path": result.get("path") or "",
            "status": result.get("decision") or "",
            "reviewer": result.get("reviewer") or "",
            "valid": result.get("valid") is True,
            "reason": "；".join(str(item) for item in result.get("issues") or []),
            "receipt_id": result.get("receipt_id") or "",
            "canonical": True,
        }
    legacy = result.get("legacy_signoff") if isinstance(result.get("legacy_signoff"), dict) else {}
    if legacy.get("available"):
        return {
            "available": False,
            "valid": False,
            "canonical": False,
            "legacy_available": True,
            "legacy_path": legacy.get("path") or "",
            "legacy_valid_for_migration": legacy.get("valid") is True,
            "reason": "legacy signoff is migration input only; issue acceptance_receipt_<集>.json",
        }
    return {"available": False, "valid": False, "canonical": False}


def release_verdict_summary(root: Path, episode: str) -> Dict[str, Any]:
    path = acceptance_contract.verdict_path(root, episode)
    data = load_json(path)
    valid = (
        isinstance(data, dict)
        and data.get("kind") == "n2d_release_verdict"
        and str(data.get("episode") or "") == episode
    )
    return {
        "available": path.is_file() and isinstance(data, dict),
        "valid": valid,
        "path": relpath(root, path),
        "sha256": sha256_file(path) if path.is_file() else "",
        "status": str(data.get("status") or "").strip().lower() if isinstance(data, dict) else "",
        "profile": str(data.get("profile") or "") if isinstance(data, dict) else "",
        "evidence_digest": (
            str((data.get("evidence_bindings") or {}).get("digest") or "")
            if isinstance(data, dict) and isinstance(data.get("evidence_bindings"), dict)
            else ""
        ),
    }


def gate_findings_freshness(root: Path, episode: str) -> Dict[str, List[str]]:
    """校验缓存的 gate_findings 是否仍对应当前产物。

    读每份 `gate_findings_*_<ep>.json` 的 `inputs_fingerprint`，按记录的文件清单重算 sha：
    - stale：指纹失配（产物已改但仍读旧判定），缓存的 0 block 不可信 → 应阻断发布、重跑 gate。
    - unverified：旧报告/手写、无可用指纹，无法证明时效 → 仅提示。
    """
    stale: List[str] = []
    unverified: List[str] = []
    for path in sorted(production_dir(root).glob(f"gate_findings_*_{episode}.json")):
        data = load_json(path)
        if not isinstance(data, dict):
            continue
        fingerprint = data.get("inputs_fingerprint")
        fresh = fingerprint_is_fresh(fingerprint, str(root)) if fingerprint_is_fresh else None
        if fresh is False:
            stale.append(relpath(root, path))
        elif fresh is None:
            unverified.append(relpath(root, path))
    return {"stale": stale, "unverified": unverified}


def build_manifest(root: Path, episode: str, *, asset: Optional[str] = None, stage: str = "review") -> Dict[str, Any]:
    root = root.resolve()
    master = find_master_asset(root, episode, asset)
    lineage = artifact_lineage.build_lineage(root, episode, asset=asset)
    lineage_json_path = artifact_lineage.lineage_path(root, episode)
    compliance_path = compliance.manifest_path(root)
    compliance_data = load_json(compliance_path)
    issues = compliance.check_manifest(root, episode, stage=stage)
    gate_rows = gate_findings(root, episode)
    blocks = [row for row in gate_rows if str(row.get("severity") or row.get("sev") or "").lower() == "block"]
    verdict = release_verdict_summary(root, episode)
    acceptance = acceptance_contract.check_acceptance(root, episode)
    readiness_blocks: List[str] = []
    if master is None or not master.is_file():
        readiness_blocks.append("missing master asset")
    if not verdict.get("available"):
        readiness_blocks.append("missing canonical release verdict")
    elif not verdict.get("valid"):
        readiness_blocks.append("canonical release verdict is invalid")
    elif verdict.get("status") not in acceptance_contract.ACCEPTABLE_VERDICT_STATUSES:
        readiness_blocks.append(f"canonical release verdict is not acceptable: {verdict.get('status') or 'missing'}")
    signoff = review_signoff(root, episode)
    if acceptance.get("status") != "pass":
        readiness_blocks.extend(
            f"canonical acceptance receipt: {item}"
            for item in (acceptance.get("issues") or ["missing or invalid"])
        )
    receipt_bindings = acceptance.get("bindings") if isinstance(acceptance.get("bindings"), dict) else {}
    accepted_master = receipt_bindings.get("master_asset") if isinstance(receipt_bindings.get("master_asset"), dict) else {}
    if acceptance.get("status") == "pass" and master is not None:
        selected_path = relpath(root, master)
        selected_sha = sha256_file(master) if master.is_file() else ""
        if (
            str(accepted_master.get("path") or "") != selected_path
            or str(accepted_master.get("sha256") or "") != selected_sha
        ):
            readiness_blocks.append(
                "selected release asset does not match canonical acceptance master binding"
            )
    findings_freshness = gate_findings_freshness(root, episode)
    if lineage.get("status") == "fail":
        readiness_blocks.append("artifact lineage has missing required evidence")
    ai_labeling = compliance_data.get("ai_labeling") if isinstance(compliance_data, dict) else {}
    transparency = transparency_summary(root, episode, compliance_data, stage=stage)
    platform_checklist = platform_release_checklist(root, episode, compliance_data, transparency, issues, stage=stage)
    diagnostics = (
        [item for item in issues if item.startswith(("BLOCK", "WARN", "INFO"))]
        + [f"current gate diagnostic: {row.get('dimension') or row.get('dim')}: {row.get('message') or row.get('msg')}" for row in blocks]
        + list(transparency.get("blocks") or [])
        + list(transparency.get("infos") or [])
        + list(platform_checklist.get("blocks") or [])
        + list(platform_checklist.get("infos") or [])
        + [f"gate findings stale after verdict/acceptance: {rel}; regenerate verdict and acceptance receipt before relying on this diagnostic" for rel in findings_freshness.get("stale", [])]
        + [f"gate findings 无输入指纹，无法校验时效（旧报告/手写）：{rel}" for rel in findings_freshness.get("unverified", [])]
    )
    payload: Dict[str, Any] = {
        "kind": KIND,
        "version": VERSION,
        "episode": episode,
        "root": str(root),
        "stage": stage,
        "asset": {
            "path": relpath(root, master) if master else "",
            "exists": bool(master and master.is_file()),
            "sha256": sha256_file(master) if master and master.is_file() else "",
            "bytes": master.stat().st_size if master and master.is_file() else 0,
        },
        "compliance": {
            "path": relpath(root, compliance_path),
            "issue_counts": issue_counts(issues),
            "issues": issues,
            "ai_labeling": ai_labeling if isinstance(ai_labeling, dict) else {},
        },
        "review": {
            "score": score_summary(root, episode),
            "signoff": signoff,
            "acceptance_receipt": acceptance,
            "release_verdict": verdict,
            "gate_blocks": len(blocks),
            "gate_findings": gate_rows,
        },
        "provenance": {
            "content_credentials": (transparency.get("content_credentials") or {}).get("status") or "missing",
            "c2pa_manifest": (transparency.get("content_credentials") or {}).get("c2pa_manifest") or "",
            "event_ledger_audit": relpath(root, production_dir(root) / "production_events_audit.json"),
            "artifact_lineage": {
                "path": relpath(root, lineage_json_path),
                "sha256": "",
                "status": lineage.get("status"),
                "lineage_id": lineage.get("lineage_id"),
            },
            "release_manifest_hash_scope": "canonical release_verdict sha256 + acceptance_receipt evidence_digest + master sha256 + lineage sha256",
        },
        "transparency": transparency,
        "platform_release_checklist": platform_checklist,
        "readiness": {
            "status": "blocked" if readiness_blocks else "ready",
            "blocks": readiness_blocks,
            "infos": list(dict.fromkeys(str(item) for item in diagnostics if str(item))),
            "definition": "acceptable canonical release_verdict AND fresh canonical acceptance_receipt bound to the same master/score/ledger/review-ui hashes",
        },
    }
    payload["manifest_id"] = hashlib.sha256(
        json.dumps(
            {
                "episode": episode,
                "asset": payload["asset"],
                "release_verdict": verdict,
                "acceptance_receipt": {
                    "receipt_id": acceptance.get("receipt_id"),
                    "evidence_digest": acceptance.get("evidence_digest"),
                },
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    return payload


def render_markdown(payload: Dict[str, Any]) -> str:
    ready = payload.get("readiness", {})
    asset = payload.get("asset", {})
    lines = [
        "# n2d 发布 Manifest",
        "",
        f"- 集：{payload.get('episode')}",
        f"- 状态：{ready.get('status')}",
        f"- 母带：`{asset.get('path') or '—'}`",
        f"- SHA256：`{asset.get('sha256') or '—'}`",
        "",
        "## 阻断",
        "",
    ]
    blocks = ready.get("blocks") or []
    lines.extend([f"- {item}" for item in blocks] or ["- 无"])
    lines.extend(["", "## 发布待办", ""])
    infos = ready.get("infos") or []
    lines.extend([f"- {item}" for item in infos[:40]] or ["- 无"])
    checklist = payload.get("platform_release_checklist") if isinstance(payload.get("platform_release_checklist"), dict) else {}
    if checklist.get("targets"):
        lines.extend(["", "## 平台交付 Checklist", ""])
        for row in checklist.get("targets") or []:
            missing = ", ".join(row.get("missing") or []) or "无"
            lines.append(f"- {row.get('platform')}：缺项 {missing}")
    lines.append("")
    return "\n".join(lines)


def write_manifest(root: Path, episode: str, payload: Dict[str, Any]) -> Path:
    lineage = artifact_lineage.build_lineage(root, episode, asset=(payload.get("asset") or {}).get("path") or None)
    lineage_path = artifact_lineage.write_lineage(root, episode, lineage)
    provenance = payload.setdefault("provenance", {})
    provenance["artifact_lineage"] = {
        "path": relpath(root, lineage_path),
        "sha256": sha256_file(lineage_path),
        "status": lineage.get("status"),
        "lineage_id": lineage.get("lineage_id"),
    }
    path = release_manifest_path(root, episode)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    release_manifest_md_path(root, episode).write_text(render_markdown(payload), encoding="utf-8")
    return path


def check_manifest(root: Path, episode: str) -> Dict[str, Any]:
    path = release_manifest_path(root, episode)
    data = load_json(path)
    if not isinstance(data, dict) or data.get("kind") != KIND:
        return {"status": "fail", "issues": [f"missing or invalid {path}"]}
    issues: List[str] = []
    asset = data.get("asset") if isinstance(data.get("asset"), dict) else {}
    asset_path = root / str(asset.get("path") or "")
    if not asset.get("path") or not asset_path.is_file():
        issues.append("asset missing")
    elif asset.get("sha256") != sha256_file(asset_path):
        issues.append("asset sha256 mismatch")

    def add_issue(text: Any) -> None:
        msg = str(text)
        if msg not in issues:
            issues.append(msg)

    blocks = (data.get("readiness") or {}).get("blocks") if isinstance(data.get("readiness"), dict) else []
    if blocks:
        for item in blocks:
            add_issue(item)
    transparency = data.get("transparency") if isinstance(data.get("transparency"), dict) else {}
    if not transparency:
        add_issue("transparency summary missing from release manifest")
    checklist = data.get("platform_release_checklist") if isinstance(data.get("platform_release_checklist"), dict) else {}
    if not checklist:
        add_issue("platform release checklist missing from release manifest")

    # Re-evaluate the one completion definition against disk.  Do not recreate
    # a second verdict from manifest-time gate/compliance summaries: those are
    # diagnostics; the hash-bound release verdict + acceptance receipt is the
    # authority.
    current_verdict = release_verdict_summary(root, episode)
    stored_review = data.get("review") if isinstance(data.get("review"), dict) else {}
    stored_verdict = stored_review.get("release_verdict") if isinstance(stored_review.get("release_verdict"), dict) else {}
    if not current_verdict.get("valid"):
        add_issue("canonical release verdict missing or invalid")
    elif current_verdict.get("status") not in acceptance_contract.ACCEPTABLE_VERDICT_STATUSES:
        add_issue(f"canonical release verdict is not acceptable: {current_verdict.get('status') or 'missing'}")
    if not stored_verdict:
        add_issue("canonical release verdict summary missing from release manifest")
    elif stored_verdict.get("sha256") != current_verdict.get("sha256"):
        add_issue("canonical release verdict sha256 mismatch")

    acceptance = acceptance_contract.check_acceptance(root, episode)
    if acceptance.get("status") != "pass":
        for item in acceptance.get("issues") or ["missing or invalid"]:
            add_issue(f"canonical acceptance receipt: {item}")
    stored_acceptance = stored_review.get("acceptance_receipt") if isinstance(stored_review.get("acceptance_receipt"), dict) else {}
    if not stored_acceptance:
        add_issue("canonical acceptance receipt summary missing from release manifest")
    else:
        if stored_acceptance.get("receipt_id") != acceptance.get("receipt_id"):
            add_issue("canonical acceptance receipt_id mismatch")
        if stored_acceptance.get("evidence_digest") != acceptance.get("evidence_digest"):
            add_issue("canonical acceptance evidence_digest mismatch")
    receipt_bindings = acceptance.get("bindings") if isinstance(acceptance.get("bindings"), dict) else {}
    accepted_master = receipt_bindings.get("master_asset") if isinstance(receipt_bindings.get("master_asset"), dict) else {}
    if acceptance.get("status") == "pass":
        if (
            str(asset.get("path") or "") != str(accepted_master.get("path") or "")
            or str(asset.get("sha256") or "") != str(accepted_master.get("sha256") or "")
        ):
            add_issue("release manifest asset does not match canonical acceptance master binding")
    lineage = (data.get("provenance") or {}).get("artifact_lineage") if isinstance(data.get("provenance"), dict) else {}
    if not isinstance(lineage, dict) or not lineage.get("path"):
        issues.append("artifact lineage missing from release manifest")
    else:
        lineage_path = root / str(lineage.get("path") or "")
        if not lineage_path.is_file():
            issues.append("artifact lineage file missing")
        elif lineage.get("sha256") and lineage.get("sha256") != sha256_file(lineage_path):
            issues.append("artifact lineage sha256 mismatch")
        lineage_check = artifact_lineage.check_lineage(root, episode)
        if lineage_check.get("status") != "pass":
            issues.extend([f"artifact lineage: {item}" for item in lineage_check.get("issues") or []])
    return {"status": "fail" if issues else "pass", "issues": issues, "path": str(path)}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="build/check n2d release manifest")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build")
    p.add_argument("root")
    p.add_argument("episode")
    p.add_argument("--asset")
    p.add_argument("--stage", default="review", choices=("compose", "review", "release"))
    p.add_argument("--write", action="store_true")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("check")
    p.add_argument("root")
    p.add_argument("episode")
    p.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root)
    if ns.cmd == "build":
        payload = build_manifest(root, ns.episode, asset=ns.asset, stage=ns.stage)
        if ns.write:
            path = write_manifest(root, ns.episode, payload)
            payload["path"] = str(path)
        if ns.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(render_markdown(payload))
        return 1 if payload.get("readiness", {}).get("status") == "blocked" else 0
    result = check_manifest(root, ns.episode)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else "\n".join(result.get("issues") or ["release manifest ok"]))
    return 1 if result.get("status") != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
