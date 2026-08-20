#!/usr/bin/env python3
"""Small, dependency-free contract helpers for the comic line.

The module deliberately contains only content-hash and receipt primitives.  It
does not know how to judge story or art quality; callers may use it to prove
that a deterministic review was run against the files that are still current.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


VERSION = 2


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def relative_path(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def file_fingerprint(root: Path, path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": relative_path(root, path),
        "exists": path.is_file(),
    }
    if path.is_file():
        record["sha256"] = sha256_file(path)
        record["size"] = path.stat().st_size
    return record


def fingerprint_files(root: Path, paths: Iterable[Path]) -> dict[str, Any]:
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    files = [file_fingerprint(root, path) for path in unique]
    return {
        "kind": "comic_inputs_fingerprint",
        "version": VERSION,
        "files": files,
        "sha256": stable_sha256(files),
    }


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _resolve_project_path(root: Path, raw: Any) -> Path | None:
    text = str(raw or "").strip()
    if not text or "://" in text or text.startswith("data:"):
        return None
    path = Path(text).expanduser()
    return path if path.is_absolute() else root / path


def _declared_paths(root: Path, payload: Any, *, parent_key: str = "") -> list[Path]:
    """Collect actual files consumed by JSON contracts.

    Registry views are string-valued maps while source/reference/render records
    use explicit ``*_path`` keys.  Both shapes are supported; prose fields are
    deliberately ignored so a filename mentioned in a note is not treated as
    an input artifact.
    """
    out: list[Path] = []
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            key_text = str(key)
            if isinstance(value, str) and (
                key_text == "path"
                or key_text.endswith("_path")
                or key_text in {"source_path", "result_path"}
                or parent_key == "views"
            ):
                resolved = _resolve_project_path(root, value)
                if resolved is not None:
                    out.append(resolved)
            else:
                out.extend(_declared_paths(root, value, parent_key=key_text))
    elif isinstance(payload, list):
        for value in payload:
            out.extend(_declared_paths(root, value, parent_key=parent_key))
    return out


def _transitive_declared_paths(root: Path, contract_paths: Iterable[Path]) -> list[Path]:
    """Follow file declarations through JSON contracts.

    Review packets are contracts of their own: a panel/identity receipt names
    its contact sheet and every comparison input.  Hashing only the receipt
    JSON would leave an already-issued stage receipt current when one of those
    files changed in place.  Follow only explicitly declared JSON paths, keep
    missing files in the result, and stop cycles by resolved path.
    """
    out: list[Path] = []
    queue = list(contract_paths)
    visited: set[str] = set()
    while queue:
        contract_path = queue.pop(0)
        key = str(contract_path.resolve())
        if key in visited:
            continue
        visited.add(key)
        for declared_path in _declared_paths(root, _load_json(contract_path)):
            out.append(declared_path)
            if declared_path.suffix.lower() == ".json":
                queue.append(declared_path)
    return out


def _rendered_paths(root: Path, manifest: Path) -> list[Path]:
    payload = _load_json(manifest)
    out: list[Path] = []
    if not isinstance(payload, Mapping):
        return out
    for item in (payload.get("pages") or []) + (payload.get("rendered") or []):
        if not isinstance(item, Mapping):
            continue
        resolved = _resolve_project_path(root, item.get("path"))
        if resolved is not None:
            out.append(resolved)
    return out


def stage_input_paths(root: Path, chapter: str, stage: str) -> list[Path]:
    """Return deterministic inputs whose mutation invalidates a stage gate.

    Missing files stay in the bundle, so a receipt also goes stale when a
    previously missing artifact is later created.
    """
    # `_进度.md` is an observation/status surface, not a creative input.  If it
    # were fingerprinted, marking a just-approved stage complete would
    # immediately invalidate the approval receipt (a circular dependency).
    common = [root / "_设置.md"]
    adaptation_strategy = root / "开发包" / "adaptation_strategy.json"
    season_arc = root / "开发包" / "season_arc.json"
    script = root / "脚本" / chapter / "panel_script.json"
    source_semantics = root / "脚本" / chapter / "source_semantics.json"
    blueprint = root / "脚本" / "split_blueprint.json"
    dev_signoff = root / "开发包" / "signoff.json"
    name = root / "排版" / chapter / "name_board.json"
    layout = root / "排版" / chapter / "layout.json"
    finishing = root / "出图" / chapter / "finishing" / "finishing_plan.json"
    registry = root / "出图" / "共享" / "identity_registry.json"
    model_pack_report = root / "生产数据" / "comic_model_pack_report.json"
    reference_plan = root / "生产数据" / f"comic_reference_plan_{chapter}.json"
    jobs = root / "出图" / chapter / "prompt" / "panel_jobs.json"
    memory_anchor = root / "生产数据" / f"comic_memory_anchor_{chapter}.json"
    manifest = root / "排版" / chapter / "export_manifest.json"
    lettering = root / "排版" / chapter / "lettering.json"
    panel_images = sorted(
        path
        for path in (root / "出图" / chapter / "panels").glob("*")
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    model_pack_signoffs = sorted((root / "生产数据" / "comic_model_pack_signoffs").glob("*.json"))
    panel_qc = sorted((root / "生产数据" / "panel_qc" / chapter).glob("*.json"))
    vlm_tasks = root / "生产数据" / f"comic_vlm_judge_tasks_{chapter}.json"
    vlm_verdicts = root / "生产数据" / f"comic_vlm_judge_verdicts_{chapter}.json"
    rendered = _rendered_paths(root, manifest)

    # Hash the bytes behind declared paths, not just the JSON that names them.
    # This closes the common hole where a source/reference/view image changes
    # in place while its registry or manifest stays byte-for-byte identical.
    declared = _transitive_declared_paths(root, (
        blueprint,
        source_semantics,
        registry,
        model_pack_report,
        memory_anchor,
        reference_plan,
        jobs,
    ))
    panel_qc_declared = _transitive_declared_paths(root, panel_qc)

    development = [adaptation_strategy, season_arc, blueprint, dev_signoff]
    source_declared = _declared_paths(root, _load_json(blueprint)) + _declared_paths(root, _load_json(source_semantics))
    script_inputs = common + development + source_declared + [source_semantics, script]
    name_inputs = script_inputs + [name]
    layout_inputs = name_inputs + [layout]
    finishing_inputs = layout_inputs + [finishing]
    identity_inputs = [
        registry,
        model_pack_report,
        *model_pack_signoffs,
        memory_anchor,
        reference_plan,
        jobs,
        *declared,
    ]
    preflight_inputs = finishing_inputs + identity_inputs
    image_inputs = preflight_inputs + panel_images + panel_qc + panel_qc_declared
    compose_inputs = image_inputs + [lettering, manifest] + rendered
    review_evidence = [
        root / "生产数据" / f"raw_bubble_acceptance_{chapter}.json",
        root / "生产数据" / f"style_consistency_acceptance_{chapter}.json",
        root / "生产数据" / f"character_consistency_acceptance_{chapter}.json",
        vlm_tasks,
        vlm_verdicts,
    ]

    by_stage: Mapping[str, list[Path]] = {
        "script": script_inputs,
        "name": name_inputs,
        "layout": layout_inputs,
        "finishing": finishing_inputs,
        "image_preflight": preflight_inputs,
        "image": image_inputs,
        "compose": compose_inputs,
        "review": compose_inputs + review_evidence,
    }
    return by_stage.get(stage, common + [script])


def stage_inputs_fingerprint(root: Path, chapter: str, stage: str) -> dict[str, Any]:
    return fingerprint_files(root, stage_input_paths(root, chapter, stage))


def receipt_is_current(receipt: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    return bool(
        receipt.get("inputs_fingerprint_sha256")
        and receipt.get("inputs_fingerprint_sha256") == current.get("sha256")
    )


def approval_is_current(
    payload: Mapping[str, Any],
    *,
    required_status: str = "approved",
    current_inputs_sha256: str = "",
) -> tuple[bool, str]:
    status = str(payload.get("workflow_status") or payload.get("status") or "").strip().lower()
    if status != required_status:
        return False, f"status={status or 'missing'}"
    approval = payload.get("approval")
    if not isinstance(approval, Mapping):
        return False, "approval missing"
    if str(approval.get("status") or approval.get("decision") or "").strip().lower() not in {"approved", "pass", "accepted"}:
        return False, "approval decision missing"
    if not str(approval.get("reviewed_by") or approval.get("reviewer") or "").strip():
        return False, "approval reviewer missing"
    if not str(approval.get("approved_at") or approval.get("reviewed_at") or "").strip():
        return False, "approval time missing"
    if current_inputs_sha256:
        source_receipt = payload.get("source_receipt")
        recorded = str(approval.get("inputs_sha256") or approval.get("subject_sha256") or "").strip()
        if not recorded and isinstance(source_receipt, Mapping):
            recorded = str(source_receipt.get("inputs_sha256") or "").strip()
        if not recorded:
            return False, "approval inputs sha missing"
        if recorded != current_inputs_sha256:
            return False, "approval stale"
    return True, ""
