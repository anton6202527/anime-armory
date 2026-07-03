#!/usr/bin/env python3
"""Generate real best-of-N keyshot candidates without overwriting final frames.

This closes the production gap between ``keyshot_candidates.py`` (plan only) and
``candidate_select.py`` (selects existing candidates only).  It reuses
``codex_image_runner`` for prompt resolution, reference attachments, generation
events, and Codex image generation, but redirects each keyshot's firstframe
target into ``出图/<episode>/候选/<clip>/candidate_NN.png``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import codex_image_runner as cir  # noqa: E402


KIND = "n2d_keyshot_candidate_generation"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def plan_path(root: Path, episode: str) -> Path:
    return root / "生产数据" / f"keyshot_candidate_plan_{episode}.json"


def load_plan(root: Path, episode: str) -> Dict[str, Any]:
    path = plan_path(root, episode)
    if not path.is_file():
        raise FileNotFoundError(f"missing keyshot candidate plan: {path}")
    data = load_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("keyshots"), list):
        raise ValueError(f"invalid keyshot candidate plan: {path}")
    return data


def prompt_shot_for_clip(clip: str) -> str:
    text = str(clip or "").strip()
    match = re.search(r"(?:EP\d+_)?CLIP[_\s-]*0*([0-9]+)", text, re.I)
    if not match:
        match = re.search(r"Clip[_\s-]*0*([0-9]+)", text, re.I)
    if not match:
        raise ValueError(f"cannot map keyshot clip id to prompt shot: {clip}")
    return f"Clip_{int(match.group(1)):02d}"


def clip_filter_match(clip: str, requested: Sequence[str]) -> bool:
    if not requested:
        return True
    aliases = {clip, prompt_shot_for_clip(clip), prompt_shot_for_clip(clip).replace("_", "")}
    normalized = {item.strip() for item in requested if item.strip()}
    normalized.update(cir.normalize_shot_name(item) for item in requested if item.strip())
    return bool(aliases & normalized)


def source_firstframe_target(root: Path, episode: str, clip: str) -> cir.Target:
    sections = cir.load_sections(root, episode)
    shot = prompt_shot_for_clip(clip)
    section = cir.section_for(sections, shot)
    target = cir.target_for_shot(shot, section, episode)
    if target.mode != "firstframe":
        raise ValueError(f"{clip}: expected firstframe target, got {target.mode}")
    return target


def candidate_rel_path(episode: str, clip: str, index: int) -> str:
    return f"出图/{episode}/候选/{clip}/candidate_{index:02d}.png"


def sidecar_path(root: Path, rel_path: str) -> Path:
    return (root / rel_path).with_suffix(".json")


def build_candidate_tasks(
    root: Path,
    episode: str,
    plan: Mapping[str, Any],
    *,
    clips: Sequence[str] = (),
    max_candidates_per_clip: Optional[int] = None,
    limit_clips: Optional[int] = None,
    force: bool = False,
) -> List[Dict[str, Any]]:
    rows = [row for row in plan.get("keyshots") or [] if isinstance(row, Mapping)]
    rows = [row for row in rows if clip_filter_match(str(row.get("clip") or ""), clips)]
    if limit_clips is not None:
        rows = rows[: max(0, limit_clips)]

    tasks: List[Dict[str, Any]] = []
    for row in rows:
        clip = str(row.get("clip") or "").strip()
        if not clip:
            continue
        source = source_firstframe_target(root, episode, clip)
        planned = int(row.get("candidate_count") or 0)
        count = planned if max_candidates_per_clip is None else min(planned, max_candidates_per_clip)
        count = max(0, count)
        for index in range(1, count + 1):
            rel_path = candidate_rel_path(episode, clip, index)
            exists = cir.png_valid(root / rel_path)
            if exists and not force:
                status = "skip_existing"
            else:
                status = "pending"
            candidate = cir.Target(
                shot=f"{prompt_shot_for_clip(clip)}_candidate_{index:02d}",
                clip=source.clip,
                mode="firstframe",
                rel_path=rel_path,
                section=source.section,
                variant_note=f"关键镜 best-of-N 候选 {index:02d}/{count}；源目标 {source.rel_path}；候选目录按 {clip} 归档。",
            )
            tasks.append({
                "clip": clip,
                "candidate": f"candidate_{index:02d}",
                "index": index,
                "planned_count": planned,
                "source_target": source,
                "target": candidate,
                "rel_path": rel_path,
                "status": status,
                "tags": list(row.get("tags") or []),
                "criteria": list(row.get("selection_criteria") or []),
            })
    return tasks


def write_candidate_sidecar(root: Path, episode: str, task: Mapping[str, Any], status: str) -> None:
    target: cir.Target = task["target"]
    source: cir.Target = task["source_target"]
    payload = {
        "kind": "n2d_keyshot_candidate",
        "episode": episode,
        "clip": task.get("clip"),
        "candidate": task.get("candidate"),
        "path": target.rel_path,
        "source_target": source.rel_path,
        "source_prompt_shot": source.shot,
        "status": status,
        "qc_status": "not_run",
        "tags": task.get("tags") or [],
        "selection_criteria": task.get("criteria") or [],
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json(sidecar_path(root, target.rel_path), payload)


def run_candidate_select(root: Path, episode: str, *, apply_selection: bool, no_ledger: bool) -> int:
    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent / "candidate_select.py"),
        str(root),
        episode,
        "--json",
    ]
    if apply_selection:
        cmd.append("--apply")
    if no_ledger:
        cmd.append("--no-ledger")
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    return proc.returncode


def run_generation(
    root: Path,
    episode: str,
    *,
    clips: Sequence[str],
    max_candidates_per_clip: Optional[int],
    limit_clips: Optional[int],
    timeout_sec: Optional[float],
    dry_run: bool,
    force: bool,
    stop_on_fail: bool,
    skip_preflight: bool,
    select_after: bool,
    apply_selection: bool,
    no_ledger: bool,
) -> Dict[str, Any]:
    plan = load_plan(root, episode)
    tasks = build_candidate_tasks(
        root,
        episode,
        plan,
        clips=clips,
        max_candidates_per_clip=max_candidates_per_clip,
        limit_clips=limit_clips,
        force=force,
    )
    summary: Dict[str, Any] = {
        "kind": KIND,
        "episode": episode,
        "planned_tasks": len(tasks),
        "generated": 0,
        "skipped_existing": 0,
        "failed": 0,
        "tasks": [],
    }
    task_id = os.environ.get("N2D_TASK_ID") or f"keyshot-candidates-{episode}"

    if dry_run:
        for task in tasks:
            target: cir.Target = task["target"]
            source: cir.Target = task["source_target"]
            summary["tasks"].append({
                "clip": task["clip"],
                "candidate": task["candidate"],
                "source_target": source.rel_path,
                "target": target.rel_path,
                "status": task["status"],
            })
        return summary

    if not skip_preflight and not cir.run_image_gate(root, episode, stage="image_preflight"):
        summary["preflight_blocked"] = True
        return summary

    for task in tasks:
        target: cir.Target = task["target"]
        if task["status"] == "skip_existing":
            summary["skipped_existing"] += 1
            summary["tasks"].append({"clip": task["clip"], "candidate": task["candidate"], "target": target.rel_path, "status": "skip_existing"})
            continue
        print(f"[candidate] {task['clip']} {task['candidate']} -> {target.rel_path}", flush=True)
        ok = cir.process_target(
            root,
            episode,
            target,
            task_id=task_id,
            timeout_sec=timeout_sec,
            dry_run=False,
            force=force,
        )
        if ok:
            write_candidate_sidecar(root, episode, task, "pass")
            summary["generated"] += 1
            status = "pass"
        else:
            write_candidate_sidecar(root, episode, task, "fail")
            summary["failed"] += 1
            status = "fail"
        summary["tasks"].append({"clip": task["clip"], "candidate": task["candidate"], "target": target.rel_path, "status": status})
        if not ok and stop_on_fail:
            break

    if select_after and summary["failed"] == 0:
        summary["candidate_select_exit_code"] = run_candidate_select(root, episode, apply_selection=apply_selection, no_ledger=no_ledger)
    return summary


def split_csv(value: str) -> List[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--clip", action="append", default=[], help="keyshot clip id or prompt clip; may be repeated or comma-separated")
    ap.add_argument("--max-candidates-per-clip", type=int, help="cap generation count per keyshot; use 3 for production floor")
    ap.add_argument("--limit-clips", type=int, help="only process the first N planned keyshots")
    ap.add_argument("--timeout-sec", type=float, default=float(os.environ.get("N2D_CODEX_IMAGE_TIMEOUT", "900")))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--stop-on-fail", action="store_true")
    ap.add_argument("--skip-preflight", action="store_true")
    ap.add_argument("--no-select", action="store_true", help="do not run candidate_select.py after generation")
    ap.add_argument("--apply-selection", action="store_true", help="pass --apply to candidate_select.py after generation")
    ap.add_argument("--no-ledger", action="store_true", help="pass --no-ledger to candidate_select.py")
    ap.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root).resolve()
    episode = cir.normalize_episode(ns.episode)
    clips: List[str] = []
    for item in ns.clip:
        clips.extend(split_csv(item))
    summary = run_generation(
        root,
        episode,
        clips=clips,
        max_candidates_per_clip=ns.max_candidates_per_clip,
        limit_clips=ns.limit_clips,
        timeout_sec=ns.timeout_sec,
        dry_run=ns.dry_run,
        force=ns.force,
        stop_on_fail=ns.stop_on_fail,
        skip_preflight=ns.skip_preflight,
        select_after=not ns.no_select,
        apply_selection=ns.apply_selection,
        no_ledger=ns.no_ledger,
    )
    if ns.json or ns.dry_run:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"关键镜候选生成 {episode}: generated={summary.get('generated')} "
            f"skipped={summary.get('skipped_existing')} failed={summary.get('failed')}"
        )
    return 0 if not summary.get("preflight_blocked") and int(summary.get("failed") or 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
