#!/usr/bin/env python3
"""Cross-project n2d asset pack import/export.

This is intentionally a lightweight local "market": asset packs are folders
under the owning series' ``_资产库/`` (for n2d, normally
``创作区/制漫剧/_资产库/``) with an ``asset_pack.json`` manifest and copied
reference files.  A pack is the cross-machine/cross-series handoff unit; no
consumer should keep a live dependency on the source series library.
Native backend IDs are reset by default on import because most Character ID /
Face Lock handles are account/project scoped and should be re-registered.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

_COMMON = str(Path(__file__).resolve().parent.parent.parent / "_lib")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import (  # noqa: E402  身份注册单一真值源
    ASSET_REFERENCE_REGISTRY_KIND,
    ASSET_PACK_KIND,
    COMBAT_REGISTRY_KIND,
    IDENTITY_ADAPTER_READY_STATUSES,
    IDENTITY_FORK_HISTORY_ENTRY_FIELDS,
    IDENTITY_FORK_HISTORY_FIELD,
    IDENTITY_HANDLE_FIELDS,
    IDENTITY_IMAGE_ADAPTERS,
    IDENTITY_REFERENCE_KEYS,
    IDENTITY_REGISTRY_KIND,
    IDENTITY_VIDEO_ADAPTERS,
    MOTIF_REGISTRY_KIND,
    SYSTEM_PANEL_MOTIF_ID,
    identity_registry_path,
    asset_registry_path,
    identity_reset_template,
    file_lock,
    registry_lock_path,
    shared_asset_path,
    shared_asset_relpath,
)


PACK_KIND = ASSET_PACK_KIND
PACK_VERSION = 1
REGISTRY_KIND = IDENTITY_REGISTRY_KIND
ASSET_REGISTRY_KIND = ASSET_REFERENCE_REGISTRY_KIND
DEFAULT_LIBRARY = Path("创作区") / "制漫剧" / "_资产库"
SERIES_LIBRARY_DIRNAME = "_资产库"
SOURCE_SERIES = "n2d"
REFERENCE_KEYS = IDENTITY_REFERENCE_KEYS
ASSET_ID_PREFIX = {
    "scene": "LOC_",
    "location": "LOC_",
    "prop": "PROP_",
    "weapon": "WEAPON_",
    "magic_weapon": "WEAPON_",
    "equipment": "WEAPON_",
    "armory": "WEAPON_",
    "outfit": "OUTFIT_",
    "costume": "OUTFIT_",
    "vfx": "VFX_",
    "effect": "VFX_",
}
ROLE_SUFFIX = {
    "front": "",
    "side": "_侧",
    "back": "_背",
    "outfit": "_半身",
    "turnaround": "_三视图",
}
CHARACTER_BUNDLE_SECTIONS = ("reference", "prompts", "lora", "voice", "adapters", "qc")
NON_PORTABLE_MODEL_SUFFIXES = {".safetensors", ".ckpt", ".pt", ".pth", ".onnx"}
TEXT_ASSET_SUFFIXES = {".md", ".json", ".jsonl", ".txt", ".yaml", ".yml", ".toml"}


def series_library_for_project(project_root: Path) -> Path:
    """Return the reusable library owned by the project's creative line.

    ``创作区/制漫剧/<作品>`` therefore resolves to
    ``创作区/制漫剧/_资产库``.  Keeping this derivation project-relative makes
    a standalone n2d distribution self-contained and avoids a repository-root
    shared library dependency.
    """
    return project_root.expanduser().resolve().parent / SERIES_LIBRARY_DIRNAME


def selected_library(args: argparse.Namespace, project_root: Optional[Path] = None) -> Path:
    explicit = str(getattr(args, "library", "") or "").strip()
    if explicit:
        return Path(explicit).expanduser()
    if project_root is not None:
        return series_library_for_project(project_root)
    return DEFAULT_LIBRARY


def portability_block(files: Iterable[Mapping[str, Any]] = ()) -> Dict[str, Any]:
    rows = [dict(row) for row in files if isinstance(row, Mapping)]
    missing = [str(row.get("source") or row.get("path") or row.get("role") or "unknown")
               for row in rows if row.get("exists") is False or not str(row.get("path") or "").strip()]
    return {
        "handoff_mode": "explicit_self_contained_pack",
        "source_series": SOURCE_SERIES,
        "self_contained": not missing,
        "requires_source_library": False,
        "import_policy": "copy_or_fork_into_target_series_library",
        "cross_series_policy": "target series reads portable core/files and ignores or adapts n2d-only fields",
        "missing_files": missing,
    }


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
    """Hold the per-project registry lock for the whole command so concurrent
    import-character / import-asset (and lora.py status writes) serialize their
    read-merge-write of identity_registry.json / asset_registry.json instead of
    clobbering each other (n2d-batch multi-worker / 后台 factory)."""
    def _wrapped(args: argparse.Namespace) -> int:
        root = getattr(args, "project_root", None)
        if not root:
            return fn(args)
        # Import commands can target a brand-new project root.  Create the lock
        # directory before opening `.registry.lock`, otherwise the first import
        # fails before it can create identity/asset registries.
        Path(root).mkdir(parents=True, exist_ok=True)
        with file_lock(registry_lock_path(str(root))):
            return fn(args)
    _wrapped.__name__ = getattr(fn, "__name__", "wrapped")
    _wrapped.__doc__ = fn.__doc__
    return _wrapped


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


def project_name(root: Path) -> str:
    return root.name or "project"


def registry_path(root: Path) -> Path:
    return Path(identity_registry_path(str(root)))


def asset_ref_registry_path(root: Path) -> Path:
    return Path(asset_registry_path(str(root)))


def load_registry(root: Path) -> Dict[str, Any]:
    path = registry_path(root)
    if not path.is_file():
        raise FileNotFoundError(f"identity_registry.json not found: {path}")
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"invalid identity_registry.json: {path}")
    return data


def empty_registry() -> Dict[str, Any]:
    return {"kind": REGISTRY_KIND, "version": 1, "characters": []}


def empty_asset_registry() -> Dict[str, Any]:
    return {"kind": ASSET_REGISTRY_KIND, "version": 1, "assets": []}


def ensure_registry(root: Path) -> Dict[str, Any]:
    path = registry_path(root)
    if path.is_file():
        data = read_json(path)
        if isinstance(data, dict):
            data.setdefault("kind", REGISTRY_KIND)
            data.setdefault("version", 1)
            data.setdefault("characters", [])
            return data
    return empty_registry()


def load_asset_registry(root: Path) -> Dict[str, Any]:
    path = asset_ref_registry_path(root)
    if not path.is_file():
        raise FileNotFoundError(f"asset_registry.json not found: {path}")
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"invalid asset_registry.json: {path}")
    return data


def ensure_asset_registry(root: Path) -> Dict[str, Any]:
    path = asset_ref_registry_path(root)
    if path.is_file():
        data = read_json(path)
        if isinstance(data, dict):
            data.setdefault("kind", ASSET_REGISTRY_KIND)
            data.setdefault("version", 1)
            data.setdefault("assets", [])
            return data
    return empty_asset_registry()


def ref_value_to_path(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        return str(value.get("path") or value.get("file") or "").strip()
    return ""


def relative_or_absolute(root: Path, rel: str) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else root / p


def find_character(registry: Mapping[str, Any], *, char_id: str = "", name: str = "") -> Dict[str, Any]:
    for char in registry.get("characters", []) or []:
        if not isinstance(char, Mapping):
            continue
        if char_id and str(char.get("id", "")).strip() == char_id:
            return copy.deepcopy(dict(char))
        if name and str(char.get("name", "")).strip() == name:
            return copy.deepcopy(dict(char))
    needle = char_id or name
    raise KeyError(f"character not found in registry: {needle}")


def find_asset(registry: Mapping[str, Any], *, asset_id: str = "", name: str = "", asset_type: str = "") -> Dict[str, Any]:
    for asset in registry.get("assets", []) or []:
        if not isinstance(asset, Mapping):
            continue
        if asset_type and str(asset.get("type", "")).strip() not in _asset_type_aliases(asset_type):
            continue
        if asset_id and str(asset.get("id", "")).strip() == asset_id:
            return copy.deepcopy(dict(asset))
        if name and str(asset.get("name", "")).strip() == name:
            return copy.deepcopy(dict(asset))
    needle = asset_id or name
    raise KeyError(f"{asset_type or 'asset'} not found in asset_registry: {needle}")


def filter_forms(char: Dict[str, Any], form_name: str = "") -> Dict[str, Any]:
    if not form_name:
        return char
    forms = [f for f in char.get("forms", []) or [] if isinstance(f, Mapping) and str(f.get("form", "")).strip() == form_name]
    if not forms:
        raise KeyError(f"form not found for {char.get('name')}: {form_name}")
    char["forms"] = [copy.deepcopy(dict(f)) for f in forms]
    return char


def pack_dir(library: Path, asset_type: str, slug: str) -> Path:
    if asset_type == "character":
        return library / "characters" / slug
    if asset_type in {"scene", "location"}:
        return library / "scenes" / slug
    if asset_type == "prop":
        return library / "props" / slug
    if asset_type == "weapon":
        return library / "weapons" / slug
    if asset_type == "outfit":
        return library / "outfits" / slug
    if asset_type == "vfx":
        return library / "vfx" / slug
    if asset_type == "route_template":
        return library / "templates" / "model_routes" / slug
    if asset_type == "motif":
        return library / "motifs" / slug
    if asset_type == "combat":
        return library / "combat" / slug
    return library / asset_type / slug


def _asset_type_aliases(asset_type: str) -> set[str]:
    if asset_type == "scene":
        return {"scene", "location"}
    if asset_type == "prop":
        return {"prop"}
    if asset_type == "weapon":
        return {"weapon", "magic_weapon", "equipment", "armory"}
    if asset_type == "outfit":
        return {"outfit", "costume"}
    if asset_type == "vfx":
        return {"vfx", "effect"}
    return {asset_type}


def validate_asset_id_prefix(asset_type: str, asset_id: str) -> None:
    prefix = ASSET_ID_PREFIX.get(asset_type)
    if prefix and not str(asset_id or "").strip().startswith(prefix):
        raise ValueError(f"{asset_type} asset id must start with {prefix}: {asset_id}")


def copy_reference_files(root: Path, out_dir: Path, char: Dict[str, Any]) -> List[Dict[str, Any]]:
    files: List[Dict[str, Any]] = []
    files_dir = out_dir / "files"
    forms = [form for form in (char.get("forms", []) or []) if isinstance(form, dict)]
    multi_form = len(forms) > 1
    for form in forms:
        ref = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
        new_ref: Dict[str, str] = {}
        form_name = str(form.get("form", "") or "form")
        form_suffix = f"_{slugify(form_name)}" if multi_form else ""
        for role, value in ref.items():
            rel = ref_value_to_path(value)
            if not rel:
                new_ref[str(role)] = ""
                continue
            source = relative_or_absolute(root, rel)
            if not source.is_file():
                new_ref[str(role)] = ""
                files.append({"form": form_name, "role": str(role), "source": rel, "path": "", "exists": False})
                continue
            target_name = f"{slugify(str(form.get('asset_key') or char.get('name') or char.get('id')))}{form_suffix}_{role}{source.suffix or '.png'}"
            target = files_dir / target_name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            pack_rel = target.relative_to(out_dir).as_posix()
            new_ref[str(role)] = pack_rel
            files.append(
                {
                    "role": str(role),
                    "form": form_name,
                    "source": rel,
                    "path": pack_rel,
                    "exists": True,
                    "sha256": sha256(target),
                    "bytes": target.stat().st_size,
                }
            )
        form["reference_group"] = new_ref
    return files


def copy_character_bundle_files(
    root: Path,
    out_dir: Path,
    char: Mapping[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Copy the portable parts of a work-local 角色库 package into one pack.

    Executable model weights remain project/account specific and are never
    copied.  Their omission is recorded so import can require retraining.
    """
    bundle = char.get("asset_bundle") if isinstance(char.get("asset_bundle"), Mapping) else {}
    package_rel = str(bundle.get("package_dir") or "").strip()
    tier = str(char.get("library_tier") or bundle.get("tier") or "named_minimal").strip()
    meta: Dict[str, Any] = {
        "source_package_dir": package_rel,
        "pack_root": "files/character_bundle",
        "library_tier": tier,
        "sections": list(CHARACTER_BUNDLE_SECTIONS),
        "included": False,
        "excluded_model_files": [],
    }
    if not package_rel:
        meta["status"] = "source_bundle_not_registered"
        return [], meta
    source_base = relative_or_absolute(root, package_rel).resolve()
    try:
        source_base.relative_to(root.resolve())
    except ValueError:
        meta["status"] = "source_bundle_outside_project"
        return [{"role": "character_bundle", "source": package_rel, "path": "", "exists": False}], meta
    if not source_base.is_dir():
        meta["status"] = "source_bundle_missing"
        return [{"role": "character_bundle", "source": package_rel, "path": "", "exists": False}], meta

    files: List[Dict[str, Any]] = []
    for source in sorted(source_base.rglob("*")):
        if not source.is_file():
            continue
        bundle_rel = source.relative_to(source_base).as_posix()
        if source.suffix.lower() in NON_PORTABLE_MODEL_SUFFIXES:
            meta["excluded_model_files"].append(bundle_rel)
            continue
        target = out_dir / "files" / "character_bundle" / bundle_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        pack_rel = target.relative_to(out_dir).as_posix()
        files.append({
            "role": "character_bundle",
            "bundle_rel": bundle_rel,
            "source": str(source.relative_to(root)),
            "path": pack_rel,
            "exists": True,
            "sha256": sha256(target),
            "bytes": target.stat().st_size,
        })
    meta["included"] = True
    meta["status"] = "copied"
    meta["included_file_count"] = len(files)
    return files, meta


