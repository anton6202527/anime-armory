#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a traditional manga name-board from panel_script.json."""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


COMIC_LIB = Path(__file__).resolve().parents[2] / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
from progress import update_stage as update_progress_stage
from editorial_authorization import (
    EditorialAuthorizationError,
    delegated_authorization_errors,
    delegated_review_authorization,
)


HEAVY_TOKENS = ("hook", "cliff", "reveal", "peak", "turn", "breakthrough", "冲击", "揭示", "钩子", "高潮", "动作")
COMPACT_TOKENS = ("reaction", "transition", "setup", "反应", "过渡", "铺垫")


class NameBoardError(ValueError):
    """Raised when deterministic editorial contracts cannot be satisfied."""


def sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def approval_subject(board: dict[str, Any]) -> dict[str, Any]:
    """Return the stable creative contract covered by an approval receipt.

    Workflow status, validation output, and the receipt itself are deliberately
    excluded so changing those bookkeeping fields does not invalidate the
    approved editorial content.
    """
    payload = copy.deepcopy(board)
    payload.pop("approval", None)
    payload.pop("validation", None)
    payload.pop("workflow_status", None)
    return payload


def approval_subject_sha256(board: dict[str, Any]) -> str:
    return sha256_json(approval_subject(board))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_setting(root: Path, key: str, default: str) -> str:
    path = root / "_设置.md"
    if not path.is_file():
        return default
    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*[:：]\s*(.+?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return default


# Only these settings change name-board geometry.  Binding the human approval to
# a hash of this subset (instead of the whole _设置.md) means editing a
# generation-only setting (生图模型/生图渠道/网点策略…) no longer stales an
# already-approved name board and forces a fresh submit-review/approve cycle.
GEOMETRY_SETTING_KEYS = ("漫画形态", "阅读方向", "页面尺寸", "原稿规格")


def settings_geometry_sha256(root: Path) -> str:
    values = {key: read_setting(root, key, "") for key in GEOMETRY_SETTING_KEYS}
    payload = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_width(value: str, default: int = 1440) -> int:
    match = re.match(r"\s*(\d+)\s*x", value)
    if match:
        return int(match.group(1))
    if value.upper() == "A4":
        return 1440
    if value.upper() == "B5":
        return 1280
    return default


def compact_text(value: Any, *, max_len: int = 90) -> str:
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value
    elif isinstance(value, list):
        text = "；".join(compact_text(item, max_len=max_len) for item in value)
    elif isinstance(value, dict):
        text = "；".join(f"{key}:{compact_text(item, max_len=max_len)}" for key, item in value.items())
    else:
        text = str(value)
    text = re.sub(r"\s+", " ", text).strip("； ")
    return text[: max_len - 1].rstrip() + "…" if len(text) > max_len else text


def explicit_weight(panel: dict[str, Any]) -> str:
    for key in ("layout_weight", "visual_weight", "importance"):
        raw = str(panel.get(key) or "").strip().lower()
        if raw in {"heavy", "large", "big", "重点", "大格", "强", "高", "3"}:
            return "heavy"
        if raw in {"compact", "small", "小格", "轻", "低", "1"}:
            return "compact"
        if raw in {"medium", "normal", "标准", "中", "2"}:
            return "medium"
    fn = str(panel.get("story_function") or "").lower()
    if any(token in fn for token in HEAVY_TOKENS):
        return "heavy"
    if any(token in fn for token in COMPACT_TOKENS):
        return "compact"
    if panel.get("sfx"):
        return "heavy"
    return "medium"


def text_load(panel: dict[str, Any]) -> int:
    load = 0
    if compact_text(panel.get("narration")) or compact_text(panel.get("narration_target")):
        load += 1
    for dialogue in panel.get("dialogue") or []:
        if isinstance(dialogue, dict) and compact_text(dialogue.get("text_target") or dialogue.get("text")):
            load += 1
    return load


def manuscript_boxes(width: int, comic_format: str, spec: str) -> dict[str, Any]:
    if "页漫" in comic_format or "B5" in spec or "A4" in spec:
        height = int(width * 1.42)
        bleed = max(24, width // 32)
        safe = max(72, width // 15)
        inner = max(104, width // 11)
    else:
        height = 1800
        bleed = 0
        safe = max(72, width // 20)
        inner = safe
    return {
        "spec": spec,
        "trim_box": {"x": 0, "y": 0, "w": width, "h": height},
        "safe_area": {"x": safe, "y": safe, "w": width - safe * 2, "h": height - safe * 2},
        "bleed": bleed,
        "inner_frame": {"x": inner, "y": inner, "w": width - inner * 2, "h": height - inner * 2},
    }


def panels_per_page(comic_format: str) -> int:
    if "四格" in comic_format:
        return 4
    if "页漫" in comic_format:
        return 5
    return 6


def page_groups(panels: list[dict[str, Any]], comic_format: str) -> list[list[dict[str, Any]]]:
    """Honor explicit page hints before falling back to equal-size chunks.

    A generic fixed `5 panels/page` split is only a rough default.  Adaptation
    scripts commonly make deliberate page-turn decisions; when page_hint is
    present, the name board must preserve that editorial intent.
    """
    explicit = [panel.get("page_hint") for panel in panels]
    has_hint = [bool(str(value or "").strip()) for value in explicit]
    if panels and any(has_hint) and not all(has_hint):
        raise NameBoardError("page_hint 只能全部提供或全部省略；部分 page_hint 会造成静默重排")
    if panels and all(has_hint):
        if not all(str(value or "").strip().isdigit() for value in explicit):
            raise NameBoardError("page_hint 必须是正整数")
        page_numbers = [int(str(value)) for value in explicit]
        if any(value <= 0 for value in page_numbers):
            raise NameBoardError("page_hint 必须从正整数页号开始")
        if page_numbers != sorted(page_numbers):
            raise NameBoardError("page_hint 必须按 panel 阅读顺序单调不减，禁止静默重排")
        groups: list[list[dict[str, Any]]] = []
        group_keys: list[int] = []
        for panel, page_number in zip(panels, page_numbers):
            if page_number not in group_keys:
                group_keys.append(page_number)
                groups.append([])
            groups[group_keys.index(page_number)].append(panel)
        return groups
    capacity = panels_per_page(comic_format)
    return [panels[start : start + capacity] for start in range(0, len(panels), capacity)]


def page_side(index: int, comic_format: str, reading_direction: str) -> str:
    if "条漫" in comic_format:
        return "scroll"
    if reading_direction == "从右到左":
        return "right" if index % 2 == 1 else "left"
    return "left" if index % 2 == 1 else "right"


def bubble_first(panel: dict[str, Any], reading_direction: str) -> str:
    if text_load(panel) == 0:
        return "none"
    if reading_direction == "从右到左":
        return "right_top"
    return "left_top" if reading_direction == "从左到右" else "top"


def panel_shape_for(weight: str, panel: dict[str, Any]) -> str:
    explicit = str(panel.get("panel_shape") or "").strip()
    if explicit:
        return explicit
    if weight == "heavy":
        return "wide"
    if weight == "compact":
        return "small"
    return "standard"


def effect_hint(panel: dict[str, Any], weight: str) -> str:
    explicit = compact_text(panel.get("effects_plan") or panel.get("effects_hint") or panel.get("sfx"))
    if explicit:
        return explicit
    fn = str(panel.get("story_function") or "").lower()
    if panel.get("sfx") or weight == "heavy" and any(token in fn for token in ("action", "peak", "动作")):
        return "speed/action lines around motion path; keep face and hands readable"
    if "reveal" in fn or "揭示" in fn:
        return "focus lines or black-field contrast toward reveal object"
    return "none"


def page_turn_hook(page_panels: list[dict[str, Any]]) -> str:
    if not page_panels:
        return ""
    # 翻页发生在最后一格之后；不能把页中间的重格误标为翻页钩子。
    chosen = page_panels[-1]
    return f"{chosen.get('panel_id', '')} {compact_text(chosen.get('story_function'), max_len=36)}".strip()


def _row_rects(
    rows: list[list[tuple[int, str]]],
    safe: dict[str, Any],
    reading_direction: str,
) -> dict[int, dict[str, int]]:
    """Lay out deterministic thumbnail rows while preserving reading order."""
    x = int(safe["x"])
    y = int(safe["y"])
    w = int(safe["w"])
    h = int(safe["h"])
    gap = max(18, w // 48)
    row_units = [max((3 if weight == "heavy" else 1 if weight == "compact" else 2) for _, weight in row) for row in rows]
    available_h = h - gap * max(0, len(rows) - 1)
    total_units = sum(row_units) or 1
    cursor_y = y
    out: dict[int, dict[str, int]] = {}
    for row_index, (row, units) in enumerate(zip(rows, row_units)):
        row_h = max(120, int(available_h * units / total_units))
        if row_index == len(rows) - 1:
            row_h = max(120, y + h - cursor_y)
        col_gap = gap if len(row) > 1 else 0
        cell_w = max(120, int((w - col_gap * max(0, len(row) - 1)) / len(row)))
        for visual_col, (panel_index, weight) in enumerate(row):
            col = len(row) - 1 - visual_col if reading_direction == "从右到左" else visual_col
            inset = max(0, cell_w // 24) if weight == "compact" else 0
            out[panel_index] = {
                "x": x + col * (cell_w + col_gap) + inset,
                "y": cursor_y,
                "w": cell_w - inset * 2,
                "h": row_h,
            }
        cursor_y += row_h + gap
    return out


def rough_rects(
    count: int,
    page: dict[str, Any],
    weights: list[str],
    comic_format: str,
    reading_direction: str,
) -> list[dict[str, int]]:
    safe = page["safe_area"]
    if count <= 0:
        return []
    if "四格" in comic_format:
        rows = [[(index, weights[index])] for index in range(count)]
        mapped = _row_rects(rows, safe, reading_direction)
        return [mapped[index] for index in range(count)]
    if "页漫" in comic_format:
        rows: list[list[tuple[int, str]]] = []
        pending: list[tuple[int, str]] = []
        for index, weight in enumerate(weights):
            if weight == "heavy":
                if pending:
                    rows.append(pending)
                    pending = []
                rows.append([(index, weight)])
            else:
                pending.append((index, weight))
                if len(pending) == 2:
                    rows.append(pending)
                    pending = []
        if pending:
            rows.append(pending)
        mapped = _row_rects(rows, safe, reading_direction)
        return [mapped[index] for index in range(count)]

    x = int(safe["x"])
    y = int(safe["y"])
    w = int(safe["w"])
    available_h = int(safe["h"])
    gap = max(18, w // 48)
    units = sum(3 if weight == "heavy" else 1 if weight == "compact" else 2 for weight in weights) or 1
    rects: list[dict[str, int]] = []
    cursor = y
    for idx, weight in enumerate(weights):
        unit = 3 if weight == "heavy" else 1 if weight == "compact" else 2
        remaining_gap = gap * max(0, count - 1)
        h = max(120, int((available_h - remaining_gap) * unit / units))
        if idx == count - 1:
            h = max(120, y + available_h - cursor)
        inset = 0 if weight == "heavy" else w // 12 if weight == "compact" else w // 24
        rects.append({"x": x + inset, "y": cursor, "w": w - inset * 2, "h": h})
        cursor += h + gap
    return rects


def _region(rect: dict[str, int], *, where: str) -> dict[str, int]:
    x, y, w, h = (int(rect[key]) for key in ("x", "y", "w", "h"))
    if where == "top_left":
        return {"x": x + w // 20, "y": y + h // 20, "w": max(1, w * 2 // 5), "h": max(1, h // 3)}
    if where == "top_right":
        return {"x": x + w * 11 // 20, "y": y + h // 20, "w": max(1, w * 2 // 5), "h": max(1, h // 3)}
    return {"x": x + w // 5, "y": y + h // 5, "w": max(1, w * 3 // 5), "h": max(1, h * 7 // 10)}


def balloon_contracts(panel: dict[str, Any], reading_direction: str) -> list[dict[str, Any]]:
    pid = str(panel.get("panel_id") or "")
    out: list[dict[str, Any]] = []
    order = 1
    if compact_text(panel.get("narration_target") or panel.get("narration")):
        out.append(
            {
                "balloon_id": f"{pid}_N1",
                "type": "narration",
                "content_ref": f"panel:{pid}.narration",
                "speaker": "",
                "order": order,
                "tail": {"mode": "none", "target": ""},
            }
        )
        order += 1
    for index, dialogue in enumerate(panel.get("dialogue") or [], 1):
        if not isinstance(dialogue, dict):
            continue
        text = compact_text(dialogue.get("text_target") or dialogue.get("text"))
        if not text:
            continue
        speaker = compact_text(dialogue.get("speaker"), max_len=64) or "unresolved_speaker"
        out.append(
            {
                "balloon_id": f"{pid}_D{index}",
                "type": "dialogue",
                "content_ref": f"panel:{pid}.dialogue:{index}",
                "speaker": speaker,
                "order": order,
                "tail": {"mode": "toward_speaker", "target": speaker or "unresolved_speaker"},
            }
        )
        order += 1
    raw_sfx = panel.get("sfx") or []
    if isinstance(raw_sfx, str):
        raw_sfx = [raw_sfx]
    for index, item in enumerate(raw_sfx, 1):
        if not compact_text(item):
            continue
        out.append(
            {
                "balloon_id": f"{pid}_S{index}",
                "type": "sfx",
                "content_ref": f"panel:{pid}.sfx:{index}",
                "speaker": "",
                "order": order,
                "tail": {"mode": "action_path", "target": "impact_or_motion_anchor"},
            }
        )
        order += 1
    return out


def panel_regions(rect: dict[str, int], balloons: list[dict[str, Any]], reading_direction: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    subject = [
        {
            "region_id": "SUBJECT_PRIMARY",
            "role": "acting_subject_and_key_action",
            "rect": _region(rect, where="center"),
            "source": "heuristic_thumbnail",
            "confidence": "heuristic",
        }
    ]
    avoid: list[dict[str, Any]] = []
    for index, balloon in enumerate(balloons):
        if reading_direction == "从右到左":
            where = "top_right" if index % 2 == 0 else "top_left"
        else:
            where = "top_left" if index % 2 == 0 else "top_right"
        avoid.append(
            {
                "region_id": f"TEXT_{index + 1:02d}",
                "role": "reserved_for_balloon_or_sfx",
                "content_ref": balloon["content_ref"],
                "rect": _region(rect, where=where),
                "source": "heuristic_thumbnail",
                "confidence": "heuristic",
            }
        )
    return subject, avoid


def finishing_preview(root: Path) -> dict[str, str]:
    style = read_setting(root, "基础视觉风格", "彩色国漫条漫")
    render_stage = read_setting(root, "出图稿层", "完成稿")
    tone_strategy = read_setting(root, "网点策略", "风格驱动")
    effects_strategy = read_setting(root, "效果线策略", "剧情驱动")
    if "黑白" in style or "网点" in style or "日漫" in style:
        tone_plan = f"{tone_strategy}: screentone hierarchy for skin, cloth, background depth, and mood blacks"
    else:
        tone_plan = f"{tone_strategy}: grayscale/value planning even when final art is color"
    return {
        "render_stage": render_stage,
        "ink_plan": "clear silhouettes, stable line weight, solid blacks assigned before tone/color",
        "tone_plan": tone_plan,
        "effects_plan": f"{effects_strategy}: action lines, focus lines, impact flashes, symbols, and omitted backgrounds only when they support reading",
    }


def build_name_board(root: Path, chapter: str) -> dict[str, Any]:
    panel_path = root / "脚本" / chapter / "panel_script.json"
    if not panel_path.is_file():
        raise NameBoardError(f"缺少输入：{panel_path}")
    panel_script = load_json(panel_path)
    comic_format = read_setting(root, "漫画形态", str(panel_script.get("format") or "条漫"))
    reading_direction = read_setting(root, "阅读方向", "从上到下")
    width = parse_width(read_setting(root, "页面尺寸", "1440xauto"))
    spec = read_setting(root, "原稿规格", "数字条漫")
    manuscript = manuscript_boxes(width, comic_format, spec)
    panels = [panel for panel in panel_script.get("panels") or [] if isinstance(panel, dict) and panel.get("panel_id")]
    if not panels:
        raise NameBoardError("panel_script.panels 为空，不能生成缩略分镜/name board")
    panel_ids = [str(panel.get("panel_id")) for panel in panels]
    if len(panel_ids) != len(set(panel_ids)):
        raise NameBoardError("panel_script.panel_id 必须唯一")
    pages: list[dict[str, Any]] = []
    for page_index, group in enumerate(page_groups(panels, comic_format), 1):
        page_id = f"SCROLL_{page_index:03d}" if "条漫" in comic_format else f"PAGE_{page_index:03d}"
        weights = [explicit_weight(panel) for panel in group]
        if "四格" in comic_format and len(group) != 4:
            raise NameBoardError("四格 adapter 要求每页恰好 4 格；请补齐 page_hint 或调整分格脚本")
        rects = rough_rects(len(group), manuscript, weights, comic_format, reading_direction)
        page_panels = []
        gutter_notes = []
        for panel, weight, rect in zip(group, weights, rects):
            pid = str(panel.get("panel_id"))
            shape = panel_shape_for(weight, panel)
            gutter = compact_text(panel.get("gutter_intent") or ("long pause" if weight == "heavy" else "quick cut" if weight == "compact" else "standard beat"), max_len=48)
            gutter_notes.append(f"{pid}:{gutter}")
            balloons = balloon_contracts(panel, reading_direction)
            subject_regions, avoid_regions = panel_regions(rect, balloons, reading_direction)
            page_panels.append(
                {
                    "panel_id": pid,
                    "thumbnail_rect": rect,
                    "layout_weight": weight,
                    "panel_shape": shape,
                    "border_style": str(panel.get("border_style") or "standard"),
                    "gutter_intent": gutter,
                    # 缩略分镜首先要回答“画面里发生什么”。art_notes 多为禁错/考据约束，
                    # 不能在缩略格里压过真实画面描述；没有 description 时才降级使用。
                    "camera_hint": compact_text(panel.get("camera_role") or panel.get("description") or panel.get("art_notes")),
                    "text_load": text_load(panel),
                    "bubble_first": bubble_first(panel, reading_direction),
                    "balloons": balloons,
                    "subject_regions": subject_regions,
                    "avoid_regions": avoid_regions,
                    "eye_flow_entry": "right_top" if reading_direction == "从右到左" else "left_top" if reading_direction == "从左到右" else "top",
                    "eye_flow_exit": "left_bottom" if reading_direction == "从右到左" else "right_bottom" if reading_direction == "从左到右" else "bottom",
                    "effects_hint": effect_hint(panel, weight),
                }
            )
        pages.append(
            {
                "page_id": page_id,
                "page_side": page_side(page_index, comic_format, reading_direction),
                "spread_id": f"SPREAD_{(page_index + 1) // 2:03d}",
                "page_turn_hook": page_turn_hook(group),
                "eye_flow_path": [str(panel.get("panel_id")) for panel in group],
                "eye_flow": {
                    "reading_direction": reading_direction,
                    "entry_panel_id": str(group[0].get("panel_id")) if group else "",
                    "exit_panel_id": str(group[-1].get("panel_id")) if group else "",
                    "path": [str(panel.get("panel_id")) for panel in group],
                },
                "gutter_intent": "；".join(gutter_notes),
                "panels": page_panels,
            }
        )
    for index, page in enumerate(pages):
        setup_panel = (page.get("panels") or [{}])[-1]
        next_panels = pages[index + 1].get("panels") or [] if index + 1 < len(pages) else []
        payoff_panel = next_panels[0] if next_panels else {}
        page["page_turn"] = {
            "setup": {
                "panel_id": str(setup_panel.get("panel_id") or ""),
                "story_function": compact_text(panels[panel_ids.index(str(setup_panel.get("panel_id")))].get("story_function"), max_len=64),
            },
            "payoff": {
                "panel_id": str(payoff_panel.get("panel_id") or ""),
                "mode": "next_page_open" if payoff_panel else "chapter_end",
            },
        }
    settings_path = root / "_设置.md"
    board = {
        "schema_version": 2,
        "kind": "comic_name_board",
        "workflow_status": "draft",
        "chapter": chapter,
        "format": comic_format,
        "reading_direction": reading_direction,
        "manuscript": manuscript,
        "pages": pages,
        "finishing_preview": finishing_preview(root),
        "upstream_receipt": {
            "panel_script": str(Path("脚本") / chapter / "panel_script.json"),
            "panel_script_sha256": sha256_file(panel_path),
            "settings": "_设置.md",
            "settings_sha256": sha256_file(settings_path),
            "settings_geometry_sha256": settings_geometry_sha256(root),
        },
        "approval": {},
    }
    errors = validate_name_board(board, panel_script)
    board["validation"] = {"status": "pass" if not errors else "fail", "errors": errors}
    if errors:
        raise NameBoardError("name_board 校验失败：" + "；".join(errors))
    return board


def validate_name_board(board: dict[str, Any], panel_script: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if board.get("schema_version") != 2 or board.get("kind") != "comic_name_board":
        errors.append("需要 comic_name_board schema v2")
    expected = [str(panel.get("panel_id")) for panel in panel_script.get("panels") or [] if isinstance(panel, dict) and panel.get("panel_id")]
    seen: list[str] = []
    safe = (board.get("manuscript") or {}).get("safe_area") or {}
    sx, sy, sw, sh = (int(safe.get(key) or 0) for key in ("x", "y", "w", "h"))
    for page in board.get("pages") or []:
        page_panels = [item for item in page.get("panels") or [] if isinstance(item, dict)]
        page_ids = [str(item.get("panel_id") or "") for item in page_panels]
        seen.extend(page_ids)
        if page.get("eye_flow_path") != page_ids or (page.get("eye_flow") or {}).get("path") != page_ids:
            errors.append(f"{page.get('page_id')}: eye_flow 未覆盖并按顺序列出所有 panel")
        for panel in page_panels:
            pid = str(panel.get("panel_id") or "")
            rect = panel.get("thumbnail_rect") or {}
            x, y, w, h = (int(rect.get(key) or 0) for key in ("x", "y", "w", "h"))
            if min(w, h) <= 0 or x < sx or y < sy or x + w > sx + sw or y + h > sy + sh:
                errors.append(f"{pid}: thumbnail_rect 越出 safe_area 或尺寸无效")
            orders = [item.get("order") for item in panel.get("balloons") or []]
            if orders != list(range(1, len(orders) + 1)):
                errors.append(f"{pid}: balloons.order 必须从 1 连续递增")
            for item in panel.get("balloons") or []:
                if not item.get("content_ref") or not isinstance(item.get("tail"), dict):
                    errors.append(f"{pid}: balloon 缺 content_ref/tail")
    if seen != expected:
        errors.append("pages/eye_flow 的 panel 顺序必须与 panel_script 完全一致")
    if len(seen) != len(set(seen)):
        errors.append("name_board 中 panel_id 重复")
    return errors


def verify_upstream(root: Path, chapter: str, board: dict[str, Any]) -> list[str]:
    receipt = board.get("upstream_receipt") if isinstance(board.get("upstream_receipt"), dict) else {}
    errors: list[str] = []
    panel_path = root / "脚本" / chapter / "panel_script.json"
    if receipt.get("panel_script_sha256") != sha256_file(panel_path):
        errors.append("panel_script 已变化，当前缩略分镜/name board 已 stale")
    # Prefer the geometry-subset hash; fall back to the whole-file hash only for
    # legacy receipts written before the subset existed (they re-approve once,
    # then get the narrower binding).
    if "settings_geometry_sha256" in receipt:
        if receipt.get("settings_geometry_sha256") != settings_geometry_sha256(root):
            errors.append("影响几何的设置（漫画形态/阅读方向/页面尺寸/原稿规格）已变化，当前缩略分镜/name board 已 stale")
    elif receipt.get("settings_sha256") != sha256_file(root / "_设置.md"):
        errors.append("_设置.md 已变化，当前缩略分镜/name board 已 stale")
    return errors


def transition_existing(
    root: Path,
    chapter: str,
    target: str,
    *,
    reviewed_by: str = "",
    note: str = "",
) -> dict[str, Any]:
    path = root / "排版" / chapter / "name_board.json"
    if not path.is_file():
        raise NameBoardError(f"缺少待签收缩略分镜/name board：{path}")
    board = load_json(path)
    panel_script = load_json(root / "脚本" / chapter / "panel_script.json")
    errors = verify_upstream(root, chapter, board) + validate_name_board(board, panel_script)
    if errors:
        raise NameBoardError("不能变更缩略分镜/name board 状态：" + "；".join(errors))
    current = str(board.get("workflow_status") or "")
    if target == "review":
        if current not in {"draft", "review"}:
            raise NameBoardError("只有 draft/review 缩略分镜可提交复核；重建后再签收")
        board["workflow_status"] = "review"
        board["approval"] = {}
    elif target == "approved":
        if current != "review":
            raise NameBoardError("缩略分镜/name board 必须先 --submit-review，再执行 --approve")
        if not reviewed_by.strip():
            raise NameBoardError("--approve 必须提供 --reviewed-by")
        try:
            authorization = delegated_review_authorization(root, reviewed_by, "name_board")
        except EditorialAuthorizationError as exc:
            raise NameBoardError(str(exc)) from exc
        board["workflow_status"] = "approved"
        board["approval"] = {
            "kind": "comic_name_board_approval",
            "status": "approved",
            "reviewed_by": reviewed_by.strip(),
            "review_kind": "delegated_policy_auto_review" if authorization is not None else "human_editorial_review",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "note": note.strip(),
            "subject_sha256": approval_subject_sha256(board),
            "panel_script_sha256": (board.get("upstream_receipt") or {}).get("panel_script_sha256", ""),
            "settings_sha256": (board.get("upstream_receipt") or {}).get("settings_sha256", ""),
            "settings_geometry_sha256": (board.get("upstream_receipt") or {}).get("settings_geometry_sha256", ""),
        }
        if authorization is not None:
            board["approval"]["authorization"] = authorization
    else:
        raise NameBoardError(f"未知状态：{target}")
    board["validation"] = {"status": "pass", "errors": []}
    path.write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return board


def verify_approval(root: Path, chapter: str, board: dict[str, Any]) -> list[str]:
    errors = verify_upstream(root, chapter, board)
    approval = board.get("approval") if isinstance(board.get("approval"), dict) else {}
    if board.get("workflow_status") != "approved" or approval.get("status") != "approved":
        errors.append("name_board 尚未 approved")
    else:
        if not str(approval.get("reviewed_by") or "").strip():
            errors.append("name_board 审批缺 reviewed_by")
        if not str(approval.get("reviewed_at") or "").strip():
            errors.append("name_board 审批缺 reviewed_at")
        if approval.get("subject_sha256") != approval_subject_sha256(board):
            errors.append("name_board 审批内容 SHA 不匹配")
        if str(approval.get("reviewed_by") or "").strip().startswith("delegate:") and approval.get("review_kind") != "delegated_policy_auto_review":
            errors.append("name_board delegate 审批 review_kind 必须为 delegated_policy_auto_review")
        errors += delegated_authorization_errors(
            root,
            str(approval.get("reviewed_by") or ""),
            "name_board",
            approval.get("authorization"),
        )
    return errors


def write_svg(root: Path, chapter: str, board: dict[str, Any]) -> Path:
    page_w = 300
    page_h = 430
    gap = 28
    cols = 3
    pages = board.get("pages") or []
    rows = max(1, (len(pages) + cols - 1) // cols)
    width = cols * page_w + (cols + 1) * gap
    height = rows * page_h + (rows + 1) * gap
    src = board.get("manuscript") if isinstance(board.get("manuscript"), dict) else {}
    safe = src.get("safe_area") if isinstance(src.get("safe_area"), dict) else {"x": 0, "y": 0, "w": 1, "h": 1}
    safe_w = max(1, int(safe.get("w") or 1))
    safe_h = max(1, int(safe.get("h") or 1))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f2efe7"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,Arial,sans-serif;font-size:11px;fill:#222}.pid{font-weight:700}.note{font-size:9px;fill:#555}</style>',
    ]
    for idx, page in enumerate(pages):
        row = idx // cols
        col = idx % cols
        ox = gap + col * (page_w + gap)
        oy = gap + row * (page_h + gap)
        parts.append(f'<rect x="{ox}" y="{oy}" width="{page_w}" height="{page_h}" fill="#fffdf7" stroke="#222" stroke-width="2"/>')
        parts.append(f'<text x="{ox + 10}" y="{oy + 18}">{html.escape(str(page.get("page_id") or ""))} {html.escape(str(page.get("page_side") or ""))}</text>')
        for panel in page.get("panels") or []:
            rect = panel.get("thumbnail_rect") if isinstance(panel.get("thumbnail_rect"), dict) else {}
            x = ox + 18 + int((int(rect.get("x") or 0) - int(safe.get("x") or 0)) / safe_w * (page_w - 36))
            y = oy + 34 + int((int(rect.get("y") or 0) - int(safe.get("y") or 0)) / safe_h * (page_h - 62))
            w = max(22, int(int(rect.get("w") or 1) / safe_w * (page_w - 36)))
            h = max(20, int(int(rect.get("h") or 1) / safe_h * (page_h - 62)))
            fill = "#f7f7f7" if panel.get("layout_weight") != "heavy" else "#ece8dc"
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="#333" stroke-width="1.5"/>')
            parts.append(f'<text class="pid" x="{x + 5}" y="{y + 15}">{html.escape(str(panel.get("panel_id") or ""))}</text>')
            hint = html.escape(compact_text(panel.get("camera_hint"), max_len=32))
            if hint:
                parts.append(f'<text class="note" x="{x + 5}" y="{min(y + h - 7, y + 30)}">{hint}</text>')
        hook = html.escape(compact_text(page.get("page_turn_hook"), max_len=46))
        parts.append(f'<text class="note" x="{ox + 10}" y="{oy + page_h - 10}">hook: {hook}</text>')
    parts.append("</svg>")
    out = root / "排版" / chapter / "name" / "name_board.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return out


def update_progress(root: Path, chapter: str, stage: str, value: str) -> None:
    update_progress_stage(root, chapter, stage, value, actor="comic-name")


def main() -> int:
    parser = argparse.ArgumentParser(description="生成漫画缩略分镜/name_board.json")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--no-progress", action="store_true")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--submit-review", action="store_true", help="把现有 draft 提交为 review，不重建")
    action.add_argument("--approve", action="store_true", help="签收现有 review，不重建")
    action.add_argument("--check", action="store_true", help="只读检查现有缩略分镜/name board 的 schema、上游 SHA 与审批")
    parser.add_argument("--reviewed-by", default="", help="--approve 的签收人；必须显式提供")
    parser.add_argument("--approval-note", default="")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    out_path = root / "排版" / args.chapter / "name_board.json"
    try:
        if args.check:
            board = load_json(out_path)
            panel_script = load_json(root / "脚本" / args.chapter / "panel_script.json")
            errors = validate_name_board(board, panel_script) + verify_approval(root, args.chapter, board)
            if errors:
                for error in errors:
                    print(f"[block] {error}")
                return 2
            print(f"[ok] approved/current {out_path}")
            return 0
        if args.submit_review:
            board = transition_existing(root, args.chapter, "review")
            if not args.no_progress:
                update_progress(root, args.chapter, "缩略分镜", "🟡待签收")
            print(f"[ok] review {out_path}")
            return 0
        if args.approve:
            board = transition_existing(
                root,
                args.chapter,
                "approved",
                reviewed_by=args.reviewed_by,
                note=args.approval_note,
            )
            if not args.no_progress:
                update_progress(root, args.chapter, "缩略分镜", "✅")
            print(f"[ok] approved {out_path}")
            return 0

        board = build_name_board(root, args.chapter)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        svg_path = write_svg(root, args.chapter, board)
        if not args.no_progress:
            update_progress(root, args.chapter, "缩略分镜", "🟡待签收")
        print(f"[ok] draft {out_path}")
        print(f"[ok] {svg_path}")
        print("[next] 审阅后先 --submit-review，再用 --approve --reviewed-by <签收人> 签收；可由用户授权制作代理执行，draft 不会写入 ✅")
        return 0
    except (ValueError, OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"[block] {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
