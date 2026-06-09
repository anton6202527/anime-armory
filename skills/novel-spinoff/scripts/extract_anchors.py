#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_anchors.py — 在原作 txt 里做配角锚点粗筛，输出候选 JSON。

粗筛 only：用正则在每章里搜配角名，抽前后段落作为候选。是 anchor 还是 mention、
事件骨架、已知/未知情报等，都由主对话的当前 agent 在第 2 步精筛时填。

用法（单独跑）：
    python3 extract_anchors.py <作品根> --character "<配角名>"

也可作模块 import：
    from extract_anchors import scan_candidates
    scan_candidates(novel_txt_path, character_name) -> list[dict]
"""
import argparse
import json
import os
import re
import sys
from datetime import date

CHAPTER_RE = re.compile(
    r"^\s*第\s*[0-9零一二三四五六七八九十百千两]+\s*[章回节卷]",
    re.MULTILINE,
)

# 候选段落上下文窗口（字符）
CONTEXT_BEFORE = 200
CONTEXT_AFTER = 300
# 同章节内相邻命中合并阈值
MERGE_WITHIN = 250


def split_into_chapters(text):
    """把 txt 按章节标题正则切分。返回 [(chapter_idx, title_line, body_text), ...]。
    跳过文件头 provenance 块（# 开头行）。"""
    # 跳过开头连续的 # 注释行
    lines = text.splitlines()
    skip = 0
    for ln in lines:
        if ln.startswith("#") or ln.strip() == "":
            skip += 1
        else:
            break
    body = "\n".join(lines[skip:])

    matches = list(CHAPTER_RE.finditer(body))
    if not matches:
        # 没有章节标志，整本当一章
        return [(1, "（全本）", body)]
    chapters = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        title_line = body[start:body.find("\n", start) if body.find("\n", start) != -1 else end].strip()
        body_text = body[body.find("\n", start) + 1:end] if body.find("\n", start) != -1 else ""
        chapters.append((i + 1, title_line, body_text))
    return chapters


def scan_candidates(novel_txt_path, character_name):
    """扫 novel_txt_path，找出 character_name 出现的每个段落，返回候选列表。
    返回 [{id, source_chapter, source_excerpt_hint, excerpt}, ...]。"""
    with open(novel_txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    chapters = split_into_chapters(text)
    candidates = []
    cand_idx = 0

    for chap_idx, title_line, body in chapters:
        hits = [m.start() for m in re.finditer(re.escape(character_name), body)]
        if not hits:
            continue
        # 合并相邻命中
        merged = []
        for pos in hits:
            if merged and pos - merged[-1][-1] <= MERGE_WITHIN:
                merged[-1].append(pos)
            else:
                merged.append([pos])

        for group in merged:
            first = group[0]
            last = group[-1]
            start = max(0, first - CONTEXT_BEFORE)
            end = min(len(body), last + CONTEXT_AFTER)
            excerpt = body[start:end].strip()
            pct = int(round(100 * (first / max(len(body), 1))))
            cand_idx += 1
            candidates.append({
                "id": f"C{cand_idx:03d}",
                "source_chapter": chap_idx,
                "source_chapter_title": title_line,
                "source_excerpt_hint": f"第{chap_idx}章约 {pct}% 位置",
                "hit_count": len(group),
                "excerpt": excerpt,
            })
    return candidates


def write_anchor_table(project_root, character_name, novel_txt_path, candidates):
    """写 设定/锚点表.json — candidates 阶段。"""
    table = {
        "character": character_name,
        "source_novel": os.path.abspath(novel_txt_path),
        "extracted_at": date.today().isoformat(),
        "stage": "candidates",
        "candidates": candidates,
        "anchors": [],
    }
    out_path = os.path.join(project_root, "设定", "锚点表.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, indent=2)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_root", help="作品根目录（已由 init_project 建好）")
    ap.add_argument("--character", required=True, help="配角名")
    args = ap.parse_args()

    novel_txt = os.path.join(args.project_root, "原作.txt")
    if not os.path.exists(novel_txt):
        print(f"[err] 找不到 {novel_txt}（先跑 init_project.py）", file=sys.stderr)
        sys.exit(2)

    candidates = scan_candidates(novel_txt, args.character)
    out = write_anchor_table(args.project_root, args.character, novel_txt, candidates)

    print(f"[ok] 候选 {len(candidates)} 条 → {out}")
    print(f"[next] 用主对话跑第 2 步精筛：判 anchor/mention、填事件骨架。")


if __name__ == "__main__":
    main()
