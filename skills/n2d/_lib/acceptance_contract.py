#!/usr/bin/env python3
"""Canonical episode acceptance receipt for n2d.

The release verdict is the machine adjudication.  Human acceptance is a
separate, immutable receipt that binds that adjudication and the exact master,
score, consistency ledger and review UI evidence that the reviewer saw.

Only ``生产数据/acceptance_receipt_<集>.json`` can prove whole-episode
acceptance.  Legacy signoff files are readable solely as migration input;
advisory signoffs are deliberately never considered here.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from content_fingerprint import build_content_fingerprint
import n2d_schema_registry


KIND = "n2d_acceptance_receipt"
VERSION = 1
RECEIPT_NAME = "acceptance_receipt_{episode}.json"
VERDICT_NAME = "release_verdict_{episode}.json"
ALLOWED_DECISIONS = {"approved", "accepted"}
ACCEPTABLE_VERDICT_STATUSES = {"pass", "demo-only", "internal-only"}
REQUIRED_EVIDENCE_ROLES = (
    "master_asset",
    "media_artifact_receipt",
    "creative_watchdown",
    "score",
    "consistency_ledger",
    "review_ui",
    "review_ui_findings",
    "event_ledger_audit",
    "artifact_validation",
)
PLACEHOLDERS = {"", "todo", "pending", "unknown", "n/a", "na", "待补", "未定"}
AUTOMATED_REVIEWER_RE = re.compile(
    r"(?:^|[^a-z0-9])(agent|ai|assistant|automation|bot|chatgpt|claude|codex|delegate|listener|"
    r"machine|model|producer|supervisor|system)(?:[^a-z0-9]|$)|"
    r"^(?:代理|制作代理|自动化|机器人|模型|系统|系统代理|执行器)(?:$|[:：/#@])", re.I
)
REQUIRED_VERDICT_COMPONENTS = {
    "progress_dag", "production_handoff", "script_supervisor_log", "production_locks",
    "pilot_release_gate", "mini_pilot", "contract_trace", "compliance", "release_profile",
    "gate", "identity_drift", "score", "ledger", "review_ui", "image_qc",
    "generation_recipe", "audience_experience", "stop_loss", "final_master",
    "release_evidence_freshness", "failure_taxonomy", "event_ledger_audit",
    "artifact_validation", "creative_watchdown",
}
_RELEASE_FINGERPRINT_EXCLUDED_PREFIXES = (
    "release_verdict_", "acceptance_receipt_", "artifact_lineage_",
)
_RELEASE_FINGERPRINT_EXCLUDED_NAMES = {
    "production_readiness.json",
}


class AcceptanceContractError(ValueError):
    """Raised when a canonical receipt cannot safely be issued."""


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def production_dir(root: Path) -> Path:
    return root / "生产数据"


def receipt_path(root: Path, episode: str) -> Path:
    return production_dir(root) / RECEIPT_NAME.format(episode=episode)


def verdict_path(root: Path, episode: str) -> Path:
    return production_dir(root) / VERDICT_NAME.format(episode=episode)


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def probe_master_duration(path: Path) -> Optional[float]:
    """Prove the canonical master has a decodable video stream and duration."""
    try:
        proc = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=codec_type:format=duration", "-of", "json", str(path),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout or "{}")
        streams = data.get("streams") if isinstance(data, Mapping) else None
        duration = float((data.get("format") or {}).get("duration") or 0)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return duration if isinstance(streams, list) and streams and duration > 0 else None


def _real_identity(value: Any) -> bool:
    text = str(value or "").strip()
    return (
        bool(text)
        and text.lower() not in PLACEHOLDERS
        and not text.lower().startswith("todo")
        and not AUTOMATED_REVIEWER_RE.search(text)
    )


def normalize_decision(value: Any) -> str:
    return str(value or "").strip().lower()


def file_binding(root: Path, path: Path, *, role: str) -> Dict[str, Any]:
    exists = path.is_file()
    return {
        "role": role,
        "path": relpath(root, path),
        "exists": exists,
        "sha256": sha256_file(path) if exists else "",
        "bytes": path.stat().st_size if exists else 0,
    }


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _content_sha256_issue(data: Mapping[str, Any], *, label: str) -> list[str]:
    recorded = str(data.get("content_sha256") or "")
    body = dict(data)
    body.pop("content_sha256", None)
    expected = _canonical_sha256(body)
    return [] if recorded and recorded == expected else [f"{label} content_sha256 invalid"]


def _same_path(left: Any, right: Path) -> bool:
    try:
        return Path(str(left)).resolve() == right.resolve()
    except (OSError, RuntimeError, ValueError):
        return False


_EVENT_LEDGER_MODULE: Any = None
_MEDIA_ARTIFACT_MODULE: Any = None
_CREATIVE_WATCHDOWN_MODULE: Any = None


def _event_ledger_module() -> Any:
    global _EVENT_LEDGER_MODULE
    if _EVENT_LEDGER_MODULE is None:
        path = Path(__file__).resolve().parents[1] / "n2d-dashboard" / "scripts" / "event_ledger.py"
        spec = importlib.util.spec_from_file_location("n2d_event_ledger_for_acceptance", path)
        if spec is None or spec.loader is None:  # pragma: no cover - repository corruption
            raise RuntimeError(f"cannot load event ledger auditor: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _EVENT_LEDGER_MODULE = module
    return _EVENT_LEDGER_MODULE


def _local_completion_module(cache_name: str, relative_path: Path, module_name: str) -> Any:
    global _MEDIA_ARTIFACT_MODULE, _CREATIVE_WATCHDOWN_MODULE
    cached = (
        _MEDIA_ARTIFACT_MODULE
        if cache_name == "media_artifact"
        else _CREATIVE_WATCHDOWN_MODULE
    )
    if cached is None:
        path = Path(__file__).resolve().parents[1] / relative_path
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:  # pragma: no cover - repository corruption
            raise RuntimeError(f"cannot load completion validator: {path}")
        cached = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cached)
        if cache_name == "media_artifact":
            _MEDIA_ARTIFACT_MODULE = cached
        else:
            _CREATIVE_WATCHDOWN_MODULE = cached
    return cached


def _media_artifact_module() -> Any:
    return _local_completion_module(
        "media_artifact", Path("n2d-compose/media_artifact.py"),
        "n2d_media_artifact_for_acceptance",
    )


def _creative_watchdown_module() -> Any:
    return _local_completion_module(
        "creative_watchdown", Path("n2d-review/scripts/creative_watchdown.py"),
        "n2d_creative_watchdown_for_acceptance",
    )


def _event_ledger_evidence(
    root: Path,
    episode: str,
    data: Any,
) -> Tuple[list[str], Dict[str, Any]]:
    issues: list[str] = []
    if not isinstance(data, Mapping):
        return ["event ledger audit missing or invalid"], {}
    if data.get("kind") != "n2d_production_event_ledger_audit":
        issues.append("event ledger audit kind invalid")
    if data.get("version") != 1:
        issues.append("event ledger audit version invalid")
    if not _same_path(data.get("root"), root):
        issues.append("event ledger audit root mismatch")
    expected_ledger = root / "生产数据" / "production_events.jsonl"
    if not _same_path(data.get("ledger"), expected_ledger):
        issues.append("event ledger audit source path mismatch")
    if data.get("strict_trace") is not True:
        issues.append("event ledger audit must be generated with strict_trace=true")
    issues.extend(_content_sha256_issue(data, label="event ledger audit"))

    auditor = _event_ledger_module()
    current = auditor.audit(str(root), write=False, strict_trace=True)
    semantic_keys = (
        "kind", "version", "root", "ledger", "source", "event_count",
        "line_errors", "event_errors", "trace_errors", "event_warnings",
        "trace_summary", "hash_chain_head", "chain_tamper", "strict_trace",
    )
    for key in semantic_keys:
        if data.get(key) != current.get(key):
            issues.append(f"event ledger audit stale or inconsistent: {key}")
    if str(data.get("status") or "").strip().lower() != "pass":
        issues.append(f"event ledger audit status is not pass: {data.get('status') or 'missing'}")
    if current.get("status") != "pass":
        issues.append(f"current event ledger audit is not pass: {current.get('status') or 'missing'}")

    events, line_errors = auditor.load_event_lines(str(root))
    episode_events = [
        {key: value for key, value in row.items() if not str(key).startswith("_")}
        for row in events
        if str(row.get("episode") or "") == episode
    ]
    projection = {
        "kind": "n2d_operational_evidence_projection",
        "version": 1,
        "role": "event_ledger_audit",
        "report_kind": data.get("kind"),
        "report_version": data.get("version"),
        "status": "pass" if not issues else "fail",
        "episode": episode,
        "strict_trace": data.get("strict_trace") is True,
        "source": {
            "path": "生产数据/production_events.jsonl",
            "episode_event_count": len(episode_events),
            "episode_events_sha256": _canonical_sha256(episode_events),
            "line_error_count": len(line_errors),
        },
    }
    return list(dict.fromkeys(issues)), projection


def _belongs_to_episode(relative_path: str, episode: str) -> bool:
    episodes = set(re.findall(r"第\d+集", relative_path))
    return not episodes or episode in episodes


_OPERATIONAL_VOLATILE_KEYS = {
    "generated_at", "updated_at", "checked_at", "written_at", "created_at",
    "mtime", "mtime_ns", "elapsed_sec", "duration_ms",
}


def _semantic_artifact_projection(root: Path, row: Mapping[str, Any]) -> Tuple[str, int]:
    """Hash JSON evidence by meaning, not by regenerated clock metadata."""
    rel = str(row.get("relative_path") or "")
    path = root / rel
    if str(row.get("format") or "") != "json" or not path.is_file():
        return str(row.get("sha256") or ""), int(row.get("bytes") or 0)
    data = load_json(path)

    def normalize(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): normalize(child)
                for key, child in value.items()
                if str(key) not in _OPERATIONAL_VOLATILE_KEYS
            }
        if isinstance(value, list):
            return [normalize(child) for child in value]
        return value

    normalized = normalize(data)
    raw = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest(), len(raw)


def _artifact_validation_evidence(
    root: Path,
    episode: str,
    data: Any,
) -> Tuple[list[str], Dict[str, Any]]:
    issues: list[str] = []
    if not isinstance(data, Mapping):
        return ["artifact validation report missing or invalid"], {}
    if data.get("kind") != n2d_schema_registry.ARTIFACT_VALIDATION_KIND:
        issues.append("artifact validation kind invalid")
    if data.get("version") != 1:
        issues.append("artifact validation version invalid")
    if not _same_path(data.get("root"), root):
        issues.append("artifact validation root mismatch")
    if data.get("scope") != n2d_schema_registry.SCAN_SCOPE_RELEASE:
        issues.append("artifact validation scope must be release")
    if data.get("strict_unknown") is not True:
        issues.append("artifact validation must use strict_unknown=true")
    if data.get("completion_inputs_only") is not True:
        issues.append("artifact validation must use completion_inputs_only=true")
    issues.extend(_content_sha256_issue(data, label="artifact validation"))

    current = n2d_schema_registry.scan_artifacts(
        str(root), strict_unknown=True, scope=n2d_schema_registry.SCAN_SCOPE_RELEASE,
        completion_inputs_only=True,
    )
    # Compare the strict release surface, not informational skipped support
    # files.  Verdict checks may emit a non-contract diagnostic JSON after the
    # preflight; that must not create a false cycle.  Any newly added/changed
    # formal artifact still changes scanned membership or its content hash.
    semantic_keys = (
        "kind", "version", "root", "scope", "strict_unknown", "completion_inputs_only", "schema_registry",
        "source", "scanned_count", "scanned", "checked_count", "checked",
        "issues", "summary", "status",
    )
    for key in semantic_keys:
        if data.get(key) != current.get(key):
            issues.append(f"artifact validation report is stale against current release evidence: {key}")
    if str(data.get("status") or "").strip().lower() != "pass":
        issues.append(f"artifact validation status is not pass: {data.get('status') or 'missing'}")
    if current.get("status") != "pass":
        issues.append(f"current artifact validation is not pass: {current.get('status') or 'missing'}")

    projected_rows: list[Dict[str, Any]] = []
    for row in current.get("scanned") or []:
        if not isinstance(row, Mapping):
            continue
        rel = str(row.get("relative_path") or "")
        # The production event stream is bound above as an episode slice.  Its
        # global file hash here would make an EP2 append revoke EP1.
        if rel == "生产数据/production_events.jsonl" or not _belongs_to_episode(rel, episode):
            continue
        classification = row.get("classification") if isinstance(row.get("classification"), Mapping) else {}
        semantic_sha256, semantic_bytes = _semantic_artifact_projection(root, row)
        projected_rows.append({
            "relative_path": rel,
            "kind": str(row.get("kind") or ""),
            "format": str(row.get("format") or ""),
            "sha256": semantic_sha256,
            "bytes": semantic_bytes,
            "issues": int(row.get("issues") or 0),
            "classifier_reason": str(row.get("classifier_reason") or ""),
            "expected_kind": str(classification.get("expected_kind") or ""),
        })
    projected_issues = [
        dict(row)
        for row in current.get("issues") or []
        if isinstance(row, Mapping)
        and _belongs_to_episode(str(row.get("source") or ""), episode)
        and "production_events.jsonl" not in str(row.get("source") or "")
    ]
    projection = {
        "kind": "n2d_operational_evidence_projection",
        "version": 1,
        "role": "artifact_validation",
        "report_kind": data.get("kind"),
        "report_version": data.get("version"),
        "status": "pass" if not issues else "fail",
        "episode": episode,
        "scope": data.get("scope"),
        "strict_unknown": data.get("strict_unknown") is True,
        "completion_inputs_only": data.get("completion_inputs_only") is True,
        "schema_registry": current.get("schema_registry"),
        "scanned": projected_rows,
        "issues": projected_issues,
    }
    return list(dict.fromkeys(issues)), projection


def validate_operational_evidence(
    root: Path,
    episode: str,
    *,
    role: str,
    path: Optional[Path] = None,
) -> Tuple[list[str], Dict[str, Any]]:
    root = root.resolve()
    expected = {
        "event_ledger_audit": root / "生产数据" / "production_events_audit.json",
        "artifact_validation": root / "生产数据" / "artifact_validation.json",
    }
    if role not in expected:
        return [f"unsupported operational evidence role: {role}"], {}
    report_path = (path or expected[role]).resolve()
    if report_path != expected[role].resolve():
        return [f"{role} path is not canonical"], {}
    data = load_json(report_path)
    if role == "event_ledger_audit":
        return _event_ledger_evidence(root, episode, data)
    return _artifact_validation_evidence(root, episode, data)


def operational_evidence_binding(
    root: Path,
    path: Path,
    *,
    role: str,
    episode: str,
) -> Dict[str, Any]:
    """Bind a verified, episode-owned projection of a global report."""
    issues, projection = validate_operational_evidence(root, episode, role=role, path=path)
    raw = json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    valid = path.is_file() and not issues and bool(projection)
    return {
        "role": role,
        "path": relpath(root, path),
        "exists": path.is_file(),
        "sha256": hashlib.sha256(raw).hexdigest() if valid else "",
        "bytes": len(raw) if valid else 0,
        "binding_kind": "operational_evidence_projection_v1",
        "projection": projection,
        "validation_issues": issues,
    }


def final_master_candidates(root: Path, episode: str) -> list[Path]:
    """Return only canonical delivery masters for an episode.

    Work files such as ``rough_cut.mp4`` deliberately do not participate in
    release selection. Verdict, acceptance and release-manifest code must all
    call this resolver so the machine decision and the human receipt can never
    describe different files.
    """
    root = root.resolve()
    candidates: list[Path] = []
    for pattern in (
        root / "合成" / episode / f"成片_{episode}_*.mp4",
        root / "合成" / episode / f"成片_{episode}_*.mov",
        root / "成片" / f"*{episode}*.mp4",
    ):
        candidates.extend(path for path in pattern.parent.glob(pattern.name) if path.is_file())
    return sorted({path.resolve() for path in candidates})


def resolve_final_master(root: Path, episode: str, explicit: Optional[str] = None) -> Optional[Path]:
    """Resolve the one canonical master consumed by every completion surface."""
    root = root.resolve()
    candidates = final_master_candidates(root, episode)
    if explicit:
        path = Path(explicit)
        path = (path if path.is_absolute() else root / path).resolve()
        # An explicit release asset may choose among canonical masters, but it
        # cannot promote a proxy/rough cut into a final master.
        return path if path in candidates else None
    if not candidates:
        return None
    # The newest named master is the one a fresh verdict must adjudicate.  A new
    # master appearing after signoff therefore invalidates the old receipt.
    return max(candidates, key=lambda path: (path.stat().st_mtime_ns, path.as_posix()))


def find_master_asset(root: Path, episode: str, explicit: Optional[str] = None) -> Optional[Path]:
    """Backward-compatible alias for the canonical resolver."""
    return resolve_final_master(root, episode, explicit)


def current_evidence_bindings(
    root: Path,
    episode: str,
    *,
    master: Optional[str] = None,
) -> Dict[str, Any]:
    root = root.resolve()
    prod = production_dir(root)
    master_path = find_master_asset(root, episode, master)
    records: Dict[str, Dict[str, Any]] = {
        "master_asset": file_binding(
            root,
            master_path if master_path is not None else root / "合成" / episode / f"成片_{episode}_MISSING.mp4",
            role="master_asset",
        ),
        "media_artifact_receipt": file_binding(
            root, prod / f"media_artifact_receipt_{episode}.json",
            role="media_artifact_receipt",
        ),
        "creative_watchdown": file_binding(
            root, prod / f"creative_watchdown_{episode}.json",
            role="creative_watchdown",
        ),
        "score": file_binding(root, prod / f"score_{episode}.json", role="score"),
        "consistency_ledger": file_binding(
            root, prod / f"consistency_ledger_{episode}.json", role="consistency_ledger"
        ),
        "review_ui": file_binding(root, prod / f"review_ui_{episode}.json", role="review_ui"),
        "review_ui_findings": file_binding(
            root, prod / f"review_ui_findings_{episode}.json", role="review_ui_findings"
        ),
        "event_ledger_audit": operational_evidence_binding(
            root, prod / "production_events_audit.json", role="event_ledger_audit", episode=episode
        ),
        "artifact_validation": operational_evidence_binding(
            root, prod / "artifact_validation.json", role="artifact_validation", episode=episode
        ),
    }
    return {
        "version": 1,
        "records": records,
        "digest": bindings_digest(records),
    }


def release_content_fingerprint(root: Path, episode: str, profile: str) -> Dict[str, Any]:
    """Hash the complete evidence surface adjudicated by a release verdict.

    The verdict/receipt/lineage/release-manifest outputs are deliberately
    excluded to avoid a cycle.  Membership is itself hashed, so adding or
    removing an episode evidence file invalidates an existing acceptance.
    """
    root = root.resolve()
    explicit = {
        "_设置.md", "合规/compliance_manifest.json",
        "设定库/global_style.md", "设定库/source_comprehension.json",
        f"生产数据/score_{episode}.json",
        f"生产数据/consistency_ledger_{episode}.json",
        f"生产数据/review_ui_{episode}.json",
        f"生产数据/review_ui_findings_{episode}.json",
        f"生产数据/media_artifact_receipt_{episode}.json",
        f"生产数据/creative_watchdown_{episode}.json",
    }
    discovered: set[str] = set()
    for pattern in (
        f"脚本/{episode}/**/*",
        f"配音/{episode}/**/*",
        f"出图/{episode}/**/*",
        f"出视频/{episode}/**/*",
        f"合成/{episode}/**/*",
        f"生产数据/gate_findings_*{episode}*.json",
        f"生产数据/score_{episode}.json",
        f"生产数据/consistency_ledger_{episode}.json",
        f"生产数据/review_ui*_{episode}.json",
        f"生产数据/pilot_acceptance_{episode}.json",
        f"生产数据/production_locks_{episode}.json",
        f"生产数据/script_supervisor_log_{episode}.jsonl",
        f"生产数据/contract_trace*_{episode}.json",
        f"生产数据/identity_*_{episode}.json",
        f"生产数据/stop_loss*_{episode}.json",
        f"生产数据/audience_experience*_{episode}.json",
        f"生产数据/final_timeline_probe_{episode}.json",
        f"生产数据/media_artifact_receipt_{episode}.json",
        f"生产数据/creative_watchdown_{episode}.json",
        f"生产数据/image_qc/{episode}/**/*",
        f"生产数据/video_batches/{episode}/**/*",
    ):
        discovered.update(
            path.relative_to(root).as_posix()
            for path in root.glob(pattern)
            if path.is_file()
        )

    def included(rel: str) -> bool:
        name = Path(rel).name
        if name in _RELEASE_FINGERPRINT_EXCLUDED_NAMES:
            return False
        if any(name.startswith(prefix) for prefix in _RELEASE_FINGERPRINT_EXCLUDED_PREFIXES):
            return False
        if rel.startswith("合规/release_manifest_"):
            return False
        return True

    membership = sorted(rel for rel in discovered if included(rel))

    # Resolve only the shared/card dependencies actually named by this
    # episode.  Adding an EP2-only character must not revoke EP1 acceptance.
    dependency_ids: set[str] = set()
    dependency_paths: set[str] = set()
    id_re = re.compile(r"(?:CHAR|BEAST|CROWD|GROUP|LOC|PROP|WEAPON|OUTFIT|VFX|MOUNT_GROUP)_[A-Za-z0-9_\u4e00-\u9fff]+")
    path_re = re.compile(r"(?:出图/共享|角色库|设定库/(?:characters|locations|参考资料))/[^\s`\"'<>|)）]+")
    for rel in list(membership) + ["合规/compliance_manifest.json"]:
        path = root / rel
        if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt", ".srt", ".yaml", ".yml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        dependency_ids.update(id_re.findall(text))
        dependency_paths.update(path_re.findall(text))

    shared_records: Dict[str, Any] = {}
    for registry_rel in ("出图/共享/identity_registry.json", "出图/共享/asset_registry.json"):
        data = load_json(root / registry_rel)
        selected: list[Any] = []

        def select_rows(value: Any) -> None:
            if isinstance(value, Mapping):
                row_ids = {
                    str(value.get(key) or "").strip()
                    for key in ("id", "character_id", "asset_id", "identity_id")
                    if value.get(key)
                }
                if row_ids & dependency_ids:
                    selected.append(dict(value))
                    return
                for child in value.values():
                    select_rows(child)
            elif isinstance(value, list):
                for child in value:
                    select_rows(child)

        select_rows(data)
        shared_records[registry_rel] = selected
        for row in selected:
            dependency_paths.update(path_re.findall(json.dumps(row, ensure_ascii=False)))

    for base in (root / "设定库" / "characters", root / "设定库" / "locations"):
        for path in base.glob("**/*") if base.is_dir() else []:
            if not path.is_file() or path.suffix.lower() not in {".md", ".json"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            if dependency_ids & set(id_re.findall(text)):
                dependency_paths.add(path.relative_to(root).as_posix())
    for rel in sorted(dependency_paths):
        if (root / rel).is_file() and rel not in membership:
            membership.append(rel)
    membership.sort()
    report_snapshots: Dict[str, Any] = {}
    volatile_keys = {
        "generated_at", "updated_at", "checked_at", "written_at", "created_at",
        "mtime", "mtime_ns", "elapsed_sec", "duration_ms",
    }

    def normalize_report(value: Any) -> Any:
        if isinstance(value, Mapping):
            path_value = str(value.get("path") or value.get("artifact") or value.get("file") or "")
            if path_value and (
                any(Path(path_value).name.startswith(prefix) for prefix in _RELEASE_FINGERPRINT_EXCLUDED_PREFIXES)
                or path_value.startswith("合规/release_manifest_")
                or Path(path_value).name.startswith("production_readiness_")
            ):
                return None
            return {
                str(key): normalized
                for key, child in value.items()
                if str(key) not in volatile_keys
                and (normalized := normalize_report(child)) is not None
            }
        if isinstance(value, list):
            return [normalized for child in value if (normalized := normalize_report(child)) is not None]
        return value

    for rel in (
        f"生产数据/generation_recipe_manifest_{episode}.json",
    ):
        report_snapshots[rel] = normalize_report(load_json(root / rel))
    episode_events: list[Any] = []
    events_path = root / "生产数据" / "production_events.jsonl"
    if events_path.is_file():
        try:
            for line in events_path.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                except (TypeError, ValueError):
                    continue
                if isinstance(row, Mapping) and str(row.get("episode") or "") == episode:
                    episode_events.append(dict(row))
        except (OSError, UnicodeError):
            episode_events = [{"error": "episode event ledger unreadable"}]
    progress_text = ""
    progress_path = root / "_进度.md"
    if progress_path.is_file():
        try:
            lines = progress_path.read_text(encoding="utf-8").splitlines()
            episode_index: Optional[int] = None
            acceptance_index: Optional[int] = None
            header_index: Optional[int] = None
            header_line = ""
            separator_line = ""
            episode_lines: list[str] = []
            for index, line in enumerate(lines):
                cells = [cell.strip() for cell in line.split("|")]
                if header_index is None and "集" in cells and "验收" in cells:
                    header_index = index
                    episode_index = cells.index("集")
                    acceptance_index = cells.index("验收")
                    header_line = "|".join(cells)
                    if index + 1 < len(lines):
                        separator_line = "|".join(
                            cell.strip() for cell in lines[index + 1].split("|")
                        )
                    continue
                if (
                    header_index is not None
                    and episode_index is not None
                    and acceptance_index is not None
                    and len(cells) > max(episode_index, acceptance_index)
                    and cells[episode_index] == episode
                ):
                    cells[acceptance_index] = "<canonical-acceptance-excluded>"
                    episode_lines.append("|".join(cells))
            progress_text = "\n".join(
                [header_line or "<progress-header-missing>", separator_line, *episode_lines]
            )
            if not episode_lines:
                progress_text += f"\n<progress-row-missing:{episode}>"
        except (OSError, UnicodeError):
            progress_text = "<unreadable>"
    patterns = sorted(explicit | set(membership))
    operational_evidence = {}
    for role, rel in (
        ("event_ledger_audit", "生产数据/production_events_audit.json"),
        ("artifact_validation", "生产数据/artifact_validation.json"),
    ):
        row = operational_evidence_binding(root, root / rel, role=role, episode=episode)
        operational_evidence[role] = {
            "sha256": row.get("sha256") or "",
            "projection": row.get("projection") or {},
            "validation_issues": row.get("validation_issues") or [],
        }
    return build_content_fingerprint(
        root,
        scope="release_verdict_inputs",
        source_patterns=patterns,
        values={
            "episode": episode,
            "profile": str(profile or "demo"),
            "membership": membership,
            "dependency_ids": sorted(dependency_ids),
            "shared_registry_records": shared_records,
            "progress_pre_acceptance": progress_text,
            "release_report_snapshots": report_snapshots,
            "episode_production_events": episode_events,
            "operational_evidence": operational_evidence,
        },
    )


def release_content_fingerprint_issues(
    root: Path,
    episode: str,
    profile: str,
    recorded: Any,
) -> list[str]:
    if not isinstance(recorded, Mapping):
        return ["release verdict content_fingerprint missing"]
    current = release_content_fingerprint(root, episode, profile)
    if recorded.get("kind") != current["kind"] or int(recorded.get("version") or 0) != current["version"]:
        return ["release verdict content_fingerprint contract invalid"]
    if str(recorded.get("scope") or "") != "release_verdict_inputs":
        return ["release verdict content_fingerprint scope invalid"]
    if str(recorded.get("sha256") or "") != current["sha256"]:
        return ["release verdict content_fingerprint stale against current component evidence"]
    return []


def verdict_contract_issues(root: Path, episode: str, verdict: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if int(verdict.get("version") or 0) != 2:
        issues.append(f"release verdict version invalid: {verdict.get('version')}")
    profile = str(verdict.get("profile") or "").strip()
    if not profile:
        issues.append("release verdict profile missing")
    if not str(verdict.get("generated_at") or "").strip():
        issues.append("release verdict generated_at missing")
    components = verdict.get("components")
    if not isinstance(components, list):
        issues.append("release verdict components missing or invalid")
        components = []
    names: set[str] = set()
    counts = {"block": 0, "warn": 0, "pass": 0}
    for index, row in enumerate(components):
        if not isinstance(row, Mapping):
            issues.append(f"release verdict component[{index}] invalid")
            continue
        name = str(row.get("name") or "").strip()
        status = str(row.get("status") or "").strip().lower()
        if not name or not str(row.get("message") or "").strip() or status not in counts:
            issues.append(f"release verdict component[{index}] incomplete")
            continue
        names.add(name)
        counts[status] += 1
    missing = sorted(REQUIRED_VERDICT_COMPONENTS - names)
    if missing:
        issues.append("release verdict components incomplete: " + ",".join(missing))
    summary = verdict.get("summary")
    if not isinstance(summary, Mapping) or any(int(summary.get(key) or 0) != value for key, value in counts.items()):
        issues.append("release verdict summary does not match components")
    top_status = str(verdict.get("status") or "").strip().lower()
    if counts["block"] and top_status != "blocked":
        issues.append("release verdict status contradicts blocking components")
    if not counts["block"] and top_status == "blocked":
        issues.append("release verdict status contradicts non-blocking components")
    expected_blocks = [row for row in components if isinstance(row, Mapping) and row.get("status") == "block"]
    expected_warnings = [row for row in components if isinstance(row, Mapping) and row.get("status") == "warn"]
    if verdict.get("blocking_reasons") != expected_blocks:
        issues.append("release verdict blocking_reasons do not match components")
    if verdict.get("warnings") != expected_warnings:
        issues.append("release verdict warnings do not match components")
    final_master = next(
        (row for row in components if isinstance(row, Mapping) and row.get("name") == "final_master"),
        None,
    )
    current_master = resolve_final_master(root, episode)
    expected_master = relpath(root, current_master) if current_master is not None else ""
    selected_master = ""
    if isinstance(final_master, Mapping):
        details = final_master.get("details")
        selected_master = str(details.get("selected") or "") if isinstance(details, Mapping) else ""
        selected_master = selected_master or str(final_master.get("path") or "")
    if selected_master != expected_master:
        issues.append(
            "release verdict final_master does not match canonical master resolver: "
            f"{selected_master or 'missing'} != {expected_master or 'missing'}"
        )
    if isinstance(final_master, Mapping) and str(final_master.get("status") or "").lower() == "pass":
        details = final_master.get("details")
        selected_sha = str(details.get("selected_sha256") or "") if isinstance(details, Mapping) else ""
        try:
            duration = float(details.get("duration_sec")) if isinstance(details, Mapping) else 0.0
        except (TypeError, ValueError):
            duration = 0.0
        expected_sha = sha256_file(current_master) if current_master is not None and current_master.is_file() else ""
        if not selected_sha or selected_sha != expected_sha:
            issues.append("release verdict final_master sha256 does not match canonical master")
        if duration <= 0:
            issues.append("release verdict final_master lacks a positive probed duration")
        current_duration = probe_master_duration(current_master) if current_master is not None else None
        if current_duration is None:
            issues.append("canonical final master is not currently ffprobe-decodable")
    # Component rows are only summaries of checks run when the verdict was
    # written. Re-run canonical completion validators now so hand-editing the
    # summary cannot preserve completion after a receipt is deleted, changed,
    # or rebound to a different master.
    media_component = next(
        (row for row in components if isinstance(row, Mapping) and row.get("name") == "final_master"),
        None,
    )
    watchdown_component = next(
        (row for row in components if isinstance(row, Mapping) and row.get("name") == "creative_watchdown"),
        None,
    )
    if current_master is None:
        issues.append("canonical final master is missing")
    else:
        try:
            media_current = _media_artifact_module().current_receipt(
                root, episode, canonical=current_master
            )
        except Exception as exc:
            media_current = {
                "status": "block",
                "issues": [f"validator error: {type(exc).__name__}: {exc}"],
            }
        if media_current.get("status") != "pass":
            detail = "; ".join(str(item) for item in media_current.get("issues") or [])
            issues.append(f"current media_artifact_receipt invalid: {detail or 'validation failed'}")
        if not isinstance(media_component, Mapping) or str(media_component.get("status") or "").lower() != "pass":
            issues.append("release verdict final_master component is not pass")
        try:
            watchdown_current = _creative_watchdown_module().validate_watchdown(
                root, episode, master=current_master
            )
        except Exception as exc:
            watchdown_current = {
                "status": "block",
                "issues": [f"validator error: {type(exc).__name__}: {exc}"],
            }
        if watchdown_current.get("status") != "pass":
            detail = "; ".join(str(item) for item in watchdown_current.get("issues") or [])
            issues.append(f"current creative_watchdown invalid: {detail or 'validation failed'}")
        if not isinstance(watchdown_component, Mapping) or str(watchdown_component.get("status") or "").lower() != "pass":
            issues.append("release verdict creative_watchdown component is not pass")
    for role, rel in (
        ("event_ledger_audit", "生产数据/production_events_audit.json"),
        ("artifact_validation", "生产数据/artifact_validation.json"),
    ):
        operational_issues, _ = validate_operational_evidence(
            root, episode, role=role, path=root / rel
        )
        component_row = next(
            (row for row in components if isinstance(row, Mapping) and row.get("name") == role),
            None,
        )
        issues.extend(f"current {role} invalid: {item}" for item in operational_issues)
        if not isinstance(component_row, Mapping) or str(component_row.get("status") or "").lower() != "pass":
            issues.append(f"release verdict {role} component is not pass")
    issues.extend(release_content_fingerprint_issues(root, episode, profile, verdict.get("content_fingerprint")))
    return issues


def _binding_digest_view(records: Mapping[str, Any]) -> Dict[str, Any]:
    view: Dict[str, Any] = {}
    for role in sorted(records):
        row = records.get(role)
        if not isinstance(row, Mapping):
            view[role] = None
            continue
        view[role] = {
            "path": str(row.get("path") or ""),
            "sha256": str(row.get("sha256") or ""),
            "bytes": int(row.get("bytes") or 0),
            "exists": row.get("exists") is True,
        }
    return view


def bindings_digest(records: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            _binding_digest_view(records),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _binding_issues(records: Any, *, prefix: str = "evidence") -> list[str]:
    issues: list[str] = []
    if not isinstance(records, Mapping):
        return [f"{prefix} bindings missing or invalid"]
    for role in REQUIRED_EVIDENCE_ROLES:
        row = records.get(role)
        if not isinstance(row, Mapping):
            issues.append(f"{prefix} binding missing: {role}")
            continue
        if row.get("exists") is not True or not str(row.get("path") or "") or not str(row.get("sha256") or ""):
            issues.append(f"{prefix} binding incomplete: {role}")
    return issues


def _records_equal(left: Any, right: Any) -> bool:
    return isinstance(left, Mapping) and isinstance(right, Mapping) and _binding_digest_view(left) == _binding_digest_view(right)


def read_legacy_signoff(root: Path, episode: str) -> Dict[str, Any]:
    """Read legacy whole-episode signoff only as migration input.

    ``review_signoff`` must say exactly ``approved``.  The older
    ``acceptance_signoff`` name may say ``approved`` or ``accepted``.  Files
    containing ``advisory`` are intentionally absent from the candidate list.
    """
    for name, allowed in (
        (f"review_signoff_{episode}.json", {"approved"}),
        (f"acceptance_signoff_{episode}.json", ALLOWED_DECISIONS),
    ):
        path = production_dir(root) / name
        data = load_json(path)
        if not isinstance(data, dict):
            continue
        reviewer = next(
            (
                str(data.get(key)).strip()
                for key in ("reviewer", "signed_by", "approver", "reviewed_by", "审核人")
                if _real_identity(data.get(key))
            ),
            "",
        )
        decision = next(
            (
                normalize_decision(data.get(key))
                for key in ("decision", "status", "verdict", "结论")
                if normalize_decision(data.get(key))
            ),
            "",
        )
        valid = bool(reviewer and decision in allowed)
        return {
            "available": True,
            "valid": valid,
            "path": relpath(root, path),
            "reviewer": reviewer,
            "decision": decision,
            "reason": "" if valid else "legacy signoff requires a real reviewer and approved decision",
        }
    return {"available": False, "valid": False}


def verdict_evidence_issues(root: Path, episode: str, verdict: Any) -> Tuple[list[str], Dict[str, Any]]:
    issues: list[str] = []
    current = current_evidence_bindings(root, episode)
    if not isinstance(verdict, Mapping):
        return ["release verdict missing or invalid"], current
    if verdict.get("kind") != "n2d_release_verdict":
        issues.append("release verdict kind invalid")
    if str(verdict.get("episode") or "") != episode:
        issues.append(f"release verdict episode mismatch: {verdict.get('episode')} != {episode}")
    issues.extend(verdict_contract_issues(root, episode, verdict))
    status = str(verdict.get("status") or "").strip().lower()
    if status not in ACCEPTABLE_VERDICT_STATUSES:
        issues.append(f"release verdict is not acceptable: {status or 'missing'}")
    embedded = verdict.get("evidence_bindings")
    embedded_records = embedded.get("records") if isinstance(embedded, Mapping) else None
    issues.extend(_binding_issues(embedded_records, prefix="release verdict"))
    if isinstance(embedded, Mapping):
        embedded_digest = str(embedded.get("digest") or "")
        if not embedded_digest or embedded_digest != bindings_digest(embedded_records or {}):
            issues.append("release verdict evidence digest invalid")
    if not _records_equal(embedded_records, current.get("records")):
        issues.append("release verdict evidence is stale against current master/score/ledger/review-ui")
    return issues, current


def build_receipt(
    root: Path,
    episode: str,
    *,
    reviewer: Optional[str] = None,
    decision: Optional[str] = "approved",
    accepted_at: Optional[str] = None,
) -> Dict[str, Any]:
    root = root.resolve()
    reviewer_text = str(reviewer or "").strip()
    decision_text = normalize_decision(decision)
    if not _real_identity(reviewer_text):
        raise AcceptanceContractError(
            "acceptance reviewer is required explicitly and cannot be inherited from a legacy signoff"
        )
    if decision_text not in ALLOWED_DECISIONS:
        raise AcceptanceContractError("acceptance decision must be approved or accepted")

    vpath = verdict_path(root, episode)
    verdict = load_json(vpath)
    issues, current = verdict_evidence_issues(root, episode, verdict)
    if not vpath.is_file():
        issues.insert(0, f"release verdict file missing: {relpath(root, vpath)}")
    if issues:
        raise AcceptanceContractError("; ".join(issues))

    records = dict(current["records"])
    verdict_binding = file_binding(root, vpath, role="release_verdict")
    verdict_binding.update({
        "status": str((verdict or {}).get("status") or "").strip().lower(),
        "profile": str((verdict or {}).get("profile") or ""),
    })
    records["release_verdict"] = verdict_binding
    evidence_digest = bindings_digest(records)
    timestamp = accepted_at or now_iso()
    identity = {
        "episode": episode,
        "reviewer": reviewer_text,
        "decision": decision_text,
        "accepted_at": timestamp,
        "evidence_digest": evidence_digest,
    }
    payload: Dict[str, Any] = {
        "kind": KIND,
        "version": VERSION,
        "episode": episode,
        "decision": decision_text,
        "reviewer": reviewer_text,
        "accepted_at": timestamp,
        "bindings": records,
        "evidence_digest": evidence_digest,
        "source": {
            "type": "explicit_human_acceptance",
        },
    }
    payload["receipt_id"] = hashlib.sha256(
        json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    return payload


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_receipt(root: Path, episode: str, payload: Mapping[str, Any]) -> Path:
    path = receipt_path(root, episode)
    atomic_write(path, json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return path


def check_acceptance(root: Path, episode: str) -> Dict[str, Any]:
    root = root.resolve()
    path = receipt_path(root, episode)
    data = load_json(path)
    legacy = read_legacy_signoff(root, episode)
    if not isinstance(data, dict):
        return {
            "status": "fail",
            "valid": False,
            "available": False,
            "path": relpath(root, path),
            "issues": ["canonical acceptance receipt missing or invalid"],
            "legacy_signoff": legacy,
        }

    issues: list[str] = []
    if data.get("kind") != KIND:
        issues.append(f"acceptance receipt kind invalid: {data.get('kind')}")
    if data.get("version") != VERSION:
        issues.append(f"acceptance receipt version invalid: {data.get('version')}")
    if str(data.get("episode") or "") != episode:
        issues.append(f"acceptance receipt episode mismatch: {data.get('episode')} != {episode}")
    decision = normalize_decision(data.get("decision"))
    if decision not in ALLOWED_DECISIONS:
        issues.append(f"acceptance decision must be approved or accepted, got {decision or 'missing'}")
    reviewer = str(data.get("reviewer") or "").strip()
    if not _real_identity(reviewer):
        issues.append("acceptance reviewer missing or placeholder")
    if not str(data.get("accepted_at") or "").strip():
        issues.append("acceptance accepted_at missing")

    records = data.get("bindings")
    issues.extend(_binding_issues(records, prefix="acceptance receipt"))
    if not isinstance(records, Mapping) or not isinstance(records.get("release_verdict"), Mapping):
        issues.append("acceptance receipt binding missing: release_verdict")
        records = records if isinstance(records, Mapping) else {}

    recorded_digest = str(data.get("evidence_digest") or "")
    calculated_digest = bindings_digest(records)
    if not recorded_digest or recorded_digest != calculated_digest:
        issues.append("acceptance evidence_digest mismatch")

    for role, row in records.items():
        if not isinstance(row, Mapping):
            continue
        rel = str(row.get("path") or "")
        if not rel:
            issues.append(f"acceptance binding has no path: {role}")
            continue
        fpath = Path(rel)
        fpath = fpath if fpath.is_absolute() else root / fpath
        if not fpath.is_file():
            issues.append(f"acceptance evidence missing: {role}: {rel}")
            continue
        if row.get("binding_kind") == "operational_evidence_projection_v1":
            current_row = operational_evidence_binding(
                root, fpath, role=str(role), episode=episode
            )
            current_sha = str(current_row.get("sha256") or "")
        else:
            current_sha = sha256_file(fpath)
        if str(row.get("sha256") or "") != current_sha:
            issues.append(f"acceptance evidence sha256 mismatch: {role}: {rel}")

    vpath = verdict_path(root, episode)
    verdict = load_json(vpath)
    verdict_issues, current = verdict_evidence_issues(root, episode, verdict)
    issues.extend(verdict_issues)
    if isinstance(records, Mapping):
        receipt_current = {role: records.get(role) for role in REQUIRED_EVIDENCE_ROLES}
        if not _records_equal(receipt_current, current.get("records")):
            issues.append("acceptance receipt is stale against current canonical evidence")
        verdict_row = records.get("release_verdict")
        if isinstance(verdict_row, Mapping):
            if str(verdict_row.get("path") or "") != relpath(root, vpath):
                issues.append("acceptance release_verdict path mismatch")
            if vpath.is_file() and str(verdict_row.get("sha256") or "") != sha256_file(vpath):
                issues.append("acceptance release_verdict sha256 mismatch")

    identity = {
        "episode": episode,
        "reviewer": reviewer,
        "decision": decision,
        "accepted_at": str(data.get("accepted_at") or ""),
        "evidence_digest": recorded_digest,
    }
    expected_id = hashlib.sha256(
        json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    if str(data.get("receipt_id") or "") != expected_id:
        issues.append("acceptance receipt_id mismatch")

    # Preserve first occurrence while keeping diagnostics deterministic.
    issues = list(dict.fromkeys(issues))
    return {
        "status": "fail" if issues else "pass",
        "valid": not issues,
        "available": True,
        "path": relpath(root, path),
        "receipt_id": data.get("receipt_id") or "",
        "decision": decision,
        "reviewer": reviewer,
        "evidence_digest": recorded_digest,
        "bindings": dict(records),
        "issues": issues,
        "legacy_signoff": legacy,
    }


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="issue/check canonical n2d episode acceptance receipts")
    sub = ap.add_subparsers(dest="cmd", required=True)
    approve = sub.add_parser("approve")
    approve.add_argument("root")
    approve.add_argument("episode")
    approve.add_argument("--reviewer", required=True)
    approve.add_argument("--decision", choices=sorted(ALLOWED_DECISIONS), default="approved")
    approve.add_argument("--accepted-at")
    approve.add_argument("--json", action="store_true")
    check = sub.add_parser("check")
    check.add_argument("root")
    check.add_argument("episode")
    check.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root)
    if ns.cmd == "approve":
        try:
            payload = build_receipt(
                root,
                ns.episode,
                reviewer=ns.reviewer,
                decision=ns.decision,
                accepted_at=ns.accepted_at,
            )
        except AcceptanceContractError as exc:
            result = {"status": "fail", "issues": [str(exc)]}
            print(json.dumps(result, ensure_ascii=False, indent=2) if ns.json else str(exc))
            return 2
        path = write_receipt(root, ns.episode, payload)
        result = {**payload, "path": relpath(root, path), "status": "pass"}
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else f"acceptance receipt written: {path}")
        return 0
    result = check_acceptance(root, ns.episode)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else "\n".join(result.get("issues") or ["acceptance receipt ok"]))
    return 0 if result.get("status") == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
