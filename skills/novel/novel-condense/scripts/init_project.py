#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_project.py — 建精简项目骨架；docx → txt 抽取。

用法:
    python3 init_project.py <原作路径> \\
        --ratio 5 \\
        [--target 漫剧|短读|大纲] \\
        [--out <输出根>] [--outputs txt,docx,outline] \\
        [--i-have-rights]

依赖: python-docx (仅当原作是 .docx 时)
"""
import argparse, json, math, os, shutil, sys
from datetime import date

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))
for _path in (os.path.join(_SKILLS, "_lib"), os.path.join(_SKILLS, "novel-craft", "scripts")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

# 共享工具（docx→txt / 版权判定 / 落 _设置.md）上移至 novel-craft，避免各 init 各写一份
from novel_contract import (AI_TEXT_USAGE_MODES, CHAPTER_GRANULARITY, NOVEL_DRAFT_MODES,
                            DRAFT_WORKFLOWS, base_meta, demo_chapters_for,
                            derived_stage_markdown, parse_outputs,
                            wordcount_band_for_words_per_chapter,
                            infer_novel_purpose, normalize_novel_purpose,
                            resolve_novel_draft_mode, resolve_novel_draft_workflow)
from derive_common import build_rights_metadata, docx_to_txt, detect_rights_status, write_settings


def chapter_plan(target_chars, target, outputs, target_chapters=None):
    text = f"{target or ''} {','.join(outputs or [])}"
    if any(key in text for key in ("漫剧", "红果", "抖音")):
        wpc = [1000, 1500]
    elif "大纲" in text:
        wpc = [1500, 2500]
    else:
        wpc = [3000, 5000]
    if target_chapters:
        return int(target_chapters), wpc
    avg = max(1, sum(wpc) / 2)
    return max(1, int(math.ceil(target_chars / avg))), wpc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source_novel")
    ap.add_argument("--ratio", type=float, default=5.0, help="压缩倍数（默认 5×；20+ 为大纲级）")
    ap.add_argument("--target", default="短读",
                    choices=["短读", "漫剧", "大纲"], help="目标用途")
    ap.add_argument("--genre", default=None,
                    help="原作题材；命中力量题材（穿越/系统流/修仙/玄幻…）时 seed power_system_registry 脚手架")
    ap.add_argument("--purpose", default=None,
                    help="小说用途：传统小说/漫剧源书/微短剧源书/短读/短篇/出海译制底稿/自定义")
    ap.add_argument("--target-chapters", type=int, default=None,
                    help="覆盖精简后目标章数；缺省按目标总量/用途估算")
    ap.add_argument("--out", default=None)
    ap.add_argument("--outputs", default="txt,docx,outline",
                    help="逗号分隔，可含 txt,docx,outline")
    ap.add_argument("--i-have-rights", action="store_true")
    ap.add_argument("--rights-jurisdiction", default=None,
                    help="公版/授权依据适用辖区，如 US/CN/GLOBAL；缺省按来源推断")
    ap.add_argument("--distribution-regions", default=None,
                    help="计划发行/交付地区，逗号分隔，如 CN,US；公版跨区时必须复核")
    ap.add_argument("--draft-mode", default=None, choices=NOVEL_DRAFT_MODES,
                    help="小说生成模式；缺省按目标用途/输出格式推导")
    ap.add_argument("--draft-workflow", default=None, choices=DRAFT_WORKFLOWS,
                    help="小说生成工作流：默认单步/三步迭代/边写边自检")
    ap.add_argument("--batch-review-interval", default="5章",
                    help="小批回扫间隔；默认 5章，可填 3章/5章/关闭")
    ap.add_argument("--chapter-granularity", default="逐章", choices=CHAPTER_GRANULARITY,
                    help="章节生成粒度：逐章/小批/全书草稿")
    ap.add_argument("--ai-text-usage", default=None, choices=AI_TEXT_USAGE_MODES,
                    help="发布披露用：AI-generated / AI-assisted / 未使用AI文本")
    args = ap.parse_args()

    source_path = os.path.abspath(args.source_novel)
    if not os.path.exists(source_path):
        print(f"[err] 找不到原作：{source_path}", file=sys.stderr); sys.exit(2)

    source_title = os.path.splitext(os.path.basename(source_path))[0]
    out_root = os.path.abspath(args.out or os.path.join("创作区", "写小说", f"{source_title}-精简"))
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

    orig_chars = sum(1 for c in open(novel_txt, encoding="utf-8").read() if c.strip())
    target_chars = int(orig_chars / args.ratio)
    outputs = parse_outputs(args.outputs)
    target_chapters, target_wpc = chapter_plan(target_chars, args.target, outputs, args.target_chapters)
    purpose = normalize_novel_purpose(args.purpose) or infer_novel_purpose(
        target=args.target
    )
    draft_mode = resolve_novel_draft_mode(
        args.draft_mode,
        purpose=purpose,
        target=args.target,
        fallback=("漫剧源书" if args.target == "漫剧" else "稳妥初稿"),
    )
    draft_workflow = resolve_novel_draft_workflow(
        args.draft_workflow,
        draft_mode=draft_mode,
        purpose=purpose,
        target_chapters=target_chapters,
    )

    meta = base_meta("condense", outputs=outputs, rights_status=rights)
    meta.update(build_rights_metadata(
        rights,
        i_have_rights=args.i_have_rights,
        rights_jurisdiction=args.rights_jurisdiction,
        distribution_regions=args.distribution_regions,
    ))
    meta.update({
        "source_novel": source_path,
        "source_title": source_title,
        "ratio": args.ratio,
        "orig_chars_estimate": orig_chars,
        "target_chars_estimate": target_chars,
        "purpose": purpose,
        "target_chapters": target_chapters,
        "target_words_per_chapter": target_wpc,
        "target_wordcount_min_max": wordcount_band_for_words_per_chapter(target_wpc),
        "target": args.target,
        "target_platform": args.target if args.target == "漫剧" else "跨平台",
        "rights_declared_at": date.today().isoformat() if args.i_have_rights else None,
        "title": None,
        "title_chosen_at": None,
        "demo_chapters": demo_chapters_for(target_chapters),  # 共享真值源，勿硬编码 min(2,…)
        "demo_passed_at": None,
        "draft_mode": draft_mode,
        "draft_workflow": draft_workflow,
        "batch_review_interval": args.batch_review_interval,
        "chapter_granularity": args.chapter_granularity,
        "ai_text_usage": args.ai_text_usage,
    })
    json.dump(meta, open(os.path.join(out_root, "_meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    write_settings(out_root, {
        "目标用途": args.target,
        "小说用途": purpose,
        "权利来源": rights,
        "权利辖区": meta.get("rights_jurisdiction", ""),
        "发行地区": ",".join(meta.get("distribution_regions") or []) or "未定",
        "压缩倍数": f"÷{args.ratio}",
        "输出格式": ",".join(outputs) + "（novel-craft/scripts/export.py）",
        "小说生成模式": draft_mode,
        "小说生成工作流": draft_workflow,
        "小批回扫间隔": args.batch_review_interval,
        "章节生成粒度": args.chapter_granularity,
        "AI使用披露": args.ai_text_usage or "（发布前用 ai_usage.py 确认）",
    }, note="精简：保主线/锚点/反转/钩子，砍描写支线并章。")

    skeletons = [
        ("设定/主线骨架.json", '{"主线": [], "锚点": [], "反转点": [], "状态": "待第 2 步精筛"}'),
        # 精简保留原作全部角色，必须给角色卡占位——否则 wiki_builder 的
        # resolve_character_card 返回 None，logic_sentry 死人复活 / 角色护栏机检拿到
        # 空实体而静默 no-op（与 continue/expand 同用「人物.md」命名，由
        # resolve_character_card 兜底两种命名）。
        ("设定/人物.md",
         "# 主要人物简卡（沿用原作设定）\n\n> 第 2 步标主线时同步登记主角 + 主要配角，"
         "供合章重写时锚定一致性、避免 OOC。\n"),
        ("设定/章节映射.md", "# 章节映射（合章计划）\n\n> 第 3 步划章 / 合章后填。\n"),
        ("设定/章纲.md", "# 章纲 — 精简版\n\n> 第 4 步由主对话填写。**章纲未敲定不进 Demo。**\n"),
        ("_进度.md",
         "# 进度\n\n" + derived_stage_markdown("condense") +
         "\n\n- [x] 项目骨架\n- [ ] 主线骨架精筛\n- [ ] 划章 + 合章\n"
         "- [ ] 章纲（用户已确认）\n- [ ] Demo 前 2 章审过\n- [ ] 续精简\n"
         "- [ ] 一致性回扫\n- [ ] 导出\n"),
    ]
    # 一致性注册表脚手架（B1）：派生作品也要有 character_guardrails / power_system_registry，
    # 否则 novel-wiki 的护栏 / 力量体系机检在精简作品上静默 no-op。
    from consistency_scaffold import (consistency_registry_files,
                                      split_source_chapters, extract_foreshadow_candidates)
    from novel_contract import CHAPTER_RE
    # 伏笔台账自动播种：精简最易砍支线留下孤儿埋点，从原作抽「待确认伏笔候选」预播，
    # 让 foreshadow_ledger.analyze() 一开局就 ran:True。候选永不升阻断，由人工 confirm/drop。
    try:
        src_text = open(novel_txt, encoding="utf-8").read()
        fs_seeds = extract_foreshadow_candidates(split_source_chapters(src_text, CHAPTER_RE))
    except OSError:
        fs_seeds = []
    skeletons += consistency_registry_files(args.genre, foreshadow_seeds=fs_seeds)
    for name, content in skeletons:
        path = os.path.join(out_root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(content)

    print(f"[ok] 项目骨架 → {out_root}")
    print(f"     原作字数估计：{orig_chars}；目标总量估计：{target_chars}（÷{args.ratio}）；目标章数：{target_chapters}")
    print(f"     版权状态：{rights}；目标用途：{args.target}")
    print(f"[next] 主对话第 2 步：标主线 / 锚点 / 反转点。")


if __name__ == "__main__":
    main()
