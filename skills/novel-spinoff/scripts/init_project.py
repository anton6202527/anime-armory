#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_project.py — 建外传项目骨架；docx → txt 抽取；调 extract_anchors 做粗筛。

用法:
    python3 init_project.py <原作路径> \
        --character "<配角名>" \
        --mode parallel|sequel|branch \
        --scale short|medium|long|微短剧|漫剧 \
        [--target-chapters N] \
        [--branch-point "第N章"] \
        [--person first|third-limited] \
        [--out <输出根>] \
        [--i-have-rights]

依赖: python-docx (仅当原作是 .docx 时)
"""
import argparse
import json
import os
import shutil
import sys
from datetime import date

# Standardized imports from novel/_lib
LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "novel", "_lib"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from novel_contract import (base_meta, build_progress_markdown, routing_stages,
                            SCALE_CHOICES, scale_profile, detect_rights_status,
                            docx_to_txt, write_project_settings, demo_chapters_for,
                            normalize_scale)

# 让本脚本能 import 同目录下 extract_anchors
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_anchors import scan_candidates, write_anchor_table


def detect_source_title(novel_path):
    base = os.path.splitext(os.path.basename(novel_path))[0]
    return base


def build_character_card_skeleton(character_name, source_title, mode):
    return f"""# 角色卡 — {character_name}

> 第 2 步由主对话填写。本骨架仅作占位。

## 来源
- 原作：{source_title}
- 模式：{mode}

## 外观

## 出身

## 能力体系

## 性格底色

## 动机 / 心结 / 渴望

## 和原作主角的关系

## 说话习惯

## 留白清单
（原作里这个角色被作者留白的部分——是续写的发力点）

- [ ] 留白 1：
- [ ] 留白 2：
- [ ] 留白 3：
"""


def build_worldview_skeleton(source_title):
    return f"""# 世界观 — 摘自《{source_title}》

> 第 2 步由主对话填写。只摘原作已确立的规则，不发明能推翻原作的新规则。

## 修炼/魔法/能力体系

## 政治 / 势力格局

## 地理

## 时间线（关键节点）

## 术语表
"""


def build_outline_skeleton(meta):
    n = meta["target_chapters"]
    if n >= 6:
        a1, a2 = max(1, n // 4), n * 3 // 4
        acts = (
            f"## 三幕结构\n"
            f"- 第一幕（约第 1 - {a1} 章）：建立配角独立世界\n"
            f"- 第二幕（约第 {a1+1} - {a2} 章）：和原作主线交汇 + 锚点密集\n"
            f"- 第三幕（约第 {a2+1} - {n} 章）：配角自己的高潮\n"
        )
    else:
        acts = "## 结构\n（短篇——围绕单一冲突推进，不强套三幕）\n"
    chapters_list = chr(10).join(f"- 第 {i:02d} 章 《》 — " for i in range(1, n + 1))
    return f"""# 章纲 — {meta['spinoff_character']}外传

> 第 3 步由主对话填写。**章纲未敲定不进第 4 步逐章写。**

## 总体弧线

{acts}
## 锚点-章节映射
（精筛完锚点表后填）

