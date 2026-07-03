#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 由 ASR 时间戳 + 校正歌词，生成 字幕/lyrics.lrc + karaoke.ass（存档），
# 并用 Pillow 渲染逐行透明 PNG + 输出 overlay 滤镜链（烧到 成片_MV.mp4 上）。
# 跑：conda run -n cosyvoice python 字幕/_build_subs.py
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
PNG = os.path.join(ROOT, "_png"); os.makedirs(PNG, exist_ok=True)
W, H = 1080, 1920
FONTS = ["/System/Library/Fonts/Supplemental/Songti.ttc",
         "/System/Library/Fonts/STHeiti Medium.ttc",
         "/System/Library/Fonts/Hiragino Sans GB.ttc"]

# (start, end, 正确歌词)  —— whisper 听到副歌(有错别字)，按已知歌词校正，沿用 ASR 时间
LINES = [
    (2.84, 4.88, "我仗剑下山，闯一闯这人间"),
    (4.88, 7.60, "江湖那么大，我偏要走在最前"),
    (7.60, 9.56, "风雪也好，刀光也好"),
    (9.56, 11.20, "我都不躲不闪"),
    (11.20, 12.94, "醉过痛过输过，也曾热血滔过天"),
    (12.94, 16.56, "回头时，我还是当年那张笑脸"),
]


def lrc_ts(t):
    m = int(t // 60); return f"[{m:02d}:{t-60*m:05.2f}]"


def ass_ts(t):
    h = int(t // 3600); m = int((t % 3600)//60); return f"{h:d}:{m:02d}:{t%60:05.2f}"


# 存档 LRC / ASS
with open(f"{ROOT}/lyrics.lrc", "w", encoding="utf-8") as f:
    f.write("[ti:仗剑下山]\n[ar:ACE-Step demo]\n")
    for s, e, t in LINES:
        f.write(f"{lrc_ts(s)}{t}\n")
ass_head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, "
            "BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: zh, Songti SC, 54, &H00FFFFFF, &H00202020, &H64000000, 1, 1, 3, 1, 2, 60, 60, 320, 1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
with open(f"{ROOT}/karaoke.ass", "w", encoding="utf-8") as f:
    f.write(ass_head)
    for s, e, t in LINES:
        f.write(f"Dialogue: 0,{ass_ts(s)},{ass_ts(e)},zh,,0,0,0,,{t}\n")

# 渲染 PNG
font_path = next(f for f in FONTS if os.path.exists(f))
font = ImageFont.truetype(font_path, 60)
for i, (s, e, t) in enumerate(LINES):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bb = d.textbbox((0, 0), t, font=font)
    tw = bb[2] - bb[0]
    x, y = (W - tw)//2 - bb[0], H - 360
    for dx in (-3, -2, 2, 3):
        for dy in (-3, -2, 2, 3):
            d.text((x+dx, y+dy), t, font=font, fill=(0, 0, 0, 235))
    d.text((x, y), t, font=font, fill=(255, 240, 220, 255))  # 暖白，古风
    img.save(f"{PNG}/l{i}.png")

# overlay 滤镜链：base=[0:v]，PNG 从 [1:v]
parts, prev = [], "[0:v]"
for i, (s, e, t) in enumerate(LINES):
    out = "[v]" if i == len(LINES)-1 else f"[s{i}]"
    parts.append(f"{prev}[{i+1}:v]overlay=0:0:enable='between(t,{s},{e})'{out}")
    prev = out
open(f"{ROOT}/_overlay.filter", "w", encoding="utf-8").write(";".join(parts))
# PNG 输入列表（给 ffmpeg -i 用）
open(f"{ROOT}/_png_list.txt", "w").write("\n".join(f"{PNG}/l{i}.png" for i in range(len(LINES))))
print(f"[ok] {len(LINES)} 行 → PNG + _overlay.filter（字体 {os.path.basename(font_path)}）")
