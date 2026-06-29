#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""场景几何一致性 —— floor_plan / doors_windows 的门窗结构像素核对（补「只验字段在不在」缺口）。

背景（2026-06 场景轴审计）：`constraints.floor_plan` / `doors_windows` / `screen_direction_rules` 此前
只在 gate 做**字段存在性** BLOCK——登记了就放行，从没人验证生成图里门窗真在 floor_plan 说的位置/朝向。
布局图 spatial_map 也喂给零代码。结果：反打能把同一房间拍成门开反向、窗户消失的「另一个房间」，
机检看不出（O2 dHash 自标定、不知 floor_plan；B1 纯文本声明）。

本模块把登记的结构开口（门/入口/窗/破顶开口）解析出**应在的画面侧**，再用 OWLv2 在场检测（复用 O3V 后端）
逐镜测门窗实际所在侧，**场景级**判定：某个登记开口在该场景所有镜里都没出现在它应在的侧 → 几何漂
（核心场景 block，其余 warn）。这是 floor_plan 的像素核对靶，不再只验字段在不在。

纯逻辑（开口解析 + 场景级一致性聚合）有 pytest；OWLv2 侧位检测走可选后端，缺则只产探针 + advisory，
不凭空 block（设计律 C4 优雅降级）。侧位需要框质心（position-aware 后端 `backends/scene_geometry_owlv2.py`）；
缺该后端时退化为「门窗是否出现」的在场核对。

用法：python3 scene_geometry_conformance.py <作品根> 第N集 [--write] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import scene_consistency as sc

SCENE_GEOMETRY_KIND = "n2d_scene_geometry"
# 门窗结构开口词（出现在 floor_plan / doors_windows 文本里）→ 归一标签 + OWLv2 检测短语
_OPENING_LEXICON = (
    ("门", "门|入口|大门|殿门|院门|door|gate|entrance", "door"),
    ("窗", "窗|窗户|window", "window"),
    ("开口", "开口|破顶|天窗|缺口|破口|opening|skylight", "opening"),
)


# ── 纯逻辑（pytest 覆盖）────────────────────────────────────────────────────────

def _side_in(text: str) -> Dict[str, Optional[str]]:
    """从一小段文本里取画面侧 {h: left|right|None, v: top|bottom|None}。"""
    h: Optional[str] = None
    v: Optional[str] = None
    if re.search(r"画左|左下|左上|左侧|左方|左边|screen[\s-]*left", text, re.I):
        h = "left"
    elif re.search(r"画右|右下|右上|右侧|右方|右边|screen[\s-]*right", text, re.I):
        h = "right"
    if re.search(r"上方|顶部|破顶|头顶|top|overhead|上沿", text, re.I):
        v = "top"
    elif re.search(r"下方|底部|地面|脚下|bottom|floor", text, re.I):
        v = "bottom"
    return {"h": h, "v": v}


def parse_openings(doors_windows_text: str = "", floor_plan_text: str = "") -> List[Dict[str, Any]]:
    """登记文本 → 结构开口清单 [{label, phrase, h, v}]（纯函数·可测）。

    在 doors_windows（含画侧）+ floor_plan（含网格位/特征）里找门/窗/开口词，就近取画面侧。
    解析不到任何开口 → 空表（不瞎编）。"""
    out: List[Dict[str, Any]] = []
    blob = str(doors_windows_text or "")
    # 按分句切，让「主要入口在画左下；破顶开口在上方」各自带自己的侧位
    segments = re.split(r"[；;。\n]", blob) + re.split(r"[，,；;。\n]", str(floor_plan_text or ""))
    seen: set = set()
    for seg in segments:
        if not seg.strip():
            continue
        side = _side_in(seg)
        for label, pat, phrase in _OPENING_LEXICON:
            if re.search(pat, seg, re.I):
                key = (label, side["h"], side["v"])
                if key in seen:
                    continue
                seen.add(key)
                out.append({"label": label, "phrase": phrase, "h": side["h"], "v": side["v"]})
    # 去无侧位冗余：某 label 已有带侧位条目时，丢它的 (label,None,None) 兜底条目（如 floor_plan「殿门」无侧）。
    has_side = {o["label"] for o in out if o["h"] or o["v"]}
    return [o for o in out if not (o["label"] in has_side and not o["h"] and not o["v"])]


def conformance_findings(scene: str, openings: Sequence[Mapping[str, Any]],
                         detected: Mapping[str, Sequence[str]], *, is_core: bool = False) -> List[dict]:
    """场景级几何一致性判定（纯函数·可测）。

    openings：parse_openings 的登记开口（带应在侧 h）。
    detected：{label: [本场景各镜检测到该结构的画面侧...]}（position-aware 后端产；侧位未知用 'unknown'）。
    判据：登记开口在该场景**所有**镜里都没出现在它应在的侧（h）→ 几何漂；core→block else warn。
    detected 为空（后端没跑）→ 不产 finding（不凭空 block）。"""
    if not detected:
        return []
    rows: List[dict] = []
    for op in openings:
        label = str(op.get("label") or "")
        want_h = op.get("h")
        sides = list(detected.get(label) or [])
        if not sides:
            # 整个场景都没检测到这类结构 → 它从场景消失了
            rows.append(_geom_row(scene, label, want_h, "缺席", is_core,
                                  f"登记结构「{label}」在场景[{scene}]所有镜均未检出"))
            continue
        if want_h in ("left", "right"):
            # 有侧位要求：若检测到的侧里从无应在侧（且不是 unknown 占位）→ 朝向漂
            concrete = [s for s in sides if s in ("left", "right")]
            if concrete and want_h not in concrete:
                rows.append(_geom_row(scene, label, want_h, "朝向漂", is_core,
                                      f"登记结构「{label}」应在画面{('左' if want_h=='left' else '右')}，"
                                      f"实测各镜均在 {('/'.join(sorted(set(concrete))))}"))
    return rows


