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
            "name": "Seedance 2.5",
            "capabilities": [
                "reference_images_up_to_30", "reference_videos_up_to_10",
                "reference_audio_up_to_10", "native_audio", "multi_shot_30s",
                "timestamp_level_editing",
            ],
            "notes": "Jimeng/Doubao 已发布；官方公告写明 API coming soon，未实际开放的 API route 必须保持 pending。",
        },
        {
            "name": "Gemini Omni Flash Preview",
            "preview": True,
            "route_status": "adapter_required",
            "provider_model_id": "gemini-omni-flash-preview",
            "capabilities": [
                "text_image_reference_video_generation", "native_generated_audio",
                "aspect_16_9_or_9_16", "synthid",
            ],
            "notes": "官方推荐的 Gemini API 预览入口，但未发布可安全固化的完整时长/fps/分辨率矩阵；上传音频参考不支持，视频参考当前处理受限。必须提供本账号/SDK 实测的具名 capability adapter，不能借用 Veo 参数。",
        },
        {
            "name": "Veo 3.1",
            "capabilities": [
                "reference_images_up_to_3", "start_end_frames", "native_audio_always_on",
                "duration_4_6_8s", "24fps", "720p_1080p_4k_with_constraints",
            ],
            "notes": "reference/end-frame/1080p/4K 均有 8 秒组合限制；由 model×channel 适配层逐请求核验。",
        },
        {
            "name": "Runway Gen-4.5",
            "capabilities": ["text_to_video", "image_to_video", "complex_sequenced_instructions"],
            "notes": "官方当前高质量模型；公开控制以 T2V/I2V 为主，首尾帧等额外输入按渠道重新核验。",
        },
        {
            "name": "Kling 3.0",
            "capabilities": ["reference_images", "elements", "start_end_frames", "reference_video_motion", "native_audio", "lip_sync", "multi_shot"],
            "notes": "适合 Elements 主体、多镜头叙事、动作镜和演唱口型候选。",
        },
        {
            "name": "Luma Ray3 / Ray3.14",
            "legacy": True,
            "capabilities": ["legacy_compatibility_only"],
            "notes": "旧项目原值，不静默升级或与 Ray3.2 混写。",
        },
        {
            "name": "Luma Ray3.2",
            "capabilities": ["multi_keyframe_up_to_16", "modify_video", "up_to_20s", "1080p", "hdr_exr", "official_api"],
            "notes": "与 Ray3/Ray3.14 分版本记录；输入组合仍由 model×channel 能力图限制。",
        },
        {
            "name": "Seedance 2.0",
            "legacy": True,
            "capabilities": ["legacy_compatibility_only"],
            "notes": "旧项目原值；新项目主菜单使用 2.5，绝不静默改旧收据。",
        },
        {
            "name": "manual",
            "capabilities": ["human_registered"],
            "notes": "人工/网页/外包登记路径，必须留来源、参数和挑版理由。",
        },
    ],
    "video_channels": [
        {"name": "即梦/Dreamina", "integration": "manual_web", "official_api": False,
         "models": {"Seedance 2.5": "available"}},
        {"name": "豆包", "integration": "manual_web", "official_api": False,
         "models": {"Seedance 2.5": "available"}},
        {"name": "火山方舟/Volcengine API", "integration": "api", "official_api": True,
         "models": {"Seedance 2.5": "api_pending"}},
        {"name": "Google Gemini API", "integration": "api", "official_api": True,
         "models": {"Veo 3.1": "available", "Gemini Omni Flash Preview": "adapter_required"}},
        {"name": "Runway API", "integration": "api", "official_api": True},
        {"name": "可灵/Kling", "integration": "api_or_web", "official_api": True},
        {"name": "Luma Dream Machine", "integration": "api_or_web", "official_api": True},
        {"name": "本地/开源", "integration": "local", "official_api": False},
        {"name": "manual", "integration": "manual", "official_api": False},
    ],
    "image_backends": [
        {"name": "GPT Image 2", "channels": ["Codex", "OpenAI API"], "high_fidelity_image_inputs": True},
        {"name": "Seedream 5.0 Lite", "channels": ["火山方舟/Seedream"], "multimodal_image_input": True},
        {"name": "Nano Banana Pro (Gemini 3 Pro Image)", "channels": ["Google Gemini API"], "multi_reference": True, "max_standard_inputs": 14},
    ],
}


def verify_url(url, timeout=8):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "mv-refresh/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"url": url, "ok": 200 <= resp.status < 400, "status": resp.status}
    except Exception as exc:
        return {"url": url, "ok": False, "error": str(exc)}


def build_snapshot(key, as_of, verify=False, verification_mode="declared_sources_only", verification_note=""):
    source = freshness.CANDIDATE_SOURCES[key]
    checks = [verify_url(url) for url in source["source_urls"]] if verify else []
    return {
        "kind": "mv_candidate_snapshot",
        "key": key,
        "collected_at": as_of,
        "description": source["description"],
        "source_urls": source["source_urls"],
        "url_checks": checks,
        "verification_mode": "url_head" if verify else verification_mode,
        "verification_note": verification_note or None,
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
    ap.add_argument(
        "--verification-mode",
        choices=("declared_sources_only", "official_content_review"),
        default="declared_sources_only",
        help="official_content_review 仅在执行者已实际阅读官方正文后使用",
    )
    ap.add_argument("--verification-note", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    keys = args.key or sorted(freshness.CANDIDATE_SOURCES)
    for key in keys:
        payload = build_snapshot(
            key, args.as_of, verify=args.verify_url,
            verification_mode=args.verification_mode,
            verification_note=args.verification_note,
        )
        if args.dry_run:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            continue
        path = write_snapshot(args.repo, key, payload)
        print(f"[ok] refreshed {key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
