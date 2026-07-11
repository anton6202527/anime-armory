#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""场景生成侧锚定规划器 —— 场景的 reference_planner（与角色侧对称，补「生成侧场景锁」缺口）。

背景（2026-06 场景轴审计 + SOTA 对标）：角色有 Face Lock / Character ID / LoRA / reference_group /
anchor_sha 一整套**生成侧身份锁**——出图前就把「这是同一主体」喂给后端，所以不漂；场景此前只有
参考图 + shared_seed + 事后 QC，没有任何生成侧锁。2026 SOTA（Kling Director Mode 环境锚定、Veo
ingredients、场景 LoRA、reference-guided 多镜）做的正是**生成时把场景钉住**，而非事后检测。

本规划器把场景补齐到与角色对称的生成侧规划（纯计划产物·不改 storyboard·不碰花钱步骤）：
  #1 参考块纳入 `reference_group.spatial_map`(布局图) + `scene_atlas.base_views`(反打/侧视) —— 此前
     这俩是声明了却喂给零代码的死字段；现在每镜场景参考清单带上它们。
  #2 场景锁档位 scene_lock_tier（reference_plate → backend_subject → scene_lora），镜像角色
     image_lock_tier：后端支持主体库就走 backend_subject（让后端自己锁场景），核心×跨多集×无后端锁
     则建议升 scene_lora。
  #3 master establishing plate 锚定：同集某 LOC 用 ≥MASTER_ANCHOR_MIN_SHOTS 镜 → 设一张主全景 plate，
     其余镜条件在它上（环境锚定）；复活了 spatial_planner.py 那段「注入 LOC_X_MASTER 字段却无人消费」的死代码意图。
  #4 scene LoRA 升档建议：核心场景跨 ≥PROACTIVE_SCENE_EPISODE_THRESHOLD 集 × 无后端场景锁 → 在烧穿多集
     积分前建议训练 scene LoRA（镜像角色 lora_upgrade_candidates 的主动档）。

纯逻辑（tier/refs/master/lora 判定）有 pytest；driver 读 storyboard + asset_registry 产
`生产数据/scene_reference_plan_第N集.json/md`，供出图 prompt 组装与 gate「场景参考落实」消费。
数据不足一律不瞎编（空计划），缺后端优雅降级（仍出 reference_plate 计划）。

用法：python3 scene_reference_planner.py <作品根> 第N集 [--write] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

SCENE_REFERENCE_PLAN_KIND = "n2d_scene_reference_plan"
SCENE_LOCK_TIERS = ("reference_plate", "backend_subject", "scene_lora")
# 同集某 LOC 用 ≥ 这么多镜 → 值得先出一张 master 全景 plate 锚定其余镜（环境锚定·#3）。
MASTER_ANCHOR_MIN_SHOTS = 3
# 核心场景跨 ≥ 这么多集 × 无后端场景锁 → 主动建议 scene LoRA（不等漂移坐实·#4）。镜像角色 PROACTIVE 档。
PROACTIVE_SCENE_EPISODE_THRESHOLD = 3
_READY_LORA = ("ready", "registered", "validated", "deployed")
_READY_SUBJECT = ("ready", "registered", "validated", "deployed")


# ── 纯逻辑（pytest 覆盖）────────────────────────────────────────────────────────

def scene_lock_tier(*, backend_supports_subject: bool, scene_lora_status: str = "") -> str:
    """该 LOC 当前可用的最强生成侧场景锁档（镜像角色 image_lock_tier·纯函数）。

    scene_lora 已 ready/training → 'scene_lora'；否则后端支持主体库/参考组 → 'backend_subject'
    （让后端自己锁场景，最接近 Character ID）；都没有 → 'reference_plate'（只能靠参考图+seed）。"""
    if str(scene_lora_status).strip().lower() in _READY_LORA:
        return "scene_lora"
    if backend_supports_subject:
        return "backend_subject"
    return "reference_plate"


def should_suggest_scene_lora(*, is_core: bool, cross_eps: int,
                              backend_supports_subject: bool, scene_lora_status: str = "") -> bool:
    """主动 scene LoRA 升档建议（纯函数）：核心场景 × 跨 ≥阈值集 × 无后端主体锁 × 未上 LoRA。"""
    if str(scene_lora_status).strip().lower() in _READY_LORA:
        return False
    return bool(is_core) and int(cross_eps) >= PROACTIVE_SCENE_EPISODE_THRESHOLD and not backend_supports_subject


def plan_master_anchor(loc_id: str, intra_shots: int) -> Optional[str]:
    """同集 LOC 镜数 ≥ 阈值 → 返回该 LOC 的 master plate id（其余镜条件在它上·#3），否则 None。"""
    if int(intra_shots) >= MASTER_ANCHOR_MIN_SHOTS:
        return f"{loc_id}_MASTER"
    return None


