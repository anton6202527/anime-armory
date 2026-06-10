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

# 共享工具（docx→txt / 版权判定 / 落 _设置.md）上移至 novel-craft，避免各 init 各写一份
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "novel-craft", "scripts"))
from contract import (AI_TEXT_USAGE_MODES, CHAPTER_GRANULARITY, NOVEL_DRAFT_MODES,
                      base_meta, demo_chapters_for, derived_stage_markdown, parse_outputs)
from derive_common import docx_to_txt, detect_rights_status, write_settings


def chapter_plan(target_chars, target, outputs, target_chapters=None):
    text = f"{target or ''} {','.join(outputs or [])}"
    if any(key in text for key in ("漫剧", "红果", "抖音", "n2d")):
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
    ap.add_argument("--target-chapters", type=int, default=None,
                    help="覆盖精简后目标章数；缺省按目标字数/用途估算")
    ap.add_argument("--out", default=None)
    ap.add_argument("--outputs", default="txt,docx,outline",
                    help="逗号分隔，可含 txt,docx,outline,n2d")
    ap.add_argument("--i-have-rights", action="store_true")
    ap.add_argument("--draft-mode", default=None, choices=NOVEL_DRAFT_MODES,
                    help="小说生成模式；缺省按目标用途/输出格式推导")
    ap.add_argument("--chapter-granularity", default="逐章", choices=CHAPTER_GRANULARITY,
                    help="章节生成粒度：逐章/小批/全书草稿")
    ap.add_argument("--ai-text-usage", default=None, choices=AI_TEXT_USAGE_MODES,
                    help="发布披露用：AI-generated / AI-assisted / 未使用AI文本")
    args = ap.parse_args()

    source_path = os.path.abspath(args.source_novel)
    if not os.path.exists(source_path):
        print(f"[err] 找不到原作：{source_path}", file=sys.stderr); sys.exit(2)

    source_title = os.path.splitext(os.path.basename(source_path))[0]
    out_root = os.path.abspath(args.out or os.path.join("写小说", f"{source_title}-精简"))
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
    draft_mode = args.draft_mode or ("漫剧源书" if args.target == "漫剧" or "n2d" in outputs else "稳妥初稿")

    meta = base_meta("condense", outputs=outputs, rights_status=rights)
    meta.update({
        "source_novel": source_path,
        "source_title": source_title,
        "ratio": args.ratio,
        "orig_chars_estimate": orig_chars,
        "target_chars_estimate": target_chars,
        "target_chapters": target_chapters,
        "target_words_per_chapter": target_wpc,
        "target": args.target,
        "target_platform": args.target if args.target == "漫剧" else "跨平台",
        "rights_declared_at": date.today().isoformat() if args.i_have_rights else None,
        "title": None,
        "title_chosen_at": None,
        "demo_chapters": demo_chapters_for(target_chapters),  # 共享真值源，勿硬编码 min(2,…)
        "demo_passed_at": None,
        "draft_mode": draft_mode,
        "chapter_granularity": args.chapter_granularity,
        "ai_text_usage": args.ai_text_usage,
    })
    json.dump(meta, open(os.path.join(out_root, "_meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    write_settings(out_root, {
        "目标用途": args.target,
        "权利来源": rights,
        "压缩倍数": f"÷{args.ratio}",
        "输出格式": ",".join(outputs) + "（漫剧友好版可加 n2d；novel-craft/scripts/export.py）",
        "小说生成模式": draft_mode,
        "章节生成粒度": args.chapter_granularity,
        "AI使用披露": args.ai_text_usage or "（发布前用 ai_usage.py 确认）",
    }, note="精简：保主线/锚点/反转/钩子，砍描写支线并章。漫剧用途可 --formats n2d 直喂 n2d-script。")

    skeletons = [
        ("设定/主线骨架.json", '{"主线": [], "锚点": [], "反转点": [], "状态": "待第 2 步精筛"}'),
        ("设定/章节映射.md", "# 章节映射（合章计划）\n\n> 第 3 步划章 / 合章后填。\n"),
        ("设定/章纲.md", "# 章纲 — 精简版\n\n> 第 4 步由主对话填写。**章纲未敲定不进 Demo。**\n"),
        ("_进度.md",
         "# 进度\n\n" + derived_stage_markdown("condense") +
         "\n\n- [x] 项目骨架\n- [ ] 主线骨架精筛\n- [ ] 划章 + 合章\n"
         "- [ ] 章纲（用户已确认）\n- [ ] Demo 前 2 章审过\n- [ ] 续精简\n"
         "- [ ] 一致性回扫\n- [ ] 导出\n"),
    ]
    for name, content in skeletons:
        path = os.path.join(out_root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(content)

    print(f"[ok] 项目骨架 → {out_root}")
    print(f"     原作字数估计：{orig_chars}；目标字数估计：{target_chars}（÷{args.ratio}）；目标章数：{target_chapters}")
    print(f"     版权状态：{rights}；目标用途：{args.target}")
    print(f"[next] 主对话第 2 步：标主线 / 锚点 / 反转点。")


if __name__ == "__main__":
    main()
