#!/usr/bin/env python3
"""片内时序一致性机检（N2）——补 n2d-review 只查首帧 + 接缝、漏查 clip 内部漂移的盲区。

2026 行业 scene-stability 记分卡把 **身份保持 + 运动稳定** 列为核心；典型崩法是
「几秒后脸渐变 + 发际线/下颌 flicker」——这发生在**单个 clip 内部**，不是 clip 之间的接缝。

本脚本对 `出视频/第N集/视频/*.mp4` 每条 clip 抽 K 帧，量两件事：
  ① **片内身份漂移**：相邻帧人脸余弦的最小值（越低越漂）——需 insightface。
  ② **flicker / TCI**：相邻帧整幅平均亮度的绝对差均值（越大越闪）——需 Pillow，越小越稳。
缺库优雅跳过，交人判。纯数学部分（pairwise/flicker/TCI/min-cosine/band）无依赖、带 pytest。

用法：python3 temporal_consistency.py <作品根> 第N集 [--frames 6] [--id-floor 0.6] [--flicker-max 0.06] [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Sequence

import face_consistency as fc  # 复用 cosine

DEFAULT_FRAMES = 6
DEFAULT_ID_FLOOR = 0.60     # 相邻帧同人余弦下限（低于=片内身份漂移）
DEFAULT_FLICKER_MAX = 0.06  # 相邻帧亮度归一化绝对差均值上限（高于=闪烁）
SEAM_WARN = 18   # 尾帧 vs 下一首帧 64位dHash 距 > 此 → 接缝构图对不上（尾帧接力本应近乎同构图）
SEAM_BLOCK = 29  # 距更大 → 接力基本断（出视频会跳切）
# 色彩直方图距（dHash 是灰度结构哈希，抓不到"同构图但灯光/色温跳"的剪辑点闪光）。
# 接缝两帧本应近乎同色，故用绝对阈值（非自标定）；cosine 距 = 1 - 余弦相似度。
SEAM_COLOR_WARN = 0.12
SEAM_COLOR_BLOCK = 0.30
HIST_BINS = 16   # 每通道直方图 bin 数（16×3=48 维，够分辨色温/明暗跳，又不过拟合噪点）


# ---------- 纯数学（无依赖 · pytest 覆盖） ----------

def pairwise_consecutive_absdiff(values: Sequence[float]) -> List[float]:
    """相邻元素绝对差序列；<2 元素返回空。"""
    return [abs(values[i + 1] - values[i]) for i in range(len(values) - 1)]


def hist_cosine_distance(h1: Sequence[float], h2: Sequence[float]) -> Optional[float]:
    """两个直方图的 cosine 距 = 1 - 余弦相似度 ∈ [0,2]；维度不等/全零 → None。纯函数·可测。"""
    if not h1 or not h2 or len(h1) != len(h2):
        return None
    dot = sum(a * b for a, b in zip(h1, h2))
    n1 = sum(a * a for a in h1) ** 0.5
    n2 = sum(b * b for b in h2) ** 0.5
    if n1 == 0 or n2 == 0:
        return None
    return max(0.0, 1.0 - dot / (n1 * n2))


def color_verdict(color_dist: Optional[float],
                  warn: float = SEAM_COLOR_WARN, block: float = SEAM_COLOR_BLOCK) -> str:
    """色彩距 → ok/warn/block。None（缺图/算不出）→ ok（不臆造，交结构哈希/人判）。纯函数。"""
    if color_dist is None:
        return "ok"
    return "block" if color_dist > block else "warn" if color_dist > warn else "ok"


def _worse(a: str, b: str) -> str:
    order = {"ok": 0, "warn": 1, "block": 2}
    return a if order.get(a, 0) >= order.get(b, 0) else b


def flicker_index(frame_luma: Sequence[float]) -> float:
    """相邻帧平均亮度(0..1)绝对差的均值 = flicker 量；越小越稳。不足两帧→0。"""
    diffs = pairwise_consecutive_absdiff(frame_luma)
    return sum(diffs) / len(diffs) if diffs else 0.0


def temporal_consistency_index(frame_luma: Sequence[float]) -> float:
    """TCI ∈(0,1]：1/(1+flicker)，越接近 1 越稳（无闪烁=1）。"""
    return 1.0 / (1.0 + flicker_index(frame_luma))


def min_consecutive_cosine(embs: Sequence[Sequence[float]]) -> Optional[float]:
    """相邻帧人脸嵌入余弦的最小值（片内身份最差的一跳）；<2 个有效嵌入→None。"""
    vals = [fc.cosine(embs[i], embs[i + 1]) for i in range(len(embs) - 1)]
    return min(vals) if vals else None


def verdict(min_id: Optional[float], flicker: float,
            id_floor: float = DEFAULT_ID_FLOOR, flicker_max: float = DEFAULT_FLICKER_MAX) -> str:
    """综合定档：身份漂移或闪烁任一超标→升级。"""
    sev = "ok"
    if min_id is not None:
        if min_id < id_floor - 0.1:
            sev = "block"
        elif min_id < id_floor:
            sev = _max(sev, "warn")
    if flicker > flicker_max * 1.5:
        sev = "block"
    elif flicker > flicker_max:
        sev = _max(sev, "warn")
    return sev


def _max(a: str, b: str) -> str:
    order = {"ok": 1, "warn": 2, "block": 3}
    return a if order[a] >= order[b] else b


# ---------- 抽帧 + 嵌入（需 ffmpeg / Pillow / insightface） ----------

def _sample_frames(mp4: str, k: int, outdir: str) -> List[str]:
    try:
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", mp4, "-vf", f"fps=1/0.001,select='not(mod(n,1))'",
             "-frames:v", str(k), os.path.join(outdir, "f_%03d.png")],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        # 退回：按时间均匀取 k 张
        try:
            dur = fc_duration(mp4)
            if not dur:
                return []
            paths = []
            for i in range(k):
                t = dur * (i + 0.5) / k
                p = os.path.join(outdir, f"t_{i:03d}.png")
                subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", mp4,
                                "-frames:v", "1", p], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(p):
                    paths.append(p)
            return paths
        except Exception:
            return []
    return sorted(glob.glob(os.path.join(outdir, "f_*.png")))


def fc_duration(mp4: str) -> Optional[float]:
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", mp4], text=True)
        return float(out.strip())
    except Exception:
        return None


def _luma(path: str) -> Optional[float]:
    try:
        from PIL import Image  # type: ignore
        im = Image.open(path).convert("L")
        im.thumbnail((64, 64))
        px = list(im.getdata())
        return (sum(px) / len(px)) / 255.0 if px else None
    except Exception:
        return None


def _rgb_hist(path: str, bins: int = HIST_BINS) -> Optional[List[float]]:
    """归一化 RGB 直方图（每通道 bins 桶，concat 成 3×bins 维）。缺 Pillow/读图失败 → None。"""
    try:
        from PIL import Image  # type: ignore
        im = Image.open(path).convert("RGB")
        im.thumbnail((96, 96))
        chans = im.split()
        step = 256 / bins
        out: List[float] = []
        for ch in chans:
            h = [0.0] * bins
            for v in ch.getdata():
                idx = min(bins - 1, int(v / step))
                h[idx] += 1.0
            total = sum(h) or 1.0
            out.extend(x / total for x in h)
        return out
    except Exception:
        return None


def _face_emb(app, path: str) -> Optional[List[float]]:
    return fc._embed(app, path) if app else None


def analyze(root: str, ep: str, frames: int = DEFAULT_FRAMES,
            id_floor: float = DEFAULT_ID_FLOOR, flicker_max: float = DEFAULT_FLICKER_MAX) -> dict:
    vids = sorted(glob.glob(os.path.join(root, "出视频", ep, "视频", "*.mp4")))
    res: dict = {"clips": [], "notes": [], "frames": frames}
    if not vids:
        res["notes"].append(f"无 clip MP4（{os.path.join(root,'出视频',ep,'视频')}）——出视频后再跑本检。")
        return res
    if not _has_ffmpeg():
        res["notes"].append("未找到 ffmpeg——片内时序机检跳过，交人判抽帧。")
        return res
    app = fc._load_embedder()  # 可能 None（缺 insightface）→ 只测 flicker
    if app is None:
        res["notes"].append("未装 insightface——仅测 flicker/TCI，身份漂移交人判。")
    for mp4 in vids:
        with tempfile.TemporaryDirectory() as td:
            fpaths = _sample_frames(mp4, frames, td)
            lumas = [x for x in (_luma(p) for p in fpaths) if x is not None]
            embs = [e for e in (_face_emb(app, p) for p in fpaths) if e is not None] if app else []
            fl = flicker_index(lumas)
            mid = min_consecutive_cosine(embs) if len(embs) >= 2 else None
            v = verdict(mid, fl, id_floor, flicker_max)
            res["clips"].append({
                "clip": os.path.basename(mp4), "frames": len(fpaths),
                "min_id_cos": round(mid, 4) if mid is not None else None,
                "flicker": round(fl, 4), "tci": round(temporal_consistency_index(lumas), 4),
                "verdict": v,
            })
    return res


def _shot_num(name: str) -> Optional[int]:
    m = re.search(r"镜头(\d+)", name) or re.search(r"Clip[_]?(\d+)", name, re.I)
    return int(m.group(1)) if m else None


def seam_analyze(root: str, ep: str, warn: int = SEAM_WARN, block: int = SEAM_BLOCK) -> dict:
    """⑤ 接缝姿态/构图连续机检（PNG 层，出图后即可跑）——把"逐接缝人判并排读图"降成机检初筛。
    尾帧接力铁律：`镜头N_end.png` 构图 = 下一 Clip 首帧。两者 dHash 距应很小；
    距大 = 尾帧没对上下一首帧 → 出视频接缝会跳切。距小不代表姿态完美（仍需人判），但距大几乎必跳。
    两个互补指标：① dHash（灰度结构）抓构图/姿态错位；② RGB 直方图 cosine 距抓"同构图但灯光/色温
    跳"的剪辑点闪光（dHash 看不到颜色）。任一超阈即报，取较重者定级。色彩端缺 Pillow 时静默退化为纯
    dHash（不臆造）。后续可再接光流/姿态距离，但二者已覆盖跳切的主要两轴（构图 + 色彩）。"""
    import scene_consistency as scn  # 复用 _dhash_image / hamming / _probe_pillow
    res: dict = {"seams": [], "notes": []}
    d = os.path.join(root, "出图", ep, "图片")
    if not os.path.isdir(d):
        res["notes"].append(f"无 {d}——出图后再跑接缝机检。"); return res
    if not scn._probe_pillow():
        res["notes"].append("未装 Pillow——接缝机检跳过，交人判并排读图。"); return res
    tails: Dict[int, str] = {}
    firsts: Dict[int, str] = {}
    for p in glob.glob(os.path.join(d, "*.png")):
        nm = os.path.basename(p); n = _shot_num(nm)
        if n is None:
            continue
        if nm[:-4].endswith("_end"):
            tails[n] = p
        else:
            firsts.setdefault(n, p)
    fnums = sorted(firsts)
    for n, tail in sorted(tails.items()):
        nxt = next((m for m in fnums if m > n), None)
        if nxt is None:
            continue
        h1, h2 = scn._dhash_image(tail), scn._dhash_image(firsts[nxt])
        if h1 is None or h2 is None:
            continue
        dist = scn.hamming(h1, h2)
        struct_v = "block" if dist > block else "warn" if dist > warn else "ok"
        # 色彩直方图距：补 dHash（灰度结构）抓不到的"同构图但灯光/色温跳"的剪辑点闪光。
        cdist = hist_cosine_distance(_rgb_hist(tail) or [], _rgb_hist(firsts[nxt]) or [])
        cv = color_verdict(cdist)
        v = _worse(struct_v, cv)
        if v != "ok":
            res["seams"].append({"tail": os.path.basename(tail), "next_first": os.path.basename(firsts[nxt]),
                                 "dist": dist, "verdict": v,
                                 "struct_verdict": struct_v, "color_verdict": cv,
                                 "color_dist": round(cdist, 4) if cdist is not None else None})
    return res


def _has_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--frames", type=int, default=DEFAULT_FRAMES)
    ap.add_argument("--id-floor", type=float, default=DEFAULT_ID_FLOOR)
    ap.add_argument("--flicker-max", type=float, default=DEFAULT_FLICKER_MAX)
    ap.add_argument("--seam", action="store_true", help="改跑接缝机检（尾帧 vs 下一首帧 dHash，出图后即可）")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    if ns.seam:
        res = seam_analyze(ns.root.rstrip("/"), ns.episode)
        if ns.json:
            print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
        print(f"=== 接缝姿态/构图连续机检（尾帧 vs 下一首帧·N2接力）：{ns.root} {ns.episode} ===")
        for n in res["notes"]:
            print("ℹ️ " + n)
        nb = 0
        for s in res["seams"]:
            if s["verdict"] == "block":
                nb += 1
            cd = s.get("color_dist")
            why = []
            if s.get("struct_verdict", "ok") != "ok":
                why.append(f"构图 dHash 距 {s['dist']}")
            if s.get("color_verdict", "ok") != "ok":
                why.append(f"色彩/灯光距 {cd}（同构图但色温/明暗跳）")
            print(f"{'⛔接力断' if s['verdict']=='block' else '⚠️接缝偏'} {s['tail']} → {s['next_first']}："
                  f"{'；'.join(why) or f'dHash 距 {s['dist']}'}（尾帧没对上下一首帧，出视频会跳切/闪）")
        print(f"\n接缝跳切疑似 🔴 {nb} · 共查 {len(res['seams'])} 处异常接缝")
        return 1 if nb else 0
    res = analyze(ns.root.rstrip("/"), ns.episode, ns.frames, ns.id_floor, ns.flicker_max)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 片内时序一致性机检（身份漂移 + flicker/TCI）：{ns.root} {ns.episode} ===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    nblk = 0
    icon = {"block": "⛔", "warn": "⚠️", "ok": "✅"}
    for c in res["clips"]:
        if c["verdict"] == "block":
            nblk += 1
        if c["verdict"] in ("block", "warn"):
            print(f"{icon[c['verdict']]} {c['clip']}: 帧间身份min={c['min_id_cos']} flicker={c['flicker']} TCI={c['tci']}")
    print(f"\n片内崩 🔴 {nblk} · 共评 {len(res['clips'])} clip")
    return 1 if nblk else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
