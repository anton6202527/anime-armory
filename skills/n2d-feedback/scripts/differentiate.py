#!/usr/bin/env python3
"""differentiate.py — 反同质化 风格/题材差异化引擎。

从 n2d-feedback 写的「自有题材战绩库」(genre_performance_record) 这朵点云 +（可选）novel-score
公榜基线，反推"未被做烂的组合"：哪些 `题材 × 开场 × 结尾节奏` 组合我们占用少（白空间）、
又能复用已被验证有效的特征轴、且避开公榜最饱和的题材 → 排序出差异化选题候选。

连接只在产物层：读战绩库（n2d-feedback 写）+ 可选公榜基线（novel-score 写），输出
`差异化候选.json/md` 供选题（novel-create/novel-title/novel-score）消费，**不互相 import**。

诚实纪律（同 n2d-feedback）：样本稀疏时占用度处处为 0，引擎退化为"靠公榜饱和信号避热门 +
复用已验证轴"，并显式标注"样本不足只作启发、不作铁律"。引擎只在被告知的题材集合内推荐
（战绩库题材 ∪ `--genres`），不凭空捏造题材。

用法：
  python3 differentiate.py [--ledger genre_ledger.jsonl] [--baseline market_baseline_*.json] \
      [--genres 仙侠,都市,悬疑] [--metric follow_next_rate] [--min-samples 2] [--top 12] \
      [--out 差异化候选.md] [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import DIFFERENTIATION_CANDIDATES_KIND, GENRE_PERFORMANCE_RECORD_KIND  # noqa: E402

LEDGER_KIND = GENRE_PERFORMANCE_RECORD_KIND
LEDGER_REL_PATH = os.path.join("生产战绩", "genre_ledger.jsonl")
OUT_REL = os.path.join("生产战绩", "差异化候选")

# 特征轴枚举（镜像 n2d-feedback 的 classify_* 输出值；genre/subgenre 数据驱动不在此固定）。
OPENING_TYPES = ("cold_conflict", "system_hook", "reverse_flash", "spectacle_hook", "dialogue_hook", "slow_lore")
CLIFFHANGER_TYPES = ("crisis_suspend", "truth_half_reveal", "reversal_signal", "resolved_clean")
OPENING_CN = {"cold_conflict": "冷开场冲突", "system_hook": "系统钩", "reverse_flash": "倒叙闪回",
              "spectacle_hook": "奇观开场", "dialogue_hook": "对白钩", "slow_lore": "慢设定"}
CLIFF_CN = {"crisis_suspend": "危机悬置", "truth_half_reveal": "真相半露", "reversal_signal": "反转预告",
            "resolved_clean": "收干净"}
AXIS_VALUES = {"opening_type": OPENING_TYPES, "cliffhanger_type": CLIFFHANGER_TYPES}


def default_ledger_path(start: str = ".") -> str:
    env = os.environ.get("N2D_GENRE_LEDGER")
    if env:
        return env
    cur = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(cur, "skills")) or os.path.isdir(os.path.join(cur, ".git")):
            return os.path.join(cur, LEDGER_REL_PATH)
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.path.join(os.path.abspath(start), LEDGER_REL_PATH)
        cur = parent


def load_ledger(path: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not path or not os.path.isfile(path):
        return records
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict) and rec.get("kind") == LEDGER_KIND:
                records.append(rec)
    return records


def load_baseline_signals(path: str) -> List[str]:
    """novel-score market_baseline_*.json → 扁平化所有 rank signal 字符串（公榜饱和信号源）。"""
    if not path or not os.path.isfile(path):
        return []
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (ValueError, OSError):
        return []
    signals: List[str] = []
    for src in (data.get("sources") or []) if isinstance(data, dict) else []:
        for s in src.get("signals", []) or []:
            if isinstance(s, str):
                signals.append(s)
    return signals


def _plays(rec: Dict[str, Any]) -> float:
    return max(1.0, float((rec.get("metrics") or {}).get("plays") or 1.0))


def saturation_by_genre(genres: List[str], baseline_signals: List[str]) -> Dict[str, int]:
    """每个候选题材在公榜信号里出现的次数 = 市场饱和度（越高越"被做烂"）。"""
    sat: Dict[str, int] = {}
    blob = " ".join(baseline_signals)
    for g in genres:
        g = (g or "").strip()
        if g:
            sat[g] = blob.count(g)
    return sat


def axis_value_performance(records: List[Dict[str, Any]], axis: str, metric: str) -> Dict[str, float]:
    """每个轴值的播放量加权 metric 均值（题材取 genre 字段，特征轴取 features[axis]）。"""
    num: Dict[str, float] = defaultdict(float)
    wt: Dict[str, float] = defaultdict(float)
    for rec in records:
        value = rec.get("genre") if axis == "genre" else (rec.get("features") or {}).get(axis)
        value = str(value or "").strip()
        m = (rec.get("metrics") or {}).get(metric)
        if not value or not isinstance(m, (int, float)):
            continue
        w = _plays(rec)
        num[value] += float(m) * w
        wt[value] += w
    return {v: round(num[v] / wt[v], 4) for v in num if wt[v]}


def proven_values(records: List[Dict[str, Any]], axis: str, metric: str, min_samples: int) -> Dict[str, float]:
    """轴值"已验证有效" = 加权 metric ≥ 该轴全局加权均值，且样本数 ≥ min_samples。"""
    perf = axis_value_performance(records, axis, metric)
    counts: Dict[str, int] = Counter()
    for rec in records:
        value = rec.get("genre") if axis == "genre" else (rec.get("features") or {}).get(axis)
        value = str(value or "").strip()
        if value and isinstance((rec.get("metrics") or {}).get(metric), (int, float)):
            counts[value] += 1
    if not perf:
        return {}
    global_mean = sum(perf.values()) / len(perf)
    return {v: s for v, s in perf.items() if s >= global_mean and counts[v] >= min_samples}


def occupancy(records: List[Dict[str, Any]]) -> Counter:
    """我们已做过的 (genre, opening_type, cliffhanger_type) 组合计数。"""
    occ: Counter = Counter()
    for rec in records:
        g = str(rec.get("genre") or "").strip()
        f = rec.get("features") or {}
        o = str(f.get("opening_type") or "").strip()
        c = str(f.get("cliffhanger_type") or "").strip()
        if g:
            occ[(g, o or "*", c or "*")] += 1
    return occ


def candidate_genres(records: List[Dict[str, Any]], extra: List[str]) -> List[str]:
    seen = {str(r.get("genre") or "").strip() for r in records}
    seen |= {g.strip() for g in extra}
    return sorted(g for g in seen if g)


def build_candidates(
    records: List[Dict[str, Any]],
    genres: List[str],
    *,
    metric: str = "follow_next_rate",
    min_samples: int = 2,
    baseline_signals: Optional[List[str]] = None,
    top: int = 12,
) -> Dict[str, Any]:
    baseline_signals = baseline_signals or []
    occ = occupancy(records)
    sat = saturation_by_genre(genres, baseline_signals)
    max_sat = max(sat.values()) if sat else 0
    proven_open = proven_values(records, "opening_type", metric, min_samples)
    proven_cliff = proven_values(records, "cliffhanger_type", metric, min_samples)
    genre_perf = axis_value_performance(records, "genre", metric)

    candidates: List[Dict[str, Any]] = []
    for g in genres:
        sat_g = sat.get(g, 0)
        sat_factor = 1.0 - 0.5 * (sat_g / max_sat) if max_sat else 1.0  # 越饱和惩罚越重（最多 ×0.5）
        for o in OPENING_TYPES:
            for c in CLIFFHANGER_TYPES:
                done = occ.get((g, o, c), 0) + occ.get((g, o, "*"), 0) + occ.get((g, "*", c), 0)
                if done > 0:
                    continue  # 只推未被我们做过的组合（白空间）
                recomb = []
                if o in proven_open:
                    recomb.append(f"开场 {OPENING_CN.get(o,o)}(已验证追更 {proven_open[o]:.0%})")
                if c in proven_cliff:
                    recomb.append(f"结尾 {CLIFF_CN.get(c,c)}(已验证 {proven_cliff[c]:.0%})")
                # 白空间分：基础(未做过=1) × 饱和因子 + 复用已验证轴加成 + 题材自有表现
                score = 1.0 * sat_factor + 0.6 * len(recomb) + (genre_perf.get(g, 0.0))
                candidates.append({
                    "genre": g,
                    "opening_type": o,
                    "cliffhanger_type": c,
                    "label": f"{g} × {OPENING_CN.get(o,o)} × {CLIFF_CN.get(c,c)}",
                    "score": round(score, 4),
                    "market_saturation": sat_g,
                    "reuses_proven": recomb,
                    "genre_self_perf": genre_perf.get(g),
                })
    # 优先复用已验证轴 + 非饱和；同分按饱和度升序
    candidates.sort(key=lambda x: (len(x["reuses_proven"]) == 0, x["market_saturation"], -x["score"]))
    return {
        "kind": DIFFERENTIATION_CANDIDATES_KIND,
        "version": 1,
        "metric": metric,
        "min_samples": min_samples,
        "ledger_records": len(records),
        "candidate_genres": genres,
        "proven_opening": proven_open,
        "proven_cliffhanger": proven_cliff,
        "saturated_genres": dict(sorted(sat.items(), key=lambda kv: -kv[1])),
        "occupied_combos": [{"combo": list(k), "n": v} for k, v in occ.most_common()],
        "candidates": candidates[:top],
        "notes": _notes(records, genres, proven_open, proven_cliff, baseline_signals),
    }


def _notes(records, genres, proven_open, proven_cliff, baseline_signals) -> List[str]:
    notes: List[str] = []
    if len(records) < 3:
        notes.append(f"战绩库样本仅 {len(records)} 条——白空间/已验证轴只作启发，不作铁律；多回灌几部再收紧。")
    if not baseline_signals:
        notes.append("未提供公榜基线（--baseline）：无市场饱和信号，仅按自有占用与已验证轴推荐；建议带 novel-score 的 market_baseline。")
    if not proven_open and not proven_cliff:
        notes.append("尚无「已验证有效」的特征轴（样本不足或无 metric）：候选只反映「我们没做过 + 非饱和」，含金量随回灌提升。")
    if not genres:
        notes.append("没有候选题材：战绩库为空且未给 --genres；先回灌或用 --genres 注入要探索的题材。")
    return notes


def render_markdown(report: Dict[str, Any]) -> str:
    lines = ["# 反同质化 · 差异化选题候选", "",
             f"- 战绩库记录数：{report['ledger_records']}　评分指标：{report['metric']}",
             f"- 候选题材：{('、'.join(report['candidate_genres'])) or '无'}", ""]
    for n in report["notes"]:
        lines.append(f"> ⚠️ {n}")
    if report["notes"]:
        lines.append("")
    po = report["proven_opening"]; pc = report["proven_cliffhanger"]
    lines += ["## 已验证有效的特征轴（可复用进新组合）", "",
              f"- 开场：{('、'.join(f'{OPENING_CN.get(k,k)} {v:.0%}' for k,v in po.items())) or '（暂无）'}",
              f"- 结尾：{('、'.join(f'{CLIFF_CN.get(k,k)} {v:.0%}' for k,v in pc.items())) or '（暂无）'}", ""]
    sat = report["saturated_genres"]
    if any(sat.values()):
        lines += ["## 公榜最饱和题材（差异化应避开/慎投）", "",
                  "、".join(f"{g}×{n}" for g, n in sat.items() if n) or "（无）", ""]
    lines += ["## 差异化候选（未被我们做过 × 复用已验证轴 × 避开饱和）", "",
              "| # | 组合 | 复用已验证轴 | 市场饱和 | 分 |", "|---|---|---|---|---|"]
    for i, c in enumerate(report["candidates"], 1):
        lines.append(f"| {i} | {c['label']} | {('；'.join(c['reuses_proven'])) or '—'} | {c['market_saturation']} | {c['score']} |")
    if not report["candidates"]:
        lines.append("| - | （无候选：题材集合为空或全部已做过） | — | — | — |")
    lines += ["", "> 用法：把高分候选作为 `novel-create`/`novel-title` 的选题输入；`novel-score` 评分时第一方战绩先验仍优先。"]
    return "\n".join(lines) + "\n"


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="反同质化差异化引擎：从战绩库反推未被做烂的组合")
    ap.add_argument("--ledger", help=f"题材战绩库；默认 $N2D_GENRE_LEDGER 或 <repo>/{LEDGER_REL_PATH}")
    ap.add_argument("--baseline", help="novel-score market_baseline_*.json（公榜饱和信号，可选）")
    ap.add_argument("--genres", help="额外候选题材（逗号分隔），与战绩库题材并集")
    ap.add_argument("--metric", default="follow_next_rate", help="评判已验证轴用的指标（默认 follow_next_rate）")
    ap.add_argument("--min-samples", type=int, default=2)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--out", help="输出路径（.md 或 .json）；缺省双写 <repo>/生产战绩/差异化候选.{md,json} 供选题 skill 发现")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)

    ledger = ns.ledger or default_ledger_path()
    records = load_ledger(ledger)
    baseline_signals = load_baseline_signals(ns.baseline) if ns.baseline else []
    if not ns.baseline:
        # 自动探测最近一个 market_baseline（同 repo 任意 评分/ 目录），best-effort。
        repo = os.path.dirname(os.path.dirname(os.path.abspath(ledger)))
        found = sorted(glob.glob(os.path.join(repo, "**", "评分", "market_baseline_*.json"), recursive=True))
        if found:
            baseline_signals = load_baseline_signals(found[-1])
    extra = [g.strip() for g in (ns.genres or "").split(",") if g.strip()]
    genres = candidate_genres(records, extra)
    report = build_candidates(records, genres, metric=ns.metric, min_samples=ns.min_samples,
                              baseline_signals=baseline_signals, top=ns.top)
    text = json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report)
    if ns.out:
        os.makedirs(os.path.dirname(os.path.abspath(ns.out)) or ".", exist_ok=True)
        with open(ns.out, "w", encoding="utf-8") as fh:
            fh.write(text + ("\n" if not text.endswith("\n") else ""))
        print(f"[differentiate] wrote {ns.out}", file=sys.stderr)
    else:
        # 缺省双写 canonical 文件，让 novel-create/novel-title 立项/起名时能稳定发现；
        # stdout 仍按 --json 输出，兼容管道用法。候选与战绩库同放在 生产战绩/ 下。
        ledger_parent = os.path.dirname(os.path.abspath(ledger))
        out_dir = ledger_parent if os.path.basename(ledger_parent) == "生产战绩" \
            else os.path.join(ledger_parent, "生产战绩")
        os.makedirs(out_dir, exist_ok=True)
        md_path = os.path.join(out_dir, "差异化候选.md")
        json_path = os.path.join(out_dir, "差异化候选.json")
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(render_markdown(report))
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
        print(f"[differentiate] 候选 → {md_path}", file=sys.stderr)
        print(f"[differentiate] 机读 → {json_path}"
              f"（novel-create/novel-title 立项/起名自动读此文件）", file=sys.stderr)
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
