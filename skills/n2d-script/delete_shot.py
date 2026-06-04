#!/usr/bin/env python3
# 删镜助手 — 后期删减「回流」的可自动推导部分一键完成（见 novel2drama/Q&A.md Q27）
# 用法: delete_shot.py <作品根> <第N集> <镜头名> [镜头名...]
#   例: delete_shot.py 制漫剧/冷宫有妖气 第2集 镜头6
# 自动做：voiceover.txt 删行 → 字幕_英文.srt 删对应块(EN文本源·必须同步) →
#         时长清单.json reflow(丢句+重编号+重命名 line wav，被删句移废料) →
#         voice_zh.wav 重拼轨(有 ffmpeg 时，含 hook 可变间隔) → finalize_storyboard 重定时
# 不动（末尾打印清单，需人工）：故事板/分镜剧本/bgm/可灵*.md 设计文档、已生成的 PNG/clip MP4、成片。
import sys, os, re, json, subprocess, shutil

if len(sys.argv) < 4: sys.exit('用法: delete_shot.py <作品根> <第N集> <镜头名> [镜头名...]')
root, ep = sys.argv[1], sys.argv[2]
shots = set(sys.argv[3:])

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VO   = os.path.join(root, '脚本', ep, 'voiceover.txt')
ENS  = os.path.join(root, '脚本', ep, '字幕_英文.srt')
CONF = os.path.join(root, '出视频', ep, '配音')
MAN  = os.path.join(CONF, '时长清单.json')

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
    blks = [b for i, b in enumerate(blks) if i not in dset]
    open(ENS, 'w', encoding='utf-8').write('\n\n'.join(blks) + '\n')

# 3) 时长清单 reflow：被删句 wav 移废料；保留句重命名为连续 line_NN.wav；保留句"时长不变"
waste = os.path.join(root, 'common', '废料', '出视频', ep, '配音'); os.makedirs(waste, exist_ok=True)
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

# 6) 还需人工（非自动推导链，脚本不动）
print('\n=== 还需手动处理 ===')
print(f'  □ 设计文档删 {sorted(shots)} 相关块：故事板.md / 分镜剧本.md / bgm.txt / 可灵*.md'
      '（故事板·可灵的 Clip 视情况重编号 + 同步拆Clip子标签）')
print(f'  □ 若已出图/出视频：移走 出图/{ep}/镜头X_*.png 与 出视频/{ep}/视频/对应 Clip*.mp4 → common/废料/')
print(f'  □ 重跑 /n2d-compose <作品根> {ep} 出新成片')
print('  □ 过一眼 novel2drama/references/导演节奏.md 留存自查（别把钩子/集尾删没）')
