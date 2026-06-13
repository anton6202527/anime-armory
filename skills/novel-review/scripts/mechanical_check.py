#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""novel-review 机检：对已写章节做确定性质检，输出问题清单（不做判断题，那是 LLM 的活）。

用法:
    python3 mechanical_check.py <作品根> [--pov 王敦] [--min 800] [--max 1800] \
        [--terms "金丹,道障,王敦密码,烈阳花"] [--no-auto-terms] [--no-plagiarism]

检查项：
  1. 格式：每章有 H1 标题 `# 第N章 标题`（N 可阿拉伯/中文数字，标题可带《》或裸标题）+ meta 注释头
  2. 字数：CJK 字数在 [min,max] 带宽内（漫剧档默认 800-1800）
  3. 视角"我"密度：引号外出现的"我"计数（第三人称限定下交 LLM 抽查）
  4. 章号连续性：与 章节/ 目录里其他章是否有缺号/重号；与 设定/章纲.md 标题是否一致
  5. 术语出现统计：自动从 设定/ 抽术语，也可用 --terms 追加（供人工看漂移）
  6. 原文照搬：24 字滑窗与 原作.txt 比对，命中即报（续写/外传用；--no-plagiarism 关闭）

输出：人类可读清单 + 末尾机器可读 JSON（FINDINGS=[...]）。
"""
import argparse, json, os, re, sys, glob
from datetime import date

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "novel", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from text_utils import cjk_count, strip_quotes  # noqa: E402  vendored 进 novel/_lib

# 章号数字：阿拉伯 / 全角 / 中文数字都接受（# 第1章 / # 第一章 / # 第 12 章 均合规）
CH_NUM = r"[0-9０-９一二三四五六七八九十百千零〇两]+"


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


def extract_terms_from_settings(root):
    """Best-effort canonical term extraction from setting-bible files."""
    terms = set()
    setting_dir = os.path.join(root, "设定")
    md_files = ["设定圣经.md", "角色卡.md", "世界观.md", "作者口吻.md", "创作蓝图.md"]
    for fname in md_files:
        path = os.path.join(setting_dir, fname)
        if not os.path.exists(path):
            continue
        text = read(path)
        for m in re.finditer(r"[《「『`“]([^》」』`”]{2,24})[》」』`”]", text):
            terms.add(m.group(1).strip())
        for line in text.splitlines():
            raw = line.strip()
            if not raw or raw.startswith(("---", "|---")):
                continue
            if raw.startswith("|"):
                cols = [c.strip() for c in raw.strip("|").split("|")]
                if cols and cols[0] not in ("字段", "项目", "术语", "名称", "角色", "锚点 ID"):
                    maybe = re.sub(r"\s+", "", cols[0])
                    if _term_like(maybe):
                        terms.add(maybe)
            elif raw.startswith(("- ", "* ")):
                head = re.split(r"[:：—-]", raw[2:].strip(), 1)[0].strip()
                if _term_like(head):
                    terms.add(head)
    anchor_path = os.path.join(setting_dir, "锚点表.json")
    if os.path.exists(anchor_path):
        try:
            data = json.loads(read(anchor_path))
            _collect_json_terms(data, terms)
        except json.JSONDecodeError:
            pass
    return sorted(terms, key=lambda x: (len(x), x))


def _term_like(value):
    if not (2 <= len(value) <= 18):
        return False
    if value in {"首现章", "复用范围", "代价或约束", "说明", "状态", "标题"}:
        return False
    return bool(re.search(r"[\u4e00-\u9fffA-Za-z0-9]", value))


def _collect_json_terms(value, terms):
    if isinstance(value, dict):
        for key, val in value.items():
            if key in {"event", "事件", "time", "时间", "present_with", "在场人", "known", "已知情报"}:
                _collect_json_terms(val, terms)
            elif isinstance(val, (dict, list)):
                _collect_json_terms(val, terms)
    elif isinstance(value, list):
        for item in value:
            _collect_json_terms(item, terms)
    elif isinstance(value, str):
        for part in re.split(r"[，,、/\s]+", value):
            part = part.strip()
            if _term_like(part):
                terms.add(part)


def build_shingles(text, n=24):
    text = re.sub(r"\s+", "", text)
    return {text[i:i + n] for i in range(0, max(0, len(text) - n + 1))}


def chapter_number_from_path(path):
    match = re.search(r"第0*(\d+)章", os.path.basename(path))
    return int(match.group(1)) if match else None


def chapter_sort_key(path):
    number = chapter_number_from_path(path)
    return (number is None, number or 0, os.path.basename(path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--pov", default=None, help="第三人称限定的 POV 角色名（用于'我'泄漏提示）")
    ap.add_argument("--min", type=int, default=800)
    ap.add_argument("--max", type=int, default=1800)
    ap.add_argument("--terms", default="", help="逗号分隔的规范术语，统计各章出现次数")
    ap.add_argument("--no-auto-terms", action="store_true",
                    help="不从 设定/ 自动抽取术语，只使用 --terms")
    ap.add_argument("--no-plagiarism", action="store_true")
    ap.add_argument("--json-out", default=None,
                    help="可选：把机检结果写成 JSON，供 review_report.json 汇总")
    args = ap.parse_args()

    chdir = os.path.join(args.root, "章节")
    if not os.path.isdir(chdir):
        sys.exit(f"找不到章节目录：{chdir}")

    files = sorted(glob.glob(os.path.join(chdir, "第*章*.md")), key=chapter_sort_key)  # 第N章.md 或 第N章_标题.md
    nums = []
    for f in files:
        m = re.search(r"第0*(\d+)章", os.path.basename(f))
        if m:
            nums.append(int(m.group(1)))
    outline = load_outline_titles(args.root)
    manual_terms = [t.strip() for t in args.terms.split(",") if t.strip()]
    auto_terms = [] if args.no_auto_terms else extract_terms_from_settings(args.root)
    terms = sorted(set(manual_terms + auto_terms), key=lambda x: (len(x), x))

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
        # 1 格式：H1 需是 `# 第N章 …`，N 可为阿拉伯或中文数字，标题可带《》或裸标题
        if not re.search(r"^#\s*第\s*" + CH_NUM + r"\s*章", md, re.M):
            add(ch, "🔴", "格式", "缺规范 H1 标题 `# 第N章 标题`（N 可中文/阿拉伯数字）")
        if "<!--" not in md:
            add(ch, "🟢", "格式", "缺 meta 注释头")
        # 标题与章纲一致（兼容《…》与裸标题两种写法）
        mt = re.search(r"^#\s*第\s*" + CH_NUM + r"\s*章\s*(?:[《<]([^》>]+)[》>]|([^\n]*))$", md, re.M)
        title = (mt.group(1) or mt.group(2) or "").strip() if mt else ""
        if mt and ch in outline and title != outline[ch].strip():
            add(ch, "🟡", "标题", f"标题与章纲不符：正文「{title}」 vs 章纲「{outline[ch]}」")
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
        source = "手动+设定自动" if manual_terms and auto_terms else ("设定自动" if auto_terms else "手动")
        print(f"\n术语出现次数（{source}；看跨章漂移，0 与突变值得注意）：")
        print("  章 | " + " | ".join(terms))
        for ch in sorted(term_matrix):
            print(f"  {ch:>2} | " + " | ".join(str(term_matrix[ch][t]) for t in terms))
    counts = {s: sum(1 for x in findings if x["severity"] == s) for s in ("🔴", "🟡", "🟢")}
    print(f"\n小结：🔴 {counts['🔴']}  🟡 {counts['🟡']}  🟢 {counts['🟢']}")
    payload = {
        "schema_version": 1,
        "kind": "novel_mechanical_findings",
        "project_root": args.root,
        "generated_at": date.today().isoformat(),
        "findings": findings,
        "counts": counts,
        "pov_density": pov_density,
        "term_matrix": term_matrix,
        "terms_source": {
            "manual": manual_terms,
            "auto": auto_terms,
        },
    }
    if args.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)), exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    print("\n<!-- FINDINGS_JSON")
    print(json.dumps(findings, ensure_ascii=False))
    print("FINDINGS_JSON -->")


if __name__ == "__main__":
    main()
