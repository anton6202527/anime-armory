#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build publishing rights metadata and a split sheet for a song project."""
from __future__ import annotations

import argparse
import hashlib
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


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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
    title = args.title or meta.get("title") or os.path.basename(root)
    payload = {
        "schema_version": 3,
        "kind": RIGHTS_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "title": title,
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
            "reference_metadata": {
                "title": title,
                "version_title": getattr(args, "version_title", "") or "Original",
                "main_artist": getattr(args, "main_artist", "") or (performers[0] if performers else ""),
                "duration_seconds": getattr(args, "duration_seconds", None) or meta.get("target_duration_seconds"),
                "recording_type": getattr(args, "recording_type", "") or "audio",
                "year_of_first_publication": getattr(args, "publication_year", None),
            },
            "performers": performers,
            "producers": producers,
            "label": args.label,
            "soundexchange_registration_status": args.soundexchange_status,
        },
        "licenses": {
            "derivative_type": getattr(args, "derivative_type", "") or "unknown",
            "composition_authorization_status": getattr(args, "composition_authorization_status", "") or "unknown",
            "sample_usage_status": getattr(args, "sample_usage_status", "") or "unknown",
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
    recording = payload.get("sound_recording") if isinstance(payload.get("sound_recording"), dict) else {}
    isrc = (recording.get("isrc") or "").strip()
    if isrc and not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{3}[0-9]{7}", isrc):
        issue("RIGHTS-ISRC-FORMAT", "warning", "ISRC 格式疑似不正确，应为 12 位标准码。")
    if not isrc:
        issue("RIGHTS-ISRC-MISSING", "warning", "缺 ISRC；demo 可缺，正式发行前应补。")
    else:
        reference = recording.get("reference_metadata") if isinstance(recording.get("reference_metadata"), dict) else {}
        labels = {
            "title": "title", "version_title": "version title", "main_artist": "main artist",
            "duration_seconds": "duration", "recording_type": "recording type",
            "year_of_first_publication": "year of first publication",
        }
        missing = [label for key, label in labels.items() if reference.get(key) in {"", None}]
        if missing:
            issue("RIGHTS-ISRC-REFERENCE-METADATA", "blocking", "已分配 ISRC，但 reference metadata 不完整：" + ", ".join(missing) + "。")
    if not comp.get("iswc"):
        issue("RIGHTS-ISWC-MISSING", "warning", "缺 ISWC；未登记作品时可先留空。")
    if not recording.get("performers"):
        issue("RIGHTS-PERFORMER-MISSING", "warning", "缺 performer/artist。")
    licenses = payload.get("licenses") if isinstance(payload.get("licenses"), dict) else {}
    derivative = licenses.get("derivative_type")
    if derivative not in {"original", "cover", "remix", "interpolation"}:
        issue("RIGHTS-DERIVATIVE-TYPE", "blocking", "derivative_type 必须明确为 original/cover/remix/interpolation。")
    if derivative == "cover" and licenses.get("cover_license_status") not in {"secured", "authorized", "licensed", "已授权"}:
        issue("RIGHTS-COVER-LICENSE", "blocking", "翻唱作品缺已落实的 cover license。")
    if derivative in {"remix", "interpolation"} and licenses.get("composition_authorization_status") not in {"secured", "authorized", "licensed", "已授权"}:
        issue("RIGHTS-DERIVATIVE-AUTH", "blocking", f"{derivative} 缺词曲/录音授权。")
    sample_usage = licenses.get("sample_usage_status")
    if sample_usage not in {"none", "used", "无", "使用"}:
        issue("RIGHTS-SAMPLE-USAGE", "blocking", "sample_usage_status 必须明确为 none/used。")
    if sample_usage in {"used", "使用"} and licenses.get("sample_clearance_status") not in {"cleared", "licensed", "authorized", "已清权", "已授权"}:
        issue("RIGHTS-SAMPLE-CLEARANCE", "blocking", "使用了 sample 但 clearance 未完成。")
    if licenses.get("voice_authorization_status") not in {"own", "authorized", "synthetic", "自有", "已授权", "合成"}:
        issue("RIGHTS-VOICE-AUTH", "blocking", "voice_authorization_status 必须单义明确为 own/authorized/synthetic。")
    blockers = [item for item in findings if item["severity"] == "blocking"]
    return {
        "schema_version": 1,
        "kind": CHECK_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": payload.get("project_root"),
        "source_sha256": canonical_hash(payload),
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
        f"- ISRC reference metadata：{recording.get('reference_metadata') or {}}",
        f"- SoundExchange：{recording.get('soundexchange_registration_status') or '未登记'}",
        f"- licenses：{payload.get('licenses') or {}}",
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
    ap.add_argument("--version-title", default="")
    ap.add_argument("--main-artist", default="")
    ap.add_argument("--duration-seconds", type=float, default=None)
    ap.add_argument("--recording-type", default="audio")
    ap.add_argument("--publication-year", type=int, default=None)
    ap.add_argument("--iswc", default="")
    ap.add_argument("--pro-status", default="not_registered")
    ap.add_argument("--mlc-status", default="not_registered")
    ap.add_argument("--soundexchange-status", default="not_registered")
    ap.add_argument("--derivative-type", default="", choices=("", "original", "cover", "remix", "interpolation"))
    ap.add_argument("--composition-authorization-status", default="")
    ap.add_argument("--sample-usage-status", default="", choices=("", "none", "used"))
    ap.add_argument("--sample-clearance-status", default="not_applicable")
    ap.add_argument("--cover-license-status", default="not_applicable")
    ap.add_argument("--voice-authorization-status", default="", choices=("", "own", "authorized", "synthetic"))
    ap.add_argument("--notes", default="")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    existing = load_json(out_paths(root)[0], {}) if not any([
        args.title, args.alternate_title, args.rights_status, args.contributor, args.performer,
        args.producer, args.label, args.isrc, args.iswc, args.notes, args.version_title,
        args.main_artist, args.duration_seconds, args.publication_year, args.derivative_type,
        args.composition_authorization_status, args.sample_usage_status, args.voice_authorization_status,
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
