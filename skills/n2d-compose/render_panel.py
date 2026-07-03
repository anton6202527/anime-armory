#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""系统面板母题 overlay 文字层 —— 把等级/属性数值渲成逐镜透明 PNG，供 ffmpeg overlay 烧在
AI 出的发光面板底框上（混合渲染：AI 出锁色锁形空光幕底框，清晰数值由本脚本叠）。

为什么单独于 render_subs：字幕是底部居中、自底向上排版；系统面板是任意锚点定位、且要读
motif_registry 的成长 progression 取"当前 Clip 的最新成长快照"。逻辑不同，但复用 subtitle_render
的 Pillow→透明PNG→ffmpeg overlay 链原语（无 libass 时的统一出路）。面板层叠在字幕层之下。

数据来源：
  · 出图/共享/motif_registry.json —— growth_state_machine.progression（逐次成长快照）+ overlay_spec
  · 脚本/第N集/storyboard.json    —— 哪些 Clip 是 system_panel、各 Clip 时长（算时间窗）

用法: render_panel.py <作品根> <第N集> <workdir>
环境: PANEL_BASE(ffmpeg png 输入起始序，compose 透传) SUB_W/SUB_H(画幅)
产出: <workdir>/panelpng/panel_NN.png + panel_inputs.txt(png路径) + panel_vfilter.txt(overlay链[0:v]->[vpanel])
      无 motif_registry 或本集无 system_panel 镜 → 写空 panel_inputs/panel_vfilter 并 exit 0（行为不变）。

测试: cd skills/n2d-compose && python -m pytest test_render_panel.py
（纯函数 select_snapshot/compute_clip_windows/panel_text_lines/anchor_xy 无需 PIL，可单测。）
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "n2d", "_lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)
import subtitle_render as sr  # 共享原语：字体回退 / overlay 链（无 PIL 也可 import）

try:
    from n2d_const import SYSTEM_PANEL_TEMPLATE_ID, SYSTEM_PANEL_MOTIF_ID
except Exception:  # 退化兜底（独立跑/测试桩）
    SYSTEM_PANEL_TEMPLATE_ID = "system_panel"
    SYSTEM_PANEL_MOTIF_ID = "MOTIF_系统面板"


# ── 纯函数（无 PIL·可测） ─────────────────────────────────────────────────────

def is_panel_clip(clip: Dict[str, Any]) -> bool:
    """Clip 是否为系统面板母题镜：template=system_panel 或 template_contract 带 motif_id。"""
    if not isinstance(clip, dict):
        return False
    if str(clip.get("template") or "") == SYSTEM_PANEL_TEMPLATE_ID:
        return True
    tc = clip.get("template_contract")
    return isinstance(tc, dict) and bool(tc.get("motif_id"))


def clip_motif_id(clip: Dict[str, Any]) -> str:
    """取 Clip 绑定的 motif_id（缺则默认系统面板）。"""
    tc = clip.get("template_contract") if isinstance(clip.get("template_contract"), dict) else {}
    return str(tc.get("motif_id") or SYSTEM_PANEL_MOTIF_ID)


def compute_clip_windows(clips: List[Dict[str, Any]]) -> List[Tuple[float, float]]:
    """按 clip.duration 累计算每个 Clip 在成片时间轴的 [start, end] 秒窗。缺时长按 0 宽处理。

    注：合成期 warp/trim 会以同一份 storyboard 时长为目标，故用 duration 累计是与剪辑同源的近似。"""
    windows: List[Tuple[float, float]] = []
    t = 0.0
    for clip in clips:
        dur = clip.get("duration") if isinstance(clip, dict) else 0
        try:
            dur = float(dur)
        except (TypeError, ValueError):
            dur = 0.0
        windows.append((round(t, 3), round(t + dur, 3)))
        t += dur
    return windows


