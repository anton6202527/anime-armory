#!/usr/bin/env python3
"""Manifest and retention policy for rebuildable n2d compose caches."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence


KIND = "n2d_compose_cache_manifest"
VERSION = 1
RETENTION_DEFAULT = "手动清理"
RETENTION_VALUES = {"手动清理", "成片后清理", "保留7天"}
DURABLE_LEGACY_NAMES = {"timeline.json", "editorial_timeline.otio", "animatic_timeline.otio"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def retention_setting(root: Path) -> str:
    path = root / "_设置.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return RETENTION_DEFAULT
    match = re.search(r"^\s*[-*]?\s*(?:\*\*)?合成缓存保留(?:\*\*)?\s*[:：]\s*([^#\n]+)", text, re.M)
    value = match.group(1).strip() if match else RETENTION_DEFAULT
    aliases = {"manual": "手动清理", "after_success": "成片后清理", "7d": "保留7天"}
    return aliases.get(value, value if value in RETENTION_VALUES else RETENTION_DEFAULT)


def tree_stats(path: Path) -> Dict[str, Any]:
    files = [item for item in path.rglob("*") if item.is_file()] if path.is_dir() else []
    newest = max((item.stat().st_mtime for item in files), default=None)
    return {
        "exists": path.is_dir(),
        "file_count": len(files),
        "size_bytes": sum(item.stat().st_size for item in files),
        "last_modified": (
            dt.datetime.fromtimestamp(newest, dt.timezone.utc).replace(microsecond=0).isoformat()
            if newest is not None else None
        ),
    }


def master_files(root: Path, episode: str) -> list[Path]:
    base = root / "合成" / episode
    return sorted(path for path in base.glob("成片*.mp4") if path.is_file() and path.stat().st_size > 0)


def legacy_evidence(root: Path, episode: str) -> list[str]:
    work = root / "合成" / episode / "_work"
    if not work.is_dir():
        return []
    return [
        path.relative_to(root).as_posix()
        for path in sorted(work.iterdir()) if path.is_file() and path.name in DURABLE_LEGACY_NAMES
    ]


def build_manifest(root: Path, episode: str, *, last_action: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    root = root.resolve()
    masters = master_files(root, episode)
    legacy = legacy_evidence(root, episode)
    work_rel = f"合成/{episode}/_work"
    clip_rel = f"合成/{episode}/_clipcache"
    work_stats = tree_stats(root / work_rel)
    clip_stats = tree_stats(root / clip_rel)
    clips = root / "出视频" / episode / "视频"
    source_clips = [path for path in clips.glob("*.mp4") if path.is_file()] if clips.is_dir() else []
    entries = [
        {
            "cache_id": "compose_work",
            "path": work_rel,
            **work_stats,
            "disposable": True,
            "safe_to_delete": bool(masters) and not legacy,
            "blocked_by": legacy,
            "rebuild_command": f"bash skills/n2d-compose/compose.sh <作品根> {episode} zh",
            "purpose": "concat、混音 WAV、字幕 PNG 与其它单次合成中间件",
        },
        {
            "cache_id": "normalized_clips",
            "path": clip_rel,
            **clip_stats,
            "disposable": True,
            "safe_to_delete": bool(source_clips),
            "blocked_by": [] if source_clips else [f"出视频/{episode}/视频 缺正式源 Clip"],
            "rebuild_command": f"bash skills/n2d-compose/compose.sh <作品根> {episode} zh",
            "purpose": "按源 Clip 版本、画幅、CRF、preset 规格化的视频缓存",
        },
    ]
    payload: Dict[str, Any] = {
        "schema_version": VERSION,
        "kind": KIND,
        "episode": episode,
        "generated_at": now_iso(),
        "retention": retention_setting(root),
        "canonical_evidence_dir": f"生产数据/timelines/{episode}",
        "entries": entries,
        "summary": {
            "cache_bytes": sum(row["size_bytes"] for row in entries),
            "safe_to_delete_bytes": sum(row["size_bytes"] for row in entries if row["safe_to_delete"]),
            "blocked_entries": sum(not row["safe_to_delete"] and row["exists"] for row in entries),
        },
        "masters": [
            {"path": path.relative_to(root).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in masters
        ],
    }
    if last_action:
        payload["last_action"] = dict(last_action)
    return payload


def manifest_path(root: Path, episode: str) -> Path:
    return root / "生产数据" / "cache_manifests" / f"compose_cache_{episode}.json"


def refresh(root: Path, episode: str, *, last_action: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    payload = build_manifest(root, episode, last_action=last_action)
    write_json_atomic(manifest_path(root, episode), payload)
    return payload


def selected_entries(payload: Mapping[str, Any], target: str) -> Iterable[Mapping[str, Any]]:
    wanted = {"compose_work"} if target == "work" else ({"normalized_clips"} if target == "clipcache" else {"compose_work", "normalized_clips"})
    return [row for row in payload.get("entries") or [] if row.get("cache_id") in wanted]


def clean(root: Path, episode: str, *, target: str = "all", apply: bool = False, force: bool = False) -> Dict[str, Any]:
    before = build_manifest(root, episode)
    planned = []
    blocked = []
    for row in selected_entries(before, target):
        if not row.get("exists"):
            continue
        item = {"cache_id": row["cache_id"], "path": row["path"], "size_bytes": row["size_bytes"]}
        if not row.get("safe_to_delete") and not force:
            blocked.append({**item, "reasons": row.get("blocked_by") or ["cache safety precondition failed"]})
        else:
            planned.append(item)
    removed = []
    if apply and not blocked:
        for item in planned:
            path = root / item["path"]
            if path.is_dir():
                shutil.rmtree(path)
                removed.append(item)
    action = {
        "at": now_iso(),
        "mode": "apply" if apply else "dry_run",
        "target": target,
        "planned": planned,
        "removed": removed,
        "blocked": blocked,
    }
    after = refresh(root, episode, last_action=action) if apply else before
    return {"kind": "n2d_compose_cache_clean", "status": "block" if blocked else "ready", "action": action, "manifest": after}


def cache_age_days(row: Mapping[str, Any]) -> Optional[float]:
    raw = row.get("last_modified")
    if not raw:
        return None
    try:
        moment = dt.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return (dt.datetime.now(dt.timezone.utc) - moment.astimezone(dt.timezone.utc)).total_seconds() / 86400
    except Exception:
        return None


def auto(root: Path, episode: str) -> Dict[str, Any]:
    payload = build_manifest(root, episode)
    retention = payload["retention"]
    should_clean = retention == "成片后清理"
    if retention == "保留7天":
        existing = [row for row in payload["entries"] if row.get("exists")]
        should_clean = bool(existing) and all((cache_age_days(row) or 0) >= 7 for row in existing)
    if should_clean:
        return clean(root, episode, target="all", apply=True)
    refreshed = refresh(root, episode, last_action={"at": now_iso(), "mode": "retain", "retention": retention})
    return {"kind": "n2d_compose_cache_auto", "status": "retained", "manifest": refreshed}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("refresh", "doctor", "clean", "auto"):
        p = sub.add_parser(name)
        p.add_argument("root")
        p.add_argument("episode")
        p.add_argument("--json", action="store_true")
        if name == "clean":
            p.add_argument("--target", choices=("work", "clipcache", "all"), default="all")
            p.add_argument("--apply", action="store_true")
            p.add_argument("--force", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root).expanduser().resolve()
    if ns.command == "refresh":
        payload = refresh(root, ns.episode)
    elif ns.command == "doctor":
        payload = build_manifest(root, ns.episode)
    elif ns.command == "clean":
        payload = clean(root, ns.episode, target=ns.target, apply=ns.apply, force=ns.force)
    else:
        payload = auto(root, ns.episode)
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        summary = payload.get("summary") or payload.get("manifest", {}).get("summary", {})
        print(f"{payload['kind']}: {payload.get('status', 'ready')} cache={summary.get('cache_bytes', 0)} safe={summary.get('safe_to_delete_bytes', 0)}")
    return 2 if payload.get("status") == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
