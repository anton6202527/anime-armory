#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一致性 detector 治理清单（detector consolidation self-audit）。

为什么需要它：n2d 的一致性机检经多轮加固已累积 ~40 个 detector 模块。意图黑板
（`n2d_intent.shot_intent`）+ `state_continuity` 上线后，一批早期 detector 的职责可能已被
"源头锁死"覆盖；项目守则反复强调"检测→源头锁死、解耦不加锁、别建重复"。本脚本把"该不该
合并/退役某个 detector"从一次性人脑判断，变成**可重复跑的机检**：枚举每个 detector，机检它
被谁消费（审计编排 / 阶段 gate / 验收总账），把**孤儿**（无任何消费者 = 要么死代码该退役、
要么漏接线该补闸）和完整消费矩阵摆出来，供人按证据决定合并，绝不自动删。

判据（"在位与否是否影响生产推进"，与契约横切口径一致）：
  - wired    = 被 `consistency_audit.py` 编排（进汇总分档表）
  - gate     = 被 `gate.py` 消费（能在阶段闸门阻断/告警）
  - ledger   = 被 `consistency_ledger.py` 收进验收总账
  - dashboard= 被 `n2d-dashboard/scripts/dashboard.py` 直接消费（进入生产总账/噪声指标）
  - advisory = detector 源码明确声明 advisory-only（只提示/降噪，不作硬阻断）
  - disabled = detector 源码显式标记停用（`N2D_DETECTOR_DISABLED = True`）
  - peer     = 被另一个 detector 模块消费（子检测器，如 state_pixel_contract 被 state_continuity 调）
  - orphan   = 以上消费/治理路径皆无 → 候选退役/合并，或漏接线（人判二选一）

注意 peer 维度治的是"传递消费"假阳性：一个被 wired detector 内部调用的子检测器不是孤儿。

用法：
    python3 detector_inventory.py            # markdown 报告
    python3 detector_inventory.py --json     # 机读
    python3 detector_inventory.py --strict   # 有 orphan 退出码 1（供 CI/流程自审）
从本目录跑测试：cd skills/n2d/n2d-review/scripts && python3 -m pytest test_detector_inventory.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
from typing import Dict, List, Optional, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))

# 这些是编排/基建/共享模块，本身不是"一个一致性维度的 detector"，不计入清单。
_INFRA = {
    "consistency_audit",            # 编排器
    "consistency_ledger",          # 验收总账
    "series_ledger",               # 剧级总账
    "consistency_dependency_graph",  # 依赖图
    "consistency_threshold_registry",  # 阈值注册表
    "video_consistency_common",    # 视频检测共享工具
    "state_ledger_build",          # 确定性状态账本生成
    "intentional_discontinuity",   # 签收消费器（逃生口，不是 detector）
    "face_compare_stitch",         # 人审拼图渲染
    "self_audit",                  # 流程自审本体
    "detector_inventory",          # 本脚本
    "gate",                        # 闸门本体
}

# 个别 detector 命名不带 _consistency/_continuity 后缀，显式纳入。
_EXTRA_DETECTORS = {
    "quality_check",
    "expression_verification",
    "state_pixel_verify",
    "state_pixel_contract",
}


def discover_detectors(scripts_dir: str) -> List[str]:
    """返回 detector 模块 stem 列表（去基建、去 test_）。"""
    stems = set()
    try:
        for fn in os.listdir(scripts_dir):
            if not fn.endswith(".py") or fn.startswith("test_"):
                continue
            stem = fn[:-3]
            if stem in _INFRA:
                continue
            if stem.endswith("_consistency") or stem.endswith("_continuity") or stem in _EXTRA_DETECTORS:
                stems.add(stem)
    except OSError:
        pass
    return sorted(stems)


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def _references(stem: str, source: str) -> bool:
    """consumer 源码里是否引用了该 detector（import 或字面量名）。整词边界，避免子串误命中。"""
    return re.search(r"\b" + re.escape(stem) + r"\b", source) is not None


def _is_advisory_source(source: str) -> bool:
    return bool(re.search(r"\badvisory\b|只\s*warn|不阻断|绝不.*block|never\s+block", source, re.I))


def _is_disabled_source(source: str) -> bool:
    return bool(re.search(r"\bN2D_DETECTOR_DISABLED\s*=\s*True\b|\bDETECTOR_DISABLED\s*=\s*True\b", source))


