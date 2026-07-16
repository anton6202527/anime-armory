#!/usr/bin/env python3
"""Derive character makeup split refs from one approved source image.

This script deliberately does not call a generation backend. It only crops
approved front / turnaround images, writes the derived PNGs, and records
provenance in identity_registry.json.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


READY_STATUSES = {"ready", "registered"}
LEGACY_TURNAROUND_SPLITS = {
    "three_quarter": (1, "turnaround_split"),
    "side": (2, "turnaround_split"),
    "back": (3, "turnaround_split"),
}
STANDARD_TURNAROUND_SPLITS = {
    "three_quarter": (1, "turnaround_split"),
    "side": (2, "turnaround_split"),
    "rear_three_quarter": (3, "turnaround_split"),
    "back": (4, "turnaround_split"),
}
TURNAROUND_FRONT_METHOD = "turnaround_split_front"
FRONT_CROPS = {
    "half_body": "front_crop",
}
FACE_ANCHOR_METHOD = "front_crop"
FACE_ANCHOR_SUFFIX = "脸部特写"
FACE_ANCHOR_TARGET_SIZE = (1024, 1024)
HALF_BODY_CROP = (0.08, 0.02, 0.92, 0.68)
FACE_ANCHOR_CROP = (0.38, 0.11, 0.57, 0.31)
SUBJECT_MASK_DISTANCE = 70
EXPRESSION_CROP_METHOD = "expression_face_crop"
BASE_EXPRESSION_CROP_METHOD = "front_expression_crop"
EXPRESSION_TIGHT_SUFFIX = "脸锚裁切"
EXPRESSION_TIGHT_TARGET_SIZE = (1024, 1024)
BASE_EXPRESSION_TARGET_SIZE = (1024, 1024)
BASE_EXPRESSION_LABELS = {"基础", "克制", "平静", "冷静", "中性", "neutral", "resting"}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _item_path(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        return str(item.get("path") or "").strip()
    return ""


def _item_ready(item: Any) -> bool:
    rel = _item_path(item)
    if not rel:
        return False
    if isinstance(item, dict):
        return str(item.get("status") or "").strip() in READY_STATUSES
    return True


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve(root: Path, rel: str) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else root / p


def _crop_box(width: int, height: int, box: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    left = max(0, min(width - 1, round(width * box[0])))
    top = max(0, min(height - 1, round(height * box[1])))
    right = max(left + 1, min(width, round(width * box[2])))
    bottom = max(top + 1, min(height, round(height * box[3])))
    return left, top, right, bottom


def _luma(pixel: tuple[int, int, int]) -> float:
    r, g, b = pixel
    return 0.299 * r + 0.587 * g + 0.114 * b


def _median(values: list[int]) -> int:
    if not values:
        return 0
    values = sorted(values)
    return values[len(values) // 2]


def _content_column_bounds(img: Image.Image) -> tuple[int, int]:
    """Find the useful portrait column inside padded turnaround splits.

    If there is no clear padded/background column contrast, return the whole image.
    """
    width, height = img.size
    y_step = max(1, height // 240)
    column_luma: list[float] = []
    for x in range(width):
        samples = [_luma(img.getpixel((x, y))) for y in range(0, height, y_step)]
        column_luma.append(sum(samples) / max(1, len(samples)))

    lo = min(column_luma)
    hi = max(column_luma)
    if hi - lo < 30:
        return 0, width - 1

    threshold = lo + (hi - lo) * 0.35
    min_segment = max(12, width // 50)
    segments: list[tuple[int, int]] = []
    start: int | None = None
    for x, value in enumerate(column_luma):
        if value > threshold:
            if start is None:
                start = x
        elif start is not None:
            if x - start >= min_segment:
                segments.append((start, x - 1))
            start = None
    if start is not None and width - start >= min_segment:
        segments.append((start, width - 1))

    if not segments:
        return 0, width - 1
    center = width / 2
    best = max(segments, key=lambda item: (item[1] - item[0] + 1) - abs(((item[0] + item[1]) / 2) - center) * 0.25)

    # The column finder exists for turnaround splits that have dark padding and
    # a bright portrait column.  Plain studio front references have no padding:
    # the brightest long segment is often just the neutral gray background at an
    # image edge, which would push face crops completely off the subject.
    touches_edge = best[0] <= width * 0.04 or best[1] >= width - 1 - width * 0.04
    off_center = abs(((best[0] + best[1]) / 2) - center) > width * 0.18
    if touches_edge and off_center:
        return 0, width - 1
    return best


def _background_rgb(img: Image.Image, x_left: int, x_right: int) -> tuple[int, int, int]:
    width, height = img.size
    x_left = max(0, min(width - 1, x_left))
    x_right = max(x_left, min(width - 1, x_right))
    x_step = max(1, (x_right - x_left + 1) // 80)
    y_step = max(1, height // 100)
    edge = max(1, (x_right - x_left + 1) // 20)
    samples: list[tuple[int, int, int]] = []
    for x in range(x_left, x_right + 1, x_step):
        for y in (0, height // 30, height - 1, max(0, height - height // 30 - 1)):
            samples.append(img.getpixel((x, max(0, min(height - 1, y)))))
    for y in range(0, height, y_step):
        for x in (x_left, min(x_right, x_left + edge), x_right, max(x_left, x_right - edge)):
            samples.append(img.getpixel((x, y)))
    return (
        _median([p[0] for p in samples]),
        _median([p[1] for p in samples]),
        _median([p[2] for p in samples]),
    )


def _subject_bbox(img: Image.Image) -> tuple[int, int, int, int] | None:
    width, height = img.size
    x_left, x_right = _content_column_bounds(img)
    bg_r, bg_g, bg_b = _background_rgb(img, x_left, x_right)
    step = max(1, min(width, height) // 700)
    xs: list[int] = []
    ys: list[int] = []
    for y in range(0, height, step):
        for x in range(x_left, x_right + 1, step):
            r, g, b = img.getpixel((x, y))
            if abs(r - bg_r) + abs(g - bg_g) + abs(b - bg_b) > SUBJECT_MASK_DISTANCE:
                xs.append(x)
                ys.append(y)

    min_count = max(64, ((x_right - x_left + 1) * height) // max(1, step * step * 4000))
    if len(xs) < min_count:
        return None
    left, top, right, bottom = min(xs), min(ys), max(xs), max(ys)
    if right - left < max(8, width * 0.03) or bottom - top < max(16, height * 0.08):
        return None
    return left, top, right, bottom


def _clamp_box(width: int, height: int, box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    left = max(0, min(width - 1, left))
    top = max(0, min(height - 1, top))
    right = max(left + 1, min(width, right))
    bottom = max(top + 1, min(height, bottom))
    return left, top, right, bottom


def _front_crop_box(img: Image.Image, kind: str) -> tuple[int, int, int, int]:
    width, height = img.size
    bbox = _subject_bbox(img)
    if not bbox:
        return _crop_box(width, height, FACE_ANCHOR_CROP if kind == "face_anchor_refs" else HALF_BODY_CROP)

    left, top, right, bottom = bbox
    subject_width = max(1, right - left)
    subject_height = max(1, bottom - top)
    if kind == "face_anchor_refs":
        content_left, content_right = _content_column_bounds(img)
        content_width = max(1, content_right - content_left + 1)
        # Front masters are centered production plates.  Build a square around
        # the head rather than widening from the whole-body bbox: a held sword
        # or trailing garment can otherwise make the face only ~10% of frame.
        side = max(96, round(min(content_width * 0.55, subject_height * 0.14)))
        center_x = (content_left + content_right) / 2
        crop_top = top + round(subject_height * 0.045)
        return _clamp_box(
            width,
            height,
            (
                round(center_x - side / 2),
                crop_top,
                round(center_x + side / 2),
                crop_top + side,
            ),
        )
    return _clamp_box(
        width,
        height,
        (
            left - round(subject_width * 0.22),
            top - round(subject_height * 0.04),
            right + round(subject_width * 0.22),
            top + round(subject_height * 0.56),
        ),
    )


def _base_expression_crop_box(img: Image.Image) -> tuple[int, int, int, int]:
    """Build an independent head-and-shoulders crop for neutral expressions.

    A neutral/controlled expression is already present in an accepted front
    plate. Re-generating it needlessly risks identity, stripe, accessory, or
    costume drift. This crop deliberately has a wider field of view than the
    canonical tight face anchor, so the two deliverables are independent pixel
    assets while retaining exact same-source identity.
    """
    width, height = img.size
    left, top, right, bottom = _front_crop_box(img, "face_anchor_refs")
    side = min(width, height, max(128, round(max(right - left, bottom - top) * 2.0)))
    center_x = (left + right) / 2
    center_y = (top + bottom) / 2 + side * 0.08
    crop_left = round(center_x - side / 2)
    crop_top = round(center_y - side / 2)
    crop_left = max(0, min(width - side, crop_left))
    crop_top = max(0, min(height - side, crop_top))
    return crop_left, crop_top, crop_left + side, crop_top + side


def _save_base_expression_crop(src: Path, dst: Path) -> list[int]:
    img = Image.open(src).convert("RGB")
    box = _base_expression_crop_box(img)
    out = ImageOps.fit(
        img.crop(box), BASE_EXPRESSION_TARGET_SIZE,
        method=Image.Resampling.LANCZOS, centering=(0.5, 0.5),
    )
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst)
    return list(box)


def _is_base_expression(emotion: str) -> bool:
    value = str(emotion or "").strip().lower()
    return value in BASE_EXPRESSION_LABELS


def _save_turnaround_split(
    src: Path,
    dst: Path,
    column_index: int,
    target_size: tuple[int, int],
    *,
    column_count: int = 4,
) -> list[int]:
    img = Image.open(src).convert("RGB")
    width, height = img.size
    column_width = width / float(column_count)
    # Do not inset equal-width board columns. Generated limbs and boots often
    # extend to the nominal split boundary; trimming 6% from both sides cut off
    # hands/feet on otherwise valid five-angle sheets. Neighbouring columns are
    # already separated by the neutral studio gap, so the exact boundary is the
    # safest deterministic crop before aspect-ratio padding.
    left = round(column_width * column_index)
    right = round(column_width * (column_index + 1))
    box = (left, 0, right, height)
    crop = img.crop(box)
    out = ImageOps.pad(crop, target_size, method=Image.Resampling.LANCZOS, color=(18, 22, 26))
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst)
    return list(box)


def _turnaround_split_plan(form: dict[str, Any]) -> tuple[dict[str, tuple[int, str]], int]:
    """Choose the board layout without corrupting legacy four-column sheets.

    A rear-three-quarter *slot* is not proof that the landed board has five
    columns: prompt-pack migration adds that slot to legacy registries too.
    Five-column splitting therefore requires explicit board metadata.  Missing
    or deliberately unknown metadata stays on the historical four-column map,
    preventing an old back view from being silently relabelled as rear 3/4.
    """
    rg = form.get("reference_group") if isinstance(form.get("reference_group"), dict) else {}
    turnaround = rg.get("turnaround") if isinstance(rg.get("turnaround"), dict) else {}
    layout = str(turnaround.get("layout") or "").strip().lower()
    if layout == "five_angle_v1":
        return STANDARD_TURNAROUND_SPLITS, 5
    if layout in {"legacy_four_angle_v1", "four_angle_v1", "unknown_existing"}:
        return LEGACY_TURNAROUND_SPLITS, 4

    try:
        column_count = int(turnaround.get("column_count") or 0)
    except (TypeError, ValueError):
        column_count = 0
    view_order = turnaround.get("view_order")
    if column_count == 5 or view_order == [
        "front", "three_quarter", "side", "rear_three_quarter", "back",
    ]:
        return STANDARD_TURNAROUND_SPLITS, 5
    return LEGACY_TURNAROUND_SPLITS, 4


def _save_front_crop(src: Path, dst: Path, kind: str, target_size: tuple[int, int]) -> list[int]:
    img = Image.open(src).convert("RGB")
    box = _front_crop_box(img, kind)
    crop = img.crop(box)
    out = ImageOps.fit(crop, target_size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.12))
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst)
    return list(box)


def _derivation(method: str, source_rel: str, source_sha: str, crop_box: list[int]) -> dict[str, Any]:
    return {
        "method": method,
        "source_path": source_rel,
        "source_sha256": source_sha,
        "crop_box": crop_box,
        "generated_by": "skills/n2d-image/scripts/derive_makeup_pack.py",
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    }


def _image_metadata(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    with Image.open(path) as im:
        width, height = im.size
    return {"sha256": _sha256(path), "dimensions": {"width": width, "height": height}}


def _ready_item(existing: Any, rel: str, derivation: dict[str, Any], dst: Path | None = None) -> dict[str, Any]:
    out = dict(existing) if isinstance(existing, dict) else {}
    out["path"] = rel
    out["status"] = "ready"
    out["derivation"] = derivation
    out.update(_image_metadata(dst))
    return out


def _update_face_anchor_list(
    items: Any,
    rel: str,
    derivation: dict[str, Any],
    label: str,
    dst: Path | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    found = False
    metadata = _image_metadata(dst)
    if isinstance(items, list):
        for item in items:
            if _item_path(item) == rel:
                base = dict(item) if isinstance(item, dict) else {}
                base.setdefault("label", label)
                base["path"] = rel
                base["status"] = "ready"
                base["derivation"] = derivation
                base.update(metadata)
                out.append(base)
                found = True
            elif isinstance(item, dict):
                out.append(dict(item))
            elif isinstance(item, str) and item.strip():
                out.append({"path": item.strip(), "status": "ready"})
    if not found:
        out.append({"label": label, "path": rel, "status": "ready", "derivation": derivation, **metadata})
    return out


def _update_expression_list(
    items: Any,
    old_rel: str,
    new_rel: str,
    derivation: dict[str, Any],
    emotion: str,
    dst: Path | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    found = False
    metadata = _image_metadata(dst)
    if isinstance(items, list):
        for item in items:
            rel = _item_path(item)
            if rel == old_rel:
                base = dict(item) if isinstance(item, dict) else {}
                if emotion:
                    base.setdefault("emotion", emotion)
                base["path"] = new_rel
                base["status"] = "ready"
                base["derivation"] = derivation
                base.update(metadata)
                out.append(base)
                found = True
            elif isinstance(item, dict):
                out.append(dict(item))
            elif isinstance(item, str) and item.strip():
                out.append({"path": item.strip(), "status": "ready"})
    elif items:
        rel = _item_path(items)
        if rel == old_rel:
            out.append({"emotion": emotion, "path": new_rel, "status": "ready", "derivation": derivation, **metadata})
            found = True
    if not found:
        out.append({"emotion": emotion, "path": new_rel, "status": "ready", "derivation": derivation, **metadata})
    return out


def _reference_group_path(form: dict[str, Any], key: str, fallback_suffix: str) -> str:
    rg = form.setdefault("reference_group", {})
    rel = _item_path(rg.get(key))
    if rel:
        return rel
    front_rel = _item_path(rg.get("front"))
    if not front_rel:
        asset_key = str(form.get("asset_key") or "CHAR_UNKNOWN").strip()
        return f"出图/共享/图片/{asset_key}_{fallback_suffix}.png"
    p = Path(front_rel)
    return str(p.with_name(f"{p.stem}_{fallback_suffix}{p.suffix or '.png'}"))


def _face_anchor_path(form: dict[str, Any]) -> str:
    rg = form.setdefault("reference_group", {})
    refs = rg.get("face_anchor_refs")
    if isinstance(refs, list):
        for item in refs:
            rel = _item_path(item)
            if rel:
                return rel
    return _reference_group_path(form, "face_anchor_refs", FACE_ANCHOR_SUFFIX)


def _update_reference_slots_for_path(form: dict[str, Any], rel: str, dst: Path | None) -> None:
    metadata = _image_metadata(dst)
    if not metadata:
        return
    slots = form.get("reference_slots")
    if not isinstance(slots, list):
        return
    for slot in slots:
        if isinstance(slot, dict) and _item_path(slot) == rel:
            slot["status"] = "ready"
            slot.update(metadata)


def _tight_expression_rel(rel: str) -> str:
    p = Path(rel)
    if p.stem.endswith(f"_{EXPRESSION_TIGHT_SUFFIX}"):
        return rel
    return str(p.with_name(f"{p.stem}_{EXPRESSION_TIGHT_SUFFIX}{p.suffix or '.png'}"))


def _expression_items(form: dict[str, Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for parent_key, child_key in (("reference_group", "expressions"), ("reference_atlas", "expression_refs")):
        parent = form.get(parent_key)
        if not isinstance(parent, dict):
            continue
        coll = parent.get(child_key)
        if isinstance(coll, dict):
            iterable = coll.values()
        elif isinstance(coll, list):
            iterable = coll
        elif coll:
            iterable = [coll]
        else:
            iterable = []
        for item in iterable:
            rel = _item_path(item)
            if not rel:
                continue
            emotion = ""
            if isinstance(item, dict):
                emotion = str(item.get("emotion") or item.get("label") or "").strip()
            out.append((rel, emotion))
    return out


def derive_project(
    root: Path,
    *,
    write: bool = False,
    force: bool = False,
    asset_keys: set[str] | None = None,
    front_from_turnaround: bool = False,
    tighten_expressions: bool = False,
    face_anchor_only: bool = False,
    views: set[str] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    data = _load_json(registry_path)
    summary: dict[str, Any] = {"derived": [], "skipped": []}
    requested_views = set(views or set())
    if face_anchor_only:
        requested_views = {"face_anchor_refs"}

    for char in data.get("characters", []):
        if not isinstance(char, dict):
            continue
        char_id = str(char.get("id") or "").strip()
        for form in char.get("forms", []):
            if not isinstance(form, dict):
                continue
            asset_key = str(form.get("asset_key") or "").strip()
            if asset_keys and asset_key not in asset_keys:
                continue
            form_name = str(form.get("form") or "").strip()
            form_label = f"{char_id}/{form_name}".strip("/")
            rg = form.setdefault("reference_group", {})
            if not isinstance(rg, dict):
                summary["skipped"].append({"form": form_label, "reason": "reference_group_not_object"})
                continue
            atlas = form.setdefault("reference_atlas", {})
            if not isinstance(atlas, dict):
                atlas = {}
                form["reference_atlas"] = atlas
            base_views = atlas.setdefault("base_views", {})
            if not isinstance(base_views, dict):
                base_views = {}
                atlas["base_views"] = base_views

            front_rel = _item_path(rg.get("front"))
            turn_rel = _item_path(rg.get("turnaround"))
            front_ready = _item_ready(rg.get("front"))
            turn_ready = _item_ready(rg.get("turnaround"))
            front_path = _resolve(root, front_rel) if front_rel else Path()
            turn_path = _resolve(root, turn_rel) if turn_rel else Path()

            turnaround_requested = not requested_views or bool(
                requested_views.intersection({
                    "front", "three_quarter", "side", "rear_three_quarter", "back"
                })
            )
            if turnaround_requested and turn_ready and turn_rel and turn_path.exists():
                with Image.open(turn_path) as opened:
                    turn_width, turn_height = opened.size
                if front_rel and front_path.exists():
                    with Image.open(front_path) as opened:
                        target_size = opened.size
                else:
                    # A wide turnaround board must split into portrait assets,
                    # not wide canvases with a tiny figure and huge side bars.
                    target_size = (max(1, round(turn_height * 9 / 16)), turn_height)
                source_sha = _sha256(turn_path)
                split_plan, column_count = _turnaround_split_plan(form)
                if front_from_turnaround and front_rel and (not requested_views or "front" in requested_views):
                    dst = _resolve(root, front_rel)
                    if dst.exists() and not force:
                        summary["skipped"].append({"form": form_label, "field": "front", "reason": "exists"})
                    else:
                        if write:
                            crop_box = _save_turnaround_split(
                                turn_path, dst, 0, target_size, column_count=column_count
                            )
                        else:
                            column_width = turn_width / column_count
                            crop_box = [
                                0,
                                0,
                                round(column_width),
                                turn_height,
                            ]
                        deriv = _derivation(TURNAROUND_FRONT_METHOD, turn_rel, source_sha, crop_box)
                        rg["front"] = _ready_item(rg.get("front"), front_rel, deriv, dst if write else None)
                        base_views["front"] = _ready_item(base_views.get("front"), front_rel, deriv, dst if write else None)
                        _update_reference_slots_for_path(form, front_rel, dst if write else None)
                        front_ready = True
                        front_path = _resolve(root, front_rel)
                        summary["derived"].append({
                            "form": form_label,
                            "field": "front",
                            "path": front_rel,
                            "method": TURNAROUND_FRONT_METHOD,
                        })
                suffixes = {
                    "three_quarter": "45度",
                    "side": "侧",
                    "rear_three_quarter": "后45度",
                    "back": "背",
                }
                for key, (column_index, method) in split_plan.items():
                    if requested_views and key not in requested_views:
                        continue
                    rel = _reference_group_path(form, key, suffixes[key])
                    dst = _resolve(root, rel)
                    if dst.exists() and not force:
                        summary["skipped"].append({"form": form_label, "field": key, "reason": "exists"})
                        continue
                    if write:
                        crop_box = _save_turnaround_split(
                            turn_path, dst, column_index, target_size, column_count=column_count
                        )
                    else:
                        column_width = turn_width / column_count
                        crop_box = [
                            round(column_width * column_index),
                            0,
                            round(column_width * (column_index + 1)),
                            turn_height,
                            ]
                    deriv = _derivation(method, turn_rel, source_sha, crop_box)
                    rg[key] = _ready_item(rg.get(key), rel, deriv, dst if write else None)
                    base_views[key] = _ready_item(base_views.get(key), rel, deriv, dst if write else None)
                    _update_reference_slots_for_path(form, rel, dst if write else None)
                    summary["derived"].append({"form": form_label, "field": key, "path": rel, "method": method})
            elif turnaround_requested:
                summary["skipped"].append({"form": form_label, "reason": "turnaround_not_ready_or_missing"})

            if front_ready and front_rel and front_path.exists():
                target_size = Image.open(front_path).size
                source_sha = _sha256(front_path)
                if not face_anchor_only:
                    for key, method in FRONT_CROPS.items():
                        if requested_views and key not in requested_views:
                            continue
                        rel = _reference_group_path(form, key, "半身")
                        dst = _resolve(root, rel)
                        if dst.exists() and not force:
                            summary["skipped"].append({"form": form_label, "field": key, "reason": "exists"})
                            continue
                        if write:
                            crop_box = _save_front_crop(front_path, dst, key, target_size)
                        else:
                            with Image.open(front_path) as opened:
                                im = opened.convert("RGB")
                                crop_box = list(_front_crop_box(im, key))
                        deriv = _derivation(method, front_rel, source_sha, crop_box)
                        rg[key] = _ready_item(rg.get(key), rel, deriv, dst if write else None)
                        base_views[key] = _ready_item(base_views.get(key), rel, deriv, dst if write else None)
                        _update_reference_slots_for_path(form, rel, dst if write else None)
                        summary["derived"].append({"form": form_label, "field": key, "path": rel, "method": method})

                if not requested_views or "face_anchor_refs" in requested_views:
                    rel = _face_anchor_path(form)
                    dst = _resolve(root, rel)
                    if dst.exists() and not force:
                        summary["skipped"].append({"form": form_label, "field": "face_anchor_refs", "reason": "exists"})
                    else:
                        if write:
                            crop_box = _save_front_crop(
                                front_path, dst, "face_anchor_refs", FACE_ANCHOR_TARGET_SIZE
                            )
                        else:
                            with Image.open(front_path) as opened:
                                im = opened.convert("RGB")
                                crop_box = list(_front_crop_box(im, "face_anchor_refs"))
                        deriv = _derivation(FACE_ANCHOR_METHOD, front_rel, source_sha, crop_box)
                        label = f"{form_label} 同源脸锚"
                        rg["face_anchor_refs"] = _update_face_anchor_list(
                            rg.get("face_anchor_refs"), rel, deriv, label, dst if write else None
                        )
                        atlas["face_anchor_refs"] = _update_face_anchor_list(
                            atlas.get("face_anchor_refs"), rel, deriv, label, dst if write else None
                        )
                        _update_reference_slots_for_path(form, rel, dst if write else None)
                        summary["derived"].append({
                            "form": form_label,
                            "field": "face_anchor_refs",
                            "path": rel,
                            "method": FACE_ANCHOR_METHOD,
                        })

                if "expression" in requested_views:
                    seen_base_expressions: set[str] = set()
                    for expr_rel, emotion in _expression_items(form):
                        if expr_rel in seen_base_expressions:
                            continue
                        seen_base_expressions.add(expr_rel)
                        if not _is_base_expression(emotion):
                            summary["skipped"].append({
                                "form": form_label,
                                "field": "expressions",
                                "path": expr_rel,
                                "reason": "non_base_expression_requires_generation",
                            })
                            continue
                        dst = _resolve(root, expr_rel)
                        if dst.exists() and not force:
                            summary["skipped"].append({
                                "form": form_label,
                                "field": "expressions",
                                "path": expr_rel,
                                "reason": "exists",
                            })
                            continue
                        if write:
                            crop_box = _save_base_expression_crop(front_path, dst)
                        else:
                            with Image.open(front_path) as opened:
                                crop_box = list(_base_expression_crop_box(opened.convert("RGB")))
                        deriv = _derivation(BASE_EXPRESSION_CROP_METHOD, front_rel, source_sha, crop_box)
                        rg["expressions"] = _update_expression_list(
                            rg.get("expressions"), expr_rel, expr_rel, deriv, emotion, dst if write else None
                        )
                        atlas["expression_refs"] = _update_expression_list(
                            atlas.get("expression_refs"), expr_rel, expr_rel, deriv, emotion, dst if write else None
                        )
                        _update_reference_slots_for_path(form, expr_rel, dst if write else None)
                        summary["derived"].append({
                            "form": form_label,
                            "field": "expressions",
                            "path": expr_rel,
                            "method": BASE_EXPRESSION_CROP_METHOD,
                        })
            else:
                summary["skipped"].append({"form": form_label, "reason": "front_not_ready_or_missing"})

            if tighten_expressions:
                seen_expr: set[str] = set()
                for expr_rel, emotion in _expression_items(form):
                    if expr_rel in seen_expr:
                        continue
                    seen_expr.add(expr_rel)
                    if Path(expr_rel).stem.endswith(f"_{EXPRESSION_TIGHT_SUFFIX}"):
                        summary["skipped"].append({"form": form_label, "field": "expressions", "path": expr_rel, "reason": "already_tight"})
                        continue
                    src = _resolve(root, expr_rel)
                    if not src.exists():
                        summary["skipped"].append({"form": form_label, "field": "expressions", "path": expr_rel, "reason": "missing"})
                        continue
                    tight_rel = _tight_expression_rel(expr_rel)
                    dst = _resolve(root, tight_rel)
                    if dst.exists() and not force:
                        crop_box: list[int]
                        with Image.open(src) as opened:
                            im = opened.convert("RGB")
                            crop_box = list(_front_crop_box(im, "face_anchor_refs"))
                        summary["skipped"].append({"form": form_label, "field": "expressions", "path": tight_rel, "reason": "exists"})
                    else:
                        if write:
                            crop_box = _save_front_crop(src, dst, "face_anchor_refs", EXPRESSION_TIGHT_TARGET_SIZE)
                        else:
                            with Image.open(src) as opened:
                                im = opened.convert("RGB")
                                crop_box = list(_front_crop_box(im, "face_anchor_refs"))
                    deriv = _derivation(EXPRESSION_CROP_METHOD, expr_rel, _sha256(src), crop_box)
                    rg["expressions"] = _update_expression_list(
                        rg.get("expressions"), expr_rel, tight_rel, deriv, emotion, dst if write else None
                    )
                    atlas["expression_refs"] = _update_expression_list(
                        atlas.get("expression_refs"), expr_rel, tight_rel, deriv, emotion, dst if write else None
                    )
                    _update_reference_slots_for_path(form, tight_rel, dst if write else None)
                    summary["derived"].append({
                        "form": form_label,
                        "field": "expressions",
                        "path": tight_rel,
                        "method": EXPRESSION_CROP_METHOD,
                    })

    if write:
        _write_json(registry_path, data)
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Derive n2d character makeup split refs from approved source images.")
    ap.add_argument("project_root", help="作品根目录")
    ap.add_argument("--write", action="store_true", help="写出 PNG 并回写 identity_registry.json")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的派生 PNG")
    ap.add_argument("--front-from-turnaround", action="store_true",
                    help="从三视图第 1 列生成/覆盖 front，确保 front 与 45/侧/背同源")
    ap.add_argument("--tighten-expressions", action="store_true",
                    help="从已存在表情 PNG 本地裁切紧脸锚，写为 *_脸锚裁切.png 并回写 expression_refs")
    ap.add_argument("--face-anchor-only", action="store_true",
                    help="只从 front 刷新 face_anchor_refs，不派生/覆盖 45度、侧、背、半身视图")
    ap.add_argument("--asset-key", action="append", default=[],
                    help="只派生指定 form.asset_key；可重复传入，避免误处理不兼容三视图布局")
    ap.add_argument(
        "--view",
        action="append",
        choices=("front", "three_quarter", "side", "rear_three_quarter", "back", "half_body", "face_anchor_refs", "expression"),
        default=[],
        help="只派生指定视图；可重复传入。用于逐张生成→QC→目视→下一张",
    )
    args = ap.parse_args()

    asset_keys = {str(v).strip() for v in args.asset_key if str(v).strip()} or None
    summary = derive_project(
        Path(args.project_root),
        write=args.write,
        force=args.force,
        asset_keys=asset_keys,
        front_from_turnaround=args.front_from_turnaround,
        tighten_expressions=args.tighten_expressions,
        face_anchor_only=args.face_anchor_only,
        views={str(v).strip() for v in args.view if str(v).strip()} or None,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
