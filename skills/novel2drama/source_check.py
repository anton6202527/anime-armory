#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""novel2drama 源新鲜度自检 —— 写小说成品一改，自动发现对应漫剧源过期 + 评估重切影响。

两条创作线只在「成品」一处耦合：写小说 `章节/*.md`（真源）→ 导出 → 漫剧 `小说/<剧>.txt`。
本脚本在漫剧侧自检：
  · 优先挂到**同名写小说项目** `写小说/<剧名>/章节/*.md`（真源·章一改即可发现，不必等重导出/同步）；
    找不到同名项目时回退用漫剧自己的 `小说/<剧>.txt`。
  · 给每章正文做指纹存 `小说/_源指纹.json`；自检时重算比对 → 列出**变动章 + 落在哪些集
    + 那些集是 raw-only(可安全重切) 还是已生产(需谨慎)**。
不自动重切（重切属"不可逆/花钱"点，每次确认）。

用法:
    python3 source_check.py <漫剧作品根>                 # 自检并报告漂移（dispatcher 入口/hook 调用）
    python3 source_check.py <漫剧作品根> --record         # 记/更新指纹基线（首切后 / 同步并确认后）
    python3 source_check.py <漫剧作品根> --link <写小说根> # 显式指定真源项目（默认按同名自动找）
    python3 source_check.py <漫剧作品根> --quiet          # 仅 clean 时不打印（hook 用，少噪声）

输出：人类可读报告 + 末行机器可读 JSON（DRIFT={...}）。纯标准库。
"""
import sys, os, re, json, glob, hashlib

CH_TXT_RE = re.compile(r"^第\s*([0-9一二三四五六七八九十百零〇两]+)\s*章", re.M)  # 导出 txt 章标记
CHAP_FILE_RE = re.compile(r"^第0*(\d+)章")          # 章节文件名：第NN章[_标题].md（数字）
RAW_CH_RE = re.compile(r"第\s*([0-9一二三四五六七八九十百零〇两]+)\s*章")  # raw.txt 原文章号(中/阿)
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


def derive_novel_project(drama_root):
    """同名约定：.../制漫剧/<名>  →  .../写小说/<名>。存在且有 章节/ 才采用。"""
    drama_root = os.path.abspath(drama_root.rstrip("/"))
    repo = os.path.dirname(os.path.dirname(drama_root))   # 跳过 制漫剧/
    cand = os.path.join(repo, "写小说", os.path.basename(drama_root))
    return cand if os.path.isdir(os.path.join(cand, "章节")) else None


def hashes_from_project(proj):
    """从 写小说项目/章节/*.md 读 {章号: 正文hash}。章号取文件名，正文去 H1+meta 注释后哈希。"""
    out = {}
    for f in glob.glob(os.path.join(proj, "章节", "*.md")):
        m = CHAP_FILE_RE.match(os.path.basename(f))
        if not m:
            continue
        lines = open(f, encoding="utf-8", errors="replace").read().split("\n")
        body = "\n".join(l for l in lines
                         if not l.startswith("# 第") and not l.strip().startswith("<!--"))
        out[int(m.group(1))] = _h(body)
    return out


def hashes_from_txt(txt_path):
    """从导出 txt 按 第N章 切开，每章正文哈希。"""
    text = open(txt_path, encoding="utf-8", errors="replace").read()
    marks = list(CH_TXT_RE.finditer(text))
    out = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out[cn2int(m.group(1))] = _h(text[m.start():end])
    return out


def resolve_source(drama_root, link):
    """返回 (hashes, label, kind)。kind: project|txt。"""
    proj = link or derive_novel_project(drama_root)
    if proj and os.path.isdir(os.path.join(proj, "章节")):
        return hashes_from_project(proj), f"写小说项目 {os.path.basename(proj)}/章节", "project"
    cands = glob.glob(os.path.join(drama_root, "小说", "*.txt"))
    if not cands:
        sys.exit(f"未找到真源：既无同名 写小说/<剧>/章节，也无 {drama_root}/小说/*.txt")
    txt = max(cands, key=os.path.getsize)
    return hashes_from_txt(txt), f"漫剧源副本 小说/{os.path.basename(txt)}", "txt"


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
        marks = sorted({cn2int(x) for x in RAW_CH_RE.findall(open(raw, encoding="utf-8", errors="replace").read())})
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
            print(f"⚠️ 无源指纹基线（{os.path.basename(root)}）。当前真源：{label}，{len(cur)} 章。")
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
            print(f"✅ 源未变动（{label}，{len(cur)} 章）。漫剧源与基线一致，无需重切。")
        print('DRIFT={"status":"clean"}')
        return

    chap_to_eps = map_chapter_to_eps(root)
    prog = ep_progress(root)
    print(f"⚠️ 源小说已更新 → 漫剧《{os.path.basename(root)}》源过期（真源：{label}）：")
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
    print("  ① 同步源：写小说 export.py 重导出 → 覆盖 漫剧 小说/<剧>.txt")
    if risky:
        print(f"  ② ⚠️ 触及已生产集（章 {risky}）：逐集评估配音/出图/出视频是否返工，与用户确认")
    print("  ② raw-only：推进到那些集前从新源重切该窗口 raw（P0→P6），勿重跑整本 split（会重排集号波及已做集）")
    print("  ③ 处理完/接受现状后：`source_check.py <作品根> --record` 更新基线")
    print("DRIFT=" + json.dumps({"status": "drift", "drama": os.path.basename(root),
                                 "changed": changed, "added": added, "removed": removed,
                                 "risky_chapters": risky, "affected": affected}, ensure_ascii=False))


if __name__ == "__main__":
    main()
