#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Source semantic normalization gate for comic-script.

The gate is deterministic: it detects whether a source looks like foreign text
or classical/literary Chinese, scaffolds the required semantic ledger, and
fails until an AI/human fills the meaning and adaptation fields.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


COMIC_LIB = Path(__file__).resolve().parents[2] / "comic" / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
from text_metadata import infer_language_metadata


TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".json"}
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


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


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
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        return int(raw)
    digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    units = {"十": 10, "百": 100}
    total = 0
    current = 0
    for ch in raw:
        if ch in digits:
            current = digits[ch]
        elif ch in units:
            unit = units[ch]
            total += (current or 1) * unit
            current = 0
        else:
            return None
    return total + current if total or current else None


def chapter_number(value: str) -> int | None:
    match = re.search(r"第\s*([0-9]+|[零〇一二两三四五六七八九十百]+)\s*[话話章节回]", str(value or ""))
    if not match:
        return None
    return chinese_number_to_int(match.group(1))


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
    cleaned = "\n".join(lines)
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
        text = read_text(path)
        records.append({"path": rel(root, path), "status": "read", "chars": len(text)})
        chunks.append(text)
    return records, "\n\n".join(chunks)


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


def split_segments(text: str, max_segments: int) -> list[str]:
    raw_parts = re.split(r"\n\s*\n+|(?<=[。！？!?])\s+", text.strip())
    parts = []
    for raw in raw_parts:
        chunk = re.sub(r"\s+", " ", raw).strip()
        if not chunk:
            continue
        parts.append(chunk[:1200])
        if len(parts) >= max_segments:
            break
    return parts


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
) -> dict[str, Any]:
    must_normalize = requires_normalization(source_language, source_records, force_normalization)
    normalized_source_text = slice_source_for_chapter(source_text, chapter)
    segment_texts = split_segments(normalized_source_text, max_segments) if must_normalize else []
    return {
        "schema_version": 1,
        "kind": "comic_source_semantics",
        "chapter": chapter,
        "status": "needs_normalization" if must_normalize else "pass",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_language": source_language,
        "target_text_language": target_text_language,
        "target_text_metadata": infer_language_metadata("", target_text_language),
        "requires_normalization": must_normalize,
        "normalization_reason": detection_reasons,
        "source_files": source_records,
        "source_slice": {
            "chapter": chapter,
            "chars": len(normalized_source_text),
            "strategy": "chapter_heading_or_cleaned_source",
        },
        "glossary_reviewed": False if must_normalize else True,
        "ambiguity_reviewed": False if must_normalize else True,
        "proper_noun_glossary": [],
        "segments": [
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
        ],
        "adaptation_ledger": [],
        "panel_script_contract": {
            "required_panel_fields_when_normalized": [
                "source_excerpt",
                "meaning_zh",
                "text_target",
                "adaptation_note",
            ],
            "panel_script_path": rel(root, root / "脚本" / chapter / "panel_script.json"),
        },
    }


def load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_report(report: dict[str, Any]) -> tuple[str, list[str]]:
    issues: list[str] = []
    if report.get("kind") != "comic_source_semantics":
        issues.append("kind must be comic_source_semantics")
    if not str(report.get("source_language") or "").strip():
        issues.append("source_language is required")
    if not str(report.get("target_text_language") or "").strip():
        issues.append("target_text_language is required")
    if not report.get("requires_normalization"):
        return ("pass" if not issues else "block"), issues

    if report.get("glossary_reviewed") is not True:
        issues.append("glossary_reviewed must be true after proper noun review")
    if report.get("ambiguity_reviewed") is not True:
        issues.append("ambiguity_reviewed must be true after ambiguity review")
    segments = report.get("segments")
    if not isinstance(segments, list) or not segments:
        issues.append("segments must contain normalized source chunks")
        return "block", issues
    for idx, segment in enumerate(segments, 1):
        prefix = str(segment.get("segment_id") or f"S{idx:03d}")
        for key in ("source_excerpt", "meaning_zh", "text_target", "adaptation_note"):
            if not str(segment.get(key) or "").strip():
                issues.append(f"{prefix}.{key} is required")
        decision = str(segment.get("adaptation_decision") or "").strip()
        if decision not in ADAPTATION_DECISIONS or decision == "待定":
            issues.append(f"{prefix}.adaptation_decision must be finalized")
    return ("pass" if not issues else "block"), issues


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
    parser.add_argument("--max-segments", type=int, default=12)
    parser.add_argument("--json", default=None, help="输出路径，默认 脚本/第N话/source_semantics.json")
    parser.add_argument("--no-md", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    out_path = Path(args.json).expanduser().resolve() if args.json else root / "脚本" / args.chapter / "source_semantics.json"
    target_language = normalize_target_language(args.target_text_language or read_setting(root, "文字语言", "中文"))

    if out_path.is_file() and not args.force:
        report = load_report(out_path)
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
        )

    verdict, issues = validate_report(report)
    report["status"] = verdict
    report["checked_at"] = datetime.now().isoformat(timespec="seconds")
    report["issues"] = issues
    write_report(out_path, report, issues, not args.no_md)
    print(json.dumps({"verdict": verdict, "issues": issues, "path": str(out_path)}, ensure_ascii=False))
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
