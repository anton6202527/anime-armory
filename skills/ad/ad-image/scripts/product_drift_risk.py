#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广告**产品漂移风险账本**（事前打分排序·advisory）。

ad 线一致性件的现状：reference_planner 管"每镜该喂哪些参考"（**处方**），product_qc 管
"出完图漂没漂"（**事后**）——中间还缺一层：**出图前把逐镜漂移风险打分排序，
高危镜先打样、先加锚，钱花在刀刃上**。产品是广告线最严格的"角色"（观众对包装/logo/
配色的记忆精度远高于对人脸），本账本把三份既有产物融合成风险序：

  分数来源（词面/字段级·不读画面）：
  · ad_reference_plan 的 delta_score（该镜资产变化量，处方侧已算好——直接复用不重算）
  · storyboard 词面风险信号：产品特写/微距(+14)、包装文字/文字渲染(+12)、多主体同框(+10)、
    透明/反光材质 玻璃瓶金属高光(+10)、极端角度 俯拍仰拍鱼眼(+8)、新场景首现(+6)
  · 参考缺口：该镜产品资产在 registry 无登记参考 → +18（无锚出图=开盲盒）
  · **实测回灌**：product_qc 已对某镜报 warn/block → 该镜直接 high（不臆造，只回灌实测）

  输出：逐镜 risk 降序 + high 名单；若 ad_pilot_matrix 已存在而 high 镜不在打样集 →
  warn `high_risk_unpiloted`（高危镜没进打样就全量出图=最贵的翻车路径）。

**审不是门**：风险分是启发式排序不是判决，`summary.block` 恒 0；gate image 阶段以
advisory 侧车并入。与 reference_planner 的分工：它开处方（喂什么），本账本排优先级
（先验证谁）；与 pilot_matrix 的分工：它选代表样（每轴一镜），本账本给它风险依据。

用法：
    python3 product_drift_risk.py <作品根> [--write] [--json] [--strict]
阈值 env：AD_DRIFT_HIGH=40（≥此分为 high）
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set

VERSION = 1
KIND = "ad_product_drift_risk"
REPORT_REL = os.path.join("生产数据", "ad_product_drift_risk.json")
STORYBOARD_REL = os.path.join("脚本", "storyboard.json")
REFERENCE_PLAN_REL = os.path.join("生产数据", "ad_reference_plan.json")
PILOT_REL = os.path.join("生产数据", "ad_pilot_matrix.json")
PRODUCT_QC_REL = os.path.join("出图", "分镜", "product_qc.json")
REGISTRY_RELS = (os.path.join("设定库", "asset_registry.json"),
                 os.path.join("出图", "共享", "asset_registry.json"))

HIGH_THRESHOLD = int(os.environ.get("AD_DRIFT_HIGH", "40"))
PROVENANCE = "internal-heuristic·confidence=low"

_CLOSEUP_RE = re.compile(r"特写|微距|大特写|close.?up|macro|极近", re.IGNORECASE)
_TEXT_RE = re.compile(r"包装文字|文字渲染|字样|标签文字|瓶身字|logo\s*文字|说明文字|字卡", re.IGNORECASE)
_MATERIAL_RE = re.compile(r"玻璃|透明|反光|高光|金属|镜面|液体|水珠|光泽")
_ANGLE_RE = re.compile(r"俯拍|仰拍|鱼眼|顶视|底视|极端角度|荷兰角", re.IGNORECASE)
_HUMAN_RE = re.compile(r"人物|模特|手部|手持|代言|演员|女生|男生|用户|她|他")
_EXEMPT_RE = re.compile(r"片尾|尾板|end.?card|endcard|logo板|二维码", re.IGNORECASE)

