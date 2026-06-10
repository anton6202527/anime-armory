#!/usr/bin/env python3
# 删镜助手 — 后期删减「回流」的可自动推导部分一键完成（见 novel2drama/Q&A.md Q27）
# 用法: delete_shot.py <作品根> <第N集> <镜头名> [镜头名...]
#   例: delete_shot.py 制漫剧/冷宫有妖气 第2集 镜头6
# 自动做：voiceover.txt 删行 → 字幕_英文.srt 删对应块(EN文本源·必须同步) →
#         时长清单.json reflow(丢句+重编号+重命名 line wav，被删句移废料) →
#         voice_zh.wav 重拼轨(有 ffmpeg 时，含 hook 可变间隔) → finalize_storyboard 重定时
# 不动（末尾打印清单，需人工）：故事板.md/分镜剧本.md/bgm.txt/storyboard.json 设计文档、已生成的 PNG/clip MP4、成片。
import sys, os, re, json, subprocess, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from n2d_route import voiceover_fingerprint  # 删镜重写 voiceover.txt 后须同步刷新 meta 指纹，否则 validate_timings 误报失配

if len(sys.argv) < 4: sys.exit('用法: delete_shot.py <作品根> <第N集> <镜头名> [镜头名...]')
root, ep = sys.argv[1], sys.argv[2]
shots = set(sys.argv[3:])

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VO   = os.path.join(root, '脚本', ep, 'voiceover.txt')
ENS  = os.path.join(root, '脚本', ep, '字幕_英文.srt')
# 配音一律落 合成/（与制作模式无关）；出视频/ 为已废弃历史路径，仅防御性兜底探测
VBASE = next((b for b in ('合成', '出视频') if os.path.isfile(os.path.join(root, b, ep, '配音', '时长清单.json'))), '合成')
CONF = os.path.join(root, VBASE, ep, '配音')
MAN  = os.path.join(CONF, '时长清单.json')

if not os.path.isfile(MAN):
    sys.exit(f'⛔ 缺 {MAN} —— 该集还没配音(无时长清单)，无可回流的删镜。请确认集号，或先 /n2d-voice。')
if not os.path.isfile(VO):
    sys.exit(f'⛔ 缺 {VO} —— voiceover.txt 不存在，无法删行。请确认作品根/集号。')

man = json.load(open(MAN, encoding='utf-8'))
dset = {i for i, r in enumerate(man) if r.get('镜头') in shots}
if not dset:
    sys.exit(f'时长清单里没有 {sorted(shots)}，无改动（可能已删）')
print('将删除句(idx/镜头/文本):')
for i in sorted(dset): print('  ', i, man[i].get('镜头'), man[i].get('文本'))

# 1) voiceover.txt 删对应行
def shot_of(l):
    m = re.match(r'\[(镜头[^·\]]*)', l); return m.group(1) if m else None
lines = open(VO, encoding='utf-8').read().splitlines()
open(VO, 'w', encoding='utf-8').write('\n'.join(l for l in lines if shot_of(l) not in shots) + '\n')

# 2) 字幕_英文.srt 删对应块 —— finalize 按 index 取 EN 文本，不同步则删除点之后全部错位
if os.path.exists(ENS):
    blks = re.split(r'\n\s*\n', open(ENS, encoding='utf-8').read().strip())
    if len(blks) != len(man):
        # EN 块数与时长清单句数不一致：按 index 删会错块。跳过 EN 同步并警告，让用户先对齐。
        print(f'⚠ 跳过英文字幕同步：EN 块数({len(blks)}) ≠ 时长清单句数({len(man)})，按 index 删会错位。'
              f'\n  请先重跑 finalize_storyboard 对齐中英字幕，或手动删 {sorted(shots)} 对应 EN 块。')
    else:
        blks = [b for i, b in enumerate(blks) if i not in dset]
        open(ENS, 'w', encoding='utf-8').write('\n\n'.join(blks) + '\n')

# 3) 时长清单 reflow：被删句 wav 移废料；保留句重命名为连续 line_NN.wav；保留句"时长不变"
waste = os.path.join(root, '废料', VBASE, ep, '配音'); os.makedirs(waste, exist_ok=True)
for i in sorted(dset):
    w = os.path.join(CONF, man[i].get('line_wav', f'line_{i:02d}.wav'))
    if os.path.exists(w): shutil.move(w, os.path.join(waste, os.path.basename(w)))
keep = [r for i, r in enumerate(man) if i not in dset]
tmp = []
for r in keep:                                   # 先改临时名避免覆盖
    old = os.path.join(CONF, r.get('line_wav', ''))
    if old and os.path.exists(old):
        t = old + '.__tmp'; shutil.move(old, t); tmp.append(t)
    else: tmp.append(None)
