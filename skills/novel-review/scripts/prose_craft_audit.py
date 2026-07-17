#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prose_craft_audit.py — 传统行文手艺 + 篇章级叙事指纹 机检（advisory·纯标准库）。

两组信号，都源自**传统小说改稿工艺**与实证研究，全部 advisory（行文好坏终归人判）：

【A. 传统 line-edit 手艺】编辑改稿时最先划掉的三类：
  ① filter_words       过滤词（看到/听到/感到/注意到/意识到…）——把读者隔在 POV 感官
                        之外的"滤镜"，show-don't-tell 的行文层。经典改法：删滤镜直写感知。
  ② adverb_dialogue_tag 副词对话标签（"冷冷地说道"）——Elmore Leonard 手艺：情绪该由
                        台词内容和动作节拍（beat）承载，副词标签是偷懒。
  ③ dialogue_balance    对话占比失衡——传统 scene/summary 节奏手艺：整章全对话（广播剧）
                        或整章零对话（论文）都是节奏红旗。
  ④ info_dump_opening   开篇设定倾倒——"第一章别倒设定"是网文与传统共识：前三章出现
                        长段无对话无动作的设定解释块=劝退高发。

【B. StoryScope 篇章指纹】（arXiv 2604.03136，61,608 篇人类 vs 5 家 LLM 实测；
  词库单一真值源 novel/_lib/keyword_banks.py——此前六桶词库**零消费者**，建了没人用）：
  ⑤ moralizing_ending   叙述者点破主题（AI 77% vs 人类 52%）——章末"他终于明白…"式
                        点题句；传统手艺：主题由事件承载，不由旁白宣讲。
  ⑥ emotion_translation 情绪全靠身体演（AI 81% 生理化 vs 人类 38%；人类反而更常直写
                        "他很害怕" 29% vs AI 8%）——label/physio 比例失衡是 AI 指纹。
  ⑦ smell_overuse       嗅觉意象滥用（AI 82% vs 人类 57%）——美食/医疗/刑侦题材豁免。
  ⑧ setting_mirror      景物映衬内心滥用（"天色暗下来，正如他的心情"）。
  ⑨ philo_dialogue      对白服务哲学思辨（AI 59% vs 人类 34%）——商业爽文档更严。

口径纪律：论文比例是英文短篇语料的**方向**不是中文网文阈值——本模块阈值全部
internal-heuristic、env 可标定、恒 advisory；burstiness/重复率等风格侧归 mechanical_check，
本模块只管**篇章/手艺侧**（改写后判别力 93% vs 风格侧 3%，见 keyword_banks 注释）。

用法：
    python3 prose_craft_audit.py <作品根> [--json]
测试：cd skills/novel-review/scripts && python3 -m pytest test_prose_craft_audit.py
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
except Exception:
    def list_chapters(project, *a, **k):  # type: ignore
        return []
try:
    from keyword_banks import (MORALIZING_PATTERNS, EMOTION_LABEL_KW, PHYSIO_BODY_KW,
                               PHYSIO_REACTION_KW, SMELL_KW, SETTING_MIRROR_KW,
                               PHILO_DIALOGUE_KW, LOGIC_KW, classify_platform,
                               PROFILE_COMMERCIAL)
except Exception:
    MORALIZING_PATTERNS = EMOTION_LABEL_KW = PHYSIO_BODY_KW = []
    PHYSIO_REACTION_KW = SMELL_KW = SETTING_MIRROR_KW = PHILO_DIALOGUE_KW = LOGIC_KW = []
    def classify_platform(p):  # type: ignore
        return "商业爽文向"
    PROFILE_COMMERCIAL = "商业爽文向"

