#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""漫画共享定妆、引用绑定和一致性重抽计划。"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


PNG_SIG = b"\x89PNG\r\n\x1a\n"
REQUIRED_CHARACTER_VIEWS = ("front", "three_quarter", "side", "back", "face")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def png_valid(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 64 and path.read_bytes()[:8] == PNG_SIG
    except OSError:
        return False


def rel_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def resolve_path(root: Path, raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else root / path


def registry_path(root: Path) -> Path:
    return root / "出图" / "共享" / "identity_registry.json"


def jobs_path(root: Path, chapter: str) -> Path:
    return root / "出图" / chapter / "prompt" / "panel_jobs.json"


def load_registry(root: Path) -> dict:
    path = registry_path(root)
    if path.is_file():
        data = load_json(path)
        if isinstance(data, dict):
            data.setdefault("schema_version", 1)
            data.setdefault("kind", "comic_identity_registry")
            data.setdefault("assets", {})
            return data
    return {"schema_version": 1, "kind": "comic_identity_registry", "assets": {}}


def ref_type(ref_id: str) -> str:
    prefix = ref_id.split("_", 1)[0]
    return {
        "CHAR": "character",
        "MON": "monster",
        "LOC": "location",
        "PROP": "prop",
        "SYS": "system_asset",
        "VFX": "vfx",
        "OUTFIT": "outfit",
    }.get(prefix, "asset")


def parse_map(items: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--map must be REF_ID=PANEL_ID_OR_PATH, got: {item}")
        rid, src = item.split("=", 1)
        rid = rid.strip()
        src = src.strip()
        if not rid or not src:
            raise SystemExit(f"--map must be REF_ID=PANEL_ID_OR_PATH, got: {item}")
        out[rid] = src
    return out


def panel_lookup(root: Path, chapter: str, jobs: dict) -> dict[str, Path]:
    panels: dict[str, Path] = {}
    for job in jobs.get("jobs") or []:
        pid = str(job.get("panel_id") or "")
        rel = str(job.get("result_path") or "")
        if pid and rel:
            panels[pid] = resolve_path(root, rel)
        if pid and pid not in panels:
            panels[pid] = root / "出图" / chapter / "panels" / f"{pid}.png"
    return panels


def source_path(root: Path, chapter: str, panels: dict[str, Path], raw: str) -> Path:
    if raw in panels:
        return panels[raw]
    path = Path(raw)
    if not path.is_absolute():
        direct = root / path
        if direct.is_file():
            return direct
        panel = root / "出图" / chapter / "panels" / raw
        if panel.is_file():
            return panel
    return path


def resolve_reference_path(root: Path, ref_id: str, registry: dict) -> str:
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    asset = assets.get(ref_id) if isinstance(assets, dict) else None
    candidates: list[Path] = []
    if isinstance(asset, dict):
        for key in ("anchor_path", "primary_path", "path"):
            raw = asset.get(key)
            if isinstance(raw, str) and raw.strip():
                candidates.append(resolve_path(root, raw))
        for item in asset.get("reference_images") or []:
            raw = item.get("path") if isinstance(item, dict) else item
            if isinstance(raw, str) and raw.strip():
                candidates.append(resolve_path(root, raw))
    shared = root / "出图" / "共享" / "图片"
    for suffix in ("__anchor.png", ".png", ".jpg", ".jpeg", ".webp"):
        candidates.append(shared / f"{ref_id}{suffix}")
    for path in candidates:
        if path.is_file():
            return rel_to_root(root, path)
    return ""


def character_view_paths(root: Path, ref_id: str, registry: dict) -> dict[str, str]:
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    asset = assets.get(ref_id) if isinstance(assets, dict) else None
    found: dict[str, str] = {}
    if isinstance(asset, dict):
        for item in asset.get("reference_images") or []:
            if not isinstance(item, dict):
                continue
            view = str(item.get("view") or "").strip()
            raw = str(item.get("path") or "").strip()
            if view and raw and resolve_path(root, raw).is_file():
                found[view] = rel_to_root(root, resolve_path(root, raw))
        views = asset.get("views")
        if isinstance(views, dict):
            for view, raw in views.items():
                if isinstance(raw, str) and raw.strip() and resolve_path(root, raw).is_file():
                    found[str(view)] = rel_to_root(root, resolve_path(root, raw))
    shared = root / "出图" / "共享" / "图片"
    for view in REQUIRED_CHARACTER_VIEWS:
        for suffix in (".png", ".jpg", ".jpeg", ".webp"):
            path = shared / f"{ref_id}__{view}{suffix}"
            if path.is_file():
                found.setdefault(view, rel_to_root(root, path))
                break
    return found


def bind_job_references(root: Path, jobs: dict, registry: dict) -> int:
    changed = 0
    for job in jobs.get("jobs") or []:
        for ref in job.get("references") or []:
            if not isinstance(ref, dict):
                continue
            rid = str(ref.get("id") or "")
            if not rid:
                continue
            path = resolve_reference_path(root, rid, registry)
            if path and ref.get("path") != path:
                ref["path"] = path
                changed += 1
    return changed


def write_reference_index(root: Path, chapter: str, jobs: dict) -> None:
    refs: dict[str, dict[str, object]] = {}
    for job in jobs.get("jobs", []):
        for ref in job.get("references", []):
            rid = ref.get("id")
            if rid:
                item = refs.setdefault(rid, {"count": 0, "path": ""})
                item["count"] = int(item.get("count") or 0) + 1
                if ref.get("path"):
                    item["path"] = ref.get("path")
    lines = [
        f"# 共享参考任务索引 — {chapter}",
        "",
        "正式逐格出图前，先补齐这些角色、场景、道具或特效参考。",
        "",
        "| ref_id | 出现次数 | 状态 | 建议 |",
        "|---|---:|---|---|",
    ]
    for rid, item in sorted(refs.items()):
        count = int(item.get("count") or 0)
        path = str(item.get("path") or "")
        if path:
            lines.append(f"| {rid} | {count} | ✅ | `{path}` |")
        else:
            lines.append(f"| {rid} | {count} | ⬜ | 生成或放入 `出图/共享/图片/` 后回填 panel_jobs.json |")
    if not refs:
        lines.append("| （无） | 0 | - | 当前脚本未声明 references |")
    path = root / "出图" / "共享" / "prompt" / "00_索引.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_event(root: Path, row: dict[str, Any]) -> None:
    path = root / "生产数据" / "comic_image_generation.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def seed(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    chapter = args.chapter
    jobs = load_json(jobs_path(root, chapter))
    mapping = parse_map(args.map)
    if not mapping:
        raise SystemExit("provide at least one --map REF_ID=PANEL_ID_OR_PATH")

    registry = load_registry(root)
    assets = registry.setdefault("assets", {})
    if not isinstance(assets, dict):
        raise SystemExit("identity_registry.json assets must be an object")

    panels = panel_lookup(root, chapter, jobs)
    shared_dir = root / "出图" / "共享" / "图片"
    shared_dir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now().isoformat(timespec="seconds")
    seeded: dict[str, str] = {}
    for rid, raw in mapping.items():
        src = source_path(root, chapter, panels, raw)
        if not png_valid(src):
            raise SystemExit(f"source for {rid} is not a valid PNG: {src}")
        dest = shared_dir / f"{rid}__anchor.png"
        if dest.exists() and not args.overwrite:
            raise SystemExit(f"{dest} already exists; pass --overwrite to replace it")
        shutil.copy2(src, dest)
        rel = rel_to_root(root, dest)
        seeded[rid] = rel
        assets[rid] = {
            **(assets.get(rid) if isinstance(assets.get(rid), dict) else {}),
            "id": rid,
            "type": ref_type(rid),
            "status": "ready",
            "anchor_path": rel,
            "source": {
                "kind": "accepted_panel_anchor",
                "chapter": chapter,
                "source": raw,
                "source_path": rel_to_root(root, src),
            },
            "sha256": file_sha256(dest),
            "updated_at": now,
            "notes": "Shared anchor seeded from an accepted comic panel; replace with dedicated turnaround/design-sheet art when available.",
        }
        append_event(root, {
            "ts": now,
            "status": "reference_anchor_ready",
            "ref_id": rid,
            "path": rel,
            "source": raw,
            "sha256": assets[rid]["sha256"],
        })

    write_json(registry_path(root), registry)
    changed = bind_job_references(root, jobs, registry)
    write_json(jobs_path(root, chapter), jobs)
    write_reference_index(root, chapter, jobs)
    print(f"[ok] seeded {len(seeded)} anchors; updated {changed} job references")
    return 0


def job_reference_status(root: Path, job: dict[str, Any]) -> tuple[list[str], list[dict[str, str]]]:
    missing: list[str] = []
    valid: list[dict[str, str]] = []
    seen: set[str] = set()
    for ref in job.get("references") or []:
        if not isinstance(ref, dict):
            continue
        rid = str(ref.get("id") or "").strip()
        raw = str(ref.get("path") or "").strip()
        if not rid:
            continue
        if not raw:
            missing.append(rid)
            continue
        path = resolve_path(root, raw)
        if not path.is_file():
            missing.append(rid)
            continue
        rel = rel_to_root(root, path)
        if rel in seen:
            continue
        seen.add(rel)
        valid.append({"id": rid, "path": rel, "sha256": file_sha256(path)})
    return missing, valid


def report_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# 漫画一致性报告 — {report['chapter']}",
        "",
        f"- 生成时间：{report['created_at']}",
        f"- reference 总数：{report['summary']['reference_count']}",
        f"- 缺失 reference：{len(report['missing_refs'])}",
        f"- 需要重抽格：{len(report['rerun_targets'])}",
        "",
    ]
    if report["missing_refs"]:
        lines += ["## 缺失 Reference", "", "| ref_id | 出现格 |", "|---|---|"]
        for rid, panels in sorted(report["missing_refs"].items()):
            lines.append(f"| {rid} | {', '.join(panels)} |")
        lines.append("")
    if report["rerun_targets"]:
        lines += ["## 重抽目标", "", "| panel | reason | valid_refs |", "|---|---|---:|"]
        panels_by_id = {item["panel_id"]: item for item in report["panels"]}
        for pid in report["rerun_targets"]:
            item = panels_by_id.get(pid, {})
            lines.append(f"| {pid} | {item.get('rerun_reason', '')} | {item.get('valid_reference_count', 0)} |")
        lines += [
            "",
            "建议命令：",
            "",
            "```bash",
            "python3 skills/comic-image/scripts/codex_panel_runner.py "
            f"\"{report['project_root']}\" --chapter {report['chapter']} "
            f"--targets {','.join(report['rerun_targets'])} --force --max-attempts 3",
            "```",
            "",
        ]
    if report.get("missing_character_views"):
        lines += ["## 人物多视图缺口", "", "| character | missing views |", "|---|---|"]
        for rid, missing in sorted(report["missing_character_views"].items()):
            lines.append(f"| {rid} | {', '.join(missing)} |")
        lines.append("")
    lines += ["## 每格状态", "", "| panel | status | refs | missing | generated_with_refs |", "|---|---|---:|---|---:|"]
    for item in report["panels"]:
        lines.append(
            f"| {item['panel_id']} | {item['status']} | {item['valid_reference_count']} | "
            f"{', '.join(item['missing_refs']) or '-'} | {item['generated_reference_input_count']} |"
        )
    return "\n".join(lines) + "\n"


def report(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    chapter = args.chapter
    jobs = load_json(jobs_path(root, chapter))
    registry = load_registry(root)
    changed = bind_job_references(root, jobs, registry) if args.write else 0
    if args.write:
        write_json(jobs_path(root, chapter), jobs)
        write_reference_index(root, chapter, jobs)

    missing_refs: dict[str, list[str]] = {}
    refs_seen: set[str] = set()
    panels: list[dict[str, Any]] = []
    rerun_targets: list[str] = []
    for job in jobs.get("jobs") or []:
        pid = str(job.get("panel_id") or "")
        missing, valid = job_reference_status(root, job)
        for ref in job.get("references") or []:
            if isinstance(ref, dict) and ref.get("id"):
                refs_seen.add(str(ref.get("id")))
        for rid in missing:
            missing_refs.setdefault(rid, []).append(pid)
        generated_count = int(job.get("reference_input_count") or 0)
        needs_rerun = False
        reason = ""
        if valid and job.get("status") == "ready" and generated_count == 0:
            needs_rerun = True
            reason = "ready panel was generated before real reference images were attached"
        elif valid and job.get("status") == "ready" and generated_count < len(valid):
            needs_rerun = True
            reason = "ready panel used fewer image references than currently bound"
        elif valid and job.get("status") == "ready" and not job.get("reference_manifest"):
            needs_rerun = True
            reason = "ready panel has no reference manifest evidence"
        if needs_rerun:
            rerun_targets.append(pid)
        panels.append(
            {
                "panel_id": pid,
                "status": job.get("status", ""),
                "valid_reference_count": len(valid),
                "valid_references": valid,
                "missing_refs": missing,
                "generated_reference_input_count": generated_count,
                "reference_manifest": job.get("reference_manifest", ""),
                "needs_rerun": needs_rerun,
                "rerun_reason": reason,
            }
        )

    registry_assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    char_ids = sorted(rid for rid in refs_seen | set(registry_assets.keys()) if rid.startswith("CHAR_"))
    missing_character_views: dict[str, list[str]] = {}
    character_views: dict[str, dict[str, str]] = {}
    for rid in char_ids:
        views = character_view_paths(root, rid, registry)
        character_views[rid] = views
        missing = [view for view in REQUIRED_CHARACTER_VIEWS if view not in views]
        if missing:
            missing_character_views[rid] = missing

    payload = {
        "schema_version": 1,
        "kind": "comic_identity_report",
        "project_root": str(root),
        "chapter": chapter,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "write_back": bool(args.write),
        "job_reference_paths_updated": changed,
        "summary": {
            "reference_count": len(refs_seen),
            "panel_count": len(panels),
            "missing_ref_count": len(missing_refs),
            "rerun_target_count": len(rerun_targets),
        },
        "missing_refs": missing_refs,
        "required_character_views": list(REQUIRED_CHARACTER_VIEWS),
        "character_views": character_views,
        "missing_character_views": missing_character_views,
        "rerun_targets": rerun_targets,
        "panels": panels,
    }
    out_json = root / "生产数据" / f"comic_identity_report_{chapter}.json"
    out_md = root / "生产数据" / f"comic_identity_report_{chapter}.md"
    write_json(out_json, payload)
    out_md.write_text(report_markdown(payload), encoding="utf-8")
    print(f"[ok] report: {out_json}")
    if missing_refs:
        print("[warn] missing refs: " + ", ".join(sorted(missing_refs)))
    if rerun_targets:
        print("[plan] rerun targets: " + ",".join(rerun_targets))
    else:
        print("[ok] no rerun targets")
    if missing_character_views:
        print("[warn] missing character views: " + ", ".join(f"{rid}({','.join(views)})" for rid, views in sorted(missing_character_views.items())))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="漫画共享定妆与一致性工具")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    sub = parser.add_subparsers(dest="command", required=True)

    p_seed = sub.add_parser("seed", help="从面板图种共享锚点")
    p_seed.add_argument("--map", action="append", default=[], help="REF_ID=PANEL_ID_OR_PATH，可重复")
    p_seed.add_argument("--overwrite", action="store_true")
    p_seed.set_defaults(func=seed)

    p_report = sub.add_parser("report", help="生成一致性报告与重抽计划")
    p_report.add_argument("--write", action="store_true", help="回填 panel_jobs.json 中可解析的 reference path")
    p_report.set_defaults(func=report)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
