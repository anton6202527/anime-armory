#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structured listening review for generated song takes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date
from typing import Any


KIND = "song_take_review"


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


def parse_timecode(value: str) -> dict[str, str]:
    """Parse MM:SS[-MM:SS]|severity|note|status."""
    parts = [p.strip() for p in str(value).split("|")]
    while len(parts) < 4:
        parts.append("")
    return {"timecode": parts[0], "severity": (parts[1] or "note").lower(), "note": parts[2], "status": (parts[3] or "open").lower()}


def score_value(value: Any) -> int:
    try:
        n = int(value)
    except Exception:
        return 0
    return max(0, min(5, n))


def manifest_takes(root: str) -> list[dict[str, Any]]:
    manifest = load_json(os.path.join(root, "歌", "takes_manifest.json"), {}) or {}
    return manifest.get("takes") if isinstance(manifest.get("takes"), list) else []


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_review(root: str, args: argparse.Namespace) -> dict[str, Any]:
    takes = manifest_takes(root)
    existing = load_json(os.path.join(root, "歌", "take_review.json"), {}) or {}
    reviews = existing.get("reviews") if isinstance(existing.get("reviews"), list) else []
    if args.take:
        manifest_row = next((item for item in takes if item.get("take_id") == args.take), {})
        audio_rel = str(manifest_row.get("audio_path") or "")
        audio_path = os.path.join(root, audio_rel)
        row = {
            "take_id": args.take,
            "blind_label": args.blind_label,
            "reviewer": args.reviewer,
            "scores": {
                "hook": score_value(args.hook_score),
                "melody": score_value(args.melody_score),
                "vocal": score_value(args.vocal_score),
                "arrangement": score_value(args.arrangement_score),
                "mix": score_value(args.mix_score),
                "brief_fit": score_value(args.fit_score),
            },
            "total_score": 0,
            "timecode_notes": [parse_timecode(item) for item in args.timecode],
            "strengths": args.strength,
            "risks": args.risk,
            "notes": args.notes,
            "audio_path": audio_rel,
            "audio_sha256": sha256_file(audio_path) if audio_rel and os.path.isfile(audio_path) else "",
        }
        row["total_score"] = sum(row["scores"].values())
        reviews = [r for r in reviews if r.get("take_id") != args.take]
        reviews.append(row)
    reviews.sort(key=lambda r: (-int(r.get("total_score") or 0), str(r.get("take_id") or "")))
    recommended = args.recommend or (reviews[0]["take_id"] if reviews else "")
    return {
        "schema_version": 1,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "take_count": len(takes),
        "review_count": len(reviews),
        "recommended_take": recommended,
        "selection_rationale": args.rationale or ("highest total structured listening score" if recommended else ""),
        "reviews": reviews,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Take Review",
        "",
        f"- 生成日期：{report.get('generated_at')}",
        f"- take_count：{report.get('take_count')}",
        f"- review_count：{report.get('review_count')}",
        f"- recommended_take：{report.get('recommended_take') or '未定'}",
        f"- rationale：{report.get('selection_rationale') or '未填写'}",
        "",
        "| take | total | hook | melody | vocal | arrangement | mix | fit | notes |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("reviews") or []:
        scores = row.get("scores") or {}
        lines.append(
            f"| {row.get('take_id')} | {row.get('total_score')} | {scores.get('hook', 0)} | "
            f"{scores.get('melody', 0)} | {scores.get('vocal', 0)} | {scores.get('arrangement', 0)} | "
            f"{scores.get('mix', 0)} | {scores.get('brief_fit', 0)} | {row.get('notes') or ''} |"
        )
        for note in row.get("timecode_notes") or []:
            lines.append(f"  - {row.get('take_id')} @{note.get('timecode')} [{note.get('severity')}] {note.get('note')}")
    return "\n".join(lines).rstrip() + "\n"


def write_report(root: str, report: dict[str, Any]) -> tuple[str, str]:
    song_dir = os.path.join(root, "歌")
    json_path = os.path.join(song_dir, "take_review.json")
    md_path = os.path.join(song_dir, "take_review.md")
    write_json(json_path, report)
    write_text(md_path, render_markdown(report))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="登记/汇总多版歌曲试听评审")
    ap.add_argument("project_root")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--take", default="")
    ap.add_argument("--blind-label", default="")
    ap.add_argument("--reviewer", default="listener")
    ap.add_argument("--hook-score", type=int, default=0)
    ap.add_argument("--melody-score", type=int, default=0)
    ap.add_argument("--vocal-score", type=int, default=0)
    ap.add_argument("--arrangement-score", type=int, default=0)
    ap.add_argument("--mix-score", type=int, default=0)
    ap.add_argument("--fit-score", type=int, default=0)
    ap.add_argument("--timecode", action="append", default=[], help="MM:SS[-MM:SS]|severity|note|open/resolved/accepted")
    ap.add_argument("--strength", action="append", default=[])
    ap.add_argument("--risk", action="append", default=[])
    ap.add_argument("--notes", default="")
    ap.add_argument("--recommend", default="")
    ap.add_argument("--rationale", default="")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    report = build_review(root, args)
    if args.write:
        json_path, md_path = write_report(root, report)
        print(f"[ok] take review JSON → {json_path}")
        print(f"[ok] take review MD   → {md_path}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
