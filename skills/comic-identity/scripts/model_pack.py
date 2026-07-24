#!/usr/bin/env python3
"""Deterministic comic turnaround/model-pack evidence and SHA-bound approval.

The checker blocks only reproducible technical defects.  Optional pixel
similarity is a warning signal; visual identity, pose and baseline alignment
are confirmed by a human receipt bound to the exact view hashes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import struct
from pathlib import Path
from typing import Any, Mapping, Sequence

from registry_v2 import canonical_json, migrate_registry


KIND = "comic_character_model_pack"
VERSION = 1
PNG_SIG = b"\x89PNG\r\n\x1a\n"
FULL_BODY_VIEWS = ("front", "three_quarter", "side", "back")
REQUIRED_CONFIRMATIONS = (
    "same_character",
    "correct_view_labels",
    "proportions_aligned",
    "baseline_aligned",
    "outfit_and_markers_consistent",
    "neutral_pose_usable",
)
TIER_REQUIRED_VIEWS = {
    "core_full": ("front", "three_quarter", "side", "back", "face"),
    "recurring_standard": ("front", "three_quarter", "face"),
    "named_minimal": ("front", "face"),
    # 2026-07-23 实证修正：restricted_partial 曾是 ()——零必需视图 + signoff_required=False
    # + readiness 自动 ready，等于整档免检旁路。第1话全员标此档后「多视图齐套 pass」，
    # 画皮鬼单锚图零签收，4/5 实体当话即漂移。最低档也必须有一张正面锚 + 人审签收。
    "restricted_partial": ("front",),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_path(root: Path, raw: str) -> Path:
    path = Path(str(raw or ""))
    return path if path.is_absolute() else root / path


def rel_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def png_dimensions(path: Path) -> tuple[int, int] | None:
    """Read PNG IHDR without Pillow; malformed/truncated files return None."""
    try:
        data = path.read_bytes()[:24]
    except OSError:
        return None
    if len(data) < 24 or path.stat().st_size < 33 or data[:8] != PNG_SIG or data[8:12] != b"\x00\x00\x00\r" or data[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", data[16:24])
    return (int(width), int(height)) if width and height else None


def required_views(asset: Mapping[str, Any]) -> tuple[str, ...]:
    tier = str(asset.get("library_tier") or asset.get("tier") or "core_full")
    return TIER_REQUIRED_VIEWS.get(tier, TIER_REQUIRED_VIEWS["core_full"])


def _view_record(asset: Mapping[str, Any], view: str) -> dict[str, Any]:
    for item in asset.get("reference_images") or []:
        if isinstance(item, Mapping) and str(item.get("view") or "") == view:
            return dict(item)
    views = asset.get("views") if isinstance(asset.get("views"), Mapping) else {}
    raw = str(views.get(view) or "").strip()
    return {"view": view, "path": raw} if raw else {}


def _heuristic_pixel_warning(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Optional low-resolution histogram proxy.  Never returns BLOCK."""
    try:
        from PIL import Image
    except Exception:
        return []
    samples: list[tuple[str, list[float]]] = []
    for row in evidence:
        if row.get("view") == "face" or not row.get("absolute_path"):
            continue
        try:
            image = Image.open(str(row["absolute_path"])).convert("RGB").resize((16, 16))
            hist = image.histogram()
            total = float(sum(hist)) or 1.0
            samples.append((str(row["view"]), [value / total for value in hist]))
        except Exception:
            continue
    if len(samples) < 2:
        return []
    base_name, base = samples[0]
    warnings: list[dict[str, Any]] = []
    for name, values in samples[1:]:
        distance = sum(abs(a - b) for a, b in zip(base, values)) / 2.0
        if distance > 0.55:
            warnings.append({
                "severity": "warn",
                "confidence": "heuristic",
                "code": "turnaround_pixel_proxy_drift",
                "message": f"{base_name}↔{name} 低分辨率色彩代理差异较大 ({distance:.3f})；请并排人审，不能据此自动判定换人",
                "metric": round(distance, 6),
            })
    return warnings


