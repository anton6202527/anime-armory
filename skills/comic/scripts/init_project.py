#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""画漫画项目初始化脚手架。

创建 `创作区/画漫画/作品名/` 的轻量 MVP 目录、设置、进度和第1话占位文件。
脚本只用标准库，不绑定任何生成后端。
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import uuid
from datetime import date
from pathlib import Path


COMIC_ROOT = Path(__file__).resolve().parents[1]
if str(COMIC_ROOT) not in sys.path:
    sys.path.insert(0, str(COMIC_ROOT))
from _lib.settings import PRODUCTION_PROFILE_PRESETS  # noqa: E402


MODES = ("原创漫画", "源本改漫画", "脚本改漫画")
FORMATS = ("条漫", "页漫", "四格", "分镜稿")

SUBDIRS = (
    "源本",
    "设定库",
    "脚本/第1话",
    "排版/第1话/name",
    "排版/第1话/pages",
    "排版/第1话/长图",
    "出图/共享/prompt",
    "出图/共享/图片",
    "出图/封面/prompt",
    "出图/第1话/prompt",
    "出图/第1话/panels",
    "出图/第1话/finishing",
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


def extract_synopsis(bible_text: str, *, max_len: int = 240) -> str:
    """从故事圣经的「一句话核心」小节提取作品简介。

    立项当刻该小节通常仍是空占位（``- ``），此时返回空串；后续创作阶段
    在圣经里补齐核心后，重跑确定性回填即可把简介写入 ``_meta.json``。
    只读本线自有产物，不跨线取数（见封面与简介契约 §3）。
    """
    lines = bible_text.splitlines()
    collecting = False
    picked: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            if collecting:
                break
            collecting = stripped.lstrip("#").strip() == "一句话核心"
            continue
        if not collecting:
            continue
        item = stripped.lstrip("-*").strip()
        if item:
            picked.append(item)
    text = " ".join(picked).strip()
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text


def settings_markdown(title: str, args: argparse.Namespace) -> str:
    return f"""# 设置 — 画漫画《{title}》

## 选择点
- 生产档位: {args.production_profile}
- 输入模式: {args.mode}
- 漫画形态: {args.format}
- 阅读方向: {args.reading_direction}
- 目标平台: {args.platform}
- 页面尺寸: {args.page_size}
- 单话分段高度: {args.max_segment_height}
- 传统原稿流程: {args.traditional_workflow}
- 出图稿层: {args.render_stage}
- 原稿规格: {args.manuscript_spec}
- 版式模板策略: {args.name_strategy}
- 审阅策略: {args.review_strategy}
- 网点策略: {args.tone_strategy}
- 效果线策略: {args.effects_strategy}
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


TRADITIONAL_OFF_VALUES = {"关闭", "off", "disabled", "false", "False"}


def traditional_enabled(value: str) -> bool:
    return str(value or "").strip() not in TRADITIONAL_OFF_VALUES


def progress_markdown(title: str, args: argparse.Namespace, source_ready: bool) -> str:
    # A copied source file (or original mode) is not an approved development
    # pack.  Init must never pre-claim the source/planning gate as complete.
    source_status = "🟡素材已入库" if source_ready else "⬜"
    stages = ["源本/企划", "漫画脚本", "缩略分镜", "页面排版", "原稿收尾", "出图包", "出图", "嵌字合成", "审查"]
    if not traditional_enabled(args.traditional_workflow):
        # 缩略分镜/name board 是所有漫画形态的页流与阅读顺序合同；
        # 关闭“传统原稿流程”只能跳过墨线/网点/效果线收尾。
        stages = [s for s in stages if s != "原稿收尾"]
    header = "| 话 | " + " | ".join(stages) + " |"
    divider = "|" + "---|" * (len(stages) + 1)
    row = "| 第1话 | " + " | ".join(source_status if s == "源本/企划" else "⬜" for s in stages) + " |"
    return f"""# 进度 — 画漫画《{title}》

> 输入模式={args.mode} 漫画形态={args.format} 阅读方向={args.reading_direction}

## 章节流程
{header}
{divider}
{row}

## 导出
- [ ] 第1话 页面图
- [ ] 第1话 长图
- [ ] 第1话 export_manifest.json

## 作品封面
- [ ] 竖版封面 prompt/job 包（出图/封面/prompt/cover_job.json）
- [ ] 竖版封面 PNG 渲染并回填 _meta.json cover
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

> 角色标题合同为 `### 人读名称 CHAR_STABLE_ID`。确定真实姓名后同步改名并用 `comic-identity` 登记；不要把待定 ID 标成 ready。

### 待定主角 CHAR_TBD_PROTAGONIST
- 角色定位：
- 角色 DNA（脸型/五官/发型/体态/标志物）：
- 禁漂移项：

### 待定对手 CHAR_TBD_ANTAGONIST
- 角色定位：
- 角色 DNA（脸型/五官/发型/体态/标志物）：
- 禁漂移项：

### 待定关键配角 CHAR_TBD_SUPPORTING
- 角色定位：
- 角色 DNA（脸型/五官/发型/体态/标志物）：
- 禁漂移项：

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
        "schema_version": 2,
        "kind": "comic_panel_script",
        "title": title,
        "chapter": "第1话",
        "status": "draft",
        "chapter_contract": {
            "path": "脚本/split_blueprint.json",
            "chapter_contract_sha256": "",
            "status": "draft",
        },
        "source_semantics": {
            "path": "脚本/第1话/source_semantics.json",
            "requires_normalization": False,
            "source_language": "",
            "target_text_language": "",
            "target_text_metadata": {},
            "status": "pass",
        },
        "panels": [
            {
                "panel_id": "P001",
                "story_function": "opening_hook",
                "source_excerpt": "",
                "meaning_zh": "",
                "text_target": "",
                "adaptation_note": "",
                "description": "待补：首格画面",
                "characters": [],
                "character_bindings": [],
                "source_segment_refs": [],
                "location": "",
                "dialogue": [],
                "narration": "",
                "sfx": [],
                "art_notes": "",
                "layout_weight": "heavy",
                "panel_shape": "full_width",
                "border_style": "standard",
                "gutter_intent": "opening pause",
                "ink_plan": "clean outer contour, readable face/hands/props, solid black only where it supports focal contrast",
                "tone_plan": "style-driven tones or grayscale; keep text-safe areas low detail",
                "effects_plan": "use action/focus/speed lines only when they clarify motion or impact",
                "references": [],
            }
        ],
    }


