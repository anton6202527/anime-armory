#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build publishing rights metadata and a split sheet for a song project."""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date
from typing import Any


RIGHTS_KIND = "song_rights_metadata"
CHECK_KIND = "song_rights_metadata_check"


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


def out_paths(root: str) -> tuple[str, str, str]:
    out_dir = os.path.join(root, "合规")
    return (
        os.path.join(out_dir, "rights_metadata.json"),
        os.path.join(out_dir, "rights_metadata_check.json"),
        os.path.join(out_dir, "split_sheet.md"),
    )


def split_person(value: str, default_role: str = "songwriter") -> dict[str, Any]:
    """Parse NAME|ROLE|SHARE|PRO|IPI|PUBLISHER."""
    parts = [p.strip() for p in str(value).split("|")]
    while len(parts) < 6:
        parts.append("")
    share = 0.0
    if parts[2]:
        share = float(parts[2])
    return {
        "name": parts[0],
        "role": parts[1] or default_role,
        "share_percent": share,
        "pro": parts[3],
        "ipi_cae": parts[4],
        "publisher": parts[5],
    }


def split_names(values: list[str] | None) -> list[str]:
    out: list[str] = []
    for value in values or []:
        for part in str(value).replace("，", ",").split(","):
            item = part.strip()
            if item and item not in out:
                out.append(item)
    return out


def build_metadata(root: str, args: argparse.Namespace) -> dict[str, Any]:
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    contributors = [split_person(item) for item in args.contributor]
    if not contributors:
        author = meta.get("author") or meta.get("creator") or ""
        if author:
            contributors = [{"name": author, "role": "songwriter", "share_percent": 100.0, "pro": "", "ipi_cae": "", "publisher": ""}]
    performers = split_names(args.performer) or split_names([meta.get("performer") or ""])
    producers = split_names(args.producer)
    payload = {
        "schema_version": 1,
        "kind": RIGHTS_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "title": args.title or meta.get("title") or os.path.basename(root),
        "alternate_titles": split_names(args.alternate_title),
        "rights_status": args.rights_status or meta.get("rights_status") or "unknown",
        "composition_rights": {
            "contributors": contributors,
            "split_total": round(sum(float(c.get("share_percent") or 0) for c in contributors), 4),
            "iswc": args.iswc,
            "pro_registration_status": args.pro_status,
            "mlc_registration_status": args.mlc_status,
        },
        "sound_recording": {
            "isrc": args.isrc,
            "performers": performers,
            "producers": producers,
            "label": args.label,
            "soundexchange_registration_status": args.soundexchange_status,
        },
        "licenses": {
            "sample_clearance_status": args.sample_clearance_status,
            "cover_license_status": args.cover_license_status,
            "voice_authorization_status": args.voice_authorization_status,
            "notes": args.notes,
        },
    }
    return payload


def check_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def issue(issue_id: str, severity: str, message: str) -> None:
        findings.append({"id": issue_id, "severity": severity, "message": message, "path": "合规/rights_metadata.json"})

    if payload.get("kind") != RIGHTS_KIND:
        issue("RIGHTS-KIND", "blocking", "rights_metadata.json kind 不正确。")
    if not str(payload.get("title") or "").strip():
        issue("RIGHTS-TITLE", "blocking", "缺歌曲标题。")
    if payload.get("rights_status") in {"unknown", "", None}:
        issue("RIGHTS-STATUS", "blocking", "词曲权利状态未知。")
    comp = payload.get("composition_rights") if isinstance(payload.get("composition_rights"), dict) else {}
    contributors = comp.get("contributors") if isinstance(comp.get("contributors"), list) else []
    if not contributors:
        issue("RIGHTS-CONTRIBUTORS", "blocking", "缺词曲作者/贡献者。")
    total = float(comp.get("split_total") or 0)
    if contributors and abs(total - 100.0) > 0.01:
        issue("RIGHTS-SPLIT", "blocking", f"Split total={total}，必须等于 100。")
    for row in contributors:
        if not row.get("name"):
            issue("RIGHTS-CONTRIBUTOR-NAME", "blocking", "贡献者缺 name。")
            break
    isrc = ((payload.get("sound_recording") or {}).get("isrc") or "").strip()
    if isrc and not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{3}[0-9]{7}", isrc):
        issue("RIGHTS-ISRC-FORMAT", "warning", "ISRC 格式疑似不正确，应为 12 位标准码。")
    if not isrc:
        issue("RIGHTS-ISRC-MISSING", "warning", "缺 ISRC；demo 可缺，正式发行前应补。")
    if not comp.get("iswc"):
        issue("RIGHTS-ISWC-MISSING", "warning", "缺 ISWC；未登记作品时可先留空。")
    recording = payload.get("sound_recording") if isinstance(payload.get("sound_recording"), dict) else {}
    if not recording.get("performers"):
        issue("RIGHTS-PERFORMER-MISSING", "warning", "缺 performer/artist。")
    blockers = [item for item in findings if item["severity"] == "blocking"]
    return {
        "schema_version": 1,
        "kind": CHECK_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": payload.get("project_root"),
        "blocking": len(blockers),
        "warnings": len(findings) - len(blockers),
        "passed": not blockers,
        "findings": findings,
    }


