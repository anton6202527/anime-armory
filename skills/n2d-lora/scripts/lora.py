#!/usr/bin/env python3
"""Local LoRA lifecycle manager for n2d.

This script does not hide cloud training behind an opaque button. It creates
auditable manifests for dataset, training, validation, and registry binding so
LoRA becomes a production asset instead of a loose safetensors file.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import struct
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import (  # noqa: E402  身份/LoRA 判定的单一真值源（与 n2d-review gate 共用）
    IDENTITY_REFERENCE_KEYS,
    IDENTITY_REGISTRY_KIND,
    LORA_CARD_KIND,
    LORA_DATASET_MANIFEST_KIND,
    LORA_TRAIN_JOB_KIND,
    LORA_VALIDATION_REPORT_KIND,
    identity_registry_path,
    lora_report_ready_blocks,
    file_lock,
    registry_lock_path,
)


REGISTRY_KIND = IDENTITY_REGISTRY_KIND
DATASET_KIND = LORA_DATASET_MANIFEST_KIND
TRAIN_KIND = LORA_TRAIN_JOB_KIND
VALIDATION_KIND = LORA_VALIDATION_REPORT_KIND
CARD_KIND = LORA_CARD_KIND
VERSION = 1
REFERENCE_KEYS = IDENTITY_REFERENCE_KEYS
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)  # same-dir temp+replace: readers never see a half-written registry


def with_registry_lock(fn):
    """Hold the per-project registry lock for the whole command so lora status
    writes (init / train-job / register) serialize their read-merge-write of
    identity_registry.json against concurrent n2d-asset-market imports."""
    def _wrapped(args: argparse.Namespace) -> int:
        root = getattr(args, "project_root", None)
        if not root:
            return fn(args)
        with file_lock(registry_lock_path(str(root))):
            return fn(args)
    _wrapped.__name__ = getattr(fn, "__name__", "wrapped")
    _wrapped.__doc__ = fn.__doc__
    return _wrapped


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def slugify(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[^\w\u4e00-\u9fff.-]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip("-_.")
    return text or "asset"


def registry_path(root: Path) -> Path:
    return Path(identity_registry_path(str(root)))


def load_registry(root: Path) -> Dict[str, Any]:
    path = registry_path(root)
    if not path.is_file():
        raise FileNotFoundError(f"identity_registry.json not found: {path}")
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"invalid identity_registry.json: {path}")
    data.setdefault("kind", REGISTRY_KIND)
    data.setdefault("version", 1)
    data.setdefault("characters", [])
    return data


def save_registry(root: Path, registry: Mapping[str, Any]) -> None:
    write_json(registry_path(root), registry)


def ref_to_path(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        return str(value.get("path") or value.get("file") or "").strip()
    return ""


def resolve_path(root: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else root / p


def find_character_form(registry: Mapping[str, Any], *, character_id: str, form_name: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    for char in registry.get("characters", []) or []:
        if not isinstance(char, dict):
            continue
        if str(char.get("id", "")).strip() != character_id:
            continue
        forms = [f for f in char.get("forms", []) or [] if isinstance(f, dict)]
        if not forms:
            raise KeyError(f"character has no forms: {character_id}")
        if form_name:
            for form in forms:
                if str(form.get("form", "")).strip() == form_name:
                    return char, form
            raise KeyError(f"form not found: {character_id} / {form_name}")
        return char, forms[0]
    raise KeyError(f"character not found: {character_id}")


def lora_dir(root: Path, character_id: str, form_name: str) -> Path:
    safe_form = slugify(form_name or "常态")
    return root / "设定库" / "lora" / slugify(character_id) / safe_form


def relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def image_size(path: Path) -> Tuple[Optional[int], Optional[int]]:
    try:
        with path.open("rb") as fh:
            header = fh.read(32)
            if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
                return struct.unpack(">II", header[16:24])
            if header[:3] == b"\xff\xd8\xff":
                fh.seek(2)
                while True:
                    byte = fh.read(1)
                    if not byte:
                        break
                    if byte != b"\xff":
                        continue
                    marker = fh.read(1)
                    while marker == b"\xff":
                        marker = fh.read(1)
                    if marker in (b"\xc0", b"\xc1", b"\xc2", b"\xc3", b"\xc5", b"\xc6", b"\xc7", b"\xc9", b"\xca", b"\xcb", b"\xcd", b"\xce", b"\xcf"):
                        length = struct.unpack(">H", fh.read(2))[0]
                        data = fh.read(length - 2)
                        if len(data) >= 5:
                            return struct.unpack(">HH", data[1:5])[::-1]
                    else:
                        length_bytes = fh.read(2)
                        if len(length_bytes) != 2:
                            break
                        length = struct.unpack(">H", length_bytes)[0]
                        fh.seek(max(0, length - 2), os.SEEK_CUR)
    except Exception:
        return None, None
    return None, None


def write_card_md(card_path: Path, card: Mapping[str, Any]) -> None:
    lines = [
        f"# LoRA Card — {card.get('character_name')} / {card.get('form')}",
        "",
        f"- character_id: `{card.get('character_id')}`",
        f"- form: `{card.get('form')}`",
        f"- trigger: `{card.get('trigger')}`",
        f"- base_model: `{card.get('base_model')}`",
        f"- license_mode: `{card.get('license_mode')}`",
        f"- provider: `{card.get('provider')}`",
        f"- status: `{card.get('status')}`",
        "",
        "## Policy",
        "",
        "- LoRA 只用于核心长线角色的 hero 镜或关键叙事镜。",
        "- 未通过 validation_report 之前不能写入 registry ready。",
        "- 商用项目前必须确认底模许可。",
        "",
    ]
    write_text(card_path, "\n".join(lines))


def cmd_hint(_: argparse.Namespace) -> int:
    print(
        """# n2d-lora 提示

