#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""foley_agent.py — V2A 视觉拟音（可插拔后端 · G5）

分析故事板，识别视觉动因（拔剑/脚步/雨/门/爆炸…）→ 产**带绝对时间戳的拟音计划**，再交给
拟音后端合成 SFX 轨。**拟音后端是选择点**（不写死）：

- 默认：**静音占位**轨（诚实标注·不假装有真音效）——保持向后兼容，compose 仍能拿到一条等长轨。
- 真 V2A 后端：设环境变量 `N2D_FOLEY_CMD` 命令模板（与 vlm_verify 的 `N2D_VLM_CMD` 同套路·厂商无关），
  用 `{plan}` `{out}` `{duration}` 占位，stdout/退出码表示成功；可包装 Sony Woosh(本地公版权重)、
  Mirelo SFX V1 / WaveSpeed(云 V2A API)、Video-Foley 等。例：
    export N2D_FOLEY_CMD='conda run -n woosh python ~/bin/woosh_v2a.py --plan {plan} --out {out} --dur {duration}'

对齐粒度从「clip 起点」细化到 **storyboard 动作时间戳**：环境/天气类铺满整 clip；冲击/动作类
（拔剑/关门/爆炸）落在 clip 内估计的动作时刻（默认 clip 中点，或读 clip 的 `动作时刻`/`action_at`
秒偏移）。诚实边界：无更细数据时是**估计**、已标 `aligned="estimated"`，不臆造精确踩点。

纯函数（extract_sfx_events / build_foley_plan / load_foley_backend / total_duration）无依赖、有 pytest；
ffmpeg/后端 I/O best-effort。退出码：产出 foley_mix.wav=0；未产出=非0（compose 据此回退自造静音轨）。

用法：python3 foley_agent.py <root> <episode>
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

# 视觉动因 → SFX 标签 + 类别（impact=点状落在动作时刻；ambience=铺满整 clip）。
# 关键词可扩展；类别决定对齐策略。顺序即匹配优先级。
SFX_RULES = (
    ("sword_whoosh", "impact", ("剑", "刀", "武器", "兵器", "挥舞", "拔剑", "出鞘", "格挡", "刀光", "剑气")),
    ("body_hit", "impact", ("击打", "命中", "受击", "撞击", "拳", "踢", "摔", "砸")),
    ("explosion", "impact", ("爆炸", "爆裂", "炸开", "轰", "崩塌", "塌")),
    ("magic_cast", "impact", ("法术", "符阵", "灵光", "雷劫", "雷落", "光束", "护盾", "阵法", "施法")),
    ("door", "impact", ("门", "开门", "关门", "推门")),
    ("glass_break", "impact", ("碎裂", "破碎", "玻璃", "瓷碎")),
    ("footsteps", "ambience", ("脚步", "走", "跑", "奔", "踱步")),
    ("weather", "ambience", ("雨", "雷雨", "风", "暴风", "雪", "雷鸣")),
    ("water", "ambience", ("流水", "溪", "河", "瀑布", "水声", "波涛")),
    ("crowd", "ambience", ("人群", "喧闹", "集市", "议论", "围观")),
    ("fire", "ambience", ("火", "篝火", "燃烧", "火焰", "炉火")),
)

DEFAULT_ACTION_FRACTION = 0.5  # impact 类无显式时刻时，落在 clip 中点（估计）


def clip_body(clip: Mapping[str, Any]) -> str:
    """汇总一条 clip 里用于识别音效的文本（prompt + 导演意图 + 描述）。纯函数。"""
    parts = [str(clip.get(k) or "") for k in ("prompt", "导演意图", "description", "描述", "镜头内容")]
    return " ".join(p for p in parts if p)


def _action_offset(clip: Mapping[str, Any], duration: float) -> Optional[float]:
    """读 clip 显式动作时刻（秒偏移）；缺则 None（调用方用估计中点）。纯函数。"""
    for key in ("动作时刻", "action_at", "impact_at", "sfx_at"):
        v = clip.get(key)
        if isinstance(v, (int, float)) and 0 <= float(v) <= max(0.0, duration):
            return float(v)
    return None