def signoff_path(root: Path, character_id: str) -> Path:
    return root / "生产数据" / "comic_model_pack_signoffs" / f"{character_id}.json"


def model_pack_fingerprint(character_id: str, tier: str, evidence: Sequence[Mapping[str, Any]]) -> str:
    material = {
        "character_id": character_id,
        "tier": tier,
        "views": [
            {
                "view": row.get("view"),
                "path": row.get("path"),
                "sha256": row.get("sha256"),
                "width": row.get("width"),
                "height": row.get("height"),
                "derivation": row.get("derivation"),
            }
            for row in evidence
        ],
    }
    return hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()


def summarize_reports(reports: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    def asset_type(row: Mapping[str, Any]) -> str:
        declared = str(row.get("asset_type") or "")
        if declared:
            return declared
        return "monster" if str(row.get("character_id") or "").startswith("MON_") else "character"

    return {
        "assets": len(reports),
        "characters": sum(1 for row in reports if asset_type(row) == "character"),
        "monsters": sum(1 for row in reports if asset_type(row) == "monster"),
        "ready": sum(1 for row in reports if row.get("readiness") == "ready"),
        "needs_approval": sum(1 for row in reports if row.get("readiness") == "needs_approval"),
        "needs_fix": sum(1 for row in reports if row.get("readiness") == "needs_fix"),
    }


def evaluate_character(root: Path, registry: Mapping[str, Any], character_id: str) -> dict[str, Any]:
    assets = registry.get("assets") if isinstance(registry.get("assets"), Mapping) else {}
    asset = assets.get(character_id) if isinstance(assets, Mapping) and isinstance(assets.get(character_id), Mapping) else {}
    tier = str(asset.get("library_tier") or asset.get("tier") or "core_full")
    required = required_views(asset)
    findings: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    full_canvas: dict[str, tuple[int, int]] = {}
    shas: dict[str, str] = {}
    origin_groups: set[str] = set()
    for view in required:
        record = _view_record(asset, view)
        raw = str(record.get("path") or "").strip()
        path = resolve_path(root, raw) if raw else Path()
        dimensions = png_dimensions(path) if raw else None
        sha = file_sha256(path) if dimensions else ""
        source = record.get("source") if isinstance(record.get("source"), Mapping) else {}
        derivation = record.get("derivation") if isinstance(record.get("derivation"), Mapping) else {}
        if not derivation and isinstance(source, Mapping):
            derivation = source.get("derivation") if isinstance(source.get("derivation"), Mapping) else {}
        row = {
            "view": view,
            "path": rel_to_root(root, path) if raw else "",
            "absolute_path": str(path) if raw else "",
            "sha256": sha,
            "width": dimensions[0] if dimensions else 0,
            "height": dimensions[1] if dimensions else 0,
            "source_view": str(source.get("view") or ""),
            "derivation": dict(derivation),
        }
        evidence.append(row)
        if not raw:
            findings.append({"severity": "block", "code": "model_pack_view_missing", "view": view, "message": f"缺必需视图 {view}"})
            continue
        if dimensions is None:
            findings.append({"severity": "block", "code": "model_pack_view_invalid_png", "view": view, "message": f"{view} 不是可读 PNG/IHDR"})
            continue
        if dimensions == (1, 1):
            findings.append({"severity": "block", "code": "model_pack_view_degenerate_1x1", "view": view, "message": f"{view} 是 1×1 占位图，不能作为定妆视图"})
        if source.get("view") and str(source.get("view")) != view:
            findings.append({"severity": "block", "code": "model_pack_source_view_mismatch", "view": view, "message": f"{view} 的来源证据声明为 {source.get('view')}"})
        if view in FULL_BODY_VIEWS:
            full_canvas[view] = dimensions
        if sha:
            if sha in shas:
                findings.append({"severity": "block", "code": "model_pack_duplicate_view_content", "view": view, "message": f"{view} 与 {shas[sha]} 是完全相同文件，不能冒充不同视角"})
            shas[sha] = view
        origin_sha = str(derivation.get("source_sha256") or "")
        if origin_sha:
            origin_groups.add(origin_sha)
        else:
            findings.append({"severity": "warn", "confidence": "deterministic", "code": "model_pack_lineage_missing", "view": view, "message": f"{view} 缺 derivation.source_sha256；旧资产可继续做人审，但不能声称已证明同源派生"})
    canvas_values = set(full_canvas.values())
    if len(canvas_values) > 1:
        findings.append({
            "severity": "block",
            "code": "model_pack_full_body_canvas_mismatch",
            "message": "全身 turnaround 视图画布尺寸不一致：" + ", ".join(f"{view}={size[0]}x{size[1]}" for view, size in sorted(full_canvas.items())),
        })
    if len(origin_groups) > 1:
        findings.append({
            "severity": "warn",
            "confidence": "deterministic",
            "code": "model_pack_lineage_groups_differ",
            "message": "required views 的 derivation.source_sha256 不同；需由人审确认确为同一母本/同一角色后签收",
        })
    findings.extend(_heuristic_pixel_warning(evidence))
    for row in evidence:
        row.pop("absolute_path", None)
    fingerprint = model_pack_fingerprint(character_id, tier, evidence)
    receipt_file = signoff_path(root, character_id)
    try:
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    except Exception:
        receipt = {}
    current_receipt = bool(
        isinstance(receipt, Mapping)
        and receipt.get("kind") == "comic_model_pack_signoff"
        and receipt.get("decision") == "approved"
        and receipt.get("character_id") == character_id
        and receipt.get("model_pack_fingerprint") == fingerprint
        and bool(str(receipt.get("reviewer") or "").strip())
        and bool(str(receipt.get("reason") or "").strip())
        and bool(str(receipt.get("approved_at") or "").strip())
        and all(bool((receipt.get("confirmations") or {}).get(key)) for key in REQUIRED_CONFIRMATIONS)
    )
    receipt_status = "current" if current_receipt else ("stale" if receipt else "missing")
    technical_block = any(item["severity"] == "block" for item in findings)
    signoff_required = bool(required)
    if technical_block:
        readiness = "needs_fix"
    elif signoff_required and not current_receipt:
        readiness = "needs_approval"
    else:
        readiness = "ready"
    return {
        "kind": KIND,
        "version": VERSION,
        "character_id": character_id,
        "asset_type": str(asset.get("type") or "character"),
        "tier": tier,
        "required_views": list(required),
        "view_evidence": evidence,
        "model_pack_fingerprint": fingerprint,
        "signoff": {
            "path": rel_to_root(root, receipt_file),
            "status": receipt_status,
            "approved_at": receipt.get("approved_at", "") if isinstance(receipt, Mapping) else "",
            "reviewer": receipt.get("reviewer", "") if isinstance(receipt, Mapping) else "",
        },
        "signoff_required": signoff_required,
        "readiness": readiness,
        "technical_block": technical_block,
        "findings": findings,
    }


def apply_character_readiness(root: Path, registry: dict[str, Any], character_id: str) -> dict[str, Any]:
    report = evaluate_character(root, registry, character_id)
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    asset = assets.get(character_id) if isinstance(assets.get(character_id), dict) else {}
    previous_pack = asset.get("model_pack") if isinstance(asset.get("model_pack"), Mapping) else {}
    next_pack = {
        "kind": KIND,
        "version": VERSION,
        "fingerprint": report["model_pack_fingerprint"],
        "readiness": report["readiness"],
        "signoff_status": report["signoff"]["status"],
        "required_views": report["required_views"],
    }
    comparable_previous = {key: value for key, value in previous_pack.items() if key != "updated_at"}
    next_pack["updated_at"] = (
        str(previous_pack.get("updated_at") or now_iso())
        if comparable_previous == next_pack
        else now_iso()
    )
    asset["model_pack"] = next_pack
    block_codes = {item["code"] for item in report["findings"] if item["severity"] == "block"}
    # "partial" remains a useful production state while views are still being
    # generated.  Technical corruption/mislabelling is a distinct needs_fix.
    asset["status"] = (
        "partial"
        if block_codes and block_codes <= {"model_pack_view_missing"}
        else report["readiness"]
    )
    assets[character_id] = asset
    registry["assets"] = assets
    return report


def create_signoff(root: Path, registry: dict[str, Any], character_id: str, reviewer: str, reason: str, confirmations: Mapping[str, bool]) -> dict[str, Any]:
    report = evaluate_character(root, registry, character_id)
    if report["technical_block"]:
        codes = ",".join(item["code"] for item in report["findings"] if item["severity"] == "block")
        raise ValueError(f"model pack has deterministic defects: {codes}")
    missing = [key for key in REQUIRED_CONFIRMATIONS if not confirmations.get(key)]
    if missing:
        raise ValueError("missing human confirmations: " + ",".join(missing))
    if not reviewer.strip() or not reason.strip():
        raise ValueError("reviewer and reason are required")
    receipt = {
        "schema_version": 1,
        "kind": "comic_model_pack_signoff",
        "decision": "approved",
        "character_id": character_id,
        "tier": report["tier"],
        "model_pack_fingerprint": report["model_pack_fingerprint"],
        "view_evidence": report["view_evidence"],
        "confirmations": {key: bool(confirmations.get(key)) for key in REQUIRED_CONFIRMATIONS},
        "reviewer": reviewer.strip(),
        "reason": reason.strip(),
        "approved_at": now_iso(),
        "policy": "human visual approval; deterministic technical defects cannot be waived; pixel proxy is warn-only",
    }
    path = signoff_path(root, character_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    apply_character_readiness(root, registry, character_id)
    return receipt


def write_stable_report(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist the shared report without timestamp-only fingerprint churn."""
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        previous = {}
    semantic = {key: value for key, value in payload.items() if key != "created_at"}
    previous_semantic = (
        {key: value for key, value in previous.items() if key != "created_at"}
        if isinstance(previous, dict)
        else {}
    )
    if semantic == previous_semantic and previous.get("created_at"):
        payload["created_at"] = previous["created_at"]
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if not path.is_file() or path.read_text(encoding="utf-8") != serialized:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding="utf-8")
    return payload


def build_montage(root: Path, registry: Mapping[str, Any], character_id: str) -> dict[str, Any]:
    """Stitch a character's required views into one labelled contact sheet so the
    定妆 human sign-off isn't semi-blind (opening five files by hand).  It's a
    review view — deletable/rebuildable, never machine truth.  No-op if Pillow is
    unavailable or no view is readable."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return {"status": "skipped", "reason": "pillow_unavailable"}
    assets = registry.get("assets") if isinstance(registry.get("assets"), Mapping) else {}
    asset = assets.get(character_id) if isinstance(assets, Mapping) and isinstance(assets.get(character_id), Mapping) else {}
    required = required_views(asset)
    if not required:
        return {"status": "skipped", "reason": "no_required_views"}
    tile_h, label_h, pad = 320, 22, 8
    thumbs: list[tuple[str, Any]] = []
    for view in required:
        record = _view_record(asset, view)
        raw = str(record.get("path") or "").strip()
        path = resolve_path(root, raw) if raw else None
        image = None
        if path and path.is_file():
            try:
                src = Image.open(path).convert("RGB")
                width = max(1, int(src.width * tile_h / max(1, src.height)))
                image = src.resize((width, tile_h))
            except (OSError, ValueError):
                image = None
        if image is None:
            image = Image.new("RGB", (int(tile_h * 0.7), tile_h), (48, 48, 48))
        thumbs.append((view, image))
    if not thumbs:
        return {"status": "skipped", "reason": "no_readable_views"}
    total_w = sum(image.width for _, image in thumbs) + pad * (len(thumbs) + 1)
    canvas = Image.new("RGB", (total_w, tile_h + label_h + pad * 2), (245, 245, 245))
    draw = ImageDraw.Draw(canvas)
    x = pad
    for view, image in thumbs:
        canvas.paste(image, (x, pad))
        draw.text((x + 2, pad + tile_h + 3), view, fill=(0, 0, 0))
        x += image.width + pad
    out = root / "生产数据" / "model_pack_montage" / f"{character_id}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "JPEG", quality=88)
    return {"status": "ok", "path": rel_to_root(root, out), "views": [view for view, _ in thumbs]}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="漫画角色 turnaround/model-pack 技术检查与人审签收")
    parser.add_argument("project_root")
    parser.add_argument("command", choices=("check", "signoff"))
    parser.add_argument(
        "--characters",
        default="",
        help="check 可逗号分隔 CHAR_/MON_；signoff 必须恰好一个 ID；默认全部纳管资产",
    )
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--reason", default="")
    parser.add_argument("--confirm-all", action="store_true", help="确认已并排检查全部人审项目")
    parser.add_argument("--write", action="store_true", help="check 时把 readiness/fingerprint 回写 registry")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.project_root).expanduser().resolve()
    registry_file = root / "出图" / "共享" / "identity_registry.json"
    registry, _migration = migrate_registry(json.loads(registry_file.read_text(encoding="utf-8")))
    assets = registry.get("assets") if isinstance(registry.get("assets"), Mapping) else {}
    selected = [item.strip() for item in args.characters.split(",") if item.strip()]
    if not selected:
        # 2026-07-17：monster 从 opt-in 改为按档位默认纳管（虎妖 P015 画成普通虎漏管）。
        # 2026-07-23 再修：当时只纳 core_full/recurring_standard，named_minimal/未标档
        # monster 仍被默认排除——与 character（任何档位都纳管）不对称，也违背 identity.py
        # 「未标档宁多不漏」的保守原则。聊斋第2话狐仆(named_minimal·8/16 格在场)因此零定妆
        # 审计。现 monster 与 character 同标准全档纳管；model_pack_required 仍可显式 false 豁免。
        def monster_managed(asset: Mapping) -> bool:
            flag = asset.get("model_pack_required")
            if flag is True or flag is False:
                return flag
            return True

        selected = sorted(
            aid for aid, asset in assets.items()
            if isinstance(asset, Mapping)
            and (
                str(asset.get("type")) == "character"
                or (str(asset.get("type")) == "monster" and monster_managed(asset))
            )
        )
    if args.command == "signoff":
        if len(selected) != 1:
            raise SystemExit("signoff requires exactly one --characters ID")
        confirmations = {key: bool(args.confirm_all) for key in REQUIRED_CONFIRMATIONS}
        create_signoff(root, registry, selected[0], args.reviewer, args.reason, confirmations)
    reports = [apply_character_readiness(root, registry, cid) for cid in selected]
    # Build the sign-off contact sheet for any character that still needs human
    # approval, so the reviewer has a single side-by-side view before signing.
    for report in reports:
        if report.get("readiness") in {"needs_approval", "needs_fix"}:
            montage = build_montage(root, registry, str(report.get("character_id") or ""))
            if montage.get("status") == "ok":
                report["montage"] = montage["path"]
    if args.write or args.command == "signoff":
        registry_file.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload = {
        "kind": "comic_model_pack_report",
        "version": VERSION,
        "created_at": now_iso(),
        "characters": reports,
        "summary": summarize_reports(reports),
    }
    if args.write or args.command == "signoff":
        out = root / "生产数据" / "comic_model_pack_report.json"
        payload = write_stable_report(out, payload)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"model-pack: ready={payload['summary']['ready']} needs_approval={payload['summary']['needs_approval']} "
            f"needs_fix={payload['summary']['needs_fix']}"
        )
        for report in reports:
            if report.get("montage"):
                print(f"  并排签收接触表 {report.get('character_id')}: {report['montage']}")
    return 0 if payload["summary"]["needs_fix"] == 0 and payload["summary"]["needs_approval"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
