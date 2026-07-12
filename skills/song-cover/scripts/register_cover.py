#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Register an authorized singing-voice conversion as the new pre-master."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import date


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def register(root: str, source: str, model: str, authorization: str, notes: str) -> str:
    allowed = {"own", "authorized", "synthetic", "自有", "已授权", "合成"}
    if authorization.strip().lower() not in allowed:
        raise SystemExit("[err] --authorization 必须明确为 own/authorized/synthetic（或自有/已授权/合成）")
    if not os.path.isfile(source):
        raise SystemExit(f"[err] 找不到 cover 音频：{source}")
    cover_id = "cover_" + date.today().strftime("%Y%m%d")
    cover_dir = os.path.join(root, "歌", "covers")
    os.makedirs(cover_dir, exist_ok=True)
    archived = os.path.join(cover_dir, cover_id + ".wav")
    shutil.copy2(source, archived)
    for relpath in ("歌/song.wav", "混音/pre_master.wav"):
        target = os.path.join(root, relpath)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(archived, target)
    invalidated_hashes = {}
    for relpath in ("合规/rights_metadata.json", "合规/ai_usage.json"):
        path = os.path.join(root, relpath)
        if os.path.isfile(path):
            invalidated_hashes[relpath] = sha256_file(path)
    receipt = {
        "schema_version": 1,
        "kind": "song_cover_receipt",
        "generated_at": date.today().isoformat(),
        "cover_id": cover_id,
        "model_or_voice": model,
        "authorization": authorization,
        "notes": notes,
        "audio": {"path": os.path.relpath(archived, root).replace(os.sep, "/"), "sha256": sha256_file(archived)},
        "invalidates": [
            "混音/mix_signoff.json", "导出/master.wav", "导出/master_delivery.json", "混音/master_check.json",
            "合规/rights_metadata.json", "合规/rights_metadata_check.json", "合规/ai_usage.json", "导出/release_pack.json",
        ],
        "invalidated_evidence_hashes": invalidated_hashes,
        "requires_new_recording_metadata": True,
        "next_action": "更新新录音的 rights/ISRC 与 AI 使用说明，重做 mix signoff、master delivery、master check、release pack",
    }
    path = os.path.join(root, "歌", "cover_receipt.json")
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(path + ".tmp", path)
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="登记合法换声结果并使下游母版/发行证据失效")
    ap.add_argument("project_root")
    ap.add_argument("audio")
    ap.add_argument("--model", required=True)
    ap.add_argument("--authorization", required=True)
    ap.add_argument("--notes", default="")
    args = ap.parse_args(argv)
    print(f"[ok] cover receipt -> {register(os.path.abspath(args.project_root), os.path.abspath(args.audio), args.model, args.authorization, args.notes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
