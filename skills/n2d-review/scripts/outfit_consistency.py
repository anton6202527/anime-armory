#!/usr/bin/env python3
"""服装/配色一致性机检（N1·脸之外的漂移）——补 face_consistency 只测脸的盲区。

2026 实战：脸锁住了，**头发/服装/配色**仍各自漂（主角夹克色到第 4 个 clip 就变）。
本脚本对每个含角色镜头的**主色分布**打分，治"服装色/配色跨镜漂移"。

机制（与 face_consistency 同构·自标定 flag-band，不写死阈值）：
  对角色 c 的定妆组（主/侧/半身/全身）各取**加权色相直方图**（按 饱和度×明度 加权，
  压低灰/暗背景，聚焦有色衣物）；组内互相余弦的最小值 = 该角色"配色下限"地板 floor_c。
  对镜头图 s（属角色 c）：score = 直方图余弦(s, 半身定妆 or 主参考)
    ≥floor_c 🟢 / [floor_c-margin,floor_c) 🟡 / <floor_c-margin 🔴(服装/配色漂)。

依赖 Pillow（缺则优雅跳过，交人判并排读图）。纯数学部分（直方图/余弦/分档）无依赖、带 pytest。

用法：python3 outfit_consistency.py <作品根> 第N集 [--margin 0.10] [--bins 24] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Sequence

import face_consistency as fc  # 复用 cosine / calibrate_floor / band / 资产发现

DEFAULT_MARGIN = 0.10
DEFAULT_BINS = 24


# ---------- 纯数学（无依赖 · pytest 覆盖） ----------

def weighted_hue_hist(hsv_samples: Sequence[Sequence[float]], bins: int = DEFAULT_BINS) -> List[float]:
    """hsv_samples: 每项 (h,s,v) 均 ∈[0,1]。按 s*v 加权累进色相直方图并归一化。
    灰/暗像素(s≈0 或 v≈0)权重≈0，不污染配色判断。全无权重时返回全 0。"""
    hist = [0.0] * bins
    total = 0.0
    for h, s, v in hsv_samples:
        w = s * v
        if w <= 0:
            continue
        idx = int(h * bins)
        if idx >= bins:
            idx = bins - 1
        hist[idx] += w
        total += w
    if total > 0:
        hist = [x / total for x in hist]
    return hist


def hist_sim(a: Sequence[float], b: Sequence[float]) -> float:
    """直方图相似度（余弦，复用 fc.cosine）；全零向量→0。"""
    return fc.cosine(a, b)


# ---------- 图像（需 Pillow · 缺则 None） ----------

def _palette_hist(path: str, bins: int) -> Optional[List[float]]:
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return None
    try:
        im = Image.open(path).convert("RGB")
        im.thumbnail((128, 128))
        hsv = im.convert("HSV")
        px = list(hsv.getdata())  # (H,S,V) 0..255
        samples = [(h / 255.0, s / 255.0, v / 255.0) for (h, s, v) in px]
        return weighted_hue_hist(samples, bins)
    except Exception:
        return None


def _outfit_ref(variants: Dict[str, str]) -> Optional[str]:
    """配色基准优先 半身/全身（锁服装），退而求其次 主参考。"""
    for k in ("半身", "全身", "主", "侧"):
        if k in variants:
            return variants[k]
    return None


def analyze(root: str, ep: str, margin: float = DEFAULT_MARGIN, bins: int = DEFAULT_BINS) -> dict:
    sets = fc.discover_costume_sets(root)
    res: dict = {"available": None, "margin": margin, "characters": {}, "shots": [], "notes": []}
    if not _probe_pillow():
        res["available"] = False
        res["notes"].append("服装/配色机检已跳过（未装 Pillow）——服装色/发型漂移暂由人判并排读图覆盖。")
        return res
    res["available"] = True

    char_floor: Dict[str, float] = {}
    char_ref_hist: Dict[str, List[float]] = {}
    for char, variants in sets.items():
        hists = {k: _palette_hist(p, bins) for k, p in variants.items()}
        ref_path = _outfit_ref(variants)
        ref_hist = _palette_hist(ref_path, bins) if ref_path else None
        intra = []
        if ref_hist is not None:
            char_ref_hist[char] = ref_hist
            for k, h in hists.items():
                if h is not None and h is not ref_hist:
                    intra.append(hist_sim(ref_hist, h))
        char_floor[char] = fc.calibrate_floor(intra, fallback=0.85)  # 配色直方图同人通常很高，地板偏高
        res["characters"][char] = {"floor": round(char_floor[char], 4), "intra_pairs": len(intra)}

    smap = fc.shot_character_map(root, ep)
    for png, chars in sorted(smap.items()):
        full = os.path.join(root, "出图", ep, png)
        if not os.path.exists(full):
            continue
        h = _palette_hist(full, bins)
        if h is None:
            continue
        worst = None
        for c in chars:
            if c in char_ref_hist:
                sc = hist_sim(h, char_ref_hist[c])
                fl = char_floor.get(c, 0.85)
                v = fc.band(sc, fl, margin)
                row = {"char": c, "score": round(sc, 4), "floor": round(fl, 4), "verdict": v}
                if worst is None or fc._sev(v) > fc._sev(worst["verdict"]):
                    worst = row
        if worst:
            res["shots"].append({"png": png, **worst})
    return res


def _probe_pillow() -> bool:
    try:
        import PIL  # noqa
        return True
    except Exception:
        return False


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--margin", type=float, default=DEFAULT_MARGIN)
    ap.add_argument("--bins", type=int, default=DEFAULT_BINS)
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode, ns.margin, ns.bins)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 服装/配色一致性机检（自标定 · margin {res['margin']}）：{ns.root} {ns.episode} ===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    if not res["available"]:
        return 0
    for c, info in res["characters"].items():
        print(f"  角色 {c}: 配色 floor={info['floor']}（定妆组对 {info['intra_pairs']}）")
    nblk = 0
    icon = {"block": "⛔配色漂", "warn": "⚠️轻漂", "ok": "✅"}
    for s in res["shots"]:
        v = s["verdict"]
        if v == "block":
            nblk += 1
        if v in ("block", "warn"):
            print(f"{icon[v]} {s['png']} · {s['char']} 配色相似 {s['score']} < floor {s['floor']}")
    print(f"\n配色漂 🔴 {nblk} · 共评 {len(res['shots'])} 镜")
    return 1 if nblk else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
