#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# mv 自带歌词渲染器（无 libass 时的字幕降级）——把 .lrc / .ass 渲染成逐行透明 PNG，
# 并产出 ffmpeg overlay 用的 sub_inputs.txt + sub_filter.txt。解析/字体/overlay 链复用
# common/subtitle_render 共享原语（不依赖其他生产线 skill）；逐行描边/版式本地保留。
# 用法: render_lyrics.py <src .lrc|.ass> <workdir> <W> <H>
import sys, os

SRC, WK, W, H = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mv", "_lib"))
import subtitle_render as sr  # 本线自包含原语（vendored mv/_lib）：LRC/ASS 解析 / 字体回退 / overlay 链

MV_FONTS = ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def main():
    txt = open(SRC, encoding='utf-8').read()
    cues = sr.parse_ass(txt) if SRC.lower().endswith('.ass') else sr.parse_lrc(txt)
    if not cues:
        sys.exit("无可渲染歌词行")
    from PIL import Image, ImageDraw
    fsize = int(H * 0.055)
    font = sr.load_font(fsize, paths=MV_FONTS)

    inputs = []
    for i, c in enumerate(cues):
        text = " ".join(c["lines"])
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        bb = d.textbbox((0, 0), text, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        x, y = (W - tw) // 2, int(H * 0.82)
        for dx in (-2, 2):                            # 描边
            for dy in (-2, 2):
                d.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 230))
        d.text((x, y), text, font=font, fill=(255, 255, 255, 255))
        p = os.path.join(WK, f"lyric_{i:03d}.png"); img.save(p)
        inputs.append(p)
    # 输入序号：silent.mp4=0, song=1, PNG 从 2 起
    filt = sr.overlay_filter_chain([(c["start"], c["end"]) for c in cues],
                                   png_input_base=2, inter_prefix="s", pre_final="[v]")
    open(os.path.join(WK, "sub_inputs.txt"), "w").write("\n".join(inputs))
    open(os.path.join(WK, "sub_filter.txt"), "w").write(filt)
    print(f"render_lyrics: {len(cues)} 行 → PNG + sub_filter.txt")


if __name__ == "__main__":
    main()
