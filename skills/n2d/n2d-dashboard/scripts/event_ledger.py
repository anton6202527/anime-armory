#!/usr/bin/env python3
"""Audit and replay the n2d production event ledger.

`production_events.jsonl` is the production truth source.  This helper keeps the
ledger inspectable without changing historical event lines: it validates event
shape, builds a deterministic hash chain, and can replay dashboard aggregation
from events only.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
DASHBOARD_PATH = SCRIPT_DIR / "dashboard.py"
spec = importlib.util.spec_from_file_location("n2d_dashboard_for_event_ledger", DASHBOARD_PATH)
dashboard = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(dashboard)


AUDIT_JSON = "production_events_audit.json"
AUDIT_MD = "production_events_audit.md"
CHAIN_JSONL = "production_events_chain.jsonl"
REPLAY_JSON = "dashboard_replay.json"
ANCHOR_JSON = "production_events_chain_anchor.json"

# dashboard.aggregate_events 每次注入 generated_at（计算时刻），把它计进 hash 会让「事件可复现 dashboard」
# 校验恒 False。复现比对前剥掉这类易变字段，hash 才反映**内容**而非生成时刻。
_VOLATILE_DASHBOARD_KEYS = ("generated_at",)


def _strip_volatile(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip_volatile(v) for k, v in value.items() if k not in _VOLATILE_DASHBOARD_KEYS}
    if isinstance(value, list):
        return [_strip_volatile(v) for v in value]
    return value


def _load_anchor(path: Path) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None

REQUIRED_FIELDS = ("kind", "version", "ts", "episode", "stage", "event", "source")
TRACE_IDENTITY_EVENTS = {"generation", "redraw", "cost", "duration", "qa_gate", "release", "revenue"}


def production_dir(root: str) -> Path:
    return Path(dashboard.production_dir(root))


def events_path(root: str) -> Path:
    return Path(dashboard.events_path(root))


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def load_event_lines(root: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    path = events_path(root)
    events: List[Dict[str, Any]] = []
    line_errors: List[Dict[str, Any]] = []
    if not path.is_file():
        return events, [{"line": 0, "error": f"missing ledger: {path}"}]
    with path.open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                line_errors.append({"line": lineno, "error": f"invalid JSONL: {exc}"})
                continue
            if not isinstance(item, dict):
                line_errors.append({"line": lineno, "error": "event line is not a JSON object"})
                continue
            item["_ledger_line"] = lineno
            events.append(item)
    return events, line_errors


def event_id(event: Dict[str, Any], previous_hash: str = "") -> str:
    body = {k: v for k, v in event.items() if not str(k).startswith("_") and k not in {"event_id", "ledger"}}
    return sha256_text(previous_hash + "\n" + canonical_json(body))


def validate_event(event: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    for field in REQUIRED_FIELDS:
        if event.get(field) in (None, ""):
            errors.append(f"missing required field `{field}`")
    if event.get("kind") not in (dashboard.EVENT_KIND, "n2d_production_event"):
        errors.append(f"kind must be {dashboard.EVENT_KIND}")
    if not isinstance(event.get("version"), int):
        errors.append("version must be an integer")
    cost = event.get("cost")
    if isinstance(cost, dict):
        if cost.get("amount") not in (None, ""):
            try:
                float(cost.get("amount"))
            except (TypeError, ValueError):
                errors.append("cost.amount must be numeric")
        if not cost.get("provider"):
            warnings.append("cost.provider missing; provider cost rollup will be `unknown`")
    generation = event.get("generation")
    if event.get("event") in {"generation", "redraw"} and not isinstance(generation, dict):
        warnings.append("generation/redraw event lacks generation payload")
    meta = event.get("meta") if isinstance(event.get("meta"), dict) else {}
    trace = event.get("trace") if isinstance(event.get("trace"), dict) else {}
    if not (trace.get("trace_id") or meta.get("trace_id") or meta.get("task_id")):
        warnings.append("no trace_id/task_id; cross-stage production tracing is degraded")
    if event.get("event") in TRACE_IDENTITY_EVENTS:
        if not (trace.get("span_id") or meta.get("span_id") or meta.get("task_id")):
            warnings.append("trace span_id/task_id missing on production event")
        if not (trace.get("idempotency_key") or meta.get("idempotency_key")):
            warnings.append("idempotency_key missing on production event")
    return errors, warnings


def trace_audit_row(event: Dict[str, Any]) -> Dict[str, Any]:
    meta = event.get("meta") if isinstance(event.get("meta"), dict) else {}
    trace = event.get("trace") if isinstance(event.get("trace"), dict) else {}
    trace_id = trace.get("trace_id") or meta.get("trace_id") or meta.get("task_id") or ""
    span_id = trace.get("span_id") or meta.get("span_id") or meta.get("task_id") or ""
    idem = trace.get("idempotency_key") or meta.get("idempotency_key") or ""
    missing = []
    if not trace_id:
        missing.append("trace_id")
    if event.get("event") in TRACE_IDENTITY_EVENTS and not span_id:
        missing.append("span_id")
    if event.get("event") in TRACE_IDENTITY_EVENTS and not idem:
        missing.append("idempotency_key")
    return {
        "line": event.get("_ledger_line"),
        "episode": event.get("episode"),
        "stage": event.get("stage"),
        "event": event.get("event"),
        "trace_id": trace_id,
        "span_id": span_id,
        "idempotency_key": idem,
        "missing": missing,
    }


def trace_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(rows)
    missing_trace = sum(1 for row in rows if "trace_id" in row.get("missing", []))
    missing_span = sum(1 for row in rows if "span_id" in row.get("missing", []))
    missing_idem = sum(1 for row in rows if "idempotency_key" in row.get("missing", []))
    by_stage: Dict[str, Dict[str, int]] = {}
    for row in rows:
        stage = str(row.get("stage") or "unknown")
        bucket = by_stage.setdefault(stage, {"total": 0, "missing_trace_id": 0})
        bucket["total"] += 1
        if "trace_id" in row.get("missing", []):
            bucket["missing_trace_id"] += 1
    return {
        "total": total,
        "missing_trace_id": missing_trace,
        "missing_span_id": missing_span,
        "missing_idempotency_key": missing_idem,
        "coverage": 1.0 if not total else round((total - missing_trace) / total, 4),
        "by_stage": by_stage,
    }


def build_hash_chain(events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    prev = "0" * 64
    for event in events:
        eid = event_id(event, prev)
        record = {
            "line": event.get("_ledger_line"),
            "event_id": eid[:16],
            "hash": eid,
            "prev_hash": prev,
            "episode": event.get("episode"),
            "stage": event.get("stage"),
            "event": event.get("event"),
            "ts": event.get("ts"),
        }
        out.append(record)
        prev = eid
    return out


def audit(root: str, *, write: bool = False, strict_trace: bool = False) -> Dict[str, Any]:
    events, line_errors = load_event_lines(root)
    event_errors: List[Dict[str, Any]] = []
    event_warnings: List[Dict[str, Any]] = []
    trace_rows: List[Dict[str, Any]] = []
    trace_errors: List[Dict[str, Any]] = []
    for event in events:
        errors, warnings = validate_event(event)
        trace_row = trace_audit_row(event)
        trace_rows.append(trace_row)
        if strict_trace and "trace_id" in trace_row.get("missing", []):
            trace_errors.append({
                "line": event.get("_ledger_line"),
                "errors": ["missing trace_id under --strict-trace"],
            })
        if errors:
            event_errors.append({"line": event.get("_ledger_line"), "errors": errors})
        if warnings:
            event_warnings.append({"line": event.get("_ledger_line"), "warnings": warnings})
    chain = build_hash_chain(events)
    chain_head = chain[-1]["hash"] if chain else ""
    # 防篡改 checkpoint 锚：上次审计记下「前 N 条事件的链头 = H」。本次重算链，前 N 条链头必须仍是 H
    # （append-only）。改写/删除历史事件行会让前缀链头变 → tamper 报警，不再「改了也无人察觉」。
    # 诚实边界：锚与事件同盘，能写盘的攻击者可一并改锚；本机制拦的是非恶意/审计间的历史改写，
    # 加密级防篡改需把锚放到外部 append-only 存储。
    anchor_path = production_dir(root) / ANCHOR_JSON
    anchor = _load_anchor(anchor_path)
    chain_tamper: Optional[Dict[str, Any]] = None
    if isinstance(anchor, dict) and isinstance(anchor.get("event_count"), int) and anchor["event_count"] >= 1:
        n = anchor["event_count"]
        if n > len(chain):
            chain_tamper = {"anchor_event_count": n, "current_event_count": len(chain),
                            "message": f"事件数从 {n} 缩到 {len(chain)}：历史事件行被删除"}
        elif chain[n - 1]["hash"] != anchor.get("head_hash"):
            chain_tamper = {"anchor_event_count": n, "anchor_head": anchor.get("head_hash"),
                            "recomputed_prefix_head": chain[n - 1]["hash"],
                            "message": f"前 {n} 条事件的链头与上次锚点不符：历史事件被改写（append-only 被破坏）"}
    payload = {
        "kind": "n2d_production_event_ledger_audit",
        "version": 1,
        "root": root,
        "ledger": str(events_path(root)),
        "event_count": len(events),
        "line_errors": line_errors,
        "event_errors": event_errors,
        "trace_errors": trace_errors,
        "event_warnings": event_warnings,
        "trace_summary": trace_summary(trace_rows),
        "hash_chain_head": chain_head,
        "chain_tamper": chain_tamper,
        "chain_anchor_event_count": anchor.get("event_count") if isinstance(anchor, dict) else None,
        "strict_trace": strict_trace,
        "status": "fail" if (line_errors or event_errors or trace_errors or chain_tamper) else ("warn" if event_warnings else "pass"),
        "chain_path": str(production_dir(root) / CHAIN_JSONL),
    }
    if write:
        pdir = production_dir(root)
        atomic_write(pdir / AUDIT_JSON, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        atomic_write(pdir / CHAIN_JSONL, "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in chain))
        atomic_write(pdir / AUDIT_MD, render_audit_markdown(payload))
        # 仅在未检出篡改时推进锚（检出篡改时保留旧锚，留待人工核查后再决定是否重锚）。
        if chain_tamper is None and chain:
            atomic_write(anchor_path, json.dumps(
                {"kind": "n2d_production_event_chain_anchor", "event_count": len(chain), "head_hash": chain_head},
                ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return payload


def replay(root: str, *, write: bool = False) -> Dict[str, Any]:
    events, line_errors = load_event_lines(root)
    if line_errors:
        return {
            "kind": "n2d_production_event_replay",
            "version": 1,
            "root": root,
            "status": "fail",
            "line_errors": line_errors,
        }
    clean_events = [{k: v for k, v in event.items() if not str(k).startswith("_")} for event in events]
    data = dashboard.aggregate_events(root, clean_events)
    payload = {
        "kind": "n2d_production_event_replay",
        "version": 1,
        "root": root,
        "status": "pass",
        "event_count": len(clean_events),
        "dashboard": data,
    }
    current_path = production_dir(root) / dashboard.DASHBOARD_JSON
    if current_path.is_file():
        try:
            current = json.loads(current_path.read_text(encoding="utf-8"))
            # 剥易变 generated_at 后比对内容（否则计算时刻不同→恒 False，校验形同虚设）。
            payload["current_dashboard_head"] = sha256_text(canonical_json(_strip_volatile(current)))
            payload["replay_dashboard_head"] = sha256_text(canonical_json(_strip_volatile(data)))
            payload["matches_current_dashboard"] = payload["current_dashboard_head"] == payload["replay_dashboard_head"]
        except Exception as exc:
            payload["current_dashboard_error"] = str(exc)
    if write:
        atomic_write(production_dir(root) / REPLAY_JSON, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return payload


def render_audit_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# production_events 账本审计",
        "",
        f"- 状态：{payload.get('status')}",
        f"- 事件数：{payload.get('event_count')}",
        f"- trace coverage：{(payload.get('trace_summary') or {}).get('coverage', '—')}",
        f"- hash head：`{payload.get('hash_chain_head') or '—'}`",
        "",
        "## 问题",
        "",
    ]
    issues = payload.get("line_errors", []) + payload.get("event_errors", []) + payload.get("trace_errors", [])
    if not issues:
        lines.append("- 无阻断问题")
    else:
        for item in issues[:40]:
            lines.append(f"- line {item.get('line')}: {item.get('error') or '; '.join(item.get('errors', []))}")
    warnings = payload.get("event_warnings", [])
    lines.extend(["", "## 提醒", ""])
    if not warnings:
        lines.append("- 无提醒")
    else:
        for item in warnings[:40]:
            lines.append(f"- line {item.get('line')}: {'; '.join(item.get('warnings', []))}")
    lines.append("")
    return "\n".join(lines)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="audit/replay n2d production_events.jsonl")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("audit", "doctor"):
        p = sub.add_parser(name)
        p.add_argument("root")
        p.add_argument("--write", action="store_true")
        p.add_argument("--json", action="store_true")
        p.add_argument("--strict-trace", action="store_true", help="treat missing trace_id as audit failure")
    p = sub.add_parser("replay")
    p.add_argument("root")
    p.add_argument("--write", action="store_true")
    p.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    ns = parser().parse_args(argv)
    if ns.cmd in {"audit", "doctor"}:
        payload = audit(ns.root, write=ns.write or ns.cmd == "doctor", strict_trace=ns.strict_trace)
    elif ns.cmd == "replay":
        payload = replay(ns.root, write=ns.write)
    else:  # pragma: no cover
        raise AssertionError(ns.cmd)
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_audit_markdown(payload) if payload.get("kind", "").endswith("audit") else json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload.get("status") == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
