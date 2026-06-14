#!/usr/bin/env python3
"""出图前·物料漂移风险分（E）——场景/道具/武器·法宝/特效版的 face_drift_risk。

脸有 `face_drift_risk.py` 事前预测高危角色；场景/道具/特效同样需要：跨集反复复用的场景最容易
背景漂移、件数/拓扑多的道具最容易自相矛盾、多形态法宝/特效最容易在形态间窜色。本脚本在**出图前**
按 asset_registry + 本集分镜预测哪些物料本集容易漂，提前提示补多视图参考/锁结构/锁颜色拖尾/上状态机，
而不是等审片 multimodal 机检事后报。

风险信号（全来自 asset_registry.json + storyboard.json，不读像素、不花钱）：
  - 复用跨度  ：scope 含「全篇/反复/复用/第N集起」= 跨集反复出现，漂移机会多（背景每集重画必崩）；
  - 本集出镜  ：该资产名在本集分镜出现次数（越多越容易自相矛盾）；
  - 禁漂项数  ：drift_forbidden 越多 = 零容忍约束越密 = 越难全保住；
  - 约束强度  ：constraints 有 structure（拓扑/件数）/ light_anchor（光位）/ color（颜色拖尾）= 强锁需求；
  - 多形态    ：forms/morph_states（武器升级、特效分级）跨形态最易窜色/串结构。

输出 生产数据/asset_drift_risk_<ep>.json + .md，按风险排序，对 high/medium 物料给可执行建议
（补多视图、锁结构/颜色、上状态机[F]）。**只提示不阻断**（落档闸门是 image_qc / multimodal）。

用法：python3 asset_drift_risk.py <作品根> <第N集> [--json]
纯 stdlib；评分纯函数有 pytest 覆盖。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

# 跨集反复复用的口径（scope 文本命中即视为高复用，背景/道具每集重画必漂）。
REUSE_MARKERS = ("全篇", "反复", "复用", "跨集", "起复用", "贯穿", "长线")
TYPE_LABEL = {"scene": "场景", "location": "场景", "prop": "道具", "vfx": "特效", "effect": "特效",
              "outfit": "服装", "costume": "服装", "weapon": "武器"}

WEIGHTS = {"reuse_high": 25, "reuse_single": 6,
           "appear_each": 3, "appear_cap": 24,
           "drift_each": 4, "drift_cap": 20,
           "structure": 8, "color": 8, "multiform": 15}
BAND_HIGH, BAND_MEDIUM = 50, 28


# ── 纯函数（无依赖·可测） ──────────────────────────────────────────────────────

def reuse_base(scope: str) -> int:
    """scope 文本 → 复用底分。命中跨集复用词 = 高底分（背景/道具反复出现，漂移机会多）。纯函数·可测。"""
    return WEIGHTS["reuse_high"] if any(m in str(scope or "") for m in REUSE_MARKERS) else WEIGHTS["reuse_single"]


def score_asset(signals: Mapping[str, Any]) -> Dict[str, Any]:
    """风险分 + 档位 + 驱动因子（纯函数·可测）。

    signals: {reuse_base, appear, drift_forbidden, has_structure, has_color, has_multiform}。
    """
    base = int(signals.get("reuse_base", WEIGHTS["reuse_single"]))
    drivers: List[Dict[str, Any]] = [{"factor": "复用跨度", "points": base}]
    appear = min(int(signals.get("appear", 0)) * WEIGHTS["appear_each"], WEIGHTS["appear_cap"])
    drift = min(int(signals.get("drift_forbidden", 0)) * WEIGHTS["drift_each"], WEIGHTS["drift_cap"])
    structure = WEIGHTS["structure"] if signals.get("has_structure") else 0
    color = WEIGHTS["color"] if signals.get("has_color") else 0
    multiform = WEIGHTS["multiform"] if signals.get("has_multiform") else 0
    if appear:
        drivers.append({"factor": f"本集出镜 {signals.get('appear', 0)} 次", "points": appear})
    if drift:
        drivers.append({"factor": f"禁漂项 {signals.get('drift_forbidden', 0)} 个", "points": drift})
    if structure:
        drivers.append({"factor": "结构/件数强锁", "points": structure})
    if color:
        drivers.append({"factor": "颜色/拖尾强锁", "points": color})
    if multiform:
        drivers.append({"factor": "多形态(跨形态易窜色)", "points": multiform})
    score = min(base + appear + drift + structure + color + multiform, 100)
    band = "high" if score >= BAND_HIGH else ("medium" if score >= BAND_MEDIUM else "low")
    drivers.sort(key=lambda d: d["points"], reverse=True)
    return {"score": score, "band": band, "drivers": drivers}


def suggestions_for(atype: str, scored: Mapping[str, Any], signals: Mapping[str, Any]) -> List[str]:
    """按类型 + 驱动因子给可执行建议（与 multimodal 机检、F 状态机对齐）。纯函数·可测。"""
    out: List[str] = []
    label = TYPE_LABEL.get(atype, "资产")
    if reuse_base(str(signals.get("scope", ""))) >= WEIGHTS["reuse_high"]:
        out.append(f"{label}跨集反复复用——必进共享定妆库一次出、跨集都引用它当参考，别每集重画（背景漂移和脸漂一样穿帮）。")
    if atype in ("scene", "location"):
        if int(signals.get("appear", 0)) >= 3:
            out.append("本集高频场景：补场景四视图/不同机位参考，锁 layout/axis/light_anchor，反打不越轴。")
    if signals.get("has_structure"):
        out.append("结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。")
    if signals.get("has_color"):
        out.append("颜色/拖尾强锁：写死 color_target(HSV) 与拖尾长度，避免跨镜窜色（特效最易漂）。")
    if signals.get("has_multiform"):
        out.append("多形态：每个形态各自定妆 + 各自锁颜色拖尾；用结构化 states/transitions（asset 状态机）防形态回退/窜色。")
    if scored.get("band") == "high":
        out.append(f"风险 high：出图后重点看 image_qc 道具/特效 P2 + 场景 O2 初筛，必要时上 asset 状态机结构化 lifecycle（防回退）。")
    return out


# ── 数据装载 + 推断（best-effort I/O） ──────────────────────────────────────────

def load_assets(root: Path) -> List[Dict[str, Any]]:
    """asset_registry.json → [{id, type, name, scope, drift_forbidden, constraints_keys, has_multiform, aliases}]。"""
    path = root / "出图" / "共享" / "asset_registry.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for a in (data.get("assets") or []):
        aid = str(a.get("id") or "").strip()
        if not aid:
            continue
        name = str(a.get("name") or "").strip()
        cons = a.get("constraints") or {}
        forms = a.get("forms") or a.get("morph_states")
        aliases = {name} if len(name) >= 2 else set()
        out.append({
            "id": aid, "type": str(a.get("type") or "").strip(), "name": name or aid,
            "scope": str(a.get("scope") or ""),
            "drift_forbidden": len(a.get("drift_forbidden") or []),
            "constraints_keys": list(cons.keys()) if isinstance(cons, dict) else [],
            "has_multiform": bool(forms),
            "aliases": aliases,
        })
    return out


def load_clip_texts(root: Path, ep: str) -> List[str]:
    """storyboard.json → 每 clip 的可匹配文本（label/scene/desc/continuity）。"""
    try:
        data = json.loads((root / "脚本" / ep / "storyboard.json").read_text(encoding="utf-8"))
    except Exception:
        return []
    out: List[str] = []
    for clip in (data.get("clips") or data.get("shots") or []):
        if not isinstance(clip, dict):
            continue
        parts = [str(clip.get("label") or ""), str(clip.get("scene") or "")]
        cont = clip.get("continuity") or {}
        parts += [str(cont.get("start_state") or ""), str(cont.get("end_state") or "")]
        for s in (clip.get("shots") or []):
            if isinstance(s, dict):
                parts.append(str(s.get("desc") or ""))
        out.append(" ".join(parts))
    return out


def analyze(root: Path, ep: str) -> Dict[str, Any]:
    assets = load_assets(root)
    clip_texts = load_clip_texts(root, ep)
    notes: List[str] = []
    if not assets:
        notes.append("asset_registry.json 缺失/无资产——无法算物料风险分。")
    if not clip_texts:
        notes.append("storyboard.json 缺失/无 clips——先跑 n2d-script 分镜设计再算风险。")
    results: List[Dict[str, Any]] = []
    for a in assets:
        appear = sum(1 for t in clip_texts if any(al and al in t for al in a["aliases"]))
        cons = a["constraints_keys"]
        signals = {
            "scope": a["scope"],
            "reuse_base": reuse_base(a["scope"]),
            "appear": appear,
            "drift_forbidden": a["drift_forbidden"],
            "has_structure": any(k in ("structure", "layout", "axis") for k in cons),
            "has_color": any(k in ("color", "lighting_signature", "light_anchor") for k in cons),
            "has_multiform": a["has_multiform"],
        }
        scored = score_asset(signals)
        results.append({
            "id": a["id"], "type": a["type"], "name": a["name"], "scope": a["scope"],
            "signals": {k: signals[k] for k in ("appear", "drift_forbidden", "has_structure",
                                                "has_color", "has_multiform", "reuse_base")},
            **scored,
            "suggestions": suggestions_for(a["type"], scored, signals),
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    return {
        "kind": "n2d_asset_drift_risk", "version": 1, "root": str(root), "episode": ep,
        "high": sum(1 for r in results if r["band"] == "high"),
        "medium": sum(1 for r in results if r["band"] == "medium"),
        "assets": results, "notes": notes,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    lines = [
        "# 出图前·物料漂移风险分（场景/道具/武器/特效·事前预测·只提示不阻断）",
        "",
        f"- episode: {report.get('episode')}",
        f"- 高危物料 🔴 {report.get('high', 0)} · 中危 🟡 {report.get('medium', 0)}",
        "",
        "| 资产 | 类型 | 风险 | 分 | 主驱动 |",
        "|---|---|---|---|---|",
    ]
    for r in report.get("assets", []):
        drv = "；".join(f"{d['factor']}(+{d['points']})" for d in r.get("drivers", [])[:3])
        lines.append(f"| {r['name']}（{r['id']}） | {TYPE_LABEL.get(r['type'], r['type'])} "
                     f"| {icon.get(r['band'], '?')} {r['band']} | {r['score']} | {drv} |")
    lines.append("")
    for r in report.get("assets", []):
        if r["band"] == "low" or not r.get("suggestions"):
            continue
        lines.append(f"## {icon.get(r['band'])} {r['name']}（{r['id']}·{TYPE_LABEL.get(r['type'], r['type'])}）· 分 {r['score']}")
        for s in r["suggestions"]:
            lines.append(f"- {s}")
        lines.append("")
    for n in report.get("notes", []):
        lines.append(f"- note: {n}")
    lines.append("")
    lines.append("说明：本表是**出图前**的物料漂移预案——high/medium 物料按建议提前补多视图/锁结构/锁颜色/上状态机，"
                 "比等审片 multimodal/场景 O2 事后报、再回头重出省返工。不阻断出图（落档闸门是 image_qc）。")
    return "\n".join(lines) + "\n"


def run(root: Path, ep: str) -> Dict[str, Any]:
    report = analyze(root, ep)
    out_dir = root / "生产数据"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"asset_drift_risk_{ep}.json"
    md_path = out_dir / f"asset_drift_risk_{ep}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    report["json_path"] = str(json_path)
    report["markdown_path"] = str(md_path)
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true", help="打印机器可读 report")
    ns = ap.parse_args(argv)
    report = run(Path(ns.root).expanduser().resolve(), ns.episode)
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    print(f"出图前物料漂移风险（{ns.episode}）：🔴 {report['high']} · 🟡 {report['medium']}")
    for r in report["assets"]:
        if r["band"] == "low":
            continue
        print(f"  {icon.get(r['band'])} {r['name']}（{r['id']}·{TYPE_LABEL.get(r['type'], r['type'])}）分 {r['score']}")
        for s in r["suggestions"]:
            print(f"     - {s}")
    for n in report["notes"]:
        print("ℹ️ " + n)
    print(f"→ {report['markdown_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
