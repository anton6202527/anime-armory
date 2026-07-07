#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""画漫画项目初始化脚手架。

创建 `创作区/画漫画/作品名/` 的轻量 MVP 目录、设置、进度和第1话占位文件。
脚本只用标准库，不绑定任何生成后端。
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path


MODES = ("原创漫画", "源本改漫画", "脚本改漫画")
FORMATS = ("条漫", "页漫", "四格", "分镜稿")

SUBDIRS = (
    "源本",
    "设定库",
    "脚本/第1话",
    "排版/第1话/pages",
    "排版/第1话/长图",
    "出图/共享/prompt",
    "出图/共享/图片",
    "出图/第1话/prompt",
    "出图/第1话/panels",
    "生产数据",
    "废料",
)


def write_if_absent(path: Path, text: str) -> None:
    if path.exists():
        print(f"[skip] 已存在：{path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"[ok] {path.relative_to(path.parents[1])}")


def slug_title(value: str) -> str:
    cleaned = "".join(ch for ch in value.strip() if ch not in "\\/:*?\"<>|")
    return cleaned or "未命名漫画"


def settings_markdown(title: str, args: argparse.Namespace) -> str:
    return f"""# 设置 — 画漫画《{title}》

## 选择点
- 输入模式: {args.mode}
- 漫画形态: {args.format}
- 阅读方向: {args.reading_direction}
- 目标平台: {args.platform}
- 页面尺寸: {args.page_size}
- 单话分段高度: {args.max_segment_height}
- 基础视觉风格: {args.visual_style}
- 风格锚: {args.style_anchor}
- 生图模型: {args.image_model}
- 生图渠道: {args.image_channel}
- 生图AI: {args.image_ai}
- 参考一致性策略: {args.consistency}
- 定妆级别: {args.identity_level}
- 年龄形态继承: {args.age_variant_inheritance}
- 角色一致性硬闸: {args.identity_hard_gate}
- 文字语言: {args.text_language}
- 嵌字方式: {args.lettering}
- 导出格式: {args.export_format}
- 发行地区: {args.region}
- 合规用途: {args.usage}
"""


def progress_markdown(title: str, args: argparse.Namespace, source_ready: bool) -> str:
    source_status = "✅" if source_ready or args.mode == "原创漫画" else "⬜"
    return f"""# 进度 — 画漫画《{title}》

> 输入模式={args.mode} 漫画形态={args.format} 阅读方向={args.reading_direction}

## 章节流程
| 话 | 源本/企划 | 漫画脚本 | 页面排版 | 出图包 | 出图 | 嵌字合成 | 审查 |
|---|---|---|---|---|---|---|---|
| 第1话 | {source_status} | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |

## 导出
- [ ] 第1话 页面图
- [ ] 第1话 长图
- [ ] 第1话 export_manifest.json
"""


def story_bible(title: str, args: argparse.Namespace) -> str:
    return f"""# 故事圣经 — 《{title}》

## 项目
- 输入模式：{args.mode}
- 漫画形态：{args.format}
- 基础视觉风格：{args.visual_style}

## 一句话核心
- 

## 角色
- 主角：
- 对手：
- 关键配角：

## 世界观 / 场景
- 

## 视觉规则
- 角色脸型与发型：
- 服装与标志物：
- 场景色彩：
- 禁漂移项：
"""


def outline(title: str) -> str:
    return f"""# 分话大纲 — 《{title}》第1话

## 本话目标
- 

## 冲突与转折
- 开场钩子：
- 中段推进：
- 反转/爽点：
- 结尾钩子：

## 分格计划
- 预计格数：
- 重点大格：
- 需要共享参考的角色/场景/道具：
"""


def panel_script(title: str) -> dict:
    return {
        "schema_version": 1,
        "kind": "comic_panel_script",
        "title": title,
        "chapter": "第1话",
        "status": "draft",
        "panels": [
            {
                "panel_id": "P001",
                "story_function": "opening_hook",
                "description": "待补：首格画面",
                "characters": [],
                "location": "",
                "dialogue": [],
                "narration": "",
                "sfx": [],
                "art_notes": "",
                "references": [],
            }
        ],
    }


def layout_json(args: argparse.Namespace) -> dict:
    return {
        "schema_version": 1,
        "kind": "comic_layout",
        "chapter": "第1话",
        "format": args.format,
        "reading_direction": args.reading_direction,
        "canvas": {"width": int(args.page_size.split("x", 1)[0]), "height": "auto"},
        "segments": [
            {
                "segment_id": "S001",
                "width": int(args.page_size.split("x", 1)[0]),
                "height": 1800,
                "panels": [
                    {
                        "panel_id": "P001",
                        "x": 0,
                        "y": 0,
                        "w": int(args.page_size.split("x", 1)[0]),
                        "h": 900,
                        "bubble_slots": [],
                    }
                ],
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化画漫画项目骨架")
    parser.add_argument("project_root", help="例如 创作区/画漫画/某作品")
    parser.add_argument("--title", default=None, help="作品名；默认取目录名")
    parser.add_argument("--mode", choices=MODES, default="原创漫画")
    parser.add_argument("--format", choices=FORMATS, default="条漫")
    parser.add_argument("--source", default=None, help="可选：源本/梗概/脚本文件，复制到 源本/")
    parser.add_argument("--platform", default="通用")
    parser.add_argument("--reading-direction", default="从上到下")
    parser.add_argument("--page-size", default="1440xauto")
    parser.add_argument("--max-segment-height", default="0", help="最大分段高度；0 表示默认导出单张长图")
    parser.add_argument("--visual-style", default="彩色国漫条漫")
    parser.add_argument("--style-anchor", default="未指定")
    parser.add_argument("--image-model", default="GPT Image 2")
    parser.add_argument("--image-channel", default="Codex CLI")
    parser.add_argument("--image-ai", default="Codex")
    parser.add_argument("--consistency", default="共享参考图")
    parser.add_argument("--identity-level", default="长线专门定妆")
    parser.add_argument("--age-variant-inheritance", default="关闭")
    parser.add_argument("--identity-hard-gate", default="关闭")
    parser.add_argument("--text-language", default="中文")
    parser.add_argument("--lettering", default="后期嵌字")
    parser.add_argument("--export-format", default="webp+png")
    parser.add_argument("--region", default="未指定")
    parser.add_argument("--usage", default="demo学习")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    title = args.title or slug_title(root.name)
    if root.exists() and any(root.iterdir()):
        print(f"[err] 目标目录已存在且非空：{root}", file=sys.stderr)
        return 2

    root.mkdir(parents=True, exist_ok=True)
    for rel in SUBDIRS:
        (root / rel).mkdir(parents=True, exist_ok=True)

    source_ready = False
    source_record = None
    if args.source:
        src = Path(args.source).expanduser().resolve()
        if not src.is_file():
            print(f"[err] 源文件不存在：{src}", file=sys.stderr)
            return 2
        target = root / "源本" / src.name
        shutil.copy2(src, target)
        source_ready = True
        source_record = {"path": str(target.relative_to(root)), "original_name": src.name}
        print(f"[ok] 源本/{src.name}")

    meta = {
        "schema_version": 1,
        "kind": "comic_project",
        "title": title,
        "created": date.today().isoformat(),
        "mode": args.mode,
        "format": args.format,
        "source": source_record,
        "rights": {
            "source_status": "original_or_user_provided",
            "font_status": "pending_before_publish",
            "asset_status": "pending_before_publish",
        },
    }

    write_if_absent(root / "_设置.md", settings_markdown(title, args))
    write_if_absent(root / "_进度.md", progress_markdown(title, args, source_ready))
    write_if_absent(root / "设定库" / "story_bible.md", story_bible(title, args))
    write_if_absent(root / "脚本" / "第1话" / "分话大纲.md", outline(title))
    write_if_absent(root / "脚本" / "第1话" / "panel_script.json", json.dumps(panel_script(title), ensure_ascii=False, indent=2) + "\n")
    write_if_absent(root / "排版" / "第1话" / "layout.json", json.dumps(layout_json(args), ensure_ascii=False, indent=2) + "\n")
    write_if_absent(root / "排版" / "第1话" / "lettering.json", json.dumps({"schema_version": 1, "kind": "comic_lettering", "chapter": "第1话", "items": []}, ensure_ascii=False, indent=2) + "\n")
    write_if_absent(root / "_meta.json", json.dumps(meta, ensure_ascii=False, indent=2) + "\n")

    print(f"\n[done] 画漫画项目已初始化：{root}")
    print("下一步：comic-script 补齐故事圣经、分话大纲和 panel_script.json。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
