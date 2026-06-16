#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
foreshadow_ledger.py — 伏笔台账：种—收对账 + 烂尾预警（确定性骨架 + LLM 补语义）

填上 dispatcher / novel-balance 一直承诺、却没人真的落地的「伏笔回收 / 烂尾预警」：
契约注册表早已声明 foreshadowing_ledger → 设定/foreshadowing_ledger.json（owner=novel-wiki），
本脚本是这个「已声明、未实现」产物的实现，与 wiki_builder.py 已初始化的同名账本对齐
（kind=novel_foreshadowing_ledger，seeds 列表；字段见 references/entity-schema.md §3）。

机检 vs LLM 的诚实边界（对标 logic_sentry.py 的「只报硬冲突候选」）：
  - **确定性（脚本算）**：JSON 完整性/去重、超期(overdue)判定、回收率(回收率) 计算、状态机合法迁移。
  - **LLM/人工（脚本不臆测）**：「这一段到底算不算埋了伏笔 / 算不算回收了」的语义识别。
    本脚本**不做**正则式的「伏笔自动识别」——那种检测在中文长篇里只会制造噪声。
    伏笔的 plant（埋）与 payoff（收）由 agent/人在交互节点判断后，用 plant/payoff 子命令登记；
    脚本负责把账记准、把超期的揪出来、把回收率算对。

子命令：
  plant   登记一条新埋下的伏笔（pending）
  payoff  标记某条伏笔已回收（resolved，可记实际回收章 + 证据）
  drop    标记某条伏笔作废（dropped，从回收率分母剔除）
  scan    巡检：按当前章号判超期(overdue) + 算回收率，落 审稿/foreshadow_report.json

  python3 foreshadow_ledger.py <作品根> plant  --desc "沈念捡到半块断剑" --at 5 --by 50 [--id SEED_001] [--importance high] [--entities 沈念,断剑]
  python3 foreshadow_ledger.py <作品根> payoff --id SEED_001 --at 50 [--evidence "断剑现真身，认主"]
  python3 foreshadow_ledger.py <作品根> drop   --id SEED_001 [--reason "线索废弃"]
  python3 foreshadow_ledger.py <作品根> scan   --through 60 [--grace 5]

