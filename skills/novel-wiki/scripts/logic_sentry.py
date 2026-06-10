#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
logic_sentry.py — 逻辑哨兵：拿《动态百科》确定性扫硬冲突（纯标准库）

跑真活，不是 mock：对目标章节扫三类**硬冲突**（确定性可机检，不靠 LLM）：
  1) 死人复活：百科里已 deceased 的角色，在其死亡章之后又"在场行动"（且非闪回/托梦语境）
  2) 弃置道具复用：百科里已 discarded/shattered/lost 的道具，又被"使用/催动/祭出"
  3) 位置跳变（保守）：角色在本章被写在与百科记录不同的已知地点，且无位移过渡词

软冲突（性格突变、动机不合理）不在此列——交 novel-review 人判。
哨兵只报"硬冲突候选"，每条带证据 + auto 标志，最终由人/LLM 定夺（容错铁律：宁缺毋滥）。

  python3 logic_sentry.py <作品根> --chapter <章节号或文件路径>

测试：cd skills/novel-wiki/scripts && python3 -m pytest test_logic_sentry.py
"""
import os
import re
import json
import argparse

from wiki_builder import FLASHBACK_HINTS, _context, list_chapters, _CJK

ITEM_USE_VERBS = ["用", "使", "催动", "祭出", "举起", "握", "拔", "挥", "取出", "拿出", "施展", "祭起"]
DISCARDED_STATUS = {"discarded", "shattered", "lost", "丢弃", "损毁", "破碎", "遗失", "摧毁"}
MOVE_HINTS = ["赶往", "前往", "来到", "回到", "抵达", "瞬移", "传送", "疾驰", "飞往", "动身", "启程", "赶赴"]


def _resolve_chapter(project, chapter):
    """--chapter 可给章号或文件路径。返回 (idx, text)。"""
    if os.path.isfile(chapter):
        m = re.search(r"(\d+)", os.path.basename(chapter))
        idx = int(m.group(1)) if m else 0
        with open(chapter, "r", encoding="utf-8") as f:
            return idx, f.read()
    idx = int(re.search(r"(\d+)", str(chapter)).group(1))
    for cid, _, text in list_chapters(project):
        if cid == idx:
            return idx, text
    return idx, ""


def scan_chapter(wiki, text, chapter_index):
    """确定性扫描，返回 alerts 列表。纯函数，便于单测。"""
    alerts = []

    for name, e in wiki.items():
        if e.get("category") == "item":
            continue
        if e.get("status") != "deceased":
            continue
        death_at = e.get("death_chapter", e.get("last_update", 0))
        if chapter_index <= death_at:
            continue
        for pos in (m.start() for m in re.finditer(re.escape(name), text)):
            ctx = _context(text, pos, 22)
            if any(h in ctx for h in FLASHBACK_HINTS):
                continue
            alerts.append({
                "type": "deceased_reactivation",
                "entity": name,
                "severity": "阻断级",
                "chapter": chapter_index,
                "death_chapter": death_at,
                "evidence": ctx.strip(),
                "auto": True,
                "note": "已标记阵亡的角色在死亡章之后再次在场行动；若为闪回/托梦请在百科加 FLASHBACK 语境或豁免",
            })
            break

    for name, e in wiki.items():
        if e.get("category") != "item":
            continue
        if e.get("status") not in DISCARDED_STATUS:
            continue
        gone_at = e.get("last_update", 0)
        if chapter_index <= gone_at:
            continue
        for pos in (m.start() for m in re.finditer(re.escape(name), text)):
            ctx = _context(text, pos, 14)
            if any(v in ctx for v in ITEM_USE_VERBS):
                alerts.append({
                    "type": "discarded_item_reuse",
                    "entity": name,
                    "severity": "阻断级",
                    "chapter": chapter_index,
                    "gone_chapter": gone_at,
                    "evidence": ctx.strip(),
                    "auto": True,
                    "note": "已弃置/损毁的道具又被使用",
                })
                break

    # 位置跳变（保守）：百科有 location，本章把该角色写在另一个已知地点，且全章无位移过渡词
    known_locations = {e["location"] for e in wiki.values() if e.get("location")}
    has_move = any(h in text for h in MOVE_HINTS)
    for name, e in wiki.items():
        loc = e.get("location")
        if not loc or e.get("status") == "deceased":
            continue
        if name not in text or has_move:
            continue
        other = [l for l in known_locations if l != loc and l in text]
        for pos in (m.start() for m in re.finditer(re.escape(name), text)):
            ctx = _context(text, pos, 30)
            hit = [l for l in other if l in ctx]
            if hit:
                alerts.append({
                    "type": "location_jump",
                    "entity": name,
                    "severity": "建议级",
                    "chapter": chapter_index,
                    "wiki_location": loc,
                    "found_location": hit[0],
                    "evidence": ctx.strip(),
                    "auto": True,
                    "note": "角色出现在与百科记录不同的地点且全章无位移过渡词（保守候选，易误报，请人判）",
                })
                break
    return alerts


def main():
    p = argparse.ArgumentParser(description="逻辑哨兵：确定性扫硬冲突")
    p.add_argument("project_path")
    p.add_argument("--chapter", required=True, help="章节号或文件路径")
    args = p.parse_args()

    wiki_path = os.path.join(args.project_path, "设定", "动态百科.json")
    if not os.path.exists(wiki_path):
        print(f"Error: 动态百科不存在 {wiki_path}，先跑 wiki_builder.py")
        return
    with open(wiki_path, "r", encoding="utf-8") as f:
        wiki = json.load(f)

    idx, text = _resolve_chapter(args.project_path, args.chapter)
    alerts = scan_chapter(wiki, text, idx)

    out_dir = os.path.join(args.project_path, "审稿")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"logic_alerts_{idx}.json")
    blocking = sum(1 for a in alerts if a["severity"] == "阻断级")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "status": "clean" if not alerts else "conflicts",
            "chapter": idx,
            "blocking": blocking,
            "alerts": alerts,
        }, f, ensure_ascii=False, indent=2)
    if alerts:
        print(f"⚠️ 第{idx}章：{len(alerts)} 条逻辑冲突候选（阻断 {blocking}）→ {out_path}")
        for a in alerts:
            print(f"  [{a['severity']}] {a['type']} · {a['entity']} · {a['evidence']}")
    else:
        print(f"✅ 第{idx}章：0 硬冲突 → {out_path}")


if __name__ == "__main__":
    main()
