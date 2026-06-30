#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""combat_punch.py — 打斗命中帧「微震屏」冲击（让规划好的撞点真的有物理冲击·P2）。

缺口：打斗的 hit-stop/震屏/SFX 峰值 cue 一直只在纸上（combat_cue_apex 校验它们对齐命中秒），
但**合成器从不渲染震屏**——这一拳规划得再准也「打不出来」。本模块产一段**保时长**的 ffmpeg
`-vf` 片段：在每个命中/撞点秒的小窗口（±0.09s）做低幅 crop 抖动（screen-shake），让命中帧有物理
冲击。**保时长**（不改帧数/PTS）是硬约束——hit-stop（冻帧）会改时长、和配音对轨错位，故**刻意不做冻帧**，
只做抖动（与白闪：本机 ffmpeg 的 eq 表达式解析器不稳，暂不做，诚实留 shake 一项）。

接法（零额外重编码）：compose.sh `[1/6]` 本就逐 clip 重编码统一规格到 `PXWxPXH`，本片段直接拼进那条
`-vf` 链尾（命中秒已被 foley 同源的 `impact_seconds_from_clip` 抽出）。只对 `fight_exchange/magic_burst`
镜生效；命中秒来自 storyboard（impact_frame/collision_or_apex_frame/post_cue_points/anchors keyframe）。
表达式**逗号已转义**（`\\,`）以穿过 bash 双引号 + ffmpeg filtergraph 切分；窗口用 `between(t\\,a\\,b)`。
抖幅按可用 headroom 自适应（恒 ≤ headroom·永不越界·无需 clip()）。

纯函数 `punch_vf`/`clip_punch_fragment` 无依赖、有 pytest；CLI 只为可视化/调试。
用法：python3 combat_punch.py <root> <ep> <PXW> <PXH> [--json]
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, List, Mapping, Optional, Sequence

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from foley_agent import impact_seconds_from_clip  # 命中秒单一真值源（同 skill·同目录）

# 只对明确的打斗模板加震屏（保守·避免给随便一个有关键帧锚的镜加抖动）。
COMBAT_TEMPLATES = frozenset({"fight_exchange", "magic_burst"})
DEFAULT_ZOOM = 1.04          # 4% 内缩给抖动留 headroom（窗口外=恒定居中裁=轻微 punch-in 感）
DEFAULT_WINDOW = 0.09        # 命中秒 ±window 才抖（点状冲击·不抖满全镜）
FREQ_X, FREQ_Y = 40.0, 33.0  # x/y 不同频 → 不规则真实抖动


def _even(n: float) -> int:
    return max(2, int(n) // 2 * 2)


def punch_vf(apex_secs: Sequence[float], w: int, h: int, *,
             zoom: float = DEFAULT_ZOOM, window: float = DEFAULT_WINDOW) -> str:
    """命中秒列表 → 保时长微震屏 `-vf` 片段（crop 抖动 + scale 回原尺寸）。纯函数·可测。

    无命中秒 / 尺寸非法 / headroom 太小（<3px）→ 返回 ""（调用方不加滤镜）。
    抖幅 amp = headroom*0.55（恒 ≤ headroom → 偏移 cx0±amp 永在 [0, w-cw]·无需 clamp）。"""
    secs = sorted({round(float(s), 2) for s in (apex_secs or [])
                   if isinstance(s, (int, float)) and float(s) > 0})
    if not secs or not isinstance(w, int) or not isinstance(h, int) or w <= 0 or h <= 0 or zoom <= 1.0:
        return ""
    cw, ch = _even(w / zoom), _even(h / zoom)
    if cw >= w or ch >= h:
        return ""
    cx0, cy0 = round((w - cw) / 2, 2), round((h - ch) / 2, 2)
    headroom = min(cx0, cy0)
    if headroom < 3:
        return ""
    amp = round(min(headroom * 0.55, 14.0), 1)
    # 逗号转义 between(t\,a\,b)：穿过 bash 双引号 + ffmpeg 链切分。窗口求和=多回合命中各抖一次。
    win = "(" + "+".join(
        f"between(t\\,{round(s - window, 2)}\\,{round(s + window, 2)})" for s in secs) + ")"
    x = f"{cx0}+{amp}*sin(2*PI*{FREQ_X}*t)*{win}"
    y = f"{cy0}+{amp}*cos(2*PI*{FREQ_Y}*t)*{win}"
    return f"crop={cw}:{ch}:x='{x}':y='{y}',scale={w}:{h}"


def clip_punch_fragment(clip: Mapping[str, Any], w: int, h: int) -> str:
    """单 clip → 震屏 `-vf` 片段（仅 fight_exchange/magic_burst 且有命中秒）。纯函数·可测。"""
    if not isinstance(clip, Mapping):
        return ""
    if str(clip.get("template") or "").strip() not in COMBAT_TEMPLATES:
        return ""
    try:
        duration = float(clip.get("duration") or 0.0)
    except (TypeError, ValueError):
        return ""
    return punch_vf(impact_seconds_from_clip(clip, duration), w, h)


def build_plan(root: str, ep: str, w: int, h: int) -> List[dict]:
    """整集 → 每个打斗镜的命中秒 + 震屏片段（可视化/调试）。"""
    sb_path = os.path.join(root, "脚本", ep, "storyboard.json")
    try:
        data = json.load(open(sb_path, encoding="utf-8"))
    except Exception:
        return []
    out: List[dict] = []
    for i, clip in enumerate(data.get("clips") or [], 1):
        if not isinstance(clip, dict):
            continue
        frag = clip_punch_fragment(clip, w, h)
        if frag:
            try:
                dur = float(clip.get("duration") or 0.0)
            except (TypeError, ValueError):
                dur = 0.0
            out.append({"clip_index": i, "clip_id": clip.get("id"),
                        "template": clip.get("template"),
                        "apex_secs": impact_seconds_from_clip(clip, dur),
                        "vf": frag})
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if len(argv) < 4:
        print("Usage: combat_punch.py <root> <ep> <PXW> <PXH> [--json]", file=sys.stderr)
        return 2
    root, ep = argv[0], argv[1]
    try:
        w, h = int(argv[2]), int(argv[3])
    except ValueError:
        print("PXW/PXH 必须是整数", file=sys.stderr)
        return 2
    plan = build_plan(root, ep, w, h)
    if "--json" in argv:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(f"打斗震屏：{len(plan)} 个打斗镜命中加微震屏（保时长·{w}x{h}）")
        for r in plan:
            print(f"  Clip {r['clip_index']}({r['template']}) 命中 {r['apex_secs']}s → 震屏")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
