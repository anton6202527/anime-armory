#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# shared-watermark — 通用水印（公共能力，不属于任何生产线家族）。
# 一个工具同时处理【图片】和【视频】，两种水印：
#   --mode ai    合规 AI 标识（法律必做·只加不去）：右上角半透明可见提示 + 写元数据。
#   --mode brand 品牌/logo/账号水印：文字或 logo PNG，位置/透明度/大小可选。
# 本机 ffmpeg 是无 libass/drawtext 的精简版 → 一律 Pillow 渲染水印层再 overlay/合成。
# 输入是图(.png/.jpg/.jpeg/.webp)还是视频(.mp4/.mov/.mkv/.webm)按扩展名自动判定。
#
# 用法:
#   watermark.py <in> <out>                          # 默认 --mode ai，烧合规 AI 标识
#   watermark.py <in> <out> --mode ai --text "本视频含 AI 合成 / AI-generated"
#   watermark.py <in> <out> --mode brand --text "@我的账号" --pos br --opacity 0.8
#   watermark.py <in> <out> --mode brand --logo logo.png --pos br --scale 0.12
#
# 铁律：本工具只“加”水印，绝不提供“去”水印（中国《标识办法》禁止改/去 AI 水印）。
import sys, os, subprocess, shutil, argparse

FONTS = ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
IMG_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
VID_EXT = (".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi")
AI_TEXT_DEFAULT = "本内容含 AI 合成 / AI-generated"
AI_META = "AI-generated content; visible label embedded (do not remove)"
FF = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
FP = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"


def _font(px):
    from PIL import ImageFont
    fp = next((f for f in FONTS if os.path.exists(f)), None)
    return ImageFont.truetype(fp, px) if fp else ImageFont.load_default()


