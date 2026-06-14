#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_project.py — 建续写项目骨架；docx → txt 抽取。

用法:
    python3 init_project.py <原作路径> \
        --mode sequel|continuation \
        --new-chapters 20 \
        [--target-platform <name>] \
        [--out <输出根>] [--outputs txt,docx,outline] \
        [--i-have-rights]

依赖: python-docx (仅当原作是 .docx 时)
"""
import argparse, json, os, shutil, sys
from datetime import date

# Standardized imports from novel/_lib
LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "novel", "_lib"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from novel_contract import (base_meta, build_progress_markdown, routing_stages,
                            SCALE_CHOICES, scale_profile, detect_rights_status,
                            docx_to_txt, write_project_settings, demo_chapters_for,
                            rights_metadata, CHAPTER_RE)


def words_per_chapter_for(target_platform):
    text = str(target_platform or "")
    if any(key in text for key in ("漫剧", "红果", "抖音")):
        return [1000, 1500]
    if "短剧" in text:
        return [1500, 2500]
    return [3000, 5000]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source_novel")
    ap.add_argument("--mode", choices=["sequel", "continuation"], required=True,
                    help="sequel = 续编（原作已完结）；continuation = 接更（原作未完结）")
    ap.add_argument("--new-chapters", type=int, default=20, help="续写章数（5-30）")
    ap.add_argument("--target-platform", default="跨平台")
    ap.add_argument("--out", default=None)
    ap.add_argument("--outputs", default="txt,docx,outline",
                    help="逗号分隔，可含 txt,docx,outline,n2d")
    ap.add_argument("--i-have-rights", action="store_true")
    ap.add_argument("--rights-jurisdiction", default=None,
                    help="公版/授权依据适用辖区，如 US/CN/GLOBAL；缺省按来源推断")
    ap.add_argument("--distribution-regions", default=None,
                    help="计划发行/交付地区，逗号分隔，如 CN,US；公版跨区时必须复核")
    ap.add_argument("--draft-mode", default=None, choices=["极速初稿", "稳妥初稿", "商业连载", "漫剧源书"],
                    help="小说生成模式；缺省按目标平台/输出格式推导")
    ap.add_argument("--chapter-granularity", default="逐章", choices=["逐章", "小批", "全书草稿"],
                    help="章节生成粒度：逐章/小批/全书草稿")
    ap.add_argument("--ai-text-usage", default=None, choices=["AI-generated", "AI-assisted", "未使用AI文本"],
                    help="发布披露用：AI-generated / AI-assisted / 未使用AI文本")
    args = ap.parse_args()

    source_path = os.path.abspath(args.source_novel)
    if not os.path.exists(source_path):
        print(f"[err] 找不到原作：{source_path}", file=sys.stderr); sys.exit(2)

    source_title = os.path.splitext(os.path.basename(source_path))[0]
    out_root = os.path.abspath(args.out or os.path.join("写小说", f"{source_title}-续写"))
    if os.path.exists(out_root):
        print(f"[err] 目标已存在：{out_root}", file=sys.stderr); sys.exit(2)

    for sub in ("设定", "章节", "导出", "写作任务", "合规"):
        os.makedirs(os.path.join(out_root, sub), exist_ok=True)

    novel_txt = os.path.join(out_root, "原作.txt")
    ext = os.path.splitext(source_path)[1].lower()
    if ext == ".txt":
        shutil.copy(source_path, novel_txt)
    elif ext == ".docx":
        docx_to_txt(source_path, novel_txt)
    else:
        print(f"[err] 不支持的格式：{ext}", file=sys.stderr); sys.exit(2)

    rights = detect_rights_status(novel_txt, args.i_have_rights)
    if rights == "unknown":
        print("[err] 无法判定版权状态；公版来源加 # copyright: public-domain，"
              "自有/已授权加 --i-have-rights", file=sys.stderr)
        shutil.rmtree(out_root); sys.exit(2)

    if args.new_chapters < 1 or args.new_chapters > 100:
        print("[err] --new-chapters 应在 1-100 之间", file=sys.stderr)
        shutil.rmtree(out_root); sys.exit(2)

    # 简单估算原作章节数（章节标题正则用共享 CHAPTER_RE）
    orig_chapter_count = sum(1 for ln in open(novel_txt, encoding="utf-8")
                              if CHAPTER_RE.match(ln))

    demo = demo_chapters_for(args.new_chapters)
    outputs = [s.strip() for s in args.outputs.split(",")]
    target_wpc = words_per_chapter_for(args.target_platform)
    draft_mode = args.draft_mode or (
        "漫剧源书" if "n2d" in outputs or any(k in args.target_platform for k in ("漫剧", "红果", "抖音"))
        else "稳妥初稿"
    )

    meta = base_meta("continue", outputs=outputs, rights_status=rights)
    # 计算派生权利字段（rights_covered_regions / requires_region_rights_review 等），
    # 否则公版续写不会触发 qa_gate 的发行地区复核（与 expand/condense 对齐）。
    meta.update(rights_metadata(
        rights,
        rights_declared=args.i_have_rights or rights in ("original", "user-owned", "user-declared"),
        rights_jurisdiction=args.rights_jurisdiction,
        distribution_regions=args.distribution_regions,
    ))
    meta.update({
        "source_novel": source_path,
        "source_title": source_title,
        "mode": args.mode,
        "new_chapters": args.new_chapters,
        "target_chapters": args.new_chapters,
        "target_words_per_chapter": target_wpc,
        "orig_chapter_count_estimate": orig_chapter_count,
        "target_platform": args.target_platform,
        "rights_declared_at": date.today().isoformat() if args.i_have_rights else None,
        "title": None,
        "title_chosen_at": None,
        "direction_chosen": None,
        "direction_chosen_at": None,
        "demo_chapters": demo,
        "demo_passed_at": None,
        "combine_with_original": False,
        "draft_mode": draft_mode,
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
        "续写模式": args.mode,
        "续写章数": args.new_chapters,
        "输出格式": ",".join(outputs) + "（合本加 --combine；novel-craft/scripts/export.py）",
        "小说生成模式": draft_mode,
        "章节生成粒度": args.chapter_granularity,
        "AI使用披露": args.ai_text_usage or "（发布前用 ai_usage.py 确认）",
    }, note="续写：从原作末章往后写新章节，沿用原作设定圣经/作者口吻。")

    mode_label = "续编（原作已完结）" if args.mode == "sequel" else "接更（原作未完结）"
    skeletons = [
        ("设定/人物.md",
         f"# 主要人物简卡（截止原作末章状态）\n\n> 第 2 步由主对话填写，覆盖主角 + 主要配角。\n"),
        ("设定/世界观.md", "# 世界观摘要\n\n> 第 2 步由主对话填写。只摘原作已确立规则。\n"),
        ("设定/主线骨架.json", '{"已发生事件": [], "状态": "待第 2 步填"}'),
        ("设定/末章状态.md",
         "# 末章状态\n\n> 第 2 步由主对话填写。**最重要**：未回收的伏笔 / 悬念 / 钩子。\n\n"
         "## 末章人物位置 / 状态\n\n## 未回收伏笔\n\n- [ ] 伏笔 1：\n- [ ] 伏笔 2：\n\n"
         "## 未回答的悬念\n\n## 章末钩子\n"),
        ("设定/作者口吻.md",
         "# 作者口吻特征\n\n> 第 2 步由主对话填写。续写章必须对齐这些特征。\n\n"
         "## 句长 / 段落节奏\n\n## 高频词汇\n\n## 标志性短句 / 口头禅（每个角色）\n\n"
         "## 描写风格（环境 / 心理 / 战斗 等）\n"),
        ("设定/续写方向.md",
         f"# 续写方向候选 — {mode_label}\n\n> 第 3 步由主对话填写：给 2-3 个方向候选，每个含主线一句话、"
         "用上的伏笔、风险点。用户选定后回写 _meta.json.direction_chosen。\n"),
        ("设定/章纲.md", f"# 章纲 — 续写 {args.new_chapters} 章\n\n> 第 4 步由主对话填写。**未敲定不进 Demo。**\n"),
    ]
    for name, content in skeletons:
        path = os.path.join(out_root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        W(name, content)

    W("_进度.md", build_progress_markdown(source_title, "continue", args.new_chapters))

    print(f"[ok] 项目骨架 → {out_root}")
    print(f"     模式：{mode_label}")
    print(f"     原作估计 {orig_chapter_count} 章；续写目标 {args.new_chapters} 章；Demo 前 {demo} 章")
    print(f"     版权状态：{rights}；平台：{args.target_platform}")
    print(f"[next] 主对话第 2 步：吸收原作，填 5 张设定卡（末章状态最关键）。")
    print(f"       后续 第 3 步续写方向 → 第 4 步章纲 → 第 5 步 Demo → 第 6 步续 → 第 7 步回扫 → 第 8 步导出。")


if __name__ == "__main__":
    main()
