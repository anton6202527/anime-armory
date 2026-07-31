#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aggregate editorial/release signals into a review board packet.

The board is advisory and auditable: gates still live in qa_gate/export/release
scripts. This packet gives a human editor one stable place to arbitrate review,
score, revision conflicts, and reader-feedback signals before release.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import sys
from datetime import datetime
from typing import Any

from report_snapshot import snapshot_chapters, validate_snapshot

try:
    from provenance import append_event
except Exception:  # pragma: no cover - provenance is additive
    append_event = None


BOARD_KIND = "novel_review_board"
BLOCKING_SCORE_VERDICTS = {"大改", "弃稿重立"}


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def evidence_record(root: str, relpath: str) -> dict[str, Any]:
    path = os.path.join(root, relpath)
    if not os.path.exists(path):
        return {"path": relpath, "exists": False}
    return {
        "path": relpath,
        "exists": True,
        "sha256": sha256_file(path),
        "size_bytes": os.path.getsize(path),
    }


def review_signal(root: str) -> dict[str, Any]:
    relpath = "审稿/review_report.json"
    payload = load_json(os.path.join(root, relpath), {}) or {}
    findings = payload.get("findings") if isinstance(payload, dict) else []
    findings = findings if isinstance(findings, list) else []
    blocking = [item for item in findings if isinstance(item, dict) and (item.get("blocking") or item.get("severity") == "blocking")]
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    blocking_count = int(summary.get("blocking_count") or len(blocking))
    fresh, fresh_message = validate_snapshot(root, payload.get("source_snapshot") if isinstance(payload, dict) else None)
    return {
        "path": relpath,
        "exists": os.path.exists(os.path.join(root, relpath)),
        "blocking_count": blocking_count,
        "finding_count": len(findings),
        "blocking_ids": [item.get("id") or item.get("dimension") or item.get("problem") for item in blocking[:20]],
        "source_snapshot_fresh": fresh,
        "source_snapshot_message": fresh_message,
        "source_aggregate_hash": (payload.get("source_snapshot") or {}).get("aggregate_hash") if isinstance(payload, dict) else "",
    }


def score_signal(root: str) -> dict[str, Any]:
    relpath = "评分/score_report.json"
    payload = load_json(os.path.join(root, relpath), {}) or {}
    decision = (payload.get("production_decision") or {}).get("decision") if isinstance(payload, dict) else ""
    verdict = payload.get("verdict") if isinstance(payload, dict) else ""
    fresh, fresh_message = validate_snapshot(root, payload.get("source_snapshot") if isinstance(payload, dict) else None)
    return {
        "path": relpath,
        "exists": os.path.exists(os.path.join(root, relpath)),
        "total_score": payload.get("total_score") if isinstance(payload, dict) else None,
        "verdict": verdict or "",
        "production_decision": decision or "",
        "blocking": verdict in BLOCKING_SCORE_VERDICTS or decision == "kill",
        "revision_recommended": verdict in {"小改", "大改"} or decision == "revise",
        "source_snapshot_fresh": fresh,
        "source_snapshot_message": fresh_message,
        "source_aggregate_hash": (payload.get("source_snapshot") or {}).get("aggregate_hash") if isinstance(payload, dict) else "",
    }


def revision_signal(root: str) -> dict[str, Any]:
    relpath = "修订/revision_plan.json"
    payload = load_json(os.path.join(root, relpath), {}) or {}
    tasks = payload.get("tasks") if isinstance(payload, dict) else []
    tasks = tasks if isinstance(tasks, list) else []
    by_priority: dict[str, int] = {}
    conflicts = []
    open_tasks = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        priority = str(task.get("priority") or "P?")
        by_priority[priority] = by_priority.get(priority, 0) + 1
        if task.get("conflict"):
            conflicts.append(task)
        if task.get("status") not in {"done", "completed", "waived"}:
            open_tasks.append(task)
    return {
        "path": relpath,
        "exists": os.path.exists(os.path.join(root, relpath)),
        "task_count": len(tasks),
        "open_task_count": len(open_tasks),
        "by_priority": by_priority,
        "conflict_count": len(conflicts),
        "conflict_ids": [item.get("id") or item.get("title") for item in conflicts[:20]],
    }


