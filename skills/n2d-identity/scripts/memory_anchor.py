#!/usr/bin/env python3
"""G2 跨集全局记忆锚（series-level memory-sink anchor）。

2026 SOTA（StoryMem 2512.19539 / EntityMem·EntityBench 2605.15199 / Context Forcing
2602.06028）实证：跨镜身份一致性**随复现间隔急剧衰减**（EntityBench Appendix F.5 "Gap-Decay
Analysis"）；顶尖流水线不止「每镜从定妆库重注入参考」，还把**早期集的关键帧钉成全局记忆锚
（memory-sink）**，在角色长间隔再登场 / 晚集累积漂移时优先重注入，治「逐镜重注入仍随 gap 衰减」。

n2d 已有两层定妆库 + B4 复现距离加权（identity.compute_recurrence）。本模块补缺的「memory-sink」
层：为目标集逐角色判定**是否需要把最早定妆记忆锚重注入**，产 report-only 计划
`生产数据/memory_anchor_plan_第N集.json`，供 n2d-image/reference_planner 出图前作为高优先锚消费
（文件契约·跨 skill 不互 import，守独立性）。永不阻断——只前置参考、降 gap 衰减风险。

用法：python3 memory_anchor.py <作品根> 第N集 [--json]
纯 stdlib；规划是纯函数，有 pytest 覆盖（test_memory_anchor.py）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMMON = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "n2d", "_lib"))
for _p in (SCRIPT_DIR, COMMON):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from identity import (  # noqa: E402  同 skill 内复用，独立性允许
    RECURRENCE_GAP_THRESHOLD,
    REFERENCE_FIELDS,
    episode_sort_key,
)

PLAN_KIND = "n2d_memory_anchor_plan"
VERSION = 1

# 距首登场 ≥ LATE_GAP 集即视为「晚集」——即便不是长间隔再登场，累积漂移也该把记忆锚重注入。
LATE_GAP = int(os.environ.get("N2D_MEMORY_LATE_GAP", "5") or "5")
# 单角色记忆锚最多注入几张（front 优先；避免参考预算被记忆锚挤爆逐镜变化锚）。
MAX_MEMORY_REFS = int(os.environ.get("N2D_MEMORY_MAX_REFS", "2") or "2")


def _ep_num(ep: str) -> Optional[int]:
    import re
    m = re.search(r"\d+", str(ep or ""))
    return int(m.group()) if m else None


def char_memory_anchors(registry: Mapping[str, Any]) -> Dict[str, List[str]]:
    """从 identity_registry 提每角色的「记忆锚参考」（front 优先的定妆锚路径，最多 MAX_MEMORY_REFS 张）。

    键同 drift_report.characters 的键（form.asset_key 优先，回退 character.name），便于对齐。纯函数·可测。"""
    out: Dict[str, List[str]] = {}
    chars = registry.get("characters") if isinstance(registry, Mapping) else None
    for char in (chars or []):
        if not isinstance(char, Mapping):
            continue
        name = str(char.get("name", "")).strip()
        for form in char.get("forms", []) or []:
            if not isinstance(form, Mapping):
                continue
            rg = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
            refs: List[str] = []
            for key in REFERENCE_FIELDS:  # front, side, back, ... —— front 居首=正脸主锚
                rel = str(rg.get(key, "")).strip()
                if rel and rel not in refs:
                    refs.append(rel)
                if len(refs) >= MAX_MEMORY_REFS:
                    break
            if not refs:
                continue
            key = str(form.get("asset_key", "")).strip() or name
            if key and key not in out:
                out[key] = refs
        if name and name not in out:
            # 角色无 form 级 reference_group 但有 name → 记空位（让规划仍可标 reinject，参考由人补）
            out.setdefault(name, [])
    return out


def memory_anchor_rows(
    characters: Mapping[str, Any],
    anchors: Mapping[str, Sequence[str]],
    target_ep: str,
    *,
    gap_threshold: int = RECURRENCE_GAP_THRESHOLD,
    late_gap: int = LATE_GAP,
) -> List[Dict[str, Any]]:
    """逐角色判定目标集是否需重注入记忆锚。纯函数·可测（report-only，永不 block）。

    characters：drift_report["characters"]（每角色带 episodes / recurrence / total_block）。
    anchors：char → 记忆锚参考路径（char_memory_anchors 提取）。
    触发任一即 reinject：① 目标集是长间隔再登场（gap≥gap_threshold）② 距首登场≥late_gap 集
    ③ 该角色已测出跨集漂移（total_block>0 或 recurrence.high_risk）。"""
    rows: List[Dict[str, Any]] = []
    tnum = _ep_num(target_ep)
    for char, info in (characters or {}).items():
        if not isinstance(info, Mapping):
            continue
        eps = sorted(
            (str(e).strip() for e in (info.get("episodes") or {}).keys() if str(e).strip()),
            key=episode_sort_key,
        )
        if not eps:
            continue
        appears_here = str(target_ep).strip() in eps
        if not appears_here:
            continue  # 只为「本集真出场」的角色前置记忆锚
        first_ep = eps[0]
        rec = info.get("recurrence") if isinstance(info.get("recurrence"), Mapping) else {}
        reentries = rec.get("long_gap_reentries") if isinstance(rec.get("long_gap_reentries"), list) else []

        reasons: List[str] = []
        gap_hit = next((r for r in reentries
                        if isinstance(r, Mapping) and str(r.get("at", "")).strip() == str(target_ep).strip()
                        and int(r.get("gap", 0) or 0) >= gap_threshold), None)
        if gap_hit:
            reasons.append(f"长间隔再登场(gap={gap_hit.get('gap')}·上次第{_ep_num(str(gap_hit.get('prev','')))}集)"
                           "·EntityBench 缺口衰减")
        fnum, target_num = _ep_num(first_ep), tnum
        if first_ep != target_ep and fnum is not None and target_num is not None and (target_num - fnum) >= late_gap:
            reasons.append(f"距首登场{target_num - fnum}集(≥{late_gap})·晚集累积漂移防护")
        if int(info.get("total_block", 0) or 0) > 0 or bool(rec.get("high_risk")):
            reasons.append("已测出跨集漂移·重锚记忆锚")

        if not reasons:
            continue
        rows.append({
            "char": char,
            "reinject": True,
            "reason": "；".join(reasons),
            "memory_sink_episode": first_ep,
            "memory_anchor_refs": list(anchors.get(char) or []),
            "recurrence": {"max_gap": rec.get("max_gap", 0), "high_risk": bool(rec.get("high_risk"))},
        })
    rows.sort(key=lambda r: str(r.get("char", "")))
    return rows


def build_plan(root: str, ep: str) -> Dict[str, Any]:
    rootp = Path(root)
    drift = _load(rootp / "生产数据" / "identity_drift_report.json")
    registry = _load(rootp / "identity_registry.json") or _load(rootp / "设定库" / "identity_registry.json")
    notes: List[str] = []
    if not isinstance(drift, Mapping) or not drift.get("characters"):
        notes.append("缺 identity_drift_report.json（先跑 identity.py --write）——无跨集出场/复现数据，记忆锚规划跳过。")
        return {"kind": PLAN_KIND, "version": VERSION, "episode": ep, "available": False,
                "rows": [], "notes": notes}
    anchors = char_memory_anchors(registry) if isinstance(registry, Mapping) else {}
    if not anchors:
        notes.append("缺 identity_registry 或无 reference_group 定妆锚——仍按出场/复现标 reinject，记忆锚参考路径留空待人补。")
    rows = memory_anchor_rows(drift.get("characters", {}), anchors, ep)
    if not rows:
        notes.append("本集无需重注入记忆锚（无长间隔再登场 / 晚集 / 已测漂移角色）。")
    return {"kind": PLAN_KIND, "version": VERSION, "episode": ep, "available": True,
            "rows": rows, "notes": notes}


def _load(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_plan(root: str, ep: str, plan: Mapping[str, Any]) -> str:
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"memory_anchor_plan_{ep}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=2, sort_keys=True)
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    ns = ap.parse_args(argv)
    plan = build_plan(ns.root.rstrip("/"), ns.episode)
    if not ns.no_write and plan.get("available"):
        plan["path"] = write_plan(ns.root.rstrip("/"), ns.episode, plan)
    if ns.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"记忆锚规划 {ns.episode}：available={plan.get('available')}，{len(plan.get('rows', []))} 角色需重注入")
        for r in plan.get("rows", []):
            print(f"  · {r['char']}（记忆锚来自{r['memory_sink_episode']}）：{r['reason']}")
        for n in plan.get("notes", []):
            print(f"  - {n}")
    return 0  # report-only，永不非零退出


if __name__ == "__main__":
    raise SystemExit(main())
