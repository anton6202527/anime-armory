#!/usr/bin/env python3
"""Structured boundary review signoff for n2d-script stage 1.

`boundary_audit.py --strict` finds risky raw episode boundaries. This script
turns those risks into a machine-checkable signoff:

  python3 boundary_review.py draft <作品根> [start-end] --write
  python3 boundary_review.py check <作品根> [start-end] --json

The review binds each signed decision to the current `raw.txt` sha256. If the
raw fragment changes, the signoff becomes stale and run.py will block again.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import boundary_audit as BA  # noqa: E402
from n2d_settings import get_setting  # noqa: E402

KIND = "n2d_boundary_review"
VERSION = 1
REVIEW_REL = os.path.join("脚本", "boundary_review.json")
VALID_DECISIONS = {
    "keep",
    "merge_prev",
    "merge_next",
    "move_boundary",
    "split",
    "rewrite",
    "accept_risk",
    "other",
}


def review_path(root: str) -> Path:
    return Path(root) / REVIEW_REL


def normalize_ep(value: Any) -> Optional[int]:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group(0)) if m else None


def range_filter(rows: List[Dict[str, Any]], range_arg: Optional[str]) -> List[Dict[str, Any]]:
    if not range_arg:
        return rows
    m = re.match(r"(\d+)-(\d+)$", range_arg)
    if not m:
        raise ValueError("范围格式应为 start-end，例如 2-10")
    a, b = map(int, m.groups())
    return [r for r in rows if a <= int(r["ep"]) <= b]


def current_audit(root: str, range_arg: Optional[str] = None) -> Dict[str, Any]:
    genre = get_setting(root, "题材", "")
    monet = get_setting(root, "变现模式", "免费") or "免费"
    strong_re, conflict_re, payoff_re = BA.build_res(genre)
    rows = BA.load_rows(root, strong_re, conflict_re, payoff_re)
    rows = range_filter(rows, range_arg)
    per_ep, has_risk = BA.enrich_episode_rows(rows)
    arc = BA.series_arc(rows, monet)
    return {
        "genre": genre,
        "monetization": monet,
        "series_arc": arc,
        "episodes": per_ep,
        "risk_episodes": [r for r in per_ep if r.get("risk")],
        "has_risk": has_risk,
    }


def load_review(root: str) -> Dict[str, Any]:
    path = review_path(root)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, dict) else {}


def review_entries(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    entries = data.get("reviews")
    if isinstance(entries, list):
        return [e for e in entries if isinstance(e, dict)]
    # Compatibility for manually authored files.
    entries = data.get("episodes")
    if isinstance(entries, list):
        return [e for e in entries if isinstance(e, dict)]
    return []


def entry_is_signed(entry: Dict[str, Any]) -> bool:
    decision = str(entry.get("decision") or "").strip()
    status = str(entry.get("status") or "").strip().lower()
    notes = str(entry.get("notes") or entry.get("boundary_decision") or "").strip()
    if decision not in VALID_DECISIONS:
        return False
    if status in {"pending", "todo", "draft"}:
        return False
    # A decision without a human/agent note is not auditable enough to unlock
    # downstream generation. Keep the note short, but make the cut explicit.
    return bool(notes)


def validate(root: str, range_arg: Optional[str] = None) -> Dict[str, Any]:
    audit = current_audit(root, range_arg)
    risks = audit["risk_episodes"]
    findings: List[Dict[str, Any]] = []
    path = review_path(root)
    data = load_review(root)
    entries = review_entries(data)
    by_ep = {normalize_ep(e.get("episode") or e.get("ep")): e for e in entries}

    if not risks:
        return {
            "ok": True,
            "review_path": str(path),
            "required": [],
            "findings": [],
            "message": "boundary_audit 当前无高风险边界，不需要签收。",
        }
    if not data:
        findings.append({
            "severity": "block",
            "code": "missing_boundary_review",
            "message": f"缺 {REVIEW_REL}；先运行 boundary_review.py draft <作品根> --write 并填写 decision/notes。",
        })
    elif data.get("kind") not in {KIND, None}:
        findings.append({
            "severity": "block",
            "code": "bad_kind",
            "message": f"{REVIEW_REL} kind={data.get('kind')}，期望 {KIND}。",
        })

    required = []
    for row in risks:
        ep_num = int(row["ep"])
        ep_label = f"第{ep_num}集"
        required.append({
            "episode": ep_label,
            "raw_sha256": row["raw_sha256"],
            "flags": row["flags"],
            "advice": row["advice"],
        })
        entry = by_ep.get(ep_num)
        if not entry:
            findings.append({
                "severity": "block",
                "code": "missing_episode_review",
                "episode": ep_label,
                "message": f"{ep_label} 有边界风险但未在 {REVIEW_REL} 签收。",
            })
            continue
        if str(entry.get("raw_sha256") or "") != row["raw_sha256"]:
            findings.append({
                "severity": "block",
                "code": "stale_episode_review",
                "episode": ep_label,
                "message": f"{ep_label} raw.txt 指纹已变化，旧签收失效；重跑 draft/check 后重新确认。",
            })
            continue
        if not entry_is_signed(entry):
            findings.append({
                "severity": "block",
                "code": "unsigned_episode_review",
                "episode": ep_label,
                "message": (
                    f"{ep_label} 签收未完成；decision 必须是 {sorted(VALID_DECISIONS)} 之一，"
                    "且 notes/boundary_decision 需写明边界处理。"
                ),
            })

    return {
        "ok": not any(f["severity"] == "block" for f in findings),
        "review_path": str(path),
        "required": required,
        "findings": findings,
        "message": "boundary_review 通过。" if not findings else "boundary_review 未通过。",
    }


def draft(root: str, range_arg: Optional[str] = None, write: bool = False) -> Dict[str, Any]:
    audit = current_audit(root, range_arg)
    path = review_path(root)
    old = load_review(root)
    old_by_ep = {normalize_ep(e.get("episode") or e.get("ep")): e for e in review_entries(old)}
    reviews: List[Dict[str, Any]] = []
    for row in audit["risk_episodes"]:
        ep_num = int(row["ep"])
        ep_label = f"第{ep_num}集"
        old_entry = old_by_ep.get(ep_num) or {}
        if old_entry.get("raw_sha256") == row["raw_sha256"] and entry_is_signed(old_entry):
            reviews.append(old_entry)
            continue
        reviews.append({
            "episode": ep_label,
            "raw_rel": row.get("raw_rel"),
            "raw_sha256": row["raw_sha256"],
            "risk_flags": row["flags"],
            "audit_advice": row["advice"],
            "decision": "pending",
            "notes": "",
            "reviewed_by": "",
            "reviewed_at": "",
        })
    data = {
        "kind": KIND,
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": range_arg or "all",
        "source": "boundary_audit.py",
        "reviews": reviews,
    }
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    return data


def print_human(result: Dict[str, Any]) -> None:
    print(f"boundary_review: {'PASS' if result.get('ok') else 'BLOCK'}")
    print(result.get("message") or "")
    if result.get("review_path"):
        print(f"review_path: {result['review_path']}")
    for f in result.get("findings") or []:
        print(f"- {f.get('severity', 'info')}: {f.get('message')}")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d boundary review structured signoff")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("draft", "check"):
        sp = sub.add_parser(name)
        sp.add_argument("root")
        sp.add_argument("range", nargs="?")
        sp.add_argument("--json", action="store_true")
        if name == "draft":
            sp.add_argument("--write", action="store_true")
    ns = ap.parse_args(argv)
    try:
        if ns.cmd == "draft":
            data = draft(ns.root.rstrip("/"), ns.range, write=ns.write)
            if ns.json:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                print(f"drafted {len(data['reviews'])} risk episode review(s)")
                if ns.write:
                    print(f"wrote {review_path(ns.root)}")
            return 0
        result = validate(ns.root.rstrip("/"), ns.range)
        if ns.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_human(result)
        return 0 if result["ok"] else 1
    except Exception as exc:
        payload = {"ok": False, "findings": [{"severity": "block", "code": "exception", "message": str(exc)}]}
        if getattr(ns, "json", False):
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"boundary_review error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
