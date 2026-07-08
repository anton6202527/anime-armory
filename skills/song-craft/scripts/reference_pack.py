#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create/check a reference-song boundary pack."""
from __future__ import annotations

import argparse
import json
import os
from datetime import date
from typing import Any


KIND = "song_reference_pack"
CHECK_KIND = "song_reference_pack_check"


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
    out_dir = os.path.join(root, "素材")
    return (
        os.path.join(out_dir, "reference_pack.json"),
        os.path.join(out_dir, "reference_pack.md"),
        os.path.join(out_dir, "reference_pack_check.json"),
    )


def parse_reference(value: str) -> dict[str, Any]:
    """TITLE|ARTIST|URL|USE|DO_NOT_COPY."""
    parts = [p.strip() for p in str(value).split("|")]
    while len(parts) < 5:
        parts.append("")
    return {
        "title": parts[0],
        "artist": parts[1],
        "url_or_source": parts[2],
        "reference_use": parts[3] or "情绪/结构/配器参考",
        "do_not_copy": parts[4] or "旋律、歌词、hook、riff、声纹、编曲标志性细节",
    }


def build_pack(root: str, args: argparse.Namespace) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "references": [parse_reference(item) for item in args.reference],
        "global_boundaries": args.boundary or [
            "只迁移情绪、能量曲线、配器类别、段落功能。",
            "不得复制旋律、歌词、标志性 hook/riff、具体编曲、歌手声纹或商业包装。",
        ],
        "notes": args.notes,
    }


def check_pack(pack: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    refs = pack.get("references") if isinstance(pack.get("references"), list) else []
    for idx, ref in enumerate(refs, 1):
        if not ref.get("title"):
            findings.append({"id": "REF-TITLE", "severity": "blocking", "message": f"reference #{idx} 缺 title。"})
        if not ref.get("reference_use"):
            findings.append({"id": "REF-USE", "severity": "warning", "message": f"reference #{idx} 缺 reference_use。"})
        if not ref.get("do_not_copy"):
            findings.append({"id": "REF-BOUNDARY", "severity": "blocking", "message": f"reference #{idx} 缺 do_not_copy 边界。"})
    if not refs:
        findings.append({"id": "REF-EMPTY", "severity": "warning", "message": "没有参考曲；可继续，但 style prompt 可控性较弱。"})
    blockers = [item for item in findings if item["severity"] == "blocking"]
    return {
        "schema_version": 1,
        "kind": CHECK_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": pack.get("project_root"),
        "passed": not blockers,
        "blocking": len(blockers),
        "warnings": len(findings) - len(blockers),
        "findings": findings,
    }


def render_markdown(pack: dict[str, Any], check: dict[str, Any]) -> str:
    lines = ["# Reference Pack", "", "## Boundaries", ""]
    for item in pack.get("global_boundaries") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## References", ""])
    for ref in pack.get("references") or []:
        lines.append(f"### {ref.get('title') or 'Untitled'} - {ref.get('artist') or 'Unknown'}")
        lines.append(f"- source: {ref.get('url_or_source') or '未填写'}")
        lines.append(f"- use: {ref.get('reference_use')}")
        lines.append(f"- do not copy: {ref.get('do_not_copy')}")
        lines.append("")
    if check.get("findings"):
        lines.extend(["## Findings", ""])
        for item in check["findings"]:
            lines.append(f"- [{item['severity']}] {item['id']}: {item['message']}")
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(root: str, pack: dict[str, Any], check: dict[str, Any]) -> tuple[str, str, str]:
    json_path, md_path, check_path = paths(root)
    write_json(json_path, pack)
    write_json(check_path, check)
    write_text(md_path, render_markdown(pack, check))
    return json_path, md_path, check_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="生成/检查参考曲边界包")
    ap.add_argument("project_root")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--reference", action="append", default=[], help="TITLE|ARTIST|URL|USE|DO_NOT_COPY")
    ap.add_argument("--boundary", action="append", default=[])
    ap.add_argument("--notes", default="")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    existing = load_json(paths(root)[0], {}) if not any([args.reference, args.boundary, args.notes]) else {}
    pack = existing if isinstance(existing, dict) and existing.get("kind") == KIND else build_pack(root, args)
    check = check_pack(pack)
    if args.write:
        json_path, md_path, check_path = write_outputs(root, pack, check)
        print(f"[ok] reference pack JSON → {json_path}")
        print(f"[ok] reference pack MD   → {md_path}")
        print(f"[ok] reference check     → {check_path}")
    if args.json:
        print(json.dumps({"reference_pack": pack, "check": check}, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(pack, check))
    return 0 if check["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