def identity_registry() -> dict:
    """Return an honest, empty schema-v2 registry for a new project.

    The initializer must not invent characters, assets, reference images or
    approval state.  Identity registration/upsert remains owned by
    ``comic-identity`` after the development pack names stable subjects.
    """
    return {
        "schema_version": 2,
        "kind": "comic_identity_registry",
        "assets": {},
        "schema_meta": {
            "initialized_at": date.today().isoformat(),
            "initialized_by": "comic init_project bootstrap",
        },
    }


PAPER_SIZES_300_DPI = {
    "A4": (2480, 3508),
    "B5": (2079, 2953),
}


def resolve_page_dimensions(value: str, comic_format: str) -> tuple[int, int]:
    """Resolve named paper or numeric canvas values without crashing init.

    `_设置.md` explicitly allows A4/B5, while the old initializer attempted
    `int("B5")`.  Named sizes use 300 dpi production dimensions; `auto` keeps
    the historic long-strip height for strips and a 1:1.42 page ratio for
    paged formats.
    """
    raw = str(value or "").strip()
    named = PAPER_SIZES_300_DPI.get(raw.upper())
    if named:
        return named
    match = re.fullmatch(r"\s*(\d+)\s*x\s*(\d+|auto)\s*", raw, re.I)
    if not match:
        raise ValueError(f"unsupported page size: {value!r}; use A4, B5, WIDTHxHEIGHT, or WIDTHxauto")
    width = int(match.group(1))
    height_token = match.group(2).lower()
    if height_token != "auto":
        return width, int(height_token)
    if comic_format in {"页漫", "四格"}:
        return width, round(width * 1.42)
    return width, 1800


