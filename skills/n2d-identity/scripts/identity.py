#!/usr/bin/env python3
"""Identity closure reports for n2d.

Outputs:
  生产数据/identity_adapter_matrix.{json,md}
  生产数据/identity_drift_report.{json,md}

The script is intentionally mostly standard-library.  If insightface/cv2 are
available, it reuses n2d-review face_consistency for cross-episode metrics; if
not, it still produces the adapter matrix and an explicit skipped drift report.
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "common"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import (  # noqa: E402  身份/LoRA 判定的单一真值源（与 gate / n2d-lora 共用）
    IDENTITY_ADAPTER_MATRIX_KIND,
    IDENTITY_DRIFT_REPORT_KIND,
    IDENTITY_HANDLE_FIELDS,
    IDENTITY_IMAGE_ADAPTERS,
    IDENTITY_REFERENCE_KEYS,
    IDENTITY_REGISTRY_KIND,
    IDENTITY_VIDEO_ADAPTERS,
    LORA_REGISTRY_READY_FIELDS,
    LORA_VALIDATION_REPORT_KIND,
    identity_allowed_modes,
    identity_registry_path,
    lora_verdict_ok,
)
from n2d_route import episode_number as route_episode_number, normalize_episode as route_normalize_episode  # noqa: E402


REGISTRY_KIND = IDENTITY_REGISTRY_KIND
MATRIX_KIND = IDENTITY_ADAPTER_MATRIX_KIND
DRIFT_KIND = IDENTITY_DRIFT_REPORT_KIND
VERSION = 1

READY_STATUSES = {"registered", "ready"}
FALLBACK_STATUSES = {"fallback_reference_group"}
PASSIVE_STATUSES = {"unsupported", "not_needed"}
IN_PROGRESS_STATUSES = {"unregistered", "candidate", "training"}
KNOWN_STATUSES = READY_STATUSES | FALLBACK_STATUSES | PASSIVE_STATUSES | IN_PROGRESS_STATUSES
HANDLE_FIELDS = IDENTITY_HANDLE_FIELDS
REFERENCE_FIELDS = IDENTITY_REFERENCE_KEYS

# 后端→允许 mode 表从契约派生（与 gate 校验、market 重置同源）
ALLOWED_IMAGE_MODES = identity_allowed_modes(IDENTITY_IMAGE_ADAPTERS)
ALLOWED_VIDEO_MODES = identity_allowed_modes(IDENTITY_VIDEO_ADAPTERS)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def registry_path(root: Path) -> Path:
    return Path(identity_registry_path(str(root)))


def load_registry(root: Path) -> Dict[str, Any]:
    data = load_json(registry_path(root))
    if not isinstance(data, dict):
        raise FileNotFoundError(f"identity_registry.json not found or invalid: {registry_path(root)}")
    return data


def handle_value(cfg: Mapping[str, Any]) -> str:
    for key in HANDLE_FIELDS:
        value = str(cfg.get(key, "")).strip()
        if value:
            return value
    return ""


def path_exists(root: Path, rel: str) -> bool:
    if not rel:
        return False
    p = Path(rel)
    return p.exists() if p.is_absolute() else (root / p).exists()


def resolve_path(root: Path, rel: str) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else root / p


def reference_group_status(root: Path, reference_group: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for key in REFERENCE_FIELDS:
        rel = str(reference_group.get(key, "")).strip()
        out[key] = {"path": rel, "exists": path_exists(root, rel)}
    extras = {k: v for k, v in reference_group.items() if k not in REFERENCE_FIELDS}
    if extras:
        out["_extra"] = {"value": extras, "exists": True}
    return out


def reference_group_ready(ref_status: Mapping[str, Mapping[str, Any]]) -> bool:
    return all(bool(ref_status.get(k, {}).get("exists")) for k in REFERENCE_FIELDS)


def allowed_modes(stage: str, backend: str) -> Optional[set[str]]:
    table = ALLOWED_IMAGE_MODES if stage == "image" else ALLOWED_VIDEO_MODES
    return table.get(backend)


def adapter_binding(
    *,
    stage: str,
    backend: str,
    cfg: Mapping[str, Any],
    ref_ready: bool,
) -> Dict[str, Any]:
    mode = str(cfg.get("mode", "")).strip()
    status = str(cfg.get("status", "")).strip()
    handle = handle_value(cfg)
    allowed = allowed_modes(stage, backend)
    gaps: List[str] = []
    recommendations: List[str] = []
    binding = "none"
    ready = False
    needs_action = ""

    if not mode:
        gaps.append("missing_mode")
    if not status:
        gaps.append("missing_status")
    elif status not in KNOWN_STATUSES:
        gaps.append(f"unknown_status:{status}")
    if allowed is not None and mode and mode not in allowed:
        gaps.append(f"invalid_mode:{backend}.{mode}")
    if status in READY_STATUSES:
        if handle:
            binding = mode
            ready = True
        else:
            gaps.append("ready_without_handle")
            binding = "fallback_reference_group"
            ready = ref_ready
            needs_action = f"fill_{mode}_handle"
    elif status in FALLBACK_STATUSES:
        binding = "reference_group"
        ready = ref_ready
        if not ref_ready:
            gaps.append("reference_group_assets_missing")
    elif status in IN_PROGRESS_STATUSES:
        binding = "fallback_reference_group"
        ready = ref_ready
        needs_action = f"register_{mode or backend}"
        recommendations.append(f"{backend}: register {mode or 'identity adapter'} for high-risk/core shots")
    elif status in PASSIVE_STATUSES:
        binding = "unsupported" if status == "unsupported" else "not_needed"
        ready = False

    out = {
        "mode": mode,
        "status": status,
        "ready": ready,
        "binding": binding,
        "handle": handle,
        "needs_action": needs_action,
        "gaps": gaps,
        "recommendations": recommendations,
    }
    return out


def lora_binding(root: Path, cfg: Mapping[str, Any]) -> Dict[str, Any]:
    status = str(cfg.get("status", "")).strip()
    gaps: List[str] = []
    ready = False
    if not status:
        gaps.append("missing_status")
    elif status not in KNOWN_STATUSES:
        gaps.append(f"unknown_status:{status}")
    if status == "ready":
        for key in LORA_REGISTRY_READY_FIELDS:  # 与 gate / n2d-lora 同源
            if not str(cfg.get(key, "")).strip():
                gaps.append(f"ready_missing_{key}")
        model_path = str(cfg.get("model_path", "")).strip()
        if model_path and not path_exists(root, model_path):
            gaps.append("ready_model_path_missing")
        validation_report = str(cfg.get("validation_report", "")).strip()
        if validation_report:
            report = load_json(resolve_path(root, validation_report))
            if not isinstance(report, Mapping):
                gaps.append("ready_validation_report_missing")
            else:
                if report.get("kind") != LORA_VALIDATION_REPORT_KIND:
                    gaps.append("ready_validation_report_kind_invalid")
                if not lora_verdict_ok(report.get("verdict")):
                    gaps.append("ready_validation_report_not_pass")
                report_hash = str(report.get("model_sha256", "")).strip()
                registry_hash = str(cfg.get("model_hash", "")).strip()
                if report_hash and registry_hash and report_hash != registry_hash:
                    gaps.append("ready_model_hash_mismatch")
                manual_review = report.get("manual_review") if isinstance(report.get("manual_review"), Mapping) else {}
                warnings = report.get("warnings") if isinstance(report.get("warnings"), list) else []
                if "dataset_has_warnings" in warnings:
                    if not manual_review.get("allow_dataset_warnings"):
                        gaps.append("ready_dataset_warnings_without_override")
                    elif not str(manual_review.get("notes") or "").strip():
                        gaps.append("ready_dataset_warnings_override_notes_missing")
        ready = not gaps
    return {
        "status": status,
        "ready": ready,
        "base_model": str(cfg.get("base_model", "")).strip(),
        "model_path": str(cfg.get("model_path", "")).strip(),
        "trigger": str(cfg.get("trigger", "")).strip(),
        "dataset": str(cfg.get("dataset", "")).strip(),
        "model_hash": str(cfg.get("model_hash", "")).strip(),
        "validation_report": str(cfg.get("validation_report", "")).strip(),
        "train_job": str(cfg.get("train_job", "")).strip(),
        "card": str(cfg.get("card", "")).strip(),
        "gaps": gaps,
    }


def build_adapter_matrix(root: Path, registry: Mapping[str, Any], generated_at: Optional[str] = None) -> Dict[str, Any]:
    forms_out: List[Dict[str, Any]] = []
    notes: List[str] = []
    if registry.get("kind") != REGISTRY_KIND:
        notes.append(f"registry kind should be {REGISTRY_KIND}")

    for char in registry.get("characters", []) or []:
        if not isinstance(char, Mapping):
            continue
        for form in char.get("forms", []) or []:
            if not isinstance(form, Mapping):
                continue
            reference_group = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
            ref_status = reference_group_status(root, reference_group)
            ref_ready = reference_group_ready(ref_status)
            adapters = form.get("identity_adapters") if isinstance(form.get("identity_adapters"), Mapping) else {}
            image_cfg = adapters.get("image") if isinstance(adapters.get("image"), Mapping) else {}
            video_cfg = adapters.get("video") if isinstance(adapters.get("video"), Mapping) else {}

            image_bindings = {
                backend: adapter_binding(stage="image", backend=str(backend), cfg=cfg if isinstance(cfg, Mapping) else {}, ref_ready=ref_ready)
                for backend, cfg in image_cfg.items()
            }
            video_bindings = {
                backend: adapter_binding(stage="video", backend=str(backend), cfg=cfg if isinstance(cfg, Mapping) else {}, ref_ready=ref_ready)
                for backend, cfg in video_cfg.items()
            }
            lora = lora_binding(root, adapters.get("lora") if isinstance(adapters.get("lora"), Mapping) else {})

            gaps: List[str] = []
            recommendations: List[str] = []
            for key, value in ref_status.items():
                if key.startswith("_"):
                    continue
                if not value.get("exists"):
                    gaps.append(f"missing_reference:{key}")
            for stage_name, bindings in (("image", image_bindings), ("video", video_bindings)):
                for backend, binding in bindings.items():
                    gaps.extend(f"{stage_name}.{backend}:{g}" for g in binding.get("gaps", []))
                    recommendations.extend(binding.get("recommendations", []))
            gaps.extend(f"lora:{g}" for g in lora.get("gaps", []))
            if image_bindings and not any(b.get("ready") and b.get("binding") != "reference_group" for b in image_bindings.values()):
                recommendations.append("image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect")
            if not any(b.get("ready") and b.get("binding") != "reference_group" for b in video_bindings.values()):
                recommendations.append("video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls")
            if not lora.get("ready") and str(char.get("scope", "")).strip() in ("全篇", "长线", "核心"):
                recommendations.append("lora: core long-running character; consider LoRA only if reference_group/native adapters still drift")

            forms_out.append({
                "character_id": str(char.get("id", "")).strip(),
                "character_name": str(char.get("name", "")).strip(),
                "scope": str(char.get("scope", "")).strip(),
                "form": str(form.get("form", "")).strip(),
                "asset_key": str(form.get("asset_key", "")).strip(),
                "anchor_phrase": str(form.get("anchor_phrase", "")).strip(),
                "reference_group": ref_status,
                "reference_group_ready": ref_ready,
                "image_bindings": image_bindings,
                "video_bindings": video_bindings,
                "lora_binding": lora,
                "angle_policy": form.get("angle_policy", {}),
                "drift_forbidden": form.get("drift_forbidden", []),
                "gaps": sorted(set(gaps)),
                "recommendations": sorted(set(recommendations)),
            })

    summary = {
        "forms": len(forms_out),
        "forms_with_reference_group_ready": sum(1 for f in forms_out if f.get("reference_group_ready")),
        "forms_with_native_image_ready": sum(1 for f in forms_out if any(b.get("ready") and b.get("binding") != "reference_group" for b in f.get("image_bindings", {}).values())),
        "forms_with_native_video_ready": sum(1 for f in forms_out if any(b.get("ready") and b.get("binding") != "reference_group" for b in f.get("video_bindings", {}).values())),
        "forms_with_lora_ready": sum(1 for f in forms_out if f.get("lora_binding", {}).get("ready")),
        "forms_with_gaps": sum(1 for f in forms_out if f.get("gaps")),
    }
    return {
        "kind": MATRIX_KIND,
        "version": VERSION,
        "root": str(root),
        "generated_at": generated_at or now_iso(),
        "summary": summary,
        "forms": forms_out,
        "notes": notes,
    }


def discover_episodes(root: Path) -> List[str]:
    names = set()
    for pattern in (root / "出图" / "第*集" / "图片", root / "出图" / "第*集" / "prompt"):
        for p in glob.glob(str(pattern)):
            names.add(Path(p).parent.name)
    return sorted(names, key=episode_sort_key)


def episode_sort_key(ep: str) -> Tuple[int, str]:
    n = route_episode_number(ep)
    return (n if n is not None else 10**9, ep)


def parse_episodes(value: str, available: List[str]) -> List[str]:
    if not value:
        return available
    out: List[str] = []
    by_num = {str(n): ep for ep in available for n in [route_episode_number(ep)] if n is not None}
    for part in re.split(r"[,，\s]+", value.strip()):
        if not part:
            continue
        range_sep = next((sep for sep in ("-", "–", "—", "~", "～", "至") if sep in part), None)
        if range_sep:
            start_s, end_s = part.split(range_sep, 1)
            a, b = route_episode_number(start_s), route_episode_number(end_s)
            if a is None or b is None:
                ep = route_normalize_episode(part)
                if ep not in out:
                    out.append(ep)
                continue
            for n in range(min(a, b), max(a, b) + 1):
                ep = by_num.get(str(n), f"第{n}集")
                if ep not in out:
                    out.append(ep)
            continue
        n = route_episode_number(part)
        ep = by_num.get(str(n), f"第{n}集") if n is not None else route_normalize_episode(part)
        if ep not in out:
            out.append(ep)
    return out


def load_face_consistency():
    here = Path(__file__).resolve()
    script = here.parents[2] / "n2d-review" / "scripts" / "face_consistency.py"
    spec = importlib.util.spec_from_file_location("n2d_identity_face_consistency", script)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def summarize_face_results(root: Path, episodes: List[str], face_results: Mapping[str, Mapping[str, Any]], generated_at: Optional[str] = None) -> Dict[str, Any]:
    chars: Dict[str, Dict[str, Any]] = {}
    available = True
    notes: List[str] = []
    for ep in episodes:
        res = face_results.get(ep, {})
        if not res.get("available", False):
            available = False
            notes.extend(res.get("notes", []))
        for shot in res.get("shots", []) or []:
            char = str(shot.get("char", "")).strip()
            if not char:
                continue
            verdict = str(shot.get("verdict", "noface"))
            c = chars.setdefault(char, {"episodes": {}, "total_warn": 0, "total_block": 0, "first_bad_episode": ""})
            e = c["episodes"].setdefault(ep, {"ok": 0, "warn": 0, "block": 0, "noface": 0, "worst_score": None, "floor": None})
            if verdict not in e:
                verdict = "noface"
            e[verdict] += 1
            if verdict == "warn":
                c["total_warn"] += 1
            if verdict == "block":
                c["total_block"] += 1
                if not c["first_bad_episode"]:
                    c["first_bad_episode"] = ep
            if shot.get("score") is not None:
                score = float(shot["score"])
                if e["worst_score"] is None or score < e["worst_score"]:
                    e["worst_score"] = score
            if shot.get("floor") is not None:
                e["floor"] = shot.get("floor")
    return {
        "kind": DRIFT_KIND,
        "version": VERSION,
        "root": str(root),
        "generated_at": generated_at or now_iso(),
        "available": available,
        "episodes": episodes,
        "characters": chars,
        "notes": sorted(set(notes)),
    }


def build_drift_report(root: Path, episodes: List[str], *, skip_face: bool = False, generated_at: Optional[str] = None) -> Dict[str, Any]:
    if skip_face:
        return {
            "kind": DRIFT_KIND,
            "version": VERSION,
            "root": str(root),
            "generated_at": generated_at or now_iso(),
            "available": False,
            "episodes": episodes,
            "characters": {},
            "notes": ["face consistency run skipped by --skip-face"],
        }
    fc = load_face_consistency()
    if fc is None:
        return {
            "kind": DRIFT_KIND,
            "version": VERSION,
            "root": str(root),
            "generated_at": generated_at or now_iso(),
            "available": False,
            "episodes": episodes,
            "characters": {},
            "notes": ["face_consistency.py not loadable"],
        }
    results = {ep: fc.analyze(str(root), ep) for ep in episodes}
    return summarize_face_results(root, episodes, results, generated_at=generated_at)


def render_matrix_md(matrix: Mapping[str, Any]) -> str:
    lines = [
        "# 角色身份 Adapter Matrix",
        "",
        f"- root: {matrix.get('root')}",
        f"- generated_at: {matrix.get('generated_at')}",
        "",
        "| 角色 | 形态 | reference_group | image native ready | video native ready | LoRA | gaps |",
        "|---|---|---|---|---|---|---|",
    ]
    for form in matrix.get("forms", []):
        image_ready = [
            f"{backend}:{binding.get('binding')}"
            for backend, binding in form.get("image_bindings", {}).items()
            if binding.get("ready") and binding.get("binding") != "reference_group"
        ]
        video_ready = [
            f"{backend}:{binding.get('binding')}"
            for backend, binding in form.get("video_bindings", {}).items()
            if binding.get("ready") and binding.get("binding") != "reference_group"
        ]
        gaps = ", ".join(form.get("gaps", [])) or "-"
        lines.append(
            "| {char} | {form} | {ref} | {image} | {video} | {lora} | {gaps} |".format(
                char=form.get("character_name") or form.get("character_id"),
                form=form.get("form", ""),
                ref="ready" if form.get("reference_group_ready") else "missing",
                image=", ".join(image_ready) or "-",
                video=", ".join(video_ready) or "-",
                lora="ready" if form.get("lora_binding", {}).get("ready") else form.get("lora_binding", {}).get("status", "-"),
                gaps=gaps.replace("|", "/"),
            )
        )
    lines.extend(["", "## Recommendations", ""])
    for form in matrix.get("forms", []):
        recs = form.get("recommendations", [])
        if not recs:
            continue
        lines.append(f"### {form.get('character_name') or form.get('character_id')} / {form.get('form')}")
        for rec in recs:
            lines.append(f"- {rec}")
        lines.append("")
    return "\n".join(lines)


def render_drift_md(report: Mapping[str, Any]) -> str:
    lines = [
        "# 跨集角色漂移报表",
        "",
        f"- root: {report.get('root')}",
        f"- generated_at: {report.get('generated_at')}",
        f"- available: {report.get('available')}",
        "",
    ]
    for note in report.get("notes", []):
        lines.append(f"- note: {note}")
    lines.extend(["", "| 角色 | first_bad_episode | total_warn | total_block | episodes |", "|---|---|---|---|---|"])
    for char, info in sorted((report.get("characters") or {}).items()):
        ep_bits = []
        for ep, counts in info.get("episodes", {}).items():
            ep_bits.append(f"{ep}: ok {counts.get('ok',0)} / warn {counts.get('warn',0)} / block {counts.get('block',0)}")
        lines.append(
            f"| {char} | {info.get('first_bad_episode') or '-'} | {info.get('total_warn', 0)} | {info.get('total_block', 0)} | {'; '.join(ep_bits)} |"
        )
    if not report.get("characters"):
        lines.append("| - | - | 0 | 0 | 无可机检角色或机检跳过 |")
    return "\n".join(lines)


def write_outputs(root: Path, matrix: Mapping[str, Any], drift: Mapping[str, Any]) -> Dict[str, Path]:
    out_dir = root / "生产数据"
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "matrix_json": out_dir / "identity_adapter_matrix.json",
        "matrix_md": out_dir / "identity_adapter_matrix.md",
        "drift_json": out_dir / "identity_drift_report.json",
        "drift_md": out_dir / "identity_drift_report.md",
    }
    atomic_write_text(paths["matrix_json"], json.dumps(matrix, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["matrix_md"], render_matrix_md(matrix) + "\n")
    atomic_write_text(paths["drift_json"], json.dumps(drift, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["drift_md"], render_drift_md(drift) + "\n")
    return paths


def main() -> int:
    ap = argparse.ArgumentParser(description="Build n2d identity adapter matrix and cross-episode drift report.")
    ap.add_argument("root")
    ap.add_argument("--episodes", default="", help="episode list/range, e.g. 1-10 or 第1集,第3集; default discovers all")
    ap.add_argument("--write", action="store_true", help="write reports under 生产数据/")
    ap.add_argument("--skip-face", action="store_true", help="skip face_consistency metrics and only write adapter matrix")
    ap.add_argument("--json", action="store_true", help="print combined JSON")
    ns = ap.parse_args()

    root = Path(ns.root)
    registry = load_registry(root)
    available = discover_episodes(root)
    episodes = parse_episodes(ns.episodes, available) if ns.episodes else available
    generated_at = now_iso()
    matrix = build_adapter_matrix(root, registry, generated_at=generated_at)
    drift = build_drift_report(root, episodes, skip_face=ns.skip_face, generated_at=generated_at)
    if ns.write:
        paths = write_outputs(root, matrix, drift)
        for p in paths.values():
            print(f"wrote {p}")
    elif ns.json:
        print(json.dumps({"matrix": matrix, "drift": drift}, ensure_ascii=False, indent=2))
    else:
        print(render_matrix_md(matrix))
        print()
        print(render_drift_md(drift))
    return 1 if matrix.get("summary", {}).get("forms_with_gaps", 0) or any(c.get("total_block", 0) for c in (drift.get("characters") or {}).values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
