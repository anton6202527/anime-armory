#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Executable pipeline registry for the novel skill family.

This is the workflow layer between prose SKILL.md instructions and individual
stage scripts.  It is intentionally deterministic: it declares what a stage
needs, what it may produce, which gate owns it, whether semantic judgement is
needed, and whether an orchestrator may run it in parallel.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
from copy import deepcopy
from datetime import date, datetime
from typing import Any


PIPELINE_REGISTRY_KIND = "novel_pipeline_registry"
PIPELINE_PLAN_KIND = "novel_pipeline_dry_run_plan"
ARTIFACT_GRAPH_KIND = "novel_artifact_graph"
HANDOFF_CONTRACT_KIND = "novel_specialist_handoff_contract"
PIPELINE_REGISTRY_VERSION = 1


PIPELINE_REGISTRY: list[dict[str, Any]] = [
    {
        "key": "setup",
        "label": "项目骨架",
        "owner": "novel dispatcher / init_project",
        "inputs": [],
        "outputs": ["_meta.json", "_设置.md", "_进度.md"],
        "gate": "deterministic",
        "cost_level": "free",
        "semantic_required": False,
        "can_parallel": False,
        "rollback": "删除新建项目目录或恢复上一版 _meta/_设置/_进度。",
        "agent_role": "workflow_orchestrator",
    },
    {
        "key": "source_import",
        "label": "源书导入",
        "owner": "novel/scripts/import_novel.py / novel-fetch",
        "applicable_kinds": ["import", "rewrite", "continue", "expand", "condense", "spinoff"],
        "inputs": ["原作.txt", "小说/source_manifest.json"],
        "input_policy": "any",
        "outputs": ["原作.txt", "小说/source_manifest.json"],
        "gate": "rights",
        "cost_level": "free",
        "semantic_required": False,
        "can_parallel": False,
        "rollback": "恢复上一版 原作.txt 与 source_manifest.json。",
        "agent_role": "workflow_orchestrator",
    },
    {
        "key": "author_workflow",
        "label": "作者成书默认工作流",
        "owner": "novel-craft/scripts/author_workflow.py",
        "inputs": ["_meta.json", "_设置.md", "_进度.md"],
        "outputs": ["生产数据/author_workflow.json", "生产数据/作者成书流程.md"],
        "gate": "deterministic workflow status",
        "cost_level": "free",
        "semantic_required": False,
        "can_parallel": False,
        "rollback": "重跑 author_workflow.py；不修改正文或进度。",
        "agent_role": "workflow_orchestrator",
    },
    {
        "key": "author_intent",
        "label": "作者意图档案",
        "owner": "novel-craft/scripts/author_intent.py",
        "inputs": ["_meta.json", "_设置.md"],
        "outputs": ["设定/author_intent.json", "设定/作者意图.md"],
        "gate": "author intent completeness",
        "cost_level": "free",
        "semantic_required": False,
        "can_parallel": False,
        "rollback": "修订 author_intent.json / 作者意图.md；后续蓝图与读者契约需对齐。",
        "agent_role": "workflow_orchestrator",
    },
    {
        "key": "blueprint",
        "label": "蓝图/方向规格",
        "owner": "novel-create / novel-rewrite / derive skill",
        "inputs": ["_meta.json", "设定/author_intent.json"],
        "outputs": ["设定/蓝图.md", "设定/改动spec.md", "设定/方向spec.md"],
        "output_policy": "any",
        "gate": "human-choice",
        "cost_level": "semantic",
        "semantic_required": True,
        "can_parallel": False,
        "rollback": "回滚设定/蓝图或改动spec，并重跑后续依赖阶段。",
        "agent_role": "specialist_writer",
    },
    {
        "key": "setting",
        "label": "设定圣经",
        "owner": "novel-create / novel-craft",
        "inputs": ["设定/蓝图.md", "设定/改动spec.md", "设定/方向spec.md"],
        "input_policy": "any",
        "outputs": ["设定/角色卡.md", "设定/世界观.md", "设定/读者契约.md"],
        "gate": "deterministic + semantic review",
        "cost_level": "semantic",
        "semantic_required": True,
        "can_parallel": False,
        "rollback": "回设定源文件修正；后续章纲/任务包需重出。",
        "agent_role": "specialist_writer",
    },
    {
        "key": "outline",
        "label": "章纲/场景卡",
        "owner": "novel-craft/scripts/scene_cards.py",
        "inputs": ["设定/角色卡.md", "设定/读者契约.md"],
        "outputs": ["设定/章纲.md", "设定/scene_cards.json"],
        "output_policy": "any",
        "gate": "deterministic",
        "cost_level": "free",
        "semantic_required": False,
        "can_parallel": False,
        "rollback": "重写章纲/scene_cards，已生成写章包需刷新。",
        "agent_role": "workflow_orchestrator",
    },
    {
        "key": "evidence_prep",
        "label": "资料/观察/审美准备",
        "owner": "novel-research / novel-observe / novel-aesthetic",
        "inputs": ["设定/读者契约.md", "设定/章纲.md"],
        "input_policy": "any",
        "outputs": ["资料/research_jobs.json", "资料/research_sources.json", "资料/research_scene_usage.json", "素材/观察素材库.md", "设定/aesthetic_bank.json"],
        "output_policy": "any",
        "gate": "research/observation/aesthetic readiness",
        "cost_level": "search+free",
        "semantic_required": False,
        "can_parallel": True,
        "rollback": "更新资料包、观察素材或审美样本；已生成写章包需刷新。",
        "agent_role": "workflow_orchestrator",
    },
    {
        "key": "manuscript_map",
        "label": "结构地图",
        "owner": "novel-craft/scripts/manuscript_map.py",
        "inputs": ["设定/章纲.md", "设定/scene_cards.json"],
        "input_policy": "any",
        "outputs": ["设定/manuscript_map.json", "设定/manuscript_map.md"],
        "gate": "manuscript map completeness",
        "cost_level": "free",
        "semantic_required": False,
        "can_parallel": False,
        "rollback": "修订章纲/scene_cards 后重跑 manuscript_map.py。",
        "agent_role": "workflow_orchestrator",
    },
    {
        "key": "demo",
        "label": "Demo 章与 Demo Gate",
        "owner": "novel-review",
        "inputs": ["章节/第*.md", "设定/读者契约.md"],
        "outputs": ["审稿/demo_gate.json"],
        "gate": "semantic review",
        "cost_level": "semantic",
        "semantic_required": True,
        "can_parallel": False,
        "rollback": "回蓝图/设定/开篇章重写后重跑 demo gate。",
        "agent_role": "specialist_reviewer",
    },
    {
        "key": "demo_readiness",
        "label": "Demo 双评分放量闸门",
        "owner": "novel-craft/scripts/demo_readiness.py",
        "inputs": ["审稿/demo_gate.json", "章节/第*.md"],
        "outputs": ["审稿/demo_readiness.json", "审稿/demo_readiness.md"],
        "gate": "commercial + literary demo readiness",
        "cost_level": "free",
        "semantic_required": False,
        "can_parallel": False,
        "rollback": "回开篇/score/aesthetic 修正后重跑 demo_readiness。",
        "agent_role": "workflow_orchestrator",
    },
    {
        "key": "draft",
        "label": "批量写章",
        "owner": "novel-craft/scripts/draft_packets.py",
        "inputs": ["设定/章纲.md", "设定/读者契约.md"],
        "outputs": ["写作任务/第*.md", "章节/第*.md"],
        "output_policy": "any",
        "gate": "drafting preflight",
        "cost_level": "semantic",
        "semantic_required": True,
        "can_parallel": True,
        "rollback": "按章节回滚；state_delta/state_ledger 必须同步处理。",
        "agent_role": "specialist_writer",
    },
    {
        "key": "post_write",
        "label": "写后账本闭环",
        "owner": "novel/scripts/post_write.py",
        "inputs": ["章节/第*.md", "审稿/state_delta_第*.json"],
        "outputs": ["审稿/state_ledger.json", "审稿/state_verify_第*.json"],
        "gate": "deterministic + semantic ledger reconcile",
        "cost_level": "semantic",
        "semantic_required": True,
        "can_parallel": False,
        "rollback": "回滚对应 chapter_delta 并重跑 reconcile_ledger。",
        "agent_role": "workflow_orchestrator",
    },
    {
        "key": "review",
        "label": "审稿/硬伤检查",
        "owner": "novel-review",
        "inputs": ["章节/第*.md", "审稿/state_ledger.json"],
        "outputs": ["审稿/review_report.json"],
        "gate": "qa-report-schema",
        "cost_level": "semantic",
        "semantic_required": True,
        "can_parallel": True,
        "rollback": "按 findings 回源头阶段修正。",
        "agent_role": "specialist_reviewer",
    },
    {
        "key": "score",
        "label": "市场评分",
        "owner": "novel-score",
        "inputs": ["章节/第*.md", "评分/market_baseline_*.json"],
        "outputs": ["评分/score_report.json", "语义任务/score_assessment_*.json"],
        "output_policy": "any",
        "gate": "market baseline freshness + semantic assessment",
        "cost_level": "search+semantic",
        "semantic_required": True,
        "can_parallel": True,
        "rollback": "重拉 market baseline 或重出 score task。",
        "agent_role": "specialist_score",
    },
    {
        "key": "revision",
        "label": "统一修订计划",
        "owner": "novel-craft/scripts/revision_planner.py",
        "inputs": [
            "审稿/review_report.json",
            "评分/score_report.json",
            "评分/reader_telemetry_summary.json",
            "评分/reader_panel_signals.json",
            "评分/market_evidence_jobs.json",
        ],
        "input_policy": "any",
        "outputs": ["修订/revision_plan.json"],
        "gate": "deterministic conflict resolution",
        "cost_level": "free",
        "semantic_required": False,
        "can_parallel": False,
        "rollback": "删除/重出 revision_plan；不直接改正文。",
        "agent_role": "workflow_orchestrator",
    },
    {
        "key": "reader_validation",
        "label": "读者测试计划/反馈归因",
        "owner": "novel-feedback",
        "inputs": ["评分/score_report.json", "审稿/review_report.json"],
        "input_policy": "any",
        "outputs": ["评分/reader_test_plan.json", "评分/reader_telemetry_summary.json"],
        "output_policy": "any",
        "gate": "reader test plan before release",
        "cost_level": "free+external",
        "semantic_required": False,
        "can_parallel": True,
        "rollback": "补 take_id/variant_id 后重导入读者反馈或记录 scoped waiver。",
        "agent_role": "specialist_score",
    },
    {
        "key": "edit",
        "label": "分层专业编辑",
        "owner": "novel-edit/scripts/edit_plan.py",
        "inputs": ["修订/revision_plan.json", "审稿/review_report.json", "评分/score_report.json"],
        "input_policy": "any",
        "outputs": ["修订/edit_plan.json", "修订/editorial_letter.md", "修订/style_sheet.md", "修订/proof_checklist.md"],
        "gate": "P0/P1 edit task closure",
        "cost_level": "free",
        "semantic_required": False,
        "can_parallel": False,
        "rollback": "关闭或重开编辑任务；结构未定不进入 proofread。",
        "agent_role": "workflow_orchestrator",
    },
    {
        "key": "ai_compliance",
        "label": "AI 使用与平台合规",
        "owner": "novel-craft/scripts/ai_usage.py + compliance_profile.py",
        "inputs": ["章节/第*.md", "_meta.json", "_设置.md"],
        "outputs": ["合规/ai_usage.json", "合规/compliance_profile.json"],
        "gate": "AI disclosure + jurisdiction/platform profile",
        "cost_level": "free",
        "semantic_required": False,
        "can_parallel": False,
        "rollback": "更新 AI 使用说明或合规确认后重跑 release manifest。",
        "agent_role": "workflow_orchestrator",
    },
    {
        "key": "metadata_pack",
        "label": "发布元数据包",
        "owner": "novel-craft/scripts/metadata_pack.py",
        "inputs": ["_meta.json", "_设置.md", "合规/ai_usage.json"],
        "input_policy": "any",
        "outputs": ["导出/metadata_pack.json", "导出/metadata_pack.md"],
        "gate": "publish metadata readiness",
        "cost_level": "free",
        "semantic_required": False,
        "can_parallel": False,
        "rollback": "更新简介、关键词、分类、权利/AI 摘要后重跑 metadata_pack.py。",
        "agent_role": "workflow_orchestrator",
    },
    {
        "key": "export",
        "label": "导出",
        "owner": "novel-craft/scripts/export.py",
        "inputs": ["章节/第*.md", "审稿/review_report.json", "评分/score_report.json", "合规/ai_usage.json"],
        "outputs": ["导出/*.txt", "导出/*.docx", "导出/*outline*.md"],
        "output_policy": "any",
        "gate": "export QA gate",
        "cost_level": "free",
        "semantic_required": False,
        "can_parallel": False,
        "rollback": "删除导出物并修复 gate blocker 后重导。",
        "agent_role": "workflow_orchestrator",
    },
    {
        "key": "release_manifest",
        "label": "发布版本清单",
        "owner": "novel-craft/scripts/release_manifest.py",
        "inputs": ["导出/*.txt", "导出/*.docx", "导出/*outline*.md"],
        "input_policy": "any",
        "outputs": ["导出/release_manifest.json", "导出/release_manifest.md"],
        "gate": "release evidence hash snapshot",
        "cost_level": "free",
        "semantic_required": False,
        "can_parallel": False,
        "rollback": "删除 release_manifest 后重建；不修改正文或导出物。",
        "agent_role": "workflow_orchestrator",
    },
    {
        "key": "screen_ready",
        "label": "转制就绪检查",
        "owner": "novel-craft/scripts/screen_adaptation_ready.py",
        "inputs": ["导出/release_manifest.json", "导出/*.txt", "导出/*.docx", "章节/第*.md", "合规/ai_usage.json"],
        "input_policy": "any",
        "outputs": ["导出/screen_adaptation_readiness.json", "导出/转制就绪检查.md"],
        "gate": "novel-side readiness",
        "cost_level": "free",
        "semantic_required": False,
        "can_parallel": False,
        "rollback": "修复 readiness blocker 后重跑检查。",
        "agent_role": "workflow_orchestrator",
    },
]


