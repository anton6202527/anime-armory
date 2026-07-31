#!/usr/bin/env python3
"""降级人审并排拼图——把『定妆主参考 ↔ 本镜脸（↔ 其它变体）』拼成一张并排 PNG。

为什么需要：脸的同人判定（insightface 余弦）在没装 insightface 的 env 下整段失明，
近景/特写脸是否漂只能靠人眼。但人眼逐个开两张图来回切换又慢又容易漏——给每个降级近景镜
**自动拼一张并排对比图**（左=定妆主参考，右=本镜脸），人眼一屏秒判同不同人，是 degraded
精度下唯一可靠的兜底。full 精度下也可生成，作为崩脸/串脸 finding 的人审佐证图。

本模块只做拼图（Pillow），不做任何相似度判断（那是 face_consistency 的事）。纯几何排版部分
（panel_size / canvas_size）无依赖、有 pytest 覆盖；实际绘制缺 Pillow 时优雅返回 False 不报错。

用法（库）：
    from face_compare_stitch import build_comparison
    build_comparison([("参考·定妆_沈念", ref_png), ("本镜·Clip_12", shot_png)], out_png)
"""
from __future__ import annotations

import os
from typing import List, Optional, Sequence, Tuple

PANEL_W = 512          # 每个面板等比缩放到的目标宽
PANEL_GAP = 16         # 面板间距
LABEL_H = 28           # 顶部标签条高
PAD = 16               # 画布内边距
BG = (24, 24, 28)
FG = (232, 232, 238)
MISS = (190, 110, 110)

# 复用 n2d-compose 的中文字体约定（本机 ffmpeg 无 libass，字体走 Pillow）。
ZH_FONT_PATHS = ["/System/Library/Fonts/STHeiti Medium.ttc",
                 "/System/Library/Fonts/PingFang.ttc",
                 "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"]


def _load_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
        return Image, ImageDraw, ImageFont
    except Exception:
        return None


def _font(ImageFont, size: int = 18):
    for p in ZH_FONT_PATHS:
        if os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None


# ── 纯几何排版（无依赖·可测） ──────────────────────────────────────────────────

def panel_size(src_w: int, src_h: int, target_w: int = PANEL_W) -> Tuple[int, int]:
    """等比缩放到目标宽，返回 (w, h)。非法尺寸 → 方形占位。纯函数·可测。"""
    if src_w <= 0 or src_h <= 0:
        return target_w, target_w
    scale = target_w / float(src_w)
    return target_w, max(1, int(round(src_h * scale)))


def canvas_size(panel_dims: Sequence[Tuple[int, int]],
                gap: int = PANEL_GAP, pad: int = PAD, label_h: int = LABEL_H) -> Tuple[int, int]:
    """N 个并排面板的画布尺寸。纯函数·可测。"""
    if not panel_dims:
        return pad * 2, pad * 2
    total_w = pad * 2 + sum(w for w, _ in panel_dims) + gap * (len(panel_dims) - 1)
    max_h = max(h for _, h in panel_dims)
    total_h = pad * 2 + label_h + max_h
    return total_w, total_h


# ── 绘制（需 Pillow；缺则 False） ───────────────────────────────────────────────

def build_comparison(panels: Sequence[Tuple[str, str]], out_path: str) -> bool:
    """panels = [(label, image_path), ...] → 并排 PNG 写到 out_path。

    任一图读不到 → 该面板画占位框（不整张失败）。Pillow 缺失或写盘失败 → 返回 False，不抛异常。
    """
    mods = _load_pillow()
    if mods is None or not panels:
        return False
    Image, ImageDraw, ImageFont = mods
    loaded: List[Tuple[str, object]] = []
    dims: List[Tuple[int, int]] = []
    for label, path in panels:
        im = None
        try:
            im = Image.open(path).convert("RGB")
        except Exception:
            im = None
        if im is not None:
            w, h = panel_size(*im.size)
            im = im.resize((w, h))
        else:
            w, h = PANEL_W, PANEL_W
        loaded.append((label, im))
        dims.append((w, h))
    cw, ch = canvas_size(dims)
    canvas = Image.new("RGB", (cw, ch), BG)
    draw = ImageDraw.Draw(canvas)
    font = _font(ImageFont, 18)
    x = PAD
    for (label, im), (w, h) in zip(loaded, dims):
        if font is not None:
            draw.text((x, PAD - 2), str(label), fill=FG, font=font)
        y = PAD + LABEL_H
        if im is not None:
            canvas.paste(im, (x, y))
        else:
            draw.rectangle([x, y, x + w, y + h], outline=MISS, width=3)
            if font is not None:
                draw.text((x + 8, y + 8), "(读不到图)", fill=MISS, font=font)
        x += w + PANEL_GAP
    try:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        canvas.save(out_path)
        return True
    except Exception:
        return False
