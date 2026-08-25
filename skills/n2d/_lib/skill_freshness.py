#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-spend skill-drift assessment shared across the n2d line.

「物料新鲜度」闸的判定核心：在**正式调用后端出图/出视频前**，回答一个问题——
*自上次记录基线以来，生产本阶段输入物料的 skill 有没有改动？*（即"物料是否因 skill
升级而过期"）。把这层判定从 `n2d-update/update_plan.py`（只在用户**手动**跑时才检测）下沉到
`n2d/_lib`，让 `n2d-review/gate.py` 的 `image_preflight` / `video_preflight` 预检也能在花钱前
顺手体检一次，命中即 WARN 并路由回 n2d-update 评估重制——不硬阻断（重制是判断题，交给精确规划器）。

与 `update_plan.py` 的关系（**刻意分工·非重复**）：
- 本模块给 gate 的是 **skill 粒度** 的粗判（"n2d-image 改了 → 出图物料可能过期"），偏向"花钱前先去查"，
  允许轻度过报；它把精确裁决（哪个文件→哪个阶段、artifact vs gate-only）让给 update_plan。
- `update_plan.py` 保留 **文件→阶段** 的精确 hint 表，产出可执行的有界重制计划。
- 二者**共享同一份真值常量**（OBSERVE_ONLY / _lib 观测白名单 / 基线路径），见下；update_plan 回引这里，
  避免常量两处漂移。

