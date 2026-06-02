#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_project.py — 建续写项目骨架；docx → txt 抽取。

用法:
    python3 init_project.py <原作路径> \\
        --mode sequel|continuation \\
        --new-chapters 20 \\
        [--target-platform <name>] \\
        [--out <输出根>] \\
        [--i-have-rights]

依赖: python-docx (仅当原作是 .docx 时)
"""
import argparse, json, os, shutil, sys
from datetime import date


def docx_to_txt(docx_path, out_txt_path):
    try:
        from docx import Document
    except ImportError:
        print("[err] 缺依赖：pip install python-docx", file=sys.stderr); sys.exit(2)
    doc = Document(docx_path)
    paras = [p.text for p in doc.paragraphs]
    open(out_txt_path, "w", encoding="utf-8").write("\n".join(paras))


def detect_rights_status(novel_txt_path, i_have_rights):
    try:
        head = open(novel_txt_path, encoding="utf-8").read(2000)
    except FileNotFoundError:
        return "unknown"
    for line in head.splitlines():
        if not line.startswith("#"):
            break
        if "copyright" in line.lower():
            val = line.split(":", 1)[1].strip().lower() if ":" in line else ""
            if any(k in val for k in ["public", "公版", "gutenberg", "wikisource", "维基文库"]):
                return "public-domain"
            if any(k in val for k in ["用户声明", "user-declared"]):
                return "user-declared"
    return "user-declared" if i_have_rights else "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source_novel")
    ap.add_argument("--mode", choices=["sequel", "continuation"], required=True,
                    help="sequel = 续编（原作已完结）；continuation = 接更（原作未完结）")
    ap.add_argument("--new-chapters", type=int, default=20, help="续写章数（5-30）")
    ap.add_argument("--target-platform", default="跨平台")
    ap.add_argument("--out", default=None)
    ap.add_argument("--i-have-rights", action="store_true")
    args = ap.parse_args()

    source_path = os.path.abspath(args.source_novel)
    if not os.path.exists(source_path):
        print(f"[err] 找不到原作：{source_path}", file=sys.stderr); sys.exit(2)

    source_title = os.path.splitext(os.path.basename(source_path))[0]
    out_root = os.path.abspath(args.out or os.path.join("写小说", f"{source_title}-续写"))
    if os.path.exists(out_root):
        print(f"[err] 目标已存在：{out_root}", file=sys.stderr); sys.exit(2)

    for sub in ("设定", "章节", "导出"):
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

    # 简单估算原作章节数（找 第N章 行）
    import re
    chap_re = re.compile(r"^\s*第\s*[0-9零一二三四五六七八九十百千两]+\s*[章回节卷]")
    orig_chapter_count = sum(1 for ln in open(novel_txt, encoding="utf-8")
                              if chap_re.match(ln))

    # Demo 章数按规模
    demo = 2 if args.new_chapters >= 5 else 1

    meta = {
        "source_novel": source_path,
        "source_title": source_title,
        "mode": args.mode,
        "new_chapters": args.new_chapters,
        "orig_chapter_count_estimate": orig_chapter_count,
        "target_platform": args.target_platform,
        "rights_status": rights,
        "rights_declared_at": date.today().isoformat() if args.i_have_rights else None,
        "title": None,
        "title_chosen_at": None,
        "direction_chosen": None,
        "direction_chosen_at": None,
        "demo_chapters": demo,
        "demo_passed_at": None,
        "combine_with_original": False,
        "created_at": date.today().isoformat(),
    }
    json.dump(meta, open(os.path.join(out_root, "_meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

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
        ("_进度.md",
         f"# 进度 — 续写（{mode_label}）\n\n"
         f"- [x] 项目骨架（原作估计 {orig_chapter_count} 章，续写 {args.new_chapters} 章）\n"
         "- [ ] 吸收原作（人物 / 世界观 / 主线骨架 / 末章状态 / 作者口吻）\n"
         "- [ ] 续写方向（用户已选定）\n"
         "- [ ] 新章纲（用户已确认）\n"
         "- [ ] 书名（如需，调 novel-title）\n"
         f"- [ ] Demo 前 {demo} 章审过\n"
         "- [ ] 续余下新章节\n"
         "- [ ] 一致性回扫\n"
         "- [ ] 导出\n"),
    ]
    for name, content in skeletons:
        path = os.path.join(out_root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(content)

    print(f"[ok] 项目骨架 → {out_root}")
    print(f"     模式：{mode_label}")
    print(f"     原作估计 {orig_chapter_count} 章；续写目标 {args.new_chapters} 章；Demo 前 {demo} 章")
    print(f"     版权状态：{rights}；平台：{args.target_platform}")
    print(f"[next] 主对话第 2 步：吸收原作，填 5 张设定卡（末章状态最关键）。")
    print(f"       后续 第 3 步续写方向 → 第 4 步章纲 → 第 5 步 Demo → 第 6 步续 → 第 7 步回扫 → 第 8 步导出。")


if __name__ == "__main__":
    main()
