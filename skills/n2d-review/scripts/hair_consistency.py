#!/usr/bin/env python3
"""发型一致性机检（H1·脸/服装之外的第三类漂移）——补 face/outfit 都不专门看头发的盲区。

2026 实战：脸锁住、服装锁住，**发型/发色/发髻**仍会跨镜漂（披发→盘发、长发→短发、
发色偏移），尤其换装独立 form、近景表情镜、接力重出时。face_consistency 只喂脸框（基本不含
发型轮廓），outfit_consistency 取整帧主色（被衣服/背景稀释），二者都不专测头发。本脚本对每个
含角色镜头的**头部区域**取「发色 + 发型轮廓」复合指纹，治这第三类漂移。

机制（与 face/outfit 同构·自标定 flag-band，不写死阈值）：
  对角色 c 的定妆组（主/侧/半身/全身）各取**头部区域指纹** =
    发色（头部区 加权色相直方图，复用 outfit 的 weighted_hue_hist）
    ⊕ 发型轮廓（头部区 灰度边缘密度网格，归一化）；两段各自归一后按权重拼接。
  组内互相余弦最小值 = 该角色"发型下限"地板 floor_c（侧脸 vs 正脸发型轮廓天然偏低，故 fallback 偏低）。
  对镜头图 s（属角色 c）：score = 指纹余弦(s, 主参考/半身)
    ≥floor_c 🟢 / [floor_c-margin,floor_c) 🟡 / <floor_c-margin 🔴(发型/发色漂)。

  **二次相对校准（减噪）**：复用 outfit 的 relative_calibrate——同角色整组镜一起低（构图/景别/
  布光污染）放行，只报相对本角色镜组明显偏低的镜；镜组 <min_group 无统计基础时 block 降 warn。
  只下调误报、不新增漏报。

诚实边界：无 insightface 时头部区用**几何启发**（取画面上半中部）裁切，是粗筛初筛，不是像素级
发丝隔离；发型轮廓用整体边缘分布近似，不解析具体发式。命中只作"可疑→人判并排看"的初筛信号，
与 face/outfit 正交互补。依赖 Pillow（缺则优雅跳过，交人判）。纯数学部分（指纹拼接/归一/分档）
无依赖、带 pytest。

用法：python3 hair_consistency.py <作品根> 第N集 [--margin 0.08] [--bins 24] [--grid 6] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Sequence

import face_consistency as fc      # cosine / calibrate_floor / band / _sev / 资产发现 / 镜头映射
import outfit_consistency as oc    # weighted_hue_hist / relative_calibrate / _median / _probe_pillow

DEFAULT_MARGIN = 0.08              # 发型指纹比配色更易随角度波动 → margin 略小，配合相对校准减噪
DEFAULT_BINS = 24                  # 发色色相直方图分箱（与 outfit 对齐）
DEFAULT_GRID = 6                   # 发型轮廓边缘网格 GxG
DEFAULT_HUE_WEIGHT = 0.5          # 发色 vs 发型轮廓 在复合指纹里的权重（各 0.5）
DEFAULT_HEAD_FRAC = 0.55          # 头部区取画面上半比例（含发型轮廓，长发可延伸到中段）
# 发型轮廓含角度依赖（侧脸轮廓 ≠ 正脸），定妆组内地板天然低于配色 → fallback 给较低值，
# 避免把"同人不同角度"误判成漂；真漂靠 margin + 相对校准抓。
DEFAULT_FALLBACK_FLOOR = 0.55


# ---------- 纯数学（无依赖 · pytest 覆盖） ----------

def _unit_sum(vec: Sequence[float]) -> List[float]:
    """归一到和为 1；全零返回原样（全零向量保持全零，cosine 自然得 0）。"""
    total = float(sum(vec))
    if total <= 0:
        return [float(x) for x in vec]
    return [float(x) / total for x in vec]


def combine_fingerprint(hue_hist: Sequence[float], edge_grid: Sequence[float],
                        hue_weight: float = DEFAULT_HUE_WEIGHT) -> List[float]:
    """发色直方图 ⊕ 发型轮廓网格 → 复合指纹。两段**各自先归一**再按权重拼接，
    使任一段不因量纲压过另一段；cosine 在拼接向量上算。纯函数·可测。"""
    hw = max(0.0, min(1.0, hue_weight))
    hue = [x * hw for x in _unit_sum(hue_hist)]
    edge = [x * (1.0 - hw) for x in _unit_sum(edge_grid)]
    return hue + edge


def hair_sim(a: Sequence[float], b: Sequence[float]) -> float:
    """复合指纹相似度（余弦，复用 fc.cosine）；全零向量→0。"""
    return fc.cosine(a, b)


# ---------- 图像（需 Pillow · 缺则 None） ----------

def _head_box(w: int, h: int, head_frac: float = DEFAULT_HEAD_FRAC):
    """头部区几何启发框：画面上半 head_frac、水平居中 80%（压掉边缘背景）。
    无人脸检测下的粗定位——漫剧竖图人物头部多在上半中部。"""
    top = 0
    bottom = max(1, int(h * head_frac))
    margin = int(w * 0.10)
    return (margin, top, max(margin + 1, w - margin), bottom)


def _hair_fingerprint(path: str, bins: int, grid: int,
                      hue_weight: float, head_frac: float) -> Optional[List[float]]:
    try:
        from PIL import Image, ImageFilter  # type: ignore
    except Exception:
        return None
    try:
        im = Image.open(path).convert("RGB")
        im.thumbnail((160, 160))
        w, h = im.size
        head = im.crop(_head_box(w, h, head_frac))
        # 发色：头部区 HSV 加权色相直方图（复用 outfit 同款，s*v 加权压灰暗）
        hsv = head.convert("HSV")
        samples = [(hh / 255.0, ss / 255.0, vv / 255.0) for (hh, ss, vv) in hsv.getdata()]
        hue_hist = oc.weighted_hue_hist(samples, bins)
        # 发型轮廓：头部区灰度边缘 → GxG 网格 平均强度（结构指纹）
        edges = head.convert("L").filter(ImageFilter.FIND_EDGES)
        small = edges.resize((grid, grid))
        edge_grid = [float(p) for p in small.getdata()]
        return combine_fingerprint(hue_hist, edge_grid, hue_weight)
    except Exception:
        return None


def _hair_ref(variants: Dict[str, str]) -> Optional[str]:
    """发型基准优先 主参考/半身（正脸发式最完整），其次侧/全身。"""
    for k in ("主", "半身", "全身", "侧"):
        if k in variants:
            return variants[k]
    return None


def analyze(root: str, ep: str, margin: float = DEFAULT_MARGIN, bins: int = DEFAULT_BINS,
            grid: int = DEFAULT_GRID, hue_weight: float = DEFAULT_HUE_WEIGHT,
            head_frac: float = DEFAULT_HEAD_FRAC,
            rel_margin: float = oc.DEFAULT_REL_MARGIN,
            min_group: int = oc.DEFAULT_MIN_GROUP) -> dict:
    sets = fc.discover_costume_sets(root)
    res: dict = {"available": None, "margin": margin, "rel_margin": rel_margin,
                 "min_group": min_group, "characters": {}, "shots": [], "notes": []}
    if not oc._probe_pillow():
        res["available"] = False
        res["notes"].append("发型机检已跳过（未装 Pillow）——发型/发色漂移暂由人判并排读图覆盖。")
        return res
    res["available"] = True

    char_floor: Dict[str, float] = {}
    char_ref_fp: Dict[str, List[float]] = {}
    for char, variants in sets.items():
        fps = {k: _hair_fingerprint(p, bins, grid, hue_weight, head_frac) for k, p in variants.items()}
        ref_path = _hair_ref(variants)
        ref_fp = _hair_fingerprint(ref_path, bins, grid, hue_weight, head_frac) if ref_path else None
        intra = []
        if ref_fp is not None:
            char_ref_fp[char] = ref_fp
            for k, fp in fps.items():
                if fp is not None and fp is not ref_fp:
                    intra.append(hair_sim(ref_fp, fp))
        char_floor[char] = fc.calibrate_floor(intra, fallback=DEFAULT_FALLBACK_FLOOR)
        res["characters"][char] = {"floor": round(char_floor[char], 4), "intra_pairs": len(intra)}

    smap = fc.shot_character_map(root, ep)
    for png, chars in sorted(smap.items()):
        full = os.path.join(root, "出图", ep, png)
        if not os.path.exists(full):
            continue
        fp = _hair_fingerprint(full, bins, grid, hue_weight, head_frac)
        if fp is None:
            continue
        worst = None
        for c in chars:
            if c in char_ref_fp:
                sc = hair_sim(fp, char_ref_fp[c])
                fl = char_floor.get(c, DEFAULT_FALLBACK_FLOOR)
                v = fc.band(sc, fl, margin)
                row = {"char": c, "score": round(sc, 4), "floor": round(fl, 4), "verdict": v}
                if worst is None or fc._sev(v) > fc._sev(worst["verdict"]):
                    worst = row
        if worst:
            res["shots"].append({"png": png, **worst})

    # 二次相对校准：抑制"整组被景别/构图/布光拉低"的假漂移（复用 outfit 同款）。
    from collections import defaultdict
    group: Dict[str, List[float]] = defaultdict(list)
    for s in res["shots"]:
        group[s["char"]].append(s["score"])
    for s in res["shots"]:
        new_v = oc.relative_calibrate(s["verdict"], s["score"], group[s["char"]], rel_margin, min_group)
        if new_v != s["verdict"]:
            s["abs_verdict"] = s["verdict"]
            s["verdict"] = new_v
    return res


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--margin", type=float, default=DEFAULT_MARGIN)
    ap.add_argument("--bins", type=int, default=DEFAULT_BINS)
    ap.add_argument("--grid", type=int, default=DEFAULT_GRID)
    ap.add_argument("--hue-weight", type=float, default=DEFAULT_HUE_WEIGHT,
                    help="发色 vs 发型轮廓 权重（0=只看轮廓，1=只看发色）")
    ap.add_argument("--head-frac", type=float, default=DEFAULT_HEAD_FRAC)
    ap.add_argument("--rel-margin", type=float, default=oc.DEFAULT_REL_MARGIN)
    ap.add_argument("--min-group", type=int, default=oc.DEFAULT_MIN_GROUP)
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode, ns.margin, ns.bins, ns.grid,
                  ns.hue_weight, ns.head_frac, ns.rel_margin, ns.min_group)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 发型一致性机检（H1·自标定 · margin {res['margin']}）：{ns.root} {ns.episode} ===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    if not res["available"]:
        return 0
    for c, info in res["characters"].items():
        print(f"  角色 {c}: 发型 floor={info['floor']}（定妆组对 {info['intra_pairs']}）")
    nblk = 0
    icon = {"block": "⛔发型漂", "warn": "⚠️轻漂", "ok": "✅"}
    for s in res["shots"]:
        v = s["verdict"]
        if v == "block":
            nblk += 1
        if v in ("block", "warn"):
            print(f"{icon[v]} {s['png']} · {s['char']} 发型相似 {s['score']} < floor {s['floor']}")
    print(f"\n发型漂 🔴 {nblk} · 共评 {len(res['shots'])} 镜")
    return 1 if nblk else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
