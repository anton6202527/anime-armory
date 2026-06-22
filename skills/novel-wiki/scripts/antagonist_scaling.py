#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""antagonist_scaling.py — 反派/威胁战力 scaling 检测器：反向「战力崩坏」（纯标准库）。

为什么：power_system.py 只盯**主角**等级/战力单调成长，但没人检查**反派/威胁是否随主角同步水涨船高**。
两种高发崩坏，power_system 都抓不到：
  · **威胁缺位**：主角连续多章碾压所有在场反派（tier 领先 > max_lead），张力塌陷（爽文无敌→读者流失）。
  · **反派战力崩坏（突兀膨胀）**：某反派在自己相邻快照间无代价地暴涨 > max_jump 个 tier（凑反派临时加戏）。

二者都是**节奏/设计信号 = 建议级**（不是硬矛盾，advisory），与 power_system 的 check_pacing 同思路（镜像）。
本检测器只读 设定/power_system_registry.json 的 tiers.sequence + progression 快照，确定性机检；
软判（这反派够不够带感）交 novel-score / 人判——宁缺毋滥。

诚实前提·需要角色身份标注：progression 快照（或 registry.roster）须带 role/阵营 字段才能区分主角与反派。
  约定取值：主角 = {"protagonist","主角","hero","主人公"}；反派 = {"antagonist","反派","villain","boss","敌"}。
  若 registry 里**没有任何角色被标为反派** → 优雅跳过（note 说明：无法凭空推断"威胁"是谁）。

  python3 antagonist_scaling.py <作品根> [--json] [--advisory]
测试：cd skills/novel-wiki/scripts && python3 -m pytest test_antagonist_scaling.py
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))

# 复用 power_system 的 registry 装载 + tier_rank + _num + _alert（同一真值源；导不动则就地兜底）。
try:
    from power_system import (
        load_registry as _load_registry,
        tier_rank as _tier_rank,
        _num as _num,
        _alert as _alert,
    )
except Exception:  # 退化兜底（独立跑/测试桩）
    import re as _re

    def _load_registry(project):
        path = os.path.join(project, "设定", "power_system_registry.json")
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("kind") == "novel_power_system_registry":
                return data
        except (OSError, json.JSONDecodeError):
            pass
        return None

    def _tier_rank(tier, sequence, subtiers=()):
        if tier is None:
            return None
        t = str(tier)
        base_idx = base_name = None
        for i, name in enumerate(sequence):
            if name and name in t and (base_name is None or len(name) > len(base_name)):
                base_idx, base_name = i, name
        if base_idx is None:
            return None
        span = max(1, len(subtiers))
        sub_idx = 0
        for j, sub in enumerate(subtiers):
            if sub and sub in t:
                sub_idx = j
                break
        return base_idx * span + sub_idx

    def _num(value):
        if isinstance(value, (int, float)):
            return float(value)
        if value is None:
            return None
        m = _re.search(r"-?\d+(?:\.\d+)?", str(value))
        return float(m.group()) if m else None

    def _alert(typ, entity, severity, chapter, evidence, note=""):
        return {"type": typ, "entity": entity, "severity": severity,
                "chapter": chapter, "evidence": evidence, "note": note, "auto": True}


# ── 角色身份标注约定（role/阵营）────────────────────────────────────────────────
PROTAGONIST_ROLES = {"protagonist", "主角", "hero", "主人公", "男主", "女主"}
ANTAGONIST_ROLES = {"antagonist", "反派", "villain", "boss", "敌", "宿敌", "反派boss"}

# 反派暴涨命中这些"代价/机缘/铺垫"词时不判崩坏（与 power_system.LEAP_JUSTIFY_KEYWORDS 同思路）。
SPIKE_JUSTIFY_KEYWORDS = ("代价", "反噬", "禁术", "献祭", "傀儡", "借力", "夺舍", "邪功",
                          "顿悟", "机缘", "传承", "血脉觉醒", "渡劫", "爆种", "燃烧寿命")

DEFAULT_MAX_LEAD = 2   # 主角 tier 领先所有在场反派超过此值 = 威胁缺位（建议级）
DEFAULT_MAX_JUMP = 2   # 反派自身相邻快照 tier 跳变超过此值且无代价 = 突兀膨胀（建议级）


def _role_of(snap_or_entry):
    """读快照/名册条目的 role/阵营 字段，归一小写去空白。无则 ''。纯函数·可测。"""
    if not isinstance(snap_or_entry, dict):
        return ""
    raw = snap_or_entry.get("role")
    if raw is None:
        raw = snap_or_entry.get("阵营")
    return str(raw or "").strip().lower()


def is_protagonist(role):
    """role 串是否归类主角。纯函数·可测。"""
    return str(role or "").strip().lower() in {r.lower() for r in PROTAGONIST_ROLES}


