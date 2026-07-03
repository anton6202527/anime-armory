#!/usr/bin/env python3
"""道具/特效状态演进结构化 + 机检（F）——把 asset_registry 的自由文本 lifecycle 升级为可机检状态机。

为什么：角色的伤/泪/妆/服有 `state_continuity.py` 机检单调推进不回退；道具/特效却只在 asset_registry
里写**自由文本** lifecycle（"Clip01-05 完整，毒酒倒入后摔碎…"），机器读不懂、查不了"摔碎的瓶子后面又
完好了"这种回退穿帮。本模块定义**可选的结构化 lifecycle**（向后兼容自由文本），并机检：
  - states：有序状态列表（intact → cracked → shattered，下标即时间序、不可回退）；
  - transitions：[{from, to, at_clip, trigger}]——from/to 必须是已声明 state，且 to 必须在 from **之后**
    （idx[to] > idx[from]）否则 = 状态回退（道具破了又自愈 / 特效退级）→ block；
  - VFX 多形态/颜色拖尾参数：forms[]（各形态各自定妆）、vfx_params.color_target / trail（锁颜色拖尾防窜色）。

自由文本 lifecycle 仍合法（info 提示"升级为结构化可机检回退"，不 block）——结构化是 opt-in 增强。

用法：python3 asset_lifecycle.py <作品根> [--json]
纯 stdlib；状态机校验纯函数有 pytest 覆盖。被 image_qc 作为 registry 级 advisory lint 调用。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence


# ── 纯函数（无依赖·可测） ──────────────────────────────────────────────────────

def is_structured_lifecycle(lifecycle: Any) -> bool:
    """lifecycle 是否为结构化（dict 且含 states 列表）。自由文本/缺失 → False。纯函数·可测。"""
    return isinstance(lifecycle, dict) and isinstance(lifecycle.get("states"), list)


def validate_lifecycle(asset: Mapping[str, Any]) -> List[Dict[str, str]]:
    """单个资产的 lifecycle/forms/vfx_params 校验 → findings [{level, code, asset, msg}]。纯函数·可测。

    结构化 lifecycle：states 有序、transitions 引用合法 state 且严格前进（回退=block）。
    自由文本 lifecycle：info（建议升级），不 block。
    """
    aid = str(asset.get("id") or "?")
    findings: List[Dict[str, str]] = []
    lc = asset.get("lifecycle")

    if not is_structured_lifecycle(lc):
        if isinstance(lc, str) and lc.strip():
            findings.append({"level": "info", "code": "lifecycle_freetext", "asset": aid,
                             "msg": f"{aid}：lifecycle 为自由文本，机器查不了状态回退；含状态演进（破损/消耗/升级）的道具"
                                    "建议升级为结构化 {states:[…], transitions:[{from,to,at_clip}]} 以机检不回退。"})
        return findings

    states = [str(s) for s in (lc.get("states") or [])]
    transitions = lc.get("transitions") or []
    if len(states) < 2:
        findings.append({"level": "warn", "code": "lifecycle_states_thin", "asset": aid,
                         "msg": f"{aid}：结构化 lifecycle 的 states 少于 2 个，状态机无意义（至少列起始态+终态）。"})
    if len(set(states)) != len(states):
        findings.append({"level": "warn", "code": "lifecycle_states_duplicate", "asset": aid,
                         "msg": f"{aid}：lifecycle.states 有重复，状态序无法定义时间序。"})
    idx = {s: i for i, s in enumerate(states)}
    if not isinstance(transitions, list):
        findings.append({"level": "warn", "code": "lifecycle_transitions_type", "asset": aid,
                         "msg": f"{aid}：lifecycle.transitions 必须是列表。"})
        transitions = []
    for tr in transitions:
        if not isinstance(tr, dict):
            findings.append({"level": "warn", "code": "lifecycle_transition_type", "asset": aid,
                             "msg": f"{aid}：transition 必须是对象 {{from,to,at_clip}}。"})
            continue
        fr = str(tr.get("from") or "")
        to = str(tr.get("to") or "")
        if fr not in idx:
            findings.append({"level": "block", "code": "lifecycle_unknown_from_state", "asset": aid,
                             "msg": f"{aid}：transition.from=`{fr}` 不在 states {states} 中。"})
        if to not in idx:
            findings.append({"level": "block", "code": "lifecycle_unknown_to_state", "asset": aid,
                             "msg": f"{aid}：transition.to=`{to}` 不在 states {states} 中。"})
        if fr in idx and to in idx and idx[to] <= idx[fr]:
            findings.append({"level": "block", "code": "lifecycle_regression", "asset": aid,
                             "msg": f"{aid}：状态回退/原地——transition `{fr}`→`{to}`（state 序 {idx[fr]}→{idx[to]}）"
                                    "不前进；道具破了不能自愈、特效不能退级，按时间序只能前进。"})

    # VFX 颜色/拖尾参数（防跨镜窜色）：有 vfx_params 时校验 color_target 结构
    params = asset.get("vfx_params")
    if params is not None and not isinstance(params, dict):
        findings.append({"level": "warn", "code": "vfx_params_type", "asset": aid,
                         "msg": f"{aid}：vfx_params 必须是对象（color_target/trail 等）。"})
    # forms 多形态：每个形态需有 id
    forms = asset.get("forms")
    if isinstance(forms, list):
        for f in forms:
            if not (isinstance(f, dict) and str(f.get("id") or "").strip()):
                findings.append({"level": "warn", "code": "form_missing_id", "asset": aid,
                                 "msg": f"{aid}：forms[] 每个形态需有 id（武器升级/特效分级各形态各自锁颜色拖尾）。"})
                break
    return findings


def validate_assets(assets: Sequence[Mapping[str, Any]]) -> List[Dict[str, str]]:
    """对一组资产逐个校验 lifecycle。纯函数·可测。"""
    out: List[Dict[str, str]] = []
    for a in assets or []:
        if isinstance(a, dict):
            out.extend(validate_lifecycle(a))
    return out


# ── registry 装载 + 汇总（best-effort I/O） ─────────────────────────────────────

def validate_registry(root: Path) -> Dict[str, Any]:
    """asset_registry.json → {available, findings, checked, structured, notes}。缺/损坏 → available False。"""
    path = Path(root) / "出图" / "共享" / "asset_registry.json"
    res: Dict[str, Any] = {"available": False, "findings": [], "checked": 0, "structured": 0, "notes": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        res["notes"].append("asset_registry.json 缺失/损坏——跳过资产状态机校验。")
        return res
    assets = data.get("assets") or []
    res["available"] = True
    res["checked"] = len(assets)
    res["structured"] = sum(1 for a in assets if isinstance(a, dict) and is_structured_lifecycle(a.get("lifecycle")))
    res["findings"] = validate_assets(assets)
    return res


def run(root: Path) -> Dict[str, Any]:
    res = validate_registry(root)
    blocks = [f for f in res["findings"] if f.get("level") == "block"]
    res["verdict"] = "block" if blocks else ("warn" if any(f.get("level") == "warn" for f in res["findings"]) else "ok")
    return res


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = run(Path(ns.root).expanduser().resolve())
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if not res["available"]:
        print("ℹ️ " + "；".join(res["notes"]))
        return 0
    icon = {"block": "⛔", "warn": "⚠️", "ok": "✅"}[res["verdict"]]
    print(f"{icon} 资产状态机校验：{res['verdict']}（{res['checked']} 资产，结构化 {res['structured']}）")
    for f in res["findings"]:
        mark = {"block": "⛔", "warn": "⚠️", "info": "ℹ️"}.get(f.get("level"), "·")
        print(f"  {mark} [{f.get('code')}] {f.get('msg')}")
    return 1 if res["verdict"] == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
