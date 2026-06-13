#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write publishing-facing AI usage metadata for a novel project.

The file is intentionally separate from export.py: not every draft is published,
but every publish/export decision should leave a clear disclosure note.

写盘/骨架统一走本线 novel/_lib/disclosure.py（vendored，本线自包含）；本线只保留专属字段与文案。
"""
import argparse
import os
import sys

_COMMON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "novel", "_lib"))
if _COMMON_DIR not in sys.path:
    sys.path.insert(0, _COMMON_DIR)
import disclosure  # noqa: E402


ALLOWED_MODES = ("AI-generated", "AI-assisted", "未使用AI文本")

NOTES = [
    "- 若文本由 AI 直接生成，即便之后做过大量人工编辑，面向需要披露的平台通常仍按 AI-generated 处理。",
    "- 若文本由人写，AI 只用于润色、纠错、头脑风暴或检查，可记录为 AI-assisted。",
    "- 发布前按目标平台最新规则复核；本文件只做项目留痕，不替代法律意见。",
]


def main():
    ap = argparse.ArgumentParser(description="写入 novel 项目的 AI 使用披露元数据")
    ap.add_argument("project_root")
    ap.add_argument("--text-mode", required=True, choices=ALLOWED_MODES)
    ap.add_argument("--image-mode", default="未使用AI图片",
                    choices=("AI-generated", "AI-assisted", "未使用AI图片"))
    ap.add_argument("--publish-target", default="未定")
    ap.add_argument("--human-contribution", default="")
    args = ap.parse_args()

    root = disclosure.resolve_root_or_exit(args.project_root)
    meta = disclosure.load_meta(root)
    payload = disclosure.base_payload(
        root, "novel_ai_usage", meta,
        title=meta.get("title") or meta.get("source_title"),
        publish_target=args.publish_target,
        human_contribution=args.human_contribution,
    )
    payload.update({
        "rights_status": meta.get("rights_status", "unknown"),
        "text_mode": args.text_mode,
        "image_mode": args.image_mode,
    })
    field_lines = [
        f"- 文本使用类型：{payload['text_mode']}",
        f"- 图片/封面使用类型：{payload['image_mode']}",
        f"- 发布平台/用途：{payload['publish_target']}",
        f"- 权利来源：{payload['rights_status']}",
    ]
    _, md_path = disclosure.write(
        root, payload,
        md_title=f"AI 使用说明 — {payload['title']}",
        field_lines=field_lines,
        notes=NOTES,
        contribution_placeholder="（待填写：创意、蓝图、设定、章纲、人工改写、审稿取舍等）",
    )
    print(f"[ok] AI 使用披露：{md_path}")


if __name__ == "__main__":
    main()
