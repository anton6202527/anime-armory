#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Source-span, semantic-normalization and panel coverage gate.

V2 consumes the chapter contract's exact source spans, binds source/contract
hashes and keeps every segment.  Language detection remains a legacy-compatible
part of the broader deterministic adaptation ledger.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from chapter_contract import (
    canonical_sha256,
    chapter_contract as get_chapter_contract,
    chapter_number as contract_chapter_number,
    file_sha256,
    normalize_chapter,
    select_unit_range,
)


COMIC_LIB = Path(__file__).resolve().parents[2] / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
from text_metadata import infer_language_metadata


TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".json", ".docx"}
DEFAULT_SOURCE_SKIP_NAMES = {
    "source_manifest.json",
    "_源指纹.json",
    "_source_fingerprint.json",
}
TARGET_LANGUAGE_ALIASES = {
    "zh": "中文",
    "chinese": "中文",
    "cn": "中文",
    "中文": "中文",
    "en": "英文",
    "english": "英文",
    "英文": "英文",
    "zh_en": "中上英下",
    "zh-en": "中上英下",
    "中英": "中上英下",
    "中上英下": "中上英下",
    "en_zh": "英上中下",
    "en-zh": "英上中下",
    "英中": "英上中下",
    "英上中下": "英上中下",
}
SOURCE_LANGUAGE_ALIASES = {
    "auto": "auto",
    "自动": "auto",
    "中文": "现代中文",
    "现代中文": "现代中文",
    "白话": "现代中文",
    "文言": "文言/古汉语",
    "古汉语": "文言/古汉语",
    "classical chinese": "文言/古汉语",
    "en": "英文/拉丁字母外语",
    "english": "英文/拉丁字母外语",
    "英文": "英文/拉丁字母外语",
    "foreign": "外语",
    "外语": "外语",
    "mixed": "混合/未知",
    "混合": "混合/未知",
}
CLASSICAL_MARKERS = (
    "曰",
    "云",
    "之",
    "其",
    "者",
    "也",
    "矣",
    "乎",
    "哉",
    "焉",
    "乃",
    "遂",
    "既",
    "皆",
    "勿",
    "未",
    "弗",
    "吾",
    "汝",
    "尔",
    "兮",
)
MODERN_MARKERS = ("的", "了", "着", "我们", "你们", "他们", "她们", "这个", "那个", "因为", "所以")
ADAPTATION_DECISIONS = {
    "成画面",
    "成对白",
    "成旁白",
    "成拟声",
    "并入",
    "删除",
    "后文带出",
    "保留原文",
    "待定",
}


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# Exact, standalone export artifacts seen in source files downloaded from
# Wikisource/MediaWiki.  Keep this allow-list deliberately narrow: source
# cleanup must never grow into a prose classifier that can silently delete
# legitimate story text.
EXPLICIT_SOURCE_WRAPPER_SIGNATURES = {
    "publicdomainpublicdomainfalsefalse",
}
_IGNORABLE_WRAPPER_CODEPOINTS = {"\u200b", "\u200c", "\u200d", "\ufeff"}


def _wrapper_signature_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return "".join(
        char
        for char in normalized
        if not char.isspace() and char not in _IGNORABLE_WRAPPER_CODEPOINTS
    )


def strip_explicit_source_wrapper_noise(text: str) -> str:
    """Remove only exact standalone source-export wrapper signatures.

    The known artifact may be concatenated in one DOCX paragraph or split
    across adjacent TXT lines.  A line containing any additional prose or
    punctuation is retained, including ordinary discussion of "public
    domain".  Blank lines are allowed inside the exact wrapper sequence.
    """
    lines = str(text or "").splitlines()
    kept: list[str] = []
    index = 0
    while index < len(lines):
        first_key = _wrapper_signature_key(lines[index])
        possible_signatures = {
            signature for signature in EXPLICIT_SOURCE_WRAPPER_SIGNATURES
            if first_key and signature.startswith(first_key)
        }
        match_end: int | None = None
        if possible_signatures:
            combined = ""
            cursor = index
            while cursor < len(lines):
                part = _wrapper_signature_key(lines[cursor])
                if not part:
                    cursor += 1
                    continue
                combined += part
                possible_signatures = {
                    signature for signature in possible_signatures
                    if signature.startswith(combined)
                }
                if not possible_signatures:
                    break
                cursor += 1
                if combined in EXPLICIT_SOURCE_WRAPPER_SIGNATURES:
                    match_end = cursor
                    break
        if match_end is not None:
            index = match_end
            continue
        kept.append(lines[index])
        index += 1
    return "\n".join(kept)