def extract_sfx_events(clip: Mapping[str, Any], clip_start: float) -> List[Dict[str, Any]]:
    """单 clip → SFX 事件列表（带绝对时间戳）。纯函数·可测。
    - ambience：start=clip 起点，span=整 clip（铺底）。
    - impact：start=clip 起点 + 动作时刻（显式秒偏移，否则估计中点），aligned=explicit/estimated。"""
    body = clip_body(clip)
    if not body.strip():
        return []
    try:
        duration = max(0.0, float(clip.get("duration") or 0.0))
    except (TypeError, ValueError):
        duration = 0.0
    explicit = _action_offset(clip, duration)
    events: List[Dict[str, Any]] = []
    seen = set()
    for tag, kind, words in SFX_RULES:
        if tag in seen or not any(w in body for w in words):
            continue
        seen.add(tag)
        if kind == "ambience":
            events.append({"clip_id": clip.get("id"), "tag": tag, "kind": kind,
                           "start": round(clip_start, 3), "duration": round(duration, 3),
                           "aligned": "span"})
        else:
            off = explicit if explicit is not None else round(duration * DEFAULT_ACTION_FRACTION, 3)
            events.append({"clip_id": clip.get("id"), "tag": tag, "kind": kind,
                           "start": round(clip_start + off, 3), "duration": 0.0,
                           "aligned": "explicit" if explicit is not None else "estimated"})
    return events


def build_foley_plan(clips: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """整集 clips → 拟音事件计划（绝对时间轴）。纯函数·可测。"""
    plan: List[Dict[str, Any]] = []
    t = 0.0
    for clip in clips:
        plan.extend(extract_sfx_events(clip, t))
        try:
            t += max(0.0, float(clip.get("duration") or 0.0))
        except (TypeError, ValueError):
            pass
    return plan


def total_duration(clips: Sequence[Mapping[str, Any]]) -> float:
    """整集时长（拟音轨总长）。纯函数。"""
    t = 0.0
    for clip in clips:
        try:
            t += max(0.0, float(clip.get("duration") or 0.0))
        except (TypeError, ValueError):
            pass
    return round(t, 3)


def load_foley_backend() -> Optional[Callable[[str, str, float], bool]]:
    """从 `N2D_FOLEY_CMD` 命令模板构造真 V2A 后端；未配置 → None（用静音占位）。纯函数（不执行）。
    模板用 {plan} {out} {duration} 占位；后端读 plan.json 合成 SFX 轨写 out，退出码 0=成功。"""
    tmpl = os.environ.get("N2D_FOLEY_CMD", "").strip()
    if not tmpl or "{out}" not in tmpl:
        return None

    def _backend(plan_path: str, out_wav: str, duration: float) -> bool:
        cmd = (tmpl.replace("{plan}", shlex.quote(plan_path))
                   .replace("{out}", shlex.quote(out_wav))
                   .replace("{duration}", str(duration)))
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=1800)
        except Exception:
            return False
        return res.returncode == 0 and os.path.exists(out_wav)

    return _backend


def _render_silent(out_wav: str, duration: float) -> bool:
    """静音占位轨（诚实默认·不假装有真音效）。ffmpeg 缺则 False。"""
    dur = max(0.1, float(duration or 0.1))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
           "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{dur}", out_wav]
    try:
        return subprocess.run(cmd, capture_output=True, timeout=300).returncode == 0 and os.path.exists(out_wav)
    except Exception:
        return False


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if len(argv) < 2:
        print("Usage: foley_agent.py <root> <episode>", file=sys.stderr)
        return 2
    root, ep = argv[0], argv[1]
    storyboard_path = os.path.join(root, "脚本", ep, "storyboard.json")
    if not os.path.exists(storyboard_path):
        return 1  # 无 storyboard：交回 compose 自造静音轨（退出码非0）
    try:
        sb = json.load(open(storyboard_path, encoding="utf-8"))
    except Exception:
        return 1
    clips = sb.get("clips", []) or []
    plan = build_foley_plan(clips)
    dur = total_duration(clips)

    work = os.path.join(root, "合成", ep, "_work")
    os.makedirs(work, exist_ok=True)
    plan_path = os.path.join(work, "foley_plan.json")
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    out_wav = os.path.join(work, "foley_mix.wav")
    backend = load_foley_backend()
    if backend is not None and backend(plan_path, out_wav, dur):
        print(f"✓ 拟音：真 V2A 后端合成 {len(plan)} 个 SFX 事件（N2D_FOLEY_CMD）。")
        return 0
    if backend is not None:
        print("⚠️ N2D_FOLEY_CMD 后端执行失败 → 回退静音占位轨。", file=sys.stderr)
    # 默认/回退：静音占位（诚实——计划已产，真音效需配 N2D_FOLEY_CMD 后端）
    if _render_silent(out_wav, dur):
        print(f"拟音计划 {len(plan)} 个事件已产；当前为**静音占位轨**（配 N2D_FOLEY_CMD 接 Woosh/Mirelo 等 V2A 后端出真音效）。")
        return 0
    return 1  # 连静音轨都没产出 → compose 回退自造


if __name__ == "__main__":
    raise SystemExit(main())
