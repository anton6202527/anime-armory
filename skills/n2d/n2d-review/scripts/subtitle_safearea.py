#!/usr/bin/env python3
"""字幕安全区构图一致（L2·脸不该压进字幕带）——出图阶段就拦"脸落在字幕会盖到的位置"。

为什么要在出图机检：
  compose 把字幕烧在画面底部一条「字幕带」里（render_subs.py：基线 HEIGHT-130 起自底向上排，
  长句最多占到 SUB_MAXH_FRAC≈0.45 高，但单/双行常态就在底部约 18% 区域）。若某镜把人脸构图在
  画面最下沿，字幕一烧上去就**盖住脸/嘴**——观感是「脸被字幕切了」或口型被遮。这类构图问题图一出来
  就定了，等合成烧完字幕才发现要重出更贵。本门在出图后量每张脸的竖直位置，脸的下缘探进字幕带就标 🟡。

机制（advisory·只 warn 不 block）：
  字幕带 = 画面底部 band_top_frac..1.0（默认 0.82——对齐 render_subs 常态单/双行字幕占底部约 18%）。
  对每张检出人脸，取其框下缘的纵向比例 face_y1_frac（y1/图高）；≥ band_top_frac 即「脸下缘进了字幕带」。
  任一脸进带 → 🟡 warn（脸可能被字幕遮挡，人判：抬构图 / 缩字幕带 / 此镜关字幕）。不 block——
  字幕带可调、也有「脸在带里但字幕短没真盖到」的情形，硬拦会误杀。

脸框来自 face_consistency 的 insightface（复用 fc 抽框逻辑）；缺 insightface → 优雅跳过，交人判。
纯数学（in_subtitle_band / safearea_band）无依赖、带 pytest。

用法：python3 subtitle_safearea.py <作品根> 第N集 [--band-top-frac 0.82] [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import List, Optional, Sequence

import face_consistency as fc  # 复用：shot_character_map + insightface 框抽取

# 默认字幕带顶（占画面高度比例）：render_subs.py 常态单/双行字幕落底部约 18%（基线 HEIGHT-130 起上排）。
DEFAULT_BAND_TOP_FRAC = 0.82


# ---------- 纯数学（无依赖 · pytest 覆盖） ----------

def in_subtitle_band(face_y1_frac: float, band_top_frac: float = DEFAULT_BAND_TOP_FRAC) -> bool:
    """脸框下缘纵向比例(face_y1_frac=y1/图高) 是否探进字幕带（≥ band_top_frac）。
    边界含等号（恰好贴带顶算进带）。纯函数·可测。"""
    return face_y1_frac >= band_top_frac


def safearea_band(num_faces_in_band: int) -> str:
    """进带脸数 → 档。任一脸进字幕带 → 'warn'（🟡 脸可能被字幕遮挡，advisory）；否则 'ok'。
    本门只 warn 不 block。纯函数·可测。"""
    return "warn" if num_faces_in_band > 0 else "ok"


# ---------- 图像（需 insightface · 缺则跳过） ----------

def _face_boxes(app, png: str) -> Optional[List[Sequence[float]]]:
    """检出图中所有人脸 bbox [(x0,y0,x1,y1), ...] + 图高；不可解码/无库 → None。
    返回 (boxes, image_height)。"""
    try:
        import cv2  # type: ignore
        img = cv2.imread(png)
        if img is None:
            return None
        h = img.shape[0]
        faces = app.get(img) or []
        boxes = [tuple(float(v) for v in f.bbox) for f in faces]
        return boxes, h
    except Exception:
        return None


def analyze(root: str, ep: str, band_top_frac: float = DEFAULT_BAND_TOP_FRAC) -> dict:
    app = fc._load_embedder()
    res: dict = {"available": app is not None, "band_top_frac": band_top_frac, "shots": [], "notes": []}
    if app is None:
        res["notes"].append("字幕安全区机检已跳过（未装 insightface/cv2）——脸是否压进字幕带暂由人判读图。")
        return res
    smap = fc.shot_character_map(root, ep)
    pngs = sorted(smap.keys()) if smap else [
        os.path.relpath(p, os.path.join(root, "出图", ep))
        for p in sorted(glob.glob(os.path.join(root, "出图", ep, "图片", "*.png")))
    ]
    if not pngs:
        res["notes"].append("本集无分镜 PNG。")
        return res
    for png in pngs:
        full = os.path.join(root, "出图", ep, png)
        if not os.path.exists(full):
            continue
        probe = _face_boxes(app, full)
        if not probe:
            continue
        boxes, h = probe
        if not boxes or h <= 0:
            continue
        n_in = sum(1 for b in boxes if in_subtitle_band(b[3] / float(h), band_top_frac))
        if n_in > 0:
            res["shots"].append({"png": os.path.basename(png), "faces": len(boxes),
                                 "faces_in_band": n_in, "verdict": safearea_band(n_in)})
    return res


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--band-top-frac", type=float, default=DEFAULT_BAND_TOP_FRAC,
                    help="字幕带顶占画面高度比例（默认 0.82，对齐 render_subs 底部字幕带）")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode, ns.band_top_frac)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 字幕安全区构图一致（L2·脸不压字幕带 top={res['band_top_frac']}）：{ns.root} {ns.episode} ===")
    for note in res["notes"]:
        print("ℹ️ " + note)
    if not res["available"]:
        return 0
    for s in res["shots"]:
        print(f"⚠️脸压字幕带 {s['png']}: {s['faces_in_band']}/{s['faces']} 张脸下缘进了字幕带（人判：抬构图/缩字幕带）")
    print(f"\n脸压字幕带 🟡 {len(res['shots'])} 镜（advisory·只提示不 block）")
    return 0   # warn-only：永不以失败退出


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