def read_docx_text(path: Path) -> str:
    """Extract readable paragraphs from DOCX with the standard library.

    comic accepts a source DOCX at initialization, so the semantic gate must
    not silently ignore that same source type.  This intentionally reads only
    the main document story; headers/comments are not adaptation source text.
    """
    try:
        with zipfile.ZipFile(path) as archive:
            document_xml = archive.read("word/document.xml")
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        raise ValueError(f"cannot read DOCX source {path}: {exc}") from exc
    try:
        root = ET.fromstring(document_xml)
    except ET.ParseError as exc:
        raise ValueError(f"invalid word/document.xml in {path}: {exc}") from exc

    q = lambda name: f"{{{WORD_NS}}}{name}"
    paragraphs: list[str] = []
    for paragraph in root.iter(q("p")):
        pieces: list[str] = []
        for node in paragraph.iter():
            if node.tag == q("t") and node.text:
                pieces.append(node.text)
            elif node.tag == q("tab"):
                pieces.append("\t")
            elif node.tag in {q("br"), q("cr")}:
                pieces.append("\n")
        text = "".join(pieces).strip()
        if text:
            paragraphs.append(text)
    return strip_explicit_source_wrapper_noise("\n\n".join(paragraphs))


def read_text(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        return read_docx_text(path)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")
    return strip_explicit_source_wrapper_noise(text)


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def read_setting(root: Path, key: str, default: str = "") -> str:
    path = root / "_设置.md"
    if not path.is_file():
        return default
    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*[:：]\s*(.+?)\s*$")
    for line in read_text(path).splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return default


def normalize_target_language(raw: str | None) -> str:
    value = str(raw or "").strip()
    if not value:
        return "中文"
    return TARGET_LANGUAGE_ALIASES.get(re.sub(r"\s+", " ", value).lower(), value)


def normalize_source_language(raw: str | None) -> str:
    value = str(raw or "auto").strip()
    if not value:
        return "auto"
    return SOURCE_LANGUAGE_ALIASES.get(value.lower(), SOURCE_LANGUAGE_ALIASES.get(value, value))


def candidate_source_paths(root: Path, raw_paths: list[str]) -> list[Path]:
    if raw_paths:
        candidates: list[Path] = []
        for item in raw_paths:
            raw = Path(item).expanduser()
            if raw.is_absolute():
                candidates.append(raw)
            else:
                root_candidate = root / raw
                candidates.append(root_candidate if root_candidate.exists() else raw.resolve())
        return sorted(set(candidates))
    source_dir = root / "源本"
    if not source_dir.is_dir():
        return []
    return sorted(
        path
        for path in source_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in TEXT_SUFFIXES
        and path.name not in DEFAULT_SOURCE_SKIP_NAMES
    )


def chinese_number_to_int(value: str) -> int | None:
    return contract_chapter_number(f"第{value}话")


def chapter_number(value: str) -> int | None:
    return contract_chapter_number(value)


def strip_source_provenance(text: str) -> str:
    lines = []
    in_provenance = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# === 抓取来源信息"):
            in_provenance = True
            continue
        if in_provenance:
            if stripped.startswith("# ==="):
                in_provenance = False
            continue
        if stripped.startswith("# source_url:") or stripped.startswith("# fetched:") or stripped.startswith("# chapters:"):
            continue
        if stripped.startswith("# chars:") or stripped.startswith("# copyright:"):
            continue
        lines.append(line)
    cleaned = strip_explicit_source_wrapper_noise("\n".join(lines))
    cleaned = re.sub(r"\[编辑\]", "", cleaned)
    return cleaned.strip()


def slice_source_for_chapter(text: str, chapter: str) -> str:
    number = chapter_number(chapter)
    cleaned = strip_source_provenance(text)
    if number is None:
        return cleaned
    patterns = [
        rf"(?m)^第\s*{number}\s*章\b",
        rf"(?m)^第\s*{number}\s*[话話]\b",
    ]
    start_match = None
    for pattern in patterns:
        start_match = re.search(pattern, cleaned)
        if start_match:
            break
    if not start_match:
        return cleaned
    next_patterns = [
        rf"(?m)^第\s*{number + 1}\s*章\b",
        rf"(?m)^第\s*{number + 1}\s*[话話]\b",
    ]
    next_start = len(cleaned)
    for pattern in next_patterns:
        match = re.search(pattern, cleaned[start_match.end() :])
        if match:
            next_start = start_match.end() + match.start()
            break
    return cleaned[start_match.start() : next_start].strip()


def load_source_texts(root: Path, paths: list[Path]) -> tuple[list[dict[str, Any]], str]:
    records: list[dict[str, Any]] = []
    chunks: list[str] = []
    for path in paths:
        if not path.is_file():
            records.append({"path": rel(root, path), "status": "missing"})
            continue
        try:
            text = read_text(path)
        except ValueError as exc:
            records.append({"path": rel(root, path), "status": "invalid", "reason": str(exc)})
            continue
        records.append(
            {
                "path": rel(root, path),
                "status": "read",
                "chars": len(text),
                "format": path.suffix.lower().lstrip(".") or "text",
                "sha256": file_sha256(path),
            }
        )
        chunks.append(text)
    return records, "\n\n".join(chunks)


def _safe_source_path(root: Path, raw: str) -> tuple[Path, str | None]:
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return candidate, "source_path_outside_project"
    return candidate, None


def load_contract_source_spans(
    root: Path, contract: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load exactly the v2 chapter contract's declared source spans."""
    file_records: dict[str, dict[str, Any]] = {}
    selections: list[dict[str, Any]] = []
    for index, span in enumerate(contract.get("source_spans") or [], 1):
        span_id = str(span.get("span_id") or f"SPAN_{index:03d}") if isinstance(span, dict) else f"SPAN_{index:03d}"
        if not isinstance(span, dict):
            selections.append({"span_id": span_id, "status": "invalid", "reason": "source_span_invalid"})
            continue
        raw_path = str(span.get("source_path") or "").strip()
        path, path_error = _safe_source_path(root, raw_path)
        selection: dict[str, Any] = {
            "span_id": span_id,
            "source_path": raw_path,
            "requested": {"start": span.get("start"), "end": span.get("end"), "whole_file": span.get("whole_file") is True},
        }
        if path_error:
            selection.update({"status": "invalid", "reason": path_error})
            selections.append(selection)
            continue
        if not path.is_file():
            file_records[raw_path] = {"path": raw_path, "status": "missing"}
            selection.update({"status": "missing", "reason": "source_file_missing"})
            selections.append(selection)
            continue
        try:
            text = read_text(path)
        except (OSError, ValueError) as exc:
            file_records[raw_path] = {"path": raw_path, "status": "invalid", "reason": str(exc)}
            selection.update({"status": "invalid", "reason": "source_file_invalid"})
            selections.append(selection)
            continue
        file_records[raw_path] = {
            "path": raw_path,
            "status": "read",
            "chars": len(text),
            "format": path.suffix.lower().lstrip(".") or "text",
            "sha256": file_sha256(path),
        }
        cleaned = strip_source_provenance(text)
        if span.get("whole_file") is True:
            selected_text, unit_refs, select_error = cleaned, ["whole_file"], None
        else:
            selected_text, unit_refs, select_error = select_unit_range(cleaned, span.get("start"), span.get("end"))
        if select_error:
            selection.update({"status": "invalid", "reason": select_error, "source_unit_refs": unit_refs})
        else:
            selection.update({
                "status": "read",
                "chars": len(selected_text),
                "source_unit_refs": unit_refs,
                "text": selected_text,
            })
        selections.append(selection)
    return list(file_records.values()), selections


def char_counts(text: str) -> dict[str, int]:
    counts = {"cjk": 0, "latin": 0, "rtl": 0, "thai_like": 0, "other_letters": 0}
    for ch in text:
        if ch.isspace() or unicodedata.category(ch).startswith("P"):
            continue
        code = ord(ch)
        if 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF or 0x20000 <= code <= 0x2A6DF:
            counts["cjk"] += 1
        elif ("A" <= ch <= "Z") or ("a" <= ch <= "z"):
            counts["latin"] += 1
        elif 0x0590 <= code <= 0x08FF:
            counts["rtl"] += 1
        elif 0x0E00 <= code <= 0x0E7F or 0x1780 <= code <= 0x17FF:
            counts["thai_like"] += 1
        elif unicodedata.category(ch).startswith("L"):
            counts["other_letters"] += 1
    return counts


def guess_source_language(text: str) -> tuple[str, list[str]]:
    sample = text[:80000]
    counts = char_counts(sample)
    total = sum(counts.values())
    if total == 0:
        return "无源本", ["no_readable_source_text"]
    reasons: list[str] = []
    cjk_ratio = counts["cjk"] / total
    latin_ratio = counts["latin"] / total
    rtl_ratio = counts["rtl"] / total
    thai_ratio = counts["thai_like"] / total
    if cjk_ratio >= 0.45:
        marker_hits = sum(sample.count(token) for token in CLASSICAL_MARKERS)
        modern_hits = sum(sample.count(token) for token in MODERN_MARKERS)
        marker_density = marker_hits / max(counts["cjk"], 1)
        if marker_density >= 0.055 and marker_hits >= max(8, modern_hits):
            reasons.append("classical_chinese_marker_density")
            return "文言/古汉语", reasons
        reasons.append("cjk_modern_or_mixed")
        return "现代中文", reasons
    if latin_ratio >= 0.45:
        reasons.append("latin_script_majority")
        return "英文/拉丁字母外语", reasons
    if rtl_ratio >= 0.20:
        reasons.append("rtl_script_detected")
        return "外语(RTL)", reasons
    if thai_ratio >= 0.20:
        reasons.append("thai_or_khmer_like_script_detected")
        return "外语(需分词文字)", reasons
    reasons.append("mixed_or_unknown_script")
    return "混合/未知", reasons


def requires_normalization(source_language: str, source_records: list[dict[str, Any]], force: bool) -> bool:
    if force:
        return True
    if not any(item.get("status") == "read" and int(item.get("chars") or 0) > 0 for item in source_records):
        return False
    return source_language not in {"现代中文", "无源本"}


def split_segments(text: str, max_segments: int | None = None) -> list[str]:
    """Split all source text without truncating content.

    ``max_segments`` remains accepted for CLI/API compatibility but no longer
    caps the ledger.  A cap silently discarded source after segment 12.
    """
    raw_parts = re.split(r"\n\s*\n+|(?<=[。！？!?])\s+", text.strip())
    parts: list[str] = []
    for raw in raw_parts:
        chunk = re.sub(r"\s+", " ", raw).strip()
        if not chunk:
            continue
        while len(chunk) > 1200:
            parts.append(chunk[:1200])
            chunk = chunk[1200:]
        if chunk:
            parts.append(chunk)
    return parts


def _segments_from_selections(selections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for selection in selections:
        if selection.get("status") != "read":
            continue
        for text in split_segments(str(selection.get("text") or "")):
            segments.append({
                "segment_id": f"S{len(segments) + 1:03d}",
                "source_path": selection.get("source_path"),
                "source_span_id": selection.get("span_id"),
                "source_unit_refs": selection.get("source_unit_refs") or [],
                "source_excerpt": text,
                "meaning_zh": "",
                "text_target": "",
                "ambiguities": [],
                "adaptation_decision": "待定",
                "adaptation_note": "",
            })
    return segments


def scaffold_report(
    root: Path,
    chapter: str,
    source_records: list[dict[str, Any]],
    source_text: str,
    source_language: str,
    detection_reasons: list[str],
    target_text_language: str,
    force_normalization: bool,
    max_segments: int,
    chapter_contract_data: dict[str, Any] | None = None,
    source_selections: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    must_normalize = requires_normalization(source_language, source_records, force_normalization)
    contract_enforced = isinstance(chapter_contract_data, dict)
    source_mode = str((chapter_contract_data or {}).get("source_mode") or ("adapted" if source_text else "original"))
    must_trace = contract_enforced and source_mode == "adapted"
    normalized_source_text = slice_source_for_chapter(source_text, chapter)
    if source_selections is not None:
        segments = _segments_from_selections(source_selections) if (must_normalize or must_trace) else []
        selected_chars = sum(int(item.get("chars") or 0) for item in source_selections if item.get("status") == "read")
    else:
        segment_texts = split_segments(normalized_source_text, max_segments) if must_normalize else []
        segments = [
            {
                "segment_id": f"S{idx:03d}",
                "source_excerpt": text,
                "meaning_zh": "",
                "text_target": "",
                "ambiguities": [],
                "adaptation_decision": "待定",
                "adaptation_note": "",
            }
            for idx, text in enumerate(segment_texts, 1)
        ]
        selected_chars = len(normalized_source_text)
    return {
        "schema_version": 2,
        "kind": "comic_source_semantics",
        "chapter": chapter,
        "status": "needs_normalization" if must_normalize else ("needs_adaptation_decisions" if must_trace else "pass"),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "chapter_contract": {
            "enforced": contract_enforced,
            "sha256": canonical_sha256(chapter_contract_data) if contract_enforced else None,
            "source_mode": source_mode,
            "format_profile": (chapter_contract_data or {}).get("format_profile"),
        },
        "source_language": source_language,
        "target_text_language": target_text_language,
        "target_text_metadata": infer_language_metadata("", target_text_language),
        "requires_normalization": must_normalize,
        "normalization_reason": detection_reasons,
        "source_files": source_records,
        "source_slice": {
            "chapter": chapter,
            "chars": selected_chars,
            "strategy": "split_blueprint.source_spans" if source_selections is not None else "legacy_chapter_heading_or_cleaned_source",
            "selections": [
                {key: value for key, value in item.items() if key != "text"}
                for item in (source_selections or [])
            ],
        },
        "glossary_reviewed": False if must_normalize else True,
        "ambiguity_reviewed": False if must_normalize else True,
        "proper_noun_glossary": [],
        "segments": segments,
        "segment_policy": {
            "coverage": "full",
            "max_segments_legacy_ignored": max_segments,
            "note": "不截断源文本；长段按 1200 字符拆块，所有源段都必须有改编决策。",
        },
        "adaptation_ledger": [],
        "panel_script_contract": {
            "required_panel_fields_when_normalized": [
                "source_excerpt",
                "meaning_zh",
                "text_target",
                "adaptation_note",
                "source_segment_refs",
            ],
            "panel_script_path": rel(root, root / "脚本" / chapter / "panel_script.json"),
        },
    }


def load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_panel_coverage(report: dict[str, Any], panel_script: dict[str, Any] | None) -> tuple[dict[str, Any], list[str]]:
    segments = [item for item in report.get("segments") or [] if isinstance(item, dict)]
    known = {str(item.get("segment_id") or "") for item in segments}
    required = {
        str(item.get("segment_id") or "")
        for item in segments
        if str(item.get("adaptation_decision") or "") not in {"删除", "后文带出"}
    }
    if panel_script is None:
        return ({"status": "pending_panel_script", "required_segment_ids": sorted(required)}, [])
    issues: list[str] = []
    panels = panel_script.get("panels") if isinstance(panel_script, dict) else None
    if not isinstance(panels, list):
        return ({"status": "block", "required_segment_ids": sorted(required), "used_segment_ids": []},
                ["panel_script.panels must be an array for source coverage"])
    used: set[str] = set()
    for index, panel in enumerate(panels, 1):
        if not isinstance(panel, dict):
            continue
        refs = panel.get("source_segment_refs")
        if not isinstance(refs, list) or not refs:
            if panel.get("adaptation_origin") == "original_bridge" and str(panel.get("adaptation_note") or "").strip():
                continue
            issues.append(
                f"panel {panel.get('panel_id') or index} source_segment_refs is required; "
                "an added bridge must declare adaptation_origin=original_bridge plus adaptation_note"
            )
            continue
        for ref in refs:
            ref_id = str(ref or "")
            if ref_id not in known:
                issues.append(f"panel {panel.get('panel_id') or index} references unknown source segment {ref_id}")
            else:
                used.add(ref_id)
    missing = sorted(required - used)
    if missing:
        issues.append("source segments lack panel coverage: " + ", ".join(missing))
    coverage = {
        "status": "pass" if not issues else "block",
        "required_segment_ids": sorted(required),
        "used_segment_ids": sorted(used),
        "missing_segment_ids": missing,
    }
    return coverage, issues


def validate_report(
    report: dict[str, Any], panel_script: dict[str, Any] | None = None
) -> tuple[str, list[str]]:
    issues: list[str] = []
    if report.get("kind") != "comic_source_semantics":
        issues.append("kind must be comic_source_semantics")
    if not str(report.get("source_language") or "").strip():
        issues.append("source_language is required")
    if not str(report.get("target_text_language") or "").strip():
        issues.append("target_text_language is required")
    for record in report.get("source_files") or []:
        if isinstance(record, dict) and record.get("status") in {"missing", "invalid"}:
            issues.append(f"source file {record.get('path')} is {record.get('status')}")
    for reason in report.get("stale_reasons") or []:
        issues.append(str(reason))
    contract_info = report.get("chapter_contract") if isinstance(report.get("chapter_contract"), dict) else {}
    contract_enforced = contract_info.get("enforced") is True
    adapted = contract_info.get("source_mode") == "adapted"
    selections = (report.get("source_slice") or {}).get("selections") if isinstance(report.get("source_slice"), dict) else []
    if contract_enforced and adapted:
        if not isinstance(selections, list) or not selections:
            issues.append("chapter contract source_spans produced no source selections")
        for selection in selections or []:
            if isinstance(selection, dict) and selection.get("status") != "read":
                issues.append(f"source span {selection.get('span_id')} is {selection.get('status')}: {selection.get('reason')}")

    if report.get("requires_normalization") and report.get("glossary_reviewed") is not True:
        issues.append("glossary_reviewed must be true after proper noun review")
    if report.get("requires_normalization") and report.get("ambiguity_reviewed") is not True:
        issues.append("ambiguity_reviewed must be true after ambiguity review")
    segments = report.get("segments")
    if (report.get("requires_normalization") or (contract_enforced and adapted)) and (not isinstance(segments, list) or not segments):
        issues.append("segments must contain normalized source chunks")
        return "block", issues
    if segments is not None and not isinstance(segments, list):
        issues.append("segments must be an array")
        segments = []
    for idx, segment in enumerate(segments or [], 1):
        if not isinstance(segment, dict):
            issues.append(f"segments[{idx - 1}] must be an object")
            continue
        prefix = str(segment.get("segment_id") or f"S{idx:03d}")
        required_fields = ["source_excerpt", "adaptation_note"]
        if report.get("requires_normalization"):
            required_fields.extend(["meaning_zh", "text_target"])
        for key in required_fields:
            if not str(segment.get(key) or "").strip():
                issues.append(f"{prefix}.{key} is required")
        decision = str(segment.get("adaptation_decision") or "").strip()
        if decision not in ADAPTATION_DECISIONS or decision == "待定":
            issues.append(f"{prefix}.adaptation_decision must be finalized")
    if contract_enforced and adapted:
        coverage, coverage_issues = validate_panel_coverage(report, panel_script)
        report["panel_coverage"] = coverage
        issues.extend(coverage_issues)
    return ("pass" if not issues else "block"), issues


def refresh_staleness(root: Path, report: dict[str, Any], contract: dict[str, Any] | None) -> list[str]:
    reasons: list[str] = []
    stored_contract = report.get("chapter_contract") if isinstance(report.get("chapter_contract"), dict) else {}
    if contract is not None and stored_contract.get("enforced") is not True:
        reasons.append("v2 chapter contract now exists but this report was built with legacy slicing; rerun with --force")
    if stored_contract.get("enforced") is True:
        if contract is None:
            reasons.append("chapter contract missing/invalid since source_semantics was created")
        elif stored_contract.get("sha256") != canonical_sha256(contract):
            reasons.append("chapter contract SHA changed; rerun with --force and review the new source slice")
    for record in report.get("source_files") or []:
        if not isinstance(record, dict) or record.get("status") != "read":
            continue
        raw = str(record.get("path") or "")
        path = Path(raw)
        if not path.is_absolute():
            path = root / path
        if not path.is_file():
            reasons.append(f"source file missing since report creation: {raw}")
        elif record.get("sha256") != file_sha256(path):
            reasons.append(f"source SHA changed: {raw}; rerun with --force and re-review decisions")
    return reasons


def render_markdown(report: dict[str, Any], issues: list[str]) -> str:
    lines = [
        f"# 源语义归一化 — {report.get('chapter', '')}",
        "",
        f"- 状态: {report.get('status')}",
        f"- 源语言: {report.get('source_language')}",
        f"- 目标嵌字语言: {report.get('target_text_language')}",
        f"- 需要归一化: {'是' if report.get('requires_normalization') else '否'}",
        f"- 专名表已审: {'是' if report.get('glossary_reviewed') else '否'}",
        f"- 歧义已审: {'是' if report.get('ambiguity_reviewed') else '否'}",
        "",
    ]
    if issues:
        lines += ["## 阻断项", ""]
        lines += [f"- {item}" for item in issues]
        lines.append("")
    if report.get("proper_noun_glossary"):
        lines += ["## 专名表", ""]
        for item in report.get("proper_noun_glossary") or []:
            lines.append(
                f"- {item.get('source_term', '')} -> {item.get('canonical_zh', '')}"
                f" / {item.get('target_text', '')}"
            )
        lines.append("")
    if report.get("segments"):
        lines += ["## 分段释义与改编账", ""]
        for segment in report.get("segments") or []:
            lines += [
                f"### {segment.get('segment_id')}",
                "",
                f"- 原文摘录: {segment.get('source_excerpt', '')}",
                f"- 白话/中文释义: {segment.get('meaning_zh', '')}",
                f"- 目标嵌字/对白: {segment.get('text_target', '')}",
                f"- 改编取舍: {segment.get('adaptation_decision', '')}",
                f"- 改编说明: {segment.get('adaptation_note', '')}",
                "",
            ]
    return "\n".join(lines).rstrip() + "\n"


def write_report(path: Path, report: dict[str, Any], issues: list[str], write_md: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if write_md:
        path.with_suffix(".md").write_text(render_markdown(report, issues), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="漫画源语义归一化 gate")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--source", action="append", default=[], help="源本文件或目录内文件；可重复。默认扫描 源本/")
    parser.add_argument("--source-language", default="auto")
    parser.add_argument("--target-text-language", default=None)
    parser.add_argument("--force-normalization", action="store_true", help="现代中文也强制建立释义/取舍账")
    parser.add_argument("--force", action="store_true", help="覆盖已有 source_semantics.json")
    parser.add_argument("--max-segments", type=int, default=12,
                        help="legacy compatibility only; v2 never truncates source coverage")
    parser.add_argument("--json", default=None, help="输出路径，默认 脚本/第N话/source_semantics.json")
    parser.add_argument("--no-md", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    args.chapter = normalize_chapter(args.chapter)
    out_path = Path(args.json).expanduser().resolve() if args.json else root / "脚本" / args.chapter / "source_semantics.json"
    target_language = normalize_target_language(args.target_text_language or read_setting(root, "文字语言", "中文"))
    contract, contract_error = get_chapter_contract(root, args.chapter)

    if out_path.is_file() and not args.force:
        report = load_report(out_path)
        report["stale_reasons"] = refresh_staleness(root, report, contract)
    else:
        source_selections: list[dict[str, Any]] | None = None
        if contract is not None and contract.get("source_mode") == "adapted":
            source_records, source_selections = load_contract_source_spans(root, contract)
            source_text = "\n\n".join(
                str(item.get("text") or "") for item in source_selections if item.get("status") == "read"
            )
        elif contract is not None and contract.get("source_mode") == "original":
            source_records, source_text = [], ""
            source_selections = []
        else:
            paths = candidate_source_paths(root, args.source)
            if len(paths) == 1 and paths[0].is_dir():
                paths = sorted(path for path in paths[0].rglob("*") if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES)
            source_records, source_text = load_source_texts(root, paths)
        source_language = normalize_source_language(args.source_language)
        if source_language == "auto":
            source_language, detection_reasons = guess_source_language(source_text)
        else:
            detection_reasons = ["manual_source_language"]
        report = scaffold_report(
            root,
            args.chapter,
            source_records,
            source_text,
            source_language,
            detection_reasons,
            target_language,
            args.force_normalization,
            max(1, args.max_segments),
            chapter_contract_data=contract,
            source_selections=source_selections,
        )
        report["chapter_contract"]["load_status"] = "loaded" if contract is not None else contract_error

    panel_path = root / "脚本" / args.chapter / "panel_script.json"
    panel_script: dict[str, Any] | None = None
    if panel_path.is_file():
        try:
            loaded_panel = json.loads(panel_path.read_text(encoding="utf-8"))
            if isinstance(loaded_panel, dict):
                panel_script = loaded_panel
        except (OSError, json.JSONDecodeError):
            # Deterministic invalid input: coverage validation will block.
            panel_script = {}
    verdict, issues = validate_report(report, panel_script)
    report["status"] = verdict
    report["checked_at"] = datetime.now().isoformat(timespec="seconds")
    report["issues"] = issues
    write_report(out_path, report, issues, not args.no_md)
    print(json.dumps({"verdict": verdict, "issues": issues, "path": str(out_path)}, ensure_ascii=False))
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
