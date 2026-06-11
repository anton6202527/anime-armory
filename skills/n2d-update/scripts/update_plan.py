#!/usr/bin/env python3
"""Plan n2d episode rebuilds after skill updates.

Pure standard-library helper.  It does not call model backends or mutate stage
artifacts; it records/compares skill fingerprints and writes a rerun plan.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

SCRIPT_DIR = os.path.dirname(__file__)
SKILL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
REPO_SKILLS = os.path.abspath(os.path.join(SKILL_DIR, ".."))
REPO_ROOT = os.path.abspath(os.path.join(REPO_SKILLS, ".."))
COMMON = os.path.join(REPO_SKILLS, "common")
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

from n2d_contract import (  # noqa: E402
    SKILL_UPDATE_PLAN_KIND,
    SKILL_UPDATE_SNAPSHOT_KIND,
    production_dir,
    stage_for_key,
    stage_specs,
)
from n2d_route import (  # noqa: E402
    cell_state,
    is_started,
    normalize_episode,
    parse_progress,
    stage_of,
)

from skill_snapshot import ( # noqa: E402
    now_iso, 
    snapshot_for_skills, 
    changed_files_since, 
    git_changed_files
)

KIND_SNAPSHOT = SKILL_UPDATE_SNAPSHOT_KIND
KIND_PLAN = SKILL_UPDATE_PLAN_KIND
SNAPSHOT_FILE = "skill_update_snapshot.json"
PLAN_PREFIX = "skill_update_plan"

ALWAYS_RELEVANT_SKILLS = {
    "common",
    "novel2drama",
    "n2d-dashboard",
    "n2d-review",
    "n2d-batch",
    "n2d-update",
}
OBSERVE_ONLY_SKILLS = {
    "common",
    "novel2drama",
    "n2d-dashboard",
    "n2d-review",
    "n2d-batch",
    "n2d-update",
}


def rel(path: str) -> str:
    return os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")


def skill_name_for_path(path: str) -> Optional[str]:
    rel_path = rel(path)
    parts = rel_path.split("/")
    if len(parts) >= 2 and parts[0] == "skills":
        return parts[1]
    return None


def snapshot_path(root: str) -> str:
    return os.path.join(production_dir(root), SNAPSHOT_FILE)


def load_snapshot(root: str) -> Optional[Dict[str, Any]]:
    path = snapshot_path(root)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        return None
    return data


def write_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def rows_by_episode(root: str) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
    header, rows = parse_progress(root)
    return header, {normalize_episode(str(r.get("_ep") or r.get("集") or "")): r for r in rows}


def spec_key_for_route(route: Dict[str, Any]) -> Optional[str]:
    col = route.get("col")
    skill = route.get("skill")
    label = route.get("label")
    for spec in stage_specs():
        if col and col in spec.get("progress_columns", ()):
            return str(spec["key"])
        if skill and skill == spec.get("owner") and label == spec.get("label"):
            return str(spec["key"])
    if label == "补真实配音":
        return "voice"
    return None


def current_stage_key(root: str, ep: str, header: List[str], row: Dict[str, str]) -> str:
    route = stage_of(root, row, header)
    route_key = spec_key_for_route(route)
    if route_key:
        return route_key
    last_started: Optional[str] = None
    for spec in stage_specs():
        if not spec.get("routes"):
            continue
        cols = [c for c in spec.get("progress_columns", ()) if c in header]
        if cols and any(is_started(row.get(c, "")) or cell_state(row.get(c, "")) == "done" for c in cols):
            last_started = str(spec["key"])
    return last_started or "script_stage1"


def stage_index(key: str) -> int:
    for idx, spec in enumerate(stage_specs()):
        if spec.get("key") == key:
            return idx
    return 10**6


def relevant_stage_specs(until_key: str) -> List[Dict[str, Any]]:
    until = stage_index(until_key)
    specs: List[Dict[str, Any]] = []
    for idx, spec in enumerate(stage_specs()):
        if spec.get("routes") and idx <= until:
            specs.append(spec)
    return specs


def relevant_skills_for_stage(until_key: str) -> List[str]:
    skills = set(ALWAYS_RELEVANT_SKILLS)
    for spec in relevant_stage_specs(until_key):
        owner = spec.get("owner")
        if owner:
            skills.add(str(owner))
    return sorted(skills)


def stage_key_for_skill(skill: str, until_key: str) -> Optional[str]:
    candidates: List[str] = []
    for spec in relevant_stage_specs(until_key):
        if spec.get("owner") == skill:
            candidates.append(str(spec["key"]))
    return candidates[0] if candidates else None


def earliest_rerun_stage(changed_skills: Iterable[str], until_key: str) -> Optional[str]:
    keys: List[str] = []
    for skill in sorted(set(changed_skills)):
        if skill in OBSERVE_ONLY_SKILLS:
            continue
        key = stage_key_for_skill(skill, until_key)
        if key:
            keys.append(key)
    if not keys:
        return None
    return sorted(keys, key=stage_index)[0]


def plan_paths(root: str, ep: str) -> Tuple[str, str]:
    safe_ep = normalize_episode(ep)
    base = os.path.join(production_dir(root), f"{PLAN_PREFIX}_{safe_ep}")
    return base + ".json", base + ".md"


def command_for_rerun(root: str, ep: str, start_key: Optional[str], until_key: str) -> List[str]:
    if not start_key:
        gate_stage = (stage_for_key(until_key) or {}).get("gate_stage")
        if not gate_stage:
            return [f"python3 skills/n2d-update/scripts/update_plan.py record \"{root}\" {ep}"]
        return [
            f"python3 skills/n2d-dashboard/scripts/dashboard.py gate \"{root}\" {ep} --stage {gate_stage}",
        ]
    start = stage_for_key(start_key) or {}
    return [
        (
            "python3 skills/n2d-batch/scripts/queue.py plan "
            f"\"{root}\" --episodes {ep.replace('第', '').replace('集', '')} "
            f"--rerun-from {start_key} --scope \"skill 更新后重制到 {until_key}\" "
            "--max-concurrency 1 --max-retries 1"
        ),
        str(start.get("command", "")).format(root=root, ep=ep),
    ]


def render_markdown(plan: Dict[str, Any]) -> str:
    changed = plan.get("changed_files", [])
    lines = [
        f"# skill 更新重制计划 — {plan['episode']}",
        "",
        f"- 作品根：`{plan['root']}`",
        f"- 当前阶段：`{plan['current_stage']}`",
        f"- 建议重制：`{plan.get('rerun_from') or '只重跑 gate/review'}` → `{plan['rerun_until']}`",
        f"- 需要重制：{'是' if plan.get('rebuild_needed') else '否'}",
    ]
    if plan.get("needs_record"):
        lines.append("- 基线：缺失，先 `record` 后才能稳定做快照比对。")
    if plan.get("changed_skills"):
        lines.append(f"- 变动 skill：{', '.join(plan['changed_skills'])}")
    if changed:
        lines.extend(["", "## 变动文件"])
        lines.extend(f"- `{p}`" for p in changed[:80])
        if len(changed) > 80:
            lines.append(f"- ... 另有 {len(changed) - 80} 个文件")
    if plan.get("commands"):
        lines.extend(["", "## 建议命令"])
        lines.extend(f"```bash\n{cmd}\n```" for cmd in plan["commands"])
    if plan.get("notes"):
        lines.extend(["", "## 备注"])
        lines.extend(f"- {note}" for note in plan["notes"])
    lines.append("")
    return "\n".join(lines)


def build_plan(root: str, ep: str, *, include_git: bool = True) -> Dict[str, Any]:
    root = os.path.abspath(root)
    ep = normalize_episode(ep)
    header, rows = rows_by_episode(root)
    if ep not in rows:
        raise SystemExit(f"未在 _进度.md 找到 {ep}")
    row = rows[ep]
    until_key = current_stage_key(root, ep, header, row)
    relevant_skills = relevant_skills_for_stage(until_key)
    old = load_snapshot(root)
    new = snapshot_for_skills(REPO_ROOT, REPO_SKILLS, relevant_skills)
    snapshot_changes = changed_files_since(old, new)
    changed = set(snapshot_changes)
    if include_git and old is None:
        relevant_prefixes = tuple(f"skills/{s}/" for s in relevant_skills)
        changed.update(p for p in git_changed_files(REPO_ROOT) if p.startswith(relevant_prefixes))
    changed_files = sorted(changed)
    changed_skills = sorted({skill_name_for_path(os.path.join(REPO_ROOT, p)) or "" for p in changed_files} - {""})
    rerun_from = earliest_rerun_stage(changed_skills, until_key)
    rebuild_needed = bool(changed_files)
    notes: List[str] = []
    if not old:
        notes.append("当前作品没有 skill_update_snapshot 基线；本次结果会结合 git 工作区变动提示，建议先 record 建立基线。")
    if rebuild_needed and not rerun_from:
        notes.append("变动集中在 common/review/dashboard/batch/novel2drama 等横切层；先重跑 gate/审查/计划，不默认重抽图。")
    if rebuild_needed and rerun_from:
        notes.append("真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。")
    return {
        "kind": KIND_PLAN,
        "created_at": now_iso(),
        "root": root,
        "episode": ep,
        "current_stage": until_key,
        "rerun_from": rerun_from,
        "rerun_until": until_key,
        "rebuild_needed": rebuild_needed,
        "needs_record": old is None,
        "relevant_skills": relevant_skills,
        "changed_skills": changed_skills,
        "changed_files": changed_files,
        "snapshot_changed_files": snapshot_changes,
        "commands": command_for_rerun(root, ep, rerun_from, until_key) if rebuild_needed else [],
        "notes": notes,
    }


def record(root: str, episodes: Sequence[str]) -> Dict[str, Any]:
    header, rows = rows_by_episode(root)
    skills: Set[str] = set(ALWAYS_RELEVANT_SKILLS)
    normalized: List[str] = []
    for ep in episodes:
        ep = normalize_episode(ep)
        if ep not in rows:
            raise SystemExit(f"未在 _进度.md 找到 {ep}")
        normalized.append(ep)
        until_key = current_stage_key(root, ep, header, rows[ep])
        skills.update(relevant_skills_for_stage(until_key))
    snap = snapshot_for_skills(REPO_ROOT, REPO_SKILLS, skills)
    snap["root"] = os.path.abspath(root)
    snap["episodes"] = normalized
    write_json(snapshot_path(root), snap)
    return snap


def all_episodes(root: str) -> List[str]:
    _header, rows = rows_by_episode(root)
    return list(rows.keys())


def write_plan(root: str, plan: Dict[str, Any]) -> None:
    json_path, md_path = plan_paths(root, plan["episode"])
    plan["plan_json"] = json_path
    plan["plan_md"] = md_path
    write_json(json_path, plan)
    with open(md_path + ".tmp", "w", encoding="utf-8") as fh:
        fh.write(render_markdown(plan))
    os.replace(md_path + ".tmp", md_path)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect n2d skill updates and plan bounded rebuilds.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("root", help="制漫剧/<剧名> 作品根")
        p.add_argument("episode", nargs="?", help="第N集；--all 时可省略")
        p.add_argument("--all", action="store_true", help="扫描/记录所有进度表集")

    p_check = sub.add_parser("check", help="compare current skills with snapshot and print rebuild plan")
    add_common(p_check)
    p_check.add_argument("--write-plan", action="store_true", help="write 生产数据/skill_update_plan_第N集.json/md")
    p_check.add_argument("--json", action="store_true", help="print JSON")
    p_check.add_argument("--no-git", action="store_true", help="ignore git working-tree changes")

    p_record = sub.add_parser("record", help="record current relevant skill fingerprints as baseline")
    add_common(p_record)
    p_record.add_argument("--json", action="store_true", help="print JSON")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = os.path.abspath(args.root)
    episodes = all_episodes(root) if args.all else [args.episode]
    if not episodes or any(not ep for ep in episodes):
        raise SystemExit("请提供集号，或使用 --all")

    if args.cmd == "record":
        snap = record(root, [str(ep) for ep in episodes])
        if args.json:
            print(json.dumps(snap, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"已记录 skill 快照：{snapshot_path(root)}（{len(snap.get('files', {}))} files）")
        return 0

    plans = [build_plan(root, str(ep), include_git=not args.no_git) for ep in episodes]
    if args.write_plan:
        for plan in plans:
            write_plan(root, plan)
    if args.json:
        print(json.dumps(plans[0] if len(plans) == 1 else plans, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for plan in plans:
            marker = "建议重制" if plan["rebuild_needed"] else "无需重制"
            print(
                f"{plan['episode']}: {marker} "
                f"current={plan['current_stage']} "
                f"rerun={plan.get('rerun_from') or 'gate/review'}→{plan['rerun_until']} "
                f"changed={len(plan['changed_files'])}"
            )
            if plan.get("plan_md"):
                print(f"  plan: {plan['plan_md']}")
            for note in plan.get("notes", []):
                print(f"  - {note}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
