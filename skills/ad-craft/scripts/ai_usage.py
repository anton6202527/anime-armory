#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write publishing-facing AI usage + 授权 disclosure for an ad (拍广告) project.

广告投放对 AI 标识、肖像/音乐/字体/素材授权、广告法 claim 留痕要求比一般视频更严。
本脚本只做项目留痕，不替代法律意见；完整合规清单留给二期 `ad-compliance`。
"""
import argparse
import json
import os
import sys
from datetime import date

from contract import AI_VISUAL_USAGE_MODES


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_markdown(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        f"# AI 使用 + 授权说明 — 广告《{payload['title']}》",
        "",
        f"- 生成日期：{payload['generated_at']}",
        f"- 项目：{payload['project_root']}",
        f"- 品牌 / 广告主：{payload['brand']}",
        f"- 视觉素材使用类型：{payload['visual_mode']}",
        f"- 视频素材使用类型：{payload['video_mode']}",
        f"- 生图后端：{payload['image_backend']}",
        f"- 生视频后端：{payload['video_backend']}",
        f"- 配音 / 旁白来源：{payload['voice_status']}",
        f"- 音乐来源 / 授权：{payload['music_status']}",
        f"- 代言人 / 真人肖像授权：{payload['talent_status']}",
        f"- 字体 / 第三方素材授权：{payload['asset_status']}",
        f"- 水印 / AI 标识：{payload['watermark_status']}",
        f"- 广告法地区：{payload['adlaw_region']}",
        f"- 投放平台 / 用途：{payload['publish_target']}",
        "",
        "## 人工贡献记录",
        payload["human_contribution"] or "（待填写：创意策划、脚本、分镜取舍、定妆选择、视频挑版、剪辑包装、字幕校正等）",
        "",
        "## 说明",
        "- 广告若图像/视频主要由 AI 生成，通常按 AI-generated 留痕，并按目标平台规则打 AI 标识。",
        "- 代言人肖像 / 真人声音 / 授权音乐 / 商业字体均需可追溯授权；未授权不得投放。",
        "- 广告语 claim（功效、对比、数据）须有依据；绝对化用语等违禁词由 `ad-script/ad_law_check.py` 机检拦截。",
        "- 本文件只做项目留痕，不替代法律意见；完整合规清单见二期 `ad-compliance`。",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


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

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)
    meta = load_json(os.path.join(root, "_meta.json"), {})
    payload = {
        "schema_version": 1,
        "kind": "ad_ai_usage",
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "title": meta.get("title") or os.path.basename(root),
        "brand": meta.get("brand") or "未记录",
        "visual_mode": args.visual_mode,
        "video_mode": args.video_mode,
        "image_backend": meta.get("image_backend") or "未记录",
        "video_backend": meta.get("video_backend") or "未记录",
        "voice_status": args.voice_status,
        "music_status": args.music_status,
        "talent_status": args.talent_status,
        "asset_status": args.asset_status,
        "watermark_status": args.watermark_status,
        "adlaw_region": meta.get("adlaw_region") or "中国大陆",
        "publish_target": args.publish_target,
        "human_contribution": args.human_contribution,
    }
    compliance_dir = os.path.join(root, "合规")
    write_json(os.path.join(compliance_dir, "ai_usage.json"), payload)
    write_markdown(os.path.join(compliance_dir, "AI使用说明.md"), payload)
    print(f"[ok] AI 使用披露：{os.path.join(compliance_dir, 'AI使用说明.md')}")


if __name__ == "__main__":
    main()
