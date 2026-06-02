#!/usr/bin/env python3
# novel2drama 确定性路由：读 <作品根>/common/_进度.md → 算每集所处阶段 + 推荐下一步命令
# 用法:
#   python3 progress.py <作品根>            # 全局：最小未完成集 + 各阶段卡集数
#   python3 progress.py <作品根> 第N集      # 查指定集
import sys, os, re

ROOT = sys.argv[1].rstrip('/')
ONLY = sys.argv[2] if len(sys.argv) > 2 else None
PROG = os.path.join(ROOT, 'common', '_进度.md')

# 阶段顺序（列名 → (阶段标签, 推荐命令)）；按此顺序找第一个未完成列
STAGES = [
    (['剧本改编', 'bgm', '封面'], '阶段1·剧本改编', '/n2d-script {root} {ep}'),
    (['配音'],                    '角色配音',        '/n2d-voice {root} {ep}'),
    (['分镜设计'],                '阶段2·分镜设计',  '/n2d-script {root} {ep}  (配音后定稿)'),
    (['出图prompt', '出图'],      '出图',            '/n2d-image {root} {ep}'),
    (['视频prompt', '视频'],      '图生视频',        '/n2d-video {root} {ep}'),
    (['成片'],                    '合成成片',        '/n2d-compose {root} {ep}'),
]

def cell_state(v):
    v = (v or '').strip()
    if v == '✅': return 'done'
    if v in ('⬜', '', '—', '-'): return 'todo'
    m = re.match(r'(\d+)\s*/\s*(\d+)', v)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if b > 0 and a >= b: return 'done'
        return 'partial' if a > 0 else 'todo'
    return 'todo'

def parse():
    if not os.path.exists(PROG):
        print(f"找不到 {PROG}"); sys.exit(1)
    lines = open(PROG, encoding='utf-8').read().split('\n')
    header = None; rows = []
    for ln in lines:
        if ln.startswith('| 集 |'):
            header = [c.strip() for c in ln.split('|')[1:-1]]; continue
        m = re.match(r'^\|\s*(第\d+集)\s*\|', ln)
        if m and header:
            cells = [c.strip() for c in ln.split('|')[1:len(header)+1]]
            row = dict(zip(header, cells))
            row['_ep'] = m.group(1)
            row['_num'] = int(re.search(r'\d+', m.group(1)).group())
            rows.append(row)
    if header is None:
        print("未找到表头（| 集 | …）"); sys.exit(1)
    return header, rows

def stage_of(row, header):
    for cols, label, cmd in STAGES:
        for c in cols:
            if c not in header:        # 该列不在表里 → 跳过(容错旧表)
                continue
            if cell_state(row.get(c)) != 'done':
                return label, cmd
    return '✅已成片', None

def fmt(ep, label, cmd):
    if cmd is None: return f"{ep}: {label}"
    return f"{ep}: {label}  → {cmd.format(root=ROOT, ep=ep)}"

def main():
    header, rows = parse()
    if ONLY:
        r = next((x for x in rows if x['_ep'] == ONLY), None)
        if not r: print(f"{ONLY} 不在进度表"); sys.exit(1)
        label, cmd = stage_of(r, header)
        print(fmt(ONLY, label, cmd)); return
    # 全局
    done = 0; bottleneck = {}; first_unfinished = None
    for r in sorted(rows, key=lambda x: x['_num']):
        label, cmd = stage_of(r, header)
        if cmd is None:
            done += 1
        else:
            bottleneck[label] = bottleneck.get(label, 0) + 1
            if first_unfinished is None:
                first_unfinished = (r['_ep'], label, cmd)
    name = os.path.basename(ROOT)
    print(f"作品: {name}（共 {len(rows)} 集）")
    print(f"成片完成: {done}/{len(rows)}")
    if first_unfinished:
        ep, label, cmd = first_unfinished
        print(f"下一步（最小未完成集）: {fmt(ep, label, cmd)}")
    else:
        print("🎉 全部成片完成")
    if bottleneck:
        order = [s[1] for s in STAGES] + ['✅已成片']
        items = sorted(bottleneck.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else 99)
        print("各阶段卡集数: " + " · ".join(f"{k}={v}" for k, v in items))

if __name__ == '__main__':
    main()
