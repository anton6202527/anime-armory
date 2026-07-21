#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同主体多视图合成参考图（composite reference sheet）。

后端一次请求的可执行附件上限（如 Dreamina image2image、Codex image_generation）
常低于一格声明的参考数。历史行为是按优先级静默省略，导致风格锚和部分角色
视图被挤出参考通道、只剩文字契约（实测表现为 style_anchor_drift 与跨话角色
漂移）。本模块把同一 ID 的多张视图拼成一张网格图，让 1 个物理附件槽携带
一个主体的全部视图，从源头释放槽位：

- 只合成同一 ID 的视图（不同主体绝不同图拼接，避免串脸串衣）。
- 拼板不加文字标注（烧字参考可能诱发成图带字）。
- 结果按内容寻址缓存到 `出图/共享/composites/`，可复现、可追溯：
  记录 layout 版本 + 每个部件的 id/path/sha256/role。
- Pillow 不可用时优雅降级：原样返回并给出披露性说明，不 fail 主流程。
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

LAYOUT_VERSION = 1
COMPOSITE_ROLE = "composite_views"
COMPOSITE_DIRNAME = "composites"
MAX_VIEWS_PER_SHEET = 4
CELL_MAX_EDGE = 1024
GUTTER = 24
BACKGROUND = (255, 255, 255)

# 视图价值排序：正/脸优先保真
ROLE_PRIORITY = {
    "memory_anchor": 0,
    "front": 1,
    "face": 2,
    "three_quarter": 3,
    "side": 4,
    "outfit": 5,
    "back": 6,
}


def _pil():
    try:
        from PIL import Image  # noqa: PLC0415

        return Image
    except Exception:
        return None


def composable_subject(record: dict[str, Any]) -> str:
    rid = str(record.get("id") or "")
    if rid.startswith(("CHAR_", "MON_")):
        return rid
    return ""


def _role_rank(record: dict[str, Any]) -> int:
    return ROLE_PRIORITY.get(str(record.get("role") or "").lower(), 9)


def _composite_key(parts: list[dict[str, Any]]) -> str:
    payload = f"layout_v{LAYOUT_VERSION}|" + "|".join(
        f"{part.get('id')}:{part.get('sha256')}:{part.get('role')}" for part in parts
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _grid_shape(count: int) -> tuple[int, int]:
    if count <= 1:
        return 1, 1
    if count == 2:
        return 2, 1
    return 2, 2


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _render_sheet(image_mod: Any, part_paths: list[Path], out_path: Path) -> None:
    images = []
    for path in part_paths:
        img = image_mod.open(path)
        img = img.convert("RGB")
        scale = CELL_MAX_EDGE / max(img.width, img.height)
        if scale < 1:
            img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
        images.append(img)
    cols, rows = _grid_shape(len(images))
    cell_w = max(img.width for img in images)
    cell_h = max(img.height for img in images)
    sheet = image_mod.new(
        "RGB",
        (cols * cell_w + (cols + 1) * GUTTER, rows * cell_h + (rows + 1) * GUTTER),
        BACKGROUND,
    )
    for index, img in enumerate(images):
        col, row = index % cols, index // cols
        x = GUTTER + col * (cell_w + GUTTER) + (cell_w - img.width) // 2
        y = GUTTER + row * (cell_h + GUTTER) + (cell_h - img.height) // 2
        sheet.paste(img, (x, y))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, format="PNG")


