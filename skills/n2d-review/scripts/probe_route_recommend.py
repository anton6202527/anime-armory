#!/usr/bin/env python3
"""Recommend video routes from consistency probe backend scores."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from collections import defaultdict
from typing import Any, Dict, List, Mapping

import production_consistency as pc


def _num(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _load_json(path: str) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _probe_pack(root: str) -> tuple[Any, str]:
    data, rel = pc._probe_pack(root)  # intentionally reuse n2d-review's accepted locations
    return data, rel


def _score(row: Mapping[str, Any]) -> float | None:
    for key in ("consistency_score", "score", "avg_score", "mean_score", "pass_rate", "quality_score"):
        val = _num(row.get(key))
        if val is not None:
            return val
    return None


def build_recommendations(root: str, ep: str) -> dict:
    data, rel = _probe_pack(root)
    scenarios = pc._probe_rows(data)
    backend_rows = pc._probe_backend_scores(data, scenarios)
    by_backend: Dict[str, List[float]] = defaultdict(list)
    by_scenario: Dict[str, Dict[str, float]] = defaultdict(dict)
    for row in backend_rows:
        backend = str(row.get("backend") or "").strip()
        scenario = str(row.get("scenario") or "overall").strip()
        score = _score(row)
        if backend and score is not None:
            by_backend[backend].append(score)
            by_scenario[scenario][backend] = score
    averages = {backend: sum(vals) / len(vals) for backend, vals in by_backend.items() if vals}
    routes = pc._load_routes(root, ep)
    route_recs: List[dict] = []
    for clip, route in routes.items():
        current = pc._backend_name(route)
        best_backend = ""
        best_score = None
        if averages:
            best_backend, best_score = max(averages.items(), key=lambda item: item[1])
        current_score = next((score for backend, score in averages.items() if pc._backend_match(current, backend)), None)
        route_recs.append({
            "clip": clip,
            "current_backend": current,
            "recommended_backend": best_backend or current,
            "current_score": current_score,
            "recommended_score": best_score,
            "reason": _reason(current, current_score, best_backend, best_score),
        })
    if not routes and averages:
        best_backend, best_score = max(averages.items(), key=lambda item: item[1])
        route_recs.append({
            "clip": "*",
            "current_backend": "",
            "recommended_backend": best_backend,
            "current_score": None,
            "recommended_score": best_score,
            "reason": "未找到当前 video_model_routes；按 probe 均分给出全局推荐。",
        })
    return {
        "kind": "n2d_probe_route_recommendations",
        "version": 1,
        "root": root,
        "episode": ep,
        "source": rel,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "backend_averages": averages,
        "scenario_scores": by_scenario,
        "route_recommendations": route_recs,
    }


def _reason(current: str, current_score: float | None, best: str, best_score: float | None) -> str:
    if not best:
        return "probe 中没有可比较的 backend_scores。"
    if not current:
        return "当前 route 未声明 backend，按 probe 最优后端推荐。"
    if current_score is None:
        return "当前 route 后端未被 probe 覆盖，建议先跑该后端哨兵。"
    if best_score is not None and best_score - current_score > 0.05:
        return "probe 一致性分差超过 0.05，建议显式切换或写 fallback_reason。"
    return "当前路由与 probe 基准基本一致。"


def write_recommendations(root: str, ep: str) -> str:
    path = os.path.join(root, "生产数据", f"video_route_recommendations_{ep}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(build_recommendations(root, ep), fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    return path


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    if ns.write:
        path = write_recommendations(ns.root.rstrip("/"), ns.episode)
        if not ns.json:
            print(path)
            return 0
    payload = build_recommendations(ns.root.rstrip("/"), ns.episode)
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"route recommendations: {len(payload.get('route_recommendations', []))}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(os.sys.argv[1:]))
