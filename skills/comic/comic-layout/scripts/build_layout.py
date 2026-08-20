#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 panel_script.json 生成条漫/页漫 MVP layout.json。"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


COMIC_LIB = Path(__file__).resolve().parents[2] / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
from text_metadata import estimated_line_count
from progress import update_stage as update_progress_stage


HEAVY_FUNCTIONS = {
    "opening_hook",
    "opening_pressure",
    "action_peak",
    "turning_point",
    "cliffhanger",
    "chapter_hook",
    "reveal",
    "major_reveal",
    "public_humiliation",
    "physical_burden",
    "resource_reveal",
    "resource_transform",
    "power_surge",
    "breakthrough",
    "speed_montage",
}
# 只收录跨作品通用的叙事功能名；作品专属 story_function 请用逐格
# layout_weight/visual_weight 显式标注，不要往这里加词。
MEDIUM_FUNCTIONS = {
    "compressed_backstory",
    "labor_montage",
    "task_assignment",
    "rules_and_threat",
    "secret_hide",
    "concealment_strategy",
    "task_speedup",
    "self_restraint",
    "warning",
    "resource_allocation",
    "strategy_choice",
}
COMPACT_FUNCTIONS = {
    "reaction",
    "transition",
    "setup",
    "identity_question",
    "mockery_setup",
    "proactive_choice",
    "sleep_transition",
}

HEAVY_TOKENS = (
    "opening",
    "hook",
    "cliffhanger",
    "reveal",
    "peak",
    "turning",
    "humiliation",
    "burden",
    "glint",
    "source",
    "energy",
    "power",
    "surge",
    "breakthrough",
    "resource",
    "transform",
    "upgrade",
    "speed",
    "shortfall",
)
MEDIUM_TOKENS = (
    "montage",
    "assignment",
    "threat",
    "scale",
    "backstory",
    "canteen",
    "allocation",
    "visit",
    "hide",
    "conceal",
    "restraint",
    "strategy",
    "warning",
    "choice",
    "raw",
    "task",
)
COMPACT_TOKENS = ("reaction", "transition", "setup", "question", "leave", "empty", "approach", "worry", "knock", "smell", "lock")


