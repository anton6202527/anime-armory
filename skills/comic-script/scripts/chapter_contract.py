#!/usr/bin/env python3
"""Shared comic chapter-contract helpers.

This module intentionally lives inside comic-script.  It has no dependency on
another production line and is small enough to ship with this skill.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = 2
CHAPTER_TYPES = {"serial", "one_shot", "gag", "bridge", "epilogue"}
FORMAT_PROFILES = {
    "vertical_serial",
    "paged_rtl",
    "paged_ltr",
    "yonkoma",
    "custom",
}
SOURCE_MODES = {"adapted", "original"}
ENDING_MODES = {
    "cliffhanger",
    "reveal",
    "decision",
    "emotional_aftershock",
    "closure_with_new_promise",
    "gag_payoff",
    "complete_closure",
    "transition",
}
CHAPTER_STATUSES = {"draft", "review", "confirmed", "locked"}
LONG_SERIES_TYPES = {"serial", "bridge", "epilogue"}

_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
_UNITS = {"十": 10, "百": 100, "千": 1000, "万": 10000}
_NUMBER_TOKEN = r"[0-9]+|[零〇一二两三四五六七八九十百千万]+"
SOURCE_UNIT_RE = re.compile(
    rf"(?m)^[ \t]*第\s*(?P<number>{_NUMBER_TOKEN})\s*(?P<kind>话|話|章|回|节)"
)


def chinese_number_to_int(value: Any) -> int | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        return int(raw)
    if any(ch not in _DIGITS and ch not in _UNITS for ch in raw):
        return None
    # Section-based parser: 十二=12, 一百零二=102, 一万零三=10003.
    total = 0
    section = 0
    number = 0
    for ch in raw:
        if ch in _DIGITS:
            number = _DIGITS[ch]
            continue
        unit = _UNITS[ch]
        if unit == 10000:
            section = (section + number) * unit
            total += section
            section = 0
            number = 0
        else:
            section += (number or 1) * unit
            number = 0
    return total + section + number


def parse_numbered_label(value: Any) -> tuple[int, str] | None:
    match = re.search(
        rf"第\s*(?P<number>{_NUMBER_TOKEN})\s*(?P<kind>话|話|章|回|节)",
        str(value or ""),
    )
    if not match:
        return None
    number = chinese_number_to_int(match.group("number"))
    if number is None:
        return None
    kind = "话" if match.group("kind") == "話" else match.group("kind")
    return number, kind


def normalize_chapter(value: Any) -> str:
    parsed = parse_numbered_label(value)
    if parsed:
        return f"第{parsed[0]}话"
    raw = str(value or "").strip()
    match = re.fullmatch(r"(?:chapter|ch)?\s*(\d+)", raw, re.IGNORECASE)
    return f"第{int(match.group(1))}话" if match else raw


def chapter_number(value: Any) -> int | None:
    parsed = parse_numbered_label(value)
    if parsed:
        return parsed[0]
    match = re.search(r"\d+", str(value or ""))
    return int(match.group()) if match else None


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_blueprint(root: Path) -> tuple[dict[str, Any] | None, str | None]:
    path = root / "脚本" / "split_blueprint.json"
    if not path.is_file():
        return None, "split_blueprint_missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "split_blueprint_invalid"
    if not isinstance(data, dict):
        return None, "split_blueprint_invalid"
    return data, None


def chapter_contract(root: Path, chapter: Any) -> tuple[dict[str, Any] | None, str | None]:
    blueprint, error = load_blueprint(root)
    if error:
        return None, error
    assert blueprint is not None
    if int(blueprint.get("version") or 1) < SCHEMA_VERSION:
        return None, "split_blueprint_v1_legacy"
    wanted = normalize_chapter(chapter)
    entries = blueprint.get("chapters")
    if not isinstance(entries, list):
        return None, "split_blueprint_chapters_invalid"
    for entry in entries:
        if isinstance(entry, dict) and normalize_chapter(entry.get("chapter")) == wanted:
            return entry, None
    return None, "chapter_contract_missing"


def _nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return bool(value)
    return value is not None


# Vacuous-but-present values that currently pass every presence-only check.
_PLACEHOLDER_TOKENS = {
    "tbd", "tba", "todo", "n/a", "na", "none", "null", "?", "??", "???",
    "待定", "待补", "待补充", "待填", "待写", "待定义", "暂无", "无", "略",
    "同上", "见上", "见下", "见后文", "xx", "xxx", "...", "…",
}
_FILLER_RE = re.compile(r"^[\s\-—.·、,，。?？!！…*xX]+$")


def _is_placeholder(value: Any) -> bool:
    """True when a required narrative field is present but vacuous.

    Presence-only validation lets `payoff: "TBD"` / `turning_point: "待定"` /
    single-char stubs pass; a real beat is a described phrase, so these are
    deterministically not-a-value.
    """
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return True
    if text.lower() in _PLACEHOLDER_TOKENS:
        return True
    if _FILLER_RE.match(text):
        return True
    # A single character can't carry a narrative beat; 2+ CJK chars may be a
    # terse-but-real value ("反击"/"封锁"), so only the explicit token set and
    # filler patterns above reject those — no blanket short-length rule.
    return len(text) <= 1


def validate_source_span(span: Any, prefix: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not isinstance(span, Mapping):
        return [{"code": "source_span_invalid", "message": f"{prefix} 必须是 object。"}]
    source_path = str(span.get("source_path") or "").strip()
    if not source_path:
        issues.append({"code": "source_span_path_missing", "message": f"{prefix}.source_path 必填。"})
    if span.get("whole_file") is True:
        if span.get("start") or span.get("end"):
            issues.append({"code": "source_span_whole_with_range", "message": f"{prefix} whole_file=true 时不要再写 start/end。"})
        return issues
    start = parse_numbered_label(span.get("start"))
    end = parse_numbered_label(span.get("end") or span.get("start"))
    if not start:
        issues.append({"code": "source_span_start_invalid", "message": f"{prefix}.start 应为第N章/回/话/节。"})
    if not end:
        issues.append({"code": "source_span_end_invalid", "message": f"{prefix}.end 应为第N章/回/话/节。"})
    if start and end:
        if start[1] != end[1]:
            issues.append({"code": "source_span_kind_mismatch", "message": f"{prefix} start/end 单位必须一致。"})
        elif start[0] > end[0]:
            issues.append({"code": "source_span_reversed", "message": f"{prefix} start 不得晚于 end。"})
    return issues


def validate_chapter_entry(entry: Any, index: int) -> list[dict[str, str]]:
    prefix = f"chapters[{index}]"
    if not isinstance(entry, Mapping):
        return [{"code": "chapter_contract_invalid", "message": f"{prefix} 必须是 object。"}]
    issues: list[dict[str, str]] = []
    normalized_chapter = normalize_chapter(entry.get("chapter"))
    number = chapter_number(normalized_chapter)
    if number is None or number <= 0 or not re.fullmatch(r"第[1-9][0-9]*话", normalized_chapter):
        issues.append({"code": "chapter_id_invalid", "message": f"{prefix}.chapter 应为第N话。"})
    chapter_type = str(entry.get("chapter_type") or "")
    if chapter_type not in CHAPTER_TYPES:
        issues.append({"code": "chapter_type_invalid", "message": f"{prefix}.chapter_type 须为 {sorted(CHAPTER_TYPES)} 之一。"})
    format_profile = str(entry.get("format_profile") or "")
    if format_profile not in FORMAT_PROFILES:
        issues.append({"code": "format_profile_invalid", "message": f"{prefix}.format_profile 须为 {sorted(FORMAT_PROFILES)} 之一。"})
    source_mode = str(entry.get("source_mode") or "adapted")
    if source_mode not in SOURCE_MODES:
        issues.append({"code": "source_mode_invalid", "message": f"{prefix}.source_mode 须为 adapted/original。"})
    spans = entry.get("source_spans")
    if source_mode == "adapted":
        if not isinstance(spans, list) or not spans:
            issues.append({"code": "source_spans_missing", "message": f"{prefix}.source_spans 改编项目必填且不得为空。"})
        else:
            for span_index, span in enumerate(spans):
                issues.extend(validate_source_span(span, f"{prefix}.source_spans[{span_index}]"))
    elif spans not in (None, []) and not isinstance(spans, list):
        issues.append({"code": "source_spans_invalid", "message": f"{prefix}.source_spans 应为数组。"})
    elif isinstance(spans, list) and spans:
        issues.append({"code": "original_source_spans_not_empty", "message": f"{prefix} source_mode=original 时 source_spans 应为空。"})

    for key in ("reader_promise", "core_conflict", "turning_point", "payoff"):
        value = entry.get(key)
        if not _nonempty(value):
            issues.append({"code": f"{key}_missing", "message": f"{prefix}.{key} 必填。"})
        elif _is_placeholder(value):
            issues.append({"code": f"{key}_placeholder", "message": f"{prefix}.{key} 是占位/空洞值（如 TBD/待定/单字），必须写出真实内容，否则闭环判据形同虚设。"})
    ending_mode = str(entry.get("ending_mode") or "")
    if ending_mode not in ENDING_MODES:
        issues.append({"code": "ending_mode_invalid", "message": f"{prefix}.ending_mode 须为精确枚举 {sorted(ENDING_MODES)} 之一。"})
    budget = entry.get("budget")
    if not isinstance(budget, Mapping):
        issues.append({"code": "budget_missing", "message": f"{prefix}.budget 必须是软容量意图 object；不得作为硬切话依据。"})
    else:
        unit = str(budget.get("unit") or "")
        if unit not in {"panels", "pages", "rows", "custom"}:
            issues.append({"code": "budget_unit_invalid", "message": f"{prefix}.budget.unit 须为 panels/pages/rows/custom。"})
        if budget.get("hard_min") is not None or budget.get("hard_max") is not None:
            issues.append({"code": "hard_budget_forbidden", "message": f"{prefix}.budget 不得设置 hard_min/hard_max；容量只能是软估算。"})
        soft = budget.get("soft_range")
        target = budget.get("target")
        if soft is None and target is None:
            issues.append({"code": "budget_intent_missing", "message": f"{prefix}.budget 至少写 target 或 soft_range。"})
        if soft is not None:
            if not isinstance(soft, list) or len(soft) != 2:
                issues.append({"code": "budget_soft_range_invalid", "message": f"{prefix}.budget.soft_range 须为 [min,max]。"})
            else:
                try:
                    low, high = float(soft[0]), float(soft[1])
                    if low < 0 or high < low:
                        raise ValueError
                except (TypeError, ValueError):
                    issues.append({"code": "budget_soft_range_invalid", "message": f"{prefix}.budget.soft_range 须为非负递增数值。"})
        if target is not None:
            try:
                if float(target) < 0:
                    raise ValueError
            except (TypeError, ValueError):
                issues.append({"code": "budget_target_invalid", "message": f"{prefix}.budget.target 须为非负数值。"})
    status = str(entry.get("status") or "")
    if status not in CHAPTER_STATUSES:
        issues.append({"code": "chapter_status_invalid", "message": f"{prefix}.status 须为 {sorted(CHAPTER_STATUSES)} 之一。"})
    if chapter_type in LONG_SERIES_TYPES:
        for key in ("entry_state", "exit_state"):
            if not isinstance(entry.get(key), Mapping) or not entry.get(key):
                issues.append({"code": f"{key}_missing", "message": f"{prefix}.{key} 是长线话次必填的非空状态 object。"})
        transitions = entry.get("continuity_delta")
        if not isinstance(transitions, list) or not transitions:
            issues.append({"code": "continuity_delta_missing", "message": f"{prefix}.continuity_delta 是长线话次必填的非空 transition 数组。"})
        else:
            required = ("entity_id", "field", "from", "to", "panel_id", "reason")
            for transition_index, transition in enumerate(transitions):
                if not isinstance(transition, Mapping):
                    issues.append({"code": "continuity_transition_invalid", "message": f"{prefix}.continuity_delta[{transition_index}] 必须是 object。"})
                    continue
                missing = [
                    key for key in required
                    if key not in transition or (key not in {"from", "to"} and not str(transition.get(key) or "").strip())
                ]
                if missing:
                    issues.append({
                        "code": "continuity_transition_fields_missing",
                        "message": f"{prefix}.continuity_delta[{transition_index}] 缺 {','.join(missing)}。",
                    })
    return issues


def validate_blueprint(data: Any) -> list[dict[str, str]]:
    if not isinstance(data, Mapping):
        return [{"code": "split_blueprint_invalid", "message": "split_blueprint 须为 JSON object。"}]
    try:
        version = int(data.get("version") or 1)
    except (TypeError, ValueError):
        return [{"code": "split_blueprint_version_invalid", "message": "split_blueprint.version 必须是整数。"}]
    if version < SCHEMA_VERSION:
        return [{
            "code": "split_blueprint_migration_required",
            "message": "split_blueprint v1 仅兼容读取；请迁移为 v2 chapter contract 后再 strict 放行。",
        }]
    issues: list[dict[str, str]] = []
    if data.get("kind") != "comic_split_blueprint":
        issues.append({"code": "split_blueprint_kind_invalid", "message": "kind 必须为 comic_split_blueprint。"})
    chapters = data.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        return issues + [{"code": "split_blueprint_chapters_missing", "message": "chapters 必须是非空数组。"}]
    seen: set[int] = set()
    previous = 0
    for index, entry in enumerate(chapters):
        issues.extend(validate_chapter_entry(entry, index))
        if not isinstance(entry, Mapping):
            continue
        number = chapter_number(entry.get("chapter"))
        if number is None:
            continue
        if number in seen:
            issues.append({"code": "chapter_duplicate", "message": f"第{number}话重复。"})
        if previous and number != previous + 1:
            issues.append({"code": "chapter_sequence_gap", "message": f"话次必须连续递增：第{previous}话后出现第{number}话。"})
        seen.add(number)
        previous = number
    return issues


def source_units(text: str) -> list[dict[str, Any]]:
    matches = list(SOURCE_UNIT_RE.finditer(text))
    units: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        number = chinese_number_to_int(match.group("number"))
        if number is None:
            continue
        kind = "话" if match.group("kind") == "話" else match.group("kind")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        units.append({
            "number": number,
            "kind": kind,
            "label": f"第{number}{kind}",
            "start": match.start(),
            "end": end,
            "text": text[match.start():end].strip(),
        })
    return units


def select_unit_range(text: str, start: Any, end: Any = None) -> tuple[str, list[str], str | None]:
    start_parsed = parse_numbered_label(start)
    end_parsed = parse_numbered_label(end or start)
    if not start_parsed or not end_parsed:
        return "", [], "source_span_label_invalid"
    if start_parsed[1] != end_parsed[1] or start_parsed[0] > end_parsed[0]:
        return "", [], "source_span_range_invalid"
    selected = [
        unit for unit in source_units(text)
        if unit["kind"] == start_parsed[1] and start_parsed[0] <= unit["number"] <= end_parsed[0]
    ]
    expected = list(range(start_parsed[0], end_parsed[0] + 1))
    actual = [int(unit["number"]) for unit in selected]
    if actual != expected:
        return "", [str(unit["label"]) for unit in selected], "source_span_units_missing"
    return "\n\n".join(str(unit["text"]) for unit in selected), [str(unit["label"]) for unit in selected], None