def feedback_signal(root: str) -> dict[str, Any]:
    candidates = [
        "反馈/feedback_report.json",
        "读者反馈/feedback_report.json",
        "模拟读者/simulate_report.json",
        "评分/simulate_report.json",
    ]
    found = [evidence_record(root, path) for path in candidates if os.path.exists(os.path.join(root, path))]
    return {
        "exists": bool(found),
        "reports": found,
        "report_count": len(found),
    }


def release_signal(root: str) -> dict[str, Any]:
    relpath = "导出/release_manifest.json"
    payload = load_json(os.path.join(root, relpath), {}) or {}
    exists = os.path.exists(os.path.join(root, relpath))
    current_snapshot = snapshot_chapters(root, mode="release:chapters")
    stored_hash = str(payload.get("chapter_aggregate_hash") or "") if isinstance(payload, dict) else ""
    fresh = bool(stored_hash and stored_hash == current_snapshot.get("aggregate_hash"))
    readiness = payload.get("release_readiness") if isinstance(payload, dict) else {}
    return {
        "path": relpath,
        "exists": exists,
        "release_ready": bool(payload.get("release_ready")) if isinstance(payload, dict) else False,
        "release_profile": payload.get("release_profile") if isinstance(payload, dict) else "",
        "blocker_count": int((readiness or {}).get("blocker_count") or 0) if isinstance(readiness, dict) else 0,
        "chapter_snapshot_fresh": fresh,
        "chapter_snapshot_message": "release manifest fresh" if fresh else "release_manifest missing or stale against current chapters",
        "stored_chapter_aggregate_hash": stored_hash,
        "current_chapter_aggregate_hash": current_snapshot.get("aggregate_hash") or "",
    }


