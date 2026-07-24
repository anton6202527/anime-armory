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

【C. 句子节奏与视角纪律】（2026-07 第三轮补，同样全 advisory）：
  ⑩ sentence_rhythm_monotony 句长单调（Gary Provost"vary the sentence length"）——
                        叙述句长变异系数过低或同档句长长 run=行文没有音乐性；纯数值。
  ⑪ crutch_phrases      拐杖短语（"忍不住/皱了皱眉/眼中闪过一丝"）——传统改稿第一刀：
                        作者无意识复读的万能短语，全书按千字密度计。
  ⑫ echo_words          近窗回声（echo words）——同一实词短语在 ~120 字窗口内复读，
                        打断行文节奏；统计侧兜住 crutch 词表外的个人拐杖词。
  ⑬ head_hopping        视角跳头（John Gardner 心理距离/POV 纪律）——第三人称限知章内
                        ≥2 个角色的内心被直读（"沈砚心想…裴决暗道…"），读者被甩出 POV。

【D. 开场滥调与段落节奏】（2026-07 第四轮补，同样全 advisory）：
  ⑭ slush_opening_cliche 行业滥调开场（出版 slush pile 退稿实务）——章首窗口命中
                        梦醒起床/天气铺陈/照镜自述模式库；plot_variety 的开篇同型查
                        **自我重复**，本信号查**行业黑名单**（用一次也是滥调）。
                        第 1 章命中最重（agent 第一页退稿高频原因）。
  ⑮ paragraph_opening_monotony 段首同型 run——连续 ≥4 个叙述段以同一开头起段
                        （都是"他…"或同一人名），句长 cv 之外的**段落级**节奏盲区；
                        传统 line-edit checklist 的 vary-paragraph-openings 项。

【E. 段落极端形态】（2026-07 第五轮补，出处见 novel/Q&A.md Q13）：
  ⑯ wall_of_text        墙文本——单段超长（编辑口径：约超过半页的连续段落即墙）；
                        手机端网文尤其致命（一屏全是字=划走）。纯字数判。
  ⑰ fragmented_paragraph_run 碎句体 run——连续多个叙述段每段只有几个字
                        （"一声。/又一声。"式短剧碎句体）。生产实锤：王敦外传
                        第20章大量单句成段，信息密度被拉薄、行文滑向短视频脚本腔。
                        只数叙述段（对话行天然短，跳过不断 run）；动作场景有意
                        碎拍合法，恒 advisory。

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
                               PHILO_DIALOGUE_KW, LOGIC_KW, CRUTCH_PHRASE_KW,
                               SLUSH_OPENING_PATTERNS,
                               classify_platform, PROFILE_COMMERCIAL)
except Exception:
    MORALIZING_PATTERNS = EMOTION_LABEL_KW = PHYSIO_BODY_KW = []
    PHYSIO_REACTION_KW = SMELL_KW = SETTING_MIRROR_KW = PHILO_DIALOGUE_KW = LOGIC_KW = []
    CRUTCH_PHRASE_KW = []
    SLUSH_OPENING_PATTERNS = {}
    def classify_platform(p):  # type: ignore
        return "商业爽文向"
    PROFILE_COMMERCIAL = "商业爽文向"
try:
    from wiki_builder import parse_character_names