AGENT_LAYER = {
    "workflow_orchestrator": {
        "purpose": "确定性串阶段、查 gate、写计划、登记 provenance。",
        "may_call_models": False,
        "handoff_contract": "只调用脚本和读取/写入机器产物；不直接写正文。",
    },
    "specialist_writer": {
        "purpose": "处理蓝图、设定、章节正文等开放写作任务。",
        "may_call_models": True,
        "handoff_contract": "必须从写作任务包/语义任务读取输入，并写回指定产物。",
    },
    "specialist_reviewer": {
        "purpose": "审稿、demo gate、账本核对、硬伤定位。",
        "may_call_models": True,
        "handoff_contract": "必须输出符合 qa-report-schema 或 semantic schema 的 JSON。",
    },
    "specialist_score": {
        "purpose": "市场深搜、评分、读者反馈归因。",
        "may_call_models": True,
        "handoff_contract": "必须绑定 score_task_id、market baseline 和 source_snapshot。",
    },
}


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_jsonl(path: str) -> list[dict[str, Any]]:
    if not os.path.exists(path):
        return []
    out: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                out.append(payload)
    return out


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def registry() -> list[dict[str, Any]]:
    return deepcopy(PIPELINE_REGISTRY)


def registry_payload() -> dict[str, Any]:
    return {
        "schema_version": PIPELINE_REGISTRY_VERSION,
        "kind": PIPELINE_REGISTRY_KIND,
        "stages": registry(),
        "agent_layer": deepcopy(AGENT_LAYER),
        "artifact_graph_kind": ARTIFACT_GRAPH_KIND,
        "handoff_contract_kind": HANDOFF_CONTRACT_KIND,
    }


