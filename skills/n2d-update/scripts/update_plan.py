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
COMMON = os.path.join(REPO_SKILLS, "n2d", "_lib")
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
from n2d_platform_profiles import backend_supports_three_plus_frames  # noqa: E402
from n2d_findings_utils import findings_status

from skill_snapshot import (  # noqa: E402
    changed_files_since,
    is_test_path,
    now_iso,
    snapshot_for_skills,
)
from settings import get_setting as get_project_setting  # noqa: E402

KIND_SNAPSHOT = SKILL_UPDATE_SNAPSHOT_KIND
KIND_PLAN = SKILL_UPDATE_PLAN_KIND
SNAPSHOT_FILE = "skill_update_snapshot.json"
PLAN_PREFIX = "skill_update_plan"

ALWAYS_RELEVANT_SKILLS = {
    "n2d",
    "n2d-dashboard",
    "n2d-review",
    "n2d-batch",
    "n2d-update",
}
OBSERVE_ONLY_SKILLS = {
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
        current = route_key
    else:
        current = "script_stage1"
    last_started: Optional[str] = None
    for spec in stage_specs():
        if not spec.get("routes"):
            continue
        cols = [c for c in spec.get("progress_columns", ()) if c in header]
        if cols and any(is_started(row.get(c, "")) or cell_state(row.get(c, "")) == "done" for c in cols):
            last_started = str(spec["key"])
    if last_started and stage_index(last_started) > stage_index(current):
        return last_started
    return current


def current_todo_context(root: str, ep: str, header: List[str], row: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Return the user-facing current production gap, distinct from update scope.

    `current_stage_key` intentionally uses the furthest started stage as the
    update upper bound. This helper keeps the operational next step visible when
    an earlier stage is still partial, e.g. images 69/85 while video has started.
    """
    route = stage_of(root, row, header)
    cmd = route.get("cmd")
    if not cmd:
        return None
    col = route.get("col")
    stage_key = spec_key_for_route(route)
    status = row.get(str(col), "") if col else ""
    command = str(cmd).format(root=root, ep=ep)
    return {
        "stage_key": stage_key,
        "label": route.get("label"),
        "column": col,
        "status": status,
        "skill": route.get("skill"),
        "command": command,
        "note": route.get("note") or "",
    }


def image_qc_requires_repair(qc: Optional[Dict[str, Any]]) -> bool:
    """Whether existing image_qc findings should pull the operational todo back to image."""
    if not qc:
        return False
    if qc.get("status") in {"error", "unavailable"}:
        return True
    try:
        if int(qc.get("hard_blocks") or 0) > 0:
            return True
    except (TypeError, ValueError):
        pass
    return str(qc.get("verdict") or "").lower() == "block"


def image_qc_repair_todo(root: str, ep: str, row: Dict[str, str], qc: Dict[str, Any]) -> Dict[str, Any]:
    hard = qc.get("hard_blocks")
    verdict = qc.get("verdict") or qc.get("status") or "unknown"
    report = qc.get("report_md") or qc.get("report_json") or ""
    note = f"image_qc={verdict}"
    if hard not in (None, ""):
        note += f"，hard_blocks={hard}"
    if report:
        note += f"；先修复报告阻断并重跑 image_qc：{report}"
    return {
        "stage_key": "image",
        "label": "出图返修",
        "column": "出图",
        "status": row.get("出图", ""),
        "skill": "n2d-image",
        "command": f"n2d-image {root} {ep}",
        "note": note,
    }


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


# owner 跨多个阶段的 skill，按文件名片段映射到具体阶段，避免任何改动都从最早阶段重制。
# 未命中任何片段的文件保守回退到该 skill 拥有的最早相关阶段。
SKILL_FILE_STAGE_HINTS: Dict[str, Tuple[Tuple[str, Tuple[str, ...]], ...]] = {
    "n2d-script": (
        ("script_stage2", ("finalize_storyboard", "validate_timings", "delete_shot",
                           "分镜语法", "打斗分镜", "专项镜头模板库", "仙侠场面分镜")),
        ("script_stage1", ("split_novel", "拆集法", "boundary_audit")),
    ),
}

GATE_ONLY_FILE_STAGE_HINTS: Dict[str, Tuple[Tuple[str, Tuple[str, ...]], ...]] = {
    # 只改变出图落档机检/报告，不改变 prompt 或 PNG 生产产物。
    "n2d-image": (
        ("image", ("scripts/image_qc.py",)),
    ),
    # 后端探活/阈值/finding 工具只影响 gate/review 结论，不直接改变已生成媒体。
    "n2d": (
        ("image_prompt", ("_lib/image_backends.py",)),
    ),
}

# `skills/n2d/_lib` 是 n2d 运行期契约层；不能整体当 observe-only。
# 这里按文件影响面映射到最早需要回放的阶段。未列入的 _lib 文件默认保守回到
# script_stage1；确认为观测/维护工具的文件列入 N2D_LIB_OBSERVE_ONLY_TOKENS。
N2D_LIB_FILE_STAGE_HINTS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        "script_stage1",
        (
            "_lib/n2d_const.py",
            "_lib/n2d_schema.py",
            "_lib/n2d_logic.py",
            "_lib/n2d_route.py",
            "_lib/n2d_contract.py",
            "_lib/settings.py",
            "_lib/n2d_settings.py",
            "_lib/markdown_parser.py",
            "_lib/n2d_visual_styles.py",
        ),
    ),
    (
        "voice",
        (
            "_lib/voice_backends.py",
            "_lib/n2d_text_utils.py",
            "_lib/text_utils.py",
        ),
    ),
    (
        "script_stage2",
        (
            "_lib/n2d_platform_profiles.py",
        ),
    ),
    (
        "image_prompt",
        (
            "_lib/n2d_registry.py",
        ),
    ),
    (
        "compose",
        (
            "_lib/subtitle_render.py",
        ),
    ),
)

N2D_LIB_OBSERVE_ONLY_TOKENS: Tuple[str, ...] = (
    "_lib/skill_snapshot.py",
    "_lib/n2d_findings_utils.py",
    "_lib/n2d_thresholds.py",
    "_lib/n2d_telemetry.py",
    "_lib/freshness.py",
    "_lib/refresh.py",
    "_lib/n2d_contract_diff.py",
    "_lib/n2d_maintenance.py",
)

# 出图阶段是两层架构：共享定妆库（定妆照/场景照/identity_registry，全篇复用的锁定档案）
# + 本集分镜帧（一镜一图）。n2d-image 变更命中以下片段，才说明"共享定妆库生产规则"变了
# （标准三视图/角色一致性/资产注册/LoRA 一致性），此时定妆库本身需按最新规则复核、必要时重出。
# 否则 image 进入重制范围时，共享定妆库默认沿用——n2d-image 的"共享先行硬闸门"本就会复用已 ✅
# 的共享 PNG、只重出本集分镜帧；本规则把这层"定妆库默认沿用"在计划里显式说清。
SHARED_LOCK_PRODUCTION_TOKENS: Tuple[str, ...] = (
    "prompt_format",          # references §1.2 标准三视图/定妆生产铁律
    "角色一致性checklist",
    "资产身份注册层",
    "资产引用注册层",
    "lora_consistency",
    "identity_registry",
    "asset_registry",
)

N2D_IMAGE_SHARED_LOCK_RULE_FILES: Dict[str, str] = {
    "skills/n2d-image/SKILL.md": "skill_rule_unknown",
    "skills/n2d-image/references/prompt_format.md": "prompt_format",
    "skills/n2d-image/references/角色一致性checklist.md": "identity_checklist",
    "skills/n2d-image/references/资产身份注册层.md": "asset_identity_registry",
    "skills/n2d-image/references/资产引用注册层.md": "asset_reference_registry",
    "skills/n2d-image/references/lora_consistency.md": "lora_consistency",
    "skills/n2d-image/references/platforms.md": "backend_capability_rules",
}


def shared_lock_production_touched(changed_files: Iterable[str]) -> List[str]:
    """n2d-image 变更里命中"共享定妆库生产规则"的文件（三视图/一致性/资产注册/LoRA）。

    非空 = 定妆库本身可能漂移，需复核/重出；空 = image 重制时共享定妆库默认沿用。
    """
    hits: List[str] = []
    for path in changed_files:
        if skill_name_for_path(os.path.join(REPO_ROOT, path)) != "n2d-image":
            continue
        if n2d_image_shared_lock_impact(path):
            hits.append(path)
    return sorted(set(hits))


def n2d_image_shared_lock_impact(rel_path: str) -> Optional[str]:
    """Return why an n2d-image change requires shared lock review, if any.

    Known shared-lock rule files are explicit. Unknown n2d-image references and
    SKILL.md changes are treated as "review shared lock" instead of silently
    reusing lock assets, because prose rule updates can change定妆生产策略 without
    matching a filename token.
    """
    if rel_path in N2D_IMAGE_SHARED_LOCK_RULE_FILES:
        return N2D_IMAGE_SHARED_LOCK_RULE_FILES[rel_path]
    if rel_path.startswith("skills/n2d-image/references/"):
        return "unknown_reference_rule"
    if rel_path == "skills/n2d-image/SKILL.md":
        return "skill_rule_unknown"
    if any(tok in rel_path for tok in SHARED_LOCK_PRODUCTION_TOKENS):
        return "shared_lock_token"
    return None


def observe_only_changed_file(rel_path: str) -> bool:
    skill = skill_name_for_path(os.path.join(REPO_ROOT, rel_path))
    return bool(skill and skill in OBSERVE_ONLY_SKILLS)


def gate_only_stage_for_changed_file(rel_path: str, until_key: str) -> Optional[str]:
    skill = skill_name_for_path(os.path.join(REPO_ROOT, rel_path))
    if not skill:
        return None
    for stage_key, tokens in GATE_ONLY_FILE_STAGE_HINTS.get(skill, ()):
        if any(tok in rel_path for tok in tokens) and stage_index(stage_key) <= stage_index(until_key):
            return stage_key
    return None


def explicit_stage_hint_for_changed_file(rel_path: str, until_key: str) -> Optional[str]:
    """Map cross-cutting runtime-contract files to concrete production stages."""
    if rel_path.startswith("skills/n2d/_lib/"):
        if any(tok in rel_path for tok in N2D_LIB_OBSERVE_ONLY_TOKENS):
            return None
        for stage_key, tokens in N2D_LIB_FILE_STAGE_HINTS:
            if any(tok in rel_path for tok in tokens):
                return stage_key if stage_index(stage_key) <= stage_index(until_key) else None
        # Unknown runtime-contract files are safer to replay from the first routed stage.
        return "script_stage1" if stage_index("script_stage1") <= stage_index(until_key) else None
    return None


def artifact_affecting_changed_file(rel_path: str, until_key: str) -> bool:
    if gate_only_stage_for_changed_file(rel_path, until_key):
        return False
    if explicit_stage_hint_for_changed_file(rel_path, until_key):
        return True
    return not observe_only_changed_file(rel_path)


def stage_key_for_changed_file(rel_path: str, until_key: str) -> Optional[str]:
    if gate_only_stage_for_changed_file(rel_path, until_key):
        return None
    explicit = explicit_stage_hint_for_changed_file(rel_path, until_key)
    if explicit:
        return explicit
    skill = skill_name_for_path(os.path.join(REPO_ROOT, rel_path))
    if not skill or skill in OBSERVE_ONLY_SKILLS:
        return None
    owned = [str(spec["key"]) for spec in relevant_stage_specs(until_key) if spec.get("owner") == skill]
    if not owned:
        return None
    for stage_key, tokens in SKILL_FILE_STAGE_HINTS.get(skill, ()):
        if any(tok in rel_path for tok in tokens):
            # 命中的阶段超出该集当前进度 → 这次还不用重制。
            return stage_key if stage_key in owned else None
    return owned[0]


def earliest_rerun_stage(changed_files: Iterable[str], until_key: str) -> Optional[str]:
    keys = [k for k in (stage_key_for_changed_file(p, until_key) for p in changed_files) if k]
    if not keys:
        return None
    return sorted(keys, key=stage_index)[0]


def gate_refresh_stage_keys(changed_files: Iterable[str], until_key: str) -> List[str]:
    keys = {k for k in (gate_only_stage_for_changed_file(p, until_key) for p in changed_files) if k}
    return sorted(keys, key=stage_index)


def snapshot_skills(snap: Dict[str, Any]) -> Set[str]:
    skills = {str(s) for s in snap.get("skills") or [] if s}
    for path in snap.get("files") or {}:
        name = skill_name_for_path(os.path.join(REPO_ROOT, str(path)))
        if name:
            skills.add(name)
    return skills


def scoped_changed_files(
    old: Optional[Dict[str, Any]], new: Dict[str, Any], skills: Iterable[str]
) -> List[str]:
    """Diff old/new snapshots, restricted to files of the given skills.

    基线和本次相关范围可能不一致（record --all 的并集 vs 单集范围、阶段推进后
    新纳入的 skill）；只比交集内的文件，范围差异不算变更。
    """
    if not old:
        return []
    prefixes = tuple(f"skills/{s}/" for s in sorted(set(skills)))
    if not prefixes:
        return []

    def scoped(files: Dict[str, Any]) -> Dict[str, Any]:
        # is_test_path 再过滤一遍：兼容仍含测试文件条目的旧基线。
        return {k: v for k, v in files.items() if k.startswith(prefixes) and not is_test_path(k)}

    return changed_files_since(
        {"files": scoped(old.get("files") or {})},
        {"files": scoped(new.get("files") or {})},
    )


def is_stale_baseline(snap: Optional[Dict[str, Any]]) -> bool:
    """旧版 git 派生基线（只有 git_commit/dirty_files、无内容 `files` 表）。

    交付环境无 git，无法对这种基线 diff——必须提示用户重新 record 建立内容基线。
    """
    return bool(snap and snap.get("git_commit") and not isinstance(snap.get("files"), dict))


def build_baseline_snapshot(skills: Iterable[str]) -> Dict[str, Any]:
    """Build a content-hash baseline (git-free).

    交付铁律：基线只用文件内容 SHA256 快照，不依赖任何版本控制。
    """
    return snapshot_for_skills(REPO_ROOT, REPO_SKILLS, skills)


def baseline_changed_files(
    old: Optional[Dict[str, Any]], relevant_skills: Iterable[str], old_skills: Set[str]
) -> Tuple[List[str], bool]:
    """Diff the recorded baseline against the current skills tree (content-hash only).

    Restricted to skills present in BOTH the baseline and the current relevant
    scope (range differences from record --all vs single-episode are not changes).
    Returns (changed_paths, baseline_stale). `baseline_stale` is True only for a
    legacy git-derived baseline that has no content map and so cannot be diffed
    without git — the caller then asks the user to re-record.
    """
    if not old:
        return [], False
    if is_stale_baseline(old):
        return [], True
    scope = sorted(old_skills & set(relevant_skills))
    scope_prefixes = tuple(f"skills/{s}/" for s in scope)
    if not scope_prefixes:
        return [], False
    new = snapshot_for_skills(REPO_ROOT, REPO_SKILLS, relevant_skills)
    return scoped_changed_files(old, new, set(scope)), False


def plan_paths(root: str, ep: str) -> Tuple[str, str]:
    safe_ep = normalize_episode(ep)
    base = os.path.join(production_dir(root), f"{PLAN_PREFIX}_{safe_ep}")
    return base + ".json", base + ".md"


REGEN_MODE_MINIMAL = "最小"
REGEN_MODE_STRICT_REFRESH = "严审刷新"
LEGACY_REGEN_MODE_KEEP_IMAGES = "保图刷新"


def read_setting(root: str, key: str) -> Optional[str]:
    """Read one setting through n2d settings parser; project/global missing/empty -> None."""
    value = get_project_setting(root, key, "")
    return value.strip() if value else None


def resolve_regen_mode(root: str, cli_mode: Optional[str]) -> str:
    """更新重制策略选择点：CLI 显式 > `_设置.md` > 全局默认 > 默认 最小。"""
    if cli_mode:
        return REGEN_MODE_STRICT_REFRESH if cli_mode == LEGACY_REGEN_MODE_KEEP_IMAGES else cli_mode
    setting = read_setting(root, "更新重制策略")
    if setting == LEGACY_REGEN_MODE_KEEP_IMAGES:
        return REGEN_MODE_STRICT_REFRESH
    if setting in (REGEN_MODE_MINIMAL, REGEN_MODE_STRICT_REFRESH):
        return setting
    return REGEN_MODE_MINIMAL


def command_step(command: str, *, role: str = "command", run_when: str = "") -> Dict[str, str]:
    out = {"type": "command", "role": role, "command": command}
    if run_when:
        out["run_when"] = run_when
    return out


def agent_step(instruction: str, *, role: str = "agent_step") -> Dict[str, str]:
    return {"type": "agent_step", "role": role, "instruction": instruction}


def commands_from_steps(steps: Sequence[Dict[str, str]]) -> List[str]:
    return [s["command"] for s in steps if s.get("type") == "command" and s.get("command")]


def steps_for_strict_image_refresh(root: str, ep: str, start_key: Optional[str], until_key: str) -> List[Dict[str, str]]:
    """「严审刷新」命令序列：按最新 skill 刷新文字阶段/prompt → 对旧图按最新 prompt/QC 标准严审
    → 只把不符合最新标准的镜排进重出。旧图不是默认受保护对象。"""
    epn = ep.replace("第", "").replace("集", "")
    # 文字阶段刷新起点：取改动起点，但不晚于出图 prompt；先让最新 prompt 成为审旧图的标准。
    text_start = start_key if (start_key and stage_index(start_key) < stage_index("image")) else "image_prompt"
    qc = f'python3 skills/n2d-image/scripts/image_qc.py "{root}" {ep}'
    return [
        # 1) 按最新 skill 刷新分镜/出图 prompt，生成新的审查标准。
        command_step(
            f'python3 skills/n2d-batch/scripts/queue.py plan "{root}" --episodes {epn} '
            f'--rerun-from {text_start} --scope "严审刷新·按最新skill刷新文字阶段与出图prompt" '
            '--max-concurrency 1 --max-retries 1',
            role="queue_text_prompt_refresh",
        ),
        # 2) 用最新 prompt/QC/review 标准严审现有图片：block/warn/降级都先列入候选重出。
        command_step(f'{qc} --regen-list --strict', role="collect_strict_image_evidence"),
        # 3) 只把严审命中的镜排进重生成；为空表示最新证据未发现需要舍弃的旧图。
        command_step(
            (
                f'if ! shots=$({qc} --affected-shots --strict); then\n'
                '  echo "image_qc --affected-shots --strict failed" >&2\n'
                '  exit 1\n'
                'fi\n'
                'if [ -n "$shots" ]; then\n'
                f'  python3 skills/n2d-batch/scripts/queue.py plan "{root}" --episodes {epn} '
                f'--rerun-from image $shots --scope "严审刷新·重出不符合最新prompt/QC标准的镜" '
                '--max-concurrency 1 --max-retries 1\n'
                'else\n'
                '  echo "严审未发现需舍弃旧图的镜"\n'
                'fi'
            ),
            role="queue_failed_strict_image_shots",
        ),
        # 4) 重出的镜回验像素一致性（dashboard gate --stage image 已含 image_qc）
        command_step(
            image_qc_verify_command(root, ep),
            role="verify_after_image_regen",
            run_when="仅在 n2d-batch/阶段 skill 已实际完成图片重出后运行；只生成队列计划时不要当作已验收。",
        ),
    ]


def commands_for_strict_image_refresh(root: str, ep: str, start_key: Optional[str], until_key: str) -> List[str]:
    return commands_from_steps(steps_for_strict_image_refresh(root, ep, start_key, until_key))


def rerun_covers_image(start_key: Optional[str], until_key: str) -> bool:
    """重制范围 [start_key, until_key] 是否覆盖 image 阶段（= 会重出 PNG）。纯函数·可测。"""
    img = stage_index("image")
    if img >= 10**6:           # 契约里没有 image 阶段（异常）→ 不追加
        return False
    lo = stage_index(start_key) if start_key else 0
    return lo <= img <= stage_index(until_key)


def image_qc_verify_command(root: str, ep: str) -> str:
    """A：重出图后验像素一致性的验证步。dashboard gate --stage image 已内含 image_qc
    （崩脸/服装/场景/接缝/lint + CHAR_xx 合法性），是重出图后该回到的验证点。"""
    return (f"python3 skills/n2d-dashboard/scripts/dashboard.py gate \"{root}\" {ep} --stage image"
            "  # 重出图后验像素一致性（含 image_qc）")


def gate_refresh_commands(root: str, ep: str, stage_keys: Sequence[str]) -> List[str]:
    return commands_from_steps(gate_refresh_steps(root, ep, stage_keys))


def gate_refresh_steps(root: str, ep: str, stage_keys: Sequence[str]) -> List[Dict[str, str]]:
    steps: List[Dict[str, str]] = []
    for stage_key in stage_keys:
        gate_stage = (stage_for_key(stage_key) or {}).get("gate_stage")
        if gate_stage:
            steps.append(command_step(
                f"python3 skills/n2d-dashboard/scripts/dashboard.py gate \"{root}\" {ep} --stage {gate_stage}",
                role="refresh_gate",
            ))
    return steps


def review_refresh_commands(root: str, ep: str, until_key: str) -> List[str]:
    return commands_from_steps(review_refresh_steps(root, ep, until_key))


def review_refresh_steps(root: str, ep: str, until_key: str) -> List[Dict[str, str]]:
    """Refresh cross-cutting review/gate outputs without implying artifact rebuilds."""
    steps: List[Dict[str, str]] = []
    gate_stage = (stage_for_key(until_key) or {}).get("gate_stage")
    if gate_stage:
        steps.append(command_step(
            f"python3 skills/n2d-dashboard/scripts/dashboard.py gate \"{root}\" {ep} --stage {gate_stage}",
            role="refresh_gate",
        ))
    if stage_index(until_key) >= stage_index("image"):
        steps.append(command_step(
            f"python3 skills/n2d-review/scripts/consistency_audit.py \"{root}\" {ep}"
            "  # 刷新 review findings；不重制产物",
            role="refresh_review_findings",
        ))
    if not steps:
        steps.append(command_step("python3 skills/n2d-review/scripts/self_audit.py --json",
                                  role="self_audit"))
    return steps


def image_qc_report_path(root: str, ep: str) -> str:
    ep = normalize_episode(ep)
    return os.path.join(production_dir(root), "image_qc", ep, f"image_qc_{ep}.json")


def load_image_qc_context(root: str, ep: str) -> Optional[Dict[str, Any]]:
    """Read current image_qc environment/stage-jump summary if it exists.

    n2d-update should not rerun paid/visual work by itself, but when image work is
    already present, the plan must carry the latest QC capability banner so users
    know whether to install dependencies, stay on image, or proceed.
    """
    path = image_qc_report_path(root, ep)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        return {
            "status": "error",
            "report_json": path,
            "report_md": os.path.splitext(path)[0] + ".md",
            "error": f"{type(exc).__name__}: {exc}",
        }
    env = data.get("qc_environment") or {}
    summary = data.get("summary") or {}
    if not isinstance(env, dict) or not env:
        return {
            "status": "unavailable",
            "report_json": path,
            "report_md": os.path.splitext(path)[0] + ".md",
            "error": "image_qc report missing qc_environment",
        }

    # Prefer hard blocker samples from image_qc itself; the broader findings pool
    # also contains non-blocking visual-review samples whose detector-level
    # "block" wording is advisory, and is misleading in this image_qc banner.
    active, _ = findings_status(root, ep)
    samples = image_qc_hard_samples(data) or active.get("samples") or []

    return {
        "status": "ok",
        "report_json": path,
        "report_md": os.path.splitext(path)[0] + ".md",
        "precision_level": env.get("precision_level"),
        "python": env.get("python"),
        "recommended_install": env.get("recommended_install") or "",
        "jump_to_stage": env.get("jump_to_stage"),
        "jump_reason": env.get("jump_reason"),
        "user_notice": env.get("user_notice"),
        "verdict": summary.get("verdict"),
        "hard_blocks": summary.get("hard_blocks"),
        "advisory": summary.get("advisory"),
        "degraded": summary.get("degraded"),
        "finding_samples": samples,
    }


def image_qc_hard_samples(data: Dict[str, Any]) -> List[str]:
    samples: List[str] = []
    face = (((data.get("checks") or {}).get("face") or {}).get("shots") or [])
    if isinstance(face, list):
        for row in face:
            if not isinstance(row, dict) or str(row.get("verdict") or "").lower() != "block":
                continue
            png = row.get("png") or row.get("shot") or ""
            samples.append(f"崩脸 G1: {png}")
            if len(samples) >= 3:
                return samples
    lint = ((data.get("lint") or {}).get("findings") or [])
    if isinstance(lint, list):
        for row in lint:
            if not isinstance(row, dict) or str(row.get("level") or "").lower() != "block":
                continue
            msg = row.get("msg") or row.get("code") or ""
            shot = row.get("shot") or ""
            samples.append(f"prompt lint: {shot} {msg}".strip())
            if len(samples) >= 3:
                return samples
    coverage = data.get("face_reference_coverage") or {}
    if isinstance(coverage, dict):
        for row in coverage.get("missing") or []:
            if isinstance(row, dict):
                samples.append(f"脸部覆盖缺失: {row.get('png') or row.get('shot') or row}")
            else:
                samples.append(f"脸部覆盖缺失: {row}")
            if len(samples) >= 3:
                return samples
    return samples


def steps_for_rerun(root: str, ep: str, start_key: Optional[str], until_key: str,
                    shared_lock_reuse: bool = False) -> List[Dict[str, str]]:
    if not start_key:
        gate_stage = (stage_for_key(until_key) or {}).get("gate_stage")
        if not gate_stage:
            return [command_step(f"python3 skills/n2d-update/scripts/update_plan.py record \"{root}\" {ep}",
                                 role="record_snapshot")]
        return [
            command_step(f"python3 skills/n2d-dashboard/scripts/dashboard.py gate \"{root}\" {ep} --stage {gate_stage}",
                         role="refresh_gate"),
        ]
    start = stage_for_key(start_key) or {}
    # 定妆库默认沿用时，把"复用共享定妆库·只重出本集分镜帧"写进队列 scope，记录意图；
    # n2d-image 共享先行硬闸门会跳过已 ✅ 的共享 PNG，实际不重出定妆/场景。
    scope = f"skill 更新后重制到 {until_key}"
    if shared_lock_reuse:
        scope += "·复用共享定妆库·只重出本集分镜帧"
    steps: List[Dict[str, str]] = [
        command_step(
            "python3 skills/n2d-batch/scripts/queue.py plan "
            f"\"{root}\" --episodes {ep.replace('第', '').replace('集', '')} "
            f"--rerun-from {start_key} --scope \"{scope}\" "
            "--max-concurrency 1 --max-retries 1"
            ,
            role="queue_bounded_rerun",
        ),
        agent_step(
            "排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。"
            f" 手工替代路径仅在不使用 batch 时执行：`{str(start.get('command', '')).format(root=root, ep=ep)}`",
            role="manual_alternative",
        ),
    ]
    # A：重制范围覆盖出图 → 追加出图落档机检验证步（避免"重出图后没人验像素"）
    if rerun_covers_image(start_key, until_key):
        steps.append(command_step(
            image_qc_verify_command(root, ep),
            role="verify_after_image_regen",
            run_when="仅在 n2d-batch/阶段 skill 已实际完成图片重出后运行；只生成队列计划时不要当作已验收。",
        ))
    return steps


def command_for_rerun(root: str, ep: str, start_key: Optional[str], until_key: str,
                      shared_lock_reuse: bool = False) -> List[str]:
    return commands_from_steps(steps_for_rerun(root, ep, start_key, until_key, shared_lock_reuse=shared_lock_reuse))


def render_markdown(plan: Dict[str, Any]) -> str:
    changed = plan.get("changed_files", [])
    action = "重制" if plan.get("rebuild_needed") else (
        "刷新 gate/QC" if plan.get("gate_refresh_needed") else "只重跑 gate/review"
    )
    from_label = ",".join(plan.get("gate_refresh_stages") or ["gate/review"]) if (
        plan.get("gate_refresh_needed") and not plan.get("rebuild_needed")
    ) else (plan.get("rerun_from") or "gate/review")
    lines = [
        f"# skill 更新重制计划 — {plan['episode']}",
        "",
        f"- 作品根：`{plan['root']}`",
        f"- 当前阶段：`{plan['current_stage']}`",
        f"- 建议动作：`{action}` · `{from_label}` → `{plan['rerun_until']}`",
        f"- 需要重制：{'是' if plan.get('rebuild_needed') else '否'}",
        f"- 重制策略：`{plan.get('regen_mode', REGEN_MODE_MINIMAL)}`"
        + ("（严审：按最新 prompt/QC 标准复核旧图，不符合即舍弃重出）" if plan.get("strict_image_refresh") else ""),
    ]
    if plan.get("shared_lock_reuse"):
        lines.append("- 共享定妆库：默认沿用（定妆照/场景照 PNG 复用，重制只覆盖本集分镜帧）")
    elif plan.get("shared_lock_changed_files"):
        lines.append(
            "- 共享定妆库：需复核（变更命中定妆库生产规则："
            + ", ".join(plan["shared_lock_changed_files"]) + "）"
        )
    if plan.get("gate_refresh_needed"):
        lines.append(f"- 需刷新 gate/QC：是（{', '.join(plan.get('gate_refresh_stages') or [])}）")
    if plan.get("needs_record"):
        lines.append("- 基线：缺失，先 `record` 后才能稳定做快照比对。")
    if plan.get("changed_skills"):
        lines.append(f"- 变动 skill：{', '.join(plan['changed_skills'])}")
    if plan.get("newly_relevant_skills"):
        lines.append(f"- 新纳入范围（不计变更）：{', '.join(plan['newly_relevant_skills'])}")
    if changed:
        lines.extend(["", "## 变动文件"])
        lines.extend(f"- `{p}`" for p in changed[:80])
        if len(changed) > 80:
            lines.append(f"- ... 另有 {len(changed) - 80} 个文件")
    todo = plan.get("current_todo")
    if todo:
        lines.extend([
            "",
            "## 当前生产缺口",
            f"- 当前待办：`{todo.get('label')}`（{todo.get('column')} = `{todo.get('status')}`）",
            f"- 建议 skill：`{todo.get('skill')}`",
            f"- 建议命令：`{todo.get('command')}`",
        ])
        if todo.get("stage_key") and todo.get("stage_key") != plan.get("current_stage"):
            lines.append(
                f"- 说明：更新影响上界仍按最远已开始产物 `{plan.get('current_stage')}` 计算；"
                f"当前待办按进度表首个未完成阶段 `{todo.get('stage_key')}` 计算。"
            )
        if todo.get("note"):
            lines.append(f"- 备注：{todo.get('note')}")
    qc = plan.get("image_qc_environment")
    if qc:
        lines.extend(["", "## 图片质检环境与阶段跳转"])
        if qc.get("status") in {"error", "unavailable"}:
            lines.append(f"- 状态：`{qc.get('status')}` — {qc.get('error') or qc.get('reason')}")
            lines.append(f"- 报告：`{qc.get('report_md')}`")
        else:
            lines.extend([
                f"- 机检能力：`{qc.get('precision_level')}`",
                f"- 当前解释器：`{qc.get('python')}`",
                f"- 当前 image_qc：`verdict={qc.get('verdict')}`，硬阻断 `{qc.get('hard_blocks')}`，非阻断初筛 `{qc.get('advisory')}`，降级 `{qc.get('degraded')}`",
            ])
            if qc.get("finding_samples"):
                samples = " | ".join(qc["finding_samples"])
                lines.append(f"- block 摘要：{samples}")
            lines.extend([
                f"- 当前应停在/回退：`{qc.get('jump_to_stage')}` — {qc.get('jump_reason')}",
                f"- 建议安装：{qc.get('recommended_install') or '无需补装'}",
                f"- 报告：`{qc.get('report_md')}`",
            ])

    sd = plan.get("source_drift")
    tf = plan.get("three_frame_compliance")
    ic = plan.get("image_consistency")
    ci = plan.get("contract_inheritance")
    if sd or tf or ic or ci:
        lines.extend(["", "## 健康检测（源/三帧/图片/契约继承）"])
        if sd:
            st = sd.get("status")
            mark = {"clean": "✅ 源未变动", "drift": "⚠️ 源已漂移",
                    "no_baseline": "— 源未建基线",
                    "error": "⚠️ 源检测失败",
                    "unavailable": "⚠️ 源检测不可用"}.get(st, f"源状态={st}")
            chs = sd.get("changed_chapters") or sd.get("changed") or []
            lines.append(f"- **源小说**：{mark}" + (f"（变动 {len(chs)} 章）" if chs else ""))
        if tf:
            if not tf.get("enforced"):
                lines.append(f"- **三帧契约**：豁免（后端 `{tf.get('backend')}` 不支持≥3帧·能力门控）")
            elif tf.get("compliant"):
                lines.append(f"- **三帧契约**：✅ 达标（{tf.get('total_clips')} Clip 全有锚帧/豁免）")
            else:
                vc = tf.get("violating_clips") or []
                lines.append(
                    f"- **三帧契约**：⚠️ {len(vc)}/{tf.get('total_clips')} Clip 缺中段锚帧"
                    f"（后端 `{tf.get('backend')}` 强制）：{', '.join(vc[:8])}"
                    + (f" 等" if len(vc) > 8 else "")
                )
        if ic:
            if ic.get("status") in {"error", "unavailable"}:
                flag = f"⚠️ 检测{ic.get('status')}"
            else:
                flag = "✅ 无硬阻断" if ic.get("consistent") else f"⚠️ hard_blocks={ic.get('hard_blocks')}"
            lines.append(f"- **图片一致性**：{flag}（verdict=`{ic.get('verdict')}`，精度 `{ic.get('precision_level')}`）")
        if ci:
            st = ci.get("status")
            if st == "missing":
                lines.append("- **契约继承**：— 未校验（缺 inherit_contract 报告，先跑 n2d-video `inherit_contract.py`）")
            elif st == "error":
                lines.append(f"- **契约继承**：⚠️ 报告不可读（{ci.get('error')}）")
            elif ci.get("inherited"):
                lines.append(f"- **契约继承**：✅ 已继承（verdict=`{ci.get('verdict')}`）")
            else:
                lines.append(
                    f"- **契约继承**：⛔ block（verdict=`{ci.get('verdict')}`，字段漂移 "
                    f"{ci.get('field_blocks')}·身份未锁 {ci.get('identity_blocks')}·资产丢失 {ci.get('asset_blocks')}）"
                    + (f"：{'; '.join(ci.get('samples') or [])}" if ci.get("samples") else "")
                )

    steps = plan.get("execution_steps") or []
    if steps:
        lines.extend(["", "## 执行步骤"])
        for idx, step in enumerate(steps, start=1):
            role = step.get("role") or step.get("type") or "step"
            if step.get("type") == "command":
                lines.append(f"{idx}. `{role}`")
                if step.get("run_when"):
                    lines.append(f"   - 运行条件：{step.get('run_when')}")
                lines.append(f"```bash\n{step.get('command', '')}\n```")
            else:
                lines.append(f"{idx}. `{role}`：{step.get('instruction', '')}")
    elif plan.get("commands"):
        lines.extend(["", "## 建议命令"])
        lines.extend(f"```bash\n{cmd}\n```" for cmd in plan["commands"])
    if plan.get("smart_suggestions"):
        lines.extend(["", "## 智能优化建议"])
        for item in plan["smart_suggestions"]:
            lines.append(
                f"- `{item.get('priority', 'medium')}` {item.get('character_name') or item.get('character_id')} "
                f"@ {item.get('backend')}: {item.get('action')}（{item.get('reason')}）"
            )
    if plan.get("smart_suggestions_error"):
        lines.extend(["", "## 智能优化建议"])
        lines.append(f"- 生成失败：{plan.get('smart_suggestions_error')}")
    if plan.get("notes"):
        lines.extend(["", "## 备注"])
        lines.extend(f"- {note}" for note in plan["notes"])
    lines.append("")
    return "\n".join(lines)


SOURCE_CHECK = os.path.join(REPO_SKILLS, "n2d", "source_check.py")


def detect_source_drift(root: str) -> Optional[Dict[str, Any]]:
    """检测「源文件=小说」是否变动：跑 n2d/source_check.py，解析末行 DRIFT={...}。

    只在已有源指纹基线（`小说/_源指纹.json`）时跑（否则无基线可比、且省去 subprocess）。
    返回 source_check 的 DRIFT dict（status: clean/drift/no_baseline/...）或 None（无基线/不可用）。
    """
    if not os.path.isfile(os.path.join(root, "小说", "_源指纹.json")):
        return None
    if not os.path.isfile(SOURCE_CHECK):
        return {"status": "unavailable", "reason": "source_check_missing", "script": SOURCE_CHECK}
    try:
        proc = subprocess.run([sys.executable, SOURCE_CHECK, root],
                              capture_output=True, text=True, timeout=120)
    except Exception as exc:
        return {"status": "error", "reason": f"{type(exc).__name__}: {exc}", "script": SOURCE_CHECK}
    for line in reversed((proc.stdout or "").splitlines()):
        if line.startswith("DRIFT="):
            try:
                return json.loads(line[len("DRIFT="):])
            except Exception as exc:
                return {"status": "error", "reason": f"invalid_drift_json:{type(exc).__name__}", "script": SOURCE_CHECK}
    return {
        "status": "error",
        "reason": f"source_check_no_drift_line:exit={proc.returncode}",
        "script": SOURCE_CHECK,
        "stderr": (proc.stderr or "")[:1000],
    }


def storyboard_path_for(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", normalize_episode(ep), "storyboard.json")


def check_three_frame_compliance(root: str, ep: str) -> Optional[Dict[str, Any]]:
    """检测本集 clip 是否遵循「至少三帧契约」（能力门控）。

    读 storyboard.json：按 policy.video_backend 的后端能力判定是否强制；列出缺
    midframe/anchors 且无豁免理由的违规 Clip。storyboard 未定稿则返回 None（无可检对象）。
    """
    path = storyboard_path_for(root, ep)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            sb = json.load(fh)
    except Exception:
        return None
    clips = sb.get("clips") if isinstance(sb, dict) else None
    if not isinstance(clips, list) or not clips:
        return None
    policy = sb.get("policy") if isinstance(sb.get("policy"), dict) else {}
    backend = policy.get("video_backend")
    enforced = backend_supports_three_plus_frames(backend)
    violating: List[str] = []
    exempt = 0
    for i, clip in enumerate(clips, 1):
        cont = (clip.get("continuity") or {}) if isinstance(clip, dict) else {}
        if has_valid_midframe(cont.get("midframe")) or has_valid_anchors(cont.get("anchors")):
            continue
        if cont.get("midframe_exempt_reason"):
            exempt += 1
            continue
        violating.append(str((clip.get("id") if isinstance(clip, dict) else None) or f"clip#{i}"))
    return {
        "backend": backend,
        "enforced": enforced,
        "total_clips": len(clips),
        "exempt_clips": exempt,
        "violating_clips": violating,
        # 后端不支持≥3帧（唯一豁免）时不算违规；强制时缺锚帧才违规。
        "compliant": (not enforced) or (not violating),
    }


def has_valid_frame_ref(value: Any, keys: Sequence[str]) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(str(value.get(k) or "").strip() for k in keys)
    return False


def has_valid_midframe(value: Any) -> bool:
    return has_valid_frame_ref(value, ("midframe_png", "anchor_png", "png", "path", "image"))


def has_valid_anchors(value: Any) -> bool:
    if isinstance(value, dict):
        return has_valid_frame_ref(value, ("anchor_png", "midframe_png", "png", "path", "image"))
    if not isinstance(value, list) or not value:
        return False
    return any(has_valid_frame_ref(item, ("anchor_png", "midframe_png", "png", "path", "image")) for item in value)


def summarize_image_consistency(qc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """从已有 image_qc 报告上下文压出「图片一致性」摘要（崩脸/服装/场景/接缝硬阻断）。"""
    if not qc:
        return None
    if qc.get("status") in {"error", "unavailable"}:
        return {
            "status": qc.get("status"),
            "verdict": qc.get("status"),
            "hard_blocks": None,
            "advisory": None,
            "degraded": None,
            "precision_level": qc.get("precision_level"),
            "report_md": qc.get("report_md"),
            "samples": [qc.get("error") or qc.get("reason") or "image_qc unavailable"],
            "consistent": False,
        }
    return {
        "status": qc.get("status") or "ok",
        "verdict": qc.get("verdict"),
        "hard_blocks": qc.get("hard_blocks"),
        "advisory": qc.get("advisory"),
        "degraded": qc.get("degraded"),
        "precision_level": qc.get("precision_level"),
        "report_md": qc.get("report_md"),
        "samples": qc.get("finding_samples") or [],
        "consistent": (qc.get("hard_blocks") in (0, None)),
    }


def contract_inheritance_report_path(root: str, ep: str) -> str:
    ep = normalize_episode(ep)
    return os.path.join(production_dir(root), f"contract_inheritance_{ep}.json")


def check_contract_inheritance(root: str, ep: str) -> Optional[Dict[str, Any]]:
    """读 出图→出视频「视觉契约继承」报告（n2d-video/inherit_contract.py 产物）。

    校验参考帧契约（色调/光位锚/轴线视线/角色状态演进/景别）与文字 prompt 是否从出图侧
    正确传递到出视频侧，外加身份交接（命名角色镜逐镜 prompt 锁脸）与物料交接
    （场景/道具/服装/特效资产不丢）。只读已有报告，不自己跑 inherit_contract——付费/出视频
    前的机检由 n2d-video 负责。报告缺失但已到 video_prompt 阶段时返回 missing，提示先跑
    inherit_contract 取证；报告不可读返回 error。
    """
    path = contract_inheritance_report_path(root, ep)
    md_path = os.path.splitext(path)[0] + ".md"
    if not os.path.isfile(path):
        return {
            "status": "missing",
            "report_json": path,
            "report_md": md_path,
            "inherited": False,
        }
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        return {
            "status": "error",
            "report_json": path,
            "report_md": md_path,
            "error": f"{type(exc).__name__}: {exc}",
            "inherited": False,
        }
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    identity = (data.get("identity_handoff") or {}).get("findings") or []
    asset = (data.get("asset_handoff") or {}).get("findings") or []
    identity_blocks = [f for f in identity if f.get("severity") == "block"]
    asset_blocks = [f for f in asset if f.get("severity") == "block"]
    field_drift = [
        f"{r.get('field')}: {r.get('status')}"
        for r in (data.get("fields") or [])
        if r.get("severity") == "block"
    ]
    verdict = data.get("verdict")
    return {
        "status": "ok",
        "verdict": verdict,
        "field_blocks": summary.get("block"),
        "field_warns": summary.get("warn"),
        "identity_blocks": len(identity_blocks),
        "asset_blocks": len(asset_blocks),
        "report_json": path,
        "report_md": md_path,
        "generated_at": data.get("generated_at"),
        "samples": (
            field_drift
            + [f"身份未锁 {f.get('clip_id')}: {f.get('code')}" for f in identity_blocks]
            + [f"资产丢失 {f.get('clip_id')}: {f.get('code')}" for f in asset_blocks]
        )[:6],
        # 契约可有意收紧/细化，只有 verdict=block（光位锚/轴线漂移、身份未锁、资产丢失）才算未继承。
        "inherited": verdict != "block",
    }


def build_plan(root: str, ep: str, *, regen_mode: Optional[str] = None) -> Dict[str, Any]:
    root = os.path.abspath(root)
    ep = normalize_episode(ep)
    header, rows = rows_by_episode(root)
    if ep not in rows:
        raise SystemExit(f"未在 _进度.md 找到 {ep}")
    row = rows[ep]
    progress_until_key = current_stage_key(root, ep, header, row)
    image_qc_context = (
        load_image_qc_context(root, ep)
        if stage_index(progress_until_key) >= stage_index("image")
        else None
    )
    qc_forces_image_repair = image_qc_requires_repair(image_qc_context)
    until_key = "image" if qc_forces_image_repair and stage_index(progress_until_key) > stage_index("image") else progress_until_key
    current_todo = current_todo_context(root, ep, header, row)
    if qc_forces_image_repair:
        current_todo = image_qc_repair_todo(root, ep, row, image_qc_context or {})
    relevant_skills = relevant_skills_for_stage(until_key)
    old = load_snapshot(root)
    old_skills = snapshot_skills(old) if old else set()
    newly_relevant = sorted(set(relevant_skills) - old_skills) if old else []
    snapshot_changes, baseline_stale = baseline_changed_files(
        old, relevant_skills, old_skills
    )
    changed = set(snapshot_changes)
    changed_files = sorted(changed)
    changed_skills = sorted({skill_name_for_path(os.path.join(REPO_ROOT, p)) or "" for p in changed_files} - {""})
    gate_refresh_stages = gate_refresh_stage_keys(changed_files, until_key)
    artifact_changed_files = [
        p for p in changed_files
        if artifact_affecting_changed_file(p, until_key)
    ]
    rerun_from = earliest_rerun_stage(artifact_changed_files, until_key)
    # 不变量：rebuild_needed 必须配有可执行的回放起点 rerun_from。artifact 文件虽变，
    # 但都映射不到本集已达阶段（横切层 / 仅涉及尚未到达的阶段）时，没有可跑的重制起点，
    # 不能报“建议重制”——转 gate/审查刷新，否则下游（n2d-batch）会拿到 rerun_from=None 无从执行。
    unmapped_artifact_changes = bool(artifact_changed_files) and rerun_from is None
    rebuild_needed = rerun_from is not None
    gate_refresh_needed = bool(gate_refresh_stages)
    # 出图两层：共享定妆库默认沿用，除非变更命中定妆库生产规则。
    image_in_scope = rebuild_needed and rerun_covers_image(rerun_from, until_key)
    shared_lock_changed = shared_lock_production_touched(changed_files)
    shared_lock_reuse = image_in_scope and not shared_lock_changed
    notes: List[str] = []
    if qc_forces_image_repair and progress_until_key != until_key:
        notes.append(
            f"image_qc 硬阻断已将当前生产阶段从 `{progress_until_key}` 拉回 `{until_key}`；"
            "先做 n2d-image 返修并重跑 image_qc，不进入下游。"
        )
    if not old:
        notes.append("当前作品没有 skill_update_snapshot 基线；首次无法检测变更，请先 record 建立内容快照基线。")
    if baseline_stale:
        notes.append("基线为旧版格式（无内容快照、不可用于变更检测）；请重新 record 建立内容基线。")
    if newly_relevant:
        notes.append(
            f"{', '.join(newly_relevant)} 因阶段推进首次纳入相关范围，本次不计为变更；该阶段完成后请 record 刷新基线。"
        )
    if changed_files and not artifact_changed_files and gate_refresh_needed:
        notes.append("变动只影响 QC/gate 报告，不重制 prompt/图片/视频；重跑对应 gate 刷新结论即可。")
    elif changed_files and not artifact_changed_files:
        notes.append("变动集中在 n2d/_lib/review/dashboard/batch/n2d-update 等横切层，不默认重制生产产物；先刷新当前 gate/审查 findings。")
    elif unmapped_artifact_changes:
        notes.append("变动集中在 n2d/_lib/review/dashboard/batch/n2d 等横切层，或只涉及该集尚未到达的阶段文件；先重跑 gate/审查/计划，不默认重抽图。")
    if rebuild_needed and rerun_from:
        notes.append("真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。")
    if image_in_scope and shared_lock_reuse:
        notes.append(
            "共享定妆库默认沿用：本次变更未命中定妆库生产规则（标准三视图/角色一致性/资产注册/LoRA），"
            "`出图/共享/图片/` 的定妆照/场景照 PNG 与 identity_registry 复用不重出，重制范围只覆盖本集分镜帧。"
            "n2d-image 共享先行硬闸门会跳过已 ✅ 的共享 PNG，直接以其为参考重出分镜。"
        )
    elif image_in_scope and shared_lock_changed:
        notes.append(
            "共享定妆库需复核（非默认沿用）：本次变更命中定妆库生产规则（"
            + ", ".join(shared_lock_changed)
            + "）。先按最新规则复核、必要时重出共享定妆/场景，再用 "
            "`python3 skills/n2d-image/scripts/asset_impact.py <作品根> <改动的定妆资产>` "
            "级联出引用它、需跟着重出的本集分镜。"
        )

    mode = resolve_regen_mode(root, regen_mode)
    strict_image_refresh = (mode == REGEN_MODE_STRICT_REFRESH and rebuild_needed
                            and rerun_covers_image(rerun_from, until_key))
    if strict_image_refresh:
        execution_steps = steps_for_strict_image_refresh(root, ep, rerun_from, until_key)
        notes.append(
            "【严审刷新】本模式不是保旧图：先按最新 skill 刷新文字阶段与出图 prompt，"
            "再用最新 prompt/QC/review 标准严审现有图片；凡 block/warn/降级或人工判定不符合预期的镜，"
            "都应舍弃旧图并排入重出。只有已有 finding/人工判定明确可沿用的镜，才允许保留。"
        )
    elif rebuild_needed:
        execution_steps = steps_for_rerun(root, ep, rerun_from, until_key, shared_lock_reuse=shared_lock_reuse)
    elif gate_refresh_needed:
        execution_steps = gate_refresh_steps(root, ep, gate_refresh_stages)
    elif changed_files:
        execution_steps = review_refresh_steps(root, ep, until_key)
    else:
        execution_steps = []
    commands = commands_from_steps(execution_steps)
    # 四项健康检测（除 skill 变更外）：源小说漂移 / 三帧契约遵循 / 图片一致性 / 出图→出视频契约继承。
    source_drift = detect_source_drift(root)
    three_frame = check_three_frame_compliance(root, ep)
    image_consistency = summarize_image_consistency(image_qc_context)
    # 契约继承（参考帧契约+文字 prompt 是否正确传到出视频侧）：到 video_prompt 阶段才有可检对象。
    contract_inheritance = (
        check_contract_inheritance(root, ep)
        if stage_index(progress_until_key) >= stage_index("video_prompt")
        else None
    )
    if source_drift and source_drift.get("status") == "drift":
        chs = source_drift.get("changed_chapters") or source_drift.get("changed") or []
        notes.append(
            f"源小说已变动（{len(chs)} 章漂移）：写小说成品改了，本剧源过期。"
            "重切属不可逆/花钱点——先看 `source_check.py` 报告，确认后再决定重切哪些集。"
        )
    elif source_drift and source_drift.get("status") in {"error", "unavailable"}:
        notes.append(
            f"源小说漂移检测不可用（status={source_drift.get('status')}，reason={source_drift.get('reason')}）；"
            "这不是源未变动，需先修复检测再判断是否重切。"
        )
    if three_frame and three_frame.get("enforced") and not three_frame.get("compliant"):
        vc = three_frame.get("violating_clips") or []
        notes.append(
            f"三帧契约未达标：{len(vc)} 个 Clip 缺中段锚帧（后端 {three_frame.get('backend')} 支持≥3帧·强制）。"
            "回 n2d-script 跑 `anchor_planner.py <作品根> "
            f"{ep} --write` 补齐，再出 `_mid` 帧。违规：{', '.join(vc[:6])}"
            + (f" 等 {len(vc)} 个" if len(vc) > 6 else "")
        )
    elif three_frame and not three_frame.get("enforced"):
        notes.append(
            f"三帧契约豁免：路由后端 {three_frame.get('backend')} 不支持≥3帧（能力门控自动豁免），本集不强制中段锚帧。"
        )
    if image_consistency and not image_consistency.get("consistent"):
        if image_consistency.get("status") in {"error", "unavailable"}:
            notes.append(
                f"图片一致性检测不可用（status={image_consistency.get('status')}）："
                f"{'; '.join(image_consistency.get('samples') or [])}。这不是图片一致，需先修复/重跑 image_qc。"
            )
        else:
            notes.append(
                f"图片一致性存在硬阻断（image_qc verdict={image_consistency.get('verdict')}，"
                f"hard_blocks={image_consistency.get('hard_blocks')}）：见 `{image_consistency.get('report_md')}`，"
                "崩脸/服装/场景/接缝需重出受影响镜。"
            )
    if contract_inheritance and not contract_inheritance.get("inherited"):
        st = contract_inheritance.get("status")
        if st == "missing":
            notes.append(
                "出图→出视频视觉契约继承尚未校验：缺 "
                f"`{contract_inheritance.get('report_json')}`。先跑 "
                f"`python3 skills/n2d-video/scripts/inherit_contract.py <作品根> {ep}`，"
                "校验参考帧契约（色调/光位锚/轴线视线/角色状态演进/景别）+ 文字 prompt 是否从出图侧正确传到出视频侧、"
                "命名角色镜是否锁脸、出图绑定的场景/道具/特效资产是否丢失，再出视频。"
            )
        elif st == "error":
            notes.append(
                f"契约继承报告不可读（{contract_inheritance.get('error')}）；"
                "重跑 `inherit_contract.py` 再判，不能当作已继承。"
            )
        else:
            notes.append(
                f"出图→出视频契约继承存在 block（verdict={contract_inheritance.get('verdict')}，"
                f"字段漂移 {contract_inheritance.get('field_blocks')}·身份未锁 {contract_inheritance.get('identity_blocks')}·"
                f"资产丢失 {contract_inheritance.get('asset_blocks')}）：见 `{contract_inheritance.get('report_md')}`，"
                "先按出图侧原文修 `出视频/prompt/00_总览.md` 的视觉契约/补 01_clips.md 的身份锚点与物料绑定，再出视频。"
            )
    return {
        "kind": KIND_PLAN,
        "created_at": now_iso(),
        "root": root,
        "episode": ep,
        "current_stage": until_key,
        "rerun_from": rerun_from,
        "rerun_until": until_key,
        "rebuild_needed": rebuild_needed,
        "gate_refresh_needed": gate_refresh_needed,
        "gate_refresh_stages": gate_refresh_stages,
        "regen_mode": mode,
        "strict_image_refresh": strict_image_refresh,
        "shared_lock_reuse": shared_lock_reuse,
        "shared_lock_changed_files": shared_lock_changed,
        "needs_record": old is None,
        "relevant_skills": relevant_skills,
        "newly_relevant_skills": newly_relevant,
        "changed_skills": changed_skills,
        "changed_files": changed_files,
        "snapshot_changed_files": snapshot_changes,
        "current_todo": current_todo,
        "image_qc_environment": image_qc_context,
        "source_drift": source_drift,
        "three_frame_compliance": three_frame,
        "image_consistency": image_consistency,
        "contract_inheritance": contract_inheritance,
        "execution_steps": execution_steps,
        "commands": commands,
        "notes": notes,
    }


def record(root: str, episodes: Sequence[str]) -> Dict[str, Any]:
    header, rows = rows_by_episode(root)
    skills: Set[str] = set(ALWAYS_RELEVANT_SKILLS)
    old = load_snapshot(root)
    if old:
        skills.update(snapshot_skills(old))
    normalized: List[str] = []
    for ep in episodes:
        ep = normalize_episode(ep)
        if ep not in rows:
            raise SystemExit(f"未在 _进度.md 找到 {ep}")
        normalized.append(ep)
        until_key = current_stage_key(root, ep, header, rows[ep])
        skills.update(relevant_skills_for_stage(until_key))
    snap = build_baseline_snapshot(skills)
    snap["kind"] = KIND_SNAPSHOT
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
    p_check.add_argument(
        "--regen-mode",
        choices=[REGEN_MODE_MINIMAL, REGEN_MODE_STRICT_REFRESH, LEGACY_REGEN_MODE_KEEP_IMAGES],
        default=None,
        help="重制策略；缺省读 _设置.md『更新重制策略』，再读私有全局默认，再缺省=最小。严审刷新=刷新最新prompt后严审旧图，不符合即重出；保图刷新为旧别名",
    )

    p_record = sub.add_parser("record", help="record current relevant skill fingerprints as baseline")
    add_common(p_record)
    p_record.add_argument("--json", action="store_true", help="print JSON")

    p_media = sub.add_parser(
        "media",
        help="selective image/video refresh plan for a few shots (evidence-first, no audit)",
    )
    p_media.add_argument("root", help="制漫剧/<剧名> 作品根")
    p_media.add_argument("episode", nargs="?", help="第N集（必填，避免误扫全剧）")
    p_media.add_argument("--image", action="append", default=[], help="候选复核/可能刷新的图片目标，可逗号分隔；不是坏图判定")
    p_media.add_argument("--video", action="append", default=[], help="候选复核/可能刷新的视频目标，可逗号分隔；不是坏视频判定")
    p_media.add_argument("--target", action="append", default=[], help="同时作为图片和视频目标的通用 selector")
    p_media.add_argument("--write-plan", action="store_true", help="写入 生产数据/media_refresh_plan*.json/md 并追加 update runs 日志")
    p_media.add_argument("--json", action="store_true", help="输出 JSON")
    return parser.parse_args(argv)


def run_media(args: argparse.Namespace) -> int:
    here = os.path.abspath(SCRIPT_DIR)
    if here not in sys.path:
        sys.path.insert(0, here)
    import media_refresh  # noqa: E402  局部导入，避免 check/record 也加载

    plan = media_refresh.build_plan(
        args.root,
        episode=args.episode,
        image_targets=args.image,
        video_targets=args.video,
        generic_targets=args.target,
    )
    if args.write_plan:
        plan = media_refresh.write_plan(os.path.abspath(args.root), plan)
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        marker = "已生成候选计划（需证据确认）" if plan["needs_media_review"] else "无图片/视频 target"
        print(f"{plan['line']}: {marker} images={len(plan['targets']['images'])} videos={len(plan['targets']['videos'])}")
        if plan.get("plan_md"):
            print(f"  plan: {plan['plan_md']}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if args.cmd == "media":
        return run_media(args)
    root = os.path.abspath(args.root)
    episodes = all_episodes(root) if args.all else [args.episode]
    if not episodes or any(not ep for ep in episodes):
        raise SystemExit("请提供集号，或使用 --all")

    if args.cmd == "record":
        snap = record(root, [str(ep) for ep in episodes])
        if args.json:
            print(json.dumps(snap, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"已记录 skill 快照：{snapshot_path(root)}（{len(snap.get('files', {}))} files 内容基线）")
        return 0

    regen_mode = getattr(args, "regen_mode", None)
    plans = [build_plan(root, str(ep), regen_mode=regen_mode) for ep in episodes]

    # 注入智能优化建议（附加功能，失败不影响重制计划主流程）。
    # JSON 模式必须保持 stdout 为纯 JSON；人读打印只在非 JSON 模式走 stdout。
    smart_suggestions: List[Dict[str, Any]] = []
    smart_suggestions_error = ""
    try:
        from smart_suggestions import get_smart_suggestions, print_suggestions
        smart_suggestions = get_smart_suggestions(root)
    except Exception as e:
        smart_suggestions_error = f"{type(e).__name__}: {e}"
        print(f"智能建议生成失败（不影响重制计划）：{smart_suggestions_error}", file=sys.stderr)
        print_suggestions = None  # type: ignore[assignment]

    for plan in plans:
        plan["smart_suggestions"] = smart_suggestions
        if smart_suggestions_error:
            plan["smart_suggestions_error"] = smart_suggestions_error

    if args.write_plan:
        for plan in plans:
            write_plan(root, plan)
    if args.json:
        print(json.dumps(plans[0] if len(plans) == 1 else plans, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if smart_suggestions and print_suggestions:
            print_suggestions(smart_suggestions)
        for plan in plans:
            marker = (
                "建议重制" if plan["rebuild_needed"]
                else ("建议刷新gate" if plan.get("gate_refresh_needed") else "无需重制")
            )
            rerun_label = (
                ",".join(plan.get("gate_refresh_stages") or ["gate/review"])
                if plan.get("gate_refresh_needed") and not plan["rebuild_needed"]
                else (plan.get("rerun_from") or "gate/review")
            )
            print(
                f"{plan['episode']}: {marker} "
                f"current={plan['current_stage']} "
                f"rerun={rerun_label}→{plan['rerun_until']} "
                f"changed={len(plan['changed_files'])}"
            )
            if plan.get("plan_md"):
                print(f"  plan: {plan['plan_md']}")
            todo = plan.get("current_todo")
            if todo:
                print(
                    f"  todo: {todo.get('label')} "
                    f"{todo.get('column')}={todo.get('status')} "
                    f"→ {todo.get('skill')}"
                )
            sd, tf, ic = plan.get("source_drift"), plan.get("three_frame_compliance"), plan.get("image_consistency")
            ci = plan.get("contract_inheritance")
            health = []
            if sd:
                health.append(f"源={sd.get('status')}")
            if tf:
                health.append("三帧=豁免" if not tf.get("enforced")
                              else ("三帧=达标" if tf.get("compliant")
                                    else f"三帧=缺{len(tf.get('violating_clips') or [])}镜"))
            if ic:
                if ic.get("status") in {"error", "unavailable"}:
                    health.append(f"图片={ic.get('status')}")
                else:
                    health.append("图片=" + ("一致" if ic.get("consistent") else f"硬阻断{ic.get('hard_blocks')}"))
            if ci:
                if ci.get("status") in {"missing", "error"}:
                    health.append(f"契约={ci.get('status')}")
                else:
                    health.append("契约=" + ("已继承" if ci.get("inherited") else "block"))
            if health:
                print("  health: " + " | ".join(health))
            for note in plan.get("notes", []):
                print(f"  - {note}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
