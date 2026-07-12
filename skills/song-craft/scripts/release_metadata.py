#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build release-level metadata separately from composition/recording rights."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import date, datetime
from typing import Any


KIND = "song_release_metadata"
CHECK_KIND = "song_release_metadata_check"
ARTIST_ROLES = {"main_artist", "featured_artist", "remixer", "composer", "lyricist", "producer"}


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_artist(value: str) -> dict[str, str]:
    parts = [item.strip() for item in str(value).split("|", 1)]
    while len(parts) < 2:
        parts.append("")
    return {"name": parts[0], "role": parts[1] or "main_artist"}


def build(root: str, args: argparse.Namespace) -> dict[str, Any]:
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    rights = load_json(os.path.join(root, "合规", "rights_metadata.json"), {}) or {}
    recording = rights.get("sound_recording") if isinstance(rights.get("sound_recording"), dict) else {}
    artists = [parse_artist(item) for item in args.artist]
    if not artists:
        artists = [{"name": name, "role": "main_artist"} for name in recording.get("performers") or []]
    territories = []
    for value in args.territory or ["worldwide"]:
        territories.extend(item.strip() for item in value.replace("，", ",").split(",") if item.strip())
    title = args.title or rights.get("title") or meta.get("title") or os.path.basename(root)
    return {
        "schema_version": 1,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "release_title": args.release_title or title,
        "track_title": title,
        "version_title": args.version_title or ((recording.get("reference_metadata") or {}).get("version_title") or "Original"),
        "artists": artists,
        "language": args.language or meta.get("language") or "",
        "genre": args.genre or meta.get("genre") or "",
        "explicit": args.explicit,
        "release_date": args.release_date,
        "territories": territories,
        "label": args.label or recording.get("label") or "",
        "copyright": {"p_line": args.p_line, "c_line": args.c_line},
        "identifiers": {"isrc": recording.get("isrc") or "", "upc_ean": args.upc_ean},
        "cover_art_path": args.cover_art,
    }


def check(payload: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    def issue(issue_id: str, severity: str, message: str) -> None:
        findings.append({"id": issue_id, "severity": severity, "message": message, "path": "发行/release_metadata.json"})

    for field in ("release_title", "track_title", "language", "genre", "release_date"):
        if not str(payload.get(field) or "").strip():
            issue(f"RELEASE-{field.upper()}", "blocking", f"缺 {field}。")
    artists = payload.get("artists") if isinstance(payload.get("artists"), list) else []
    if not artists or not any(row.get("role") == "main_artist" and row.get("name") for row in artists):
        issue("RELEASE-MAIN-ARTIST", "blocking", "缺独立字段 main_artist。")
    for row in artists:
        if not row.get("name") or row.get("role") not in ARTIST_ROLES:
            issue("RELEASE-ARTIST-ROLE", "blocking", f"艺人字段或 role 无效：{row}。")
    if payload.get("explicit") not in {"clean", "explicit", "instrumental"}:
        issue("RELEASE-EXPLICIT", "blocking", "explicit 必须明确为 clean/explicit/instrumental。")
    if not payload.get("territories"):
        issue("RELEASE-TERRITORIES", "blocking", "缺发行地域或 worldwide。")
    try:
        release_day = datetime.strptime(str(payload.get("release_date")), "%Y-%m-%d").date()
        lead_days = (release_day - date.today()).days
        if 0 <= lead_days < 7:
            issue("RELEASE-LEAD-TIME", "warning", "发行日期不足 7 天，可能来不及完成分发与编辑推荐提交。")
    except ValueError:
        issue("RELEASE-DATE-FORMAT", "blocking", "release_date 必须为 YYYY-MM-DD。")
    copyright_data = payload.get("copyright") if isinstance(payload.get("copyright"), dict) else {}
    for key in ("p_line", "c_line"):
        if not str(copyright_data.get(key) or "").strip():
            issue(f"RELEASE-{key.upper()}", "blocking", f"缺 {key}。")
    upc = ((payload.get("identifiers") or {}).get("upc_ean") or "").strip()
    if upc and not re.fullmatch(r"\d{12,14}", upc):
        issue("RELEASE-UPC", "warning", "UPC/EAN 通常为 12-14 位数字。")
    blockers = [item for item in findings if item["severity"] == "blocking"]
    return {
        "schema_version": 1,
        "kind": CHECK_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": payload.get("project_root"),
        "source_sha256": canonical_hash(payload),
        "passed": not blockers,
        "blocking": len(blockers),
        "warnings": len(findings) - len(blockers),
        "findings": findings,
    }


def write_outputs(root: str, payload: dict[str, Any], report: dict[str, Any]) -> tuple[str, str, str]:
    out_dir = os.path.join(root, "发行")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "release_metadata.json")
    check_path = os.path.join(out_dir, "release_metadata_check.json")
    md_path = os.path.join(out_dir, "release_metadata.md")
    for path, data in ((json_path, payload), (check_path, report)):
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(path + ".tmp", path)
    lines = ["# Release Metadata", ""]
    for key, value in payload.items():
        if key not in {"project_root", "kind", "schema_version"}:
            lines.append(f"- {key}: {value}")
    if report.get("findings"):
        lines.extend(["", "## Findings", ""])
        lines.extend(f"- [{item['severity']}] {item['id']}: {item['message']}" for item in report["findings"])
    with open(md_path + ".tmp", "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    os.replace(md_path + ".tmp", md_path)
    return json_path, check_path, md_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="生成发行级 track/release metadata")
    ap.add_argument("project_root")
    ap.add_argument("--release-title", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--version-title", default="")
    ap.add_argument("--artist", action="append", default=[], help="NAME|ROLE")
    ap.add_argument("--language", default="")
    ap.add_argument("--genre", default="")
    ap.add_argument("--explicit", default="", choices=("", "clean", "explicit", "instrumental"))
    ap.add_argument("--release-date", default="")
    ap.add_argument("--territory", action="append", default=[])
    ap.add_argument("--label", default="")
    ap.add_argument("--p-line", default="")
    ap.add_argument("--c-line", default="")
    ap.add_argument("--upc-ean", default="")
    ap.add_argument("--cover-art", default="导出/cover.jpg")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    existing_path = os.path.join(root, "发行", "release_metadata.json")
    explicit_input = any([
        args.release_title, args.title, args.version_title, args.artist, args.language, args.genre,
        args.explicit, args.release_date, args.territory, args.label, args.p_line, args.c_line, args.upc_ean,
    ])
    existing = load_json(existing_path, {}) if not explicit_input else {}
    payload = existing if isinstance(existing, dict) and existing.get("kind") == KIND else build(root, args)
    report = check(payload)
    if args.write:
        print("[ok] release metadata -> " + " / ".join(write_outputs(root, payload, report)))
    if args.json or not args.write:
        print(json.dumps({"metadata": payload, "check": report}, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