def _ref_path(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        return str(value.get("path") or value.get("ref") or "").strip()
    return ""


def plan_scene_refs(loc_asset: Mapping[str, Any], master_anchor: Optional[str] = None,
                    *, master_anchor_planned: bool = True) -> List[Dict[str, Any]]:
    """该 LOC 每镜应携带的**场景参考槽**（纯函数·#1 的核心：纳入 spatial_map + base_views）。

    顺序按锚定强度：master 全景 plate（若有·#3）→ 场景定妆 primary → 布局图 spatial_map → 反打/侧视
    base_views → 光位锚 plate。weight 是建议 i2i 参考权重（让 prompt 组装/runner 有据可依，非硬绑）。"""
    rg = loc_asset.get("reference_group") if isinstance(loc_asset.get("reference_group"), Mapping) else {}
    atlas = loc_asset.get("scene_atlas") if isinstance(loc_asset.get("scene_atlas"), Mapping) else {}
    out: List[Dict[str, Any]] = []

    def add(slot: str, ref: str, weight: float, reason: str, *, planned: bool = False) -> None:
        if ref or planned:
            out.append({"slot": slot, "ref": ref, "weight": weight, "planned": not ref, "reason": reason})

    if master_anchor:
        add("master_plate", master_anchor, 0.4, "主全景 establishing plate：其余镜条件在它上锚定空间（环境锚定）",
            planned=master_anchor_planned)
    add("primary", _ref_path(rg.get("primary")), 0.45, "场景定妆主参考（空场景底板/主视角）")
    # #1：布局图（此前死字段）——锁门窗位置/空间几何，治反打把房间拍成另一个房间
    add("spatial_map", _ref_path(rg.get("spatial_map")), 0.3, "布局图 spatial_map：锁门窗朝向/floor_plan 几何")
    # #1：scene_atlas 多视角 base_views（反打/侧视）——锁「同一空间换机位」而非换房间
    base_views = atlas.get("base_views") if isinstance(atlas.get("base_views"), Mapping) else {}
    for key in ("reverse", "side", "front"):
        p = _ref_path(base_views.get(key))
        if p:
            add(f"base_view:{key}", p, 0.3, f"scene_atlas {key} 视角：锁同一空间换机位的一致性")
    add("lighting_plate", _ref_path(rg.get("lighting_plate")), 0.25, "光位锚 plate：锁主光方向/色温")
    return out


def plan_loc(loc_asset: Mapping[str, Any], *, intra_shots: int, cross_eps: int,
            backend_supports_subject: bool) -> Dict[str, Any]:
    """单个 LOC 的完整场景锚定计划（纯函数·组合 tier/master/refs/lora）。"""
    loc_id = str(loc_asset.get("id") or loc_asset.get("asset_id") or "")
    is_core = bool(loc_asset.get("core")) or str(loc_asset.get("tier") or "").strip().lower() == "core"
    lora = loc_asset.get("scene_lora") if isinstance(loc_asset.get("scene_lora"), Mapping) else {}
    subject = loc_asset.get("scene_subject") if isinstance(loc_asset.get("scene_subject"), Mapping) else {}
    lora_status = str(lora.get("status") or "")
    subject_status = str(subject.get("status") or "").strip().lower()
    subject_ready = backend_supports_subject and subject_status in _READY_SUBJECT
    tier = scene_lock_tier(backend_supports_subject=subject_ready, scene_lora_status=lora_status)
    master = plan_master_anchor(loc_id, intra_shots)
    rg = loc_asset.get("reference_group") if isinstance(loc_asset.get("reference_group"), Mapping) else {}
    master_ref = _ref_path(rg.get("master_plate")) or (_ref_path(rg.get("primary")) if master else "")
    suggest_lora = should_suggest_scene_lora(is_core=is_core, cross_eps=cross_eps,
                                             backend_supports_subject=backend_supports_subject,
                                             scene_lora_status=lora_status)
    return {
        "loc_id": loc_id,
        "is_core": is_core,
        "intra_shots": int(intra_shots),
        "cross_eps": int(cross_eps),
        "scene_lock_tier": tier,
        "master_anchor": master,
        "master_anchor_ref": master_ref,
        "refs": plan_scene_refs(
            loc_asset,
            master_anchor=master_ref or master,
            master_anchor_planned=bool(master and not master_ref),
        ),
        "suggest_scene_lora": suggest_lora,
        "subject_registration_required": bool(backend_supports_subject and not subject_ready),
        "subject_status": subject_status,
        "lora_status": lora_status,
    }


# ── I/O driver ─────────────────────────────────────────────────────────────────

def _load_registry(root: str) -> Dict[str, Mapping[str, Any]]:
    try:
        from n2d_contract import asset_registry_path  # n2d/_lib
        path = asset_registry_path(root)
    except Exception:
        path = os.path.join(root, "出图", "共享", "asset_registry.json")
    if not os.path.isfile(path):
        return {}
    try:
        data = json.load(open(path, encoding="utf-8"))
        return {str(a["id"]): a for a in data.get("assets", []) if isinstance(a, Mapping) and a.get("id")}
    except Exception:
        return {}


def _loc_usage(root: str, ep: str) -> Dict[str, int]:
    """每个 LOC 在本集 storyboard 里被多少镜引用（intra_shots）。"""
    sb_path = os.path.join(root, "脚本", ep, "storyboard.json")
    usage: Dict[str, int] = {}
    if not os.path.isfile(sb_path):
        return usage
    try:
        sb = json.load(open(sb_path, encoding="utf-8"))
    except Exception:
        return usage
    for clip in sb.get("clips", []):
        if not isinstance(clip, Mapping):
            continue
        loc = str(clip.get("location") or clip.get("loc") or "").strip()
        if loc:
            usage[loc] = usage.get(loc, 0) + 1
    return usage


def _cross_eps_count(root: str, loc_name: str) -> int:
    """该场景跨集出现集数（读 SCNX 自累积的 scene_ep_means.json；缺则按本集=1）。"""
    path = os.path.join(root, "生产数据", "scene_ep_means.json")
    if not os.path.isfile(path):
        return 1
    try:
        hist = json.load(open(path, encoding="utf-8"))
    except Exception:
        return 1
    n = sum(1 for ep_scenes in hist.values()
            if isinstance(ep_scenes, Mapping) and any(loc_name in s or s in loc_name for s in ep_scenes))
    return max(n, 1)


def _match_loc_asset(loc_name: str, registry: Mapping[str, Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
    for aid, asset in registry.items():
        if not aid.startswith("LOC_"):
            continue
        if loc_name in aid or loc_name in str(asset.get("name") or "") or aid.endswith(loc_name):
            return asset
    return registry.get(loc_name) if str(loc_name).startswith("LOC_") else None


def _backend_supports_subject(root: str) -> bool:
    """当前生图后端是否有「场景主体库/参考组」级身份机制（→ 可走 backend_subject 档）。"""
    try:
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib")))
        from n2d_settings import get_setting  # type: ignore
        from n2d_platform_profiles import VIDEO_BACKEND_PROFILES  # noqa: F401  (probe presence; tolerant)
    except Exception:
        return False
    try:
        backend = str(get_setting(root, "生图模型") or get_setting(root, "生图AI") or "").lower()
    except Exception:
        backend = ""
    # 已知带主体库/参考组的官方后端（保守白名单；未知后端按不支持，走 reference_plate 不高估）
    return any(k in backend for k in ("seedream", "kling", "可灵", "nano banana", "nano-banana", "seedance"))


def plan_episode_scenes(root: str, ep: str) -> Dict[str, Any]:
    registry = _load_registry(root)
    usage = _loc_usage(root, ep)
    backend_subject = _backend_supports_subject(root)
    plans: List[Dict[str, Any]] = []
    for loc_name, intra in sorted(usage.items()):
        asset = _match_loc_asset(loc_name, registry)
        if not isinstance(asset, Mapping):
            continue
        cross = _cross_eps_count(root, loc_name)
        plans.append(plan_loc(asset, intra_shots=intra, cross_eps=cross,
                              backend_supports_subject=backend_subject))
    return {
        "kind": SCENE_REFERENCE_PLAN_KIND,
        "root": root,
        "episode": ep,
        "backend_supports_subject": backend_subject,
        "master_anchors": [p["master_anchor"] for p in plans if p.get("master_anchor")],
        "scene_lora_suggestions": [p["loc_id"] for p in plans if p.get("suggest_scene_lora")],
        "locations": plans,
    }


def render_md(plan: Mapping[str, Any]) -> str:
    lines = [f"# 场景生成侧锚定计划 — {plan.get('episode')}", "",
             f"- 后端场景主体库：{'有(可走 backend_subject)' if plan.get('backend_supports_subject') else '无(走 reference_plate)'}",
             f"- master 全景锚：{('、'.join(plan.get('master_anchors') or [])) or '（无 LOC 达 3 镜）'}",
             f"- 建议 scene LoRA：{('、'.join(plan.get('scene_lora_suggestions') or [])) or '无'}", "",
             "| LOC | 核心 | 本集镜数 | 跨集 | 锁档 | master | 参考槽 |",
             "|---|---|---|---|---|---|---|"]
    for p in plan.get("locations", []):
        slots = "、".join(r["slot"] + ("(缺)" if r.get("planned") and not r.get("ref") else "") for r in p.get("refs", []))
        lines.append(f"| {p['loc_id']} | {'★' if p['is_core'] else '-'} | {p['intra_shots']} | {p['cross_eps']} "
                     f"| {p['scene_lock_tier']} | {p.get('master_anchor') or '-'} | {slots} |")
    return "\n".join(lines) + "\n"


def write(root: str, ep: str) -> str:
    plan = plan_episode_scenes(root, ep)
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    jpath = os.path.join(out_dir, f"scene_reference_plan_{ep}.json")
    with open(jpath, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(os.path.join(out_dir, f"scene_reference_plan_{ep}.md"), "w", encoding="utf-8") as fh:
        fh.write(render_md(plan))
    return jpath


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="场景生成侧锚定规划器")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = ns.root.rstrip("/")
    if ns.write:
        path = write(root, ns.episode)
        if not ns.json:
            print(path)
            return 0
    plan = plan_episode_scenes(root, ns.episode)
    print(json.dumps(plan, ensure_ascii=False, indent=2) if ns.json else render_md(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