def is_antagonist(role):
    """role 串是否归类反派/威胁。纯函数·可测。"""
    return str(role or "").strip().lower() in {r.lower() for r in ANTAGONIST_ROLES}


# ── 纯函数：威胁差距 + scaling 带 ──────────────────────────────────────────────

def threat_gap(protag_rank, antag_ranks):
    """主角 tier 序 - 在场反派里**最强者**的 tier 序。大正数 = 主角碾压全场（无敌）。

    antag_ranks: 在场反派的 tier 序 int 列表（None/空项已剔除）。空列表返回 None（无威胁可比）。纯函数·可测。"""
    ranks = [r for r in (antag_ranks or []) if r is not None]
    if protag_rank is None or not ranks:
        return None
    return int(protag_rank) - max(int(r) for r in ranks)


def scaling_band(gap, max_lead=DEFAULT_MAX_LEAD):
    """gap > max_lead → 'warn'（威胁缺位/反派战力跟不上，建议级）；否则 'ok'。

    gap=None（无可比）也算 'ok'（不臆造威胁）。纯函数·可测。"""
    if gap is None:
        return "ok"
    return "warn" if int(gap) > int(max_lead) else "ok"


# ── 纯函数：反派自身暴涨带 ─────────────────────────────────────────────────────

def antag_spike_band(prev_rank, cur_rank, max_jump=DEFAULT_MAX_JUMP):
    """同一反派相邻快照 tier 跳变 > max_jump → 'warn'（反派战力崩坏/突兀膨胀，建议级）；否则 'ok'。

    任一为 None 视为 'ok'（无法判）。下降不在此报（power_system 的退档机检管单调）。纯函数·可测。"""
    if prev_rank is None or cur_rank is None:
        return "ok"
    return "warn" if (int(cur_rank) - int(prev_rank)) > int(max_jump) else "ok"


# ── analyze：装载 registry → 逐章威胁差距 + 逐反派暴涨 ─────────────────────────

def _ranked_snaps(progression, tiers, role_by_char):
    """把 progression 折成 {char: [(chapter:int, rank:int, raw_tier, role), ...]}（按章排序，剔无 rank）。"""
    sequence = list((tiers or {}).get("sequence") or [])
    subtiers = list((tiers or {}).get("subtiers") or [])
    by_char = {}
    for snap in progression or []:
        if not isinstance(snap, dict):
            continue
        char = str(snap.get("character") or "主角")
        r = _tier_rank(snap.get("tier"), sequence, subtiers)
        ch = _num(snap.get("chapter"))
        # 战力数值作 rank 的 tie-break 备用：tier 缺失时退用 战力/power 排序，仍允许同框比较。
        if r is None:
            r = _num(snap.get("战力") if snap.get("战力") is not None else snap.get("power"))
        # 快照自带 role 优先，否则查名册推断的 role_by_char。
        role = _role_of(snap) or role_by_char.get(char, "")
        if ch is None or r is None:
            continue
        by_char.setdefault(char, []).append((int(ch), r, snap.get("tier"), role))
    for char in by_char:
        by_char[char].sort(key=lambda t: t[0])
    return by_char


def _roster_roles(reg):
    """从 registry.roster（若有）建 {character: role}；快照自带 role 仍优先。"""
    out = {}
    for entry in (reg or {}).get("roster") or []:
        if isinstance(entry, dict):
            name = str(entry.get("character") or entry.get("name") or "").strip()
            role = _role_of(entry)
            if name and role:
                out[name] = role
    return out