for n, (r, t) in enumerate(zip(keep, tmp)):
    r['idx'] = n; r['line_wav'] = f'line_{n:02d}.wav'
    if t: shutil.move(t, os.path.join(CONF, f'line_{n:02d}.wav'))
json.dump(keep, open(MAN, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'时长清单: {len(man)} → {len(keep)} 句；保留句时长不变')

# 3.5) 刷新 时长清单.meta.json 指纹 —— 删镜是「授权的回流」（保留句真实音频+时长不变），
#      但已改写了 voiceover.txt，若不同步指纹，validate_timings 会把这次删镜误报为「配音后改词失配」。
META = os.path.join(CONF, '时长清单.meta.json')
if os.path.isfile(META):
    try:
        _m = json.load(open(META, encoding='utf-8')) or {}
    except Exception:
        _m = {}
    _m['voiceover_fingerprint'] = voiceover_fingerprint(VO)
    _m['lines'] = len(keep)
    _m['placeholder_lines'] = sum(1 for r in keep if r.get('占位'))
    json.dump(_m, open(META, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('时长清单.meta.json 指纹已同步（删镜后 validate_timings 不会误报失配）')

# 4) voice_zh.wav 重拼轨（需 ffmpeg；hook 可变间隔与 render_voice 一致）
FF = shutil.which('ffmpeg')
GAP = float(os.environ.get('LINE_GAP', '0.4'))
HG = {'end': float(os.environ.get('GAP_END', '1.0')),
      'climax': float(os.environ.get('GAP_CLIMAX', '0.7')),
      'hook': float(os.environ.get('GAP_HOOK', '0.6'))}
vw = os.path.join(CONF, 'voice_zh.wav')
if FF:
    sil = {}
    def silf(d):
        if d not in sil:
            p = os.path.join(CONF, f'_gap_{int(round(d*100))}.wav')
            subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i',
                            'anullsrc=r=44100:cl=stereo', '-t', str(d), p], check=True)
            sil[d] = p
        return sil[d]
    seq = []
    for k, r in enumerate(keep):
        seq.append(os.path.join(CONF, r['line_wav']))
        if k < len(keep) - 1: seq.append(silf(HG.get(r.get('钩子', ''), GAP)))
    lf = os.path.join(CONF, '_concat.txt')
    open(lf, 'w').write('\n'.join(f"file '{os.path.abspath(p)}'" for p in seq))
    subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
                    '-i', lf, '-c', 'copy', vw], check=True)
    print('voice_zh.wav 已重拼轨')
else:
    if os.path.exists(vw): shutil.move(vw, vw + '.stale')
    print('⚠ 无 ffmpeg：voice_zh.wav → .stale，请在装 ffmpeg 的机器重跑 /n2d-voice 重拼轨')

# 5) finalize 重定时（纯 python）
subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, 'finalize_storyboard.py'), root, ep], check=True)

# 5.5) 跑 image gate 强制对账 storyboard.json —— 删句后 storyboard.json 的 Clip/接力/duration 会失配，
#      靠人记着改极易漏；这里主动让 gate 把"现在哪里对不上"列出来（非阻断，删镜本身已落地）。
gate = os.path.join(SCRIPT_DIR, '..', 'n2d-review', 'scripts', 'gate.py')
if os.path.isfile(gate):
    print('\n=== 删镜后 storyboard 对账（gate --stage image，仅提示）===')
    r = subprocess.run([sys.executable, gate, root, ep, '--stage', 'image'],
                       capture_output=True, text=True)
    out = (r.stdout or '').strip()
    print('\n'.join(l for l in out.splitlines() if ('storyboard' in l or '故事板' in l or 'continuity'
          in l or '尾帧' in l or '首帧' in l or 'block' in l)) or '  （gate 未报 storyboard 相关问题）')
    print('  ↑ 若上面列出接力/首尾帧/duration 问题，按提示改 storyboard.json 再出图。')

# 6) 还需人工（非自动推导链，脚本不动）
print('\n=== 还需手动处理 ===')
print(f'  □ 设计文档删 {sorted(shots)} 相关块：故事板.md / 分镜剧本.md / bgm.txt / storyboard.json'
      '（故事板与 storyboard.json 的 Clip 视情况重编号 + 同步拆Clip子标签；改完按上面 gate 对账复跑）')
print(f'  □ 若已出图/出视频：移走 出图/{ep}/镜头X_*.png 与 出视频/{ep}/视频/对应 Clip*.mp4 → 废料/')
print(f'  □ 重跑 /n2d-compose <作品根> {ep} 出新成片')
print('  □ 过一眼 novel2drama/references/导演节奏.md 留存自查（别把钩子/集尾删没）')
