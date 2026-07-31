#!/usr/bin/env python3
"""色温/调色跨镜一致机检（GRADE1·补"光位锚有了、色温/调色没成契约"的盲区）。

2026 实战缺口：同一场景里 AI 出图常一镜暖橙、下一镜冷蓝，或忽然偏品红/偏绿——色温(white balance)
和整体调色(color grade)在跨镜里没人当常量管。光位锚(light_anchor)管"光从哪来"，但不管"画面什么色温"。
观感像"换了台相机/换了次调色"，是公认的破连续点；face/outfit/scene/dof 都不测它。

机制（与 dof 同构·自标定 flag-band，不写死绝对色温）：
  对每镜图取两个全局调色代理：
    ① 暖冷 = log(mean_R / mean_B)  —— 暖(琥珀)>0、冷(蓝)<0，对应色温高低。
    ② 品绿 = log(mean_G / sqrt(mean_R·mean_B)) —— 偏绿>0、偏品红<0（tint 轴）。
  按场景分组（复用 scene_consistency 的镜头→场景映射），组内取中位数当"本场景基线调色"，
  某镜暖冷偏离中位数超 warmth_margin（或品绿偏离超 tint_margin）→ 与同场景其它镜调色不一致 🟡。
  组 <3 镜统计不稳跳过；缺 Pillow 优雅跳过交人判。

诚实边界：这是**全局通道均值代理**（不分前景/背景、不做白点估计），同场景里本就该有的明暗变化用
log 比值+中位数压住；跨场景不比（不同场景本就不同调）。warn-only，命中只作"同场景调色横跳→人并排看"。
纯数学（log 比值/中位数/离群）无依赖、带 pytest；通道均值需 Pillow，缺则优雅跳过。

用法：python3 color_grade_consistency.py <作品根> 第N集 [--warmth-margin 0.18] [--json]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import Counter
from typing import Dict, List, Optional, Sequence, Tuple

import scene_consistency as scn  # 复用 _scene_of_shot（镜头→场景映射）+ _probe_pillow
import av_emotion_consistency as _ave  # 复用 voiceover 逐镜情绪解析（纯文本·不引 insightface）

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_color import grade_proxy  # noqa: E402  暖冷/品绿度量单一真值源（与 image tone_light 共用同一公式）

KIND = "n2d_color_grade_consistency"
VERSION = 1

DEFAULT_WARMTH_MARGIN = 0.18   # |本镜暖冷代理 - 同场景中位| 超过 = 色温横跳（≈R/B 比值偏离 1.2x）
DEFAULT_TINT_MARGIN = 0.16     # 品红/绿 tint 偏离阈
MIN_GROUP = 3


# ---------- 纯数学（无依赖 · pytest 覆盖） ----------
# grade_proxy（暖冷 log(R/B)、品绿 log(G/sqrt(R·B))）现由 n2d_color 单一真值源提供（见上 import）——
# 与 image 侧 tone_light_contract 共用同一公式，避免「同一个『暖冷』两套不可比度量」。


_CLIP_RE = re.compile(r"(?:Clip|镜头?|片段|shot)\s*[_\- ]?\s*0*([0-9]+)", re.I)


def _png_clip_num(value: object) -> Optional[int]:
    # 只认 Clip/镜/shot 前缀编号（voiceover 情绪键固定 "Clip N"）；非 Clip 命名的 png 不强行抽数字，
    # 避免 "S1_01" 被误读成 clip 1 → 错配情绪。解析不出→None→不豁免（保守）。
    m = _CLIP_RE.search(str(value or ""))
    return int(m.group(1)) if m else None


def _modal_emotion(emotions: Sequence[Optional[str]]) -> Optional[str]:
    c = Counter(e for e in emotions if e)
    return c.most_common(1)[0][0] if c else None


def motivated_grade_shift(shot_emotion: Optional[str], scene_modal_emotion: Optional[str]) -> bool:
    """本镜情绪 beat ≠ 场景主情绪 → 调色偏离属「随情绪有意调色」(warm=亲密/cold=紧张)，非穿帮。
    两者皆有且不等才算（缺标注→不豁免，保守）。纯函数·可测——根治 GRADE1 误报压平戏剧调色。"""
    a = str(shot_emotion or "").strip().lower()
    b = str(scene_modal_emotion or "").strip().lower()
    return bool(a and b and a != b)


def _clip_emotions(root: str, ep: str) -> Dict[int, str]:
    out: Dict[int, str] = {}
    for k, v in (_ave._parse_voiceover_emotions(root, ep) or {}).items():
        n = _png_clip_num(k)
        if n is not None and v:
            out[n] = str(v).strip().lower()
    return out


def median(xs: Sequence[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


# ---------- 图像通道均值（需 Pillow） ----------

def _channel_means(path: str) -> Optional[Tuple[float, float, float]]:
    try:
        from PIL import Image, ImageStat  # type: ignore
    except Exception:
        return None
    try:
        im = Image.open(path).convert("RGB")
        im.thumbnail((160, 160))
        m = ImageStat.Stat(im).mean  # [R, G, B]
        return float(m[0]), float(m[1]), float(m[2])
    except Exception:
        return None


def _shot_proxy(path: str) -> Optional[Tuple[float, float]]:
    means = _channel_means(path)
    if means is None:
        return None
    return grade_proxy(*means)


# ---------- 装配 ----------

def analyze(root: str, ep: str, *, warmth_margin: float = DEFAULT_WARMTH_MARGIN,
            tint_margin: float = DEFAULT_TINT_MARGIN) -> dict:
    root = root.rstrip("/")
    res: dict = {"kind": KIND, "version": VERSION, "available": scn._probe_pillow(),
                 "groups": {}, "shots": [], "verdicts": [], "notes": []}
    if not res["available"]:
        res["notes"].append("色温/调色一致性机检已跳过（未装 Pillow）——调色横跳暂由人判并排读图。")
        return res
    smap = scn._scene_of_shot(root, ep)
    clip_emotions = _clip_emotions(root, ep)  # 逐镜情绪 beat（voiceover 标注）；空→不豁免（保守=现状）
    groups: Dict[str, List[str]] = {}
    for png, scene in smap.items():
        if os.path.exists(os.path.join(root, "出图", ep, png)):
            groups.setdefault(scene, []).append(png)
    for scene, pngs in sorted(groups.items()):
        proxies = {p: _shot_proxy(os.path.join(root, "出图", ep, p)) for p in pngs}
        proxies = {p: v for p, v in proxies.items() if v is not None}
        if len(proxies) < MIN_GROUP:
            res["groups"][scene] = {"shots": len(proxies), "skipped": "组<3镜"}
            continue
        warmth_med = median([v[0] for v in proxies.values()])
        tint_med = median([v[1] for v in proxies.values()])
        scene_modal = _modal_emotion([clip_emotions.get(_png_clip_num(p)) for p in proxies])
        res["groups"][scene] = {"shots": len(proxies),
                                "warmth_median": round(warmth_med, 3), "tint_median": round(tint_med, 3),
                                "modal_emotion": scene_modal}
        for p, (w, t) in sorted(proxies.items()):
            wdev, tdev = abs(w - warmth_med), abs(t - tint_med)
            verdict = "warn" if (wdev > warmth_margin or tdev > tint_margin) else "ok"
            shot = {"png": p, "scene": scene, "warmth": round(w, 3), "tint": round(t, 3),
                    "warmth_dev": round(wdev, 3), "tint_dev": round(tdev, 3), "verdict": verdict}
            if verdict == "warn":
                bits = []
                if wdev > warmth_margin:
                    bits.append("偏暖(琥珀)" if w > warmth_med else "偏冷(蓝)")
                if tdev > tint_margin:
                    bits.append("偏绿" if t > tint_med else "偏品红")
                emo = clip_emotions.get(_png_clip_num(p))
                if motivated_grade_shift(emo, scene_modal):
                    # 本镜情绪 beat ≠ 场景主情绪：调色随情绪变属预期，warn 降 ok（留痕，不再压平戏剧调色）
                    shot["abs_verdict"] = "warn"
                    shot["grade_shift_motivated"] = emo
                    shot["message"] = (f"{p}：色温/调色偏离同场景中位（{'、'.join(bits)}），但本镜情绪『{emo}』"
                                       f"≠场景主情绪『{scene_modal}』——调色随情绪 beat 变化属预期(暖=亲密/冷=紧张)，"
                                       f"已降为 info(ok)，人核对是否过度。")
                    verdict = "ok"
                    shot["verdict"] = "ok"
                else:
                    shot["message"] = (f"{p}：色温/调色与同场景其它镜不一致——本镜{'、'.join(bits)}"
                                       f"（暖冷 {round(w,3)} vs 场景中位 {round(warmth_med,3)}）；"
                                       f"同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。")
            res["shots"].append(shot)
            res["verdicts"].append(verdict)
    if not res["shots"]:
        res["notes"].append("色温/调色跨镜一致（或每场景可比镜不足）。")
    return res


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="色温/调色跨镜一致机检（GRADE1）")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--warmth-margin", type=float, default=DEFAULT_WARMTH_MARGIN)
    ap.add_argument("--tint-margin", type=float, default=DEFAULT_TINT_MARGIN)
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root, ns.episode, warmth_margin=ns.warmth_margin, tint_margin=ns.tint_margin)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    warns = sum(1 for v in res["verdicts"] if v == "warn")
    print(f"GRADE1 色温/调色：{len(res['groups'])} 个场景组，横跳镜 {warns}")
    for n in res["notes"]:
        print(f"  - {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
