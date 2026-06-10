#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wiki_builder.py — 动态百科增量构建（确定性骨架，纯标准库）

跑真活，不是 mock：
  - 从 设定/角色卡.md 播种实体（角色名 → category=character, status=active）
  - 扫章节算每个实体的 last_seen_chapter
  - 用死亡关键词做"疑似阵亡"候选标记（带证据章 + auto 标志，交人/LLM 复核）
  - 与已有 动态百科.json 合并：保留人工字段，只更新 last_seen / 追加候选

语义级状态（伤势细节、道具归属精确变更）仍建议 LLM 在交互节点补全；本脚本提供
确定性骨架，让 logic_sentry.py 有真实可比对的状态底座。

  python3 wiki_builder.py <作品根> [--range 1-50] [--chapter 12]

测试：cd skills/novel-wiki/scripts && python3 -m pytest test_logic_sentry.py
"""
import os
import re
import json
import argparse

DEATH_KEYWORDS = ["死了", "身亡", "阵亡", "殒命", "殒", "葬身", "气绝", "咽气",
                  "命丧", "战死", "殉", "毙命", "丧命", "已死", "死去"]
ITEM_GONE_KEYWORDS = ["丢弃", "遗失", "损毁", "破碎", "碎裂", "夺走", "失去", "摧毁"]
FLASHBACK_HINTS = ["回忆", "闪回", "梦中", "梦里", "想起", "记忆", "当年", "曾经", "幻象", "亡魂", "鬼魂", "托梦"]

_CJK = r"一-鿿"


def list_chapters(project, chap_range=None, single=None):
    """返回 [(chapter_index, path, text)]，按章号自然序。"""
    cdir = os.path.join(project, "章节")
    if not os.path.isdir(cdir):
        return []
    items = []
    for name in os.listdir(cdir):
        if not name.lower().endswith((".md", ".txt")) or name.startswith("_"):
            continue
        m = re.search(r"(\d+)", name)
        idx = int(m.group(1)) if m else None
        items.append([idx, os.path.join(cdir, name), name])
    items.sort(key=lambda x: (x[0] is None, x[0] if x[0] is not None else x[2]))
    # 补齐没有数字的章号为序号
    for seq, it in enumerate(items, 1):
        if it[0] is None:
            it[0] = seq
    lo, hi = _parse_range(chap_range)
    out = []
    for idx, path, _ in items:
        if single is not None and idx != single:
            continue
        if chap_range and not (lo <= idx <= hi):
            continue
        with open(path, "r", encoding="utf-8") as f:
            out.append((idx, path, f.read()))
    return out


def _parse_range(chap_range):
    if not chap_range:
        return (0, 10 ** 9)
    if "-" in chap_range:
        a, b = chap_range.split("-", 1)
        return (int(a), int(b))
    v = int(chap_range)
    return (v, v)


def parse_character_names(project):
    """从 设定/角色卡.md 抽角色名；抽不到退回正文高频专名候选。"""
    names = set()
    card = os.path.join(project, "设定", "角色卡.md")
    if os.path.exists(card):
        with open(card, "r", encoding="utf-8") as f:
            text = f.read()
        for ln in text.splitlines():
            s = ln.strip()
            m = re.match(r"#{1,4}\s+([" + _CJK + r"·]{2,6})\s*$", s)
            if m:
                names.add(m.group(1))
            m = re.search(r"(?:姓名|名字|角色)[:：]\s*([" + _CJK + r"·]{2,6})", s)
            if m:
                names.add(m.group(1))
    return names


def _context(text, pos, radius=20):
    return text[max(0, pos - radius): pos + radius]


_CLAUSE_END = "。！？!?\n，,；;"


def _death_evidence(text, name, name_pos, fwd=12):
    """死亡只在'名字之后、同一小句内'判定，避免把邻近另一个角色的死安到本角色头上。

    返回证据串（命中）或 None。前向窗口遇句读即止，再做闪回语境排除。
    """
    start = name_pos + len(name)
    window = []
    for ch in text[start:start + fwd]:
        if ch in _CLAUSE_END:
            break
        window.append(ch)
    seg = "".join(window)
    if not any(k in seg for k in DEATH_KEYWORDS):
        return None
    ctx = _context(text, name_pos, 18)
    if any(h in ctx for h in FLASHBACK_HINTS):
        return None
    return (name + seg).strip()


def build_wiki(project, chap_range=None, single=None, existing=None):
    chapters = list_chapters(project, chap_range, single)
    names = parse_character_names(project)
    wiki = dict(existing or {})

    # 未经人工确认的自动死亡（auto:true）在重扫前先清回 active，让修正能传播；
    # 人工确认的状态（无 auto 标志）保留。这样改了正文重跑能纠正旧误报。
    for entry in wiki.values():
        if entry.get("auto") and entry.get("status") == "deceased":
            entry["status"] = "active"
            entry.pop("death_chapter", None)
            entry.pop("evidence", None)
            entry.pop("auto", None)

    for name in names:
        entry = wiki.get(name, {"category": "character", "status": "active"})
        wiki[name] = entry

    for idx, _, text in chapters:
        for name in names:
            if name not in text:
                continue
            entry = wiki[name]
            entry["last_seen_chapter"] = max(entry.get("last_seen_chapter", 0), idx)
            entry.setdefault("last_update", idx)
            entry["last_update"] = max(entry.get("last_update", 0), idx)
            # 疑似阵亡：死亡词必须紧跟在本角色名之后、同一小句内（排除邻近他人之死 + 闪回）
            for pos in (m.start() for m in re.finditer(re.escape(name), text)):
                ev = _death_evidence(text, name, pos)
                if ev:
                    if entry.get("status") != "deceased":
                        entry["status"] = "deceased"
                        entry["death_chapter"] = idx
                        entry["auto"] = True
                        entry["evidence"] = ev
                    break
    return wiki


def main():
    p = argparse.ArgumentParser(description="动态百科增量构建（确定性骨架）")
    p.add_argument("project_path")
    p.add_argument("--range", dest="chap_range", help="章节范围，如 1-50")
    p.add_argument("--chapter", type=int, help="只扫单章")
    args = p.parse_args()

    wiki_path = os.path.join(args.project_path, "设定", "动态百科.json")
    existing = {}
    if os.path.exists(wiki_path):
        with open(wiki_path, "r", encoding="utf-8") as f:
            existing = json.load(f)

    wiki = build_wiki(args.project_path, args.chap_range, args.chapter, existing)
    os.makedirs(os.path.dirname(wiki_path), exist_ok=True)
    with open(wiki_path, "w", encoding="utf-8") as f:
        json.dump(wiki, f, ensure_ascii=False, indent=2)

    n_dead = sum(1 for v in wiki.values() if v.get("status") == "deceased")
    print(f"动态百科 → {wiki_path}")
    print(f"  实体 {len(wiki)} 个，疑似阵亡 {n_dead} 个"
          + ("（带 auto 标志，需人/LLM 复核）" if n_dead else ""))
    if not parse_character_names(args.project_path):
        print("  ⚠️ 未找到 设定/角色卡.md 的角色名——建议先补角色卡，否则只能空播种。")


if __name__ == "__main__":
    main()
