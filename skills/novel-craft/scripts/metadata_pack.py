#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build and validate publishing metadata for a novel release."""
from __future__ import annotations

import argparse
import json
import os
from datetime import date
from typing import Any


PACK_KIND = "novel_metadata_pack"
CHECK_KIND = "novel_metadata_pack_check"


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def paths(root: str) -> tuple[str, str, str]:
    out_dir = os.path.join(root, "导出")
    return (
        os.path.join(out_dir, "metadata_pack.json"),
        os.path.join(out_dir, "metadata_pack.md"),
        os.path.join(out_dir, "metadata_pack_check.json"),
    )


def _split(values: list[str] | None) -> list[str]:
    out: list[str] = []
    for value in values or []:
        for part in str(value).replace("，", ",").split(","):
            item = part.strip()
            if item and item not in out:
                out.append(item)
    return out


def build_pack(root: str, args: argparse.Namespace | None = None) -> dict[str, Any]:
    args = args or argparse.Namespace()
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    ai_usage = load_json(os.path.join(root, "合规", "ai_usage.json"), {}) or {}
    compliance = load_json(os.path.join(root, "合规", "compliance_profile.json"), {}) or {}
    return {
        "schema_version": 1,
        "kind": PACK_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "title": getattr(args, "title", "") or meta.get("title") or meta.get("source_title") or os.path.basename(root),
        "subtitle": getattr(args, "subtitle", "") or "",
        "series": getattr(args, "series", "") or meta.get("series") or "",
        "series_number": getattr(args, "series_number", "") or "",
        "author_name": getattr(args, "author_name", "") or meta.get("author") or "",
        "short_blurb": getattr(args, "short_blurb", "") or "",
        "long_description": getattr(args, "long_description", "") or "",
        "keywords": _split(getattr(args, "keyword", [])),
        "categories": _split(getattr(args, "category", [])),
        "age_rating": getattr(args, "age_rating", "") or "",
        "content_warnings": _split(getattr(args, "content_warning", [])),
        "target_platforms": _split(getattr(args, "target_platform", [])) or _split([str(meta.get("target_platform") or "")]),
        "rights_summary": {
            "rights_status": meta.get("rights_status") or "unknown",
            "rights_jurisdiction": meta.get("rights_jurisdiction") or "",
            "distribution_regions": meta.get("distribution_regions") or [],
        },
        "ai_disclosure_summary": {
            "text_mode": ai_usage.get("text_mode") if isinstance(ai_usage, dict) else "",
            "text_authorship_mode": ai_usage.get("text_authorship_mode") if isinstance(ai_usage, dict) else "",
            "publish_target": ai_usage.get("publish_target") if isinstance(ai_usage, dict) else "",
        },
        "compliance_summary": {
            "profile_present": bool(compliance),
            "target_axes": compliance.get("target_axes") if isinstance(compliance, dict) else {},
        },
    }


