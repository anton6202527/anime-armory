#!/usr/bin/env python3
"""Gate policy coverage audit for n2d release readiness."""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import glob
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent  # skills/n2d/scripts
REPO_ROOT = SCRIPT_DIR.parents[2]              # 仓根
LIB = SCRIPT_DIR.parents[0] / "_lib"           # skills/n2d/_lib（修：原 parents[1]=skills/_lib 不存在，
                                               # 仅靠全套 pytest 的 sys.path 污染才能 import，独立跑必崩）
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from n2d_const import GATE_POLICY_COVERAGE_KIND, PRODUCTION_DIR  # noqa: E402
from gate_policy_matrix import load_matrix, validate_matrix  # noqa: E402


VERSION = 1
COVERAGE_JSON = "gate_policy_coverage_{episode}.json"
COVERAGE_MD = "gate_policy_coverage_{episode}.md"


GROUP_COVERAGE: Dict[str, Dict[str, Any]] = {
    "compliance": {
        "implementation": ["skills/n2d/n2d-compliance/scripts/compliance.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-compliance/scripts/test_compliance.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["合规/compliance_manifest.json"],
        "release_required": True,
    },
    "progress": {
        "implementation": ["skills/n2d/progress.py", "skills/n2d/_lib/n2d_route.py"],
        "tests": ["skills/n2d/test_progress_manifest.py"],
        "evidence": ["_进度.md"],
        "release_required": True,
    },
    "voice_timing": {
        "implementation": ["skills/n2d/n2d-script/validate_timings.py", "skills/n2d/n2d-voice/render_voice.py"],
        "tests": ["skills/n2d/n2d-script/test_validate_timings.py", "skills/n2d/n2d-voice/test_render_voice.py"],
        "evidence": ["合成/{ep}/配音/时长清单.json"],
    },
    "storyboard_contract": {
        "implementation": ["skills/n2d/n2d-script/validate_storyboard_contract.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["脚本/{ep}/storyboard.json"],
        "release_required": True,
    },
    "style_contract": {
        "implementation": ["skills/n2d/_lib/style_policy.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-review/scripts/test_style_consistency.py"],
        "evidence": ["脚本/{ep}/storyboard.json", "出图/共享/visual_state_ledger.json"],
    },
    "special_templates": {
        "implementation": ["skills/n2d/n2d-script/scripts/spectacle_contract_audit.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-script/scripts/test_story_integrity_audit.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["脚本/{ep}/storyboard.json", "生产数据/spectacle_plan_{ep}.json"],
    },
    "story_economy": {
        "implementation": ["skills/n2d/n2d-script/scripts/story_economy_audit.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-script/scripts/test_story_economy_audit.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["生产数据/story_economy_audit_{ep}.json"],
        "release_required": True,
    },
    "production_handoff": {
        "implementation": ["skills/n2d/n2d-script/scripts/production_breakdown.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-script/scripts/test_production_breakdown.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["脚本/{ep}/production_handoff_pack.json", "脚本/{ep}/continuity_chain.json", "脚本/{ep}/continuity_bible.json", "脚本/{ep}/ai_shooting_schedule.json", "脚本/{ep}/ai_call_sheet.md"],
        "release_required": True,
    },
    "production_locks": {
        "implementation": ["skills/n2d/scripts/production_locks.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/scripts/test_production_locks.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["生产数据/production_locks_{ep}.json"],
        "release_required": True,
    },
    "identity_registry": {
        "implementation": ["skills/n2d/n2d-identity/scripts/identity.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-identity/scripts/test_identity.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["出图/共享/identity_registry.json"],
        "release_required": True,
    },
    "asset_registry": {
        "implementation": ["skills/n2d/n2d-asset-market/scripts/asset_registry.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-asset-market/scripts/test_asset_registry.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["出图/共享/asset_registry.json"],
        "release_required": True,
    },
    "retention": {
        "implementation": ["skills/n2d/n2d-script/scripts/beat_audit.py", "skills/n2d/n2d-script/scripts/story_integrity_audit.py"],
        "tests": ["skills/n2d/n2d-script/scripts/test_story_integrity_audit.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["生产数据/story_integrity_{ep}.json", "生产数据/beat_audit_{ep}.json"],
    },
    "budget": {
        "implementation": ["skills/n2d/n2d-batch/scripts/queue.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-batch/scripts/test_queue.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["生产数据/budget_{ep}.json", "生产数据/budget_ledger.json"],
        "release_required": True,
    },
    "backend_evidence": {
        "implementation": ["skills/n2d/_lib/image_backend_adapter.py", "skills/n2d/_lib/video_backend_adapter.py"],
        "tests": ["skills/n2d/_lib/test_video_backend_adapter.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["生产数据/image_backend_capabilities/*.json", "生产数据/video_backend_capabilities/*.json"],
        "release_required": True,
    },
    "skill_freshness": {
        # 花钱出图/出视频前的「物料新鲜度」预检：skill 自上次基线后是否漂移 → 物料是否过期。
        # release_required=False：基线（skill_update_snapshot.json）是可选的——无基线时预检静默，
        # 不能因为没记基线就让发布覆盖闸 fail。
        "implementation": ["skills/n2d/_lib/skill_freshness.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/_lib/test_skill_freshness.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["生产数据/skill_update_snapshot.json"],
    },
    "image_qc": {
        "implementation": ["skills/n2d/n2d-image/scripts/image_qc.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-image/scripts/test_image_qc.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["生产数据/image_qc/{ep}/image_qc_{ep}.json"],
        "release_required": True,
    },
    "consistency_audit": {
        "implementation": ["skills/n2d/n2d-review/scripts/consistency_audit.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-review/scripts/test_consistency_audit.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["生产数据/consistency_ledger_{ep}.json", "生产数据/gate_findings_*_{ep}.json"],
        "release_required": True,
    },
    "generation_recipe": {
        "implementation": ["skills/n2d/scripts/generation_recipe_manifest.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/scripts/test_generation_recipe_manifest.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["生产数据/generation_recipe_manifest_{ep}.json"],
        "release_required": True,
    },
    "seed_events": {
        "implementation": ["skills/n2d/scripts/generation_recipe_manifest.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/scripts/test_generation_recipe_manifest.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["生产数据/generation_recipe_manifest_{ep}.json", "生产数据/production_events.jsonl"],
        "release_required": True,
    },
    "contract_inheritance": {
        "implementation": ["skills/n2d/n2d-video/scripts/inherit_contract.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-video/scripts/test_inherit_contract.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["生产数据/contract_inheritance_{ep}.json"],
        "release_required": True,
    },
    "identity_handoff": {
        "implementation": ["skills/n2d/_lib/n2d_handoff.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["生产数据/contract_inheritance_{ep}.json", "出视频/{ep}/prompt/video_model_routes.json"],
    },
    "asset_handoff": {
        "implementation": ["skills/n2d/_lib/n2d_handoff.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["生产数据/contract_inheritance_{ep}.json", "出视频/{ep}/prompt/video_model_routes.json"],
    },
    "model_router": {
        "implementation": ["skills/n2d/n2d-model-router/scripts/router.py"],
        "tests": ["skills/n2d/n2d-model-router/scripts/test_router.py"],
        "evidence": ["出视频/{ep}/prompt/video_model_routes.json"],
    },
    "motion_contract": {
        "implementation": ["skills/n2d/n2d-model-router/scripts/motion_control.py", "skills/n2d/n2d-script/scripts/spectacle_plan.py"],
        "tests": ["skills/n2d/n2d-model-router/scripts/test_motion_control.py"],
        "evidence": ["生产数据/motion_control_manifest.json", "生产数据/spectacle_plan_{ep}.json"],
    },
    "video_routes": {
        "implementation": ["skills/n2d/n2d-model-router/scripts/router.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-model-router/scripts/test_router.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["出视频/{ep}/prompt/video_model_routes.json"],
        "release_required": True,
    },
    "video_assets": {
        "implementation": ["skills/n2d/n2d-video/scripts/video_qc.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-video/scripts/test_video_qc.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["出视频/{ep}/视频/*.mp4"],
        "release_required": True,
    },
    "semantic_lineage": {
        "implementation": ["skills/n2d/n2d-review/scripts/semantic_continuity.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-review/scripts/test_semantic_continuity.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["脚本/{ep}/storyboard.json", "出图/{ep}/prompt/*.md", "出视频/{ep}/prompt/*.md"],
    },
    "compose_inputs": {
        "implementation": ["skills/n2d/n2d-compose/release_manifest.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-compose/test_release_manifest.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["合成/{ep}/成片_{ep}_*.mp4", "出视频/{ep}/视频/*.mp4"],
        "release_required": True,
    },
    "subtitle_alignment": {
        "implementation": ["skills/n2d/n2d-review/scripts/subtitle_align.py", "skills/n2d/n2d-review/scripts/gate.py"],
        "tests": ["skills/n2d/n2d-review/scripts/test_subtitle_align.py", "skills/n2d/n2d-review/scripts/test_gate.py"],
        "evidence": ["脚本/{ep}/字幕_中文.srt", "生产数据/native_av_subtitle_alignment_{ep}.json"],
        "release_required": True,
    },
    "voice_identity": {
        "implementation": ["skills/n2d/n2d-identity/scripts/voice_consistency.py", "skills/n2d/n2d-identity/scripts/voice_print_consistency.py"],
        "tests": ["skills/n2d/n2d-identity/scripts/test_voice_consistency.py", "skills/n2d/n2d-identity/scripts/test_voice_print_consistency.py"],
        "evidence": ["生产数据/native_voice_identity_{ep}.json", "生产数据/identity_voice_print_{ep}.json"],
        # 2026-07 标准审计：音色一致性是 score 正式维度（权重 10），发布口径不该比它松。
        # voice_print_consistency 在无音频/无声纹后端时也落 available=false 的诚实报告，
        # 故 release_required 只要求「检查至少跑过并留档」，不会对无对白集误伤。
        "release_required": True,
    },
    "score": {
        "implementation": ["skills/n2d/n2d-score/scripts/score.py"],
        "tests": ["skills/n2d/n2d-score/scripts/test_score.py"],
        "evidence": ["生产数据/score_{ep}.json"],
        "release_required": True,
    },
    "review_ui": {
        "implementation": ["skills/n2d/n2d-review-ui/scripts/review_ui.py"],
        "tests": ["skills/n2d/n2d-review-ui/scripts/test_review_ui.py"],
        "evidence": ["生产数据/review_ui_{ep}.json", "生产数据/review_ui_findings_{ep}.json"],
        "release_required": True,
    },
    "consistency_ledger": {
        "implementation": ["skills/n2d/n2d-review/scripts/consistency_ledger.py"],
        "tests": ["skills/n2d/n2d-review/scripts/test_consistency_ledger.py"],
        "evidence": ["生产数据/consistency_ledger_{ep}.json"],
        "release_required": True,
    },
    "human_review": {
        "implementation": ["skills/n2d/n2d-review-ui/scripts/review_ui.py", "skills/n2d/n2d-compose/release_manifest.py"],
        "tests": ["skills/n2d/n2d-review-ui/scripts/test_review_ui.py", "skills/n2d/n2d-compose/test_release_manifest.py"],
        "evidence": ["生产数据/review_signoff_{ep}.json", "生产数据/acceptance_signoff_{ep}.json"],
        "release_required": True,
    },
    "release_verdict": {
        "implementation": ["skills/n2d/scripts/release_verdict.py"],
        "tests": ["skills/n2d/scripts/test_release_verdict.py"],
        "evidence": ["生产数据/release_verdict_{ep}.json"],
        "release_required": True,
    },
}


# 政策↔gate **代码**绑定（P0-5）：每个 group 在 gate.py 里真正执行它的 check 函数名。
# 旧 coverage 只查 implementation 文件存在——有人删/短路 gate.py 里的 check_* 调用、文件还在，coverage 仍绿
# （data↔code 漂移，问题问的正中点）。这里要求这些函数在 gate.py 里**既定义又被调用**，把声明的政策绑到
# 被执行的政策。只列能确信映射的 release/gate 关键组；未列组按旧逻辑（不新增校验）。
GROUP_GATE_CHECKS: Dict[str, List[str]] = {
    "compliance": ["check_compliance_manifest"],
    "storyboard_contract": ["check_storyboard_contract"],
    "style_contract": ["check_storyboard_style_contract"],
    "special_templates": ["check_storyboard_special_templates"],
    "identity_registry": ["check_identity_registry"],
    "asset_registry": ["check_asset_reference_registry"],
    "backend_evidence": ["check_backend_smoke_evidence"],
    "identity_handoff": ["check_identity_handoff_inheritance"],
    "asset_handoff": ["check_asset_handoff_inheritance"],
    "voice_identity": ["check_native_voice_identity"],
    # 2026-06-26 扩面（P1）：补到 19 组——每个都已 AST 验证「从 run/main 可达」。未列组的强制在
    # gate.py 之外（独立脚本/release_manifest），映射见 GROUP_ENFORCED_OUTSIDE_GATE（机器可见，
    # 不再只留注释）。
    "budget": ["check_budget_cap"],
    "image_qc": ["check_input_frame_qc", "check_image_assets"],
    "consistency_audit": ["check_consistency_audit_gate"],
    "video_routes": ["check_video_model_routes"],
    "video_assets": ["check_video_assets"],
    "semantic_lineage": ["check_semantic_lineage"],
    "compose_inputs": ["check_compose_inputs"],
    "subtitle_alignment": ["check_subtitle_alignment", "check_native_av_subtitle_alignment"],
    "motion_contract": ["check_motion_control_route"],
    "skill_freshness": ["check_skill_freshness"],
    "story_economy": ["check_story_economy_audit"],
    "production_handoff": ["check_production_handoff_pack"],
    "production_locks": ["check_production_locks_preflight"],
}

_GATE_PY = REPO_ROOT / "skills" / "n2d" / "n2d-review" / "scripts" / "gate.py"
_gate_src_cache: Optional[str] = None


def _gate_source() -> str:
    """gate 闸源码全集 = gate.py + gate_core.py + gates/*.py（2026-06-28 按证据族拆分后）。

    check_* 的定义已分散到 gates/<family>.py，run() 入口仍在 gate.py——可达性分析必须看全集，
    否则把"迁出 gate.py 但仍被 run() 调用"的闸误判成 dead/缺。与 consistency_charter.gate_source_text
    / validate_skills._gate_layer_text 同一多文件纪律。"""
    global _gate_src_cache
    if _gate_src_cache is None:
        scripts_dir = _GATE_PY.parent
        parts = []
        for f in [_GATE_PY, scripts_dir / "gate_core.py", *sorted(scripts_dir.glob("gates/*.py"))]:
            if f.name == "__init__.py":
                continue
            try:
                parts.append(f.read_text(encoding="utf-8"))
            except Exception:
                pass
        _gate_src_cache = "\n".join(parts)
    return _gate_src_cache


_gate_graph_cache: Dict[str, Tuple[Set[str], Set[str]]] = {}


def _gate_call_graph(src: str) -> Tuple[Set[str], Set[str]]:
    """解析 gate.py 源 → (已定义函数名, 从 run/main 入口可达的被调用名)。

    比旧正则强在两点：① AST 只认真正的 ast.Call，忽略注释/字符串/文档里的同名 token（堵「字符串里
    出现也算 wired」）；② 只把从入口 run/main 可达的调用算 wired——死代码/未接进 run 分支里的调用
    不再蒙混过关（堵「死代码里的调用也算 wired」）。跨阶段分支精确归属仍超出静态可达性，边界诚实标注。"""
    key = hashlib.sha256(src.encode("utf-8", "replace")).hexdigest()
    cached = _gate_graph_cache.get(key)
    if cached is not None:
        return cached
    try:
        tree = ast.parse(src)
    except Exception:
        result: Tuple[Set[str], Set[str]] = (set(), set())
        _gate_graph_cache[key] = result
        return result
    funcs: Dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs[node.name] = node
    edges: Dict[str, Set[str]] = {name: set() for name in funcs}
    for name, node in funcs.items():
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                edges[name].add(sub.func.id)
    reachable: Set[str] = set()
    stack = [entry for entry in ("run", "main") if entry in funcs]
    while stack:
        cur = stack.pop()
        for callee in edges.get(cur, ()):  # type: ignore[arg-type]
            if callee not in reachable:
                reachable.add(callee)
                if callee in funcs:
                    stack.append(callee)
    result = (set(funcs), reachable)
    _gate_graph_cache[key] = result
    return result


GATE_INVENTORY_KIND = "n2d_gate_inventory"


def gate_inventory() -> Dict[str, Any]:
    """全量闸门自清点：gate.py 里每个 `check_*` 必须从 run() 入口可达，否则=死闸（定义在、永不执行）。

    P1-4 的政策↔代码绑定只校验「映射组」的 check；本清点把同一套 AST 可达性扩到 gate.py 的**全部**
    check_*，自动捕获「dead BLOCK 分支」那一类 bug——它曾经只能靠人肉发现、整个 commit 去修
    （某 BLOCK 整条 dispatch 路径从未触达）。这是给 94-gate / ~10k 行单体的回归守卫。纯静态读源。"""
    src = _gate_source()
    if not src:
        return {"kind": GATE_INVENTORY_KIND, "status": "fail", "total": 0, "reachable": 0,
                "dead": [], "issues": ["gate_source_unreadable"]}
    defined, reachable = _gate_call_graph(src)
    if not defined:
        return {"kind": GATE_INVENTORY_KIND, "status": "fail", "total": 0, "reachable": 0,
                "dead": [], "issues": ["gate_source_unparseable"]}
    checks = sorted(name for name in defined if name.startswith("check_"))
    dead = [name for name in checks if name not in reachable]
    return {
        "kind": GATE_INVENTORY_KIND,
        "total": len(checks),
        "reachable": len(checks) - len(dead),
        "dead": dead,
        "status": "fail" if dead else "pass",
        "issues": [f"dead gate（定义在 gate.py 但从 run() 不可达，永不执行）：{name}" for name in dead],
    }


def gate_check_gaps(group: str) -> List[str]:
    """该 group 在 gate.py 里执行它的 check 函数是否**既定义又从入口可达地被调用**。返回缺口码（空=健全）。

    catch：函数被删（gate_check_missing）/ 定义在但接不进 run 入口（gate_check_unwired，含死代码/未接线）。
    纯函数（读 gate.py 源，AST 可达性分析）。"""
    checks = GROUP_GATE_CHECKS.get(group)
    if not checks:
        return []
    src = _gate_source()
    if not src:
        return ["gate_source_unreadable"]
    defined, reachable = _gate_call_graph(src)
    if not defined:
        return ["gate_source_unreadable"]
    gaps: List[str] = []
    for fn in checks:
        if fn not in defined:
            gaps.append(f"gate_check_missing:{fn}")
        elif fn not in reachable:
            gaps.append(f"gate_check_unwired:{fn}")
    return gaps


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def production_dir(root: Path) -> Path:
    return root / PRODUCTION_DIR


def coverage_path(root: Path, episode: str) -> Path:
    return production_dir(root) / COVERAGE_JSON.format(episode=episode)


def coverage_md_path(root: Path, episode: str) -> Path:
    return production_dir(root) / COVERAGE_MD.format(episode=episode)


def relpath(base: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except Exception:
        return str(path)


def repo_matches(patterns: Sequence[str]) -> List[str]:
    out: List[str] = []
    for pattern in patterns:
        for path in glob.glob(str(REPO_ROOT / pattern)):
            p = Path(path)
            if p.is_file():
                out.append(relpath(REPO_ROOT, p))
    return sorted(set(out))


def _evidence_is_valid(p: Path) -> bool:
    """release evidence 不能只「文件存在」：必须非空；.json 还须能解析（堵陈旧/空壳/坏 JSON 蒙混过关）。

    其余类型（.mp4/.srt/.md/.jsonl）只验非空——它们的语义校验由各自阶段 gate 负责，这里只挡「0 字节占位」。"""
    try:
        if p.stat().st_size <= 0:
            return False
    except OSError:
        return False
    if p.suffix.lower() == ".json":
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return False
    return True


def evidence_matches(root: Path, episode: str, patterns: Sequence[str]) -> List[str]:
    out: List[str] = []
    for pattern in patterns:
        rel = pattern.format(ep=episode, episode=episode)
        for path in glob.glob(str(root / rel)):
            p = Path(path)
            if p.is_file() and _evidence_is_valid(p):
                out.append(relpath(root, p))
    return sorted(set(out))


# gate.py 之外强制的 group → 实际执行者（2026-07 标准审计：此前只在注释里说"在 gate.py 之外"，
# coverage 报告里看不到谁负责——现落成字段，report 消费方可核对执行者存在）。
GROUP_ENFORCED_OUTSIDE_GATE: Dict[str, str] = {
    "progress": "skills/n2d/progress.py (audit-dag) + run.py 收尾自动包",
    "score": "skills/n2d/scripts/release_verdict.py check_score",
    "review_ui": "skills/n2d/scripts/release_verdict.py check_review_ui",
    "consistency_ledger": "skills/n2d/scripts/release_verdict.py check_ledger",
    "human_review": "skills/n2d/scripts/release_verdict.py + run.py needs_acceptance_signoff",
    "generation_recipe": "skills/n2d/scripts/generation_recipe_manifest.py + release_manifest.py",
    "seed_events": "skills/n2d/n2d-dashboard/scripts/event_ledger.py audit",
    "contract_inheritance": "skills/n2d/n2d-video/scripts/inherit_contract.py（video prework）",
    "model_router": "skills/n2d/n2d-model-router/scripts/router.py + video preflight consumed_contracts",
    "voice_timing": "skills/n2d/n2d-script/validate_timings.py（finalize/compose 前）",
    "retention": "skills/n2d/n2d-script/scripts/beat_audit.py --strict（image_prompt prework）",
    "release_verdict": "skills/n2d/scripts/release_verdict.py（终判本体）",
}


def matrix_required_groups(matrix: Dict[str, Any]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for stage, policy in (matrix.get("stages") or {}).items():
        if not isinstance(policy, dict):
            continue
        for group in policy.get("required_check_groups") or []:
            out.setdefault(str(group), []).append(str(stage))
    return {key: sorted(set(value)) for key, value in sorted(out.items())}


def group_row(root: Path, episode: str, group: str, stages: Sequence[str]) -> Dict[str, Any]:
    spec = GROUP_COVERAGE.get(group, {})
    impl = repo_matches(spec.get("implementation") or [])
    tests = repo_matches(spec.get("tests") or [])
    evidence = evidence_matches(root, episode, spec.get("evidence") or [])
    missing: List[str] = []
    if not spec:
        missing.append("coverage_mapping")
    if not impl:
        missing.append("implementation")
    if not tests:
        missing.append("tests")
    release_required = bool(spec.get("release_required"))
    if release_required and not evidence:
        missing.append("release_evidence")
    # P0-5：政策↔gate 代码绑定——该 group 的 check 函数必须在 gate.py 既定义又被调用（堵 data↔code 漂移）。
    gate_checks = GROUP_GATE_CHECKS.get(group, [])
    gate_gaps = gate_check_gaps(group)
    missing.extend(gate_gaps)
    return {
        "group": group,
        "stages": list(stages),
        "release_required": release_required,
        "enforced_outside_gate": GROUP_ENFORCED_OUTSIDE_GATE.get(group, ""),
        "implementation": impl,
        "tests": tests,
        "evidence": evidence,
        "gate_checks": gate_checks,
        "gate_check_gaps": gate_gaps,
        "missing": missing,
        "status": "fail" if missing else "pass",
    }


def build_coverage(root: Path, episode: str) -> Dict[str, Any]:
    root = root.resolve()
    matrix = load_matrix()
    matrix_errors = validate_matrix(matrix)
    groups = [
        group_row(root, episode, group, stages)
        for group, stages in matrix_required_groups(matrix).items()
    ]
    counts = {"pass": 0, "fail": 0}
    for row in groups:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    payload = {
        "kind": GATE_POLICY_COVERAGE_KIND,
        "version": VERSION,
        "root": str(root),
        "episode": episode,
        "generated_at": now_iso(),
        "matrix": {
            "path": relpath(REPO_ROOT, LIB / "gate_policy_matrix.json"),
            "errors": matrix_errors,
            "stage_count": len((matrix.get("stages") or {})),
        },
        "groups": groups,
        "summary": {
            "groups": len(groups),
            "pass": counts.get("pass", 0),
            "fail": counts.get("fail", 0),
            "matrix_errors": len(matrix_errors),
            "release_required": sum(1 for row in groups if row.get("release_required")),
        },
        "status": "fail" if matrix_errors or counts.get("fail") else "pass",
    }
    return payload


def render_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# n2d Gate Policy Coverage",
        "",
        f"- 集：{payload.get('episode')}",
        f"- 状态：{payload.get('status')}",
        f"- summary：{payload.get('summary')}",
        "",
        "| group | release evidence | status | missing |",
        "|---|---:|---|---|",
    ]
    for row in payload.get("groups") or []:
        missing = ",".join(row.get("missing") or []) or "-"
        lines.append(f"| {row.get('group')} | {len(row.get('evidence') or [])} | {row.get('status')} | {missing} |")
    lines.append("")
    return "\n".join(lines)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_coverage(root: Path, episode: str, payload: Dict[str, Any]) -> Path:
    path = coverage_path(root, episode)
    atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    atomic_write(coverage_md_path(root, episode), render_markdown(payload))
    # Compatibility pointer for older scripts and humans looking for the generic name.
    atomic_write(production_dir(root) / "gate_policy_coverage.json", json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return path


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def check_coverage(root: Path, episode: str) -> Dict[str, Any]:
    path = coverage_path(root, episode)
    data = load_json(path)
    if not isinstance(data, dict) or data.get("kind") != GATE_POLICY_COVERAGE_KIND:
        return {"status": "fail", "issues": [f"missing or invalid {path}"], "path": str(path)}
    issues: List[str] = []
    if data.get("episode") != episode:
        issues.append(f"episode mismatch: {data.get('episode')} != {episode}")
    if data.get("status") != "pass":
        for row in data.get("groups") or []:
            if isinstance(row, dict) and row.get("status") != "pass":
                issues.append(f"{row.get('group')}: missing {','.join(row.get('missing') or [])}")
        for item in ((data.get("matrix") or {}).get("errors") or []):
            issues.append(f"matrix: {item}")
    return {"status": "fail" if issues else "pass", "issues": issues, "path": str(path)}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="build/check n2d gate policy coverage")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build")
    p.add_argument("root")
    p.add_argument("episode")
    p.add_argument("--write", action="store_true")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("check")
    p.add_argument("root")
    p.add_argument("episode")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("inventory", help="全量闸门自清点：检测 gate.py 里从 run() 不可达的死闸")
    p.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    if ns.cmd == "inventory":
        inv = gate_inventory()
        if ns.json:
            print(json.dumps(inv, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"gate inventory: {inv['reachable']}/{inv['total']} reachable, {len(inv['dead'])} dead")
            for item in inv.get("issues") or []:
                print(f"- {item}")
        return 1 if inv.get("status") != "pass" else 0
    root = Path(ns.root)
    if ns.cmd == "build":
        payload = build_coverage(root, ns.episode)
        if ns.write:
            path = write_coverage(root, ns.episode, payload)
            payload["path"] = str(path)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_markdown(payload))
        return 1 if payload.get("status") != "pass" else 0
    result = check_coverage(root, ns.episode)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else "\n".join(result.get("issues") or ["gate policy coverage ok"]))
    return 1 if result.get("status") != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
