#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write publishing-facing AI usage metadata for a novel project.

The file is intentionally separate from export.py: not every draft is published,
but every publish/export decision should leave a clear disclosure note.

写盘/骨架统一走本线 novel/_lib/disclosure.py（vendored，本线自包含）；本线只保留专属字段与文案。
"""
import argparse
import glob
import os
import re
import sys

_COMMON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if _COMMON_DIR not in sys.path:
    sys.path.insert(0, _COMMON_DIR)
import disclosure  # noqa: E402


ALLOWED_MODES = ("AI-generated", "AI-assisted", "未使用AI文本")
TRANSLATION_MODES = ("AI-generated", "AI-assisted", "未使用AI翻译", "不适用")
TEXT_DIRECTNESS_MODES = (
    "direct_generation",
    "outline_to_draft",
    "revision_only",
    "brainstorming_only",
    "none",
)
REPLACEABILITY_MODES = (
    "replaceable",
    "assistive_non_replaceable",
    "human_primary",
    "unknown",
)
DIRECT_INCORPORATION_MODES = (
    "none",
    "minor_phrases",
    "substantial_passages",
    "full_draft",
)
CHAPTER_USAGE_MODES = (
    "human_written",
    "AI-assisted",
    "AI-generated",
    "human_revised_ai_draft",
    "unknown",
)

NOTES = [
    "- `text_authorship_mode` 记录正文主创责任：人类主创 / AI辅助 / AI生成。它比 text_mode 更贴近投稿风险判断。",
    "- 若文本由 AI 直接生成，即便之后做过大量人工编辑，面向需要披露的平台通常仍按 AI-generated 处理。",
    "- 若文本由人写，AI 只用于润色、纠错、头脑风暴或检查，可记录为 AI-assisted。",
    "- disclosure_detail 记录 AI 介入的直接程度、人类 steering、可替代性、直接纳入程度与复核步骤，便于按平台/读者要求生成更细披露。",
    "- 发布前按目标平台最新规则复核；本文件只做项目留痕，不替代法律意见。",
]


def default_directness(text_mode):
    if text_mode == "AI-generated":
        return "direct_generation"
    if text_mode == "AI-assisted":
        return "revision_only"
    return "none"


def default_authorship_mode(text_mode):
    if text_mode == "AI-generated":
        return "AI生成"
    if text_mode == "AI-assisted":
        return "AI辅助"
    return "人类主创"


def chapter_number_from_path(path):
    match = re.search(r"第0*(\d+)章", os.path.basename(path))
    return int(match.group(1)) if match else None


def parse_chapter_mode(spec):
    if ":" not in spec:
        raise argparse.ArgumentTypeError("--chapter-mode 格式应为 NN:mode")
    raw_chapter, mode = spec.split(":", 1)
    try:
        chapter = int(raw_chapter)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--chapter-mode 章节必须是数字") from exc
    if mode not in CHAPTER_USAGE_MODES:
        raise argparse.ArgumentTypeError(f"unsupported chapter usage mode: {mode}")
    return chapter, mode


def build_chapter_usage(root, *, default_mode="", chapter_modes=None):
    explicit = dict(chapter_modes or [])
    rows = []
    for path in sorted(glob.glob(os.path.join(root, "章节", "第*.md"))):
        chapter = chapter_number_from_path(path)
        if chapter is None:
            continue
        mode = explicit.get(chapter) or default_mode
        if not mode:
            continue
        rows.append({
            "chapter": chapter,
            "path": os.path.relpath(path, root).replace(os.sep, "/"),
            "usage_mode": mode,
            "human_review_required": mode in {"AI-assisted", "AI-generated", "human_revised_ai_draft"},
            "note": "",
        })
    for chapter, mode in explicit.items():
        if not any(row["chapter"] == chapter for row in rows):
            rows.append({
                "chapter": chapter,
                "path": "",
                "usage_mode": mode,
                "human_review_required": mode in {"AI-assisted", "AI-generated", "human_revised_ai_draft"},
                "note": "章节文件未找到，作为计划/补录记录保留。",
            })
    rows.sort(key=lambda item: item["chapter"])
    return rows


def main():
    ap = argparse.ArgumentParser(description="写入 novel 项目的 AI 使用披露元数据")
    ap.add_argument("project_root")
    ap.add_argument("--text-mode", required=True, choices=ALLOWED_MODES)
    ap.add_argument("--image-mode", default="未使用AI图片",
                    choices=("AI-generated", "AI-assisted", "未使用AI图片"))
    ap.add_argument("--translation-mode", default="不适用", choices=TRANSLATION_MODES,
                    help="译文是否由 AI 生成/辅助；KDP 把 AI-generated 译文纳入披露范围")
    ap.add_argument("--publish-target", default="未定")
    ap.add_argument("--text-authorship-mode", choices=("人类主创", "AI辅助", "AI生成"),
                    help="正文主创责任模式；缺省按 --text-mode 推断")
    ap.add_argument("--human-contribution", default="")
    ap.add_argument("--text-directness", choices=TEXT_DIRECTNESS_MODES,
                    help="AI 介入文本成品的直接程度；缺省按 text-mode 推断")
    ap.add_argument("--human-steering", default="",
                    help="人工如何设定目标、蓝图、取舍和最终责任")
    ap.add_argument("--replaceability", choices=REPLACEABILITY_MODES, default="unknown",
                    help="AI 工作是否替代核心作者劳动")
    ap.add_argument("--direct-incorporation", choices=DIRECT_INCORPORATION_MODES,
                    default="none", help="AI 输出被直接纳入成品文本的程度")
    ap.add_argument("--review-step", action="append", default=[],
                    help="复核步骤，可重复，如 人工通读/设定一致性审稿/平台合规复核")
    ap.add_argument("--default-chapter-mode", choices=CHAPTER_USAGE_MODES, default="",
                    help="给当前 章节/第*.md 默认写入逐章 AI 使用模式")
    ap.add_argument("--chapter-mode", type=parse_chapter_mode, action="append", default=[],
                    help="逐章覆盖 AI 使用模式，格式 NN:mode，例如 1:human_written")
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
        "text_authorship_mode": args.text_authorship_mode or default_authorship_mode(args.text_mode),
        "image_mode": args.image_mode,
        "translation_mode": args.translation_mode,
        "disclosure_detail": {
            "text_directness": args.text_directness or default_directness(args.text_mode),
            "human_steering": args.human_steering or args.human_contribution,
            "replaceability": args.replaceability,
            "direct_incorporation": args.direct_incorporation,
            "review_steps": args.review_step,
        },
        "chapter_usage": build_chapter_usage(
            root,
            default_mode=args.default_chapter_mode,
            chapter_modes=args.chapter_mode,
        ),
    })
    field_lines = [
        f"- 文本使用类型：{payload['text_mode']}",
        f"- 正文主创模式：{payload['text_authorship_mode']}",
        f"- 图片/封面使用类型：{payload['image_mode']}",
        f"- 翻译使用类型：{payload['translation_mode']}",
        f"- 发布平台/用途：{payload['publish_target']}",
        f"- 权利来源：{payload['rights_status']}",
        f"- AI 介入直接程度：{payload['disclosure_detail']['text_directness']}",
        f"- AI 输出直接纳入：{payload['disclosure_detail']['direct_incorporation']}",
        f"- 可替代性判断：{payload['disclosure_detail']['replaceability']}",
    ]
    if payload["disclosure_detail"].get("human_steering"):
        field_lines.append(f"- 人工 steering：{payload['disclosure_detail']['human_steering']}")
    if payload["disclosure_detail"].get("review_steps"):
        field_lines.append("- 复核步骤：" + "、".join(payload["disclosure_detail"]["review_steps"]))
    if payload.get("chapter_usage"):
        field_lines.append(f"- 逐章 AI 使用记录：{len(payload['chapter_usage'])} 章")
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
