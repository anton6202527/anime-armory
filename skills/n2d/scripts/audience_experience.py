#!/usr/bin/env python3
"""Audience-experience gate for n2d episodes."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
LIB = SCRIPT_DIR.parents[0] / "_lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

try:
    from n2d_route import normalize_episode  # type: ignore
except Exception:  # pragma: no cover
    normalize_episode = lambda x: str(x or "").strip()  # type: ignore


VERSION = 1
OUT_JSON = "audience_experience_{episode}.json"
OUT_MD = "audience_experience_{episode}.md"
PAYOFF_MARKERS = ("兑现", "推进", "发现", "揭示", "反转", "冲突", "阻碍", "选择", "结果", "代价", "爽点", "钩", "reveal", "payoff", "turn", "choice")
HOOK_MARKERS = ("钩", "危机", "冲突", "悬念", "问题", "反转", "承诺", "hook", "promise", "question")


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


def flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join(str(k) + " " + flatten(v) for k, v in value.items())
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    return str(value or "")


def filled(value: Any) -> bool:
    text = flatten(value).strip()
    return bool(text) and not re.search(r"(待补|TODO|TBD|<[^>]+>|__.+?__)", text, re.I)


def storyboard_data(root: Path, episode: str) -> Mapping[str, Any]:
    data = load_json(root / "脚本" / episode / "storyboard.json")
    return data if isinstance(data, Mapping) else {}


def storyboard(root: Path, episode: str) -> List[Mapping[str, Any]]:
    data = storyboard_data(root, episode)
    clips = data.get("clips") if isinstance(data, Mapping) else []
    return [c for c in clips or [] if isinstance(c, Mapping)]


def preventive_contract(root: Path, episode: str) -> Mapping[str, Any]:
    data = load_json(root / "脚本" / episode / "preventive_contracts.json")
    return data if isinstance(data, Mapping) else {}


def _first_real(*values: Any) -> str:
    for value in values:
        text = flatten(value).strip()
        if filled(text):
            return text
    return ""


def episode_promise_fields(root: Path, episode: str) -> Dict[str, str]:
    """Return promise fields, falling back to storyboard-level contracts.

    Older script outputs may have an empty preventive_contracts.episode_promise
    while storyboard.json already carries first_3s_visual_hook,
    retention_promise_ledger and audience_question_ledger. The audience gate is
    about whether the current edit can be reviewed, so those storyboard contracts
    are valid evidence instead of forcing a script-stage false block.
    """
    contract = preventive_contract(root, episode)
    promise = contract.get("episode_promise") if isinstance(contract.get("episode_promise"), Mapping) else {}
    story = storyboard_data(root, episode)
    first = story.get("first_3s_visual_hook") if isinstance(story.get("first_3s_visual_hook"), Mapping) else {}
    core = story.get("core_attraction") if isinstance(story.get("core_attraction"), Mapping) else {}
    questions = story.get("audience_question_ledger") if isinstance(story.get("audience_question_ledger"), Mapping) else {}
    ledger = story.get("retention_promise_ledger") if isinstance(story.get("retention_promise_ledger"), list) else []
    paid = [row for row in ledger if isinstance(row, Mapping) and str(row.get("payoff_status") or "").lower() in {"paid", "progressed", "done", "pass"}]
    open_tail = [row for row in ledger if isinstance(row, Mapping) and str(row.get("promise_type") or "").lower() == "tail_hook"]
    payoff_text = "；".join(_first_real(row.get("payoff_evidence"), row.get("promise")) for row in paid)
    tail_text = _first_real(questions.get("tail_hook"), *(row.get("promise") for row in open_tail))
    return {
        "opening_hook": _first_real(promise.get("opening_hook"), first.get("visual_hook"), first.get("content_proposition"), first.get("content_promise"), first.get("onscreen_text")),
        "payoff_or_progress": _first_real(promise.get("payoff_or_progress"), payoff_text, core.get("why_watch")),
        "cliffhanger": _first_real(promise.get("cliffhanger"), tail_text, core.get("viewer_question")),
    }


def duration(clip: Mapping[str, Any]) -> float:
    for key in ("duration", "duration_sec", "seconds", "时长"):
        try:
            value = clip.get(key)
            if value is not None:
                return max(0.5, float(value))
        except Exception:
            pass
    return 3.0


def clip_text(clip: Mapping[str, Any]) -> str:
    return flatten({
        "description": clip.get("description") or clip.get("画面") or "",
        "dramatic_function": clip.get("dramatic_function") or "",
        "editing_intent": clip.get("editing_intent") or "",
        "audience_effect": clip.get("audience_effect") or "",
        "intent": clip.get("intent") or {},
    })


def has_marker(text: str, markers: Sequence[str]) -> bool:
    low = text.lower()
    return any(marker.lower() in low for marker in markers)


def build_report(root: Path, episode: str) -> Dict[str, Any]:
    root = root.resolve()
    episode = normalize_episode(episode)
    clips = storyboard(root, episode)
    promise = episode_promise_fields(root, episode)
    findings: List[Dict[str, Any]] = []

    if not clips:
        findings.append({"severity": "block", "code": "missing_storyboard", "message": "缺 storyboard clips，无法审观众体验。", "return_to_stage": "script_stage2"})
    if not filled(promise.get("opening_hook")):
        findings.append({"severity": "block", "code": "missing_opening_hook", "message": "每集承诺合同缺 opening_hook，前3秒钩子不可审。", "return_to_stage": "script_stage1"})
    if not filled(promise.get("payoff_or_progress")):
        findings.append({"severity": "block", "code": "missing_payoff", "message": "每集承诺合同缺 payoff_or_progress，爽点/信息回报不可审。", "return_to_stage": "script_stage1"})
    if not filled(promise.get("cliffhanger")):
        findings.append({"severity": "block", "code": "missing_cliffhanger", "message": "每集承诺合同缺 cliffhanger，集尾追看钩不可审。", "return_to_stage": "script_stage1"})

    first_window = []
    acc = 0.0
    for clip in clips:
        if acc <= 3.0:
            first_window.append(clip)
        acc += duration(clip)
    if clips and not any(has_marker(clip_text(c), HOOK_MARKERS) for c in first_window):
        findings.append({"severity": "block", "code": "weak_first_3s", "message": "前3秒窗口没有钩子/危机/悬念/承诺信号。", "return_to_stage": "script_stage2"})

    total = 0.0
    last_payoff = 0.0
    stale_windows: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, 1):
        total += duration(clip)
        if has_marker(clip_text(clip), PAYOFF_MARKERS):
            last_payoff = total
        if total - last_payoff > 20.0:
            stale_windows.append({"clip_index": idx, "at_sec": round(total, 2), "gap_sec": round(total - last_payoff, 2)})
            last_payoff = total
    if stale_windows:
        findings.append({
            "severity": "warn",
            "code": "payoff_gap_over_20s",
            "message": "超过 20 秒缺信息回报/阻碍/兑现/反转信号。",
            "details": stale_windows[:5],
            "return_to_stage": "script_stage2",
        })

    final_text = " ".join(clip_text(c) for c in clips[-2:])
    cliff = flatten(promise.get("cliffhanger"))
    if clips and cliff and not has_marker(final_text + " " + cliff, ("钩", "悬念", "危机", "反转", "下一", "cliff", "question")):
        findings.append({"severity": "warn", "code": "weak_tail_hook", "message": "结尾两镜和 cliffhanger 缺追看信号，可能制作没错但不想追。", "return_to_stage": "script_stage1"})

    block = sum(1 for f in findings if f["severity"] == "block")
    warn = sum(1 for f in findings if f["severity"] == "warn")
    return {
        "kind": "n2d_audience_experience",
        "version": VERSION,
        "root": str(root),
        "episode": episode,
        "generated_at": now_iso(),
        "status": "blocked" if block else ("warn" if warn else "pass"),
        "summary": {"clips": len(clips), "duration_sec_est": round(sum(duration(c) for c in clips), 2), "block": block, "warn": warn},
        "findings": findings,
    }


def render_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# n2d Audience Experience",
        "",
        f"- 集：{payload.get('episode')}",
        f"- 状态：{payload.get('status')}",
        f"- 汇总：{payload.get('summary')}",
        "",
        "| severity | code | message |",
        "|---|---|---|",
    ]
    for row in payload.get("findings") or []:
        lines.append(f"| {row.get('severity')} | {row.get('code')} | {str(row.get('message') or '').replace(chr(10), ' ')[:240]} |")
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, episode: str, payload: Mapping[str, Any]) -> Dict[str, str]:
    out = production_dir(root)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / OUT_JSON.format(episode=episode)
    md_path = out / OUT_MD.format(episode=episode)
    tmp = json_path.with_name(f"{json_path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, json_path)
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {"json": relpath(root, json_path), "markdown": relpath(root, md_path)}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="check n2d audience experience gate")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root)
    payload = build_report(root, ns.episode)
    if ns.write:
        payload["outputs"] = write_outputs(root, payload["episode"], payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_markdown(payload))
    return 2 if payload.get("status") == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
