#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a lossless delivery master from an approved pre-master.

This performs format conformance only. It does not claim to replace mix or
mastering decisions and intentionally applies no loudness normalization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import date


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def source_format(path: str) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {}
    proc = subprocess.run([
        ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries",
        "stream=sample_rate,bits_per_raw_sample,bits_per_sample,sample_fmt", "-of", "json", path,
    ], capture_output=True, text=True, check=True)
    stream = (json.loads(proc.stdout).get("streams") or [{}])[0]
    return {
        "sample_rate": int(stream.get("sample_rate") or 0),
        "bit_depth": int(stream.get("bits_per_raw_sample") or stream.get("bits_per_sample") or 0),
        "sample_fmt": stream.get("sample_fmt"),
    }


def load_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def build(root: str, source: str = "", *, allow_unsigned_demo: bool = False) -> tuple[str, str]:
    source_path = os.path.abspath(source) if source else os.path.join(root, "混音", "pre_master.wav")
    if not os.path.isfile(source_path):
        raise SystemExit(f"[err] 缺 pre-master：{source_path}")
    signoff = load_json(os.path.join(root, "混音", "mix_signoff.json"))
    signed_hash = ((signoff.get("audio") or {}).get("sha256") or "")
    if not allow_unsigned_demo and (signoff.get("passed") is not True or signed_hash != sha256_file(source_path)):
        raise SystemExit("[err] mix_signoff 未通过或未绑定当前 pre-master；先跑 song-review/scripts/mix_signoff.py")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("[err] 缺 ffmpeg，无法生成可验证的 24-bit PCM 交付母版")
    out_dir = os.path.join(root, "导出")
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, "master.wav")
    subprocess.run([
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", source_path,
        "-map_metadata", "-1", "-vn", "-c:a", "pcm_s24le", target,
    ], check=True)
    receipt = {
        "schema_version": 1,
        "kind": "song_master_delivery_receipt",
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "operation": "lossless_format_conformance_only",
        "loudness_normalization_applied": False,
        "mix_signoff": {
            "path": "混音/mix_signoff.json",
            "passed": signoff.get("passed") is True,
            "audio_sha256": signed_hash,
            "demo_waiver": bool(allow_unsigned_demo),
        },
        "source": {
            "path": os.path.relpath(source_path, root).replace(os.sep, "/"),
            "sha256": sha256_file(source_path),
            **source_format(source_path),
        },
        "master": {"path": "导出/master.wav", "sha256": sha256_file(target), "codec": "pcm_s24le"},
        "next_gate": "song-review/scripts/master_check.py --platform streaming --write",
        "note": "Converting 16-bit input to a 24-bit container does not restore lost resolution and does not qualify it as an Apple Digital Masters source.",
    }
    receipt_path = os.path.join(out_dir, "master_delivery.json")
    with open(receipt_path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(receipt_path + ".tmp", receipt_path)
    return target, receipt_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="从已批准 pre-master 生成 24-bit PCM 交付母版")
    ap.add_argument("project_root")
    ap.add_argument("--source", default="")
    ap.add_argument("--allow-unsigned-demo", action="store_true")
    args = ap.parse_args(argv)
    target, receipt = build(os.path.abspath(args.project_root), args.source, allow_unsigned_demo=args.allow_unsigned_demo)
    print(f"[ok] delivery master -> {target}")
    print(f"[ok] receipt         -> {receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
