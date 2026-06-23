#!/usr/bin/env python3
"""Generate consistency threshold recommendations from CAL jsonl rows.

两层产物：
1. `build_recommendations`（旧）：从人审标注（误报/漏报/导演意图接受）出方向建议（松/紧/加规则）。
2. `build_calibration`（2026-06 新·把 CAL 升为一等公民）：从**金标集** `consistency_golden_set.jsonl`
   按 FCB（Face Consistency Benchmark）那套**多识别器投票**思路，per-(维度, 后端, 风格) 反推
   推荐 floor——因为 `SEMANTIC_FLOOR=0.55` 之类"起步线"复用同一阈值跨后端/风格迟早假绿/假红。
   金标行：{dimension, backend, style, label: pass|fail, scores: {arcface, facenet, sface, ...}}
   或单 `similarity`。floor 取可分时 pass 下界与 fail 上界中点；重叠时走 Youden(TPR-FPR) 最优切点并标
   `separable=false`。样本不足则 `insufficient_samples`，绝不臆造阈值。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Tuple


def _jsonl(path: str) -> List[dict]:
    rows: List[dict] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except FileNotFoundError:
        pass
    return rows


def _calibration_path(root: str) -> str:
    for rel in ("生产数据/consistency_calibration.jsonl", "设定库/consistency_calibration.jsonl"):
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            return path
    return os.path.join(root, "生产数据", "consistency_calibration.jsonl")


def build_recommendations(root: str) -> dict:
    path = _calibration_path(root)
    rows = _jsonl(path)
    by_dim: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    examples: Dict[str, List[dict]] = defaultdict(list)
    for row in rows:
        dim = str(row.get("dimension") or row.get("dim") or "(unknown)").strip()
        label = str(row.get("label") or row.get("review_label") or "").strip()
        if not dim or not label:
            continue
        by_dim[dim][label] += 1
        if len(examples[dim]) < 5:
            examples[dim].append({
                "label": label,
                "reason": row.get("reason"),
                "finding_hash": row.get("finding_hash") or row.get("source_hash"),
            })
    recs: List[dict] = []
    for dim, counts in sorted(by_dim.items()):
        fp = counts.get("false_positive", 0)
        missed = counts.get("missed_by_machine", 0)
        accepted = counts.get("accepted_intentional", 0)
        if fp < 2 and missed < 1 and accepted < 2:
            continue
        direction = "review_rule"
        if missed:
            direction = "tighten_threshold_or_add_rule"
        elif fp >= 2:
            direction = "loosen_threshold_or_add_exemption"
        elif accepted >= 2:
            direction = "add_intentional_override_pattern"
        recs.append({
            "dimension": dim,
            "direction": direction,
            "counts": dict(counts),
            "suggested_action": _suggested_action(dim, direction),
            "examples": examples[dim],
        })
    return {
        "kind": "n2d_consistency_threshold_recommendations",
        "version": 1,
        "root": root,
        "source": os.path.relpath(path, root),
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "recommendations": recs,
    }


def _suggested_action(dim: str, direction: str) -> str:
    if direction == "tighten_threshold_or_add_rule":
        return f"{dim}: 漏检已出现，降低 warn/block 阈值或新增同类规则；复跑历史校准样本确认召回。"
    if direction == "loosen_threshold_or_add_exemption":
        return f"{dim}: 误报重复出现，提高阈值/加入遮挡、风格化或导演意图豁免；保留人工复核。"
    if direction == "add_intentional_override_pattern":
        return f"{dim}: 已有人审接受的导演意图样本，抽象成结构化 signoff 匹配规则。"
    return f"{dim}: 需要人工复核规则。"


MIN_PASS_SAMPLES = 3
MIN_FAIL_SAMPLES = 2


def _golden_path(root: str) -> str:
    for rel in ("生产数据/consistency_golden_set.jsonl", "设定库/consistency_golden_set.jsonl"):
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            return path
    return os.path.join(root, "生产数据", "consistency_golden_set.jsonl")


def _agg_score(row: dict) -> Optional[float]:
    """多识别器投票 → 单行聚合分（FCB：多张人脸识别器各打分，取中位数抗单识别器抖动）。"""
    scores = row.get("scores")
    vals: List[float] = []
    if isinstance(scores, dict):
        vals = [float(v) for v in scores.values() if isinstance(v, (int, float))]
    elif isinstance(scores, (list, tuple)):
        vals = [float(v) for v in scores if isinstance(v, (int, float))]
    if not vals:
        sim = row.get("similarity") if isinstance(row.get("similarity"), (int, float)) else None
        return float(sim) if sim is not None else None
    vals.sort()
    n = len(vals)
    return vals[n // 2] if n % 2 else round((vals[n // 2 - 1] + vals[n // 2]) / 2, 6)


def _is_pass(label: str) -> Optional[bool]:
    t = str(label or "").strip().lower()
    if t in {"pass", "ok", "consistent", "good", "一致", "通过"}:
        return True
    if t in {"fail", "block", "drift", "bad", "漂移", "不一致", "崩"}:
        return False
    return None


def derive_floor(pass_scores: Sequence[float], fail_scores: Sequence[float]) -> dict:
    """从 pass/fail 分布反推推荐 floor。可分→两界中点；重叠→Youden 最优切点 + separable=false。"""
    p = sorted(pass_scores)
    f = sorted(fail_scores)
    if len(p) < MIN_PASS_SAMPLES or len(f) < MIN_FAIL_SAMPLES:
        return {"status": "insufficient_samples", "pass_n": len(p), "fail_n": len(f),
                "need": f">= {MIN_PASS_SAMPLES} pass & {MIN_FAIL_SAMPLES} fail"}
    if max(f) < min(p):  # 完全可分
        floor = round((max(f) + min(p)) / 2, 3)
        return {"status": "separable", "recommended_floor": floor, "pass_n": len(p), "fail_n": len(f),
                "margin": round(min(p) - max(f), 3)}
    # 重叠：在候选切点里取 Youden's J = TPR - FPR 最大者（FPR=fail 被判 pass 的比例）
    cands = sorted(set(p) | set(f))
    best_floor, best_j = cands[0], -1.0
    for c in cands:
        tpr = sum(1 for x in p if x >= c) / len(p)
        fpr = sum(1 for x in f if x >= c) / len(f)
        j = tpr - fpr
        if j > best_j:
            best_j, best_floor = j, c
    return {"status": "overlap", "recommended_floor": round(best_floor, 3), "youden_j": round(best_j, 3),
            "separable": False, "pass_n": len(p), "fail_n": len(f),
            "note": "pass/fail 分布重叠——floor 取 Youden 最优切点，建议补金标样本或换更强识别器组提升可分性。"}


def build_calibration(root: str) -> dict:
    rows = _jsonl(_golden_path(root))
    groups: Dict[Tuple[str, str, str], Dict[str, List[float]]] = defaultdict(lambda: {"pass": [], "fail": []})
    recognizers: Dict[Tuple[str, str, str], set] = defaultdict(set)
    for row in rows:
        dim = str(row.get("dimension") or row.get("dim") or "").strip()
        backend = str(row.get("backend") or "any").strip() or "any"
        style = str(row.get("style") or "any").strip() or "any"
        is_pass = _is_pass(row.get("label") or row.get("review_label"))
        score = _agg_score(row)
        if not dim or is_pass is None or score is None:
            continue
        groups[(dim, backend, style)]["pass" if is_pass else "fail"].append(score)
        if isinstance(row.get("scores"), dict):
            recognizers[(dim, backend, style)].update(row["scores"].keys())
    calibrations: List[dict] = []
    for (dim, backend, style), dist in sorted(groups.items()):
        floor = derive_floor(dist["pass"], dist["fail"])
        floor.update({"dimension": dim, "backend": backend, "style": style,
                      "recognizers": sorted(recognizers[(dim, backend, style)])})
        calibrations.append(floor)
    return {
        "kind": "n2d_consistency_threshold_calibration",
        "version": 1,
        "root": root,
        "source": os.path.relpath(_golden_path(root), root),
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "protocol": "FCB-style multi-recognizer median vote; per (dimension, backend, style) floor",
        "calibrations": calibrations,
    }


def write_calibration(root: str) -> str:
    path = os.path.join(root, "生产数据", "consistency_threshold_calibration.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(build_calibration(root), fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    return path


def write_recommendations(root: str) -> str:
    path = os.path.join(root, "生产数据", "consistency_threshold_recommendations.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(build_recommendations(root), fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    return path


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--calibrate", action="store_true",
                    help="从金标集反推 per-(维度,后端,风格) floor（FCB 多识别器投票），而非人审方向建议")
    ns = ap.parse_args(argv)
    root = ns.root.rstrip("/")
    if ns.calibrate:
        if ns.write:
            path = write_calibration(root)
            if not ns.json:
                print(path)
                return 0
        payload = build_calibration(root)
        if ns.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            cal = payload.get("calibrations", [])
            print(f"calibrations: {len(cal)}")
            for c in cal:
                floor = c.get("recommended_floor", "—")
                print(f"  {c['dimension']}/{c['backend']}/{c['style']}: floor={floor} ({c['status']})")
        return 0
    if ns.write:
        path = write_recommendations(root)
        if not ns.json:
            print(path)
            return 0
    payload = build_recommendations(root)
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"recommendations: {len(payload.get('recommendations', []))}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(os.sys.argv[1:]))