# ── 阈值（internal-heuristic·env 可标定·全 advisory）─────────────────────────
FILTER_PER_K = float(os.environ.get("NOVEL_PROSE_FILTER_PER_K", "6"))       # 过滤词/千字
ADV_TAG_PER_K = float(os.environ.get("NOVEL_PROSE_ADVTAG_PER_K", "1.5"))    # 副词标签/千字
DIALOGUE_HI = float(os.environ.get("NOVEL_PROSE_DIALOGUE_HI", "0.75"))      # 对话行占比上限
DIALOGUE_LO = float(os.environ.get("NOVEL_PROSE_DIALOGUE_LO", "0.05"))      # 下限
DIALOGUE_MIN_LINES = int(os.environ.get("NOVEL_PROSE_DIALOGUE_MIN_LINES", "20"))
DUMP_PARA_CHARS = int(os.environ.get("NOVEL_PROSE_DUMP_PARA_CHARS", "180"))  # 设定块最短长度
DUMP_LOGIC_PER_K = float(os.environ.get("NOVEL_PROSE_DUMP_LOGIC_PER_K", "18"))  # 块内设定词/千字
DUMP_OPENING_CHAPTERS = int(os.environ.get("NOVEL_PROSE_DUMP_CHAPTERS", "3"))
DUMP_WARN_PARAS = int(os.environ.get("NOVEL_PROSE_DUMP_WARN_PARAS", "2"))
MORALIZE_TAIL_CHARS = 200
MORALIZE_PER_CHAPTER = float(os.environ.get("NOVEL_PROSE_MORALIZE_PER_CH", "0.5"))  # 章均点题句
PHYSIO_RATIO_WARN = float(os.environ.get("NOVEL_PROSE_PHYSIO_RATIO", "0.9"))  # physio/(label+physio)
PHYSIO_MIN_TOTAL = int(os.environ.get("NOVEL_PROSE_PHYSIO_MIN_TOTAL", "30"))
SMELL_PER_K = float(os.environ.get("NOVEL_PROSE_SMELL_PER_K", "1.2"))
MIRROR_PER_K = float(os.environ.get("NOVEL_PROSE_MIRROR_PER_K", "1.0"))
PHILO_PER_K_COMMERCIAL = float(os.environ.get("NOVEL_PROSE_PHILO_PER_K", "0.8"))
PHILO_PER_K_LITERARY = float(os.environ.get("NOVEL_PROSE_PHILO_PER_K_LIT", "2.0"))
PROVENANCE = "internal-heuristic·confidence=low"

# 过滤词（filter words）：POV 角色与感知之间的"滤镜"。只算**叙述行**（引号外），
# 对话里人物自述"我看到…"是台词内容不是滤镜。
FILTER_WORDS = ("看到", "看见", "听到", "听见", "闻到", "感到", "感觉到", "觉得",
                "注意到", "意识到", "发现", "发觉", "心想", "心道", "暗想")
# 副词对话标签："XX地说/道/说道/问道/答道…"——情绪塞进标签而非台词与动作。
_ADV_TAG_RE = re.compile(r"[一-鿿]{1,4}地(?:说道|说|道|问道|问|答道|回道|喊道|叫道|开口)")
# 对话行：以引号开头（含前置人名短语）。
_DIALOGUE_LINE_RE = re.compile(r"^[^「“\"『]{0,12}[「“\"『]")
# 题材豁免（嗅觉刚需）：美食/医疗/刑侦/探案。
_SMELL_EXEMPT_RE = re.compile(r"美食|厨|医|刑侦|探案|缉|法医|悬疑")
_EXEMPT_TITLE_RE = re.compile(r"番外|楔子|序章|回顾|尾声|后记|人物志|设定集")


def _per_k(count, chars):
    return count * 1000.0 / chars if chars else 0.0


def split_narration_dialogue(text):
    """按行拆（叙述行, 对话行）。纯函数·可测。"""
    narration, dialogue = [], []
    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        (dialogue if _DIALOGUE_LINE_RE.match(s) else narration).append(s)
    return narration, dialogue


def filter_word_count(narration_lines):
    """叙述行内过滤词出现次数。纯函数。"""
    text = "\n".join(narration_lines)
    return sum(text.count(w) for w in FILTER_WORDS)


def adverb_tag_count(text):
    return len(_ADV_TAG_RE.findall(text or ""))


def dialogue_ratio(narration, dialogue):
    total = len(narration) + len(dialogue)
    return (len(dialogue) / total if total else 0.0), total


def moralizing_hits(text, tail_chars=MORALIZE_TAIL_CHARS):
    """点题句命中（章末段加权：末 tail_chars 内命中计 2，其余计 1）。纯函数。"""
    t = text or ""
    tail = t[-tail_chars:]
    head = t[:-tail_chars] if len(t) > tail_chars else ""
    score = 0
    for p in MORALIZING_PATTERNS:
        score += head.count(p) + 2 * tail.count(p)
    return score


def physio_cooccur_count(text):
    """生理化情绪：部位词 + 生理动词**同句共现**才算（避免打斗场景字面误计）。纯函数。"""
    n = 0
    for sent in re.split(r"[。！？!?\n]", text or ""):
        if any(b in sent for b in PHYSIO_BODY_KW) and any(r in sent for r in PHYSIO_REACTION_KW):
            n += 1
    return n


def emotion_label_count(text):
    t = text or ""
    return sum(t.count(w) for w in EMOTION_LABEL_KW)


def setting_mirror_count(text):
    """景物词与情绪词同句共现 = 映衬。纯函数。"""
    n = 0
    emo = list(EMOTION_LABEL_KW) + ["心情", "心境", "心底", "心头"]
    for sent in re.split(r"[。！？!?\n]", text or ""):
        if any(s in sent for s in SETTING_MIRROR_KW) and any(e in sent for e in emo):
            n += 1
    return n


