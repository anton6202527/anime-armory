#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""字幕 PNG 渲染（本机 ffmpeg 无 libass/drawtext，走 Pillow 渲 PNG + overlay）。

读 SRT → 每条字幕渲一张透明 PNG（带描边，安全框内居中底部），输出 PNG + overlay 时间表，
供 compose.sh 用 ffmpeg overlay 烧进成片。SRT 解析/字体回退复用 common/subtitle_render
共享原语；描边/版式/overlay_table 本地保留。依赖 Pillow。

用法：
    python3 render_subs.py 脚本/字幕_zh.srt --out-dir 合成/_work/subs --size 1920x1080
"""
import argparse
import json
import os
import re
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("[err] 需要 Pillow", file=sys.stderr)
    sys.exit(2)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ad", "_lib"))
import subtitle_render as sr  # 本线自包含原语（vendored ad/_lib）：SRT 解析 / 字体回退

AD_FONTS = ("/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def render(blocks, out_dir, w, h, safe=0.90):
    os.makedirs(out_dir, exist_ok=True)
    font = sr.load_font(int(h * 0.05), paths=AD_FONTS)
    table = []
    for i, blk in enumerate(blocks):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        lines = blk["text"].split("\n")
        total_h = sum(draw.textbbox((0, 0), ln, font=font)[3] for ln in lines) + (len(lines) - 1) * 8
        y = h * safe - total_h
        for ln in lines:
            bbox = draw.textbbox((0, 0), ln, font=font)
            tw = bbox[2] - bbox[0]
            x = (w - tw) / 2
            # 描边
            for dx in (-2, -1, 0, 1, 2):
                for dy in (-2, -1, 0, 1, 2):
                    draw.text((x + dx, y + dy), ln, font=font, fill=(0, 0, 0, 220))
            draw.text((x, y), ln, font=font, fill=(255, 255, 255, 255))
            y += bbox[3] + 8
        png = os.path.join(out_dir, f"sub_{i:04d}.png")
        img.save(png)
        table.append({"png": png, "start": blk["start"], "end": blk["end"]})
    return table


def main():
    ap = argparse.ArgumentParser(description="字幕 PNG 渲染（无 libass）")
    ap.add_argument("srt")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--size", default="1920x1080")
    args = ap.parse_args()
    if not os.path.isfile(args.srt):
        print(f"[err] 缺 {args.srt}", file=sys.stderr)
        sys.exit(2)
    w, h = (int(x) for x in args.size.lower().split("x"))
    with open(args.srt, encoding="utf-8") as f:
        blocks = [{"start": c["start"], "end": c["end"], "text": "\n".join(c["lines"])}
                  for c in sr.parse_srt(f.read())]
    table = render(blocks, args.out_dir, w, h)
    with open(os.path.join(args.out_dir, "overlay_table.json"), "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, indent=2)
    print(f"[ok] 渲染 {len(table)} 条字幕 PNG → {args.out_dir}")


if __name__ == "__main__":
    main()
