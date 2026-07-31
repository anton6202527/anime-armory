#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广告**生成次数预算**账本（事前·advisory）。

为什么：stop_loss 管的是**事后**止损（重抽率/credit 已花超线），管不了**结构性浪费**——
分镜定稿那一刻，这条片要花多少次付费生成（首帧+尾帧+图生视频逐镜）就已经定了。
生产中的典型教训（take 爆炸：8 clip 被拆成 24 次付费 take）在广告线的对应病：连续同场景
产品镜/同人物镜逐镜独立生成，而 2026 视频后端（Seedance 2.0 多镜、Kling multishot）
本可一次带过。本账本在**出图前**把账算明白：

  · 逐镜生成预算：首帧 1 次 + 尾帧（continuity.need_end_frame 时）1 次 + 图生视频 1 次
  · 合并候选：**相邻**镜同场景（scene 相同非空）且合并时长 ≤ 上限 → 候选合并链
    （一次多镜生成或一镜到底后剪开），省 len(链)-1 次视频生成
  · 预算线：设 AD_BUDGET_MAX_GENERATIONS 时超线 warn

安全边界：endcard/产品 beauty 等有意独立镜
不进合并链；合并只是**候选**——高动作/需要独立运镜的镜由人剔除（词面判不动作强度，
不臆造）。**审不是门**：`summary.block` 恒 0；gate image 阶段 advisory 侧车并入。

用法：
    python3 generation_budget.py <作品根> [--write] [--json] [--strict]
阈值 env：AD_BUDGET_MERGE_CEILING_SECONDS=10  AD_BUDGET_MAX_GENERATIONS
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

VERSION = 1
KIND = "ad_generation_budget"
REPORT_REL = os.path.join("生产数据", "ad_generation_budget.json")
STORYBOARD_REL = os.path.join("脚本", "storyboard.json")
DURATIONS_REL = os.path.join("脚本", "镜头时长.json")

MERGE_CEILING = float(os.environ.get("AD_BUDGET_MERGE_CEILING_SECONDS", "10"))
ENV_MAX_GEN = os.environ.get("AD_BUDGET_MAX_GENERATIONS", "")
PROVENANCE = "internal-heuristic·confidence=low"

_EXEMPT_RE = re.compile(
    r"片尾|尾板|end.?card|endcard|logo|产品特写|产品beauty|beauty.?shot|hero.?shot|价格板|二维码",
    re.IGNORECASE)


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


def shot_duration(shot: Mapping[str, Any], durations: Mapping[str, Any], label: str) -> float:
    for source in (shot.get("duration"), shot.get("时长"), durations.get(label)):
        try:
            val = float(source)  # type: ignore[arg-type]
            if val > 0:
                return val
        except (TypeError, ValueError):
            continue
    return 0.0


def needs_end_frame(shot: Mapping[str, Any]) -> bool:
    cont = shot.get("continuity")
    if isinstance(cont, Mapping) and cont.get("need_end_frame"):
        return True
    return bool(shot.get("need_end_frame"))


def is_exempt(shot: Mapping[str, Any]) -> bool:
    blob = " ".join(str(shot.get(k) or "") for k in
                    ("shot_type", "scene", "场景", "shot", "frame", "画面", "role", "purpose"))
    if shot.get("endcard") or shot.get("is_endcard") or shot.get("is_hero") or shot.get("hero_product"):
        return True
    return bool(_EXEMPT_RE.search(blob))


def merge_chains(rows: Sequence[Mapping[str, Any]], ceiling: float = MERGE_CEILING) -> List[List[str]]:
    """相邻同场景（scene 非空相同）且累计时长 ≤ceiling 的合并候选链（≥2 镜）。纯函数·可测。

    豁免镜断链；时长缺失（0）视为不可判断链（宁缺毋滥）。"""
    chains: List[List[str]] = []
    cur: List[str] = []
    cur_scene = ""
    cur_dur = 0.0
    for row in rows:
        scene = str(row.get("scene") or "").strip()
        dur = float(row.get("duration") or 0.0)
        ok = scene and dur > 0 and not row.get("exempt")
        if ok and scene == cur_scene and cur_dur + dur <= ceiling:
            cur.append(str(row.get("label")))
            cur_dur += dur
        else:
            if len(cur) >= 2:
                chains.append(cur)
            cur = [str(row.get("label"))] if ok else []
            cur_scene = scene if ok else ""
            cur_dur = dur if ok else 0.0
    if len(cur) >= 2:
        chains.append(cur)
    return chains