def stage_by_key(key: str) -> dict[str, Any] | None:
    for stage in PIPELINE_REGISTRY:
        if stage["key"] == key:
            return deepcopy(stage)
    return None


SOURCE_IMPORT_KINDS = {"import", "rewrite", "continue", "expand", "condense", "spinoff"}
ORIGINAL_KINDS = {"", "create", "original", "原创"}


def _has_legacy_source_artifacts(root: str | None) -> bool:
    if not root:
        return False
    return any(
        os.path.exists(os.path.join(root, item))
        for item in ("原作.txt", os.path.join("小说", "source_manifest.json"))
    )


def normalized_project_kind(meta: dict[str, Any] | None = None, root: str | None = None) -> str:
    """Canonicalize project kind for pipeline filtering.

    Older original projects often have no `_meta.kind`; treating that as
    "match all" incorrectly inserts the source_import stage. A missing/legacy
    kind is create unless source artifacts prove it is an imported source book.
    """
    raw = str((meta or {}).get("kind") or "").strip().lower()
    if raw in SOURCE_IMPORT_KINDS:
        return raw
    if raw in ORIGINAL_KINDS:
        return "import" if _has_legacy_source_artifacts(root) else "create"
    return raw or "create"


def applicable_stages(meta: dict[str, Any] | None = None, root: str | None = None) -> list[dict[str, Any]]:
    kind = normalized_project_kind(meta, root)
    out: list[dict[str, Any]] = []
    for stage in PIPELINE_REGISTRY:
        allowed = stage.get("applicable_kinds")
        if allowed and kind not in allowed:
            continue
        out.append(deepcopy(stage))
    return out