_SIGNAL_WEIGHTS = (
    ("closeup", _CLOSEUP_RE, 14, "产品特写/微距（细节还原压力最大）"),
    ("text_render", _TEXT_RE, 12, "包装/标签文字渲染（生成器文字是重灾区）"),
    ("material", _MATERIAL_RE, 10, "透明/反光材质（玻璃瓶金属高光最易变形）"),
    ("angle", _ANGLE_RE, 8, "极端角度（训练分布外视角易漂）"),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def finding(severity: str, code: str, msg: str, shots: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"severity": severity, "code": code, "msg": msg}
    if shots:
        out["shots"] = list(shots)
    return out


def load_json_file(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def iter_shots(storyboard: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows = storyboard.get("shots") or storyboard.get("clips") or storyboard.get("镜头") or []
    return [r for r in rows if isinstance(r, dict)]


def shot_label(shot: Mapping[str, Any], idx: int) -> str:
    return str(shot.get("shot_id") or shot.get("clip_id") or shot.get("id") or f"镜头{idx + 1:02d}")


def shot_blob(shot: Mapping[str, Any]) -> str:
    parts = []
    for key in ("shot", "frame", "画面", "prompt", "description", "desc", "shot_type", "scene", "场景"):
        val = shot.get(key)
        if val:
            parts.append(str(val))
    for key in ("assets", "entities", "资产"):
        val = shot.get(key)
        if isinstance(val, (list, tuple)):
            parts.extend(str(x) for x in val if x)
    return " ".join(parts)


def plan_scores(reference_plan: Optional[Mapping[str, Any]]) -> Dict[str, float]:
    """ad_reference_plan → {镜 label: max delta_score}（与 pilot_matrix 同口径读法）。纯函数·可测。"""
    out: Dict[str, float] = {}
    if not isinstance(reference_plan, Mapping):
        return out
    for row in reference_plan.get("shots") or []:
        if not isinstance(row, Mapping):
            continue
        label = str(row.get("shot") or "")
        scores = [float(p.get("delta_score") or 0.0) for p in (row.get("plans") or [])
                  if isinstance(p, Mapping)]
        if label and scores:
            out[label] = max(scores)
    return out


def plan_reference_gaps(reference_plan: Optional[Mapping[str, Any]]) -> Set[str]:
    """处方里"资产未登记参考"的镜集合（registered=false 任一资产即算）。纯函数·可测。"""
    gaps: Set[str] = set()
    if not isinstance(reference_plan, Mapping):
        return gaps
    for row in reference_plan.get("shots") or []:
        if not isinstance(row, Mapping):
            continue
        label = str(row.get("shot") or "")
        for plan in row.get("plans") or []:
            if isinstance(plan, Mapping) and plan.get("registered") is False:
                gaps.add(label)
    return gaps


def qc_flagged_shots(product_qc: Optional[Mapping[str, Any]]) -> Set[str]:
    """product_qc 已报 warn/block 的镜（词面抽取镜头NN/shot 键）——实测回灌源。纯函数·可测。"""
    flagged: Set[str] = set()
    if not isinstance(product_qc, Mapping):
        return flagged
    for entry in product_qc.get("findings") or []:
        if not isinstance(entry, Mapping) or entry.get("severity") not in ("block", "warn"):
            continue
        for key in ("shot", "shot_id", "image", "file", "asset", "subject"):
            val = entry.get(key)
            if val:
                flagged.add(str(val))
        blob = str(entry.get("msg") or entry.get("message") or "")
        flagged.update(m.group(0) for m in re.finditer(r"镜头\s*\d+|C\d{2}\b", blob))
    return {re.sub(r"\s+", "", s) for s in flagged}


def score_shot(shot: Mapping[str, Any], label: str, *, delta: float, ref_gap: bool,
               seen_scenes: Set[str]) -> Optional[Dict[str, Any]]:
    """单镜风险行 {label, score, signals:[...]}；endcard/非产品镜返回 None。纯函数·可测。"""
    blob = shot_blob(shot)
    if not blob or _EXEMPT_RE.search(blob):
        return None
    signals: List[str] = []
    score = 0.0
    for name, pattern, weight, desc in _SIGNAL_WEIGHTS:
        if pattern.search(blob):
            score += weight
            signals.append(f"{name}(+{weight}·{desc.split('（')[0]})")
    if _HUMAN_RE.search(blob) and re.search(r"产品|包装|瓶|盒|app|界面|ui", blob, re.IGNORECASE):
        score += 10
        signals.append("multi_entity(+10·人物+产品同框互相拉扯)")
    scene = str(shot.get("scene") or shot.get("场景") or "").strip()
    if scene and scene not in seen_scenes:
        score += 6
        signals.append("new_scene(+6·场景首现)")
        seen_scenes.add(scene)
    if delta:
        pts = min(20.0, delta * 10)
        score += pts
        signals.append(f"delta_score(+{pts:g}·处方变化量 {delta:g})")
    if ref_gap:
        score += 18
        signals.append("reference_gap(+18·资产未登记参考=无锚出图)")
    if not signals:
        return None
    return {"label": label, "score": round(score, 1), "signals": signals}


def build(root: Path) -> Dict[str, Any]:
    root = Path(root)
    storyboard = load_json_file(root / STORYBOARD_REL)
    findings: List[Dict[str, Any]] = []
    available = isinstance(storyboard, dict)
    rows: List[Dict[str, Any]] = []
    if not available:
        findings.append(finding("warn", "storyboard_missing",
                                "缺 脚本/storyboard.json——没有分镜可算漂移风险（insufficient_data）。"))
    else:
        deltas = plan_scores(load_json_file(root / REFERENCE_PLAN_REL))
        gaps = plan_reference_gaps(load_json_file(root / REFERENCE_PLAN_REL))
        flagged = qc_flagged_shots(load_json_file(root / PRODUCT_QC_REL))
        seen_scenes: Set[str] = set()
        for idx, shot in enumerate(iter_shots(storyboard)):
            label = shot_label(shot, idx)
            row = score_shot(shot, label, delta=deltas.get(label, 0.0),
                            ref_gap=label in gaps, seen_scenes=seen_scenes)
            if row is None:
                continue
            norm = re.sub(r"\s+", "", label)
            if norm in flagged or any(norm in f or f in norm for f in flagged):
                row["score"] = max(row["score"], float(HIGH_THRESHOLD))
                row["signals"].append("measured(+实测回灌·product_qc 已报此镜 warn/block)")
            row["tier"] = "high" if row["score"] >= HIGH_THRESHOLD else "normal"
            rows.append(row)
        rows.sort(key=lambda r: -r["score"])
        high = [r for r in rows if r["tier"] == "high"]
        if high:
            findings.append(finding("info", "high_risk_shots",
                                    f"{len(high)} 镜为高漂移风险（≥{HIGH_THRESHOLD} 分）——建议先打样/加锚再全量："
                                    + "、".join(f"{r['label']}({r['score']:g})" for r in high[:5]),
                                    [r["label"] for r in high]))
            pilot = load_json_file(root / PILOT_REL)
            if isinstance(pilot, Mapping):
                picked = {str((v or {}).get("label") or "") for v in (pilot.get("coverage") or {}).values()
                          if isinstance(v, Mapping)}
                missing = [r["label"] for r in high if r["label"] not in picked]
                if missing:
                    findings.append(finding(
                        "warn", "high_risk_unpiloted",
                        f"高危镜 {'、'.join(missing[:4])} 不在打样矩阵里——高危镜没进打样就全量出图"
                        "是最贵的翻车路径；重跑 pilot_matrix 或人工把这些镜加进打样集", missing))
        elif rows:
            findings.append(finding("info", "risk_ranked",
                                    f"{len(rows)} 镜已按风险排序，无 high 档（阈 {HIGH_THRESHOLD}）"))
        else:
            findings.append(finding("info", "no_product_signals",
                                    "分镜里没有可判的产品风险信号（词面初筛；不代表零风险）"))
    return {
        "schema_version": VERSION, "kind": KIND, "available": available,
        "project_root": str(root), "generated_at": now_iso(),
        "thresholds": {"high": HIGH_THRESHOLD, "provenance": PROVENANCE,
                       "note": "advisory：风险分是排序启发式不是判决，summary.block 恒 0；"
                               "实测回灌只认 product_qc 已报镜，不臆造"},
        "shots": rows,
        "summary": {"block": 0,
                    "warn": sum(1 for f in findings if f["severity"] == "warn"),
                    "info": sum(1 for f in findings if f["severity"] == "info"),
                    "high": sum(1 for r in rows if r.get("tier") == "high")},
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = ["# 广告产品漂移风险账本（事前）", "",
             f"- high {s.get('high')} 镜 · warn {s.get('warn')} · info {s.get('info')}"
             "（advisory·不产 block）", ""]
    for r in (report.get("shots") or [])[:12]:
        lines.append(f"- {'🔴' if r.get('tier') == 'high' else '·'} {r['label']}：{r['score']:g} 分"
                     f"（{'；'.join(r['signals'])}）")
    lines.append("")
    icon = {"warn": "⚠️", "info": "ℹ️"}
    for f in report.get("findings") or []:
        lines.append(f"- {icon.get(f['severity'], '·')} `{f['code']}` {f['msg']}")
    return "\n".join(lines) + "\n"


def write_report(root: Path, report: Mapping[str, Any]) -> None:
    path = root / REPORT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    for target, payload in ((path, json.dumps(report, ensure_ascii=False, indent=2) + "\n"),
                            (path.with_suffix(".md"), render_markdown(report))):
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, target)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("--write", action="store_true", help=f"落盘 {REPORT_REL}（+ .md·原子写）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="warn>0 时 exit 1")
    ns = ap.parse_args(argv)
    report = build(Path(ns.root))
    if ns.write:
        write_report(Path(ns.root), report)
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    return 1 if (ns.strict and report["summary"]["warn"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
