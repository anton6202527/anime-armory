#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""n2d 源新鲜度自检 —— 检测本剧规范源文件是否变动并评估重切影响。

本脚本在漫剧侧自检：
  · 只读取本剧作品根下的 `小说/<剧>.txt` 规范源副本。
  · 给每章正文做指纹存 `小说/_源指纹.json`；自检时重算比对 → 列出**变动章 + 落在哪些集
    + 那些集是 raw-only(可安全重切) 还是已生产(需谨慎)**。
不自动重切（重切属"不可逆/花钱"点，每次确认）。

用法:
    python3 source_check.py <漫剧作品根>                 # 自检并报告漂移（dispatcher 入口/hook 调用）
    python3 source_check.py <漫剧作品根> --record         # 记/更新指纹基线（首切后 / 同步并确认后）
    python3 source_check.py <漫剧作品根> --quiet          # 仅 clean 时不打印（hook 用，少噪声）

输出：人类可读报告 + 末行机器可读 JSON（DRIFT={...}）。纯标准库。
"""
import sys, os, re, json, glob, hashlib

_CHAPTER_UNITS = "章回囬囘廻节節卷"
_HUI_UNITS = frozenset("回囬囘廻")
CH_TXT_RE = re.compile(
    rf"^\s*(?:\[编辑\]\s*)?第\s*([0-9一二三四五六七八九十百零〇两]+)\s*([{_CHAPTER_UNITS}])",
    re.M,
)  # 导出 txt 章/回标记（兼容明清刻本异体字）
RAW_CH_RE = re.compile(
    rf"^\s*(?:\[编辑\]\s*)?第\s*([0-9一二三四五六七八九十百零〇两]+)\s*([{_CHAPTER_UNITS}])",
    re.M,
)  # raw.txt 原文章/回号(中/阿)
EP_RE = re.compile(r"第(\d+)集")
_CN_D = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
         "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_U = {"十": 10, "百": 100}


def cn2int(s):
    """中文/阿拉伯数字 → int（支持到几百，够章号用）。"""
    if s.isdigit():
        return int(s)
    total = cur = 0
    for ch in s:
        if ch in _CN_D:
            cur = _CN_D[ch]
        elif ch in _CN_U:
            total += (cur or 1) * _CN_U[ch]
            cur = 0
    return total + cur


def _h(s):
    return hashlib.sha1(re.sub(r"\s+", "", s).encode("utf-8")).hexdigest()[:12]


def _preferred_marks(text, pattern):
    """Prefer real 章回 headings over volume-wrapper ``第N章`` exports.

    Some public-domain editions wrap every ten hui in a synthetic ``第N章``
    while the actual story units use ``第一囬`` ... ``第一百囬``. Mixing both
    systems would overwrite hashes 1-10 and report a ten-chapter book. If any
    hui-style headings exist, they are the canonical source units.
    """
    marks = list(pattern.finditer(text or ""))
    hui = [mark for mark in marks if mark.group(2) in _HUI_UNITS]
    return hui or marks


def hashes_from_txt(txt_path):
    """从导出 txt 按 第N章/回 切开，每个真实源单元正文哈希。"""
    text = open(txt_path, encoding="utf-8", errors="replace").read()
    marks = _preferred_marks(text, CH_TXT_RE)
    out = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out[cn2int(m.group(1))] = _h(text[m.start():end])
    return out


def resolve_source(drama_root, link=None):
    """返回 (hashes, label, kind)。kind: txt。"""
    if link:
        sys.exit("--link 已移除：n2d 源检查只读取本作品根下的 小说/*.txt")
    cands = glob.glob(os.path.join(drama_root, "小说", "*.txt"))
    if not cands:
        sys.exit(f"未找到源文件：{drama_root}/小说/*.txt")
    txt = max(cands, key=os.path.getsize)
    return hashes_from_txt(txt), f"源副本 小说/{os.path.basename(txt)}", "txt"


def map_chapter_to_eps(root):
    """扫 脚本/第N集/raw.txt，按集号顺序 + 章标记进位，建 {章号: [集号...]}（含跨集 span）。"""
    eps = []
    for d in glob.glob(os.path.join(root, "脚本", "第*集")):
        m = EP_RE.search(os.path.basename(d))
        if m:
            eps.append((int(m.group(1)), d))
    eps.sort()
    chap_to_eps, current = {}, None
    for ep, d in eps:
        raw = os.path.join(d, "raw.txt")
        if not os.path.isfile(raw):
            continue
        raw_text = open(raw, encoding="utf-8", errors="replace").read()
        marks = sorted({cn2int(m.group(1)) for m in _preferred_marks(raw_text, RAW_CH_RE)})
        if marks:
            for ch in marks:
                chap_to_eps.setdefault(ch, []).append(ep)
            current = marks[-1]
        elif current is not None:
            chap_to_eps.setdefault(current, []).append(ep)
    return chap_to_eps


def ep_progress(root):
    """读 _进度.md 流程矩阵，返回 {集号: raw 之后任一列已有产出}。"""
    p = os.path.join(root, "_进度.md")
    started = {}
    if not os.path.isfile(p):
        return started
    for line in open(p, encoding="utf-8", errors="replace"):
        if not line.strip().startswith("| 第"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        m = EP_RE.search(cells[0])
        if not m:
            continue
        downstream = cells[3:]  # 列序：集|字数|raw|剧本改编|...|成片
        started[int(m.group(1))] = any(c == "✅" or re.match(r"[1-9]\d*/\d+", c) for c in downstream)
    return started


def main():
    a = sys.argv
    root = a[1]
    record = "--record" in a
    quiet = "--quiet" in a
    link = a[a.index("--link") + 1] if "--link" in a else None

    cur, label, kind = resolve_source(root, link)
    fp_path = os.path.join(root, "小说", "_源指纹.json")

    if record:
        os.makedirs(os.path.dirname(fp_path), exist_ok=True)
        json.dump({"source_label": label, "source_kind": kind, "chapters": len(cur),
                   "chapter_hashes": {str(k): v for k, v in cur.items()}},
                  open(fp_path, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        print(f"[ok] 已记录源指纹基线：{label}（{len(cur)} 章）→ {fp_path}")
        return

    if not os.path.isfile(fp_path):
        if not quiet:
            print(f"⚠️ 无源指纹基线（{os.path.basename(root)}）。当前源文本：{label}，{len(cur)} 章。")
            print("   首切定稿后跑 `source_check.py <作品根> --record` 记基线，之后才能自动发现源更新。")
        print('DRIFT={"status":"no_baseline"}')
        return

    base = json.load(open(fp_path, encoding="utf-8"))
    old = {int(k): v for k, v in base.get("chapter_hashes", {}).items()}
    changed = sorted(ch for ch in cur if ch in old and cur[ch] != old[ch])
    added = sorted(set(cur) - set(old))
    removed = sorted(set(old) - set(cur))

    if not (changed or added or removed):
        if not quiet:
            print(f"✅ 源未变动（{label}，{len(cur)} 章）。源文本与基线一致，无需重切。")
        print('DRIFT={"status":"clean"}')
        return

    chap_to_eps = map_chapter_to_eps(root)
    prog = ep_progress(root)
    print(f"⚠️ 源文本已更新 → 漫剧《{os.path.basename(root)}》源过期（当前源：{label}）：")
    if changed: print(f"   变动章：{changed}")
    if added:   print(f"   新增章：{added}")
    if removed: print(f"   删除章：{removed}")
    affected, risky = [], []
    for ch in changed + added:
        eps = chap_to_eps.get(ch, [])
        prod = [e for e in eps if prog.get(e)]
        if prod:
            risky.append(ch)
        tag = "⚠️已生产·需谨慎" if prod else "✅raw-only·可安全重切"
        print(f"   原文第{ch}章 → 集 {eps or '（未拆到）'}  [{tag}]" + (f"  已生产集={prod}" if prod else ""))
        affected.append({"chapter": ch, "eps": eps, "produced_eps": prod})
    print("下一步（重切属'不可逆/花钱'点，每次确认，绝不自动执行）：")
    print("  ① 确认本剧 `小说/<剧>.txt` 已是当前要使用的源文本")
    if risky:
        print(f"  ② ⚠️ 触及已生产集（章 {risky}）：逐集评估配音/出图/出视频是否返工，与用户确认")
    print("  ② raw-only：推进到那些集前从新源重切该窗口 raw（P0→P6），勿重跑整本 split（会重排集号波及已做集）")
    print("  ③ 处理完/接受现状后：`source_check.py <作品根> --record` 更新基线")
    print("DRIFT=" + json.dumps({"status": "drift", "drama": os.path.basename(root),
                                 "changed": changed, "added": added, "removed": removed,
                                 "risky_chapters": risky, "affected": affected}, ensure_ascii=False))


if __name__ == "__main__":
    main()
