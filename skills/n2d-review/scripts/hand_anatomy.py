#!/usr/bin/env python3
"""手部/解剖畸形机检（N5·崩脸/糊之外的第四类「单帧崩坏」）——补 AI 生图头号翻车点的盲区。

2026 实测：脸锁住、发型/服装锁住，**手仍最容易崩**——六指/七指、手指粘连、断指、手肘
反折、多肢。行业调研里「手部/肢体畸形」常年是设计师第一痛点。既有 quality_check 只测「糊」，
face/outfit/hair 都不看手 → 这一类畸形在现产线完全无机检，全靠人逐帧瞪眼。本脚本把它脚本化成
**可疑→人判**的初筛门。

机制（诚实优先·只抓高置信畸形）：
  手的「指尖数」从**手轮廓的凸缺陷（convexity defects）**数：相邻手指间的深谷=指缝，
  指尖数 = 深指缝数 + 1（经典 CV 手势计数法）。正常张开手 ≤5 指尖；**≥6 指尖**是
  「多指」高置信信号（误报来源少），判 🔴；指尖异常少（粘连/糊成一团）置信低，仅 🟡。
  握拳/侧手/半遮挡天然 0–2 指尖，不报（不误杀）。

  手部定位优先级：mediapipe Hands（有则用，定位最稳）> cv2 肤色分割取最大候选块（粗筛）。
  二者都不可用 → 优雅跳过（交人判），绝不输出假阳性。

诚实边界：风格化漫剧手 + 无专训畸形模型，这是**粗筛初筛不是裁决**——命中只作「这镜的手可疑，
人放大看」的信号，绝不自动改图。漏报（把崩手放过）比误报代价低，故只在 ≥6 指尖这种铁证上判 🔴。
依赖 cv2（缺则跳过）；mediapipe 可选增强。纯几何部分（指尖计数/分档）无依赖、带 pytest。

用法：python3 hand_anatomy.py <作品根> 第N集 [--extra 6] [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
from typing import List, Optional, Sequence, Tuple

DEFAULT_EXTRA_FINGERS = 6      # ≥ 此指尖数 → 🔴 多指（高置信）
DEFAULT_MIN_DEFECT_FRAC = 0.22  # 指缝深度 ≥ 手框对角线 * 此比例 才算一道真指缝（滤掉轮廓毛刺）
DEFAULT_MIN_HAND_FRAC = 0.012   # 手候选块面积 ≥ 全图 * 此比例 才评（太小=远景手，测不准，跳过）


# ---------- 纯几何（无依赖 · pytest 覆盖） ----------

def count_fingertips(defect_depths: Sequence[float], scale: float,
                     min_frac: float = DEFAULT_MIN_DEFECT_FRAC) -> int:
    """由手轮廓凸缺陷深度列表数指尖：深度 ≥ scale*min_frac 的为真指缝，指尖=真指缝+1。
    无任何真指缝（握拳/单指/糊团）→ 至多 1。scale<=0（无尺度）→ 0。纯函数·可测。"""
    if scale <= 0:
        return 0
    deep = [d for d in defect_depths if d >= scale * min_frac]
    if not deep:
        return 0
    return len(deep) + 1


def anatomy_band(fingertips: int, extra_threshold: int = DEFAULT_EXTRA_FINGERS) -> str:
    """单只手指尖数 → 档。≥extra_threshold(默认6)=🔴多指（铁证）；
    其余一律 ok——握拳/遮挡/正常 5 指都在此，不误杀。粘连/断指置信太低，不在这里判（交人判）。
    纯函数·可测。"""
    if fingertips >= extra_threshold:
        return "block"
    return "ok"


def worst_band(bands: Sequence[str]) -> str:
    order = {"ok": 0, "warn": 1, "block": 2}
    w = "ok"
    for b in bands:
        if order.get(b, 0) > order.get(w, 0):
            w = b
    return w


# ---------- 图像（需 cv2 · 可选 mediapipe） ----------

def _probe_cv2() -> bool:
    try:
        import cv2  # noqa
        return True
    except Exception:
        return False


def episode_png_paths(root: str, ep: str) -> List[str]:
    """Return episode PNGs from the canonical 图片/ directory, plus legacy flat files."""
    patterns = [
        os.path.join(root, "出图", ep, "图片", "*.png"),
        os.path.join(root, "出图", ep, "*.png"),
    ]
    out: List[str] = []
    seen = set()
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            norm = os.path.normpath(path)
            if norm not in seen:
                seen.add(norm)
                out.append(path)
    return out


def _hand_boxes_mediapipe(bgr) -> Optional[List[Tuple[int, int, int, int]]]:
    """mediapipe Hands 定位 → [(x0,y0,x1,y1)]；不可用返回 None（让上层回退肤色启发）。"""
    try:
        import cv2  # type: ignore
        import mediapipe as mp  # type: ignore
    except Exception:
        return None
    hands_mod = getattr(getattr(mp, "solutions", None), "hands", None)
    if hands_mod is None:
        try:
            from mediapipe.python.solutions import hands as hands_mod  # type: ignore
        except Exception:
            return None
    try:
        h, w = bgr.shape[:2]
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        with hands_mod.Hands(static_image_mode=True, max_num_hands=6,
                             min_detection_confidence=0.3) as hands:
            res = hands.process(rgb)
        boxes: List[Tuple[int, int, int, int]] = []
        for lm in (res.multi_hand_landmarks or []):
            xs = [p.x * w for p in lm.landmark]
            ys = [p.y * h for p in lm.landmark]
            pad_x = (max(xs) - min(xs)) * 0.25
            pad_y = (max(ys) - min(ys)) * 0.25
            boxes.append((int(max(0, min(xs) - pad_x)), int(max(0, min(ys) - pad_y)),
                          int(min(w, max(xs) + pad_x)), int(min(h, max(ys) + pad_y))))
        return boxes
    except Exception:
        return None


def _skin_hand_boxes(bgr, min_hand_frac: float) -> List[Tuple[int, int, int, int]]:
    """无 mediapipe 时的粗回退：YCrCb 肤色分割 → 取面积达标的连通块当手候选（含脸，靠指尖数过滤）。"""
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except Exception:
        return []
    h, w = bgr.shape[:2]
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    mask = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: List[Tuple[int, int, int, int]] = []
    for c in cnts:
        if cv2.contourArea(c) < min_hand_frac * w * h:
            continue
        x, y, bw, bh = cv2.boundingRect(c)
        boxes.append((x, y, x + bw, y + bh))
    return boxes


def _convexity_defect_depths(defects) -> List[float]:
    """Return cv2 convexityDefects depths in pixels, accepting OpenCV 4/5 shapes."""
    if defects is None:
        return []
    rows = []
    if hasattr(defects, "reshape"):
        try:
            rows = list(defects.reshape(-1, 4))
        except Exception:
            rows = []
    if not rows:
        try:
            rows = list(defects)
        except Exception:
            return []
    depths: List[float] = []
    for row in rows:
        cur = row
        while isinstance(cur, (list, tuple)) and len(cur) == 1:
            cur = cur[0]
        if not isinstance(cur, (list, tuple)) and not hasattr(cur, "__getitem__"):
            continue
        try:
            depth = cur[3]
        except Exception:
            continue
        try:
            depths.append(float(depth) / 256.0)
        except Exception:
            continue
    return depths


def _fingertips_in_box(bgr, box) -> Optional[int]:
    """对手候选框内的肤色轮廓数指尖（凸缺陷法）。返回该框最大轮廓的指尖数；不可解→None。"""
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except Exception:
        return None
    x0, y0, x1, y1 = box
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    roi = bgr[y0:y1, x0:x1]
    ycrcb = cv2.cvtColor(roi, cv2.COLOR_BGR2YCrCb)
    mask = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    if len(c) < 5:
        return None
    hull = cv2.convexHull(c, returnPoints=False)
    if hull is None or len(hull) < 4:
        return 0
    try:
        defects = cv2.convexityDefects(c, hull)
    except Exception:
        return None
    if defects is None:
        return 0
    diag = math.hypot(x1 - x0, y1 - y0)
    depths = _convexity_defect_depths(defects)   # cv2 defect depth 定点数 /256 → 像素
    return count_fingertips(depths, diag)


def analyze(root: str, ep: str, extra: int = DEFAULT_EXTRA_FINGERS,
            min_hand_frac: float = DEFAULT_MIN_HAND_FRAC) -> dict:
    res: dict = {"available": _probe_cv2(), "extra_threshold": extra, "shots": [], "notes": []}
    if not res["available"]:
        res["notes"].append("手部畸形机检已跳过（未装 cv2）——多指/粘连暂由人逐帧放大看。")
        return res
    import cv2  # type: ignore
    pngs = episode_png_paths(root, ep)
    if not pngs:
        res["notes"].append("本集无分镜 PNG。")
        return res
    used_mp = None
    for p in pngs:
        bgr = cv2.imread(p)
        if bgr is None:
            continue
        boxes = _hand_boxes_mediapipe(bgr)
        if boxes is None:
            boxes = _skin_hand_boxes(bgr, min_hand_frac)
            used_mp = used_mp or False
        else:
            used_mp = True
        bands, max_ft = [], 0
        for b in boxes:
            ft = _fingertips_in_box(bgr, b)
            if ft is None:
                continue
            max_ft = max(max_ft, ft)
            bands.append(anatomy_band(ft, extra))
        v = worst_band(bands) if bands else "ok"
        if v != "ok":
            res["shots"].append({"png": os.path.basename(p), "max_fingertips": max_ft,
                                 "hands": len(boxes), "verdict": v})
    res["locator"] = "mediapipe" if used_mp else ("肤色启发" if used_mp is False else "无手候选")
    if used_mp is False:
        res["notes"].append("mediapipe Hands solutions API absent; 手部定位走肤色启发粗筛，仅抓 ≥6 指尖铁证，置信偏低。")
    return res


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--extra", type=int, default=DEFAULT_EXTRA_FINGERS)
    ap.add_argument("--min-hand-frac", type=float, default=DEFAULT_MIN_HAND_FRAC)
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode, ns.extra, ns.min_hand_frac)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 手部/解剖畸形机检（N5·≥{res['extra_threshold']}指尖判多指）：{ns.root} {ns.episode} ===")
    for note in res["notes"]:
        print("ℹ️ " + note)
    if not res["available"]:
        return 0
    nb = 0
    icon = {"block": "⛔多指/畸形", "warn": "⚠️手可疑"}
    for s in res["shots"]:
        if s["verdict"] == "block":
            nb += 1
        print(f"{icon[s['verdict']]} {s['png']}: 单手最多 {s['max_fingertips']} 指尖（手候选 {s['hands']}）")
    print(f"\n多指/畸形 🔴 {nb} · 标出 {len(res['shots'])} 镜（定位={res.get('locator','-')}）")
    return 1 if nb else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