def select_snapshot(progression: List[Dict[str, Any]], clip_order: Dict[str, int],
                    current_clip_id: str) -> Optional[Dict[str, Any]]:
    """取"当前 Clip 的最新成长快照"：progression 中 at_clip 排在 current 之前(含本身)的、序最大者。

    clip_order：clip_id → storyboard 内序号。current 不在序表里时按 progression 列表序兜底取 ≤ 出现位置。
    无候选返回 None（该面板镜不叠数值，只显 AI 光幕底）。纯函数·可测。"""
    cur_rank = clip_order.get(current_clip_id)
    best: Optional[Dict[str, Any]] = None
    best_rank = -1
    for i, snap in enumerate(progression):
        if not isinstance(snap, dict):
            continue
        at = str(snap.get("at_clip") or "")
        rank = clip_order.get(at, i)  # at 不在序表→用 progression 列表序兜底
        if cur_rank is not None and clip_order.get(at, None) is not None and rank > cur_rank:
            continue  # 这条快照属于"未来"的 Clip，跳过
        if rank >= best_rank:
            best, best_rank = snap, rank
    return best


def panel_text_lines(snapshot: Dict[str, Any], overlay_spec: Dict[str, Any]) -> List[str]:
    """按 overlay_spec.fields 把成长快照格式化成 overlay 文字行（title / Lv.N / 属性 值）。纯函数·可测。"""
    fields = overlay_spec.get("fields") or ["title", "level", "attrs"]
    lines: List[str] = []
    for field in fields:
        if field == "title":
            title = snapshot.get("title")
            if title:
                lines.append(str(title))
        elif field == "level":
            lvl = snapshot.get("level")
            if lvl is not None:
                lines.append(f"Lv.{lvl}")
        elif field == "attrs":
            attrs = snapshot.get("attrs")
            if isinstance(attrs, dict):
                for k, v in attrs.items():
                    lines.append(f"{k}  {v}")
        else:
            val = snapshot.get(field)
            if val is not None:
                lines.append(str(val))
    return lines


