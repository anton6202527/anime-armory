#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""behavioral_signals.py — 行为式读者模拟的确定性度量层（advisory·纯标准库）。

为什么：传统"扮演读者发感想"的模拟只能产主观定性；2024-2026 研究给了**行为式**替代
（arXiv 2412.15239 想象续写预测 engagement；arXiv 2604.09854 Spoiler Alert：以结局预测
偏离率量化张力——目前唯一能把人类小说正确排在 LLM 产出之上的自动指标，抓的是评分模型
抓不到的"可预测性"维度）。协议：AI 读者面板在章末各写一条"下一章会发生什么"的短预测
（10-20 条），本脚本对已收集的预测做两个确定性度量：

  悬念值 guess_diversity  预测两两 char-2gram 相异度均值——读者猜的方向越散，悬念越足；
                          全员猜同一个方向 = 悬念塌缩（只剩一条明线）。
  意外度 surprise         1 - 预测与**真实下一章**的最大相似度——真实剧情离最像的预测
                          越远越"想不到"；意外度过低 = 剧情太顺/可预测（套路化预警）。

输入（面板产出·LLM 按 SKILL 协议落盘）：`评分/reader_predictions_第NN章.json`
    {"schema_version":1, "kind":"novel_reader_predictions", "chapter":NN,
     "predictions":[{"persona":"rookie","text":"主角会当场反杀"}, …]}

口径纪律：相似度是字面 2-gram 近似（confidence=heuristic）——换词同义预测会高估意外度，
所以**只报低分候选**（明显猜中/明显同向），不认证"高分=真悬念"；advisory 恒不阻断。

2026-07 增补：beta reader 标准问卷聚合（业界六问，Jane Friedman/FoxPrint 口径）。
面板按 SKILL 协议落盘 `评分/reader_survey_第NN章.json`（bored/confused/disbelief/
favorite/annoying/recall），本脚本做确定性聚合：
  reader_bored_run        连续 ≥N 章过半读者报 bored → 弃书风险段（带 span 供修订工单定位）
  reader_confusion_spike  单章过半读者报 confused → 信息管理事故（该露的没露/时序乱）
  reader_disbelief        任一读者报 disbelief 且点名人物 → OOC 候选（与一致性审计互补）
  recall_failure          recall 复述对上一章正文的 2-gram 包含度过半读者低于阈值 →
                          该章信息未留存（写了但没进读者脑子）。recall 是读者自己的话，
                          换词会压低包含度——阈值放宽、只报过半共识，单人低分不报。

用法：
    python3 behavioral_signals.py <作品根> [--json]
