#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a release-facing delivery pack for a song project."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date
from typing import Any


KIND = "song_release_pack"


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


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def record(root: str, relpath: str) -> dict[str, Any]:
    path = os.path.join(root, relpath)
    out = {"path": relpath, "exists": os.path.exists(path)}
    if os.path.isfile(path):
        out.update({
            "sha256": sha256_file(path),
            "size_bytes": os.path.getsize(path),
        })
    return out


def build_pack(root: str, release_name: str, profile: str) -> dict[str, Any]:
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    rights = load_json(os.path.join(root, "合规", "rights_metadata.json"), {}) or {}
    rights_check = load_json(os.path.join(root, "合规", "rights_metadata_check.json"), {}) or {}
    master = load_json(os.path.join(root, "混音", "master_check.json"), {}) or {}
    ai_usage = load_json(os.path.join(root, "合规", "ai_usage.json"), {}) or {}
    take_manifest = load_json(os.path.join(root, "歌", "takes_manifest.json"), {}) or {}
    evidence = {
        "audio_master": record(root, "歌/song.wav"),
        "lyrics": record(root, "词/lyrics.md"),
        "take_manifest": record(root, "歌/takes_manifest.json"),
        "take_review": record(root, "歌/take_review.json"),
        "master_check": record(root, "混音/master_check.json"),
        "rights_metadata": record(root, "合规/rights_metadata.json"),
        "split_sheet": record(root, "合规/split_sheet.md"),
        "ai_usage": record(root, "合规/ai_usage.json"),
        "cover_art": record(root, "导出/cover.jpg"),
    }
    readiness = release_readiness(profile, evidence, rights, rights_check, master, ai_usage, take_manifest)
    return {
        "schema_version": 1,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "release_name": release_name,
        "release_profile": profile,
        "title": meta.get("title") or os.path.basename(root),
        "artist": (rights.get("sound_recording") or {}).get("performers") or [meta.get("performer") or ""],
        "release_ready": not readiness["blockers"],
        "readiness": readiness,
        "metadata": {
            "rights_status": rights.get("rights_status") or meta.get("rights_status") or "unknown",
            "isrc": ((rights.get("sound_recording") or {}).get("isrc") or ""),
            "iswc": ((rights.get("composition_rights") or {}).get("iswc") or ""),
            "selected_take": take_manifest.get("selected_take"),
            "ai_audio_mode": ai_usage.get("audio_mode"),
            "ai_lyrics_mode": ai_usage.get("lyrics_mode"),
        },
        "evidence": evidence,
    }


def release_readiness(
    profile: str,
    evidence: dict[str, dict[str, Any]],
    rights: dict[str, Any],
    rights_check: dict[str, Any],
    master: dict[str, Any],
    ai_usage: dict[str, Any],
    take_manifest: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    def issue(target: list[dict[str, str]], issue_id: str, message: str) -> None:
        target.append({"id": issue_id, "message": message})

    for key in ("audio_master", "lyrics", "take_manifest", "master_check", "rights_metadata", "ai_usage"):
        if not evidence.get(key, {}).get("exists"):
            issue(blockers, f"MISSING-{key.upper()}", f"缺少 {key} 证据。")
    if take_manifest and not take_manifest.get("selected_take"):
        issue(blockers, "TAKE-NOT-SELECTED", "takes_manifest 缺 selected_take。")
    if rights_check and rights_check.get("passed") is False:
        issue(blockers, "RIGHTS-CHECK", "rights metadata check 未通过。")
    elif rights and rights.get("rights_status") in {"unknown", "", None}:
        issue(blockers, "RIGHTS-UNKNOWN", "权利状态未知。")
    if master and master.get("passed") is False:
        issue(blockers, "MASTER-CHECK", "master_check 未通过。")
    if ai_usage and not ai_usage.get("human_contribution"):
        issue(warnings, "AI-HUMAN-CONTRIBUTION", "AI 使用披露缺 human_contribution。")
    if profile in {"distribution", "streaming"}:
        if not ((rights.get("sound_recording") or {}).get("isrc")):
            issue(warnings, "ISRC-MISSING", "正式发行建议补 ISRC。")
        if not evidence.get("cover_art", {}).get("exists"):
            issue(warnings, "COVER-ART-MISSING", "缺导出/cover.jpg；发行平台通常需要封面。")
    return {
        "profile": profile,
        "blockers": blockers,
        "warnings": warnings,
    }


def render_markdown(pack: dict[str, Any]) -> str:
    lines = [
        "# Song Release Pack",
        "",
        f"- release：{pack.get('release_name')}",
        f"- profile：{pack.get('release_profile')}",
        f"- title：{pack.get('title')}",
        f"- release_ready：{pack.get('release_ready')}",
        "",
        "## Metadata",
        "",
    ]
    for key, value in (pack.get("metadata") or {}).items():
        lines.append(f"- {key}: {value}")
    readiness = pack.get("readiness") or {}
    if readiness.get("blockers"):
        lines.extend(["", "## Blockers", ""])
        for item in readiness["blockers"]:
            lines.append(f"- {item['id']}: {item['message']}")
    if readiness.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for item in readiness["warnings"]:
            lines.append(f"- {item['id']}: {item['message']}")
    lines.extend(["", "## Evidence", ""])
    for key, item in (pack.get("evidence") or {}).items():
        lines.append(f"- {key}: {item.get('path')} exists={item.get('exists')} sha256={item.get('sha256', '')}")
    return "\n".join(lines).rstrip() + "\n"


def write_pack(root: str, pack: dict[str, Any]) -> tuple[str, str]:
    out_dir = os.path.join(root, "导出")
    json_path = os.path.join(out_dir, "release_pack.json")
    md_path = os.path.join(out_dir, "release_pack.md")
    write_json(json_path, pack)
    write_text(md_path, render_markdown(pack))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="生成歌曲发布交付包")
    ap.add_argument("project_root")
    ap.add_argument("--release-name", default="v1")
    ap.add_argument("--profile", default="distribution", choices=("demo", "distribution", "streaming", "archive"))
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--allow-not-ready", action="store_true")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    pack = build_pack(root, args.release_name, args.profile)
    if args.write:
        json_path, md_path = write_pack(root, pack)
        print(f"[ok] release pack JSON → {json_path}")
        print(f"[ok] release pack MD   → {md_path}")
    if args.json:
        print(json.dumps(pack, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(pack))
    if pack["release_ready"] or args.allow_not_ready:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
