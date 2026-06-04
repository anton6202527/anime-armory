#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# video-faceswap 强制 AI 标识（法律必做）——给换脸视频烧"可见提示"+ 写元数据。
# 自包含：Pillow 渲染标识 PNG → ffmpeg 全程 overlay + 写 comment 元数据。
# 用法: label_watermark.py <in.mp4> <out.mp4> [提示文字]
# 注：本工具只"加"标识，绝不提供"去"标识（中国《标识办法》禁止改 AI 水印）。
import sys, os, subprocess, shutil

IN, OUT = sys.argv[1], sys.argv[2]
TEXT = sys.argv[3] if len(sys.argv) > 3 else "本视频含 AI 换脸合成 / AI-generated"
FF = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
FP = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
FONTS = ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def probe_wh(p):
    out = subprocess.run([FP, "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0:s=x", p],
                         capture_output=True, text=True).stdout.strip()
    w, h = out.split("x"); return int(w), int(h)


def main():
    if not os.path.exists(IN):
        sys.exit(f"找不到输入：{IN}")
    W, H = probe_wh(IN)
    from PIL import Image, ImageDraw, ImageFont
    wk = os.path.dirname(os.path.abspath(OUT)) or "."
    badge = os.path.join(wk, "_ai_badge.png")
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fs = max(18, int(H * 0.030))
    fp = next((f for f in FONTS if os.path.exists(f)), None)
    font = ImageFont.truetype(fp, fs) if fp else ImageFont.load_default()
    bb = d.textbbox((0, 0), TEXT, font=font); tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad = int(fs * 0.5); x = W - tw - pad * 2 - int(W * 0.02); y = int(H * 0.03)
    d.rectangle([x, y, x + tw + pad * 2, y + th + pad * 2], fill=(0, 0, 0, 140))  # 半透明底
    d.text((x + pad, y + pad - bb[1]), TEXT, font=font, fill=(255, 255, 255, 235))
    img.save(badge)

    # 全程 overlay + 写元数据（标注 AI 合成，便于溯源）
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", IN, "-i", badge,
                    "-filter_complex", "[0:v][1:v]overlay=0:0[v]",
                    "-map", "[v]", "-map", "0:a?",
                    "-metadata", "comment=AI-generated face swap (consented); label embedded",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "copy", "-movflags", "+faststart", OUT], check=True)
    print(f"[ok] 已烧 AI 可见标识 + 写元数据 → {OUT}")
    print("     提醒：平台投放时按各平台要求补'隐式水印'；隐式标识不在本地工具范围。")


if __name__ == "__main__":
    main()