def copy_asset_reference_files(root: Path, out_dir: Path, asset: Dict[str, Any]) -> List[Dict[str, Any]]:
    files: List[Dict[str, Any]] = []
    files_dir = out_dir / "files"
    ref = asset.get("reference_group") if isinstance(asset.get("reference_group"), Mapping) else {}
    new_ref: Dict[str, str] = {}
    base = slugify(str(asset.get("name") or asset.get("id") or "asset"))
    for role, value in ref.items():
        rel = ref_value_to_path(value)
        if not rel:
            new_ref[str(role)] = ""
            continue
        source = relative_or_absolute(root, rel)
        if not source.is_file():
            new_ref[str(role)] = ""
            files.append({"role": str(role), "source": rel, "path": "", "exists": False})
            continue
        suffix = "" if str(role) == "primary" else f"_{slugify(str(role))}"
        target = files_dir / f"{base}{suffix}{source.suffix or '.png'}"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        pack_rel = target.relative_to(out_dir).as_posix()
        new_ref[str(role)] = pack_rel
        files.append(
            {
                "role": str(role),
                "source": rel,
                "path": pack_rel,
                "exists": True,
                "sha256": sha256(target),
                "bytes": target.stat().st_size,
            }
        )
    asset["reference_group"] = new_ref
    return files


def reset_identity_adapters() -> Dict[str, Any]:
    return {
        # 后端默认 mode/status 从契约派生（与 identity/gate 的 allowed_modes 校验同源）
        "image": identity_reset_template(IDENTITY_IMAGE_ADAPTERS),
        "video": identity_reset_template(IDENTITY_VIDEO_ADAPTERS),
        # LoRA 完全重置：清掉所有审计/路径字段，避免新项目沿用指向旧项目的失效 model_path/safetensors。
        # .safetensors 不随资产包迁移；新项目要用 LoRA 须重新训练/验证/注册（n2d-lora）。
        "lora": {
            "status": "not_needed", "base_model": "", "model_path": "", "trigger": "", "dataset": "",
            "model_hash": "", "validation_report": "", "train_job": "", "card": "",
            "notes": "导入新项目已重置 LoRA：旧 .safetensors 不迁移，需在本项目重新训练/验证/注册",
        },
    }


def downgrade_preserved_adapters(adapters: Any, *, reason: str, pack_path: Path) -> Dict[str, Any]:
    if not isinstance(adapters, dict):
        return reset_identity_adapters()
    imported_at = now_iso()

    def review(previous_status: str) -> Dict[str, str]:
        return {
            "reason": reason,
            "imported_at": imported_at,
            "source_asset_pack": str(pack_path),
            "previous_status": previous_status,
        }

    for label in ("image", "video"):
        section = adapters.get(label)
        if not isinstance(section, dict):
            continue
        for cfg in section.values():
            if not isinstance(cfg, dict):
                continue
            previous = str(cfg.get("status", "")).strip()
            if previous in {"registered", "ready"}:
                cfg["status"] = "candidate"
                cfg["preserve_review"] = review(previous)

    lora = adapters.get("lora")
    if isinstance(lora, dict):
        previous = str(lora.get("status", "")).strip()
        if previous == "ready":
            lora["status"] = "candidate"
            lora["preserve_review"] = review(previous)
            # 清掉指向旧项目的资产/验证字段：safetensors 不随包迁移，candidate 不得带失效 model_path，
            # 否则 gate 会读到旧路径误判文件存在。用 pop 彻底移除键（置空字符串仍是"残留字段"，
            # 下游 `if lora.get("model_path")` 类判断虽不命中，但 schema 对账/diff 会把空串当已登记）。
            # 保留 base_model/trigger/dataset 作重训参考。
            for stale in ("model_path", "model_hash", "validation_report", "train_job", "card"):
                lora.pop(stale, None)
            lora["notes"] = "保留为 candidate 参考：旧 .safetensors 未迁移，本项目需重新验证/注册才可回 ready"
    return adapters


