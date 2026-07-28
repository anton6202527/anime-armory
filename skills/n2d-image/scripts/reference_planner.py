#!/usr/bin/env python3
"""出图前·能力路由的逐镜参考规划器（治跨集脸漂）。

为什么存在：跨集人物脸会漂，真因之一是——不同集的**服装/表情/景别/角度/光线**变化时，
只靠**单张定妆照做图生图不够准**。定妆照对 AI 只是个"固定板式"，身份判别细节不足，模型在新
条件下会重画整张脸，逐集累积成漂移。现状里逐镜"参考图块"是人工静态 prose 手写进
`出图/第N集/prompt/01_分镜出图.md`，**没有任何按镜头变化量去选参考、按后端能力路由策略**的逻辑；
治漂字段（`reference_group.expressions`、`angle_policy.requires_extra_reference`、后端能力表
`IMAGE_IDENTITY_PROFILES`）都已存在却悬空。

本规划器是 `face_drift_risk.py`（逐镜**诊断**）的**处方层**：逐镜逐角色算"变化量 delta"，再按
所选生图后端的真实能力（`image_identity_profile`）路由出"这一镜该喂哪些参考 + 要不要控制网 +
要不要升档"；多人同框再给 clip 级"身份槽位 + 执行策略"，写成**建议侧车**
`生产数据/reference_plan_第N集.{json,md}`，人审后落进 prompt；
gate 用它在 image_preflight 对账（`参考规划落实`）。**只建议不阻断**——零像素、零花钱、纯 stdlib。

复用（不重造）：face_drift_risk 的 is_closeup/has_strong_emotion/extreme_angle_tokens/clip_text/
load_clips/present_characters/project_default_backend；契约 image_identity_profile/image_lock_tier。

用法：python3 reference_planner.py <作品根> <第N集> [--json]
纯 stdlib；选择/路由是纯函数，有 pytest 覆盖（test_reference_planner.py）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_COMMON = os.path.abspath(os.path.join(_HERE, "..", "..", "n2d", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)

import face_drift_risk as fdr  # 同 skill·同目录复用诊断层纯函数

try:
    import codex_image_runner as cir  # 同 skill·复用 face_policy/承载脸锚单一真值源（不 fork）
except Exception:  # pragma: no cover - 异常布局兜底
    cir = None  # type: ignore

try:
    from n2d_contract import (
        character_library_tier_for_record,
        image_identity_profile,
        image_lock_tier,
    )
except Exception:  # pragma: no cover - 异常布局兜底
    character_library_tier_for_record = None  # type: ignore
    image_identity_profile = None  # type: ignore
    image_lock_tier = None  # type: ignore

# 镜头不是对视对象铁律·生成侧前移（治"防脸漂堆 frontal → 全员正对镜头摆拍"）：
# image_qc 侧只在交付/出图后**检测**直视镜头/frontal portrait 偏置（_lint_action_eyeline/
# _lint_camera_gaze_general），但参考规划是**生成侧**——这里在选参考时就把动作镜导向 ¾/侧脸主锚 +
# 写「不看镜头·视线锁戏内目标」prompt 指令，让偏置在花钱出图前就被掰正，而不是事后返工。
# 动作标记与 POV 豁免**与 image_qc/n2d_const 同源**（单一真值源·避免规划侧/QC 侧判定漂离）。
try:
    from n2d_const import is_camera_gaze_pov_exempt as _is_camera_gaze_pov_exempt, CAMERA_GAZE_NEGATIVES
except Exception:  # pragma: no cover - 异常布局兜底
    CAMERA_GAZE_NEGATIVES = (
        "looking at viewer", "直视镜头", "看镜头", "正对镜头摆拍", "肖像摆拍", "selfie",
    )

    def _is_camera_gaze_pov_exempt(text: str) -> bool:  # type: ignore
        return False

try:
    from image_qc import ACTION_EYELINE_MARKERS as _ACTION_EYELINE_MARKERS
except Exception:  # pragma: no cover - 异常布局兜底（与 image_qc.ACTION_EYELINE_MARKERS 同步）
    _ACTION_EYELINE_MARKERS = (
        "fight_exchange", "magic_burst", "chase", "battle", "combat", "action keyframe",
        "打斗", "武打", "拆招", "交锋", "对打", "攻防", "追逐", "爆冲", "斜劈", "劈", "斩",
        "刺", "挥", "命中", "受击", "撞击", "投掷", "施法", "法术", "斗法", "枪线", "戟刃",
        "spear", "slash", "strike", "impact", "attack", "burst",
    )

PLAN_KIND = "n2d_reference_plan"

# 核心长线角色判定（与 gate.check_image_ai_policy 同口径）：scope 含贯穿全篇/长线/主角标记。
_CORE_SCOPE_RE = re.compile(r"全篇|全程|长线|核心|主角|女主|男主|主反派")

# 参考角色 → 默认 image2image 强度建议（对齐现有 01_分镜出图.md 写法）。
STRENGTH = {
    "front": 0.8, "expression": 0.6, "side": 0.55,
    "rear_three_quarter": 0.55, "back": 0.5,
    "three_quarter": 0.65, "face_anchor": 0.7, "outfit": 0.5, "turnaround": 0.5, "scene_light": 0.45,
    # G2 跨集记忆锚（memory-sink）：最早定妆锚，最高优先（抗 EntityBench 复现间隔衰减）。
    "memory_anchor": 0.78,
}


# ── 纯函数（无依赖·可测） ──────────────────────────────────────────────────────

def is_action_eyeline_shot(text: str) -> bool:
    """本镜是否动作/打斗/强互动镜（与 image_qc._is_action_eyeline_shot 同源标记）。纯函数·可测。

    动作镜是「角色总看镜头/摆拍宣传照」最高发档——拆招本该把视线/姿态锁向对手·武器·命中点，
    一旦被防脸漂的 frontal 措辞带偏成正对镜头，力线与真实感全丢。规划侧据此把动作镜导向 ¾/侧脸主锚。"""
    t = str(text or "").lower()
    return any(str(m).lower() in t for m in _ACTION_EYELINE_MARKERS)


def variation_deltas(lens: str, text: str, angle_policy: Mapping[str, Any],
                     shot_size: str = "", expression_span: str = "") -> List[str]:
    """单角色单镜相对定妆照的变化量（不含多人同框，那个在 clip 级算）。纯函数·可测。

    兼容两套 storyboard schema：旧 schema 靠 lens/desc 文本启发；新 schema 直接吃结构化
    `continuity.shot_size`（含近景/特写/ECU…）与 `continuity.expression_span`（微/中/大）——
    结构化字段优先，启发兜底，二者取并集（宁多提示勿漏）。
    """
    d: List[str] = []
    if fdr.is_closeup(lens) or fdr.is_closeup(text) or fdr.is_closeup(shot_size):
        d.append("closeup")
    if fdr.has_strong_emotion(text) or str(expression_span).strip() in {"大"}:
        d.append("strong_emotion")
    for tok in fdr.extreme_angle_tokens(f"{lens} {shot_size}", text,
                                        (angle_policy or {}).get("risky") or []):
        d.append(f"extreme_angle:{tok}")
    # 动作镜视线/姿态锁（生成侧前移·治"全员正对镜头摆拍"）：命中动作标记且非显式 POV/破第四墙镜，
    # 标 action_eyeline_lock → 下游把 ¾/侧脸提为主身份锚 + 写「不看镜头」prompt 指令。
    if is_action_eyeline_shot(f"{lens} {text} {shot_size}") and not _is_camera_gaze_pov_exempt(text):
        d.append("action_eyeline_lock")
    return d


def _expr_paths(reference_group: Mapping[str, Any]) -> List[str]:
    """expressions 兼容两种登记：路径字符串 或 {emotion, path} 字典。"""
    out: List[str] = []
    for e in (reference_group or {}).get("expressions") or []:
        if isinstance(e, dict):
            p = str(e.get("path") or "").strip()
        else:
            p = str(e or "").strip()
        if p:
            out.append(p)
    return out


def _ref_item_path(item: object, *, require_ready: bool = False) -> str:
    """路径项兼容字符串或 {path,status}；require_ready 时 planned 不当成可用参考。"""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        if require_ready and str(item.get("status") or "").strip() != "ready":
            return ""
        return str(item.get("path") or "").strip()
    return ""


def _ref_list_paths(value: object, *, require_ready: bool = False) -> List[str]:
    if not isinstance(value, list):
        return []
    return [p for p in (_ref_item_path(item, require_ready=require_ready) for item in value) if p]


def _base_view_path(reference_atlas: Mapping[str, Any], key: str) -> str:
    base = reference_atlas.get("base_views") if isinstance(reference_atlas, Mapping) else {}
    if not isinstance(base, Mapping):
        return ""
    return _ref_item_path(base.get(key), require_ready=True)


def _face_anchor_paths(reference_group: Mapping[str, Any], reference_atlas: Mapping[str, Any]) -> List[str]:
    """基础脸锚：优先 face_anchor_refs；旧项目回退 expressions。"""
    out: List[str] = []
    out += _ref_list_paths((reference_group or {}).get("face_anchor_refs"), require_ready=False)
    out += _ref_list_paths((reference_atlas or {}).get("face_anchor_refs"), require_ready=True)
    seen = set()
    uniq = []
    for p in out:
        if p not in seen:
            uniq.append(p)
            seen.add(p)
    return uniq or _expr_paths(reference_group)


def _character_library_tier(char: Mapping[str, Any], atlas: Mapping[str, Any]) -> str:
    record = dict(char)
    if "library_tier" not in record and atlas.get("build_tier"):
        record["library_tier"] = atlas.get("build_tier")
    if character_library_tier_for_record is None:
        return "core_full"  # safe fallback: never reduce requirements on import damage
    return character_library_tier_for_record(record)


def _is_emotion_bank(expr_paths: Sequence[str]) -> bool:
    """是否是真·情绪表情库（≥2 张或含情绪命名），而非只有一张中性脸部特写。"""
    if len(expr_paths) >= 2:
        return True
    return any(re.search(r"表情|哭|怒|惊|喜|悲", os.path.basename(p)) for p in expr_paths)


def plan_character_in_clip(
    char: Mapping[str, Any],
    deltas: Sequence[str],
    multi: bool,
    profile: Mapping[str, Any],
    tier: str,
    scope_is_core: bool,
    memory_refs: Sequence[str] = (),
) -> Dict[str, Any]:
    """逐镜逐角色处方：推荐参考集 + 控制网 + 原生主体动作 + 升档 + 补拍缺口。纯函数·可测。

    char: {id, name, form, reference_group(dict), angle_policy(dict)}。
    tier: image_lock_tier → reference_group|multi_reference|face_embedding|native_unregistered|native_subject|lora。
    memory_refs: G2 跨集记忆锚路径（n2d-identity memory_anchor_plan 标 reinject 时），作为最高优先锚前置、
        参与后端参考预算封顶（抗 EntityBench 复现间隔衰减）。
    """
    rg = char.get("reference_group") or {}
    atlas = char.get("reference_atlas") or {}
    ap = char.get("angle_policy") or {}
    cid, form = str(char.get("id") or ""), str(char.get("form") or "")
    label = str(profile.get("label") or profile.get("canonical") or "当前后端")
    deltas = list(deltas)
    closeup = "closeup" in deltas
    strong_emotion = "strong_emotion" in deltas
    extreme = [d.split(":", 1)[1] for d in deltas if d.startswith("extreme_angle:")]
    library_tier = _character_library_tier(char, atlas)

    refs: List[Dict[str, Any]] = []
    missing: List[str] = []
    controlnet: List[str] = []

    def add_ref(role: str, key: Optional[str] = None) -> None:
        if role in {"front", "three_quarter", "side", "rear_three_quarter", "back"}:
            path = _base_view_path(atlas, role) or _ref_item_path(rg.get(key or role), require_ready=True)
        else:
            path = _ref_item_path(rg.get(key or role), require_ready=True)
        if path:
            refs.append({"role": role, "path": path, "strength_hint": STRENGTH.get(role, 0.5)})

    # 身份核心集：所有具名角色要正面 + 脸锚 + 服装体态锚；45° 由角色库档位和镜头需要决定。
    needs_three_quarter = (
        library_tier != "named_minimal"
        or closeup
        or strong_emotion
        or bool(extreme)
        or "action_eyeline_lock" in deltas
    )
    add_ref("front")
    if needs_three_quarter:
        add_ref("three_quarter")
    face_anchor_paths = _face_anchor_paths(rg, atlas)
    for p in face_anchor_paths[:1]:
        refs.append({"role": "face_anchor", "path": p, "strength_hint": STRENGTH["face_anchor"]})
    add_ref("outfit")
    # G2 跨集记忆锚（memory-sink）：长间隔再登场/晚集/已漂移角色，把最早定妆记忆锚前置为最高优先锚，
    # 抗 EntityBench 复现间隔衰减。前置=后端预算封顶时最先保留；去重已在 refs 里的同路径。
    memory_requested = list(dict.fromkeys(str(p or "").strip() for p in memory_refs if str(p or "").strip()))
    memory_injected: List[Dict[str, Any]] = []
    _have = {r["path"] for r in refs}
    for mp in memory_requested:
        if mp and mp not in _have:
            memory_injected.append({"role": "memory_anchor", "path": mp,
                                    "strength_hint": STRENGTH["memory_anchor"]})
            _have.add(mp)
    if memory_injected:
        refs = memory_injected + refs
    if needs_three_quarter and not _base_view_path(atlas, "three_quarter") and not _ref_item_path(rg.get("three_quarter"), require_ready=True):
        missing.append(f"45°/three_quarter 角度参考（当前角色库档位={library_tier}，本镜实际需要）")
    if not face_anchor_paths:
        missing.append("脸部特写基础锚（所有角色/形态强制 ready）")

    # 近景/大表情 → 表情库（治表情镜脸重画；与 image_qc no_expression_lib_ref 互补，前者 pre-gen 选）
    if closeup or strong_emotion:
        expr_paths = _expr_paths(rg)
        for p in expr_paths:
            refs.append({"role": "expression", "path": p, "strength_hint": STRENGTH["expression"]})
        if strong_emotion and not _is_emotion_bank(expr_paths):
            missing.append("情绪表情库（哭/怒/惊…起止表情；当前仅中性脸部特写或缺）")
        elif closeup and not expr_paths:
            missing.append("脸部特写主参考")

    # 极端角度 / requires_extra_reference → 补侧/背/全身参考（或改分镜避开）
    need_extra = set(ap.get("requires_extra_reference") or [])
    if "face_too_small" in extreme or "full_body_action" in need_extra:
        if rg.get("outfit") or rg.get("turnaround"):
            add_ref("turnaround")
        else:
            missing.append("全身/三视图参考（远景/全身动作镜）")
    if "side" in need_extra or any(t in extreme for t in ("extreme_top", "extreme_low")):
        if rg.get("side"):
            add_ref("side")
        else:
            missing.append("侧脸参考（极端角度/转头镜）")
    if "back" in need_extra:
        if rg.get("back"):
            add_ref("back")
        else:
            missing.append("背身参考（过肩/背身镜）")
    if "rear_three_quarter" in need_extra or "rear_3q" in need_extra:
        rear_path = _base_view_path(atlas, "rear_three_quarter") or _ref_item_path(
            rg.get("rear_three_quarter"), require_ready=True
        )
        if rear_path:
            add_ref("rear_three_quarter")
        else:
            missing.append("后3/4参考（后侧动作/过肩/回身镜）")

    # 多人同框 → 控制网锁站位（正交叠加：控制网锁站位、参考锁身份），仅多参考后端且非已注册主体时建议
    if multi and bool(profile.get("multi_reference")) and tier in {"reference_group", "multi_reference"}:
        controlnet = ["pose", "depth"]

    # 动作镜视线/姿态锁（生成侧·治"防脸漂堆 frontal → 拆招拍成正对镜头摆拍"）：
    # ¾/侧轮廓做主身份锚（避免 frontal portrait 偏置），front 降权为辅助身份核对；并开出
    # 「不看镜头·视线锁戏内目标·camera=observer」prompt 指令——这是 image_qc 动作视线 block 闸的
    # 生成侧前移（出图前掰正，而非交付后返工）。在预算封顶前重排，让 ¾ 锚优先保住。
    pose_gaze_directive: Optional[str] = None
    prompt_required: List[str] = []
    if "action_eyeline_lock" in deltas:
        for r in refs:
            if r.get("role") == "three_quarter":
                r["strength_hint"] = max(float(r.get("strength_hint") or 0), 0.78)
            elif r.get("role") == "front":
                r["strength_hint"] = min(float(r.get("strength_hint") or 0), 0.55)
        # 稳定排序：memory_anchor / three_quarter 提到 front 之前，保留同组相对次序。
        refs.sort(key=lambda r: 0 if r.get("role") in ("memory_anchor", "three_quarter") else 1)
        pose_gaze_directive = (
            "动作镜：脸可辨但不直视镜头——¾/侧/背侧轮廓，视线锁戏内目标（对手/武器来路/命中点），"
            "camera=observer 而非 opponent POV；负面词注入「"
            + "、".join(CAMERA_GAZE_NEGATIVES[:6]) + "…」。"
            "若本镜确为 opponent POV/破第四墙/对观众压迫特写，请在分镜显式标 POV 豁免。"
        )
        prompt_required.append("动作镜视线锁定指令（不看镜头/¾侧脸/视线锁对手或命中点）")
        if not any(r.get("role") == "three_quarter" for r in refs):
            missing.append("45°/¾ 侧脸参考（动作镜主身份锚·避免 frontal 摆拍偏置）")

    # 按后端能力封顶参考张数；预算溢出要显式写进 plan，不能静默吞参考。
    requested_ref_count = len(refs)
    dropped_refs: List[Dict[str, Any]] = []
    max_refs = profile.get("max_reference_images")
    if isinstance(max_refs, int) and max_refs > 0 and len(refs) > max_refs:
        dropped_refs = refs[max_refs:]
        refs = refs[:max_refs]
    selected_paths = {str(row.get("path") or "") for row in refs}
    memory_consumed = [path for path in memory_requested if path in selected_paths]
    memory_dropped = [path for path in memory_requested if path not in selected_paths]
    if memory_requested and not memory_consumed:
        missing.append("跨集记忆锚未进入本镜实际参考包；不得只在侧车声称已重注入")
    elif memory_dropped:
        missing.append(
            "跨集记忆锚未全部进入实际参考包（被预算丢弃 "
            + "、".join(memory_dropped)
            + "）；重选参考或拆镜"
        )
    reference_budget = {
        "limit": max_refs if isinstance(max_refs, int) and max_refs > 0 else None,
        "requested": requested_ref_count,
        "selected": len(refs),
        "dropped": len(dropped_refs),
    }
    if dropped_refs:
        dropped_roles = "、".join(str(r.get("role") or "?") for r in dropped_refs)
        missing.append(f"参考预算溢出（后端上限 {max_refs} 张，已丢弃 {dropped_roles}）；请拆镜/升档/重选参考包")

    # 原生主体动作（治"板式"根因：注册时喂多样集而非单 sheet）
    native_action: Optional[str] = None
    if tier == "native_unregistered":
        min_div = profile.get("recommended_diverse_reference_min") or 8
        extra = "；Kling 优先 Custom Model 吃多帧/视频拿最丰富身份" if profile.get("ingests_video") else ""
        native_action = (
            f"先在 {label} 注册原生主体（喂 ≥{min_div} 张**多样参考**：多角度+多表情+多光，"
            f"而非单张定妆 sheet），再按 ID/handle 跨镜引用{extra}"
        )
    elif tier == "native_subject":
        native_action = f"按 {label} 已注册主体 ID/handle 引用 + 上面参考做双保险"

    # 升档建议：弱后端 × 核心长线角 × 大变化镜
    escalation: Optional[str] = None
    big_delta = closeup or strong_emotion or bool(extreme) or multi
    if tier in {"reference_group", "multi_reference"} and scope_is_core and big_delta:
        escalation = (
            f"弱后端×核心长线角×大变化镜：建议升档——注册原生主体(Seedream/可灵/Sora)；仍压不住则 "
            f"`python3 skills/n2d-lora/scripts/lora.py init <作品根> --character-id {cid} --form '{form}'`"
        )

    # P2-7 窄增量：把后端已知能力（multi_reference / ingests_video）显式翻成「这一镜怎么喂参考」处方。
    # 2026 SOTA 是**分离的带标签多参考**（Seedance @Image1.. / Seedream Universal Reference / 可灵主体库），
    # 而非把多张定妆照拼成一张参考表 sheet（拼图损分辨率与可寻址性）；支持视频参考的后端（Kling Elements/
    # Custom Model）对身份信息量最大的镜（大表情/近景/原生主体注册）可喂定妆**视频/多帧**胜单张静帧。
    multi_cap = bool(profile.get("multi_reference"))
    video_cap = bool(profile.get("ingests_video"))
    ref_count = len(refs)
    if multi_cap and ref_count > 1:
        feed_mode = "tagged_multi_image"
        feed_guidance = (
            f"{label} 支持多参考：把这 {ref_count} 张作为**分离的带标签参考**喂（每张独立 @Image1/@Image2… "
            "各自语义角色），不要拼成一张参考表 sheet——拼图损分辨率/可寻址性，2026 SOTA 是分图分标。")
        tagged_inputs = [f"@Image{i + 1}:{r.get('role')}" for i, r in enumerate(refs)]
    elif ref_count > 1:
        feed_mode = "sequential_single_reference"
        feed_guidance = (
            f"{label} 不支持多图参考：以最高优先锚为主图做图生图，其余角度/表情参考转写进 prompt 描述或分步参考。")
        tagged_inputs = []
    else:
        feed_mode = "single_reference"
        feed_guidance = ""
        tagged_inputs = []
    video_hint = ""
    if video_cap and (closeup or strong_emotion or tier in {"native_unregistered", "native_subject"}):
        video_hint = (
            f"{label} 可吃视频参考：身份信息量最大化可喂该角色定妆**视频/多帧**（读 3D 结构 + 表情动态，"
            "胜单张静帧），尤其大表情/近景与原生主体注册时。")
    reference_feed = {
        "mode": feed_mode,
        "guidance": feed_guidance,
        "tagged_inputs": tagged_inputs,
        "video_reference_supported": video_cap,
        "video_reference_hint": video_hint,
    }

    needs_action = bool(missing or escalation or tier == "native_unregistered")
    return {
        "char_id": cid,
        "name": char.get("name"),
        "form": form,
        "tier": tier,
        "library_tier": library_tier,
        "variation_delta": deltas + (["multi_character"] if multi else []),
        "recommended_references": refs,
        "reference_budget": reference_budget,
        "dropped_references": dropped_refs,
        "controlnet": controlnet,
        "reference_feed": reference_feed,
        "missing_references": missing,
        "native_subject_action": native_action,
        "escalation": escalation,
        "needs_action": needs_action,
        "memory_anchor_reinjected": bool(memory_consumed),
        "memory_anchor_refs_requested": memory_requested,
        "memory_anchor_refs_consumed": memory_consumed,
        "memory_anchor_refs_dropped": memory_dropped,
        "pose_gaze_directive": pose_gaze_directive,
        "prompt_required": prompt_required,
    }


def _slot_name(index: int) -> str:
    names = ("LEFT_SLOT", "RIGHT_SLOT", "FOREGROUND_SLOT", "BACKGROUND_SLOT")
    return names[index] if index < len(names) else f"EXTRA_SLOT_{index + 1}"


# 锚点去重：把发色/服装主色归一到颜色桶，同框同桶=高串脸风险（模型易把两张近似的脸平均掉）。
_COLOR_BUCKETS: Sequence[tuple] = (
    ("红", ("红", "赤", "朱", "绛", "丹", "胭脂", "猩红", "酒红")),
    ("白", ("白", "素", "皓", "雪", "月白", "缟")),
    ("黑", ("黑", "玄", "墨", "乌", "缁", "黛")),
    ("蓝", ("蓝", "青", "碧", "靛", "藏青", "天青")),
    ("绿", ("绿", "翠", "葱", "苍", "竹")),
    ("紫", ("紫", "绛紫", "藕")),
    ("金", ("金", "黄", "鎏金", "杏", "明黄")),
    ("银灰", ("银", "灰", "缃", "霜")),
    ("粉", ("粉", "桃", "藕荷", "嫣")),
    ("褐", ("褐", "棕", "黄褐", "栗", "驼", "土")),
)


def _color_bucket(text: str) -> Optional[str]:
    """从 DNA 描述里取第一个命中的颜色桶；取不到返回 None（不参与撞色判定）。"""
    t = str(text or "")
    for name, kws in _COLOR_BUCKETS:
        if any(k in t for k in kws):
            return name
    return None


def _is_closeup(parsed: Mapping[str, Any]) -> bool:
    """近景/特写判定（多人近景=脸漂最高发档，触发降景别/拆反打处方）。纯函数·可测。"""
    blob = " ".join(str(parsed.get(k) or "") for k in ("shot_size", "lens", "text"))
    if _has(blob, ("远景", "大全景", "全景", "群像", "wide", "long shot", "ELS", "LS")):
        return False
    return _has(blob, ("ECU", "BCU", "CU", "MCU", "近景", "特写", "面部", "脸部", "反应镜", "表情镜"))


def _has(text: str, kws: Sequence[str]) -> bool:
    low = str(text or "").lower()
    return any(k.lower() in low for k in kws)


_REVIEW_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "n2d-review" / "scripts"


def _load_face_consistency():
    """惰性加载 n2d-review/face_consistency（embedding）；缺 insightface/模块即返回 None，降级回颜色桶。"""
    d = str(_REVIEW_SCRIPTS_DIR)
    if d not in sys.path:
        sys.path.insert(0, d)
    try:
        return __import__("face_consistency")
    except Exception:
        return None


def _front_ref_abs(root: Path, form: Mapping[str, Any]) -> Optional[str]:
    """取一个 form 最适合做脸部身份比对的参考图绝对路径：优先脸部特写(face)，回退正面(front)。"""
    rg = form.get("reference_group") or {}
    for key in ("face", "front"):
        v = rg.get(key)
        if isinstance(v, str) and v:
            return str(Path(root) / v)
    return None


def compute_confusable_pairs(root: Path, ref_paths_by_id: Mapping[str, Optional[str]],
                             threshold: float = 0.6) -> Dict[str, Any]:
    """对多人镜涉及的角色，用 insightface 嵌入参考脸算两两余弦，≥threshold 标"易混对"。

    这是比颜色词更硬的串脸真信号：两张参考脸客观相似时，模型最容易把同框两人画成一张脸。
    insightface 缺席 / 参考图缺失 → available=False，调用方回退颜色桶。每角色只嵌入一次。
    阈值 0.6：风格化漫剧脸跨"不同角色"余弦常 0.3–0.5，同人 0.6–0.8，故 ≥0.6 视为不同角色却高度相似。"""
    fc = _load_face_consistency()
    if fc is None or not hasattr(fc, "_load_embedder"):
        return {"available": False, "pairs": set()}
    app = fc._load_embedder()
    if app is None:
        return {"available": False, "pairs": set()}
    embs: Dict[str, Any] = {}
    for cid, path in ref_paths_by_id.items():
        if path and os.path.exists(path):
            try:
                e = fc._embed(app, path)
            except Exception:
                e = None
            if e:
                embs[cid] = e
    ids = [c for c in ref_paths_by_id if c in embs]
    pairs: set = set()
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            try:
                if fc.cosine(embs[ids[i]], embs[ids[j]]) >= threshold:
                    pairs.add(frozenset((ids[i], ids[j])))
            except Exception:
                continue
    return {"available": True, "pairs": pairs}


def plan_distinct_anchors(dna_by_id: Mapping[str, Mapping[str, Any]],
                          unique_ids: Sequence[str],
                          confusable_pairs: Optional[Sequence[Any]] = None) -> Dict[str, Any]:
    """同框各角色的发色/服装主色桶 + 撞色判定（颜色桶 + 可选参考脸 embedding 易混对）。纯函数·可测。

    撞色定义（取并集）：① 颜色桶——「服装主色桶相同」且「发色桶相同（或任一缺失）」；
    ② embedding——`confusable_pairs` 里的角色对（参考脸客观高度相似，比颜色更硬的真信号，优先级更高）。
    只要任一对命中就 collision=True，并给出"哪两个、撞在哪层"的处方。
    """
    confusable: set = set()
    for p in (confusable_pairs or []):
        try:
            a, b = tuple(p)
            confusable.add(frozenset((a, b)))
        except Exception:
            continue
    per_char: List[Dict[str, Any]] = []
    for cid in unique_ids:
        dna = dna_by_id.get(cid) or {}
        per_char.append({
            "char_id": cid,
            "hair_bucket": _color_bucket(dna.get("hair")),
            "outfit_bucket": _color_bucket(dna.get("outfit")),
            "anchor_phrase": str(dna.get("anchor_phrase") or ""),
        })
    collisions: List[Dict[str, Any]] = []
    for i in range(len(per_char)):
        for j in range(i + 1, len(per_char)):
            a, b = per_char[i], per_char[j]
            emb_conf = frozenset((a["char_id"], b["char_id"])) in confusable
            same_outfit = a["outfit_bucket"] and a["outfit_bucket"] == b["outfit_bucket"]
            same_hair = (a["hair_bucket"] == b["hair_bucket"]) or not a["hair_bucket"] or not b["hair_bucket"]
            color_collide = bool(same_outfit and same_hair)
            if not (emb_conf or color_collide):
                continue
            layers: List[str] = []
            if emb_conf:
                layers.append("参考脸 embedding 高度相似（模型最易混的硬信号）")
            if color_collide:
                layers.append(f"服装主色同为「{a['outfit_bucket']}」"
                              + (f"、发色同为「{a['hair_bucket']}」" if a["hair_bucket"] and a["hair_bucket"] == b["hair_bucket"] else "、发色未区分"))
            collisions.append({
                "pair": f"{a['char_id']}↔{b['char_id']}",
                "layer": "；".join(layers),
                "embedding_confusable": emb_conf,
            })
    collision = bool(collisions)
    if collision:
        guidance = (
            "同框角色易混=高串脸风险：给每个角色 5–7 个互斥锚点，至少在发色/发型/服装主色HEX/标志配饰上"
            "拉开区分；embedding 易混对（参考脸本就像）尤其要靠服装/配饰强分，必要时拆反打避免同框近景，"
            "并在逐镜 prompt 写 `区分锚点` 字段。"
        )
    else:
        guidance = "同框角色主色/参考脸已可区分；逐镜 prompt 仍写 `区分锚点` 字段把各自唯一发色/服装主色/配饰锚点列清楚。"
    return {"per_char": per_char, "collision": collision, "collisions": collisions,
            "embedding_checked": confusable_pairs is not None, "guidance": guidance}


def plan_multi_subject_strategy(
    char_plans: Sequence[Mapping[str, Any]],
    profile: Mapping[str, Any],
    dna_by_id: Optional[Mapping[str, Mapping[str, Any]]] = None,
    closeup: bool = False,
    confusable_pairs: Optional[Sequence[Any]] = None,
) -> Optional[Dict[str, Any]]:
    """多人同框 clip 级处方：身份槽位 + 后端能力路由 + prompt 必填字段。纯函数·可测。

    逐角色参考只能解决"每个人喂什么图"；多人同框真正的漂脸/串脸高发点在于：
    生成端不知道每个身份绑定哪个画面位置，也不知道弱后端是否必须分层合成。因此 clip 级单独
    输出确定性执行策略，供 `01_分镜出图.md` 登记、gate 对账。
    """
    chars = [c for c in char_plans if c.get("char_id")]
    unique_ids = []
    for c in chars:
        cid = str(c.get("char_id") or "")
        if cid and cid not in unique_ids:
            unique_ids.append(cid)
    if len(unique_ids) < 2:
        return None

    persistent = bool(profile.get("persistent_subject"))
    tiers = {str(c.get("char_id")): str(c.get("tier") or "") for c in chars}
    all_native_ready = persistent and all(tiers.get(cid) in {"native_subject", "lora"} for cid in unique_ids)
    needs_registration = persistent and any(tiers.get(cid) == "native_unregistered" for cid in unique_ids)

    if not persistent:
        mode = "regional_construct_required"
        execution = (
            "无持久角色 ID 后端：默认走空场景底板 empty_plate + 官方 inpaint / regional-prompt 分区构建；"
            "每个槽位只喂该角色自己的 reference_group / face_anchor_refs / expressions，逐区域生成后统一 relighting/color match。"
            "本模式等价硬执行 token：regional_construct_required + split_composite_required，不是条件式兜底。"
        )
    elif all_native_ready:
        mode = "native_subject_slots"
        execution = (
            "按后端原生主体/角色 ID 逐槽位引用；每个槽位绑定具体注册角色ID/形态 + 屏幕位置 + 视线方向，"
            "pose/depth/区域绑定可用时作为站位双保险。"
        )
    else:
        mode = "register_subjects_or_split"
        execution = (
            "当前后端支持持久主体但至少一个角色未 registered/ready：核心角色先注册主体；"
            "来不及注册时本镜按 regional_construct_required / split_composite_required 登记降级。"
        )

    slots: List[Dict[str, Any]] = []
    seen_slots: set = set()
    for i, c in enumerate(chars):
        cid = str(c.get("char_id") or "")
        if cid not in unique_ids or cid in seen_slots:
            continue
        seen_slots.add(cid)
        slots.append({
            "slot": _slot_name(len(slots)),
            "char_id": cid,
            "form": c.get("form") or "常态",
            "tier": c.get("tier"),
            "face_priority": "primary" if i == 0 else "secondary",
            "required_binding": f"`{cid}/{c.get('form') or '常态'}` + 自己的 reference_group / 脸部特写 / 表情库",
        })

    required_prompt_fields = [
        "多人同框身份槽位",
        "多人同框执行策略",
        "screen_positions/blocking",
        "逐主体参考绑定",
        "primary 星标具体注册角色ID*",
        "区分锚点（互斥发色/服装主色/配饰）",
    ]
    if mode not in {"split_composite_required", "regional_construct_required"}:
        required_prompt_fields.append("区域绑定/pose-depth（后端支持时）")
    if mode == "regional_construct_required":
        required_prompt_fields += [
            "空场景底板 empty_plate",
            "区域遮罩/region masks",
            "统一 relighting/color match",
        ]

    distinct = plan_distinct_anchors(dna_by_id or {}, unique_ids, confusable_pairs=confusable_pairs)

    # 相对身量注入：多人同框是体型信号唯一真有用的地方（区分角色 + 跨镜保持谁比谁高/壮，参考图本身保证不了）。
    # registry 角色若声明了 physical_scale.relative_scale（以某角色为标尺的相对身量），收进 clip 策略，
    # 供 01_分镜出图.md 写进 prompt、gate 对账。绝对 height_cm/weight 是写作元数据，不进 prompt（数字 steer 不动像素）。
    relative_scale: Dict[str, str] = {}
    for cid in unique_ids:
        rs = str((dna_by_id or {}).get(cid, {}).get("relative_scale") or "").strip()
        if rs:
            relative_scale[cid] = rs
    if relative_scale:
        required_prompt_fields.append("相对身量/身高比例（relative_scale）")

    # ① 分镜调度（C6 剧情优先）：多人同框由剧情决定，不为迁就后端删戏。
    #    任一 ≥2 清晰具名同框都必须登记槽位+执行策略；≥4/近景/遮挡只是更高风险档。
    n = len(unique_ids)
    if closeup:
        shot_scheduling = {
            "verdict": "split_or_layer_required",
            "default": "优先拆「单人CU + 反打」或降到中景/全景做景别分层；坚持同框近景则登记 regional_construct/split_composite，把每张脸分开生成再合成",
            "note": f"{n} 个具名角色近景同框：近景是串脸最高发档，必须有 `多人同框身份槽位` + `多人同框执行策略`，且策略应是反打、景别分层或分别出图+合成；不是删戏。",
        }
    elif n >= 4:
        shot_scheduling = {
            "verdict": "large_same_frame_requires_strategy",
            "default": "登记 regional_construct/split_composite（empty_plate + 每主体身份槽位 + region masks）把每张脸分别做好再统一融光，或拆 establish+反打把整场拍全",
            "note": f"{n} 个具名角色清晰同框：人数高，优先拆组/反打/分区构建；剧情需要就照出，但必须登记槽位+执行策略后放行；确属远景群像请标 `远景/群像`。",
        }
    else:
        shot_scheduling = {
            "verdict": "slots_required",
            "default": "2-3 人中景/全景同框可行；仍必须按身份槽位 + 执行策略 + 区分锚点出图",
            "note": "2-3 张清晰脸只是相对省钱/稳定的构图区，不是免登记区；gate 仍要求槽位+策略。",
        }

    return {
        "applies": True,
        "mode": mode,
        "backend_label": profile.get("label") or profile.get("canonical") or "当前后端",
        "persistent_subject": persistent,
        "needs_registration": needs_registration,
        "slots": slots,
        "required_prompt_fields": required_prompt_fields,
        "execution": execution,
        "distinct_anchors": distinct,
        "relative_scale": relative_scale,
        "shot_scheduling": shot_scheduling,
        "needs_action": True,
    }


# ── 装配（读盘 → 计划 → 落档） ─────────────────────────────────────────────────

def load_character_forms(root: Path) -> List[Dict[str, Any]]:
    """identity_registry.json → 每角色保留 scope + 各 form 的 reference_group/angle_policy/adapters/lora。

    与 face_drift_risk.load_characters 区别：本规划器需要逐 form 的 reference_group/expressions 选图。
    """
    path = root / "出图" / "共享" / "identity_registry.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for ch in data.get("characters") or []:
        cid = str(ch.get("id") or "").strip()
        forms = [f for f in (ch.get("forms") or []) if isinstance(f, dict)]
        if not cid or not forms:
            continue
        aliases = fdr._split_aliases(ch.get("name") or "")
        for f in forms:
            aliases |= fdr._split_aliases(f.get("asset_key") or "")
        lora = {"status": "not_ready"}
        for f in forms:
            ls = str(((f.get("identity_adapters") or {}).get("lora") or {}).get("status") or "")
            if ls in {"ready", "training"}:
                lora = {"status": ls}
                break
        norm_forms = [{
            "form": str(f.get("form") or "常态"),
            "asset_key": str(f.get("asset_key") or ""),
            "reference_group": f.get("reference_group") or {},
            "reference_atlas": f.get("reference_atlas") or {},
            "angle_policy": f.get("angle_policy") or {},
            "image_adapters": (f.get("identity_adapters") or {}).get("image") or {},
            "character_dna": f.get("character_dna") or {},
            "anchor_phrase": str(f.get("anchor_phrase") or ""),
            "physical_scale": f.get("physical_scale") or {},
        } for f in forms]
        out.append({
            "id": cid,
            "name": str(ch.get("name") or cid),
            "scope": str(ch.get("scope") or ""),
            "aliases": aliases,
            "forms": norm_forms,
            "lora": lora,
        })
    return out


def parse_clip(clip: Mapping[str, Any]) -> Dict[str, Any]:
    """抽取一镜的文本/景别/结构化信号，兼容新旧两套 storyboard schema。纯函数·可测。

    旧 schema：label/scene + shots[].desc/lens。
    新 schema：description + character_ids + continuity.shot_size/expression_span +
              template_contract.camera_rule/blocking/beats/character_slots（shots 可能是 int 列表）。
    """
    parts: List[str] = [str(clip.get("clip") or ""), str(clip.get("label") or ""), str(clip.get("scene") or ""),
                        str(clip.get("description") or ""), str(clip.get("action") or ""), str(clip.get("camera") or "")]
    raw_characters = clip.get("characters") or []
    if isinstance(raw_characters, (list, tuple)):
        parts += [str(item) for item in raw_characters if item]
    elif raw_characters:
        parts.append(str(raw_characters))
    cont = clip.get("continuity") or {}
    parts += [str(cont.get("start_state") or ""), str(cont.get("end_state") or "")]
    tc = clip.get("template_contract") or {}
    if isinstance(tc, Mapping):
        parts += [str(tc.get("camera_rule") or ""), str(tc.get("blocking") or ""), str(tc.get("face_priority") or "")]
        parts += [str(b) for b in (tc.get("beats") or [])]
        slots = tc.get("character_slots")
        if isinstance(slots, dict):
            parts += [str(v) for v in slots.values()]
    elif isinstance(tc, (list, tuple)):
        parts += [str(item) for item in tc if item]
    else:
        parts.append(str(tc))
    lenses: List[str] = []
    for s in (clip.get("shots") or []):
        if isinstance(s, dict):
            parts.append(str(s.get("desc") or ""))
            lenses.append(str(s.get("lens") or ""))
    schedule = clip.get("entity_schedule") if isinstance(clip.get("entity_schedule"), Mapping) else {}
    scheduled_chars = schedule.get("characters") if isinstance(schedule.get("characters"), list) else None
    if scheduled_chars is not None:
        offscreen = {str(x).strip() for x in (schedule.get("offscreen_presence") or []) if str(x).strip()}
        forbidden = {str(x).strip() for x in (schedule.get("forbidden_presence") or []) if str(x).strip()}
        scheduled_visible = [str(x).strip() for x in scheduled_chars
                             if str(x).strip() and str(x).strip() not in offscreen and str(x).strip() not in forbidden]
        # entity_schedule may bind an exact form as CHAR_01/形态.  Identity
        # lookup is by stable character id, while the full token remains in
        # clip text so _pick_form can select the declared form.
        parts += scheduled_visible
        cids = [value.split("/", 1)[0] for value in scheduled_visible]
    else:
        declared = [str(x) for x in (clip.get("character_ids") or []) if x]
        parts += declared
        cids = [value.split("/", 1)[0] for value in declared]
    if not cids and isinstance(raw_characters, (list, tuple)):
        for item in raw_characters:
            text = str(item or "").strip()
            if text.startswith("CHAR_"):
                cids.append(text.split("/", 1)[0])
    return {
        "text": " ".join(p for p in parts if p),
        "lens": " ".join(lenses),
        "shot_size": str(cont.get("shot_size") or ""),
        "expression_span": str(cont.get("expression_span") or ""),
        "character_ids": cids,
    }


def clip_present(parsed: Mapping[str, Any], chars: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    """新 schema 有 character_ids → 按 id 精确匹配（比别名稳）；旧 schema 退回别名匹配。"""
    cids = set(parsed.get("character_ids") or [])
    if cids:
        return [c for c in chars if c.get("id") in cids]
    return fdr.present_characters(str(parsed.get("text") or ""), chars)


def _pick_form(char: Mapping[str, Any], clip_text: str) -> Dict[str, Any]:
    """clip 文本命中某变体 form 的 asset_key → 选该 form，否则用第 1 form 作策略锚。"""
    forms = char.get("forms") or [{}]
    for f in forms:
        fname = str(f.get("form") or "")
        if fname and fname in clip_text:
            return f
        ak = str(f.get("asset_key") or "")
        if ak and ak in clip_text:
            return f
    return forms[0]


def _file_sha256(path: Path) -> str:
    try:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def _memory_anchor_contract(root: Path, ep: str) -> Tuple[Dict[str, List[str]], Dict[str, Any]]:
    """读并 fail-closed 核验 memory_anchor_plan。

    只有当 v3 plan.available 严格为 true、registry/drift/storyboard 三个当前文件都可读且
    SHA 与 source_fingerprint 精确一致、每条 reinject 的每个 reference 都是真实文件时，
    才返回可消费 memory_map。任一项失败则 map={} ，但保留逐项证据供 gate 独立核销。
    """
    path = root / "生产数据" / f"memory_anchor_plan_{ep}.json"
    rel_path = str(path.relative_to(root))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}, {
            "status": "missing",
            "available": False,
            "path": rel_path,
            "sha256": "",
            "required_rows": 0,
            "required_char_keys": [],
            "consumed_char_keys": [],
            "consumed_clip_ids_by_char": {},
            "missing_reference_rows": [],
            "missing_reference_files": {},
            "validated_reference_sha256_by_char": {},
            "errors": ["memory_anchor_plan_missing"],
            "source_fingerprint": {},
            "current_source_fingerprint": {},
        }
    errors: List[str] = []
    if not isinstance(data, Mapping) or data.get("kind") != "n2d_memory_anchor_plan":
        errors.append("kind_invalid")
        data = data if isinstance(data, Mapping) else {}
    try:
        plan_version = int(data.get("version") or 0)
    except (TypeError, ValueError):
        plan_version = 0
    if plan_version < 3:
        errors.append("plan_version_legacy")
    if str(data.get("status") or "").strip().lower() != "ready":
        errors.append("plan_status_not_ready")
    available = data.get("available") is True
    if not available:
        errors.append("plan_available_not_true")
    if str(data.get("episode") or "") != ep:
        errors.append("episode_mismatch")
    source = data.get("source_fingerprint") if isinstance(data.get("source_fingerprint"), Mapping) else {}
    current_registry = _file_sha256(root / "出图" / "共享" / "identity_registry.json")
    current_drift = _file_sha256(root / "生产数据" / "identity_drift_report.json")
    current_storyboard = _file_sha256(root / "脚本" / ep / "storyboard.json")
    source_registry = str(source.get("identity_registry_sha256") or "").strip()
    source_drift = str(source.get("identity_drift_report_sha256") or "").strip()
    source_storyboard = str(source.get("storyboard_sha256") or "").strip()
    if not current_registry:
        errors.append("identity_registry_missing_or_unreadable")
    elif not source_registry:
        errors.append("identity_registry_sha256_missing")
    elif source_registry != current_registry:
        errors.append("identity_registry_sha256_stale")
    if not current_drift:
        errors.append("identity_drift_report_missing_or_unreadable")
    elif not source_drift:
        errors.append("identity_drift_report_sha256_missing")
    elif source_drift != current_drift:
        errors.append("identity_drift_report_sha256_stale")
    if not current_storyboard:
        errors.append("storyboard_missing_or_unreadable")
    elif not source_storyboard:
        errors.append("storyboard_sha256_missing")
    elif source_storyboard != current_storyboard:
        errors.append("storyboard_sha256_stale")
    raw_rows = data.get("rows")
    if not isinstance(raw_rows, list):
        errors.append("rows_invalid")
        raw_rows = []
    rows = [
        row for row in raw_rows
        if isinstance(row, Mapping) and row.get("reinject") is True
    ]
    memory_map: Dict[str, List[str]] = {}
    missing_refs: List[str] = []
    missing_files: Dict[str, List[str]] = {}
    validated_sha: Dict[str, Dict[str, str]] = {}
    required_keys: List[str] = []
    for row in rows:
        key = str(row.get("char") or "").strip()
        if not key:
            errors.append("reinject_row_char_missing")
            continue
        if key in required_keys:
            errors.append(f"reinject_row_duplicate:{key}")
            continue
        required_keys.append(key)
        raw_refs = row.get("memory_anchor_refs")
        refs = [str(p).strip() for p in raw_refs] if isinstance(raw_refs, list) else []
        refs = list(dict.fromkeys(p for p in refs if p))
        if not refs:
            missing_refs.append(key)
            errors.append(f"memory_anchor_refs_missing:{key}")
            continue
        valid_refs: List[str] = []
        missing_for_key: List[str] = []
        sha_for_key: Dict[str, str] = {}
        for rel in refs:
            ref_path = Path(rel).expanduser()
            if not ref_path.is_absolute():
                ref_path = root / ref_path
            sha = _file_sha256(ref_path) if ref_path.is_file() else ""
            if not sha:
                missing_for_key.append(rel)
                errors.append(f"memory_anchor_ref_missing:{key}:{rel}")
                continue
            valid_refs.append(rel)
            sha_for_key[rel] = sha
        if missing_for_key:
            missing_refs.append(key)
            missing_files[key] = missing_for_key
        if valid_refs:
            memory_map[key] = valid_refs
            validated_sha[key] = sha_for_key
    status = "invalid" if errors or missing_refs else "ready"
    contract = {
        "status": status,
        "available": available,
        "path": rel_path,
        "sha256": _file_sha256(path),
        "required_rows": len(rows),
        "required_char_keys": sorted(required_keys),
        "consumed_char_keys": [],
        "consumed_clip_ids_by_char": {},
        "missing_reference_rows": sorted(set(missing_refs)),
        "missing_reference_files": {
            key: sorted(values) for key, values in sorted(missing_files.items())
        },
        "validated_reference_sha256_by_char": {
            key: dict(sorted(values.items())) for key, values in sorted(validated_sha.items())
        },
        "errors": errors,
        "source_fingerprint": dict(source),
        "current_source_fingerprint": {
            "identity_registry_sha256": current_registry,
            "identity_drift_report_sha256": current_drift,
            "storyboard_sha256": current_storyboard,
        },
    }
    return (memory_map if status == "ready" else {}), contract


def _memory_match_for(
    mem_map: Mapping[str, List[str]], cid: str, name: str, asset_key: str
) -> Tuple[str, List[str]]:
    """精确对齐 clip 角色与 drift key，禁止子串串绑。

    允许：asset_key/cid/name 整值 exact，或 key 以 ``cid/`` / ``name/`` 开头。
    不允许：``cid in key`` / ``name in key``；因此 CHAR_1 绝不会命中 CHAR_10。
    """
    cid = str(cid or "").strip()
    name = str(name or "").strip()
    asset_key = str(asset_key or "").strip()
    for candidate in dict.fromkeys(value for value in (asset_key, cid, name) if value):
        if candidate in mem_map:
            return candidate, list(mem_map[candidate])
    prefix_matches: List[Tuple[str, List[str]]] = []
    for raw_key, refs in mem_map.items():
        key = str(raw_key or "").strip()
        if (cid and key.startswith(cid + "/")) or (name and key.startswith(name + "/")):
            prefix_matches.append((key, list(refs)))
    # A cid/name-only fallback is safe only for a single registered form.
    # With multiple forms, choosing the first dictionary row would silently
    # inject the wrong costume/state memory; leave it unconsumed so the gate
    # forces an exact storyboard form binding.
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    return "", []


def _memory_refs_for(mem_map: Mapping[str, List[str]], cid: str, name: str, asset_key: str) -> List[str]:
    """向后兼容的 refs-only 包装；新消费证据用 `_memory_match_for` 保留命中 key。"""
    return _memory_match_for(mem_map, cid, name, asset_key)[1]


def plan_shared_assets(root: Path, chars: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """规划共享定妆资产（武器/道具/VFX/海报…）的脸策略——治"含人资产镜被规划器静默跳过、无脸参考"。

    此前 reference_planner 只逐 storyboard clip × 角色规划，**共享资产不是 clip → 从不进规划器**，
    含人脸的武器握持/持械动作/海报等就被静默放任（大荒碎星戟握持镜脸漂的规划侧盲区）。这里按
    `codex_image_runner.resolve_face_policy`（单一真值源）逐资产判脸策略并开处方：
      - face_locked：列出承载角色（owner/carries_identity·owner-aware）+ 可注入脸锚路径；无承载或承载
        无 ready 脸锚 → action（与 image_qc.audit_asset_face_policy 硬闸互补，规划侧前移提示）。
      - faceless：显式标"出图须背身/裁到下巴以下/无清晰五官·落档像素验 0 脸"（不再静默无参考）。
      - none：纯武器美术/空镜/道具不涉脸，跳过。
    cir 不可加载（缺依赖）→ available=False 优雅跳过。report-only·处方层。"""
    out: Dict[str, Any] = {"available": True, "assets": [], "actions": [], "notes": []}
    if cir is None or not hasattr(cir, "resolve_face_policy"):
        out["available"] = False
        out["notes"].append("codex_image_runner.resolve_face_policy 不可用——共享资产脸策略规划跳过。")
        return out
    try:
        reg = json.loads((Path(root) / "出图" / "共享" / "asset_registry.json").read_text(encoding="utf-8"))
    except Exception:
        out["notes"].append("asset_registry.json 缺失/损坏——共享资产脸策略规划跳过。")
        return out
    by_id = {str(c.get("id") or "").strip(): c for c in (chars or [])}

    def _anchor_for(ref: str) -> Optional[str]:
        cid = ref.split("/", 1)[0]
        ch = by_id.get(cid)
        if not isinstance(ch, dict) or not ch.get("forms"):
            return None
        bare = "/" not in ref
        for form in ch["forms"]:
            fname = str(form.get("form") or "常态").strip()
            if bare or f"{cid}/{fname}" == ref:
                p = _front_ref_abs(root, form)
                if p:
                    return p
        return _front_ref_abs(root, ch["forms"][0])

    for asset in reg.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        aid = str(asset.get("id") or asset.get("name") or "?").strip()
        policy = cir.resolve_face_policy(asset)
        if policy == "none":
            continue
        entry: Dict[str, Any] = {"asset_id": aid, "type": asset.get("type"), "face_policy": policy}
        if policy == "faceless":
            entry["requirement"] = "出图须背身/裁到下巴以下/无脸中性人台·禁清晰五官；落档像素核验 0 清晰脸。"
            entry["face_refs"] = []
        else:  # face_locked
            carried = cir._asset_carried_identities(asset) if hasattr(cir, "_asset_carried_identities") else []
            entry["carried_identities"] = carried
            if not carried:
                entry["issue"] = "face_locked_no_owner"
                out["actions"].append({"kind": "shared_asset_face", "asset": aid,
                                       "issue": "face_locked_no_owner",
                                       "fix": "补 owner: CHAR_xx 或 carries_identity，或改 face_policy: faceless。"})
            else:
                refs = []
                missing = []
                for ref in carried:
                    p = _anchor_for(ref)
                    (refs.append({"carried": ref, "path": p, "role": "face_anchor",
                                  "strength_hint": STRENGTH["face_anchor"]}) if p else missing.append(ref))
                entry["face_refs"] = refs
                if missing:
                    entry["issue"] = "carried_anchor_missing"
                    entry["missing_carried"] = missing
                    out["actions"].append({"kind": "shared_asset_face", "asset": aid,
                                           "issue": "carried_anchor_missing", "missing": missing,
                                           "fix": "把承载角色脸部特写/正面参考置 ready，规划器才能折脸锚。"})
        out["assets"].append(entry)
    out["summary"] = {
        "person_bearing_assets": len(out["assets"]),
        "faceless": sum(1 for a in out["assets"] if a["face_policy"] == "faceless"),
        "face_locked": sum(1 for a in out["assets"] if a["face_policy"] == "face_locked"),
        "actions": len(out["actions"]),
    }
    return out


def build_plan(root: Path, ep: str) -> Dict[str, Any]:
    chars = load_character_forms(root)
    clips = fdr.load_clips(root, ep)
    memory_map, memory_contract = _memory_anchor_contract(root, ep)
    backend = fdr.project_default_backend(root)
    profile = fdr.backend_profile(backend)
    notes: List[str] = []
    if not chars:
        notes.append("identity_registry.json 缺失/无角色——无法规划参考。")
    if not clips:
        notes.append("storyboard.json 缺失/无 clips——先跑 n2d-script 分镜设计再规划。")

    clip_plans: List[Dict[str, Any]] = []
    action_required: List[Dict[str, Any]] = []
    core_present = any(_CORE_SCOPE_RE.search(str(char.get("scope") or "")) for char in chars)
    if core_present and memory_contract.get("status") != "ready":
        action_required.append({
            "kind": "memory_anchor_contract",
            "issue": memory_contract.get("status"),
            "errors": memory_contract.get("errors") or [],
            "fix": f"先运行 n2d-identity memory_anchor.py <作品根> {ep}，再重建 reference_plan。",
        })
    for char_key in memory_contract.get("missing_reference_rows") or []:
        action_required.append({
            "kind": "memory_anchor_missing_reference",
            "char": char_key,
            "issue": "reinject_row_has_no_ready_anchor",
            "fix": "先补齐并验收该角色最早定妆锚，再重跑 memory_anchor.py/reference_planner.py。",
        })
    need_registration: set = set()
    need_lora: set = set()
    multi_subject_actions: List[Dict[str, Any]] = []
    weak_big_delta_clips = 0
    multi_person_clips = 0  # G3：多人同框镜计数（驱动项目级 reference-library 后端建议）

    # C: 预扫所有多人镜涉及的角色，一次性算"参考脸 embedding 易混对"（embedder 只加载一次、每角色只嵌入一次）。
    multiframe_ids: set = set()
    for clip in clips:
        present_ids = {c["id"] for c in clip_present(parse_clip(clip), chars)}
        if len(present_ids) >= 2:
            multiframe_ids |= present_ids
    ref_paths = {}
    for c in chars:
        if c["id"] in multiframe_ids and c.get("forms"):
            ref_paths[c["id"]] = _front_ref_abs(root, c["forms"][0])
    confusable_pairs = compute_confusable_pairs(root, ref_paths)["pairs"] if ref_paths else set()

    for idx, clip in enumerate(clips, 1):
        parsed = parse_clip(clip)
        text, lens = parsed["text"], parsed["lens"]
        present = clip_present(parsed, chars)
        multi = len({c["id"] for c in present}) >= 2
        if multi:
            multi_person_clips += 1
        clip_id = str(clip.get("id") or clip.get("clip") or clip.get("label") or "")
        char_plans: List[Dict[str, Any]] = []
        clip_has_weak_big = False
        for c in present:
            form = _pick_form(c, text)
            tier = (image_lock_tier or (lambda *a, **k: "multi_reference"))(
                backend, form.get("image_adapters") or {}, c.get("lora") or {}
            )
            scope_is_core = bool(_CORE_SCOPE_RE.search(c.get("scope") or ""))
            deltas = variation_deltas(lens, text, form.get("angle_policy") or {},
                                      parsed["shot_size"], parsed["expression_span"])
            cf = {"id": c["id"], "name": c["name"], "form": form.get("form"),
                  "scope": c.get("scope"),
                  "narrative_tier": c.get("narrative_tier"),
                  "library_tier": c.get("library_tier") or form.get("library_tier"),
                  "planned_episode_count": c.get("planned_episode_count"),
                  "face_policy": form.get("face_policy") or c.get("face_policy"),
                  "restricted_partial": form.get("restricted_partial") or c.get("restricted_partial"),
                  "restricted_partial_contract": form.get("restricted_partial_contract") or c.get("restricted_partial_contract"),
                  "reference_group": form.get("reference_group") or {},
                  "reference_atlas": form.get("reference_atlas") or {},
                  "angle_policy": form.get("angle_policy") or {}}
            memory_char_key, mem_refs = _memory_match_for(
                memory_map, c["id"], c["name"], str(form.get("asset_key", ""))
            )
            p = plan_character_in_clip(cf, deltas, multi, profile, tier, scope_is_core, memory_refs=mem_refs)
            if memory_char_key:
                p["memory_anchor_required_char_key"] = memory_char_key
                if p.get("memory_anchor_refs_consumed"):
                    p["memory_anchor_char_key"] = memory_char_key
            char_plans.append(p)
            if p["needs_action"]:
                action_required.append({"clip": clip_id, "char_id": p["char_id"],
                                        "form": p["form"], "missing": p["missing_references"],
                                        "escalation": p["escalation"],
                                        "native_subject_action": p["native_subject_action"]})
            if tier == "native_unregistered" and scope_is_core:
                need_registration.add(f"{p['char_id']}/{p['form']}")
            if p["escalation"] and "lora" in (p["escalation"] or "").lower():
                need_lora.add(f"{p['char_id']}/{p['form']}")
            if tier in {"reference_group", "multi_reference"} and scope_is_core and \
                    ({"closeup", "strong_emotion"} & set(p["variation_delta"]) or
                     any(d.startswith("extreme_angle") for d in p["variation_delta"]) or multi):
                clip_has_weak_big = True
        if clip_has_weak_big:
            weak_big_delta_clips += 1
        clip_plan: Dict[str, Any] = {"clip_id": clip_id, "lens": lens, "characters": char_plans}
        dna_by_id = {}
        for c in present:
            form = _pick_form(c, text)
            dna = dict(form.get("character_dna") or {})
            dna["anchor_phrase"] = form.get("anchor_phrase") or ""
            dna["relative_scale"] = str((form.get("physical_scale") or {}).get("relative_scale") or "")
            dna_by_id[c["id"]] = dna
        clip_confusable = [p for p in confusable_pairs if set(p) <= {c["id"] for c in present}]
        strategy = plan_multi_subject_strategy(char_plans, profile,
                                               dna_by_id=dna_by_id, closeup=_is_closeup(parsed),
                                               confusable_pairs=clip_confusable)
        if strategy:
            clip_plan["multi_subject_strategy"] = strategy
            _sched = strategy.get("shot_scheduling") or {}
            _dist = strategy.get("distinct_anchors") or {}
            action = {
                "kind": "multi_subject_strategy",
                "clip": clip_id,
                "mode": strategy["mode"],
                "chars": [f"{s['char_id']}/{s['form']}" for s in strategy.get("slots") or []],
                "required_prompt_fields": strategy.get("required_prompt_fields") or [],
                "execution": strategy.get("execution"),
                "shot_scheduling": _sched.get("verdict"),
                "shot_scheduling_default": _sched.get("default"),
                "anchor_collision": bool(_dist.get("collision")),
                "anchor_embedding_confusable": any(c.get("embedding_confusable") for c in (_dist.get("collisions") or [])),
                "anchor_guidance": _dist.get("guidance"),
            }
            action_required.append(action)
            multi_subject_actions.append(action)
        clip_plans.append(clip_plan)

    # G2 消费证据必须从最终 clip plan 反推，不信上游 row 的 reinject 声明。
    # 只有真实进入 recommended_references（含与常规 front 同路径去重的情况）
    # 才记 consumed；并保留逐角色的真实 clip ids，供 gate 独立核销。
    consumed_clip_ids_by_char: Dict[str, List[str]] = {}
    for clip_plan in clip_plans:
        clip_id = str(clip_plan.get("clip_id") or "").strip()
        for char_plan in clip_plan.get("characters") or []:
            if not isinstance(char_plan, Mapping) or not char_plan.get("memory_anchor_refs_consumed"):
                continue
            key = str(char_plan.get("memory_anchor_char_key") or "").strip()
            if not key:
                continue
            ids = consumed_clip_ids_by_char.setdefault(key, [])
            if clip_id and clip_id not in ids:
                ids.append(clip_id)
    consumed_clip_ids_by_char = {
        key: values for key, values in sorted(consumed_clip_ids_by_char.items())
    }
    consumed_char_keys = sorted(consumed_clip_ids_by_char)
    required_char_keys = sorted(
        str(key) for key in (memory_contract.get("required_char_keys") or []) if str(key)
    )
    unconsumed_char_keys = sorted(set(required_char_keys) - set(consumed_char_keys))
    memory_contract = {
        **memory_contract,
        "required_char_keys": required_char_keys,
        "consumed_char_keys": consumed_char_keys,
        "consumed_clip_ids_by_char": consumed_clip_ids_by_char,
        "unconsumed_char_keys": unconsumed_char_keys,
    }
    if memory_contract.get("status") == "ready" and unconsumed_char_keys:
        action_required.append({
            "kind": "memory_anchor_unconsumed",
            "chars": unconsumed_char_keys,
            "issue": "required_memory_anchor_not_consumed_by_any_real_clip_plan",
            "fix": "修正角色/形态 key 映射或 storyboard 出场绑定，再重建reference_plan。",
        })

    # G3 项目级建议：多人同框是 2026 仍未解的崩脸/串脸高发区（attention leakage·swap/blend）。
    # 默认 GPT Image 2 等 multi_reference 后端在 2026 多角色一致性 benchmark 无专门优势；reference-library /
    # 持久主体后端（Seedream Universal Reference / 可灵主体库 / Sora Character Cameo）锁多人更稳。
    # 只在项目选择点层面建议整项目统一切换——**勿逐镜切**（项目内模型混用会被 gate 拦）。report-only。
    if multi_person_clips and not bool(profile.get("persistent_subject")):
        ratio = multi_person_clips / max(len(clip_plans), 1)
        notes.append(
            f"G3 多人同框：本集 {multi_person_clips}/{len(clip_plans)} 镜多人同框，当前生图模型 "
            f"{profile.get('label') or backend}（非持久主体/reference-library 后端）。多人同框是 2026 崩脸/串脸"
            "高发区，若本剧群像/对手戏重，建议在选择点 `生图模型` 把**整项目**统一切到 reference-library 后端"
            "（Seedream Universal Reference / 可灵主体库 / Sora Character Cameo·官方多参考后端按官方口径最多约 14 张/"
            "保 5 人）。注意：勿逐镜换后端（=项目内模型混用，gate 会拦）；切则整项目切并重置后端主体/Face Lock 状态。"
            + ("（本集多人镜占比高，优先评估）" if ratio >= 0.4 else "")
        )

    # 动作镜视线/姿态锁汇总（生成侧前移·治"全员正对镜头摆拍"）：逐镜处方已写 ¾ 主锚 + 视线指令，
    # 这里给整集一句总览，提示落进 prompt 并由 image_qc 动作视线闸交付侧兜底。
    _eyeline_clips = sum(1 for cp in clip_plans
                         if any(p.get("pose_gaze_directive") for p in cp.get("characters") or []))
    if _eyeline_clips:
        notes.append(
            f"动作镜视线/姿态锁：本集 {_eyeline_clips} 镜命中动作/打斗 → 逐镜已把 ¾/侧脸提为主身份锚、"
            "front 降权，并写「不看镜头·视线锁戏内目标·camera=observer」指令（生成侧前移，治'全员正对镜头摆拍'）。"
            "逐镜 prompt 落 `pose_gaze_directive`/`视线锁定` 字段；image_qc 动作视线闸在交付侧兜底。"
        )

    # 共享资产脸策略规划（治含人资产镜被规划器静默跳过·无脸参考）：与逐镜规划并列。
    shared_assets = plan_shared_assets(root, chars)
    for a in shared_assets.get("actions") or []:
        action_required.append({"kind": "shared_asset_face", "asset": a.get("asset"),
                                "issue": a.get("issue"), "fix": a.get("fix"),
                                "missing": a.get("missing")})

    return {
        "kind": PLAN_KIND,
        "version": 1,
        "root": str(root),
        "episode": ep,
        "backend": profile.get("canonical") or backend,
        "backend_label": profile.get("label") or backend,
        "backend_strategy": profile.get("strategy"),
        "clips": clip_plans,
        "shared_assets": shared_assets,
        "summary": {
            "clip_count": len(clip_plans),
            "shared_person_bearing_assets": (shared_assets.get("summary") or {}).get("person_bearing_assets", 0),
            "shared_asset_actions": (shared_assets.get("summary") or {}).get("actions", 0),
            "weak_backend_large_delta_clips": weak_big_delta_clips,
            "chars_need_native_registration": sorted(need_registration),
            "chars_need_lora": sorted(need_lora),
            "multi_subject_actions": multi_subject_actions,
            "action_required": action_required,
            "multi_person_clips": multi_person_clips,
            "action_eyeline_lock_clips": sum(
                1 for cp in clip_plans
                if any(p.get("pose_gaze_directive") for p in cp.get("characters") or [])
            ),
            "memory_anchor_reinjected_clips": sum(
                1 for cp in clip_plans
                if any(p.get("memory_anchor_refs_consumed") for p in cp.get("characters") or [])
            ),
            "memory_anchor_contract": memory_contract,
            # 顶层镜像便于 gate/报表无需解释内嵌 contract 就能逐项核销；
            # 内嵌 memory_anchor_contract 中同时保留这三项作自包含证据。
            "required_char_keys": required_char_keys,
            "consumed_char_keys": consumed_char_keys,
            "consumed_clip_ids_by_char": consumed_clip_ids_by_char,
            "tagged_multi_image_clips": sum(
                1 for cp in clip_plans
                if any((p.get("reference_feed") or {}).get("mode") == "tagged_multi_image"
                       for p in cp.get("characters") or [])
            ),
            "video_reference_candidate_clips": sum(
                1 for cp in clip_plans
                if any((p.get("reference_feed") or {}).get("video_reference_hint")
                       for p in cp.get("characters") or [])
            ),
        },
        "notes": notes + ([
            f"G2 跨集记忆锚：{len(memory_map)} 个角色按 memory_anchor_plan_{ep}.json 标记重注入最早定妆记忆锚"
            "（抗 EntityBench 复现间隔衰减·已作为最高优先锚参与参考预算）。"
        ] if memory_map else []),
    }


def render_md(plan: Mapping[str, Any]) -> str:
    s = plan.get("summary") or {}
    lines = [
        "# 逐镜参考规划（治跨集脸漂）",
        "",
        f"- root: {plan.get('root')}",
        f"- episode: {plan.get('episode')}",
        f"- 生图后端: {plan.get('backend_label')}（{plan.get('backend')} · 策略 {plan.get('backend_strategy')}）",
        f"- 镜头数: {s.get('clip_count')} ｜ 弱后端×大变化镜: {s.get('weak_backend_large_delta_clips')}",
        "",
        "> 定妆照对 AI 只是固定板式；本表按**每镜变化量 + 后端能力**给参考处方。建议侧车，人审后落进 "
        "`01_分镜出图.md`；gate 在 image_preflight 对账。",
        "",
    ]
    if plan.get("notes"):
        lines += ["## 备注"] + [f"- {n}" for n in plan["notes"]] + [""]

    sa = plan.get("shared_assets") or {}
    if sa.get("assets"):
        lines += ["## 共享资产脸策略（含人资产镜·治规划侧脸漂盲区）"]
        for a in sa["assets"]:
            pol = a.get("face_policy")
            if pol == "faceless":
                lines.append(f"- `{a.get('asset_id')}`（{a.get('type')}）→ **faceless**：{a.get('requirement')}")
            else:
                carried = "、".join(a.get("carried_identities") or []) or "（无）"
                tail = f"⚠️ {a.get('issue')}" if a.get("issue") else "脸锚已可注入"
                lines.append(f"- `{a.get('asset_id')}`（{a.get('type')}）→ **face_locked**：承载 {carried}；{tail}")
        lines.append("")

    reg = s.get("chars_need_native_registration") or []
    lora = s.get("chars_need_lora") or []
    if reg:
        lines += [f"## 建议注册原生主体（核心长线角·喂多样集）", f"- {'、'.join(reg)}", ""]
    if lora:
        lines += [f"## 建议升 LoRA（弱后端压不住的核心角）", f"- {'、'.join(lora)}", ""]

    multi_actions = s.get("multi_subject_actions") or []
    if multi_actions:
        lines += ["## 多人同框策略", "",
                  "> ① 分镜调度优先：`slots_required`=≥2 清晰具名同框必须登记槽位+策略；"
                  "`large_same_frame_requires_strategy`=高人数同框建议拆组/分区；`split_or_layer_required`=多人近景必须反打/分层/分别出图；"
                  "④ 锚点撞色=同框角色发色/服装主色雷同，逐主体补互斥 `区分锚点`。",
                  "",
                  "| 镜头 | 模式 | 角色槽位 | 分镜调度 | 撞色 | prompt 必填 | 执行 |",
                  "|---|---|---|---|---|---|---|"]
        for a in multi_actions:
            sched = a.get("shot_scheduling") or "ok"
            sched_cell = sched if sched == "ok" else f"⚠️{sched}"
            coll_cell = ("🔴脸像" if a.get("anchor_embedding_confusable")
                         else ("⚠️撞色" if a.get("anchor_collision") else "-"))
            lines.append(
                f"| {a.get('clip')} | {a.get('mode')} | {'、'.join(a.get('chars') or []) or '-'} "
                f"| {sched_cell} | {coll_cell} "
                f"| {'、'.join(a.get('required_prompt_fields') or []) or '-'} | {a.get('execution') or '-'} |"
            )
        lines.append("")

    s2 = plan.get("summary") or {}
    if s2.get("tagged_multi_image_clips") or s2.get("video_reference_candidate_clips"):
        lines += [
            f"> 喂法（后端能力路由）：分图分标镜 {s2.get('tagged_multi_image_clips', 0)}、"
            f"可喂视频参考镜 {s2.get('video_reference_candidate_clips', 0)}。多参考后端喂**分离带标签图**而非拼 sheet；"
            "支持视频参考的后端对大表情/近景/原生主体注册可喂定妆视频/多帧。",
            "",
        ]
    _FEED_LABEL = {"tagged_multi_image": "分图分标", "sequential_single_reference": "单图主参考",
                   "single_reference": "单参考"}
    lines += ["## 逐镜处方", "", "| 镜头 | 角色/形态 | 档位 | 变化量 | 推荐参考 | 喂法 | 预算 | 控制网 | 补拍缺口 | 升档 |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for clip in plan.get("clips") or []:
        for c in clip.get("characters") or []:
            refs = "<br>".join(f"{r['role']}({r['strength_hint']})" for r in c.get("recommended_references") or []) or "-"
            budget = c.get("reference_budget") or {}
            limit = budget.get("limit")
            dropped = budget.get("dropped") or 0
            budget_cell = f"{budget.get('selected', '-')}/{limit or '不限'}"
            if dropped:
                budget_cell += f"<br>丢弃{dropped}"
            cn = "、".join(c.get("controlnet") or []) or "-"
            miss_items = list(c.get("missing_references") or [])
            if c.get("pose_gaze_directive"):
                miss_items.append("🎥动作视线锁：¾/侧脸主锚 + 不看镜头·视线锁戏内目标（见 pose_gaze_directive）")
            miss = "<br>".join(miss_items) or "-"
            esc = "✅需升档" if c.get("escalation") else "-"
            feed = c.get("reference_feed") or {}
            feed_cell = _FEED_LABEL.get(feed.get("mode") or "", "-")
            if feed.get("video_reference_hint"):
                feed_cell += "<br>🎬视频参考"
            lines.append(
                f"| {clip.get('clip_id')} | {c.get('char_id')}/{c.get('form')} | {c.get('tier')} "
                f"| {'、'.join(c.get('variation_delta') or []) or '-'} | {refs} | {feed_cell} | {budget_cell} | {cn} | {miss} | {esc} |"
            )
    lines.append("")
    actions = s.get("action_required") or []
    if actions:
        lines += ["## 行动项（人审后落进 prompt）"]
        for a in actions:
            if a.get("kind") == "multi_subject_strategy":
                lines.append(
                    f"- [{a.get('clip')}] 多人同框：{a.get('mode')}；"
                    f"角色槽位={'、'.join(a.get('chars') or []) or '-'}；"
                    f"必填={'、'.join(a.get('required_prompt_fields') or []) or '-'}；{a.get('execution') or ''}"
                )
                continue
            bits = []
            if a.get("missing"):
                bits.append("补拍：" + "；".join(a["missing"]))
            if a.get("native_subject_action"):
                bits.append(a["native_subject_action"])
            if a.get("escalation"):
                bits.append(a["escalation"])
            lines.append(f"- [{a.get('clip')}] {a.get('char_id')}/{a.get('form')}：" + " ｜ ".join(bits))
        lines.append("")
    return "\n".join(lines)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_plan(root: Path, ep: str, plan: Mapping[str, Any]) -> Tuple[Path, Path]:
    out_dir = root / "生产数据"
    jp = out_dir / f"reference_plan_{ep}.json"
    mp = out_dir / f"reference_plan_{ep}.md"
    _atomic_write(jp, json.dumps(plan, ensure_ascii=False, indent=2))
    _atomic_write(mp, render_md(plan))
    return jp, mp


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="出图前·能力路由的逐镜参考规划器（治跨集脸漂）")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true", help="只打印 JSON，不落档")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    plan = build_plan(root, ns.episode)
    if ns.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    jp, mp = write_plan(root, ns.episode, plan)
    print(f"wrote {jp}")
    print(f"wrote {mp}")
    s = plan["summary"]
    print(f"镜头 {s['clip_count']} ｜ 弱后端×大变化镜 {s['weak_backend_large_delta_clips']} "
          f"｜ 待注册主体 {len(s['chars_need_native_registration'])} ｜ 待升LoRA {len(s['chars_need_lora'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