## 逐章
{chapters_list}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source_novel", help="原作 .txt 或 .docx 路径")
    ap.add_argument("--character", required=True, help="配角名")
    ap.add_argument("--mode", required=True, choices=["parallel", "sequel", "branch"])
    ap.add_argument("--scale", required=True, choices=list(SCALE_CHOICES))
    ap.add_argument("--target-chapters", type=int, default=None,
                    help="覆盖规模档默认章数")
    ap.add_argument("--branch-point", default=None, help="分叉模式必填，例：'第15章'")
    ap.add_argument("--person", default="third-limited", choices=["first", "third-limited"])
    ap.add_argument("--out", default=None, help="输出根，缺省 写小说/<原作名>-<配角名>外传/")
    ap.add_argument("--outputs", default="txt,docx,outline",
                    help="逗号分隔，可含 txt,docx,outline,n2d")
    ap.add_argument("--target-platform", default="跨平台",
                    help="目标平台（第 3 步书名候选用）：起点/晋江/抖音漫剧/番茄/红果/历史向/跨平台")
    ap.add_argument("--draft-mode", default="稳妥初稿", choices=["极速初稿", "稳妥初稿", "商业连载", "漫剧源书"],
                    help="小说生成模式：决定速度/质量 gate 密度")
    ap.add_argument("--chapter-granularity", default="逐章", choices=["逐章", "小批", "全书草稿"],
                    help="章节生成粒度：逐章/小批/全书草稿")
    ap.add_argument("--ai-text-usage", default=None, choices=["AI-generated", "AI-assisted", "未使用AI文本"],
                    help="发布披露用：AI-generated / AI-assisted / 未使用AI文本")
    ap.add_argument("--i-have-rights", action="store_true",
                    help="原作非公版时声明你有权使用")
    ap.add_argument("--rights-jurisdiction", default=None,
                    help="公版/授权依据适用辖区，如 US/CN/GLOBAL；缺省按来源推断")
    ap.add_argument("--distribution-regions", default=None,
                    help="计划发行/交付地区，逗号分隔，如 CN,US；公版跨区时必须复核")
    args = ap.parse_args()

    if args.mode == "branch" and not args.branch_point:
        print("[err] --mode branch 必须配 --branch-point", file=sys.stderr)
        sys.exit(2)

    source_path = os.path.abspath(args.source_novel)
    if not os.path.exists(source_path):
        print(f"[err] 找不到原作：{source_path}", file=sys.stderr)
        sys.exit(2)

    source_title = detect_source_title(source_path)
    project_name = f"{source_title}-{args.character}外传"
    out_root = args.out or os.path.join("写小说", project_name)
    out_root = os.path.abspath(out_root)

    if os.path.exists(out_root):
        print(f"[err] 目标已存在：{out_root}（手动备份/删除后重试）", file=sys.stderr)
        sys.exit(2)

    # 建目录
    for sub in ("设定", "章节", "导出", "写作任务", "合规"):
        os.makedirs(os.path.join(out_root, sub), exist_ok=True)

    # 原作 → txt 副本
    novel_txt = os.path.join(out_root, "原作.txt")
    ext = os.path.splitext(source_path)[1].lower()
    if ext == ".txt":
        shutil.copy(source_path, novel_txt)
    elif ext == ".docx":
        docx_to_txt(source_path, novel_txt)
    else:
        print(f"[err] 不支持的原作格式：{ext}（请 .txt 或 .docx）", file=sys.stderr)
        sys.exit(2)

    # 版权状态
    rights_status = detect_rights_status(novel_txt, args.i_have_rights)
    if rights_status == "unknown":
        print("[err] 无法判定原作版权状态。", file=sys.stderr)
        shutil.rmtree(out_root)
        sys.exit(2)

    # _meta.json
    scale = normalize_scale(args.scale)
    profile = scale_profile(scale)
    if args.target_chapters is not None:
        profile["target_chapters"] = args.target_chapters
    outputs = [s.strip() for s in args.outputs.split(",")]
    demo_chapters = demo_chapters_for(profile["target_chapters"])
    
    meta = base_meta("spinoff", outputs=outputs, rights_status=rights_status)
    meta.update({
        "source_novel": source_path,
        "source_title": source_title,
        "spinoff_character": args.character,
        "mode": args.mode,
        "branch_point": args.branch_point,
        "scale": scale,
        "target_chapters": profile["target_chapters"],
        "target_words_per_chapter": profile["words_per_chapter"],
        "person": args.person,
        "rights_declared_at": date.today().isoformat() if args.i_have_rights else None,
        "title": None,
        "title_chosen_at": None,
        "target_platform": args.target_platform,
        "demo_chapters": demo_chapters,
        "demo_passed_at": None,
        "draft_mode": args.draft_mode,
        "chapter_granularity": args.chapter_granularity,
        "ai_text_usage": args.ai_text_usage,
    })
    
    W = lambda rel, txt: open(os.path.join(out_root, rel), "w", encoding="utf-8").write(txt)
    json.dump(meta, open(os.path.join(out_root, "_meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    
    write_project_settings(out_root, {
        "目标平台": args.target_platform,
        "权利来源": rights_status,
        "权利辖区": meta.get("rights_jurisdiction", ""),
        "发行地区": ",".join(meta.get("distribution_regions") or []) or "未定",
        "外传模式": args.mode,
        "输出格式": ",".join(outputs) + "（novel-craft/scripts/export.py）",
        "小说生成模式": args.draft_mode,
        "章节生成粒度": args.chapter_granularity,
        "AI使用披露": args.ai_text_usage or "（发布前用 ai_usage.py 确认）",
    }, note="外传：配角平行视角，锚点处锁原作事件。")

    # 设定卡骨架
    W("设定/角色卡.md", build_character_card_skeleton(args.character, source_title, args.mode))
    W("设定/世界观.md", build_worldview_skeleton(source_title))
    W("设定/章纲.md", build_outline_skeleton(meta))

    # 锚点粗筛
    candidates = scan_candidates(novel_txt, args.character)
    anchor_path = write_anchor_table(out_root, args.character, novel_txt, candidates)

    # _进度.md
    W("_进度.md", build_progress_markdown(project_name, "spinoff", profile["target_chapters"]))

    # 报告
    print(f"[ok] 项目骨架 → {out_root}")
    print(f"     原作.txt           ← {ext} 抽取")
    print(f"     设定/角色卡.md      ← 骨架（待第 2 步填）")
    print(f"     设定/世界观.md      ← 骨架（待第 2 步填）")
    print(f"     设定/锚点表.json    ← {len(candidates)} 个候选（待第 2 步精筛）")
    print(f"     设定/章纲.md        ← {meta['target_chapters']} 章占位（待第 4 步填）")
    print(f"     _meta.json: mode={args.mode} scale={args.scale} 人称={args.person} "
          f"平台={args.target_platform} 版权={rights_status}")
    print(f"[next] 主对话进第 2 步：精筛锚点表 + 填角色卡 + 填世界观。")
    print(f"       之后第 3 步 书名候选 / 第 4 步 章纲 / 第 5 步 Demo gate / 第 6 步 续写余下章节。")


if __name__ == "__main__":
    main()
