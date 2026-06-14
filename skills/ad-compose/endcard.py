#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""品牌包装片尾 end card：logo + slogan + CTA 合成一张 PNG，供 ad-compose 接到成片尾。

广告独有的后端包装。无 libass 也能做（Pillow 渲染）。可选叠 logo 图片，背景用品牌色。
自包含；依赖 Pillow（与 n2d/mv 字幕渲染同栈）。

尺寸不再写死 1920x1080：可传 `--size WxH`，或传 `--aspect 9:16` 按比例推（竖版片尾不再被
拉成横版）。版式用 Pillow 实测文字高度堆叠 slogan / CTA，避免比例变化时 slogan 与 CTA 叠死。

用法：
    python3 endcard.py --out 合成/_work/endcard.png --size 1920x1080 \
        --bg "#E60012" --slogan "更轻盈的一天" --cta "立即体验" --logo 设定库/logo.png
    python3 endcard.py --out 合成/_work/endcard.png --aspect 9:16 --slogan ... --cta ...
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


def text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1], bbox


def text_center(draw, text, font, cy, w, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    # 用 bbox[1] 做基线偏移，cy 即文字顶
    draw.text(((w - tw) / 2, cy - bbox[1]), text, font=font, fill=fill)


def resolve_size(size, aspect, out_long=1920):
    """优先 --size WxH；否则按 --aspect 推（长边 out_long）。都没有 → 1920x1080。"""
    if size:
        w, h = (int(x) for x in size.lower().split("x"))
        return w - w % 2, h - h % 2
    if aspect:
        a, _, b = aspect.replace("x", ":").partition(":")
        av = float(a) / float(b)
        if av >= 1:
            w, h = out_long, round(out_long / av)
        else:
            h, w = out_long, round(out_long * av)
        return w - w % 2, h - h % 2
    return 1920, 1080


def main():
    ap = argparse.ArgumentParser(description="品牌包装片尾 end card 生成")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default=None, help="WxH，如 1920x1080；不传则用 --aspect 推")
    ap.add_argument("--aspect", default=None, help="比例，如 16:9 / 9:16 / 1:1（--size 缺省时用）")
    ap.add_argument("--out-long", type=int, default=1920, help="--aspect 推尺寸时的长边像素")
    ap.add_argument("--bg", default="#000000", help="背景色（品牌色）HEX")
    ap.add_argument("--fg", default="#FFFFFF", help="文字色 HEX")
    ap.add_argument("--slogan", default="")
    ap.add_argument("--cta", default="")
    ap.add_argument("--logo", default=None, help="logo PNG 路径（可选）")
    args = ap.parse_args()

    w, h = resolve_size(args.size, args.aspect, args.out_long)
    img = Image.new("RGB", (w, h), hex_to_rgb(args.bg))
    draw = ImageDraw.Draw(img)
    fg = hex_to_rgb(args.fg)

    # 实测各块高度，自上而下顺序堆叠（带间距），不靠写死的 0.12/0.04 比例叠死。
    y = h * 0.30
    gap = h * 0.045

    if args.logo and os.path.isfile(args.logo):
        try:
            logo = Image.open(args.logo).convert("RGBA")
            scale = (w * 0.32) / logo.width
            logo = logo.resize((int(logo.width * scale), int(logo.height * scale)))
            img.paste(logo, (int((w - logo.width) / 2), int(y)), logo)
            y += logo.height + gap
        except Exception as e:
            print(f"[warn] logo 加载失败：{e}", file=sys.stderr)

    if args.slogan:
        sfont = load_font(int(h * 0.075))
        _, sth, _ = text_size(draw, args.slogan, sfont)
        text_center(draw, args.slogan, sfont, y, w, fg)
        y += sth + gap

    if args.cta:
        # CTA 做成胶囊按钮感（用实测高度算胶囊，不与 slogan 叠死）
        font = load_font(int(h * 0.045))
        tw, th, bbox = text_size(draw, args.cta, font)
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
