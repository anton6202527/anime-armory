#!/usr/bin/env python3
"""Batch stop-loss audit for n2d production metrics."""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


VERSION = 1
OUT_JSON = "stop_loss.json"
OUT_MD = "stop_loss.md"
DEFAULT_THRESHOLDS = {
    "max_face_drift_rate": 0.08,
    "max_redraw_rate": 0.35,
    "max_cost_per_finished_min": 1000.0,
    "max_qc_block_rate": 0.15,
    "max_seam_failure_rate": 0.05,
    "max_lipsync_failure_rate": 0.08,
}
FACE_MARKERS = ("脸", "face", "identity", "五官", "漂移", "drift")
SEAM_MARKERS = ("接缝", "seam", "首尾帧", "endframe")
LIPSYNC_MARKERS = ("口型", "唇形", "lipsync", "mouth")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def production_dir(root: Path) -> Path:
    return root / "生产数据"


def relpath(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_thresholds(root: Path) -> Dict[str, float]:
    out = dict(DEFAULT_THRESHOLDS)
    for path in (production_dir(root) / "production_slo.json", production_dir(root) / "stop_loss_thresholds.json"):
        data = load_json(path)
        if not isinstance(data, Mapping):
            continue
        node = data.get("stop_loss") if isinstance(data.get("stop_loss"), Mapping) else data
        for key, default in DEFAULT_THRESHOLDS.items():
            try:
                if key in node:
                    out[key] = float(node[key])
            except Exception:
                out[key] = default
    return out


def iter_jsonl(path: Path) -> Iterable[Mapping[str, Any]]:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except Exception:
            continue
        if isinstance(data, Mapping):
            yield data


def deep_numbers(value: Any, key_pattern: re.Pattern[str]) -> List[float]:
    out: List[float] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key_pattern.search(str(key)):
                try:
                    out.append(float(child))
                    continue
                except Exception:
                    pass
            out.extend(deep_numbers(child, key_pattern))
    elif isinstance(value, list):
        for child in value:
            out.extend(deep_numbers(child, key_pattern))
    return out


def finding_rows(data: Any) -> List[Mapping[str, Any]]:
    rows: List[Mapping[str, Any]] = []
    if not isinstance(data, Mapping):
        return rows
    for key in ("findings", "issues", "warnings", "blocks"):
        raw = data.get(key)
        if isinstance(raw, list):
            for row in raw:
                if isinstance(row, Mapping):
                    rows.append(row)
                elif isinstance(row, str):
                    rows.append({"message": row, "severity": "warn"})
    return rows


def text_of(row: Mapping[str, Any]) -> str:
    return " ".join(str(row.get(k) or "") for k in ("dimension", "category", "message", "reason", "loc", "code")).lower()


def is_block(row: Mapping[str, Any]) -> bool:
    return str(row.get("severity") or row.get("sev") or row.get("level") or "").strip().lower() in {"block", "blocked", "fail", "fatal", "error", "high"}


def has_redraw_signal(row: Mapping[str, Any]) -> bool:
    for key in ("redraw_reason", "rerun_reason", "retry_reason", "regeneration_reason"):
        if str(row.get(key) or "").strip():
            return True
    text = " ".join(str(row.get(k) or "") for k in ("event", "type", "reason", "message", "note", "action")).lower()
    return "redraw" in text or "rerun" in text or "重抽" in text or "重绘" in text


def _matches_episode(path: Path, episode: Optional[str]) -> bool:
    if not episode:
        return True
    return episode in path.name or episode in str(path)


def _event_matches_episode(row: Mapping[str, Any], episode: Optional[str]) -> bool:
    if not episode:
        return True
    blob = json.dumps(row, ensure_ascii=False)
    return episode in blob


def metrics(root: Path, episode: Optional[str] = None) -> Dict[str, Any]:
    prod = production_dir(root)
    events = [e for e in iter_jsonl(prod / "production_events.jsonl") if _event_matches_episode(e, episode)]
    generation = [e for e in events if str(e.get("event") or e.get("type") or "").lower() in {"image", "video", "compose", "generate", "generation"}]
    redraw = [e for e in events if has_redraw_signal(e)]
    dashboard = load_json(prod / "dashboard.json")
    cost_values = deep_numbers(dashboard, re.compile(r"cost_per_finished_min|cost_per_min|每分钟成本", re.I)) if isinstance(dashboard, Mapping) else []
    cost_per_min = max(cost_values) if cost_values else None

    finding_files = [
        path for path in (Path(p) for p in glob.glob(str(prod / "*findings*.json")) + glob.glob(str(prod / "consistency_ledger_*.json")))
        if _matches_episode(path, episode)
    ]
    rows: List[Mapping[str, Any]] = []
    for path in finding_files:
        rows.extend(finding_rows(load_json(path)))
    block_rows = [r for r in rows if is_block(r)]
    face_blocks = [r for r in block_rows if any(m in text_of(r) for m in FACE_MARKERS)]
    seam_blocks = [r for r in block_rows if any(m in text_of(r) for m in SEAM_MARKERS)]
    lipsync_blocks = [r for r in block_rows if any(m in text_of(r) for m in LIPSYNC_MARKERS)]
    denom = max(len(rows), len(generation), 1)
    return {
        "events": len(events),
        "generation_events": len(generation),
        "redraw_events": len(redraw),
        "redraw_rate": round(len(redraw) / max(len(generation), 1), 4) if generation else 0.0,
        "finding_rows": len(rows),
        "qc_blocks": len(block_rows),
        "qc_block_rate": round(len(block_rows) / denom, 4),
        "face_drift_rate": round(len(face_blocks) / denom, 4),
        "seam_failure_rate": round(len(seam_blocks) / denom, 4),
        "lipsync_failure_rate": round(len(lipsync_blocks) / denom, 4),
        "cost_per_finished_min": cost_per_min,
        "evidence_files": len(finding_files) + (1 if (prod / "production_events.jsonl").is_file() else 0) + (1 if (prod / "dashboard.json").is_file() else 0),
    }


def build_report(root: Path, episode: Optional[str] = None) -> Dict[str, Any]:
    root = root.resolve()
    thresholds = load_thresholds(root)
    m = metrics(root, episode=episode)
    violations: List[Dict[str, Any]] = []

    checks = [
        ("redraw_rate", "max_redraw_rate"),
        ("qc_block_rate", "max_qc_block_rate"),
        ("face_drift_rate", "max_face_drift_rate"),
        ("seam_failure_rate", "max_seam_failure_rate"),
        ("lipsync_failure_rate", "max_lipsync_failure_rate"),
    ]
    for metric, threshold_key in checks:
        value = float(m.get(metric) or 0.0)
        threshold = float(thresholds[threshold_key])
        if value > threshold:
            violations.append({"level": "critical", "metric": metric, "value": value, "threshold": threshold, "action": "stop_batch_and_return_to_contract_layer"})
    cost = m.get("cost_per_finished_min")
    if cost is not None and float(cost) > float(thresholds["max_cost_per_finished_min"]):
        violations.append({"level": "critical", "metric": "cost_per_finished_min", "value": float(cost), "threshold": thresholds["max_cost_per_finished_min"], "action": "stop_batch_and_review_roi_or_backend"})
    if m.get("evidence_files", 0) == 0:
        violations.append({"level": "info", "metric": "evidence", "value": 0, "threshold": "n/a", "action": "no_batch_metrics_yet"})

    return {
        "kind": "n2d_stop_loss",
        "version": VERSION,
        "root": str(root),
        "episode": episode or "",
        "generated_at": now_iso(),
        "status": "critical" if any(v["level"] == "critical" for v in violations) else "pass",
        "thresholds": thresholds,
        "metrics": m,
        "violations": violations,
    }


def render_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# n2d Stop Loss",
        "",
        f"- 状态：{payload.get('status')}",
        f"- metrics：{payload.get('metrics')}",
        "",
        "## Violations",
        "",
    ]
    violations = payload.get("violations") or []
    lines.extend([f"- {v.get('level')} {v.get('metric')}: {v.get('value')} > {v.get('threshold')} ({v.get('action')})" for v in violations] or ["- 无"])
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, payload: Mapping[str, Any]) -> Dict[str, str]:
    out = production_dir(root)
    out.mkdir(parents=True, exist_ok=True)
    episode = str(payload.get("episode") or "").strip()
    stem = f"stop_loss_{episode}" if episode else "stop_loss"
    json_path = out / f"{stem}.json"
    md_path = out / f"{stem}.md"
    tmp = json_path.with_name(f"{json_path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, json_path)
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {"json": relpath(root, json_path), "markdown": relpath(root, md_path)}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="check n2d batch stop-loss thresholds")
    ap.add_argument("root")
    ap.add_argument("--episode", default="", help="scope metrics to one episode for release verdict checks")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root)
    payload = build_report(root, episode=ns.episode or None)
    if ns.write:
        payload["outputs"] = write_outputs(root, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_markdown(payload))
    return 3 if payload.get("status") == "critical" else 0


if __name__ == "__main__":
    raise SystemExit(main())
