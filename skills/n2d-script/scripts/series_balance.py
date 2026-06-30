#!/usr/bin/env python3
"""series_balance.py — 剧级质量/资源均衡视图（对冲「虎头蛇尾」）。

为什么存在：逐集 gate（beat_audit/boundary/source）都只看**单集**好不好，没人看**全剧曲线**。
2026 漫剧头号死因就是「虎头蛇尾」——前几集把钩子/反转/爽点全堆完，中后段叙事密度雪崩，观众弃
追、96% 项目被拖欠尾款。那是后期投流挤占制作预算的结果，但**苗头在拆集就能看见**：后 1/3 集的
钩子密度/反转率/镜数相比前 1/3 显著下滑 = 资源/叙事被前置。本脚本把各集 beat_audit 信号摊成一条
曲线，量前 1/3 vs 后 1/3 的落差，提前报警。

复用 beat_audit.audit_episode 的统计（钩子/爽点/反转/镜数），纯读 voiceover；report-only，
--strict 时严重前置（后段密度 < 前段一半）exit 1。

用法：
  python3 series_balance.py <作品根> [--strict] [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import beat_audit as ba  # noqa: E402


def ep_num(ep: str) -> Optional[int]:
    m = re.search(r"\d+", str(ep or ""))
    return int(m.group()) if m else None


def discover_episodes(root: str) -> List[str]:
    eps = [os.path.basename(os.path.dirname(p))
           for p in glob.glob(os.path.join(root, "脚本", "第*集", "voiceover.txt"))]
    return sorted(eps, key=lambda e: ep_num(e) or 0)


def episode_metrics(root: str, ep: str) -> Dict[str, Any]:
    _findings, stats = ba.audit_episode(root, ep)
    shots = int(stats.get("shots") or 0)
    hooks = int(stats.get("hooks") or 0)
    payoffs = int(stats.get("payoffs") or 0)
    return {
        "episode": ep, "shots": shots, "hooks": hooks, "payoffs": payoffs,
        "reversal": 1 if stats.get("has_reversal") else 0,
        "hook_density": round(hooks / shots, 3) if shots else 0.0,
    }


def _avg(rows: Sequence[Dict[str, Any]], key: str) -> float:
    return round(sum(r[key] for r in rows) / len(rows), 3) if rows else 0.0


def thirds(rows: Sequence[Dict[str, Any]]) -> Tuple[List, List, List]:
    """把按集序排好的指标切成前/中/后三段（尽量均分）。"""
    n = len(rows)
    k = n // 3
    if k == 0:
        return list(rows), [], []
    return list(rows[:k]), list(rows[k:n - k]), list(rows[n - k:])


def analyze(root: str) -> Dict[str, Any]:
    eps = discover_episodes(root)
    rows = [episode_metrics(root, ep) for ep in eps]
    findings: List[Dict[str, Any]] = []
    front, mid, back = thirds(rows)
    summary: Dict[str, Any] = {
        "episodes": len(rows),
        "front": {"eps": [r["episode"] for r in front], "avg_hooks": _avg(front, "hooks"),
                  "avg_shots": _avg(front, "shots"), "reversal_rate": _avg(front, "reversal")},
        "back": {"eps": [r["episode"] for r in back], "avg_hooks": _avg(back, "hooks"),
                 "avg_shots": _avg(back, "shots"), "reversal_rate": _avg(back, "reversal")},
    }
    if len(rows) < 6 or not front or not back:
        findings.append({"severity": "info", "code": "too_few_episodes",
                         "message": f"留存集 {len(rows)} 部（<6），曲线样本不足，仅记录指标不判趋势。"})
        return {"rows": rows, "summary": summary, "findings": findings}

    fh, bh = summary["front"]["avg_hooks"], summary["back"]["avg_hooks"]
    fs, bs = summary["front"]["avg_shots"], summary["back"]["avg_shots"]
    fr, br = summary["front"]["reversal_rate"], summary["back"]["reversal_rate"]

    if fh > 0 and bh < 0.5 * fh:
        findings.append({"severity": "warn", "code": "back_loaded_decline_severe",
                         "message": f"虎头蛇尾（重度）：后 1/3 集均钩子 {bh} < 前 1/3 的一半（{fh}）——"
                                    "钩子/爽点严重前置，后段留不住人。把后段补钩或重新分配高能桥段。",
                         "front_avg_hooks": fh, "back_avg_hooks": bh})
    elif fh > 0 and bh < 0.7 * fh:
        findings.append({"severity": "warn", "code": "back_loaded_decline",
                         "message": f"叙事密度后段下滑：后 1/3 集均钩子 {bh} 仅为前 1/3（{fh}）的 {bh/fh:.0%}——"
                                    "确认不是把好桥段都堆在开头。",
                         "front_avg_hooks": fh, "back_avg_hooks": bh})
    if fr > 0 and br == 0:
        findings.append({"severity": "warn", "code": "reversal_drought_late",
                         "message": f"后 1/3 集反转率为 0（前段 {fr:.0%}）——后段无反转，爽感断崖，补反转桥段。"})
    if fs > 0 and bs < 0.6 * fs:
        findings.append({"severity": "info", "code": "shot_count_decline",
                         "message": f"后 1/3 集均镜数 {bs} 明显少于前 1/3（{fs}）——可能后段制作资源被压缩，留意成片质量曲线。"})
    if not findings:
        findings.append({"severity": "info", "code": "balanced",
                         "message": f"全剧密度均衡：前/后 1/3 均钩子 {fh}/{bh}、反转率 {fr:.0%}/{br:.0%}。"})
    return {"rows": rows, "summary": summary, "findings": findings}


def print_human(res: Dict[str, Any]) -> None:
    s = res["summary"]
    print(f"# 剧级质量/资源均衡 — {s['episodes']} 集")
    print(f"前 1/3：均钩子 {s['front']['avg_hooks']}　均镜数 {s['front']['avg_shots']}　反转率 {s['front']['reversal_rate']:.0%}")
    print(f"后 1/3：均钩子 {s['back']['avg_hooks']}　均镜数 {s['back']['avg_shots']}　反转率 {s['back']['reversal_rate']:.0%}")
    icon = {"warn": "WARN", "info": "INFO"}
    for f in res["findings"]:
        print(f"- {icon.get(f['severity'], 'INFO')} [{f['code']}] {f['message']}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d 剧级质量/资源均衡视图（对冲虎头蛇尾）")
    ap.add_argument("root")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"))
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print_human(res)
    severe = any(f["code"] == "back_loaded_decline_severe" for f in res["findings"])
    return 1 if (ns.strict and severe) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
