#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# image-faceswap 强制 AI 标识（法律必做）——给换脸图片烧"可见提示"+ 写元数据。
# 自包含：Pillow 在角落合成半透明标识 + 写图片元数据（PNG comment / JPEG EXIF ImageDescription）。
# 用法: label_watermark_image.py <in.png|jpg> <out.png|jpg> [提示文字]
# 注：本工具只"加"标识，绝不提供"去"标识（中国《标识办法》禁止改 AI 水印）。
import sys, os

IN, OUT = sys.argv[1], sys.argv[2]
TEXT = sys.argv[3] if len(sys.argv) > 3 else "本图含 AI 换脸合成 / AI-generated"
META = "AI-generated face swap (consented); label embedded"
FONTS = ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def main():
    if not os.path.exists(IN):
        sys.exit(f"找不到输入：{IN}")
    from PIL import Image, ImageDraw, ImageFont

    base = Image.open(IN).convert("RGBA")
    W, H = base.size
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    fs = max(18, int(H * 0.030))
    fp = next((f for f in FONTS if os.path.exists(f)), None)
    font = ImageFont.truetype(fp, fs) if fp else ImageFont.load_default()
    bb = d.textbbox((0, 0), TEXT, font=font); tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad = int(fs * 0.5); x = W - tw - pad * 2 - int(W * 0.02); y = int(H * 0.03)
    d.rectangle([x, y, x + tw + pad * 2, y + th + pad * 2], fill=(0, 0, 0, 140))  # 半透明底
    d.text((x + pad, y + pad - bb[1]), TEXT, font=font, fill=(255, 255, 255, 235))
    out = Image.alpha_composite(base, overlay)

    ext = os.path.splitext(OUT)[1].lower()
    if ext in (".jpg", ".jpeg"):
        rgb = out.convert("RGB")
        exif = rgb.getexif()
        exif[0x010E] = META  # ImageDescription
        rgb.save(OUT, quality=92, exif=exif)
    else:
        from PIL.PngImagePlugin import PngInfo
        info = PngInfo(); info.add_text("Comment", META)
        out.save(OUT, pnginfo=info)
    print(f"[ok] 已烧 AI 可见标识 + 写元数据 → {OUT}")
    print("     提醒：平台投放时按各平台要求补'隐式水印'；隐式标识不在本地工具范围。")


if __name__ == "__main__":
    main()
