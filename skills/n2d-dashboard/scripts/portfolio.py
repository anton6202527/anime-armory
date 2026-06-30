#!/usr/bin/env python3
"""跨作品 portfolio rollup + 吞吐率指标 —— 把每部剧的 per-work dashboard 汇成「制片厂级」视图。

`dashboard.py` 只算单部剧（`<作品根>`）；批量产线同时在做多部剧时，没有「全盘成本/完成集数/
单分钟成本/一次通过率/吞吐率」的组合视图。本脚本扫多个作品根、复用 `dashboard.aggregate_events`
逐部聚合，再汇成 portfolio：

- 组合成本 / 完成集数 / 完成分钟 / 单完成分钟成本（跨剧）；
- 加权一次通过率 / 重抽率（按生成次数加权，不是简单平均）；
- 回收比（recoup = 净收益 / 成本）跨剧；
- **吞吐率指标**：从事件时间戳算日历跨度 → 完成集/天、完成分钟/天、单剧速度（dashboard 此前只有
  「生成耗时之和」，不是日历吞吐）。

报告型：写 `<base>/生产数据/portfolio.{json,md}`（或 `--out` 指定）。纯标准库；聚合是纯函数，有 pytest。

用法：python3 portfolio.py [base目录] [--out DIR] [--json]
  base 默认=当前目录；自动发现其下含 `生产数据/production_events.jsonl` 的作品根（递归一层~两层）。
  也可显式 `--work <作品根> --work <作品根> ...` 指定要汇总哪几部。
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_dashboard_module():
    spec = importlib.util.spec_from_file_location("n2d_dashboard", os.path.join(SCRIPT_DIR, "dashboard.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── 成本/时间小工具（纯函数）──────────────────────────────────────────────────

def add_cost(into: Dict[str, float], more: Dict[str, Any]) -> None:
    """把 {unit: amount} 成本累加进 into（跨剧/跨集同单位相加）。纯函数（原地）。"""
    for unit, amt in (more or {}).items():
        try:
            into[unit] = round(float(into.get(unit, 0.0)) + float(amt), 4)
        except (TypeError, ValueError):
            continue


def divide_cost(cost: Dict[str, float], denom: float) -> Dict[str, float]:
    if not denom or denom <= 0:
        return {}
    return {unit: round(float(amt) / denom, 4) for unit, amt in (cost or {}).items()}


def _parse_ts(ts: Optional[str]) -> Optional[dt.datetime]:
    """解析事件 ts → **UTC 归一**的 aware datetime。

    归一是关键：混合时区(+08:00 vs Z)的字符串**字典序**比较会排错（同一瞬间排成先后不同），
    且 aware 与 naive 相减会 TypeError。统一转 UTC 后比较/相减才正确——修跨机/跨时区舰队的吞吐错算。"""
    raw = str(ts or "").strip()
    if not raw:
        return None
    try:
        d = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        try:
            d = dt.datetime.fromisoformat(raw[:19])
        except Exception:
            return None
    return d.replace(tzinfo=dt.timezone.utc) if d.tzinfo is None else d.astimezone(dt.timezone.utc)


def span_days(first_ts: Optional[str], last_ts: Optional[str]) -> Optional[float]:
    """日历跨度（天·≥一点点，避免除零）。两端任一缺→None。纯函数。"""
    a, b = _parse_ts(first_ts), _parse_ts(last_ts)
    if a is None or b is None:
        return None
    secs = (b - a).total_seconds()
    return max(secs / 86400.0, 1.0 / 24)  # 地板=1 小时，避免「同一天出 3 集」算出天文吞吐


# ── portfolio 聚合（纯函数·可测）────────────────────────────────────────────────

def aggregate_portfolio(works: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """把多部剧的 {name, totals, finished_episodes, finished_min, first_ts, last_ts} 汇成 portfolio。

    纯函数：不读盘、不算时间（now 由调用方注入到行里）。totals 取自 dashboard.aggregate_events 的 totals。"""
    rows: List[Dict[str, Any]] = []
    cost_total: Dict[str, float] = {}
    revenue_total: Dict[str, float] = {}
    net_total: Dict[str, float] = {}
    tot_finished_ep = 0
    tot_finished_min = 0.0
    tot_one_pass = 0
    tot_attempts = 0
    tot_redraw = 0
    tot_plays = 0
    tot_episodes = 0
    tot_qa_blockers = 0
    tot_qa_warnings = 0
    tot_consistency_blockers = 0
    tot_consistency_warnings = 0
    earliest: Optional[str] = None
    latest: Optional[str] = None
    earliest_dt: Optional[dt.datetime] = None
    latest_dt: Optional[dt.datetime] = None
    active_dates_union: set = set()  # 全作品有事件的不同日历日(UTC)并集 → backfill 稳健吞吐分母

    for w in works:
        t = w.get("totals") or {}
        fin_ep = int(w.get("finished_episodes") or 0)
        fin_min = float(w.get("finished_min") or 0.0)
        attempts = int(t.get("generation_attempts") or 0)
        one_pass = int(t.get("one_pass_count") or 0)
        redraw = int(t.get("redraw_count") or 0)
        qa_blockers = int(t.get("qa_blockers") or 0)
        qa_warnings = int(t.get("qa_warnings") or 0)
        consistency_blockers = int(t.get("consistency_blockers") or 0)
        consistency_warnings = int(t.get("consistency_warnings") or 0)
        wcost = t.get("cost_totals") or {}
        add_cost(cost_total, wcost)
        add_cost(revenue_total, t.get("release_revenue_totals") or {})
        add_cost(net_total, t.get("release_net_totals") or {})
        tot_finished_ep += fin_ep
        tot_finished_min += fin_min
        tot_one_pass += one_pass
        tot_attempts += attempts
        tot_redraw += redraw
        tot_plays += int(t.get("release_plays") or 0)
        tot_episodes += int(t.get("episode_count") or 0)
        tot_qa_blockers += qa_blockers
        tot_qa_warnings += qa_warnings
        tot_consistency_blockers += consistency_blockers
        tot_consistency_warnings += consistency_warnings
        first_ts, last_ts = w.get("first_ts"), w.get("last_ts")
        # 按 UTC 归一时间比较选首/末事件（非字典序，避免混时区排错）。
        ft, lt = _parse_ts(first_ts), _parse_ts(last_ts)
        if ft is not None and (earliest_dt is None or ft < earliest_dt):
            earliest_dt, earliest = ft, first_ts
        if lt is not None and (latest_dt is None or lt > latest_dt):
            latest_dt, latest = lt, last_ts
        active_dates_union.update(w.get("active_dates") or [])
        sd = span_days(first_ts, last_ts)
        rows.append({
            "work": w.get("name") or "",
            "episodes": int(t.get("episode_count") or 0),
            "finished_episodes": fin_ep,
            "finished_min": round(fin_min, 2),
            "cost_totals": wcost,
            "cost_per_finished_min": divide_cost(wcost, fin_min) if fin_min else {},
            "one_pass_rate": round(one_pass / attempts, 4) if attempts else None,
            "redraw_rate": round(redraw / attempts, 4) if attempts else None,
            "qa_blockers": qa_blockers,
            "qa_warnings": qa_warnings,
            "warnings_per_attempt": round(qa_warnings / attempts, 4) if attempts else None,
            "blockers_per_attempt": round(qa_blockers / attempts, 4) if attempts else None,
            "consistency_blockers": consistency_blockers,
            "consistency_warnings": consistency_warnings,
            "release_plays": int(t.get("release_plays") or 0),
            "recoup_ratio": t.get("recoup_ratio") or {},
            "release_net_totals": dict(t.get("release_net_totals") or {}),
            "span_days": round(sd, 2) if sd is not None else None,
            "episodes_per_day": round(fin_ep / sd, 2) if (sd and fin_ep) else None,
        })

    rows.sort(key=lambda r: str(r["work"]))
    portfolio_span = span_days(earliest, latest)
    return {
        "kind": "n2d_portfolio_rollup",
        "version": 1,
        "work_count": len(rows),
        "total_episodes": tot_episodes,
        "total_finished_episodes": tot_finished_ep,
        "total_finished_min": round(tot_finished_min, 2),
        "cost_totals": cost_total,
        "cost_per_finished_min": divide_cost(cost_total, tot_finished_min) if tot_finished_min else {},
        "one_pass_rate": round(tot_one_pass / tot_attempts, 4) if tot_attempts else None,
        "redraw_rate": round(tot_redraw / tot_attempts, 4) if tot_attempts else None,
        "qa_blockers_total": tot_qa_blockers,
        "qa_warnings_total": tot_qa_warnings,
        "consistency_blockers_total": tot_consistency_blockers,
        "consistency_warnings_total": tot_consistency_warnings,
        "gate_noise": {
            "warnings_per_attempt": round(tot_qa_warnings / tot_attempts, 4) if tot_attempts else None,
            "blockers_per_attempt": round(tot_qa_blockers / tot_attempts, 4) if tot_attempts else None,
            "warning_to_blocker_ratio": round(tot_qa_warnings / tot_qa_blockers, 4) if tot_qa_blockers else None,
        },
        "release_plays": tot_plays,
        "release_revenue_totals": revenue_total,
        "release_net_totals": net_total,
        "recoup_ratio": _ratio(net_total, cost_total),
        "throughput": {
            "span_days": round(portfolio_span, 2) if portfolio_span is not None else None,
            "first_event": earliest,
            "last_event": latest,
            "episodes_per_day": round(tot_finished_ep / portfolio_span, 3) if (portfolio_span and tot_finished_ep) else None,
            "finished_min_per_day": round(tot_finished_min / portfolio_span, 3) if (portfolio_span and tot_finished_min) else None,
            # active_days=有生产事件的不同日历日数：同会话 backfill（全压一天）下 span_days 塌到 1 小时地板会把
            # 集/天虚高 ~24×，active_days 用「真正干活的天数」当分母更稳健。两个口径都给，由看板取舍。
            "active_days": len(active_dates_union) or None,
            "episodes_per_active_day": round(tot_finished_ep / len(active_dates_union), 3) if (active_dates_union and tot_finished_ep) else None,
        },
        "rankings": _portfolio_rankings(rows),
        "works": rows,
    }


def _portfolio_rankings(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """管理层"先动哪部"三问：通过率最低先救、阻断最多先停、净回收为负在亏钱。

    dashboard/portfolio 此前只算成本/吞吐/通过率聚合，没把"哪部该优先处理"显式排出来——
    这是舰队层缺的决策口（不重算，只对已聚合的 works 行排序/筛选）。
    """
    rated = [r for r in rows if r.get("one_pass_rate") is not None]
    worst_one_pass = sorted(rated, key=lambda r: r["one_pass_rate"])[:5]
    most_blockers = sorted(
        rows,
        key=lambda r: (int(r.get("qa_blockers") or 0) + int(r.get("consistency_blockers") or 0)),
        reverse=True,
    )
    most_blockers = [r for r in most_blockers
                     if (int(r.get("qa_blockers") or 0) + int(r.get("consistency_blockers") or 0)) > 0][:5]
    noisy = [r for r in rows if r.get("warnings_per_attempt") is not None and int(r.get("qa_warnings") or 0) > 0]
    highest_gate_noise = sorted(
        noisy,
        key=lambda r: (float(r.get("warnings_per_attempt") or 0.0), int(r.get("qa_warnings") or 0)),
        reverse=True,
    )[:5]
    losing_money = [
        {"work": r["work"], "release_net_totals": r.get("release_net_totals") or {}}
        for r in rows
        if any((_num(v) or 0) < 0 for v in (r.get("release_net_totals") or {}).values())
    ]
    return {
        "worst_one_pass": [{"work": r["work"], "one_pass_rate": r["one_pass_rate"]} for r in worst_one_pass],
        "most_blockers": [
            {"work": r["work"], "qa_blockers": int(r.get("qa_blockers") or 0),
             "consistency_blockers": int(r.get("consistency_blockers") or 0)}
            for r in most_blockers
        ],
        "highest_gate_noise": [
            {"work": r["work"], "qa_warnings": int(r.get("qa_warnings") or 0),
             "warnings_per_attempt": r.get("warnings_per_attempt")}
            for r in highest_gate_noise
        ],
        "losing_money": losing_money,
    }


def _num(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _ratio(net: Dict[str, float], cost: Dict[str, float]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for unit, c in (cost or {}).items():
        try:
            if float(c):
                out[unit] = round(float(net.get(unit, 0.0)) / float(c), 4)
        except (TypeError, ValueError):
            continue
    return out


# ── 发现作品根 + 逐部聚合（IO）──────────────────────────────────────────────────

def discover_works(base: str, max_depth: int = 2) -> List[str]:
    """递归（≤max_depth 层）找含 `生产数据/production_events.jsonl` 的作品根。"""
    found: List[str] = []
    base = os.path.abspath(base)

    def _walk(d: str, depth: int) -> None:
        if depth > max_depth:
            return
        if os.path.isfile(os.path.join(d, "生产数据", "production_events.jsonl")):
            found.append(d)
            return  # 作品根不再下钻
        try:
            entries = sorted(os.listdir(d))
        except Exception:
            return
        for name in entries:
            if name.startswith(".") or name in {"生产数据", "出图", "出视频", "合成", "脚本"}:
                continue
            sub = os.path.join(d, name)
            if os.path.isdir(sub):
                _walk(sub, depth + 1)

    _walk(base, 0)
    return found


def summarize_work(dash, root: str) -> Optional[Dict[str, Any]]:
    """复用 dashboard.aggregate_events 聚合单部剧，提取 portfolio 需要的字段。"""
    try:
        events = dash.load_events(root)
    except Exception:
        return None
    if not events:
        return None
    db = dash.aggregate_events(root, events)
    totals = db.get("totals") or {}
    eps = db.get("episodes") or []
    finished_episodes = sum(1 for e in eps if float(e.get("runtime_sec") or 0) > 0)
    finished_min = round(float(totals.get("runtime_sec") or 0) / 60.0, 4)
    # 按 UTC 归一时间排序选首尾（非字典序，避免混时区排错）；active_dates=有事件的不同日历日(UTC)。
    parsed = [(_parse_ts(ev.get("ts")), str(ev.get("ts"))) for ev in events if ev.get("ts")]
    parsed = [p for p in parsed if p[0] is not None]
    parsed.sort(key=lambda x: x[0])
    active_dates = sorted({p[0].date().isoformat() for p in parsed})
    return {
        "name": os.path.basename(os.path.normpath(root)),
        "root": root,
        "totals": totals,
        "finished_episodes": finished_episodes,
        "finished_min": finished_min,
        "first_ts": parsed[0][1] if parsed else None,
        "last_ts": parsed[-1][1] if parsed else None,
        "active_dates": active_dates,
    }


def _fmt_cost(cost: Dict[str, Any]) -> str:
    return "、".join(f"{amt}{unit}" for unit, amt in (cost or {}).items()) or "—"


def render_md(p: Dict[str, Any]) -> str:
    th = p.get("throughput") or {}
    gn = p.get("gate_noise") or {}
    lines = [
        "# 跨作品 Portfolio Rollup", "",
        f"- 作品数: {p['work_count']}　总集数: {p['total_episodes']}　完成集: {p['total_finished_episodes']}　完成分钟: {p['total_finished_min']}",
        f"- 组合成本: {_fmt_cost(p['cost_totals'])}　单完成分钟成本: {_fmt_cost(p['cost_per_finished_min'])}",
        f"- 一次通过率: {p['one_pass_rate']}　重抽率: {p['redraw_rate']}　总播放: {p['release_plays']}　回收比: {_fmt_cost(p['recoup_ratio'])}",
        f"- **吞吐率**: 跨度 {th.get('span_days')} 天　完成集/天 {th.get('episodes_per_day')}　完成分钟/天 {th.get('finished_min_per_day')}"
        f"　｜ 活跃天 {th.get('active_days')}　完成集/活跃天 {th.get('episodes_per_active_day')}（backfill 稳健口径）",
        f"- **QA 债**: QA 阻断合计 {p.get('qa_blockers_total', 0)} / warn {p.get('qa_warnings_total', 0)}"
        f"　一致性阻断合计 {p.get('consistency_blockers_total', 0)} / warn {p.get('consistency_warnings_total', 0)}",
        f"- **Gate 噪声**: warn/生成 {gn.get('warnings_per_attempt')}　block/生成 {gn.get('blockers_per_attempt')}"
        f"　warn:block {gn.get('warning_to_blocker_ratio')}",
        "", "## 逐部",
        "| 作品 | 集数 | 完成 | 完成分钟 | 成本 | 单完成分钟成本 | 一次过 | QA阻断 | QAwarn | warn/生成 | 一致性阻断 | 集/天 | 播放 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in p.get("works", []):
        lines.append(
            f"| {r['work']} | {r['episodes']} | {r['finished_episodes']} | {r['finished_min']} | "
            f"{_fmt_cost(r['cost_totals'])} | {_fmt_cost(r['cost_per_finished_min'])} | "
            f"{r['one_pass_rate']} | {r.get('qa_blockers', 0)} | {r.get('qa_warnings', 0)} | "
            f"{r.get('warnings_per_attempt')} | {r.get('consistency_blockers', 0)} | "
            f"{r['episodes_per_day']} | {r['release_plays']} |")

    rk = p.get("rankings") or {}
    if rk.get("losing_money"):
        lines += ["", "## ⚠️ 在亏钱的剧（净回收为负·优先复盘止损）"]
        for r in rk["losing_money"]:
            lines.append(f"- {r['work']}：净 {_fmt_cost(r['release_net_totals'])}")
    if rk.get("worst_one_pass"):
        w = rk["worst_one_pass"][0]
        lines += ["", f"## 先动哪部：一次通过率最低 = {w['work']}（{w['one_pass_rate']}）"]
    if rk.get("most_blockers"):
        b = rk["most_blockers"][0]
        lines.append(f"## QA 债最重 = {b['work']}（QA {b['qa_blockers']} · 一致性 {b['consistency_blockers']}）")
    if rk.get("highest_gate_noise"):
        n = rk["highest_gate_noise"][0]
        lines.append(f"## Gate 噪声最高 = {n['work']}（warn/生成 {n['warnings_per_attempt']} · warn {n['qa_warnings']}）")
    return "\n".join(lines) + "\n"


def build(base: str, explicit_works: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    dash = _load_dashboard_module()
    roots = list(explicit_works) if explicit_works else discover_works(base)
    summaries = [s for s in (summarize_work(dash, r) for r in roots) if s]
    portfolio = aggregate_portfolio(summaries)
    portfolio["base"] = os.path.abspath(base)
    portfolio["discovered_roots"] = roots
    return portfolio


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("base", nargs="?", default=".", help="扫描基目录（默认当前目录）")
    ap.add_argument("--work", action="append", default=[], help="显式指定作品根（可多次）")
    ap.add_argument("--out", help="输出目录（默认 <base>/生产数据）")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    portfolio = build(ns.base, ns.work or None)
    out_dir = ns.out or os.path.join(os.path.abspath(ns.base), "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    jp = os.path.join(out_dir, "portfolio.json")
    with open(jp, "w", encoding="utf-8") as fh:
        json.dump(portfolio, fh, ensure_ascii=False, indent=2, sort_keys=True)
    with open(os.path.join(out_dir, "portfolio.md"), "w", encoding="utf-8") as fh:
        fh.write(render_md(portfolio))
    if ns.json:
        print(json.dumps(portfolio, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        th = portfolio.get("throughput") or {}
        print(f"Portfolio：{portfolio['work_count']} 部剧，完成 {portfolio['total_finished_episodes']} 集 / "
              f"{portfolio['total_finished_min']} 分钟，组合成本 {_fmt_cost(portfolio['cost_totals'])}")
        print(f"吞吐率：完成集/天 {th.get('episodes_per_day')}　完成分钟/天 {th.get('finished_min_per_day')}"
              f"（跨度 {th.get('span_days')} 天）")
        print(f"→ {jp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
