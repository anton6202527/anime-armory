#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拍广告 出图前·打样矩阵 pilot_matrix（传统打样/PPM 纪律：先看小样再开机）。

为什么存在：
    传统广告制片在 PPM（制前会）后、正式开机前，先拍/先做**小样**给导演与客户过目——
    画风、产品质感、文字版式塌在小样里改是便宜的，整批出完再发现是重烧。
    ad 线现状是「出图 gate 通过 → 全批量出图」，没有任何"先出 2-5 镜代表样"的机制。
    本脚本是「代表样探针矩阵」（高光/风险探针先行）的广告线实现：
    从 storyboard 里挑 2–5 个**代表镜**，建议先出这几张给人看，确认画风/产品还原/
    品牌色/文字渲染/多主体关系后再放量。

五个必查轴（REQUIRED_COVERAGE）：
    hook          开场首镜——广告被看得最多的一帧，定整片基调
    product_hero  产品 hero/beauty 镜——产品是 ad 线最严格的“角色”（漂了整片报废）
    risk_max      本片风险最高镜——优先取 ad_reference_plan 的 delta_score 最大镜；
                  缺处方报告时回退为「涉及资产最多的镜」
    text_render   文字/片尾板/卖点板镜——文字渲染是 AI 生图公认弱项
    multi_entity  多主体同框镜（人物+产品等）——构图/比例关系/特征串染高发

诚实边界：
    - **全 advisory**：这是打样**计划**，不是门。`summary.block` 恒 0；打不打样由人定。
    - 某轴没有候选镜（如整片无文字镜）→ coverage 行如实标 `absent`，**绝不臆造**。
    - 本脚本只产计划，不生成任何图、不花任何钱。
    - 缺 storyboard → available=false + warn，不抛异常。

产物：`生产数据/ad_pilot_matrix.json` + `.md`（原子写）。
     findings 用 **`msg`**（对齐 ad-craft/scripts/gate.py 的 finding schema）。

用法（拍广告不拆集，粒度是镜头 shot）：
    python3 pilot_matrix.py <作品根> [--write] [--json] [--strict]

测试（从本目录跑）：
    cd skills/ad-image/scripts && python3 -m pytest test_pilot_matrix.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

# 同目录 sibling：镜头标签/产品镜识别/资产抽取全部复用，避免两套表漂移。
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import product_qc  # noqa: E402
import reference_planner  # noqa: E402

SCHEMA_VERSION = 1
KIND = "ad_pilot_matrix"
REPORT_REL = os.path.join("生产数据", "ad_pilot_matrix.json")
STORYBOARD_REL = os.path.join("脚本", "storyboard.json")
REFERENCE_PLAN_REL = os.path.join("生产数据", "ad_reference_plan.json")
PROVENANCE = "internal-heuristic·confidence=low"

# 打样规模：传统小样纪律——最少 2 镜（有对比才看得出画风稳定性），最多 5 镜（再多就不是小样了）。
MIN_PICKS = 2
MAX_PICKS = 5

# 五个必查轴（顺序即报告展示顺序）。
REQUIRED_COVERAGE: Tuple[str, ...] = ("hook", "product_hero", "risk_max", "text_render", "multi_entity")

# 每轴的人工复核重点（打样图给人看时该盯什么）。
REVIEW_FOCUS: Dict[str, List[str]] = {
    "hook": ["开场基调/画风是否成立", "主体清晰度（首帧被看得最多）", "构图是否抓眼"],
    "product_hero": ["品牌色 ΔE（对定妆照）", "logo 还原", "包装文字", "材质质感（光位/反射）"],
    "risk_max": ["大变化量下身份是否保持", "参考图还原度", "是否需要补定妆参考/升档"],
    "text_render": ["错别字/字形崩坏", "排版溢出/截断", "中英文混排"],
    "multi_entity": ["主体比例关系（人手 vs 产品尺寸）", "构图层次", "特征串染（产品特征跑到人身上等）"],
    "style_probe": ["与其它打样镜画风是否一致（跨镜稳定性对比样本）"],
}

# 产品 hero/beauty 语义（在产品镜里再挑「定妆展示位」）。
_HERO_RE = re.compile(r"产品特写|产品展示|beauty ?shot|hero ?shot|包装展示|定妆|主视觉|瓶身|特写", re.I)
# 文字面/板类镜（文字渲染弱项高发位）。
_TEXT_RE = re.compile(
    r"片尾|尾板|end ?card|endcard|卖点板|价格板|字卡|标题|slogan|口号|CTA|二维码|扫码|字幕板|文字|logo", re.I)

