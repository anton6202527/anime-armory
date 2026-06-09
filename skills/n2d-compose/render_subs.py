#!/usr/bin/env python3
# 把中/英 SRT 渲染成逐句透明 PNG（1080x1920），供 ffmpeg overlay 烧录。
# 用法: render_subs.py <workdir> <zh|en|bilingual>
# 产出: <workdir>/subpng/sub_NN.png + 写 inputs.txt(png路径) + vfilter.txt(overlay链)
import sys, os, re

if len(sys.argv) < 3:
    print("usage: render_subs.py <workdir> <zh|en|bilingual>", file=sys.stderr)
    sys.exit(2)
W, MODE = sys.argv[1], sys.argv[2]
from PIL import Image, ImageDraw, ImageFont

ZH_FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
EN_FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
if not os.path.exists(EN_FONT):
    EN_FONT = "/System/Library/Fonts/Helvetica.ttc" if os.path.exists("/System/Library/Fonts/Helvetica.ttc") else ZH_FONT
WIDTH  = int(os.environ.get('SUB_W', 1080))   # 由 compose.sh 按画幅选择点透传（竖屏 1080 / 横屏 1920）
HEIGHT = int(os.environ.get('SUB_H', 1920))

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

# ── 字幕样式分级（cue 标签 → 字号/颜色）。默认=normal 即原行为，全部 env 可覆盖 ──
# 标签来自 时长清单.json（compose.sh 复制为 W/manifest.json）：角色含"系统/旁白"→narrator；钩子=climax→emphasis。
import json as _json
TAGS = {}   # cue_idx(1-based) -> 'normal'|'narrator'|'emphasis'
_mf = os.path.join(W, 'manifest.json')
if os.path.exists(_mf):
    try:
        for k, r in enumerate(_json.load(open(_mf, encoding='utf-8'))):
            cue = int(r.get('idx', k)) + 1   # manifest idx 0-based → SRT cue 1-based
            role = str(r.get('角色', '')); hook = str(r.get('钩子', ''))
            if ('系统' in role) or ('旁白' in role): TAGS[cue] = 'narrator'
            elif hook == 'climax': TAGS[cue] = 'emphasis'
    except Exception:
        TAGS = {}
# 每级 (中字号增量, 中色RGBA, 英字号增量, 英色RGBA)；env 覆盖键见注释
STYLES = {
    'normal':   (0,                                  (255,255,255,255), 0,                                  (235,235,235,255)),
    'narrator': (int(os.environ.get('NARR_DZH',-8)), (205,205,205,235), int(os.environ.get('NARR_DEN',-4)), (200,200,200,225)),  # 旁白/系统：小一号、灰
    'emphasis': (int(os.environ.get('EMPH_DZH', 6)), (255,225,120,255), int(os.environ.get('EMPH_DEN', 2)), (255,225,120,255)),  # 爽点：大一号、暖金
}
_fcache = {}
def _font(path, size):
    size = max(18, size)
    if (path, size) not in _fcache: _fcache[(path, size)] = ImageFont.truetype(path, size)
    return _fcache[(path, size)]

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
# 垂直安全区：字幕总高超过画面这一比例就缩字号（治长双语句顶出画面/叠死画面元素）
MAXH = int(HEIGHT * float(os.environ.get('SUB_MAXH_FRAC', '0.45')))
overflow_hits = 0

def _layout(d, i, zh_sz, en_sz):
    zh_font = _font(ZH_FONT, zh_sz); en_font = _font(EN_FONT, en_sz)
    zh_lines, en_lines = [], []
    if MODE in ('zh','bilingual') and i in zh:
        for ln in zh[i][2]: zh_lines += wrap(d, ln, zh_font, MAXW)
    if MODE in ('en','bilingual') and i in en:
        for ln in en[i][2]: en_lines += wrap(d, ln, en_font, MAXW)
    total_h = len(en_lines)*(en_sz+12) + (8 if (en_lines and zh_lines) else 0) + len(zh_lines)*(zh_sz+14)
    return zh_font, en_font, zh_lines, en_lines, total_h

for i in idxs:
    img = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
    d = ImageDraw.Draw(img)
    s = (zh.get(i) or en.get(i))[0]
    e = (zh.get(i) or en.get(i))[1]
    # 本句样式分级
    dzh, zh_fill, den, en_fill = STYLES[TAGS.get(i, 'normal')]
    zh_sz = ZH_SIZE + dzh; en_sz = EN_SIZE + den
    zh_font, en_font, zh_lines, en_lines, total_h = _layout(d, i, zh_sz, en_sz)
    # 溢出保护：逐步缩字号直到落进安全区或触到字号下限（18）
    if total_h > MAXH:
        overflow_hits += 1
        while total_h > MAXH and zh_sz > 18 and en_sz > 16:
            zh_sz -= 2; en_sz -= 2
            zh_font, en_font, zh_lines, en_lines, total_h = _layout(d, i, zh_sz, en_sz)
    # 自底向上排版：英文在最底，中文在其上
    y = HEIGHT - 130
    def draw_line(text, font, fill, stroke, y_baseline):
        d.text((WIDTH//2, y_baseline), text, font=font, fill=fill,
               anchor='ms', stroke_width=stroke, stroke_fill=(10,10,10,255))
    for ln in reversed(en_lines):
        draw_line(ln, en_font, en_fill, 3, y); y -= en_sz+12
    if en_lines and zh_lines: y -= 8
    for ln in reversed(zh_lines):
        draw_line(ln, zh_font, zh_fill, 4, y); y -= zh_sz+14
    p = os.path.join(W, 'subpng', f'sub_{i:02d}.png')
    img.save(p)
    manifest.append((p, s, e))

# 写 inputs 与 overlay 链（ffmpeg 输入序: 0=concat 1=bgm 2=clip_audio，png 从 PNG_INPUT_BASE 开始）
# compose.sh 始终传 PNG_INPUT_BASE=3（含 clip_audio 输入）；默认值与之对齐，便于独立跑。
PNG_INPUT_BASE = int(os.environ.get('PNG_INPUT_BASE', '3'))
with open(os.path.join(W,'inputs.txt'),'w') as f:
    for p,_,_ in manifest: f.write(p+'\n')
chain, prev = [], '[0:v]'
n = len(manifest)
for k,(p,s,e) in enumerate(manifest):
    inp = k + PNG_INPUT_BASE
    out = '[vsub]' if k == n-1 else f'[v{k}]'
    chain.append(f"{prev}[{inp}:v]overlay=0:0:enable='between(t,{s:.3f},{e:.3f})'{out}")
    prev = out
if n:
    filt = ';'.join(chain) + ';[vsub]format=yuv420p[v]'
else:
    filt = '[0:v]format=yuv420p[v]'
open(os.path.join(W,'vfilter.txt'),'w').write(filt)
print(f"渲染 {len(manifest)} 句字幕 PNG，模式={MODE}，画幅 {WIDTH}x{HEIGHT}"
      + (f"；⚠️ {overflow_hits} 句超垂直安全区已自动缩字号（如仍挤可拆句或 SUB_MAXH_FRAC 调大）" if overflow_hits else ""))