def layout_json(args: argparse.Namespace) -> dict:
    width, height = resolve_page_dimensions(args.page_size, args.format)
    is_paged = args.format in {"页漫", "四格"}
    bleed = max(24, width // 32) if is_paged else 0
    safe = max(72, width // 15) if is_paged else 72
    return {
        "schema_version": 1,
        "kind": "comic_layout",
        "chapter": "第1话",
        "format": args.format,
        "reading_direction": args.reading_direction,
        "geometry_profile": "page_placeholder_manual_required" if is_paged else "longstrip_placeholder",
        "format_supported_by_script": not is_paged,
        "manual_layout_required": is_paged,
        "manuscript": {
            "spec": args.manuscript_spec,
            "trim_box": {"x": 0, "y": 0, "w": width, "h": height},
            "safe_area": {"x": safe, "y": safe, "w": width - safe * 2, "h": height - safe * 2},
            "bleed": bleed,
        },
        "canvas": {"width": width, "height": height if is_paged else "auto"},
        "segments": [
            {
                "segment_id": "PAGE_001" if is_paged else "S001",
                "width": width,
                "height": height,
                "panels": [
                    {
                        "panel_id": "P001",
                        "x": safe if is_paged else 0,
                        "y": safe if is_paged else 0,
                        "w": width - safe * 2 if is_paged else width,
                        "h": height - safe * 2 if is_paged else 900,
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
    parser.add_argument("--traditional-workflow", default=None)
    parser.add_argument("--render-stage", default=None)
    parser.add_argument("--manuscript-spec", default="数字条漫")
    parser.add_argument("--name-strategy", default="自动缩略分镜")
    parser.add_argument("--review-strategy", default="用户授权制作代理")
    parser.add_argument("--tone-strategy", default="风格驱动")
    parser.add_argument("--effects-strategy", default="剧情驱动")
    parser.add_argument("--visual-style", default="彩色国漫条漫")
    parser.add_argument("--style-anchor", default="未指定")
    parser.add_argument("--image-model", default="GPT Image 2")
    parser.add_argument("--image-channel", default="Codex CLI")
    parser.add_argument("--image-ai", default="Codex")
    parser.add_argument("--production-profile", choices=tuple(PRODUCTION_PROFILE_PRESETS), default="连载标准")
    parser.add_argument("--consistency", default=None)
    parser.add_argument("--identity-level", default=None)
    parser.add_argument("--age-variant-inheritance", default=None)
    parser.add_argument("--identity-hard-gate", default=None)
    parser.add_argument("--text-language", default="中文")
    parser.add_argument("--lettering", default="后期嵌字")
    parser.add_argument("--export-format", default="webp+png")
    parser.add_argument("--region", default="未指定")
    parser.add_argument("--usage", default="demo学习")
    args = parser.parse_args()

    preset = PRODUCTION_PROFILE_PRESETS[args.production_profile]
    linked_args = {
        "traditional_workflow": "传统原稿流程",
        "render_stage": "出图稿层",
        "consistency": "参考一致性策略",
        "identity_level": "定妆级别",
        "age_variant_inheritance": "年龄形态继承",
        "identity_hard_gate": "角色一致性硬闸",
    }
    fallbacks = {
        "traditional_workflow": "启用",
        "render_stage": "完成稿",
        "consistency": "共享参考图",
        "identity_level": "长线专门定妆",
        "age_variant_inheritance": "开启",
        "identity_hard_gate": "开启",
    }
    for attr, setting_key in linked_args.items():
        if getattr(args, attr) is None:
            setattr(args, attr, preset.get(setting_key, fallbacks[attr]))

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

    write_if_absent(root / "_设置.md", settings_markdown(title, args))
    write_if_absent(root / "_进度.md", progress_markdown(title, args, source_ready))
    write_if_absent(root / "设定库" / "story_bible.md", story_bible(title, args))

    # synopsis 取自本线已有产物 story_bible.md 的「一句话核心」。write_if_absent
    # 尊重用户既有圣经，因此从磁盘上真正的文件（用户版或刚生成的占位）取数。
    # 立项当刻该小节多为空，synopsis 先落空串，后续阶段确定性回填。
    bible_path = root / "设定库" / "story_bible.md"
    synopsis = ""
    if bible_path.is_file():
        synopsis = extract_synopsis(bible_path.read_text(encoding="utf-8"))

    meta = {
        "schema_version": 1,
        "kind": "comic_project",
        "project_id": f"comic_{uuid.uuid4().hex[:16]}",
        "line": "comic",
        "title": title,
        "created": date.today().isoformat(),
        "mode": args.mode,
        "format": args.format,
        "source": source_record,
        # 作品卡片字段：synopsis=一句话简介，cover=作品级竖版封面相对路径。
        # cover 立项恒为 null，只有真正渲染出竖版 PNG 后由 build_cover_job.py
        # --backfill 确定性回填；纯净机上封面步骤只产 prompt/job 包 + 合规留痕。
        "synopsis": synopsis,
        "cover": None,
        "rights": {
            "source_status": "original_or_user_provided",
            "font_status": "pending_before_publish",
            "asset_status": "pending_before_publish",
        },
    }

    write_if_absent(root / "脚本" / "第1话" / "分话大纲.md", outline(title))
    write_if_absent(root / "脚本" / "第1话" / "panel_script.json", json.dumps(panel_script(title), ensure_ascii=False, indent=2) + "\n")
    write_if_absent(root / "出图" / "共享" / "identity_registry.json", json.dumps(identity_registry(), ensure_ascii=False, indent=2) + "\n")
    # Layout is a downstream approved production artifact.  Do not seed a
    # plausible-looking placeholder before script/name approval: old projects
    # could mistake that file for completed geometry and only fail near image
    # generation.  ``layout_json()`` remains available for migration/tests,
    # while the normal initializer leaves layout creation to comic-layout.
    write_if_absent(root / "排版" / "第1话" / "lettering.json", json.dumps({"schema_version": 1, "kind": "comic_lettering", "chapter": "第1话", "items": []}, ensure_ascii=False, indent=2) + "\n")
    write_if_absent(root / "_meta.json", json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    write_if_absent(root / "生产数据" / "artifact_catalog.json", json.dumps({
        "schema_version": 1, "kind": "artifact_catalog", "status": "bootstrap",
        "generated_at": date.today().isoformat(),
        "project": {"project_id": meta["project_id"], "line": "comic", "title": title, "root_rel": "."},
        "summary": {"artifact_count": 0, "total_bytes": 0, "disposable_bytes": 0, "invalid_count": 0},
        "event_sources": [], "view_sources": [], "artifacts": [], "duplicates": [],
    }, ensure_ascii=False, indent=2) + "\n")

    print(f"\n[done] 画漫画项目已初始化：{root}")
    print("下一步：comic-script 补齐开发包、chapter_contract、故事圣经和 panel_script.json；通过后再做缩略分镜/name board 与排版。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
