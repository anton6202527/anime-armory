#!/usr/bin/env python3
"""服装/配色一致性机检（N1·脸之外的漂移）——补 face_consistency 只测脸的盲区。

2026 实战：脸锁住了，**头发/服装/配色**仍各自漂（主角夹克色到第 4 个 clip 就变）。
本脚本对每个含角色镜头的**主色分布**打分，治"服装色/配色跨镜漂移"。

机制（与 face_consistency 同构·自标定 flag-band，不写死阈值）：
  对角色 c 的定妆组（主/侧/半身/全身）各取**加权色相直方图**（按 饱和度×明度 加权，
  压低灰/暗背景，聚焦有色衣物）；组内互相余弦的最小值 = 该角色"配色下限"地板 floor_c。
  对镜头图 s（属角色 c）：score = 直方图余弦(s, 半身定妆 or 主参考)
    ≥floor_c 🟢 / [floor_c-margin,floor_c) 🟡 / <floor_c-margin 🔴(服装/配色漂)。

  **二次相对校准（减噪·与 scene_consistency 同构）**：上面拿"镜头整帧 vs 中性灰底定妆整帧"
  算绝对相似度，戏剧布光/CU 构图会把同角色整组镜一起拉低 → 误报。所以再按"同角色镜组相对离群"
  二次校准（见 relative_calibrate）：整组一起低（场景污染）放行，只报相对本角色明显偏低的镜；
  镜组 <3 张无统计基础时 block 降 warn。只下调误报、不新增漏报。

依赖 Pillow（缺则优雅跳过，交人判并排读图）。纯数学部分（直方图/余弦/分档/相对校准）无依赖、带 pytest。

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
# 相对离群二次校准（治"整帧调色板被场景灯光/构图拉低"的假漂移）：
# outfit 老逻辑拿"镜头整帧 vs 中性灰底定妆整帧"算绝对相似度，戏剧布光/CU 构图天然把整组拉低，
# 误报成片。与 scene_consistency 同构——只把"相对本角色镜组明显偏低"的镜判漂，整组一致放行。
DEFAULT_REL_MARGIN = 0.15   # 低于同角色镜组中位这么多才算相对漂移；整组一起低（场景污染）不触发
DEFAULT_MIN_GROUP = 3       # 镜组够大才有统计基础下 block；<3 时 palette 分不清漂移 vs 构图/灯光 → 降 warn


# ---------- 纯数学（无依赖 · pytest 覆盖） ----------

def _median(xs: Sequence[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def relative_calibrate(verdict: str, score: float, group_scores: Sequence[float],
                       rel_margin: float = DEFAULT_REL_MARGIN,
                       min_group: int = DEFAULT_MIN_GROUP) -> str:
    """把绝对 verdict 按"同角色镜组相对离群"二次校准。**只下调误报，从不上调**：
    - 镜组 ≥ min_group：只有 score 明显低于组中位（median−score > rel_margin）才保留 block/warn；
      否则整组一致（场景灯光把所有镜一起拉低，≠服装漂）→ 放行 ok。
    - 镜组 < min_group：1–2 张 palette 分不清"服装漂"还是"构图/灯光" → block 降 warn（交人判，不强制重生成）。
    纯函数·可测。"""
    if verdict == "ok":
        return "ok"
    if len(group_scores) >= min_group:
        if (_median(group_scores) - score) <= rel_margin:
            return "ok"
        return verdict
    return "warn" if verdict == "block" else verdict

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


def analyze(root: str, ep: str, margin: float = DEFAULT_MARGIN, bins: int = DEFAULT_BINS,
            rel_margin: float = DEFAULT_REL_MARGIN, min_group: int = DEFAULT_MIN_GROUP) -> dict:
    sets = fc.discover_costume_sets(root)
    res: dict = {"available": None, "margin": margin, "rel_margin": rel_margin,
                 "min_group": min_group, "characters": {}, "shots": [], "notes": []}
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

    # 二次相对校准：按角色镜组抑制"整组被场景灯光/构图拉低"的假漂移（见 relative_calibrate）。
    from collections import defaultdict
    group: Dict[str, List[float]] = defaultdict(list)
    for s in res["shots"]:
        group[s["char"]].append(s["score"])
    for s in res["shots"]:
        new_v = relative_calibrate(s["verdict"], s["score"], group[s["char"]], rel_margin, min_group)
        if new_v != s["verdict"]:
            s["abs_verdict"] = s["verdict"]   # 留痕绝对判定，便于审计/调参
            s["verdict"] = new_v
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
    ap.add_argument("--rel-margin", type=float, default=DEFAULT_REL_MARGIN,
                    help="同角色镜组相对离群阈值（低于组中位这么多才判漂；调大=更宽松）")
    ap.add_argument("--min-group", type=int, default=DEFAULT_MIN_GROUP,
                    help="可下 block 的最小镜组数；不足则 block 降 warn")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode, ns.margin, ns.bins, ns.rel_margin, ns.min_group)
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
