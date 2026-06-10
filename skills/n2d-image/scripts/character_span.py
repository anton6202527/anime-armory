#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""character_span.py — 扫原著全文，产「角色出场跨度」数据，喂出图前一致性定档。

为什么存在：一致性定档（档①参考图 / ②后端主体ID / ③LoRA / 表情库）的主驱动是
**角色体量（出场跨度）**，而它在「只粗切了几集」时看不到。体量真值在原著全文里，
不在分镜里——所以定档前先扫原著，比拆 N 集又快又全。

两段用法（先发现、人筛、再算跨度）：
  # ① 候选发现：n-gram 词频捞高频 token，人工筛出真角色名（会混入职务/势力/功能词，需人判）
  python3 character_span.py 原著.txt --discover [--min 25]
  # ② 跨度报表：对确认的角色名算 首现%/退场%/密度分布，输出 Markdown 跨度表
  python3 character_span.py 原著.txt --names 沈念,小禾,皇后,太后,林渊 [--bins 10]

输出的 Markdown 直接贴进 设定库/characters/_出场跨度表.md；密度 sparkline 用来判
「短线（全堆开头）/ 低频长线 / 全程核心」——决定该角色封顶在哪一档。

纯 stdlib，系统 Python 即可，不碰重型 conda 环境。
（自测：cd 到本目录后 `python3 character_span.py --selftest`）
"""
import sys, re, argparse
from collections import Counter

CJK = r'[一-鿿]+'
# 宫斗/玄幻题材常见非人名功能词 + 通用词，候选发现时降噪（仍需人工二次筛）
STOP = set(
    '自己什么这个那个一个我们你们他们她们这样那样知道现在已经如果因为所以但是'
    '就是还是这么那么怎么时候没有这些那些起来出来过来上去下去眼神声音心里身上脸上'
    '手里之后之前一声一眼一下两人这位那位真正东西要的同源血脉妖纹暗金鳞甲妖躯反噬'
    '封印目光指尖深处此刻今日今夜清楚缓缓看着顺着成了到了住了'
)


def discover(text, min_n=25, top=60):
    """n-gram 词频捞候选角色名（2/3-gram），输出供人工筛选。"""
    runs = re.findall(CJK, text)
    c2, c3 = Counter(), Counter()
    for r in runs:
        for i in range(len(r) - 1):
            c2[r[i:i + 2]] += 1
        for i in range(len(r) - 2):
            c3[r[i:i + 3]] += 1
    out = []
    for label, c in (('3-gram', c3), ('2-gram', c2)):
        rows = []
        for w, n in c.most_common(400):
            if n < min_n:
                break
            if any(s in w for s in STOP):
                continue
            rows.append((w, n))
        out.append((label, rows[:top]))
    return out


def spans(lines, names, nb=10):
    """对每个角色名算 次数 / 首现% / 退场% / 逐段密度(sparkline)。"""
    N = max(1, len(lines))
    blocks = '▁▂▃▄▅▆▇█'
    res = []
    for nm in names:
        hits = [i for i, l in enumerate(lines) if nm in l]
        if not hits:
            res.append((nm, 0, None, None, '—' * nb))
            continue
        cnt = sum(l.count(nm) for l in lines)
        bins = [0] * nb
        for i in hits:
            bins[min(nb - 1, i * nb // N)] += 1
        mx = max(bins) + 1
        spark = ''.join(blocks[min(7, b * 8 // mx)] for b in bins)
        res.append((nm, cnt, hits[0] * 100 // N, hits[-1] * 100 // N, spark))
    return res


def render_md(rows, nb):
    out = ['## 角色出场跨度表（扫原著 character_span.py 生成）',
           f'> 密度=全书按行均分 {nb} 段，每段出现频次（首→尾）。'
           '全堆开头=短线封顶档①；全程均匀=核心长线候选②/③；'
           '后段加重=后期主戏角，定妆/升档别拖到登场才补。',
           '',
           '| 角色 | 次数 | 首现% | 退场% | 密度分布(首→尾) | 体量读法 |',
           '|---|---|---|---|---|---|']
    for nm, cnt, fp, lp, sp in rows:
        if cnt == 0:
            out.append(f'| {nm} | 0 | — | — | {sp} | 未出现/别名? |')
            continue
        # 简单体量启发：退场<35% 且 密度集中 → 短线；首尾跨度>80% → 长线
        span = (lp - fp) if (fp is not None and lp is not None) else 0
        if lp is not None and lp < 35:
            read = '短线·开场单元'
        elif span >= 80 and cnt >= 200:
            read = '全程核心'
        elif span >= 80:
            read = '低频长线'
        else:
            read = '中段/局部'
        out.append(f'| {nm} | {cnt} | {fp}% | {lp}% | {sp} | {read} |')
    return '\n'.join(out)


def _selftest():
    lines = []
    for i in range(100):
        parts = ['沈念']                 # 全程每段都在
        if i < 5:
            parts.append('柳娘子')       # 只在开头 5% → 短线早退场
        if i >= 90:
            parts.append('太后')         # 只在末段 → 后段登场
        lines.append(' '.join(parts))
    d = {x[0]: x for x in spans(lines, ['沈念', '柳娘子', '太后', '无人'], nb=10)}
    assert d['无人'][1] == 0, d['无人']
    assert d['柳娘子'][1] == 5 and d['柳娘子'][3] < 35, d['柳娘子']  # 早退场
    assert d['沈念'][1] == 100 and d['沈念'][2] == 0, d['沈念']      # 全程
    assert d['太后'][2] > 80, d['太后']                             # 后段登场
    print('selftest OK')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('novel', nargs='?')
    ap.add_argument('--names', help='逗号分隔的确认角色名')
    ap.add_argument('--discover', action='store_true', help='n-gram 候选发现')
    ap.add_argument('--bins', type=int, default=10)
    ap.add_argument('--min', type=int, default=25)
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        _selftest()
        return
    if not a.novel:
        ap.error('需要原著 txt 路径')
    text = open(a.novel, encoding='utf-8').read()
    if a.discover or not a.names:
        for label, rows in discover(text, a.min):
            print(f'\n=== {label} 候选（人工筛出真角色，剔除职务/势力/功能词）===')
            for w, n in rows:
                print(f'  {w}\t{n}')
        if not a.names:
            return
    lines = text.split('\n')
    names = [x.strip() for x in a.names.split(',') if x.strip()]
    print()
    print(render_md(spans(lines, names, a.bins), a.bins))


if __name__ == '__main__':
    main()
