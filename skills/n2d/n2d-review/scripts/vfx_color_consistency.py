#!/usr/bin/env python3
"""特效颜色/拖尾窜色机检（VFXC·补 asset_lifecycle 只校验 vfx_params 是不是 dict 的盲区）。

2026 实战缺口：仙侠/系统流的剑气、系统面板、妖纹光效，跨镜常一会儿青白一会儿偏紫偏红——
asset_registry 早就用 `vfx_params.color_target`(HSV) 声明了"这道光该是什么色"，却**没有任何脚本真去
量两张图里特效的实际色相**，是接近 orphan 的登记字段。face/outfit/scene/dof 都不测特效色。剑气从青白
窜成火红、系统面板从靛蓝飘成紫，是观众一眼"换了法宝/换了世界"的破沉浸点。

机制（与 dof/scene 同构·窗口内 vivid 像素色相质心 + 自标定中位数 + 登记色锚双轨）：
  只对 type=vfx 且声明了 `vfx_params.color_target` 的资产跑。按 `01_分镜出图.md` 找引用该 VFX 的镜
  （复用 multimodal 的资产→镜映射）+ 共享定妆板。每张图取 HSV，在**登记目标色相 ±窗口**内取
  足够鲜艳(s≥sat_floor,v≥val_floor)的像素，算它们的**环形色相质心**(turn) + 覆盖率：
    - 覆盖率 < floor（太细/被压暗，测不到该色）→ 该镜跳过测量，只记 note，不误报"丢特效"。
    - 可测镜 ≥2：组内质心中位数=本特效色基线，某镜质心偏离 > drift_margin → 跨镜窜色 🟡。
    - 组内质心中位数 vs 登记 color_target 偏离 > anchor_margin → 整体偏离登记色 ℹ️（info）。

诚实边界：这是**窗口内主色质心**启发（不分割特效形状、不解析材质），窗口外的极端窜色表现为"该镜测不到
该色"而非高漂移读数；warn-only，靠"同特效跨镜"分组 + 自标定中位数压误报。色相用环形均值/距离正确处理
红色 0/360 缠绕。纯数学(环形统计/中位数/离群)无依赖、带 pytest；像素采样需 Pillow，缺则优雅跳过交人判。

用法：python3 vfx_color_consistency.py <作品根> 第N集 [--drift-margin-deg 20] [--json]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Dict, List, Optional, Sequence, Tuple

import multimodal_consistency as mm  # 复用 split_blocks / target_from_block / asset_registry_*
from pillow_compat import pixel_data

KIND = "n2d_vfx_color_consistency"
VERSION = 1

DEFAULT_SAT_FLOOR = 0.35      # 像素被视为"鲜艳特效色"的最低饱和度
DEFAULT_VAL_FLOOR = 0.28      # 最低明度（滤掉黑/暗背景）
DEFAULT_WINDOW_DEG = 55.0     # 登记目标色相两侧多宽内的像素算"这道特效的色"
DEFAULT_COVERAGE_FLOOR = 0.0015  # 窗口内 vivid 像素占比低于此 = 测不到该色（不误报）
DEFAULT_DRIFT_MARGIN_DEG = 20.0  # 某镜质心偏离同特效跨镜中位数超过此 = 窜色 warn
DEFAULT_ANCHOR_MARGIN_DEG = 32.0  # 跨镜中位数偏离登记 color_target 超过此 = 整体偏离 info


# ---------- 纯数学（环形色相统计 · 无依赖 · pytest 覆盖） ----------

def hue_to_turn(deg: float) -> float:
    """0-360 度 → 0-1 turn（取模）。"""
    return (float(deg) % 360.0) / 360.0


def hue_dist_deg(a_turn: float, b_turn: float) -> float:
    """两个色相(turn 0-1)的环形距离，返回 0-180 度（正确处理红色 0/1 缠绕）。"""
    d = abs((a_turn - b_turn) % 1.0)
    d = min(d, 1.0 - d)
    return d * 360.0


def circular_mean_turn(turns: Sequence[float], weights: Optional[Sequence[float]] = None) -> Optional[float]:
    """加权环形均值色相(turn)；空/零权重→None。"""
    sx = sy = 0.0
    for i, t in enumerate(turns):
        w = 1.0 if weights is None else float(weights[i])
        if w <= 0:
            continue
        ang = 2.0 * math.pi * float(t)
        sx += w * math.cos(ang)
        sy += w * math.sin(ang)
    if sx == 0.0 and sy == 0.0:
        return None
    ang = math.atan2(sy, sx)
    return (ang / (2.0 * math.pi)) % 1.0


def circular_median_turn(turns: Sequence[float]) -> Optional[float]:
    """环形中位数近似：取使到其它点环形距离和最小的那个样本点（稳健、避免线性中位数缠绕错）。"""
    pts = [float(t) % 1.0 for t in turns]
    if not pts:
        return None
    best, best_cost = pts[0], None
    for c in pts:
        cost = sum(hue_dist_deg(c, p) for p in pts)
        if best_cost is None or cost < best_cost:
            best, best_cost = c, cost
    return best


def window_centroid(hsv_samples: Sequence[Sequence[float]], center_turn: float, *,
                    half_width_turns: float, sat_floor: float, val_floor: float) -> Tuple[Optional[float], float]:
    """登记目标色相 ±窗口内、足够鲜艳的像素的(环形色相质心 turn, 覆盖率)。

    hsv_samples: 每项 (h,s,v) ∈[0,1]。覆盖率 = 命中像素数 / 总像素数。无命中→(None,0)。纯函数·可测。"""
    hues: List[float] = []
    wts: List[float] = []
    total = len(hsv_samples)
    if total == 0:
        return None, 0.0
    for h, s, v in hsv_samples:
        if s < sat_floor or v < val_floor:
            continue
        if hue_dist_deg(h, center_turn) > half_width_turns * 360.0:
            continue
        hues.append(h)
        wts.append(s * v)
    coverage = len(hues) / total
    return circular_mean_turn(hues, wts), coverage


# ---------- 图像采样（需 Pillow） ----------

def _probe_pillow() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except Exception:
        return False


def _hsv_samples(path: str) -> Optional[List[Tuple[float, float, float]]]:
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return None
    try:
        im = Image.open(path).convert("RGB")
        im.thumbnail((160, 160))
        hsv = im.convert("HSV")
        return [(h / 255.0, s / 255.0, v / 255.0) for (h, s, v) in pixel_data(hsv)]
    except Exception:
        return None


def measure_png(path: str, target_turn: float, *, window_deg: float,
                sat_floor: float, val_floor: float) -> Optional[Dict[str, float]]:
    samples = _hsv_samples(path)
    if samples is None:
        return None
    centroid, coverage = window_centroid(
        samples, target_turn, half_width_turns=window_deg / 360.0,
        sat_floor=sat_floor, val_floor=val_floor,
    )
    return {"centroid_turn": centroid, "coverage": coverage}


# ---------- 装配（registry + 镜映射 → 测量 → 判定） ----------

def _vfx_assets_with_color(root: str) -> List[Dict[str, object]]:
    """asset_registry 里 type=vfx 且声明了 vfx_params.color_target(h) 的资产。"""
    try:
        data = json.load(open(mm.asset_registry_path(root), encoding="utf-8"))
    except Exception:
        return []
    out: List[Dict[str, object]] = []
    for a in (data.get("assets") if isinstance(data, dict) else []) or []:
        if not isinstance(a, dict) or str(a.get("type") or "").strip().lower() != "vfx":
            continue
        ct = ((a.get("vfx_params") or {}).get("color_target") or {}) if isinstance(a.get("vfx_params"), dict) else {}
        if not isinstance(ct, dict) or "h" not in ct:
            continue
        out.append({"id": str(a.get("id") or ""), "name": str(a.get("name") or ""),
                    "target_turn": hue_to_turn(ct.get("h", 0)), "target_h": ct.get("h")})
    return out


def _shared_plate(root: str, name: str) -> Optional[str]:
    if not name:
        return None
    p = os.path.join(root, "出图", "共享", "图片", f"定妆_{name}.png")
    return p if os.path.isfile(p) else None


def analyze(root: str, ep: str, *, drift_margin_deg: float = DEFAULT_DRIFT_MARGIN_DEG,
            anchor_margin_deg: float = DEFAULT_ANCHOR_MARGIN_DEG,
            window_deg: float = DEFAULT_WINDOW_DEG, sat_floor: float = DEFAULT_SAT_FLOOR,
            val_floor: float = DEFAULT_VAL_FLOOR, coverage_floor: float = DEFAULT_COVERAGE_FLOOR) -> dict:
    root = root.rstrip("/")
    res: dict = {"kind": KIND, "version": VERSION, "root": root, "episode": ep,
                 "available": _probe_pillow(), "groups": {}, "shots": [], "verdicts": [], "notes": []}
    if not res["available"]:
        res["notes"].append("特效窜色机检已跳过（未装 Pillow）；后续可接 CLIP/分割精确定位特效区。")
        return res
    vfx = _vfx_assets_with_color(root)
    if not vfx:
        res["notes"].append("无 type=vfx 且声明 color_target 的特效资产——本检不适用。")
        return res
    pp = os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")
    blocks = mm.split_blocks(open(pp, encoding="utf-8").read()) if os.path.isfile(pp) else []
    entries = mm.asset_registry_entries(root)

    # 镜 → 引用的 VFX id（复用 multimodal 的资产绑定）
    shot_refs: List[Tuple[str, str, List[str]]] = []  # (heading, png, vfx_ids)
    for blk in blocks:
        target = mm.target_from_block(root, ep, blk)
        if not target or not os.path.isfile(target):
            continue
        ids = [r for r in mm.asset_registry_refs_from_block(blk, entries) if r in {v["id"] for v in vfx}]
        if ids:
            shot_refs.append((blk.get("heading", ""), target, ids))

    for v in vfx:
        vid, target_turn = v["id"], float(v["target_turn"])
        pngs: List[Tuple[str, str]] = []  # (label, path)
        plate = _shared_plate(root, str(v["name"]))
        if plate:
            pngs.append((f"定妆_{v['name']}", plate))
        for heading, png, ids in shot_refs:
            if vid in ids:
                pngs.append((heading or os.path.basename(png), png))
        measured: List[Dict[str, object]] = []
        unmeasurable = 0
        for label, path in pngs:
            m = measure_png(path, target_turn, window_deg=window_deg, sat_floor=sat_floor, val_floor=val_floor)
            if m is None or m["centroid_turn"] is None or m["coverage"] < coverage_floor:
                unmeasurable += 1
                continue
            measured.append({"label": label, "png": os.path.basename(path),
                             "centroid_turn": m["centroid_turn"], "coverage": round(m["coverage"], 5)})
        group = {"vfx": vid, "name": v["name"], "target_h": v["target_h"],
                 "measured": len(measured), "unmeasurable": unmeasurable}
        if len(measured) < 2:
            group["skipped"] = "可测镜<2（特效太细/被压暗，跨镜窜色无法统计）"
            res["groups"][vid] = group
            continue
        baseline = circular_median_turn([float(m["centroid_turn"]) for m in measured])
        group["baseline_h"] = round(float(baseline) * 360.0, 1) if baseline is not None else None
        anchor_off = hue_dist_deg(baseline, target_turn) if baseline is not None else 0.0
        group["anchor_off_deg"] = round(anchor_off, 1)
        if anchor_off > anchor_margin_deg:
            res["notes"].append(
                f"{vid} {v['name']}：跨镜实测主色相 {group['baseline_h']}° 偏离登记 color_target {v['target_h']}° "
                f"达 {round(anchor_off,1)}°——整体偏离登记色，核对 vfx_params 或重出。")
        for m in measured:
            off = hue_dist_deg(float(m["centroid_turn"]), baseline)
            verdict = "warn" if off > drift_margin_deg else "ok"
            row = {"vfx": vid, "shot": m["label"], "png": m["png"],
                   "hue_deg": round(float(m["centroid_turn"]) * 360.0, 1),
                   "baseline_deg": group["baseline_h"], "drift_deg": round(off, 1),
                   "coverage": m["coverage"], "verdict": verdict,
                   "msg": (f"{vid} {v['name']} 特效色相 {round(float(m['centroid_turn'])*360.0,1)}° 偏离同特效跨镜基线 "
                           f"{group['baseline_h']}° 达 {round(off,1)}°（窜色：剑气/光效跨镜变色，破"
                           f"'同一道法术'感）" if verdict == "warn" else "")}
            res["shots"].append(row)
            res["verdicts"].append(verdict)
        res["groups"][vid] = group
    if not res["shots"] and not any("偏离登记色" in n for n in res["notes"]):
        res["notes"].append("特效色相跨镜一致（或可测镜不足）。")
    return res


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="特效颜色/拖尾窜色机检（VFXC）")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--drift-margin-deg", type=float, default=DEFAULT_DRIFT_MARGIN_DEG)
    ap.add_argument("--anchor-margin-deg", type=float, default=DEFAULT_ANCHOR_MARGIN_DEG)
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root, ns.episode, drift_margin_deg=ns.drift_margin_deg, anchor_margin_deg=ns.anchor_margin_deg)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    warns = sum(1 for v in res["verdicts"] if v == "warn")
    print(f"VFXC 特效窜色：{len(res['groups'])} 个特效组，窜色镜 {warns}")
    for n in res["notes"]:
        print(f"  - {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
