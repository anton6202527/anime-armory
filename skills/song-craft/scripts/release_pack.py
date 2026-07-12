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


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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
    mix_signoff = load_json(os.path.join(root, "混音", "mix_signoff.json"), {}) or {}
    release_metadata = load_json(os.path.join(root, "发行", "release_metadata.json"), {}) or {}
    release_metadata_check = load_json(os.path.join(root, "发行", "release_metadata_check.json"), {}) or {}
    evidence = {
        "audio_master": record(root, "导出/master.wav"),
        "selected_preview": record(root, "歌/song.wav"),
        "pre_master": record(root, "混音/pre_master.wav"),
        "master_delivery": record(root, "导出/master_delivery.json"),
        "mix_signoff": record(root, "混音/mix_signoff.json"),
        "selection_gate": record(root, "评审/quality_gate_select.json"),
        "lyrics": record(root, "词/lyrics.md"),
        "take_manifest": record(root, "歌/takes_manifest.json"),
        "take_review": record(root, "歌/take_review.json"),
        "master_check": record(root, "混音/master_check.json"),
        "rights_metadata": record(root, "合规/rights_metadata.json"),
        "rights_check": record(root, "合规/rights_metadata_check.json"),
        "split_sheet": record(root, "合规/split_sheet.md"),
        "ai_usage": record(root, "合规/ai_usage.json"),
        "cover_receipt": record(root, "歌/cover_receipt.json"),
        "release_metadata": record(root, "发行/release_metadata.json"),
        "release_metadata_check": record(root, "发行/release_metadata_check.json"),
        "cover_art": record(root, "导出/cover.jpg"),
    }
    readiness = release_readiness(
        root, profile, evidence, rights, rights_check, master, ai_usage, take_manifest,
        mix_signoff, release_metadata, release_metadata_check,
    )
    return {
        "schema_version": 2,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "release_name": release_name,
        "release_profile": profile,
        "title": release_metadata.get("track_title") or meta.get("title") or os.path.basename(root),
        "artist": [row.get("name") for row in release_metadata.get("artists") or [] if row.get("role") == "main_artist"] or (rights.get("sound_recording") or {}).get("performers") or [meta.get("performer") or ""],
        "release_ready": not readiness["blockers"],
        "readiness": readiness,
        "metadata": {
            "rights_status": rights.get("rights_status") or meta.get("rights_status") or "unknown",
            "isrc": ((rights.get("sound_recording") or {}).get("isrc") or ""),
            "iswc": ((rights.get("composition_rights") or {}).get("iswc") or ""),
            "selected_take": take_manifest.get("selected_take"),
            "ai_audio_mode": ai_usage.get("audio_mode"),
            "ai_lyrics_mode": ai_usage.get("lyrics_mode"),
            "release_date": release_metadata.get("release_date"),
            "explicit": release_metadata.get("explicit"),
            "territories": release_metadata.get("territories"),
        },
        "evidence": evidence,
    }


