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

from skill_snapshot import (  # noqa: E402
    changed_files_since,
    git_changed_files,
    is_test_path,
    now_iso,
    snapshot_for_skills,
)

KIND_SNAPSHOT = SKILL_UPDATE_SNAPSHOT_KIND
KIND_PLAN = SKILL_UPDATE_PLAN_KIND
SNAPSHOT_FILE = "skill_update_snapshot.json"
PLAN_PREFIX = "skill_update_plan"

ALWAYS_RELEVANT_SKILLS = {
    "common",
    "n2d",
    "n2d-dashboard",
    "n2d-review",
    "n2d-batch",
    "n2d-update",
}
OBSERVE_ONLY_SKILLS = {
    "common",
    "n2d",
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
}


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


def stage_key_for_changed_file(rel_path: str, until_key: str) -> Optional[str]:
    if gate_only_stage_for_changed_file(rel_path, until_key):
        return None
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


def plan_paths(root: str, ep: str) -> Tuple[str, str]:
    safe_ep = normalize_episode(ep)
    base = os.path.join(production_dir(root), f"{PLAN_PREFIX}_{safe_ep}")
    return base + ".json", base + ".md"


REGEN_MODE_MINIMAL = "最小"
REGEN_MODE_STRICT_REFRESH = "严审刷新"
LEGACY_REGEN_MODE_KEEP_IMAGES = "保图刷新"


def read_setting(root: str, key: str) -> Optional[str]:
    """从 `<作品根>/_设置.md` 读一行 `- <key>：<值>` / `- <key>: <值>`。缺文件/缺键 → None。纯解析。"""
    path = os.path.join(root, "_设置.md")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except Exception:
        return None
    import re as _re
    m = _re.search(rf"^[\-\*\s]*{_re.escape(key)}\s*[:：]\s*(.+?)\s*$", text, _re.MULTILINE)
    return m.group(1).strip() if m else None


def resolve_regen_mode(root: str, cli_mode: Optional[str]) -> str:
    """更新重制策略选择点：CLI 显式 > `_设置.md 更新重制策略` > 默认 最小（保守，不打扰现有流程）。"""
    if cli_mode:
        return REGEN_MODE_STRICT_REFRESH if cli_mode == LEGACY_REGEN_MODE_KEEP_IMAGES else cli_mode
    setting = read_setting(root, "更新重制策略")
    if setting == LEGACY_REGEN_MODE_KEEP_IMAGES:
        return REGEN_MODE_STRICT_REFRESH
    if setting in (REGEN_MODE_MINIMAL, REGEN_MODE_STRICT_REFRESH):
        return setting
    return REGEN_MODE_MINIMAL


def commands_for_strict_image_refresh(root: str, ep: str, start_key: Optional[str], until_key: str) -> List[str]:
    """「严审刷新」命令序列：按最新 skill 刷新文字阶段/prompt → 对旧图按最新 prompt/QC 标准严审
    → 只把不符合最新标准的镜排进重出。旧图不是默认受保护对象。"""
    epn = ep.replace("第", "").replace("集", "")
    # 文字阶段刷新起点：取改动起点，但不晚于出图 prompt；先让最新 prompt 成为审旧图的标准。
    text_start = start_key if (start_key and stage_index(start_key) < stage_index("image")) else "image_prompt"
    qc = f'python3 skills/n2d-image/scripts/image_qc.py "{root}" {ep}'
    return [
        # 1) 按最新 skill 刷新分镜/出图 prompt，生成新的审查标准。
        (f'python3 skills/n2d-batch/scripts/queue.py plan "{root}" --episodes {epn} '
         f'--rerun-from {text_start} --scope "严审刷新·按最新skill刷新文字阶段与出图prompt" '
         '--max-concurrency 1 --max-retries 1'),
        # 2) 用最新 prompt/QC/review 标准严审现有图片：block/warn/降级都先列入候选重出。
        f'{qc} --regen-list --strict',
        # 3) 只把严审命中的镜排进重生成；为空表示最新证据未发现需要舍弃的旧图。
        (f'shots=$({qc} --affected-shots --strict); [ -n "$shots" ] && '
         f'python3 skills/n2d-batch/scripts/queue.py plan "{root}" --episodes {epn} '
         f'--rerun-from image $shots --scope "严审刷新·重出不符合最新prompt/QC标准的镜" '
         '--max-concurrency 1 --max-retries 1 || echo "严审未发现需舍弃旧图的镜"'),
        # 4) 重出的镜回验像素一致性（dashboard gate --stage image 已含 image_qc）
        image_qc_verify_command(root, ep),
    ]


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
    cmds: List[str] = []
    for stage_key in stage_keys:
        gate_stage = (stage_for_key(stage_key) or {}).get("gate_stage")
        if gate_stage:
            cmds.append(
                f"python3 skills/n2d-dashboard/scripts/dashboard.py gate \"{root}\" {ep} --stage {gate_stage}"
            )
    return cmds


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
    except Exception:
        return None
    env = data.get("qc_environment") or {}
    summary = data.get("summary") or {}
    if not isinstance(env, dict) or not env:
        return None
    return {
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
    }