测试：cd skills/novel-wiki/scripts && python3 -m pytest test_foreshadow_ledger.py
"""
import os
import re
import json
import argparse

LEDGER_REL = os.path.join("设定", "foreshadowing_ledger.json")
KIND = "novel_foreshadowing_ledger"

# 与 references/entity-schema.md §3 一致的存储态。overdue 不是存储态——它是 scan 按章号算出来的派生态。
STORED_STATUS = {"pending", "partially_resolved", "resolved", "dropped"}
IMPORTANCE = {"low", "medium", "high", "critical"}
DEFAULT_GRACE = 5  # 超过 expected_payoff_chapter 多少章才算超期（与 logic_sentry 的宽容窗口一致）


# ── 账本读写（保持 JSON 完整性，幂等） ──────────────────────────────────────────
def ledger_path(project):
    return os.path.join(project, LEDGER_REL)


def load_ledger(project):
    path = ledger_path(project)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("kind", KIND)
        data.setdefault("seeds", [])
        return data
    return {"kind": KIND, "seeds": []}


def save_ledger(project, data):
    path = ledger_path(project)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _next_id(seeds):
    """生成 SEED_NNN，避开已用号。"""
    used = set()
    for s in seeds:
        m = re.match(r"SEED_(\d+)$", str(s.get("id", "")))
        if m:
            used.add(int(m.group(1)))
    n = 1
    while n in used:
        n += 1
    return f"SEED_{n:03d}"


def find_seed(seeds, seed_id):
    for s in seeds:
        if s.get("id") == seed_id:
            return s
    return None


# ── 登记动作（plant / payoff / drop） ────────────────────────────────────────
def plant(data, description, planted_chapter, expected_payoff_chapter,
          seed_id=None, importance="medium", linked_entities=None):
    seeds = data["seeds"]
    if not seed_id:
        seed_id = _next_id(seeds)
    if find_seed(seeds, seed_id):
        raise ValueError(f"伏笔 id 已存在: {seed_id}")
    if importance not in IMPORTANCE:
        raise ValueError(f"importance 须为 {sorted(IMPORTANCE)}，得到 {importance}")
    seed = {
        "id": seed_id,
        "description": description,
        "status": "pending",
        "planted_chapter": int(planted_chapter),
        "expected_payoff_chapter": int(expected_payoff_chapter) if expected_payoff_chapter is not None else None,
        "actual_payoff_chapter": None,
        "importance": importance,
        "linked_entities": list(linked_entities or []),
        "evidence": None,
    }
    seeds.append(seed)
    return seed


def payoff(data, seed_id, actual_payoff_chapter=None, evidence=None, partial=False):
    seed = find_seed(data["seeds"], seed_id)
    if not seed:
        raise KeyError(f"找不到伏笔 id: {seed_id}")
    seed["status"] = "partially_resolved" if partial else "resolved"
    if actual_payoff_chapter is not None:
        seed["actual_payoff_chapter"] = int(actual_payoff_chapter)
    if evidence:
        seed["evidence"] = evidence
    return seed


def drop(data, seed_id, reason=None):
    seed = find_seed(data["seeds"], seed_id)
    if not seed:
        raise KeyError(f"找不到伏笔 id: {seed_id}")
    seed["status"] = "dropped"
    if reason:
        seed["evidence"] = reason
    return seed


# ── 确定性巡检：超期判定 + 回收率 ─────────────────────────────────────────────
def is_overdue(seed, through_chapter, grace=DEFAULT_GRACE):
    """未回收(pending/partially_resolved) 且当前章号已越过 expected_payoff_chapter + grace。

    没有 expected_payoff_chapter 的伏笔无法机检超期（脚本不臆测截止章），返回 False。
    """
    if seed.get("status") not in ("pending", "partially_resolved"):
        return False
    expected = seed.get("expected_payoff_chapter")
    if expected is None:
        return False
    return through_chapter > int(expected) + int(grace)


def payoff_rate(seeds):
    """回收率 = resolved / (有效伏笔)；有效伏笔 = 全部 - dropped（作废不进分母）。

    无有效伏笔时回收率为 None（避免 0/0 谎报）。partially_resolved 记为半收（0.5）。
    """
    effective = [s for s in seeds if s.get("status") != "dropped"]
    if not effective:
        return {"rate": None, "resolved": 0, "partial": 0, "pending": 0,
                "effective_total": 0, "dropped": len(seeds) - len(effective)}
    resolved = sum(1 for s in effective if s.get("status") == "resolved")
    partial = sum(1 for s in effective if s.get("status") == "partially_resolved")
    pending = sum(1 for s in effective if s.get("status") == "pending")
    rate = (resolved + 0.5 * partial) / len(effective)
    return {"rate": round(rate, 4), "resolved": resolved, "partial": partial,
            "pending": pending, "effective_total": len(effective),
            "dropped": len(seeds) - len(effective)}


def scan(data, through_chapter, grace=DEFAULT_GRACE):
    """巡检：揪超期伏笔（烂尾预警的真实数据源）+ 算回收率。纯函数，便于单测。"""
    seeds = data.get("seeds", [])
    overdue = []
    for s in seeds:
        if is_overdue(s, through_chapter, grace):
            overdue.append({
                "id": s["id"],
                "description": s.get("description", ""),
                "status": s.get("status"),
                "planted_chapter": s.get("planted_chapter"),
                "expected_payoff_chapter": s.get("expected_payoff_chapter"),
                "importance": s.get("importance", "medium"),
                # critical/high 超期是烂尾级，low/medium 是提醒级
                "severity": "阻断级" if s.get("importance") in ("high", "critical") else "建议级",
                "overdue_by": through_chapter - int(s["expected_payoff_chapter"]),
                "note": "高价值伏笔已越过预期回收窗口，疑似遗忘/烂尾——补回收或调整章纲",
                "auto": True,
            })
    rate = payoff_rate(seeds)
    blocking = sum(1 for o in overdue if o["severity"] == "阻断级")
    return {
        "kind": "foreshadow_report",
        "through_chapter": through_chapter,
        "grace": grace,
        "total_seeds": len(seeds),
        "payoff_rate": rate,
        "overdue_count": len(overdue),
        "blocking": blocking,
        "overdue": overdue,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────
def _split_entities(s):
    if not s:
        return []
    return [x.strip() for x in re.split(r"[,，、]", s) if x.strip()]


def main():
    p = argparse.ArgumentParser(description="伏笔台账：种—收对账 + 烂尾预警")
    p.add_argument("project_path")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("plant", help="登记一条新埋下的伏笔")
    sp.add_argument("--desc", required=True, help="伏笔描述")
    sp.add_argument("--at", type=int, required=True, help="埋设章 planted_chapter")
    sp.add_argument("--by", type=int, default=None, help="预期回收章 expected_payoff_chapter")
    sp.add_argument("--id", default=None, help="自定 id（默认自动 SEED_NNN）")
    sp.add_argument("--importance", default="medium", help="low|medium|high|critical")
    sp.add_argument("--entities", default=None, help="关联实体，逗号分隔")

    so = sub.add_parser("payoff", help="标记伏笔已回收")
    so.add_argument("--id", required=True)
    so.add_argument("--at", type=int, default=None, help="实际回收章")
    so.add_argument("--evidence", default=None, help="回收证据/落点")
    so.add_argument("--partial", action="store_true", help="只部分回收（partially_resolved）")

    sd = sub.add_parser("drop", help="作废伏笔（从回收率分母剔除）")
    sd.add_argument("--id", required=True)
    sd.add_argument("--reason", default=None)

    ss = sub.add_parser("scan", help="巡检超期 + 算回收率")
    ss.add_argument("--through", type=int, required=True, help="对账到第几章（当前进度章号）")
    ss.add_argument("--grace", type=int, default=DEFAULT_GRACE, help=f"超期宽容窗口（默认 {DEFAULT_GRACE} 章）")

    args = p.parse_args()
    data = load_ledger(args.project_path)

    if args.cmd == "plant":
        seed = plant(data, args.desc, args.at, args.by, seed_id=args.id,
                     importance=args.importance, linked_entities=_split_entities(args.entities))
        save_ledger(args.project_path, data)
        print(f"🌱 埋伏笔 {seed['id']}（第{seed['planted_chapter']}章，预期第{seed['expected_payoff_chapter']}章收）→ {ledger_path(args.project_path)}")

    elif args.cmd == "payoff":
        seed = payoff(data, args.id, args.at, args.evidence, partial=args.partial)
        save_ledger(args.project_path, data)
        print(f"✅ 回收 {seed['id']}（{seed['status']}{('，第%d章' % seed['actual_payoff_chapter']) if seed.get('actual_payoff_chapter') else ''}）")

    elif args.cmd == "drop":
        seed = drop(data, args.id, args.reason)
        save_ledger(args.project_path, data)
        print(f"🗑️  作废 {seed['id']}（dropped，不计入回收率）")

    elif args.cmd == "scan":
        report = scan(data, args.through, args.grace)
        out_dir = os.path.join(args.project_path, "审稿")
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, "foreshadow_report.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        rate = report["payoff_rate"]["rate"]
        rate_str = "—（无有效伏笔）" if rate is None else f"{rate*100:.1f}%"
        print(f"伏笔台账巡检（对账至第{args.through}章）→ {out}")
        print(f"  伏笔 {report['total_seeds']} 条 · 回收率 {rate_str} · 超期 {report['overdue_count']} 条（阻断 {report['blocking']}）")
        for o in report["overdue"]:
            print(f"  [{o['severity']}] {o['id']} 超期{o['overdue_by']}章 · {o['description']}")


if __name__ == "__main__":
    main()