def reset_preserve_review(old_adapters: Any, new_adapters: Mapping[str, Any], *, pack_path: Path) -> List[Dict[str, Any]]:
    """默认重置 identity_adapters 时的审计痕迹（挂 form.preserve_review，导入者可见）。

    记录两类被重置的后端：① 旧 registry 存在、但新模板（identity_reset_template 派生）里
    没有的后端——整条配置随导入被移除；② 旧 status ∈ registered/ready 被降级回模板默认——
    句柄（Character ID / Face Lock / model_path）随之失效。逐条带 原 status/mode/句柄/重置原因，
    让导入者知道"源项目曾在哪些后端注册过身份"，而不是悄悄抹掉。
    """
    entries: List[Dict[str, Any]] = []
    if not isinstance(old_adapters, Mapping):
        return entries
    imported_at = now_iso()

    def entry(area: str, backend: str, cfg: Mapping[str, Any], reset_reason: str) -> Dict[str, Any]:
        return {
            "area": area,
            "backend": str(backend),
            "previous_status": str(cfg.get("status", "")).strip(),
            "previous_mode": str(cfg.get("mode", "")).strip(),
            "previous_handles": {f: cfg.get(f) for f in IDENTITY_HANDLE_FIELDS if str(cfg.get(f) or "").strip()},
            "reset_reason": reset_reason,
            "imported_at": imported_at,
            "source_asset_pack": str(pack_path),
        }

    for area in ("image", "video"):
        old = old_adapters.get(area)
        if not isinstance(old, Mapping):
            continue
        new = new_adapters.get(area)
        new = new if isinstance(new, Mapping) else {}
        for backend, cfg in old.items():
            if not isinstance(cfg, Mapping):
                continue
            status = str(cfg.get("status", "")).strip()
            if backend not in new:
                entries.append(entry(area, backend, cfg, "后端不在当前重置模板，旧配置随导入移除"))
            elif status in IDENTITY_ADAPTER_READY_STATUSES:
                entries.append(entry(area, backend, cfg, "registered/ready 身份随导入重置为模板默认，需在本项目重新注册"))
    lora = old_adapters.get("lora")
    if isinstance(lora, Mapping) and str(lora.get("status", "")).strip() in IDENTITY_ADAPTER_READY_STATUSES:
        entries.append(entry("lora", "lora", lora, "LoRA 完全重置：旧 .safetensors 不随资产包迁移，需在本项目重新训练/验证/注册"))
    return entries


def target_reference_path(name: str, role: str, suffix: str, form_name: str = "") -> str:
    form_suffix = f"_{slugify(form_name)}" if form_name else ""
    return shared_asset_relpath("图片", f"定妆_{name}{form_suffix}{ROLE_SUFFIX.get(role, '_' + role)}{suffix or '.png'}")


def target_asset_reference_path(name: str, role: str, suffix: str) -> str:
    role_suffix = "" if role == "primary" else f"_{slugify(role)}"
    return shared_asset_relpath("图片", f"定妆_{name}{role_suffix}{suffix or '.png'}")


def append_import_log(root: Path, text: str) -> None:
    path = Path(shared_asset_path(str(root), "prompt", "资产库导入记录.md", prefer_existing=False))
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.is_file() else "# 资产库导入记录\n\n"
    path.write_text(old.rstrip() + "\n\n" + text.strip() + "\n", encoding="utf-8")


def character_bundle_target(root: Path, character_id: str, name: str) -> Path:
    return root / "角色库" / f"{character_id}__{slugify(name)}"


def target_character_bundle_ref(root: Path, character_id: str, name: str, tier: str) -> Dict[str, Any]:
    base = character_bundle_target(root, character_id, name)
    rel = base.relative_to(root).as_posix()
    return {
        "manifest": f"{rel}/manifest.json",
        "package_dir": rel,
        "base_dir": rel,
        "sections": {section: f"{rel}/{section}" for section in CHARACTER_BUNDLE_SECTIONS},
        "tier": tier,
    }


