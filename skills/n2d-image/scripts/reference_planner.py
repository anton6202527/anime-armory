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
要不要升档"，写成**建议侧车** `生产数据/reference_plan_第N集.{json,md}`，人审后落进 prompt；
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
    "outfit": 0.5, "turnaround": 0.5, "scene_light": 0.45,
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
    tier: image_lock_tier → reference_group|multi_reference|native_unregistered|native_subject|lora。
    """
    rg = char.get("reference_group") or {}
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
        path = str(rg.get(key or role) or "").strip()
        if path:
            refs.append({"role": role, "path": path, "strength_hint": STRENGTH.get(role, 0.5)})

    # 身份主参考 + 服装体态锚（每镜底座）
    add_ref("front")
    add_ref("outfit")

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

    # 按后端能力封顶参考张数
    max_refs = profile.get("max_reference_images")
    if isinstance(max_refs, int) and max_refs > 0 and len(refs) > max_refs:
        refs = refs[:max_refs]

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
        "controlnet": controlnet,
        "missing_references": missing,
        "native_subject_action": native_action,
        "escalation": escalation,
        "needs_action": needs_action,
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
            "angle_policy": f.get("angle_policy") or {},
            "image_adapters": (f.get("identity_adapters") or {}).get("image") or {},
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
    weak_big_delta_clips = 0

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
        clip_plans.append({"clip_id": clip_id, "lens": lens, "characters": char_plans})

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

    lines += ["## 逐镜处方", "", "| 镜头 | 角色/形态 | 档位 | 变化量 | 推荐参考 | 控制网 | 补拍缺口 | 升档 |",
              "|---|---|---|---|---|---|---|---|"]
    for clip in plan.get("clips") or []:
        for c in clip.get("characters") or []:
            refs = "<br>".join(f"{r['role']}({r['strength_hint']})" for r in c.get("recommended_references") or []) or "-"
            cn = "、".join(c.get("controlnet") or []) or "-"
            miss = "<br>".join(c.get("missing_references") or []) or "-"
            esc = "✅需升档" if c.get("escalation") else "-"
            lines.append(
                f"| {clip.get('clip_id')} | {c.get('char_id')}/{c.get('form')} | {c.get('tier')} "
                f"| {'、'.join(c.get('variation_delta') or []) or '-'} | {refs} | {cn} | {miss} | {esc} |"
            )
    lines.append("")
    actions = s.get("action_required") or []
    if actions:
        lines += ["## 行动项（人审后落进 prompt）"]
        for a in actions:
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