except Exception:
    def parse_character_names(project):  # type: ignore
        return []

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
# C 组阈值（句节奏/拐杖短语/回声/视角跳头）
RHYTHM_MIN_SENTS = int(os.environ.get("NOVEL_PROSE_RHYTHM_MIN_SENTS", "30"))   # 章内叙述句样本下限
RHYTHM_CV_WARN = float(os.environ.get("NOVEL_PROSE_RHYTHM_CV", "0.30"))        # 句长变异系数下限
RHYTHM_RUN_WARN = int(os.environ.get("NOVEL_PROSE_RHYTHM_RUN", "8"))           # 同档句长连续 run
CRUTCH_PER_K = float(os.environ.get("NOVEL_PROSE_CRUTCH_PER_K", "1.2"))        # 拐杖短语/千字（全书）
ECHO_WINDOW = int(os.environ.get("NOVEL_PROSE_ECHO_WINDOW", "120"))            # 回声近窗字数
ECHO_MIN_REPEATS = int(os.environ.get("NOVEL_PROSE_ECHO_REPEATS", "3"))        # 窗口内同短语次数
ECHO_MAX_ALERTS = int(os.environ.get("NOVEL_PROSE_ECHO_MAX_ALERTS", "5"))      # 全书回声告警上限
HEADHOP_MIN_HITS = int(os.environ.get("NOVEL_PROSE_HEADHOP_HITS", "2"))        # 每角色内心直读次数下限
FIRST_PERSON_PER_K = float(os.environ.get("NOVEL_PROSE_FIRSTPERSON_PER_K", "8"))  # "我"密度超此值视为第一人称章
# D 组阈值（开场滥调/段首同型）
SLUSH_HEAD_CHARS = int(os.environ.get("NOVEL_PROSE_SLUSH_HEAD_CHARS", "300"))   # 开篇窗口字数
PARA_OPEN_RUN = int(os.environ.get("NOVEL_PROSE_PARA_OPEN_RUN", "4"))           # 段首同型连续段数
# E 组阈值（段落极端形态）
WALL_PARA_CHARS = int(os.environ.get("NOVEL_PROSE_WALL_CHARS", "400"))          # 单段字数上限（墙）
WALL_MIN_PARAS = int(os.environ.get("NOVEL_PROSE_WALL_MIN_PARAS", "2"))         # 章内墙段数达此才报
FRAG_PARA_CHARS = int(os.environ.get("NOVEL_PROSE_FRAG_CHARS", "12"))           # 碎段字数下限
FRAG_RUN = int(os.environ.get("NOVEL_PROSE_FRAG_RUN", "8"))                     # 连续碎段数
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


# ── C 组纯函数（句节奏 / 拐杖短语 / 回声 / 视角跳头）──────────────────────────
_SENT_SPLIT_RE = re.compile(r"[。！？!?；;]+")
# 回声候选 3-gram 的排除字符：全是虚词/代词的短语不算"实词回声"。
_ECHO_STOP_CHARS = set("的了是在有和与就都也又还这那他她它我你们自己一个不没到把被向从")
# 内心直读动词（psychic distance level 5 的确定性形态）：主语紧邻这些词=该角色内心被直读。
_INTERIOR_VERBS = ("心想", "心道", "暗想", "暗道", "暗忖", "腹诽", "心里嘀咕", "心中暗", "心里暗")
_INTERIOR_FALLBACK_RE = re.compile(r"([一-鿿]{2,3})(?:" + "|".join(_INTERIOR_VERBS) + r")")


def sentence_lengths(narration_lines):
    """叙述行按句切分后的句长列表（字数，丢空句）。纯函数·可测。"""
    text = "\n".join(narration_lines or [])
    return [len(s.strip()) for s in _SENT_SPLIT_RE.split(text) if s.strip()]


def rhythm_stats(lengths):
    """句长节奏统计：{cv 变异系数, max_run 同档(6字一档)最长连续}。纯函数·可测。

    Gary Provost 手艺（"This sentence has five words…"）：句长必须有长短交替的音乐性。
    cv 过低=全书一个节拍；同档长 run=连续 N 句几乎等长（哪怕全书 cv 尚可）。
    """
    n = len(lengths or [])
    if not n:
        return {"cv": 0.0, "max_run": 0}
    mean = sum(lengths) / n
    if mean <= 0:
        return {"cv": 0.0, "max_run": 0}
    var = sum((x - mean) ** 2 for x in lengths) / n
    cv = (var ** 0.5) / mean
    max_run = run = 1
    for prev, cur in zip(lengths, lengths[1:]):
        if cur // 6 == prev // 6:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 1
    return {"cv": round(cv, 3), "max_run": max_run}


def crutch_phrase_counts(text):
    """{拐杖短语: 次数}（只留 >0 项）。纯函数。词表单一真值源 keyword_banks.CRUTCH_PHRASE_KW。"""
    t = text or ""
    out = {}
    for ph in CRUTCH_PHRASE_KW:
        c = t.count(ph)
        if c:
            out[ph] = c
    return out


