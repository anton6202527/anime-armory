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


def scan_chapter(wiki, text, chapter_index, project_root=None):
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

    # 位置跳变（保守）
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

    # 新增：伏笔回收对账 (Foreshadowing Audit)
    if project_root:
        ledger_path = os.path.join(project_root, "设定", "foreshadowing_ledger.json")
        if os.path.exists(ledger_path):
            try:
                with open(ledger_path, "r", encoding="utf-8") as f:
                    ledger = json.load(f)
                for seed in ledger.get("seeds", []):
                    if seed.get("status") == "pending" and seed.get("expected_payoff_chapter"):
                        if chapter_index > seed["expected_payoff_chapter"] + 5: # 宽容 5 章
                            alerts.append({
                                "type": "foreshadowing_overdue",
                                "entity": seed["id"],
                                "severity": "建议级",
                                "chapter": chapter_index,
                                "expected_at": seed["expected_payoff_chapter"],
                                "evidence": seed["description"],
                                "auto": True,
                                "note": "高价值伏笔已超过预期的回收窗口，请检查是否遗忘或需调整章纲"
                            })
            except Exception: pass

    # 新增：世界观规则演进对账 (World Rule Evolution)
    if project_root:
        world_path = os.path.join(project_root, "设定", "world_state_ledger.json")
        if os.path.exists(world_path):
            try:
                with open(world_path, "r", encoding="utf-8") as f:
                    world = json.load(f)
                for change in world.get("major_changes", []):
                    if chapter_index > change.get("chapter", 0):
                        # Simple rule check: if the impact contains "forbidden" but it appears in text
                        if "forbidden" in change.get("impact", "").lower() or "禁止" in change.get("impact", ""):
                            # This would need specific keyword extraction from impact
                            pass
            except Exception: pass

    # 新增：人物关系温度计异常波动检查 (Relationship Fluctuation)
    if project_root:
        matrix_path = os.path.join(project_root, "设定", "relationship_matrix.json")
        if os.path.exists(matrix_path):
            try:
                with open(matrix_path, "r", encoding="utf-8") as f:
                    matrix_data = json.load(f)
                # This would ideally compare current chapter's emotional output with matrix
                # For deterministic check, we can only warn if the matrix is updated but chapter text seems contradictory
                pass
            except Exception: pass

    return alerts


def generate_red_team_task(project_path):
    out_dir = os.path.join(project_path, "审稿")
    os.makedirs(out_dir, exist_ok=True)
    task_path = os.path.join(out_dir, "red_team_task.json")
    
    context = {}
    for filename in ["设定圣经.md", "创作蓝图.md", "世界观.md", "角色卡.md"]:
        filepath = os.path.join(project_path, "设定", filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                context[filename] = f.read()
                
    if not context:
        print("❌ Red-Team Failed: No setting documents found in '设定/' directory. Establish the Bible and Blueprint first.")
        return
        
    task = {
        "mission": "Red-Teaming (Devil's Advocate)",
        "attack_vectors": [
            "Resource Exploit (资源滥用)",
            "Logic Bypass (逻辑短路)",
            "Consequence Evasion (金手指零代价)"
        ],
        "context": context,
        "instructions": "Act as a ruthless red-teaming agent. Read the provided settings and find the easiest, most pragmatic ways for the protagonist or antagonist to achieve their goals, completely bypassing the intended plot constraints. If there are no counter-measures, log it as a vulnerability."
    }
    
    with open(task_path, "w", encoding="utf-8") as f:
        json.dump(task, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Red-Team Task Generated -> {task_path}")
    print("  Use this payload to instruct an LLM to attack the world-building logic before drafting the outline.")

def main():
    p = argparse.ArgumentParser(description="逻辑哨兵：确定性扫硬冲突 & 事前红蓝对抗")
    p.add_argument("project_path")
    p.add_argument("--chapter", help="章节号或文件路径（普通模式必填）")
    p.add_argument("--red-team", action="store_true", help="启动事前红蓝对抗（剧情漏洞爆破手）模式")
    args = p.parse_args()

    if args.red_team:
        generate_red_team_task(args.project_path)
        return

    if not args.chapter:
        p.error("the following arguments are required: --chapter (unless --red-team is used)")

    wiki_path = os.path.join(args.project_path, "设定", "动态百科.json")
    if not os.path.exists(wiki_path):
        print(f"Error: 动态百科不存在 {wiki_path}，先跑 wiki_builder.py")
        return
    with open(wiki_path, "r", encoding="utf-8") as f:
        wiki = json.load(f)

    idx, text = _resolve_chapter(args.project_path, args.chapter)
    alerts = scan_chapter(wiki, text, idx, project_root=args.project_path)

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