交付铁律：零版本控制依赖，纯文件内容 SHA256（沿用 skill_snapshot 的 git-free 思路），中文路径无碍。
"""
from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional, Set

from skill_snapshot import (
    changed_files_since,
    file_sha256,  # noqa: F401  re-export convenience
    is_test_path,
    snapshot_for_skills,
)
from n2d_contract import production_dir, stage_specs

LIB_DIR = os.path.dirname(os.path.abspath(__file__))
N2D_DIR = os.path.dirname(LIB_DIR)
REPO_SKILLS = os.path.dirname(N2D_DIR)
REPO_ROOT = os.path.dirname(REPO_SKILLS)

SNAPSHOT_FILE = "skill_update_snapshot.json"

# ── 共享真值常量（update_plan.py 回引，单一来源）─────────────────────────────
# 进度无关、永远纳入基线范围的 skill（调度/质检/批处理/更新自身）。
ALWAYS_RELEVANT_SKILLS: Set[str] = {
    "n2d",
    "n2d-dashboard",
    "n2d-review",
    "n2d-batch",
    "n2d-update",
    "n2d-lora",
}
# 只观测、从不生产阶段物料的 skill：它们改动**不会**让任何前期物料过期。
OBSERVE_ONLY_SKILLS: Set[str] = {
    "n2d-dashboard",
    "n2d-review",
    "n2d-batch",
    "n2d-update",
}
# `skills/n2d/_lib` 里确认为观测/维护/加速基建的文件：改了不影响已产物料。
# 与 update_plan.N2D_LIB_OBSERVE_ONLY_TOKENS 同源（那边回引本常量）。
N2D_LIB_OBSERVE_ONLY_TOKENS = (
    "_lib/skill_snapshot.py",
    "_lib/skill_freshness.py",
    "_lib/n2d_findings_utils.py",
    "_lib/n2d_thresholds.py",
    "_lib/n2d_telemetry.py",
    "_lib/freshness.py",
    "_lib/refresh.py",
    "_lib/n2d_contract_diff.py",
    "_lib/n2d_color.py",
    "_lib/style_policy.py",
    "_lib/seam_conditioning.py",
    "_lib/gate_policy_matrix.py",
    "_lib/gate_receipt.py",
    "_lib/n2d_action_registry.py",
    "_lib/n2d_schema_registry.py",
    "_lib/n2d_trace.py",
    "_lib/n2d_friction.py",
    "_lib/prework_cache.py",
    # 预算信封只改变未来付费调用的授权/消费控制，不改变已生成媒体或 prompt 内容。
    "_lib/spend_envelope.py",
    "_lib/n2d_cross_episode.py",
    "_lib/n2d_maintenance.py",
    # 血缘索引：只从既有产物派生节点/边，从不改变阶段状态或替代 _进度.md/gate。
    "_lib/episode_graph.py",
    # 控制面 telemetry：只记阶段/停点/缓存/耗时事件，不产也不改任何物料。
    "_lib/flow_telemetry.py",
    # 把 NextAction 停点归一化成修复导向 bundle，纯控制面，不产物料。
    "_lib/n2d_blocking.py",
    # 制作模式路由只给证据化建议，从不改写 _设置.md、不构成阻断 gate。
    "_lib/production_mode_router.py",
)
# 命中即只改 gate/QC 结论、不改 prompt/PNG/视频产物（与 update_plan.GATE_ONLY_FILE_STAGE_HINTS 对齐的常见项）。
GATE_ONLY_TOKENS = (
    "n2d-image/scripts/image_qc.py",
    "_lib/image_backends.py",
    "_lib/backend_smoke.py",
)


def skill_name_for_rel(rel_path: str) -> Optional[str]:
    """Resolve a skill name from the nested layout or a legacy flat snapshot."""
    parts = str(rel_path).replace(os.sep, "/").split("/")
    if len(parts) >= 2 and parts[0] == "skills":
        line = parts[1]
        if len(parts) >= 3 and parts[2].startswith(f"{line}-"):
            return parts[2]
        return line
    return None


def stage_index(key: str) -> int:
    for idx, spec in enumerate(stage_specs()):
        if spec.get("key") == key:
            return idx
    return 10 ** 6


def until_key_for_gate_stage(stage: str) -> Optional[str]:
    """把 gate 的 stage 串映射回 stage_specs 的 key（确定本阶段输入物料的"上界"）。

    image_preflight→image, video_preflight→video, image_prompt_preflight→image_prompt,
    video_prompt_preflight→video_prompt, compose/review→同名 key。未知 → None。
    """
    base = stage[: -len("_preflight")] if stage.endswith("_preflight") else stage
    keys = {str(s.get("key")) for s in stage_specs()}
    if base in keys:
        return base
    for spec in stage_specs():
        if spec.get("gate_stage") == base:
            return str(spec.get("key"))
    return None


def production_owner_skills_until(until_key: str) -> Set[str]:
    """生产阶段 ≤ until_key 的 owner skill 集合（其改动可能让本阶段输入物料过期）。"""
    until = stage_index(until_key)
    owners: Set[str] = set()
    for idx, spec in enumerate(stage_specs()):
        if idx <= until and spec.get("owner"):
            owners.add(str(spec["owner"]))
    return owners


def relevant_skills_for_diff(until_key: str) -> Set[str]:
    """参与漂移比对的 skill 范围：生产 owner(≤阶段) + n2d 核心库（_lib 在 skills/n2d 下）。

    刻意**不含** observe-only skill：它们改动不会让物料过期，纳入只会徒增噪声。
    always-relevant 里的非 observe-only skill（如 n2d-lora）是横切生产规则，也参与花钱前体检。
    """
    cross_cutting = set(ALWAYS_RELEVANT_SKILLS) - set(OBSERVE_ONLY_SKILLS)
    return production_owner_skills_until(until_key) | {"n2d"} | cross_cutting


def is_material_affecting(rel_path: str) -> bool:
    """该变动文件是否可能让"前期物料"过期（粗判·skill 粒度，精确裁决交给 update_plan）。"""
    skill = skill_name_for_rel(rel_path)
    if skill in OBSERVE_ONLY_SKILLS:
        return False
    if any(tok in rel_path for tok in GATE_ONLY_TOKENS):
        return False
    if skill == "n2d":
        # n2d 核心**不拥有任何生产阶段**：只有 `_lib/` 运行期契约层是物料生产规则；
        # `scripts/`（治理/覆盖/配方清单）与顶层 `run.py`/`progress.py`/`source_check.py`
        # 是编排/治理工具，改了映射不到任何生产阶段（与 update_plan 一致），不算物料过期。
        if not rel_path.startswith("skills/n2d/_lib/"):
            return False
        if any(tok in rel_path for tok in N2D_LIB_OBSERVE_ONLY_TOKENS):
            return False
    return True


def snapshot_path(root: str) -> str:
    return os.path.join(production_dir(root), SNAPSHOT_FILE)


def load_baseline(root: str) -> Optional[Dict[str, Any]]:
    import json

    path = snapshot_path(root)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _scoped(files: Dict[str, Any], relevant_skills: set[str]) -> Dict[str, Any]:
    return {
        k: v
        for k, v in files.items()
        if skill_name_for_rel(k) in relevant_skills and not is_test_path(k)
    }


def scoped_changed(
    baseline: Dict[str, Any], new: Dict[str, Any], relevant_skills: Iterable[str]
) -> List[str]:
    """只在相关 skill 的交集内 diff 内容快照（范围差异不算变更）。"""
    relevant = set(relevant_skills)
    if not relevant:
        return []
    before = _scoped(baseline.get("files") or {}, relevant)
    after = _scoped(new.get("files") or {}, relevant)
    return changed_files_since({"files": before}, {"files": after})


def assess(
    root: str,
    until_key: str,
    *,
    repo_root: str = REPO_ROOT,
    skills_dir: str = REPO_SKILLS,
) -> Dict[str, Any]:
    """花钱前的 skill 漂移体检。

    返回:
      status: "no_baseline" | "no_baseline_legacy" | "fresh" | "drift"
      changed_skills: 比对范围内所有有改动的 skill
      material_skills: 其中**可能让物料过期**的 skill（material-affecting）
      changed_files / material_files: 对应文件列表
      bootstrap: 基线是否为 check 自动建立的临时基线（看不到更早差异）
      baseline_path
    """
    baseline = load_baseline(root)
    out: Dict[str, Any] = {
        "until_key": until_key,
        "baseline_path": snapshot_path(root),
        "bootstrap": bool(baseline and baseline.get("bootstrap")),
        "changed_skills": [],
        "material_skills": [],
        "changed_files": [],
        "material_files": [],
    }
    if not baseline:
        out["status"] = "no_baseline"
        return out
    if not isinstance(baseline.get("files"), dict):
        # 旧版 git 派生基线（无内容快照）→ 无法 git-free 比对。
        out["status"] = "no_baseline_legacy"
        return out

    relevant = relevant_skills_for_diff(until_key)
    new = snapshot_for_skills(repo_root, skills_dir, relevant)
    changed = scoped_changed(baseline, new, relevant)
    material = [f for f in changed if is_material_affecting(f)]
    out["changed_files"] = changed
    out["material_files"] = material
    out["changed_skills"] = sorted(
        {skill_name_for_rel(f) or "" for f in changed} - {""}
    )
    out["material_skills"] = sorted(
        {skill_name_for_rel(f) or "" for f in material} - {""}
    )
    out["status"] = "drift" if changed else "fresh"
    return out