def release_readiness(
    root: str,
    profile: str,
    evidence: dict[str, dict[str, Any]],
    rights: dict[str, Any],
    rights_check: dict[str, Any],
    master: dict[str, Any],
    ai_usage: dict[str, Any],
    take_manifest: dict[str, Any],
    mix_signoff: dict[str, Any],
    release_metadata: dict[str, Any],
    release_metadata_check: dict[str, Any],
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
    if profile != "demo":
        for key in (
            "selected_preview", "pre_master", "take_review", "mix_signoff", "master_delivery",
            "selection_gate", "rights_check", "release_metadata", "release_metadata_check",
        ):
            if not evidence.get(key, {}).get("exists"):
                issue(blockers, f"MISSING-{key.upper()}", f"正式交付缺少 {key} 证据。")
    if rights_check and rights_check.get("passed") is not True:
        issue(blockers, "RIGHTS-CHECK", "rights metadata check 未通过。")
    elif rights and rights.get("rights_status") in {"unknown", "", None}:
        issue(blockers, "RIGHTS-UNKNOWN", "权利状态未知。")
    if profile != "demo" and rights and rights_check.get("source_sha256") != canonical_hash(rights):
        issue(blockers, "RIGHTS-CHECK-STALE", "rights metadata check 与当前 rights metadata 不一致。")
    if master and master.get("passed") is not True:
        issue(blockers, "MASTER-CHECK", "master_check 未通过。")
    elif profile != "demo" and master.get("measurement_complete") is not True:
        issue(blockers, "MASTER-MEASUREMENT", "master_check 缺 ITU-R BS.1770 完整测量。")
    if profile in {"archive", "apple_digital_masters"} and master.get("platform_profile") != profile:
        issue(blockers, "MASTER-PROFILE", f"{profile} 发行包必须使用同 profile 的 master_check。")
    master_hash = ((master.get("metrics") or {}).get("sha256") or "") if master else ""
    evidence_hash = evidence.get("audio_master", {}).get("sha256") or ""
    if master_hash and evidence_hash and master_hash != evidence_hash:
        issue(blockers, "MASTER-CHECK-STALE", "master_check 绑定的音频与当前 master.wav 不一致。")
    elif profile != "demo" and evidence_hash and not master_hash:
        issue(blockers, "MASTER-HASH-MISSING", "master_check 未绑定 master.wav sha256。")
    delivery = load_json(os.path.join(root, "导出", "master_delivery.json"), {}) or {}
    pre_master_path = os.path.join(root, "混音", "pre_master.wav")
    if profile != "demo" and os.path.isfile(pre_master_path):
        expected_source = ((delivery.get("source") or {}).get("sha256") or "")
        if not expected_source or expected_source != sha256_file(pre_master_path):
            issue(blockers, "MASTER-DELIVERY-STALE", "master_delivery 不是由当前 pre_master.wav 生成。")
        signoff_hash = ((mix_signoff.get("audio") or {}).get("sha256") or "")
        if mix_signoff.get("passed") is not True or signoff_hash != sha256_file(pre_master_path):
            issue(blockers, "MIX-SIGNOFF-STALE", "mix_signoff 未通过或未绑定当前 pre_master.wav。")
    if profile == "apple_digital_masters" and int(((delivery.get("source") or {}).get("bit_depth") or 0)) < 24:
        issue(blockers, "APPLE-SOURCE-BIT-DEPTH", "Apple Digital Masters 要求原始 source 至少 24-bit；升位深封装不能补回精度。")
    selection_gate = load_json(os.path.join(root, "评审", "quality_gate_select.json"), {}) or {}
    if profile != "demo":
        if selection_gate.get("passed_without_waiver") is not True:
            issue(blockers, "SELECTION-GATE-WAIVED", "正式发行要求 select 闸门无 waiver 通过。")
        if selection_gate.get("take_id") != take_manifest.get("selected_take"):
            issue(blockers, "SELECTION-GATE-STALE", "select 闸门与当前 selected_take 不一致。")
        preview_path = os.path.join(root, "歌", "song.wav")
        preview_hash = sha256_file(preview_path) if os.path.isfile(preview_path) else ""
        cover = load_json(os.path.join(root, "歌", "cover_receipt.json"), {}) or {}
        if cover:
            cover_hash = ((cover.get("audio") or {}).get("sha256") or "")
            if cover.get("authorization") not in {"own", "authorized", "synthetic", "自有", "已授权", "合成"} or cover_hash != preview_hash:
                issue(blockers, "COVER-RECEIPT-STALE", "cover receipt 授权或音频 hash 与当前 song.wav 不一致。")
            invalidated = cover.get("invalidated_evidence_hashes") if isinstance(cover.get("invalidated_evidence_hashes"), dict) else {}
            for relpath, old_hash in invalidated.items():
                path = os.path.join(root, relpath)
                if os.path.isfile(path) and sha256_file(path) == old_hash:
                    issue(blockers, "COVER-DOWNSTREAM-STALE", f"换声后仍沿用旧证据：{relpath}。")
        else:
            receipt = take_manifest.get("selection_receipt") if isinstance(take_manifest.get("selection_receipt"), dict) else {}
            if not receipt or receipt.get("song_audio_sha256") != preview_hash:
                issue(blockers, "SELECTION-RECEIPT-STALE", "selection receipt 与当前 song.wav 不一致。")
    if ai_usage and not ai_usage.get("human_contribution"):
        target = blockers if profile != "demo" else warnings
        issue(target, "AI-HUMAN-CONTRIBUTION", "AI 使用披露缺 human_contribution；无法说明可主张的人类创作贡献。")
    if profile != "demo":
        if release_metadata_check.get("passed") is not True:
            issue(blockers, "RELEASE-METADATA-CHECK", "release metadata check 未通过。")
        elif release_metadata_check.get("source_sha256") != canonical_hash(release_metadata):
            issue(blockers, "RELEASE-METADATA-STALE", "release metadata check 与当前 metadata 不一致。")
        recording = rights.get("sound_recording") if isinstance(rights.get("sound_recording"), dict) else {}
        reference = recording.get("reference_metadata") if isinstance(recording.get("reference_metadata"), dict) else {}
        identifiers = release_metadata.get("identifiers") if isinstance(release_metadata.get("identifiers"), dict) else {}
        if release_metadata.get("track_title") != rights.get("title"):
            issue(blockers, "METADATA-TITLE-DRIFT", "release track title 与 rights title 不一致。")
        if (identifiers.get("isrc") or "") != (recording.get("isrc") or ""):
            issue(blockers, "METADATA-ISRC-DRIFT", "release metadata 与 rights metadata 的 ISRC 不一致。")
        if release_metadata.get("version_title") != reference.get("version_title"):
            issue(blockers, "METADATA-VERSION-DRIFT", "release version title 与 ISRC reference metadata 不一致。")
        actual_duration = ((master.get("metrics") or {}).get("duration_seconds"))
        declared_duration = reference.get("duration_seconds")
        if actual_duration is not None and declared_duration is not None and abs(float(actual_duration) - float(declared_duration)) > 1.0:
            issue(blockers, "METADATA-DURATION-DRIFT", "ISRC reference duration 与当前 master 相差超过 1 秒。")
    if profile in {"distribution", "streaming", "archive", "apple_digital_masters"}:
        if not ((rights.get("sound_recording") or {}).get("isrc")):
            issue(warnings, "ISRC-MISSING", "正式发行建议补 ISRC。")
        if not evidence.get("cover_art", {}).get("exists"):
            target = blockers if profile in {"distribution", "streaming", "apple_digital_masters"} else warnings
            issue(target, "COVER-ART-MISSING", "缺导出/cover.jpg；正式数字发行包不完整。")
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
    ap.add_argument("--profile", default="distribution", choices=("demo", "distribution", "streaming", "archive", "apple_digital_masters"))
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
