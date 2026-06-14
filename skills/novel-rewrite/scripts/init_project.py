#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_project.py — 建【改写】项目骨架；docx → txt 抽取；判版权。
与 novel-spinoff 的 init 镜像：**不扫锚点**，改为生成 改动spec + 新设定圣经 骨架。

用法:
    python3 init_project.py <原作路径> \\
        --rewrite-type "<一句话改动方向>" \\
        --scale short|medium|long|微短剧|漫剧 \\
        [--target-chapters N]  [--person first|third-limited] \\
        [--out <输出根>] [--outputs txt,docx,outline] \\
        [--target-platform 跨平台] [--i-have-rights]

依赖: python-docx（仅当原作是 .docx 时）
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
                            normalize_scale, parse_outputs, parse_regions, rights_metadata,
                            SCALE_PROFILES, NOVEL_DRAFT_MODES, CHAPTER_GRANULARITY,
                            AI_TEXT_USAGE_MODES)

SCALE_PROFILE = SCALE_PROFILES  # scale-band 契约：test_scale_contract 校验其与规模档一致


def build_change_spec(source_title):
    return f"""# 改动spec — 《{source_title}》→《<新书名待定>》

> 这部改写的"宪法"。动笔前与用户敲定。每条要具体可判定，别写空话。

## 一句话改动方向
（把"X 的故事"改成"Y 的故事"——一句话说清灵魂）

## ① 保留的内核（魂，不许丢）
- 主角人设内核：
- 情感主线：
- 世界观底色 / 基调：
- 必须保留的标志性桥段/意象：

## ② 改的部分（事件 / 设定 / 结局）
- 改主线走向：原作是… → 改成…
- 改/删的事件：
- 改的设定（改了的要在 新设定.md 登记新值）：
- 改的结局：

## ③ 加的新料（清单；详细体系进 新设定.md）
- 新金手指/系统：
- 新势力/组织：
- 新人物：
- 新地理/秘境/物品：
"""


def build_new_settings(source_title):
    return f"""# 新设定圣经 — 《<新书名待定>》（改写自《{source_title}》）

> 本作相对原作【新增/改写】的所有设定。逐章写作硬约束，回扫逐条核。
> 与原作旧设定冲突的以本表为准；本表内部不许自相矛盾。新金手指必须有代价。

## 体系（金手指/力量/修炼）
### <名称>
- 是什么 / 规则边界 / **代价限制** / 首现章·复用 / 不可违反点

## 势力 / 组织
### <名称>　立场·目的·与主角关系·首现章

## 新人物
### <名称>　身份·外貌锚定·性格·动机·说话习惯·首现章·复用范围

## 地理 / 秘境 / 物品
### <名称>　描述·规则·首现章

## 改写后的旧设定（覆盖原作）
| 原作设定 | 改成 | 影响范围 |
|---|---|---|
"""


def build_character_card(source_title):
    return f"""# 角色卡 — 主角（改写自《{source_title}》）

> 第 3 步填。改写常重塑主角——内核可承原作（见 改动spec ①），事件/能力按新设定。

## 姓名 / 年龄 / 性别
## 外观（锚定）
## 出身
## 能力体系（依 新设定.md）
## 性格底色（保留的内核 + 新增）
## 动机 / 心结 / 渴望
## 关键关系
## 说话习惯
"""


def build_worldview(source_title):
    return f"""# 世界观 — 《<新书名待定>》（改写自《{source_title}》）

> 第 3 步填。= 原作保留的底色 + 新设定圣经覆盖/新增后的"现行"世界规则总览。
> 注意：这里写的是**改写后**的现行世界，不是原作世界。

## 力量 / 修炼 / 魔法体系（现行）
## 政治 / 势力格局（现行）
## 地理
## 时间线（关键节点）
## 术语表（新旧混合，以现行为准）
"""


