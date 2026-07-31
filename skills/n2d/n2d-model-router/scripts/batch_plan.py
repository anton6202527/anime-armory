#!/usr/bin/env python3
"""batch/隔夜半价档：提交清单 + 折扣计费投影（F4·2026-06-26）。

2026 视频/图像生成 API 普遍上线「batch/隔夜」档：24h SLA、约 **-50%**（OpenAI Batch 覆盖 /v1/images
+/v1/videos、Seedance/Sora 同向）。`n2d-model-router` 已对非赶投放窗口的量产集出 `urgency_tier=batch_24h`
**路由意图**，但此前没有：① 一份「该把哪些 clip 走 batch 通道提交」的**提交清单**（后端接入 batch
endpoint 时消费的文件契约）；② 把折扣算进**成本投影**让操作者看见省了多少。本脚本补这两块。

**诚实边界（关键）**：本脚本只产 plan + 折扣投影，**不调用任何后端 batch API**（实际 async 提交由
执行适配层在视频后端 batch 通道接入后做——那才真省钱）。也**不臆造各家单价**（2026 多源价格互相打架、
未经独立核验）：要 ¥ 估算请传 `--rate <每秒成本>`（你按当前后端官方价填）；不传则只报「可走 batch 的
clip 数 / 总秒数 / 折扣率」+「省下折扣那一半」的相对量。dashboard 侧已按 urgency_tier 拆 realtime vs
batch 的**实际**成本账，与本脚本的**事前**投影互补。

用法：python3 batch_plan.py <作品根> 第N集 [--rate 每秒成本] [--unit 单位] [--json]
纯标准库；plan/折扣是纯函数，有 pytest（test_batch_plan.py）。
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Mapping, Optional, Sequence

URGENCY_BATCH = "batch_24h"
KIND = "n2d_batch_submission_plan"
VERSION = 1


def batch_discount_factor() -> float:
    """付费倍率：batch 档付 factor× 原价（-50% → 0.5）。env N2D_BATCH_DISCOUNT 可调（取 0–1）。纯函数。"""
    try:
        f = float(os.environ.get("N2D_BATCH_DISCOUNT", "0.5") or "0.5")
    except ValueError:
        f = 0.5
    return min(max(f, 0.0), 1.0)


def apply_discount(cost_per_sec: Optional[float], seconds: float, factor: float) -> Dict[str, Optional[float]]:
    """单 clip realtime / batch 成本 + 省下额。无单价→全 None（只算秒数·不臆造钱）。纯函数。"""
    if cost_per_sec is None or seconds <= 0:
        return {"realtime": None, "batch": None, "savings": None}
    rt = round(float(cost_per_sec) * seconds, 4)
    bt = round(rt * factor, 4)
    return {"realtime": rt, "batch": bt, "savings": round(rt - bt, 4)}


def build_batch_plan(clips: Sequence[Mapping[str, Any]], *,
                     factor: Optional[float] = None,
                     rate_per_sec: Optional[float] = None,
                     unit: str = "") -> Dict[str, Any]:
    """从逐 clip {clip_id, urgency_tier, backend, duration_sec} 产 batch 提交清单 + 折扣投影。纯函数·可测。

    只收 `urgency_tier==batch_24h` 的 clip（量产档·非赶投放）。rate_per_sec 缺→只报秒数/折扣率不报钱。"""
    factor = batch_discount_factor() if factor is None else min(max(float(factor), 0.0), 1.0)
    rows: List[Dict[str, Any]] = []
    total_seconds = 0.0
    total_realtime = 0.0
    total_batch = 0.0
    have_cost = rate_per_sec is not None
    for c in clips:
        if str(c.get("urgency_tier") or "").strip() != URGENCY_BATCH:
            continue
        secs = float(c.get("duration_sec") or 0.0)
        money = apply_discount(rate_per_sec, secs, factor)
        total_seconds += secs
        if money["realtime"] is not None:
            total_realtime += money["realtime"]
            total_batch += money["batch"]
        rows.append({
            "clip_id": str(c.get("clip_id") or ""),
            "backend": str(c.get("backend") or c.get("primary_backend") or ""),
            "duration_sec": round(secs, 3),
            "submit_channel": "batch_24h",
            "est_cost_realtime": money["realtime"],
            "est_cost_batch": money["batch"],
            "est_savings": money["savings"],
        })
    rows.sort(key=lambda r: r["clip_id"])
    summary = {
        "batch_eligible_clips": len(rows),
        "batch_eligible_seconds": round(total_seconds, 2),
        "discount_factor": factor,
        "discount_pct": round((1.0 - factor) * 100, 1),
        "unit": unit if have_cost else "",
        "est_cost_realtime": round(total_realtime, 4) if have_cost else None,
        "est_cost_batch": round(total_batch, 4) if have_cost else None,
        "est_savings": round(total_realtime - total_batch, 4) if have_cost else None,
    }
    return {
        "kind": KIND, "version": VERSION,
        "summary": summary,
        "clips": rows,
        "notes": [
            "提交清单：后端接入 batch endpoint 后，按本清单把这些 clip 走 batch_24h 通道异步提交（24h SLA·约 -50%）。",
            "本脚本只产 plan + 投影，不调用后端 API；不传 --rate 时不臆造单价、只报秒数与折扣率。",
        ],
    }


# ── IO：从 video_model_routes.json + 镜头时长.json 采逐 clip ─────────────────────

def _load(path: str) -> Optional[Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _routes_path(root: str, ep: str) -> str:
    return os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json")


def _durations(root: str, ep: str) -> Dict[str, float]:
    """clip_id → 时长秒，从 镜头时长.json（list[{clip,seconds}] 或 {clip:sec}）。缺→{}。"""
    out: Dict[str, float] = {}
    data = _load(os.path.join(root, "脚本", ep, "镜头时长.json"))
    if isinstance(data, list):
        for r in data:
            if isinstance(r, dict):
                cid = str(r.get("clip") or r.get("clip_id") or r.get("id") or "").strip()
                sec = r.get("seconds") or r.get("duration") or r.get("duration_sec")
                if cid and isinstance(sec, (int, float)):
                    out[cid] = float(sec)
    elif isinstance(data, dict):
        for cid, sec in data.items():
            if isinstance(sec, (int, float)):
                out[str(cid)] = float(sec)
    return out


def gather_clips(root: str, ep: str) -> List[Dict[str, Any]]:
    """从 routes 取逐 clip 的 urgency_tier/backend，并对上时长。"""
    plan = _load(_routes_path(root, ep))
    routes = (plan.get("routes") if isinstance(plan, dict) else None) or []
    durs = _durations(root, ep)
    clips: List[Dict[str, Any]] = []
    for r in routes:
        if not isinstance(r, dict):
            continue
        cid = str(r.get("clip_id") or r.get("clip") or "").strip()
        clips.append({
            "clip_id": cid,
            "urgency_tier": r.get("urgency_tier"),
            "backend": r.get("primary_backend") or r.get("backend"),
            "duration_sec": durs.get(cid, float(r.get("duration_sec") or 0.0)),
        })
    return clips


def build(root: str, ep: str, *, rate_per_sec: Optional[float] = None, unit: str = "") -> Dict[str, Any]:
    plan = build_batch_plan(gather_clips(root, ep), rate_per_sec=rate_per_sec, unit=unit)
    plan["episode"] = ep
    return plan


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--rate", type=float, help="每秒成本（按当前后端官方价填；不传则只报秒数/折扣率·不臆造钱）")
    ap.add_argument("--unit", default="", help="成本单位（如 积分/CNY/USD）")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = ns.root.rstrip("/")
    plan = build(root, ns.episode, rate_per_sec=ns.rate, unit=ns.unit)
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"batch_submission_plan_{ns.episode}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=2, sort_keys=True)
    s = plan["summary"]
    if ns.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        money = (f"，预计省 {s['est_savings']}{s['unit']}（{s['est_cost_realtime']}→{s['est_cost_batch']}）"
                 if s["est_savings"] is not None else "（未传 --rate：只报量·不估钱）")
        print(f"batch 提交清单 {ns.episode}：{s['batch_eligible_clips']} 镜 / {s['batch_eligible_seconds']}s "
              f"可走 batch_24h（-{s['discount_pct']}%）{money}")
        print(f"→ {path}（后端接入 batch 通道后按此异步提交）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
