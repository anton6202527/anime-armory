#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_style.py — 文风指纹提取 + 漂移比对（确定性，纯标准库）

不需要 NLP 库 / 不调 LLM：只做可复现的文本统计，算出一份《风格指纹.json》。
语义层（"这段像不像名家"）交给 LLM 人判；本脚本只负责确定性的句式/节奏/词频骨架，
跟 novel-review/mechanical_check.py 同一分工哲学（脚本算确定项，LLM 判语义项）。

两种用法：
  1) 提取指纹
     python3 extract_style.py --source <文件或目录> --output <作品根>/设定/风格指纹.json
  2) 漂移比对（给 novel-review 做"文风漂移"机检）
     python3 extract_style.py --compare <锚点指纹.json> <候选文本或指纹> [--json-out 审稿/style_drift.json]
     - 第二个参数可以是另一份指纹 .json，也可以是章节文本（自动先提取再比）。

测试：cd skills/novel-style/scripts && python3 -m pytest test_extract_style.py
"""
import os
import re
import json
import argparse
from collections import Counter

SCHEMA_VERSION = 1
STYLE_SOURCE_RIGHTS = ("project-demo", "user-owned", "licensed", "public-domain", "unknown")
AUTHORIZED_STYLE_RIGHTS = {"project-demo", "user-owned", "licensed", "public-domain"}

# 句子终结符（中英）
_SENT_END = "。！？!?…\n"
# 引号对（对白识别）
_QUOTE_PAIRS = [("“", "”"), ("「", "」"), ("『", "』"), ("\"", "\"")]
# 高频虚词/停用词，不进词频锚点
_STOPWORDS = set("""
的 了 是 在 我 你 他 她 它 们 这 那 和 与 也 都 就 又 不 没 有 个 上 下 中 里
一 二 三 着 过 把 被 给 让 向 从 到 对 之 其 而 且 但 却 还 很 太 更 最 些 啊 呢
吗 吧 呀 啦 嗯 哦 道 说 自己 什么 怎么 这样 那样 因为 所以 如果 已经 一个 起来
""".split())

_CJK = r"一-鿿"


def _read_text(path):
    """读单文件或目录（.txt/.md）的全文，目录按文件名自然序拼接。"""
    if os.path.isdir(path):
        files = []
        for name in os.listdir(path):
            if name.lower().endswith((".txt", ".md")) and not name.startswith("_"):
                files.append(os.path.join(path, name))
        files.sort(key=_chapter_sort_key)
        return "\n".join(_read_one(f) for f in files)
    return _read_one(path)


def _read_one(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _chapter_sort_key(path):
    """从文件名抽章号自然排序，抽不到退回文件名。"""
    base = os.path.basename(path)
    m = re.search(r"(\d+)", base)
    return (0, int(m.group(1))) if m else (1, base)


def _strip_markup(text):
    """去掉 markdown 标题/分隔，避免污染句长统计。"""
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or set(s) <= set("-=*"):
            continue
        lines.append(s)
    return "\n".join(lines)


def _split_sentences(text):
    out, cur = [], []
    for ch in text:
        cur.append(ch)
        if ch in _SENT_END:
            seg = "".join(cur).strip(_SENT_END + " \t")
            if seg:
                out.append(seg)
            cur = []
    seg = "".join(cur).strip(_SENT_END + " \t")
    if seg:
        out.append(seg)
    return out


def _cjk_len(s):
    return len(re.findall(f"[{_CJK}]", s))


def _dialogue_chars(text):
    total = 0
    for lq, rq in _QUOTE_PAIRS:
        if lq == rq:  # 直引号：成对计
            quoted = re.findall(re.escape(lq) + r"([^" + re.escape(lq) + r"]*)" + re.escape(rq), text)
        else:
            quoted = re.findall(re.escape(lq) + r"(.*?)" + re.escape(rq), text, re.DOTALL)
        total += sum(_cjk_len(q) for q in quoted)
    return total


def _lexicon(text, top=20):
    """无分词环境下的词频锚点：抽 2-4 字 CJK 连续片段做 n-gram 计数，滤停用词。"""
    runs = re.findall(f"[{_CJK}]{{2,}}", text)
    counter = Counter()
    for run in runs:
        n = len(run)
        for size in (4, 3, 2):
            for i in range(n - size + 1):
                gram = run[i:i + size]
                if gram in _STOPWORDS:
                    continue
                if any(c in _STOPWORDS for c in gram) and size == 2:
                    continue
                counter[gram] += 1
    # 去掉被更长高频词完全包含的短词噪声
    items = [(w, c) for w, c in counter.items() if c >= 3]
    items.sort(key=lambda x: (-x[1], -len(x[0])))
    seen, result = [], []
    for w, c in items:
        if any(w in longer and w != longer for longer, _ in result):
            continue
        result.append((w, c))
        if len(result) >= top:
            break
    return [{"term": w, "count": c} for w, c in result]


def _extract_character_text(text, name):
    """提取特定角色的对白与心声。"""
    segments = []
    # 对白匹配: "姓名道：“...”" 或 “...”，姓名...
    # 简单实现：找包含姓名的段落，且提取引号内内容
    for lq, rq in _QUOTE_PAIRS:
        pattern = re.compile(re.escape(lq) + r"(.*?)" + re.escape(rq), re.DOTALL)
        # 找引号前后的姓名提示
        for m in pattern.finditer(text):
            content = m.group(1)
            start, end = m.start(), m.end()
            # 引号前后 15 字内出现姓名
            context_before = text[max(0, start-15):start]
            context_after = text[end:end+15]
            if name in context_before or name in context_after:
                segments.append(content)
    return "\n".join(segments)


def fingerprint(text, source="<inline>", character=None, *, source_rights="project-demo",
                style_source_name="", style_source_author="", authorization_note=""):
    if character:
        text = _extract_character_text(text, character)
        if not text.strip():
            # Fallback if no dialogue found
            return {"error": f"未在样本中找到角色 {character} 的对白"}

    raw = _strip_markup(text)
    total_cjk = _cjk_len(raw) or 1
    sents = _split_sentences(raw)
    lengths = [_cjk_len(s) for s in sents if _cjk_len(s) > 0]
    n = len(lengths) or 1
    avg = sum(lengths) / n
    short = sum(1 for x in lengths if x <= 12) / n
    long_ = sum(1 for x in lengths if x >= 30) / n
    med = sorted(lengths)[len(lengths) // 2] if lengths else 0

    de = len(re.findall(r"[的地得]", raw))
    puncts = len(re.findall(r"[，。！？、；：]", raw))
    ellipsis = len(re.findall(r"…|\.\.\.|——|—", raw))
    commas = len(re.findall(r"，", raw))
    periods = len(re.findall(r"[。！？]", raw)) or 1

    if avg <= 14 and short >= 0.5:
        pace = "fast_pulse"
    elif avg >= 24 or long_ >= 0.25:
        pace = "dense"
    else:
        pace = "measured"

    return {
        "schema_version": SCHEMA_VERSION,
        "source": source,
        "style_source_rights": {
            "status": source_rights,
            "source_name": style_source_name,
            "source_author": style_source_author,
            "authorization_note": authorization_note,
            "policy": "指纹仅用于授权/自有/公版/项目Demo样本的抽象风格约束；不得做未授权姓名式复刻。",
        },
        "sampled_chars": total_cjk,
        "sentence_count": len(lengths),
        "syntax_profile": {
            "avg_sentence_length": round(avg, 2),
            "median_sentence_length": med,
            "short_sentence_ratio": round(short, 3),   # <=12 字
            "long_sentence_ratio": round(long_, 3),    # >=30 字
        },
        "dialogue_ratio": round(_dialogue_chars(raw) / total_cjk, 3),
        "descriptive_habits": {
            "de_particle_density": round(de / total_cjk * 100, 3),   # 的地得 / 100 字
            "punctuation_density": round(puncts / total_cjk * 100, 3),
            "ellipsis_dash_per_kchar": round(ellipsis / total_cjk * 1000, 3),
            "comma_to_period_ratio": round(commas / periods, 3),
        },
        "lexicon_anchor": _lexicon(raw),
        "rhythm": {"pace_tag": pace},
    }


# ---- 漂移比对 ----

def _flatten(fp):
    s = fp["syntax_profile"]
    d = fp["descriptive_habits"]
    return {
        "avg_sentence_length": s["avg_sentence_length"],
        "short_sentence_ratio": s["short_sentence_ratio"],
        "long_sentence_ratio": s["long_sentence_ratio"],
        "dialogue_ratio": fp["dialogue_ratio"],
        "de_particle_density": d["de_particle_density"],
        "comma_to_period_ratio": d["comma_to_period_ratio"],
    }


# 各指标的"显著漂移"阈值（相对差），超过即记一条 flag
_DRIFT_BANDS = {
    "avg_sentence_length": 0.35,
    "short_sentence_ratio": 0.40,
    "long_sentence_ratio": 0.50,
    "dialogue_ratio": 0.50,
    "de_particle_density": 0.40,
    "comma_to_period_ratio": 0.45,
}


def compare(anchor_fp, candidate_fp):
    a, c = _flatten(anchor_fp), _flatten(candidate_fp)
    metrics, flags = {}, []
    rel_sum = 0.0
    for k in a:
        base = abs(a[k]) if abs(a[k]) > 1e-6 else 1e-6
        rel = abs(c[k] - a[k]) / base
        rel_sum += rel
        metrics[k] = {"anchor": a[k], "candidate": c[k], "rel_diff": round(rel, 3)}
        if rel > _DRIFT_BANDS[k]:
            flags.append({
                "metric": k,
                "anchor": a[k],
                "candidate": c[k],
                "rel_diff": round(rel, 3),
                "band": _DRIFT_BANDS[k],
                "severity": "建议级",
            })
    drift_score = round(rel_sum / len(a), 3)
    pace_shift = anchor_fp["rhythm"]["pace_tag"] != candidate_fp["rhythm"]["pace_tag"]
    if pace_shift:
        flags.append({
            "metric": "pace_tag",
            "anchor": anchor_fp["rhythm"]["pace_tag"],
            "candidate": candidate_fp["rhythm"]["pace_tag"],
            "severity": "建议级",
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "drift_score": drift_score,        # 0=完全一致，越大越漂
        "drift_flag": bool(flags),
        "metrics": metrics,
        "flags": flags,
        "note": "drift_score/flags 为确定性信号，是否真的'文风崩了'仍需 LLM 结合语境人判",
    }


def _load_fp_or_text(path):
    """参数既可能是指纹 json，也可能是章节文本——自动判别。"""
    if path.lower().endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "syntax_profile" in data:
            return data
    return fingerprint(_read_text(path), source=path)


def main():
    p = argparse.ArgumentParser(description="文风指纹提取 + 漂移比对（确定性）")
    p.add_argument("--source", help="样本文本/目录（提取模式）")
    p.add_argument("--output", help="指纹 JSON 落盘路径（提取模式）")
    p.add_argument("--character", help="提取特定角色的对白与心声指纹")
    p.add_argument("--source-rights", default="project-demo", choices=STYLE_SOURCE_RIGHTS,
                   help="样本权利来源：project-demo/user-owned/licensed/public-domain/unknown")
    p.add_argument("--style-source-name", default="", help="样本作品名；若填写，必须明确 source-rights")
    p.add_argument("--style-source-author", default="", help="样本作者名；若填写，必须明确 source-rights")
    p.add_argument("--authorization-note", default="", help="授权/公版依据简述")
    p.add_argument("--compare", nargs=2, metavar=("ANCHOR", "CANDIDATE"),
                   help="比对两份（指纹.json 或 文本）算漂移分")
    p.add_argument("--json-out", help="比对结果落盘路径")
    args = p.parse_args()

    if args.compare:
        anchor = _load_fp_or_text(args.compare[0])
        cand = _load_fp_or_text(args.compare[1])
        result = compare(anchor, cand)
        if args.json_out:
            os.makedirs(os.path.dirname(args.json_out) or ".", exist_ok=True)
            with open(args.json_out, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"漂移报告 → {args.json_out}")
        print(f"drift_score={result['drift_score']}  flags={len(result['flags'])}"
              f"  {'⚠️ 文风疑似漂移' if result['drift_flag'] else '✅ 文风稳定'}")
        return

    if not args.source or not args.output:
        p.error("提取模式需同时给 --source 和 --output")
    if (args.style_source_name or args.style_source_author) and args.source_rights not in AUTHORIZED_STYLE_RIGHTS:
        print("[err] 命名作品/作者样本必须声明 project-demo/user-owned/licensed/public-domain；"
              "未授权姓名式复刻不允许。")
        sys.exit(2)
    fp = fingerprint(
        _read_text(args.source),
        source=args.source,
        character=args.character,
        source_rights=args.source_rights,
        style_source_name=args.style_source_name,
        style_source_author=args.style_source_author,
        authorization_note=args.authorization_note,
    )
    if "error" in fp:
        print(f"[err] {fp['error']}")
        sys.exit(1)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(fp, f, ensure_ascii=False, indent=2)
    sp = fp["syntax_profile"]
    print(f"指纹 → {args.output}")
    print(f"  句均长 {sp['avg_sentence_length']} · 短句比 {sp['short_sentence_ratio']} "
          f"· 对白比 {fp['dialogue_ratio']} · 节奏 {fp['rhythm']['pace_tag']}")
    print(f"  词频锚点 top: {', '.join(x['term'] for x in fp['lexicon_anchor'][:8])}")


if __name__ == "__main__":
    main()
