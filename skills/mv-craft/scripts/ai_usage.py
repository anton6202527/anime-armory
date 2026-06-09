#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write publishing-facing AI usage metadata for an MV project."""
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
        f"# AI 使用说明 — MV《{payload['title']}》",
        "",
        f"- 生成日期：{payload['generated_at']}",
        f"- 项目：{payload['project_root']}",
        f"- 输入歌权利状态：{payload['song_rights_status']}",
        f"- 视觉素材使用类型：{payload['visual_mode']}",
        f"- 视频素材使用类型：{payload['video_mode']}",
        f"- 生图后端：{payload['image_backend']}",
        f"- 生视频后端：{payload['video_backend']}",
        f"- 换脸/真人肖像：{payload['faceswap_status']}",
        f"- 水印 / AI 标识：{payload['watermark_status']}",
        f"- 发布平台/用途：{payload['publish_target']}",
        "",
        "## 人工贡献记录",
        payload["human_contribution"] or "（待填写：视觉蓝图、定妆选择、分镜取舍、视频挑版、剪辑审片、字幕校正等）",
        "",
        "## 说明",
        "- 若 MV 的图像或视频主要由 AI 生成，通常按 AI-generated 留痕。",
        "- 使用真人肖像、换脸或真实人物风格时，需记录授权；未授权不得用于投放。",
        "- 发布前按目标平台最新规则复核 AI 标识、水印、版权和音乐授权；本文件只做项目留痕，不替代法律意见。",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


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

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)
    meta = load_json(os.path.join(root, "_meta.json"), {})
    payload = {
        "schema_version": 1,
        "kind": "mv_ai_usage",
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "title": meta.get("title") or os.path.basename(root),
        "song_rights_status": meta.get("song_rights_status") or meta.get("rights_status") or "unknown",
        "visual_mode": args.visual_mode,
        "video_mode": args.video_mode,
        "image_backend": meta.get("image_backend") or "未记录",
        "video_backend": meta.get("video_backend") or "未记录",
        "faceswap_status": args.faceswap_status,
        "watermark_status": args.watermark_status,
        "publish_target": args.publish_target,
        "human_contribution": args.human_contribution,
    }
    compliance_dir = os.path.join(root, "合规")
    write_json(os.path.join(compliance_dir, "ai_usage.json"), payload)
    write_markdown(os.path.join(compliance_dir, "AI使用说明.md"), payload)
    print(f"[ok] AI 使用披露：{os.path.join(compliance_dir, 'AI使用说明.md')}")


if __name__ == "__main__":
    main()
