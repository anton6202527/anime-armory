#!/usr/bin/env python3
# novel2drama 确定性路由 + 进度回写：读/写 <作品根>/_进度.md
# 用法:
#   python3 progress.py <作品根>                    # 全局：最小未完成集 + 各阶段卡集数
#   python3 progress.py <作品根> 第N集              # 查指定集所处阶段 + 推荐命令
#   python3 progress.py set <作品根> 第N集 <列名> <值>   # 回写某列(✅ / ⬜ / 12/19)，各 skill 收尾调用
#   python3 progress.py ensure-col <作品根> <列名> [默认值] # 旧项目迁移：缺列则追加到「成片」前
import sys, os, re

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'common'))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_contract import write_episode_manifest
from n2d_route import STAGES, cell_state, format_route, is_episode_row, parse_progress, progress_path, stage_of, summarize

def prog_path(root):
    return progress_path(root)

def parse(root):
    try:
        return parse_progress(root)
    except FileNotFoundError as e:
        print(f"找不到 {e.args[0]}"); sys.exit(1)
    except ValueError as e:
        print(str(e)); sys.exit(1)

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
    try:
        write_episode_manifest(root, ep, extra={"last_progress_column": col, "last_progress_value": val})
    except Exception as e:
        print(f"⚠️ manifest 快照写入失败：{e}")
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
        elif is_episode_row(ln):
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
        route = stage_of(root, r, header)
        print(format_route(root, route))
        if route.get('note'):
            print(f"  ⚠️ {route['note']}")
        return
    summary = summarize(root)
    done = summary["done"]; bottleneck = summary["bottleneck"]; first = summary["first"]
    print(f"作品: {os.path.basename(root)}（共 {len(rows)} 集）")
    print(f"成片完成: {done}/{len(rows)}")
    if first:
        print(f"下一步（最小未完成集）: {format_route(root, first)}")
        if first.get('note'):
            print(f"  ⚠️ {first['note']}")
    else: print("🎉 全部成片完成")
    if bottleneck:
        order = [s[1] for s in STAGES] + ['补真实配音', '✅已成片']
        items = sorted(bottleneck.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else 99)
        print("各阶段卡集数: " + " · ".join(f"{k}={v}" for k, v in items))

if __name__ == '__main__':
    main()