def command_for_rerun(root: str, ep: str, start_key: Optional[str], until_key: str) -> List[str]:
    if not start_key:
        gate_stage = (stage_for_key(until_key) or {}).get("gate_stage")
        if not gate_stage:
            return [f"python3 skills/n2d-update/scripts/update_plan.py record \"{root}\" {ep}"]
        return [
            f"python3 skills/n2d-dashboard/scripts/dashboard.py gate \"{root}\" {ep} --stage {gate_stage}",
        ]
    start = stage_for_key(start_key) or {}
    cmds = [
        (
            "python3 skills/n2d-batch/scripts/queue.py plan "
            f"\"{root}\" --episodes {ep.replace('第', '').replace('集', '')} "
            f"--rerun-from {start_key} --scope \"skill 更新后重制到 {until_key}\" "
            "--max-concurrency 1 --max-retries 1"
        ),
        str(start.get("command", "")).format(root=root, ep=ep),
    ]
    # A：重制范围覆盖出图 → 追加出图落档机检验证步（避免"重出图后没人验像素"）
    if rerun_covers_image(start_key, until_key):
        cmds.append(image_qc_verify_command(root, ep))
    return cmds


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
        lines.extend([
            "",
            "## 图片质检环境与阶段跳转",
            f"- 机检能力：`{qc.get('precision_level')}`",
            f"- 当前解释器：`{qc.get('python')}`",
            f"- 当前 image_qc：`verdict={qc.get('verdict')}`，硬阻断 `{qc.get('hard_blocks')}`，非阻断初筛 `{qc.get('advisory')}`，降级 `{qc.get('degraded')}`",
            f"- 当前应停在/回退：`{qc.get('jump_to_stage')}` — {qc.get('jump_reason')}",
            f"- 建议安装：{qc.get('recommended_install') or '无需补装'}",
            f"- 报告：`{qc.get('report_md') or qc.get('report_json')}`",
        ])
    if plan.get("commands"):
        lines.extend(["", "## 建议命令"])
        lines.extend(f"```bash\n{cmd}\n```" for cmd in plan["commands"])
    if plan.get("notes"):
        lines.extend(["", "## 备注"])
        lines.extend(f"- {note}" for note in plan["notes"])
    lines.append("")
    return "\n".join(lines)