def _matches(root: str, patterns: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for pattern in patterns:
        hits = sorted(glob.glob(os.path.join(root, pattern)))
        out[pattern] = [rel(root, item) for item in hits]
    return out


def _artifact_patterns(stages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    for stage in stages:
        for pattern in stage.get("inputs") or []:
            item = artifacts.setdefault(pattern, {
                "pattern": pattern,
                "producers": [],
                "consumers": [],
            })
            if stage["key"] not in item["consumers"]:
                item["consumers"].append(stage["key"])
        for pattern in stage.get("outputs") or []:
            item = artifacts.setdefault(pattern, {
                "pattern": pattern,
                "producers": [],
                "consumers": [],
            })
            if stage["key"] not in item["producers"]:
                item["producers"].append(stage["key"])
    return artifacts


def _latest_recorded_outputs(root: str) -> dict[str, dict[str, Any]]:
    events = _load_jsonl(os.path.join(root, "生产数据", "provenance.jsonl"))
    recorded: dict[str, dict[str, Any]] = {}
    for event in events:
        for artifact in event.get("outputs") or []:
            if not isinstance(artifact, dict):
                continue
            path = artifact.get("path")
            if not path:
                continue
            recorded[str(path)] = {
                "sha256": artifact.get("sha256"),
                "event_type": event.get("event_type"),
                "tool": event.get("tool"),
                "created_at": event.get("created_at"),
                "metadata": event.get("metadata") or {},
            }
    return recorded


def _file_record(root: str, path: str, recorded: dict[str, dict[str, Any]]) -> dict[str, Any]:
    abs_path = path if os.path.isabs(path) else os.path.join(root, path)
    rel_path = rel(root, abs_path)
    payload: dict[str, Any] = {
        "path": rel_path,
        "exists": os.path.exists(abs_path),
    }
    if os.path.isfile(abs_path):
        payload.update({
            "sha256": sha256_file(abs_path),
            "size_bytes": os.path.getsize(abs_path),
            "mtime": datetime.fromtimestamp(os.path.getmtime(abs_path)).isoformat(timespec="seconds"),
        })
    previous = recorded.get(rel_path)
    if previous:
        payload["recorded"] = previous
        if payload.get("sha256") and previous.get("sha256") and payload["sha256"] != previous["sha256"]:
            payload["stale"] = True
            payload["stale_reason"] = "current_hash_differs_from_latest_provenance_output"
    return payload


def _satisfied(matches: dict[str, list[str]], policy: str) -> bool:
    if not matches:
        return True
    values = [bool(v) for v in matches.values()]
    return any(values) if policy == "any" else all(values)


def evaluate_stage(root: str, stage: dict[str, Any],
                   recorded_outputs: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    inputs = list(stage.get("inputs") or [])
    outputs = list(stage.get("outputs") or [])
    input_matches = _matches(root, inputs)
    output_matches = _matches(root, outputs)
    input_policy = str(stage.get("input_policy") or "all")
    output_policy = str(stage.get("output_policy") or "all")
    inputs_ok = _satisfied(input_matches, input_policy)
    outputs_ok = _satisfied(output_matches, output_policy) if outputs else False
    status = "done" if outputs_ok else ("ready" if inputs_ok else "blocked")
    missing_inputs = [pat for pat, hits in input_matches.items() if not hits]
    gate_blockers: list[str] = []
    if stage.get("key") == "release_manifest" and outputs_ok:
        manifest = load_json(os.path.join(root, "导出", "release_manifest.json"), {}) or {}
        if manifest.get("release_ready") is not True:
            status = "blocked"
            gate_blockers.append("导出/release_manifest.json: release_ready is not true")
    if stage.get("key") == "evidence_prep" and outputs_ok:
        jobs = load_json(os.path.join(root, "资料", "research_jobs.json"), {}) or {}
        open_blocking = [
            job for job in (jobs.get("jobs") or [])
            if isinstance(job, dict)
            and job.get("severity") == "blocking"
            and job.get("status") not in {"done", "verified", "waived"}
        ] if isinstance(jobs, dict) else []
        if open_blocking:
            status = "blocked"
            gate_blockers.append(f"资料/research_jobs.json: {len(open_blocking)} 个 P0 专业资料任务未关闭")
    if stage.get("key") == "author_intent" and outputs_ok:
        intent = load_json(os.path.join(root, "设定", "author_intent.json"), {}) or {}
        missing = []
        if not intent.get("core_theme") or "待填写" in str(intent.get("core_theme")):
            missing.append("core_theme")
        if not intent.get("non_negotiables") or "待填写" in str(intent.get("non_negotiables")):
            missing.append("non_negotiables")
        if missing:
            status = "blocked"
            gate_blockers.append("设定/author_intent.json: 未完成 " + ", ".join(missing))
    if stage.get("key") == "manuscript_map" and outputs_ok:
        check = load_json(os.path.join(root, "设定", "manuscript_map_check.json"), {}) or {}
        if check.get("blocking"):
            status = "blocked"
            gate_blockers.append(f"设定/manuscript_map_check.json: {check.get('blocking')} 个结构地图阻断")
    if stage.get("key") == "demo_readiness" and outputs_ok:
        readiness = load_json(os.path.join(root, "审稿", "demo_readiness.json"), {}) or {}
        if readiness.get("ready_for_batch") is not True:
            status = "blocked"
            gate_blockers.append("审稿/demo_readiness.json: ready_for_batch is not true")
    if stage.get("key") == "edit" and outputs_ok:
        edit_plan = load_json(os.path.join(root, "修订", "edit_plan.json"), {}) or {}
        closed = {"fixed", "accepted", "waived", "closed", "done", "resolved"}
        open_p0_p1 = [
            task for task in (edit_plan.get("tasks") or [])
            if isinstance(task, dict)
            and str(task.get("priority") or "").upper() in {"P0", "P1"}
            and str(task.get("status") or "open").lower() not in closed
        ] if isinstance(edit_plan, dict) else []
        if open_p0_p1:
            status = "blocked"
            gate_blockers.append(f"修订/edit_plan.json: {len(open_p0_p1)} 个 P0/P1 编辑任务未关闭")
        open_queries = [
            query for query in _load_jsonl(os.path.join(root, "修订", "editor_queries.jsonl"))
            if str(query.get("status") or "open").lower() not in {"answered", "accepted", "rejected", "resolved", "waived", "closed"}
        ]
        if open_queries:
            status = "blocked"
            gate_blockers.append(f"修订/editor_queries.jsonl: {len(open_queries)} 个 editor query 未关闭")
    if stage.get("key") == "ai_compliance" and outputs_ok:
        ai_usage = load_json(os.path.join(root, "合规", "ai_usage.json"), {}) or {}
        if ai_usage.get("text_mode") in {"AI-generated", "AI-assisted"} and not ai_usage.get("chapter_usage"):
            status = "blocked"
            gate_blockers.append("合规/ai_usage.json: 缺 chapter_usage 逐章 AI 使用记录")
    if stage.get("key") == "metadata_pack" and outputs_ok:
        check = load_json(os.path.join(root, "导出", "metadata_pack_check.json"), {}) or {}
        if check.get("blocking"):
            status = "blocked"
            gate_blockers.append(f"导出/metadata_pack_check.json: {check.get('blocking')} 个发布元数据阻断")
    if stage.get("key") == "draft" and outputs_ok:
        # output_policy="any" 下，写出 1 章就会判 draft「done」，macro-plan 会带着 1/N 章冲进 review/score。
        # 按 _meta.target_chapters 计数把关：未达目标章数则保持 ready（仍停在 draft），不算完成。
        meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
        target = int(meta.get("target_chapters") or 0)
        chapter_hits = output_matches.get("章节/第*.md") or []
        if target and len(chapter_hits) < target:
            status = "ready"
            gate_blockers.append(f"章节/第*.md: 已写 {len(chapter_hits)}/{target} 章，未达目标章数")
    recorded_outputs = recorded_outputs if recorded_outputs is not None else _latest_recorded_outputs(root)
    stale_inputs = [
        pat for pat, hits in input_matches.items()
        if any(_file_record(root, hit, recorded_outputs).get("stale") for hit in hits)
    ]
    return {
        "key": stage["key"],
        "label": stage["label"],
        "owner": stage["owner"],
        "status": status,
        "gate": stage.get("gate"),
        "cost_level": stage.get("cost_level"),
        "semantic_required": bool(stage.get("semantic_required")),
        "can_parallel": bool(stage.get("can_parallel")),
        "agent_role": stage.get("agent_role"),
        "rollback": stage.get("rollback"),
        "input_policy": input_policy,
        "output_policy": output_policy,
        "missing_inputs": missing_inputs,
        "gate_blockers": gate_blockers,
        "stale_inputs": stale_inputs,
        "inputs": input_matches,
        "outputs": output_matches,
    }


def artifact_graph(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    stages = applicable_stages(meta, root)
    recorded = _latest_recorded_outputs(root)
    artifacts = []
    stale_artifacts: list[dict[str, Any]] = []
    for pattern, spec in sorted(_artifact_patterns(stages).items()):
        matches = sorted(glob.glob(os.path.join(root, pattern)))
        files = [_file_record(root, path, recorded) for path in matches]
        stale_files = [item for item in files if item.get("stale")]
        if stale_files:
            stale_artifacts.append({
                "pattern": pattern,
                "files": [item["path"] for item in stale_files],
                "consumers": spec.get("consumers") or [],
            })
        artifacts.append({
            "pattern": pattern,
            "producers": spec.get("producers") or [],
            "consumers": spec.get("consumers") or [],
            "files": files,
            "missing": not bool(files),
            "stale": bool(stale_files),
        })
    return {
        "schema_version": 1,
        "kind": ARTIFACT_GRAPH_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "title": meta.get("title") or meta.get("source_title") or os.path.basename(root),
        "artifacts": artifacts,
        "stale_artifacts": stale_artifacts,
    }


def handoff_contract(root: str, stage_key: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    stage = stage_by_key(stage_key)
    if not stage:
        raise KeyError(f"unknown pipeline stage: {stage_key}")
    evaluated = evaluate_stage(root, stage, _latest_recorded_outputs(root))
    role = str(stage.get("agent_role") or "workflow_orchestrator")
    role_spec = deepcopy(AGENT_LAYER.get(role) or {})
    return {
        "schema_version": 1,
        "kind": HANDOFF_CONTRACT_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "stage": evaluated,
        "agent_role": role,
        "role_spec": role_spec,
        "allowed_decisions": [
            "complete_declared_outputs",
            "create_or_complete_semantic_job",
            "mark_blocked_with_reason",
            "request_human_confirmation",
        ],
        "forbidden_actions": [
            "edit_unlisted_outputs_without_new_plan",
            "bypass_gate_without_waiver",
            "mutate_progress_without_runner_or_progress_script",
            "call_models_from_workflow_orchestrator_role",
        ],
        "required_return": {
            "status": "completed|blocked|needs_human|rejected",
            "stage_key": stage_key,
            "outputs": list(stage.get("outputs") or []),
            "evidence": "paths plus hashes or semantic_job ids",
            "notes": "short explanation of decisions",
        },
    }


def _reconcile_progress(root: str, stages: list[dict[str, Any]], next_stage_key: str | None) -> list[dict[str, Any]]:
    """状态源对账（report-only）：dry_run_plan 走 artifact glob，flow.py/_进度.md 走勾选表。
    二者对"是否写完"分歧时发 progress_disagreement advisory——不改 next_stage，只让两套 next-step 的
    静默打架变可见，提醒以 _进度.md 为准。novel_route 不可用/无 _进度.md 时安全跳过。"""
    out: list[dict[str, Any]] = []
    try:
        import novel_route  # 同在 _lib，path 已含
        summary = novel_route.summarize(root)
    except Exception:
        return out
    if not isinstance(summary, dict) or summary.get("error"):
        return out
    progress_pending = summary.get("first") is not None  # _进度.md 仍有待办章节行
    draft = next((s for s in stages if s.get("key") == "draft"), None)
    if draft and draft.get("status") == "done" and progress_pending:
        out.append({
            "type": "progress_disagreement",
            "detail": "artifact 视图判 draft 已完成，但 _进度.md 仍有待办章节行；"
                      "可能部分章节产物存在但章未真正写完（或勾选表滞后）。以 _进度.md 为准复核。",
            "next_pending_label": str((summary.get("first") or {}).get("label") or ""),
        })
    post_draft = {"post_write", "review", "score", "revision", "reader_validation", "edit", "ai_compliance", "export", "release_manifest", "screen_ready"}
    if next_stage_key in post_draft and progress_pending:
        out.append({
            "type": "progress_disagreement",
            "detail": f"macro next_stage={next_stage_key}（已过 draft），但 _进度.md 仍有待办章节；"
                      "下游阶段可能在章节未写全时被触发，请先核对勾选表。",
        })
    return out


def dry_run_plan(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    project_kind = normalized_project_kind(meta, root)
    recorded = _latest_recorded_outputs(root)
    stages = [evaluate_stage(root, stage, recorded) for stage in applicable_stages(meta, root)]
    graph = artifact_graph(root)
    open_semantic_jobs = sorted(glob.glob(os.path.join(root, "语义任务", "*.json")))
    market_jobs = os.path.join(root, "评分", "market_evidence_jobs.json")
    next_stage = next((stage for stage in stages if stage["status"] != "done"), None)
    progress_reconciliation = _reconcile_progress(root, stages, next_stage["key"] if next_stage else None)
    return {
        "schema_version": 1,
        "kind": PIPELINE_PLAN_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "title": meta.get("title") or meta.get("source_title") or os.path.basename(root),
        "project_kind": project_kind,
        "next_stage": next_stage["key"] if next_stage else None,
        "stages": stages,
        "artifact_graph_summary": {
            "artifact_count": len(graph.get("artifacts") or []),
            "stale_count": len(graph.get("stale_artifacts") or []),
            "stale_artifacts": graph.get("stale_artifacts") or [],
        },
        "open_semantic_jobs": [rel(root, path) for path in open_semantic_jobs],
        "market_evidence_jobs": rel(root, market_jobs) if os.path.exists(market_jobs) else "",
        "progress_reconciliation": progress_reconciliation,
        "agent_layer": deepcopy(AGENT_LAYER),
    }