def analyze(project, *, max_lead=DEFAULT_MAX_LEAD, max_jump=DEFAULT_MAX_JUMP):
    """跑反派 scaling 全检，返回 {ran, alerts, ...}。registry 缺 / 无反派标注 → 优雅跳过。"""
    reg = _load_registry(project)
    if reg is None:
        return {"ran": False,
                "skipped": "无 设定/power_system_registry.json——先 novel-create 立项脚手架或手建"}
    tiers = reg.get("tiers") or {}
    progression = reg.get("progression") or []
    role_by_char = _roster_roles(reg)
    by_char = _ranked_snaps(progression, tiers, role_by_char)

    # 角色按 role 归类（快照里出现过的 role 也并进来）。
    char_role = dict(role_by_char)
    for char, snaps in by_char.items():
        for _ch, _r, _t, role in snaps:
            if role and char not in char_role:
                char_role[char] = role
                break

    protags = [c for c in by_char if is_protagonist(char_role.get(c, ""))]
    antags = [c for c in by_char if is_antagonist(char_role.get(c, ""))]
    if not antags:
        return {"ran": True, "alerts": [], "total": 0, "blocking": 0,
                "note": "registry 无任何角色被标为反派（role/阵营）——无法推断威胁，跳过 scaling 检测；"
                        "如需检测请在 progression 快照或 roster 标 role=\"antagonist\"/\"反派\""}

    alerts = []

    # (A) 逐章威胁差距：每个既有主角快照又有 ≥1 反派快照的章，比 tier 领先。
    #     反派"在场 rank"取截至该章其最近一笔快照（反派常不是每章都出现）。
    protag_points = []  # (chapter, rank) 排序
    for c in protags:
        protag_points.extend((ch, r) for ch, r, _t, _role in by_char[c])
    protag_points.sort(key=lambda x: x[0])

    def _latest_rank_upto(char, chapter):
        best = None
        for ch, r, _t, _role in by_char[char]:
            if ch <= chapter:
                best = r
            else:
                break
        return best

    for ch, p_rank in protag_points:
        active = [(c, _latest_rank_upto(c, ch)) for c in antags]
        active_ranks = [(c, r) for c, r in active if r is not None]
        if not active_ranks:
            continue
        gap = threat_gap(p_rank, [r for _c, r in active_ranks])
        if scaling_band(gap, max_lead) == "warn":
            strongest = max(active_ranks, key=lambda cr: cr[1])
            alerts.append(_alert(
                "threat_underscaled", "威胁缺位", "建议级", ch,
                f"第{ch}章主角(序{p_rank:g})领先最强在场反派`{strongest[0]}`(序{strongest[1]:g}) {gap} 个 tier（>{max_lead}）",
                "主角碾压全场反派，张力缺位（爽文无敌→读者流失）：拉高反派战力 / 引入更高阶威胁 / 给主角设非战力困境"))

    # (B) 逐反派自身暴涨：相邻快照 tier 跳变 > max_jump 且对应快照无代价词。
    for c in antags:
        snaps = by_char[c]
        prev_rank = prev_ch = None
        for ch, r, raw_tier, _role in snaps:
            if prev_rank is not None and antag_spike_band(prev_rank, r, max_jump) == "warn":
                # 代价/机缘豁免：查该反派最近一笔快照的 spike_reason 字段。
                reason = ""
                for snap in progression:
                    if (isinstance(snap, dict)
                            and str(snap.get("character") or "") == c
                            and _num(snap.get("chapter")) == ch):
                        reason = str(snap.get("spike_reason") or snap.get("regress_reason") or "")
                        break
                if not any(k in reason for k in SPIKE_JUSTIFY_KEYWORDS):
                    alerts.append(_alert(
                        "antagonist_power_spike", c, "建议级", ch,
                        f"反派`{c}`第{prev_ch}→{ch}章 tier 序 {prev_rank:g}→{r:g}（跳 {int(r - prev_rank)}>{max_jump}）`{raw_tier}`",
                        "反派战力崩坏（突兀膨胀）：无铺垫地暴涨为反派临时加戏，读者会出戏；"
                        "分段铺垫成长或在快照写 spire/spike_reason 标明代价/机缘"))
            prev_rank, prev_ch = r, ch

    blocking = sum(1 for a in alerts if a["severity"] == "阻断级")  # 本检测器全建议级 → 恒 0
    return {"ran": True, "alerts": alerts, "total": len(alerts), "blocking": blocking,
            "protagonists": protags, "antagonists": antags}


# ── IO + main ─────────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(description="反派/威胁战力 scaling 检测器（反向战力崩坏）")
    ap.add_argument("project_path")
    ap.add_argument("--max-lead", type=int, default=DEFAULT_MAX_LEAD,
                    help="主角领先所有在场反派多少 tier 算威胁缺位")
    ap.add_argument("--max-jump", type=int, default=DEFAULT_MAX_JUMP,
                    help="反派相邻快照 tier 跳变多少算突兀膨胀")
    ap.add_argument("--advisory", action="store_true",
                    help="本检测器输出本就全为建议级（advisory），此旗标仅为与同线工具对齐，不改变严重度")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    res = analyze(args.project_path, max_lead=args.max_lead, max_jump=args.max_jump)
    out = os.path.join(args.project_path, "审稿", "antagonist_findings.json")
    if res.get("ran"):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    if not res.get("ran"):
        print("ℹ️ " + res.get("skipped", "skipped"))
        return 0
    if res.get("note") and not res["total"]:
        print("ℹ️ " + res["note"])
        return 0
    icon = "⚠️" if res["total"] else "✅"
    print(f"{icon} 反派战力 scaling 自检：{res['total']} 项建议级 → {out}")
    for a in res["alerts"]:
        print(f"  ⚠️ [{a['type']}] 第{a.get('chapter')}章 {a['entity']}：{a['evidence']}")
    # advisory：全建议级，恒 0 退出——这些是节奏/设计信号，不是硬矛盾，不该硬挡 post_write。
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