def check_pack(pack: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def issue(issue_id: str, severity: str, message: str) -> None:
        findings.append({"id": issue_id, "severity": severity, "message": message, "path": "导出/metadata_pack.json"})

    if pack.get("kind") != PACK_KIND:
        issue("METADATA-PACK-MISSING", "blocking", "metadata_pack.json 缺失或 kind 不正确。")
    for field in ("title", "short_blurb"):
        if not str(pack.get(field) or "").strip():
            issue(f"METADATA-{field.upper()}-MISSING", "blocking", f"发布元数据缺 {field}。")
    if len(pack.get("keywords") or []) < 3:
        issue("METADATA-KEYWORDS-WEAK", "warning", "建议至少准备 3 个关键词。")
    if not pack.get("categories"):
        issue("METADATA-CATEGORIES-MISSING", "blocking", "缺少分类/品类，平台上架不可用。")
    if not str(pack.get("age_rating") or "").strip():
        issue("METADATA-AGE-RATING-MISSING", "warning", "缺少年龄/内容适配口径。")
    if not pack.get("target_platforms"):
        issue("METADATA-TARGET-PLATFORM-MISSING", "warning", "缺少目标平台，关键词和分类难以审核。")
    rights = pack.get("rights_summary") if isinstance(pack.get("rights_summary"), dict) else {}
    if rights.get("rights_status") in {"unknown", "", None}:
        issue("METADATA-RIGHTS-UNKNOWN", "blocking", "权利来源未知，不能发布。")
    blockers = [item for item in findings if item["severity"] == "blocking"]
    return {
        "schema_version": 1,
        "kind": CHECK_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": pack.get("project_root"),
        "blocking": len(blockers),
        "warnings": len(findings) - len(blockers),
        "passed": not blockers,
        "findings": findings,
    }


def render_markdown(pack: dict[str, Any], check: dict[str, Any]) -> str:
    lines = [
        "# Metadata Pack",
        "",
        f"- 生成日期：{pack.get('generated_at')}",
        f"- 标题：{pack.get('title')}",
        f"- 副标题：{pack.get('subtitle') or '无'}",
        f"- 作者名：{pack.get('author_name') or '未填写'}",
        f"- 系列：{pack.get('series') or '无'} {pack.get('series_number') or ''}".rstrip(),
        f"- 年龄/内容口径：{pack.get('age_rating') or '未填写'}",
        f"- 平台：{', '.join(pack.get('target_platforms') or []) or '未填写'}",
        "",
        "## 简介",
        "",
        pack.get("short_blurb") or "待填写短简介。",
        "",
        "## 长简介",
        "",
        pack.get("long_description") or "待填写长简介。",
        "",
        "## 分类与关键词",
        "",
        "- 分类：" + (", ".join(pack.get("categories") or []) or "未填写"),
        "- 关键词：" + (", ".join(pack.get("keywords") or []) or "未填写"),
        "- 内容提示：" + (", ".join(pack.get("content_warnings") or []) or "无"),
        "",
        "## 权利与 AI 摘要",
        "",
        f"- 权利：{pack.get('rights_summary')}",
        f"- AI：{pack.get('ai_disclosure_summary')}",
    ]
    if check.get("findings"):
        lines.extend(["", "## Findings", ""])
        for item in check["findings"]:
            lines.append(f"- [{item['severity']}] {item['id']}: {item['message']}")
    return "\n".join(lines).rstrip() + "\n"


def write_pack(root: str, pack: dict[str, Any], check: dict[str, Any]) -> tuple[str, str, str]:
    json_path, md_path, check_path = paths(root)
    write_json(json_path, pack)
    write_json(check_path, check)
    write_text(md_path, render_markdown(pack, check))
    return json_path, md_path, check_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成/检查发布元数据包")
    parser.add_argument("project_root")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--title", default="")
    parser.add_argument("--subtitle", default="")
    parser.add_argument("--series", default="")
    parser.add_argument("--series-number", default="")
    parser.add_argument("--author-name", default="")
    parser.add_argument("--short-blurb", default="")
    parser.add_argument("--long-description", default="")
    parser.add_argument("--keyword", action="append", default=[])
    parser.add_argument("--category", action="append", default=[])
    parser.add_argument("--age-rating", default="")
    parser.add_argument("--content-warning", action="append", default=[])
    parser.add_argument("--target-platform", action="append", default=[])
    args = parser.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    existing = load_json(paths(root)[0], {}) if not any([
        args.title, args.subtitle, args.series, args.series_number, args.author_name,
        args.short_blurb, args.long_description, args.keyword, args.category,
        args.age_rating, args.content_warning, args.target_platform,
    ]) else {}
    pack = existing if isinstance(existing, dict) and existing.get("kind") == PACK_KIND else build_pack(root, args)
    check = check_pack(pack)
    if args.write:
        json_path, md_path, check_path = write_pack(root, pack, check)
        print(f"[ok] metadata pack JSON → {json_path}")
        print(f"[ok] metadata pack MD   → {md_path}")
        print(f"[ok] metadata check     → {check_path}")
    if args.json:
        print(json.dumps({"metadata_pack": pack, "check": check}, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(pack, check))
    return 0 if check["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
