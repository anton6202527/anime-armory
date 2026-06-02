#!/usr/bin/env python3
# 把中/英 SRT 渲染成逐句透明 PNG（1080x1920），供 ffmpeg overlay 烧录。
# 用法: _render_subs.py <workdir> <zh|en|bilingual>
# 产出: <workdir>/subpng/sub_NN.png + 写 inputs.txt(png路径) + vfilter.txt(overlay链)
import sys, os, re

W, MODE = sys.argv[1], sys.argv[2]
from PIL import Image, ImageDraw, ImageFont

ZH_FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
EN_FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
if not os.path.exists(EN_FONT):
    EN_FONT = "/System/Library/Fonts/Helvetice.ttc" if os.path.exists("/System/Library/Fonts/Helvetice.ttc") else ZH_FONT
WIDTH, HEIGHT = 1080, 1920

def parse_srt(path):
    cues = {}
    if not os.path.exists(path): return cues
    blocks = re.split(r'\n\s*\n', open(path, encoding='utf-8').read().strip())
    for b in blocks:
        lines = [l for l in b.splitlines() if l.strip() != '']
        if len(lines) < 2: continue
        idx = int(re.match(r'\d+', lines[0]).group())
        m = re.search(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)', lines[1])
        if not m: continue
        g = list(map(int, m.groups()))
        s = g[0]*3600+g[1]*60+g[2]+g[3]/1000.0
        e = g[4]*3600+g[5]*60+g[6]+g[7]/1000.0
        text = [l for l in lines[2:]]
        cues[idx] = (s, e, text)
    return cues

zh = parse_srt(os.path.join(W, 'zh.srt'))
en = parse_srt(os.path.join(W, 'en.srt'))
idxs = sorted(set(zh) | set(en))

ZH_SIZE = int(os.environ.get('ZH_SIZE', 50))   # 原58→50 调小一号
EN_SIZE = int(os.environ.get('EN_SIZE', 34))
zh_font = ImageFont.truetype(ZH_FONT, ZH_SIZE)
en_font = ImageFont.truetype(EN_FONT, EN_SIZE)

def wrap(draw, text, font, maxw):
    # 按字符/单词折行，超过 maxw 像素换行
    out, cur = [], ''
    tokens = list(text) if re.search(r'[一-鿿]', text) else text.split(' ')
    join = '' if re.search(r'[一-鿿]', text) else ' '
    for t in tokens:
        trial = (cur + join + t).strip() if cur else t
        if draw.textlength(trial, font=font) <= maxw:
            cur = trial
        else:
            if cur: out.append(cur)
            cur = t
    if cur: out.append(cur)
    return out

os.makedirs(os.path.join(W, 'subpng'), exist_ok=True)
manifest = []
MAXW = WIDTH - 120
for i in idxs:
    img = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
    d = ImageDraw.Draw(img)
    s = (zh.get(i) or en.get(i))[0]
    e = (zh.get(i) or en.get(i))[1]
    zh_lines, en_lines = [], []
    if MODE in ('zh','bilingual') and i in zh:
        for ln in zh[i][2]: zh_lines += wrap(d, ln, zh_font, MAXW)
    if MODE in ('en','bilingual') and i in en:
        for ln in en[i][2]: en_lines += wrap(d, ln, en_font, MAXW)
    # 自底向上排版：英文在最底，中文在其上
    y = HEIGHT - 130
    def draw_line(text, font, fill, stroke, y_baseline):
        d.text((WIDTH//2, y_baseline), text, font=font, fill=fill,
               anchor='ms', stroke_width=stroke, stroke_fill=(10,10,10,255))
    for ln in reversed(en_lines):
        draw_line(ln, en_font, (235,235,235,255), 3, y); y -= EN_SIZE+12
    if en_lines and zh_lines: y -= 8
    for ln in reversed(zh_lines):
        draw_line(ln, zh_font, (255,255,255,255), 4, y); y -= ZH_SIZE+14
    p = os.path.join(W, 'subpng', f'sub_{i:02d}.png')
    img.save(p)
    manifest.append((p, s, e))

# 写 inputs 与 overlay 链（ffmpeg 输入序: 0=concat 1=bgm，png 从 2 开始）
with open(os.path.join(W,'inputs.txt'),'w') as f:
    for p,_,_ in manifest: f.write(p+'\n')
chain, prev = [], '[0:v]'
n = len(manifest)
for k,(p,s,e) in enumerate(manifest):
    inp = k+2
    out = '[vsub]' if k == n-1 else f'[v{k}]'
    chain.append(f"{prev}[{inp}:v]overlay=0:0:enable='between(t,{s:.3f},{e:.3f})'{out}")
    prev = out
if n:
    filt = ';'.join(chain) + ';[vsub]format=yuv420p[v]'
else:
    filt = '[0:v]format=yuv420p[v]'
open(os.path.join(W,'vfilter.txt'),'w').write(filt)
print(f"渲染 {len(manifest)} 句字幕 PNG，模式={MODE}")
