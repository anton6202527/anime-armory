#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# mv 自带歌词渲染器（无 libass 时的字幕降级）——把 .lrc / .ass 渲染成逐行透明 PNG，
# 并产出 ffmpeg overlay 用的 sub_inputs.txt + sub_filter.txt。完全独立，不依赖其他 skill。
# 用法: render_lyrics.py <src .lrc|.ass> <workdir> <W> <H>
import sys, os, re

SRC, WK, W, H = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
FONTS = ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
         "/System/Library/Fonts/Hiragino Sans GB.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def parse_lrc(txt):
    out = []
    for ln in txt.splitlines():
        m = re.match(r'\[(\d+):(\d+(?:\.\d+)?)\]\s*(.+)', ln.strip())
        if m:
            t = int(m.group(1)) * 60 + float(m.group(2))
            out.append([t, None, m.group(3).strip()])
    for i in range(len(out)):                         # end = 下行 start，末行 +4s
        out[i][1] = out[i + 1][0] if i + 1 < len(out) else out[i][0] + 4
    return out


def _ass_t(s):
    h, m, rest = s.split(':'); return int(h) * 3600 + int(m) * 60 + float(rest)


def parse_ass(txt):
    out = []
    for ln in txt.splitlines():
        if ln.startswith('Dialogue:'):
            f = ln.split(',', 9)
            if len(f) >= 10:
                text = re.sub(r'\{[^}]*\}', '', f[9]).replace('\\N', ' ').strip()
                if text: out.append([_ass_t(f[1].strip()), _ass_t(f[2].strip()), text])
    return out


def main():
    txt = open(SRC, encoding='utf-8').read()
    lines = parse_ass(txt) if SRC.lower().endswith('.ass') else parse_lrc(txt)
    if not lines:
        sys.exit("无可渲染歌词行")
    from PIL import Image, ImageDraw, ImageFont
    font_path = next((f for f in FONTS if os.path.exists(f)), None)
    fsize = int(H * 0.055)
    font = ImageFont.truetype(font_path, fsize) if font_path else ImageFont.load_default()

    inputs, filt = [], ""
    for i, (st, en, text) in enumerate(lines):
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
        src = "[0:v]" if i == 0 else f"[s{i-1}]"
        out = "[v]" if i == len(lines) - 1 else f"[s{i}]"
        # 输入序号：silent.mp4=0, song=1, PNG 从 2 起
        filt += f"{src}[{i+2}:v]overlay=enable='between(t,{st:.3f},{en:.3f})'{out};"
    filt = filt.rstrip(';')
    open(os.path.join(WK, "sub_inputs.txt"), "w").write("\n".join(inputs))
    open(os.path.join(WK, "sub_filter.txt"), "w").write(filt)
    print(f"render_lyrics: {len(lines)} 行 → PNG + sub_filter.txt")


if __name__ == "__main__":
    main()
