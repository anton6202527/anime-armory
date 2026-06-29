#!/usr/bin/env python3
"""Production governance checks for n2d-batch queues."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
QUEUE_PATH = SCRIPT_DIR / "queue.py"
spec = importlib.util.spec_from_file_location("n2d_batch_queue_for_governance", QUEUE_PATH)
queue_mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(queue_mod)


SLO_FILE = "production_slo.json"
REPORT_JSON = "batch_governance.json"
REPORT_MD = "batch_governance.md"
DEAD_JSON = queue_mod.DEAD_LETTER_JSON
DEAD_MD = "dead_letter_queue.md"
KIND = "n2d_batch_governance"


DEFAULT_SLO = {
    "kind": "n2d_batch_slo",
    "version": 1,
    "queue": {
        "max_dead_letters": 0,
        "max_retry_rate": 0.35,
        "max_running_age_sec": 7200,
    },
    "stages": {
        "image": {"max_duration_sec": 3600, "max_attempts": 3},
        "video": {"max_duration_sec": 7200, "max_attempts": 3},
        "compose": {"max_duration_sec": 1800, "max_attempts": 2},
        "review": {"max_duration_sec": 1800, "max_attempts": 2},
    },
}


def production_dir(root: str) -> Path:
    return Path(queue_mod.production_dir(root))


def slo_path(root: str) -> Path:
    return production_dir(root) / SLO_FILE


def load_slo(root: str) -> Dict[str, Any]:
    path = slo_path(root)
    if not path.is_file():
        return json.loads(json.dumps(DEFAULT_SLO, ensure_ascii=False))
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be an object")
    out = json.loads(json.dumps(DEFAULT_SLO, ensure_ascii=False))
    out.update(data)
    if isinstance(data.get("queue"), dict):
        out["queue"].update(data["queue"])
    if isinstance(data.get("stages"), dict):
        out["stages"].update(data["stages"])
    return out


def write_slo(root: str, *, force: bool = False) -> Path:
    path = slo_path(root)
    if path.exists() and not force:
        raise RuntimeError(f"{path} already exists; use --force")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(DEFAULT_SLO, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def dead_letters(queue: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for task in queue.get("tasks", []):
        if task.get("dead_letter") is True or task.get("status") == "failed":
            out.append(task)
    return out


def evaluate(root: str) -> Dict[str, Any]:
    q = queue_mod.load_queue(root)
    slo = load_slo(root)
    tasks = q.get("tasks", [])
    total = len(tasks)
    retried = sum(1 for task in tasks if int(task.get("attempts") or 0) > 1)
    retry_rate = (retried / total) if total else 0.0
    dead = dead_letters(q)
    violations: List[Dict[str, Any]] = []
    q_slo = slo.get("queue", {})
    if len(dead) > int(q_slo.get("max_dead_letters", 0)):
        violations.append({"level": "critical", "kind": "dead_letters", "value": len(dead), "threshold": q_slo.get("max_dead_letters")})
    if retry_rate > float(q_slo.get("max_retry_rate", 1.0)):
        violations.append({"level": "warn", "kind": "retry_rate", "value": round(retry_rate, 4), "threshold": q_slo.get("max_retry_rate")})
    stage_slo = slo.get("stages") if isinstance(slo.get("stages"), dict) else {}
    for task in tasks:
        stage = str(task.get("stage_key") or "")
        spec = stage_slo.get(stage) if isinstance(stage_slo.get(stage), dict) else {}
        attempts = int(task.get("attempts") or 0)
        if spec.get("max_attempts") is not None and attempts > int(spec.get("max_attempts")):
            violations.append({"level": "warn", "kind": "attempts", "task_id": task.get("id"), "value": attempts, "threshold": spec.get("max_attempts")})
        runner = task.get("last_runner") if isinstance(task.get("last_runner"), dict) else {}
        duration = runner.get("duration_sec")
        if duration is not None and spec.get("max_duration_sec") is not None and float(duration) > float(spec.get("max_duration_sec")):
            violations.append({"level": "warn", "kind": "stage_duration", "task_id": task.get("id"), "value": duration, "threshold": spec.get("max_duration_sec")})
    payload = {
        "kind": KIND,
        "version": 1,
        "root": root,
        "status": "critical" if any(v["level"] == "critical" for v in violations) else ("warn" if violations else "pass"),
        "summary": {
            "total": total,
            "retried": retried,
            "retry_rate": round(retry_rate, 4),
            "dead_letters": len(dead),
        },
        "violations": violations,
        "dead_letters": [
            {
                "id": task.get("id"),
                "episode": task.get("episode"),
                "stage_key": task.get("stage_key"),
                "attempts": task.get("attempts"),
                "error_class": task.get("last_error_class") or (task.get("last_runner") or {}).get("error_class"),
                "note": task.get("last_note") or (task.get("last_runner") or {}).get("note"),
                "idempotency_key": task.get("idempotency_key"),
            }
            for task in dead
        ],
    }
    return payload


def render_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    lines = [
        "# n2d-batch 生产治理",
        "",
        f"- 状态：{payload.get('status')}",
        f"- 任务数：{summary.get('total', 0)}",
        f"- 重试率：{summary.get('retry_rate', 0)}",
        f"- 死信：{summary.get('dead_letters', 0)}",
        "",
        "## 违规",
        "",
    ]
    violations = payload.get("violations") or []
    lines.extend([f"- {v.get('level')} {v.get('kind')}: {v}" for v in violations] or ["- 无"])
    lines.extend(["", "## Dead Letter", ""])
    dead = payload.get("dead_letters") or []
    lines.extend([f"- {d.get('id')} {d.get('episode')} {d.get('stage_key')} {d.get('error_class')}: {d.get('note')}" for d in dead] or ["- 无"])
    lines.append("")
    return "\n".join(lines)


def write_report(root: str, payload: Dict[str, Any]) -> None:
    pdir = production_dir(root)
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / REPORT_JSON).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (pdir / REPORT_MD).write_text(render_markdown(payload), encoding="utf-8")
    (pdir / DEAD_JSON).write_text(json.dumps({
        "kind": "n2d_dead_letter_queue",
        "version": 1,
        "tasks": payload.get("dead_letters") or [],
    }, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (pdir / DEAD_MD).write_text(render_markdown({**payload, "violations": []}), encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="n2d-batch production governance")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init-slo")
    p.add_argument("root")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("check")
    p.add_argument("root")
    p.add_argument("--write", action="store_true")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("dead-letter")
    p.add_argument("root")
    p.add_argument("--write", action="store_true")
    p.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    if ns.cmd == "init-slo":
        path = write_slo(ns.root, force=ns.force)
        print(f"wrote {path}")
        return 0
    payload = evaluate(ns.root)
    if ns.write:
        write_report(ns.root, payload)
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_markdown(payload))
    if ns.cmd == "dead-letter":
        return 1 if payload.get("dead_letters") else 0
    return 1 if payload.get("status") == "critical" else 0


if __name__ == "__main__":
    raise SystemExit(main())
