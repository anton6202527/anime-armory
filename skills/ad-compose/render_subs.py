#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""字幕 PNG 渲染（本机 ffmpeg 无 libass/drawtext，走 Pillow 渲 PNG + overlay）。

读 SRT → 每条字幕渲一张透明 PNG（带描边，安全框内居中底部），输出 PNG + overlay 时间表
+ ffmpeg overlay 滤镜链字符串，供 compose.sh 用 ffmpeg overlay 烧进成片。

SRT 解析 / 字体回退 / overlay 链拼装用 `ad/_lib/subtitle_render.py`（ad 线自带原语，本线私有）；
描边 / 版式 / overlay_table 命名在本文件保留。依赖 Pillow。

产出（写到 --out-dir）：
  - sub_NNNN.png        逐句透明字幕 PNG
  - overlay_table.json  [{png, start, end}]（人读 / 调试 / deliver 对账）
  - vfilter.txt         ffmpeg overlay 滤镜链（compose.sh 直接 -filter_complex 消费）

用法：
    python3 render_subs.py 脚本/字幕_zh.srt --out-dir 合成/_work/subs --size 1920x1080 \
        --png-input-base 1
"""
import argparse
import json
import os
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("[err] 需要 Pillow", file=sys.stderr)
    sys.exit(2)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ad", "_lib"))
import subtitle_render as sr  # 本线自带原语（vendored ad/_lib）：SRT 解析 / 字体回退 / overlay 链

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
    ap.add_argument("--png-input-base", type=int, default=1,
                    help="overlay 链里第一张字幕 PNG 的 ffmpeg 输入序号"
                         "（compose.sh 烧字幕时 0=底片视频，PNG 从 1 开始）")
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

    # compose.sh 消费的两件产物：inputs.txt（PNG 路径，按序 -i 喂给 ffmpeg）+ vfilter.txt（overlay 链）
    with open(os.path.join(args.out_dir, "inputs.txt"), "w", encoding="utf-8") as f:
        for row in table:
            f.write(row["png"] + "\n")
    vfilter = sr.overlay_filter_chain(
        [(row["start"], row["end"]) for row in table],
        png_input_base=args.png_input_base, first_input="[0:v]",
        inter_prefix="s", pre_final="[v]", overlay_xy="0:0",
        format_tail="yuv420p", format_final="[v]")
    with open(os.path.join(args.out_dir, "vfilter.txt"), "w", encoding="utf-8") as f:
        f.write(vfilter)
    print(f"[ok] 渲染 {len(table)} 条字幕 PNG → {args.out_dir}"
          f"（overlay_table.json + inputs.txt + vfilter.txt）")


if __name__ == "__main__":
    main()
