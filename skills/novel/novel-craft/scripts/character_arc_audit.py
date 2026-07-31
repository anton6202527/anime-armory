#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""character_arc_audit.py — 人物弧线推进机检（advisory·纯标准库）。

为什么：scene_cards 已有完整的人物引擎字段（want/need/misbelief/wound/fear/tactic/
moral_boundary/choice_cost，对应 K.M. Weiland 的 Lie/Want/Need 弧线内构），但此前只有
"字段填没填"的静态检查（scene_cards.py check）——**没有任何东西看这些字段跨章是否在
推进**。弧线是时间性的：谎言(misbelief)要被一次次挑战、每次挑战要付代价(choice_cost)、
Want 和 Need 要逐渐撕开——字段填了但从不变化=弧线纸面化，人物"有设定没有弧"。

三条确定性信号（全 advisory·blocking 恒 0——弧线兑现与否终归 LLM/人判，
本模块只把"计划面上的弧线停摆"变成可见候选）：

  ① WANT-NEED-COLLAPSED   同一场景卡 want 与 need 填了但**逐字相同**——Weiland：
                          Want 是情节目标（表层驱动），Need 是主题真值（内在缺口），
                          二者相同=人物没有内外张力，弧线无从展开。（info）
  ② MISBELIEF-NO-COST-RUN 某 POV 角色连续 ≥N 章场景卡都登记 misbelief 却全程
                          choice_cost 为空——谎言挂在设定里却从不逼人物付代价去
                          维护/动摇它=弧线停摆。传统手艺：信念只有在**付了代价的
                          选择**里才显形。（建议级）
  ③ ARC-ENGINE-DECAY      人物引擎字段填充率前段 vs 后段跌半——开书时认真填
                          want/misbelief，写到中后期场景卡人物引擎整体荒废，
                          是"人设前紧后松"的计划期先兆。（建议级）

用法：
    python3 character_arc_audit.py <作品根> [--json]
测试：cd skills/novel/novel-craft/scripts && python3 -m pytest test_character_arc_audit.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

_HERE = os.path.dirname(os.path.abspath(__file__))

try:
    from scene_cards import CHARACTER_ENGINE_FIELDS, load_json, scene_path
except Exception:  # pragma: no cover - 独立跑兜底
    CHARACTER_ENGINE_FIELDS = ("want", "need", "misbelief", "wound", "fear",
                               "tactic", "moral_boundary", "choice_cost")

    def load_json(path, default=None):  # type: ignore
        if not os.path.exists(path):
            return default
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def scene_path(root):  # type: ignore
        return os.path.join(root, "设定", "scene_cards.json")

# ── 阈值（internal-heuristic·env 可标定·全 advisory）─────────────────────────
NO_COST_RUN = int(os.environ.get("NOVEL_ARC_NO_COST_RUN", "6"))       # misbelief 无代价连续章数
DECAY_MIN_CHAPTERS = int(os.environ.get("NOVEL_ARC_DECAY_MIN_CH", "9"))   # 衰减判定最少章数
DECAY_RATIO = float(os.environ.get("NOVEL_ARC_DECAY_RATIO", "0.5"))   # 后段/前段填充率跌破比例
DECAY_FLOOR = float(os.environ.get("NOVEL_ARC_DECAY_FLOOR", "0.5"))   # 前段填充率至少这么高才谈衰减
PROVENANCE = "internal-heuristic·confidence=low"


def _filled(card: dict, field: str) -> bool:
    return bool(str(card.get(field) or "").strip())


def _cards_by_chapter(scenes: list) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    for sc in scenes:
        if isinstance(sc, dict) and isinstance(sc.get("chapter"), int):
            out.setdefault(sc["chapter"], []).append(sc)
    return out


def want_need_collapsed(scenes: list) -> list[dict[str, Any]]:
    """want 与 need 同卡逐字相同的告警列表。纯函数·可测。"""
    alerts = []
    for sc in scenes:
        if not isinstance(sc, dict):
            continue
        want = str(sc.get("want") or "").strip()
        need = str(sc.get("need") or "").strip()
        if want and want == need:
            alerts.append({
                "type": "WANT-NEED-COLLAPSED", "severity": "info", "auto": True,
                "chapter": sc.get("chapter"), "scene_id": sc.get("id"),
                "note": (f"第{sc.get('chapter')}章场景卡 {sc.get('id')} 的 want 与 need 逐字相同"
                         f"（「{want[:20]}」）——Want 是情节目标、Need 是内在缺口，二者相同="
                         f"人物没有内外张力；把 Need 挖到 Want 的水面之下（{PROVENANCE}）"),
            })
    return alerts


