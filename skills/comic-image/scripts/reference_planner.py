#!/usr/bin/env python3
"""出图前·能力路由的逐格参考规划器（治跨话脸漂·2026-07 标准审计·参照同仓成熟生产线处方层的漫画重实现，不跨线 import）。

为什么存在：跨话人物脸会漂，真因之一是——不同格的**服装/表情/景别/角度**变化时，只靠**单张定妆照做图生图不够准**。
定妆照对 AI 只是个"固定板式"，身份判别细节不足，模型在新条件下会重画整张脸，逐话累积成漂移。漫画线此前只有：
`memory_anchor`（跨话记忆锚·治长间隔再登场的 Gap-Decay·**事前钉锚**）+ `character_consistency`/`identity report`
（**事后**量漂移）。缺的是**事前处方**：按这一格的变化量 × 所选生图后端的真实能力，开出"该喂哪些参考 + 要不要升档"。

本规划器就是那层处方（与 `character_consistency` 的事后诊断互补·同 identity 一致性口径）：逐格逐角色算"变化量 delta"
（近景/大表情/极端角度/换装/动作/多人同框），再按后端能力表（comic `_lib/image_backend_adapter`）路由参考集、
封顶参考预算、给弱后端×核心长线角×大变化格开升档建议，并对多人同框给身份槽位 + 撞色区分。产物是
`生产数据/comic_reference_plan_第N话.{json,md}`；`build_panel_jobs` 必须消费其当前 SHA 版本。
缺结构化 ID/真实附件/当前 memory plan 属确定性交接缺口并阻断，颜色撞色、升档和像素代理仍只提示。纯 stdlib、零生成成本。

用法：
  cd skills/comic-image/scripts
  python3 reference_planner.py <作品根> 第N话 [--write] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

# comic 线自有后端能力表（独立线·非跨线 import：comic 的 _lib 属于本线）。
_COMIC_LIB = Path(__file__).resolve().parents[2] / "comic" / "_lib"
if str(_COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(_COMIC_LIB))
try:
    from image_backend_adapter import resolve_capabilities
except Exception:  # pragma: no cover - 部分复制的 skill 目录兜底
    resolve_capabilities = None  # type: ignore

VERSION = 2
KIND = "comic_reference_plan"

# 参考角色 → 默认 image2image 强度建议（与 build_panel_jobs 的视图优先级同向）。
STRENGTH = {
    "memory_anchor": 0.82, "face": 0.72, "front": 0.8, "three_quarter": 0.65,
    "side": 0.55, "back": 0.5, "expression": 0.6, "outfit": 0.55,
}
# 标准五视图（与 comic-identity 同口径）。
STANDARD_VIEWS = ("face", "front", "three_quarter", "side", "back")
# 按 library_tier 的必需视图（与 comic-identity tier 分档同口径·独立线复制不 import）。
TIER_REQUIRED_VIEWS = {
    "core_full": ("front", "three_quarter", "side", "back", "face"),
    "recurring_standard": ("front", "three_quarter", "face"),
    "named_minimal": ("front", "face"),
    "restricted_partial": (),
}
# 核心长线角色判定（与 comic 长线定妆口径一致）。
_CORE_SCOPE_RE = re.compile(r"全篇|全程|长线|核心|主角|女主|男主|主反派")

CLOSEUP_RE = re.compile(r"特写|近景|大头|面部|脸部|ECU|BCU|MCU|CU\b", re.IGNORECASE)
WIDE_RE = re.compile(r"远景|大远景|全景|全身|群像|WS|EWS|\bLS\b", re.IGNORECASE)
EMOTION_RE = re.compile(r"哭|泪|怒|愤|狂喜|惊|恐|惧|悲|绝望|震惊|嘶吼|咆哮|狞|狂|痛|颤")
ANGLE_RE = re.compile(r"俯视|仰视|鸟瞰|大俯|大仰|顶视|极端角度|逆光顶光")
BACK_RE = re.compile(r"背身|背对|背影|过肩|OTS|回眸")
ACTION_RE = re.compile(r"打斗|动作|冲击|命中|受击|斩|劈|挥|刺|追|扑|格挡|施法|爆|拆招|交锋|武打")
EMOTION_FUNCS = ("reaction", "emotional_peak", "reveal", "turning_point", "climax", "payoff")
CHARACTER_PREFIXES = ("CHAR_", "MON_")
ASSET_PREFIX_TYPES = {
    "LOC_": "location",
    "PROP_": "prop",
    "OUTFIT_": "outfit",
    "SYS_": "system_asset",
    "FX_": "vfx",
    "VFX_": "vfx",
    "STYLE_": "style",
}
BINDING_KEYS = ("form_id", "outfit_id", "expression_id", "state_id")

# 撞色桶（多人同框区分锚点用·从 character_dna 文本粗取主色）。
_COLOR_BUCKETS: Sequence = (
    ("红", ("红", "赤", "朱", "绛", "丹", "胭脂", "猩红")),
    ("白", ("白", "素", "皓", "雪", "月白")),
    ("黑", ("黑", "玄", "墨", "乌", "黛")),
    ("蓝", ("蓝", "青", "碧", "靛", "藏青")),
    ("绿", ("绿", "翠", "葱", "苍")),
    ("紫", ("紫", "藕")),
    ("金", ("金", "黄", "鎏金", "明黄")),
    ("银灰", ("银", "灰", "霜")),
    ("粉", ("粉", "桃", "嫣")),
    ("褐", ("褐", "棕", "栗", "驼")),
)


# ── 纯函数（无依赖·可测） ─────────────────────────────────────────────────────

def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_chapter(value: str) -> str:
    raw = str(value or "").strip()
    if raw.startswith("第") and raw.endswith("话"):
        return raw
    m = re.search(r"\d+", raw)
    return f"第{int(m.group(0))}话" if m else raw


def _color_bucket(text: str) -> Optional[str]:
    t = str(text or "")
    for name, kws in _COLOR_BUCKETS:
        if any(k in t for k in kws):
            return name
    return None


def dna_text(dna: Any) -> str:
    """character_dna 兼容 str 或 dict → 扁平文本。纯函数·可测。"""
    if isinstance(dna, str):
        return dna
    if isinstance(dna, Mapping):
        return " ".join(str(v) for v in dna.values())
    return ""


def panel_text(panel: Mapping[str, Any]) -> str:
    """一格里参与变化量判定的画面文本（art_notes/description/景别/角度提示）。纯函数·可测。"""
    parts = [str(panel.get(k) or "") for k in
             ("description", "art_notes", "shot_size", "lens", "camera", "gaze_target", "eyeline_direction")]
    return " ".join(p for p in parts if p)


def panel_character_ids(panel: Mapping[str, Any]) -> List[str]:
    ids: List[str] = []
    for binding in panel.get("character_bindings") or []:
        if isinstance(binding, Mapping):
            cid = str(binding.get("character_id") or binding.get("id") or "").strip()
            if cid.startswith(CHARACTER_PREFIXES) and cid not in ids:
                ids.append(cid)
    for key in ("references", "characters", "character_ids"):
        for raw in panel.get(key) or []:
            rid = str(raw or "").split("/", 1)[0].strip()
            if rid.startswith(("CHAR_", "MON_")) and rid not in ids:
                ids.append(rid)
    return ids


def structured_character_bindings(panel: Mapping[str, Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for raw in panel.get("character_bindings") or []:
        if not isinstance(raw, Mapping):
            continue
        cid = str(raw.get("character_id") or raw.get("id") or "").strip()
        if not cid:
            continue
        row = {"character_id": cid}
        for key in BINDING_KEYS:
            row[key] = str(raw.get(key) or "").strip()
        out.append(row)
    return out


def validate_panel_bindings(panel: Mapping[str, Any], chars: Mapping[str, Mapping[str, Any]]) -> tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
    """Validate deterministic ID links; never guesses a display name."""
    pid = str(panel.get("panel_id") or "?")
    bindings = structured_character_bindings(panel)
    findings: List[Dict[str, Any]] = []
    bound_ids = {row["character_id"] for row in bindings}
    declared_ids: set[str] = set()
    for key in ("characters", "character_ids", "references"):
        for raw in panel.get(key) or []:
            value = str(raw or "").split("/", 1)[0].strip()
            if value.startswith(CHARACTER_PREFIXES):
                declared_ids.add(value)
            elif key in {"characters", "character_ids"} and value:
                findings.append({
                    "severity": "block", "code": "named_character_without_stable_id", "panel": pid,
                    "message": f"{pid} characters 含裸名字「{value}」；显示名不能替代 CHAR_/MON_ 稳定 ID 与真实附件",
                })
    for cid in sorted(declared_ids - bound_ids):
        findings.append({
            "severity": "block", "code": "missing_structured_character_binding", "panel": pid,
            "character_id": cid,
            "message": f"{pid}·{cid} 缺 character_bindings（form_id/outfit_id/expression_id/state_id）",
        })
    seen: set[str] = set()
    for row in bindings:
        cid = row["character_id"]
        if cid in seen:
            findings.append({"severity": "block", "code": "duplicate_character_binding", "panel": pid, "character_id": cid,
                             "message": f"{pid}·{cid} 重复绑定；同一角色同格只能有一组状态合同"})
            continue
        seen.add(cid)
        char = chars.get(cid)
        if not isinstance(char, Mapping):
            findings.append({"severity": "block", "code": "unknown_character_binding", "panel": pid, "character_id": cid,
                             "message": f"{pid}·{cid} 未登记到 identity_registry"})
            continue
        collections = {
            "form_id": char.get("forms"),
            "outfit_id": char.get("outfits"),
            "expression_id": char.get("expressions"),
            "state_id": char.get("states"),
        }
        for key, collection in collections.items():
            value = row.get(key, "")
            if not value:
                findings.append({"severity": "block", "code": f"character_binding_{key}_missing", "panel": pid,
                                 "character_id": cid, "message": f"{pid}·{cid} 缺 {key}"})
            elif not isinstance(collection, Mapping) or value not in collection:
                findings.append({"severity": "block", "code": f"character_binding_{key}_unknown", "panel": pid,
                                 "character_id": cid, "message": f"{pid}·{cid} 引用未登记 {key}={value}"})
        states = char.get("states") if isinstance(char.get("states"), Mapping) else {}
        state = states.get(row.get("state_id")) if isinstance(states, Mapping) else None
        if isinstance(state, Mapping):
            for key in ("form_id", "outfit_id", "expression_id"):
                expected = str(state.get(key) or "")
                if expected and row.get(key) != expected:
                    findings.append({"severity": "block", "code": "character_binding_state_conflict", "panel": pid,
                                     "character_id": cid,
                                     "message": f"{pid}·{cid} 的 state_id={row.get('state_id')} 要求 {key}={expected}，实际为 {row.get(key)}"})
    return bindings, findings


def variation_deltas(text: str, story_function: str = "") -> List[str]:
    """单格单角色相对定妆照的变化量（多人同框在 clip 级另算）。纯函数·可测。"""
    d: List[str] = []
    if CLOSEUP_RE.search(text):
        d.append("closeup")
    if WIDE_RE.search(text):
        d.append("wide_full_body")
    if EMOTION_RE.search(text) or str(story_function or "").strip().lower() in EMOTION_FUNCS:
        d.append("strong_emotion")
    if ANGLE_RE.search(text):
        d.append("extreme_angle")
    if BACK_RE.search(text):
        d.append("back_or_over_shoulder")
    if ACTION_RE.search(text):
        d.append("action_eyeline_lock")
    return d


def required_views_for_tier(tier: str) -> Sequence[str]:
    return TIER_REQUIRED_VIEWS.get(str(tier or "").strip() or "core_full",
                                   TIER_REQUIRED_VIEWS["core_full"])


def plan_character_in_panel(
    char: Mapping[str, Any],
    deltas: Sequence[str],
    multi: bool,
    caps: Mapping[str, Any],
    scope_is_core: bool,
    memory_refs: Sequence[str] = (),
) -> Dict[str, Any]:
    """逐格逐角色处方：推荐参考集 + 缺口 + 升档 + 预算封顶。纯函数·可测。

    char: {id, display_name, tier, views(dict view→path), outfit_ids(set), dna(str)}。
    caps: {persistent_subject, single_character_reference_limit, multi_character_reference_limit, adapter_id}。
    memory_refs: 跨话记忆锚路径（memory_anchor 计划标 ready 时），作为最高优先锚前置。
    """
    cid = str(char.get("id") or "")
    views = char.get("views") if isinstance(char.get("views"), Mapping) else {}
    tier = str(char.get("tier") or "core_full")
    deltas = list(deltas)
    closeup = "closeup" in deltas
    strong_emotion = "strong_emotion" in deltas
    extreme = "extreme_angle" in deltas
    back = "back_or_over_shoulder" in deltas
    wide = "wide_full_body" in deltas
    action = "action_eyeline_lock" in deltas
    big_delta = closeup or strong_emotion or extreme or back or wide or multi

    refs: List[Dict[str, Any]] = []
    missing: List[str] = []
    have_paths: set = set()

    def add(role: str, view_key: Optional[str] = None) -> bool:
        path = str(views.get(view_key or role) or "").strip()
        if path and path not in have_paths:
            refs.append({"role": role, "path": path, "strength_hint": STRENGTH.get(role, 0.5)})
            have_paths.add(path)
            return True
        return False

    # 身份核心集：正面 + 脸锚；¾ 由档位/变化量决定。
    if tier == "restricted_partial":
        if not add("anchor"):
            missing.append("受限主体允许范围内的身份锚（anchor）")
    else:
        if not add("front"):
            missing.append("正面定妆（front）")
        if not add("face"):
            missing.append("脸部特写锚（face·具名角色强制）")
    needs_three_quarter = (
        tier not in ("named_minimal", "restricted_partial")
        or closeup or strong_emotion or extreme or action
    )
    if needs_three_quarter and not add("three_quarter"):
        missing.append("45°/three_quarter 参考（档位或本格变化量需要）")

    # 形态/状态/表情是逐角色绑定，不再用 panel-wide 模糊词猜测。
    form_id = str(char.get("panel_form_id") or "").strip()
    form_ref = str((char.get("form_refs") or {}).get(form_id) or "").strip()
    if form_id and form_ref and form_ref not in have_paths:
        refs.append({"role": "form", "path": form_ref, "strength_hint": 0.72, "contract_id": form_id})
        have_paths.add(form_ref)
    expression_id = str(char.get("panel_expression_id") or "").strip()
    expression_ref = str((char.get("expression_refs") or {}).get(expression_id) or "").strip()
    expression_emotion = str((char.get("expression_emotions") or {}).get(expression_id) or "").lower()
    if expression_ref and expression_ref not in have_paths:
        refs.append({"role": "expression", "path": expression_ref, "strength_hint": STRENGTH["expression"],
                     "contract_id": expression_id})
        have_paths.add(expression_ref)
    if strong_emotion and (not expression_ref or expression_emotion in {"", "neutral", "中性"}):
        missing.append(f"强情绪格缺对应表情参考（expression_id={expression_id or 'missing'}；不能用中性 face 冒充）")

    # 极端角度 / 过肩背身 → 侧/背视图。
    if (extreme or back) and not add("side"):
        missing.append("侧脸参考（极端角度/转头/过肩格）")
    if back and not add("back"):
        missing.append("背身参考（背影/过肩格）")

    # 远景/全身 → 需要全身或转身参考（漫画 registry 无 turnaround 时用 side/back 兜，仍不足则缺口）。
    if wide and not (views.get("side") or views.get("back")):
        missing.append("全身/三视图参考（远景/全身动作格·单张头肩定妆不够）")

    # 换装格：服装子注册 + 服装参考图（业界失效模式：锁脸锁不住领型/纽扣/花纹）。
    outfit_ids = char.get("outfit_ids") if isinstance(char.get("outfit_ids"), (set, list, tuple)) else set()
    panel_outfit = str(char.get("panel_outfit_id") or "").strip()
    if panel_outfit:
        outfit_ref = str((char.get("outfit_refs") or {}).get(panel_outfit) or "").strip()
        if outfit_ref and outfit_ref not in have_paths:
            refs.append({"role": "outfit", "path": outfit_ref, "strength_hint": STRENGTH["outfit"]})
            have_paths.add(outfit_ref)
        elif panel_outfit not in outfit_ids or not outfit_ref:
            missing.append(f"服装参考图（换装 {panel_outfit}：换装格锁脸锁不住领型/纽扣/花纹，须登记 outfits 子注册 + 参考图）")

    state_id = str(char.get("panel_state_id") or "").strip()
    state_ref = str((char.get("state_refs") or {}).get(state_id) or "").strip()
    if state_ref and state_ref not in have_paths:
        refs.append({"role": "state", "path": state_ref, "strength_hint": 0.58, "contract_id": state_id})
        have_paths.add(state_ref)

    # G2 跨话记忆锚（memory-sink）：长间隔再登场/晚话/已漂移角色，最早定妆锚前置为最高优先。
    memory_injected: List[Dict[str, Any]] = []
    for mp in memory_refs:
        mp = str(mp or "").strip()
        if mp and mp not in have_paths:
            memory_injected.append({"role": "memory_anchor", "path": mp,
                                    "strength_hint": STRENGTH["memory_anchor"]})
            have_paths.add(mp)
    if memory_injected:
        refs = memory_injected + refs

    # 动作镜视线锁（生成侧前移·治"防脸漂堆 frontal → 拆招拍成正对镜头摆拍"）：¾ 提为主锚、front 降权，
    # 写「不看镜头·视线锁戏内目标」指令。与 comic gate 的 panel_camera_gaze_unjustified 硬闸同向、事前化。
    pose_gaze_directive: Optional[str] = None
    prompt_required: List[str] = []
    if action:
        for r in refs:
            if r["role"] == "three_quarter":
                r["strength_hint"] = max(float(r["strength_hint"]), 0.78)
            elif r["role"] == "front":
                r["strength_hint"] = min(float(r["strength_hint"]), 0.55)
        refs.sort(key=lambda r: 0 if r["role"] in ("memory_anchor", "three_quarter") else 1)
        pose_gaze_directive = ("动作格：脸可辨但不直视读者/镜头——¾/侧轮廓，视线锁戏内目标（对手/武器来路/命中点），"
                               "负面词注入「看镜头、looking at viewer、正对镜头摆拍」。除非本格显式标 POV/破第四墙。")
        prompt_required.append("动作格视线锁定指令（不看镜头/¾侧脸/视线锁对手或命中点）")
        if not any(r["role"] == "three_quarter" for r in refs):
            missing.append("45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置）")

    # 按后端能力封顶参考张数；溢出显式记账，不静默吞参考。
    limit_key = "multi_character_reference_limit" if multi else "single_character_reference_limit"
    max_refs = int(caps.get(limit_key) or 0)
    requested = len(refs)
    dropped: List[Dict[str, Any]] = []
    if max_refs > 0 and len(refs) > max_refs:
        dropped = refs[max_refs:]
        refs = refs[:max_refs]
        missing.append(f"参考预算溢出（后端 {limit_key}={max_refs} 张，已丢 "
                       + "、".join(str(r["role"]) for r in dropped) + "）；拆格/升档/精选参考包")

    # 升档建议：弱后端（无持久主体）× 核心长线角 × 大变化格。
    escalation: Optional[str] = None
    if not caps.get("persistent_subject") and scope_is_core and big_delta:
        escalation = ("弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），"
                      "或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，"
                      "坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。")

    needs_action = bool(missing or escalation)
    return {
        "char_id": cid, "name": char.get("display_name") or cid, "tier": tier,
        "binding": {
            "form_id": form_id,
            "outfit_id": panel_outfit,
            "expression_id": expression_id,
            "state_id": state_id,
        },
        "variation_delta": deltas + (["multi_character"] if multi else []),
        "recommended_references": refs,
        "reference_budget": {"limit": max_refs or None, "requested": requested,
                             "selected": len(refs), "dropped": len(dropped)},
        "dropped_references": dropped,
        "missing_references": missing,
        "memory_anchor_reinjected": bool(memory_injected),
        "escalation": escalation,
        "pose_gaze_directive": pose_gaze_directive,
        "prompt_required": prompt_required,
        "needs_action": needs_action,
    }


def plan_multi_subject(char_plans: Sequence[Mapping[str, Any]], caps: Mapping[str, Any],
                       dna_by_id: Mapping[str, str], closeup: bool) -> Optional[Dict[str, Any]]:
    """多人同框格级处方：身份槽位 + 后端路由 + 撞色区分 + 近景拆反打建议。纯函数·可测。"""
    ids: List[str] = []
    for c in char_plans:
        cid = str(c.get("char_id") or "")
        if cid and cid not in ids:
            ids.append(cid)
    if len(ids) < 2:
        return None
    persistent = bool(caps.get("persistent_subject"))
    slot_names = ("画左槽位", "画右槽位", "前景槽位", "后景槽位")
    slots = [{"slot": slot_names[i] if i < len(slot_names) else f"额外槽位{i + 1}",
              "char_id": cid, "face_priority": "primary" if i == 0 else "secondary",
              "required_binding": f"{cid} 自己的 front/face/¾ 参考"}
             for i, cid in enumerate(ids)]
    # 撞色判定：主色桶相同=模型易把两张脸平均（串脸高发）。
    buckets = {cid: _color_bucket(dna_by_id.get(cid, "")) for cid in ids}
    collisions = [f"{a}↔{b}（同主色「{buckets[a]}」）"
                  for i, a in enumerate(ids) for b in ids[i + 1:]
                  if buckets[a] and buckets[a] == buckets[b]]
    if not persistent:
        mode = "per_character_reference_slots"
        execution = ("无持久主体后端：每个槽位只喂该角色自己的参考，逐区域构图；近景多人易串脸时优先拆单人特写+反打，"
                     "或分别出图后合成，不为迁就后端删角色。")
    else:
        mode = "native_subject_slots"
        execution = "后端支持持久主体：按注册主体 ID 逐槽位引用 + 各自参考做双保险。"
    return {
        "applies": True, "mode": mode, "backend": caps.get("adapter_id"),
        "persistent_subject": persistent, "slots": slots,
        "color_collisions": collisions,
        "required_prompt_fields": ["多人同框身份槽位", "画左/画右/前后景 blocking", "逐主体参考绑定", "区分锚点（互斥发色/服装主色/配饰）"],
        "shot_scheduling": ("近景多人=串脸最高发档：优先拆「单人CU+反打」或降中景/全景，坚持同框近景须登记分区/分别出图+合成"
                            if closeup else "2-3 人中景/全景可行，仍须按身份槽位+区分锚点出图"),
        "execution": execution, "needs_action": True,
    }


# ── IO + 装配 ────────────────────────────────────────────────────────────────

def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def read_setting(root: Path, key: str, default: str) -> str:
    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*[:：]\s*(.+?)\s*$")
    for line in load_text(root / "_设置.md").splitlines():
        m = pattern.match(line)
        if m:
            return m.group(1).strip()
    return default


def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def backend_caps(root: Path, chapter: str) -> Dict[str, Any]:
    model = read_setting(root, "生图模型", "自定义")
    channel = read_setting(root, "生图渠道", "manual")
    if resolve_capabilities is None:
        return {"adapter_id": "unavailable", "persistent_subject": False,
                "single_character_reference_limit": 4, "multi_character_reference_limit": 2}
    caps = resolve_capabilities(model, channel)
    return caps.to_dict()


def load_characters(registry: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """identity_registry.assets → {cid: {id, display_name, tier, scope, views, outfit_ids, outfit_refs, dna}}。"""
    assets = registry.get("assets") if isinstance(registry.get("assets"), Mapping) else {}
    out: Dict[str, Dict[str, Any]] = {}
    for cid, asset in assets.items():
        if not isinstance(asset, Mapping) or not str(cid).startswith(("CHAR_", "MON_")):
            continue
        views = dict(asset.get("views") or {})
        # reference_images 里的 anchor/view 兜底进 views（older schema 无独立 views 时）。
        for ri in asset.get("reference_images") or []:
            if isinstance(ri, Mapping):
                v, p = str(ri.get("view") or "").strip(), str(ri.get("path") or "").strip()
                if v and p and v not in views:
                    views[v] = p
        if asset.get("anchor_path") and "anchor" not in views:
            views["anchor"] = asset["anchor_path"]
        outfits = asset.get("outfits") if isinstance(asset.get("outfits"), Mapping) else {}
        outfit_refs: Dict[str, str] = {}
        for oid, ov in outfits.items():
            if isinstance(ov, Mapping):
                imgs = ov.get("reference_images") or []
                if imgs:
                    first = imgs[0]
                    outfit_refs[oid] = str(first.get("path") if isinstance(first, Mapping) else first or "").strip()
        forms = asset.get("forms") if isinstance(asset.get("forms"), Mapping) else {}
        expressions = asset.get("expressions") if isinstance(asset.get("expressions"), Mapping) else {}
        states = asset.get("states") if isinstance(asset.get("states"), Mapping) else {}

        def first_ref(record: Any) -> str:
            if not isinstance(record, Mapping):
                return ""
            refs = record.get("reference_images") or []
            if not refs:
                return ""
            first = refs[0]
            return str(first.get("path") if isinstance(first, Mapping) else first or "").strip()

        out[str(cid)] = {
            "id": str(cid),
            "display_name": str(asset.get("display_name") or cid),
            "tier": str(asset.get("library_tier") or asset.get("tier") or "core_full"),
            "scope": str(asset.get("scope") or ""),
            "views": views,
            "outfit_ids": set(outfits.keys()),
            "outfit_refs": outfit_refs,
            "forms": dict(forms),
            "form_refs": {str(key): first_ref(record) for key, record in forms.items()},
            "outfits": dict(outfits),
            "expressions": dict(expressions),
            "expression_refs": {str(key): first_ref(record) for key, record in expressions.items()},
            "expression_emotions": {
                str(key): str(record.get("emotion") or record.get("name") or "") if isinstance(record, Mapping) else ""
                for key, record in expressions.items()
            },
            "states": dict(states),
            "state_refs": {str(key): first_ref(record) for key, record in states.items()},
            "default_binding": dict(asset.get("default_binding") or {}) if isinstance(asset.get("default_binding"), Mapping) else {},
            "dna": dna_text(asset.get("character_dna")),
        }
    return out


def load_memory_refs(root: Path, chapter: str) -> Dict[str, List[str]]:
    """comic-identity memory_anchor 计划（文件契约·不跨 skill import），返回 {cid: [路径]} 仅 ready。"""
    status = memory_plan_status(root, chapter)
    if status.get("status") != "current":
        return {}
    plan = status.get("plan") or {}
    out: Dict[str, List[str]] = {}
    for row in plan.get("characters") or []:
        if isinstance(row, Mapping) and row.get("status") == "ready":
            cid = str(row.get("character_id") or "")
            paths = [str(r.get("path") or "").strip()
                     for r in (row.get("pinned_refs") or []) if isinstance(r, Mapping) and r.get("path")]
            if cid and paths:
                out[cid] = paths
    return out


def memory_plan_status(root: Path, chapter: str) -> Dict[str, Any]:
    path = root / "生产数据" / f"comic_memory_anchor_{chapter}.json"
    plan = load_json(path, {}) or {}
    if not plan:
        return {"status": "missing", "path": str(path.relative_to(root)), "sha256": "", "plan": {}}
    inputs = plan.get("inputs") if isinstance(plan.get("inputs"), Mapping) else {}
    expected_scripts = []
    script_root = root / "脚本"
    for chapter_dir in sorted(script_root.glob("第*话")) if script_root.is_dir() else []:
        script_path = chapter_dir / "panel_script.json"
        if script_path.is_file():
            expected_scripts.append({"path": str(script_path.relative_to(root)), "sha256": file_sha256(script_path)})
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    current_registry_sha = file_sha256(registry_path) if registry_path.is_file() else ""
    current = (
        plan.get("kind") == "comic_memory_anchor_plan"
        and plan.get("chapter") == chapter
        and list(inputs.get("panel_scripts") or []) == expected_scripts
        and str(inputs.get("identity_registry_sha256") or "") == current_registry_sha
    )
    # A pinned file changing also invalidates the plan even if the registry file
    # was not updated correctly.
    for row in plan.get("characters") or []:
        for ref in row.get("pinned_refs") or []:
            if not isinstance(ref, Mapping):
                continue
            raw = str(ref.get("path") or "")
            ref_path = Path(raw) if Path(raw).is_absolute() else root / raw
            if not ref_path.is_file() or str(ref.get("sha256") or "") != file_sha256(ref_path):
                current = False
    return {
        "status": "current" if current else "stale",
        "path": str(path.relative_to(root)),
        "sha256": file_sha256(path),
        "inputs_fingerprint": str(plan.get("inputs_fingerprint") or ""),
        "plan": plan,
    }


def character_needs_memory_anchor(root: Path, chapter: str, character_id: str) -> bool:
    match = re.search(r"\d+", chapter)
    target = int(match.group(0)) if match else 0
    seen: List[int] = []
    for chapter_dir in (root / "脚本").glob("第*话") if (root / "脚本").is_dir() else []:
        number_match = re.search(r"\d+", chapter_dir.name)
        if not number_match:
            continue
        number = int(number_match.group(0))
        data = load_json(chapter_dir / "panel_script.json", {}) or {}
        if any(character_id in panel_character_ids(panel) for panel in data.get("panels") or [] if isinstance(panel, Mapping)):
            seen.append(number)
    earlier = sorted(value for value in seen if value < target)
    return bool(earlier and (target - earlier[-1] >= 2 or target - earlier[0] >= 5))


def asset_reference_path(root: Path, registry: Mapping[str, Any], asset_id: str) -> str:
    assets = registry.get("assets") if isinstance(registry.get("assets"), Mapping) else {}
    asset = assets.get(asset_id) if isinstance(assets, Mapping) and isinstance(assets.get(asset_id), Mapping) else {}
    candidates: List[str] = []
    for key in ("anchor_path", "primary_path", "path"):
        value = str(asset.get(key) or "").strip()
        if value:
            candidates.append(value)
    for ref in asset.get("reference_images") or []:
        value = str(ref.get("path") if isinstance(ref, Mapping) else ref or "").strip()
        if value:
            candidates.append(value)
    for raw in candidates:
        path = Path(raw) if Path(raw).is_absolute() else root / raw
        if path.is_file():
            return str(path.relative_to(root)) if not Path(raw).is_absolute() else str(path)
    return ""


def panel_asset_ids(panel: Mapping[str, Any]) -> List[str]:
    ids: List[str] = []
    for key in ("references", "resident_assets"):
        value = panel.get(key) or []
        values = value if isinstance(value, list) else re.findall(r"(?:LOC|PROP|OUTFIT|SYS|FX|VFX|STYLE)_[A-Z0-9_]+", str(value))
        for raw in values:
            rid = str(raw or "").split("/", 1)[0].strip()
            if rid.startswith(tuple(ASSET_PREFIX_TYPES)) and rid not in ids:
                ids.append(rid)
    scene_id = str(panel.get("scene_anchor_id") or panel.get("scene_id") or panel.get("location_id") or "").strip()
    if scene_id.startswith("LOC_") and scene_id not in ids:
        ids.insert(0, scene_id)
    return ids


def effective_attachment_limit(caps: Mapping[str, Any]) -> int:
    limit = int(caps.get("reference_image_limit") or 0)
    if str(caps.get("adapter_id") or "") == "openai_gpt_image_project_memory":
        limit = min(limit or 5, 5)  # current executable Codex image_generation attachment ceiling
    return max(0, limit)


def allocate_panel_attachments(
    root: Path,
    panel: Mapping[str, Any],
    char_plans: Sequence[Mapping[str, Any]],
    registry: Mapping[str, Any],
    caps: Mapping[str, Any],
) -> Dict[str, Any]:
    """Fair attachment allocation: one real anchor per named subject first."""
    limit = effective_attachment_limit(caps)
    mandatory: List[Dict[str, Any]] = []
    extras_by_character: List[List[Dict[str, Any]]] = []
    missing: List[str] = []
    seen_paths: set[str] = set()
    for plan in char_plans:
        cid = str(plan.get("char_id") or "")
        candidates = [dict(item) for item in plan.get("recommended_references") or [] if isinstance(item, Mapping) and item.get("path")]
        first = next((item for item in candidates if item.get("role") in {"memory_anchor", "front", "face", "three_quarter"}), candidates[0] if candidates else None)
        if not first:
            missing.append(f"{cid} 无任何真实身份锚")
            continue
        first["id"] = cid
        first["character_id"] = cid
        first["required"] = True
        if str(first["path"]) not in seen_paths:
            mandatory.append(first)
            seen_paths.add(str(first["path"]))
        extras: List[Dict[str, Any]] = []
        for item in candidates:
            if str(item.get("path")) in seen_paths:
                continue
            item["id"] = cid
            item["character_id"] = cid
            item["required"] = False
            extras.append(item)
        extras_by_character.append(extras)
    for asset_id in panel_asset_ids(panel):
        path = asset_reference_path(root, registry, asset_id)
        if not path:
            if asset_id.startswith(("LOC_", "PROP_")):
                missing.append(f"{asset_id} 缺真实共享参考图")
            continue
        if path in seen_paths:
            continue
        mandatory.append({
            "id": asset_id,
            "role": ASSET_PREFIX_TYPES.get(next((prefix for prefix in ASSET_PREFIX_TYPES if asset_id.startswith(prefix)), ""), "asset"),
            "path": path,
            "required": asset_id.startswith(("LOC_", "PROP_")),
        })
        seen_paths.add(path)
    over_capacity = limit <= 0 or len(mandatory) > limit
    selected = list(mandatory[:limit]) if limit else []
    if not over_capacity:
        while len(selected) < limit and any(extras_by_character):
            progressed = False
            for extras in extras_by_character:
                while extras and str(extras[0].get("path")) in seen_paths:
                    extras.pop(0)
                if extras and len(selected) < limit:
                    item = extras.pop(0)
                    selected.append(item)
                    seen_paths.add(str(item.get("path")))
                    progressed = True
            if not progressed:
                break
    for item in selected:
        path = Path(str(item.get("path") or ""))
        resolved = path if path.is_absolute() else root / path
        item["sha256"] = file_sha256(resolved) if resolved.is_file() else ""
    return {
        "limit": limit,
        "required_count": len(mandatory),
        "selected_count": len(selected),
        "selected": selected,
        "missing_required": missing,
        "over_capacity": over_capacity,
        "split_suggestion": (
            f"本格至少需要 {len(mandatory)} 个关键附件，但执行后端上限为 {limit}；拆成单人反打/分区生成后合成，不得删角色或静默丢 LOC/PROP"
            if over_capacity else ""
        ),
    }


def build_plan(root: Path, chapter: str) -> Dict[str, Any]:
    script_path = root / "脚本" / chapter / "panel_script.json"
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    memory_path = root / "生产数据" / f"comic_memory_anchor_{chapter}.json"
    settings_path = root / "_设置.md"
    script = load_json(script_path, {}) or {}
    registry = load_json(registry_path, {}) or {}
    chars = load_characters(registry)
    caps = backend_caps(root, chapter)
    memory_status = memory_plan_status(root, chapter)
    memory_refs = load_memory_refs(root, chapter)
    dna_by_id = {cid: c["dna"] for cid, c in chars.items()}

    panels = [p for p in (script.get("panels") or []) if isinstance(p, Mapping)]
    panel_plans: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []
    notes: List[str] = []
    if not chars:
        notes.append("identity_registry.json 缺角色——先跑 comic-identity 建定妆再规划。")
    if not panels:
        notes.append("panel_script.json 无格——先跑 comic-script 分格再规划。")

    for panel in panels:
        pid = str(panel.get("panel_id") or "?")
        bindings, binding_findings = validate_panel_bindings(panel, chars)
        findings.extend(binding_findings)
        cids = [row["character_id"] for row in bindings if row["character_id"] in chars]
        if not cids and not binding_findings and not panel_asset_ids(panel):
            continue
        multi = len(cids) >= 2
        text = panel_text(panel)
        story_function = str(panel.get("story_function") or "").strip().lower()
        deltas_panel = variation_deltas(text, story_function)
        strong_emotion_contract = bool(
            story_function in EMOTION_FUNCS
            or panel.get("strong_emotion") is True
            or str(panel.get("expression_intensity") or "").strip().lower() in {"strong", "extreme", "high", "强", "极强"}
        )
        closeup = "closeup" in deltas_panel
        bindings_by_id = {row["character_id"]: row for row in bindings}
        char_plans: List[Dict[str, Any]] = []
        for cid in cids:
            c = dict(chars[cid])
            binding = bindings_by_id[cid]
            c["panel_form_id"] = binding.get("form_id")
            c["panel_outfit_id"] = binding.get("outfit_id")
            c["panel_expression_id"] = binding.get("expression_id")
            c["panel_state_id"] = binding.get("state_id")
            scope_core = bool(_CORE_SCOPE_RE.search(c.get("scope") or "")
                              or _CORE_SCOPE_RE.search(c.get("dna") or ""))
            cp = plan_character_in_panel(c, deltas_panel, multi, caps, scope_core,
                                         memory_refs.get(cid, []))
            char_plans.append(cp)
            for miss in cp["missing_references"]:
                strong_expression_gap = "强情绪格缺对应表情参考" in miss
                severity = "block" if (
                    (strong_expression_gap and strong_emotion_contract)
                    or "正面定妆" in miss
                    or "脸部特写锚" in miss
                    or "服装参考图" in miss
                ) else "warn"
                code = "strong_emotion_expression_reference_missing" if "强情绪格缺对应表情参考" in miss else "missing_reference"
                finding = {"severity": severity, "code": code, "panel": pid,
                           "character_id": cid, "message": f"{pid}·{cp['name']}：缺 {miss}"}
                if strong_expression_gap and not strong_emotion_contract:
                    finding["confidence"] = "heuristic"
                findings.append(finding)
            if cp["escalation"]:
                findings.append({"severity": "info", "code": "escalation_suggested", "panel": pid,
                                 "message": f"{pid}·{cp['name']}：{cp['escalation']}"})
        multi_plan = plan_multi_subject(char_plans, caps, dna_by_id, closeup) if multi else None
        if multi_plan:
            if multi_plan["color_collisions"]:
                findings.append({"severity": "warn", "code": "same_frame_color_collision", "panel": pid,
                                 "message": f"{pid} 多人同框主色撞色（易串脸）：{'、'.join(multi_plan['color_collisions'])}"
                                            "——用互斥发色/服装主色/配饰强分，必要时拆反打。"})
            if closeup:
                findings.append({"severity": "warn", "code": "multi_character_closeup", "panel": pid,
                                 "message": f"{pid} 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，"
                                            "坚持同框须登记分区/分别出图+合成。"})
        for cid in cids:
            if character_needs_memory_anchor(root, chapter, cid) and memory_status.get("status") != "current":
                findings.append({
                    "severity": "block", "code": "memory_anchor_plan_not_current", "panel": pid, "character_id": cid,
                    "message": f"{pid}·{cid} 是长间隔再登场角色，但 memory anchor 计划为 {memory_status.get('status')}；先重跑 comic-identity memory_anchor --write",
                })
        attachments = allocate_panel_attachments(root, panel, char_plans, registry, caps)
        for message in attachments["missing_required"]:
            findings.append({"severity": "block", "code": "required_attachment_missing", "panel": pid,
                             "message": f"{pid}：{message}"})
        if attachments["over_capacity"]:
            findings.append({"severity": "block", "code": "critical_reference_budget_overflow", "panel": pid,
                             "message": f"{pid}：{attachments['split_suggestion']}"})
        panel_findings = [item for item in findings if item.get("panel") == pid]
        panel_record = {"panel_id": pid, "character_bindings": bindings, "characters": char_plans,
                            "multi_subject": multi_plan,
                            "attachment_plan": attachments,
                            "blocked": any(item.get("severity") == "block" for item in panel_findings),
                            "blocking_codes": sorted({str(item.get("code")) for item in panel_findings if item.get("severity") == "block"}),
                            "needs_action": any(cp["needs_action"] for cp in char_plans) or bool(multi_plan) or bool(panel_findings)}
        panel_record["panel_plan_sha256"] = canonical_sha(panel_record)
        panel_plans.append(panel_record)

    input_files = []
    for path in (script_path, registry_path, memory_path, settings_path):
        input_files.append({
            "path": str(path.relative_to(root)),
            "exists": path.is_file(),
            "sha256": file_sha256(path) if path.is_file() else "",
        })
    inputs = {
        "files": input_files,
        "backend": caps,
        "memory_anchor_status": {key: memory_status.get(key) for key in ("status", "path", "sha256", "inputs_fingerprint")},
    }
    inputs_fingerprint = canonical_sha(inputs)

    result = {
        "kind": KIND, "version": VERSION, "chapter": chapter, "generated_at": now_iso(),
        "inputs": inputs,
        "inputs_fingerprint": inputs_fingerprint,
        "backend": caps,
        "provenance": "事前处方·结构化角色绑定×能力路由×真实附件分配·SHA 输入指纹·2026-07",
        "summary": {
            "panels_with_characters": len(panel_plans),
            "panels_needing_action": sum(1 for p in panel_plans if p["needs_action"]),
            "panels_blocked": sum(1 for p in panel_plans if p["blocked"]),
            "block": sum(1 for f in findings if f["severity"] == "block"),
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
            "info": sum(1 for f in findings if f["severity"] == "info"),
        },
        "panel_plans": panel_plans,
        "findings": findings,
        "notes": notes,
    }
    result["plan_sha256"] = canonical_sha({key: value for key, value in result.items() if key not in {"generated_at", "plan_sha256"}})
    return result


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    b = report.get("backend") or {}
    lines = [f"# 逐格参考规划（事前处方）· {report.get('chapter')}", "",
             f"- 后端 {b.get('adapter_id')}（持久主体 {b.get('persistent_subject')}·单角色参考上限 "
             f"{b.get('single_character_reference_limit')}）",
             f"- 含角色格 {s.get('panels_with_characters')} · 需处理 {s.get('panels_needing_action')} · "
             f"warn {s.get('warn')} · info {s.get('info')}", ""]
    for f in report.get("findings") or []:
        icon = "⛔" if f["severity"] == "block" else ("⚠️" if f["severity"] == "warn" else "ℹ️")
        lines.append(f"- {icon} `{f['code']}` {f['message']}")
    if not report.get("findings"):
        lines.append("- ✅ 逐格参考处方无缺口（现有定妆足以覆盖本话变化量）")
    for note in report.get("notes") or []:
        lines.append(f"- · {note}")
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("chapter")
    ap.add_argument("--write", action="store_true", help="写 生产数据/comic_reference_plan_<话>.json/md")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    chapter = normalize_chapter(ns.chapter)
    report = build_plan(root, chapter)
    if ns.write:
        out = root / "生产数据"
        out.mkdir(parents=True, exist_ok=True)
        (out / f"comic_reference_plan_{chapter}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out / f"comic_reference_plan_{chapter}.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
