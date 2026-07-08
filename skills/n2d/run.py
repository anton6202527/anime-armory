#!/usr/bin/env python3
"""n2d 编排器 —— 把"找前沿 → 跑确定性前置 → 停在第一个决策/花钱/合规点"收敛成一个入口。

设计契约见 docs/n2d-编排器设计.md（评审 v0.1）。核心约束：stage skill 混着"确定性脚本"
与"代理创作/花钱生成"，所以本编排器不把 stage 当 subprocess 一把梭跑完——它只**自动跑掉
确定性前置**（gate / model-router / doctor / compliance / 身份矩阵刷新），跑到第一个
「需要脑子 / 需要钱包 / 需要签字」的点就停，交回一张结构化「下一步动作卡」NextAction。

用法：
    python3 run.py next <作品根> [第N集] [--json] [--auto] [--preview]

铁规对齐：VCS-free（只读文件/内容快照，不调 git）；契约单一真值（阶段图/列名/gate stage
一律读 STAGE_GRAPH/stage_of/gate.py，不复制）；选择点经设置适配层、不 branch 菜单文字；
只读/只跑确定性前置，绝不自行花钱、自行执行创作、自行换后端。
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

_LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from n2d_contract import stage_for_key, stage_for_progress_column  # 契约真值（facade）
from n2d_logic import normalize_production_mode
from n2d_route import compose_stage_enabled, normalize_episode, parse_progress, stage_of, summarize
from n2d_visual_styles import STYLE_INTAKE_OPTIONS, STYLE_OPTIONS
from n2d_action_registry import (
    context_pack_relpath,
    creative_loop_relpath,
    specialist_for_stage,
    stage_action_spec,
)
from n2d_trace import new_trace_context

try:
    from settings import get_setting, get_setting_spec, load_settings, project_setting_source
except ImportError:  # pragma: no cover - 包式导入兜底
    from n2d_settings import get_setting, get_setting_spec, load_settings, project_setting_source

try:
    from n2d_platform_profiles import video_backend_capability_confidence
    from video_backend_adapter import refresh_evidence_status
except Exception:  # pragma: no cover - keep dispatcher usable if adapter import is damaged
    video_backend_capability_confidence = None
    refresh_evidence_status = None

# prework 提速层（输入指纹缓存 + 顺序保持并行）。缺模块/异常时整体降级回串行，绝不让编排器崩。
try:
    from prework_cache import (
        PreworkCache as _PreworkCache,
        episode_input_fingerprint as _episode_input_fingerprint,
        run_cached_parallel as _run_cached_parallel,
    )
except Exception:  # pragma: no cover - degrade to serial if cache module unavailable
    _PreworkCache = None
    _episode_input_fingerprint = None
    _run_cached_parallel = None

SKILLS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _prework_run(steps, run_one, *, cache=None, should_cache=None):
    """Facade over prework_cache.run_cached_parallel; ordered-serial fallback if unavailable.

    Returns outcomes in the SAME order as `steps`, so callers can apply order-sensitive
    state (e.g. first-block-wins prework_block) identically to the old serial loops.
    """
    if _run_cached_parallel is not None:
        return _run_cached_parallel(steps, run_one, cache=cache, should_cache=should_cache)
    return [run_one(obj) for _key, obj in steps]


def _make_prework_cache(root, ep, stage_key, script_paths):
    """Build a per-(root,ep,stage) prework cache keyed on episode inputs + audit-script mtimes.
    Returns None (cache off, run fresh) when the module is unavailable or fingerprinting fails."""
    if _PreworkCache is None or _episode_input_fingerprint is None or not ep:
        return None
    try:
        fp = _episode_input_fingerprint(root, ep, list(script_paths))
        return _PreworkCache(root, ep, stage_key, fp)
    except Exception:  # pragma: no cover - never let caching break the orchestrator
        return None


def _identity_matrix_path(root: str) -> str:
    return os.path.join(root, "生产数据", "identity_adapter_matrix.json")


def _identity_exit_is_planned_asset_gap(root: str) -> tuple[bool, str]:
    """Return true when identity.py only reports missing shared makeup assets.

    `image_prompt` is the stage that creates the shared makeup prompt plan, so
    missing reference PNGs are expected there. Later image/video stages must keep
    treating the same gaps as blockers.
    """
    path = _identity_matrix_path(root)
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        return False, ""
    forms = data.get("forms")
    if not isinstance(forms, list) or not forms:
        return False, ""
    allowed_exact = {
        "reference_group_assets_missing",
        "lora:unknown_status:candidate",
    }
    gap_count = 0
    for form in forms:
        if not isinstance(form, dict):
            return False, ""
        gaps = form.get("gaps") or []
        if not isinstance(gaps, list):
            return False, ""
        for gap in gaps:
            g = str(gap or "").strip()
            if not g:
                continue
            gap_count += 1
            if g in allowed_exact or g.startswith("missing_reference:"):
                continue
            if g.startswith(("image.", "video.")) and g.endswith(":reference_group_assets_missing"):
                continue
            return False, ""
    return True, f"{len(forms)} forms have {gap_count} planned shared-reference gaps"

# ── 阶段分类（key 来自 STAGE_GRAPH，不另立并行表，只贴标签）──────────────────
AGENT_GEN_STAGES = {"script_stage1", "script_stage2", "image_prompt", "video_prompt"}
GENERATION_STAGES = {"voice", "image", "video", "compose"}
PAID_STAGES = {"image", "video", "compose"}          # 进这些前必过合规闸门
ENTRY_GATED_STAGES = AGENT_GEN_STAGES | GENERATION_STAGES | {"review"}
ROUTER_STAGES = {"video_prompt", "video"}            # 出视频前置：先写模型路由表
IDENTITY_REFRESH_STAGES = {"image_prompt", "image", "video_prompt", "video", "compose", "review"}
IMAGE_QC_STRICT_STAGES = {"video_prompt", "video", "compose", "review"}
SCRIPT_TEXT_AUDIT_STAGES = {"image_prompt"}
FIRST_RUN_CHOICES = ("制作模式", "基础视觉风格")
REFERENCE_MEDIA_STYLE_OPTION = STYLE_INTAKE_OPTIONS[0]
EXPLICIT_SETTING_SOURCES = {"explicit_user", "cli", "manual", "user"}
# 各生成阶段"放行前必问"的选择点（菜单随动作卡一起给，不另起一次 needs_choice）
STAGE_MENU = {
    "voice": ("配音后端", False),    # (选择点, 是否每次必问)
    "image": ("生成粒度", True),
    "video": ("生成粒度", True),
    "compose": ("BGM来源", True),
}


def _is_video_first_rough_voice(root: str, route: Dict[str, Any], stage_key: str) -> bool:
    """视频先行模式下，进度表「配音」列先产占位/估算时长，不是最终真实配音。"""
    if stage_key != "voice" or route.get("col") != "配音":
        return False
    mode = normalize_production_mode(get_setting(root, "制作模式", "先出视频后配音"))
    return mode == "先出视频后配音"


# ── 探针结果（decide() 的纯输入，便于测试注入）────────────────────────────────
@dataclass
class Probes:
    env_missing: Optional[str] = None            # 该阶段所需后端缺失名；None=可跑
    entry_check_block: Optional[str] = None      # 源文本/skill 更新影响明确阻断
    capability_block: Optional[str] = None       # 模型/平台能力证据不足或已废弃
    prework_block: Optional[str] = None          # 必跑确定性前置失败；不能继续生成/花钱
    image_qc_block: Optional[str] = None         # 出图落档 QC 未过；不同于环境缺失
    review_acceptance_block: Optional[str] = None  # 最终验收证据未过
    gate: Optional[Dict[str, Any]] = None        # {stage,blocked,return_to_stage,affected_artifacts,rerun_scope,findings_path}
    compliance_gap: Optional[bool] = None        # True=有缺口；None=未检/检不了
    pending_choices: List[str] = field(default_factory=list)  # 首跑必给但尚未显式记录的选择点
    entry_checks: List[Dict[str, Any]] = field(default_factory=list)
    prework: List[Dict[str, Any]] = field(default_factory=list)  # 本轮自动跑掉的确定性步骤记录
    prework_blocks: List[Dict[str, str]] = field(default_factory=list)  # 同轮收集到的全部前置硬阻断


def _record_prework_block(p: Probes, step: str, message: str) -> None:
    message = str(message or "").strip()
    if not message:
        return
    if not p.prework_block:
        p.prework_block = message
    if not any(row.get("step") == step and row.get("message") == message for row in p.prework_blocks):
        p.prework_blocks.append({"step": step, "message": message})


def _prework_block_items(probes: Probes) -> List[Dict[str, str]]:
    if probes.prework_blocks:
        return [dict(row) for row in probes.prework_blocks]
    if probes.prework_block:
        return [{"step": "prework", "message": probes.prework_block}]
    return []


def _prework_status_summary(prework: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {"block": 0, "warn": 0, "pass": 0, "skip": 0}
    steps: List[Dict[str, str]] = []
    for row in prework:
        step = str(row.get("step") or "")
        status = str(row.get("status") or "unknown").lower()
        counts[status] = counts.get(status, 0) + 1
        if step:
            steps.append({"step": step, "status": status})
    return {"counts": counts, "steps": steps}


# ── 前沿解析（复用 stage_of/summarize，不重算路由）────────────────────────────
def resolve_frontier(root: str, ep: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """返回 stage_of 的 route dict（{ep,col,label,skill,cmd,note}），已完成/找不到返回 None。"""
    header, rows = parse_progress(root)
    if ep:
        ep = normalize_episode(ep)
        row = next((r for r in rows if r["_ep"] == ep), None)
        if row is None:
            return None
        route = stage_of(root, row, header)
    else:
        route = summarize(root)["first"]
    if not route or not route.get("col"):
        return None
    return route


def stage_key_of(route: Dict[str, Any]) -> Optional[str]:
    """从 route 反查 STAGE_GRAPH 的 stage key。

    特例：先出视频后配音模式下，compose 前沿会被重定向成 label='补真实配音'、skill='n2d-voice'
    （col 仍是 '成片'）——这里按 voice 处理，否则 stage_for_progress_column('成片') 会误判成 compose。
    """
    if route.get("label") == "补真实配音" or (route.get("skill") == "n2d-voice" and route.get("col") == "成片"):
        return "voice"
    spec = stage_for_progress_column(route["col"])
    return spec["key"] if spec else None


def _missing_progress_action(root: str, ep: Optional[str] = None) -> Dict[str, Any]:
    target = normalize_episode(ep) if ep else "第1集"
    return {
        "frontier": None,
        "prework": [],
        "stop_reason": "blocked_by_entry_check",
        "action_card": {
            "headline": "作品缺少 _进度.md，需先初始化或恢复进度表",
            "to_user": (
                f"作品根已存在，但没有 `_进度.md`，编排器无法判断 {target} 的生产前沿。"
                "先确认源小说并用 n2d-script 粗切/恢复项目骨架，再重新进入 `run.py next`。"
            ),
            "block_reason": "missing_progress",
            "recovery_command": f"python3 skills/n2d-script/scripts/split_novel.py <小说路径> --out '{root}' --limit 10",
        },
        "gate": None,
        "auto_continue": False,
    }


# ── 纯决策（全部测试覆盖；不做任何 I/O）──────────────────────────────────────
def decide(root: str, route: Dict[str, Any], stage_key: str, probes: Probes) -> Dict[str, Any]:
    spec = stage_for_key(stage_key) or {}
    frontier = {
        "ep": route.get("ep"),
        "stage_key": stage_key,
        "label": route.get("label") or spec.get("label"),
        "owner": route.get("skill") or spec.get("owner"),
    }

    def na(stop_reason: str, card: Dict[str, Any]) -> Dict[str, Any]:
        trace = new_trace_context(root, ep, stage_key, action=stop_reason)
        action_contract = stage_action_spec(stage_key)
        if stage_key == "voice" and stop_reason == "needs_stage_execution":
            action_contract["stop_policy"] = stop_reason
            action_contract["requires_human_approval"] = False
            action_contract["paid_or_irreversible"] = False
        card = dict(card)
        if "block_reason" not in card:
            block_reason = _default_block_reason(stop_reason, card, probes.gate)
            if block_reason:
                card["block_reason"] = block_reason
        if probes.prework:
            card.setdefault("prework_status_summary", _prework_status_summary(probes.prework))
        card.setdefault("context_pack", _context_pack_card(root, ep, stage_key))
        if action_contract.get("requires_creative_loop"):
            card.setdefault("creative_loop", _creative_loop_card(root, ep, stage_key))
        card.setdefault("specialist", specialist_for_stage(stage_key))
        return {
            "frontier": frontier,
            "entry_checks": probes.entry_checks,
            "prework": probes.prework,
            "stop_reason": stop_reason,
            "action_card": card,
            "gate": probes.gate,
            "trace": trace,
            "action_contract": action_contract,
            "auto_continue": stop_reason == "auto_ran",
        }

    ep = frontier["ep"]
    cmd_template = route.get("cmd") or spec.get("command") or ""
    cmd = cmd_template.format(root=root, ep=ep)

    # 1. env 缺失 —— 不让代理跑到花钱工位才发现
    if probes.env_missing:
        return na("env_missing", {
            "headline": f"{ep} {frontier['label']}：所需后端不可用（{probes.env_missing}）",
            "to_user": f"该阶段后端 {probes.env_missing} 探测不可用。先修复/换后端，或选占位路线后再放行。",
            "exact_command": cmd,
        })

    # 1.1 源文本/skill 更新影响：明确漂移或需重制时，不能继续写/花钱/签收。
    if probes.entry_check_block:
        return na("blocked_by_entry_check", {
            "headline": f"{ep} {frontier['label']}：入口检查未放行",
            "to_user": probes.entry_check_block,
            "exact_command": cmd,
        })

    # 1.15 模型/平台能力证据：候选日期新鲜不等于当前后端可付费执行。
    if probes.capability_block:
        return na("capability_evidence_required", {
            "headline": f"{ep} {frontier['label']}：模型/平台能力证据不足",
            "to_user": probes.capability_block,
            "exact_command": cmd,
        })

    # 1.2 必跑前置失败 —— router/identity/gate/compliance 跑不通不等于通过
    if probes.prework_block:
        block_items = _prework_block_items(probes)
        extra = ""
        if len(block_items) > 1:
            extra = " 同轮还检测到：" + "；".join(f"{b.get('step')}: {b.get('message')}" for b in block_items[1:4])
        return na("prework_failed", {
            "headline": f"{ep} {frontier['label']}：确定性前置失败",
            "to_user": f"{probes.prework_block}{extra} 修复该前置脚本/产物后再继续；不能把 warn/skip 当放行。",
            "exact_command": cmd,
            "prework_blocks": block_items,
        })

    # 1.5 出图落档 QC 硬阻断 —— 已知图问题不能带进视频/合成
    if probes.image_qc_block:
        return na("blocked_by_image_qc", {
            "headline": f"{ep} {frontier['label']}：image_qc 未放行",
            "to_user": f"{probes.image_qc_block} 先回 n2d-image 修复/确认受影响图，再重跑 image_qc。",
            "exact_command": f"python3 skills/n2d-image/scripts/image_qc.py {root} {ep} --prop-shape-report",
        })

    # 2. gate 阻断 —— 透传 gate.py 结构化字段，指向最小返工
    if probes.gate and probes.gate.get("blocked"):
        g = probes.gate
        return na("blocked_by_gate", {
            "headline": f"{ep} {frontier['label']}：gate「{g.get('stage')}」阻断",
            "to_user": f"先按 return_to_stage={g.get('return_to_stage')} 补齐再来；细节见 {g.get('findings_path')}。",
            "exact_command": cmd,
        })

    # 2.5 最终验收证据未过：score/ledger/review-ui 是交付面，不再只是建议收尾。
    if probes.review_acceptance_block:
        return na("blocked_by_review_acceptance", {
            "headline": f"{ep} 审查验收：交付证据未通过",
            "to_user": probes.review_acceptance_block,
            "exact_command": cmd,
            "post_qc_bundle": _post_qc_bundle(root, ep, "review_acceptance"),
        })

    # 3. 合规缺口（仅花钱档）
    if stage_key in PAID_STAGES and probes.compliance_gap:
        return na("needs_compliance", {
            "headline": f"{ep} {frontier['label']}：合规缺口未补齐（花钱前阻断）",
            "to_user": "跑 n2d-compliance --check 补齐 evidence/profile 后再进付费 gate。绝不放行。",
            "exact_command": f"python3 skills/n2d-compliance/scripts/compliance.py {root} {ep} --check",
        })

    # 4. 首跑必给但尚未显式选过的选择点（制作模式/基础视觉风格）
    if probes.pending_choices:
        return na("needs_choice", {
            "headline": f"{ep} 开局必给选择包（之后沉默沿用，随时可改）",
            "to_user": (
                "新作品首跑必须显式选一次以下选项，再继续："
                + "、".join(probes.pending_choices)
                + "。生视频后端选择已后移到 n2d-video；开局只记录用户主动指定的固定后端/账号硬约束。"
            ),
            "menu": [_menu(root, cp) for cp in probes.pending_choices],
            "exact_command": cmd,
        })

    # 5. 代理创作（LLM 写剧本/分镜/出图文案）——脚手架已就绪，停下交回代理
    if stage_key in AGENT_GEN_STAGES:
        return na("needs_agent_gen", {
            "headline": f"{ep} {frontier['label']}：脚手架就绪，待代理生成",
            "to_user": f"读 {frontier['owner']} 的 prompt 包 → 调 LLM 生成 → 注入项目；完成后回写进度再 run next。",
            "exact_command": cmd,
            "writeback_after": _writeback_hint(root, ep, spec),
        })

    # 5.5 视频先行模式的「配音」列只做占位/估算时长，真实配音留到成片前补。
    if _is_video_first_rough_voice(root, route, stage_key):
        return na("needs_stage_execution", {
            "headline": f"{ep} {frontier['label']}（视频先行：先产占位/估算时长）",
            "to_user": (
                "本作品制作模式=先出视频后配音；当前只生成 rough timing 脚手架，"
                "不触发真实音色克隆或付费配音。真实角色配音留到视频完成后、合成前再确认。"
            ),
            "exact_command": cmd,
            "writeback_after": f"python3 skills/n2d/progress.py set {root} {ep} 配音 ⏳rough",
            "expected_writeback": "配音=⏳rough",
            "recommended_backend": "say占位/估算时长",
        })

    # 6. 花钱/重活生成 —— 停下，附该阶段"放行前必问"菜单
    if stage_key in GENERATION_STAGES:
        cp, _every = STAGE_MENU.get(stage_key, (None, False))
        card = {
            "headline": f"{ep} {frontier['label']}（花钱·不可逆，需你放行）",
            "to_user": f"确认后再生成；{frontier['label']}是最贵环节之一，放行 ≠ 安全。",
            "exact_command": cmd,
            "writeback_after": _writeback_hint(root, ep, spec),
        }
        if stage_key == "compose":
            card["post_qc_bundle"] = _post_qc_bundle(root, ep, "pre_compose_review")
            card["to_user"] = (
                f"确认后再合成；合成前建议先跑审查包，确认视频、接缝、身份和字幕没有把问题带进终片。"
            )
        if cp:
            card["menu"] = [_menu(root, cp)]
        return na("needs_payment_confirm", card)

    if stage_key == "review":
        return na("needs_acceptance_signoff", {
            "headline": f"{ep} 审查验收证据已生成，待显式签收",
            "to_user": "progress DAG、P-3 check、score、ledger、review-ui、failure taxonomy 与 release verdict 已生成且未 blocked；人工确认交付面后再把「验收」列回写为 ✅。",
            "exact_command": _writeback_hint(root, ep, spec),
            "post_qc_bundle": _post_qc_bundle(root, ep, "review_acceptance"),
        })

    # 7. 纯确定性（当前无此类路由阶段，留给将来）
    return na("auto_ran", {"headline": f"{ep} {frontier['label']}：确定性步骤已自动完成"})


def _menu(root: str, choice_point: str) -> Dict[str, Any]:
    """选择点菜单：选项来自 SettingSpec（适配层真值），预选=设置里上次值或默认首项；不 branch 菜单文字。"""
    spec = None
    try:
        spec = get_setting_spec(choice_point, "n2d")
    except Exception:
        pass
    options = list(getattr(spec, "allowed", ()) or getattr(spec, "choices", ()) or [])
    if choice_point == "基础视觉风格":
        options = list(STYLE_OPTIONS)
    transient_options: List[str] = []
    if choice_point == "基础视觉风格" and REFERENCE_MEDIA_STYLE_OPTION not in options:
        if "自定义" in options:
            options.insert(options.index("自定义"), REFERENCE_MEDIA_STYLE_OPTION)
        else:
            options.append(REFERENCE_MEDIA_STYLE_OPTION)
        transient_options.append(REFERENCE_MEDIA_STYLE_OPTION)
    preselect = get_setting(root, choice_point, None) or (options[0] if options else None)
    menu = {
        "choice_point": choice_point,
        "options": options,
        "default_preselect": preselect,
    }
    if transient_options:
        menu["transient_options"] = transient_options
        menu["follow_up"] = (
            "选择参考图片/视频自动识别时，先让用户上传参考图或视频；"
            "抽帧/看片提炼后，再把基础视觉风格落成已有预设或自定义 style_contract，"
            "不要把该临时入口本身写入 _设置.md。"
        )
    return menu


def _writeback_hint(root: str, ep: str, spec: Dict[str, Any]) -> str:
    cols = list(spec.get("progress_columns", ()))
    col = cols[0] if cols else "<列名>"
    try:
        header, _rows = parse_progress(root)
    except Exception:
        header = []
    if col != "<列名>" and col not in header:
        return (
            f"python3 skills/n2d/progress.py ensure-col {root} {col} ⬜\n"
            f"python3 skills/n2d/progress.py set {root} {ep} {col} <值>"
        )
    return f"python3 skills/n2d/progress.py set {root} {ep} {col} <值>"


def _post_qc_bundle(root: str, ep: str, scope: str = "post_compose") -> Dict[str, Any]:
    """Post-video/post-compose review command bundle shown in action cards."""
    commands = [
        f"python3 skills/n2d-review/scripts/spectacle_video_qc.py {root} {ep} --write --write-sidecars",
        f"python3 skills/n2d-review/scripts/motion_reference_library.py {root} {ep} --write",
        f"python3 skills/n2d-dashboard/scripts/dashboard.py gate {root} {ep} --stage review",
        f"python3 skills/n2d-score/scripts/score.py {root} {ep} --run-checks --threshold 85",
        f"python3 skills/n2d-review/scripts/consistency_ledger.py {root} {ep}",
        f"python3 skills/n2d-review-ui/scripts/review_ui.py {root} {ep} --write --export-findings --markdown",
        f"python3 skills/n2d-review-ui/scripts/episode_app.py {root} --episode {ep} --write --index",
        f"python3 skills/n2d-review-ui/scripts/board.py {root} --write --markdown",
    ]
    if scope in {"review_acceptance", "post_compose_review", "episode_closeout"}:
        commands.extend([
            f"python3 skills/n2d/progress.py audit-dag {root} --json",
            f"python3 skills/n2d-script/scripts/production_breakdown.py {root} {ep} check --json",
            f"python3 skills/n2d-compose/scripts/final_timeline_probe.py {root} {ep} --write --json",
            f"python3 skills/n2d/scripts/script_supervisor_log.py {root} {ep} check --write-missing --json",
            f"python3 skills/n2d/scripts/failure_taxonomy.py {root} {ep} --write",
            f"python3 skills/n2d/scripts/release_verdict.py {root} {ep} --write",
        ])
    return {
        "scope": scope,
        "headline": "合成/交付前审查包" if scope == "pre_compose_review" else "每集收尾验收包",
        "commands": commands,
    }


def _context_pack_card(root: str, ep: str, stage_key: str) -> Dict[str, Any]:
    rel = context_pack_relpath(ep, stage_key)
    return {
        "relpath": rel,
        "command": f"python3 skills/n2d/scripts/context_pack.py {root} {ep} {stage_key} --write --json",
        "rule": "先读 context pack，再按缺口打开完整 references，避免把整套 n2d 文档塞进上下文。",
    }


def _creative_loop_card(root: str, ep: str, stage_key: str) -> Dict[str, Any]:
    rel = creative_loop_relpath(ep, stage_key)
    return {
        "relpath": rel,
        "command": f"python3 skills/n2d/scripts/creative_loop.py {root} {ep} {stage_key} --write --json",
        "rule": "生成 → 评估 → 修订 → final gate；最多两轮，block 必须回最小阶段。",
    }


def _explicit_choice_missing(root: str, key: str) -> bool:
    """Sensitive first-run choices must be project-local and explicitly confirmed."""
    if key not in load_settings(root):
        return True
    return project_setting_source(root, key) not in EXPLICIT_SETTING_SOURCES


def _entry_check_block(checks: List[Dict[str, Any]], stage_key: str) -> Optional[str]:
    if stage_key not in ENTRY_GATED_STAGES:
        return None
    for chk in checks:
        step = str(chk.get("step") or "")
        status = str(chk.get("status") or "").strip().lower()
        detail = str(chk.get("detail") or "").strip()
        if step == "source_check" and status == "drift":
            return f"源文本已漂移：{detail or 'source_check 检测到 DRIFT=drift'}。先确认重切/接受现状并更新源指纹基线，再继续当前阶段。"
        if step == "update_plan":
            plan = chk.get("plan") if isinstance(chk.get("plan"), dict) else {}
            if plan.get("rebuild_needed"):
                return (
                    f"skill 更新影响当前集，需先执行/确认重制计划：{plan.get('plan_md') or detail or '见 skill_update_plan'}。"
                )
            source_drift = plan.get("source_drift") if isinstance(plan.get("source_drift"), dict) else {}
            if source_drift.get("status") == "drift":
                return f"update_plan 检测到源文本漂移：{detail or plan.get('plan_md') or ''}。先处理源更新影响。"
    return None


def _video_capability_block(root: str, stage_key: str) -> Optional[str]:
    if stage_key != "video" or video_backend_capability_confidence is None:
        return None
    backend = get_setting(root, "生视频模型", "") or get_setting(root, "生视频AI", "")
    channel = get_setting(root, "生视频渠道", "")
    info = video_backend_capability_confidence(backend, channel)
    confidence = str(info.get("confidence") or "").strip()
    if confidence in {"evidence", ""}:
        return None
    if confidence == "deprecated":
        return (
            f"当前生视频后端 {backend or channel} 已标记 deprecated/manual-only（execution={info.get('execution_backend')}），"
            "不得进入付费批量视频生成；请换可自动路由后端或手动补充迁移方案。"
        )
    if confidence == "manual_required":
        return (
            f"当前生视频后端 {backend or channel} 缺机器可执行能力档（confidence=manual_required），"
            "付费生成前必须换后端或补正式 adapter/profile。"
        )
    if confidence == "conservative":
        if refresh_evidence_status is None:
            return f"当前生视频后端 {backend or channel} 只有 conservative 能力档，且 per-run refresh evidence 检查不可用；先补能力证据。"
        status = refresh_evidence_status(root, backend, channel)
        if status.get("status") != "fresh":
            return (
                f"当前生视频后端 {backend or channel} 只有 conservative 能力档；付费出视频前需当天 per-run 能力证据。"
                f"状态={status.get('status')}，证据文件={status.get('path')}。"
            )
    return None


def _load_json_file(path: str) -> Optional[Dict[str, Any]]:
    try:
        data = json.load(open(path, encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _gate_findings_path(root: str, ep: str, stage: str) -> str:
    return os.path.join(root, "生产数据", f"gate_findings_{stage}_{normalize_episode(ep)}.json")


def _has_episode_image_rasters(root: str, ep: str) -> bool:
    base = os.path.join(root, "出图", normalize_episode(ep), "图片")
    if not os.path.isdir(base):
        return False
    for _dirpath, _dirnames, filenames in os.walk(base):
        for name in filenames:
            if name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                return True
    return False


def _gate_stage_for_frontier(root: str, ep: Optional[str], stage_key: str, spec: Dict[str, Any]) -> Optional[str]:
    gate_stage = spec.get("gate_stage")
    if stage_key == "image" and ep and not _has_episode_image_rasters(root, ep):
        return "image_preflight"
    return gate_stage


def _gate_from_existing_findings(root: str, ep: str, stage: str) -> Optional[Dict[str, Any]]:
    path = _gate_findings_path(root, ep, stage)
    data = _load_json_file(path)
    if not data:
        return None
    severity = data.get("summary", {}).get("severity", {}) if isinstance(data.get("summary"), dict) else {}
    blocked = int((severity or {}).get("block") or 0) > 0
    gate = {
        "stage": stage,
        "blocked": blocked,
        "findings_path": path,
        "return_to_stage": None,
        "affected_artifacts": [],
        "rerun_scope": None,
    }
    if blocked:
        _enrich_gate(gate, path)
    return gate


def _default_block_reason(stop_reason: str, card: Dict[str, Any], gate: Optional[Dict[str, Any]]) -> str:
    is_blocking = (
        stop_reason.startswith("blocked")
        or "failed" in stop_reason
        or stop_reason in {"env_missing", "capability_evidence_required", "needs_compliance"}
    )
    if not is_blocking:
        return ""
    reason = str(card.get("to_user") or card.get("headline") or stop_reason)
    if gate and gate.get("blocked"):
        details = [
            f"stage={gate.get('stage')}" if gate.get("stage") else "",
            f"return_to={gate.get('return_to_stage')}" if gate.get("return_to_stage") else "",
            str(gate.get("rerun_scope") or ""),
            f"findings={gate.get('findings_path')}" if gate.get("findings_path") else "",
        ]
        extra = "；".join(x for x in details if x)
        if extra and extra not in reason:
            reason = f"{reason}；{extra}"
    return reason


def _review_acceptance_issue(root: str, ep: str) -> Optional[str]:
    prod = os.path.join(root, "生产数据")
    score_path = os.path.join(prod, f"score_{ep}.json")
    score = _load_json_file(score_path)
    if not score:
        return f"缺机器评分：{score_path}。先跑 score.py --run-checks --threshold 85。"
    if str(score.get("status") or "").lower() != "pass":
        return f"机器评分未通过（status={score.get('status')} score={score.get('total_score')}）：{score_path}。先按 auto_return_tasks/data_collection_tasks 处理。"

    ledger_path = os.path.join(prod, f"consistency_ledger_{ep}.json")
    ledger = _load_json_file(ledger_path)
    if not ledger:
        return f"缺验收总账：{ledger_path}。先跑 consistency_ledger.py 生成唯一交付面。"
    surface = ledger.get("delivery_surface") if isinstance(ledger.get("delivery_surface"), dict) else {}
    counts = ledger.get("counts") if isinstance(ledger.get("counts"), dict) else {}
    block = int(counts.get("block") or 0)
    high = int(counts.get("high") or 0)
    if surface.get("status") == "blocked" or block or high:
        return f"验收总账仍有高风险项（status={surface.get('status')}, block={block}, high={high}）：{ledger_path}。先回流修复或写结构化人工签收。"

    review_json = os.path.join(prod, f"review_ui_{ep}.json")
    review_html = os.path.join(prod, f"review_ui_{ep}.html")
    findings = os.path.join(prod, f"review_ui_findings_{ep}.json")
    missing = [p for p in (review_json, review_html, findings) if not os.path.isfile(p)]
    if missing:
        return "缺人审画布/导出 findings：" + "、".join(missing)
    verdict_path = os.path.join(prod, f"release_verdict_{ep}.json")
    verdict = _load_json_file(verdict_path)
    if not verdict:
        return f"缺发布裁决聚合：{verdict_path}。先跑 release_verdict.py --write 统一 gate/score/ledger/review-ui/QC/配方/合规结论。"
    verdict_status = str(verdict.get("status") or "").strip().lower()
    if verdict_status == "blocked":
        reasons = verdict.get("blocking_reasons") if isinstance(verdict.get("blocking_reasons"), list) else []
        first = reasons[0].get("message") if reasons and isinstance(reasons[0], dict) else ""
        suffix = f"：{first}" if first else ""
        return f"发布裁决仍 blocked{suffix}。见 {verdict_path}。"
    if verdict_status not in {"pass", "demo-only", "internal-only"}:
        return f"发布裁决状态异常（status={verdict_status or 'unset'}）：{verdict_path}。"
    return None


def _run_review_evidence_pre_gate(root: str, ep: str, p: Probes) -> None:
    for step, script, args in (
        ("final_timeline_probe", os.path.join(SKILLS_DIR, "n2d-compose", "scripts", "final_timeline_probe.py"), [root, ep, "--write", "--json"]),
        ("script_supervisor_log", os.path.join(SKILLS_DIR, "n2d", "scripts", "script_supervisor_log.py"), [root, ep, "check", "--write-missing", "--json"]),
    ):
        if not os.path.exists(script):
            p.prework.append({"step": step, "status": "skip", "detail": "script missing"})
            continue
        try:
            r = _run([sys.executable, script, *args])
            status = _script_result_status(r.returncode, r.stdout)
            p.prework.append({"step": step, "status": status, "detail": _finding_detail(r.stdout, r.stderr)})
            if status == "block" and not p.prework_block:
                p.prework_block = f"{step} 未通过；先补齐粗剪时间线/场记日志证据。"
        except Exception as e:  # pragma: no cover
            detail = str(e)[:160]
            p.prework.append({"step": step, "status": "block", "detail": detail})
            if not p.prework_block:
                p.prework_block = f"{step} 无法运行：{detail}"
    for step, script_name, args in (
        ("spectacle_video_qc", "spectacle_video_qc.py", [root, ep, "--write", "--write-sidecars"]),
        ("motion_reference_library", "motion_reference_library.py", [root, ep, "--write"]),
    ):
        script = os.path.join(SKILLS_DIR, "n2d-review", "scripts", script_name)
        if not os.path.exists(script):
            continue
        try:
            r = _run([sys.executable, script, *args])
            status = _script_result_status(r.returncode, r.stdout)
            p.prework.append({"step": step, "status": status, "detail": _finding_detail(r.stdout, r.stderr)})
            if status == "block" and not p.prework_block:
                p.prework_block = f"{step} 未通过；先补齐成片侧高动态/动作证据。"
        except Exception as e:  # pragma: no cover
            detail = str(e)[:160]
            p.prework.append({"step": step, "status": "block", "detail": detail})
            if not p.prework_block:
                p.prework_block = f"{step} 无法运行：{detail}"


def _run_review_acceptance_outputs(root: str, ep: str, p: Probes) -> None:
    governance_required = _production_governance_required(root)
    creative_args = [root, "check", "--write-missing", "--json"]
    if governance_required:
        creative_args.extend(["--require-decision", "--reason", "production/review acceptance"])
    commands = (
        ("progress_dag", os.path.join(SKILLS_DIR, "n2d", "progress.py"), ["audit-dag", root, "--json"], True),
        ("production_breakdown", os.path.join(SKILLS_DIR, "n2d-script", "scripts", "production_breakdown.py"), [root, ep, "check", "--json"], True),
        ("final_timeline_probe", os.path.join(SKILLS_DIR, "n2d-compose", "scripts", "final_timeline_probe.py"), [root, ep, "--write", "--json"], True),
        ("script_supervisor_log", os.path.join(SKILLS_DIR, "n2d", "scripts", "script_supervisor_log.py"), [root, ep, "check", "--write-missing", "--json"], True),
        ("production_locks", os.path.join(SKILLS_DIR, "n2d", "scripts", "production_locks.py"), [root, ep, "check", "--stage", "review", "--write-missing", "--json"], True),
        ("creative_governance", os.path.join(SKILLS_DIR, "n2d", "scripts", "creative_governance.py"), creative_args, True),
        ("score", os.path.join(SKILLS_DIR, "n2d-score", "scripts", "score.py"), [root, ep, "--run-checks", "--threshold", "85"], True),
        ("consistency_ledger", os.path.join(SKILLS_DIR, "n2d-review", "scripts", "consistency_ledger.py"), [root, ep], True),
        ("review_ui", os.path.join(SKILLS_DIR, "n2d-review-ui", "scripts", "review_ui.py"), [root, ep, "--write", "--export-findings", "--markdown"], True),
        ("episode_app", os.path.join(SKILLS_DIR, "n2d-review-ui", "scripts", "episode_app.py"), [root, "--episode", ep, "--write", "--index"], False),
        ("n2d_board", os.path.join(SKILLS_DIR, "n2d-review-ui", "scripts", "board.py"), [root, "--write", "--markdown"], False),
        ("failure_taxonomy", os.path.join(SKILLS_DIR, "n2d", "scripts", "failure_taxonomy.py"), [root, ep, "--write"], True),
        ("release_verdict", os.path.join(SKILLS_DIR, "n2d", "scripts", "release_verdict.py"), [root, ep, "--write"], True),
    )
    for step, script, args, required in commands:
        if not os.path.exists(script):
            p.prework.append({"step": step, "status": "skip", "detail": "script missing"})
            if required and not p.review_acceptance_block:
                p.review_acceptance_block = f"{step} 脚本缺失：{script}"
            continue
        try:
            r = _run([sys.executable, script, *args])
            status = _script_result_status(r.returncode, r.stdout)
            detail = _finding_detail(r.stdout, r.stderr)
            p.prework.append({"step": step, "status": status, "detail": detail})
            if required and status == "block" and not p.review_acceptance_block:
                p.review_acceptance_block = f"{step} 未通过：{detail or f'exit={r.returncode}'}"
        except Exception as e:  # pragma: no cover
            detail = str(e)[:160]
            p.prework.append({"step": step, "status": "block", "detail": detail})
            if required and not p.review_acceptance_block:
                p.review_acceptance_block = f"{step} 无法运行：{detail}"
    issue = _review_acceptance_issue(root, ep)
    if issue and not p.review_acceptance_block:
        p.review_acceptance_block = issue


# ── 真实探针（subprocess/import；全部防御性，绝不让编排器崩）──────────────────
def _run(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=900)


def _parse_trailing_json(stdout: str) -> Dict[str, Any]:
    """取 stdout 末尾的 JSON 块。dashboard gate 先打 alerts、最后 json.dumps(indent=2) 多行输出，
    所以不能只看最后一行——从末尾逐行上移，找到第一个能整体解析成 dict 的后缀。"""
    lines = (stdout or "").splitlines()
    for i in range(len(lines)):
        if lines[len(lines) - 1 - i].lstrip().startswith("{"):
            try:
                obj = json.loads("\n".join(lines[len(lines) - 1 - i:]))
                if isinstance(obj, dict):
                    return obj
            except Exception:
                continue
    return {}


def _parse_json_tail(stdout: str) -> Dict[str, Any]:
    """Backward-compatible alias for older call sites."""
    return _parse_trailing_json(stdout)


def _script_result_status(returncode: int, stdout: str) -> str:
    if returncode != 0:
        return "block"
    obj = _parse_trailing_json(stdout)
    raw = str(obj.get("status") or obj.get("verdict") or "").strip().lower() if isinstance(obj, dict) else ""
    if raw in {"block", "blocked", "fail", "failed", "error"}:
        return "block"
    if raw in {"warn", "warning", "warnings"}:
        return "warn"
    return "pass"


def _finding_detail(stdout: str, stderr: str) -> str:
    obj = _parse_trailing_json(stdout)
    findings = obj.get("findings") if isinstance(obj, dict) else None
    if isinstance(findings, list) and findings:
        first = next((f for f in findings if isinstance(f, dict)), findings[0])
        if isinstance(first, dict):
            msg = first.get("message") or first.get("msg") or first.get("code")
            if msg:
                return str(msg)[:200]
        return str(first)[:200]
    text = (stderr or stdout or "").strip()
    if not text:
        return ""
    return (text.splitlines()[-1] if text.splitlines() else text)[:200]


def _run_report_only_prework(p: Probes, commands: List[tuple], cache=None) -> None:
    """Run deterministic sidecar planners without turning report-only gaps into blockers.

    这些 planner 互相独立、只产 report/sidecar、从不阻断流程，是并行+缓存的安全目标：
    缺脚本仍按序记 skip；存在的脚本并发执行、按声明顺序回填结果（顺序不变，只更快），
    pass/warn 结果写入 prework 缓存，输入/脚本未变时下次直接复用、跳过 subprocess。
    """
    steps = []          # (step_key, (step, script_path, args))
    placeholders = {}   # step -> 缺脚本的 skip 占位，保持原有顺序
    for step, script_path, args in commands:
        if not os.path.exists(script_path):
            placeholders[step] = {"step": step, "status": "skip", "detail": "script missing"}
        else:
            steps.append((step, (step, script_path, args)))

    def run_one(obj):
        step, script_path, args = obj
        try:
            r = _run([sys.executable, script_path, *args])
            return {"step": step, "status": "pass" if r.returncode == 0 else "warn",
                    "detail": _finding_detail(r.stdout, r.stderr)}
        except Exception as exc:  # pragma: no cover
            return {"step": step, "status": "skip", "detail": str(exc)[:160]}

    outcomes = {}
    if steps:
        for o in _prework_run(steps, run_one, cache=cache,
                              should_cache=lambda o: o.get("status") in ("pass", "warn")):
            outcomes[o.get("step")] = {k: v for k, v in o.items() if k != "_cached"}

    # 按 commands 原顺序回填，保证 p.prework 顺序与串行版逐字一致。
    for step, _script_path, _args in commands:
        entry = placeholders.get(step) or outcomes.get(step)
        if entry is not None:
            p.prework.append(entry)


def _script_episode_labels(root: str) -> List[str]:
    sdir = os.path.join(root, "脚本")
    try:
        eps = [
            d for d in os.listdir(sdir)
            if d.startswith("第") and d.endswith("集") and os.path.isfile(os.path.join(sdir, d, "voiceover.txt"))
        ]
    except Exception:
        return []
    def key(label: str) -> int:
        m = re.search(r"\d+", label)
        return int(m.group()) if m else 10**9
    return sorted(eps, key=key)


def _series_msg_implicates_ep(msg: str, ep: str) -> bool:
    if not ep:
        return False
    return ep in str(msg or "")


def _run_series_retention_prework(p: Probes, root: str, ep: str) -> None:
    """Run series-level retention gates before image prompt production.

    compose/review gate still performs the deliverable-boundary check. This prework
    catches obvious cross-episode retention damage before expensive image/video work.
    """
    eps = _script_episode_labels(root)
    if len(eps) < 3:
        story_script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "story_integrity_audit.py")
        if os.path.exists(story_script) and ep:
            try:
                r = _run([sys.executable, story_script, root, ep, "--write", "--strict", "--json"])
                out = _parse_trailing_json(r.stdout)
                findings = out.get("findings") if isinstance(out, dict) else []
                warn_n = sum(1 for f in findings if isinstance(f, dict) and f.get("severity") == "warn")
                if r.returncode != 0:
                    if not p.prework_block:
                        p.prework_block = (
                            "pilot_arc_contract 未通过；第1-2集也必须先锁系列承诺、主角欲望、首个兑现/阻碍/反转，"
                            "再进入出图 prompt。"
                        )
                    p.prework.append({
                        "step": "pilot_arc_contract_gate",
                        "status": "block",
                        "detail": _finding_detail(r.stdout, r.stderr) or f"episodes={len(eps)} warn={warn_n}",
                    })
                else:
                    p.prework.append({"step": "pilot_arc_contract_gate", "status": "pass", "detail": f"episodes={len(eps)} warn={warn_n}"})
            except Exception as exc:  # pragma: no cover
                p.prework.append({"step": "pilot_arc_contract_gate", "status": "skip", "detail": str(exc)[:160]})
        else:
            p.prework.append({"step": "pilot_arc_contract_gate", "status": "skip", "detail": f"episodes={len(eps)} < 3"})
        return

    beat_script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "beat_audit.py")
    if os.path.exists(beat_script):
        try:
            r = _run([sys.executable, beat_script, root, "--series", "--json"])
            out = _parse_trailing_json(r.stdout)
            blockers: List[str] = []
            for pair in out.get("duplicates") or []:
                if isinstance(pair, (list, tuple)) and len(pair) >= 3 and ep in {str(pair[0]), str(pair[1])}:
                    blockers.append(f"{pair[0]}↔{pair[1]} 桥段指纹重合 {pair[2]}")
            for key in ("cold_open_chain_findings", "highlight_climax_findings"):
                for item in out.get(key) or []:
                    if not isinstance(item, dict):
                        continue
                    msg = str(item.get("msg") or item.get("message") or "")
                    sev = str(item.get("severity") or "")
                    if sev in {"warn", "must", "block"} and _series_msg_implicates_ep(msg, ep):
                        blockers.append(msg)
            if blockers:
                detail = blockers[0][:200]
                if not p.prework_block:
                    p.prework_block = (
                        "series_retention_gate 未通过；先回 n2d-script 调整跨集冷开场链、雷同桥段或看点高潮位，"
                        "再进入出图 prompt。"
                    )
                p.prework.append({"step": "series_retention_gate", "status": "block", "detail": detail})
            else:
                other_n = sum(len(out.get(k) or []) for k in ("cold_open_chain_findings", "highlight_climax_findings")) + len(out.get("duplicates") or [])
                p.prework.append({"step": "series_retention_gate", "status": "pass", "detail": f"episodes={len(eps)} other_findings={other_n}"})
        except Exception as exc:  # pragma: no cover
            p.prework.append({"step": "series_retention_gate", "status": "skip", "detail": str(exc)[:160]})

    balance_script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "series_balance.py")
    if os.path.exists(balance_script):
        try:
            r = _run([sys.executable, balance_script, root, "--strict", "--json"])
            out = _parse_trailing_json(r.stdout)
            findings = out.get("findings") if isinstance(out, dict) else []
            detail = _finding_detail(r.stdout, r.stderr)
            if r.returncode != 0:
                if not p.prework_block:
                    p.prework_block = "series_balance 未通过；全剧后段钩子/反转曲线塌陷，先回 n2d-script 重排高能桥段。"
                p.prework.append({"step": "series_balance", "status": "block", "detail": detail})
            else:
                warn_n = sum(1 for f in findings if isinstance(f, dict) and f.get("severity") == "warn")
                p.prework.append({"step": "series_balance", "status": "warn" if warn_n else "pass", "detail": detail or f"warn={warn_n}"})
        except Exception as exc:  # pragma: no cover
            p.prework.append({"step": "series_balance", "status": "skip", "detail": str(exc)[:160]})


def _run_production_breakdown_prework(p: Probes, root: str, ep: str) -> None:
    """P-3 production handoff must be confirmed before image prompt/paid image work.

    New projects hit this at `image_prompt`; old projects may already have
    `出图prompt=✅`, so `image` also rechecks it before paid generation.
    """
    production_script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "production_breakdown.py")
    if not os.path.exists(production_script):
        return
    try:
        r = _run([sys.executable, production_script, root, ep, "check", "--json", "--write-missing"])
        report = _parse_trailing_json(r.stdout) or {}
        status = str(report.get("status") or ("pass" if r.returncode == 0 else "block")).strip()
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        p.prework.append({
            "step": "production_breakdown",
            "status": "pass" if status == "pass" else "block",
            "detail": f"{summary.get('pass', 0)}/{summary.get('required', 5)} confirmed",
            "check_path": report.get("check_path") or os.path.join(root, "生产数据", f"production_breakdown_check_{ep}.json"),
        })
        if status != "pass":
            _record_prework_block(p, "production_breakdown", (
                "P-3 制片拆解包未确认；先补齐 脚本/{ep}/production_breakdown.json、"
                "continuity_breakdown.json、continuity_chain.json、continuity_bible.json、ai_shooting_schedule.json、ai_call_sheet.md，删除待补/TODO，"
                "并把每个文件 status 改为 confirmed，再进入出图 prompt/付费出图。"
            ).format(ep=ep))
    except Exception as e:  # pragma: no cover
        detail = str(e)[:160]
        _record_prework_block(p, "production_breakdown", f"production_breakdown 无法运行：{detail}")
        p.prework.append({"step": "production_breakdown", "status": "block", "detail": detail})


def _run_story_acceptance_prework(p: Probes, root: str, ep: str, packet_kind: str) -> None:
    """Traditional low-cost acceptance: table read before storyboard, animatic before image prompt."""
    script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "story_acceptance_packets.py")
    if not os.path.exists(script):
        return
    try:
        r = _run([sys.executable, script, root, ep, "check", "--kind", packet_kind, "--write-missing", "--json"])
        report = _parse_trailing_json(r.stdout) or {}
        status = str(report.get("status") or ("pass" if r.returncode == 0 else "block")).strip()
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        p.prework.append({
            "step": f"story_acceptance_{packet_kind}",
            "status": "pass" if status == "pass" else "block",
            "detail": f"{summary.get('pass', 0)}/{summary.get('required', 0)} confirmed",
            "check_path": report.get("check_path"),
        })
        if status != "pass":
            label = "围读验收包" if packet_kind == "table_read" else "animatic 粗剪验收包"
            _record_prework_block(p, f"story_acceptance_{packet_kind}", (
                f"{label}未确认；先补齐 脚本/{ep}/{packet_kind}_packet.json/md，"
                "确认台词/节奏/时长风险后把 status 改为 confirmed，再继续。"
            ))
    except Exception as e:  # pragma: no cover
        detail = str(e)[:160]
        _record_prework_block(p, f"story_acceptance_{packet_kind}", f"story_acceptance_{packet_kind} 无法运行：{detail}")
        p.prework.append({"step": f"story_acceptance_{packet_kind}", "status": "block", "detail": detail})


def _run_preventive_contract_prework(p: Probes, root: str, ep: str, stage_name: str) -> None:
    """Run preventive production contracts before expensive or irreversible stages."""
    script = os.path.join(SKILLS_DIR, "n2d", "scripts", "preventive_contracts.py")
    if not os.path.exists(script):
        detail = "缺 skills/n2d/scripts/preventive_contracts.py，预防式合同 gate 无法运行（fail-closed）"
        _record_prework_block(p, "preventive_contracts", detail)
        p.prework.append({"step": "preventive_contracts", "stage": stage_name, "status": "block", "detail": detail})
        return
    try:
        r = _run([sys.executable, script, root, ep, "--stage", stage_name, "--write", "--write-missing", "--json"])
        report = _parse_trailing_json(r.stdout) or {}
        status = str(report.get("status") or ("pass" if r.returncode == 0 else "blocked")).strip().lower()
        findings = report.get("findings") if isinstance(report.get("findings"), list) else []
        gates = ", ".join(str(g) for g in (report.get("gates") or [])) or stage_name
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        detail = _finding_detail(r.stdout, r.stderr) or f"{gates}; block={summary.get('block', 0)}"
        entry = {
            "step": "preventive_contracts",
            "stage": stage_name,
            "status": "pass" if r.returncode == 0 and status == "pass" else "block",
            "detail": detail,
        }
        if report.get("contract_path"):
            entry["contract_path"] = report.get("contract_path")
        outputs = report.get("outputs") if isinstance(report.get("outputs"), dict) else {}
        if outputs.get("json"):
            entry["check_path"] = outputs.get("json")
        p.prework.append(entry)
        if entry["status"] == "block":
            return_stage = ""
            for finding in findings:
                if isinstance(finding, dict) and finding.get("return_to_stage"):
                    return_stage = str(finding.get("return_to_stage"))
                    break
            target = f"先回 {return_stage} " if return_stage else "先"
            _record_prework_block(p, "preventive_contracts", (
                f"预防式合同未通过（{gates}）：{detail}。"
                f"{target}补齐 {report.get('contract_path') or '脚本/<集>/preventive_contracts.json'} 并确认后再继续。"
            ))
    except Exception as e:  # pragma: no cover
        detail = str(e)[:160]
        _record_prework_block(p, "preventive_contracts", f"preventive_contracts 无法运行：{detail}")
        p.prework.append({"step": "preventive_contracts", "stage": stage_name, "status": "block", "detail": detail})


PRODUCTION_LOCK_STAGES = {"script_stage2", "image_prompt", "image", "video_prompt", "video", "compose", "review"}


def _production_governance_required(root: str) -> bool:
    profile = str(get_setting(root, "一致性严格度", "") or "").strip().lower()
    intent = str(get_setting(root, "合规用途", "") or "").strip().lower()
    smoke = str(get_setting(root, "后端Smoke硬闸", "") or "").strip()
    if profile.startswith("production") or intent == "paid_distribution" or smoke in {"是", "true", "1", "yes"}:
        return True
    return os.path.exists(os.path.join(root, "生产数据", "batch_queue.json"))


def _production_lock_ledger_exists(root: str, ep: str) -> bool:
    return os.path.exists(os.path.join(root, "生产数据", f"production_locks_{ep}.json"))


def _run_production_locks_prework(p: Probes, root: str, ep: str, stage_key: str, *, write_missing: bool = False) -> None:
    if stage_key not in PRODUCTION_LOCK_STAGES:
        return
    if not write_missing and not (_production_governance_required(root) or _production_lock_ledger_exists(root, ep)):
        return
    script = os.path.join(SKILLS_DIR, "n2d", "scripts", "production_locks.py")
    if not os.path.exists(script):
        detail = "缺 skills/n2d/scripts/production_locks.py，生产锁版账无法核验（fail-closed）"
        _record_prework_block(p, "production_locks", detail)
        p.prework.append({"step": "production_locks", "stage": stage_key, "status": "block", "detail": detail})
        return
    args = [root, ep, "check", "--stage", stage_key, "--json"]
    if write_missing:
        args.insert(3, "--write-missing")
    try:
        r = _run([sys.executable, script, *args])
        report = _parse_trailing_json(r.stdout) or {}
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        detail = _finding_detail(r.stdout, r.stderr) or f"block={summary.get('block', 0)} locks={summary.get('locks', 0)}/{summary.get('required_locks', 0)}"
        status = "pass" if r.returncode == 0 and report.get("status") == "pass" else "block"
        p.prework.append({
            "step": "production_locks",
            "stage": stage_key,
            "status": status,
            "detail": detail,
            "check_path": report.get("check_path"),
        })
        if status == "block":
            _record_prework_block(p, "production_locks", f"生产锁版账未通过（{stage_key}）：{detail}。先确认相关 lock，或在 creative_decisions.jsonl 记录解锁/最小返工范围后再继续。")
    except Exception as e:  # pragma: no cover
        detail = str(e)[:160]
        _record_prework_block(p, "production_locks", f"production_locks 无法运行：{detail}")
        p.prework.append({"step": "production_locks", "stage": stage_key, "status": "block", "detail": detail})


def _image_qc_report_path(root: str, ep: str) -> str:
    return os.path.join(root, "生产数据", "image_qc", ep, f"image_qc_{ep}.json")


def _image_qc_gate_issue(root: str, ep: str) -> Optional[str]:
    """Video/compose 前的硬护栏：缺报告、低精度或已有 hard block 都不能继续。"""
    path = _image_qc_report_path(root, ep)
    if not os.path.isfile(path):
        return f"缺 image_qc 报告：{path}；先跑 n2d-image 的 image_qc 并确认 full 精度。"
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception as exc:
        return f"image_qc 报告不可读：{path}（{exc}）；修复后重跑 image_qc。"
    # 新鲜度先于一切：旧报告/产物在 QC 后被重出，verdict 再绿也不证明当前像素。镜像 dashboard
    # 的 image_qc_fingerprint_status 口径——非 fresh（stale 或无 inputs_fingerprint）一律 block，
    # 堵「证声明不证现实」（fail-closed，与 video/compose 下游护栏同源）。
    try:
        from skill_snapshot import fingerprint_is_fresh
        fresh = fingerprint_is_fresh((data or {}).get("inputs_fingerprint"), root)
    except Exception:
        fresh = None
    if fresh is not True:
        state = "stale（QC 后产物又变了）" if fresh is False else "unknown（报告无 inputs_fingerprint，无法证明对应当前图片）"
        return (f"image_qc 报告新鲜度={state}：{path}；旧报告不能证明当前图片一致，"
                f"先对当前产物重跑 image_qc / dashboard gate --stage image。")
    env = data.get("qc_environment") if isinstance(data, dict) else {}
    summary = data.get("summary") if isinstance(data, dict) else {}
    precision = str((env or {}).get("precision_level") or "").strip().lower()
    if precision != "full":
        label = precision or "unknown"
        return f"image_qc 精度为 {label}：{path}；补依赖重跑到 full，或停下登记人审后再继续。"
    hard_blocks = int((summary or {}).get("hard_blocks") or 0)
    verdict = str((summary or {}).get("verdict") or "").strip().lower()
    if hard_blocks > 0 or verdict == "block":
        return f"image_qc 仍有硬阻断（hard_blocks={hard_blocks}, verdict={verdict or 'unknown'}）：{path}。"
    return None


def gather_preview_probes(root: str, route: Dict[str, Any], stage_key: str) -> Probes:
    """Read-only probe set for desktop UI previews.

    Opening or refreshing the app's "next action" strip must not write production
    sidecars; otherwise an archive baseline can immediately get new diffs.
    """
    spec = stage_for_key(stage_key) or {}
    p = Probes()
    ep = route.get("ep")
    if ep:
        p.entry_checks = entry_checks(root, ep, stage_key=stage_key, preview=True)
        p.entry_check_block = _entry_check_block(p.entry_checks, stage_key)
    if stage_key in IMAGE_QC_STRICT_STAGES and ep:
        issue = _image_qc_gate_issue(root, ep)
        if issue:
            p.image_qc_block = issue
            p.prework.append({"step": "image_qc", "status": "block", "detail": issue[:160]})
        else:
            p.prework.append({"step": "image_qc", "status": "pass"})
    gate_stage = _gate_stage_for_frontier(root, ep, stage_key, spec)
    if gate_stage and ep:
        gate = _gate_from_existing_findings(root, ep, gate_stage)
        if gate:
            p.gate = gate
            p.prework.append({
                "step": "gate",
                "stage": gate_stage,
                "status": "block" if gate.get("blocked") else "pass",
                "detail": "existing findings",
            })
    if stage_key == "review" and ep:
        issue = _review_acceptance_issue(root, ep)
        if issue:
            p.review_acceptance_block = issue
            p.prework.append({"step": "review_acceptance", "status": "block", "detail": issue[:160]})
    if stage_key == "script_stage1":
        try:
            p.pending_choices = [k for k in FIRST_RUN_CHOICES if _explicit_choice_missing(root, k)]
        except Exception:  # pragma: no cover
            p.pending_choices = []
    return p


def gather_probes(root: str, route: Dict[str, Any], stage_key: str, preview: bool = False) -> Probes:
    if preview:
        return gather_preview_probes(root, route, stage_key)
    spec = stage_for_key(stage_key) or {}
    p = Probes()
    ep = route.get("ep")

    if ep:
        p.entry_checks = entry_checks(root, ep, stage_key=stage_key)
        p.entry_check_block = _entry_check_block(p.entry_checks, stage_key)
    p.capability_block = _video_capability_block(root, stage_key)
    script_stage1_missing_choices: List[str] = []
    if stage_key == "script_stage1":
        try:
            script_stage1_missing_choices = [k for k in FIRST_RUN_CHOICES if _explicit_choice_missing(root, k)]
        except Exception:  # pragma: no cover
            script_stage1_missing_choices = []

    # Context pack / creative loop：确定性生成阶段最小上下文和评审-修订包。
    # 失败不默认阻断；真正的 stage gate 仍是放行真值。
    if ep and stage_key in ENTRY_GATED_STAGES:
        for step, script_name, args in (
            ("context_pack", "context_pack.py", [root, ep, stage_key, "--write", "--json"]),
            ("creative_loop", "creative_loop.py", [root, ep, stage_key, "--write", "--json"]),
        ):
            if step == "creative_loop" and stage_key not in AGENT_GEN_STAGES:
                continue
            script = os.path.join(SKILLS_DIR, "n2d", "scripts", script_name)
            if not os.path.exists(script):
                p.prework.append({"step": step, "status": "skip", "detail": "script missing"})
                continue
            try:
                r = _run([sys.executable, script, *args])
                p.prework.append({
                    "step": step,
                    "status": "pass" if r.returncode == 0 else "warn",
                    "detail": _finding_detail(r.stdout, r.stderr),
                })
            except Exception as e:  # pragma: no cover
                p.prework.append({"step": step, "status": "skip", "detail": str(e)[:160]})
        genre_script = os.path.join(SKILLS_DIR, "n2d", "scripts", "genre_packs.py")
        if os.path.exists(genre_script):
            try:
                r = _run([sys.executable, genre_script, "context", root, ep, stage_key, "--write", "--json"])
                out = _parse_trailing_json(r.stdout)
                status = str(out.get("status") or ("pass" if r.returncode == 0 else "warn"))
                p.prework.append({
                    "step": "genre_pack_context",
                    "status": "pass" if status == "pass" else ("block" if status == "fail" else "warn"),
                    "detail": f"genre={(out.get('genre') or {}).get('genre_key') or '-'} active={(out.get('summary') or {}).get('active_scenes', 0)}",
                })
                if status == "fail" and stage_key in {"video_prompt", "video", "compose", "review"} and not p.prework_block:
                    p.prework_block = "genre_pack_context 未通过；先补齐本题材典型场景的运动契约/降级方案，再进入下游 gate。"
            except Exception as e:  # pragma: no cover
                p.prework.append({"step": "genre_pack_context", "status": "skip", "detail": str(e)[:160]})

    # doctor：能力/精度档（只探不改、不花钱）
    try:
        import doctor
        caps = doctor.collect(root)
        p.prework.append({"step": "doctor", "status": "ok",
                          "image_backend": (caps.get("image_backend") or {}).get("status"),
                          "voice": caps.get("voice")})
        img = caps.get("image_backend") or {}
        if stage_key in ("image_prompt", "image") and img.get("status") in ("down", "error", "missing"):
            p.env_missing = f"{img.get('name')}（{img.get('status')}）"
    except Exception as e:  # pragma: no cover - 环境相关
        p.prework.append({"step": "doctor", "status": "skip", "detail": str(e)[:120]})

    # source_comprehension_gate：最上游前置——只要有源小说，就先把编剧理解变成可审计合同。
    if stage_key == "script_stage1":
        lang_script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "source_language.py")
        if os.path.exists(lang_script):
            try:
                r = _run([sys.executable, lang_script, root, "--json"])
                report = _parse_json_tail(r.stdout) or {}
                verdict = str(report.get("verdict") or "").strip()
                if verdict == "needs_comprehension":
                    reg = report.get("register")
                    issues = [str(x) for x in (report.get("contract_issues") or [])]
                    issue_text = "；".join(issues[:6]) or (report.get("message") or "")[:220]
                    p.prework_block = (
                        f"源理解合同未确认或不完整（register={reg}）：{issue_text}。"
                        "小说不能只切章节；要先把现代白话理解、爽点/承诺账、人物动机、因果链、伏笔账、"
                        "设定/战力规则变成可审计输入。先跑 "
                        f"python3 skills/n2d-script/scripts/source_language.py {root} --scaffold，"
                        "补全 设定库/source_comprehension.md 与 "
                        "source_comprehension.json.understanding_contract，并把 status 置 confirmed，再从理解层拆集。")
                    p.prework.append({"step": "source_comprehension_gate", "status": "block",
                                      "detail": issue_text[:240], "register": reg})
                else:
                    p.prework.append({"step": "source_comprehension_gate",
                                      "status": "pass" if verdict in ("pass", "no_source") else (verdict or "skip"),
                                      "detail": f"register={report.get('register')}"})
            except Exception as e:  # pragma: no cover - 环境相关
                p.prework.append({"step": "source_comprehension_gate", "status": "skip", "detail": str(e)[:120]})

    # boundary_audit：script stage1 前必须先确认粗胚边界没有把剧情闭环切断。
    if stage_key == "script_stage1":
        midstart_pack = os.path.join(root, "设定库", "中段开工前情资产包.md")
        midstart_script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "midstart_context.py")
        if os.path.exists(midstart_pack) and os.path.exists(midstart_script):
            try:
                r = _run([sys.executable, midstart_script, root, "check", "--json"])
                report = _parse_json_tail(r.stdout)
                verdict = str((report or {}).get("verdict") or "").strip().lower()
                if r.returncode == 0 and verdict in ("pass", "warn"):
                    p.prework.append({"step": "midstart_context", "status": verdict or "pass"})
                else:
                    findings = (report or {}).get("findings") or []
                    detail = ""
                    if findings:
                        first = findings[0]
                        detail = str(first.get("message") or first)[:160]
                    else:
                        detail = (r.stderr or r.stdout or "").strip()[:160]
                    if not p.prework_block:
                        p.prework_block = (
                            "中段开工前情资产包未通过；先补齐 "
                            f"{midstart_pack}，再写 voiceover。"
                        )
                    p.prework.append({"step": "midstart_context", "status": "block", "detail": detail})
            except Exception as e:  # pragma: no cover
                detail = str(e)[:160]
                if not p.prework_block:
                    p.prework_block = f"midstart_context 无法运行：{detail}"
                p.prework.append({"step": "midstart_context", "status": "block", "detail": detail})

        script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "boundary_audit.py")
        review_script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "boundary_review.py")
        review_json = os.path.join(root, "脚本", "boundary_review.json")
        if os.path.exists(script):
            try:
                r = _run([sys.executable, script, root, "--strict"])
                if r.returncode == 0:
                    p.prework.append({"step": "boundary_audit", "status": "pass"})
                elif os.path.exists(review_script):
                    rr = _run([sys.executable, review_script, "check", root, "--json"])
                    if rr.returncode == 0:
                        detail = (r.stdout or r.stderr or "").strip().splitlines()[-1:] or [""]
                        p.prework.append({"step": "boundary_audit", "status": "reviewed",
                                          "detail": (detail[0] if detail else "")[:160],
                                          "review_path": review_json})
                    else:
                        detail = _finding_detail(rr.stdout, rr.stderr)
                        if not p.prework_block:
                            p.prework_block = (
                                "boundary_audit 标出高风险粗胚边界；先运行 "
                                f"python3 skills/n2d-script/scripts/boundary_review.py draft {root} --write，"
                                f"填写 {review_json} 的 decision/notes，再复跑 check。"
                            )
                        p.prework.append({"step": "boundary_audit", "status": "block",
                                          "detail": detail[:160], "review_path": review_json})
                else:
                    detail = (r.stdout or r.stderr or "").strip().splitlines()[-1:] or [""]
                    if not p.prework_block:
                        p.prework_block = (
                            "boundary_audit 标出高风险粗胚边界；先做 5-10 集窗口复核并写 "
                            f"{review_json}，再写 voiceover。"
                        )
                    p.prework.append({"step": "boundary_audit", "status": "block",
                                      "detail": (detail[0] if detail else "")[:160]})
            except Exception as e:  # pragma: no cover
                detail = str(e)[:160]
                if not p.prework_block:
                    p.prework_block = f"boundary_audit 无法运行：{detail}"
                p.prework.append({"step": "boundary_audit", "status": "block", "detail": detail})

        dev_script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "development_pack.py")
        if os.path.exists(dev_script):
            try:
                r = _run([sys.executable, dev_script, root, "check", "--json", "--write-missing"])
                report = _parse_trailing_json(r.stdout) or {}
                status = str(report.get("status") or ("pass" if r.returncode == 0 else "block")).strip()
                summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
                p.prework.append({
                    "step": "development_pack",
                    "status": "pass" if status == "pass" else "block",
                    "detail": f"{summary.get('pass', 0)}/{summary.get('required', 5)} confirmed",
                    "check_path": report.get("check_path") or os.path.join(root, "生产数据", "development_pack_check.json"),
                })
                if status != "pass" and not p.prework_block and not script_stage1_missing_choices:
                    p.prework_block = (
                        "P-1 开发包未确认；先补齐 开发包/series_bible.md、adaptation_strategy.json、"
                        "season_arc.json、production_feasibility.json、pilot_greenlight.md，删除待补/TODO，"
                        "并把每个文件 status 改为 confirmed，再进入阶段1写词。"
                    )
            except Exception as e:  # pragma: no cover
                detail = str(e)[:160]
                if not p.prework_block:
                    p.prework_block = f"development_pack 无法运行：{detail}"
                p.prework.append({"step": "development_pack", "status": "block", "detail": detail})

    # director_blocking_pack：阶段2 分镜前先过导演排戏层，不让 storyboard 临场发明轴线/调度/转场。
    if stage_key == "script_stage2" and ep:
        _run_story_acceptance_prework(p, root, ep, "table_read")
        _run_preventive_contract_prework(p, root, ep, "script_stage2")
        director_script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "director_blocking_pack.py")
        if os.path.exists(director_script):
            try:
                r = _run([sys.executable, director_script, root, ep, "check", "--json", "--write-missing"])
                report = _parse_trailing_json(r.stdout) or {}
                status = str(report.get("status") or ("pass" if r.returncode == 0 else "block")).strip()
                summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
                p.prework.append({
                    "step": "director_blocking_pack",
                    "status": "pass" if status == "pass" else "block",
                    "detail": f"{summary.get('pass', 0)}/{summary.get('required', 6)} confirmed",
                    "check_path": report.get("check_path") or os.path.join(root, "生产数据", f"director_blocking_pack_check_{ep}.json"),
                })
                if status != "pass":
                    _record_prework_block(p, "director_blocking_pack", (
                        "P-2 导演排戏包未确认；先补齐 脚本/{ep}/director_beat_sheet.json、"
                        "axis_blocking_map.json、shot_progression_plan.json、transition_map.json、"
                        "vertical_composition_plan.json、edit_rhythm_map.json，删除待补/TODO，"
                        "并把每个文件 status 改为 confirmed，再进入阶段2分镜设计。"
                    ).format(ep=ep))
            except Exception as e:  # pragma: no cover
                detail = str(e)[:160]
                _record_prework_block(p, "director_blocking_pack", f"director_blocking_pack 无法运行：{detail}")
                p.prework.append({"step": "director_blocking_pack", "status": "block", "detail": detail})

    # script text audits：分镜/台词一旦放进出图 prompt，后续全是贵工位；
    # 在 image_prompt 前沿把源文覆盖和集内留存节拍收紧为固定前置。
    if stage_key in SCRIPT_TEXT_AUDIT_STAGES and ep:
        _run_story_acceptance_prework(p, root, ep, "animatic")
        _run_preventive_contract_prework(p, root, ep, "image_prompt")
        # 本阶段 prework 缓存：指纹覆盖本集主输入 + 全部 n2d-script 审计脚本的 mtime，
        # 任一变化即失效；输入/脚本未变时复用上轮结果，跳过十几个 subprocess 冷启动。
        _audit_script_paths = sorted(glob.glob(os.path.join(SKILLS_DIR, "n2d-script", "scripts", "*.py")))
        _prework_cache_obj = _make_prework_cache(root, ep, "image_prompt", _audit_script_paths)
        audits = [
            (
                "source_adaptation_audit",
                os.path.join(SKILLS_DIR, "n2d-script", "scripts", "source_adaptation_audit.py"),
                [root, ep, "--strict", "--json"],
                "source_adaptation_audit 未通过；先回 n2d-script 补齐 raw→voiceover/storyboard 的关键动机/伏笔/反转覆盖。",
            ),
            (
                "beat_audit",
                os.path.join(SKILLS_DIR, "n2d-script", "scripts", "beat_audit.py"),
                [root, ep, "--strict", "--json"],
                "beat_audit 未通过；先回 n2d-script 补冷开场、钩子间隔、反转、集尾钩、信息回报或集间钩子接力（上集集尾钩→本集冷开场接住同一根线）。",
            ),
            (
                "script_quality_gate",
                os.path.join(SKILLS_DIR, "n2d-script", "scripts", "script_quality_gate.py"),
                [root, ep, "--strict", "--write", "--json"],
                "script_quality_gate 未通过；n2d-script 必须先把“好看”拆成可签收字段（核心看点、首屏钩、留存账本、逐镜戏剧功能、观众问题账本），再交给 image/video 下游。",
            ),
            (
                "story_economy_audit",
                os.path.join(SKILLS_DIR, "n2d-script", "scripts", "story_economy_audit.py"),
                [root, ep, "--strict", "--write", "--json"],
                "story_economy_audit 未通过；先回 n2d-script 压缩非战斗/非强情绪长段，把解释、行进、普通反应改成短镜/旁白/蒙太奇后再进贵工位。",
            ),
            (
                "spectacle_contract_audit",
                os.path.join(SKILLS_DIR, "n2d-script", "scripts", "spectacle_contract_audit.py"),
                [root, ep, "--strict", "--json"],
                "spectacle_contract_audit 未通过；先回 n2d-script 补打斗/追逐/腾云驾雾/大场景专项契约。",
            ),
            (
                "setup_payoff_gate",
                os.path.join(SKILLS_DIR, "n2d-script", "scripts", "setup_payoff_ledger.py"),
                [root, "--gate", ep, "--json"],
                "本集显式伏笔在 setup_payoff_ledger 缺登记或未填兑现集；先跑 setup_payoff_ledger.py --write 建账并锁每个伏笔的兑现集。",
            ),
            (
                "antecedent_audit",
                os.path.join(SKILLS_DIR, "n2d-script", "scripts", "antecedent_audit.py"),
                [root, ep, "--strict", "--json"],
                "antecedent_audit 发现本集引用的人/物/设定缺前情交代（删集/跳章致前因缺失）；先补前情或恢复被删集。",
            ),
        ]
        # 硬闸门审计：互相独立 → 并行执行、按声明顺序回填（"第一个失败决定 prework_block"
        # 与串行逐字一致）。只缓存 pass；block/异常下次仍重跑（修复后输入变化本会失效，
        # 这是防瞬时崩溃假阻断的廉价保险）。
        def _run_audit(obj):
            step, script_path, args, block_msg = obj
            try:
                r = _run([sys.executable, script_path, *args])
                if r.returncode == 0:
                    return {"step": step, "status": "pass"}
                return {"step": step, "status": "block",
                        "detail": _finding_detail(r.stdout, r.stderr), "block_msg": block_msg}
            except Exception as e:  # pragma: no cover
                detail = str(e)[:160]
                return {"step": step, "status": "block", "detail": detail,
                        "block_msg": f"{step} 无法运行：{detail}"}

        _audit_steps = [(step, (step, sp, args, block_msg))
                        for step, sp, args, block_msg in audits if os.path.exists(sp)]
        for o in _prework_run(_audit_steps, _run_audit, cache=_prework_cache_obj,
                              should_cache=lambda o: o.get("status") == "pass"):
            entry = {"step": o["step"], "status": o["status"]}
            if "detail" in o:
                entry["detail"] = o["detail"]
            p.prework.append(entry)
            if o["status"] == "block" and not p.prework_block:
                p.prework_block = o.get("block_msg") or f"{o['step']} 未通过"

        _run_series_retention_prework(p, root, ep)

        story_script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "story_integrity_audit.py")
        if os.path.exists(story_script):
            try:
                r = _run([sys.executable, story_script, root, ep, "--write", "--json"])
                out = _parse_trailing_json(r.stdout)
                findings = out.get("findings") if isinstance(out, dict) else []
                block_n = sum(1 for f in findings if isinstance(f, dict) and f.get("severity") in {"block", "must"})
                warn_n = sum(1 for f in findings if isinstance(f, dict) and f.get("severity") == "warn")
                info_n = sum(1 for f in findings if isinstance(f, dict) and f.get("severity") == "info")
                detail = f"warn={warn_n} info={info_n}"
                if r.returncode != 0 or block_n:
                    if not p.prework_block:
                        p.prework_block = "story_integrity_audit 无法完成剧情完整性体检；先回 n2d-script 补 voiceover/剧情账本。"
                    p.prework.append({"step": "story_integrity_audit", "status": "block",
                                      "detail": _finding_detail(r.stdout, r.stderr) or detail})
                else:
                    p.prework.append({"step": "story_integrity_audit",
                                      "status": "warn" if warn_n else "pass",
                                      "detail": detail})
            except Exception as e:  # pragma: no cover
                detail = str(e)[:160]
                p.prework.append({"step": "story_integrity_audit", "status": "skip", "detail": detail})

        risk_script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "shot_risk_audit.py")
        if os.path.exists(risk_script):
            try:
                r = _run([sys.executable, risk_script, root, ep, "--json"])
                out = _parse_trailing_json(r.stdout)
                summary = out.get("summary") if isinstance(out, dict) else {}
                detail = ""
                if isinstance(summary, dict):
                    detail = f"max_score={summary.get('max_score', 0)} high_risk={summary.get('warn_or_higher', 0)}"
                if r.returncode != 0:
                    if not p.prework_block:
                        p.prework_block = "shot_risk_audit 发现必须先处理的高风险镜头；先回 n2d-script 拆镜/补锚帧/降级同框。"
                    p.prework.append({"step": "shot_risk_audit", "status": "block", "detail": _finding_detail(r.stdout, r.stderr)})
                else:
                    status = "warn" if isinstance(summary, dict) and int(summary.get("warn_or_higher") or 0) else "pass"
                    p.prework.append({"step": "shot_risk_audit", "status": status, "detail": detail})
            except Exception as e:  # pragma: no cover
                detail = str(e)[:160]
                p.prework.append({"step": "shot_risk_audit", "status": "skip", "detail": detail})

        entity_script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "entity_schedule_audit.py")
        if os.path.exists(entity_script):
            try:
                r = _run([sys.executable, entity_script, root, ep, "--json"])
                out = _parse_trailing_json(r.stdout)
                stats = out.get("stats") if isinstance(out, dict) else {}
                findings = out.get("findings") if isinstance(out, dict) else []
                warn_n = sum(1 for f in findings if isinstance(f, dict) and f.get("severity") in {"warn", "must", "block"})
                detail = ""
                if isinstance(stats, dict):
                    detail = f"coverage={stats.get('coverage')} missing={stats.get('missing_schedule_units', 0)}"
                p.prework.append({"step": "entity_schedule_audit",
                                  "status": "warn" if warn_n else "pass",
                                  "detail": detail})
            except Exception as e:  # pragma: no cover
                detail = str(e)[:160]
                p.prework.append({"step": "entity_schedule_audit", "status": "skip", "detail": detail})

        _run_production_breakdown_prework(p, root, ep)

        _run_report_only_prework(p, [
            (
                "series_bible",
                os.path.join(SKILLS_DIR, "n2d-script", "scripts", "series_bible.py"),
                [root, "--write", "--json"],
            ),
            (
                "performance_signature",
                os.path.join(SKILLS_DIR, "n2d-script", "scripts", "performance_signature.py"),
                [root, "--write", "--json"],
            ),
            (
                "episode_probe_matrix",
                os.path.join(SKILLS_DIR, "n2d-script", "scripts", "episode_probe_matrix.py"),
                [root, ep, "--write", "--json"],
            ),
            (
                "shot_split_decision",
                os.path.join(SKILLS_DIR, "n2d-script", "scripts", "shot_split_decision.py"),
                [root, ep, "--write", "--json"],
            ),
            (
                "audience_emotion_account",
                os.path.join(SKILLS_DIR, "n2d-script", "scripts", "audience_emotion_account.py"),
                [root, ep, "--write", "--json"],
            ),
            (
                "story_quality_pack",
                os.path.join(SKILLS_DIR, "n2d-script", "scripts", "story_quality_pack.py"),
                [root, ep, "--write", "--json"],
            ),
            # 剧情/分镜质量启发式（2026-06-24·report-only·warn 透出不阻断）：
            (
                "causal_graph",            # A1 因果链：天降/为反转而反转候选 + 因果覆盖率 + A6 降智糖精
                os.path.join(SKILLS_DIR, "n2d-script", "scripts", "causal_graph.py"),
                [root, ep, "--strict", "--json"],
            ),
            (
                "scene_turn_audit",        # A2 场必转：价值极性翻转 + 憋→放 + 转折点位置
                os.path.join(SKILLS_DIR, "n2d-script", "scripts", "scene_turn_audit.py"),
                [root, ep, "--strict", "--json"],
            ),
            (
                "subtext_audit",           # A5 潜台词/去AI味：直白情绪/动机/exposition
                os.path.join(SKILLS_DIR, "n2d-script", "scripts", "subtext_audit.py"),
                [root, ep, "--strict", "--json"],
            ),
            (
                "shot_grammar_audit",      # B1 景别进程 + B2 转场单调/J-L cut
                os.path.join(SKILLS_DIR, "n2d-script", "scripts", "shot_grammar_audit.py"),
                [root, ep, "--strict", "--json"],
            ),
            (
                "character_arc_ledger",    # A3 人物弧光：want-vs-need + 挣来的转变（账本存在才报）
                os.path.join(SKILLS_DIR, "n2d-script", "scripts", "character_arc_ledger.py"),
                [root, "--check", "--strict", "--json"],
            ),
        ], cache=_prework_cache_obj)

        # 落盘本阶段缓存（audits + report-only 的 pass/warn 结果），供下次 run next 复用。
        if _prework_cache_obj is not None:
            _prework_cache_obj.save()

        for step, script_name, args in (
            ("spectacle_plan", "spectacle_plan.py", [root, ep, "--write", "--json"]),
            ("spectacle_sequence_plan", "spectacle_sequence_plan.py", [root, ep, "--write", "--json"]),
            ("scene_layer_pack", "scene_layer_pack.py", [root, ep, "--write"]),
            ("spectacle_probe_pack", "spectacle_probe_pack.py", [root, ep, "--write", "--json"]),
        ):
            script_path = os.path.join(SKILLS_DIR, "n2d-script", "scripts", script_name)
            if not os.path.exists(script_path):
                continue
            try:
                r = _run([sys.executable, script_path, *args])
                if r.returncode == 0:
                    p.prework.append({"step": step, "status": "pass"})
                else:
                    detail = _finding_detail(r.stdout, r.stderr)
                    if not p.prework_block:
                        p.prework_block = f"{step} 无法生成；先修复 storyboard 或脚本错误后再继续。"
                    p.prework.append({"step": step, "status": "block", "detail": detail})
            except Exception as e:  # pragma: no cover
                detail = str(e)[:160]
                if not p.prework_block:
                    p.prework_block = f"{step} 无法运行：{detail}"
                p.prework.append({"step": step, "status": "block", "detail": detail})

        # 奇观连续性留痕（best-effort·绝不阻断）：序列总账生成后把状态写回 _进度.md 可见列。
        # ✅=有奇观镜且被序列覆盖；—=本集无奇观镜(N/A)。失败只记 skip，不影响 prework_block。
        try:
            seq_path = os.path.join(root, "生产数据", f"spectacle_sequence_plan_{ep}.json")
            if os.path.isfile(seq_path):
                with open(seq_path, encoding="utf-8") as fh:
                    seq = json.load(fh)
                summary = seq.get("summary") if isinstance(seq, dict) else {}
                n_clips = int(summary.get("spectacle_clips") or 0) if isinstance(summary, dict) else 0
                covered = bool(seq.get("sequences")) if isinstance(seq, dict) else False
                mark = "✅" if (n_clips > 0 and covered) else "—"
                prog = os.path.join(SKILLS_DIR, "n2d", "progress.py")
                if os.path.exists(prog):
                    _run([sys.executable, prog, "ensure-col", root, "奇观连续性", "—"])
                    _run([sys.executable, prog, "set", root, ep, "奇观连续性", mark])
                    p.prework.append({"step": "spectacle_continuity_mark", "status": "ok", "detail": mark})
        except Exception as e:  # pragma: no cover - 留痕失败不影响主流程
            p.prework.append({"step": "spectacle_continuity_mark", "status": "skip", "detail": str(e)[:120]})

    if stage_key == "image" and ep:
        _run_production_breakdown_prework(p, root, ep)
        _run_preventive_contract_prework(p, root, ep, "image")

    # model-router：出视频前置（写理论路由表），幂等
    if stage_key in ROUTER_STAGES:
        script = os.path.join(SKILLS_DIR, "n2d-model-router", "scripts", "router.py")
        if os.path.exists(script):
            try:
                r = _run([sys.executable, script, root, ep, "--write"])
                if r.returncode == 0:
                    p.prework.append({"step": "model_router", "status": "ok"})
                else:
                    detail = (r.stderr or r.stdout or "").strip()[:160]
                    p.prework_block = f"model_router 退出码 {r.returncode}{f'：{detail}' if detail else ''}"
                    p.prework.append({"step": "model_router", "status": "block", "detail": detail})
            except Exception as e:  # pragma: no cover
                detail = str(e)[:160]
                p.prework_block = f"model_router 无法运行：{detail}"
                p.prework.append({"step": "model_router", "status": "block", "detail": detail})
        mouth_script = os.path.join(SKILLS_DIR, "n2d-model-router", "scripts", "mouth_detect.py")
        if os.path.exists(mouth_script):
            try:
                r = _run([sys.executable, mouth_script, root, ep, "--write", "--json"])
                p.prework.append({
                    "step": "mouth_visible_audit",
                    "status": "pass" if r.returncode == 0 else "warn",
                    "detail": _finding_detail(r.stdout, r.stderr),
                })
            except Exception as e:  # pragma: no cover
                p.prework.append({"step": "mouth_visible_audit", "status": "skip", "detail": str(e)[:160]})
        spectacle_script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "spectacle_plan.py")
        if os.path.exists(spectacle_script):
            try:
                r = _run([sys.executable, spectacle_script, root, ep, "--write", "--write-manifests", "--json"])
                if r.returncode == 0:
                    p.prework.append({"step": "spectacle_motion_plan", "status": "pass"})
                else:
                    detail = _finding_detail(r.stdout, r.stderr)
                    if not p.prework_block:
                        p.prework_block = "spectacle_plan Motion Control 骨架生成失败；先修复 storyboard/控制契约。"
                    p.prework.append({"step": "spectacle_motion_plan", "status": "block", "detail": detail})
            except Exception as e:  # pragma: no cover
                detail = str(e)[:160]
                if not p.prework_block:
                    p.prework_block = f"spectacle_motion_plan 无法运行：{detail}"
                p.prework.append({"step": "spectacle_motion_plan", "status": "block", "detail": detail})

        sequence_script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "spectacle_sequence_plan.py")
        if os.path.exists(sequence_script):
            try:
                r = _run([sys.executable, sequence_script, root, ep, "--write", "--json"])
                if r.returncode == 0:
                    p.prework.append({"step": "spectacle_sequence_plan", "status": "pass"})
                else:
                    detail = _finding_detail(r.stdout, r.stderr)
                    if not p.prework_block:
                        p.prework_block = "spectacle_sequence_plan 生成失败；先修复 storyboard 的高动态/大场景连续性契约。"
                    p.prework.append({"step": "spectacle_sequence_plan", "status": "block", "detail": detail})
            except Exception as e:  # pragma: no cover
                detail = str(e)[:160]
                if not p.prework_block:
                    p.prework_block = f"spectacle_sequence_plan 无法运行：{detail}"
                p.prework.append({"step": "spectacle_sequence_plan", "status": "block", "detail": detail})

        controller_script = os.path.join(SKILLS_DIR, "n2d-model-router", "scripts", "trajectory_controller_plan.py")
        if os.path.exists(controller_script):
            try:
                r = _run([sys.executable, controller_script, root, ep, "--write"])
                if r.returncode == 0:
                    p.prework.append({"step": "trajectory_controller_plan", "status": "pass"})
                else:
                    p.prework.append({"step": "trajectory_controller_plan", "status": "warn", "detail": _finding_detail(r.stdout, r.stderr)})
            except Exception as e:  # pragma: no cover
                p.prework.append({"step": "trajectory_controller_plan", "status": "skip", "detail": str(e)[:160]})

        _run_report_only_prework(p, [
            (
                "video_production_pack",
                os.path.join(SKILLS_DIR, "n2d-video", "scripts", "video_production_pack.py"),
                [root, ep, "--write", "--json"],
            ),
        ])
        _run_preventive_contract_prework(p, root, ep, stage_key)

    if stage_key in {"video", "compose"} and ep:
        if stage_key == "compose":
            _run_preventive_contract_prework(p, root, ep, "compose")
            mouth_script = os.path.join(SKILLS_DIR, "n2d-model-router", "scripts", "mouth_detect.py")
            if os.path.exists(mouth_script):
                try:
                    r = _run([sys.executable, mouth_script, root, ep, "--write", "--json"])
                    p.prework.append({
                        "step": "mouth_visible_audit",
                        "status": "pass" if r.returncode == 0 else "warn",
                        "detail": _finding_detail(r.stdout, r.stderr),
                    })
                except Exception as e:  # pragma: no cover
                    p.prework.append({"step": "mouth_visible_audit", "status": "skip", "detail": str(e)[:160]})
        materialize_script = os.path.join(SKILLS_DIR, "n2d-video", "scripts", "materialize_shared_clips.py")
        if os.path.exists(materialize_script):
            try:
                r = _run([sys.executable, materialize_script, root, ep, "--json"])
                p.prework.append({
                    "step": "shared_video_materialize",
                    "status": "pass" if r.returncode == 0 else "block",
                    "detail": _finding_detail(r.stdout, r.stderr),
                })
                if r.returncode != 0 and not p.prework_block:
                    p.prework_block = "共享视频物化失败；先修复 storyboard 的 shared_video/source 或共享视频文件。"
            except Exception as e:  # pragma: no cover
                p.prework.append({"step": "shared_video_materialize", "status": "skip", "detail": str(e)[:160]})

    if stage_key == "compose" and ep:
        script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "action_edit_cues.py")
        if os.path.exists(script):
            try:
                r = _run([sys.executable, script, root, ep, "--write", "--json"])
                if r.returncode == 0:
                    p.prework.append({"step": "action_edit_cues", "status": "pass"})
                else:
                    detail = _finding_detail(r.stdout, r.stderr)
                    if not p.prework_block:
                        p.prework_block = "action_edit_cues 生成失败；先修复 storyboard 后再合成。"
                    p.prework.append({"step": "action_edit_cues", "status": "block", "detail": detail})
            except Exception as e:  # pragma: no cover
                detail = str(e)[:160]
                if not p.prework_block:
                    p.prework_block = f"action_edit_cues 无法运行：{detail}"
                p.prework.append({"step": "action_edit_cues", "status": "block", "detail": detail})

    if stage_key == "review" and ep:
        _run_review_evidence_pre_gate(root, ep, p)
        _run_report_only_prework(p, [
            (
                "production_learning_pack",
                os.path.join(SKILLS_DIR, "n2d-review", "scripts", "production_learning_pack.py"),
                [root, ep, "--write", "--json"],
            ),
        ])

    if stage_key in PRODUCTION_LOCK_STAGES and ep:
        _run_production_locks_prework(p, root, ep, stage_key)

    # identity：把 identity_registry 展开成 adapter matrix，供后续 gate 按执行后端核验。
    # --skip-face 只刷新矩阵/漂移报告骨架，避免 run.py next 在日常路由时触发重视觉机检。
    if stage_key in IDENTITY_REFRESH_STAGES:
        script = os.path.join(SKILLS_DIR, "n2d-identity", "scripts", "identity.py")
        if os.path.exists(script):
            try:
                r = _run([sys.executable, script, root, "--write", "--skip-face"])
                if r.returncode == 0:
                    p.prework.append({"step": "identity", "status": "ok"})
                else:
                    detail = (r.stderr or r.stdout or "").strip()[:160]
                    planned_gap, planned_detail = _identity_exit_is_planned_asset_gap(root)
                    if planned_gap and _gate_stage_for_frontier(root, ep, stage_key, spec):
                        p.prework.append({
                            "step": "identity",
                            "status": "warn",
                            "detail": (planned_detail or detail) + "；计划中的共享参考缺口交由 stage gate 定位/阻断。",
                        })
                    else:
                        p.prework_block = f"identity adapter matrix 刷新退出码 {r.returncode}{f'：{detail}' if detail else ''}"
                        p.prework.append({"step": "identity", "status": "block", "detail": detail})
            except Exception as e:  # pragma: no cover
                detail = str(e)[:160]
                p.prework_block = f"identity adapter matrix 无法刷新：{detail}"
                p.prework.append({"step": "identity", "status": "block", "detail": detail})

    # image_qc：出图落档后的机检报告必须 full 且无 hard block，才允许进入视频/合成链路。
    if stage_key in IMAGE_QC_STRICT_STAGES and ep:
        issue = _image_qc_gate_issue(root, ep)
        if issue:
            p.image_qc_block = issue
            p.prework.append({"step": "image_qc", "status": "block", "detail": issue[:160]})
        else:
            p.prework.append({"step": "image_qc", "status": "pass"})

    if stage_key == "image" and ep:
        _run_report_only_prework(p, [
            (
                "reference_plan",
                os.path.join(SKILLS_DIR, "n2d-image", "scripts", "reference_planner.py"),
                [root, ep],
            ),
            (
                "no_cost_reference_pack",
                os.path.join(SKILLS_DIR, "n2d-image", "scripts", "reference_pack.py"),
                [root, ep, "--write", "--json"],
            ),
            (
                "scene_reference_plan",
                os.path.join(SKILLS_DIR, "n2d-image", "scripts", "scene_reference_planner.py"),
                [root, ep, "--write", "--json"],
            ),
            (
                "keyshot_candidates",
                os.path.join(SKILLS_DIR, "n2d-image", "scripts", "keyshot_candidates.py"),
                [root, ep, "--write", "--json"],
            ),
            (
                "no_cost_image_pack",
                os.path.join(SKILLS_DIR, "n2d-image", "scripts", "no_cost_image_pack.py"),
                [root, ep, "--write", "--json"],
            ),
        ])

    # gate：有 gate_stage 的阶段先过 dashboard gate（退出码 1=block）
    gate_stage = _gate_stage_for_frontier(root, ep, stage_key, spec)
    if gate_stage:
        script = os.path.join(SKILLS_DIR, "n2d-dashboard", "scripts", "dashboard.py")
        if os.path.exists(script):
            try:
                r = _run([sys.executable, script, "gate", root, ep, "--stage", gate_stage])
                out = _parse_trailing_json(r.stdout)
                blocked = r.returncode != 0
                p.gate = {"stage": gate_stage, "blocked": blocked,
                          "findings_path": out.get("findings_path"),
                          "return_to_stage": None, "affected_artifacts": [], "rerun_scope": None}
                if blocked and out.get("findings_path") and os.path.exists(out["findings_path"]):
                    _enrich_gate(p.gate, out["findings_path"])
                p.prework.append({"step": "gate", "stage": gate_stage,
                                  "status": "block" if blocked else "pass"})
            except Exception as e:  # pragma: no cover
                detail = str(e)[:160]
                p.gate = {"stage": gate_stage, "blocked": True,
                          "findings_path": None, "return_to_stage": stage_key,
                          "affected_artifacts": [], "rerun_scope": detail}
                p.prework.append({"step": "gate", "stage": gate_stage, "status": "block", "detail": detail})
        else:
            # 缺 dashboard.py = 一致性闸门跑不起来。受闸阶段绝不能因工具缺失静默放行
            # （「缺脚本=skip=pass」正是声明≠现实的逃逸口）。fail-closed：缺脚本即 block，
            # 并指明补什么。这是损坏的安装，不是 C4 那种可优雅降级的可选重型依赖。
            detail = "缺 skills/n2d-dashboard/scripts/dashboard.py，一致性闸门无法运行（fail-closed，先修复安装再继续）"
            p.gate = {"stage": gate_stage, "blocked": True, "findings_path": None,
                      "return_to_stage": stage_key, "affected_artifacts": [], "rerun_scope": detail}
            p.prework.append({"step": "gate", "stage": gate_stage, "status": "block", "detail": detail})

    # compliance：花钱档前置检查
    if stage_key in PAID_STAGES:
        script = os.path.join(SKILLS_DIR, "n2d-compliance", "scripts", "compliance.py")
        if os.path.exists(script):
            try:
                r = _run([sys.executable, script, root, ep, "--check"])
                p.compliance_gap = (r.returncode != 0)
                p.prework.append({"step": "compliance", "status": "gap" if p.compliance_gap else "ok"})
            except Exception as e:  # pragma: no cover
                detail = str(e)[:160]
                p.compliance_gap = True
                p.prework.append({"step": "compliance", "status": "gap", "detail": detail})
        else:
            # 合规是不可协商前置（设计律 D1）。compliance.py 缺失=无法核验版权/授权/审核，
            # 付费档绝不静默放行 → fail-closed 记 gap（同样是损坏安装，非可降级依赖）。
            p.compliance_gap = True
            p.prework.append({"step": "compliance", "status": "gap",
                              "detail": "缺 skills/n2d-compliance/scripts/compliance.py，合规前置无法核验（fail-closed）"})

    if stage_key == "review" and ep and not (p.gate and p.gate.get("blocked")) and not p.prework_block:
        _run_review_acceptance_outputs(root, ep, p)

    # 首跑必给：仅在 script_stage1 前沿，挑出尚未显式记录的选择点
    if stage_key == "script_stage1":
        p.pending_choices = script_stage1_missing_choices

    return p


def _enrich_gate(gate: Dict[str, Any], findings_path: str) -> None:
    """从 gate_findings 文件取首条 finding 的回退字段（best-effort）。"""
    try:
        data = json.load(open(findings_path, encoding="utf-8"))
    except Exception:
        return
    findings = data.get("findings") if isinstance(data, dict) else None
    first = findings[0] if isinstance(findings, list) and findings else {}
    if isinstance(first, dict):
        gate["return_to_stage"] = first.get("return_to_stage") or gate.get("return_to_stage")
        gate["affected_artifacts"] = first.get("affected_artifacts") or gate.get("affected_artifacts")
        gate["rerun_scope"] = first.get("rerun_scope") or gate.get("rerun_scope")


# ── 顶层：一次步进（v1：每个路由阶段都是 stop-point，--auto 预留给将来确定性阶段）──
def next_action(root: str, ep: Optional[str] = None, auto: bool = False, preview: bool = False) -> Dict[str, Any]:
    while True:
        try:
            route = resolve_frontier(root, ep)
        except FileNotFoundError:
            return _missing_progress_action(root, ep)
        if route is None:
            delivery_hint = (
                "合成阶段已启用，当前没有未完成的合成/验收前沿；若 release/readiness 通过，可视为 master_delivery_complete。"
                if compose_stage_enabled(root)
                else "默认主流程到「视频」列完成只表示 clip_delivery_complete（镜头交付完成），不是可投放母版；如需 master_delivery_complete，需要把 `_设置.md` 的「合成阶段」设为「启用」并运行 n2d-compose / review / release readiness。"
            )
            action_card = {
                "headline": "该作品/该集当前阶段已完成，无下一步",
                "to_user": f"{delivery_hint} 若后续源文或 skill 更新，再按 update/source 检查生成最小重制计划。",
            }
            if compose_stage_enabled(root):
                action_card["post_qc_bundle"] = _post_qc_bundle(root, ep or "<集>", "post_compose_review")
            return {"frontier": None, "prework": [], "stop_reason": "done",
                    "action_card": action_card,
                    "gate": None, "auto_continue": False}
        stage_key = stage_key_of(route)
        if stage_key is None:
            return {"frontier": {"ep": route.get("ep"), "label": route.get("label")},
                    "prework": [], "stop_reason": "unknown_stage",
                    "action_card": {"headline": f"无法识别阶段：{route}"},
                    "gate": None, "auto_continue": False}
        probes = gather_probes(root, route, stage_key, preview=preview)
        na = decide(root, route, stage_key, probes)
        if auto and na["auto_continue"]:
            continue  # 仅当出现纯确定性阶段时才真正跨阶段推进
        return na


def entry_checks(root: str, ep: Optional[str] = None, stage_key: Optional[str] = None, preview: bool = False) -> List[Dict[str, Any]]:
    """Dispatcher-level entry checks: source freshness + skill update plan.

    `next_action()` consumes explicit drift/rebuild signals from these checks, so
    batch and single-episode runs share the same preflight.
    """
    checks: List[Dict[str, Any]] = []
    source = os.path.join(SKILLS_DIR, "n2d", "source_check.py")
    if os.path.exists(source):
        try:
            r = _run([sys.executable, source, root, "--quiet"])
            status = "ok" if r.returncode == 0 else "warn"
            detail = (r.stdout or r.stderr or "").strip().splitlines()[-1:] or [""]
            if "DRIFT=" in (detail[0] or ""):
                raw = detail[0].split("DRIFT=", 1)[1]
                try:
                    obj = json.loads(raw)
                    status = obj.get("status") or status
                except Exception:
                    pass
            checks.append({"step": "source_check", "status": status, "detail": detail[0]})
        except Exception as exc:  # pragma: no cover
            checks.append({"step": "source_check", "status": "skip", "detail": str(exc)[:160]})

    target_ep = ep
    if not target_ep:
        route = resolve_frontier(root)
        target_ep = route.get("ep") if route else None
    update = os.path.join(SKILLS_DIR, "n2d-update", "scripts", "update_plan.py")
    if target_ep and os.path.exists(update) and not preview:
        try:
            r = _run([sys.executable, update, "check", root, target_ep, "--write-plan", "--json"])
            plan = _parse_trailing_json(r.stdout)
            status = "ok" if r.returncode == 0 else "warn"
            if isinstance(plan, dict) and plan.get("rebuild_needed"):
                status = "rebuild_needed"
            elif isinstance(plan, dict) and (plan.get("source_drift") or {}).get("status") == "drift":
                status = "source_drift"
            checks.append({
                "step": "update_plan",
                "episode": target_ep,
                "stage_key": stage_key,
                "status": status,
                "detail": (r.stdout or r.stderr or "").strip().splitlines()[-1] if (r.stdout or r.stderr).strip() else "",
                "plan": plan,
            })
        except Exception as exc:  # pragma: no cover
            checks.append({"step": "update_plan", "episode": target_ep, "status": "skip", "detail": str(exc)[:160]})
    return checks


def enter_action(root: str, ep: Optional[str] = None, auto: bool = False, preview: bool = False) -> Dict[str, Any]:
    na = next_action(root, ep, auto=auto, preview=preview)
    if not na.get("entry_checks"):
        na["entry_checks"] = entry_checks(root, ep, preview=preview)
    return na


def pilot_action(root: str, ep: Optional[str] = None) -> Dict[str, Any]:
    """Return a first-episode pilot plan without triggering generation."""
    ep = ep or "第1集"
    if not str(ep).startswith("第"):
        ep = f"第{ep}集"
    risk_script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "shot_risk_audit.py")
    risk = {}
    prework: List[Dict[str, Any]] = []
    if os.path.exists(risk_script):
        try:
            r = _run([sys.executable, risk_script, root, ep, "--json"])
            risk = _parse_trailing_json(r.stdout)
            prework.append({"step": "shot_risk_audit", "status": "ok" if r.returncode == 0 else "block",
                            "detail": _finding_detail(r.stdout, r.stderr)})
        except Exception as exc:  # pragma: no cover
            prework.append({"step": "shot_risk_audit", "status": "skip", "detail": str(exc)[:160]})
    probe_script = os.path.join(SKILLS_DIR, "n2d-script", "scripts", "spectacle_probe_pack.py")
    if os.path.exists(probe_script):
        try:
            r = _run([sys.executable, probe_script, root, ep, "--write", "--json"])
            prework.append({"step": "spectacle_probe_pack", "status": "ok" if r.returncode == 0 else "block",
                            "detail": _finding_detail(r.stdout, r.stderr)})
        except Exception as exc:  # pragma: no cover
            prework.append({"step": "spectacle_probe_pack", "status": "skip", "detail": str(exc)[:160]})
    candidates = []
    if isinstance(risk, dict):
        for item in risk.get("pilot_candidates") or []:
            candidates.append({
                "clip": item.get("id"),
                "score": item.get("score"),
                "tags": item.get("tags") or [],
                "recommendations": item.get("recommendations") or [],
            })
    return {
        "frontier": {"ep": ep, "stage_key": "pilot", "label": "首集打样", "owner": "n2d"},
        "prework": prework,
        "stop_reason": "needs_payment_confirm",
        "action_card": {
            "headline": f"{ep} 首集打样计划：先验证代表 Clip，不全量放量",
            "to_user": "先用 2-3 个代表 Clip 验证画风、脸、口型、接缝和模型路由；通过后再批量推进。",
            "pilot_clips": candidates,
            "commands": [
                f"python3 skills/n2d/run.py next {root} {ep}",
                f"python3 skills/n2d-dashboard/scripts/dashboard.py gate {root} {ep} --stage image_prompt_preflight",
                f"python3 skills/n2d-script/scripts/shot_risk_audit.py {root} {ep}",
                f"python3 skills/n2d-script/scripts/spectacle_probe_pack.py {root} {ep} --write",
            ],
        },
        "gate": None,
        "auto_continue": False,
    }


# ── 输出 ──────────────────────────────────────────────────────────────────────
def render_human(na: Dict[str, Any]) -> str:
    lines = []
    for chk in na.get("entry_checks", []) or []:
        ep = f" [{chk.get('episode')}]" if chk.get("episode") else ""
        lines.append(f"入口检查 {chk.get('step')}{ep}: {chk.get('status')}" + (f" · {chk.get('detail')}" if chk.get("detail") else ""))
    f = na.get("frontier") or {}
    if f.get("ep"):
        lines.append(f"前沿：{f.get('ep')} · {f.get('label')}（{f.get('owner')}）")
    for pw in na.get("prework", []):
        detail = f" · {pw.get('detail')}" if pw.get("detail") else ""
        lines.append(f"  ✔ 前置 {pw.get('step')}: {pw.get('status')}" + (f" [{pw.get('stage')}]" if pw.get('stage') else "") + detail)
    card = na.get("action_card") or {}
    lines.append("")
    lines.append(f"⏸ 停因：{na.get('stop_reason')}")
    lines.append(f"   {card.get('headline','')}")
    if card.get("to_user"):
        lines.append(f"   {card['to_user']}")
    specialist = card.get("specialist") or {}
    if specialist:
        lines.append(f"   Specialist：{specialist.get('name')}（{specialist.get('scope')}）")
    context_pack = card.get("context_pack") or {}
    if context_pack:
        lines.append(f"   Context pack：{context_pack.get('relpath')}")
    creative_loop = card.get("creative_loop") or {}
    if creative_loop:
        lines.append(f"   Creative loop：{creative_loop.get('relpath')}")
    trace = na.get("trace") or {}
    if trace.get("trace_id"):
        lines.append(f"   Trace：{trace.get('trace_id')} span={trace.get('span_id')}")
    for m in card.get("menu", []) or []:
        opts = " / ".join(m.get("options", []) or []) or "(见选择点文档)"
        lines.append(f"   选择点【{m['choice_point']}】：{opts}（上次：{m.get('default_preselect') or '未记录'}）")
    if card.get("exact_command"):
        lines.append(f"   命令：{card['exact_command']}")
    for c in card.get("pilot_clips", []) or []:
        lines.append(f"   打样 Clip：{c.get('clip')} score={c.get('score')} tags={','.join(c.get('tags') or [])}")
        for rec in c.get("recommendations") or []:
            lines.append(f"     - {rec}")
    for command in card.get("commands", []) or []:
        lines.append(f"   命令：{command}")
    if card.get("writeback_after"):
        lines.append(f"   完成后回写：{card['writeback_after']}")
    bundle = card.get("post_qc_bundle") or {}
    if bundle:
        lines.append(f"   {bundle.get('headline', '审查包')}：")
        for command in bundle.get("commands", []) or []:
            lines.append(f"     - {command}")
    return "\n".join(lines)


def main(argv: List[str]) -> int:
    if not argv or argv[0] not in {"next", "enter", "pilot"}:
        print("用法: run.py next|enter|pilot <作品根> [第N集] [--json] [--auto] [--preview]")
        return 1
    command = argv[0]
    rest = argv[1:]
    as_json = "--json" in rest
    auto = "--auto" in rest
    preview = "--preview" in rest
    pos = [a for a in rest if not a.startswith("--")]
    if not pos:
        print("用法: run.py next|enter|pilot <作品根> [第N集] [--json] [--auto] [--preview]")
        return 1
    root = pos[0].rstrip("/")
    ep = pos[1] if len(pos) > 1 else None
    if command == "enter":
        na = enter_action(root, ep, auto=auto, preview=preview)
    elif command == "pilot":
        na = pilot_action(root, ep)
    else:
        na = next_action(root, ep, auto=auto, preview=preview)
    print(json.dumps(na, ensure_ascii=False, indent=2) if as_json else render_human(na))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
