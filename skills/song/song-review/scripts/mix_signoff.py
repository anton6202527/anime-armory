#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Human mix/performance sign-off bound to the exact pre-master audio."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date
from typing import Any


KIND = "song_mix_performance_signoff"
REQUIRED_CHECKS = (
    "lyric_alignment",
    "diction_and_artifacts",
    "emotional_delivery",
    "vocal_instrument_balance",
    "arrangement_translation",
    "clicks_edits_and_tails",
    "mono_compatibility",
    "low_end_and_headroom",
)
PASS_VALUES = {"pass", "passed", "ok", "通过"}
NA_VALUES = {"na", "n/a", "not_applicable", "不适用"}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_check(value: str) -> tuple[str, dict[str, str]]:
    parts = [item.strip() for item in str(value).split("|", 2)]
    while len(parts) < 3:
        parts.append("")
    return parts[0], {"status": parts[1].lower(), "note": parts[2]}


def build(root: str, args: argparse.Namespace) -> dict[str, Any]:
    relpath = args.audio or "混音/pre_master.wav"
    audio_path = relpath if os.path.isabs(relpath) else os.path.join(root, relpath)
    checks = dict(parse_check(item) for item in args.check)
    findings: list[dict[str, str]] = []
    if not os.path.isfile(audio_path):
        findings.append({"id": "MIX-AUDIO-MISSING", "severity": "blocking", "message": "缺待签核 pre-master。"})
    for name in REQUIRED_CHECKS:
        row = checks.get(name)
        if not row:
            findings.append({"id": "MIX-CHECK-MISSING", "severity": "blocking", "message": f"缺人工检查：{name}。"})
        elif row["status"] not in PASS_VALUES | NA_VALUES:
            findings.append({"id": "MIX-CHECK-FAILED", "severity": "blocking", "message": f"{name}={row['status'] or '未填写'}。"})
        elif row["status"] in NA_VALUES and not row.get("note"):
            findings.append({"id": "MIX-NA-REASON", "severity": "blocking", "message": f"{name}=N/A 时必须说明理由。"})
    if not str(args.reviewer or "").strip():
        findings.append({"id": "MIX-REVIEWER", "severity": "blocking", "message": "缺签核人。"})
    return {
        "schema_version": 1,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "reviewer": args.reviewer,
        "monitoring_context": args.monitoring_context,
        "audio": {
            "path": os.path.relpath(audio_path, root).replace(os.sep, "/") if os.path.exists(audio_path) else relpath,
            "sha256": sha256_file(audio_path) if os.path.isfile(audio_path) else "",
        },
        "checks": checks,
        "notes": args.notes,
        "passed": not findings,
        "blocking": len(findings),
        "findings": findings,
    }


def write_report(root: str, report: dict[str, Any]) -> tuple[str, str]:
    out_dir = os.path.join(root, "混音")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "mix_signoff.json")
    md_path = os.path.join(out_dir, "mix_signoff.md")
    with open(json_path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(json_path + ".tmp", json_path)
    lines = [
        "# Mix / Performance Sign-off", "",
        f"- reviewer: {report.get('reviewer')}", f"- passed: {report.get('passed')}",
        f"- audio: {(report.get('audio') or {}).get('path')} sha256={(report.get('audio') or {}).get('sha256')}", "",
        "## Checks", "",
    ]
    for name in REQUIRED_CHECKS:
        row = (report.get("checks") or {}).get(name) or {}
        lines.append(f"- {name}: {row.get('status', 'missing')} {row.get('note', '')}".rstrip())
    if report.get("findings"):
        lines.extend(["", "## Findings", ""])
        lines.extend(f"- [{item['severity']}] {item['id']}: {item['message']}" for item in report["findings"])
    with open(md_path + ".tmp", "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    os.replace(md_path + ".tmp", md_path)
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="对 pre-master 做绑定音频 hash 的人工混音/表演签核")
    ap.add_argument("project_root")
    ap.add_argument("--audio", default="混音/pre_master.wav")
    ap.add_argument("--reviewer", required=True)
    ap.add_argument("--monitoring-context", default="headphones+speakers")
    ap.add_argument("--check", action="append", default=[], help="NAME|pass/fail/na|NOTE")
    ap.add_argument("--notes", default="")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    report = build(root, args)
    if args.write:
        json_path, md_path = write_report(root, report)
        print(f"[ok] mix signoff JSON -> {json_path}")
        print(f"[ok] mix signoff MD   -> {md_path}")
    if args.json or not args.write:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