def anchor_xy(anchor: str, w: int, h: int) -> Tuple[int, int]:
    """overlay_spec.anchor → 文字块中心像素坐标。纯函数·可测。"""
    table = {
        "panel_center": (w // 2, h // 2),
        "panel_top": (w // 2, h // 3),
        "panel_bottom": (w // 2, (2 * h) // 3),
        "panel_left": (w // 4, h // 2),
        "panel_right": (3 * w // 4, h // 2),
    }
    return table.get(anchor, table["panel_center"])


# ── motif_registry 装载 ───────────────────────────────────────────────────────

def load_json(path: str) -> Optional[Any]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def motif_by_id(registry: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(registry, dict):
        return {}
    return {str(m.get("motif_id")): m for m in registry.get("motifs") or [] if isinstance(m, dict)}


def plan_panels(clips: List[Dict[str, Any]], registry: Optional[Dict[str, Any]], ep: str
                ) -> List[Dict[str, Any]]:
    """规划本集面板 overlay：每个 system_panel 镜 → {window, lines, anchor, color}。纯函数·可测。"""
    motifs = motif_by_id(registry)
    windows = compute_clip_windows(clips)
    # clip_order：用 clip.id（缺则合成 id）→ 序号
    order: Dict[str, int] = {}
    ids: List[str] = []
    for i, clip in enumerate(clips):
        cid = str(clip.get("id") or f"{ep}_CLIP{i+1:02d}") if isinstance(clip, dict) else f"#{i}"
        order[cid] = i
        ids.append(cid)
    panels: List[Dict[str, Any]] = []
    for i, clip in enumerate(clips):
        if not is_panel_clip(clip):
            continue
        motif = motifs.get(clip_motif_id(clip))
        if not motif:
            continue
        gsm = motif.get("growth_state_machine") if isinstance(motif.get("growth_state_machine"), dict) else {}
        prog = gsm.get("progression") or []
        spec = motif.get("overlay_spec") if isinstance(motif.get("overlay_spec"), dict) else {}
        snap = select_snapshot(prog, order, ids[i])
        if snap is None:
            continue
        lines = panel_text_lines(snap, spec)
        if not lines:
            continue
        panels.append({
            "clip_index": i,
            "clip_id": ids[i],
            "window": windows[i],
            "lines": lines,
            "anchor": str(spec.get("anchor") or "panel_center"),
            "color": spec.get("color") or [180, 230, 255],
        })
    return panels


# ── 渲染（PIL·惰性 import，纯函数测试不触） ─────────────────────────────────────

def render(root: str, ep: str, workdir: str) -> int:
    panel_inputs = os.path.join(workdir, "panel_inputs.txt")
    panel_vfilter = os.path.join(workdir, "panel_vfilter.txt")
    # 先落空文件——无 motif/无面板镜时 compose 据空文件跳过（行为不变）。
    open(panel_inputs, "w").close()
    open(panel_vfilter, "w").close()

    registry = load_json(os.path.join(root, "出图", "共享", "motif_registry.json"))
    if not isinstance(registry, dict):
        print("（无 motif_registry.json：跳过系统面板 overlay）")
        return 0
    sb = load_json(os.path.join(root, "脚本", ep, "storyboard.json"))
    clips = sb.get("clips") if isinstance(sb, dict) else None
    if not isinstance(clips, list):
        print("（无 storyboard.json：跳过系统面板 overlay）")
        return 0
    panels = plan_panels(clips, registry, ep)
    if not panels:
        print("（本集无系统面板镜或无成长数值：跳过 overlay）")
        return 0

    from PIL import Image, ImageDraw  # 惰性 import：纯函数测试无需 PIL

    W = int(os.environ.get("SUB_W", 1080))
    H = int(os.environ.get("SUB_H", 1920))
    SIZE = int(os.environ.get("PANEL_SIZE", 46))
    panel_dir = os.path.join(workdir, "panelpng")
    os.makedirs(panel_dir, exist_ok=True)
    font = sr.load_font(SIZE, paths=["/System/Library/Fonts/STHeiti Medium.ttc"])
    manifest: List[Tuple[str, float, float]] = []
    for k, p in enumerate(panels):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        cx, cy = anchor_xy(p["anchor"], W, H)
        col = tuple(p["color"]) + (255,) if len(p["color"]) == 3 else tuple(p["color"])
        lines = p["lines"]
        total_h = len(lines) * (SIZE + 14)
        y = cy - total_h // 2
        for ln in lines:
            d.text((cx, y), ln, font=font, fill=col, anchor="ma",
                   stroke_width=4, stroke_fill=(8, 16, 28, 255))
            y += SIZE + 14
        out = os.path.join(panel_dir, f"panel_{k:02d}.png")
        img.save(out)
        manifest.append((out, p["window"][0], p["window"][1]))

    base = int(os.environ.get("PANEL_BASE", "4"))
    with open(panel_inputs, "w") as f:
        for path, _, _ in manifest:
            f.write(path + "\n")
    # 面板链：[0:v] 叠 N 张面板 PNG → [vpanel]（不加 format，留给字幕链收尾出 [v]）。
    filt = sr.overlay_filter_chain([(s, e) for _, s, e in manifest],
                                   png_input_base=base, first_input="[0:v]",
                                   inter_prefix="p", pre_final="[vpanel]", overlay_xy="0:0")
    with open(panel_vfilter, "w") as f:
        f.write(filt)
    print(f"渲染 {len(manifest)} 张系统面板 overlay PNG，画幅 {W}x{H}（数值层叠在 AI 光幕底之上、字幕之下）")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 3:
        print("usage: render_panel.py <作品根> <第N集> <workdir>", file=sys.stderr)
        return 2
    return render(argv[0], argv[1], argv[2])


if __name__ == "__main__":
    raise SystemExit(main())
