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

N2D_SCRIPTS = SKILLS_DIR / "n2d" / "scripts"
if str(N2D_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(N2D_SCRIPTS))
import artifact_lineage  # noqa: E402

N2D_LIB = SKILLS_DIR / "n2d" / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))
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
    c2pa_rel = _rel_if_exists(root, c2pa_manifest)
    machine_readable = bool(meta.get("applied") is True or c2pa_rel or any(r.get("status") == "present" for r in provider_rows))
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
        "content_credentials": {
            "c2pa_manifest": c2pa_rel,
            "status": "present" if c2pa_rel else "missing",
        },
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
    if explicit:
        path = Path(explicit)
        return path if path.is_absolute() else root / path
    base = root / "合成" / episode
    if not base.is_dir():
        return None
    candidates = sorted(base.glob(f"成片_{episode}_*.mp4"))
    return candidates[0] if candidates else None


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
    for name in (
        f"review_signoff_{episode}.json",
        f"acceptance_signoff_{episode}.json",
        f"consistency_advisory_signoff_{episode}.json",
    ):
        path = production_dir(root) / name
        data = load_json(path)
        if isinstance(data, dict):
            # 空 dict / 橡皮图章不算人审：必须同时有真实的审核人身份 + 审核结论，
            # 否则「文件存在」只证声明不证现实（曾经空 {} 也能清掉人审 block）。
            reviewer = ""
            for key in ("reviewer", "signed_by", "approver", "reviewed_by", "owner", "审核人"):
                if has_real_value(data.get(key)):
                    reviewer = str(data.get(key)).strip()
                    break
            decision = ""
            for key in ("decision", "status", "verdict", "label", "结论"):
                if has_real_value(data.get(key)):
                    decision = str(data.get(key)).strip()
                    break
            missing = []
            if not reviewer:
                missing.append("reviewer/signed_by")
            if not decision:
                missing.append("decision/status")
            return {
                "available": True,
                "path": relpath(root, path),
                "status": decision or "present",
                "reviewer": reviewer,
                "valid": not missing,
                "reason": ("签收缺字段：" + ", ".join(missing)) if missing else "",
            }
    return {"available": False, "valid": False}


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
    readiness_blocks: List[str] = []
    if master is None or not master.is_file():
        readiness_blocks.append("missing master asset")
    readiness_blocks.extend([item for item in issues if item.startswith("BLOCK")])
    readiness_blocks.extend([f"gate block: {row.get('dimension') or row.get('dim')}: {row.get('message') or row.get('msg')}" for row in blocks])
    signoff = review_signoff(root, episode)
    if not signoff.get("available"):
        readiness_blocks.append("missing human review signoff")
    elif not signoff.get("valid"):
        readiness_blocks.append(
            f"human review signoff invalid（空签收/橡皮图章不算人审）：{signoff.get('reason')}"
        )
    findings_freshness = gate_findings_freshness(root, episode)
    for rel in findings_freshness.get("stale", []):
        readiness_blocks.append(
            f"gate findings stale：{rel} 的输入指纹与当前产物不符，缓存判定不可信；请重跑该阶段 gate 后再发布"
        )
    if lineage.get("status") == "fail":
        readiness_blocks.append("artifact lineage has missing required evidence")
    ai_labeling = compliance_data.get("ai_labeling") if isinstance(compliance_data, dict) else {}
    transparency = transparency_summary(root, episode, compliance_data, stage=stage)
    readiness_blocks.extend(transparency.get("blocks") or [])
    platform_checklist = platform_release_checklist(root, episode, compliance_data, transparency, issues, stage=stage)
    readiness_blocks.extend(platform_checklist.get("blocks") or [])
    payload: Dict[str, Any] = {
        "kind": KIND,
        "version": VERSION,
        "episode": episode,
        "root": str(root),
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
            "release_manifest_hash_scope": "this JSON file + asset.sha256 + compliance/review evidence paths",
        },
        "transparency": transparency,
        "platform_release_checklist": platform_checklist,
        "readiness": {
            "status": "blocked" if readiness_blocks else "ready",
            "blocks": readiness_blocks,
            "infos": [item for item in issues if item.startswith("INFO")] + list(transparency.get("infos") or []) + list(platform_checklist.get("infos") or []) + [f"gate findings 无输入指纹，无法校验时效（旧报告/手写）：{rel}" for rel in findings_freshness.get("unverified", [])],
        },
    }
    payload["manifest_id"] = hashlib.sha256(
        json.dumps(
            {
                "episode": episode,
                "asset": payload["asset"],
                "compliance_issue_counts": payload["compliance"]["issue_counts"],
                "review": payload["review"],
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
    elif transparency.get("blocks"):
        for item in transparency.get("blocks") or []:
            add_issue(item)
    checklist = data.get("platform_release_checklist") if isinstance(data.get("platform_release_checklist"), dict) else {}
    if not checklist:
        add_issue("platform release checklist missing from release manifest")
    elif checklist.get("blocks"):
        for item in checklist.get("blocks") or []:
            add_issue(item)
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
    # 重新对当前盘上文件校验 gate findings 时效，不只信 manifest 落盘时的判定（manifest 可能已陈旧）。
    for rel in gate_findings_freshness(root, episode).get("stale", []):
        add_issue(f"gate findings stale：{rel}")
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