def build_plan(root: str, ep: str, *, include_git: bool = True,
               regen_mode: Optional[str] = None) -> Dict[str, Any]:
    root = os.path.abspath(root)
    ep = normalize_episode(ep)
    header, rows = rows_by_episode(root)
    if ep not in rows:
        raise SystemExit(f"未在 _进度.md 找到 {ep}")
    row = rows[ep]
    until_key = current_stage_key(root, ep, header, row)
    current_todo = current_todo_context(root, ep, header, row)
    relevant_skills = relevant_skills_for_stage(until_key)
    old = load_snapshot(root)
    new = snapshot_for_skills(REPO_ROOT, REPO_SKILLS, relevant_skills)
    old_skills = snapshot_skills(old) if old else set()
    newly_relevant = sorted(set(relevant_skills) - old_skills) if old else []
    snapshot_changes = scoped_changed_files(old, new, old_skills & set(relevant_skills))
    changed = set(snapshot_changes)
    if include_git and old is None:
        relevant_prefixes = tuple(f"skills/{s}/" for s in relevant_skills)
        changed.update(
            p for p in git_changed_files(REPO_ROOT)
            if p.startswith(relevant_prefixes) and not is_test_path(p)
        )
    elif include_git and newly_relevant:
        newly_relevant_prefixes = tuple(f"skills/{s}/" for s in newly_relevant)
        changed.update(
            p for p in git_changed_files(REPO_ROOT)
            if p.startswith(newly_relevant_prefixes) and not is_test_path(p)
        )
    changed_files = sorted(changed)
    changed_skills = sorted({skill_name_for_path(os.path.join(REPO_ROOT, p)) or "" for p in changed_files} - {""})
    gate_refresh_stages = gate_refresh_stage_keys(changed_files, until_key)
    artifact_changed_files = [
        p for p in changed_files
        if not observe_only_changed_file(p) and not gate_only_stage_for_changed_file(p, until_key)
    ]
    rerun_from = earliest_rerun_stage(artifact_changed_files, until_key)
    rebuild_needed = bool(artifact_changed_files)
    gate_refresh_needed = bool(gate_refresh_stages)
    notes: List[str] = []
    if not old:
        notes.append("当前作品没有 skill_update_snapshot 基线；本次结果会结合 git 工作区变动提示，建议先 record 建立基线。")
    if newly_relevant:
        notes.append(
            f"{', '.join(newly_relevant)} 因阶段推进首次纳入相关范围，本次不计为变更；该阶段完成后请 record 刷新基线。"
        )
    if changed_files and not artifact_changed_files and gate_refresh_needed:
        notes.append("变动只影响 QC/gate 报告，不重制 prompt/图片/视频；重跑对应 gate 刷新结论即可。")
    elif changed_files and not artifact_changed_files:
        notes.append("变动集中在 common/review/dashboard/batch/n2d-update 等横切层，不默认重制生产产物；先重跑 gate/审查/计划。")
    elif rebuild_needed and not rerun_from:
        notes.append("变动集中在 common/review/dashboard/batch/n2d 等横切层，或只涉及该集尚未到达的阶段文件；先重跑 gate/审查/计划，不默认重抽图。")
    if rebuild_needed and rerun_from:
        notes.append("真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。")

    mode = resolve_regen_mode(root, regen_mode)
    strict_image_refresh = (mode == REGEN_MODE_STRICT_REFRESH and rebuild_needed
                            and rerun_covers_image(rerun_from, until_key))
    if strict_image_refresh:
        commands = commands_for_strict_image_refresh(root, ep, rerun_from, until_key)
        notes.append(
            "【严审刷新】本模式不是保旧图：先按最新 skill 刷新文字阶段与出图 prompt，"
            "再用最新 prompt/QC/review 标准严审现有图片；凡 block/warn/降级或人工判定不符合预期的镜，"
            "都应舍弃旧图并排入重出。只有已有 finding/人工判定明确可沿用的镜，才允许保留。"
        )
    elif rebuild_needed:
        commands = command_for_rerun(root, ep, rerun_from, until_key)
    elif gate_refresh_needed:
        commands = gate_refresh_commands(root, ep, gate_refresh_stages)
    else:
        commands = []
    image_qc_context = (
        load_image_qc_context(root, ep)
        if stage_index(until_key) >= stage_index("image")
        else None
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
        "needs_record": old is None,
        "relevant_skills": relevant_skills,
        "newly_relevant_skills": newly_relevant,
        "changed_skills": changed_skills,
        "changed_files": changed_files,
        "snapshot_changed_files": snapshot_changes,
        "current_todo": current_todo,
        "image_qc_environment": image_qc_context,
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
    snap = snapshot_for_skills(REPO_ROOT, REPO_SKILLS, skills)
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
    p_check.add_argument("--no-git", action="store_true", help="ignore git working-tree changes")
    p_check.add_argument(
        "--regen-mode",
        choices=[REGEN_MODE_MINIMAL, REGEN_MODE_STRICT_REFRESH, LEGACY_REGEN_MODE_KEEP_IMAGES],
        default=None,
        help="重制策略；缺省读 _设置.md『更新重制策略』，再缺省=最小。严审刷新=刷新最新prompt后严审旧图，不符合即重出；保图刷新为旧别名",
    )

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

    regen_mode = getattr(args, "regen_mode", None)
    plans = [build_plan(root, str(ep), include_git=not args.no_git, regen_mode=regen_mode) for ep in episodes]
    if args.write_plan:
        for plan in plans:
            write_plan(root, plan)
    if args.json:
        print(json.dumps(plans[0] if len(plans) == 1 else plans, ensure_ascii=False, indent=2, sort_keys=True))
    else:
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
            for note in plan.get("notes", []):
                print(f"  - {note}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
