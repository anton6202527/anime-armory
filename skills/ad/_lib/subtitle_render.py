#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""字幕渲染原语（ad 线自带·vendored）。

本机 ffmpeg 是裁剪版、无 libass/drawtext，所以 ad-compose 得自己把字幕渲成透明 PNG 再
overlay 烧录。本模块是 ad 线**自包含**的字幕底层：SRT/LRC/ASS 解析 + 时间戳解析 + 字体
回退加载 + CJK 折行 + ffmpeg overlay 链拼装——纯确定性、可单测，随 ad 线一起交付。
（n2d/mv 各自有自己的同名副本；ad 不复用别线的副本，别线也不复用本份。）

ad-compose/render_subs.py 在此之上叠**视觉部分**（描边技法、版式、输出文件命名）——
那是 ad 线真正分叉、改一像素就动既有产物的部分。

无 PIL 环境也能 import：解析/链路原语不碰 PIL，只有 load_font 内部惰性 import PIL。
"""
from __future__ import annotations

import os
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# ── 时间戳 + 字幕/歌词解析（纯函数·无 PIL） ──────────────────────────────────

_TS = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)")          # HH:MM:SS,mmm / HH:MM:SS.mmm
_CJK = re.compile(r"[一-鿿]")
_LRC_LINE = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]\s*(.+)")


def parse_timestamp(s: str) -> float:
    """`HH:MM:SS,mmm`（SRT 逗号或点）→ 秒。抓不到返回 0.0。"""
    m = _TS.search(s or "")
    if not m:
        return 0.0
    hh, mm, ss, ms = (int(x) for x in m.groups())
    return hh * 3600 + mm * 60 + ss + ms / 1000.0


def _ass_timestamp(s: str) -> float:
    """ASS 的 `H:MM:SS.cc` → 秒。"""
    h, m, rest = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def parse_srt(text: str) -> List[Dict[str, Any]]:
    """SRT → 规范 cue 列表 `[{index, start, end, lines:[str,...]}]`。

    宽松：以含 `-->` 的行为时间行，其前一行若是纯数字即取为 index（无则 None），其后为文本。
    既吃严格 SRT（idx 行 + 时间行 + 文本），也吃无 index 的精简 SRT。"""
    cues: List[Dict[str, Any]] = []
    for block in re.split(r"\n\s*\n", (text or "").strip()):
        rows = [ln for ln in block.splitlines() if ln.strip()]
        ti = next((i for i, ln in enumerate(rows) if "-->" in ln), None)
        if ti is None:
            continue
        a, _, b = rows[ti].partition("-->")
        body = rows[ti + 1:]
        if not body:
            continue
        idx = int(rows[ti - 1]) if ti >= 1 and rows[ti - 1].strip().isdigit() else None
        cues.append({"index": idx, "start": parse_timestamp(a), "end": parse_timestamp(b), "lines": body})
    return cues


def parse_lrc(text: str, tail: float = 4.0) -> List[Dict[str, Any]]:
    """LRC → 规范 cue 列表。每行 end = 下一行 start，末行 start+tail。"""
    cues: List[Dict[str, Any]] = []
    for ln in (text or "").splitlines():
        m = _LRC_LINE.match(ln.strip())
        if m:
            t = int(m.group(1)) * 60 + float(m.group(2))
            cues.append({"index": None, "start": t, "end": None, "lines": [m.group(3).strip()]})
    for i in range(len(cues)):
        cues[i]["end"] = cues[i + 1]["start"] if i + 1 < len(cues) else cues[i]["start"] + tail
    return cues


def parse_ass(text: str) -> List[Dict[str, Any]]:
    """ASS 的 Dialogue 行 → 规范 cue 列表（剥 override tag、`\\N`→空格）。"""
    cues: List[Dict[str, Any]] = []
    for ln in (text or "").splitlines():
        if not ln.startswith("Dialogue:"):
            continue
        f = ln.split(",", 9)
        if len(f) < 10:
            continue
        body = re.sub(r"\{[^}]*\}", "", f[9]).replace("\\N", " ").strip()
        if body:
            cues.append({"index": None, "start": _ass_timestamp(f[1].strip()),
                         "end": _ass_timestamp(f[2].strip()), "lines": [body]})
    return cues


# ── 字体回退加载（路径解析纯函数·可测；truetype 惰性 import PIL） ──────────────

# 跨平台中文优先字体回退序（macOS 优先，Linux DejaVu 兜底）。调用方可传自己的 paths 覆盖。
DEFAULT_CJK_FONTS: Tuple[str, ...] = (
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)

_FONT_CACHE: Dict[Tuple[Any, int], Any] = {}


def resolve_font_path(paths: Optional[Sequence[str]] = None,
                      exists: Callable[[str], bool] = os.path.exists) -> Optional[str]:
    """回退序里第一条存在的字体路径；都不存在→None（调用方回退 load_default）。纯函数·可测。"""
    for p in (paths or DEFAULT_CJK_FONTS):
        if exists(p):
            return p
    return None


def load_font(size: float, paths: Optional[Sequence[str]] = None, min_size: int = 18):
    """按回退序加载字体（缓存）。size 夹到 ≥min_size。无可用字体或加载失败 → ImageFont.load_default。"""
    from PIL import ImageFont  # 惰性：本模块在无 PIL 环境仍可 import（解析/链路原语不需要 PIL）
    size = max(min_size, int(size))
    key = (tuple(paths) if paths else None, size)
    cached = _FONT_CACHE.get(key)
    if cached is not None:
        return cached
    p = resolve_font_path(paths)
    try:
        font = ImageFont.truetype(p, size) if p else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


# ── CJK 折行（需要 draw.textlength；用假 draw 即可单测） ─────────────────────

def wrap_cjk(draw: Any, text: str, font: Any, max_width: float) -> List[str]:
    """按像素宽折行：含 CJK 时逐字断、否则按空格断词，累计宽度超 max_width 换行。"""
    is_cjk = bool(_CJK.search(text or ""))
    tokens = list(text) if is_cjk else (text or "").split(" ")
    join = "" if is_cjk else " "
    out: List[str] = []
    cur = ""
    for t in tokens:
        trial = (cur + join + t).strip() if cur else t
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            if cur:
                out.append(cur)
            cur = t
    if cur:
        out.append(cur)
    return out


# ── ffmpeg overlay 链拼装（纯函数·无 PIL·字节级可复现既有输出） ──────────

def overlay_filter_chain(cues: Sequence[Tuple[float, float]], *, png_input_base: int,
                         first_input: str = "[0:v]", inter_prefix: str = "v",
                         pre_final: str = "[v]", overlay_xy: str = "",
                         format_tail: Optional[str] = None, format_final: str = "[v]") -> str:
    """把 N 张时间门控 PNG 拼成 ffmpeg overlay 滤镜链字符串。

    每张 PNG 是第 `png_input_base+k` 路输入，时间窗 `enable='between(t,start,end)'`。
    参数化便于 ad-compose 按不同输入布局复用，例如：
      - ad 烧字幕（底片在 0 路）：png_input_base=1, inter_prefix='s', pre_final='[v]',
              overlay_xy='0:0', format_tail='yuv420p', format_final='[v]'

    cues 为 (start, end) 秒序列。空列表：有 format_tail 时回 `<first>format=<tail><final>`，
    否则回 first_input。
    """
    if not cues:
        return f"{first_input}format={format_tail}{format_final}" if format_tail else first_input
    xy = f"{overlay_xy}:" if overlay_xy else ""
    chain: List[str] = []
    prev = first_input
    n = len(cues)
    for k, (s, e) in enumerate(cues):
        out = pre_final if k == n - 1 else f"[{inter_prefix}{k}]"
        chain.append(f"{prev}[{k + png_input_base}:v]overlay={xy}"
                     f"enable='between(t,{float(s):.3f},{float(e):.3f})'{out}")
        prev = out
    filt = ";".join(chain)
    if format_tail:
        filt += f";{pre_final}format={format_tail}{format_final}"
    return filt
