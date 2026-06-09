#!/usr/bin/env python3
"""糊/低质无参考质检（N4）——商用审片 12 类含「糊」，本脚本把它脚本化。

无参考清晰度用 **Laplacian 方差**（图像二阶差分的方差）：越糊→高频越少→方差越低。
绝对阈值因画风/分辨率漂，所以**自标定**：拿本集所有镜头图的 Laplacian 方差求中位数，
显著低于中位数的镜判为「相对糊」（关键镜更严）。与一致性正交，同属「崩脸/糊」族。

依赖 Pillow（缺则优雅跳过）。纯数学（laplacian_variance/median/blur_band）无依赖、带 pytest。

用法：python3 quality_check.py <作品根> 第N集 [--block-frac 0.4] [--warn-frac 0.6] [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import List, Optional, Sequence

DEFAULT_BLOCK_FRAC = 0.40   # < 中位数*0.40 → 🔴 明显糊
DEFAULT_WARN_FRAC = 0.60    # < 中位数*0.60 → 🟡 偏糊


# ---------- 纯数学（无依赖 · pytest 覆盖） ----------

def laplacian_variance(gray: Sequence[Sequence[float]]) -> float:
    """gray = 2D 灰度(行优先)。对内部像素算 4-邻 Laplacian(4*c-上-下-左-右)，返回其方差。
    平坦图→0；边缘/细节越多→越大。尺寸 <3x3 返回 0。"""
    h = len(gray)
    if h < 3:
        return 0.0
    w = len(gray[0])
    if w < 3:
        return 0.0
    vals = []
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            lap = 4.0 * gray[y][x] - gray[y-1][x] - gray[y+1][x] - gray[y][x-1] - gray[y][x+1]
            vals.append(lap)
    if not vals:
        return 0.0
    mean = sum(vals) / len(vals)
    return sum((v - mean) ** 2 for v in vals) / len(vals)


def median(xs: Sequence[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def blur_band(var: float, ref_median: float,
              block_frac: float = DEFAULT_BLOCK_FRAC, warn_frac: float = DEFAULT_WARN_FRAC) -> str:
    """相对本集中位数定档。ref_median<=0（无参考）→ 'ok'（不误杀）。"""
    if ref_median <= 0:
        return "ok"
    if var < ref_median * block_frac:
        return "block"
    if var < ref_median * warn_frac:
        return "warn"
    return "ok"


# ---------- 图像（需 Pillow） ----------

def _gray_2d(path: str, size: int = 128) -> Optional[List[List[float]]]:
    try:
        from PIL import Image  # type: ignore
        im = Image.open(path).convert("L")
        im.thumbnail((size, size))
        w, h = im.size
        px = list(im.getdata())
        return [[float(px[y * w + x]) for x in range(w)] for y in range(h)]
    except Exception:
        return None


def _probe_pillow() -> bool:
    try:
        import PIL  # noqa
        return True
    except Exception:
        return False


def _key_shots(root: str, ep: str) -> set:
    """从 00_总览.md「关键镜」段或 01 prompt 的 🔑 标记里粗取关键镜 PNG 名（糊得更严）。"""
    keys = set()
    p = os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")
    if os.path.isfile(p):
        import re
        for blk in re.split(r"(?m)(?=^## )", open(p, encoding="utf-8").read()):
            if "🔑" in (blk.splitlines()[0] if blk.strip() else ""):
                m = re.search(r"出图/[^/]+/([^`』\s]+\.png)", blk)
                if m:
                    keys.add(m.group(1))
    return keys


def analyze(root: str, ep: str, block_frac: float = DEFAULT_BLOCK_FRAC,
            warn_frac: float = DEFAULT_WARN_FRAC) -> dict:
    res: dict = {"available": _probe_pillow(), "median": None, "shots": [], "notes": []}
    if not res["available"]:
        res["notes"].append("糊检已跳过（未装 Pillow）——清晰度/糊脸暂由人判。")
        return res
    pngs = sorted(glob.glob(os.path.join(root, "出图", ep, "*.png")))
    if not pngs:
        res["notes"].append("本集无分镜 PNG。")
        return res
    keys = _key_shots(root, ep)
    var_by = {}
    for p in pngs:
        g = _gray_2d(p)
        if g is not None:
            var_by[os.path.basename(p)] = laplacian_variance(g)
    if not var_by:
        res["notes"].append("无法读图算清晰度。")
        return res
    med = median(list(var_by.values()))
    res["median"] = round(med, 2)
    for name, var in sorted(var_by.items()):
        is_key = name in keys
        # 关键镜门槛收紧一档（warn_frac 当 block_frac 用）
        v = blur_band(var, med, block_frac if not is_key else warn_frac,
                      warn_frac if not is_key else min(0.8, warn_frac + 0.15))
        if v != "ok":
            res["shots"].append({"png": name, "var": round(var, 2), "key": is_key, "verdict": v})
    return res


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--block-frac", type=float, default=DEFAULT_BLOCK_FRAC)
    ap.add_argument("--warn-frac", type=float, default=DEFAULT_WARN_FRAC)
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode, ns.block_frac, ns.warn_frac)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 糊/低质无参考质检 (N4·自标定中位数)：{ns.root} {ns.episode} ===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    if res["median"] is not None:
        print(f"  本集清晰度中位数 Laplacian方差={res['median']}")
    nb = 0
    icon = {"block": "⛔糊", "warn": "⚠️偏糊"}
    for s in res["shots"]:
        if s["verdict"] == "block":
            nb += 1
        print(f"{icon[s['verdict']]} {s['png']}{'·🔑关键镜' if s['key'] else ''}: 清晰度 {s['var']} (中位数 {res['median']})")
    print(f"\n明显糊 🔴 {nb} · 标出 {len(res['shots'])} 镜")
    return 1 if nb else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
