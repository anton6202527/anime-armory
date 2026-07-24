#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plot_variety_audit.py — 情节节拍多样性/桥段复读 机检（advisory·纯标准库）。

为什么：现有重复检测只有**字面级**（mechanical_check 的 shingle 近重复、句式模板），
抓不到"每个弧段都是危机→打脸→升级循环""连续五章都靠身份揭露撑场"这类**桥段级复读**——
它们换了措辞，字面相似度极低，但读者一眼看穿"套路又来了"。这是 AI 长篇最常见的
想象力塌陷形态。对标兄弟线镜头多样性审计 shot_variety_audit（构图重复/景别单调/再钩间隔）的
成熟范式，给 novel 补上情节侧的"视觉不重复"审计。

六个信号（全部 advisory·blocking 恒 0）：
  ① beat_monotony        同一主导节拍连续 ≥3 章（打脸连打三章，疲劳）→ 建议级
  ② beat_cycle_repetition 节拍序列出现 ABAB… 周期循环 ≥3 轮 → 建议级
  ③ payoff_gap           商业爽文向连续 >2 章零爽点命中（马良口径：铺垫不超 2 章；
                          品质向平台放宽到 4 章且只 info——别拿爽文密度尺量文学向）
  ④ hook_type_repetition 章末钩型 3 连同型（全靠问句钩/全靠危机钩）→ info
  ⑤ opening_pattern_repetition 连续 ≥4 章开篇同型（都是对话开头/都是醒来开头）→ info
  ⑥ payoff_without_suppression 爽点密集章的回溯窗口（含本章）零受挫命中=无抑之扬
                          （欲扬先抑/打脸三拍工艺：没有"抑"垫势能的爽点是打空气，
                          优越感地基缺失；前 2 章豁免——开局爽点合法）→ 建议级

口径纪律：
  - 节拍识别是**关键词密度启发式**（confidence=heuristic），只报候选，好不好看仍需人判；
    番外/楔子/序章/回顾章豁免（有意重复或非主线，打断 run 不计入）。
  - 词表复用 novel/_lib/keyword_banks.py（单一真值源），不另建一套。
  - blocking 恒 0：情节多样性是创作判断，机检永不硬挡（Creative heuristics stay advisory）。

用法：
    python3 plot_variety_audit.py <作品根> [--json]