def render_split_sheet(payload: dict[str, Any], check: dict[str, Any]) -> str:
    comp = payload.get("composition_rights") or {}
    recording = payload.get("sound_recording") or {}
    lines = [
        "# Split Sheet",
        "",
        f"- 标题：{payload.get('title')}",
        f"- 权利状态：{payload.get('rights_status')}",
        f"- ISWC：{comp.get('iswc') or '未填写'}",
        f"- ISRC：{recording.get('isrc') or '未填写'}",
        "",
        "## Composition Splits",
        "",
        "| name | role | share | PRO | IPI/CAE | publisher |",
        "|---|---|---:|---|---|---|",
    ]
    for row in comp.get("contributors") or []:
        lines.append(
            f"| {row.get('name') or ''} | {row.get('role') or ''} | {row.get('share_percent') or 0}% | "
            f"{row.get('pro') or ''} | {row.get('ipi_cae') or ''} | {row.get('publisher') or ''} |"
        )
    lines.extend([
        "",
        f"- split total：{comp.get('split_total')}",
        "",
        "## Sound Recording",
        "",
        "- performers：" + (", ".join(recording.get("performers") or []) or "未填写"),
        "- producers：" + (", ".join(recording.get("producers") or []) or "未填写"),
        f"- label：{recording.get('label') or '未填写'}",
        f"- SoundExchange：{recording.get('soundexchange_registration_status') or '未登记'}",
    ])
    if check.get("findings"):
        lines.extend(["", "## Findings", ""])
        for item in check["findings"]:
            lines.append(f"- [{item['severity']}] {item['id']}: {item['message']}")
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(root: str, payload: dict[str, Any], check: dict[str, Any]) -> tuple[str, str, str]:
    json_path, check_path, split_path = out_paths(root)
    write_json(json_path, payload)
    write_json(check_path, check)
    write_text(split_path, render_split_sheet(payload, check))
    return json_path, check_path, split_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="生成/检查歌曲权益元数据与 split sheet")
    ap.add_argument("project_root")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--title", default="")
    ap.add_argument("--alternate-title", action="append", default=[])
    ap.add_argument("--rights-status", default="")
    ap.add_argument("--contributor", action="append", default=[], help="NAME|ROLE|SHARE|PRO|IPI|PUBLISHER")
    ap.add_argument("--performer", action="append", default=[])
    ap.add_argument("--producer", action="append", default=[])
    ap.add_argument("--label", default="")
    ap.add_argument("--isrc", default="")
    ap.add_argument("--iswc", default="")
    ap.add_argument("--pro-status", default="not_registered")
    ap.add_argument("--mlc-status", default="not_registered")
    ap.add_argument("--soundexchange-status", default="not_registered")
    ap.add_argument("--sample-clearance-status", default="not_applicable")
    ap.add_argument("--cover-license-status", default="not_applicable")
    ap.add_argument("--voice-authorization-status", default="synthetic_or_own")
    ap.add_argument("--notes", default="")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    existing = load_json(out_paths(root)[0], {}) if not any([
        args.title, args.alternate_title, args.rights_status, args.contributor, args.performer,
        args.producer, args.label, args.isrc, args.iswc, args.notes,
    ]) else {}
    payload = existing if isinstance(existing, dict) and existing.get("kind") == RIGHTS_KIND else build_metadata(root, args)
    check = check_metadata(payload)
    if args.write:
        json_path, check_path, split_path = write_outputs(root, payload, check)
        print(f"[ok] rights metadata → {json_path}")
        print(f"[ok] rights check    → {check_path}")
        print(f"[ok] split sheet     → {split_path}")
    if args.json:
        print(json.dumps({"rights_metadata": payload, "check": check}, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_split_sheet(payload, check))
    return 0 if check["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