def _pos_xy(W, H, ew, eh, pos, margin):
    m = int(min(W, H) * margin)
    pos = (pos or "br").lower()
    x = {"tl": m, "bl": m, "tr": W - ew - m, "br": W - ew - m,
         "center": (W - ew) // 2}.get(pos, W - ew - m)
    y = {"tl": m, "tr": m, "bl": H - eh - m, "br": H - eh - m,
         "center": (H - eh) // 2}.get(pos, H - eh - m)
    return x, y


def _text_box_img(text, px, opacity, box=True):
    """把一行文字渲染成自适应大小的 RGBA 小图（可选半透明底）。"""
    from PIL import Image, ImageDraw
    font = _font(px)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bb = probe.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad = int(px * 0.5)
    img = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if box:
        d.rectangle([0, 0, img.width, img.height], fill=(0, 0, 0, int(140 * opacity)))
    d.text((pad, pad - bb[1]), text, font=font, fill=(255, 255, 255, int(235 * opacity)))
    return img


def _load_logo(path, W, scale, opacity):
    from PIL import Image
    if not os.path.exists(path):
        sys.exit(f"找不到 logo：{path}")
    logo = Image.open(path).convert("RGBA")
    tw = max(1, int(W * scale)); th = max(1, int(logo.height * tw / logo.width))
    logo = logo.resize((tw, th))
    if opacity < 1.0:
        logo.putalpha(logo.getchannel("A").point(lambda v: int(v * opacity)))
    return logo


def build_overlay(W, H, a):
    """返回一张 RGBA 全画幅透明水印层。

    ai 模式：右上角合规标识徽标（默认文案，强制醒目）。
    brand 模式：logo / 主文字 / 描述行 三者可任意组合，竖向堆成一个块，
                整块按 --pos 落位（logo 在上、主文字其次、描述行最小在下）。"""
    from PIL import Image
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    if a.mode == "ai":
        text = a.text or AI_TEXT_DEFAULT
        img = _text_box_img(text, max(18, int(H * a.fontscale)), 1.0, box=True)
        x, y = _pos_xy(W, H, img.width, img.height, a.pos or "tr", a.margin)
        layer.alpha_composite(img, (x, y))
        return layer

    # ---- brand：logo + 主文字 + 描述行（任意子集）竖向堆叠 ----
    elems = []
    if a.logo:
        elems.append(_load_logo(a.logo, W, a.scale, a.opacity))
    if a.text:
        elems.append(_text_box_img(a.text, max(18, int(H * a.fontscale)), a.opacity))
    if a.desc:
        elems.append(_text_box_img(a.desc, max(14, int(H * a.fontscale * a.descscale)), a.opacity))
    if not elems:
        sys.exit("brand 模式至少给 --logo / --text / --desc 之一")

    gap = int(H * 0.012)
    bw = max(e.width for e in elems)
    bh = sum(e.height for e in elems) + gap * (len(elems) - 1)
    block = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    cy = 0
    for e in elems:  # 每个元素水平居中对齐
        block.alpha_composite(e, ((bw - e.width) // 2, cy))
        cy += e.height + gap
    x, y = _pos_xy(W, H, bw, bh, a.pos or "br", a.margin)
    layer.alpha_composite(block, (x, y))
    return layer


def do_image(a):
    from PIL import Image
    base = Image.open(a.inp).convert("RGBA")
    W, H = base.size
    out = Image.alpha_composite(base, build_overlay(W, H, a))
    meta = a.meta or (AI_META if a.mode == "ai" else None)
    ext = os.path.splitext(a.out)[1].lower()
    if ext in (".jpg", ".jpeg"):
        rgb = out.convert("RGB")
        if meta:
            exif = rgb.getexif(); exif[0x010E] = meta  # ImageDescription
            rgb.save(a.out, quality=92, exif=exif)
        else:
            rgb.save(a.out, quality=92)
    elif meta and ext == ".png":
        from PIL.PngImagePlugin import PngInfo
        info = PngInfo(); info.add_text("Comment", meta)
        out.save(a.out, pnginfo=info)
    else:
        out.save(a.out)


def probe_wh(p):
    out = subprocess.run([FP, "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0:s=x", p],
                         capture_output=True, text=True).stdout.strip()
    w, h = out.split("x"); return int(w), int(h)


def do_video(a):
    W, H = probe_wh(a.inp)
    badge = os.path.join(os.path.dirname(os.path.abspath(a.out)) or ".", "_wm_overlay.png")
    build_overlay(W, H, a).save(badge)
    meta = a.meta or (AI_META if a.mode == "ai" else "watermark embedded")
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", a.inp, "-i", badge,
                    "-filter_complex", "[0:v][1:v]overlay=0:0[v]",
                    "-map", "[v]", "-map", "0:a?",
                    "-metadata", f"comment={meta}",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
                    a.out], check=True)
    os.path.exists(badge) and os.remove(badge)


def main():
    ap = argparse.ArgumentParser(description="通用水印：图/视频 · 合规AI标识 / 品牌logo")
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--mode", choices=["ai", "brand"], default="ai")
    ap.add_argument("--text", default=None, help="主文字水印")
    ap.add_argument("--desc", default=None, help="描述行（小字，配在 logo/主文字下方·仅 brand）")
    ap.add_argument("--logo", default=None)
    ap.add_argument("--pos", default=None, help="tl|tr|bl|br|center（ai默认tr，brand默认br）")
    ap.add_argument("--opacity", type=float, default=1.0, help="brand 文字/logo 透明度 0~1")
    ap.add_argument("--scale", type=float, default=0.12, help="brand logo 宽 / 画面宽")
    ap.add_argument("--fontscale", type=float, default=0.030, help="主文字字号 / 画面高")
    ap.add_argument("--descscale", type=float, default=0.62, help="描述行字号 / 主文字字号")
    ap.add_argument("--margin", type=float, default=0.02, help="边距 / min(W,H)")
    ap.add_argument("--meta", default=None, help="写入元数据 comment（ai 模式有默认值）")
    a = ap.parse_args()

    if not os.path.exists(a.inp):
        sys.exit(f"找不到输入：{a.inp}")
    ext = os.path.splitext(a.inp)[1].lower()
    if ext in IMG_EXT:
        do_image(a)
    elif ext in VID_EXT:
        do_video(a)
    else:
        sys.exit(f"无法判定图/视频（扩展名 {ext}）。图:{IMG_EXT} 视频:{VID_EXT}")

    kind = "AI 合规标识" if a.mode == "ai" else "品牌水印"
    print(f"[ok] 已烧{kind} + 写元数据 → {a.out}")
    if a.mode == "ai":
        print("     提醒：平台投放时按各平台要求补'隐式水印'；隐式标识不在本地工具范围。")
        print("     铁律：AI 标识只加不去——本工具不提供任何去水印能力。")


if __name__ == "__main__":
    main()
