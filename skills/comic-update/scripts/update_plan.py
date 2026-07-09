#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plan comic project rework after comic skill updates.

Pure standard-library helper. It records and compares content fingerprints for
the comic skill family, and also detects legacy workflow gaps that predate
current comic stages.
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

LINE = "comic"
LINE_LABEL = "画漫画"
KIND_SNAPSHOT = "comic_skill_update_snapshot"
KIND_PLAN = "comic_skill_update_plan"
SCHEMA_VERSION = 1
SNAPSHOT_FILE = "comic_skill_update_snapshot.json"
PLAN_JSON = "comic_skill_update_plan.json"
PLAN_MD = "comic_skill_update_plan.md"
TEXT_SUFFIXES = {".md", ".py", ".sh", ".json", ".html"}
EXCLUDED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
PARTIAL_RE = re.compile(r"(\d+)\s*/\s*(\d+)")

STAGE_ORDER = [
    "source",
    "script",
    "name",
    "layout",
    "finishing",
    "image_jobs",
    "image",
    "compose",
    "review",
]
STAGE_LABELS = {
    "source": "源本/企划",
    "script": "漫画脚本",
    "name": "缩略分镜",
    "layout": "页面排版",
    "finishing": "原稿收尾",
    "image_jobs": "出图包",
    "image": "出图",
    "compose": "嵌字合成",
    "review": "审查",
}
LABEL_TO_STAGE = {
    "源本/企划": "source",
    "源本": "source",
    "企划": "source",
    "漫画脚本": "script",
    "脚本": "script",
    "缩略分镜": "name",
    "ネーム": "name",
    "name": "name",
    "页面排版": "layout",
    "排版": "layout",
    "原稿收尾": "finishing",
    "传统收尾": "finishing",
    "出图包": "image_jobs",
    "出图": "image",
    "嵌字合成": "compose",
    "合成": "compose",
    "审查": "review",
    "质检": "review",
}
OBSERVE_ONLY_SKILLS = {"comic-progress", "comic-settings", "comic-update"}
ALWAYS_RELEVANT_SKILLS = {"comic"} | OBSERVE_ONLY_SKILLS
SKILL_DEFAULT_STAGE = {
    "comic": "source",
    "comic-script": "script",
    "comic-name": "name",
    "comic-layout": "layout",
    "comic-finishing": "finishing",
    "comic-identity": "image_jobs",
    "comic-image": "image_jobs",
    "comic-batch": "image",
    "comic-compose": "compose",
    "comic-review": "review",
    "comic-progress": "source",
    "comic-settings": "source",
    "comic-update": "source",
}
FILE_STAGE_HINTS: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "comic": (
        ("compose", ("platform_profiles.py", "text_metadata.py")),
        ("image_jobs", ("image_backend_adapter.py", "视觉风格候选", "选择点与偏好")),
        ("source", ("init_project.py", "architecture.md")),
    ),
    "comic-image": (
        ("image", ("codex_panel_runner.py", "panel_qc", "detect_image_backend.py")),
        ("image_jobs", ("build_panel_jobs.py", "prompt_job_schema.md", "prompt")),
    ),
    "comic-review": (
        ("review", ("review.py", "gate.py", "style_consistency.py", "character_consistency.py")),
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
    if "✅" in raw or "[x]" in low or low in {"done", "pass", "完成"}:
        return "done"
    match = PARTIAL_RE.search(raw)
    if match:
        current = int(match.group(1))
        total = int(match.group(2))
        if total > 0 and current >= total:
            return "done"
        if current > 0:
            return "partial"
    if "⏳" in raw or "rough" in low or "draft" in low or "block" in low or "🔴" in raw:
        return "partial"
    if not raw or raw in {"⬜", "[ ]"}:
        return "todo"
    return "partial"


def parse_markdown_table(path: str) -> list[dict[str, str]]:
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    rows: list[dict[str, str]] = []
    headers: list[str] = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table:
                in_table = False
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells:
            continue
        if cells[0] == "话":
            headers = cells
            in_table = True
            continue
        if in_table and all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        if in_table and headers and len(cells) >= len(headers):
            rows.append(dict(zip(headers, cells)))
    return rows


def parse_progress(root: str) -> list[dict[str, str]]:
    path = os.path.join(root, "_进度.md")
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    return parse_markdown_table(path)


def panel_script_summary(root: str, chapter: str) -> dict[str, Any]:
    path = os.path.join(root, "脚本", chapter, "panel_script.json")
    data = read_json(path)
    if not data:
        return {"path": path, "exists": os.path.isfile(path), "valid_json": False}
    panels = data.get("panels") if isinstance(data.get("panels"), list) else []
    return {
        "path": path,
        "exists": True,
        "valid_json": True,
        "has_visual_contract": isinstance(data.get("visual_contract"), dict) and bool(data.get("visual_contract")),
        "panel_count": len(panels),
    }


def latest_gate_summary(root: str, chapter: str, stage: str = "review") -> dict[str, Any] | None:
    path = os.path.join(root, "生产数据", f"comic_gate_{stage}_{chapter}.json")
    data = read_json(path)
    if not data:
        return None
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    return {
        "path": path,
        "verdict": data.get("verdict"),
        "block_count": int(summary.get("block_count") or 0),
        "warn_count": int(summary.get("warn_count") or 0),
    }


def artifact_gaps(root: str, chapter: str, current_stage: str) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    if stage_index(current_stage) >= stage_index("script"):
        script = panel_script_summary(root, chapter)
        if not script.get("exists") or not script.get("valid_json"):
            gaps.append({
                "chapter": chapter,
                "stage": "script",
                "severity": "block",
                "code": "panel_script_missing_or_invalid",
                "artifact": os.path.relpath(script["path"], root).replace(os.sep, "/"),
                "reason": "漫画脚本缺失或不可解析。",
            })
        elif not script.get("has_visual_contract"):
            gaps.append({
                "chapter": chapter,
                "stage": "script",
                "severity": "block",
                "code": "visual_contract_missing",
                "artifact": os.path.relpath(script["path"], root).replace(os.sep, "/"),
                "reason": "panel_script 缺少新版必需的 visual_contract。",
            })
    if stage_index(current_stage) >= stage_index("name"):
        path = os.path.join(root, "排版", chapter, "name_board.json")
        if not os.path.isfile(path):
            gaps.append({
                "chapter": chapter,
                "stage": "name",
                "severity": "warn",
                "code": "name_board_missing",
                "artifact": os.path.relpath(path, root).replace(os.sep, "/"),
                "reason": "已推进到后续阶段，但缺少缩略分镜/name_board。",
            })
    if stage_index(current_stage) >= stage_index("finishing"):
        path = os.path.join(root, "出图", chapter, "finishing", "finishing_plan.json")
        if not os.path.isfile(path):
            gaps.append({
                "chapter": chapter,
                "stage": "finishing",
                "severity": "warn",
                "code": "finishing_plan_missing",
                "artifact": os.path.relpath(path, root).replace(os.sep, "/"),
                "reason": "已推进到出图/合成/审查，但缺少原稿收尾计划。",
            })
    gate = latest_gate_summary(root, chapter)
    if gate and gate.get("block_count", 0) > 0:
        gaps.append({
            "chapter": chapter,
            "stage": "review",
            "severity": "block",
            "code": "review_gate_block",
            "artifact": os.path.relpath(str(gate["path"]), root).replace(os.sep, "/"),
            "reason": f"最近 review gate 仍有 {gate['block_count']} 个阻断。",
            "gate": gate,
        })
    return gaps


def progress_context(root: str) -> dict[str, Any]:
    raw_rows = parse_progress(root)
    normalized_rows: list[dict[str, Any]] = []
    headers = list(raw_rows[0].keys()) if raw_rows else []
    stage_columns = {LABEL_TO_STAGE[h]: h for h in headers if h in LABEL_TO_STAGE}
    missing_stage_columns = [stage for stage in STAGE_ORDER if stage not in stage_columns]
    for row in raw_rows:
        chapter = row.get("话", "未命名")
        current_stage = "source"
        first_open: dict[str, Any] | None = None
        stage_states: dict[str, dict[str, str]] = {}
        for stage in STAGE_ORDER:
            label = stage_columns.get(stage)
            status = row.get(label, "") if label else ""
            state = "missing_column" if label is None else state_of(status)
            stage_states[stage] = {"label": stage_label(stage), "status": status, "state": state}
            if label is not None and state != "todo" and stage_index(stage) > stage_index(current_stage):
                current_stage = stage
        for stage in STAGE_ORDER:
            item = stage_states[stage]
            if item["state"] == "missing_column" and stage_index(current_stage) > stage_index(stage):
                first_open = {
                    "stage_key": stage,
                    "stage_label": stage_label(stage),
                    "status": "missing_column",
                    "skill": SKILL_FOR_STAGE.get(stage),
                }
                break
            if item["state"] not in {"done", "missing_column"}:
                first_open = {
                    "stage_key": stage,
                    "stage_label": stage_label(stage),
                    "status": item["status"],
                    "skill": SKILL_FOR_STAGE.get(stage),
                }
                break
        gaps = artifact_gaps(root, chapter, current_stage)
        normalized_rows.append({
            "chapter": chapter,
            "current_stage": current_stage,
            "current_stage_label": stage_label(current_stage),
            "current_todo": first_open or {
                "stage_key": None,
                "stage_label": "全部完成",
                "status": "",
                "skill": "comic-review",
            },
            "stage_states": stage_states,
            "artifact_gaps": gaps,
        })
    current_stage = max((row["current_stage"] for row in normalized_rows), key=stage_index, default="source")
    first_open_project = next((row["current_todo"] for row in normalized_rows if row["current_todo"]["stage_key"]), None)
    all_gaps = [gap for row in normalized_rows for gap in row["artifact_gaps"]]
    return {
        "schema": "chapter_table",
        "kind": load_meta(root).get("kind") or LINE,
        "current_stage": current_stage,
        "current_stage_label": stage_label(current_stage),
        "current_todo": first_open_project or {
            "stage_key": None,
            "stage_label": "全部完成",
            "status": "",
            "skill": "comic-review",
        },
        "stage_count": len(STAGE_ORDER),
        "chapter_count": len(normalized_rows),
        "missing_stage_columns": missing_stage_columns,
        "artifact_gaps": all_gaps,
        "rows": normalized_rows,
    }


SKILL_FOR_STAGE = {
    "source": "comic-script",
    "script": "comic-script",
    "name": "comic-name",
    "layout": "comic-layout",
    "finishing": "comic-finishing",
    "image_jobs": "comic-image",
    "image": "comic-image",
    "compose": "comic-compose",
    "review": "comic-review",
}


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


def affected_chapters(progress: dict[str, Any], rerun_from: str | None, *, force_project_scope: bool = False) -> list[dict[str, Any]]:
    if not rerun_from:
        return []
    chapters: list[dict[str, Any]] = []
    for row in progress.get("rows") or []:
        current_stage = row.get("current_stage")
        gaps = [gap for gap in row.get("artifact_gaps") or [] if stage_index(gap.get("stage")) >= stage_index(rerun_from)]
        own_gap_stages = [gap.get("stage") for gap in row.get("artifact_gaps") or [] if gap.get("stage")]
        if own_gap_stages:
            chapter_rerun_from = min(own_gap_stages, key=stage_index)
            if force_project_scope and stage_index(rerun_from) < stage_index(chapter_rerun_from):
                chapter_rerun_from = rerun_from
        else:
            chapter_rerun_from = rerun_from
        if force_project_scope and stage_index(current_stage) >= stage_index(rerun_from):
            include = True
        else:
            include = bool(own_gap_stages)
        if include:
            chapters.append({
                "chapter": row.get("chapter"),
                "current_stage": current_stage,
                "current_stage_label": stage_label(current_stage),
                "rerun_from": chapter_rerun_from,
                "rerun_from_label": stage_label(chapter_rerun_from),
                "rerun_until": current_stage,
                "rerun_until_label": stage_label(current_stage),
                "gaps": gaps,
            })
    return chapters


def build_execution_steps(root: str, plan: dict[str, Any]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if not plan.get("rebuild_needed"):
        steps.append({"type": "command", "purpose": "查看当前前沿", "command": f'python3 skills/comic-progress/scripts/scan.py "{root}"'})
        if plan.get("changed_skills") or plan.get("baseline_bootstrapped"):
            steps.append({
                "type": "command",
                "purpose": "接受当前产物后记录新基线",
                "command": f'python3 skills/comic-update/scripts/update_plan.py record "{root}"',
                "run_when": "用户确认无需重制",
            })
        return steps

    steps.append({
        "type": "agent_step",
        "purpose": "保留当前产物",
        "instruction": "重制前先保留当前 panel_script/layout/panel_jobs/成图/导出物；旧图进入 candidates 或废料目录，不无痕覆盖。",
    })
    for chapter in plan.get("affected_chapters") or []:
        ch = chapter.get("chapter")
        rerun_from = chapter.get("rerun_from") or plan.get("rerun_from")
        if stage_index(rerun_from) <= stage_index("script"):
            steps.append({
                "type": "agent_step",
                "purpose": f"{ch} 修订漫画脚本",
                "instruction": f"按 comic-script 补齐 {ch} 的 visual_contract、逐格场景锚/视线/完整性/站位字段。",
            })
        if stage_index(rerun_from) <= stage_index("name"):
            steps.append({"type": "command", "purpose": f"{ch} 生成缩略分镜", "command": f'python3 skills/comic-name/scripts/build_name_board.py "{root}" --chapter {ch}'})
        if stage_index(rerun_from) <= stage_index("layout"):
            steps.append({"type": "command", "purpose": f"{ch} 重建页面排版", "command": f'python3 skills/comic-layout/scripts/build_layout.py "{root}" --chapter {ch}'})
        if stage_index(rerun_from) <= stage_index("finishing"):
            steps.append({"type": "command", "purpose": f"{ch} 生成原稿收尾计划", "command": f'python3 skills/comic-finishing/scripts/build_finishing_plan.py "{root}" --chapter {ch}'})
        if stage_index(rerun_from) <= stage_index("image_jobs"):
            steps.append({"type": "command", "purpose": f"{ch} 重建出图包", "command": f'python3 skills/comic-image/scripts/build_panel_jobs.py "{root}" --chapter {ch}'})
        if stage_index(chapter.get("current_stage")) >= stage_index("image"):
            steps.append({
                "type": "agent_step",
                "purpose": f"{ch} 评估是否重出图",
                "instruction": "正式重出 PNG 前确认模型、渠道、预算和目标格；若只改便宜结构层，先跑 image gate 判断旧图是否可保留。",
            })
            steps.append({"type": "command", "purpose": f"{ch} 出图前 gate", "command": f'python3 skills/comic-review/scripts/gate.py "{root}" --chapter {ch} --stage image_preflight'})
        if stage_index(chapter.get("current_stage")) >= stage_index("compose"):
            steps.append({
                "type": "agent_step",
                "purpose": f"{ch} 重建嵌字/导出",
                "instruction": f"若 layout 或面板图变化，重新运行 comic-compose 生成 {ch} 的 lettering、页面图和长图。",
            })
        steps.append({"type": "command", "purpose": f"{ch} 重制后审查 gate", "command": f'python3 skills/comic-review/scripts/gate.py "{root}" --chapter {ch} --stage review'})
    steps.append({
        "type": "command",
        "purpose": "验收后记录新基线",
        "command": f'python3 skills/comic-update/scripts/update_plan.py record "{root}"',
        "run_when": "重制产物验收通过",
    })
    return steps


def build_plan(root: str, *, bootstrap: bool = True) -> dict[str, Any]:
    root = os.path.abspath(root)
    progress = progress_context(root)
    current_stage = progress.get("current_stage") or "source"
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
    structural_gaps = progress.get("artifact_gaps") or []
    candidate_stages.extend(gap["stage"] for gap in structural_gaps if gap.get("stage"))
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
        "structural_gaps": structural_gaps,
        "rebuild_needed": rebuild_needed,
        "rerun_from": rerun_from,
        "rerun_from_label": stage_label(rerun_from),
        "rerun_until": current_stage if rebuild_needed else None,
        "rerun_until_label": stage_label(current_stage) if rebuild_needed else "",
        "notes": [],
    }
    plan["affected_chapters"] = affected_chapters(progress, rerun_from, force_project_scope=bool(production_changed_files)) if rebuild_needed else []
    if needs_record:
        plan["notes"].append("当前项目没有内容基线；先 record，或去掉 --no-bootstrap 建立临时基线。")
    if bootstrapped:
        plan["notes"].append("本次 check 已建立临时基线；此前更早 skill 版本差异不可见。")
    if structural_gaps:
        plan["notes"].append("项目存在新版 comic 流程缺口；即使没有历史快照，也建议按缺口回放。")
    if diff.get("legacy_snapshot"):
        plan["notes"].append("旧快照缺少文件内容表；请重新 record 建立内容基线。")
    if future_stage_changes:
        plan["notes"].append("部分变化只影响尚未开始的未来阶段，本次不要求重制。")
    if observe_only_changed and not production_changed_files and not structural_gaps:
        plan["notes"].append("本次变化只影响控制面，不要求漫画产物重制。")
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
        f"- 结构缺口：{len(plan.get('structural_gaps') or [])}",
        f"- 是否建议重制：{'是' if plan.get('rebuild_needed') else '否'}",
    ]
    if plan.get("rebuild_needed"):
        lines.append(f"- 建议回放：{plan.get('rerun_from_label')} → {plan.get('rerun_until_label')}")
        affected = "、".join(str(item.get("chapter")) for item in plan.get("affected_chapters") or [])
        lines.append(f"- 受影响话别：{affected or '无'}")
    if plan.get("notes"):
        lines.extend(["", "## 备注"])
        lines.extend(f"- {note}" for note in plan["notes"])
    if plan.get("structural_gaps"):
        lines.extend(["", "## 结构缺口"])
        for gap in plan["structural_gaps"][:80]:
            lines.append(
                f"- `{gap.get('chapter')}` `{stage_label(gap.get('stage'))}` {gap.get('severity')}: "
                f"{gap.get('code')} — {gap.get('reason')}（{gap.get('artifact')}）"
            )
        if len(plan["structural_gaps"]) > 80:
            lines.append(f"- ... 另 {len(plan['structural_gaps']) - 80} 个")
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
    current_stage = progress.get("current_stage") or "source"
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
    if plan.get("affected_chapters"):
        print("[chapters] " + ",".join(str(item.get("chapter")) for item in plan["affected_chapters"]))
    for note in plan.get("notes") or []:
        print(f"[note] {note}")
    if args.write_plan:
        print(f"[write] {plan['written']['json']}")
        print(f"[write] {plan['written']['md']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="画漫画 skill 更新影响扫描")
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
