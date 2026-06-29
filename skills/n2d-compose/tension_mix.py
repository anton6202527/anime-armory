#!/usr/bin/env python3
"""张力感知 BGM ducking —— 按 storyboard 每 Clip 的 `rhythm`（张力词）给 BGM 一条
随时间变化的音量包络，替代全集一刀切的固定 ducking。

现状：`compose.sh` 用单一全局 `DUCK_RATIO` + 静态 `volume=0.9` 压 BGM，整集一个档——
爽点/爆发镜的 BGM 本该顶上去放大冲击，细节对白/悬念镜本该压更狠让台词清楚，一刀切做不到。
本脚本读 `storyboard.json` 每 Clip 的 `rhythm` + `duration`，映射成 BGM 增益，拼成一条 ffmpeg
`volume='...':eval=frame` 时间包络，由 compose.sh 经 `BGM_GAIN_EXPR` 选用（不传则保持原行为）。
这条增益作用在「voice sidechain ducking 之前的 BGM 基准音量」上：爽点抬、细节压，叠加台词侧链。

纯函数（张力→增益映射 / 时间分段 / 包络表达式）无依赖、带 pytest。SFX 强调镜只在 plan 里列出
（爽点/爆发镜建议叠打击音效），不在本脚本另起 SFX 轨（留 compose/未来扩展）。

用法：
    python3 tension_mix.py <作品根> 第N集                 # 人读 plan
    python3 tension_mix.py <作品根> 第N集 --expr           # 只打增益表达式（喂 BGM_GAIN_EXPR）
    python3 tension_mix.py <作品根> 第N集 --json
    # compose 用法：BGM_GAIN_EXPR="$(python3 tension_mix.py <根> 第N集 --expr)" bash compose.sh ...
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

# 张力词（rhythm 含此子串即命中）→ BGM 基准增益。爽点顶上去、细节压下来。
# 顺序即优先级：靠前的强张力优先匹配。
TENSION_GAIN: List[Tuple[str, float]] = [
    ("命中", 0.98), ("撞点", 0.98), ("破防", 0.98), ("反杀", 0.98), ("破境", 0.98),
    ("突破", 0.98), ("雷劫", 0.96), ("武技", 0.96), ("剑气", 0.96), ("斗法", 0.96),
    ("开炉", 0.92), ("成丹", 0.92), ("出器", 0.92), ("淬火", 0.88), ("炼器", 0.84), ("炼丹", 0.82),
    ("飞行", 0.86), ("御剑", 0.88), ("追逐", 0.88), ("hit-stop", 0.98), ("impact", 0.98),
    ("爽点", 0.95), ("爆发", 0.95), ("反转", 0.92), ("高潮", 0.95),
    ("危机", 0.82), ("压迫", 0.80), ("对峙", 0.80), ("钩子", 0.80), ("加速", 0.82),
    ("双修", 0.58), ("合修", 0.56), ("共修", 0.56),
    ("接吻", 0.54), ("亲吻", 0.54), ("近吻", 0.50), ("额头吻", 0.50), ("脸颊吻", 0.50),
    ("拥抱", 0.62), ("抱住", 0.62), ("牵手", 0.52), ("搀扶", 0.50),
    ("说话", 0.45), ("台词", 0.45), ("对白", 0.45), ("口型", 0.45),  # 针对原生音画/说话镜压低BGM
    ("打坐", 0.48), ("入定", 0.48), ("冥想", 0.46), ("静坐", 0.44), ("吐纳", 0.46),
    ("定场", 0.62), ("铺垫", 0.58), ("反应", 0.60), ("反压", 0.66),
    ("悬念", 0.40), ("细节", 0.38), ("留白", 0.36), ("定格", 0.36), ("集尾", 0.42),
]
DEFAULT_GAIN = 0.60
SFX_EMPHASIS = (
    "爽点", "爆发", "反转", "危机", "高潮",
    "命中", "撞点", "破防", "反杀", "破境", "突破", "雷劫", "武技", "剑气", "斗法",
    "开炉", "成丹", "出器", "淬火", "炼器", "炼丹", "hit-stop", "impact",
)


def _as_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def tension_gain(clip: Dict[str, Any] | str | None) -> float:
    """按 Clip 属性（rhythm/mode）决定 BGM 基准增益。纯函数。"""
    if isinstance(clip, dict):
        rhythm = str(clip.get("rhythm") or "")
        mode = str(clip.get("mode") or "").lower()
    else:
        rhythm = str(clip or "")
        mode = ""
    
    # 优先级 1：明确的说话镜（含原生音画）压低 BGM 以突出台词
    if "native_av" in mode or "speech" in rhythm or "说话" in rhythm or "台词" in rhythm:
        return 0.42
        
    # 优先级 2：按 TENSION_GAIN 关键词匹配
    for key, gain in TENSION_GAIN:
        if key in rhythm:
            return gain
            
    return DEFAULT_GAIN


def build_segments(clips: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """clips → [{start,end,gain,rhythm,id}]，按 duration 累计时间轴。纯函数。"""
    segs: List[Dict[str, Any]] = []
    t = 0.0
    for c in clips:
        if not isinstance(c, dict):
            continue
        dur = _as_float(c.get("duration")) or 0.0
        if dur <= 0:
            continue
        gain = tension_gain(c)
        segs.append({"start": round(t, 3), "end": round(t + dur, 3), "gain": gain,
                     "rhythm": str(c.get("rhythm") or ""), "id": str(c.get("id") or c.get("label") or "")})
        t += dur
    return segs



def build_volume_expr(segments: Sequence[Dict[str, Any]], default: float = DEFAULT_GAIN) -> str:
    """时间分段 → ffmpeg volume eval=frame 表达式（嵌套 if(between(t,..),g,..)）。纯函数。

    末段不收尾时用最后一段增益兜底，超出总时长保持默认。
    """
    if not segments:
        return f"{default:g}"
    expr = f"{default:g}"
    for seg in reversed(segments):
        expr = f"if(between(t,{seg['start']:g},{seg['end']:g}),{seg['gain']:g},{expr})"
    return expr


def load_clips(root: str, ep: str) -> Optional[List[Dict[str, Any]]]:
    p = os.path.join(root, "脚本", ep, "storyboard.json")
    if not os.path.isfile(p):
        return None
    try:
        data = json.load(open(p, encoding="utf-8"))
    except Exception:
        return None
    clips = data.get("clips") if isinstance(data, dict) else None
    return clips if isinstance(clips, list) else None


def analyze(root: str, ep: str) -> Dict[str, Any]:
    clips = load_clips(root, ep)
    if clips is None:
        return {"available": False, "segments": [], "volume_expr": str(DEFAULT_GAIN),
                "notes": [f"缺 脚本/{ep}/storyboard.json——先做分镜设计；compose 不传 BGM_GAIN_EXPR 时保持固定 ducking"]}
    segs = build_segments(clips)
    expr = build_volume_expr(segs)
    sfx = [s for s in segs if any(k in s["rhythm"] for k in SFX_EMPHASIS)]
    return {"available": True, "segments": segs, "volume_expr": expr,
            "sfx_emphasis": [{"id": s["id"], "at": [s["start"], s["end"]], "rhythm": s["rhythm"]} for s in sfx],
            "notes": []}


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="张力感知 BGM 增益包络")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--expr", action="store_true", help="只打 ffmpeg volume 表达式（喂 compose.sh BGM_GAIN_EXPR）")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode)
    if ns.expr:
        print(res["volume_expr"]); return 0
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 张力感知 BGM 增益：{ns.root} {ns.episode} ===")
    if not res["available"]:
        for n in res["notes"]:
            print(f"  · {n}")
        return 0
    for s in res["segments"]:
        bar = "█" * int(s["gain"] * 10)
        print(f"  [{s['start']:>6.1f}–{s['end']:>6.1f}s] gain {s['gain']:.2f} {bar:<10} {s['rhythm']}  {s['id']}")
    if res["sfx_emphasis"]:
        print(f"\n建议叠音效/打击强调：{'、'.join(x['id'] or x['rhythm'] for x in res['sfx_emphasis'])}")
    print(f"\nffmpeg volume 表达式（喂 compose.sh BGM_GAIN_EXPR）：")
    print(f"  BGM_GAIN_EXPR=\"$(python3 tension_mix.py {ns.root} {ns.episode} --expr)\"")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
