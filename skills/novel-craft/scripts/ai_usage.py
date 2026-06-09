#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write publishing-facing AI usage metadata for a novel project.

The file is intentionally separate from export.py: not every draft is published,
but every publish/export decision should leave a clear disclosure note.
"""
import argparse
import json
import os
import sys
from datetime import date


ALLOWED_MODES = ("AI-generated", "AI-assisted", "未使用AI文本")


def load_meta(root):
    path = os.path.join(root, "_meta.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_markdown(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        f"# AI 使用说明 — {payload['title']}",
        "",
        f"- 生成日期：{payload['generated_at']}",
        f"- 项目：{payload['project_root']}",
        f"- 文本使用类型：{payload['text_mode']}",
        f"- 图片/封面使用类型：{payload['image_mode']}",
        f"- 发布平台/用途：{payload['publish_target']}",
        f"- 权利来源：{payload['rights_status']}",
        "",
        "## 人工贡献记录",
        payload["human_contribution"] or "（待填写：创意、蓝图、设定、章纲、人工改写、审稿取舍等）",
        "",
        "## 说明",
        "- 若文本由 AI 直接生成，即便之后做过大量人工编辑，面向需要披露的平台通常仍按 AI-generated 处理。",
        "- 若文本由人写，AI 只用于润色、纠错、头脑风暴或检查，可记录为 AI-assisted。",
        "- 发布前按目标平台最新规则复核；本文件只做项目留痕，不替代法律意见。",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description="写入 novel 项目的 AI 使用披露元数据")
    ap.add_argument("project_root")
    ap.add_argument("--text-mode", required=True, choices=ALLOWED_MODES)
    ap.add_argument("--image-mode", default="未使用AI图片",
                    choices=("AI-generated", "AI-assisted", "未使用AI图片"))
    ap.add_argument("--publish-target", default="未定")
    ap.add_argument("--human-contribution", default="")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)
    meta = load_meta(root)
    payload = {
        "schema_version": 1,
        "kind": "novel_ai_usage",
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "title": meta.get("title") or meta.get("source_title") or os.path.basename(root),
        "rights_status": meta.get("rights_status", "unknown"),
        "text_mode": args.text_mode,
        "image_mode": args.image_mode,
        "publish_target": args.publish_target,
        "human_contribution": args.human_contribution,
    }
    compliance_dir = os.path.join(root, "合规")
    write_json(os.path.join(compliance_dir, "ai_usage.json"), payload)
    write_markdown(os.path.join(compliance_dir, "AI使用说明.md"), payload)
    print(f"[ok] AI 使用披露：{os.path.join(compliance_dir, 'AI使用说明.md')}")


if __name__ == "__main__":
    main()
