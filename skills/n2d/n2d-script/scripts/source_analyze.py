#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""n2d source analysis.

Builds a local analysis package from the n2d project's own source text. This
keeps stage-1 scaffolding self-contained: no upstream project ledger or export
schema is required.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Iterable, Sequence


KIND = "n2d_source_analysis"
ANALYSIS_JSON_REL = os.path.join("设定库", "source_analysis.json")
ANALYSIS_MD_REL = os.path.join("设定库", "source_analysis.md")
SPLIT_PLAN_REL = os.path.join("脚本", "split_plan.json")
SPLIT_PLAN_HEAD_BYTES = 64 * 1024
ESTIMATED_EPISODE_COUNT_RE = re.compile(
    rb'"estimated_total_episode_count"\s*:\s*([0-9]+)'
)

CHAPTER_RE = re.compile(
    r"^\s*(?:\[编辑\]\s*)?第\s*([0-9零〇一二三四五六七八九十百千万两]+)\s*([章回囬囘廻节節卷])"
)
HUI_UNITS = frozenset("回囬囘廻")
CHINESE_DIGITS = {
    "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}
CHINESE_UNITS = {"十": 10, "百": 100, "千": 1000}
INTEGRITY_EXAMPLE_LIMIT = 50

# Conservative source-hygiene signals. These are report-only: source text is
# never rewritten, and downstream creators must still confirm every candidate.
SEPARATOR_RE = re.compile(r"^(?:-{3,}|—{3,}|_{3,}|={3,}|\*{3,}|\.{3,}|…{2,})$")
HARD_SEPARATOR_RE = re.compile(r"^(?:-{5,}|—{5,}|_{5,}|={5,}|\*{5,})$")
CAPTION_RE = re.compile(r"^[一-龥A-Za-z·—-]{2,16}$")
AUTHOR_NOTE_HINT_RE = re.compile(
    r"(?:作者的话|本章说|本书|打卡处|前文已修改|请假|休息|歇.{0,3}天|加更|"
    r"更新|码字|发[一二两三四五六七八九十\d]+章|[一二两三四五六七八九十\d]+更|继续.{0,4}更|"
    r"剩下.{0,6}发|欠.{0,8}章|还债|求.{0,8}(?:票|收藏|好评|评分)|"
    r"跪求|催更|礼物|奉上|道歉|感谢.{0,8}支持|五星|小作者|新地图|铺垫.{0,4}章|"
    r"理解一下|TVT|OVO|ovo|嘤嘤|困困|八爪)"
)
COMPLETE_SIGNAL_RE = re.compile(r"(?:全书完|全文完|正文完|完结感言|正式完结|已完结)")
ONGOING_SIGNAL_RE = re.compile(
    r"(?:未完待续|请假|加更|继续更新|明天.{0,8}(?:继续|更新|还债)|恢复.{0,4}更|"
    r"欠.{0,8}章|还债|下一章)"
)
SENT_SPLIT_RE = re.compile(r"(?<=[。！？!?；;])")
SPEECH_VERB_RE = re.compile(
    r"([一-龥]{2,4}?)(?:[，,、]?\s*)"
    r"(?:低声|沉声|冷声|淡淡|忽然|立刻|缓缓|咬牙|皱眉|抬头|转身|一笑|冷笑|苦笑|"
    r"轻声|柔声|漠然|平静|连忙|大声|高声|沙哑)?"
    r"(?:问道|说道|喝道|喊道|怒道|笑道|答道|道|说|问|喊|喝|叫|答)\s*(?:[:：]|[“\"])"
)
SPEECH_TAIL_RE = re.compile(
    r"(?:低声|沉声|冷声|淡淡|忽然|立刻|缓缓|咬牙|皱眉|抬头|转身|一笑|冷笑|苦笑|"
    r"轻声|柔声|漠然|平静|连忙|大声|高声|沙哑|拱手|缓缓开口|忽然开口|开口|"
    r"语重心长|没好气|解释|厉声|摇了摇头|硬着头皮|讥讽|压低嗓音|皮笑肉不笑|"
    r"接着|面无表情|抱拳)?"
    r"(?:问道|说道|喝道|喊道|怒道|笑道|答道|道|说|问|喊|喝|叫|答)\s*$"
)
TITLE_NAME_RE = re.compile(r"(?:我是|本座|老夫|贫道|臣|妾身|在下)([一-龥]{2,4})")

STOP_NAMES = {
    "第一", "第二", "第三", "这一", "那一", "所有", "众人", "他们", "她们", "你们", "我们", "自己",
    "这个", "那个", "什么", "怎么", "只是", "已经", "突然", "这里", "那里", "眼前", "身后",
    "时候", "声音", "男人", "女人", "少年", "少女", "老人", "系统", "面板", "灵气", "众弟子",
    "获得", "当前", "死死", "不知", "我知", "谁知", "无数", "一道", "开口", "话未", "消耗",
    "九大", "二十五脉", "化作一", "六尊天品", "你爹", "亲爹",
    # Speech/action modifiers often appear immediately before “道/说/问”.
    # The lightweight regex can otherwise misread “轻声道” as a character named “轻声”.
    "继续", "轻声", "低声", "沉声", "冷声", "淡淡", "忽然", "立刻", "缓缓", "咬牙", "皱眉",
    "抬头", "转身", "一笑", "冷笑", "苦笑", "漠然", "随后", "按理", "还是", "随口", "连忙",
    "这番话", "能眼睁睁", "凄厉的惨", "侧过头", "面色放缓", "思索片刻", "叹了口气", "自顾自",
}
STOP_ENDINGS = ("时候", "声音", "眼神", "脸色", "身影", "心中", "门口", "台下", "众人", "所有")
NON_PERSON_PREFIXES = ("获得", "当前", "消耗", "化作", "无数", "一道")
BAD_NAME_FRAGMENTS = (
    "开口", "拱手", "解释", "厉声", "摇了摇头", "硬着头皮", "讥讽", "压低嗓音",
    "皮笑肉不", "接着", "面无表情", "忽然", "缓缓", "没好气", "语重心长",
    "是否", "消耗", "要知", "世道", "没有", "高临下", "思索", "声音", "侧过头",
    "面色", "闻言", "继续", "顿了顿", "摇头", "抱拳", "无奈", "疑惑", "试探",
    "意味深长", "躬身", "忽而", "森然", "说着", "平淡", "喃喃", "神神秘秘",
    "下意识", "正色", "咬牙切齿", "叹了口气", "自顾自",
)
SPEAKER_ACTION_MARKERS = (
    "侧过头", "面色", "声音", "叹了口气", "闻言", "思索", "摇了摇头", "抬起头",
    "皱眉", "微微", "缓缓", "漠然", "冷笑", "苦笑", "柔声", "轻声", "低声",
    "沉声", "冷声", "厉声", "拱手", "咬牙", "转身", "看着", "望着", "盯着",
    "整理", "直起身", "眼中", "脸上", "神色", "心中", "嘴角", "眉头",
    "自顾自",
)

LOCATION_SUFFIXES = (
    "殿", "宫", "楼", "阁", "城", "山", "峰", "谷", "院", "府", "堂", "厅", "门", "宗", "派",
    "村", "镇", "街", "巷", "河", "湖", "岛", "洞府", "战场", "客栈", "书房", "房间", "后院",
)
LOCATION_RE = re.compile(
    r"(?:来到|进入|走进|回到|赶到|站在|坐在|藏在|冲进|逃进|离开|穿过)"
    r"([一-龥]{2,14}(?:" + "|".join(re.escape(s) for s in LOCATION_SUFFIXES) + r"))"
)

FORESHADOW_MARKERS = (
    "伏笔", "悬念", "埋下", "未解", "成谜", "暗藏", "别有深意", "意味深长",
    "似乎另有", "不为人知", "秘密", "真相", "线索", "钥匙", "印记", "玉佩", "令牌",
)
REALM_TERMS = (
    "练气", "筑基", "金丹", "元婴", "化神", "炼虚", "合体", "大乘", "渡劫",
    "武徒", "武者", "武师", "宗师", "大宗师", "先天", "后天", "觉醒", "超凡", "神通",
)
SYSTEM_TERMS = ("系统", "面板", "属性", "等级", "经验值", "任务", "签到", "抽奖", "积分", "战力")
STATE_TERMS = (
    "受伤", "重伤", "中毒", "失明", "毁容", "断臂", "白发", "黑化", "觉醒",
    "换上", "战甲", "嫁衣", "面具", "蒙面", "破损", "血迹",
)
GENRE_SIGNALS = {
    "系统流": ("系统", "面板", "签到", "任务", "抽奖", "奖励"),
    "修仙/玄幻": ("练气", "筑基", "灵根", "宗门", "妖兽", "法宝", "丹药", "渡劫"),
    "都市异能": ("觉醒", "异能", "都市", "公司", "警局", "医院", "学校"),
    "女频情感": ("婚约", "夫人", "王爷", "侯府", "总裁", "离婚", "重逢", "心动"),
    "悬疑": ("尸体", "凶手", "线索", "证据", "案发", "真相", "监控"),
}


def read_text(path: str) -> str:
    raw = Path(path).read_bytes()
    for enc in ("utf-8", "utf-8-sig", "gb18030", "gbk", "big5"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def read_estimated_episode_count(root: str) -> int | None:
    """Read the split-plan summary field without loading a potentially huge plan.

    split_novel writes this field near the JSON header before source_units. A
    bounded binary read keeps the standalone source_analyze CLI safe for plans
    that are tens of MiB while preserving the explicit-episodes API behavior.
    """
    path = Path(root) / SPLIT_PLAN_REL
    try:
        with path.open("rb") as handle:
            head = handle.read(SPLIT_PLAN_HEAD_BYTES)
    except OSError:
        return None
    match = ESTIMATED_EPISODE_COUNT_RE.search(head)
    return int(match.group(1)) if match else None


def normalize_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\r?\n+", text or "") if p.strip()]


def parse_chapter_number(value: str | None) -> int | None:
    """Parse the Arabic/common-Chinese chapter token captured by CHAPTER_RE."""
    token = str(value or "").strip()
    if token.isdigit():
        return int(token)
    if not token or any(ch not in CHINESE_DIGITS and ch not in CHINESE_UNITS for ch in token):
        return None
    total = 0
    number = 0
    for ch in token:
        if ch in CHINESE_DIGITS:
            number = CHINESE_DIGITS[ch]
        else:
            total += (number or 1) * CHINESE_UNITS[ch]
            number = 0
    return total + number


def fold_adjacent_duplicate_chapter_headings(text: str) -> str:
    """Drop only physically adjacent, byte-equivalent chapter-heading lines.

    Comparison happens after Python removes the newline terminator but before
    stripping any other whitespace. Thus differently spaced/titled headings,
    or the same heading separated by a blank/body line, remain untouched.
    """
    kept: list[str] = []
    previous: str | None = None
    for line in (text or "").splitlines():
        if previous is not None and line == previous and CHAPTER_RE.match(line):
            previous = line
            continue
        kept.append(line)
        previous = line
    return "\n".join(kept)


def _near_line(index: int, candidates: set[int], distance: int) -> bool:
    return any(abs(index - other) <= distance for other in candidates)


def _source_integrity(text: str) -> dict:
    """Return report-only source-integrity evidence with original line numbers."""
    lines = (text or "").splitlines()
    duplicate_rows: list[dict] = []
    kept_headings: list[dict] = []
    previous: str | None = None
    previous_line = 0
    chapter_line_indexes: set[int] = set()

    for index, line in enumerate(lines):
        match = CHAPTER_RE.match(line)
        if match:
            chapter_line_indexes.add(index)
            if previous is not None and line == previous and CHAPTER_RE.match(previous):
                duplicate_rows.append({
                    "line": index + 1,
                    "duplicate_of_line": previous_line,
                    "text": line.strip(),
                })
            else:
                kept_headings.append({
                    "line": index + 1,
                    "number": parse_chapter_number(match.group(1)),
                    "unit": match.group(2),
                    "text": line.strip(),
                })
        previous = line
        previous_line = index + 1

    # 维基文库/古籍导出常用「第1章」包十个真实「第N囬」。若存在回目，
    # 以回目为有效源单元，避免把卷包装标题混入章节数并覆盖 1-10 回。
    hui_headings = [row for row in kept_headings if row.get("unit") in HUI_UNITS]
    effective_headings = hui_headings or kept_headings
    chapter_numbers = sorted({
        row["number"] for row in effective_headings if isinstance(row.get("number"), int)
    })
    missing: list[int] = []
    missing_truncated = False
    if chapter_numbers:
        span = chapter_numbers[-1] - chapter_numbers[0]
        if span <= 10000:
            present = set(chapter_numbers)
            missing = [n for n in range(chapter_numbers[0], chapter_numbers[-1] + 1) if n not in present]
        else:
            missing_truncated = True

    captions: list[dict] = []
    for index, line in enumerate(lines):
        value = line.strip()
        if (
            not value
            or CHAPTER_RE.match(line)
            or not CAPTION_RE.fullmatch(value)
            or SEPARATOR_RE.fullmatch(value)
            or value.endswith(("——", "--"))
            or AUTHOR_NOTE_HINT_RE.search(value)
        ):
            continue
        adjacent_separator = any(
            0 <= other < len(lines) and SEPARATOR_RE.fullmatch(lines[other].strip())
            for other in (index - 1, index + 1)
        )
        if _near_line(index, chapter_line_indexes, 4) or adjacent_separator:
            captions.append({"line": index + 1, "text": value, "kind": "suspected_caption"})

    hard_separator_indexes = {
        index for index, line in enumerate(lines) if HARD_SEPARATOR_RE.fullmatch(line.strip())
    }
    author_notes: list[dict] = []
    for index, line in enumerate(lines):
        value = line.strip()
        if not value or not AUTHOR_NOTE_HINT_RE.search(value):
            continue
        if index < 20 or _near_line(index, hard_separator_indexes, 2):
            author_notes.append({
                "line": index + 1,
                "text": value[:200],
                "kind": "suspected_author_note",
            })

    completion_clues: list[dict] = []
    for index, line in enumerate(lines):
        value = line.strip()
        if not value:
            continue
        if COMPLETE_SIGNAL_RE.search(value):
            completion_clues.append({"line": index + 1, "text": value[:200], "kind": "complete"})
        if ONGOING_SIGNAL_RE.search(value) and (
            index < 20 or _near_line(index, hard_separator_indexes, 2)
        ):
            completion_clues.append({"line": index + 1, "text": value[:200], "kind": "ongoing"})

    last_content_line = max((i + 1 for i, line in enumerate(lines) if line.strip()), default=0)
    near_end = [
        clue for clue in completion_clues
        if clue["line"] >= max(1, last_content_line - 200)
    ]
    if near_end:
        completion_status = "likely_complete" if near_end[-1]["kind"] == "complete" else "likely_ongoing"
    else:
        completion_status = "unknown"

    return {
        "line_count": len(lines),
        "raw_chapter_heading_count": len(kept_headings) + len(duplicate_rows),
        "adjacent_duplicate_heading_count": len(duplicate_rows),
        "adjacent_duplicate_heading_examples": duplicate_rows[:INTEGRITY_EXAMPLE_LIMIT],
        "duplicate_heading_examples_truncated": len(duplicate_rows) > INTEGRITY_EXAMPLE_LIMIT,
        "recognized_heading_count_after_fold": len(kept_headings),
        "ignored_wrapper_heading_count": len(kept_headings) - len(effective_headings),
        "preferred_unit_system": "hui" if hui_headings else "chapter",
        "chapter_headings_after_fold": len(effective_headings),
        "unique_chapter_count": len(chapter_numbers),
        "missing_chapter_numbers": missing,
        "missing_chapter_numbers_truncated": missing_truncated,
        "completion_status": completion_status,
        "completion_clues": completion_clues,
        "suspected_captions": captions,
        "author_notes": author_notes,
    }


def split_sentences(text: str) -> list[str]:
    out: list[str] = []
    for para in normalize_paragraphs(text):
        out.extend(s.strip() for s in SENT_SPLIT_RE.split(para) if s.strip())
    return out


def chapter_count(text: str) -> int:
    folded = fold_adjacent_duplicate_chapter_headings(text)
    matches = [CHAPTER_RE.match(line) for line in folded.splitlines()]
    matches = [match for match in matches if match]
    hui = [match for match in matches if match.group(2) in HUI_UNITS]
    return len(hui or matches)


def clean_name(name: str) -> str:
    return re.sub(r"[，,。！？!?；;：“”\"'、\s]", "", name or "")


def valid_name(name: str) -> bool:
    if len(name) < 2 or len(name) > 4:
        return False
    if name[0] in {"他", "她", "它", "这", "那", "着"}:
        return False
    if name in STOP_NAMES:
        return False
    if name.startswith(NON_PERSON_PREFIXES):
        return False
    if any(fragment in name for fragment in BAD_NAME_FRAGMENTS):
        return False
    if re.search(r"[0-9零〇一二三四五六七八九十百千万两]", name):
        return False
    if any(name.endswith(s) for s in STOP_ENDINGS):
        return False
    return True


def speaker_name_from_left_context(left: str) -> str | None:
    """Infer a speaker from the text immediately before a quote/colon.

    This remains intentionally conservative: it only accepts clauses that end in
    a speech tail like “轻声道/拱手道/问道”. The subject is taken from the start
    of that clause, before common action markers, so “姜月初侧过头，轻声道”
    yields “姜月初” instead of the modifier “轻声”.
    """
    left = re.sub(r"\s+", "", left or "").strip("，,、：:“”\"' ")
    if not left or not SPEECH_TAIL_RE.search(left):
        return None
    stem = SPEECH_TAIL_RE.sub("", left).strip("，,、：:“”\"' ")
    if not stem:
        return None
    segment = re.split(r"[，,、]", stem)[0].strip()
    if not segment:
        return None
    cut = len(segment)
    for marker in SPEAKER_ACTION_MARKERS:
        idx = segment.find(marker)
        if idx >= 2:
            cut = min(cut, idx)
    candidate = clean_name(segment[:cut])
    if valid_name(candidate):
        return candidate
    if 2 <= len(segment) <= 4 and valid_name(segment):
        return segment
    return None


def extract_dialogue_speaker_names(sentence: str) -> list[str]:
    names: list[str] = []
    for m in re.finditer(r"[:：“\"]", sentence or ""):
        left = sentence[:m.start()]
        left = re.split(r"[。！？!?；;\n“”\"]", left)[-1]
        name = speaker_name_from_left_context(left)
        if name and name not in names:
            names.append(name)
    return names


def extract_characters(text: str, limit: int = 16) -> list[dict]:
    counts: Counter[str] = Counter()
    evidence: dict[str, list[str]] = defaultdict(list)
    for sentence in split_sentences(text):
        raw_names = []
        raw_names.extend(extract_dialogue_speaker_names(sentence))
        for rx in (SPEECH_VERB_RE, TITLE_NAME_RE):
            raw_names.extend(rx.findall(sentence))
        for raw in raw_names:
            name = clean_name(raw)
            if not valid_name(name):
                continue
            counts[name] += 1
            if len(evidence[name]) < 3:
                evidence[name].append(sentence[:80])
    return [
        {"name": name, "mentions": count, "evidence": evidence[name]}
        for name, count in counts.most_common(limit)
    ]


def extract_locations(text: str, limit: int = 12) -> list[dict]:
    counts: Counter[str] = Counter()
    evidence: dict[str, list[str]] = defaultdict(list)
    for sentence in split_sentences(text):
        for raw in LOCATION_RE.findall(sentence):
            loc = raw.strip("，,。！？!?；;：“”\"'、 ")
            if len(loc) < 2:
                continue
            counts[loc] += 1
            if len(evidence[loc]) < 2:
                evidence[loc].append(sentence[:80])
    return [
        {"name": name, "mentions": count, "evidence": evidence[name]}
        for name, count in counts.most_common(limit)
    ]


def extract_foreshadowing(text: str, limit: int = 20) -> list[dict]:
    candidates: list[dict] = []
    seen: set[str] = set()
    for sentence in split_sentences(text):
        if not any(marker in sentence for marker in FORESHADOW_MARKERS):
            continue
        desc = re.sub(r"\s+", "", sentence)[:60]
        if desc in seen:
            continue
        seen.add(desc)
        candidates.append({
            "id": f"SETUP_{len(candidates) + 1:03d}",
            "description": desc,
            "status": "candidate",
            "payoff_ep": "",
        })
        if len(candidates) >= limit:
            break
    return candidates


def extract_power_system(text: str) -> dict:
    realm_hits = [term for term in REALM_TERMS if term in text]
    system_hits = [term for term in SYSTEM_TERMS if term in text]
    return {
        "has_power_system_signal": bool(realm_hits or system_hits),
        "realm_terms": realm_hits,
        "system_terms": system_hits,
        "notes": "候选项来自 n2d 源文本启发式扫描；正式等级/数值规则需在阶段1精修时人工确认。",
    }


def extract_visual_state_signals(text: str, limit: int = 24) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for sentence in split_sentences(text):
        hits = [term for term in STATE_TERMS if term in sentence]
        if not hits:
            continue
        snippet = re.sub(r"\s+", "", sentence)[:70]
        if snippet in seen:
            continue
        seen.add(snippet)
        out.append({"signal": hits[0], "snippet": snippet})
        if len(out) >= limit:
            break
    return out


def infer_genres(text: str) -> list[dict]:
    scores = []
    for genre, terms in GENRE_SIGNALS.items():
        hits = [term for term in terms if term in text]
        if hits:
            scores.append({"genre": genre, "score": len(hits), "signals": hits})
    return sorted(scores, key=lambda item: item["score"], reverse=True)


def summarize_worldview(text: str, limit: int = 8) -> list[str]:
    paras = [p for p in normalize_paragraphs(text) if not CHAPTER_RE.match(p)]
    picked: list[str] = []
    signal_words = ("世界", "灵气", "王朝", "宗门", "系统", "异能", "朝堂", "都市", "末世", "学院", "大陆")
    for para in paras:
        clean = re.sub(r"\s+", "", para)
        if len(clean) > 140:
            continue
        if any(word in clean for word in signal_words) or len(picked) < 3:
            picked.append(clean[:100])
        if len(picked) >= limit:
            break
    return picked


def episode_briefs(episodes: Sequence[str], limit: int = 12) -> list[dict]:
    briefs = []
    for i, ep_text in enumerate(episodes[:limit], 1):
        clean = re.sub(r"\s+", "", ep_text or "")
        briefs.append({
            "episode": f"第{i}集",
            "chars": len(clean),
            "opening": clean[:80],
            "ending": clean[-80:],
        })
    return briefs


def analyze_source(title: str, text: str, episodes: Sequence[str] | None = None) -> dict:
    source_integrity = _source_integrity(text)
    normalized = "\n".join(normalize_paragraphs(fold_adjacent_duplicate_chapter_headings(text)))
    return {
        "schema_version": 1,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "title": title,
        "source": "n2d_source_text",
        "stats": {
            "characters": len(re.sub(r"\s+", "", normalized)),
            "chapters": source_integrity["chapter_headings_after_fold"],
            "episode_scaffolds": len(episodes or []),
        },
        "source_integrity": source_integrity,
        "genre_candidates": infer_genres(normalized),
        "worldview_candidates": summarize_worldview(normalized),
        "characters": extract_characters(normalized),
        "locations": extract_locations(normalized),
        "foreshadowing_candidates": extract_foreshadowing(normalized),
        "power_system": extract_power_system(normalized),
        "visual_state_signals": extract_visual_state_signals(normalized),
        "episode_briefs": episode_briefs(episodes or []),
    }


def render_character_roster(title: str, analysis: dict) -> str:
    lines = [
        f"# {title} — 角色卡总表",
        "",
        "> 本表由 n2d 源书分析预填候选；定妆前必须人工确认姓名、角色定位、视觉特征和形态变体。",
        "> 全篇首次出现即建卡，后续所有镜头严格复用。格式见 references/formats.md。",
        "",
    ]
    characters = analysis.get("characters") or []
    if not characters:
        lines += [
            "## 待建角色",
            "- 来源：源书分析未稳定识别具名角色；阶段1精修时按首现顺序补齐。",
            "- 视觉特征（脸/发/瞳/体型/服装）：（待补：定妆前必填）",
            "",
        ]
        return "\n".join(lines) + "\n"
    for item in characters:
        name = item.get("name") or "未命名"
        lines += [
            f"## {name}",
            f"- 源书命中次数：{item.get('mentions', 0)}",
            "- 角色定位：（待人工确认）",
            "- 计划出场集数：（待人工确认；供角色库分档，未知不要拿源书提及次数冒充）",
            "- 当前状态：（待人工确认）",
            "- 视觉特征（脸/发/瞳/体型/服装）：（待补：定妆前必填）",
        ]
        evidence = item.get("evidence") or []
        if evidence:
            lines.append(f"- 首批证据：{evidence[0]}")
        lines.append("")
    return "\n".join(lines) + "\n"


def render_analysis_md(analysis: dict) -> str:
    title = analysis.get("title") or "未命名"
    stats = analysis.get("stats") or {}
    lines = [
        f"# {title} — n2d 源书分析包",
        "",
        "> 本文件由 n2d-script 从本剧源文本直接生成，只作为阶段1改编/建卡/分镜的候选资料。",
        "> 候选项由制作代理按原文证据和当前合同复核后进入角色卡、世界观、伏笔账本或力量体系规则；证据冲突、改变核心方向或需要新增事实时才升级人工。",
        "",
        "## 统计",
        f"- 正文字数估算：{stats.get('characters', 0)}",
        f"- 章节数：{stats.get('chapters', 0)}",
        f"- 粗切集数：{stats.get('episode_scaffolds', 0)}",
        "",
    ]
    integrity = analysis.get("source_integrity") or {}
    if integrity:
        missing = integrity.get("missing_chapter_numbers") or []
        status_labels = {
            "likely_complete": "存在靠近文末的完结线索",
            "likely_ongoing": "存在靠近文末的连载/续更线索",
            "unknown": "未识别到可靠完结或续更线索",
        }
        lines += [
            "## 源完整性（source_integrity）",
            f"- 原始章节标题：{integrity.get('raw_chapter_heading_count', 0)}",
            f"- 相邻完全重复标题：{integrity.get('adjacent_duplicate_heading_count', 0)}（仅分析时折叠，源文件不改）",
            f"- 折叠后章节标题：{integrity.get('chapter_headings_after_fold', 0)}",
            f"- 唯一章号数：{integrity.get('unique_chapter_count', 0)}",
            f"- 缺失章号：{', '.join(str(n) for n in missing) if missing else '（无）'}",
            f"- 连载/完结判断：{status_labels.get(integrity.get('completion_status'), integrity.get('completion_status', 'unknown'))}",
        ]
        clues = integrity.get("completion_clues") or []
        if clues:
            lines.append("- 连载/完结线索：" + "；".join(
                f"L{item.get('line')} {item.get('text')}" for item in clues[-5:]
            ))
        captions = integrity.get("suspected_captions") or []
        lines.append(f"- 疑似图注：{len(captions)} 条")
        for item in captions[:20]:
            lines.append(f"  - L{item.get('line')}：{item.get('text')}")
        notes = integrity.get("author_notes") or []
        lines.append(f"- 疑似作者注：{len(notes)} 条")
        for item in notes[:20]:
            lines.append(f"  - L{item.get('line')}：{item.get('text')}")
        lines.append("")
    genres = analysis.get("genre_candidates") or []
    lines.append("## 题材候选")
    if genres:
        for g in genres:
            lines.append(f"- {g['genre']}：{', '.join(g.get('signals') or [])}")
    else:
        lines.append("- （未稳定识别，阶段1人工确认）")
    lines += ["", "## 世界观候选"]
    for item in analysis.get("worldview_candidates") or ["（待阶段1补写）"]:
        lines.append(f"- {item}")
    lines += ["", "## 角色候选"]
    chars = analysis.get("characters") or []
    if chars:
        for c in chars:
            lines.append(f"- {c.get('name')}（命中 {c.get('mentions', 0)} 次）")
    else:
        lines.append("- （未稳定识别，按首现手工建卡）")
    lines += ["", "## 场景候选"]
    locs = analysis.get("locations") or []
    if locs:
        for loc in locs:
            lines.append(f"- {loc.get('name')}（命中 {loc.get('mentions', 0)} 次）")
    else:
        lines.append("- （待阶段1补写）")
    lines += ["", "## 伏笔候选"]
    setups = analysis.get("foreshadowing_candidates") or []
    if setups:
        for setup in setups:
            lines.append(f"- {setup.get('id')}：{setup.get('description')}（payoff_ep 待填）")
    else:
        lines.append("- （未检测到显式伏笔标记；精修时仍需人工登记）")
    ps = analysis.get("power_system") or {}
    lines += ["", "## 力量体系候选"]
    lines.append(f"- 等级/境界词：{', '.join(ps.get('realm_terms') or []) or '（无）'}")
    lines.append(f"- 系统/数值词：{', '.join(ps.get('system_terms') or []) or '（无）'}")
    lines.append(f"- 备注：{ps.get('notes', '')}")
    return "\n".join(lines) + "\n"


def write_analysis(root: str, title: str, text: str, episodes: Sequence[str] | None = None) -> dict:
    analysis = analyze_source(title, text, episodes)
    if episodes is None:
        estimated_episode_count = read_estimated_episode_count(root)
        if estimated_episode_count is not None:
            analysis["stats"]["episode_scaffolds"] = estimated_episode_count
            analysis["stats"]["episode_scaffolds_source"] = (
                "脚本/split_plan.json:estimated_total_episode_count"
            )
    root_path = Path(root)
    json_path = root_path / ANALYSIS_JSON_REL
    md_path = root_path / ANALYSIS_MD_REL
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_analysis_md(analysis), encoding="utf-8")
    return analysis


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="从 n2d 源文本生成本线源书分析包")
    ap.add_argument("source_text")
    ap.add_argument("--root", required=True, help="n2d 作品根")
    ap.add_argument("--title", default=None)
    ns = ap.parse_args(argv)
    text = read_text(ns.source_text)
    title = ns.title or os.path.splitext(os.path.basename(ns.source_text))[0]
    analysis = write_analysis(ns.root, title, text)
    print(f"[ok] 已写 {ANALYSIS_JSON_REL} / {ANALYSIS_MD_REL}："
          f"角色候选 {len(analysis.get('characters') or [])}，"
          f"场景候选 {len(analysis.get('locations') or [])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