你不需要记 CLI。遇到这些场景，直接对 agent 说自然语言即可：
- “给沈念启动 LoRA 生命周期”
- “审计沈念 LoRA 数据集”
- “为沈念生成 LoRA 训练任务”
- “验证这个 safetensors，验证过再注册”
- “把沈念 LoRA 写回 identity_registry”
- “看看哪些角色该升档 LoRA”

agent 内部会按阶段运行：
- python3 skills/n2d-lora/scripts/lora.py suggest <作品根>  # 读漂移报表打印升档建议
- python3 skills/n2d-lora/scripts/lora.py init <作品根> --character-id CHAR_XXX --form 常态
- python3 skills/n2d-lora/scripts/lora.py dataset <作品根> --character-id CHAR_XXX --form 常态 --copy-references
- python3 skills/n2d-lora/scripts/lora.py train-job <作品根> --character-id CHAR_XXX --form 常态 --provider fal
- python3 skills/n2d-lora/scripts/lora.py validate <作品根> --character-id CHAR_XXX --form 常态 --model-path ... --approved  # 数据集无 warning 时
- python3 skills/n2d-lora/scripts/lora.py register <作品根> --character-id CHAR_XXX --form 常态
"""
    )
    return 0


@with_registry_lock
def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    registry = load_registry(root)
    char, form = find_character_form(registry, character_id=args.character_id, form_name=args.form)
    out_dir = lora_dir(root, args.character_id, str(form.get("form", "") or args.form))
    out_dir.mkdir(parents=True, exist_ok=True)
    trigger = args.trigger or f"{slugify(str(char.get('name') or args.character_id)).lower()}_{slugify(str(form.get('form') or 'normal')).lower()}_v1"

    card = {
        "kind": CARD_KIND,
        "version": VERSION,
        "project_root": str(root),
        "character_id": args.character_id,
        "character_name": str(char.get("name", "")),
        "form": str(form.get("form", "") or args.form),
        "asset_key": str(form.get("asset_key", "")),
        "trigger": trigger,
        "base_model": args.base_model,
        "license_mode": args.license_mode,
        "provider": args.provider,
        "status": "candidate",
        "created_at": now_iso(),
        "paths": {
            "root": relative(root, out_dir),
            "dataset": relative(root, out_dir / "dataset"),
            "dataset_manifest": relative(root, out_dir / "dataset_manifest.json"),
            "train_job": relative(root, out_dir / "train_job.json"),
            "validation_report": relative(root, out_dir / "validation_report.json"),
            "card_md": relative(root, out_dir / "lora_card.md"),
        },
        "policy": {
            "hero_shots_only": True,
            "commercial_license_must_be_verified": args.license_mode == "commercial",
            "register_ready_requires_validation_pass": True,
        },
    }
    write_json(out_dir / "lora_card.json", card)
    write_card_md(out_dir / "lora_card.md", card)

    adapters = form.setdefault("identity_adapters", {})
    lora = adapters.setdefault("lora", {})
    lora.update(
        {
            "status": "candidate",
            "base_model": args.base_model,
            "model_path": "",
            "trigger": trigger,
            "dataset": relative(root, out_dir / "dataset"),
            "card": relative(root, out_dir / "lora_card.json"),
        }
    )
    save_registry(root, registry)
    print(f"[ok] initialized LoRA lifecycle: {out_dir}")
    print(f"[next] python3 skills/n2d-lora/scripts/lora.py dataset '{root}' --character-id {args.character_id} --form '{card['form']}' --copy-references")
    return 0


def iter_dataset_images(dataset_dir: Path) -> Iterable[Path]:
    if not dataset_dir.is_dir():
        return []
    return sorted(p for p in dataset_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS)


def copy_reference_group(root: Path, form: Mapping[str, Any], dataset_dir: Path, trigger: str) -> List[Dict[str, Any]]:
    copied: List[Dict[str, Any]] = []
    ref = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
    dataset_dir.mkdir(parents=True, exist_ok=True)
    for role in REFERENCE_KEYS:
        rel = ref_to_path(ref.get(role, ""))
        if not rel:
            continue
        src = resolve_path(root, rel)
        if not src.is_file():
            continue
        target = dataset_dir / f"seed_{role}{src.suffix.lower() or '.png'}"
        shutil.copy2(src, target)
        caption = f"{trigger}, {role} reference, {form.get('anchor_phrase', '')}".strip().strip(",")
        write_text(target.with_suffix(".txt"), caption + "\n")
        copied.append({"role": role, "source": rel, "target": target.name})
    return copied


def build_dataset_manifest(root: Path, out_dir: Path, char: Mapping[str, Any], form: Mapping[str, Any], trigger: str) -> Dict[str, Any]:
    dataset_dir = out_dir / "dataset"
    images = list(iter_dataset_images(dataset_dir))
    items: List[Dict[str, Any]] = []
    role_counts: Dict[str, int] = {}
    warnings: List[str] = []
    for img in images:
        caption_path = img.with_suffix(".txt")
        caption = caption_path.read_text(encoding="utf-8").strip() if caption_path.is_file() else ""
        width, height = image_size(img)
        lower = img.stem.lower()
        role = "unknown"
        for candidate in ("front", "side", "back", "outfit", "turnaround", "closeup", "halfbody", "fullbody", "expression"):
            if candidate in lower:
                role = candidate
                break
        role_counts[role] = role_counts.get(role, 0) + 1
        item_warnings: List[str] = []
        if not caption:
            item_warnings.append("missing_caption")
        elif trigger and trigger not in caption:
            item_warnings.append("caption_missing_trigger")
        if width is not None and height is not None and min(width, height) < 512:
            item_warnings.append("image_too_small")
        items.append(
            {
                "file": relative(root, img),
                "caption_file": relative(root, caption_path) if caption_path.is_file() else "",
                "caption": caption,
                "width": width,
                "height": height,
                "role": role,
                "sha256": sha256(img),
                "warnings": item_warnings,
            }
        )
    if len(items) < 15:
        warnings.append("dataset_below_recommended_15_images")
    if len(items) > 50:
        warnings.append("dataset_above_recommended_50_images_overfit_risk")
    if sum(1 for item in items if item.get("warnings")):
        warnings.append("item_warnings_present")
    if "front" not in role_counts and "closeup" not in role_counts:
        warnings.append("missing_front_or_closeup_samples")
    if "side" not in role_counts:
        warnings.append("missing_side_samples")
    if not any(k in role_counts for k in ("fullbody", "outfit")):
        warnings.append("missing_fullbody_or_outfit_samples")

    return {
        "kind": DATASET_KIND,
        "version": VERSION,
        "project_root": str(root),
        "character_id": str(char.get("id", "")),
        "character_name": str(char.get("name", "")),
        "form": str(form.get("form", "")),
        "trigger": trigger,
        "generated_at": now_iso(),
        "dataset_dir": relative(root, dataset_dir),
        "recommended": {"min_images": 15, "max_images": 50, "target_resolution": "1024x1024"},
        "summary": {
            "images": len(items),
            "captions": sum(1 for item in items if item.get("caption")),
            "role_counts": role_counts,
            "warnings": warnings,
            "ready_for_training": bool(items) and not warnings,
        },
        "items": items,
    }


def cmd_dataset(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    registry = load_registry(root)
    char, form = find_character_form(registry, character_id=args.character_id, form_name=args.form)
    out_dir = lora_dir(root, args.character_id, str(form.get("form", "") or args.form))
    card_path = out_dir / "lora_card.json"
    card = read_json(card_path) if card_path.is_file() else {}
    trigger = args.trigger or str(card.get("trigger") or form.get("identity_adapters", {}).get("lora", {}).get("trigger") or f"{slugify(args.character_id).lower()}_v1")
    copied: List[Dict[str, Any]] = []
    if args.copy_references:
        copied = copy_reference_group(root, form, out_dir / "dataset", trigger)
    manifest = build_dataset_manifest(root, out_dir, char, form, trigger)
    manifest["copied_references"] = copied
    write_json(out_dir / "dataset_manifest.json", manifest)
    print(f"[ok] wrote dataset manifest: {out_dir / 'dataset_manifest.json'}")
    print(f"[summary] images={manifest['summary']['images']} warnings={','.join(manifest['summary']['warnings']) or 'none'}")
    return 1 if args.fail_on_warnings and manifest["summary"]["warnings"] else 0


@with_registry_lock
def cmd_train_job(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    registry = load_registry(root)
    char, form = find_character_form(registry, character_id=args.character_id, form_name=args.form)
    out_dir = lora_dir(root, args.character_id, str(form.get("form", "") or args.form))
    dataset_manifest_path = out_dir / "dataset_manifest.json"
    if not dataset_manifest_path.is_file():
        raise FileNotFoundError(f"dataset manifest not found: {dataset_manifest_path}")
    dataset = read_json(dataset_manifest_path)
    card = read_json(out_dir / "lora_card.json") if (out_dir / "lora_card.json").is_file() else {}
    trigger = args.trigger or str(card.get("trigger") or dataset.get("trigger") or f"{slugify(args.character_id).lower()}_v1")
    base_model = args.base_model or str(card.get("base_model") or "sdxl")
    provider = args.provider or str(card.get("provider") or "manual")
    warnings: List[str] = []
    if dataset.get("summary", {}).get("warnings"):
        warnings.append("dataset_has_warnings")
    if dataset.get("summary", {}).get("images", 0) < 15:
        warnings.append("dataset_below_recommended_15_images")
    if args.license_mode == "commercial" and base_model in {"flux-dev", "flux.1-dev"}:
        warnings.append("commercial_license_risk_flux_dev")
    job = {
        "kind": TRAIN_KIND,
        "version": VERSION,
        "project_root": str(root),
        "character_id": args.character_id,
        "character_name": str(char.get("name", "")),
        "form": str(form.get("form", "")),
        "created_at": now_iso(),
        "status": "planned",
        "provider": provider,
        "base_model": base_model,
        "license_mode": args.license_mode,
        "trigger": trigger,
        "dataset_manifest": relative(root, dataset_manifest_path),
        "output_dir": relative(root, out_dir),
        "expected_model_path": relative(root, out_dir / f"{slugify(args.character_id)}_{slugify(str(form.get('form') or 'normal'))}_v1.safetensors"),
        "hyperparameters": {
            "steps": args.steps,
            "rank": args.rank,
            "learning_rate": args.learning_rate,
        },
        "provider_payload": {
            "provider": provider,
            "base_model": base_model,
            "trigger": trigger,
            "dataset_dir": dataset.get("dataset_dir", ""),
            "steps": args.steps,
            "rank": args.rank,
            "learning_rate": args.learning_rate,
        },
        "warnings": warnings,
        "notes": [
            "This job manifest is auditable input for fal/RunPod/manual training.",
            "Do not mark LoRA ready until validation_report verdict is pass.",
        ],
    }
    write_json(out_dir / "train_job.json", job)
    adapters = form.setdefault("identity_adapters", {})
    lora = adapters.setdefault("lora", {})
    lora.update({"status": "training" if args.mark_training else "candidate", "base_model": base_model, "trigger": trigger, "dataset": dataset.get("dataset_dir", ""), "train_job": relative(root, out_dir / "train_job.json")})
    save_registry(root, registry)
    print(f"[ok] wrote train job: {out_dir / 'train_job.json'}")
    if warnings:
        print(f"[warn] {', '.join(warnings)}")
    return 1 if args.fail_on_warnings and warnings else 0


def cmd_validate(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    registry = load_registry(root)
    char, form = find_character_form(registry, character_id=args.character_id, form_name=args.form)
    out_dir = lora_dir(root, args.character_id, str(form.get("form", "") or args.form))
    dataset_path = out_dir / "dataset_manifest.json"
    train_path = out_dir / "train_job.json"
    dataset = read_json(dataset_path) if dataset_path.is_file() else {}
    train_job = read_json(train_path) if train_path.is_file() else {}
    model_path = Path(args.model_path)
    if not model_path.is_absolute():
        model_path = root / model_path
    warnings: List[str] = []
    blocks: List[str] = []
    if not model_path.is_file():
        blocks.append("model_path_missing")
    if not dataset_path.is_file():
        blocks.append("dataset_manifest_missing")
    dataset_summary = dataset.get("summary", {}) if isinstance(dataset, Mapping) else {}
    dataset_warnings = list(dataset_summary.get("warnings", []) or []) if isinstance(dataset_summary, Mapping) else []
    if dataset_warnings:
        warnings.append("dataset_has_warnings")
        if args.allow_dataset_warnings:
            warnings.append("dataset_warnings_overridden")
            if not str(args.notes or "").strip():
                blocks.append("dataset_warnings_override_notes_missing")
        else:
            blocks.append("dataset_warnings_unresolved")
    if not args.trigger and not train_job.get("trigger"):
        blocks.append("trigger_missing")
    if not args.base_model and not train_job.get("base_model"):
        blocks.append("base_model_missing")
    if args.approved:
        verdict = "pass" if not blocks else "block"
    else:
        verdict = "warn" if not blocks else "block"
        warnings.append("manual_approval_required")
    report = {
        "kind": VALIDATION_KIND,
        "version": VERSION,
        "project_root": str(root),
        "character_id": args.character_id,
        "character_name": str(char.get("name", "")),
        "form": str(form.get("form", "")),
        "generated_at": now_iso(),
        "model_path": relative(root, model_path),
        "model_sha256": sha256(model_path) if model_path.is_file() else "",
        "base_model": args.base_model or train_job.get("base_model", ""),
        "trigger": args.trigger or train_job.get("trigger", ""),
        "dataset_manifest": relative(root, dataset_path) if dataset_path.is_file() else "",
        "train_job": relative(root, train_path) if train_path.is_file() else "",
        "verdict": verdict,
        "warnings": warnings,
        "blocks": blocks,
        "manual_review": {
            "approved": bool(args.approved),
            "allow_dataset_warnings": bool(args.allow_dataset_warnings),
            "notes": args.notes or "",
        },
        "checks": {
            "model_exists": model_path.is_file(),
            "dataset_manifest_exists": dataset_path.is_file(),
            "dataset_ready_for_training": bool(dataset_summary.get("ready_for_training")),
            "dataset_warnings": dataset_warnings,
            "trigger_present": bool(args.trigger or train_job.get("trigger")),
            "base_model_present": bool(args.base_model or train_job.get("base_model")),
        },
    }
    write_json(out_dir / "validation_report.json", report)
    print(f"[ok] wrote validation report: {out_dir / 'validation_report.json'}")
    print(f"[verdict] {verdict}")
    return 0 if verdict == "pass" else 1


@with_registry_lock
def cmd_register(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    registry = load_registry(root)
    char, form = find_character_form(registry, character_id=args.character_id, form_name=args.form)
    out_dir = lora_dir(root, args.character_id, str(form.get("form", "") or args.form))
    report_path = out_dir / "validation_report.json"
    if not report_path.is_file():
        raise FileNotFoundError(f"validation report not found: {report_path}")
    report = read_json(report_path)
    if not isinstance(report, Mapping):
        raise ValueError(f"validation report is not an object: {report_path}")
    # 报告层缺口判定收口到契约（verdict/必填字段/数据集警告覆核，与 identity / review gate 同源）；
    # 本地只补磁盘层检查：model 文件真实存在 + 实测 hash 与报告一致（契约层不碰文件系统）。
    ready_blocks: List[str] = lora_report_ready_blocks(report)
    model_rel = str(report.get("model_path", "")).strip()
    model_path = resolve_path(root, model_rel)
    if not model_path.is_file():
        ready_blocks.append("model_path_missing")
    if model_path.is_file() and report.get("model_sha256") and sha256(model_path) != str(report.get("model_sha256")):
        ready_blocks.append("model_hash_mismatch")
    if ready_blocks and not args.force:
        raise ValueError("validation report is not ready: " + ", ".join(ready_blocks))
    adapters = form.setdefault("identity_adapters", {})
    lora = adapters.setdefault("lora", {})
    lora.update(
        {
            "status": "candidate" if ready_blocks else "ready",
            "base_model": str(report.get("base_model", "")),
            "model_path": model_rel,
            "trigger": str(report.get("trigger", "")),
            "dataset": str(report.get("dataset_manifest", "")),
            "model_hash": str(report.get("model_sha256", "")),
            "validation_report": relative(root, report_path),
            "train_job": str(report.get("train_job", "")),
            "card": relative(root, out_dir / "lora_card.json") if (out_dir / "lora_card.json").is_file() else "",
        }
    )
    if ready_blocks:
        lora["manual_override"] = {
            "forced": True,
            "reasons": ready_blocks,
            "registered_at": now_iso(),
        }
    else:
        lora.pop("manual_override", None)
    save_registry(root, registry)
    if ready_blocks:
        print(f"[warn] force registered LoRA candidate for {args.character_id} / {form.get('form')}: {', '.join(ready_blocks)}")
    else:
        print(f"[ok] registered LoRA ready for {args.character_id} / {form.get('form')}")
    print(f"[next] python3 skills/n2d-identity/scripts/identity.py '{root}' --write")
    return 0


def cmd_suggest(args: argparse.Namespace) -> int:
    """读 identity 漂移报表里的 LoRA 升档建议（判定在 n2d-identity，本命令只消费不重算）。"""
    root = Path(args.project_root)
    report_path = root / "生产数据" / "identity_drift_report.json"
    if not report_path.is_file():
        print(f"[hint] 未找到漂移报表：{report_path}")
        print(f"[next] 先跑 python3 skills/n2d-identity/scripts/identity.py '{root}' --write 生成 identity_drift_report.json")
        return 1
    report = read_json(report_path)
    if not isinstance(report, Mapping):
        print(f"[error] 漂移报表不是 JSON 对象：{report_path}", file=sys.stderr)
        return 2
    recommendations = [r for r in (report.get("recommendations") or []) if isinstance(r, Mapping)]
    if not report.get("available"):
        print("[hint] 漂移报表 available=false（机检跳过/缺依赖），没有可用的升档判定。")
        print(f"[next] 在装好 insightface/cv2 的环境重跑 python3 skills/n2d-identity/scripts/identity.py '{root}' --write")
        return 0
    if not recommendations:
        print("[ok] 无 LoRA 升档建议：无显著跨集漂移，或相关角色 LoRA 已 ready/training。")
        return 0
    print(f"# LoRA 升档建议（{len(recommendations)} 条，来自 {report_path}）")
    for rec in recommendations:
        name = rec.get("character_name") or rec.get("character_id") or rec.get("character")
        print(f"- {name}（{rec.get('character_id')} / {rec.get('form')}，lora_status={rec.get('lora_status') or 'absent'}）")
        print(f"  理由: {rec.get('reason')}")
        print(f"  next: {rec.get('next_command')}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    registry = load_registry(root)
    char, form = find_character_form(registry, character_id=args.character_id, form_name=args.form)
    out_dir = lora_dir(root, args.character_id, str(form.get("form", "") or args.form))
    lora = form.get("identity_adapters", {}).get("lora", {}) if isinstance(form.get("identity_adapters"), Mapping) else {}
    print(f"# LoRA status: {char.get('name')} / {form.get('form')}")
    print(f"- root: {out_dir}")
    print(f"- registry_status: {lora.get('status', '-')}")
    print(f"- base_model: {lora.get('base_model', '-')}")
    print(f"- trigger: {lora.get('trigger', '-')}")
    for name in ("lora_card.json", "dataset_manifest.json", "train_job.json", "validation_report.json"):
        print(f"- {name}: {'yes' if (out_dir / name).is_file() else 'no'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="n2d LoRA lifecycle manager")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("hint")
    p.set_defaults(func=cmd_hint)

    p = sub.add_parser("init")
    p.add_argument("project_root")
    p.add_argument("--character-id", required=True)
    p.add_argument("--form", default="")
    p.add_argument("--trigger", default="")
    p.add_argument("--base-model", default="sdxl")
    p.add_argument("--license-mode", default="unknown", choices=["self_test", "commercial", "unknown"])
    p.add_argument("--provider", default="manual", choices=["manual", "fal", "runpod"])
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("dataset")
    p.add_argument("project_root")
    p.add_argument("--character-id", required=True)
    p.add_argument("--form", default="")
    p.add_argument("--trigger", default="")
    p.add_argument("--copy-references", action="store_true")
    p.add_argument("--fail-on-warnings", action="store_true")
    p.set_defaults(func=cmd_dataset)

    p = sub.add_parser("train-job")
    p.add_argument("project_root")
    p.add_argument("--character-id", required=True)
    p.add_argument("--form", default="")
    p.add_argument("--provider", default="")
    p.add_argument("--base-model", default="")
    p.add_argument("--license-mode", default="unknown", choices=["self_test", "commercial", "unknown"])
    p.add_argument("--trigger", default="")
    p.add_argument("--steps", type=int, default=1000)
    p.add_argument("--rank", type=int, default=8)
    p.add_argument("--learning-rate", default="5e-4")
    p.add_argument("--mark-training", action="store_true")
    p.add_argument("--fail-on-warnings", action="store_true")
    p.set_defaults(func=cmd_train_job)

    p = sub.add_parser("validate")
    p.add_argument("project_root")
    p.add_argument("--character-id", required=True)
    p.add_argument("--form", default="")
    p.add_argument("--model-path", required=True)
    p.add_argument("--base-model", default="")
    p.add_argument("--trigger", default="")
    p.add_argument("--approved", action="store_true")
    p.add_argument("--allow-dataset-warnings", action="store_true", help="explicitly allow dataset warnings to pass validation")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("register")
    p.add_argument("project_root")
    p.add_argument("--character-id", required=True)
    p.add_argument("--form", default="")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_register)

    p = sub.add_parser("status")
    p.add_argument("project_root")
    p.add_argument("--character-id", required=True)
    p.add_argument("--form", default="")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("suggest", help="读 生产数据/identity_drift_report.json 打印 LoRA 升档建议")
    p.add_argument("project_root")
    p.set_defaults(func=cmd_suggest)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
