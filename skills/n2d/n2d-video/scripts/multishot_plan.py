#!/usr/bin/env python3
"""原生多镜单次生成·执行计划（P2-7 原生主体绑定快车道）。

2026 工业前沿（Seedance 2.0 / Kling 3.0）从「逐镜拼」走向「原生多镜一次出 + 角色数字身份绑定」：
一次 co-generate 多个连续镜头，模型自带主体绑定 → 跨镜身份/光照/转场由模型内部锁，省去逐镜定妆锚
焊接。n2d 的 `n2d-model-router` 已把「连续接力镜 + 支持多镜的 primary」标成 `multishot_groups`
**候选**（advisory，不自动合并，保逐 Clip 可重跑粒度）。

本脚本把那条候选**升为执行计划**——与 `同场景批量出图`/scene_batch 同范式：
  • 选择点 `原生多镜生成`=自动（默认·能力门控）或开启，且 primary 后端 multishot_native 时，候选组成为
    **激活的**一次 co-generate 计划——治「single_take_multishot 决定了却仍被逐镜拆成很多 clip」；
    显式 `关闭` 才退回逐镜独立出（保稳）。后端不支持多镜时自动降级为逐镜，不强推。
  • 计划给出 `model_handled_seams`：组内非首成员与前一成员的接缝由模型一次生成内部消除——
    供 seam/QC 层 `seam_is_model_handled()` 消费，对组内接力镜**不再要求逐镜尾帧接力焊接**
    （那是逐镜拼的补丁；原生多镜不需要）。组间接缝仍按逐镜严格。
  • 不合并 Clip 记账：逐 Clip 仍是独立可追踪可重跑单元（模型矩阵立身原则），只是出片侧可按本计划
    把一组喂一次 co-generate。组大小上限由 router 按 max_clip_seconds 已切好，本脚本只读不再切。

纯函数（resolve/seam helper）有 pytest 覆盖；CLI 读 video_model_routes.json + _设置.md，落
出视频/<集>/prompt/multishot_plan.{json,md}。git-free·只读已落盘 router 产物，不出图不花钱。

用法：python3 multishot_plan.py <作品根> <第N集> [--write] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set

_LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

KIND = "n2d_multishot_plan"
SETTING_KEY = "原生多镜生成"
SETTING_ON_VALUES = ("开启", "on", "true", "enabled", "1", "启用")
SETTING_OFF_VALUES = ("关闭", "off", "false", "disabled", "0", "禁用", "逐镜")
SETTING_AUTO_VALUES = ("自动", "auto")


# ── 纯函数 ─────────────────────────────────────────────────────────────────────

def setting_is_on(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in {v.lower() for v in SETTING_ON_VALUES}


def setting_mode(value: Optional[str]) -> str:
    """`原生多镜生成` 原值 → 'on' | 'off' | 'auto'。

    缺省/空/不认得 → 'auto'（能力门控默认）：治「single_take_multishot 决定了却仍被逐镜拆成很多 clip」——
    后端支持原生多镜时默认一次 co-generate 接力组（=更少 clip），只有显式 `关闭` 才退回逐镜独立出。
    """
    raw = str(value or "").strip().lower()
    if raw in {v.lower() for v in SETTING_OFF_VALUES}:
        return "off"
    if raw in {v.lower() for v in SETTING_ON_VALUES}:
        return "on"
    return "auto"


def resolve_plan(routes_payload: Mapping[str, Any], *, active: bool) -> Dict[str, Any]:
    """router 的 video_model_routes.json → 原生多镜执行计划。纯函数。

    active=False（选择点关闭/默认）→ groups=[]、model_handled_seams=[]，等于逐镜独立出（零变化）。
    active=True → 把 router 的 multishot_groups 升为激活组；组内**第 2..n 个**成员标 model-handled
    （它与前一成员的接缝由一次 co-generate 内部消除）。组首成员的入点接缝仍按逐镜（与前一组/前一独立镜）。"""
    groups: List[Dict[str, Any]] = []
    model_handled: List[str] = []
    if not active:  # 选择点关闭/默认 → 零输出 = 逐镜独立出，零行为变化
        return {"active": False, "groups": groups, "model_handled_seams": model_handled}
    groups_in = routes_payload.get("multishot_groups") if isinstance(routes_payload, Mapping) else None
    groups_in = groups_in if isinstance(groups_in, list) else []
    for g in groups_in:
        if not isinstance(g, Mapping):
            continue
        members = [str(m) for m in (g.get("members") or []) if str(m)]
        if len(members) < 2:
            continue
        backend = str(g.get("backend") or "")
        groups.append({
            "group_id": str(g.get("group_id") or f"MSG_{len(groups)+1:02d}"),
            "members": members,
            "backend": backend,
            "approx_seconds": g.get("approx_seconds"),
            "activated": bool(active),
        })
        if active:
            model_handled.extend(members[1:])  # 组内接力接缝由模型一次生成内部消除
    return {
        "active": bool(active),
        "groups": groups,
        "model_handled_seams": sorted(set(model_handled)),
    }


def seam_is_model_handled(clip_id: str, plan: Mapping[str, Any]) -> bool:
    """组内接力镜的接缝是否由原生多镜一次生成内部消除（供 seam/QC 层消费，不再要求逐镜尾帧焊接）。

    仅当计划 active 且该 clip 是某激活组的非首成员时为 True。纯函数·无 IO。"""
    if not isinstance(plan, Mapping) or not plan.get("active"):
        return False
    return str(clip_id) in set(plan.get("model_handled_seams") or [])


def summarize(plan: Mapping[str, Any]) -> Dict[str, Any]:
    groups = plan.get("groups") or []
    return {
        "active": bool(plan.get("active")),
        "group_count": len(groups),
        "co_generated_clips": sum(len(g.get("members") or []) for g in groups),
        "model_handled_seam_count": len(plan.get("model_handled_seams") or []),
    }


# ── IO ────────────────────────────────────────────────────────────────────────

def _routes_path(root: str, ep: str) -> str:
    return os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json")


def _load_routes(root: str, ep: str) -> Optional[Dict[str, Any]]:
    try:
        with open(_routes_path(root, ep), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _setting_value(root: str) -> Optional[str]:
    try:
        from settings import load_settings
        return load_settings(root).get(SETTING_KEY)
    except Exception:
        return None


def _primary_is_multishot(routes_payload: Optional[Mapping[str, Any]]) -> bool:
    """计划里至少一个 route 的 primary 后端属 MULTISHOT_NATIVE_BACKENDS。"""
    if not isinstance(routes_payload, Mapping):
        return False
    try:
        from n2d_platform_profiles import MULTISHOT_NATIVE_BACKENDS, normalize_video_backend
    except Exception:
        return bool(routes_payload.get("multishot_groups"))
    for r in routes_payload.get("routes") or []:
        if not isinstance(r, Mapping):
            continue
        key = normalize_video_backend(str(r.get("primary_backend") or ""), default="")
        if key and key in MULTISHOT_NATIVE_BACKENDS:
            return True
    return bool(routes_payload.get("multishot_groups"))


def build(root: str, ep: str) -> Dict[str, Any]:
    root = root.rstrip("/")
    routes = _load_routes(root, ep)
    mode = setting_mode(_setting_value(root))
    setting_on = mode in {"on", "auto"}  # 记账：auto 与 on 都算「意图开」，最终仍需 backend_ok
    backend_ok = _primary_is_multishot(routes)
    active = setting_on and backend_ok
    notes: List[str] = []
    if routes is None:
        notes.append("缺 出视频/<集>/prompt/video_model_routes.json——先跑 n2d-model-router 再规划多镜。")
    elif mode == "off":
        notes.append("选择点『原生多镜生成』=关闭（显式逐镜独立出）；改 `自动`/`开启` 可让支持多镜的后端一次 co-generate 接力组、少出很多 clip。")
    elif mode == "auto" and not backend_ok:
        notes.append("选择点=自动，但 primary 后端非 multishot_native——本集无法一次 co-generate，仍逐镜独立出。")
    elif mode == "on" and not backend_ok:
        notes.append("选择点已开启但 primary 后端非 multishot_native——无法激活原生多镜，仍逐镜独立出。")
    elif active:
        candidate_groups = [
            g for g in (routes.get("multishot_groups") or [])
            if isinstance(g, Mapping) and len([m for m in (g.get("members") or []) if str(m)]) >= 2
        ]
        saved = sum(len([m for m in (g.get("members") or []) if str(m)]) - 1 for g in candidate_groups)
        if saved > 0:
            how = "自动（能力门控默认）" if mode == "auto" else "已开启"
            notes.append(
                f"原生多镜{how}：primary 后端支持，本集 {len(candidate_groups)} 组一次 co-generate，"
                f"约少出 {saved} 个 clip（组内接缝由模型内部消除）。要退回逐镜写 `原生多镜生成: 关闭`。"
            )
    plan = resolve_plan(routes or {}, active=active)
    try:
        from video_execution_adapter import execution_status
    except Exception:
        execution_status = None  # type: ignore
    ready_groups = 0
    for group in plan.get("groups") or []:
        status = execution_status(
            root, group.get("backend"), "",
            required_operations=("multishot_submit", "multishot_query"),
        ) if execution_status else {
            "state": "adapter_module_unavailable", "automated": False, "supports_multishot": False,
        }
        group["execution_adapter"] = status
        group["execution_ready"] = bool(status.get("automated") and status.get("supports_multishot"))
        group["execution_status"] = "ready" if group["execution_ready"] else "job_package_only"
        ready_groups += int(group["execution_ready"])
    plan.update({
        "kind": KIND, "version": 2, "root": root, "episode": ep,
        "setting_on": setting_on, "backend_multishot_native": backend_ok,
        "summary": {**summarize(plan), "execution_ready_groups": ready_groups}, "notes": notes,
    })
    if active and plan.get("groups") and not ready_groups:
        notes.append(
            "原生多镜能力已激活，但本机没有同时支持 multishot_submit/query 的 adapter v2；"
            "可先生成自包含 job package，实际提交需登记 wrapper 或转人工。"
        )
    return plan


def render_md(plan: Mapping[str, Any]) -> str:
    s = plan.get("summary", {})
    lines = [
        f"# 原生多镜执行计划 · {plan.get('episode')}",
        f"- 激活：{'是' if plan.get('active') else '否'}（选择点={plan.get('setting_on')} · 后端支持={plan.get('backend_multishot_native')}）",
        f"- 激活组：{s.get('group_count', 0)} · 可自动执行组：{s.get('execution_ready_groups', 0)} · 一次 co-generate 镜数：{s.get('co_generated_clips', 0)} · 模型消缝接缝：{s.get('model_handled_seam_count', 0)}",
        "",
    ]
    for g in plan.get("groups") or []:
        lines.append(f"- **{g['group_id']}**（{g.get('backend')}·≈{g.get('approx_seconds')}s·{g.get('execution_status', 'unknown')}）：{' → '.join(g['members'])}")
    for n in plan.get("notes") or []:
        lines.append(f"> {n}")
    return "\n".join(lines) + "\n"


def write_plan(root: str, ep: str, plan: Mapping[str, Any]) -> Dict[str, str]:
    out_dir = os.path.join(root.rstrip("/"), "出视频", ep, "prompt")
    os.makedirs(out_dir, exist_ok=True)
    jp = os.path.join(out_dir, "multishot_plan.json")
    mp = os.path.join(out_dir, "multishot_plan.md")
    with open(jp, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    with open(mp, "w", encoding="utf-8") as fh:
        fh.write(render_md(plan))
    return {"json": jp, "md": mp}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="原生多镜单次生成执行计划")
    ap.add_argument("root")
    ap.add_argument("ep")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    ep = ns.ep if str(ns.ep).startswith("第") else f"第{ns.ep}集"
    plan = build(ns.root, ep)
    if ns.write:
        paths = write_plan(ns.root, ep, plan)
        plan["_written"] = paths
    if ns.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        s = plan["summary"]
        print(f"原生多镜：激活={plan['active']} · 组={s['group_count']} · co-gen镜={s['co_generated_clips']}")
        for n in plan["notes"]:
            print(f"  · {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
