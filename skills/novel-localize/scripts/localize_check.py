#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
localize_check.py — 出海本地化「确定性」机检（纯标准库）

诚实分工（同 mechanical_check / n2d_readiness 哲学）：脚本只算**确定性候选线索**，
是否地道/语气/文化适配到位由 LLM 人判。三类确定性查：
  1. 未译 CJK 残留 —— 拉丁/非 CJK 目标语译文里残留中文 = 漏译段落（ja/zh 等 CJK 系目标语跳过）。
  2. 术语未本地化 —— 术语表 source 专名仍出现在译文 = 专名漏锁（跨章漂移的源头）。
  3. 章节覆盖 + 长度比 —— 缺章 / 译文异常短（截断）。

  python3 localize_check.py <项目根> --lang en

读 `<项目根>/章节/*.md`（源）+ `<项目根>/出海/<lang>/章节/*.md`（译）+ `出海/<lang>/术语表.json`（术语锁），
落 `出海/<lang>/localize_report.json`。无依赖。
"""
import argparse
import glob
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.abspath(os.path.join(_HERE, "..", "..", "novel", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)
from project_io import read_chapters  # noqa: E402  本线共享读章接口

_CJK = r"一-鿿㐀-䶿"
_CJK_RE = re.compile(f"[{_CJK}]")

# 目标语用 CJK 文字系统时（含汉字），残留 CJK 不是"漏译"——跳过残留检查，仅靠术语表/覆盖兜底。
CJK_SCRIPT_LANGS = {"ja", "jp", "zh", "zh-hans", "zh-hant", "zh-tw", "yue"}
# 译文/源长度比的合理下限（按字符数）：低于此疑似截断。非 CJK 目标语字符通常多于中文，
# 故下限设保守的 0.5（只抓明显截断，不误伤正常压缩）。
LEN_RATIO_FLOOR = 0.5
# 整章 CJK 残留占比超此值 → block（大段未译）；0<占比≤此 → warn（零星专名/漏改）。
RESIDUE_BLOCK_RATIO = 0.02


def _cjk_len(s):
    return len(_CJK_RE.findall(s))


def _chapter_num(path):
    m = re.search(r"(\d+)", os.path.basename(path))
    return int(m.group(1)) if m else None


def load_glossary(project, lang):
    """读 出海/<lang>/术语表.json → [(source, target, type)]。支持 list 或 dict 两种格式。

    无术语表 → 返回空列表（优雅跳过术语检查，不臆造）。
    """
    path = os.path.join(project, "出海", lang, "术语表.json")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    terms = data.get("terms", data) if isinstance(data, dict) else data
    out = []
    if isinstance(terms, dict):
        for src, tgt in terms.items():
            out.append((str(src), str(tgt), ""))
    elif isinstance(terms, list):
        for t in terms:
            if isinstance(t, dict) and t.get("source"):
                out.append((str(t["source"]), str(t.get("target", "")), str(t.get("type", ""))))
    return out


def load_translated(project, lang):
    """读 出海/<lang>/章节/*.md → {章号: text}。"""
    cdir = os.path.join(project, "出海", lang, "章节")
    out = {}
    for p in sorted(glob.glob(os.path.join(cdir, "*.md"))):
        n = _chapter_num(p)
        if n is not None:
            with open(p, encoding="utf-8") as f:
                out[n] = f.read()
    return out


def check(project, lang):
    residue_on = lang.lower() not in CJK_SCRIPT_LANGS
    glossary = load_glossary(project, lang)
    translated = load_translated(project, lang)
    rows = []
    missing = []
    for idx, _path, src_text in read_chapters(project, None):
        flags = []
        if idx not in translated:
            missing.append(idx)
            rows.append({"chapter": idx, "status": "missing", "flags": ["未翻译（缺译文章节）"]})
            continue
        tgt = translated[idx]
        src_len = _cjk_len(src_text) or 1
        tgt_chars = len(tgt.strip())
        residue = _cjk_len(tgt) if residue_on else 0
        residue_ratio = residue / (len(tgt) or 1)
        # 1) 未译残留
        if residue_on and residue > 0:
            sev = "block" if residue_ratio >= RESIDUE_BLOCK_RATIO else "warn"
            flags.append(f"{'大段' if sev == 'block' else '零星'}未译 CJK 残留 {residue} 字")
        # 2) 术语未本地化（术语表 source 仍出现在译文）
        unlocalized = [src for src, _tgt, _t in glossary if src and src in tgt]
        if unlocalized:
            flags.append("术语未本地化: " + "、".join(unlocalized[:5]) + ("…" if len(unlocalized) > 5 else ""))
        # 3) 长度比（截断）
        ratio = round(tgt_chars / src_len, 2)
        if ratio < LEN_RATIO_FLOOR:
            flags.append(f"译文异常短(长度比 {ratio})，疑似截断")
        rows.append({
            "chapter": idx,
            "status": "ok" if not flags else "flagged",
            "residue_cjk": residue,
            "len_ratio": ratio,
            "unlocalized_terms": unlocalized,
            "flags": flags,
        })
    block = sum(1 for r in rows for f in r["flags"] if "大段未译" in f) + len(missing)
    summary = {
        "lang": lang,
        "residue_check": residue_on,
        "glossary_terms": len(glossary),
        "source_chapters": len(rows),
        "translated_chapters": len(translated),
        "missing_chapters": missing,
        "flagged_chapters": [r["chapter"] for r in rows if r["flags"]],
        "blocking": block,
    }
    return rows, summary


def main():
    ap = argparse.ArgumentParser(description="出海本地化确定性机检")
    ap.add_argument("project_path", help="项目根（含 章节/ 与 出海/<lang>/）")
    ap.add_argument("--lang", required=True, help="目标语言代码，如 en/id/th/ja")
    ap.add_argument("--json-out", help="报告落盘路径（默认 出海/<lang>/localize_report.json）")
    args = ap.parse_args()

    src = list(read_chapters(args.project_path, None))
    if not src:
        print(f"Error: {args.project_path}/章节 下没有可读源章节")
        return 1
    rows, summary = check(args.project_path, args.lang)
    out = args.json_out or os.path.join(args.project_path, "出海", args.lang, "localize_report.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"kind": "novel_localize_report", "summary": summary, "chapters": rows},
                  f, ensure_ascii=False, indent=2)

    print(f"本地化机检 [{args.lang}]：源 {summary['source_chapters']} 章 / 译 "
          f"{summary['translated_chapters']} 章，术语 {summary['glossary_terms']} 条")
    if summary["missing_chapters"]:
        print(f"  ⚠️ 缺译文：{len(summary['missing_chapters'])} 章")
    if summary["flagged_chapters"]:
        head = "、".join(f"第{c}章" for c in summary["flagged_chapters"][:8])
        print(f"  待复核：{head}{' …' if len(summary['flagged_chapters']) > 8 else ''}（block {summary['blocking']}）")
    if not summary["missing_chapters"] and not summary["flagged_chapters"]:
        print("  ✅ 0 残留 / 术语全锁 / 覆盖完整")
    print(f"  机读报告 → {out}")
    print("  ⚠️ 是否地道/语气/文化适配由 LLM 人判；机检只兜确定性残留/术语/覆盖")
    return 0


if __name__ == "__main__":
    sys.exit(main())