def philo_dialogue_count(dialogue_lines):
    text = "\n".join(dialogue_lines)
    return sum(text.count(w) for w in PHILO_DIALOGUE_KW)


def info_dump_paragraphs(text):
    """疑似设定倾倒段：≥DUMP_PARA_CHARS 字、无引号（无对话）、设定/解释词密度高。纯函数。"""
    hits = []
    for para in re.split(r"\n\s*\n|\n", text or ""):
        p = para.strip()
        if len(p) < DUMP_PARA_CHARS:
            continue
        if re.search(r"[「“\"『]", p):
            continue
        logic_n = sum(p.count(w) for w in LOGIC_KW)
        if _per_k(logic_n, len(p)) >= DUMP_LOGIC_PER_K:
            hits.append(p[:30])
    return hits


def _load_settings(project):
    try:
        from project_io import load_project_settings
        return load_project_settings(project) or {}
    except Exception:
        return {}


def analyze(project):
    """novel-review 检测器契约：{ran, alerts, chapters, total, blocking(=0)}。"""
    chapters = [(cid, path, text) for cid, path, text in list_chapters(project)
                if not _EXEMPT_TITLE_RE.search(os.path.basename(str(path or "")))]
    if not chapters:
        return {"ran": False, "skipped": "无章节——先有正文再查行文手艺"}
    settings = _load_settings(project)
    profile = classify_platform(settings.get("目标平台"))
    genre_blob = " ".join(str(settings.get(k) or "") for k in ("题材", "小说用途", "目标平台"))
    smell_exempt = bool(_SMELL_EXEMPT_RE.search(genre_blob))
    philo_limit = PHILO_PER_K_COMMERCIAL if profile == PROFILE_COMMERCIAL else PHILO_PER_K_LITERARY

    alerts, rows = [], []
    tot_chars = tot_label = tot_physio = tot_smell = tot_mirror = tot_moralize = 0
    for cid, _path, text in chapters:
        text = text or ""
        chars = len(text)
        narration, dialogue = split_narration_dialogue(text)
        fw = filter_word_count(narration)
        at = adverb_tag_count(text)
        dr, lines = dialogue_ratio(narration, dialogue)
        row = {"chapter": cid, "chars": chars,
               "filter_per_k": round(_per_k(fw, chars), 2),
               "adv_tag_per_k": round(_per_k(at, chars), 2),
               "dialogue_ratio": round(dr, 2)}
        rows.append(row)

        if chars and _per_k(fw, chars) > FILTER_PER_K:
            alerts.append({"type": "filter_words", "severity": "建议级", "auto": True, "chapter": cid,
                           "note": (f"第{cid}章过滤词 {_per_k(fw, chars):.1f}/千字（阈 {FILTER_PER_K:g}）——"
                                    f"『他看到/感到/注意到 X』把读者隔在滤镜外；传统改法：删滤镜直写感知"
                                    f"（『他看到刀光一闪』→『刀光一闪』）（{PROVENANCE}）")})
        if chars and _per_k(at, chars) > ADV_TAG_PER_K:
            alerts.append({"type": "adverb_dialogue_tag", "severity": "建议级", "auto": True, "chapter": cid,
                           "note": (f"第{cid}章副词对话标签 {_per_k(at, chars):.1f}/千字（阈 {ADV_TAG_PER_K:g}）——"
                                    f"『冷冷地说道』式标签是把情绪塞进说明而非台词；传统手艺：情绪由台词内容"
                                    f"和动作节拍（beat）承载，标签只留最朴素的『说/道』（{PROVENANCE}）")})
        if lines >= DIALOGUE_MIN_LINES:
            if dr > DIALOGUE_HI:
                alerts.append({"type": "dialogue_balance", "severity": "info", "auto": True, "chapter": cid,
                               "note": (f"第{cid}章对话行占比 {dr:.0%}（>{DIALOGUE_HI:.0%}）——整章近似广播剧，"
                                        f"缺场景锚定与动作节拍；穿插叙述/动作换气（{PROVENANCE}）")})
            elif dr < DIALOGUE_LO:
                alerts.append({"type": "dialogue_balance", "severity": "info", "auto": True, "chapter": cid,
                               "note": (f"第{cid}章对话行占比 {dr:.0%}（<{DIALOGUE_LO:.0%}）——整章近乎纯叙述，"
                                        f"节奏易闷；考虑把关键信息改由对话/冲突呈现（{PROVENANCE}）")})
        if cid <= DUMP_OPENING_CHAPTERS:
            dumps = info_dump_paragraphs(text)
            if len(dumps) >= DUMP_WARN_PARAS:
                alerts.append({"type": "info_dump_opening", "severity": "建议级", "auto": True, "chapter": cid,
                               "evidence": "；".join(dumps[:2]),
                               "note": (f"第{cid}章有 {len(dumps)} 个疑似设定倾倒段（长段无对话且设定/解释词"
                                        f"密集）——开篇倒设定是劝退高发；传统手艺：设定拆进冲突现场按需露出，"
                                        f"『读者需要时才给，给时藏在事件里』（{PROVENANCE}）")})

        tot_chars += chars
        tot_label += emotion_label_count(text)
        tot_physio += physio_cooccur_count(text)
        tot_smell += sum(text.count(w) for w in SMELL_KW)
        tot_mirror += setting_mirror_count(text)
        tot_moralize += moralizing_hits(text)
        ph = philo_dialogue_count(dialogue)
        if chars and _per_k(ph, chars) > philo_limit:
            alerts.append({"type": "philo_dialogue", "severity": "info", "auto": True, "chapter": cid,
                           "note": (f"第{cid}章对白哲理词 {_per_k(ph, chars):.1f}/千字（{profile}阈 {philo_limit:g}）——"
                                    f"角色在对话里辩论人生意义是 AI 指纹（59% vs 人类 34%），网文读者尤其无感；"
                                    f"思辨改由处境与选择呈现（{PROVENANCE}）")})

    # ── 全书级指纹（单章样本太小，只在全书聚合层判）─────────────────────────
    n_ch = len(chapters)
    if n_ch and tot_moralize / n_ch > MORALIZE_PER_CHAPTER:
        alerts.append({"type": "moralizing_ending", "severity": "建议级", "auto": True,
                       "note": (f"全书点题句密度 {tot_moralize / n_ch:.1f}/章（阈 {MORALIZE_PER_CHAPTER:g}·章末加权）——"
                                f"『他终于明白，XX才是YY』式旁白宣讲主题是 AI 惯性（77% vs 人类 52%）；"
                                f"传统手艺：主题由事件与代价承载，讲出来就轻了（{PROVENANCE}）")})
    emo_total = tot_label + tot_physio
    if emo_total >= PHYSIO_MIN_TOTAL and tot_physio / emo_total > PHYSIO_RATIO_WARN:
        alerts.append({"type": "emotion_translation", "severity": "info", "auto": True,
                       "note": (f"全书情绪表达 {tot_physio}/{emo_total} 走生理化（>{PHYSIO_RATIO_WARN:.0%}）——"
                                f"『心脏一紧/指尖发凉』全书复读是 AI 指纹（81% vs 人类 38%；人类反而更敢"
                                f"直写『他很害怕』）；混用直陈、动作与留白（{PROVENANCE}）")})
    if tot_chars and not smell_exempt and _per_k(tot_smell, tot_chars) > SMELL_PER_K:
        alerts.append({"type": "smell_overuse", "severity": "info", "auto": True,
                       "note": (f"全书嗅觉意象 {_per_k(tot_smell, tot_chars):.1f}/千字（阈 {SMELL_PER_K:g}）——"
                                f"AI 爱写气味（82% vs 人类 57%）；非美食/医疗/刑侦题材建议稀释（{PROVENANCE}）")})
    if tot_chars and _per_k(tot_mirror, tot_chars) > MIRROR_PER_K:
        alerts.append({"type": "setting_mirror", "severity": "info", "auto": True,
                       "note": (f"全书景物映衬内心 {_per_k(tot_mirror, tot_chars):.1f}/千字（阈 {MIRROR_PER_K:g}）——"
                                f"『天色暗下来，正如他的心情』用多即腻；让景物偶尔与情绪**相反**更高级"
                                f"（{PROVENANCE}）")})

    return {
        "ran": True,
        "profile": profile,
        "thresholds": {"filter_per_k": FILTER_PER_K, "adv_tag_per_k": ADV_TAG_PER_K,
                       "dialogue_hi": DIALOGUE_HI, "dialogue_lo": DIALOGUE_LO,
                       "moralize_per_chapter": MORALIZE_PER_CHAPTER,
                       "physio_ratio_warn": PHYSIO_RATIO_WARN, "smell_per_k": SMELL_PER_K,
                       "mirror_per_k": MIRROR_PER_K, "philo_per_k": philo_limit,
                       "smell_exempt": smell_exempt, "provenance": PROVENANCE,
                       "note": "advisory：StoryScope 比例是英文短篇的方向非中文阈值；恒不阻断。"},
        "chapters": rows,
        "alerts": alerts,
        "total": len(alerts),
        "blocking": 0,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="传统行文手艺 + 篇章叙事指纹 机检（advisory）")
    ap.add_argument("project_path")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    res = analyze(args.project_path)
    if res.get("ran"):
        out = os.path.join(args.project_path, "审稿", "prose_craft_findings.json")
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
    print(f"{icon} 行文手艺机检：{len(res['chapters'])} 章，{res['total']} 条提示")
    for a in res["alerts"]:
        print(f"  - [{a['severity']}] {a['type']}: {a['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