def echo_hits(text, exclude=(), window=None, min_repeats=None):
    """近窗回声：实词 3-gram 在 window 字内复读 ≥ min_repeats 次。纯函数·可测。

    返回 [{"phrase", "count", "span"}]，按次数降序、贪心去重（与已取回声共享 2 字重叠的
    候选丢弃，避免"深吸一/吸一口"重复报）。exclude：角色名/已计入拐杖词表的短语不报
    （名字复读是正常指代；词表命中归 crutch_phrases 信号）。
    """
    window = window or ECHO_WINDOW
    min_repeats = min_repeats or ECHO_MIN_REPEATS
    t = re.sub(r"\s+", "", text or "")
    positions = {}
    for i in range(len(t) - 2):
        g = t[i:i + 3]
        if not re.fullmatch(r"[一-鿿]{3}", g):
            continue
        if sum(1 for ch in g if ch in _ECHO_STOP_CHARS) >= 2:
            continue
        positions.setdefault(g, []).append(i)
    cands = []
    for g, pos in positions.items():
        if len(pos) < min_repeats:
            continue
        if any(g in ex or ex in g for ex in exclude if ex):
            continue
        for k in range(len(pos) - min_repeats + 1):
            span = pos[k + min_repeats - 1] - pos[k]
            if span <= window:
                cands.append({"phrase": g, "count": len(pos), "span": span})
                break
    cands.sort(key=lambda c: (-c["count"], c["span"]))
    picked = []
    for c in cands:
        if any(len(set(c["phrase"]) & set(p["phrase"])) >= 2 for p in picked):
            continue
        picked.append(c)
    return picked


def interiority_subjects(text, roster=()):
    """{角色名: 内心直读次数}。纯函数·可测。

    名册优先（wiki 角色卡单一来源）：名字后 ≤2 字内跟内心动词才计；名册空时退化用
    正则捕获主语（会糙，仅兜底）。POV 纪律（John Gardner）：第三人称限知视角下，
    一章内被直读内心的角色应只有一个——两个及以上=head-hopping 候选。
    """
    t = text or ""
    out = {}
    verbs = "|".join(_INTERIOR_VERBS)
    if roster:
        for name in roster:
            if not name:
                continue
            c = len(re.findall(re.escape(name) + r".{0,2}?(?:" + verbs + r")", t))
            if c:
                out[name] = c
    else:
        for m in _INTERIOR_FALLBACK_RE.finditer(t):
            out[m.group(1)] = out.get(m.group(1), 0) + 1
    return out


# ── D 组纯函数（开场滥调 / 段首同型）────────────────────────────────────────
def slush_opening_hits(text, head_chars=None):
    """章首窗口命中的滥调开场类别 → [{"category", "pattern"}]。纯函数·可测。

    只在开篇窗口匹配（"睁开眼"落在章中是正常动作，落在开篇即梦醒滥调）；
    每类只报首个命中模式，宁漏勿滥。
    """
    head_chars = head_chars or SLUSH_HEAD_CHARS
    head = (text or "").lstrip()[:head_chars]
    hits = []
    for category in sorted(SLUSH_OPENING_PATTERNS):
        for pattern in SLUSH_OPENING_PATTERNS[category]:
            if pattern in head:
                hits.append({"category": category, "pattern": pattern})
                break
    return hits


def paragraph_openers(text):
    """叙述段的段首 opener 序列（排除对白引导段）。纯函数·可测。

    opener = 段首 2 字；首字是单字代词（他/她/我/它）时取首字——
    "他推门"与"他转身"同 opener（都是"他"起段），2 字人名/名词则整取。
    """
    openers = []
    for para in (text or "").splitlines():
        p = para.strip()
        if not p or _DIALOGUE_LINE_RE.match(p) or p.startswith("#"):
            continue
        openers.append(p[0] if p[0] in "他她我它" else p[:2])
    return openers


def opener_max_run(openers):
    """(最长同 opener 连续段数, 该 opener)。纯函数·可测。"""
    best_run, best_val = 0, None
    run = 0
    prev = None
    for o in openers or []:
        run = run + 1 if o == prev else 1
        prev = o
        if run > best_run:
            best_run, best_val = run, o
    return best_run, best_val