def build(root: Path) -> Dict[str, Any]:
    root = Path(root)
    storyboard = load_json_file(root / STORYBOARD_REL)
    durations = load_json_file(root / DURATIONS_REL) or {}
    if isinstance(durations.get("durations"), Mapping):
        durations = durations["durations"]
    findings: List[Dict[str, Any]] = []
    available = isinstance(storyboard, dict)
    rows: List[Dict[str, Any]] = []
    if not available:
        findings.append(finding("warn", "storyboard_missing",
                                "缺 脚本/storyboard.json——没有分镜可算生成预算（insufficient_data）。"))
        chains = []
        totals = {"image": 0, "video": 0, "total": 0}
    else:
        for idx, shot in enumerate(iter_shots(storyboard)):
            label = shot_label(shot, idx)
            dur = shot_duration(shot, durations, label)
            images = 1 + (1 if needs_end_frame(shot) else 0)
            rows.append({"label": label, "scene": str(shot.get("scene") or shot.get("场景") or "").strip(),
                         "duration": dur, "images": images, "videos": 1, "exempt": is_exempt(shot)})
        totals = {"image": sum(r["images"] for r in rows),
                  "video": sum(r["videos"] for r in rows)}
        totals["total"] = totals["image"] + totals["video"]
        chains = merge_chains(rows)
        savable = sum(len(c) - 1 for c in chains)
        if rows:
            findings.append(finding("info", "generation_budget_summary",
                                    f"{len(rows)} 镜计划共 {totals['total']} 次付费生成"
                                    f"（图 {totals['image']} + 视频 {totals['video']}）"))
        if chains:
            desc = "；".join("+".join(c) for c in chains[:4])
            findings.append(finding(
                "info", "merge_candidates_available",
                f"{len(chains)} 条相邻同场景合并候选链（{desc}），合并可省约 {savable} 次视频生成"
                f"（一次多镜生成/一镜到底后剪开，链内累计 ≤{MERGE_CEILING:g}s）——高动作/需独立运镜"
                f"的镜请人工剔除；这是候选不是决定（{PROVENANCE}）",
                [s for c in chains for s in c]))
        max_gen = None
        if ENV_MAX_GEN:
            try:
                max_gen = int(ENV_MAX_GEN)
            except ValueError:
                max_gen = None
        if max_gen is not None and totals["total"] > max_gen:
            findings.append(finding("warn", "budget_over_line",
                                    f"计划生成 {totals['total']} 次已超预算线 {max_gen}——先采纳合并候选"
                                    "或砍镜，别开工后靠 stop_loss 事后止血"))
    return {
        "schema_version": VERSION, "kind": KIND, "available": available,
        "project_root": str(root), "generated_at": now_iso(),
        "thresholds": {"merge_ceiling_seconds": MERGE_CEILING,
                       "max_generations": ENV_MAX_GEN or None, "provenance": PROVENANCE,
                       "note": "advisory：合并是候选不是决定，summary.block 恒 0；"
                               "与 stop_loss 分工：这管事前结构性预算，那管事后止损"},
        "shots": rows,
        "merge_chains": chains,
        "totals": totals,
        "summary": {"block": 0,
                    "warn": sum(1 for f in findings if f["severity"] == "warn"),
                    "info": sum(1 for f in findings if f["severity"] == "info")},
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    t = report.get("totals") or {}
    lines = ["# 广告生成次数预算（事前）", "",
             f"- 计划生成：图 {t.get('image')} + 视频 {t.get('video')} = {t.get('total')} 次"
             "（advisory·不产 block）", ""]
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