测试：cd skills/novel-simulate/scripts && python3 -m pytest test_behavioral_signals.py
"""
import argparse
import glob
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_WIKI = os.path.abspath(os.path.join(_HERE, "..", "..", "novel-wiki", "scripts"))
if _WIKI not in sys.path:
    sys.path.insert(0, _WIKI)
try:
    from wiki_builder import list_chapters
except Exception:
    def list_chapters(project, *a, **k):  # type: ignore
        return []

PREDICTIONS_GLOB = os.path.join("评分", "reader_predictions_第*章.json")
SURVEY_GLOB = os.path.join("评分", "reader_survey_第*章.json")
MIN_PREDICTIONS = int(os.environ.get("NOVEL_BEHAV_MIN_PREDICTIONS", "5"))
SURPRISE_WARN = float(os.environ.get("NOVEL_BEHAV_SURPRISE_WARN", "0.35"))
DIVERSITY_WARN = float(os.environ.get("NOVEL_BEHAV_DIVERSITY_WARN", "0.55"))  # 短中文预测 2-gram 相异度天然偏高，换措辞同向约 0.4-0.55
ACTUAL_HEAD_CHARS = int(os.environ.get("NOVEL_BEHAV_ACTUAL_HEAD", "1200"))
BORED_RUN = int(os.environ.get("NOVEL_BEHAV_BORED_RUN", "2"))          # 连续多少章过半 bored 才报
MAJORITY = float(os.environ.get("NOVEL_BEHAV_MAJORITY", "0.5"))        # "过半"口径（含端点）
RECALL_MIN = float(os.environ.get("NOVEL_BEHAV_RECALL_MIN", "0.25"))   # recall 对上一章 2-gram 包含度下限
MIN_SURVEY_RESPONSES = int(os.environ.get("NOVEL_BEHAV_MIN_SURVEY", "2"))  # 过半类信号最少答卷数
NGRAM = 2
PROVENANCE = "internal-heuristic·confidence=low"

_NOISE_RE = re.compile(r"[\s，。！？、；：…—\-\|,.!?;:\"'“”‘’()（）\[\]【】《》]+")


def clean(text):
    return _NOISE_RE.sub("", str(text or ""))


def shingles(text, n=NGRAM):
    c = clean(text)
    if len(c) < n:
        return {c} if c else set()
    return {c[i:i + n] for i in range(len(c) - n + 1)}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter) if inter else 0.0


def guess_diversity(predictions):
    """预测两两相异度（1-Jaccard）均值 ∈ [0,1]，越高悬念越足。<2 条返回 None。纯函数。"""
    sets = [shingles(p) for p in predictions if clean(p)]
    if len(sets) < 2:
        return None
    total, pairs = 0.0, 0
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            total += 1.0 - jaccard(sets[i], sets[j])
            pairs += 1
    return round(total / pairs, 3) if pairs else None


def surprise_score(predictions, actual_text):
    """1 - max(预测对真实下一章开头的**包含度**) ∈ [0,1]，越高越"想不到"。纯函数。

    用包含度（inter/|预测 shingles|）而非对称 Jaccard：真实章远长于一条短预测，
    对称 Jaccard 会被长度稀释——预测哪怕逐字命中也只有 |pred|/|actual| 的上限，
    "猜中了"永远测不出来。包含度问的是"这条预测有多少被真实剧情覆盖"，与长度无关。"""
    actual = shingles(str(actual_text or "")[:ACTUAL_HEAD_CHARS])
    if not actual:
        return None
    sims = []
    for p in predictions:
        ps = shingles(p)
        if ps:
            sims.append(len(ps & actual) / len(ps))
    if not sims:
        return None
    return round(1.0 - max(sims), 3)


def _pred_texts(payload):
    out = []
    for p in payload.get("predictions") or []:
        if isinstance(p, dict):
            t = str(p.get("text") or "").strip()
        else:
            t = str(p or "").strip()
        if t:
            out.append(t)
    return out


def recall_containment(recall_text, prev_text):
    """recall 复述对上一章正文的 2-gram 包含度 ∈ [0,1]；任一侧为空返回 None。纯函数。

    与 surprise_score 同理用包含度而非对称 Jaccard：复述远短于整章正文，问的是
    "复述里有多少内容真出现在上一章"——专名与关键动作会命中，纯编造/张冠李戴命不中。"""
    rs = shingles(recall_text)
    prev = shingles(str(prev_text or ""))
    if not rs or not prev:
        return None
    return round(len(rs & prev) / len(rs), 3)


def _field_span(value):
    """问卷答案归一：dict 取 span/note、字符串原样、空值→None。返回定位用短文本或 None。"""
    if isinstance(value, dict):
        t = str(value.get("span") or value.get("note") or "").strip()
        return t or None
    t = str(value or "").strip()
    return t or None


def _survey_responses(payload):
    """归一 responses：[{persona, bored, confused, disbelief, disbelief_characters, recall}]。"""
    out = []
    for r in payload.get("responses") or []:
        if not isinstance(r, dict):
            continue
        dis = r.get("disbelief")
        chars = []
        if isinstance(dis, dict):
            chars = [str(c).strip() for c in (dis.get("characters") or []) if str(c).strip()]
        out.append({
            "persona": str(r.get("persona") or "").strip() or "unknown",
            "bored": _field_span(r.get("bored")),
            "confused": _field_span(r.get("confused")),
            "disbelief": _field_span(dis),
            "disbelief_characters": chars,
            "recall": str(r.get("recall") or "").strip(),
        })
    return out


def _majority(count, total):
    return total >= MIN_SURVEY_RESPONSES and count / total >= MAJORITY


def _analyze_surveys(project, chapters):
    """聚合问卷文件 → (survey_rows, alerts)。文件缺失/坏 JSON/旧 schema 一律跳过。"""
    alerts, rows = [], []
    bored_by_ch = {}   # ch -> {"spans": […], "flagged": bool}
    for path in sorted(glob.glob(os.path.join(project, SURVEY_GLOB))):
        try:
            with open(path, encoding="utf-8") as f:
                payload = json.load(f)
        except (OSError, ValueError):
            continue
        try:
            ch = int(payload.get("chapter"))
        except (TypeError, ValueError):
            continue
        resp = _survey_responses(payload)
        if not resp:
            continue
        n = len(resp)
        bored = [r for r in resp if r["bored"]]
        confused = [r for r in resp if r["confused"]]
        disbelief = [r for r in resp if r["disbelief"] and r["disbelief_characters"]]
        recalls = [(r["persona"], recall_containment(r["recall"], chapters.get(ch - 1)))
                   for r in resp if r["recall"]]
        recalls = [(p, c) for p, c in recalls if c is not None]
        low_recall = [(p, c) for p, c in recalls if c < RECALL_MIN]
        row = {"chapter": ch, "responses": n, "bored": len(bored), "confused": len(confused),
               "disbelief": len(disbelief),
               "recall_containment": {p: c for p, c in recalls} or None}
        rows.append(row)
        bored_by_ch[ch] = {"spans": [r["bored"] for r in bored][:3],
                           "flagged": _majority(len(bored), n)}
        if _majority(len(confused), n):
            spans = "；".join(f"{r['persona']}「{r['confused']}」" for r in confused[:3])
            alerts.append({
                "type": "reader_confusion_spike", "severity": "建议级", "auto": True, "chapter": ch,
                "note": (f"第{ch}章 {len(confused)}/{n} 名模拟读者困惑到需要回读（{spans}）——"
                         f"信息管理事故候选：该露的没露/时序乱/指代不清，对照知情面与章间承接检查"
                         f"（{PROVENANCE}）"),
            })
        for r in disbelief:
            alerts.append({
                "type": "reader_disbelief", "severity": "建议级", "auto": True, "chapter": ch,
                "characters": r["disbelief_characters"],
                "note": (f"第{ch}章读者({r['persona']})对 {'、'.join(r['disbelief_characters'])} "
                         f"不再相信：「{r['disbelief']}」——OOC/强行剧情候选，与一致性审计互补"
                         f"（{PROVENANCE}）"),
            })
        if recalls and _majority(len(low_recall), len(recalls)) and (ch - 1) in chapters:
            detail = "、".join(f"{p}={c:.0%}" for p, c in low_recall[:4])
            alerts.append({
                "type": "recall_failure", "severity": "建议级", "auto": True, "chapter": ch - 1,
                "note": (f"第{ch - 1}章信息未留存：过半读者凭记忆复述该章时与正文包含度低于 "
                         f"{RECALL_MIN:.0%}（{detail}）——事件密度过高或全程平铺都会让读者"
                         f"『读了但没记住』，考虑压缩支线信息或给关键事件加落点"
                         f"（{PROVENANCE}·复述是读者自己的话，换词会压低分数，只报过半共识）"),
            })
    # bored 连续段：章号断档清零（同 hook_endings 序列口径）
    run = []
    for ch in sorted(bored_by_ch):
        if bored_by_ch[ch]["flagged"] and (not run or ch == run[-1] + 1):
            run.append(ch)
            continue
        if len(run) >= BORED_RUN:
            _emit_bored_run(alerts, run, bored_by_ch)
        run = [ch] if bored_by_ch[ch]["flagged"] else []
    if len(run) >= BORED_RUN:
        _emit_bored_run(alerts, run, bored_by_ch)
    return rows, alerts


def _emit_bored_run(alerts, run, bored_by_ch):
    spans = "；".join(s for ch in run for s in bored_by_ch[ch]["spans"][:1])
    alerts.append({
        "type": "reader_bored_run", "severity": "建议级", "auto": True,
        "chapters": list(run),
        "note": (f"第{run[0]}-{run[-1]}章连续 {len(run)} 章过半模拟读者报『想放下』"
                 f"（走神点：{spans or '未定位'}）——弃书风险段，按 span 定位到场景级修订工单"
                 f"（{PROVENANCE}）"),
    })


def analyze(project):
    """扫预测+问卷文件，算悬念/意外度并聚合六问 advisory。{ran, alerts, chapters, blocking(=0)}。"""
    paths = sorted(glob.glob(os.path.join(project, PREDICTIONS_GLOB)))
    has_survey = bool(glob.glob(os.path.join(project, SURVEY_GLOB)))
    if not paths and not has_survey:
        return {"ran": False,
                "skipped": ("无 评分/reader_predictions_第NN章.json 或 reader_survey_第NN章.json——"
                            "行为式协议：AI 读者面板在章末写『下一章会发生什么』短预测（≥5 条）"
                            "与六问问卷落盘后再跑本度量")}
    chapters = {cid: text for cid, _p, text in list_chapters(project)}
    alerts, rows = [], []
    for path in paths:
        try:
            with open(path, encoding="utf-8") as f:
                payload = json.load(f)
        except (OSError, ValueError):
            continue
        ch = payload.get("chapter")
        try:
            ch = int(ch)
        except (TypeError, ValueError):
            continue
        preds = _pred_texts(payload)
        row = {"chapter": ch, "predictions": len(preds)}
        if len(preds) < MIN_PREDICTIONS:
            row["insufficient"] = True
            rows.append(row)
            continue
        div = guess_diversity(preds)
        sup = surprise_score(preds, chapters.get(ch + 1))
        row.update({"guess_diversity": div, "surprise": sup,
                    "next_chapter_available": (ch + 1) in chapters})
        rows.append(row)
        if div is not None and div < DIVERSITY_WARN:
            alerts.append({
                "type": "suspense_collapse", "severity": "建议级", "auto": True, "chapter": ch,
                "note": (f"第{ch}章末读者预测同质度过高（发散度 {div:.0%} < {DIVERSITY_WARN:.0%}）——"
                         f"全员只猜到一个方向，说明只剩一条明线在走；埋第二悬念线或制造歧义"
                         f"（{PROVENANCE}）"),
            })
        if sup is not None and sup < SURPRISE_WARN:
            alerts.append({
                "type": "predictable_plot", "severity": "建议级", "auto": True, "chapter": ch + 1,
                "note": (f"第{ch + 1}章走向被章末预测猜中（意外度 {sup:.0%} < {SURPRISE_WARN:.0%}）——"
                         f"剧情太顺=套路化预警；老读者能预测的展开考虑做一次预期颠覆"
                         f"（{PROVENANCE}·字面近似，换词猜中会漏）"),
            })
    survey_rows, survey_alerts = _analyze_surveys(project, chapters)
    alerts.extend(survey_alerts)
    return {
        "ran": True,
        "thresholds": {"min_predictions": MIN_PREDICTIONS, "surprise_warn": SURPRISE_WARN,
                       "diversity_warn": DIVERSITY_WARN, "ngram": NGRAM,
                       "bored_run": BORED_RUN, "majority": MAJORITY, "recall_min": RECALL_MIN,
                       "min_survey_responses": MIN_SURVEY_RESPONSES, "provenance": PROVENANCE,
                       "note": "advisory：只报低分候选，不认证高分=真悬念；恒不阻断。"},
        "chapters": rows,
        "survey_chapters": survey_rows,
        "alerts": alerts,
        "total": len(alerts),
        "blocking": 0,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="行为式读者模拟确定性度量（advisory）")
    ap.add_argument("project_path")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    res = analyze(args.project_path)
    if res.get("ran"):
        out = os.path.join(args.project_path, "评分", "behavioral_signals.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    if not res.get("ran"):
        print("ℹ️ " + res.get("skipped", "skipped"))
        return 0
    icon = "⚠️" if res["total"] else "✅"
    print(f"{icon} 行为式读者度量：{len(res['chapters'])} 个章末预测点，"
          f"{len(res.get('survey_chapters') or [])} 个问卷点，{res['total']} 条提示")
    for a in res["alerts"]:
        print(f"  - [{a['severity']}] {a['type']}: {a['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
