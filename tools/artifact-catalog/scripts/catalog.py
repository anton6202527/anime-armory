#!/usr/bin/env python3
"""Build a portable artifact catalog and audit/migrate legacy work trees."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = 1
CATALOG_REL = Path("生产数据/artifact_catalog.json")
LINE_DIRS = {
    "写小说": "novel",
    "制漫剧": "n2d",
    "画漫画": "comic",
    "写歌": "song",
    "制MV": "mv",
    "拍广告": "ad",
}
KIND_LINES = {
    "create": "novel",
    "rewrite": "novel",
    "spinoff": "novel",
    "novel_project": "novel",
    "n2d": "n2d",
    "n2d_project": "n2d",
    "comic": "comic",
    "comic_project": "comic",
    "song": "song",
    "mv": "mv",
    "ad": "ad",
    "ad_project": "ad",
}
MEDIA_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".wav", ".mp3", ".m4a", ".flac", ".mp4", ".mov", ".mkv", ".pdf", ".docx"}
TEXT_EXTS = {".json", ".jsonl", ".md", ".html", ".txt", ".srt", ".lrc", ".ass", ".otio", ".csv"}
CACHE_PARTS = {"_work", "_clipcache", "_voicecache", "cache", "__pycache__"}
VIEW_EXTS = {".md", ".html"}
ZERO_VOICE_RE = re.compile(r"^Clip\d+_voice\.(?:wav|json)$", re.I)
UNIT_RE = re.compile(r"(第\d+[集章话]|Clip[_ -]?\d+|P\d{3,})", re.I)
ABS_PATH_RE = re.compile(r"(?:/Users/|/home/|[A-Za-z]:\\\\)")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


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


def stable_project_id(line: str, title: str) -> str:
    raw = f"anime-armory:{line}:{title}".encode("utf-8")
    return f"{line}_{hashlib.sha256(raw).hexdigest()[:16]}"


def infer_line(root: Path, meta: Mapping[str, Any], explicit: Optional[str] = None) -> str:
    if explicit:
        return explicit
    raw = str(meta.get("line") or "").strip().lower()
    if raw in set(LINE_DIRS.values()):
        return raw
    kind = str(meta.get("kind") or "").strip().lower()
    if kind in KIND_LINES:
        return KIND_LINES[kind]
    for part in reversed(root.parts):
        if part in LINE_DIRS:
            return LINE_DIRS[part]
    return "unknown"


def project_identity(root: Path, explicit_line: Optional[str] = None) -> Dict[str, Any]:
    meta = load_json(root / "_meta.json", {})
    meta = meta if isinstance(meta, Mapping) else {}
    line = infer_line(root, meta, explicit_line)
    title = str(meta.get("title") or root.name).strip() or root.name
    project_id = str(meta.get("project_id") or stable_project_id(line, title))
    return {
        "project_id": project_id,
        "line": line,
        "title": title,
        "root_rel": ".",
    }


def iter_files(root: Path) -> Iterable[Path]:
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in {".git", "__pycache__"})
        for name in sorted(files):
            path = Path(base) / name
            rel = path.relative_to(root)
            if rel == CATALOG_REL or name == ".DS_Store" or ".tmp." in name:
                continue
            if path.is_symlink() or not path.is_file():
                continue
            yield path


def stage_for(rel: Path) -> str:
    top = rel.parts[0] if rel.parts else "root"
    aliases = {
        "设定": "design", "设定库": "design", "角色库": "design",
        "章节": "writing", "脚本": "script", "词": "lyrics", "创意": "concept",
        "需求": "brief", "排版": "layout", "节拍": "beat", "字幕": "subtitle",
        "配音": "voice", "歌": "audio", "出图": "image", "出视频": "video",
        "合成": "compose", "审稿": "review", "评分": "score", "合规": "compliance",
        "导出": "export", "投放反馈": "feedback", "生产数据": "production",
        "废料": "waste", "修订": "revision", "语义任务": "semantic_job",
    }
    return aliases.get(top, "project")


def unit_for(rel: Path) -> Optional[str]:
    match = UNIT_RE.search(rel.as_posix())
    if not match:
        return None
    value = match.group(1)
    if value.lower().startswith("clip"):
        number = re.search(r"\d+", value)
        return f"Clip_{int(number.group()):02d}" if number else value
    return value


def twin_json(root: Path, rel: Path) -> Optional[str]:
    if rel.suffix.lower() not in VIEW_EXTS:
        return None
    candidate = root / rel.with_suffix(".json")
    if candidate.is_file():
        return rel.with_suffix(".json").as_posix()
    if "views" in rel.parts:
        matches = [
            path for path in (root / "生产数据").rglob(f"{rel.stem}.json")
            if path.is_file() and "views" not in path.relative_to(root).parts
        ] if (root / "生产数据").is_dir() else []
        if len(matches) == 1:
            return matches[0].relative_to(root).as_posix()
    return None


def classify(root: Path, rel: Path, size: int) -> Tuple[str, bool, Optional[str], str]:
    parts = set(rel.parts)
    suffix = rel.suffix.lower()
    name = rel.name.lower()
    derived_from = twin_json(root, rel)
    if size == 0 and ZERO_VOICE_RE.match(rel.name):
        return "invalid", True, None, "invalid"
    if parts & CACHE_PARTS or name.endswith(".lock"):
        return "cache", True, None, "cached"
    if "views" in parts or derived_from:
        return "view", True, derived_from, "derived"
    if rel == Path("_meta.json") or rel.name in {"_设置.md", "_进度.md"}:
        return "contract", False, None, "present"
    if rel.parts and rel.parts[0] == "废料":
        return "waste", False, None, "archived"
    if suffix == ".jsonl":
        return "event_log", False, None, "present"
    if rel.parts and rel.parts[0] == "生产数据":
        if "qc" in name or "finding" in name or "review" in name or "score" in name:
            return "qc", False, None, "present"
        if "manifest" in name or "contract" in name or "receipt" in name or "timeline" in name:
            return "contract", False, None, "present"
        if "run" in name or "batch" in name or "task" in name or "job" in name:
            return "run", False, None, "present"
        return "production_record", False, None, "present"
    if suffix in MEDIA_EXTS:
        return "media", False, None, "present"
    return "document", False, None, "present"


def previous_index(root: Path) -> Dict[str, Mapping[str, Any]]:
    old = load_json(root / CATALOG_REL, {})
    rows = old.get("artifacts") if isinstance(old, Mapping) else []
    return {
        str(row.get("path")): row
        for row in (rows or [])
        if isinstance(row, Mapping) and row.get("path")
    }


def build_catalog(root: Path, *, line: Optional[str] = None, hash_mode: str = "full") -> Dict[str, Any]:
    root = root.expanduser().resolve()
    identity = project_identity(root, line)
    prior = previous_index(root)
    artifacts: List[Dict[str, Any]] = []
    role_bytes: Counter[str] = Counter()
    stage_bytes: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    duplicate_groups: Dict[str, List[str]] = defaultdict(list)
    for path in iter_files(root):
        rel = path.relative_to(root)
        stat = path.stat()
        old = prior.get(rel.as_posix(), {})
        sha = ""
        if hash_mode != "none":
            if (
                old.get("sha256")
                and old.get("size_bytes") == stat.st_size
                and old.get("mtime_ns") == stat.st_mtime_ns
            ):
                sha = str(old.get("sha256"))
            elif hash_mode == "full" or stat.st_size <= 16 * 1024 * 1024:
                sha = sha256_file(path)
        role, disposable, derived_from, status = classify(root, rel, stat.st_size)
        stage = stage_for(rel)
        row: Dict[str, Any] = {
            "artifact_id": f"a_{hashlib.sha256(rel.as_posix().encode('utf-8')).hexdigest()[:16]}",
            "path": rel.as_posix(),
            "name": rel.name,
            "extension": rel.suffix.lower(),
            "role": role,
            "stage": stage,
            "status": status,
            "size_bytes": stat.st_size,
            "mtime": dt.datetime.fromtimestamp(stat.st_mtime, dt.timezone.utc).replace(microsecond=0).isoformat(),
            "mtime_ns": stat.st_mtime_ns,
            "sha256": sha or None,
            "disposable": disposable,
        }
        unit = unit_for(rel)
        if unit:
            row["unit"] = unit
        if derived_from:
            row["derived_from"] = derived_from
        artifacts.append(row)
        role_counts[role] += 1
        role_bytes[role] += stat.st_size
        stage_bytes[stage] += stat.st_size
        if sha:
            duplicate_groups[sha].append(rel.as_posix())
    dupes = [
        {"sha256": sha, "paths": paths, "copies": len(paths)}
        for sha, paths in sorted(duplicate_groups.items())
        if len(paths) > 1
    ]
    event_sources = [row["path"] for row in artifacts if row["role"] == "event_log"]
    view_sources = [row["path"] for row in artifacts if row["role"] == "view"]
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "artifact_catalog",
        "status": "ready",
        "generated_at": now_iso(),
        "project": identity,
        "summary": {
            "artifact_count": len(artifacts),
            "total_bytes": sum(role_bytes.values()),
            "disposable_bytes": sum(row["size_bytes"] for row in artifacts if row["disposable"]),
            "invalid_count": role_counts.get("invalid", 0),
            "by_role": {key: {"count": role_counts[key], "bytes": role_bytes[key]} for key in sorted(role_counts)},
            "by_stage_bytes": dict(sorted(stage_bytes.items())),
            "duplicate_group_count": len(dupes),
        },
        "event_sources": event_sources,
        "view_sources": view_sources,
        "artifacts": artifacts,
        "duplicates": dupes,
    }


def absolute_path_hits(root: Path) -> List[str]:
    hits: List[str] = []
    for path in iter_files(root):
        if path.suffix.lower() not in TEXT_EXTS or path.stat().st_size > 4 * 1024 * 1024:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if ABS_PATH_RE.search(text):
            hits.append(path.relative_to(root).as_posix())
    return hits


def doctor(root: Path, *, line: Optional[str] = None) -> Dict[str, Any]:
    catalog = build_catalog(root, line=line, hash_mode="metadata")
    issues: List[Dict[str, Any]] = []
    meta = load_json(root / "_meta.json", {})
    if not isinstance(meta, Mapping):
        issues.append({"code": "missing_or_invalid_meta", "severity": "warn", "path": "_meta.json"})
    else:
        for key in ("project_id", "line", "title"):
            if not meta.get(key):
                issues.append({"code": f"meta_missing_{key}", "severity": "warn", "path": "_meta.json"})
    for row in catalog["artifacts"]:
        if row["role"] == "invalid":
            issues.append({"code": "zero_byte_legacy_voice", "severity": "block", "path": row["path"]})
    legacy_timeline = [
        row["path"] for row in catalog["artifacts"]
        if re.search(r"^合成/第\d+集/_work/(?:timeline\.json|editorial_timeline\.otio|animatic_timeline\.otio)$", row["path"])
    ]
    for rel in legacy_timeline:
        issues.append({"code": "durable_evidence_in_work_cache", "severity": "warn", "path": rel})
    for rel in absolute_path_hits(root):
        issues.append({"code": "persisted_absolute_path", "severity": "warn", "path": rel})
    derived = [row for row in catalog["artifacts"] if row["role"] == "view" and row.get("derived_from")]
    if derived:
        issues.append({
            "code": "derived_view_twins",
            "severity": "info",
            "count": len(derived),
            "paths": [row["path"] for row in derived[:20]],
        })
    legacy_qc = [
        row for row in catalog["artifacts"]
        if re.search(r"^生产数据/video_qc/第\d+集/(?!_frames/).+/frames/.+\.jpg$", row["path"])
    ]
    if legacy_qc:
        issues.append({"code": "legacy_batch_local_qc_frames", "severity": "warn", "count": len(legacy_qc)})
    catalog_path = root / CATALOG_REL
    if not catalog_path.is_file():
        issues.append({"code": "catalog_missing", "severity": "warn", "path": CATALOG_REL.as_posix()})
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "artifact_catalog_doctor",
        "generated_at": now_iso(),
        "project": catalog["project"],
        "status": "block" if any(row["severity"] == "block" for row in issues) else ("warn" if issues else "pass"),
        "summary": {
            "issues": len(issues),
            "blocks": sum(row["severity"] == "block" for row in issues),
            "warnings": sum(row["severity"] == "warn" for row in issues),
            "infos": sum(row["severity"] == "info" for row in issues),
        },
        "issues": issues,
    }


def move_plan(root: Path) -> List[Dict[str, str]]:
    operations: List[Dict[str, str]] = []
    compose = root / "合成"
    for work in sorted(compose.glob("第*集/_work")) if compose.is_dir() else []:
        ep = work.parent.name
        target = root / "生产数据" / "timelines" / ep
        for name in ("timeline.json", "editorial_timeline.otio", "animatic_timeline.otio"):
            src = work / name
            if src.is_file():
                operations.append({"action": "move", "source": src.relative_to(root).as_posix(), "target": (target / name).relative_to(root).as_posix()})
        preview = work.parent / "rough_cut_preview.html"
        if preview.is_file():
            operations.append({"action": "move", "source": preview.relative_to(root).as_posix(), "target": f"生产数据/views/rough_cut_preview_{ep}.html"})
    # Voice cleanup must not depend on an episode having a compose work cache.
    # Old projects can contain only `合成/第N集/配音/Clip*_voice.*`.
    for voice in sorted(compose.glob("第*集/配音")) if compose.is_dir() else []:
        for path in sorted(voice.glob("Clip*_voice.*")):
            if path.is_file() and path.stat().st_size == 0 and ZERO_VOICE_RE.match(path.name):
                operations.append({"action": "delete_zero_placeholder", "source": path.relative_to(root).as_posix(), "target": ""})
    return operations


def merge_meta(root: Path, identity: Mapping[str, Any]) -> None:
    path = root / "_meta.json"
    data = load_json(path, {})
    data = dict(data) if isinstance(data, Mapping) else {}
    data.setdefault("schema_version", 1)
    data.setdefault("kind", f"{identity['line']}_project")
    data.setdefault("project_id", identity["project_id"])
    data.setdefault("line", identity["line"])
    data.setdefault("title", identity["title"])
    data["updated_at"] = now_iso()
    data.setdefault("created_at", data["updated_at"])
    write_json_atomic(path, data)


def same_file(a: Path, b: Path) -> bool:
    return a.stat().st_size == b.stat().st_size and sha256_file(a) == sha256_file(b)


def update_legacy_references(root: Path, ep: str) -> None:
    replacements = {
        f"合成/{ep}/_work/timeline.json": f"生产数据/timelines/{ep}/timeline.json",
        f"合成/{ep}/_work/editorial_timeline.otio": f"生产数据/timelines/{ep}/editorial_timeline.otio",
        f"合成/{ep}/_work/animatic_timeline.otio": f"生产数据/timelines/{ep}/animatic_timeline.otio",
        f"合成/{ep}/rough_cut_preview.html": f"生产数据/views/rough_cut_preview_{ep}.html",
    }
    candidates = [
        root / "生产数据" / f"editorial_timeline_{ep}.json",
        root / "生产数据" / f"final_timeline_probe_{ep}.json",
    ]
    for path in candidates:
        data = load_json(path)
        if not isinstance(data, (dict, list)):
            continue
        text = json.dumps(data, ensure_ascii=False)
        changed = False
        for old, new in replacements.items():
            if old in text:
                text = text.replace(old, new)
                changed = True
        if changed:
            write_json_atomic(path, json.loads(text))


def migrate(root: Path, *, line: Optional[str], apply: bool) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    identity = project_identity(root, line)
    operations = [{"action": "merge_project_identity", "source": "_meta.json", "target": "_meta.json"}] + move_plan(root)
    operations.append({"action": "rebuild_catalog", "source": "", "target": CATALOG_REL.as_posix()})
    applied: List[Dict[str, str]] = []
    conflicts: List[Dict[str, str]] = []
    if apply:
        merge_meta(root, identity)
        applied.append(operations[0])
        touched_eps = set()
        for op in operations[1:-1]:
            src = root / op["source"]
            if op["action"] == "delete_zero_placeholder":
                if src.is_file() and src.stat().st_size == 0 and ZERO_VOICE_RE.match(src.name):
                    src.unlink()
                    applied.append(op)
                continue
            dst = root / op["target"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                if src.is_file() and dst.is_file() and same_file(src, dst):
                    src.unlink()
                    applied.append(op)
                else:
                    conflicts.append(op)
                continue
            shutil.move(str(src), str(dst))
            applied.append(op)
            match = re.search(r"(第\d+集)", op["target"])
            if match:
                touched_eps.add(match.group(1))
        for ep in sorted(touched_eps):
            update_legacy_references(root, ep)
        write_json_atomic(root / CATALOG_REL, build_catalog(root, line=line, hash_mode="full"))
        applied.append(operations[-1])
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "artifact_catalog_migration",
        "generated_at": now_iso(),
        "project": identity,
        "mode": "apply" if apply else "dry_run",
        "status": "conflict" if conflicts else "ready",
        "operations": operations,
        "applied": applied,
        "conflicts": conflicts,
    }


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("build", "doctor", "migrate"):
        p = sub.add_parser(name)
        p.add_argument("root")
        p.add_argument("--line", choices=sorted(set(LINE_DIRS.values())))
        p.add_argument("--json", action="store_true")
        if name == "build":
            p.add_argument("--write", action="store_true")
            p.add_argument("--hash-mode", choices=("full", "metadata", "none"), default="full")
        if name == "migrate":
            p.add_argument("--apply", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root).expanduser().resolve()
    if not root.is_dir():
        print(f"not a project directory: {root}", file=sys.stderr)
        return 2
    if ns.command == "build":
        payload = build_catalog(root, line=ns.line, hash_mode=ns.hash_mode)
        if ns.write:
            write_json_atomic(root / CATALOG_REL, payload)
    elif ns.command == "doctor":
        payload = doctor(root, line=ns.line)
    else:
        payload = migrate(root, line=ns.line, apply=ns.apply)
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{payload['kind']}: {payload.get('status', 'ready')} — {root}")
        if ns.command == "doctor":
            for issue in payload["issues"]:
                suffix = f" {issue.get('path')}" if issue.get("path") else f" count={issue.get('count', 0)}"
                print(f"  {issue['severity']}: {issue['code']}{suffix}")
        elif ns.command == "migrate":
            for op in payload["operations"]:
                arrow = f" -> {op['target']}" if op.get("target") else ""
                print(f"  {op['action']}: {op.get('source', '')}{arrow}")
        elif getattr(ns, "write", False):
            print(f"  wrote {CATALOG_REL.as_posix()} ({payload['summary']['artifact_count']} artifacts)")
    if ns.command == "doctor" and payload["status"] == "block":
        return 2
    if ns.command == "migrate" and payload["status"] == "conflict":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