# ── E 组纯函数（段落极端形态）────────────────────────────────────────────
def paragraph_extremes(text):
    """(墙段列表[前30字], 最长叙述碎段连续 run)。纯函数·可测。

    墙 = 单段 ≥WALL_PARA_CHARS 字（所有段都算，长对白段同样是墙）；
    碎段 run = **叙述段**连续 <FRAG_PARA_CHARS 字的最长 run——对话行天然短，
    跳过且**不断** run（碎句体的病灶在叙述侧，混排对白不该稀释信号）。"""
    walls, frag_run, frag_best = [], 0, 0
    for para in (text or "").splitlines():
        p = para.strip()
        if not p or p.startswith("#"):
            continue
        if len(p) >= WALL_PARA_CHARS:
            walls.append(p[:30])
        if _DIALOGUE_LINE_RE.match(p):
            continue
        frag_run = frag_run + 1 if len(p) < FRAG_PARA_CHARS else 0
        frag_best = max(frag_best, frag_run)
    return walls, frag_best


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

    try:
        roster = tuple(parse_character_names(project) or [])
    except Exception:
        roster = ()
    alerts, rows = [], []
    tot_chars = tot_label = tot_physio = tot_smell = tot_mirror = tot_moralize = 0
    crutch_totals = {}
    echo_alerts_left = ECHO_MAX_ALERTS
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

        # ── C 组：句节奏 / 回声 / 视角跳头（逐章）＋ 拐杖短语（累计）────────────
        lengths = sentence_lengths(narration)
        if len(lengths) >= RHYTHM_MIN_SENTS:
            rs = rhythm_stats(lengths)
            if rs["cv"] < RHYTHM_CV_WARN or rs["max_run"] >= RHYTHM_RUN_WARN:
                detail = (f"变异系数 {rs['cv']:g}（阈 {RHYTHM_CV_WARN:g}）" if rs["cv"] < RHYTHM_CV_WARN
                          else f"连续 {rs['max_run']} 句同档句长（阈 {RHYTHM_RUN_WARN}）")
                alerts.append({"type": "sentence_rhythm_monotony", "severity": "建议级", "auto": True,
                               "chapter": cid,
                               "note": (f"第{cid}章叙述句长单调：{detail}——Provost 手艺：句长要有"
                                        f"长短交替的音乐性，短句提速、长句蓄势；连排等长句读起来是"
                                        f"节拍器不是文章（{PROVENANCE}）")})
        narr_text = "\n".join(narration)
        if echo_alerts_left > 0:
            echoes = echo_hits(narr_text, exclude=roster + tuple(CRUTCH_PHRASE_KW))
            for e in echoes[:echo_alerts_left]:
                alerts.append({"type": "echo_words", "severity": "info", "auto": True, "chapter": cid,
                               "phrase": e["phrase"],
                               "note": (f"第{cid}章「{e['phrase']}」在 {e['span']} 字内复读（全章 {e['count']} 次）"
                                        f"——近窗回声（echo）打断行文节奏；换说法或删并（{PROVENANCE}）")})
            echo_alerts_left -= len(echoes[:echo_alerts_left])
        if chars and _per_k(narr_text.count("我"), len(narr_text) or 1) < FIRST_PERSON_PER_K:
            subjects = interiority_subjects(text, roster)
            hoppers = sorted(n for n, c in subjects.items() if c >= HEADHOP_MIN_HITS)
            if len(hoppers) >= 2:
                alerts.append({"type": "head_hopping", "severity": "建议级", "auto": True, "chapter": cid,
                               "entities": hoppers,
                               "note": (f"第{cid}章 {len(hoppers)} 个角色的内心被直读（{'、'.join(hoppers[:4])}）"
                                        f"——第三人称限知的 POV 纪律：一章一双眼睛，跳头（head-hopping）"
                                        f"把读者甩出视角；他人内心改由言行外显（{PROVENANCE}）")})
        for ph, c in crutch_phrase_counts(text).items():
            crutch_totals[ph] = crutch_totals.get(ph, 0) + c

        # ── D 组：开场滥调（章首窗口）/ 段首同型（逐章）──────────────────────
        slush = slush_opening_hits(text)
        if slush:
            cats = "、".join(f"{h['category']}（「{h['pattern']}」）" for h in slush)
            first_page = "——第 1 章开篇即滥调是 agent 第一页退稿的高频原因，务必改切入" if cid == 1 else ""
            alerts.append({"type": "slush_opening_cliche", "severity": "建议级", "auto": True,
                           "chapter": cid, "categories": [h["category"] for h in slush],
                           "note": (f"第{cid}章开篇窗口命中行业滥调开场：{cats}——梦醒/天气/照镜是"
                                    f"编辑退稿统计的头部滥调（区别于开篇自我重复：黑名单模式用一次"
                                    f"也是滥调）；从冲突或动作切入{first_page}（{PROVENANCE}）")})
        run_len, run_val = opener_max_run(paragraph_openers(text))
        if run_len >= PARA_OPEN_RUN:
            alerts.append({"type": "paragraph_opening_monotony", "severity": "建议级", "auto": True,
                           "chapter": cid, "opener": run_val, "run": run_len,
                           "note": (f"第{cid}章连续 {run_len} 个叙述段都以「{run_val}」起段"
                                    f"（阈 {PARA_OPEN_RUN}）——段首同型是句长之外的段落级单调；"
                                    f"传统 line-edit：换主语、换句式、动作或场景先行（{PROVENANCE}）")})

        # ── E 组：段落极端形态（逐章）──────────────────────────────────────
        walls, frag_best = paragraph_extremes(text)
        if len(walls) >= WALL_MIN_PARAS:
            alerts.append({"type": "wall_of_text", "severity": "建议级", "auto": True,
                           "chapter": cid, "count": len(walls), "evidence": "；".join(walls[:2]),
                           "note": (f"第{cid}章 {len(walls)} 个超长段（≥{WALL_PARA_CHARS} 字/段）——"
                                    f"墙文本：编辑口径约半页不分段即墙，手机端一屏全是字=划走；"
                                    f"按动作/视点/话题转换拆段，留白也是节奏（{PROVENANCE}）")})
        if frag_best >= FRAG_RUN:
            alerts.append({"type": "fragmented_paragraph_run", "severity": "建议级", "auto": True,
                           "chapter": cid, "run": frag_best,
                           "note": (f"第{cid}章连续 {frag_best} 个叙述段每段不足 {FRAG_PARA_CHARS} 字"
                                    f"（阈 {FRAG_RUN}）——碎句体：单句成段连排是短视频脚本腔，"
                                    f"信息密度被拉薄、庄重感流失；碎拍留给真正的爆点，"
                                    f"其余合并成正常段落（动作场景有意碎拍合法，人工取舍）（{PROVENANCE}）")})

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
    crutch_n = sum(crutch_totals.values())
    if tot_chars and _per_k(crutch_n, tot_chars) > CRUTCH_PER_K:
        top = sorted(crutch_totals.items(), key=lambda kv: -kv[1])[:5]
        alerts.append({"type": "crutch_phrases", "severity": "建议级", "auto": True,
                       "top": [{"phrase": p, "count": c} for p, c in top],
                       "note": (f"全书拐杖短语 {_per_k(crutch_n, tot_chars):.1f}/千字（阈 {CRUTCH_PER_K:g}）——"
                                f"高频：{'、'.join(f'{p}×{c}' for p, c in top)}。单次无罪，全书复读="
                                f"行文肌理单一；传统改稿第一刀就是列出自己的拐杖词清单逐个替换（{PROVENANCE}）")})

    return {
        "ran": True,
        "profile": profile,
        "thresholds": {"filter_per_k": FILTER_PER_K, "adv_tag_per_k": ADV_TAG_PER_K,
                       "dialogue_hi": DIALOGUE_HI, "dialogue_lo": DIALOGUE_LO,
                       "moralize_per_chapter": MORALIZE_PER_CHAPTER,
                       "physio_ratio_warn": PHYSIO_RATIO_WARN, "smell_per_k": SMELL_PER_K,
                       "mirror_per_k": MIRROR_PER_K, "philo_per_k": philo_limit,
                       "rhythm_cv": RHYTHM_CV_WARN, "rhythm_run": RHYTHM_RUN_WARN,
                       "crutch_per_k": CRUTCH_PER_K, "echo_window": ECHO_WINDOW,
                       "headhop_min_hits": HEADHOP_MIN_HITS,
                       "slush_head_chars": SLUSH_HEAD_CHARS, "para_open_run": PARA_OPEN_RUN,
                       "wall_chars": WALL_PARA_CHARS, "frag_chars": FRAG_PARA_CHARS,
                       "frag_run": FRAG_RUN,
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
