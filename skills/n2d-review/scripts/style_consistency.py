#!/usr/bin/env python3
"""风格一致性机检（S1·补 style_contract 落地后仍零机检的盲区）。

风格刚升成 gate 强制契约（storyboard.style_contract + 「本集基础视觉风格契约」），
但 face/outfit/scene/temporal 各有检测器，**风格漂移没有**——契约管"写没写"，
管不了"产出有没有漂离所选风格"。本脚本补这条 QA 闭环。

机制（与 face/outfit/scene 同构·自标定 flag-band，不写死阈值）：
  风格是**整幅属性**，且本集所有镜头应风格一致。每镜取**风格指纹**：
    饱和度直方图（低饱和写实 vs 高饱和二次元/霓虹）
    + 明度直方图（高调/低调/对比）
    + 边缘密度（照片级细节 vs 扁平插画/线条）。
  每镜对**其余镜头**的平均余弦 = 该镜"风格内聚度"；
  内聚度 < 本集内聚度中位数−margin 的镜头 = 风格离群（某镜突然照片感/突然插画/突然高饱和）。

依赖 Pillow（缺则优雅跳过，交人判读「本集基础视觉风格契约」并排看）。纯数学部分带 pytest。

用法：python3 style_consistency.py <作品根> 第N集 [--margin 0.06] [--bins 16] [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from typing import Dict, List, Optional, Sequence

import face_consistency as fc  # 复用 cosine / band / _sev

DEFAULT_MARGIN = 0.06
DEFAULT_BINS = 16
EDGE_WEIGHT_DIMS = 4   # 边缘密度作为 4 个重复维并入指纹，给它 ~1/8 权重（不喧宾夺主）


# ---------- 纯数学（无依赖 · pytest 覆盖） ----------

def channel_hist(values: Sequence[float], bins: int = DEFAULT_BINS) -> List[float]:
    """单通道(0..1)归一化直方图。空输入→全 0。"""
    hist = [0.0] * bins
    n = 0
    for v in values:
        idx = int(v * bins)
        if idx >= bins:
            idx = bins - 1
        if idx < 0:
            idx = 0
        hist[idx] += 1.0
        n += 1
    if n > 0:
        hist = [x / n for x in hist]
    return hist


def style_fingerprint(sat_hist: Sequence[float], val_hist: Sequence[float], edge_density: float) -> List[float]:
    """拼成风格指纹：饱和直方图 + 明度直方图 + 边缘密度(重复 EDGE_WEIGHT_DIMS 维加权)。"""
    return list(sat_hist) + list(val_hist) + [float(edge_density)] * EDGE_WEIGHT_DIMS


def cohesion_scores(fingerprints: Sequence[Sequence[float]]) -> List[float]:
    """每个指纹对其余指纹的平均余弦（风格内聚度）。单镜→[1.0]，无→[]。"""
    n = len(fingerprints)
    if n <= 1:
        return [1.0] * n
    out: List[float] = []
    for i in range(n):
        sims = [fc.cosine(fingerprints[i], fingerprints[j]) for j in range(n) if j != i]
        out.append(sum(sims) / len(sims) if sims else 1.0)
    return out


def median(values: Sequence[float]) -> float:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return 0.0
    m = len(vals) // 2
    return vals[m] if len(vals) % 2 else (vals[m - 1] + vals[m]) / 2.0


def style_band(cohesion: float, med: float, margin: float = DEFAULT_MARGIN) -> str:
    """风格离群分档（median-中心）：内聚度本就有一半低于中位，所以只有**显著**低于中位才算漂。
    ok = ≥ median−margin（正常波动）；warn = [median−2·margin, median−margin)；block = < median−2·margin（真离群）。
    """
    if cohesion >= med - margin:
        return "ok"
    if cohesion >= med - 2 * margin:
        return "warn"
    return "block"


# ── 跨集画风基线（集级指纹 vs 基线集）────────────────────────────────────────
# 集内自标定抓"某镜突然漂"，抓不到"整集一起漂"（跨后端混跑/模型升级最常见）。
# 跨集对账：每集出图的平均风格指纹 vs 基线集（默认最早一集）的 cosine 距。
CROSS_EP_WARN = 0.06
CROSS_EP_BLOCK = 0.15


def mean_fingerprint(fps: Sequence[Sequence[float]]) -> Optional[List[float]]:
    """多镜指纹的逐维均值 = 集级风格指纹。空/维度不齐 → None。纯函数。"""
    fps = [f for f in fps if f]
    if not fps:
        return None
    dim = len(fps[0])
    if any(len(f) != dim for f in fps):
        return None
    return [sum(f[i] for f in fps) / len(fps) for i in range(dim)]


def cross_band(dist: Optional[float], warn: float = CROSS_EP_WARN, block: float = CROSS_EP_BLOCK) -> str:
    """集间指纹距 → ok/warn/block；算不出 → skipped（不臆造）。纯函数。"""
    if dist is None:
        return "skipped"
    return "block" if dist > block else "warn" if dist > warn else "ok"


def _ep_num(ep: str) -> int:
    m = re.search(r"第(\d+)集", ep)
    return int(m.group(1)) if m else 10**9


def cross_analyze(root: str, bins: int = DEFAULT_BINS, baseline_ep: Optional[str] = None) -> dict:
    """跨集画风对账：各集出图均值指纹 vs 基线集。"""
    res: dict = {"available": None, "baseline": None, "episodes": [], "notes": []}
    if not _probe_pillow():
        res["available"] = False
        res["notes"].append("未装 Pillow——跨集画风对账跳过，交人判抽帧并排看。")
        return res
    res["available"] = True
    per_ep: List[tuple] = []
    for d in sorted(glob.glob(os.path.join(root, "出图", "第*集")), key=lambda p: _ep_num(os.path.basename(p))):
        ep = os.path.basename(d)
        fps = [fp for fp in (_fingerprint(p, bins) for p in _shot_pngs(root, ep)) if fp is not None]
        mfp = mean_fingerprint(fps)
        if mfp is not None:
            per_ep.append((ep, mfp, len(fps)))
    if len(per_ep) < 2:
        res["notes"].append(f"可对账集 {len(per_ep)} <2——跨集画风对账需至少两集出图。")
        return res
    base = next((x for x in per_ep if x[0] == baseline_ep), per_ep[0])
    res["baseline"] = base[0]
    for ep, mfp, n in per_ep:
        dist = max(0.0, 1.0 - fc.cosine(base[1], mfp))
        res["episodes"].append({"episode": ep, "shots": n, "dist": round(dist, 4),
                                "verdict": "baseline" if ep == base[0] else cross_band(dist)})
    return res


# ---------- 图像（需 Pillow · 缺则 None） ----------

def _probe_pillow() -> bool:
    try:
        import PIL  # noqa
        return True
    except Exception:
        return False


def _fingerprint(path: str, bins: int) -> Optional[List[float]]:
    try:
        from PIL import Image, ImageFilter  # type: ignore
    except Exception:
        return None
    try:
        im = Image.open(path).convert("RGB")
        im.thumbnail((128, 128))
        hsv = im.convert("HSV")
        px = list(hsv.getdata())
        sat = [s / 255.0 for (_h, s, _v) in px]
        val = [v / 255.0 for (_h, _s, v) in px]
        sat_h = channel_hist(sat, bins)
        val_h = channel_hist(val, bins)
        edges = im.convert("L").filter(ImageFilter.FIND_EDGES)
        ed = list(edges.getdata())
        edge_density = (sum(ed) / len(ed) / 255.0) if ed else 0.0
        return style_fingerprint(sat_h, val_h, edge_density)
    except Exception:
        return None


def _shot_pngs(root: str, ep: str) -> List[str]:
    """本集分镜首帧 PNG（含尾帧——尾帧也是剧情帧、同风格）。"""
    d = os.path.join(root, "出图", ep, "图片")
    return sorted(p for p in glob.glob(os.path.join(d, "*.png")))


def analyze(root: str, ep: str, margin: float = DEFAULT_MARGIN, bins: int = DEFAULT_BINS) -> dict:
    res: dict = {"available": None, "margin": margin, "floor": None, "shots": [], "notes": []}
    if not _probe_pillow():
        res["available"] = False
        res["notes"].append("风格一致性机检已跳过（未装 Pillow）——风格漂移暂由人判对照「本集基础视觉风格契约」并排看。")
        return res
    res["available"] = True
    pngs = _shot_pngs(root, ep)
    fps: List[List[float]] = []
    kept: List[str] = []
    for p in pngs:
        fp = _fingerprint(p, bins)
        if fp is not None:
            fps.append(fp)
            kept.append(os.path.basename(p))
    if len(fps) < 3:
        res["notes"].append(f"本集可评镜头 {len(fps)} <3，风格内聚度无统计意义，跳过（风格漂移靠人判）。")
        return res
    cohesion = cohesion_scores(fps)
    floor = median(cohesion)
    res["floor"] = round(floor, 4)
    for name, c in zip(kept, cohesion):
        res["shots"].append({"png": name, "cohesion": round(c, 4), "floor": round(floor, 4),
                             "verdict": style_band(c, floor, margin)})
    return res


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode", nargs="?", help="--cross 模式下可省略")
    ap.add_argument("--margin", type=float, default=DEFAULT_MARGIN)
    ap.add_argument("--bins", type=int, default=DEFAULT_BINS)
    ap.add_argument("--cross", action="store_true", help="跨集画风对账（各集均值指纹 vs 基线集）")
    ap.add_argument("--baseline", help="--cross 时指定基线集（默认最早一集），如 第1集")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    if ns.cross:
        res = cross_analyze(ns.root.rstrip("/"), ns.bins, ns.baseline)
        if ns.json:
            print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
        print(f"=== 跨集画风对账（集级指纹 vs 基线 {res.get('baseline')}）：{ns.root} ===")
        for n in res["notes"]:
            print("ℹ️ " + n)
        nblk = 0
        for e in res["episodes"]:
            v = e["verdict"]
            if v == "block":
                nblk += 1
            mark = {"baseline": "📌基线", "ok": "✅", "warn": "⚠️整集轻漂", "block": "⛔整集画风漂"}.get(v, v)
            print(f"{mark} {e['episode']}（{e['shots']} 镜）距基线 {e['dist']}")
        print(f"\n整集画风漂 🔴 {nblk} · 共对账 {len(res['episodes'])} 集")
        return 1 if nblk else 0
    if not ns.episode:
        ap.error("非 --cross 模式需要 episode 参数")
    res = analyze(ns.root.rstrip("/"), ns.episode, ns.margin, ns.bins)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 风格一致性机检（自标定内聚度 · margin {res['margin']}）：{ns.root} {ns.episode} ===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    if not res["available"] or res["floor"] is None:
        return 0
    print(f"  本集风格内聚度中位 floor={res['floor']}（评 {len(res['shots'])} 镜）")
    nblk = 0
    icon = {"block": "⛔风格跳变", "warn": "⚠️轻漂", "ok": "✅"}
    for s in res["shots"]:
        v = s["verdict"]
        if v == "block":
            nblk += 1
        if v in ("block", "warn"):
            print(f"{icon[v]} {s['png']} · 风格内聚 {s['cohesion']} < floor {s['floor']}（疑似突然偏离本集风格）")
    print(f"\n风格跳变 🔴 {nblk} · 共评 {len(res['shots'])} 镜")
    return 1 if nblk else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