def build_inventory(scripts_dir: str) -> Dict[str, object]:
    detectors = discover_detectors(scripts_dir)
    consumers = {
        "wired": _read(os.path.join(scripts_dir, "consistency_audit.py")),
        "gate": _read(os.path.join(scripts_dir, "gate.py")),
        "ledger": _read(os.path.join(scripts_dir, "consistency_ledger.py")),
        "dashboard": _read(os.path.join(os.path.dirname(scripts_dir), "..", "n2d-dashboard", "scripts", "dashboard.py")),
    }
    # peer 消费：把每个 detector 模块自身源码读出来，互查引用（子检测器治传递消费假阳性）。
    detector_sources = {stem: _read(os.path.join(scripts_dir, stem + ".py")) for stem in detectors}
    rows: List[Dict[str, object]] = []
    for stem in detectors:
        consumed = {role: _references(stem, src) for role, src in consumers.items()}
        source = detector_sources.get(stem, "")
        peer = any(other != stem and _references(stem, src) for other, src in detector_sources.items())
        advisory = _is_advisory_source(source)
        disabled = _is_disabled_source(source)
        is_orphan = not any(consumed.values()) and not peer and not advisory and not disabled
        rows.append({
            "detector": stem,
            "wired": consumed["wired"],
            "gate": consumed["gate"],
            "ledger": consumed["ledger"],
            "dashboard": consumed["dashboard"],
            "advisory": advisory,
            "disabled": disabled,
            "peer": peer,
            "orphan": is_orphan,
            "governance_path": (
                "disabled" if disabled else
                "gate" if consumed["gate"] else
                "dashboard" if consumed["dashboard"] else
                "ledger" if consumed["ledger"] else
                "wired" if consumed["wired"] else
                "peer" if peer else
                "advisory" if advisory else
                "orphan"
            ),
        })
    orphans = [r["detector"] for r in rows if r["orphan"]]
    return {
        "kind": "n2d_detector_inventory",
        "version": 1,
        "total": len(rows),
        "orphans": orphans,
        "counts": {
            "wired": sum(1 for r in rows if r["wired"]),
            "gate": sum(1 for r in rows if r["gate"]),
            "ledger": sum(1 for r in rows if r["ledger"]),
            "dashboard": sum(1 for r in rows if r["dashboard"]),
            "advisory": sum(1 for r in rows if r["advisory"]),
            "disabled": sum(1 for r in rows if r["disabled"]),
            "peer": sum(1 for r in rows if r["peer"]),
            "orphan": len(orphans),
        },
        "rows": rows,
    }


def render_markdown(inv: Dict[str, object]) -> str:
    rows = inv.get("rows", [])  # type: ignore[assignment]
    c = inv.get("counts", {})  # type: ignore[assignment]
    yn = lambda b: "✅" if b else "—"
    lines = [
        "# 一致性 detector 治理清单",
        "",
        f"- detector 总数：{inv.get('total')}",
        f"- 进编排 {c.get('wired', 0)} · 进 gate {c.get('gate', 0)} · 进 dashboard {c.get('dashboard', 0)} "
        f"· 进验收总账 {c.get('ledger', 0)} · advisory {c.get('advisory', 0)} · disabled {c.get('disabled', 0)} "
        f"· 子检测器 {c.get('peer', 0)} · 孤儿 {c.get('orphan', 0)}",
        "",
        "| detector | 编排 | gate | dashboard | 验收总账 | advisory | disabled | 子检测器 | 治理路径 | 孤儿 |",
        "|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---|:--:|",
    ]
    for r in sorted(rows, key=lambda x: (not x["orphan"], x["detector"])):
        lines.append(f"| {r['detector']} | {yn(r['wired'])} | {yn(r['gate'])} | {yn(r['dashboard'])} | "
                     f"{yn(r['ledger'])} | {yn(r['advisory'])} | {yn(r['disabled'])} | {yn(r['peer'])} | "
                     f"{r['governance_path']} | {'⚠️' if r['orphan'] else '—'} |")
    orphans = inv.get("orphans", [])
    if orphans:
        lines += [
            "",
            "## ⚠️ 孤儿 detector（候选退役/合并，或漏接线——人判二选一，勿自动删）",
            "",
        ]
        for o in orphans:
            lines.append(f"- `{o}`：无任何编排/gate/总账消费者。先 grep 确认是否被别处直接调用，"
                         "再判定『退役/并入近义 detector』或『补接进 consistency_audit/gate』。")
    else:
        lines += ["", "✅ 无孤儿 detector：每个一致性维度都至少被一处消费。"]
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scripts-dir", default=HERE, help="detector 所在目录（默认本脚本同目录）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="有孤儿 detector 退出码 1")
    ns = ap.parse_args(argv)
    inv = build_inventory(ns.scripts_dir)
    if ns.json:
        print(json.dumps(inv, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_markdown(inv))
    return 1 if (ns.strict and inv["orphans"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