def land_character_bundle(
    root: Path,
    pack_root: Path,
    pack: Mapping[str, Any],
    *,
    character_id: str,
    name: str,
    tier: str,
    source_character_id: str,
    source_name: str,
    replace: bool,
) -> Dict[str, Any]:
    """Fork the pack's portable role package into the target work 角色库."""
    target = character_bundle_target(root, character_id, name)
    if target.exists() and not replace:
        raise ValueError(f"target character bundle already exists: {target} (use --replace)")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for section in CHARACTER_BUNDLE_SECTIONS:
        (target / section).mkdir(parents=True, exist_ok=True)

    template = pack.get("character_template") if isinstance(pack.get("character_template"), Mapping) else {}
    bundle_meta = template.get("source_asset_bundle") if isinstance(template.get("source_asset_bundle"), Mapping) else {}
    source_package_dir = str(bundle_meta.get("source_package_dir") or "")
    for row in pack.get("files") or []:
        if not isinstance(row, Mapping) or row.get("role") != "character_bundle":
            continue
        bundle_rel = str(row.get("bundle_rel") or "").strip()
        pack_rel = str(row.get("path") or "").strip()
        if not bundle_rel or not pack_rel or Path(bundle_rel).name == "manifest.json":
            continue
        source = (pack_root / pack_rel).resolve()
        dest = (target / bundle_rel).resolve()
        try:
            source.relative_to(pack_root.resolve())
            dest.relative_to(target.resolve())
        except ValueError:
            raise ValueError(f"character bundle file escapes pack/target root: {bundle_rel}")
        if not source.is_file():
            raise FileNotFoundError(f"character bundle file missing in pack: {pack_rel}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        if dest.suffix.lower() in TEXT_ASSET_SUFFIXES:
            try:
                text = dest.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            text = text.replace(source_character_id, character_id).replace(source_name, name)
            if source_package_dir:
                text = text.replace(source_package_dir, target.relative_to(root).as_posix())
            dest.write_text(text, encoding="utf-8")

    ref = target_character_bundle_ref(root, character_id, name, tier)
    manifest = {
        "kind": "n2d_project_character_asset_bundle",
        "version": 1,
        "character_id": character_id,
        "name": name,
        "library_tier": tier,
        "directories": ref["sections"],
        "truth_sources": {
            "identity_registry": "出图/共享/identity_registry.json",
            "character_card": f"设定库/characters/{name}.md",
        },
        "imported_from": str(pack_root / "asset_pack.json"),
        "forked_from_character_id": source_character_id,
        "excluded_model_files": list(bundle_meta.get("excluded_model_files") or []),
        "notes": "后端主体 ID、Face Lock、LoRA ready 已重置；被排除的模型权重须在目标项目重新训练/验证。",
        "updated_at": now_iso(),
    }
    write_json(target / "manifest.json", manifest)
    readme = root / "角色库" / "README.md"
    if not readme.exists():
        readme.write_text(
            "# 角色库\n\n本目录存本作品角色生产包；语义真值仍在 `设定库/` 与 identity_registry。\n",
            encoding="utf-8",
        )
    return ref


def cmd_hint(_: argparse.Namespace) -> int:
    print(
        """# n2d 跨项目资产库提示

你不需要记 CLI。遇到这些场景，直接对 agent 说自然语言即可：
- 开新剧 / 建角色卡前：先说“查资产库有没有可复用模板”。
- 出图新增角色、场景、道具、武器、服装、VFX 前：先说“先查资产库，能导入就导入”。
- 某类镜头路由反复失败后：说“把这套路由沉淀成模板”。
- 新剧想复用原型：说“把冷宫废妃模板导入为沈念 / 把霜纹长剑导入为雷纹长剑”。

agent 内部会按需运行：
- python3 skills/n2d/n2d-asset-market/scripts/market.py list
- python3 skills/n2d/n2d-asset-market/scripts/market.py export-character <作品根> --character-id CHAR_XXX
- python3 skills/n2d/n2d-asset-market/scripts/market.py import-character <作品根> <资产包> --as-id CHAR_YYY --as-name 新角色名
- python3 skills/n2d/n2d-asset-market/scripts/market.py export-weapon|export-outfit|export-vfx <作品根> --asset-id WEAPON_/OUTFIT_/VFX_XXX
- python3 skills/n2d/n2d-asset-market/scripts/market.py import-weapon|import-outfit|import-vfx <作品根> <资产包> --as-id ... --as-name ...
- python3 skills/n2d/n2d-asset-market/scripts/market.py export-combat <作品根> --combat-id COMBAT_XXX

导入角色资产后，下一步固定是：
python3 skills/n2d/n2d-identity/scripts/identity.py <作品根> --write
"""
    )
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    library = selected_library(args)
    packs = sorted(library.glob("**/asset_pack.json"))
    if not packs:
        print(f"[empty] no asset packs under {library}")
        print("提示：开新剧或新增角色前仍应先查一次；没有命中再新建定妆。")
        return 0
    print(f"# assets under {library}")
    for path in packs:
        try:
            data = read_json(path)
        except Exception as exc:  # pragma: no cover - diagnostic only
            print(f"- [broken] {path}: {exc}")
            continue
        print(f"- {data.get('asset_type', 'unknown')}: {data.get('title') or data.get('slug')} ({path.parent})")
        tags = ", ".join(data.get("style_tags", []) or data.get("tags", []) or [])
        if tags:
            print(f"  tags: {tags}")
        print(f"  reuse: {data.get('license', {}).get('reuse', 'template_only')}")
    return 0


def cmd_verify_pack(args: argparse.Namespace) -> int:
    """Verify that a handoff pack can travel without its source library."""
    raw = Path(args.pack).expanduser()
    pack_path = raw / "asset_pack.json" if raw.is_dir() else raw
    pack_root = pack_path.parent.resolve()
    pack = read_json(pack_path)
    findings: List[str] = []
    if pack.get("kind") != PACK_KIND:
        findings.append(f"kind must be {PACK_KIND}: {pack.get('kind')}")
    for row in pack.get("files") or []:
        if not isinstance(row, Mapping):
            findings.append("files[] contains a non-object entry")
            continue
        rel = str(row.get("path") or "").strip()
        if not rel:
            findings.append(f"missing copied file for {row.get('source') or row.get('role') or 'unknown'}")
            continue
        target = (pack_root / rel).resolve()
        try:
            target.relative_to(pack_root)
        except ValueError:
            findings.append(f"file escapes pack root: {rel}")
            continue
        if not target.is_file():
            findings.append(f"file missing inside pack: {rel}")
            continue
        expected = str(row.get("sha256") or "").strip()
        if expected and sha256(target) != expected:
            findings.append(f"sha256 mismatch: {rel}")
    portability = pack.get("portability") if isinstance(pack.get("portability"), Mapping) else {}
    if portability.get("self_contained") is not True:
        findings.append("portability.self_contained must be true")
    if portability.get("requires_source_library") is not False:
        findings.append("portability.requires_source_library must be false")
    if findings:
        print(f"[fail] portable asset pack verification: {pack_path}")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print(f"[ok] self-contained asset pack: {pack_path}")
    return 0


def cmd_export_character(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    registry = load_registry(root)
    char = find_character(registry, char_id=args.character_id or "", name=args.character_name or "")
    char = filter_forms(char, args.form or "")
    title = args.title or str(char.get("name") or char.get("id") or "character")
    slug = slugify(args.slug or title)
    out_dir = pack_dir(selected_library(args, root), "character", slug)
    if out_dir.exists() and not args.force:
        raise FileExistsError(f"asset pack already exists, use --force: {out_dir}")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = copy_reference_files(root, out_dir, char)
    bundle_files, bundle_meta = copy_character_bundle_files(root, out_dir, char)
    files.extend(bundle_files)

    pack = {
        "kind": PACK_KIND,
        "version": PACK_VERSION,
        "asset_type": "character",
        "slug": slug,
        "title": title,
        "source_project": str(root),
        "source_project_name": project_name(root),
        "exported_at": now_iso(),
        "license": {
            "status": args.license_status,
            "reuse": args.reuse,
            "notes": args.license_notes or "",
        },
        "style_tags": args.style_tag or [],
        "tags": args.tag or [],
        "character_template": {
            "original_character": {
                "id": char.get("id", ""),
                "name": char.get("name", ""),
                "scope": char.get("scope", ""),
            },
            "fork_required": True,
            "reset_native_adapters_on_import": True,
            "source_asset_bundle": bundle_meta,
        },
        "registry_fragment": {"kind": REGISTRY_KIND, "version": 1, "characters": [char]},
        "files": files,
        "portability": portability_block(files),
        "reminders": [
            "导入到新剧时必须 fork 新 character_id/name，避免多剧撞脸撞身份。",
            "Character ID / Face Lock / reference controls 通常需在新项目重新注册；默认导入会重置。",
            "导入后运行 n2d-identity 生成 adapter matrix。",
        ],
    }
    write_json(out_dir / "asset_pack.json", pack)
    print(f"[ok] exported character asset pack: {out_dir}")
    return 0


def merge_character(
    registry: Dict[str, Any],
    character: Dict[str, Any],
    *,
    replace: bool = False,
) -> None:
    chars = [c for c in registry.get("characters", []) if isinstance(c, dict)]
    existing = [c for c in chars if str(c.get("id", "")).strip() == str(character.get("id", "")).strip()]
    if existing and not replace:
        raise ValueError(f"character id already exists: {character.get('id')} (use --replace)")
    if existing:
        chars = [c for c in chars if str(c.get("id", "")).strip() != str(character.get("id", "")).strip()]
    chars.append(character)
    registry["characters"] = chars


def merge_asset(
    registry: Dict[str, Any],
    asset: Dict[str, Any],
    *,
    replace: bool = False,
) -> None:
    assets = [a for a in registry.get("assets", []) if isinstance(a, dict)]
    asset_id = str(asset.get("id", "")).strip()
    existing = [a for a in assets if str(a.get("id", "")).strip() == asset_id]
    if existing and not replace:
        raise ValueError(f"asset id already exists: {asset_id} (use --replace)")
    if existing:
        assets = [a for a in assets if str(a.get("id", "")).strip() != asset_id]
    assets.append(asset)
    registry["assets"] = assets


@with_registry_lock
def cmd_import_character(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    preserve_reason = str(args.preserve_reason or "").strip()
    if args.preserve_adapters and not preserve_reason:
        raise ValueError("--preserve-adapters requires --preserve-reason; preserved adapters are imported as candidate only")
    pack_dir_path = Path(args.pack)
    pack_path = pack_dir_path / "asset_pack.json" if pack_dir_path.is_dir() else pack_dir_path
    pack_root = pack_path.parent
    pack = read_json(pack_path)
    if pack.get("kind") != PACK_KIND or pack.get("asset_type") != "character":
        raise ValueError(f"not a character asset pack: {pack_path}")
    fragment_chars = pack.get("registry_fragment", {}).get("characters", [])
    if not fragment_chars:
        raise ValueError(f"asset pack has no character fragment: {pack_path}")
    source_char = copy.deepcopy(fragment_chars[0])
    source_character_id = str(source_char.get("id", "")).strip()  # 覆盖前捕获，写入 fork 溯源
    as_name = args.as_name or str(source_char.get("name") or pack.get("title") or "角色")
    as_id = args.as_id or f"CHAR_{slugify(as_name).upper()}"
    template = pack.get("character_template") if isinstance(pack.get("character_template"), Mapping) else {}
    bundle_meta = template.get("source_asset_bundle") if isinstance(template.get("source_asset_bundle"), Mapping) else {}
    source_bundle = source_char.get("asset_bundle") if isinstance(source_char.get("asset_bundle"), Mapping) else {}
    library_tier = str(
        source_char.get("library_tier")
        or bundle_meta.get("library_tier")
        or source_bundle.get("tier")
        or "named_minimal"
    ).strip()
    if library_tier not in {"core_full", "recurring_standard", "named_minimal", "restricted_partial"}:
        library_tier = "named_minimal"
    bundle_target = character_bundle_target(root, as_id, as_name)
    if bundle_target.exists() and not args.replace:
        raise ValueError(f"target character bundle already exists: {bundle_target} (use --replace)")

    # fork 溯源链：先继承源角色自带的 fork_history（源若本身是 fork 来的，链 A→B→C 不断），
    # 再追加本次条目；entry 键严格按契约 IDENTITY_FORK_HISTORY_ENTRY_FIELDS 构造。
    inherited_history = [dict(e) for e in source_char.get(IDENTITY_FORK_HISTORY_FIELD) or [] if isinstance(e, dict)]
    fork_reason = f"import-character fork 为 {as_id}/{as_name}"
    if preserve_reason:
        fork_reason += f"；{preserve_reason}"
    fork_values = {
        "from_pack": str(pack_path),
        "from_slug": str(pack.get("slug", "")),
        "from_character_id": source_character_id,
        "forked_at": now_iso(),
        "reason": fork_reason,
    }
    source_char[IDENTITY_FORK_HISTORY_FIELD] = inherited_history + [
        {key: fork_values.get(key, "") for key in IDENTITY_FORK_HISTORY_ENTRY_FIELDS}
    ]

    source_char["id"] = as_id
    source_char["name"] = as_name
    # 单层旧字段继续兼容（指向最近一次来源；多级链看 fork_history）
    source_char["source_asset_pack"] = str(pack_path)
    source_char["source_asset_slug"] = pack.get("slug", "")
    source_char["scope"] = args.scope or source_char.get("scope") or "全篇"
    source_char["library_tier"] = library_tier
    source_char["asset_bundle"] = target_character_bundle_ref(root, as_id, as_name, library_tier)

    forms = [form for form in (source_char.get("forms", []) or []) if isinstance(form, dict)]
    multi_form = len(forms) > 1
    for form in forms:
        form["asset_key"] = args.asset_key or as_name
        if args.form:
            form["form"] = args.form
        ref = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
        new_ref: Dict[str, str] = {}
        for role, value in ref.items():
            pack_rel = ref_value_to_path(value)
            if not pack_rel:
                new_ref[str(role)] = ""
                continue
            source = pack_root / pack_rel
            suffix = source.suffix or ".png"
            target_rel = target_reference_path(as_name, str(role), suffix, str(form.get("form", "")) if multi_form else "")
            target = root / target_rel
            if source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                new_ref[str(role)] = target_rel
            else:
                new_ref[str(role)] = ""
        form["reference_group"] = new_ref
        if not args.preserve_adapters:
            reset = reset_identity_adapters()
            review = reset_preserve_review(form.get("identity_adapters"), reset, pack_path=pack_path)
            if review:
                form["preserve_review"] = review  # 审计痕迹：被重置/移除的后端身份，导入者可见
            form["identity_adapters"] = reset
        else:
            form["identity_adapters"] = downgrade_preserved_adapters(
                form.get("identity_adapters"),
                reason=preserve_reason,
                pack_path=pack_path,
            )

    registry = ensure_registry(root)
    merge_character(registry, source_char, replace=args.replace)
    land_character_bundle(
        root,
        pack_root,
        pack,
        character_id=as_id,
        name=as_name,
        tier=library_tier,
        source_character_id=source_character_id,
        source_name=str(fragment_chars[0].get("name") or ""),
        replace=args.replace,
    )
    write_json(registry_path(root), registry)

    adapter_strategy = "已保留为 candidate 参考，需在本项目重新审核/注册" if args.preserve_adapters else "已重置，需按新项目重新注册"
    append_import_log(
        root,
        f"""## {now_iso()} 导入角色资产

- 来源：`{pack_path}`
- 新角色：`{as_id}` / {as_name}
- 策略：fork 新身份；native adapters {adapter_strategy}
- 下一步：`python3 skills/n2d/n2d-identity/scripts/identity.py '{root}' --write`
""",
    )
    print(f"[ok] imported character {as_id} / {as_name} into {registry_path(root)}")
    print(f"[next] python3 skills/n2d/n2d-identity/scripts/identity.py '{root}' --write")
    return 0


def cmd_export_asset(args: argparse.Namespace) -> int:
    asset_type = str(args.asset_type)
    root = Path(args.project_root)
    registry = load_asset_registry(root)
    asset = find_asset(
        registry,
        asset_id=args.asset_id or "",
        name=args.asset_name or "",
        asset_type=asset_type,
    )
    validate_asset_id_prefix(asset_type, str(asset.get("id", "")).strip())
    title = args.title or str(asset.get("name") or asset.get("id") or asset_type)
    slug = slugify(args.slug or title)
    out_dir = pack_dir(selected_library(args, root), asset_type, slug)
    if out_dir.exists() and not args.force:
        raise FileExistsError(f"asset pack already exists, use --force: {out_dir}")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = copy_asset_reference_files(root, out_dir, asset)

    pack = {
        "kind": PACK_KIND,
        "version": PACK_VERSION,
        "asset_type": asset_type,
        "slug": slug,
        "title": title,
        "source_project": str(root),
        "source_project_name": project_name(root),
        "exported_at": now_iso(),
        "license": {
            "status": args.license_status,
            "reuse": args.reuse,
            "notes": args.license_notes or "",
        },
        "style_tags": args.style_tag or [],
        "tags": args.tag or [],
        "asset_registry_fragment": {"kind": ASSET_REGISTRY_KIND, "version": 1, "assets": [asset]},
        "files": files,
        "portability": portability_block(files),
        "reminders": [
            "导入到新剧时必须按新项目命名/ID 合并，避免 LOC_/PROP_/WEAPON_/OUTFIT_/VFX_ 冲突。",
            "非角色资产模板只复用结构、参考图和约束；新剧仍要按剧情校准 constraints/lifecycle/profile。",
            "导入后重跑 image/video gate，确认逐镜 prompt 已绑定对应资产 ID。",
        ],
    }
    write_json(out_dir / "asset_pack.json", pack)
    print(f"[ok] exported {asset_type} asset pack: {out_dir}")
    return 0


@with_registry_lock
def cmd_import_asset(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    pack_dir_path = Path(args.pack)
    pack_path = pack_dir_path / "asset_pack.json" if pack_dir_path.is_dir() else pack_dir_path
    pack_root = pack_path.parent
    pack = read_json(pack_path)
    expected = str(args.asset_type)
    if pack.get("kind") != PACK_KIND or pack.get("asset_type") not in _asset_type_aliases(expected):
        raise ValueError(f"not a {expected} asset pack: {pack_path}")
    fragment_assets = pack.get("asset_registry_fragment", {}).get("assets", [])
    if not fragment_assets:
        raise ValueError(f"asset pack has no asset registry fragment: {pack_path}")
    source_asset = copy.deepcopy(fragment_assets[0])
    as_name = args.as_name or str(source_asset.get("name") or pack.get("title") or expected)
    as_id = args.as_id or str(source_asset.get("id") or "").strip()
    if not as_id:
        raise ValueError("--as-id is required when pack has no source id")
    validate_asset_id_prefix(expected, as_id)

    source_asset["id"] = as_id
    source_asset["name"] = as_name
    source_asset["source_asset_pack"] = str(pack_path)
    source_asset["source_asset_slug"] = pack.get("slug", "")
    if args.scope:
        source_asset["scope"] = args.scope
    if args.owner and str(source_asset.get("type", "")).strip() in (_asset_type_aliases("prop") | _asset_type_aliases("weapon")):
        source_asset["owner"] = args.owner

    ref = source_asset.get("reference_group") if isinstance(source_asset.get("reference_group"), Mapping) else {}
    new_ref: Dict[str, str] = {}
    for role, value in ref.items():
        pack_rel = ref_value_to_path(value)
        if not pack_rel:
            new_ref[str(role)] = ""
            continue
        source = pack_root / pack_rel
        suffix = source.suffix or ".png"
        target_rel = target_asset_reference_path(as_name, str(role), suffix)
        target = root / target_rel
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            new_ref[str(role)] = target_rel
        else:
            new_ref[str(role)] = ""
    source_asset["reference_group"] = new_ref

    registry = ensure_asset_registry(root)
    merge_asset(registry, source_asset, replace=args.replace)
    write_json(asset_ref_registry_path(root), registry)

    append_import_log(
        root,
        f"""## {now_iso()} 导入{expected}资产

- 来源：`{pack_path}`
- 新资产：`{as_id}` / {as_name}
- 下一步：在出图 prompt 的「资产引用注册层」绑定 `{as_id}`，并重跑 image/video gate。
""",
    )
    print(f"[ok] imported {expected} {as_id} / {as_name} into {asset_ref_registry_path(root)}")
    return 0


def cmd_export_routes(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    route_path = root / "出视频" / args.episode / "prompt" / "video_model_routes.json"
    if args.routes_json:
        route_path = Path(args.routes_json)
    if not route_path.is_file():
        raise FileNotFoundError(f"video_model_routes.json not found: {route_path}")
    routes = read_json(route_path)
    slug = slugify(args.slug or f"{project_name(root)}-{args.episode}-routes")
    out_dir = pack_dir(selected_library(args, root), "route_template", slug)
    if out_dir.exists() and not args.force:
        raise FileExistsError(f"route template already exists, use --force: {out_dir}")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pack = {
        "kind": PACK_KIND,
        "version": PACK_VERSION,
        "asset_type": "route_template",
        "slug": slug,
        "title": args.title or f"{project_name(root)} {args.episode} 模型路由模板",
        "source_project": str(root),
        "source_episode": args.episode,
        "exported_at": now_iso(),
        "style_tags": args.style_tag or [],
        "tags": args.tag or [],
        "route_template": routes,
        "portability": portability_block(),
        "reminders": [
            "路由模板只做参考，不直接覆盖新剧逐 Clip 路由。",
            "新剧仍需按 storyboard 重新运行 n2d-model-router。",
        ],
    }
    write_json(out_dir / "asset_pack.json", pack)
    print(f"[ok] exported route template pack: {out_dir}")
    return 0


def cmd_import_routes(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    pack_dir_path = Path(args.pack)
    pack_path = pack_dir_path / "asset_pack.json" if pack_dir_path.is_dir() else pack_dir_path
    pack = read_json(pack_path)
    if pack.get("kind") != PACK_KIND or pack.get("asset_type") != "route_template":
        raise ValueError(f"not a route template pack: {pack_path}")
    target = root / "生产数据" / "imported_route_templates" / f"{pack.get('slug') or pack_path.parent.name}.json"
    write_json(target, pack)
    print(f"[ok] imported route template reference: {target}")
    print("[next] 新剧仍要运行 n2d-model-router；这个模板用于人工/agent 对照，不直接覆盖逐 Clip 路由。")
    return 0


# ── 母题(motif) pack：跨剧复用系统面板等复现桥段 ─────────────────────────────────

def motif_registry_path(root: Path) -> Path:
    return Path(shared_asset_path(str(root), "motif_registry.json", prefer_existing=False))


def load_motif_registry(root: Path) -> Dict[str, Any]:
    path = motif_registry_path(root)
    if not path.is_file():
        raise FileNotFoundError(f"motif_registry.json not found: {path}")
    data = read_json(path)
    if not isinstance(data, dict) or data.get("kind") != MOTIF_REGISTRY_KIND:
        raise ValueError(f"invalid motif_registry.json: {path}")
    return data


def find_motif(registry: Mapping[str, Any], motif_id: str) -> Dict[str, Any]:
    for m in registry.get("motifs", []) or []:
        if isinstance(m, dict) and str(m.get("motif_id")) == motif_id:
            return m
    raise KeyError(f"motif not found in motif_registry: {motif_id}")


def cmd_export_motif(args: argparse.Namespace) -> int:
    """导出一个母题（默认系统面板）为可复用 pack：母题定义 + 绑定的成长 VFX + 参考图。"""
    root = Path(args.project_root)
    motif_id = args.motif_id or SYSTEM_PANEL_MOTIF_ID
    motif = copy.deepcopy(find_motif(load_motif_registry(root), motif_id))
    title = args.title or str(motif.get("motif_type") or motif_id)
    slug = slugify(args.slug or title)
    out_dir = pack_dir(selected_library(args, root), "motif", slug)
    if out_dir.exists() and not args.force:
        raise FileExistsError(f"motif pack already exists, use --force: {out_dir}")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 绑定的成长 VFX（从 asset_registry 抽出 + 拷参考图），新剧 import 时一并落地。
    gsm = motif.get("growth_state_machine") if isinstance(motif.get("growth_state_machine"), dict) else {}
    bound_vfx_id = str(gsm.get("bound_vfx") or "")
    vfx_assets: List[Dict[str, Any]] = []
    files: List[Dict[str, Any]] = []
    if bound_vfx_id:
        try:
            vfx_asset = copy.deepcopy(find_asset(load_asset_registry(root), asset_id=bound_vfx_id))
            files = copy_asset_reference_files(root, out_dir, vfx_asset)
            vfx_assets.append(vfx_asset)
        except (FileNotFoundError, KeyError, ValueError):
            print(f"[warn] 绑定 VFX `{bound_vfx_id}` 未在 asset_registry 找到——pack 只含母题定义，导入后需补建 VFX。")

    pack = {
        "kind": PACK_KIND,
        "version": PACK_VERSION,
        "asset_type": "motif",
        "slug": slug,
        "title": title,
        "source_project": str(root),
        "source_project_name": project_name(root),
        "exported_at": now_iso(),
        "license": {"status": args.license_status, "reuse": args.reuse, "notes": args.license_notes or ""},
        "style_tags": args.style_tag or [],
        "tags": args.tag or [],
        "motif_fragment": {"kind": MOTIF_REGISTRY_KIND, "version": 1, "motifs": [motif]},
        "asset_registry_fragment": {"kind": ASSET_REGISTRY_KIND, "version": 1, "assets": vfx_assets},
        "files": files,
        "portability": portability_block(files),
        "reminders": [
            "母题模板只复用结构（镜头模板/台词腔/VFX 定妆/overlay 规格），不复用具体剧情数值。",
            "导入到新剧时 progression 成长档会被重置（新剧从 Lv.1 起按自身剧情重排）。",
            "导入后跑 motif_detector 在新剧分镜上重新检测桥段、绑定 Clip，再重跑 image/video gate。",
        ],
    }
    write_json(out_dir / "asset_pack.json", pack)
    print(f"[ok] exported motif pack: {out_dir}")
    return 0


@with_registry_lock
def cmd_import_motif(args: argparse.Namespace) -> int:
    """把母题 pack 合并进目标项目 motif_registry.json + asset_registry.json，重置成长 progression。"""
    root = Path(args.project_root)
    pack_dir_path = Path(args.pack)
    pack_path = pack_dir_path / "asset_pack.json" if pack_dir_path.is_dir() else pack_dir_path
    pack_root = pack_path.parent
    pack = read_json(pack_path)
    if pack.get("kind") != PACK_KIND or pack.get("asset_type") != "motif":
        raise ValueError(f"not a motif pack: {pack_path}")
    motifs = pack.get("motif_fragment", {}).get("motifs", [])
    if not motifs:
        raise ValueError(f"motif pack has no motif fragment: {pack_path}")
    motif = copy.deepcopy(motifs[0])
    if args.as_id:
        motif["motif_id"] = args.as_id
    motif["source_motif_pack"] = str(pack_path)
    motif["source_motif_slug"] = pack.get("slug", "")
    # 重置成长档：新剧从 Lv.1 起，按自身剧情重排（类比 import-character 重置 Character ID）。
    gsm = motif.get("growth_state_machine") if isinstance(motif.get("growth_state_machine"), dict) else {}
    if isinstance(gsm, dict):
        gsm["progression"] = []

    # 合并绑定 VFX 进 asset_registry + 拷参考图（新剧路径）。
    vfx_assets = pack.get("asset_registry_fragment", {}).get("assets", []) or []
    if vfx_assets:
        vfx = copy.deepcopy(vfx_assets[0])
        as_name = str(vfx.get("name") or vfx.get("id") or "系统面板")
        ref = vfx.get("reference_group") if isinstance(vfx.get("reference_group"), Mapping) else {}
        new_ref: Dict[str, str] = {}
        for role, value in ref.items():
            pack_rel = ref_value_to_path(value)
            if not pack_rel:
                new_ref[str(role)] = ""
                continue
            source = pack_root / pack_rel
            target_rel = target_asset_reference_path(as_name, str(role), source.suffix or ".png")
            target = root / target_rel
            if source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                new_ref[str(role)] = target_rel
            else:
                new_ref[str(role)] = ""
        vfx["reference_group"] = new_ref
        asset_reg = ensure_asset_registry(root)
        merge_asset(asset_reg, vfx, replace=args.replace)
        write_json(asset_ref_registry_path(root), asset_reg)

    # 合并母题进 motif_registry（去重 motif_id）。
    mpath = motif_registry_path(root)
    if mpath.is_file():
        mreg = read_json(mpath)
        if not isinstance(mreg, dict) or mreg.get("kind") != MOTIF_REGISTRY_KIND:
            mreg = {"kind": MOTIF_REGISTRY_KIND, "version": 1, "motifs": []}
    else:
        mreg = {"kind": MOTIF_REGISTRY_KIND, "version": 1, "motifs": []}
    mid = str(motif.get("motif_id"))
    existing = [m for m in mreg.get("motifs", []) if isinstance(m, dict) and str(m.get("motif_id")) == mid]
    if existing and not args.replace:
        raise ValueError(f"motif id already exists: {mid} (use --replace)")
    mreg["motifs"] = [m for m in mreg.get("motifs", []) if not (isinstance(m, dict) and str(m.get("motif_id")) == mid)]
    mreg["motifs"].append(motif)
    write_json(mpath, mreg)

    append_import_log(
        root,
        f"""## {now_iso()} 导入母题(motif)

- 来源：`{pack_path}`
- 母题：`{mid}`（progression 已重置，新剧从 Lv.1 起）
- 下一步：在新剧分镜上跑 `motif_detector.py <作品根> 第N集` 重新检测桥段并 --write 绑定 Clip，再重跑 image/video gate。
""",
    )
    print(f"[ok] imported motif {mid} into {mpath}（progression 已重置）")
    return 0


# ── 招式/打斗(combat) pack：跨剧复用一整套打斗套路 ─────────────────────────────
#
# 一套打斗 = 招式骨架(SM_ 五帧拆招 + action_choreography 契约) + 节奏 preset + 绑定的
# WEAPON_/VFX_ 实体。跨剧复用的是【结构】，不是【同一把可识别武器/同一条数值】：导入即
# reskin——保留五帧/力链/contact/速度曲线骨架，清掉项目专属的关键帧 PNG（须在新剧重出图、
# 重过 image/video gate），并提示换皮（元素主色/武器剪影/角色）。与 import-character 重置
# Character ID、import-motif 重置 progression 同构。

def combat_registry_path(root: Path) -> Path:
    return Path(shared_asset_path(str(root), "combat_registry.json", prefer_existing=False))


def load_combat_registry(root: Path) -> Dict[str, Any]:
    path = combat_registry_path(root)
    if not path.is_file():
        raise FileNotFoundError(f"combat_registry.json not found: {path}")
    data = read_json(path)
    if not isinstance(data, dict) or data.get("kind") != COMBAT_REGISTRY_KIND:
        raise ValueError(f"invalid combat_registry.json: {path}")
    return data


def find_combat_set(registry: Mapping[str, Any], combat_id: str = "") -> Dict[str, Any]:
    sets = [s for s in registry.get("combat_sets", []) or [] if isinstance(s, dict)]
    if not sets:
        raise KeyError("combat_registry has no combat_sets")
    if not combat_id:
        return copy.deepcopy(sets[0])
    for s in sets:
        if str(s.get("combat_id")) == combat_id:
            return copy.deepcopy(s)
    raise KeyError(f"combat set not found in combat_registry: {combat_id}")


def bound_asset_ids(combat_set: Mapping[str, Any]) -> List[str]:
    """绑定的武器+特效资产 id（去重保序）：先 WEAPON_ 后 VFX_。"""
    ids: List[str] = []
    for key in ("bound_weapons", "bound_vfx"):
        for aid in combat_set.get(key, []) or []:
            aid = str(aid).strip()
            if aid and aid not in ids:
                ids.append(aid)
    return ids


def land_asset_reference_files(root: Path, pack_root: Path, asset: Dict[str, Any]) -> None:
    """把 pack 内某资产的相对参考图落到目标项目共享 图片/，并把 reference_group 改写成项目相对路径。"""
    as_name = str(asset.get("name") or asset.get("id") or "asset")
    ref = asset.get("reference_group") if isinstance(asset.get("reference_group"), Mapping) else {}
    new_ref: Dict[str, str] = {}
    for role, value in ref.items():
        pack_rel = ref_value_to_path(value)
        if not pack_rel:
            new_ref[str(role)] = ""
            continue
        source = pack_root / pack_rel
        target_rel = target_asset_reference_path(as_name, str(role), source.suffix or ".png")
        target = root / target_rel
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            new_ref[str(role)] = target_rel
        else:
            new_ref[str(role)] = ""
    asset["reference_group"] = new_ref


def reskin_reset_combat_set(combat_set: Dict[str, Any]) -> List[str]:
    """导入时 reskin 重置：清掉每招项目专属的关键帧 PNG 引用（须新剧重出图），保留五帧/编排骨架。
    返回被清掉的关键帧路径清单，写进导入日志，让导入者知道要重出哪些图。"""
    cleared: List[str] = []
    for move in combat_set.get("moves", []) or []:
        if not isinstance(move, dict):
            continue
        kf = move.get("keyframe_refs")
        if isinstance(kf, Mapping):
            for slot, path in kf.items():
                p = ref_value_to_path(path)
                if p:
                    cleared.append(f"{move.get('move_id') or move.get('name') or '招式'}/{slot}: {p}")
        # 关键帧不迁移：和 .safetensors/Character ID 同理，是项目专属可执行产物，须新剧重出。
        move["keyframe_refs"] = {}
        move["needs_keyframe_regen"] = True
    return cleared


def cmd_export_combat(args: argparse.Namespace) -> int:
    """导出一套打斗 pack：combat set(招式五帧+编排+节奏) + 绑定的 WEAPON_/VFX_ + 参考图。"""
    root = Path(args.project_root)
    combat_set = find_combat_set(load_combat_registry(root), args.combat_id or "")
    title = args.title or str(combat_set.get("name") or combat_set.get("combat_id") or "combat")
    slug = slugify(args.slug or title)
    out_dir = pack_dir(selected_library(args, root), "combat", slug)
    if out_dir.exists() and not args.force:
        raise FileExistsError(f"combat pack already exists, use --force: {out_dir}")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 绑定的武器+特效实体（从 asset_registry 抽出 + 拷参考图），新剧 import 时一并落地。
    bound_assets: List[Dict[str, Any]] = []
    files: List[Dict[str, Any]] = []
    missing: List[str] = []
    bound_ids = bound_asset_ids(combat_set)
    if bound_ids:
        try:
            asset_reg = load_asset_registry(root)
        except (FileNotFoundError, ValueError):
            asset_reg = empty_asset_registry()
        for aid in bound_ids:
            try:
                asset = copy.deepcopy(find_asset(asset_reg, asset_id=aid))
            except (KeyError, ValueError):
                missing.append(aid)
                continue
            files.extend(copy_asset_reference_files(root, out_dir, asset))
            bound_assets.append(asset)
    if missing:
        print(f"[warn] 绑定资产未在 asset_registry 找到，pack 只含招式结构: {', '.join(missing)}")

    pack = {
        "kind": PACK_KIND,
        "version": PACK_VERSION,
        "asset_type": "combat",
        "slug": slug,
        "title": title,
        "source_project": str(root),
        "source_project_name": project_name(root),
        "exported_at": now_iso(),
        "license": {"status": args.license_status, "reuse": args.reuse, "notes": args.license_notes or ""},
        "style_tags": args.style_tag or [],
        "tags": args.tag or [],
        "combat_fragment": {"kind": COMBAT_REGISTRY_KIND, "version": 1, "combat_sets": [combat_set]},
        "asset_registry_fragment": {"kind": ASSET_REGISTRY_KIND, "version": 1, "assets": bound_assets},
        "files": files,
        "portability": portability_block(files),
        "reminders": [
            "打斗 pack 只复用结构：五帧拆招/力链/contact/速度曲线/节奏 preset + 武器VFX定妆锁形，不复用同一把可识别武器或具体数值。",
            "导入到新剧时关键帧 PNG 会被清空（reskin）：必须在新剧重出起手/命中关键帧，再过 image/video gate。",
            "换皮提示：元素主色(如暗金→雷蓝)/武器剪影/角色按新剧改；五帧与 action_choreography 骨架原样继承。",
        ],
    }
    write_json(out_dir / "asset_pack.json", pack)
    print(f"[ok] exported combat pack: {out_dir}")
    return 0


@with_registry_lock
def cmd_import_combat(args: argparse.Namespace) -> int:
    """把打斗 pack 合并进目标 combat_registry + asset_registry，reskin 重置(清关键帧)。"""
    root = Path(args.project_root)
    pack_dir_path = Path(args.pack)
    pack_path = pack_dir_path / "asset_pack.json" if pack_dir_path.is_dir() else pack_dir_path
    pack_root = pack_path.parent
    pack = read_json(pack_path)
    if pack.get("kind") != PACK_KIND or pack.get("asset_type") != "combat":
        raise ValueError(f"not a combat pack: {pack_path}")
    sets = pack.get("combat_fragment", {}).get("combat_sets", [])
    if not sets:
        raise ValueError(f"combat pack has no combat fragment: {pack_path}")
    combat_set = copy.deepcopy(sets[0])
    if args.as_id:
        combat_set["combat_id"] = args.as_id
    combat_set["source_combat_pack"] = str(pack_path)
    combat_set["source_combat_slug"] = pack.get("slug", "")
    cleared = reskin_reset_combat_set(combat_set)

    # 合并绑定 WEAPON_/VFX_ 进 asset_registry + 拷参考图（新剧路径）。
    bound = pack.get("asset_registry_fragment", {}).get("assets", []) or []
    landed_ids: List[str] = []
    if bound:
        asset_reg = ensure_asset_registry(root)
        for raw in bound:
            asset = copy.deepcopy(raw)
            asset["source_asset_pack"] = str(pack_path)
            asset["source_asset_slug"] = pack.get("slug", "")
            land_asset_reference_files(root, pack_root, asset)
            merge_asset(asset_reg, asset, replace=args.replace)
            landed_ids.append(str(asset.get("id", "")).strip())
        write_json(asset_ref_registry_path(root), asset_reg)

    # 合并 combat set 进 combat_registry（去重 combat_id）。
    cpath = combat_registry_path(root)
    if cpath.is_file():
        creg = read_json(cpath)
        if not isinstance(creg, dict) or creg.get("kind") != COMBAT_REGISTRY_KIND:
            creg = {"kind": COMBAT_REGISTRY_KIND, "version": 1, "combat_sets": []}
    else:
        creg = {"kind": COMBAT_REGISTRY_KIND, "version": 1, "combat_sets": []}
    cid = str(combat_set.get("combat_id"))
    existing = [s for s in creg.get("combat_sets", []) if isinstance(s, dict) and str(s.get("combat_id")) == cid]
    if existing and not args.replace:
        raise ValueError(f"combat id already exists: {cid} (use --replace)")
    creg["combat_sets"] = [s for s in creg.get("combat_sets", []) if not (isinstance(s, dict) and str(s.get("combat_id")) == cid)]
    creg["combat_sets"].append(combat_set)
    write_json(cpath, creg)

    cleared_md = "\n".join(f"  - {c}" for c in cleared) if cleared else "  - （无登记关键帧）"
    append_import_log(
        root,
        f"""## {now_iso()} 导入招式/打斗(combat)

- 来源：`{pack_path}`
- 打斗套路：`{cid}`（已 reskin 重置：清空关键帧 PNG，保留五帧+编排骨架）
- 绑定资产合并进 asset_registry：{', '.join(landed_ids) or '（无）'}
- 待新剧重出的关键帧：
{cleared_md}
- 下一步：在新剧分镜按五帧拆招把该套路织进 `故事板.md`，换皮(元素主色/武器/角色)，重出起手/命中关键帧，再重跑 image/video gate。
""",
    )
    print(f"[ok] imported combat {cid} into {cpath}（已 reskin 重置，需重出关键帧）")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="n2d cross-project asset pack market")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("hint", help="show natural-language trigger hints")
    p.set_defaults(func=cmd_hint)

    p = sub.add_parser("list", help="list local asset packs")
    p.add_argument("--library", default="", help=f"override series library (default: {DEFAULT_LIBRARY})")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("verify-pack", help="verify one self-contained asset pack for file handoff")
    p.add_argument("pack")
    p.set_defaults(func=cmd_verify_pack)

    p = sub.add_parser("export-character", help="export one registry character as an asset pack")
    p.add_argument("project_root")
    p.add_argument("--character-id", default="")
    p.add_argument("--character-name", default="")
    p.add_argument("--form", default="")
    p.add_argument("--title", default="")
    p.add_argument("--slug", default="")
    p.add_argument("--library", default="", help="override; default is <project series>/_资产库")
    p.add_argument("--force", action="store_true")
    p.add_argument("--license-status", default="user_owned_or_synthetic")
    p.add_argument("--reuse", default="template_only", choices=["template_only", "same_ip", "licensed_reuse"])
    p.add_argument("--license-notes", default="")
    p.add_argument("--style-tag", action="append")
    p.add_argument("--tag", action="append")
    p.set_defaults(func=cmd_export_character)

    p = sub.add_parser("import-character", help="fork a character asset pack into a target project")
    p.add_argument("project_root")
    p.add_argument("pack")
    p.add_argument("--as-id", required=True)
    p.add_argument("--as-name", required=True)
    p.add_argument("--asset-key", default="")
    p.add_argument("--form", default="")
    p.add_argument("--scope", default="")
    p.add_argument("--replace", action="store_true")
    p.add_argument("--preserve-adapters", action="store_true")
    p.add_argument("--preserve-reason", default="")
    p.set_defaults(func=cmd_import_character)

    def add_export_asset_parser(name: str, asset_type: str, help_text: str) -> None:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("project_root")
        p.add_argument("--asset-id", default="")
        p.add_argument("--asset-name", default="")
        p.add_argument("--title", default="")
        p.add_argument("--slug", default="")
        p.add_argument("--library", default="", help="override; default is <project series>/_资产库")
        p.add_argument("--force", action="store_true")
        p.add_argument("--license-status", default="user_owned_or_synthetic")
        p.add_argument("--reuse", default="template_only", choices=["template_only", "same_ip", "licensed_reuse"])
        p.add_argument("--license-notes", default="")
        p.add_argument("--style-tag", action="append")
        p.add_argument("--tag", action="append")
        p.set_defaults(func=cmd_export_asset, asset_type=asset_type)

    def add_import_asset_parser(name: str, asset_type: str, help_text: str) -> None:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("project_root")
        p.add_argument("pack")
        p.add_argument("--as-id", required=True)
        p.add_argument("--as-name", required=True)
        p.add_argument("--scope", default="")
        p.add_argument("--owner", default="", help="prop/weapon owner override, e.g. CHAR_SHEN")
        p.add_argument("--replace", action="store_true")
        p.set_defaults(func=cmd_import_asset, asset_type=asset_type)

    add_export_asset_parser("export-scene", "scene", "export one LOC_/scene asset as an asset pack")
    add_import_asset_parser("import-scene", "scene", "import a scene asset pack into target asset_registry")
    add_export_asset_parser("export-prop", "prop", "export one PROP_/prop asset as an asset pack")
    add_import_asset_parser("import-prop", "prop", "import a prop asset pack into target asset_registry")
    add_export_asset_parser("export-weapon", "weapon", "export one WEAPON_/weapon asset as an asset pack")
    add_import_asset_parser("import-weapon", "weapon", "import a weapon asset pack into target asset_registry")
    add_export_asset_parser("export-outfit", "outfit", "export one OUTFIT_/outfit asset as an asset pack")
    add_import_asset_parser("import-outfit", "outfit", "import an outfit asset pack into target asset_registry")
    add_export_asset_parser("export-vfx", "vfx", "export one VFX_/effect asset as an asset pack")
    add_import_asset_parser("import-vfx", "vfx", "import a VFX asset pack into target asset_registry")

    p = sub.add_parser("export-routes", help="export a video_model_routes.json as a route template pack")
    p.add_argument("project_root")
    p.add_argument("episode")
    p.add_argument("--routes-json", default="")
    p.add_argument("--title", default="")
    p.add_argument("--slug", default="")
    p.add_argument("--library", default="", help="override; default is <project series>/_资产库")
    p.add_argument("--force", action="store_true")
    p.add_argument("--style-tag", action="append")
    p.add_argument("--tag", action="append")
    p.set_defaults(func=cmd_export_routes)

    p = sub.add_parser("import-routes", help="copy a route template pack into a target project as reference")
    p.add_argument("project_root")
    p.add_argument("pack")
    p.set_defaults(func=cmd_import_routes)

    p = sub.add_parser("export-motif", help="export a motif (e.g. 系统面板) + its growth VFX as a reusable pack")
    p.add_argument("project_root")
    p.add_argument("--motif-id", default="", help=f"母题 id（默认 {SYSTEM_PANEL_MOTIF_ID}）")
    p.add_argument("--title", default="")
    p.add_argument("--slug", default="")
    p.add_argument("--library", default="", help="override; default is <project series>/_资产库")
    p.add_argument("--force", action="store_true")
    p.add_argument("--license-status", default="user_owned_or_synthetic")
    p.add_argument("--reuse", default="template_only", choices=["template_only", "same_ip", "licensed_reuse"])
    p.add_argument("--license-notes", default="")
    p.add_argument("--style-tag", action="append")
    p.add_argument("--tag", action="append")
    p.set_defaults(func=cmd_export_motif)

    p = sub.add_parser("import-motif", help="merge a motif pack into target motif_registry + asset_registry (progression reset)")
    p.add_argument("project_root")
    p.add_argument("pack")
    p.add_argument("--as-id", default="", help="rename motif_id in target (default keep source id)")
    p.add_argument("--replace", action="store_true")
    p.set_defaults(func=cmd_import_motif)

    p = sub.add_parser("export-combat", help="export a combat set (招式五帧+编排+绑定WEAPON_/VFX_) as a reusable pack")
    p.add_argument("project_root")
    p.add_argument("--combat-id", default="", help="combat_id（默认导出 combat_registry 第一条）")
    p.add_argument("--title", default="")
    p.add_argument("--slug", default="")
    p.add_argument("--library", default="", help="override; default is <project series>/_资产库")
    p.add_argument("--force", action="store_true")
    p.add_argument("--license-status", default="user_owned_or_synthetic")
    p.add_argument("--reuse", default="template_only", choices=["template_only", "same_ip", "licensed_reuse"])
    p.add_argument("--license-notes", default="")
    p.add_argument("--style-tag", action="append")
    p.add_argument("--tag", action="append")
    p.set_defaults(func=cmd_export_combat)

    p = sub.add_parser("import-combat", help="merge a combat pack into target combat_registry + asset_registry (reskin: keyframes cleared)")
    p.add_argument("project_root")
    p.add_argument("pack")
    p.add_argument("--as-id", default="", help="rename combat_id in target (default keep source id)")
    p.add_argument("--replace", action="store_true")
    p.set_defaults(func=cmd_import_combat)

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