def decide_board(review: dict[str, Any], score: dict[str, Any], revision: dict[str, Any], release: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if not review.get("exists"):
        reasons.append("review_report is missing")
    elif not review.get("source_snapshot_fresh"):
        reasons.append(f"review_report is stale: {review.get('source_snapshot_message')}")
    if not score.get("exists"):
        reasons.append("score_report is missing")
    elif not score.get("source_snapshot_fresh"):
        reasons.append(f"score_report is stale: {score.get('source_snapshot_message')}")
    if review.get("blocking_count"):
        reasons.append("review_report still has blocking findings")
    if score.get("blocking"):
        reasons.append("score verdict/production decision blocks release")
    if revision.get("conflict_count"):
        reasons.append("revision_plan contains unresolved conflicts")
    if release.get("exists") and not release.get("chapter_snapshot_fresh"):
        reasons.append("release_manifest is stale against current chapters")
    if release.get("exists") and not release.get("release_ready"):
        reasons.append("release_manifest is not ready")
    if reasons:
        return "hold_for_editor_arbitration", reasons
    if revision.get("open_task_count") or score.get("revision_recommended"):
        if revision.get("open_task_count"):
            reasons.append("revision_plan has open tasks")
        if score.get("revision_recommended"):
            reasons.append("score recommends revision")
        return "revise_before_release", reasons
    return "ready_for_release_review", ["no blocking board-level signals detected"]


def build_board(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    review = review_signal(root)
    score = score_signal(root)
    revision = revision_signal(root)
    feedback = feedback_signal(root)
    release = release_signal(root)
    decision, reasons = decide_board(review, score, revision, release)
    evidence = {
        "review_report": evidence_record(root, "审稿/review_report.json"),
        "score_report": evidence_record(root, "评分/score_report.json"),
        "revision_plan": evidence_record(root, "修订/revision_plan.json"),
        "release_manifest": evidence_record(root, "导出/release_manifest.json"),
        "feedback_reports": feedback.get("reports") or [],
    }
    return {
        "schema_version": 1,
        "kind": BOARD_KIND,
        "generated_at": now(),
        "project_root": root,
        "decision": decision,
        "reasons": reasons,
        "approval_required": decision != "ready_for_release_review",
        "signals": {
            "review": review,
            "score": score,
            "revision": revision,
            "feedback": feedback,
            "release": release,
        },
        "evidence": evidence,
        "next_actions": next_actions(root, decision, revision),
    }


def next_actions(root: str, decision: str, revision: dict[str, Any]) -> list[str]:
    if decision == "hold_for_editor_arbitration":
        return [f'python3 skills/novel/novel-edit/scripts/edit_plan.py "{root}"']
    if decision == "revise_before_release":
        if revision.get("exists"):
            return [f'sed -n "1,220p" "{root}/修订/修订计划.md"']
        return [f'python3 skills/novel/novel-craft/scripts/revision_planner.py "{root}"']
    return [f'python3 skills/novel/novel-craft/scripts/release_manifest.py "{root}" --release-profile platform_publish']


def render_markdown(board: dict[str, Any]) -> str:
    signals = board.get("signals") or {}
    review = signals.get("review") or {}
    score = signals.get("score") or {}
    revision = signals.get("revision") or {}
    release = signals.get("release") or {}
    lines = [
        "# Novel Review Board",
        "",
        f"- generated_at: {board.get('generated_at')}",
        f"- decision: {board.get('decision')}",
        f"- approval_required: {board.get('approval_required')}",
        "",
        "## Reasons",
        "",
    ]
    lines.extend(f"- {item}" for item in board.get("reasons") or [])
    lines.extend([
        "",
        "## Signals",
        "",
        f"- review blockers: {review.get('blocking_count', 0)} / findings={review.get('finding_count', 0)} fresh={review.get('source_snapshot_fresh')}",
        f"- score: {score.get('total_score')} verdict={score.get('verdict') or ''} decision={score.get('production_decision') or ''} fresh={score.get('source_snapshot_fresh')}",
        f"- revision: open={revision.get('open_task_count', 0)} conflicts={revision.get('conflict_count', 0)} by_priority={revision.get('by_priority') or {}}",
        f"- release manifest: exists={release.get('exists')} ready={release.get('release_ready')} fresh={release.get('chapter_snapshot_fresh')} blockers={release.get('blocker_count', 0)}",
        "",
        "## Next Actions",
        "",
    ])
    lines.extend(f"- {item}" for item in board.get("next_actions") or [])
    return "\n".join(lines) + "\n"


def render_html(board: dict[str, Any], markdown: str) -> str:
    payload = html.escape(json.dumps(board, ensure_ascii=False, indent=2))
    summary = html.escape(markdown)
    return (
        "<!doctype html><meta charset='utf-8'>"
        "<title>Novel Review Board</title>"
        "<style>body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;margin:24px;line-height:1.45}"
        "pre{background:#f6f8fa;padding:16px;border-radius:6px;overflow:auto}"
        ".decision{font-weight:700}.grid{display:grid;grid-template-columns:minmax(280px,1fr) minmax(280px,1fr);gap:20px}"
        "@media(max-width:800px){.grid{grid-template-columns:1fr}}</style>"
        f"<h1>Novel Review Board</h1><p class='decision'>{html.escape(str(board.get('decision') or ''))}</p>"
        f"<div class='grid'><section><h2>Summary</h2><pre>{summary}</pre></section>"
        f"<section><h2>JSON</h2><pre>{payload}</pre></section></div>"
    )


def write_board(root: str, board: dict[str, Any] | None = None, *, html_out: bool = False) -> tuple[str, str, dict[str, Any]]:
    root = os.path.abspath(root)
    board = board or build_board(root)
    out_dir = os.path.join(root, "审稿")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "review_board.json")
    md_path = os.path.join(out_dir, "review_board.md")
    html_path = os.path.join(out_dir, "review_board.html")
    markdown = render_markdown(board)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(board, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    if html_out:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(render_html(board, markdown))
        board.setdefault("outputs", {})["html"] = rel(root, html_path)
    if append_event:
        append_event(
            root,
            event_type="review_board_written",
            tool="novel-craft/scripts/review_board.py",
            outputs=[json_path, md_path],
            metadata={"decision": board.get("decision"), "approval_required": board.get("approval_required")},
        )
    return json_path, md_path, board


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="build novel review board packet")
    parser.add_argument("project_root")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--html", action="store_true", help="also write 审稿/review_board.html with --write")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    board = build_board(root)
    if args.write:
        json_path, md_path, _board = write_board(root, board, html_out=args.html)
        if not args.json:
            print(f"[ok] review board JSON → {json_path}")
            print(f"[ok] review board MD   → {md_path}")
            if args.html:
                print(f"[ok] review board HTML → {os.path.join(root, '审稿', 'review_board.html')}")
    print(json.dumps(board, ensure_ascii=False, indent=2) if args.json else render_markdown(board))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