class LayoutError(ValueError):
    """Raised when an approved editorial input cannot produce valid geometry."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def approval_subject(value: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(value)
    payload.pop("approval", None)
    payload.pop("validation", None)
    payload.pop("workflow_status", None)
    return payload


def approval_subject_sha256(value: dict[str, Any]) -> str:
    return sha256_json(approval_subject(value))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = load_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


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


# Only these settings change layout geometry (geometry_profile / canvas / segment
# height).  Binding the human approval to a hash of this subset instead of the
# whole _设置.md means a generation-only setting edit no longer stales an
# already-approved layout and forces a fresh submit-review/approve cycle.
GEOMETRY_SETTING_KEYS = ("漫画形态", "阅读方向", "页面尺寸", "原稿规格", "单话分段高度")
# Must mirror comic-name's GEOMETRY_SETTING_KEYS exactly (layout re-implements
# name-board verification for cross-line independence, so it recomputes the name
# board's own geometry hash — a different key set would never match).
NAME_GEOMETRY_SETTING_KEYS = ("漫画形态", "阅读方向", "页面尺寸", "原稿规格")


def _settings_subset_sha256(root: Path, keys: tuple[str, ...]) -> str:
    values = {key: read_setting(root, key, "") for key in keys}
    payload = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def settings_geometry_sha256(root: Path) -> str:
    return _settings_subset_sha256(root, GEOMETRY_SETTING_KEYS)


def name_settings_geometry_sha256(root: Path) -> str:
    return _settings_subset_sha256(root, NAME_GEOMETRY_SETTING_KEYS)


def parse_width(value: str, default: int = 1440) -> int:
    match = re.match(r"\s*(\d+)\s*x", value)
    if match:
        return int(match.group(1))
    if value.upper() == "B5":
        return 1280
    if value.upper() == "A4":
        return 1440
    return default


def manuscript_boxes(root: Path, width: int, comic_format: str, name_board: dict) -> dict:
    manuscript = name_board.get("manuscript") if isinstance(name_board.get("manuscript"), dict) else {}
    if manuscript:
        return manuscript
    spec = read_setting(root, "原稿规格", "数字条漫")
    if "页漫" in comic_format or "B5" in spec or "A4" in spec:
        height = int(width * 1.42)
        bleed = max(24, width // 32)
        safe = max(72, width // 15)
        inner = max(104, width // 11)
    else:
        height = "auto"
        bleed = 0
        safe = max(72, width // 20)
        inner = safe
    numeric_h = int(height) if isinstance(height, int) else 1800
    return {
        "spec": spec,
        "trim_box": {"x": 0, "y": 0, "w": width, "h": height},
        "safe_area": {"x": safe, "y": safe, "w": width - safe * 2, "h": max(1, numeric_h - safe * 2)},
        "bleed": bleed,
        "inner_frame": {"x": inner, "y": inner, "w": width - inner * 2, "h": max(1, numeric_h - inner * 2)},
    }


def name_panel_index(name_board: dict) -> dict[str, tuple[dict, dict]]:
    out: dict[str, tuple[dict, dict]] = {}
    for page in name_board.get("pages") or []:
        if not isinstance(page, dict):
            continue
        for panel in page.get("panels") or []:
            if not isinstance(panel, dict):
                continue
            pid = str(panel.get("panel_id") or "")
            if pid:
                out[pid] = (page, panel)
    return out


def verify_name_board(
    root: Path,
    chapter: str,
    name_board: dict[str, Any],
    *,
    allow_legacy_name: bool = False,
) -> list[str]:
    """Verify the signed name contract before committing layout geometry."""
    if not name_board:
        return ["缺少 name_board.json；layout 必须消费已签收缩略分镜/name board"]
    if name_board.get("schema_version") != 2:
        return [] if allow_legacy_name else ["name_board 必须升级为 schema v2 并签收；迁移时可显式 --allow-legacy-name"]
    errors: list[str] = []
    receipt = name_board.get("upstream_receipt") if isinstance(name_board.get("upstream_receipt"), dict) else {}
    if receipt.get("panel_script_sha256") != sha256_file(root / "脚本" / chapter / "panel_script.json"):
        errors.append("name_board 的 panel_script SHA 已过期")
    if "settings_geometry_sha256" in receipt:
        if receipt.get("settings_geometry_sha256") != name_settings_geometry_sha256(root):
            errors.append("name_board 的几何设置 SHA 已过期")
    elif receipt.get("settings_sha256") != sha256_file(root / "_设置.md"):
        errors.append("name_board 的 settings SHA 已过期")
    approval = name_board.get("approval") if isinstance(name_board.get("approval"), dict) else {}
    if name_board.get("workflow_status") != "approved" or approval.get("status") != "approved":
        errors.append("name_board 尚未 approved")
    else:
        if not str(approval.get("reviewed_by") or "").strip():
            errors.append("name_board approval 缺 reviewed_by")
        if not str(approval.get("reviewed_at") or "").strip():
            errors.append("name_board approval 缺 reviewed_at")
        if approval.get("subject_sha256") != approval_subject_sha256(name_board):
            errors.append("name_board approval subject SHA 不匹配")
    return errors


def parse_max_segment_height(value: str, default: int = 0) -> int:
    raw = str(value or "").strip()
    if not raw:
        return default
    lowered = raw.lower()
    if raw == "0" or any(token in lowered for token in ("不分段", "不限", "单张", "single", "none", "no-split", "unlimited")):
        return 0
    match = re.search(r"\d+", raw)
    return int(match.group(0)) if match else default


def explicit_layout_weight(panel: dict) -> str:
    for key in ("layout_weight", "visual_weight", "importance"):
        raw = str(panel.get(key) or "").strip().lower()
        if not raw:
            continue
        if raw in {"heavy", "large", "big", "重点", "大格", "强", "高"}:
            return "heavy"
        if raw in {"medium", "normal", "标准", "中"}:
            return "medium"
        if raw in {"compact", "small", "轻", "低", "小格"}:
            return "compact"
        if raw.isdigit():
            value = int(raw)
            if value >= 3:
                return "heavy"
            if value <= 1:
                return "compact"
            return "medium"
    return ""


def first_text(record: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        value = str(record.get(key, "") or "").strip()
        if value:
            return value
    return ""


def target_dialogue_text(dialogue: dict) -> str:
    return first_text(dialogue, ("text_target", "target_text", "text"))


def narration_text(panel: dict) -> str:
    return first_text(panel, ("narration_target", "target_narration", "narration"))


def text_overflow_units(panel: dict) -> int:
    units = 0
    if narration_text(panel):
        units += max(0, estimated_line_count(narration_text(panel), 560, 42) - 2)
    for dialogue in panel.get("dialogue") or []:
        units += max(0, estimated_line_count(target_dialogue_text(dialogue), 430, 44) - 2)
    return units


def panel_height(panel: dict) -> int:
    fn = str(panel.get("story_function", "")).strip()
    dialogue_count = len(panel.get("dialogue") or [])
    has_narration = bool(narration_text(panel))
    has_sfx = bool(panel.get("sfx") or [])
    lowered = fn.lower()
    notes = str(panel.get("art_notes") or "")
    description = str(panel.get("description") or "")
    wants_big = any(token in notes or token in description for token in ("大格", "重点", "钩子", "压迫", "奇观"))
    explicit = explicit_layout_weight(panel)
    if explicit == "heavy" or fn in HEAVY_FUNCTIONS or any(token in lowered for token in HEAVY_TOKENS) or wants_big:
        base = 960
    elif explicit == "medium" or fn in MEDIUM_FUNCTIONS or any(token in lowered for token in MEDIUM_TOKENS):
        base = 840
    elif explicit == "compact" or fn in COMPACT_FUNCTIONS:
        base = 620
    elif any(token in lowered for token in COMPACT_TOKENS):
        base = 680
    else:
        base = 760
    if dialogue_count >= 2:
        base += 120
    if has_narration:
        base += 80
    if has_sfx:
        base += 80
    base += min(260, text_overflow_units(panel) * 36)
    return min(max(base, 560), 1500)


def text_slot_height(text: str, slot_w: int, font_size: int, base: int) -> int:
    lines = estimated_line_count(text, slot_w, font_size)
    return base + max(0, lines - 2) * 34


def _fallback_balloon_contracts(panel: dict[str, Any]) -> list[dict[str, Any]]:
    pid = str(panel.get("panel_id") or "")
    out: list[dict[str, Any]] = []
    order = 1
    if narration_text(panel):
        out.append({"type": "narration", "content_ref": f"panel:{pid}.narration", "speaker": "", "order": order, "tail": {"mode": "none", "target": ""}})
        order += 1
    for item_index, dialogue in enumerate(panel.get("dialogue") or [], 1):
        if not isinstance(dialogue, dict) or not target_dialogue_text(dialogue):
            continue
        speaker = str(dialogue.get("speaker") or "")
        out.append({"type": "dialogue", "content_ref": f"panel:{pid}.dialogue:{item_index}", "speaker": speaker, "order": order, "tail": {"mode": "toward_speaker", "target": speaker or "unresolved_speaker"}})
        order += 1
    raw_sfx = panel.get("sfx") or []
    if isinstance(raw_sfx, str):
        raw_sfx = [raw_sfx]
    for item_index, item in enumerate(raw_sfx, 1):
        if str(item or "").strip():
            out.append({"type": "sfx", "content_ref": f"panel:{pid}.sfx:{item_index}", "speaker": "", "order": order, "tail": {"mode": "action_path", "target": "impact_or_motion_anchor"}})
            order += 1
    return out


def bubble_slots(panel: dict, rect: dict, index: int, name_panel: dict[str, Any] | None = None) -> list[dict]:
    """Place one bounded slot for every signed text/SFX content reference."""
    name_panel = name_panel or {}
    contracts = [item for item in name_panel.get("balloons") or [] if isinstance(item, dict)] or _fallback_balloon_contracts(panel)
    x, y, w, h = (int(rect[key]) for key in ("x", "y", "w", "h"))
    pad = max(12, min(48, w // 18, h // 18))
    usable_w = max(80, w - pad * 2)
    usable_h = max(80, h - pad * 2)
    text_contracts = [item for item in contracts if item.get("type") != "sfx"]
    rows = max(1, (len(text_contracts) + 1) // 2)
    slot_w = max(80, min(430, (usable_w - pad) // 2 if len(text_contracts) > 1 else min(560, usable_w)))
    slot_h_cap = max(48, min(180, usable_h // max(2, rows + 1)))
    slots: list[dict[str, Any]] = []
    text_index = 0
    for contract_index, contract in enumerate(contracts, 1):
        kind = str(contract.get("type") or "dialogue")
        if kind == "sfx":
            sfx_count = sum(1 for item in contracts[:contract_index] if item.get("type") == "sfx")
            sw = max(80, min(360, usable_w // 2))
            sh = max(48, min(150, usable_h // 4))
            slot_x = x + max(pad, (w - sw) // 2)
            slot_y = y + h - pad - sh - (sfx_count - 1) * min(sh + 8, max(1, usable_h // 5))
        else:
            row = text_index // 2
            col = text_index % 2
            if len(text_contracts) == 1:
                col = 0
            bubble_first = str(rect.get("bubble_first") or "")
            prefer_right = bubble_first == "right_top"
            if len(text_contracts) > 1:
                visual_col = 1 - col if prefer_right else col
                slot_x = x + pad + visual_col * (slot_w + pad)
            else:
                slot_x = x + w - pad - slot_w if prefer_right else x + pad
            raw_text = narration_text(panel) if kind == "narration" else ""
            if kind == "dialogue":
                dialogue_items = [item for item in panel.get("dialogue") or [] if isinstance(item, dict) and target_dialogue_text(item)]
                dialogue_number = sum(1 for item in contracts[:contract_index] if item.get("type") == "dialogue")
                if 0 < dialogue_number <= len(dialogue_items):
                    raw_text = target_dialogue_text(dialogue_items[dialogue_number - 1])
            sh = min(slot_h_cap, text_slot_height(raw_text, slot_w, 44 if kind == "dialogue" else 42, 88))
            slot_y = y + pad + row * (slot_h_cap + max(6, pad // 2))
            sw = slot_w
            text_index += 1
        slots.append(
            {
                "slot_id": f"B{index:03d}{'S' if kind == 'sfx' else 'N' if kind == 'narration' else 'D'}{contract_index}",
                "type": kind,
                "content_ref": str(contract.get("content_ref") or ""),
                "speaker": str(contract.get("speaker") or ""),
                "order": int(contract.get("order") or contract_index),
                "tail": contract.get("tail") if isinstance(contract.get("tail"), dict) else {"mode": "none", "target": ""},
                "x": max(x, min(slot_x, x + w - sw)),
                "y": max(y, min(slot_y, y + h - sh)),
                "w": sw,
                "h": sh,
            }
        )
    return slots


def gutter_after(name_panel: dict[str, Any], default: int) -> int:
    explicit = name_panel.get("gutter_after") or name_panel.get("gutter_px")
    if str(explicit or "").strip().isdigit():
        return max(0, int(explicit))
    intent = str(name_panel.get("gutter_intent") or "").lower()
    if any(token in intent for token in ("long", "pause", "breath", "停顿", "呼吸", "留白")):
        return max(default, default * 2)
    if any(token in intent for token in ("quick", "fast", "cut", "快切", "紧接")):
        return max(8, int(default * 0.6))
    return default


def map_thumbnail_rect(name_panel: dict[str, Any], manuscript: dict[str, Any], width: int) -> dict[str, int]:
    thumb = name_panel.get("thumbnail_rect") if isinstance(name_panel.get("thumbnail_rect"), dict) else {}
    safe = manuscript.get("safe_area") if isinstance(manuscript.get("safe_area"), dict) else {}
    if not thumb or not safe:
        raise LayoutError(f"{name_panel.get('panel_id')}: 缺 thumbnail_rect/manuscript.safe_area")
    source_w = max(1, int((manuscript.get("trim_box") or {}).get("w") or width))
    scale = width / source_w
    return {key: max(1 if key in {"w", "h"} else 0, int(round(int(thumb.get(key) or 0) * scale))) for key in ("x", "y", "w", "h")}


def panel_metadata(
    panel: dict[str, Any],
    name_page: dict[str, Any],
    name_panel: dict[str, Any],
    rect: dict[str, int],
    index: int,
) -> dict[str, Any]:
    thumb = name_panel.get("thumbnail_rect") if isinstance(name_panel.get("thumbnail_rect"), dict) else {}

    def mapped_regions(key: str) -> list[dict[str, Any]]:
        regions: list[dict[str, Any]] = []
        tx, ty, tw, th = (int(thumb.get(item) or 0) for item in ("x", "y", "w", "h"))
        for source in name_panel.get(key) or []:
            if not isinstance(source, dict):
                continue
            item = copy.deepcopy(source)
            source_rect = item.get("rect") if isinstance(item.get("rect"), dict) else {}
            if tw > 0 and th > 0 and source_rect:
                rx, ry, rw, rh = (int(source_rect.get(field) or 0) for field in ("x", "y", "w", "h"))
                item["rect"] = {
                    "x": int(rect["x"] + (rx - tx) / tw * rect["w"]),
                    "y": int(rect["y"] + (ry - ty) / th * rect["h"]),
                    "w": max(1, int(rw / tw * rect["w"])),
                    "h": max(1, int(rh / th * rect["h"])),
                }
            regions.append(item)
        return regions

    out: dict[str, Any] = {
        "panel_id": str(panel.get("panel_id")),
        **rect,
        "layout_weight": name_panel.get("layout_weight") or explicit_layout_weight(panel) or "medium",
        "panel_shape": name_panel.get("panel_shape") or panel.get("panel_shape") or "standard",
        "border_style": name_panel.get("border_style") or panel.get("border_style") or "standard",
        "gutter_intent": name_panel.get("gutter_intent") or panel.get("gutter_intent") or "",
        "bubble_first": name_panel.get("bubble_first") or "",
        "effects_hint": name_panel.get("effects_hint") or panel.get("effects_plan") or panel.get("effects_hint") or "",
        "name_page_id": name_page.get("page_id") or "",
        "page_side": name_page.get("page_side") or "",
        "spread_id": name_page.get("spread_id") or "",
        "page_turn_hook": name_page.get("page_turn_hook") or "",
        "page_turn": name_page.get("page_turn") if isinstance(name_page.get("page_turn"), dict) else {},
        "subject_regions": mapped_regions("subject_regions"),
        "avoid_regions": mapped_regions("avoid_regions"),
        "eye_flow_entry": name_panel.get("eye_flow_entry") or "",
        "eye_flow_exit": name_panel.get("eye_flow_exit") or "",
    }
    out["bubble_slots"] = bubble_slots(panel, out, index, name_panel)
    return out


def _script_panel_map(panel_script: dict[str, Any]) -> tuple[list[str], dict[str, dict[str, Any]]]:
    panels = [item for item in panel_script.get("panels") or [] if isinstance(item, dict) and item.get("panel_id")]
    ids = [str(item.get("panel_id")) for item in panels]
    if not ids:
        raise LayoutError("panel_script.panels 为空")
    if len(ids) != len(set(ids)):
        raise LayoutError("panel_script.panel_id 必须唯一")
    return ids, {str(item.get("panel_id")): item for item in panels}


def _build_paged_segments(
    pages: list[dict[str, Any]],
    panel_map: dict[str, dict[str, Any]],
    manuscript: dict[str, Any],
    width: int,
) -> list[dict[str, Any]]:
    page_h = int((manuscript.get("trim_box") or {}).get("h") or int(width * 1.42))
    segments: list[dict[str, Any]] = []
    index = 0
    for page_number, page in enumerate(pages, 1):
        items: list[dict[str, Any]] = []
        for name_panel in page.get("panels") or []:
            pid = str(name_panel.get("panel_id") or "")
            index += 1
            items.append(panel_metadata(panel_map[pid], page, name_panel, map_thumbnail_rect(name_panel, manuscript, width), index))
        segments.append(
            {
                "segment_id": str(page.get("page_id") or f"PAGE_{page_number:03d}"),
                "page_side": str(page.get("page_side") or ""),
                "spread_id": str(page.get("spread_id") or ""),
                "width": width,
                "height": page_h,
                "reading_order": [item["panel_id"] for item in items],
                "panels": items,
            }
        )
    return segments


def _build_longstrip_segments(
    pages: list[dict[str, Any]],
    panel_map: dict[str, dict[str, Any]],
    manuscript: dict[str, Any],
    width: int,
    max_segment_height: int,
    gutter: int,
) -> list[dict[str, Any]]:
    safe = manuscript.get("safe_area") or {}
    source_x, source_w = int(safe.get("x") or 0), max(1, int(safe.get("w") or width))
    margin = max(24, width // 20)
    available_w = width - margin * 2
    segments: list[dict[str, Any]] = []
    global_index = 0
    for page_number, page in enumerate(pages, 1):
        part = 1
        current: dict[str, Any] = {
            "segment_id": str(page.get("page_id") or f"SCROLL_{page_number:03d}"),
            "source_name_page_id": str(page.get("page_id") or ""),
            "width": width,
            "height": 0,
            "reading_order": [],
            "panels": [],
        }
        cursor_y = gutter
        for name_panel in page.get("panels") or []:
            pid = str(name_panel.get("panel_id") or "")
            panel = panel_map[pid]
            thumb = name_panel.get("thumbnail_rect") or {}
            rel_x = (int(thumb.get("x") or source_x) - source_x) / source_w
            rel_w = int(thumb.get("w") or source_w) / source_w
            panel_x = margin + int(max(0.0, rel_x) * available_w)
            panel_w = max(int(width * 0.35), min(available_w, int(rel_w * available_w)))
            if panel_x + panel_w > width - margin:
                panel_x = width - margin - panel_w
            thumb_ratio = int(thumb.get("h") or 1) / max(1, int((manuscript.get("safe_area") or {}).get("h") or 1800))
            h = max(panel_height(panel), int(thumb_ratio * 4200))
            h = min(max(h, 480), 1800)
            gap_after = gutter_after(name_panel, gutter)
            if max_segment_height > 0 and current["panels"] and cursor_y + h + gap_after > max_segment_height:
                current["height"] = cursor_y
                segments.append(current)
                part += 1
                current = {
                    "segment_id": f"{page.get('page_id') or f'SCROLL_{page_number:03d}'}_{part}",
                    "source_name_page_id": str(page.get("page_id") or ""),
                    "width": width,
                    "height": 0,
                    "reading_order": [],
                    "panels": [],
                }
                cursor_y = gutter
            global_index += 1
            item = panel_metadata(panel, page, name_panel, {"x": panel_x, "y": cursor_y, "w": panel_w, "h": h}, global_index)
            item["gutter_after"] = gap_after
            current["panels"].append(item)
            current["reading_order"].append(pid)
            cursor_y += h + gap_after
        if current["panels"]:
            current["height"] = cursor_y
            segments.append(current)
    return segments


def build_layout(
    root: Path,
    chapter: str,
    max_segment_height: int,
    gutter: int,
    *,
    allow_legacy_name: bool = False,
) -> dict:
    panel_path = root / "脚本" / chapter / "panel_script.json"
    name_path = root / "排版" / chapter / "name_board.json"
    if not panel_path.is_file():
        raise LayoutError(f"缺少输入：{panel_path}")
    if not name_path.is_file():
        raise LayoutError(f"缺少输入：{name_path}")
    panel_script = load_json(panel_path)
    name_board = load_json(name_path)
    name_errors = verify_name_board(root, chapter, name_board, allow_legacy_name=allow_legacy_name)
    if name_errors:
        raise LayoutError("；".join(name_errors))
    expected_ids, panel_map = _script_panel_map(panel_script)
    pages = [item for item in name_board.get("pages") or [] if isinstance(item, dict)]
    name_ids = [str(item.get("panel_id") or "") for page in pages for item in page.get("panels") or [] if isinstance(item, dict)]
    if name_ids != expected_ids:
        raise LayoutError("name_board panel 顺序/覆盖与 panel_script 不一致")
    width = parse_width(read_setting(root, "页面尺寸", "1440xauto"))
    comic_format = read_setting(root, "漫画形态", str(name_board.get("format") or "条漫"))
    reading_direction = read_setting(root, "阅读方向", str(name_board.get("reading_direction") or "从上到下"))
    manuscript = manuscript_boxes(root, width, comic_format, name_board)
    if "四格" in comic_format:
        if any(len(page.get("panels") or []) != 4 for page in pages):
            raise LayoutError("yonkoma_four_rows 要求每页恰好 4 格")
        geometry_profile = "yonkoma_four_rows"
        segments = _build_paged_segments(pages, panel_map, manuscript, width)
    elif "页漫" in comic_format:
        geometry_profile = "paged_grid_rtl" if reading_direction == "从右到左" else "paged_grid_ltr"
        segments = _build_paged_segments(pages, panel_map, manuscript, width)
    else:
        geometry_profile = "longstrip_single_column"
        segments = _build_longstrip_segments(pages, panel_map, manuscript, width, max_segment_height, gutter)
    layout: dict[str, Any] = {
        "schema_version": 2,
        "kind": "comic_layout",
        "workflow_status": "draft",
        "chapter": chapter,
        "format": comic_format,
        "reading_direction": reading_direction,
        "geometry_profile": geometry_profile,
        "format_supported_by_script": True,
        "manuscript": manuscript,
        "name_board": str(Path("排版") / chapter / "name_board.json"),
        "canvas": {"width": width, "height": (manuscript.get("trim_box") or {}).get("h", "auto") if geometry_profile.startswith("paged_") or geometry_profile.startswith("yonkoma") else "auto"},
        "segments": segments,
        "upstream_receipt": {
            "panel_script": str(Path("脚本") / chapter / "panel_script.json"),
            "panel_script_sha256": sha256_file(panel_path),
            "name_board": str(Path("排版") / chapter / "name_board.json"),
            "name_board_sha256": sha256_file(name_path),
            "name_approval_subject_sha256": ((name_board.get("approval") or {}).get("subject_sha256") if isinstance(name_board.get("approval"), dict) else ""),
            "settings": "_设置.md",
            "settings_sha256": sha256_file(root / "_设置.md"),
            "settings_geometry_sha256": settings_geometry_sha256(root),
            "legacy_name_waiver": bool(allow_legacy_name and name_board.get("schema_version") != 2),
        },
        "approval": {},
    }
    errors = validate_layout(layout, panel_script, name_board)
    layout["validation"] = {"status": "pass" if not errors else "fail", "errors": errors}
    if errors:
        raise LayoutError("layout 校验失败：" + "；".join(errors))
    return layout


def _rect_overlap(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return not (
        int(left.get("x") or 0) + int(left.get("w") or 0) <= int(right.get("x") or 0)
        or int(right.get("x") or 0) + int(right.get("w") or 0) <= int(left.get("x") or 0)
        or int(left.get("y") or 0) + int(left.get("h") or 0) <= int(right.get("y") or 0)
        or int(right.get("y") or 0) + int(right.get("h") or 0) <= int(left.get("y") or 0)
    )


def validate_layout(layout: dict[str, Any], panel_script: dict[str, Any], name_board: dict[str, Any]) -> list[str]:
    """Deterministic structural validator; it does not make aesthetic claims."""
    errors: list[str] = []
    if layout.get("schema_version") != 2 or layout.get("kind") != "comic_layout":
        errors.append("需要 comic_layout schema v2")
    expected, panel_map = _script_panel_map(panel_script)
    name_index = name_panel_index(name_board)
    seen: list[str] = []
    for segment in layout.get("segments") or []:
        if not isinstance(segment, dict):
            errors.append("segments[] 必须是对象")
            continue
        width, height = int(segment.get("width") or 0), int(segment.get("height") or 0)
        panels = [item for item in segment.get("panels") or [] if isinstance(item, dict)]
        if width <= 0 or height <= 0 or not panels:
            errors.append(f"{segment.get('segment_id')}: width/height/panels 无效")
            continue
        ids = [str(item.get("panel_id") or "") for item in panels]
        if segment.get("reading_order") != ids:
            errors.append(f"{segment.get('segment_id')}: reading_order 与 panels 顺序不一致")
        for index, panel in enumerate(panels):
            pid = str(panel.get("panel_id") or "")
            seen.append(pid)
            x, y, w, h = (int(panel.get(key) or 0) for key in ("x", "y", "w", "h"))
            if min(w, h) <= 0 or x < 0 or y < 0 or x + w > width or y + h > height:
                errors.append(f"{pid}: panel rect 越界或尺寸无效")
            for other in panels[index + 1 :]:
                if _rect_overlap(panel, other):
                    errors.append(f"{pid}/{other.get('panel_id')}: panel rect 重叠")
            source = panel_map.get(pid, {})
            _page, name_panel = name_index.get(pid, ({}, {}))
            expected_contracts = [item for item in name_panel.get("balloons") or [] if isinstance(item, dict)] or _fallback_balloon_contracts(source)
            slots = [item for item in panel.get("bubble_slots") or [] if isinstance(item, dict)]
            expected_types = [str(item.get("type") or "") for item in expected_contracts]
            actual_types = [str(item.get("type") or "") for item in slots]
            if actual_types != expected_types:
                errors.append(f"{pid}: bubble_slots 未完整覆盖 narration/dialogue/SFX")
            for slot in slots:
                sx, sy, sw, sh = (int(slot.get(key) or 0) for key in ("x", "y", "w", "h"))
                if min(sw, sh) <= 0 or sx < x or sy < y or sx + sw > x + w or sy + sh > y + h:
                    errors.append(f"{pid}/{slot.get('slot_id')}: bubble slot 越出 panel")
                if name_board.get("schema_version") == 2 and not slot.get("content_ref"):
                    errors.append(f"{pid}/{slot.get('slot_id')}: 缺 content_ref")
    if seen != expected:
        errors.append("layout panel 顺序/覆盖必须与 panel_script 完全一致")
    if len(seen) != len(set(seen)):
        errors.append("layout 中 panel_id 重复")
    profile = str(layout.get("geometry_profile") or "")
    fmt = str(layout.get("format") or "")
    if "四格" in fmt and profile != "yonkoma_four_rows":
        errors.append("四格必须使用 yonkoma_four_rows")
    elif "页漫" in fmt and profile not in {"paged_grid_ltr", "paged_grid_rtl"}:
        errors.append("页漫必须使用 paged_grid_ltr/rtl")
    elif not any(token in fmt for token in ("四格", "页漫")) and profile != "longstrip_single_column":
        errors.append("条漫必须使用 longstrip_single_column")
    return errors


def verify_layout_upstream(
    root: Path,
    chapter: str,
    layout: dict[str, Any],
    name_board: dict[str, Any],
    *,
    allow_legacy_name: bool = False,
) -> list[str]:
    errors = verify_name_board(root, chapter, name_board, allow_legacy_name=allow_legacy_name)
    receipt = layout.get("upstream_receipt") if isinstance(layout.get("upstream_receipt"), dict) else {}
    current = {
        "panel_script_sha256": sha256_file(root / "脚本" / chapter / "panel_script.json"),
        "name_board_sha256": sha256_file(root / "排版" / chapter / "name_board.json"),
    }
    for key, value in current.items():
        if receipt.get(key) != value:
            errors.append(f"layout upstream {key} 已过期")
    # Prefer the geometry-subset hash; fall back to whole-file only for legacy
    # receipts written before the subset existed.
    if "settings_geometry_sha256" in receipt:
        if receipt.get("settings_geometry_sha256") != settings_geometry_sha256(root):
            errors.append("影响几何的设置（漫画形态/阅读方向/页面尺寸/原稿规格/单话分段高度）已变化，layout 已过期")
    elif receipt.get("settings_sha256") != sha256_file(root / "_设置.md"):
        errors.append("layout upstream settings_sha256 已过期")
    return errors


def transition_existing(
    root: Path,
    chapter: str,
    target: str,
    *,
    reviewed_by: str = "",
    note: str = "",
    allow_legacy_name: bool = False,
) -> dict[str, Any]:
    layout_path = root / "排版" / chapter / "layout.json"
    name_path = root / "排版" / chapter / "name_board.json"
    if not layout_path.is_file() or not name_path.is_file():
        raise LayoutError("缺少 layout.json 或 name_board.json")
    layout = load_json(layout_path)
    name_board = load_json(name_path)
    panel_script = load_json(root / "脚本" / chapter / "panel_script.json")
    errors = verify_layout_upstream(root, chapter, layout, name_board, allow_legacy_name=allow_legacy_name)
    errors += validate_layout(layout, panel_script, name_board)
    if errors:
        raise LayoutError("不能变更 layout 状态：" + "；".join(errors))
    current = str(layout.get("workflow_status") or "")
    if target == "review":
        if current not in {"draft", "review"}:
            raise LayoutError("只有 draft/review layout 可提交复核")
        layout["workflow_status"] = "review"
        layout["approval"] = {}
    elif target == "approved":
        if current != "review":
            raise LayoutError("layout 必须先 --submit-review，再执行 --approve")
        if not reviewed_by.strip():
            raise LayoutError("--approve 必须提供 --reviewed-by")
        layout["workflow_status"] = "approved"
        layout["approval"] = {
            "kind": "comic_layout_approval",
            "status": "approved",
            "reviewed_by": reviewed_by.strip(),
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "note": note.strip(),
            "subject_sha256": approval_subject_sha256(layout),
            "panel_script_sha256": (layout.get("upstream_receipt") or {}).get("panel_script_sha256", ""),
            "name_board_sha256": (layout.get("upstream_receipt") or {}).get("name_board_sha256", ""),
            "settings_sha256": (layout.get("upstream_receipt") or {}).get("settings_sha256", ""),
            "settings_geometry_sha256": (layout.get("upstream_receipt") or {}).get("settings_geometry_sha256", ""),
        }
    else:
        raise LayoutError(f"未知状态：{target}")
    layout["validation"] = {"status": "pass", "errors": []}
    layout_path.write_text(json.dumps(layout, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return layout


def verify_layout_approval(layout: dict[str, Any]) -> list[str]:
    approval = layout.get("approval") if isinstance(layout.get("approval"), dict) else {}
    if layout.get("workflow_status") != "approved" or approval.get("status") != "approved":
        return ["layout 尚未 approved"]
    errors: list[str] = []
    if not str(approval.get("reviewed_by") or "").strip():
        errors.append("layout approval 缺 reviewed_by")
    if not str(approval.get("reviewed_at") or "").strip():
        errors.append("layout approval 缺 reviewed_at")
    if approval.get("subject_sha256") != approval_subject_sha256(layout):
        errors.append("layout approval subject SHA 不匹配")
    return errors


def update_progress(root: Path, chapter: str, stage: str, value: str) -> None:
    update_progress_stage(root, chapter, stage, value, actor="comic-layout")


def write_notes(root: Path, chapter: str, layout: dict) -> None:
    total_panels = sum(len(seg.get("panels", [])) for seg in layout.get("segments", []))
    lines = [
        f"# 排版说明 — {chapter}",
        "",
        f"- 形态：{layout.get('format')}",
        f"- 阅读方向：{layout.get('reading_direction')}",
        f"- 原稿规格：{(layout.get('manuscript') or {}).get('spec', '')}",
        f"- 几何 adapter：{layout.get('geometry_profile')}",
        f"- 工作流状态：{layout.get('workflow_status')}",
        f"- 缩略分镜：{layout.get('name_board') or '未接入'}",
        f"- 分段数：{len(layout.get('segments', []))}",
        f"- 面板数：{total_panels}",
        "- 气泡坐标为 MVP 占位，正式嵌字前需人工检查是否挡脸、手、刀、妖物关键动作。",
        "- 出图阶段应生成无字画面，只预留低细节留白；不要把正文台词、文字框或空白气泡烘焙进图片。",
    ]
    path = root / "排版" / chapter / "layout_notes.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="从 panel_script.json 生成 comic layout.json")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--max-segment-height", type=int, default=None)
    parser.add_argument("--gutter", type=int, default=28)
    parser.add_argument("--no-progress", action="store_true")
    parser.add_argument("--allow-legacy-name", action="store_true", help="仅迁移/旧测试：显式接受未签收 schema v1 name")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--submit-review", action="store_true", help="把现有 draft layout 提交为 review")
    action.add_argument("--approve", action="store_true", help="签收现有 review layout")
    action.add_argument("--check", action="store_true", help="只读检查 layout 的结构、上游 SHA 与审批")
    parser.add_argument("--reviewed-by", default="")
    parser.add_argument("--approval-note", default="")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    out_path = root / "排版" / args.chapter / "layout.json"
    try:
        if args.check:
            layout = load_json(out_path)
            name_board = load_json(root / "排版" / args.chapter / "name_board.json")
            panel_script = load_json(root / "脚本" / args.chapter / "panel_script.json")
            errors = verify_layout_upstream(root, args.chapter, layout, name_board, allow_legacy_name=args.allow_legacy_name)
            errors += validate_layout(layout, panel_script, name_board)
            errors += verify_layout_approval(layout)
            if errors:
                for error in errors:
                    print(f"[block] {error}")
                return 2
            print(f"[ok] approved/current {out_path}")
            return 0
        if args.submit_review:
            layout = transition_existing(root, args.chapter, "review", allow_legacy_name=args.allow_legacy_name)
            write_notes(root, args.chapter, layout)
            if not args.no_progress:
                update_progress(root, args.chapter, "页面排版", "🟡待签收")
            print(f"[ok] review {out_path}")
            return 0
        if args.approve:
            layout = transition_existing(
                root,
                args.chapter,
                "approved",
                reviewed_by=args.reviewed_by,
                note=args.approval_note,
                allow_legacy_name=args.allow_legacy_name,
            )
            write_notes(root, args.chapter, layout)
            if not args.no_progress:
                update_progress(root, args.chapter, "页面排版", "✅")
            print(f"[ok] approved {out_path}")
            return 0

        max_height = args.max_segment_height if args.max_segment_height is not None else parse_max_segment_height(read_setting(root, "单话分段高度", "0"))
        layout = build_layout(root, args.chapter, max_height, args.gutter, allow_legacy_name=args.allow_legacy_name)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(layout, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_notes(root, args.chapter, layout)
        if not args.no_progress:
            update_progress(root, args.chapter, "页面排版", "🟡待签收")
        print(f"[ok] draft {out_path}")
        print(f"[ok] adapter={layout.get('geometry_profile')} validator=pass")
        print("[next] 审阅后先 --submit-review，再用 --approve --reviewed-by <签收人>；可由用户授权制作代理执行，未签收 layout 不写 ✅")
        return 0
    except (ValueError, OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"[block] {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