def compact_records_with_composites(
    root: Path,
    records: list[dict[str, Any]],
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """当声明参考数超过实机上限时，把同主体多视图折叠为单张拼板。

    返回 (处理后的 records, 披露信息)。records 顺序保持首次出现顺序；
    折叠不损失任何视图（≤4 视图全部进拼板，超出部分按角色优先级截断并披露）。
    """
    disclosure: dict[str, Any] = {
        "applied": False,
        "layout_version": LAYOUT_VERSION,
        "composites": [],
        "notes": [],
    }
    if limit <= 0 or len(records) <= limit:
        return records, disclosure
    image_mod = _pil()
    if image_mod is None:
        disclosure["notes"].append(
            "Pillow 不可用：无法折叠多视图为拼板，按历史省略路径执行（保真度损失已披露）。"
        )
        return records, disclosure

    grouped: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    passthrough: list[tuple[int, dict[str, Any]]] = []
    for index, record in enumerate(records):
        subject = composable_subject(record)
        if subject:
            if subject not in grouped:
                grouped[subject] = []
                order.append(subject)
            grouped[subject].append(record)
        else:
            passthrough.append((index, record))

    compacted: list[dict[str, Any]] = []
    for subject in order:
        views = grouped[subject]
        if len(views) <= 1:
            compacted.extend(views)
            continue
        ranked = sorted(views, key=_role_rank)
        kept = ranked[:MAX_VIEWS_PER_SHEET]
        truncated = ranked[MAX_VIEWS_PER_SHEET:]
        parts = [
            {
                "id": str(view.get("id") or ""),
                "path": str(view.get("path") or ""),
                "sha256": str(view.get("sha256") or ""),
                "role": str(view.get("role") or ""),
            }
            for view in kept
        ]
        key = _composite_key(parts)
        out_path = root / "出图" / "共享" / COMPOSITE_DIRNAME / f"{subject}__{key[:12]}.png"
        if not out_path.is_file():
            part_paths = []
            for view in kept:
                raw = view.get("abs_path") or view.get("path") or ""
                path = Path(str(raw))
                if not path.is_absolute():
                    path = root / path
                if not path.is_file():
                    disclosure["notes"].append(f"{subject} 视图缺文件 {raw}，跳过折叠该主体。")
                    part_paths = []
                    break
                part_paths.append(path)
            if not part_paths:
                compacted.extend(views)
                continue
            try:
                _render_sheet(image_mod, part_paths, out_path)
            except Exception as exc:  # 渲染失败按披露降级，不 fail 主流程
                disclosure["notes"].append(f"{subject} 拼板渲染失败（{exc}），按原视图执行。")
                compacted.extend(views)
                continue
        try:
            rel_path = str(out_path.resolve().relative_to(root.resolve()))
        except ValueError:
            rel_path = str(out_path)
        composite_record = {
            "id": subject,
            "path": rel_path,
            "abs_path": str(out_path),
            "sha256": _file_sha256(out_path),
            "role": COMPOSITE_ROLE,
            "required": any(bool(view.get("required")) for view in views),
            "composite": True,
            "layout_version": LAYOUT_VERSION,
            "parts": parts,
        }
        if truncated:
            composite_record["truncated_parts"] = [
                {
                    "id": str(view.get("id") or ""),
                    "path": str(view.get("path") or ""),
                    "role": str(view.get("role") or ""),
                    "reason": f"composite_sheet_max_{MAX_VIEWS_PER_SHEET}_views",
                }
                for view in truncated
            ]
        compacted.append(composite_record)
        disclosure["applied"] = True
        disclosure["composites"].append(
            {
                "id": subject,
                "path": rel_path,
                "sha256": composite_record["sha256"],
                "part_count": len(parts),
                "truncated_count": len(truncated),
            }
        )

    # 恢复整体顺序：主体按首次出现位置，直通记录按原索引
    if not disclosure["applied"]:
        return records, disclosure
    subject_first_index = {}
    for index, record in enumerate(records):
        subject = composable_subject(record)
        if subject and subject not in subject_first_index:
            subject_first_index[subject] = index
    merged: list[tuple[int, dict[str, Any]]] = list(passthrough)
    consumed_subjects: set[str] = set()
    for record in compacted:
        subject = composable_subject(record) or str(record.get("id") or "")
        if record.get("composite"):
            merged.append((subject_first_index.get(subject, 0), record))
            consumed_subjects.add(subject)
        elif subject not in consumed_subjects:
            original_index = next(
                (
                    index
                    for index, item in enumerate(records)
                    if item is record
                ),
                subject_first_index.get(subject, 0),
            )
            merged.append((original_index, record))
    merged.sort(key=lambda item: item[0])
    return [record for _index, record in merged], disclosure


def attachment_equivalent_count(records: list[dict[str, Any]]) -> int:
    """声明口径的等效附件数：拼板按其部件数计，普通记录计 1。"""
    total = 0
    for record in records:
        if record.get("composite") and isinstance(record.get("parts"), list):
            total += len(record["parts"])
        else:
            total += 1
    return total
