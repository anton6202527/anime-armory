#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refresh MV candidate snapshots and provenance.

The script writes dated, source-backed snapshots. URL verification is optional
because many production runs happen offline or inside restricted environments.
"""
import argparse
import json
import os
import sys
import urllib.request
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import freshness  # noqa: E402


CURRENT_SNAPSHOTS = {
    "video_models": [
        {
            "name": "Veo 3.1",
            "capabilities": ["reference_images", "start_end_frames", "native_audio"],
            "notes": "适合电影感关键镜；正式使用前确认地区/API配额/价格。",
        },
        {
            "name": "Runway Gen-4",
            "capabilities": ["reference_images", "start_end_frames", "character_consistency"],
            "notes": "适合单参考角色一致性和质感关键镜。",
        },
        {
            "name": "Kling 3.0",
            "capabilities": ["reference_images", "start_end_frames", "reference_video_motion", "native_audio", "lip_sync"],
            "notes": "适合动作镜、首尾帧控制和演唱口型候选。",
        },
        {
            "name": "Luma Ray3 / Ray3.14",
            "capabilities": ["reference_images", "keyframes", "start_end_frames", "hdr_export"],
            "notes": "适合 keyframe/角色参考/调色链路。",
        },
        {
            "name": "Seedance 2.0",
            "capabilities": ["reference_images", "start_end_frames", "reference_video_motion"],
            "notes": "适合快节奏短视频和批量镜头；以所用渠道官方说明为准。",
        },
        {
            "name": "manual",
            "capabilities": ["human_registered"],
            "notes": "人工/网页/外包登记路径，必须留来源、参数和挑版理由。",
        },
    ],
    "video_channels": [
        {"name": "Google Gemini API", "integration": "api", "official_api": True},
        {"name": "Runway API", "integration": "api", "official_api": True},
        {"name": "可灵/Kling", "integration": "api_or_web", "official_api": True},
        {"name": "Luma Dream Machine", "integration": "api_or_web", "official_api": True},
        {"name": "即梦/Dreamina", "integration": "manual_web", "official_api": False},
        {"name": "本地/开源", "integration": "local", "official_api": False},
        {"name": "manual", "integration": "manual", "official_api": False},
    ],
    "image_backends": [
        {"name": "Codex / OpenAI gpt-image", "multi_reference": False, "native_subject": False},
        {"name": "Seedream Universal Reference", "multi_reference": True, "native_subject": True},
        {"name": "可灵主体库", "multi_reference": True, "native_subject": True},
        {"name": "Nano Banana / Gemini", "multi_reference": True, "native_subject": False},
        {"name": "Sora Cameo", "multi_reference": True, "native_subject": True},
    ],
}


def verify_url(url, timeout=8):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "mv-refresh/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"url": url, "ok": 200 <= resp.status < 400, "status": resp.status}
    except Exception as exc:
        return {"url": url, "ok": False, "error": str(exc)}


def build_snapshot(key, as_of, verify=False):
    source = freshness.CANDIDATE_SOURCES[key]
    checks = [verify_url(url) for url in source["source_urls"]] if verify else []
    return {
        "kind": "mv_candidate_snapshot",
        "key": key,
        "collected_at": as_of,
        "description": source["description"],
        "source_urls": source["source_urls"],
        "url_checks": checks,
        "verification_mode": "url_head" if verify else "declared_sources_only",
        "items": CURRENT_SNAPSHOTS[key],
        "notes": [
            "候选清单只是带日期的能力快照，不是唯一真理。",
            "正式花钱/不可逆步骤前按所选模型和渠道再次核验官方文档、价格、地区和 API 限制。",
        ],
    }


def write_snapshot(repo, key, payload):
    path = freshness.snapshot_path(key, repo)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path


def main():
    ap = argparse.ArgumentParser(description="Refresh MV model/channel candidate snapshots")
    ap.add_argument("--repo", default=freshness.repo_root())
    ap.add_argument("--key", choices=sorted(freshness.CANDIDATE_SOURCES), action="append")
    ap.add_argument("--as-of", default=date.today().isoformat())
    ap.add_argument("--verify-url", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    keys = args.key or sorted(freshness.CANDIDATE_SOURCES)
    for key in keys:
        payload = build_snapshot(key, args.as_of, verify=args.verify_url)
        if args.dry_run:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            continue
        path = write_snapshot(args.repo, key, payload)
        print(f"[ok] refreshed {key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
