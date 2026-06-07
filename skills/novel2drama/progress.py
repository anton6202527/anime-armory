#!/usr/bin/env python3
# novel2drama 确定性路由 + 进度回写：读/写 <作品根>/_进度.md
# 用法:
#   python3 progress.py <作品根>                    # 全局：最小未完成集 + 各阶段卡集数
#   python3 progress.py <作品根> 第N集              # 查指定集所处阶段 + 推荐命令
#   python3 progress.py set <作品根> 第N集 <列名> <值>   # 回写某列(✅ / ⬜ / 12/19)，各 skill 收尾调用
#   python3 progress.py ensure-col <作品根> <列名> [默认值] # 旧项目迁移：缺列则追加到「成片」前
import sys, os, re

# 阶段顺序（列名组 → (阶段标签, 推荐命令)）；按顺序找第一个未完成列
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

def prog_path(root):
    root = root.rstrip('/')
    primary = os.path.join(root, '_进度.md')
    if os.path.exists(primary):
        return primary
    # Backward compatibility for older projects that still keep progress in common/.
    return os.path.join(root, 'common', '_进度.md')

def parse(root):
    p = prog_path(root)
    if not os.path.exists(p): print(f"找不到 {p}"); sys.exit(1)
    lines = open(p, encoding='utf-8').read().split('\n')
    header = None; rows = []
    for ln in lines:
        if ln.startswith('| 集 |'):
            header = [c.strip() for c in ln.split('|')[1:-1]]; continue
        m = re.match(r'^\|\s*(第\d+集)\s*\|', ln)
        if m and header:
            cells = [c.strip() for c in ln.split('|')[1:len(header)+1]]
            row = dict(zip(header, cells)); row['_ep'] = m.group(1)
            row['_num'] = int(re.search(r'\d+', m.group(1)).group())
            rows.append(row)
    if header is None: print("未找到表头（| 集 | …）"); sys.exit(1)
    return header, rows

def stage_of(row, header):
    for cols, label, cmd in STAGES:
        for c in cols:
            if c in header and cell_state(row.get(c)) != 'done':
                return label, cmd
    return '✅已成片', None

def fmt(root, ep, label, cmd):
    return f"{ep}: {label}" if cmd is None else f"{ep}: {label}  → {cmd.format(root=root, ep=ep)}"

def do_set(root, ep, col, val):
    p = prog_path(root)
    lines = open(p, encoding='utf-8').read().split('\n')
    header = None; hidx = {}
    for i, ln in enumerate(lines):
        if ln.startswith('| 集 |'):
            header = [c.strip() for c in ln.split('|')[1:-1]]
            hidx = {name: j for j, name in enumerate(header)}
    if header is None or col not in hidx:
        print(f"列名 '{col}' 不在表头：{header}"); sys.exit(1)
    ci = hidx[col]  # 含 集/字数 在内的列下标
    out = []; hit = False
    for ln in lines:
        m = re.match(r'^\|\s*' + re.escape(ep) + r'\s*\|', ln)
        if m:
            parts = ln.split('|')  # ['', 集, 字数, cells..., (note)]
            # parts[1]=集, parts[2]=字数, 物料列从 parts[3] 起；header[0]=集 → ci 对应 parts[ci+1]
            tgt = ci + 1
            if tgt < len(parts):
                parts[tgt] = f' {val} '
                ln = '|'.join(parts); hit = True
        out.append(ln)
    if not hit: print(f"{ep} 不在进度表"); sys.exit(1)
    open(p, 'w', encoding='utf-8').write('\n'.join(out))
    print(f"✅ 回写 {ep} 「{col}」= {val}")

def _split_row(ln):
    return [c.strip() for c in ln.split('|')[1:-1]]

def _row_trailing(ln):
    # 末尾 `|` 之后的行尾备注（如 `|（开局即高潮）`）；ensure-col 重建行时原样保回，避免吞注释
    parts = ln.split('|')
    return parts[-1] if len(parts) >= 2 else ''

def do_ensure_col(root, col, default='⬜'):
    p = prog_path(root)
    lines = open(p, encoding='utf-8').read().split('\n')
    header = None
    insert_at = None
    for ln in lines:
        if ln.startswith('| 集 |'):
            header = _split_row(ln)
            break
    if header is None:
        print("未找到表头（| 集 | …）"); sys.exit(1)
    if col in header:
        print(f"✅ 列已存在：{col}"); return
    preferred_before = {'视频prompt': '视频'}
    before = preferred_before.get(col, '成片')
    insert_at = header.index(before) if before in header else (header.index('成片') if '成片' in header else len(header))

    out = []
    for ln in lines:
        if ln.startswith('| 集 |') or re.match(r'^\|\s*-+', ln):
            cells = _split_row(ln); trailing = _row_trailing(ln)
            filler = '---' if re.match(r'^\|\s*-+', ln) else col
            cells.insert(insert_at, filler)
            out.append('| ' + ' | '.join(cells) + ' |' + trailing)
        elif re.match(r'^\|\s*第\d+集\s*\|', ln):
            cells = _split_row(ln); trailing = _row_trailing(ln)
            while len(cells) < len(header):
                cells.append('')
            cells.insert(insert_at, default)
            out.append('| ' + ' | '.join(cells) + ' |' + trailing)
        else:
            out.append(ln)
    open(p, 'w', encoding='utf-8').write('\n'.join(out))
    print(f"✅ 已追加列「{col}」（默认 {default}）")

def main():
    if len(sys.argv) >= 2 and sys.argv[1] == 'set':
        if len(sys.argv) != 6:
            print("用法: progress.py set <作品根> 第N集 <列名> <值>"); sys.exit(1)
        do_set(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]); return
    if len(sys.argv) >= 2 and sys.argv[1] == 'ensure-col':
        if len(sys.argv) not in (4, 5):
            print("用法: progress.py ensure-col <作品根> <列名> [默认值]"); sys.exit(1)
        do_ensure_col(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) == 5 else '⬜'); return
    root = sys.argv[1].rstrip('/'); only = sys.argv[2] if len(sys.argv) > 2 else None
    header, rows = parse(root)
    if only:
        r = next((x for x in rows if x['_ep'] == only), None)
        if not r: print(f"{only} 不在进度表"); sys.exit(1)
        label, cmd = stage_of(r, header); print(fmt(root, only, label, cmd)); return
    done = 0; bottleneck = {}; first = None
    for r in sorted(rows, key=lambda x: x['_num']):
        label, cmd = stage_of(r, header)
        if cmd is None: done += 1
        else:
            bottleneck[label] = bottleneck.get(label, 0) + 1
            if first is None: first = (r['_ep'], label, cmd)
    print(f"作品: {os.path.basename(root)}（共 {len(rows)} 集）")
    print(f"成片完成: {done}/{len(rows)}")
    if first: print(f"下一步（最小未完成集）: {fmt(root, *first)}")
    else: print("🎉 全部成片完成")
    if bottleneck:
        order = [s[1] for s in STAGES] + ['✅已成片']
        items = sorted(bottleneck.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else 99)
        print("各阶段卡集数: " + " · ".join(f"{k}={v}" for k, v in items))

if __name__ == '__main__':
    main()
