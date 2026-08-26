#!/usr/bin/env python3
"""Build and summarize a hash-bound, shot-class-stratified video backend pilot.

The planner never claims a backend is good merely because a provider returned
``succeeded``.  A completed trial must bind the current plan, decoded artifact,
QC receipt, and actual-inspection receipt.  With too few real samples the
summary stays ``insufficient_evidence`` and emits no recommendation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


VERSION = 1
PLAN_KIND = "n2d_shot_class_benchmark_plan"
RESULTS_KIND = "n2d_shot_class_benchmark_results"
SUMMARY_KIND = "n2d_shot_class_benchmark_summary"

CLASS_BACKENDS: Dict[str, Tuple[str, ...]] = {
    "dialogue_closeup": ("gemini_omni", "veo", "kling"),
    "multi_character_dialogue": ("gemini_omni", "seedance", "kling"),
    "action_contact": ("kling", "seedance", "dreamina"),
    "pursuit_motion": ("seedance", "kling", "veo"),
    "large_establishing": ("veo", "gemini_omni", "seedance"),
    "vfx_magic": ("seedance", "veo", "dreamina"),
    "insert_or_transition": ("dreamina", "gemini_omni", "veo"),
    "general_narrative": ("gemini_omni", "seedance", "veo"),
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def episode_label(raw: str) -> str:
    value = str(raw or "").strip()
    if value.startswith("第") and value.endswith("集"):
        return value
    match = re.search(r"(\d+)", value)
    return f"第{int(match.group(1))}集" if match else value


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def storyboard_path(root: Path, episode: str) -> Path:
    candidates = (
        root / "脚本" / episode / "storyboard.json",
        root / "生产数据" / f"storyboard_{episode}.json",
    )
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(f"storyboard not found for {episode}")


def clip_rows(payload: Any) -> List[Mapping[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, Mapping)]
    if isinstance(payload, Mapping):
        for key in ("clips", "shots", "storyboard"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, Mapping)]
    return []


def clip_id(row: Mapping[str, Any], index: int) -> str:
    return str(row.get("clip_id") or row.get("clip") or row.get("id") or f"Clip_{index:02d}")


def flatten(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(f"{key} {flatten(item)}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(flatten(item) for item in value)
    return str(value or "")


def classify_shot(row: Mapping[str, Any]) -> str:
    text = flatten(row).lower()
    characters = row.get("characters") or row.get("character_ids") or []
    count = len(characters) if isinstance(characters, list) else len(re.findall(r"\bCHAR[_-]?[A-Z0-9]+\b", text, re.I))
    if any(token in text for token in ("fight", "combat", "contact", "grapple", "punch", "kick", "打斗", "交手", "搏斗", "碰撞")):
        return "action_contact"
    if any(token in text for token in ("chase", "pursuit", "running", "vehicle", "flight", "追逐", "狂奔", "飞行", "骑乘", "车辆")):
        return "pursuit_motion"
    if any(token in text for token in ("magic", "vfx", "spell", "explosion", "法术", "魔法", "特效", "爆炸")):
        return "vfx_magic"
    if any(token in text for token in ("establishing", "aerial wide", "extreme wide", "大全景", "航拍", "建立镜头", "大场景")):
        return "large_establishing"
    if any(token in text for token in ("insert", "cutaway", "transition", "match cut", "插入", "空镜", "转场", "特写道具")):
        return "insert_or_transition"
    speaking = any(token in text for token in ("dialogue", "speaks", "says", "lip", "台词", "对白", "说道", "口型"))
    close = any(token in text for token in ("close-up", "closeup", "mcu", "cu", "近景", "特写"))
    if speaking and count >= 2:
        return "multi_character_dialogue"
    if speaking or close:
        return "dialogue_closeup"
    return "general_narrative"


def risk_weight(row: Mapping[str, Any]) -> int:
    text = flatten(row).lower()
    tokens = ("risk", "critical", "key", "identity", "lipsync", "seam", "contact", "高风险", "关键", "口型", "接缝", "同框")
    return sum(text.count(token) for token in tokens)


def route_backends(root: Path, episode: str) -> Dict[str, Tuple[str, ...]]:
    paths = (
        root / "出视频" / episode / "prompt" / "video_model_routes.json",
        root / "生产数据" / f"video_model_routes_{episode}.json",
    )
    for path in paths:
        if not path.is_file():
            continue
        data = load_json(path)
        routes = data.get("routes") if isinstance(data, Mapping) else data
        out: Dict[str, Tuple[str, ...]] = {}
        for row in routes or []:
            if not isinstance(row, Mapping):
                continue
            cid = str(row.get("clip_id") or row.get("clip") or row.get("id") or "")
            names = [str(row.get("primary_backend") or "")]
            names.extend(str(item) for item in (row.get("fallback_backends") or []) if str(item))
            names = list(dict.fromkeys(item for item in names if item))
            if cid and names:
                out[cid] = tuple(names)
        return out
    return {}


def build_plan(root: Path, episode: str, *, replicates: int = 2) -> Dict[str, Any]:
    episode = episode_label(episode)
    source = storyboard_path(root, episode)
    rows = clip_rows(load_json(source))
    by_class: Dict[str, List[Tuple[int, str, Mapping[str, Any]]]] = {}
    for index, row in enumerate(rows, 1):
        cid = clip_id(row, index)
        by_class.setdefault(classify_shot(row), []).append((risk_weight(row), cid, row))
    routes = route_backends(root, episode)
    selections: List[Dict[str, Any]] = []
    trials: List[Dict[str, Any]] = []
    for shot_class in sorted(by_class):
        _, cid, row = sorted(by_class[shot_class], key=lambda item: (-item[0], item[1]))[0]
        backends = routes.get(cid) or CLASS_BACKENDS[shot_class]
        selection = {
            "shot_class": shot_class,
            "clip_id": cid,
            "clip_contract_sha256": digest_value(row),
            "candidate_backends": list(backends),
        }
        selections.append(selection)
        for backend in backends:
            for replicate in range(1, max(1, replicates) + 1):
                trials.append({
                    "trial_id": f"{shot_class}::{cid}::{backend}::r{replicate}",
                    "shot_class": shot_class,
                    "clip_id": cid,
                    "backend": backend,
                    "replicate": replicate,
                    "clip_contract_sha256": selection["clip_contract_sha256"],
                    "required_evidence": (
                        "artifact_path+artifact_sha256",
                        "qc_receipt_path+qc_receipt_sha256+qc_verdict",
                        "inspection_receipt_path+inspection_receipt_sha256",
                        "cost+latency+accepted_seconds",
                    ),
                })
    core: Dict[str, Any] = {
        "kind": PLAN_KIND,
        "version": VERSION,
        "episode": episode,
        "storyboard": {"path": str(source), "sha256": sha256_file(source)},
        "selection_policy": "highest deterministic risk weight per observed shot class",
        "replicates_per_backend_class": max(1, replicates),
        "selections": selections,
        "trials": trials,
    }
    core["plan_digest"] = digest_value(core)
    return core


def _bound_file(root: Path, raw_path: Any, expected: Any, label: str) -> Tuple[Optional[Path], Optional[str]]:
    text = str(raw_path or "").strip()
    digest = str(expected or "").strip().lower()
    if not text or not re.fullmatch(r"[0-9a-f]{64}", digest):
        return None, f"{label}: missing path/sha256"
    path = Path(text)
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        return None, f"{label}: file missing: {path}"
    actual = sha256_file(path)
    if actual != digest:
        return None, f"{label}: sha256 mismatch"
    return path, None


def _receipt_artifact_sha(data: Mapping[str, Any]) -> str:
    direct = str(data.get("artifact_sha256") or data.get("master_sha256") or "").lower()
    if direct:
        return direct
    for key in ("artifact", "master", "output", "media"):
        nested = data.get(key)
        if isinstance(nested, Mapping) and nested.get("sha256"):
            return str(nested.get("sha256")).lower()
    return ""


def _read_receipt(path: Optional[Path], label: str) -> Tuple[Optional[Mapping[str, Any]], Optional[str]]:
    if path is None:
        return None, f"{label}: missing receipt"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, f"{label}: receipt is not valid JSON"
    if not isinstance(data, Mapping):
        return None, f"{label}: receipt root must be an object"
    return data, None


def validate_trial(root: Path, planned: Mapping[str, Any], result: Mapping[str, Any]) -> List[str]:
    issues: List[str] = []
    for key in ("trial_id", "shot_class", "clip_id", "backend", "clip_contract_sha256"):
        if str(result.get(key) or "") != str(planned.get(key) or ""):
            issues.append(f"{planned.get('trial_id')}: {key} binding mismatch")
    status = str(result.get("status") or "").lower()
    if status not in {"completed", "failed"}:
        issues.append(f"{planned.get('trial_id')}: status must be completed|failed")
    if status == "completed":
        bound: Dict[str, Optional[Path]] = {}
        for stem in ("artifact", "qc_receipt", "inspection_receipt"):
            path, issue = _bound_file(root, result.get(f"{stem}_path"), result.get(f"{stem}_sha256"), f"{planned.get('trial_id')} {stem}")
            bound[stem] = path
            if issue:
                issues.append(issue)
        artifact_sha = str(result.get("artifact_sha256") or "").lower()
        result_qc = str(result.get("qc_verdict") or "").lower()
        if result_qc not in {"pass", "fail"}:
            issues.append(f"{planned.get('trial_id')}: qc_verdict must be pass|fail")
        qc, issue = _read_receipt(bound.get("qc_receipt"), f"{planned.get('trial_id')} qc_receipt")
        if issue:
            issues.append(issue)
        elif qc is not None:
            if _receipt_artifact_sha(qc) != artifact_sha:
                issues.append(f"{planned.get('trial_id')}: QC receipt is not bound to artifact sha256")
            receipt_verdict = str(qc.get("verdict") or qc.get("status") or "").lower()
            if receipt_verdict != result_qc:
                issues.append(f"{planned.get('trial_id')}: QC receipt verdict mismatch")
        inspection, issue = _read_receipt(bound.get("inspection_receipt"), f"{planned.get('trial_id')} inspection_receipt")
        if issue:
            issues.append(issue)
        elif inspection is not None:
            if _receipt_artifact_sha(inspection) != artifact_sha:
                issues.append(f"{planned.get('trial_id')}: inspection receipt is not bound to artifact sha256")
            inspection_verdict = str(inspection.get("verdict") or inspection.get("status") or "").lower()
            if inspection_verdict not in {"pass", "accepted", "accept"}:
                issues.append(f"{planned.get('trial_id')}: inspection receipt does not accept current pixels/audio")
            if not str(inspection.get("reviewer_kind") or inspection.get("review_kind") or "").strip():
                issues.append(f"{planned.get('trial_id')}: inspection receipt lacks reviewer_kind")
    for key in ("cost", "latency_seconds", "accepted_seconds"):
        try:
            value = float(result.get(key, 0))
            if value < 0:
                raise ValueError
        except (TypeError, ValueError):
            issues.append(f"{planned.get('trial_id')}: {key} must be non-negative number")
    if str(result.get("attempt_kind") or "initial") not in {"initial", "repair"}:
        issues.append(f"{planned.get('trial_id')}: attempt_kind must be initial|repair")
    return issues


def _median(values: Iterable[float]) -> Optional[float]:
    rows = list(values)
    return round(float(statistics.median(rows)), 4) if rows else None


def summarize(root: Path, plan: Mapping[str, Any], results: Mapping[str, Any], min_samples: int = 2) -> Dict[str, Any]:
    expected_digest = str(plan.get("plan_digest") or "")
    if digest_value({key: value for key, value in plan.items() if key != "plan_digest"}) != expected_digest:
        raise ValueError("plan_digest does not match canonical plan content")
    issues: List[str] = []
    if str(results.get("kind") or "") != RESULTS_KIND:
        issues.append(f"results kind must be {RESULTS_KIND}")
    if str(results.get("plan_digest") or "") != expected_digest:
        issues.append("results plan_digest mismatch")
    planned = {str(row.get("trial_id")): row for row in plan.get("trials") or [] if isinstance(row, Mapping)}
    result_rows = [row for row in (results.get("trials") or []) if isinstance(row, Mapping)]
    seen: set[str] = set()
    valid: List[Mapping[str, Any]] = []
    for row in result_rows:
        trial_id = str(row.get("trial_id") or "")
        if trial_id in seen:
            issues.append(f"duplicate trial_id: {trial_id}")
            continue
        seen.add(trial_id)
        if trial_id not in planned:
            issues.append(f"unknown trial_id: {trial_id}")
            continue
        trial_issues = validate_trial(root, planned[trial_id], row)
        issues.extend(trial_issues)
        if not trial_issues:
            valid.append(row)

    groups: Dict[Tuple[str, str], List[Mapping[str, Any]]] = {}
    for row in valid:
        groups.setdefault((str(row["shot_class"]), str(row["backend"])), []).append(row)
    aggregates: List[Dict[str, Any]] = []
    for (shot_class, backend), rows in sorted(groups.items()):
        completed = [row for row in rows if str(row.get("status")) == "completed"]
        accepted = [row for row in completed if str(row.get("qc_verdict")).lower() == "pass" and float(row.get("accepted_seconds") or 0) > 0]
        initial = [row for row in completed if str(row.get("attempt_kind") or "initial") == "initial"]
        repairs = [row for row in completed if str(row.get("attempt_kind")) == "repair"]
        accepted_seconds = sum(float(row.get("accepted_seconds") or 0) for row in accepted)
        total_cost = sum(float(row.get("cost") or 0) for row in completed)
        aggregates.append({
            "shot_class": shot_class,
            "backend": backend,
            "sample_count": len(completed),
            "accepted_count": len(accepted),
            "one_pass_yield": round(sum(1 for row in initial if row in accepted) / len(initial), 4) if initial else None,
            "repair_yield": round(sum(1 for row in repairs if row in accepted) / len(repairs), 4) if repairs else None,
            "accepted_yield": round(len(accepted) / len(completed), 4) if completed else None,
            "cost_per_accepted_second": round(total_cost / accepted_seconds, 6) if accepted_seconds else None,
            "p50_latency_seconds": _median(float(row.get("latency_seconds") or 0) for row in completed),
            "eligible": len(completed) >= min_samples and bool(accepted),
        })
    recommendations: Dict[str, Dict[str, Any]] = {}
    for shot_class in sorted({row["shot_class"] for row in aggregates}):
        choices = [row for row in aggregates if row["shot_class"] == shot_class and row["eligible"]]
        if len(choices) < 2:
            continue
        choices.sort(key=lambda row: (
            -(row["accepted_yield"] or 0),
            -(row["one_pass_yield"] or 0),
            row["cost_per_accepted_second"] if row["cost_per_accepted_second"] is not None else float("inf"),
            row["p50_latency_seconds"] if row["p50_latency_seconds"] is not None else float("inf"),
            row["backend"],
        ))
        winner = choices[0]
        recommendations[shot_class] = {
            "primary_backend": winner["backend"],
            "basis": "accepted_yield > one_pass_yield > cost_per_accepted_second > p50_latency",
            "sample_count": winner["sample_count"],
        }
    return {
        "kind": SUMMARY_KIND,
        "version": VERSION,
        "episode": plan.get("episode"),
        "plan_digest": expected_digest,
        "status": "ready" if recommendations and not issues else "insufficient_evidence",
        "min_samples_per_backend_class": min_samples,
        "invalid_results": issues,
        "aggregates": aggregates,
        "recommendations": recommendations,
        "note": "No recommendation is emitted without two eligible backends in the same shot class; provider success alone is never acceptance.",
    }


def plan_path(root: Path, episode: str) -> Path:
    return root / "生产数据" / f"model_route_benchmark_plan_{episode_label(episode)}.json"


def summary_path(root: Path, episode: str) -> Path:
    return root / "生产数据" / f"model_route_benchmark_{episode_label(episode)}.json"


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="n2d shot-class backend benchmark")
    sub = ap.add_subparsers(dest="cmd", required=True)
    create = sub.add_parser("plan")
    create.add_argument("root")
    create.add_argument("episode")
    create.add_argument("--replicates", type=int, default=2)
    create.add_argument("--write", action="store_true")
    report = sub.add_parser("summarize")
    report.add_argument("root")
    report.add_argument("plan")
    report.add_argument("results")
    report.add_argument("--min-samples", type=int, default=2)
    report.add_argument("--write", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root).resolve()
    if ns.cmd == "plan":
        payload = build_plan(root, ns.episode, replicates=max(1, ns.replicates))
        if ns.write:
            atomic_json(plan_path(root, ns.episode), payload)
    else:
        plan = load_json(Path(ns.plan))
        results = load_json(Path(ns.results))
        payload = summarize(root, plan, results, min_samples=max(1, ns.min_samples))
        if ns.write:
            atomic_json(summary_path(root, str(plan.get("episode") or "")), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload.get("status") != "insufficient_evidence" else 3


if __name__ == "__main__":
    raise SystemExit(main())