_SHOT_TEXT_KEYS = ("scene", "shot", "frame", "prompt", "desc", "description",
                   "product_lock", "subtitle", "vo", "section", "role", "purpose")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def finding(severity: str, code: str, msg: str, shot: Optional[str] = None) -> Dict[str, Any]:
    """ad gate 的 finding schema：`msg`（不是 message）——见 ad-craft/scripts/gate.py。"""
    out: Dict[str, Any] = {"severity": severity, "code": code, "msg": msg}
    if shot:
        out["shot"] = shot
    return out


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def _atomic_write(path: Path, text: str) -> None:
    """同盘 temp + os.replace：写一半被打断也不会留下半个报告。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def shot_text(shot: Mapping[str, Any]) -> str:
    """参与语义判定的镜头文本。纯函数·可测。"""
    parts: List[str] = []
    for key in _SHOT_TEXT_KEYS:
        value = shot.get(key)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, (list, tuple)):
            parts.extend(str(v) for v in value)
    return " ".join(p for p in parts if p)


def is_hero_shot(shot: Mapping[str, Any]) -> bool:
    """产品 hero/beauty 语义（在产品镜集合内再挑）。纯函数·可测。"""
    if shot.get("is_hero") or shot.get("hero_product"):
        return True
    return bool(_HERO_RE.search(shot_text(shot)))


def is_text_shot(shot: Mapping[str, Any]) -> bool:
    """文字/板类镜（endcard/卖点板/字卡…）。纯函数·可测。"""
    if shot.get("endcard") or shot.get("is_endcard"):
        return True
    return bool(_TEXT_RE.search(shot_text(shot)))


def plan_risk_by_label(reference_plan: Optional[Mapping[str, Any]]) -> Dict[str, float]:
    """ad_reference_plan → {镜头label: 该镜最大 delta_score}。缺报告返回空 dict。纯函数·可测。"""
    if not isinstance(reference_plan, Mapping):
        return {}
    out: Dict[str, float] = {}
    for row in reference_plan.get("shots") or []:
        if not isinstance(row, Mapping):
            continue
        label = str(row.get("shot") or "")
        scores = [float(p.get("delta_score") or 0.0)
                  for p in row.get("assets") or [] if isinstance(p, Mapping)]
        if label and scores:
            out[label] = max(scores)
    return out


# ── 各轴的指定镜（designate：每轴挑唯一最佳候选；同镜覆盖多轴 = 天然去重） ─────────

def designate_axes(shot_map: "Dict[str, Dict[str, Any]]",
                   product_labels: Sequence[str],
                   risk_by_label: Mapping[str, float]) -> Dict[str, Optional[Dict[str, Any]]]:
    """每轴 → {label, reason} 或 None（该轴无候选=absent，如实报）。纯函数·可测。

    去重靠「多轴指定同一镜」自然发生（picks 数 = 去重后的指定镜数 ≤ 5）。
    """
    labels = list(shot_map.keys())
    out: Dict[str, Optional[Dict[str, Any]]] = {}

    # hook：首镜（广告被看得最多的一帧）。
    out["hook"] = ({"label": labels[0],
                    "reason": "开场首镜：广告被看得最多的一帧，画风/基调在这里定生死"}
                   if labels else None)

    # product_hero：产品镜集合内优先 hero/beauty 语义，否则第一个产品镜。
    hero = next((lb for lb in product_labels if lb in shot_map and is_hero_shot(shot_map[lb])), None)
    fallback = next((lb for lb in product_labels if lb in shot_map), None)
    pick = hero or fallback
    out["product_hero"] = ({"label": pick,
                            "reason": ("产品 hero/beauty 镜" if hero else "产品镜（无显式 hero 语义，取首个产品镜）")
                                      + "：产品是 ad 线最严格的“角色”，品牌色/logo/包装文字先在小样里验"}
                           if pick else None)

    # risk_max：优先 ad_reference_plan 的 delta_score 最大镜；回退为资产最多的镜。
    valid_risk = {lb: sc for lb, sc in risk_by_label.items() if lb in shot_map}
    if valid_risk:
        top = max(valid_risk, key=lambda lb: (valid_risk[lb], -labels.index(lb)))
        out["risk_max"] = {"label": top,
                           "reason": f"参考处方判定的最高风险镜（delta_score={valid_risk[top]}）：变化量最大，最易漂"}
    else:
        by_entities = [(len(reference_planner.shot_asset_ids(shot_map[lb])), lb) for lb in labels]
        by_entities = [(n, lb) for n, lb in by_entities if n > 0]
        if by_entities:
            n, top = max(by_entities, key=lambda t: (t[0], -labels.index(t[1])))
            out["risk_max"] = {"label": top,
                               "reason": f"缺 ad_reference_plan，回退为涉及资产最多的镜（{n} 个资产）"}
        else:
            out["risk_max"] = None

    # text_render：第一个文字/板类镜。
    text_label = next((lb for lb in labels if is_text_shot(shot_map[lb])), None)
    out["text_render"] = ({"label": text_label,
                           "reason": "文字/板类镜：文字渲染是 AI 生图公认弱项，错字/崩形先在小样里抓"}
                          if text_label else None)

    # multi_entity：结构化资产 ≥2 的镜里取最多者。
    multi = [(len(reference_planner.shot_asset_ids(shot_map[lb])), lb) for lb in labels]
    multi = [(n, lb) for n, lb in multi if n >= 2]
    if multi:
        n, lb = max(multi, key=lambda t: (t[0], -labels.index(t[1])))
        out["multi_entity"] = {"label": lb,
                               "reason": f"多主体同框镜（{n} 个资产）：比例关系/特征串染高发位"}
    else:
        out["multi_entity"] = None
    return out


def build(root: Path) -> Dict[str, Any]:
    """打样矩阵计划。缺料只降级不抛异常；summary.block 恒 0（advisory·这是计划不是门）。"""
    root = Path(root).resolve()
    storyboard = load_json(root / STORYBOARD_REL)
    registry, registry_rel = reference_planner.resolve_registry(root)
    reference_plan = load_json(root / REFERENCE_PLAN_REL)

    findings: List[Dict[str, Any]] = []
    available = isinstance(storyboard, Mapping)
    shot_map: Dict[str, Dict[str, Any]] = {}
    product_labels: List[str] = []

    if not available:
        findings.append(finding(
            "warn", "storyboard_missing",
            f"缺 {STORYBOARD_REL}——没有分镜可挑打样镜（insufficient_data，不代表不用打样）。"
            "先跑 ad-script 分镜 pass 再规划打样。"))
    else:
        shot_map = product_qc.storyboard_shot_by_label(storyboard)
        product_labels = product_qc.product_shots(storyboard)
        if not shot_map:
            available = False
            findings.append(finding("warn", "storyboard_empty",
                                    "storyboard.json 存在但没有 shots——分镜还没落档，无镜可打样。"))

    if available and not isinstance(reference_plan, Mapping):
        findings.append(finding(
            "info", "reference_plan_missing",
            "缺 生产数据/ad_reference_plan.json：risk_max 轴回退为「资产最多的镜」；"
            "建议先跑 reference_planner.py，风险排序会更准。"))

    designations = (designate_axes(shot_map, product_labels, plan_risk_by_label(reference_plan))
                    if available else {axis: None for axis in REQUIRED_COVERAGE})

    # 指定镜去重 → picks（一镜可覆盖多轴；轴顺序稳定，故输出确定性）。
    picks: List[Dict[str, Any]] = []
    by_label: Dict[str, Dict[str, Any]] = {}
    for axis in REQUIRED_COVERAGE:
        row = designations.get(axis)
        if not row:
            continue
        label = row["label"]
        if label not in by_label:
            pick = {"shot": label, "axes": [], "reasons": [], "review_focus": []}
            by_label[label] = pick
            picks.append(pick)
        by_label[label]["axes"].append(axis)
        by_label[label]["reasons"].append(row["reason"])
        for item in REVIEW_FOCUS.get(axis, []):
            if item not in by_label[label]["review_focus"]:
                by_label[label]["review_focus"].append(item)

    # 小样下限：只有 1 个指定镜且片子不止 1 镜时，补 1 个「画风对比样本」——
    # 单张小样看不出跨镜稳定性（不虚构轴覆盖，axes 标 style_probe）。
    labels = list(shot_map.keys())
    if available and len(picks) == 1 and len(labels) >= MIN_PICKS:
        extra = next((lb for lb in labels if lb not in by_label), None)
        if extra:
            picks.append({"shot": extra, "axes": ["style_probe"],
                          "reasons": ["补充画风对比样本：单张小样看不出跨镜稳定性"],
                          "review_focus": list(REVIEW_FOCUS["style_probe"])})

    coverage = []
    for axis in REQUIRED_COVERAGE:
        row = designations.get(axis)
        coverage.append({"axis": axis,
                         "status": "covered" if row else "absent",
                         "shot": row["label"] if row else None})
    absent = [c["axis"] for c in coverage if c["status"] == "absent"]
    if available and absent:
        findings.append(finding(
            "info", "coverage_axis_absent",
            f"本片没有可覆盖以下打样轴的候选镜：{'、'.join(absent)}——如实标 absent，不臆造"
            "（如整片无文字镜/无多主体镜属正常创意选择）。"))

    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "available": available,
        "project_root": str(root),
        "generated_at": now_iso(),
        "inputs": {
            "storyboard": {"path": STORYBOARD_REL, "available": available},
            "asset_registry": {"path": registry_rel or "设定库/asset_registry.json",
                               "available": bool(registry)},
            "reference_plan": {"path": REFERENCE_PLAN_REL,
                               "available": isinstance(reference_plan, Mapping)},
        },
        "thresholds": {
            "min_picks": MIN_PICKS, "max_picks": MAX_PICKS,
            "required_coverage": list(REQUIRED_COVERAGE),
            "provenance": PROVENANCE,
            "note": "advisory：打样**计划**，不是门——block 恒 0，打不打样由人定；"
                    "轴无候选镜如实标 absent，绝不臆造。本脚本不生成图、不花钱。",
        },
        "coverage": coverage,
        "picks": picks,
        "summary": {
            "block": 0,  # advisory：恒 0——这是计划，不是「这次刚好没有」
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
            "info": sum(1 for f in findings if f["severity"] == "info"),
            "picks": len(picks),
            "axes_covered": len(REQUIRED_COVERAGE) - len(absent) if available else 0,
            "axes_absent": absent,
        },
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = ["# 出图前·打样矩阵（ad_pilot_matrix）", ""]
    if not report.get("available"):
        lines += ["- ⚠️ 缺 `脚本/storyboard.json`（available=false·降级为建议，不阻断）", ""]
    else:
        lines += [f"- 建议先出 {s.get('picks')} 镜小样（轴覆盖 {s.get('axes_covered')}/{len(REQUIRED_COVERAGE)}"
                  + (f"·absent：{'、'.join(s.get('axes_absent') or [])}" if s.get("axes_absent") else "")
                  + "）",
                  "- advisory：打样计划不是门（block 恒 0），打不打样由人定；本脚本不生成图、不花钱", ""]
    icon = {"block": "⛔", "warn": "⚠️", "info": "ℹ️"}
    for f in report.get("findings") or []:
        lines.append(f"- {icon.get(f['severity'], '·')} `{f['code']}` {f['msg']}")
    if report.get("picks"):
        lines += ["", "## 打样镜", ""]
        for pick in report["picks"]:
            lines.append(f"### {pick['shot']}（轴：{'、'.join(pick['axes'])}）")
            for reason in pick["reasons"]:
                lines.append(f"- {reason}")
            lines.append("- 复核重点：" + "；".join(pick["review_focus"]))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_report(root: Path, report: Mapping[str, Any]) -> Dict[str, str]:
    json_path = Path(root) / REPORT_REL
    md_path = json_path.with_suffix(".md")
    _atomic_write(json_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    _atomic_write(md_path, render_markdown(report))
    return {"json": str(json_path), "md": str(md_path)}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", help="作品根（拍广告不拆集，粒度是镜头 shot）")
    ap.add_argument("--write", action="store_true", help=f"落盘 {REPORT_REL}（+ 同名 .md·原子写）")
    ap.add_argument("--json", action="store_true", help="stdout 打 JSON 而非 markdown")
    ap.add_argument("--strict", action="store_true",
                    help="available=false 时 exit 1（本检 advisory·恒无 block）")
    ns = ap.parse_args(argv)
    report = build(Path(ns.root))
    if ns.write:
        write_report(Path(ns.root), report)
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    return 1 if (ns.strict and not report["available"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
