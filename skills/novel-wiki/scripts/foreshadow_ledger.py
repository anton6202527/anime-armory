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


def is_confirmed(seed):
    """seed 是否为「已确认伏笔」。手动 plant / 历史 seed 无此字段 → 默认 True；
    `extract_foreshadow_candidates` 抽的待确认候选显式 `confirmed=False`。
    未确认候选只是给人的工作清单，**永不升阻断、不进回收率分母**——既保住「不做正则式
    自动识别免得制造噪声」的原则，又让 analyze() 不再对派生线空转。"""
    return bool(seed.get("confirmed", True))


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
        "auto_extracted": False,
        "confirmed": True,
    }
    seeds.append(seed)
    return seed


def confirm(data, seed_id, expected_payoff_chapter=None, importance=None):
    """把一条自动抽取的「伏笔候选」确认为正式伏笔（confirmed=True）。

    确认后才进超期机检 / 回收率分母。可顺手补预期回收章（机检超期的前提）和重要度。
    不存在的 id 抛 KeyError。"""
    seed = find_seed(data["seeds"], seed_id)
    if not seed:
        raise KeyError(f"找不到伏笔 id: {seed_id}")
    seed["confirmed"] = True
    if expected_payoff_chapter is not None:
        seed["expected_payoff_chapter"] = int(expected_payoff_chapter)
    if importance is not None:
        if importance not in IMPORTANCE:
            raise ValueError(f"importance 须为 {sorted(IMPORTANCE)}，得到 {importance}")
        seed["importance"] = importance
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
    if not is_confirmed(seed):
        return False  # 未确认候选不是已承诺的伏笔，谈不上「烂尾」
    if seed.get("status") not in ("pending", "partially_resolved"):
        return False
    expected = seed.get("expected_payoff_chapter")
    if expected is None:
        return False
    return through_chapter > int(expected) + int(grace)


def payoff_rate(seeds):
    """回收率 = resolved / (有效伏笔)；有效伏笔 = 全部 - dropped（作废不进分母）。

    无有效伏笔时回收率为 None（避免 0/0 谎报）。partially_resolved 记为半收（0.5）。
    未确认候选（auto_extracted 待 confirm）不是已承诺伏笔，**不计入分母**，单列 candidates。
    """
    candidates = sum(1 for s in seeds if not is_confirmed(s))
    confirmed = [s for s in seeds if is_confirmed(s)]
    effective = [s for s in confirmed if s.get("status") != "dropped"]
    if not effective:
        return {"rate": None, "resolved": 0, "partial": 0, "pending": 0,
                "effective_total": 0, "dropped": len(confirmed) - len(effective),
                "candidates": candidates}
    resolved = sum(1 for s in effective if s.get("status") == "resolved")
    partial = sum(1 for s in effective if s.get("status") == "partially_resolved")
    pending = sum(1 for s in effective if s.get("status") == "pending")
    rate = (resolved + 0.5 * partial) / len(effective)
    return {"rate": round(rate, 4), "resolved": resolved, "partial": partial,
            "pending": pending, "effective_total": len(effective),
            "dropped": len(confirmed) - len(effective), "candidates": candidates}


def never_fired_at_finale(seeds, through_chapter, target_chapters, grace=DEFAULT_GRACE):
    """契诃夫之枪的反向检查：临近/抵达终章仍未击发的「已上膛的枪」。

    `is_overdue` 只抓「设了 expected_payoff_chapter 又越窗」的伏笔；但一条**已确认、却从没设回收章**的
    伏笔（expected=None）在 is_overdue 里永远返回 False——埋了忘了，机检完全看不见（正是本函数补的洞）。
    终章判据：target_chapters>0 且 through_chapter>=target_chapters。到终章仍 pending/partially_resolved 的
    已确认伏笔 = 上膛未击发。为避免与 overdue 双报，**已被 is_overdue 命中的不重复计**。
    high/critical=阻断级（读者会记得你埋过、却没兑现），low/medium=建议级。纯函数。"""
    if not target_chapters or through_chapter < int(target_chapters):
        return []
    out = []
    for s in seeds:
        if not is_confirmed(s):
            continue
        if s.get("status") not in ("pending", "partially_resolved"):
            continue
        if is_overdue(s, through_chapter, grace):
            continue  # 已在 overdue 里，别双报
        out.append({
            "id": s["id"],
            "description": s.get("description", ""),
            "status": s.get("status"),
            "planted_chapter": s.get("planted_chapter"),
            "expected_payoff_chapter": s.get("expected_payoff_chapter"),
            "importance": s.get("importance", "medium"),
            "severity": "阻断级" if s.get("importance") in ("high", "critical") else "建议级",
            "kind": "foreshadow_never_fired",
            "note": ("已抵达终章仍未回收的伏笔（上膛未击发的契诃夫之枪）——要么补一次回收、"
                     "要么显式 drop 并清干净前文线索；埋而不收会被读者记恨为烂尾"),
            "auto": True,
        })
    return out


