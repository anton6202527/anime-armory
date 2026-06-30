#!/usr/bin/env python3
"""Plan novel project rework after novel skill updates.

Pure standard-library helper. It records and compares content fingerprints for
the novel skill family, then writes a project-local rework plan.
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
NOVEL_LIB = os.path.join(REPO_SKILLS, "novel", "_lib")
if NOVEL_LIB not in sys.path:
    sys.path.insert(0, NOVEL_LIB)

try:  # noqa: E402
    from novel_route import cell_state, parse_progress, stage_of, summarize
except Exception:  # pragma: no cover - import failure is reported in progress parsing
    cell_state = None
    parse_progress = None
    stage_of = None
    summarize = None

try:  # noqa: E402
    from qa_gate import collect_gate_status
except Exception:  # pragma: no cover - gate is optional for update planning
    collect_gate_status = None

KIND_SNAPSHOT = "novel_skill_update_snapshot"
KIND_PLAN = "novel_skill_update_plan"
SCHEMA_VERSION = 1
SNAPSHOT_FILE = "novel_skill_update_snapshot.json"
PLAN_JSON = "novel_skill_update_plan.json"
PLAN_MD = "novel_skill_update_plan.md"

TEXT_SUFFIXES = {".md", ".py", ".sh", ".json"}
EXCLUDED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}

STAGE_ORDER = [
    "setup",
    "source_import",
    "blueprint",
    "setting",
    "title",
    "outline",
    "chapter_outline",
    "demo",
    "draft",
    "post_write",
    "mechanical_review",
    "human_review",
    "scoring",
    "rewrite",
    "revision",
    "export",
    "release_manifest",
    "screen_ready",
]

STAGE_LABELS = {
    "setup": "项目骨架",
    "source_import": "源书导入",
    "blueprint": "蓝图",
    "setting": "设定",
    "title": "书名",
    "outline": "大纲",
    "chapter_outline": "细纲",
    "demo": "Demo gate",
    "draft": "正文初稿",
    "post_write": "写后账本",
    "mechanical_review": "机检",
    "human_review": "审稿",
    "scoring": "评分",
    "rewrite": "改写",
    "revision": "修订计划",
    "export": "导出",
    "release_manifest": "发布版本清单",
    "screen_ready": "转制就绪检查",
}

MATRIX_LABEL_TO_STAGE = {
    "大纲": "outline",
    "细纲": "chapter_outline",
    "正文初稿": "draft",
    "机检": "mechanical_review",
    "审稿": "human_review",
    "评分": "scoring",
    "改写": "rewrite",
    "导出": "export",
}

STAGE_ALIASES = {
    "setting_bible": "setting",
    "source_model": "blueprint",
    "direction_spec": "setting",
    "rights_review": "source_import",
    "next_action": "source_import",
    "review": "human_review",
    "score": "scoring",
}

OBSERVE_ONLY_SKILLS = {
    "novel-batch",
    "novel-dashboard",
    "novel-progress",
    "novel-supervisor",
    "novel-update",
}

ALWAYS_RELEVANT_SKILLS = {"novel", "novel-craft"} | OBSERVE_ONLY_SKILLS

SKILL_DEFAULT_STAGE = {
    "novel": "setup",
    "novel-aesthetic": "setting",
    "novel-balance": "human_review",
    "novel-condense": "blueprint",
    "novel-continue": "draft",
    "novel-craft": "outline",
    "novel-create": "blueprint",
    "novel-edit": "revision",
    "novel-expand": "chapter_outline",
    "novel-feedback": "scoring",
    "novel-fetch": "source_import",
    "novel-localize": "export",
    "novel-observe": "setting",
    "novel-promote": "export",
    "novel-research": "setting",
    "novel-review": "mechanical_review",
    "novel-rewrite": "rewrite",
    "novel-score": "scoring",
    "novel-simulate": "scoring",
    "novel-spinoff": "blueprint",
    "novel-style": "setting",
    "novel-title": "title",
    "novel-wiki": "post_write",
}

FILE_STAGE_HINTS: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "novel": (
        ("source_import", ("scripts/import_novel.py",)),
        ("post_write", ("scripts/post_write.py", "_lib/power_system_defs.py")),
        ("human_review", ("novel-gate.py", "_lib/qa_gate.py")),
        ("draft", ("scripts/flow.py", "_lib/context_loader.py", "_lib/novel_pipeline.py")),
        ("setup", ("_lib/novel_contract.py", "_lib/novel_route.py", "progress.py")),
    ),
    "novel-craft": (
        ("release_manifest", ("scripts/release_manifest.py",)),
        ("export", ("scripts/export.py", "references/contract.md")),
        ("revision", ("scripts/revision_planner.py",)),
        (
            "human_review",
            (
                "scripts/qa_gate.py",
                "scripts/report_gate.py",
                "scripts/report_snapshot.py",
                "scripts/review_board.py",
                "references/qa-report-schema.md",
            ),
        ),
        (
            "draft",
            (
                "scripts/draft_packets.py",
                "scripts/draft_queue.py",
                "scripts/propose_state_delta.py",
                "scripts/reconcile_ledger.py",
                "references/chapter.md",
                "references/draft-pipeline.md",
                "references/trio-pipeline.md",
                "references/reader-contract.md",
            ),
        ),
        (
            "outline",
            (
                "scripts/scene_cards.py",
                "references/outline.md",
                "references/scene-cards.md",
                "references/story-skeleton.md",
            ),
        ),
        ("setting", ("references/setting-bible.md", "references/力量体系设计.md")),
    ),
}

STAGE_ITEM_RE = re.compile(r"^\s*-\s*\[([ xX])\]\s*(.*?)\s*<!--\s*stage:([a-z_]+)\s*-->")
KIND_RE = re.compile(r"novel-progress-schema:\s*\d+;\s*kind:\s*([a-zA-Z0-9_-]+)")


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


def skill_name_for_relpath(path: str) -> str | None:
    parts = path.split("/")
    if len(parts) >= 2 and parts[0] == "skills":
        return parts[1]
    return None


def stage_index(stage: str | None) -> int:
    if not stage:
        return 10**6
    normalized = STAGE_ALIASES.get(stage, stage)
    try:
        return STAGE_ORDER.index(normalized)
    except ValueError:
        return 10**6


def normalize_stage(stage: str | None) -> str | None:
    if not stage:
        return None
    return STAGE_ALIASES.get(stage, stage)


def stage_label(stage: str | None) -> str:
    stage = normalize_stage(stage)
    if not stage:
        return ""
    return STAGE_LABELS.get(stage, stage)


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
            path = os.path.join(dirpath, filename)
            suffix = os.path.splitext(filename)[1]
            relpath = rel(path)
            if suffix not in TEXT_SUFFIXES:
                continue
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
            files[relpath] = {
                "sha256": sha256_file(path),
                "size": os.path.getsize(path),
            }
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
    data = read_json(snapshot_path(root))
    if not data:
        return None
    return data


def relevant_skills_for_stage(stage: str | None) -> list[str]:
    idx = stage_index(stage)
    skills = set(ALWAYS_RELEVANT_SKILLS)
    for skill, skill_stage in SKILL_DEFAULT_STAGE.items():
        if stage_index(skill_stage) <= idx:
            skills.add(skill)
    return existing_skill_names(skills)


def progress_markdown_path(root: str) -> str:
    return os.path.join(root, "_进度.md")


def load_meta(root: str) -> dict[str, Any]:
    data = read_json(os.path.join(root, "_meta.json"))
    return data or {}


def parse_stage_checklist(root: str) -> dict[str, Any] | None:
    path = progress_markdown_path(root)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    text = open(path, encoding="utf-8").read()
    items = []
    for line in text.splitlines():
        match = STAGE_ITEM_RE.match(line)
        if not match:
            continue
        key = normalize_stage(match.group(3))
        items.append({
            "done": match.group(1).lower() == "x",
            "label": re.sub(r"\s+", " ", match.group(2)).strip(),
            "stage": key,
        })
    if not items:
        return None
    kind_match = KIND_RE.search(text)
    kind = kind_match.group(1) if kind_match else (load_meta(root).get("kind") or "unknown")
    done_items = [item for item in items if item["done"]]
    current_stage = done_items[-1]["stage"] if done_items else "setup"
    first_open = next((item for item in items if not item["done"]), None)
    return {
        "schema": "stage_checklist",
        "kind": kind,
        "current_stage": current_stage,
        "current_todo": {
            "stage_key": first_open["stage"] if first_open else None,
            "stage_label": first_open["label"] if first_open else "全部完成",
            "chapter": None,
            "skill": skill_for_stage(first_open["stage"]) if first_open else None,
            "command": f'python3 skills/novel/scripts/flow.py "{root}"' if first_open else None,
        },
        "stage_count": len(items),
        "done_count": len(done_items),
    }


def parse_matrix_progress(root: str) -> dict[str, Any]:
    if parse_progress is None or summarize is None or stage_of is None or cell_state is None:
        raise RuntimeError("novel progress parser unavailable")
    header, rows = parse_progress(root)
    matrix_stages = [label for label in MATRIX_LABEL_TO_STAGE if label in header]
    furthest: str | None = None
    started_cells = []
    for row in rows:
        chapter = row.get("_ch") or row.get("章节") or row.get("章") or ""
        for label in matrix_stages:
            state = cell_state(row.get(label, ""))
            if state in {"done", "flagged", "rough"}:
                stage = MATRIX_LABEL_TO_STAGE[label]
                started_cells.append({"chapter": chapter, "label": label, "stage": stage, "state": state})
                if furthest is None or stage_index(stage) > stage_index(furthest):
                    furthest = stage
    current_stage = furthest or "setup"
    summary = summarize(root)
    first = summary.get("first") if isinstance(summary, dict) else None
    todo: dict[str, Any]
    if isinstance(first, dict) and first.get("cmd"):
        todo_stage = MATRIX_LABEL_TO_STAGE.get(str(first.get("label") or ""))
        command = str(first.get("cmd") or "").format(root=root, ch=first.get("ch") or "")
        todo = {
            "stage_key": todo_stage,
            "stage_label": first.get("label"),
            "chapter": first.get("ch"),
            "skill": first.get("skill"),
            "command": command,
        }
    else:
        todo = {
            "stage_key": None,
            "stage_label": "全部完成",
            "chapter": None,
            "skill": None,
            "command": None,
        }
    return {
        "schema": "chapter_matrix",
        "kind": load_meta(root).get("kind") or "unknown",
        "current_stage": current_stage,
        "current_todo": todo,
        "chapter_count": len(rows),
        "done_count": summary.get("done") if isinstance(summary, dict) else None,
        "started_cells": started_cells,
    }


def progress_context(root: str) -> dict[str, Any]:
    try:
        return parse_matrix_progress(root)
    except Exception as matrix_error:
        checklist = parse_stage_checklist(root)
        if checklist:
            checklist["matrix_error"] = str(matrix_error)
            return checklist
        raise


def skill_for_stage(stage: str | None) -> str | None:
    stage = normalize_stage(stage)
    if stage in {"setup", "blueprint", "setting", "outline", "demo"}:
        return "novel-create"
    if stage == "source_import":
        return "novel-fetch"
    if stage == "title":
        return "novel-title"
    if stage == "chapter_outline":
        return "novel-expand"
    if stage in {"draft", "post_write"}:
        return "novel-continue"
    if stage in {"mechanical_review", "human_review"}:
        return "novel-review"
    if stage == "scoring":
        return "novel-score"
    if stage == "rewrite":
        return "novel-rewrite"
    if stage in {"revision", "export", "release_manifest", "screen_ready"}:
        return "novel-craft"
    return None


def stage_for_changed_file(relpath: str) -> str | None:
    skill = skill_name_for_relpath(relpath)
    if not skill or skill in OBSERVE_ONLY_SKILLS:
        return None
    for stage, tokens in FILE_STAGE_HINTS.get(skill, ()):
        if any(token in relpath for token in tokens):
            return normalize_stage(stage)
    return normalize_stage(SKILL_DEFAULT_STAGE.get(skill))


def changed_files_since(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    old_files = baseline.get("files")
    if not isinstance(old_files, dict):
        return {
            "legacy_snapshot": True,
            "changed_files": [],
            "newly_relevant_files": [],
            "deleted_files": [],
        }
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


def summarize_qa_gate(root: str) -> dict[str, Any]:
    if collect_gate_status is None:
        return {"status": "unavailable", "blocking_count": 0, "blockers": []}
    try:
        gate = collect_gate_status(root)
    except Exception as exc:
        return {"status": "error", "error": str(exc), "blocking_count": 0, "blockers": []}
    blockers = gate.get("blockers") or []
    out_blockers = []
    for item in blockers[:12]:
        if isinstance(item, dict):
            out_blockers.append({
                "id": item.get("id") or item.get("code") or "",
                "stage": item.get("stage") or "",
                "skill": item.get("skill") or item.get("recommended_skill") or "",
                "reason": item.get("reason") or item.get("message") or item.get("problem") or "",
            })
        else:
            out_blockers.append({"id": "", "stage": "", "skill": "", "reason": str(item)})
    return {
        "status": "blocking" if gate.get("blocking") else "ok",
        "blocking_count": len(blockers),
        "blockers": out_blockers,
    }


def build_execution_steps(root: str, plan: dict[str, Any]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if not plan.get("rebuild_needed"):
        steps.append({
            "type": "command",
            "purpose": "查看当前前沿",
            "command": f'python3 skills/novel-progress/scan.py "{root}"',
        })
        if plan.get("changed_skills"):
            steps.append({
                "type": "command",
                "purpose": "接受当前产物后记录新基线",
                "command": f'python3 skills/novel-update/scripts/update_plan.py record "{root}"',
                "run_when": "用户确认无需返工",
            })
        return steps

    rerun_from = plan.get("rerun_from")
    if stage_index(rerun_from) <= stage_index("draft"):
        steps.append({
            "type": "agent_step",
            "purpose": "保留当前正文",
            "instruction": "返工会触及大纲/细纲/正文；执行前先用 story_vcs 或项目既有归档方式保留当前文本。",
        })
    steps.append({
        "type": "agent_step",
        "purpose": "确认返工范围",
        "instruction": f"向用户确认从 {stage_label(rerun_from)} 回放到 {stage_label(plan.get('rerun_until'))}，再进入对应 novel skill。",
    })
    steps.append({
        "type": "command",
        "purpose": "按 novel 调度续跑",
        "command": f'python3 skills/novel/scripts/flow.py "{root}"',
        "run_when": "用户确认返工",
    })
    steps.append({
        "type": "command",
        "purpose": "刷新生产控制台",
        "command": f'python3 skills/novel-dashboard/scripts/dashboard.py "{root}" --write',
        "run_when": "返工后",
    })
    steps.append({
        "type": "command",
        "purpose": "验收后记录新基线",
        "command": f'python3 skills/novel-update/scripts/update_plan.py record "{root}"',
        "run_when": "返工产物验收通过",
    })
    return steps


def build_plan(root: str, *, bootstrap: bool = True) -> dict[str, Any]:
    root = os.path.abspath(root)
    progress = progress_context(root)
    current_stage = normalize_stage(progress.get("current_stage")) or "setup"
    relevant_skills = relevant_skills_for_stage(current_stage)
    baseline = load_snapshot(root)
    bootstrapped = False
    needs_record = False
    if baseline is None:
        if not bootstrap:
            needs_record = True
            baseline = None
        else:
            baseline = snapshot_for_skills(relevant_skills, status="bootstrap")
            write_json(snapshot_path(root), baseline)
            bootstrapped = True

    current_snapshot = snapshot_for_skills(relevant_skills, status="current")
    if baseline is None:
        diff = {"legacy_snapshot": False, "changed_files": [], "newly_relevant_files": [], "deleted_files": []}
    else:
        diff = changed_files_since(baseline, current_snapshot)

    changed_files = diff["changed_files"]
    changed_skills = sorted({skill_name_for_relpath(path) for path in changed_files if skill_name_for_relpath(path)})
    baseline_skills = set((baseline or {}).get("relevant_skills") or [])
    newly_relevant_skills = sorted(set(relevant_skills) - baseline_skills)
    observe_only_changed = sorted(skill for skill in changed_skills if skill in OBSERVE_ONLY_SKILLS)
    production_changed_files = [path for path in changed_files if skill_name_for_relpath(path) not in OBSERVE_ONLY_SKILLS]
    future_stage_changes: list[dict[str, str]] = []
    candidate_stages: list[str] = []
    for path in production_changed_files:
        stage = stage_for_changed_file(path)
        if stage is None:
            continue
        if stage_index(stage) <= stage_index(current_stage):
            candidate_stages.append(stage)
        else:
            future_stage_changes.append({"file": path, "stage": stage, "stage_label": stage_label(stage)})

    rerun_from = min(candidate_stages, key=stage_index) if candidate_stages else None
    rebuild_needed = bool(rerun_from) and not needs_record and not diff.get("legacy_snapshot")
    qa_gate = summarize_qa_gate(root)
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
        "qa_gate": qa_gate,
        "notes": [],
    }
    if needs_record:
        plan["notes"].append("当前项目没有内容基线；先 record 或允许 check bootstrap 后，才能检测后续 skill 变化。")
    if bootstrapped:
        plan["notes"].append("本次 check 已建立临时基线；此前更早 skill 版本差异不可见。确认现状后请 record 固化。")
    if diff.get("legacy_snapshot"):
        plan["notes"].append("旧快照缺少文件内容表；请重新 record 建立内容基线。")
    if future_stage_changes:
        plan["notes"].append("部分变化只影响尚未开始的未来阶段，本次不要求返工。")
    if observe_only_changed and not production_changed_files:
        plan["notes"].append("本次变化只影响控制面，不要求正文返工。")
    plan["execution_steps"] = build_execution_steps(root, plan)
    plan["commands"] = [s["command"] for s in plan["execution_steps"] if s.get("type") == "command"]
    return plan


def write_plan(root: str, plan: dict[str, Any]) -> tuple[str, str]:
    json_path, md_path = plan_paths(root)
    write_json(json_path, plan)
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    lines = [
        f"# novel skill 更新计划 — {plan.get('project_title')}",
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
    gate = plan.get("qa_gate") or {}
    lines.append(f"- QA gate：{gate.get('status')}，阻断 {gate.get('blocking_count', 0)} 项")
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


def format_todo(todo: Any) -> str:
    if not isinstance(todo, dict):
        return "未知"
    label = todo.get("stage_label") or "未知"
    chapter = todo.get("chapter")
    skill = todo.get("skill")
    parts = [str(label)]
    if chapter:
        parts.append(str(chapter))
    if skill:
        parts.append(str(skill))
    return " / ".join(parts)


def command_record(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    progress = progress_context(root)
    current_stage = normalize_stage(progress.get("current_stage")) or "setup"
    skills = relevant_skills_for_stage(current_stage)
    snapshot = snapshot_for_skills(skills, status="recorded")
    snapshot["project_root"] = root
    snapshot["current_stage"] = current_stage
    snapshot["current_stage_label"] = stage_label(current_stage)
    write_json(snapshot_path(root), snapshot)
    print(f"[ok] recorded novel skill snapshot: {snapshot_path(root)} ({snapshot['file_count']} files)")
    return 0


def command_check(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    plan = build_plan(root, bootstrap=not args.no_bootstrap)
    written: tuple[str, str] | None = None
    if args.write_plan:
        written = write_plan(root, plan)
        plan["written_plan"] = {"json": written[0], "md": written[1]}
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"[check] current_stage={plan['current_stage']} changed_skills={','.join(plan['changed_skills']) or 'none'}")
        print(f"[check] rebuild_needed={str(plan['rebuild_needed']).lower()} rerun_from={plan.get('rerun_from') or '-'}")
        if plan.get("baseline_bootstrapped"):
            print("[check] baseline_bootstrapped=true; confirm current artifacts then run record")
        if plan.get("notes"):
            for note in plan["notes"]:
                print(f"[note] {note}")
        if written:
            print(f"[write] {written[0]}")
            print(f"[write] {written[1]}")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="novel skill 更新影响扫描与返工计划")
    sub = parser.add_subparsers(dest="cmd", required=True)

    check = sub.add_parser("check", help="对比当前 novel skills 与项目基线，生成计划")
    check.add_argument("project_root")
    check.add_argument("--write-plan", action="store_true", help="写入 生产数据/novel_skill_update_plan.{json,md}")
    check.add_argument("--json", action="store_true", help="输出 JSON")
    check.add_argument("--no-bootstrap", action="store_true", help="无基线时不自动建立临时基线")
    check.set_defaults(func=command_check)

    record = sub.add_parser("record", help="记录当前 novel skill 内容快照")
    record.add_argument("project_root")
    record.set_defaults(func=command_record)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
