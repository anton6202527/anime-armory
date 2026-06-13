#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write publishing-facing AI usage metadata for an MV project.

写盘/骨架统一走本线 mv/_lib/disclosure.py（vendored，本线自包含）；本线只保留专属字段与文案。
"""
import argparse
import os
import sys

_COMMON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "mv", "_lib"))
if _COMMON_DIR not in sys.path:
    sys.path.insert(0, _COMMON_DIR)
import disclosure  # noqa: E402  vendored 进 mv/_lib

from contract import AI_VISUAL_USAGE_MODES  # noqa: E402

NOTES = [
    "- 若 MV 的图像或视频主要由 AI 生成，通常按 AI-generated 留痕。",
    "- 使用真人肖像、换脸或真实人物风格时，需记录授权；未授权不得用于投放。",
    "- 发布前按目标平台最新规则复核 AI 标识、水印、版权和音乐授权；本文件只做项目留痕，不替代法律意见。",
]


def main():
    ap = argparse.ArgumentParser(description="写入 MV 项目的 AI 视觉使用披露元数据")
    ap.add_argument("project_root")
    ap.add_argument("--visual-mode", required=True, choices=AI_VISUAL_USAGE_MODES)
    ap.add_argument("--video-mode", default="AI-generated", choices=AI_VISUAL_USAGE_MODES)
    ap.add_argument("--publish-target", default="未定")
    ap.add_argument("--faceswap-status", default="未使用")
    ap.add_argument("--watermark-status", default="未记录")
    ap.add_argument("--human-contribution", default="")
    args = ap.parse_args()

    root = disclosure.resolve_root_or_exit(args.project_root)
    meta = disclosure.load_meta(root)
    payload = disclosure.base_payload(
        root, "mv_ai_usage", meta,
        publish_target=args.publish_target,
        human_contribution=args.human_contribution,
    )
    payload.update({
        "song_rights_status": meta.get("song_rights_status") or meta.get("rights_status") or "unknown",
        "visual_mode": args.visual_mode,
        "video_mode": args.video_mode,
        "image_backend": meta.get("image_backend") or "未记录",
        "video_model": meta.get("video_model") or "未记录",
        "video_channel": meta.get("video_channel") or meta.get("video_backend") or "未记录",
        "video_backend": meta.get("video_backend") or "未记录",
        "faceswap_status": args.faceswap_status,
        "watermark_status": args.watermark_status,
    })
    field_lines = [
        f"- 输入歌权利状态：{payload['song_rights_status']}",
        f"- 视觉素材使用类型：{payload['visual_mode']}",
        f"- 视频素材使用类型：{payload['video_mode']}",
        f"- 生图后端：{payload['image_backend']}",
        f"- 生视频模型：{payload['video_model']}",
        f"- 生视频渠道：{payload['video_channel']}",
        f"- 换脸/真人肖像：{payload['faceswap_status']}",
        f"- 水印 / AI 标识：{payload['watermark_status']}",
        f"- 发布平台/用途：{payload['publish_target']}",
    ]
    _, md_path = disclosure.write(
        root, payload,
        md_title=f"AI 使用说明 — MV《{payload['title']}》",
        field_lines=field_lines,
        notes=NOTES,
        contribution_placeholder="（待填写：视觉蓝图、定妆选择、分镜取舍、视频挑版、剪辑审片、字幕校正等）",
    )
    print(f"[ok] AI 使用披露：{md_path}")


if __name__ == "__main__":
    main()
