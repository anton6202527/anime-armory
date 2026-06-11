#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""品牌包装片尾 end card：logo + slogan + CTA 合成一张 PNG，供 ad-compose 接到成片尾。

广告独有的后端包装。无 libass 也能做（Pillow 渲染）。可选叠 logo 图片，背景用品牌色。
自包含；依赖 Pillow（与 n2d/mv 字幕渲染同栈）。

用法：
    python3 endcard.py --out 合成/_work/endcard.png --size 1920x1080 \
        --bg "#E60012" --slogan "更轻盈的一天" --cta "立即体验" --logo 设定库/logo.png
"""
import argparse
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("[err] 需要 Pillow：pip install Pillow（或在带 Pillow 的 env 里跑）", file=sys.stderr)
    sys.exit(2)


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def load_font(size):
    for p in ("/System/Library/Fonts/PingFang.ttc",
              "/System/Library/Fonts/STHeiti Medium.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def text_center(draw, text, font, cy, w, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) / 2, cy), text, font=font, fill=fill)


def main():
    ap = argparse.ArgumentParser(description="品牌包装片尾 end card 生成")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--bg", default="#000000", help="背景色（品牌色）HEX")
    ap.add_argument("--fg", default="#FFFFFF", help="文字色 HEX")
    ap.add_argument("--slogan", default="")
    ap.add_argument("--cta", default="")
    ap.add_argument("--logo", default=None, help="logo PNG 路径（可选）")
    args = ap.parse_args()

    w, h = (int(x) for x in args.size.lower().split("x"))
    img = Image.new("RGB", (w, h), hex_to_rgb(args.bg))
    draw = ImageDraw.Draw(img)
    fg = hex_to_rgb(args.fg)

    y = h * 0.30
    if args.logo and os.path.isfile(args.logo):
        try:
            logo = Image.open(args.logo).convert("RGBA")
            scale = (w * 0.32) / logo.width
            logo = logo.resize((int(logo.width * scale), int(logo.height * scale)))
            img.paste(logo, (int((w - logo.width) / 2), int(y)), logo)
            y += logo.height + h * 0.04
        except Exception as e:
            print(f"[warn] logo 加载失败：{e}", file=sys.stderr)

    if args.slogan:
        text_center(draw, args.slogan, load_font(int(h * 0.075)), y, w, fg)
        y += h * 0.12
    if args.cta:
        # CTA 做成胶囊按钮感
        font = load_font(int(h * 0.045))
        bbox = draw.textbbox((0, 0), args.cta, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad_x, pad_y = th * 0.9, th * 0.5
        bx0 = (w - tw) / 2 - pad_x
        bx1 = (w + tw) / 2 + pad_x
        draw.rounded_rectangle([bx0, y, bx1, y + th + pad_y * 2], radius=th, fill=fg)
        draw.text(((w - tw) / 2, y + pad_y - bbox[1]), args.cta, font=font, fill=hex_to_rgb(args.bg))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    img.save(args.out)
    print(f"[ok] end card：{args.out}  ({w}x{h}, bg={args.bg})")


if __name__ == "__main__":
    main()
