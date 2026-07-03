#!/usr/bin/env python3
"""Materialize shared n2d video clips into an episode video directory.

Shared ambience / transition clips live under `出视频/共享/视频/`, but compose
orders clips from `出视频/<ep>/视频/`.  This script turns storyboard-level reuse
references into deterministic symlinks or copies so the compose stage sees them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


KIND = "n2d_shared_video_materialization"
REUSE_FIELDS = (
    "shared_video",
    "shared_clip",
    "shared_video_path",
    "reuse_video",
    "video_reuse",
)


def load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def clip_id(clip: Mapping[str, Any], index: int) -> str:
    raw = str(clip.get("id") or clip.get("clip_id") or "").strip()
    if raw:
        raw = raw.replace(" ", "_")
        if raw.lower().startswith("clip_"):
            return raw[:64]
        digits = "".join(ch for ch in raw if ch.isdigit())
        if digits:
            return f"Clip_{int(digits):02d}"
    return f"Clip_{index:02d}"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _spec_from_value(value: Any) -> Optional[Dict[str, Any]]:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        return {"path": value}
    if isinstance(value, Mapping):
        for key in ("path", "file", "src", "source"):
            if value.get(key):
                out = dict(value)
                out["path"] = str(value.get(key))
                return out
    return None


def shared_specs(clip: Mapping[str, Any]) -> Iterable[Tuple[str, Dict[str, Any]]]:
    for field in REUSE_FIELDS:
        spec = _spec_from_value(clip.get(field))
        if spec:
            yield field, spec
    video_out = str(clip.get("video_out") or "").strip()
    if video_out and ("出视频/共享/" in video_out or video_out.startswith("shared:")):
        yield "video_out", {"path": video_out}


def resolve_source(root: Path, raw_path: str) -> Path:
    path = raw_path.replace("shared:", "").strip()
    p = Path(path)
    if p.is_absolute():
        return p
    if "/" not in path and "\\" not in path:
        return root / "出视频" / "共享" / "视频" / path
    return root / path


def destination_for(root: Path, ep: str, cid: str, source: Path, spec: Mapping[str, Any]) -> Path:
    explicit = str(spec.get("dest") or spec.get("target") or "").strip()
    if explicit:
        p = Path(explicit)
        return p if p.is_absolute() else root / p
    name = source.name
    if not name.lower().endswith(".mp4"):
        name = f"{name}.mp4"
    if not name.startswith(cid):
        name = f"{cid}_{name}"
    return root / "出视频" / ep / "视频" / name


def materialize_one(source: Path, dest: Path, *, copy: bool, force: bool) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "source": str(source),
        "dest": str(dest),
        "action": "",
        "status": "ok",
    }
    if not source.is_file():
        row.update({"status": "missing_source", "action": "skip"})
        return row
    src_hash = sha256(source)
    row["sha256"] = src_hash
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() or dest.is_symlink():
        try:
            if dest.resolve() == source.resolve():
                row["action"] = "already_linked"
                return row
        except Exception:
            pass
        if dest.is_file() and sha256(dest) == src_hash:
            row["action"] = "already_present"
            return row
        if not force:
            row.update({"status": "dest_conflict", "action": "skip"})
            return row
        if dest.is_dir():
            row.update({"status": "dest_conflict", "action": "skip", "message": "dest is directory"})
            return row
        dest.unlink()
    if copy:
        shutil.copy2(source, dest)
        row["action"] = "copied"
    else:
        try:
            rel = os.path.relpath(source, dest.parent)
            dest.symlink_to(rel)
            row["action"] = "symlinked"
        except OSError:
            shutil.copy2(source, dest)
            row["action"] = "copied_fallback"
    return row


def run(root: Path, ep: str, *, copy: bool = False, force: bool = False, write: bool = True) -> Dict[str, Any]:
    storyboard = load_json(root / "脚本" / ep / "storyboard.json")
    clips = storyboard.get("clips") if isinstance(storyboard.get("clips"), list) else []
    rows: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, 1):
        if not isinstance(clip, Mapping):
            continue
        cid = clip_id(clip, idx)
        for field, spec in shared_specs(clip):
            source = resolve_source(root, str(spec.get("path") or ""))
            dest = destination_for(root, ep, cid, source, spec)
            row = materialize_one(source, dest, copy=copy, force=force)
            row.update({"clip_id": cid, "field": field})
            expected = str(spec.get("sha256") or spec.get("hash") or "").strip().lower()
            if expected and row.get("sha256") and expected != row["sha256"].lower():
                row["status"] = "hash_mismatch"
                row["expected_sha256"] = expected
            rows.append(row)
    payload = {
        "kind": KIND,
        "episode": ep,
        "rows": rows,
        "summary": {
            "total": len(rows),
            "ok": sum(1 for r in rows if r.get("status") == "ok"),
            "errors": sum(1 for r in rows if r.get("status") != "ok"),
        },
    }
    if write:
        out = root / "生产数据" / f"shared_video_materialized_{ep}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name(f".{out.name}.tmp.{os.getpid()}")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, out)
        payload["path"] = str(out)
    return payload


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="materialize shared video clips for one episode")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--copy", action="store_true", help="copy files instead of symlinking")
    ap.add_argument("--force", action="store_true", help="replace conflicting destination files")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    payload = run(Path(ns.root), ns.episode, copy=ns.copy, force=ns.force, write=not ns.no_write)
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        s = payload["summary"]
        print(f"shared video materialized: ok={s['ok']} errors={s['errors']} total={s['total']}")
    return 1 if payload["summary"]["errors"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