def scan(data, through_chapter, grace=DEFAULT_GRACE, target_chapters=None):
    """巡检：揪超期伏笔（烂尾预警的真实数据源）+ 算回收率 + 终章未击发反查。纯函数，便于单测。"""
    seeds = data.get("seeds", [])
    candidates = [
        {
            "id": s["id"],
            "description": s.get("description", ""),
            "planted_chapter": s.get("planted_chapter"),
            "anchor": s.get("anchor"),
            "note": "自动抽取的伏笔候选——请人工 confirm（设预期回收章）或 drop",
        }
        for s in seeds if not is_confirmed(s)
    ]
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
    never_fired = never_fired_at_finale(seeds, through_chapter, target_chapters, grace)
    rate = payoff_rate(seeds)
    blocking = (sum(1 for o in overdue if o["severity"] == "阻断级")
                + sum(1 for n in never_fired if n["severity"] == "阻断级"))
    return {
        "kind": "foreshadow_report",
        "through_chapter": through_chapter,
        "target_chapters": target_chapters,
        "grace": grace,
        "total_seeds": len(seeds),
        "payoff_rate": rate,
        "overdue_count": len(overdue),
        "never_fired_count": len(never_fired),
        "blocking": blocking,
        "overdue": overdue,
        "never_fired": never_fired,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def _target_chapters(project):
    """从 _meta.json 读 target_chapters；缺失/异常 → None（终章反查即优雅关闭，不误报）。"""
    path = os.path.join(project, "_meta.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        tc = int(meta.get("target_chapters") or 0)
        return tc or None
    except Exception:
        return None


def _max_written_chapter(project):
    """从 章节/第NN章.md 推当前已写到第几章；无章节返回 0。"""
    cdir = os.path.join(project, "章节")
    if not os.path.isdir(cdir):
        return 0
    mx = 0
    for name in os.listdir(cdir):
        if not name.endswith(".md"):
            continue
        m = re.search(r"第0*(\d+)章", name)
        if m:
            mx = max(mx, int(m.group(1)))
    return mx


def analyze(project, through_chapter=None, grace=DEFAULT_GRACE):
    """consistency_audit 子检测器契约：analyze(project) → {ran, alerts, ...}。

    伏笔超期是 novel-review 该消费却长期没接的「烂尾预警」真实数据源。这里把 scan 适配成
    统一 subrunner 形态：through_chapter 缺省取已写最大章号；无台账/无 seeds 优雅跳过；
    overdue 直接当 alerts（每条自带 severity=阻断级/建议级，阻断级=高价值伏笔越窗）。"""
    data = load_ledger(project)
    seeds = data.get("seeds") or []
    if not seeds:
        return {"ran": False,
                "skipped": "无伏笔台账或台账为空（先用 foreshadow_ledger.py plant 埋点）"}
    if through_chapter is None:
        through_chapter = _max_written_chapter(project)
    report = scan(data, through_chapter, grace, target_chapters=_target_chapters(project))
    report["ran"] = True
    # alerts = 已确认伏笔的超期（可阻断）+ 终章未击发（契诃夫反查，可阻断）+ 待确认候选（建议级，永不阻断）。
    # 派生线一开局就有候选 → analyze 不再 ran:False 空转，但噪声候选挡不住导出。
    alerts = list(report.get("overdue", [])) + list(report.get("never_fired", []))
    for c in report.get("candidates", []):
        alerts.append({**c, "severity": "建议级", "auto": True,
                       "kind": "foreshadow_candidate"})
    report["alerts"] = alerts
    return report


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

    sc = sub.add_parser("confirm", help="把自动抽取的伏笔候选确认为正式伏笔")
    sc.add_argument("--id", required=True)
    sc.add_argument("--by", type=int, default=None, help="预期回收章 expected_payoff_chapter（机检超期前提）")
    sc.add_argument("--importance", default=None, help="low|medium|high|critical")

    sd = sub.add_parser("drop", help="作废伏笔/否决候选（从回收率分母剔除）")
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

    elif args.cmd == "confirm":
        seed = confirm(data, args.id, args.by, args.importance)
        save_ledger(args.project_path, data)
        exp = seed.get("expected_payoff_chapter")
        print(f"✔️  确认伏笔 {seed['id']}（confirmed{('，预期第%d章收' % exp) if exp else '，未设回收章'}）")

    elif args.cmd == "drop":
        seed = drop(data, args.id, args.reason)
        save_ledger(args.project_path, data)
        print(f"🗑️  作废 {seed['id']}（dropped，不计入回收率）")

    elif args.cmd == "scan":
        report = scan(data, args.through, args.grace, target_chapters=_target_chapters(args.project_path))
        out_dir = os.path.join(args.project_path, "审稿")
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, "foreshadow_report.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        rate = report["payoff_rate"]["rate"]
        rate_str = "—（无有效伏笔）" if rate is None else f"{rate*100:.1f}%"
        print(f"伏笔台账巡检（对账至第{args.through}章）→ {out}")
        cand = report.get("candidate_count", 0)
        nf = report.get("never_fired_count", 0)
        print(f"  伏笔 {report['total_seeds']} 条 · 回收率 {rate_str} · 超期 {report['overdue_count']} 条 · 终章未击发 {nf} 条（合计阻断 {report['blocking']}）· 待确认候选 {cand} 条")
        for o in report["overdue"]:
            print(f"  [{o['severity']}] {o['id']} 超期{o['overdue_by']}章 · {o['description']}")
        for n in report.get("never_fired", []):
            print(f"  [{n['severity']}·未击发] {n['id']} 第{n.get('planted_chapter')}章埋 · {n['description']}")
        for c in report.get("candidates", []):
            print(f"  [候选] {c['id']} 第{c['planted_chapter']}章「{c.get('anchor','')}」· {c['description']} → confirm/drop")


if __name__ == "__main__":
    main()
