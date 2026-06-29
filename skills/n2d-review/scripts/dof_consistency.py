#!/usr/bin/env python3
"""景深/虚化一致性机检（DOF1·镜头光学的"景深档"维度）——补 shot_scale 只管景别(脸占画幅)、
不管"背景虚化程度"的盲区。

2026 实战缺口：同一场景里，AI 出图常一会儿深焦（背景和主体一样清）、一会儿奶油浅景深（背景糊成一片），
观感像"换了台相机/换了个空间"，是公认却没人专测的破沉浸点。face/outfit/hair/scene 都不测景深。

机制（与 scene/hair 同构·自标定 flag-band，不写死绝对景深值）：
  对每镜图取**景深代理** = 背景区清晰度 / 主体区清晰度（清晰度用灰度梯度能量近似）。
    深焦镜：背景≈主体清晰 → 比值高（≈1）；浅景深镜：背景糊 → 比值低。
  按场景分组（复用 scene_consistency 的镜头→场景映射），组内取景深代理中位数当"本场景景深基线"，
  某镜比值偏离中位数超 margin → 该镜景深档与同场景其它镜不一致（深焦↔浅景深横跳）🟡。
  组 <3 镜统计不稳跳过；缺 Pillow 优雅跳过交人判。

诚实边界：这是**景深代理**（中心=主体、四周=背景的几何启发 + 梯度能量近似），不解析真实光圈/焦段，
也不做主体分割；命中只作"可疑→人并排看"的初筛，warn-only（正当的浅景深特写本就和深焦全景不同档，
靠"同场景内"分组 + 自标定中位数压误报）。纯数学（区域清晰度/景深比/中位数/离群）无依赖、带 pytest。

用法：python3 dof_consistency.py <作品根> 第N集 [--margin 0.3] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Sequence

import scene_consistency as scn  # 复用 _scene_of_shot（镜头→场景映射）+ _probe_pillow

DEFAULT_MARGIN = 0.30   # 景深代理比值偏离同场景中位数超过这个绝对量 = 景深档不一致
DEFAULT_GRID = 64       # 灰度缩放边长（梯度能量统计用）
CENTER_FRAC = 0.5       # 主体区取中心比例（其余为背景区）


# ---------- 纯数学（无依赖 · pytest 覆盖） ----------

def median(xs: Sequence[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def _grad_energy(gray: Sequence[Sequence[float]], x0: int, y0: int, x1: int, y1: int) -> float:
    """区域 [y0:y1, x0:x1] 的平均梯度能量（|dx|+|dy|）——清晰度近似。空区域返回 0。"""
    n = 0
    total = 0.0
    for y in range(y0, y1):
        for x in range(x0, x1):
            gx = abs(gray[y][x] - gray[y][x + 1]) if x + 1 < len(gray[0]) else 0.0
            gy = abs(gray[y][x] - gray[y + 1][x]) if y + 1 < len(gray) else 0.0
            total += gx + gy
            n += 1
    return total / n if n else 0.0


def dof_ratio(gray: Sequence[Sequence[float]], center_frac: float = CENTER_FRAC) -> Optional[float]:
    """景深代理 = 背景区清晰度 / 主体区清晰度。主体区=中心 center_frac 矩形，背景区=四周环带。
    主体区清晰度≈0（全糊镜）→ None（无法判，不假报）。比值越低=背景越糊=越浅景深。纯函数·可测。"""
    h = len(gray)
    w = len(gray[0]) if h else 0
    if h < 4 or w < 4:
        return None
    cw, ch = int(w * center_frac), int(h * center_frac)
    cx0, cy0 = (w - cw) // 2, (h - ch) // 2
    cx1, cy1 = cx0 + cw, cy0 + ch
    center = _grad_energy(gray, cx0, cy0, cx1, cy1)
    if center <= 1e-6:
        return None
    # 背景区 = 全图能量 - 中心能量贡献（用四周环带四块平均近似）
    bands = [
        _grad_energy(gray, 0, 0, w, cy0),       # 上
        _grad_energy(gray, 0, cy1, w, h),       # 下
        _grad_energy(gray, 0, cy0, cx0, cy1),   # 左
        _grad_energy(gray, cx1, cy0, w, cy1),   # 右
    ]
    bands = [b for b in bands if b is not None]
    bg = sum(bands) / len(bands) if bands else 0.0
    return bg / center


# ---------- 图像（需 Pillow） ----------

def _gray_grid(path: str, grid: int = DEFAULT_GRID) -> Optional[List[List[float]]]:
    try:
        from PIL import Image  # type: ignore
        im = Image.open(path).convert("L").resize((grid, grid))
        px = list(im.getdata())
        return [[float(px[y * grid + x]) for x in range(grid)] for y in range(grid)]
    except Exception:
        return None


def _dof_proxy(path: str) -> Optional[float]:
    g = _gray_grid(path)
    return dof_ratio(g) if g is not None else None


def _norm_dof_intent(value: object) -> str:
    """注册 depth_intent → 归一档（shallow/deep/medium/""）。纯函数·可测。"""
    t = str(value or "").strip().lower()
    if any(m in t for m in ("shallow", "浅", "奶油", "虚化", "bokeh")):
        return "shallow"
    if any(m in t for m in ("deep", "深焦", "全清", "pan_focus", "deep_focus")):
        return "deep"
    if any(m in t for m in ("medium", "中", "适中")):
        return "medium"
    return ""


def dof_intent_violation(ratio: float, intent: object, *,
                         shallow_max: float = 0.85, deep_min: float = 0.55) -> Optional[str]:
    """实测景深比(背景清晰/主体清晰) vs 注册 depth_intent 是否矛盾 → 原因串或 None。纯函数·可测。
    浅景深应低(背景虚)、深焦应高(背景清)；medium 不强判。"""
    norm = _norm_dof_intent(intent)
    if norm == "shallow" and ratio > shallow_max:
        return f"登记浅景深(背景应虚化)但实测背景偏清(景深比 {round(ratio, 3)}>{shallow_max})"
    if norm == "deep" and ratio < deep_min:
        return f"登记深焦(背景应清晰)但实测背景偏糊(景深比 {round(ratio, 3)}<{deep_min})"
    return None


def dof_profile_rows(root: str, ep: str) -> List[dict]:
    """场景 dof_profile.depth_intent 锁（per-scene 景深锁）：逐镜实测景深比 vs 注册意图，矛盾=warn。

    补 DOF1（analyze）只做**集内自比**、无 per-scene 注册锚的缺口——把每镜景深档锚到声明的场景景深意图
    （跨镜/跨集一致到同一意图）。dof_profile 可放 scene_dna.dof_profile 或 constraints.dof_profile（任一）。
    只对登记了 depth_intent 的场景生效；需 Pillow。warn 级（景深代理是几何启发·不硬阻断）。"""
    if not scn._probe_pillow():
        return []
    registry = scn._load_asset_registry(root)
    smap = scn._scene_of_shot(root, ep)
    rows: List[dict] = []
    for png, scene in sorted(smap.items()):
        aid = scn._match_asset_id(scene, registry)
        asset = registry.get(aid) if aid else None
        if not isinstance(asset, dict):
            continue
        prof = (asset.get("scene_dna") or {}).get("dof_profile")
        if not isinstance(prof, dict):
            prof = (asset.get("constraints") or {}).get("dof_profile")
        if not isinstance(prof, dict) or not prof.get("depth_intent"):
            continue
        r = _dof_proxy(os.path.join(root, "出图", ep, png))
        if r is None:
            continue
        why = dof_intent_violation(r, prof.get("depth_intent"))
        if why:
            rows.append({"png": png, "scene": scene, "verdict": "warn",
                         "message": (f"场景[{scene}] 景深锁矛盾：{why}——对齐登记 dof_profile.depth_intent，"
                                     f"或确认意图后改注册。"),
                         "ratio": round(r, 3), "intent": _norm_dof_intent(prof.get("depth_intent"))})
    return rows


def analyze(root: str, ep: str, margin: float = DEFAULT_MARGIN) -> dict:
    res: dict = {"available": scn._probe_pillow(), "groups": {}, "shots": [], "notes": []}
    if not res["available"]:
        res["notes"].append("景深一致性机检已跳过（未装 Pillow）——景深档横跳暂由人判并排读图。")
        return res
    smap = scn._scene_of_shot(root, ep)
    groups: Dict[str, List[str]] = {}
    for png, scene in smap.items():
        if os.path.exists(os.path.join(root, "出图", ep, png)):
            groups.setdefault(scene, []).append(png)
    for scene, pngs in sorted(groups.items()):
        ratios = {p: _dof_proxy(os.path.join(root, "出图", ep, p)) for p in pngs}
        ratios = {p: r for p, r in ratios.items() if r is not None}
        if len(ratios) < 3:
            res["groups"][scene] = {"shots": len(ratios), "skipped": "组<3镜"}
            continue
        med = median(list(ratios.values()))
        res["groups"][scene] = {"shots": len(ratios), "median_ratio": round(med, 3)}
        for p, r in sorted(ratios.items()):
            dev = abs(r - med)
            verdict = "warn" if dev > margin else "ok"
            shot = {"png": p, "scene": scene, "ratio": round(r, 3), "median": round(med, 3),
                    "verdict": verdict}
            if verdict == "warn":
                kind = "深焦(背景偏清)" if r > med else "浅景深(背景偏糊)"
                shot["message"] = (f"{p}：景深档与同场景其它镜不一致——本镜偏{kind}"
                                   f"（景深比 {round(r,3)} vs 场景中位 {round(med,3)}）；"
                                   f"同场景深焦↔浅景深横跳像换相机，人核对是否有意，否则统一景深档重出。")
            res["shots"].append(shot)
    return res


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="景深/虚化一致性机检（DOF1）")
    ap.add_argument("root")
    ap.add_argument("ep")
    ap.add_argument("--margin", type=float, default=DEFAULT_MARGIN)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    report = analyze(args.root, args.ep, margin=args.margin)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if not report.get("available"):
        print("· " + "；".join(report.get("notes", []) or ["跳过"]))
        return 0
    warns = [s for s in report["shots"] if s.get("verdict") == "warn"]
    print(f"# 景深一致性（DOF1）：🟡景深档横跳 {len(warns)}")
    for s in warns:
        print(f"🟡 {s.get('message')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
