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
    from n2d_contract import image_identity_profile, image_lock_tier
except Exception:  # pragma: no cover - 异常布局兜底
    image_identity_profile = None  # type: ignore
    image_lock_tier = None  # type: ignore

PLAN_KIND = "n2d_reference_plan"

# 核心长线角色判定（与 gate.check_image_ai_policy 同口径）：scope 含贯穿全篇/长线/主角标记。
_CORE_SCOPE_RE = re.compile(r"全篇|全程|长线|核心|主角|女主|男主|主反派")

# 参考角色 → 默认 image2image 强度建议（对齐现有 01_分镜出图.md 写法）。
STRENGTH = {
    "front": 0.8, "expression": 0.6, "side": 0.55, "back": 0.5,
    "three_quarter": 0.65, "face_anchor": 0.7, "outfit": 0.5, "turnaround": 0.5, "scene_light": 0.45,
}


# ── 纯函数（无依赖·可测） ──────────────────────────────────────────────────────

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
) -> Dict[str, Any]:
    """逐镜逐角色处方：推荐参考集 + 控制网 + 原生主体动作 + 升档 + 补拍缺口。纯函数·可测。

    char: {id, name, form, reference_group(dict), angle_policy(dict)}。
    tier: image_lock_tier → reference_group|multi_reference|face_embedding|native_unregistered|native_subject|lora。
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

    refs: List[Dict[str, Any]] = []
    missing: List[str] = []
    controlnet: List[str] = []

    def add_ref(role: str, key: Optional[str] = None) -> None:
        if role == "three_quarter":
            path = _base_view_path(atlas, "three_quarter") or str(rg.get(key or role) or "").strip()
        else:
            path = str(rg.get(key or role) or "").strip()
        if path:
            refs.append({"role": role, "path": path, "strength_hint": STRENGTH.get(role, 0.5)})

    # 身份核心集（每镜底座）：正面 + 45° + 基础脸锚 + 服装体态锚。
    add_ref("front")
    add_ref("three_quarter")
    face_anchor_paths = _face_anchor_paths(rg, atlas)
    for p in face_anchor_paths[:1]:
        refs.append({"role": "face_anchor", "path": p, "strength_hint": STRENGTH["face_anchor"]})
    add_ref("outfit")
    if not _base_view_path(atlas, "three_quarter") and not str(rg.get("three_quarter") or "").strip():
        missing.append("45°/three_quarter 基础角度参考（所有角色/形态强制 ready）")
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

    # 多人同框 → 控制网锁站位（正交叠加：控制网锁站位、参考锁身份），仅多参考后端且非已注册主体时建议
    if multi and bool(profile.get("multi_reference")) and tier in {"reference_group", "multi_reference"}:
        controlnet = ["pose", "depth"]

    # 按后端能力封顶参考张数；预算溢出要显式写进 plan，不能静默吞参考。
    requested_ref_count = len(refs)
    dropped_refs: List[Dict[str, Any]] = []
    max_refs = profile.get("max_reference_images")
    if isinstance(max_refs, int) and max_refs > 0 and len(refs) > max_refs:
        dropped_refs = refs[max_refs:]
        refs = refs[:max_refs]
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

    needs_action = bool(missing or escalation or tier == "native_unregistered")
    return {
        "char_id": cid,
        "name": char.get("name"),
        "form": form,
        "tier": tier,
        "variation_delta": deltas + (["multi_character"] if multi else []),
        "recommended_references": refs,
        "reference_budget": reference_budget,
        "dropped_references": dropped_refs,
        "controlnet": controlnet,
        "missing_references": missing,
        "native_subject_action": native_action,
        "escalation": escalation,
        "needs_action": needs_action,
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
        mode = "split_composite_required"
        execution = (
            "无持久角色 ID 后端：每个角色单独以自己的 reference_group / expressions 做 image2image 出图，"
            "再按同一构图槽位合成同框；这是硬执行，不是条件式兜底。"
        )
    elif all_native_ready:
        mode = "native_subject_slots"
        execution = (
            "按后端原生主体/角色 ID 逐槽位引用；每个槽位绑定 CHAR_xx/形态 + 屏幕位置 + 视线方向，"
            "pose/depth/区域绑定可用时作为站位双保险。"
        )
    else:
        mode = "register_subjects_or_split"
        execution = (
            "当前后端支持持久主体但至少一个角色未 registered/ready：核心角色先注册主体；"
            "来不及注册时本镜按 split_composite_required 登记降级。"
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
        "primary 星标 CHAR_xx*",
        "区分锚点（互斥发色/服装主色/配饰）",
    ]
    if mode != "split_composite_required":
        required_prompt_fields.append("区域绑定/pose-depth（后端支持时）")

    distinct = plan_distinct_anchors(dna_by_id or {}, unique_ids, confusable_pairs=confusable_pairs)

    # ① 分镜调度：默认避开多人近景同框。≥4 清晰同框=任何后端都压不住（实测 ≤3 上限）。
    n = len(unique_ids)
    if n >= 4:
        shot_scheduling = {
            "verdict": "over_cap",
            "default": "拆镜：清晰同框 ≤3 具名角色，其余推背景/虚焦/背身/过肩或拆成反打/分镜",
            "note": f"{n} 个具名角色清晰同框超出 ≤3 上限——单帧里 4+ 张清晰脸必崩，确属远景群像请标 `远景/群像` 豁免。",
        }
    elif closeup:
        shot_scheduling = {
            "verdict": "downgrade_recommended",
            "default": "优先拆「单人CU + 反打」或降到中景/全景做景别分层（清晰主角1人，余者推后景/虚焦）",
            "note": "多人近景同框是脸漂/串脸最高发档；保留同框近景须显式登记 split_composite/分层合成。",
        }
    else:
        shot_scheduling = {
            "verdict": "ok",
            "default": "中景/全景同框可行；按身份槽位 + 区分锚点出图",
            "note": "",
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
    parts: List[str] = [str(clip.get("label") or ""), str(clip.get("scene") or ""),
                        str(clip.get("description") or "")]
    cont = clip.get("continuity") or {}
    parts += [str(cont.get("start_state") or ""), str(cont.get("end_state") or "")]
    tc = clip.get("template_contract") or {}
    parts += [str(tc.get("camera_rule") or ""), str(tc.get("blocking") or ""), str(tc.get("face_priority") or "")]
    parts += [str(b) for b in (tc.get("beats") or [])]
    slots = tc.get("character_slots")
    if isinstance(slots, dict):
        parts += [str(v) for v in slots.values()]
    lenses: List[str] = []
    for s in (clip.get("shots") or []):
        if isinstance(s, dict):
            parts.append(str(s.get("desc") or ""))
            lenses.append(str(s.get("lens") or ""))
    cids = [str(x) for x in (clip.get("character_ids") or []) if x]
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
        ak = str(f.get("asset_key") or "")
        if ak and ak in clip_text:
            return f
    return forms[0]


def build_plan(root: Path, ep: str) -> Dict[str, Any]:
    chars = load_character_forms(root)
    clips = fdr.load_clips(root, ep)
    backend = fdr.project_default_backend(root)
    profile = fdr.backend_profile(backend)
    notes: List[str] = []
    if not chars:
        notes.append("identity_registry.json 缺失/无角色——无法规划参考。")
    if not clips:
        notes.append("storyboard.json 缺失/无 clips——先跑 n2d-script 分镜设计再规划。")

    clip_plans: List[Dict[str, Any]] = []
    action_required: List[Dict[str, Any]] = []
    need_registration: set = set()
    need_lora: set = set()
    multi_subject_actions: List[Dict[str, Any]] = []
    weak_big_delta_clips = 0

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

    for clip in clips:
        parsed = parse_clip(clip)
        text, lens = parsed["text"], parsed["lens"]
        present = clip_present(parsed, chars)
        multi = len({c["id"] for c in present}) >= 2
        clip_id = str(clip.get("id") or clip.get("label") or "")
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
                  "reference_group": form.get("reference_group") or {},
                  "reference_atlas": form.get("reference_atlas") or {},
                  "angle_policy": form.get("angle_policy") or {}}
            p = plan_character_in_clip(cf, deltas, multi, profile, tier, scope_is_core)
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

    return {
        "kind": PLAN_KIND,
        "version": 1,
        "root": str(root),
        "episode": ep,
        "backend": profile.get("canonical") or backend,
        "backend_label": profile.get("label") or backend,
        "backend_strategy": profile.get("strategy"),
        "clips": clip_plans,
        "summary": {
            "clip_count": len(clip_plans),
            "weak_backend_large_delta_clips": weak_big_delta_clips,
            "chars_need_native_registration": sorted(need_registration),
            "chars_need_lora": sorted(need_lora),
            "multi_subject_actions": multi_subject_actions,
            "action_required": action_required,
        },
        "notes": notes,
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

    reg = s.get("chars_need_native_registration") or []
    lora = s.get("chars_need_lora") or []
    if reg:
        lines += [f"## 建议注册原生主体（核心长线角·喂多样集）", f"- {'、'.join(reg)}", ""]
    if lora:
        lines += [f"## 建议升 LoRA（弱后端压不住的核心角）", f"- {'、'.join(lora)}", ""]

    multi_actions = s.get("multi_subject_actions") or []
    if multi_actions:
        lines += ["## 多人同框策略", "",
                  "> ① 分镜调度优先：`over_cap`=拆镜(≥4清晰同框)、`downgrade_recommended`=多人近景建议拆反打/降景别；"
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

    lines += ["## 逐镜处方", "", "| 镜头 | 角色/形态 | 档位 | 变化量 | 推荐参考 | 预算 | 控制网 | 补拍缺口 | 升档 |",
              "|---|---|---|---|---|---|---|---|---|"]
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
            miss = "<br>".join(c.get("missing_references") or []) or "-"
            esc = "✅需升档" if c.get("escalation") else "-"
            lines.append(
                f"| {clip.get('clip_id')} | {c.get('char_id')}/{c.get('form')} | {c.get('tier')} "
                f"| {'、'.join(c.get('variation_delta') or []) or '-'} | {refs} | {budget_cell} | {cn} | {miss} | {esc} |"
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
