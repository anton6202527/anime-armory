#!/usr/bin/env python3
"""Build and compare the comic line's panel-level production dependencies.

The index is a derived control-plane artifact.  It never replaces panel jobs,
layout, lettering, or gate receipts; it only explains which panels/pages have
to be reconsidered after a project input changes in place.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


KIND = "comic_panel_dependency_index"
VERSION = 1


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _sha_bytes(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _sha_file(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_path(root: Path, raw: Any) -> Path | None:
    text = str(raw or "").strip()
    if not text or "://" in text or text.startswith("data:"):
        return None
    path = Path(text).expanduser()
    candidate = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _chapter_names(root: Path) -> list[str]:
    names: set[str] = set()
    for base in (root / "脚本", root / "排版", root / "出图"):
        if not base.is_dir():
            continue
        for child in base.iterdir():
            if child.is_dir() and child.name.startswith("第") and child.name.endswith("话"):
                names.add(child.name)
    return sorted(names)


def _layout_membership(layout: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    layout_shared = {key: value for key, value in layout.items() if key != "segments"}
    for segment_index, segment in enumerate(layout.get("segments") or []):
        if not isinstance(segment, Mapping):
            continue
        segment_id = str(segment.get("segment_id") or segment.get("page_id") or f"segment_{segment_index + 1}")
        page_id = str(segment.get("page_id") or segment.get("page") or segment_id)
        segment_contract = {key: value for key, value in segment.items() if key != "panels"}
        for panel in segment.get("panels") or []:
            if not isinstance(panel, Mapping) or not panel.get("panel_id"):
                continue
            result[str(panel["panel_id"])] = {
                "segment_id": segment_id,
                "page_id": page_id,
                "panel_geometry_sha256": _sha_bytes(panel),
                "segment_contract_sha256": _sha_bytes(segment_contract),
                "layout_shared_sha256": _sha_bytes(layout_shared),
            }
    return result


def _lettering_by_panel(lettering: Mapping[str, Any]) -> dict[str, list[Mapping[str, Any]]]:
    result: dict[str, list[Mapping[str, Any]]] = {}
    for item in lettering.get("items") or []:
        if isinstance(item, Mapping) and item.get("panel_id"):
            result.setdefault(str(item["panel_id"]), []).append(item)
    return result


def _translation_context(
    root: Path,
    chapter: str,
    lettering: Mapping[str, Any],
) -> tuple[Path, Mapping[str, Any]]:
    bindings = lettering.get("source_bindings") if isinstance(lettering.get("source_bindings"), Mapping) else {}
    recorded = bindings.get("translation_map") if isinstance(bindings.get("translation_map"), Mapping) else {}
    path = _project_path(root, recorded.get("path")) or root / "排版" / chapter / "lettering_translations.json"
    payload = _load_json(path)
    values = payload.get("translations") if isinstance(payload, Mapping) and isinstance(payload.get("translations"), Mapping) else payload
    return path, values if isinstance(values, Mapping) else {}


def _translation_dependencies(
    values: Mapping[str, Any],
    lettering_items: list[Mapping[str, Any]],
) -> dict[str, Any]:
    dependencies: dict[str, Any] = {}
    for item in lettering_items:
        content_ref = str(item.get("content_ref") or "").strip()
        source_text = str(item.get("source_text") or item.get("text") or "").strip()
        if content_ref and content_ref in values:
            dependencies[f"content_ref:{content_ref}"] = values[content_ref]
        if source_text and source_text in values:
            dependencies[f"source_text:{source_text}"] = values[source_text]
    return dependencies


def _registry_asset_fingerprints(registry: Mapping[str, Any]) -> dict[str, str]:
    assets = registry.get("assets") if isinstance(registry.get("assets"), Mapping) else {}
    return {str(asset_id): _sha_bytes(payload) for asset_id, payload in assets.items()}


def build_index(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry = _load_json(registry_path)
    registry_assets = _registry_asset_fingerprints(registry if isinstance(registry, Mapping) else {})
    chapters: dict[str, Any] = {}
    asset_consumers: dict[str, list[dict[str, str]]] = {}

    for chapter in _chapter_names(root):
        script_path = root / "脚本" / chapter / "panel_script.json"
        layout_path = root / "排版" / chapter / "layout.json"
        lettering_path = root / "排版" / chapter / "lettering.json"
        jobs_path = root / "出图" / chapter / "prompt" / "panel_jobs.json"
        manifest_path = root / "排版" / chapter / "export_manifest.json"
        script = _load_json(script_path)
        layout = _load_json(layout_path)
        lettering = _load_json(lettering_path)
        jobs = _load_json(jobs_path)
        manifest = _load_json(manifest_path)
        layout_map = _layout_membership(layout if isinstance(layout, Mapping) else {})
        lettering_map = _lettering_by_panel(lettering if isinstance(lettering, Mapping) else {})
        lettering_shared = (
            {
                key: value for key, value in lettering.items()
                if key not in {
                    "items", "source_bindings", "translation_usage",
                    "editorial_override_issues", "style_consistency",
                }
            }
            if isinstance(lettering, Mapping) else {}
        )
        translation_path, translation_values = _translation_context(
            root,
            chapter,
            lettering if isinstance(lettering, Mapping) else {},
        )
        script_panels = {
            str(panel.get("panel_id")): panel
            for panel in (script.get("panels") or [])
            if isinstance(panel, Mapping) and panel.get("panel_id")
        } if isinstance(script, Mapping) else {}
        script_shared = (
            {key: value for key, value in script.items() if key != "panels"}
            if isinstance(script, Mapping) else {}
        )
        jobs_by_panel = {
            str(job.get("panel_id")): job
            for job in (jobs.get("jobs") or [])
            if isinstance(job, Mapping) and job.get("panel_id")
        } if isinstance(jobs, Mapping) else {}
        panel_ids = sorted(set(script_panels) | set(layout_map) | set(lettering_map) | set(jobs_by_panel))
        panel_records: dict[str, Any] = {}

        rendered: list[dict[str, str]] = []
        if isinstance(manifest, Mapping):
            for section in ("pages", "rendered"):
                for item in manifest.get(section) or []:
                    if not isinstance(item, Mapping):
                        continue
                    path = _project_path(root, item.get("path"))
                    if path is not None:
                        rendered.append({"path": _rel(root, path), "sha256": _sha_file(path)})

        for panel_id in panel_ids:
            job = jobs_by_panel.get(panel_id, {})
            panel_lettering_items = lettering_map.get(panel_id, [])
            panel_translations = _translation_dependencies(translation_values, panel_lettering_items)
            reference_records: list[dict[str, str]] = []
            referenced_asset_ids: list[str] = []
            for ref in job.get("references") or []:
                if not isinstance(ref, Mapping):
                    continue
                asset_id = str(ref.get("id") or "").strip()
                path = _project_path(root, ref.get("path"))
                record = {
                    "id": asset_id,
                    "path": _rel(root, path) if path is not None else str(ref.get("path") or ""),
                    "sha256": _sha_file(path) if path is not None else "",
                    "registry_asset_sha256": registry_assets.get(asset_id, ""),
                }
                reference_records.append(record)
                if asset_id and asset_id not in referenced_asset_ids:
                    referenced_asset_ids.append(asset_id)
                key = record["path"] or f"registry:{asset_id}"
                asset_consumers.setdefault(key, []).append({"chapter": chapter, "panel_id": panel_id, "asset_id": asset_id})

            result_path = _project_path(root, job.get("result_path"))
            membership = layout_map.get(panel_id, {})
            panel_records[panel_id] = {
                "script_sha256": _sha_bytes({"shared": script_shared, "panel": script_panels.get(panel_id, {})}),
                "layout_sha256": _sha_bytes(membership),
                "lettering_sha256": _sha_bytes({
                    "shared": lettering_shared,
                    "items": panel_lettering_items,
                    "translation_dependencies": panel_translations,
                }),
                "job_contract_sha256": str(job.get("execution_input_sha256") or job.get("submit_prompt_sha256") or ""),
                "result": {
                    "path": _rel(root, result_path) if result_path is not None else str(job.get("result_path") or ""),
                    "sha256": _sha_file(result_path) if result_path is not None else "",
                },
                "references": sorted(reference_records, key=lambda row: (row["id"], row["path"])),
                "asset_ids": sorted(referenced_asset_ids),
                **membership,
            }

        chapters[chapter] = {
            "panels": panel_records,
            "rendered": sorted(rendered, key=lambda row: row["path"]),
            "contracts": {
                "panel_script": {"path": _rel(root, script_path), "sha256": _sha_file(script_path)},
                "layout": {"path": _rel(root, layout_path), "sha256": _sha_file(layout_path)},
                "lettering": {"path": _rel(root, lettering_path), "sha256": _sha_file(lettering_path)},
                "translation_map": {"path": _rel(root, translation_path), "sha256": _sha_file(translation_path)},
                "panel_jobs": {"path": _rel(root, jobs_path), "sha256": _sha_file(jobs_path)},
                "manifest": {"path": _rel(root, manifest_path), "sha256": _sha_file(manifest_path)},
            },
        }

    payload = {
        "kind": KIND,
        "schema_version": VERSION,
        "registry": {"path": _rel(root, registry_path), "sha256": _sha_file(registry_path), "assets": registry_assets},
        "chapters": chapters,
        "asset_consumers": {key: sorted(value, key=lambda row: (row["chapter"], row["panel_id"], row["asset_id"])) for key, value in sorted(asset_consumers.items())},
    }
    payload["index_sha256"] = _sha_bytes(payload)
    return payload


def compare_indices(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[dict[str, Any]]:
    impacts: list[dict[str, Any]] = []
    before_chapters = before.get("chapters") if isinstance(before.get("chapters"), Mapping) else {}
    after_chapters = after.get("chapters") if isinstance(after.get("chapters"), Mapping) else {}
    for chapter in sorted(set(before_chapters) | set(after_chapters)):
        old = before_chapters.get(chapter) if isinstance(before_chapters.get(chapter), Mapping) else {}
        new = after_chapters.get(chapter) if isinstance(after_chapters.get(chapter), Mapping) else {}
        old_panels = old.get("panels") if isinstance(old.get("panels"), Mapping) else {}
        new_panels = new.get("panels") if isinstance(new.get("panels"), Mapping) else {}
        affected: list[dict[str, Any]] = []
        for panel_id in sorted(set(old_panels) | set(new_panels)):
            old_panel = old_panels.get(panel_id) if isinstance(old_panels.get(panel_id), Mapping) else {}
            new_panel = new_panels.get(panel_id) if isinstance(new_panels.get(panel_id), Mapping) else {}
            reasons: list[str] = []
            stage = "review"
            for key, reason, candidate_stage in (
                ("script_sha256", "panel_script_changed", "script"),
                ("layout_sha256", "panel_layout_changed", "layout"),
                ("job_contract_sha256", "panel_job_contract_changed", "image_jobs"),
                ("references", "reference_or_registry_asset_changed", "image"),
                ("result", "panel_pixels_changed", "image"),
                ("lettering_sha256", "lettering_changed", "compose"),
            ):
                if old_panel.get(key) != new_panel.get(key):
                    reasons.append(reason)
                    if _stage_rank(candidate_stage) < _stage_rank(stage):
                        stage = candidate_stage
            if reasons:
                membership = new_panel or old_panel
                affected.append({
                    "panel_id": panel_id,
                    "from_stage": stage,
                    "page_id": str(membership.get("page_id") or ""),
                    "segment_id": str(membership.get("segment_id") or ""),
                    "reasons": reasons,
                })
        old_rendered = old.get("rendered") if isinstance(old.get("rendered"), list) else []
        new_rendered = new.get("rendered") if isinstance(new.get("rendered"), list) else []
        rendered_changed = old_rendered != new_rendered
        if affected or rendered_changed:
            stages = [row["from_stage"] for row in affected]
            impacts.append({
                "chapter": chapter,
                "from_stage": min(stages, key=_stage_rank) if stages else "compose",
                "panels": affected,
                "panel_targets": [row["panel_id"] for row in affected],
                "page_targets": sorted({row["page_id"] for row in affected if row["page_id"]}),
                "rendered_outputs_changed": rendered_changed,
            })
    return impacts


def _stage_rank(stage: str) -> int:
    order = ("source", "script", "name", "layout", "finishing", "image_jobs", "image", "compose", "review")
    try:
        return order.index(stage)
    except ValueError:
        return len(order)
