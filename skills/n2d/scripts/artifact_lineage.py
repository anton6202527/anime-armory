#!/usr/bin/env python3
"""Build and check n2d artifact lineage manifests.

The lineage manifest is release evidence, not a new creative gate.  It records
which source/settings/prompt/media/governance files a release boundary depends
on, with hashes that can be checked later.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from n2d_const import ARTIFACT_LINEAGE_MANIFEST_KIND, PRODUCTION_DIR  # noqa: E402


VERSION = 1
LINEAGE_JSON = "artifact_lineage_{episode}.json"
LINEAGE_MD = "artifact_lineage_{episode}.md"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def production_dir(root: Path) -> Path:
    return root / PRODUCTION_DIR


def lineage_path(root: Path, episode: str) -> Path:
    return production_dir(root) / LINEAGE_JSON.format(episode=episode)


def lineage_md_path(root: Path, episode: str) -> Path:
    return production_dir(root) / LINEAGE_MD.format(episode=episode)


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


def file_record(root: Path, path: Path, *, role: str, required: bool = False) -> Dict[str, Any]:
    exists = path.is_file()
    return {
        "role": role,
        "path": relpath(root, path),
        "required": required,
        "exists": exists,
        "sha256": sha256_file(path) if exists else "",
        "bytes": path.stat().st_size if exists else 0,
    }


def add_file(out: List[Dict[str, Any]], root: Path, path: Path, *, role: str, required: bool = False) -> None:
    out.append(file_record(root, path, role=role, required=required))


def add_glob(out: List[Dict[str, Any]], root: Path, pattern: str, *, role: str, limit: int = 200) -> None:
    for path in sorted(root.glob(pattern))[:limit]:
        if path.is_file():
            add_file(out, root, path, role=role, required=False)


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def find_master_asset(root: Path, episode: str, explicit: Optional[str] = None) -> Optional[Path]:
    if explicit:
        path = Path(explicit)
        return path if path.is_absolute() else root / path
    base = root / "合成" / episode
    if not base.is_dir():
        return None
    candidates = sorted(base.glob(f"成片_{episode}_*.mp4"))
    return candidates[0] if candidates else None


def event_ledger_summary(root: Path) -> Dict[str, Any]:
    audit = production_dir(root) / "production_events_audit.json"
    data = load_json(audit)
    if not isinstance(data, dict):
        return {"audit_path": relpath(root, audit), "available": False}
    return {
        "audit_path": relpath(root, audit),
        "available": True,
        "status": data.get("status"),
        "event_count": data.get("event_count"),
        "hash_chain_head": data.get("hash_chain_head") or "",
        "strict_trace": bool(data.get("strict_trace")),
    }


def build_lineage(root: Path, episode: str, *, asset: Optional[str] = None) -> Dict[str, Any]:
    root = root.resolve()
    files: List[Dict[str, Any]] = []
    master = find_master_asset(root, episode, asset)

    add_file(files, root, root / "_设置.md", role="settings", required=True)
    add_file(files, root, root / "_进度.md", role="progress_state", required=True)
    add_file(files, root, root / "脚本" / episode / "storyboard.json", role="storyboard", required=True)
    add_file(files, root, root / "合规" / "compliance_manifest.json", role="compliance_manifest", required=True)
    add_file(files, root, production_dir(root) / "production_events_audit.json", role="event_ledger_audit", required=True)
    add_file(files, root, production_dir(root) / "artifact_validation.json", role="artifact_validation", required=True)
    add_file(files, root, production_dir(root) / f"generation_recipe_manifest_{episode}.json", role="generation_recipe_manifest", required=True)
    add_file(files, root, production_dir(root) / f"gate_policy_coverage_{episode}.json", role="gate_policy_coverage", required=True)
    add_file(files, root, production_dir(root) / f"score_{episode}.json", role="score", required=False)
    add_file(files, root, production_dir(root) / f"consistency_ledger_{episode}.json", role="consistency_ledger", required=False)
    add_file(files, root, production_dir(root) / f"review_ui_{episode}.json", role="review_ui", required=False)
    add_file(files, root, production_dir(root) / f"review_signoff_{episode}.json", role="human_signoff", required=False)
    add_file(files, root, production_dir(root) / f"acceptance_signoff_{episode}.json", role="human_signoff", required=False)
    add_file(files, root, production_dir(root) / "batch_queue.json", role="batch_queue", required=False)
    add_file(files, root, production_dir(root) / "job_reconcile.json", role="job_reconcile", required=False)
    add_file(files, root, production_dir(root) / "dead_letter_queue.json", role="dead_letter_queue", required=False)
    add_file(files, root, production_dir(root) / "gate_policy_coverage.json", role="gate_policy_coverage_latest", required=False)
    add_file(files, root, Path(__file__).resolve().parents[1] / "_lib" / "gate_policy_matrix.json", role="gate_policy_matrix", required=True)
    if master is not None:
        add_file(files, root, master, role="master_asset", required=True)
    else:
        files.append({"role": "master_asset", "path": "", "required": True, "exists": False, "sha256": "", "bytes": 0})

    add_glob(files, root, f"出图/{episode}/prompt/*.md", role="image_prompt")
    add_glob(files, root, f"出视频/{episode}/prompt/*.md", role="video_prompt")
    add_glob(files, root, f"出视频/{episode}/prompt/*.json", role="video_route")
    add_glob(files, root, f"出图/{episode}/图片/*", role="image_asset")
    add_glob(files, root, f"出视频/{episode}/视频/*", role="video_clip")

    missing_required = [item for item in files if item.get("required") and not item.get("exists")]
    evidence_issues: List[str] = []
    for rel, label in (
        (f"生产数据/generation_recipe_manifest_{episode}.json", "generation_recipe_manifest"),
        (f"生产数据/gate_policy_coverage_{episode}.json", "gate_policy_coverage"),
    ):
        data = load_json(root / rel)
        if isinstance(data, dict) and data.get("status") != "pass":
            evidence_issues.append(f"{label} status={data.get('status')}")
    payload = {
        "kind": ARTIFACT_LINEAGE_MANIFEST_KIND,
        "version": VERSION,
        "root": str(root),
        "episode": episode,
        "generated_at": now_iso(),
        "files": files,
        "trace": event_ledger_summary(root),
        "summary": {
            "file_count": len(files),
            "required_count": sum(1 for item in files if item.get("required")),
            "missing_required": len(missing_required),
            "evidence_issues": len(evidence_issues),
            "total_bytes": sum(int(item.get("bytes") or 0) for item in files),
        },
        "evidence_issues": evidence_issues,
        "status": "fail" if missing_required or evidence_issues else "pass",
    }
    payload["lineage_id"] = hashlib.sha256(
        json.dumps(
            {
                "episode": episode,
                "files": [
                    {
                        "role": item.get("role"),
                        "path": item.get("path"),
                        "sha256": item.get("sha256"),
                        "exists": item.get("exists"),
                    }
                    for item in files
                ],
                "trace": payload["trace"],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]
    return payload


def render_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# n2d Artifact Lineage",
        "",
        f"- 集：{payload.get('episode')}",
        f"- 状态：{payload.get('status')}",
        f"- lineage_id：`{payload.get('lineage_id') or '—'}`",
        f"- 文件数：{summary.get('file_count', 0)}",
        f"- 缺必需文件：{summary.get('missing_required', 0)}",
        "",
        "## Required Evidence",
        "",
        "| role | exists | path | sha256 |",
        "|---|---|---|---|",
    ]
    for item in payload.get("files") or []:
        if not item.get("required"):
            continue
        sha = str(item.get("sha256") or "")
        lines.append(f"| {item.get('role')} | {item.get('exists')} | `{item.get('path') or '—'}` | `{sha[:12] or '—'}` |")
    lines.append("")
    return "\n".join(lines)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_lineage(root: Path, episode: str, payload: Dict[str, Any]) -> Path:
    path = lineage_path(root, episode)
    atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    atomic_write(lineage_md_path(root, episode), render_markdown(payload))
    return path


def check_lineage(root: Path, episode: str) -> Dict[str, Any]:
    path = lineage_path(root, episode)
    data = load_json(path)
    if not isinstance(data, dict) or data.get("kind") != ARTIFACT_LINEAGE_MANIFEST_KIND:
        return {"status": "fail", "issues": [f"missing or invalid {path}"], "path": str(path)}
    issues: List[str] = []
    if data.get("episode") != episode:
        issues.append(f"episode mismatch: {data.get('episode')} != {episode}")
    for item in data.get("files") or []:
        if not isinstance(item, dict):
            continue
        rel = str(item.get("path") or "")
        if not rel:
            if item.get("required"):
                issues.append(f"required {item.get('role')} has no path")
            continue
        fpath = root / rel
        if item.get("required") and not fpath.is_file():
            issues.append(f"required {item.get('role')} missing: {rel}")
            continue
        if fpath.is_file() and item.get("sha256") and item.get("sha256") != sha256_file(fpath):
            issues.append(f"sha256 mismatch: {rel}")
        if item.get("role") in {"generation_recipe_manifest", "gate_policy_coverage"} and fpath.is_file():
            payload = load_json(fpath)
            if not isinstance(payload, dict):
                issues.append(f"{item.get('role')} invalid JSON: {rel}")
            elif payload.get("status") != "pass":
                issues.append(f"{item.get('role')} status is {payload.get('status')}: {rel}")
    return {"status": "fail" if issues else "pass", "issues": issues, "path": str(path)}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="build/check n2d artifact lineage manifest")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build")
    p.add_argument("root")
    p.add_argument("episode")
    p.add_argument("--asset")
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
        payload = build_lineage(root, ns.episode, asset=ns.asset)
        if ns.write:
            path = write_lineage(root, ns.episode, payload)
            payload["path"] = str(path)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_markdown(payload))
        return 1 if payload.get("status") == "fail" else 0
    result = check_lineage(root, ns.episode)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else "\n".join(result.get("issues") or ["artifact lineage ok"]))
    return 1 if result.get("status") != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