def _geom_row(scene: str, label: str, want_h, kind: str, is_core: bool, msg: str) -> dict:
    return {
        "scene": scene, "label": label, "expected_side": want_h, "kind": kind,
        "verdict": "block" if is_core else "warn",
        "message": msg + "——floor_plan/门窗几何不符；回 n2d-image 对齐场景定妆 spatial_layout/布局图，"
                         "或确认是否 allowed_variations 内的合理变化。",
    }


# ── I/O driver ─────────────────────────────────────────────────────────────────

def build_manifest(root: str, ep: str) -> dict:
    registry = sc._load_asset_registry(root)
    smap = sc._scene_of_shot(root, ep)
    probes: List[dict] = []
    scene_openings: Dict[str, List[Dict[str, Any]]] = {}
    for png, scene in sorted(smap.items()):
        aid = sc._match_asset_id(scene, registry)
        asset = registry.get(aid) if aid else None
        cons = (asset or {}).get("constraints") if isinstance(asset, Mapping) else None
        if not isinstance(cons, Mapping):
            continue
        openings = parse_openings(str(cons.get("doors_windows") or ""), str(cons.get("floor_plan") or ""))
        if not openings:
            continue
        scene_openings.setdefault(scene, openings)
        rel = os.path.join("出图", ep, png)
        if os.path.isfile(os.path.join(root, rel)):
            probes.append({"shot": png, "scene": scene, "image": rel,
                           "expected_openings": [{"label": o["label"], "phrase": o["phrase"],
                                                  "expected_h": o["h"]} for o in openings]})
    return {"kind": SCENE_GEOMETRY_KIND, "root": root, "episode": ep,
            "scene_openings": scene_openings, "probes": probes, "detected": {}, "findings": []}


def _run_batch(path: str) -> bool:
    cmd = os.environ.get("N2D_SCENE_GEOMETRY_BATCH_CMD", "").strip()
    if not cmd:
        return False
    try:
        subprocess.run([*cmd.split(), path], timeout=3600, check=True)
        return True
    except Exception as exc:
        print(f"[scene_geometry][warn] batch 后端调用失败（忽略）：{exc}", file=sys.stderr)
        return False


def _core_scenes(root: str) -> List[str]:
    try:
        from n2d_cross_episode import core_scene_names
        return core_scene_names(root)
    except Exception:
        return []


def aggregate(manifest: Mapping[str, Any], core_scenes: Iterable[str] = ()) -> List[dict]:
    """读后端回填的 detected（{scene: {label: [sides]}}）→ 逐场景 conformance_findings。"""
    detected_all = manifest.get("detected") if isinstance(manifest.get("detected"), Mapping) else {}
    scene_openings = manifest.get("scene_openings") if isinstance(manifest.get("scene_openings"), Mapping) else {}
    core = [c for c in (core_scenes or ()) if c]
    out: List[dict] = []
    for scene, openings in scene_openings.items():
        is_core = any(scene in c or c in scene for c in core)
        detected = detected_all.get(scene) if isinstance(detected_all.get(scene), Mapping) else {}
        out.extend(conformance_findings(scene, openings, detected, is_core=is_core))
    return out


def write(root: str, ep: str) -> str:
    manifest = build_manifest(root, ep)
    path = os.path.join(root, "生产数据", f"scene_geometry_{ep}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    ran = _run_batch(path)
    if ran:
        try:
            manifest = json.load(open(path, encoding="utf-8"))
        except Exception:
            pass
    manifest["detector_ran"] = ran
    manifest["findings"] = aggregate(manifest, core_scenes=_core_scenes(root))
    if not ran:
        manifest.setdefault("notes", []).append(
            "未配置门窗侧位检测后端（N2D_SCENE_GEOMETRY_BATCH_CMD）；只产开口探针清单，"
            "门窗几何是否符 floor_plan 仍由人判兜底。装好 position-aware OWLv2 后端后复跑即机检。")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="场景几何(floor_plan/门窗) 一致性 manifest/runner")
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
        print(json.dumps(json.load(open(path, encoding="utf-8")), ensure_ascii=False, indent=2))
        return 0
    manifest = build_manifest(root, ns.episode)
    print(json.dumps(manifest, ensure_ascii=False, indent=2) if ns.json
          else f"scenes={len(manifest['scene_openings'])} probes={len(manifest['probes'])} "
               f"detector={'on' if os.environ.get('N2D_SCENE_GEOMETRY_BATCH_CMD') else 'off(manifest only)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
