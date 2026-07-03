#!/usr/bin/env python3
"""Content-addressed asset registry for n2d projects."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


KIND = "n2d_asset_registry"
REGISTRY_JSONL = "asset_registry.jsonl"
SUMMARY_JSON = "asset_registry_summary.json"
SUMMARY_MD = "asset_registry_summary.md"
DEFAULT_DIRS = ("出图", "出视频", "合成", "脚本", "合规")
ASSET_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".wav", ".mp3", ".srt", ".json", ".md"}


def production_dir(root: str) -> Path:
    return Path(root) / "生产数据"


def registry_path(root: str) -> Path:
    return production_dir(root) / REGISTRY_JSONL


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relpath(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def stage_for_path(rel: str) -> str:
    if rel.startswith("出图/"):
        return "image"
    if rel.startswith("出视频/"):
        return "video"
    if rel.startswith("合成/"):
        return "compose"
    if rel.startswith("脚本/"):
        return "script"
    if rel.startswith("合规/"):
        return "compliance"
    if rel.startswith("生产数据/"):
        return "production_data"
    return "unknown"


def load_generation_events(root: Path) -> Dict[str, List[Dict[str, Any]]]:
    path = root / "生产数据" / "production_events.jsonl"
    out: Dict[str, List[Dict[str, Any]]] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        gen = event.get("generation") if isinstance(event.get("generation"), dict) else {}
        asset = str(gen.get("asset") or event.get("asset") or "").strip()
        if asset:
            out.setdefault(asset.replace("\\", "/"), []).append({
                "episode": event.get("episode"),
                "stage": event.get("stage"),
                "event": event.get("event"),
                "provider": (event.get("cost") or {}).get("provider") if isinstance(event.get("cost"), dict) else "",
                "ts": event.get("ts"),
            })
    return out


def iter_assets(root: Path, *, include_production_data: bool = False) -> Iterable[Path]:
    dirs = list(DEFAULT_DIRS)
    if include_production_data:
        dirs.append("生产数据")
    for dirname in dirs:
        base = root / dirname
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if ".tmp." in path.name or path.name.startswith("."):
                continue
            if path.suffix.lower() not in ASSET_SUFFIXES:
                continue
            if path.name in {REGISTRY_JSONL, SUMMARY_JSON, SUMMARY_MD}:
                continue
            yield path


def scan(root: str, *, include_production_data: bool = False) -> List[Dict[str, Any]]:
    root_path = Path(root).resolve()
    events = load_generation_events(root_path)
    rows: List[Dict[str, Any]] = []
    for path in sorted(iter_assets(root_path, include_production_data=include_production_data)):
        rel = relpath(root_path, path)
        rows.append({
            "kind": KIND,
            "version": 1,
            "path": rel,
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "stage": stage_for_path(rel),
            "suffix": path.suffix.lower(),
            "generation_events": events.get(rel, []),
        })
    return rows


def summarize(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    by_stage: Dict[str, int] = {}
    total_bytes = 0
    hashes: Dict[str, List[str]] = {}
    for row in rows:
        by_stage[row["stage"]] = by_stage.get(row["stage"], 0) + 1
        total_bytes += int(row.get("bytes") or 0)
        hashes.setdefault(str(row.get("sha256")), []).append(str(row.get("path")))
    duplicates = {h: paths for h, paths in hashes.items() if len(paths) > 1}
    return {
        "kind": "n2d_asset_registry_summary",
        "version": 1,
        "total": len(rows),
        "total_bytes": total_bytes,
        "by_stage": by_stage,
        "duplicate_hashes": duplicates,
    }


def write_registry(root: str, rows: Sequence[Dict[str, Any]]) -> None:
    pdir = production_dir(root)
    pdir.mkdir(parents=True, exist_ok=True)
    registry_path(root).write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    summary = summarize(rows)
    (pdir / SUMMARY_JSON).write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (pdir / SUMMARY_MD).write_text(render_summary(summary), encoding="utf-8")


def load_registry(root: str) -> List[Dict[str, Any]]:
    path = registry_path(root)
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
    return rows


def verify(root: str) -> Dict[str, Any]:
    rows = load_registry(root)
    root_path = Path(root).resolve()
    issues = []
    for row in rows:
        path = root_path / str(row.get("path") or "")
        if not path.is_file():
            issues.append({"path": row.get("path"), "issue": "missing"})
            continue
        current = sha256_file(path)
        if current != row.get("sha256"):
            issues.append({"path": row.get("path"), "issue": "sha256_mismatch", "was": row.get("sha256"), "now": current})
    return {
        "kind": "n2d_asset_registry_verify",
        "version": 1,
        "status": "fail" if issues else "pass",
        "checked": len(rows),
        "issues": issues,
    }


def render_summary(summary: Dict[str, Any]) -> str:
    lines = [
        "# n2d 资产内容账本",
        "",
        f"- 资产数：{summary.get('total', 0)}",
        f"- 总字节：{summary.get('total_bytes', 0)}",
        "",
        "## Stage",
        "",
        "| stage | count |",
        "|---|---:|",
    ]
    for stage, count in sorted((summary.get("by_stage") or {}).items()):
        lines.append(f"| {stage} | {count} |")
    lines.append("")
    return "\n".join(lines)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="n2d content-addressed asset registry")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("scan")
    p.add_argument("root")
    p.add_argument("--include-production-data", action="store_true")
    p.add_argument("--write", action="store_true")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("verify")
    p.add_argument("root")
    p.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    if ns.cmd == "scan":
        rows = scan(ns.root, include_production_data=ns.include_production_data)
        if ns.write:
            write_registry(ns.root, rows)
        payload: Any = {"summary": summarize(rows), "rows": rows} if ns.json else summarize(rows)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_summary(payload))
        return 0
    payload = verify(ns.root)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload.get("status") != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
