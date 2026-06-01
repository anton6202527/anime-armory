#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_project.py — 建扩写项目骨架；docx → txt 抽取。

用法:
    python3 init_project.py <原作路径> \\
        --ratio 5 \\
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
    with open(out_txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(paras))


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
    ap.add_argument("--ratio", type=float, default=5.0, help="扩写倍数（默认 5×）")
    ap.add_argument("--target-platform", default="跨平台")
    ap.add_argument("--out", default=None)
    ap.add_argument("--i-have-rights", action="store_true")
    args = ap.parse_args()

    source_path = os.path.abspath(args.source_novel)
    if not os.path.exists(source_path):
        print(f"[err] 找不到原作：{source_path}", file=sys.stderr); sys.exit(2)

    source_title = os.path.splitext(os.path.basename(source_path))[0]
    out_root = os.path.abspath(args.out or os.path.join("作品集", f"{source_title}-扩写"))
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

    orig_chars = sum(1 for c in open(novel_txt, encoding="utf-8").read() if c.strip())
    target_chars = int(orig_chars * args.ratio)

    meta = {
        "source_novel": source_path,
        "source_title": source_title,
        "ratio": args.ratio,
        "orig_chars_estimate": orig_chars,
        "target_chars_estimate": target_chars,
        "target_platform": args.target_platform,
        "rights_status": rights,
        "rights_declared_at": date.today().isoformat() if args.i_have_rights else None,
        "title": None,
        "title_chosen_at": None,
        "demo_chapters": 2,
        "demo_passed_at": None,
        "created_at": date.today().isoformat(),
    }
    json.dump(meta, open(os.path.join(out_root, "_meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    skeletons = [
        ("设定/事件骨架.json", '{"骨架": [], "状态": "待第 2 步精筛"}'),
        ("设定/人物.md", "# 主要人物简卡\n\n> 第 2 步由主对话填写。\n"),
        ("设定/世界观.md", "# 世界观摘要\n\n> 第 2 步由主对话填写。\n"),
        ("设定/章节映射.md", "# 章节映射\n\n> 第 3 步划章后填。\n"),
        ("设定/章纲.md", "# 章纲 — 扩写版\n\n> 第 4 步由主对话填写。**章纲未敲定不进 Demo。**\n"),
        ("_进度.md",
         "# 进度\n\n- [x] 项目骨架\n- [ ] 事件骨架精筛\n- [ ] 人物 / 世界观\n"
         "- [ ] 划章 + 映射\n- [ ] 章纲（用户已确认）\n- [ ] 书名（如需）\n"
         "- [ ] Demo 前 2 章审过\n- [ ] 续扩剩余章节\n- [ ] 一致性回扫\n- [ ] 导出\n"),
    ]
    for name, content in skeletons:
        path = os.path.join(out_root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(content)

    print(f"[ok] 项目骨架 → {out_root}")
    print(f"     原作字数估计：{orig_chars}；目标字数估计：{target_chars}（{args.ratio}×）")
    print(f"     版权状态：{rights}；平台：{args.target_platform}")
    print(f"[next] 主对话第 2 步：提取事件骨架 + 人物简卡 + 世界观。")
    print(f"       后续 第 3 步划章 / 第 4 步章纲 / 第 5 步 Demo / 第 6 步续 / 第 7 步导出。")


if __name__ == "__main__":
    main()
