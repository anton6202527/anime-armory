#!/usr/bin/env python3
"""Build/check per-asset generation recipe manifests for n2d releases."""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from n2d_const import GENERATION_RECIPE_MANIFEST_KIND, PRODUCTION_DIR  # noqa: E402


VERSION = 1
MANIFEST_JSON = "generation_recipe_manifest_{episode}.json"
MANIFEST_MD = "generation_recipe_manifest_{episode}.md"
RECIPE_EVIDENCE_STAGES = {"image", "video"}
RECIPE_REQUIRED_FIELDS = (
    "provider",
    "model",
    "channel",
    "route_hash",
    "capability_evidence_id",
    "recipe_hash",
    "prompt_sha256",
    "reference_bundle_sha256",
    "backend_version",
    "quality_tier",
    "actual_image_inputs",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def production_dir(root: Path) -> Path:
    return root / PRODUCTION_DIR


def manifest_path(root: Path, episode: str) -> Path:
    return production_dir(root) / MANIFEST_JSON.format(episode=episode)


def manifest_md_path(root: Path, episode: str) -> Path:
    return production_dir(root) / MANIFEST_MD.format(episode=episode)


def events_path(root: Path) -> Path:
    return production_dir(root) / "production_events.jsonl"


def relpath(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def norm_rel(path: str) -> str:
    return os.path.normpath(str(path or "").strip()).replace(os.sep, "/")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_events(root: Path) -> List[Tuple[int, Dict[str, Any]]]:
    path = events_path(root)
    if not path.is_file():
        return []
    out: List[Tuple[int, Dict[str, Any]]] = []
    with path.open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            if isinstance(item, dict):
                out.append((lineno, item))
    return out


def nested(event: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = event.get(key)
    return value if isinstance(value, Mapping) else {}


def event_value_any(event: Mapping[str, Any], *keys: str) -> Any:
    sources = (event, nested(event, "generation"), nested(event, "meta"), nested(event, "cost"))
    for key in keys:
        for source in sources:
            value = source.get(key) if isinstance(source, Mapping) else None
            if value not in (None, "", [], {}):
                return value
    return ""


def event_status_pass(event: Mapping[str, Any]) -> bool:
    generation = nested(event, "generation")
    status = str(generation.get("status") or event.get("status") or "").strip().lower()
    return status in {"", "pass", "passed", "ok", "success", "succeeded", "done", "ready"}


def event_asset_rel(root: Path, event: Mapping[str, Any]) -> str:
    generation = nested(event, "generation")
    raw = str(generation.get("asset") or event.get("asset") or "").strip()
    if not raw:
        return ""
    if os.path.isabs(raw):
        try:
            return Path(raw).resolve().relative_to(root.resolve()).as_posix()
        except Exception:
            pass
    # Production events may survive project moves or machine-user changes.  If an
    # event still contains ".../<project-name>/出视频/..." or a relative path with
    # the workspace prefix, recover the project-local suffix so manifests remain
    # portable across checkouts.
    parts = Path(raw).parts
    root_name = root.name
    if root_name in parts:
        idx = len(parts) - 1 - list(reversed(parts)).index(root_name)
        tail = parts[idx + 1 :]
        if tail:
            return norm_rel(os.path.join(*tail))
    return norm_rel(raw)


def final_media_rels(root: Path, episode: str) -> List[str]:
    rels: List[str] = []
    for pattern in (
        root / "出图" / episode / "图片" / "*.png",
        root / "出视频" / episode / "视频" / "*.mp4",
    ):
        for raw in glob.glob(str(pattern)):
            rels.append(relpath(root, Path(raw)))
    return sorted(set(rels))


def stage_for_asset(rel: str, event: Optional[Mapping[str, Any]] = None) -> str:
    if event:
        stage = str(event.get("stage") or "").strip()
        if stage:
            return stage
    return "image" if rel.lower().endswith(".png") else "video"


def missing_recipe_fields(event: Mapping[str, Any]) -> List[str]:
    missing = [key for key in RECIPE_REQUIRED_FIELDS if event_value_any(event, key) in (None, "", [], {})]
    seed_effective = event_value_any(event, "seed_effective", "effective_seed")
    if seed_effective in (None, "", [], {}):
        missing.append("seed_effective")
    else:
        seed_text = str(seed_effective).strip().lower()
        if seed_text in {"true", "1", "yes", "supported", "pass"} and event_value_any(event, "effective_seed") in (None, "", [], {}):
            missing.append("effective_seed")
        if seed_text in {"false", "0", "no", "none", "unsupported", "unsupported_or_unknown"} and event_value_any(event, "seed_support") in (None, "", [], {}):
            missing.append("seed_support")
    return missing


def latest_generation_events(root: Path, episode: str) -> Dict[str, Tuple[int, Dict[str, Any]]]:
    latest: Dict[str, Tuple[int, Dict[str, Any]]] = {}
    for lineno, event in load_events(root):
        if str(event.get("episode") or "").strip() != episode:
            continue
        if str(event.get("stage") or "").strip() not in RECIPE_EVIDENCE_STAGES:
            continue
        if str(event.get("event") or "").strip() not in {"generation", "redraw"}:
            continue
        if not event_status_pass(event):
            continue
        rel = event_asset_rel(root, event)
        if rel:
            latest[rel] = (lineno, event)
    return latest


def record_hash(record: Mapping[str, Any]) -> str:
    scope = {
        key: record.get(key)
        for key in (
            "asset",
            "stage",
            "provider",
            "model",
            "channel",
            "route_hash",
            "capability_evidence_id",
            "recipe_hash",
            "prompt_sha256",
            "reference_bundle_sha256",
            "backend_version",
            "quality_tier",
            "output_sha256",
            "seed_effective",
            "seed_support",
            "effective_seed",
        )
    }
    return hashlib.sha256(json.dumps(scope, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def recipe_record(root: Path, rel: str, event_row: Optional[Tuple[int, Mapping[str, Any]]]) -> Dict[str, Any]:
    event = dict(event_row[1]) if event_row else {}
    lineno = event_row[0] if event_row else 0
    path = root / rel
    missing = missing_recipe_fields(event) if event else ["generation_event"]
    record: Dict[str, Any] = {
        "asset": rel,
        "stage": stage_for_asset(rel, event),
        "source": f"{relpath(root, events_path(root))}:line {lineno}" if lineno else "",
        "exists": path.is_file(),
        "output_sha256": sha256_file(path) if path.is_file() else "",
        "output_bytes": path.stat().st_size if path.is_file() else 0,
        "provider": event_value_any(event, "provider"),
        "model": event_value_any(event, "model"),
        "channel": event_value_any(event, "channel"),
        "route_hash": event_value_any(event, "route_hash"),
        "capability_evidence_id": event_value_any(event, "capability_evidence_id"),
        "recipe_hash": event_value_any(event, "recipe_hash"),
        "prompt_sha256": event_value_any(event, "prompt_sha256"),
        "reference_bundle_sha256": event_value_any(event, "reference_bundle_sha256"),
        "backend_version": event_value_any(event, "backend_version"),
        "quality_tier": event_value_any(event, "quality_tier"),
        "actual_image_inputs": event_value_any(event, "actual_image_inputs"),
        "requested_seed": event_value_any(event, "requested_seed"),
        "effective_seed": event_value_any(event, "effective_seed"),
        "seed_effective": event_value_any(event, "seed_effective"),
        "seed_support": event_value_any(event, "seed_support"),
        "trace": event.get("trace") if isinstance(event.get("trace"), dict) else {},
        "cost": event.get("cost") if isinstance(event.get("cost"), dict) else {},
        "missing_fields": missing,
        "status": "fail" if missing or not path.is_file() else "pass",
    }
    if not path.is_file():
        record["missing_fields"] = sorted(set(list(record["missing_fields"]) + ["output_asset"]))
    record["recipe_record_hash"] = record_hash(record)
    return record


def build_manifest(root: Path, episode: str) -> Dict[str, Any]:
    root = root.resolve()
    latest = latest_generation_events(root, episode)
    targets = final_media_rels(root, episode) or sorted(latest)
    records = [recipe_record(root, rel, latest.get(rel)) for rel in targets]
    missing_events = sum(1 for item in records if "generation_event" in (item.get("missing_fields") or []))
    missing_fields = sum(len(item.get("missing_fields") or []) for item in records)
    failed = [item for item in records if item.get("status") != "pass"]
    payload = {
        "kind": GENERATION_RECIPE_MANIFEST_KIND,
        "version": VERSION,
        "root": str(root),
        "episode": episode,
        "generated_at": now_iso(),
        "source_events": relpath(root, events_path(root)),
        "records": records,
        "summary": {
            "records": len(records),
            "missing_events": missing_events,
            "missing_fields": missing_fields,
            "failed_records": len(failed),
        },
        "status": "fail" if failed else "pass",
    }
    payload["manifest_id"] = hashlib.sha256(
        json.dumps(
            {"episode": episode, "records": [item.get("recipe_record_hash") for item in records]},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]
    return payload


def render_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# n2d Generation Recipe Manifest",
        "",
        f"- 集：{payload.get('episode')}",
        f"- 状态：{payload.get('status')}",
        f"- 记录数：{summary.get('records', 0)}",
        f"- 失败记录：{summary.get('failed_records', 0)}",
        "",
        "| asset | stage | status | missing | source |",
        "|---|---|---|---|---|",
    ]
    for item in payload.get("records") or []:
        missing = ",".join(str(x) for x in (item.get("missing_fields") or [])) or "-"
        lines.append(f"| `{item.get('asset')}` | {item.get('stage')} | {item.get('status')} | {missing} | `{item.get('source') or '-'}` |")
    lines.append("")
    return "\n".join(lines)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_manifest(root: Path, episode: str, payload: Dict[str, Any]) -> Path:
    path = manifest_path(root, episode)
    atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    atomic_write(manifest_md_path(root, episode), render_markdown(payload))
    return path


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def check_manifest(root: Path, episode: str) -> Dict[str, Any]:
    path = manifest_path(root, episode)
    data = load_json(path)
    if not isinstance(data, dict) or data.get("kind") != GENERATION_RECIPE_MANIFEST_KIND:
        return {"status": "fail", "issues": [f"missing or invalid {path}"], "path": str(path)}
    issues: List[str] = []
    if data.get("episode") != episode:
        issues.append(f"episode mismatch: {data.get('episode')} != {episode}")
    if data.get("status") != "pass":
        issues.append(f"manifest status is {data.get('status')}")
    for item in data.get("records") or []:
        if not isinstance(item, dict):
            continue
        rel = str(item.get("asset") or "")
        if item.get("status") != "pass":
            issues.append(f"recipe record failed: {rel or '<unknown>'}")
        if not rel:
            issues.append("recipe record missing asset")
            continue
        asset = root / rel
        if not asset.is_file():
            issues.append(f"recipe asset missing: {rel}")
        elif item.get("output_sha256") and item.get("output_sha256") != sha256_file(asset):
            issues.append(f"recipe asset sha256 mismatch: {rel}")
    return {"status": "fail" if issues else "pass", "issues": issues, "path": str(path)}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="build/check n2d generation recipe manifest")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build")
    p.add_argument("root")
    p.add_argument("episode")
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
        payload = build_manifest(root, ns.episode)
        if ns.write:
            path = write_manifest(root, ns.episode, payload)
            payload["path"] = str(path)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_markdown(payload))
        return 1 if payload.get("status") != "pass" else 0
    result = check_manifest(root, ns.episode)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else "\n".join(result.get("issues") or ["generation recipe manifest ok"]))
    return 1 if result.get("status") != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
