#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""novel-review 机检：对已写章节做确定性质检，输出问题清单（不做判断题，那是 LLM 的活）。

用法:
    python3 mechanical_check.py <作品根> [--pov 王敦] [--min 1200] [--max 2800] \
        [--terms "金丹,道障,王敦密码,烈阳花"] [--no-plagiarism]

检查项：
  1. 格式：每章有 H1 标题 `# 第 N 章 《…》` + meta 注释头
  2. 字数：CJK 字数在 [min,max] 带宽内（漫剧档默认 1200-2800）
  3. 章末钩子：末段是否以悬念性收尾（启发式，低置信，仅提示）
  4. 视角"我"泄漏：引号外出现的"我"计数（第三人称限定下应≈0）
  5. 章号连续性：与 章节/ 目录里其他章是否有缺号/重号；与 设定/章纲.md 标题是否一致
  6. 术语出现统计：--terms 指定的规范术语在各章的出现次数（供人工看漂移）
  7. 原文照搬：24 字滑窗与 原作.txt 比对，命中即报（续写/外传用；--no-plagiarism 关闭）

输出：人类可读清单 + 末尾机器可读 JSON（FINDINGS=[...]）。
"""
import argparse, json, os, re, sys, glob

CJK = re.compile(r"[一-鿿]")
QUOTE_PAIRS = [("「", "」"), ("“", "”"), ("‘", "’"), ("『", "』")]


def cjk_count(s):
    return len(CJK.findall(s))


def strip_quotes(text):
    """移除成对引号内的内容，返回引号外文本（用于检测叙述里的'我'）。"""
    out = text
    for a, b in QUOTE_PAIRS:
        out = re.sub(re.escape(a) + r"[^" + re.escape(b) + r"]*" + re.escape(b), "", out)
    return out


def read(p):
    return open(p, encoding="utf-8", errors="replace").read()


def body_of(md):
    """去掉 H1 标题行与 meta 注释，取正文。"""
    lines = md.split("\n")
    body = [l for l in lines if not l.startswith("# 第") and not l.strip().startswith("<!--")]
    return "\n".join(body).strip()


def load_outline_titles(root):
    """从 设定/章纲.md 抽 {章号: 标题}（匹配 '第 N 章 《标题》'）。"""
    f = os.path.join(root, "设定", "章纲.md")
    titles = {}
    if os.path.exists(f):
        for m in re.finditer(r"第\s*0*(\d+)\s*章\s*[《<]([^》>]+)[》>]", read(f)):
            titles.setdefault(int(m.group(1)), m.group(2))
    return titles


def build_shingles(text, n=24):
    text = re.sub(r"\s+", "", text)
    return {text[i:i + n] for i in range(0, max(0, len(text) - n + 1))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--pov", default=None, help="第三人称限定的 POV 角色名（用于'我'泄漏提示）")
    ap.add_argument("--min", type=int, default=1200)
    ap.add_argument("--max", type=int, default=2800)
    ap.add_argument("--terms", default="", help="逗号分隔的规范术语，统计各章出现次数")
    ap.add_argument("--no-plagiarism", action="store_true")
    args = ap.parse_args()

    chdir = os.path.join(args.root, "章节")
    if not os.path.isdir(chdir):
        sys.exit(f"找不到章节目录：{chdir}")

    files = sorted(glob.glob(os.path.join(chdir, "第*章*.md")))  # 第N章.md 或 第N章_标题.md
    nums = []
    for f in files:
        m = re.search(r"第0*(\d+)章", os.path.basename(f))
        if m:
            nums.append(int(m.group(1)))
    outline = load_outline_titles(args.root)
    terms = [t.strip() for t in args.terms.split(",") if t.strip()]

    # 原文照搬：预载原作滑窗集
    src_shingles = None
    src_path = os.path.join(args.root, "原作.txt")
    if not args.no_plagiarism and os.path.exists(src_path):
        src_shingles = build_shingles(read(src_path), 24)

    findings = []
    pov_density = {}

    def add(ch, sev, dim, msg, ev=""):
        findings.append({"chapter": ch, "severity": sev, "dim": dim, "msg": msg, "evidence": ev[:40]})

    # 章号连续性
    if nums:
        full = set(range(min(nums), max(nums) + 1))
        miss = sorted(full - set(nums))
        dup = sorted({n for n in nums if nums.count(n) > 1})
        if miss:
            add(0, "🟡", "章号", f"缺号：{miss}")
        if dup:
            add(0, "🔴", "章号", f"重号：{dup}")

    for f in files:
        m = re.search(r"第0*(\d+)章", os.path.basename(f))
        ch = int(m.group(1)) if m else 0
        md = read(f)
        # 1 格式
        if not re.search(r"^# 第\s*\d+\s*章\s*[《<]", md, re.M):
            add(ch, "🔴", "格式", "缺规范 H1 标题 `# 第 N 章 《…》`")
        if "<!--" not in md:
            add(ch, "🟢", "格式", "缺 meta 注释头")
        # 标题与章纲一致
        mt = re.search(r"^# 第\s*\d+\s*章\s*[《<]([^》>]+)[》>]", md, re.M)
        if mt and ch in outline and mt.group(1).strip() != outline[ch].strip():
            add(ch, "🟡", "标题", f"标题与章纲不符：正文「{mt.group(1)}」 vs 章纲「{outline[ch]}」")
        is_demo = "demo=true" in md
        body = body_of(md)
        # 2 字数（demo 特长开篇豁免带宽）
        wc = cjk_count(body)
        if not is_demo:
            if wc < args.min:
                add(ch, "🟡", "字数", f"偏短 {wc} 字（<{args.min}）")
            elif wc > args.max:
                add(ch, "🟡", "字数", f"偏长 {wc} 字（>{args.max}）")
        # 3 钩子 = 判断题，交 LLM（见 checklist.md 维度5）；机检不报，避免误判好钩子。
        # 4 视角"我"密度：内心独白（——我…/自由直接引语）在第三人称限定里合法，机检无法
        #    可靠区分"合法独白"与"真串视角"——这是判断题，交 LLM。机检只收集密度，末尾给一条
        #    抽查建议（指向密度最高的章），不当 🟡 噪声刷屏。
        if args.pov:
            outside = strip_quotes(body)
            mono_removed = re.sub(r"[—－]{1,2}[^\n。！？!?…]*", "", outside)
            pov_density[ch] = mono_removed.count("我")
        # 5 术语统计（仅记录，供人看漂移）
        # 6 原文照搬
        if src_shingles is not None:
            bsh = re.sub(r"\s+", "", body)
            hit = None
            for i in range(0, max(0, len(bsh) - 24 + 1), 6):
                w = bsh[i:i + 24]
                if w in src_shingles:
                    hit = w
                    break
            if hit:
                add(ch, "🔴", "原文照搬", "发现与原作连续雷同片段（≥24字）", hit)

    # 术语出现矩阵（单列打印，不进 findings）
    term_matrix = {}
    if terms:
        for f in files:
            ch = int(re.search(r"第0*(\d+)章", os.path.basename(f)).group(1))
            md = read(f)
            term_matrix[ch] = {t: md.count(t) for t in terms}

    # ---- 输出 ----
    print(f"# 机检报告 — {args.root}")
    print(f"章节数：{len(files)}（{min(nums) if nums else '-'}–{max(nums) if nums else '-'}）"
          f" | POV：{args.pov or '未指定'} | 原文照搬检查：{'开' if src_shingles is not None else '关'}")
    order = {"🔴": 0, "🟡": 1, "🟢": 2}
    findings.sort(key=lambda x: (order.get(x["severity"], 9), x["chapter"]))
    print(f"\n确定性问题 {len(findings)} 条：")
    for x in findings:
        loc = "全局" if x["chapter"] == 0 else f"第{x['chapter']}章"
        ev = f" ｜证据「{x['evidence']}」" if x["evidence"] else ""
        print(f"  {x['severity']} [{loc}·{x['dim']}] {x['msg']}{ev}")
    if args.pov and pov_density:
        top = sorted(pov_density.items(), key=lambda kv: -kv[1])[:8]
        top = [(c, n) for c, n in top if n > 0]
        if top:
            print(f"\n视角抽查建议（POV={args.pov} 第三人称限定）：以下章叙述中第一人称『我』密度较高，"
                  f"多为内心独白（合法），但**请 LLM 优先抽查这几章是否有真串视角**：")
            print("  " + "、".join(f"第{c}章({n})" for c, n in top))
    if term_matrix:
        print("\n术语出现次数（看跨章漂移；0 与突变值得注意）：")
        print("  章 | " + " | ".join(terms))
        for ch in sorted(term_matrix):
            print(f"  {ch:>2} | " + " | ".join(str(term_matrix[ch][t]) for t in terms))
    counts = {s: sum(1 for x in findings if x["severity"] == s) for s in ("🔴", "🟡", "🟢")}
    print(f"\n小结：🔴 {counts['🔴']}  🟡 {counts['🟡']}  🟢 {counts['🟢']}")
    print("\n<!-- FINDINGS_JSON")
    print(json.dumps(findings, ensure_ascii=False))
    print("FINDINGS_JSON -->")


if __name__ == "__main__":
    main()
