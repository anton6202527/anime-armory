#!/usr/bin/env python3
"""场景/环境一致性机检（O2）——补最后一条仍只人判的视觉轴。

2026 环境一致性已是"expected"，但脸/服装/片内都有机检了，场景还只靠人判"场景漂移"。
本脚本对**同一场景的多个镜头**做结构一致性：用 dHash（感知哈希）量两两结构距离，
**自标定**——同场景镜头互相结构应相近，离群者(远高于本组中位距离)= 该镜背景画歪了。
不直接比 `定妆_<场景>.png`（场景镜有前景人物、与空场景定妆天然差很大，比组内更稳）。

依赖 Pillow（缺则优雅跳过）。纯数学（dhash_bits/hamming/is_outlier/median）无依赖、带 pytest。

用法：python3 scene_consistency.py <作品根> 第N集 [--factor 1.8] [--floor 12] [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from typing import Dict, List, Optional, Sequence

import face_consistency as fc  # 复用 cosine（光色指纹相似度）

DEFAULT_FACTOR = 1.8   # 镜头平均结构距离 > 组中位 * factor → 离群
DEFAULT_FLOOR = 12     # 且绝对汉明距 > floor（64 位里差这么多才算真漂，避免小组误杀）
TONE_FACTOR = 2.2      # 光色距离 > 组中位 * factor → 光位/色调离群（比结构更宽，光色波动天然大些）
TONE_FLOOR = 0.06      # 且绝对光色距离(1-cos) > floor，避免小组误杀
TONE_BINS = 10

_SCENE_WORDS = ("山洞", "花田", "破院", "山道", "偏厅", "大殿", "洞府", "山谷", "谷",
                "宫", "殿", "庭", "院", "厅", "房", "室", "林", "桥", "街", "城", "府", "门外", "广场")


# ---------- 纯数学（无依赖 · pytest 覆盖） ----------

def dhash_bits(gray: Sequence[Sequence[float]]) -> List[int]:
    """行内相邻比较的差分感知哈希位串：每行 左<右 记 1。HxW → H*(W-1) 位。"""
    bits: List[int] = []
    for row in gray:
        for x in range(len(row) - 1):
            bits.append(1 if row[x] < row[x + 1] else 0)
    return bits


def hamming(a: Sequence[int], b: Sequence[int]) -> int:
    """等长位串汉明距；长度不等取较短长度比较（容错）。"""
    return sum(1 for p, q in zip(a, b) if p != q)


def median(xs: Sequence[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    m = n // 2
    return s[m] if n % 2 else (s[m - 1] + s[m]) / 2.0


def is_outlier(value: float, group_median: float, factor: float = DEFAULT_FACTOR,
               floor: float = DEFAULT_FLOOR) -> bool:
    """离群 = 同时 超组中位*factor 且 超绝对 floor。"""
    return value > group_median * factor and value > floor


# ---------- 图像（需 Pillow） ----------

def _dhash_image(path: str) -> Optional[List[int]]:
    try:
        from PIL import Image  # type: ignore
        im = Image.open(path).convert("L").resize((9, 8))
        w, h = im.size
        px = list(im.getdata())
        gray = [[float(px[y * w + x]) for x in range(w)] for y in range(h)]
        return dhash_bits(gray)  # 8*(9-1)=64 位
    except Exception:
        return None


def _probe_pillow() -> bool:
    try:
        import PIL  # noqa
        return True
    except Exception:
        return False


def _tone_fp(path: str, bins: int = TONE_BINS) -> Optional[List[float]]:
    """光位/色调指纹：明度直方图（主光强度·高调低调）+ 饱和度加权色相直方图（场景色调）。
    同一场景跨镜应一致——某镜光打错方向/色温跳/调色跳 → 该指纹离群（光位锚的可机检代理）。"""
    try:
        from PIL import Image  # type: ignore
        im = Image.open(path).convert("RGB"); im.thumbnail((96, 96))
        hsv = im.convert("HSV"); px = list(hsv.getdata())
        vh = [0.0] * bins; hh = [0.0] * bins; tot = 0.0
        for h, s, v in px:
            vi = min(int(v / 256 * bins), bins - 1); vh[vi] += 1.0
            w = (s / 255.0) * (v / 255.0)
            if w > 0:
                hi = min(int(h / 256 * bins), bins - 1); hh[hi] += w; tot += w
        n = len(px) or 1
        vh = [x / n for x in vh]
        hh = [x / tot for x in hh] if tot > 0 else hh
        return vh + hh
    except Exception:
        return None


def _scene_of_shot(root: str, ep: str) -> Dict[str, str]:
    """每镜 PNG → 它引用的场景定妆名（取 01_分镜出图.md 参考图行里含场景词的 定妆_<X>）。"""
    p = os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")
    out: Dict[str, str] = {}
    if not os.path.isfile(p):
        return out
    for blk in re.split(r"(?m)(?=^## )", open(p, encoding="utf-8").read()):
        if not blk.strip().startswith("## "):
            continue
        mt = re.search(r"出图/[^/]+/([^`』\s]+\.png)", blk)
        if not mt:
            continue
        png = mt.group(1)
        m = re.search(r"(?ms)(?:\*\*)?参考图(?:\*\*)?.*?(?=^###\s+|^##\s+|\Z)", blk)
        refs = m.group(0) if m else ""
        scenes = [s for s in re.findall(r"定妆_([^`\s，。、,）)]+)", refs)
                  if any(w in s for w in _SCENE_WORDS)]
        if scenes:
            out[png] = scenes[0]
    return out


def analyze(root: str, ep: str, factor: float = DEFAULT_FACTOR, floor: float = DEFAULT_FLOOR) -> dict:
    res: dict = {"available": _probe_pillow(), "groups": {}, "shots": [], "notes": []}
    if not res["available"]:
        res["notes"].append("场景一致性机检已跳过（未装 Pillow）——背景漂移暂由人判并排读图。")
        return res
    smap = _scene_of_shot(root, ep)
    # 按场景分组
    groups: Dict[str, List[str]] = {}
    for png, scene in smap.items():
        full = os.path.join(root, "出图", ep, png)
        if os.path.exists(full):
            groups.setdefault(scene, []).append(png)
    for scene, pngs in sorted(groups.items()):
        hashes = {p: _dhash_image(os.path.join(root, "出图", ep, p)) for p in pngs}
        hashes = {p: h for p, h in hashes.items() if h is not None}
        if len(hashes) < 3:   # 组太小，统计不稳，跳过（少于3镜无法定离群）
            res["groups"][scene] = {"shots": len(hashes), "skipped": "组<3镜"}
            continue
        # 每镜对组内其他镜的平均汉明距
        names = list(hashes)
        avg = {}
        for p in names:
            ds = [hamming(hashes[p], hashes[q]) for q in names if q != p]
            avg[p] = sum(ds) / len(ds)
        gmed = median(list(avg.values()))
        res["groups"][scene] = {"shots": len(names), "median_dist": round(gmed, 1)}
        for p in names:
            if is_outlier(avg[p], gmed, factor, floor):
                res["shots"].append({"png": p, "scene": scene, "kind": "结构", "avg_dist": round(avg[p], 1),
                                     "group_median": round(gmed, 1), "verdict": "warn"})
        # ③ 光位/色调离群（同场景跨镜光打错/色调跳——光位锚的可机检代理）
        tfps = {p: _tone_fp(os.path.join(root, "出图", ep, p)) for p in names}
        tfps = {p: f for p, f in tfps.items() if f is not None}
        if len(tfps) >= 3:
            tnames = list(tfps)
            tavg = {p: sum(1.0 - fc.cosine(tfps[p], tfps[q]) for q in tnames if q != p) / (len(tnames) - 1)
                    for p in tnames}
            tmed = median(list(tavg.values()))
            for p in tnames:
                if is_outlier(tavg[p], tmed, TONE_FACTOR, TONE_FLOOR):
                    res["shots"].append({"png": p, "scene": scene, "kind": "光色", "avg_dist": round(tavg[p], 3),
                                         "group_median": round(tmed, 3), "verdict": "warn"})
    return res


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--factor", type=float, default=DEFAULT_FACTOR)
    ap.add_argument("--floor", type=float, default=DEFAULT_FLOOR)
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode, ns.factor, ns.floor)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 场景/环境一致性机检（同场景结构离群·自标定）：{ns.root} {ns.episode} ===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    for s in res["shots"]:
        if s.get("kind") == "光色":
            print(f"⚠️ {s['png']} · 场景[{s['scene']}] 光色离群 dist {s['avg_dist']} ≫ 组中位 {s['group_median']}（疑光位/色调跳：光打错向/色温跳/调色跳）")
        else:
            print(f"⚠️ {s['png']} · 场景[{s['scene']}] 结构离群 dist {s['avg_dist']} ≫ 组中位 {s['group_median']}（疑背景漂移）")
    nstruct = sum(1 for s in res["shots"] if s.get("kind") != "光色")
    ntone = sum(1 for s in res["shots"] if s.get("kind") == "光色")
    print(f"\n场景漂移疑似 🟡 结构 {nstruct} · 光色 {ntone} · 共 {len(res['groups'])} 个场景组")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