def build_outline(n, rewrite_type):
    if n >= 6:
        a1, a2 = max(1, n // 4), n * 3 // 4
        acts = (f"## 三幕结构（自由编织，不受原作章节束缚）\n"
                f"- 第一幕（约 1-{a1}）：立新世界 + 新主角处境 + 抛改动钩子\n"
                f"- 第二幕（约 {a1+1}-{a2}）：新设定展开 + 大势推进 + 中段反转\n"
                f"- 第三幕（约 {a2+1}-{n}）：高潮 + 新结局\n")
    else:
        acts = "## 结构\n（短篇——围绕单一改动核心推进）\n"
    chapters = "\n".join(f"- 第 {i:02d} 章 《》 — 主线事件 / 涉及的新设定 / 钩子" for i in range(1, n + 1))
    return f"""# 章纲 — 《<新书名待定>》改写

> 改动方向：{rewrite_type}
> 第 5 步填。**章纲未敲定不进 Demo。** 改写自由重排，不必对齐原作章节顺序。

## 总体弧线

{acts}
## 逐章
{chapters}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source_novel", help="原作 .txt 或 .docx")
    ap.add_argument("--rewrite-type", required=True, help="一句话改动方向（如：换主角+加任务系统魔改）")
    ap.add_argument("--scale", required=True, choices=list(SCALE_CHOICES))
    ap.add_argument("--target-chapters", type=int, default=None, help="覆盖规模档的章数")
    ap.add_argument("--person", default="third-limited", choices=["first", "third-limited"])
    ap.add_argument("--out", default=None, help="输出根，缺省 写小说/<原作名>-改写/")
    ap.add_argument("--outputs", default="txt,docx,outline")
    ap.add_argument("--target-platform", default="跨平台")
    ap.add_argument("--draft-mode", default="稳妥初稿", choices=NOVEL_DRAFT_MODES,
                    help="小说生成模式：决定速度/质量 gate 密度")
    ap.add_argument("--chapter-granularity", default="逐章", choices=CHAPTER_GRANULARITY,
                    help="章节生成粒度：逐章/小批/全书草稿")
    ap.add_argument("--ai-text-usage", default=None, choices=AI_TEXT_USAGE_MODES,
                    help="发布披露用：AI-generated / AI-assisted / 未使用AI文本")
    ap.add_argument("--i-have-rights", action="store_true")
    ap.add_argument("--rights-jurisdiction", default=None,
                    help="公版/授权依据适用辖区，如 US/CN/GLOBAL；缺省按来源推断")
    ap.add_argument("--distribution-regions", default=None,
                    help="计划发行/交付地区，逗号分隔，如 CN,US；公版跨区时必须复核")
    args = ap.parse_args()

    source_path = os.path.abspath(args.source_novel)
    if not os.path.exists(source_path):
        print(f"[err] 找不到原作：{source_path}", file=sys.stderr)
        sys.exit(2)

    source_title = os.path.splitext(os.path.basename(source_path))[0]
    out_root = os.path.abspath(args.out or os.path.join("写小说", f"{source_title}-改写"))
    if os.path.exists(out_root):
        print(f"[err] 目标已存在：{out_root}（备份/删除后重试）", file=sys.stderr)
        sys.exit(2)

    for sub in ("设定", "章节", "导出", "写作任务", "合规"):
        os.makedirs(os.path.join(out_root, sub), exist_ok=True)

    novel_txt = os.path.join(out_root, "原作.txt")
    ext = os.path.splitext(source_path)[1].lower()
    if ext == ".txt":
        shutil.copy(source_path, novel_txt)
    elif ext == ".docx":
        docx_to_txt(source_path, novel_txt)
    else:
        print(f"[err] 不支持的格式：{ext}（请 .txt/.docx）", file=sys.stderr)
        shutil.rmtree(out_root); sys.exit(2)

    rights = detect_rights_status(novel_txt, args.i_have_rights)
    if rights == "unknown":
        print("[err] 无法判定原作版权。公版来源请在 txt 头加 `# copyright: public-domain`；"
              "自有/已授权重跑加 --i-have-rights。", file=sys.stderr)
        shutil.rmtree(out_root); sys.exit(2)

    scale = normalize_scale(args.scale)
    profile = scale_profile(scale)
    n = args.target_chapters or profile["target_chapters"]
    outputs = parse_outputs(args.outputs)
    meta = base_meta("rewrite", outputs=outputs, rights_status=rights)
    # 派生权利字段（rights_covered_regions / requires_region_rights_review 等）统一由
    # rights_metadata 计算，使公版改写也能触发 qa_gate 的发行地区复核。
    meta.update(rights_metadata(
        rights,
        rights_declared=args.i_have_rights or rights in ("original", "user-owned", "user-declared"),
        rights_jurisdiction=args.rights_jurisdiction,
        distribution_regions=args.distribution_regions,
    ))
    meta.update({
        "source_novel": source_path,
        "source_title": source_title,
        "rewrite_type": args.rewrite_type,
        "scale": scale,
        "target_chapters": n,
        "target_words_per_chapter": profile["words_per_chapter"],
        "person": args.person,
        "rights_declared_at": date.today().isoformat() if args.i_have_rights else None,
        "title": None,
        "target_platform": args.target_platform,
        "demo_chapters": demo_chapters_for(n),
        "draft_mode": args.draft_mode,
        "chapter_granularity": args.chapter_granularity,
        "ai_text_usage": args.ai_text_usage,
    })
    W = lambda rel, txt: open(os.path.join(out_root, rel), "w", encoding="utf-8").write(txt)
    json.dump(meta, open(os.path.join(out_root, "_meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    write_project_settings(out_root, {
        "目标平台": args.target_platform,
        "权利来源": rights,
        "权利辖区": meta.get("rights_jurisdiction", ""),
        "发行地区": ",".join(meta.get("distribution_regions") or []) or "未定",
        "篇幅档": f"{scale}（{n}章×{profile['words_per_chapter'][0]}-{profile['words_per_chapter'][1]}字）",
        "改动方向": args.rewrite_type,
        "输出格式": ",".join(outputs) + "（novel-craft/scripts/export.py）",
        "小说生成模式": args.draft_mode,
        "章节生成粒度": args.chapter_granularity,
        "AI使用披露": args.ai_text_usage or "（发布前用 ai_usage.py 确认）",
    }, note="改写：改主线/换设定/加原创料，新设定圣经为准。")
    W("设定/改动spec.md", build_change_spec(source_title))
    W("设定/新设定.md", build_new_settings(source_title))
    W("设定/角色卡.md", build_character_card(source_title))
    W("设定/世界观.md", build_worldview(source_title))
    W("设定/章纲.md", build_outline(n, args.rewrite_type))
    W("_进度.md", build_progress_markdown("<新书名待定>", "rewrite", n))

    print(f"[ok] 改写项目骨架 → {out_root}")
    print(f"     原作.txt        ← {ext} 抽取（参考素材，非底稿）")
    print(f"     设定/改动spec.md ← 骨架（第 2 步填：保留/改/加 三栏）★最重要")
    print(f"     设定/新设定.md   ← 骨架（第 3 步填：新增/覆盖设定 + 一致性约束）")
    print(f"     设定/角色卡.md / 世界观.md / 章纲.md ← 骨架")
    print(f"     _meta: kind=rewrite type=\"{args.rewrite_type}\" 章数={n} 版权={rights}")
    print(f"[next] 第 2 步填改动spec（先定'保留内核'）→ 第 3 步新设定圣经 → 书名 → 章纲 → Demo gate → 续写+回扫。")


if __name__ == "__main__":
    main()
