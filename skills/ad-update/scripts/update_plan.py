#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plan ad project rework after ad skill updates.

Pure standard-library helper. It records and compares content fingerprints for
the ad skill family, then writes a project-local rework plan.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from typing import Any, Iterable

SCRIPT_DIR = os.path.dirname(__file__)
SKILL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
REPO_SKILLS = os.path.abspath(os.path.join(SKILL_DIR, ".."))
REPO_ROOT = os.path.abspath(os.path.join(REPO_SKILLS, ".."))
CRAFT_DIR = os.path.join(REPO_SKILLS, "ad-craft", "scripts")
LIB_DIR = os.path.join(REPO_SKILLS, "ad", "_lib")
for path in (CRAFT_DIR, LIB_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

import contract  # noqa: E402
import progress_md  # noqa: E402

LINE = "ad"
LINE_LABEL = "拍广告"
KIND_SNAPSHOT = "ad_skill_update_snapshot"
KIND_PLAN = "ad_skill_update_plan"
SCHEMA_VERSION = 1
SNAPSHOT_FILE = "ad_skill_update_snapshot.json"
PLAN_JSON = "ad_skill_update_plan.json"
PLAN_MD = "ad_skill_update_plan.md"
TEXT_SUFFIXES = {".md", ".py", ".sh", ".json", ".html"}
EXCLUDED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
PARTIAL_RE = re.compile(r"(\d+)\s*/\s*(\d+)")

STAGE_ORDER = [str(stage["key"]) for stage in contract.stage_table()]
STAGE_LABELS = {str(stage["key"]): str(stage["label"]) for stage in contract.stage_table()}
OBSERVE_ONLY_SKILLS = {"ad-progress", "ad-update"}
ALWAYS_RELEVANT_SKILLS = {"ad", "ad-craft"} | OBSERVE_ONLY_SKILLS
SKILL_DEFAULT_STAGE = {
    "ad": "brief",
    "ad-craft": "brief",
    "ad-concept": "concept",
    "ad-script": "script",
    "ad-voice": "voice",
    "ad-score": "image",
    "ad-image": "image",
    "ad-video": "video",
    "ad-compose": "compose",
    "ad-review": "review",
    "ad-feedback": "feedback",
    "ad-progress": "brief",
    "ad-update": "brief",
}
FILE_STAGE_HINTS: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "ad-craft": (
        ("handoff", ("ai_usage.py", "AI使用", "授权")),
        ("brief", ("contract.py", "gate.py", "progress_set.py", "选择点与偏好")),
    ),
    "ad-script": (
        ("storyboard", ("storyboard", "镜头", "分镜")),
        ("script", ("广告脚本", "voiceover", "广告法")),
    ),
    "ad-compose": (
        ("compose", ("deliver.py", "delivery", "交付")),
    ),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def rel(path: str) -> str:
    return os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")


def production_dir(root: str) -> str:
    return os.path.join(root, "生产数据")


def snapshot_path(root: str) -> str:
    return os.path.join(production_dir(root), SNAPSHOT_FILE)


def plan_paths(root: str) -> tuple[str, str]:
    return os.path.join(production_dir(root), PLAN_JSON), os.path.join(production_dir(root), PLAN_MD)


def write_json(path: str, payload: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def read_json(path: str) -> dict[str, Any] | None:
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, dict) else None


def load_meta(root: str) -> dict[str, Any]:
    return read_json(os.path.join(root, "_meta.json")) or {}


def skill_name_for_relpath(path: str) -> str | None:
    parts = path.split("/")
    if len(parts) >= 2 and parts[0] == "skills":
        return parts[1]
    return None


def stage_index(stage: str | None) -> int:
    if not stage:
        return 10**6
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        return 10**6


def stage_label(stage: str | None) -> str:
    return STAGE_LABELS.get(stage or "", stage or "")


def state_of(status: str) -> str:
    raw = (status or "").strip()
    low = raw.lower()
    if "✅" in raw or "[x]" in low:
        return "done"
    match = PARTIAL_RE.search(raw)
    if match:
        current = int(match.group(1))
        total = int(match.group(2))
        if total > 0 and current >= total:
            return "done"
        if current > 0:
            return "partial"
    if "⏳" in raw or "rough" in low or "block" in low or "🔴" in raw:
        return "partial"
    if not raw or raw in {"⬜", "[ ]"}:
        return "todo"
    return "partial"


def parse_stage_rows(root: str) -> list[dict[str, str]]:
    path = os.path.join(root, "_进度.md")
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    return progress_md.parse_stage_rows(
        text,
        section_keywords=("阶段进度",),
        min_cols=2,
        label_col=0,
        status_col=1,
    )


def progress_context(root: str) -> dict[str, Any]:
    rows = parse_stage_rows(root)
    label_to_stage = {str(stage["label"]): str(stage["key"]) for stage in contract.stage_table()}
    stage_to_owner = {str(stage["key"]): str(stage.get("owner", "")) for stage in contract.stage_table()}
    current_stage = STAGE_ORDER[0] if STAGE_ORDER else "brief"
    first_open: dict[str, Any] | None = None
    normalized_rows = []
    for row in rows:
        label = row["label"]
        stage = label_to_stage.get(label)
        owner = stage_to_owner.get(stage or "", "")
        skill = skill_from_owner(owner)
        state = state_of(row["status"])
        normalized = {"label": label, "owner": owner, "skill": skill, "stage": stage, "status": row["status"], "state": state}
        normalized_rows.append(normalized)
        if stage and state != "todo" and stage_index(stage) > stage_index(current_stage):
            current_stage = stage
        if first_open is None and state != "done":
            first_open = normalized
    todo = {
        "stage_key": first_open.get("stage") if first_open else None,
        "stage_label": first_open.get("label") if first_open else "全部完成",
        "skill": first_open.get("skill") if first_open else None,
        "status": first_open.get("status") if first_open else "",
    }
    return {
        "schema": "stage_table",
        "kind": load_meta(root).get("kind") or LINE,
        "current_stage": current_stage,
        "current_todo": todo,
        "stage_count": len(rows),
        "done_count": sum(1 for row in normalized_rows if row["state"] == "done"),
        "rows": normalized_rows,
    }


def skill_from_owner(owner: str) -> str | None:
    names = existing_skill_names(SKILL_DEFAULT_STAGE)
    for name in sorted(names, key=len, reverse=True):
        if name in owner:
            return name
    return None


def is_test_path(path: str) -> bool:
    parts = path.split("/")
    base = parts[-1]
    return base.startswith("test_") or "tests" in parts


def iter_skill_files(skill: str) -> Iterable[str]:
    root = os.path.join(REPO_SKILLS, skill)
    if not os.path.isdir(root):
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for filename in filenames:
            suffix = os.path.splitext(filename)[1]
            if suffix not in TEXT_SUFFIXES:
                continue
            path = os.path.join(dirpath, filename)
            relpath = rel(path)
            if is_test_path(relpath):
                continue
            yield path


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def existing_skill_names(names: Iterable[str]) -> list[str]:
    return sorted(name for name in set(names) if os.path.isdir(os.path.join(REPO_SKILLS, name)))


def snapshot_for_skills(skills: Iterable[str], *, status: str = "recorded") -> dict[str, Any]:
    skill_names = existing_skill_names(skills)
    files: dict[str, dict[str, Any]] = {}
    for skill in skill_names:
        for path in iter_skill_files(skill):
            relpath = rel(path)
            files[relpath] = {"sha256": sha256_file(path), "size": os.path.getsize(path)}
    return {
        "kind": KIND_SNAPSHOT,
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "status": status,
        "relevant_skills": skill_names,
        "file_count": len(files),
        "files": files,
    }


def load_snapshot(root: str) -> dict[str, Any] | None:
    return read_json(snapshot_path(root))


def relevant_skills_for_stage(stage: str | None) -> list[str]:
    idx = stage_index(stage)
    skills = set(ALWAYS_RELEVANT_SKILLS)
    for skill, skill_stage in SKILL_DEFAULT_STAGE.items():
        if stage_index(skill_stage) <= idx:
            skills.add(skill)
    return existing_skill_names(skills)


def changed_files_since(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    old_files = baseline.get("files")
    if not isinstance(old_files, dict):
        return {"legacy_snapshot": True, "changed_files": [], "newly_relevant_files": [], "deleted_files": []}
    current_files = current.get("files") or {}
    baseline_skills = set(baseline.get("relevant_skills") or [])
    current_skills = set(current.get("relevant_skills") or [])
    changed: list[str] = []
    newly_relevant: list[str] = []
    deleted: list[str] = []
    for path, meta in current_files.items():
        skill = skill_name_for_relpath(path)
        old = old_files.get(path)
        if old is None:
            if skill not in baseline_skills:
                newly_relevant.append(path)
            else:
                changed.append(path)
            continue
        if old.get("sha256") != meta.get("sha256"):
            changed.append(path)
    for path in old_files:
        skill = skill_name_for_relpath(path)
        if skill in current_skills and path not in current_files:
            changed.append(path)
            deleted.append(path)
    return {
        "legacy_snapshot": False,
        "changed_files": sorted(set(changed)),
        "newly_relevant_files": sorted(set(newly_relevant)),
        "deleted_files": sorted(set(deleted)),
    }


def stage_for_changed_file(relpath: str) -> str | None:
    skill = skill_name_for_relpath(relpath)
    if not skill or skill in OBSERVE_ONLY_SKILLS:
        return None
    for stage, tokens in FILE_STAGE_HINTS.get(skill, ()):
        if any(token in relpath for token in tokens):
            return stage
    return SKILL_DEFAULT_STAGE.get(skill)


def build_execution_steps(root: str, plan: dict[str, Any]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if not plan.get("rebuild_needed"):
        steps.append({"type": "command", "purpose": "查看当前前沿", "command": f'python3 skills/ad-progress/scan.py "{root}"'})
        if plan.get("changed_skills") or plan.get("baseline_bootstrapped"):
            steps.append({
                "type": "command",
                "purpose": "接受当前产物后记录新基线",
                "command": f'python3 skills/ad-update/scripts/update_plan.py record "{root}"',
                "run_when": "用户确认无需返工",
            })
        return steps
    steps.append({
        "type": "agent_step",
        "purpose": "确认返工范围",
        "instruction": f"向用户确认从 {stage_label(plan.get('rerun_from'))} 回放到 {stage_label(plan.get('rerun_until'))}，再进入对应 ad skill。",
    })
    if stage_index(plan.get("rerun_from")) <= stage_index("compose"):
        steps.append({
            "type": "agent_step",
            "purpose": "保留当前广告产物",
            "instruction": "返工可能触及 brief、脚本、配音、出图、视频或交付；执行前先保留当前关键 JSON、媒体文件和成片。",
        })
    steps.append({"type": "command", "purpose": "查看生产前沿", "command": f'python3 skills/ad-progress/scan.py "{root}"', "run_when": "返工前后"})
    steps.append({
        "type": "command",
        "purpose": "验收后记录新基线",
        "command": f'python3 skills/ad-update/scripts/update_plan.py record "{root}"',
        "run_when": "返工产物验收通过",
    })
    return steps


def build_plan(root: str, *, bootstrap: bool = True) -> dict[str, Any]:
    root = os.path.abspath(root)
    progress = progress_context(root)
    current_stage = progress.get("current_stage") or (STAGE_ORDER[0] if STAGE_ORDER else "brief")
    relevant_skills = relevant_skills_for_stage(current_stage)
    baseline = load_snapshot(root)
    bootstrapped = False
    needs_record = False
    if baseline is None:
        if bootstrap:
            baseline = snapshot_for_skills(relevant_skills, status="bootstrap")
            baseline["project_root"] = root
            baseline["current_stage"] = current_stage
            write_json(snapshot_path(root), baseline)
            bootstrapped = True
        else:
            needs_record = True
    current_snapshot = snapshot_for_skills(relevant_skills, status="current")
    diff = changed_files_since(baseline, current_snapshot) if baseline else {
        "legacy_snapshot": False,
        "changed_files": [],
        "newly_relevant_files": [],
        "deleted_files": [],
    }
    changed_files = diff["changed_files"]
    changed_skills = sorted({skill_name_for_relpath(path) for path in changed_files if skill_name_for_relpath(path)})
    baseline_skills = set((baseline or {}).get("relevant_skills") or [])
    newly_relevant_skills = sorted(set(relevant_skills) - baseline_skills)
    observe_only_changed = sorted(skill for skill in changed_skills if skill in OBSERVE_ONLY_SKILLS)
    production_changed_files = [path for path in changed_files if skill_name_for_relpath(path) not in OBSERVE_ONLY_SKILLS]
    candidate_stages: list[str] = []
    future_stage_changes: list[dict[str, str]] = []
    for path in production_changed_files:
        stage = stage_for_changed_file(path)
        if not stage:
            continue
        if stage_index(stage) <= stage_index(current_stage):
            candidate_stages.append(stage)
        else:
            future_stage_changes.append({"file": path, "stage": stage, "stage_label": stage_label(stage)})
    rerun_from = min(candidate_stages, key=stage_index) if candidate_stages else None
    rebuild_needed = bool(rerun_from) and not needs_record and not diff.get("legacy_snapshot")
    plan: dict[str, Any] = {
        "kind": KIND_PLAN,
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "project_root": root,
        "project_title": load_meta(root).get("title") or os.path.basename(root),
        "progress": progress,
        "current_stage": current_stage,
        "current_stage_label": stage_label(current_stage),
        "current_todo": progress.get("current_todo"),
        "snapshot_path": snapshot_path(root),
        "baseline_status": (baseline or {}).get("status"),
        "baseline_bootstrapped": bootstrapped,
        "needs_record": needs_record,
        "legacy_snapshot": bool(diff.get("legacy_snapshot")),
        "relevant_skills": relevant_skills,
        "newly_relevant_skills": newly_relevant_skills,
        "changed_files": changed_files,
        "changed_skills": changed_skills,
        "observe_only_changed_skills": observe_only_changed,
        "production_changed_files": production_changed_files,
        "future_stage_changes": future_stage_changes,
        "deleted_files": diff.get("deleted_files") or [],
        "rebuild_needed": rebuild_needed,
        "rerun_from": rerun_from,
        "rerun_from_label": stage_label(rerun_from),
        "rerun_until": current_stage if rebuild_needed else None,
        "rerun_until_label": stage_label(current_stage) if rebuild_needed else "",
        "notes": [],
    }
    if needs_record:
        plan["notes"].append("当前项目没有内容基线；先 record，或去掉 --no-bootstrap 建立临时基线。")
    if bootstrapped:
        plan["notes"].append("本次 check 已建立临时基线；此前更早 skill 版本差异不可见。确认现状后请 record 固化。")
    if diff.get("legacy_snapshot"):
        plan["notes"].append("旧快照缺少文件内容表；请重新 record 建立内容基线。")
    if future_stage_changes:
        plan["notes"].append("部分变化只影响尚未开始的未来阶段，本次不要求返工。")
    if observe_only_changed and not production_changed_files:
        plan["notes"].append("本次变化只影响控制面，不要求广告返工。")
    plan["execution_steps"] = build_execution_steps(root, plan)
    plan["commands"] = [step["command"] for step in plan["execution_steps"] if step.get("type") == "command"]
    return plan


def format_todo(todo: Any) -> str:
    if not isinstance(todo, dict):
        return "未知"
    label = todo.get("stage_label") or "未知"
    skill = todo.get("skill")
    status = todo.get("status")
    parts = [str(label)]
    if skill:
        parts.append(str(skill))
    if status:
        parts.append(str(status))
    return " / ".join(parts)


def write_plan(root: str, plan: dict[str, Any]) -> tuple[str, str]:
    json_path, md_path = plan_paths(root)
    write_json(json_path, plan)
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    lines = [
        f"# {LINE_LABEL} skill 更新计划 — {plan.get('project_title')}",
        "",
        f"- 生成时间：{plan.get('generated_at')}",
        f"- 当前阶段上界：{plan.get('current_stage_label')} (`{plan.get('current_stage')}`)",
        f"- 当前前沿：{format_todo(plan.get('current_todo'))}",
        f"- 变更 skill：{', '.join(plan.get('changed_skills') or []) or '无'}",
        f"- 新纳入 skill：{', '.join(plan.get('newly_relevant_skills') or []) or '无'}",
        f"- 是否建议返工：{'是' if plan.get('rebuild_needed') else '否'}",
    ]
    if plan.get("rebuild_needed"):
        lines.append(f"- 建议回放：{plan.get('rerun_from_label')} → {plan.get('rerun_until_label')}")
    if plan.get("notes"):
        lines.extend(["", "## 备注"])
        lines.extend(f"- {note}" for note in plan["notes"])
    if plan.get("changed_files"):
        lines.extend(["", "## 变更文件"])
        lines.extend(f"- `{path}`" for path in plan["changed_files"][:80])
        if len(plan["changed_files"]) > 80:
            lines.append(f"- ... 另 {len(plan['changed_files']) - 80} 个")
    lines.extend(["", "## 建议步骤"])
    for step in plan.get("execution_steps") or []:
        if step.get("type") == "command":
            suffix = f"（{step.get('run_when')}）" if step.get("run_when") else ""
            lines.append(f"- 可执行命令{suffix}：`{step.get('command')}`")
        else:
            lines.append(f"- 人工/AI判断：{step.get('instruction')}")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines).rstrip() + "\n")
    return json_path, md_path


def command_record(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    progress = progress_context(root)
    current_stage = progress.get("current_stage") or (STAGE_ORDER[0] if STAGE_ORDER else "brief")
    snapshot = snapshot_for_skills(relevant_skills_for_stage(current_stage), status="recorded")
    snapshot["project_root"] = root
    snapshot["current_stage"] = current_stage
    snapshot["current_stage_label"] = stage_label(current_stage)
    write_json(snapshot_path(root), snapshot)
    print(f"[ok] recorded {LINE} skill snapshot: {snapshot_path(root)} ({snapshot['file_count']} files)")
    return 0


def command_check(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    plan = build_plan(root, bootstrap=not args.no_bootstrap)
    if args.write_plan:
        json_path, md_path = write_plan(root, plan)
        plan["written"] = {"json": json_path, "md": md_path}
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"[check] {LINE_LABEL} skill update: rebuild_needed={plan['rebuild_needed']} changed_skills={','.join(plan['changed_skills']) or 'none'}")
    print(f"[stage] current={plan['current_stage_label']} todo={format_todo(plan.get('current_todo'))}")
    if plan.get("rerun_from"):
        print(f"[plan] rerun {plan['rerun_from_label']} -> {plan['rerun_until_label']}")
    for note in plan.get("notes") or []:
        print(f"[note] {note}")
    if args.write_plan:
        print(f"[write] {plan['written']['json']}")
        print(f"[write] {plan['written']['md']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="拍广告 skill 更新影响扫描")
    sub = ap.add_subparsers(dest="cmd", required=True)
    rec = sub.add_parser("record", help="记录当前本线 skill 内容快照")
    rec.add_argument("project_root")
    rec.set_defaults(func=command_record)
    chk = sub.add_parser("check", help="检查本线 skill 更新是否影响项目")
    chk.add_argument("project_root")
    chk.add_argument("--write-plan", action="store_true")
    chk.add_argument("--json", action="store_true")
    chk.add_argument("--no-bootstrap", action="store_true", help="无基线时不自动建立临时快照")
    chk.set_defaults(func=command_check)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
