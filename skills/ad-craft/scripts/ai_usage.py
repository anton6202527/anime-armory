#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write publishing-facing AI usage + 授权 disclosure for an ad (拍广告) project.

广告投放对 AI 标识、肖像/音乐/字体/素材授权、广告法 claim 留痕要求比一般视频更严。
本脚本只做项目留痕，不替代法律意见；完整合规清单留给二期 `ad-compliance`。
写盘/骨架统一走本线 ad/_lib/disclosure.py（vendored，本线自包含）；本线只保留专属字段与文案。
"""
import argparse
import os
import sys

_COMMON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ad", "_lib"))
if _COMMON_DIR not in sys.path:
    sys.path.insert(0, _COMMON_DIR)
import disclosure  # noqa: E402

from contract import AI_VISUAL_USAGE_MODES  # noqa: E402

NOTES = [
    "- 广告若图像/视频主要由 AI 生成，通常按 AI-generated 留痕，并按目标平台规则打 AI 标识。",
    "- 代言人肖像 / 真人声音 / 授权音乐 / 商业字体均需可追溯授权；未授权不得投放。",
    "- 广告语 claim（功效、对比、数据）须有依据；绝对化用语等违禁词由 `ad-script/ad_law_check.py` 机检拦截。",
    "- 本文件只做项目留痕，不替代法律意见；完整合规清单见二期 `ad-compliance`。",
]


def main():
    ap = argparse.ArgumentParser(description="写入拍广告项目的 AI 使用 + 授权披露元数据")
    ap.add_argument("project_root")
    ap.add_argument("--visual-mode", required=True, choices=AI_VISUAL_USAGE_MODES)
    ap.add_argument("--video-mode", default="AI-generated", choices=AI_VISUAL_USAGE_MODES)
    ap.add_argument("--publish-target", default="未定")
    ap.add_argument("--talent-status", default="未使用真人")
    ap.add_argument("--music-status", default="未记录")
    ap.add_argument("--voice-status", default="未记录")
    ap.add_argument("--asset-status", default="未记录")
    ap.add_argument("--watermark-status", default="未记录")
    ap.add_argument("--human-contribution", default="")
    args = ap.parse_args()

    root = disclosure.resolve_root_or_exit(args.project_root)
    meta = disclosure.load_meta(root)
    payload = disclosure.base_payload(
        root, "ad_ai_usage", meta,
        publish_target=args.publish_target,
        human_contribution=args.human_contribution,
    )
    payload.update({
        "brand": meta.get("brand") or "未记录",
        "visual_mode": args.visual_mode,
        "video_mode": args.video_mode,
        "image_backend": meta.get("image_backend") or "未记录",
        "video_model": meta.get("video_model") or "未记录",
        "video_channel": meta.get("video_channel") or meta.get("video_backend") or "未记录",
        "video_backend": meta.get("video_backend") or "未记录",
        "voice_status": args.voice_status,
        "music_status": args.music_status,
        "talent_status": args.talent_status,
        "asset_status": args.asset_status,
        "watermark_status": args.watermark_status,
        "adlaw_region": meta.get("adlaw_region") or "中国大陆",
    })
    field_lines = [
        f"- 品牌 / 广告主：{payload['brand']}",
        f"- 视觉素材使用类型：{payload['visual_mode']}",
        f"- 视频素材使用类型：{payload['video_mode']}",
        f"- 生图后端：{payload['image_backend']}",
        f"- 生视频模型：{payload['video_model']}",
        f"- 生视频渠道：{payload['video_channel']}",
        f"- 配音 / 旁白来源：{payload['voice_status']}",
        f"- 音乐来源 / 授权：{payload['music_status']}",
        f"- 代言人 / 真人肖像授权：{payload['talent_status']}",
        f"- 字体 / 第三方素材授权：{payload['asset_status']}",
        f"- 水印 / AI 标识：{payload['watermark_status']}",
        f"- 广告法地区：{payload['adlaw_region']}",
        f"- 投放平台 / 用途：{payload['publish_target']}",
    ]
    _, md_path = disclosure.write(
        root, payload,
        md_title=f"AI 使用 + 授权说明 — 广告《{payload['title']}》",
        field_lines=field_lines,
        notes=NOTES,
        contribution_placeholder="（待填写：创意策划、脚本、分镜取舍、定妆选择、视频挑版、剪辑包装、字幕校正等）",
    )
    print(f"[ok] AI 使用披露：{md_path}")


if __name__ == "__main__":
    main()