测试：cd skills/novel-review/scripts && python3 -m pytest test_plot_variety_audit.py
"""
import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_WIKI = os.path.abspath(os.path.join(_HERE, "..", "..", "novel-wiki", "scripts"))
_LIB = os.path.abspath(os.path.join(_HERE, "..", "..", "novel", "_lib"))
for _p in (_WIKI, _LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    from wiki_builder import list_chapters
except Exception:  # 独立跑/测试桩兜底：纯函数不依赖它，仍可单测
    def list_chapters(project, *a, **k):  # type: ignore
        return []
try:
    from keyword_banks import (PAYOFF_KW, FEMALE_PAYOFF_KW, SETBACK_KW, payoff_bank_for,
                               classify_platform, PROFILE_COMMERCIAL)
except Exception:
    PAYOFF_KW, FEMALE_PAYOFF_KW, SETBACK_KW = [], [], []
    def payoff_bank_for(*signals):  # type: ignore
        return list(PAYOFF_KW)
    def classify_platform(p):  # type: ignore
        return "商业爽文向"
    PROFILE_COMMERCIAL = "商业爽文向"

# ── 阈值（internal-heuristic·env 可标定·confidence=low）───────────────────────
BEAT_MIN_HITS = int(os.environ.get("NOVEL_PLOTVAR_BEAT_MIN_HITS", "2"))       # 主导节拍最少命中次数
MONOTONY_RUN = int(os.environ.get("NOVEL_PLOTVAR_MONOTONY_RUN", "3"))         # 同节拍连跑几章算单调
CYCLE_MIN_REPEATS = int(os.environ.get("NOVEL_PLOTVAR_CYCLE_REPEATS", "3"))   # ABAB 循环最少轮数
PAYOFF_GAP_COMMERCIAL = int(os.environ.get("NOVEL_PLOTVAR_PAYOFF_GAP", "2"))  # 商业向：铺垫不超 N 章
PAYOFF_GAP_LITERARY = int(os.environ.get("NOVEL_PLOTVAR_PAYOFF_GAP_LIT", "4"))
HOOK_TYPE_RUN = int(os.environ.get("NOVEL_PLOTVAR_HOOK_RUN", "3"))            # 章末钩型几连同型
OPENING_RUN = int(os.environ.get("NOVEL_PLOTVAR_OPENING_RUN", "4"))           # 开篇同型几连
PAYOFF_DENSE_MIN = int(os.environ.get("NOVEL_PLOTVAR_PAYOFF_DENSE_MIN", "3"))  # 爽点密集章最少命中
SUPPRESS_LOOKBACK = int(os.environ.get("NOVEL_PLOTVAR_SUPPRESS_LOOKBACK", "3"))  # "抑"回溯窗口（含本章）
SUPPRESS_EXEMPT_CHAPTERS = 2   # 开局爽点豁免（黄金三章开局可以直接爽）
TAIL_CHARS = 120   # 章末断章区（与 hook_endings.TAIL_CHARS 同口径）
HEAD_CHARS = 60    # 章首开篇区
PROVENANCE = "internal-heuristic·confidence=low"

# 豁免章（有意非主线节拍）：番外/楔子/序章/回顾/尾声——打断 run，不参与判定。
_EXEMPT_TITLE_RE = re.compile(r"番外|楔子|序章|回顾|尾声|后记|人物志|设定集")

# ── 节拍词表（桥段级·与 keyword_banks 的行文级词桶正交）─────────────────────
# 每类是网文最常复用的"桥段"（beat）。命中≥BEAT_MIN_HITS 才算该章带此节拍——单次命中
# 可能只是提及；主导节拍=命中最多的一类。词表刻意收窄到高置信桥段词，宁漏勿滥。
BEAT_BANKS = {
    "打脸翻盘": ["打脸", "碾压", "吊打", "反杀", "翻盘", "解气", "逆袭", "跪下", "求饶",
             "后悔", "傻眼", "脸色惨白", "下不来台"],
    "升级突破": ["突破", "晋升", "晋级", "进阶", "升级", "觉醒", "境界提升", "更进一步",
             "瓶颈", "破境", "凝丹", "筑基", "金丹", "元婴"],
    "身份揭露": ["掉马", "身份暴露", "揭穿", "竟是", "认出", "真实身份", "马甲", "原来是他",
             "原来是她", "正是当年", "真面目"],
    "危机压迫": ["危机", "追杀", "围攻", "绝境", "大军压境", "兵临城下", "袭来", "陷阱",
             "埋伏", "生死关头", "命悬一线"],
    "情感兑现": list(FEMALE_PAYOFF_KW),
    "奇遇馈赠": ["奇遇", "宝物", "传承", "秘籍", "机缘", "掉落", "奖励", "宝藏", "遗迹",
             "洞府", "神器", "灵药"],
}

# ── 章末钩型（多样性视角：钩子"够不够强"归 hook_endings，这里只看"是不是总用同一招"）──
_HOOK_TYPE_RULES = [
    ("问句钩", lambda t: "？" in t or "?" in t),
    ("反转钩", lambda t: any(w in t for w in ("竟然", "竟是", "没想到", "不料", "原来", "却见", "赫然"))),
    ("危机钩", lambda t: any(w in t for w in ("刀光", "袭来", "扑来", "爆炸", "坠落", "逼近", "鲜血", "黑暗"))),
    ("留白钩", lambda t: t.rstrip("”\"』」）)】》").endswith(("…", "……", "—", "——"))),
    ("登场钩", lambda t: bool(re.search(r"(出现|现身|走来|传来|响起)", t))),
]

# ── 开篇型 ────────────────────────────────────────────────────────────────
_OPENING_RULES = [
    ("对话开头", lambda t: t.lstrip().startswith(("「", "“", "\"", "『"))),
    ("醒来开头", lambda t: any(w in t[:40] for w in ("醒来", "睁开眼", "睁眼", "从梦中"))),
    ("时间开头", lambda t: t.lstrip().startswith(("清晨", "翌日", "次日", "第二天", "夜", "黄昏",
                                             "三日后", "半月后", "一个月后", "数日后"))),
]


def _norm_title(path):
    return os.path.basename(str(path or ""))


def is_exempt(path):
    return bool(_EXEMPT_TITLE_RE.search(_norm_title(path)))


def beat_hits(text):
    """{节拍类型: 命中次数}（每词按出现次数累计）。纯函数·可测。"""
    hits = {}
    t = text or ""
    for beat, words in BEAT_BANKS.items():
        n = sum(t.count(w) for w in words)
        if n:
            hits[beat] = n
    return hits


def dominant_beat(text, min_hits=None):
    """该章主导节拍（命中最多且 ≥min_hits），无则 None。命中并列取字典序保证确定性。"""
    min_hits = BEAT_MIN_HITS if min_hits is None else min_hits
    hits = beat_hits(text)
    best = None
    for beat in sorted(hits):
        if hits[beat] >= min_hits and (best is None or hits[beat] > hits[best]):
            best = beat
    return best


def hook_type(text, tail_chars=TAIL_CHARS):
    """章末钩型（规则序=优先级），无钩返回 None。纯函数·可测。"""
    tail = (text or "").rstrip()[-tail_chars:]
    if not tail:
        return None
    for name, rule in _HOOK_TYPE_RULES:
        if rule(tail):
            return name
    return None


def opening_type(text, head_chars=HEAD_CHARS):
    """章首开篇型，无匹配返回 None。纯函数·可测。"""
    head = (text or "").lstrip()[:head_chars]
    if not head:
        return None
    for name, rule in _OPENING_RULES:
        if rule(head):
            return name
    return None


def _runs(seq):
    """把 [(章号, 值)] 压成 [(值, [章号...])] 的连续段；值为 None 的段也保留（供 gap 判定）。"""
    out = []
    for ch, val in seq:
        if out and out[-1][0] == val:
            out[-1][1].append(ch)
        else:
            out.append((val, [ch]))
    return out


def detect_beat_monotony(beat_seq, alerts, run_len=None):
    """信号①：同一主导节拍连续 ≥run_len 章。beat_seq=[(章号, beat|None)]。"""
    run_len = MONOTONY_RUN if run_len is None else run_len
    n = 0
    for val, chapters in _runs(beat_seq):
        if val and len(chapters) >= run_len:
            alerts.append({
                "type": "beat_monotony", "severity": "建议级", "auto": True,
                "chapter": chapters[0], "chapters": chapters,
                "note": (f"第{chapters[0]}–{chapters[-1]}章连续 {len(chapters)} 章主导节拍都是"
                         f"「{val}」——同一桥段连打读者会疲劳，穿插别的节拍换气"
                         f"（{PROVENANCE}·桥段好坏仍需人判）"),
            })
            n += 1
    return n


def detect_beat_cycle(beat_seq, alerts, min_repeats=None):
    """信号②：ABAB… 周期 2 循环 ≥min_repeats 轮（如 危机→打脸→危机→打脸→危机→打脸）。"""
    min_repeats = CYCLE_MIN_REPEATS if min_repeats is None else min_repeats
    vals = [(ch, b) for ch, b in beat_seq if b]
    n = 0
    i = 0
    while i + 2 * min_repeats <= len(vals):
        a, b = vals[i][1], vals[i + 1][1]
        if a == b:
            i += 1
            continue
        length = 0
        while (i + length < len(vals)
               and vals[i + length][1] == (a if length % 2 == 0 else b)):
            length += 1
        if length >= 2 * min_repeats:
            chapters = [ch for ch, _ in vals[i:i + length]]
            alerts.append({
                "type": "beat_cycle_repetition", "severity": "建议级", "auto": True,
                "chapter": chapters[0], "chapters": chapters,
                "note": (f"第{chapters[0]}–{chapters[-1]}章节拍呈「{a}→{b}」循环复读 "
                         f"{length // 2} 轮——套路循环是 AI 长篇的典型想象力塌陷，"
                         f"考虑引入第三种节拍或颠覆预期（{PROVENANCE}）"),
            })
            n += 1
            i += length
        else:
            i += 1
    return n


def detect_payoff_gap(payoff_seq, alerts, profile=PROFILE_COMMERCIAL):
    """信号③：连续零爽点章超铺垫上限。payoff_seq=[(章号, 命中数)]。品质向放宽且只 info。"""
    commercial = (profile == PROFILE_COMMERCIAL)
    gap_limit = PAYOFF_GAP_COMMERCIAL if commercial else PAYOFF_GAP_LITERARY
    severity = "建议级" if commercial else "info"
    n = 0
    for val, chapters in _runs([(ch, hits == 0) for ch, hits in payoff_seq]):
        if val and len(chapters) > gap_limit:
            alerts.append({
                "type": "payoff_gap", "severity": severity, "auto": True,
                "chapter": chapters[0], "chapters": chapters,
                "note": (f"第{chapters[0]}–{chapters[-1]}章连续 {len(chapters)} 章零爽点命中"
                         f"（{profile}口径：铺垫不宜超 {gap_limit} 章）——长铺垫是弃读高发区，"
                         f"插小爽点/小兑现维持期待（{PROVENANCE}·关键词初筛会漏非词表爽点）"),
            })
            n += 1
    return n


def detect_hook_type_repetition(hook_seq, alerts, run_len=None):
    """信号④：章末钩型 ≥run_len 连同型（钩子强弱归 hook_endings，这里只查单一化）。"""
    run_len = HOOK_TYPE_RUN if run_len is None else run_len
    n = 0
    for val, chapters in _runs(hook_seq):
        if val and len(chapters) >= run_len:
            alerts.append({
                "type": "hook_type_repetition", "severity": "info", "auto": True,
                "chapter": chapters[0], "chapters": chapters,
                "note": (f"第{chapters[0]}–{chapters[-1]}章章末连续 {len(chapters)} 章都用"
                         f"「{val}」——断章手法单一会让读者免疫，换型（问句/反转/危机/留白/登场）"
                         f"更保钩（{PROVENANCE}）"),
            })
            n += 1
    return n


def detect_opening_repetition(opening_seq, alerts, run_len=None):
    """信号⑤：开篇型 ≥run_len 连同型。"""
    run_len = OPENING_RUN if run_len is None else run_len
    n = 0
    for val, chapters in _runs(opening_seq):
        if val and len(chapters) >= run_len:
            alerts.append({
                "type": "opening_pattern_repetition", "severity": "info", "auto": True,
                "chapter": chapters[0], "chapters": chapters,
                "note": (f"第{chapters[0]}–{chapters[-1]}章连续 {len(chapters)} 章开篇同型"
                         f"（{val}）——开篇模板化读起来像流水线，换切入角度（{PROVENANCE}）"),
            })
            n += 1
    return n


def setback_hits(text):
    """受挫/被贬词命中数（欲扬先抑的"抑"）。纯函数·可测。词表 keyword_banks.SETBACK_KW。"""
    t = text or ""
    return sum(t.count(w) for w in SETBACK_KW)


def detect_payoff_without_suppression(seq, alerts, dense_min=None, lookback=None):
    """信号⑥：无抑之扬——爽点密集章的回溯窗口内零受挫命中。

    seq=[(章号, 爽点命中数, 受挫命中数|None)]，None=豁免章（打断窗口、不判定）。
    窗口**含本章**：打脸章内的挑衅/贬低（"废物"出口在前、反转在后）就是同章的"抑"，
    计入可大幅压误报（宁漏勿滥）。连续密集章只报窗口起点一次，避免同一段连环告警。
    """
    dense_min = PAYOFF_DENSE_MIN if dense_min is None else dense_min
    lookback = SUPPRESS_LOOKBACK if lookback is None else lookback
    n = 0
    last_flagged_idx = None
    for i, (ch, payoff, setback) in enumerate(seq):
        if setback is None or ch <= SUPPRESS_EXEMPT_CHAPTERS or payoff < dense_min:
            continue
        window = [seq[j] for j in range(max(0, i - lookback + 1), i + 1) if seq[j][2] is not None]
        if sum(s for _, _, s in window) > 0:
            continue
        if last_flagged_idx is not None and i - last_flagged_idx == 1:
            last_flagged_idx = i   # 连续密集章同属一段"无抑"，不重复告警
            continue
        last_flagged_idx = i
        chapters = [c for c, _, _ in window]
        alerts.append({
            "type": "payoff_without_suppression", "severity": "建议级", "auto": True,
            "chapter": ch, "chapters": chapters,
            "note": (f"第{ch}章爽点密集（命中 {payoff}）但第{chapters[0]}–{chapters[-1]}章窗口内"
                     f"零受挫/贬低命中——欲扬先抑：没有'抑'垫势能的爽点是打空气（打脸三拍：反派"
                     f"抬高→主角受压→反转），先垫憋屈值再兑现（{PROVENANCE}·词表初筛会漏非词表的抑）"),
        })
        n += 1
    return n


def _load_profile(project):
    """读 _设置.md 的目标平台 → 商业爽文向/品质向。读不到按商业向（网文默认密尺）。"""
    try:
        from project_io import load_project_settings
        settings = load_project_settings(project) or {}
    except Exception:
        settings = {}
    return classify_platform(settings.get("目标平台")), settings


def analyze(project):
    """逐章抽节拍/爽点/钩型/开篇型序列，跑五个多样性信号。返回 novel-review 检测器契约：
    {ran, alerts, beats, total, blocking(=0)}；无章节优雅跳过（ran=False），不臆造。"""
    chapters = list(list_chapters(project))
    if not chapters:
        return {"ran": False, "skipped": "无章节——先有正文再查情节多样性"}

    profile, settings = _load_profile(project)
    payoff_bank = payoff_bank_for(str(settings.get("题材") or ""), str(settings.get("目标平台") or ""))

    beat_seq, payoff_seq, hook_seq, opening_seq, suppress_seq, per_chapter = [], [], [], [], [], []
    for cid, path, text in chapters:
        if is_exempt(path):
            # 豁免章打断 run（用 None 段隔开），不参与任何判定
            beat_seq.append((cid, None))
            payoff_seq.append((cid, 1))
            hook_seq.append((cid, None))
            opening_seq.append((cid, None))
            suppress_seq.append((cid, 0, None))
            per_chapter.append({"chapter": cid, "exempt": True})
            continue
        beat = dominant_beat(text)
        payoff_hits = sum((text or "").count(w) for w in payoff_bank)
        sb_hits = setback_hits(text)
        htype = hook_type(text)
        otype = opening_type(text)
        beat_seq.append((cid, beat))
        payoff_seq.append((cid, payoff_hits))
        hook_seq.append((cid, htype))
        opening_seq.append((cid, otype))
        suppress_seq.append((cid, payoff_hits, sb_hits))
        per_chapter.append({"chapter": cid, "dominant_beat": beat, "payoff_hits": payoff_hits,
                            "setback_hits": sb_hits, "hook_type": htype, "opening_type": otype})

    alerts = []
    detect_beat_monotony(beat_seq, alerts)
    detect_beat_cycle(beat_seq, alerts)
    detect_payoff_gap(payoff_seq, alerts, profile=profile)
    detect_hook_type_repetition(hook_seq, alerts)
    detect_opening_repetition(opening_seq, alerts)
    detect_payoff_without_suppression(suppress_seq, alerts)

    return {
        "ran": True,
        "profile": profile,
        "thresholds": {
            "beat_min_hits": BEAT_MIN_HITS, "monotony_run": MONOTONY_RUN,
            "cycle_min_repeats": CYCLE_MIN_REPEATS,
            "payoff_gap": PAYOFF_GAP_COMMERCIAL if profile == PROFILE_COMMERCIAL else PAYOFF_GAP_LITERARY,
            "hook_type_run": HOOK_TYPE_RUN, "opening_run": OPENING_RUN,
            "payoff_dense_min": PAYOFF_DENSE_MIN, "suppress_lookback": SUPPRESS_LOOKBACK,
            "provenance": PROVENANCE,
            "note": "advisory：本检永不阻断；番外/楔子/序章等豁免章打断 run 不计入。",
        },
        "beats": per_chapter,
        "alerts": alerts,
        "total": len(alerts),
        "blocking": 0,  # advisory 纪律：恒 0，不是「这次刚好没有」
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="情节节拍多样性/桥段复读 机检（advisory）")
    ap.add_argument("project_path")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    res = analyze(args.project_path)
    if res.get("ran"):
        out = os.path.join(args.project_path, "审稿", "plot_variety_findings.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    else:
        out = None

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    if not res.get("ran"):
        print("ℹ️ " + res.get("skipped", "skipped"))
        return 0
    icon = "⚠️" if res["total"] else "✅"
    print(f"{icon} 情节多样性机检：{len(res['beats'])} 章，{res['total']} 条多样性提示 → {out}")
    for a in res["alerts"]:
        print(f"  - [{a['severity']}] {a['type']}: {a['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