def misbelief_no_cost_runs(scenes: list, run_len: int = None) -> list[dict[str, Any]]:
    """按 POV 分组：连续 ≥run_len 章登记 misbelief 却全程无 choice_cost → 弧线停摆。纯函数。

    章级归并：同章多卡，任一卡有 choice_cost 即算该章"付了代价"（宁缺毋滥）。
    """
    run_len = run_len or NO_COST_RUN
    by_pov: dict[str, dict[int, dict[str, bool]]] = {}
    for sc in scenes:
        if not isinstance(sc, dict) or not isinstance(sc.get("chapter"), int):
            continue
        pov = str(sc.get("pov") or "").strip()
        if not pov:
            continue
        ch = by_pov.setdefault(pov, {}).setdefault(sc["chapter"], {"misbelief": False, "cost": False})
        ch["misbelief"] = ch["misbelief"] or _filled(sc, "misbelief")
        ch["cost"] = ch["cost"] or _filled(sc, "choice_cost")

    alerts = []
    for pov, chapters in by_pov.items():
        run: list[int] = []

        def _flush():
            if len(run) >= run_len:
                alerts.append({
                    "type": "MISBELIEF-NO-COST-RUN", "severity": "建议级", "auto": True,
                    "entity": pov, "chapters": list(run), "chapter": run[0],
                    "note": (f"POV「{pov}」第{run[0]}–{run[-1]}章连续 {len(run)} 章登记了 misbelief"
                             f"（人物的谎言/误信）却全程 choice_cost 为空——谎言从不逼人物付代价="
                             f"弧线停摆。Weiland 手艺：信念只有在付了代价的选择里才显形；"
                             f"安排一场让 misbelief 帮他赢（付隐性代价）或让它坑他（付显性代价）"
                             f"的戏（{PROVENANCE}）"),
                })
            run.clear()

        for ch in sorted(chapters):
            flags = chapters[ch]
            if flags["misbelief"] and not flags["cost"]:
                if run and ch != run[-1] + 1:
                    _flush()
                run.append(ch)
            else:
                _flush()
        _flush()
    return alerts


def engine_decay(scenes: list) -> list[dict[str, Any]]:
    """人物引擎字段填充率：前 1/3 章 vs 后 1/3 章跌破 DECAY_RATIO → 计划纪律衰减。纯函数。"""
    by_ch = _cards_by_chapter(scenes)
    chs = sorted(by_ch)
    if len(chs) < DECAY_MIN_CHAPTERS:
        return []

    def _fill_rate(chapter_ids):
        total = hit = 0
        for cid in chapter_ids:
            for card in by_ch[cid]:
                for field in CHARACTER_ENGINE_FIELDS:
                    total += 1
                    hit += 1 if _filled(card, field) else 0
        return hit / total if total else 0.0

    third = len(chs) // 3
    head, tail = _fill_rate(chs[:third]), _fill_rate(chs[-third:])
    if head >= DECAY_FLOOR and tail < head * DECAY_RATIO:
        return [{
            "type": "ARC-ENGINE-DECAY", "severity": "建议级", "auto": True,
            "head_fill": round(head, 2), "tail_fill": round(tail, 2),
            "note": (f"人物引擎字段填充率从前段 {head:.0%} 跌到后段 {tail:.0%}（跌破 "
                     f"{DECAY_RATIO:.0%}）——开书认真填 want/misbelief/choice_cost，中后期"
                     f"场景卡人物引擎荒废，是『人设前紧后松』的计划期先兆；补卡或承认"
                     f"降级并让 review 侧加密人物一致性抽查（{PROVENANCE}）"),
        }]
    return []


def analyze(project: str) -> dict[str, Any]:
    """consistency_audit 子检测器契约：{ran, alerts, total, blocking(=0)}。

    无场景卡/人物引擎从未启用（全部卡引擎字段全空）→ 优雅跳过，不臆造。
    """
    data = load_json(scene_path(project), {}) or {}
    scenes = [s for s in (data.get("scenes") or []) if isinstance(s, dict)]
    if data.get("kind") != "novel_scene_cards" or not scenes:
        return {"ran": False, "skipped": "无 scene_cards——先有场景卡再查弧线推进"}
    if not any(_filled(sc, f) for sc in scenes for f in CHARACTER_ENGINE_FIELDS):
        return {"ran": False, "skipped": "场景卡人物引擎字段从未启用——弧线推进无从对账"}

    alerts = want_need_collapsed(scenes) + misbelief_no_cost_runs(scenes) + engine_decay(scenes)
    return {
        "ran": True,
        "thresholds": {"no_cost_run": NO_COST_RUN, "decay_ratio": DECAY_RATIO,
                       "decay_floor": DECAY_FLOOR, "provenance": PROVENANCE,
                       "note": "advisory：弧线兑现与否归 LLM/人判；本模块只报计划面停摆候选。"},
        "alerts": alerts,
        "total": len(alerts),
        "blocking": 0,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="人物弧线推进机检（advisory）")
    ap.add_argument("project_root")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    res = analyze(os.path.abspath(args.project_root))
    if res.get("ran"):
        out = os.path.join(args.project_root, "审稿", "character_arc_findings.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    if not res.get("ran"):
        print("ℹ️ " + res.get("skipped", "skipped"))
        return 0
    icon = "⚠️" if res["total"] else "✅"
    print(f"{icon} 人物弧线推进机检：{res['total']} 条提示")
    for a in res["alerts"]:
        print(f"  - [{a['severity']}] {a['type']}: {a['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
